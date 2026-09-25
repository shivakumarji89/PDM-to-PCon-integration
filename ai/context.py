"""Engineering context.

A read-only snapshot of the current engineering session, assembled entirely
from the existing services, snapshot and workflow manager. The assistant reads
this - it never computes engineering data itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.enums import WorkflowStep
from models.product import Product

# Canonical selectable collections: (key, label, workflow step, service attribute).
COLLECTIONS: tuple[tuple[str, str, WorkflowStep, str], ...] = (
    ("articles", "articles", WorkflowStep.ARTICLES, "article_service"),
    ("properties", "properties", WorkflowStep.PROPERTIES, "property_service"),
    ("property_values", "property values", WorkflowStep.VALUES, "property_value_service"),
    ("options", "options", WorkflowStep.OPTIONS, "option_service"),
    ("option_values", "option values", WorkflowStep.OPTION_VALUES, "option_value_service"),
)


@dataclass
class EngineeringContext:
    """Read-only view of the current engineering session."""

    product: Product | None
    current_step: WorkflowStep
    has_snapshot: bool
    counts: dict[str, int] = field(default_factory=dict)
    selected: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    missing_relationships: list[str] = field(default_factory=list)
    readiness: bool = False
    progress: tuple[int, int] = (0, 0)

    @property
    def product_label(self) -> str:
        if self.product is None:
            return "No product loaded"
        return f"{self.product.code} - {self.product.name}"


def build_context(app_context, manager) -> EngineeringContext:
    """Assemble an :class:`EngineeringContext` from existing services only."""
    snapshot = app_context.active_snapshot
    product = snapshot.product if snapshot else None

    counts: dict[str, int] = {}
    selected: dict[str, int] = {}
    for key, _label, _step, service_attr in COLLECTIONS:
        service = getattr(app_context, service_attr)
        counts[key] = len(service.items())
        selected[key] = service.selected_count()

    review = app_context.validation_service.review()

    return EngineeringContext(
        product=product,
        current_step=manager.current_step(),
        has_snapshot=snapshot is not None and product is not None,
        counts=counts,
        selected=selected,
        warnings=list(review.warnings),
        errors=list(review.errors),
        duplicates=list(review.duplicates),
        missing_relationships=list(review.missing_relationships),
        readiness=review.ready,
        progress=manager.progress(),
    )
