from dataclasses import asdict, replace
from decimal import Decimal
import hashlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.errors import PDMQueryError
from models.product import Product
from models.snapshot import Snapshot
from repositories.pdm_repository import GlobalOptionPriceRow, PDMRepository
from services.price_text_blocks import record_result_key, row_result_key, text_block_cells
from services.price_mdb_export_service import PriceMdbExportService
from services.pricing_service import PriceParams, PricingService
from services.snapshot_serialization import price_record_from_dict, price_record_to_dict
from tests.test_price_mdb_export_service import (
    _OptimizedFake, _RecordingMDB, _eur_gbp_lists, _export, _export_dry,
)


ITEM = "RY3SNNB.105512F"
FAMILIES = [
    ("1FD", 148810, 194788, "77", "89"),
    ("1HA", 136033, 136035, "38", "44"),
    ("4MT", 290057, 290058, "115", "133"),
    ("ZM2", 196842, 196843, "77", "89"),
]


def source_rows(item=ITEM, option=8):
    return [
        GlobalOptionPriceRow(
            item, vid, option, code + "#", f"{item}_{code}#",
            f"{item} {option}={code}#", Decimal(raw), None, Decimal(price),
        ) for code, vid, _, raw, price in FAMILIES
    ]


def relation(vid: int = 148810, colour: int | None = 194788,
             target: int = 28, price: Decimal | None = None):
    return SimpleNamespace(
        SourceValueId=vid, ParentItem="PARENT", TargetOptionId=target,
        ColourValueId=colour, IncrementalPrice=price,
        IncrementalPrice2=None, IncrementalPrice3=None,
    )


def resolve(rows, relations=None):
    repo = PDMRepository(MagicMock())
    execute = MagicMock(return_value=relations if relations is not None else [
        relation(vid, colour) for _, vid, colour, _, _ in FAMILIES
    ])
    repo._execute = execute
    repo._resolve_global_fabric_targets(rows, 658, object())
    return execute


def records():
    rows = source_rows()
    resolve(rows)
    return PricingService.build_records([], rows, {ITEM}, {}, PriceParams(currency="EUR"))[0]


def target_mdb(records_, **overrides):
    globals_, texts = [], []
    for i, record in enumerate(records_):
        code = record.variant_condition.split("=")[1]
        for option in (8, 28):
            pid = 100 + i * 2 + (option == 28)
            condition = f"{option}={ITEM}_{code}"
            globals_.append({
                "com_GlobalPriceID": pid, "com_PackageID": 1, "com_PriceListID": 21,
                "com_VariantCondition": condition, "com_PriceValue": 0.0,
                "com_PriceLevelCode": "X", "sys_ISOCurrencyCode": "EUR", "com_TextID": pid + 1000,
            })
            texts.append({"com_TextID": pid + 1000, "com_TextName": condition,
                          "com_Text_1_en": condition})
    return _OptimizedFake(_eur_gbp_lists(), linked=[21, 22],
                          globals_=overrides.get("globals_", globals_), texts=texts)


def test_relationship_separates_price_source_from_colour_target_without_reordering():
    rows = source_rows()
    before = [asdict(row) for row in rows]
    execute = resolve(rows)
    query, params = execute.call_args.args
    for required in (
        "source_option.IsFabric = 1", "colour_option.IsFabric = 2",
        "source.OptionValueId = dependency.OptionValueId",
        "dependency.AdditionalOptionValueId = colour.OptionValueId",
        "colour.OptionId = colour_option.OptionId",
        "mapping.FeaturePositionString", "cov.CatalogueId = ?",
    ):
        assert required in query
    assert params == (658, 658, ITEM, *(r.OptionValueId for r in rows))
    for row, original, family in zip(rows, before, FAMILIES):
        assert row.TargetOptionId == 28
        assert row.ColourValueIds == (family[2],)
        assert {k: v for k, v in asdict(row).items()
                if k not in ("TargetOptionId", "ColourValueIds")} == {
                    k: v for k, v in original.items()
                    if k not in ("TargetOptionId", "ColourValueIds")
                }
    result, unresolved = PricingService.build_records(
        [], rows, {ITEM}, {}, PriceParams(currency="EUR")
    )
    assert not unresolved
    assert [r.variant_condition for r in result] == [f"{ITEM} 28={f[0]}" for f in FAMILIES]
    assert [r.value for r in result] == [float(f[4]) for f in FAMILIES]
    assert [r.pdm_lookup_code for r in result] == [f"{ITEM} 8={f[0]}#" for f in FAMILIES]
    assert all(price_record_from_dict(price_record_to_dict(r)) == r for r in result)
    assert text_block_cells(result[0]) == ("Not checked", "28 (proposed)", "unchecked")


