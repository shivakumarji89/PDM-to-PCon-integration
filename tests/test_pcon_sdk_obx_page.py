"""Workflow registration and page behaviour for QA → Article OBX Generator (standalone OCD Engine)."""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import Mock

import pytest
from PySide6.QtCore import QCoreApplication, QDate, QThreadPool
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
    widget.deleteLater()
    drain()


def test_step_is_registered_under_qa_and_in_workflow_items():
    steps = [item.step for item in WORKFLOW_ITEMS]
    assert WorkflowStep.PCON_ARTICLE_OBX_GENERATOR in steps
    item = next(i for i in WORKFLOW_ITEMS if i.step == WorkflowStep.PCON_ARTICLE_OBX_GENERATOR)
    assert item.title == "Article OBX Generator (OCD Engine)"
    qa = module_workflows(WorkbenchModule.QA_VALIDATION)
    assert qa.index(WorkflowStep.PCON_ARTICLE_OBX_GENERATOR) == qa.index(WorkflowStep.ARTICLE_OBX_GENERATOR) + 1
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


@pytest.fixture
def no_plugin(monkeypatch):
    """Any construction of the plugin bridge fails the test: the page must not need it."""
    import services.pcon_sdk_obx.bridge as bridge_module

    def forbidden(*_args, **_kwargs):
        raise AssertionError("PconPluginBridge must not be used by the standalone generator")

    monkeypatch.setattr(bridge_module.PconPluginBridge, "__init__", forbidden)


@pytest.fixture
def page(tmp_path, monkeypatch, ocd_root, no_plugin):
    _boxes(monkeypatch)
    widget = PconArticleObxGeneratorPage(context=None, catalogue=OcdCatalogueService(ocd_root))
    widget._output_path.setText(str(tmp_path / "page.obx"))
    yield widget
    dispose(widget)


def _open_demo(widget):
    widget._load_catalogue()
    drain()
    _select(widget._manufacturer, "MK")
    _program(widget, "demo")
    _select(widget._series, "DM")
    widget._load_articles()
    drain()


@pytest.fixture
def gen_page(tmp_path, monkeypatch, generation_root, no_plugin):
    _boxes(monkeypatch)
    widget = PconArticleObxGeneratorPage(context=None, catalogue=OcdCatalogueService(generation_root))
    widget._output_path.setText(str(tmp_path / "page.obx"))
    _open_demo(widget)
    yield widget
    dispose(widget)


def _pick(widget, article):
    widget._article_filter.setText(article)
    widget._article_table.selectRow(0)


def _results(widget, column=2):
    return [widget._result_table.item(r, column).text() for r in range(widget._result_table.rowCount())]


def _generate(widget, currency="EUR"):
    widget._currency.setCurrentText(currency)
    widget._generate()
    drain()


def test_page_has_no_plugin_connection_controls(no_plugin):
    widget = PconArticleObxGeneratorPage(context=None)
    assert widget.is_ready()
    assert widget._load_catalog_button.isEnabled()
    assert not widget._generate_button.isEnabled() and not widget._export_button.isEnabled()
    for removed in ("_connection_status", "_job_dir_label", "_check_button", "_install_button",
                    "_bridge", "_catalog", "_generation", "_discard_planning"):
        assert not hasattr(widget, removed)
    texts = {button.text() for button in widget.findChildren(page_module.QPushButton)}
    assert {"Launch pCon.planner", "Load Catalogue", "Load Articles", "Inspect Properties",
            "Generate Valid SKUs", "Export OBX"} <= texts
    assert not {"Check Connection", "Install Plugin"} & texts
    assert widget.header.title_label.text() == "Article OBX Generator (OCD Engine)"
    dispose(widget)


def test_page_module_reaches_the_plugin_package_only_to_launch_the_planner():
    source = open(page_module.__file__, encoding="utf-8").read()
    for name in ("PconCatalogService", "PconObxGenerationService", "PconConfigurationService",
                 "ReferenceObxComparer", "FakePconPlugin", "heartbeat", "job_dir", "send("):
        assert name not in source, name
    assert source.count("PconPluginBridge") == 2        # the lazy import and construction behind Launch
    assert source.count("from services.pcon_sdk_obx import") == 1


def test_launch_button_does_not_need_a_connection():
    launched = Mock()

    class Launcher:
        launch_planner = launched

    widget = PconArticleObxGeneratorPage(context=None, bridge=Launcher())
    widget._launch_button.click()
    launched.assert_called_once()
    dispose(widget)


