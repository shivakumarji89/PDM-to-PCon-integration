"""Reusable progress reporting for long-running operations.

This module provides a single, UI-agnostic :class:`ProgressReporter` that
business logic (services) can drive to report high-level progress and activity
for any long-running task - Load Family, Load Product, Generate, Import, Export,
Synchronization, etc.

Design goals:
  * Business logic depends only on this reporter's simple methods
    (:meth:`ProgressReporter.begin`, :meth:`~ProgressReporter.advance`,
    :meth:`~ProgressReporter.set_product`, :meth:`~ProgressReporter.set_counts`,
    :meth:`~ProgressReporter.log`, :meth:`~ProgressReporter.pause`,
    :meth:`~ProgressReporter.finish`); it never imports or references any widget.
  * The reporter owns the *only* progress calculation (step counter -> percent)
    and the elapsed/remaining estimation, so no consumer duplicates it.
  * UI consumers (a progress dialog and the Activity panel) subscribe to the
    reporter's Qt signals. Multiple consumers can bind to the same reporter.

Only :mod:`PySide6.QtCore` is used (signals + timer); no widgets are imported,
so the reporter is safe to construct and drive from business logic and tests.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer, Signal


class ProgressReporter(QObject):
    """Drives progress + activity events for one long-running operation.

    Consumers connect to the signals; business logic calls the plain methods.
    The reporter is the single source of the percent calculation and the
    elapsed/remaining estimate.
    """

    title_changed = Signal(str)
    family_changed = Signal(str)
    product_changed = Signal(str)
    step_changed = Signal(str)
    progress_changed = Signal(int)
    counts_changed = Signal(int, int, int, int, int, int, int, int)
    metrics_changed = Signal(list)
    elapsed_changed = Signal(int)
    remaining_changed = Signal(int)
    activity = Signal(str, str)
    finished = Signal(bool, str)
    _timer_control = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._total_steps = 0
        self._current_step = 0
        self._start_time = 0.0
        self._committed = 0.0
        self._display = 0.0
        self._last_sec = 0
        self._cancelled = False
        self._finished = False
        self._paused = False

        self._tick_interval = 0.120
        self._timer = QTimer(self)
        self._timer.setInterval(int(self._tick_interval * 1000))
        self._timer.timeout.connect(self._on_tick)
        self._timer_control.connect(self._apply_timer)

    def _apply_timer(self, running: bool) -> None:
        if running:
            self._timer.start()
        else:
            self._timer.stop()

    # -- lifecycle ---------------------------------------------------------
    def begin(self, total_steps: int, *, title: str = "", subject: str = "") -> None:
        """Start a new operation with a known number of ``advance`` steps."""
        self._total_steps = max(1, int(total_steps))
        self._current_step = 0
        self._start_time = time.perf_counter()
        self._committed = 0.0
        self._display = 0.0
        self._last_sec = 0
        self._cancelled = False
        self._finished = False
        self._paused = False
        if title:
            self.title_changed.emit(title)
        if subject:
            self.family_changed.emit(subject)
        self.progress_changed.emit(0)
        self.elapsed_changed.emit(0)
        self.remaining_changed.emit(0)
        self._timer_control.emit(True)

    def advance(self, step_text: str = "") -> None:
        """Complete one step: update the step text, percent, elapsed, remaining."""
        if self._finished or self._paused:
            return
        self._current_step = min(self._current_step + 1, self._total_steps)
        self._committed = self._current_step / self._total_steps
        if self._display < self._committed:
            self._display = self._committed
        if step_text:
            self.step_changed.emit(step_text)
        self.progress_changed.emit(min(int(self._display * 100), 99))
        elapsed = time.perf_counter() - self._start_time
        self._last_sec = int(elapsed)
        self.elapsed_changed.emit(self._last_sec)
        self.remaining_changed.emit(self._estimate_remaining(elapsed, self._committed))

    def note(self, text: str) -> None:
        """Update the step/detail text without advancing the step counter."""
        if not self._finished and text:
            self.step_changed.emit(text)

    def pause(self, message: str = "") -> None:
        """Pause the monitor without completing or cancelling the operation.

        A paused operation remains resumable; unlike :meth:`finish`, this does
        not emit ``finished`` and does not mark the reporter terminal.
        """
        if self._finished:
            return
        self._paused = True
        self._timer_control.emit(False)
        if message:
            self.step_changed.emit(message)

    def finish(self, success: bool = True, message: str = "") -> None:
        """End the operation: force 100%, stop the timer, emit ``finished``."""
        if self._finished:
            return
        self._finished = True
        self._paused = False
        self._timer_control.emit(False)
        self._current_step = self._total_steps
        self._display = 1.0
        self.progress_changed.emit(100)
        self.elapsed_changed.emit(int(time.perf_counter() - self._start_time))
        self.remaining_changed.emit(0)
        if message:
            self.step_changed.emit(message)
        self.finished.emit(success, message)

    # -- subject / detail --------------------------------------------------
    def set_title(self, title: str) -> None:
        self.title_changed.emit(title)

    def set_subject(self, subject: str) -> None:
        self.family_changed.emit(subject)

    def set_product(self, name: str) -> None:
        self.product_changed.emit(name)

    def set_counts(self, products: int, total_products: int, articles: int,
                   properties: int, property_values: int, options: int,
                   option_values: int, relations: int = 0) -> None:
        self.counts_changed.emit(products, total_products, articles, properties,
                                 property_values, options, option_values, relations)

    def log(self, kind: str, message: str) -> None:
        self.activity.emit(kind, message)

    def set_metrics(self, items) -> None:
        self.metrics_changed.emit(list(items))

    # -- cancellation (wired for future support) ---------------------------
    def request_cancel(self) -> None:
        """Flag a cancellation request. Business logic may poll
        :meth:`is_cancelled`; no operation is forced to honour it yet."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    # -- internals ---------------------------------------------------------
    def _on_tick(self) -> None:
        if self._finished or self._paused:
            return
        now = time.perf_counter()
        span = 1.0 / self._total_steps
        eff_span = min(span, 0.15)
        if self._current_step >= 1:
            avg_step = (now - self._start_time) / self._current_step
        else:
            avg_step = max(now - self._start_time, 3.0)
        avg_step = max(avg_step, 0.4)
        ceiling = 0.99
        if self._display < ceiling:
            lead = max(0.0, self._display - self._committed)
            damp = eff_span / (eff_span + lead)
            move = eff_span * (self._tick_interval / avg_step) * damp
            if move > 0:
                self._display = min(ceiling, self._display + move)
                self.progress_changed.emit(min(int(self._display * 100), 99))
        elapsed = now - self._start_time
        sec = int(elapsed)
        if sec != self._last_sec:
            self._last_sec = sec
            self.elapsed_changed.emit(sec)
            self.remaining_changed.emit(self._estimate_remaining(elapsed, self._committed))

    @staticmethod
    def _estimate_remaining(elapsed: float, fraction: float) -> int:
        if fraction <= 0.0:
            return 0
        total_estimate = elapsed / fraction
        return max(0, int(total_estimate - elapsed))
