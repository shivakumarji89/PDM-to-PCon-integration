# Application-wide cancellation

## Contract

Cancel requests cooperative cancellation of the operation named by the control.
It is not a successful completion, an error, or merely a hidden progress window.
Workers are never terminated forcibly. An operation remains busy until its worker
has unwound and released its resources; retry uses a new run and a new token.

Closing the shared progress **monitor** hides it; it intentionally does not cancel
the operation. Its Cancel button cancels the bound operation. Hiding a workflow
page to navigate elsewhere likewise permits its task to finish in the background.
Destroying a task's owning widget requests cancellation where results would no
longer have a consumer, without destroying objects still used by its worker.

## Mechanism

- [`core/cancellation.py`](../../core/cancellation.py) defines an Event-backed,
  thread-safe `CancellationToken` and the distinct `OperationCancelled` exception.
  Repeated requests are harmless. `checkpoint()` raises only for a requested token.
- `cancellation_scope(token)` propagates the token through synchronous service
  calls on a worker using a `ContextVar`. This preserves existing service APIs.
  New threads must receive their operation control explicitly; context propagation
  is not assumed across executors.
- `commit()` atomically checks cancellation and closes the cancellation window
  before an indivisible final publication. If cancellation wins, publication never
  starts. If publication wins, late Cancel cannot relabel committed work as cancelled.
- [`BackgroundTask`](../../ui/workers/background_task.py) accepts an optional
  `cancellation_token`, checks before invoking work and before returning success,
  and emits exactly one of `finished`, `failed`, or `cancelled`. GUI-thread delivery
  suppresses queued progress after cancellation and all signals after a terminal
  outcome. Genuine exceptions retain the failure path.
- `ReportedTask` owns its reporter and signal receivers under the application task
  host, not a page. It guards callbacks against destroyed Qt owners, releases the
  reporter/timer after worker completion, and restores UI state through separate
  success/failure/cancellation callbacks.
- [`ProgressReporter`](../../core/progress.py) owns the token; `begin()` cannot
  erase an early request. Worker progress boundaries observe the scoped token.
  Cancellation/failure does not force the progress bar to 100%.
- OBX's pause-aware `ValidationControl` and SyteLine's `ExportJob` retain their
  public APIs while using the shared cancellation primitive.

Example for a service caller outside a Qt worker:

```python
token = CancellationToken()
with cancellation_scope(token):
    result = service.operation()
# Another thread calls token.request_cancel().
```

## Active-operation control inventory

All progress-popup rows below use
[`ProgressDialog._on_cancel_clicked`](../../ui/dialogs/progress_dialog.py),
which requests its bound reporter's token immediately. The button shows
Cancelling until a terminal outcome, then becomes Close.

