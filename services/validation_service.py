"""Validation service.

Produces a combined, read-only engineering review of the active snapshot by
aggregating the per-area validations (articles, properties, property values,
options, option values). Performs no SQL and no mutations.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from services.base_service import BaseService


@dataclass
class EngineeringReview:
    """Aggregate engineering review of the active snapshot."""

    counts: dict[str, int] = field(default_factory=dict)
    selected_counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    missing_relationships: list[str] = field(default_factory=list)
    ready: bool = False


class ValidationService(BaseService):
    """Aggregates per-area validations into a single engineering review."""

    def review(self) -> EngineeringReview:
        ctx = self.context
        snapshot = ctx.active_snapshot
        review = EngineeringReview()

        if snapshot is None or snapshot.product is None:
            review.errors.append("No product loaded.")
            return review

        articles = ctx.article_service.validate()
        properties = ctx.property_service.validate()
        property_values = ctx.property_value_service.validate()
        options = ctx.option_service.validate()
        option_values = ctx.option_value_service.validate()

        review.counts = {
            "Articles": articles.total,
            "Properties": properties.total,
            "Property Values": property_values.total,
            "Options": options.total,
            "Option Values": option_values.total,
        }
        review.selected_counts = {
            "Articles": articles.selected,
            "Properties": properties.selected,
            "Property Values": property_values.selected,
            "Options": options.selected,
            "Option Values": option_values.selected,
        }

        # Warnings aggregated per area.
        for label, result in (
            ("Articles", articles), ("Properties", properties),
            ("Property Values", property_values), ("Options", options),
            ("Option Values", option_values),
        ):
            for warning in result.warnings:
                review.warnings.append(f"{label}: {warning}")

        # Duplicates.
        if articles.duplicate_codes:
            review.duplicates.append(
                f"Articles: {len(articles.duplicate_codes)} duplicate code(s)"
            )
        if properties.duplicate_names:
            review.duplicates.append(
                f"Properties: {len(properties.duplicate_names)} duplicate name(s)"
            )
        if property_values.duplicate_groups:
            review.duplicates.append(
                f"Property Values: {len(property_values.duplicate_groups)} duplicate group(s)"
            )
        if options.duplicate_names:
            review.duplicates.append(
                f"Options: {len(options.duplicate_names)} duplicate name(s)"
            )
        if option_values.duplicate_groups:
            review.duplicates.append(
                f"Option Values: {len(option_values.duplicate_groups)} duplicate group(s)"
            )

        # Missing relationships (orphan values).
        if property_values.orphan_values:
            review.missing_relationships.append(
                f"{property_values.orphan_values} property value(s) with no owning property"
            )
        if option_values.orphan_values:
            review.missing_relationships.append(
                f"{option_values.orphan_values} option value(s) with no owning option"
            )

        # Errors: nothing engineering-usable loaded.
        if properties.total == 0 and options.total == 0:
            review.errors.append("No properties or options loaded.")

        # Block generation while any configuration attribute still has no code
        # the automation could assign - one property's code depends on others.
        unresolved = ctx.engineering_class_service.unresolved_config_codes(snapshot)
        if unresolved:
            review.errors.append(
                f"{len(unresolved)} configuration attribute(s) need a manual "
                "code before generation."
            )

        review.ready = not review.errors and not review.missing_relationships
        return review

