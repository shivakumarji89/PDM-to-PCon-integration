"""Result of inspecting one HMX series' existing Metatype conventions (creation Step 1).

Fields and (de)serialisation only. Every finding carries :class:`Evidence`
(source table, line number and the raw values) so a later step can show where
a convention came from. Nothing here interprets or validates Metatype rules.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

SERIES_SCHEMA_VERSION = 1


class InspectionStatus(str, Enum):
    OK = "ok"                        # the target series has Metatype examples
    REFERENCE_ONLY = "reference_only"  # target has none; conventions come from reference series
    INSUFFICIENT = "insufficient"    # neither the target nor any reference gave usable examples
    FAILED = "failed"                # the request itself was invalid (no family id / root)


class SeriesStatus(str, Enum):
    OK = "ok"                # at least one metatype was found in go_types
    NO_EXAMPLES = "no_examples"  # tables loaded, but go_types defines no metatype
    FAILED = "failed"        # the family could not be loaded


@dataclass
class Evidence:
    """One source row: table, 1-based line, and the trimmed values of that row."""

    table: str
    line: int
    values: tuple[str, ...]


@dataclass
class SourceTable:
    """A table the inspection read, with enough to tell later whether it changed."""

    table: str
    file: str
    path: str
    state: str                       # TableLoadState value, or "not_declared"
    size_bytes: int | None = None
    modified_ns: int | None = None   # os.stat st_mtime_ns when inspected
    row_count: int = 0
    rejected_line_count: int = 0
    note: str = ""


@dataclass
class CountedValue:
    value: str
    count: int
    evidence: list[Evidence] = field(default_factory=list)  # first few rows only


@dataclass
class MetatypeSummary:
    id: str
    property_count: int              # rows that have a format (real properties)
    setting_count: int               # rows without a format (e.g. GType, GMode)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ModeUsage:
    mode: int
    count: int
    bits: list[int]
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class PropertyRef:
    metatype: str
    name: str
    mode: int
    evidence: Evidence


@dataclass
class TypesConventions:
    metatype_count: int = 0
    metatypes: list[MetatypeSummary] = field(default_factory=list)
    metatype_id_prefixes: list[CountedValue] = field(default_factory=list)
    #: Prefix groups of the series' own properties. ``na`` (native wrapper) properties are left out:
    #: their name is 'G' + the native name (Metatype.md section 5.3), so they carry no series prefix.
    property_prefixes: list[CountedValue] = field(default_factory=list)
    native_wrapper_count: int = 0
    native_wrapper_examples: list[Evidence] = field(default_factory=list)
    #: ``G<FAMILY>_`` as the template writes it; informational, not enforced.
    template_prefix: str = ""
    properties_following_template_prefix: int = 0
    #: Rows without a format (GType, GMode, ... in the real data): metatype-level settings.
    settings: list[CountedValue] = field(default_factory=list)   # value = "name = default"
    formats: list[CountedValue] = field(default_factory=list)
    modes: list[ModeUsage] = field(default_factory=list)
    bit_counts: dict[int, int] = field(default_factory=dict)
    #: Properties per documented mode bit (Metatype.md section 5.4).
    polymorphism_properties: list[PropertyRef] = field(default_factory=list)  # bit 4
    child_properties: list[PropertyRef] = field(default_factory=list)         # bit 8
    ordered_properties: list[PropertyRef] = field(default_factory=list)       # bit 128
    value_limited_properties: list[PropertyRef] = field(default_factory=list)  # bit 8192
    non_numeric_modes: list[Evidence] = field(default_factory=list)
    #: Every go_types row (metatype settings and properties alike), so later steps can check
    #: a proposed property name against what the series already defines. values = the row.
    defined_properties: list[Evidence] = field(default_factory=list)


@dataclass
class PropValuesConvention:
    row_count: int = 0
    rows_with_condition: int = 0
    #: One entry per (metatype id, property): value = "id / name", count = rows.
    properties: list[CountedValue] = field(default_factory=list)
    #: Properties flagged 8192 in go_types that have no go_propvalues row, and vice versa.
    flagged_without_rows: list[str] = field(default_factory=list)
    rows_without_flag: list[str] = field(default_factory=list)
    condition_examples: list[Evidence] = field(default_factory=list)


@dataclass
class PropOrderConvention:
    row_count: int = 0
    entries: list[Evidence] = field(default_factory=list)    # every row: values = (value, number)
    min_number: int | None = None
    max_number: int | None = None
    #: Most common positive difference between consecutive numbers (e.g. 10).
    common_step: int | None = None
    non_numeric: list[Evidence] = field(default_factory=list)


@dataclass
class ChildrenConvention:
    row_count: int = 0
    distinct_keys: int = 0
    key_prefixes: list[CountedValue] = field(default_factory=list)
    #: Keys that appear on several rows (conditional alternatives).
    repeated_keys: list[CountedValue] = field(default_factory=list)
    rows_with_condition: int = 0
    manufacturers: list[CountedValue] = field(default_factory=list)
    programs: list[CountedValue] = field(default_factory=list)
    condition_examples: list[Evidence] = field(default_factory=list)


@dataclass
class SeriesConventions:
    family_id: str
    status: SeriesStatus
    directory: str = ""
    sources: list[SourceTable] = field(default_factory=list)
    types: TypesConventions = field(default_factory=TypesConventions)
    propvalues: PropValuesConvention = field(default_factory=PropValuesConvention)
    proporder: PropOrderConvention = field(default_factory=PropOrderConvention)
    children: ChildrenConvention = field(default_factory=ChildrenConvention)
    #: Markdown files that may describe prior Metatype work (names only; not read).
    docs_files: list[str] = field(default_factory=list)
    #: Human-readable reasons why the data is missing, partial or insufficient.
    notes: list[str] = field(default_factory=list)


@dataclass
class SeriesInspection:
    repository_root: str
    target_series: str
    inspected_at: str
    inspector_version: str
    status: InspectionStatus
    target: SeriesConventions | None = None
    #: Why reference series were consulted ("" when they were not).
    reference_reason: str = ""
    references: list[SeriesConventions] = field(default_factory=list)
    #: Decisions the sources do not settle; carried so no caller mistakes them for fact.
    unresolved: list[str] = field(default_factory=list)
    #: Tables deliberately not read (go_texts: encoding undecided).
    excluded_tables: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    schema_version: int = SERIES_SCHEMA_VERSION

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
