"""Qt-free pending-edit layer over a read-only Articles reconciliation.

The reconciliation (``ArticleReconciliation``) stays the untouched source truth. This session keeps the
user's staged ``metatypeid`` / ``childparentid`` edits separately, keyed by article *identity*
(manufacturer, program, article) and never by row position, so sorting, filtering and refreshing cannot
attach an edit to the wrong article. Nothing is written to the repository here.

Editing rules (only what the schema and the reconciliation can verify):

* Only the ``metatypeid`` and ``childparentid`` roles are editable. A role is a literal column of that name
  or, for the manual's six-column go_articles layout, the verified alias (``id`` / ``chprm_key``); see
  ``ArticleReconciliation.roles``. Manufacturer, program and article are repository-derived; ``configid``
  (``prm_key``) is read-only: it is a key into go_properties and is never generated.
* A row whose identity is missing, ambiguous or in conflict is not editable: its mapping cannot be
  attributed to one record.
* A value containing the table delimiter, a double quote or a line break would corrupt the CSV and is an
  error, as is a first-column value starting with ``#`` (the line would become a comment). Whitespace at
  either end is a warning (the schema fields declare ``trim``).
* Dangling references are warnings, never errors: the production repository itself contains them (3 of 39
  series have an unresolved prm_key, 27 of 518 chprm_key tokens are unresolved). MetatypeID should be a
  go_types.id, ConfigID a go_properties.key, each ChildParentID token (a comma list) a go_childprops.key.
  A reference is only judged when its table was read.
* No format or uniqueness rule for MetatypeID / ChildParentID exists in any source, so none is enforced
  (docs/02_Domain/Engineering/Metatype_Write_Contract_Decisions.md).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from models.metatype_articles import (
    AMBIGUOUS_IDENTITY, CONFLICT, INVALID_IDENTITY, NEEDS_ASSIGNMENT, ArticleReconciliation, ArticleRow,
)

EDITABLE_ROLES = ("metatypeid", "childparentid")
DELIMITER = ";"          # every Metatype schema field observed declares ``delim ;``
_NOT_EDITABLE_STATUS = (AMBIGUOUS_IDENTITY, CONFLICT, INVALID_IDENTITY)

#: Why Create Metatype stays disabled. See docs/02_Domain/Engineering/Metatype_Write_Contract_Decisions.md.
WRITER_BLOCKER = (
    "Writing is blocked: nothing may be written to the Subversion working copy until the owner authorises it "
    "(decision D8). Staged MetatypeID / ChildParentID edits can be planned and verified in memory (Review "
    "changes); creating a new polymorphic property additionally needs decisions D2, D4, D5 and D6 "
    "(value-to-article binding, mode policy, go_texts encoding for new text, property format/default). "
    "Nothing is written to the repository.")

_ROLE_LABELS = {"metatypeid": "MetatypeID", "configid": "ConfigID", "childparentid": "ChildParentID"}

RowKey = tuple


@dataclass(frozen=True)
class Issue:
    severity: str          # "error" | "warning" | "info"
    code: str
    message: str


@dataclass(frozen=True)
class Change:
    key: RowKey
    column: str
    old: str
    new: str


@dataclass
class _Pending:
    new: str
    baseline: str          # the source value the user edited from


@dataclass
class RefreshReport:
    kept: int = 0
    dropped: list[Change] = field(default_factory=list)      # article no longer present / no longer editable
    conflicted: list[Change] = field(default_factory=list)   # source value changed under a pending edit


def row_key(row: ArticleRow) -> RowKey:
    """Stable identity of a row. Rows without a usable identity fall back to their source line."""
    return row.identity if row.identity else ("<line>", row.source_file, row.source_line)


class ArticleEditSession:
    def __init__(self, result: ArticleReconciliation | None = None) -> None:
        self._result: ArticleReconciliation | None = None
        self._index: dict[RowKey, ArticleRow] = {}
        self._roles: dict[str, str] = {}
        self._pending: dict[tuple[RowKey, str], _Pending] = {}
        self._written: dict[tuple[RowKey, str], str] = {}     # verified-written values (staging), not the loaded source
        self._failed: dict[tuple[RowKey, str], str] = {}      # pending cells whose last write attempt failed -> reason
        self.last_refresh: RefreshReport | None = None
        if result is not None:
            self._adopt(result)

    # -- source -------------------------------------------------------------------------------------------
    @property
    def result(self) -> ArticleReconciliation | None:
        return self._result

    def _adopt(self, result: ArticleReconciliation) -> None:
        self._result = result
        self._roles = dict(result.roles) or {c.casefold(): c for c in result.columns}
        self._index = {row_key(r): r for r in result.rows}

    def role_column(self, role: str) -> str | None:
        return self._roles.get(role)

    def editable_columns(self) -> list[str]:
        return [self._roles[r] for r in EDITABLE_ROLES if r in self._roles]

    def is_column_editable(self, column: str) -> bool:
        return column in self.editable_columns()

    def role_of(self, column: str) -> str | None:
        return next((role for role in _ROLE_LABELS if self._roles.get(role) == column), None)

    def column_label(self, column: str) -> str:
        """Header text: ``MetatypeID (id)`` for an aliased role column, the plain name otherwise."""
        label = _ROLE_LABELS.get(self.role_of(column) or "")
        return column if label is None or label.casefold() == column.casefold() else f"{label} ({column})"

    def row_editable(self, key: RowKey) -> bool:
        row = self._index.get(key)
        return row is not None and row.identity is not None and row.status not in _NOT_EDITABLE_STATUS

    def cell_editable(self, key: RowKey, column: str) -> bool:
        return self.is_column_editable(column) and self.row_editable(key)

    # -- values -------------------------------------------------------------------------------------------
    def source_value(self, key: RowKey, column: str) -> str:
        row = self._index.get(key)
        return row.values.get(column, "") if row else ""

    def base_value(self, key: RowKey, column: str) -> str:
        """Last persisted value: the verified-written one if any, else the loaded source value."""
        return self._written.get((key, column), self.source_value(key, column))

    def value(self, key: RowKey, column: str) -> str:
        pending = self._pending.get((key, column))
        return pending.new if pending else self.base_value(key, column)

    def cell_state(self, key: RowKey, column: str) -> str:
        """``failed`` (pending, last write failed) | ``pending`` | ``written`` (verified in staging) | ``source``."""
        if (key, column) in self._pending:
            return "failed" if (key, column) in self._failed else "pending"
        return "written" if (key, column) in self._written else "source"

    def is_written(self, key: RowKey, column: str | None = None) -> bool:
        return any(k == key and (column is None or c == column) for k, c in self._written)

    @property
    def written_count(self) -> int:
        return len(self._written)

    def failure_reason(self, key: RowKey, column: str) -> str:
        return self._failed.get((key, column), "")

    def is_modified(self, key: RowKey, column: str | None = None) -> bool:
        if column is not None:
            return (key, column) in self._pending
        return any(k == key for k, _ in self._pending)

    def set_value(self, key: RowKey, column: str, text: str) -> bool:
        """Stage an edit. Returns False (and changes nothing) when the cell is not editable."""
        if not self.cell_editable(key, column):
            return False
        base = self.base_value(key, column)
        self._failed.pop((key, column), None)
        if text == base:
            self._pending.pop((key, column), None)   # editing back to the persisted value is no change
        else:
            self._pending[(key, column)] = _Pending(text, base)
        return True

    # -- persisted-state tracking -------------------------------------------------------------------------
    def mark_applied(self, plan, result) -> int:
        """Record a *verified* staging write: the planned cells move from pending to written.

        Only files whose outcome is written AND verified count; anything else is untouched (still pending).
        The loaded source snapshot (``result``) is never modified.
        """
        done = 0
        for file_plan, outcome in zip(plan.files, result.files):
            if not (result.success and outcome.written and outcome.verified):
                continue
            lines = {(c.line, c.column) for c in file_plan.changes}
            for cell, pending in list(self._pending.items()):
                row = self._index.get(cell[0])
                if row is not None and row.source_file == file_plan.path and (row.source_line, cell[1]) in lines:
                    self._written[cell] = pending.new
                    del self._pending[cell]
                    self._failed.pop(cell, None)
                    done += 1
        return done

    def mark_failed(self, plan, reason: str) -> int:
        """Flag the pending cells of a plan whose write failed or was rolled back; they stay pending, never saved."""
        done = 0
        for file_plan in plan.files:
            lines = {(c.line, c.column) for c in file_plan.changes}
            for cell in self._pending:
                row = self._index.get(cell[0])
                if row is not None and row.source_file == file_plan.path and (row.source_line, cell[1]) in lines:
                    self._failed[cell] = reason
                    done += 1
        return done

    def discard(self, key: RowKey | None = None) -> int:
        """Drop the staged edits of one row, or of all rows. Returns how many cells were reverted."""
        doomed = [k for k in self._pending if key is None or k[0] == key]
        for k in doomed:
            del self._pending[k]
            self._failed.pop(k, None)
        return len(doomed)

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def pending_changes(self) -> list[Change]:
        return [Change(k, c, p.baseline, p.new) for (k, c), p in self._pending.items()]

    # -- validation ---------------------------------------------------------------------------------------
    def issues(self, key: RowKey) -> list[Issue]:
        row = self._index.get(key)
        if row is None:
            return [Issue("error", "ARTICLE_NOT_IN_SOURCE", "The article is not in the loaded source.")]
        found: list[Issue] = []
        if row.status in _NOT_EDITABLE_STATUS:
            found.append(Issue("error", "ROW_NOT_EDITABLE", f"{row.status}: this record's mapping cannot be "
                                                            "attributed to one article; it is not editable."))
        for d in (self._result.diagnostics if self._result else []):
            if d.line == row.source_line and d.file and d.file == row.source_file.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]:
                found.append(Issue("error" if d.severity == "error" else "warning", d.code, d.message))
        metatype = self._roles.get("metatypeid")
        if metatype is None:
            found.append(Issue("info", "METATYPEID_UNAVAILABLE",
                               "The series schema declares no metatypeid column; the mapping cannot be edited."))
        else:
            if not self.value(key, metatype).strip(" \t") and row.identity is not None \
                    and row.status not in _NOT_EDITABLE_STATUS:
                found.append(Issue("info", "NEEDS_ASSIGNMENT", "No MetatypeID is assigned yet."))
        if "configid" not in self._roles:
            found.append(Issue("info", "CONFIGID_UNAVAILABLE",
                               "The series schema declares no configid column; no ConfigID can be resolved."))
        found.extend(self._reference_issues(key))
        first_column = self._result.columns[0] if self._result and self._result.columns else None
        for column in self.editable_columns():
            if not self.is_modified(key, column):
                continue
            text = self.value(key, column)
            if DELIMITER in text or '"' in text or "\r" in text or "\n" in text:
                found.append(Issue("error", "INVALID_CHARACTER",
                                   f"{column} contains the delimiter '{DELIMITER}', a double quote or a line break."))
            elif column == first_column and text.lstrip(" \t").startswith("#"):
                found.append(Issue("error", "COMMENT_PREFIX",
                                   f"{column} starts with '#': the line would become a comment."))
            elif text != text.strip(" \t"):
                found.append(Issue("warning", "UNTRIMMED_VALUE", f"{column} has leading or trailing whitespace."))
            if text == "" and self.source_value(key, column).strip(" \t"):
                found.append(Issue("warning", "MAPPING_CLEARED", f"{column} existing value "
                                   f"'{self.source_value(key, column).strip()}' would be removed."))
        return found

    def _reference_issues(self, key: RowKey) -> list[Issue]:
        """Dangling-reference warnings, judged only against tables that were actually read."""
        refs = self._result.references if self._result else {}
        out: list[Issue] = []
        checks = (("metatypeid", "metatype_ids", "METATYPEID_NOT_IN_GO_TYPES", "go_types.id", False),
                  ("configid", "config_keys", "CONFIGID_NOT_IN_GO_PROPERTIES", "go_properties.key", False),
                  ("childparentid", "child_keys", "CHILDPARENTID_NOT_IN_GO_CHILDPROPS", "go_childprops.key", True))
        for role, ref, code, target, is_list in checks:
            column, known = self._roles.get(role), refs.get(ref)
            if column is None or known is None:
                continue
            text = self.value(key, column).strip(" \t")
            tokens = [t.strip() for t in text.split(",")] if is_list else [text]
            missing = [t for t in tokens if t and t not in known]
            if missing:
                out.append(Issue("warning", code, f"{_ROLE_LABELS[role]} {', '.join(missing)} is not a {target} "
                                                  "in this series."))
        return out

    def severity(self, key: RowKey) -> str:
        """``error`` > ``warning`` > ``unavailable`` > ``ok``; other ``info`` issues do not change the verdict.

        ``unavailable`` means the schema declares no metatypeid column, so the row's mapping cannot be
        evaluated at all; such a row is never reported as valid.
        """
        levels = {i.severity for i in self.issues(key)}
        if "error" in levels:
            return "error"
        if "warning" in levels:
            return "warning"
        return "unavailable" if "metatypeid" not in self._roles else "ok"

    def validate_all(self) -> dict[RowKey, list[Issue]]:
        return {k: [i for i in self.issues(k) if i.severity != "info"] for k in self._index
                if any(i.severity != "info" for i in self.issues(k))}

    # -- counts / readiness -------------------------------------------------------------------------------
    def counts(self) -> dict[str, int]:
        mapped = sum(1 for r in self._index.values() if self._is_mapped(r))
        sev = [self.severity(k) for k in self._index]
        return {"total": len(self._index), "mapped": mapped, "unmapped": len(self._index) - mapped,
                "invalid": sev.count("error"), "warnings": sev.count("warning"),
                "unavailable": sev.count("unavailable"), "valid": sev.count("ok"), "pending": self.pending_count,
                "written": self.written_count}

    def _is_mapped(self, row: ArticleRow) -> bool:
        column = self._roles.get("metatypeid")
        return bool(column and self.value(row_key(row), column).strip(" \t"))

    def creation_blockers(self) -> list[str]:
        """Reasons the final write cannot run. Always includes the unverified-writer blocker."""
        reasons: list[str] = []
        if self._result is None:
            reasons.append("No series is loaded.")
        elif self._result.status.value == "failed":
            reasons.append("The article list failed to load.")
        if not self.pending_count:
            reasons.append("There are no pending changes.")
        if any(self.severity(k) == "error" for k, _ in self._pending):
            reasons.append("Pending edits have validation errors.")
        if "configid" not in self._roles:
            reasons.append("ConfigID cannot be resolved: the schema declares no configid column.")
        reasons.append(WRITER_BLOCKER)
        return reasons

    def can_create(self) -> bool:
        return False   # the verified write path does not exist; see WRITER_BLOCKER

    # -- review -------------------------------------------------------------------------------------------
    def review_text(self) -> str:
        if not self.pending_count:
            return "No pending changes."
        lines = [f"{self.pending_count} pending change(s) (nothing has been written):", ""]
        for change in sorted(self.pending_changes(), key=lambda c: (str(c.key), c.column)):
            label = " / ".join(str(p) for p in change.key)
            old = change.old.strip() or "(empty)"
            new = change.new.strip() or "(empty)"
            lines.append(f"  {label}: {change.column}: {old} -> {new}")
            for issue in self.issues(change.key):
                if issue.severity != "info":
                    lines.append(f"      {issue.severity.upper()} [{issue.code}] {issue.message}")
        lines += ["", "Blockers:"] + [f"  - {r}" for r in self.creation_blockers()]
        return "\n".join(lines)

    # -- refresh ------------------------------------------------------------------------------------------
    def refresh(self, result: ArticleReconciliation) -> RefreshReport:
        """Adopt a freshly loaded reconciliation, carrying pending edits over by article identity.

        An edit survives while its article still exists and is editable. If the source value changed since
        the edit was made, the edit is kept but reported as a conflict (the user decides); it is never
        silently replaced and never silently dropped without being reported.
        """
        old_pending = dict(self._pending)
        old_written, old_failed = dict(self._written), dict(self._failed)
        self._adopt(result)
        report = RefreshReport()
        self._pending = {}
        self._failed = {}
        # A written value stays shown while the (re)loaded source still differs from it; once the source catches up
        # (e.g. it is the staging copy that is loaded) the overlay is redundant and dropped.
        self._written = {cell: v for cell, v in old_written.items()
                         if cell[0] in self._index and self.source_value(*cell).strip(" 	") != v.strip(" 	")}
        for (key, column), pending in old_pending.items():
            change = Change(key, column, pending.baseline, pending.new)
            if not self.cell_editable(key, column):
                report.dropped.append(change)
                continue
            current = self.base_value(key, column)
            if pending.new == current:
                continue          # the persisted value already holds the user's value
            self._pending[(key, column)] = _Pending(pending.new, current)
            if (key, column) in old_failed:
                self._failed[(key, column)] = old_failed[(key, column)]
            report.kept += 1
            if current != pending.baseline:
                report.conflicted.append(Change(key, column, current, pending.new))
        self.last_refresh = report
        return report
