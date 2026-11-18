"""Phase 2 / area 1: one controlled refresh per navigation.

``WorkspaceHost.activate`` used to refresh a page up to three times (the ``showEvent``
refresh, the host's own ``refresh()``, then ``on_enter()``, which is ``refresh()`` again for most
pages). These tests keep the previous sequence as an oracle (``_legacy_activate``), run it and the
new host on identical, independent contexts, and compare every widget and the whole snapshot
afterwards. They also pin the refresh counts and prove that the load-time refresh of hidden pages
must stay (it materialises snapshot data, not just widgets).
"""
from __future__ import annotations

import json
import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import (
    QApplication, QComboBox, QLabel, QLineEdit, QListWidget, QPlainTextEdit, QPushButton,
    QStackedWidget, QTableWidget, QTextEdit, QTreeWidget,
)

from core.application_context import ApplicationContext
from core.enums import WorkflowStep
from core.modules import WorkbenchModule
from models.product import Product
from services.snapshot_serialization import snapshot_to_dict
from tests.perf_synthetic import build_class_creation_snapshot
from ui.pages.articles_page import ArticlesPage
from ui.pages.class_creation_page import ClassCreationPage
from ui.pages.engineering_page import EngineeringPage
from ui.pages.pricing_page import PricingPage
from ui.pages.pricing_relation_page import PricingRelationPage
from ui.pages.relation_page import RelationPage
from ui.pages.review_page import ReviewPage
from ui.pages.text_page import TextPage
from workflow.host import WorkspaceHost

PAGES = {
    WorkflowStep.CLASS_CREATION: ClassCreationPage,
    WorkflowStep.ARTICLES: ArticlesPage,
    WorkflowStep.TEXT: TextPage,
    WorkflowStep.RELATION: RelationPage,
    WorkflowStep.PRICING: PricingPage,
    WorkflowStep.PRICING_RELATION: PricingRelationPage,
    WorkflowStep.REVIEW: ReviewPage,
    WorkflowStep.ENGINEERING: EngineeringPage,
}


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


_STACKS: list = []


@pytest.fixture(autouse=True)
def _tear_down_pages():
    """``WorkspaceHost.activate`` schedules ``QTimer.singleShot(0, page.auto_fit_tables)``. Run those timers while
    the pages are alive and delete the widgets explicitly; otherwise they fire (or crash) inside a later,
    unrelated test after the pages were garbage-collected."""
    yield
    QCoreApplication.processEvents()
    while _STACKS:
        stack = _STACKS.pop()
        stack.close()
        stack.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QCoreApplication.processEvents()


def _legacy_activate(host: WorkspaceHost, step) -> None:
    """The host's behaviour before this change: show (pages refresh in showEvent), refresh,
    activate, on_enter."""
    if host._current is not None and host._current != step:
        previous = host._pages.get(host._current)
        if previous is not None:
            previous.on_leave()
            previous.deactivate()
    page = host._pages[step]
    host._stack.setCurrentWidget(page)          # _host_activating stays False: showEvent refreshes
    page.refresh()
    page.activate()
    page.on_enter()
    host._current = step


def _build(count=90, steps=tuple(PAGES)):
    """Pages first, data afterwards: the order of the real application (the pages exist from start-up
    and a load publishes the snapshot later), so activating a page is its first look at the data."""
    ctx = ApplicationContext()
    stack = QStackedWidget()
    stack._active_module = WorkbenchModule.DEVELOPMENT
    pages = {}
    for step in steps:
        page = PAGES[step](ctx, stack)
        stack.addWidget(page)
        pages[step] = page
    snapshot = build_class_creation_snapshot(count, structures=3, members_per_family=40)
    snapshot.product = Product(id="p1", code="DSK", name="Desk", category="Desks")
    ctx.register_pdm_snapshot(snapshot)
    ctx.activate_snapshot_source("pdm")
    ctx.engineering_initialization_service.initialize(snapshot)
    stack.show()
    _STACKS.append(stack)
    return ctx, stack, WorkspaceHost(stack, pages), pages


_UUID = re.compile(r"[0-9a-f]{32}")


def _snapshot_text(ctx) -> str:
    return _UUID.sub("U", json.dumps(snapshot_to_dict(ctx.active_snapshot), sort_keys=True, default=str))