def test_launch_failure_is_reported(monkeypatch):
    monkeypatch.setattr(page_module.QMessageBox, "warning", Mock())

    class Launcher:
        def launch_planner(self):
            raise RuntimeError("pCon.planner executable not found")

    widget = PconArticleObxGeneratorPage(context=None, bridge=Launcher())
    widget._launch_button.click()
    page_module.QMessageBox.warning.assert_called_once()
    dispose(widget)


# ---- the standalone workflow: catalogue -> articles -> properties -> SKUs -> OBX ----
def test_page_runs_the_complete_standalone_workflow(gen_page, tmp_path):
    widget = gen_page
    assert widget._article_table.rowCount() == 5
    assert [widget._currency.itemText(i) for i in range(widget._currency.count())] == ["EUR", "GBP"]
    _pick(widget, "chair1")
    assert widget._generate_button.isEnabled() and not widget._export_button.isEnabled()

    widget._price_date.setDate(QDate.fromString("2026-01-15", "yyyy-MM-dd"))
    _generate(widget)                        # automatic: no property inspection needed
    assert _results(widget) == CHAIR1_FINALS
    assert _results(widget, 5) == ["100.00 EUR", "125.00 EUR", "100.00 EUR"]
    assert _results(widget, 4)[1] == "Material=W; Size=L"
    assert "Generated 3 valid unique SKU(s)" in widget._generation_status.text()
    assert widget._export_button.isEnabled()
    assert not (tmp_path / "page.obx").exists()          # generating does not write; Export does

    widget._export_obx()
    drain()
    assert (tmp_path / "page.obx").is_file()
    assert "Exported 3 SKU(s)" in widget._generation_status.text()
    assert "3 article line(s) read back" in widget._generation_status.text()
    assert widget._validation_label.text() == ""
    assert widget._open_folder_button.isEnabled() and widget._compare_button.isEnabled()
    text = (tmp_path / "page.obx").read_text(encoding="utf-8")
    assert "DEMO_OPT.Material=W;DEMO_OPT.Size=L" in text and 'value="125.00"' in text


def test_selected_program_series_and_articles_reach_the_generator(tmp_path, monkeypatch, generation_root, no_plugin):
    _boxes(monkeypatch)
    seen = {}

    class Spy(OcdArticleGenerator):
        def generate(self, article_numbers, rules=(), **kwargs):
            seen.update(db_dir=self.db_dir, articles=list(article_numbers), **kwargs)
            return super().generate(article_numbers, rules, **kwargs)

    widget = PconArticleObxGeneratorPage(
        context=None, catalogue=OcdCatalogueService(generation_root), generator_factory=Spy)
    _open_demo(widget)
    _pick(widget, "chair1")
    widget._max_configurations.setValue(7)
    widget._price_date.setDate(QDate.fromString("2026-02-03", "yyyy-MM-dd"))
    _generate(widget, "GBP")
    assert seen["db_dir"] == generation_root / "demo" / "ANY" / "1" / "db"
    assert seen["articles"] == ["CHAIR1"]
    assert (seen["currency"], seen["price_date"], seen["max_configurations"]) == ("GBP", "2026-02-03", 7)
    dispose(widget)


def test_inspect_shows_properties_values_and_relations_and_pins_apply(gen_page):
    widget = gen_page
    _pick(widget, "chair1")
    widget._inspect_properties()
    drain()
    table = widget._property_table
    assert [table.item(r, 0).text() for r in range(table.rowCount())] == ["DEMO_OPT:Material", "DEMO_OPT:Size"]
    assert [table.item(r, 1).text() for r in range(table.rowCount())] == ["Material", "Size"]
    assert [table.item(r, 2).text() for r in range(table.rowCount())] == ["M", "S"]    # flagged defaults
    assert [table.item(r, 5).text() for r in range(table.rowCount())] == ["2", "2"]
    assert table.item(0, 6).text() == "" and table.item(1, 6).text() == "1"
    assert "precondition" in table.item(1, 6).toolTip() and "Material = 'W'" in table.item(1, 6).toolTip()
    assert "$VARCOND" in widget._inspected_label.toolTip()                             # article-level relation
    assert "Inspected CHAIR1: scheme U1, 2 properties, 2 with values" in widget._inspected_label.text()
    assert "2 varied properties; naive upper bound 4" in widget._estimate_label.text()
    assert table.cellWidget(0, 4).itemText(1) == "M — Metal"

    mode, value = table.cellWidget(0, 3), table.cellWidget(0, 4)
    mode.setCurrentIndex(mode.findData("fixed"))
    value.setCurrentIndex(value.findData("M"))
    assert "1 varied property" in widget._estimate_label.text()
    _generate(widget)
    assert _results(widget) == ["CHAIR1 M S"]            # the relation still removes Metal/Large

    mode.setCurrentIndex(mode.findData("default"))
    size_mode = table.cellWidget(1, 3)
    size_mode.setCurrentIndex(size_mode.findData("default"))
    _generate(widget)
    assert _results(widget) == ["CHAIR1 M S"]


