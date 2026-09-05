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
    candidate_products: list[dict[str, Any]] = field(default_factory=list)
    candidate_catalogues: list[dict[str, Any]] = field(default_factory=list)
    established_connection: dict[str, Any] | None = None


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

        # Always run fresh discovery. An established connection is persistent
        # evidence for maintenance, but it must never replace or narrow the live
        # catalogue list shown in Review.
        self._cross_check_pdm(active)

        established = self.context.repository_connection_service.get(folder)
        if established is not None:
            self._apply_established_connection(active, established)

        self._active = active
        return active

    def _apply_established_connection(
        self,
        active: RepositoryProductContext,
        connection: dict[str, Any],
    ) -> None:
        """Attach stored connection evidence without replacing fresh discovery.

        The central registry remembers the previously established relationship
        for maintenance and future agents. Review discovery remains independent:
        all currently matching catalogues stay visible so the user can inspect
        PDM changes or choose a different catalogue when required.
        """
        pdm = connection.get("pdm") or {}
        established_catalogue = str(pdm.get("catalogue") or "")
        active.established_connection = connection
        active.pdm_product_id = str(pdm.get("product_id") or "") or None

        # Preserve the fresh candidate_products/candidate_catalogues generated
        # by _cross_check_pdm(). Only add the stored catalogue as fallback when
        # fresh discovery did not return it.
        if established_catalogue and not any(
            item.get("catalogue") == established_catalogue
            for item in active.candidate_catalogues
        ):
            active.candidate_catalogues.append({
                "catalogue": established_catalogue,
                "lead_time": pdm.get("lead_time"),
                "product_count": 0,
                "categories": [
                    str(pdm.get("category") or "")
                ] if pdm.get("category") else [],
            })

        active.candidate_catalogues.sort(
            key=lambda item: (
                item.get("lead_time") is None,
                -(int(item.get("lead_time") or 0)),
                str(item.get("catalogue") or "").casefold(),
            )
        )

        for record in active.records.values():
            record.pdm_mapping_status = (
                "established_with_fresh_discovery"
                if active.candidate_catalogues
                else "established"
            )

        if established_catalogue:
            active.records["catalogue"].value = established_catalogue
            active.records["catalogue"].fetch_status = "fetched"

        discovery_count = len(active.candidate_catalogues)
        active.pdm_match_status = (
            "established_with_catalogues_found"
            if discovery_count
            else "established"
        )
        active.records["name"].notes = (
            "Established repository ↔ PDM connection loaded from the central registry "
            f"(Catalogue: {established_catalogue or '-'}). Fresh discovery remains "
            f"available and found {discovery_count} catalogue(s)."
        )

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

    @staticmethod
    def _catalogue_lead_time(name: str) -> int | None:
        """Extract a numeric lead time from catalogue names such as 120-day."""
        # Catalogue names are the source of lead-time evidence in the cached
        # hierarchy. Accept optional spaces around the hyphen and preserve the
        # value as an integer so sorting is numeric (120, 110, 100 ...), not
        # alphabetical (05, 10, 100 ...).
        match = re.search(
            r"(?<!\d)(\d+)\s*-\s*day\b",
            str(name or ""),
            re.IGNORECASE,
        )
        return int(match.group(1)) if match else None

    def _cross_check_pdm(self, active: RepositoryProductContext) -> None:
        """Discover matching hierarchy occurrences and preserve their catalogue links.

        Standard discovery order:
        repository series -> all matching Catalogue/Product occurrences
        -> catalogue grouping -> user selects catalogue -> user selects series.

        Discovery never auto-selects a catalogue and must preserve repeated
        ProductIds when they occur under different catalogues.
        """
        name = active.series_name.strip()
        code = str(active.records["code"].value or "").strip()
        # Keep each catalogue occurrence. A ProductId can legitimately appear
        # in several catalogues, so deduplicating by ProductId would destroy the
        # exact Catalogue → Product relationship visible in Product Explorer.
        candidates: list[Any] = []
        candidate_keys: set[tuple[str, str, str]] = set()
        discovery_level = ""

        def add_candidate(product) -> None:
            key = (
                str(product.id),
                str(getattr(product, "catalogue_id", "") or ""),
                str(product.description or ""),
            )
            if key not in candidate_keys:
                candidate_keys.add(key)
                candidates.append(product)

        try:
            # Search the complete cached hierarchy first. The old bounded live
            # search could stop inside one catalogue and therefore could not
            # apply the established catalogue-selection standard.
            hierarchy = self.context.pdm_service.get_cached_products()
            normalized_name = self._normalize(name)
            normalized_code = self._normalize(code)

            for product in hierarchy:
                product_name = self._normalize(product.name)
                product_code = self._normalize(product.code)
                product_category = self._normalize(product.category)
                name_hit = bool(
                    normalized_name
                    and (
                        product_name == normalized_name
                        or product_name.startswith(normalized_name + " ")
                    )
                )
                code_hit = bool(
                    normalized_code
                    and (
                        normalized_code == product_code
                        or normalized_code in product_code
                    )
                )
                if name_hit or code_hit:
                    add_candidate(product)

            if candidates:
                discovery_level = "direct name/code match"

            # Level 2: first-word discovery. Repository folder naming can contain
            # technical suffixes (for example Nevi_enhanced) while PDM may use
            # the base series name. This remains discovery-only evidence.
            if not candidates and name:
                first_word = re.split(r"[_\\-\\s]+", name, maxsplit=1)[0].strip()
                normalized_first_word = self._normalize(first_word)
                if normalized_first_word:
                    for product in hierarchy:
                        product_name = self._normalize(product.name)
                        if (
                            product_name == normalized_first_word
                            or product_name.startswith(normalized_first_word + " ")
                        ):
                            add_candidate(product)
                if candidates:
                    discovery_level = f"first-word match ({first_word})"

            # Live search remains a fallback for an empty/stale local hierarchy.
            if not candidates:
                if name:
                    for product in self.context.pdm_service.search_products_by_name(name, 100):
                        add_candidate(product)
                if code:
                    for product in self.context.pdm_service.search_products_by_code(code, 100):
                        add_candidate(product)
                if candidates:
                    discovery_level = "direct live search"

            if not candidates and name:
                first_word = re.split(r"[_\\-\\s]+", name, maxsplit=1)[0].strip()
                if first_word:
                    for product in self.context.pdm_service.search_products_by_name(first_word, 100):
                        add_candidate(product)
                if candidates:
                    discovery_level = f"first-word live search ({first_word})"

            # Level 3: category-based discovery. When repository naming does
            # not exist in PDM, use the workspace category as independent
            # evidence and let catalogue lead-time priority narrow the result.
            if not candidates and active.category:
                normalized_category = self._normalize(active.category)
                for product in hierarchy:
                    if self._normalize(product.category) == normalized_category:
                        add_candidate(product)
                if candidates:
                    discovery_level = f"category discovery ({active.category})"
        except Exception as exc:
            active.pdm_match_status = "unavailable"
            for record in active.records.values():
                record.pdm_mapping_status = "connection_unavailable"
            active.records["name"].notes = f"PDM cross-check unavailable: {exc}"
            return

        by_catalogue: dict[str, list] = {}
        for product in candidates:
            catalogue = (product.description or "").strip()
            by_catalogue.setdefault(catalogue, []).append(product)

        ranked_catalogues = sorted(
            by_catalogue.items(),
            key=lambda entry: (
                self._catalogue_lead_time(entry[0]) is None and not any(getattr(p, "lead_time", None) is not None for p in entry[1]),
                -(next((int(p.lead_time) for p in entry[1] if getattr(p, "lead_time", None) is not None), self._catalogue_lead_time(entry[0]) or 0)),
                entry[0].casefold(),
            ),
        )
        # Discovery must not auto-select a catalogue. Aggregate the evidence so
        # the user first chooses the PDM catalogue/lead-time context, then loads
        # the series belonging to that catalogue.
        active.candidate_catalogues = [
            {
                "catalogue": catalogue,
                "lead_time": next((int(product.lead_time) for product in products if getattr(product, "lead_time", None) is not None), self._catalogue_lead_time(catalogue)),
                "product_count": len(products),
                "categories": sorted({
                    str(product.category or "") for product in products
                    if str(product.category or "")
                }),
            }
            for catalogue, products in ranked_catalogues
        ]
        active.candidate_products = [
            {
                "id": str(product.id),
                "code": product.code or "",
                "name": product.name or "",
                "category": product.category or "",
                "catalogue": product.description or "",
                "lead_time": (int(product.lead_time) if getattr(product, "lead_time", None) is not None else self._catalogue_lead_time(product.description or "")),
            }
            for _catalogue, products in ranked_catalogues
            for product in products
        ]
        active.pdm_match_count = len(active.candidate_products)

        if active.candidate_catalogues:
            active.pdm_match_status = "catalogues_found"
            for record in active.records.values():
                record.pdm_mapping_status = "catalogues_found"
            active.records["name"].notes = (
                f"Discovery used {discovery_level or 'matching evidence'} and found "
                f"{len(active.candidate_catalogues)} catalogue(s). "
                "Select a catalogue/lead-time first; no catalogue is automatically chosen."
            )
        else:
            active.pdm_match_status = "not_found"
            for record in active.records.values():
                record.pdm_mapping_status = "not_found"

    def _category_from_path(self, folder: Path) -> str:
        """Resolve repository workspace category through the shared context."""
        return self.context.category_context_service.from_repository_path(folder).category

    @staticmethod
    def _normalize(value: str) -> str:
        """Normalize repository/PDM formatting for direct comparison.

        Repository folder names commonly use underscores while PDM display names
        use spaces. Treat separators as formatting only; do not remove words or
        otherwise guess semantic equivalence.
        """
        text = re.sub(r"[_-]+", " ", value or "")
        return " ".join(text.casefold().split())
