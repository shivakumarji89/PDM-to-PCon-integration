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

Class Creation uses the Export-column article selection from the Articles page.
One selected source article resolves only its related classes; multiple selected
articles resolve the union of their related classes. When several selected
variants share one base article, their class links are unioned and linked once
to that retained MDB Article row.

The incremental workflow inserts only **`tCOMd_Class`** and
**`tCOMd_ArticleClass`** rows, and extends the selected **`tCOMd_CodeScheme`**
bodies in place. It reuses existing Class IDs, Article IDs and CodeScheme IDs,
adds only missing class rows and article/class links, and never deletes
unrelated rows. Properties and values belong to their own later workflows.

The Class Creation page uses the same selected article IDs to filter the
Attribute and Options workspaces. Visual definitions remain product-wide.
The export preview and actual write use the same selection and mapping.

Value Combination tables are explicitly outside the current implementation
scope.

## Remaining workflows

Properties, Values, Relations, Text and Prices still need incremental session
exporters. Each must reuse the same product MDB and must not call the legacy
full exporter. Value Combination tables are excluded from the current scope.
