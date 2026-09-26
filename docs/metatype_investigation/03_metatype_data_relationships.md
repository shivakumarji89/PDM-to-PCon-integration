# 03 — go_* Data Relationship Map

All relationships below are **REPOSITORY FACT** — confirmed by literal string matches on values
actually read from the CSVs (cited by exact file/family), not inferred from column-name
similarity alone. Source family unless noted: `cyclade_Tables/1` and `atlas/1`.

## Confirmed relationship table

| Source File | Source Key | Target File | Target Key | Meaning | Evidence |
|---|---|---|---|---|---|
| go_articles | `prm_key` (e.g. `CFG_FE1L`) | go_properties | `key` | article's standard-property parameter set | `cyclade_Tables/1`: `go_articles` row `...;FE1L;CFG_FE1L;CHP_FE21` ↔ `go_properties` row `MT_CYCLADE;CFG_FE1L;GTABLE_Type;Cyclade_Table_Low;;` |
| go_articles | `chprm_key` (e.g. `CHP_FE21`) | go_childprops | `key` | article's child-property parameter set | same rows as above |
| go_childprops | `child_key` (e.g. `CH_FE21`) | go_children | `child_key` | which concrete child article this value creates | `go_childprops` row `CHP_FE21;GGLASS_BOWL;GLASS_BOWL_YES;CH_FE21` ↔ `go_children` row `CH_FE21;hmx;cyclade_tables;FE21;...` |
| go_properties/go_types/go_propclasses | `name` / `prop_name` | go_texts | `key` | i18n label lookup | `GTABLE_Type`, `Cyclade_Table_Low`, `GGLASS_BOWL`, `GLASS_BOWL_YES`, `GLASS_BOWL_NO` all present as both property/value identifiers AND as `go_texts.key` rows (en/de/fr/nl) |
| go_attpt | `pos_x`/`pos_z` NumExpr (e.g. `GATLAS_OffsetX * 0.001`) | go_freenumeric | `name` | attachment-point position parametrized by a free-numeric property | `atlas/1/go_attpt.csv` references `GATLAS_OffsetX`/`GATLAS_OffsetZ`; `atlas/1/go_freenumeric.csv` declares exactly those two names |
| go_propvalues | `condition` `@Token` references | go_proporder | `value` | value-validity condition branches on a value that also has a declared sort position | `atlas/1/go_propvalues.csv` conditions reference `@ATLAS_Type_SG/_PT/_CR/_SA/_PR/_ME/_CL/_TP` (8 tokens); `atlas/1/go_proporder.csv` enumerates exactly those 8 values — 8/8 matched |
| go_types / go_articles / go_setup / go_propclasses | `id` (metatype id, e.g. `MT_CYCLADE`) | (shared join key, not a separate target file) | `id` | unifies every table describing one metatype | same `MT_CYCLADE` (and sibling `MT_CYCLADE_B`) appears as column 1 in all four tables in `cyclade_Tables/1` |
| go_classes | `id` | go_types | `id` | maps metatype to implementing OFML class | `layout_studio/1/go_classes.csv`: `MT_LS_Desk;::hmx::layout_studio::lsMetaType` — id matches a `go_types.id` |
| go_articles.csv vs. go_articles.csv.bak | `program` column | — | — | evidences a family rename over time | `.bak`: `program=cyclade`, empty `chprm_key`; live: `program=cyclade_tables`, populated `chprm_key` — direct field diff, not inferred |

## Primary / foreign identifiers, by role

- **Primary identifiers**: `go_types.id` + `go_types.name` (metatype id + property name, one row
  per pair) is the master key for property definitions. `go_articles.id` + `go_articles.article_nr`
  is the master key for concrete articles (both indexed per `mt.inp_descr`).
- **Foreign identifiers**: `go_articles.prm_key`/`chprm_key` (→ go_properties/go_childprops),
  `go_childprops.child_key` (→ go_children), property `name`/value identifiers (→ go_texts.key,
  go_propvalues.name, go_proporder.value, go_types.filter entries).
- **Parent/child relationships**: realized through the `go_articles→go_childprops→go_children`
  chain (a value assigned to a child-controlling property, mode bit 8, creates/attaches a
  concrete child article) — this is structurally distinct from OCD's `tCOMd_RelObj`/`Relation`
  relation-object model used elsewhere in this codebase (see file 06 §3g).
- **Article/class relationships**: `go_classes.id → go_types.id`, binding a metatype to its OFML
  implementing class (defaults to `::ofml::go::GoMetaType` if no row exists).
- **Property/value relationships**: `go_types.name` (property) ↔ `go_propvalues.name`/`value`
  (validity restriction, gated by mode 8192) ↔ `go_proporder.value` (display order, gated by mode
  128) ↔ `go_texts.key` (label).
- **Template relationships**: `go_itemplates.id/template` (obsolete, always empty in this
  snapshot) — no evidence any current family uses ITemplates.
- **Inheritance relationships**: `go_inhproperties.id/pid/property` (explicit inherit-from-ancestor
  entries) and `go_nativeproperties.id/pid/mode/identifier` (native-property inclusion/exclusion
  filter, resolution algorithm documented in file 04 §5) — both **always empty** in this
  repository snapshot (file 02), so no concrete on-disk example of either mechanism exists to
  cross-check against the manual's algorithm.
- **Geometry-related relationships**: `go_attpt.pos_*`/`rot_y` NumExpr fields reference
  `go_freenumeric.name` identifiers (confirmed, atlas); `odb2d.csv`/`odb3d.csv` (non-go_* files)
  separately link geometry-choice rows to actual `.egms`/`.dwg` filenames — this is a **different,
  lower ("ODB") layer**, not part of the go_* schema itself, and should not be conflated with it.
- **Metadata relationships**: `go_setup.id → go_types.id` (per-metatype behavior flags),
  `go_propclasses.id/prop_name → go_types.id/name` (property-editor grouping).
- **Polymorphic relationships**: no separate "polymorphism table" exists — polymorphism is
  realized entirely through the ordinary tables above (mode-4/mode-8 flags on `go_types` rows,
  `go_propvalues` gating, `go_actions` CON_PROP/SET_PROP rows) rather than a dedicated schema
  construct. See file 04 §1 and file 05.

## What was NOT found

- No relationship evidence at all for the always-empty tables (`go_inhproperties`,
  `go_nativeproperties`, `go_propindex`, `go_propmapping`, `go_metainfo`, `go_feedback`,
  `go_attptgeo`, `go_interactors`, `go_itemplates`, `go_resetnativeprops`) — their FK behavior as
  documented in the manual (file 02, file 04 §5) is **DOCUMENTED FACT only, not REPOSITORY
  FACT** — no live example exists anywhere sampled to confirm it operates as described.
- `go_childmoving` was found non-empty only as a comment-only template (97-byte header, no data
  rows) in every family checked (accessories, atlas_storage, kumi, para) — so its condition/mode/
  command relationship structure is likewise DOCUMENTED FACT only in this snapshot.
