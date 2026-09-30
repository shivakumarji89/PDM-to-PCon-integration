from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from repositories.cancellable_pdm_repository import CancellablePDMRepository
from repositories.pdm_repository import PDMRepository, _IncPriceRow
from services.obx_validation_service import ObxLine, ObxValidationService
from services.sif_validation_service import SifLine, SifOption, SifValidationService


def _eligible_validation_repo_methods(**overrides):
    methods = {
        "find_normal_items": lambda items, **kwargs: set(items),
        "find_us_items": lambda items, **kwargs: set(),
        "fetch_validation_catalogue_ids": lambda *args, **kwargs: [17],
        "fetch_item_validation_price_context": lambda items, currency, *args, **kwargs: [
            SimpleNamespace(
                Item=item, Status=1, IsSuperProduct=0, ProductCodeId=1,
                PriceCode="PC", BasePriceRef=1, Rounding=2,
                MatchedCurrency=currency,
            )
            for item in items
        ],
        "fetch_items_valid_catalogues": lambda items, catalogue_ids, **kwargs: {
            str(item): list(catalogue_ids) for item in items
        } if catalogue_ids else {},
    }
    methods.update(overrides)
    return methods


def _superproduct_validation_repo(bom_rows, component_price_rows, increment_rows=(), option_rows=()):
    return SimpleNamespace(**_eligible_validation_repo_methods(
        fetch_item_validation_price_context=lambda items, currency, *args, **kwargs: [
            SimpleNamespace(
                Item=item, ItemId=123, Status=1, IsSuperProduct=1,
                ProductCodeId=None, PriceCode=None, BasePriceRef=None,
                Rounding=None, MatchedCurrency=None,
            )
            for item in items
        ],
        fetch_item_validation_options=lambda *args: list(option_rows),
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: pytest.fail(
            "SuperProduct parents must not use the standard base-price query"
        ),
        fetch_item_components=lambda *args, **kwargs: list(bom_rows),
        fetch_item_component_prices=lambda *args, **kwargs: list(component_price_rows),
        fetch_item_component_increment_prices=lambda *args, **kwargs: list(increment_rows),
    ))


def _us_item_context(item="USSKU", currency="USD", base=100.0):
    return SimpleNamespace(
        Item=item, ItemId=900, Status=1, IsSuperProduct=0, ProductId=-1,
        ProductCodeId=90, PriceCode="USPC", BasePriceRef=1, Rounding=2,
        MatchedCurrency=currency, BasePrice=base,
    )


def _us_increment(item, option_id, code, price):
    return SimpleNamespace(
        Item=item, OptionId=option_id, OrderCodeValue2=code,
        IncPrice=price, Quantity=1, IsFabric=0,
    )


def _us_only_validation_repo(option_rows=()):
    return SimpleNamespace(
        find_normal_items=lambda items, **kwargs: set(),
        find_us_items=lambda items, **kwargs: set(items),
        fetch_validation_catalogue_ids=lambda *args, **kwargs: pytest.fail(
            "USItem-only validation must bypass normal catalogue resolution"
        ),
        fetch_item_validation_price_context=lambda *args, **kwargs: pytest.fail(
            "USItem-only validation must bypass normal Item context"
        ),
        fetch_items_valid_catalogues=lambda *args, **kwargs: pytest.fail(
            "USItem-only validation must bypass normal catalogue eligibility"
        ),
        fetch_us_item_price_context=lambda items, currency, site_id, connection=None: [
            _us_item_context(item, currency) for item in items
        ],
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: pytest.fail(
            "USItem-only validation must not call the normal base-price API"
        ),
        fetch_item_validation_options=lambda *args, **kwargs: pytest.fail(
            "USItem-only validation bypasses VerifyOptions"
        ),
        fetch_us_item_base_prices=lambda items, *args, **kwargs: [
            SimpleNamespace(Item=item, price=100.0) for item in items
        ],
        fetch_item_us_option_increment_prices=lambda items, *args, **kwargs: [
            row for row in option_rows if row.Item in items
        ],
    )


def _option_row(code, group=1, status=1, increment=0.0, item="SKU1"):
    return SimpleNamespace(
        Item=item, OptionId=group, OptionValueId=group * 100,
        OrderCodeValue2=code, Status=status, IsFabric=0,
        IncPrice=increment, Quantity=1, ParentOptId=None,
    )


def _component_option_row(
    code, option_id, price, *, component="PART", quantity=1,
    display=1, tertiary=1, feature_positions=None,
):
    return SimpleNamespace(
        OrderCodeValue2=code, OptionId=option_id, IncPrice=price,
        CompItem=component, Quantity=quantity, DisplayOrder=display,
        TertiaryOption=tertiary, FeaturePositionString=feature_positions,
    )


def test_legacy_validation_base_price_query_uses_get_price_ext_semantics(monkeypatch):
    repo = PDMRepository(None)
    calls = []
    expected_rows = [SimpleNamespace(Item="SKU1", price=123.456)]
    monkeypatch.setattr(
        repo,
        "_execute",
        lambda query, params, connection=None: (
            calls.append((query, params, connection)) or expected_rows
        ),
    )

    rows = repo.fetch_validation_get_price_ext_base_prices(
        ["SKU1"], "EUR", "2026-09-28", connection="conn", site_id=17
    )

    query, params, connection = calls[0]
    assert rows == expected_rows
    assert rows[0].price == 123.456
    assert "dbo.fnGetListPrice(" in query
    assert "CASE WHEN pc.BasePriceRef = 2 THEN i.BasePrice2" in query
    assert "WHEN pc.BasePriceRef = 3 THEN i.BasePrice3" in query
    assert "ELSE i.BasePrice END" in query
    assert "pc.ProductCodeId = CASE" in query
    assert "i.ProductCodeIdOverride" in query
    assert "pc.SiteId = ?" in query
    assert "pm.Rounding" in query
    assert "DATEADD(SECOND, DATEDIFF(SECOND" in query
    assert "CAST(? AS datetime)" in query
    assert "'DMY'" in query
    assert params == ("2026-09-28", 17, 17, "EUR", "SKU1")
    assert connection == "conn"


def test_legacy_validation_base_price_query_leaves_missing_price_unresolved(monkeypatch):
    repo = PDMRepository(None)
    monkeypatch.setattr(repo, "_execute", lambda *args, **kwargs: [])

    assert repo.fetch_validation_get_price_ext_base_prices(
        ["MISSING"], "EUR", "2026-09-28"
    ) == []


def test_validation_catalogues_use_current_site_and_legacy_ordering(monkeypatch):
    repo = PDMRepository(None)
    calls = []
    monkeypatch.setattr(
        repo,
        "_execute",
        lambda query, params, connection=None: (
            calls.append((query, params, connection))
            or [SimpleNamespace(CatalogueId=31), SimpleNamespace(CatalogueId=32)]
        ),
    )

    catalogue_ids = repo.fetch_validation_catalogue_ids(17, connection="conn")

    query, params, connection = calls[0]
    assert catalogue_ids == [31, 32]
    assert "c.PrimarySiteId = ?" in query
    assert "c.Status <> 2" in query
    assert "ORDER BY c.LeadTime" in query
    assert "CASE WHEN c.PrimarySiteId = ? THEN 0 ELSE 1 END" in query
    assert "c.Name" in query
    assert params == (17, 17)
    assert connection == "conn"


