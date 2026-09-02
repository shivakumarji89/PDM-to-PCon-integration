"""Product Information Page (PIP) records.

A :class:`PipProduct` is one product's PIP sheet parsed from the vocabulary
workbook: the ordered properties (the ``Feature 1..N`` columns), each with its
values and order codes, plus the base/tail separator and engineering notes. It
is the manufacturer's authoritative spec, used to validate Class Creation.
Fields only - no logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PipValue:
    """One property value and its order code, as printed on the PIP."""

    value: str = ""
    code: str = ""


@dataclass
class PipProperty:
    """One PIP property (a ``Feature`` column): its name, ordered values and
    codes. ``is_separator`` marks the literal ``.`` between the base article
    number and the parametric tail."""

    name: str = ""
    order: int = 0
    values: list[PipValue] = field(default_factory=list)
    is_separator: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class PipProduct:
    """One product's PIP: title + ordered properties (left-to-right feature
    order = the article-code assembly order)."""

    title: str = ""
    sheet: str = ""
    properties: list[PipProperty] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class PipDiffItem:
    """One finding from comparing a ground-truth PIP against Class Creation."""

    severity: str = "error"   # "error" | "warning" | "info"
    category: str = ""        # missing_property / extra_property / split /
    #                            missing_value / extra_value / code_mismatch /
    #                            missing_code / order / head_pending
    message: str = ""


@dataclass
class PipDiff:
    """The result of diffing a PIP (expected) against Class Creation (actual)."""

    title: str = ""
    items: list[PipDiffItem] = field(default_factory=list)

    @property
    def errors(self) -> list[PipDiffItem]:
        return [i for i in self.items if i.severity == "error"]

    @property
    def warnings(self) -> list[PipDiffItem]:
        return [i for i in self.items if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        """Pass = no hard errors (warnings/info are advisory)."""
        return not self.errors

    def summary(self) -> str:
        return f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)"

