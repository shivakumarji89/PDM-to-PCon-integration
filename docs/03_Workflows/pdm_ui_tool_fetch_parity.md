# PDM UI vs tool pricing fetch parity

**Evidence date:** 2026-10-18
**Scope:** Article Price and Global Price only.
**Data source:** the non-production `DBCHIP11V.PDMTEST` database, using the
local PDM build `1.0.9686.24988` and its matching `PDMMaintenance` source.
No production database or MDB was accessed, and no export workflow was run.
The non-production Revive staging MDB mentioned below was inspected with
read-only queries only.

## Result

| Scenario | Status | What the evidence establishes |
|---|---|---|
| Article Price | **MATCH**, evidence B, tested fetches | 96 scenarios, 936 base/increment observations, all exact against source-equivalent SQL. No Article calculation change in this update. Physical duplicate ID selection and actual UI/MDB results remain **NOT VERIFIED**. |
| Global Price | **MATCH**, evidence B, tested source fetch/calculation/lookup metadata; direct-item and observed component-parent target conditions covered; worker matching remains internally inconsistent for some programs | Dedicated catalogue-scoped source queries match 1,052 increment observations in 108 scenarios. Direct-item `variant_condition` follows `AddMissingGlobalPricingRecords`; component rows with the source's `OptionId=ITEM_suffix` shape retain that component-parent target key. Existing-row selection is covered by fake-target tests and an exact Revive staging-row fixture; physical UI/MDB results and arbitrary parent-option mapping remain **NOT VERIFIED**. |

These are bounded results, not a claim of universal or full UI parity. The
actual PDM UI was not run against a pCon MDB. The live evidence below comes
from source-equivalent PDM SQL and read-only tool repository/procedure calls
against non-production PDM Test; target-MDB selection and record IDs remain
unverified.

## Current implementation and before/after measurement

The clean `main` baseline was safely fast-forwarded from `ab591a7` to
`199540b5d14c694f7ea733e92dcde026515f6bbc` before implementation. The intervening
remote commits concern Syteline, not these pricing methods. No branch, reset,
production SQL write, MDB write, or export was used.

Evidence levels in this section:

- **A:** actual original application output versus tool output: not captured.
- **B:** independently transcribed original source SQL/calculation against
  `DBCHIP11V.PDMTEST`, compared with actual repository calls: measured below.
- **C:** deterministic mocked regression tests: separate from live evidence.

### Changes and source rules

[`fetch_global_option_increment_prices`](../../repositories/pdm_repository.py)
now uses a dedicated source-query builder; it does not call the generic option
report procedure. The generic `fetch_item_option_increment_prices` remains
unchanged for other consumers. Both
[`compute` and `compute_streaming`](../../services/pricing_service.py) pass the
selected catalogue and generation program. An explicit `PriceParams.catalogue_id`
overrides `snapshot.product.catalogue_id`; a missing catalogue raises a query
error rather than issuing an unscoped request.

The reproduced path is `UpdatePriceThread.execThread` calling
`UpdatePConItemIncrementalPrice` with a selected item, `categoryId=-1` and
`categoryname=""`, not the separate category-wide UI modes:

- Initial `SELECT DISTINCT ... UNION SELECT DISTINCT`: direct catalogue items
  plus subitems with a catalogue parent. Item scope is `LIKE '%selecteditem%'`,
  not exact equality. Preserve SQL projection multiplicity; do not add a
  dictionary or another Python deduplication step.
- Resolve item product-code override, otherwise product product-code, for the
  selected site; retain `PriceMatrix`, requested `Currency`, `ProductRange`,
  `OptionValue.Status=1`, and `FabricBands.Application=1`.
- Preserve `lf`'s `NOT LIKE 'MRF7%'`, `av`'s `NOT LIKE 'AS7%'`, and the source
  `swoop` product predicate. Sort by the **SQL-projected** order code, not raw
  option code: for `WE51`, `61=MS` precedes `62=DS`.
- `Product_Code.BasePriceRef` selects `IncrementalPrice`, `IncrementalPrice2`,
  or `IncrementalPrice3`. Skip null selected raw increments.
- Replay the secondary `fnGetListPrice` query with the same scope, date, site,
  currency and rounding. Its predicate deliberately remains
  `itov.IncrementalPrice = selected_raw`, even for references 2/3; it does not
  repeat the active-status filter or specify ordering.
- Preserve the source's cache: compare the first item index with the first
  raw-increment index. Initial secondary processing takes the last non-null
  returned price; later cache reuse can take the first cached price. No
  secondary value leaves the source sentinel **-1**, not zero/null.
- Preserve the actual source helper's `count > -1` behavior, not its apparent
  intended multiple-option-ID test. For `revive` RYM/RYT, source lookup is
  `OptionId=ITEM_CODE` (e.g. `3848=RYMPSH.12SW_OKG`); other variable increments
  replace underscores with ` OptionId=`. The source's non-variable program list
  and WE51 exception remain distinct.

