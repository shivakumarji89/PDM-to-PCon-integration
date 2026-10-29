# Cross-series pricing parity: Aeron, Always, Nevi Screens, Layout Screens (+ Revive reference)

Branch `feature/maintenance-legacy-pricing-engine`. Runs captured 2026-10-27/28 on the Windows PDM machine.
Reference implementation: the compiled legacy PDM (`PDMMaintenance.exe` 1.0.9686.24988, driven through
`UpdatePriceThread.execThread`, the method the *Update pCon prices* buttons start). Workbench side: the
**production** path - `PDMService.load_product` -> `PricingService.compute` (same `PriceParams` the Pricing page
builds) -> `PriceMdbExportService` dry-run plan + approved write. Machine-readable evidence:
[`cross_series_pricing_parity_evidence.json`](cross_series_pricing_parity_evidence.json).

## Status labels
PASS = confirmed against compiled legacy PDM. FAIL = reproducible mismatch. PARTIAL = some cases verified, others
outstanding. NOT RUN = legacy execution or inputs unavailable. NOT APPLICABLE = feature does not apply.
Harness-level labels used per run: PASS, FAIL, NOT RUN, CRASHED, INCOMPLETE (export blocked, or legacy itself left
items unresolved, so an identical end state proves nothing).

## Summary

| Series | Scenarios tested | Legacy PDM executed | Article pricing | Global pricing | VARCOND parity | Export parity | Status |
|---|---|---|---|---|---|---|---|
| Aeron | X1 | yes | PASS (18 stale rows updated identically) | NOT APPLICABLE (no super product, 0 global rows in the MDB) | NOT RUN | PASS | PARTIAL |
| Always | X2, X2p | yes | PASS (3 stale rows updated identically; X2 alone was a no-op) | NOT APPLICABLE (no super product, 0 global rows) | NOT RUN | PASS | PARTIAL |
| Nevi Screens | X3, X3b, X6, X6p | yes | PASS (X6p: 1 stale row) | PASS for existing rows under `nevi_enhanced` (261/261 identical); 20 extra rows explained; blank program INCOMPLETE | NOT RUN | PARTIAL (text labels differ, documented S10) | PARTIAL |
| Layout Screens | X4, X4p, X5, X5p, X8 | yes | PASS (X5p: 2 stale rows) | PASS under `layout_studio` (X4p: 3 stale rows identical); blank program INCOMPLETE | NOT RUN | PASS | PARTIAL |
| Revive (reference, not requested) | X7 | yes | not run | PARTIAL: legacy left 312 fabric rows unresolved | NOT RUN | INCOMPLETE | PARTIAL |

No series is PASS overall because the legacy VARCOND comparison needs a non-production SQL target (see below).

## Inputs
Starting MDBs are copies of the working-copy OCDs under `C:\HermanMillerOFMLSVN\Staging\HermanMiller\WS\...`
(Aeron, Always, Nevi_enhanced, Layout_Studio, Revive); every run used fresh disposable copies, one for PDM and one per
Workbench variant. Site 1, currency GBP, pricing date 16-Oct-2026, valid from 2026-10-16, PDM SQL = `DBCHIP12V/PDMLive`
(read only). EUR was not run.

| Series | Workspace / package | Program | Catalogue | List (GBP) | Product -> items priced |
|---|---|---|---|---|---|
| Aeron | Aeron / 369 | aeron | 518 | GBP_2026 (30) | `AER1A11PW` (article; MDB base `AER1A11`) |
| Always | Always / 375 | always | 381 | GBP_2026 (30) | `NOALE181` (MDB base `NOALE18`) |
| Nevi | Nevi_enhanced / 1 | nevi_enhanced | 764 | GBP_2026_2 (35) | screen `DWE3SCRNNS.105516F` -> 21 global components (`DWE3VNNS.105512F`...); article `DWE3WLES.` |
| Layout | Layout_Studio / 375 | layout_studio | 660 | GBP_2026_2 (22) | screen `GESCRNNU.105508F` -> 29 global components (`GESNNU.105508F`...); article `GEWQ.` |
| Revive | Revive / 240 | revive | 658 | GBP_2026_2 (27) | screen `RY3SCRNNB.105512F` -> 26 global components (`RY3SNNB.105512F`...) |

