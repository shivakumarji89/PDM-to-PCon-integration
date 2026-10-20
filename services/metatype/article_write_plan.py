"""In-memory write plan for staged MetatypeID / ChildParentID edits of ``go_articles.csv``.

This module produces and verifies the exact bytes a write *would* produce. It never opens a file for
writing, never runs a version-control command and never touches the repository: applying a plan needs the
owner authorisation recorded in docs/02_Domain/Engineering/Metatype_Write_Contract_Decisions.md (D8).

Verified format facts the planner relies on (all from that document):

* One record per physical line, fields separated by ``;``; lines starting with ``#`` are comments; blank lines
  are ignored (MT 1.18.0 section 2, 50/50 real series). Physical line numbers are what the loader reports.
* Only the edited field changes. Surrounding padding, comments, blank lines, line terminators (CRLF in 46/46
  real go_texts files and every sampled table), a UTF-8 byte order mark and every other field stay
  byte-for-byte. The schema fields declare ``trim``, so the written value is the trimmed value.
* Encoding follows the loader: strict UTF-8 (real go_articles.csv files are ASCII). Anything else is refused
  rather than guessed.
* A line using the quoting rule (``"``) is refused: the planner does not rewrite quoted fields.
* Mapping fields that live in another table (external mapping records) are refused; only fields stored in the
  article table itself are planned.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from collections.abc import Callable
from pathlib import Path

from services.metatype.article_edit_session import ArticleEditSession
from services.metatype.metatype_table_loader import parse_table_text, split_fields

_UTF8_BOM = b"\xef\xbb\xbf"
_BREAK = re.compile(r"(\r\n|\n|\r)")
_BLANKS = " \t"


@dataclass(frozen=True)
class LineChange:
    line: int
    column: str
    old: str
    new: str


@dataclass
class FilePlan:
    path: str
    changes: list[LineChange] = field(default_factory=list)
    original: bytes = b""
    new: bytes = b""
    problems: list[str] = field(default_factory=list)
    verified: bool = False
    columns: list[str] = field(default_factory=list)   # the file's own fields, for post-write verification
    verifier: Callable[[bytes], list[str]] | None = field(default=None, repr=False, compare=False)  # appended-row plans

    @property
    def ok(self) -> bool:
        return bool(self.changes) and not self.problems and self.verified


@dataclass
class ArticleWritePlan:
    series: str
    files: list[FilePlan] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems and bool(self.files) and all(f.ok for f in self.files)

    def review_text(self, max_lines: int = 40) -> str:
        if not self.files and not self.problems:
            return "No planned file changes."
        out = ["Planned output (computed in memory; NOTHING has been written):"]
        for problem in self.problems:
            out.append(f"  PROBLEM: {problem}")
        for plan in self.files:
            out.append(f"  {plan.path}: {len(plan.changes)} field change(s), "
                       + ("verified by re-parsing" if plan.verified else "NOT verified"))
            for problem in plan.problems:
                out.append(f"    PROBLEM: {problem}")
            original = _lines(plan.original)
            new = _lines(plan.new)
            for change in plan.changes[:max_lines]:
                out.append(f"    line {change.line}: {change.column}: {change.old or '(empty)'} -> {change.new or '(empty)'}")
                if change.line - 1 < len(original) and change.line - 1 < len(new):
                    out.append(f"      - {original[change.line - 1][0]}")
                    out.append(f"      + {new[change.line - 1][0]}")
            if len(plan.changes) > max_lines:
                out.append(f"    ... {len(plan.changes) - max_lines} more change(s)")
        return "\n".join(out)


def _lines(raw: bytes) -> list[tuple[str, str]]:
    """(text, terminator) per physical line. Joining ``text + terminator`` reproduces the input exactly."""
    if raw.startswith(_UTF8_BOM):
        raw = raw[len(_UTF8_BOM):]
    parts = _BREAK.split(raw.decode("utf-8", errors="replace"))
    texts, terms = parts[0::2], parts[1::2] + [""]
    pairs = list(zip(texts, terms))
    if pairs and pairs[-1] == ("", ""):
        pairs.pop()
    return pairs


def _replace_field(old: str, value: str) -> str:
    """Put ``value`` into a field, keeping the field's own leading and trailing padding."""
    core = old.strip(_BLANKS)
    if not core:
        return value
    lead = old[:len(old) - len(old.lstrip(_BLANKS))]
    trail = old[len(old.rstrip(_BLANKS)):]
    return lead + value + trail


def plan_article_edits(session: ArticleEditSession) -> ArticleWritePlan:
    """Plan the staged edits. Pure: reads the article table's file, writes nothing."""
    result = session.result
    plan = ArticleWritePlan(result.series if result else "")
    if result is None or result.status.value == "failed" or not result.article_table:
        plan.problems.append("No usable article table is loaded.")
        return plan
    pending = session.pending_changes()
    if not pending:
        return plan
    by_file: dict[str, list] = {}
    for change in pending:
        row = session._index.get(change.key)
        if row is None:
            plan.problems.append(f"{' / '.join(map(str, change.key))}: the article is not in the loaded source.")
            continue
        by_file.setdefault(row.source_file, []).append((change, row))
    for path, items in by_file.items():
        plan.files.append(_plan_file(session, path, items))
    return plan


