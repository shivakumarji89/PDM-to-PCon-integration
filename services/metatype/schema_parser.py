"""Parser for the table declarations in a family's ``mt.inp_descr``.

Shared by the repository scanner and the table loader so both agree on which
tables a family declares and what their columns are.

Observed format (all 49 real files; the EasternGraphics header says "GO III
(MT) Input Description, Version 1.16"):

    table   go_types<TAB>go_types.csv<TAB><TAB>csv
    fields  6
    field   1  id<TAB><TAB>vstring<TAB>delim ; trim hidx link
    ...
    comment
    ...text and table declarations that are NOT compiled...
    end comment

Blocks between ``comment`` and ``end comment`` are skipped. The real files use
this to disable ``go_propindex``/``go_propmapping``. The block syntax is inferred
from those files; no document in the project describes it (unresolved).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Upper bound for reading ``mt.inp_descr`` (real files are ~9 KB); shared by scanner and loader.
MAX_SCHEMA_BYTES = 1024 * 1024

_TABLE = re.compile(r"^table\s+(\S+)\s+(\S+)", re.IGNORECASE)
_FIELDS = re.compile(r"^fields\s+(\d+)", re.IGNORECASE)
_FIELD = re.compile(r"^field\s+(\d+)\s+(\S+)", re.IGNORECASE)


@dataclass
class SchemaTable:
    name: str
    file_name: str
    #: Column names ordered by their declared position.
    columns: list[str] = field(default_factory=list)
    #: Value of the ``fields N`` line, ``None`` if absent.
    declared_field_count: int | None = None
    #: Problems found while parsing this declaration (never silently dropped).
    problems: list[str] = field(default_factory=list)


def parse_mt_schema(text: str) -> list[SchemaTable]:
    """Return the compiled table declarations in file order."""
    tables: list[SchemaTable] = []
    current: SchemaTable | None = None
    positions: list[int] = []
    in_comment = False

    def close() -> None:
        if current is None:
            return
        if current.declared_field_count is not None and current.declared_field_count != len(current.columns):
            current.problems.append(
                f"'fields {current.declared_field_count}' but {len(current.columns)} field line(s)")
        if positions != list(range(1, len(positions) + 1)):
            current.problems.append("field positions are not 1..N in order")
        if len(set(current.columns)) != len(current.columns):
            current.problems.append("duplicate column names")

    for raw in text.splitlines():
        line = raw.strip()
        lowered = line.lower()
        if lowered == "comment":
            in_comment = True
            continue
        if lowered == "end comment":
            in_comment = False
            continue
        if in_comment:
            continue
        match = _TABLE.match(line)
        if match:
            close()
            current = SchemaTable(match.group(1), match.group(2))
            positions = []
            tables.append(current)
            continue
        if current is None:
            continue
        match = _FIELDS.match(line)
        if match:
            current.declared_field_count = int(match.group(1))
            continue
        match = _FIELD.match(line)
        if match:
            positions.append(int(match.group(1)))
            current.columns.append(match.group(2))
    close()
    return tables
