# OBX 724 Failure Investigation

Status: IN PROGRESS. All 724 reported option failures are corrected, and every failed record passes full live option/pricing validation in an explicit GBP or EUR trial at the authoritative 2026-11-03 effective date. Matched source OBX data also passes at that date for 44 failed occurrences. The feature is not frozen: source files are still missing for 680 failed occurrences, and original report settings/provenance and an interactive PDM comparison are still needed for original-source parity validation.

## Problem

Input: `C:\Users\siaoca\Downloads\OBX_Validation_Consolidated (1).csv`.
SHA-256: `44262e319248f42cbabc8dd32e2b08c74565186de4247c925bb7d678c42a8286`.

The full report contains 2,017 data rows: 724 failed SKU records, 1,292 valid SKU records and one short elapsed-time summary row. The 724 failures represent 362 distinct SKUs, with both occurrences retained individually by their report CSV row. There are 40 failed base codes, three product families, 18 distinct option strings and 18 exact error messages. Every reported failure is at option position 2; every failed SKU has exactly two options.

| Family from live PDM | Failed Records |
| --- | ---: |
| Gould Sofa | 600 |
| Perron Bun Lounge Collection | 88 |
| Muecke Wood Collection | 36 |
| Total | 724 |

| Reported Option String | Failed Records |
| --- | ---: |
| G 01FED | 60 |
| G 01H | 48 |
| G 01PE | 48 |
| C 01CI | 48 |
| C 01CU | 48 |
| S 154D | 48 |
| S 101FI | 8 |
| S 103H | 8 |
| S 01HL | 8 |
| S 02TOS | 48 |
| A 02AN | 60 |
| C 01AL | 52 |
| S 001HER | 40 |
| C 12MO | 40 |
| Y 01 | 40 |
| C 01IS | 40 |
| Y 02B | 40 |
| C 100T | 40 |

## Root Cause and Evidence

The controlling path is `ObxValidationService.validate` -> `SifValidationService._validate_group` -> `_verify_selected_options`. The lookup is `PDMRepository.fetch_item_validation_options`, which calls `dbo.PDMOptionDataReportWithIncList` with `excludeFabricColours=0`. The wrapper previously dropped `ParentOptValId` and `ParentOptValCode`, and the verifier unconditionally discarded active `IsFabric=2` colour rows.

PDMLive on DBCHIP12V was accessed read-only on 2026-10-12. For every one of the 724 failures, the rejected token exactly matches an active item-scoped colour row (`Status=1`, `IsFabric=2`, parent option 8512). Its active fabric parent and the selected ancestor group are present in the captured metadata. These are suffix-style colour codes: `01FED` depends on `FED#`, rather than starting with that band. `FED#` in turn depends on family-specific group `G`. `001HER` -> `HER#` -> `S` is a different dependency chain. The 18 option patterns were all checked individually; no expected outcome was inferred from one sample.

The complete pre-fix parameterized reproducer failed on all 724 records. After correction all 724 pass their option check, and replacing the group with a different active group is rejected for each record. This establishes one shared confirmed software root cause, not 724 independent defects. No genuine option-data error was established among these records. Monetary validity is a separate gate.

No local PDM snapshot matched any of the 40 failed base codes. Existing Article OBX generation, permutation and price services were inspected: they generate from repository snapshots and do not decide this validation error. No change to those services is justified by these failures.

## Fix and Scope

- `repositories/pdm_repository.py`: retain the two parent-value metadata fields already returned by PDM.
- `services/sif_validation_service.py`: allow an exact active colour through its matching active fabric parent and selected active ancestors; consume the parent's option group once.
- `tests/test_sif_obx_validation_parity.py`: all 724 failures, incompatible alternatives for all 724, all 1,292 original-valid option outcomes, metadata retention, service-level pricing gates, order independence, unknown/inactive/orphaned colours and duplicate protection.
- `scripts/investigate_obx_failures.py`: complete inventory, source matching, live reference capture, record reconciliation and explicitly labelled reconstructed currency trials.
- This report and the order-validation workflow documentation.

Pricing calculations, component quantities, source product data, parser tokenization, component-local matching, duplicate-row protection, global deduplication, duplicate exports, `operation_control`, cancellation, 8+8 workers, progress/elapsed-time reporting, Bulk Update, Development and Maintenance workflows are unchanged. Existing tests exercise these protected paths. Builder Table and generator code were not modified; interactive Builder Table/downstream parity is not claimed.

## Artifacts and Reproduction

- `reconciliation.csv`: all 724 failures, original diagnostic fields and CSV row, family/base/option grouping, responsible code, fix, option outcome, full-source outcome, remaining limitation and evidence.
- `original_valid.csv`: all 1,292 original-valid records, available source-validation results and same-context before/after currency comparisons.
- `pdm_reference.json`: captured item-scoped option metadata for failed and control items, with database, date and site provenance. Regression tests replay this without a live connection.
- `summary.json`: record counts, exact-error/base/option/root-cause groups and verification totals.
- `currency_trials.json`: full live pricing trials in explicit GBP and EUR contexts on 2026-10-12 and 2026-11-03, with original/corrected behavior side by side. These are reconstructed CSV checks, not proof of original source date/currency.