Global applicability was established from the data, not assumed: Aeron and Always products are not super products,
have no `ItemComponents`, and their MDBs hold 0 `tCOMd_GlobalPrice` rows. Nevi and Layout screens are super products
whose components carry a priced Fabric Type (option 8) and a BOM `FeaturePositionString` `|8|28|`.

## Per-scenario results

| Scenario | Compiled PDM | Workbench (production path) | Result |
|---|---|---|---|
| X1 Aeron article | "18 price(s) updated" | 20 records, 18 updated; blank and `aeron` program identical | PASS, 0 differing rows |
| X2 Always article | "1 price(s) already up to date" | 68 records, all existing, 0 changes | no-op, not discriminating |
| X2p Always, 3 stale rows (`1`, `1 3344=622`, `1 6530=R39`) | "3 price(s) updated" | 3 updated | PASS, 0 differing rows |
| X3 Nevi screen global | "261 updated, 20 already up to date" | explicit program: 261 updated + 20 inserted, all `8=` | 261/261 identical; 20 extra Workbench rows (`8=T2RE`) - explained below |
| X3b Nevi, placeholders then global | placeholders "21 existed, 20 inserted"; global "281 updated, 20 up to date" | 261 updated + 20 inserted | row set, conditions and values identical (incl. the 20 `T2RE` rows); 42 base rows differ only in text labels (S10, documented) |
| X4 Layout screen global | "731 price(s) already up to date" | explicit program: 380 records, 0 changes, all `8=` | no-op match; blank program: INCOMPLETE (below) |
| X4p Layout, 3 stale global rows (`GESNNU.105508F`, `... 8=1FD`, `... 8=TI`) | "3 updated, 728 up to date" | 3 updated | PASS, 0 differing rows |
| X5 / X5p Layout article (`GEWQ.`) | X5 no-op; X5p "updated" | X5p: 2 stale rows updated | PASS |
| X6 / X6p Nevi article (`DWE3WLES.`) | X6 no-op; X6p "1 price(s) updated" | X6p: 1 updated | PASS |
| X7 Revive screen global | "26 up to date, **312 item(s) unresolved**" | 338 records (312 as `28=`), 0 changes | INCOMPLETE: legacy never priced the 312 fabric rows |
| X8 Layout screen, PDM run with `programCode=revive` (diagnostic) | "1 price(s) up to date, **28 item(s) not found**" | not run | legacy lookup is program dependent |

Row counts for every compared variant (only-in-PDM / only-in-Workbench rows, option-id histograms, sample records)
are in the evidence JSON. Logs and job/out files of each PDM run were kept in the disposable work folders
(`log_dir` in the evidence).

## Option identity: `8=` versus `28=`
* **Layout and Nevi (real MDBs):** every global fabric row is `8=` (`GESNNU.105508F 8=1FD`, `DWE3VNNS.105516F 8=1FD`);
  the MDBs contain no `28=` rows. Compiled PDM under `layout_studio` / `nevi_enhanced` matches those `8=` rows
  (X4/X4p/X3) and the Workbench with the explicit program writes the same `8=` conditions. **Valid, no mapping.**
* **Revive (real MDB):** global fabric rows are `28=` (`RY3SNNT.125020F 28=4MT`). The Workbench routes priced
  Fabric Type `8` to the mapped colour option `28` (`variant_condition` `28=`, `pdm_lookup_code` keeps `8=...#`), and
  its 312 `28=` records match existing MDB rows. Compiled PDM, however, reports these rows as "did not match
  (variable: True), current pCon inc price: 77 (expected prev: 0, new value: 0)" - it never resolves them. So
  `8` -> `28` for Revive is **valid as an export target (proved by the existing MDB rows) but not reproducible from
  legacy output**; the source-to-target relation itself is **unresolved (no legacy evidence)**.
* **Program dependence:** X8 shows legacy's lookup changes with `programCode` (28 items "not found" under `revive`
  for Layout components), so the program is a real input and must not be guessed.

