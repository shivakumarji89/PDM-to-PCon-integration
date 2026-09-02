# Relationship Matrix

**Cross-refs:** [ERDiagram](./ERDiagram.md) · [DependencyGraph](./DependencyGraph.md) · [WriteOrder](./WriteOrder.md)

| Parent Table | Child Table | Relationship Field | Type | Generation Stage | Consumer | Example |
|---|---|---|---|---|---|---|
| `tCOMd_ComGroup` | `tCOMd_Package` | `com_ComGroupID` | 1→N (required) | Package Builder | `get_or_create_package` | ComGroup "SEATING" → Package "seating" |
| `tCOMd_DistributionRegion` | `tCOMd_Package` | `com_DistributionRegionID` | 1→N (required) | Package Builder | `get_or_create_package` | Region 5 → Package |
| `tCOMd_OfmlType` | `tCOMd_Article` | `com_OfmlTypeID` | 1→N (required) | Article Builder | `resolve_ofml_type_id` | OfmlType → Article NOALE191 |
| `tCOMd_Package` | `tCOMd_Article` | `com_PackageID` | 1→N (required) | Article Builder | `get_or_create_article` | Package → Article |
| `tCOMd_Text` | `tCOMd_Article` | `com_ShortTextID` | 1→N (optional) | Text/Article | `get_or_create_text` | Text "NOALE191" → Article |
| `tCOMd_Text` | `tCOMd_Class` | `com_TextID` | 1→N (optional) | Class Builder | `get_or_create_class` | Text → Class label |
| `tCOMd_Text` | `tCOMd_Property` | `com_TextID` | 1→N (optional) | Property Builder | `get_or_create_property` | Text → Property label |
| `tCOMd_Text` | `tCOMd_PropValue` | `com_TextID` | 1→N (optional) | PropValue Builder | `get_or_create_prop_value` | Text → Value label |
| `tCOMd_Article` | `tCOMd_ArticleClass` | `com_ArticleID` | N↔N (required) | Class link | `get_or_create_article_class` | Article ↔ Class |
| `tCOMd_Class` | `tCOMd_ArticleClass` | `com_ClassID` | N↔N (required) | Class link | `get_or_create_article_class` | Article ↔ Class |
| `tCOMd_Article` | `tCOMd_ArtBase` | `com_ArticleID` | 1→N (required) | ArtBase Builder | `get_or_create_art_base` | Article → base config |
| `tCOMd_Property` | `tCOMd_PropValue` | `com_PropertyID` | 1→N (required) | PropValue Builder | `get_or_create_prop_value` | Property "Fabric" → Value "Red" |
| `tCOMd_Article` | `tCOMd_Price` | `com_ArticleID` | 1→N (optional) | Price Generator | (item-level) | Article → Price |
| `tCOMd_PriceList2` | `tCOMd_Price` | `com_PriceListID` | 1→N (optional) | Price Generator | (item-level) | PriceList "EUR2019" → Price |

## Relationship Type Legend

- **1→N (required):** child cannot exist without the parent; parent is written first.
- **1→N (optional):** child references parent only when a label/price applies (Text, Price).
- **N↔N:** join table (`tCOMd_ArticleClass`) linking two independently-created parents.

## Stage Grouping

- **Structural (Package Builder):** ComGroup, DistributionRegion, OfmlType, Package, Text, Class,
  Property, PropValue, Article, ArticleClass, ArtBase.
- **Item-level (Price Generator):** PriceList2, Price — see [../PriceGeneration.md](../PriceGeneration.md).
