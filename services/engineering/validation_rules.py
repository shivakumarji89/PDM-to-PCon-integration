"""Concrete Engineering validation rules.

Pluggable :class:`~services.engineering.engineering_validation_service.
ValidationRule` implementations that operate on a single reduction group. Each
rule is stateless and read-only: it inspects the group's members and their
property assignments and returns zero or more validation messages. A rule never
mutates the group, Engineering, or assignments, and never raises for a business
validation failure.

Only rules that are meaningful with the current Engineering model are provided.
A rule receives only a reduction group (its members and their assignments); it
cannot reach property definitions, and the model has no "required", allowed-
value, or type metadata - so "missing required property" and "invalid value"
rules are intentionally omitted until the model supports them.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from services.engineering.engineering_validation_service import (
    Severity,
    ValidationMessage,
    ValidationRule,
)

if TYPE_CHECKING:
    from services.engineering.engineering_reduction_service import ReductionGroup


class EmptyPropertyValueRule(ValidationRule):
    """Flag any member assignment whose value is empty or blank (WARNING)."""

    code = "EMPTY_PROPERTY_VALUE"

    def validate(self, group: "ReductionGroup") -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        group_id = getattr(group, "id", "")
        for member in getattr(group, "members", ()):
            for assignment in getattr(member, "property_values", ()):
                if not (assignment.value or "").strip():
                    messages.append(
                        ValidationMessage(
                            severity=Severity.WARNING,
                            code=self.code,
                            message=(
                                f"Property '{assignment.property_id}' has an "
                                "empty value."
                            ),
                            group_id=group_id,
                            member_id=getattr(member, "id", None),
                        )
                    )
        return messages


class DuplicatePropertyAssignmentRule(ValidationRule):
    """Flag a member with more than one assignment for the same property (ERROR)."""

    code = "DUPLICATE_PROPERTY_ASSIGNMENT"

    def validate(self, group: "ReductionGroup") -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        group_id = getattr(group, "id", "")
        for member in getattr(group, "members", ()):
            counts: dict[str, int] = {}
            for assignment in getattr(member, "property_values", ()):
                property_id = assignment.property_id
                counts[property_id] = counts.get(property_id, 0) + 1
            for property_id, count in counts.items():
                if count > 1:
                    messages.append(
                        ValidationMessage(
                            severity=Severity.ERROR,
                            code=self.code,
                            message=(
                                f"Property '{property_id}' is assigned "
                                f"{count} times to the same member."
                            ),
                            group_id=group_id,
                            member_id=getattr(member, "id", None),
                        )
                    )
        return messages


def default_engineering_validation_rules() -> tuple[ValidationRule, ...]:
    """The default rule collection, in registration (execution) order."""
    return (
        EmptyPropertyValueRule(),
        DuplicatePropertyAssignmentRule(),
    )
