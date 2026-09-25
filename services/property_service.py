"""Property service.

Snapshot-based property operations: reading the active snapshot's properties,
managing selection (via the shared selection engine), and validating them.
Contains no SQL and never touches the database.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.engines import statistics
from core.engines.validation import BaseValidation
from models.property import Property
from services.selectable_service import SelectableSnapshotService


@dataclass
class PropertyValidation(BaseValidation):
    """Result of validating the active snapshot's properties."""

    duplicate_names: list[str] = field(default_factory=list)
    properties_without_values: int = 0
    missing_names: int = 0

    @staticmethod
    def _key(prop: Property) -> str:
        return str(prop.id) if prop.id is not None else prop.name


class PropertyService(SelectableSnapshotService):
    """Reads, analyses and validates properties from the active snapshot."""

    def items(self) -> list[Property]:
        snapshot = self.context.active_snapshot
        if snapshot is None or not snapshot.properties:
            return []
        return list(snapshot.properties)

    def get_properties(self) -> list[Property]:
        """Return the active snapshot's properties, ordered by display order.

        Properties are sorted by ``display_order`` (then name); those without a
        display order sort after the ordered ones.
        """
        return sorted(self.items(), key=self._display_order_key)

    @staticmethod
    def _display_order_key(prop: Property) -> tuple[bool, int, str]:
        order = prop.display_order
        return (order is None, order if order is not None else 0,
                (prop.name or "").casefold())

    def selected_properties(self) -> list[Property]:
        return self.selected()

    def validate(self) -> PropertyValidation:
        """Validate the active snapshot's properties (in-memory checks only)."""
        properties = self.get_properties()
        result = PropertyValidation(total=len(properties))

        if not properties:
            result.warnings.append("No properties loaded.")
            return result

        result.duplicate_names = statistics.duplicate_keys(properties, lambda p: p.name)

        for prop in properties:
            issues: list[str] = []
            if not (prop.name or "").strip():
                issues.append("Missing name")
                result.missing_names += 1
            if prop.name in result.duplicate_names:
                issues.append("Duplicate name")
            if not prop.values:
                issues.append("No values")
                result.properties_without_values += 1
            elif any(not (v.value or "").strip() for v in prop.values):
                issues.append("Empty value(s)")
            if issues:
                result.issues_by_id[PropertyValidation._key(prop)] = issues

        result.selected = sum(1 for p in properties if p.selected)
        result.invalid_selections = sum(
            1 for p in properties
            if p.selected and PropertyValidation._key(p) in result.issues_by_id
        )

        if result.duplicate_names:
            result.warnings.append(
                f"{len(result.duplicate_names)} duplicate property name(s)."
            )
        if result.properties_without_values:
            result.warnings.append(
                f"{result.properties_without_values} property(ies) without values."
            )
        if result.missing_names:
            result.warnings.append(f"{result.missing_names} property(ies) missing a name.")
        if result.invalid_selections:
            result.warnings.append(
                f"{result.invalid_selections} selected property(ies) have issues."
            )
        return result
