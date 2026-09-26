"""Models for the Article OBX generation pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ArticleConfigurationValue:
    """One property/option value selected by a real PDM article."""

    kind: str
    entity_id: str
    value_id: str
    name: str
    value: str
    code: str = ""
    display_order: int = 0


@dataclass(frozen=True)
class ArticlePermutation:
    """One valid article configuration sourced from an existing Snapshot article.

    A permutation is never manufactured by Cartesian-product expansion. The
    source article itself proves that this exact combination exists in PDM.
    """

    article_id: str
    product_id: str
    base_code: str
    final_article: str
    name: str = ""
    description: str = ""
    quantity: int = 1
    is_super_item: bool = False
    properties: tuple[ArticleConfigurationValue, ...] = ()
    options: tuple[ArticleConfigurationValue, ...] = ()

    @property
    def all_values(self) -> tuple[ArticleConfigurationValue, ...]:
        return self.properties + self.options


@dataclass(frozen=True)
class ArticlePrice:
    """Resolved PDM price for one article permutation."""

    article_id: str
    article_code: str
    currency: str
    effective_date: str
    site_id: int
    base_price: float | None = None
    option_increments: tuple[float, ...] = ()
    total_price: float | None = None
    unresolved_reason: str = ""


@dataclass(frozen=True)
class ArticleObxRow:
    """One priced article ready for OBX serialization."""

    permutation: ArticlePermutation
    price: ArticlePrice


@dataclass
class ArticleObxResult:
    """Result of a complete Article OBX generation run."""

    rows: list[ArticleObxRow] = field(default_factory=list)
    xml: str = ""
    warnings: list[str] = field(default_factory=list)
