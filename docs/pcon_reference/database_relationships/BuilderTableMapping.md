# Builder Table → `tCOMd_*` Mapping

**Cross-refs:** [ServiceMapping](./ServiceMapping.md) · [../BuilderTableMapping.md](../BuilderTableMapping.md) · [ValidationRules](./ValidationRules.md)

For each Builder Table engineering model: destination table(s), transformation, responsible generator,
and validation method.

| Builder Table Model | Destination `tCOMd_*` | Transformation | Generator Responsible | Validation Method |
|---|---|---|---|---|
| `product_engineering_metadata` + article identity (`Product.Product`) | `tCOMd_Article` (+ `tCOMd_ArtBase`) | article code → `com_ArticleCode`; order-code/model fields → base config | Article/ArtBase Builder | article code non-empty; unique per package |
| Localized names | `tCOMd_Text` | property/value/article label → `com_TextName` / `com_Text_1_en` | Text Builder (get_or_create) | text type resolvable; label non-empty |
| `product_attributes` (Attribute/Value) | `tCOMd_Property` + `tCOMd_PropValue` | property name → Property; each value → PropValue under it | Property/PropValue Builder | property exists before value; value code normalized |
| `product_options` (Option/Value) | `tCOMd_Property` + `tCOMd_PropValue` | option name → Property; option value → PropValue; `Code` retained for pricing/variant | Property/PropValue Builder | catalogue-scoped; H2 option set |
| Property class grouping | `tCOMd_Class` + `tCOMd_ArticleClass` | class name → Class; article↔class → ArticleClass | Class Builder | class exists; both endpoints present |
| `product_configuration_features` | `tCOMd_Class` / Relationships | layout feature/value → class/relationship structure | Configuration Builder | prefix scope matches product |
| `product_child_configurations` / `product_configuration_graph` | child `tCOMd_Article` + Relationships | parent→child product → child article + `contains` | Configuration Builder | child article resolvable |
| `product_dependencies` | (drives variant conditions) | dependency edges → valid option combinations | Variant Condition Generator | edge endpoints exist in option set |
| `product_option_exclusion_rules` | (drives variant conditions) | CPOE/CIOE → excluded combinations | Variant Condition Generator | exclusion targets exist |
| Item pricing (NOT in Builder Table) | `tCOMd_Price` + `tCOMd_PriceList2` | `Item.BasePrice*` / `ItemOptionValues` → price rows keyed by article + variant + list | Price Generator | article/list exist; item enumeration here only |

## Transformation Notes

- **Article code = `Product.Product`** (identity), threaded into `com_ArticleCode`.
- **Property vs Option:** both land in `tCOMd_Property`/`tCOMd_PropValue`; the payload `source`
  (`attribute` | `option`) distinguishes them and drives the `contains` relationship type.
- **Order codes** (`product_options[*].Code`) are retained through the payload for the Variant
  Condition Generator and Price Generator; they are not needed to build the structural Property/Value.
- **Configurations** map to Class/Relationship structure, not to new Property definitions.

## Validation Hook Points

- Pre-write: `OCDPayloadValidationService` (payload rows).
- Write-time: `get_or_create_*` natural-key lookups prevent duplicates.
- Post-write: `WorkspaceSnapshotBuilder` read-back conflict check.