def test_resolution_uses_metadata_not_literal_option_ids_or_article_names():
    for item in ("ANOTHER.COMPONENT", "THIRD.COMPONENT"):
        rows = source_rows(item, option=108)
        execute = resolve(rows, [relation(vid, colour, target=228) for _, vid, colour, _, _ in FAMILIES])
        assert all(row.TargetOptionId == 228 and row.OptionId == 108 for row in rows)
        assert execute.call_args.args[1][2] == item
        result, _ = PricingService.build_records([], rows, {item}, {}, PriceParams())
        assert [r.variant_condition for r in result] == [f"{item} 228={f[0]}" for f in FAMILIES]


@pytest.mark.parametrize("relations", [
    [relation(colour=None)],
    [relation(), relation(target=3346)],
    [relation(price=Decimal("1"))],
])
def test_missing_ambiguous_or_separately_priced_colour_relationship_fails_explicitly(relations):
    with pytest.raises(PDMQueryError, match=r"parent PARENT, component RY3SNNB.*source option 8/value 148810"):
        resolve(source_rows(), relations)


def test_fabric_type_without_component_colour_mapping_stays_unchanged():
    rows = source_rows()
    resolve(rows, [])
    result, _ = PricingService.build_records([], rows, {ITEM}, {}, PriceParams())
    assert [r.variant_condition for r in result] == [f"{ITEM} 8={f[0]}" for f in FAMILIES]
    assert all(r.TargetOptionId is None for r in rows)

    article_rows, _ = PricingService.build_records(
        [], [SimpleNamespace(Item="PLAIN", OptionId=8, Code="1FD#", IncPrice=Decimal("89"))],
        set(), {"PLAIN": "PLAIN"}, PriceParams(),
    )
    assert article_rows[0].variant_condition == " 8=1FD"
    assert not article_rows[0].is_global


@pytest.mark.parametrize("program", ["av", "embody", "layout_studio"])
def test_other_programs_do_not_resolve_or_remap_fabric_targets(program):
    repo = PDMRepository(MagicMock())
    repo._resolve_global_fabric_targets = MagicMock()
    repo._execute = lambda query, params, connection=None: (
        [SimpleNamespace(Item=ITEM, NewPrice=Decimal("89"))] if "AS NewPrice" in query else [
            SimpleNamespace(Item=ITEM, OptionId=8, OptionValueId=148810,
                            OrderCodeValue=f"{ITEM}_1FD#", RawIncrement=Decimal("77"), PriceBand=None)
        ]
    )
    fetched = repo.fetch_global_option_increment_prices(
        [ITEM], "EUR", "25-Oct-2026", 1, object(), catalogue_id=658, program_code=program
    )
    repo._resolve_global_fabric_targets.assert_not_called()
    assert fetched[0].OptionId == 8 and fetched[0].TargetOptionId is None


