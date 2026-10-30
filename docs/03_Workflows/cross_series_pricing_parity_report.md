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

## Blank-program `28=` routing: diagnosis kept, mandatory validation withdrawn (2026-10-29)

**Observation.** The Pricing page (PDM snapshot, Site 1, currency `All`) showed `28 (propo...)` text blocks for
`GESNNU.105508F` (Nevi/Layout Screens).

**Proven by code path.** `snapshot.generation_program` is `""` unless Review > Generation > Program is set;
`PricingPage._params` passes it through; `PDMRepository.fetch_global_option_increment_prices` treats
`program_code in ("", "revive")` as Revive and runs `_resolve_global_fabric_targets`, routing Fabric Type `8` to
colour option `28`. This is the legacy-compatible blank handling and was not changed. Previous commit 8d85fca warns
when routing happened only because the program was blank.

**Regression and correction.** Commit a420cf4 made a program mandatory in Maintenance (Compute, preview, export),
which blocked the previously working workflow. That page/export enforcement has been removed; the page, export
tests and fixtures are back to 8d85fca. Retained, opt-in and **off by default** (no existing caller enables it):
`services/pricing_program.py` (`validate_pricing_program`), `PriceParams.require_program`, and
`PriceMdbExportService.export(require_program=...)`, with tests in `tests/test_pricing_program_validation.py`
covering explicit `layout_studio` / `nevi_enhanced` (`8=`) and `revive` (`28=`) routing, blank/unsupported rejection
when opted in, and unchanged behaviour when not. A page test pins that a blank Program does not block Compute.

**Still unresolved.** What the correct routing is for a blank Program on a Layout/Nevi series. Evidence: under the
explicit programs the compiled legacy PDM matches the MDB's `8=` rows; a blank program yields `28=` rows that the
existing export safeguard rejects (blocked, which is not parity). Whether the application should infer the program
for those series, or require it, is an owner decision; no mapping or requirement was introduced. `28=` was not
globally replaced; Revive routing is unchanged. Evidence is mocked tests plus the earlier compiled-PDM runs; no
live PDM/MDB was used for this correction.

## Blank Program: resolved from the linked repository (2026-10-29, follow-up)

**Root cause (unchanged).** Blank `snapshot.generation_program` reaches `PDMRepository.fetch_global_option_increment_prices`
as `""`, which it handles as Revive (`28=`). The series name (`range_name`) is not an input to routing, and
`XocdExportService.program_key` cannot yield `layout_studio`/`nevi_enhanced`.

**Authoritative metadata found.** The Maintenance state (`context.maintenance_snapshot`) holds the MDB of the repository
the user linked to this PDM product (`MaintenanceRepositoryLinkService`); its package `reg_ProgramCode` is imported as
`mdb_import_snapshot.product.code`. `PriceParams.program_code` is documented as "PDM text_programcode / package
reg_ProgramCode", and legacy price update reads `tCOMd_Package.reg_ProgramCode`.

**Change.** `PricingPage._program_code`: explicit Review program first; otherwise, **only in Maintenance** and only when
the Maintenance state is aligned to the active snapshot, `program_from_linked_repository` returns that package code if
(and only if) it is `layout_studio`, `nevi_enhanced` or `revive`. Anything else returns `""` and the previous
behaviour (including the 8d85fca routing warning) applies. No mandatory validation (`require_program` stays off), no
name or article-number guessing, snapshot not mutated, Development unchanged, `28=` not replaced globally.

**Not verified.** The real `reg_ProgramCode` values of the Layout, Nevi and Revive MDBs. No MDB was read (constraint),
and the only fixture in the repo uses `"NEVI"`, which is deliberately *not* matched. If production codes differ
(e.g. `NEVI`), blank-program behaviour stays as before for that series until the exact codes are confirmed and added
to `_ALIASES`; that is the smallest remaining decision. Evidence for this change is mocked tests; no compiled-PDM or
UI run was made.

## Option-code routing audit: where `8=` is read and `28=` is introduced (2026-10-29)

