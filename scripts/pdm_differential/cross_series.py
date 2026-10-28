"""Cross-series PDM-versus-Workbench pricing parity run (Aeron, Always, Nevi, Layout Studio).

Unlike ``differential.py`` (which drives the repository fetch methods directly for a fixed Layout_Studio
fixture) this runner exercises the *production* Maintenance computation: the product is loaded through
``PDMService.load_product`` into a real snapshot and priced with ``PricingService.compute`` using the same
``PriceParams`` the Pricing page builds (``program_code`` = ``snapshot.generation_program``). The result is
exported with ``PriceMdbExportService`` (dry-run plan, then the approved write) into a disposable MDB copy,
and compared with the compiled legacy PDM run on a second copy of the same starting MDB.

Safety: only copies of the starting MDB are ever written. ``--source-root`` holds per-series copies
``<root>/<Series>/pcr_data_com_ocd.mdb``; never point it at a live workspace. SQL Server is only read.
``PDMService.save_family_snapshot`` is stubbed so loading a product never rewrites ``cache/pdm_snapshots``.

    python scripts/pdm_differential/cross_series.py --source-root <dir> --pdm-dir <PDM bin copy> \
        --work <scratch> --out raw.json [--scenarios X1,X2]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import differential as d  # noqa: E402

from services.pdm_service import PDMService  # noqa: E402
from services.pricing_service import PriceParams, PricingService  # noqa: E402

# Series fixtures: workspace folder, package id, program code and the price lists (label, id) per currency,
# all read from each series' own starting MDB (tCOMd_Package / tCOMd_PriceList2), not assumed.
SERIES: dict[str, dict[str, Any]] = {
    "Aeron": {"workspace": "Aeron", "package": 369, "program": "aeron",
              "lists": {"GBP": ("GBP_2026", 30), "EUR": ("EURO_2026", 29)}},
    "Always": {"workspace": "Always", "package": 375, "program": "always",
               "lists": {"GBP": ("GBP_2026", 30), "EUR": ("EURO_2026", 29)}},
    "Nevi": {"workspace": "Nevi_enhanced", "package": 1, "program": "nevi_enhanced",
             "lists": {"GBP": ("GBP_2026_2", 35), "EUR": ("EURO_2026_2", 34)}},
    "Layout": {"workspace": "Layout_Studio", "package": 375, "program": "layout_studio",
               "lists": {"GBP": ("GBP_2026_2", 22), "EUR": ("EURO_2026_2", 21)}},
    # Reference series whose real MDB rows use the Fabric Type -> Colour target (28=) form.
    "Revive": {"workspace": "Revive", "package": 240, "program": "revive",
               "lists": {"GBP": ("GBP_2026_2", 27), "EUR": ("EURO_2026_2", 26)}},
}

# ``generation_programs``: values of ``snapshot.generation_program`` to run through production compute.
# "" is the Pricing page default when the Review page never set a program; the series program is the
# explicit alternative. PDM is run once, always with the series program (what the PDM buttons pass).
SCENARIOS: dict[str, dict[str, Any]] = {}


def _add(name, series, find_article, catalogue, title, generation_programs=("", None), pdm_program=None,
         perturb=(), placeholders_first=False):
    SCENARIOS[name] = {"pdm_program": pdm_program, "placeholders_first": placeholders_first, "perturb": tuple(perturb), "series": series, "find_article": find_article, "catalogue": catalogue, "title": title,
                       "generation_programs": generation_programs}


def _load_product(ctx, article: str, catalogue: int):
    svc = ctx.pdm_service
    matches = [p for p in svc.search_products_by_article(article, 50) if p.catalogue_id == str(catalogue)]
    if not matches:
        raise RuntimeError(f"no product for article {article} in catalogue {catalogue}")
    result = svc.load_product(matches[0])
    if not result.ok or result.snapshot is None:
        raise RuntimeError(f"load_product failed: {result.message}")
    return result.snapshot


def _record_dict(r) -> dict[str, Any]:
    return {"global": r.is_global, "article": r.article_code, "variant_condition": r.variant_condition,
            "pdm_lookup_code": r.pdm_lookup_code, "source_item": r.source_item, "level": r.level,
            "value": r.value, "currency": r.currency, "valid_from": r.valid_from, "product_code": r.product_code}


def _apply_perturb(m, path: Path, fx: dict[str, Any], spec: dict[str, Any]) -> None:
    """Identical stale values on every copy so each side has real existing rows to update.

    ``perturb`` entries are ``("article", article_code, variant_condition)`` or ``("global", "", variant)``;
    only the GBP target list of the series is touched.
    """
    label, list_id = fx["lists"]["GBP"]
    ops = []
    for kind, article, variant in spec.get("perturb", ()):
        if kind == "article":
            ids = d._price_ids(m, path, label, article, variant)
            ops += [{"op": "update", "table": "tCOMd_Price", "set": {"com_PriceValue": 7.0},
                     "where": {"com_PriceID": i}} for i in ids]
        else:
            ids = d._global_ids(m, path, label, variant)
            ops += [{"op": "update", "table": "tCOMd_GlobalPrice", "set": {"com_PriceValue": 7.0},
                     "where": {"com_GlobalPriceID": i}} for i in ids]
    if ops:
        m.write(path, ops)


def _copy_start(source_mdb: Path, dest: Path) -> Path:
    shutil.rmtree(dest.parent if dest.name.endswith(".mdb") else dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_mdb, dest)
    return dest


def _variant_status(export: dict[str, Any], diff: dict[str, Any], unresolved, legacy_unresolved: int = 0) -> str:
    """PASS only when the export really ran, both end states are identical and legacy resolved every item.

    A blocked or failed export leaves the MDB untouched, so an empty diff would be vacuous: INCOMPLETE.
    Items the compiled PDM itself reported as unmatched (noPDMprice/notfound) were never priced by legacy,
    so an identical end state proves nothing about them: INCOMPLETE as well.
    """
    if not export.get("ok") or legacy_unresolved:
        return "INCOMPLETE"
    clean = (not diff["only_in_pdm_result"] and not diff["only_in_pricing_result"]
             and diff["lists_equal"] and diff["texts_equal"])
    return "PASS" if clean and not unresolved else "FAIL"


def run_scenario(name: str, spec: dict[str, Any], ctx, source_root: Path, pdm_dir: Path, work: Path) -> dict[str, Any]:
    fx = SERIES[spec["series"]]
    ccy = "GBP"
    label, list_id = fx["lists"][ccy]
    start = source_root / spec["series"] / "pcr_data_com_ocd.mdb"
    m = d.Mdb(ctx)
    glob_lists = tuple(i for _, i in fx["lists"].values())

    snapshot = _load_product(ctx, spec["find_article"], spec["catalogue"])
    svc = PricingService(ctx)
    items, super_codes = svc._price_plan(snapshot)
    article_items = [i for i in items if i not in super_codes]
    global_items = [i for i in items if i in super_codes]
    report: dict[str, Any] = {
        "scenario": name, "title": spec["title"], "series": spec["series"],
        "inputs": {"product": snapshot.product.code, "product_id": snapshot.product.id,
                   "catalogue": spec["catalogue"], "workspace": fx["workspace"], "package": fx["package"],
                   "program": fx["program"], "site": 1, "currency": ccy, "price_list": label,
                   "price_list_id": list_id, "date": d.VALID_FROM, "mydate": d.MYDATE,
                   "is_super_product": bool(snapshot.product.is_super_product),
                   "article_items": article_items, "global_items": global_items,
                   "snapshot_articles": len(snapshot.articles)}}

    # ---- compiled legacy PDM on its own copy --------------------------------------------------------
    pdm_dir_ = work / f"{name}_pdm"
    a_mdb = _copy_start(start, pdm_dir_ / "root" / "WS" / fx["workspace"] / "pcr_data_com_ocd.mdb")
    _apply_perturb(m, a_mdb, fx, spec)
    before = m.state(a_mdb, glob_lists)
    report["inputs"]["perturbed_rows"] = [list(x) for x in spec.get("perturb", ())]
    steps = []
    if article_items:
        steps.append(("article", article_items, 1))
    if global_items and spec.get("placeholders_first"):
        # PDM's two-step new-global workflow: placeholder rows first, then values.
        steps.append(("placeholders", global_items, spec["catalogue"]))
    if global_items:
        steps.append(("global", global_items, spec["catalogue"]))
    pdm_out = []
    for mode, its, cat in steps:
        pdm_out.append(d.run_pdm(work, pdm_dir, f"{name}_pdm", mode, its, ccy, list_id, label, catalogue=cat,
                                 program_code=(spec.get("pdm_program") or fx["program"]), workspace=fx["workspace"],
                                 package_id=fx["package"]))
        if not pdm_out[-1].get("executed"):
            break
    report["pdm"] = pdm_out
    legacy_unresolved = sum(len(o.get("noPDMprice") or []) + len(o.get("notfound") or []) for o in pdm_out)
    if not all(o.get("executed") for o in pdm_out):
        report["status"] = "NOT RUN"
        report["reason"] = "compiled PDM did not execute (see pdm[].returncode/error/dialogs)"
        return report
    after_a = m.state(a_mdb, glob_lists)

    # ---- production compute + export, once per generation_program value ------------------------------
    report["workbench"] = {}
    for gp in spec["generation_programs"]:
        gp_value = fx["program"] if gp is None else gp
        tag = f"{name}_wb_{gp_value or 'blank'}"
        snap = _load_product(ctx, spec["find_article"], spec["catalogue"])
        snap.generation_program = gp_value
        params = PriceParams(currency="", mydate=d.MYDATE, site_id=1, valid_from=d.VALID_FROM, valid_to="",
                             program_code=gp_value)  # == ui/pages/pricing_page.py::_params
        try:
            computed = svc.compute(params, snap)
        except Exception as exc:  # a PDMQueryError is a result, not a harness failure
            report["workbench"][gp_value or "blank"] = {"compute_error": f"{type(exc).__name__}: {exc}"}
            continue
        records = [r for r in computed.records if r.currency == ccy]
        b_mdb = _copy_start(start, work / tag / "pcr_data_com_ocd.mdb")
        _apply_perturb(m, b_mdb, fx, spec)
        export = d.run_pricing(ctx, b_mdb, records, ccy, lists=fx["lists"])
        after_b = m.state(b_mdb, glob_lists)
        diff = d.diff_states(before, after_a, after_b)
        report["workbench"][gp_value or "blank"] = {
            "generation_program": gp_value, "records": [_record_dict(r) for r in records],
            "unresolved": computed.unresolved, "export": export, "differences": diff,
            "legacy_unresolved": legacy_unresolved,
            "status": _variant_status(export, diff, computed.unresolved, legacy_unresolved)}
    report["pdm_result_rows"] = {
        "added": d.diff_states(before, after_a, after_a)["pdm_changed"]["added"],
        "removed": d.diff_states(before, after_a, after_a)["pdm_changed"]["removed"]}
    variants = [v.get("status", "INCOMPLETE") for v in report["workbench"].values()]
    report["status"] = "COMPARED"
    report["variant_statuses"] = {k: v.get("status", "INCOMPLETE") for k, v in report["workbench"].items()}
    report["all_variants_pass"] = bool(variants) and all(v == "PASS" for v in variants)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", required=True)
    ap.add_argument("--pdm-dir", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scenarios", default="")
    args = ap.parse_args()
    PDMService.save_family_snapshot = lambda *a, **k: None  # never rewrite cache/pdm_snapshots
    from core.application_context import ApplicationContext
    ctx = ApplicationContext()
    names = [s for s in args.scenarios.split(",") if s] or list(SCENARIOS)
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    out = Path(args.out)
    results = json.loads(out.read_text(encoding="utf-8"))["scenarios"] if out.is_file() else []
    for n in names:
        try:
            res = run_scenario(n, SCENARIOS[n], ctx, Path(args.source_root), Path(args.pdm_dir), work)
        except Exception as exc:  # never lose the other scenarios' evidence
            import traceback
            res = {"scenario": n, "status": "CRASHED", "error": f"{type(exc).__name__}: {exc}",
                   "traceback": traceback.format_exc()[-2000:]}
        results = [r for r in results if r["scenario"] != n] + [res]
        out.write_text(json.dumps({"scenarios": results}, indent=1, default=str), encoding="utf-8")
        print(n, res.get("status"), flush=True)


# ---- scenario catalogue (articles verified in live PDM and in each series' MDB; see the report) --------
_add("X1_aeron_article", "Aeron", "AER1A11PW", 518,
     "Aeron ordinary article with base price and option increments (no super products in this series)")
_add("X2_always_article", "Always", "NOALE181", 381,
     "Always ordinary article with base price and option increments")
_add("X3_nevi_screen_global", "Nevi", "DWE3SCRNNS.105516F", 764,
     "Nevi screen super product: global base + Fabric Type surcharges (component DWE3VNNS.105516F)")
_add("X4_layout_screen_global", "Layout", "GESCRNNU.105508F", 660,
     "Layout Studio screen super product: global base + Fabric Type surcharges (component GESNNU.105508F)")
_add("X5_layout_article", "Layout", "GEWQ.", 660,
     "Layout Studio ordinary article with option increments")
_add("X7_revive_screen_global", "Revive", "RY3SCRNNB.105512F", 658,
     "Revive (reference) screen super product: legacy writes Fabric Type -> Colour 28= rows")
_add("X8_layout_screen_pdm_as_revive", "Layout", "GESCRNNU.105508F", 660,
     "DIAGNOSTIC: compiled PDM run on the Layout screen with programCode=revive (does legacy route by program?)",
     generation_programs=(), pdm_program="revive")
_add("X2p_always_article_stale", "Always", "NOALE181", 381,
     "Always article with three stale values (base '1', '1 3344=622', '1 6530=R39') forced into both copies",
     perturb=(("article", "NOALE18", "1"), ("article", "NOALE18", "1 3344=622"),
              ("article", "NOALE18", "1 6530=R39")))
_add("X5p_layout_article_stale", "Layout", "GEWQ.", 660,
     "Layout Studio article with stale base '.' and option-increment '. 3827=DB3' values forced into both copies",
     perturb=(("article", "GEWQ", "."), ("article", "GEWQ", ". 3827=DB3")))
_add("X6_nevi_article", "Nevi", "DWE3WLES.", 764, "Nevi ordinary article with base price")

_add("X4p_layout_screen_global_stale", "Layout", "GESCRNNU.105508F", 660,
     "Layout screen global with stale base and two Fabric Type surcharge rows forced into both copies",
     generation_programs=(None,),
     perturb=(("global", "", "GESNNU.105508F"), ("global", "", "GESNNU.105508F 8=1FD"),
              ("global", "", "GESNNU.105508F 8=TI")))
_add("X3b_nevi_screen_placeholders_then_global", "Nevi", "DWE3SCRNNS.105516F", 764,
     "Nevi screen with PDM's placeholders step before the global step: does legacy create the 8=T2RE rows?",
     generation_programs=("nevi_enhanced",), placeholders_first=True)
_add("X6p_nevi_article_stale", "Nevi", "DWE3WLES.", 764,
     "Nevi article with a stale base value forced into both copies",
     perturb=(("article", "DWE3WLE", "S."),))

if __name__ == "__main__":
    main()
