"""Reusable operation card widget.

An :class:`OperationCard` renders the state of a single operation from an
immutable :class:`~core.activity.models.ActivitySnapshot`. It is deliberately
self-contained and reusable: it depends only on the snapshot type and the shared
theme, never on :class:`~ui.widgets.activity_panel.ActivityPanel`, so any view
can display operations by creating cards and feeding them snapshots.

The only update entry point is :meth:`OperationCard.update` - callers pass the
latest snapshot and the card refreshes itself. Callers never manipulate the
card's internal labels or progress bar directly.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.activity.models import ActivitySnapshot, ActivityStatus, LogLevel
from ui import theme

# Map an activity status to the shared status vocabulary (colour + glyph).
_STATUS_KIND = {
    ActivityStatus.PENDING: "not_started",
    ActivityStatus.RUNNING: "current",
    ActivityStatus.COMPLETED: "completed",
    ActivityStatus.FAILED: "error",
    ActivityStatus.CANCELLED: "blocked",
}

# Map a log level to the shared status vocabulary for colouring log lines.
_LOG_KIND = {
    LogLevel.INFO: "information",
    LogLevel.SUCCESS: "success",
    LogLevel.WARNING: "warning",
    LogLevel.ERROR: "error",
}


class OperationCard(QFrame):
    """A compact, self-updating card for one operation (activity)."""

    #: Reserved for future action buttons (e.g. Cancel). Carries the activity id.
    cancel_requested = Signal(str)

    def __init__(self, snapshot: ActivitySnapshot, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("operationCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._activity_id = snapshot.id
        self._log_count = 0

        self._build_ui()
        self.update(snapshot)

    # -- identity ----------------------------------------------------------
    @property
    def activity_id(self) -> str:
        return self._activity_id

    # -- construction ------------------------------------------------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(6)

        outer.addWidget(self._build_header())

        self._progress = QProgressBar(self)
        self._progress.setObjectName("operationProgress")
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(10)
        outer.addWidget(self._progress)

        outer.addWidget(self._build_info())
        outer.addWidget(self._build_details())

    def _build_header(self) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._icon = QLabel(row)
        self._icon.setObjectName("operationIcon")
        layout.addWidget(self._icon)

        self._title = QLabel("-", row)
        self._title.setObjectName("operationTitle")
        font = self._title.font()
        font.setBold(True)
        self._title.setFont(font)
        layout.addWidget(self._title, 1)

        self._status = QLabel("-", row)
        self._status.setObjectName("operationStatus")
        layout.addWidget(self._status)

        self._percent = QLabel("", row)
        self._percent.setObjectName("operationPercent")
        layout.addWidget(self._percent)

        self._duration = QLabel("00:00", row)
        self._duration.setObjectName("operationDuration")
        layout.addWidget(self._duration)

        self._toggle = QToolButton(row)
        self._toggle.setObjectName("operationToggle")
        self._toggle.setCheckable(True)
        self._toggle.setArrowType(Qt.ArrowType.RightArrow)
        self._toggle.setAutoRaise(True)
        self._toggle.toggled.connect(self._on_toggle_details)
        layout.addWidget(self._toggle)

        return row

    def _build_info(self) -> QWidget:
        box = QWidget(self)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._stage = QLabel("", box)
        self._stage.setObjectName("operationStage")
        self._step = QLabel("", box)
        self._step.setObjectName("operationStep")
        self._step.setWordWrap(True)
        self._context = QLabel("", box)
        self._context.setObjectName("operationContext")
        self._context.setWordWrap(True)

        layout.addWidget(self._stage)
        layout.addWidget(self._step)
        layout.addWidget(self._context)
        return box

    def _build_details(self) -> QWidget:
        self._details = QWidget(self)
        self._details.setObjectName("operationDetails")
        layout = QVBoxLayout(self._details)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(4)

        self._log = QListWidget(self._details)
        self._log.setObjectName("operationLog")
        self._log.setWordWrap(True)
        self._log.setMaximumHeight(160)
        layout.addWidget(self._log)

        # Reserved row for future action buttons (Cancel, Retry, ...). Empty for
        # now; kept so future actions can be added without layout changes.
        self._actions = QWidget(self._details)
        self._actions.setObjectName("operationActions")
        actions_layout = QHBoxLayout(self._actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(6)
        actions_layout.addStretch(1)
        layout.addWidget(self._actions)

        self._details.setVisible(False)
        return self._details

    # -- the single update entry point ------------------------------------
    def update(self, snapshot: ActivitySnapshot) -> None:  # noqa: A003 (Qt-style API)
        """Refresh the whole card from ``snapshot`` (the only public update)."""
        self._activity_id = snapshot.id
        self._apply_header(snapshot)
        self._apply_progress(snapshot)
        self._apply_info(snapshot)
        self._apply_log(snapshot)

    # -- rendering helpers -------------------------------------------------
    def _apply_header(self, snapshot: ActivitySnapshot) -> None:
        style = theme.status_style(_STATUS_KIND.get(snapshot.status, "information"))
        self._icon.setText(style.glyph)
        self._icon.setStyleSheet(f"color: {style.color};")
        self._title.setText(snapshot.title or "-")
        self._status.setText(snapshot.status.value.capitalize())
        self._status.setStyleSheet(f"color: {style.color};")
        self._percent.setText(self._percent_text(snapshot))
        self._duration.setText(self._format_time(snapshot.duration_seconds))

    def _apply_progress(self, snapshot: ActivitySnapshot) -> None:
        percent = snapshot.progress_percent
        if snapshot.is_finished:
            self._progress.setRange(0, 100)
            self._progress.setValue(
                100 if snapshot.status is ActivityStatus.COMPLETED
                else int(percent or 0)
            )
        elif snapshot.is_determinate and percent is not None:
            self._progress.setRange(0, 100)
            self._progress.setValue(int(percent))
        else:
            # Indeterminate: a busy bar (Qt shows a moving indicator).
            self._progress.setRange(0, 0)

    def _apply_info(self, snapshot: ActivitySnapshot) -> None:
        stage = self._stage_text(snapshot)
        self._stage.setText(stage)
        self._stage.setVisible(bool(stage))

        step = snapshot.current_step
        if snapshot.current_item:
            step = f"{step} - {snapshot.current_item}" if step else snapshot.current_item
        self._step.setText(step)
        self._step.setVisible(bool(step))

        context = " \u00b7 ".join(f"{k}={v}" for k, v in snapshot.context.items())
        self._context.setText(context)
        self._context.setVisible(bool(context))

    def _apply_log(self, snapshot: ActivitySnapshot) -> None:
        total = len(snapshot.log)
        if total < self._log_count:
            # Log shrank (e.g. reused id) - rebuild from scratch.
            self._log.clear()
            self._log_count = 0
        for entry in snapshot.log[self._log_count:]:
            kind = _LOG_KIND.get(entry.level, "information")
            style = theme.status_style(kind)
            item = QListWidgetItem(f"{style.glyph}  {entry.message}")
            item.setForeground(QBrush(QColor(style.color)))
            self._log.addItem(item)
        if total > self._log_count:
            self._log_count = total
            self._log.scrollToBottom()

    # -- interaction -------------------------------------------------------
    def _on_toggle_details(self, expanded: bool) -> None:
        self._toggle.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self._details.setVisible(expanded)

    # -- formatting --------------------------------------------------------
    @staticmethod
    def _percent_text(snapshot: ActivitySnapshot) -> str:
        if snapshot.status is ActivityStatus.COMPLETED:
            return "100%"
        if snapshot.progress_percent is not None:
            return f"{snapshot.progress_percent:.0f}%"
        return ""

    @staticmethod
    def _stage_text(snapshot: ActivitySnapshot) -> str:
        if snapshot.total_stages > 0:
            label = f"Stage {snapshot.stage_index}/{snapshot.total_stages}"
            return f"{label}: {snapshot.stage_name}" if snapshot.stage_name else label
        return snapshot.stage_name

    @staticmethod
    def _format_time(seconds: float) -> str:
        seconds = max(0, int(seconds))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"
