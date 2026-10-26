"""Background execution of a SyteLine export job (keeps the UI thread free)."""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QRunnable, Signal

from core.cancellation import OperationCancelled
from services.syteline_export.job import ExportJob, ExportResult
from ui.workers.background_task import task_host

LOGGER = logging.getLogger("syteline_export")


class ExportSignals(QObject):
    status = Signal(str)
    finished = Signal(object)   # ExportResult

    def __init__(self):
        super().__init__(task_host())
        self._cancel = None
        self.finished.connect(self._release)

    def bind(self, job, owner):
        self._cancel = job.cancel
        owner.destroyed.connect(self._owner_destroyed)

    def _owner_destroyed(self, *_args):
        if self._cancel is not None:
            self._cancel()

    def _release(self, _result):
        self._cancel = None
        self.deleteLater()


class ExportWorker(QRunnable):
    """Runs ``job.execute()`` off the UI thread and always emits exactly one ``finished``."""

    def __init__(self, job: ExportJob, signals: ExportSignals) -> None:
        super().__init__()
        self._job = job
        self._signals = signals

    def run(self) -> None:
        try:
            result = self._job.execute()
        except OperationCancelled as exc:
            result = ExportResult(status="cancelled", message=str(exc) or "Export cancelled; no output was published.")
        except BaseException as exc:  # the worker thread must never die silently
            LOGGER.exception("SyteLine export worker crashed")
            result = ExportResult(
                status="failed", message=f"Export crashed unexpectedly: {exc}",
                errors=(f"{type(exc).__name__}: {exc}",),
            )
        self._signals.finished.emit(result)


class MetadataSignals(QObject):
    done = Signal(object)
    failed = Signal(object)


class MetadataWorker(QRunnable):
    """Runs a read-only metadata fetch off the UI thread; the page applies the result on the UI thread."""

    def __init__(self, fetch, signals: MetadataSignals) -> None:
        super().__init__()
        self._fetch = fetch
        self._signals = signals

    def run(self) -> None:
        try:
            result = self._fetch()
        except Exception as exc:
            LOGGER.warning("SyteLine metadata fetch failed: %s", exc)
            self._signals.failed.emit(exc)
        else:
            self._signals.done.emit(result)
