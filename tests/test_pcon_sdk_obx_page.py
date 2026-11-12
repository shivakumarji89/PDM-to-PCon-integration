"""Workflow registration and page behaviour for QA → Article OBX Generator (standalone OCD Engine)."""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import Mock

import pytest
from PySide6.QtCore import QCoreApplication, QDate, QItemSelectionModel, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

from core.enums import WorkflowStep
from core.modules import WorkbenchModule, module_workflows
from core.workflow import WORKFLOW_ITEMS
from services.ocd_engine.catalogue import CatalogueError, OcdCatalogueService
from services.ocd_engine.generator import OcdArticleGenerator
from tests.ocd_engine.ocd_repo_fixture import CHAIR1_FINALS, write_demo_range, write_plain_range
import ui.pages.pcon_article_obx_generator_page as page_module
from ui.pages.pcon_article_obx_generator_page import PconArticleObxGeneratorPage
from workflow.manager import WorkflowManager


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def drain(timeout_ms: int = 10000) -> None:
    assert QThreadPool.globalInstance().waitForDone(timeout_ms)
    for _ in range(20):
        QCoreApplication.processEvents()


def dispose(widget) -> None:
    """Hide the page's progress dialog and delete the page, then flush pending deletes."""
    dialog = getattr(widget, "_progress_dialog", None)
    if dialog is not None:
        dialog.hide()
    widget._article_dialog.hide()
    widget.deleteLater()
    drain()


def test_step_is_registered_under_qa_and_in_workflow_items():
    steps = [item.step for item in WORKFLOW_ITEMS]
    assert WorkflowStep.PCON_ARTICLE_OBX_GENERATOR in steps
    item = next(i for i in WORKFLOW_ITEMS if i.step == WorkflowStep.PCON_ARTICLE_OBX_GENERATOR)
    assert item.title == "Article OBX Generator (OCD Engine)"
    qa = module_workflows(WorkbenchModule.QA_VALIDATION)
    assert WorkflowStep.PCON_ARTICLE_OBX_GENERATOR in qa and WorkflowStep.ARTICLE_OBX_GENERATOR not in qa   # legacy removed
    # Other modules are untouched.
    for module in (WorkbenchModule.DEVELOPMENT, WorkbenchModule.MAINTENANCE, WorkbenchModule.METATYPE,
                   WorkbenchModule.BULK_UPDATE, WorkbenchModule.SYTELINE_EXPORT, WorkbenchModule.OAP):
        assert WorkflowStep.PCON_ARTICLE_OBX_GENERATOR not in module_workflows(module)


def test_main_window_constructs_the_page_for_the_step():
    import ui.main_window as main_window
    assert main_window.PconArticleObxGeneratorPage is PconArticleObxGeneratorPage


def test_step_is_standalone_in_workflow_manager():
    class Host:
        def __init__(self):
            self.current = None

        def show(self, step):
            self.current = step

        def is_ready(self, step):
            return True

        def has_page(self, step):
            return True

        def refresh(self, step):
            pass

    from core.application_context import ApplicationContext
    from core.config import AppConfig

    steps = [item.step for item in WORKFLOW_ITEMS]
    manager = WorkflowManager(ApplicationContext(AppConfig()), Host(), steps)
    assert WorkflowStep.PCON_ARTICLE_OBX_GENERATOR in manager.enabled_steps()


def _plain_articles(root):
    write_plain_range(root, "demo", [
        ("CHAIR1", "MK", "DM", "Demo Chair"), ("STOOL1", "MK", "DM", "Demo Stool"),
        ("BROKEN", "MK", "DM", "Broken Item"), ("DUPE", "MK", "DM", "Duplicate"),
        ("DUPE", "MK", "DM", "Duplicate again"), ("TABLE1", "MK", "DX", "Demo Table"),
    ])
    write_plain_range(root, "found", [("FOUND1", "MK", "", "Foundation Item")])
    write_plain_range(root, "office", [("DESK1", "EG", "AX", "Desk A"), ("DESK2", "EG", "BX", "Desk B")])


@pytest.fixture
def ocd_root(tmp_path):
    root = tmp_path / "hmx"
    root.mkdir()
    _plain_articles(root)
    (root / "assets").mkdir()          # a folder without OCD data
    return root


