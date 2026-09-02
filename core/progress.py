"""Reusable progress reporting for long-running operations.

This module provides a single, UI-agnostic :class:`ProgressReporter` that
business logic (services) can drive to report high-level progress and activity
for any long-running task - Load Family, Load Product, Generate, Import, Export,
Synchronization, etc.

Design goals:
  * Business logic depends only on this reporter's simple methods
    (:meth:`ProgressReporter.begin`, :meth:`~ProgressReporter.advance`,
    :meth:`~ProgressReporter.set_product`, :meth:`~ProgressReporter.set_counts`,
    :meth:`~ProgressReporter.log`, :meth:`~ProgressReporter.finish`); it never
    imports or references any widget.
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

    #: The operation title, e.g. "Loading Family".
    title_changed = Signal(str)
    #: A high-level subject line, e.g. the family name.
    family_changed = Signal(str)
    #: The product currently being processed.
    product_changed = Signal(str)
    #: The current step text, e.g. "Loading Product Options...".
    step_changed = Signal(str)
    #: Overall completion as an integer percentage (0-100).
    progress_changed = Signal(int)
    #: Aggregate counts: (products, total_products, articles, properties,
    #: property_values, options, option_values, relations).
    counts_changed = Signal(int, int, int, int, int, int, int, int)
    #: Generic named metric tiles: a list of (key, label, target, suffix)
    #: tuples, for operations whose counters are not the loading set.
    metrics_changed = Signal(list)
    #: Elapsed whole seconds since :meth:`begin`.
    elapsed_changed = Signal(int)
    #: Estimated remaining whole seconds (0 when unknown).
    remaining_changed = Signal(int)
    #: A single detailed activity line: (kind, message). ``kind`` is a status
    #: vocabulary name such as "info", "success", "warning", "error".
    activity = Signal(str, str)
    #: Emitted once when the operation ends: (success, message).
    finished = Signal(bool, str)
    #: Internal: marshals timer start/stop onto the reporter's own thread so
    #: begin()/finish() are safe to call from a worker thread.
    _timer_control = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._total_steps = 0
        self._current_step = 0
        self._start_time = 0.0
        self._committed = 0.0   # fraction of steps actually completed
        self._display = 0.0     # smoothly-animated fraction shown to the user
        self._last_sec = 0      # last whole second emitted for elapsed/remaining
        self._cancelled = False
        self._finished = False

        # Ticks several times a second so the bar creeps CONTINUOUSLY toward the
        # next step (instead of jumping on each step) and elapsed/remaining move
        # even while a single long step (e.g. a slow query) is in flight.
        self._tick_interval = 0.120  # seconds; kept in sync with the QTimer
        self._timer = QTimer(self)
        self._timer.setInterval(int(self._tick_interval * 1000))
        self._timer.timeout.connect(self._on_tick)
        self._timer_control.connect(self._apply_timer)

    def _apply_timer(self, running: bool) -> None:
        # Runs on the reporter's own thread (queued when emitted from a worker).
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
        if self._finished:
            return
        self._current_step = min(self._current_step + 1, self._total_steps)
        # Commit the completed fraction; the creep floor rises to match it.
        self._committed = self._current_step / self._total_steps
        if self._display < self._committed:
            self._display = self._committed
        if step_text:
            self.step_changed.emit(step_text)
        self.progress_changed.emit(min(int(self._display * 100), 99))
        elapsed = time.perf_counter() - self._start_time
        self._last_sec = int(elapsed)
        self.elapsed_changed.emit(self._last_sec)
        self.remaining_changed.emit(
            self._estimate_remaining(elapsed, self._committed)
        )

    def note(self, text: str) -> None:
        """Update the step/detail text WITHOUT advancing the step counter.

        Use for sub-stage messages and running counts (e.g. "priced 300/890
        items") that happen *within* one step - the bar keeps creeping smoothly
        while the text reflects live progress, instead of jumping a whole step.
        """
        if not self._finished and text:
            self.step_changed.emit(text)

    def finish(self, success: bool = True, message: str = "") -> None:
        """End the operation: force 100%, stop the timer, emit ``finished``."""
        if self._finished:
            return
        self._finished = True
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
        """Set the high-level subject (e.g. the family name)."""
        self.family_changed.emit(subject)

    def set_product(self, name: str) -> None:
        self.product_changed.emit(name)

    def set_counts(
        self,
        products: int,
        total_products: int,
        articles: int,
        properties: int,
        property_values: int,
        options: int,
        option_values: int,
        relations: int = 0,
    ) -> None:
        self.counts_changed.emit(
            products, total_products, articles, properties,
            property_values, options, option_values, relations,
        )

    def log(self, kind: str, message: str) -> None:
        """Emit a detailed activity line without advancing progress."""
        self.activity.emit(kind, message)

    def set_metrics(self, items) -> None:
        """Emit generic named metric tiles (key, label, target, suffix)."""
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
        if self._finished:
            return
        # Advance the displayed fraction smoothly. Motion is paced to how long
        # steps actually take (so it never rushes ahead), and it DECELERATES the
        # further it gets ahead of real committed progress - so a long step (e.g.
        # a slow query) keeps the bar visibly inching forward instead of pinning
        # at a boundary, while never reaching 100% before finish().
        now = time.perf_counter()
        span = 1.0 / self._total_steps
        # Cap the span used for pacing so operations with very few coarse steps
        # (a big span each) still creep gently instead of lurching forward.
        eff_span = min(span, 0.15)
        if self._current_step >= 1:
            avg_step = (now - self._start_time) / self._current_step
        else:
            # No step has completed yet: assume a few seconds, but let a long
            # first step stretch the estimate so the creep slows as it drags.
            avg_step = max(now - self._start_time, 3.0)
        avg_step = max(avg_step, 0.4)
        ceiling = 0.99
        if self._display < ceiling:
            # Cross one step-span per average step, damped by how far the creep
            # already leads the committed progress (span/(span+lead) -> slows the
            # further ahead it is), so it eases forward without stalling.
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
            self.remaining_changed.emit(
                self._estimate_remaining(elapsed, self._committed)
            )

    @staticmethod
    def _estimate_remaining(elapsed: float, fraction: float) -> int:
        if fraction <= 0.0:
            return 0
        total_estimate = elapsed / fraction
        return max(0, int(total_estimate - elapsed))
