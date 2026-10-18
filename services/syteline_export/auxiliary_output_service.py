"""Source-mapped auxiliary output writers from the legacy ExportThread.

These two families have self-contained, traceable SQL in the legacy source.
They do not pretend to replace the complex item/material/BOM transformation.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable

from repositories.pdm_repository import PDMRepository
from services.syteline_export.config import LEGACY_TSV_HEADERS


PRICE_FORMULA_HEADER = (
    "Site", "CustPriceCode", "ItemPriceCode", "PriceFormula", "PriceFactor", "EffectiveDate"
)
PRODUCT_CODE_HEADER = ("Site", "ProductCode", "Description", "PriceCode", "UnitCode")


class SyteLineAuxiliaryOutputService:
    """Read-only SQL and deterministic TSV output for legacy auxiliary files."""

    def __init__(self, context: Any, connection_factory: Callable[[], Any] | None = None) -> None:
        self._context = context
        self._connection_factory = connection_factory

    def _connect(self):
        if self._connection_factory is not None:
            return self._connection_factory()
        return PDMRepository(self._context).get_connection()

    def _query(self, query: str, parameters: tuple) -> list[tuple]:
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(query, *parameters)
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    def price_formula_rows(self, site_id: int, item_price_codes: Iterable[str]) -> list[tuple]:
        codes = tuple(dict.fromkeys(str(code).strip() for code in item_price_codes if str(code).strip()))
        if site_id < 1:
            raise ValueError("A valid site ID is required.")
        if not codes:
            return []
        placeholders = ", ".join("?" for _ in codes)
        query = f"""
            SELECT Site.Site, pm.CustPriceCode, pm.ItemPriceCode, pf.PriceFormula,
                   pf.FirstPrice, CONVERT(VARCHAR(11), pf.EffectiveDate, 106) AS EffDate
            FROM PriceFormula pf WITH (NOLOCK)
            INNER JOIN PriceMatrix pm ON pf.PriceFormula = pm.PriceFormula
            INNER JOIN Site ON pf.SiteId = Site.SiteId
            WHERE Site.SiteId = ? AND pm.ItemPriceCode IN ({placeholders})
            ORDER BY pm.CustPriceCode, pf.EffectiveDate DESC
        """
        return self._query(query, (site_id, *codes))

    def product_code_rows(self, site_id: int, product_codes: Iterable[str]) -> list[tuple]:
        codes = tuple(dict.fromkeys(str(code).strip() for code in product_codes if str(code).strip()))
        if site_id < 1:
            raise ValueError("A valid site ID is required.")
        if not codes:
            return []
        placeholders = ", ".join("?" for _ in codes)
        query = f"""
            SELECT Site.Site, pc.Product_Code, pc.Description, pc.PriceCode
            FROM Product_Code pc WITH (NOLOCK)
            INNER JOIN Site ON pc.SiteId = Site.SiteId
            WHERE Site.SiteId = ? AND pc.Product_Code IN ({placeholders})
            ORDER BY pc.Product_Code
        """
        return self._query(query, (site_id, *codes))

    @staticmethod
    def _write_tsv(path: str | Path, header: tuple[str, ...], rows: Iterable[tuple]) -> Path:
        target = Path(path).expanduser()
        if not target.parent.is_dir():
            raise ValueError(f"Output directory does not exist: {target.parent}")
        target = target.resolve()
        fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as stream:
                # The legacy C# writer concatenates fields with literal tabs; it
                # does not apply CSV quoting or escaping.
                stream.write("\t".join(header) + "\r\n")
                for row in rows:
                    stream.write("\t".join("" if value is None else str(value) for value in row) + "\r\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, target)
        except Exception:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
            raise
        return target

    @staticmethod
    def write_header_only_outputs(
        export_directory: str | Path,
        export_file_name: str = "PDMExport",
        format_csi: bool = False,
    ) -> dict[str, Path]:
        """Write the two header-only files emitted by legacy ExportThread.

        The legacy source writes the planning and description headers but does
        not append data rows to either file. They live under the export temp
        directory, with a _csi suffix in CSI mode.
        """
        root = Path(export_directory).expanduser()
        if not root.is_dir():
            raise ValueError(f"Export directory does not exist: {root}")
        temp = root / "temp"
        temp.mkdir(exist_ok=True)
        suffix = "_csi" if format_csi else ""
        outputs = {
            "description": temp / f"{export_file_name}_description_data{suffix}.txt",
            "planning": temp / f"{export_file_name}_planning_data{suffix}.txt",
        }
        for family, target in outputs.items():
            SyteLineAuxiliaryOutputService._write_tsv(
                target, LEGACY_TSV_HEADERS[family], ()
            )
        return outputs

    def write_price_formula(self, path: str | Path, site_id: int, item_price_codes: Iterable[str]) -> Path:
        return self._write_tsv(path, PRICE_FORMULA_HEADER, self.price_formula_rows(site_id, item_price_codes))

    def write_product_codes(self, path: str | Path, site_id: int, product_codes: Iterable[str]) -> Path:
        # The legacy source declares UnitCode in the header but writes only four
        # values per row. Preserve that source-defined shape for parity.
        return self._write_tsv(path, PRODUCT_CODE_HEADER, self.product_code_rows(site_id, product_codes))
