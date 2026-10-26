# Legacy VARCOND parity review

**Status: source-level (compiled IL) review plus runtime-verified pure helpers. Exact generator parity is NOT proven: no legacy generation run was executed because no verified non-production database was available.**

Scope: `PDMMaintenance.VarCondThread.execThread` versus the Workbench super-product generator `services/varcond_service.py`. The non-super-product `PricingRelationService` path is a separate scope and is not covered.

## Evidence classes

| Class | What it is | Where |
|---|---|---|
| **Runtime, real legacy** | Pure helpers (`parseAttributeNameAsPConProperty`, `ParsePConPropertyName`, `SIFImport.camelCase`, `isInteger`) executed from the real `PDMMaintenance.exe` 1.0.9686.24988 (SHA-256 prefix `494CC99E4C99`) over 355 vectors; Python ports compared to the recorded output | `scripts/varcond_parity/run_legacy_helpers.ps1`, `fixtures/helper_*.json` |
| **Runtime, real legacy (binding)** | Bridge `dryRun` against the real assembly: signatures, delegate type, static fields, x86 process. No DB | `verify_legacy_binding`, `tests/test_legacy_varcond_bridge.py` |
| **Source-level (IL)** | `execThread` and `getOptionIncrementSuffixes` read from `ildasm` output (the C# source is not in this checkout). Expectations in `fixtures/legacy_exact_cases.json` are hand-derived from it | `tests/test_varcond_legacy_parity.py` |
| **Not done** | Any run of `execThread`, i.e. real legacy generated text | blocked, see below |

Mock tests in `test_legacy_varcond_bridge.py` verify adapter behaviour only.

## Helper parity (runtime-confirmed)

Zero differences: 297 `parseAttributeNameAsPConProperty` vectors, 24 `camelCase` vectors, 12 `ParsePConPropertyName` vectors (new port `_parse_pcon_property_name`), 11 `isInteger` quantity cases.

## What legacy really does (from IL)

Pass 1, per parent in the caller's list: BOM rows `ORDER BY CONVERT(INT, ComponentSequence)`; quantity defaults to 1 and is replaced only by an all-digit text (`isInteger`); attribute rows via one SQL (`SELECT DISTINCT`, order by `DisplayOrder`, parametric `SUBSTRING(Item, prefixLen+1+Σ ABS(HDO) of strictly lower DisplayOrder, ABS(HDO))`); property name = SQL second-word capitalisation, `parseAttributeNameAsPConProperty`, spaces to `_`; exclusion = `exclusions.IndexOf(prop) > -1`; substitutions; one IF text per parent built from non-excluded rows. For each BOM row it appends `(target, shared IF, qty)`. A parent with no BOM and at least one accepted term appends the article code with its **Product name removed**.
Pass 2, per target: `$VARCOND = 'sub' IF…`, `,\r\n$SET_PRICING_FACTOR('sub', q) IF…` when q > 1, then option-increment suffix rules; entries joined by `,\r\n`, final `\r\n`; delivered once as a `VARCOND:` status.

## Differences, with intended behaviour

| # | Difference | Legacy (IL) | Workbench default | Status |
|---|---|---|---|---|
| 1 | IF per component | shared parent IF for every row | filtered by `component_head_attrs` | **Confirmed.** Deliberate Workbench feature (`validate_varcond.py` case 11). `legacy_exact` follows legacy |
| 2 | Duplicate rules | one per BOM row, no dedup | identical rules dropped | **Confirmed.** Deliberate (case 12) |
| 3 | Unresolved parametric code | emits `Prop = ''` | auto-excluded | **Confirmed.** Deliberate (case 10) |
| 4 | Parent order / selection | caller's list order | snapshot dict order, all BOM parents | **Confirmed**; `article_codes` added (legacy mode) |
| 5 | BOM order | integer `ComponentSequence` | load order | **Confirmed**; sorted in legacy mode |
| 6 | Whitespace-only prefix | `"  "` gives `.` property prefix | no prefix | **Confirmed** quirk, reproduced in legacy mode |
| 7 | `RYT*` / `RYMPSH*` suffix form | `'<optId>=<target>_' + Name` | `'<target> <optId>=' + Name` | **Confirmed**, ported in legacy mode |
| 8 | HZ13/HZ14 fabric rename | `Upper_/Lower_Front_Fabric_Type` | none | **Confirmed**, ported in legacy mode |
| 9 | Suffix-name substitution | plain `IndexOf`/`Replace` | guarded IF-style substitution | **Confirmed**, ported in legacy mode |
| 10 | Suffix name de-duplication | by property name | by option id | **Confirmed**, ported in legacy mode |
| 11 | Non-BOM parent | emits rule for article minus Product name | none | Not reproducible: snapshot has no Product name. Legacy mode warns |
| 12 | Prefix length 0 | modal Yes/No dialog (No aborts run) | silent | Legacy mode warns, assumes Yes |
| 13 | `RYMPSH`/`RY3VNN..HW`/`RYT`/`RY2U` fixed names (`Panel_Finish`…) | re-call `getOptionIncrementSuffixes` with the same cache key after an empty result, then require non-empty | not ported | Appear **unreachable** (inference from IL; runtime unconfirmed). Not ported |

**Intended behaviour decision.** Differences 1-3 are documented Workbench refinements with their own validators and are consumed by `PricingRelationService`, so the default output is unchanged. `generate(..., legacy_exact=True)` reproduces legacy literally. Which mode should be the default is an owner decision.

## Input (data-source) differences, not algorithm

- **Option-increment suffixes (largest gap).** Legacy takes names/ids from stored procedure `PDMOptionDataReportWithIncBase(item, 1, 1)` (rows with non-empty `IncPriceBase`, after item pre-processing for items without `.`/`F`/`MET` and `-` items). The snapshot carries `ItemOptionValues`, a different source. Suffix parity is **unverified**; legacy mode warns about it.
- Snapshot keeps one term per attribute name (first wins); legacy returns every `BaseAttributeValues` row.
- Snapshot stores NULL `OrderCodeValue` as `""`; SQL distinguishes them.
- Snapshot stores `Quantity` as `int(...)`; legacy accepts only all-digit text (a decimal column such as `2.00` yields 1 in legacy). Column type not verified.
- `getArticlePrefixLength` is reloaded from `Notes`/category in the snapshot (separate port).
- Legacy output is also affected by `Environment.UserName` branches in `ConnectionFactory`.

## Harness

`scripts/varcond_parity/`: `run_python.py` (fixture to text + input manifest), `compare.py` (exact text, separate normalised view, missing/extra/duplicate/ordering/pricing-factor differences, input-manifest diff, attribution that never blames the algorithm unless manifests are identical), fixtures. Legacy side: feed the bridge JSON response and a legacy input manifest of the same schema. A SQL capture tool for that manifest does **not** exist yet.

## Blockers to proving exact parity

1. **A verified non-production SQL Server + database** (server, database, read-only login, written confirmation) containing known super-products. No SQL Server or LocalDB exists on this machine, and the legacy `ConnectionFactory` decides its own target from `Global` plus per-user logic. A name-only guard is not proof; no run was executed (one early run of the pre-attestation bridge with a fictitious server name `s` hung at a legacy dialog and was killed after 60 s).
2. The body of `dbo.PDMOptionDataReportWithIncBase` and its output for those articles (read from that same database).
3. A SQL capture of the exact input rows (components, attribute rows, prefix length, `Quantity` type) for the same articles, to build the legacy input manifest.
4. The C# source (`VarCondThread.cs`, `PriceMaintenance`, `CADMaintenance`) is not in this checkout; findings come from the compiled IL of build 1.0.9686.24988.

## Verification record

- Bridge build: `MSBuild /restore /p:Configuration=Release` exit 0 (needed `/restore`; first failure was `NETSDK1004`).
- `dryRun` against the real assembly: ok. Refusals (prod-looking name, `live` inside a test name, missing attestation): verified on the built exe.
- Tests: see the completion report. Full-suite failure `test_product_repository_link_actions::test_status_message_reflects_loaded_product` also fails on base `f8adc66`; `scripts/validate_article_property_link.py` exits 1 identically on base.
