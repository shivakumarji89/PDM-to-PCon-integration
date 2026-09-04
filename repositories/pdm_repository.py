"""PDM data-access repository.

Owns the SQL Server connection and every PDM query. All SQL in the application
lives here so no UI or coordination code ever touches the database directly.

The queries are ported verbatim from the proven V1 implementation:
  * product listing        <- GlobalProductRegistryService.REGISTRY_QUERY
  * product attributes     <- PDMService.get_product_attributes
  * product options        <- PDMService.get_product_options

Read-only: this repository never writes to PDM.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence

from core.errors import PDMConnectionError, PDMQueryError
from repositories.base_repository import BaseRepository

if TYPE_CHECKING:
    from core.application_context import ApplicationContext


class _IncPriceRow:
    """Wraps a PDMOptionDataReportWithIncList row, supplying ``Item`` (the
    proc is called per-item and never echoes it back as a column)."""

    __slots__ = ("Item", "OptionId", "OrderCodeValue2", "IncPrice", "IsFabric", "Quantity")

    def __init__(self, item: str, row: Any) -> None:
        self.Item = item
        self.OptionId = getattr(row, "OptionId", None)
        self.OrderCodeValue2 = getattr(row, "OrderCodeValue2", None)
        self.IncPrice = getattr(row, "IncPrice", None)
        self.IsFabric = getattr(row, "IsFabric", None)
        self.Quantity = getattr(row, "Quantity", None)


class PDMRepository(BaseRepository):
    """SQL Server data access for PDM product data (read-only)."""

    # --- product listing (identity + catalogue/category context) ---------
    # Ported from V1 GlobalProductRegistryService.REGISTRY_QUERY. Combines
    # released (CatalogueItems) and unreleased (CatalogueItemsUnreleased) items
    # so one execution yields every (product, catalogue) pair.
    _PRODUCTS_UNION = """
        SELECT DISTINCT
            p.ProductId,
            p.Name        AS ProductName,
            p.Product     AS ProductCode,
            p.Status      AS ProductStatus,
            c.CatalogueId,
            c.Name        AS CatalogueName,
            c.LeadTime,
            pr.ProductCategoryId,
            cpc.Name      AS ProductCategoryName
        FROM Product p
        INNER JOIN ProductRange pr
            ON p.ProductRangeId = pr.ProductRangeId
        INNER JOIN Item i
            ON i.ProductId = p.ProductId
        INNER JOIN CatalogueItems ci
            ON ci.ItemId = i.ItemId
        INNER JOIN Catalogue c
            ON c.CatalogueId = ci.CatalogueId
        INNER JOIN Site st
            ON st.SiteId = c.PrimarySiteId
        INNER JOIN CatalogueProductCategories cpc
            ON cpc.CatalogueId = c.CatalogueId
           AND cpc.ProductCategoryId = pr.ProductCategoryId
        WHERE i.Status = 1
          AND p.Status <> 2
          AND c.Status <> 2
          AND st.Site = ?

        UNION

        SELECT DISTINCT
            p.ProductId,
            p.Name        AS ProductName,
            p.Product     AS ProductCode,
            p.Status      AS ProductStatus,
            c.CatalogueId,
            c.Name        AS CatalogueName,
            c.LeadTime,
            pr.ProductCategoryId,
            cpc.Name      AS ProductCategoryName
        FROM Product p
        INNER JOIN ProductRange pr
            ON p.ProductRangeId = pr.ProductRangeId
        INNER JOIN Item i
            ON i.ProductId = p.ProductId
        INNER JOIN CatalogueItemsUnreleased ci
            ON ci.ItemId = i.ItemId
        INNER JOIN Catalogue c
            ON c.CatalogueId = ci.CatalogueId
        INNER JOIN Site st
            ON st.SiteId = c.PrimarySiteId
        INNER JOIN CatalogueProductCategories cpc
            ON cpc.CatalogueId = c.CatalogueId
           AND cpc.ProductCategoryId = pr.ProductCategoryId
        WHERE i.Status < 2
          AND p.Status <> 2
          AND c.Status <> 2
          AND st.Site = ?
    """

    # Full (unfiltered) product list - retained for completeness. Not used by
    # the UI, which searches on demand instead of loading the whole catalogue.
    PRODUCTS_QUERY = (
        _PRODUCTS_UNION
        + "\n        ORDER BY CatalogueName, ProductCategoryName, ProductName\n    "
    )

    # --- product search (on-demand, bounded) -----------------------------
    # Two-stage bounding keeps search responsive on a 100k+ catalogue:
    #   1. The LIKE predicate runs against the Product table inside a derived
    #      table capped with TOP, so only a handful of matching products are
    #      ever joined.
    #   2. The catalogue/category joins then run for that small set only, and
    #      the outer TOP bounds the final (product, category) rows.
    # Only the fields the UI needs are projected; search text is a parameter.
    _SEARCH_BRANCH = """
        SELECT DISTINCT
            p.ProductId,
            p.Name        AS ProductName,
            p.Product     AS ProductCode,
            p.Status      AS ProductStatus,
            c.CatalogueId,
            c.Name        AS CatalogueName,
            cpc.Name      AS ProductCategoryName
        FROM (
            SELECT TOP (?)
                ProductId, Name, Product, Status, ProductRangeId
            FROM Product
            WHERE {pred} AND Status <> 2
            ORDER BY Product
        ) p
        INNER JOIN ProductRange pr
            ON p.ProductRangeId = pr.ProductRangeId
        INNER JOIN Item i
            ON i.ProductId = p.ProductId
        INNER JOIN {item_table} ci
            ON ci.ItemId = i.ItemId
        INNER JOIN Catalogue c
            ON c.CatalogueId = ci.CatalogueId
        INNER JOIN Site st
            ON st.SiteId = c.PrimarySiteId
        INNER JOIN CatalogueProductCategories cpc
            ON cpc.CatalogueId = c.CatalogueId
           AND cpc.ProductCategoryId = pr.ProductCategoryId
        WHERE {status}
          AND c.Status <> 2
          AND st.Site = ?
    """

    _PRED_CODE = "Product LIKE ?"
    _PRED_NAME = "Name LIKE ?"
    _PRED_ANY = "(Product LIKE ? OR Name LIKE ?)"

    # Article-number search: the inner TOP filters the Item table by the full
    # item/article code (with its parametric tail), then resolves each match to
    # its owning product - so a full article number finds its product.
    _SEARCH_BRANCH_ARTICLE = """
        SELECT DISTINCT
            p.ProductId,
            p.Name        AS ProductName,
            p.Product     AS ProductCode,
            p.Status      AS ProductStatus,
            c.CatalogueId,
            c.Name        AS CatalogueName,
            cpc.Name      AS ProductCategoryName
        FROM (
            SELECT TOP (?)
                i.ItemId, i.ProductId, i.Status
            FROM Item i
            WHERE i.Item LIKE ?
            ORDER BY i.Item
        ) im
        INNER JOIN Product p
            ON p.ProductId = im.ProductId AND p.Status <> 2
        INNER JOIN ProductRange pr
            ON p.ProductRangeId = pr.ProductRangeId
        INNER JOIN {item_table} ci
            ON ci.ItemId = im.ItemId
        INNER JOIN Catalogue c
            ON c.CatalogueId = ci.CatalogueId
        INNER JOIN Site st
            ON st.SiteId = c.PrimarySiteId
        INNER JOIN CatalogueProductCategories cpc
            ON cpc.CatalogueId = c.CatalogueId
           AND cpc.ProductCategoryId = pr.ProductCategoryId
        WHERE {status}
          AND c.Status <> 2
          AND st.Site = ?
    """

    # --- product attributes (properties + property values) ---------------
    # Ported from V1 PDMService.get_product_attributes, enriched with real
    # Attribute metadata (id, key, display order, type, dependent-options flag)
    # for the Properties workspace. Still a single query - no extra round trips.
    PRODUCT_ATTRIBUTES_QUERY = """
        SELECT
            a.AttributeId,
            a.Name AS Property,
            a.OrderCodeFormatKey AS PropertyKey,
            a.DisplayOrder,
            a.AttributeType,
            a.HasDependentOptions,
            av.Name AS Value,
            av.AttributeValueId,
            av.OrderCodeValue AS Code,
            av.ProductMaskValue AS MaskValue,
            av.ModelSuffix,
            av.DisplayOrdinal AS ValueDisplayOrder
        FROM ProductAttributeValues pav
        INNER JOIN AttributeValue av
            ON pav.AttributeValueId = av.AttributeValueId
        INNER JOIN Attribute a
            ON av.AttributeId = a.AttributeId
        WHERE pav.ProductId = ?
          AND av.Status = 1
        ORDER BY a.DisplayOrder, a.Name, av.DisplayOrdinal
    """

    # --- product options (options + option values) -----------------------
    # DPS parity (OptionSelector.LoadOptionValues, B1). The product's option
    # values are the UNION of:
    #   * ProductOptionValues        (product-level assignments)
    #   * ProductRangeOptionValues   (range-level assignments - inherited)
    #   * DependentAttributeValues   (attribute-driven options)
    # plus DependentOptionValues (option-driven), then gated by the catalogue
    # via CatalogueOptionValues and filtered by CatalogueProductOptionExclusions.
    # The "Non standard" fabric-type/colour placeholders (order codes CM01* =
    # Non standard fabric, CM02* = Non standard colour) are hidden from the
    # resolved values via _OPTIONS_HIDE_FILTER (DPS OptionSelector UI hiding).
    _OPTIONS_CTE = """
        WITH BaseOptionValues AS
        (
            SELECT pov.OptionValueId
            FROM ProductOptionValues pov
            INNER JOIN OptionValue base_ov
                ON pov.OptionValueId = base_ov.OptionValueId
            WHERE pov.ProductId = ?
              AND base_ov.Status = 1

            UNION

            SELECT prov.OptionValueId
            FROM ProductRangeOptionValues prov
            INNER JOIN Product p
                ON p.ProductRangeId = prov.ProductRangeId
            INNER JOIN OptionValue base_ov
                ON prov.OptionValueId = base_ov.OptionValueId
            WHERE p.ProductId = ?
              AND base_ov.Status = 1

            UNION

            SELECT dav.AdditionalOptionValueId AS OptionValueId
            FROM ProductAttributeValues pav
            INNER JOIN DependentAttributeValues dav
                ON pav.AttributeValueId = dav.AttributeValueId
            INNER JOIN OptionValue base_ov
                ON dav.AdditionalOptionValueId = base_ov.OptionValueId
            WHERE pav.ProductId = ?
              AND base_ov.Status = 1
        ),
        IncludedOptionValues AS
        (
            SELECT OptionValueId FROM BaseOptionValues

            UNION

            SELECT dov.AdditionalOptionValueId AS OptionValueId
            FROM DependentOptionValues dov
            INNER JOIN BaseOptionValues bov
                ON dov.OptionValueId = bov.OptionValueId
        )
    """

    _OPTIONS_SELECT = """
        SELECT DISTINCT
            o.OptionId,
            o.Name AS Property,
            o.OrderCodeFormatKey AS OptionKey,
            o.IsFabric,
            ov.Name AS Value,
            ov.OrderCodeValue AS Code,
            ov.SupplierCode,
            ov.OptionValueId,
            o.DisplayOrder AS OptionDisplayOrder,
            ov.DisplayOrdinal AS OptionValueDisplayOrdinal
        FROM IncludedOptionValues iov
        INNER JOIN OptionValue ov
            ON iov.OptionValueId = ov.OptionValueId
        INNER JOIN [Option] o
            ON ov.OptionId = o.OptionId
    """

    # Catalogue gate + product exclusions (applied when a catalogue is known).
    _OPTIONS_CATALOGUE_JOIN = """
        INNER JOIN CatalogueOptionValues cov
            ON ov.OptionValueId = cov.OptionValueId
           AND cov.CatalogueId = ?
    """
    _OPTIONS_EXCLUSION_FILTER = """
              AND ov.OptionValueId NOT IN (
                  SELECT OptionValueId
                  FROM CatalogueProductOptionExclusions
                  WHERE CatalogueId = ? AND ProductId = ?
              )
    """
    _OPTIONS_ORDER = """
        ORDER BY o.DisplayOrder, o.Name, ov.DisplayOrdinal
    """

    # Hide the "Non standard" fabric placeholders from the value list: their
    # order codes are CM01* (Non standard fabric) and CM02* (Non standard
    # colour). Applied to every option-value resolution (single + bulk).
    _OPTIONS_HIDE_FILTER = (
        " AND ov.OrderCodeValue NOT LIKE 'CM01%'"
        " AND ov.OrderCodeValue NOT LIKE 'CM02%'"
    )
    # --- product articles / items ----------------------------------------
    # DPS parity (TemplateForm.cs 3942: SELECT Item FROM Item WHERE ProductId).
    # An article is a configured order-code item belonging to the product.
    # Real Item columns only (no invented fields); the localized short
    # description is resolved via OtherDescription (DPS pattern, LanguageId 1).
    PRODUCT_ITEMS_QUERY = """
        SELECT
            i.ItemId,
            i.Item,
            i.Status,
            i.IsSuperItem,
            i.Notes,
            i.WeightKilos,
            i.VolumeLitres,
            i.Height,
            i.Width,
            i.Depth,
            od.ShortDescription AS Description
        FROM Item i WITH (NOLOCK)
        LEFT OUTER JOIN OtherDescription od
            ON i.DescriptionId = od.DescriptionId
           AND od.LanguageId = 1
        WHERE i.ProductId = ?
        ORDER BY i.Item
    """

    # --- product descriptive info ----------------------------------------
    # Real product metadata (no invented fields). Product Family / Revision do
    # not exist in this PDM schema, so they are intentionally not selected.
    PRODUCT_INFO_QUERY = """
        SELECT
            p.Name        AS ProductName,
            p.Product     AS ProductCode,
            p.Status,
            p.NewProduct,
            p.IsSuperProduct,
            pr.Name       AS RangeName
        FROM Product p WITH (NOLOCK)
        INNER JOIN ProductRange pr
            ON p.ProductRangeId = pr.ProductRangeId
        WHERE p.ProductId = ?
    """

    def __init__(self, context: "ApplicationContext") -> None:
        super().__init__(context)
        self._pyodbc = None

    # -- connection --------------------------------------------------------
    def _driver(self):
        """Import pyodbc lazily so the app can start without the driver."""
        if self._pyodbc is None:
            try:
                import pyodbc
            except ImportError as error:  # pragma: no cover - env dependent
                raise PDMConnectionError(
                    "The 'pyodbc' package is required for PDM access but is not installed."
                ) from error
            self._pyodbc = pyodbc
        return self._pyodbc

    def get_connection(self):
        """Open a new connection to the PDM database."""
        pyodbc = self._driver()
        connection_string = self.context.config.pdm_connection_string()
        try:
            return pyodbc.connect(connection_string)
        except pyodbc.Error as error:
            raise PDMConnectionError(
                f"Could not connect to PDM database "
                f"'{self.context.config.pdm_database}' on "
                f"'{self.context.config.pdm_server}': {error}"
            ) from error

    def test_connection(self) -> str:
        """Verify connectivity and return the connected database name."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DB_NAME()")
            row = cursor.fetchone()
            return row[0] if row else ""
        except self._driver().Error as error:
            raise PDMQueryError(f"PDM connection test failed: {error}") from error
        finally:
            conn.close()

    # -- queries -----------------------------------------------------------
    def fetch_products(self) -> list[Any]:
        """Return every (product, catalogue) identity row available in PDM."""
        region = self.context.config.catalogue_region
        return self._execute(self.PRODUCTS_QUERY, (region, region))

    def search_products(self, text: str, limit: int = 50) -> list[Any]:
        """Return up to ``limit`` products matching code OR name."""
        pattern = self._like_pattern(text)
        region = self.context.config.catalogue_region
        query = self._search_query(self._PRED_ANY)
        # Order follows the ? positions: outer TOP, then per branch
        # (inner TOP, pred, pred, region).
        return self._execute(
            query,
            (limit, limit, pattern, pattern, region,
             limit, pattern, pattern, region),
        )

    def search_products_by_code(self, text: str, limit: int = 50) -> list[Any]:
        """Return up to ``limit`` products whose code matches ``text``."""
        pattern = self._like_pattern(text)
        region = self.context.config.catalogue_region
        query = self._search_query(self._PRED_CODE)
        return self._execute(
            query, (limit, limit, pattern, region, limit, pattern, region)
        )

    def search_products_by_name(self, text: str, limit: int = 50) -> list[Any]:
        """Return up to ``limit`` products whose name matches ``text``."""
        pattern = self._like_pattern(text)
        region = self.context.config.catalogue_region
        query = self._search_query(self._PRED_NAME)
        return self._execute(
            query, (limit, limit, pattern, region, limit, pattern, region)
        )

    def search_products_by_article(self, text: str, limit: int = 50) -> list[Any]:
        """Return up to ``limit`` products that own an ITEM whose full article
        code matches ``text`` - lets a full article number resolve its product."""
        pattern = self._like_pattern(text)
        region = self.context.config.catalogue_region
        query = self._article_search_query()
        return self._execute(
            query, (limit, limit, pattern, region, limit, pattern, region)
        )

    def fetch_product_attributes(self, product_id: Any, connection: Any = None) -> list[Any]:
        """Return property/value rows for a single product."""
        return self._execute(
            self.PRODUCT_ATTRIBUTES_QUERY, (product_id,), connection=connection
        )

    def fetch_product_options(
        self, product_id: Any, catalogue_id: Any = None, connection: Any = None
    ) -> list[Any]:
        """Return option/value rows for a product (DPS parity).

        When ``catalogue_id`` is provided the results are catalogue-gated and
        product exclusions are applied (matching the DPS OptionSelector). When
        it is omitted the ungated resolution is returned.
        """
        if catalogue_id is None:
            query = (
                self._OPTIONS_CTE
                + self._OPTIONS_SELECT
                + "\n        WHERE ov.Status = 1"
                + self._OPTIONS_HIDE_FILTER
                + "\n"
                + self._OPTIONS_ORDER
            )
            params: tuple[Any, ...] = (product_id, product_id, product_id)
        else:
            query = (
                self._OPTIONS_CTE
                + self._OPTIONS_SELECT
                + self._OPTIONS_CATALOGUE_JOIN
                + "\n        WHERE ov.Status = 1"
                + self._OPTIONS_HIDE_FILTER
                + "\n"
                + self._OPTIONS_EXCLUSION_FILTER
                + self._OPTIONS_ORDER
            )
            params = (
                product_id, product_id, product_id,
                catalogue_id, catalogue_id, product_id,
            )
        return self._execute(query, params, connection=connection)

    def fetch_product_items(self, product_id: Any, connection: Any = None) -> list[Any]:
        """Return the article/item rows belonging to a product."""
        return self._execute(
            self.PRODUCT_ITEMS_QUERY, (product_id,), connection=connection
        )

    def fetch_product_info(self, product_id: Any, connection: Any = None) -> list[Any]:
        """Return descriptive metadata rows for a product (0 or 1 row)."""
        return self._execute(
            self.PRODUCT_INFO_QUERY, (product_id,), connection=connection
        )

    # -- bulk queries (Loading Engine) ------------------------------------
    # One query per data type for a whole set of products, using
    # ``WHERE ProductId IN (...)``. Each row carries its ``ProductId`` so the
    # caller can index results per product. Large id sets are chunked to stay
    # under the SQL Server parameter limit.
    _IN_CHUNK = 500

    @staticmethod
    def _placeholders(count: int) -> str:
        return ", ".join("?" for _ in range(count))

    @staticmethod
    def _chunked(ids: Sequence[Any], size: int):
        for start in range(0, len(ids), size):
            yield ids[start:start + size]

    def fetch_products_info(
        self, product_ids: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Bulk product info for many products (one query per chunk)."""
        ids = [pid for pid in product_ids if pid is not None]
        rows: list[Any] = []
        for chunk in self._chunked(ids, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT p.ProductId, p.Name AS ProductName, p.Product AS ProductCode, "
                "p.Status, p.NewProduct, p.IsSuperProduct, pr.Name AS RangeName "
                "FROM Product p WITH (NOLOCK) "
                "INNER JOIN ProductRange pr ON p.ProductRangeId = pr.ProductRangeId "
                f"WHERE p.ProductId IN ({ph})"
            )
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def fetch_products_attributes(
        self, product_ids: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Bulk property/value rows for many products (ordered by ProductId)."""
        ids = [pid for pid in product_ids if pid is not None]
        rows: list[Any] = []
        for chunk in self._chunked(ids, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT pav.ProductId, a.AttributeId, a.Name AS Property, "
                "a.OrderCodeFormatKey AS PropertyKey, a.DisplayOrder, a.AttributeType, "
                "a.HasDependentOptions, av.Name AS Value, av.AttributeValueId, "
                "av.OrderCodeValue AS Code, av.ProductMaskValue AS MaskValue, "
                "av.ModelSuffix, pc.Name AS AttrCategory, "
                "av.DisplayOrdinal AS ValueDisplayOrder "
                "FROM ProductAttributeValues pav "
                "INNER JOIN AttributeValue av ON pav.AttributeValueId = av.AttributeValueId "
                "INNER JOIN Attribute a ON av.AttributeId = a.AttributeId "
                "LEFT JOIN ProductCategory pc ON pc.ProductCategoryId = a.ProductCategoryId "
                f"WHERE pav.ProductId IN ({ph}) AND av.Status = 1 "
                "ORDER BY pav.ProductId, a.DisplayOrder, a.Name, av.DisplayOrdinal"
            )
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    # --- PIP reconstruction (feature vocabulary straight from PDM) --------
    def fetch_pip_header(self, product_id: Any, connection: Any = None) -> list[Any]:
        """Product code + range + the tail code-assembly template
        (``ProductRange.OrderCodeFormatString``) for one product."""
        query = (
            "SELECT TOP 1 p.Product, pr.Name AS RangeName, pr.OrderCodeFormatString "
            "FROM Product p WITH (NOLOCK) "
            "INNER JOIN ProductRange pr ON pr.ProductRangeId = p.ProductRangeId "
            "WHERE p.ProductId = ?"
        )
        return self._execute(query, (product_id,), connection=connection)

    def fetch_pip_attributes(self, product_id: Any, connection: Any = None) -> list[Any]:
        """Every attribute a product carries with the signals that classify it
        functional (head, no format key) vs physical (tail, has ``{TOKEN}``),
        plus each value's order code. Ordered by attribute then value."""
        query = (
            "SELECT a.AttributeId, a.Name AS AttrName, a.AttributeType, "
            "a.OrderCodeFormatKey, a.DisplayOrder, a.HasDependentOptions, "
            "av.AttributeValueId, av.Name AS ValueName, av.OrderCodeValue, av.DisplayOrdinal "
            "FROM ProductAttributeValues pav WITH (NOLOCK) "
            "INNER JOIN AttributeValue av ON av.AttributeValueId = pav.AttributeValueId "
            "INNER JOIN Attribute a ON a.AttributeId = av.AttributeId "
            "WHERE pav.ProductId = ? AND av.Status = 1 "
            "ORDER BY a.DisplayOrder, av.DisplayOrdinal"
        )
        return self._execute(query, (product_id,), connection=connection)

    def fetch_pip_options(self, product_id: Any, connection: Any = None) -> list[Any]:
        """Every option a product carries with its format key and value codes
        (options are tail/physical features)."""
        query = (
            "SELECT o.OptionId, o.Name AS OptName, o.OrderCodeFormatKey, o.DisplayOrder, "
            "ov.OptionValueId, ov.Name AS ValueName, ov.OrderCodeValue, ov.DisplayOrdinal "
            "FROM ProductOptionValues pov WITH (NOLOCK) "
            "INNER JOIN OptionValue ov ON ov.OptionValueId = pov.OptionValueId "
            "INNER JOIN [Option] o ON o.OptionId = ov.OptionId "
            "WHERE pov.ProductId = ? AND ov.Status = 1 "
            "ORDER BY o.DisplayOrder, ov.DisplayOrdinal"
        )
        return self._execute(query, (product_id,), connection=connection)

    def fetch_pip_notes(self, product_id: Any, connection: Any = None) -> list[Any]:
        """Product application text / notes (``CatalogueApplicationText``)."""
        query = (
            "SELECT DISTINCT ApplicationText FROM CatalogueApplicationText WITH (NOLOCK) "
            "WHERE ProductId = ? AND LanguageId = 1 AND ApplicationText IS NOT NULL"
        )
        return self._execute(query, (product_id,), connection=connection)

    def fetch_pip_products(
        self, like: str, connection: Any = None, limit: int = 25
    ) -> list[Any]:
        """Active (ProductId, Product, Name) whose code matches ``like`` - a
        convenience for picking a product to reconstruct."""
        query = (
            f"SELECT TOP {int(limit)} p.ProductId, p.Product, p.Name "
            "FROM Product p WITH (NOLOCK) "
            "WHERE p.Product LIKE ? AND p.Status = 1 ORDER BY p.Product"
        )
        return self._execute(query, (like,), connection=connection)

    def fetch_products_items(
        self, product_ids: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Bulk item/article rows for many products (ordered by ProductId)."""
        ids = [pid for pid in product_ids if pid is not None]
        rows: list[Any] = []
        for chunk in self._chunked(ids, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT i.ProductId, i.ItemId, i.Item, i.Status, i.IsSuperItem, i.Notes, "
                "i.WeightKilos, i.VolumeLitres, i.Height, i.Width, i.Depth, "
                "od.ShortDescription AS Description "
                "FROM Item i WITH (NOLOCK) "
                "LEFT OUTER JOIN OtherDescription od "
                "ON i.DescriptionId = od.DescriptionId AND od.LanguageId = 1 "
                f"WHERE i.ProductId IN ({ph}) "
                "ORDER BY i.ProductId, i.Item"
            )
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def fetch_item_attribute_values(
        self, item_ids: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Bulk per-article attribute values (PDM ``BaseAttributeValues``).

        Returns which attribute values each item/article actually carries - the
        real article<->property-value link - ordered by item then attribute
        display order. Chunked to stay under the SQL parameter limit.
        """
        ids = [iid for iid in item_ids if iid is not None]
        rows: list[Any] = []
        for chunk in self._chunked(ids, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT bav.ItemId, av.AttributeValueId, av.OrderCodeValue AS Code, "
                "av.ModelSuffix, a.DisplayOrder, av.DisplayOrdinal, "
                "a.Name AS AttrName, a.HasDependentOptions "
                "FROM BaseAttributeValues bav "
                "INNER JOIN AttributeValue av ON bav.AttributeValueId = av.AttributeValueId "
                "INNER JOIN Attribute a ON av.AttributeId = a.AttributeId "
                f"WHERE bav.ItemId IN ({ph}) AND av.Status = 1 "
                "ORDER BY bav.ItemId, a.DisplayOrder, av.DisplayOrdinal"
            )
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def fetch_attribute_value_exclusions(
        self, product_id: Any, connection: Any = None
    ) -> list[Any]:
        """AttributeValueExclusions among a product's attribute values.

        DPS parity: a pair (AttributeValueId, ExcludedAttributeValueId) that
        cannot co-exist. Scoped so BOTH values belong to this product.
        """
        query = (
            "SELECT ave.AttributeValueId, ave.ExcludedAttributeValueId "
            "FROM AttributeValueExclusions ave "
            "INNER JOIN ProductAttributeValues pav1 "
            "  ON pav1.AttributeValueId = ave.AttributeValueId AND pav1.ProductId = ? "
            "INNER JOIN ProductAttributeValues pav2 "
            "  ON pav2.AttributeValueId = ave.ExcludedAttributeValueId AND pav2.ProductId = ?"
        )
        return self._execute(query, (product_id, product_id), connection=connection)

    def fetch_attribute_option_dependencies(
        self, product_id: Any, connection: Any = None
    ) -> list[Any]:
        """DependentAttributeValues for a product: attribute value -> the option
        value it additionally enables (DPS dependency). Source scoped to product."""
        query = (
            "SELECT dav.AttributeValueId, dav.AdditionalOptionValueId "
            "FROM DependentAttributeValues dav "
            "INNER JOIN ProductAttributeValues pav "
            "  ON pav.AttributeValueId = dav.AttributeValueId AND pav.ProductId = ?"
        )
        return self._execute(query, (product_id,), connection=connection)

    def fetch_option_option_dependencies(
        self, product_id: Any, connection: Any = None
    ) -> list[Any]:
        """DependentOptionValues for a product: option value -> the option value
        it additionally enables (DPS dependency). Source scoped to product."""
        query = (
            "SELECT dov.OptionValueId, dov.AdditionalOptionValueId "
            "FROM DependentOptionValues dov "
            "INNER JOIN ProductOptionValues pov "
            "  ON pov.OptionValueId = dov.OptionValueId AND pov.ProductId = ?"
        )
        return self._execute(query, (product_id,), connection=connection)

    def fetch_products_option_dependencies(
        self, product_ids: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Bulk DependentOptionValues for a family: parent option value -> the
        option value it additionally enables, scoped to the given products.

        Drives the fabric/finish value combination tables. Chunked; DISTINCT so
        edges shared across the family collapse.
        """
        ids = [pid for pid in product_ids if pid is not None]
        rows: list[Any] = []
        for chunk in self._chunked(ids, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT DISTINCT dov.OptionValueId, dov.AdditionalOptionValueId "
                "FROM DependentOptionValues dov "
                "INNER JOIN ProductOptionValues pov "
                "  ON pov.OptionValueId = dov.OptionValueId "
                f"WHERE pov.ProductId IN ({ph})"
            )
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def fetch_item_head_attribute_names(
        self, item_codes: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Bulk head-attribute NAMES per item code (PDM ``BaseAttributeValues``).

        For each item CODE returns the head attributes it actually carries (a
        coded or dependent ``BaseAttributeValues`` entry). Used to find the head
        properties that control a super-product COMPONENT - each component is
        conditioned only by its own head properties, not the parent's full set.
        Matched by ``Item.Item`` (component sub-item codes), chunked.
        """
        vals = [str(c) for c in item_codes if c]
        rows: list[Any] = []
        for chunk in self._chunked(vals, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT i.Item, a.Name AS AttrName "
                "FROM BaseAttributeValues bav "
                "INNER JOIN AttributeValue av "
                "ON bav.AttributeValueId = av.AttributeValueId "
                "INNER JOIN Attribute a ON av.AttributeId = a.AttributeId "
                "INNER JOIN Item i ON bav.ItemId = i.ItemId "
                f"WHERE i.Item IN ({ph}) AND av.Status = 1 "
                "AND (av.OrderCodeValue IS NOT NULL "
                "OR ABS(a.HasDependentOptions) > 0)"
            )
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def fetch_item_components(
        self, item_ids: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Bulk super-product BOM (PDM ``ItemComponents``) for parent items.

        Returns each parent article/item's sub-items with quantity and
        component sequence - the backbone of super-product VARCOND generation.
        Chunked to stay under the SQL parameter limit.
        """
        ids = [iid for iid in item_ids if iid is not None]
        rows: list[Any] = []
        for chunk in self._chunked(ids, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT itco.ItemId AS ParentItemId, sub.Item AS SubItem, "
                "itco.Quantity, itco.ComponentSequence "
                "FROM ItemComponents itco "
                "INNER JOIN Item sub ON itco.SubItemId = sub.ItemId "
                f"WHERE itco.ItemId IN ({ph}) "
                "ORDER BY itco.ItemId, CONVERT(INT, itco.ComponentSequence)"
            )
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def count_product_option_values(
        self, product_id: Any, connection: Any = None
    ) -> int:
        """Number of direct ProductOptionValues assigned to a product.

        Distinguishes "genuinely no options" from "options exist but the
        catalogue gate removed them" (a stale-hierarchy signal).
        """
        rows = self._execute(
            "SELECT COUNT(*) AS n FROM ProductOptionValues WHERE ProductId = ?",
            (product_id,),
            connection=connection,
        )
        return int(rows[0].n) if rows else 0

    def fetch_article_prefix_lengths(
        self, item_ids: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Bulk raw inputs for PDM ``getArticlePrefixLength`` (per item).

        Returns one row per item with its ``Item``, ``Notes`` and
        ``ProductCategoryId``; the pCon prefix length is derived from ``Notes``
        (a short integer token) with a per-category master fallback resolved by
        :meth:`fetch_category_master_notes`. Chunked to stay under the SQL
        parameter limit.
        """
        ids = [iid for iid in item_ids if iid is not None]
        rows: list[Any] = []
        for chunk in self._chunked(ids, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT i.ItemId, i.Item, i.Notes, pr.ProductCategoryId "
                "FROM Item i "
                "INNER JOIN Product p ON i.ProductId = p.ProductId "
                "INNER JOIN ProductRange pr ON p.ProductRangeId = pr.ProductRangeId "
                f"WHERE i.ItemId IN ({ph})"
            )
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def fetch_item_notes(self, codes: Sequence[Any], connection: Any = None) -> list[Any]:
        """Item ``Notes`` per item CODE - the CAD-maintenance field carrying the
        pCon article prefix length. (:meth:`fetch_article_prefix_lengths` keys by
        ``ItemId``; this keys by the item code we hold in a published package.)
        Returns ``(Item, Notes)`` rows, chunked."""
        vals = [str(c) for c in codes if c]
        rows: list[Any] = []
        for chunk in self._chunked(vals, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = f"SELECT i.Item, i.Notes FROM Item i WHERE i.Item IN ({ph})"
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def fetch_item_option_increments(
        self, prefixes: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Bulk option increment prices (PDM ``ItemOptionValues.IncrementalPrice``).

        For each item-name ``prefix`` (matched ``LIKE '<prefix>%'``) returns the
        option values that carry an incremental price, joined to their option and
        option value - the direct source PDM's ``getOptionIncrementSuffixes``
        falls back to. Values whose order code is a ``#`` placeholder or that
        have no increment are excluded, exactly as PDM does.
        """
        vals = [str(p) for p in prefixes if p]
        rows: list[Any] = []
        for chunk in self._chunked(vals, 50):
            likes = " OR ".join("i.Item LIKE ?" for _ in chunk)
            params = tuple(p + "%" for p in chunk)
            query = (
                "SELECT i.Item, itov.IncrementalPrice, opt.OptionId, "
                "opt.Name AS OptionName, optval.Name AS ValueName, "
                "optval.OrderCodeValue AS Code "
                "FROM Item i "
                "INNER JOIN ItemOptionValues itov ON i.ItemId = itov.ItemId "
                "INNER JOIN OptionValue optval "
                "ON itov.OptionValueId = optval.OptionValueId "
                "INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId "
                f"WHERE ({likes}) AND optval.OrderCodeValue NOT LIKE '%#' "
                "AND itov.IncrementalPrice IS NOT NULL "
                "ORDER BY i.Item, opt.OptionId, optval.OrderCodeValue"
            )
            rows.extend(self._execute(query, params, connection=connection))
        return rows

    def fetch_item_base_prices(
        self,
        items: Sequence[Any],
        currency: str,
        mydate: str,
        connection: Any = None,
        site_id: int = 1,
    ) -> list[Any]:
        """Bulk base list prices (PDM ``fnGetListPriceByItem``), set-based.

        Replaces PDM's per-item ``SELECT dbo.fnGetListPriceByItem(item, currency,
        date, site, NULL)`` with one call per chunk. The value is computed by SQL
        Server via the identical function, so results are byte-identical to PDM's
        - only the number of round trips changes. Returns ``(Item, price)`` rows;
        a NULL/blank price means PDM could not resolve a list price for that item.
        """
        vals = [str(i) for i in items if i]
        rows: list[Any] = []
        for chunk in self._chunked(vals, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT i.Item, "
                "dbo.fnGetListPriceByItem(i.Item, ?, ?, ?, NULL) AS price "
                "FROM Item i "
                f"WHERE i.Item IN ({ph})"
            )
            params = (currency, mydate, site_id) + tuple(chunk)
            rows.extend(self._execute(query, params, connection=connection))
        return rows

    def fetch_validation_catalogue_ids(
        self,
        currency: str,
        site_id: int | None,
        *,
        obx: bool = False,
        connection: Any = None,
    ) -> list[int]:
        """Return the catalogue scope used by the legacy SIF/OBX validator."""
        code = (currency or "").strip().upper()
        if obx:
            site_scope = [1, 4]
        elif code in {"GBP", "EUR"}:
            site_scope = [1, 4]
        elif code in {"JPY", "CNY", "HKD"} or (code == "USD" and site_id == 3):
            site_scope = [2, 3, 7, 9]
        elif code == "USD" and site_id in {10, 16}:
            site_scope = [site_id]
        elif code == "BRL" and site_id == 11:
            site_scope = [11]
        elif code == "INR" and site_id == 8:
            site_scope = [8]
        elif site_id is not None:
            site_scope = [site_id]
        else:
            return []

        ph = self._placeholders(len(site_scope))
        rows = self._execute(
            "SELECT CatalogueId FROM Catalogue "
            f"WHERE PrimarySiteId IN ({ph}) ORDER BY LeadTime, Name",
            tuple(site_scope),
            connection=connection,
        )
        return [int(r.CatalogueId) for r in rows]

    def fetch_validation_catalogue_ids_ordered(
        self,
        catalogue_ids: Sequence[int],
        site_id: int,
        connection: Any = None,
    ) -> list[int]:
        """Apply the exact legacy GetPrice catalogue ordering.

        GetPrice reorders the supplied catalogue ids by LeadTime and gives the
        current pricing site priority when lead times are equal.
        """
        ids = [int(value) for value in catalogue_ids]
        if not ids:
            return []
        ph = self._placeholders(len(ids))
        query = (
            "SELECT CatalogueId, LeadTime "
            "FROM Catalogue "
            f"WHERE CatalogueId IN ({ph}) "
            "ORDER BY LeadTime, "
            "CASE WHEN PrimarySiteId = ? THEN PrimarySiteId ELSE PrimarySiteId * 10 END, "
            "Name"
        )
        rows = self._execute(
            query,
            tuple(ids) + (int(site_id),),
            connection=connection,
        )
        return [int(row.CatalogueId) for row in rows]

    def fetch_item_price_context(
        self,
        items: Sequence[Any],
        currency: str,
        site_id: int,
        connection: Any = None,
    ) -> list[Any]:
        """Legacy GetPrice item/price-matrix validation context."""
        vals = [str(value) for value in items if value]
        if not vals:
            return []
        rows: list[Any] = []
        for chunk in self._chunked(vals, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT i.Item, i.ItemId, i.Status, i.ProductId, "
                "p.IsSuperProduct, pc.ProductCodeId, pc.PriceCode, "
                "pm.Rounding, pc.BasePriceRef "
                "FROM Item i "
                "INNER JOIN Product p ON i.ProductId = p.ProductId "
                "LEFT JOIN Product_Code pc ON "
                "pc.ProductCodeId = CASE "
                "WHEN i.ProductCodeIdOverride IS NOT NULL THEN i.ProductCodeIdOverride "
                "ELSE p.ProductCodeId END "
                "AND pc.SiteId = ? "
                "LEFT JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode "
                "LEFT JOIN Currency c ON pm.CustPriceCode = c.PriceCode "
                "AND UPPER(c.Currency) = UPPER(?) "
                f"WHERE i.Item IN ({ph})"
            )
            rows.extend(
                self._execute(
                    query,
                    (site_id, currency) + tuple(chunk),
                    connection=connection,
                )
            )
        return rows

    def fetch_items_valid_catalogues(
        self,
        items: Sequence[Any],
        catalogue_ids: Sequence[int],
        connection: Any = None,
    ) -> dict[str, list[int]]:
        """Resolve legacy GetShortestLeadTime catalogue eligibility.

        A candidate catalogue must contain the item, have the product category
        active, and contain the product range. Results are ordered by the
        caller's already legacy-ordered catalogue list.
        """
        vals = [str(value) for value in items if value]
        cats = [int(value) for value in catalogue_ids]
        if not vals or not cats:
            return {}
        item_ph = self._placeholders(len(vals))
        cat_ph = self._placeholders(len(cats))
        query = (
            "SELECT DISTINCT i.Item, c.CatalogueId "
            "FROM Item i "
            "INNER JOIN Product p ON i.ProductId = p.ProductId "
            "INNER JOIN ProductRange pr ON p.ProductRangeId = pr.ProductRangeId "
            "INNER JOIN CatalogueItems ci ON ci.ItemId = i.ItemId "
            "INNER JOIN Catalogue c ON c.CatalogueId = ci.CatalogueId "
            "INNER JOIN CatalogueProductCategories cpc ON "
            "cpc.CatalogueId = c.CatalogueId "
            "AND cpc.ProductCategoryId = pr.ProductCategoryId "
            "AND cpc.Status = 1 "
            "INNER JOIN CatalogueProductRanges cpr ON "
            "cpr.CatalogueId = c.CatalogueId "
            "AND cpr.ProductRangeId = pr.ProductRangeId "
            f"WHERE i.Item IN ({item_ph}) AND c.CatalogueId IN ({cat_ph})"
        )
        rows = self._execute(
            query,
            tuple(vals) + tuple(cats),
            connection=connection,
        )
        allowed: dict[str, set[int]] = {}
        for row in rows:
            allowed.setdefault(str(row.Item), set()).add(int(row.CatalogueId))
        return {
            item: [catalogue for catalogue in cats if catalogue in ids]
            for item, ids in allowed.items()
        }

    def fetch_item_get_price_ext_base_prices(
        self,
        items: Sequence[Any],
        currency: str,
        mydate: str,
        connection: Any = None,
        site_id: int = 1,
    ) -> list[Any]:
        """Bulk base prices using the same query shape as legacy GetPriceExt."""
        vals = [str(i) for i in items if i]
        rows: list[Any] = []
        for chunk in self._chunked(vals, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT i.Item, "
                "dbo.fnGetListPrice("
                "c.Currency, "
                "CASE WHEN pc.BasePriceRef = 2 THEN i.BasePrice2 "
                "WHEN pc.BasePriceRef = 3 THEN i.BasePrice3 "
                "ELSE i.BasePrice END, "
                "pc.PriceCode, ?, 'DMY', pm.Rounding, ?, NULL"
                ") AS price "
                "FROM Item i "
                "INNER JOIN Product p ON i.ProductId = p.ProductId "
                "INNER JOIN ProductRange pr ON p.ProductRangeId = pr.ProductRangeId "
                "INNER JOIN Product_Code pc ON "
                "pc.ProductCodeId = CASE "
                "WHEN i.ProductCodeIdOverride IS NOT NULL THEN i.ProductCodeIdOverride "
                "ELSE p.ProductCodeId END "
                "AND pc.SiteId = ? "
                "INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode "
                "INNER JOIN Currency c ON pm.CustPriceCode = c.PriceCode "
                "AND UPPER(c.Currency) = UPPER(?) "
                f"WHERE i.Item IN ({ph})"
            )
            params = (mydate, site_id, site_id, currency) + tuple(chunk)
            rows.extend(self._execute(query, params, connection=connection))
        return rows

    def fetch_item_base_prices_all_sites(
        self,
        items: Sequence[Any],
        currency: str,
        mydate: str,
        site_ids: Sequence[int],
        connection: Any = None,
    ) -> list[Any]:
        """Base list price of each item at EVERY given site in one round trip.

        Same ``fnGetListPriceByItem`` as :meth:`fetch_item_base_prices` (identical
        values), but cross-joined against the site list so site calibration needs
        a single query instead of one per site. Returns ``(SiteId, Item, price)``.
        """
        vals = [str(i) for i in items if i]
        sites = [int(s) for s in site_ids]
        if not vals or not sites:
            return []
        item_ph = self._placeholders(len(vals))
        site_ph = self._placeholders(len(sites))
        query = (
            "SELECT s.SiteId, i.Item, "
            "dbo.fnGetListPriceByItem(i.Item, ?, ?, s.SiteId, NULL) AS price "
            "FROM Item i CROSS JOIN Site s "
            f"WHERE i.Item IN ({item_ph}) AND s.SiteId IN ({site_ph})"
        )
        params = (currency, mydate) + tuple(vals) + tuple(sites)
        return self._execute(query, params, connection=connection)

    def fetch_item_option_increment_prices(
        self,
        items: Sequence[Any],
        currency: str,
        mydate: str,
        site_id: int,
        connection: Any = None,
    ) -> list[Any]:
        """Return option pricing rows directly from PDM's
        PDMOptionDataReportWithIncList stored procedure.
    
        This intentionally does not recreate PDM pricing logic in Python.
        """
    
        rows: list[Any] = []
    
        vals = [str(i) for i in items if i]
    
        # The proc's data result set has no "Item" column (it is called per-item
        # and never echoes the item back), so callers' r.Item is supplied here.
        required_columns = {"ordercodevalue2", "incprice"}
        owns_connection = connection is None
        conn = self.get_connection() if owns_connection else connection
        try:
            for item in vals:
                query = """
                    EXEC dbo.PDMOptionDataReportWithIncList
                        @item = ?,
                        @siteId = ?,
                        @currency = ?,
                        @effectivedate = ?,
                        @custPriceCodeOverride = NULL,
                        @excludeFabricColours = 1
                """

                cursor = conn.cursor()
                cursor.execute(query, (item, site_id, currency, mydate))

                # The proc emits non-query result sets (rowcounts etc.) before
                # the actual price rows; skip those and stop at the first match.
                while True:
                    if cursor.description is not None:
                        columns = {c[0].lower() for c in cursor.description}
                        if required_columns.issubset(columns):
                            data = cursor.fetchall()
                            rows.extend(_IncPriceRow(item, r) for r in data)
                            break
                    if not cursor.nextset():
                        break
        finally:
            if owns_connection:
                conn.close()

        return rows

    def fetch_category_master_notes(
        self, category_ids: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Bulk master-item ``Notes`` per category (PDM prefix-length fallback).
        ``CADImage2D = 'master'`` items for each category, used to derive a
        default article prefix length when an item defines none of its own.
        """
        ids = [cid for cid in category_ids if cid is not None]
        rows: list[Any] = []
        for chunk in self._chunked(ids, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT pr.ProductCategoryId, i.Notes "
                "FROM Item i "
                "INNER JOIN Product p ON i.ProductId = p.ProductId "
                "INNER JOIN ProductRange pr ON p.ProductRangeId = pr.ProductRangeId "
                f"WHERE pr.ProductCategoryId IN ({ph}) AND i.CADImage2D = 'master'"
            )
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def fetch_products_options(
        self,
        product_ids: Sequence[Any],
        catalogue_by_product: dict[Any, Any] | None = None,
        connection: Any = None,
    ) -> list[Any]:
        """Bulk option/value rows for many products, carrying ``ProductId``.

        When ``catalogue_by_product`` maps each product id to its catalogue id,
        results are catalogue-gated and product exclusions are applied per
        product (identical to the single-product gated resolution), using a
        ``(ProductId, CatalogueId)`` VALUES join. When it is omitted the ungated
        resolution is returned.
        """
        ids = [pid for pid in product_ids if pid is not None]
        rows: list[Any] = []
        base_cte = (
            "WITH BaseOptionValues AS ("
            " SELECT pov.ProductId, pov.OptionValueId FROM ProductOptionValues pov"
            " INNER JOIN OptionValue base_ov ON pov.OptionValueId = base_ov.OptionValueId"
            " WHERE pov.ProductId IN ({ph}) AND base_ov.Status = 1"
            " UNION"
            " SELECT p.ProductId, prov.OptionValueId FROM ProductRangeOptionValues prov"
            " INNER JOIN Product p ON p.ProductRangeId = prov.ProductRangeId"
            " INNER JOIN OptionValue base_ov ON prov.OptionValueId = base_ov.OptionValueId"
            " WHERE p.ProductId IN ({ph}) AND base_ov.Status = 1"
            " UNION"
            " SELECT pav.ProductId, dav.AdditionalOptionValueId AS OptionValueId"
            " FROM ProductAttributeValues pav"
            " INNER JOIN DependentAttributeValues dav"
            " ON pav.AttributeValueId = dav.AttributeValueId"
            " INNER JOIN OptionValue base_ov"
            " ON dav.AdditionalOptionValueId = base_ov.OptionValueId"
            " WHERE pav.ProductId IN ({ph}) AND base_ov.Status = 1"
            "),"
            " IncludedOptionValues AS ("
            " SELECT ProductId, OptionValueId FROM BaseOptionValues"
            " UNION"
            " SELECT bov.ProductId, dov.AdditionalOptionValueId AS OptionValueId"
            " FROM DependentOptionValues dov"
            " INNER JOIN BaseOptionValues bov ON dov.OptionValueId = bov.OptionValueId"
            ")"
        )
        select_cols = (
            " o.OptionId, o.Name AS Property, o.OrderCodeFormatKey AS OptionKey,"
            " o.IsFabric, ov.Name AS Value, ov.OrderCodeValue AS Code, ov.SupplierCode,"
            " ov.OptionValueId, o.DisplayOrder AS OptionDisplayOrder,"
            " ov.DisplayOrdinal AS OptionValueDisplayOrdinal"
        )

        if catalogue_by_product:
            # Gated: 3 IN lists + 2 params per VALUES pair => 5*chunk params.
            for chunk in self._chunked(ids, 400):
                ph = self._placeholders(len(chunk))
                values = ", ".join(
                    "(CAST(? AS INT), CAST(? AS INT))" for _ in chunk
                )
                query = (
                    base_cte.format(ph=ph)
                    + ", ProductCatalogue AS ( SELECT v.ProductId, v.CatalogueId"
                    + f" FROM (VALUES {values}) AS v(ProductId, CatalogueId) )"
                    + " SELECT DISTINCT iov.ProductId,"
                    + select_cols
                    + " FROM IncludedOptionValues iov"
                    + " INNER JOIN ProductCatalogue pc ON pc.ProductId = iov.ProductId"
                    + " INNER JOIN OptionValue ov ON iov.OptionValueId = ov.OptionValueId"
                    + " INNER JOIN [Option] o ON ov.OptionId = o.OptionId"
                    + " INNER JOIN CatalogueOptionValues cov"
                    + " ON cov.OptionValueId = ov.OptionValueId AND cov.CatalogueId = pc.CatalogueId"
                    + " WHERE ov.Status = 1"
                    + self._OPTIONS_HIDE_FILTER
                    + " AND NOT EXISTS ("
                    + " SELECT 1 FROM CatalogueProductOptionExclusions x"
                    + " WHERE x.CatalogueId = pc.CatalogueId"
                    + " AND x.ProductId = iov.ProductId"
                    + " AND x.OptionValueId = ov.OptionValueId)"
                    + " ORDER BY iov.ProductId, o.DisplayOrder, o.Name, ov.DisplayOrdinal"
                )
                pair_params: list[Any] = []
                for pid in chunk:
                    pair_params.append(pid)
                    pair_params.append(catalogue_by_product.get(pid))
                params = tuple(chunk) * 3 + tuple(pair_params)
                rows.extend(self._execute(query, params, connection=connection))
            return rows

        # Ungated resolution (no catalogue context).
        for chunk in self._chunked(ids, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                base_cte.format(ph=ph)
                + " SELECT DISTINCT iov.ProductId,"
                + select_cols
                + " FROM IncludedOptionValues iov"
                + " INNER JOIN OptionValue ov ON iov.OptionValueId = ov.OptionValueId"
                + " INNER JOIN [Option] o ON ov.OptionId = o.OptionId"
                + " WHERE ov.Status = 1"
                + self._OPTIONS_HIDE_FILTER
                + " ORDER BY iov.ProductId, o.DisplayOrder, o.Name, ov.DisplayOrdinal"
            )
            rows.extend(self._execute(query, tuple(chunk) * 3, connection=connection))
        return rows

    # -- PDM change monitoring (watermark-based, read-only) ---------------

    def fetch_watermarks(self) -> dict[str, int]:
        """Return current MAX primary-key ids for the key monitored tables."""
        queries = {
            "OptionValueId": "SELECT ISNULL(MAX(OptionValueId), 0) FROM OptionValue",
            "ProductId":     "SELECT ISNULL(MAX(ProductId), 0) FROM Product",
            "ItemId":        "SELECT ISNULL(MAX(ItemId), 0) FROM Item",
            "PriceFormulaId": "SELECT ISNULL(MAX(PriceFormulaId), 0) FROM PriceFormula",
        }
        result: dict[str, int] = {}
        conn = self.get_connection()
        try:
            for key, sql in queries.items():
                rows = self._execute(sql, (), connection=conn)
                result[key] = int(rows[0][0]) if rows else 0
        finally:
            conn.close()
        return result

    def fetch_new_option_values(self, since_id: int) -> list[Any]:
        """Return new OptionValues added after ``since_id`` with series/product context."""
        return self._execute(
            """
            SELECT DISTINCT
                ov.OptionValueId,
                o.Name        AS OptionName,
                ov.Name       AS ValueName,
                pr.Name       AS SeriesName,
                p.Product     AS ProductCode,
                p.Name        AS ProductName
            FROM OptionValue ov
            INNER JOIN [Option] o ON o.OptionId = ov.OptionId
            INNER JOIN ProductOptionValues pov ON pov.OptionValueId = ov.OptionValueId
            INNER JOIN Product p ON p.ProductId = pov.ProductId
            INNER JOIN ProductRange pr ON pr.ProductRangeId = p.ProductRangeId
            WHERE ov.OptionValueId > ?
              AND p.Status <> 2
            ORDER BY ov.OptionValueId
            """,
            (since_id,),
        )

    def fetch_new_products(self, since_id: int) -> list[Any]:
        """Return new Products added after ``since_id`` with series context."""
        return self._execute(
            """
            SELECT
                p.ProductId,
                p.Product     AS ProductCode,
                p.Name        AS ProductName,
                p.Status      AS ProductStatus,
                pr.Name       AS SeriesName
            FROM Product p
            INNER JOIN ProductRange pr ON pr.ProductRangeId = p.ProductRangeId
            WHERE p.ProductId > ?
              AND p.Status <> 2
            ORDER BY p.ProductId
            """,
            (since_id,),
        )

    def fetch_new_items(self, since_id: int) -> list[Any]:
        """Return new Items (SKUs) added after ``since_id`` with series/product context."""
        return self._execute(
            """
            SELECT
                i.ItemId,
                i.Item        AS ArticleCode,
                p.Product     AS ProductCode,
                p.Name        AS ProductName,
                pr.Name       AS SeriesName,
                i.Status      AS ItemStatus
            FROM Item i
            INNER JOIN Product p ON p.ProductId = i.ProductId
            INNER JOIN ProductRange pr ON pr.ProductRangeId = p.ProductRangeId
            WHERE i.ItemId > ?
              AND p.Status <> 2
            ORDER BY i.ItemId
            """,
            (since_id,),
        )

    def fetch_changed_option_value_statuses(self, since_date: str) -> list[Any]:
        """Return OptionValues whose Status changed on or after ``since_date``."""
        return self._execute(
            """
            SELECT DISTINCT
                ov.OptionValueId,
                o.Name        AS OptionName,
                ov.Name       AS ValueName,
                ov.Status     AS NewStatus,
                ov.NewStatusDate,
                pr.Name       AS SeriesName,
                p.Product     AS ProductCode,
                p.Name        AS ProductName
            FROM OptionValue ov
            INNER JOIN [Option] o ON o.OptionId = ov.OptionId
            INNER JOIN ProductOptionValues pov ON pov.OptionValueId = ov.OptionValueId
            INNER JOIN Product p ON p.ProductId = pov.ProductId
            INNER JOIN ProductRange pr ON pr.ProductRangeId = p.ProductRangeId
            WHERE ov.NewStatusDate >= ?
            ORDER BY ov.NewStatusDate DESC, ov.OptionValueId
            """,
            (since_date,),
        )

    # -- internals ---------------------------------------------------------
    def _search_query(self, pred: str) -> str:
        released = self._SEARCH_BRANCH.format(
            item_table="CatalogueItems", status="i.Status = 1", pred=pred
        )
        unreleased = self._SEARCH_BRANCH.format(
            item_table="CatalogueItemsUnreleased", status="i.Status < 2", pred=pred
        )
        return (
            "SELECT TOP (?)\n"
            "    q.ProductId, q.ProductCode, q.ProductName, q.ProductStatus,"
            " q.CatalogueId,"
            " q.CatalogueName, q.ProductCategoryName\n"
            "FROM (\n"
            f"{released}\n"
            "UNION\n"
            f"{unreleased}\n"
            ") q\n"
            "ORDER BY q.ProductCode, q.ProductName"
        )

    def _article_search_query(self) -> str:
        released = self._SEARCH_BRANCH_ARTICLE.format(
            item_table="CatalogueItems", status="im.Status = 1"
        )
        unreleased = self._SEARCH_BRANCH_ARTICLE.format(
            item_table="CatalogueItemsUnreleased", status="im.Status < 2"
        )
        return (
            "SELECT TOP (?)\n"
            "    q.ProductId, q.ProductCode, q.ProductName, q.ProductStatus,"
            " q.CatalogueId,"
            " q.CatalogueName, q.ProductCategoryName\n"
            "FROM (\n"
            f"{released}\n"
            "UNION\n"
            f"{unreleased}\n"
            ") q\n"
            "ORDER BY q.ProductCode, q.ProductName"
        )

    @staticmethod
    def _like_pattern(text: str) -> str:
        # Escape LIKE wildcards in the user input, then wrap for a contains
        # match. (The ESCAPE clause is not required for '[' with default
        # collation, but escaping %/_ keeps the search literal.)
        cleaned = (text or "").strip().replace("%", "[%]").replace("_", "[_]")
        return f"%{cleaned}%"

    def _execute(
        self, query: str, params: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Run a query and return all rows.

        When ``connection`` is supplied it is reused and left open (the caller
        owns its lifetime). When omitted a new connection is opened and closed
        for this single call - the original per-call behaviour.
        """
        owns_connection = connection is None
        conn = self.get_connection() if owns_connection else connection
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except self._driver().Error as error:
            raise PDMQueryError(f"PDM query failed: {error}") from error
        finally:
            if owns_connection:
                conn.close()