`GlobalOptionPriceRow` retains option-value ID, option ID, raw code, projected
source code, selected raw increment, price band, calculated price and source
lookup. `PriceRecord` persists `source_item` and `pdm_lookup_code`, separately
from the target condition; old snapshots default these fields to empty.
Substring-expanded items remain Global records. Direct-item stored conditions
follow `AddMissingGlobalPricingRecords`: ordinary rows use
`ITEM OptionId=Code`; `memo` uses `ITEMCode`. RYM/RYT worker lookup keys remain
`OptionId=ITEM_CODE` metadata and are not substituted for the generated target
condition for direct items. For component rows whose source key is the
numeric-option-prefixed `OptionId=ITEM_suffix` form, the target condition now
uses that key, matching the component-parent placeholder form. The non-production
Revive staging MDB (package 240, price list 12) contains both `RYMPSH.12SW`
and `3848=RYMPSH.12SW_OKG`; this is read-only target-row evidence, not a
production or UI export. Regression tests cover condition generation,
exact-key matching and export preparation. The general
`FeaturePositionString`-to-component-option mapping and physical UI/MDB export
remain unverified.
Product-code attachment and surcharge/base classification use source-item
metadata so these records do not accidentally become base records or update
only the last duplicate.

### Exact live matrix and metrics (B)

Main Global matrix: 27 item/program/catalogue/site configurations, each in GBP
and EUR at `15-Oct-2026` and `16-Oct-2026` (108 scenarios):

| Item | Program | Catalogues | Site |
|---|---|---|---:|
| `GEMAP.12S1M` | `layout_studio` | 394, 414, 660 | 1 |
| `GEBH.10` | `layout_studio` | 414, 521, 660, 662 | 1 |
| `DTW2B1T2.C` | `layout_studio` | 521, 662 | 1 |
| `GETH.1022FS4W` | `layout_studio` | 660, 662 | 1 |
| `MRFN121HWAP` | `lf` | 4, 652 | 1 |
| `AS7EA52AA`, `AS2EA32AA` | `av` | 4, 683 | 1 |
| `WE5110L` | `caper` | 4, 652 | 1 |
| `RY3VFTB.105512F`, `RYMPSH.12SW`, `RYTRFA.0812SW` | `revive` | 658 | 1 |
| `894-176092` | empty | 301 | 1 |
| `PDRSDNBFG.1114` | `ratio` | 755 | 1 |
| `1205S1BQ` | empty | 649 | 1 |
| `CN132AWAA` | `embody` | 4 | 9 |
| `CD63NC0600` | empty | 172 | 9 |

Article matrix: 24 item/program configurations, both currencies and dates,
site 1 (96 scenarios). The exact item/program pairs are `ARTICLE_CASES` in
[`fetch_parity.py`](../../scripts/pdm_differential/fetch_parity.py); they include
the ten layout items above/in the historical Article section, normal and
`lf`/`av` controls, WE51, all three Revive items, Monarch, `OAW102`, Ratio,
and `2003`. Article queries have no catalogue argument.

Complete Global comparison tuples are `(Item, OptionValueId, OptionId,
raw Code, calculated IncPrice, PriceBand)` plus source lookup for the lookup
stage. Currency/date/site/catalogue/program are scenario inputs. Decimal
values are numerically normalized; nulls and duplicate multiplicity are
retained. Business pairing key is `(Item, OptionValueId)`. After exact multiset
intersection E, remaining same-key pairs count as field differences V; residual
missing M and extra X also enter the denominator. Record accuracy is
`E / (E + V + M + X)`. Ordering is checked separately.

| Stage | PDM / tool | Exact | V / M / X | Record accuracy | Multiset scenarios | Ordered scenarios |
|---|---:|---:|---:|---:|---:|---:|
| Baseline Global processed increments | 1,052 / 1,128 | 596 | 244 / 212 / 288 | 596/1,340 = **44.48%** | 68/108 | 60/108 |
| Corrected Global processed increments | 1,052 / 1,052 | 1,052 | 0 / 0 / 0 | **100% in this matrix** | 108/108 | 108/108 |
| Baseline Global source-lookup preparation | 1,052 / 1,128 | 316 | 524 / 212 / 288 | 316/1,340 = **23.58%** | 60/108 | 52/108 |
| Corrected Global source-lookup metadata | 1,052 / 1,052 | 1,052 | 0 / 0 / 0 | **100% in this matrix** | 108/108 | 108/108 |
| Article fetch, before and after | 936 / 936 | 936 | 0 / 0 / 0 | **100% in this matrix** | 96/96 | 96/96 observed |

These Global totals contain **increments only**, not Global base observations,
and are not directly comparable with earlier percentages that included bases.
Source duplicate complete tuples: 0; baseline tool duplicate complete tuples:
48; corrected tool: 0. This does not say option IDs are unique: different
option-value identities sharing an option ID remain distinct. There are 16
empty corrected Global scenarios (negative controls), so the nonempty result
is also 92/92. Article includes base-function observations, including nulls;
this table is not a count of rows selected for export. Observed Article order
agreement cannot prove deterministic order where neither query orders rows.
Global ordering also has no additional tie-breaker, and its secondary query
has no `ORDER BY`; observed agreement is not a guarantee for tied rows or
future execution plans.

The main commands were:

```powershell
& .\.venv\Scripts\python.exe -B -m scripts.pdm_differential.fetch_parity --baseline-ref 199540b --article
& .\.venv\Scripts\python.exe -B -m scripts.pdm_differential.fetch_parity --article
```

Baseline exit 1 (measured mismatches); corrected exit 0 for the two Global
stages and Article stage present when that run started. The script subsequently added **separate** source-projection and worker-target
matching diagnostics; a run exits 1 when the parsed prepared condition does not
match the update worker's source key. This diagnostic exposes conflicting
source paths; it is not a measurement of `AddMissingGlobalPricingRecords`
output or physical MDB rows. Do not confuse source-fetch success with full
target-row verification.
The old `validate_pricing_parity.py` is a batching/self-consistency check, not
an independent original-PDM oracle.

