# ComGroup & Package

**Related:** [OCD_Tables_Overview.md](./OCD_Tables_Overview.md) · [Repository_Model.md](./Repository_Model.md)

> **2026-09-27 correction:** this document previously described `ComGroup`/`Package` as built fresh from a category name by `PDMToMDBService.build_com_group`/`build_package`, with IDs assigned by `generate_initial_tables`. That service does not exist in the current codebase. The corrected description below is verified against `services/ocd_export_service.py` (2026-09-27). See [Repository_Model.md §2, row 1](./Repository_Model.md) for the FK evidence this correction is based on.

`ComGroup` and `Package` are the top two levels of the OCD package skeleton. They are **not created fresh** by the current exporter — they already exist in the template MDB the export starts from, and the exporter only relabels them.

## What the current exporter actually does

`OcdExportService.export` (`services/ocd_export_service.py`) copies a template `pcr_data_com_ocd.mdb` (chosen by `template_kind`, e.g. `"seating"`/`"tables"`) as the write target, then reads the **existing** `com_PackageID` and `com_ComGroupID` off the template's single `tCOMd_Package` row. It never creates a new ComGroup/Package row and never re-parents `Package.com_ComGroupID` — those FKs are template-owned for the life of the export.

- `tCOMd_ComGroup` / `tCOMd_Package` are **updated** (label/code fields), not written from scratch.
- `com_MaterialMF` / `com_MaterialPK` are set from the constants below (verified live in `ocd_export_service.py`).
- The distribution region (`tCOMd_DistributionRegion`) is read from the real table via `DistributionRegionService`, not a hardcoded id.

## Constants (packaging-only, business-fixed)

| Constant | Value | Meaning | Verified in |
|---|---|---|---|
| `material_manufacturer_code` | `"hmx"` | Manufacturer material key (Herman Miller X) | `models/snapshot.py`, `services/ocd_export_service.py` (`_MATERIAL_MANUFACTURER`), `services/xocd_export_service.py` (`_MANUFACTURER_ID`) |
| `material_package_code` | `"basics"` | Program/package material key | `models/snapshot.py`, `services/ocd_export_service.py` (`_MATERIAL_PACKAGE`) |

These are packaging configuration, not engineering data — they are stored on the `Snapshot` model (`material_manufacturer_code`/`material_package_code`) with those two literal defaults, and read from there by both exporters.

## Downstream relationships

`Package → Article` and `ComGroup → Article` (the current exporter writes **both**: `Article.com_PackageID` and a direct `Article.com_ComGroupID`, not only the indirect Package→ComGroup path) — see [Repository_Model.md §2, rows 1-3](./Repository_Model.md) for the full verified FK detail. That table is the canonical source for this relationship; it is intentionally not repeated here.