@pytest.mark.parametrize("program", ["revive", ""])
def test_fetch_keeps_calculation_order_and_applies_relationship_after_prices(program):
    rows = source_rows()
    repo = PDMRepository(MagicMock())
    calls = []

    def execute(query, params, connection=None):
        if "AS TargetOptionId" in query:
            calls.append("relationships")
            return [relation(vid, colour) for _, vid, colour, _, _ in FAMILIES]
        if "AS NewPrice" in query:
            vid = params[6]
            calls.append(vid)
            return [SimpleNamespace(Item=ITEM, NewPrice=next(r.IncPrice for r in rows if r.OptionValueId == vid))]
        calls.append("source")
        return [
            SimpleNamespace(Item=r.Item, OptionId=r.OptionId, OptionValueId=r.OptionValueId,
                            OrderCodeValue=r.SourceCode, RawIncrement=r.RawIncrement, PriceBand=None)
            for r in rows
        ]

    repo._execute = execute
    actual = repo.fetch_global_option_increment_prices(
        [ITEM], "EUR", "25-Oct-2026", 1, object(), catalogue_id=658, program_code=program
    )
    # The last family's raw 77 reuses the original cache entry, as before.
    assert calls == ["source", 148810, 136033, 290057, "relationships"]
    assert [(r.OptionValueId, r.OptionId, r.TargetOptionId, r.IncPrice) for r in actual] == [
        (r.OptionValueId, 8, 28, r.IncPrice) for r in rows
    ]


def test_existing_legacy_colour_targets_normalize_and_preserve_text_ids():
    computed = records()
    mdb = target_mdb(computed)
    before = [dict(r) for r in mdb.rows[next(k for k in mdb.rows if k.startswith("SELECT com_GlobalPriceID"))]]
    preview = _export_dry(mdb, computed)
    assert mdb.ops == []
    assert preview["export_allowed"]
    assert (preview["updated_global_prices"], preview["inserted_global_prices"]) == (4, 0)
    assert preview["text_summary"]["text_preserve"] == 4
    assert preview["text_summary"]["text_create"] == 0
    for entry, rec in zip(preview["text_rows"], computed):
        assert entry["price_source_condition"] == rec.pdm_lookup_code
        assert row_result_key(entry) == record_result_key(rec)
        assert text_block_cells(rec, entry)[0] == str(entry["text_id"])
        assert entry["variant_condition"] == rec.variant_condition

    result = _export(mdb, computed)
    assert result["ok"] and result["verified"]
    assert [op["where"] for op in mdb.ops] == [
        {"com_GlobalPriceID": 101 + i * 2} for i in range(4)
    ]
    assert all(op["op"] == "update" and set(op["set"]) == {
        "com_PriceValue", "com_VariantCondition"
    } for op in mdb.ops)
    assert [op["set"]["com_VariantCondition"] for op in mdb.ops] == [
        rec.variant_condition for rec in computed
    ]
    updated = {op["where"]["com_GlobalPriceID"]: op["set"]["com_PriceValue"] for op in mdb.ops}
    repeated = target_mdb(computed, globals_=[
        {**r,
         "com_PriceValue": updated.get(r["com_GlobalPriceID"], r["com_PriceValue"]),
         "com_VariantCondition": next(
             (op["set"]["com_VariantCondition"] for op in mdb.ops
              if op["where"]["com_GlobalPriceID"] == r["com_GlobalPriceID"]),
             r["com_VariantCondition"],
         )}
        for r in before
    ])
    again = _export(repeated, computed)
    assert again["ok"] and repeated.ops == []
    assert (again["updated_global_prices"], again["inserted_global_prices"]) == (0, 0)


def test_existing_canonical_colour_target_only_updates_its_price():
    record = records()[0]
    mdb = target_mdb([record])
    key = next(k for k in mdb.rows if k.startswith("SELECT com_GlobalPriceID"))
    target = next(row for row in mdb.rows[key] if row["com_VariantCondition"].startswith("28="))
    target["com_VariantCondition"] = record.variant_condition

    result = _export(mdb, [record])

    assert result["ok"] and result["verified"]
    assert result["updated_global_prices"] == 1
    assert result["inserted_global_prices"] == 0
    assert mdb.ops[0]["set"] == {"com_PriceValue": record.value}


