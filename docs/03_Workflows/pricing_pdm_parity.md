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

## Evidence from the real MDB (backup copy)

* Lists 23/24 (`GBP 2026_2` / `EURO 2026_2`) held the 1,520 earlier rows and have no region link;
  region 6 (EURO) -> list 21 and region 7 (GBP) -> list 22 (`EURO_2026_2` / `GBP_2026_2`), whose level-`X`
  rows for the same variants were 0 in 54 of 57 overlapping cases.
* All 132,964 vendor global rows are level `X`; no duplicate (package, list, variant) exists.
* Every vendor global row has a `com_TextID`; all 760 variants of the earlier export resolve through the
  PDM text-name rule to an existing `price` text.

## Global increment fetch comparison (PDM Test, 2026-10-18)

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
query orders by `OrderCodeValue`; the tool Global fetch now filters inactive
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
| new global row, text missing | `create` the text (PDM's columns, `com_TextID` = max+1) then link; later rows with the same name `link_new` to it, so EUR and GBP share one text |
| existing global row with a link | `preserve` (value-only update; link untouched) |
| existing global row with no link | `unlinked` - reported, left unchanged (PDM does not repair it either) |
| several texts share the name | `skip` - row not inserted, reported (never guess) |
| `tCOMd_Text` has no language columns | `skip` - cannot create |
| article row | `none` |

All texts, price rows and updates run in **one transaction**; ids are allocated explicitly (max+1) so the text id is
known when the global row is built. A failed batch changes nothing. Read-back then checks: created texts exist with
the intended package/type/name/language text, each inserted row's `com_TextID` equals the planned id and resolves to
an existing text (no dangling reference), preserved rows keep their id, and no duplicate text name exists.

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


## Actual PDM differential (real PDM, not a transcription)

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
| S4b duplicate identity, both stale | yes | difference, intentional (below) |
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
| Duplicate identities: Pricing updates every stale duplicate | S4b: PDM updated only the last-read row, left the other at the stale value | Intentional - pCon may read either row. Real-MDB scope has no duplicates (`duplicate_matches` 0). |
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
