"""Parameterized port of the legacy ExportThread item-selection SQL.

This module reproduces the source-defined item selection/filter rules only. It
does not perform the downstream option, price, material, or BOM transformations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ScopeMode = Literal["catalogue", "products", "range", "list"]


@dataclass(frozen=True)
class ItemSelection:
    site_id: int
    catalogue_id: int
    language_id: int
    other_language_id: int
    scope_mode: ScopeMode = "catalogue"
    product_code_id: int = -1
    min_item: str = ""
    max_item: str = ""
    item_list: tuple[str, ...] = ()
    active_only: bool = False
    syteline: bool = True
    miller_cad: bool = False
    item_report: bool = False
    export_all_catalogues_in_site: bool = False
    exclude_superproducts: bool = False
    max_description_length: int = 200
    include_list_price: bool = False
    currency: str = "GBP"
    list_price_effective_date: str = ""


@dataclass(frozen=True)
class ItemSelectionQuery:
    sql: str
    parameters: tuple[object, ...]


_BROWNING_ITEMS = (
    "BREF.CL", "BRWBTEENONN.AAM", "BRWLEELDLEFHN.AAMM",
    "BRWUPMEELSBRSGN.AAMWM", "BRWLEELDLEFHN.AAMM",
    "BRWLEELDLEFHN.AAWM", "BREUBLL.", "BREUBLR.",
)


def build_item_selection_query(selection: ItemSelection) -> ItemSelectionQuery:
    """Build the legacy SELECT/UNION with bound values instead of SQL concatenation."""
    if selection.site_id < 1 or selection.language_id < 1 or selection.other_language_id < 1:
        raise ValueError("Site, language, and alternate-language IDs must be positive.")
    if selection.catalogue_id < 1 and (selection.syteline or selection.miller_cad or selection.item_report or selection.scope_mode in {"products", "range"}):
        raise ValueError("A valid catalogue ID is required for this export scope.")
    if selection.scope_mode not in {"catalogue", "products", "range", "list"}:
        raise ValueError("Unsupported item-selection scope.")
    if selection.scope_mode == "products" and selection.product_code_id < 1:
        raise ValueError("A product code ID is required for product scope.")
    if selection.scope_mode == "range" and not (selection.min_item and selection.max_item):
        raise ValueError("Both minimum and maximum item codes are required for range scope.")
    if selection.max_description_length < 1:
        raise ValueError("Description length must be positive.")

    fields = [
        "SELECT DISTINCT Item.Item AS LongItem, Item.Notes, Item.LegacyItem,",
        "Item.Height, Item.Width, Item.Depth,",
        "CASE WHEN LEN(Item.Item) > 22 THEN SUBSTRING(Item.Item, 1, 22) ELSE Item.Item END AS Item,",
        "Item.Status, Item.FSCCompliant, Item.WeightKilos, Item.VolumeLitres,",
        "Product.Product, Product.IsSuperProduct, Item.ItemId,",
        "CASE WHEN item_desc.ShortDescription IS NOT NULL AND LEN(item_desc.ShortDescription) > 0",
        "THEN SUBSTRING(item_desc.ShortDescription, 1, ?) WHEN pd.ShortDescription IS NULL",
        "THEN Item.Item ELSE SUBSTRING(pd.ShortDescription, 1, ?) END AS ShortDescription,",
        "SUBSTRING(alt_desc.ShortDescription, 1, ?) AS AltDescription,",
        "CASE WHEN pc.BasePriceRef = 1 THEN Item.BasePrice WHEN pc.BasePriceRef = 2",
        "THEN Item.BasePrice2 WHEN pc.BasePriceRef = 3 THEN Item.BasePrice3 END AS MyBasePrice,",
    ]
    params: list[object] = [
        selection.max_description_length,
        selection.max_description_length,
        selection.max_description_length,
    ]
    if selection.include_list_price or selection.miller_cad or (selection.syteline and not selection.active_only):
        fields.append("dbo.fnGetListPriceByItem(Item.Item, ?, ?, ?, NULL) AS ListPrice,")
        params.extend([
            selection.currency, selection.list_price_effective_date, selection.site_id,
        ])
    fields.append(
        "Product.ProductId, pc.Product_Code, pc.Description, "
        "Product.OrderCodeFormatString AS prodFS, ProductRange.ProductRangeId, "
        "ProductRange.OrderCodeFormatString AS rangeFS, ProductRange.ProductCategoryId, "
        "Item.CommodityCode, pc.PriceCode "
    )
    fields.append(
        "FROM Item WITH (NOLOCK) CROSS JOIN (SELECT NULL AS ProductCodeIdOverride) x "
        "INNER JOIN Product ON Item.ProductId = Product.ProductId "
        "INNER JOIN ProductRange ON Product.ProductRangeId = ProductRange.ProductRangeId "
        "INNER JOIN Product_Code pc ON CASE WHEN (SELECT ProductCodeIdOverride FROM Item i2 "
        "WHERE i2.ItemId = Item.ItemId) IS NOT NULL THEN (SELECT ProductCodeIdOverride "
        "FROM Item i2 WHERE i2.ItemId = Item.ItemId) ELSE Product.ProductCodeId END = pc.ProductCodeId "
        "LEFT OUTER JOIN ProductDescription pd ON Product.DescriptionId = pd.DescriptionId "
        "AND pd.LanguageId = ? LEFT OUTER JOIN OtherDescription item_desc "
        "ON Item.DescriptionId = item_desc.DescriptionId AND item_desc.LanguageId = ? "
    )
    params.extend([selection.language_id, selection.language_id])
    joins_catalogue_items = selection.syteline or selection.miller_cad or selection.item_report
    if joins_catalogue_items:
        fields.append("INNER JOIN CatalogueItems ON Item.ItemId = CatalogueItems.ItemId ")
    if selection.miller_cad:
        fields.append("INNER JOIN Catalogue ON CatalogueItems.CatalogueId = Catalogue.CatalogueId ")
    fields.append(
        "LEFT OUTER JOIN ProductDescription alt_desc ON pd.DescriptionId = alt_desc.DescriptionId "
        "AND alt_desc.LanguageId = ? WHERE pc.SiteId = ? "
    )
    params.extend([selection.other_language_id, selection.site_id])

    if selection.scope_mode == "products":
        fields.append("AND pc.ProductCodeId = ? AND CatalogueItems.CatalogueId = ? ")
        params.extend([selection.product_code_id, selection.catalogue_id])
    elif selection.scope_mode == "range":
        if selection.min_item == "BRW" and selection.max_item == "BRW":
            fields.append("AND Item.Item IN (" + ", ".join("?" for _ in _BROWNING_ITEMS) + ") ")
            params.extend(_BROWNING_ITEMS)
        else:
            fields.append(
                "AND (Item.Item > ? OR Item.Item LIKE ?) "
                "AND (Item.Item < ? OR Item.Item LIKE ?) "
            )
            params.extend([
                selection.min_item, selection.min_item + "%",
                selection.max_item, selection.max_item + "%",
            ])
        if selection.syteline:
            fields.append("AND CatalogueItems.CatalogueId = ? ")
            params.append(selection.catalogue_id)
    elif selection.scope_mode == "list":
        if selection.item_list:
            fields.append("AND Item.Item IN (" + ", ".join("?" for _ in selection.item_list) + ") ")
            params.extend(selection.item_list)
    elif selection.syteline:
        fields.append("AND CatalogueItems.CatalogueId = ? ")
        params.append(selection.catalogue_id)
    elif selection.miller_cad:
        if selection.export_all_catalogues_in_site:
            fields.append("AND Catalogue.PrimarySiteId = ? ")
            params.append(selection.site_id)
        else:
            fields.append("AND CatalogueItems.CatalogueId = ? ")
            params.append(selection.catalogue_id)
    elif selection.item_report:
        if selection.active_only:
            fields.append("AND CatalogueItems.CatalogueId = ? ")
            params.append(selection.catalogue_id)
        else:
            # The original replaces the inner join with two left joins in this mode.
            sql = "".join(fields).replace(
                "INNER JOIN CatalogueItems ON Item.ItemId = CatalogueItems.ItemId ",
                "LEFT OUTER JOIN CatalogueItems ON Item.ItemId = CatalogueItems.ItemId "
                "LEFT OUTER JOIN CatalogueItemsUnreleased ON Item.ItemId = CatalogueItemsUnreleased.ItemId ",
            )
            fields = [sql]
            fields.append("AND (CatalogueItems.CatalogueId = ? OR CatalogueItemsUnreleased.CatalogueId = ?) ")
            params.extend([selection.catalogue_id, selection.catalogue_id])

    if selection.active_only:
        fields.append("AND Product.Status = 1 AND Item.Status = 1 ")
    base_sql = "".join(fields)
    sql = base_sql
    if not selection.active_only:
        # Keep the source's UNION against unreleased catalogue membership.
        unreleased_sql = base_sql.replace("CatalogueItems", "CatalogueItemsUnreleased").replace(
            "Item.Status", "0 AS Status"
        )
        sql = base_sql + " UNION " + unreleased_sql
        params = params + params
    if selection.exclude_superproducts and selection.active_only:
        # Source-specific SQL text rewrite, retained for parity; still bound values.
        alternate = base_sql.replace(
            "INNER JOIN CatalogueItems ON Item.ItemId",
            "INNER JOIN ItemComponents itco ON Item.ItemId = itco.SubItemId "
            "INNER JOIN Item sp_item ON itco.ItemId = sp_item.ItemId "
            "INNER JOIN CatalogueItems ON sp_item.ItemId",
        ).replace("Item.Item ", "sp_item.Item ").replace(
            "sp_item.Item AS LongItem", "Item.Item AS LongItem"
        ).replace("sp_item.Item END AS Item", "Item.Item END AS Item").replace(
            "pd.ShortDescription IS NULL THEN sp_item.Item",
            "pd.ShortDescription IS NULL THEN Item.Item",
        )
        sql += " UNION " + alternate + " AND sp_item.Status = 1"
        params.extend(params[:len(params)])
    sql += " ORDER BY Item.Item"
    return ItemSelectionQuery(sql, tuple(params))
