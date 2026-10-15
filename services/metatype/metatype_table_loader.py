"""Read-only loader for a Metatype family's ``go_*.csv`` tables.

Turns the files declared by a family's ``mt.inp_descr`` into raw in-memory rows.
It does not interpret values, resolve relationships or validate Metatype rules,
and it never writes, renames or executes anything.

File format (MT_1.18.0 section 2, checked against every real ``go_*.csv`` in the
HMX repository):

* one record per line; separator ``;``; UTF-8 or ASCII.
* lines starting with ``#`` are comments; lines of only blanks/tabs are ignored.
* a field that *starts* with ``"`` is quoted: ``""`` is a literal quote and the
  field must end at the closing quote. Any other field is taken literally, so a
  ``"`` inside it is data (real example: ``Farben "Dipped in colour"``).
* column names and the expected field count come from ``mt.inp_descr``; the CSV
  files carry no header row.

Observed deviations, reported rather than repaired:

* 40 real ``go_texts.csv`` files are not valid UTF-8 (bytes such as ``E4``/``FC``/
  ``E9`` look like Latin-1/cp1252). Decoding is strict by default and fails with
  ``DECODE_ERROR``; ``fallback_encoding`` is an explicit opt-in.
* ``oe1/go_actions.csv`` has lines with one field instead of nine.
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from models.metatype_tables import (
    LoadDiagnostic,
    LoadedTable,
    LoadStatus,
    MetatypeFamilyTables,
    RejectedLine,
    TableLoadState,
    TableRow,
)
from services.metatype.repository_scanner import OPTIONAL_TABLES, SCHEMA_FILE
from services.metatype.schema_parser import MAX_SCHEMA_BYTES, SchemaTable, parse_mt_schema

LOADER_VERSION = "1.0.0"

#: Real tables are < 1 MB; refuse anything absurd instead of exhausting memory.
MAX_TABLE_BYTES = 64 * 1024 * 1024
_UTF8_BOM = b"\xef\xbb\xbf"
_LINE_BREAK = re.compile(r"\r\n|\n|\r")


class QuoteError(ValueError):
    """A quoted field was not closed or was followed by text."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def split_fields(line: str) -> list[str]:
    """Split one record on ``;`` using the Metatype quoting rule (see module doc)."""
    fields: list[str] = []
    n = len(line)
    i = 0
    while True:
        if i < n and line[i] == '"':
            parts: list[str] = []
            j = i + 1
            while True:
                k = line.find('"', j)
                if k < 0:
                    raise QuoteError("UNTERMINATED_QUOTE", f"quoted field starting at column {i + 1} is not closed")
                parts.append(line[j:k])
                if k + 1 < n and line[k + 1] == '"':
                    parts.append('"')
                    j = k + 2
                    continue
                break
            fields.append("".join(parts))
            i = k + 1
            if i < n and line[i] != ";":
                raise QuoteError("TEXT_AFTER_QUOTE", f"text after the closing quote at column {i + 1}")
        else:
            k = line.find(";", i)
            if k < 0:
                fields.append(line[i:])
                return fields
            fields.append(line[i:k])
            i = k
        if i >= n:
            return fields
        i += 1  # skip ';'
        if i == n:
            fields.append("")
            return fields


def parse_table_text(text: str, column_count: int):
    """Parse decoded table text into (rows, rejected, comment_count, blank_count)."""
    rows: list[TableRow] = []
    rejected: list[RejectedLine] = []
    comments = blanks = 0
    lines = _LINE_BREAK.split(text)
    if lines and lines[-1] == "":
        lines.pop()
    for number, line in enumerate(lines, 1):
        if not line.strip(" \t"):
            blanks += 1
            continue
        if line.startswith("#"):
            comments += 1
            continue
        try:
            values = split_fields(line)
        except QuoteError as exc:
            rejected.append(RejectedLine(number, line, exc.code, str(exc)))
            continue
        if len(values) != column_count:
            rejected.append(RejectedLine(
                number, line, "FIELD_COUNT_MISMATCH",
                f"expected {column_count} field(s), found {len(values)}"))
            continue
        rows.append(TableRow(number, tuple(values)))
    return rows, rejected, comments, blanks


