"""Concrete Engineering generation rules.

Pluggable :class:`~services.engineering.engineering_generation_service.
EngineeringGenerationRule` implementations. Each rule receives a validation
group result and returns a
:class:`~services.engineering.engineering_generation_service.GenerationRuleOutput`
(messages and/or artifacts). Rules are stateless, read-only and deterministic:
they never mutate the validation result, the reduction result, or Engineering,
and never write files.

A generation rule only receives a validation group result (its ``group_id`` and
validation ``messages``); it cannot reach members, articles, or property values.
Rules that would need that source data (e.g. article/property generation) are
therefore intentionally omitted until the framework exposes it - the framework
must not be modified here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from services.engineering.engineering_generation_service import (
    EngineeringGenerationRule,
    GenerationMessage,
    GenerationRuleOutput,
    Severity,
)

if TYPE_CHECKING:
    from services.engineering.engineering_validation_service import (
        ValidationGroupResult,
    )


def _severity_value(severity: object) -> str:
    """Return the string value of a (validation) severity, decoupled from its enum."""
    return getattr(severity, "value", severity)


@dataclass(frozen=True)
class GroupMetadataArtifact:
    """An immutable metadata artifact summarising a group's validation outcome."""

    group_id: str
    info_count: int
    warning_count: int
    error_count: int
    valid: bool


class MetadataGenerationRule(EngineeringGenerationRule):
    """Generate one metadata artifact per group from its validation messages."""

    def generate(self, group_result: "ValidationGroupResult") -> GenerationRuleOutput:
        messages = getattr(group_result, "messages", ()) or ()
        info = sum(1 for m in messages if _severity_value(m.severity) == "info")
        warning = sum(1 for m in messages if _severity_value(m.severity) == "warning")
        error = sum(1 for m in messages if _severity_value(m.severity) == "error")
        artifact = GroupMetadataArtifact(
            group_id=getattr(group_result, "group_id", ""),
            info_count=info,
            warning_count=warning,
            error_count=error,
            valid=(error == 0),
        )
        return GenerationRuleOutput(artifacts=(artifact,))


class ReadinessGenerationRule(EngineeringGenerationRule):
    """Report whether a group is ready for generation (INFO) or blocked (ERROR)."""

    READY_CODE = "GENERATION_READY"
    BLOCKED_CODE = "GENERATION_BLOCKED"

    def generate(self, group_result: "ValidationGroupResult") -> GenerationRuleOutput:
        messages = getattr(group_result, "messages", ()) or ()
        group_id = getattr(group_result, "group_id", "")
        has_error = any(_severity_value(m.severity) == "error" for m in messages)
        if has_error:
            return GenerationRuleOutput(
                messages=(
                    GenerationMessage(
                        severity=Severity.ERROR,
                        code=self.BLOCKED_CODE,
                        message="Group has validation errors; generation blocked.",
                        group_id=group_id,
                    ),
                )
            )
        return GenerationRuleOutput(
            messages=(
                GenerationMessage(
                    severity=Severity.INFO,
                    code=self.READY_CODE,
                    message="Group passed validation; ready for generation.",
                    group_id=group_id,
                ),
            )
        )


def default_engineering_generation_rules() -> tuple[EngineeringGenerationRule, ...]:
    """The default generation rule collection, in registration (execution) order."""
    return (
        MetadataGenerationRule(),
        ReadinessGenerationRule(),
    )
