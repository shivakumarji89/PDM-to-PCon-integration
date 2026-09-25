"""Workflow session model.

Holds the workflow-level state of the current engineering session. It owns
workflow state only (navigation, progress, timing) and mirrors the active
product/snapshot for convenience - it does not own engineering data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from core.enums import WorkflowStep
from models.product import Product
from models.snapshot import Snapshot
from workflow.state import WorkflowState


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkflowSession:
    """Workflow-level session state (in memory only)."""

    product: Product | None = None
    snapshot: Snapshot | None = None
    current_step: WorkflowStep = WorkflowStep.PRODUCT
    completed_steps: set[WorkflowStep] = field(default_factory=set)
    enabled_steps: set[WorkflowStep] = field(default_factory=set)
    state: WorkflowState = WorkflowState.NOT_STARTED
    started_at: str = field(default_factory=_now)
    last_updated: str = field(default_factory=_now)

    def touch(self) -> None:
        """Record that the session state changed."""
        self.last_updated = _now()
