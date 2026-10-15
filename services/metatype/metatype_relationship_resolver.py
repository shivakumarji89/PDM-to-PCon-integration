"""Resolve references between the tables of one loaded Metatype family.

Pure and filesystem-free: it consumes a :class:`MetatypeFamilyTables` produced
by the table loader and a list of rules (``relationship_specs``). It reports
unresolved references, duplicate keys, and rules that could not be checked
because a table was missing, unreadable or only partly loaded. It does not
validate Metatype semantics (modes, formats, conditions, reachability).

Matching is exact and case-sensitive (identifiers are case-sensitive per
MT_1.18.0 section 2) on values with surrounding blanks removed (``mt.inp_descr``
declares ``trim``). Raw values are kept in the findings.
"""
from __future__ import annotations

import itertools
from datetime import datetime, timezone

from models.metatype_relationships import (
    DuplicateResult,
    DuplicateSpec,
    DuplicateStatus,
    MetatypeRelationshipReport,
    RelationshipFinding,
    RelationshipResult,
    RelationshipSpec,
    RelationshipStatus,
    ReportStatus,
    ReportSummary,
)
from models.metatype_tables import LoadedTable, MetatypeFamilyTables, TableLoadState
from services.metatype.relationship_specs import DUPLICATES, RELATIONSHIPS

RESOLVER_VERSION = "1.0.0"
#: Counts stay exact; only the stored finding list is capped per rule.
MAX_FINDINGS_PER_RULE = 500

_USABLE = {TableLoadState.VALID, TableLoadState.EMPTY, TableLoadState.NO_DATA, TableLoadState.MALFORMED}


class _Access:
    """A table as the resolver may use it."""

    def __init__(self, name: str, table: LoadedTable | None) -> None:
        self.name = name
        self.table = table
        self.usable = table is not None and table.state in _USABLE
        #: Some lines were rejected while loading, so rows may be missing.
        self.partial = table is not None and table.state is TableLoadState.MALFORMED
        if table is None:
            self.reason = f"{name} is not declared by mt.inp_descr"
        elif not self.usable:
            self.reason = f"{table.file_name} is {table.state.value}"
        else:
            self.reason = ""
        self._index = {c: i for i, c in enumerate(table.columns)} if table is not None else {}

    @property
    def file(self) -> str:
        return self.table.file_name if self.table is not None else f"{self.name}.csv"

    def missing_columns(self, columns) -> list[str]:
        return [c for c in columns if c not in self._index]

    def rows(self):
        """Yield ``(line, {column: trimmed value}, raw tuple)`` for every loaded row."""
        for row in self.table.rows:
            trimmed = row.trimmed()
            yield row.line, {c: trimmed[i] for c, i in self._index.items()}, row.values

    def raw(self, raw_values: tuple[str, ...], columns) -> tuple[str, ...]:
        return tuple(raw_values[self._index[c]] for c in columns)


