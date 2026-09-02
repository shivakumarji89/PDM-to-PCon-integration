"""Workflow state definitions."""
from __future__ import annotations

from enum import Enum


class WorkflowState(Enum):
    """Lifecycle state of a workflow step or the overall session."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    READY = "ready"
    INVALID = "invalid"
