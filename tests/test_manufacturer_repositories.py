"""Home-page HM / Knoll repository status and the QA Article OBX page's Manufacturer (workspace) selector."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QCoreApplication, QSettings, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

from core.application_context import ApplicationContext
from core.config import AppConfig
from services.ocd_engine.catalogue import forget_loaded
from tests.ocd_engine.ocd_repo_fixture import write_plain_range
import ui.pages.pcon_article_obx_generator_page as page_module
from ui.pages.module_home_page import ModuleHomePage
from ui.pages.pcon_article_obx_generator_page import PconArticleObxGeneratorPage

GREEN = "background:#27A032"


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    previous = QSettings.defaultFormat()
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qt"))
    forget_loaded()
    yield
    forget_loaded()
    QSettings.setDefaultFormat(previous)


def drain(timeout_ms: int = 10000) -> None:
    """Let chained background work (fingerprint check -> catalogue load -> article load) finish."""
    for _ in range(5):
        assert QThreadPool.globalInstance().waitForDone(timeout_ms)
        for _ in range(20):
            QCoreApplication.processEvents()


@pytest.fixture
def workspaces(tmp_path):
    """HM: hmx/{aeron, mirra}. Knoll: kno/{os_basics, os_tone} (series-like folder names, discovered, not listed)."""
    hm = tmp_path / "hm" / "_repository"
    knoll = tmp_path / "knoll" / "_repository"
    (hm / "hmx").mkdir(parents=True)
    (knoll / "kno").mkdir(parents=True)
    write_plain_range(hm / "hmx", "aeron", [("AE1", "HM", "AE", "Aeron Chair"), ("AE2", "HM", "AF", "Aeron Stool")])
    write_plain_range(hm / "hmx", "mirra", [("MI1", "HM", "MI", "Mirra Chair")])
    write_plain_range(knoll / "kno", "os_basics", [("KB1", "KNO", "BA", "Basics Desk")])
    write_plain_range(knoll / "kno", "os_tone", [("KT1", "KNO", "TO", "Tone Desk"), ("KT2", "KNO", "TO", "Tone Shelf")])
    return hm, knoll


def config_for(hm, knoll, tmp_path=None) -> AppConfig:
    return AppConfig(hm_repository_workspace=str(hm), knoll_repository_workspace=str(knoll),
                     repository_browser_roots={})


# ------------------------------------------------------------------ home page
def home(config: AppConfig) -> ModuleHomePage:
    return ModuleHomePage(ApplicationContext(config))


def test_both_repositories_connected(workspaces):
    page = home(config_for(*workspaces))
    assert page._hm_repository_status._second.text() == "Connected"
    assert page._knoll_repository_status._second.text() == "Connected"
    assert page._hm_repository_status._dot.styleSheet().startswith(GREEN)
    assert page._knoll_repository_status._dot.styleSheet().startswith(GREEN)
    assert page._hm_repository_status._first.text() == "HM Repository"
    assert page._knoll_repository_status._first.text() == "Knoll Repository"


@pytest.mark.parametrize("down", ["hm", "knoll"])
def test_one_unavailable_repository_does_not_affect_the_other(workspaces, tmp_path, down):
    hm, knoll = workspaces
    gone = tmp_path / "gone" / "_repository"
    page = home(config_for(gone if down == "hm" else hm, gone if down == "knoll" else knoll))
    bad, good = ((page._hm_repository_status, page._knoll_repository_status) if down == "hm"
                 else (page._knoll_repository_status, page._hm_repository_status))
    assert bad._second.text().startswith("Not connected")
    assert not bad._dot.styleSheet().startswith(GREEN)
    assert "Folder not found" in bad.toolTip() and str(gone) in bad.toolTip()
    assert good._second.text() == "Connected" and good._dot.styleSheet().startswith(GREEN)


def test_both_unavailable_each_reports_its_own_reason(tmp_path):
    page = home(config_for(tmp_path / "no_hm", tmp_path / "no_knoll"))
    assert str(tmp_path / "no_hm") in page._hm_repository_status.toolTip()
    assert str(tmp_path / "no_knoll") in page._knoll_repository_status.toolTip()
    assert page._hm_repository_status._second.text().startswith("Not connected")
    assert page._knoll_repository_status._second.text().startswith("Not connected")


def test_status_is_independent_of_active_repository_and_pdm(workspaces, tmp_path):
    hm, knoll = workspaces
    config = config_for(hm, knoll)
    config.repository_browser_roots = {"Seating": str(tmp_path / "no_seating")}      # Active Repository unavailable
    page = home(config)
    assert page._repository_status._second.text().startswith("Not connected")
    assert page._hm_repository_status._second.text() == "Connected"
    assert page._knoll_repository_status._second.text() == "Connected"
    assert page._pdm_status._first.text() == "PDM Database"                           # separate item, untouched


def test_status_strip_keeps_module_order_and_adds_the_two_items(workspaces):
    page = home(config_for(*workspaces))
    items = page._status_strip._items
    assert items.index(page._repository_status) < items.index(page._hm_repository_status) \
        < items.index(page._knoll_repository_status) < items.index(page._pdm_group)
    assert page._mdb_status in items and page._application_status in items


def test_refresh_status_notices_a_repository_coming_and_going(workspaces, tmp_path):
    hm, knoll = workspaces
    config = config_for(hm, knoll)
    page = home(config)
    config.knoll_repository_workspace = str(tmp_path / "unplugged")
    page.refresh_status()
    assert page._knoll_repository_status._second.text().startswith("Not connected")
    assert page._hm_repository_status._second.text() == "Connected"


def test_configured_paths_come_from_config_and_can_be_overridden(tmp_path, monkeypatch):
    import json

    monkeypatch.setenv("TEST_SVN", str(tmp_path))
    settings = tmp_path / "workbench_config.json"
    settings.write_text(json.dumps({"knoll_repository_workspace": "%TEST_SVN%\\kn\\_repository",
                                    "hm_repository_workspace": "%TEST_SVN%\\hm\\_repository"}), encoding="utf-8")
    config = AppConfig.load(settings)
    assert config.manufacturer_workspaces == {"HM": str(tmp_path / "hm" / "_repository"),
                                              "Knoll": str(tmp_path / "kn" / "_repository")}
    assert not config.config_warnings


# ------------------------------------------------------------------ QA page
def _boxes(monkeypatch):
    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(page_module.QMessageBox, name, Mock())
    monkeypatch.setattr(page_module.QMessageBox, "question", Mock(return_value=QMessageBox.StandardButton.Yes))


def make_page(config) -> PconArticleObxGeneratorPage:
    return PconArticleObxGeneratorPage(context=SimpleNamespace(config=config))


def dispose(widget) -> None:
    dialog = getattr(widget, "_progress_dialog", None)
    if dialog is not None:
        dialog.hide()
    widget._article_dialog.hide()
    widget._catalogue_poll.stop()
    widget.deleteLater()
    drain()


@pytest.fixture
def qa(workspaces, monkeypatch):
    _boxes(monkeypatch)
    widgets = []

    def build(hm=None, knoll=None):
        config = config_for(hm or workspaces[0], knoll or workspaces[1])
        widget = make_page(config)
        widgets.append(widget)
        drain()
        return widget

    yield build
    for widget in widgets:
        dispose(widget)


def options(combo):
    return [combo.itemData(i) for i in range(combo.count())]


def programs(widget):
    return [widget._program.itemData(i).program for i in range(widget._program.count())]


def pick(combo, data):
    index = combo.findData(data)
    assert index >= 0
    combo.setCurrentIndex(index)
    drain()


def select_program(widget, name):
    """Choose a program as a user does; a program that is already shown is re-chosen so its articles load."""
    index = next(i for i in range(widget._program.count()) if widget._program.itemData(i).program == name)
    if widget._program.currentIndex() == index:
        other = next((i for i in range(widget._program.count()) if i != index), None)
        if other is not None:
            widget._program.setCurrentIndex(other)
            drain()
    widget._program.setCurrentIndex(index)
    drain()


def article_numbers(widget):
    return [widget._article_table.item(r, 0).text() for r in range(widget._article_table.rowCount())]


def test_dropdown_offers_the_configured_manufacturers(qa):
    widget = qa()
    assert options(widget._manufacturer) == ["HM", "Knoll"]


def test_hm_selection_loads_only_hm_repository_data(qa):
    widget = qa()
    pick(widget._manufacturer, "HM")
    assert programs(widget) == ["aeron", "mirra"]
    select_program(widget, "aeron")
    assert [widget._series.itemData(i) for i in range(widget._series.count())] == ["", "AE", "AF"]
    assert article_numbers(widget) == ["AE1", "AE2"]
    assert {widget._program.itemData(i).manufacturer_id for i in range(widget._program.count())} == {"HM"}


def test_knoll_selection_loads_only_knoll_repository_data(qa):
    widget = qa()
    pick(widget._manufacturer, "Knoll")
    assert programs(widget) == ["os_basics", "os_tone"]                 # discovered from the repository, not configured
    select_program(widget, "os_tone")
    assert article_numbers(widget) == ["KT1", "KT2"]
    assert {widget._program.itemData(i).manufacturer_id for i in range(widget._program.count())} == {"KNO"}
    assert not any(n.startswith(("AE", "MI")) for n in article_numbers(widget))


def test_switching_manufacturer_clears_stale_selection_and_results(qa):
    widget = qa()
    pick(widget._manufacturer, "HM")
    select_program(widget, "aeron")
    widget._article_table.selectRow(0)
    widget._outcome = SimpleNamespace(exportable=[object()], skus=[])        # a result from HM
    widget._outcome_program = widget._selected_program()
    widget._generation_status.setText("Generated 4 SKUs")
    widget._generators[widget._selected_program().db_dir] = object()

    widget._manufacturer.blockSignals(True)
    widget._manufacturer.setCurrentIndex(widget._manufacturer.findData("Knoll"))
    widget._manufacturer.blockSignals(False)
    widget._on_manufacturer_selected()                                      # the synchronous part of the switch

    assert widget._articles == [] and widget._article_table.rowCount() == 0
    assert widget._outcome is None and widget._outcome_program is None
    assert widget._generators == {}
    assert widget._generation_status.text() == "No generation run yet."
    assert widget._program.count() == 0 and widget._series.count() == 0
    assert not widget._export_action.isEnabled() and not widget._validator_action.isEnabled()
    drain()
    assert programs(widget) == ["os_basics", "os_tone"]                    # Knoll's own list, nothing from HM
    assert widget._selected_program() is None or widget._selected_program().manufacturer_id == "KNO"


def test_switching_back_and_forth_never_mixes_records(qa):
    widget = qa()
    for label, expected in (("Knoll", ["os_basics", "os_tone"]), ("HM", ["aeron", "mirra"]),
                            ("Knoll", ["os_basics", "os_tone"])):
        pick(widget._manufacturer, label)
        assert programs(widget) == expected
        assert widget._articles == []


def test_unavailable_workspace_shows_error_and_blocks_qa_execution(qa, workspaces, tmp_path, monkeypatch):
    hm, _knoll = workspaces
    gone = tmp_path / "unplugged" / "_repository"
    widget = qa(knoll=gone)
    pick(widget._manufacturer, "Knoll")
    assert widget._program.count() == 0
    assert "Knoll repository is not available" in widget._catalogue_status.text()
    assert str(gone) in widget._catalogue_status.text()
    assert not widget._program.isEnabled()

    widget._outcome = SimpleNamespace(exportable=[object()], skus=[object()])
    widget._outcome_program = SimpleNamespace(manufacturer_id="KNO")
    widget._update_controls()
    assert not widget._export_action.isEnabled() and not widget._validator_action.isEnabled()
    for action in (widget._load_articles, widget._generate, widget._export_obx, widget._prepare_for_validator,
                   widget._price_generated_skus):
        before = page_module.QMessageBox.warning.call_count
        action()
        assert page_module.QMessageBox.warning.call_count == before + 1
    assert widget._run is None                                               # nothing was started

    pick(widget._manufacturer, "HM")                                        # the other repository still works
    assert programs(widget) == ["aeron", "mirra"] and widget._workspace_error == ""


def test_workspace_that_disappears_after_loading_blocks_execution(qa, workspaces, monkeypatch):
    widget = qa()
    pick(widget._manufacturer, "HM")
    select_program(widget, "aeron")
    real = page_module.check_location
    hm_path = str(workspaces[0])
    monkeypatch.setattr(page_module, "check_location",
                        lambda p: real(str(p) + "_gone") if str(p) == hm_path else real(p))
    before = page_module.QMessageBox.warning.call_count
    widget._load_articles()
    assert page_module.QMessageBox.warning.call_count == before + 1
    assert widget._run is None


def test_manufacturer_ids_reach_the_export_from_the_selected_repository(qa):
    widget = qa()
    pick(widget._manufacturer, "Knoll")
    select_program(widget, "os_basics")
    assert widget._selected_program().manufacturer_id == "KNO"
    assert str(widget._selected_program().db_dir).startswith(str(widget._workspaces["Knoll"]))
