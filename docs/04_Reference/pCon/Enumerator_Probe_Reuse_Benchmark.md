# Enumerator probe reuse: what changed and how to measure it on a real host

## Change
`ConfigurationEnumerator.Enumerate` used to discard the probe it had just configured and read, then
insert a new probe for every child and replay the whole prefix. A non-leaf probe is now handed to its
**first child**, which applies only its one new assignment. Later siblings still insert a fresh probe and
replay the prefix, because the SDK has no clone/snapshot/rollback (`IProperty.SetValue` documents that a
change may alter other properties and add new ones; setting the old value back does not undo that).

Also: the value keys read while choosing the next property are reused (one `ValueSet` read less per
internal node), and the first-child apply skips the `Offers()` pre-check because the value was read from
that same probe a moment earlier.

Unchanged: DFS order, property order, leaf verification, dedup, cancel/truncate checks, warnings text,
single-threaded SDK use, OBX export.

## Verified locally (no pCon host)
`python -m pytest tests/test_pcon_enumerator_probe_reuse.py` - a port of the algorithm in both shapes over
a dependent product model. Output equal to baseline (rows, order, warnings, counters) and to an
independent oracle; no leaked probes on cancel/truncate/SDK exception; one open instance at a time.
Counts only (not timings): `python -I tests/test_pcon_enumerator_probe_reuse.py`.

> Update: `MK_OBX_REUSE_PROBE=0` keeps the ValueSet-read saving, so it is not the original baseline. Use
> `MK_OBX_REUSE_PROBE=0` together with `MK_OBX_LEGACY_READS=1` for that, and read the new `metrics` object in the result.
> See `Enumeration_Performance_PEP100.md` (sections 6-8) for the switches, counters and the live-host procedure. The
> Article OBX Generator page itself uses the Python OCD engine, not this plugin.

## Real-host benchmark (not yet run)
1. Build the baseline: `git stash`/checkout `fe4534e`, `tools/pcon_obx_plugin/build.ps1`, copy the output
   to a folder `plugins\MKObxGenerator_base`. Build the branch under test into `plugins\MKObxGenerator`.
   (Only one of the two may be installed in pCon at a time.)
2. In the Workbench Article OBX Generator page, pick a representative catalogue/article set with relations
   (same articles, rules, `maxConfigurations` and price date for both runs). Keep the planning discarded
   between runs.
3. Run baseline, then optimized. The result JSON carries `visited`, `probeInsertions`,
   `propertyApplications`, `probeInsertElapsedMs`, `propertyApplyElapsedMs`, `enumerationElapsedMs`.
   `MK_OBX_REUSE_PROBE=0` in pCon's environment disables only the probe reuse (the ValueSet-read saving
   stays), so use the `fe4534e` build for the true baseline.
4. Compare: the sorted `finalArticle` lists must be identical, `visited`/`skipped`/`duplicates` equal, and
   the OBX files equal after sorting. Repeat each run 3 times; report medians and
   `speedup = 1 - optimized/baseline` for `enumerationElapsedMs`.
5. Expect insert count and replay work to drop by roughly the number of internal nodes. If SKUs differ,
   the assumption that interleaved property reads do not perturb pCon's relation evaluation is wrong for
   that product: set `MK_OBX_REUSE_PROBE=0` and report the article.
