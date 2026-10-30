"""Workflow shell: header, sidebar, flow toolbar and the Maintenance Articles pilot."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFormLayout, QPushButton

from core.application_context import ApplicationContext
from core.enums import WorkflowStep
from core.modules import WorkbenchModule
from core.workflow import WORKFLOW_ITEMS
from models.article import Article
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.product import Product
from models.snapshot import Snapshot
from ui.components import AppHeaderBar, DetailTabs, WorkflowSidebar
from ui.components.flow_layout import FlowFrame
from ui.pages.articles_page import ArticlesPage
from workflow.state import WorkflowState


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    previous = QSettings.defaultFormat()
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    yield
    QSettings.setDefaultFormat(previous)


class _FakeManager(QObject):
    state_changed = Signal()
    step_changed = Signal(object)

    def __init__(self, states, current):
        super().__init__()
        self.states, self.current, self.jumps = states, current, []

    def current_step(self):
        return self.current

    def step_state(self, step):
        return self.states[step]

    def jump_to(self, step):
        self.jumps.append(step)
        return True


STEPS = (WorkflowStep.PRODUCT, WorkflowStep.ARTICLES, WorkflowStep.TEXT)


def _items():
    by = {i.step: i for i in WORKFLOW_ITEMS}
    return [by[s] for s in STEPS]


def _sidebar(states, current):
    manager = _FakeManager(dict(zip(STEPS, states)), current)
    bar = WorkflowSidebar()
    bar.bind_manager(manager)
    bar.set_module("Maintenance", "desc", _items())
    return bar, manager


# ---- sidebar -----------------------------------------------------------------
def test_sidebar_states_and_current_highlight(app):
    bar, _ = _sidebar(
        [WorkflowState.COMPLETED, WorkflowState.COMPLETED, WorkflowState.BLOCKED], WorkflowStep.ARTICLES
    )
    rows = bar.nav.rows()
    assert rows[WorkflowStep.PRODUCT].state == "completed"
    assert rows[WorkflowStep.ARTICLES].state == "current"  # open step always highlighted
    assert rows[WorkflowStep.TEXT].state == "blocked"


def test_sidebar_click_goes_through_manager_and_respects_lock(app):
    bar, manager = _sidebar(
        [WorkflowState.COMPLETED, WorkflowState.READY, WorkflowState.BLOCKED], WorkflowStep.PRODUCT
    )
    bar.resize(260, 400)
    bar.show()
    rows = bar.nav.rows()
    QTest.mouseClick(rows[WorkflowStep.ARTICLES], Qt.MouseButton.LeftButton)
    QTest.mouseClick(rows[WorkflowStep.TEXT], Qt.MouseButton.LeftButton)  # locked: ignored
    assert manager.jumps == [WorkflowStep.ARTICLES]


def test_sidebar_steps_follow_declared_order_without_inventing(app):
    bar, _ = _sidebar([WorkflowState.READY] * 3, WorkflowStep.PRODUCT)
    assert list(bar.nav.rows()) == list(STEPS)
    assert bar.tips.text_label.text() == _items()[0].description


def test_sidebar_rerenders_on_manager_state(app):
    bar, manager = _sidebar([WorkflowState.READY] * 3, WorkflowStep.PRODUCT)
    manager.states[WorkflowStep.TEXT] = WorkflowState.COMPLETED
    manager.state_changed.emit()
    assert bar.nav.rows()[WorkflowStep.TEXT].state == "completed"


# ---- header ------------------------------------------------------------------
def test_header_indicators_and_settings_signal(app):
    header = AppHeaderBar()
    hits = []
    header.settings_clicked.connect(lambda: hits.append(1))
    header.set_indicator("pdm", "Loaded", "success")
    header.set_indicator("mdb", "Not loaded", "neutral")
    header.settings_button.click()
    assert header.indicator("pdm").state_label.text() == "Loaded"
    assert header.indicator("mdb").state_label.text() == "Not loaded"
    assert hits == [1]


# ---- flow toolbar ------------------------------------------------------------
def test_flow_frame_wraps_without_clipping(app):
    frame = FlowFrame()
    buttons = [QPushButton(f"Action number {i}") for i in range(8)]
    for b in buttons:
        frame.flow.addWidget(b)
    frame.resize(1200, 40)
    frame.show()
    app.processEvents()
    wide_h = frame.height()
    frame.resize(300, 40)
    app.processEvents()
    assert frame.height() > wide_h
    for b in buttons:  # every control inside the frame
        assert frame.rect().contains(b.geometry())


# ---- Maintenance Articles pilot ----------------------------------------------
def _snapshot(n=6):
    s = Snapshot()
    s.metadata.source = "PDM"
    s.product = Product(id="1", code="HM", name="Series")
    s.articles = [Article(id=f"a{i}", code=f"HM.{1000 + i}", description=f"Art {i}") for i in range(n)]
    s.engineering.families = [EngineeringFamily(id="f", name="Fam", members=[
        MemberArticle(id=f"m{i}", article_id=a.id, family_id="f", reduced_article=a.code[:6])
        for i, a in enumerate(s.articles)])]
    return s


_PAGES = []


@pytest.fixture(autouse=True)
def _dispose_pages(app):
    """Stop debounce timers and delete pages deterministically after each test."""
    yield
    while _PAGES:
        page = _PAGES.pop()
        page._filter_timer.stop()
        page.close()
        page.deleteLater()
    app.processEvents()


def _articles(module):
    ctx = ApplicationContext()
    ctx.register_pdm_snapshot(_snapshot())
    ctx.activate_snapshot_source("pdm")
    page = ArticlesPage(ctx)
    page._active_module = module
    _PAGES.append(page)
    page.resize(1100, 700)
    page.show()
    page.refresh()
    return page


def test_articles_shell_is_maintenance_only(app):
    dev = _articles(WorkbenchModule.DEVELOPMENT)
    assert dev._shell_on is False
    assert dev._toolbar_box.isVisibleTo(dev)
    mnt = _articles(WorkbenchModule.MAINTENANCE)
    assert mnt._shell_on is True
    assert not mnt._toolbar_box.isVisibleTo(mnt)
    assert mnt._shell_toolbar.isVisibleTo(mnt)


def test_articles_shell_reverts_for_development(app):
    page = _articles(WorkbenchModule.MAINTENANCE)
    assert page._shell_on
    page._active_module = WorkbenchModule.DEVELOPMENT
    page.refresh()
    assert not page._shell_on
    assert page._toolbar_box.isVisibleTo(page)
    assert not page._shell_toolbar.isVisibleTo(page)
    assert page._table.parent() is not page._shell_hsplit
    assert page._table.minimumHeight() == 280
    # every toolbar control is back in the original layout, same order
    layout = page._toolbar_box.layout()
    assert [layout.itemAt(i).widget() for i in range(layout.count())] == [w for w, _ in page._toolbar_widgets]


def test_articles_shell_kpis_use_real_counts(app):
    page = _articles(WorkbenchModule.MAINTENANCE)
    assert page._kpi_loaded.value_label.text() == "6"
    assert page._kpi_shown.value_label.text() == "6"
    page._search.setText("HM.1002")
    page._apply_filter()
    assert page._kpi_shown.value_label.text() == "1"
    assert page._kpi_loaded.value_label.text() == "6"


def test_articles_shell_keeps_existing_controls_and_signals(app):
    page = _articles(WorkbenchModule.MAINTENANCE)
    for name in ("_search", "_base_len_spin", "_apply_len_btn", "_dot_base_btn", "_copy_long_btn",
                 "_components_btn", "_clear_btn", "_group_check", "_export_mdb_btn"):
        assert page._shell_toolbar.isAncestorOf(getattr(page, name))
    assert page._table.isSortingEnabled()
    # the original click handlers are still connected (signal receivers unchanged)
    assert page._copy_long_btn.receivers("2clicked(bool)") > 0
    assert page._apply_len_btn.receivers("2clicked(bool)") > 0


def test_articles_selection_shows_detail_tab(app):
    page = _articles(WorkbenchModule.MAINTENANCE)
    assert not page._details_box.isVisibleTo(page._detail_tabs)
    assert page._detail_placeholder.isVisibleTo(page._detail_tabs)
    page._table.selectRow(0)
    app.processEvents()
    assert page._details_box.isVisibleTo(page._detail_tabs)
    assert not page._detail_placeholder.isVisibleTo(page._detail_tabs)
    assert isinstance(page._detail_tabs, DetailTabs)


@pytest.mark.parametrize("size", [(1500, 900), (1000, 640), (760, 560)])
def test_articles_shell_resizes(app, size):
    page = _articles(WorkbenchModule.MAINTENANCE)
    page.resize(*size)
    app.processEvents()
    assert page._shell_card.isVisible()
    assert page._shell_toolbar.height() >= 30


def test_articles_shell_roundtrip_restores_legacy_details_and_toolbar(app):
    page = _articles(WorkbenchModule.MAINTENANCE)
    page._table.selectRow(0)
    app.processEvents()
    assert page._details_host.isVisibleTo(page) or not page._details_host.isHidden()
    page._active_module = WorkbenchModule.DEVELOPMENT
    page._apply_shell(False)
    # every detail label is back in the original form, the toolbar in its box
    for row, attr in enumerate(page._DETAIL_FIELDS):
        assert page._details_form.itemAt(row, QFormLayout.ItemRole.FieldRole).widget() is getattr(page, attr)
        assert page._details_form.itemAt(row, QFormLayout.ItemRole.LabelRole).widget() is not None
    assert page._details_host.isHidden()
    assert page._search.parent() is page._toolbar_box
    assert page._export_mdb_btn.parent() is page._toolbar_box
    # and the shell can be re-entered
    page._apply_shell(True)
    assert page._shell_toolbar.isAncestorOf(page._search)


def test_sidebar_step_text_wraps_instead_of_clipping(app):
    bar, _ = _sidebar(
        [WorkflowState.COMPLETED, WorkflowState.READY, WorkflowState.BLOCKED], WorkflowStep.ARTICLES
    )
    bar.resize(260, 600)
    bar.show()
    app.processEvents()
    row = bar.nav.rows()[WorkflowStep.ARTICLES]
    narrow = row._height_for(150)
    wide = row._height_for(400)
    assert narrow >= wide
    assert all(line for line in row._desc_lines(150))
