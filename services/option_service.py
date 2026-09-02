"""Option service.

Snapshot-based option operations: reading the active snapshot's options,
managing selection (via the shared selection engine), and validating them.
Contains no SQL and never touches the database.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.engines import statistics
from core.engines.validation import BaseValidation
from models.option import Option
from services.selectable_service import SelectableSnapshotService


@dataclass
class OptionValidation(BaseValidation):
    """Result of validating the active snapshot's options."""

    duplicate_names: list[str] = field(default_factory=list)
    options_without_values: int = 0
    missing_names: int = 0

    @staticmethod
    def _key(option: Option) -> str:
        return str(option.id) if option.id is not None else option.name


class OptionService(SelectableSnapshotService):
    """Reads, analyses and validates options from the active snapshot."""

    def items(self) -> list[Option]:
        snapshot = self.context.active_snapshot
        if snapshot is None or not snapshot.options:
            return []
        return list(snapshot.options)

    def get_options(self) -> list[Option]:
        """Active snapshot's options, ordered by display order (then name);
        those without a display order sort after the ordered ones."""
        return sorted(self.items(), key=self._display_order_key)

    @staticmethod
    def _display_order_key(option: Option) -> tuple[bool, int, str]:
        order = option.display_order
        return (order is None, order if order is not None else 0,
                (option.name or "").casefold())

    def selected_options(self) -> list[Option]:
        return self.selected()

    def validate(self) -> OptionValidation:
        options = self.get_options()
        result = OptionValidation(total=len(options))
        if not options:
            result.warnings.append("No options loaded.")
            return result

        result.duplicate_names = statistics.duplicate_keys(options, lambda o: o.name)

        for option in options:
            issues: list[str] = []
            if not (option.name or "").strip():
                issues.append("Missing name")
                result.missing_names += 1
            if option.name in result.duplicate_names:
                issues.append("Duplicate name")
            if not option.values:
                issues.append("No values")
                result.options_without_values += 1
            if issues:
                result.issues_by_id[OptionValidation._key(option)] = issues

        result.selected = sum(1 for o in options if o.selected)
        result.invalid_selections = sum(
            1 for o in options
            if o.selected and OptionValidation._key(o) in result.issues_by_id
        )

        if result.duplicate_names:
            result.warnings.append(f"{len(result.duplicate_names)} duplicate option name(s).")
        if result.options_without_values:
            result.warnings.append(f"{result.options_without_values} option(s) without values.")
        if result.missing_names:
            result.warnings.append(f"{result.missing_names} option(s) missing a name.")
        if result.invalid_selections:
            result.warnings.append(f"{result.invalid_selections} selected option(s) have issues.")
        return result
