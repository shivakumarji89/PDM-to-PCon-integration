# SyteLine Export module

This is a separate top-level module in MK Product Workbench based on
`Archive_demmy/PDMMaintenance/SytelineExport.cs`.

## Current stage

- Dedicated module card and standalone workflow page.
- Locally persisted SQL Server/database, site, product line, catalogue, language,
  currency, output folder, scope and export-option settings.
- Local configuration validation and unit-test coverage.
- Export execution is intentionally disabled. The legacy exporter contains
  domain-specific SQL, BOM/material transformations, feature-option handling,
  price logic, CSI formatting, validation, queueing and several output files.
  Those rules and dependencies must be mapped and compared with reference outputs
  before execution is enabled.
- This page does not connect to SQL Server or read/write SyteLine/PDM data.
  Saving settings only writes local application settings.

## Remaining parity work

1. Trace the legacy SQL calls and exporter/helper dependencies.
2. Identify stored procedures, connection settings, external assemblies and
   DTS/Excel/COM assumptions.
3. Capture known-good output files for representative sites, catalogues,
   currencies, products, ranges, explicit lists, BOMs, super-products and options.
4. Implement a read-only extraction adapter, transformations and output writers,
   with cancellation and diagnostics.
5. Differential-test every output against reference files before enabling export
   behind preflight and explicit confirmation.
