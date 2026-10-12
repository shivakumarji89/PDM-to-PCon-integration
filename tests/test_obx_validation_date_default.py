from types import SimpleNamespace

from PySide6.QtCore import QDate

from ui.pages.obx_validation_page import ObxValidationPage


def test_obx_source_date_uses_price_date_format():
    lines = [SimpleNamespace(source_date="03-Sep-2026")]

    assert ObxValidationPage._date_from_source_lines(lines) == QDate(2026, 9, 3)


def test_obx_source_date_skips_missing_and_invalid_values():
    lines = [
        SimpleNamespace(source_date=""),
        SimpleNamespace(source_date="not-a-date"),
        SimpleNamespace(source_date="2026-11-11"),
    ]

    assert ObxValidationPage._date_from_source_lines(lines) == QDate(2026, 11, 11)


def test_obx_source_date_returns_none_when_no_valid_date_exists():
    lines = [
        SimpleNamespace(source_date=""),
        SimpleNamespace(source_date="32-Nov-2026"),
    ]

    assert ObxValidationPage._date_from_source_lines(lines) is None


def test_obx_source_date_uses_first_valid_date_in_loaded_line_order():
    lines = [
        SimpleNamespace(source_date=""),
        SimpleNamespace(source_date="03-Sep-2026"),
        SimpleNamespace(source_date="2026-11-11"),
    ]

    assert ObxValidationPage._date_from_source_lines(lines) == QDate(2026, 9, 3)
