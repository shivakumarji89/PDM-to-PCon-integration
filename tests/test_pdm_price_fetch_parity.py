"""Read-only contracts for the source-price rows used by Article/Global pricing."""
from types import SimpleNamespace

from repositories.pdm_repository import PDMRepository


def test_base_price_fetch_preserves_rows_nulls_duplicates_and_scope():
    repo = PDMRepository(None)
    connection = object()
    expected = [
        SimpleNamespace(Item="GEWQ.", price=171.0),
        SimpleNamespace(Item="GEPBPANNF.0608S4M", price=None),
        # The repository layer must not silently collapse duplicate result rows.
        SimpleNamespace(Item="GEWQ.", price=9.0),
    ]
    calls = []

    def execute(query, params, connection=None):
        calls.append((query, params, connection))
        return expected

    repo._execute = execute
    rows = repo.fetch_item_base_prices(
        ["GEWQ.", "GEPBPANNF.0608S4M"], "GBP", "16-Oct-2026",
        connection=connection, site_id=1,
    )

    assert rows == expected
    assert [(row.Item, row.price) for row in rows] == [
        ("GEWQ.", 171.0),
        ("GEPBPANNF.0608S4M", None),
        ("GEWQ.", 9.0),
    ]
    query, params, used_connection = calls[0]
    assert "dbo.fnGetListPriceByItem(i.Item, ?, ?, ?, NULL)" in query
    assert "FROM Item i" in query and "WHERE i.Item IN (?, ?)" in query
    assert params == ("GBP", "16-Oct-2026", 1, "GEWQ.", "GEPBPANNF.0608S4M")
    assert used_connection is connection


def test_option_increment_fetch_keeps_all_result_columns_nulls_and_duplicates():
    rows_by_item = {
        "GEWQ.": [
            SimpleNamespace(
                OptionId=3827, OptionValueId=71, OrderCodeValue2="DB3",
                Status=1, IncPrice=12.5, IsFabric=0, Quantity=1,
                ParentOptId=None, ParentOptValId=None, ParentOptValCode=None,
                FeaturePositionString=None, TertiaryOption=0,
                DisplayOrder=3, DisplayOrdinal=1,
            ),
        ],
        "GETH.1022FS4W": [
            SimpleNamespace(
                OptionId=9168, OptionValueId=44, OrderCodeValue2="AA",
                Status=1, IncPrice=None, IsFabric=1, Quantity=2,
                ParentOptId=10, ParentOptValId=11, ParentOptValCode="P",
                FeaturePositionString="|1|", TertiaryOption=1,
                DisplayOrder=4, DisplayOrdinal=2,
            ),
            # Preserve duplicate rows and their original order at the fetch layer.
            SimpleNamespace(
                OptionId=9168, OptionValueId=44, OrderCodeValue2="AA",
                Status=1, IncPrice=None, IsFabric=1, Quantity=2,
                ParentOptId=10, ParentOptValId=11, ParentOptValCode="P",
                FeaturePositionString="|1|", TertiaryOption=1,
                DisplayOrder=4, DisplayOrdinal=2,
            ),
        ],
    }
    columns = [
        "OptionId", "OptionValueId", "OrderCodeValue2", "Status", "IncPrice",
        "IsFabric", "Quantity", "ParentOptId", "ParentOptValId",
        "ParentOptValCode", "FeaturePositionString", "TertiaryOption",
        "DisplayOrder", "DisplayOrdinal",
    ]
    calls = []

    class Cursor:
        def __init__(self, item):
            self.item = item
            self.result_index = 0
            self.description = None

        def execute(self, query, params):
            calls.append((query, params))

        def fetchall(self):
            if self.result_index == 0:
                return []
            return rows_by_item[self.item]

        def nextset(self):
            if self.result_index == 0:
                self.result_index = 1
                self.description = [(column,) for column in columns]
                return True
            return False

        def close(self):
            pass

    class Connection:
        def __init__(self):
            self.items = iter(rows_by_item)

        def cursor(self):
            return Cursor(next(self.items))

    records = PDMRepository(None).fetch_item_option_increment_prices(
        ["GEWQ.", "GETH.1022FS4W"], "GBP", "16-Oct-2026", 1,
        connection=Connection(),
    )

    assert [row.Item for row in records] == [
        "GEWQ.", "GETH.1022FS4W", "GETH.1022FS4W",
    ]
    assert [row.IncPrice for row in records] == [12.5, None, None]
    assert records[0].OptionValueId == 71
    assert records[1].ParentOptValCode == "P"
    assert records[1].FeaturePositionString == "|1|"
    assert all("EXEC dbo.PDMOptionDataReportWithIncList" in query for query, _ in calls)
    assert [params for _, params in calls] == [
        ("GEWQ.", 1, "GBP", "16-Oct-2026"),
        ("GETH.1022FS4W", 1, "GBP", "16-Oct-2026"),
    ]


