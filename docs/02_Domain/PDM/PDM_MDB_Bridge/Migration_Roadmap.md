# 08 — Migration Roadmap

**Status:** Analysis + plan over the existing implementation; unverified items marked `UNKNOWN`.

> **2026-09-27 correction:** the tables below cite `PDMToMDBService`,
> `MDBService.create_handbook_base`, `helpers/mdb_helper.py::create_handbook_base`,
> `workspace_import_service.py`, and `workspace_pipeline_service.py` as the
> "existing compatibility layer." Direct repo search confirms none of
> `services/pdm_to_mdb_service.py`, `helpers/mdb_helper.py`,
> `services/workspace_import_service.py`, `services/workspace_pipeline_service.py`,
> or `services/workspace_snapshot_builder.py` exist in the current codebase, and
> `services/mdb_service.py::MDBService` no longer has `create_handbook_base` or
> `get_rows`. This is the same stale architecture documented in
> [Repository_Model.md §0](../../Repository/Repository_Model.md) and
> [Snapshot.md](../../Repository/Snapshot.md). The **real, current** pipeline is:
> write — `services/ocd_export_service.py` (`OcdExportService`),
> `services/xocd_export_service.py` (`XocdExportService`); read-back —
> `services/mdb_reverse_engineering_service.py` (`MdbReverseEngineeringService`);
> PDM read — `services/pdm_service.py` (`PDMService`). Treat the specific
> file/function citations below as historical evidence of *what the gap analysis
> was reasoning about*, not as a description of the live pipeline — the
> **conclusions** (Option/OptionValue write coverage, property class sourcing,
> ODB, relationship types) still hold and are canonically listed in
> [Engineering_Object_Mapping.md](Engineering_Object_Mapping.md#flagged-gaps).

## Purpose

This document consolidates the companion analysis into an actionable migration
picture: **can a PDM-sourced product travel the existing MDB/OCD engineering
pipeline and behave exactly like an MDB-sourced one?** It does *not* redesign the
Builder, OCD writer, or ODB layer — it verifies compatibility per engineering
component and lists the *scoped gap-closures* that would bring PDM products to
full parity **inside the current architecture**.

Grounded entirely in the sibling docs (cross-linked, not duplicated):

- [MDB_Engineering_Workflow.md](MDB_Engineering_Workflow.md) — the MDB/OCD read + write flow.
- [PDM_Data_Model.md](PDM_Data_Model.md) — the PDM source side / payload shape.
- [Engineering_Object_Mapping.md](Engineering_Object_Mapping.md) — object-by-object mapping + flagged gaps.
- [Compatibility_Layer.md](Compatibility_Layer.md) — the existing PDM→payload→OCD bridge.
- [ODB_Integration.md](ODB_Integration.md) — geometry (path only, no reader/writer).
- [OCD_Integration.md](OCD_Integration.md) — authoritative `tCOMd_*` commercial model.
- [../../../01_Architecture/Workflow_Architecture.md](../../../01_Architecture/Workflow_Architecture.md) — the single source-agnostic workspace.

**Authoritative workflow** = OCD (`tCOMd_*` in `pcr_data_com_ocd.mdb`).
**Builder Workspace** = [`ui/widgets/wizard_shell.py`](../../ui/widgets/wizard_shell.py).
**Existing compatibility layer** = [`PDMToMDBService`](../../services/pdm_to_mdb_service.py)
+ [`build_product_payload`](../../scripts/run_workspace_pipeline.py)
+ [`MDBService.create_handbook_base`](../../services/mdb_service.py)
+ the [workspace_import](../../services/workspace_import_service.py) /
[workspace_pipeline](../../services/workspace_pipeline_service.py) services.

---

## TASK 5 — Compatibility verification

For each engineering concern: does it work for an **MDB**-sourced product, does
it work for a **PDM**-sourced product, what transformation is required, and its
overall **Status**. Grounded in the companion docs.

| Concern | Works for MDB? | Works for PDM? | Required transformation | Status |
|---|---|---|---|---|
| **Builder Workspace** | ✓ reads `project.articles` ([07](../../../01_Architecture/Workflow_Architecture.md#how-it-is-populated)) | ✓ *by contract* — same `.articles` shape ([07](../../../01_Architecture/Workflow_Architecture.md#source-agnostic-contract-what-the-builder-consumes)); wiring partial (`UNKNOWN`) | None for the widget; origin must set `controller.project` with the uniform article shape | **Ready** (widget) / **Gap** (project wiring — controller handlers `TODO`/`pass`, [01](MDB_Engineering_Workflow.md), [07](../../../01_Architecture/Workflow_Architecture.md#how-it-is-populated)) |
| **ODB (geometry)** | Path resolved/validated only; no reader/writer ([05](ODB_Integration.md#1-actual-state--path-resolvedvalidated-only)) | ✗ PDM provides no geometry source ([05](ODB_Integration.md)) | `tGEOd_*` reader/writer + geometry source — all `UNKNOWN` | **Gap / out-of-scope** — not on the OCD critical path ([05](ODB_Integration.md#3-odb-does-not-block-ocd-engineering)) |
| **OCD (commercial model)** | ✓ authoritative read + write ([06](OCD_Integration.md)) | ✓ converges on the same `tCOMd_*` rows via `create_handbook_base` ([04](Compatibility_Layer.md#end-to-end-flow), [06](OCD_Integration.md#4-how-ocd-stays-identical-for-mdb-vs-pdm-products)) | PDM data shaped to the existing payload contract; writer unchanged | **Ready** (except Option/OptionValue rows — see below) |
| **Articles** | ✓ `tCOMd_Article` read/written ([06](OCD_Integration.md#3-ocd-object--table--producerconsumer)) | ✓ `payload.Articles[]` from selected products → `get_or_create_article` ([03](Engineering_Object_Mapping.md#master-mapping-table)) | `ArticleCode = product.Product`; name fallback to code | **Ready** (geometry/lifecycle fields `UNKNOWN`) |
| **Properties** | ✓ `tCOMd_Property` read/written ([06](OCD_Integration.md)) | ✓ from `AttributeValues.property` ([03](Engineering_Object_Mapping.md#master-mapping-table)) | `(class_name, property)` dedup; created under class | **Ready** (data type/units `UNKNOWN`) |
| **Property Values** | ✓ `tCOMd_PropValue` read/written ([06](OCD_Integration.md)) | ✓ from `AttributeValues.value` → `normalize_prop_value_code` ([03](Engineering_Object_Mapping.md#master-mapping-table)) | Value-code normalization; optional text/price row | **Ready** (pricing/dependency links `UNKNOWN`) |
| **Options** | See [Engineering_Object_Mapping.md](Engineering_Object_Mapping.md#flagged-gaps) — write-coverage gap | ✗ not persisted | See canonical gap list | **Gap** (write-coverage) |
| **Option Values** | See [Engineering_Object_Mapping.md](Engineering_Object_Mapping.md#flagged-gaps) — write-coverage gap | ✗ not persisted | See canonical gap list | **Gap** (write-coverage) |
| **Configuration (Relationships)** | See [Engineering_Object_Mapping.md](Engineering_Object_Mapping.md#flagged-gaps) — single relationship type | Partial | See canonical gap list | **Gap** (single relationship type) |

---

## TASK 6 — Migration plan

Master table: one row per engineering component. `✓` = present/works, `✗` =
absent, `Partial` = partially present. Each claim is cited to the doc that proves
it.

| Component | Current Implementation | PDM Available | MDB Compatible | Mapping Complete | Transformation Required | Ready | Blocked |
|---|---|---|---|---|---|---|---|
| **ComGroup** | `build_com_group` → `get_or_create_com_group` ([03](Engineering_Object_Mapping.md#master-mapping-table)) | ✓ (category name) | ✓ | ✓ | `ComGroupCode = name.upper()` | ✓ | ✗ |
| **Package** | `build_package` → `get_or_create_package` ([03](Engineering_Object_Mapping.md#master-mapping-table)) | ✓ (category name) | ✓ | ✓ | `ProgramCode = name.lower()`; region/material defaults | ✓ | ✗ |
| **Article** | `payload.Articles[]` → `get_or_create_article` ([06](OCD_Integration.md#3-ocd-object--table--producerconsumer)) | ✓ | ✓ | Partial (geometry/lifecycle `UNKNOWN`) | code/name mapping | ✓ | ✗ |
| **ArtBase** | projection of `AttributeValues` → ArtBase writer ([03](Engineering_Object_Mapping.md#master-mapping-table)) | ✓ (derived) | ✓ | ✓ | `normalize_prop_value_code`; longest-prefix article map | ✓ | ✗ |
| **ArticleClass** | derived join row → ArticleClass writer ([03](Engineering_Object_Mapping.md#master-mapping-table)) | ✓ (derived) | ✓ | ✓ | order `100 + i*10`; propclass text | ✓ | ✗ |
| **PropertyClass (Class)** | See [Engineering_Object_Mapping.md](Engineering_Object_Mapping.md#flagged-gaps) — property class sourcing gap | Partial — `class_name` largely unpopulated | ✓ | ✗ (real class `UNKNOWN`) | See canonical gap list | Partial | ✗ |
| **Property** | `AttributeValues.property` → `get_or_create_property` ([03](Engineering_Object_Mapping.md#master-mapping-table)) | ✓ | ✓ | Partial (type/units `UNKNOWN`) | `(class, property)` dedup | ✓ | ✗ |
| **PropertyValue** | `AttributeValues.value` → property-value writer ([03](Engineering_Object_Mapping.md#master-mapping-table)) | ✓ | ✓ | Partial (pricing `UNKNOWN`) | value-code normalization | ✓ | ✗ |
| **Option** | See [Engineering_Object_Mapping.md](Engineering_Object_Mapping.md#flagged-gaps) — write-coverage gap | ✓ (payload) | Read-only ✓ / write ✗ | ✗ | See canonical gap list | ✗ | Gap |
| **OptionValue** | See [Engineering_Object_Mapping.md](Engineering_Object_Mapping.md#flagged-gaps) — write-coverage gap | ✓ (payload) | Read-only ✓ / write ✗ | ✗ | See canonical gap list | ✗ | Gap |
| **Text** | `get_or_create_text` / `insert_text` ([06](OCD_Integration.md#3-ocd-object--table--producerconsumer)) | Partial (synthesized on write) | ✓ | Partial (source strings `UNKNOWN`) | multilingual defaults | ✓ | ✗ |
| **Relationships / Configuration** | See [Engineering_Object_Mapping.md](Engineering_Object_Mapping.md#flagged-gaps) — single relationship type | Partial | Partial | ✗ (single type) | See canonical gap list | Partial | ✗ |
| **Builder Workspace** | `wizard_shell` reads `project.articles` ([07](../../../01_Architecture/Workflow_Architecture.md)) | ✓ (by contract) | ✓ | ✓ (widget) | none for widget | ✓ | ✗ |
| **OCD read (snapshot)** | `WorkspaceSnapshotBuilder.build` ([06](OCD_Integration.md#1-ocd-loading-read-sequence)) | ✓ | ✓ | ✓ | none (source-agnostic) | ✓ | ✗ |
| **OCD write (`create_handbook_base`)** | `mdb_helper.create_handbook_base` ([04](Compatibility_Layer.md#what-must-not-change)) | ✓ | ✓ | Partial (no Option/OptionValue) | none — unchanged writer | ✓ | ✗ |
| **ODB geometry** | path resolved/validated only ([05](ODB_Integration.md#1-actual-state--path-resolvedvalidated-only)) | ✗ | ✗ | ✗ | `tGEOd_*` reader/writer + source `UNKNOWN` | ✗ | Blocked (out-of-scope) |
| **Project wiring** | controller `open_project`/`select_product`/`load_articles` `TODO`/`pass` ([01](MDB_Engineering_Workflow.md), [07](../../../01_Architecture/Workflow_Architecture.md#how-it-is-populated)) | n/a | n/a | ✗ | assign `controller.project` from selection | ✗ | Gap |

> Note: [`ProjectService.load_product` / `load_articles`](../../services/project_service.py)
> are implemented; the unwired step is the **controller** handlers that select a
> product and place the project on `controller.project` — those are `TODO`/`pass`.

---

## Recommended sequence (parity WITHOUT redesign)

Each item is a **scoped gap-closure** that makes PDM products behave like MDB
products in the *existing* pipeline. None changes the OCD schema, the Builder, or
the source-agnostic contract.

- [ ] **Close Option write coverage** — add a `tCOMd_Option` insert in
  [`create_handbook_base`](../../helpers/mdb_helper.py#L1387) fed from the
  existing option-source `AttributeValues`, so options persist and round-trip
  (snapshot already reads them). See [03](Engineering_Object_Mapping.md#flagged-gaps),
  [04](Compatibility_Layer.md#known-gaps-to-close-for-full-parity).
- [ ] **Close OptionValue write coverage** — add the matching
  `tCOMd_OptionValue` insert under each Option, using the already-built
  `payload.OptionValues[]` from
  [`add_option_values`](../../services/generate_payload_service.py#L140). See [03](Engineering_Object_Mapping.md#master-mapping-table).
- [ ] **Populate property class** — source `class_name` from PDM instead of
  inferring it in [`_class_name_for_row`](../../services/pdm_to_mdb_service.py), or
  document the inference as authoritative. See [03](Engineering_Object_Mapping.md#flagged-gaps).
- [ ] **Finish project wiring** — implement the controller
  `open_project`/`select_product`/`load_articles` handlers to assign
  `controller.project` (they are `TODO`/`pass`), reusing the already-implemented
  [`ProjectService`](../../services/project_service.py) so the Builder Table
  populates end-to-end. See [01](MDB_Engineering_Workflow.md), [07](../../../01_Architecture/Workflow_Architecture.md#how-it-is-populated).
- [ ] **(Optional) Broaden relationships** — extend
  [`add_relationships`](../../services/generate_payload_service.py#L75) beyond the
  single `contains` type once richer OCD edge semantics are known (`UNKNOWN`
  today). See [03](Engineering_Object_Mapping.md#flagged-gaps).

Framing: these are additive write-coverage / wiring fixes on top of the existing
compatibility layer — **not** architecture changes.

---

## Explicitly out of scope

The following are **not** part of this migration phase:

- **GO generation** — out of scope.
- **MetaType generation** — out of scope.
- **Export** — out of scope.
- **ODB geometry authoring** — no `tGEOd_*` reader/writer and no PDM geometry
  source exist; not on the OCD critical path. See
  [ODB_Integration.md](ODB_Integration.md).
