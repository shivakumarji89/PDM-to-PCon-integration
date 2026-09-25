"""Option value service.

Snapshot-based option-value operations: reading the active snapshot's option
values, resolving their owning option, managing selection (via the shared
selection engine), and validating them. Contains no SQL and never touches the
database.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from core.engines.validation import BaseValidation
from models.option_value import OptionValue
from services.selectable_service import SelectableSnapshotService


@dataclass
class OptionValueValidation(BaseValidation):
    """Result of validating the active snapshot's option values."""

    empty_values: int = 0
    missing_codes: int = 0
    duplicate_groups: list[str] = field(default_factory=list)
    orphan_values: int = 0

    @staticmethod
    def _key(value: OptionValue) -> str:
        if value.id is not None:
            return str(value.id)
        return f"{value.option_id}:{value.value}"


class OptionValueService(SelectableSnapshotService):
    """Reads, analyses and validates option values from the snapshot."""

    def items(self) -> list[OptionValue]:
        snapshot = self.context.active_snapshot
        if snapshot is None or not snapshot.option_values:
            return []
        return list(snapshot.option_values)

    def get_values(self) -> list[OptionValue]:
        return self.items()

    def selected_values(self) -> list[OptionValue]:
        return self.selected()

    def option_name_map(self) -> dict[str | None, str]:
        snapshot = self.context.active_snapshot
        if snapshot is None:
            return {}
        return {o.id: o.name for o in snapshot.options}

    def option_name_for(self, value: OptionValue) -> str:
        return self.option_name_map().get(value.option_id, "")

    def validate(self) -> OptionValueValidation:
        values = self.get_values()
        result = OptionValueValidation(total=len(values))
        if not values:
            result.warnings.append("No option values loaded.")
            return result

        option_ids = set(self.option_name_map().keys())
        pair_counts = Counter((v.option_id, v.value) for v in values)
        duplicate_pairs = {pair for pair, n in pair_counts.items() if n > 1}
        result.duplicate_groups = sorted(f"{oid}:{val}" for (oid, val) in duplicate_pairs)

        for value in values:
            issues: list[str] = []
            if not (value.value or "").strip():
                issues.append("Empty value")
                result.empty_values += 1
            if not (value.code or "").strip():
                issues.append("Missing code")
                result.missing_codes += 1
            if (value.option_id, value.value) in duplicate_pairs:
                issues.append("Duplicate value")
            if value.option_id not in option_ids:
                issues.append("Orphan value")
                result.orphan_values += 1
            if issues:
                result.issues_by_id[OptionValueValidation._key(value)] = issues

        result.selected = sum(1 for v in values if v.selected)
        result.invalid_selections = sum(
            1 for v in values
            if v.selected and OptionValueValidation._key(v) in result.issues_by_id
        )

        if duplicate_pairs:
            result.warnings.append(f"{len(duplicate_pairs)} duplicate value group(s).")
        if result.empty_values:
            result.warnings.append(f"{result.empty_values} empty value(s).")
        if result.missing_codes:
            result.warnings.append(f"{result.missing_codes} value(s) missing a code.")
        if result.orphan_values:
            result.warnings.append(f"{result.orphan_values} orphan value(s).")
        if result.invalid_selections:
            result.warnings.append(f"{result.invalid_selections} selected value(s) have issues.")
        return result
