"""Per-product MDB export session model.

One product has exactly one MDB. The session records where that MDB lives and
the identifiers every later workflow export must reuse. It contains no
credentials or engineering payload - only paths, surrogate keys and
source-to-MDB identity mappings.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SESSION_VERSION = 1


@dataclass
class MdbExportSession:
    """State of the single MDB created for one product."""

    product_key: str
    mdb_path: str
    product_code: str = ""
    product_name: str = ""
    template_kind: str = ""
    manufacturer_id: str = ""
    package_id: Any = None
    comgroup_id: Any = None
    program_code: str = ""
    series_id: str = ""
    created_at: str = ""
    #: NOT-NULL boilerplate captured from the template's example rows *before*
    #: they were removed, keyed by table. The primary key is excluded.
    prototypes: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: ``{base_article_code: {"mdb_id": int, "source_ids": [..], "source_codes": [..]}}``
    article_map: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: ``{scheme_name: com_CodeSchemeID}`` for schemes created by this session.
    scheme_map: dict[str, int] = field(default_factory=dict)
    #: ``{workflow: {"status": str, "exported_at": str, "counts": {..}}}``
    workflow_status: dict[str, dict[str, Any]] = field(default_factory=dict)
    version: int = SESSION_VERSION

    def article_ids(self) -> dict[str, int]:
        """``{base_article_code: com_ArticleID}`` retained for later workflows."""
        return {
            code: int(entry["mdb_id"])
            for code, entry in self.article_map.items()
            if entry.get("mdb_id") is not None
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MdbExportSession":
        known = {name for name in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})