def _plan_file(session: ArticleEditSession, path: str, items: list) -> FilePlan:
    result = session.result
    file_plan = FilePlan(path)
    table = result.loader_result.table(result.article_table) if result.loader_result else None
    if table is None:
        file_plan.problems.append("The article table's loaded columns are unavailable.")
        return file_plan
    columns = list(table.columns)          # the article file's own fields (result.columns may add mapping-table columns)
    label = lambda change: " / ".join(map(str, change.key))   # noqa: E731
    wanted: dict[int, dict[int, str]] = {}                     # line -> column index -> new trimmed value
    for change, row in items:
        index = columns.index(change.column) if change.column in columns else -1
        if index < 0:
            file_plan.problems.append(f"{label(change)}: {change.column} is not a column of the article table.")
            continue
        external = [s for s in row.mapping_sources if s.table != result.article_table]
        if external:
            file_plan.problems.append(
                f"{label(change)}: its mapping also lives in {', '.join(sorted({s.table for s in external}))}; "
                "only fields stored in the article table are planned.")
            continue
        if session.severity(change.key) == "error":
            file_plan.problems.append(f"{label(change)}: the row has validation errors.")
            continue
        value = change.new.strip(_BLANKS)
        if session.role_of(change.column) == "metatypeid" and not value:
            file_plan.problems.append(
                f"{label(change)}: an empty MetatypeID is not written (go_articles.id binds the article to a "
                "Metatype in 822/822 real rows).")
            continue
        if value == change.old.strip(_BLANKS):
            continue                                            # whitespace-only difference: nothing to write
        wanted.setdefault(row.source_line, {})[index] = value
        file_plan.changes.append(LineChange(row.source_line, change.column, change.old.strip(_BLANKS), value))
    if file_plan.problems:
        return file_plan
    if not wanted:
        return file_plan

    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        file_plan.problems.append(f"The article file cannot be read: {exc}")
        return file_plan
    file_plan.original = raw
    file_plan.columns = columns
    bom = raw.startswith(_UTF8_BOM)
    try:
        text = (raw[len(_UTF8_BOM):] if bom else raw).decode("utf-8")
    except UnicodeDecodeError as exc:
        file_plan.problems.append(f"The article file is not valid UTF-8 ({exc}); it is not rewritten.")
        return file_plan
    parts = _BREAK.split(text)
    texts, terms = parts[0::2], parts[1::2] + [""]
    rows_by_line = {r.source_line: r for _, r in items}
    for number, edits in sorted(wanted.items()):
        if number < 1 or number > len(texts):
            file_plan.problems.append(f"Line {number} no longer exists: the file changed since it was loaded.")
            continue
        line = texts[number - 1]
        if '"' in line:
            file_plan.problems.append(f"Line {number} uses the quoting rule; quoted fields are not rewritten.")
            continue
        if not line.strip(_BLANKS) or line.startswith("#"):
            file_plan.problems.append(f"Line {number} is a comment or blank: the file changed since it was loaded.")
            continue
        fields = split_fields(line)
        row = rows_by_line[number]
        loaded = [row.values.get(c, "") for c in columns]
        if fields != loaded:
            file_plan.problems.append(f"Line {number} differs from the loaded record: the file changed since it "
                                      "was loaded. Refresh before planning.")
            continue
        for index, value in edits.items():
            fields[index] = _replace_field(fields[index], value)
        texts[number - 1] = ";".join(fields)
    if file_plan.problems:
        return file_plan
    out = "".join(t + n for t, n in zip(texts, terms)).encode("utf-8")
    file_plan.new = (_UTF8_BOM + out) if bom else out
    file_plan.problems.extend(verify_file_plan(file_plan, columns))
    file_plan.verified = not file_plan.problems
    return file_plan


def verify_file_plan(plan: FilePlan, columns: list[str]) -> list[str]:
    """Re-parse original and new bytes with the loader's parser and prove that only the planned fields changed."""
    problems: list[str] = []

    def parse(raw: bytes):
        body = raw[len(_UTF8_BOM):] if raw.startswith(_UTF8_BOM) else raw
        return parse_table_text(body.decode("utf-8"), len(columns))

    try:
        old_rows, old_rej, old_comments, old_blanks = parse(plan.original)
        new_rows, new_rej, new_comments, new_blanks = parse(plan.new)
    except UnicodeDecodeError as exc:
        return [f"The planned output is not valid UTF-8: {exc}"]
    if plan.original.startswith(_UTF8_BOM) != plan.new.startswith(_UTF8_BOM):
        problems.append("The byte order mark would change.")
    if (len(old_rows), len(old_rej), old_comments, old_blanks) != (len(new_rows), len(new_rej), new_comments, new_blanks):
        problems.append("The number of records, comments or blank lines would change.")
        return problems
    expected = {(c.line, columns.index(c.column)): c.new for c in plan.changes}
    for before, after in zip(old_rows, new_rows):
        if before.line != after.line:
            problems.append(f"Record at line {before.line} moved to line {after.line}.")
            continue
        for index, (b, a) in enumerate(zip(before.values, after.values)):
            want = expected.pop((before.line, index), None)
            if want is not None:
                if a.strip(_BLANKS) != want:
                    problems.append(f"Line {before.line}, {columns[index]}: reads back as {a.strip(_BLANKS)!r}, "
                                    f"expected {want!r}.")
            elif a != b:
                problems.append(f"Line {before.line}, {columns[index]}: an unplanned field would change.")
    problems.extend(f"Line {line}, {columns[index]}: the planned change was not found in the output."
                    for (line, index) in expected)
    old_lines, new_lines = _lines(plan.original), _lines(plan.new)
    changed_lines = {c.line for c in plan.changes}
    if len(old_lines) != len(new_lines):
        problems.append("The number of physical lines would change.")
    else:
        for number, (before, after) in enumerate(zip(old_lines, new_lines), 1):
            if before[1] != after[1]:
                problems.append(f"Line {number}: the line terminator would change.")
            if number not in changed_lines and before[0] != after[0]:
                problems.append(f"Line {number}: an unplanned line would change.")
    return problems