@pytest.mark.parametrize(
    "currency, site_code, description",
    [
        ("GBP", "UK", "UK"),
        ("EUR", "UK", "UK"),
        ("HKD", "HK", "Hong Kong"),
        ("CNY", "DG", "HM Dongguan"),
        ("JPY", "JP", "Japan"),
        ("INR", "IN", "India"),
        ("BRL", "BR", "Brazil"),
        ("USD", "SG", "Singapore"),
    ],
)
def test_currency_site_resolution_uses_site_code_with_description_fallback(
    currency, site_code, description
):
    calls = []
    repo = SimpleNamespace(
        _execute=lambda query, params, connection: (
            calls.append((query, params, connection))
            or [SimpleNamespace(SiteId=3)]
        )
    )

    resolved = SifValidationService(None).site_for_currency(
        currency, repo, "conn"
    )

    query, params, connection = calls[0]
    assert resolved == 3
    assert "UPPER(Site) = UPPER(?)" in query
    assert "UPPER(Description) = UPPER(?)" in query
    assert params == (site_code, description, site_code)
    assert connection == "conn"


def test_validation_price_context_uses_selected_site_and_currency(monkeypatch):
    repo = PDMRepository(None)
    calls = []
    expected = [SimpleNamespace(Item="SKU1", Status=1, BasePriceRef=2)]
    monkeypatch.setattr(
        repo,
        "_execute",
        lambda query, params, connection=None: (
            calls.append((query, params, connection)) or expected
        ),
    )

    rows = repo.fetch_item_validation_price_context(
        ["SKU1"], "EUR", 17, connection="conn"
    )

    query, params, connection = calls[0]
    assert rows == expected
    assert "i.ProductCodeIdOverride" in query
    assert "pc.SiteId = ?" in query
    assert "PriceMatrix pm" in query
    assert "UPPER(c.Currency) = UPPER(?)" in query
    assert "pc.BasePriceRef" in query
    assert params == (17, "EUR", "SKU1")
    assert connection == "conn"


def test_validation_catalogue_eligibility_requires_item_active_category_and_range(monkeypatch):
    repo = PDMRepository(None)
    calls = []
    monkeypatch.setattr(
        repo,
        "_execute",
        lambda query, params, connection=None: (
            calls.append((query, params, connection))
            or [
                SimpleNamespace(Item="SKU1", CatalogueId=20),
                SimpleNamespace(Item="SKU1", CatalogueId=10),
            ]
        ),
    )

    eligible = repo.fetch_items_valid_catalogues(
        ["SKU1", "OUTSIDE"], [10, 20], connection="conn"
    )

    query, params, connection = calls[0]
    assert eligible == {"SKU1": [10, 20]}
    assert "INNER JOIN CatalogueItems" in query
    assert "cpc.Status = 1" in query
    assert "INNER JOIN CatalogueProductRanges" in query
    assert "c.Status <> 2" in query
    assert params == ("SKU1", "OUTSIDE", 10, 20)
    assert connection == "conn"


def test_validation_option_rows_preserve_verifyoptions_metadata():
    columns = [
        "OptionId", "OptionValueId", "OrderCodeValue2", "Status", "IsFabric",
        "IncPrice", "Quantity", "FeaturePositionString", "TertiaryOption",
    ]
    row = SimpleNamespace(
        OptionId=7, OptionValueId=71, OrderCodeValue2="RED", Status=1,
        IsFabric=0, IncPrice=12.5, Quantity=1,
        FeaturePositionString="|7|", TertiaryOption=0,
    )
    calls = []

    class Cursor:
        description = [(column,) for column in columns]

        def execute(self, query, params):
            calls.append((query, params))

        def fetchall(self):
            return [row]

        def nextset(self):
            return False

        def close(self):
            pass

    class Connection:
        def cursor(self):
            return Cursor()

    repo = PDMRepository(None)
    rows = repo.fetch_item_validation_options(
        ["SKU1"], "EUR", "2026-09-28", 17, connection=Connection()
    )

    query, params = calls[0]
    assert "PDMOptionDataReportWithIncList" in query
    assert "@excludeFabricColours = 0" in query
    assert params == ("SKU1", 17, "EUR", "2026-09-28")
    assert len(rows) == 1
    assert rows[0].Item == "SKU1"
    assert rows[0].OptionValueId == 71
    assert rows[0].Status == 1
    assert rows[0].FeaturePositionString == "|7|"
    assert rows[0].TertiaryOption == 0


def test_superproduct_component_base_query_preserves_missing_prices_and_quantity(monkeypatch):
    repo = PDMRepository(None)
    calls = []
    expected = [SimpleNamespace(
        ParentItem="SUPER", ComponentItem="PART", ComponentSequence="1",
        Quantity=2, price=50.0,
    )]
    monkeypatch.setattr(
        repo,
        "_execute",
        lambda query, params, connection=None: calls.append((query, params, connection)) or expected,
    )

    rows = repo.fetch_item_component_prices(
        ["SUPER"], "EUR", "2026-09-28", 17, connection="conn"
    )

    query, params, connection = calls[0]
    assert rows == expected
    assert "ItemComponents" in query
    assert "ic.ComponentSequence" in query
    assert "ic.Quantity" in query
    assert "LEFT JOIN Product_Code" in query
    assert "LEFT JOIN (SELECT DISTINCT pm.ItemPriceCode" in query
    assert "UPPER(c.Currency) = UPPER(?)" in query
    assert "pc.BasePriceRef = 2 THEN component.BasePrice2" in query
    assert "pc.BasePriceRef = 3 THEN component.BasePrice3" in query
    assert "pm.Rounding" in query
    assert "DATEADD(SECOND, DATEDIFF(SECOND" in query
    assert params == ("2026-09-28", 17, 17, "EUR", "SUPER")
    assert connection == "conn"



def test_superproduct_component_price_query_deduplicates_currency_matrix_rows(monkeypatch):
    repo = PDMRepository(None)
    calls = []
    expected = [SimpleNamespace(
        ParentItem="SUPER", ComponentItem="PART", ComponentSequence="1",
        Quantity=1, price=26.0,
    )]
    monkeypatch.setattr(
        repo,
        "_execute",
        lambda query, params, connection=None: (
            calls.append((query, params, connection)) or expected
        ),
    )

    rows = repo.fetch_item_component_prices(
        ["SUPER"], "GBP", "2026-09-30", 1, connection="conn"
    )

    query, params, connection = calls[0]
    assert rows == expected
    assert "SELECT DISTINCT pm.ItemPriceCode, pm.Rounding" in query
    assert "UPPER(c.Currency) = UPPER(?)" in query
    assert params == ("2026-09-30", 1, 1, "GBP", "SUPER")
    assert connection == "conn"


