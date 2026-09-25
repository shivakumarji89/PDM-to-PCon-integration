# 02 — PDM Data Model
**Status:** Analysis of the existing implementation; unverified items marked `UNKNOWN`.

## Purpose

This document describes the **PDM source side** of the PDM↔MDB/OCD compatibility
layer: how the existing services read engineering data out of the PDM SQL Server
database and reshape it into the payload/explorer structures that must eventually
map onto OCD `tCOMd_*` objects. The **destination side** (MDB/OCD table objects,
the actual `tCOMd_*` mapping) is covered in the sibling documents and is out of
scope here.

Every claim below cites the file and function it was read from. Items that could
not be proven from the source are marked `UNKNOWN`.

---

## Master service table

| Service | Method | Return Type | Data Structure (fields / keys) | Dependencies | Current Usage |
|---|---|---|---|---|---|
| `PDMService` (`services/pdm_service.py`) | `get_products_for_category(product_category_id, catalogue_id=None, product_search_text=None)` | `list` of pyodbc rows | Columns `ProductId, Name, Product, ProductRangeId[, NewProduct]` | pyodbc connection (SQL Server) | Root product selection for `build_product_payload` / pipeline (`scripts/run_workspace_pipeline.py`) |
| `PDMService` | `get_product_attributes_bulk(product_ids)` | `list` of pyodbc rows | `ProductId, Property, Value, AttributeValueId, Code(OrderCodeValue), ModelSuffix` | pyodbc | Feeds `build_product_attributes_cache`; snapshot Phase 1 |
| `PDMService` | `get_product_options(product_id)` / `get_product_options_bulk(...)` | `list` of pyodbc rows | `Property, Value, Code(OrderCodeValue), OptionValueId` | pyodbc | Option data for snapshot |
| `PDMService` | `get_option_values_by_ids`, `get_catalogue_product_categories`, `get_catalogues`, `get_fabric_options` | `list` rows | Row shapes `UNKNOWN` beyond call sites | pyodbc | Category-name resolution, filters |
| `PDMSnapshotService` (`services/pdm_snapshot_service.py`) | `build_snapshot(products, pdm_service, product_category_id=None)` | `dict` | `products, product_ids, product_by_id, product_range_ids, product_attributes, product_options, option_value_details_by_id, option_value_products, attribute_ids, table_cache` | `PDMService`, `ThreadPoolExecutor` (parallel bulk fetch) | `build_attribute_rows(..., include_options=True)`; full pipeline |
| `PDMFilterBuilderService` (`services/pdm_filter_builder_service.py`) | `build_product_attributes_cache(bulk_attribute_rows)` | `dict[product_id → list]` | Each value: tuples `(Property, Value, AttributeValueId, Code, ModelSuffix)` (cols 1–5 of the bulk row) | none (pure) | `build_attribute_rows` (non-option path) |
| `PDMFilterBuilderService` | `build_selected_attribute_rows(products, product_attributes, resolve, option_value_details, option_value_products, clean_code)` | `tuple(attribute_value_id_set, selected_rows)` | `selected_rows` = the `AttributeValues` rows (see payload shape below) | `PDMArticleCodeService.resolve_attribute_value_code`, `clean_code` | Produces `attribute_rows` consumed by `generate_payload_service.build_payload` |
| `PDMArticleCodeService` (`services/pdm_article_code_service.py`) | `resolve_attribute_value_code(prop, val, order_code, model_suffix, article_number, ...)` | `str` (value code) | derived article/order code string | pure string logic | Called per attribute row in `build_selected_attribute_rows` |
| `PDMPrefixRuleService` (`services/pdm_prefix_rule_service.py`) | `filter_products`, `group_products_by_base_code`, `build_product_table_rows`, `matches_prefix_rule` | `list` / `dict` / `bool` | prefix/wildcard grouping helpers | pure | Product-code filtering (UI/filter flows) |
| `PDMFilterService` (`services/pdm_filter_service.py`) | `read_filter_settings`, `build_catalogue_filter`, `filter_products`, `build_filter_state`, `build_apply_payload` | `dict` / `list` | filter-state dicts (exact keys `UNKNOWN`) | settings store | Catalogue/attribute filtering |
| `PDMContext` (`services/pdm_context_service.py`) | `set_catalogue/category/series/product/item`, `to_filter_dict()`, `most_specific()` | `QObject` state / `dict` | `ContextRef(kind, id, label)`; `to_filter_dict` → id-list filter dict | Qt (`QObject`) | Tracks current selection; UNKNOWN if used inside payload build |
| `PDMContextScopeService` (`services/pdm_context_scope_service.py`) | `list_catalogues/categories/series/products/items`, `resolve_scope(...)` | `List[ContextRef]` / `ScopeResult` / `EngineeringScopeBundle` | `ScopeResult`, `EngineeringScopeBundle` dataclasses | `PDMSchemaService` | Navigation/scope resolution (context-driven) |
| `PDMSchemaService` (`services/pdm_schema_service.py`) | `list_tables`, `get_columns`, `get_primary_key`, `get_foreign_keys`, `get_table_schema`, `get_tables_metadata` | `List` / `TableSchema` / `dict` | `ColumnInfo`, `ForeignKeyInfo`, `IndexInfo`, `TableSchema` | pyodbc | Live schema introspection of PDM DB |
| `PDMKnowledgeService` (`services/pdm_knowledge_service.py`) | `hierarchy`, `business_paths`, `dependency_paths`, `all_paths`, `paths_from`, `navigation_chains` | `List[str]` / `List[BusinessPath]` | static model from `constants/` | none (static) | Documented navigation/business knowledge, not live data |
| `PDMToMDBService` (`services/pdm_to_mdb_service.py`) | `build_com_group(category_name)` | `dict` | `ComGroupCode` (upper), `ComGroupLabel` | none (pure) | Payload skeleton (called `build_product_payload` ~line 276) |
| `PDMToMDBService` | `build_package(category_name, com_group_id)` | `dict` | `ProgramCode` (lower), `ProgramLabel`, `ComGroupID`, `DistributionRegionID=5`, `MaterialMF="hmx"`, `MaterialPK="basics"` | none (pure) | Payload skeleton |
| `GeneratePayloadService` (`services/generate_payload_service.py`) | `build_payload(ocd_payload_service, pdm_to_mdb_service, com_group, package, attribute_rows, products, article_codes, article_rows, mode)` | `dict` or `None` | Payload (see shape below); adds `OptionValues` + `Relationships` | `OCDPayloadService`, `PDMToMDBService` | The engineering payload aggregator |
| `GlobalProductRegistryService` (`services/global_product_registry_service.py`) | `build_registry()` | `List[ProductRegistryEntry]` | see ProductRegistryEntry | `PDMService`, `REGISTRY_QUERY` | Builds identity-only global registry |
| `GlobalProductRegistryService` | `save_registry`, `load_registry`, `validate_registry` | disk I/O / status | JSON persistence (`REGISTRY_SCHEMA_VERSION = 1`) | filesystem | Cache the registry to `cache/global_product_registry.json` |
| `GlobalProductSearchService` (`services/global_product_search_service.py`) | `search(query, limit)`, `ensure_loaded`, `reload` | `List[SearchResult]` / `List[ProductRegistryEntry]` | search rows are generic `SearchResult` | `GlobalProductRegistryService`, `GlobalSearchEngine` | In-memory product search (no SQL at query time) |
| Aggregator (`scripts/run_workspace_pipeline.py`) | `build_product_payload(category_id, catalogue_id, category_name, plan, limit)` | `tuple(payload, products, category_name, services)` | `payload` = `Articles / AttributeValues / OptionValues / Relationships` (+ `ComGroup`, `Package`) | all PDM services + `GeneratePayloadService` | **Single shared engineering assembly** for import-preview and Product Explorer |
| `AppController` (`ui/controllers/app_controller.py`) | `build_product_explorer(...)` → `_build_explorer_model(payload, products, category_name, catalogue_id)` | `dict` | `summary, articles, properties, property_values, options, option_values, configuration, article_properties, article_options` | `build_product_payload` (pure reshape) | Feeds the read-only Product Explorer dashboard |

