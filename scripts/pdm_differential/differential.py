"""PDM-versus-Pricing differential on isolated MDB copies.

For each scenario: two byte-identical copies of a *backup* MDB get the same setup edits; the REAL compiled PDM
(``run_pdm_price_update.ps1`` -> ``UpdatePriceThread.execThread``) runs on copy A, the Pricing export runs on
copy B with the same items / currency / date / price list; both result states are read back with independent
queries and compared after removing only autonumber ids and row order.

usage (reads SQL Server only; writes only the two copies under --work):
    python scripts/pdm_differential/differential.py --backup <pcr_data_com_ocd.mdb copy> --pdm-dir <dir with
        PDMMaintenance.exe + dlls (a COPY)> --work <scratch dir> --out <report.json> [--scenarios S1,S2]
Never pass the live MDB: pass a backup copy.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.application_context import ApplicationContext  # noqa: E402
from models.price_record import PriceRecord  # noqa: E402
from models.snapshot import Snapshot  # noqa: E402
from repositories.pdm_repository import PDMRepository  # noqa: E402
from services.price_list_targets import normalize_mdb_date  # noqa: E402
from services.price_mdb_export_service import PriceMdbExportService  # noqa: E402
from services.pricing_service import PriceParams, PricingService  # noqa: E402

PS32 = r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
HARNESS = Path(__file__).with_name("run_pdm_price_update.ps1")
WATCHER = Path(__file__).with_name("dialog_watcher.ps1")
WORKSPACE = "Layout_Studio"
PROGRAM = "layout_studio"
PACKAGE_ID = 375
CAT_GLOBAL = 660
MYDATE, PREVDATE, VALID_FROM = "16-Oct-2026", "15-Oct-2026", "2026-10-16"
LISTS = {"EUR": ("EURO_2026_2", 21), "GBP": ("GBP_2026_2", 22)}


# ---- MDB helpers ----------------------------------------------------------------------------------
class Mdb:
    def __init__(self, ctx):
        self.svc = ctx.mdb_service

    def read(self, path: Path, **queries):
        return self.svc.read_tables(path, queries)

    def write(self, path: Path, ops: list[dict[str, Any]]):
        res = self.svc.execute_batch(path, ops, transaction=True)
        if not res.ok:
            raise RuntimeError(res.first_error())

    def state(self, path: Path) -> dict[str, Any]:
        """Normalised rows of every table PDM/Pricing may touch (ids stripped)."""
        r = self.read(
            path,
            lists="SELECT com_PriceListID, com_PriceListLabel, sys_ISOCurrencyCode, com_PriceValidFrom, com_PriceValidTo FROM tCOMd_PriceList2",
            price="SELECT l.com_PriceListLabel, a.com_ArticleCode, p.com_PriceID, p.com_VariantCondition, p.com_PriceLevelCode, "
                  "p.com_PriceTypeCode, p.com_PriceValue, p.sys_ISOCurrencyCode, p.com_PriceValidFrom, p.com_PriceValidTo, p.com_TextID "
                  "FROM (tCOMd_Price p INNER JOIN tCOMd_Article a ON p.com_ArticleID=a.com_ArticleID) "
                  "INNER JOIN tCOMd_PriceList2 l ON p.com_PriceListID=l.com_PriceListID",
            glob="SELECT l.com_PriceListLabel, l.com_PriceListID, g.com_GlobalPriceID, g.com_VariantCondition, g.com_PriceLevelCode, "
                 "g.com_PriceTypeCode, g.com_PriceValue, g.sys_ISOCurrencyCode, g.com_PriceValidFrom, g.com_PriceValidTo, g.com_TextID "
                 "FROM tCOMd_GlobalPrice g INNER JOIN tCOMd_PriceList2 l ON g.com_PriceListID=l.com_PriceListID "
                 "WHERE l.com_PriceListID IN (21,22,23,24)",
            gagg="SELECT com_PriceListID, COUNT(*) AS n, SUM(com_PriceValue) AS v FROM tCOMd_GlobalPrice GROUP BY com_PriceListID",
            texts="SELECT * FROM tCOMd_Text",
        )
        texts = {t["com_TextID"]: t for t in r["texts"]}

        def text_key(tid):
            t = texts.get(tid)
            if tid in (None, ""):
                return None
            if t is None:
                return ("DANGLING",)
            return (t["com_TextTypeCode"], t["com_TextName"], t.get("com_Text_1_en"), t.get("com_Text_1_de"),
                    t.get("com_Text_1_fr"), t.get("com_Text_1_nl"))

        def d(v):
            return normalize_mdb_date(v, "")

        rows = []
        for p in r["price"]:
            rows.append(("article", p["com_PriceListLabel"], p["com_ArticleCode"], p["com_VariantCondition"] or "",
                         p["com_PriceLevelCode"], p["com_PriceTypeCode"], _num(p["com_PriceValue"]),
                         p["sys_ISOCurrencyCode"], d(p["com_PriceValidFrom"]), d(p["com_PriceValidTo"]), text_key(p["com_TextID"])))
        for g in r["glob"]:
            rows.append(("global", g["com_PriceListLabel"], "", g["com_VariantCondition"] or "",
                         g["com_PriceLevelCode"], g["com_PriceTypeCode"], _num(g["com_PriceValue"]),
                         g["sys_ISOCurrencyCode"], d(g["com_PriceValidFrom"]), d(g["com_PriceValidTo"]), text_key(g["com_TextID"])))
        return {
            "rows": rows,
            "lists": sorted((l["com_PriceListLabel"], l["sys_ISOCurrencyCode"], d(l["com_PriceValidFrom"]),
                             d(l["com_PriceValidTo"])) for l in r["lists"]),
            "gagg": {x["com_PriceListID"]: (x["n"], _num(x["v"])) for x in r["gagg"]},
            "texts": sorted(json.dumps(text_key(t["com_TextID"]), default=str) for t in r["texts"]),
            "text_count": len(r["texts"]),
        }


def _num(v):
    try:
        return round(float(v), 6)
    except (TypeError, ValueError):
        return None


def _multiset(rows):
    out: dict[tuple, int] = {}
    for row in rows:
        key = json.dumps(row, default=str)
        out[key] = out.get(key, 0) + 1
    return out


def diff_states(before, after_a, after_b):
    """What PDM changed (A) vs what Pricing changed (B), and where the two results differ."""
    def delta(a, b):
        ma, mb = _multiset(a), _multiset(b)
        added = {k: v - ma.get(k, 0) for k, v in mb.items() if v > ma.get(k, 0)}
        removed = {k: v - mb.get(k, 0) for k, v in ma.items() if v > mb.get(k, 0)}
        return added, removed

    pdm_add, pdm_rem = delta(before["rows"], after_a["rows"])
    pr_add, pr_rem = delta(before["rows"], after_b["rows"])
    only_pdm = {k: v for k, v in _msub(_multiset(after_a["rows"]), _multiset(after_b["rows"])).items()}
    only_pr = {k: v for k, v in _msub(_multiset(after_b["rows"]), _multiset(after_a["rows"])).items()}
    return {
        "pdm_changed": {"added": sorted(pdm_add), "removed": sorted(pdm_rem)},
        "pricing_changed": {"added": sorted(pr_add), "removed": sorted(pr_rem)},
        "only_in_pdm_result": sorted(only_pdm),
        "only_in_pricing_result": sorted(only_pr),
        "lists_equal": after_a["lists"] == after_b["lists"],
        "texts_equal": after_a["texts"] == after_b["texts"],
        "texts_added": [after_a["text_count"] - before["text_count"], after_b["text_count"] - before["text_count"]],
        "global_aggregates_equal": after_a["gagg"] == after_b["gagg"],
    }


def _msub(a, b):
    return {k: v - b.get(k, 0) for k, v in a.items() if v > b.get(k, 0)}


# ---- PDM ---------------------------------------------------------------------------------------------
def run_pdm(work: Path, pdm_dir: Path, tag: str, mode: str, items, currency, list_id, label, catalogue=1,
            variableincs=None, item_filter="", timeout=300, program_code=PROGRAM) -> dict[str, Any]:
    job = {
        "pconRoot": str(work / tag / "root") + "\\", "workspace": WORKSPACE, "mode": mode, "items": list(items),
        "itemFilter": item_filter, "programCode": program_code, "siteId": 1, "catalogueId": catalogue,
        "mydate": MYDATE, "prevdate": PREVDATE, "currency": currency, "priceListId": list_id, "pricelist": label,
        "variableincsFromProgram": variableincs is None, "variableincs": bool(variableincs), "packageId": PACKAGE_ID, "resetToZero": False,
    }
    job_path, out_path = work / tag / "job.json", work / tag / "out.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")
    out_path.unlink(missing_ok=True)
    dialog_log = work / tag / "dialogs.jsonl"
    dialog_log.unlink(missing_ok=True)
    # PDM reports its own errors with modal message boxes: log + dismiss them (== an operator clicking OK).
    watcher = subprocess.Popen([PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(WATCHER),
                                "-LogPath", str(dialog_log), "-Seconds", str(timeout + 30)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        proc = subprocess.run(
            [PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HARNESS), "-JobPath", str(job_path),
             "-OutPath", str(out_path), "-PdmDir", str(pdm_dir)],
            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"executed": False, "error": f"PDM run exceeded {timeout}s", "dialogs": _dialogs(dialog_log)}
    finally:
        watcher.kill()
    if not out_path.is_file():
        return {"executed": False, "error": (proc.stderr or proc.stdout or "no output")[:800],
                "dialogs": _dialogs(dialog_log)}
    out = json.loads(out_path.read_text(encoding="utf-8-sig"))
    out["executed"] = bool(out.get("finished"))
    out["dialogs"] = _dialogs(dialog_log)
    return out


def _dialogs(path: Path) -> list[str]:
    if not path.is_file():
        return []
    texts = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        try:
            texts.append(json.loads(line)["dialog"])
        except (ValueError, KeyError):
            pass
    return texts


# ---- Pricing -----------------------------------------------------------------------------------------
def pricing_records(
    ctx, items, currency, super_codes=frozenset(), prefix_from_notes=True,
    catalogue_id=CAT_GLOBAL, program_code=PROGRAM,
):
    """Build expected records using the same distinct PDM fetch paths as Maintenance.

    Article items use the same inline increment query as PricingService.
    Super-products use the
    UpdatePriceThread global query (including its secondary price calculation,
    lookup-code construction, and Fabric Type -> Colour target routing). Using
    the article procedure for both paths can produce plausible but invalid
    global comparisons, so keep the two sources separate.
    """
    repo = PDMRepository(ctx)
    conn = repo.get_connection()
    try:
        item_codes = [str(item) for item in items if item]
        super_set = set(super_codes)
        article_items = [item for item in item_codes if item not in super_set]
        global_items = [item for item in item_codes if item in super_set]
        params = PriceParams(
            currency=currency, mydate=MYDATE, site_id=1,
            valid_from=VALID_FROM, valid_to="",
            program_code=program_code, catalogue_id=catalogue_id,
        )
        prefix = {}
        if prefix_from_notes:  # PDM's prefix length rule: Item.Notes up to the comma
            cur = conn.cursor()
            for it in item_codes:
                cur.execute("SELECT Notes FROM Item WHERE Item = ?", (it,))
                row = cur.fetchone()
                notes = (row[0] or "") if row else ""
                head = notes.split(",")[0].strip()
                if head.isdigit() and 0 < int(head) <= 20 and it not in super_set:
                    prefix[it] = it[:int(head)]
        base = repo.fetch_item_base_prices(item_codes, currency, MYDATE, conn, site_id=1)
        inc = []
        if article_items:
            inc.extend(repo.fetch_article_option_increment_prices(
                article_items, currency, MYDATE, 1, conn,
                program_code=program_code,
            ))
        if global_items:
            inc.extend(repo.fetch_global_option_increment_prices(
                global_items, currency, MYDATE, 1, conn,
                catalogue_id=catalogue_id, program_code=program_code,
            ))
        records, unresolved = PricingService.build_records(base, inc, super_set, prefix, params)
        PricingService._attach_product_codes(records, repo, conn, 1)
        return records, unresolved
    finally:
        conn.close()


def run_pricing(ctx, mdb_path: Path, records, currency, dry_first=True):
    snap = Snapshot()
    snap.price_records = list(records)
    name = LISTS[currency][0]
    svc = PriceMdbExportService(ctx)
    plan = svc.export(snap, mdb_path, dry_run=True, list_targets={currency: name})
    if not plan.get("ok") or not plan.get("export_allowed"):
        return {"ok": False, "plan": _slim(plan)}
    res = svc.export(snap, mdb_path, list_targets={currency: name}, expected_plan=plan["plan_digest"])
    res["plan_summary"] = plan.get("text_summary")
    return _slim(res)


def _slim(result):
    keep = {k: v for k, v in result.items() if k not in ("text_rows", "target_lists", "blocked_rows")}
    keep["text_row_count"] = len(result.get("text_rows") or [])
    return keep


# ---- scenarios ---------------------------------------------------------------------------------------
def _price_ids(m: Mdb, path: Path, label: str, article: str, variant: str):
    rows = m.read(path, x=(
        "SELECT p.com_PriceID AS id FROM (tCOMd_Price p INNER JOIN tCOMd_Article a ON p.com_ArticleID=a.com_ArticleID) "
        "INNER JOIN tCOMd_PriceList2 l ON p.com_PriceListID=l.com_PriceListID "
        f"WHERE l.com_PriceListLabel='{label}' AND a.com_ArticleCode='{article}' AND p.com_VariantCondition='{variant}'"))["x"]
    return [r["id"] for r in rows]


def _global_ids(m: Mdb, path: Path, label: str, variant: str, like=False):
    op = "LIKE" if like else "="
    rows = m.read(path, x=(
        "SELECT g.com_GlobalPriceID AS id FROM tCOMd_GlobalPrice g INNER JOIN tCOMd_PriceList2 l "
        f"ON g.com_PriceListID=l.com_PriceListID WHERE l.com_PriceListLabel='{label}' AND g.com_VariantCondition {op} '{variant}'"))["x"]
    return [r["id"] for r in rows]


def _setup_article(label, both_duplicates_stale=False):
    def setup(m: Mdb, path: Path):
        """Change three values, delete one row (missing-row insert), keep the rest."""
        ops = []
        if both_duplicates_stale:
            _setup_duplicates(m, path)
            for i in _price_ids(m, path, label, "GEWQ", "."):
                ops.append({"op": "update", "table": "tCOMd_Price", "set": {"com_PriceValue": 9.0}, "where": {"com_PriceID": i}})
        for art, var, val in (("GESG", ".", 2.0), ("GEWC", ".10", 3.0), ("GEWQ", ". 3827=DB3", 1.0)):
            for i in _price_ids(m, path, label, art, var):
                ops.append({"op": "update", "table": "tCOMd_Price", "set": {"com_PriceValue": val}, "where": {"com_PriceID": i}})
        for i in _price_ids(m, path, label, "GEWDP", ".S"):
            ops.append({"op": "delete", "table": "tCOMd_Price", "where": {"com_PriceID": i}})
        m.write(path, ops)
    return setup


def _setup_duplicates(m: Mdb, path: Path):
    """Duplicate identity: a second GEWQ '.' row in list 22 with a different stale value."""
    row = m.read(path, x="SELECT p.* FROM (tCOMd_Price p INNER JOIN tCOMd_Article a ON p.com_ArticleID=a.com_ArticleID) "
                         "INNER JOIN tCOMd_PriceList2 l ON p.com_PriceListID=l.com_PriceListID "
                         "WHERE l.com_PriceListLabel='GBP_2026_2' AND a.com_ArticleCode='GEWQ' AND p.com_VariantCondition='.'")["x"][0]
    new_id = m.read(path, x="SELECT MAX(com_PriceID) AS n FROM tCOMd_Price")["x"][0]["n"] + 1
    dup = {k: v for k, v in row.items() if not k.startswith("sys_tmp")}
    dup.update(com_PriceID=new_id, com_PriceValue=5.0,
               com_PriceValidFrom="#2026-09-07 00:00:00#", com_PriceValidTo="#9999-12-31 00:00:00#")
    m.write(path, [{"op": "insert", "table": "tCOMd_Price", "rows": [dup]}])


def _setup_global(delete_variants=(), changes=(), delete_text=None, delete_all_lists=False, label="GBP_2026_2",
                  delete_option_texts=()):
    def setup(m: Mdb, path: Path):
        ops = []
        for var, val in changes:
            for i in _global_ids(m, path, label, var):
                ops.append({"op": "update", "table": "tCOMd_GlobalPrice", "set": {"com_PriceValue": val}, "where": {"com_GlobalPriceID": i}})
        for var in delete_variants:
            ids = (m.read(path, x=f"SELECT com_GlobalPriceID AS id FROM tCOMd_GlobalPrice WHERE com_VariantCondition LIKE '{var}'")["x"]
                   if delete_all_lists else [{"id": i} for i in _global_ids(m, path, label, var, like=True)])
            ops += [{"op": "delete", "table": "tCOMd_GlobalPrice", "where": {"com_GlobalPriceID": r["id"]}} for r in ids]
        for name in delete_option_texts:  # option-id text: remove it and every global row that points at it
            for t in m.read(path, x=f"SELECT com_TextID AS id FROM tCOMd_Text WHERE com_TextTypeCode='price' AND com_TextName='{name}'")["x"]:
                for g in m.read(path, x=f"SELECT com_GlobalPriceID AS id FROM tCOMd_GlobalPrice WHERE com_TextID={t['id']}")["x"]:
                    ops.append({"op": "delete", "table": "tCOMd_GlobalPrice", "where": {"com_GlobalPriceID": g["id"]}})
                ops.append({"op": "delete", "table": "tCOMd_Text", "where": {"com_TextID": t["id"]}})
        if delete_text:
            for t in m.read(path, x=f"SELECT com_TextID AS id FROM tCOMd_Text WHERE com_TextTypeCode='price' AND com_TextName='{delete_text}'")["x"]:
                ops.append({"op": "delete", "table": "tCOMd_Text", "where": {"com_TextID": t["id"]}})
        m.write(path, ops)
    return setup


def _setup_text_refresh(m: Mdb, path: Path):
    """A hand-edited label on an existing price text ('GE2HBS.'), rows and links untouched."""
    ops = []
    for t in m.read(path, x="SELECT com_TextID AS id FROM tCOMd_Text WHERE com_TextTypeCode='price' AND com_TextName='GE2HBS.'")["x"]:
        ops.append({"op": "update", "table": "tCOMd_Text",
                    "set": {c: "CUSTOM LABEL" for c in ("com_Text_1_en", "com_Text_1_de", "com_Text_1_fr", "com_Text_1_nl")},
                    "where": {"com_TextID": t["id"]}})
    m.write(path, ops)


def _setup_non_price_text_collision(m: Mdb, path: Path):
    """Item GE2HDF. has no price text and no global rows, but a NON-price text carries its name."""
    _setup_global(delete_variants=("GE2HDF.%",), delete_text="GE2HDF.", delete_all_lists=True)(m, path)
    new_id = m.read(path, x="SELECT MAX(com_TextID) AS n FROM tCOMd_Text")["x"][0]["n"] + 1
    m.write(path, [{"op": "insert", "table": "tCOMd_Text", "rows": [{
        "com_TextID": new_id, "com_PackageID": PACKAGE_ID, "com_TextTypeCode": "artlong", "com_TextName": "GE2HDF.",
        "com_Text_1_en": "article long text", "com_Text_1_de": "article long text",
        "com_Text_1_fr": "article long text", "com_Text_1_nl": "article long text"}]}])


def _setup_lookalike_lists(m: Mdb, path: Path):
    """Stale values for global item GESNNU.105508F in the linked list 22 AND the look-alike orphan list 23."""
    ops = []
    for label in ("GBP_2026_2", "GBP 2026_2"):
        for i in _global_ids(m, path, label, "GESNNU.105508F"):
            ops.append({"op": "update", "table": "tCOMd_GlobalPrice", "set": {"com_PriceValue": 3.0},
                        "where": {"com_GlobalPriceID": i}})
    m.write(path, ops)


GLOBAL_ITEMS = ["GE2HBS.", "GE2HDF.", "GE2WE.", "GEAH.", "GEBA.08", "GETH.1022FS4W"]

SCENARIOS: dict[str, dict[str, Any]] = {
    "S1_article_gbp": {
        "title": "Article base + upcharge prices, GBP list 22: changed value, unchanged value, missing row, unresolved item",
        "covers": [1, 4, 5, 6, 8],
        "steps": [{"mode": "article", "items": ["GESG.", "GEWC.10", "GEWDP.L", "GEWDP.S", "GEWQ.", "GEPBPANNF.0608S4M"]}],
        "currency": "GBP", "setup": _setup_article("GBP_2026_2"), "second_run": True,
    },
    "S2_article_eur": {
        "title": "Same article scenario routed to the EUR list 21 (currency separation, EUR values)",
        "covers": [1, 4, 5, 6],
        "steps": [{"mode": "article", "items": ["GESG.", "GEWC.10", "GEWDP.L", "GEWDP.S", "GEWQ."]}],
        "currency": "EUR", "setup": _setup_article("EURO_2026_2"),
    },
    "S3_article_first_price_for_existing_article": {
        "title": "Items of articles that exist in tCOMd_Article but have no price row in the list",
        "covers": [5],
        "steps": [{"mode": "article", "items": ["GEWK.08", "GEWL.08", "GE3WS.08Y"]}],
        "currency": "GBP", "setup": None,
    },
    "S4_duplicate_article_identity": {
        "title": "Duplicate article price identity (two GEWQ '.' rows)",
        "covers": [9],
        "steps": [{"mode": "article", "items": ["GEWQ."]}],
        "currency": "GBP", "setup": _setup_duplicates,
    },
    "S4b_duplicates_both_stale": {
        "title": "Duplicate article identity where BOTH rows are stale (which row does PDM update?)",
        "covers": [9],
        "steps": [{"mode": "article", "items": ["GEWQ."]}],
        "currency": "GBP", "setup": _setup_article("GBP_2026_2", both_duplicates_stale=True),
    },
    "S5_global_update": {
        "title": "Global base + surcharge values, GBP list 22: changed values, unchanged, missing global row",
        "covers": [2, 3, 4, 5],
        "steps": [{"mode": "global", "items": GLOBAL_ITEMS, "catalogue": CAT_GLOBAL}],
        "currency": "GBP", "super": GLOBAL_ITEMS, "setup": _setup_global(
            delete_variants=("GE2HDF.",), changes=(("GE2HBS.", 1.0), ("GETH.1022FS4W 9168=AA", 1.0))),
        "second_run": True,
    },
    "S5b_global_update_variableincs_false": {
        "title": "As S5 but PDM forced to variableincs=false (item-prefixed surcharge matching) to compare surcharge VALUES",
        "covers": [3, 4],
        "steps": [{"mode": "global", "items": GLOBAL_ITEMS, "variableincs": False, "catalogue": CAT_GLOBAL}],
        "currency": "GBP", "super": GLOBAL_ITEMS, "setup": _setup_global(
            delete_variants=("GE2HDF.",), changes=(("GE2HBS.", 1.0), ("GETH.1022FS4W 9168=AA", 1.0))),
    },
    "S6_placeholders_then_global_reuse_text": {
        "title": "PDM's two-step new-global workflow (placeholders, then values) vs the single Pricing step; text reused",
        "covers": [2, 3, 5, 10, 11],
        "steps": [{"mode": "placeholders", "items": ["GE2HDF."], "catalogue": CAT_GLOBAL},
                  {"mode": "global", "items": ["GE2HDF."], "catalogue": CAT_GLOBAL}],
        "currency": "GBP", "super": ["GE2HDF."], "setup": _setup_global(delete_variants=("GE2HDF.%",)),
        "second_run": True,
    },
    "S8_global_eur": {
        "title": "Global values routed to EUR list 21: changed, unchanged, missing row",
        "covers": [2, 3, 4, 5, 6],
        "steps": [{"mode": "global", "items": GLOBAL_ITEMS, "catalogue": CAT_GLOBAL}],
        "currency": "EUR", "super": GLOBAL_ITEMS, "setup": _setup_global(
            label="EURO_2026_2", delete_variants=("GE2HDF.",), changes=(("GE2HBS.", 1.0), ("GETH.1022FS4W 9168=AA", 1.0))),
    },
    "S9_global_surcharge_text_creation": {
        "title": "Global item with surcharges whose option-id texts (9168, 3831) are missing: PDM's text names/labels",
        "covers": [3, 10, 11],
        "steps": [{"mode": "placeholders", "items": ["GETH.1022FS4W"], "catalogue": CAT_GLOBAL},
                  {"mode": "global", "items": ["GETH.1022FS4W"], "catalogue": CAT_GLOBAL}],
        "currency": "GBP", "super": ["GETH.1022FS4W"],
        "setup": _setup_global(delete_variants=("GETH.1022FS4W%",), delete_all_lists=True,
                               delete_text="GETH.1022FS4W", delete_option_texts=("9168", "3831")),
    },
    "S10_existing_text_label_refresh": {
        "title": "Existing price text with a hand-edited label: does PDM rewrite it on a placeholder run?",
        "covers": [10, 11],
        "steps": [{"mode": "placeholders", "items": ["GE2HBS."], "catalogue": CAT_GLOBAL}],
        "currency": "GBP", "super": ["GE2HBS."], "setup": _setup_text_refresh,
    },
    "S11_non_price_text_name_collision": {
        "title": "A non-price (artlong) text shares the item's name: does PDM link the new global row to it?",
        "covers": [10],
        "steps": [{"mode": "placeholders", "items": ["GE2HDF."], "catalogue": CAT_GLOBAL},
                  {"mode": "global", "items": ["GE2HDF."], "catalogue": CAT_GLOBAL}],
        "currency": "GBP", "super": ["GE2HDF."], "setup": _setup_non_price_text_collision,
    },
    "S13_lookalike_orphan_list": {
        "title": "PDM matches the list by LIKE 'GBP%2026%2' (also the orphan list 23 'GBP 2026_2'): does it write both?",
        "covers": [6],
        "steps": [{"mode": "global", "items": ["GESNNU.105508F"], "catalogue": CAT_GLOBAL}],
        "currency": "GBP", "super": ["GESNNU.105508F"], "setup": _setup_lookalike_lists,
    },
    "S7_placeholders_then_global_create_text": {
        "title": "As S6 but the price texts of the item are missing everywhere: text creation and Product_Code label",
        "covers": [10, 11],
        "steps": [{"mode": "placeholders", "items": ["GE2HDF."], "catalogue": CAT_GLOBAL},
                  {"mode": "global", "items": ["GE2HDF."], "catalogue": CAT_GLOBAL}],
        "currency": "GBP", "super": ["GE2HDF."],
        "setup": _setup_global(delete_variants=("GE2HDF.%",), delete_text="GE2HDF.", delete_all_lists=True),
    },
    "S14_revive_fabric_family_target": {
        "title": "Revive component fabric-family price source vs mapped colour-option export target",
        "covers": [3, 6],
        "steps": [{"mode": "global", "items": ["RY3SNNB.105512F"], "catalogue": CAT_GLOBAL}],
        "currency": "GBP", "super": ["RY3SNNB.105512F"], "program_code": "revive",
        "setup": None,
    },
}


def run_scenario(name, spec, ctx, backup: Path, pdm_dir: Path, work: Path) -> dict[str, Any]:
    m = Mdb(ctx)
    a_dir, b_dir = work / f"{name}_pdm", work / f"{name}_pricing"
    for d in (a_dir, b_dir):
        shutil.rmtree(d, ignore_errors=True)
    a_mdb = a_dir / "root" / "WS" / WORKSPACE / "pcr_data_com_ocd.mdb"
    b_mdb = b_dir / "pcr_data_com_ocd.mdb"
    a_mdb.parent.mkdir(parents=True)
    b_dir.mkdir(parents=True)
    shutil.copyfile(backup, a_mdb)
    shutil.copyfile(backup, b_mdb)
    for path in (a_mdb, b_mdb):
        if spec.get("setup"):
            spec["setup"](m, path)
    before = m.state(b_mdb)
    if m.state(a_mdb)["rows"] != before["rows"]:
        raise RuntimeError("setup differs between the copies")
    ccy = spec["currency"]
    label, list_id = LISTS[ccy]
    all_items = [i for s in spec["steps"] if s["mode"] != "placeholders" for i in s["items"]]
    report: dict[str, Any] = {
        "scenario": name, "title": spec["title"], "covers": spec["covers"],
        "inputs": {"steps": spec["steps"], "currency": ccy, "date": VALID_FROM, "list": label, "list_id": list_id}}

    def pdm_all():
        outs = []
        for n, st in enumerate(spec["steps"]):
            outs.append(run_pdm(work, pdm_dir, f"{name}_pdm", st["mode"], st["items"], ccy, list_id, label,
                                catalogue=st.get("catalogue", 1), variableincs=st.get("variableincs"),
                                program_code=spec.get("program_code", PROGRAM)))
            if not outs[-1].get("executed"):
                break
        return outs

    report["pdm"] = pdm_all()
    global_step = next((st for st in spec["steps"] if st["mode"] == "global"), None)
    catalogue_id = global_step.get("catalogue", CAT_GLOBAL) if global_step else CAT_GLOBAL
    records, unresolved = pricing_records(
        ctx, all_items, ccy, spec.get("super", ()),
        catalogue_id=catalogue_id, program_code=spec.get("program_code", PROGRAM),
    )
    report["pricing_inputs"] = {"records": len(records), "unresolved": unresolved}
    report["pricing"] = run_pricing(ctx, b_mdb, records, ccy)
    if not all(o.get("executed") for o in report["pdm"]):
        report["status"] = "UNVERIFIED: PDM did not execute"
        return report
    after_a, after_b = m.state(a_mdb), m.state(b_mdb)
    report["differences"] = diff_states(before, after_a, after_b)
    d = report["differences"]
    clean = not d["only_in_pdm_result"] and not d["only_in_pricing_result"] and d["lists_equal"] and d["texts_equal"]
    report["status"] = "MATCH" if clean else "DIFFERENCES"
    if spec.get("second_run"):
        pdm2 = pdm_all()
        pr2 = run_pricing(ctx, b_mdb, records, ccy)
        a2, b2 = m.state(a_mdb), m.state(b_mdb)
        report["second_run"] = {
            "pdm_status": [o.get("status", [])[-1:] for o in pdm2],
            "pricing": {k: pr2.get(k) for k in ("ok", "inserted_prices", "inserted_global_prices", "updated_prices",
                                                "updated_global_prices")},
            "pdm_changed_rows": a2["rows"] != after_a["rows"], "pdm_texts_changed": a2["texts"] != after_a["texts"],
            "pricing_changed_rows": b2["rows"] != after_b["rows"], "pricing_texts_changed": b2["texts"] != after_b["texts"],
        }
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backup", required=True)
    ap.add_argument("--pdm-dir", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scenarios", default="")
    args = ap.parse_args()
    ctx = ApplicationContext()
    names = [s for s in args.scenarios.split(",") if s] or list(SCENARIOS)
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    out = Path(args.out)
    results = []
    for n in names:
        results.append(run_scenario(n, SCENARIOS[n], ctx, Path(args.backup), Path(args.pdm_dir), work))
        out.write_text(json.dumps({"scenarios": results}, indent=1, default=str), encoding="utf-8")  # incremental
        print(n, results[-1].get("status"), flush=True)


if __name__ == "__main__":
    main()
