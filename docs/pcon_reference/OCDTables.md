# OCD Tables (`tCOMd_*`)

**Cross-refs:** [PackagingPipeline](./PackagingPipeline.md) · [Relationships](./Relationships.md) · [BuilderTableMapping](./BuilderTableMapping.md)

The OCD commercial database (`pcr_data_com_ocd.mdb`) holds all `tCOMd_*` tables — the authoritative
engineering model that PCon consumes. Field names use the `com_` prefix. Names/fields below are
grounded in `services/mdb_service.py`, `services/pdm_to_mdb_service.py`, `PDMMaintenance/MDBQuery.cs`,
and `services/article_service.py`.

| Table | Purpose | Primary key | Relationships | Source Builder Table model | Consumer services | Stage | Layer |
|---|---|---|---|---|---|---|---|
| `tCOMd_ComGroup` | Top-level commercial group (brand/program container) | `com_ComGroupID` | parent of Package | category name (skeleton) | `PDMToMDBService`, `MDBService` | 4–6 | Packaging |
| `tCOMd_Package` | Program/series package under a ComGroup | `com_PackageID` | → ComGroup; parent of Article | category name (skeleton) | `PDMToMDBService`, `MDBService` | 4–6 | Packaging |
| `tCOMd_Class` | Property/article classes (metatype behaviour grouping) | `com_ClassID` | parent of ArticleClass; referenced by Property | property class (from PDM option/attribute grouping) | `get_class_names`, `create_handbook_base` | 4–6 | Packaging (source = engineering class) |
| `tCOMd_Article` | Articles (article codes) | `com_ArticleID` | → Package; → ArticleClass, ArtBase, Price, Text | `product_engineering_metadata` + article identity (`Product.Product`) | `get_article_property_summary`, `create_handbook_base` | 4–6 | Packaging (id) / Engineering (code) |
| `tCOMd_ArticleClass` | Article ↔ Class link | (`com_ArticleID`,`com_ClassID`) | join Article↔Class | derived | `create_handbook_base` | 4–6 | Packaging |
| `tCOMd_ArtBase` | Article base / base configuration (series base) | `com_ArtBaseID` | → Article | `product_engineering_metadata` (base/model) | `create_handbook_base` | 4–6 | Packaging |
| `tCOMd_Property` | Properties | `com_PropertyID` | parent of PropValue; referenced by ArticleClass/Article | `product_attributes` (Attribute) and `product_options` (Option name) | `get_property_definitions`, `create_handbook_base` | 4–6 | Engineering source |
| `tCOMd_PropValue` | Property values | `com_PropValueID` | → Property | `product_attributes`/`product_options` values | `get_article_property_summary` | 4–6 | Engineering source |
| `tCOMd_Text` | Localized text (labels/descriptions) | `com_TextID` | referenced by Article/Property/Value | display text (`com_Text_1_en`, `com_TextName`) | `article_service.load_articles`, `get_article_property_summary` | 4–6 | Packaging (display) |
| `tCOMd_Price` | Article/option prices | `com_PriceID` | → Article; → PriceList; carries `com_VariantCondition`, `com_PriceValue` | **item-level** (`Item.BasePrice`, `ItemOptionValues.IncrementalPrice`) | `MDBQuery` (`PDMMaintenance`) | Price stage | PCon Generator (item-level) |
| `tCOMd_PriceList2` | Price lists | `com_PriceListID` | → Price | price list metadata | `MDBQuery` | Price stage | PCon Generator |

## Notes on Classification

- **Engineering source tables** (`tCOMd_Property`, `tCOMd_PropValue`) are *populated from* the
  Builder Table engineering model but the row objects themselves are packaging artifacts.
- **Packaging tables** (`tCOMd_ComGroup`, `tCOMd_Package`, `tCOMd_ArticleClass`, `tCOMd_ArtBase`,
  `tCOMd_Text`) exist purely to structure the OCD package.
- **Item-level tables** (`tCOMd_Price`, `tCOMd_PriceList2`) are produced at generation time from
  per-item PDM pricing — see [PriceGeneration.md](./PriceGeneration.md).

## ID / Creation Flow

`generate_initial_tables` assigns IDs top-down: `ComGroupID` → `PackageID` → Article/Class/Property/
PropValue/ArtBase. The write is delegated to `mdb_helper` (32-bit). See [PackagingPipeline.md](./PackagingPipeline.md).
