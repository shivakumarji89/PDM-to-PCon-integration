"""The Loading Engine.

The single backend that serves every loading operation (Load Product / Family /
Category / Catalogue). It executes the frozen pipeline in full - including the
four bulk ``WHERE ProductId IN (...)`` queries - and returns a completed
snapshot.

Frozen pipeline (each stage is its own private method):

    Resolve Product IDs
    Bulk Query #1 - Product Info
    Bulk Query #2 - Attributes
    Bulk Query #3 - Options
    Bulk Query #4 - Items
    Build Lookup Indexes
    Build Product Objects
    Build Snapshot
    Engineering Initialization
    (Return Snapshot)

The only per-selection-type difference is Product ID resolution; once the ids
are known the remaining pipeline is identical. All four bulk queries run over a
single shared connection. The engine reports progress through the Activity
Framework (one activity per run, stage-based percentage, elapsed time, current
operation) and does not touch the existing Load Product / Load Family
implementations or the shared active snapshot.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from core.activity import ActivityType
from models.product import Product
from models.snapshot import Snapshot, SnapshotMetadata
from services.loading.load_request import LoadRequest, LoadResult, SelectionType

if TYPE_CHECKING:
    from core.activity.handle import ActivityHandle
    from core.application_context import ApplicationContext


@dataclass
class _LookupIndexes:
    """Bulk results indexed by product id (string keys)."""

    info: dict[str, Any] = field(default_factory=dict)
    attributes: dict[str, list] = field(default_factory=dict)
    options: dict[str, list] = field(default_factory=dict)
    items: dict[str, list] = field(default_factory=dict)


@dataclass
class _BuiltProduct:
    """A product plus its mapped engineering data (before snapshot merge)."""

    product: Product
    properties: list = field(default_factory=list)
    property_values: list = field(default_factory=list)
    options: list = field(default_factory=list)
    option_values: list = field(default_factory=list)
    articles: list = field(default_factory=list)


class LoadingEngine:
    """Runs the complete bulk loading pipeline for any selection type."""

    #: The ordered pipeline stages (drives progress percentage).
    _STAGES: tuple[str, ...] = (
        "Resolve Selection Context",
        "Load Product Information",
        "Load Attributes",
        "Load Options",
        "Load Items",
        "Build Lookup Indexes",
        "Build Product Objects",
        "Build Snapshot",
        "Engineering Initialization",
    )

    def __init__(self, context: "ApplicationContext") -> None:
        self._context = context

    # -- public entry point ------------------------------------------------
    def load(self, request: LoadRequest) -> LoadResult:
        """Execute the full bulk pipeline for ``request`` and return a result."""
        activity = self._context.activity_service.start_activity(
            self._title(request),
            ActivityType.LOAD,
            total_stages=len(self._STAGES),
            supports_cancel=True,
            context={
                "Selection": request.selection_type.value,
                "Label": request.label or (request.selection_id or ""),
            },
        )
        connection = None
        try:
            product_ids, catalogue_by_product = self._resolve_selection_context(
                request, activity
            )
            if product_ids:
                connection = self._repository().get_connection()

            info_rows = self._load_product_information(product_ids, activity, connection)
            attribute_rows = self._load_attributes(product_ids, activity, connection)
            option_rows = self._load_options(
                product_ids, catalogue_by_product, activity, connection
            )
            item_rows = self._load_items(product_ids, activity, connection)

            indexes = self._build_lookup_indexes(
                info_rows, attribute_rows, option_rows, item_rows, activity
            )
            built = self._build_product_objects(product_ids, indexes, activity)
            snapshot = self._build_snapshot(built, request, activity)
            self._engineering_initialization(snapshot, activity)

            activity.complete("Load complete")
            return LoadResult(
                ok=True,
                snapshot=snapshot,
                product_ids=product_ids,
                activity_id=activity.id,
            )
        except Exception as error:  # defensive: report and never leak partials
            activity.fail(str(error))
            return LoadResult(ok=False, message=str(error), activity_id=activity.id)
        finally:
            if connection is not None:
                connection.close()

    # -- pipeline stages ---------------------------------------------------
    def _resolve_selection_context(
        self, request: LoadRequest, activity: "ActivityHandle"
    ) -> tuple[list[str], dict[str, Any]]:
        self._begin_stage(activity, 0, "Resolving selection context")
        # Selection-type-specific resolution is the ONLY branch in the pipeline.
        # It yields the product ids AND their catalogue context so downstream
        # bulk queries produce results identical to the existing loader.
        if request.products:
            product_ids = [p.id for p in request.products]
            catalogue_by_product = {
                p.id: getattr(p, "catalogue_id", None) for p in request.products
            }
        elif request.selection_type is SelectionType.PRODUCT and request.selection_id:
            product_ids = [request.selection_id]
            catalogue_by_product = {}
        else:
            product_ids = list(request.product_ids)
            catalogue_by_product = {}
        activity.add_log(f"Resolved {len(product_ids)} product id(s)")
        return product_ids, catalogue_by_product

    def _load_product_information(
        self, product_ids: list[str], activity: "ActivityHandle", connection
    ) -> list:
        self._begin_stage(activity, 1, "Loading product information")
        rows = self._repository().fetch_products_info(product_ids, connection=connection)
        activity.add_log(f"Product info rows: {len(rows)}")
        return rows

    def _load_attributes(
        self, product_ids: list[str], activity: "ActivityHandle", connection
    ) -> list:
        self._begin_stage(activity, 2, "Loading attributes")
        rows = self._repository().fetch_products_attributes(
            product_ids, connection=connection
        )
        activity.add_log(f"Attribute rows: {len(rows)}")
        return rows

    def _load_options(
        self,
        product_ids: list[str],
        catalogue_by_product: dict[str, Any],
        activity: "ActivityHandle",
        connection,
    ) -> list:
        self._begin_stage(activity, 3, "Loading options")
        rows = self._repository().fetch_products_options(
            product_ids,
            catalogue_by_product=catalogue_by_product or None,
            connection=connection,
        )
        activity.add_log(f"Option rows: {len(rows)}")
        return rows

    def _load_items(
        self, product_ids: list[str], activity: "ActivityHandle", connection
    ) -> list:
        self._begin_stage(activity, 4, "Loading items")
        rows = self._repository().fetch_products_items(
            product_ids, connection=connection
        )
        activity.add_log(f"Item rows: {len(rows)}")
        return rows

    def _build_lookup_indexes(
        self,
        info_rows: list,
        attribute_rows: list,
        option_rows: list,
        item_rows: list,
        activity: "ActivityHandle",
    ) -> _LookupIndexes:
        self._begin_stage(activity, 5, "Building lookup indexes")
        info = {str(r.ProductId): r for r in info_rows}
        attributes: dict[str, list] = defaultdict(list)
        for r in attribute_rows:
            attributes[str(r.ProductId)].append(r)
        options: dict[str, list] = defaultdict(list)
        for r in option_rows:
            options[str(r.ProductId)].append(r)
        items: dict[str, list] = defaultdict(list)
        for r in item_rows:
            items[str(r.ProductId)].append(r)
        return _LookupIndexes(
            info=info,
            attributes=dict(attributes),
            options=dict(options),
            items=dict(items),
        )

    def _build_product_objects(
        self,
        product_ids: list[str],
        indexes: _LookupIndexes,
        activity: "ActivityHandle",
    ) -> list[_BuiltProduct]:
        self._begin_stage(activity, 6, "Building product objects")
        pdm = self._context.pdm_service
        built: list[_BuiltProduct] = []
        for pid in product_ids:
            product = Product(id=pid)
            info_row = indexes.info.get(pid)
            if info_row is not None:
                # Reuse the proven single-product mapping (no duplication).
                pdm._apply_product_info(product, [info_row])
                product.code = (info_row.ProductCode or "").strip()

            properties, property_values = pdm._map_attributes(
                indexes.attributes.get(pid, [])
            )
            options, option_values = pdm._map_options(indexes.options.get(pid, []))
            articles = pdm._map_articles(indexes.items.get(pid, []), pid)

            product.options = options
            product.articles = articles
            built.append(
                _BuiltProduct(
                    product=product,
                    properties=properties,
                    property_values=property_values,
                    options=options,
                    option_values=option_values,
                    articles=articles,
                )
            )
        activity.add_log(f"Built {len(built)} product object(s)")
        return built

    def _build_snapshot(
        self,
        built: list[_BuiltProduct],
        request: LoadRequest,
        activity: "ActivityHandle",
    ) -> Snapshot:
        self._begin_stage(activity, 7, "Building snapshot")
        # The engine builds a fresh snapshot and merges every product's mapped
        # data into the flat collections (append-only). It does NOT touch the
        # shared SnapshotManager, so existing loaders are unaffected.
        snapshot = Snapshot()
        if built:
            first = built[0].product
            snapshot.product = first
            snapshot.id = first.id
        for entry in built:
            snapshot.articles.extend(entry.articles)
            snapshot.properties.extend(entry.properties)
            snapshot.property_values.extend(entry.property_values)
            snapshot.options.extend(entry.options)
            snapshot.option_values.extend(entry.option_values)
        snapshot.metadata = SnapshotMetadata(
            source="LoadingEngine",
            product_code=request.label or (request.selection_id or ""),
        )
        return snapshot

    def _engineering_initialization(
        self, snapshot: Snapshot, activity: "ActivityHandle"
    ) -> None:
        self._begin_stage(activity, 8, "Initializing engineering")
        self._context.engineering_initialization_service.initialize(snapshot)
        # Structural-trait classifier (post-load, read-only): tag the snapshot
        # with its ProductProfile so downstream workflows pick the right approach.
        self._context.product_profile_service.classify(snapshot)
        # Background relationship engine: derive the explicit Article/Property/
        # Value relationship maps from the freshly initialized engineering graph.
        # This runs on the engine's worker thread, so the workflow never waits.
        self._context.engineering_relationship_service.rebuild(snapshot)

    # -- helpers -----------------------------------------------------------
    def _repository(self):
        return self._context.pdm_service.repository

    def _begin_stage(
        self, activity: "ActivityHandle", index: int, operation: str
    ) -> None:
        """Report the current stage, operation and (stage-based) percentage."""
        activity.update_step(
            operation,
            stage_name=self._STAGES[index],
            stage_index=index + 1,
            total_stages=len(self._STAGES),
        )

    @staticmethod
    def _title(request: LoadRequest) -> str:
        label = request.label or request.selection_id or ""
        kind = request.selection_type.value.capitalize()
        return f"Loading {kind}: {label}" if label else f"Loading {kind}"