def new_target_mdb(texts=()):
    base = {
        "com_GlobalPriceID": 9, "com_PackageID": 1, "com_PriceListID": 21,
        "com_VariantCondition": ITEM, "com_PriceValue": 50.0,
        "com_PriceLevelCode": "X", "sys_ISOCurrencyCode": "EUR", "com_TextID": 70,
    }
    return _OptimizedFake(_eur_gbp_lists(), linked=[21, 22], globals_=[base], texts=[
        {"com_TextID": 70, "com_TextName": ITEM}, *texts,
    ])


@pytest.mark.parametrize("reuse", [False, True])
def test_new_family_rows_use_option_text_not_option_as_database_id(tmp_path, reuse):
    computed = records()
    mdb = new_target_mdb([{"com_TextID": 9307, "com_TextName": "28",
                          "com_Text_1_en": "Translated fabric surcharge"}] if reuse else [])
    mdb.identity_seeds = {"tCOMd_Text": 8401, "tCOMd_GlobalPrice": 9701}
    path = tmp_path / "disposable.mdb"
    path.write_bytes(b"Preview must not change these bytes")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    service = PriceMdbExportService(SimpleNamespace(mdb_service=mdb))
    snapshot = Snapshot(price_records=computed)
    preview = service.export(snapshot, path, dry_run=True)
    assert preview["ok"] and preview["export_allowed"]
    assert mdb.ops == [] and hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert preview["inserted_global_prices"] == 4 and preview["updated_global_prices"] == 0
    assert preview["text_summary"]["text_create"] == (0 if reuse else 1)
    assert preview["text_summary"]["text_reuse"] == (4 if reuse else 0)
    assert preview["text_summary"]["text_link_new"] == (0 if reuse else 3)
    assert {e["text_name"] for e in preview["text_rows"]} == {"28"}
    assert {e["text_id"] for e in preview["text_rows"]} == ({9307} if reuse else {None})
    for record, entry in zip(computed, preview["text_rows"]):
        assert row_result_key(entry) == record_result_key(record)
        if not reuse:
            assert text_block_cells(record, entry)[0] == "New (not written)"

    result = service.export(snapshot, path, expected_plan=preview["plan_digest"])
    assert result["ok"] and result["verified"], result
    assert mdb.transaction
    assert {op["table"] for op in mdb.ops} == (
        {"tCOMd_GlobalPrice"} if reuse else {"tCOMd_Text", "tCOMd_GlobalPrice"})
    rows = next(op["rows"] for op in mdb.ops if op["table"] == "tCOMd_GlobalPrice")
    tid = 9307 if reuse else 8401
    assert {r["com_TextID"] for r in rows} == {tid}
    assert [r["com_GlobalPriceID"] for r in rows] == [9701, 9708, 9715, 9722]
    assert [r["com_VariantCondition"] for r in rows] == [f"{ITEM} 28={f[0]}" for f in FAMILIES]
    assert [r["com_PriceValue"] for r in rows] == [89, 44, 133, 89]
    assert all(r["com_PriceLevelCode"] == "X" and r["com_PriceListID"] == 21 for r in rows)
    if not reuse:
        text = mdb.ops[0]["rows"][0]
        assert text["com_TextName"] == "28" and text["com_TextTypeCode"] == "price"
        assert {v for k, v in text.items() if k.startswith("com_Text_1_")} == {"Surcharge 28"}
        submitted = mdb.submitted_ops[-1]["rows"]
        assert all(r["com_TextID"] == {"$ref": "new:text:28"} for r in submitted)
    assert {e["text_id"] for e in result["text_rows"]} == {tid}

    again = new_target_mdb()
    key = next(k for k in again.rows if k.startswith("SELECT com_GlobalPriceID"))
    again.rows[key].extend(rows)
    again.texts.extend([{"com_TextID": tid, "com_TextName": "28"}])
    repeated = _export(again, computed)
    assert repeated["ok"] and again.ops == []


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("different_price", [False, True])
def test_duplicate_computed_family_targets_block_the_entire_export(existing, different_price):
    record = records()[0]
    mdb = target_mdb([record]) if existing else new_target_mdb()
    computed = [record, replace(record, value=90 if different_price else record.value)]
    preview = _export_dry(mdb, computed)
    assert not preview["export_allowed"]
    assert "duplicate input=True" in "; ".join(preview["blocking_errors"])
    result = _export(mdb, computed)
    assert not result["ok"] and mdb.ops == []


