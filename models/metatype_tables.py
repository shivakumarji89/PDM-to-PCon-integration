"""In-memory result of loading one Metatype family's ``go_*.csv`` tables.

Fields and (de)serialisation only. Rows keep the values exactly as read (no
trimming, case change or interpretation); column names come from the family's
own ``mt.inp_descr``. Nothing here resolves relationships or validates data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

TABLES_SCHEMA_VERSION = 1


class TableLoadState(str, Enum):
    VALID = "valid"                # decoded, parsed, every data line had the declared field count
    EMPTY = "empty"                # file exists and is zero bytes
    NO_DATA = "no_data"            # file has content but only comments / blank lines
    MISSING = "missing"            # declared table without a file
    MALFORMED = "malformed"        # one or more lines were rejected (conforming rows are still loaded)
    DECODE_ERROR = "decode_error"  # bytes could not be decoded; no rows loaded
    UNREADABLE = "unreadable"      # OS error, link, or file too large; no rows loaded


class LoadStatus(str, Enum):
    OK = "ok"            # every declared table loaded cleanly, or is absent/empty where that is allowed
    PARTIAL = "partial"  # at least one table could not be loaded cleanly
    FAILED = "failed"    # nothing could be loaded (bad family, directory or schema)


@dataclass
class LoadDiagnostic:
    severity: str  # "error" | "warning"
    code: str
    message: str
    table: str = ""
    file: str = ""
    line: int | None = None


@dataclass
class TableRow:
    """One data line: 1-based source line number and the raw field values."""

    line: int
    values: tuple[str, ...]

    def trimmed(self) -> tuple[str, ...]:
        """Values with surrounding blanks removed (``mt.inp_descr`` declares ``trim``)."""
        return tuple(value.strip(" \t") for value in self.values)


@dataclass
class RejectedLine:
    line: int
    text: str
    code: str
    reason: str


@dataclass
class LoadedTable:
    table: str
    file_name: str
    path: str
    columns: list[str]
    state: TableLoadState
    size_bytes: int | None = None
    encoding: str = ""
    rows: list[TableRow] = field(default_factory=list)
    rejected_lines: list[RejectedLine] = field(default_factory=list)
    comment_lines: int = 0
    blank_lines: int = 0
    diagnostics: list[LoadDiagnostic] = field(default_factory=list)

    def records(self) -> list[dict[str, str]]:
        """Rows as ``{column: raw value}`` dicts (convenience; rows stay authoritative)."""
        return [dict(zip(self.columns, row.values)) for row in self.rows]


@dataclass
class MetatypeFamilyTables:
    repository_root: str
    family_id: str
    loaded_at: str
    loader_version: str
    status: LoadStatus
    directory: str = ""
    directory_path: str = ""
    schema_source: str = ""
    tables: list[LoadedTable] = field(default_factory=list)
    #: ``go_*`` files that ``mt.inp_descr`` does not declare. Listed, never loaded.
    unlisted_go_files: list[str] = field(default_factory=list)
    diagnostics: list[LoadDiagnostic] = field(default_factory=list)
    schema_version: int = TABLES_SCHEMA_VERSION

    def table(self, name: str) -> LoadedTable | None:
        for item in self.tables:
            if item.table == name or item.file_name == name:
                return item
        return None

    def all_diagnostics(self) -> list[LoadDiagnostic]:
        return self.diagnostics + [d for t in self.tables for d in t.diagnostics]

    def to_dict(self) -> dict[str, Any]:
        return _plain(asdict(self))


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value