def test_superproduct_component_increment_query_preserves_position_metadata(monkeypatch):
    repo = PDMRepository(None)
    calls = []
    expected = [SimpleNamespace(
        ParentItem="SUPER", CompItem="PART", ComponentSequence="1",
        Quantity=2, OptionId=7, OptionValueId=71, DisplayOrder=1,
        TertiaryOption=1, FeaturePositionString="|7|", DisplayOrdinal=1,
        OrderCodeValue2="RED", IncPrice=5.0,
    )]
    monkeypatch.setattr(
        repo,
        "_execute",
        lambda query, params, connection=None: calls.append((query, params, connection)) or expected,
    )

    rows = repo.fetch_item_component_increment_prices(
        ["SUPER"], "EUR", "2026-09-28", 17, connection="conn"
    )

    query, params, connection = calls[0]
    assert rows == expected
    assert "ItemOptionValues" in query
    assert "FeaturePositionString" in query
    assert "TertiaryOption" in query
    assert "opt.DisplayOrder" in query
    assert "ov.DisplayOrdinal" in query
    assert "IncrementalPrice2" in query
    assert "IncrementalPrice3" in query
    assert "ORDER BY parent.Item, CONVERT(INT, itco.ComponentSequence)" in query
    assert params == ("2026-09-28", 17, 17, "EUR", "SUPER")
    assert connection == "conn"


def test_normal_and_usitem_domains_are_resolved_separately(monkeypatch):
    repo = PDMRepository(None)
    calls = []

    def execute(query, params, connection=None):
        calls.append((query, params))
        if "FROM Item i" in query:
            return [SimpleNamespace(Item="NORMAL"), SimpleNamespace(Item="COLLISION")]
        return [SimpleNamespace(USItem="USONLY"), SimpleNamespace(USItem="COLLISION")]

    monkeypatch.setattr(repo, "_execute", execute)

    normal = repo.find_normal_items(["NORMAL", "USONLY", "COLLISION"])
    us_items = repo.find_us_items(["NORMAL", "USONLY", "COLLISION"])

    assert normal == {"NORMAL", "COLLISION"}
    assert us_items == {"USONLY", "COLLISION"}
    assert "FROM Item i" in calls[0][0]
    assert "FROM USItem u" in calls[1][0]


def test_usitem_context_and_base_query_keep_us_pricing_separate(monkeypatch):
    repo = PDMRepository(None)
    calls = []

    def execute(query, params, connection=None):
        calls.append((query, params, connection))
        if "AS MatchedCurrency" in query:
            return [SimpleNamespace(Item="USONLY", BasePrice=100.0)]
        return [SimpleNamespace(Item="USONLY", price=125.0)]

    monkeypatch.setattr(repo, "_execute", execute)
    context = repo.fetch_us_item_price_context(["USONLY"], "USD", 3, "conn")
    prices = repo.fetch_us_item_base_prices(
        ["USONLY"], "USD", "2026-09-28", 3, connection="conn"
    )

    context_query, context_params, _ = calls[0]
    base_query, base_params, _ = calls[1]
    assert context[0].BasePrice == 100.0
    assert prices[0].price == 125.0
    assert "FROM USItem u" in context_query
    assert "u.Product_Code = pc.Product_Code" in context_query
    assert context_params == (3, "USD", "USONLY")
    assert "dbo.fnGetListPrice(c.Currency, u.BasePrice, pc.PriceCode" in base_query
    assert "DATEADD(SECOND, DATEDIFF(SECOND" in base_query
    assert base_params == ("2026-09-28", 3, 3, "USD", "USONLY")


def test_usitem_increment_query_combines_direct_and_dependent_sources(monkeypatch):
    repo = PDMRepository(None)
    calls = []
    expected = [SimpleNamespace(Item="USONLY", OrderCodeValue2="RED", IncPrice=10.0)]
    monkeypatch.setattr(
        repo,
        "_execute",
        lambda query, params, connection=None: calls.append((query, params, connection)) or expected,
    )

    rows = repo.fetch_item_us_option_increment_prices(
        ["USONLY"], "USD", "2026-09-28", 3, connection="conn"
    )

    query, params, connection = calls[0]
    assert rows == expected
    assert "USItemOptionValues" in query
    assert "uitov.IncrementalPrice" in query
    assert "UNION" in query
    assert "USDependentOptionValues" in query
    assert "udov.CommonIncrementalPrice" in query
    assert query.count("DATEADD(SECOND, DATEDIFF(SECOND") == 2
    assert params == (
        "2026-09-28", 3, 3, "USD", "USONLY",
        "2026-09-28", 3, 3, "USD", "USONLY",
    )
    assert connection == "conn"


@pytest.mark.parametrize("obx", [False, True])
def test_usitem_direct_and_dependent_increments_price_through_usdata(obx, monkeypatch):
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    option_rows = [
        _us_increment("USSKU", 10, "RED", 5.0),
        _us_increment("USSKU", 20, "BLUE", 7.0),
    ]
    repo = _us_only_validation_repo(option_rows)
    if obx:
        line = ObxLine(
            seq=1, base_article="USSKU", final_article="USSKU RED BLUE",
            currency="USD", obx_price=112.0,
        )
    else:
        line = SifLine(
            seq=1, base="USSKU", currency="USD", pl=100.0,
            options=[SifOption(code="RED", ol=5.0), SifOption(code="BLUE", ol=7.0)],
        )

    results = service._validate_group(
        "USD", [line], 3, repo, None, "2026-09-28", [0], 1,
        None, None, obx=obx,
    )

    assert results[0].status == "ok"
    assert results[0].pdm_price == 112.0


@pytest.mark.parametrize("obx", [False, True])
def test_usitem_repeated_direct_dependent_code_consumes_distinct_groups(obx, monkeypatch):
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    repo = _us_only_validation_repo([
        _us_increment("USSKU", 10, "RED", 5.0),
        _us_increment("USSKU", 20, "RED", 7.0),
    ])
    if obx:
        line = ObxLine(
            seq=1, base_article="USSKU", final_article="USSKU RED RED",
            currency="USD", obx_price=112.0,
        )
    else:
        line = SifLine(
            seq=1, base="USSKU", currency="USD", pl=100.0,
            options=[SifOption(code="RED", ol=5.0), SifOption(code="RED", ol=7.0)],
        )

    results = service._validate_group(
        "USD", [line], 3, repo, None, "2026-09-28", [0], 1,
        None, None, obx=obx,
    )

    assert results[0].status == "ok"
    assert results[0].pdm_price == 112.0


def test_normal_item_wins_when_code_exists_in_both_item_domains(monkeypatch):
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    normal_context = SimpleNamespace(
        Item="COLLISION", ItemId=123, Status=1, IsSuperProduct=0,
        ProductCodeId=1, PriceCode="PC", BasePriceRef=1,
        Rounding=2, MatchedCurrency="EUR",
    )
    repo = SimpleNamespace(
        find_normal_items=lambda items, **kwargs: {"COLLISION"},
        find_us_items=lambda items, **kwargs: {"COLLISION"},
        fetch_validation_catalogue_ids=lambda *args, **kwargs: [17],
        fetch_item_validation_price_context=lambda *args, **kwargs: [normal_context],
        fetch_us_item_price_context=lambda *args, **kwargs: pytest.fail(
            "normal Item must win a domain collision"
        ),
        fetch_items_valid_catalogues=lambda items, *args, **kwargs: {
            "COLLISION": [17]
        },
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: [
            SimpleNamespace(Item="COLLISION", price=100.0)
        ],
        fetch_us_item_base_prices=lambda *args, **kwargs: pytest.fail(
            "normal Item must use normal base pricing"
        ),
    )
    line = SifLine(seq=1, base="COLLISION", currency="EUR", pl=100.0)

    results = service._validate_group(
        "EUR", [line], 17, repo, None, "2026-09-28", [0], 1, None, None
    )

    assert results[0].status == "ok"
    assert results[0].pdm_price == 100.0


