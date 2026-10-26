from __future__ import annotations

from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QThreadPool
from PySide6.QtWidgets import QApplication

from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope
from core.validation_control import ValidationCancelled, ValidationControl, ValidationPaused
from repositories.cancellable_pdm_repository import CancellablePDMRepository, _TrackedCursor
from repositories.pdm_repository import PDMRepository
from services.cancellable_sif_validation_service import CancellableSifValidationService
from services.obx_validation_service import ObxLine, ObxValidationService
from services.sif_validation_service import SifResult
from ui.pages.obx_validation_page import ObxValidationPage, _ObxRunHost, _ObxSignals, _ObxWorker


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def test_validation_control_shares_token_and_preserves_pause():
    token = CancellationToken()
    with cancellation_scope(token):
        control = ValidationControl()
    assert control.cancellation_token is token
    control.pause()
    with pytest.raises(ValidationPaused):
        control.checkpoint()
    control.resume()
    control.checkpoint()
    calls = []
    control.register_cancel_handler(lambda: calls.append("active"))
    token.request_cancel()
    control.cancel()
    control.cancel()
    control.register_cancel_handler(lambda: calls.append("late"))
    assert calls == ["active", "late"]
    with pytest.raises(ValidationCancelled):
        control.checkpoint()
    assert issubclass(ValidationCancelled, OperationCancelled)


def test_cancelled_repository_and_service_never_open_a_connection(monkeypatch):
    calls = []
    monkeypatch.setattr(PDMRepository, "get_connection", lambda self: calls.append("open"))
    control = ValidationControl()
    control.cancel()
    repo = CancellablePDMRepository(None, control)
    with pytest.raises(OperationCancelled):
        repo.get_connection()
    service = CancellableSifValidationService(None)
    with pytest.raises(OperationCancelled):
        service.validate("GBP", [], operation_control=control)
    assert calls == []


@pytest.mark.parametrize("method", [
    "fetch_item_validation_options", "fetch_item_option_increment_prices",
])
@pytest.mark.parametrize("interruption", [ValidationPaused, ValidationCancelled])
def test_option_failures_never_swallow_pause_or_cancel(monkeypatch, method, interruption):
    control = ValidationControl()
    conn = MagicMock()
    monkeypatch.setattr(CancellablePDMRepository, "get_connection", lambda self: conn)

    def interrupt(*args, **kwargs):
        raise interruption("stop")

    monkeypatch.setattr(PDMRepository, method, interrupt)
    cache = {}
    repo = CancellablePDMRepository(None, control, cache)
    with pytest.raises(interruption):
        getattr(repo, method)(["A"], "GBP", "2026-10-25", 1)
    assert repo.last_skipped_option_items == []
    assert all(not value for value in cache.values())
    assert len(control._cancel_handlers) == 1  # Only the caller remains registered.
    conn.close.assert_called_once()


def test_parallel_option_workers_are_drained_before_cancellation_returns(monkeypatch):
    control = ValidationControl()
    entered = [Event(), Event()]
    release = Event()
    done = Event()
    errors = []
    closed = []

    class Connection:
        def close(self):
            closed.append(True)

    monkeypatch.setattr(CancellablePDMRepository, "get_connection", lambda self: Connection())

    def fetch(_repo, items, *args, **kwargs):
        entered[0 if items == ["A"] else 1].set()
        assert release.wait(5)
        control.checkpoint()

    monkeypatch.setattr(PDMRepository, "fetch_item_validation_options", fetch)
    repo = CancellablePDMRepository(None, control, {})

    def work():
        try:
            repo.fetch_item_validation_options(["A", "B"], "GBP", "2026-10-25", 1)
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()

    thread = Thread(target=work)
    thread.start()
    try:
        assert all(event.wait(5) for event in entered)
        control.cancel()
        assert not done.is_set()
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive()
    assert len(errors) == 1 and isinstance(errors[0], OperationCancelled)
    assert len(closed) == 2
    assert len(control._cancel_handlers) == 1