### Demonstrated discrepancies corrected

- `MRFN121HWAP`: restore the source identities/multiplicity instead of the
  procedure's repeated/missing options.
- `AS7EA52AA`: correctly excludes all increments in the tested `av` scope.
  `AS2EA32AA`: restores 46 source identities per scenario and Application-1
  bands, including option-value 148810, rather than 30 procedure rows.
- `RY3VFTB.105512F`: restores source bands; RYM/RYT retain the actual projected
  and lookup codes as separate metadata from the AddMissing-generated target
  condition.
- `1205S1BQ`: source substring scope also includes `1205S1BQI`; the old exact
  item procedure omitted those records.
- `CN132AWAA` (site 9, reference 2) and `CD63NC0600` (site 9, reference 3):
  preserve the secondary field-1 equality and cache, including -1 when no
  secondary match exists. CD's two source bands are null, not procedure 2/3.
- `GETH.1022FS4W`: source inner joins return the applicable 16 rows. The old
  procedure's eight additional null rows have no selected-item increment
  association; filtering them explained this case but not the other defects.

### Variable populated fields are not quantity tiers

A fresh read of `sys.columns` finds three decimal base fields and three decimal
increment fields, `Product_Code.BasePriceRef`, and one integer
`ItemComponents.Quantity` (also `SPItemPricePercentage`); no numbered
quantity-tier matrix was discovered. PDM labels its price bases Euro, Dollar
and Tertiary. Populated field counts vary, not the actual schema:

| Series/item | Base fields 1 / 2 / 3 | Non-null increment assignments 1 / 2 / 3 | Tested selection |
|---|---|---:|---|
| Meeting Table `GETH.1022FS4W` | 850.64729330 / null / null | 24 / 0 / 0 | Site 1, ref 1 |
| Florence `1205S1BQ` | 4000 / 3780 / 3860 | 10 / 7 / 10 | Site 1, ref 1 |
| U-Series `2003` | 2050 / 3089 / null | 52 / 18 / 0 | Article control; no Global catalogue fixture |
| Monarch `894-176092` | null / 3849.89124000 / null | 0 / 17 / 0 | Site 1, ref 2; empty Global matrix control |
| Embody `CN132AWAA` | 1645 / 2483.78 / null | 11 / 14 / 0 | Site 9, ref 2 |
| CD `CD63NC0600` | null / null / 169 | 0 / 0 / 2 | Site 9, ref 3 |

Counts above include inactive assignments, before source scope/status filtering.
Price bands come independently from `FabricBands.Application=1`, not field
position or quantity. No generic quantity-column abstraction was added.

### Additional current-code checks and remaining boundary

The nonempty Ratio accessories item `RZTA.`, catalogue 405, site 1, GBP/EUR,
`16-Oct-2026` contributes **two supplemental scenarios**, not part of the
108-scenario aggregate. All four stages match 6/6 records, ordered, with
option-value IDs 287202/287203/287204, option ID 6867, codes DB3/DN2/DR1.
This exercises the worker's default category-name mode, **not** the separate
Ratio Worksurfaces/Screens modes.

```powershell
& .\.venv\Scripts\python.exe -B -m scripts.pdm_differential.fetch_parity --item RZTA. --dates 16-Oct-2026
& .\.venv\Scripts\python.exe -B -m scripts.pdm_differential.fetch_parity --item RYMPSH.12SW --item RYTRFA.0812SW --item MRFN121HWAP --item AS2EA32AA --item CN132AWAA --dates 16-Oct-2026 --currencies GBP
```

The prior run of the second command, before the current target-condition
builder, matched **318/318** processed/source-projection/source-lookup records
across 14/14 scenarios. Its worker-parser diagnostic matched **20/318 (6.29%)**
and had 298 field differences, no missing/extra rows. Those target-condition
counts are historical and do not measure the current builder.

Direct source inspection established incompatible paths: the update worker
compares plain source codes for `lf`/`av`/`embody` and `OptionId=ITEM_CODE` for
RYM/RYT, while `AddMissingGlobalPricingRecords` creates item-qualified
conditions for direct items and parent-option-prefixed conditions for eligible
components. The tool follows those separate shapes and retains worker keys as
metadata. A read-only Revive staging MDB inspection found the exact
`3848=RYMPSH.12SW_OKG` target condition alongside its base row in package 240;
the synthetic export regression verifies exact-key row selection. This does
not prove the general parent-option mapping or physical production behavior,
which remain **NOT VERIFIED**.

A fresh read-only PDMTEST run of the same five item inputs, restricted to
GBP/16-Oct-2026, completed seven actual catalogue/program scenarios:
processed fetch, source projection and source lookup were each **159/159**
exact and ordered. The current worker-target diagnostic was **0/159** exact
(159 same-identity field differences, no missing/extra rows), so the command
exited 1 intentionally. This confirms the source-path conflict for the
current AddMissing-shaped conditions; it does not compare against physical
target rows or establish their validity.

Nonempty live coverage includes default variable increments, `lf`/`av`
routing, WE51, RY3V/RYM/RYT, non-variable Embody, and Ratio accessories.
Read-only fixture discovery found no applicable nonempty `swoop` or `memo`
sample; their transcribed source rules remain **live-unverified**, as do other
non-variable families and category-wide modes. No program-rule coverage
percentage is invented.

