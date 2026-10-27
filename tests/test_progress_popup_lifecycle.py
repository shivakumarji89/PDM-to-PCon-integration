"""Progress popup lifecycle: binding, updates, terminal states, reuse, cleanup.

Uses the real ``QThreadPool`` / ``ReportedTask`` / ``ProgressDialog`` so queued
cross-thread delivery is exercised, plus the real ``ProductPage`` driven with a
stub PDM service for the Load Family / Add Family to Session lifecycle.
"""
from __future__ import annotations

import os
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

from core.cancellation import CancellationToken, cancellation_scope
from core.progress import ProgressReporter
from models.product import Product
from models.snapshot import Snapshot
from services.engineering.engineering_reduction_service import EngineeringReductionService
from services.pdm_service import PDMService, ProductLoadResult
from ui.dialogs.progress_dialog import ProgressDialog
from ui.pages.product_page import ProductPage
from ui.workers.background_task import ReportedTask


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _drain():
    yield
    QThreadPool.globalInstance().waitForDone(5000)
    _flush()


def _flush() -> None:
    QCoreApplication.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def _pump(predicate, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("timed out waiting for the Qt event loop")
        QCoreApplication.processEvents()
        time.sleep(0.002)


def _percent(dialog: ProgressDialog) -> int:
    return int(dialog._percent.text().rstrip("%"))


def _start(owner, dialog, work, *, total=4, title="Run", subject="Subj"):
    """The same order every page uses: bind, begin, show, then start the task."""
    run = ReportedTask(owner)
    dialog.bind(run.reporter)
    run.reporter.begin(total, title=title, subject=subject)
    dialog.show()
    outcome: dict = {}
    run.start(
        work,
        finished=lambda r: outcome.setdefault("finished", r),
        failed=lambda m: outcome.setdefault("failed", m),
        cancelled=lambda m: outcome.setdefault("cancelled", m),
    )
    return run, outcome


@pytest.fixture
def dialog():
    dlg = ProgressDialog()
    yield dlg
    dlg.close()
    dlg.deleteLater()


# -- visibility, binding and live updates -----------------------------------


def test_popup_is_visible_and_bound_before_the_task_runs(dialog):
    release = threading.Event()
    ran_with = {}

    def work(_emit):
        ran_with["visible"] = dialog.isVisible()
        ran_with["bound"] = dialog._reporter
        release.wait(5)
        return "ok"

    owner = ProgressDialog()
    run, outcome = _start(owner, dialog, work)
    assert dialog.isVisible() and dialog._reporter is run.reporter
    assert dialog._title.text() == "Run"        # begin() output survived the bind
    release.set()
    _pump(lambda: outcome)
    assert ran_with["bound"] is run.reporter
    owner.deleteLater()


def test_worker_progress_reaches_the_dialog_while_work_is_running(dialog):
    step_done = threading.Event()
    release = threading.Event()

    def work(_emit):
        run.reporter.advance("Step one")
        step_done.set()
        release.wait(5)
        return "ok"

    owner = ProgressDialog()
    run, outcome = _start(owner, dialog, work)
    assert step_done.wait(5)
    _pump(lambda: _percent(dialog) >= 25)
    assert dialog._progress_card._operation.text() == "Step one"
    assert not outcome                          # still running
    release.set()
    _pump(lambda: outcome)
    owner.deleteLater()


def test_success_reaches_a_consistent_terminal_state(dialog):
    owner = ProgressDialog()
    run, outcome = _start(owner, dialog, lambda _e: "done")
    _pump(lambda: outcome and dialog._finished)
    assert outcome == {"finished": "done"}
    assert _percent(dialog) == 100
    assert dialog._cancel_btn.text() == "Close" and dialog._cancel_btn.isEnabled()
    owner.deleteLater()


def test_failure_reaches_a_terminal_state_without_faking_100(dialog):
    def work(_emit):
        run.reporter.advance("Half way")
        raise RuntimeError("boom")

    owner = ProgressDialog()
    run, outcome = _start(owner, dialog, work, total=2)
    _pump(lambda: outcome and dialog._finished)
    assert outcome == {"failed": "boom"}
    assert _percent(dialog) < 100
    assert dialog._progress_card._operation.text() == "boom"
    assert dialog._cancel_btn.text() == "Close"
    owner.deleteLater()


def test_cancel_click_cancels_cooperatively_and_ends_consistently(dialog):
    started = threading.Event()

    def work(_emit):
        started.set()
        while True:
            run.reporter.note("working")      # checkpoint raises once cancelled
            time.sleep(0.005)

    owner = ProgressDialog()
    run, outcome = _start(owner, dialog, work)
    assert started.wait(5)
    dialog._cancel_btn.click()
    assert dialog._cancel_btn.text() == "Cancelling..." and not dialog._cancel_btn.isEnabled()
    _pump(lambda: outcome and dialog._finished)
    assert list(outcome) == ["cancelled"]
    assert _percent(dialog) < 100
    assert dialog._cancel_btn.text() == "Close" and dialog._cancel_btn.isEnabled()
    owner.deleteLater()


# -- closing policy ---------------------------------------------------------


def test_closing_the_popup_hides_it_without_cancelling_or_unbinding(dialog):
    release, finish = threading.Event(), threading.Event()

    def work(_emit):
        release.wait(5)
        run.reporter.advance("after reopen")
        finish.wait(5)
        return "ok"

    owner = ProgressDialog()
    run, outcome = _start(owner, dialog, work, total=2)
    dialog.close()
    assert not dialog.isVisible()
    assert not run.reporter.is_cancelled()
    assert dialog._reporter is run.reporter
    release.set()
    _pump(lambda: _percent(dialog) >= 50)         # hidden dialog still updates
    dialog.show()
    assert dialog._progress_card._operation.text() == "after reopen"
    finish.set()
    _pump(lambda: outcome)
    owner.deleteLater()


# -- reuse, stale runs and cleanup -----------------------------------------


def test_reusing_the_dialog_resets_it_for_the_next_run(dialog):
    owner = ProgressDialog()
    run1, out1 = _start(owner, dialog, lambda _e: "one", title="First")
    _pump(lambda: out1 and dialog._finished)
    assert dialog._cancel_btn.text() == "Close"

    release = threading.Event()
    run2, out2 = _start(owner, dialog, lambda _e: release.wait(5), title="Second", subject="Next")
    assert dialog._reporter is run2.reporter
    assert not dialog._finished and _percent(dialog) == 0
    assert dialog._title.text() == "Second" and dialog._subtitle.text() == "Next"
    assert dialog._cancel_btn.text() == "Cancel" and dialog._cancel_btn.isEnabled()
    release.set()
    _pump(lambda: out2)
    owner.deleteLater()


def test_older_runs_events_cannot_overwrite_a_newer_run(dialog):
    owner = ProgressDialog()
    old = ProgressReporter()
    old.begin(4, title="Old", subject="old")
    dialog.bind(old)
    # Events the old run posted from its worker thread, not yet delivered.
    t = threading.Thread(target=lambda: (old.advance("old step"), old.advance("old step 2")))
    t.start(); t.join()

    new = ProgressReporter()
    dialog.bind(new)
    new.begin(10, title="New", subject="new")
    new.advance("new step")
    _flush()
    old.finish(True, "old finished")              # a late terminal event too
    _flush()

    assert dialog._title.text() == "New"
    assert dialog._progress_card._operation.text() == "new step"
    assert _percent(dialog) == 10
    assert not dialog._finished
    owner.deleteLater()


def test_pending_auto_dismiss_of_an_earlier_run_never_hides_the_next_run(dialog):
    owner = ProgressDialog()
    first = ProgressReporter()
    dialog.bind(first)
    first.begin(1)
    first.finish(True, "done")                    # arms the auto-dismiss
    assert dialog._dismiss_timer.isActive()

    second = ProgressReporter()
    dialog.bind(second)
    second.begin(2)
    assert not dialog._dismiss_timer.isActive()   # cancelled by the rebind
    dialog.show()
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:            # outlive the 700 ms window
        QCoreApplication.processEvents()
        time.sleep(0.01)
    assert dialog.isVisible()
    owner.deleteLater()


def test_unbind_detaches_every_connection_exactly_once(dialog):
    reporter = ProgressReporter()
    dialog.bind(reporter)
    reporter.begin(4, title="T")
    reporter.advance("a")
    dialog.unbind_reporter(reporter)
    assert dialog._reporter is None
    before = (_percent(dialog), dialog._progress_card._operation.text())
    reporter.advance("b")
    reporter.finish(True, "x")
    _flush()
    assert (_percent(dialog), dialog._progress_card._operation.text()) == before
    assert not dialog._finished
    cancels = []
    reporter.request_cancel = lambda: cancels.append(1)
    dialog.cancel_requested.emit()
    assert cancels == [] and not reporter.is_cancelled()


def test_unbinding_a_finished_run_does_not_disturb_a_newer_one(dialog):
    old, new = ProgressReporter(), ProgressReporter()
    dialog.bind(old)
    dialog.bind(new)
    dialog.unbind_reporter(old)                   # late cleanup of the old run
    assert dialog._reporter is new
    new.begin(2)
    new.advance("still wired")
    _flush()
    assert dialog._progress_card._operation.text() == "still wired"


def test_rebinding_after_the_old_reporter_was_deleted_is_clean(dialog):
    old = ProgressReporter()
    dialog.bind(old)
    old.deleteLater()
    _flush()
    assert not shiboken6.isValid(old)
    new = ProgressReporter()
    dialog.bind(new)                              # must not raise
    new.begin(2)
    new.advance("ok")
    _flush()
    assert dialog._reporter is new
    assert dialog._progress_card._operation.text() == "ok"


# -- Load Family / Add Family to Session on the real ProductPage -----------


def _product_page(fake_service):
    from core.application_context import ApplicationContext
    from core.modules import WorkbenchModule

    context = ApplicationContext()
    context._services[PDMService] = fake_service
    with patch.object(ProductPage, "_load_navigator", lambda *a, **k: None):
        page = ProductPage(context)
    page.set_module(WorkbenchModule.DEVELOPMENT)
    products = [Product(id="1", code="P1", name="One"), Product(id="2", code="P2", name="Two")]
    page._selected_family_products = lambda: (products, "Fam")
    page._refresh_display = lambda *a, **k: None
    return page


class _FakeService:
    def __init__(self, ok=True, gate=None, steps=3):
        self.ok, self.gate, self.steps = ok, gate, steps
        self.calls = []

    def _run(self, kind, reporter):
        self.calls.append(kind)
        for i in range(self.steps):
            reporter.advance(f"{kind} step {i}")
        if self.gate is not None:
            self.gate.wait(5)
            reporter.note("after gate")
        return ProductLoadResult(self.ok, "fine" if self.ok else "load failed",
                                 Snapshot(product=Product(id="1", code="P1")) if self.ok else None, [])

    def load_family(self, products, name, reporter=None, **kw):
        return self._run("load", reporter)

    def add_family_to_session(self, products, name, reporter=None, **kw):
        return self._run("add", reporter)


@pytest.fixture
def no_message_box(monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: shown.append(a[2]))
    return shown


@pytest.mark.parametrize("action,total,kind", [
    ("_on_load_family", 20, "load"),
    ("_on_add_family_to_session", 10, "add"),
])
def test_family_load_shows_popup_updates_it_and_cleans_up_once(action, total, kind):
    gate = threading.Event()
    service = _FakeService(gate=gate)
    page = _product_page(service)
    getattr(page, action)()
    dialog, reporter = page._progress_dialog, page._family_reporter

    assert dialog.isVisible() and dialog._reporter is reporter    # before work
    assert dialog._subtitle.text() == "Fam"
    _pump(lambda: dialog._progress_card._operation.text() == f"{kind} step 2")
    assert 0 < _percent(dialog) < 100
    assert page._family_run.active

    done = []
    page.load_complete.connect(lambda: done.append(1))
    gate.set()
    _pump(lambda: done)
    _pump(lambda: dialog._finished)
    assert _percent(dialog) == 100
    assert dialog._reporter is None                                # released once
    assert page._family_reporter is None and not page._family_run.active
    assert dialog._cancel_btn.text() == "Close"
    _flush()
    assert not shiboken6.isValid(reporter)                          # reporter deleted


def test_family_load_failure_is_terminal_and_cleans_up(no_message_box):
    page = _product_page(_FakeService(ok=False))
    page._on_load_family()
    dialog = page._progress_dialog
    _pump(lambda: dialog._finished)
    assert no_message_box == ["load failed"]
    assert _percent(dialog) < 100
    assert dialog._reporter is None and page._family_reporter is None


def test_family_load_cancel_is_terminal_and_cleans_up():
    gate = threading.Event()
    service = _FakeService(gate=gate, steps=1)
    page = _product_page(service)
    page._on_load_family()
    dialog = page._progress_dialog
    _pump(lambda: dialog._progress_card._operation.text() == "load step 0")
    dialog._cancel_btn.click()
    gate.set()                                   # worker hits its next checkpoint
    _pump(lambda: dialog._finished)
    assert _percent(dialog) < 100
    assert dialog._reporter is None and page._family_reporter is None
    assert not page._family_run.active


def test_second_family_request_reopens_the_hidden_popup_instead_of_ignoring_it():
    gate = threading.Event()
    service = _FakeService(gate=gate)
    page = _product_page(service)
    page._on_load_family()
    dialog = page._progress_dialog
    dialog.close()
    assert not dialog.isVisible()

    _pump(lambda: service.calls == ["load"])     # the worker really started
    page._on_load_family()                       # refused, but visibly
    page._on_add_family_to_session()
    assert dialog.isVisible()
    assert service.calls == ["load"]
    gate.set()
    _pump(lambda: dialog._finished)
    assert service.calls == ["load"]


def test_consecutive_family_loads_reuse_one_dialog_cleanly():
    page = _product_page(_FakeService())
    page._on_load_family()
    dialog = page._progress_dialog
    _pump(lambda: dialog._finished and page._family_reporter is None)

    page._on_add_family_to_session()
    assert page._progress_dialog is dialog
    assert not dialog._finished and dialog._title.text() == "Add Family to Session"
    _pump(lambda: dialog._finished and page._family_reporter is None)
    assert _percent(dialog) == 100


# -- the confirmed slow-load cause: PDM validation moved off the UI thread --


def _reduction_service(call_log):
    candidate = SimpleNamespace(
        set_id="S", base_code="B", product_range="R", product_ids=("1", "2"),
        article_ids=("a", "b"), strategy="primary", strategy_reason="",
    )
    verdict = SimpleNamespace(
        status="validated", reason="", product_range_id=1, product_category_id=1,
        functional_attribute_value_ids=(), filtered_product_ids=(), missing_from_filter=(),
        extra_in_filter=(), extra_outside_known=(), range_population_complete=True,
        unloaded_range_product_count=0,
    )

    def validate_families(candidates, language_id, known_product_ids=()):
        call_log.append(threading.current_thread().name)
        return [verdict for _ in candidates]

    context = SimpleNamespace(
        pdm_family_reduction_service=SimpleNamespace(validate_families=validate_families)
    )
    service = EngineeringReductionService(context)
    service.candidate_families = lambda snapshot, per_product_range=True: (
        __import__("services.engineering.engineering_reduction_service",
                   fromlist=["CandidateFamily"]).CandidateFamily(
            set_id="S", base_code="B", product_range="R", product_ids=("1", "2"),
            article_ids=("a", "b"),
        ),
    )
    return service


def test_prewarmed_validation_is_consumed_once_and_only_for_the_same_snapshot():
    calls: list[str] = []
    service = _reduction_service(calls)
    snapshot = Snapshot(product=Product(id="1", code="P"))

    worker = threading.Thread(
        target=lambda: service.prewarm_article_set_validation(snapshot), name="worker"
    )
    worker.start(); worker.join()
    assert calls == ["worker"]

    first = service.validate_article_sets(snapshot)      # UI call: no new PDM query
    assert calls == ["worker"]
    second = service.validate_article_sets(snapshot)     # one-shot: asks PDM again
    assert len(calls) == 2 and second == first


def test_prewarm_is_ignored_when_the_snapshot_state_changed_or_differs():
    calls: list[str] = []
    service = _reduction_service(calls)
    snapshot = Snapshot(product=Product(id="1", code="P"))
    service.prewarm_article_set_validation(snapshot)
    snapshot.product_range = {"1": "Changed"}            # state moved on since the prewarm
    service.validate_article_sets(snapshot)
    assert len(calls) == 2

    service.prewarm_article_set_validation(snapshot)
    service.validate_article_sets(Snapshot(product=Product(id="9", code="Q")))
    assert len(calls) == 4


def test_prewarm_failure_is_not_fatal_and_leaves_the_live_path_intact():
    service = _reduction_service([])
    service.validate_article_sets = MagicMock(side_effect=RuntimeError("pdm down"))
    service.prewarm_article_set_validation(Snapshot(product=Product(id="1", code="P")))
    assert service._prewarmed_validation is None


def test_prewarm_propagates_cancellation():
    from core.cancellation import OperationCancelled

    service = _reduction_service([])
    service.validate_article_sets = MagicMock(side_effect=OperationCancelled("Cancelled by user."))
    with pytest.raises(OperationCancelled):
        service.prewarm_article_set_validation(Snapshot(product=Product(id="1", code="P")))
    assert service._prewarmed_validation is None


@pytest.mark.parametrize("entry", ["load_family", "add_family_to_session"])
def test_family_load_prewarms_validation_inside_the_cancellable_window(entry):
    order: list[str] = []
    snapshot = Snapshot(product=Product(id="1", code="P"))
    products = [Product(id="1", code="P")]
    context = MagicMock()
    context.active_snapshot = snapshot
    context.engineering_initialization_service.initialize.side_effect = lambda s: order.append("engineering")
    context.engineering_initialization_service.sync.side_effect = lambda s: order.append("engineering")
    context.engineering_reduction_service.prewarm_article_set_validation.side_effect = (
        lambda s: order.append("prewarm"))
    context.snapshot_manager.load_snapshot.side_effect = lambda s: order.append("publish")
    service = PDMService(context)
    result = ProductLoadResult(True, "ok", snapshot, [])
    reporter = MagicMock()

    with patch.object(PDMService, "load_family_articles", return_value=result), \
         patch.object(PDMService, "load_family_details", return_value=result), \
         patch.object(PDMService, "save_family_snapshot"), \
         patch.object(PDMService, "_fetch_and_map", create=True), \
         cancellation_scope(CancellationToken()):
        if entry == "load_family":
            service.load_family(products, "Fam", reporter=reporter, initialize_engineering=True)
        else:
            context.active_snapshot = None          # falls back to a fresh load
            service.add_family_to_session(products, "Fam", reporter=reporter, sync_engineering=True)

    assert order == ["engineering", "prewarm", "publish"]
    reporter.note.assert_any_call("Validating article families against PDM...")
