"""Run one export at a time on a worker thread, with GUI-thread callbacks.

Exports used to run inside Qt slots and froze the window for their whole duration. ``ExportRunner``
moves the service call onto the shared thread pool through :class:`ReportedTask` and keeps the
behaviour the synchronous handlers relied on:

* only one export runs at a time (``begin`` fails while another holds the slot), so two exports can
  never write the same output concurrently;
* a modal status popup blocks input to the main window while the export runs (no Cancel button: the
  export services have no cancellation checkpoints and write non-transactionally, so a cancel could
  only be reported, never honoured), which also keeps the user from editing the snapshot mid-export;
* the work callable runs on the worker thread and must not touch widgets; ``finished`` / ``failed``
  run on the GUI thread, where the caller shows the result.

Snapshot isolation stays the caller's job: take the isolating copy (``prepare_mdb_export_snapshot`` /
``copy.deepcopy``) on the GUI thread *before* calling :meth:`run`, and hand the copy to the work.
"""
from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget

from ui.widgets.busy_popup import BusyPopup
from ui.workers.background_task import ReportedTask


class ExportRunner(QObject):
    def __init__(self, owner: QWidget) -> None:
        super().__init__(owner)
        self._owner = owner
        self._claimed = False
        self._popup: BusyPopup | None = None
        self._task: ReportedTask | None = None

    @property
    def busy(self) -> bool:
        return self._claimed

    def begin(self, title: str, *, popup: bool = True) -> bool:
        """Claim the single export slot. Returns False when an export is already running."""
        if self._claimed:
            return False
        self._claimed = True
        if popup:
            self._popup = BusyPopup(title, self._owner)
            self._popup.show_centered()
        return True

    def status(self, text: Any) -> None:
        """Update the popup's status line (GUI thread; also the work's progress callback)."""
        if self._popup is not None:
            self._popup.set_status(str(text))

    def end(self) -> None:
        """Release the slot and close the popup. Safe to call more than once."""
        popup, self._popup = self._popup, None
        self._claimed = False
        if popup is not None:
            popup.close()
            popup.deleteLater()

    def run(
        self,
        work: Callable[[Callable[[Any], None]], Any],
        *,
        finished: Callable[[Any], None],
        failed: Callable[[str], None],
    ) -> None:
        """Run ``work(emit)`` on a worker thread; ``emit(text)`` updates the popup status.

        The slot must have been claimed with :meth:`begin`. Callbacks are responsible for calling
        :meth:`end` (or :meth:`run` again for a follow-up step) before they show dialogs; if a
        callback raises, the slot is released so the next export is not blocked.
        """
        if not self._claimed:
            raise RuntimeError("ExportRunner.run() needs begin() first")

        def guarded(callback):
            def call(value):
                try:
                    callback(value)
                except Exception:
                    self.end()
                    raise
            return call

        task = ReportedTask(self._owner)
        self._task = task
        task.start(
            work,
            finished=guarded(finished),
            failed=guarded(failed),
            cancelled=guarded(failed),
            progress=self.status,
        )