@pytest.fixture
def generation_root(tmp_path):
    """A repository whose ``demo`` range is fully configurable (see ocd_repo_fixture)."""
    root = tmp_path / "gen_hmx"
    root.mkdir()
    write_demo_range(root)
    return root


def _select(combo, data):
    index = combo.findData(data)
    assert index >= 0, f"{data!r} not offered; have {[combo.itemData(i) for i in range(combo.count())]}"
    combo.setCurrentIndex(index)


def _program(widget, name):
    for index in range(widget._program.count()):
        if widget._program.itemData(index).program == name:
            widget._program.setCurrentIndex(index)
            return
    raise AssertionError(f"program {name} not offered")


def _boxes(monkeypatch):
    monkeypatch.setattr(page_module.QMessageBox, "information", Mock())
    monkeypatch.setattr(page_module.QMessageBox, "warning", Mock())
    monkeypatch.setattr(page_module.QMessageBox, "critical", Mock())
    monkeypatch.setattr(page_module.QMessageBox, "question", Mock(return_value=QMessageBox.StandardButton.Yes))
    monkeypatch.setattr(page_module.QMessageBox, "exec", Mock(return_value=0))   # the Price Diagnostics dialog


@pytest.fixture
def no_plugin(monkeypatch):
    """Importing any pCon plugin/SDK/launcher module fails the test: generation must not need pCon."""
    import importlib.abc
    import sys

    class Forbidden(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            if name.startswith(("services.pcon_sdk_obx", "services.pcon_launcher")):
                raise AssertionError(f"{name} must not be used by the standalone generator")
            return None

    finder = Forbidden()
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])


def generation_available(widget) -> bool:
    """Generation has no button any more (it starts when the article dialog is accepted); this is its precondition."""
    return (widget._run is None and widget._selected_program() is not None
            and bool(widget._article_table.selectedIndexes()))


def _save_dialog_returns(monkeypatch, path) -> Mock:
    """The page asks for the OBX path when exporting (there is no output-path field any more)."""
    dialog = Mock(return_value=(str(path), "OBX files (*.obx)"))
    monkeypatch.setattr(page_module.QFileDialog, "getSaveFileName", dialog)
    return dialog


@pytest.fixture
def page(tmp_path, monkeypatch, ocd_root, no_plugin):
    _boxes(monkeypatch)
    widget = PconArticleObxGeneratorPage(context=None, catalogue=OcdCatalogueService(ocd_root))
    _save_dialog_returns(monkeypatch, tmp_path / "page.obx")
    yield widget
    dispose(widget)


def _open_demo(widget):
    widget._load_catalogue()
    drain()
    _select(widget._manufacturer, "MK")
    _program(widget, "demo")          # choosing a program loads its articles automatically
    drain()
    _select(widget._series, "DM")     # and so does choosing a series
    drain()


@pytest.fixture
def gen_page(tmp_path, monkeypatch, generation_root, no_plugin):
    _boxes(monkeypatch)
    widget = PconArticleObxGeneratorPage(context=None, catalogue=OcdCatalogueService(generation_root))
    _save_dialog_returns(monkeypatch, tmp_path / "page.obx")
    _open_demo(widget)
    yield widget
    dispose(widget)


def _pick(widget, article):
    widget._article_filter.setText(article)
    widget._article_table.selectRow(0)


def _results(widget, column=2):
    model = widget._result_model
    return [model.text(r, column) for r in range(model.rowCount())]


def _generate(widget):
    """Generation is unpriced: it only enumerates the valid SKUs (pricing is a separate, on-demand step)."""
    widget._generate()
    drain()


