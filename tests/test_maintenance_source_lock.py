"""Source-lock lifecycle on the Maintenance pages.

The MDB view locks the page's mutating widgets and restores them on the way
back to PDM. The lock table must only ever hold widgets that still belong to the
page: pages rebuild their views (and the combo editors inside them) on refresh,
and a destroyed widget left in the table crashed the PDM restore with
"Internal C++ object (QListView) already deleted".
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import re
import sys
from pathlib import Path

import pytest
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QPushButton,
    QTableWidget,
)

from core.application_context import ApplicationContext
from core.modules import WorkbenchModule
from models.article import Article
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from ui.pages.articles_page import ArticlesPage
from ui.pages.class_creation_page import ClassCreationPage
from ui.pages.pricing_page import PricingPage
from ui.pages.relation_page import RelationPage
from ui.pages.text_page import TextPage

NO_EDIT = QAbstractItemView.EditTrigger.NoEditTriggers


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def excepthook():
    """Collect exceptions raised inside Qt slots (they would otherwise only log)."""
    errors = []
    previous = sys.excepthook
    sys.excepthook = lambda kind, value, tb: errors.append(value)
    yield errors
    sys.excepthook = previous


def _snapshot(source):
    snap = Snapshot(id=source)
    snap.metadata.source = source
    snap.articles = [Article(id=f"{source}:{i}", code=f"{source}{i:03d}") for i in range(3)]
    snap.properties = [
        Property(
            id=f"{source}:P{p}",
            name=f"{source}Prop{p}",
            values=[
                PropertyValue(id=f"{source}:P{p}V{v}", property_id=f"{source}:P{p}",
                              value=f"V{v}", code=f"{v}")
                for v in range(3)
            ],
        )
        for p in range(3)
    ]
    return snap


def _context():
    ctx = ApplicationContext()
    for snap in (_snapshot("PDM"), _snapshot("MDB")):
        ctx.engineering_initialization_service.initialize(snap)
    ctx.register_pdm_snapshot(_snapshot_registered(ctx, "PDM"))
    ctx.register_mdb_import_snapshot(_snapshot_registered(ctx, "MDB"))
    ctx.activate_snapshot_source("pdm")
    return ctx


def _snapshot_registered(ctx, source):
    snap = _snapshot(source)
    ctx.engineering_initialization_service.initialize(snap)
    return snap


def _page(cls, ctx, module=WorkbenchModule.MAINTENANCE):
    page = cls(ctx)
    page._active_module = module
    page.refresh()
    return page


def _flush_deletes():
    """What the real event loop does after a rebuild: run pending deleteLater."""
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QCoreApplication.processEvents()


def _alive_tracked(page):
    return all(shiboken6.isValid(w) for w in page._locked_widgets)


def _page_view_triggers(page):
    return {v: v.editTriggers() for v in page._page_item_views()}


# -- which widgets are lockable -------------------------------------------------
def test_class_creation_never_registers_editor_internal_views():
    page = _page(ClassCreationPage, _context())
    combos = page.findChildren(QComboBox)
    assert combos, "fixture must build embedded combo editors"
    internal = [
        v for v in page.findChildren(QAbstractItemView)
        if any(v in c.findChildren(QAbstractItemView) for c in combos)
    ]
    assert internal, "combo popups own QListViews that findChildren returns"
    lockable = page._lockable_widgets()
    assert not [v for v in internal if v in lockable]
    assert all(v.window() is page.window() for v in page._page_item_views())


# -- the crash: rebuild while locked, then restore -----------------------------
def test_pdm_mdb_pdm_with_rebuild_and_deferred_delete_does_not_raise(excepthook):
    page = _page(ClassCreationPage, _context())
    pristine = _page_view_triggers(page)
    for _ in range(4):
        page._source_tabs.set_source("mdb")  # lock, then (re)build under the lock
        assert page._locked_widgets and _alive_tracked(page)
        page.refresh()
        _flush_deletes()  # cell editors of the rebuilt views are destroyed here
        assert _alive_tracked(page)
        page._source_tabs.set_source("pdm")  # restore must not touch dead widgets
        _flush_deletes()
        assert not page._locked_widgets
    assert excepthook == []
    # Every surviving page view is back to its pre-lock edit triggers.
    for view, triggers in _page_view_triggers(page).items():
        if view in pristine:
            assert triggers == pristine[view]
        assert triggers != NO_EDIT or view in pristine and pristine[view] == NO_EDIT


def test_lock_table_is_bounded_by_the_pages_own_widgets():
    page = _page(ClassCreationPage, _context())
    page._source_tabs.set_source("mdb")
    expected = len([w for w in page._lockable_widgets() if w is not None])
    for _ in range(5):
        page.refresh()
        _flush_deletes()
        assert len(page._locked_widgets) <= expected + 2  # no growth per refresh
    assert _alive_tracked(page)


# -- replacing / deleting a view while the source lock is active ------------------
def test_deleted_view_leaves_the_lock_table_immediately(excepthook):
    page = _page(ArticlesPage, _context())
    page._source_tabs.set_source("mdb")
    table = page._table
    assert table in page._locked_widgets and table.editTriggers() == NO_EDIT
    page._table = QTableWidget(0, 3, page)  # a rebuild replaces the page's view...
    table.setParent(None)
    table.deleteLater()  # ...and the old one is destroyed
    _flush_deletes()
    assert not shiboken6.isValid(table)
    assert all(shiboken6.isValid(w) for w in page._locked_widgets)
    assert table not in page._locked_widgets  # pruned on destruction, not kept
    page._source_tabs.set_source("pdm")  # must not raise
    assert excepthook == []


def test_replacement_view_is_registered_with_its_own_default_and_restored(excepthook):
    page = _page(ArticlesPage, _context())
    page._source_tabs.set_source("mdb")
    old = page._table
    replacement = QTableWidget(0, 3, page)
    replacement.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)  # its default
    page._table = replacement
    old.setParent(None)
    old.deleteLater()
    _flush_deletes()
    page._apply_lock_state()  # the page re-asserts the lock after a rebuild
    assert replacement in page._locked_widgets
    assert replacement.editTriggers() == NO_EDIT
    assert page._locked_widgets[replacement] == QAbstractItemView.EditTrigger.DoubleClicked
    page._source_tabs.set_source("pdm")
    assert replacement.editTriggers() == QAbstractItemView.EditTrigger.DoubleClicked
    assert not page._locked_widgets
    assert excepthook == []


def test_replaced_but_alive_view_gets_its_state_back_and_is_dropped():
    page = _page(ArticlesPage, _context())
    page._source_tabs.set_source("mdb")
    old = page._table
    original = page._locked_widgets[old]
    replacement = QTableWidget(0, 3, page)
    page._table = replacement  # old stays alive (still a child) but is no longer the page's
    page._apply_lock_state()
    assert old not in page._locked_widgets
    assert old.editTriggers() == original  # restored, not left permanently locked
    assert replacement in page._locked_widgets and replacement.editTriggers() == NO_EDIT


def test_replaced_button_is_not_left_disabled_or_filtered():
    page = _page(ArticlesPage, _context())
    page._source_tabs.set_source("mdb")
    old = page._apply_len_btn
    assert not old.isEnabled()
    page._apply_len_btn = QPushButton("Apply", page)
    page._apply_lock_state()
    assert old.isEnabled()  # given back
    assert not page._apply_len_btn.isEnabled()
    page._source_tabs.set_source("pdm")
    assert page._apply_len_btn.isEnabled()


# -- navigation and repeated switching -------------------------------------------
@pytest.mark.parametrize("cls", [ArticlesPage, ClassCreationPage, TextPage, RelationPage, PricingPage])
def test_repeated_switching_and_navigation_leaves_no_stuck_controls(cls, excepthook):
    ctx = _context()
    page = _page(cls, ctx)
    pdm_state = {
        w: (w.editTriggers() if isinstance(w, QAbstractItemView) else w.isEnabled())
        for w in page._lockable_widgets() if w is not None
    }
    for i in range(12):
        page._source_tabs.set_source("mdb" if i % 2 == 0 else "pdm")
        if i % 3 == 0:  # navigate away (Development) and back (Maintenance)
            page._active_module = WorkbenchModule.DEVELOPMENT
            page.refresh()
            assert not page._locked_widgets
            page._active_module = WorkbenchModule.MAINTENANCE
            page.refresh()
        _flush_deletes()
        assert _alive_tracked(page)
    page._source_tabs.set_source("pdm")
    _flush_deletes()
    assert not page._locked_widgets
    for widget, state in pdm_state.items():
        if shiboken6.isValid(widget):
            now = widget.editTriggers() if isinstance(widget, QAbstractItemView) else widget.isEnabled()
            assert now == state, widget
    assert excepthook == []


def test_mdb_view_is_still_read_only_after_the_lifecycle_churn():
    ctx = _context()
    page = _page(ClassCreationPage, ctx)
    for _ in range(3):
        page._source_tabs.set_source("mdb")
        page.refresh()
        _flush_deletes()
        page._source_tabs.set_source("pdm")
    page._source_tabs.set_source("mdb")
    assert page.is_mdb_view()
    for view in page._page_item_views():
        assert view.editTriggers() == NO_EDIT
    assert ctx.active_snapshot is ctx.pdm_snapshot and ctx.snapshot_source == "pdm"


# -- the Qt font warning: base stylesheet size must be a point size --------------
def test_stylesheet_base_font_size_is_not_pixel_based():
    """A pixel base size makes Qt log 'QFont::setPointSize: Point size <= 0 (-1)'
    when a QPushButton with a QMenu is polished (traced to this one rule)."""
    qss = (Path(__file__).resolve().parents[1] / "resources" / "styles.qss").read_text(encoding="utf-8")
    base = re.search(r"(?m)^QWidget\s*\{(.*?)\}", qss, re.S)
    assert base, "base QWidget rule missing"
    size = re.search(r"font-size:\s*([\d.]+)(px|pt)", base.group(1))
    assert size and size.group(2) == "pt"