| Control / workflow | UI handler and worker | Service and stopping boundaries |
|---|---|---|
| Compute Prices popup Cancel | [`pricing_page.py`](../../ui/pages/pricing_page.py), `_PricingRun`, `BackgroundTask` | [`PricingService`](../../services/pricing_service.py): currencies, base-price batches, per-item increments, queued record emission, and final snapshot publication |
| Load Family / Category / Catalogue / selected products popup Cancel | [`product_page.py`](../../ui/pages/product_page.py), `_on_load_family`, `ReportedTask` | [`PDMService`](../../services/pdm_service.py): article retrieval, detail retrieval, mapping, article-set building, engineering initialization, then publication |
| Add Family to Session popup Cancel, including range-completion calls using the same service | [`product_page.py`](../../ui/pages/product_page.py), `_on_add_family_to_session`, `ReportedTask` | Same service, working snapshot copy, query/mapping boundaries, engineering sync, then publication |
| Open Repository extraction popup Cancel | [`repository_workspace.py`](../../ui/widgets/repository_workspace.py), `_start_repository_extraction`, `ReportedTask` | Inspection, [`MDB reverse engineering`](../../services/mdb_reverse_engineering_service.py), mapping records/tables, engineering initialization; no partial registration |
| Article OBX Generator / Build Permutations popup Cancel | [`article_obx_generator_page.py`](../../ui/pages/article_obx_generator_page.py), `ReportedTask` | [`ArticlePermutationService`](../../services/article_obx/article_permutation_service.py): recursive property choices, option combinations, articles, and result return |
| CET SIF validation popup Cancel | [`cet_sif_validation_page.py`](../../ui/pages/cet_sif_validation_page.py), `ReportedTask` | [`SifValidationService`](../../services/sif_validation_service.py): currency groups, query windows, records and streamed results; connection closed on every outcome |
| OBX Validation Cancel, including while paused | [`obx_validation_page.py`](../../ui/pages/obx_validation_page.py), `_on_cancel`, worker rounds | [`obx_validation_service.py`](../../services/obx_validation_service.py), [`cancellable_sif_validation_service.py`](../../services/cancellable_sif_validation_service.py), [`cancellable_pdm_repository.py`](../../repositories/cancellable_pdm_repository.py): shared control, active cursor cancellation, worker drain and queued-result guards |
| SyteLine export Cancel / closing its active page | [`syteline_export_page.py`](../../ui/pages/syteline_export_page.py), export worker | [`ExportJob`](../../services/syteline_export/job.py) and [`pipeline`](../../services/syteline_export/pipeline/): queries, records, helper loops and stages; cancellation before publish discards staging |
| Price roll-over Scan / Apply popup Cancel | [`price_rollover_dialog.py`](../../ui/dialogs/price_rollover_dialog.py), `ReportedTask` | [`PriceUpdateService`](../../services/price_update_service.py): discovery, files, PDM lookup batches and rows, staged package writes; completed packages retained and counted |
| Base Length Check popup Cancel | [`base_length_check_dialog.py`](../../ui/dialogs/base_length_check_dialog.py), `ReportedTask` | Same service: packages, PDM lookups and records; cancellation prevents registry-write follow-up |
| Scan Versions / Update Version popup Cancel | [`version_update_dialog.py`](../../ui/dialogs/version_update_dialog.py), `ReportedTask` | [`VersionUpdateService`](../../services/version_update_service.py): folders, files, series and staged writes; committed series retained and counted |
| Loading Engine activity cancellation API | [`ActivityHandle`](../../core/activity/handle.py) | [`LoadingEngine`](../../services/loading/loading_engine.py): stages, indexes and products; returns `LoadResult(cancelled=True, ok=False)` without a snapshot |

No active Python UI uses `QProgressDialog`; the application uses its own shared
progress dialog. `OperationCard.cancel_requested` is reserved infrastructure:
the card has no Cancel button or menu action.

## Input and confirmation controls (not running-task cancellation)

These controls reject the pending choice before starting its associated work.
They intentionally do not cancel a different, already-running operation.

| Controls | Owning files / intended scope |
|---|---|
| Series selection Cancel | [`series_select_dialog.py`](../../ui/dialogs/series_select_dialog.py): discard pending package subset |
| Special-article mapping Cancel | [`special_article_dialog.py`](../../ui/dialogs/special_article_dialog.py): discard pending mapping; do not undo already committed roll-over packages |
| Metatype owner Cancel and write/replace confirmations | [`metatype_owner_dialog.py`](../../ui/pages/metatype_owner_dialog.py), [`metatype_creation_page.py`](../../ui/pages/metatype_creation_page.py): keep previous explicit choice / pending edits; do not start writes |
| PDM Maintenance Scope Cancel | [`pdm_maintenance_scope_dialog.py`](../../ui/dialogs/pdm_maintenance_scope_dialog.py): do not apply/load pending scope |
| Price-list manager Cancel | [`price_list_manager_dialog.py`](../../ui/dialogs/price_list_manager_dialog.py): close without applying pending proposals; explicit prior "Save Existing List Edits" remains committed |
| Pricing target-list Cancel | [`price_list_target_dialog.py`](../../ui/dialogs/price_list_target_dialog.py), [`pricing_page.py`](../../ui/pages/pricing_page.py): stop the export workflow before write; restore export controls |
| Unsaved Save/Discard/Cancel and XOCD export-options Cancel | [`main_window.py`](../../ui/main_window.py): abort pending navigation/close or pending export setup |
| Article-range exclusion Cancel | [`articles_page.py`](../../ui/pages/articles_page.py): do not apply pending exclusions |
| Class code-edit Cancel | [`class_creation_page.py`](../../ui/pages/class_creation_page.py): do not apply pending code edits |
| Review generation-options Cancel | [`review_page.py`](../../ui/pages/review_page.py): leave generation overrides unchanged |
| SyteLine configuration-choice Cancel | [`syteline_export_page.py`](../../ui/pages/syteline_export_page.py): discard pending configuration choice, not the separate active export |
| Repository browser Cancel and class-classification rejection | [`repository_workspace.py`](../../ui/widgets/repository_workspace.py): do not start extraction / do not publish the newly extracted snapshot |
| Native open/save/directory dialogs throughout import/export and project workflows | Empty/rejected selection exits before the selected read/write stage; previously committed stages are not rolled back |

