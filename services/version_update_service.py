"""Bulk product-version updater for published OCD + ODB packages.

The export version of a series is stored as ``Major.Minor.Build`` in BOTH the
commercial and geometry databases of its package folder:

* OCD - ``pcr_data_com_ocd.mdb`` -> ``tCOMd_Package.reg_Version{Major,Minor,Build}``
* ODB - ``pcr_data_geo_odb.mdb`` -> ``tGEOd_Package.reg_Version{Major,Minor,Build}``

This service discovers the series under a repository (reusing the price-update
package discovery, so the same non-product-folder guard and multi-root support
apply), reads each one's current OCD/ODB version, and writes a user-keyed version
into the selected series' both files. Optionally stamps the release date.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from services.base_service import BaseService
from services.price_update_service import _mdb_date_literal

_ODB_FILE = "pcr_data_geo_odb.mdb"
#: The package table that carries the version, per database.
_PACKAGE_TABLE = {"ocd": "tCOMd_Package", "odb": "tGEOd_Package"}


@dataclass
class SeriesVersion:
    """One series' folder + its current OCD/ODB export versions."""

    folder: str
    program: str = ""
    ocd_path: str = ""
    odb_path: str = ""
    ocd_version: str = ""   # "M.m.b" or "" when absent/unreadable
    odb_version: str = ""


@dataclass
class VersionUpdateResult:
    """Outcome of writing the version into one series' two databases."""

    series: str = ""
    ocd_updated: bool = False
    odb_updated: bool = False
    error: str | None = None


class VersionUpdateService(BaseService):
    """Read + bulk-write the export version across OCD and ODB packages."""

    @staticmethod
    def parse_version(text: str) -> tuple[int, int, int] | None:
        """``"1.34.0"`` -> ``(1, 34, 0)``. Needs three numeric parts."""
        parts = re.findall(r"\d+", text or "")
        if len(parts) < 3:
            return None
        return int(parts[0]), int(parts[1]), int(parts[2])

    def series_folders(self, repository: str | Path) -> list[Path]:
        """The product folders under the repository (fast - just the OCD-file
        glob, with the shared non-product-folder guard)."""
        return [ocd.parent for ocd in
                self.context.price_update_service._discover_packages(repository, is_mdb=True)]

    def read_series(self, folders, progress=None) -> list[SeriesVersion]:
        """Read each folder's current OCD + ODB versions. ``progress(done, total,
        text)`` is called per series for a progress bar."""
        folders = list(folders)
        out: list[SeriesVersion] = []
        for i, folder in enumerate(folders, 1):
            folder = Path(folder)
            if progress:
                progress(i, len(folders), folder.name)
            ocd = folder / "pcr_data_com_ocd.mdb"
            odb = folder / _ODB_FILE
            sv = SeriesVersion(folder=str(folder),
                               ocd_path=str(ocd) if ocd.is_file() else "",
                               odb_path=str(odb) if odb.is_file() else "")
            if sv.ocd_path:
                sv.program, sv.ocd_version = self._read_version(sv.ocd_path, "ocd")
            if sv.odb_path:
                prog, sv.odb_version = self._read_version(sv.odb_path, "odb")
                sv.program = sv.program or prog
            sv.program = sv.program or folder.name
            out.append(sv)
        return out

    def _read_version(self, mdb: str, db: str) -> tuple[str, str]:
        """``(program, "M.m.b")`` from a package table; ``("", "")`` if unreadable."""
        table = _PACKAGE_TABLE[db]
        try:
            rows = self.context.mdb_service.read_table(
                mdb, f"SELECT reg_ProgramCode, reg_VersionMajor, reg_VersionMinor, "
                     f"reg_VersionBuild FROM [{table}]")
        except OSError:
            return "", ""
        if not rows:
            return "", ""
        r = rows[0]
        version = (f"{r.get('reg_VersionMajor')}.{r.get('reg_VersionMinor')}."
                   f"{r.get('reg_VersionBuild')}")
        return str(r.get("reg_ProgramCode") or ""), version

    def update(
        self, series, major: int, minor: int, build: int, progress=None,
    ) -> list[VersionUpdateResult]:
        """Write ``major.minor.build`` into every selected series' OCD + ODB
        package rows and stamp today's release date."""
        series = list(series)
        results: list[VersionUpdateResult] = []
        for i, sv in enumerate(series, 1):
            if progress:
                progress(i, len(series), sv.program or Path(sv.folder).name)
            results.append(self._update_one(sv, major, minor, build))
        return results

    def _update_one(
        self, sv: SeriesVersion, major: int, minor: int, build: int
    ) -> VersionUpdateResult:
        result = VersionUpdateResult(series=sv.program or Path(sv.folder).name)
        version_fields: dict[str, Any] = {
            "reg_VersionMajor": major, "reg_VersionMinor": minor, "reg_VersionBuild": build,
        }
        release = {"reg_ReleaseDate": _mdb_date_literal(datetime.now().strftime("%Y%m%d"))}
        svc = self.context.mdb_service
        for db, path in (("ocd", sv.ocd_path), ("odb", sv.odb_path)):
            if not path or result.error is not None:
                continue
            table = _PACKAGE_TABLE[db]
            # The version (integers) and the release date (a datetime) must be
            # separate updates: ADODB rejects an int and a datetime field set in
            # the same recordset update ("Specified cast is not valid").
            ver = svc.execute_batch(path, [{"op": "update", "table": table, "set": version_fields}])
            dated = svc.execute_batch(
                path, [{"op": "update", "table": table, "set": release}]) if ver.ok else None
            updated = ver.ok and dated is not None and dated.ok
            if db == "ocd":
                result.ocd_updated = updated
            else:
                result.odb_updated = updated
            if not ver.ok:
                result.error = ver.first_error()
            elif dated is not None and not dated.ok:
                result.error = dated.first_error()
        return result