def test_missing_usitem_and_normal_item_remains_unresolved(monkeypatch):
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    repo = SimpleNamespace(
        find_normal_items=lambda items, **kwargs: set(),
        find_us_items=lambda items, **kwargs: set(),
        fetch_validation_catalogue_ids=lambda *args, **kwargs: [17],
        fetch_item_validation_price_context=lambda *args, **kwargs: [],
        fetch_items_valid_catalogues=lambda *args, **kwargs: {},
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: pytest.fail(
            "missing item must not be priced"
        ),
    )
    line = SifLine(seq=1, base="MISSING", currency="EUR", pl=100.0)

    results = service._validate_group(
        "EUR", [line], 17, repo, None, "2026-09-28", [0], 1, None, None
    )

    assert results[0].status == "unresolved"
    assert "validation catalogue scope" in results[0].message


def test_usitem_without_base_or_matrix_data_is_unresolved(monkeypatch):
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    repo = _us_only_validation_repo()
    repo.fetch_us_item_price_context = lambda items, currency, site_id, connection=None: [
        _us_item_context(item, currency, base=None) for item in items
    ]
    repo.fetch_us_item_base_prices = lambda *args, **kwargs: pytest.fail(
        "incomplete USItem context must fail before base pricing"
    )
    line = SifLine(seq=1, base="USSKU", currency="USD", pl=100.0)

    results = service._validate_group(
        "USD", [line], 3, repo, None, "2026-09-28", [0], 1, None, None
    )

    assert results[0].status == "unresolved"
    assert "incomplete USItem price context" in results[0].message


def test_cancellable_validation_option_rows_are_cached(monkeypatch):
    class Control:
        def register_cancel_handler(self, callback):
            pass

        def unregister_cancel_handler(self, callback):
            pass

    class Connection:
        def close(self):
            pass

    row = _IncPriceRow("SKU1", _option_row("RED"))
    calls = []
    monkeypatch.setattr(
        CancellablePDMRepository, "get_connection", lambda self: Connection()
    )

    def fetch_options(self, items, currency, mydate, site_id, connection=None):
        calls.append((tuple(items), currency, mydate, site_id))
        return [row]

    monkeypatch.setattr(PDMRepository, "fetch_item_validation_options", fetch_options)
    repo = CancellablePDMRepository(None, Control(), {})

    first = repo.fetch_item_validation_options(["SKU1"], "EUR", "2026-09-28", 17)
    second = repo.fetch_item_validation_options(["SKU1"], "EUR", "2026-09-28", 17)

    assert first == second == [row]
    assert calls == [(('SKU1',), "EUR", "2026-09-28", 17)]


def test_stale_skipped_option_state_does_not_skip_later_optionless_line(monkeypatch):
    service = SifValidationService(None)
    service._PRICE_WINDOW = 1
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    repo = SimpleNamespace(**_eligible_validation_repo_methods(
        fetch_item_validation_options=lambda *args: [_option_row("RED", item="SKU1")],
        fetch_validation_get_price_ext_base_prices=lambda items, *args, **kwargs: [
            SimpleNamespace(Item=item, price=100.0) for item in items
        ],
    ))
    repo.last_skipped_option_items = ["SKU1"]
    lines = [
        SifLine(seq=1, base="SKU1", currency="EUR", pl=100.0,
                options=[SifOption(code="RED")]),
        SifLine(seq=2, base="SKU1", currency="EUR", pl=100.0),
    ]

    results = service._validate_group(
        "EUR", lines, 17, repo, None, "2026-09-28", [0], 2, None, None
    )

    assert [result.seq for result in results] == [2]
    assert results[0].status == "ok"


def test_verifyoptions_accepts_exact_and_prefix_codes():
    assert SifValidationService._verify_selected_options(
        [_option_row("RED"), _option_row("1HA#", group=2)],
        ["RED", "1HA01"],
    ) is None


def test_verifyoptions_prefers_exact_then_longest_overlapping_prefix():
    values = {"AB#": object(), "ABC#": object(), "ABC01": object()}

    assert SifValidationService._increment_key_match("ABC01", values) == "ABC01"
    assert SifValidationService._increment_key_match("ABC02", values) == "ABC#"


@pytest.mark.parametrize(
    "rows",
    [
        [_option_row("RED", status=2)],
        [],
    ],
)
def test_verifyoptions_rejects_inactive_and_missing_codes(rows):
    error = SifValidationService._verify_selected_options(rows, ["RED"])

    assert error is not None
    assert "position 1" in error


def test_verifyoptions_consumes_option_groups_for_repeated_codes():
    rows = [_option_row("RED", group=10), _option_row("RED", group=20)]

    assert SifValidationService._verify_selected_options(rows, ["RED", "RED"]) is None
    assert "position 2" in SifValidationService._verify_selected_options(
        rows[:1], ["RED", "RED"]
    )


def test_verifyoptions_accepts_active_codes_with_zero_or_null_increment():
    rows = [
        _option_row("FREE", group=10, increment=0.0),
        _option_row("INCLUDED", group=20, increment=None),
    ]

    assert SifValidationService._verify_selected_options(
        rows, ["FREE", "INCLUDED"]
    ) is None


def test_verifyoptions_excludes_dependent_fabric_colour_rows_but_accepts_their_band():
    rows = [
        _option_row("1HA#", group=10),
        SimpleNamespace(
            Item="SKU1", OptionId=10, OrderCodeValue2="1HA01", Status=1,
            IsFabric=2, IncPrice=25.0,
        ),
    ]

    assert SifValidationService._verify_selected_options(rows, ["1HA01"]) is None
    assert "invalid option string" in SifValidationService._verify_selected_options(
        [rows[1]], ["1HA01"]
    )


def test_component_increment_matching_uses_positions_across_components_and_quantity():
    rows = [
        _component_option_row("RED", 10, 5.0, component="PART-A", quantity=2),
        _component_option_row(
            "BLUE", 20, 7.0, component="PART-B", quantity=3,
            display=2, tertiary=2,
        ),
    ]

    assert SifValidationService._match_component_increments(
        rows, ["RED", "BLUE"], "SUPER"
    ) == 31.0


def test_component_increment_matching_uses_feature_position_mapping():
    rows = [
        _component_option_row("RED", 10, 5.0),
        _component_option_row(
            "BLUE", 20, 7.0, display=0, tertiary=0,
            component="PART-B", feature_positions="10|20|",
        ),
    ]

    assert SifValidationService._match_component_increments(
        rows, ["RED", "BLUE"], "SUPER"
    ) == 12.0


