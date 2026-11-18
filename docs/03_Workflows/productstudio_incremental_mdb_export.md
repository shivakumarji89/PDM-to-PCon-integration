# ProductStudio incremental MDB export

**Rule: one product → one MDB → each workflow adds its own data.** The template is
copied once; later workflows never re-copy it, never wipe it and never renumber keys.

## Components

| Piece | Role |
|---|---|
| `models/mdb_export_session.py` | `MdbExportSession`: MDB path, package / ComGroup / manufacturer ids, template boilerplate rows, `article_map`, `scheme_map`, `workflow_status`. |
| `services/mdb_export_session_service.py` | Product key, persistence, recovery, one-time `initialize()`, `record_workflow()`. |
| `services/article_mdb_export_service.py` | `export_to_session()` — Articles workflow. |
| `services/class_creation_mdb_export_service.py` | `export_to_session()` — article-scoped Class Creation, CodeScheme body extension, and ArticleClass links. |
| `services/properties_values_mdb_export_service.py` | `export_to_session()` — selected-article Properties and Values, adding only missing `tCOMd_Property` / `tCOMd_PropValue` rows. |
| `services/text_mdb_export_service.py` | `export_to_session()` — selected-article Text upsert, retaining Text IDs and linking Article / Property / PropValue text references. |
| `services/relation_mdb_export_service.py` | `export_to_session()` — selected-article Relation Object, Relation and RelObjRel upsert with entity back-references. |
| `services/price_mdb_export_service.py` | Existing price-list / price-row exporter, now routed to the active Maintenance product session and filtered to selected article base codes (global prices remain product-level). |
| `services/mdb_service.py` | Unchanged: the only MDB I/O gateway (transactional `execute_batch`). |
| `ui/main_window.py::_on_export_articles_to_mdb` | Dialogs only; called from the Articles page "Export to MDB". |

## Recommended workflow order

Articles → Class Creation → Properties & Values → Text → Relations / Relation Objects → Pricing / Price Export. Pricing Relation / VARCOND can then be exported for complete selected prefix groups. Each step reuses the same product MDB session.

## Session persistence