class MetatypeTableLoader:
    """Load one family's declared ``go_*`` tables from ``<root>/<family>/<number>/``."""

    def __init__(self, fallback_encoding: str | None = None) -> None:
        #: Opt-in decoding used only when strict UTF-8 fails (e.g. ``"cp1252"``).
        self.fallback_encoding = fallback_encoding

    # -- filesystem seams (overridden in tests) --------------------------------
    def _list_dir(self, path: Path) -> list[os.DirEntry]:
        with os.scandir(path) as iterator:
            return sorted(iterator, key=lambda e: e.name.casefold())

    def _read_bytes(self, path: str, limit: int) -> bytes:
        with open(path, "rb") as handle:
            return handle.read(limit + 1)

    # -- public API ----------------------------------------------------------------
    def load_family(
        self,
        root: str | Path,
        family_id: str,
        directory: str | None = None,
        tables: Iterable[str] | None = None,
    ) -> MetatypeFamilyTables:
        """Load a family. ``tables`` (declared table names) limits which files are read; ``None`` loads all."""
        wanted = None if tables is None else set(tables)
        result = MetatypeFamilyTables(
            repository_root=str(root), family_id=family_id,
            loaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            loader_version=LOADER_VERSION, status=LoadStatus.OK,
        )
        data_dir = self._resolve_directory(result, Path(root), family_id, directory)
        if data_dir is None:
            result.status = LoadStatus.FAILED
            return result

        try:
            entries = self._list_dir(data_dir)
        except OSError as exc:
            self._error(result, "DIRECTORY_UNREADABLE", f"Cannot list {data_dir}: {exc}")
            result.status = LoadStatus.FAILED
            return result
        files = {e.name.casefold(): e for e in entries if _is_file(e)}

        schema = self._read_schema(result, files)
        if schema is None:
            result.status = LoadStatus.FAILED
            return result

        declared_files = {t.file_name.casefold() for t in schema}
        result.unlisted_go_files = sorted(
            e.name for key, e in files.items() if key.startswith("go_") and key not in declared_files)
        for table in schema:
            if wanted is not None and table.name not in wanted:
                continue  # not requested: its file is neither opened nor decoded
            result.tables.append(self._load_table(table, files.get(table.file_name.casefold()), data_dir))

        bad = {TableLoadState.MALFORMED, TableLoadState.DECODE_ERROR, TableLoadState.UNREADABLE}
        if any(t.state in bad for t in result.tables) or any(
            t.state is TableLoadState.MISSING and t.table.casefold() not in OPTIONAL_TABLES
            for t in result.tables
        ):
            result.status = LoadStatus.PARTIAL
        return result

    # -- directory / schema -----------------------------------------------------------
    def _resolve_directory(self, result, root: Path, family_id: str, directory: str | None) -> Path | None:
        if (not family_id or family_id in (".", "..") or any(sep in family_id for sep in ("/", "\\", ":"))
                or (directory is not None and (not directory.isdigit()))):
            self._error(result, "INVALID_SELECTION", "Family id must be one folder name and the directory a number.")
            return None
        family_path = root / family_id
        try:
            if not family_path.is_dir():
                self._error(result, "FAMILY_NOT_FOUND", f"Family directory not found: {family_path}")
                return None
            children = self._list_dir(family_path)
        except OSError as exc:
            self._error(result, "FAMILY_UNREADABLE", f"Cannot read family directory: {exc}")
            return None
        numbered = [e for e in children if e.name.isdigit() and _is_dir(e)]
        for entry in numbered:
            if _is_link(entry):
                self._warn(result, "LINKED_DIRECTORY_SKIPPED", f"{entry.name} is a link and was not followed.")
        usable = [e for e in numbered if not _is_link(e)]
        if directory is not None:
            chosen = [e for e in usable if e.name == directory]
        else:
            chosen = usable
        if len(chosen) != 1:
            code = "NUMBERED_DIRECTORY_NOT_FOUND" if not chosen else "AMBIGUOUS_NUMBERED_DIRECTORY"
            names = ", ".join(e.name for e in usable) or "none"
            self._error(result, code, f"Expected exactly one numbered directory (found: {names}); not guessing.")
            return None
        result.directory = chosen[0].name
        result.directory_path = chosen[0].path
        return Path(chosen[0].path)

    def _read_schema(self, result, files) -> list[SchemaTable] | None:
        entry = files.get(SCHEMA_FILE)
        if entry is None:
            self._error(result, "SCHEMA_MISSING",
                        f"{SCHEMA_FILE} not found; column names and the expected table set are unknown.",
                        file=SCHEMA_FILE)
            return None
        if _is_link(entry):
            self._error(result, "SCHEMA_LINKED", f"{SCHEMA_FILE} is a link and was not read.", file=SCHEMA_FILE)
            return None
        try:
            raw = self._read_bytes(entry.path, MAX_SCHEMA_BYTES)
        except OSError as exc:
            self._error(result, "SCHEMA_UNREADABLE", f"Cannot read {SCHEMA_FILE}: {exc}", file=SCHEMA_FILE)
            return None
        schema = parse_mt_schema(raw.decode("utf-8", errors="replace"))
        if not schema:
            self._error(result, "SCHEMA_NO_TABLES", f"{SCHEMA_FILE} declares no tables.", file=SCHEMA_FILE)
            return None
        result.schema_source = SCHEMA_FILE
        for table in schema:
            for problem in table.problems:
                self._warn(result, "SCHEMA_DECLARATION_PROBLEM", f"{table.name}: {problem}", table=table.name,
                           file=SCHEMA_FILE)
        return schema

    # -- one table ------------------------------------------------------------------
    def _load_table(self, schema: SchemaTable, entry, data_dir: Path) -> LoadedTable:
        columns = list(schema.columns)
        path = entry.path if entry is not None else str(data_dir / schema.file_name)
        table = LoadedTable(schema.name, schema.file_name, path, columns, TableLoadState.MISSING)

        def diag(severity, code, message, line=None):
            table.diagnostics.append(LoadDiagnostic(severity, code, message, schema.name, schema.file_name, line))

        if entry is None:
            if schema.name.casefold() in OPTIONAL_TABLES:
                diag("warning", "TABLE_MISSING", "Optional declared table has no file.")
            else:
                diag("error", "TABLE_MISSING", "Declared table has no file.")
            return table
        if _is_link(entry):
            table.state = TableLoadState.UNREADABLE
            diag("error", "LINKED_FILE_NOT_FOLLOWED", "File is a link and was not read.")
            return table
        if not columns:
            table.state = TableLoadState.UNREADABLE
            diag("error", "NO_COLUMNS", "mt.inp_descr declares no fields for this table.")
            return table
        try:
            raw = self._read_bytes(entry.path, MAX_TABLE_BYTES)
        except OSError as exc:
            table.state = TableLoadState.UNREADABLE
            diag("error", "FILE_UNREADABLE", f"Cannot read file: {exc}")
            return table
        table.size_bytes = len(raw)
        if len(raw) > MAX_TABLE_BYTES:
            table.state = TableLoadState.UNREADABLE
            table.size_bytes = None
            diag("error", "FILE_TOO_LARGE", f"File exceeds the {MAX_TABLE_BYTES}-byte limit and was not loaded.")
            return table
        if not raw:
            table.state = TableLoadState.EMPTY
            return table

        text = self._decode(raw, table, diag)
        if text is None:
            return table

        table.rows, table.rejected_lines, table.comment_lines, table.blank_lines = parse_table_text(
            text, len(columns))
        for item in table.rejected_lines:
            diag("error", item.code, item.reason, item.line)
        if table.rejected_lines:
            table.state = TableLoadState.MALFORMED
        elif table.rows:
            table.state = TableLoadState.VALID
        else:
            table.state = TableLoadState.NO_DATA
        return table

    def _decode(self, raw: bytes, table: LoadedTable, diag) -> str | None:
        if raw.startswith(_UTF8_BOM):
            raw = raw[len(_UTF8_BOM):]
            diag("warning", "BOM_PRESENT", "UTF-8 byte order mark found and skipped.")
        try:
            table.encoding = "utf-8"
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            line = raw.count(b"\n", 0, exc.start) + 1
            if self.fallback_encoding:
                try:
                    text = raw.decode(self.fallback_encoding)
                except (UnicodeDecodeError, LookupError) as fallback_exc:
                    table.encoding = ""
                    table.state = TableLoadState.DECODE_ERROR
                    diag("error", "DECODE_ERROR",
                         f"Not valid UTF-8 (byte {exc.start}, line {line}) and fallback "
                         f"{self.fallback_encoding!r} failed: {fallback_exc}", line)
                    return None
                table.encoding = self.fallback_encoding
                diag("warning", "ENCODING_FALLBACK",
                     f"Not valid UTF-8 (byte {exc.start}, line {line}); decoded as {self.fallback_encoding}. "
                     "The manual only permits UTF-8 or ASCII.", line)
                return text
            table.encoding = ""
            table.state = TableLoadState.DECODE_ERROR
            diag("error", "DECODE_ERROR",
                 f"Not valid UTF-8 (invalid byte 0x{raw[exc.start]:02X} at offset {exc.start}, line {line}); "
                 "no rows were loaded.", line)
            return None

    # -- diagnostics helpers ----------------------------------------------------------
    @staticmethod
    def _error(result, code, message, table="", file=""):
        result.diagnostics.append(LoadDiagnostic("error", code, message, table, file))

    @staticmethod
    def _warn(result, code, message, table="", file=""):
        result.diagnostics.append(LoadDiagnostic("warning", code, message, table, file))


def _is_link(entry: os.DirEntry) -> bool:
    try:
        return entry.is_symlink() or bool(getattr(entry, "is_junction", lambda: False)())
    except OSError:
        return True  # cannot tell: do not follow


def _is_dir(entry: os.DirEntry) -> bool:
    try:
        return entry.is_dir()
    except OSError:
        return False


def _is_file(entry: os.DirEntry) -> bool:
    try:
        return entry.is_file()
    except OSError:
        return False