def test_default_mode_is_disabled_for_a_property_without_a_default(gen_page):
    widget = gen_page
    _pick(widget, "side1")
    widget._inspect_properties()
    drain()
    colour = widget._property_table.cellWidget(1, 3)
    assert not colour.model().item(colour.findData("default")).isEnabled()
    assert widget._property_table.item(1, 2).text() == ""


def test_generation_reports_duplicates_and_unpriced_skus(gen_page):
    widget = gen_page
    _pick(widget, "side1")
    _generate(widget)
    assert _results(widget) == ["SIDE1 S", "SIDE1 L"]
    assert "2 duplicate SKU(s) removed" in widget._generation_status.text()
    _generate(widget, "GBP")                             # SIDE1 has no GBP price
    assert "2 without price" in widget._generation_status.text()
    assert set(_results(widget, 6)) == {
        "unpriced: no usable B price row for key (none) on %s in GBP: no row in GBP on %s; currencies valid then: EUR"
        % ((widget._price_date.date().toString("yyyyMMdd"),) * 2)}
    assert not widget._export_button.isEnabled()          # nothing priced, nothing to export


def test_price_diagnostics_explain_the_selected_row(gen_page):
    widget = gen_page
    assert not widget._diagnostics_button.isEnabled()      # nothing generated yet
    _pick(widget, "side1")
    _generate(widget, "GBP")                               # SIDE1 only has an EUR price
    assert widget._diagnostics_button.isEnabled()
    widget._result_table.selectRow(1)
    text = widget._price_diagnostics_text()
    assert "SIDE1 L" in text.splitlines()[0] and "demo" in text.splitlines()[0]
    assert "price key(s) derived for this SKU: ['SIZE=L']" in text
    assert "keys ['', 'SIZE=L']" in text
    assert "ocd_price.csv" in text and "currencies ['EUR']" in text
    assert "B:(none): 1 candidate(s) -> fixed 1 -> date 1 -> scale 1 -> currency 0" in text
    assert "result: unpriced - no usable B price row for key (none)" in text
    _generate(widget, "EUR")
    assert "result: 50.00 EUR" in widget._price_diagnostics_text()


def test_generation_limit_is_reported(gen_page):
    widget = gen_page
    _pick(widget, "chair1")
    widget._max_configurations.setValue(2)
    _generate(widget)
    assert _results(widget) == CHAIR1_FINALS[:2]
    assert "(limit reached)" in widget._generation_status.text()
    assert "Stopped at the limit of 2 SKU(s)." in widget._validation_label.text()


def test_currency_must_be_chosen_when_the_repository_has_several(gen_page):
    widget = gen_page
    _pick(widget, "chair1")
    widget._currency.setCurrentIndex(-1)
    widget._currency.setCurrentText("")
    widget._generate()
    drain()
    assert "Choose a currency (EUR, GBP)" in widget._generation_status.text()
    page_module.QMessageBox.critical.assert_called_once()
    assert widget._generate_button.isEnabled()             # can be retried


