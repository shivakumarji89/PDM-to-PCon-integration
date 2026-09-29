# Summary

**Cross-refs:** [README](./README.md) · [Architecture](./Architecture.md) · [GeneratorArchitecture](./GeneratorArchitecture.md) · [BuilderTableMapping](./BuilderTableMapping.md)

Executive summary of the PCon packaging subsystem and the roadmap for the future generator.

## Engineering Models (product-centric, in the Builder Table snapshot)

| Model | Snapshot key | Purpose |
|---|---|---|
| Properties/Values | `product_attributes` | Product configured attributes → `tCOMd_Property`/`PropValue` |
| Options/Values | `product_options` | Selectable options (PDM `OptionSelector` parity) + order codes |
| Configuration features | `product_configuration_features` | LayoutFeatures/Values scoped by product prefix |
| Child configurations | `product_child_configurations` | Product-level parent/child (from `ItemComponents`) |
| Configuration graph | `product_configuration_graph` | Parent→child edges |
| Dependencies | `product_dependencies` | Option/attribute dependencies + attribute exclusions |
| Exclusion rules | `product_option_exclusion_rules` | CPOE/CIOE |
| Engineering metadata | `product_engineering_metadata` | Order-code/model/business-rule fields |
| Hierarchy | catalogues/categories/products | Selection scope |

## Packaging Models (generator-only, not in the Builder Table)

- `ComGroup`/`Package` skeleton + constants (`DistributionRegionID=5`, `MaterialMF="hmx"`, `MaterialPK="basics"`).
- `tCOMd_*` object/ID creation and `contains` relationship edges.
- `tCOMd_Text` localized text packaging.
- MDB write mechanics (`mdb_helper`, 32-bit Access driver).

## Generator-Only Logic

- Payload assembly extensions (`add_option_values`, `add_relationships`).
- Article/ArtBase construction from order-code metadata.
- Variant condition composition from order codes.
- Price rounding/derivation via `PriceFormula`/`PriceMatrix`.

## Item-Level Logic (enumerate Items only here)

- Pricing (`Item.BasePrice*`, `ItemOptionValues.IncrementalPrice*`).
- Per-item variant pricing conditions.
- Rationale: base price varies per item for ~18% of multi-item products; incremental price varies per
  item for ~24% of sampled option groups — see [PriceGeneration.md](./PriceGeneration.md).

## Validation Strategy

1. **Pre-write:** `OCDPayloadValidationService` blocks invalid payload rows (empty class/property,
   invalid article numbers) — see `docs/uat_checklist.md` UAT-02.
2. **Post-write:** `WorkspaceSnapshotBuilder` reads the OCD MDB back into a read-only snapshot for
   conflict detection.
3. **Generator additions:** validate pricing references and variant-condition targets resolve to
   existing articles/options before writing `tCOMd_Price`.

## Future Implementation Roadmap

1. **Package Builder** — wrap `PDMToMDBService.generate_initial_tables` + `MDBService.create_handbook_base`
   behind a `PConPackageBuilder`; consume the snapshot only.
2. **Article/ArtBase Generator** — build article + base rows from `product_engineering_metadata`.
3. **Variant Condition Generator** — compose `com_VariantCondition` from `product_options.Code` +
   order-code format rules; gate by `product_dependencies` / `product_option_exclusion_rules`.
4. **Price Generator** — enumerate released Items; read pricing; apply `PriceMatrix`/`PriceFormula`;
   emit `tCOMd_Price` + `tCOMd_PriceList2`.
5. **Orchestrator + validation** — sequence stages, run pre/post validation, produce the finished OCD package.
6. **Optional CAD extension** — if CAD/PCon 3D is in scope, add a CAD-metadata engineering model
   (`CADAlias`, `CADPlaceProgram`, `CADSuffix`, `CADMaterial`, `LayerNameList`) using the same additive,
   validated methodology.

## Engineering Completeness Statement

The Builder Table is **engineering-complete for Metatype and GO** and for the **structural** part of a
PCon package. The only intentionally-deferred areas are **item-level pricing** and **generated variant
conditions** (both belong in the generator), and **CAD metadata** (only if CAD generation is added).