def _price(widget, currency="EUR", rows=None):
    """Price the selected SKU rows (all by default) with the chosen currency, as the Price Selected button does."""
    widget._currency.setCurrentText(currency)
    if rows is None:
        widget._result_table.selectAll()
    else:
        selection = widget._result_table.selectionModel()
        selection.clearSelection()
        for row in rows:
            selection.select(widget._result_proxy.index(row, 0),
                             QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    widget._price_generated_skus()
    drain()


def _generate_and_price(widget, currency="EUR"):
    _generate(widget)
    _price(widget, currency)


def test_page_has_no_plugin_connection_controls(no_plugin, monkeypatch):
    _boxes(monkeypatch)      # the page loads its catalogue itself; with no repository configured that reports an error
    widget = PconArticleObxGeneratorPage(context=None)
    assert widget.is_ready()
    assert not generation_available(widget) and not widget._obx_actions_button.isEnabled()
    for removed in ("_connection_status", "_job_dir_label", "_check_button", "_install_button",
                    "_bridge", "_catalog", "_generation", "_discard_planning"):
        assert not hasattr(widget, removed)
    texts = {button.text() for button in widget.findChildren(page_module.QPushButton)}
    assert "Price Selected" in texts
    assert {a.text() for a in widget._obx_actions_button.menu().actions()} == {"Export OBX", "Prepare for Validator"}
    assert "Load Articles" not in texts and "Export OBX" not in texts   # articles load automatically; export is in the dropdown
    assert "Generate Valid SKUs" not in texts      # generation starts when the article dialog is accepted
    assert "Inspect Properties" not in texts and "Max SKUs:" not in texts
    assert not {"Check Connection", "Install Plugin"} & texts
    assert widget.header.title_label.text() == "Article OBX Generator (OCD Engine)"
    dispose(widget)


def test_page_module_has_no_pcon_runtime_dependency(monkeypatch):
    _boxes(monkeypatch)
    source = open(page_module.__file__, encoding="utf-8").read()
    for name in ("PconPluginBridge", "PconLauncher", "pcon_launcher", "launch_planner", "Launch pCon",
                 "PconCatalogService", "PconObxGenerationService", "PconConfigurationService",
                 "ReferenceObxComparer", "FakePconPlugin", "heartbeat", "job_dir", "send(",
                 "import pcon", "from services.pcon"):
        assert name not in source, name
    widget = page_module.PconArticleObxGeneratorPage(context=None)
    texts = {button.text() for button in widget.findChildren(page_module.QPushButton)}
    assert not any("pcon" in text.lower() for text in texts)
    dispose(widget)




# ---- the standalone workflow: catalogue -> articles -> properties -> SKUs -> OBX ----
def test_page_runs_the_complete_standalone_workflow(gen_page, tmp_path):
    widget = gen_page
    assert widget._article_table.rowCount() == 5            # loaded automatically when the series was chosen
    assert [widget._currency.itemText(i) for i in range(widget._currency.count())] == ["EUR", "GBP"]
    _pick(widget, "chair1")
    assert generation_available(widget) and not widget._obx_actions_button.isEnabled()

    widget._price_date.setDate(QDate.fromString("2026-01-15", "yyyy-MM-dd"))
    _generate(widget)                        # automatic: no property inspection needed, and no pricing yet
    assert _results(widget) == CHAIR1_FINALS
    assert _results(widget, 5) == ["", "", ""]
    assert _results(widget, 4)[1] == "Material=W; Size=L"
    assert "Generated 3 valid unique SKU(s)" in widget._generation_status.text()
    assert "Pricing not run" in widget._generation_status.text()
    assert not widget._obx_actions_button.isEnabled()        # unpriced SKUs cannot be exported
    assert not widget._diagnostics_button.isEnabled()        # Price Selected needs selected rows

    widget._result_table.selectAll()
    assert widget._diagnostics_button.isEnabled()
    _price(widget, "EUR")
    assert _results(widget, 5) == ["100.00 EUR", "125.00 EUR", "100.00 EUR"]
    assert "Price selection complete: 3 selected SKU(s) processed; 3 total priced and 0 unpriced" in \
        widget._generation_status.text()
    assert widget._obx_actions_button.isEnabled() and widget._export_action.isEnabled()
    assert not (tmp_path / "page.obx").exists()          # generating and pricing do not write; Export does

    widget._export_obx()
    drain()
    assert (tmp_path / "page.obx").is_file()
    assert "Exported 3 SKU(s)" in widget._generation_status.text()
    assert "3 article line(s) read back" in widget._generation_status.text()
    assert widget._validation_label.text() == ""
    text = (tmp_path / "page.obx").read_text(encoding="utf-8")
    assert "DEMO_OPT.Material=W;DEMO_OPT.Size=L" in text and 'value="125.00"' in text


def test_selected_program_series_and_articles_reach_the_generator(tmp_path, monkeypatch, generation_root, no_plugin):
    _boxes(monkeypatch)
    seen = {}

    class Spy(OcdArticleGenerator):
        def generate(self, article_numbers, rules=(), **kwargs):
            seen.update(db_dir=self.db_dir, articles=list(article_numbers), **kwargs)
            return super().generate(article_numbers, rules, **kwargs)

        def price_skus(self, skus, **kwargs):
            seen["priced"] = (len(skus), kwargs["currency"], kwargs["price_date"])
            return super().price_skus(skus, **kwargs)

    widget = PconArticleObxGeneratorPage(
        context=None, catalogue=OcdCatalogueService(generation_root), generator_factory=Spy)
    _open_demo(widget)
    _pick(widget, "chair1")
    widget._price_date.setDate(QDate.fromString("2026-02-03", "yyyy-MM-dd"))
    _generate(widget)
    assert seen["db_dir"] == generation_root / "demo" / "ANY" / "1" / "db"
    assert seen["articles"] == ["CHAIR1"]
    assert (seen["price"], seen["max_configurations"]) == (False, None)      # complete, unpriced enumeration
    assert "priced" not in seen
    _price(widget, "GBP")
    assert seen["priced"] == (3, "GBP", "2026-02-03")                          # pricing gets the chosen currency/date
    dispose(widget)


def test_generation_reports_duplicates_and_unpriced_skus(gen_page):
    widget = gen_page
    _pick(widget, "side1")
    _generate(widget)
    assert _results(widget) == ["SIDE1 S", "SIDE1 L"]
    assert "2 duplicate SKU(s) removed" in widget._generation_status.text()
    _price(widget, "GBP")                                # SIDE1 has no GBP price
    assert "0 total priced and 2 unpriced" in widget._generation_status.text()
    assert set(_results(widget, 6)) == {
        "unpriced: no usable B price row for key (none) on %s in GBP: no row in GBP on %s; currencies valid then: EUR"
        % ((widget._price_date.date().toString("yyyyMMdd"),) * 2)}
    assert not widget._obx_actions_button.isEnabled()      # nothing priced, nothing to export


def test_price_diagnostics_explain_the_selected_row(gen_page):
    widget = gen_page
    assert not widget._diagnostics_button.isEnabled()      # nothing generated yet
    _pick(widget, "side1")
    _generate(widget)
    assert not widget._diagnostics_button.isEnabled()      # generated, but no SKU rows selected
    _price(widget, "GBP", rows=[1])                        # SIDE1 only has an EUR price
    page_module.QMessageBox.exec.assert_called()           # pricing shows the diagnostics for the selection
    widget._result_table.selectRow(1)                      # repricing resets the model, so select the row again
    assert widget._diagnostics_button.isEnabled()
    text = widget._price_diagnostics_text()
    assert "SIDE1 L" in text.splitlines()[0] and "demo" in text.splitlines()[0]
    assert "price key(s) derived for this SKU: ['SIZE=L']" in text
    assert "keys ['', 'SIZE=L']" in text
    assert "ocd_price.csv" in text and "currencies ['EUR']" in text
    assert "B:(none): 1 candidate(s) -> fixed 1 -> date 1 -> scale 1 -> currency 0" in text
    assert "result: unpriced - no usable B price row for key (none)" in text
    _price(widget, "EUR", rows=[1])
    widget._result_table.selectRow(1)
    assert "result: 50.00 EUR" in widget._price_diagnostics_text()
    assert _results(widget, 5)[0] == ""                    # the unselected row was not priced


def test_currency_must_be_chosen_when_the_repository_has_several(gen_page):
    widget = gen_page
    _pick(widget, "chair1")
    _generate(widget)
    widget._currency.setCurrentIndex(-1)
    widget._currency.setCurrentText("")
    widget._result_table.selectAll()
    widget._price_generated_skus()
    drain()
    assert "Choose a currency (EUR, GBP)" in widget._generation_status.text()
    page_module.QMessageBox.critical.assert_called_once()
    assert _results(widget, 5) == ["", "", ""]
    assert widget._diagnostics_button.isEnabled()      # can be retried


def test_malformed_article_data_is_reported_and_the_page_recovers(gen_page):
    widget = gen_page
    _pick(widget, "broken")
    _generate(widget)
    assert "Malformed OCD data for article BROKEN" in widget._generation_status.text()
    assert page_module.QMessageBox.critical.call_count == 1
    assert generation_available(widget) and not widget._obx_actions_button.isEnabled()


def test_missing_data_tables_are_reported(monkeypatch, ocd_root, no_plugin):
    """The plain ranges have articles but no property data: generation says so instead of guessing."""
    _boxes(monkeypatch)
    widget = PconArticleObxGeneratorPage(context=None, catalogue=OcdCatalogueService(ocd_root))
    _open_demo(widget)
    assert not widget._currency.count()
    _pick(widget, "chair1")
    _generate(widget)
    assert "ocd_property, ocd_propertyvalue" in widget._generation_status.text()
    dispose(widget)


def test_export_asks_before_overwriting_and_honours_the_answer(gen_page, tmp_path):
    widget = gen_page
    _pick(widget, "chair1")
    _generate_and_price(widget)
    target = tmp_path / "page.obx"
    target.write_text("old")
    page_module.QMessageBox.question.return_value = QMessageBox.StandardButton.No
    widget._export_obx()
    drain()
    assert target.read_text() == "old"
    page_module.QMessageBox.question.return_value = QMessageBox.StandardButton.Yes
    widget._export_obx()
    drain()
    assert "<cutBuffer>" in target.read_text(encoding="utf-8")


def test_export_without_a_path_uses_the_file_dialog_and_can_be_declined(gen_page, tmp_path, monkeypatch):
    widget = gen_page
    _pick(widget, "chair1")
    _generate_and_price(widget)
    chosen = tmp_path / "chosen" / "x.obx"
    dialog = _save_dialog_returns(monkeypatch, chosen)
    widget._export_obx()
    drain()
    dialog.assert_called_once()
    assert chosen.is_file()
    assert "Exported 3 SKU(s)" in widget._generation_status.text() and str(chosen) in widget._generation_status.text()
    monkeypatch.setattr(page_module.QFileDialog, "getSaveFileName", Mock(return_value=("", "")))
    before = widget._generation_status.text()
    widget._export_obx()
    drain()
    assert widget._generation_status.text() == before     # declined: nothing written, nothing reported


def test_export_failure_is_reported(gen_page, tmp_path, monkeypatch):
    widget = gen_page
    _pick(widget, "chair1")
    _generate_and_price(widget)
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, so nothing can be created below it")
    _save_dialog_returns(monkeypatch, blocker / "x.obx")
    widget._export_obx()
    drain()
    assert "Exporting OBX failed: Cannot write" in widget._generation_status.text()
    page_module.QMessageBox.critical.assert_called_once()


def test_export_requires_priced_skus(gen_page, tmp_path):
    widget = gen_page
    _pick(widget, "chair1")
    _generate(widget)                                    # generated but not priced
    widget._export_obx()
    drain()
    page_module.QMessageBox.information.assert_called_with(widget, "Export OBX", "Generate valid SKUs with a price first.")
    assert not (tmp_path / "page.obx").exists()


def test_only_priced_skus_are_exported(gen_page, tmp_path):
    widget = gen_page
    _pick(widget, "chair1")
    _generate(widget)
    _price(widget, "EUR", rows=[0, 2])                   # row 1 stays unpriced
    assert _results(widget, 5) == ["100.00 EUR", "", "100.00 EUR"]
    widget._export_obx()
    drain()
    assert "Exported 2 SKU(s)" in widget._generation_status.text()
    text = (tmp_path / "page.obx").read_text(encoding="utf-8")
    assert 'value="100.00"' in text and 'value="125.00"' not in text


def test_prepare_for_validator_requires_priced_skus_and_writes_a_temporary_obx(gen_page, tmp_path):
    widget = gen_page
    _pick(widget, "chair1")
    _generate(widget)
    widget._prepare_for_validator()
    page_module.QMessageBox.information.assert_called_with(
        widget, "Prepare for Validator", "Generate valid SKUs with a price first.")
    _price(widget, "EUR")
    widget._prepare_for_validator()
    drain()
    assert "Temporary OBX ready (3 article line(s))" in widget._generation_status.text()
    assert not (tmp_path / "page.obx").exists()          # the exported file is not touched


def test_generate_without_selection_shows_message(page):
    page._generate()
    page_module.QMessageBox.information.assert_called()


def test_export_without_generation_shows_message(page):
    page._export_obx()
    page_module.QMessageBox.information.assert_called()


# ---- Catalogue section: OCD repository -> manufacturer -> program -> series -> articles ----
def _loaded(page):
    widget = page
    widget._load_catalogue()
    drain()
    return widget


def _names(table, column=0):
    return [table.item(r, column).text() for r in range(table.rowCount())]


def test_controls_wait_for_their_prerequisites(page):
    widget = page
    for control in (widget._manufacturer, widget._program, widget._series, widget._article_filter,
                    widget._obx_actions_button, widget._diagnostics_button):
        assert not control.isEnabled()
    assert "automatically" in widget._catalogue_status.text().lower()
    _loaded(page)
    assert widget._manufacturer.isEnabled() and widget._program.isEnabled()
    assert not widget._article_filter.isEnabled()        # nothing to filter yet
    assert not generation_available(widget)       # nothing selected yet


def test_load_catalogue_populates_manufacturers_from_repository(page):
    widget = _loaded(page)
    manufacturers = [widget._manufacturer.itemData(i) for i in range(widget._manufacturer.count())]
    assert manufacturers == ["EG", "MK"]
    assert "Catalogue updated automatically: 3 program(s), 2 manufacturer(s)" in widget._catalogue_status.text()
    assert "1 folder(s) without OCD data skipped" in widget._catalogue_status.text()


def test_manufacturer_program_series_cascade_and_reset(page):
    widget = _loaded(page)
    _select(widget._manufacturer, "MK")
    assert sorted(widget._program.itemData(i).program for i in range(widget._program.count())) == ["demo", "found"]
    _program(widget, "demo")
    assert [widget._series.itemData(i) for i in range(widget._series.count())] == ["", "DM", "DX"]
    _select(widget._manufacturer, "EG")
    assert [widget._program.itemData(i).program for i in range(widget._program.count())] == ["office"]
    assert [widget._series.itemData(i) for i in range(widget._series.count())] == ["", "AX", "BX"]
    # A program without series offers only "(all series)"; choosing it loads its articles automatically.
    _select(widget._manufacturer, "MK")
    _program(widget, "found")
    drain()
    assert [widget._series.itemData(i) for i in range(widget._series.count())] == [""]
    assert not widget._series.isEnabled()
    assert _names(widget._article_table) == ["FOUND1"]


def test_changing_the_selection_clears_loaded_articles(page):
    widget = _loaded(page)
    _select(widget._manufacturer, "MK")
    _program(widget, "demo")
    drain()
    _select(widget._series, "DM")
    drain()
    widget._article_table.selectRow(0)
    assert generation_available(widget)
    page_module.QMessageBox.critical.assert_not_called()
    _select(widget._series, "DX")                     # the change reloads the list for the new selection
    assert widget._article_table.rowCount() == 0      # ...and drops the old one at once
    assert widget._article_count.text() == "0 of 0 articles"
    assert widget._catalogue_status.text().startswith("Loading articles of demo / DX")
    assert not generation_available(widget)
    drain()
    assert _names(widget._article_table) == ["TABLE1"]
    _program(widget, "found")
    drain()
    assert _names(widget._article_table) == ["FOUND1"]


def test_load_articles_for_a_series_fills_table_and_count(page):
    widget = _loaded(page)
    _select(widget._manufacturer, "MK")
    _program(widget, "demo")
    _select(widget._series, "DM")
    widget._load_articles()
    drain()
    # DUPE appears twice in the data; one row per article number, sorted.
    assert _names(widget._article_table) == ["BROKEN", "CHAIR1", "DUPE", "STOOL1"]
    row = [widget._article_table.item(1, c).text() for c in range(4)]
    assert row == ["CHAIR1", "—", "Demo Chair", "demo"]       # English label; OCD has no variant code
    assert widget._article_count.text() == "4 of 4 articles"
    assert "Loaded 4 article(s) of demo / DM" in widget._catalogue_status.text()
    assert widget._article_filter.isEnabled()
    _select(widget._series, "DX")
    widget._load_articles()
    drain()
    assert _names(widget._article_table) == ["TABLE1"]
    _select(widget._series, "")
    widget._load_articles()
    drain()
    assert widget._article_table.rowCount() == 5


def test_filter_matches_number_or_label_and_keeps_the_data(page):
    widget = _loaded(page)
    _select(widget._manufacturer, "MK")
    _program(widget, "demo")
    _select(widget._series, "")
    widget._load_articles()
    drain()
    assert widget._article_count.text() == "5 of 5 articles"
    widget._article_filter.setText("stool")                 # label, case-insensitive
    assert _names(widget._article_table) == ["STOOL1"]
    assert widget._article_count.text() == "1 of 5 articles"
    widget._article_filter.setText("table1")                # article number
    assert _names(widget._article_table) == ["TABLE1"]
    widget._article_filter.setText("zzz")
    assert widget._article_table.rowCount() == 0
    assert widget._article_count.text() == "0 of 5 articles"
    assert len(widget._articles) == 5                       # filtering never drops the data
    widget._article_filter.setText("")
    assert widget._article_table.rowCount() == 5


def test_empty_catalogue_is_reported_as_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(page_module.QMessageBox, "critical", Mock())
    root = tmp_path / "empty_hmx"
    (root / "nothing").mkdir(parents=True)
    widget = PconArticleObxGeneratorPage(context=None, catalogue=OcdCatalogueService(root))
    widget._load_catalogue()
    drain()
    assert widget._manufacturer.count() == 0 and widget._program.count() == 0
    assert "No OCD catalogue data found" in widget._catalogue_status.text()
    assert not widget._manufacturer.isEnabled()
    assert not widget._program.isEnabled()
    page_module.QMessageBox.critical.assert_not_called()      # empty is not a failure
    dispose(widget)


def test_missing_repository_is_reported_as_a_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(page_module.QMessageBox, "critical", Mock())
    missing = tmp_path / "does_not_exist"
    widget = PconArticleObxGeneratorPage(context=None, catalogue=OcdCatalogueService(missing))
    widget._load_catalogue()
    drain()
    text = widget._catalogue_status.text()
    assert "Loading catalogue failed" in text and str(missing) in text
    page_module.QMessageBox.critical.assert_called_once()
    dispose(widget)


def test_unconfigured_repository_is_reported_as_a_failure(monkeypatch):
    monkeypatch.setattr(page_module.QMessageBox, "critical", Mock())
    widget = PconArticleObxGeneratorPage(context=None)         # nothing configured
    widget._load_catalogue()
    drain()
    assert "No OCD repository folder is configured" in widget._catalogue_status.text()
    dispose(widget)


def test_failed_article_load_is_reported_and_keeps_the_catalogue(page, monkeypatch):
    widget = _loaded(page)
    _select(widget._manufacturer, "MK")

    def boom(self, program, series_id=""):
        raise CatalogueError("disk unplugged")

    monkeypatch.setattr(OcdCatalogueService, "list_articles", boom)
    _program(widget, "demo")
    widget._load_articles()                               # demo is already the first program, so load explicitly
    drain()
    assert "Loading articles failed: disk unplugged" in widget._catalogue_status.text()
    page_module.QMessageBox.critical.assert_called()
    assert widget._manufacturer.count() == 2 and widget._program.isEnabled()


def test_series_without_articles_is_reported_as_empty(page, monkeypatch):
    widget = _loaded(page)
    _select(widget._manufacturer, "MK")
    _program(widget, "demo")
    monkeypatch.setattr(OcdCatalogueService, "list_articles", lambda self, program, series_id="": [])
    widget._load_articles()
    drain()
    assert "No articles found for demo" in widget._catalogue_status.text()
    assert widget._article_table.rowCount() == 0
    page_module.QMessageBox.critical.assert_not_called()


def test_catalogue_uses_the_configured_repository_root(ocd_root):
    from core.config import AppConfig

    class Context:
        config = AppConfig(metatype_repository_root=str(ocd_root))

    widget = PconArticleObxGeneratorPage(context=Context())
    widget._load_catalogue()
    drain()
    assert widget._manufacturer.count() == 2
    dispose(widget)


def test_deleting_the_page_before_its_startup_callbacks_run_is_safe(ocd_root):
    """The startup catalogue check is queued with singleShot; it must not run against a deleted page."""
    from PySide6.QtCore import QEvent

    widget = PconArticleObxGeneratorPage(context=None, catalogue=OcdCatalogueService(ocd_root))
    widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)    # the page is gone, the timer is pending
    for _ in range(5):
        QCoreApplication.processEvents()                                    # raised "already deleted" before
    drain()
