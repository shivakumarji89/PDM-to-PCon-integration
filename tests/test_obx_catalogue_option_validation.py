import csv
import json
import sqlite3
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.errors import PDMQueryError
from core.validation_control import ValidationCancelled, ValidationControl, ValidationPaused
from repositories.pdm_repository import PDMRepository
from services.cancellable_sif_validation_service import CancellableSifValidationService
from services.obx_validation_service import ObxLine, ObxValidationService
from services.sif_validation_service import SifLine, SifOption, SifValidationService


REFERENCE = json.loads(
    (Path(__file__).parent / "fixtures" / "obx_catalogue_option_scope.json").read_text(
        encoding="utf-8"
    )
)


def _option(value, group, code, *, fabric=0, parent=None, increment=0.0, status=1):
    return {
        "OptionValueId": value, "OptionId": group, "OrderCodeValue2": code,
        "Status": status, "IsFabric": fabric, "IncPrice": increment,
        "ParentOptId": parent[0] if parent else None,
        "ParentOptValId": parent[1] if parent else None,
        "ParentOptValCode": parent[2] if parent else None,
    }


def _simple_data():
    return {
        "SKU": {
            "options": [
                _option(1, 10, "G", increment=7),
                _option(2, 20, "FED#", fabric=1, parent=(10, 1, "G")),
                _option(3, 30, "01FED", fabric=2, parent=(20, 2, "FED#")),
            ],
            "catalogues": {
                "11": {"membership": [1, 2, 3], "product_exclusions": [], "item_exclusions": []},
                "12": {"membership": [1, 2, 3], "product_exclusions": [], "item_exclusions": []},
            },
        },
    }


class _Cursor:
    def __init__(self, harness):
        self.harness = harness
        self.cursor = harness.db.cursor()

    def execute(self, query, params):
        self.harness.queries.append((query, params))
        if self.harness.on_scope_query is not None:
            self.harness.on_scope_query()
        self.cursor.execute(query, params)
        return self

    def fetchall(self):
        columns = [column[0] for column in self.cursor.description]
        return [SimpleNamespace(**dict(zip(columns, row))) for row in self.cursor.fetchall()]

    def close(self):
        self.cursor.close()

    def cancel(self):
        self.harness.cancel_calls += 1


class _Connection:
    def __init__(self, harness):
        self.harness = harness

    def cursor(self):
        return _Cursor(self.harness)

    def close(self):
        self.harness.closed += 1


