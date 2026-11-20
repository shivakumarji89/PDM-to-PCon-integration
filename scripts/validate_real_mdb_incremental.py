"""Real-ACE validation of the incremental Maintenance MDB export on isolated copies.

Drives the real stage services (Articles, Class Creation, Properties & Values, Text,
Relations, Pricing, VARCOND relations) against a COPY of a genuine ProductStudio
``pcr_data_com_ocd.mdb`` through the 32-bit ACE bridge and records evidence.

Safety (enforced in code, not by convention):
  * the source MDB is only ever *read* (file copy); its SHA-256 is recorded before and
    after and the run fails if it changed;
  * every write goes to the copy under --workdir, which must be outside the source tree
    and outside this repository; source != destination is asserted before any write;
  * the MDB session store is a temporary folder inside --workdir;
  * nothing under --workdir is meant for Git (it is outside the repository).

Usage (repository root):
  python scripts/validate_real_mdb_incremental.py --source <pcr_data_com_ocd.mdb> \
      --snapshot <snapshot.json> --schema <schema.json> --workdir <dir> --name Dalby \
      [--stages articles,class_creation,...] [--limit N]

``--schema`` is the JSON written by the read-only schema dump (table, pk, indexes, fks).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from copy import copy
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.application_context import ApplicationContext  # noqa: E402
from services.mdb_service import MDBService  # noqa: E402
from services.snapshot_serialization import snapshot_from_dict  # noqa: E402

STAGES = ["articles", "class_creation", "properties_values", "text", "relations"]


# ---------------------------------------------------------------- safety helpers

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_isolated(source: Path, dest: Path) -> None:
    s, d = source.resolve(), dest.resolve()
    if s == d:
        raise SystemExit("REFUSED: source and destination are the same file.")
    if str(d).lower().startswith(str(ROOT).lower()):
        raise SystemExit("REFUSED: test copies must live outside the repository.")
    if str(d.parent).lower().startswith(str(s.parent).lower()):
        raise SystemExit("REFUSED: test copy is inside the source workspace folder.")


# ---------------------------------------------------------------- MDB state capture

class FailingMDB(MDBService):
    """Real bridge; when armed, a bad op is appended to every transactional write."""

    armed = False

    def execute_batch(self, mdb_path, ops, transaction=False):
        if self.armed and transaction and any(o["op"] in ("insert", "update") for o in ops):
            ops = [*ops, {"op": "insert", "table": "tCOMd_DoesNotExist", "rows": [{"x": 1}]}]
        return super().execute_batch(mdb_path, ops, transaction=transaction)


def _row_hash(row: dict) -> str:
    return hashlib.sha1(json.dumps(row, sort_keys=True, default=str).encode("utf-8")).hexdigest()


class Schema:
    def __init__(self, path: Path):
        tables = json.loads(path.read_text(encoding="utf-8-sig"))
        self.tables = {t["table"]: t for t in tables}
        self.pk = {n: (t["pk"] if isinstance(t["pk"], list) else [t["pk"]]) for n, t in self.tables.items()}
        self.fks = []  # (child table, child col, parent table, parent col)
        for name, t in self.tables.items():
            fks = t["fks"] if isinstance(t["fks"], list) else [t["fks"]]
            for fk in fks:
                if not fk:
                    continue
                _, rest = fk.split(": ", 1)
                child, parent = rest.split(" -> ")
                ptable, pcol = parent.split(".", 1)
                self.fks.append((name, child, ptable, pcol))
        self.unique = {}  # table -> {index name: [cols]}
        for name, t in self.tables.items():
            groups: dict[str, list[str]] = {}
            idx = t["indexes"] if isinstance(t["indexes"], list) else [t["indexes"]]
            for entry in idx:
                if entry and entry.endswith(" UNIQUE"):
                    iname, col = entry[:-len(" UNIQUE")].rsplit("(", 1)
                    groups.setdefault(iname, []).append(col.rstrip(")"))
            if groups:
                self.unique[name] = groups


def capture(db: MDBService, mdb: Path, schema: Schema) -> dict:
    """Full read-back of every table: {table: {pk tuple: row hash}} plus raw rows."""
    data = db.read_tables(mdb, {t: f"SELECT * FROM [{t}]" for t in schema.tables})
    state = {}
    for table, rows in data.items():
        pk = schema.pk.get(table) or []
        keyed = {}
        for i, row in enumerate(rows):
            key = tuple(row.get(c) for c in pk) if pk else (i,)
            keyed[key] = _row_hash(row)
        state[table] = {"rows": rows, "keyed": keyed}
    return state


def delta(before: dict, after: dict) -> dict:
    out = {}
    for table in after:
        b, a = before[table]["keyed"], after[table]["keyed"]
        added = [k for k in a if k not in b]
        removed = [k for k in b if k not in a]
        changed = [k for k in a if k in b and a[k] != b[k]]
        if added or removed or changed:
            out[table] = {"added": len(added), "removed": len(removed), "changed": len(changed)}
    return out


def integrity(state: dict, schema: Schema) -> dict:
    """FK orphans and unique-index violations over the whole captured MDB."""
    orphans, dups = {}, {}
    for child, ccol, parent, pcol in schema.fks:
        if child not in state or parent not in state:
            continue
        parents = {r.get(pcol) for r in state[parent]["rows"]}
        bad = [r.get(ccol) for r in state[child]["rows"]
               if r.get(ccol) not in (None, "") and r.get(ccol) not in parents]
        if bad:
            orphans[f"{child}.{ccol}->{parent}.{pcol}"] = len(bad)
    for table, groups in schema.unique.items():
        for iname, cols in groups.items():
            seen, dup = set(), 0
            for r in state[table]["rows"]:
                tup = tuple(r.get(c) for c in cols)
                if any(v is None for v in tup):
                    continue
                if tup in seen:
                    dup += 1
                seen.add(tup)
            if dup:
                dups[f"{table}.{iname}"] = dup
    return {"fk_orphans": orphans, "unique_violations": dups}


def invariants(base: dict, final: dict, selected_ids: set) -> dict:
    """Whole-run safety checks against the baseline MDB (all must be empty / True for a pass)."""
    def keyed(state, table, pk):
        return {r.get(pk): r for r in state[table]["rows"]}

    a0, a1 = keyed(base, "tCOMd_Article", "com_ArticleID"), keyed(final, "tCOMd_Article", "com_ArticleID")
    changed = {k: sorted(c for c in a1[k] if a1[k].get(c) != a0[k].get(c)) for k in a0 if k in a1 and a1[k] != a0[k]}
    s0, s1 = keyed(base, "tCOMd_CodeScheme", "com_CodeSchemeID"), keyed(final, "tCOMd_CodeScheme", "com_CodeSchemeID")
    users: dict = {}
    for row in a1.values():
        users.setdefault(row.get("com_CodeSchemeID"), set()).add(row.get("com_ArticleID"))
    changed_schemes = [k for k in s0 if k in s1 and s0[k] != s1[k]]
    columns: dict = {}
    for cols in changed.values():
        for c in cols:
            columns[c] = columns.get(c, 0) + 1
    names = {k: r.get("com_CodeSchemeName") for k, r in s1.items()}
    return {
        "selected_articles": len(selected_ids),
        "unselected_articles_changed": sorted(k for k in changed if k not in selected_ids),
        "articles_removed": sorted(k for k in a0 if k not in a1),
        "article_columns_changed": columns,
        "articles_with_relobj_link_changed": sorted(k for k, cols in changed.items() if "com_RelObjID" in cols),
        "articles_reassigned_to_scheme": {k: names.get(a1[k].get("com_CodeSchemeID"))
                                          for k, cols in changed.items() if "com_CodeSchemeID" in cols},
        "schemes_removed": sorted(k for k in s0 if k not in s1),
        "schemes_added": sorted(names[k] for k in s1 if k not in s0),
        "existing_schemes_modified": [names[k] for k in changed_schemes],
        "modified_schemes_have_unselected_users": [
            names[k] for k in changed_schemes if users.get(k, set()) - selected_ids],
        "modified_schemes_only_extended": all(
            str(s1[k].get("com_CodeSchemeBody") or "").startswith(str(s0[k].get("com_CodeSchemeBody") or ""))
            for k in changed_schemes),
        "unmodified_existing_schemes": len([k for k in s0 if k in s1 and k not in changed_schemes]),
    }


def compact(result: dict) -> dict:
    """Scalars and small count dicts of a stage result; lists are reduced to their length."""
    keep = {}
    for k, v in (result or {}).items():
        if isinstance(v, (bool, int, float, str)):
            keep[k] = v if not isinstance(v, str) else v[:300]
        elif isinstance(v, dict) and len(v) <= 40 and all(isinstance(x, (bool, int, float, str)) for x in v.values()):
            keep[k] = v
        elif isinstance(v, (list, tuple, set)):
            keep[k + "_n"] = len(v)
            if k == "warnings":
                keep[k] = [str(w)[:200] for w in list(v)[:5]]
    return keep


# ---------------------------------------------------------------- the run

def prepare_snapshot(ctx, snapshot):
    ctx.snapshot_manager.load_snapshot(snapshot)
    ctx.engineering_reduction_service.materialize_article_sets(snapshot)
    ctx.engineering_initialization_service.initialize(snapshot)
    ctx.engineering_member_service.auto_reduce(snapshot)
    category = (snapshot.product.category if snapshot.product else "") or "Class"
    ctx.engineering_class_service.ensure_standard_classes(snapshot, category)
    ctx.engineering_class_service.commit_config_codes(snapshot)


class PricingStage:
    """Price export of live-PDM-computed records into the session MDB (all-or-selected by article code)."""

    def __init__(self, ctx, snapshot, targets: dict[str, str]):
        self.ctx, self.snapshot, self.targets = ctx, snapshot, targets
        codes = sorted({r.article_code for r in snapshot.price_records if not r.is_global and r.article_code})
        self.first_codes = set(codes[: max(1, len(codes) // 2)])

    def export_to_session(self, snapshot, session, selected_article_ids=None, dry_run=False):
        from services.price_mdb_export_service import PriceMdbExportService
        everything = selected_article_ids is not None and len(selected_article_ids) > self.first_n
        subset = copy(self.snapshot)
        subset.price_records = [r for r in self.snapshot.price_records
                                if everything or (not r.is_global and r.article_code in self.first_codes)]
        return PriceMdbExportService(self.ctx).export(
            subset, session.mdb_path, dry_run=dry_run, list_targets=self.targets)

    first_n = 0  # set by main: size of the first batch of article ids


class VarcondStage:
    """Writer path for generated VARCOND price relations (real Dalby body convention).

    The relation objects are supplied by this harness; BOM-based *generation* needs a
    super-product BOM that neither Dalby nor Lino has, and is NOT exercised here.
    """

    def __init__(self, ctx, snapshot, objects_first, objects_all):
        self.ctx, self.snapshot = ctx, snapshot
        self.first, self.all = objects_first, objects_all
        self.first_n = 0

    def export_to_session(self, snapshot, session, selected_article_ids=None, dry_run=False):
        from services.pricing_relation_service import prepare_price_relation_export
        from services.relation_mdb_export_service import RelationMdbExportService
        everything = selected_article_ids is not None and len(selected_article_ids) > self.first_n
        generated = list(self.all if everything else self.first)
        export_snapshot = copy(self.snapshot)
        prepare_price_relation_export(self.ctx, export_snapshot, generated)
        return RelationMdbExportService(self.ctx).export_to_session(
            export_snapshot, session, selected_article_ids=selected_article_ids,
            dry_run=dry_run, workflow="pricing_relations")


def stage_runner(ctx, name: str):
    if name == "articles":
        from services.article_mdb_export_service import ArticleMdbExportService as S
    elif name == "class_creation":
        from services.class_creation_mdb_export_service import ClassCreationMdbExportService as S
    elif name == "properties_values":
        from services.properties_values_mdb_export_service import PropertiesValuesMdbExportService as S
    elif name == "text":
        from services.text_mdb_export_service import TextMdbExportService as S
    elif name == "relations":
        from services.relation_mdb_export_service import RelationMdbExportService as S
    else:
        raise SystemExit(f"unknown stage {name}")
    return S(ctx)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--stages", default=",".join(STAGES))
    ap.add_argument("--limit", type=int, default=0, help="use only the first N articles")
    ap.add_argument("--select-codes", default="",
                    help="comma-separated BASE article codes for the full selection (overrides --limit)")
    ap.add_argument("--first-codes", default="",
                    help="comma-separated BASE codes for the first batch (default: same as --select-codes)")
    ap.add_argument("--template-kind", default="hm_seating")
    ap.add_argument("--price-date", default=time.strftime("%d-%b-%Y"), help="PDM computation date, dd-MMM-yyyy")
    ap.add_argument("--price-valid-from", default="2026-04-06")
    ap.add_argument("--price-targets", default="EUR=EURO_2026,GBP=GBP_2026",
                    help="currency=price list name,... (must exist in the MDB)")
    ap.add_argument("--force-unattached", action="store_true",
                    help="attach, then run as a template-initialized session (attached_existing=False): "
                         "reproduces the pre-preservation overwrite behaviour for an A/B comparison")
    ap.add_argument("--unattached-stages", default="",
                    help="comma-separated stages run as a template-initialized session (e.g. class_creation, "
                         "to build the classes that production-class identity would otherwise stop)")
    ap.add_argument("--init-template", default="",
                    help="path of a real template MDB: validate initialize() on a copy instead of attach")
    args = ap.parse_args()

    init_mode = bool(args.init_template)
    source = Path(args.init_template if init_mode else args.source)
    work = Path(args.workdir) / args.name
    # attach mode: the copy IS the export MDB; init mode: the copy is the template that
    # initialize() copies again into <work>/out/ (the export MDB it creates).
    dest = work / ("template_copy.mdb" if init_mode else "pcr_data_com_ocd.mdb")
    work.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    shutil.rmtree(work / "out", ignore_errors=True)
    assert_isolated(source, dest)
    src_hash = sha256(source)
    shutil.copyfile(source, dest)
    assert sha256(dest) == src_hash, "copy differs from source"
    print(f"source {source}\ncopy   {dest}\nsha256 {src_hash}", flush=True)

    schema = Schema(Path(args.schema))
    ctx = ApplicationContext()
    ctx._services[MDBService] = FailingMDB(ctx)  # same real bridge; can inject a transactional fault
    sessions = ctx.mdb_export_session_service
    sessions.store_dir = work / "sessions"
    shutil.rmtree(sessions.store_dir, ignore_errors=True)
    db = ctx.mdb_service
    if not db.is_available():
        print("SKIP: 32-bit PowerShell / ACE bridge unavailable")
        return 2

    snapshot = snapshot_from_dict(json.loads(Path(args.snapshot).read_text(encoding="utf-8")))
    prepare_snapshot(ctx, snapshot)
    articles = list(snapshot.articles)
    if args.limit:
        articles = articles[: args.limit]
    all_ids = {str(a.id) for a in articles}
    half = {str(a.id) for a in articles[: max(1, len(articles) // 2)]}
    if args.select_codes:
        # Scenario selection by BASE article code (e.g. one article of a shared scheme).
        entries = ctx.xocd_export_service.base_code_entries(snapshot)
        by_code: dict[str, set[str]] = {}
        for article_id, base_code in entries:
            by_code.setdefault(str(base_code), set()).add(str(article_id))
        wanted = [c.strip() for c in args.select_codes.split(",") if c.strip()]
        first = [c.strip() for c in (args.first_codes or args.select_codes).split(",") if c.strip()]
        missing = [c for c in wanted + first if c not in by_code]
        if missing:
            raise SystemExit(f"base article code(s) not in the snapshot: {missing}")
        all_ids = set().union(*(by_code[c] for c in wanted))
        half = set().union(*(by_code[c] for c in first))
    selected_base_codes = None
    if args.select_codes:
        selected_base_codes = set(wanted)
    print(f"snapshot: {len(snapshot.articles)} articles, using {len(all_ids)} (first batch {len(half)})", flush=True)

    evidence = {"name": args.name, "source": str(source), "copy": str(dest), "source_sha256": src_hash,
                "articles_used": len(all_ids), "first_batch": len(half), "stages": {}}
    t0 = time.time()
    state = capture(db, dest, schema)
    base_state = state
    evidence["baseline"] = {"rows": {t: len(s["rows"]) for t, s in state.items()},
                            "integrity": integrity(state, schema)}
    print(f"baseline captured {time.time()-t0:.0f}s; integrity {evidence['baseline']['integrity']}", flush=True)

    # --- session attachment (populated workspace) or initialization (clean template)
    if init_mode:
        from services import ocd_export_service as _ocd
        template_state = state
        try:
            session = sessions.initialize(snapshot, work / "out", args.template_kind, template_path=dest)
        except Exception as exc:  # noqa: BLE001 - recorded as the finding
            evidence["initialize"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                                      "out_exists": any((work / "out").glob("*")) if (work / "out").exists() else False,
                                      "session_saved": sessions.load(snapshot) is not None}
            evidence["template_rows"] = evidence["baseline"]["rows"]
            (work / "evidence.json").write_text(json.dumps(evidence, indent=1, default=str), encoding="utf-8")
            print("initialize FAILED:", evidence["initialize"], flush=True)
            return 0
        dest = Path(session.mdb_path)
        after = capture(db, dest, schema)
        product_tables = set(_ocd._PRODUCT_TABLES)
        reference = {t for t in after if t not in product_tables}
        ref_changes = {t: d for t, d in delta(template_state, after).items() if t in reference}
        evidence["initialize"] = {
            "ok": True, "out_mdb": str(dest), "package_id": session.package_id,
            "comgroup_id": session.comgroup_id, "program_code": session.program_code,
            "product_tables_remaining": {t: len(after[t]["rows"]) for t in product_tables if after[t]["rows"]},
            "product_tables_cleared": {t: len(template_state[t]["rows"]) for t in product_tables
                                       if template_state[t]["rows"]},
            "reference_tables_changed": ref_changes,
            "reference_row_counts": {t: len(after[t]["rows"]) for t in sorted(reference) if after[t]["rows"]},
            "integrity": integrity(after, schema),
            "template_unmodified_after_init": sha256(dest.parent.parent / "template_copy.mdb") == src_hash,
        }
        # the initialized MDB is the new baseline for the incremental stages
        base_state = after
        state = after
        evidence["attach"] = {"recovered_after_restart": None}
        fresh = type(sessions)(ctx)
        fresh.store_dir = sessions.store_dir
        rec_session = fresh.get_active(snapshot)
        evidence["initialize"]["session_recovered_after_restart"] = (
            rec_session is not None and rec_session.mdb_path == session.mdb_path)
        print("initialize:", json.dumps(evidence["initialize"], indent=1, default=str), flush=True)
    else:
        session = sessions.attach_existing(snapshot, dest, args.template_kind)
        if args.force_unattached:
            session.attached_existing = False
            sessions.save(session)
        after = capture(db, dest, schema)
        evidence["attach"] = {"package_id": session.package_id, "comgroup_id": session.comgroup_id,
                              "program_code": session.program_code, "mdb_writes": delta(state, after),
                              "prototype_tables": sorted(session.prototypes)}
        state = after
    # session persistence / recovery
    fresh = type(sessions)(ctx)
    fresh.store_dir = sessions.store_dir
    recovered = fresh.get_active(snapshot)
    evidence["attach"]["recovered_after_restart"] = recovered is not None and recovered.mdb_path == session.mdb_path
    print("attach:", evidence["attach"], flush=True)

    unattached_stages = {x.strip() for x in args.unattached_stages.split(",") if x.strip()}
    for name in [s for s in args.stages.split(",") if s]:
        rec = {}
        t = time.time()
        if name == "pricing":
            from services.pricing_service import PriceParams, PricingService
            params = PriceParams(currency="", mydate=args.price_date, site_id=1, valid_from=args.price_valid_from,
                                 valid_to="", program_code=session.program_code)
            computed = PricingService(ctx).compute(params, snapshot)
            rec["compute"] = {"records": len(snapshot.price_records),
                              "global": sum(1 for r in snapshot.price_records if r.is_global),
                              "warnings": list(computed.warnings)[:5], "unresolved": len(computed.unresolved),
                              "seconds": round(time.time() - t, 1)}
            print("pricing compute:", rec["compute"], flush=True)
            if not snapshot.price_records:
                rec["skipped"] = "no price records computed"
                evidence["stages"][name] = rec
                continue
            targets = dict(kv.split("=", 1) for kv in args.price_targets.split(",") if kv)
            service = PricingStage(ctx, snapshot, targets)
            service.first_n = len(half)
        elif name == "varcond":
            xocd = ctx.xocd_export_service
            from models.relation_object import RelationObject
            existing = {r["com_RelationName"]: r for r in state["tCOMd_Relation"]["rows"]}
            codes = sorted(set(xocd._base_codes(snapshot)))
            have = [c for c in codes if f"PA_PRICING_{c}" in existing]
            new = [c for c in codes if f"PA_PRICING_{c}" not in existing]

            def obj(code, body):
                return RelationObject(name=f"P_PRICING_{code}", relation_name=f"PA_PRICING_{code}", type_code="3",
                                      domain="P", order=100, body=body, article_codes=[code])
            objs_first, objs_all = [], []
            if len(have) >= 2:
                same = obj(have[0], existing[f"PA_PRICING_{have[0]}"]["com_RelationBody"])
                changed = obj(have[1], existing[f"PA_PRICING_{have[1]}"]["com_RelationBody"] + "\r\n* harness body change")
                objs_first = [changed]
                objs_all = [same, changed]
                rec["inputs"] = {"identical_to_existing": have[0], "changed_existing": have[1]}
            if new:
                objs_all.append(obj(new[0], "$VARCOND = '" + new[0] + "-1'"))
                rec.setdefault("inputs", {})["new_relation_for"] = new[0]
            if not objs_all:
                rec["skipped"] = "no PA_PRICING relations to exercise"
                evidence["stages"][name] = rec
                continue
            service = VarcondStage(ctx, snapshot, objs_first or objs_all[:1], objs_all)
            service.first_n = len(half)
        else:
            service = stage_runner(ctx, name)

        def run(ids, dry=False):
            s = sessions.get_active(snapshot)
            if name in unattached_stages:
                s.attached_existing = False
            elif not args.force_unattached and not init_mode:
                s.attached_existing = True
            kw = {"dry_run": dry}
            return service.export_to_session(snapshot, s, selected_article_ids=ids, **kw)

        before = state
        # 1 dry run must not write
        rec["dry_run"] = compact(run(all_ids, dry=True))
        s1 = capture(db, dest, schema)
        rec["dry_run_writes"] = delta(before, s1)
        # 2 injected failure must roll back completely
        db.armed = True
        failed = run(all_ids)
        db.armed = False
        s2 = capture(db, dest, schema)
        rec["rollback"] = {"result_ok": bool(failed.get("ok")), "error": str(failed.get("error", ""))[:160],
                           "writes_after_failure": delta(before, s2)}
        # 3 first batch, 4 full selection (incremental add), 5 repeat (idempotent)
        rec["first_batch"] = compact(run(half))
        s3 = capture(db, dest, schema)
        rec["first_batch_delta"] = delta(before, s3)
        rec["full_selection"] = compact(run(all_ids))
        s4 = capture(db, dest, schema)
        rec["full_selection_delta"] = delta(s3, s4)
        # rows that existed before this stage and were modified/removed by it
        rec["preexisting_modified"] = {
            tb: {"changed": d["changed"], "removed": d["removed"]}
            for tb, d in delta(before, s4).items() if d["changed"] or d["removed"]}
        rec["repeat"] = compact(run(all_ids))
        s5 = capture(db, dest, schema)
        rec["repeat_delta"] = delta(s4, s5)
        rec["integrity"] = integrity(s5, schema)
        rec["seconds"] = round(time.time() - t, 1)
        evidence["stages"][name] = rec
        state = s5
        print(f"== {name} ({rec['seconds']}s)\n" + json.dumps(rec, indent=1, default=str), flush=True)

    evidence["final_delta_vs_baseline"] = delta(base_state, state)
    evidence["final_integrity"] = integrity(state, schema)
    final_session = sessions.get_active(snapshot)
    selected_codes = selected_base_codes or set(final_session.article_map)
    selected_mdb_ids = {entry["mdb_id"] for code, entry in final_session.article_map.items()
                        if code in selected_codes and entry.get("mdb_id") is not None}
    evidence["invariants"] = invariants(base_state, state, selected_mdb_ids)
    print("invariants:", json.dumps(evidence["invariants"], indent=1, default=str), flush=True)
    after_hash = sha256(source)
    evidence["source_sha256_after"] = after_hash
    evidence["source_unchanged"] = after_hash == src_hash
    out = work / "evidence.json"
    out.write_text(json.dumps(evidence, indent=1, default=str), encoding="utf-8")
    print(f"source unchanged: {evidence['source_unchanged']}; evidence -> {out}")
    return 0 if evidence["source_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