def test_article_increment_fetch_uses_pdm_inline_query_and_preserves_price_band():
    calls = []
    source_rows = {
        "GEWQ.": [
            SimpleNamespace(
                OptionValueId=300267,
                OptionId=3827,
                OrderCodeValue="DB3",
                IncPrice=16.0,
                PriceBand=None,
            ),
        ],
        "GEWDP.L": [],
    }
    repo = PDMRepository(None)

    def execute(query, params, connection=None):
        calls.append((query, params, connection))
        return source_rows[params[-1]]

    repo._execute = execute
    records = repo.fetch_article_option_increment_prices(
        ["GEWQ.", "GEWDP.L"],
        "GBP",
        "16-Oct-2026",
        1,
        connection=object(),
    )

    assert len(records) == 1
    row = records[0]
    assert (row.Item, row.OptionValueId, row.OptionId, row.Code, row.IncPrice) == (
        "GEWQ.", 300267, 3827, "DB3", 16.0,
    )
    assert row.PriceBand is None
    assert len(calls) == 2
    assert all("dbo.fnGetListPrice(" in query for query, _, _ in calls)
    assert all("dbo.PDMOptionDataReportWithIncList" not in query for query, _, _ in calls)
    assert all("SELECT DISTINCT" in query for query, _, _ in calls)
    assert all("optval.Status = 1" in query for query, _, _ in calls)
    assert all("INNER JOIN PriceMatrix pm" in query for query, _, _ in calls)
    assert all("INNER JOIN Currency" in query for query, _, _ in calls)
    assert [params for _, params, _ in calls] == [
        ("GBP", "16-Oct-2026", 1, 1, "GBP", "GEWQ."),
        ("GBP", "16-Oct-2026", 1, 1, "GBP", "GEWDP.L"),
    ]


def test_article_increment_query_preserves_pdm_program_exclusions():
    repo = PDMRepository(None)
    captured = []
    repo._execute = lambda query, params, connection=None: (
        captured.append(query) or []
    )

    repo.fetch_article_option_increment_prices(
        ["GEWQ."], "GBP", "16-Oct-2026", 1, program_code="lf"
    )

    assert "Product.Product NOT LIKE 'MRF7%'" in captured[0]


def test_article_price_compute_uses_the_article_inline_fetch(monkeypatch):
    from models.snapshot import Snapshot
    from services.pricing_service import PriceParams, PricingService

    calls = {"article": [], "procedure": []}

    class Connection:
        def close(self):
            pass

    def fetch_base(self, items, currency, mydate, connection=None, site_id=1):
        return [SimpleNamespace(Item=item, price=10.0) for item in items]

    def fetch_article(self, items, currency, mydate, site_id, connection=None, program_code=""):
        calls["article"].append((list(items), currency, mydate, site_id, program_code))
        return [
            SimpleNamespace(
                Item=item, OptionId=3827, Code="DB3", IncPrice=16.0, PriceBand=None
            )
            for item in items
        ]

    def fetch_procedure(self, items, currency, mydate, site_id, connection=None):
        calls["procedure"].append((list(items), currency))
        return []

    monkeypatch.setattr(PDMRepository, "get_connection", lambda self: Connection())
    monkeypatch.setattr(PDMRepository, "fetch_item_base_prices", fetch_base)
    monkeypatch.setattr(
        PDMRepository, "fetch_article_option_increment_prices", fetch_article
    )
    monkeypatch.setattr(
        PDMRepository, "fetch_item_option_increment_prices", fetch_procedure
    )
    monkeypatch.setattr(PricingService, "_attach_product_codes", lambda *args: None)

    snapshot = Snapshot()
    snapshot.generation_program = "lf"
    snapshot.articles = [
        SimpleNamespace(id="1", code="GEWQ.", product_id="1")
    ]
    result = PricingService(None).compute(
        PriceParams(mydate="16-Oct-2026", site_id=1), snapshot
    )

    assert calls["article"] == [
        (["GEWQ."], "EUR", "16-Oct-2026", 1, "lf"),
        (["GEWQ."], "GBP", "16-Oct-2026", 1, "lf"),
    ]
    assert calls["procedure"] == []
    assert len(result.records) == 4
    assert {record.level for record in result.records} == {"B", "X"}


