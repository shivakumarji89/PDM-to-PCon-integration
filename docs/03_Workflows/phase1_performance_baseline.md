# Phase 1 performance work: baseline and results

Offline, non-destructive measurements. Synthetic data only (`tests/perf_synthetic.py`); the MDB bridge is
exercised against a scratch MDB created in a temporary folder. No PDM connection and no real MDB is touched.
Same machine, quiet, original code and new code run back to back (original = commit `ea18115`).

Reproduce:

```
python tools/perf_phase1_baseline.py --sizes 1000,3000 --bridge-rows 5000,20000,50000 --out result.json
python tools/perf_phase1_baseline.py --only materialize --sizes 7560
```

## What changed

| Area | Before | After |
|---|---|---|
| `EngineeringReductionService.materialize_class_creation_article_sets` | per article: class-wide common prefix over all articles (O(n²)), `effective_codes` re-sorted per property, ModelSuffix code sets rebuilt | class prefix computed once per class (lazily), `effective_codes` and suffix code sets memoised per class, first-wins property index |
| `EngineeringMemberService.get_article` (Articles `_collect_rows`, Class Creation `_split_members`, `auto_reduce`) | linear scan of `snapshot.articles` per member | optional `index=` built once with `index_articles()` (first article wins, as before) |
| Articles `_populate_grouped` | per group, rescans every row and every member of the group | export ids gathered in one pass (identity semantics kept) |
| Articles `_populate_sets` / `_set_rows` | code map rebuilt per set row; unique ids by list scan | one code map; companion set (same first-seen order) |
| Class Creation `_populate_visible_values` | scan of all articles for every displayed value | one value -> article-codes index per call |
| SyteLine `list_index_of` | Python loop with a cancellation check per element | `list.index` in C for list/tuple, type rule and `==` re-checked, other iterables keep the original loop |
| SyteLine stage P00 | heaviest item query executed twice | executed once; the count list is built from the same rows |
| `PDMService` family-snapshot and product-registry caches | `json.dumps(..., indent=1)` (pure-Python encoder) | compact separators (both files are only read with `json.loads`) |
| `resources/mdb_bridge.ps1` | `$rows += ...` / `$result.results += ...` (array copy per append) | `List[object].Add` (output JSON is byte-identical) |

Not changed on purpose: VARCOND generation, pricing, export transaction handling, threading, navigation refresh,
user-facing project files (`project_service`), `snapshot_store`, and the per-process cost of the bridge.

## Measurements (seconds unless noted)

| Workload | Before | After |
|---|---:|---:|
| Materialise one 1,000-article class | 1.97 | 0.020 |
| Materialise one 3,000-article class | 20.7 | 0.064 |
| Materialise one 7,560-article class | 117.5 | 0.186 |
| Class Creation `refresh()`, 3,000 articles | 7.16 | 0.10 |
| Class Creation select a 90-value property, 3,000 articles | 0.072 | 0.022 |
| Articles `_collect_rows`, 3,000 articles | 0.178 | 0.002 |
| Articles `_populate_sets`, 3,000 articles | 0.045 | 0.010 |
| Articles grouped `_apply_filter`, 3,000 articles | 0.266 | 0.056 |
| Articles `refresh()`, 3,000 articles | 0.601 | 0.060 |
| SyteLine: 100 misses against a 100,000-entry list | 2.88 | 0.09 |
| SyteLine P00: item query executions | 2 | 1 |
| `save_family_snapshot`, 3,000 articles (time / size) | 0.085 / 1.54 MB | 0.029 / 1.05 MB |
| Bridge read 5,000 rows | 5.4 | 4.1 |
| Bridge read 20,000 rows | 22.7 | 5.4 |
| Bridge read 50,000 rows | 114.9 | 10.0 |
| Bridge batch of 50 / 200 / 400 query ops | 3.5 / 4.1 / 4.8 | 3.5 / 3.9 / 5.6 |

Python heap peak (tracemalloc) for a 1,000-article materialisation: 0.60 MB -> 0.55 MB. The PowerShell process
memory was not measured.

The many-ops change (`$result.results`) is not measurable up to 400 ops (process start-up dominates and the
differences above are run-to-run noise); it only matters for batches with thousands of ops, which was not benchmarked.

Observations that are not fixed in Phase 1: a bridge call costs about 3.4 s of process start-up on this machine
(the 50-op batch above), so the number of calls per export matters more than the rows per call; the bridge row
cost is still dominated by per-cell COM reads and JSON, not by the copy that was removed.

## Equivalence evidence

* Output digests of the materialiser are identical before and after at every size above, and for 300
  randomised snapshots (blank codes, zero widths, shuffled placement, duplicate property ids, odd article codes).
* Bridge output files were compared byte for byte (old script vs new script) for 11 scenarios: 0 / 1 / 2 / 2,000
  rows, 120 ops, transaction with insert + update + delete + query, failing ops with and without a transaction,
  empty batch, unknown op, connection failure.
* `tests/test_phase1_performance_equivalence.py` pins the golden digests (taken from the original code), reference
  oracles copied from the replaced algorithms, and generous scale bounds.
