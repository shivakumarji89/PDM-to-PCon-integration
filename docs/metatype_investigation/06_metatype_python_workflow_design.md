# 06 — Existing Code, Reuse, Gap Analysis, and Proposed Python Workflow

This file answers "what already exists / what can be reused / what's missing" and then, only
after that, sketches the proposed workflow shape. **Nothing described here has been implemented.**

## 1. What already exists (CODE FACT, file:line cited)

- **`services/mdb_service.py:76-139`** — the sole Access-`.mdb` I/O gateway (32-bit PowerShell
  bridge, `resources/mdb_bridge.ps1`, because the app runs 64-bit and has no in-process ACE
  provider). Every other MDB consumer in the repo goes through it. **go_* data is pure CSV and
  never touches MDB anywhere sampled in the repository (file 01/02) — this service is only
  relevant to Metatype work if some future package/registration metadata ends up MDB-backed; it
  must not be duplicated if so.**
- **`services/mdb_reverse_engineering_service.py:1-15,36-64,163-459`** — reads an allow-listed set
  of `tCOMd_*` OCD tables and reconstructs a `Snapshot` via `import_snapshot()`. Its own docstring
  explicitly names "future Metatype work" as a beneficiary of this layer's design — but its
  `READABLE_TABLES` allow-list contains zero `go_*` names. **This is the right pattern to mirror
  (allow-list → normalize → write into Snapshot), not directly reusable code (CSV vs MDB).**
- **`models/snapshot.py:1-238`** — "the single source of truth for all engineering data held in
  memory... fields and relationships only, no logic." Already holds OCD-specific extensions
  (`text_blocks`, `relation_objects`, `value_tables`, `art_base`, `prog_info_rows`,
  `material_manufacturer_code` defaulting to `"hmx"`). Per the prior `docs/pcon_investigation/
  10_canonical_model.md`, this is the confirmed canonical model to extend, not replace. **Zero
  fields exist today for any Metatype concept** (no child/attachment-point/OFML-class-mapping
  equivalent).
