"""Full parity + referential-integrity validation of the direct OCD MDB export.

Exports a cached snapshot (with synthetic prices) into a temp ``pcr_data_com_ocd
.mdb`` and then, reading everything back through the 32-bit ADODB bridge:

1. **Referential integrity** - every foreign key in the exported MDB resolves to
   an existing parent row (no orphans), the strongest "importable" signal.
2. **Convention parity** - each coded column's vocabulary (article/price type &
   level codes, ``EQ`` operator, relation-object type/domain codes, text types,
   relation-name and code-scheme grammar) is a subset of a golden MDB's, so we
   emit the manufacturer's conventions, not invented ones.
3. **Row-count read-back** per product table + the package rename.

Run:  $env:PYTHONPATH="."; python scripts/validate_ocd_parity.py [family.json]
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

from core.application_context import ApplicationContext
from models.price_record import PriceRecord
from services.snapshot_serialization import snapshot_from_dict

_CACHE = Path(__file__).resolve().parents[1] / "cache" / "pdm_snapshots"
_GOLDEN = Path(
    r"C:\HermanMillerOFMLSVN\Staging\HermanMiller_old\WS\Seating\Seating\Always\pcr_data_com_ocd.mdb"
)

#: (child table, fk column, parent table, parent key) - every reference our
#: writer sets. Null child values are legitimate (optional link) and excluded.
_FK = [
    ("tCOMd_Property", "com_ClassID", "tCOMd_Class", "com_ClassID"),
    ("tCOMd_PropValue", "com_PropertyID", "tCOMd_Property", "com_PropertyID"),
    ("tCOMd_PropValue", "com_TextID", "tCOMd_Text", "com_TextID"),
    ("tCOMd_PropValue", "com_RelObjID", "tCOMd_RelObj", "com_RelObjID"),
    ("tCOMd_Property", "com_TextID", "tCOMd_Text", "com_TextID"),
    ("tCOMd_Property", "com_RelObjID", "tCOMd_RelObj", "com_RelObjID"),
    ("tCOMd_Article", "com_ComGroupID", "tCOMd_ComGroup", "com_ComGroupID"),
    ("tCOMd_Article", "com_CodeSchemeID", "tCOMd_CodeScheme", "com_CodeSchemeID"),
    ("tCOMd_Article", "com_ShortTextID", "tCOMd_Text", "com_TextID"),
    ("tCOMd_Article", "com_LongTextID", "tCOMd_Text", "com_TextID"),
    ("tCOMd_ArticleClass", "com_ArticleID", "tCOMd_Article", "com_ArticleID"),
    ("tCOMd_ArticleClass", "com_ClassID", "tCOMd_Class", "com_ClassID"),
    ("tCOMd_ArtBase", "com_ArticleID", "tCOMd_Article", "com_ArticleID"),
    ("tCOMd_RelObjRel", "com_RelObjID", "tCOMd_RelObj", "com_RelObjID"),
    ("tCOMd_RelObjRel", "com_RelationID", "tCOMd_Relation", "com_RelationID"),
    ("tCOMd_TableColumn", "com_TableID", "tCOMd_Table", "com_TableID"),
    ("tCOMd_TableLine", "com_TableColumnID", "tCOMd_TableColumn", "com_TableColumnID"),
    ("tCOMd_Price", "com_ArticleID", "tCOMd_Article", "com_ArticleID"),
    ("tCOMd_Price", "com_PriceListID", "tCOMd_PriceList2", "com_PriceListID"),
    ("tCOMd_Price", "com_TextID", "tCOMd_Text", "com_TextID"),
    ("tCOMd_GlobalPrice", "com_PriceListID", "tCOMd_PriceList2", "com_PriceListID"),
    ("tCOMd_GlobalPrice", "com_TextID", "tCOMd_Text", "com_TextID"),
    ("tCOMd_GlobalPrice", "com_PackageID", "tCOMd_Package", "com_PackageID"),
]

#: (table, column) whose value vocabulary must be a subset of the golden MDB's.
_VOCAB = [
    ("tCOMd_Article", "com_ArticleTypeCode"),
    ("tCOMd_Price", "com_PriceTypeCode"),
    ("tCOMd_Price", "com_PriceLevelCode"),
    ("tCOMd_PropValue", "com_PropValOpCodeFrom"),
    ("tCOMd_RelObjRel", "com_RelObjTypeCode"),
    ("tCOMd_RelObjRel", "com_RelObjDomainCode"),
    ("tCOMd_Text", "com_TextTypeCode"),
]

_READBACK = [
    "tCOMd_Text", "tCOMd_Class", "tCOMd_Property", "tCOMd_PropValue",
    "tCOMd_Article", "tCOMd_ArticleClass", "tCOMd_ArtBase", "tCOMd_RelObj",
    "tCOMd_Relation", "tCOMd_RelObjRel", "tCOMd_CodeScheme", "tCOMd_Table",
    "tCOMd_TableColumn", "tCOMd_TableLine", "tCOMd_Price", "tCOMd_GlobalPrice",
]


def _prepare(ctx, snapshot):
    ctx.snapshot_manager.load_snapshot(snapshot)
    ctx.engineering_reduction_service.materialize_article_sets(snapshot)
    ctx.engineering_initialization_service.initialize(snapshot)
    ctx.engineering_member_service.auto_reduce(snapshot)
    category = (snapshot.product.category if snapshot.product else "") or "Class"
    ctx.engineering_class_service.ensure_standard_classes(snapshot, category)
    ctx.engineering_class_service.commit_config_codes(snapshot)


def _inject_prices(ctx, snapshot):
    base_codes = ctx.xocd_export_service._base_codes(snapshot)
    if not base_codes:
        return
    code = base_codes[0]
    opt = snapshot.options[0] if snapshot.options else None
    opt_id = str(opt.id) if opt is not None else "9502"
    snapshot.price_records = [
        PriceRecord(False, code, "", "B", 100.0, "EUR", "", ""),
        PriceRecord(False, code, "", "B", 90.0, "GBP", "", ""),
        PriceRecord(False, code, f" {opt_id}=OK", "X", 5.0, "EUR", "", ""),
        PriceRecord(True, "", "SUPER1", "X", 50.0, "EUR", "", ""),
    ]


def _distinct(m, mdb, table, col):
    rows = m.read_table(mdb, f"SELECT DISTINCT [{col}] AS v FROM [{table}]")
    return {r["v"] for r in rows if r["v"] is not None}


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "always.json"
    src = _CACHE / name
    if not src.is_file():
        print(f"snapshot not found: {src}")
        return 1

    snapshot = snapshot_from_dict(json.loads(src.read_text(encoding="utf-8")))
    ctx = ApplicationContext()
    _prepare(ctx, snapshot)
    _inject_prices(ctx, snapshot)
    m = ctx.mdb_service

    if not m.is_available():
        print("SKIP: 32-bit PowerShell / ACE bridge unavailable on this host.")
        return 0
    if not _GOLDEN.is_file():
        print(f"SKIP: golden MDB not found: {_GOLDEN}")
        return 0

    folder = Path(tempfile.gettempdir()) / "validate_ocd_parity"
    folder.mkdir(parents=True, exist_ok=True)
    mdb = folder / "pcr_data_com_ocd.mdb"
    if mdb.is_file():
        mdb.unlink()

    result = ctx.ocd_export_service.export(snapshot, mdb)
    print(f"export: ok={result.ok} template={result.template} error={result.error}")
    if not result.ok:
        return 1
    mdb = str(mdb)

    print("\nread-back row counts:")
    for table in _READBACK:
        rows = m.read_table(mdb, f"SELECT COUNT(*) AS n FROM [{table}]")
        print(f"  {table}: {rows[0]['n'] if rows else 0}")

    checks: dict[str, bool] = {}

    # 1. Referential integrity - no orphan foreign keys.
    print("\nreferential integrity (orphan foreign keys):")
    for child, col, parent, pkey in _FK:
        sql = (f"SELECT COUNT(*) AS n FROM [{child}] c LEFT JOIN [{parent}] p "
               f"ON c.[{col}] = p.[{pkey}] WHERE c.[{col}] IS NOT NULL AND p.[{pkey}] IS NULL")
        orphans = m.read_table(mdb, sql)[0]["n"]
        checks[f"FK {child}.{col} -> {parent}"] = orphans == 0
        if orphans:
            print(f"  [ORPHANS={orphans}] {child}.{col} -> {parent}")

    # 2. Convention parity - our vocabulary is a subset of golden's.
    print("\nconvention parity (our codes subset of golden):")
    for table, col in _VOCAB:
        ours = _distinct(m, mdb, table, col)
        golden = _distinct(m, str(_GOLDEN), table, col)
        subset = ours <= golden
        checks[f"vocab {table}.{col} subset of golden"] = subset
        print(f"  {table}.{col}: ours={sorted(map(str, ours))} "
              f"golden={sorted(map(str, golden))} {'OK' if subset else 'MISMATCH'}")

    # 3. Grammar parity - relation names AA_/BA_ style; code-scheme body '@'/token.
    rel_names = [r["com_RelationName"] for r in
                 m.read_table(mdb, "SELECT com_RelationName FROM tCOMd_Relation")]
    checks["relation names follow <X>A_ grammar"] = all(
        re.match(r"^[A-Z]A_", n or "") for n in rel_names)  # empty -> vacuously true
    scheme_bodies = [r["com_CodeSchemeBody"] for r in
                     m.read_table(mdb, "SELECT com_CodeSchemeBody FROM tCOMd_CodeScheme")]
    checks["code-scheme body uses @/Class:Prop grammar"] = all(
        ("@" in (b or "") or ":" in (b or "")) for b in scheme_bodies) if scheme_bodies else True

    # 4. Package rename applied.
    pkg = m.read_table(mdb, "SELECT reg_ProgramCode, reg_ProgramLabel FROM tCOMd_Package")
    program = ctx.xocd_export_service.program_key(snapshot.product)
    checks["package renamed to product"] = bool(pkg) and pkg[0]["reg_ProgramCode"] == program
    print(f"\npackage rename: {pkg[0] if pkg else '(none)'} (expected {program})")

    print("\nchecks:")
    ok = True
    for check_name, passed in checks.items():
        if not passed:
            print(f"  [FAIL] {check_name}")
        ok = ok and bool(passed)
    print(f"  ({sum(checks.values())}/{len(checks)} passed)")
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
