"""Property domain model."""
from __future__ import annotations

from dataclasses import dataclass, field

from models.property_value import PropertyValue


@dataclass
class Property:
    """A product property definition.

    A property owns its assigned values (Property -> Property Values).
    Fields and relationships only.
    """

    id: str | None = None
    code: str = ""
    name: str = ""
    data_type: str = ""
    display_order: int | None = None
    attribute_type: int | None = None
    has_dependent_options: bool = False
    # Character width of this property's order/config code (PDM
    # ``HasDependentOptions``: 2 -> 2 chars, 1 -> 1 char, -1 -> not in the code).
    code_width: int = 0
    selected: bool = False

    # Relationship: Property -> Property Values.
    values: list[PropertyValue] = field(default_factory=list)
