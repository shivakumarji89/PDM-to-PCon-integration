"""ACE integration tests. Only newly created files under pytest's tmp_path are opened."""
from dataclasses import replace
import hashlib
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from models.snapshot import Snapshot
from services.mdb_service import MDBService, _PS32
from services.price_mdb_export_service import PriceMdbExportService
from tests.test_pricing_fabric_targets import FAMILIES, ITEM, records


@pytest.fixture
def disposable_mdb(tmp_path):
    if not Path(_PS32).is_file():
        pytest.skip("32-bit Windows PowerShell / ACE integration unavailable")
    path = tmp_path / "pricing.mdb"
    script = (
        "$ErrorActionPreference = 'Stop'; "
        "$catalog = New-Object -ComObject ADOX.Catalog; "
        f"$catalog.Create(\"Provider=Microsoft.ACE.OLEDB.16.0;Data Source={path};\"); "
        "$catalog.ActiveConnection.Close()"
    )
    created = subprocess.run([_PS32, "-NoProfile", "-Command", script],
                             capture_output=True, text=True)
    if created.returncode:
        if any(message in created.stderr.lower() for message in (
            "provider cannot be found", "class not registered", "80040154",
        )):
            pytest.skip("32-bit ACE provider is not installed")
        pytest.fail(f"Could not create disposable ACE MDB: {created.stderr}")
    service = MDBService(SimpleNamespace())
    common = (
        "com_PriceListID LONG, com_VariantCondition TEXT(255), com_PriceTypeCode TEXT(1), "
        "com_PriceLevelCode TEXT(1), com_PriceRuleCode TEXT(50), com_TextID LONG, "
        "com_PriceValue DOUBLE, sys_ISOCurrencyCode TEXT(3), com_PriceIndex TEXT(50), "
        "com_PriceValidFrom DATETIME, com_PriceValidTo DATETIME, com_RoundingID LONG, "
        "com_StatusInfoID LONG"
    )
    schema = [
        "CREATE TABLE tCOMd_Package (com_PackageID COUNTER PRIMARY KEY)",
        "CREATE TABLE tCOMd_Article (com_ArticleID COUNTER PRIMARY KEY, com_ArticleCode TEXT(100), "
        "com_ShortTextID LONG, com_LongTextID LONG)",
        "CREATE TABLE tCOMd_PriceList2 (com_PriceListID COUNTER PRIMARY KEY, "
        "com_PriceListLabel TEXT(100), sys_ISOCurrencyCode TEXT(3), "
        "com_PriceValidFrom DATETIME, com_PriceValidTo DATETIME)",
        "CREATE TABLE tCOMd_DistributionRegionPriceList (com_DistributionRegionID LONG, com_PriceListID LONG)",
        "CREATE TABLE tCOMd_Text (com_TextID COUNTER PRIMARY KEY, com_PackageID LONG, "
        "com_TextTypeCode TEXT(50), com_TextName TEXT(255), "
        "com_Text_1_en MEMO, com_Text_1_de MEMO, com_Text_1_fr MEMO, com_Text_1_nl MEMO, com_Text_1_it MEMO)",
        f"CREATE TABLE tCOMd_Price (com_PriceID COUNTER PRIMARY KEY, com_ArticleID LONG, {common})",
        f"CREATE TABLE tCOMd_GlobalPrice (com_GlobalPriceID COUNTER PRIMARY KEY, com_PackageID LONG, {common})",
        "CREATE TABLE tCOMd_Property (com_PropertyID COUNTER PRIMARY KEY, com_TextID LONG)",
        "CREATE TABLE tCOMd_PropValue (com_ValueID COUNTER PRIMARY KEY, com_PropertyID LONG, com_TextID LONG)",
        "CREATE TABLE tCOMd_ArticleClass (com_ArticleClassID COUNTER PRIMARY KEY, com_ArticleID LONG, com_ClassID LONG)",
        "ALTER TABLE tCOMd_GlobalPrice ADD CONSTRAINT price_text_fk FOREIGN KEY (com_TextID) "
        "REFERENCES tCOMd_Text (com_TextID)",
    ]
    setup = "; ".join(
        "$conn.Execute('" + sql.replace("'", "''") + "') | Out-Null" for sql in schema
    )
    proc = subprocess.run([
        _PS32, "-NoProfile", "-Command",
        "$ErrorActionPreference='Stop'; $conn=New-Object -ComObject ADODB.Connection; "
        f"$conn.Open('Provider=Microsoft.ACE.OLEDB.16.0;Data Source={path};'); "
        + setup + "; $conn.Close()",
    ], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    seed = [
        {"op": "insert", "table": "tCOMd_Package", "rows": [{"com_PackageID": 1}]},
        {"op": "insert", "table": "tCOMd_PriceList2", "rows": [
            {"com_PriceListID": i, "com_PriceListLabel": label, "sys_ISOCurrencyCode": ccy,
             "com_PriceValidFrom": "#2026-01-01 00:00:00#", "com_PriceValidTo": "#9999-12-31 00:00:00#"}
            for i, label, ccy in [(21, "EURO_2026_2", "EUR"), (22, "GBP_2026_2", "GBP")]]},
        {"op": "insert", "table": "tCOMd_DistributionRegionPriceList", "rows": [
            {"com_DistributionRegionID": 6, "com_PriceListID": 21},
            {"com_DistributionRegionID": 7, "com_PriceListID": 22}]},
        {"op": "insert", "table": "tCOMd_Text", "rows": [
            {"com_TextID": tid, "com_PackageID": 1, "com_TextTypeCode": kind,
             "com_TextName": name, "com_Text_1_en": content}
            for tid, kind, name, content in [
                (70, "price", ITEM, "Base price"), (501, "artlong", ITEM, "Long description"),
                (502, "artshort", ITEM, "Short description"),
                (503, "property", "Fabric_Colour", "Fabric colour"),
                (504, "propvalue", "Fabric_Colour_1FD", "Fabric value")]]},
        {"op": "insert", "table": "tCOMd_GlobalPrice", "rows": [
            {"com_GlobalPriceID": i, "com_PackageID": 1, "com_PriceListID": lid,
             "com_VariantCondition": ITEM, "com_PriceValue": 50,
             "com_PriceLevelCode": "X", "com_TextID": 70} for i, lid in [(9, 21), (10, 22)]]},
        {"op": "insert", "table": "tCOMd_Article", "rows": [
            {"com_ArticleID": 1, "com_ArticleCode": ITEM, "com_LongTextID": 501, "com_ShortTextID": 502}]},
        {"op": "insert", "table": "tCOMd_Property", "rows": [{"com_PropertyID": 640, "com_TextID": 503}]},
        {"op": "insert", "table": "tCOMd_PropValue", "rows": [
            {"com_ValueID": 1, "com_PropertyID": 640, "com_TextID": 504}]},
        {"op": "insert", "table": "tCOMd_ArticleClass", "rows": [
            {"com_ArticleClassID": 1, "com_ArticleID": 1, "com_ClassID": 2}]},
    ]
    seeded = service.execute_batch(path, seed, transaction=True)
    assert seeded.ok, seeded.first_error()
    try:
        yield path, service
    finally:
        path.unlink(missing_ok=True)
        path.with_suffix(".ldb").unlink(missing_ok=True)


def test_complete_family_export_against_disposable_ace_mdb(disposable_mdb):
    path, mdb = disposable_mdb
    service = PriceMdbExportService(SimpleNamespace(mdb_service=mdb))
    snapshot = Snapshot(price_records=records() + [replace(r, currency="GBP") for r in records()])
    preserved_tables = ("tCOMd_Article", "tCOMd_Property", "tCOMd_PropValue", "tCOMd_ArticleClass")
    queries = {t: f"SELECT * FROM {t}" for t in preserved_tables}
    queries["texts"] = "SELECT * FROM tCOMd_Text WHERE com_TextID <= 504"
    before = mdb.read_tables(path, queries)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    preview = service.export(snapshot, path, dry_run=True)
    assert preview["ok"] and preview["export_allowed"], preview
    assert preview["inserted_global_prices"] == 8
    assert preview["text_summary"]["text_create"] == 1
    assert preview["text_summary"]["text_link_new"] == 7
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    result = service.export(snapshot, path, expected_plan=preview["plan_digest"])
    assert result["ok"] and result["verified"], result
    assert result["inserted_global_prices"] == 8
    conditions = mdb.read_table(
        path,
        "SELECT com_PriceListID, com_VariantCondition FROM tCOMd_GlobalPrice "
        "WHERE com_PriceListID IN (21, 22)",
    )
    expected_conditions = {f"{ITEM} 28={family[0]}" for family in FAMILIES}
    fabric_rows = [row for row in conditions if " 28=" in row["com_VariantCondition"]]
    fabric_conditions = {row["com_VariantCondition"] for row in fabric_rows}
    assert fabric_conditions == expected_conditions
    assert len(fabric_rows) == 8
    tid = result["text_rows"][0]["text_id"]
    assert isinstance(tid, int) and tid > 504
    assert {r["text_id"] for r in result["text_rows"]} == {tid}
    texts = mdb.read_table(path, f"SELECT * FROM tCOMd_Text WHERE com_TextID = {tid}")
    assert texts[0]["com_TextName"] == "28"
    assert texts[0]["com_TextTypeCode"] == "price"
    assert {texts[0][f"com_Text_1_{lang}"] for lang in ("en", "de", "fr", "nl", "it")} == {"Surcharge 28"}
    assert mdb.read_tables(path, queries) == before
    repeated = service.export(snapshot, path)
    assert repeated["ok"] and repeated["inserted_global_prices"] == 0
    assert repeated["updated_global_prices"] == 0
    snapshot.price_records[0] = replace(snapshot.price_records[0], value=90)
    updated = service.export(snapshot, path)
    assert updated["ok"] and updated["updated_global_prices"] == 1
    assert updated["text_rows"][0]["text_id"] == tid
    assert mdb.read_tables(path, queries) == before
    snapshot.price_records = [replace(r, valid_from="2027-01-05") for r in snapshot.price_records]
    snapshot.price_records += [
        replace(snapshot.price_records[0], currency=ccy, variant_condition=ITEM,
                pdm_lookup_code=ITEM, value=50) for ccy in ("EUR", "GBP")
    ]
    targets = {"EUR": "EURO_2027", "GBP": "GBP_2027"}
    preview = service.export(snapshot, path, dry_run=True, list_targets=targets)
    assert preview["ok"] and preview["export_allowed"] and preview["inserted_price_lists"] == 2, preview
    exported = service.export(snapshot, path, list_targets=targets, expected_plan=preview["plan_digest"])
    assert exported["ok"] and exported["verified"], exported
    assert exported["inserted_price_lists"] == 2 and exported["inserted_global_prices"] == 10
    assert exported["text_summary"]["text_create"] == 0
    assert mdb.read_tables(path, queries) == before


def test_existing_legacy_fabric_condition_is_normalized_and_repeated_export_is_idempotent(disposable_mdb):
    path, mdb = disposable_mdb
    service = PriceMdbExportService(SimpleNamespace(mdb_service=mdb))
    seeded = mdb.execute_batch(path, [{
        "op": "insert", "table": "tCOMd_GlobalPrice", "rows": [{
            "com_GlobalPriceID": 90, "com_PackageID": 1, "com_PriceListID": 21,
            "com_VariantCondition": f"28={ITEM}_1FD", "com_PriceLevelCode": "X",
            "com_PriceValue": 50, "com_TextID": 70,
        }],
    }], transaction=True)
    assert seeded.ok, seeded.first_error()

    snapshot = Snapshot(price_records=records())
    preview = service.export(snapshot, path, dry_run=True)
    assert preview["ok"] and preview["export_allowed"], preview
    assert preview["updated_global_prices"] == 1
    assert preview["inserted_global_prices"] == len(FAMILIES) - 1
    assert preview["plan_updates"][0]["variant_condition"] == f"28={ITEM}_1FD"
    assert preview["plan_updates"][0]["target_variant_condition"] == f"{ITEM} 28=1FD"

    exported = service.export(snapshot, path, expected_plan=preview["plan_digest"])
    assert exported["ok"] and exported["verified"], exported
    stored = mdb.read_table(
        path,
        "SELECT com_GlobalPriceID, com_VariantCondition, com_PriceValue, com_TextID "
        "FROM tCOMd_GlobalPrice WHERE com_GlobalPriceID = 90",
    )
    assert stored == [{
        "com_GlobalPriceID": 90, "com_VariantCondition": f"{ITEM} 28=1FD",
        "com_PriceValue": 89.0, "com_TextID": 70,
    }]

    repeated = service.export(snapshot, path)
    assert repeated["ok"], repeated
    assert repeated["updated_global_prices"] == 0
    assert repeated["inserted_global_prices"] == 0
    assert mdb.read_table(
        path,
        "SELECT com_VariantCondition FROM tCOMd_GlobalPrice WHERE com_GlobalPriceID = 90",
    ) == [{"com_VariantCondition": f"{ITEM} 28=1FD"}]


def test_generated_identity_reference_failure_rolls_back(disposable_mdb):
    path, mdb = disposable_mdb
    result = mdb.execute_batch(path, [
        {"op": "insert", "table": "tCOMd_Text", "identity": "com_TextID", "rows": [
            {"com_TextID": "new:text:rollback", "com_TextName": "rollback", "com_PackageID": 1}]},
        {"op": "insert", "table": "tCOMd_GlobalPrice", "identity": "com_GlobalPriceID", "rows": [
            {"com_GlobalPriceID": "new:global:rollback", "com_TextID": {"$ref": "missing"}}]},
    ], transaction=True)
    assert not result.ok and "Unresolved identity reference" in result.first_error()
    assert mdb.read_table(path, "SELECT * FROM tCOMd_Text WHERE com_TextName = 'rollback'") == []
