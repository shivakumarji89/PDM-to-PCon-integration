"""Maintenance alignment state referencing the shared PDM and MDB Import data."""
from __future__ import annotations

from dataclasses import dataclass, field

from models.snapshot import Snapshot


@dataclass(frozen=True)
class MaintenanceBaseRule:
    base_code: str
    base_length: int
    slicing_method: str = "RELEASED_MDB_BASE_CODE"
    source: str = "MDB"


@dataclass(frozen=True)
class MaintenanceArticleRelation:
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
class MaintenanceAlignment:
    status: str = "UNRESOLVED"
    base_rules: list[MaintenanceBaseRule] = field(default_factory=list)
    relations: list[MaintenanceArticleRelation] = field(default_factory=list)
    unresolved_article_ids: list[str] = field(default_factory=list)
    unresolved_article_codes: list[str] = field(default_factory=list)
    message: str = ""

    @property
    def is_aligned(self) -> bool:
        return self.status == "ALIGNED"

    @property
    def relation_by_pdm_id(self) -> dict[str, MaintenanceArticleRelation]:
        return {row.pdm_article_id: row for row in self.relations}


@dataclass
class MaintenanceSnapshot:
    """Maintenance workflow state; it does not own or copy source snapshots.

    * ``pdm_snapshot`` references the shared PDM source.
    * ``mdb_import_snapshot`` references the existing MDB comparison state.
    """

    pdm_snapshot: Snapshot | None = None
    mdb_import_snapshot: Snapshot | None = None
    alignment: MaintenanceAlignment = field(default_factory=MaintenanceAlignment)

    def clear_alignment(self) -> None:
        self.alignment = MaintenanceAlignment()