Fresh permission checks return `HAS_PERMS_BY_NAME(...,'VIEW DEFINITION')=0`
and `OBJECT_DEFINITION(...)=NULL`. An authorized DBA-provided definition or
read-only `VIEW DEFINITION` grant is still needed to explain procedure internals;
the corrected Global path no longer depends on that procedure. Actual UI
capture, target list/text relationships, physical target rows, and physical
duplicate IDs remain unmeasured. The duplicate loop is covered with fake
ordered target rows, but neither original MDB query guarantees physical order.

### Regression and static validation (C)

- Focused Article/Global/source/export/text suite: **113 passed**.
- Broader non-GUI pricing suite: **159 passed**.
- GUI pricing export/text-block suite: **21 passed**, using installed Python
  3.12 and offscreen Qt; fake MDB adapters only.
- Editor Problems: no errors in changed Python implementation/tests; Pylance
  reports all six Global-fetch call sites signature-compatible.
- The editor test runner discovered no tests; pytest was used directly.
- Tests cover the source SQL/parameters, catalogue scope, all three field
  selectors, secondary/cache/null behavior, duplicates, WE51 order, actual
  RYM/RYT mapping, both compute routes, snapshot serialization and fake-target
  duplicate/base-prerequisite behavior. No real MDB writer was invoked.

```powershell
& .\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider tests\test_pdm_price_fetch_parity.py tests\test_global_price_source_parity.py tests\test_price_mdb_export_service.py tests\test_pricing_pdm_text_parity.py -q
& .\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider tests\test_price_list_service.py tests\test_price_list_targets.py tests\test_price_mdb_export_service.py tests\test_price_product_code.py tests\test_pricing_pdm_text_parity.py tests\test_pdm_price_fetch_parity.py tests\test_pdm_differential_report.py tests\test_global_price_source_parity.py -q
git diff --check
```

GUI command (existing Python 3.12 with PySide6):

```powershell
$env:QT_QPA_PLATFORM='offscreen'
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -B -m pytest -p no:cacheprovider tests\test_pricing_export_workflow.py tests\test_pricing_page_text_blocks.py -q
```

The historical sections below retain earlier captures and are not additional
measurements of this implementation. In particular, historical compiled-PDM
MDB outcomes do not establish current UI or physical-row parity.

## Implementations traced

### Original PDM UI

- `PConPriceUpdate.button_article_Click` starts `UpdatePriceThread` with
  `articlepricing=true`, `variableincs=false`.
- `PConPriceUpdate.button_global_Click` derives `variableincs` from
  `programCodeHasVariableIncs` and starts the same worker with
  `articlepricing=false`.
- `UpdatePriceThread.execThread` reads the item prefix (`Item.Notes`) and calls
  `PriceMaintenance.UpdatePConItemPrice`. For the Global path it also calls
  `PriceMaintenance.UpdatePConItemIncrementalPrice`.
- The source locations are `PConPriceUpdate.cs` (Article/Global handlers,
  lines 2021/2084), `UpdatePriceThread.cs` (worker, line 110),
  `PriceMaintenance.cs` (`UpdatePConItemPrice`, line 8714;
  `UpdatePConItemIncrementalPrice`, line 9128; and
  `AddMissingGlobalPricingRecords`, line 9921).
- `UpdatePConItemPrice` obtains base values from
  `dbo.fnGetListPriceByItem`. Its Article increment query is inline SQL over
  `ItemOptionValues`, `OptionValue`, `Item`, `Product`, `Product_Code`,
  `PriceMatrix`, `Currency`, `ProductRange`, and `FabricBands`; it filters
  `OptionValue.Status=1`, the selected item, site, and currency, and computes
  `IncPrice` with `dbo.fnGetListPrice`.
- `UpdatePConItemIncrementalPrice` first selects raw global increments for
  the selected catalogue, including direct catalogue items and component items
  whose parent is in the catalogue. It then calculates applicable values with
  `dbo.fnGetListPrice`. Its first query orders by `OrderCodeValue`.
- The Global source query uses an `INNER JOIN` from `ItemOptionValues` to
  `OptionValue`, requires `OptionValue.Status=1`, and joins the item either
  directly to the catalogue or through `ItemComponents` to a catalogue parent.
  It also joins the selected site's product code, price matrix, and requested
  currency; `FabricBands` is left-joined for `PriceBand`.
- `AddMissingGlobalPricingRecords` is a separate placeholder-creation step;
  the Global value update does not itself create a missing placeholder.

### Tool

- `PricingService.compute` obtains base rows through
  [`fetch_item_base_prices`](../../repositories/pdm_repository.py), then routes
  article items through the new
  [`fetch_article_option_increment_prices`](../../repositories/pdm_repository.py)
  method and global component items through
  [`fetch_global_option_increment_prices`](../../repositories/pdm_repository.py).
- The streaming compute path uses the same Article/Global routing.
- Article fetch now uses the source-equivalent inline SQL, including the
  `PriceMatrix`/`Currency` joins, active-option filter, `fnGetListPrice`,
  `PriceBand`, and PDM's `lf`/`av` filters when a program code is supplied.
  Both compute paths pass `PriceParams.program_code` or fall back to the
  snapshot's `generation_program`; the Pricing page supplies that snapshot
  value.
- Global fetch uses the catalogue-scoped source path described above. The
  filtered-procedure implementation discussed in historical captures below is
  superseded; the shared generic procedure method is unchanged.
- `PricingService.build_records` maps base rows to Article level `B` or Global
  records and priced option rows to level `X`. The target MDB export is separate
  and was not run.

## Article Price comparison

### Inputs

