"""Cross-source data lineage models.

Values in the Product Workbench should carry enough provenance for workflows,
validation and future agents to explain where a value came from and where its
equivalent can be checked in another source.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceLocation:
    """A traceable location for one data item in one system."""

    system: str
    path: str = ""
    file: str = ""
    table: str = ""
    column: str = ""
    relationship: str = ""
    status: str = "known"


@dataclass
class DataLineageRecord:
    """One logical data item plus its repository and PDM lineage."""

    key: str
    value: Any = None
    fetch_status: str = "not_fetched"
    sources: list[SourceLocation] = field(default_factory=list)
    pdm_mapping_status: str = "not_checked"
    notes: str = ""


@dataclass
class RepositoryProductContext:
    """Read-only context created when an existing repository series is opened."""

    repository_path: str
    series_name: str
    category: str = ""
    records: dict[str, DataLineageRecord] = field(default_factory=dict)
    pdm_match_count: int = 0
    pdm_match_status: str = "not_checked"
    pdm_product_id: str | None = None
