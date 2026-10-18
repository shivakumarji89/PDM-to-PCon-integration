# SyteLine Export module

This is a separate top-level module in MK Product Workbench based on
`Archive_demmy/PDMMaintenance/SytelineExport.cs` and its legacy export helpers.

## Phase 1 scope

- Dedicated top-level module and isolated workflow page.
- Legacy-shaped controls for site, language, other language, catalogue, product-line/product-code filter,
  currency, range/list scope, effective date, catalogue-code override, export-all-in-site and legacy
  option tabs (SyteLine, SyteLine CSI, OFDA/CET and Other).
- Local persistence for editable controls, output folder, PDM User ID and selected item lists using application settings.
- Output-folder selection and a setup preflight that checks database-selected IDs and maps current controls to
  the legacy `ExportThread.initThread` argument names. This is a mapping/validation boundary only; it does not
  start the legacy thread or enable export.
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

The metadata loader connects read-only to the configured PDM database to retrieve site, language, currency,
permitted catalogue and product-code choices. It does not write to PDM or connect to SyteLine. SQL Server
connectivity requires a reachable configured server, appropriate read permissions, an installed SQL Server
ODBC driver, and a PDM User ID that is permitted by `PDMUserCatalogues`. The authenticated user ID is
entered explicitly because this application does not yet share the legacy PDM Maintenance authentication
session.

The exporter is not yet 100% functionally equivalent or production-ready. The core item/material/super-product
transformation, planning and description row logic, base-price calculations, option/dependency traversal,
CSI-specific formatting, OFDA/CET generation and validation, queue/scheduler execution, and differential
output verification remain unported. Only price-formula and product-code auxiliary outputs have dedicated
source-mapped query/writer implementations so far. Live export remains disabled; metadata connectivity and
two auxiliary writers are not a claim of end-to-end export parity.

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