**Question.** Should Maintenance pricing read/generate Fabric Type `8=` instead of Finish/Colour `28=`?

**Flow, by code.**
1. *Source read (`8=`)*: `PDMRepository.fetch_global_option_increment_prices` runs PDM's Global query. Rows carry
   `OptionId` = the priced Fabric Type option (8) and the price/cache sequence is unchanged by routing.
2. *Target introduced (`28=`)*: only `PDMRepository._resolve_global_fabric_targets`, which runs after the prices and only when
   `program_code.strip().casefold() in ("", "revive")`. It sets `GlobalOptionPriceRow.TargetOptionId` from PDM metadata
   (`Option.IsFabric=2` option present in the component's `FeaturePositionString`).
3. *Record build*: `PricingService.build_records` writes `variant_condition = "<item> <TargetOptionId>=<code>"` (export
   target) and keeps `pdm_lookup_code = "<item> 8=<code>"` (source). So `8` is the **source** option, `28` the **target**
   option; both appear on the same record. `PriceMdbExportService` treats them as source/target and matches existing MDB rows.
4. *Program*: `PricingPage._program_code` passes the explicit Review program, else (Maintenance only) the linked
   repository's `reg_ProgramCode` if it is exactly `layout_studio`/`nevi_enhanced`/`revive`, else `""`.
   Price Relation / VARCOND is a separate path and never rewrites `8=` to `28=` (see Price Relation section above).

**What the evidence proves.**
* Layout/Nevi under explicit `layout_studio`/`nevi_enhanced`: compiled legacy PDM matches the MDB's `8=` rows; the Workbench
  writes the same `8=` conditions and never calls `_resolve_global_fabric_targets`. **8= is correct; no mapping.**
* The compiled legacy PDM **never produced a `28=` row in any run**. For Revive it reported the 312 fabric rows as
  unresolved. So `8`->`28` is **not legacy behaviour**; it is the Workbench's owner-requested Revive compatibility policy
  (docs/03_Workflows/pricing_pdm_parity.md, "Revive component fabric-family routing"), validated only by the existing Revive
  MDB rows (`28=`). It was deliberately extended to a blank program so an unset optional setting does not bypass the relation.
* Layout/Nevi components carry the same `|8|28|` metadata as Revive, so no PDM metadata discriminates the series. Only the
  program does. A blank program therefore cannot be told apart from Revive by the data.

**What is NOT proven.** What compiled legacy does for a *blank* `programCode` on Layout/Nevi (only `layout_studio` and
`revive` were run; blank was run on the Workbench side only), and the real `reg_ProgramCode` values of the three MDBs.
No PDM/MDB was queried or run for this audit (production PDM excluded by instruction), so no parity is claimed.

**Decision: no routing change.** Making a blank program stop routing to `28=` would break the legitimate Revive blank-program
workflow and contradict the 25-Oct policy; making the choice by program name would be new automatic Program mapping; making
the program mandatory was withdrawn. None is supported by evidence, so none was done. The `28=` the user still sees is the
blank-program path: either Review > Generation > Program is unset and the linked repository code did not resolve (unverified
code values, see above), or the series is Revive. Setting the program to `layout_studio`/`nevi_enhanced` yields `8=`.

**Added.** `tests/test_fabric_option_routing_matrix.py` (mocked logic tests, **not** compiled-PDM evidence): `8=` source
identical for every program; explicit layout/nevi -> `8=` target; revive and blank -> `28=` target with `8=` source lookup;
blank-program warning present only when routing was caused by a blank program; `require_program` stays off.
Existing coverage retained: export safeguards (`test_pricing_fabric_targets.py`, `test_price_mdb_export_service.py`),
program resolution (`test_pricing_page_text_blocks.py`), Development unchanged (`test_pricing_page_program_...` case).

**Tests.** Full suite `QT_QPA_PLATFORM=offscreen`: 4565 passed, 11 skipped, 0 failed (220 s). Two earlier full runs aborted
with a Windows access violation in `tests/test_progress_popup_lifecycle.py` (Qt teardown, intermittent: the file passes 24/24
alone, and the suite passes without and with the new file); this flake is unrelated to pricing and is not fixed here.

**Open owner decision (smallest remaining step).** Confirm the real `reg_ProgramCode` of the Layout/Nevi/Revive MDBs, and
authorise a non-production legacy run with a blank `programCode` on Layout. Only then can blank-program routing be changed
with proof.

## Legacy source review and live PDM check (2026-10-30)

Authorised by the owner: legacy source `PDMMaintenance/PriceMaintenance.cs`, `UpdatePriceThread.cs`, `PConPriceUpdate.cs`
(`Desktop\PDM`) read directly, and read-only SELECTs against PDMLive. No MDB was written.

**Legacy facts (source).**
* `UpdatePConItemIncrementalPrice` (PriceMaintenance.cs:9128) reads `ItemOptionValues` for every option value of the component
  (no `IsFabric` filter), builds `<item> <OptionId>=<code>` and matches it to the existing MDB `com_VariantCondition`
  (`parsePConOrderCode`). **There is no `8`->`28` mapping anywhere in legacy**; a row only updates if PDM's own option id matches
  the MDB row, otherwise it is "did not match".
* `programCode` is never blank in legacy: `PConPriceUpdate.InitWorkspace` (line ~1527) sets `text_programcode` to the
  **workspace folder name, lower-cased, spaces -> `_`**, and passes it as both `programCode` and `actualProgramCode`;
  `actualProgramCode` must equal the MDB package `reg_ProgramCode`.

**Live PDM (read-only).** For `GESNNU.105508F`, `DWE3VNNS.105516F` and `RY3SNNB.105512F` every priced `ItemOptionValues` row is
Fabric Type (`OptionId 8`, `IsFabric=1`); **no colour-level (`28`) price exists**. So the price value is always the Fabric Type
price; `28=` is only a target relabel. Fetch with program `""` or `revive` gives (source 8 -> target 28) for all rows;
`layout_studio` gives (8 -> none).

**Root cause of the `28=` seen on Layout/Nevi.** The Workbench let a blank Program fall into Revive routing, but a blank program
does not exist in legacy: legacy derives it from the workspace. **Fix:** `PricingPage._program_code` now follows legacy.
Explicit Review program first; in Maintenance, else the workspace folder of the linked repository MDB
(`services.pricing_program.program_from_workspace_path`, only when the Maintenance state is aligned to the snapshot); else the
previous package-code lookup. No mandatory validation, snapshot not mutated, Development unchanged. Layout_Studio ->
`layout_studio` -> `8=`; Nevi_enhanced -> `nevi_enhanced` -> `8=`; Revive -> `revive` (28 target retained, see below).

**Revive routing removed (owner decision, 2026-10-30).** `PDMRepository.fetch_global_option_increment_prices` no longer calls
`_resolve_global_fabric_targets`, so no program (blank, `revive`, `layout_studio`, `nevi_enhanced`) remaps Fabric Type `8` to a
colour option: records are `<item> 8=<code>` exactly as legacy builds them. The helper and `TargetOptionId` support remain in the
code but are unused by the fetch. The blank-program routing warning can no longer fire.

**Consequences / remaining differences (not hidden).**
* **Revive MDBs hold `28=` rows.** With `8=` records the export preview will not find those rows; it will plan inserts of `8=` rows
  (or block) instead of updating the `28=` ones. This is the legacy outcome ("did not match"), but review the **preview** before
  any Revive write. Not exercised against a Revive MDB in this change.
* The legacy-derived program is applied for any workspace name (as legacy does); only Layout, Nevi, Revive, Aeron and Always
  workspaces have compiled-PDM evidence. Article and `8=` global parity under explicit programs is from the 10-27/28 runs.
* No new compiled-PDM run was made for this change; tests are mocked. Legacy VARCOND parity remains NOT RUN.
* Superseded: the earlier "Revive `8`->`28`" statements above describe the behaviour before this change.

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