The Maintenance Comparison, Maintenance Parity, Review preview, Pricing MDB
read/preview/write workers and product navigator/single-product loader do not
expose a running-task Cancel. Their successful and failure paths remain supported
by the shared background runner. The PDM Change Monitor has Close, not Cancel:
its worker was moved from a dialog-held `QThread` to the host-owned background
runner so closing/destroying the dialog cannot destroy a running thread.

## Safe boundaries and integrity

- CPU work stops at its next record/combination/stage check. Built-in sorts,
  serialization, a single file read/copy, and native calls finish their current
  indivisible call before a checkpoint can run.
- Ordinary PDM `pyodbc` reads check before execute, after execute and after
  fetch. An in-progress ordinary call is **not** claimed to be interrupted:
  it must return before cancellation unwinds and closes the connection. No
  cross-thread connection close or unsupported driver cancellation is attempted.
- OBX additionally uses the driver's supported `Cursor.cancel()` seam while
  tracking active cursors. The driver/server still determines when that call
  returns; cancellation cannot promise a fixed wall-clock deadline.
- MDB/ADODB bridge requests are indivisible native/external API calls. Cancellation
  is checked before and after the call; the current bridge request may finish.
  No subsequent mapping, query window, package or publication starts afterward.
- Pricing retains the complete snapshot baseline when cancelled. Streamed rows
  are provisional; cancellation restores the snapshot-backed view. Results for
  an old snapshot are never applied to a newly active snapshot.
- Cancellable family loads stage a new snapshot. Add-family stages a deep copy;
  existing members/collections are not incrementally mutated. Engineering runs
  before the final publication boundary. Non-cancellable service callers retain
  their existing behavior.
- Family cache output uses a same-directory temporary file and atomic replacement;
  cancellation or failure removes the temporary and leaves the final file intact.
  A fully constructed valid cache may survive cancellation before UI publication.
- Repository import retains the previous complete repository snapshot until the
  replacement has finished extraction and classification.
- Roll-over and version updates stage writes before publication. A package/series
  already committed remains valid when later work is cancelled. Cancellation
  reports completed counts rather than claiming that nothing was written.
  Individual replacements are atomic; a multi-file package replacement group
  is not power-loss atomic, and cancellation is deferred across that group.
- SyteLine writes to staging, releases its site lock and database sessions on
  unwind, and never publishes cancelled staging output. Final publication has an
  explicit non-interruptible commit boundary.
- Task-owned reporters, timers and signals survive destroyed widgets until their
  workers drain. No cleanup path kills a Python or Qt worker thread.

## Regression validation

New deterministic cancellation coverage:

- [`test_application_cancellation.py`](../../tests/test_application_cancellation.py):
  pre-start cancellation, repeated requests, commit races, retry, queued progress,
  database wait, cache integrity, snapshot staging, engineering-stage cancellation,
  worker lifetime and Loading Engine cancellation.
- [`test_cancellation_workflow_surfaces.py`](../../tests/test_cancellation_workflow_surfaces.py):
  actual CET/Article OBX/repository monitor Cancel controls, guarded retry,
  streaming results and recursive CPU checkpoints.
- [`test_price_version_cancellation.py`](../../tests/test_price_version_cancellation.py)
  and [`test_maintenance_dialog_cancellation.py`](../../tests/test_maintenance_dialog_cancellation.py):
  package/series cancellation, staged-file integrity and dialog lifecycle.
- [`test_obx_cancellation.py`](../../tests/test_obx_cancellation.py) and
  [`test_syteline_cancellation.py`](../../tests/test_syteline_cancellation.py):
  pause/cancel, worker draining, cursor tracking, pre-start cancellation,
  query/helper-loop checkpoints and publication races.
- Existing pricing lifecycle tests now expect real cancellation, not continued
  successful completion, when their page is destroyed.

Tests use thread events and controlled driver doubles rather than sleep-based
cancellation timing. Live PDM/SQL Server and Access/ACE interruption behavior
requires an environment with those systems; automated tests validate the precise
supported boundaries without claiming native calls were forcibly interrupted.

### Validation results

Run with `QT_QPA_PLATFORM=offscreen`:

| Validation | Result |
|---|---|
| Six cancellation regression files plus Pricing worker lifecycle | 105 passed |
| Focused OBX/SyteLine existing and new regressions | 2,981 passed, 16 subtests passed |
| Focused package/version and adjacent regressions | 86 passed |
| Focused shared/snapshot/Maintenance/Review regressions | 149 passed |
| Full application suite | 4,046 passed, 10 skipped, 22 subtests passed; 1 pre-existing failure |
| Shared token and worker syntax; changed PDM/worker API call-site compatibility | Passed |

