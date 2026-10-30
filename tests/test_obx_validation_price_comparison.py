import csv
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTableWidget

from services.sif_validation_service import SifResult, SifValidationService
from ui.pages.obx_validation_page import ObxValidationPage


def _app():
    return QApplication.instance() or QApplication([])


def _write_obx_result_row(result):
    _app()
    page = SimpleNamespace(
        _table=QTableWidget(0, 11),
        _seq_key=ObxValidationPage._seq_key,
        _price_difference_text=ObxValidationPage._price_difference_text,
        _file_of_seq={},
        _source_path="",
    )
    ObxValidationPage._put_row(page, 0, result)
    return [page._table.item(0, column).text() for column in range(11)]


def test_obx_results_show_pdm_minus_obx_and_preserve_both_prices():
    result = SifResult(
        seq=1,
        sku="SKU OPTION",
        currency="GBP",
        sif_price=9.2,
        pdm_price=10.1,
        status="price_mismatch",
    )

    cells = _write_obx_result_row(result)

    assert cells[2] == "GBP"
    assert cells[5:8] == ["9.20", "10.10", "0.90"]
    assert result.sif_price == 9.2
    assert result.pdm_price == 10.1


def test_obx_price_difference_is_negative_and_missing_price_is_blank():
    assert ObxValidationPage._price_difference_text(
        SifResult(sif_price=10.3, pdm_price=10.1)
    ) == "-0.20"
    assert ObxValidationPage._price_difference_text(
        SifResult(sif_price=10.1, pdm_price=None)
    ) == "-"
    assert ObxValidationPage._price_difference_text(
        SifResult(sif_price=None, pdm_price=10.1)
    ) == "-"


def test_obx_export_uses_record_currency_and_currency_neutral_price_headers(tmp_path):
    output = tmp_path / "obx-validation.csv"
    results = [
        SifResult(sku="EUR SKU", currency="EUR", pdm_price=12.34, sif_price=12.0),
        SifResult(sku="GBP SKU", currency="GBP", pdm_price=23.45, sif_price=23.0),
    ]

    SifValidationService.__new__(SifValidationService).export_csv(
        output, "EUR", results, source_label="OBX"
    )

    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == [
        "SKU", "Currency", "Category (PLC)", "PDM List Price",
        "OBX List Price", "OBX Qty", "Result",
    ]
    assert rows[1][1] == "EUR"
    assert rows[2][1] == "GBP"
    assert "EUR" not in rows[0]
    assert "Euro" not in rows[0]


def test_sif_export_keeps_its_existing_single_currency_headers(tmp_path):
    output = tmp_path / "sif-validation.csv"

    SifValidationService.__new__(SifValidationService).export_csv(
        output, "EUR", [SifResult(sku="SKU", sif_price=12.0, pdm_price=12.0)]
    )

    with output.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    assert header == [
        "SKU", "Category (PLC)", "PDM List Price (EUR)",
        "SIF List Price (EUR)", "SIF Qty", "Result",
    ]
