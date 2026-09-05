"""Product domain model."""
from __future__ import annotations

from dataclasses import dataclass, field

from models.article import Article
from models.option import Option


@dataclass
class Product:
    """A product record and the root of the engineering object graph.

    A product owns its articles and options, which in turn own their
    properties/values. Fields and relationships only - no behavior.
    """

    id: str | None = None
    code: str = ""
    name: str = ""
    description: str = ""
    category: str = ""
    catalogue_id: str | None = None
    lead_time: int | None = None
    range_name: str = ""
    status: str = ""
    is_super_product: bool = False
    new_product: bool = False

    # Relationships: Product -> Articles and Product -> Options.
    articles: list[Article] = field(default_factory=list)
    options: list[Option] = field(default_factory=list)
