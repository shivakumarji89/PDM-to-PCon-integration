"""Engineering PropertyAssignment model.

Represents the value a :class:`~models.member_article.MemberArticle` gives to an
Engineering property. It links to a
:class:`~models.property_definition.PropertyDefinition` by its ``id`` (a plain
string) - it never stores a PropertyDefinition object, and never references the
Snapshot source :class:`~models.property.Property`.

Pure data - fields only, no methods, logic, validation, uniqueness rules, or
services.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PropertyAssignment:
    """A member's value for a property definition (definition referenced by id)."""

    property_id: str = ""
    value: str = ""
