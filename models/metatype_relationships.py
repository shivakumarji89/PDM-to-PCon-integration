"""Typed result of resolving references between one family's Metatype tables.

Fields and (de)serialisation only. A report says which documented/observed
references were checked, how many resolved, and exactly which did not. It does
not judge whether a Metatype is *correct* (that is domain validation).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

RELATIONSHIP_SCHEMA_VERSION = 1


class RelationshipStatus(str, Enum):
    RESOLVED = "resolved"              # references existed and every one resolved
    UNRESOLVED = "unresolved"          # at least one reference has no target
    NO_REFERENCES = "no_references"    # source table loaded but holds nothing to check
    NOT_CHECKABLE = "not_checkable"    # a needed table/column is missing or was not loaded


class DuplicateStatus(str, Enum):
    UNIQUE = "unique"
    DUPLICATES = "duplicates"
    NOT_CHECKABLE = "not_checkable"


class ReportStatus(str, Enum):
    OK = "ok"                # everything checkable was checked and is clean
    ISSUES = "issues"        # unresolved references and/or duplicate keys were found
    INCOMPLETE = "incomplete"  # no issues found, but some checks could not run or ran on partial data
    FAILED = "failed"        # no tables were available at all


@dataclass(frozen=True)
class RelationshipSpec:
    """One reference rule: ``source_table.source_columns`` must exist in ``target_table.target_columns``."""

    id: str
    description: str
    source_table: str
    source_columns: tuple[str, ...]
    target_table: str
    target_columns: tuple[str, ...]
    #: "documented" = stated by MT_1.18.0; "observed" = shown by repository data and
    #: the project notes but not stated explicitly in the manual.
    basis: str
    #: Comma-separated (ID_List) source columns, expanded one reference per item.
    list_columns: tuple[str, ...] = ()
    #: Only rows where ``column`` is one of the values are references: (column, values).
    only_when: tuple[str, tuple[str, ...]] | None = None
    #: Rows where ``column`` is one of the values are not references: (column, values).
    except_when: tuple[str, tuple[str, ...]] | None = None
    #: Source values that are legitimately not table keys (e.g. ``_native_``, ``*``): (column, values).
    ignore_values: tuple[str, tuple[str, ...]] | None = None
    #: A blank value in this source column means "any" instead of "no reference".
    wildcard_blank: str | None = None
    #: Name of a hand-written evaluator for rules that need a join.
    custom: str = ""
    note: str = ""
    severity: str = "error"


@dataclass(frozen=True)
class DuplicateSpec:
    id: str
    description: str
    table: str
    key_columns: tuple[str, ...]
    basis: str  # "documented" | "inferred"
    severity: str = "warning"
    note: str = ""


@dataclass
class RelationshipFinding:
    code: str  # UNRESOLVED_REFERENCE | DUPLICATE_KEY
    severity: str
    rule: str
    table: str
    file: str
    line: int | None
    columns: tuple[str, ...]
    #: The cell values exactly as read from the file (a list cell stays whole).
    values: tuple[str, ...]
    message: str
    #: The trimmed key that was looked up (one item of a list cell).
    reference: tuple[str, ...] = ()
    #: True when the target table was only partly loaded, so the reference may
    #: exist in a rejected line.
    uncertain: bool = False
    #: Other source lines involved (duplicates).
    related_lines: list[int] = field(default_factory=list)


@dataclass
class RelationshipResult:
    id: str
    description: str
    basis: str
    source: str
    target: str
    status: RelationshipStatus
    reference_count: int = 0
    resolved_count: int = 0
    unresolved_count: int = 0
    #: Rows with a blank/ignored key that do not carry a reference.
    skipped_count: int = 0
    reason: str = ""
    #: Tables used by this rule that were only partly loaded.
    partial_tables: list[str] = field(default_factory=list)
    findings_truncated: bool = False
    note: str = ""


@dataclass
class DuplicateResult:
    id: str
    description: str
    table: str
    key_columns: tuple[str, ...]
    basis: str
    status: DuplicateStatus
    row_count: int = 0
    duplicate_groups: int = 0
    #: Rows beyond the first of each group.
    extra_rows: int = 0
    reason: str = ""
    partial: bool = False
    findings_truncated: bool = False


@dataclass
class ReportSummary:
    relationships: int = 0
    resolved: int = 0
    unresolved: int = 0
    no_references: int = 0
    not_checkable: int = 0
    unresolved_references: int = 0
    duplicate_checks: int = 0
    duplicate_groups: int = 0
    duplicate_checks_not_checkable: int = 0
    findings: int = 0


@dataclass
class MetatypeRelationshipReport:
    repository_root: str
    family_id: str
    directory: str
    resolved_at: str
    resolver_version: str
    status: ReportStatus
    relationships: list[RelationshipResult] = field(default_factory=list)
    duplicate_checks: list[DuplicateResult] = field(default_factory=list)
    findings: list[RelationshipFinding] = field(default_factory=list)
    summary: ReportSummary = field(default_factory=ReportSummary)
    #: Table-level state copied from the load (name -> state), for context.
    table_states: dict[str, str] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    schema_version: int = RELATIONSHIP_SCHEMA_VERSION

    def relationship(self, rule_id: str) -> RelationshipResult | None:
        return next((r for r in self.relationships if r.id == rule_id), None)

    def duplicate_check(self, rule_id: str) -> DuplicateResult | None:
        return next((r for r in self.duplicate_checks if r.id == rule_id), None)

    def findings_for(self, rule_id: str) -> list[RelationshipFinding]:
        return [f for f in self.findings if f.rule == rule_id]

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