### Blank program defect (confirmed, narrowed)
`PricingService` receives `snapshot.generation_program`, which is `""` until the Review page sets it. The fetch layer
(`repositories/pdm_repository.py`, `program_code in ("", "revive")`) treats blank like Revive, so for Layout and Nevi
screens a blank program produces `28=` records (Layout X4: 351 of 380; Nevi X3: 280 of 301) whose conditions cannot
match the MDB's `8=` rows. The export safety check correctly **blocks** it ("Fabric family target
'GESNNU.105508F 28=1FD': expected at most one linked existing row, found 0"), so nothing was written; the run was
INCOMPLETE, not a silent corruption. The blank-routing behaviour is deliberately covered by existing tests for
Revive snapshots, and `XocdExportService.program_key` cannot infer `layout_studio`/`nevi_enhanced`, so routing was
**not** changed. Fix made: `PricingService.compute`/`compute_streaming` now append a warning (shown by the Pricing
page) when routing happened only because no program was set, telling the user to set the series program.

### The 20 extra `8=T2RE` rows (Nevi, X3)
The Nevi MDB had no `T2RE` global rows for the 20 components. The Workbench inserts missing rows directly; PDM's
global step only updates existing ones. In X3b PDM's placeholders step inserted exactly 20 records and the PDM result
contains the same 20 `8=T2RE` rows with identical values. **Intentional / equivalent**: single-step Workbench insert
equals PDM's two-step workflow (consistent with the earlier S6/S7 findings).

### Text labels (X3b)
42 base global rows (21 per list) differ only in the price-text label (PDM `(FR-FS-SC)` vs preserved `(FR-ID-SC)`).
This is the documented S10 behaviour (PDM rewrites an existing price text's language columns on a placeholder run;
the Workbench preserves existing text). Not changed.

## Price Relation / VARCOND
Legacy VARCOND comparison: **NOT RUN**. `legacy_varcond_bridge` refuses any database not clearly named
test/dev/uat/sandbox and needs an operator attestation; only `PDMLive` was used here, and `PDMTEST` was not
authorised. Workbench-only output (`MaintenanceVarCondService.generate`, live PDM read) for the parents:

| Parent | Workbench relation rule | Price-row option |
|---|---|---|
| `GESCRNNU.105508F` | `'GESNNU.105508F 8=' + Fabric_Type IF Application = 'U' AND Height = '1055' AND Width = '08' AND Material = 'F'` | `8=` - compatible |
| `DWE3SCRNNS.105516F` | `'DWE3VNNS.105516F 8=' + Fabric_Type IF Application = '' AND Height = '10551' AND Width = '6F' AND Material_Type = ''` | `8=` - compatible; the IF attributes look mis-sliced (**unverified, needs the legacy run**) |
| `RY3SCRNNB.105512F` | `'RY3SNNB.105512F 8=' + Fabric_Type IF ...` | price rows use `28=` - source option in the relation, target option in the rows; **unresolved** |

Nothing in the Workbench replaces a relation's source option with a target option.

## Changes made
* `scripts/pdm_differential/cross_series.py` (new): production-path runner for the four series plus Revive; sequential,
  per-scenario CRASHED isolation, identical stale-value perturbation for both copies, placeholders-first option,
  PASS/FAIL/INCOMPLETE/NOT RUN classification (a blocked export or legacy-unresolved items are never PASS).
* `scripts/pdm_differential/differential.py`: workspace, package and list ids parametrised (defaults unchanged);
  `run_pdm` records exit code, stderr and log dir and treats a non-zero exit as not executed.
* `scripts/pdm_differential/cross_series_evidence.py` (new): condenses raw runs and re-derives statuses uniformly.
* `services/pricing_service.py`: blank-program routing warning (no behaviour change to prices, routing or export).
* `tests/test_cross_series_pricing_parity.py` (new, mocked logic tests - **not** compiled-PDM evidence).

## Test results (2026-10-28, `QT_QPA_PLATFORM=offscreen`)
* Focused (7 files: cross-series parity, fabric targets, differential fetch routing, global/article price source
  parity, Pricing page text blocks, Maintenance VARCOND): **151 passed**.
* Full suite: **4524 passed, 11 skipped, 22 subtests passed, 0 failed** (260 s).
* One regression caused by this work was found and fixed during validation: the new blank-program warning opened a
  modal `QMessageBox.information` inside `test_actual_compute_refresh_and_snapshot_roundtrip_display_resolved_conditions`
  and hung the run; the test now captures the dialog and asserts the warning is shown for the routed case.
* These are mocked/logic tests; the compiled-PDM evidence is the scenario table above.