```powershell
$env:PYTHONPATH = '.'
python scripts/investigate_obx_failures.py "$HOME\Downloads\OBX_Validation_Consolidated (1).csv" --output docs/04_Reference/OBX_724_Investigation --sources "$HOME\Downloads" --live --validation-date 2026-10-12 --currency-trials GBP EUR --reference-trial-date 2026-11-03
python -m pytest tests/test_sif_obx_validation_parity.py -q
$env:QT_QPA_PLATFORM = 'offscreen'
python -m pytest -q --tb=short
```

The original-behavior pricing comparison filters dependent-colour rows before invoking the shared verifier, reproducing the pre-change option behavior; all pricing and eligibility code is unchanged. A fresh validation cache is used for each side. Trials do not hardcode acceptance, change prices or infer the report's omitted currency. The first default-window trial stalled and was cancelled. The completed diagnostic uses report-wide windows, per-item metadata reuse and a 60-second query timeout only within the script; production query windows/workers are unchanged.

## Validation Results

| Gate | Result |
| --- | --- |
| Failed records individually accounted for | 724/724 |
| Confirmed software root cause | Dependent-colour exclusion, 724 records |
| Corrected option checks | 724/724 |
| Incompatible group/colour negative checks | 724/724 rejected |
| 2026-10-12 full live pricing trials | 18 pass in a GBP/EUR context; 706 price mismatches in both |
| 2026-11-03 full live pricing trials | 724/724 pass in a GBP/EUR context |
| Original-valid records, 2026-11-03 live pricing | 1,292/1,292 match in a GBP/EUR context |
| Original-valid records, 2026-10-12 live pricing | 126 match in a GBP/EUR context; 1,166 mismatches |
| Original-valid before/after code regressions, both dates | 0; all 1,292 records compared |
| Confirmed genuine option-data errors among the failures | 0 |
| Missing authoritative option references | 0 |
| Known unresolved software defects in these failures | 0 |
| Original failed-source confirmation pending | 724 |
| Failed occurrences with matched source data passing at 2026-11-03 | 44 |
| Failed occurrences without a source match | 680 |

The scheduled-date test is grounded in a read-only query of all linked product price matrices/formulas: live PDM has formulas effective 2026-11-03 for these families. Every reported amount matches one explicitly tested currency under that scheduled price list. The current-date differences are therefore consistent with effective-date context, not evidence of a pricing algorithm defect. This does not establish the omitted original report date/currency. No price, quantity, formula or date-selection logic was changed to force a pass.

Focused option/integration tests and artifact-accounting checks pass (2,144 tests in the validation file). The complete suite has 2,500 passes, four skips and one pre-existing failure in `DuplicateReportTests.test_not_called_from_validation_paths`: it rejects the already-existing `_on_export_duplicate_details` calls in the OBX UI. Those calls were verified in committed HEAD; neither file was changed. `git diff --check` is clean. The new ancestor-attribute diagnostic was corrected; pre-existing Pylance warnings in the shared service remain, including its missing `Any` import and nullable conversions. Unrelated type cleanup was not performed.

## Remaining Gates

The CSV does not record the original OBX source filename, source row/index, currency, validation date or selected site. Even though its price headers say EUR, available matched records include GBP and EUR, so assigning EUR to all rows would fabricate context. The first recursive Downloads search found source matches by exact SKU and price for 176 originally valid records and none of the failures. Files became available during the investigation: the final search matches 200 originally valid records and 44 failed occurrences, leaving 680 failures unmatched. Candidate paths, sequence/index, currency, dates and features are preserved where available; matches are evidence, not a claim that the original source filename is known. The Bun GBP files explicitly carry price date 2026-11-03, independently supporting the effective-date trial. All 44 matched failures pass source-context validation at that explicit date.

Current-date validation of the initially available 176 original-valid occurrences produced 98 price differences even before the code change. The final scan has 122 such differences among 200 original-valid occurrences, plus current-date price differences in the 44 matched failed occurrences. They must not be called regressions or assumed to be product-data defects: the explicit 2026-11-03 price-list checks match the reported amounts. Same-date, same-currency before/after checks distinguish code changes from existing price/context differences.

To finish original-source validation, supply the files for the 680 unmatched failed occurrences (listed individually in the reconciliation), the remaining original-valid files, and confirm the report's actual validation date/site settings and source provenance. The 724 report rows already have individually recorded option and full live price evidence; none are dropped or reported as fully fixed merely because the option error cleared. Interactive legacy PDM validation is required before a parity freeze. No branch, commit or push was created.