# ProductStudio incremental MDB export

**Rule: one product → one MDB → each workflow adds its own data.** The template is
copied once; later workflows never re-copy it, never wipe it and never renumber keys.

## Components

| Piece | Role |
|---|---|
| `models/mdb_export_session.py` | `MdbExportSession`: MDB path, package / ComGroup / manufacturer ids, template boilerplate rows, `article_map`, `scheme_map`, `workflow_status`. |
| `services/mdb_export_session_service.py` | Product key, persistence, recovery, one-time `initialize()`, `record_workflow()`. |
| `services/article_mdb_export_service.py` | `export_to_session()` — Articles workflow. |
| `services/class_creation_mdb_export_service.py` | `export_to_session()` — Class Creation, properties, values, code-scheme extension, ArticleClass and ArtBase. |
| `services/mdb_service.py` | Unchanged: the only MDB I/O gateway (transactional `execute_batch`). |
| `ui/main_window.py::_on_export_articles_to_mdb` | Dialogs only; called from the Articles page "Export to MDB". |

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

Class Creation reads `session.article_ids()` and incrementally upserts Classes,
Properties, PropValues, CodeSchemes, ArticleClass and ArtBase. It uses
`engineering_class_service.get_classes(snapshot)` and the Development
`OcdExportService._code_schemes()` mapping. Existing primary keys and
unrelated rows are preserved. Text and Relation records are not created by
this workflow; their IDs are linked only when already present.

The UI export action requires an existing Articles-created session MDB. It
previews the operation counts and warnings before asking for confirmation.
All writes run in one MDBService transaction followed by table read-back.

## Remaining workflows

Value-combination tables, Relations, Text and prices still need incremental
session exporters. Each must reuse the same product MDB and must not call the
legacy full exporter.
