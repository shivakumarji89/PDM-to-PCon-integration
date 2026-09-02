"""Property value domain model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PropertyValue:
    """A value assigned to a property. Fields only."""

    id: str | None = None
    property_id: str | None = None
    value: str = ""
    code: str = ""
    model_suffix: str = ""
    display_order: int | None = None
    selected: bool = False
