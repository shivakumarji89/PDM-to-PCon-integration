# PEP100 enumeration performance: where the time goes

Article `PEP100` (Bay Work Pod, `…/hmx/bay_work_pod/ANY/1/db`), generated with every property varied, no rules, price
date 2026-11-04, currency EUR (the currency does not affect enumeration). Every number below comes from this one input.

Labels used throughout: **MEASURED** = timed or counted on this machine from the real PEP100 data;
**MOCK** = counted on the Python port of the C# algorithm over a toy product; **ESTIMATE** = derived arithmetic, not
a measurement. Nothing here is a pCon-host timing: no pCon.planner host was available, so the C# plugin has not been timed.

## 1. The dialog was not produced by the C# enumerator

The progress text in the report ("N configuration(s), N node(s) evaluated, N valid SKU(s)") is written by
[generator.py:442](../../../services/ocd_engine/generator.py#L442) and the summary by
[pcon_article_obx_generator_page.py:776](../../../ui/pages/pcon_article_obx_generator_page.py#L776). The Article OBX
Generator page calls `OcdArticleGenerator.generate` (the Python OCD engine) and does not start the pCon plugin. The C#
`ConfigurationEnumerator` has no "nodes" counter and cannot print those figures. So the observed slowdown belongs to
the Python engine; the C# plugin was investigated and instrumented as well (section 7), but it is not the source of the
observation and has no timings.

## 2. What the numbers in the dialog mean

| Figure | Where it comes from | Reflects remaining work? |
|---|---|---|
| Percentage | `ProgressReporter` ([progress.py](../../../core/progress.py)): the page declares `steps = number of articles` = **1**, and `advance()` is called once, at the end. Until then the bar is a damped creep driven only by the clock (`_on_tick`, 120 ms). | **No.** It is a function of elapsed time. |
| configurations | `engine.stats.emitted`: complete configurations the walk produced, before `finalize`, validation and dedup. | Counts work done; there is no total. |
| nodes | `engine.stats.nodes`, reported every 5,000 nodes. | Counts work done. |
| valid SKUs | `len(outcome.skus)`: after validation and dedup. | Counts work done. |

Replaying the bar's formula (MEASURED by simulation, `core/progress.py` logic with one step) gives 23 % at 18 s,
32 % at 96 s and 38 % at 379 s, against the observed 21 %, 30 % and 36 %. The curve is the same shape whatever the
engine does. The full walk is **122,304 configurations** (section 3), so at 06:19 the run had done
14,596 / 122,304 = **11.9 %** of the configurations while the bar showed 36 %.

The C# plugin's progress is different and also not work-based: `processed = accepted rows`, `total = maxConfigurations`,
and the callback only runs when a row is accepted (never for duplicates, skipped leaves or internal nodes), so a run
that is mostly duplicates shows a stalled bar.

## 3. Same input, same SKU set, two builds of the measurement

`tools/ocd_enumeration_profile.py` wraps the engine from outside (no `services/` change). Two full runs were made on the
identical input at the same time, one with the wrappers and one plain, to bound the instrumentation overhead.
Raw output: [profile_instrumented.json](Enumeration_Performance_PEP100/profile_instrumented.json),
[profile_plain.json](Enumeration_Performance_PEP100/profile_plain.json).

| | plain | instrumented |
|---|---|---|
| wall time | 4,358.2 s | 4,368.6 s (+0.24 %) |
| valid unique SKUs | 43,680 | 43,680 |
| configurations / nodes | 122,304 / 417,559 | 122,304 / 417,559 |
| duplicates removed / invalid / pruned | 78,624 / 0 / 16 | 78,624 / 0 / 16 |
| ordered SKU digest (final, variant, varcode, price, currency, status) | `936cfd44…c1e1d` | `936cfd44…c1e1d` |
| sorted-final-number digest | `4406196e…d8d2` | `4406196e…d8d2` |

The outputs are identical, so the timings are comparable and no correctness question arises. The dialog ratio of valid
SKUs to configurations at 01:36 (2,000 / 5,693 = 35 %) matches the full-run ratio (43,680 / 122,304 = 35.7 %), and the
dialog's nodes per configuration (50,000 / 14,596 = 3.4) matches 417,559 / 122,304 = 3.4: the user's run is this same walk.

### Where the time goes (MEASURED, instrumented full run)

| Phase | Seconds | Share | Per call |
|---|---|---|---|
| depth-first walk (`enumerate`, includes hidden/candidate/constraint checks) | 9.8 | 0.2 % | 80 µs / configuration |
| **`finalize` per configuration** | **4,332.7** | **99.2 %** | **35.4 ms** |
| of which `VarcondEngine.run` (price-domain relations) | 4,296.7 | 98.4 % | 35.1 ms |
| of which computed properties (`ComputedPropertyEngine.run`) | 20.3 | 0.5 % | 0.17 ms |
| of which `_verify` | 9.6 | 0.2 % | 0.08 ms |
| code-scheme `encode` | 3.5 | 0.1 % | 29 µs |
| `price_resolved` (1,600 distinct price keys; 42,080 reused) | 2.0 | 0.0 % | 1.2 ms |
| SKU rows + `ResolvedConfiguration.of` | 7.5 | 0.2 % | |
| `reporter.note` (172 calls) | < 0.01 | 0.0 % | 1 µs |

The walk, the SDK-free equivalent of "enumeration", is not the bottleneck: a walk-only run (no `finalize`) of the whole
tree takes **1.45 s**. 99 % of the time is spent re-evaluating the article's price relations once per complete
configuration.

Why: PEP100 carries **160 article-level price-domain action relations** of 5-6 KB each (`IF … THEN $VARCOND = …`
chains). `execute_relations` runs all 160 for every configuration (a cProfile of the first 89 configurations shows
~14,300 `run_actions` calls and 1.2 M `eval_cond` calls, i.e. about 13,800 condition evaluations per configuration).
Their results depend on **9 of the 17 properties** (Ceiling_Finish, Country, Door_Finish, Monitor_Support,
Occupancy_Indicator, Power_Finish, Power_Option, Surface_Height, Surface_Material). Across all 122,304 configurations
those nine properties take only **2,240 distinct value combinations** (54.6x redundancy; each individual relation sees
1,280-2,240 distinct inputs; `tools/ocd_enumeration_analysis.py price-inputs`).

## 4. Does the cost grow with depth, branching, cascades, dynamic properties or duplicates?

| Hypothesis | Evidence | Verdict |
|---|---|---|
| **Depth** | The walk is 80 µs/configuration. Per-configuration `finalize` is the same function of the finished configuration whatever depth it was reached at. | No (MEASURED) |
| **Branching factor** | Average branching 2.0-5.0 per property, max 6; candidate cache 236,578 hits / 21 misses; `_filter_values` total 0.001 s. | No (MEASURED) |
| **Relation cascades** | `_is_hidden` 8.9 µs, `_early_constraints_ok` 0.8 µs per call; 16 values pruned in total. | No (MEASURED) |
| **Dynamic property creation** | The OCD engine has a fixed property list (17 properties; `Monitor` and `Power_Finish` hidden on some branches). No property is created during the walk. | Not applicable to the Python path; **unmeasured** for pCon |
| **Duplicate configurations** | 78,624 of 122,304 (64 %) are duplicates, but `finalize` and `encode` run **before** the duplicate check, so each costs the full 35 ms. Cost is per configuration, so duplicates make the run ~2.8x longer than the 43,680 SKUs need. | **Yes, as multiplier on the real cost** (MEASURED count; time share = 64 % of 4,333 s ≈ 2,780 s, ESTIMATE) |
| **Cost drifting with position** | See below. | No |

**The rate change seen in the dialog.** The dialog's own numbers are 16.9 ms/configuration for the first 5,693
configurations (96 s) and 31.8 ms/configuration for the next 8,903 (283 s). In the full run, `finalize` cost per
2,000-configuration bucket swung between 17.6 and 76.6 ms with no trend (mean per third: 31.4 / 43.7 / 31.5 ms).
That swing is machine noise, not content: timing fixed slices of the same configuration list, interleaved in one quiet
process (`tools/ocd_enumeration_analysis.py slices`), gives the same cost for slices taken from buckets that cost 18 ms
and from buckets that cost 77 ms in the full run: two independent runs of the tool gave medians of 17.8-21.4 ms
(buckets 2, 6, 14, 21, 22, 3, 28 and 2, 6, 21, 22; individual slices 17-27 ms). So per-
configuration cost is constant at about 18-21 ms on a quiet machine, and the slowdown inside one run is environmental
(the two runs here shared the machine, which is why the full run averaged 35 ms). The dialog's 17 ms start matches the
quiet figure; whether the later 32 ms is CPU contention on the user's machine is **not proven** by this data.
At 18-21 ms the whole run would take about 37-43 minutes on a quiet machine (ESTIMATE: 122,304 x 18-21 ms).

## 5. Do the UI updates contribute?

Not measurably (MEASURED for the Python path, with the live-GUI caveat below).

* The work runs on a worker thread (`ReportedTask`), not the GUI thread. Progress calls are `reporter.note`, which only
  emits a Qt signal: **172 calls in the full run, < 0.01 s total** (1.2 µs each with a counting reporter).
  `python -I tools/ocd_enumeration_profile.py bay_work_pod PEP100 --reporter real` runs the production
  `ProgressReporter` (signals, no receivers) to include its own cost.
* Caveat: GIL contention with a painting GUI thread cannot be measured headless. The comparison that settles it is the
  elapsed time of the UI run against `profile_plain` on the same machine; the dialog's 16.9 ms/configuration at the
  start equals the headless 18-21 ms, which suggests no UI overhead.
* C# plugin: `Application.DoEvents()` runs inside the progress callback, once per **accepted** row. It is timed
  separately now (`progressDoEvents`, `progressSetProgress`, `progressWriteFile`, `progressCallback`) but was not run.

## 6. The original-vs-optimised comparison: what could and could not be done

The comparison the task asks for (probe reuse on/off, original baseline) concerns the **C# plugin**, which needs a
pCon.planner host. It was not run. What exists instead:

* **MOCK** counts on the Python port of the algorithm (toy chair model, **not PEP100**). All three switch settings give
  identical rows, order, warnings and counters, and an independent oracle agrees (`tests/test_pcon_enumerator_probe_reuse.py`):

| Product | Variant | SKUs | Same output | Inserts | SetValues | Replay | ValueSet reads |
|---|---|---|---|---|---|---|---|
| LARGE | original (`REUSE=0`, `LEGACY=1`) | 16 | yes | 32 | 114 | 114 | 146 |
| LARGE | shipped `MK_OBX_REUSE_PROBE=0` (`LEGACY=0`) | 16 | yes | 32 | 114 | 114 | 130 |
| LARGE | optimised (`REUSE=1`, `LEGACY=0`) | 16 | yes | 16 | 72 | 56 | 72 |

  The full table (4 products) comes from `python -I tests/test_pcon_enumerator_probe_reuse.py`.

* **Limitation, stated plainly.** `MK_OBX_REUSE_PROBE=0` disables only probe hand-over. It keeps the second optimisation
  (skipping the offered-check and the second `ValueSet` read), so it is **not** the original baseline: the mock shows it
  makes the same inserts and SetValues as the original but 16 fewer ValueSet reads. Therefore the shipped switch cannot
  by itself measure "original vs optimised".
* **New switch** `MK_OBX_LEGACY_READS=1` restores those reads (second `ValueSet` read of the chosen property, and the
  offered-check before every SetValue). `MK_OBX_REUSE_PROBE=0` + `MK_OBX_LEGACY_READS=1` reproduces the original's SDK call
  pattern on a single build. By default (switch unset) behaviour is unchanged.

### ESTIMATE: what the C# walk would look like on PEP100 if pCon's tree mirrors the OCD tree

Assumption (unverified): pCon exposes the same 16 valued choice properties in the same dependency shape. Using the
measured per-property visit and branching counts: original ≈ **359,000 probe inserts and ≈ 4.9 million SetValues**
(replay, upper bound: assumes no property is hidden along the way); optimised ≈ **122,000 inserts and ≈ 1.9 million
SetValues**. The SDK cost per insert or SetValue is unknown, so no time can be derived. These are structural
counts for sizing the live test, not results.

## 7. Instrumentation added (C#, builds clean; not run on a host)

`tools/pcon_obx_plugin/EnumerationMetrics.cs` (new), threaded through `ArticleConfigurator`, `ConfigurationEnumerator`
and `PluginMain`. The result JSON gains a `metrics` object; the existing flat keys are kept. Time is kept in Stopwatch
ticks: the previous counters summed `ElapsedMilliseconds` per call, which truncates sub-millisecond SDK calls to 0, so
`probeInsertElapsedMs`/`propertyApplyElapsedMs` from earlier builds under-report; they are now tick-based.

| Requested measurement | `metrics` key |
|---|---|
| probe insertion time and count | `probeInsert` |
| SetValue apply time and count | `propertyApply` (inclusive of lookup and offered-check), `setValue` (SDK call alone) |
| property enumeration | `propertyList` (GetProperties call), `propertyFind`, `nextProperty` (selection, inclusive) |
| ValueSet read time and count | `valueSetRead` |
| leaf verification | `leafVerify` (also `rowBuild`, `priceDateUpdate`) |
| duplicate detection | `duplicateCheck` (count = leaves checked; `duplicates` = hits) |
| probe discard / cleanup | `probeDiscard`, `leafClose` |
| total enumeration | `totalMs` and `enumerationElapsedMs` |
| UI | `progressCallback`, `progressSetProgress`, `progressWriteFile`, `progressDoEvents` |
| depth, branching, replay | `visitsByDepth`, `insertsByDepth`, `replayApplicationsByDepth`, `averageBranching`, `maxDepth`, `leaves`, `internalNodes`, `replayApplications`, `incrementalApplications` |
| trend over the run | `samples`: one entry per 500 visited nodes (elapsed, counts, SDK ms so far; at most 2,000) |

Timers are inclusive and overlap; compare each to `totalMs`, do not add them. SDK use is single-threaded and unchanged;
nothing is parallelised. Enumeration order, relation behaviour, cancellation, truncation and OBX export are unchanged
(the mock tests cover output equality, counter consistency and cleanup on cancel/truncate/SDK exception).

Python side: `tools/ocd_enumeration_profile.py` and `tools/ocd_enumeration_analysis.py` (read-only wrappers).

## 8. How to measure the C# plugin on a live host (not yet done)

1. Build three plugin folders from this tree: `tools/pcon_obx_plugin/build.ps1`. (A single build is enough because of the
   env switches; only one folder may be installed in pCon at a time.)
2. In the Workbench page use the same catalogue, article `PEP100`, rules, `maxConfigurations` and price date for every run;
   discard the planning between runs. Quit pCon between runs, and keep the machine otherwise idle (the Python numbers above
   show a 2x swing under load).
3. Run each variant three times, setting the variables in pCon's environment before it starts:
   * A original: `MK_OBX_REUSE_PROBE=0`, `MK_OBX_LEGACY_READS=1`
   * B shipped switch: `MK_OBX_REUSE_PROBE=0`
   * C optimised: no variables
4. Accept the comparison only if the sorted `finalArticle` lists are identical, `visited`, `skipped`, `duplicates` are equal
   and the OBX files are equal after sorting. If any differ, stop and investigate correctness; report the article.
5. Read from `metrics`: `totalMs` against `probeInsert.ms`, `propertyApply.ms`, `valueSetRead.ms`, `nextProperty.ms`,
   `rowBuild.ms`, `probeDiscard.ms` (which dominates?), `progressCallback.ms` (UI share), the `samples` trend (does ms per
   visit rise?), `visitsByDepth` / `insertsByDepth` (depth and branching), and `duplicates` (rows built then thrown away).
   Report medians and `1 - C/A` for `totalMs`.

## 9. Recommendation

**Next optimisation (Python OCD path, where the observed slowdown is): evaluate the price relations once per distinct
input instead of once per configuration.** `VarcondEngine.run` is a pure function of the property values the 160 relations
read (nine properties), plus fixed model data. Key a cache on those values (the set is derivable from
`compile_relation(...).refs` that `price-inputs` already computes) and reuse `VarcondResult` for equal keys. On PEP100
there are 2,240 distinct keys against 122,304 configurations, so about 98 % of the varcond evaluations (≈ 98 % x 98.4 %
of the run) are repeats; the achievable saving is large, on the order of 40x on that phase (ESTIMATE, not measured: the
cost of a hit and of building the key is not included).

Risks: (1) a relation may read something outside the property list (computed properties set by `$SELF`/earlier relations,
aliases, `ban`, table lookups, rhs values), which would make the key incomplete and silently reuse a wrong price
condition. Mitigation: build the key from the transitive references (including computed properties' own inputs), and fall
back to no caching for any relation whose references cannot be fully resolved. (2) Mutable context: `VarcondEngine.run`
copies `computed`/`aliases`, so results are cacheable, but warnings recorded into the sink must still be emitted once.

Validation: run `tools/ocd_enumeration_profile.py bay_work_pod PEP100` before and after on a quiet machine; the ordered
`skuDigest` must stay `936cfd44…c1e1d` and `invalid`/`duplicates`/`priceEvaluations` must be unchanged; also run
`tests/ocd_engine` and compare the digest on the other real series (Lino, Tun, Dalby, Betwixt) where price relations differ.

Secondary, lower risk, separate changes: (a) make the dialog determinate: the walk takes 1.45 s here, so a counting pass
before `finalize` would give an exact total and an honest percentage and ETA; (b) skip `finalize` for configurations whose
final article is already known only if the price key is provably identical, which needs the encode-before-finalize
ordering to be checked first (the code scheme reads computed properties), so treat it as unproven.

C# plugin: no optimisation is recommended before the live measurement in section 8. Its cost model (a probe and a prefix
replay per node, one full row build per leaf including the 64 %-duplicate share) is plausible but unmeasured.

## 10. Caveats

* Both full runs shared the machine, so absolute times are inflated about 1.8x against the quiet slice timing (18-21 ms vs
  35 ms per configuration); the phase shares are robust (confirmed independently with cProfile).
* One run per variant for the 72-minute measurement; the slice timing has 3 interleaved rounds.
* The per-property cost table in the raw JSON (`leafCost`) is contaminated by that machine noise; do not read differences
  of a few ms between values as content effects (the slice test shows there are none).
* Nothing in this document is a pCon timing.
