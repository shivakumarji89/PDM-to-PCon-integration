"""Append-only writers for the five property-creation tables, as in-memory ``FilePlan`` objects. Never writes.

Verified layouts (docs/02_Domain/Engineering/Metatype_Write_Contract_Decisions.md D3, ``mt.inp_descr`` of every
series): ``go_types`` (id;name;format;default;mode;filter), ``go_properties`` (id;key;name;value;variant_code;
variant_value), ``go_propvalues`` (id;name;value;condition), ``go_proporder`` (value;number, ``number`` is ``uint8``),
``go_texts`` (key;language;text). A series whose declared columns differ is refused, not adapted.

A new row is appended after every existing line, so existing rows, comments, blank lines, padding, BOM, encoding and
line endings stay byte-identical (the only possible change to old bytes is a line terminator added after an
unterminated last line). Each new row copies the leading/trailing padding of the file's last data row. A row whose key
is already present is a conflict, never an overwrite. The output is re-parsed and compared with the input; the same
check is returned as ``verifier`` so it can run again on the bytes read back after writing.
"""
from __future__ import annotations

import os
import re

from models.metatype_tables import LoadedTable
from services.metatype.article_write_plan import FilePlan, LineChange
from services.metatype.metatype_table_loader import parse_table_text, split_fields
from services.metatype.text_encoding import Encoding, append_text_lines, detect_encoding

LAYOUTS: dict[str, list[str]] = {
    "go_types": ["id", "name", "format", "default", "mode", "filter"],
    "go_properties": ["id", "key", "name", "value", "variant_code", "variant_value"],
    "go_propvalues": ["id", "name", "value", "condition"],
    "go_proporder": ["value", "number"],
    "go_texts": ["key", "language", "text"],
}
#: columns identifying a record; a new row repeating them is a conflict
KEY_COLUMNS: dict[str, tuple[int, ...]] = {
    "go_types": (0, 1), "go_properties": (0, 1, 2), "go_propvalues": (0, 1, 2), "go_proporder": (0,),
    "go_texts": (0, 1),
}
REQUIRED: dict[str, tuple[int, ...]] = {
    "go_types": (0, 1, 2, 3, 4), "go_properties": (0, 1, 2, 3), "go_propvalues": (0, 1, 2), "go_proporder": (0, 1),
    "go_texts": (0, 1, 2),
}
LANGUAGES = ("en", "de", "fr", "nl")
PROPORDER_MAX = 255            # go_proporder.number is uint8
MODE_MAX = 0xFFFF              # go_types.mode is uint16
_BLANKS = " \t"
_BREAK = re.compile(r"\r\n|\n|\r")
_CODEC = {Encoding.EMPTY: "ascii", Encoding.ASCII: "ascii", Encoding.UTF8: "utf-8", Encoding.UTF8_BOM: "utf-8-sig",
          Encoding.CP1252: "cp1252"}


def _trim(row) -> tuple[str, ...]:
    return tuple(v.strip(_BLANKS) for v in row)


def validate_row(table: str, row: list[str]) -> list[str]:
    problems: list[str] = []
    layout = LAYOUTS[table]
    if len(row) != len(layout):
        return [f"{table}: a row needs {len(layout)} field(s), got {len(row)}."]
    for index, value in enumerate(row):
        if any(c in value for c in (";", '"', "\r", "\n")):
            problems.append(f"{table}.{layout[index]}: {value!r} contains the delimiter, a quote or a line break.")
        if index in REQUIRED[table] and not value.strip(_BLANKS):
            problems.append(f"{table}.{layout[index]} is required.")
    if row[0].lstrip(_BLANKS).startswith("#"):
        problems.append(f"{table}: {row[0]!r} starts with '#' and would become a comment.")
    if table == "go_types" and row[4].strip(_BLANKS):
        if not re.fullmatch(r"\d+", row[4].strip()) or int(row[4]) > MODE_MAX:
            problems.append(f"go_types.mode {row[4]!r} is not an integer 0..{MODE_MAX} (uint16).")
    if table == "go_proporder" and row[1].strip(_BLANKS):
        if not re.fullmatch(r"\d+", row[1].strip()) or not 1 <= int(row[1]) <= PROPORDER_MAX:
            problems.append(f"go_proporder.number {row[1]!r} must be an integer 1..{PROPORDER_MAX} (uint8).")
    if table == "go_texts" and row[1].strip(_BLANKS) not in LANGUAGES:
        problems.append(f"go_texts.language {row[1]!r} is not one of {', '.join(LANGUAGES)}.")
    return problems


def _style(template: str | None, row: list[str]) -> str:
    """Copy the last data row's padding around each field, so the new row looks like its neighbours."""
    if template is not None and '"' not in template:
        fields = split_fields(template)
        if len(fields) == len(row):
            out = []
            for old, value in zip(fields, row):
                if old.strip(_BLANKS) and value:
                    lead = old[:len(old) - len(old.lstrip(_BLANKS))]
                    trail = old[len(old.rstrip(_BLANKS)):]
                    out.append(lead + value + trail)
                else:
                    out.append(value)
            return ";".join(out)
    return ";".join(row)


