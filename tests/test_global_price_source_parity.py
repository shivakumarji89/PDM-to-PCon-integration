from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.errors import PDMQueryError
from models.product import Product
from models.snapshot import Snapshot
from repositories.pdm_repository import GlobalOptionPriceRow, PDMRepository
from services.pricing_service import PriceParams, PricingService
from services.snapshot_serialization import price_record_from_dict, price_record_to_dict


def source(item="GETH.1022FS4W", code="AA", option_id=9168, value="27.9", vid=299995):
    return SimpleNamespace(
        Item=item, OptionValueId=vid, OptionId=option_id,
        OrderCodeValue=f"{item}_{code}",
        RawIncrement=None if value is None else Decimal(value), PriceBand=None,
    )


def fetch(repo, *, program="", item="GETH.1022FS4W", site=1):
    return repo.fetch_global_option_increment_prices(
        [item], "GBP", "16-Oct-2026", site, object(),
        catalogue_id=660, program_code=program,
    )


@pytest.mark.parametrize("program,predicate", [
    ("lf", "Product.Product NOT LIKE 'MRF7%'"),
    ("av", "Product.Product NOT LIKE 'AS7%'"),
    ("swoop", "Product.Product LIKE 'OAW1%'"),
    ("revive", ""),
])
def test_global_query_scope_and_parameters(program, predicate):
    query, params = PDMRepository._global_price_query(
        "GETH.1022FS4W", "EUR", "16-Oct-2026", 9, 660, program
    )
    assert params == (660, 9, "EUR", "%GETH.1022FS4W%") * 2
    assert query.count("SELECT DISTINCT") == 2
    assert " UNION " in query and "UNION ALL" not in query
    assert "INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId" in query
    assert "Item.ItemId = itco.SubItemId" in query
    assert "parent_item.ItemId = ci_parent.ItemId" in query
    for clause in [
        "optval.Status = 1", "pc.SiteId = ?", "Currency.Currency = ?",
        "pm.ItemPriceCode", "fb.Application = 1",
        "WHEN pc.BasePriceRef = 1 THEN itov.IncrementalPrice",
        "WHEN pc.BasePriceRef = 2 THEN itov.IncrementalPrice2",
        "WHEN pc.BasePriceRef = 3 THEN itov.IncrementalPrice3",
    ]:
        assert query.count(clause) == 2
    assert query.count("SELECT ProductCodeIdOverride FROM Item i2") == 4
    assert predicate in query
    assert query.endswith(" ORDER BY OrderCodeValue")


def test_secondary_binds_date_and_keeps_original_base1_predicate():
    query, params = PDMRepository._global_price_query(
        "CD63NC0600", "GBP", "16-Oct-2026", 9, 172, "",
        option_value_id=33597, raw_increment=Decimal("9"),
    )
    assert params == (
        "GBP", "16-Oct-2026", 9, 172, 9, "GBP", 33597, Decimal("9"), "%CD63NC0600%"
    ) * 2
    assert query.count("optval.OptionValueId = ? AND itov.IncrementalPrice = ?") == 2
    assert "optval.Status = 1" not in query
    assert "ORDER BY" not in query


@pytest.mark.parametrize("name,raw,calculated,expected", [
    ("base1", "27.9", Decimal("47"), Decimal("47")),
    ("base2_50_vs_base1_47", "50", None, -1),
    ("base3_9_vs_null_base1", "9", None, -1),
    ("null_selected_field", None, None, None),
])
def test_secondary_value_and_missing_selected_field(name, raw, calculated, expected):
    repo = PDMRepository(MagicMock())
    calls = []

    def execute(query, params, connection=None):
        calls.append(query)
        if "AS NewPrice" not in query:
            return [source(value=raw)]
        return [] if calculated is None else [
            SimpleNamespace(Item="GETH.1022FS4W", NewPrice=calculated)
        ]

    repo._execute = execute
    rows = fetch(repo)
    assert [r.IncPrice for r in rows] == ([] if expected is None else [expected])
    assert len(calls) == (1 if raw is None else 2)


def test_source_duplicates_order_and_cache_are_not_replaced_by_dictionary():
    repo = PDMRepository(MagicMock())
    first = source()
    second = source(code="BA", vid=300275)
    calls = []

    def execute(query, params, connection=None):
        calls.append(query)
        if "AS NewPrice" not in query:
            return [first, first, second]
        return [
            SimpleNamespace(Item=first.Item, NewPrice=None),
            SimpleNamespace(Item=first.Item, NewPrice=Decimal("46")),
            SimpleNamespace(Item=first.Item, NewPrice=Decimal("47")),
        ]

    repo._execute = execute
    rows = fetch(repo)
    assert [r.OptionValueId for r in rows] == [299995, 299995, 300275]
    # Last row wins initially; IndexOf then reuses the first cached value.
    assert [r.IncPrice for r in rows] == [47, 46, 46]
    assert len(calls) == 2


