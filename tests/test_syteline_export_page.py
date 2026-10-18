from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from core.application_context import ApplicationContext
from core.config import AppConfig
import ui.pages.syteline_export_page as page_module
import services.syteline_export.metadata_service as metadata_module


class MemorySettings:
    def __init__(self):
        self.values = {}

    def value(self, key, default=None, type=None):
        value = self.values.get(key, default)
        if type is bool:
            return bool(value)
        if type is str:
            return str(value)
        if type is list:
            return list(value) if value is not None else []
        return value

    def setValue(self, key, value):
        self.values[key] = value

    def sync(self):
        pass


class Choice:
    def __init__(self, id, label, code="", description="", extra_id=None):
        self.id, self.label, self.code = id, label, code
        self.description, self.extra_id = description, extra_id


class FakeMetadata:
    def __init__(self, context):
        pass

    def sites(self):
        return [Choice(1, "UK", "UK")]

    def languages(self):
        return [Choice(2, "English", "en-GB")]

    def currencies(self):
        return [Choice(3, "GBP")]

    def catalogues(self, user_id):
        assert user_id == 123
        return [Choice(10, "Example Catalogue")]

    def product_codes(self, site_id, catalogue_id):
        assert (site_id, catalogue_id) == (1, 10)
        return [Choice(8, "ABC  |  Sample", "ABC", "Sample", 44)]


_APP = None


def make_page(monkeypatch):
    global _APP
    _APP = QApplication.instance() or QApplication([])
    monkeypatch.setattr(page_module, "QSettings", MemorySettings)
    monkeypatch.setattr(metadata_module, "SyteLineMetadataService", FakeMetadata)
    return page_module.SyteLineExportPage(ApplicationContext(AppConfig()))


def test_scope_modes_are_mutually_exclusive_like_legacy(monkeypatch):
    page = make_page(monkeypatch)
    page.range_check.setChecked(True)
    assert page.range_check.isChecked()
    assert not page.list_check.isChecked()
    assert not page.export_products.isChecked()
    assert page.min_item.isEnabled()
    assert page.max_item.isEnabled()
    assert not page.item_list.isEnabled()
    page.list_check.setChecked(True)
    assert page.list_check.isChecked()
    assert not page.range_check.isChecked()
    assert not page.export_products.isChecked()
    assert page.item_list.isEnabled()
    assert not page.min_item.isEnabled()
    page.export_products.setChecked(True)
    assert page.export_products.isChecked()
    assert not page.range_check.isChecked()
    assert not page.list_check.isChecked()
    assert not page.item_list.isEnabled()


def test_product_line_filter_only_enables_with_product_scope(monkeypatch):
    page = make_page(monkeypatch)
    assert not page.product_line.isEnabled()
    page.filter_product_code.setChecked(True)
    assert page.product_line.isEnabled()
    page.range_check.setChecked(True)
    assert not page.product_line.isEnabled()
    page.export_products.setChecked(True)
    assert page.product_line.isEnabled()


def test_database_choices_load_with_ids_and_user_scoped_catalogues(monkeypatch):
    page = make_page(monkeypatch)
    page.pdm_user_id.setText("123")
    page._load_database_choices()
    assert page.site.currentText() == "UK"
    assert page.site.currentData() == 1
    assert page.language.currentData() == 2
    assert page.currency.currentData() == 3
    assert page.catalogue.currentData() == 10
    assert page.product_line.currentData() == 8
    assert "Loaded 1 sites" in page.status.text()


def test_database_choices_require_numeric_user_id(monkeypatch):
    page = make_page(monkeypatch)
    page.pdm_user_id.setText("abc")
    page._load_database_choices()
    assert "positive integer" in page.status.text()


def test_ofda_xml_actions_are_present_but_guarded(monkeypatch):
    page = make_page(monkeypatch)
    assert page.compare_xml.text() == "Compare"
    assert page.validate_xml.text() == "Validate"
    assert not page.compare_xml.isEnabled()
    assert not page.validate_xml.isEnabled()
