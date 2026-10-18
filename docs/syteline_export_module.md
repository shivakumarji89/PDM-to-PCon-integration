# SyteLine Export module

This is a separate top-level module in MK Product Workbench based on
`Archive_demmy/PDMMaintenance/SytelineExport.cs` and its legacy export helpers.

## Phase 1 scope

- Dedicated top-level module and isolated workflow page.
- Legacy-shaped controls for site, language, other language, catalogue, product-line/product-code filter,
  currency, range/list scope, effective date, catalogue-code override, export-all-in-site and legacy
  option tabs (SyteLine, SyteLine CSI, OFDA/CET and Other).
- Local persistence for editable controls and selected item lists using application settings.
- Local scope-control behavior: range endpoints are enabled only for range mode and item-list editing is
  enabled only for list mode.
- Read-only metadata loading for site, language, currency, permitted catalogue and product-code choices, using
  source-mapped legacy PDM queries and parameterized user/site/catalogue IDs. The authenticated PDM User ID is
  required to query the legacy `PDMUserCatalogues` access list.
- Source-mapped SQL and atomic TSV writers for price-formula and product-code outputs. The legacy product-code
  file's five-column header/four-column row mismatch is preserved deliberately.
- Clear UI guardrails for functions whose data dependencies have not been ported: scheduler, contract
  loading, multi-site/language/currency selection, BOM export, queueing and live export remain disabled.
  Compare/Validate XML also remain disabled until their legacy behavior is ported.
- Local configuration validation and unit-test coverage.
- TSV structure validation for the known legacy description, planning, super-product, material, price-formula and
  product-code headers, including header-only output and row-width checks.

## Captured legacy Verbose Extract evidence

The supplied sample extraction contained three readable files and an empty item file:
- `PDMExport_description_data.txt`: header `Lang\tItem\tDescription`, no data rows.
- `PDMExport_item_data.txt`: empty in this run; its header/schema is therefore unknown.
- `PDMExport_planning_data.txt`: the captured 22-column header, no data rows.
- `PDMExport_superprod_data.txt`: populated tab-separated records with the captured 19-column header
  (`Item`, `Super Description`, `Seq`, `Component`, `Quantity`, `Description`, `Num Features`,
  and `FP1` through `FP12`).

Additional output headers were verified directly against `Archive_demmy/PDMMaintenance/ExportThread.cs`:
- Material: 12 columns, beginning `Parent Item`, `Feature`, `Component`.
- Price formula: 6 columns, `Site`, `CustPriceCode`, `ItemPriceCode`, `PriceFormula`, `PriceFactor`, `EffectiveDate`.
- Product code: 5 declared header columns, `Site`, `ProductCode`, `Description`, `PriceCode`, `UnitCode`. The legacy row writer emits four values, so this header/row-width discrepancy must be preserved as a known legacy defect until its downstream contract is verified.

An empty item file is accepted as an observed empty result for this run, not as proof that item exports
are always empty. No item header or row mapping is inferred. The sample output provides structural
evidence only; it does not establish SQL mapping, transformation, filtering, price, BOM, or option parity.

## Safety and verification boundary

The page does not connect to SQL Server or read/write SyteLine/PDM data. Saving settings only writes local
application settings. The legacy implementation depends on database-backed site/catalogue/language/currency
IDs, product-code mappings, contracts, stored procedures, BOM/material transforms, price calculations,
feature/option logic, CSI formatting, OFDA/CET outputs, validation and queue behavior. These must not be
approximated with invented SQL or placeholder output.

The current Phase 1 deliverable is a legacy-shaped configuration surface plus local validation of captured
TSV structure, not 100% functional parity and not production-ready export execution. Export remains disabled
until the execution path and output formats are ported and differentially tested.

## Remaining work before Phase 1 can be signed off

1. Finish a control-by-control inventory against the full legacy form and document every mapped, intentionally
   disabled, hidden, or unsupported control.
2. Trace each legacy control to its handler, value mapping and downstream export-thread argument.
3. Identify stored procedures, connection settings, external assemblies and Excel/COM assumptions.
4. Add tests for parameter mapping, validation, persistence, mode-dependent controls, and every known output.
5. Obtain representative known-good legacy output files for sites, catalogues, currencies, products, ranges,
   explicit lists, BOMs, super-products and options.
6. Implement read-only extraction adapters, transformations, writers, cancellation and diagnostics.
7. Differential-test each generated output against known-good files before enabling export behind preflight
   checks and explicit confirmation.

## Known legacy output families

The legacy exporter creates separate item, material, super-product, description, planning, price-formula and
product-code outputs, with additional CSI/OFDA/CET and optional downstream formats. Each output family needs
an explicit field mapping and parity test; a successful UI render or SQL query alone is not proof of parity.