The source-equivalent query comparison covered the six `S1_article_gbp` items
and four additional representative item codes for both currencies:

- Items: `GESG.`, `GEWC.10`, `GEWDP.L`, `GEWDP.S`, `GEWQ.`,
  `GEPBPANNF.0608S4M`, `GEMAP.12S1M`, `GEBH.10`, `DTW2B1T2.C`,
  `GETH.1022FS4W`.
- Currency / selected list: GBP / `GBP_2026_2` and EUR / `EURO_2026_2`.
- Effective date: `16-Oct-2026`; site: `1`.
- PDM Test database: `DBCHIP11V.PDMTEST`.

The PDM SQL price functions take currency, date, and site. The SQL Server
queries do not return a pCon price-list ID; list association is resolved by the
separate pCon workflow.

For each Article increment item, the tool executes the inline query with
parameters `(currency, effective_date, site_id, site_id, currency, item)`.
The base query binds currency/date, the requested item set, and site IDs.

### Base prices

The PDM per-item `fnGetListPriceByItem` values and tool's set-based repository
query matched for all ten items in each currency:

| Item | GBP | EUR |
|---|---:|---:|
| `GESG.` | 29 | 32 |
| `GEWC.10` | 10 | 11 |
| `GEWDP.L` | 84 | 95 |
| `GEWDP.S` | 56 | 63 |
| `GEWQ.` | 166 | 188 |
| `GEPBPANNF.0608S4M` | 984 | 1112 |
| `GEMAP.12S1M` | 124 | 140 |
| `GEBH.10` | 55 | 62 |
| `DTW2B1T2.C` | 405 | 460 |
| `GETH.1022FS4W` | 1442 | 1628 |

Each item returned one base value in the tool set-based query; values were
equal to the PDM per-item `fnGetListPriceByItem` result for all 20
item/currency inputs. This confirms the tested base-price values, not the
target MDB article/global owner, list ID, or duplicate target-row ID.

### Increment rows and confirmed fetch correction

The source-equivalent PDM Article query and the tool Article query matched as
multisets for all 20 item/currency pairs. The six original inputs returned
four rows only for `GEWQ.` and zero rows for the other five items. The expanded
items returned 3 rows for `GEMAP.12S1M`, 4 for `GEBH.10`, 1 for
`DTW2B1T2.C`, and 16 for `GETH.1022FS4W`, in each currency:

For `GEWQ.`, the four matching rows in each currency were:

| OptionValueId | OptionId | Code | GBP IncPrice | EUR IncPrice | PriceBand |
|---:|---:|---|---:|---:|---|
| 300267 | 3827 | `DB3` | 16 | 19 | `NULL` |
| 300268 | 3827 | `DN2` | 16 | 19 | `NULL` |
| 300269 | 3827 | `DR1` | 16 | 19 | `NULL` |
| 300270 | 3827 | `OLF` | 16 | 19 | `NULL` |

The prior tool procedure fetch did not match this source row set:

- For `GEWQ.`, it returned 13 rows: the four priced rows above plus 9 null
  increment rows.
- For `GEPBPANNF.0608S4M`, it returned 48 rows, including 7 non-null
  increments, while the PDM Article query returned no rows for the same
  inputs. Those procedure rows are no longer used by Article Price compute.
- For `GEWDP.L` and `GEWDP.S`, the procedure returned 8 null rows per item
  while the PDM Article query returned none.

The root cause was using the generic option-data procedure for Article Price
instead of the original Article inline query. The tool now uses the source
query and preserves `OptionValueId`, `OptionId`, code, computed increment,
and `PriceBand`. Tests cover query shape, parameters, nulls, filtering, and
Article-vs-Global compute routing.

The PDM Article increment SELECT has no `ORDER BY`; comparisons therefore use
row identity/value multisets, not a claim about deterministic physical row
order. The tested rows had no duplicate option identity and all `PriceBand`
values were null.

For the expanded four-item set, the matched identities, codes, and GBP/EUR
values were:

| Item | OptionValueId | OptionId | Code | GBP | EUR | PriceBand |
|---|---:|---:|---|---:|---:|---|
| `GEMAP.12S1M` | 181901 | 3853 | `HFK` | 12 | 13 | `NULL` |
| `GEMAP.12S1M` | 289546 | 3853 | `BFK` | 12 | 13 | `NULL` |
| `GEMAP.12S1M` | 289548 | 3853 | `WFK` | 12 | 13 | `NULL` |
| `GEBH.10` | 300242 | 3845 | `DB3` | 5 | 6 | `NULL` |
| `GEBH.10` | 300243 | 3845 | `DN2` | 5 | 6 | `NULL` |
| `GEBH.10` | 300244 | 3845 | `DR1` | 5 | 6 | `NULL` |
| `GEBH.10` | 300245 | 3845 | `OLF` | 5 | 6 | `NULL` |
| `DTW2B1T2.C` | 51546 | 3785 | `CD` | 221 | 251 | `NULL` |
| `GETH.1022FS4W` | 62287 | 3831 | `OKG` | 202 | 228 | `NULL` |
| `GETH.1022FS4W` | 62288 | 3831 | `OUG` | 294 | 332 | `NULL` |
| `GETH.1022FS4W` | 62290 | 3831 | `EU` | 612 | 691 | `NULL` |
| `GETH.1022FS4W` | 62291 | 3831 | `EV` | 612 | 691 | `NULL` |
| `GETH.1022FS4W` | 194059 | 3831 | `NOK` | 202 | 228 | `NULL` |
| `GETH.1022FS4W` | 299995 | 9168 | `AA` | 47 | 53 | `NULL` |
| `GETH.1022FS4W` | 300271 | 9168 | `SC` | 45 | 51 | `NULL` |
| `GETH.1022FS4W` | 300272 | 9168 | `RR` | 45 | 51 | `NULL` |
| `GETH.1022FS4W` | 300273 | 9168 | `SS` | 45 | 51 | `NULL` |
| `GETH.1022FS4W` | 300274 | 9168 | `SL` | 66 | 75 | `NULL` |
| `GETH.1022FS4W` | 300275 | 9168 | `BA` | 45 | 51 | `NULL` |
| `GETH.1022FS4W` | 300276 | 9168 | `BC` | 66 | 75 | `NULL` |
| `GETH.1022FS4W` | 300284 | 9168 | `EB` | 45 | 51 | `NULL` |
| `GETH.1022FS4W` | 300285 | 9168 | `ED` | 66 | 75 | `NULL` |
| `GETH.1022FS4W` | 300286 | 9168 | `VS` | 1100 | 1242 | `NULL` |
| `GETH.1022FS4W` | 300287 | 9168 | `VL` | 1320 | 1490 | `NULL` |

