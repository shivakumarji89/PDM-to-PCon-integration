"""Product data lineage service.

Builds a traceable context when an existing repository series is opened. The
service deliberately separates:
  * fetched repository values,
  * known PDM locations for equivalent data,
  * actual PDM candidate/match results.

This gives workflows and future agents evidence instead of a flat collection of
values.
"""
from __future__ import annotations

from pathlib import Path

from models.data_lineage import (
    DataLineageRecord,
    RepositoryProductContext,
    SourceLocation,
)
from services.base_service import BaseService


class DataLineageService(BaseService):
    """Creates and retains the active product's cross-source lineage context."""

    _OCD_FILE = "pcr_data_com_ocd.mdb"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._active: RepositoryProductContext | None = None

    @property
    def active_context(self) -> RepositoryProductContext | None:
        return self._active

    def clear(self) -> None:
        self._active = None

    def open_repository_series(self, repository_path: str | Path) -> RepositoryProductContext:
        """Read initial repository identity and cross-check its PDM equivalents.

        This is intentionally metadata-only. It does not load articles,
        properties or workflow data yet; each future fetch can extend the same
        lineage context using the same record structure.
        """
        folder = Path(repository_path)
        series_name = folder.name
        category = self._category_from_path(folder)

        records = {
            "name": self._record(
                "name",
                series_name,
                SourceLocation(
                    system="repository",
                    path=str(folder),
                    notes if False else "",
                ),
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
                    relationship="Workspace root identifies Seating/Tables category",
                ),
            ),
            "catalogue": self._record(
                "catalogue",
                None,
            ),
        }

        # Record the PDM locations even before a value match is confirmed.
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

        self._read_repository_package(folder, records["code"])

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
        value,
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

    def _read_repository_package(
        self,
        folder: Path,
        code_record: DataLineageRecord,
    ) -> None:
        ocd_path = folder / self._OCD_FILE
        if not ocd_path.is_file():
            code_record.fetch_status = "not_available"
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
        code_record.fetch_status = "not_available"
        code_record.notes = "reg_ProgramCode is empty or unavailable."

    def _cross_check_pdm(self, active: RepositoryProductContext) -> None:
        """Find PDM candidates without silently inventing a product match."""
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
        normalized_name = self._normalize(name)
        normalized_code = self._normalize(code)

        exact = [
            product for product in candidates.values()
            if (
                normalized_name
                and self._normalize(product.name) == normalized_name
            )
            or (
                normalized_code
                and self._normalize(product.code) == normalized_code
            )
        ]

        if len(exact) == 1:
            product = exact[0]
            active.pdm_match_status = "exact_match"
            active.pdm_product_id = str(product.id)
            active.records["name"].pdm_mapping_status = "matched"
            active.records["code"].pdm_mapping_status = "matched"
            active.records["category"].pdm_mapping_status = "matched"
            active.records["catalogue"].pdm_mapping_status = "matched"
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
        parts = {part.lower() for part in folder.parts}
        if "seating" in parts:
            return "Seating"
        if "tables" in parts:
            return "Tables"
        return ""

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join((value or "").casefold().split())
