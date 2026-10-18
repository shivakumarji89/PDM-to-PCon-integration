from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.syteline_export.auxiliary_output_service import (
    PRICE_FORMULA_HEADER,
    PRODUCT_CODE_HEADER,
    SyteLineAuxiliaryOutputService,
)


class FakeCursor:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []

    def execute(self, query, *parameters):
        self.calls.append((query, parameters))
        return self

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


def make_service(rows=()):
    cursor = FakeCursor(rows)
    connection = FakeConnection(cursor)
    service = SyteLineAuxiliaryOutputService(
        SimpleNamespace(config=SimpleNamespace()),
        connection_factory=lambda: connection,
    )
    return service, cursor, connection


def test_price_formula_query_is_parameterized_and_deduplicates_codes():
    service, cursor, connection = make_service((("UK", "C1", "P1", "F1", 12.5, "18 Oct 2026"),))
    rows = service.price_formula_rows(2, ["P1", "P1", " P2 ", ""])
    assert rows[0][2] == "P1"
    query, parameters = cursor.calls[0]
    assert parameters == (2, "P1", "P2")
    assert "pm.ItemPriceCode IN (?, ?)" in query
    assert connection.closed


def test_product_code_query_is_parameterized():
    service, cursor, _ = make_service((("UK", "ABC", "Sample", "GBP"),))
    assert service.product_code_rows(1, ["ABC"])[0] == ("UK", "ABC", "Sample", "GBP")
    assert cursor.calls[0][1] == (1, "ABC")
    assert "pc.Product_Code IN (?)" in cursor.calls[0][0]


def test_auxiliary_queries_require_valid_site_and_skip_empty_code_lists():
    service, cursor, _ = make_service()
    with pytest.raises(ValueError, match="site ID"):
        service.price_formula_rows(0, ["P1"])
    with pytest.raises(ValueError, match="site ID"):
        service.product_code_rows(-1, ["ABC"])
    assert service.price_formula_rows(1, []) == []
    assert service.product_code_rows(1, []) == []
    assert not cursor.calls


def test_price_formula_writer_uses_legacy_header_and_atomic_tsv(tmp_path):
    service, _, _ = make_service((("UK", "C1", "P1", "F1", 12.5, "18 Oct 2026"),))
    target = tmp_path / "priceformula.txt"
    service.write_price_formula(target, 2, ["P1"])
    assert not target.read_bytes().startswith(b"\\xef\\xbb\\xbf")
    with target.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream, delimiter="\t"))
    assert tuple(rows[0]) == PRICE_FORMULA_HEADER
    assert rows[1] == ["UK", "C1", "P1", "F1", "12.5", "18 Oct 2026"]


def test_product_code_writer_preserves_legacy_four_field_row_under_five_field_header(tmp_path):
    service, _, _ = make_service((("UK", "ABC", "Sample", "GBP"),))
    target = tmp_path / "productcode.txt"
    service.write_product_codes(target, 1, ["ABC"])
    with target.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream, delimiter="\t"))
    assert tuple(rows[0]) == PRODUCT_CODE_HEADER
    assert rows[1] == ["UK", "ABC", "Sample", "GBP"]
    assert len(rows[0]) == 5 and len(rows[1]) == 4


def test_writer_requires_existing_directory(tmp_path):
    service, _, _ = make_service()
    with pytest.raises(ValueError, match="does not exist"):
        service._write_tsv(tmp_path / "missing" / "out.tsv", PRICE_FORMULA_HEADER, [])


def test_writer_matches_legacy_literal_tab_concatenation(tmp_path):
    target = tmp_path / "raw.tsv"
    SyteLineAuxiliaryOutputService._write_tsv(
        target, ("First", "Second"), (("contains\ttab", "value"),)
    )
    with target.open(encoding="utf-8", newline="") as stream:
        output = stream.read()
    assert output == "First\tSecond\r\ncontains\ttab\tvalue\r\n"


def test_header_only_outputs_match_legacy_verbose_extract(tmp_path):
    outputs = SyteLineAuxiliaryOutputService.write_header_only_outputs(tmp_path, "PDMExport")
    assert outputs["description"].name == "PDMExport_description_data.txt"
    assert outputs["planning"].name == "PDMExport_planning_data.txt"
    with outputs["description"].open(encoding="utf-8", newline="") as stream:
        description = stream.read()
    with outputs["planning"].open(encoding="utf-8", newline="") as stream:
        planning = stream.read()
    assert description == "Lang\tItem\tDescription\r\n"
    assert planning.startswith("Item\tDescription\tProduct Code\tVendor Call\tStocked\tDock to Stock\t")
    assert planning.endswith("Kanban qty\r\n")
    assert outputs["description"].parent == tmp_path / "temp"


def test_header_only_outputs_use_csi_suffix(tmp_path):
    outputs = SyteLineAuxiliaryOutputService.write_header_only_outputs(
        tmp_path, "PDMExport", format_csi=True
    )
    assert outputs["description"].name == "PDMExport_description_data_csi.txt"
    assert outputs["planning"].name == "PDMExport_planning_data_csi.txt"