## Blank-program fix: explicit program validation (2026-10-29)

**Observation.** The Pricing page (`Source: PDM snapshot`, Site 1, currency `All`) still showed several `28 (propo...)`
text blocks for `GESNNU.105508F` (Nevi/Layout Screens).

**Root cause.** Nothing in the Maintenance workflow sets `snapshot.generation_program`; it stays `""` unless the user
opens Review > Generation > Program. `PricingPage._params` passed that `""` as `program_code`, `PricingService`
accepted it, and `PDMRepository.fetch_global_option_increment_prices` treats `program_code in ("", "revive")` as
Revive, running `_resolve_global_fabric_targets` and routing Fabric Type `8` to colour option `28`. The previous
commit only added a *warning*, so computation and its `28=` text blocks were still produced. Nothing overwrote or
mis-mapped a selected program: the program was blank. (Export: `ocd_export_service` falls back to a name-derived key,
which is never `layout_studio`/`nevi_enhanced`.)

**Fix.**
* `services/pricing_program.py` (new): `validate_pricing_program` accepts only Layout Screens -> `layout_studio`,
  Nevi Screens -> `nevi_enhanced`, Revive -> `revive` (codes or those labels); blank or anything else raises
  `PricingProgramError` with the remedy. Blank is never defaulted to Revive.
* `PriceParams.require_program` (default False): `PricingService.compute`/`compute_streaming` validate before any
  PDM query when set. `PriceMdbExportService.export(require_program=...)` blocks preview and write.
* `PricingPage` sets it only when the active module is Maintenance, shows the error on Compute and blocks export.
  Development and unspecified-module behaviour, the repository, and Revive `28=` routing are unchanged.

**Tests.** New `tests/test_pricing_program_validation.py` (19): three programs resolve; blank/unsupported rejected;
the selected program reaches the repository and routing (`8=` for Layout/Nevi, `28=` for Revive) in `compute` and
`compute_streaming`; blank/unsupported block before any query; Development unchanged; export blocked. Page-level
tests added in `test_pricing_page_text_blocks.py` and `test_pricing_export_workflow.py`. Existing Maintenance fixtures
that relied on a blank program now set an explicit one.
Results (`QT_QPA_PLATFORM=offscreen`): full suite **4546 passed, 11 skipped, 22 subtests, 0 failed** (220 s).

**Evidence limits.** Mocked/logic tests only; no compiled-PDM or live-MDB run was made for this fix, and the
screenshot's snapshot was not inspected directly. The root cause is established from the code path.

## Limitations
* One representative product per case, GBP and site 1 only; EUR not run. Existing-row parity is shown only for
  rows the scenario made stale or that PDM actually priced; "no-op" runs (X2, X4, X5, X6) are not discriminating.
* Aeron/Always global pricing is NOT APPLICABLE only for the products tested; the series' other products were not
  scanned for super products.
* Starting MDBs are the working-copy OCDs at the time of the run, not a controlled baseline.
* Revive fabric rows: legacy leaves them unresolved, so their values rest on the existing MDB rows only.
* pCon rendering is out of scope. VARCOND legacy parity is open.

## Reproduce
```
# per series copy: <root>\<Series>\pcr_data_com_ocd.mdb (never the live workspace); PDM bin copied to <pdm_bin>
python scripts/pdm_differential/cross_series.py --source-root <root> --pdm-dir <pdm_bin> --work <work> --out raw.json \
    --scenarios X1_aeron_article,X2p_always_article_stale,X3_nevi_screen_global,X3b_nevi_screen_placeholders_then_global,X4_layout_screen_global,X4p_layout_screen_global_stale,X5p_layout_article_stale,X6p_nevi_article_stale,X7_revive_screen_global,X8_layout_screen_pdm_as_revive
python scripts/pdm_differential/cross_series_evidence.py raw.json --out evidence.json
```
Run scenarios sequentially (shared SQL connection and 32-bit MDB bridge); a scenario takes about 10-35 minutes.

To unblock VARCOND parity, authorise a non-production SQL target (server and database whose name contains
test/dev/uat/sandbox) and a group filter/category id, then run `services/legacy_varcond_bridge.py` against
`GESCRNNU.105508F`, `DWE3SCRNNS.105516F` and `RY3SCRNNB.105512F` with `confirm_non_production=True`.
