"""Workflow definition for the MK Product Workbench.

Defines the ordered set of workflow steps used by the navigator and the
center workspace stack. This is pure metadata - no business logic.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.enums import WorkflowStep


@dataclass(frozen=True)
class WorkflowItem:
    """Presentation metadata for a single workflow step."""

    step: WorkflowStep
    title: str
    description: str


# Ordered list that drives both the navigator and the page stack.
WORKFLOW_ITEMS: tuple[WorkflowItem, ...] = (
    WorkflowItem(WorkflowStep.PRODUCT, "Product", "Select and review the active product."),
    WorkflowItem(WorkflowStep.ARTICLES, "Articles", "Manage articles for the product."),
    WorkflowItem(WorkflowStep.CLASS_CREATION, "Class Creation",
                 "Assign order-code letters, select values, and create visual/misc properties."),
    WorkflowItem(WorkflowStep.TEXT, "Text",
                 "Author localized text blocks for articles, properties and values."),
    WorkflowItem(WorkflowStep.RELATION, "Relation Object",
                 "Author configuration relations (preconditions and code actions)."),
    WorkflowItem(WorkflowStep.PRICING, "Pricing",
                 "Compute PDM-accurate OCD prices and review year-over-year changes."),
    WorkflowItem(WorkflowStep.PRICING_RELATION, "Pricing Relation",
                 "Generate the PA_PRICING relation that merges config to price varconds."),
    WorkflowItem(WorkflowStep.REVIEW, "Review", "Review the assembled configuration."),
    WorkflowItem(WorkflowStep.ENGINEERING, "Engineering", "Read-only view of the engineering hierarchy."),
    WorkflowItem(WorkflowStep.MAINTENANCE, "Maintenance",
                 "Annual maintenance on a published package: price-list roll-over (fabric later)."),
)

# --- CET SIF Validation (self-contained, easily disconnectable) -------------
# Set False (or delete this block) to fully disconnect the CET SIF Validation
# workflow: its navigator entry, page and step all disappear with no other
# change needed elsewhere.
CET_SIF_VALIDATION_ENABLED = True

if CET_SIF_VALIDATION_ENABLED:
    WORKFLOW_ITEMS = WORKFLOW_ITEMS + (
        WorkflowItem(WorkflowStep.CET_SIF_VALIDATION, "CET SIF Validation",
                     "Validate CET-generated SIF files (standalone tool)."),
        WorkflowItem(WorkflowStep.OBX_VALIDATION, "OBX Validation",
                     "Validate OBX files against PDM (standalone tool)."),
    )
