"""Engineering property assignment service.

Set, clear and read the value a :class:`~models.member_article.MemberArticle`
gives to a property definition. It mutates **only** ``member.property_values``
and never touches source data, PDM, the UI, or signals.

Business rules:
  * At most one assignment per property per member.
  * Setting a value for an existing property updates it in place.
  * An empty value removes the assignment.
  * Properties are referenced by ``property_id`` only.

It performs no validation, uniqueness checking against definitions, reduction,
generation, or synchronization.
"""
from __future__ import annotations

from models.member_article import MemberArticle
from models.property_assignment import PropertyAssignment
from services.base_service import BaseService


class EngineeringAssignmentService(BaseService):
    """Manage a member's property value assignments (business logic only)."""

    def set_value(
        self,
        member: MemberArticle | None,
        property_id: str | None,
        value: str,
    ) -> PropertyAssignment | None:
        """Set ``property_id`` to ``value`` on ``member``.

        Creates the assignment if absent, updates it if present. An empty value
        removes the assignment and returns ``None``. Returns the assignment on
        success, or ``None`` on invalid input / removal.
        """
        if member is None or not property_id:
            return None
        text = "" if value is None else value
        if text == "":
            self.clear_value(member, property_id)
            return None
        existing = self._find(member, property_id)
        if existing is not None:
            existing.value = text
            return existing
        assignment = PropertyAssignment(property_id=property_id, value=text)
        member.property_values.append(assignment)
        return assignment

    def clear_value(
        self, member: MemberArticle | None, property_id: str | None
    ) -> bool:
        """Remove the assignment for ``property_id``. Returns whether one was removed."""
        if member is None or not property_id:
            return False
        before = len(member.property_values)
        member.property_values[:] = [
            assignment
            for assignment in member.property_values
            if assignment.property_id != property_id
        ]
        return len(member.property_values) != before

    def get_value(
        self, member: MemberArticle | None, property_id: str | None
    ) -> str | None:
        """Return the value assigned for ``property_id``, or ``None`` if unassigned."""
        assignment = self._find(member, property_id)
        return assignment.value if assignment is not None else None

    @staticmethod
    def _find(
        member: MemberArticle | None, property_id: str | None
    ) -> PropertyAssignment | None:
        if member is None or not property_id:
            return None
        for assignment in member.property_values:
            if assignment.property_id == property_id:
                return assignment
        return None
