"""Metatype module entry point for Step 1, ``inspect_series``.

Qt-free wrapper: picks the repository root (as the table loader service does),
runs the read-only :class:`SeriesInspector` and keeps the latest result for the
session so later creation steps can read it. The result is not written to disk:
the template only asks for a summary shown to the user before Step 2.
"""
from __future__ import annotations

from pathlib import Path

from models.metatype_series import SeriesInspection
from services.base_service import BaseService
from services.metatype.series_inspector import SeriesInspector, format_inspection_summary

_SESSION_KEY = "metatype.series_inspection"


class MetatypeSeriesService(BaseService):
    """Run and retain the series-conventions inspection."""

    def __init__(self, context) -> None:
        super().__init__(context)
        self._inspector = SeriesInspector()

    @property
    def last_result(self) -> SeriesInspection | None:
        result = self.context.workflow_session(_SESSION_KEY).get("result")
        return result if isinstance(result, SeriesInspection) else None

    def inspect_series(
        self,
        series: str,
        root: str | Path | None = None,
        directory: str | None = None,
        reference_series: tuple[str, ...] | list[str] | None = None,
    ) -> SeriesInspection:
        """Inspect ``series`` and remember the result. Always re-reads the files (explicit refresh)."""
        root = self.context.metatype_table_loader_service.default_root() if root is None else root
        result = self._inspector.inspect_series(root, series, directory, reference_series)
        self.context.workflow_session(_SESSION_KEY)["result"] = result
        return result

    def stale_sources(self, result: SeriesInspection | None = None) -> list[str]:
        """Source files that changed since ``result`` (default: the latest) was produced."""
        result = result or self.last_result
        return self._inspector.check_staleness(result) if result is not None else []

    @staticmethod
    def summary_text(result: SeriesInspection) -> str:
        return format_inspection_summary(result)
