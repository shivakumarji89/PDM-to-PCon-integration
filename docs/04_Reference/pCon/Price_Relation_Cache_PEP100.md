# Price-relation result cache: design, proof and PEP100 benchmark

Follows `Enumeration_Performance_PEP100.md` (98.4 % of the run was `VarcondEngine.run`). Scope: the Python OCD engine only
(`varcond_engine.py`, `computed_property_engine.py`, `configuration_engine.py`, `generator.py`) and its tests. The C# plugin,
Development/Maintenance, PDM/snapshot/repository loading are untouched.

## What changed
`VarcondEngine.run` evaluated all price-domain relations for every complete configuration. With `cache=True` it memoises
the result per distinct set of inputs. Off by default on `ConfigurationEngine` (`price_relation_cache=False`, so the Snapshot
permutation service is unchanged); `OcdArticleGenerator.generate` turns it on (`price_relation_cache=True`, switch it off
to get the original behaviour). The cache lives in the engine instance: one article model, one `generate` call.

## Dependency analysis (what can change `VarcondEngine.run`)
Traced path: `generate` -> `engine.enumerate()` -> `engine.finalize` (values dict, computed engine, `_verify`, `VarcondEngine.run`)
-> `encode` -> duplicate check by final article.

| Input | Reads | In the key |
|---|---|---|
| Relations in scope | article/class relations fixed; property relations only for visible properties; value relations only for selected values | tuple of relation identities, in evaluation order |
| `ctx.values` | `EvalContext.lookup(name)` for names in the relation AST (`PropRef`, `SPECIFIED`, `$` variables), reachable via the name, its alias target, its `VAR.PROP` tail and that tail's alias | values under exactly those names; absent differs from `None`; non-strings type-tagged (1 / 1.0 / True) |
| `ctx.computed` | same lookup, answered from `computed` first | entries under those same names only. (Keying on the whole dict was tried first: PEP100's `Code` is unique per configuration, so nothing ever hit - found by measuring a 64 % hit rate against the expected 98 %.) |
| `ctx.aliases` | written by constraints in `_verify` | included |
| `$BAN` | `ctx.ban` | included |
| value-combination tables | `ctx.tables` | pinned by identity: the first object seen is kept, a different one bypasses the cache |
| `rhs_values` | not passed to the price context | not needed |

Side effects: `run_actions` mutates only the throwaway price context; the sink counts every diagnostic, so a run that
reported anything (parse error, unsupported or failing clause) is never stored and re-runs each time
(`execute_relations` now returns whether it was clean). A relation whose AST contains a node the dependency walk does not
understand, or state that cannot be hashed, bypasses the cache. Cached values are immutable tuples; every hit builds a new
list and dict. A size cap (250,000 entries) stops storing beyond it.

Counters (`GenerationOutcome.price_relation_stats`, per run): `runs`, `relationEvaluations`, `cacheHits`, `cacheMisses`
(evaluated and stored), `cacheBypassed`, `cacheUnclean`, `cacheFull`, `cacheVerified`, `cacheEntries`.
`price_cache_verify_every=N` re-evaluates every Nth hit and raises on any difference (benchmark/diagnostic use).

## Benchmark: article PEP100, bay_work_pod, EUR, 2026-11-04 (all MEASURED on this machine)
Original = a clean checkout of HEAD (`fe4534e`) running the same harness (`tools/ocd_enumeration_profile.py --plain`).
Optimised = working tree. Raw JSON: `Price_Relation_Cache_PEP100/`.

| | original | optimised | optimised + verify every 100th hit |
|---|---|---|---|
| wall time | **3,672 s** | **200.7 s** and **107.1 s** (two runs) | 319.4 s |
| speedup vs original | 1x | **18.3x** and **34.3x** | 11.5x |
| configurations / nodes | 122,304 / 417,559 | same | same |
| valid unique SKUs / duplicates / invalid / pruned | 43,680 / 78,624 / 0 / 16 | same | same |
| price evaluations / reused | 1,600 / 42,080 | same | same |
| relation evaluations | 19,568,640 (= 122,304 x 160, derived from the scope size; the 453-leaf check below confirms 160 per run) | **358,400** (2,240 x 160) | 358,400 (+ 1,200 verification re-runs, not counted) |
| cache hits / misses / bypassed / unclean | - | 120,064 / 2,240 / 0 / 0 | 120,064 / 2,240 / 0 / 0 (1,200 verified, 0 mismatches) |
| peak working set | 256.3 MB | 241.4 MB | 241.4 MB |
| ordered SKU digest | `936cfd440240c7cdc8d87f4bb36daa3a99b387caa637f2afe2004071874c1e1d` | identical | identical |
| sorted SKU digest | `4406196e82bf69738fcaf183676cb940e9e811b5af2c5c83f54d574d6eb9d8d2` | identical | identical |
| every field of every SKU (values, variant conditions, pricing factors, price, currency, status, message, in order) | `5c5a3d1a6aa7d2af45214138837f32179c87c1decfe5bc0d2fa9f9562c916361` | identical | identical |

The ordered digest equals the baseline in the profiling report (`936cfd44…c1e1d`). Generated prices, variant conditions and
pricing factors are identical because the all-fields digest covers them.

Caveats: timings are single runs on a shared machine (the Workbench application was running during the original and the
first optimised run, hence 200.7 s vs 107.1 s for the same code); quote the speedup as 18-34x, not as a precise figure. The
original run was made after the cache work, on the same machine, not concurrently with the optimised runs.
Peak memory is the process peak working set (`GetProcessMemoryInfo`); the first optimised run predates that code and has none.
With the cache the remaining time is mostly the 2,240 evaluations (~80 s at the loaded rate), the walk (10 s) and per-leaf key building.

## Tests
`tests/ocd_engine/test_ocd_price_relation_cache.py` (25 tests): equal inputs reuse; any read property, `SPECIFIED` target, alias, qualified
name, absent-vs-empty value, value type, selected value or computed input read by a relation changes the key; a computed value
no relation reads does not defeat sharing; `$BAN`, different articles and different tables objects never share; mutating a
returned result cannot affect later hits; parse errors, failing and unsupported clauses are never cached and keep their
diagnostic counts; unanalysable relations and unhashable state bypass; a corrupted entry is caught by verify mode; the
size cap keeps results correct; cancellation is honoured; the cache is off by default; generator output (all SKU fields,
order, warnings, counters) is identical with and without the cache.
Regression: `tests/ocd_engine` plus the article OBX engine/fabric/export/basket tests: 478 passed.
`tests/test_article_obx_large_results.py::test_the_page_shows_the_complete_set_with_no_cap_and_no_widget_item_per_cell`
fails with an `AttributeError` on `_export_button`; it fails identically on a clean HEAD checkout and is unrelated.

## Not done (separate follow-up)
Earlier duplicate detection: 78,624 of 122,304 configurations are duplicates and still go through `finalize` and `encode`.
After this change `finalize` is cheap for repeated inputs, so the payoff is much smaller; re-profile before deciding.