def _items(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


class MetatypeRelationshipResolver:
    """Check the configured rules against one family's loaded tables."""

    def __init__(self, relationships=RELATIONSHIPS, duplicates=DUPLICATES) -> None:
        self.relationships = tuple(relationships)
        self.duplicates = tuple(duplicates)

    # -- public API ---------------------------------------------------------------
    def resolve(self, tables: MetatypeFamilyTables) -> MetatypeRelationshipReport:
        report = MetatypeRelationshipReport(
            repository_root=tables.repository_root, family_id=tables.family_id, directory=tables.directory,
            resolved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            resolver_version=RESOLVER_VERSION, status=ReportStatus.OK,
            table_states={t.table: t.state.value for t in tables.tables},
        )
        if not tables.tables:
            report.status = ReportStatus.FAILED
            report.messages = [f"[{d.code}] {d.message}" for d in tables.diagnostics] or ["No tables were loaded."]
            return report
        if tables.status.value == "partial":
            report.messages.append("The tables were loaded with problems; checks that depend on them are flagged.")

        for spec in self.relationships:
            if spec.custom == "owner_scoped":
                result, findings = self._owner_scoped(spec, tables)
            else:
                result, findings = self._relationship(spec, tables)
            self._store(report, result, findings)
        for spec in self.duplicates:
            result, findings = self._duplicates(spec, tables)
            self._store(report, result, findings)
        self._summarise(report)
        return report

    # -- relationships ----------------------------------------------------------------
    def _relationship(self, spec: RelationshipSpec, tables: MetatypeFamilyTables):
        src, tgt = _Access(spec.source_table, tables.table(spec.source_table)), _Access(
            spec.target_table, tables.table(spec.target_table))
        result = self._blank_result(spec)
        if not src.usable:
            return self._not_checkable(result, src.reason), []
        needed = list(spec.source_columns)
        for condition in (spec.only_when, spec.except_when, spec.ignore_values):
            if condition:
                needed.append(condition[0])
        missing = src.missing_columns(needed)
        if missing:
            return self._not_checkable(result, f"{src.file} has no column {', '.join(missing)}"), []

        references = self._collect(spec, src, result)
        if src.partial:
            result.partial_tables.append(src.name)
        if not references:
            result.status = RelationshipStatus.NO_REFERENCES
            result.reason = "no row carries a reference" if src.table.rows else f"{src.file} holds no data rows"
            return result, []
        if not tgt.usable:
            return self._not_checkable(result, tgt.reason), []
        missing = tgt.missing_columns(spec.target_columns)
        if missing:
            return self._not_checkable(result, f"{tgt.file} has no column {', '.join(missing)}"), []
        if tgt.partial:
            result.partial_tables.append(tgt.name)

        full = set()
        any_projection = set()
        wildcard_at = spec.source_columns.index(spec.wildcard_blank) if spec.wildcard_blank else None
        for _, values, _raw in tgt.rows():
            key = tuple(values[c] for c in spec.target_columns)
            full.add(key)
            if wildcard_at is not None:
                any_projection.add(key[:wildcard_at] + key[wildcard_at + 1:])

        findings: list[RelationshipFinding] = []
        for line, key, raw, wildcard in references:
            result.reference_count += 1
            if wildcard:
                found = (key[:wildcard_at] + key[wildcard_at + 1:]) in any_projection
            else:
                found = key in full
            if found:
                result.resolved_count += 1
                continue
            result.unresolved_count += 1
            self._add_finding(result, findings, RelationshipFinding(
                "UNRESOLVED_REFERENCE", spec.severity, spec.id, src.name, src.file, line,
                spec.source_columns, raw,
                f"{src.file} line {line}: {_describe(spec.source_columns, key)} has no match in "
                f"{tgt.file} ({', '.join(spec.target_columns)})"
                + (" - target table was only partly loaded" if tgt.partial else ""),
                reference=key, uncertain=tgt.partial,
            ))
        result.status = RelationshipStatus.UNRESOLVED if result.unresolved_count else RelationshipStatus.RESOLVED
        return result, findings

    def _collect(self, spec: RelationshipSpec, src: _Access, result: RelationshipResult):
        """Return ``[(line, key tuple, raw values, wildcard?)]`` and count skipped rows."""
        references = []
        for line, values, raw_row in src.rows():
            if spec.only_when and values[spec.only_when[0]] not in spec.only_when[1]:
                continue
            if spec.except_when and values[spec.except_when[0]] in spec.except_when[1]:
                continue
            if spec.ignore_values and values[spec.ignore_values[0]] in spec.ignore_values[1]:
                result.skipped_count += 1
                continue
            options: list[list[str]] = []
            wildcard = False
            usable = True
            for column in spec.source_columns:
                value = values[column]
                if column == spec.wildcard_blank and not value:
                    wildcard = True
                    options.append([""])
                    continue
                choices = _items(value) if column in spec.list_columns else ([value] if value else [])
                if not choices:
                    usable = False
                    break
                options.append(choices)
            if not usable:
                result.skipped_count += 1
                continue
            raw = src.raw(raw_row, spec.source_columns)
            for key in itertools.product(*options):
                references.append((line, tuple(key), raw, wildcard))
        return references

    def _owner_scoped(self, spec: RelationshipSpec, tables: MetatypeFamilyTables):
        """go_childprops.name must be a property of a metatype whose article uses the key."""
        props = _Access("go_childprops", tables.table("go_childprops"))
        articles = _Access("go_articles", tables.table("go_articles"))
        types = _Access("go_types", tables.table("go_types"))
        result = self._blank_result(spec)
        if not props.usable:
            return self._not_checkable(result, props.reason), []
        missing = props.missing_columns(("key", "name"))
        if missing:
            return self._not_checkable(result, f"{props.file} has no column {', '.join(missing)}"), []
        rows = [(line, v, raw) for line, v, raw in props.rows() if v["key"] and v["name"]]
        if not rows:
            result.status = RelationshipStatus.NO_REFERENCES
            result.reason = f"{props.file} holds no data rows"
            return result, []
        for other, columns in ((articles, ("id", "chprm_key")), (types, ("id", "name"))):
            if not other.usable:
                return self._not_checkable(result, other.reason), []
            missing = other.missing_columns(columns)
            if missing:
                return self._not_checkable(result, f"{other.file} has no column {', '.join(missing)}"), []
        result.partial_tables = [a.name for a in (props, articles, types) if a.partial]

        owners: dict[str, set[str]] = {}
        for _, values, _raw in articles.rows():
            for key in _items(values["chprm_key"]):
                owners.setdefault(key, set()).add(values["id"])
        defined = {(values["id"], values["name"]) for _, values, _raw in types.rows()}

        findings: list[RelationshipFinding] = []
        for line, values, raw_row in rows:
            ids = owners.get(values["key"])
            if not ids:
                result.skipped_count += 1       # no article uses this set: owner unknown
                continue
            result.reference_count += 1
            if any((owner, values["name"]) in defined for owner in ids):
                result.resolved_count += 1
                continue
            result.unresolved_count += 1
            uncertain = types.partial or articles.partial
            self._add_finding(result, findings, RelationshipFinding(
                "UNRESOLVED_REFERENCE", spec.severity, spec.id, props.name, props.file, line,
                ("key", "name"), props.raw(raw_row, ("key", "name")),
                f"{props.file} line {line}: property {values['name']!r} of set {values['key']!r} is not "
                f"defined in go_types for metatype(s) {', '.join(sorted(ids))}"
                + (" - a table was only partly loaded" if uncertain else ""),
                reference=(values["key"], values["name"]), uncertain=uncertain,
            ))
        if not result.reference_count:
            result.status = RelationshipStatus.NO_REFERENCES
            result.reason = "no go_childprops key is used by a go_articles row"
        else:
            result.status = (RelationshipStatus.UNRESOLVED if result.unresolved_count
                             else RelationshipStatus.RESOLVED)
        return result, findings

    # -- duplicate keys --------------------------------------------------------------------
    def _duplicates(self, spec: DuplicateSpec, tables: MetatypeFamilyTables):
        access = _Access(spec.table, tables.table(spec.table))
        result = DuplicateResult(spec.id, spec.description, spec.table, spec.key_columns, spec.basis,
                                 DuplicateStatus.NOT_CHECKABLE)
        if not access.usable:
            result.reason = access.reason
            return result, []
        missing = access.missing_columns(spec.key_columns)
        if missing:
            result.reason = f"{access.file} has no column {', '.join(missing)}"
            return result, []
        groups: dict[tuple[str, ...], list[tuple[int, tuple[str, ...]]]] = {}
        for line, values, raw_row in access.rows():
            result.row_count += 1
            key = tuple(values[c] for c in spec.key_columns)
            groups.setdefault(key, []).append((line, access.raw(raw_row, spec.key_columns)))
        result.partial = access.partial
        findings: list[RelationshipFinding] = []
        for key, members in groups.items():
            if len(members) < 2:
                continue
            result.duplicate_groups += 1
            result.extra_rows += len(members) - 1
            if len(findings) >= MAX_FINDINGS_PER_RULE:
                result.findings_truncated = True
                continue
            lines = [line for line, _ in members]
            findings.append(RelationshipFinding(
                "DUPLICATE_KEY", spec.severity, spec.id, access.name, access.file, lines[0],
                spec.key_columns, members[0][1],
                f"{access.file}: {_describe(spec.key_columns, members[0][1])} appears on lines "
                + ", ".join(map(str, lines)),
                reference=key, uncertain=False, related_lines=lines[1:],
            ))
        result.status = DuplicateStatus.DUPLICATES if result.duplicate_groups else DuplicateStatus.UNIQUE
        return result, findings

    # -- helpers ----------------------------------------------------------------------------------
    @staticmethod
    def _blank_result(spec: RelationshipSpec) -> RelationshipResult:
        return RelationshipResult(
            id=spec.id, description=spec.description, basis=spec.basis,
            source=f"{spec.source_table}.{'+'.join(spec.source_columns)}",
            target=f"{spec.target_table}.{'+'.join(spec.target_columns)}",
            status=RelationshipStatus.NOT_CHECKABLE, note=spec.note,
        )

    @staticmethod
    def _not_checkable(result: RelationshipResult, reason: str) -> RelationshipResult:
        result.status = RelationshipStatus.NOT_CHECKABLE
        result.reason = reason
        return result

    @staticmethod
    def _add_finding(result: RelationshipResult, findings: list, finding: RelationshipFinding) -> None:
        if len(findings) >= MAX_FINDINGS_PER_RULE:
            result.findings_truncated = True
        else:
            findings.append(finding)

    @staticmethod
    def _store(report: MetatypeRelationshipReport, result, findings) -> None:
        if isinstance(result, DuplicateResult):
            report.duplicate_checks.append(result)
        else:
            report.relationships.append(result)
        report.findings.extend(findings)

    @staticmethod
    def _summarise(report: MetatypeRelationshipReport) -> None:
        s = ReportSummary(relationships=len(report.relationships), duplicate_checks=len(report.duplicate_checks),
                          findings=len(report.findings))
        for r in report.relationships:
            if r.status is RelationshipStatus.RESOLVED:
                s.resolved += 1
            elif r.status is RelationshipStatus.UNRESOLVED:
                s.unresolved += 1
                s.unresolved_references += r.unresolved_count
            elif r.status is RelationshipStatus.NO_REFERENCES:
                s.no_references += 1
            else:
                s.not_checkable += 1
        for d in report.duplicate_checks:
            s.duplicate_groups += d.duplicate_groups
            s.duplicate_checks_not_checkable += d.status is DuplicateStatus.NOT_CHECKABLE
        report.summary = s
        partial = any(r.partial_tables for r in report.relationships) or any(d.partial for d in report.duplicate_checks)
        if s.unresolved or s.duplicate_groups:
            report.status = ReportStatus.ISSUES
        elif s.not_checkable or s.duplicate_checks_not_checkable or partial:
            report.status = ReportStatus.INCOMPLETE
        else:
            report.status = ReportStatus.OK


def _describe(columns, values) -> str:
    return ", ".join(f"{c}={v!r}" for c, v in zip(columns, values))
