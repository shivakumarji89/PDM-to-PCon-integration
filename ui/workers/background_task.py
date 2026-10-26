"""Reusable Qt background-task primitive for workflow pages.

The runner owns only execution mechanics. Workflow-specific code stays in the
service/page that owns the operation, while completion, failure, and optional
streamed progress are delivered back through Qt signals.

Lifecycle guarantees
--------------------
* The signal object is parented to a long-lived, GUI-thread host object, not to
  the page that started the task and not to Python garbage collection. Closing
  or destroying the page therefore never deletes the object the worker emits on.
* The worker thread only emits private signals. They are delivered (queued) to
  the signal object on the GUI thread, which re-emits the public ``progress`` /
  ``finished`` / ``failed`` signals there - so receivers, including plain
  callables, always run on the GUI thread.
* Exactly one of ``finished`` / ``failed`` / ``cancelled`` is emitted per task. Afterwards no
  public signal is emitted and the signal object is released with
  ``deleteLater`` on the GUI thread.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any
from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope

import shiboken6
from PySide6.QtCore import QCoreApplication, QObject, QRunnable, Signal

_host: QObject | None = None


def task_host() -> QObject:
    """Return the GUI-thread parent for task-owned QObjects.

    Task-owned objects (signal objects, run controllers, progress reporters)
    are children of this host so their C++ lifetime is never decided by a page
    being closed or by a Python reference being dropped on a worker thread.
    Each owner releases its objects explicitly with ``deleteLater`` once the
    task has delivered its outcome.
    """
    global _host
    if _host is None or not shiboken6.isValid(_host):
        host = QObject()
        host.setObjectName("backgroundTaskHost")
        app = QCoreApplication.instance()
        if app is not None and host.thread() is not app.thread():
            host.moveToThread(app.thread())
        _host = host
    return _host


class BackgroundTaskSignals(QObject):
    """Signals emitted by BackgroundTask (always on the signal object's thread)."""

    progress = Signal(object)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    # Internal: emitted from the worker thread, queued to this object's thread.
    _worker_progress = Signal(object)
    _worker_finished = Signal(object)
    _worker_failed = Signal(str)
    _worker_cancelled = Signal(str)

    def __init__(self, parent: QObject | None = None, token: CancellationToken | None = None) -> None:
        super().__init__(parent)
        self._completed = False
        self._token = token
        self._worker_progress.connect(self._deliver_progress)
        self._worker_finished.connect(self._deliver_finished)
        self._worker_failed.connect(self._deliver_failed)
        self._worker_cancelled.connect(self._deliver_cancelled)

    @property
    def completed(self) -> bool:
        """True once a terminal outcome has been delivered."""
        return self._completed

    def _deliver_progress(self, value: Any) -> None:
        if not self._completed and not (self._token and self._token.is_cancelled()):
            self.progress.emit(value)

    def _deliver_cancelled(self, message: str) -> None:
        if self._completed:
            return
        self._completed = True
        try:
            self.cancelled.emit(message)
        finally:
            self._release()

    def _deliver_finished(self, result: Any) -> None:
        if self._completed:
            return
        self._completed = True
        try:
            self.finished.emit(result)
        finally:
            self._release()

    def _deliver_failed(self, message: str) -> None:
        if self._completed:
            return
        self._completed = True
        try:
            self.failed.emit(message)
        finally:
            self._release()

    def _release(self) -> None:
        # Host-owned objects are deleted on their own (GUI) thread; an unparented
        # instance (no QApplication) is simply left to Python.
        if self.parent() is not None:
            self.deleteLater()


class BackgroundTask(QRunnable):
    """Run one callable on the shared Qt thread pool.

    ``work`` receives a progress callback as its only argument; each value it
    is called with is delivered through ``signals.progress`` on the GUI thread.
    The callable must not touch Qt widgets; progress/results are marshalled back
    to the GUI through the signals.
    """

    def __init__(self, work: Callable[[Callable[[Any], None]], Any],
                 *, cancellation_token: CancellationToken | None = None) -> None:
        super().__init__()
        self._work = work
        self.cancellation_token = cancellation_token or CancellationToken()
        self.signals = BackgroundTaskSignals(task_host(), self.cancellation_token)

    def cancel(self) -> None:
        self.cancellation_token.request_cancel()

    def run(self) -> None:
        signals = self.signals

        def report_progress(value: Any) -> None:
            self.cancellation_token.checkpoint()
            if shiboken6.isValid(signals):
                signals._worker_progress.emit(value)

        try:
            with cancellation_scope(self.cancellation_token):
                result = self._work(report_progress)
                self.cancellation_token.commit()
        except OperationCancelled as error:
            outcome, payload = "cancelled", str(error)
        except Exception as error:
            outcome, payload = "failed", str(error)
        else:
            outcome, payload = "finished", result
        # The signal object is only released after this outcome is delivered,
        # so it can only be invalid if it was destroyed externally (application
        # teardown); then there is nobody left to notify.
        if not shiboken6.isValid(signals):
            return
        if outcome == "cancelled":
            signals._worker_cancelled.emit(payload)
        elif outcome == "failed":
            signals._worker_failed.emit(payload)
        else:
            signals._worker_finished.emit(payload)


class ReportedTask(QObject):
    """Host-owned progress run, safe even when its owning widget is destroyed."""

    def __init__(self, owner: QObject) -> None:
        super().__init__(task_host())
        from core.progress import ProgressReporter

        self.reporter = ProgressReporter(self)
        self.active = True
        self._owner: QObject | None = owner
        owner.destroyed.connect(self._owner_destroyed)

    def _owner_destroyed(self, *_args) -> None:
        self._owner = None
        self.reporter.request_cancel()

    def start(self, work, *, finished, failed, cancelled=None, progress=None) -> None:
        from PySide6.QtCore import QThreadPool

        self._finished_callback = finished
        self._failed_callback = failed
        self._cancelled_callback = cancelled
        self._progress_callback = progress
        task = BackgroundTask(work, cancellation_token=self.reporter.cancellation_token)
        task.signals.finished.connect(self._finished)
        task.signals.failed.connect(self._failed)
        task.signals.cancelled.connect(self._cancelled)
        task.signals.progress.connect(self._progress)
        QThreadPool.globalInstance().start(task)

    def _live(self) -> bool:
        return self._owner is not None and shiboken6.isValid(self._owner)

    def _progress(self, value) -> None:
        if self._live() and self._progress_callback is not None:
            self._progress_callback(value)

    def _finish(self, callback, payload, success: bool, message: str) -> None:
        self.active = False
        try:
            if self._live() and callback is not None:
                callback(payload)
        finally:
            self.reporter.finish(success, message)
            self._owner = None
            self._finished_callback = self._failed_callback = None
            self._cancelled_callback = self._progress_callback = None
            self.deleteLater()

    def _finished(self, result) -> None:
        self._finish(self._finished_callback, result, True, "Completed")

    def _failed(self, message: str) -> None:
        self._finish(self._failed_callback, message, False, message)

    def _cancelled(self, message: str) -> None:
        self._finish(self._cancelled_callback, message, False, message)
