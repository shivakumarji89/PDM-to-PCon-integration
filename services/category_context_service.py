"""Central category/workspace context.

Keeps Seating/Tables classification in one place so repository discovery,
PDM-loaded products and generation select the same workspace semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.base_service import BaseService


@dataclass(frozen=True)
class CategoryContext:
    """Normalized category plus the engineering workspace/template kind."""

    category: str = ""
    workspace_kind: str = ""
    source: str = ""


class CategoryContextService(BaseService):
    """Resolve product category into the shared workspace context."""

    _WORKSPACES = {
        "seating": "seating",
        "tables": "tables",
    }

    def resolve(
        self,
        category: str = "",
        *,
        range_name: str = "",
        product_name: str = "",
        source: str = "",
    ) -> CategoryContext:
        """Resolve a canonical workspace from explicit category first.

        The explicit category is authoritative. Range/name keywords remain only
        as a compatibility fallback for legacy PDM data where category is empty.
        """
        raw = (category or "").strip()
        kind = self._workspace_from_text(raw)
        if not kind:
            fallback = " ".join(
                part for part in (range_name or "", product_name or "") if part
            )
            kind = self._workspace_from_text(fallback)

        canonical = (
            "Seating" if kind == "seating"
            else "Tables" if kind == "tables"
            else raw
        )
        return CategoryContext(
            category=canonical,
            workspace_kind=kind,
            source=source,
        )

    def from_product(self, product) -> CategoryContext:
        return self.resolve(
            getattr(product, "category", "") or "",
            range_name=getattr(product, "range_name", "") or "",
            product_name=getattr(product, "name", "") or "",
            source="pdm_product",
        )

    def from_repository_path(self, folder: str | Path) -> CategoryContext:
        parts = [part.casefold() for part in Path(folder).parts]
        for part in parts:
            kind = self._WORKSPACES.get(part)
            if kind:
                return CategoryContext(
                    category="Seating" if kind == "seating" else "Tables",
                    workspace_kind=kind,
                    source="repository_workspace",
                )
        return CategoryContext(source="repository_workspace")

    @staticmethod
    def _workspace_from_text(value: str) -> str:
        text = (value or "").casefold()
        if any(token in text for token in ("table", "desk", "desking")):
            return "tables"
        if any(token in text for token in ("seating", "seat", "chair")):
            return "seating"
        return ""