## Global Price comparison

### Inputs

Global base prices were compared for the six `S5` items
(`GE2HBS.`, `GE2HDF.`, `GE2WE.`, `GEAH.`, `GEBA.08`,
`GETH.1022FS4W`) in GBP and EUR, at `16-Oct-2026`, site `1`.

The Global increment source comparison used the `S9` input:

- Item: `GETH.1022FS4W`.
- Currency / selected list: GBP / `GBP_2026_2` (list 22).
- Effective date: `16-Oct-2026`; site: `1`.
- Catalogue: `660`; PDM program: `layout_studio`;
  `variableincs=true`.
- The expanded matrix used GBP / `GBP_2026_2` and EUR / `EURO_2026_2`;
  SQL fetch results are currency-scoped but do not return pCon list IDs.
- The source capture used both PDM query branches: direct catalogue item and
  component whose parent is in catalogue `660`. `layout_studio` adds no
  program-specific SQL predicate in this source method.

The read-only matrix was then expanded to four representative item codes,
both GBP and EUR, and every catalogue associated with each item in PDM Test.
PDM's source query was executed separately for each catalogue, while the tool
procedure was called with the same item/site/currency/date (it has no
catalogue parameter):

| Item | Catalogues tested | Tool procedure rows per currency | Priced rows | Null-priced rows | PDM source rows per catalogue |
|---|---|---:|---:|---:|---:|
| `GEMAP.12S1M` | 394, 414, 660 | 27 | 3 | 24 | 3 |
| `GEBH.10` | 414, 521, 660, 662 | 14 | 4 | 10 | 4 |
| `DTW2B1T2.C` | 521, 662 | 6 | 1 | 5 | 1 |
| `GETH.1022FS4W` | 660, 662 | 24 | 16 | 8 | 16 |

For each item and currency, the PDM source result in every listed catalogue
matched the tool's priced row multiset on option-value identity, option ID,
order code, calculated price, and price band. Procedure row counts were the
same in GBP and EUR. A follow-up read-only join check for both currencies found
zero `ItemOptionValues` matches for all procedure null-priced option
identities (24, 10, 5, and 8 respectively). This supports the observed
explanation for the extra rows, but does not expose the procedure's internal
query or prove its scope for other items/catalogues.
The row-level option IDs, codes, currency amounts, and price bands for these
four item codes are enumerated in the expanded Article increment table above;
the Global source/procedure comparison separately confirmed those identities
and values within each listed catalogue.

### Base prices

PDM's per-item `fnGetListPriceByItem` and the tool's base query matched for all
six original Global items and both currencies. For `GETH.1022FS4W`, both
returned GBP `1442` and EUR `1628`; for `GE2HDF.`, both returned GBP `110` and
EUR `125`. The expanded base-price capture also includes `GEMAP.12S1M`
(GBP 124/EUR 140), `GEBH.10` (GBP 55/EUR 62), and `DTW2B1T2.C`
(GBP 405/EUR 460); all tool set-based values equalled the PDM per-item
function values.

### Increment query, filtering, and calculated-result comparison

The PDM Global path first selects `ItemOptionValues` increment amounts for
active option values in catalogue scope, then calculates each applicable value
with `dbo.fnGetListPrice`. It ignores rows whose selected increment is null
before building PDM codes; the follow-up calculation is retained only when its
`newprice` is non-null. The tool calls
`EXEC dbo.PDMOptionDataReportWithIncList @item=?, @siteId=?, @currency=?, @effectivedate=?`
with `(item, site_id, currency, effective_date)` and receives computed
`IncPrice`. This procedure interface has no catalogue parameter.

The live source-equivalent PDM query returned 16 rows. A read-only call to the
tool's lower-level procedure fetch returned 24 rows: the same 16 priced
identities and eight active rows with null `IncPrice`. The PDM query requires
an `ItemOptionValues` row by `INNER JOIN`; a read-only join diagnostic confirmed
that none of those eight option values has an `ItemOptionValues` row for
`GETH.1022FS4W` (`ItemId=2145150`). Their `OptionValue.Status` is `1`, the item
has a direct catalogue row, and the product-code/GBP currency joins resolve.
Thus, for these eight, the differentiating source fact is absence of an
item-specific increment row, not inactive status, catalogue membership,
currency, or price band. All eight have `PriceBand=NULL`.
The expanded four-item/two-currency matrix found the same
no-item-increment explanation for every additional null-priced procedure row.

