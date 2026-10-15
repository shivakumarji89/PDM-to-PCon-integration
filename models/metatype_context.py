"""Typed, session-owned state for the Metatype creation workflow.

This model deliberately contains no Qt dependencies. It temporarily implements
MutableMapping for the existing service's internal key access while callers are
migrated to typed attributes; the workflow session stores only this context.
"""
from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from dataclasses import dataclass, field
from typing import Any

from models.metatype_creation import (
    ArticleRef, ConfirmedSpecification, PolymorphismBranch, PropertyIdentity,
    TranslationDraft, Translations, ValueValidity, ValueValidityDraft,
)
from models.metatype_pattern import PatternSelection, SelectionStatus
from models.metatype_series import SeriesInspection


@dataclass
class MetatypeCreationContext(MutableMapping[str, object]):
    """All state for one creation session, independent of Repository Analysis."""

    schema_version: int = 1
    revision: int = 0
    series: str = ""
    inspection: SeriesInspection | None = None
    pattern_selection: PatternSelection | None = None
    pattern_status: SelectionStatus | None = None
    pattern_warnings: list[str] = field(default_factory=list)
    identity: PropertyIdentity | None = None
    branch: PolymorphismBranch | None = None
    validity: ValueValidity | None = None
    validity_draft: ValueValidityDraft | None = None
    translations: Translations | None = None
    translation_draft: TranslationDraft | None = None
    confirmation: ConfirmedSpecification | None = None
    known_articles: list[ArticleRef] | None = None
    pending_series: str | None = None

    _FIELDS = (
        "series", "inspection", "pattern_selection", "pattern_status", "pattern_warnings",
        "identity", "branch", "validity", "validity_draft", "translations",
        "translation_draft", "confirmation", "known_articles", "pending_series",
    )

    def __getitem__(self, key: str) -> object:
        if key not in self._FIELDS:
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key: str, value: object) -> None:
        if key not in self._FIELDS:
            raise KeyError(key)
        setattr(self, key, value)

    def __delitem__(self, key: str) -> None:
        if key not in self._FIELDS:
            raise KeyError(key)
        setattr(self, key, None if key not in ("series", "pattern_warnings") else
                ("" if key == "series" else []))

    def __iter__(self) -> Iterator[str]:
        return iter(self._FIELDS)

    def __len__(self) -> int:
        return len(self._FIELDS)

    def reset_for_series(self, series: str) -> None:
        """Reset answer state explicitly when the user chooses to discard this series."""
        self.revision += 1
        self.series = series
        self.inspection = None
        self.pattern_selection = None
        self.pattern_status = None
        self.pattern_warnings = []
        self.identity = None
        self.branch = None
        self.validity = None
        self.validity_draft = None
        self.translations = None
        self.translation_draft = None
        self.confirmation = None
        self.known_articles = None
        self.pending_series = None

    def touch(self) -> None:
        """Advance the monotonic context revision after a meaningful accepted edit."""
        self.revision += 1

    def snapshot(self) -> dict[str, Any]:
        """Small diagnostic summary; intentionally excludes mutable answer contents."""
        return {
            "schema_version": self.schema_version,
            "revision": self.revision,
            "series": self.series,
            "has_inspection": self.inspection is not None,
            "has_identity": self.identity is not None,
            "has_branch": self.branch is not None,
            "has_validity": self.validity is not None,
            "has_translations": self.translations is not None,
            "has_confirmation": self.confirmation is not None,
            "pending_series": self.pending_series,
        }
