"""Headless validation for the direct OCD MDB exporter.

Loads a cached family snapshot, runs the engineering pipeline, then exports a
``pcr_data_com_ocd.mdb`` into a temp folder and reads the row counts back from
the copied template via the 32-bit ADODB bridge.

Run:  $env:PYTHONPATH="."; python scripts/validate_ocd_export.py [family.json]
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from core.application_context import ApplicationContext
from models.price_record import PriceRecord
from services.snapshot_serialization import snapshot_from_dict

_CACHE = Path(__file__).resolve().parents[1] / "cache" / "pdm_snapshots"

_READBACK = [
    "tCOMd_Text", "tCOMd_Class", "tCOMd_Property", "tCOMd_PropValue",
    "tCOMd_Article", "tCOMd_ArticleClass", "tCOMd_ArtBase", "tCOMd_RelObj",
    "tCOMd_Relation", "tCOMd_RelObjRel", "tCOMd_CodeScheme", "tCOMd_Table",
    "tCOMd_TableColumn", "tCOMd_TableLine", "tCOMd_Price", "tCOMd_GlobalPrice",
]


def _inject_prices(ctx, snapshot):
    """Give the snapshot a few synthetic price records (base + upcharge + global,
    EUR and GBP) so the Price/GlobalPrice writer is exercised - cached snapshots
    carry no prices (pricing is a separate live PDM step). Uses a real exported
    base article code so the tCOMd_Price -> tCOMd_Article foreign key holds, and a
    real option id on the upcharge so its 'price' text block has content."""
    if snapshot.price_records:
        return None
    base_codes = ctx.xocd_export_service._base_codes(snapshot)
    if not base_codes:
        return None
    code = base_codes[0]
    opt = snapshot.options[0] if snapshot.options else None
    opt_id = str(opt.id) if opt is not None else "9502"
    snapshot.price_records = [
        PriceRecord(False, code, "", "B", 100.0, "EUR", "", ""),
        PriceRecord(False, code, "", "B", 90.0, "GBP", "", ""),
        PriceRecord(False, code, f" {opt_id}=OK", "X", 5.0, "EUR", "", ""),
        PriceRecord(True, "", "SUPER1", "X", 50.0, "EUR", "", ""),
    ]
    return {"code": code, "opt_id": opt_id, "opt_name": (opt.name if opt is not None else "")}


def _prepare(ctx, snapshot):
    ctx.snapshot_manager.load_snapshot(snapshot)
    ctx.engineering_reduction_service.materialize_article_sets(snapshot)
    ctx.engineering_initialization_service.initialize(snapshot)
    ctx.engineering_member_service.auto_reduce(snapshot)
    category = (snapshot.product.category if snapshot.product else "") or "Class"
    ctx.engineering_class_service.ensure_standard_classes(snapshot, category)
    ctx.engineering_class_service.commit_config_codes(snapshot)


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "always.json"
    src = _CACHE / name
    if not src.is_file():
        print(f"snapshot not found: {src}")
        return 1

    snapshot = snapshot_from_dict(json.loads(src.read_text(encoding="utf-8")))
    ctx = ApplicationContext()
    _prepare(ctx, snapshot)
    priced_code = _inject_prices(ctx, snapshot)

    if not ctx.mdb_service.is_available():
        print("SKIP: 32-bit PowerShell / ACE bridge unavailable on this host.")
        return 0

    folder = Path(tempfile.gettempdir()) / "validate_ocd_mdb"
    folder.mkdir(parents=True, exist_ok=True)
    mdb = folder / "pcr_data_com_ocd.mdb"
    if mdb.is_file():
        mdb.unlink()

    result = ctx.ocd_export_service.export(snapshot, mdb)
    print(f"export: ok={result.ok} template={result.template} error={result.error}")
    for table, n in sorted(result.table_counts.items()):
        print(f"  {table}: {n} built")

    if not result.ok:
        return 1

    print("\nread-back from MDB:")
    counts: dict[str, int] = {}
    for table in _READBACK:
        rows = ctx.mdb_service.read_table(mdb, f"SELECT COUNT(*) AS n FROM [{table}]")
        counts[table] = rows[0]["n"] if rows else 0
        print(f"  {table}: {counts[table]}")

    pkg = ctx.mdb_service.read_table(
        mdb, "SELECT reg_ProgramCode, reg_ProgramLabel FROM tCOMd_Package"
    )
    print(f"\npackage rename: {pkg[0] if pkg else '(none)'}")

    if priced_code is not None:
        print("\nprice checks:")
        prices = ctx.mdb_service.read_table(
            mdb, "SELECT p.com_PriceValue, p.sys_ISOCurrencyCode, p.com_VariantCondition, "
                 "p.com_PriceLevelCode, p.com_TextID, p.com_PriceValidFrom, p.com_PriceValidTo, "
                 "pl.com_PriceListLabel "
                 "FROM tCOMd_Price p INNER JOIN tCOMd_PriceList2 pl "
                 "ON p.com_PriceListID = pl.com_PriceListID")
        globals_ = ctx.mdb_service.read_table(
            mdb, "SELECT com_PriceValue, sys_ISOCurrencyCode, com_VariantCondition "
                 "FROM tCOMd_GlobalPrice")
        price_text = ctx.mdb_service.read_table(
            mdb, "SELECT t.com_TextName, t.com_TextTypeCode, t.com_Text_1_en "
                 "FROM tCOMd_Price p INNER JOIN tCOMd_Text t ON p.com_TextID = t.com_TextID "
                 "WHERE p.com_PriceLevelCode = 'X'")
        ymd = ctx.price_update_service._bridge_ymd
        base = [r for r in prices if r["com_PriceLevelCode"] == "B"]
        upcharge = [r for r in prices if r["com_PriceLevelCode"] == "X"]
        checks = {
            "3 article price rows": counts["tCOMd_Price"] == 3,
            "1 global price row": counts["tCOMd_GlobalPrice"] == 1,
            "EUR base = 100": any(
                r["sys_ISOCurrencyCode"] == "EUR" and r["com_PriceValue"] == 100 for r in base),
            "GBP base = 90": any(
                r["sys_ISOCurrencyCode"] == "GBP" and r["com_PriceValue"] == 90 for r in base),
            "EUR upcharge = 5": any(r["com_PriceValue"] == 5 for r in upcharge),
            "global SUPER1 = 50": any(
                r["com_VariantCondition"] == "SUPER1" and r["com_PriceValue"] == 50 for r in globals_),
            "price on a currency list": all(
                (r["com_PriceListLabel"] or "").upper() != "NOPRICE" for r in prices),
            "valid dates round-trip (no day shift)": all(
                len(ymd(r["com_PriceValidFrom"])) == 8 and ymd(r["com_PriceValidTo"]).startswith("9999")
                for r in prices),
            "base rows carry no text (golden pattern)": all(r["com_TextID"] is None for r in base),
            "upcharge row links a 'price' text": bool(upcharge) and upcharge[0]["com_TextID"] is not None,
            "price text named by option id": any(
                r["com_TextName"] == priced_code["opt_id"] and r["com_TextTypeCode"] == "price"
                for r in price_text),
        }
        ok = True
        for name, passed in checks.items():
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
            ok = ok and bool(passed)
        print("\nRESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