For this item, the PDM source query uses `Item.ProductCodeIdOverride=1751`
rather than the product default code `813`; the site-1 code resolves to
`PriceCode=F80`, `BasePriceRef=1`, and the GBP price matrix. The comparison
used PDM's full override expression, not the product default.

The procedure definition is not visible to the current SQL principal, so its
internal branch that returns these null rows cannot be audited. The observable
output and source joins establish why PDM does not treat them as pricing rows.
This is an intermediate result-set difference, not a priced-record discrepancy
for this tested input. Tool-side null filtering is covered by a regression
fixture with the exact 24 identities below.

| OptionValueId | OptionId | Code | PDM raw increment | PDM `fnGetListPrice` | Tool `IncPrice` | PriceBand |
|---:|---:|---|---:|---:|---:|---|
| 299995 | 9168 | `AA` | 27.90071214 | 47 | 47 | `NULL` |
| 300275 | 9168 | `BA` | 26.60300460 | 45 | 45 | `NULL` |
| 300276 | 9168 | `BC` | 38.93122624 | 66 | 66 | `NULL` |
| 300284 | 9168 | `EB` | 26.60300460 | 45 | 45 | `NULL` |
| 300285 | 9168 | `ED` | 38.93122624 | 66 | 66 | `NULL` |
| 62290 | 3831 | `EU` | 361.20583000 | 612 | 612 | `NULL` |
| 62291 | 3831 | `EV` | 361.20583000 | 612 | 612 | `NULL` |
| 194059 | 3831 | `NOK` | 119.34284000 | 202 | 202 | `NULL` |
| 62287 | 3831 | `OKG` | 119.34284000 | 202 | 202 | `NULL` |
| 62288 | 3831 | `OUG` | 173.58958000 | 294 | 294 | `NULL` |
| 300272 | 9168 | `RR` | 26.60300460 | 45 | 45 | `NULL` |
| 300271 | 9168 | `SC` | 26.60300460 | 45 | 45 | `NULL` |
| 300274 | 9168 | `SL` | 38.93122624 | 66 | 66 | `NULL` |
| 300273 | 9168 | `SS` | 26.60300460 | 45 | 45 | `NULL` |
| 300287 | 9168 | `VL` | 778.62452474 | 1320 | 1320 | `NULL` |
| 300286 | 9168 | `VS` | 648.85377060 | 1100 | 1100 | `NULL` |

For all 16 rows, the comparison matched `(OptionValueId, OptionId, code,
final price, PriceBand)` exactly. All were active (`Status=1`) and the tool
procedure returned the same `PriceBand=NULL`. PDM's query orders by
`OrderCodeValue`; the procedure's observed row order was different and did not
provide that ordering. The Global wrapper now sorts the 16 retained rows, and
the live comparison matched PDM's ordered sequence. For `variableincs=true`,
the PDM code construction yields the same tested variant identities as the
tool, e.g. `GETH.1022FS4W 9168=AA` and `GETH.1022FS4W 3831=EU`.

**Classification:** raw procedure-to-source result sets differ (24 vs 16 for
`GETH.1022FS4W`), fully accounted for in the tested matrix by active
null-priced options with no item-specific increment rows. After PDM's source
filtering/calculation and the tool's global filtering/calculation, the tested
priced identities, values, PriceBand, and order match exactly. This does not
prove the procedure's internal query or universal query-scope parity.

The null procedure rows were: `(299994, 9168, NN)`, `(62286, 3831, Z5G)`,
`(300309, 3832, Z5G)`, `(300310, 3832, OKG)`, `(300311, 3832, OUG)`,
`(300313, 3832, EU)`, `(300314, 3832, EV)`, and `(300315, 3832, PLV)`.
Each had `Status=1`, `IncPrice=NULL`, and `PriceBand=NULL`; no corresponding
`ItemOptionValues` row exists for the selected item.

### Related records and placeholder workflow

The PDM Test relationship query found `GETH.1022FS4W` as a component of
`GEPMSM.1022S4W` (parent ItemId `2233201`) and `GEPMST.1022S4W` (parent
ItemId `2233365`), each with quantity `1`, component sequence `1`, and feature
position `9355|8992|8993|`. These are live source relationships; they were not
compared with a matching loaded tool snapshot or raw target-MDB relationships.

Historical isolated-copy differential evidence records MATCH for complete
PDM placeholder-then-update scenarios `S6`, `S7`, and `S9`. The tool's focused
fake-MDB regression checks missing Global row value, X level, currency/list,
and text link. Neither historical evidence nor the unit test is a live raw
fetch comparison. The old `S5_global_update` value-only run reported
`GE2HDF.` as not found while the tool's one-step exporter produced a row at
`114.0`. That is a processing/workflow-step difference: PDM's value-update
step does not create placeholders. The complete placeholder-then-update
workflow matched in historical isolated-copy scenarios `S6`, `S7`, and `S9`;
no live UI/MDB result was captured here.

## Duplicate handling confirmed from PDM source

`UpdatePConItemPrice` assigns the matching `com_PriceID`/`com_GlobalPriceID`
on each reader iteration and updates only the final ID retained for Article
base, Article surcharge, and Global base lookups. The Global surcharge path
loads each existing global row and processes each row. The tool exporter now
uses those four behaviors, with focused tests for duplicate Article base,
Article surcharge, Global base, and Global surcharge rows.

