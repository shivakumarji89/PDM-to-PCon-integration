import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core.modules import WorkbenchModule
from ui.pages.module_home_page import ModuleHomePage

PRIMARY = (
    WorkbenchModule.DEVELOPMENT,
    WorkbenchModule.MAINTENANCE,
    WorkbenchModule.METATYPE,
    WorkbenchModule.OAP,
    WorkbenchModule.QA_VALIDATION,
    WorkbenchModule.BULK_UPDATE,
)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


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
        tile = {t.module: t for t in window._module_home._module_buttons}[WorkbenchModule.METATYPE]
        tile.click()
        assert window._active_module == WorkbenchModule.METATYPE
        window._show_module_home()
        assert window._active_module is None
    finally:
        window.close()


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
        window.close()


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
        window.close()
