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

In an **attached production workspace** the Text stage follows the text-preservation policy (below): existing populated text is kept, never overwritten by a normal export.

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

Evidence was produced locally on Windows 11, 64-bit Python 3.12.0, `QT_QPA_PLATFORM=offscreen`. Commit `9e79d52` (branch `feature/incremental-class-creation`) is the tested tree. No GitHub Actions run has been verified (`gh` is not installed here); CI is **pending**.

| Gate (commit `9e79d52`) | Result | Level |
|---|---|---|
| Focused incremental MDB + pricing set (the workflow's command) | 158 passed, 6 subtests, 2 s | unit/simulated |
| The 7 previously failing files (snapshot consistency, source tabs, Maintenance VARCOND, Metatype staged writer, home page, Phase 3 workspaces, workflow shell) | 189 passed, 0 failed | unit/UI |
| Whole suite, **one pytest process** (`python -X faulthandler -m pytest -q tests`) | 5,536 passed, 15 skipped, 22 subtests, 0 failed, exit 0, 783 s | mixed |
| Whole suite, **one process per test file** (174 files) | 5,536 passed, 15 skipped, 0 failed, every file exit 0, 1,310 s | mixed |
| `tests/test_mdb_export_session.py` on real 32-bit ACE with generated stand-in templates (inside both runs above) | 14 passed, about 12 min | real ACE; NOT the real ProductStudio template |

### The 12 earlier failures
All were reproduced on the branch, compared with `main` (`805030a`) and root-caused. Only one was a production defect.

| Test(s) | Cause | Kind |
|---|---|---|
| `test_maintenance_varcond` x3 | Fake `_load_live` lacked the `progress_callback`/`source_callback` added in `0bceb99`, so every load raised; tests also drove the Generate button/prefix field removed in `02109aa` and assumed PDM is read on selection (it is read once when the workflow opens). | obsolete test |
| (found while fixing the above) Development VARCOND | Since `a52c937` selecting a relation only displayed cached rules, so in Development a second relation stayed on "Waiting for this relation to finish loading" forever. Fixed in `VarCondGenerationPanel._on_relation_changed`: generate on selection when not cached; cached rules are dropped when prefix length, filter, exclusions or substitutions change (they were previously served stale). `test_varcond_background` expectations were updated (selection generates; return to a superseded relation regenerates). | **production defect** |
| `test_workflow_shell` x2, `test_maintenance_source_tabs` x1 | `_actions_btn` became `_actions_combo` (`8341429`), `_pricelists_btn` was removed (price lists live in the Pricing export, `0b48c7e`), `_group_class_check` was removed (`76623ff`), the toolbar has a leading stretch, and rows are always grouped so column sorting is off. | obsolete test |
| `test_maintenance_snapshot_consistency` x3 | Articles always insert Class Creation group header rows (`76623ff`); tests counted them as articles. | obsolete test |
| `test_phase3_database_and_workspaces` x1 | Knoll default workspace deliberately corrected in `a1a92d6`. | obsolete test |
| `test_metatype_staged_writer` x1 | Review text shows the resolved real path; on Windows `realpath` normalises directory case (`pytest-of-SIAOCA`). | Windows path |
| `test_module_home_page` x1 (3 on `main` under load) | Product page intentionally has Refresh PDM, not Reload; the intermittent extra failure was `MainWindow`'s Product page loading the catalogue from live SQL Server when the on-disk registry cache is stale, overrunning the 10 s thread-pool drain. The tests now stub the catalogue load. | obsolete test + isolation |

Module order on the home page is unchanged and still asserted.

### Qt access violation (open, not reproduced)
One earlier single-process run on this branch, and one on `main`, aborted with a Windows access violation inside `QCoreApplication.processEvents` in `test_pricing_worker_lifecycle.py::test_destroying_page_before_failure_reports_without_second_exception` (the test deliberately deletes the page mid-run). It could **not** be reproduced afterwards: the file passed 80/80 times under 4x concurrency; the Pricing/VARCOND group passed 4/4 in one process; the preceding-files prefix run passed on the branch (1,715) and on `main` (no crash, 16 failures); the complete single-process run on `9e79d52` passed. Re-checked on `cd6bc19`: `test_pricing_worker_lifecycle.py` passed 40/40 in separate processes with `-X faulthandler`, while the whole suite ran concurrently; two further complete single-process runs (with faulthandler) finished without a crash. Still not reproduced, so still **not proven fixed**. A possible contributor is state leaked by the failing tests that are now fixed, but this is a hypothesis. Keep running the full suite in one process in CI and treat any recurrence as a release blocker.

### Real ProductStudio MDB validation (2026-11-19)

Harness: `scripts/validate_real_mdb_incremental.py` (32-bit ACE bridge). Every write goes to a **copy** under a temp folder outside the repository and outside the SVN workspace; source != destination is asserted before any write, the source SHA-256 is recorded before/after (unchanged in every run), the session store is a temp folder, and nothing copied is committed. After each stage the harness re-reads **every table** and records: rows added/changed/removed, FK orphans over all 52 foreign keys and duplicates against every unique index. Per stage it checks: dry run writes nothing; an injected failure in the transaction rolls back with zero writes; a first batch, then the full selection (adds only the missing rows, earlier rows untouched); a repeat is a no-op.

Sources (read-only, copied): `...\WS\Seating\Seating\Dalby` (primary), `...\Lino` (secondary), `...\WS\1_WS_Templates\{Seating_Template,Tables_Template,Seating_N1_Template}`. All five OCD MDBs share an identical 50-table / 52-FK schema (Seating_Template lacks the unrelated `Plakfouten` table). Live PDM supplied the Dalby family (26 articles) and Lino family (104 articles) read-only, with the cache save stubbed.

| Scenario | Result |
|---|---|
| `initialize()` on real **Seating_Template** | OK. Cleared exactly the 12 example-product tables (4 articles, 20 relations, 7,784 prices, 112 texts ...), kept all reference tables, only Package and ComGroup changed (renamed), 0 FK/unique violations, session recovered after restart, template copy untouched. |
| `initialize()` on real **Tables_Template** | Refused cleanly: `Template tCOMd_Package is empty.` No file, no session. The legacy full export refuses the same template with the same message, so this is a template-content gap, not a regression. |
| Seating_Template -> 10 Dalby articles: Articles | 10 inserted + 10 code schemes; repeat no-op; rollback 0 writes. |
| Class Creation | 2 classes, 20 ArticleClass links, 10 code schemes updated in place; repeat no-op. |
| Properties & Values | **Failed on the real schema** (defect, below), then 6 properties + 31 values after the fix; repeat no-op. |
| Text | 57 texts + property/value/article links; repeat no-op. |
| Relations | 1 relation object, relation and link; repeat no-op. |
| Pricing (live PDM, 1,588 records) | 572 prices inserted for the selected articles; repeat reports all as existing. |
| **Dalby (attach), Articles** | 25 of 26 articles matched by natural key and left untouched (IDs preserved), 1 inserted. |
| Dalby, Pricing | Live-PDM prices equal production: 1,532 of 1,588 identical to the MDB, 0 updated, 56 inserted for the new article; idempotent. |
| Dalby, VARCOND relation writer | Identical relation skipped; changed body updated in place (ID kept); see rebinding finding. |
| **Lino (attach)** | Articles / Pricing (276 prices) / VARCOND writer behave as above; Class Creation blocked (below). |

Findings:
1. **Defect, fixed** - Properties & Values wrote `NULL` into `tCOMd_Property.com_PropInfoPicPrefix` for properties with no source property object. The real column is a required text field (real rows hold `''`); the full export always writes a string. Stand-in test schemas had no such constraint. Now a string is always written (`tests/test_properties_values_mdb_export_service.py`, both variants fail without the fix). The dry run cannot detect NOT-NULL violations; the real write fails atomically with a clear message.
2. **Design gap - resolved by decision 1 below (CodeScheme clone-on-write).** Class Creation required one CodeScheme *named after each article code*; real workspaces share schemes (Dalby: 26 articles on 2 schemes `NODLE100`/`NODLE300`; Lino: 3 on `LINO`), so on an attached MDB it stopped with `Expected one existing CodeScheme named '...'` and the stages behind it stopped too.
3. **Rebinding of existing articles - resolved by decision 2 below (relation-object links are preserved).** Lino `MI1E3` was re-pointed from `P_PRICING_CHAIR` (a real price relation) to `P_MI1E3` (an object with no relation) and Dalby articles from the shared `P_PRICING_DALBY` to per-code objects. The first fix only warned; the writer now no longer changes the link.
Regression after these changes: targeted export-service tests 200 passed (153 s); whole suite in one process `python -m pytest tests -q` -> **5539 passed, 15 skipped, 0 failed, exit 0, 1207 s** (previous 5536 + 3 new tests; run under concurrent ACE load, hence slower than the earlier 783 s).

4. VARCOND *generation* was not exercised: Dalby and Lino snapshots have no super-product BOM (`article_components` empty). Only the writer path was tested, with relation objects in the real Dalby body format.

### Approved decisions and their implementation (2026-11-19)

**Decision 1 - CodeScheme clone-on-write** (`services/class_creation_mdb_export_service.py`, `_plan_code_schemes`).
- Each selected article is resolved through its own `com_CodeSchemeID` (the name lookup `scheme == article code` remains only for an article that has no scheme link). An unresolvable id, a scheme outside the package, a clone-name clash with a different body, or a pattern-length mismatch fail with a clear error before anything is written.
- Scheme used **only by selected articles** -> updated in place; the existing body is kept verbatim and only the missing `CLASS:Property` tokens are appended (`TOKEN, ,TOKEN` form), so a production body's spacing is never rewritten.
- Scheme **also used by unselected articles** -> cloned: the original and every unselected article stay untouched; the clone copies the original's settings, carries the original body plus the new tokens, and only the selected articles are reassigned to it. If the shared scheme already carries every needed token, nothing is written.
- Deterministic identity: `<root name>_CS<first 8 hex of sha1(clone body)>` (root = scheme name without a previous suffix, truncated so the name stays within the 30-character column). Selected articles with the same class needs therefore share one clone, a later export finds and reuses it (`code_schemes_clone_reused`), and a repeat creates no scheme and no link. The multiple-variant class union (several source articles on one base article) is unchanged.
- Result counts: `code_schemes_updated`, `code_schemes_cloned`, `code_schemes_clone_reused`, `articles_reassigned`; the preview warning names the scheme, the number of unselected users and the clone.
- The Articles stage preserves a non-null article scheme link in attached mode, so re-exporting Articles cannot revert a clone assignment.

**Decision 2 - existing relation-object links are preserved** (`services/relation_link_policy.py`; `attached_existing` flag on the session, set by `attach_existing`; sessions created from a template keep the previous "incoming wins" behaviour).
- Articles stage, and the Relations / VARCOND writer (article, article-class, property and value links): an existing **valid** link (its target row exists) is kept; a link is created only when it is NULL or dangling; a differing incoming link is a **conflict** reported in `result["conflicts"]` and in the preview/result dialogs with both ids, names and relation information (relation name, type, domain, order). The Relations / VARCOND preview dialogs and the Articles result now list the kept links.
- Replacement exists only as the keyword `replace_existing_links=True` on the services - a separate, explicit operation that no export button passes. Repeated exports keep the same link and are no-ops. The relation description is read lazily (only when a conflict exists) so a minimal schema still exports.
- A new relation object / relation (e.g. a generated `P_PRICING_<code>`) is still created and its body updated; only the *article's link to it* is preserved.

Evidence (isolated copies, source SHA-256 identical before/after every run and again when re-hashed at the end; no lock files left beside the originals):

| Scenario (real MDB copy) | Result |
|---|---|
| Dalby: `NODLE100` alone (shares `NODLE100`/6335 with 8 articles), then + `NODLE110`, + `NODLE300/310/320` | Clone `NODLE100_CS729461aa` for 100 and 110; second clone `NODLE300_CSd982aa29` shared by 300/310/320 (multiple selected on one scheme). Exactly those 5 articles reassigned (only `com_CodeSchemeID` changed); both original schemes and the 21 other articles untouched; 0 relation-object links changed; repeat no-op; FK/unique clean. |
| Dalby: all 9 users of scheme 6335 selected | In place, extended only; no clone, no reassignment; the other scheme untouched. |
| Lino: `MI1E3`, then + `MI2E3` (share `LINO` with unselected `MI7E3`) | Clone `LINO_CS28742d7f` for the 2 selected; `MI7E3` and `LINO` unchanged; `MI1E3` keeps `P_PRICING_CHAIR` (Articles and VARCOND writer both report it preserved). |
| Dalby + Lino: Properties, Text, Relations, Pricing, VARCOND after Class Creation | Pass (Lino 12 properties/800 values/792 texts/25 relation objects; Dalby 6 properties/26 values/25 texts), each stage idempotent, rollback leaves 0 writes. |
| Seating_Template initialized (10 articles) all 7 stages | Same result as before the change: 10 articles, 20 class links, 6 properties/31 values, 57 texts, 1 relation, 572 prices, no clone; invariants clean. |

Regression on `cd6bc19` (all on the existing branch, nothing pushed): focused CodeScheme/Class Creation/Articles/Relations tests pass; the CI workflow set (12 files + the 2 new ones) **191 passed**; the real-ACE `tests/test_mdb_export_session.py` **14 passed (5m42s)** after a regression the first full run exposed (my lazy relation-info read - the stand-in templates lack `tCOMd_RelObjRel` columns; fixed and covered by a minimal-schema test); whole suite in one process `python -X faulthandler -m pytest tests -q` -> **5570 passed, 15 skipped, 0 failed, exit 0, 1111 s**. The earlier unexplained background "exit 1" (a `nohup python ... &` launch with a concurrent job, no traceback) was re-attempted in the same shape and did not recur; every later background run logged `rc=0`. It is documented as not reproduced.

Further defect found and fixed by this revalidation: the **Text stage** looked a value up with the `#` removed from its code while Properties & Values had stored `1FD#`, so it refused on the real Lino MDB; the stored code is now tried first (`TextMdbExportService._value_rows`).

Findings that need a decision (not changed):
- **Text content in attached workspaces.** The Text stage updated 11 existing Dalby texts (and 4 on Lino), replacing e.g. the long description `Dalby Circular Coffee Table / 650mm` with the engineering text block's default `NODLE100`. Text comes from the Text workflow's blocks; with uncurated defaults it overwrites curated production text. The relation-link policy (preserve, report conflict, explicit replace) is the obvious candidate to extend to texts.
- **Class naming.** Production classes are `DALBY_ATTR`/`DALBY_OPT`; engineering creates `Dalby_Attribute`/`Dalby_Option`, so Class Creation on an attached workspace adds classes beside the existing ones.
- **Pricing on Lino** updated 3,472 existing prices: the live PDM has newer values than that obsolete workspace (Dalby: 0 updated, all identical). This is what a price update does, but note it for attached production files.
- Lino "all users selected" cannot be reproduced on real data (the live Lino family has no `MI7E3`); it is covered by unit tests and by Dalby.

### Decision 3 - existing production text is preserved (`services/text_preservation_policy.py`)

Status: **implemented, unit-tested** (`tests/test_text_preservation.py`, 12 tests); real-ACE evidence below.

Natural key of a text row: `(com_TextTypeCode, com_TextName)` within the package (e.g. `artlong/NODLE100`); it is read per language column (`com_Text_1_<lang>`). Text IDs, the other language columns and unrelated rows are never touched.

| Situation (attached session) | Behaviour |
|---|---|
| Existing populated value, incoming differs | **Preserved**; conflict reported (text id, key, language, existing and incoming value) in the preview and the result (`conflicts`, `warnings`, counts `texts_preserved`) |
| Text row missing | Created |
| Existing value empty / NULL | Populated |
| Incoming value blank | Never erases an existing value |
| Existing valid article / property / value text link differing from the incoming link | Preserved and reported (`text_link` conflict), via `relation_link_policy.decide`; NULL or dangling links are set |
| Explicit authorization `replace_existing_text=True` | Replaces; reported as `replaced`. Only a service keyword - **no export button passes it** |
| Repeated export | Same result, no writes; the preserved conflicts are still listed |
| Template-initialized session | Unchanged behaviour (incoming wins, no conflicts reported) |

The Text preview dialog lists the preserved values under "Existing production text (kept, NOT overwritten)". A failed transaction writes nothing (existing transactional batch).

**Legacy sessions.** A session file saved before the `attached_existing` flag existed lacks it. It is not guessed: `MdbExportSession.from_dict` sets `attached_flag_known=False` (persisted, so a re-save does not turn the unknown into a "known template"), the session is treated as template-initialized (previous behaviour) and the Text preview warns first. `MdbExportSessionService.declare_attachment(session, attached)` records the explicit answer once; it refuses to rewrite a known flag. No UI action calls it yet - **owner decision / follow-up** (a one-line confirmation dialog on the warning is the proposed UI).

**Real-ACE evidence (isolated copies, 2026-11-19; harness `scripts/validate_real_mdb_incremental.py`, new `--force-unattached` / `--unattached-stages`).** Live PDM snapshots rebuilt for the run (Dalby 27 NODLE products = 26 workspace articles + 1 new; Lino `MI1E3/MI2E3/MI7E3`). Class Creation and Properties & Values were run as unattached only to build the classes the identity stop would otherwise refuse; Text ran attached.

| Workspace / mode | Existing text cells changed | Populated values overwritten | New text rows | Other |
|---|---|---|---|---|
| Dalby, **attached policy** | 0 | **0** | 47 | 32 conflicts preserved (e.g. `Access_Cutout_NC`: existing "No cutout - NC" kept, incoming "No cutout" not applied) |
| Dalby, legacy behaviour (`--force-unattached`) | 36 | **32** | 47 | e.g. `Dalby Circular Coffee Table / 650mm` -> `NODLE100` |
| Lino, **attached policy** | 0 | **0** | 792 | |
| Lino, legacy behaviour | 5 | **5** | 792 | |

The counts differ from the earlier 11 (Dalby) / 4 (Lino) because the snapshots were rebuilt and select a different text-block set; the overwrite itself is reproduced. First attached run exposed a further defect: the writer **renamed existing text keys by case** (`Cable_leg` -> `Cable_Leg`, 4 rows on Dalby); fixed (existing key spelling is never changed in attached sessions) and re-run: 0 changed cells. Per stage: dry run 0 writes, injected failure 0 writes, repeat no-op, 0 FK orphans / unique violations.

Class identity on real data (attached, Class Creation alone): Dalby and Lino both stop with `Class identity cannot be established, nothing was written ... no reliable mapping exists` for `Dalby_Attribute/Dalby_Options` vs `DALBY_ATTR/DALBY_OPT` and `Lino_Attribute/...` vs `LINO_ATTR/LINO_OPT`; first-batch and full-selection deltas empty. Source SHA-256 before and after: Dalby `18bcb07e2014...`, Lino `87926b2a69f6...` (unchanged; the `.ldb` beside Lino pre-existed).

**Validation levels.** Implemented + unit-tested + real-ACE validated (isolated copies): text preservation, key-spelling preservation, class identity stop. Unit-tested only: legacy-session flag handling, `replace_existing_text`. NOT validated: packaged application, pCon.basket, CI on the final commit.

**Not changed / open.** Lino pricing (3,472 updates) is unchanged and undocumented as defect: live PDM is newer than that workspace; no price-conflict preview exists yet and no evidence was gathered to change it. BOM-based VARCOND generation still needs a product with a super-product BOM (`article_components` populated). Tables template still has an empty Package table; no seed invented. Pricing-page crash, Qt access violation and live 1-vs-2-worker pricing benchmark were not investigated/run in this pass.

### Production class identity (`services/class_creation_mdb_export_service.py`)

Status: **implemented as a safe conflict, unit-tested** (`tests/test_class_production_identity.py`, 7 tests). **Reuse by mapping is NOT implemented, because no reliable mapping exists.**

Findings (real Dalby and Lino copies, live PDM):
- `tCOMd_Class` carries only `com_ClassID`, `com_ClassName`, `com_PackageID` (+ status/tmp columns): no code, reference or alias.
- Dalby: `DALBY_ATTR` (6 properties `Series, TTSH, TTSZ, Table_type, Access_Cutout, Cable_leg`) and `DALBY_OPT` (6: `Frame_Finish, Top_Finish, Bottom_Material_G, Bottom_Stright_Edge, Bottom_WFT, PLC`), each linked to all 26 articles. Lino: `LINO_ATTR` (6), `LINO_OPT` (9), linked to its 3 articles.
- Engineering generates `Dalby_Attribute` (`Series, Type`), `Dalby_Options` (`Frame finish, Top material, Access cutout, Cable Leg`) and `Dalby_Visual` (empty). Engineering class ids are random GUIDs. Property membership differs from production (e.g. `Cable Leg` is an option in engineering but an attribute in production), so structural equivalence cannot be proven either.
- Nothing in PDM or in this application records which production class an engineering class corresponds to.

Behaviour in an attached session: classes are matched by exact (case-insensitive) name only; a match is reused with its ID and name preserved and no duplicate. If an incoming class is new by name while a selected base article is already linked to production classes this export does not resolve, the export stops with an `class_identity` conflict (article, incoming classes, existing production classes) and **writes nothing** (also in the preview). Articles with no production classes, and unselected articles, are unaffected. Template-initialized sessions keep the previous behaviour. Later stages (Properties & Values, Text) then stop on "Class Creation must be exported first" instead of building on duplicate classes.

**Proposed mapping mechanism (not implemented, needs owner approval).** An explicit, deterministic map `{engineering class name -> production com_ClassName}` stored in the export session (`MdbExportSession.class_map`, default `{}`; persisted in the session JSON, so no schema migration of the MDB and old sessions load with an empty map), created by a Class Creation review dialog that lists the unresolved pairs with both property lists and requires the user to confirm each, and shown in the session summary. Writers would resolve a class through the map first, then by exact name, and fail with the conflict otherwise; `discard()` forgets it with the session. The map would have to be honoured by Class Creation, Properties & Values, Text and Relations (they all look classes up by name today). Properties of a mapped class that exist only on one side would still need a decision (add to production class vs ignore).

### Not validated (external requirements)
- **Real ProductStudio MDBs**: now exercised - see "Real ProductStudio MDB validation" below. Not yet validated: Class Creation / Properties / Text / Relations on an *attached production workspace* (blocked by the shared-CodeScheme gap), BOM-based VARCOND *generation* (Dalby and Lino have no super-product BOM), the Tables template (empty Package table).
- **Live PDM pricing benchmark**: not run. Required: reachable SQL Server PDM; run the pricing compute for one large product with the 1-worker and 2-worker code paths and record wall time.
- **Windows click-through of the packaged app** and **pCon.basket** opening of the final MDB: pending, require a human on a machine with the packaged build and pCon.basket.

Value Combination tables remain explicitly out of scope. Do not use the legacy full exporter for these incremental workflows.
