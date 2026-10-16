"""Read-only reconciliation of a series' articles with their existing Metatype assignments.

Qt-free. Loads the series through the existing :class:`MetatypeTableLoaderService` (one loader, one
parser) and combines the loaded tables in memory. Nothing is written, generated or executed.

Semantics (kept deliberately narrow; anything not verifiable is reported, not guessed):

* The article list is the schema-declared ``go_articles`` table. Its identity key is
  (manufacturer, program, article) using the columns the schema declares (``article`` or
  ``article_nr``); blanks are trimmed for comparison only, displayed values stay raw.
* ``metatypeid``, ``childparentid`` and ``configid`` are used only when the schema declares a column of
  exactly that name. ``id`` is never treated as ``metatypeid``. Assignment fields may sit in the article
  table or in another declared table that carries the identity columns; both are combined by identity.
* Differing assignments for one article are a conflict and are shown unresolved; identical repeats are
  reported as duplicates. Rows are never merged by column position.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from models.metatype_articles import (
    AMBIGUOUS_IDENTITY, CONFLICT, INVALID_IDENTITY, MAPPED, MAPPING_UNAVAILABLE, NEEDS_ASSIGNMENT,
    ArticleReconciliation, ArticleRow, MappingSource, ReconciliationStatus,
)
from models.metatype_tables import (
    LoadDiagnostic, LoadedTable, LoadStatus, MetatypeFamilyTables, TableLoadState,
)
from services.base_service import BaseService
from services.metatype.repository_scanner import OPTIONAL_TABLES

ARTICLE_TABLE = "go_articles"
_SESSION_KEY = "metatype.article_reconciliation"
_ASSIGNMENT_ROLES = ("metatypeid", "childparentid")
_ALL_MAPPING_ROLES = ("metatypeid", "childparentid", "configid")
_RESERVED_ID = "_native_"   # reserved go_articles row (also skipped by MetatypeCreationService)
_NO_ROWS = (TableLoadState.MISSING, TableLoadState.DECODE_ERROR, TableLoadState.UNREADABLE)
_CLEAN = (TableLoadState.VALID, TableLoadState.EMPTY, TableLoadState.NO_DATA)


def _by_role(columns: list[str]) -> dict[str, str]:
    """Lower-cased column name -> declared column name."""
    return {name.casefold(): name for name in columns}


def _identity_columns(columns: list[str]) -> tuple[str, str, str] | None:
    lookup = _by_role(columns)
    article = lookup.get("article") or lookup.get("article_nr")
    if "manufacturer" in lookup and "program" in lookup and article:
        return lookup["manufacturer"], lookup["program"], article
    return None


class MetatypeArticleService(BaseService):
    """Build and retain the Articles reconciliation for the loaded series."""

    @property
    def last_result(self) -> ArticleReconciliation | None:
        value = self.context.workflow_session(_SESSION_KEY).get("result")
        return value if isinstance(value, ArticleReconciliation) else None

    def reconcile(self, series: str, root: str | Path | None = None,
                  directory: str | None = None) -> ArticleReconciliation:
        loaded = self.context.metatype_table_loader_service.load_family(series, root, directory)
        result = self.build(series, loaded)
        self.context.workflow_session(_SESSION_KEY)["result"] = result
        return result

    # -- reconciliation ---------------------------------------------------------------------------------
    @staticmethod
    def build(series: str, loaded: MetatypeFamilyTables) -> ArticleReconciliation:
        rec = ArticleReconciliation(series, ReconciliationStatus.FAILED, directory=loaded.directory,
                                    loader_result=loaded)

        def diag(severity, code, message, table="", file="", line=None):
            rec.diagnostics.append(LoadDiagnostic(severity, code, message, table, file, line))

        if loaded.status is LoadStatus.FAILED:
            rec.diagnostics.extend(loaded.diagnostics)
            return rec
        articles = loaded.table(ARTICLE_TABLE)
        if articles is None:
            rec.diagnostics.extend(loaded.diagnostics)
            diag("error", "ARTICLE_TABLE_NOT_DECLARED", f"mt.inp_descr does not declare {ARTICLE_TABLE}; "
                 "there is no article list to reconcile.", file=loaded.schema_source)
            return rec
        rec.article_table = articles.table
        if articles.state in _NO_ROWS:
            rec.diagnostics.extend(loaded.diagnostics + articles.diagnostics)
            return rec

        # -- sources -----------------------------------------------------------------------------------
        key_columns = _identity_columns(articles.columns)
        mapping_tables: list[tuple[LoadedTable, tuple[str, str, str]]] = []
        for table in loaded.tables:
            if table is articles:
                continue  # a declared-but-missing/unreadable mapping table still counts: its problem is reported
            lookup = _by_role(table.columns)
            if not any(role in lookup for role in _ASSIGNMENT_ROLES):
                continue
            keys = _identity_columns(table.columns)
            if keys is None:
                diag("error", "MAPPING_KEY_COLUMNS_MISSING",
                     f"{table.table} declares Metatype assignment fields but not manufacturer, program and "
                     "article; its records cannot be matched to articles and were not used.",
                     table.table, table.file_name)
                continue
            mapping_tables.append((table, keys))
        rec.mapping_tables = [t.table for t, _ in mapping_tables]
        used = {articles.table, *rec.mapping_tables}

        columns = list(articles.columns)
        for table, _ in mapping_tables:
            for name in table.columns:
                if name.casefold() in _ASSIGNMENT_ROLES and name.casefold() not in _by_role(columns):
                    columns.append(name)
        rec.columns = columns
        roles = _by_role(columns)
        rec.unavailable_fields = [role for role in _ALL_MAPPING_ROLES if role not in roles]

        # -- diagnostics of the sources actually used ---------------------------------------------------
        rec.diagnostics.extend(d for d in loaded.diagnostics
                               if not d.table or d.table in used or d.code != "SCHEMA_DECLARATION_PROBLEM")
        schema_problem = any(d.code == "SCHEMA_DECLARATION_PROBLEM" and d.table in used for d in loaded.diagnostics)
        for table in loaded.tables:
            if table.table in used:
                rec.diagnostics.extend(table.diagnostics)
            elif table.state not in _CLEAN and not (table.state is TableLoadState.MISSING
                                                    and table.table.casefold() in OPTIONAL_TABLES):
                diag("warning", "UNRELATED_TABLE_NOT_CLEAN",
                     f"{table.table} is {table.state.value}; it is not used by the Articles table.",
                     table.table, table.file_name)
        for name in loaded.unlisted_go_files:
            diag("warning", "UNDECLARED_GO_FILE", f"{name} is not declared in mt.inp_descr and was not loaded.",
                 file=name)
        for role in rec.unavailable_fields:
            diag("warning", "MAPPING_FIELD_UNAVAILABLE",
                 f"The schema declares no '{role}' column; the field is shown as unavailable and "
                 "nothing is generated for it.", file=loaded.schema_source)
        if key_columns is None:
            diag("error", "ARTICLE_IDENTITY_COLUMNS_MISSING",
                 f"{articles.table} does not declare manufacturer, program and article/article_nr; articles "
                 "cannot be identified or matched to mappings.", articles.table, articles.file_name)

        # -- article rows ---------------------------------------------------------------------------------
        article_roles = _by_role(articles.columns)
        embedded = [article_roles[r] for r in _ASSIGNMENT_ROLES if r in article_roles]
        id_column = article_roles.get("id")
        rows: list[ArticleRow] = []
        for source in articles.rows:
            raw = dict(zip(articles.columns, source.values))
            if id_column and raw[id_column].strip(" \t") == _RESERVED_ID:
                diag("warning", "RESERVED_ROW_SKIPPED",
                     f"Line {source.line} is the reserved '{_RESERVED_ID}' row, not an article.",
                     articles.table, articles.file_name, source.line)
                continue
            identity = None
            if key_columns:
                parts = tuple(raw[c].strip(" \t") for c in key_columns)
                if all(parts):
                    identity = parts
                else:
                    diag("error", "MISSING_ARTICLE_IDENTITY",
                         "manufacturer, program or article is empty; the article cannot be identified.",
                         articles.table, articles.file_name, source.line)
            row = ArticleRow(dict.fromkeys(columns, ""), articles.path, source.line, identity,
                             INVALID_IDENTITY if identity is None else "")
            row.values.update(raw)
            rows.append(row)

        lines_by_identity: dict[tuple, list[int]] = defaultdict(list)
        for row in rows:
            if row.identity:
                lines_by_identity[row.identity].append(row.source_line)
        ambiguous = {k for k, lines in lines_by_identity.items() if len(lines) > 1}
        for key in sorted(ambiguous):
            diag("error", "AMBIGUOUS_ARTICLE_IDENTITY",
                 f"Article {' / '.join(key)} occurs on lines {', '.join(map(str, lines_by_identity[key]))}; "
                 "its mapping cannot be attributed to one record.", articles.table, articles.file_name,
                 lines_by_identity[key][0])

        # -- external mapping records -----------------------------------------------------------------------
        external: dict[tuple, list[MappingSource]] = defaultdict(list)
        for table, keys in mapping_tables:
            assigned = [name for name in table.columns if name.casefold() in _ASSIGNMENT_ROLES]
            for source in table.rows:
                raw = dict(zip(table.columns, source.values))
                record = MappingSource(table.path, source.line, {c: raw[c] for c in assigned}, table.table)
                parts = tuple(raw[c].strip(" \t") for c in keys)
                if not all(parts):
                    rec.unmatched_mappings.append(record)
                    diag("error", "MAPPING_IDENTITY_MISSING",
                         "manufacturer, program or article is empty; the mapping cannot be matched to an article.",
                         table.table, table.file_name, source.line)
                else:
                    external[parts].append(record)
        known = set(lines_by_identity)
        for key, records in external.items():
            if key in known and key not in ambiguous:
                continue
            for record in records:
                rec.unmatched_mappings.append(record)
                if key in ambiguous:
                    diag("error", "AMBIGUOUS_MAPPING_TARGET",
                         f"Mapping for {' / '.join(key)} matches several article records and was not attached.",
                         record.table, file=record.file, line=record.line)
                else:
                    diag("error", "MAPPING_WITHOUT_ARTICLE",
                         f"Mapping for {' / '.join(key)} matches no article in {articles.table}.",
                         record.table, file=record.file, line=record.line)

        # -- combine ----------------------------------------------------------------------------------------
        mapping_cols = [roles[r] for r in _ASSIGNMENT_ROLES if r in roles]
        for row in rows:
            if row.status == INVALID_IDENTITY:
                continue
            if row.identity in ambiguous:
                row.status = AMBIGUOUS_IDENTITY
                continue
            candidates: list[MappingSource] = []
            own = {c: row.values[c] for c in embedded}
            if any(v.strip(" \t") for v in own.values()):
                candidates.append(MappingSource(row.source_file, row.source_line, own, articles.table))
            candidates.extend(external.get(row.identity, []))
            row.mapping_sources = candidates
            distinct = {tuple(c.values.get(name, "").strip(" \t") for name in mapping_cols) for c in candidates}
            if len(distinct) > 1:
                for name in mapping_cols:
                    row.values[name] = ""
                row.status = CONFLICT
                diag("error", "CONFLICTING_MAPPINGS",
                     f"Article {' / '.join(row.identity)} has {len(distinct)} different assignments "
                     f"({'; '.join(f'{c.table} line {c.line}' for c in candidates)}); none was chosen.",
                     articles.table, articles.file_name, row.source_line)
                continue
            if candidates:
                if len(candidates) > 1:
                    diag("warning", "DUPLICATE_MAPPING",
                         f"Article {' / '.join(row.identity)} has {len(candidates)} identical mapping records "
                         f"({'; '.join(f'{c.table} line {c.line}' for c in candidates)}).",
                         articles.table, articles.file_name, row.source_line)
                for name in mapping_cols:
                    row.values[name] = candidates[0].values.get(name, "")
            if "metatypeid" not in roles:
                row.status = MAPPING_UNAVAILABLE
            else:
                row.status = MAPPED if row.values[roles["metatypeid"]].strip(" \t") else NEEDS_ASSIGNMENT
        rec.rows = rows

        incomplete = (schema_problem or "metatypeid" not in roles or bool(rec.errors())
                      or any(t.state not in _CLEAN for t in loaded.tables if t.table in used))
        rec.status = ReconciliationStatus.PARTIAL if incomplete else ReconciliationStatus.COMPLETE
        return rec