@pytest.mark.parametrize("native_supported", [True, False])
def test_cursor_cancel_is_best_effort_without_cross_thread_connection_close(monkeypatch, native_supported):
    control = ValidationControl()
    entered, release = Event(), Event()
    errors = []
    cancel_calls = []
    closed = []

    class DriverError(Exception):
        pass

    class Cursor:
        def execute(self, *args):
            entered.set()
            assert release.wait(5)
            if native_supported:
                raise DriverError("cancelled SQL")

        def cancel(self):
            cancel_calls.append(True)
            if not native_supported:
                raise NotImplementedError()
            release.set()

        def fetchall(self):
            return []

        def close(self):
            pass

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            closed.append(True)

    monkeypatch.setattr(PDMRepository, "get_connection", lambda self: Connection())
    monkeypatch.setattr(PDMRepository, "_driver", staticmethod(lambda: SimpleNamespace(Error=DriverError)))
    repo = CancellablePDMRepository(None, control)

    def work():
        try:
            repo._execute("SELECT 1", ())
        except BaseException as exc:
            errors.append(exc)

    thread = Thread(target=work)
    thread.start()
    try:
        assert entered.wait(5)
        control.cancel()
        control.cancel()
        if not native_supported:
            assert closed == [] and thread.is_alive()
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive()
    assert cancel_calls == [True] and closed == [True]
    assert len(errors) == 1 and isinstance(errors[0], OperationCancelled)


def test_connection_failure_unregisters_service_cancel_hook(monkeypatch):
    control = ValidationControl()

    def fail(_self):
        raise RuntimeError("offline")

    monkeypatch.setattr(CancellablePDMRepository, "get_connection", fail)
    with pytest.raises(RuntimeError, match="offline"):
        CancellableSifValidationService(None).validate("GBP", [], operation_control=control)
    assert control._cancel_handlers == []


@pytest.mark.parametrize("method", ["execute", "executemany"])
def test_cancel_during_cursor_activation_never_starts_a_statement(monkeypatch, method):
    control = ValidationControl()
    repo = CancellablePDMRepository(None, control)
    cursor = MagicMock()
    activate = repo._set_active

    def activate_then_cancel(raw, connection):
        activate(raw, connection)
        control.cancel()

    monkeypatch.setattr(repo, "_set_active", activate_then_cancel)
    tracked = _TrackedCursor(cursor, repo, object())
    with pytest.raises(OperationCancelled):
        getattr(tracked, method)("SELECT 1")
    cursor.execute.assert_not_called()
    cursor.executemany.assert_not_called()


def test_cancellation_during_duplicate_fanout_stops_before_next_callback():
    control = ValidationControl()
    service = ObxValidationService(None)
    lines = [ObxLine(seq=index, base_article="A", final_article="A", currency="GBP")
             for index in (1, 2)]
    received = []

    class Pricing:
        def validate(self, _currency, _lines, **kwargs):
            kwargs["on_result"](SifResult(seq=1, sku="A", currency="GBP"))

    service._pricing_service = lambda _control: Pricing()

    def on_result(result):
        received.append(result.seq)
        control.cancel()

    with pytest.raises(OperationCancelled):
        service.validate("GBP", lines, site=1, on_result=on_result, operation_control=control)
    assert received == [1]


def test_cancelled_page_drops_queued_results_and_waits_for_both_workers():
    page = MagicMock()
    page._active_control = ValidationControl()
    page._active_control.cancel()
    page._dispatch_workers = 2
    page._discard_results = True
    ObxValidationPage._on_unique_result(page, object())
    ObxValidationPage._on_line_done(page, object())
    ObxValidationPage._on_results(page, ({}, [object()]))
    page._results.append.assert_not_called()
    ObxValidationPage._on_cancelled(page, "stop")
    assert page._dispatch_workers == 1
    page._release_active_control.assert_not_called()
    ObxValidationPage._start_validation(page, [], fresh=True)
    page._begin_live.assert_not_called()
    ObxValidationPage._on_cancelled(page, "stop")
    assert page._dispatch_workers == 0
    page._release_active_control.assert_called_once()


def test_destroyed_page_keeps_worker_reporter_alive_until_drained(monkeypatch):
    import sys
    errors = []
    monkeypatch.setattr(sys, "excepthook", lambda _kind, value, _tb: errors.append(value))
    owner = QObject()
    host = _ObxRunHost(owner)
    reporter = host.reporter
    entered, release = Event(), Event()

    class Service:
        def validate(self, *args, **kwargs):
            entered.set()
            assert release.wait(5)
            kwargs["operation_control"].checkpoint()

    signals = _ObxSignals(host)
    signals.cancelled.connect(host.worker_finished)
    host.workers = 1
    worker = _ObxWorker(Service(), "GBP", [SimpleNamespace(seq=1)], 1, "2026-10-25",
                        reporter, signals, host.control)
    QThreadPool.globalInstance().start(worker)
    try:
        assert entered.wait(5)
        owner.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        assert host.control.is_cancelled()
        assert shiboken6.isValid(reporter)
    finally:
        release.set()
        assert QThreadPool.globalInstance().waitForDone(5000)
    QCoreApplication.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert not shiboken6.isValid(reporter)
    assert errors == []
