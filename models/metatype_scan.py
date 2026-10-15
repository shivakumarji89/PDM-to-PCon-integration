"""Result model for the read-only Metatype repository scan.

Fields and (de)serialisation only - no filesystem access, no Qt. The scanner
fills these in; UI and exports consume them.

Terminology follows ``docs/02_Domain/Engineering/Metatype.md``. In the ``hmx``
repository a *series* and a *family* are the same directory (``hmx/<name>/``);
there is no directory level above it, so both identifiers carry the same value.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

SCAN_RESULT_SCHEMA_VERSION = 1


class BuildStatus(str, Enum):
    """Evidence-based build classification of a family or numbered directory."""

    BUILT = "built"
    UNBUILT = "unbuilt"
    UNCERTAIN = "uncertain"


class EntryKind(str, Enum):
    """What a directory directly under the HMX root is, judged from file evidence."""

    #: Metatype or OFML product-data files were found in a numbered directory.
    PRODUCT_FAMILY = "product_family"
    #: No such evidence (non-product folder, empty folder, or unexpected layout).
    #: Deliberately *not* called "non-product": no exclusion rule is assumed.
    UNCLASSIFIED = "unclassified"


class ScanStatus(str, Enum):
    """Overall outcome of a scan."""

    OK = "ok"            # root scanned, no errors recorded
    PARTIAL = "partial"  # root scanned, but some directories/files raised errors
    FAILED = "failed"    # root invalid or unreadable; nothing was scanned


class TableState(str, Enum):
    PRESENT = "present"      # file exists and has content
    ZERO_BYTE = "zero_byte"  # file exists but is empty
    MISSING = "missing"      # expected table has no file


@dataclass
class ScanIssue:
    """A warning or error that was recorded instead of being dropped."""

    code: str
    message: str
    path: str = ""


@dataclass
class GoFileRecord:
    """One ``go_*`` file found in a numbered directory."""

    name: str
    path: str
    size_bytes: int | None
    #: ``go_<table>.csv`` whose table name is declared by ``mt.inp_descr``.
    is_declared_table: bool = False
    #: Declared table name, or ``""`` for files that are not declared tables
    #: (backups, ``.new`` copies, variants, tables ``mt.inp_descr`` omits).
    table: str = ""
    state: TableState = TableState.PRESENT


@dataclass
class ExpectedTable:
    """A table declared by ``mt.inp_descr`` and its on-disk state."""

    table: str
    file_name: str
    state: TableState
    path: str = ""
    size_bytes: int | None = None
    #: Table is marked "(obsolete)" in the manual (MT_1.18.0).
    obsolete: bool = False


@dataclass
class BuildIndicator:
    """One build-related file and whether it was found."""

    name: str
    present: bool
    path: str = ""
    size_bytes: int | None = None
    note: str = ""


@dataclass
class ClassificationEvidence:
    """A single fact that supported (or complicated) a classification."""

    indicator: str
    observed: str
    supports: str  # "built" | "unbuilt" | "uncertain" | "info"


@dataclass
class Classification:
    status: BuildStatus
    #: Machine-readable id of the rule that produced ``status``.
    rule: str
    summary: str
    evidence: list[ClassificationEvidence] = field(default_factory=list)


@dataclass
class NumberedDirectoryScan:
    """Inspection of ``hmx/<family>/<number>/``."""

    name: str
    path: str
    classification: Classification | None = None
    go_files: list[GoFileRecord] = field(default_factory=list)
    #: ``"mt.inp_descr"`` when the expected table set was read from it; ``""``
    #: when it is absent/unreadable, so the set is unknown rather than assumed
    #: (``expected_tables`` is then empty).
    expected_tables_source: str = ""
    expected_tables: list[ExpectedTable] = field(default_factory=list)
    missing_tables: list[str] = field(default_factory=list)
    zero_byte_tables: list[str] = field(default_factory=list)
    build_indicators: list[BuildIndicator] = field(default_factory=list)
    #: ``*.ebase`` files that are not Metatype outputs (e.g. ``odb.ebase``).
    other_ebase_files: list[str] = field(default_factory=list)
    #: OFML product-data files (odb/ofml schema or compiled databases) found here.
    product_data_files: list[str] = field(default_factory=list)
    warnings: list[ScanIssue] = field(default_factory=list)
    errors: list[ScanIssue] = field(default_factory=list)


@dataclass
class FamilyScan:
    series_id: str
    family_id: str
    path: str
    classification: Classification | None = None
    entry_kind: EntryKind = EntryKind.UNCLASSIFIED
    entry_kind_evidence: list[ClassificationEvidence] = field(default_factory=list)
    numbered_directories: list[NumberedDirectoryScan] = field(default_factory=list)
    #: Non-numbered subdirectories (e.g. ``ANY``/``EURO``) - listed, never entered.
    other_directories: list[str] = field(default_factory=list)
    warnings: list[ScanIssue] = field(default_factory=list)
    errors: list[ScanIssue] = field(default_factory=list)


@dataclass
class ScanSummary:
    #: Counts below cover confirmed product families only; every other root
    #: directory is reported under ``unclassified_count``.
    series_count: int = 0
    family_count: int = 0
    unclassified_count: int = 0
    built: int = 0
    unbuilt: int = 0
    uncertain: int = 0
    families_with_errors: int = 0
    families_with_warnings: int = 0


@dataclass
class MetatypeScanResult:
    repository_root: str
    scanned_at: str
    scanner_version: str
    status: ScanStatus
    schema_version: int = SCAN_RESULT_SCHEMA_VERSION
    #: Human-readable statement of what was and was not traversed.
    scan_policy: list[str] = field(default_factory=list)
    #: Product-family ids only (see ``EntryKind``).
    series: list[str] = field(default_factory=list)
    #: Every candidate directory under the root, each tagged with ``entry_kind``.
    families: list[FamilyScan] = field(default_factory=list)
    summary: ScanSummary = field(default_factory=ScanSummary)
    errors: list[ScanIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-compatible dict (enums become their string values)."""
        return _plain(asdict(self))

    def family(self, family_id: str) -> FamilyScan | None:
        for item in self.families:
            if item.family_id == family_id:
                return item
        return None


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value
