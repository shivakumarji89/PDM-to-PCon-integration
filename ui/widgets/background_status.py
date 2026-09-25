"""Reusable background status indicator.

A single, clickable status-bar label that surfaces the *current background
activity* (title / stage and percentage) and lets the user reopen the progress
monitor. It is intentionally generic: it observes the shared
:class:`~core.activity.service.ActivityService` through the application
:class:`~core.events.EventBus`, so it reflects **any** background task that
publishes an :class:`~core.activity.events.ActivityEvent` - today's Load Family
and any future long-running work - without those tasks knowing about the status
bar.

It never touches loading, the repository, snapshots or engineering logic; it
only reads immutable :class:`~core.activity.models.ActivitySnapshot` values and
renders one line of text.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QLabel, QWidget

from core.activity.events import ActivityEvent
from core.activity.models import ActivityStatus


class BackgroundStatusIndicator(QLabel):
    """Clickable status-bar label showing the current background activity.

    Driven by the shared :class:`ActivityService` via the event bus:

      * while an activity is active - ``Background: <stage>... NN%``
      * on successful completion   - ``Snapshot Ready`` (briefly, then hidden)
      * when nothing is active      - hidden

    Emits :attr:`clicked` when pressed so the host can reopen the progress
    monitor. Reusable: future background tasks appear here automatically.
    """

    #: Emitted when the label is clicked (host reopens the progress monitor).
    clicked = Signal()

    #: How long the terminal message lingers before the label hides (ms).
    _HIDE_DELAY_MS = 4000

    def __init__(self, activity_service, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("backgroundStatus")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setVisible(False)

        self._service = activity_service
        self._tracked_id: str | None = None

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide)

        # Observe every activity event (delivered on the bus/UI thread).
        self._service.event_bus.subscribe(self._on_event, ActivityEvent)

        # Reflect any activity already running when this indicator is created.
        for snapshot in self._service.active_snapshots():
            self._apply(snapshot)

    # -- interaction -------------------------------------------------------
    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    # -- event handling ----------------------------------------------------
    def _on_event(self, event: ActivityEvent) -> None:
        self._apply(event.snapshot)

    def _apply(self, snapshot) -> None:
        if snapshot.is_active:
            self._tracked_id = snapshot.id
            self._hide_timer.stop()
            self.setText(self._active_text(snapshot))
            self.setVisible(True)
            return

        # Terminal event: only react to the activity we are currently showing.
        if snapshot.id != self._tracked_id:
            return

        # If other background work is still running, switch to the latest one.
        remaining = self._service.active_snapshots()
        if remaining:
            nxt = remaining[-1]
            self._tracked_id = nxt.id
            self.setText(self._active_text(nxt))
            self.setVisible(True)
            return

        # Nothing else active: show the terminal message briefly, then hide.
        self._tracked_id = None
        self.setText(self._terminal_text(snapshot))
        self.setVisible(True)
        self._hide_timer.start(self._HIDE_DELAY_MS)

    def _hide(self) -> None:
        if self._tracked_id is None:
            self.setVisible(False)

    # -- text formatting ---------------------------------------------------
    def _active_text(self, snapshot) -> str:
        label = snapshot.stage_name or snapshot.current_step or snapshot.title
        percent = snapshot.progress_percent
        if percent is None:
            return f"Background: {label}..."
        return f"Background: {label}... {int(round(percent))}%"

    def _terminal_text(self, snapshot) -> str:
        if snapshot.status is ActivityStatus.COMPLETED:
            return "Snapshot Ready" if self._is_load(snapshot) else "Ready"
        if snapshot.status is ActivityStatus.FAILED:
            return "Background task failed"
        return "Background task cancelled"

    @staticmethod
    def _is_load(snapshot) -> bool:
        value = getattr(snapshot.type, "value", snapshot.type)
        return str(value).lower() == "load"
