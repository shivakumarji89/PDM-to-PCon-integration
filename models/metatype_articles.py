"""In-memory, read-only reconciliation of a series' articles with their Metatype assignments.

Fields only. Values are the raw strings read by the table loader (never trimmed, generated or
re-keyed); column names come from the family's own ``mt.inp_descr``. ``status`` is derived in
memory and is never stored in a repository file.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from models.metatype_tables import LoadDiagnostic, MetatypeFamilyTables

STATUS_COLUMN = "status"

MAPPED = "Mapped"
NEEDS_ASSIGNMENT = "Needs assignment"
MAPPING_UNAVAILABLE = "Mapping unavailable"
CONFLICT = "Conflicting mappings"
AMBIGUOUS_IDENTITY = "Ambiguous identity"
INVALID_IDENTITY = "Invalid identity"


class ReconciliationStatus(str, Enum):
    COMPLETE = "complete"  # every source loaded cleanly and every field needed for the reconciliation exists
    PARTIAL = "partial"    # rows are shown, but a source problem or unavailable field makes them incomplete
    FAILED = "failed"      # the article list itself could not be loaded


@dataclass
class MappingSource:
    """One source record that assigns Metatype fields to an article (kept for diagnostics)."""

    file: str
    line: int
    values: dict[str, str]
    table: str = ""


@dataclass
class ArticleRow:
    #: Raw values by column name (article columns plus mapping columns that exist in the schema).
    values: dict[str, str]
    source_file: str
    source_line: int
    #: (manufacturer, program, article) with blanks trimmed for comparison only; ``None`` if not derivable.
    identity: tuple[str, str, str] | None
    status: str
    mapping_sources: list[MappingSource] = field(default_factory=list)


@dataclass
class ArticleReconciliation:
    series: str
    status: ReconciliationStatus
    directory: str = ""
    #: Columns shown by the table, in schema order, ``status`` excluded.
    columns: list[str] = field(default_factory=list)
    #: Roles (``metatypeid``, ``childparentid``, ``configid``) the schema does not declare.
    unavailable_fields: list[str] = field(default_factory=list)
    #: role -> declared column of the article table: literal names, or the verified positional aliases
    #: (id / prm_key / chprm_key, see ``ARTICLE_COLUMN_ALIASES`` in the article service).
    roles: dict[str, str] = field(default_factory=dict)
    #: Identifier sets read from the loaded tables, used only to *report* dangling references:
    #: ``metatype_ids`` (go_types.id), ``config_keys`` (go_properties.key), ``child_keys`` (go_childprops.key).
    #: A key is absent when its table could not be read, so "unknown" is never mistaken for "dangling".
    references: dict[str, frozenset[str]] = field(default_factory=dict)
    article_table: str = ""
    mapping_tables: list[str] = field(default_factory=list)
    rows: list[ArticleRow] = field(default_factory=list)
    #: Mapping records whose article identity matches no article (never dropped).
    unmatched_mappings: list[MappingSource] = field(default_factory=list)
    diagnostics: list[LoadDiagnostic] = field(default_factory=list)
    #: The loader's own result, untouched, so the original diagnostics stay inspectable.
    loader_result: MetatypeFamilyTables | None = None

    @property
    def headers(self) -> list[str]:
        return [*self.columns, STATUS_COLUMN]

    def errors(self) -> list[LoadDiagnostic]:
        return [d for d in self.diagnostics if d.severity == "error"]