# -- repository data context / lineage -------------------------------------

@dataclass
class SourceLocation:
    """Traceable location of one logical value in a source system."""

    system: str
    path: str = ""
    file: str = ""
    table: str = ""
    column: str = ""
    relationship: str = ""
    status: str = "known"


@dataclass
class DataLineageRecord:
    """Value plus repository origin and known PDM equivalent."""

    key: str
    value: Any = None
    fetch_status: str = "not_fetched"
    sources: list[SourceLocation] = field(default_factory=list)
    pdm_mapping_status: str = "not_checked"
    notes: str = ""


@dataclass
class RepositoryProductContext:
    """Read-only cross-source context created for one existing series."""

    repository_path: str
    series_name: str
    category: str = ""
    records: dict[str, DataLineageRecord] = field(default_factory=dict)
    pdm_match_count: int = 0
    pdm_match_status: str = "not_checked"
    pdm_product_id: str | None = None


class RepositoryContextService(BaseService):
    """Build a traceable repository -> PDM context for an existing series.

    Phase 1 intentionally loads identity metadata only. Articles, properties,
    relations and pricing can extend the same context later instead of creating
    separate, untraceable reverse-loading paths.
    """

    _OCD_FILE = "pcr_data_com_ocd.mdb"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._active: RepositoryProductContext | None = None

    @property
    def active_context(self) -> RepositoryProductContext | None:
        return self._active

    def clear(self) -> None:
        self._active = None

    def open_series(self, repository_path: str | Path) -> RepositoryProductContext:
        folder = Path(repository_path)
        series_name = folder.name
        category = self._category_from_path(folder)

        records = {
            "name": self._record(
                "name",
                series_name,
                SourceLocation(system="repository", path=str(folder)),
            ),
            "code": self._record(
                "code",
                None,
                SourceLocation(
                    system="repository",
                    path=str(folder),
                    file=self._OCD_FILE,
                    table="tCOMd_Package",
                    column="reg_ProgramCode",
                ),
            ),
            "category": self._record(
                "category",
                category or None,
                SourceLocation(
                    system="repository",
                    path=str(folder),
                    relationship="Workspace root identifies Seating/Tables",
                ),
            ),
            "catalogue": self._record("catalogue", None),
        }

        # Store the PDM locations even before an actual value match is found.
        records["name"].sources.append(
            SourceLocation(system="pdm", table="Product", column="Name", status="mapped")
        )
        records["code"].sources.append(
            SourceLocation(system="pdm", table="Product", column="Product", status="mapped")
        )
        records["category"].sources.append(
            SourceLocation(
                system="pdm",
                table="ProductRange / CatalogueProductCategories",
                column="Name",
                relationship="Product.ProductRangeId -> ProductRange.ProductCategoryId",
                status="mapped",
            )
        )
        records["catalogue"].sources.append(
            SourceLocation(
                system="pdm",
                table="Catalogue",
                column="Name",
                relationship="Product -> Item -> CatalogueItems/CatalogueItemsUnreleased -> Catalogue",
                status="mapped",
            )
        )

        self._read_repository_program(folder, records["code"])

        active = RepositoryProductContext(
            repository_path=str(folder),
            series_name=series_name,
            category=category,
            records=records,
        )
        self._cross_check_pdm(active)
        self._active = active
        return active

    @staticmethod
    def _record(
        key: str,
        value: Any,
        source: SourceLocation | None = None,
    ) -> DataLineageRecord:
        record = DataLineageRecord(
            key=key,
            value=value,
            fetch_status="fetched" if value not in (None, "") else "not_available",
        )
        if source is not None:
            record.sources.append(source)
        return record

    def _read_repository_program(
        self, folder: Path, code_record: DataLineageRecord
    ) -> None:
        ocd_path = folder / self._OCD_FILE
        if not ocd_path.is_file():
            code_record.notes = "Commercial package database not found."
            return
        rows = self.context.mdb_service.read_table(
            ocd_path,
            "SELECT reg_ProgramCode FROM [tCOMd_Package]",
        )
        if rows:
            value = str(rows[0].get("reg_ProgramCode") or "").strip()
            if value:
                code_record.value = value
                code_record.fetch_status = "fetched"
                return
        code_record.notes = "reg_ProgramCode is empty or unavailable."

    def _cross_check_pdm(self, active: RepositoryProductContext) -> None:
        """Find candidates without silently treating a fuzzy result as a match."""
        name = active.series_name.strip()
        code = str(active.records["code"].value or "").strip()
        candidates = {}
        try:
            if name:
                for product in self.context.pdm_service.search_products_by_name(name, 25):
                    candidates[str(product.id)] = product
            if code:
                for product in self.context.pdm_service.search_products_by_code(code, 25):
                    candidates[str(product.id)] = product
        except Exception as exc:
            active.pdm_match_status = "unavailable"
            for record in active.records.values():
                record.pdm_mapping_status = "connection_unavailable"
            active.records["name"].notes = f"PDM cross-check unavailable: {exc}"
            return

        active.pdm_match_count = len(candidates)
        name_key = self._normalize(name)
        code_key = self._normalize(code)
        exact = [
            product for product in candidates.values()
            if (
                name_key and self._normalize(product.name) == name_key
            ) or (
                code_key and self._normalize(product.code) == code_key
            )
        ]

        if len(exact) == 1:
            product = exact[0]
            active.pdm_match_status = "exact_match"
            active.pdm_product_id = str(product.id)
            for record in active.records.values():
                record.pdm_mapping_status = "matched"
            active.records["catalogue"].value = product.description or None
            active.records["catalogue"].fetch_status = (
                "fetched" if product.description else "not_available"
            )
        elif candidates:
            active.pdm_match_status = "candidates_found"
            for record in active.records.values():
                record.pdm_mapping_status = "candidates_found"
        else:
            active.pdm_match_status = "not_found"
            for record in active.records.values():
                record.pdm_mapping_status = "not_found"

    @staticmethod
    def _category_from_path(folder: Path) -> str:
        parts = {part.casefold() for part in folder.parts}
        if "seating" in parts:
            return "Seating"
        if "tables" in parts:
            return "Tables"
        return ""

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join((value or "").casefold().split())
