"""Qt lifecycle of the background worker and the Pricing "Compute Prices" run.

These tests use the real ``QThreadPool`` (not the synchronous stand-in used by
the other page tests), so worker-thread emissions, queued delivery to the GUI
thread, page destruction mid-run and deferred deletion are all exercised.
"""
from __future__ import annotations

import sys
import threading
import time

import pytest
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QThread, QThreadPool
from PySide6.QtWidgets import QApplication

from core.progress import ProgressReporter
from services.pricing_service import PriceComputeResult, PricingService
from ui.pages import pricing_page as pp
from ui.workers.background_task import BackgroundTask, BackgroundTaskSignals, task_host

from tests.test_pricing_page_text_blocks import _page, _rec, _rows


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def errors(monkeypatch):
    """Collect every exception PySide reports from slots or worker callbacks."""
    seen: list[BaseException] = []
    monkeypatch.setattr(sys, "excepthook", lambda _t, value, _tb: seen.append(value))
    monkeypatch.setattr(sys, "unraisablehook", lambda info: seen.append(info.exc_value))
    yield seen
    QThreadPool.globalInstance().waitForDone(5000)


def _pump(predicate, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("timed out waiting for the Qt event loop")
        QCoreApplication.processEvents()
        time.sleep(0.002)


def _flush_deletes() -> None:
    QCoreApplication.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


# -- BackgroundTask ----------------------------------------------------------


def _start(work):
    task = BackgroundTask(work)
    log: dict = {"progress": [], "finished": [], "failed": [], "threads": set()}
    gui = QThread.currentThread()

    def on(kind):
        def slot(value):
            log["threads"].add(QThread.currentThread() is gui)
            log[kind].append(value)
        return slot

    task.signals.progress.connect(on("progress"))
    task.signals.finished.connect(on("finished"))
    task.signals.failed.connect(on("failed"))
    signals = task.signals
    QThreadPool.globalInstance().start(task)
    return signals, log


def test_task_streams_progress_in_order_and_finishes_once_on_gui_thread(errors):
    def work(emit):
        for i in range(20):
            emit(i)
        return "done"

    signals, log = _start(work)
    _pump(lambda: log["finished"])
    _flush_deletes()
    assert log["progress"] == list(range(20))
    assert log["finished"] == ["done"] and log["failed"] == []
    assert log["threads"] == {True}  # plain callables never run on the worker
    assert not shiboken6.isValid(signals)  # released after its outcome
    assert errors == []


def test_task_failure_is_reported_once_without_finished(errors):
    def work(emit):
        emit("partial")
        raise ValueError("boom")

    signals, log = _start(work)
    _pump(lambda: log["failed"])
    _flush_deletes()
    assert log["failed"] == ["boom"] and log["finished"] == []
    assert log["progress"] == ["partial"]
    assert errors == []


def test_task_signals_are_not_owned_by_the_starting_page():
    page = QObject()
    task = BackgroundTask(lambda emit: None)
    assert task.signals.parent() is task_host()
    shiboken6.delete(page)
    assert shiboken6.isValid(task.signals)
    task.run()  # same thread: delivered synchronously
    _flush_deletes()


def test_no_public_signal_after_completion():
    signals = BackgroundTaskSignals()
    seen = []
    signals.progress.connect(seen.append)
    signals.finished.connect(seen.append)
    signals.failed.connect(seen.append)
    signals._worker_finished.emit("result")
    signals._worker_progress.emit("late")
    signals._worker_failed.emit("late failure")
    signals._worker_finished.emit("second result")
    assert seen == ["result"]
    assert signals.completed


def test_worker_does_not_emit_after_signal_owner_is_destroyed():
    started, release = threading.Event(), threading.Event()
    outcome: dict = {}

    def work(emit):
        started.set()
        release.wait(5)
        emit("after owner destroyed")
        return "result"

    task = BackgroundTask(work)
    received = []
    task.signals.progress.connect(received.append)
    task.signals.finished.connect(received.append)

    def run():
        try:
            task.run()
        except BaseException as error:  # pragma: no cover - the regression
            outcome["error"] = error
        else:
            outcome["ok"] = True

    thread = threading.Thread(target=run)
    thread.start()
    assert started.wait(5)
    shiboken6.delete(task.signals)  # e.g. application teardown
    release.set()
    thread.join(5)
    QCoreApplication.processEvents()
    assert outcome == {"ok": True}
    assert received == []


# -- Pricing page ------------------------------------------------------------


class _Fake:
    """Controllable stand-in for PricingService.compute_streaming."""

    def __init__(self, batches, *, gate: bool = False, fail_after=None):
        self.batches = batches
        self.calls = 0
        self.threads: list[bool] = []
        self.started = threading.Event()
        self.release = threading.Event()
        if not gate:
            self.release.set()
        self.fail_after = fail_after

    def __call__(self, service, params, snapshot=None, on_batch=None, batch_size=10, reporter=None):
        self.calls += 1
        self.threads.append(QThread.currentThread() is QCoreApplication.instance().thread())
        self.started.set()
        reporter.begin(len(self.batches), title="Computing Prices")
        records = []
        for index, batch in enumerate(self.batches):
            assert self.release.wait(5)
            if self.fail_after == index:
                raise RuntimeError("batch callback failed")
            records.extend(batch)
            on_batch(batch)
            reporter.advance(f"item {index + 1}")
        reporter.finish(True, f"Priced {len(records)} records")
        result = PriceComputeResult()
        result.records = records
        return result


@pytest.fixture
def pricing(monkeypatch, errors):
    page = _page([_rec(1.0, "EUR")])
    page._context.active_snapshot.generation_program = "layout_studio"  # Maintenance needs an explicit program
    monkeypatch.setattr(PricingService, "target_currencies", lambda self, s, p: ["EUR"])
    dialogs = {"critical": [], "information": []}
    monkeypatch.setattr(pp.QMessageBox, "critical", lambda *a: dialogs["critical"].append(a[-1]))
    monkeypatch.setattr(pp.QMessageBox, "information",
                        lambda *a: dialogs["information"].append(a[-1]))
    activity = {"complete": [], "fail": []}
    service = page._context.activity_service
    for name in ("complete", "fail"):
        original = getattr(service, name)

        def spy(activity_id, message="", _name=name, _original=original):
            activity[_name].append(message)
            return _original(activity_id, message)

        monkeypatch.setattr(service, name, spy)
    state = {"page": page, "dialogs": dialogs, "activity": activity, "errors": errors}

    def use(fake):
        monkeypatch.setattr(PricingService, "compute_streaming", fake)
        return fake

    state["use"] = use
    yield state
    QThreadPool.globalInstance().waitForDone(5000)
    _flush_deletes()


def _batches():
    return [[_rec(float(10 + i), "EUR")] for i in range(4)]


def _idle(page) -> bool:
    return page._price_run is None


def test_streaming_compute_succeeds_in_record_order(pricing):
    page = pricing["page"]
    fake = pricing["use"](_Fake(_batches()))
    page._on_compute()
    run = page._price_run
    reporter = run.reporter
    _pump(lambda: _idle(page))
    _flush_deletes()
    expected = [r for batch in _batches() for r in batch]
    assert [r.value for r in page._records] == [r.value for r in expected]
    assert len(_rows(page)) == len(expected)
    assert fake.calls == 1 and fake.threads == [False]  # computed off the GUI thread
    assert not page._pricing_running and page._compute_btn.isEnabled()
    assert pricing["activity"] == {"complete": ["Priced 4 records"], "fail": []}
    assert pricing["dialogs"]["critical"] == []
    # Worker completion released the run, its reporter and the monitor binding.
    assert not shiboken6.isValid(run) and not shiboken6.isValid(reporter)
    assert page._monitor._reporter is None
    assert pricing["errors"] == []


def test_exception_in_batch_callback_reports_failure_once(pricing):
    page = pricing["page"]
    pricing["use"](_Fake(_batches(), fail_after=2))
    page._on_compute()
    reporter = page._price_run.reporter
    finished = []
    reporter.finished.connect(lambda ok, msg: finished.append((ok, msg)))
    _pump(lambda: _idle(page))
    assert finished == [(False, "batch callback failed")]
    assert pricing["dialogs"]["critical"] == [
        "Price computation failed:\n\nbatch callback failed"
    ]
    assert pricing["activity"] == {"complete": [], "fail": ["batch callback failed"]}
    assert not page._pricing_running and page._compute_btn.isEnabled()
    assert pricing["errors"] == []


def test_exception_in_page_batch_slot_does_not_break_the_run(pricing, monkeypatch):
    page = pricing["page"]
    pricing["use"](_Fake(_batches()))
    append = page._append_batch
    calls = []

    def flaky(batch):
        calls.append(batch)
        if len(calls) == 1:
            raise ValueError("render failed")
        append(batch)

    monkeypatch.setattr(page, "_append_batch", flaky)
    page._on_compute()
    _pump(lambda: _idle(page))
    # The slot error is reported once by Qt; the run still finishes cleanly and
    # the final authoritative render shows every record in order.
    assert [type(e) for e in pricing["errors"]] == [ValueError]
    pricing["errors"].clear()
    assert len(calls) == 4
    assert [r.value for r in page._records] == [10.0, 11.0, 12.0, 13.0]
    assert pricing["activity"]["complete"] == ["Priced 4 records"]


def test_exception_during_progress_reporting_reports_failure_once(pricing, monkeypatch):
    page = pricing["page"]
    pricing["use"](_Fake(_batches()))

    def broken_advance(self, step_text=""):
        raise RuntimeError("progress reporting failed")

    monkeypatch.setattr(ProgressReporter, "advance", broken_advance)
    page._on_compute()
    _pump(lambda: _idle(page))
    assert pricing["dialogs"]["critical"] == [
        "Price computation failed:\n\nprogress reporting failed"
    ]
    assert pricing["activity"] == {"complete": [], "fail": ["progress reporting failed"]}
    assert not page._pricing_running and page._compute_btn.isEnabled()
    assert pricing["errors"] == []


def test_navigating_away_mid_run_still_completes_the_page(pricing):
    page = pricing["page"]
    fake = pricing["use"](_Fake(_batches(), gate=True))
    page.show()
    page._on_compute()
    assert fake.started.wait(5)
    page.hide()  # switching workflow steps hides the page
    fake.release.set()
    _pump(lambda: _idle(page))
    assert [r.value for r in page._records] == [10.0, 11.0, 12.0, 13.0]
    assert pricing["activity"]["complete"] == ["Priced 4 records"]
    assert pricing["errors"] == []


def test_destroying_page_mid_run_keeps_worker_objects_alive(pricing):
    page = pricing["page"]
    fake = pricing["use"](_Fake(_batches(), gate=True))
    page._on_compute()
    run = page._price_run
    reporter = run.reporter
    assert fake.started.wait(5)
    shiboken6.delete(page)  # closing the window destroys the page
    assert shiboken6.isValid(run) and shiboken6.isValid(reporter)
    assert reporter.is_cancelled()
    fake.release.set()
    _pump(lambda: not run.active)
    _flush_deletes()
    assert not shiboken6.isValid(run) and not shiboken6.isValid(reporter)
    # The Activity is still closed exactly once; the destroyed page is not called.
    assert pricing["activity"] == {"complete": [], "fail": []}
    activities = page._context.activity_service.finished_snapshots()
    assert activities[-1].status.value == "cancelled"
    assert pricing["dialogs"] == {"critical": [], "information": []}
    assert pricing["errors"] == []


def test_destroying_page_before_failure_reports_without_second_exception(pricing):
    page = pricing["page"]
    fake = pricing["use"](_Fake(_batches(), gate=True, fail_after=1))
    page._on_compute()
    run = page._price_run
    assert fake.started.wait(5)
    shiboken6.delete(page)
    fake.release.set()
    _pump(lambda: not run.active)
    assert pricing["activity"] == {"complete": [], "fail": []}
    assert page._context.activity_service.finished_snapshots()[-1].status.value == "cancelled"
    assert pricing["dialogs"]["critical"] == []
    assert pricing["errors"] == []


def test_monitor_cancel_preserves_snapshot_and_allows_successful_retry(pricing):
    page = pricing["page"]
    baseline = list(page._context.active_snapshot.price_records)
    fake = pricing["use"](_Fake(_batches(), gate=True))
    page._on_compute()
    assert fake.started.wait(5)
    page._monitor._cancel_btn.click()
    page._on_compute()
    assert fake.calls == 1
    fake.release.set()
    assert QThreadPool.globalInstance().waitForDone(5000)
    _pump(lambda: _idle(page))
    assert page._context.active_snapshot.price_records == baseline
    assert [r.value for r in page._records] == [r.value for r in baseline]
    assert page._compute_btn.isEnabled()
    assert pricing["dialogs"]["critical"] == []
    assert page._context.activity_service.finished_snapshots()[-1].status.value == "cancelled"
    pricing["use"](_Fake(_batches()))
    page._on_compute()
    _pump(lambda: _idle(page))
    assert [r.value for r in page._records] == [10.0, 11.0, 12.0, 13.0]
    assert pricing["errors"] == []


def test_genuine_worker_error_after_request_remains_failure(pricing):
    page = pricing["page"]
    fake = pricing["use"](_Fake(_batches(), gate=True, fail_after=0))
    page._on_compute()
    assert fake.started.wait(5)
    page._monitor._cancel_btn.click()
    fake.release.set()
    _pump(lambda: _idle(page))
    assert pricing["activity"]["fail"] == ["batch callback failed"]
    assert pricing["dialogs"]["critical"] == [
        "Price computation failed:\n\nbatch callback failed"
    ]
    assert pricing["errors"] == []


def test_activity_reporting_after_activity_ui_is_destroyed(errors):
    from core.application_context import ApplicationContext
    from core.activity.models import ActivityType
    from ui.widgets.activity_panel import ActivityPanel
    from ui.widgets.background_status import BackgroundStatusIndicator

    ctx = ApplicationContext()
    panel = ActivityPanel(ctx.activity_service)
    indicator = BackgroundStatusIndicator(ctx.activity_service)
    handle = ctx.activity_service.start_activity("Computing Prices", ActivityType.GENERIC)
    QCoreApplication.processEvents()
    shiboken6.delete(panel)  # the window (Activity dock + status bar) was closed
    shiboken6.delete(indicator)
    handle.update_step("Pricing EUR 1/4 items...")
    handle.fail("PDM unavailable")
    QCoreApplication.processEvents()
    assert errors == []


def test_repeated_compute_requests_do_not_overlap(pricing):
    page = pricing["page"]
    fake = pricing["use"](_Fake(_batches(), gate=True))
    page._on_compute()
    first = page._price_run
    assert fake.started.wait(5)
    page._compute_btn.setEnabled(True)  # e.g. a source-lock restore re-enabled it
    page._on_compute()
    page._on_compute()
    assert page._price_run is first and fake.calls == 1
    fake.release.set()
    _pump(lambda: _idle(page))
    assert fake.calls == 1
    assert [r.value for r in page._records] == [10.0, 11.0, 12.0, 13.0]
    # Once finished, a new request starts a fresh, independent run.
    second = pricing["use"](_Fake([[_rec(20.0, "EUR")]]))
    page._on_compute()
    assert page._price_run is not None and page._price_run is not first
    _pump(lambda: _idle(page))
    assert second.calls == 1
    assert [r.value for r in page._records] == [20.0]
    assert pricing["activity"]["complete"] == ["Priced 4 records", "Priced 1 records"]
    assert pricing["errors"] == []
