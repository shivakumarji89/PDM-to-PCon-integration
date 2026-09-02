# 08 — Migration Roadmap

**Status:** Analysis + plan over the existing implementation; unverified items marked `UNKNOWN`.

## Purpose

This document consolidates the companion analysis into an actionable migration
picture: **can a PDM-sourced product travel the existing MDB/OCD engineering
pipeline and behave exactly like an MDB-sourced one?** It does *not* redesign the
Builder, OCD writer, or ODB layer — it verifies compatibility per engineering
component and lists the *scoped gap-closures* that would bring PDM products to
full parity **inside the current architecture**.

Grounded entirely in the sibling docs (cross-linked, not duplicated):

- [01_MDB_Engineering_Workflow.md](01_MDB_Engineering_Workflow.md) — the MDB/OCD read + write flow.
- [02_PDM_Data_Model.md](02_PDM_Data_Model.md) — the PDM source side / payload shape.
- [03_Engineering_Object_Mapping.md](03_Engineering_Object_Mapping.md) — object-by-object mapping + flagged gaps.
- [04_Compatibility_Layer.md](04_Compatibility_Layer.md) — the existing PDM→payload→OCD bridge.
- [05_ODB_Integration.md](05_ODB_Integration.md) — geometry (path only, no reader/writer).
- [06_OCD_Integration.md](06_OCD_Integration.md) — authoritative `tCOMd_*` commercial model.
- [07_Builder_Workspace.md](07_Builder_Workspace.md) — the single source-agnostic workspace.

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
| **Builder Workspace** | ✓ reads `project.articles` ([07](07_Builder_Workspace.md#how-it-is-populated)) | ✓ *by contract* — same `.articles` shape ([07](07_Builder_Workspace.md#source-agnostic-contract-what-the-builder-consumes)); wiring partial (`UNKNOWN`) | None for the widget; origin must set `controller.project` with the uniform article shape | **Ready** (widget) / **Gap** (project wiring — controller handlers `TODO`/`pass`, [01](01_MDB_Engineering_Workflow.md), [07](07_Builder_Workspace.md#how-it-is-populated)) |
| **ODB (geometry)** | Path resolved/validated only; no reader/writer ([05](05_ODB_Integration.md#1-actual-state--path-resolvedvalidated-only)) | ✗ PDM provides no geometry source ([05](05_ODB_Integration.md)) | `tGEOd_*` reader/writer + geometry source — all `UNKNOWN` | **Gap / out-of-scope** — not on the OCD critical path ([05](05_ODB_Integration.md#3-odb-does-not-block-ocd-engineering)) |
| **OCD (commercial model)** | ✓ authoritative read + write ([06](06_OCD_Integration.md)) | ✓ converges on the same `tCOMd_*` rows via `create_handbook_base` ([04](04_Compatibility_Layer.md#end-to-end-flow), [06](06_OCD_Integration.md#4-how-ocd-stays-identical-for-mdb-vs-pdm-products)) | PDM data shaped to the existing payload contract; writer unchanged | **Ready** (except Option/OptionValue rows — see below) |
| **Articles** | ✓ `tCOMd_Article` read/written ([06](06_OCD_Integration.md#3-ocd-object--table--producerconsumer)) | ✓ `payload.Articles[]` from selected products → `get_or_create_article` ([03](03_Engineering_Object_Mapping.md#master-mapping-table)) | `ArticleCode = product.Product`; name fallback to code | **Ready** (geometry/lifecycle fields `UNKNOWN`) |
| **Properties** | ✓ `tCOMd_Property` read/written ([06](06_OCD_Integration.md)) | ✓ from `AttributeValues.property` ([03](03_Engineering_Object_Mapping.md#master-mapping-table)) | `(class_name, property)` dedup; created under class | **Ready** (data type/units `UNKNOWN`) |
| **Property Values** | ✓ `tCOMd_PropValue` read/written ([06](06_OCD_Integration.md)) | ✓ from `AttributeValues.value` → `normalize_prop_value_code` ([03](03_Engineering_Object_Mapping.md#master-mapping-table)) | Value-code normalization; optional text/price row | **Ready** (pricing/dependency links `UNKNOWN`) |
| **Options** | Snapshot **reads** `tCOMd_Option`; nothing writes it ([03](03_Engineering_Object_Mapping.md#flagged-gaps), [06](06_OCD_Integration.md#3-ocd-object--table--producerconsumer)) | ✗ present in payload/explorer but **not persisted** ([04](04_Compatibility_Layer.md#known-gaps-to-close-for-full-parity)) | Map option name → `tCOMd_Option` insert in `create_handbook_base` | **Gap** (write-coverage) |
| **Option Values** | Snapshot **reads** `tCOMd_OptionValue`; nothing writes it ([06](06_OCD_Integration.md#3-ocd-object--table--producerconsumer)) | ✗ produced by `add_option_values` but **not persisted** ([03](03_Engineering_Object_Mapping.md#master-mapping-table)) | Map value → `tCOMd_OptionValue` under its Option | **Gap** (write-coverage) |
| **Configuration (Relationships)** | Snapshot links parent/child best-effort ([06](06_OCD_Integration.md#1-ocd-loading-read-sequence)) | Partial — only `relationship_type = "contains"`, empty `metadata` ([03](03_Engineering_Object_Mapping.md#flagged-gaps)) | Richer edge types (constraint/price/dependency) — `UNKNOWN` | **Gap** (single relationship type) |

---

## TASK 6 — Migration plan

Master table: one row per engineering component. `✓` = present/works, `✗` =
absent, `Partial` = partially present. Each claim is cited to the doc that proves
it.

| Component | Current Implementation | PDM Available | MDB Compatible | Mapping Complete | Transformation Required | Ready | Blocked |
|---|---|---|---|---|---|---|---|
| **ComGroup** | `build_com_group` → `get_or_create_com_group` ([03](03_Engineering_Object_Mapping.md#master-mapping-table)) | ✓ (category name) | ✓ | ✓ | `ComGroupCode = name.upper()` | ✓ | ✗ |
| **Package** | `build_package` → `get_or_create_package` ([03](03_Engineering_Object_Mapping.md#master-mapping-table)) | ✓ (category name) | ✓ | ✓ | `ProgramCode = name.lower()`; region/material defaults | ✓ | ✗ |
| **Article** | `payload.Articles[]` → `get_or_create_article` ([06](06_OCD_Integration.md#3-ocd-object--table--producerconsumer)) | ✓ | ✓ | Partial (geometry/lifecycle `UNKNOWN`) | code/name mapping | ✓ | ✗ |
| **ArtBase** | projection of `AttributeValues` → ArtBase writer ([03](03_Engineering_Object_Mapping.md#master-mapping-table)) | ✓ (derived) | ✓ | ✓ | `normalize_prop_value_code`; longest-prefix article map | ✓ | ✗ |
| **ArticleClass** | derived join row → ArticleClass writer ([03](03_Engineering_Object_Mapping.md#master-mapping-table)) | ✓ (derived) | ✓ | ✓ | order `100 + i*10`; propclass text | ✓ | ✗ |
| **PropertyClass (Class)** | `_class_name_for_row` inference → `get_or_create_class` ([03](03_Engineering_Object_Mapping.md#master-mapping-table)) | Partial — `class_name` largely unpopulated | ✓ | ✗ (real class `UNKNOWN`) | infer `<series>_attr`/`_options`/`PLC`/`Code` | Partial | ✗ |
| **Property** | `AttributeValues.property` → `get_or_create_property` ([03](03_Engineering_Object_Mapping.md#master-mapping-table)) | ✓ | ✓ | Partial (type/units `UNKNOWN`) | `(class, property)` dedup | ✓ | ✗ |
| **PropertyValue** | `AttributeValues.value` → property-value writer ([03](03_Engineering_Object_Mapping.md#master-mapping-table)) | ✓ | ✓ | Partial (pricing `UNKNOWN`) | value-code normalization | ✓ | ✗ |
| **Option** | mapped in payload; **no `tCOMd_Option` insert** ([03](03_Engineering_Object_Mapping.md#flagged-gaps)) | ✓ (payload) | Read-only ✓ / write ✗ | ✗ | add Option writer to `create_handbook_base` | ✗ | Gap |
| **OptionValue** | `add_option_values` payload; **no `tCOMd_OptionValue` insert** ([04](04_Compatibility_Layer.md#known-gaps-to-close-for-full-parity)) | ✓ (payload) | Read-only ✓ / write ✗ | ✗ | add OptionValue writer under its Option | ✗ | Gap |
| **Text** | `get_or_create_text` / `insert_text` ([06](06_OCD_Integration.md#3-ocd-object--table--producerconsumer)) | Partial (synthesized on write) | ✓ | Partial (source strings `UNKNOWN`) | multilingual defaults | ✓ | ✗ |
| **Relationships / Configuration** | `add_relationships` → `contains` edges ([03](03_Engineering_Object_Mapping.md#flagged-gaps)) | Partial | Partial | ✗ (single type) | richer edge types `UNKNOWN` | Partial | ✗ |
| **Builder Workspace** | `wizard_shell` reads `project.articles` ([07](07_Builder_Workspace.md)) | ✓ (by contract) | ✓ | ✓ (widget) | none for widget | ✓ | ✗ |
| **OCD read (snapshot)** | `WorkspaceSnapshotBuilder.build` ([06](06_OCD_Integration.md#1-ocd-loading-read-sequence)) | ✓ | ✓ | ✓ | none (source-agnostic) | ✓ | ✗ |
| **OCD write (`create_handbook_base`)** | `mdb_helper.create_handbook_base` ([04](04_Compatibility_Layer.md#what-must-not-change)) | ✓ | ✓ | Partial (no Option/OptionValue) | none — unchanged writer | ✓ | ✗ |
| **ODB geometry** | path resolved/validated only ([05](05_ODB_Integration.md#1-actual-state--path-resolvedvalidated-only)) | ✗ | ✗ | ✗ | `tGEOd_*` reader/writer + source `UNKNOWN` | ✗ | Blocked (out-of-scope) |
| **Project wiring** | controller `open_project`/`select_product`/`load_articles` `TODO`/`pass` ([01](01_MDB_Engineering_Workflow.md), [07](07_Builder_Workspace.md#how-it-is-populated)) | n/a | n/a | ✗ | assign `controller.project` from selection | ✗ | Gap |

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
  (snapshot already reads them). See [03](03_Engineering_Object_Mapping.md#flagged-gaps),
  [04](04_Compatibility_Layer.md#known-gaps-to-close-for-full-parity).
- [ ] **Close OptionValue write coverage** — add the matching
  `tCOMd_OptionValue` insert under each Option, using the already-built
  `payload.OptionValues[]` from
  [`add_option_values`](../../services/generate_payload_service.py#L140). See [03](03_Engineering_Object_Mapping.md#master-mapping-table).
- [ ] **Populate property class** — source `class_name` from PDM instead of
  inferring it in [`_class_name_for_row`](../../services/pdm_to_mdb_service.py), or
  document the inference as authoritative. See [03](03_Engineering_Object_Mapping.md#flagged-gaps).
- [ ] **Finish project wiring** — implement the controller
  `open_project`/`select_product`/`load_articles` handlers to assign
  `controller.project` (they are `TODO`/`pass`), reusing the already-implemented
  [`ProjectService`](../../services/project_service.py) so the Builder Table
  populates end-to-end. See [01](01_MDB_Engineering_Workflow.md), [07](07_Builder_Workspace.md#how-it-is-populated).
- [ ] **(Optional) Broaden relationships** — extend
  [`add_relationships`](../../services/generate_payload_service.py#L75) beyond the
  single `contains` type once richer OCD edge semantics are known (`UNKNOWN`
  today). See [03](03_Engineering_Object_Mapping.md#flagged-gaps).

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
  [05_ODB_Integration.md](05_ODB_Integration.md).
