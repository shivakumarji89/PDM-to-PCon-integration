from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from core.application_context import ApplicationContext
from core.config import AppConfig
import ui.pages.syteline_export_page as page_module


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


_APP = None


def make_page(monkeypatch):
    global _APP
    _APP = QApplication.instance() or QApplication([])
    monkeypatch.setattr(page_module, "QSettings", MemorySettings)
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
