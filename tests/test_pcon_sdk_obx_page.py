"""Workflow registration and page behaviour for QA → Article OBX Generator (pCon SDK)."""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import Mock

import pytest
from PySide6.QtCore import QCoreApplication, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

from core.enums import WorkflowStep
from core.modules import WorkbenchModule, module_workflows
from core.workflow import WORKFLOW_ITEMS
from services.pcon_sdk_obx import BridgeSettings, PconPluginBridge
from tests.pcon_sdk_fake_plugin import FakePconPlugin
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


def test_step_is_registered_under_qa_and_in_workflow_items():
    steps = [item.step for item in WORKFLOW_ITEMS]
    assert WorkflowStep.PCON_ARTICLE_OBX_GENERATOR in steps
    item = next(i for i in WORKFLOW_ITEMS if i.step == WorkflowStep.PCON_ARTICLE_OBX_GENERATOR)
    assert item.title == "Article OBX Generator (pCon SDK)"
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


@pytest.fixture
def page(tmp_path, monkeypatch):
    settings = BridgeSettings(job_dir=tmp_path / "jobs", planner_exe="", plugin_install_dir=tmp_path / "plug",
                              request_timeout=10.0, generate_timeout=30.0, poll_interval=0.01)
    bridge = PconPluginBridge(settings)
    monkeypatch.setattr(page_module.QMessageBox, "information", Mock())
    monkeypatch.setattr(page_module.QMessageBox, "warning", Mock())
    monkeypatch.setattr(page_module.QMessageBox, "critical", Mock())
    monkeypatch.setattr(page_module.QMessageBox, "question", Mock(return_value=QMessageBox.StandardButton.Yes))
    with FakePconPlugin(bridge.ensure_job_dir()) as plugin:
        widget = PconArticleObxGeneratorPage(context=None, bridge=bridge)
        widget._output_path.setText(str(tmp_path / "page.obx"))
        yield widget, plugin, tmp_path
        widget.deleteLater()
        drain()


def test_page_disables_actions_without_plugin(tmp_path, monkeypatch):
    settings = BridgeSettings(job_dir=tmp_path / "nojobs", planner_exe="", plugin_install_dir=tmp_path / "plug",
                              poll_interval=0.01)
    widget = PconArticleObxGeneratorPage(context=None, bridge=PconPluginBridge(settings))
    assert widget.is_ready()
    assert not widget._generate_button.isEnabled()
    assert "not detected" in widget._connection_status.text()
    widget.deleteLater()


def test_page_runs_the_complete_workflow(page):
    widget, plugin, tmp_path = page
    widget.refresh()
    assert widget._generate_button.isEnabled()

    widget._load_catalogue()
    drain()
    assert widget._manufacturer.count() == 2
    widget._manufacturer.setCurrentIndex(widget._manufacturer.findData("MK"))
    assert widget._program.currentData().package_name == "::mk::demo::1"
    assert widget._series.currentData() == "DM"

    widget._load_articles()
    drain()
    assert widget._article_table.rowCount() == 4
    widget._article_filter.setText("chair")
    assert widget._article_table.rowCount() == 1
    widget._article_table.selectRow(0)

    # Automatic generation straight away: no property inspection needed.
    widget._generate()
    drain()
    assert widget._result_table.rowCount() == 8
    finals = [widget._result_table.item(r, 2).text() for r in range(8)]
    assert finals == ["CHAIR1 WOS", "CHAIR1 WOL", "CHAIR1 WWS", "CHAIR1 WWL",
                      "CHAIR1 MSSF", "CHAIR1 MSSA", "CHAIR1 MSLF", "CHAIR1 MSLA"]
    assert "Generated 8 valid unique SKU(s)" in widget._generation_status.text()
    assert "8 article line(s) parsed, 8 expected" in widget._validation_label.text()
    assert widget._open_folder_button.isEnabled() and widget._compare_button.isEnabled()
    assert (tmp_path / "page.obx").is_file()
    assert plugin.requests[-1]["kind"] == "generate"
    assert plugin.requests[-1]["varyAll"] is True and plugin.requests[-1]["properties"] == []

    # Optional scope: inspect, pin Material=Metal and keep Size at its default.
    widget._inspect_properties()
    drain()
    assert widget._property_table.rowCount() == 4
    assert "CHAIR1 WOS" in widget._inspected_label.text()
    for row in range(widget._property_table.rowCount()):
        key = widget._property_table.item(row, 0).text()
        mode = widget._property_table.cellWidget(row, 3)
        value = widget._property_table.cellWidget(row, 4)
        if key == "Material":
            mode.setCurrentIndex(mode.findData("fixed"))
            value.setCurrentIndex(value.findData("Metal"))
        if key == "Size":
            mode.setCurrentIndex(mode.findData("default"))
        if key == "Height":
            assert not mode.isEnabled()
    assert "1 varied property" in widget._estimate_label.text()
    widget._generate()
    drain()
    finals = [widget._result_table.item(r, 2).text() for r in range(widget._result_table.rowCount())]
    assert finals == ["CHAIR1 MSSF", "CHAIR1 MSSA"]
    assert plugin.requests[-1]["properties"] == [
        {"key": "Material", "mode": "fixed", "valueKey": "Metal"},
        {"key": "Size", "mode": "default", "valueKey": ""},
    ]


def test_page_reports_plugin_failure(page):
    widget, plugin, tmp_path = page
    widget._load_catalogue()
    drain()
    widget._manufacturer.setCurrentIndex(widget._manufacturer.findData("MK"))
    widget._load_articles()
    drain()
    widget._article_filter.setText("BROKEN")
    widget._article_table.selectRow(0)
    widget._generate()
    drain()
    assert "did not succeed" in widget._validation_label.text() or "could not insert" in widget._validation_label.text()
    assert "Generated 0 valid" in widget._generation_status.text()
    assert widget._generate_button.isEnabled()


def test_generate_without_selection_shows_message(page):
    widget, _, _ = page
    widget._generate()
    page_module.QMessageBox.information.assert_called()
