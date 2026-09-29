"""Article-set classification records.

An :class:`ArticleSet` captures one group of articles that share the same
property structure (e.g. single desk vs back-to-back). It is a *derived*,
persisted table - materialised from the snapshot's product/property/option
links - that records, per set, the properties and options its articles carry,
the values of each, and exactly which articles carry each value (some values
apply to only part of a set). It feeds relation creation. Fields only - no logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SetValue:
    """One property/option value and the articles in the set that carry it."""

    id: str = ""
    value: str = ""
    code: str = ""
    article_ids: list[str] = field(default_factory=list)


@dataclass
class SetAttribute:
    """One property or option carried by a set, with its value coverage."""

    id: str = ""
    name: str = ""
    values: list[SetValue] = field(default_factory=list)


@dataclass
class ArticleSet:
    """A group of articles sharing a property structure (single, b2b, ...)."""

    id: str = ""
    base_length: int = 0
    base_code: str = ""
    article_ids: list[str] = field(default_factory=list)
    properties: list[SetAttribute] = field(default_factory=list)
    options: list[SetAttribute] = field(default_factory=list)