One JSON file per product in `%LOCALAPPDATA%\MK Product Workbench\export_sessions\`
(file name = hash of the product key = PDM product id, else product code). It holds paths,
numeric ids and source→MDB id maps only. On recovery `get_active()` raises if the MDB is
gone (never treated as "first export"); the Articles export also verifies the MDB still holds
the recorded package id. `discard()` forgets a session but never deletes an MDB.

## Initialization (first export only)

Template chosen by the existing logic (`generation_template` → product category keywords →
`_template_for_kind`). The template is copied to `<dest>.init`; the template's example-product
rows are removed and Package / ComGroup renamed in **one transaction**; the staging file is then
moved into place and the session saved. Failure at any step leaves nothing at the destination.
An existing file at the destination is never overwritten. The example rows' NOT-NULL boilerplate
is captured first (prototypes) because the rows no longer exist afterwards.

## Articles workflow

Selected articles only (Articles page Export checkboxes) → one MDB row per base article code
(same price-base slicing as the full exporter, so prices later line up).

Tables written: **`tCOMd_Article`** and **`tCOMd_CodeScheme`** only.

`com_CodeSchemeID` is a mandatory reference, so the minimum scheme per article is written:
name = the article's scheme (default: its code), body = `@,@,…` (one `@` per code character), plus
template boilerplate. Property tokens in the body belong to Class Creation, which will extend them.
Article text / relation-object links are reused when already present, otherwise left NULL for the
Text / Relation workflows.

Identity: a row is found by the id retained in the session, else by `(package, article code)`.
Existing rows are updated only where a field differs, and the primary key never changes. A retained
id whose row has vanished is re-used for re-insertion; an id now owned by a different code, or
duplicate codes, are skipped with a warning. Writes are one transaction followed by a read-back check.

Result: inserted / updated / skipped (unchanged + ambiguous) / schemes created, MDB path.

## Legacy full export

`OcdExportService.export()` is unchanged in purpose (it copies a template and rebuilds everything),
but `_build()` now accepts `selected_article_ids`, and the export refuses to target an active session MDB.

## Implemented: Class Creation

Class Creation uses the Export-column article selection from the Articles page.
One selected source article resolves only its related classes; multiple selected
articles resolve the union of their related classes. When several selected
variants share one base article, their class links are unioned and linked once
to that retained MDB Article row.

The incremental workflow inserts only **`tCOMd_Class`** and
**`tCOMd_ArticleClass`** rows, and extends the selected **`tCOMd_CodeScheme`**
bodies in place. It reuses existing Class IDs, Article IDs and CodeScheme IDs,
adds only missing class rows and article/class links, and never deletes
unrelated rows. When selected variants share a class name, their property
assignments are unioned on detached class copies so the source engineering
snapshot is not mutated. Properties and values belong to the following Properties & Values workflow.

The Class Creation page uses the same selected article IDs to filter the
Attribute and Options workspaces. Visual definitions remain product-wide.
The export preview and actual write use the same selection and mapping.

Value Combination tables are explicitly outside the current implementation
scope.

## Implemented: Properties & Values

The Class Creation page exposes a separate **Export Properties & Values** action. It uses the
same Articles-page Export checkboxes and the same selected-article class mapping as Class Creation.
One selected article exports only its related class properties; multiple selected articles union
their related properties and values.

The workflow requires Articles and Class Creation to have run first. It inserts only missing
`tCOMd_Property` and `tCOMd_PropValue` rows, reuses existing class/property/value identities,
and writes both tables in one transaction with read-back verification. Existing Text and Relation
Object references are reused only when an unambiguous matching row already exists; otherwise
those fields remain NULL for their owning workflows. It does not write Text, Relation, Article,
Class, CodeScheme, Price, or Value Combination tables.

## Implemented: Relations / Relation Objects

The Relation page's Export to MDB action now uses the active product session and the Articles-page Export selection. It selects relation objects by article, article/class, property or value bindings; unbound authored relations are treated as product-level. It inserts only missing tCOMd_RelObj, tCOMd_Relation and tCOMd_RelObjRel rows, retains existing IDs, updates changed relation bodies in place, and resolves source property/value identities through class/property/value natural keys before updating com_RelObjID references. Class Creation and Properties & Values must exist first when a relation binds to those entities. A relation object shared beyond the selected article set is rejected rather than partially linked. The write is transactional and followed by package-scoped read-back checks.

## Implemented: Pricing Relation / VARCOND

The Maintenance Pricing Relation action now generates VARCOND relations for the selected Articles-page scope and writes them into the same product MDB session through the Relation exporter. Because each VARCOND relation is shared by every article in its prefix group, a partial group selection is rejected; users must select all articles in each affected group. Existing Relation Object and Relation IDs are reused, changed relation bodies are updated in place, and article relation links are updated transactionally. Development retains its existing full-export flow.

## Implemented: Text

The Text page's Export to MDB action now uses the active product session and the same Articles-page selection. It exports selected base-article descriptions and selected class property / option text blocks. Existing Text IDs are retained; changed translations are updated in place; missing rows are inserted. It then links selected Article, Property and PropValue rows to their Text IDs. Price text remains owned by the pricing exporter. Text reads are package-scoped, with a separate global TextID maximum query.

## Implemented: Pricing / Price Export

In Maintenance, the Pricing export / preview workflow now uses the active product MDB session rather than asking the user to choose a second MDB. It requires the Articles-page selection and filters article price records to selected base article codes; global price records remain product-level. Existing price-list target review, preview digest, non-destructive price upsert and read-back verification remain in use. Successful exports are recorded in session workflow status. Development's existing destination-file flow is unchanged.

## Performance work

- Text reads are scoped to the active package; TextID allocation uses a separate global MAX query so IDs remain unique without reading every Text row.
- Relation Object, Relation, Article, Class, Property and Value reads are scoped to the active package and related rows.
- Relation and Text exporters build in-memory indexes for class/property/value natural-key lookups instead of repeatedly scanning the same MDB row lists.
- Price export keeps the existing optimized MDB reads and filters article price records to selected base article codes before preview/write. Product-level global prices remain included, including global-only exports.
- Price computation processes up to two batches concurrently, with one PDM connection owned by each worker. Results are emitted in original item order; the final product-code lookup opens its own connection only after the workers finish.
- The concurrency regression test verifies two overlapping worker connections, stable result order and connection cleanup. Worker cancellation is checked immediately after the PDM base-price query returns, before result processing or another query. A live SQL Server timing benchmark on representative large products remains pending.
- Relation links are deduplicated in memory before transactional inserts.

## Validation status

Evidence below was produced locally on Windows 11, 64-bit Python 3.12.0, `QT_QPA_PLATFORM=offscreen`, at commit `ca9d56b` (branch `feature/incremental-class-creation`). No GitHub Actions run has been verified for this commit from this environment (`gh` is not installed); CI status is **pending**.

| Gate | Result | Level |
|---|---|---|
| Focused incremental MDB + pricing set (the workflow's command) | 158 passed, 6 subtests, 2.4 s | unit/simulated |
| `tests/test_mdb_export_session.py` against real 32-bit ACE (PowerShell 32) on **generated stand-in templates** | 14 passed, 718 s (each test 60-95 s) | integration, real ACE; NOT the real ProductStudio template |
| Whole suite, one process per test file (all files except the session file above) | 5,510 passed, 12 failed, 15 skipped | mixed |
| Whole suite in a single process | aborts with a Windows access violation inside `tests/test_pricing_worker_lifecycle.py::test_destroying_page_before_failure_reports_without_second_exception` (`QCoreApplication.processEvents`) in one run; the same file passes 3/3 in isolation; a second single-process run of `main` did not crash, so it is non-deterministic | Qt lifecycle, open |

### The 12 per-file failures are not caused by this branch
Seven files fail identically on `main` (805030a): `test_maintenance_snapshot_consistency` (3), `test_maintenance_source_tabs` (1), `test_maintenance_varcond` (3), `test_metatype_staged_writer` (1), `test_phase3_database_and_workspaces` (1), `test_workflow_shell` (2) all fail with the same counts on `main`; `test_module_home_page` fails 1 on the branch and 3 on `main` (flaky). Causes seen: tests referencing removed widgets (`ArticlesPage._actions_btn`, `PricingPage._pricelists_btn`), Windows path expectations in the Metatype/workspace tests, and the Maintenance VARCOND cache expectations. They are pre-existing and remain an **open gate**: they were not fixed here, and no test was removed or skipped.

### Not validated (external requirements)
- **Real ProductStudio MDB template**: none is in the repository or workspace. Stages other than Articles/session have not been run against the real schema; do not claim ACE parity for Class Creation, Properties, Text, Relations, Pricing or VARCOND until run with the real template under 32-bit Python + ACE.
- **Live PDM pricing benchmark**: not run. Required: reachable SQL Server PDM; run the pricing compute for one large product with the 1-worker and 2-worker code paths and record wall time.
- **Windows click-through of the packaged app** and **pCon.basket** opening of the final MDB: pending, require a human on a machine with the packaged build and pCon.basket.

Value Combination tables remain explicitly out of scope. Do not use the legacy full exporter for these incremental workflows.