def test_new_family_with_ambiguous_option_text_or_no_base_is_blocked():
    for mdb in (new_target_mdb([{"com_TextID": 44, "com_TextName": "28"},
                                {"com_TextID": 55, "com_TextName": "28"}]),
                _OptimizedFake(_eur_gbp_lists(), linked=[21, 22])):
        preview = _export_dry(mdb, records()[:1])
        assert not preview["export_allowed"]
        assert not _export(mdb, records()[:1])["ok"] and mdb.ops == []


def test_missing_generated_ids_are_reported_as_unverified_not_invented():
    mdb = new_target_mdb()
    execute = mdb.execute_batch

    def without_ids(*args, **kwargs):
        result = execute(*args, **kwargs)
        for op in result.results:
            op.generated_ids = {}
        return result

    mdb.execute_batch = without_ids
    result = _export(mdb, records()[:1])
    assert not result["ok"] and result["verified"] is False
    assert "did not return generated IDs" in result["error"]
    assert result["text_rows"][0]["text_id"] is None


def test_changed_existing_family_text_link_invalidates_approved_preview(tmp_path):
    computed = records()[:1]
    mdb = target_mdb(computed)
    path = tmp_path / "disposable.mdb"
    path.touch()
    service = PriceMdbExportService(SimpleNamespace(mdb_service=mdb))
    snapshot = Snapshot(price_records=computed)
    preview = service.export(snapshot, path, dry_run=True)
    key = next(k for k in mdb.rows if k.startswith("SELECT com_GlobalPriceID"))
    mdb.rows[key][-1]["com_TextID"] = 1777
    mdb.texts.append({"com_TextID": 1777, "com_TextName": "28"})
    result = service.export(snapshot, path, expected_plan=preview["plan_digest"])
    assert not result["ok"] and "Preview Export again" in result["error"]
    assert mdb.ops == []


def test_family_target_matching_is_case_insensitive_like_jet():
    computed = records()[:1]
    mdb = target_mdb(computed)
    key = next(k for k in mdb.rows if k.startswith("SELECT com_GlobalPriceID"))
    mdb.rows[key][-1]["com_VariantCondition"] = mdb.rows[key][-1]["com_VariantCondition"].lower()
    result = _export(mdb, computed)
    assert result["ok"] and result["updated_global_prices"] == 1
    assert result["inserted_global_prices"] == 0


def test_read_table_adapter_fetches_existing_text_link_instead_of_reporting_it_missing():
    computed = records()[:1]
    optimized = target_mdb(computed)
    key = next(k for k in optimized.rows if k.startswith("SELECT com_GlobalPriceID"))
    mdb = _RecordingMDB(_eur_gbp_lists(), globals_=optimized.rows[key], linked=[21, 22])
    read = mdb.read_table

    def read_with_texts(path, sql):
        if "FROM tCOMd_GlobalPrice" in sql:
            assert "com_TextID" in sql
        if "FROM tCOMd_Text WHERE" in sql:
            return optimized.texts
        return read(path, sql)

    mdb.read_table = read_with_texts
    result = _export(mdb, computed)
    assert result["ok"] and result["updated_global_prices"] == 1
    assert result["text_rows"][0]["text_id"] == 1101


def test_zero_source_placeholder_does_not_block_a_new_colour_target():
    computed = records()[:1]
    mdb = new_target_mdb()
    key = next(k for k in mdb.rows if k.startswith("SELECT com_GlobalPriceID"))
    mdb.rows[key].append({
        **mdb.rows[key][0], "com_GlobalPriceID": 88,
        "com_VariantCondition": f"8={ITEM}_1FD#", "com_PriceValue": "0.00",
    })
    result = _export(mdb, computed)
    assert result["ok"] and result["inserted_global_prices"] == 1