def _widget_state(page) -> list:
    # A rebuild leaves the previous cards/rows scheduled for deletion; flush them so only live
    # widgets are compared (the legacy triple refresh leaves more of them behind).
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()
    state = []
    for widget in page.findChildren(object):
        kind = type(widget).__name__
        if isinstance(widget, QTableWidget):
            cells = [
                (r, c, (widget.item(r, c).text(), int(widget.item(r, c).checkState().value))
                 if widget.item(r, c) is not None else None)
                for r in range(widget.rowCount()) for c in range(widget.columnCount())
            ]
            state.append((kind, widget.objectName(), widget.rowCount(), widget.columnCount(), cells))
        elif isinstance(widget, QTreeWidget):
            def walk(item):
                return (item.text(0), [walk(item.child(i)) for i in range(item.childCount())])
            state.append((kind, widget.objectName(),
                          [walk(widget.topLevelItem(i)) for i in range(widget.topLevelItemCount())]))
        elif isinstance(widget, QListWidget):
            state.append((kind, widget.objectName(), [widget.item(i).text() for i in range(widget.count())]))
        elif isinstance(widget, QLabel):
            state.append((kind, widget.objectName(), widget.text()))
        elif isinstance(widget, (QPlainTextEdit, QTextEdit)):
            state.append((kind, widget.objectName(), widget.toPlainText()))
        elif isinstance(widget, QLineEdit):
            state.append((kind, widget.objectName(), widget.text()))
        elif isinstance(widget, QComboBox):
            state.append((kind, widget.objectName(), widget.currentText(), widget.count()))
        elif isinstance(widget, QPushButton):
            state.append((kind, widget.objectName(), widget.text(), widget.isEnabled()))
    return [_UUID.sub("U", json.dumps(item, default=str)) for item in state]


def _count_refreshes(pages):
    counts = {step: 0 for step in pages}
    for step, page in pages.items():
        original = page.refresh

        def counted(*args, _step=step, _original=original, **kwargs):
            counts[_step] += 1
            return _original(*args, **kwargs)

        page.refresh = counted
    return counts


# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("step", list(PAGES), ids=lambda s: s.name)
def test_activation_leaves_page_and_snapshot_exactly_as_the_legacy_sequence_did(step):
    old_ctx, old_stack, old_host, old_pages = _build()
    new_ctx, new_stack, new_host, new_pages = _build()

    _legacy_activate(old_host, step)
    new_host.activate(step)

    assert _snapshot_text(new_ctx) == _snapshot_text(old_ctx)
    assert _widget_state(new_pages[step]) == _widget_state(old_pages[step])


def test_a_navigation_tour_ends_in_the_same_state_as_the_legacy_tour():
    tour = [WorkflowStep.CLASS_CREATION, WorkflowStep.ARTICLES, WorkflowStep.TEXT, WorkflowStep.RELATION,
            WorkflowStep.PRICING, WorkflowStep.PRICING_RELATION, WorkflowStep.REVIEW,
            WorkflowStep.ENGINEERING, WorkflowStep.ARTICLES,
            WorkflowStep.CLASS_CREATION, WorkflowStep.PRICING]
    old_ctx, _s1, old_host, old_pages = _build()
    new_ctx, _s2, new_host, new_pages = _build()

    for step in tour:
        _legacy_activate(old_host, step)
        new_host.activate(step)
        assert _snapshot_text(new_ctx) == _snapshot_text(old_ctx), step
        assert _widget_state(new_pages[step]) == _widget_state(old_pages[step]), step


def test_reentering_a_page_shows_data_that_changed_while_it_was_hidden():
    from models.price_record import PriceRecord

    ctx, _stack, host, pages = _build()
    host.activate(WorkflowStep.PRICING)
    assert pages[WorkflowStep.PRICING]._table.rowCount() == 0
    host.activate(WorkflowStep.ARTICLES)
    ctx.active_snapshot.price_records.append(PriceRecord(
        is_global=False, article_code="DSK", variant_condition="", level="B", value=12.5, currency="GBP"))

    host.activate(WorkflowStep.PRICING)

    assert pages[WorkflowStep.PRICING]._table.rowCount() == 1