def plan_append(table: str, loaded: LoadedTable | None, rows: list[list[str]], fallback: Encoding | None = None,
                skip_existing: bool = False) -> FilePlan:
    """Plan appending ``rows`` to the table's file. ``skip_existing`` drops rows already present with identical
    values (idempotent re-run); a key present with *different* values is always a conflict."""
    plan = FilePlan(loaded.path if loaded is not None else table)
    layout = LAYOUTS[table]
    if loaded is None or not loaded.path:
        plan.problems.append(f"{table} is not declared by this series' schema; it is not written.")
        return plan
    if [c.casefold() for c in loaded.columns] != layout:
        plan.problems.append(f"{table}: the declared layout {loaded.columns} is not the verified layout {layout}; "
                             "it is not written.")
        return plan
    path = loaded.path
    if os.path.islink(path) or not os.path.isfile(path):
        plan.problems.append(f"{table}: {path} is not a regular file.")
        return plan
    with open(path, "rb") as handle:
        raw = handle.read()
    plan.original = raw
    encoding = detect_encoding(raw)
    if encoding is Encoding.AMBIGUOUS:
        plan.problems.append(f"{table}: the file's encoding is ambiguous; it is not rewritten.")
        return plan
    codec = _CODEC[encoding]
    old_rows, _, old_comments, old_blanks = parse_table_text(raw.decode(codec), len(layout))
    keys = KEY_COLUMNS[table]
    existing = {tuple(_trim(r.values)[i] for i in keys): _trim(r.values) for r in old_rows}
    new_rows: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        problems = validate_row(table, row)
        plan.problems.extend(problems)
        if problems:
            continue
        trimmed = _trim(row)
        key = tuple(trimmed[i] for i in keys)
        if key in existing:
            if skip_existing and existing[key] == trimmed:
                continue
            plan.problems.append(f"{table}: {' / '.join(key)} is already defined"
                                 + (" with different values." if existing[key] != trimmed else "."))
            continue
        if key in seen:
            plan.problems.append(f"{table}: {' / '.join(key)} appears twice in the new rows.")
            continue
        seen.add(key)
        new_rows.append(row)
    if plan.problems or not new_rows:
        return plan
    template = None
    for line in reversed(_BREAK.split(raw.decode(codec, errors="replace").lstrip("﻿"))):
        if line.strip(_BLANKS) and not line.startswith("#"):
            template = line
            break
    lines = [_style(template, row) for row in new_rows]
    appended = append_text_lines(raw, lines, fallback=fallback, default_eol="\r\n")
    if not appended.ok:
        plan.problems.extend(f"{table}: {p}" for p in appended.problems)
        return plan
    plan.new = appended.data
    expected = [_trim(r) for r in new_rows]
    old_values = [_trim(r.values) for r in old_rows]
    new_codec = _CODEC[appended.encoding]

    def verifier(data: bytes) -> list[str]:
        return _verify(table, raw, data, encoding, new_codec, len(layout), old_comments, old_blanks, old_values,
                       expected)

    plan.verifier = verifier
    plan.problems.extend(verifier(plan.new))
    first_line = len(_BREAK.split(raw.decode(codec, errors="replace"))) - (1 if raw.endswith((b"\n", b"\r")) else 0) + 1
    plan.changes = [LineChange(first_line + i, "row", "", line) for i, line in enumerate(lines)]
    plan.verified = not plan.problems
    return plan


def _verify(table, original, data, old_encoding, codec, columns, old_comments, old_blanks, old_values,
            expected) -> list[str]:
    problems: list[str] = []
    if not data.startswith(original):
        stripped = original.rstrip(b"\r\n")
        if not data.startswith(stripped) or data[len(stripped):len(original)].strip(b"\r\n") != b"":
            problems.append(f"{table}: existing bytes would change.")
    if old_encoding is Encoding.UTF8_BOM and not data.startswith(b"\xef\xbb\xbf"):
        problems.append(f"{table}: the byte order mark would be lost.")
    try:
        text = data.decode(codec)
    except UnicodeDecodeError as exc:
        return problems + [f"{table}: the output cannot be decoded as {codec}: {exc}"]
    rows, _, comments, blanks = parse_table_text(text, columns)
    if (comments, blanks) != (old_comments, old_blanks):
        problems.append(f"{table}: the number of comments or blank lines would change.")
    count = len(old_values)
    if len(rows) != count + len(expected):
        problems.append(f"{table}: expected {count + len(expected)} records, found {len(rows)}.")
        return problems
    if [_trim(r.values) for r in rows[:count]] != old_values:
        problems.append(f"{table}: an existing record would change.")
    if [_trim(r.values) for r in rows[count:]] != list(expected):
        problems.append(f"{table}: the appended records do not read back as planned.")
    return problems