def test_article_price_streaming_uses_generation_program(monkeypatch):
    from models.snapshot import Snapshot
    from services.pricing_service import PriceParams, PricingService

    calls = []

    class Connection:
        def close(self):
            pass

    def fetch_base(self, items, currency, mydate, connection=None, site_id=1):
        return [SimpleNamespace(Item=item, price=10.0) for item in items]

    def fetch_article(
        self, items, currency, mydate, site_id, connection=None, program_code=""
    ):
        calls.append((list(items), currency, mydate, site_id, program_code))
        return []

    monkeypatch.setattr(PDMRepository, "get_connection", lambda self: Connection())
    monkeypatch.setattr(PDMRepository, "fetch_item_base_prices", fetch_base)
    monkeypatch.setattr(
        PDMRepository, "fetch_article_option_increment_prices", fetch_article
    )
    monkeypatch.setattr(PricingService, "_attach_product_codes", lambda *args: None)

    snapshot = Snapshot()
    snapshot.generation_program = "lf"
    snapshot.articles = [
        SimpleNamespace(id="1", code="GEWQ.", product_id="1")
    ]
    PricingService(None).compute_streaming(
        PriceParams(mydate="16-Oct-2026", site_id=1), snapshot
    )

    assert calls == [
        (["GEWQ."], "EUR", "16-Oct-2026", 1, "lf"),
        (["GEWQ."], "GBP", "16-Oct-2026", 1, "lf"),
    ]


def test_global_increment_fetch_keeps_only_active_priced_rows(monkeypatch):
    repo = PDMRepository(None)
    source_rows = [
        SimpleNamespace(
            Item="GETH.1022FS4W", OrderCodeValue="GETH.1022FS4W_AA",
            RawIncrement=16, OptionValueId=10, OptionId=8, PriceBand=None,
        ),
        SimpleNamespace(
            Item="GETH.1022FS4W", OrderCodeValue="GETH.1022FS4W_BB",
            RawIncrement=None, OptionValueId=11, OptionId=8, PriceBand=None,
        ),
    ]
    def execute(query, params, connection=None):
        assert "fb.Application = 1" in query
        if "AS NewPrice" in query:
            return [SimpleNamespace(Item="GETH.1022FS4W", NewPrice=16)]
        assert "optval.Status = 1" in query
        return source_rows
    monkeypatch.setattr(repo, "_execute", execute)

    rows = repo.fetch_global_option_increment_prices(
        ["GETH.1022FS4W"], "GBP", "16-Oct-2026", 1, connection=object(),
        catalogue_id=660,
    )

    assert [(row.OptionValueId, row.IncPrice) for row in rows] == [(10, 16.0)]