def test_malformed_article_data_is_reported_and_the_page_recovers(gen_page):
    widget = gen_page
    _pick(widget, "broken")
    _generate(widget)
    assert "Malformed OCD data for article BROKEN" in widget._generation_status.text()
    assert page_module.QMessageBox.critical.call_count == 1
    assert widget._generate_button.isEnabled() and not widget._export_button.isEnabled()
    widget._inspect_properties()
    drain()
    assert "Inspecting properties failed: Malformed OCD data for article BROKEN" in widget._generation_status.text()
    assert page_module.QMessageBox.critical.call_count == 2


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
    _generate(widget)
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
    _generate(widget)
    widget._output_path.setText("")
    chosen = tmp_path / "chosen" / "x.obx"
    dialog = Mock(return_value=(str(chosen), "OBX files (*.obx)"))
    monkeypatch.setattr(page_module.QFileDialog, "getSaveFileName", dialog)
    widget._export_obx()
    drain()
    dialog.assert_called_once()
    assert chosen.is_file() and widget._output_path.text() == str(chosen)
    widget._output_path.setText("")
    monkeypatch.setattr(page_module.QFileDialog, "getSaveFileName", Mock(return_value=("", "")))
    before = widget._generation_status.text()
    widget._export_obx()
    drain()
    assert widget._generation_status.text() == before     # declined: nothing written, nothing reported


def test_export_failure_is_reported(gen_page, tmp_path):
    widget = gen_page
    _pick(widget, "chair1")
    _generate(widget)
    widget._output_path.setText(str(tmp_path / "not_obx.txt"))
    widget._export_obx()
    drain()
    assert "Exporting OBX failed: The output file must use the .obx extension." in widget._generation_status.text()
    page_module.QMessageBox.critical.assert_called_once()


def test_compare_with_reference_obx(gen_page, tmp_path, monkeypatch):
    widget = gen_page
    _pick(widget, "chair1")
    _generate(widget)
    widget._export_obx()
    drain()
    reference = tmp_path / "reference.obx"
    reference.write_text((tmp_path / "page.obx").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(page_module.QFileDialog, "getOpenFileName", Mock(return_value=(str(reference), "")))
    widget._compare_reference()
    assert "3 matched, 0 only in reference, 0 only generated" in widget._validation_label.text()


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
    assert widget._load_catalog_button.isEnabled()
    for control in (widget._manufacturer, widget._program, widget._series, widget._load_articles_button,
                    widget._article_filter, widget._inspect_button, widget._generate_button):
        assert not control.isEnabled()
    assert "Load Catalogue" in widget._catalogue_status.text()
    _loaded(page)
    assert widget._manufacturer.isEnabled() and widget._program.isEnabled()
    assert widget._load_articles_button.isEnabled()
    assert not widget._article_filter.isEnabled()        # nothing to filter yet
    assert not widget._generate_button.isEnabled()       # nothing selected yet


def test_load_catalogue_populates_manufacturers_from_repository(page):
    widget = _loaded(page)
    manufacturers = [widget._manufacturer.itemData(i) for i in range(widget._manufacturer.count())]
    assert manufacturers == ["EG", "MK"]
    assert "Catalogue loaded: 3 program(s), 2 manufacturer(s)" in widget._catalogue_status.text()
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
    # A program without series offers only "(all series)" and Load Articles stays available.
    _select(widget._manufacturer, "MK")
    _program(widget, "found")
    assert [widget._series.itemData(i) for i in range(widget._series.count())] == [""]
    assert not widget._series.isEnabled()
    assert widget._load_articles_button.isEnabled()


def test_changing_the_selection_clears_loaded_articles(page):
    widget = _loaded(page)
    _select(widget._manufacturer, "MK")
    _program(widget, "demo")
    _select(widget._series, "DM")
    widget._load_articles()
    drain()
    widget._article_table.selectRow(0)
    assert widget._generate_button.isEnabled()
    _select(widget._series, "DX")
    assert widget._article_table.rowCount() == 0
    assert widget._article_count.text() == "0 of 0 articles"
    assert "load the articles again" in widget._catalogue_status.text()
    assert not widget._generate_button.isEnabled()
    _program(widget, "found")
    assert widget._article_table.rowCount() == 0


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
    assert not widget._load_articles_button.isEnabled()
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
    assert widget._load_catalog_button.isEnabled()            # can be retried
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
    _program(widget, "demo")
    _select(widget._series, "DM")

    def boom(self, program, series_id=""):
        raise CatalogueError("disk unplugged")

    monkeypatch.setattr(OcdCatalogueService, "list_articles", boom)
    widget._load_articles()
    drain()
    assert "Loading articles failed: disk unplugged" in widget._catalogue_status.text()
    page_module.QMessageBox.critical.assert_called()
    assert widget._manufacturer.count() == 2 and widget._load_articles_button.isEnabled()


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