The historical Article case showed the PDM duplicate value `9.0` remaining
while the former tool implementation changed it to `171.0`. The source-backed
root cause was that the tool updated every duplicate while PDM updates only
the last matching ID; the tool now follows the last-row rule. This resolves
the implementation difference for the tool's returned order, but does not
prove that PDM and the tool select the same physical MDB duplicate because
neither target SELECT specifies an `ORDER BY`.

Neither PDM's target SELECT nor the tool's target query specifies an explicit
ordering for these duplicate matches. The tool test verifies the rule against
the last row returned by its fake reader; it does not establish that PDM and
the tool would choose the same physical duplicate ID in a particular MDB.
Historical duplicate differential evidence compares normalized outcomes, not
the physical IDs or reader order.

## Remaining verification gaps

1. **Actual PDM UI execution and target records:** no disposable pCon MDB and
   no capture-only PDM reader instrumentation that denies writes were
   available. The PDM UI was not run; no MDB was opened or written. A
   read-only source-equivalent query cannot prove which MDB-dependent branch
   the UI would execute or compare raw `com_PriceID`, `com_GlobalPriceID`,
   `com_PackageID`, `com_PriceListID`, `com_ArticleID`, or `com_TextID`.
2. **Global fetch scope:** the tested Global source rows match after PDM
   filtering for the four item codes and all their associated catalogues.
   PDM scopes by catalogue and component relationships; the tool procedure
   accepts item/site/currency/date only. No procedure definition is visible,
   so equivalence beyond this matrix is unproven.
3. **Program-specific behavior:** Article `lf`/`av` predicates are implemented
   when `program_code` is supplied; both compute routes now propagate the
   snapshot's `generation_program`. The live Article sample was not captured
   under `lf` or `av`, so those filtered data sets are not live-verified. For
   Global, PDM derives `variableincs` from the program: it is false for
   `aeron`, `verus`, `lino`, `embody`, `cosm`, `mirra2`, `sayl`, `setu`,
   `celle`, `keyn`, `caper`, `mirra`, `em`, `lf`, `av`, `ce`, and `cp`, and
   true by default. PDM's Global code projection/matching also has
   `swoop`, `ratio`, `memo`, `WE51`, `RY3V`/`RYM`/`RYT`, and
   multiple-option-ID special cases. The tool's Global record builder uses the
   common `item OptionId=code` representation; only the `layout_studio`
   comparison was checked against PDM's resulting identity. Other
   program-specific Global mappings remain unverified and are not asserted
   as matching.
4. **Price-list and text identity:** the source price queries filter by
   currency but do not return a pCon price-list ID. Historical outcome
   comparisons use normalized list labels and semantic text, not raw list or
   text IDs. Those associations were not compared against a live disposable
   MDB.
5. **Order/duplicates/null edge cases:** Article SQL has no `ORDER BY`;
   duplicate target-row physical IDs cannot be compared without a disposable
   MDB and deterministic source ordering. The tested Global PDM query orders
   by `OrderCodeValue`; the tool now sorts its retained priced rows to that
   order. Other null/rounding/date boundary cases remain unverified.
6. **Source identity and relationships:** the pricing queries project item
   codes and option-value identities, not all `ItemId`, `ProductId`,
   `ProductCodeId`, or target article/global primary keys. The explicit
   ProductCode override diagnostic was performed for `GETH.1022FS4W` only;
   the live `ItemComponents` relationships for that item were not reconciled
   to a loaded tool snapshot. Those IDs/relationships and the original UI's
   selected records remain unverified.

The stored procedure metadata check on `DBCHIP11V.PDMTEST` found
`IsEncrypted=0`, `VIEW DEFINITION=0`, and `EXECUTE=1`; its `sys.sql_modules`
definition is therefore unavailable to this account. The smallest action to
audit its internals is for a DBA to grant this account `VIEW DEFINITION` on
`dbo.PDMOptionDataReportWithIncList` or provide its definition through an
approved read-only channel. Broader UI/target-record parity additionally
requires a disposable pCon MDB and a capture-only PDM execution path that
rejects all MDB writes. The current evidence does not need MDB writes or the
existing differential harness.

## Automated validation and reproduction

Focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_pdm_price_fetch_parity.py tests\test_price_mdb_export_service.py tests\test_pricing_pdm_text_parity.py -q
```

**Result: 82 passed.**

Broader non-GUI pricing suite:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_price_list_service.py tests\test_price_list_targets.py tests\test_price_mdb_export_service.py tests\test_price_product_code.py tests\test_pricing_pdm_text_parity.py tests\test_pdm_price_fetch_parity.py tests\test_pdm_differential_report.py -q
```

**Result: 127 passed.** The 21 focused GUI pricing tests passed under Python
3.12 with `QT_QPA_PLATFORM=offscreen`; the configured project venv is 32-bit
Python 3.14 and does not contain PySide6. Pylance Problems reported no errors
in the changed Python source and test files, and `git diff --check` passed.
No Metatype tests were run. The MDB-writing differential harness was not run.

GUI test command:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
C:\Users\siaoca\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests\test_pricing_page_text_blocks.py tests\test_pricing_export_workflow.py -q
```

The live SQL captures used Windows integrated authentication to
`DBCHIP11V.PDMTEST`; the source-equivalent query, left-join diagnostics, and
tool procedure/repository calls were read-only and executed in
non-autocommit transactions that were rolled back. The procedure body is not
visible to the current account. No PDM UI export or MDB write was performed.
