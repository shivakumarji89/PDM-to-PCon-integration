"""Option value domain model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OptionValue:
    """A value belonging to an option. Fields only."""

    id: str | None = None
    option_id: str | None = None
    value: str = ""
    code: str = ""
    supplier_code: str = ""
    display_order: int | None = None
    selected: bool = False