def test_component_increment_matching_consumes_repeated_codes_without_duplicate_charge():
    repeated_groups = [
        _component_option_row("RED", 10, 5.0, component="PART-A"),
        _component_option_row(
            "RED", 20, 7.0, component="PART-B", display=2, tertiary=2
        ),
    ]
    duplicate_group = [
        _component_option_row("RED", 10, 5.0, component="PART-A"),
        _component_option_row(
            "RED", 10, 7.0, component="PART-B", display=2, tertiary=2
        ),
    ]

    assert SifValidationService._match_component_increments(
        repeated_groups, ["RED", "RED"], "SUPER"
    ) == 12.0
    assert SifValidationService._match_component_increments(
        duplicate_group, ["RED", "RED"], "SUPER"
    ) == 5.0


@pytest.mark.parametrize(
    "item, option_id, display, expected",
    [
        ("YH304SUPER", "6733", 1, (3, 1)),
        ("YI303SUPER", "6768", 1, (3, 1)),
        ("NOFTE123", "6820", 3, (1, 1)),
        ("NODLE140", "6699", 4, (1, 1)),
        ("NODLE240", "6695", 4, (2, 1)),
        ("EX1CHAIR", "1206", 1, (3, 1)),
        ("OAW30SUPER", "3278", 4, (1, 1)),
        ("OAW30SUPER", "3716", 4, (2, 1)),
        ("HECHAIR", "3765", 1, (3, 1)),
        ("HECHAIR", "3761", 1, (4, 1)),
        ("AS4SUPER", "500", 3, (1, 1)),
        ("AS1SUPER", "500", 2, (2, 2)),
    ],
)
def test_component_matching_applies_audited_display_overrides(
    item, option_id, display, expected
):
    assert SifValidationService._legacy_component_display_override(
        item, option_id, display
    ) == expected


def test_component_matching_applies_audited_of_product_deferred_increment():
    rows = [
        _component_option_row("FAB", 3344, 30.0),
        _component_option_row("FIN", 8, 20.0, display=2, tertiary=2),
    ]

    assert SifValidationService._match_component_increments(
        rows, ["FAB", "FIN"], "OFCHAIR2"
    ) == 30.0


@pytest.mark.parametrize(
    "bom_rows, component_rows, expected",
    [
        (
            [SimpleNamespace(ParentItemId=123, SubItem="PART-A", Quantity=2, ComponentSequence="1")],
            [SimpleNamespace(ParentItem="SUPER", ComponentItem="PART-A", Quantity=2, ComponentSequence="1", price=50.0)],
            100.0,
        ),
        (
            [
                SimpleNamespace(ParentItemId=123, SubItem="PART-A", Quantity=2, ComponentSequence="1"),
                SimpleNamespace(ParentItemId=123, SubItem="PART-B", Quantity=3, ComponentSequence="2"),
            ],
            [
                SimpleNamespace(ParentItem="SUPER", ComponentItem="PART-A", Quantity=2, ComponentSequence="1", price=10.0),
                SimpleNamespace(ParentItem="SUPER", ComponentItem="PART-B", Quantity=3, ComponentSequence="2", price=5.0),
            ],
            35.0,
        ),
    ],
)
def test_superproduct_validation_prices_component_totals_and_quantities(
    monkeypatch, bom_rows, component_rows, expected
):
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    repo = _superproduct_validation_repo(bom_rows, component_rows)
    line = SifLine(seq=1, base="SUPER", currency="EUR", pl=expected)

    results = service._validate_group(
        "EUR", [line], 17, repo, None, "2026-09-28", [0], 1, None, None
    )

    assert results[0].status == "ok"
    assert results[0].pdm_price == expected


def test_superproduct_missing_component_price_is_unresolved_not_zero(monkeypatch):
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    bom_rows = [
        SimpleNamespace(ParentItemId=123, SubItem="PART-A", Quantity=1, ComponentSequence="1")
    ]
    component_rows = [
        SimpleNamespace(
            ParentItem="SUPER", ComponentItem="PART-A", Quantity=1,
            ComponentSequence="1", price=None,
        )
    ]
    repo = _superproduct_validation_repo(bom_rows, component_rows)
    line = SifLine(seq=1, base="SUPER", currency="EUR", pl=0.0)

    results = service._validate_group(
        "EUR", [line], 17, repo, None, "2026-09-28", [0], 1, None, None
    )

    assert results[0].status == "unresolved"
    assert results[0].pdm_price is None
    assert "component price" in results[0].message


def test_superproduct_option_increment_uses_component_position_and_quantity(monkeypatch):
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    bom_rows = [
        SimpleNamespace(ParentItemId=123, SubItem="PART-A", Quantity=1, ComponentSequence="1")
    ]
    component_rows = [
        SimpleNamespace(
            ParentItem="SUPER", ComponentItem="PART-A", Quantity=1,
            ComponentSequence="1", price=100.0,
        )
    ]
    increment_rows = [SimpleNamespace(
        ParentItem="SUPER", CompItem="PART-A", OptionId=20,
        OrderCodeValue2="RED", IncPrice=5.0, Quantity=2,
        DisplayOrder=0, TertiaryOption=0, FeaturePositionString="20|",
    )]
    repo = _superproduct_validation_repo(
        bom_rows, component_rows, increment_rows,
        option_rows=[_option_row("RED", group=20, increment=10.0, item="SUPER")],
    )
    line = SifLine(
        seq=1, base="SUPER", currency="EUR", pl=100.0,
        options=[SifOption(code="RED", ol=10.0)],
    )

    results = service._validate_group(
        "EUR", [line], 17, repo, None, "2026-09-28", [0], 1, None, None
    )

    assert results[0].status == "ok", results[0].message
    assert results[0].pdm_price == 110.0


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2026-09-28", "2026-09-28"),
        ("28-Sep-2026", "2026-09-28"),
        ("28 Sep 2026", "2026-09-28"),
        ("28/09/2026", "2026-09-28"),
        ("2027-01-05", "2027-01-05"),
        (date(2026, 9, 28), "2026-09-28"),
        (datetime(2026, 9, 28, 14, 5, 6), "2026-09-28 14:05:06"),
        ("2026-09-28T14:05:06", "2026-09-28 14:05:06"),
    ],
)
def test_validation_date_normalization(value, expected):
    assert SifValidationService._normalise_pricing_date(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "", "31/02/2026", "01-02-2026", "2026/09/28",
        datetime(2026, 9, 28, tzinfo=timezone.utc),
    ],
)
def test_validation_date_normalization_rejects_invalid_or_ambiguous_values(value):
    with pytest.raises(ValueError, match="invalid validation date"):
        SifValidationService._normalise_pricing_date(value)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("30-Sep-2026", True),
        ("2026-09-27", False),
        ("30/09/2026", True),
        (datetime(2026, 9, 28, 23, 59), False),
    ],
)
def test_future_price_date_comparison_reuses_validation_normalization(value, expected):
    assert SifValidationService._is_future_date(value, "28 Sep 2026") is expected


