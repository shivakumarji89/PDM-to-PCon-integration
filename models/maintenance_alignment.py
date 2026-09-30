"""Maintenance alignment records derived from the released MDB repository."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaintenanceBaseRule:
    """One base article rule copied from the released MDB."""

    base_code: str
    base_length: int
    slicing_method: str = "RELEASED_MDB_BASE_CODE"
    source: str = "MDB"


@dataclass(frozen=True)
class MaintenanceArticleRelation:
    """Explicit PDM article -> released MDB base-article relationship."""

    pdm_article_id: str
    pdm_article_code: str
    mdb_article_id: str
    mdb_article_code: str
    base_code: str
    base_length: int
    slicing_method: str = "RELEASED_MDB_BASE_CODE"
    status: str = "MATCHED"
    reason: str = ""


@dataclass
class MaintenanceAlignmentResult:
    """Result of applying the released MDB base rules to a PDM snapshot."""

    status: str = "UNRESOLVED"
    base_rules: list[MaintenanceBaseRule] = field(default_factory=list)
    relations: list[MaintenanceArticleRelation] = field(default_factory=list)
    unresolved_article_ids: list[str] = field(default_factory=list)
    unresolved_article_codes: list[str] = field(default_factory=list)
    message: str = ""

    @property
    def is_aligned(self) -> bool:
        return self.status == "ALIGNED"
