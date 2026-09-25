"""Property value service.

Snapshot-based property-value operations: reading the active snapshot's property
values, resolving their owning property, managing selection (via the shared
selection engine), and validating them. Contains no SQL and never touches the
database.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from core.engines.validation import BaseValidation
from models.property_value import PropertyValue
from services.selectable_service import SelectableSnapshotService


@dataclass
class PropertyValueValidation(BaseValidation):
    """Result of validating the active snapshot's property values."""

    empty_values: int = 0
    missing_codes: int = 0
    duplicate_groups: list[str] = field(default_factory=list)
    orphan_values: int = 0

    @staticmethod
    def _key(value: PropertyValue) -> str:
        if value.id is not None:
            return str(value.id)
        return f"{value.property_id}:{value.value}"


class PropertyValueService(SelectableSnapshotService):
    """Reads, analyses and validates property values from the snapshot."""

    def items(self) -> list[PropertyValue]:
        snapshot = self.context.active_snapshot
        if snapshot is None or not snapshot.property_values:
            return []
        return list(snapshot.property_values)

    def get_values(self) -> list[PropertyValue]:
        """Return the active snapshot's property values, grouped and ordered by
        their owning property's display order, then by value.

        Values whose owning property is unknown sort last.
        """
        order_map = self._property_order_map()
        return sorted(
            self.items(),
            key=lambda v: (
                *order_map.get(v.property_id, (True, 0, 0)),
                (v.value or "").casefold(),
            ),
        )

    def _property_order_map(self) -> dict[str | None, tuple[bool, int, int]]:
        """Map property id -> sort key following the snapshot's property display
        order (missing/None display order sorts last)."""
        snapshot = self.context.active_snapshot
        if snapshot is None:
            return {}
        result: dict[str | None, tuple[bool, int, int]] = {}
        for index, prop in enumerate(snapshot.properties):
            order = prop.display_order
            result[prop.id] = (order is None, order if order is not None else 0, index)
        return result

    def selected_values(self) -> list[PropertyValue]:
        return self.selected()

    def property_name_map(self) -> dict[str | None, str]:
        """Map property id -> property name for the active snapshot."""
        snapshot = self.context.active_snapshot
        if snapshot is None:
            return {}
        return {p.id: p.name for p in snapshot.properties}

    def property_name_for(self, value: PropertyValue) -> str:
        return self.property_name_map().get(value.property_id, "")

    def validate(self) -> PropertyValueValidation:
        """Validate the active snapshot's property values (in-memory only)."""
        values = self.get_values()
        result = PropertyValueValidation(total=len(values))

        if not values:
            result.warnings.append("No property values loaded.")
            return result

        property_ids = set(self.property_name_map().keys())
        pair_counts = Counter((v.property_id, v.value) for v in values)
        duplicate_pairs = {pair for pair, n in pair_counts.items() if n > 1}
        result.duplicate_groups = sorted(
            f"{pid}:{val}" for (pid, val) in duplicate_pairs
        )

        for value in values:
            issues: list[str] = []
            if not (value.value or "").strip():
                issues.append("Empty value")
                result.empty_values += 1
            if not (value.code or "").strip():
                issues.append("Missing code")
                result.missing_codes += 1
            if (value.property_id, value.value) in duplicate_pairs:
                issues.append("Duplicate value")
            if value.property_id not in property_ids:
                issues.append("Orphan value")
                result.orphan_values += 1
            if issues:
                result.issues_by_id[PropertyValueValidation._key(value)] = issues

        result.selected = sum(1 for v in values if v.selected)
        result.invalid_selections = sum(
            1 for v in values
            if v.selected and PropertyValueValidation._key(v) in result.issues_by_id
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
            result.warnings.append(
                f"{result.invalid_selections} selected value(s) have issues."
            )
        return result
