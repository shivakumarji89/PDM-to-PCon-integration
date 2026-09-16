"""Read an existing OCD MDB into a structured, maintenance-friendly model.

This service deliberately sits *above* :class:`MDBService`.  MDBService remains
our only low-level MDB I/O gateway; this module owns only the domain-level
selection, normalization, and relationship indexing needed by Maintenance and
future Metatype work.

The reader is intentionally non-mutating.  It never writes to the MDB and it
keeps pricing out of the generic structural read path.  Price data can be read
explicitly through ``include_prices`` so callers do not accidentally treat
pricing as ordinary product structure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from services.base_service import BaseService


# Product/engineering tables already used by OcdExportService.  Keep this list
# centralized so Maintenance and Metatype consume the same structural scope.
STRUCTURAL_TABLES: tuple[str, ...] = (
    "tCOMd_Text",
    "tCOMd_RelObj",
    "tCOMd_Relation",
    "tCOMd_CodeScheme",
    "tCOMd_Class",
    "tCOMd_Property",
    "tCOMd_PropValue",
    "tCOMd_Article",
    "tCOMd_ArticleClass",
    "tCOMd_ArtBase",
    "tCOMd_RelObjRel",
    "tCOMd_Table",
    "tCOMd_TableColumn",
    "tCOMd_TableLine",
)

PRICE_TABLES: tuple[str, ...] = (
    "tCOMd_Price",
    "tCOMd_GlobalPrice",
)

PACKAGE_TABLES: tuple[str, ...] = (
    "tCOMd_Package",
    "tCOMd_ComGroup",
)

READABLE_TABLES = frozenset(PACKAGE_TABLES + STRUCTURAL_TABLES + PRICE_TABLES)


@dataclass(frozen=True)
class MdbTableData:
    """Rows read from one MDB table."""

    name: str
    rows: tuple[dict[str, Any], ...] = ()

    @property
    def count(self) -> int:
        return len(self.rows)

    @property
    def columns(self) -> tuple[str, ...]:
        if not self.rows:
            return ()
        # Preserve the column order returned by Access for stable diagnostics.
        return tuple(self.rows[0].keys())


@dataclass
class MdbPackageData:
    """Non-mutating structural snapshot of an existing OCD MDB."""

    path: str
    package: dict[str, Any] | None = None
    com_group: dict[str, Any] | None = None
    tables: dict[str, MdbTableData] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def table_counts(self) -> dict[str, int]:
        return {name: table.count for name, table in self.tables.items()}

    def rows(self, table: str) -> tuple[dict[str, Any], ...]:
        data = self.tables.get(table)
        return data.rows if data else ()

    def first(self, table: str) -> dict[str, Any] | None:
        rows = self.rows(table)
        return rows[0] if rows else None


class MdbReverseEngineeringService(BaseService):
    """Read and normalize an existing OCD MDB without modifying it.

    The service uses ``context.mdb_service`` for every database operation.  It
    therefore does not introduce another OLEDB/PowerShell connection or another
    MDB abstraction.
    """

    def read(
        self,
        mdb_path: str | Path,
        *,
        include_prices: bool = False,
        tables: Iterable[str] | None = None,
    ) -> MdbPackageData:
        """Read the selected OCD tables from ``mdb_path``.

        By default only package metadata and structural/engineering tables are
        loaded.  Pricing is opt-in because it has its own maintenance pipeline.
        ``tables`` may narrow the read to a specific allow-listed set.
        """
        path = Path(mdb_path)
        result = MdbPackageData(path=str(path))

        if not path.is_file():
            result.notes.append(f"MDB not found: {path}")
            return result

        requested = tuple(tables) if tables is not None else (
            STRUCTURAL_TABLES + (PRICE_TABLES if include_prices else ())
        )
        invalid = [table for table in requested if table not in READABLE_TABLES]
        if invalid:
            raise ValueError(f"Unsupported MDB table(s): {', '.join(invalid)}")

        package_rows = self._read(path, "tCOMd_Package")
        group_rows = self._read(path, "tCOMd_ComGroup")
        result.package = package_rows[0] if package_rows else None
        result.com_group = group_rows[0] if group_rows else None

        if result.package is None:
            result.notes.append("tCOMd_Package is empty.")
        if result.com_group is None:
            result.notes.append("tCOMd_ComGroup is empty.")

        for table in requested:
            rows = self._read(path, table)
            result.tables[table] = MdbTableData(
                name=table,
                rows=tuple(rows),
            )

        return result

    def read_table(self, mdb_path: str | Path, table: str) -> MdbTableData:
        """Read one allow-listed table through the shared MDB service."""
        self._validate_table(table)
        rows = self._read(Path(mdb_path), table)
        return MdbTableData(name=table, rows=tuple(rows))

    def inspect_schema(self, mdb_path: str | Path, table: str) -> tuple[str, ...]:
        """Return the columns present in a live MDB table.

        This is intentionally implemented as ``SELECT TOP 1 *`` rather than a
        second schema/ADO abstraction, keeping all MDB access in MDBService.
        Empty tables cannot expose columns through the current MDBService API;
        in that case an empty tuple is returned.
        """
        return self.read_table(mdb_path, table).columns

    def table_counts(
        self,
        mdb_path: str | Path,
        *,
        include_prices: bool = False,
    ) -> dict[str, int]:
        """Return row counts using the same structural scope as ``read``."""
        data = self.read(mdb_path, include_prices=include_prices)
        return data.table_counts

    def _read(self, path: Path, table: str) -> list[dict[str, Any]]:
        self._validate_table(table)
        # Table names are constants from READABLE_TABLES, never user-supplied
        # SQL fragments.  Brackets protect Access identifiers safely.
        return self.context.mdb_service.read_table(
            path,
            f"SELECT * FROM [{table}]",
        )

    @staticmethod
    def _validate_table(table: str) -> None:
        if table not in READABLE_TABLES:
            raise ValueError(f"Unsupported MDB table: {table}")
