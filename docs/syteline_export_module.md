# SyteLine Export module

This is a separate top-level module in MK Product Workbench based on
`Archive_demmy/PDMMaintenance/SytelineExport.cs` and its legacy export helpers.

## Implemented components

- Dedicated top-level module and isolated workflow page.
- Legacy-shaped controls for site, language, other language, catalogue, product-line/product-code filter,
  currency, range/list scope, effective date, catalogue-code override, export-all-in-site and legacy
  option tabs (SyteLine, SyteLine CSI, OFDA/CET and Other).
- Local persistence for editable controls, output folder, PDM User ID and selected item lists using application settings.
- Output-folder selection and setup preflight mapping controls to the legacy `ExportThread.initThread`
  argument names. This is a mapping/validation boundary only; it does not start the legacy thread or enable export.
- Local scope-control behavior: range endpoints are enabled only for range mode and item-list editing is
   enabled only for list mode.
- Read-only metadata loading for site, language, currency, permitted catalogue and product-code choices, using
  source-mapped legacy PDM queries and parameterized user/site/catalogue IDs.
- Parameterized item-selection SQL for catalogue, product-code, range, list, active-only, unreleased-catalogue,
  Browning range exception, alternate description, list-price query conditions, and super-product exclusion rewrite.
- Read-only item-query adapter returning database rows keyed by result column name.
- Read-only option-report adapter executing the legacy `PDMOptionDataReport` procedure for one item and
  returning raw result rows. The complex downstream dependency/fabric/feature transformation is not part of this adapter.
- Standard SyteLine item-row formatter for resolved inputs, including status/reason mapping, price source and
  negative-price clamp, description character replacement, note/legacy marker selection, fixed fields,
  20 feature slots and dimensions. It does not resolve option values or build material/BOM rows by itself.
- Source-mapped SQL and atomic TSV writers for price-formula and product-code outputs. The legacy product-code
  file's five-column header/four-column row mismatch is preserved deliberately.
- TSV structure validation for known legacy description, planning, super-product, material, price-formula and
  product-code headers, including header-only output and row-width checks.
- Unit tests for query parameter binding, item-row mapping, connection cleanup, option-report extraction and invalid input.

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
- Product code: 5 declared header columns, `Site`, `ProductCode`, `Description`, `PriceCode`, `UnitCode`. The legacy row writer emits four values, so this header/row-width discrepancy remains a known legacy defect pending downstream verification.

An empty item file is accepted as an observed empty result for this run, not as proof that item exports are always empty.
No item header or row mapping is inferred. The sample output provides structural evidence only; it does not establish
SQL mapping, transformation, filtering, price, BOM, or option parity.

## Safety and verification boundary

The metadata loader connects read-only to the configured PDM database to retrieve site, language, currency,
permitted catalogue and product-code choices. It does not write to PDM or connect to SyteLine. SQL Server
connectivity requires a reachable configured server, appropriate read permissions, an installed SQL Server
ODBC driver, and a PDM User ID permitted by `PDMUserCatalogues`. The authenticated user ID is entered explicitly
because this application does not yet share the legacy PDM Maintenance authentication session.

The exporter is not yet 100% functionally equivalent or production-ready. The option report can now be extracted,
but legacy option/dependency traversal, fabric and feature transformations, material/super-product/BOM row generation,
full base-price behavior, CSI-specific formatting, OFDA/CET generation and validation, queue/scheduler execution,
and differential output verification remain unported. Live export remains disabled; query and row-formatting helpers
are not a claim of end-to-end export parity.

## Remaining work before sign-off

1. Finish a control-by-control inventory against the full legacy form and trace each control through handlers and
   `initThread` arguments.
2. Port the option report's transformation and dependency traversal, including legacy special cases and fabric handling.
3. Implement material, super-product and BOM row generation and the associated output writers.
4. Complete base-price and product-code/price-formula behavior and determine the actual downstream contract for
   the product-code header/row discrepancy.
5. Port CSI formatting and OFDA/CET generation/validation.
6. Port queue/scheduler execution, cancellation and diagnostics.
7. Obtain representative known-good legacy outputs for item, material, super-products, options, BOMs, pricing,
   catalogues, ranges and explicit lists.
8. Differential-test generated files against those outputs before enabling export behind preflight checks and
   explicit confirmation.

The legacy exporter creates separate item, material, super-product, description, planning, price-formula and
product-code outputs, with additional CSI/OFDA/CET and optional downstream formats. Each output family needs an
explicit field mapping and parity test; a successful UI render or SQL query alone is not proof of parity.
