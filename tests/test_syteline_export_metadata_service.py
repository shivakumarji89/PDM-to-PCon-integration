from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.syteline_export.metadata_service import SyteLineMetadataService


class FakeCursor:
    def __init__(self, columns, rows):
        self.description = [(name,) for name in columns]
        self._rows = rows
        self.calls = []

    def execute(self, query, *parameters):
        self.calls.append((query, parameters))
        return self

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


def make_service(monkeypatch, server="DBCHIP12V", columns=(), rows=()):
    cursor = FakeCursor(columns, rows)
    connection = FakeConnection(cursor)
    context = SimpleNamespace(config=SimpleNamespace(pdm_server=server))
    service = SyteLineMetadataService(context, connection_factory=lambda: connection)
    return service, cursor, connection


def test_sites_apply_legacy_site_20_filter_for_standard_server():
    service, _, connection = make_service(
        None,
        columns=("SiteId", "Description", "Site"),
        rows=((1, "UK", "UK"), (20, "Knoll Site", "KN")),
    )
    assert [(x.id, x.label, x.code) for x in service.sites()] == [(1, "UK", "UK")]
    assert connection.closed


def test_sites_keep_only_legacy_knoll_server_site_ids():
    service, _, _ = make_service(
        None,
        server="DBIA01SQLSV.knoll.dom",
        columns=("SiteId", "Description", "Site"),
        rows=((1, "UK", "UK"), (20, "Knoll Site", "KN"), (21, "Other", "OT")),
    )
    assert [x.id for x in service.sites()] == [1, 20]


def test_languages_and_currencies_map_database_ids():
    service, _, _ = make_service(
        None,
        columns=("Language_ID", "Language", "CultureCode"),
        rows=((2, "French", "fr-FR"),),
    )
    assert service.languages()[0].label == "French"
    assert service.languages()[0].code == "fr-FR"

    service, _, _ = make_service(
        None,
        columns=("Currency_ID", "Currency"),
        rows=((3, "GBP"),),
    )
    assert service.currencies()[0].id == 3
    assert service.currencies()[0].label == "GBP"


def test_catalogue_query_requires_user_id_and_parameterizes_it():
    service, cursor, _ = make_service(
        None,
        columns=("CatalogueId", "Name", "ReadOnly"),
        rows=((10, "Example Catalogue", 1),),
    )
    with pytest.raises(ValueError, match="User ID"):
        service.catalogues(0)
    assert service.catalogues(123)[0].id == 10
    assert cursor.calls[0][1] == (123,)
    assert "puc.UserId = ?" in cursor.calls[0][0]


def test_product_code_query_parameterizes_site_and_catalogue_ids():
    service, cursor, _ = make_service(
        None,
        columns=("ProductCodeId", "Product_Code", "Description", "BasePriceRef"),
        rows=((8, "ABC", "Sample", 44),),
    )
    choice = service.product_codes(2, 10)[0]
    assert choice.label == "ABC  |  Sample"
    assert choice.id == 8
    assert cursor.calls[0][1] == (2, 10, 2, 10)
    assert "ci.CatalogueId IN (-1, ?)" in cursor.calls[0][0]


@pytest.mark.parametrize(("site_id", "catalogue_id"), [(0, 1), (1, 0), (-1, 1)])
def test_product_code_query_rejects_invalid_scope(site_id, catalogue_id):
    service, cursor, _ = make_service(None)
    with pytest.raises(ValueError, match="site and catalogue"):
        service.product_codes(site_id, catalogue_id)
    assert not cursor.calls