@pytest.mark.parametrize("scope", ["list", "package"])
def test_family_in_a_different_scope_does_not_replace_a_new_target(scope):
    computed = records()[:1]
    mdb = new_target_mdb()
    key = next(k for k in mdb.rows if k.startswith("SELECT com_GlobalPriceID"))
    mdb.rows[key].append({
        **mdb.rows[key][0], "com_GlobalPriceID": 88,
        "com_VariantCondition": f"28={ITEM}_1FD",
        "com_PriceListID": 22 if scope == "list" else 21,
        "com_PackageID": 2 if scope == "package" else 1,
    })
    result = _export(mdb, computed)
    assert result["ok"] and result["inserted_global_prices"] == 1
    assert result["updated_global_prices"] == 0


@pytest.mark.parametrize("problem", [
    "duplicate", "canonical", "unlinked", "dangling",
    "priced_source", "priced_hash_source",
])
def test_unsafe_target_blocks_export_instead_of_inserting_or_double_charging(problem):
    computed = records()[:1]
    mdb = target_mdb(computed)
    key = next(k for k in mdb.rows if k.startswith("SELECT com_GlobalPriceID"))
    rows = mdb.rows[key]
    if problem == "duplicate":
        rows.append({**rows[-1], "com_GlobalPriceID": 999})
    elif problem == "canonical":
        rows.append({**rows[-1], "com_GlobalPriceID": 999,
                     "com_VariantCondition": computed[0].variant_condition})
    elif problem in ("unlinked", "dangling"):
        rows[-1]["com_TextID"] = None if problem == "unlinked" else 999999
    elif problem in ("priced_source", "priced_hash_source"):
        rows[0]["com_PriceValue"] = 89.0
        if problem == "priced_hash_source":
            rows[0]["com_VariantCondition"] += "#"
    preview = _export_dry(mdb, computed)
    assert not preview["export_allowed"]
    assert preview["inserted_global_prices"] == 0
    assert preview["text_rows"][0]["action"] == "skip"
    result = _export(mdb, computed)
    assert not result["ok"] and "Fabric family target" in result["error"]
    assert mdb.ops == []


@pytest.mark.parametrize("program", ["revive", ""])
def test_normal_and_streaming_keep_identical_order_prices_and_relationships(monkeypatch, program):
    monkeypatch.setattr(PDMRepository, "get_connection", lambda self: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(PDMRepository, "fetch_item_base_prices", lambda *a, **kw: [])
    monkeypatch.setattr(PricingService, "_attach_product_codes", lambda *a: None)

    def fetch(self, items, currency, *args, **kwargs):
        rows = source_rows(items[0])
        resolve(rows)
        return rows

    monkeypatch.setattr(PDMRepository, "fetch_global_option_increment_prices", fetch)
    service = PricingService(MagicMock())
    normal_snapshot = Snapshot(product=Product(catalogue_id="658"), generation_program=program)
    normal_snapshot.article_components = {
        "parent1": [{"sub_item": ITEM}],
        "parent2": [{"sub_item": "ANOTHER.COMPONENT"}],
    }
    streaming_snapshot = replace(normal_snapshot, price_records=[])
    normal = service.compute(PriceParams(), normal_snapshot)
    batches = []
    streaming = service.compute_streaming(
        PriceParams(), streaming_snapshot, on_batch=batches.extend, batch_size=1
    )
    assert normal.records == streaming.records == batches
    assert [(r.currency, r.source_item, r.variant_condition) for r in normal.records] == [
        (cur, item, f"{item} 28={family[0]}")
        for cur in ("EUR", "GBP") for item in (ITEM, "ANOTHER.COMPONENT") for family in FAMILIES
    ]