def test_cache_requires_both_first_indices_to_match():
    repo = PDMRepository(MagicMock())
    secondary_calls = []

    def execute(query, params, connection=None):
        if "AS NewPrice" not in query:
            return [source(value="10"), source(value="20"), source(value="20")]
        secondary_calls.append(params[7])
        return [SimpleNamespace(Item="GETH.1022FS4W", NewPrice=params[7])]

    repo._execute = execute
    rows = fetch(repo)
    assert [r.IncPrice for r in rows] == [10, 20, 20]
    # IndexOf(item)=0 but IndexOf(20)=1; PDM recalculates the third row.
    assert secondary_calls == [10, 20, 20]


@pytest.mark.parametrize("item,program,projected,lookup,raw", [
    ("MRFN121HWAP", "lf", "ZM", "ZM", "ZM"),
    ("AS2EA32AA", "av", "1FD#", "1FD#", "1FD#"),
    ("RY3VFTB.105512F", "revive", "RY3VFTB.105512F_1FD#",
     "RY3VFTB.105512F 8=1FD#", "1FD#"),
    ("RYMPSH.12SW", "revive", "RYMPSH.12SW_OKG",
     "3848=RYMPSH.12SW_OKG", "OKG"),
    ("RYTRFA.0812SW", "revive", "RYTRFA.0812SW_OKG",
     "6027=RYTRFA.0812SW_OKG", "OKG"),
    ("WE5110L", "caper", "WE5110L 62=DS", "WE5110L 62=DS", "DS"),
    ("RZTA.", "ratio", "RZTA._DB3", "RZTA. 6867=DB3", "DB3"),
])
def test_observed_source_code_and_lookup_mappings(item, program, projected, lookup, raw):
    option_id = {
        "RYMPSH.12SW": 3848, "RYTRFA.0812SW": 6027,
        "WE5110L": 62, "RZTA.": 6867,
    }.get(item, 8)
    repo = PDMRepository(MagicMock())
    row = source(item=item, option_id=option_id)
    row.OrderCodeValue = projected

    def execute(query, params, connection=None):
        return [SimpleNamespace(Item=item, NewPrice=Decimal("47"))] if "AS NewPrice" in query else [row]

    repo._execute = execute
    result = fetch(repo, program=program, item=item)
    assert [(r.Code, r.SourceCode, r.LookupCode) for r in result] == [
        (raw, projected, lookup)
    ]


def test_we51_order_is_sql_projection_order_not_raw_code_order():
    repo = PDMRepository(MagicMock())
    rows = [
        SimpleNamespace(
            Item="WE5110L", OptionValueId=vid, OptionId=oid,
            OrderCodeValue=f"WE5110L {oid}={code}",
            RawIncrement=Decimal("10"), PriceBand=None,
        ) for vid, oid, code in [(337, 61, "MS"), (1651, 62, "DS")]
    ]
    repo._execute = lambda query, params, connection=None: (
        [SimpleNamespace(Item="WE5110L", NewPrice=Decimal("10"))]
        if "AS NewPrice" in query else rows
    )
    assert [r.Code for r in fetch(repo, item="WE5110L", program="caper")] == ["MS", "DS"]


def test_av_source_band_is_not_replaced_with_procedure_band_for_same_price():
    repo = PDMRepository(MagicMock())
    row = source(item="AS2EA32AA", vid=148810)
    row.OrderCodeValue = "TEST"
    row.PriceBand = 3
    repo._execute = lambda query, params, connection=None: (
        [SimpleNamespace(Item=row.Item, NewPrice=Decimal("47"))]
        if "AS NewPrice" in query else [row]
    )
    result = fetch(repo, item=row.Item, program="av")
    assert [(r.OptionValueId, r.PriceBand, r.IncPrice) for r in result] == [
        (148810, 3, Decimal("47"))
    ]


def test_null_projected_code_uses_pdm_empty_string_not_python_none_literal():
    repo = PDMRepository(MagicMock())
    row = source()
    row.OrderCodeValue = None
    repo._execute = lambda query, params, connection=None: (
        [SimpleNamespace(Item=row.Item, NewPrice=Decimal("47"))]
        if "AS NewPrice" in query else [row]
    )
    result = fetch(repo)
    assert (result[0].Code, result[0].SourceCode, result[0].LookupCode) == ("", "", "")


def test_scope_expanded_items_remain_global_and_keep_lookup_separate_from_target():
    row = GlobalOptionPriceRow(
        "1205S1BQI", 288124, 8704, "C", "1205S1BQI_C",
        "1205S1BQI 8704=C", Decimal("470"), None, Decimal("403"),
    )
    records, _ = PricingService.build_records(
        [], [row], {"1205S1BQ"}, {}, PriceParams(currency="GBP")
    )
    assert records[0].is_global
    assert records[0].source_item == "1205S1BQI"
    assert records[0].pdm_lookup_code == "1205S1BQI 8704=C"
    restored = price_record_from_dict(price_record_to_dict(records[0]))
    assert restored == records[0]
    assert price_record_from_dict({}).pdm_lookup_code == ""