def test_future_price_date_comparison_rejects_invalid_values():
    with pytest.raises(ValueError, match="invalid validation date"):
        SifValidationService._is_future_date("01-02-2026", "28 Sep 2026")


def test_sif_validation_uses_legacy_base_price_path_and_keeps_option_increments(monkeypatch):
    service = SifValidationService(None)
    calls = []
    repo = SimpleNamespace(
        **_eligible_validation_repo_methods(),
        get_connection=lambda: object(),
        _execute=lambda query, params, connection: [SimpleNamespace(d="28 Sep 2026")],
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: (
            calls.append((args, kwargs)) or [SimpleNamespace(Item="SKU1", price=100.0)]
        ),
        fetch_item_validation_options=lambda *args: [
            _IncPriceRow("SKU1", SimpleNamespace(
                OptionId=1, OptionValueId=101, OrderCodeValue2="RED",
                Status=1, IncPrice=5.0,
                IsFabric=0, Quantity=1, ParentOptId=None,
            ))
        ],
    )
    scope_calls = []
    repo.fetch_validation_catalogue_ids = lambda site_id, connection=None: (
        scope_calls.append(("scope", site_id)) or [17]
    )
    repo.fetch_item_validation_price_context = lambda items, currency, site_id, connection=None: (
        scope_calls.append(("price_context", currency, site_id))
        or _eligible_validation_repo_methods()["fetch_item_validation_price_context"](
            items, currency, site_id, connection=connection
        )
    )
    monkeypatch.setattr("repositories.pdm_repository.PDMRepository", lambda context: repo)
    monkeypatch.setattr(service, "site_for_currency", lambda *args, **kwargs: 17)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    line = SifLine(
        seq=1, base="SKU1", currency="EUR", pl=100.0,
        options=[SifOption(code="RED", ol=5.0)],
    )

    sites, results = service.validate("EUR", [line], validation_date="28-Sep-2026")

    assert sites == {"EUR": 17}
    assert ("scope", 17) in scope_calls
    assert ("price_context", "EUR", 17) in scope_calls
    assert len(calls) == 1
    assert calls[0][0][2] == "2026-09-28"
    assert results[0].pdm_price == 105.0
    assert results[0].status == "ok"


def test_sif_verifies_options_without_ol_without_changing_base_only_pricing(monkeypatch):
    service = SifValidationService(None)
    option_rows = [_option_row("RED", increment=25.0)]
    repo = SimpleNamespace(**_eligible_validation_repo_methods(
        fetch_item_validation_options=lambda *args: option_rows,
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: [
            SimpleNamespace(Item="SKU1", price=100.0)
        ],
    ))
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    line = SifLine(
        seq=1, base="SKU1", currency="EUR", pl=100.0,
        options=[SifOption(code="RED", ol=0.0)],
    )

    results = service._validate_group(
        "EUR", [line], 17, repo, None, "2026-09-28", [0], 1, None, None
    )

    assert results[0].status == "ok"
    assert results[0].pdm_price == 100.0


def test_sif_prices_only_active_rows_from_shared_option_data(monkeypatch):
    service = SifValidationService(None)
    option_rows = [
        _IncPriceRow("SKU1", SimpleNamespace(
            OptionId=1, OptionValueId=101, OrderCodeValue2="RED", Status=1,
            IncPrice=10.0, IsFabric=0, Quantity=1,
        )),
        _IncPriceRow("SKU1", SimpleNamespace(
            OptionId=1, OptionValueId=102, OrderCodeValue2="RED", Status=2,
            IncPrice=99.0, IsFabric=0, Quantity=1,
        )),
    ]
    repo = SimpleNamespace(**_eligible_validation_repo_methods(
        fetch_item_validation_options=lambda *args: option_rows,
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: [
            SimpleNamespace(Item="SKU1", price=100.0)
        ],
    ))
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    line = SifLine(
        seq=1, base="SKU1", currency="EUR", pl=100.0,
        options=[SifOption(code="RED", ol=10.0)],
    )

    results = service._validate_group(
        "EUR", [line], 17, repo, None, "2026-09-28", [0], 1, None, None
    )

    assert results[0].status == "ok"
    assert results[0].pdm_price == 110.0


def test_sif_validation_rejects_invalid_date_before_base_price_lookup(monkeypatch):
    service = SifValidationService(None)
    base_price_calls = []
    repo = SimpleNamespace(
        get_connection=lambda: object(),
        _execute=lambda query, params, connection: [SimpleNamespace(d="28 Sep 2026")],
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: (
            base_price_calls.append(args)
        ),
    )
    monkeypatch.setattr("repositories.pdm_repository.PDMRepository", lambda context: repo)
    line = SifLine(seq=1, base="SKU1", currency="EUR", pl=100.0)

    with pytest.raises(ValueError, match="invalid validation date"):
        service.validate("EUR", [line], validation_date="01-02-2026")

    assert base_price_calls == []


def test_sif_validation_reports_unresolved_legacy_base_price(monkeypatch):
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    repo = SimpleNamespace(
        **_eligible_validation_repo_methods(),
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: [],
    )
    line = SifLine(seq=1, base="MISSING", currency="EUR", pl=100.0)

    results = service._validate_group(
        "EUR", [line], 17, repo, None, "2026-09-28", [0], 1, None, None
    )

    assert results[0].status == "unresolved"
    assert results[0].pdm_price is None
    assert "unable to resolve SKU" in results[0].message


def test_sif_validation_rejects_item_outside_validation_catalogue(monkeypatch):
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    repo = SimpleNamespace(**_eligible_validation_repo_methods(
        fetch_items_valid_catalogues=lambda *args, **kwargs: {},
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: pytest.fail(
            "ineligible item must not be priced"
        ),
    ))
    line = SifLine(seq=1, base="OUTSIDE", currency="EUR", pl=100.0)

    results = service._validate_group(
        "EUR", [line], 17, repo, None, "2026-09-28", [0], 1, None, None
    )

    assert results[0].status == "unresolved"
    assert "validation catalogue scope" in results[0].message


def test_sif_validation_reports_unresolved_when_site_has_no_catalogue_context(monkeypatch):
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    repo = SimpleNamespace(**_eligible_validation_repo_methods(
        fetch_validation_catalogue_ids=lambda *args, **kwargs: [],
        fetch_items_valid_catalogues=lambda *args, **kwargs: pytest.fail(
            "empty catalogue context must not issue a membership query"
        ),
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: pytest.fail(
            "unresolved catalogue context must stop pricing"
        ),
    ))
    line = SifLine(seq=1, base="SKU1", currency="EUR", pl=100.0)

    results = service._validate_group(
        "EUR", [line], 17, repo, None, "2026-09-28", [0], 1, None, None
    )

    assert results[0].status == "unresolved"
    assert "validation catalogue scope" in results[0].message


