"""Left panel workflow navigator.

A manager-driven navigator: it renders the workflow steps with their current
state (completed / current / ready / blocked), shows overall progress, and
provides Continue / Back navigation. All state is obtained from the
:class:`~workflow.manager.WorkflowManager`; the navigator holds none of its
own workflow state.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QFont
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.workflow import WORKFLOW_ITEMS, WorkflowStep
from ui import theme
from workflow.state import WorkflowState

# Map workflow states onto the shared design-system status vocabulary so the
# navigator uses the same colours, glyphs and wording as the rest of the app.
_STATE_STATUS = {
    WorkflowState.COMPLETED: "completed",
    WorkflowState.IN_PROGRESS: "current",
    WorkflowState.READY: "ready",
    WorkflowState.BLOCKED: "blocked",
    WorkflowState.NOT_STARTED: "not_started",
    WorkflowState.INVALID: "invalid",
}


class WorkflowNavigator(QWidget):
    """Left-panel workflow navigator driven by the WorkflowManager."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("workflowNavigator")
        self._manager = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QLabel("Workflow", self)
        header.setObjectName("panelHeader")
        layout.addWidget(header)

        self._list = QListWidget(self)
        self._list.setObjectName("workflowList")
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        # Show every workflow step at once: the list never scrolls, it grows to
        # fit its rows and the surrounding panel absorbs any spare space.
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setUniformItemSizes(True)
        self._list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        for item in WORKFLOW_ITEMS:
            list_item = QListWidgetItem(item.title, self._list)
            list_item.setData(Qt.ItemDataRole.UserRole, item.step)
            list_item.setToolTip(item.description)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._fit_list_height()
        layout.addWidget(self._list)
        layout.addStretch(1)

        self._progress = QLabel("", self)
        self._progress.setObjectName("pageSubtitle")
        self._progress.setWordWrap(True)
        layout.addWidget(self._progress)

    def _fit_list_height(self) -> None:
        """Size the list to show all rows so it never needs a scrollbar."""
        total = 2 * self._list.frameWidth()
        for row in range(self._list.count()):
            total += self._list.sizeHintForRow(row)
        self._list.setFixedHeight(total)

    def set_manager(self, manager) -> None:
        self._manager = manager
        manager.state_changed.connect(self._render)
        self._render()

    # -- user actions ------------------------------------------------------
    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        if self._manager is None:
            return
        step = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(step, WorkflowStep):
            self._manager.jump_to(step)

    # -- rendering ---------------------------------------------------------
    def _render(self) -> None:
        if self._manager is None:
            return
        current = self._manager.current_step()
        for row in range(self._list.count()):
            item = self._list.item(row)
            step = item.data(Qt.ItemDataRole.UserRole)
            state = self._manager.step_state(step)

            status = theme.status_style(_STATE_STATUS[state])
            item.setText(f"{status.glyph}   {self._title(step)}")
            item.setToolTip(f"{self._title(step)} \u2014 {status.label}")
            item.setForeground(QBrush(theme.status_color(_STATE_STATUS[state])))
            font = QFont(item.font())
            font.setBold(step == current)
            item.setFont(font)

            flags = Qt.ItemFlag.ItemIsSelectable
            if state != WorkflowState.BLOCKED:
                flags |= Qt.ItemFlag.ItemIsEnabled
            item.setFlags(flags)

            if step == current:
                self._list.setCurrentRow(row)

        completed, total = self._manager.progress()
        index = self._manager.steps().index(current) + 1
        self._progress.setText(
            f"Progress: {completed}/{total} completed\n"
            f"Step {index} of {total}: {self._title(current)}"
        )
        # Re-fit after styling/glyphs are applied so all rows stay visible.
        self._fit_list_height()

    @staticmethod
    def _title(step: WorkflowStep) -> str:
        for item in WORKFLOW_ITEMS:
            if item.step == step:
                return item.title
        return step.name.title()
