# 00 — Metatype Investigation Index

**Status:** Forensic, evidence-only investigation. No production code changed, no branch created,
nothing committed. This tree is a companion to, and does not duplicate, the existing
`docs/pcon_investigation/` tree (which covers OCD/XOCD/MDB/EBASE only — it never mentions
Metatype or any `go_*` table, confirmed in file 06 §4 below).

**Sources read in full**, three parallel investigation legs:
1. **Manual + process docs** — `MT_1.18.0_en.md` (OFML Metatype spec, v1.18.0, 3977 md lines /
   47 pages, EasternGraphics), `POLYMORPHIC_METATYPE_CREATION_TEMPLATE_04092026.md`,
   `Verus_Metatype_Prompt_TEST.md`, `oap_metatype2type.csv`, `Metatype-Inspector_3.0_History_EN.pdf`.
2. **hmx repository** — `C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx`, 102
   directories inspected structurally, 6 families inspected in file-content depth
   (cyclade_Tables, aeron, atlas built; comma, knot, hush unbuilt).
3. **Existing codebase** — `C:\01 Projects\mk_product_workbench` (this repo, branch `main`),
   full grep sweep + targeted reads of `services/mdb_service.py`,
   `services/mdb_reverse_engineering_service.py`, `models/snapshot.py`, engineering/*, plus a
   cross-check against `docs/pcon_investigation/`. **Discovery made during this leg**: the
   repo already contains a substantial internal reference chapter,
   `docs/Engineering_Handbook/10_Metatype.md` (plus `13_Naming_Standards.md`,
   `14_Generation_Process.md`, `15_File_Formats.md`, and a vendor spec reprint
   `docs/pcon_reference/MT_1.18.0_en.md`). **This investigation treats that handbook as prior
   documentation to cross-check, not as ground truth** — every claim below is independently
   re-derived from the manual/repository/code and labeled per the evidentiary convention.

**Labeling convention used throughout this tree** (per the investigation brief):
- **DOCUMENTED FACT** — stated in `MT_1.18.0_en.md`, section cited.
- **PROJECT PROCESS FACT** — stated in the polymorphic-creation template or Verus prompt, doc cited.
- **REPOSITORY FACT** — observed directly in `hmx\*` files, path/values cited.
- **CODE FACT** — observed directly in this repo's `.py` files, file:line cited.
- **INFERENCE** — logically derived, reasoning given.
- **UNKNOWN** — gap explicitly flagged, not silently resolved.

## Reading order

1. **[01 — Repository Structure](01_metatype_repository_structure.md)** — what `hmx\` actually
   contains: 102 directories, only 53 "compiled" (populated go_* + family `.ebase`), the
   build toolchain (`ebmkdb.exe`/`mt.inp_descr`/`make_ebase.bat`).
2. **[02 — go_* File Inventory](02_metatype_go_file_inventory.md)** — every go_* table's schema
   (from the manual and from each family's own `mt.inp_descr`), cross-checked against actual
   on-disk population; which tables are always empty repo-wide.
3. **[03 — Data Relationship Map](03_metatype_data_relationships.md)** — the confirmed FK chain
   between go_* tables, built from literal value matches, not filename guessing.
4. **[04 — Manual → Repository → Code Mapping](04_metatype_manual_mapping.md)** — per-concept
   status table (FOUND / PARTIALLY FOUND / NOT FOUND / UNKNOWN) plus the DOCUMENTED / PROCESS /
   INFERENCE / UNKNOWN separation the brief mandates.
5. **[05 — Polymorphic Metatype Workflow](05_polymorphic_metatype_workflow.md)** — the
   reconstructed end-to-end creation sequence (STEP 1..N format), built from the process docs +
   manual + Verus worked example.
6. **[06 — Existing Code / Reuse / Gap Analysis](06_metatype_python_workflow_design.md)** — what
   already exists in this codebase, what's reusable, what's missing, and the proposed (not yet
   implemented) Python workflow shape.
7. **[07 — Validation & Test Plan](07_metatype_validation_plan.md)** — independent test
   boundaries for each proposed workflow step.

## Single most important finding

**The phrase "Polymorphic Metatype" never appears in the official manual.** The manual calls the
underlying mechanism "article polymorphism" (config-on-inter-product-level: a property change
that switches the *basic article number* itself, via mode-4 properties + `go_info.configuration`
+ `go_propvalues`/`go_actions`). "Polymorphic Metatype" is MillerKnoll project terminology for
this same mechanism, used interchangeably in practice with the "Metatype with Childs" pattern
(mode-8 properties driving `go_children`/`go_childprops`). Both patterns are exercised in the
worked `Verus_Metatype_Prompt_TEST.md` example (parent-article switching AND a conditionally
attached child). See file 04 §1 and file 05 for the full reconstruction, and file 04 §7 item 1
for the one **unresolved spec-vs-practice contradiction** found (mode 2048 applied to a `ch`
property in the Verus example, which the manual restricts to `na`/`fn` formats only).

## Gap analysis (summary — see file 06 for full detail)

| # | Category | Finding |
|---|---|---|
| A | Already implemented | Nothing — zero `.py` files in this repo reference any `go_*` table name or "metatype" (grep-confirmed) |
| B | Reusable existing services | `services/mdb_service.py` (only if go_* is ever MDB-backed — it isn't today, go_* is pure CSV); the `mdb_reverse_engineering_service.py` **pattern** (allow-list → `import_snapshot()`); `models/snapshot.py` as the extension target; PDM connection/presets (`core/config.py`); the `"hmx"` manufacturer constant; the folder-browser scaffolding (`core/config.py:repository_browser_roots` → `product_page.py` → `maintenance_repository_link_service.py`) |
| C | Partially implemented | The repository browser (two-level, MDB-file-only, two hardcoded roots — would need extending to recurse into `go_*.csv` and to target `_repository\hmx\<series>` rather than the `WS\...` published tree) |
| D | Missing | Any CSV go_* reader/writer, any `Snapshot` fields for child/attachment-point/OFML-class concepts, any Metatype-specific model |
| E | Unclear / needs confirmation | 6 items — see file 04 §8 (mode-2048 contradiction, `configid` column origin, OAP mapping file schema, Metatype-Inspector 3.0 validation rules, the basket-position diagram, whether this ties to Phase-1-test artifacts already in git status) |
| F | Implementation risks | Only 53/~99 real families are "compiled" — any workflow must handle the unbuilt case; go_* has real on-disk anomalies (backup/variant files, a stray `Copy.csv`) that a naive glob would misread; several declared tables are obsolete and should not be written to for new work |

## Open questions carried into file 04 §8 / file 06

Not resolved by this investigation, flagged rather than guessed:
1. Does mode 2048 actually work on `ch`-format properties in practice, or is the Verus example non-compliant?
2. What is `go_articles.configid` relative to the documented `article_nr`/`id` columns?
3. What do `oap_metatype2type.csv` columns 4–5 mean precisely?
4. What does Metatype-Inspector 3.0 actually validate?
5. Exact basket-order-position 6-scenario mapping (manual page 34 diagram, lossy in md conversion).
6. Relationship (if any) of this investigation to `MK_Workbench_Phase1_Test.spec` / other untracked git-status artifacts — out of scope, not read.
