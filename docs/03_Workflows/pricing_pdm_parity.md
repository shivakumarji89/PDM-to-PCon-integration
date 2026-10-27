# Pricing export vs the PDM "Update pCon" price update

Source of truth: the PDM desktop application source (`PDMMaintenance`, VB-converted C#).
Traced path (all line numbers refer to that source):

| Step | PDM location |
|---|---|
| Button | `PriceMaintenance._button_update_pcon_MouseDown` (9631) opens `PConPriceUpdate` |
| Handlers | `PConPriceUpdate.button_article_Click` (2021), `button_global_Click` (2084) |
| Worker thread | `UpdatePriceThread.execThread` (110): per item reads `Item.Notes` for the article prefix length, then calls the two methods below |
| Base / article / global value | `PriceMaintenance.UpdatePConItemPrice` (8714) |
| Global surcharge values | `PriceMaintenance.UpdatePConItemIncrementalPrice` (9128) |
| New article row | `PriceMaintenance.addNewArticlePriceRecord` (8658) |
| New global row | `PriceMaintenance.AddMissingGlobalPricingRecords` (9921), "Create global" button |

Database access: Jet OLEDB straight into `<pConPath>\WS\<workspace>\pcr_data_com_ocd.mdb`; prices come from
SQL Server `dbo.fnGetListPriceByItem` / `dbo.fnGetListPrice`. There is no transaction, no read-back, and PDM
never consults `tCOMd_DistributionRegionPriceList` - the list is whatever the user selected (all
`tCOMd_PriceList2` labels except `default`, shown by label).

## Semantics, and what the Pricing export does

| Topic | PDM | Pricing export |
|---|---|---|
| Price list | `com_PriceListLabel LIKE pricelist.Replace("_","%")` - so `EURO_2026_2` also matches `EURO 2026_2` | Currency + case/space/underscore-insensitive label; among matches **prefers a list linked to a distribution region** (pCon reads only those), then exact label, then lowest id. *Intentional difference*: PDM would write to every matching list, including unlinked orphans. |
| Article base row | `tCOMd_Price`, level `B`, article/variant match | same identity: article + list + variant + level |
| Global row | `tCOMd_GlobalPrice` by package + variant condition; **no level filter** | package + list + variant; level ignored for matching |
| Row currency | not compared | not compared (no real row disagrees with its list) |
| Zero price | never written (`num7 != 0.0`) -> "unresolved" | skipped, counted as `skipped_zero_price` |
| Unchanged value | counted `samevaluecount`, no write | skipped, counted `skipped_existing` |
| Update | `UPDATE ... SET com_PriceValue WHERE <PK>` | same, value only |
| Duplicates | PDM retains the last matching ID for Article base, Article surcharge, and Global base; Global surcharge processes each matched row | Article base/surcharge and Global base update only the last matching target row; Global surcharge updates every differing matched row |
| Missing article row | inserted at level `B`, validity copied from the article's existing price rows | same |
| Missing global row | created separately: level **`X`**, `com_TextID` linked to the `price` text, list's validity dates, value filled by the update | inserted at level `X` with the value, `com_TextID` resolved by PDM's name rule (surcharge `ITEM 8=1FD` -> text `8`): an existing text is **reused**, a missing one is **created** exactly as PDM does (see *Text blocks* below), list's validity dates. |
| Transaction | none | one transaction; a failed batch changes nothing |
| Counts | `ExecuteNonQuery` rows affected | rows affected reported by the bridge (`mdb_bridge.ps1` now returns the real update count) |
| Post-write check | none | read-back of every written row; mismatch -> `ok: False` |
| Preview | none | `export(..., dry_run=True)` returns the exact plan and writes nothing |

## Revive component fabric-family routing (25-Oct-2026)

Pricing now separates a fabric family's **price source** from its related
colour-option **export target**. This is the requested compatibility policy
for existing Revive component family records; it is not individual-colour
price inheritance or a claim that the unavailable legacy desktop worker has
been executed for this case.

`PDMRepository._resolve_global_fabric_targets` runs after the unchanged Global
calculation/cache path, for `revive` or when generation-program settings have
not been configured. A freshly loaded PDM snapshot need not have a
`generation_program`; that optional generation setting must not bypass the
actual fabric relationship. Explicit other programs remain unchanged.
It joins the priced `OptionValue`
to its `[Option].IsFabric=1` definition and follows
`DependentOptionValues.OptionValueId -> AdditionalOptionValueId` to active,
catalogue-applicable values of a component-mapped option with `IsFabric=2`.
Both options must be present as complete tokens in the catalogue-scoped
parent/component `ItemComponents.FeaturePositionString`. The target option ID
is read from metadata, not hardcoded to 28. Multiple mapped colour options,
missing applicable dependent values, or separately priced related colours
fail computation explicitly. Components without a mapped colour option and
all explicitly selected other programs retain their original pricing.

The Pricing table displays the resolved `PriceRecord.variant_condition`;
`pdm_lookup_code` retains the original price source through snapshot save/load.
New computations stamp a pricing-only `pricing_revision`. Older unresolved
global fabric records are shown as outdated and require **Compute Prices**
before preview/export; they are never silently rewritten. Previously resolved
source/target-aware records remain usable. Imported MDB views and unrelated
programs are not invalidated. Failed recomputation restores the historical
table rather than leaving partially streamed results exportable.

The source `OptionId`, `OptionValueId`, code, price, calculation/cache sequence,
and result order are unchanged. `PricingService.build_records` emits
`COMPONENT <colour-option>=<family>` while retaining the priced family's
`COMPONENT <type-option>=<raw-code>` identity in the existing
`pdm_lookup_code` field. The pricing-only revision is also serialized; no
shared snapshot loading or migration behavior changes.
These are family surcharges, not invented prices for individual colour
values whose direct `IncPrice` is NULL. Recompute existing pricing snapshots
to obtain the relationship-resolved target; old records are not rewritten
or guessed during snapshot loading.

Export uses that explicit source/target distinction to recognize the legacy
`<colour-option>=COMPONENT_<family>` row, scoped to package/list and matched
case-insensitively as Jet does. That key is lookup-only; new MDB rows use the
canonical computed `COMPONENT <colour-option>=<family>` condition. A single
legacy target row is normalized to the canonical condition while its price,
MDB-generated ID, text link and other fields are preserved. A missing target is
an **insert**, not an error, provided its component base price exists or is
planned in the same list. Duplicate stored or computed family targets,
simultaneous legacy/canonical rows, unlinked/dangling existing targets, already
priced source-family rows, and ambiguous new-row text mappings still block the
entire export. No fallback updates of both type and colour records are
permitted. Preview retains source, computed and stored identities and
distinguishes insert/update and text create/reuse.

For `RY3SNNB.105512F`, **28 is the related Fabric colour option ID**, not a
`com_TextID`. The exact `com_VariantCondition` written to the MDB is
`RY3SNNB.105512F 28=1FD`. Its option ID independently determines the legacy
price-text name `"28"` and label `"Surcharge 28"`. New family rows reuse the
unique package-scoped `price` text named `"28"`, or create it in the supported
language columns. Subsequent families and EUR/GBP rows share that text. An
existing row keeps its linked text even when its name differs from `"28"`;
translated labels are not rewritten. MDB generates the numeric IDs during the
final transaction; preview never assigns a numeric ID to a proposed text.

The relationship for pricing is **GlobalPrice.com_TextID -> Text.com_TextID**.
It does not require additional article/class/property connection records.
Article long/short texts remain linked through `Article.com_LongTextID` /
`com_ShortTextID`; property/value texts remain linked through
`Property.com_TextID` / `PropValue.com_TextID`, with article/class and relation
connections left untouched. These are separate full-OCD export surfaces, not
price-text creation requirements. The disposable ACE workflow test seeds and
asserts preservation of these texts and connections.

Read-only PDMLive, UK/site 1, EUR/25-Oct-2026, catalogue 658:
`RY3SNNB.105512F` resolves source option 8 to related colour option 28.
`1FD/1HA/4MT/ZM2` remain **89/44/133/89 EUR**. Actual Revive package 240,
list 26 (`EURO_2026_2`), SELECT-only preview: **14 updates** (base plus 13
families), **0 inserts**, **14 existing text links preserved**. No MDB write
was performed. PDM's own option report confirms the dependent colour IDs
but returns NULL direct colour prices; the new routing does not change that
fact or assert legacy runtime/rendered-total parity.

## Evidence from the real MDB (backup copy)

* Lists 23/24 (`GBP 2026_2` / `EURO 2026_2`) held the 1,520 earlier rows and have no region link;
  region 6 (EURO) -> list 21 and region 7 (GBP) -> list 22 (`EURO_2026_2` / `GBP_2026_2`), whose level-`X`
  rows for the same variants were 0 in 54 of 57 overlapping cases.
* All 132,964 vendor global rows are level `X`; no duplicate (package, list, variant) exists.
* Every vendor global row has a `com_TextID`; all 760 variants of the earlier export resolve through the
  PDM text-name rule to an existing `price` text.

## Current Global source implementation and measured limits

Work continued on `main` after safely fast-forwarding to `199540b` (the remote
Syteline changes were preserved). Global pricing no longer uses the filtered
`PDMOptionDataReportWithIncList` wrapper. A dedicated source query in
[`pdm_repository.py`](../../repositories/pdm_repository.py) reproduces PDM's
selected catalogue/direct-and-parent-component scope, substring item scope,
active status, site/override product code, currency/matrix joins,
`FabricBands.Application=1`, and projected SQL ordering. The generic option
report procedure is unchanged for other consumers.

Both compute paths in
[`pricing_service.py`](../../services/pricing_service.py) propagate catalogue
and program; missing catalogue fails explicitly. `BasePriceRef` selects the
correct initial increment field, but the secondary predicate deliberately
remains `IncrementalPrice = selected_raw`, including references 2/3.
The source's first-index cache, last non-null secondary value, and -1 sentinel
are preserved. This is not a generic quantity-tier implementation: a fresh
schema read found three alternative base/increment fields and one component
`Quantity`. Meeting Table `GETH.1022FS4W` populates only field 1; Florence
`1205S1BQ` populates all three; live site-9 Embody/CD cases exercise references
2/3. Bands are selected independently from Application 1.

Source/raw lookup identity and insertion condition are separate,
backward-compatible snapshot fields (`source_item`, `pdm_lookup_code`,
`variant_condition`). Substring-expanded items stay Global. Global option
rows, including components, use `ITEM OptionId=Code` for insertion; `memo`
uses `ITEMCode`. These are built from the item's actual option ID and raw
option value, stripping `#`, not by rearranging the worker key.

**Correction to f724311:** an existing reversed staging row does not establish
the placeholder-generation rule. In `PriceMaintenance.cs:10062`, PDM builds
`Item + suffix`; the component rewrite at 10064 runs only when that candidate
has no `=`. The actual option-procedure suffix already contains `=`, so it
bypasses the rewrite. Hardcoded raw selectors (`MYST`, `~W`, `~M`, etc.) have a
different branch; this change does not implement or claim parity for those
selector modes or arbitrary `FeaturePositionString` remapping.

For fabric-family records, the export recognizes the legacy MDB key only when
the source/target option and family code in the record metadata establish that
mapping. If both legacy and canonical targets exist, export blocks rather than
guessing or merging. A uniquely matched legacy row is corrected to the
canonical condition; an already canonical row is reused without changing its
condition. If neither exists, insertion uses `variant_condition`. Other global
surcharge records retain the general worker-key lookup and value-only update
behavior. Records without lookup metadata retain exact-condition matching.
Recompute old snapshots to obtain the relationship-resolved condition; no
general string-replacement migration is performed.
Article pricing, source SQL, currency/list routing and product-code attachment
are unchanged. Both compute paths now pass the resolved snapshot program to
the builder as well as the source fetch, preserving the `memo` exception.

**Evidence B, independent original-source SQL versus actual repository calls
on PDMTEST**, GBP/EUR, 15/16-Oct-2026:

| Measured stage | Before | After |
|---|---|---|
| Global calculated increments, 108 scenarios | 596 exact / 1,340 comparison slots = **44.48%**; 68/108 multiset passes, 60 ordered | **1,052/1,052 exact**, 108/108 multiset and order passes |
| Global source-lookup metadata, same scenarios | 316/1,340 = **23.58%**; 60/108 multiset passes, 52 ordered | **1,052/1,052 exact**, 108/108 multiset and order passes |
| Article fetch, 96 scenarios, unchanged implementation | **936/936 exact** | **936/936 exact** |

The denominator includes same-identity field differences, missing and extra
records; duplicates are not collapsed. Global totals exclude base observations.
Sixteen corrected Global scenarios are empty controls; all 92 nonempty
scenarios match. These results do **not** measure exported or physical rows.

A supplemental nonempty Ratio-accessories sample, `RZTA.`/405/site 1 at
16-Oct-2026 in both currencies, matches all four measured stages, **6/6**
records. No nonempty `swoop`/`memo` fixture was found; those branches and
Ratio's category-wide Worksurfaces/Screens modes remain live-unverified.

**Known boundary, not completed parity:** the earlier 14-scenario sample
(RYM, RYT, `lf` MRFN, `av` AS2, site-9 Embody) matched **318/318** source
records, source projections and source-lookup metadata. Before the target
condition change, the worker-parser comparison matched **20/318 (6.29%)**.
That sample predates the current AddMissing-shaped conditions and is not a
measurement of the current builder. The source itself has conflicting paths:
`UpdatePConItemIncrementalPrice` compares plain source codes for `lf`/`av`/
`embody` and special `OptionId=ITEM_CODE` keys for RYM/RYT, while
`AddMissingGlobalPricingRecords` creates item-qualified conditions for
option-procedure suffixes, even for components. Parent-option rewriting applies
only to its separate raw-suffix branch. The builder keeps the worker key in
`pdm_lookup_code`; staging proves an existing worker-shaped row, not a universal
insertion rule or arbitrary parent-option mapping.
Physical UI output and current production-MDB behavior remain **NOT VERIFIED**.

### Special selectors and component-condition evidence

The original `PriceMaintenance.cs` is not present in this checkout or in the
local staging tree; the investigation below uses the source-derived notes in
this repository and the checked-in tests. The production MDB was not opened.
Where those notes do not preserve the source expression or a fixture, no
selector-to-condition mapping is inferred.

| Case | Source rule supported by available evidence | Inputs | Expected stored condition / coverage |
|---|---|---|---|
| Ordinary option-procedure suffix | `AddMissingGlobalPricingRecords` forms `Item + suffix`. For the option-procedure suffix, the component rewrite is guarded by the candidate having no `=`; an `OptionId=Code` suffix therefore bypasses it. | Item (for a component, the component Item), procedure suffix containing the option id and value code | `ITEM OptionId=Code`; covered by `test_global_condition_matches_pdm_option_suffix_shape` for direct and component rows and by the component lookup/target test. |
| `memo` option suffix | The checked-in source notes record the special no-separator form. The source-derived builder uses the raw option code rather than the normal `OptionId=Code` representation. | Item and option code | `ITEMCode` (e.g. the synthetic `MEMO123`/`AA` case stores `MEMO123AA`). Unit-test coverage exists, but no nonempty source/live memo fixture was found. |
| Hardcoded raw selectors (`MYST`, `~W`, `~M`, and related branches) | The notes establish that these take a separate branch in `AddMissingGlobalPricingRecords`; they do not retain the branch predicates, transformations, or selector-specific output. | The raw selector, selected item, and whatever component metadata that branch reads are not fully recoverable from the checked-in evidence. | **Not established.** No expected stored condition is asserted and no generic option mapping is applied to these selectors. Recover the original source or capture a non-production PDM output before implementing. |
| Parent-option to component-option mapping | `FeaturePositionString` is a pipe-delimited positional mapping on `ItemComponents`, as documented in the Super Product source notes. The notes establish its role but not the precise lookup/rewrite performed by the pricing branch. | Parent and component item IDs, `ItemComponents.FeaturePositionString`, and the option/selector data consumed by the pricing branch; exact field use is not preserved. | **Not established.** Do not derive component conditions from position or option names. Existing component tests exercise the option-procedure suffix rule only, not arbitrary parent-option mapping. |
| Ratio Worksurfaces / Screens selectors | These are separate category-wide modes, not the measured Ratio accessories/default-category path. The exact selector inputs and branch conditions are absent from the checked-in source notes. | Category selector (ID/name) and the mode-specific item/option rows; exact values not preserved. | **Not established.** No usable nonempty Worksurfaces/Screens fixture was found. The `RZTA.` accessory fixture only supports its observed option-suffix condition (`RZTA. 6867=DB3`, likewise `DN2`/`DR1`). |
| `swoop` | The checked-in fetch implementation transcribes a product filter for `OAW1%` or `OAW2%`; the source notes do not establish a special stored-condition rewrite for the selected-item worker path. | Selected item/program and product code; projected option-code row | **Stored condition not established.** Regression coverage checks both query predicates only. No usable nonempty `swoop` fixture was found. |

The option-condition regressions intentionally stop at the rules supported by
the source notes or observed rows: ordinary suffixes, component suffixes, the
synthetic `memo` shape, and the observed Ratio accessories. They are not
evidence for `MYST`/`~W`/`~M`, arbitrary `FeaturePositionString` mappings,
Ratio Worksurfaces/Screens, or a nonempty `swoop`/`memo` source result. Those
cases remain live-QA/source-recovery gaps.

The procedure definition still returns null and `VIEW DEFINITION` permission
is 0. An approved DBA definition/grant is required to inspect its internals,
but it is no longer a dependency of Global source fetching.

Historical validation before this condition correction: **36 focused**,
**166 broader non-GUI**, and **21 offscreen GUI** pricing tests passed.
Article duplicate-loop tests retain
the last supplied target row, but physical duplicate-ID parity cannot be
claimed without deterministic MDB ordering. No Development/Metatype changes,
MDB-writing differential run, live MDB write, or production export occurred.

Exact inputs, missing/extra counts, source/cache details, regression commands,
and the deliberately failing worker-target matching diagnostic are in
[`pdm_ui_tool_fetch_parity.md`](./pdm_ui_tool_fetch_parity.md). The read-only
comparison command is:

```powershell
& .\.venv\Scripts\python.exe -B -m scripts.pdm_differential.fetch_parity --article
```

The current script includes worker-target matching diagnostics and exits 1
when parsed prepared conditions disagree with the update worker's key. The
diagnostic is not a check of the missing-record generator or physical MDB rows.

### Global lookup/insertion correction: exact verification

Starting branch `main`, HEAD and fetched `origin/main`:
`f72431186a09262ebc9d462695df06c2020dda41`. No branches or production MDB
writes were used.

Read-only PDMTEST, item `RYMPSH.12SW`, site 1, catalogue 658, EUR,
`16-Oct-2026`:

| Stage | Observed output |
|---|---|
| Exact `dbo.PDMOptionDataReportWithIncBase`, item/site/excludeFabricColours = `RYMPSH.12SW`/1/1 | Option 3848, value `OKG`, option-value ID 62547, `IncPriceBase=21.00000000` |
| PDM `getOptionIncrementSuffixes` rule | ` 3848=OKG` |
| PDM missing-row candidate | `RYMPSH.12SW 3848=OKG`; component rewrite bypassed because `=` is present |
| Actual repository fetch | Five rows; OKG raw increment 21, projected `RYMPSH.12SW_OKG`, calculated price **64** |
| Builder before / after | Before: lookup and target both `3848=RYMPSH.12SW_OKG`. After: lookup unchanged; target `RYMPSH.12SW 3848=OKG`; price unchanged at 64 |
| Actual staging SELECT-only preview | Package 240 (`revive`), list 12 (`EURO_2022`, EUR), row **122850**, value 34 -> planned 64; **1 update, 0 inserts**; stored reversed condition and text **49959** preserved |

Additional read-only suffix-procedure controls (same site 1 and exclusion
flag, with PDM's item preprocessing) returned ` 9227=AJ` for `lf`
`MRFN121HWAP` (six rows), ` 8=1FD` for `av` `AS2EA32AA` (one),
` 6027=OKG` for `RYTRFA.0812SW` (one), and ` 9168=AA` for ordinary
`GETH.1022FS4W` (one). Embody `CN132AWAA` had **no** priced suffix row for
option 8/value AJ at site 1. Its site-9 worker fetch remains covered by the
seven-scenario parity check and its format/matching by mocked tests; live
placeholder eligibility for that particular Embody option is **unverified**.

Staging file:
`C:\HermanMillerOFMLSVN\Staging\HermanMiller\WS\Tables\Tables\Revive\pcr_data_com_ocd.mdb`.
The preview used 2022 validity solely to select that historic list; it was not
a 2026 export. Its adapter rejected non-SELECT operations and transactions.
The MDB SHA256 before/after was identical. No screenshot-format OKG row exists
in the inspected list. No target writes or application-level pCon run occurred.

The seven-scenario GBP/16-Oct-2026 read-only command above was rerun before
and after this fix. Source fetch, projection and lookup metadata remain
**159/159 exact**, seven multiset/order passes each, with zero missing/extra
rows. The worker-parser-versus-insertion-condition diagnostic changes from
**10/159** at f724311 to **0/159** after the correction (149 -> 159 field
differences), and exits 1. That is the expected distinction between the PDM
paths, **not** evidence that the canonical insertion condition is wrong.

Validation commands:

```powershell
& .\.venv\Scripts\python.exe -m pytest tests\test_global_price_source_parity.py tests\test_price_mdb_export_service.py -q
& .\.venv\Scripts\python.exe -m pytest tests\test_global_price_source_parity.py tests\test_pdm_price_fetch_parity.py tests\test_price_mdb_export_service.py tests\test_pricing_pdm_text_parity.py tests\test_price_list_targets.py tests\test_price_list_service.py tests\test_price_product_code.py -q
$env:QT_QPA_PLATFORM = 'offscreen'
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pytest tests\test_pricing_export_workflow.py tests\test_pricing_page_text_blocks.py -q
git diff --check
```

- Focused: **123 passed, 6 subtests passed**.
- Broader non-GUI: **176 passed, 6 subtests passed** (Python 3.14.6).
- GUI: **21 passed** with installed Python 3.12/PySide6 6.11.1. The configured
  32-bit venv cannot collect these two GUI modules because PySide6 is absent;
  no dependencies were installed.
- Combined nine-file pricing selection on Python 3.12: **197 passed,
  6 subtests passed**.
- Regressions cover direct/component RYM and RYT; `lf`, `av`, Embody, ordinary,
  WE51, Ratio and memo controls; existing-row value-only updates; hash variants;
  canonical insertion/text linking; repeat-run reuse; worker precedence and
  package/list scoping; serialization; normal/streaming EUR and GBP results.
- Editor Problems reports no changed-file errors. Direct Pylance analysis
  reports existing `reportArgumentType` diagnostics at the unchanged
  `int(row.get("com_PriceListID"))` statement (line 194), plus existing test
  fake/optional-access diagnostics outside the edited logic; no new errors.

Remaining evidence gaps: the screenshot MDB/package identity is unknown;
PDM/pCon runtime interpretation and physical write/read-back parity were not
executed. The procedure can be executed but its body remains inaccessible
(`VIEW DEFINITION=0`). Embody's AJ placeholder eligibility and nonempty memo
runtime evidence remain unavailable. No claim of end-to-end or universal
special-selector parity is made.

## Historical filtered-procedure comparison (PDM Test, 2026-10-18)

The following narrower captures predate the source-query implementation above
and are retained as historical evidence, not current full-workflow verification.

For `GETH.1022FS4W`, GBP, `16-Oct-2026`, site 1, catalogue 660,
`layout_studio` (`variableincs=true`), the original PDM source query returned
16 active increment rows. A read-only tool call to
`PDMOptionDataReportWithIncList` returned those same 16 priced option
identities plus eight active rows with `IncPrice=NULL`. Each of the eight has
no matching `ItemOptionValues` row for the selected item; PDM's source query
requires that row via an inner join. Their status is active, but they are not
price-bearing options for this item.

For all 16 price-bearing rows, the key `(OptionValueId, OptionId,
OrderCodeValue)` matched, and PDM's `fnGetListPrice` values matched the tool
procedure's computed `IncPrice`. `PriceBand` was null on both sides. The PDM
query orders by `OrderCodeValue`; the then-current Global fetch filtered inactive
or null-priced rows and sorts by `OrderCodeValue2` to reproduce that order.
Regression coverage checks all 24 procedure rows, the eight null exclusions,
and the resulting 16 ordered Global price records.

This explains the observed intermediate row-count difference for this input;
it does not prove the stored procedure's internal implementation or parity
for every catalogue/program. The current SQL principal has `EXECUTE` but not
`VIEW DEFINITION` on the procedure. Its definition must be provided through an
approved read-only route before making claims about other scopes.

The subsequent read-only matrix covered `GEMAP.12S1M`, `GEBH.10`,
`DTW2B1T2.C`, and `GETH.1022FS4W` in GBP and EUR at the same date/site, with
PDM's source query run for every catalogue associated with each item
(394/414/660; 414/521/660/662; 521/662; and 660/662 respectively). The
source query's priced row counts were 3, 4, 1, and 16 per catalogue. The tool
procedure returned 27/14/6/24 rows per item and currency, of which the same
3/4/1/16 priced option identities and values matched the source query; the
remaining 24/10/5/8 rows were null-priced. A read-only check in both currencies
found no item-specific `ItemOptionValues` row for any such null option.
Therefore the 16-vs-24 observation is an intermediate-row difference, not a
priced-row discrepancy for the tested matrix. It remains a raw result-set
mismatch and does not establish untested procedure scope.

Article base function values and Article inline-query rows were also compared
for ten representative items in GBP/EUR at the same date/site; the values and
row multisets matched the source-equivalent PDM queries. The Article report
contains the item-level identities and values. The UI did not run and no
target MDB was opened or modified for this fetch comparison.

PDM's `programCodeHasVariableIncs` returns false for `aeron`, `verus`,
`lino`, `embody`, `cosm`, `mirra2`, `sayl`, `setu`, `celle`, `keyn`, `caper`,
`mirra`, `em`, `lf`, `av`, `ce`, and `cp`, and true by default. The live
Global identity comparison used `layout_studio` only. The exporter/source
code tracing does not prove the tool's normalized Global record mapping for
the other program-specific branches (`swoop`, `ratio`, `memo`, `WE51`,
`RY3V`/`RYM`/`RYT`, or multiple-option-ID handling).

The regression runs covering these fetch and export contracts passed: 82
focused Article/Global/export tests, 127 broader non-GUI pricing tests, and 21
focused GUI pricing tests under offscreen Qt. The exact commands and remaining
runtime limitations are recorded in
[`pdm_ui_tool_fetch_parity.md`](./pdm_ui_tool_fetch_parity.md). No live PDM UI
execution, MDB write, export, or MDB-writing differential harness was used for
these fetch comparisons.

## Decisions on the two intentional differences

**Duplicate rows.** Inspection of `PriceMaintenance.UpdatePConItemPrice` and
`UpdatePConItemIncrementalPrice` confirms that PDM retains the last matching ID
for Article base, Article surcharge, and Global base rows; its Global surcharge
path processes every matching row. The exporter follows those separate rules,
with focused regression tests for each. The target SELECTs do not specify
`ORDER BY`, and the historical differential normalizes away primary keys and
row order. Thus the selection rule is source-confirmed, but the physical
duplicate ID selected by each runtime remains unverified.

**Price-list selection - honour the named list, prefer linked, warn if unlinked.** PDM writes to the list the
user selected. The Pricing page has no list picker: the target is the list named by the snapshot's price lists
(Price List Manager) and the record date. The exporter therefore (1) honours that named list even if it is not
region-linked (as PDM would), (2) chooses a region-linked list only among lists that are the *same list under a
spelling variant* (`EURO 2026_2` vs `EURO_2026_2`), and (3) lists every target list with its link status in
`target_lists` and warns when a written list is not region-linked, since pCon will not read it.

## Text blocks (`tCOMd_Text`, type `price`)

**What a text block is.** A real record, not an id: `tCOMd_Text` (PK `com_TextID`) holds `com_PackageID`,
`com_TextTypeCode`, `com_TextName` and one column per language (`com_Text_1_en/de/fr/nl`; PDM detects the
`com_Text_1_` prefix from the schema and also fills `it` when present). `tCOMd_GlobalPrice.com_TextID` points at it.
`tCOMd_Price` (article prices) *has* a `com_TextID` column but PDM's `INSERT INTO tCOMd_Price` never sets it, so
article prices carry no text block. Existing rows' links are never rewritten by the value update.

**PDM path** (`PriceMaintenance.AddMissingGlobalPricingRecords`, 9921; reached from `UpdatePriceThread` line 148
when "add global price placeholders" is chosen and from `PriceMaintenance` line 10400):

1. `SELECT com_TextID FROM tCOMd_GlobalPrice WHERE com_PackageID AND com_VariantCondition AND com_PriceListID` (10166)
2. no row: `SELECT com_TextID FROM tCOMd_Text WHERE com_PackageId AND com_TextName = <text12>` (10198)
3. none: `INSERT INTO tCOMd_Text (com_PackageId, com_TextTypeCode, com_TextName, <lang cols>) VALUES (pkg, 'price', text12, text11 ...)` (10214), re-SELECT the autonumber id (10218)
4. `INSERT INTO tCOMd_GlobalPrice (com_PackageId, com_PriceListID, com_VariantCondition, com_PriceTypeCode='S', com_PriceLevelCode='X', com_TextID, sys_ISOCurrencyCode, com_PriceIndex='', com_PriceValidFrom, com_PriceValidTo)` (10228)
5. for non-surcharge conditions without `_`, `UPDATE tCOMd_Text SET <lang cols> = text11` (10235)

`text11` (the language text) / `text12` (the name): a surcharge `ITEM 8=1FD` -> `Surcharge 8` / `8`; a condition with `_`
-> itself / itself; any other -> `"<cond>  (<Product_Code>)"` / `<cond>`. `Product_Code` is the item's PDM product code
(`ProductCodeIdOverride` wins); `PricingService` now carries it on global `PriceRecord`s (`product_code`).

**What the export does** (`services/price_text_blocks.py`, `services/price_mdb_export_service.py`):

| Case | Action |
|---|---|
| new global row, text exists | `reuse` - link to it |
| new global row, text missing | `create` the text (PDM's columns, MDB-generated `com_TextID`) then link; later rows with the same name `link_new` to it, so EUR and GBP share one text |
| existing global row with a link | `preserve` (value-only update; link untouched) |
| existing global row with no link | `unlinked` - reported, left unchanged (PDM does not repair it either) |
| several texts share the name | `skip` - row not inserted, reported (never guess) |
| `tCOMd_Text` has no language columns | `skip` - cannot create |
| article row | `none` |

All texts, price lists, price rows and updates run in **one transaction**.
New rows use symbolic identity tokens in the plan, not guessed numeric IDs.
The bridge omits their AutoNumber columns, reads `@@IDENTITY` immediately on
the same connection, and resolves later foreign-key references using those
generated IDs. Texts still precede prices and lists precede their price rows.
A failed batch stops and rolls back. Missing returned IDs are an explicit,
unverified export error, never replaced with invented IDs.
Query-only bridge batches open in read-only mode; preview executes no writes.
The approved plan digest includes text associations as well as write operations.
Read-back then checks: created texts exist with
the intended package/type/name/language text, each inserted row's `com_TextID` equals the generated id and resolves to
an existing text (no dangling reference), preserved rows keep their id, and no duplicate text name exists.

Regression coverage: `tests/test_pricing_fabric_targets.py` exercises new and
existing family targets, conflicts and invalid source relationships;
`tests/test_pricing_page_text_blocks.py` checks preview/result labels;
`tests/test_pricing_disposable_mdb.py` creates fresh ACE MDBs under pytest's
temporary directory, verifies preview file hashes, real AutoNumber/FK behavior,
EUR/GBP list reuse, repeat exports, preserved article/property connections,
new-list creation and transaction rollback. It never opens a production MDB.
The original legacy source is unavailable in this checkout; legacy claims
remain grounded in the source-derived notes and checked-in parity oracle,
not a newly executed desktop-PDM run.

**Intentional differences from PDM** (each has a test in `tests/test_pricing_pdm_text_parity.py`):

* Existing text content is **not rewritten** (PDM re-`UPDATE`s the language columns on every run, step 5). Kept deliberately: step 5 is a text-maintenance side effect, not price data, and rewriting would modify existing records the price export otherwise never touches. Consequence: a text whose label PDM would refresh stays as is.
* The name lookup is restricted to `com_TextTypeCode = 'price'` (PDM has no type filter). Checked on the real MDB: no non-price text shares a price-text name and no global price links to a non-price text, so the restriction changes nothing on current data and only guards against a future collision.
* Names are matched case-insensitively (as Jet does); an ambiguous name blocks the row instead of taking the last match.
* A missing `Product_Code` (snapshots computed before `product_code` existed) **blocks creating a code-labelled text** (`skip`, reason "Product_Code unknown; recompute prices") instead of creating a label PDM would never write. Rows that reuse a text, surcharge rows and `_` names need no code and are unaffected.
* Value and text are written in one step; PDM inserts a placeholder row first and fills the value in a second pass.

**Verified against a copy of the real MDB** (see the commit message for the numbers): dry run leaves the file
byte-identical; real export of 29 global + 8 article rows (EUR list 21, GBP list 22) updated 15 + 6 values, inserted
14 global rows (8 reusing existing texts, 6 linking 3 newly created texts shared by EUR and GBP) and 2 article rows;
no pre-existing text changed, no dangling reference, no new duplicate or orphan text, other lists' aggregates and
orphan lists 23/24 unchanged; a second export wrote nothing.

**Not done:** a differential run of the real PDM application (needs the PDM UI and PDMLive write access - not used
without explicit authorization), and an in-pCon check that the new texts render.


## Target price lists, computation date and currency routing

**Workflow (Pricing page).** *Export to MDB...* (or *Preview Export...*) -> pick the MDB -> **Target price lists**
dialog (one editable name per currency, prefilled `EURO_<year>` / `GBP_<year>`, moving to the sole mid-year suffix
`_2` when the base list exists but does not cover the computation date, or from the Price List Manager's named list)
-> exact preview (dry run) -> *Export to MDB* inside the preview. The preview carries a `plan_digest` (hash of every
planned write and the list plan); the write passes it back as `expected_plan` and **refuses** if the MDB or any input
differs ("run Preview Export again"). Changing a name, recomputing prices or editing the MDB therefore always needs a
new preview; the preview button without the export button never writes.

**Target resolution** (`services/price_list_targets.py`): labels match ignoring case / space / underscore / hyphen but
a created list keeps the operator's spelling. Several look-alikes (e.g. `EURO_2026_2` id 21 and `EURO 2026_2` id 24 in
the real MDB): the exact label wins, else a single region-linked list, else the export stops as ambiguous; ignored
look-alikes are reported. A reused list must have the same currency and its validity must cover the computation date
(otherwise blocked - never an older list); a label owned by another currency is blocked; EUR and GBP names must
differ; a missing list is created with the chosen name, the currency and `computation date .. 9999-12-31`, with a
warning that it is not region-linked (the export never links or unlinks regions) and, when it overlaps an existing
list, which one. Historical lists and rows are never changed or deleted.

**Computation date** = the date carried by the computed records (`valid_from`, set from the Pricing date picker);
today's date is never substituted - no date means "recompute". Each record is also checked against its target list's
period; a record outside it is blocked with its reason (`blocked_rows`).

**Routing.** Each record goes only to the target list of its own currency; the list's currency comes from the MDB row
read in the same session. After the write, the read-back checks every written row's currency and list id, that each
list the rows point at has that currency, and that a created list exists with the intended label, currency and dates.

**Sharing.** Verified on a copy with a second ACE connection open: a *shared* connection (like pCon reading) does not
block the write; an *exclusive* connection gives "file already in use", which is reported as a clear error with nothing
written. The MDB is not assumed unwritable.

**Verified on copies of the real MDB** (comp. date 2026-10-16, A) and a 2027-01-05 run that creates renamed lists (B):

| | A: reuse lists 21 / 22 | B: create `EURO_2027` / `GBP_2027` |
|---|---|---|
| list plan | reuse 21 (EUR) / 22 (GBP); look-alikes 24 / 23 ignored | create ids 25 / 26, 2027-01-05..9999-12-31 |
| global rows | 15 updated, 14 inserted | 29 inserted |
| article rows | 6 updated, 2 inserted | 8 inserted |
| texts | 3 created, 8 reused (+3 shared links), 14 preserved | 3 created, 23 reused |
| read-back | verified | verified |
| currency / list mismatches in whole MDB | 0 | 0 |
| unrelated rows, lists 23 / 24 | unchanged | unchanged |
| stale digest | refused, file unchanged | refused, file unchanged |
| second export | wrote nothing | wrote nothing |


## Historical actual PDM differential (real PDM, not a transcription)

This committed capture predates the current source-query changes. It was not
rerun for this update; its compiled-runtime/MDB outcomes are not new UI or
target verification of the implementation above.

**What was run.** The installed, compiled `PDMMaintenance.exe` (assembly version 1.0.9686.24988; its method signatures
match the source in `Desktop\PDM`) was loaded as a library from a copy and `UpdatePriceThread.execThread` - the method
PDM's *Update pCon prices* / *Create global price placeholders* buttons start - was executed with the arguments those
buttons pass, against an isolated copy of a backup MDB (`CADMaintenance.pConPath` redirected; the live MDB, PDM.bat and
PDM's UI were never touched). The same inputs (items, currency, price date 16-Oct-2026, site 1, price list, catalogue)
went through the Pricing compute core and `PriceMdbExportService` on a second identical copy, and the two result
states were compared with independent reads (only autonumber ids and row order ignored). SQL Server was only read:
every INSERT/UPDATE in the exercised PDM methods targets `tCOMd_*` Jet tables. Harness, driver and instructions:
`scripts/pdm_differential/`; machine-readable result: `docs/03_Workflows/pdm_differential_report.json`
(13 scenarios, all executed in real PDM, 0 unexplained; guarded by `tests/test_pdm_differential_report.py`).

| Scenario | PDM executed | Result |
|---|---|---|
| S1 article GBP: 3 changed values, unchanged rows, 1 deleted row (insert), 1 unpriced item | yes | **MATCH** (after the fix below) |
| S2 same, EUR list 21 | yes | **MATCH** |
| S3 first prices for articles that exist but have no price row | yes | **MATCH** (rows, validity) |
| S4 duplicate article identity, one stale | yes | **MATCH** |
| S4b duplicate identity, both stale | yes | historical difference; subsequent duplicate-loop fix retains the last supplied row |
| S5 / S8 global base + surcharge update, GBP / EUR, one missing global row | yes | identical except the missing row: PDM's value update never inserts (needs its placeholders step) |
| S6 PDM two-step (placeholders -> values) vs Pricing one step, text reused | yes | **MATCH** |
| S7 same, price text missing: created | yes | **MATCH** (text name, type, `<item>  (<Product_Code>)` in 4 languages, link) |
| S9 global item with surcharges, option texts `9168`/`3831` missing: 3 texts + 18 rows | yes | **MATCH** (names `Surcharge <optionId>`, labels, links, all 18 rows incl. values) |
| S10 existing text with a hand-edited label | yes | difference, intentional (below) |
| S11 non-price text sharing the item's name | yes | difference, intentional / protective (below) |
| S13 look-alike orphan list 23 | yes | difference, intentional / protective (below) |
| second execution of S1 / S5 / S6 | yes | PDM and Pricing both wrote nothing |

Also executed: unresolved item (S1 `GEPBPANNF.0608S4M`, S5 `GEBA.08`): neither side writes a base price; EUR vs GBP
routing (S1/S2/S5/S8); validity of inserted rows (PDM copies the article's existing dates, else the list's - Pricing
identical); in S5/S8 the stale base and surcharge rows were corrected identically (PDM 2 updates, 19 already current).

**Defect found by the differential and fixed.** For an item whose base price is unresolved, PDM wrote nothing
(it raises a `FormatException` dialog from `addNewArticlePriceRecord` - `double.Parse("")` - which the harness
dismisses like an operator clicking OK) while Pricing inserted that item's 7 upcharge rows without any base row. In the
real MDB every article upcharge has a base row (0 of 24 dangle) and every global surcharge has a base global row
(0 of 16,594). The exporter now inserts an upcharge only when its base row exists or is written by the same export
(`skipped_no_base_price`, reason in `blocked_reasons`); updating existing upcharge rows is unchanged.

**Remaining differences, each verified against real PDM:**

| Difference | Real-PDM evidence | Disposition |
|---|---|---|
| Historical duplicate identities: Pricing updated every stale duplicate | S4b: PDM updated only the last-read row, left the other at the stale value | Subsequently fixed to retain the last supplied Article/base row. Physical ID agreement is unverified because target queries do not guarantee row order. |
| Existing text content is not rewritten | S10: PDM reset a hand-edited label to `GE2HBS.  (FR-AA-US)` | Intentional - the price export is not a text-maintenance tool; label is cosmetic. Consequence: a text PDM would refresh stays as it is. |
| Text lookup restricted to `com_TextTypeCode = 'price'` | S11: PDM linked the new global row to an `artlong` text and **overwrote that article text's labels** | Intentional and protective. 0 such collisions in the real MDB today. |
| Ambiguous price-text name blocks the row | `tCOMd_Text` rejects a second text with the same package + type + name (case-insensitive; verified: "duplicate values in the index"), so this cannot occur within type `price` | Defensive only; kept and unit-tested. |
| Only the validated target list is written | S13: PDM's `LIKE 'GBP%2026%2'` also matched orphan list 23: it updated only one of the two stale base rows and treated list 23's surcharge rows as "up to date", so list 22 never got them | Intentional - required by the "do not touch lists 23/24" rule. |
| Missing global row inserted with its value in one step | S5/S8: PDM's value update reports "not found"; S6/S7/S9 show the two-step PDM workflow equals Pricing's single step | Intentional, equivalent end state. |
| Code-labelled text is blocked when `Product_Code` is unknown | PDM always has the code (read from SQL Server in the same run); cannot occur in PDM | Pricing-only safeguard for snapshots computed before `product_code` existed. |

**Not comparable with PDM (no equivalent in PDM, so not "verified against PDM"):** price-list name editing and the
computation-date / list-validity checks (PDM never checks that a list covers the date), strict currency routing
guards, plan-digest / stale-preview protection, transactions and rollback (PDM has none), read-back verification.
These are covered by Pricing unit tests and the real-MDB copy runs above, not by a PDM differential.

**Not verified at all:** how pCon renders any of this (physical pCon testing is out of scope).


## Calling the compiled legacy worker from Python

The opt-in adapter `services/legacy_pricing_engine.py` invokes the same
compiled `PDMMaintenance.UpdatePriceThread.execThread` method through
`scripts/pdm_differential/run_pdm_price_update.ps1`. It accepts the actual
Maintenance inputs (item list, program, site, catalogue, date, currency, price
list and package) and returns the worker status, unresolved items and assembly
version. Unit tests mock the subprocess; they do not claim the installed legacy
assembly was run.

Example from a controlled diagnostic script:

```python
from services.legacy_pricing_engine import (
    LegacyPricingEngineRequest,
    run_legacy_pricing_engine,
)

request = LegacyPricingEngineRequest(
    pdm_dir=r"C:\\scratch\\pdm_copy",
    pcon_root=r"C:\\scratch\\legacy_pricing_sandbox",
    workspace="Layout_Studio",
    mode="global",
    items=["RY3SNNB.105512F"],
    program_code="revive",
    site_id=1,
    catalogue_id=658,
    mydate="27-Oct-2026",
    prevdate="26-Oct-2026",
    currency="EUR",
    price_list_id=26,
    price_list_label="EURO_2026_2",
    package_id=240,
    isolated_mdb_confirmed=True,
)
result = run_legacy_pricing_engine(request)
print(result)
```

Before running, prepare `pcon_root\\WS\\Layout_Studio\\pcr_data_com_ocd.mdb`
as a disposable copy of the matching package MDB, and copy the full legacy PDM
runtime (including `ExprEvaluator.dll`) into `pdm_dir`. Use the same values
as the PDM form. The method writes to that MDB and has no rollback, so never
point it at the live OCD. The legacy SQL connection still follows PDM's own
connection policy; only use an approved test target.

This adapter is deliberately not wired as the production Pricing engine yet.
The legacy worker updates price rows already present in the MDB and has
different missing-row/placeholder semantics from the Workbench's compute and
export flow. First compare its output with the current workflow on the same
input and classify option-condition differences (Fabric Type, Fabric Colour,
Trim, Finish and other options). Only a demonstrated parity fix should then
change the Maintenance workflow.
