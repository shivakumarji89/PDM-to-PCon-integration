"""Engineering property definition management service.

Create, rename, delete and reorder :class:`~models.property_definition.
PropertyDefinition` entries in the Engineering vocabulary. It mutates **only**
``snapshot.engineering.properties`` (and, on delete, removes the assignments
that reference the deleted property from every member). It never touches source
data, PDM, the UI, or signals.

Business rules:
  * Property names are unique (case-insensitive, trimmed).
  * A property ``id`` never changes once created.
  * Deleting a property removes every assignment that references it.
  * ``order`` is kept contiguous (0-based) and reflects list position.

It performs no validation, reduction, configuration, generation, or
synchronization.
"""
from __future__ import annotations

from uuid import uuid4

from models.property_definition import PropertyDataType, PropertyDefinition
from models.snapshot import Snapshot
from services.base_service import BaseService


class EngineeringPropertyService(BaseService):
    """Create / rename / delete / reorder engineering property definitions."""

    def create_property(
        self,
        snapshot: Snapshot | None,
        name: str,
        data_type: PropertyDataType = PropertyDataType.TEXT,
    ) -> PropertyDefinition | None:
        """Append a new property definition and return it.

        Rejects a missing snapshot, a blank name, or a duplicate name. The new
        property gets a fresh, permanent ``id`` and is ordered last.
        """
        if snapshot is None or snapshot.engineering is None:
            return None
        clean = (name or "").strip()
        if not clean:
            return None
        properties = snapshot.engineering.properties
        if self._find_by_name(properties, clean) is not None:
            return None
        definition = PropertyDefinition(
            id=uuid4().hex,
            name=clean,
            order=len(properties),
            data_type=data_type,
        )
        properties.append(definition)
        return definition

    def rename_property(
        self, snapshot: Snapshot | None, property_id: str | None, new_name: str
    ) -> bool:
        """Rename the property with ``property_id``. The ``id`` is unchanged.

        Rejects an unknown property, a blank name, or a name already used by a
        different property.
        """
        if snapshot is None or snapshot.engineering is None or not property_id:
            return False
        properties = snapshot.engineering.properties
        target = self._find_by_id(properties, property_id)
        if target is None:
            return False
        clean = (new_name or "").strip()
        if not clean:
            return False
        existing = self._find_by_name(properties, clean)
        if existing is not None and existing is not target:
            return False
        target.name = clean
        return True

    def delete_property(
        self, snapshot: Snapshot | None, property_id: str | None
    ) -> bool:
        """Delete the property with ``property_id`` and every assignment to it."""
        if snapshot is None or snapshot.engineering is None or not property_id:
            return False
        properties = snapshot.engineering.properties
        target = self._find_by_id(properties, property_id)
        if target is None:
            return False
        properties.remove(target)
        self._renumber(properties)
        for family in snapshot.engineering.families:
            for member in family.members:
                member.property_values[:] = [
                    assignment
                    for assignment in member.property_values
                    if assignment.property_id != property_id
                ]
        return True

    def reorder_property(
        self, snapshot: Snapshot | None, property_id: str | None, new_index: int
    ) -> bool:
        """Move the property to ``new_index`` and renumber all ``order`` values.

        ``new_index`` is clamped to the valid range. Rejects an unknown property.
        """
        if snapshot is None or snapshot.engineering is None or not property_id:
            return False
        properties = snapshot.engineering.properties
        target = self._find_by_id(properties, property_id)
        if target is None:
            return False
        properties.remove(target)
        index = max(0, min(new_index, len(properties)))
        properties.insert(index, target)
        self._renumber(properties)
        return True

    @staticmethod
    def _find_by_id(
        properties: list[PropertyDefinition], property_id: str
    ) -> PropertyDefinition | None:
        for definition in properties:
            if definition.id == property_id:
                return definition
        return None

    @staticmethod
    def _find_by_name(
        properties: list[PropertyDefinition], name: str
    ) -> PropertyDefinition | None:
        target = name.strip().casefold()
        for definition in properties:
            if definition.name.strip().casefold() == target:
                return definition
        return None

    @staticmethod
    def _renumber(properties: list[PropertyDefinition]) -> None:
        for index, definition in enumerate(properties):
            definition.order = index
