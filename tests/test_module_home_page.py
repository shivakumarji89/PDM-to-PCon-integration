import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QPoint, QSettings, QThreadPool, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core.modules import WorkbenchModule
from ui.pages.module_home_page import ModuleHomePage

PRIMARY = (
    WorkbenchModule.PRODUCT_DATA_WORKSPACE,
    WorkbenchModule.METATYPE,
    WorkbenchModule.OAP,
    WorkbenchModule.QA_VALIDATION,
    WorkbenchModule.BULK_UPDATE,
)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _dispose_window(window) -> None:
    """Close a MainWindow and let its pages' background work (e.g. the catalogue check) finish before the next test.

    Closing alone leaves those worker threads running into later tests, which then crash inside Qt.
    """
    window.close()
    assert QThreadPool.globalInstance().waitForDone(10000)
    QCoreApplication.processEvents()


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    """MainWindow saves its layout on close; keep that out of the user's registry."""
    previous = QSettings.defaultFormat()
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    yield
    QSettings.setDefaultFormat(previous)


@pytest.fixture
def page(app):
    page = ModuleHomePage()
    page.resize(1360, 760)
    page.show()
    app.processEvents()
    yield page
    page.close()


def test_every_primary_module_tile_emits_its_module(page):
    received = []
    page.module_selected.connect(received.append)
    tiles = {tile.module: tile for tile in page._module_buttons}
    assert set(tiles) == set(PRIMARY)
    for module in PRIMARY:
        tile = tiles[module]
        QTest.mouseClick(tile, Qt.MouseButton.LeftButton, pos=tile.rect().center())
    assert received == list(PRIMARY)


def test_click_in_shadow_margin_does_not_select(page):
    received = []
    page.module_selected.connect(received.append)
    tile = page._module_buttons[0]
    QTest.mouseClick(tile, Qt.MouseButton.LeftButton, pos=QPoint(1, 1))
    assert received == []


def test_syteline_export_stays_in_additional_tools(page):
    received = []
    page.module_selected.connect(received.append)
    page._syteline_button.click()
    assert received == [WorkbenchModule.SYTELINE_EXPORT]


@pytest.mark.parametrize("size", [(800, 420), (1000, 640), (1360, 760), (1900, 1000)])
def test_tiles_keep_inside_stage_and_do_not_overlap(app, page, size):
    page.resize(*size)
    app.processEvents()
    stage = page._stage
    cards = []
    for tile in page._module_buttons:
        assert stage.rect().contains(tile.geometry())
        cards.append(tile.geometry().adjusted(*(int(tile._MARGIN * tile._scale),) * 2,
                                              *(-int(tile._MARGIN * tile._scale),) * 2))
    for i, a in enumerate(cards):
        for b in cards[i + 1:]:
            assert not a.intersects(b)


def test_main_window_still_routes_module_selection(app):
    from ui.main_window import MainWindow

    window = MainWindow()
    try:
        tile = {t.module: t for t in window._module_home._module_buttons}[WorkbenchModule.PRODUCT_DATA_WORKSPACE]
        tile.click()
        assert window._active_module == WorkbenchModule.DEVELOPMENT
        assert not hasattr(window, "_product_data_context_selector")

        # The workspace changes mode only when both source snapshots are loaded.
        from models.snapshot import Snapshot
        window._context.register_pdm_snapshot(Snapshot())
        window._sync_product_data_mode()
        assert window._active_module == WorkbenchModule.DEVELOPMENT
        window._context.register_mdb_import_snapshot(Snapshot())
        window._sync_product_data_mode()
        assert window._active_module == WorkbenchModule.MAINTENANCE
        window._context.register_mdb_import_snapshot(None)
        window._sync_product_data_mode()
        assert window._active_module == WorkbenchModule.DEVELOPMENT
        window._show_module_home()
        tile = {t.module: t for t in window._module_home._module_buttons}[WorkbenchModule.METATYPE]
        tile.click()
        assert window._active_module == WorkbenchModule.METATYPE
        window._show_module_home()
        assert window._active_module is None
    finally:
        _dispose_window(window)


