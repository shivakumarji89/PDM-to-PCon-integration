"""Configuration model and legacy TSV output validation for SyteLine export."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Literal

ScopeMode = Literal["products", "range", "list"]

# Headers captured from the supplied legacy Verbose Extract files.
# The item output was empty in the supplied run, so its schema is deliberately
# not guessed here.
LEGACY_TSV_HEADERS: dict[str, tuple[str, ...]] = {
    "description": ("Lang", "Item", "Description"),
    "planning": (
        "Item", "Description", "Product Code", "Vendor", "Call", "Stocked",
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
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            raise ValueError(
                f"{output_name} row {line_number} has {len(row)} columns; expected {width}."
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
