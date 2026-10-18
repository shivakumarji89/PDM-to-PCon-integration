# PDM UI vs tool pricing fetch parity

**Evidence date:** 2026-10-18
**Scope:** Article Price and Global Price only.
**Data source:** the non-production `DBCHIP11V.PDMTEST` database, using the
local PDM build `1.0.9686.24988` and its matching `PDMMaintenance` source.
No production database, MDB, or export workflow was used.

## Result

| Scenario | Status | What the evidence establishes |
|---|---|---|
| Article Price | **MATCH** (tested source rows; bounded) | Ten item codes in GBP/EUR were compared at the same date/site. Tool base values and Article inline-query row identities/values matched the source-equivalent PDM results. Program-filter execution, actual UI-selected rows, and physical duplicate target IDs remain unverified. |
| Global Price | **MISMATCH** (raw intermediate result sets); **MATCH** (priced rows after PDM-equivalent filtering for tested inputs) | For four item codes, GBP/EUR, and each associated catalogue, source-scoped PDM priced rows match the tool procedure's priced rows after filtering. The procedure returns additional null-priced rows (24 vs 16 for `GETH.1022FS4W`); those rows have no item-specific increment row. The procedure definition and broader program behavior remain unavailable/unverified. |

These are bounded results, not a claim of universal or full UI parity. The
actual PDM UI was not run against a pCon MDB. The live evidence below comes
from source-equivalent PDM SQL and read-only tool repository/procedure calls
against non-production PDM Test; target-MDB selection and record IDs remain
unverified.

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
- Global fetch still calls `PDMOptionDataReportWithIncList`; its pricing
  wrapper now keeps only active rows with non-null increment values. The
  shared lower-level procedure method remains unchanged for its other callers.
  The Global wrapper sorts the surviving rows by `OrderCodeValue2`, matching
  PDM's `ORDER BY OrderCodeValue`.
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
