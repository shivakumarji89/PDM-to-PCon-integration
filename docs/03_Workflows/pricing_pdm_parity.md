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
| Duplicates | base path updates the **last** row read; surcharge path updates every row | updates **every** differing duplicate row (decision in commit 5a5655e) - intentional difference |
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

## Decisions on the two intentional differences

**Duplicate rows - keep "update every duplicate".** PDM's base-price path updates the last row it reads;
its surcharge path updates all rows. pCon can read either duplicate, so correcting only one can leave a stale
value on screen (the reason for commit 5a5655e). Every row is written only if its own value differs, so the
result is a superset of PDM's and never worse. The real MDB has **no** duplicate identity in the planned
scope (`duplicate_matches: 0` in the dry run), so on current data both behaviours are identical. The export
reports `duplicate_matches`, so a duplicate-bearing file is visible before writing.

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

* Existing text content is **not rewritten** (PDM re-`UPDATE`s the language columns on every run, step 5). A hand-translated label survives.
* The name lookup is restricted to `com_TextTypeCode = 'price'` (PDM has no type filter and could link a global price to an `artlong` text that shares the item's name).
* Names are matched case-insensitively (as Jet does); an ambiguous name blocks the row instead of taking the last match.
* A missing `Product_Code` (snapshots computed before `product_code` existed) creates the text without the `(code)` suffix and warns; recomputing fixes it. PDM always has the code because it reads it from SQL Server during the run.
* Value and text are written in one step; PDM inserts a placeholder row first and fills the value in a second pass.

**Verified against a copy of the real MDB** (see the commit message for the numbers): dry run leaves the file
byte-identical; real export of 29 global + 8 article rows (EUR list 21, GBP list 22) updated 15 + 6 values, inserted
14 global rows (8 reusing existing texts, 6 linking 3 newly created texts shared by EUR and GBP) and 2 article rows;
no pre-existing text changed, no dangling reference, no new duplicate or orphan text, other lists' aggregates and
orphan lists 23/24 unchanged; a second export wrote nothing.

**Not done:** a differential run of the real PDM application (needs the PDM UI and PDMLive write access - not used
without explicit authorization), and an in-pCon check that the new texts render.
