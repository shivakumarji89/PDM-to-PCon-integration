"""Workflow manager.

Owns navigation rules and drives the workflow session. It never performs
engineering validation itself - readiness is always obtained from the hosted
workspaces (which delegate to the existing services). It reacts to snapshot
changes to keep progress, step readiness and session status up to date.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from core.enums import WorkflowStep
from core.workflow import WORKFLOW_ITEMS
from workflow.host import WorkspaceHost
from workflow.session import WorkflowSession
from workflow.state import WorkflowState

_TITLES = {item.step: item.title for item in WORKFLOW_ITEMS}


class WorkflowManager(QObject):
    """Coordinates workflow navigation and session state."""

    #: Emitted whenever workflow state (progress/readiness/status) changes.
    state_changed = Signal()
    #: Emitted with the new current :class:`WorkflowStep` after navigation.
    step_changed = Signal(object)

    def __init__(self, context, host: WorkspaceHost, steps: list[WorkflowStep]) -> None:
        super().__init__()
        self._context = context
        self._host = host
        self._steps = list(steps)
        self._session = WorkflowSession(current_step=self._steps[0])
        self._last_product_id: str | None = None
        self.refresh()

    # -- accessors ---------------------------------------------------------
    @property
    def session(self) -> WorkflowSession:
        return self._session

    def steps(self) -> list[WorkflowStep]:
        return list(self._steps)

    def current_step(self) -> WorkflowStep:
        return self._session.current_step

    @staticmethod
    def title(step: WorkflowStep) -> str:
        return _TITLES.get(step, step.name.title())

    def _index(self, step: WorkflowStep) -> int:
        return self._steps.index(step)

    def _product_loaded(self) -> bool:
        snapshot = self._context.active_snapshot
        return snapshot is not None and snapshot.product is not None

    def is_ready(self, step: WorkflowStep) -> bool:
        return self._host.is_ready(step)

    # -- navigation rules --------------------------------------------------
    def enabled_steps(self) -> set[WorkflowStep]:
        # Steps that work on the published-package repository (not the loaded
        # product) stay reachable; the rest unlock once a product is loaded.
        standalone = {WorkflowStep.MAINTENANCE, WorkflowStep.CET_SIF_VALIDATION}
        always = {self._steps[0]} | (standalone & set(self._steps))
        if self._product_loaded():
            return set(self._steps)
        return always

    def can_continue(self) -> bool:
        index = self._index(self.current_step())
        return index < len(self._steps) - 1 and self.is_ready(self.current_step())

    def can_go_back(self) -> bool:
        return self._index(self.current_step()) > 0

    def can_jump(self, step: WorkflowStep) -> bool:
        return step in self.enabled_steps()

    def next(self) -> bool:
        if not self.can_continue():
            return False
        self.complete_step()
        self._set_current(self._steps[self._index(self.current_step()) + 1])
        return True

    def back(self) -> bool:
        if not self.can_go_back():
            return False
        self._set_current(self._steps[self._index(self.current_step()) - 1])
        return True

    def jump_to(self, step: WorkflowStep) -> bool:
        if not self.can_jump(step):
            return False
        self._set_current(step)
        return True

    def complete_step(self, step: WorkflowStep | None = None) -> None:
        self._session.completed_steps.add(step or self.current_step())

    def reset(self) -> None:
        first = self._steps[0]
        self._session = WorkflowSession(current_step=first)
        self._set_current(first)

    # -- state -------------------------------------------------------------
    def step_state(self, step: WorkflowStep) -> WorkflowState:
        # Completion is derived from readiness, not from how the step was
        # reached, so left-panel jumps and Continue produce identical ticks.
        if step not in self.enabled_steps():
            return WorkflowState.BLOCKED
        if self.is_ready(step):
            return WorkflowState.COMPLETED
        if step == self.current_step():
            return WorkflowState.IN_PROGRESS
        return WorkflowState.NOT_STARTED

    def progress(self) -> tuple[int, int]:
        """Return (completed_count, total_steps)."""
        completed = sum(1 for step in self._steps if self.is_ready(step))
        return completed, len(self._steps)

    def recommended_action(self) -> str:
        if not self._product_loaded():
            return "Load a product on the Product page to begin."
        current = self.current_step()
        if not self.is_ready(current):
            return f"Complete the {self.title(current)} step before continuing."
        index = self._index(current)
        if index < len(self._steps) - 1:
            return f"Continue to {self.title(self._steps[index + 1])}."
        return "All steps ready - you can generate output."

    # -- lifecycle ---------------------------------------------------------
    def _set_current(self, step: WorkflowStep) -> None:
        self._session.current_step = step
        self._host.activate(step)
        self.step_changed.emit(step)
        self.refresh()

    def refresh(self) -> None:
        """Recompute session state from the snapshot and notify listeners."""
        snapshot = self._context.active_snapshot
        product = snapshot.product if snapshot else None
        product_id = product.id if product else None

        # A new (or cleared) product starts a fresh workflow.
        if product_id != self._last_product_id:
            self._session.completed_steps.clear()
            self._last_product_id = product_id

        self._session.product = product
        self._session.snapshot = snapshot
        self._session.enabled_steps = self.enabled_steps()
        self._session.state = self._compute_session_state()
        self._session.touch()
        self.state_changed.emit()

    def _compute_session_state(self) -> WorkflowState:
        if not self._product_loaded():
            return WorkflowState.NOT_STARTED
        if all(self.is_ready(step) for step in self._steps):
            return WorkflowState.COMPLETED
        return WorkflowState.IN_PROGRESS
