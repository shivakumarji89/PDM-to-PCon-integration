"""Validation engine.

A shared base for workspace validation results. Every workspace validation
carries the same core fields (totals, selection, per-item issues, warnings)
and the same readiness semantics; domain-specific results extend this base
with their own fields and key strategy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BaseValidation:
    """Common validation result shape shared by all workspaces."""

    total: int = 0
    selected: int = 0
    invalid_selections: int = 0
    warnings: list[str] = field(default_factory=list)
    issues_by_id: dict[str, list[str]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """Whether there are no warnings and no invalid selections."""
        return not self.warnings and self.invalid_selections == 0

    def issues_for(self, item: Any) -> list[str]:
        """Return the recorded issues for an item (empty when valid)."""
        return self.issues_by_id.get(self._key(item), [])

    @staticmethod
    def _key(item: Any) -> str:
        """Stable identity key for an item. Overridable by subclasses."""
        return str(getattr(item, "id", None))
