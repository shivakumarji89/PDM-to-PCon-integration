"""Read-only database metadata for the legacy SyteLine export workflow.

SQL is limited to metadata queries found in the legacy PDM Maintenance source.
Export execution and data transformation are deliberately outside this service.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from repositories.pdm_repository import PDMRepository


@dataclass(frozen=True)
class ExportChoice:
    id: int
    label: str
    code: str = ""
    description: str = ""
    extra_id: int | None = None


class SyteLineMetadataService:
    """Fetch live site/language/currency/catalogue/product-code choices read-only."""

    _SITES = "SELECT SiteId, Description, Site FROM Site WITH (NOLOCK)"
    _LANGUAGES = "SELECT Language_ID, Language, CultureCode FROM Language WITH (NOLOCK)"
    _CURRENCIES = "SELECT Currency_ID, Currency FROM Currency WITH (NOLOCK) ORDER BY Currency_ID"
    _CATALOGUES = """
        SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly
        FROM PDMUserCatalogues puc WITH (NOLOCK)
        INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId
        WHERE puc.UserId = ? AND Catalogue.Status = 1
        ORDER BY Catalogue.Name
    """
    _PRODUCT_CODES = """
        SELECT DISTINCT pc.ProductCodeId, pc.Product_Code, pc.Description, pc.BasePriceRef
        FROM Product_Code pc WITH (NOLOCK)
        INNER JOIN Product ON Product.ProductCodeId = pc.ProductCodeId
        INNER JOIN Item ON Product.ProductId = Item.ProductId
        INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId
        WHERE pc.SiteId IN (-1, ?) AND ci.CatalogueId IN (-1, ?)
        UNION
        SELECT DISTINCT pc.ProductCodeId, pc.Product_Code, pc.Description, pc.BasePriceRef
        FROM Product_Code pc WITH (NOLOCK)
        INNER JOIN Product ON Product.ProductCodeId = pc.ProductCodeId
        INNER JOIN Item ON Product.ProductId = Item.ProductId
        INNER JOIN CatalogueItemsUnreleased ci ON Item.ItemId = ci.ItemId
        WHERE pc.SiteId IN (-1, ?) AND ci.CatalogueId IN (-1, ?)
        ORDER BY Product_Code
    """

    def __init__(
        self,
        context: Any,
        connection_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._context = context
        self._connection_factory = connection_factory

    def _connect(self):
        if self._connection_factory is not None:
            return self._connection_factory()
        return PDMRepository(self._context).get_connection()

    def _fetch(self, query: str, parameters: tuple = ()) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(query, *parameters)
            names = [column[0] for column in cursor.description]
            return [dict(zip(names, row)) for row in cursor.fetchall()]
        finally:
            connection.close()

    def sites(self) -> list[ExportChoice]:
        rows = self._fetch(self._SITES)
        # Preserve the legacy rule: site 20 is excluded except on the two
        # Knoll SQL servers, where the legacy form limits choices to 1 and 20.
        server = str(self._context.config.pdm_server)
        if server in {"DBIA01SQLSV.knoll.dom", "DBIA08SQPDMLV.knoll.dom"}:
            rows = [row for row in rows if int(row["SiteId"]) in {1, 20}]
        else:
            rows = [row for row in rows if int(row["SiteId"]) != 20]
        return [
            ExportChoice(int(row["SiteId"]), str(row["Description"]), str(row["Site"]))
            for row in rows
        ]

    def languages(self) -> list[ExportChoice]:
        return [
            ExportChoice(int(row["Language_ID"]), str(row["Language"]), str(row.get("CultureCode") or ""))
            for row in self._fetch(self._LANGUAGES)
        ]

    def currencies(self) -> list[ExportChoice]:
        return [
            ExportChoice(int(row["Currency_ID"]), str(row["Currency"]))
            for row in self._fetch(self._CURRENCIES)
        ]

    def catalogues(self, user_id: int) -> list[ExportChoice]:
        if user_id < 1:
            raise ValueError("Enter the authenticated PDM User ID to load permitted catalogues.")
        return [
            ExportChoice(
                int(row["CatalogueId"]), str(row["Name"]),
                extra_id=int(row["ReadOnly"]) if row.get("ReadOnly") is not None else 0,
            )
            for row in self._fetch(self._CATALOGUES, (user_id,))
        ]

    def product_codes(self, site_id: int, catalogue_id: int) -> list[ExportChoice]:
        if site_id < 1 or catalogue_id < 1:
            raise ValueError("A valid site and catalogue are required to load product codes.")
        params = (site_id, catalogue_id, site_id, catalogue_id)
        return [
            ExportChoice(
                int(row["ProductCodeId"]),
                f'{row["Product_Code"]}  |  {row["Description"]}',
                str(row["Product_Code"]),
                str(row["Description"] or ""),
                int(row["BasePriceRef"]) if row.get("BasePriceRef") is not None else None,
            )
            for row in self._fetch(self._PRODUCT_CODES, params)
        ]
