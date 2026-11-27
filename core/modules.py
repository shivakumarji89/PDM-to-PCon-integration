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

    # ARCHIVED: legacy Development module. Not offered in MODULE_ITEMS or
    # MODULE_WORKFLOWS. The member and the Development-specific branches in the
    # Articles / Class Creation pages are kept so it can be restored later.
    DEVELOPMENT = "development"
    # LEGACY INTERNAL IDENTITY of ProductStudio. The value "maintenance" is kept
    # because pages, snapshot/export rules and tests key off it. Prefer the
    # PRODUCT_STUDIO alias in new code.
    MAINTENANCE = "maintenance"
    PRODUCT_STUDIO = "maintenance"  # alias of MAINTENANCE (same member)
    QA_VALIDATION = "qa_validation"
    METATYPE = "metatype"
    OAP = "oap"
    BULK_UPDATE = "bulk_update"
    SYTELINE_EXPORT = "syteline_export"


@dataclass(frozen=True)
class ModuleItem:
    """Presentation metadata for a top-level module."""

    module: WorkbenchModule
    title: str
    description: str


MODULE_ITEMS: tuple[ModuleItem, ...] = (
    ModuleItem(
        WorkbenchModule.MAINTENANCE,
        "ProductStudio",
        "Product Development & Configuration",
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
    ModuleItem(
        WorkbenchModule.SYTELINE_EXPORT,
        "SyteLine Export",
        "Configure and run the legacy-compatible SyteLine data export.",
    ),
)


def is_active_module(module: WorkbenchModule | None) -> bool:
    """Return True if the module is offered in the active module launcher."""
    return any(item.module == module for item in MODULE_ITEMS)


def module_title(module: WorkbenchModule) -> str:
    """Return the display title for a module."""
    for item in MODULE_ITEMS:
        if item.module == module:
            return item.title
    return module.name.replace("_", " ").title()


def snapshot_source_for_module(module: WorkbenchModule | None) -> str:
    """Return the active data source required by each module's workflow."""
    if module in (WorkbenchModule.BULK_UPDATE, WorkbenchModule.QA_VALIDATION):
        return "mdb_import"
    return "pdm"


# Archived Development workflow definition. Keep this intact for reference and
# possible future reactivation, but do not route users into it from the active
# module selector. To restore Development: add a ModuleItem to MODULE_ITEMS and
# move this entry back into MODULE_WORKFLOWS.
ARCHIVED_MODULE_WORKFLOWS: dict[WorkbenchModule, tuple[WorkflowStep, ...]] = {
    WorkbenchModule.DEVELOPMENT: (
        WorkflowStep.PRODUCT,
        WorkflowStep.ARTICLES,
        WorkflowStep.CLASS_CREATION,
        WorkflowStep.TEXT,
        WorkflowStep.RELATION,
        WorkflowStep.PRICING,
        WorkflowStep.PRICING_RELATION,
        WorkflowStep.REVIEW,
    ),
}

# Workflows exposed after entering each module. Existing workflow/page
# implementations are reused; this mapping only controls which ones are shown.
# Engineering remains available to the application internally, but is not
# exposed as a user-facing workflow step for now.
MODULE_WORKFLOWS: dict[WorkbenchModule, tuple[WorkflowStep, ...]] = {
    # Maintenance keeps its existing workflow order.
    WorkbenchModule.MAINTENANCE: (
        WorkflowStep.PRODUCT,
        WorkflowStep.ARTICLES,
        WorkflowStep.CLASS_CREATION,
        WorkflowStep.TEXT,
        WorkflowStep.RELATION,
        WorkflowStep.PRICING,
        WorkflowStep.PRICING_RELATION,
        WorkflowStep.MAINTENANCE_COMPARISON,
    ),
    WorkbenchModule.BULK_UPDATE: (
        WorkflowStep.BULK_PRICE_UPDATE,
        WorkflowStep.BULK_VERSION_UPDATE,
        WorkflowStep.BULK_REPOSITORY_LINK,
    ),
    # QA owns the OCD-backed Article OBX generator and validation flow.
    WorkbenchModule.QA_VALIDATION: (
        WorkflowStep.PRODUCT,
        WorkflowStep.PCON_ARTICLE_OBX_GENERATOR,
        WorkflowStep.OBX_VALIDATION,
        WorkflowStep.CET_SIF_VALIDATION,
    ),
    # Metatype works on the HMX repository, not on a PDM product, so it has no Product step. The
    # repository-analysis page remains registered as a development diagnostic but is not part of the
    # runtime creation workflow.
    WorkbenchModule.METATYPE: (
        WorkflowStep.METATYPE_ARTICLES,
        WorkflowStep.METATYPE_PROPERTIES,
        WorkflowStep.METATYPE_VALUES,
        WorkflowStep.METATYPE_TEXTS,
        WorkflowStep.METATYPE_SETUP,
        WorkflowStep.METATYPE_RELATIONS,
        WorkflowStep.METATYPE_REVIEW,
    ),
    WorkbenchModule.OAP: (
        WorkflowStep.PRODUCT,
    ),
    WorkbenchModule.SYTELINE_EXPORT: (
        WorkflowStep.SYTELINE_EXPORT,
    ),
}


def module_workflows(module: WorkbenchModule) -> tuple[WorkflowStep, ...]:
    """Return the existing workflows exposed by a top-level module."""
    return MODULE_WORKFLOWS.get(module, ())
