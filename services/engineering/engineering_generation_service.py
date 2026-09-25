"""Engineering generation framework.

An extensible pipeline that consumes a validation result and produces immutable
generation results. New generation rules can be added without modifying the
service: the service simply executes the rules injected into it.

This milestone implements the *framework* only - no concrete generation rules,
GO/OAP/OCD generation, or exports are included.

The service is stateless, read-only and deterministic: it never mutates the
validation result (nor the reduction result or Engineering behind it), and never
raises for a rule finding - every message is returned in the result.

To keep engineering services decoupled, the validation result is consumed by
duck typing; its concrete type is imported only for static type checking.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Iterable

from services.base_service import BaseService

if TYPE_CHECKING:
    from core.application_context import ApplicationContext
    from services.engineering.engineering_validation_service import (
        ValidationGroupResult,
        ValidationResult,
    )


class Severity(str, Enum):
    """The severity of a generation message."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class GenerationMessage:
    """A single generation finding (immutable)."""

    severity: Severity
    code: str
    message: str
    group_id: str
    member_id: str | None = None


@dataclass(frozen=True)
class GenerationRuleOutput:
    """What a generation rule returns for one group: messages and artifacts."""

    messages: tuple[GenerationMessage, ...] = ()
    artifacts: tuple[object, ...] = ()


@dataclass(frozen=True)
class GenerationGroupResult:
    """The generation outcome for a single group (immutable)."""

    group_id: str
    messages: tuple[GenerationMessage, ...] = ()
    artifacts: tuple[object, ...] = ()


@dataclass(frozen=True)
class GenerationResult:
    """The complete, read-only outcome of a generation run."""

    groups: tuple[GenerationGroupResult, ...] = ()
    artifacts: tuple[object, ...] = ()
    messages: tuple[GenerationMessage, ...] = ()
    has_errors: bool = False


class EngineeringGenerationRule(ABC):
    """Extension point: a single generation rule over a validation group result.

    A rule is stateless, read-only and deterministic. It inspects a validation
    group result and returns the messages and artifacts it generates for that
    group. Concrete rules are added by future milestones.
    """

    @abstractmethod
    def generate(self, group_result: "ValidationGroupResult") -> GenerationRuleOutput:
        """Return the generation output for ``group_result``."""
        raise NotImplementedError


class EngineeringGenerationService(BaseService):
    """Execute the registered generation rules over a validation result."""

    def __init__(
        self,
        context: "ApplicationContext",
        rules: Iterable[EngineeringGenerationRule] | None = None,
    ) -> None:
        super().__init__(context)
        self._rules: tuple[EngineeringGenerationRule, ...] = tuple(rules or ())

    def generate(
        self, validation_result: "ValidationResult | None"
    ) -> GenerationResult:
        """Generate from ``validation_result`` and return the outcome.

        Deterministic: groups are processed in order, and within each group the
        rules run in registration order. Never mutates its input.
        """
        groups = getattr(validation_result, "groups", ()) or ()

        group_results: list[GenerationGroupResult] = []
        all_messages: list[GenerationMessage] = []
        all_artifacts: list[object] = []
        for group_result in groups:
            group_messages: list[GenerationMessage] = []
            group_artifacts: list[object] = []
            for rule in self._rules:
                output = rule.generate(group_result)
                group_messages.extend(getattr(output, "messages", ()) or ())
                group_artifacts.extend(getattr(output, "artifacts", ()) or ())
            group_results.append(
                GenerationGroupResult(
                    group_id=getattr(group_result, "group_id", ""),
                    messages=tuple(group_messages),
                    artifacts=tuple(group_artifacts),
                )
            )
            all_messages.extend(group_messages)
            all_artifacts.extend(group_artifacts)

        has_errors = any(
            message.severity is Severity.ERROR for message in all_messages
        )
        return GenerationResult(
            groups=tuple(group_results),
            artifacts=tuple(all_artifacts),
            messages=tuple(all_messages),
            has_errors=has_errors,
        )
