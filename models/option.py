"""Option domain model."""
from __future__ import annotations

from dataclasses import dataclass, field

from models.option_value import OptionValue


@dataclass
class Option:
    """A configurable option.

    An option owns its selectable values (Option -> Option Values).
    Fields and relationships only.
    """

    id: str | None = None
    code: str = ""
    name: str = ""
    display_order: int | None = None
    is_fabric: bool = False
    selected: bool = False

    # Relationship: Option -> Option Values.
    values: list[OptionValue] = field(default_factory=list)
