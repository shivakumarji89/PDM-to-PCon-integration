"""Snapshot domain model.

The Snapshot is the single source of truth for all engineering data held in
memory. It owns the product object graph plus flat collections that act as
convenient indexes into the same objects, and carries descriptive metadata.
Fields and relationships only - no logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.enums import SnapshotStatus
from models.article import Article
from models.article_set import ArticleSet
from models.engineering import Engineering
from models.option import Option
from models.option_value import OptionValue
from models.price_list import PriceList
from models.price_record import PriceRecord
from models.product import Product
from models.product_profile import ProductProfile
from models.property import Property
from models.property_value import PropertyValue
from models.relation_object import RelationObject
from models.text_block import TextBlock
from models.value_table import ValueCombinationTable


@dataclass
class SnapshotMetadata:
    """Descriptive metadata for a snapshot. Placeholder fields only."""

    source: str = ""
    product_code: str = ""
    created_at: str | None = None
    created_by: str = ""
    notes: str = ""


@dataclass
class Snapshot:
    """The application's in-memory working document.

    Holds two kinds of data:
      * **Source Data** loaded from PDM - the product object graph plus the flat
        ``articles`` / ``properties`` / ``property_values`` / ``options`` /
        ``option_values`` collections and descriptive ``metadata``.
      * **Engineering Data** created by the application, under ``engineering``.

    Fields and relationships only - no logic.
    """

    id: str | None = None
    status: SnapshotStatus = SnapshotStatus.NOT_CREATED

    # Root of the engineering object graph.
    product: Product | None = None

    # Flat collections - authoritative indexes into the object graph.
    articles: list[Article] = field(default_factory=list)
    properties: list[Property] = field(default_factory=list)
    property_values: list[PropertyValue] = field(default_factory=list)
    options: list[Option] = field(default_factory=list)
    option_values: list[OptionValue] = field(default_factory=list)

    # Source link from PDM ``BaseAttributeValues``: article/ItemId -> the
    # PropertyValue/AttributeValueIds that specific article actually carries.
    article_property_value_ids: dict[str, list[str]] = field(default_factory=dict)

    # Source link from PDM ``ProductAttributeValues``: product id -> the
    # AttributeValueIds assigned to that product (the product-level config,
    # always populated even when the per-article link is sparse).
    product_property_value_ids: dict[str, list[str]] = field(default_factory=dict)

    # Source link from PDM ``ProductOptions``: product id -> the OptionValueIds
    # offered by that product (the product-level option config).
    product_option_value_ids: dict[str, list[str]] = field(default_factory=dict)

    # Super-product BOM from PDM ``ItemComponents``: article/ItemId -> the
    # sub-items it is composed of, each ``{sub_item, quantity, sequence}``.
    article_components: dict[str, list[dict]] = field(default_factory=dict)

    # Per-component controlling head properties (PDM ``BaseAttributeValues`` of
    # the sub-item itself): component code -> the head-attribute NAMES that
    # actually control it. A super component is priced/conditioned only by its
    # own head properties, not the parent super item's full set.
    component_head_attrs: dict[str, list[str]] = field(default_factory=dict)

    # VARCOND source rows (PDM ``BaseAttributeValues`` joined to Attribute):
    # article/ItemId -> ordered attribute rows used to build the pCon condition,
    # each ``{name, order, has_dependent_options, order_code}``. Carries every
    # ingredient PDM's ``VarCondThread`` query needs so generation runs offline.
    article_varcond_terms: dict[str, list[dict]] = field(default_factory=dict)

    # pCon article prefix length (PDM ``getArticlePrefixLength``): article/ItemId
    # -> the fixed-prefix character count, used to slice parametric dimension
    # codes (Width/Height/Depth) out of the article number, exactly as PDM does.
    article_prefix_length: dict[str, int] = field(default_factory=dict)

    # Authoritative base-length overrides applied when standardising an existing
    # series: article CODE -> base length (from the base-length registry: the
    # user override, else CAD Maintenance). Empty by default (no effect); when
    # populated it wins over the reduction/PDM length in the base article split.
    base_length_overrides: dict[str, int] = field(default_factory=dict)

    # Repository-derived implemented base relationships for existing-series work.
    # member article CODE -> base article CODE. Empty for new series.
    base_article_overrides: dict[str, str] = field(default_factory=dict)

    # Option increment prices (PDM ``ItemOptionValues.IncrementalPrice``): item
    # prefix (name up to and including the first ``.``) -> option-value rows,
    # each ``{item, option_id, option_name, value_name, code, increment}``. Feeds
    # the VARCOND price-suffix lines and the pricing report, offline.
    option_increments: dict[str, list[dict]] = field(default_factory=dict)

    # DPS AttributeValueExclusions: attribute value id -> excluded value ids
    # (symmetric); a combination pairing an excluded value is invalid.
    attribute_value_exclusions: dict[str, list[str]] = field(default_factory=dict)

    # DPS dependency edges: a selected value additionally ENABLES option values.
    # attribute value id -> option value ids (DependentAttributeValues).
    attribute_option_dependencies: dict[str, list[str]] = field(default_factory=dict)
    # option value id -> option value ids (DependentOptionValues).
    option_option_dependencies: dict[str, list[str]] = field(default_factory=dict)

    metadata: SnapshotMetadata = field(default_factory=SnapshotMetadata)

    # Derived article-set table (property/option structure per article group).
    # Materialised from the product links above; feeds relation creation.
    article_sets: list[ArticleSet] = field(default_factory=list)

    # OCD text blocks (tCOMd_Text): authored by the Text workflow.
    text_blocks: list[TextBlock] = field(default_factory=list)

    # OCD relation objects (tCOMd_RelObj/Relation): authored by the Relation workflow.
    relation_objects: list[RelationObject] = field(default_factory=list)

    # OCD price records (tCOMd_Price / tCOMd_GlobalPrice): computed by the Pricing
    # workflow from PDM's fnGetListPrice* functions. The persisted price baseline;
    # a later run diffs against these to emit only the changed cells.
    price_records: list[PriceRecord] = field(default_factory=list)

    # OCD price lists (tCOMd_PriceList): named lists (id, label, currency,
    # validity window) the price rows reference. Chained by date so a new list
    # closes the previous one's window (roll-over). Persisted with the project.
    price_lists: list[PriceList] = field(default_factory=list)

    # OCD value combination tables (<name>_tbl.csv) + their TABLE() constraints,
    # derived from the article set (property config) and the option dependency
    # graph (fabric/finish). Persisted with the project; regenerated on demand.
    value_tables: list[ValueCombinationTable] = field(default_factory=list)

    # OCD article base table (ArtBase): base master -> {property/option id ->
    # allowed value ids}, where the base allows only a subset of the entity's
    # values. Derived per base article; a value confined to certain bases lives
    # here instead of a $BAN precondition. Persisted with the project.
    art_base: dict[str, dict[str, list[str]]] = field(default_factory=dict)

    # User-clarified config value codes the automation could not resolve
    # unambiguously: property id -> {value id -> code}. Persisted with the
    # project and applied on top of the automatic decode (the user's answer wins).
    config_code_overrides: dict[str, dict[str, str]] = field(default_factory=dict)

    # Stored config value codes = the head-property filter relation captured like
    # PDM: property id -> {value id -> code}. Committed from the automatic decode
    # so slicing and article relations read a persisted map. Overrides still win.
    config_value_codes: dict[str, dict[str, str]] = field(default_factory=dict)

    # User decision on which head properties to slice: property id -> ignore?
    # (True = keep in base / metatype, False = force slice). Absent uses the
    # automatic suggestion (redundant duplicates ignored). Persisted; user wins.
    config_ignore_overrides: dict[str, bool] = field(default_factory=dict)

    # User opt-in: split the standard classes into one <Group>_* set per product
    # range (desk / screen / wire management) instead of one flat <Category>_*
    # set. Off by default (flat, historical behaviour). Persisted with the project.
    split_classes_by_group: bool = False

    # How the split groups are formed when the split is on: 'range' (one group per
    # PDM ProductRange, default) or 'article_set' (one group per article set /
    # base article). Persisted with the project.
    class_group_basis: str = "range"

    # User rename/merge of the split groups: raw ProductRange name -> the group
    # name to show it under. Several ranges mapped to the same name MERGE into one
    # group (e.g. two screen ranges -> 'Screen'). Absent = the raw range name.
    class_group_names: dict[str, str] = field(default_factory=dict)

    # Attribute functional group = its ProductCategory name (Attribute.
    # ProductCategoryId): attribute/property id -> category (e.g. 'Nevi',
    # 'Screens Components', 'Wire Management'). Class Creation groups properties
    # by this when a load spans categories; a single-category load stays flat.
    attribute_category: dict[str, str] = field(default_factory=dict)

    # Property functional group = the ProductRange name(s) of the products that
    # carry it: property id -> sorted range names (e.g. ['Nevi Desks'],
    # ['Wire Management']). Class Creation groups by this when a load spans
    # ranges (desk / screen / wire management); shared properties list under
    # every range that carries them. Persisted with the project.
    attribute_range: dict[str, list[str]] = field(default_factory=dict)

    # Value functional group = the ProductRange name(s) of the products that
    # carry that specific value: value id -> sorted range names. Under a range
    # group Class Creation shows only the values that range's products carry, so
    # a property listed in several ranges shows the right values in each.
    value_range: dict[str, list[str]] = field(default_factory=dict)

    # Product -> its ProductRange name. Drives the Articles "Filter Components"
    # picker (range list + per-range article counts) and lets the user scope the
    # load to the main product's range(s).
    product_range: dict[str, str] = field(default_factory=dict)

    # ProductRange names the user chose to ignore (components / accessories /
    # hardware). Class Creation drops properties/values belonging only to these,
    # so it builds classes for the main product alone. Persisted with the project.
    ignored_ranges: list[str] = field(default_factory=list)

    # Held "exclusion table": a live, in-memory copy of the full pre-exclusion
    # collections (object references, not deep copies) captured the first time a
    # range is excluded, so unticking a range restores it with no PDM reload.
    # Runtime only - never serialized; a project save fixes the current exclusion.
    exclusion_baseline: dict | None = field(default=None, repr=False, compare=False)

    # Detected structural traits (workflow classifier); persisted with the project.
    product_profile: ProductProfile = field(default_factory=ProductProfile)

    # Engineering section (Phase 2 root container; empty until future phases).
    engineering: Engineering = field(default_factory=Engineering)
