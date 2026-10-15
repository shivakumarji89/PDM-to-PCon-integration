"""Metatype creation Step 2: the kind of Metatype the user wants.

Source: POLYMORPHIC_METATYPE_CREATION_TEMPLATE_04092026.md, "Step 2 - Ask which
kind of Metatype is wanted". The template offers exactly two choices and says
the answer drives the Step 4 branch. Fields only; no workflow logic.

The option wording is the template's own. It is deliberately NOT mapped to mode
bits or tables here: how polymorphism is encoded (mode bit 4 vs the real data)
is an open owner decision.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

PATTERN_SCHEMA_VERSION = 1


class MetatypePattern(str, Enum):
    POLYMORPHISM = "polymorphism"
    WITH_CHILDS = "with_childs"


@dataclass(frozen=True)
class PatternOption:
    pattern: MetatypePattern
    label: str
    description: str


#: Wording from the template, Step 2.
PATTERN_OPTIONS: tuple[PatternOption, ...] = (
    PatternOption(
        MetatypePattern.POLYMORPHISM, "Polymorphism Metatype",
        "Articles switch/swap based on a Metatype Property (no parent/child structure, "
        "just article substitution driven by a property value)."),
    PatternOption(
        MetatypePattern.WITH_CHILDS, "Metatype with Childs",
        "A parent Metatype that attaches/controls child articles."),
)


class SelectionStatus(str, Enum):
    SELECTED = "selected"
    REJECTED = "rejected"


@dataclass
class PatternSelection:
    """The recorded Step 2 answer, handed to the Step 4 branch."""

    series: str
    pattern: MetatypePattern
    selected_at: str
    #: Step 1 result the choice was made on (``SeriesInspection.inspected_at`` / status).
    inspection_inspected_at: str
    inspection_status: str
    schema_version: int = PATTERN_SCHEMA_VERSION


@dataclass
class PatternSelectionResult:
    status: SelectionStatus
    selection: PatternSelection | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

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