class _Harness:
    """Keep the production service and eligibility SQL, substituting only PDM I/O."""

    def __init__(self, monkeypatch, data):
        self.data = deepcopy(data)
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
            CREATE TABLE Item (Item TEXT, ItemId INTEGER, ProductId INTEGER);
            CREATE TABLE CatalogueOptionValues (CatalogueId INTEGER, OptionValueId INTEGER);
            CREATE TABLE CatalogueProductOptionExclusions
                (CatalogueId INTEGER, ProductId INTEGER, OptionValueId INTEGER);
            CREATE TABLE CatalogueItemOptionExclusions
                (CatalogueId INTEGER, ItemId INTEGER, OptionValueId INTEGER);
        """)
        self.rows = []
        self.queries = []
        self.priced = []
        self.closed = 0
        self.cancel_calls = 0
        self.on_scope_query = None
        membership = set()
        for index, (item, details) in enumerate(self.data.items(), 1):
            self.db.execute("INSERT INTO Item VALUES (?,?,?)", (item, index, 100 + index))
            self.rows.extend(
                SimpleNamespace(**{"Item": item, "IncPrice": None, "Quantity": 1, **row})
                for row in details["options"]
            )
            for catalogue, scope in details["catalogues"].items():
                membership.update((int(catalogue), value) for value in scope["membership"])
                self.db.executemany(
                    "INSERT INTO CatalogueProductOptionExclusions VALUES (?,?,?)",
                    [(int(catalogue), 100 + index, value) for value in scope["product_exclusions"]],
                )
                self.db.executemany(
                    "INSERT INTO CatalogueItemOptionExclusions VALUES (?,?,?)",
                    [(int(catalogue), index, value) for value in scope["item_exclusions"]],
                )
        self.db.executemany("INSERT INTO CatalogueOptionValues VALUES (?,?)", sorted(membership))
        self.catalogues = list(dict.fromkeys(
            int(cat) for details in self.data.values() for cat in details["catalogues"]
        ))
        monkeypatch.setattr(PDMRepository, "get_connection", lambda repo: _Connection(self))
        monkeypatch.setattr(PDMRepository, "_driver", staticmethod(
            lambda: SimpleNamespace(Error=sqlite3.Error)
        ))
        monkeypatch.setattr(PDMRepository, "find_normal_items", lambda repo, items, **kw: set(items))
        monkeypatch.setattr(PDMRepository, "find_us_items", lambda repo, items, **kw: set())
        monkeypatch.setattr(PDMRepository, "fetch_validation_catalogue_ids", lambda *a, **kw: self.catalogues)
        monkeypatch.setattr(
            PDMRepository, "fetch_items_valid_catalogues",
            lambda repo, items, catalogues, **kw: {
                item: [cat for cat in catalogues if str(cat) in self.data[item]["catalogues"]]
                for item in items
            },
        )
        monkeypatch.setattr(
            PDMRepository, "fetch_item_validation_price_context",
            lambda repo, items, currency, *a, **kw: [
                SimpleNamespace(
                    Item=item, Status=1, IsSuperProduct=0, ProductCodeId=1,
                    PriceCode="PC", BasePriceRef=1, Rounding=2, MatchedCurrency=currency,
                )
                for item in items
            ],
        )
        monkeypatch.setattr(
            PDMRepository, "fetch_item_validation_options",
            lambda repo, items, *a, **kw: [row for row in self.rows if row.Item in items],
        )
        monkeypatch.setattr(
            PDMRepository, "fetch_validation_get_price_ext_base_prices", self._base_prices,
        )
        monkeypatch.setattr(SifValidationService, "_server_date", lambda *a: "2026-11-03")
        monkeypatch.setattr(SifValidationService, "_fetch_plc", lambda *a: {})
        monkeypatch.setattr(CancellableSifValidationService, "_fetch_plc", lambda *a: {})
        self.context = SimpleNamespace()
        self.context.sif_validation_service = SifValidationService(self.context)
        self.service = ObxValidationService(self.context)

    def _base_prices(self, items, *args, **kwargs):
        self.priced.extend(items)
        return [SimpleNamespace(Item=item, price=100.0) for item in items]

    def validate(self, skus, *, prices=None, control=None, **kwargs):
        lines = [
            ObxLine(
                seq=index, base_article=sku.split()[0], final_article=sku,
                currency="EUR", obx_price=prices[index - 1] if prices else 100.0,
            )
            for index, sku in enumerate(skus, 1)
        ]
        return self.service.validate(
            "EUR", lines, site=1, validation_date="2026-11-03",
            operation_control=control, **kwargs,
        )[1]


@pytest.fixture
def harness(monkeypatch):
    instances = []

    def create(data=None):
        instance = _Harness(monkeypatch, _simple_data() if data is None else data)
        instances.append(instance)
        return instance

    yield create
    for instance in instances:
        instance.db.close()


@pytest.mark.parametrize("controlled", [False, True])
@pytest.mark.parametrize("case", REFERENCE["cases"], ids=lambda case: case["sku"])
def test_all_11_reported_configurations_reject_through_obx_entry_point(harness, case, controlled):
    item = case["sku"].split()[0]
    h = harness({item: REFERENCE["items"][item]})
    control = ValidationControl() if controlled else None
    results = h.validate([case["sku"]], prices=[case["reported_price"]], control=control)

    assert len(h.catalogues) == 13
    assert len(results) == 1
    assert results[0].status == "unresolved"
    assert "invalid option string in order code at position 2" in results[0].message
    assert results[0].pdm_price is None
    assert results[0].sif_price == case["reported_price"]
    assert h.priced == []
    assert h.queries
    if control:
        assert control._cancel_handlers == []


@pytest.mark.parametrize("sku", [
    "70LMC G 01H", "74YMC G 01H", "70LMC C T1P201", "74YMC C T1P201",
    "BUNLC G 01FED", "AER1B33DW-AERON-FAST01 ALP G1 G1 G1 BB BK 23103",
])
@pytest.mark.parametrize("controlled", [False, True])
def test_captured_valid_families_still_reach_unchanged_pricing(harness, sku, controlled):
    item = sku.split()[0]
    h = harness({item: REFERENCE["items"][item]})
    results = h.validate([sku], control=ValidationControl() if controlled else None)

    assert results[0].status == "ok"
    assert results[0].pdm_price == 100.0  # Isolated base-price fixture, not a live price claim.
    assert h.priced == [item]


@pytest.mark.parametrize("gate", ["membership", "product_exclusions", "item_exclusions"])
@pytest.mark.parametrize("value", [1, 2, 3])
def test_each_catalogue_gate_rejects_selected_value_parent_or_ancestor(harness, gate, value):
    data = _simple_data()
    for scope in data["SKU"]["catalogues"].values():
        if gate == "membership":
            scope[gate].remove(value)
        else:
            scope[gate].append(value)
    h = harness(data)

    result = h.validate(["SKU G 01FED"])[0]

    assert result.status == "unresolved"
    assert "invalid option string" in result.message
    assert h.priced == []


def test_later_catalogue_can_admit_complete_configuration(harness):
    data = _simple_data()
    data["SKU"]["catalogues"]["11"]["product_exclusions"] = [2]
    h = harness(data)

    result = h.validate(["SKU G 01FED"], prices=[107.0])[0]

    assert result.status == "ok"
    assert result.pdm_price == 107.0
    assert h.priced == ["SKU"]


def test_does_not_union_parent_and_colour_permissions_across_catalogues(harness):
    data = _simple_data()
    data["SKU"]["catalogues"]["11"]["product_exclusions"] = [2]
    data["SKU"]["catalogues"]["12"]["item_exclusions"] = [3]
    h = harness(data)

    result = h.validate(["SKU G 01FED"])[0]

    assert result.status == "unresolved"
    assert h.priced == []


def test_overlapping_band_cannot_bypass_excluded_colour_parent(harness):
    data = _simple_data()
    data["SKU"]["options"] = [
        _option(1, 10, "G"),
        _option(2, 20, "T1#", fabric=1, parent=(10, 1, "G")),
        _option(3, 30, "T123", fabric=2, parent=(20, 2, "T1#")),
        _option(4, 20, "T#", fabric=1, parent=(10, 1, "G")),
    ]
    for scope in data["SKU"]["catalogues"].values():
        scope["membership"] = [1, 2, 3, 4]
        scope["product_exclusions"] = [2]
    h = harness(data)

    assert h.validate(["SKU G T123"])[0].status == "unresolved"


def test_eligible_exact_ordinary_value_can_share_a_dependent_colour_code(harness):
    data = _simple_data()
    data["SKU"]["options"].append(_option(4, 10, "01FED"))
    for scope in data["SKU"]["catalogues"].values():
        scope["membership"].append(4)
        scope["product_exclusions"] = [2]
    h = harness(data)

    assert h.validate(["SKU 01FED"])[0].status == "ok"


def test_sql_distinguishes_product_item_and_catalogue_keys(harness):
    data = _simple_data()
    data["OTHER"] = deepcopy(data["SKU"])
    h = harness(data)
    # Share a product: the product exclusion must affect both items, the item exclusion only one.
    h.db.execute("UPDATE Item SET ProductId=101 WHERE Item='OTHER'")
    h.db.execute("INSERT INTO CatalogueProductOptionExclusions VALUES (11,101,2)")
    h.db.execute("INSERT INTO CatalogueItemOptionExclusions VALUES (12,1,3)")
    h.db.execute("DELETE FROM CatalogueOptionValues WHERE CatalogueId=12 AND OptionValueId=1")

    allowed = PDMRepository(None).fetch_obx_catalogue_option_values(
        ["SKU", "OTHER"], [11, 12], [1, 2, 3], connection=_Connection(h)
    )

    assert allowed == {
        ("SKU", 11): {1, 3}, ("OTHER", 11): {1, 3},
        ("SKU", 12): {2}, ("OTHER", 12): {2, 3},
    }


def test_query_chunks_all_parameter_dimensions(harness, monkeypatch):
    h = harness()
    monkeypatch.setattr(PDMRepository, "_IN_CHUNK", 1)

    allowed = PDMRepository(None).fetch_obx_catalogue_option_values(
        ["SKU", "SKU"], [11, 12, 12], [1, 2, 3, 3], connection=_Connection(h)
    )

    assert allowed == {("SKU", 11): {1, 2, 3}, ("SKU", 12): {1, 2, 3}}
    assert len(h.queries) == 6
    assert all(len(params) == 3 for _, params in h.queries)


@pytest.mark.parametrize("empty", [0, 1, 2])
def test_empty_scope_inputs_do_not_query(harness, empty):
    h = harness()
    args = [["SKU"], [11], [1, 2, 3]]
    args[empty] = []

    assert PDMRepository(None).fetch_obx_catalogue_option_values(*args) == {}
    assert h.queries == []


def test_sql_errors_are_surfaced_without_valid_result_or_cached_success(harness):
    h = harness()
    h.db.execute("DROP TABLE CatalogueItemOptionExclusions")
    emitted = []

    with pytest.raises(PDMQueryError, match="CatalogueItemOptionExclusions"):
        h.validate(["SKU G 01FED"], control=ValidationControl(), on_result=emitted.append)

    assert emitted == []
    assert not h.service._validation_cache()


@pytest.mark.parametrize("action,error", [("pause", ValidationPaused), ("cancel", ValidationCancelled)])
def test_scope_query_honours_pause_cancel_and_resume(harness, action, error):
    h = harness()
    control = ValidationControl()
    h.on_scope_query = getattr(control, action)
    emitted = []

    with pytest.raises(error):
        h.validate(["SKU G 01FED"], control=control, on_result=emitted.append)

    assert emitted == []
    assert control._cancel_handlers == []
    h.on_scope_query = None
    if action == "pause":
        control.resume()
        result = h.validate(["SKU G 01FED"], prices=[107], control=control)[0]
        assert result.status == "ok"
        assert result.pdm_price == 107.0


@pytest.mark.parametrize("sku", ["SKU G UNKNOWN", "SKU S 01FED", "SKU G 01FED 01FED"])
def test_invalid_controls_still_reject(harness, sku):
    h = harness()

    assert h.validate([sku])[0].status == "unresolved"
    assert h.priced == []


def test_duplicate_expansion_progress_report_and_filtered_obx_export(harness, tmp_path):
    data = _simple_data()
    for scope in data["SKU"]["catalogues"].values():
        scope["item_exclusions"] = [2]
    h = harness(data)
    source = tmp_path / "input.obx"
    source.write_text(
        "<root>" + "".join(
            f'<bskArticle itemType="BasketArticle"><artNr type="base">SKU</artNr>'
            f'<artNr type="final">SKU G 01FED</artNr>'
            f'<itemPrice type="sale" pd="1" currency="EUR" value="{price}"/>'
            f'</bskArticle>' for price in [100, 107]
        ) + "</root>", encoding="utf-8",
    )
    currency, lines = h.service.parse_obx(source.read_text())
    progress = []
    emitted = []
    _, results = h.service.validate(
        currency, lines, site=1, validation_date="2026-11-03",
        progress=lambda *args: progress.append(args), on_result=emitted.append,
    )

    assert len(progress) == 1
    assert [r.seq for r in results] == [1, 2]
    assert [r.sif_price for r in results] == [100, 107]
    assert all(r.status == "unresolved" for r in results)
    assert emitted == results
    report = tmp_path / "report.csv"
    h.service.export_csv(report, currency, results)
    with report.open(encoding="utf-8-sig", newline="") as file:
        records = list(csv.reader(file))
    assert len(records) == 3
    assert all("invalid option string" in row[-1] for row in records[1:])
    document = h.service._filtered_obx_document(str(source), lines)
    _, exported = h.service.parse_obx(document)
    assert [line.final_article for line in exported] == ["SKU G 01FED"] * 2
    assert [line.obx_price for line in exported] == [100, 107]


def test_cet_sif_does_not_query_catalogue_option_scope(harness):
    data = _simple_data()
    for scope in data["SKU"]["catalogues"].values():
        scope["product_exclusions"] = [2]
    h = harness(data)
    _, results = h.context.sif_validation_service.validate(
        "EUR", [SifLine(
            seq=1, base="SKU", currency="EUR", pl=100,
            options=[SifOption(code="G"), SifOption(code="01FED")],
        )], site=1, validation_date="2026-11-03",
    )

    assert results[0].status == "ok"
    assert h.queries == []
    assert h.priced == ["SKU"]


def test_optionless_obx_does_not_query_catalogue_option_scope(harness):
    h = harness()

    assert h.validate(["SKU"])[0].status == "ok"
    assert h.queries == []


def test_price_mismatch_still_fails_after_valid_catalogue_option_check(harness):
    h = harness()

    result = h.validate(["SKU G 01FED"], prices=[100])[0]

    assert result.status == "price_mismatch"
    assert result.pdm_price == 107.0
    assert "price mismatch" in result.message