---

## PDM engineering payload shape

Source: `build_product_payload` (`scripts/run_workspace_pipeline.py`) →
`GeneratePayloadService.build_payload` (`services/generate_payload_service.py`).
The returned `payload` dict is what must map onto OCD `tCOMd_*` objects.

- **`ComGroup`** — from `PDMToMDBService.build_com_group`: `{ ComGroupCode, ComGroupLabel }`.
- **`Package`** — from `build_package`: `{ ProgramCode, ProgramLabel, ComGroupID, DistributionRegionID, MaterialMF, MaterialPK }`.
- **`Articles`** — list of `{ article_code, article_name }` (assembled from `products` / `article_rows`).
- **`AttributeValues`** — the workhorse rows (from `build_selected_attribute_rows`). Keys referenced downstream (`add_relationships`, `add_option_values`, `_build_explorer_model`):
  `source` (`"attribute"` | `"option"`), `property`, `value`, `name`, `order_code`, `description`, `article_numbers` (comma-joined article codes), `class_name` (present as a read key but not observed being populated — `UNKNOWN`).
- **`OptionValues`** — added by `add_option_values`, projected from option-source `AttributeValues`: `{ option_name, value_name, value_code, display_order, description, parent_option, relationships:[{type:"Option", name}] }`.
- **`Relationships`** — added by `add_relationships`, `contains` edges over existing objects only: `{ source_type, source_name, target_type, target_name, relationship_type:"contains", metadata }`. Edge chain: `ComGroup→Package→Article→Property/Option→Value`.

