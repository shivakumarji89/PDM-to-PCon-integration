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
| Missing global row | created separately: level **`X`**, `com_TextID` linked to the `price` text, list's validity dates, value filled by the update | inserted at level `X`, `com_TextID` looked up in `tCOMd_Text` by PDM's name rule (surcharge `ITEM 8=1FD` -> text `8`), list's validity dates. Texts are looked up, **not created** (PDM would create a missing `tCOMd_Text`); rows without a text are reported. |
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
