"""Top-level module definitions for MK Product Workbench.

Modules are the product-level entry points above the individual workflow
steps. This layer intentionally contains metadata only; workflow selection and
module-specific rules are implemented separately.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.enums import WorkflowStep


class WorkbenchModule(Enum):
    """Top-level functional modules of the workbench."""

    DEVELOPMENT = "development"
    MAINTENANCE = "maintenance"
    QA_VALIDATION = "qa_validation"
    METATYPE = "metatype"
    OAP = "oap"
    BULK_UPDATE = "bulk_update"


@dataclass(frozen=True)
class ModuleItem:
    """Presentation metadata for a top-level module."""

    module: WorkbenchModule
    title: str
    description: str


MODULE_ITEMS: tuple[ModuleItem, ...] = (
    ModuleItem(
        WorkbenchModule.DEVELOPMENT,
        "Development",
        "Create and develop product engineering data.",
    ),
    ModuleItem(
        WorkbenchModule.MAINTENANCE,
        "Maintenance",
        "Maintain and update published product packages.",
    ),
    ModuleItem(
        WorkbenchModule.QA_VALIDATION,
        "QA Validation",
        "Validate product data and generated deliverables.",
    ),
    ModuleItem(
        WorkbenchModule.METATYPE,
        "Metatype",
        "Create and validate metatype definitions.",
    ),
    ModuleItem(
        WorkbenchModule.OAP,
        "OAP",
        "Create and validate OAP definitions and packages.",
    ),
    ModuleItem(
        WorkbenchModule.BULK_UPDATE,
        "Bulk Update",
        "Run bulk maintenance operations on published product packages.",
    ),
)


def module_title(module: WorkbenchModule) -> str:
    """Return the display title for a module."""
    for item in MODULE_ITEMS:
        if item.module == module:
            return item.title
    return module.name.replace("_", " ").title()


# Workflows exposed after entering each module. Existing workflow/page
# implementations are reused; this mapping only controls which ones are shown.
# Engineering remains available to the application internally, but is not
# exposed as a user-facing workflow step for now.
MODULE_WORKFLOWS: dict[WorkbenchModule, tuple[WorkflowStep, ...]] = {
    # Development: Class Creation comes before Articles because class-derived
    # article/base-position information is finalized there. Articles is then
    # revisited to apply/review the resulting position.
    WorkbenchModule.DEVELOPMENT: (
        WorkflowStep.PRODUCT,
        WorkflowStep.CLASS_CREATION,
        WorkflowStep.ARTICLES,
        WorkflowStep.TEXT,
        WorkflowStep.RELATION,
        WorkflowStep.PRICING,
        WorkflowStep.PRICING_RELATION,
        WorkflowStep.REVIEW,
    ),
    # Maintenance keeps its existing workflow order.
    WorkbenchModule.MAINTENANCE: (
        WorkflowStep.PRODUCT,
        WorkflowStep.ARTICLES,
        WorkflowStep.CLASS_CREATION,
        WorkflowStep.TEXT,
        WorkflowStep.RELATION,
        WorkflowStep.PRICING,
        WorkflowStep.PRICING_RELATION,
        WorkflowStep.REVIEW,
    ),
    WorkbenchModule.BULK_UPDATE: (
        WorkflowStep.MAINTENANCE,
    ),
    WorkbenchModule.QA_VALIDATION: (
        WorkflowStep.PRODUCT,
        WorkflowStep.CET_SIF_VALIDATION,
        WorkflowStep.OBX_VALIDATION,
    ),
    WorkbenchModule.METATYPE: (
        WorkflowStep.PRODUCT,
    ),
    WorkbenchModule.OAP: (
        WorkflowStep.PRODUCT,
    ),
}


def module_workflows(module: WorkbenchModule) -> tuple[WorkflowStep, ...]:
    """Return the existing workflows exposed by a top-level module."""
    return MODULE_WORKFLOWS.get(module, ())
