# SyteLine Export module

This is a separate top-level module in MK Product Workbench based on
`PDMMaintenance/SytelineExport.cs` and its legacy export helpers. The verified local copy of the legacy
source tree is `C:\Users\siaoca\Desktop\PDM\PDMMaintenance\`; the `Archive_demmy/` path cited by earlier
revisions of this document does not exist. See `syteline_export_legacy_behavior_inventory.md` for the
line-referenced behavior inventory.

## Implemented components

- Dedicated top-level module and isolated workflow page.
- Legacy-shaped controls for site, language, other language, catalogue, product-line/product-code filter,
  currency, range/list scope, effective date, catalogue-code override, export-all-in-site and legacy
  option tabs (SyteLine, SyteLine CSI, OFDA/CET and Other).
- Local persistence for editable controls, output folder, PDM User ID and selected item lists using application settings.
- Output-folder selection and setup preflight mapping controls to the legacy `ExportThread.initThread`
  argument names; the SyteLine tab can start the ported export (see Execution status).
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

Additional output headers were verified directly against `PDMMaintenance/ExportThread.cs`:
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

## Execution status (current)

The SyteLine tab can now run the exporter. `services/syteline_export/pipeline/` is a literal transliteration of
`ExportThread.execThread` and its helpers; `services/syteline_export/job.py` runs it safely (configuration
validation, per-site extract lock check, staged output published only when the run finishes, one explicit
status: success / completed_with_errors / cancelled / failed / blocked); the page starts it on a worker thread
after a confirmation dialog, with Cancel, elapsed time and distinct result messages. Database metadata loading
also runs off the UI thread. Nothing runs when the page opens.

**Not production-certified.** The port has not been compared with genuine legacy output (none populated was
available) and has not been run against a real database. The SyteLine CSI tab (`SytelineCSIExport`), OFDA/CET,
the "Other" tab and the legacy queue/scheduler are not ported; their buttons stay disabled. Excel COM output is
replaced by `.xlsx`. See `syteline_export_legacy_behavior_inventory.md` for the verification matrix, the
deviation register and the remaining blockers.

## Remaining work before sign-off

1. Produce known-good legacy outputs with the real PDM against a non-production database copy and add golden
   comparison tests (the exporter writes `Site.ExtractUser`, so never against production).
2. Read-only run of the pipeline against the PDM Test copy to validate the SQL and driver value types.
3. Port `SytelineCSIExport` (CSI tab), `OFDAExport`, and the queue/scheduler if they are required.
4. Decide the downstream `.xls` -> `.xlsx` change and the exclude-superproducts status rule.

The legacy exporter creates separate item, material, super-product, description, planning, price-formula and
product-code outputs, with additional CSI/OFDA/CET and optional downstream formats. Each output family needs an
explicit field mapping and parity test; a successful UI render or SQL query alone is not proof of parity.
