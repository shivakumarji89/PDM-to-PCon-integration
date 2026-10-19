from services.syteline_export.item_selection_query import ItemSelection
from services.syteline_export.item_source_service import SyteLineItemSourceService


class FakeCursor:
    def __init__(self):
        self.timeout = 0
        self.description = [("LongItem",), ("Status",)]
        self.executed = None

    def execute(self, sql, *params):
        self.executed = (sql, params)

    def fetchall(self):
        return [("ITEM-1", 1), ("ITEM-2", 0)]


class FakeConnection:
    def __init__(self):
        self.fake_cursor = FakeCursor()
        self.closed = False

    def cursor(self):
        return self.fake_cursor

    def close(self):
        self.closed = True


def test_item_source_executes_bound_query_maps_columns_and_closes_connection():
    connection = FakeConnection()
    service = SyteLineItemSourceService(connection_factory=lambda: connection)
    rows = service.fetch_items(ItemSelection(
        site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
        active_only=True,
    ))
    assert rows == [
        {"LongItem": "ITEM-1", "Status": 1},
        {"LongItem": "ITEM-2", "Status": 0},
    ]
    sql, params = connection.fake_cursor.executed
    assert "WHERE pc.SiteId = ?" in sql
    assert 1 in params
    assert connection.fake_cursor.timeout == 600
    assert connection.closed


def test_item_source_closes_connection_when_query_fails():
    class BrokenCursor(FakeCursor):
        def execute(self, sql, *params):
            raise RuntimeError("database unavailable")

    connection = FakeConnection()
    connection.fake_cursor = BrokenCursor()
    service = SyteLineItemSourceService(connection_factory=lambda: connection)
    import pytest
    with pytest.raises(RuntimeError, match="database unavailable"):
        service.fetch_items(ItemSelection(
            site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
            active_only=True,
        ))
    assert connection.closed


def test_option_report_executes_legacy_procedure_with_bound_item_and_maps_rows():
    connection = FakeConnection()
    connection.fake_cursor.description = [("OptionValueId",), ("OrderCodeValue2",)]
    connection.fake_cursor.fetchall = lambda: [(123, "BLK")]
    service = SyteLineItemSourceService(connection_factory=lambda: connection)

    rows = service.fetch_option_report("ITEM-42")

    assert rows == [{"OptionValueId": 123, "OrderCodeValue2": "BLK"}]
    assert connection.fake_cursor.executed == ("EXEC PDMOptionDataReport ?", ("ITEM-42",))
    assert connection.fake_cursor.timeout == 900
    assert connection.closed


def test_option_report_rejects_blank_item_without_connecting():
    import pytest

    service = SyteLineItemSourceService(connection_factory=lambda: (_ for _ in ()).throw(
        AssertionError("must not connect for invalid item")
    ))
    with pytest.raises(ValueError, match="non-empty long item"):
        service.fetch_option_report("  ")


def test_option_report_closes_connection_when_procedure_fails():
    class BrokenCursor(FakeCursor):
        def execute(self, sql, *params):
            raise RuntimeError("procedure unavailable")

    connection = FakeConnection()
    connection.fake_cursor = BrokenCursor()
    service = SyteLineItemSourceService(connection_factory=lambda: connection)
    import pytest
    with pytest.raises(RuntimeError, match="procedure unavailable"):
        service.fetch_option_report("ITEM-42")
    assert connection.closed



def test_prepared_option_report_normalizes_orders_and_reconciles_children():
    connection = FakeConnection()
    columns = [
        "Range2", "Product2", "DisplayOrder", "OrderCodeValue2", "DisplayOrdinal",
        "OptionValueId", "OptionId", "IsFabric", "OptDescId", "optvalDescId",
        "ParentOptValId", "OptChildCount", "OptChildId", "optval_name", "fsccompliant",
    ]
    connection.fake_cursor.description = [(name,) for name in columns]
    connection.fake_cursor.fetchall = lambda: [
        ("R", "P", 1, "LEG", 1, 10, 2, 0, 3, 4, None, 1, None, "Leg", 0),
        ("R", "P", 1, "LEG", 2, 10, 2, 0, 3, 4, None, 1, 77, "Leg", 0),
    ]
    service = SyteLineItemSourceService(connection_factory=lambda: connection)

    rows = service.fetch_prepared_option_report("ITEM-42")

    assert len(rows) == 1
    assert rows[0]["ResolvedChildOptionIds"] == (77,)
    assert rows[0]["OrderCodeValue2"] == "LEG"
    assert connection.closed



def test_legacy_feature_length_query_binds_catalogue_and_option_ids_and_maps_rows():
    connection = FakeConnection()
    connection.fake_cursor.description = [
        ("SLFeatureLength",), ("max_length",), ("IsFabric",),
    ]
    connection.fake_cursor.fetchall = lambda: [(2, 4, 0)]
    service = SyteLineItemSourceService(connection_factory=lambda: connection)

    rows = service.fetch_legacy_option_feature_length_rows(17, 30)

    assert rows == [{"SLFeatureLength": 2, "max_length": 4, "IsFabric": 0}]
    sql, params = connection.fake_cursor.executed
    assert "cov.CatalogueId = ?" in sql
    assert "HAVING opt.OptionId = ?" in sql
    assert params == (30, 17)
    assert connection.fake_cursor.timeout == 600
    assert connection.closed


def test_legacy_feature_length_query_rejects_invalid_ids_before_connecting():
    import pytest

    service = SyteLineItemSourceService(connection_factory=lambda: (_ for _ in ()).throw(
        AssertionError("must not connect for invalid IDs")
    ))
    with pytest.raises(ValueError, match="must be integers"):
        service.fetch_legacy_option_feature_length_rows("bad", 30)
    with pytest.raises(ValueError, match="must be positive"):
        service.fetch_legacy_option_feature_length_rows(17, 0)