def test_pages_that_were_refreshed_three_times_are_refreshed_once():
    expected_new = {
        WorkflowStep.PRICING: 1, WorkflowStep.REVIEW: 1,
        WorkflowStep.ENGINEERING: 1, WorkflowStep.CLASS_CREATION: 1,
    }
    for step, expected in expected_new.items():
        old_ctx, _s1, old_host, old_pages = _build(steps=(step, WorkflowStep.TEXT))
        new_ctx, _s2, new_host, new_pages = _build(steps=(step, WorkflowStep.TEXT))
        old_host.activate(WorkflowStep.TEXT)            # make ``step`` a page that is hidden first
        new_host.activate(WorkflowStep.TEXT)
        old_counts, new_counts = _count_refreshes(old_pages), _count_refreshes(new_pages)

        _legacy_activate(old_host, step)
        new_host.activate(step)

        assert new_counts[step] == expected, (step, new_counts[step])
        assert old_counts[step] > new_counts[step], (step, old_counts[step])


def test_pages_whose_on_enter_does_more_than_refresh_keep_their_refresh_before_it():
    """Articles / Text / Relation / PricingRelation: never fewer than one host refresh, never more than before."""
    for step in (WorkflowStep.ARTICLES, WorkflowStep.TEXT, WorkflowStep.RELATION, WorkflowStep.PRICING_RELATION):
        old_ctx, _s1, old_host, old_pages = _build(steps=(step, WorkflowStep.REVIEW))
        new_ctx, _s2, new_host, new_pages = _build(steps=(step, WorkflowStep.REVIEW))
        old_host.activate(WorkflowStep.REVIEW)
        new_host.activate(WorkflowStep.REVIEW)
        old_counts, new_counts = _count_refreshes(old_pages), _count_refreshes(new_pages)

        _legacy_activate(old_host, step)
        new_host.activate(step)

        assert 1 <= new_counts[step] <= old_counts[step], (step, new_counts[step], old_counts[step])


def test_show_time_refresh_still_happens_when_a_page_is_shown_outside_the_host():
    ctx, stack, host, pages = _build(steps=(WorkflowStep.PRICING, WorkflowStep.TEXT))
    stack.setCurrentWidget(pages[WorkflowStep.TEXT])
    counts = _count_refreshes(pages)

    stack.setCurrentWidget(pages[WorkflowStep.PRICING])        # not via the host

    assert counts[WorkflowStep.PRICING] == 1


def test_the_activation_flag_is_always_cleared():
    ctx, stack, host, pages = _build(steps=(WorkflowStep.PRICING,))
    host.activate(WorkflowStep.PRICING)
    assert pages[WorkflowStep.PRICING]._host_activating is False


# --------------------------------------------------------------------------------------
def test_refreshing_hidden_pages_after_a_load_materialises_snapshot_data():
    """Why ``_on_engineering_ready`` must keep refreshing every dependent page. In the real order
    (pages exist, data arrives later) the refresh of Class Creation, Text and Relation *changes the
    snapshot* (article sets / reduced articles, text blocks, relation objects) that a later export
    reads, even if the page is never opened. Deferring those refreshes would change an export."""
    ctx = ApplicationContext()
    stack = QStackedWidget()
    _STACKS.append(stack)
    stack._active_module = WorkbenchModule.DEVELOPMENT
    pages = {step: PAGES[step](ctx, stack) for step in PAGES}
    for page in pages.values():
        stack.addWidget(page)
    snapshot = build_class_creation_snapshot(90, structures=3, members_per_family=40)
    snapshot.product = Product(id="p1", code="DSK", name="Desk", category="Desks")
    ctx.register_pdm_snapshot(snapshot)
    ctx.activate_snapshot_source("pdm")
    ctx.engineering_initialization_service.initialize(snapshot)

    changed = []
    for step in (WorkflowStep.CLASS_CREATION, WorkflowStep.TEXT, WorkflowStep.RELATION):
        before = _snapshot_text(ctx)
        pages[step].refresh()
        if _snapshot_text(ctx) != before:
            changed.append(step)

    assert changed == [WorkflowStep.CLASS_CREATION, WorkflowStep.TEXT, WorkflowStep.RELATION]
