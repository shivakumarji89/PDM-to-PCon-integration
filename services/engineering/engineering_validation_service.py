"""Engineering validation framework.

Consumes a reduction result and validates every reduction group against a set
of pluggable rules, returning an immutable :class:`ValidationResult`. This
milestone implements the *framework* only - no concrete engineering business
rules are included; future milestones register :class:`ValidationRule`
implementations.

The service is stateless, read-only and deterministic: it never mutates the
reduction result, Engineering, members, or assignments, and it never raises for
business validation failures - every finding is returned in the result.

To keep engineering services decoupled, the reduction result is consumed by
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
    from services.engineering.engineering_reduction_service import (
        ReductionGroup,
        ReductionResult,
    )


class Severity(str, Enum):
    """The severity of a validation message."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ValidationMessage:
    """A single validation finding (immutable)."""

    severity: Severity
    code: str
    message: str
    group_id: str
    member_id: str | None = None


@dataclass(frozen=True)
class ValidationGroupResult:
    """The validation findings for a single reduction group (immutable)."""

    group_id: str
    messages: tuple[ValidationMessage, ...] = ()


@dataclass(frozen=True)
class ValidationResult:
    """The complete, read-only outcome of a validation run."""

    groups: tuple[ValidationGroupResult, ...] = ()
    messages: tuple[ValidationMessage, ...] = ()
    has_errors: bool = False


class ValidationRule(ABC):
    """Extension point: a single validation rule over a reduction group.

    A rule is read-only and returns zero or more :class:`ValidationMessage`
    objects for the group it is given. Concrete rules are added by future
    milestones.
    """

    @abstractmethod
    def validate(self, group: "ReductionGroup") -> Iterable[ValidationMessage]:
        """Return the validation messages this rule produces for ``group``."""
        raise NotImplementedError


class EngineeringValidationService(BaseService):
    """Validate every reduction group against the registered rules (read-only)."""

    def __init__(
        self,
        context: "ApplicationContext",
        rules: Iterable[ValidationRule] | None = None,
    ) -> None:
        super().__init__(context)
        if rules is None:
            # Register the default rule collection when none is supplied. Imported
            # lazily so the rules module (which imports this framework) does not
            # create an import cycle. Passing an explicit (possibly empty) list
            # bypasses the defaults.
            from services.engineering.validation_rules import (
                default_engineering_validation_rules,
            )

            rules = default_engineering_validation_rules()
        self._rules: tuple[ValidationRule, ...] = tuple(rules)

    def validate(self, reduction_result: "ReductionResult | None") -> ValidationResult:
        """Validate each group in ``reduction_result`` and return the outcome.

        Deterministic: groups are processed in order, and within each group the
        rules run in registration order. Never mutates its input.
        """
        groups = getattr(reduction_result, "groups", ()) or ()

        group_results: list[ValidationGroupResult] = []
        all_messages: list[ValidationMessage] = []
        for group in groups:
            group_messages: list[ValidationMessage] = []
            for rule in self._rules:
                for message in rule.validate(group) or ():
                    group_messages.append(message)
            group_results.append(
                ValidationGroupResult(
                    group_id=getattr(group, "id", ""),
                    messages=tuple(group_messages),
                )
            )
            all_messages.extend(group_messages)

        has_errors = any(
            message.severity is Severity.ERROR for message in all_messages
        )
        return ValidationResult(
            groups=tuple(group_results),
            messages=tuple(all_messages),
            has_errors=has_errors,
        )
