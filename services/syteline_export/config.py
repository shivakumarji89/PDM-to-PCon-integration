"""Configuration model and legacy TSV output validation for SyteLine export."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Literal

ScopeMode = Literal["catalogue", "products", "range", "list"]

# Headers captured from the supplied legacy Verbose Extract files.
# The item output was empty in the supplied run, so its schema is deliberately
# not guessed here.
# The legacy product-code writer emits four data fields beneath a five-column
# header (UnitCode is not written). Accept that observed source behavior rather
# than falsely treating every real legacy file as malformed.
LEGACY_TSV_ROW_WIDTHS: dict[str, frozenset[int]] = {
    "productcode": frozenset({4, 5}),
}


LEGACY_TSV_HEADERS: dict[str, tuple[str, ...]] = {
    "description": ("Lang", "Item", "Description"),
    "planning": (
        "Item", "Description", "Product Code", "Vendor Call", "Stocked",
        "Dock to Stock", "Fixed lead time", "Planner Code", "Days Supply",
        "Safety Stock", "Buyer", "CustomH", "CustomW", "CustomD",
        "Gross Weight", "LocRank", "Location", "Origin Country", "Pack qty",
        "Accept Requirement", "Pass Requirement", "Kanban qty",
    ),
    "superprod": (
        "Item", "Super Description", "Seq", "Component", "Quantity",
        "Description", "Num Features", "FP1", "FP2", "FP3", "FP4", "FP5",
        "FP6", "FP7", "FP8", "FP9", "FP10", "FP11", "FP12",
    ),
    "material": (
        "Parent Item", "Feature", "Component", "Opt code", "Inc. price",
        "Matl Qty", "Scrap fact", "Seq", "Effect Date", "Obs Date",
        "Oper Num", "BackFlush",
    ),
    "priceformula": (
        "Site", "CustPriceCode", "ItemPriceCode", "PriceFormula",
        "PriceFactor", "EffectiveDate",
    ),
    "productcode": (
        "Site", "ProductCode", "Description", "PriceCode", "UnitCode",
    ),
}


def parse_legacy_tsv(text: str, output_name: str) -> tuple[tuple[str, ...], ...]:
    """Parse a legacy tab-separated output and check its known header/row widths.

    Header-only files are valid: an individual extract can legitimately contain
    no rows. Empty files are accepted only for the item output, whose schema
    could not be observed in the supplied extraction.
    """
    if output_name not in (*LEGACY_TSV_HEADERS, "item"):
        raise ValueError(f"Unknown legacy output family: {output_name}")
    if not text.strip():
        if output_name == "item":
            return ()
        raise ValueError(f"{output_name} output is empty; expected a header row.")

    rows = tuple(tuple(row) for row in csv.reader(StringIO(text), delimiter="\t"))
    if not rows or not rows[0]:
        raise ValueError(f"{output_name} output is missing its header.")
    expected = LEGACY_TSV_HEADERS.get(output_name)
    if expected is not None and rows[0] != expected:
        raise ValueError(
            f"{output_name} header mismatch: expected {expected!r}, got {rows[0]!r}"
        )
    width = len(rows[0])
    allowed_widths = LEGACY_TSV_ROW_WIDTHS.get(output_name, frozenset({width}))
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) not in allowed_widths:
            expected = " or ".join(str(n) for n in sorted(allowed_widths))
            raise ValueError(
                f"{output_name} row {line_number} has {len(row)} columns; expected {expected}."
            )
    return rows


@dataclass(frozen=True)
class SyteLineExportConfig:
    server: str
    database: str
    output_directory: Path
    site: str
    product_line: str = ""
    catalogue: str = ""
    language: str = ""
    currency: str = "GBP"
    scope_mode: ScopeMode = "products"
    min_item: str = ""
    max_item: str = ""
    item_list: tuple[str, ...] = ()
    options: frozenset[str] = field(default_factory=frozenset)
    site_id: int = 0
    catalogue_id: int = 0
    language_id: int = 0
    other_language_id: int = 0
    currency_id: int = 0
    product_code_id: int = -1
    export_mode: Literal["syteline", "csi", "ofda", "other"] = "syteline"
    effective_date: str = ""
    export_all_catalogues_in_site: bool = False
    active_only: bool = True
    export_base_prices: bool = True
    export_bom_data: bool = False
    extend_sp_options: bool = False
    run_as_service: bool = False
    length5_feats: bool = False
    ignore_option_dependencies: bool = False
    unique_components: bool = True
    plc_phantoms: bool = False
    exclude_superproducts: bool = False
    superproducts_only: bool = False
    flatten_fabrics: bool = False
    miller_cad: bool = False
    item_report: bool = False
    send_tradenet: str = ""
    send_contract: str = ""

    def legacy_thread_arguments(self) -> dict[str, object]:
        """Return the source-named arguments accepted by legacy ExportThread.initThread.

        This is a deterministic mapping contract only; it does not invoke the
        legacy thread or enable export.
        """
        return {
            "siteId": self.site_id,
            "site": self.site,
            "catalogueId": self.catalogue_id,
            "languageId": self.language_id,
            "currency": self.currency,
            "productCodeId": self.product_code_id,
            "productcheck": self.scope_mode == "products",
            "rangecheck": self.scope_mode == "range",
            "minitem": self.min_item,
            "maxitem": self.max_item,
            "listcheck": self.scope_mode == "list",
            "itemlist": list(self.item_list),
            "activeonly": self.active_only,
            "syteline": self.export_mode == "syteline",
            "millerCAD": self.miller_cad,
            "itemreport": self.item_report,
            "sendTradeNet": self.send_tradenet,
            "sendContract": self.send_contract,
            "exportBasePrices": self.export_base_prices,
            "effectiveDate": self.effective_date,
            "exportAllCataloguesInSite": self.export_all_catalogues_in_site,
            "otherlanguageId": self.other_language_id,
            "exportBOMData": self.export_bom_data,
            "extendSPOpts": self.extend_sp_options,
            "runAsService": self.run_as_service,
            "length5Feats": self.length5_feats,
            "ignoreOptDeps": self.ignore_option_dependencies,
            "uniqueComponents": self.unique_components,
            "formatCSI": self.export_mode == "csi",
            "plcPhantoms": self.plc_phantoms,
            "excludeSuperProducts": self.exclude_superproducts,
            "superProductsOnly": self.superproducts_only,
            "flattenFabrics": self.flatten_fabrics,
        }

    def validate_for_execution(self) -> tuple[str, ...]:
        """Validate local values and required database identities before execution."""
        errors = list(self.validate())
        for field_name, label in (
            ("site_id", "Site"),
            ("catalogue_id", "Catalogue"),
            ("language_id", "Language"),
            ("currency_id", "Currency"),
        ):
            if getattr(self, field_name) < 1:
                errors.append(f"{label} must be selected from live database choices.")
        if self.scope_mode == "products" and self.product_code_id < 1:
            errors.append("Select a product code from live database choices when product-code filtering is enabled.")
        if self.export_mode not in {"syteline", "csi", "ofda", "other"}:
            errors.append("Unsupported export mode.")
        return tuple(errors)

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if not self.server.strip():
            errors.append("SQL Server is required.")
        if not self.database.strip():
            errors.append("Database name is required.")
        if not self.site.strip():
            errors.append("Site is required.")
        if not self.currency.strip():
            errors.append("Currency is required.")
        if not str(self.output_directory).strip():
            errors.append("Output folder is required.")
        elif not self.output_directory.expanduser().is_dir():
            errors.append("Output folder must already exist.")
        if self.scope_mode not in {"catalogue", "products", "range", "list"}:
            errors.append("Unknown export scope mode.")
        if self.scope_mode == "range":
            if not self.min_item.strip() or not self.max_item.strip():
                errors.append("Both range endpoints are required.")
            elif self.min_item > self.max_item:
                errors.append("First item must not sort after last item.")
        elif self.scope_mode == "list":
            if not self.item_list:
                errors.append("At least one item code is required.")
            elif len(self.item_list) != len(set(self.item_list)):
                errors.append("Item list contains duplicates.")
        if not self.options.intersection(
            {"products", "ranges", "lists", "base_prices", "ofda", "bom"}
        ):
            errors.append("Select at least one export data type.")
        return tuple(errors)
