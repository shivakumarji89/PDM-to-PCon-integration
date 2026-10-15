"""Metatype module entry point for loading a family's ``go_*`` tables.

Qt-free wrapper the Metatype module calls. It picks the repository root (the
latest scan's root, else the configured one), runs the read-only loader and
keeps the latest result for the session.
"""
from __future__ import annotations

from pathlib import Path

from models.metatype_tables import MetatypeFamilyTables
from services.base_service import BaseService
from services.metatype.metatype_table_loader import MetatypeTableLoader

_SESSION_KEY = "metatype.family_tables"


class MetatypeTableLoaderService(BaseService):
    """Load and retain one family's Metatype tables."""

    @property
    def last_result(self) -> MetatypeFamilyTables | None:
        result = self.context.workflow_session(_SESSION_KEY).get("result")
        return result if isinstance(result, MetatypeFamilyTables) else None

    def default_root(self) -> str:
        scan = self.context.metatype_repository_service.last_result
        return scan.repository_root if scan is not None else self.context.config.metatype_repository_root

    def load_family(
        self,
        family_id: str,
        root: str | Path | None = None,
        directory: str | None = None,
        fallback_encoding: str | None = None,
    ) -> MetatypeFamilyTables:
        result = MetatypeTableLoader(fallback_encoding).load_family(
            self.default_root() if root is None else root, family_id, directory)
        self.context.workflow_session(_SESSION_KEY)["result"] = result
        return result

    @staticmethod
    def summary_text(result: MetatypeFamilyTables) -> str:
        """Plain-text summary (UIs should consume the model, not this)."""
        lines = [f"Tables of {result.family_id}/{result.directory or '?'} - {result.status.value}"]
        for item in result.diagnostics:
            lines.append(f"  {item.severity.upper()} [{item.code}] {item.message}")
        for table in result.tables:
            detail = f"{len(table.rows)} row(s)" if table.rows or table.state.value in ("valid", "malformed") else ""
            if table.rejected_lines:
                detail += f", {len(table.rejected_lines)} rejected line(s)"
            lines.append(f"  {table.file_name:<28} {table.state.value:<13} {detail}".rstrip())
        if result.unlisted_go_files:
            lines.append("  Not loaded (not declared): " + ", ".join(result.unlisted_go_files))
        return "\n".join(lines)
