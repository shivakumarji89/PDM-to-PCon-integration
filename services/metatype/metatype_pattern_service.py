"""Metatype creation Step 2: record which kind of Metatype is wanted.

Template Step 2 asks the user to choose between a Polymorphism Metatype and a
Metatype with Childs, and to wait for the answer before continuing. Step 1 (the
series summary) must have been produced first, so a choice is only accepted for
a series with a Step 1 inspection in this session. The choice is returned and
kept in the workflow session for Step 3/4; nothing is written to disk and no
table is read or changed.
"""
from __future__ import annotations

from datetime import datetime, timezone

from models.metatype_pattern import (
    PATTERN_OPTIONS,
    MetatypePattern,
    PatternOption,
    PatternSelection,
    PatternSelectionResult,
    SelectionStatus,
)
from models.metatype_series import InspectionStatus
from services.base_service import BaseService

_SESSION_KEY = "metatype.pattern_selection"


class MetatypePatternService(BaseService):
    """Validate and retain the Step 2 pattern choice."""

    @staticmethod
    def options() -> tuple[PatternOption, ...]:
        return PATTERN_OPTIONS

    @property
    def last_selection(self) -> PatternSelection | None:
        value = self.context.workflow_session(_SESSION_KEY).get("selection")
        return value if isinstance(value, PatternSelection) else None

    def selection_for(self, series: str) -> PatternSelection | None:
        selection = self.last_selection
        return selection if selection is not None and selection.series == series else None

    def can_select(self, series: str) -> bool:
        """True when Step 1 has produced a summary for ``series`` in this session."""
        inspection = self.context.metatype_series_service.last_result
        return (bool(series) and inspection is not None and inspection.target_series == series
                and inspection.status is not InspectionStatus.FAILED)

    def select_pattern(self, series: str, pattern: MetatypePattern | str) -> PatternSelectionResult:
        """Record the user's choice for ``series``; a later call replaces an earlier choice."""
        rejected = PatternSelectionResult(SelectionStatus.REJECTED)
        try:
            chosen = MetatypePattern(pattern)
        except ValueError:
            valid = ", ".join(option.pattern.value for option in PATTERN_OPTIONS)
            rejected.errors.append(f"Unknown pattern {pattern!r}; choose one of: {valid}.")
            return rejected
        inspection = self.context.metatype_series_service.last_result
        if not series.strip():
            rejected.errors.append("A target series is required.")
        elif inspection is None or inspection.target_series != series:
            rejected.errors.append(
                f"Step 1 has not been run for {series!r}: inspect the series before choosing a pattern.")
        elif inspection.status is InspectionStatus.FAILED:
            rejected.errors.append(f"The Step 1 inspection of {series!r} failed; there is no summary to proceed from.")
        if rejected.errors:
            return rejected

        result = PatternSelectionResult(SelectionStatus.SELECTED)
        if inspection.status is InspectionStatus.INSUFFICIENT:
            result.warnings.append("Step 1 found no usable Metatype examples in the series or the reference series.")
        elif inspection.status is InspectionStatus.REFERENCE_ONLY:
            result.warnings.append("Step 1 conventions come from reference series; the target has no examples.")
        if self.context.metatype_series_service.stale_sources(inspection):
            result.warnings.append("Source tables changed since Step 1 ran; consider re-inspecting.")
        result.selection = PatternSelection(
            series=series, pattern=chosen,
            selected_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            inspection_inspected_at=inspection.inspected_at, inspection_status=inspection.status.value,
        )
        self.context.workflow_session(_SESSION_KEY)["selection"] = result.selection
        return result

    @staticmethod
    def summary_text(result: PatternSelectionResult) -> str:
        if result.status is SelectionStatus.SELECTED and result.selection is not None:
            label = next(o.label for o in PATTERN_OPTIONS if o.pattern is result.selection.pattern)
            lines = [f"Step 2 - {result.selection.series}: {label}"]
        else:
            lines = ["Step 2 - no pattern selected"]
        lines += [f"  ERROR {message}" for message in result.errors]
        lines += [f"  WARNING {message}" for message in result.warnings]
        return "\n".join(lines)