@pytest.mark.parametrize("size", [(760, 400), (1000, 560), (1360, 760), (1900, 1000)])
def test_illustration_ring_stays_inside_stage_and_keeps_aspect(app, page, size):
    from ui.pages.module_home_page import _RING_CENTER, _RING_RADIUS

    page.resize(*size)
    app.processEvents()
    stage = page._stage
    s, ox, oy = stage._scale()
    cx, cy = _RING_CENTER
    left, right = ox + (cx - _RING_RADIUS) * s, ox + (cx + _RING_RADIUS) * s
    top, bottom = oy + (cy - _RING_RADIUS) * s, oy + (cy + _RING_RADIUS) * s
    assert left >= 0 and top >= 0
    assert right <= stage.width() and bottom <= stage.height()
    # one uniform scale factor: the ring stays a circle
    assert abs((right - left) - (bottom - top)) < 1e-6


def test_small_page_scrolls_instead_of_clipping(app):
    from ui.widgets.page_viewport import scrollable

    page = ModuleHomePage()
    area = scrollable(page)
    area.resize(900, 300)
    area.show()
    app.processEvents()
    try:
        assert page.height() >= page.minimumSizeHint().height()
        assert area.verticalScrollBar().maximum() > 0
    finally:
        area.close()


def test_hidden_workflow_pages_do_not_set_window_minimum_size(app):
    from ui.main_window import MainWindow

    window = MainWindow()
    try:
        tallest_page = max(
            window._stack.widget(i).minimumSizeHint().height()
            for i in range(window._stack.count())
        )
        assert tallest_page > 900  # the regression: a hidden page this tall
        assert window.minimumSizeHint().height() < 400
        assert window._stack.minimumSizeHint() == window._module_home.minimumSizeHint()
    finally:
        _dispose_window(window)


def test_oversized_window_is_fitted_to_the_screen(app):
    from ui.main_window import MainWindow

    window = MainWindow()
    try:
        window.resize(5000, 4000)
        window.show()
        window._geometry_fitted = False
        window._fit_window_to_screen()
        avail = window.screen().availableGeometry()
        frame = window.frameGeometry()
        assert frame.width() <= avail.width() and frame.height() <= avail.height()
        assert avail.contains(frame.topLeft())
    finally:
        _dispose_window(window)


def test_database_selector_lives_on_home_page_and_header_drops_pdm_status(app):
    from core.modules import module_workflows
    from ui.main_window import MainWindow

    window = MainWindow()
    try:
        selector = window._database_selector
        home = window._module_home
        assert selector.parent() is home
        layout = home._header_layout
        assert layout.indexOf(selector) == layout.indexOf(home._pdm_changes_button) - 1
        assert layout.contentsMargins().right() == 34  # aligns with the footer status strip inset

        with pytest.raises(KeyError):
            window._app_header.indicator("pdm")
        assert {"repository", "mdb"} <= set(window._app_header._indicators)

        maintenance_pages = [window._pages[s] for s in module_workflows(WorkbenchModule.MAINTENANCE)]
        window._product_data_context_active = True
        window._on_module_selected(WorkbenchModule.MAINTENANCE)
        for page in maintenance_pages:
            if getattr(page, "header", None) is None or not hasattr(page.header, "add_action"):
                continue
            assert not page._maintenance_reload_button.isHidden()
            assert not page._maintenance_export_mdb_button.isHidden()

        window._show_module_home()
        window._on_module_selected(WorkbenchModule.DEVELOPMENT)
        for page in maintenance_pages:
            if hasattr(page, "_maintenance_reload_button"):
                assert page._maintenance_reload_button.isHidden()
                assert page._maintenance_export_mdb_button.isHidden()
    finally:
        _dispose_window(window)


def test_product_data_workspace_uses_one_persistent_source_selector(app):
    from ui.main_window import MainWindow
    from core.workflow import WorkflowStep

    window = MainWindow()
    try:
        tile = {
            t.module: t for t in window._module_home._module_buttons
        }[WorkbenchModule.PRODUCT_DATA_WORKSPACE]
        tile.click()

        shared = window._workspace_source_tabs
        assert not shared.isHidden()
        assert shared.source == "pdm"

        steps = (
            WorkflowStep.ARTICLES,
            WorkflowStep.CLASS_CREATION,
            WorkflowStep.TEXT,
            WorkflowStep.RELATION,
            WorkflowStep.PRICING,
            WorkflowStep.PRICING_RELATION,
        )
        for step in steps:
            page = window._pages[step]
            page._sync_source()
            assert page._source_tabs is shared
            assert page.current_source() == "pdm"

        shared.set_source("mdb")
        for step in steps:
            page = window._pages[step]
            page._sync_source()
            assert page._source_tabs is shared
            assert page.current_source() == "mdb"

        # Returning to Product must not reset the selected source.
        window._manager.jump_to(WorkflowStep.PRODUCT)
        assert window._workspace_source_tabs.source == "mdb"
        window._show_module_home()
        assert shared.isHidden()
    finally:
        _dispose_window(window)



