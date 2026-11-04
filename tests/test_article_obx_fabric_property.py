"""The one manual option of the Article OBX Generator page: **Fabric property**.

Standalone fixtures (the older page tests need an ``_output_path`` widget the page no longer has). The repository is the
synthetic fabric range of ``tests/ocd_engine/test_ocd_fabric_override.py``.
"""
from __future__ import annotations

from unittest.mock import Mock

import pytest
from PySide6.QtCore import QCoreApplication, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

import ui.pages.pcon_article_obx_generator_page as page_module
from services.ocd_engine.catalogue import OcdCatalogueService
from services.ocd_engine.generator import OcdArticleGenerator
from tests.ocd_engine.test_ocd_fabric_override import NO_KEYWORDS, build
from ui.pages.pcon_article_obx_generator_page import PconArticleObxGeneratorPage


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def drain(timeout_ms: int = 10000) -> None:
    assert QThreadPool.globalInstance().waitForDone(timeout_ms)
    for _ in range(20):
        QCoreApplication.processEvents()


def dispose(widget) -> None:
    dialog = getattr(widget, "_progress_dialog", None)
    if dialog is not None:
        dialog.hide()
    widget._article_dialog.hide()
    widget.deleteLater()
    drain()


@pytest.fixture
def make_page(monkeypatch, tmp_path):
    made = []

    def factory(**build_kw):
        widget, seen = _make_page(monkeypatch, tmp_path, **build_kw)
        made.append(widget)
        return widget, seen

    yield factory
    for widget in made:
        dispose(widget)


def _make_page(monkeypatch, tmp_path, **build_kw):
    monkeypatch.setattr(page_module.QMessageBox, "information", Mock())
    monkeypatch.setattr(page_module.QMessageBox, "warning", Mock())
    monkeypatch.setattr(page_module.QMessageBox, "critical", Mock())
    monkeypatch.setattr(page_module.QMessageBox, "question", Mock(return_value=QMessageBox.StandardButton.Yes))
    root = tmp_path / "hmx"
    root.mkdir()
    build(root, **build_kw)
    seen = {}

    class Spy(OcdArticleGenerator):
        def generate(self, article_numbers, rules=(), **kwargs):
            seen.update(kwargs)
            return super().generate(article_numbers, rules, **kwargs)

    widget = PconArticleObxGeneratorPage(context=None, catalogue=OcdCatalogueService(root), generator_factory=Spy)
    widget._load_catalogue()
    drain()
    widget._manufacturer.setCurrentIndex(widget._manufacturer.findData("MK"))
    widget._program.setCurrentIndex(0)
    widget._load_articles()
    drain()
    widget._article_dialog.hide()
    widget._currency.setCurrentText("EUR")
    return widget, seen


def select_article(widget):
    widget._article_table.selectRow(0)


def offered(widget):
    box = widget._fabric_property
    return [(box.itemText(i), box.itemData(i)) for i in range(box.count())]


def generate(widget):
    widget._generate()
    drain()
    return widget._outcome


def test_there_is_exactly_one_fabric_selector_and_it_starts_on_automatic(make_page):
    widget, _ = make_page()
    boxes = [name for name in vars(widget) if "fabric" in name.lower()]
    assert boxes == ["_fabric_property"]                      # no type/colour/group/relation selectors
    assert offered(widget) == [("Automatic", "")] and not widget._fabric_property.isEnabled()


def test_the_selector_lists_the_selected_articles_properties_with_their_labels(make_page):
    widget, _ = make_page()
    select_article(widget)
    items = dict(offered(widget))
    assert items["Automatic"] == ""
    assert items["Cover - Upholstery type"] == "Cover" and items["Shade"] == "Shade"
    assert items["Fabric_Care - Care"] == "Fabric_Care" and widget._fabric_property.isEnabled()
    first_after_automatic = widget._fabric_property.itemData(1)
    assert first_after_automatic in ("Cover", "Fabric_Care")      # keyword candidates are listed first


def test_the_choice_reaches_the_generator_and_automatic_sends_nothing(make_page):
    widget, seen = make_page(labels=NO_KEYWORDS)
    select_article(widget)
    outcome = generate(widget)
    assert seen["fabric_property"] == "" and len(outcome.skus) == 5 * 2 * 2    # no keyword: every colour stays
    widget._fabric_property.setCurrentIndex(widget._fabric_property.findData("Shade"))
    outcome = generate(widget)
    assert seen["fabric_property"] == "Shade" and len(outcome.skus) == 2 * 2 * 2
    widget._fabric_property.setCurrentIndex(0)                                  # back to Automatic
    assert len(generate(widget).skus) == 5 * 2 * 2 and seen["fabric_property"] == ""


def test_an_unresolvable_choice_is_reported_and_nothing_is_enumerated(make_page):
    widget, _ = make_page(labels=NO_KEYWORDS)
    select_article(widget)
    widget._fabric_property.setCurrentIndex(widget._fabric_property.findData("Grade"))
    widget._generate()
    drain()
    assert widget._outcome is None
    text = widget._generation_status.text() + " ".join(str(c) for c in page_module.QMessageBox.critical.call_args_list)
    assert "no fabric type/colour relationship" in text or "Grade" in text


def test_the_choice_is_kept_while_still_offered_and_reset_when_the_selection_changes(make_page):
    widget, _ = make_page()
    select_article(widget)
    widget._fabric_property.setCurrentIndex(widget._fabric_property.findData("Shade"))
    widget._on_article_selection_changed()
    assert widget._fabric_property.currentData() == "Shade"
    widget._article_table.clearSelection()
    assert widget._fabric_property.currentData() == "" and not widget._fabric_property.isEnabled()


def test_fabric_notes_are_available_as_the_status_tooltip(make_page):
    widget, _ = make_page()
    select_article(widget)
    generate(widget)
    assert "Shade for Cover='A'" in widget._generation_status.toolTip()
