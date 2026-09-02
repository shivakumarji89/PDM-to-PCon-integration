"""Engineering PropertyDefinition model.

Defines a single entry in the Engineering *vocabulary* - the definition of an
engineering property (e.g. "Width", "Color"). This is a definition only: it is
NOT a property value and carries no assigned data. Property definitions are
owned by :class:`~models.engineering.Engineering`; assignments will reference a
definition by its ``id`` in a later step.

Pure data - fields only, no methods, logic, services, or persistence. It never
references the Snapshot source :class:`~models.property.Property`.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PropertyDataType(str, Enum):
    """The data type of an engineering property definition."""

    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"


@dataclass
class PropertyDefinition:
    """An entry in the Engineering property vocabulary (definition only)."""

    id: str = ""
    name: str = ""
    order: int = 0
    data_type: PropertyDataType = PropertyDataType.TEXT