### Explorer view-model shape

Source: `_build_explorer_model` (`ui/controllers/app_controller.py`). Pure reshape
of the payload above (no SQL/I/O). Returns:

- **`summary`** — `catalogue, category, product, description, article_count, property_count, property_value_count, option_count, option_value_count, relationship_count`.
- **`articles`** — `{ code, description, property_count, option_count, status:"Active" }`.
- **`properties`** — `{ property, property_class, data_type ("List"/"Single"), value_count, used_by_articles }`.
- **`options`** — `{ option, option_type, value_count, used_by_articles }`.
- **`property_values[name]`** — `{ value, order_code, description, related_articles }`.
- **`option_values[name]`** — `{ value, order_code, description, display_order, related_articles }`.
- **`configuration`** — `{ package, articles:[{ code, description, properties[], options[] }] }`.
- **`article_properties` / `article_options`** — `{ article_code → sorted[name] }`.

---

## ProductRegistryEntry

Source: `models/product_registry_entry.py` (frozen dataclass) built from
`GlobalProductRegistryService.REGISTRY_QUERY`. **Identity/label fields only** — the
class docstring states it deliberately carries *no attributes, options, properties
or snapshot engineering data*:

`product_id, product_name, product_code, catalogue_id, catalogue_name, lead_time,
product_category_id, product_category_name`.

The same `product_id` may appear in multiple entries (one per catalogue). This is
the correct identity anchor for cross-referencing engineering data to a product,
but it supplies **none** of the engineering payload itself.

---

## PDM-side data shapes (core / models)

- `core/article.py` `Article` — GO-schema holder: `article_code, article_nr, prm_key, chprm_key, short_text, property_count, selected, metatype_id, status, is_new, requested_properties, requested_property_values`. (Note: distinct from the payload `Articles` dict rows.)
- `models/property.py` `Property` (re-exported by `core/property.py`) — `property_id, property_name, display_name` only.
- `core/schema_model.py` — workspace/MDB schema holders (`TableSchema`, `DatabaseSchema`, `WorkspaceSchema`, `ForeignKeySchema`); these describe the **MDB destination** structure, not PDM engineering content.

---

## Gaps for engineering

Fields/coverage OCD/ODB may need that the PDM source side does **not** currently provide:

- **Geometry / 3D / CAD data** — no geometry, dimensions, mounting or 2D/3D reference is produced anywhere in the payload or snapshot. `UNKNOWN` / **gap**.
- **Property classes** — `class_name` is read in `_build_explorer_model` and surfaces as `property_class`, but no analyzed service was observed populating it on the `AttributeValues` rows; effective value appears empty. `UNKNOWN` / likely **gap**.
- **Option / OptionValue completeness** — `OptionValues` is a *projection* of option-source `AttributeValues` (`add_option_values`); full option metadata (e.g. pricing links, dependency rules from `DependentOptionValues`/`ItemOptionValues` fetched into `snapshot.table_cache`) is not exposed in the payload. Coverage vs OCD requirements `UNKNOWN`.
- **Relationships semantics** — only a single `relationship_type:"contains"` is emitted; richer OCD relation types (constraints, prices, dependencies) are not modelled. `UNKNOWN` / **gap**.
- **Pricing** — `get_pricing_tables` / fabric pricing exist on `PDMService` but are not wired into `build_product_payload`; whether OCD needs price objects here is `UNKNOWN`.
- **Direct `tCOMd_*` mapping** — no analyzed PDM-side service names or targets an OCD `tCOMd_*` object; the destination mapping lives outside this source side. `UNKNOWN` here by design.