@pytest.mark.parametrize(
    "context, expected_message",
    [
        (SimpleNamespace(Item="SKU1", Status=2, IsSuperProduct=0), "inactive"),
        (
            SimpleNamespace(
                Item="SKU1", Status=1, IsSuperProduct=0, ProductCodeId=1,
                PriceCode="PC", Rounding=2, MatchedCurrency="EUR",
            ),
            "incomplete price matrix",
        ),
    ],
)
def test_sif_validation_rejects_inactive_or_incomplete_item_context(
    monkeypatch, context, expected_message
):
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    repo = SimpleNamespace(**_eligible_validation_repo_methods(
        fetch_item_validation_price_context=lambda *args, **kwargs: [context],
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: pytest.fail(
            "invalid item context must not be priced"
        ),
    ))
    line = SifLine(seq=1, base="SKU1", currency="EUR", pl=100.0)

    results = service._validate_group(
        "EUR", [line], 17, repo, None, "2026-09-28", [0], 1, None, None
    )

    assert results[0].status == "unresolved"
    assert expected_message in results[0].message


def test_sif_and_obx_share_option_code_validation(monkeypatch):
    service = SifValidationService(None)
    repo = SimpleNamespace(**_eligible_validation_repo_methods(
        fetch_item_validation_options=lambda *args: [_option_row("BLUE")],
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: pytest.fail(
            "invalid selected option must fail before base pricing"
        ),
    ))
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    sif_line = SifLine(
        seq=1, base="SKU1", currency="EUR", pl=100.0,
        options=[SifOption(code="RED")],
    )
    obx_line = ObxLine(
        seq=1, base_article="SKU1", final_article="SKU1 RED",
        currency="EUR", obx_price=100.0,
    )

    sif_result = service._validate_group(
        "EUR", [sif_line], 17, repo, None, "2026-09-28", [0], 1,
        None, None, obx=False,
    )[0]
    obx_result = service._validate_group(
        "EUR", [obx_line], 17, repo, None, "2026-09-28", [0], 1,
        None, None, obx=True,
    )[0]

    assert sif_result.status == obx_result.status == "unresolved"
    assert sif_result.message == obx_result.message


def test_obx_validation_continues_through_shared_sif_repricing():
    calls = []

    class PricingSpy:
        def validate(self, *args, **kwargs):
            calls.append((args, kwargs))
            return ({"EUR": 17}, [])

    service = ObxValidationService(SimpleNamespace(sif_validation_service=PricingSpy()))
    line = ObxLine(
        seq=1, base_article="SKU1", final_article="SKU1 RED",
        currency="EUR", obx_price=105.0,
    )

    service.validate("EUR", [line], site=17, validation_date="28-Sep-2026")

    assert len(calls) == 1
    assert calls[0][0][1] == [line]
    assert calls[0][1]["obx"] is True
    assert calls[0][1]["validation_date"] == "28-Sep-2026"


def test_obx_uses_sale_price_with_pd_1():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle basketId="1" itemType="BasketArticle">
        <artNr type="base">ABC</artNr>
        <artNr type="final">ABC RED</artNr>
        <itemPrice type="purchase" currency="EUR" value="80"/>
        <itemPrice type="sale" pd="0" currency="EUR" value="90"/>
        <itemPrice type="sale" pd="1" currency="EUR" value="100"/>
      </bskArticle>
    </root>
    """
    currency, lines = service.parse_obx(xml)

    assert currency == "EUR"
    assert len(lines) == 1
    assert lines[0].obx_price == 100.0
    assert lines[0].currency == "EUR"


def test_obx_ignores_partial_planning_articles():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle basketId="partial" itemType="BasketPartialPlanning">
        <artNr type="base">PARTIAL</artNr>
        <artNr type="final">PARTIAL RED</artNr>
        <itemPrice type="sale" pd="1" currency="EUR" value="999"/>
      </bskArticle>
      <bskArticle basketId="main" itemType="BasketArticle">
        <artNr type="base">MAIN</artNr>
        <artNr type="final">MAIN BLUE</artNr>
        <itemPrice type="sale" pd="1" currency="EUR" value="100"/>
      </bskArticle>
    </root>
    """
    currency, lines = service.parse_obx(xml)

    assert currency == "EUR"
    assert len(lines) == 1
    assert lines[0].base == "MAIN"
    assert lines[0].obx_price == 100.0
    assert lines[0].seq == 1


def test_obx_parent_does_not_inherit_child_price():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle basketId="parent" itemType="BasketAggregate">
        <artNr type="base">PARENT</artNr>
        <artNr type="final">PARENT BASE</artNr>
        <itemPrice type="sale" pd="1" currency="EUR" value="100"/>
        <bskArticle basketId="child" itemType="BasketArticle">
          <artNr type="base">CHILD</artNr>
          <artNr type="final">CHILD RED</artNr>
          <itemPrice type="sale" pd="1" currency="EUR" value="25"/>
        </bskArticle>
      </bskArticle>
    </root>
    """
    currency, lines = service.parse_obx(xml)

    assert currency == "EUR"
    assert [line.base for line in lines] == ["PARENT", "CHILD"]
    assert [line.obx_price for line in lines] == [100.0, 25.0]


def test_sif_prefers_specific_prefix_band():
    inc = {
        "1H#": (10.0, 1, 1),
        "1HA#": (25.0, 1, 1),
    }

    assert SifValidationService._match_inc(inc, "1HA01") == 25.0


def test_sif_uses_two_character_prefix_when_no_three_character_band():
    inc = {
        "1H#": (10.0, 1, 1),
    }

    assert SifValidationService._match_inc(inc, "1HA01") == 10.0


def test_obx_does_not_fallback_to_purchase_or_pd0_when_sale_pd1_is_missing():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle itemType="BasketArticle">
        <artNr type="base">ABC</artNr>
        <artNr type="final">ABC RED</artNr>
        <itemPrice type="purchase" currency="EUR" value="80"/>
        <itemPrice type="sale" pd="0" currency="EUR" value="90"/>
      </bskArticle>
    </root>
    """
    currency, lines = service.parse_obx(xml)

    assert currency == ""
    assert len(lines) == 1
    assert lines[0].currency == ""
    assert lines[0].obx_price == 0.0


def test_obx_non_finite_sale_price_is_not_accepted():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle itemType="BasketArticle">
        <artNr type="base">ABC</artNr>
        <artNr type="final">ABC RED</artNr>
        <itemPrice type="sale" pd="1" currency="EUR" value="NaN"/>
      </bskArticle>
    </root>
    """
    currency, lines = service.parse_obx(xml)

    assert currency == "EUR"
    assert len(lines) == 1
    assert lines[0].obx_price == 0.0


def test_sif_price_is_base_plus_explicit_option_line_amounts():
    service = SifValidationService(None)
    sif = """
    PZ=EUR
    PN=ABC
    PL=100.00
    SP=999.00
    ON=RED
    OL=12.50
    ON=BLUE
    OL=7.50
    SL=END OF FILE
    """
    currency, lines = service.parse_sif(sif)

    assert currency == "EUR"
    assert len(lines) == 1
    assert lines[0].sif_price == 120.0


def test_obx_selected_options_are_represented_as_priced_codes():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle itemType="BasketArticle">
        <artNr type="base">NODLE140</artNr>
        <artNr type="final">NODLE140 OAK WSE 1HA01</artNr>
        <feature name="PLC" value="DESK"/>
        <feature name="DERIVED" value="NOT_A_PRICED_OPTION"/>
        <itemPrice type="sale" pd="1" currency="EUR" value="250"/>
      </bskArticle>
    </root>
    """
    currency, lines = service.parse_obx(xml)

    assert currency == "EUR"
    assert len(lines) == 1
    assert lines[0].base == "NODLE140"
    assert [option.code for option in lines[0].options] == ["OAK", "WSE", "1HA01"]
    assert lines[0].plc == "DESK"
    assert "DERIVED" in lines[0].features


