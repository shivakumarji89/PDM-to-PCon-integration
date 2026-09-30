"""Reusable Qt background-task primitive for workflow pages.

The runner owns only execution mechanics. Workflow-specific code stays in the
service/page that owns the operation, while completion, failure, and optional
streamed progress are delivered back through Qt signals.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal


class BackgroundTaskSignals(QObject):
    """Signals emitted by BackgroundTask."""

    progress = Signal(object)
    finished = Signal(object)
    failed = Signal(str)


class BackgroundTask(QRunnable):
    """Run one callable on the shared Qt thread pool.

    ``work`` receives ``signals.progress.emit`` as its only callback. The
    callable must not touch Qt widgets; progress/results are marshalled back to
    the GUI through the signals.
    """

    def __init__(self, work: Callable[[Callable[[Any], None]], Any]) -> None:
        super().__init__()
        self._work = work
        self.signals = BackgroundTaskSignals()

    def run(self) -> None:
        try:
            result = self._work(self.signals.progress.emit)
        except Exception as error:
            self.signals.failed.emit(str(error))
        else:
            self.signals.finished.emit(result)
