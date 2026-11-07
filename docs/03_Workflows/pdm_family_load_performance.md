# PDM family load performance

Measured against the live PDM (DBCHIP12V / PDMLive, read-only; `save_family_snapshot`
stubbed so no cache file was overwritten). Both code versions were run back to back
from the same machine, original HEAD `4f7e5de` in a separate worktree vs the working tree.

## Findings

Path: Product Explorer `_on_load_family` -> `ReportedTask` worker ->
`PDMService.load_family(initialize_engineering=True)` -> `load_family_articles` ->
`load_family_details` -> engineering initialization. Loading already runs off the UI thread.

The "Loading Article Links (N articles)" label covers everything from the link fetch to
the next `advance()`: six fetches, not one. It is not an N+1 (queries were already chunked
at 500 ids), but the chunking was by **ItemId**, and each 500-id lookup carries a large fixed
cost (~0.6 s for 500 rows vs 0.8 s for all 3,000 items fetched by ProductId in one query).

Wasted work found:

| Stage | Problem | Fix |
|---|---|---|
| Article links / components / prefix lengths | 6 (3,000 art.) to 16 (7,560 art.) ItemId-chunk queries *each* | select by `Item.ProductId`: 1-2 queries each, rows filtered back to the article set |
| Option increments | 50 LIKE prefixes per query (14 queries for 132 rows) | 500 per query |
| Product info | re-queried in the details phase although phase 1 stored `range_name` | reuse; query only products lacking one |
| Article-set building | `if article_id not in carriers` list scan: quadratic when a value is shared by thousands of articles | companion set, same order/uniqueness |

SQL is the dominant cost (~85% of load time on the 3,000-article family); `materialize_article_sets`
was the dominant Python cost (26 s of 80 s on the 7,560-article family).

## Results (same dataset, live PDM, alternating runs)

The screenshot's 6,474 articles could not be reproduced exactly (the 60-day Ratio Desks family
is 3,000 articles now; 6 min was not reproduced on this machine). Two live families bracket it.

| Metric | Before | After |
|---|---:|---:|
| 60-day Ratio Desks (3,000 art.) total load | 23.7 / 23.7 / 26.3 s | 10.9 / 13.6 / 14.2 s |
| ...SQL queries | 30 | 11 |
| ...SQL time | ~21 s | ~10-13 s |
| 40-day Ratio Legacy Super Products Desks (7,560 art.) total load | 79.9 s | 22.7 s (3.5x) |
| ...SQL queries | 76 | 20 |
| ...SQL time | 52.0 s | 19.9 s |
| ...Building Article Sets | 26.2 s | 0.8 s |

Per-query fetch checks on the 7,560 set: attribute values 10.0 -> 3.4 s, components 9.9 -> 2.2 s,
prefix lengths 9.4 -> 1.1 s, option increments 10.3 -> 3.4 s, all with identical rows.

Not measured: peak memory, UI rendering time, cold/warm cache (no cache was added). Remote
latency was not varied; a slower link favours this change since it removes ~60-75% of round trips.

## Equivalence

Full snapshot digest (articles, properties, options, links, varcond terms, components,
prefix lengths, increments, ranges, article sets) is identical before/after for both families,
except random UUIDs inside article sets, which also differ between two runs of the original.

## Tests

`tests/test_family_load_performance.py` (15): small and 6,480-article families, link completeness,
duplicate relationships, article-to-product mapping, scoped == item-id result, fallback, filtering,
repeated selection, range reuse, cancellation, error handling, chunk batching, `_set_attributes`
equivalence and non-quadratic bound. Test doubles in `test_application_cancellation.py` and
`scripts/validate_family_load.py` gained the three new repository method names.
Pre-existing unrelated failures (identical on the original tree): `test_article_obx_large_results`,
`test_maintenance_source_lock`, `test_pcon_sdk_obx_page`, `test_workflow_layout_components`,
`test_workflow_shell`; the full suite in one process also hits a Qt access violation (order-dependent).

## Remaining

Option increments (~3 s) and component head attributes (~3 s) are single slow queries; ~30 queries
still run serially on one connection. Lazy loading was not pursued: all links feed article sets at load.