The remaining full-suite failure is
`RepositoryLinkActionsTest.test_status_message_reflects_loaded_product` in
[`test_product_repository_link_actions.py`](../../tests/test_product_repository_link_actions.py):
its `SimpleNamespace` page double lacks `_refresh_maintenance_source_table`.
Both that test function and `ProductPage._on_shared_repository_loaded` were
AST-compared with `HEAD` and are unchanged. No unrelated fix was applied.

## Supporting files updated

The inventory above links the workflow entry points and primary services.
Additional shared and supporting changes:

- [`core/validation_control.py`](../../core/validation_control.py),
  [`services/loading/load_request.py`](../../services/loading/load_request.py).
- [`engineering_initialization_service.py`](../../services/engineering/engineering_initialization_service.py)
  and [`engineering_reduction_service.py`](../../services/engineering/engineering_reduction_service.py):
  cancellable engineering/member and article-set construction on staged snapshots.
- [`repositories/pdm_repository.py`](../../repositories/pdm_repository.py):
  ordinary read-query cancellation boundaries without changing SQL/pricing rules.
- [`ui/pages/syteline_export_worker.py`](../../ui/pages/syteline_export_worker.py):
  task-owned signals and guarded queued delivery.
- [`ui/dialogs/pdm_changes_dialog.py`](../../ui/dialogs/pdm_changes_dialog.py):
  safe background ownership for a monitor that permits work to continue on Close.
- SyteLine pipeline plumbing:
  [`db.py`](../../services/syteline_export/pipeline/db.py),
  [`run.py`](../../services/syteline_export/pipeline/run.py),
  [`run_base.py`](../../services/syteline_export/pipeline/run_base.py),
  [`bom_export.py`](../../services/syteline_export/pipeline/bom_export.py),
  [`helpers_fabric.py`](../../services/syteline_export/pipeline/helpers_fabric.py),
  [`helpers_misc.py`](../../services/syteline_export/pipeline/helpers_misc.py),
  [`io_output.py`](../../services/syteline_export/pipeline/io_output.py),
  [`netsem.py`](../../services/syteline_export/pipeline/netsem.py).
- SyteLine stage checkpoints:
  [`stage_p00_setup.py`](../../services/syteline_export/pipeline/stage_p00_setup.py),
  [`stage_p01_item_head.py`](../../services/syteline_export/pipeline/stage_p01_item_head.py),
  [`stage_p02_option_rows.py`](../../services/syteline_export/pipeline/stage_p02_option_rows.py),
  [`stage_p03_materials.py`](../../services/syteline_export/pipeline/stage_p03_materials.py),
  [`stage_p04_feature_templates.py`](../../services/syteline_export/pipeline/stage_p04_feature_templates.py),
  [`stage_p05_item_row.py`](../../services/syteline_export/pipeline/stage_p05_item_row.py),
  [`stage_p06_item_tail.py`](../../services/syteline_export/pipeline/stage_p06_item_tail.py),
  [`stage_p07_converted_rows.py`](../../services/syteline_export/pipeline/stage_p07_converted_rows.py),
  [`stage_p08_postprocess.py`](../../services/syteline_export/pipeline/stage_p08_postprocess.py),
  [`stage_p09_patches.py`](../../services/syteline_export/pipeline/stage_p09_patches.py),
  [`stage_p10_bom.py`](../../services/syteline_export/pipeline/stage_p10_bom.py),
  [`stage_p11_finish.py`](../../services/syteline_export/pipeline/stage_p11_finish.py).
- Existing regression expectations updated where cancellation is now observed
  earlier: [`test_sif_obx_validation_parity.py`](../../tests/test_sif_obx_validation_parity.py),
  [`test_syteline_export_page_run.py`](../../tests/test_syteline_export_page_run.py),
  [`test_syteline_job.py`](../../tests/test_syteline_job.py),
  [`test_syteline_pipeline_end_to_end.py`](../../tests/test_syteline_pipeline_end_to_end.py),
  [`test_syteline_pipeline_helpers_fabric.py`](../../tests/test_syteline_pipeline_helpers_fabric.py),
  [`test_syteline_pipeline_stage_p00.py`](../../tests/test_syteline_pipeline_stage_p00.py),
  [`test_syteline_pipeline_stage_p11.py`](../../tests/test_syteline_pipeline_stage_p11.py),
  and [`test_pricing_worker_lifecycle.py`](../../tests/test_pricing_worker_lifecycle.py).
