"""Structured diagnostics for the OCD engine.

Data problems are reported as :class:`Diagnostic` records, never raised: an
engine call returns its result plus whatever it had to skip, reject or could
not interpret, so no configuration disappears without a recorded reason.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


# Diagnostic codes (stable identifiers; tests and UI key on these).
INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
UNDEFINED_RELATION_RESULT = "UNDEFINED_RELATION_RESULT"
RELATION_PARSE_ERROR = "RELATION_PARSE_ERROR"
UNSUPPORTED_SYNTAX = "UNSUPPORTED_SYNTAX"
RELATION_EVAL_ERROR = "RELATION_EVAL_ERROR"
MISSING_RELATION = "MISSING_RELATION"
MISSING_PROPERTY = "MISSING_PROPERTY"
MISSING_SCHEME = "MISSING_SCHEME"
MISSING_TABLE = "MISSING_TABLE"
NO_VALID_VALUE = "NO_VALID_VALUE"
UNSUPPORTED_ENCODING = "UNSUPPORTED_ENCODING"
ENUMERATION_TRUNCATED = "ENUMERATION_TRUNCATED"
CYCLIC_DEPENDENCY = "CYCLIC_DEPENDENCY"
VARCOND_UNDEFINED = "VARCOND_UNDEFINED"
NO_PRICE_FOR_KEY = "NO_PRICE_FOR_KEY"
NO_BASE_PRICE = "NO_BASE_PRICE"
AMBIGUOUS_PRICE_WINDOW = "AMBIGUOUS_PRICE_WINDOW"
UNSUPPORTED_PRICE_FEATURE = "UNSUPPORTED_PRICE_FEATURE"
UNSUPPORTED_RUNTIME_FIELD = "UNSUPPORTED_RUNTIME_FIELD"
LOAD_ERROR = "LOAD_ERROR"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    severity: Severity = Severity.WARNING
    article: str = ""
    property: str = ""
    value: str = ""
    relation: str = ""
    source: str = ""

    def __str__(self) -> str:
        where = " ".join(
            f"{label}={text}"
            for label, text in (
                ("article", self.article), ("property", self.property),
                ("value", self.value), ("relation", self.relation),
                ("source", self.source),
            )
            if text
        )
        return f"[{self.severity.value}] {self.code}: {self.message}" + (f" ({where})" if where else "")


class DiagnosticSink:
    """Collects diagnostics, keeping counts exact while bounding memory.

    A large product can reject millions of candidates; storing one record per
    rejection would itself be the performance problem. Records beyond
    ``max_records`` are counted per code but not stored.
    """

    def __init__(self, max_records: int = 5000) -> None:
        self.max_records = max_records
        self.items: list[Diagnostic] = []
        self.counts: Counter[str] = Counter()

    def add(self, code: str, message: str, severity: Severity = Severity.WARNING, **where: str) -> None:
        self.counts[code] += 1
        if len(self.items) < self.max_records:
            self.items.append(Diagnostic(code, message, severity, **where))

    def extend(self, other: "DiagnosticSink") -> None:
        for diag in other.items:
            if len(self.items) < self.max_records:
                self.items.append(diag)
        self.counts.update(other.counts)

    def by_code(self, code: str) -> list[Diagnostic]:
        return [d for d in self.items if d.code == code]

    def count(self, code: str) -> int:
        return self.counts[code]

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.items if d.severity is Severity.ERROR]

    def __len__(self) -> int:
        return sum(self.counts.values())

    def __iter__(self):
        return iter(self.items)
