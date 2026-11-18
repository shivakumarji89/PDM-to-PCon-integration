# Phase 2 performance work: navigation, background exports, Development VARCOND

Offline, non-destructive measurements (synthetic snapshots, offscreen Qt, fake PDM, no database). Reproduce with
`python tools/perf_phase2_baseline.py --only navigation|exports|varcond`. Phase 1 is in
[phase1_performance_baseline.md](./phase1_performance_baseline.md).

## 1. Navigation: one refresh per navigation

`WorkspaceHost.activate` refreshed a page from `showEvent`, again explicitly, and a third time through `on_enter()`
(which is `refresh()` for most pages).

* Pages skip their `showEvent` refresh while the host is switching them in (`BasePage._host_activating`); the
  host's own refresh follows immediately, so the show-time one was an identical rebuild.
* A page whose `on_enter()` is exactly `refresh()` (`BasePage.ENTER_IS_PLAIN_REFRESH`, true by default) is refreshed
  by `on_enter()` alone. Articles, Text, Relation and Pricing Relation set it to False: their `on_enter()` does more or
  does not always call `refresh()`, so the host keeps its refresh before it. (Articles' auto-reduce is gated by a
  signature and `on_enter()` materialises Article Sets between the two refreshes, so its first refresh is not
  provably redundant.)
* **Not changed on purpose: the load-time refresh of hidden pages** (`_on_engineering_ready`, `refresh_workspaces`).
  With the pages built before the data arrives (the real order) the refresh of Class Creation, Text and Relation
  changes the snapshot (article sets / reduced articles, text blocks, relation objects) that a later export reads, even
  if the page is never opened (`test_refreshing_hidden_pages_after_a_load_materialises_snapshot_data`). Deferring it
  with dirty flags would change export content. Each page is already refreshed once per load event.

| Page (2,000 articles, 20,000 price records) | refreshes before -> after | seconds before -> after |
|---|---|---|
| Pricing | 3 -> 1 | 1.8-1.9 -> 0.5-0.7 |
| Class Creation | 2 -> 1 | 0.078 -> 0.040 |
| Text | 2 -> 1 | 0.48 -> 0.37 |
| Review / Engineering | 2 -> 1 | < 0.02 (negligible) |
| Relation / Pricing Relation | 2 -> 2 / 2 -> 1 | negligible |
| Articles | 3 -> 2 | not measurable: first activation costs ~3.7 s of one-time work either way |

(Both orders of legacy/new were run; the first activation of Articles pays the one-time cost whichever goes first.)

## 2. Exports on a worker thread

`ui/workers/export_runner.py` (`ExportRunner`, on `ReportedTask`): one export at a time, a modal status popup without
Cancel (these exports have no cancellation checkpoints and write non-transactionally, so a cancel could only be
reported, not honoured), GUI-thread callbacks, slot released if a callback raises.

Moved onto it: full MDB export, article MDB export (prepare the MDB, then export, as two worker steps), Excel export,
both XOCD publish stages, and the VARCOND relation generation that precedes the MDB export. The GUI thread keeps the
dialogs, `apply_registry` and the isolating snapshot copy, in the original order, so the worker only sees its copy.

| Export | GUI thread blocked before | after |
|---|---|---|
| Excel, 300 articles | 5.0 s | 0.05 s |
| XOCD, 7,560 articles (synthetic) | 0.23 s | 0.66 s (the isolating deep copy) |

XOCD on synthetic data is cheap, so the copy costs more than the export; its benefit with real, price-heavy packages
merged into an SVN working copy is **not demonstrated**. The real OCD MDB export could not be compared (the bundled
templates are not in the repository); it receives the same isolated copy as before and the same call.

## 3. Development VARCOND

* Filter typing is debounced (250 ms). The prefix-length spin box is still immediate.
* Development generation runs on a worker. The two requests the panel makes when it is built or re-entered become
  one generation; a newer request supersedes an older one; a stale result is dropped; only the selected relation's
  rules are shown. The Maintenance path is unchanged.
* `generate_live` asks for the option increments of each component prefix once per run (and once per export, through a
  shared cache) instead of once per component occurrence. Output is identical (golden digests from the original code).
* The relation export computes the selection-independent part of the base codes once instead of once per relation.

Fake PDM with a simulated 20 ms per query (no real PDM was used): export 29 -> 23 queries, 0.60 -> 0.47 s;
typing 7 characters: 7 synchronous generations blocking the GUI for 0.86 s -> 1 background generation, GUI never
blocked (worst event gap 13 ms).

## Observations that are not changed

* In Development, selecting a relation only displays cached rules; generation starts on a filter / prefix-length /
  exclusion / substitution change. That is how the panel behaves at `ea18115` and was kept.
* `tests/test_maintenance_varcond.py` still calls `_generate_selected`, which no longer exists (3 of the 17
  pre-existing failures). `GeneratePage` cannot be constructed (no `export_service` on the context) and is unused.
* The load-time refresh of every dependent page remains synchronous on the GUI thread (see section 1).

## Verification

* New tests: `tests/test_navigation_refresh.py` (15), `tests/test_background_exports.py` (22),
  `tests/test_varcond_background.py` (25). The UI test files tear their widgets down deterministically
  (`WorkspaceHost.activate` schedules `QTimer.singleShot(0, page.auto_fit_tables)`; a test that lets its pages be
  garbage-collected first makes that timer fire inside a later test).
* Per-file run (each test file in its own process): 17 failures, exactly the 17 failures of the original commit,
  5,453 passed. `test_pricing_worker_lifecycle.py` passes but exits with code 127 at interpreter shutdown, on the
  original code too.
* **A single-process run of the whole suite is not reliable on this machine, independent of these changes.**
  It ended in a Qt access violation in several runs; the same subset of the suite (`test_[a-p]*.py`) crashes the same
  way on the untouched original commit. Earlier single-process runs (before Phase 2) completed, so it is
  timing-dependent. Compare per file, as above.
