"""Project domain / session-state model.

Holds the runtime state of a working project: the selected product, its
snapshot, the current workflow step, and a modified flag. Fields only -
no logic in Phase 2.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.enums import WorkflowStep
from models.product import Product
from models.snapshot import Snapshot


@dataclass
class Project:
    """Runtime state for the active project."""

    name: str = ""
    selected_product: Product | None = None
    snapshot: Snapshot | None = None
    current_step: WorkflowStep = WorkflowStep.PRODUCT
    modified: bool = False
