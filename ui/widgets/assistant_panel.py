"""AI Engineering Assistant panel (dockable).

A presentation panel that hosts the :class:`~ai.assistant.EngineeringAssistant`.
It focuses on engineering awareness and guidance through three sections:
Session ("where am I?"), Engineering Activity (an intelligent timeline that
merges what happened with the recommended next step) and Conversation. It owns
no engineering logic and duplicates no application commands - navigation lives
in the Workflow Navigator and per-workspace commands in their own toolbars.
"""
from __future__ import annotations

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ai.actions import ActionType
from ai.assistant import EngineeringAssistant
from ui import theme
from workflow.state import WorkflowState

_STATE_TEXT = {
    WorkflowState.NOT_STARTED: "Not started",
    WorkflowState.IN_PROGRESS: "In progress",
    WorkflowState.COMPLETED: "Completed",
    WorkflowState.BLOCKED: "Blocked",
    WorkflowState.READY: "Ready",
    WorkflowState.INVALID: "Invalid",
}


class AssistantPanel(QWidget):
    """Dockable AI assistant UI bound to the workflow manager and services."""

    def __init__(self, app_context, manager, pages: dict, refresh_callback,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("assistantPanel")
        self._app_context = app_context
        self._manager = manager
        self._pages = pages
        self._refresh = refresh_callback
        self._assistant = EngineeringAssistant(app_context, manager)
        self._activity_signature = None

        layout = QVBoxLayout(self)
        # No left inset so the inner blocks run to the panel's left edge (toward
        # the center panel); other sides keep the standard inset.
        layout.setContentsMargins(
            0, theme.PANEL_INSET,
            theme.PANEL_INSET, theme.PANEL_INSET,
        )
        layout.setSpacing(theme.SECTION_SPACING)

        self._title = QLabel("Engineering Assistant", self)
        self._title.setObjectName("assistantTitle")
        layout.addWidget(self._title)
        layout.addWidget(self._build_status_group())
        layout.addWidget(self._build_activity_group(), 1)
        layout.addWidget(self._build_conversation_group(), 1)
        layout.addWidget(self._build_input_row())

        manager.state_changed.connect(self._refresh_view)
        self._refresh_view()

    # -- construction ------------------------------------------------------
    def _build_status_group(self) -> QWidget:
        box = QGroupBox("Session", self)
        form = QFormLayout(box)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(4)
        self._s_product = QLabel("-", box)
        self._s_step = QLabel("-", box)
        self._s_snapshot = QLabel("-", box)
        self._s_connection = QLabel("-", box)
        self._s_state = QLabel("-", box)
        self._s_product.setWordWrap(True)
        form.addRow("Product:", self._s_product)
        form.addRow("Current Step:", self._s_step)
        form.addRow("Snapshot:", self._s_snapshot)
        form.addRow("Connection:", self._s_connection)
        form.addRow("Engineering State:", self._s_state)
        return box

    def _build_activity_group(self) -> QWidget:
        box = QGroupBox("Engineering Activity", self)
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        self._activity = QListWidget(box)
        self._activity.setObjectName("assistantActivity")
        self._activity.setWordWrap(True)
        v.addWidget(self._activity)
        return box

    def _build_conversation_group(self) -> QWidget:
        box = QGroupBox("Conversation", self)
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        self._conversation = QTextEdit(box)
        self._conversation.setReadOnly(True)
        v.addWidget(self._conversation)
        return box

    def _build_input_row(self) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        self._input = QLineEdit(row)
        self._input.setPlaceholderText("Ask or command (e.g. 'find oak options')...")
        self._input.returnPressed.connect(self._on_send)
        layout.addWidget(self._input, 1)
        send = QPushButton("Send", row)
        send.setDefault(True)
        send.clicked.connect(self._on_send)
        layout.addWidget(send)
        return row

    # -- interaction -------------------------------------------------------
    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._submit(text)

    def _submit(self, text: str) -> None:
        self._append("You", text)
        response = self._assistant.handle(text)
        self._append("Assistant", response.message)

        action = response.action
        if action.type == ActionType.SEARCH and action.step is not None:
            self._manager.jump_to(action.step)
            page = self._pages.get(action.step)
            if page is not None and hasattr(page, "_search"):
                page._search.setText(action.query)

        if action.requires_ui:
            self._refresh()
        self._refresh_view()

    def _append(self, who: str, text: str) -> None:
        self._conversation.append(f"<b>{who}:</b> {text}".replace("\n", "<br>"))

    # -- view refresh ------------------------------------------------------
    def _refresh_view(self) -> None:
        context = self._assistant.context()
        self._s_product.setText(context.product_label)
        self._s_step.setText(self._manager.title(context.current_step))
        self._s_snapshot.setText("Loaded" if context.has_snapshot else "Empty")
        self._s_connection.setText(
            "Connected"
            if self._app_context.pdm_service.is_connected()
            else "Disconnected"
        )
        self._s_state.setText(_STATE_TEXT.get(self._manager.session.state, "-"))

        self._log_engineering_activity(context)

    # -- engineering activity timeline ------------------------------------
    def _log_engineering_activity(self, context) -> None:
        """Append an intelligent activity entry when the engineering situation
        changes: what happened, any validation events, and the next step.
        Recommendations are merged here rather than shown separately."""
        recommended = self._manager.recommended_action()
        signature = (
            context.current_step,
            context.has_snapshot,
            context.readiness,
            len(context.warnings),
            len(context.errors),
            recommended,
        )
        if signature == self._activity_signature:
            return
        self._activity_signature = signature

        # What happened.
        if not context.has_snapshot:
            self._add_activity("not_started", "No engineering session loaded")
        else:
            self._add_activity(
                "completed",
                f"{context.product_label} \u00b7 "
                f"{self._manager.title(context.current_step)}",
            )
        # Important events / validation.
        if context.errors:
            self._add_activity("error", f"{len(context.errors)} error(s) detected")
        elif context.warnings:
            self._add_activity(
                "warning", f"{len(context.warnings)} warning(s) detected"
            )
        elif context.has_snapshot and context.readiness:
            self._add_activity("success", "Engineering data ready")
        # What should I do next.
        if recommended:
            self._add_activity("next", f"Next: {recommended}")
        self._activity.scrollToBottom()

    def _add_activity(self, kind: str, message: str) -> None:
        if kind == "next":
            glyph, color = "\u2192", theme.ACCENT
        else:
            style = theme.status_style(kind)
            glyph, color = style.glyph, style.color
        item = QListWidgetItem(f"{glyph}  {message}")
        item.setForeground(QBrush(QColor(color)))
        self._activity.addItem(item)
        while self._activity.count() > 200:
            self._activity.takeItem(0)

    # -- external activity feed -------------------------------------------
    def log_activity(self, kind: str, message: str) -> None:
        """Append a detailed activity line from an external operation.

        This is the public entry point used by long-running operations (e.g.
        Load Family) so their :class:`~core.progress.ProgressReporter` activity
        events land in the same Engineering Activity timeline.
        """
        self._add_activity(kind, message)
        self._activity.scrollToBottom()