- **`services/engineering/engineering_repository.py:1-50`** — a **naming collision to avoid**:
  this class means an in-memory read-only query layer over `snapshot.engineering.families`, NOT a
  filesystem/OFML repository tree. A Metatype design must pick a different term (e.g. "OFML
  Repository" / "hmx Repository").
- **Repository browser scaffolding** — `core/config.py:46-51`
  (`repository_browser_roots`, currently hardcoded to two published `WS\...` roots) →
  `ui/pages/product_page.py:747-796` (`_load_repository_browser`, lists immediate series folders
  only, two levels deep) → `services/maintenance_repository_link_service.py:63-96`
  (`inspect_repository`, checks only for `pcr_data_com_ocd.mdb`, reads only `tCOMd_Package`).
  **Real, reusable scaffolding (persisted-link registry, tree-walk shape), but currently
  MDB-file-only and points at the published `WS\...` tree, not the `_repository\hmx\<series>`
  engineering tree that actually holds `go_*.csv` files.**
- **`"hmx"` manufacturer constant** — live in current code, not just docs:
  `services/ocd_export_service.py:35`, `services/xocd_export_service.py:45`,
  `services/engineering/material_picking_service.py:22`, `models/snapshot.py:180`,
  `services/snapshot_serialization.py:1062`. Directly reusable.
- **PDM connection/presets** — `core/config.py:11-17,32-37,53-81`
  (`PDM_DATABASE_PRESETS`, `AppConfig.pdm_connection_string()`). Generic, format-neutral, reusable
  as-is if a future Metatype generator needs PDM source data.
- **Internal documentation (real, substantial, already present)** —
  `docs/Engineering_Handbook/10_Metatype.md` (table-graph + field descriptions),
  `13_Naming_Standards.md`, `14_Generation_Process.md`, `15_File_Formats.md`, plus vendor spec
  reprints `docs/pcon_reference/MT_1.18.0_en.md` / `MT-StyleGuide_1.2_en.md`, and legacy-C#-exporter
  forensics in `docs/Legacy_PDM_Business_Logic/06_Articles.md` / `07_Attributes.md` / `21_OCD.md`
  describing how the *old* exporter built `go_articles`/`go_properties` DTOs
  (`metaArticles.cs`/`metaProperties.cs`, explicitly "not table-backed, no DB access") and wrote
  them to `hmx\<series>\1\`. **This investigation independently re-derived the same schema/
  workflow facts from the manual/repository rather than trusting that handbook — the two agree
  everywhere cross-checked, which raises confidence in both.**

## 2. What can be reused as-is

`MDBService` (only if MDB involvement ever arises — currently N/A), the PDM connection/preset
stack, the `"hmx"` constant, and the persisted repository-link registry pattern
(`MaintenanceRepositoryLinkService`, JSON-backed via `core/config.py:44
repository_connection_registry`).

## 3. What is partially implemented

The repository browser (two-level tree, but MDB-file-only and wrong root — needs extending to
recurse into a series' `1/` subfolder and glob `go_*.csv`, and to target
`_repository\hmx\<series>` as an additional/alternate root alongside the existing `WS\...` roots).
The `mdb_reverse_engineering_service.py` shape (allow-list → import_snapshot) is a proven pattern
to mirror for a parallel CSV-based reader — but would be new code, not an extension of that file,
since it's a structurally different I/O path (plain CSV, not MDB).

## 4. What is missing entirely

Any Python code reading or writing a `go_*.csv` table (grep-confirmed zero hits repo-wide outside
`docs/`). Any `Snapshot` fields for Metatype concepts (children/attachment-points/OFML-class
mapping/setup-flags/actions). Any workflow/UI page analogous to Class Creation/Articles/Relation
for Metatype. Any validation tool integration (Metatype-Inspector 3.0's actual checks are
undocumented in the supplied materials — file 04 §8 item 4).

## 5. Do-not-duplicate list (explicit, per investigation brief rule 11)

- Do not build a second MDB access path — go through `MDBService` if MDB is ever involved.
- Do not reuse `models/relation_object.py` for `go_attpt`/`go_children`/`go_childprops` — per
  `docs/pcon_investigation/07_relation_object_configuration_model.md`, that model deliberately
  abstracts only over OCD's two relation wire-shapes (MDB join-table vs. XOCD name-linked); the
  Metatype attachment-point/child-creation graph is a third, structurally distinct relationship
  domain and needs its own model(s), though it can follow the same "abstract over multiple wire
  formats" design principle.
- Do not name a new class "Engineering Repository" — that name is taken by
  `services/engineering/engineering_repository.py` for an unrelated in-memory concept.
- Do not build a new PDM access layer or a new folder-tree browser from scratch — extend the
  existing ones (§1/§3 above).

## 6. Proposed Python workflow (conceptual only — not implemented, not to be built in one step)

Following the reconstructed process in file 05, and mirroring the reuse/extend shape established
by `mdb_reverse_engineering_service.py` for the OCD/MDB side:

```
MetatypeWorkflow
    discover_repository(root)          # find hmx\<series> folders, classify built vs. unbuilt (file 01 §2)
    inspect_series(series)             # STEP 1: read go_types/go_propvalues/go_proporder/go_children for a target series
    load_go_tables(series)             # parse every go_*.csv per the mt.inp_descr-confirmed schema (file 02)
    resolve_relationships(tables)      # build the FK graph from file 03 (prm_key/chprm_key/child_key/id chains)
    construct_metatype_model(tables)   # populate new Snapshot-adjacent fields (not yet defined) mirroring OCD extensions
    validate_metatype(model)           # mode/format compatibility checks, go_propvalues vs go_actions reachability (STEP 4a bug class)
    generate_output(model, series)     # write go_*.csv per series conventions identified in inspect_series()
    verify_output(series)              # invoke ebmkdb.exe, check exit code + timestamp (STEP 7)
```

Per method:

| Method | Purpose | Inputs | Outputs | Existing service to reuse | New logic required | Validation | Failure conditions | Evidence |
|---|---|---|---|---|---|---|---|---|
| `discover_repository` | enumerate hmx series folders, classify built/unbuilt | root path | list of series + built-flag | folder-browser scaffolding pattern (§1) | recursive walk + `go_*` glob (doesn't exist today) | root exists, is a directory | root missing/inaccessible | file 01 |
| `inspect_series` | STEP 1 evidence gathering | series name | conventions summary (prefix, existing values) | none directly; new CSV parser | yes — CSV read | series folder exists; if unbuilt, fall back to reference series | series not found anywhere, including reference series | file 05 STEP 1 |
| `load_go_tables` | parse all go_*.csv per schema | series, tables list | typed rows per table | none | yes — schema-driven CSV parser (semicolon, `#` comments, quoting rules per [MT §2]) | column count/type per `mt.inp_descr`-derived schema (file 02) | malformed CSV, unknown column count | file 02 |
| `resolve_relationships` | build FK graph | parsed tables | linked model | none | yes | every `chprm_key`/`prm_key`/`child_key` resolves to an existing row (file 03) | dangling reference | file 03 |
| `construct_metatype_model` | populate canonical model | linked tables | new Snapshot-adjacent structure | `models/snapshot.py` as extension target (§1) | yes — new fields/model, mirroring how `relation_objects`/`text_blocks` were added | — | — | file 06 §1 |
| `validate_metatype` | catch known bug classes + spec rules | model | pass/fail + findings | none | yes | mode 8192 has a go_propvalues entry; default value reachable under every article's filter (STEP 4a); mode/format compatibility (file 04 §3/§4) | default value unreachable, missing i18n row, mode/format mismatch | file 05 STEP 4a; file 04 §7 item 1 (flag mode-2048-on-ch as a warning, not a hard failure, given the unresolved contradiction) |
| `generate_output` | write go_*.csv | model, series | updated CSV files on disk | none | yes | only after explicit user confirmation (STEP 6) | write conflicts with unsaved manual edits (`.bak`/`.new` files observed in file 02 show this already happens by hand) | file 05 STEP 6 |
| `verify_output` | compile + sanity-check | series | ebase build result | none (shell out to `ebmkdb.exe`, not a Python reimplementation) | yes — subprocess wrapper | exit code 0, fresh `.ebase` timestamp | non-zero exit, `make_ebase.bat`'s blocking `pause` if invoked by mistake | file 05 STEP 7 |

These method names/signatures are illustrative, not a commitment — actual design should happen in
a follow-up planning step, one connected piece at a time (rule 12), starting with
`discover_repository`/`load_go_tables` (read-only, lowest risk, and independently testable per
file 07) before any write path is attempted.
