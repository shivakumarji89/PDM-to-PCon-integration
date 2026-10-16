"""Additive, PDM-authoritative article-code matching helpers.

This module deliberately sits alongside the existing splitting/reduction
engines. It provides a single exact-source method for identifying the portion
of a PDM article code before the first dot, while retaining the original source
code, source order, and PDM article identity for downstream order-code/value
matching.

It does not mutate snapshots or replace existing reduction behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Any


@dataclass(frozen=True)
class PDMExactArticleCode:
    """One source article and its PDM-derived pre-dot matching key."""

    article_id: str
    product_id: str
    source_code: str
    match_key: str
    suffix: str
    source_order: int


@dataclass(frozen=True)
class PDMExactArticleIndex:
    """Ordered PDM code rows plus any non-unique pre-dot keys."""

    rows: tuple[PDMExactArticleCode, ...] = ()
    duplicate_keys: tuple[str, ...] = ()

    @property
    def by_article_id(self) -> dict[str, PDMExactArticleCode]:
        return {row.article_id: row for row in self.rows}

    @property
    def by_match_key(self) -> dict[str, tuple[PDMExactArticleCode, ...]]:
        grouped: dict[str, list[PDMExactArticleCode]] = {}
        for row in self.rows:
            grouped.setdefault(row.match_key, []).append(row)
        return {key: tuple(rows) for key, rows in grouped.items()}


def extract_pdm_exact_article_code(
    source_code: Any,
    *,
    article_id: Any = "",
    product_id: Any = "",
    source_order: int = 0,
) -> PDMExactArticleCode:
    """Extract the PDM matching key before the first dot without rewriting source.

    The original source code is preserved byte-for-byte after string
    conversion. No trimming, case-folding, padding, or character slicing is
    applied. A code without a dot has an empty suffix and matches itself.
    """
    original = "" if source_code is None else str(source_code)
    match_key, separator, suffix = original.partition(".")
    return PDMExactArticleCode(
        article_id="" if article_id is None else str(article_id),
        product_id="" if product_id is None else str(product_id),
        source_code=original,
        match_key=match_key,
        suffix=suffix if separator else "",
        source_order=int(source_order),
    )


def build_pdm_exact_article_index(articles: Iterable[Any]) -> PDMExactArticleIndex:
    """Index article records in source order and report ambiguous pre-dot keys.

    Duplicate keys are preserved rather than silently selecting one PDM row.
    The caller can therefore use PDM order/value relationships and explicitly
    resolve ambiguity without losing source records.
    """
    rows = tuple(
        extract_pdm_exact_article_code(
            getattr(article, "code", ""),
            article_id=getattr(article, "id", ""),
            product_id=getattr(article, "product_id", ""),
            source_order=index,
        )
        for index, article in enumerate(articles)
    )
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.match_key] = counts.get(row.match_key, 0) + 1
    duplicates = tuple(key for key, count in counts.items() if count > 1)
    return PDMExactArticleIndex(rows=rows, duplicate_keys=duplicates)