def test_unified_workspace_preserves_full_maintenance_workflow_and_switches_automatically(app):
    from core.workflow import WorkflowStep
    from core.modules import module_workflows
    from models.snapshot import Snapshot
    from ui.main_window import MainWindow

    window = MainWindow()
    try:
        tile = {
            item.module: item for item in window._module_home._module_buttons
        }[WorkbenchModule.PRODUCT_DATA_WORKSPACE]
        assert "Development + Maintenance" in tile._description
        assert "automatically" in tile._description.lower()

        tile.click()
        assert window._product_data_context_active
        assert window._active_module == WorkbenchModule.DEVELOPMENT
        assert window._manager.steps() == list(module_workflows(WorkbenchModule.DEVELOPMENT))

        pdm = Snapshot()
        window._context.register_pdm_snapshot(pdm)
        window._sync_product_data_mode()
        assert window._active_module == WorkbenchModule.DEVELOPMENT

        # An imported but empty MDB is not a maintenance baseline.
        mdb = Snapshot()
        window._context.register_mdb_import_snapshot(mdb)
        window._sync_product_data_mode()
        assert window._active_module == WorkbenchModule.DEVELOPMENT

        from models.article import Article
        mdb.articles.append(Article(id="mdb-article-1", code="SERIES.001"))
        window._sync_product_data_mode()

        expected_maintenance = list(module_workflows(WorkbenchModule.MAINTENANCE))
        assert window._active_module == WorkbenchModule.MAINTENANCE
        assert window._product_data_context_active
        assert window._manager.steps() == expected_maintenance
        assert WorkflowStep.MAINTENANCE_COMPARISON in expected_maintenance
        assert WorkflowStep.REVIEW in expected_maintenance
        assert expected_maintenance.index(WorkflowStep.REVIEW) < expected_maintenance.index(
            WorkflowStep.MAINTENANCE_COMPARISON
        )
        assert set(module_workflows(WorkbenchModule.DEVELOPMENT)).issubset(
            set(expected_maintenance)
        )
        assert not window._workspace_source_tabs.isHidden()

        # Review is brought over from Development as a workflow stage, but
        # must not receive generic Maintenance reload/export actions.
        review_page = window._pages[WorkflowStep.REVIEW]
        assert not hasattr(review_page, "_maintenance_reload_button")
        assert not hasattr(review_page, "_maintenance_export_mdb_button")

        # Existing Maintenance actions remain attached to their original pages.
        for step in expected_maintenance:
            page = window._pages[step]
            reload_button = getattr(page, "_maintenance_reload_button", None)
            export_button = getattr(page, "_maintenance_export_mdb_button", None)
            if reload_button is not None:
                assert not reload_button.isHidden()
            if export_button is not None:
                assert not export_button.isHidden()

        # Clearing the imported MDB returns to Development without deleting
        # any Maintenance workflow registrations or page implementations.
        window._context.register_mdb_import_snapshot(None)
        window._sync_product_data_mode()
        assert window._active_module == WorkbenchModule.DEVELOPMENT
        assert window._manager.steps() == list(module_workflows(WorkbenchModule.DEVELOPMENT))
        assert module_workflows(WorkbenchModule.MAINTENANCE) == tuple(expected_maintenance)
        assert all(step in window._pages for step in expected_maintenance)
        for step in expected_maintenance:
            page = window._pages[step]
            for name in (
                "_maintenance_reload_button",
                "_maintenance_refresh_pdm_button",
                "_maintenance_export_mdb_button",
            ):
                button = getattr(page, name, None)
                if button is not None:
                    assert button.isHidden()
    finally:
        _dispose_window(window)
