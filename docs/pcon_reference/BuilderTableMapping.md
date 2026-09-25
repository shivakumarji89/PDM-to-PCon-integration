# Builder Table Mapping Matrix

**Cross-refs:** [OCDTables](./OCDTables.md) · [GeneratorArchitecture](./GeneratorArchitecture.md) · [VariantConditions](./VariantConditions.md) · [PriceGeneration](./PriceGeneration.md)

Mapping from each **Builder Table engineering model** → its **source PDM tables** → the
**destination OCD tables** → the **generator stage** that consumes it.

| Builder Table Model | Source PDM Tables | Destination OCD Tables | Generator Stage |
|---|---|---|---|
| `product_attributes` | `Attribute`, `AttributeValue`, `ProductAttributeValues` | `tCOMd_Property`, `tCOMd_PropValue` | Package Builder |
| `product_options` | `Option`, `OptionValue`, `ProductOptionValues`, `CatalogueOptionValues` | `tCOMd_Property`, `tCOMd_PropValue` | Package Builder (+ `Code` → Variant Generator) |
| `product_configuration_features` | `LayoutFeatures`, `LayoutFeatureValues` | `Relationships` / Class structure | Package Builder (configuration) |
| `product_child_configurations` | `ItemComponents` (→ `Item`/`Product`) | Child `tCOMd_Article` + Relationships | Package Builder (child articles) |
| `product_configuration_graph` | `ItemComponents` (product-level) | Relationships (parent/child) | Package Builder |
| `product_dependencies` | `DependentOptionValues`, `DependentAttributeValues`, `AttributeValueExclusions` | (drives valid combinations) | Variant Condition Generator |
| `product_option_exclusion_rules` | `CatalogueProductOptionExclusions`, `CatalogueItemOptionExclusions` | (drives excluded combinations) | Variant Condition Generator |
| `product_engineering_metadata` | `Product`, `ProductRange` (`OrderCodeFormatString`, `ProductMaskKey`, `ModelList`, `ProductCodeId`, `IsSuperProduct`) | `tCOMd_Article`, `tCOMd_ArtBase` | Article/ArtBase Generator + Variant Generator |
| Article identity | `Product.Product` | `tCOMd_Article.com_ArticleCode` | Package Builder |
| Localized text | `OtherDescription` / names | `tCOMd_Text` | Package Builder (display) |
| **Pricing (item-level, NOT in Builder Table)** | `Item.BasePrice*`, `ItemOptionValues`, `PriceFormula`, `PriceMatrix` | `tCOMd_Price`, `tCOMd_PriceList2` | Price Generator |
| **Variant conditions (generated, NOT in Builder Table)** | derived from order codes | `tCOMd_Price.com_VariantCondition` | Variant Condition Generator |

## Reading the Matrix

- Rows above the pricing/variant separators are **product-centric engineering models** — already in the
  snapshot, consumed directly by the generator with no PDM re-query.
- The last two rows are **generation-time / item-level** — intentionally excluded from the Builder
  Table (see [PriceGeneration.md](./PriceGeneration.md), [VariantConditions.md](./VariantConditions.md)).

## Coverage Check for Generation Targets

| Target | Data available in Builder Table? | Gap |
|---|---|---|
| Metatype | Yes (attributes, options, dependencies, config, order-code metadata) | none |
| GO | Yes (child configurations, feature positions, order-code metadata) | generation logic only (`go_children`/`go_childprops`) |
| PCon package (structure) | Yes | none |
| PCon pricing | Item-level (read at generation) | not a Builder Table gap |
| CAD | No | CAD metadata not exposed (`CADAlias`, `CADPlaceProgram`, `CADSuffix`, `CADMaterial`, `LayerNameList`) — add only if CAD is in scope |
