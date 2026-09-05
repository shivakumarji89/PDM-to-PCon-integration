"""PDM service.

Coordinates read-only PDM data retrieval and snapshot population. It asks the
:class:`~repositories.pdm_repository.PDMRepository` for data (all SQL lives
there), maps the rows into strongly typed models, and loads the result into the
active snapshot via the shared :class:`~core.snapshot_manager.SnapshotManager`.

Contains no SQL and no MDB/export/validation/business logic.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path

from core.errors import PDMError
from models.article import Article
from models.option import Option
from models.option_value import OptionValue
from models.product import Product
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot, SnapshotMetadata
from repositories.pdm_repository import PDMRepository
from services.base_service import BaseService


@dataclass
class ProductLoadResult:
    """Outcome of a product load request."""

    ok: bool
    message: str
    snapshot: Snapshot | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class ProductLoadData:
    """Internal transport for a product's fetched-and-mapped engineering data.

    Not part of the public API - it exists only to carry the Fetch + Map stage
    output between :meth:`PDMService._fetch_and_map` and
    :meth:`PDMService._populate_snapshot`. It holds no snapshot and no metadata.
    """

    product: Product
    properties: list[Property]
    property_values: list[PropertyValue]
    options: list[Option]
    option_values: list[OptionValue]
    articles: list[Article]


@dataclass
class _SnapshotAccumulator:
    """Local property/option collections built before assigning them onto the
    snapshot atomically (so a background details load never leaves the
    snapshot's lists mid-append while the Articles workflow reads them)."""

    properties: list = field(default_factory=list)
    property_values: list = field(default_factory=list)
    options: list = field(default_factory=list)
    option_values: list = field(default_factory=list)


class PDMService(BaseService):
    """Read-only PDM integration and snapshot population."""

    #: On-disk identity-only product registry cache (Catalogue/Category/Product).
    _REGISTRY_CACHE = (
        Path(__file__).resolve().parents[1] / "cache" / "global_product_registry.json"
    )
    # Bumped to 2 when catalogue fetching was scoped to active + region (UK):
    # invalidates the stale all-region cache so it rebuilds on next launch.
    _REGISTRY_SCHEMA_VERSION = 3

    #: On-disk cache of a loaded FAMILY snapshot's source PDM data - one JSON
    #: file per family, named after the family (e.g. "bolster.json").
    _SNAPSHOT_CACHE_DIR = (
        Path(__file__).resolve().parents[1] / "cache" / "pdm_snapshots"
    )
    _SNAPSHOT_SCHEMA_VERSION = 2

    def __init__(self, context) -> None:
        super().__init__(context)
        self._repository: PDMRepository | None = None
        self._connected = False

    # -- repository access -------------------------------------------------
    @property
    def repository(self) -> PDMRepository:
        if self._repository is None:
            self._repository = PDMRepository(self.context)
        return self._repository

    # -- connection --------------------------------------------------------
    def connect(self) -> str:
        """Verify PDM connectivity; returns the connected database name."""
        database = self.repository.test_connection()
        self._connected = True
        return database

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    # -- product listing ---------------------------------------------------
    def get_products(self) -> list[Product]:
        """Return the selectable products from PDM as ``Product`` models.

        Loads the entire catalogue; retained for completeness but not used by
        the UI, which searches on demand via :meth:`search_products`.
        """
        rows = self.repository.fetch_products()
        products: list[Product] = []
        for row in rows:
            products.append(
                Product(
                    id=str(row.ProductId),
                    code=(row.ProductCode or "").strip(),
                    name=(row.ProductName or "").strip(),
                    category=(row.ProductCategoryName or "").strip(),
                    description=(row.CatalogueName or "").strip(),
                    catalogue_id=str(row.CatalogueId) if row.CatalogueId is not None else None,
                    lead_time=int(row.LeadTime) if getattr(row, "LeadTime", None) is not None else None,
                )
            )
        self._connected = True
        return products

    # -- cached product listing (identity-only registry) ------------------
    def get_cached_products(self, force_refresh: bool = False) -> list[Product]:
        """Return the product hierarchy, preferring the on-disk registry cache.

        On the first launch (or when ``force_refresh`` is set) the full
        catalogue is pulled from PDM via :meth:`get_products` and written to
        ``cache/global_product_registry.json``; subsequent launches load from
        that file without touching the database.
        """
        if not force_refresh:
            cached = self._load_registry_cache()
            if cached is not None:
                return cached
        products = self.get_products()
        self._save_registry_cache(products)
        return products

    def _load_registry_cache(self) -> list[Product] | None:
        try:
            if not self._REGISTRY_CACHE.exists():
                return None
            data = json.loads(self._REGISTRY_CACHE.read_text(encoding="utf-8"))
            if data.get("schema_version") != self._REGISTRY_SCHEMA_VERSION:
                return None
            products = [
                Product(
                    id=entry.get("id"),
                    code=entry.get("code", ""),
                    name=entry.get("name", ""),
                    category=entry.get("category", ""),
                    description=entry.get("description", ""),
                    catalogue_id=entry.get("catalogue_id"),
                    lead_time=entry.get("lead_time"),
                )
                for entry in data.get("products", [])
            ]
            return products or None
        except (OSError, ValueError):
            # A missing or corrupt cache simply falls back to a live query.
            return None

    def _save_registry_cache(self, products: list[Product]) -> None:
        try:
            self._REGISTRY_CACHE.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema_version": self._REGISTRY_SCHEMA_VERSION,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "count": len(products),
                "products": [
                    {
                        "id": p.id,
                        "code": p.code,
                        "name": p.name,
                        "category": p.category,
                        "description": p.description,
                        "catalogue_id": p.catalogue_id,
                        "lead_time": p.lead_time,
                    }
                    for p in products
                ],
            }
            self._REGISTRY_CACHE.write_text(
                json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        except OSError:
            # Cache writing is best-effort and must never break a load.
            pass

    # -- family snapshot cache (source data only) -------------------------
    def save_family_snapshot(
        self, snapshot: Snapshot | None, family_name: str
    ) -> Path | None:
        """Persist a loaded family snapshot's source data to disk.

        Writes ``cache/pdm_snapshots/<family>.json`` containing the source PDM
        data (the product plus the flat article/property/value/option
        collections) AND the engineering section (families keyed by id, each
        member's ``reduced_article`` / ``long_description`` / property
        assignments, and the engineering property vocabulary). Best-effort: any
        failure is swallowed so it never affects the load. Returns the written
        path, or ``None`` on failure / when there is nothing to save.
        """
        if snapshot is None:
            return None
        try:
            self._SNAPSHOT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            path = (
                self._SNAPSHOT_CACHE_DIR
                / f"{self._sanitize_family_name(family_name)}.json"
            )
            payload = {
                "schema_version": self._SNAPSHOT_SCHEMA_VERSION,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "family_name": family_name,
                "product": (
                    self._scalars(snapshot.product) if snapshot.product else None
                ),
                "articles": [self._scalars(a) for a in snapshot.articles],
                "properties": [self._scalars(p) for p in snapshot.properties],
                "property_values": [
                    self._scalars(v) for v in snapshot.property_values
                ],
                "options": [self._scalars(o) for o in snapshot.options],
                "option_values": [self._scalars(v) for v in snapshot.option_values],
                "engineering": self._engineering_dict(snapshot.engineering),
                # Snapshot-level maps Class Creation needs so a restored cache
                # keeps the PDM range grouping.
                "attribute_category": dict(snapshot.attribute_category),
                "attribute_range": dict(snapshot.attribute_range),
                "value_range": dict(snapshot.value_range),
                "product_range": dict(snapshot.product_range),
            }
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
            )
            return path
        except OSError:
            # Saving is best-effort and must never break a load.
            return None

    @staticmethod
    def _engineering_dict(engineering) -> dict:
        """Serialize the engineering section (families by id + members + vocab).

        Captures the user's reduction workbench output: each engineering family
        (by ``id``), its members' ``reduced_article`` / ``long_description``, the
        per-member property assignments, and the engineering property
        definitions - so the work is persisted per family and can be restored.
        """
        if engineering is None:
            return {"families": [], "properties": []}
        from services.snapshot_serialization import (
            engineering_relationships_to_dict,
        )
        return {
            "families": [
                {
                    "id": family.id,
                    "name": family.name,
                    "members": [
                        {
                            "id": member.id,
                            "article_id": member.article_id,
                            "reduced_article": member.reduced_article,
                            "long_description": member.long_description,
                            "property_values": [
                                {
                                    "property_id": assignment.property_id,
                                    "value": assignment.value,
                                }
                                for assignment in member.property_values
                            ],
                        }
                        for member in family.members
                    ],
                }
                for family in engineering.families
            ],
            "properties": [
                PDMService._scalars(definition)
                for definition in engineering.properties
            ],
            "relationships": engineering_relationships_to_dict(
                engineering.relationships
            ),
        }

    @staticmethod
    def _scalars(obj) -> dict:
        """Serialize a dataclass's scalar (non-list) fields.

        List fields hold object-graph relationships (e.g. Article -> properties)
        that are already represented by the snapshot's separate flat
        collections, so they are skipped to keep the cache compact.
        """
        return {
            f.name: getattr(obj, f.name)
            for f in fields(obj)
            if not isinstance(getattr(obj, f.name), list)
        }

    @staticmethod
    def _sanitize_family_name(name: str) -> str:
        """Turn a family name into a safe lowercase file stem (e.g. 'bolster')."""
        stem = re.sub(r"[^\w\-]+", "_", (name or "family").strip().lower())
        stem = re.sub(r"_+", "_", stem).strip("_")
        return stem or "family"

    # -- product search (on-demand) ---------------------------------------
    def search_products(self, text: str, limit: int = 50) -> list[Product]:
        """Search PDM for products matching code or name (bounded results)."""
        return self._map_search_rows(self.repository.search_products(text, limit))

    def search_products_by_code(self, text: str, limit: int = 50) -> list[Product]:
        """Search PDM for products whose code matches ``text``."""
        return self._map_search_rows(
            self.repository.search_products_by_code(text, limit)
        )

    def search_products_by_name(self, text: str, limit: int = 50) -> list[Product]:
        """Search PDM for products whose name matches ``text``."""
        return self._map_search_rows(
            self.repository.search_products_by_name(text, limit)
        )

    def search_products_by_article(self, text: str, limit: int = 50) -> list[Product]:
        """Search PDM for products that own an article (item) matching ``text``."""
        return self._map_search_rows(
            self.repository.search_products_by_article(text, limit)
        )

    def _map_search_rows(self, rows) -> list[Product]:
        products: list[Product] = []
        for row in rows:
            products.append(
                Product(
                    id=str(row.ProductId),
                    code=(row.ProductCode or "").strip(),
                    name=(row.ProductName or "").strip(),
                    category=(row.ProductCategoryName or "").strip(),
                    description=(row.CatalogueName or "").strip(),
                    catalogue_id=str(row.CatalogueId) if row.CatalogueId is not None else None,
                )
            )
        self._connected = True
        return products

    # -- product load ------------------------------------------------------
    def load_product(self, product: Product) -> ProductLoadResult:
        """Load a selected product's engineering data into the active snapshot.

        Fetches properties/values and options/values from PDM, maps them to
        models, and populates a new active snapshot. Returns a
        :class:`ProductLoadResult` and never raises for expected PDM failures.
        """
        if product is None or not product.id:
            return ProductLoadResult(False, "No valid product was selected.")

        connection = None
        try:
            # One connection reused for all queries (opening a fresh connection
            # per query roughly doubled load time on this server).
            connection = self.repository.get_connection()
            load_data = self._fetch_and_map(product, connection=connection)
            snapshot = self.context.snapshot_manager.create_empty_snapshot(product)
            self._populate_snapshot(snapshot, load_data)
            # Per-article links (BaseAttributeValues + ItemComponents) that the
            # Builder, reduction and config-decode read; empty otherwise.
            self._populate_links(snapshot, connection=connection)
        except PDMError as error:
            return ProductLoadResult(False, str(error))
        finally:
            if connection is not None:
                connection.close()

        # Derived article-set table (property/option structure per group).
        self.context.engineering_reduction_service.materialize_article_sets(snapshot)

        properties = load_data.properties
        property_values = load_data.property_values
        options = load_data.options
        option_values = load_data.option_values
        articles = load_data.articles

        warnings: list[str] = []
        if not properties and not options:
            warnings.append("The selected product returned no properties or options.")

        message = (
            f"Loaded '{product.name}' ({product.code}): "
            f"{len(properties)} properties, {len(property_values)} property values, "
            f"{len(options)} options, {len(option_values)} option values, "
            f"{len(articles)} articles."
        )
        return ProductLoadResult(True, message, snapshot, warnings)

    def _fetch_and_map(
        self, product: Product, connection=None, reporter=None
    ) -> ProductLoadData:
        """Fetch + Map stage: read PDM rows and map them to models.

        Reusable, read-only stage shared by product loading (and, in future,
        family loading). It performs no snapshot creation, no SnapshotManager
        access, no snapshot assignment, and no metadata creation. May raise
        :class:`PDMError` for expected PDM failures.

        When ``connection`` is supplied it is passed to every repository call so
        they reuse one open connection; when omitted each repository call opens
        and closes its own connection (the original per-call behaviour).

        When ``reporter`` is supplied, one progress step is advanced before each
        repository call and a success activity line is logged per data category.
        """
        if reporter is not None:
            reporter.advance("Loading Articles...")
        item_rows = self.repository.fetch_product_items(
            product.id, connection=connection
        )
        if reporter is not None:
            reporter.advance("Loading Properties...")
        attribute_rows = self.repository.fetch_product_attributes(
            product.id, connection=connection
        )
        if reporter is not None:
            reporter.advance("Loading Options...")
        option_rows = self.repository.fetch_product_options(
            product.id, product.catalogue_id, connection=connection
        )
        if reporter is not None:
            reporter.advance("Loading Product Information...")
        info_rows = self.repository.fetch_product_info(
            product.id, connection=connection
        )

        self._apply_product_info(product, info_rows)
        properties, property_values = self._map_attributes(attribute_rows)
        options, option_values = self._map_options(option_rows)
        articles = self._map_articles(item_rows, product.id)

        if reporter is not None:
            reporter.log("success", "\u2713 Product Information")
            reporter.log("success", f"\u2713 Properties ({len(properties)})")
            reporter.log("success", f"\u2713 Options ({len(options)})")
            reporter.log("success", f"\u2713 Articles ({len(articles)})")

        return ProductLoadData(
            product=product,
            properties=properties,
            property_values=property_values,
            options=options,
            option_values=option_values,
            articles=articles,
        )

    def _populate_snapshot(
        self, snapshot: Snapshot, load_data: ProductLoadData
    ) -> None:
        """Snapshot Population stage: assign mapped data and metadata.

        Performs no database access and no repository calls - it only assigns
        the already-mapped collections onto the snapshot and product and builds
        the snapshot metadata.
        """
        product = load_data.product
        snapshot.id = product.id
        snapshot.properties = load_data.properties
        snapshot.property_values = load_data.property_values
        snapshot.options = load_data.options
        snapshot.option_values = load_data.option_values
        snapshot.articles = load_data.articles
        product.options = load_data.options
        product.articles = load_data.articles
        # Product-level attribute assignment (from ProductAttributeValues).
        snapshot.product_property_value_ids = {
            str(product.id): [v.id for v in load_data.property_values if v.id]
        }
        # Product-level option offering (from ProductOptions).
        snapshot.product_option_value_ids = {
            str(product.id): [v.id for v in load_data.option_values if v.id]
        }
        snapshot.metadata = SnapshotMetadata(
            source="PDM",
            product_code=product.code,
            created_at=datetime.now(timezone.utc).isoformat(),
            notes=(
                f"Loaded from PDM {self.context.config.pdm_server}/"
                f"{self.context.config.pdm_database}"
            ),
        )

    def _populate_links(
        self, snapshot: Snapshot, connection=None
    ) -> None:
        """Populate the per-article link maps the snapshot carries.

        Reads PDM ``BaseAttributeValues`` (article -> its attribute value ids +
        the ordered varcond terms) and ``ItemComponents`` (super-product
        sub-items) for every loaded article, in one connection. No-op when there
        are no articles. These maps feed the Builder, reduction and config-decode
        (they are empty otherwise).
        """
        item_ids = [a.id for a in snapshot.articles if getattr(a, "id", None)]
        if not item_ids:
            return
        own = connection is None
        conn = self.repository.get_connection() if own else connection
        try:
            link_rows = self.repository.fetch_item_attribute_values(
                item_ids, connection=conn
            )
            component_rows = self.repository.fetch_item_components(
                item_ids, connection=conn
            )
            prefix_rows, master_rows = self._fetch_prefix_length_rows(
                item_ids, conn
            )
            component_head_attrs = self._fetch_component_head_attrs(
                component_rows, conn
            )
            option_increments = self._fetch_option_increments(
                self._increment_codes(
                    [a.code for a in snapshot.articles], component_rows
                ), conn
            )
        finally:
            if own and conn is not None:
                conn.close()
        snapshot.article_property_value_ids = self._index_item_attribute_values(
            link_rows
        )
        snapshot.article_varcond_terms = self._index_item_varcond_terms(link_rows)
        snapshot.article_components = self._index_item_components(component_rows)
        snapshot.component_head_attrs = component_head_attrs
        snapshot.option_increments = option_increments
        snapshot.article_prefix_length = self._index_article_prefix_lengths(
            prefix_rows, master_rows
        )

    @staticmethod
    def _merge_properties(
        snapshot, properties, seen_props: dict, seen_values: set
    ) -> None:
        """Add each property once (by id), unioning values into the existing one.

        A property with no id is always added (cannot be safely deduped).
        """
        for prop in properties:
            existing = seen_props.get(prop.id) if prop.id else None
            if existing is None:
                if prop.id:
                    seen_props[prop.id] = prop
                snapshot.properties.append(prop)
                new_property = True
            else:
                new_property = False
            target = prop if new_property else existing
            for value in prop.values:
                if value.id and value.id in seen_values:
                    continue
                if value.id:
                    seen_values.add(value.id)
                snapshot.property_values.append(value)
                if not new_property:
                    target.values.append(value)

    @staticmethod
    def _merge_options(
        snapshot, options, seen_options: dict, seen_values: set
    ) -> None:
        """Add each option once (by id), unioning values into the existing one."""
        for option in options:
            existing = seen_options.get(option.id) if option.id else None
            if existing is None:
                if option.id:
                    seen_options[option.id] = option
                snapshot.options.append(option)
                new_option = True
            else:
                new_option = False
            target = option if new_option else existing
            for value in option.values:
                if value.id and value.id in seen_values:
                    continue
                if value.id:
                    seen_values.add(value.id)
                snapshot.option_values.append(value)
                if not new_option:
                    target.values.append(value)

    @staticmethod
    def _index_item_attribute_values(rows) -> dict:
        """Index BaseAttributeValues rows as ItemId -> [AttributeValueId].

        Order-preserving and unique per article (first occurrence wins).
        """
        index: dict[str, list[str]] = {}
        for row in rows:
            key = str(row.ItemId)
            value_id = str(row.AttributeValueId)
            bucket = index.setdefault(key, [])
            if value_id not in bucket:
                bucket.append(value_id)
        return index

    @staticmethod
    def _index_item_varcond_terms(rows) -> dict:
        """Index BaseAttributeValues rows as ItemId -> ordered varcond terms.

        Each term is ``{name, order, has_dependent_options, order_code}`` (the
        ingredients PDM's VarCondThread query needs). One term per attribute
        name (first occurrence wins), sorted by attribute display order.
        """
        by_item: dict[str, dict[str, dict]] = {}
        for row in rows:
            item = str(row.ItemId)
            name = (getattr(row, "AttrName", "") or "")
            seen = by_item.setdefault(item, {})
            if name in seen:
                continue
            seen[name] = {
                "name": name,
                "order": int(row.DisplayOrder)
                if row.DisplayOrder is not None
                else 0,
                "has_dependent_options": int(row.HasDependentOptions)
                if getattr(row, "HasDependentOptions", None) is not None
                else 0,
                "order_code": (getattr(row, "Code", "") or ""),
            }
        return {
            item: sorted(terms.values(), key=lambda t: t["order"])
            for item, terms in by_item.items()
        }

    @staticmethod
    def _index_item_components(rows) -> dict:
        """Index ItemComponents rows as ParentItemId -> ordered sub-items.

        Each sub-item is ``{sub_item, quantity, sequence}`` (quantity defaults to
        1 when null; sequence kept as text).
        """
        index: dict[str, list[dict]] = {}
        for row in rows:
            index.setdefault(str(row.ParentItemId), []).append(
                {
                    "sub_item": row.SubItem,
                    "quantity": int(row.Quantity) if row.Quantity is not None else 1,
                    "sequence": str(row.ComponentSequence),
                }
            )
        return index

    def _fetch_prefix_length_rows(self, item_ids, connection):
        """Raw inputs for the pCon article prefix length: each item's Notes +
        category, plus the category master-item Notes used as the fallback."""
        prefix_rows = self.repository.fetch_article_prefix_lengths(
            item_ids, connection=connection
        )
        category_ids = sorted({
            str(r.ProductCategoryId) for r in prefix_rows
            if getattr(r, "ProductCategoryId", None) is not None
        })
        master_rows = (
            self.repository.fetch_category_master_notes(
                category_ids, connection=connection
            )
            if category_ids else []
        )
        return prefix_rows, master_rows

    @staticmethod
    def _index_article_prefix_lengths(prefix_rows, master_rows) -> dict:
        """Port of PDM ``getArticlePrefixLength`` (+ category master fallback):
        item id -> pCon article prefix length (the super-product VARCOND base
        length used to slice parametric dimension codes out of the article
        number). Item ``Notes`` is comma-split; the last 1-2 char integer token
        is the length. When an item defines none, the category's
        ``CADImage2D='master'`` item ``Notes`` first token (1-2 chars, integer)
        is the fallback (``getPConPrefixLengthByCategory``).
        """
        # Category fallback: master item's FIRST Notes token, 1-2 chars, integer.
        by_category: dict[str, int] = {}
        for row in master_rows:
            notes = (getattr(row, "Notes", "") or "")
            if not notes:
                continue
            token = notes.split(",", 1)[0]
            if len(token) > 2:
                token = ""
            if token.isdigit():
                by_category[str(row.ProductCategoryId)] = int(token)

        out: dict[str, int] = {}
        for row in prefix_rows:
            notes = (getattr(row, "Notes", "") or "")
            num = -1
            for token in notes.split(","):
                if 0 < len(token) < 3 and token.isdigit():
                    num = int(token)   # last matching token wins (PDM loop)
            if num == -1:
                num = by_category.get(
                    str(getattr(row, "ProductCategoryId", "")), 0
                )
            out[str(row.ItemId)] = num if num >= 0 else 0
        return out

    def _fetch_component_head_attrs(self, component_rows, connection) -> dict:
        """Head-attribute names per super-product COMPONENT (its own
        BaseAttributeValues): component code -> the head properties that control
        it. Empty when there are no components."""
        sub_codes = sorted({
            (getattr(r, "SubItem", "") or "").strip()
            for r in component_rows
            if getattr(r, "SubItem", None)
        })
        if not sub_codes:
            return {}
        attr_rows = self.repository.fetch_item_head_attribute_names(
            sub_codes, connection=connection
        )
        return self._index_component_head_attrs(attr_rows)

    @staticmethod
    def _index_component_head_attrs(rows) -> dict:
        """Index (Item code, AttrName) rows as component code -> sorted head
        attribute names (unique)."""
        index: dict[str, set] = {}
        for row in rows:
            name = (getattr(row, "AttrName", "") or "").strip()
            if name:
                index.setdefault(str(row.Item), set()).add(name)
        return {code: sorted(names) for code, names in index.items()}

    @staticmethod
    def _item_prefix(item) -> str:
        """Item name up to and including the first ``.`` (the option-increment
        grouping key; matches VarCondService)."""
        item = (item or "").strip()
        dot = item.find(".")
        return item[: dot + 1] if dot > -1 else item

    @staticmethod
    def _increment_codes(article_codes, component_rows) -> set:
        """Item codes to fetch option increments for: the articles plus any
        super-product component sub-items."""
        codes = {(c or "").strip() for c in article_codes if c}
        for row in component_rows:
            sub = (getattr(row, "SubItem", "") or "").strip()
            if sub:
                codes.add(sub)
        return codes

    def _fetch_option_increments(self, codes, connection) -> dict:
        """Option increment prices (PDM ``ItemOptionValues``) indexed by item
        prefix, for the given item codes. Empty when there are no codes."""
        prefixes = sorted({self._item_prefix(c) for c in codes if c})
        if not prefixes:
            return {}
        rows = self.repository.fetch_item_option_increments(
            prefixes, connection=connection
        )
        return self._index_option_increments(rows)

    @staticmethod
    def _index_option_increments(rows) -> dict:
        """Index option-increment rows as item prefix -> option-value rows
        ``{item, option_id, option_name, value_name, code, increment}``."""
        index: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            item = str(getattr(row, "Item", "") or "")
            if not item:
                continue
            dot = item.find(".")
            prefix = item[: dot + 1] if dot > -1 else item
            inc = getattr(row, "IncrementalPrice", None)
            index[prefix].append({
                "item": item,
                "option_id": int(row.OptionId) if row.OptionId is not None else None,
                "option_name": (getattr(row, "OptionName", "") or ""),
                "value_name": (getattr(row, "ValueName", "") or ""),
                "code": (getattr(row, "Code", "") or ""),
                "increment": float(inc) if inc is not None else None,
            })
        return dict(index)

    # -- family load -------------------------------------------------------
    def load_family(
        self, products: list[Product], family_name: str = "", reporter=None
    ) -> ProductLoadResult:
        """Load a whole family in one call (articles, then details).

        Thin wrapper over the two-phase load - :meth:`load_family_articles`
        then :meth:`load_family_details` - so batch/headless callers get the
        complete snapshot from a single call, while the UI can run the phases
        separately (fast articles first, details in the background).
        """
        result = self.load_family_articles(products, family_name, reporter=reporter)
        if not result.ok or result.snapshot is None:
            return result
        return self.load_family_details(
            result.snapshot, products, family_name, reporter=reporter
        )

    def set_excluded_ranges(self, snapshot: Snapshot | None, ranges) -> int:
        """Set the COMPLETE list of excluded ProductRanges and re-derive the
        snapshot to match.

        Excluded ranges (components / accessories / hardware) are held aside in a
        live baseline rather than deleted, so unticking a range restores it with
        no reload. Rebuilds the article-set table and engineering so every
        workspace shows only what remains. Returns the number of articles now
        excluded. The baseline is in-memory only: a project save fixes the
        current exclusion.
        """
        if snapshot is None:
            return 0
        wanted = {r for r in (ranges or []) if r}
        self._capture_exclusion_baseline(snapshot)
        self._restore_exclusion_baseline(snapshot)
        total = len(snapshot.articles)
        if wanted:
            self._prune_to_kept(snapshot, wanted)
        snapshot.ignored_ranges = sorted(wanted)
        self.context.engineering_reduction_service.materialize_article_sets(snapshot)
        self.context.engineering_class_service.commit_config_codes(snapshot)
        self.context.engineering_initialization_service.initialize(snapshot)
        self.context.snapshot_manager.mark_modified()
        return total - len(snapshot.articles)

    def _capture_exclusion_baseline(self, snapshot: Snapshot) -> None:
        """Capture the full pre-exclusion collections once (object references),
        so an excluded range can be restored without a reload."""
        if getattr(snapshot, "exclusion_baseline", None) is not None:
            return
        snapshot.exclusion_baseline = {
            "articles": list(snapshot.articles),
            "properties": list(snapshot.properties),
            "prop_values": {str(p.id): list(p.values) for p in snapshot.properties},
            "property_values": list(snapshot.property_values),
            "options": list(snapshot.options),
            "opt_values": {str(o.id): list(o.values) for o in snapshot.options},
            "option_values": list(snapshot.option_values),
            "product_property_value_ids": dict(snapshot.product_property_value_ids),
            "product_option_value_ids": dict(snapshot.product_option_value_ids),
            "product_range": dict(snapshot.product_range),
            "article_property_value_ids": dict(snapshot.article_property_value_ids),
            "article_varcond_terms": dict(snapshot.article_varcond_terms),
            "article_components": dict(snapshot.article_components),
            "article_prefix_length": dict(snapshot.article_prefix_length),
            "attribute_range": dict(snapshot.attribute_range),
            "value_range": dict(snapshot.value_range),
        }

    def _restore_exclusion_baseline(self, snapshot: Snapshot) -> None:
        """Reset the working collections to the captured full load."""
        base = getattr(snapshot, "exclusion_baseline", None)
        if not base:
            return
        snapshot.articles = list(base["articles"])
        snapshot.properties = list(base["properties"])
        for prop in snapshot.properties:
            prop.values = list(base["prop_values"].get(str(prop.id), []))
        snapshot.property_values = list(base["property_values"])
        snapshot.options = list(base["options"])
        for opt in snapshot.options:
            opt.values = list(base["opt_values"].get(str(opt.id), []))
        snapshot.option_values = list(base["option_values"])
        snapshot.product_property_value_ids = dict(base["product_property_value_ids"])
        snapshot.product_option_value_ids = dict(base["product_option_value_ids"])
        snapshot.product_range = dict(base["product_range"])
        snapshot.article_property_value_ids = dict(base["article_property_value_ids"])
        snapshot.article_varcond_terms = dict(base["article_varcond_terms"])
        snapshot.article_components = dict(base["article_components"])
        snapshot.article_prefix_length = dict(base["article_prefix_length"])
        snapshot.attribute_range = dict(base["attribute_range"])
        snapshot.value_range = dict(base["value_range"])

    def _prune_to_kept(self, snapshot: Snapshot, excluded: set) -> None:
        """Drop the excluded ProductRanges from the working collections."""
        pr = snapshot.product_range or {}
        kept_products = {pid for pid, rng in pr.items() if rng not in excluded}
        snapshot.articles = [
            a for a in snapshot.articles
            if str(getattr(a, "product_id", "") or "") in kept_products
        ]
        kept_article_ids = {str(a.id) for a in snapshot.articles if a.id is not None}

        kept_value_ids: set[str] = set()
        for pid in kept_products:
            kept_value_ids.update(snapshot.product_property_value_ids.get(pid, []))
        snapshot.property_values = [
            v for v in snapshot.property_values if str(v.id) in kept_value_ids
        ]
        kept_props = []
        for prop in snapshot.properties:
            prop.values = [v for v in prop.values if str(v.id) in kept_value_ids]
            if prop.values:
                kept_props.append(prop)
        snapshot.properties = kept_props

        kept_opt_value_ids: set[str] = set()
        for pid in kept_products:
            kept_opt_value_ids.update(snapshot.product_option_value_ids.get(pid, []))
        snapshot.option_values = [
            v for v in snapshot.option_values if str(v.id) in kept_opt_value_ids
        ]
        kept_opts = []
        for opt in snapshot.options:
            opt.values = [v for v in opt.values if str(v.id) in kept_opt_value_ids]
            if opt.values:
                kept_opts.append(opt)
        snapshot.options = kept_opts

        snapshot.product_property_value_ids = {
            pid: v for pid, v in snapshot.product_property_value_ids.items()
            if pid in kept_products
        }
        snapshot.product_option_value_ids = {
            pid: v for pid, v in snapshot.product_option_value_ids.items()
            if pid in kept_products
        }
        snapshot.product_range = {
            pid: rng for pid, rng in pr.items() if pid in kept_products
        }
        snapshot.article_property_value_ids = {
            aid: v for aid, v in snapshot.article_property_value_ids.items()
            if aid in kept_article_ids
        }
        snapshot.article_varcond_terms = {
            aid: v for aid, v in snapshot.article_varcond_terms.items()
            if aid in kept_article_ids
        }
        snapshot.article_components = {
            aid: v for aid, v in snapshot.article_components.items()
            if aid in kept_article_ids
        }
        snapshot.article_prefix_length = {
            aid: v for aid, v in snapshot.article_prefix_length.items()
            if aid in kept_article_ids
        }
        prop_ids = {str(p.id) for p in snapshot.properties}
        snapshot.attribute_range = {
            k: v for k, v in snapshot.attribute_range.items() if k in prop_ids
        }
        val_ids = {str(v.id) for v in snapshot.property_values}
        snapshot.value_range = {
            k: v for k, v in snapshot.value_range.items() if k in val_ids
        }

    def load_family_articles(
        self, products: list[Product], family_name: str = "", reporter=None
    ) -> ProductLoadResult:
        """Phase 1: load just the family's ARTICLES into a new snapshot.

        Fetches items (+ product info) only - the fast subset that lets the
        Articles workflow open immediately - and returns the snapshot. The
        remaining details (properties, options, per-article links, article
        sets) are loaded by :meth:`load_family_details`.
        """
        if not products:
            return ProductLoadResult(False, "No products in the selected family.")

        first_product = products[0]
        snapshot = self.context.snapshot_manager.create_empty_snapshot(first_product)
        snapshot.id = first_product.id

        connection = None
        try:
            if reporter is not None:
                reporter.advance("Connecting to PDM...")
                reporter.log("info", "Connecting to PDM...")
            connection = self.repository.get_connection()
            if reporter is not None:
                reporter.log("success", "Connection established")
            product_ids = [p.id for p in products if p.id]
            if reporter is not None:
                reporter.advance("Loading Articles...")
            item_rows = self.repository.fetch_products_items(
                product_ids, connection=connection
            )
            if reporter is not None:
                reporter.log("success", f"\u2713 Articles ({len(item_rows)} rows)")
                reporter.advance("Loading Product Information...")
            info_rows = self.repository.fetch_products_info(
                product_ids, connection=connection
            )
        except PDMError as error:
            return ProductLoadResult(False, str(error))
        finally:
            if connection is not None:
                connection.close()

        items_by: dict[str, list] = defaultdict(list)
        for row in item_rows:
            items_by[str(row.ProductId)].append(row)
        info_by = {str(row.ProductId): row for row in info_rows}

        for product in products:
            pid = str(product.id)
            if reporter is not None:
                reporter.set_product(product.code)
            self._apply_product_info(
                product, [info_by[pid]] if pid in info_by else []
            )
            articles = self._map_articles(items_by.get(pid, []), product.id)
            snapshot.articles.extend(articles)
            product.articles = articles

        # Register the family's products so pages resolve product NAMES (not
        # numbers) from an article's product_id (e.g. Articles Long Text).
        self.context.set_product_registry(products)

        snapshot.metadata = SnapshotMetadata(
            source="PDM",
            product_code=family_name,
            created_at=datetime.now(timezone.utc).isoformat(),
            notes=(
                f"Loaded family '{family_name}' from PDM "
                f"{self.context.config.pdm_server}/{self.context.config.pdm_database}"
            ),
        )
        if reporter is not None:
            reporter.set_counts(
                len(products), len(products), len(snapshot.articles), 0, 0, 0, 0, 0
            )
        message = (
            f"Loaded {len(snapshot.articles)} article(s) for family "
            f"'{family_name}' ({len(products)} product(s))."
        )
        return ProductLoadResult(True, message, snapshot, [])

    def load_family_details(
        self, snapshot: Snapshot | None, products: list[Product],
        family_name: str = "", reporter=None
    ) -> ProductLoadResult:
        """Phase 2: load the family DETAILS onto an articles-only snapshot.

        Fetches properties, options and the per-article links, merges them into
        ``snapshot`` (property/option collections are built locally and assigned
        atomically so a live UI reading the snapshot is never mid-mutation),
        materialises the article-set table and saves the family cache. Safe to
        run on a background worker while the Articles workflow is already open.
        """
        if snapshot is None or not products:
            return ProductLoadResult(False, "No snapshot to complete.")

        product_ids = [p.id for p in products if p.id]
        catalogue_by_product = {
            p.id: getattr(p, "catalogue_id", None) for p in products if p.id
        }
        item_ids = [str(a.id) for a in snapshot.articles if getattr(a, "id", None)]

        connection = None
        try:
            if reporter is not None:
                reporter.advance("Loading Properties...")
            connection = self.repository.get_connection()
            attribute_rows = self.repository.fetch_products_attributes(
                product_ids, connection=connection
            )
            if reporter is not None:
                reporter.log("success", f"\u2713 Properties ({len(attribute_rows)} rows)")
                reporter.advance("Loading Options...")
            option_rows = self.repository.fetch_products_options(
                product_ids,
                catalogue_by_product=catalogue_by_product or None,
                connection=connection,
            )
            if reporter is not None:
                reporter.log("success", f"\u2713 Options ({len(option_rows)} rows)")
                reporter.advance(f"Loading Article Links ({len(item_ids)} articles)...")
            link_rows = self.repository.fetch_item_attribute_values(
                item_ids, connection=connection
            )
            component_rows = self.repository.fetch_item_components(
                item_ids, connection=connection
            )
            prefix_rows, master_rows = self._fetch_prefix_length_rows(
                item_ids, connection
            )
            component_head_attrs = self._fetch_component_head_attrs(
                component_rows, connection
            )
            option_increments = self._fetch_option_increments(
                self._increment_codes(
                    [a.code for a in snapshot.articles], component_rows
                ), connection
            )
            # Product-level ProductRange name per product; drives Class Creation
            # functional grouping (desk / screen / wire management).
            product_range: dict[str, str] = {}
            try:
                for r in self.repository.fetch_products_info(
                    product_ids, connection=connection
                ):
                    product_range[str(r.ProductId)] = (
                        getattr(r, "RangeName", "") or ""
                    ).strip()
            except Exception:
                product_range = {}
            # Option-value dependency edges (DependentOptionValues): a parent
            # option value -> the option values it makes valid. Drives the
            # fabric/finish value combination tables. Best-effort.
            option_deps: dict[str, set] = defaultdict(set)
            try:
                for r in self.repository.fetch_products_option_dependencies(
                    product_ids, connection=connection
                ):
                    src = str(r.OptionValueId)
                    dst = str(r.AdditionalOptionValueId)
                    if src and dst:
                        option_deps[src].add(dst)
            except Exception:
                option_deps = defaultdict(set)
            if reporter is not None:
                reporter.log("success", f"\u2713 Article Links ({len(link_rows)} rows)")
        except PDMError as error:
            return ProductLoadResult(False, str(error))
        finally:
            if connection is not None:
                connection.close()

        attrs_by: dict[str, list] = defaultdict(list)
        for row in attribute_rows:
            attrs_by[str(row.ProductId)].append(row)
        opts_by: dict[str, list] = defaultdict(list)
        for row in option_rows:
            opts_by[str(row.ProductId)].append(row)

        # Build the unioned collections locally, then assign them onto the
        # snapshot in one shot (atomic for a live reader).
        if reporter is not None:
            reporter.advance("Merging snapshot...")
        acc = _SnapshotAccumulator()
        seen_props: dict[str, Property] = {}
        seen_prop_values: set[str] = set()
        seen_options: dict[str, Option] = {}
        seen_option_values: set[str] = set()
        for product in products:
            pid = str(product.id)
            properties, _pv = self._map_attributes(attrs_by.get(pid, []))
            options, _ov = self._map_options(opts_by.get(pid, []))
            self._merge_properties(acc, properties, seen_props, seen_prop_values)
            self._merge_options(acc, options, seen_options, seen_option_values)
            product.options = options
        # Values display in DisplayOrdinal order (DPS parity); the cross-product
        # union can append values out of order, so sort each property's values.
        for prop in acc.properties:
            prop.values.sort(
                key=lambda v: (v.display_order is None, v.display_order or 0)
            )
        for option in acc.options:
            option.values.sort(
                key=lambda v: (v.display_order is None, v.display_order or 0)
            )
        snapshot.properties = acc.properties
        snapshot.property_values = acc.property_values
        snapshot.options = acc.options
        snapshot.option_values = acc.option_values

        # Attribute functional group = its ProductCategory name; Class Creation
        # groups by this when a load spans categories (Nevi / Screens / Wire
        # Management), else stays flat.
        snapshot.attribute_category = {
            str(r.AttributeId): (r.AttrCategory or "").strip()
            for r in attribute_rows
            if getattr(r, "AttrCategory", None)
        }

        # Per-article links across the whole family (article -> its value ids,
        # varcond terms, and super-product sub-items).
        snapshot.article_property_value_ids = self._index_item_attribute_values(
            link_rows
        )
        snapshot.article_varcond_terms = self._index_item_varcond_terms(link_rows)
        snapshot.article_components = self._index_item_components(component_rows)
        snapshot.component_head_attrs = component_head_attrs
        snapshot.option_increments = option_increments
        snapshot.article_prefix_length = self._index_article_prefix_lengths(
            prefix_rows, master_rows
        )
        # Product-level attribute assignment (always populated from
        # ProductAttributeValues, unlike the sometimes-sparse per-article link).
        snapshot.product_property_value_ids = {
            pid: [str(r.AttributeValueId) for r in rows
                  if r.AttributeValueId is not None]
            for pid, rows in attrs_by.items()
        }
        # Property functional group = the ProductRange(s) of the products that
        # carry it (property id -> sorted range names). Class Creation groups by
        # this when a load spans ranges (desk / screen / wire management); shared
        # properties list under every range that carries them.
        value_to_prop: dict[str, str] = {}
        for prop in acc.properties:
            for v in prop.values:
                if v.id is not None:
                    value_to_prop[str(v.id)] = str(prop.id)
        prop_ranges: dict[str, set] = defaultdict(set)
        value_ranges: dict[str, set] = defaultdict(set)
        for pid, value_ids in snapshot.product_property_value_ids.items():
            rng = product_range.get(pid, "")
            if not rng:
                continue
            for vid in value_ids:
                prop_id = value_to_prop.get(vid)
                if prop_id:
                    prop_ranges[prop_id].add(rng)
                    value_ranges[vid].add(rng)
        snapshot.attribute_range = {k: sorted(v) for k, v in prop_ranges.items()}
        snapshot.value_range = {k: sorted(v) for k, v in value_ranges.items()}
        snapshot.product_range = dict(product_range)
        # Fabric/finish dependency edges (DependentOptionValues): parent option
        # value -> allowed dependent option values. Feeds the finish combination
        # tables so a fabric/finish change regenerates them.
        snapshot.option_option_dependencies = {
            k: sorted(v) for k, v in option_deps.items()
        }
        # Product-level option offering (from ProductOptions).
        snapshot.product_option_value_ids = {
            pid: [str(r.OptionValueId) for r in rows
                  if r.OptionValueId is not None]
            for pid, rows in opts_by.items()
        }
        if reporter is not None:
            reporter.set_counts(
                len(products), len(products), len(snapshot.articles),
                len(snapshot.properties), len(snapshot.property_values),
                len(snapshot.options), len(snapshot.option_values),
                sum(len(v) for v in snapshot.article_property_value_ids.values()),
            )

        # Derived article-set table (property/option structure per group),
        # materialised before the auto-save so it persists with the snapshot.
        if reporter is not None:
            reporter.advance("Building Article Sets...")
        self.context.engineering_reduction_service.materialize_article_sets(snapshot)

        # Capture the head-property filter as the stored value->code relation so
        # slicing/relations read a persisted map (survives save/load).
        self.context.engineering_class_service.commit_config_codes(snapshot)

        # Auto-save the completed family snapshot (source data only) to
        # cache/pdm_snapshots/<family>.json; best-effort so a save failure never
        # affects the load.
        if reporter is not None:
            reporter.log("success", f"\u2713 Article Sets ({len(snapshot.article_sets)})")
            reporter.advance("Saving Snapshot...")
        self.save_family_snapshot(snapshot, family_name)

        message = (
            f"Loaded family '{family_name}': {len(products)} product(s), "
            f"{len(snapshot.properties)} properties, "
            f"{len(snapshot.property_values)} property values, "
            f"{len(snapshot.options)} options, "
            f"{len(snapshot.option_values)} option values, "
            f"{len(snapshot.articles)} articles."
        )
        return ProductLoadResult(True, message, snapshot, [])

    def add_family_to_session(
        self, products: list[Product], family_name: str = "", reporter=None
    ) -> ProductLoadResult:
        """Load a family and MERGE it into the CURRENT session's snapshot.

        Unlike :meth:`load_family` (which starts a fresh snapshot), this unions
        the family's articles/properties/options and per-article links into the
        active snapshot, then re-materialises the article-set table across every
        family now in the session - so a session can hold several families and
        re-group across all of them. With no active snapshot it falls back to a
        fresh :meth:`load_family`.
        """
        if not products:
            return ProductLoadResult(False, "No products in the selected family.")
        snapshot = self.context.active_snapshot
        if snapshot is None:
            return self.load_family(products, family_name, reporter=reporter)

        product_ids = [p.id for p in products if p.id]
        catalogue_by_product = {
            p.id: getattr(p, "catalogue_id", None) for p in products if p.id
        }
        connection = None
        try:
            if reporter is not None:
                reporter.advance("Connecting to PDM...")
            connection = self.repository.get_connection()
            if reporter is not None:
                reporter.advance("Loading Articles...")
            item_rows = self.repository.fetch_products_items(
                product_ids, connection=connection
            )
            if reporter is not None:
                reporter.advance("Loading Product Information...")
            info_rows = self.repository.fetch_products_info(
                product_ids, connection=connection
            )
            if reporter is not None:
                reporter.advance("Loading Properties...")
            attribute_rows = self.repository.fetch_products_attributes(
                product_ids, connection=connection
            )
            if reporter is not None:
                reporter.advance("Loading Options...")
            option_rows = self.repository.fetch_products_options(
                product_ids,
                catalogue_by_product=catalogue_by_product or None,
                connection=connection,
            )
            item_ids = [row.ItemId for row in item_rows if row.ItemId is not None]
            if reporter is not None:
                reporter.advance(f"Loading Article Links ({len(item_ids)} articles)...")
            link_rows = self.repository.fetch_item_attribute_values(
                item_ids, connection=connection
            )
            component_rows = self.repository.fetch_item_components(
                item_ids, connection=connection
            )
            prefix_rows, master_rows = self._fetch_prefix_length_rows(
                item_ids, connection
            )
            component_head_attrs = self._fetch_component_head_attrs(
                component_rows, connection
            )
            option_increments = self._fetch_option_increments(
                self._increment_codes(
                    [row.Item for row in item_rows], component_rows
                ), connection
            )
        except PDMError as error:
            return ProductLoadResult(False, str(error))
        finally:
            if connection is not None:
                connection.close()

        attrs_by: dict[str, list] = defaultdict(list)
        for row in attribute_rows:
            attrs_by[str(row.ProductId)].append(row)
        opts_by: dict[str, list] = defaultdict(list)
        for row in option_rows:
            opts_by[str(row.ProductId)].append(row)
        items_by: dict[str, list] = defaultdict(list)
        for row in item_rows:
            items_by[str(row.ProductId)].append(row)
        info_by = {str(row.ProductId): row for row in info_rows}

        # Seed the dedup sets from the EXISTING snapshot so shared properties/
        # options/values are unioned (added once), not duplicated.
        seen_props: dict[str, Property] = {p.id: p for p in snapshot.properties if p.id}
        seen_prop_values: set[str] = {v.id for v in snapshot.property_values if v.id}
        seen_options: dict[str, Option] = {o.id: o for o in snapshot.options if o.id}
        seen_option_values: set[str] = {
            v.id for v in snapshot.option_values if v.id
        }

        if reporter is not None:
            reporter.advance("Merging snapshot...")
        for product in products:
            pid = str(product.id)
            self._apply_product_info(
                product, [info_by[pid]] if pid in info_by else []
            )
            properties, _pv = self._map_attributes(attrs_by.get(pid, []))
            options, _ov = self._map_options(opts_by.get(pid, []))
            articles = self._map_articles(items_by.get(pid, []), product.id)
            snapshot.articles.extend(articles)
            self._merge_properties(
                snapshot, properties, seen_props, seen_prop_values
            )
            self._merge_options(
                snapshot, options, seen_options, seen_option_values
            )
            product.options = options
            product.articles = articles
        for prop in snapshot.properties:
            prop.values.sort(
                key=lambda v: (v.display_order is None, v.display_order or 0)
            )
        for option in snapshot.options:
            option.values.sort(
                key=lambda v: (v.display_order is None, v.display_order or 0)
            )

        # Register the added family's products so pages resolve product NAMES.
        self.context.set_product_registry(products)

        # Extend the per-article/product link maps with the new family's keys.
        snapshot.article_property_value_ids.update(
            self._index_item_attribute_values(link_rows)
        )
        snapshot.article_varcond_terms.update(
            self._index_item_varcond_terms(link_rows)
        )
        snapshot.article_components.update(
            self._index_item_components(component_rows)
        )
        snapshot.component_head_attrs.update(component_head_attrs)
        snapshot.option_increments.update(option_increments)
        snapshot.article_prefix_length.update(
            self._index_article_prefix_lengths(prefix_rows, master_rows)
        )
        snapshot.product_property_value_ids.update({
            pid: [str(r.AttributeValueId) for r in rows
                  if r.AttributeValueId is not None]
            for pid, rows in attrs_by.items()
        })
        snapshot.product_option_value_ids.update({
            pid: [str(r.OptionValueId) for r in rows
                  if r.OptionValueId is not None]
            for pid, rows in opts_by.items()
        })

        # Re-materialise the article-set table across ALL families in the session.
        if reporter is not None:
            reporter.advance("Building Article Sets...")
        self.context.engineering_reduction_service.materialize_article_sets(snapshot)
        if reporter is not None:
            reporter.advance("Saving Snapshot...")
        self.save_family_snapshot(
            snapshot, snapshot.metadata.product_code or family_name
        )

        message = (
            f"Added family '{family_name}': the session now holds "
            f"{len(snapshot.articles)} articles, "
            f"{len(snapshot.properties)} properties and "
            f"{len(snapshot.article_sets)} article set(s)."
        )
        return ProductLoadResult(True, message, snapshot, [])

    # -- mapping helpers ---------------------------------------------------
    _STATUS_TEXT = {1: "Active", 2: "Obsolete", 3: "Hold"}

    @staticmethod
    def _status_text(code) -> str:
        try:
            return PDMService._STATUS_TEXT.get(int(code), "Unreleased")
        except (TypeError, ValueError):
            return "Unknown"

    @staticmethod
    def _attribute_value_code(row) -> str:
        """DPS-parity config code for an attribute value.

        DPS ``BOM_Manager.LoadLists``: the stored ``OrderCodeValue`` is the code
        for parametric values; when it is NULL the code is the ``paravalue`` -
        the ``ProductMaskValue`` substring before ``'|'`` (e.g. ``'1055|mm'`` ->
        ``'1055'``). Pure functional/identity values have neither and stay
        code-less (their code lives in the base article number).
        """
        code = (row.Code or "").strip() if row.Code else ""
        if not code:
            mask = getattr(row, "MaskValue", None)
            if mask and "|" in mask:
                code = mask.split("|", 1)[0].strip()
        return code

    @staticmethod
    def _code_width(has_dependent_options) -> int:
        """The raw PDM ``HasDependentOptions`` flag stored on the property.

        Drives the configuration code width (2 -> 2 chars, 1 -> 1 char); 0 is an
        identity attribute and a negative value is not-applicable. The effective
        width for a 0 flag also depends on the value count (resolved at decode
        time), so the raw flag is kept here.
        """
        try:
            return int(has_dependent_options)
        except (TypeError, ValueError):
            return 0

    def _apply_product_info(self, product: Product, info_rows) -> None:
        """Populate descriptive metadata on the product from PDM (if present)."""
        if not info_rows:
            return
        info = info_rows[0]
        product.range_name = (info.RangeName or "").strip()
        product.status = self._status_text(info.Status)
        product.is_super_product = bool(info.IsSuperProduct)
        product.new_product = bool(info.NewProduct)
        if not product.name:
            product.name = (info.ProductName or "").strip()

    def _map_attributes(self, rows) -> tuple[list[Property], list[PropertyValue]]:
        """Group attribute rows into properties keyed by AttributeId."""
        properties: list[Property] = []
        property_values: list[PropertyValue] = []
        by_id: dict[str, Property] = {}

        for row in rows:
            key = str(row.AttributeId) if row.AttributeId is not None else (row.Property or "").strip()
            prop = by_id.get(key)
            if prop is None:
                prop = Property(
                    id=str(row.AttributeId) if row.AttributeId is not None else None,
                    code=(row.PropertyKey or "").strip() if row.PropertyKey else "",
                    name=(row.Property or "").strip(),
                    display_order=int(row.DisplayOrder) if row.DisplayOrder is not None else None,
                    attribute_type=int(row.AttributeType) if row.AttributeType is not None else None,
                    has_dependent_options=bool(row.HasDependentOptions),
                    code_width=self._code_width(row.HasDependentOptions),
                )
                by_id[key] = prop
                properties.append(prop)

            value = PropertyValue(
                id=str(row.AttributeValueId) if row.AttributeValueId is not None else None,
                property_id=prop.id,
                value=(row.Value or "").strip(),
                code=self._attribute_value_code(row),
                model_suffix=(row.ModelSuffix or "").strip() if row.ModelSuffix else "",
                display_order=int(row.ValueDisplayOrder)
                if getattr(row, "ValueDisplayOrder", None) is not None else None,
            )
            prop.values.append(value)
            property_values.append(value)

        return properties, property_values

    def _map_options(self, rows) -> tuple[list[Option], list[OptionValue]]:
        """Group option rows into options keyed by OptionId."""
        options: list[Option] = []
        option_values: list[OptionValue] = []
        by_id: dict[str, Option] = {}

        for row in rows:
            key = str(row.OptionId) if row.OptionId is not None else (row.Property or "").strip()
            option = by_id.get(key)
            if option is None:
                option = Option(
                    id=str(row.OptionId) if row.OptionId is not None else None,
                    code=(row.OptionKey or "").strip() if row.OptionKey else "",
                    name=(row.Property or "").strip(),
                    display_order=int(row.OptionDisplayOrder) if row.OptionDisplayOrder is not None else None,
                    is_fabric=bool(row.IsFabric),
                )
                by_id[key] = option
                options.append(option)

            value = OptionValue(
                id=str(row.OptionValueId) if row.OptionValueId is not None else None,
                option_id=option.id,
                value=(row.Value or "").strip(),
                code=(row.Code or "").strip() if row.Code else "",
                supplier_code=(row.SupplierCode or "").strip() if row.SupplierCode else "",
                display_order=int(row.OptionValueDisplayOrdinal)
                if getattr(row, "OptionValueDisplayOrdinal", None) is not None else None,
            )
            option.values.append(value)
            option_values.append(value)

        return options, option_values

    def _map_articles(self, rows, product_id) -> list[Article]:
        """Map Item rows into Article models (real fields only)."""
        articles: list[Article] = []
        for row in rows:
            code = (row.Item or "").strip()
            description = (getattr(row, "Description", None) or "").strip()
            articles.append(
                Article(
                    id=str(row.ItemId) if row.ItemId is not None else None,
                    product_id=product_id,
                    code=code,
                    name=description or code,
                    description=description,
                    status=self._status_text(row.Status),
                    source="PDM",
                    notes=(row.Notes or "").strip() if row.Notes else "",
                    is_super_item=bool(row.IsSuperItem),
                    weight_kg=float(row.WeightKilos) if row.WeightKilos is not None else None,
                    volume_l=float(row.VolumeLitres) if row.VolumeLitres is not None else None,
                    height=int(row.Height) if row.Height is not None else None,
                    width=int(row.Width) if row.Width is not None else None,
                    depth=int(row.Depth) if row.Depth is not None else None,
                )
            )
        return articles