@pytest.mark.parametrize(
    "program,item,option_id,code,source_code,lookup,condition",
    [
        ("lf", "MRFN121HWAP", 9227, "AJ", "AJ", "AJ",
         "MRFN121HWAP 9227=AJ"),
        ("av", "AS2EA32AA", 8, "1FD#", "1FD#", "1FD#",
         "AS2EA32AA 8=1FD"),
        ("embody", "CN132AWAA", 8, "AJ", "AJ", "AJ",
         "CN132AWAA 8=AJ"),
        ("layout_studio", "GETH.1022FS4W", 9168, "AA",
         "GETH.1022FS4W_AA", "GETH.1022FS4W 9168=AA",
         "GETH.1022FS4W 9168=AA"),
        ("caper", "WE5110L", 62, "DS", "WE5110L 62=DS",
         "WE5110L 62=DS",
         "WE5110L 62=DS"),
        ("revive", "RYMPSH.12SW", 3848, "OKG",
         "RYMPSH.12SW_OKG",
         "3848=RYMPSH.12SW_OKG", "RYMPSH.12SW 3848=OKG"),
        ("revive", "RYTRFA.0812SW", 6027, "OKG",
         "RYTRFA.0812SW_OKG",
         "6027=RYTRFA.0812SW_OKG", "RYTRFA.0812SW 6027=OKG"),
        ("ratio", "RZTA.", 6867, "DB3", "RZTA._DB3", "RZTA. 6867=DB3",
         "RZTA. 6867=DB3"),
        ("memo", "MEMO123", 8, "AA", "MEMO123AA", "MEMO123AA",
         "MEMO123AA"),
    ],
)
def test_global_direct_item_condition_matches_pdm_missing_record_shape(
    program, item, option_id, code, source_code, lookup, condition,
):
    row = GlobalOptionPriceRow(
        item, 1, option_id, code, source_code, lookup,
        Decimal("21"), None, Decimal("52"),
    )
    records, _ = PricingService.build_records(
        [], [row], set(), {}, PriceParams(program_code=program)
    )
    assert records[0].variant_condition == condition
    assert records[0].pdm_lookup_code == lookup


def test_component_parent_global_condition_uses_the_parent_option_target_key():
    item = "RYMPSH.12SW"
    source_code = f"{item}_OKG"
    lookup = f"3848={source_code}"
    row = GlobalOptionPriceRow(
        item, 1, 3848, "OKG", source_code, lookup,
        Decimal("21"), None, Decimal("52"),
    )

    records, _ = PricingService.build_records(
        [], [row], {item}, {}, PriceParams(program_code="revive")
    )

    assert records[0].variant_condition == lookup
    assert records[0].pdm_lookup_code == lookup


@pytest.mark.parametrize("streaming", [False, True])
def test_compute_paths_forward_snapshot_catalogue_and_program(monkeypatch, streaming):
    snapshot = Snapshot(product=Product(catalogue_id="658"))
    snapshot.generation_program = "revive"
    snapshot.article_components = {"1": [{"sub_item": "RYMPSH.12SW"}]}
    calls = []
    connection = SimpleNamespace(close=lambda: calls.append("closed"))
    monkeypatch.setattr(PDMRepository, "get_connection", lambda self: connection)
    monkeypatch.setattr(PDMRepository, "fetch_item_base_prices", lambda *a, **kw: [])
    monkeypatch.setattr(PricingService, "_attach_product_codes", lambda *a: None)

    def fetch_global(self, items, currency, mydate, site, conn, **kwargs):
        calls.append((items, currency, kwargs))
        return []

    monkeypatch.setattr(PDMRepository, "fetch_global_option_increment_prices", fetch_global)
    service = PricingService(MagicMock())
    method = service.compute_streaming if streaming else service.compute
    method(PriceParams(mydate="16-Oct-2026"), snapshot)
    assert calls == [
        (["RYMPSH.12SW"], cur, {"catalogue_id": "658", "program_code": "revive"})
        for cur in ["EUR", "GBP"]
    ] + ["closed"]


def test_missing_catalogue_fails_explicitly():
    with pytest.raises(PDMQueryError, match="selected catalogue"):
        PricingService._global_catalogue(Snapshot(), PriceParams())


def test_explicit_catalogue_overrides_snapshot_without_unscoped_fallback():
    snapshot = Snapshot(product=Product(catalogue_id="658"))
    assert PricingService._global_catalogue(snapshot, PriceParams(catalogue_id=660)) == 660


def test_comparison_preserves_duplicates_and_penalizes_missing_and_extra_rows():
    from scripts.pdm_differential.fetch_parity import compare

    expected = [("ITEM", 1, "A"), ("ITEM", 1, "A"), ("ITEM", 2, "B"),
                ("ITEM", 3, "C")]
    actual = [("ITEM", 1, "A"), ("ITEM", 2, "changed"), ("ITEM", 4, "extra")]
    result = compare(expected, actual)
    assert {name: result[name] for name in (
        "exact", "fields", "missing", "extra", "denominator", "pdm_duplicates"
    )} == {
        "exact": 1, "fields": 1, "missing": 2, "extra": 1,
        "denominator": 5, "pdm_duplicates": 1,
    }
    assert not result["order_match"]
