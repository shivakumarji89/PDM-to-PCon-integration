"""Article domain model."""
from __future__ import annotations

from dataclasses import dataclass, field

from models.property import Property


@dataclass
class Article:
    """An article belonging to a product.

    An article owns the properties that describe it (Article -> Properties).
    Fields and relationships only.
    """

    id: str | None = None
    product_id: str | None = None
    code: str = ""
    name: str = ""
    quantity: int = 0
    description: str = ""
    status: str = ""
    source: str = ""
    notes: str = ""
    is_super_item: bool = False
    weight_kg: float | None = None
    volume_l: float | None = None
    height: int | None = None
    width: int | None = None
    depth: int | None = None
    selected: bool = False

    # Relationship: Article -> Properties.
    properties: list[Property] = field(default_factory=list)
