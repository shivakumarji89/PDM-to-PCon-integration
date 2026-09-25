"""Engineering repository.

The single read-only query layer for the Engineering domain. It owns traversal
and lookup over ``snapshot.engineering`` (families and their members) and nothing
else: it contains no business rules, performs no caching or indexing, and never
mutates the Snapshot or the Engineering model.

Every method takes the Snapshot to read from and returns either a live object,
``None``, or an empty collection when there is nothing to return. Callers must
treat the returned objects as read-only.
"""
from __future__ import annotations

from typing import Iterator

from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.property_assignment import PropertyAssignment
from models.property_definition import PropertyDefinition
from models.snapshot import Snapshot
from repositories.base_repository import BaseRepository


class EngineeringRepository(BaseRepository):
    """Read-only traversal and lookup over ``snapshot.engineering``."""

    def get_families(self, snapshot: Snapshot | None) -> list[EngineeringFamily]:
        """Return the engineering families, or an empty list if there are none."""
        if snapshot is None or snapshot.engineering is None:
            return []
        return list(snapshot.engineering.families)

    def get_family(
        self, snapshot: Snapshot | None, family_id: str | None
    ) -> EngineeringFamily | None:
        """Return the family whose ``id`` equals ``family_id``, else ``None``."""
        if snapshot is None or snapshot.engineering is None or not family_id:
            return None
        for family in snapshot.engineering.families:
            if family.id == family_id:
                return family
        return None

    def get_members(self, snapshot: Snapshot | None) -> list[MemberArticle]:
        """Return all members across every family, or an empty list."""
        return list(self.iter_members(snapshot))

    def iter_members(self, snapshot: Snapshot | None) -> Iterator[MemberArticle]:
        """Iterate every member across all families (read-only traversal)."""
        if snapshot is None or snapshot.engineering is None:
            return
        for family in snapshot.engineering.families:
            for member in family.members:
                yield member

    def find_member(
        self, snapshot: Snapshot | None, article_id: str | None
    ) -> MemberArticle | None:
        """Return the member whose ``article_id`` matches, else ``None``."""
        if not article_id:
            return None
        for member in self.iter_members(snapshot):
            if member.article_id == article_id:
                return member
        return None

    def get_reduced_article(self, member: MemberArticle | None) -> str:
        """Return the member's reduced article, or an empty string."""
        if member is None:
            return ""
        return member.reduced_article

    def get_long_description(self, member: MemberArticle | None) -> str:
        """Return the member's long description, or an empty string."""
        if member is None:
            return ""
        return member.long_description

    def get_short_description(self, member: MemberArticle | None) -> str:
        """Return the member's short description, or an empty string."""
        if member is None:
            return ""
        return member.short_description

    def get_properties(
        self, snapshot: Snapshot | None
    ) -> list[PropertyDefinition]:
        """Return the engineering property definitions, or an empty list."""
        if snapshot is None or snapshot.engineering is None:
            return []
        return list(snapshot.engineering.properties)

    def find_property(
        self, snapshot: Snapshot | None, property_id: str | None
    ) -> PropertyDefinition | None:
        """Return the property definition with ``property_id``, else ``None``."""
        if snapshot is None or snapshot.engineering is None or not property_id:
            return None
        for definition in snapshot.engineering.properties:
            if definition.id == property_id:
                return definition
        return None

    def find_property_by_name(
        self, snapshot: Snapshot | None, name: str | None
    ) -> PropertyDefinition | None:
        """Return the property definition whose name matches (trimmed, case-
        insensitive), else ``None``."""
        if snapshot is None or snapshot.engineering is None or not name:
            return None
        target = name.strip().casefold()
        if not target:
            return None
        for definition in snapshot.engineering.properties:
            if definition.name.strip().casefold() == target:
                return definition
        return None

    def get_assignments(
        self, member: MemberArticle | None
    ) -> list[PropertyAssignment]:
        """Return the member's property assignments, or an empty list."""
        if member is None:
            return []
        return list(member.property_values)

    def find_assignment(
        self, member: MemberArticle | None, property_id: str | None
    ) -> PropertyAssignment | None:
        """Return the member's assignment for ``property_id``, else ``None``."""
        if member is None or not property_id:
            return None
        for assignment in member.property_values:
            if assignment.property_id == property_id:
                return assignment
        return None
