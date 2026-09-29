# Relationship Matrix

**Cross-refs:** [ERDiagram](./ERDiagram.md) · [DependencyGraph](./DependencyGraph.md) · [WriteOrder](./WriteOrder.md)

For the full parent/child/FK-field/cardinality facts, see [ERDiagram.md](./ERDiagram.md) (canonical
for this subtree). This file cross-references those same 9 relationships against **Generation
Stage**, **Consumer** (the code path that materializes the relationship), and a concrete **Example**
— columns not present in ERDiagram.md.

| Relationship (see [ERDiagram.md](./ERDiagram.md)) | Generation Stage | Consumer | Example |
|---|---|---|---|
| ComGroup → Package | Package Builder | `get_or_create_package` | ComGroup "SEATING" → Package "seating" |
| DistributionRegion → Package | Package Builder | `get_or_create_package` | Region 5 → Package |
| OfmlType → Article | Article Builder | `resolve_ofml_type_id` | OfmlType → Article NOALE191 |
| Package → Article | Article Builder | `get_or_create_article` | Package → Article |
| Text → Article (`com_ShortTextID`) | Text/Article | `get_or_create_text` | Text "NOALE191" → Article |
| Text → Class | Class Builder | `get_or_create_class` | Text → Class label |
| Text → Property | Property Builder | `get_or_create_property` | Text → Property label |
| Text → PropValue | PropValue Builder | `get_or_create_prop_value` | Text → Value label |
| Article ↔ Class (via ArticleClass) | Class link | `get_or_create_article_class` | Article ↔ Class |
| Article → ArtBase | ArtBase Builder | `get_or_create_art_base` | Article → base config |
| Property → PropValue | PropValue Builder | `get_or_create_prop_value` | Property "Fabric" → Value "Red" |
| Article → Price | Price Generator | (item-level) | Article → Price |
| PriceList2 → Price | Price Generator | (item-level) | PriceList "EUR2019" → Price |

## Stage Grouping

- **Structural (Package Builder):** ComGroup, DistributionRegion, OfmlType, Package, Text, Class,
  Property, PropValue, Article, ArticleClass, ArtBase.
- **Item-level (Price Generator):** PriceList2, Price — see [../PriceGeneration.md](../PriceGeneration.md).
