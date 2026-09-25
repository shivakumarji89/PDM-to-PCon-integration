"""Loading Engine - request and result models.

Data-only models describing a loading request and its result. The request is
passed through the :class:`~services.loading.loading_engine.LoadingEngine`; the
only difference between selection types is how Product IDs are resolved - once
they are known the pipeline is identical.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from models.product import Product
from models.snapshot import Snapshot


class SelectionType(str, Enum):
    """What the user selected in the explorer."""

    PRODUCT = "product"
    FAMILY = "family"
    CATEGORY = "category"
    CATALOGUE = "catalogue"


@dataclass
class LoadRequest:
    """A single loading request routed through the Loading Engine.

    The request carries the *selection context* - the selected ``products``
    (each with its own ``catalogue_id``) - not just their ids, so the engine can
    resolve catalogue-gated data identically to the existing loader.
    ``load_options`` is reserved for future flags and is never interpreted here.
    """

    selection_type: SelectionType
    selection_id: str | None = None
    #: The selected products (carry catalogue context). May be empty when only
    #: ids are known (then catalogue-gated stages fall back to ungated).
    products: list[Product] = field(default_factory=list)
    product_ids: list[str] = field(default_factory=list)
    load_options: dict[str, Any] = field(default_factory=dict)
    #: Human-readable label for progress/UI (family/category/catalogue name).
    label: str = ""

    # -- convenience constructors (Phase 5 entry-point mapping) ------------
    @classmethod
    def for_product(cls, product: Product | str, label: str = "") -> "LoadRequest":
        if isinstance(product, Product):
            return cls(
                SelectionType.PRODUCT,
                selection_id=product.id,
                products=[product],
                product_ids=[product.id] if product.id else [],
                label=label or (product.name or ""),
            )
        return cls(
            SelectionType.PRODUCT,
            selection_id=product,
            product_ids=[product] if product else [],
            label=label,
        )

    @classmethod
    def for_family(
        cls,
        products: list[Product] | list[str] | None = None,
        selection_id: str | None = None,
        label: str = "",
    ) -> "LoadRequest":
        return cls._grouping(SelectionType.FAMILY, products, selection_id, label)

    @classmethod
    def for_category(
        cls,
        products: list[Product] | list[str] | None = None,
        selection_id: str | None = None,
        label: str = "",
    ) -> "LoadRequest":
        return cls._grouping(SelectionType.CATEGORY, products, selection_id, label)

    @classmethod
    def for_catalogue(
        cls,
        products: list[Product] | list[str] | None = None,
        selection_id: str | None = None,
        label: str = "",
    ) -> "LoadRequest":
        return cls._grouping(SelectionType.CATALOGUE, products, selection_id, label)

    @classmethod
    def _grouping(
        cls,
        selection_type: SelectionType,
        products: list[Product] | list[str] | None,
        selection_id: str | None,
        label: str,
    ) -> "LoadRequest":
        items = list(products or [])
        if items and isinstance(items[0], Product):
            return cls(
                selection_type,
                selection_id=selection_id,
                products=items,  # type: ignore[arg-type]
                product_ids=[p.id for p in items],  # type: ignore[union-attr]
                label=label,
            )
        # Ids-only fallback (catalogue-gated stages become ungated).
        return cls(
            selection_type,
            selection_id=selection_id,
            product_ids=[str(x) for x in items],
            label=label,
        )


@dataclass
class LoadResult:
    """The outcome of a Loading Engine run."""

    ok: bool
    snapshot: Snapshot | None = None
    message: str = ""
    product_ids: list[str] = field(default_factory=list)
    #: The Activity id used to report this load (for correlation / UI).
    activity_id: str | None = None