def test_obx_option_group_matching_consumes_each_pdm_group_once():
    groups = {
        "10": {"RED": (20.0, 1)},
        "20": {"RED": (35.0, 1)},
    }

    assert SifValidationService._match_inc_groups(groups, ["RED", "RED"]) == 55.0


def test_obx_repeated_wfk_uses_priced_group_quantity_not_null_group():
    groups = {
        "7576": {"WFK": (220.0, 2)},
        "7577": {"WFK": (0.0, 2)},
    }

    assert SifValidationService._match_inc_groups(groups, ["WFK", "WFK"]) == 440.0


@pytest.mark.parametrize("article,base,increment,quantity,expected", [
    ("MEXXAW.2020S4MG", 2932, 220, 2, 3372),
    ("MEXXAW.2020P2MG", 3014, 220, 2, 3454),
    ("MEXXAW.2222S4MG", 3150, 241, 2, 3632),
    ("MEXXAW.2222P2MG", 3230, 241, 2, 3712),
    ("MEXXAW.2424S4MG", 3286, 263, 2, 3812),
    ("MEXXAW.2424P2MG", 3366, 263, 2, 3892),
    ("SINGLE", 100, 20, 1, 120),
])
def test_obx_validation_prices_pdm_option_quantity(
    monkeypatch, article, base, increment, quantity, expected
):
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    option_rows = [
        _IncPriceRow(article, SimpleNamespace(
                OptionId=option_id, OptionValueId=option_id * 10,
                OrderCodeValue2=code, Status=1, IncPrice=price,
            IsFabric=0, Quantity=row_quantity, ParentOptId=None,
        ))
        for option_id, code, price, row_quantity in [
            (7578, "NN", None, quantity),
            (7576, "WFK", increment, quantity),
            (7577, "WFK", None, quantity),
            (7573, "X1", None, quantity),
            (7683, "X1", None, quantity),
            (8894, "X1", None, quantity),
        ]
    ]
    repo = SimpleNamespace(
        **_eligible_validation_repo_methods(),
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: [SimpleNamespace(Item=article, price=base)],
        fetch_item_validation_options=lambda *args: option_rows,
    )
    line = ObxLine(seq=1, base_article=article,
                   final_article=f"{article} NN WFK WFK X1 X1 X1", obx_price=expected)

    results = service._validate_group(
        "GBP", [line], 1, repo, None, "28 Sep 2026", [0], 1,
        None, None, obx=True,
    )

    assert len(results) == 1
    assert results[0].pdm_price == expected
    assert results[0].status == "ok"


def test_obx_recovers_completed_articles_from_truncated_export():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle itemType="BasketArticle">
        <artNr type="base">ABC</artNr>
        <artNr type="final">ABC RED</artNr>
        <itemPrice type="sale" pd="1" currency="GBP" value="100"/>
      </bskArticle>
      <bskArticle itemType="BasketArticle">
        <artNr type="base">DEF</artNr>
        <artNr type="final">DEF BLUE</artNr>
        <itemPrice type="sale" pd="1" currency="GBP" value="200"/>
      </bskArticle>
      <bskArticle itemType="BasketArticle">
        <artNr type="base">INCOMPLETE</artNr>
    """
    currency, lines = service.parse_obx(xml)

    assert currency == "GBP"
    assert len(lines) == 2
    assert [line.base for line in lines] == ["ABC", "DEF"]
    assert [line.obx_price for line in lines] == [100.0, 200.0]
    assert service.last_parse_recovered is True


def test_obx_does_not_recover_structural_xml_corruption():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle itemType="BasketArticle">
        <artNr type="base">ABC</artNr>
      </bskArticle>
      <broken>
    </root>
    """
    try:
        service.parse_obx(xml)
    except Exception as exc:
        assert "mismatched tag" in str(exc).lower()
    else:
        raise AssertionError("Structural XML corruption must not be silently recovered")


def test_pdm_query_window_is_independent_of_total_workload():
    service = SifValidationService(None)
    service._PRICE_WINDOW = 16

    assert service._PRICE_WINDOW == 16


def test_obx_filtered_export_preserves_selected_source_articles(tmp_path):
    service = ObxValidationService(None)
    source = tmp_path / "source.obx"
    target = tmp_path / "source_Failed.obx"
    source.write_text(
        """<?xml version="1.0"?>
<root>
  <header value="keep"/>
  <bskArticle itemType="BasketArticle">
    <artNr type="base">A</artNr>
    <artNr type="final">A RED</artNr>
    <itemPrice type="sale" pd="1" currency="EUR" value="100"/>
  </bskArticle>
  <bskArticle itemType="BasketArticle">
    <artNr type="base">B</artNr>
    <artNr type="final">B BLUE</artNr>
    <itemPrice type="sale" pd="1" currency="EUR" value="200"/>
  </bskArticle>
</root>
""",
        encoding="utf-8",
    )

    currency, lines = service.parse_obx(source.read_text(encoding="utf-8"))

    assert currency == "EUR"
    assert [line.source_index for line in lines] == [0, 1]

    written = service.export_filtered_obx(str(source), [lines[1]], str(target))

    assert written == 1
    filtered_currency, filtered = service.parse_obx(target.read_text(encoding="utf-8"))
    assert filtered_currency == "EUR"
    assert len(filtered) == 1
    assert filtered[0].base == "B"
    assert filtered[0].final_article == "B BLUE"
    assert filtered[0].obx_price == 200.0


def test_obx_filtered_export_supports_recovered_truncated_source(tmp_path):
    service = ObxValidationService(None)
    source = tmp_path / "truncated.obx"
    target = tmp_path / "truncated_Failed.obx"
    source.write_text(
        """<root>
  <bskArticle itemType="BasketArticle">
    <artNr type="base">A</artNr>
    <artNr type="final">A RED</artNr>
    <itemPrice type="sale" pd="1" currency="GBP" value="100"/>
  </bskArticle>
  <bskArticle itemType="BasketArticle">
    <artNr type="base">B</artNr>
    <artNr type="final">B BLUE</artNr>
    <itemPrice type="sale" pd="1" currency="GBP" value="200"/>
  </bskArticle>
""",
        encoding="utf-8",
    )

    currency, lines = service.parse_obx(source.read_text(encoding="utf-8"))

    assert currency == "GBP"
    assert len(lines) == 2
    assert service.last_parse_recovered is True

    written = service.export_filtered_obx(str(source), [lines[0]], str(target))

    assert written == 1
    filtered_currency, filtered = service.parse_obx(target.read_text(encoding="utf-8"))
    assert filtered_currency == "GBP"
    assert [line.base for line in filtered] == ["A"]
