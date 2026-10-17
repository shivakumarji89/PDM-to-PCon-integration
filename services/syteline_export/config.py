"""Configuration model for the separate SyteLine export module."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

ScopeMode = Literal["products", "range", "list"]


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
