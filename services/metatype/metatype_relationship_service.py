"""Metatype module entry point for relationship resolution.

Qt-free wrapper: loads a family's tables through the table loader service (or
takes tables you already loaded), resolves them, and keeps the latest report.
"""
from __future__ import annotations

from models.metatype_relationships import (
    DuplicateStatus, MetatypeRelationshipReport, RelationshipStatus,
)
from models.metatype_tables import MetatypeFamilyTables
from services.base_service import BaseService
from services.metatype.metatype_relationship_resolver import MetatypeRelationshipResolver

_SESSION_KEY = "metatype.relationship_report"


class MetatypeRelationshipService(BaseService):
    """Resolve and retain one family's table relationships."""

    def __init__(self, context) -> None:
        super().__init__(context)
        self._resolver = MetatypeRelationshipResolver()

    @property
    def last_result(self) -> MetatypeRelationshipReport | None:
        result = self.context.workflow_session(_SESSION_KEY).get("result")
        return result if isinstance(result, MetatypeRelationshipReport) else None

    def resolve(self, tables: MetatypeFamilyTables) -> MetatypeRelationshipReport:
        report = self._resolver.resolve(tables)
        self.context.workflow_session(_SESSION_KEY)["result"] = report
        return report

    def resolve_family(self, family_id: str, **load_options) -> MetatypeRelationshipReport:
        """Load ``family_id`` with the table loader service, then resolve it."""
        tables = self.context.metatype_table_loader_service.load_family(family_id, **load_options)
        return self.resolve(tables)

    @staticmethod
    def summary_text(report: MetatypeRelationshipReport) -> str:
        """Plain-text summary (UIs should consume the model, not this)."""
        s = report.summary
        lines = [f"Relationships of {report.family_id}/{report.directory or '?'} - {report.status.value}"]
        lines += [f"  {message}" for message in report.messages]
        if report.status.value == "failed":
            return "\n".join(lines)
        lines.append(
            f"  {s.relationships} rules: {s.resolved} resolved, {s.unresolved} unresolved "
            f"({s.unresolved_references} reference(s)), {s.no_references} nothing to check, "
            f"{s.not_checkable} not checkable")
        lines.append(f"  {s.duplicate_checks} key checks: {s.duplicate_groups} duplicate group(s), "
                     f"{s.duplicate_checks_not_checkable} not checkable")
        for item in report.relationships:
            if item.status is RelationshipStatus.UNRESOLVED:
                lines.append(f"  UNRESOLVED {item.id}: {item.unresolved_count} of {item.reference_count}")
            elif item.status is RelationshipStatus.NOT_CHECKABLE:
                lines.append(f"  NOT CHECKABLE {item.id}: {item.reason}")
        for item in report.duplicate_checks:
            if item.status is DuplicateStatus.DUPLICATES:
                lines.append(f"  DUPLICATES {item.id}: {item.duplicate_groups} group(s)")
            elif item.status is DuplicateStatus.NOT_CHECKABLE:
                lines.append(f"  NOT CHECKABLE {item.id}: {item.reason}")
        return "\n".join(lines)