def test_global_fetch_matches_pdm_priced_rows_and_query_order(monkeypatch):
    priced = [
        (299995, 9168, "AA", 47.0),
        (300275, 9168, "BA", 45.0),
        (300276, 9168, "BC", 66.0),
        (300284, 9168, "EB", 45.0),
        (300285, 9168, "ED", 66.0),
        (62290, 3831, "EU", 612.0),
        (62291, 3831, "EV", 612.0),
        (194059, 3831, "NOK", 202.0),
        (62287, 3831, "OKG", 202.0),
        (62288, 3831, "OUG", 294.0),
        (300272, 9168, "RR", 45.0),
        (300271, 9168, "SC", 45.0),
        (300274, 9168, "SL", 66.0),
        (300273, 9168, "SS", 45.0),
        (300287, 9168, "VL", 1320.0),
        (300286, 9168, "VS", 1100.0),
    ]
    procedure_rows = [
        SimpleNamespace(
            Item="GETH.1022FS4W",
            OptionValueId=option_value_id,
            OptionId=option_id,
            OrderCodeValue2=code,
            Status=1,
            IncPrice=price,
            PriceBand=None,
        )
        for option_value_id, option_id, code, price in [
            priced[0],
            (300271, 9168, "SC", 45.0),
            (300272, 9168, "RR", 45.0),
            (300273, 9168, "SS", 45.0),
            (300274, 9168, "SL", 66.0),
            (300275, 9168, "BA", 45.0),
            (300276, 9168, "BC", 66.0),
            (300284, 9168, "EB", 45.0),
            (300285, 9168, "ED", 66.0),
            (300286, 9168, "VS", 1100.0),
            (300287, 9168, "VL", 1320.0),
            (62287, 3831, "OKG", 202.0),
            (62288, 3831, "OUG", 294.0),
            (62290, 3831, "EU", 612.0),
            (62291, 3831, "EV", 612.0),
            (194059, 3831, "NOK", 202.0),
            (299994, 9168, "NN", None),
            (62286, 3831, "Z5G", None),
            (300309, 3832, "Z5G", None),
            (300310, 3832, "OKG", None),
            (300311, 3832, "OUG", None),
            (300313, 3832, "EU", None),
            (300314, 3832, "EV", None),
            (300315, 3832, "PLV", None),
        ]
    ]
    repo = PDMRepository(None)
    def execute(query, params, connection=None):
        if "AS NewPrice" in query:
            return [SimpleNamespace(Item="GETH.1022FS4W", NewPrice=params[7])]
        return [
            SimpleNamespace(
                Item="GETH.1022FS4W", OptionValueId=vid, OptionId=oid,
                OrderCodeValue=f"GETH.1022FS4W_{code}",
                RawIncrement=value, PriceBand=None,
            ) for vid, oid, code, value in priced
        ]
    monkeypatch.setattr(repo, "_execute", execute)
    monkeypatch.setattr(repo, "fetch_item_option_increment_prices",
                        lambda *args: (_ for _ in ()).throw(AssertionError("procedure")))

    rows = repo.fetch_global_option_increment_prices(
        ["GETH.1022FS4W"], "GBP", "16-Oct-2026", 1, connection=object(),
        catalogue_id=660,
    )

    assert len(procedure_rows) == 24
    assert len(rows) == 16
    assert all(row.Status == 1 and row.PriceBand is None for row in procedure_rows)
    null_rows = [row for row in procedure_rows if row.IncPrice is None]
    assert {
        (row.OptionValueId, row.OptionId, row.OrderCodeValue2)
        for row in null_rows
    } == {
        (299994, 9168, "NN"),
        (62286, 3831, "Z5G"),
        (300309, 3832, "Z5G"),
        (300310, 3832, "OKG"),
        (300311, 3832, "OUG"),
        (300313, 3832, "EU"),
        (300314, 3832, "EV"),
        (300315, 3832, "PLV"),
    }
    assert [
        (row.OptionValueId, row.OptionId, row.Code, row.IncPrice)
        for row in rows
    ] == priced

    from services.pricing_service import PriceParams, PricingService

    records, unresolved = PricingService.build_records(
        [],
        rows,
        {"GETH.1022FS4W"},
        {},
        PriceParams(mydate="16-Oct-2026", site_id=1, currency="GBP"),
    )
    assert unresolved == []
    assert [
        (record.variant_condition, record.value)
        for record in records
    ] == [
        (f"GETH.1022FS4W {option_id}={code}", value)
        for _, option_id, code, value in priced
    ]


def test_global_price_compute_uses_global_increment_fetch(monkeypatch):
    from models.snapshot import Snapshot
    from services.pricing_service import PriceParams, PricingService

    calls = {"article": [], "global": []}

    class Connection:
        def close(self):
            pass

    def fetch_base(self, items, currency, mydate, connection=None, site_id=1):
        return [SimpleNamespace(Item=item, price=10.0) for item in items]

    def fetch_article(self, items, currency, mydate, site_id, connection=None, program_code=""):
        calls["article"].append(list(items))
        return []

    def fetch_global(self, items, currency, mydate, site_id, connection=None,
                     *, catalogue_id, program_code=""):
        calls["global"].append((list(items), currency, catalogue_id, program_code))
        return [
            SimpleNamespace(
                Item=item, OptionId=3827, Code="DB3", IncPrice=16.0, PriceBand=None
            )
            for item in items
        ]

    monkeypatch.setattr(PDMRepository, "get_connection", lambda self: Connection())
    monkeypatch.setattr(PDMRepository, "fetch_item_base_prices", fetch_base)
    monkeypatch.setattr(
        PDMRepository, "fetch_article_option_increment_prices", fetch_article
    )
    monkeypatch.setattr(
        PDMRepository, "fetch_global_option_increment_prices", fetch_global
    )
    monkeypatch.setattr(PricingService, "_attach_product_codes", lambda *args: None)

    snapshot = Snapshot()
    snapshot.articles = [
        SimpleNamespace(id="10", code="SUPER.", product_id="1"),
        SimpleNamespace(id="11", code="GETH.1022FS4W", product_id="2"),
    ]
    snapshot.article_components = {
        "10": [{"sub_item": "GETH.1022FS4W", "quantity": 1, "sequence": "1"}]
    }
    result = PricingService(None).compute(
        PriceParams(mydate="16-Oct-2026", site_id=1, catalogue_id=660), snapshot
    )

    assert calls["article"] == []
    assert calls["global"] == [
        (["GETH.1022FS4W"], "EUR", 660, ""),
        (["GETH.1022FS4W"], "GBP", 660, ""),
    ]
    assert result.records
    assert all(record.is_global for record in result.records)
