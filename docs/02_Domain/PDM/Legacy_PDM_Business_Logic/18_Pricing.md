# 18 — Pricing

**Module prefix:** BR-PRICE
**Primary legacy source:** `PriceMaintenance.cs` (~11 298 lines), `FinancialMaintenance.cs` (~3 553), `PConPriceUpdate.cs` (~3 013), `CustomPricePerm.cs` (~2 109), `IncPriceThread.cs`, `UpdatePriceThread.cs`, `UpdatePricesThread.cs`, `ItemPriceExport.cs`, `ocdPrice.cs`; DB objects `fnGetListPrice`, `fnGetListPriceByItem`, `fnGetFabricBandOrderCodes`, stored procs `PricePermutation`, `PDMOptionDataReport`, `PDMOptionDataReportWithIncList`.
**Status:** Verified from source unless marked `UNKNOWN`.

> Foundation facts (documented in `00_System_Architecture.md` / `01_Authentication.md` / `02_User_Permissions.md`, reused here):
> identity = Windows account (`Environment.UserName.ToLower()`); `ConnectionFactory.CreateNewConnection` → `SqlConnection`; inline **string‑concatenated SQL** (injection‑prone); `Global` static singleton (`connectedServer`, `connectedDB`); `-1` = invalid/unset sentinel; permission flags on `AuthenticateUser` (`PriceMaintenance`, `CurrencyMaintenance`, `ExchangeRates`, `ReadOnlyFinancial`, `FormulaMaintenance`).

---

## 1. Purpose

Price Maintenance is the module that manages **item base prices**, **incremental (option/upcharge) prices**, **price formulas (uplift factors)**, and downstream **price calculation / export**. It centres on the SQL price model:

- **Base prices** live on `Item` in three "slots" — `BasePrice`, `BasePrice2`, `BasePrice3`. Which slot is authoritative for a given product/site is chosen by `Product_Code.BasePriceRef` (1/2/3).
- **Incremental prices** live on `ItemOptionValues` in three matching slots — `IncrementalPrice`, `IncrementalPrice2`, `IncrementalPrice3`.
- **List price = base price + uplift**, where the uplift percentage comes from `PriceFormula.FirstPrice`, selected through `PriceMatrix` (product‑line `ItemPriceCode` × currency `CustPriceCode`). Currency conversion uses `ExchangeRate.BuyRate`.

The module supports four operational flows:

1. **Interactive grid maintenance** (`PriceMaintenance` form) — view/edit base and incremental prices per site/currency/catalogue, import from CSV, export permutations.
2. **Price‑formula CRUD** (`FinancialMaintenance` form) — insert/update/delete `PriceFormula` records with full audit.
3. **pCon price push** (`PConPriceUpdate` + `UpdatePriceThread`) — copy PDM list prices into an external pCon configurator MDB (`tCOMd_*` tables via Jet OLE DB).
4. **Bespoke exports** (`ItemPriceExport`, `CustomPricePerm`, `ClippingsExport`) — flat price‑permutation files for third parties.

`ocdPrice` is a pure in‑memory DTO for the OCD `ocd_price` export (module 21), not a table.

---

## 2. Entry Points

| # | Trigger | Location | Kind |
|---|---------|----------|------|
| E1 | Main menu → **Price Maintenance** button | `MainMenu.cs:2750` `PriceMaintButton_Click` → `new PriceMaintenance()` | Opens grid form |
| E2 | Main menu → **Static Maintenance** button, **right‑click** | `MainMenu.cs:2867` `StaticMaintButton_Click` → `new FinancialMaintenance()` | Opens price‑formula form |
| E3 | Price Maintenance → **Update pCon Prices** button | `PriceMaintenance.cs:9631` `_button_update_pcon_MouseDown` → `new PConPriceUpdate()` | Opens pCon push form |
| E4 | Price Maintenance → import base prices (CSV) | `PriceMaintenance.cs:3346` `importPricesFromExcel` | Bulk base‑price update |
| E5 | Price Maintenance → import incremental prices (CSV) | `PriceMaintenance.cs:3745` `importIncPricesFromExcel` | Bulk inc‑price update |
| E6 | Price Maintenance → US/Mexico base import (background) | `PriceMaintenance.cs:3315` `importPricesFromExcelUSUpdate` → `UpdatePricesThread` | Slot‑2 base import |
| E7 | Price Maintenance → item selection change / grid load | `PriceMaintenance.cs` `IncPriceThread`, `showListPrices` | Async grid population |
| E8 | Price Maintenance → validate product line code | `PriceMaintenance.cs:3254` `validateProductLineCode` | Diagnostic |
| E9 | pCon form → **Update Article / Global Pricing** | `PConPriceUpdate.cs` → `UpdatePriceThread.execThread` | Threaded pCon push |
| E10 | Financial form → **Insert / Submit** | `FinancialMaintenance.cs` `SubmitButton_Click` → `updateOrInsertPriceFormula` | PriceFormula insert/update |
| E11 | Financial form → **Delete Selected** | `FinancialMaintenance.cs:2308` `DeleteButton_Click` → `deletePriceFormula` | PriceFormula delete |
| E12 | Item price export tool | `ItemPriceExport.cs:172` `ExportItemPrices` | Flat‑file price export |
| E13 | `CustomPricePerm` custom permutation export | `CustomPricePerm.cs` (`ExecuteSeating`, `getPriceLineGBPandEUR`, `getLine`) | **ORPHANED — never instantiated** (see §7) |
| E14 | Reused by SIF import for reverse‑uplift | `SIFImport.cs:9009`, `:9499` call `PriceMaintenance.getBasePrice(...)` | Cross‑module reuse |

---

## 3. Call Hierarchy

Interactive base‑price CSV import (representative path):

```
MainMenu.PriceMaintButton_Click
  └─ PriceMaintenance (Form)
       ├─ initialiseArrays()                → loads Site / Currency / Catalogue / Category selectors (Q-PRICE-001..004)
       ├─ importPricesFromExcel (Event: button)
       │    ├─ [parse CSV → item,listprice pairs]
       │    ├─ resolve item price context   → SELECT Item.ItemId, pc.Product_Code, pc.BasePriceRef,
       │    │                                        pc.PriceCode, pm.PriceFormula, pf.FirstPrice … (Q-PRICE-020)
       │    ├─ getBasePrice(listprice,…)     → reverse‑uplift calculation (Q-PRICE-030/031/032 ; BR-PRICE-030)
       │    │      ├─ SELECT DomCurrCode FROM Site …             (Q-PRICE-030)
       │    │      ├─ SELECT BuyRate FROM ExchangeRate …         (Q-PRICE-031)
       │    │      └─ SELECT pf.FirstPrice FROM PriceMatrix pm … (Q-PRICE-032)
       │    └─ updateItemBasePrice(itemId, basestr, priceref)
       │           ├─ SELECT BasePrice,BasePrice2,BasePrice3 …   (Q-PRICE-040)
       │           ├─ [audit] INSERT Transactions / ItemPriceUpdates (Q-PRICE-041/042 ; BR-PRICE-060)
       │           └─ UPDATE Item SET BasePrice[n] = …           (Q-PRICE-043)
       └─ (List/UI) getListPrice() → SELECT dbo.fnGetListPrice(…) (Q-PRICE-050 ; forward uplift, DB function)
```

Price‑formula CRUD (Financial form):

```
FinancialMaintenance.SubmitButton_Click
  └─ updateOrInsertPriceFormula(id, siteId, dcc, formula, factor, date)
       ├─ SELECT … FROM PriceFormula WHERE PriceFormulaId = …   (Q-PRICE-070, read prior values)
       ├─ INSERT PDMAudit..Transactions ; SELECT TOP 1 TransactionId (Q-PRICE-071/072)
       ├─ INSERT PDMAudit..PFUpdates (…, Prev…)                 (Q-PRICE-073 ; BR-PRICE-061)
       └─ INSERT PriceFormula (…) | UPDATE PriceFormula (…)     (Q-PRICE-074/075)
FinancialMaintenance.DeleteButton_Click → deletePriceFormula(id)
       ├─ SELECT … FROM PriceFormula …                          (Q-PRICE-076)
       ├─ INSERT PDMAudit..Transactions / PFUpdates             (Q-PRICE-073)
       └─ DELETE FROM PriceFormula WHERE PriceFormulaId = …     (Q-PRICE-077)
```

pCon push (threaded):

```
PriceMaintenance._button_update_pcon_MouseDown → PConPriceUpdate (Form)
  └─ UpdatePriceThread.execThread (Thread)
       ├─ SELECT Notes FROM Item …                              (Q-PRICE-090, prefix length)
       ├─ PriceMaintenance.UpdatePConItemPrice(…)               (OLE DB Jet ↔ SQL)
       │      ├─ SELECT … FROM tCOMd_Price INNER JOIN tCOMd_Article … (Q-PRICE-091)
       │      ├─ SELECT dbo.fnGetListPriceByItem(item,ccy,date,1,NULL) (Q-PRICE-092)
       │      └─ UPDATE tCOMd_Price/tCOMd_GlobalPrice SET com_PriceValue = … (Q-PRICE-093/094)
       └─ PriceMaintenance.UpdatePConItemIncrementalPrice(…)
```

---

## 4. SQL Analysis

> All queries below are inline, string‑concatenated, and interpolate raw values → **SQL‑injection surface** (`BR-PRICE-100`). WHERE noted, values derive from the CSV file, item codes, or selector text.

### Selector / bootstrap queries (`PriceMaintenance.initialiseArrays`, `PConPriceUpdate`)

**Q-PRICE-001** — Sites (site 20 hidden). *Why:* populate the site selector; site 20 is a virtual/aggregate site excluded everywhere.
```sql
SELECT SiteId, Description FROM Site WHERE SiteId NOT IN (20)
```
`PriceMaintenance.cs:2539`, `PConPriceUpdate.cs:1555` (adds `WITH (NOLOCK)`).

**Q-PRICE-002** — Currencies. *Why:* populate the currency selector, retaining `PriceCode` used to join `PriceMatrix`.
```sql
SELECT Currency_ID, Currency, Description, Symbol FROM Currency
```
`PriceMaintenance.cs:2560` (`PConPriceUpdate.cs:1572` selects only `Currency_ID, Currency`).

**Q-PRICE-003** — Catalogues visible to user (with read‑only flag + item counts). *Why:* scope pricing to catalogues the user may see; `puc.ReadOnly` drives read‑only gating (BR‑PRICE‑050). Full text (line truncated in source dump but header shown):
```sql
SELECT DISTINCT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly, Catalogue.CatalogueType ,
       SUM(CASE WHEN pgc … ) …
```
`PriceMaintenance.cs:2584`, `PConPriceUpdate.cs:1588`. (Aggregated per‑catalogue item count; full body UNKNOWN beyond header.)

**Q-PRICE-004** — Product categories for a catalogue (`-1` display order pushed to `9999`). *Why:* category selector; mirrors ordering rule in `04_Product_Categories.md`.
```sql
SELECT pc.ProductCategoryId, od.ShortDescription,
       CASE WHEN cpc.DisplayOrder = -1 THEN 9999 ELSE cpc.DisplayOrder … END …
```
`PriceMaintenance.cs:2740`, `FinancialMaintenance.cs:2110`, `PConPriceUpdate.cs:1623`.

**Q-PRICE-005** — US‑category test. *Why:* categories flagged `USCategory` route to the `US*` shadow tables instead of the main `Item`/`ItemOptionValues` tables.
```sql
SELECT USCategory FROM ProductCategory WHERE ProductCategoryId = <categoryId>
```
`PriceMaintenance.cs:2820` (`isUSCategory`).

### Item / product‑code resolution

**Q-PRICE-020** — Full price context for an item under the selected site + currency. *Why:* the heart of import validation — resolves product code, base‑price slot (`BasePriceRef`), the currency’s `PriceCode`→`PriceMatrix`→`PriceFormula`, and the newest `FirstPrice`. Left joins so missing links surface as blank columns (→ exception messages).
```sql
SELECT Item.ItemId, pc.Product_Code, pc.BasePriceRef, pc.PriceCode, pm.PriceFormula, pf.FirstPrice
FROM Item
INNER JOIN Product ON Item.ProductId = Product.ProductId
LEFT OUTER JOIN Product_Code pc
       ON CASE WHEN Item.ProductCodeIdOverride IS NOT NULL
               THEN Item.ProductCodeIdOverride ELSE Product.ProductCodeId END = pc.ProductCodeId
      AND pc.SiteId = <siteId>
LEFT OUTER JOIN PriceMatrix pm
       ON pc.PriceCode = pm.ItemPriceCode
      AND pm.CustPriceCode IN (SELECT PriceCode FROM Currency WHERE Currency_ID = <currencyId>)
LEFT OUTER JOIN PriceFormula pf
       ON pm.PriceFormula = pf.PriceFormula
      AND pf.DomCurrCode = '<currencyCode>' AND pf.SiteId = <siteId>
WHERE Item = '<item>'
  AND (ItemId IN (SELECT ItemId FROM CatalogueItems WHERE CatalogueId = <catId>)
    OR ItemId IN (SELECT ItemId FROM CatalogueItemsUnreleased WHERE CatalogueId = <catId>)
    OR Item.IsSuperItem = 1)
ORDER BY pf.EffectiveDate DESC
```
`PriceMaintenance.cs:3595` (base import) & `:4020` (inc import). The catalogue filter is **omitted when catalogue id = 81** ("Spares & Parts" = all‑items scope, BR‑PRICE‑014). `ProductCodeIdOverride` (item‑level product‑code override) takes precedence over the product’s default code (BR‑PRICE‑011).

**Q-PRICE-021** — Product‑line / price‑code lookup for the manual validate button.
```sql
SELECT pc.ProductCodeId, pc.Product_Code, pc.PriceCode
FROM Item
INNER JOIN Product ON Item.ProductId = Product.ProductId
INNER JOIN Product_Code pc ON Product.ProductCodeId = pc.ProductCodeId AND pc.SiteId = <siteId>
WHERE Item.ItemId = <itemId>
```
`PriceMaintenance.cs:3268`.

**Q-PRICE-022** — Price formula name via matrix for validate button.
```sql
SELECT PriceFormula FROM PriceMatrix
WHERE ItemPriceCode = '<priceCode>'
  AND CustPriceCode IN (SELECT PriceCode FROM Currency WHERE Currency = '<currencyCode>')
```
`PriceMaintenance.cs:3281`.

**Q-PRICE-023** — Uplift factor for validate button.
```sql
SELECT FirstPrice FROM PriceFormula WHERE PriceFormula = '<formula>' AND SiteId = <siteId>
```
`PriceMaintenance.cs:3293`.

### Base‑price read/write (`updateItemBasePrice`, `PriceMaintenance.cs:6106`)

**Q-PRICE-040** — Read current base prices (all 3 slots).
```sql
SELECT BasePrice, BasePrice2, BasePrice3 FROM Item WHERE ItemId = <itemId>
```

**Q-PRICE-041/042** — Audit transaction header + id (PDMAudit database, only when server is **not** `eoscloud`).
```sql
INSERT INTO Transactions (UserName, TransactionDate, DatabaseEffected)
VALUES ('<user>', GetUTCDate(), '<connectedDB>')
SELECT TOP 1 TransactionId FROM Transactions WHERE UserName = '<user>' ORDER BY TransactionId DESC
```

**Q-PRICE-042b** — Base‑price audit row (before/after values per slot).
```sql
INSERT INTO ItemPriceUpdates
 (TransactionId, ItemId, PrevBasePrice, PrevBasePrice2, PrevBasePrice3,
  NewBasePrice, NewBasePrice2, NewBasePrice3)
VALUES (<tx>, <itemId>, <prev1|NULL>, <prev2|NULL>, <prev3|NULL>, <new/prev per priceref>)
```

**Q-PRICE-043** — Commit the base price into the slot selected by `priceref` (1→`BasePrice`, 2→`BasePrice2`, 3→`BasePrice3`).
```sql
UPDATE Item SET BasePrice = <basestr> WHERE ItemId = <itemId>   -- (or BasePrice2 / BasePrice3)
```

### Incremental‑price read/write (`updateItemOptIncPrice`, `PriceMaintenance.cs:6253`)

**Q-PRICE-044** — Read current incremental prices.
```sql
SELECT IncrementalPrice, IncrementalPrice2, IncrementalPrice3
FROM ItemOptionValues WHERE ItemId = <itemId> AND OptionValueId = <optvalId>
```

**Q-PRICE-045** — Inc‑price audit row.
```sql
INSERT INTO IncrementalPriceUpdates
 (TransactionId, ItemId, OptionValueId, PrevIncPrice, PrevIncPrice2, PrevIncPrice3,
  NewIncPrice, NewIncPrice2, NewIncPrice3)
VALUES (<tx>, <itemId>, <optvalId>, …)
```

**Q-PRICE-046** — Insert vs update decision (row may not yet exist).
```sql
SELECT COUNT(*) AS cnt FROM ItemOptionValues WHERE ItemId = <itemId> AND OptionValueId = <optvalId>
```

**Q-PRICE-047** — Commit inc price (insert when absent & non‑NULL; else update; NULL insert is skipped).
```sql
INSERT INTO ItemOptionValues (ItemId, OptionValueId, IncrementalPrice) VALUES (<itemId>,<optvalId>,<v>)
-- or
UPDATE ItemOptionValues SET IncrementalPrice = <v> WHERE OptionValueId = <optvalId> AND ItemId = <itemId>
```
(slot column `IncrementalPrice[2|3]` chosen by `priceref`).

### Price calculation — reverse uplift (`getBasePrice`, `PriceMaintenance.cs:6040`, **public static**)

**Q-PRICE-030** — Site domestic currency.
```sql
SELECT DomCurrCode FROM Site WHERE SiteId = <siteId>
```
**Q-PRICE-031** — Exchange buy‑rate (only when input currency ≠ site domestic currency).
```sql
SELECT BuyRate FROM ExchangeRate
WHERE CurrCode = '<currency>' AND DomCurrCode = '<siteDomCurr>'
  AND EffectiveDate <= '<effdate dd-MMM-yyyy>'
ORDER BY EffectiveDate DESC
```
**Q-PRICE-032** — Uplift percentage for the item’s price code.
```sql
SELECT pf.FirstPrice
FROM PriceMatrix pm INNER JOIN PriceFormula pf ON pm.PriceFormula = pf.PriceFormula
WHERE pf.SiteId = <siteId> AND pm.CustPriceCode = '<currencyPriceCode>'
  AND pm.ItemPriceCode = '<pricecode>'
  AND DATEDIFF(DAY, pf.EffectiveDate, '<effdate>') >= 0
ORDER BY pf.EffectiveDate DESC
```
*Why:* takes a list price and works **backwards** to the base price. See BR‑PRICE‑030 for the exact formula.

### Price calculation — forward uplift (DB functions)

**Q-PRICE-050** — Forward list price from a base price (`getListPrice`, `PriceMaintenance.cs:4613`).
```sql
SELECT dbo.fnGetListPrice('<currency>', <basePrice>, '<itemPriceCode>',
        '<effDate dd-MMM-yyyy>', 'DMY', <rounding>, <siteId>, <custPriceCodeOverride|NULL>) AS ListPrice
```
**Q-PRICE-051** — List price directly from an item (`ItemPriceExport`, `UpdatePConItemPrice`, `ClippingsExport`, `CADMaintenance`).
```sql
SELECT dbo.fnGetListPriceByItem('<item>', '<currency>', '<effDate>', <siteId>, NULL) AS ListPrice
```
Grid variants embed `fnGetListPrice(...)` with a `CASE WHEN pc.BasePriceRef = 1 THEN Item.BasePrice … END` argument (`PriceMaintenance.cs:4220`, `:6561`, `:6610`) — the base slot is chosen inline by `BasePriceRef`. **The bodies of `fnGetListPrice*` are SQL‑side and are `UNKNOWN` from this source set** (they implement the forward uplift + rounding, mirror of Q‑PRICE‑030..032).

### Fabric‑band incremental grid (`IncPriceThread.execThread`)

**Q-PRICE-060** — Fabric price bands with generated order‑code lists and list/base inc price. *Why:* fabric options are priced by **band** not individual value; `fnGetFabricBandOrderCodes` and `fnGetListPrice` are used, `FabricBands.PriceBand`/`Application` group the values.
```sql
SELECT DISTINCT fb.PriceBand, 'Band ' + convert(varchar, fb.PriceBand) AS Name,
       dbo.fnGetFabricBandOrderCodes(<catalogueId>, fb.PriceBand, <optval…>) AS [OrderCode(s)],
       …  itov.IncrementalPrice[2|3]  … | dbo.fnGetListPrice('<currency>', itov.IncrementalPrice[n], …)
FROM OptionValue optval
LEFT OUTER JOIN ( … ItemOptionValues itov … Product_Code pc … PriceMatrix pm … Currency … ) AS itov
       ON optval.OptionValueId = itov.OptionValueId
INNER JOIN FabricBands fb ON optval.OptionValueId = fb.OptionValueId
INNER JOIN CatalogueOptionValues cov ON optval.OptionValueId = cov.OptionValueId
WHERE cov.CatalogueId = <catalogueId> AND fb.Application = <appband> AND optval.OptionId = <optionId> …
```
`IncPriceThread.cs` (full text in source). `CommandTimeout = 300` (BR‑PRICE‑103).

### Price‑formula CRUD (`FinancialMaintenance`)

**Q-PRICE-070** — Read PriceFormula list for the grid.
```sql
SELECT DISTINCT pf.PriceFormulaId, Site.SiteId, Site.Site, pf.DomCurrCode, pf.PriceFormula,
       pf.FirstPrice, REPLA… (EffectiveDate formatting) …
```
`FinancialMaintenance.cs:1701`, `:1929`.

**Q-PRICE-073** — PriceFormula audit (before/after, PDMAudit database).
```sql
INSERT INTO PDMAudit.dbo.PFUpdates
 (PriceFormulaId, TransactionId, SiteId, DomCurrCode, EffectiveDate, FirstBase, FirstPrice,
  PriceFormula, PrevDomCurrCode, PrevEffectiveDate, PrevFirstBase, PrevFirstPrice, PrevPriceFormula)
VALUES (…)
```
`FinancialMaintenance.cs:2285` (delete), `:2455` (upsert).

**Q-PRICE-074** — Insert new PriceFormula (`FirstBase` hard‑coded `'P1'`).
```sql
INSERT INTO PriceFormula (SiteId, DomCurrCode, PriceFormula, FirstPrice, EffectiveDate, FirstBase)
VALUES (<siteId>, '<dcc>', '<formula>', <factor>, '<date>', 'P1')
```
**Q-PRICE-075** — Update existing PriceFormula.
```sql
UPDATE PriceFormula SET SiteId = <siteId>, DomCurrCode = '<dcc>', PriceFormula = '<formula>',
       FirstPrice = <factor>, EffectiveDate = '<date>' WHERE PriceFormulaId = <id>
```
**Q-PRICE-077** — Delete PriceFormula (after writing audit).
```sql
DELETE FROM PriceFormula WHERE PriceFormulaId = <priceFormulaId>
```
`FinancialMaintenance.cs:2288`.

### pCon push (OLE DB Jet MDB `pcr_data_com_ocd.mdb` ↔ SQL) — `UpdatePConItemPrice` (`PriceMaintenance.cs:8714`)

**Q-PRICE-090** — Item note → prefix length (variant split).
```sql
SELECT Notes FROM Item WHERE Item = '<item>'
```
`UpdatePriceThread.cs:156` (value ≤ 20 used as prefix length; comma‑delimited, first token).

**Q-PRICE-091** — Existing article price row in pCon (base level `'B'`).
```sql
SELECT tCOMd_Article.com_ArticleCode, tCOMd_Price.com_PriceID, tCOMd_Price.com_ArticleID,
       tCOMd_Price.com_PriceValue, tCOMd_Price.com_VariantCondition,
       tCOMd_Price.com_PriceValidFrom, tCOMd_Price.com_PriceValidTo
FROM tCOMd_Price INNER JOIN tCOMd_Article ON tCOMd_Price.com_ArticleID = tCOMd_Article.com_ArticleID
  AND (tCOMd_Article.com_ArticleCode = '<item>' OR … LIKE '<article>%' AND com_VariantCondition = '<varcond>' …)
WHERE com_PriceListID IN (SELECT com_PriceListID FROM tCOMd_PriceList2
                          WHERE com_PriceListLabel Like '<pricelist with _→%>')
  AND tCOMd_Price.com_PriceLevelCode = 'B'
```
**Q-PRICE-092** — PDM list price to push (skipped when `resetToZero`).
```sql
SELECT dbo.fnGetListPriceByItem('<item>', '<currency>', '<mydate>', 1, NULL) As price
```
**Q-PRICE-093/094** — Write price into pCon MDB.
```sql
UPDATE tCOMd_GlobalPrice SET com_PriceValue = <listprice> WHERE com_GlobalPriceID = <id>
-- or article-level
UPDATE tCOMd_Price       SET com_PriceValue = <listprice> WHERE com_PriceID = <id>
```
Global‑price fallback lookup (SuperProduct / hybrid pricing):
```sql
SELECT tCOMd_GlobalPrice.com_GlobalPriceID, com_VariantCondition, com_PriceValue
FROM tCOMd_PriceList2 INNER JOIN (tCOMd_Package INNER JOIN tCOMd_GlobalPrice
     ON tCOMd_Package.com_PackageID = tCOMd_GlobalPrice.com_PackageID)
     ON tCOMd_PriceList2.com_PriceListID = tCOMd_GlobalPrice.com_PriceListID
WHERE (com_VariantCondition = '<item>' OR com_VariantCondition = '<item w/o dots>')
  AND tCOMd_Package.reg_ProgramCode = '<actualProgramCode>'
  AND com_PriceListLabel LIKE '<pricelist>'
```
`PConPriceUpdate.cs` also manages the pCon price lists directly (`tCOMd_Price`, `tCOMd_GlobalPrice`, `tCOMd_PriceList2`, `tCOMd_Article`, `tCOMd_Package`): copy‑between‑lists (`INSERT INTO tCOMd_Price/tCOMd_GlobalPrice … `, `:2579`/`:2582`), delete (`DELETE FROM tCOMd_GlobalPrice WHERE com_GlobalPriceID IN (…)`, `:1985`), and reads at `:1661`, `:1763`, `:1775`, `:1827`, `:2413`, `:2563`, `:2574`, `:2611`.

### US / Mexico slot‑2 import (`UpdatePricesThread`)

**Q-PRICE-095** — Create missing shadow product/item, write `BasePrice2`.
```sql
SELECT ItemId, BasePrice, BasePrice2, BasePrice3 FROM Item WHERE Item = '<item>'
INSERT INTO Product (Product, Name, ProductRangeId) VALUES ('<item>','<item>',1000)
INSERT INTO Item (ProductId, Item) VALUES (<productId>, '<item>')
UPDATE Item SET BasePrice2 = <price> WHERE Item = '<item>'
```
`UpdatePricesThread.cs:166‑258`.

**Q-PRICE-096** — Slot‑2 incremental write.
```sql
SELECT IncrementalPrice2 AS inc_price FROM ItemOptionValues WHERE ItemId = <id> AND OptionValueId = <ov>
UPDATE ItemOptionValues SET IncrementalPrice2 = <v> WHERE ItemId = <id> AND OptionValueId = <ov>
INSERT INTO ItemOptionValues (ItemId, OptionValueId, IncrementalPrice2) VALUES (<id>, <ov>, <v>)
```
`UpdatePricesThread.cs:394‑447`.

### Housekeeping

**Q-PRICE-097** — Delete empty inc‑price rows (all 3 slots NULL).
```sql
DELETE FROM ItemOptionValues WHERE IncrementalPrice IS NULL AND IncrementalPrice2 IS NULL AND IncrementalPrice3 IS NULL
```
`PriceMaintenance.cs:3033`.

### CustomPricePerm exchange lookup (orphaned form)

**Q-PRICE-098** — GBP→EUR live rate.
```sql
SELECT BuyRate FROM ExchangeRate WHERE (DomCurrCode = 'GBP') AND (CurrCode = 'EUR') ORDER BY EffectiveDate DESC
```
`CustomPricePerm.cs:988`.

**Q-PRICE-099** — SuperProduct component first price (note the malformed cross‑join join order preserved verbatim).
```sql
SELECT TOP 1 PriceFormula.FirstPrice
FROM PriceMatrix INNER JOIN PriceFormula ON PriceMatrix.PriceFormula = PriceFormula.PriceFormula
     INNER JOIN ItemComponents INNER JOIN Item ON ItemComponents.ItemId = Item.ItemId
     INNER JOIN Item Item_1 ON ItemComponents.SubItemId = Item_1.ItemId
     INNER JOIN Product ON Item_1.ProductId = Product.ProductId
     INNER JOIN Product_Code ON Product.ProductCodeId = Product_Code.ProductCodeId
       ON PriceMatrix.ItemPRiceCode = Product_Code.PriceCode
WHERE (Item.ItemId = <id>) AND (PriceFormula.DomCurrCode = 'GBP') ORDER BY PriceFormula.EffectiveDate DESC
```
`CustomPricePerm.cs:1127`, `:1448`.

---

## 5. Data Model

### `PriceFormula` — the uplift factor (per site + domestic currency)
| Column | PK/FK | Meaning |
|---|---|---|
| `PriceFormulaId` | PK | identity |
| `SiteId` | FK→`Site` | which site the factor applies to |
| `DomCurrCode` | — | domestic currency code, e.g. `GBP`, `EUR`, `USD` (matches `Currency.Currency`) |
| `PriceFormula` | — | the formula **name/code** joined from `PriceMatrix.PriceFormula` |
| `FirstPrice` | — | **uplift percentage** (e.g. `35` = +35 %). Divided by 100 in code. `NULL`/blank → treated as 0 (no uplift) |
| `FirstBase` | — | base marker; **hard‑coded `'P1'` on insert** (Q‑PRICE‑074). Meaning otherwise `UNKNOWN` |
| `EffectiveDate` | — | effective date; latest ≤ target date wins (`ORDER BY EffectiveDate DESC`) |

### `PriceMatrix` — maps product‑line price code × customer price code → formula
| Column | Meaning |
|---|---|
| `ItemPriceCode` | matches `Product_Code.PriceCode` (product‑line price band) |
| `CustPriceCode` | matches `Currency.PriceCode` (customer/currency price band) |
| `PriceFormula` | formula name → `PriceFormula.PriceFormula` |
| `Rounding` | rounding mode passed to `fnGetListPrice` |

### `Currency`
| Column | Meaning |
|---|---|
| `Currency_ID` | PK |
| `Currency` | ISO‑like code (`GBP`, `EUR`, `USD`) — matches `PriceFormula.DomCurrCode` |
| `Description`, `Symbol` | display |
| `PriceCode` | joins `PriceMatrix.CustPriceCode`; value `'OGC'` is filtered out in Financial (`WHERE Currency.PriceCode <> 'OGC'`, `FinancialMaintenance.cs:1814`) |

### `ExchangeRate`
| Column | Meaning |
|---|---|
| `DomCurrCode` | domestic currency |
| `CurrCode` | foreign currency |
| `BuyRate` | conversion rate; `1.0` means no conversion applied |
| `EffectiveDate` | latest ≤ target date wins |

### `Item` (price‑relevant columns)
| Column | Meaning |
|---|---|
| `ItemId`, `Item` | PK / code |
| `BasePrice`, `BasePrice2`, `BasePrice3` | **three base‑price slots**; active slot chosen by `Product_Code.BasePriceRef` |
| `ListPrice` | stored list price (updated when `display_selector = 1`) |
| `BasePriceRef` (via `Product_Code`) | 1→`BasePrice`, 2→`BasePrice2`, 3→`BasePrice3` |
| `Notes` | encodes variant **prefix length** for pCon splitting (integer ≤ 20, optional comma suffix) |
| `IsSuperItem` | 1 = super item, always in scope regardless of catalogue |
| `ProductCodeIdOverride` | item‑level product‑code override; takes precedence over `Product.ProductCodeId` |
| `Status` | 1 = active (filtered in article discovery) |

### `ItemOptionValues` — per‑item incremental prices
| Column | Meaning |
|---|---|
| `ItemId`, `OptionValueId` | composite key |
| `IncrementalPrice`, `IncrementalPrice2`, `IncrementalPrice3` | three inc‑price slots, matching base slots (chosen by `BasePriceRef`) |

### `Product_Code`
| Column | Meaning |
|---|---|
| `ProductCodeId`, `Product_Code` | PK / code |
| `PriceCode` | → `PriceMatrix.ItemPriceCode` |
| `SiteId` | per‑site product code |
| `BasePriceRef` | selects base/inc slot (1/2/3) |
| `Status` | 1 = active |

### `Site`
| Column | Meaning |
|---|---|
| `SiteId`, `Site`, `Description` | identity |
| `DomCurrCode` | site’s domestic currency (drives exchange decision) |
| `SiteId = 20` | virtual/aggregate site, **excluded everywhere**; on export it is remapped to 1 (`ItemPriceExport.cs:78`) |

### `FabricBands` — band pricing for fabric options
`OptionValueId`, `PriceBand`, `Application` (= "app band"). Fabric option values are grouped into bands; band determines inc price.

### US shadow tables
`USItem`, `USItemOptionValues`, `USOptionValue`, `USOptionValue.OrderCodeValue`, `USItemOptInc` — parallel structures used when the selected category is a US category (Q‑PRICE‑005). Same slot semantics.

### pCon MDB tables (Jet OLE DB, external `pcr_data_com_ocd.mdb`)
`tCOMd_Price` (`com_PriceID`, `com_ArticleID`, `com_PriceValue`, `com_VariantCondition`, `com_PriceLevelCode` [`'B'`=base], `com_PriceListID`, `com_PriceValidFrom/To`), `tCOMd_GlobalPrice` (`com_GlobalPriceID`, `com_PackageID`, `com_PriceValue`, `com_VariantCondition`), `tCOMd_Article` (`com_ArticleID`, `com_ArticleCode`, `com_PackageID`), `tCOMd_Package` (`com_PackageID`, `reg_ProgramCode`), `tCOMd_PriceList2` (`com_PriceListID`, `com_PriceListLabel`, `sys_ISOCurrencyCode`, `com_PriceValidFrom/To`). Price‑list label `'default'` is excluded from selectors (`PConPriceUpdate.cs:1661`).

### Audit tables (`PDMAudit` database)
`Transactions` (`TransactionId`, `UserName`, `TransactionDate`, `DatabaseEffected`), `ItemPriceUpdates` (base before/after), `IncrementalPriceUpdates` (inc before/after), `PFUpdates` (price‑formula before/after). Audit is **skipped entirely when `Global.connectedServer` contains `eoscloud`** (BR‑PRICE‑062).

### `ocdPrice` (DTO, not a table)
Fields: `articleID, variantCondition, type, level, rule, textID, priceValue, fixValue, currency, dateFrom, dateTo`; `fileName = "ocd_price"`; serialized via `getAllProperties()` for OCD export (module 21).

---

## 6. Business Rules

### Price calculation (the critical maths — quoted exactly)

- **BR-PRICE-030 — Reverse‑uplift (list → base).** `getBasePrice` (`PriceMaintenance.cs:6040`) computes, in order:
  1. Look up the site’s domestic currency (Q‑PRICE‑030).
  2. **If** the input `currency` ≠ site domestic currency: read `BuyRate` (Q‑PRICE‑031); `if (num != 1.0) listprice /= num;` — i.e. convert to domestic currency by **dividing** by the buy rate. (`BuyRate = 1.0` → no conversion.)
  3. Read the uplift: `num2 = FirstPrice / 100.0` (Q‑PRICE‑032); when no formula found `num2 = 0`.
  4. Final: `result = (num2 == 0.0) ? listprice : (listprice / (1.0 + num2));`

  Combined formula (verbatim semantics):
  $$\text{BasePrice} = \frac{\text{ListPrice} / \text{BuyRate}}{1 + (\text{FirstPrice}/100)}$$
  Order of operations is exactly: currency division **first**, then divide by `(1 + FirstPrice/100)`. No rounding is applied inside `getBasePrice` (returns a raw `double`).

- **BR-PRICE-031 — Forward uplift is DB‑side.** The forward direction (base → list) is delegated to `dbo.fnGetListPrice(currency, base, itemPriceCode, effDate, 'DMY', rounding, siteId, custPriceCodeOverride)` and `dbo.fnGetListPriceByItem(item, currency, effDate, siteId, NULL)`. Their internal formula/rounding is `UNKNOWN` from this source set but is the inverse of BR‑PRICE‑030 (apply `+FirstPrice%`, then apply `Rounding`, then convert by exchange).

- **BR-PRICE-032 — Rounding override for `zz-zz`.** In `getListPrice` (`:4600`): `if (productcode_label.Text.ToLower() == "zz-zz") rounding = 2;` — a hard‑coded product‑code special case forcing rounding mode 2.

- **BR-PRICE-033 — Base‑slot selection.** The base/inc slot is chosen by `Product_Code.BasePriceRef`: `1 → BasePrice/IncrementalPrice`, `2 → BasePrice2/IncrementalPrice2`, `3 → BasePrice3/IncrementalPrice3`. Any other value → invalid (grid shows `-1 AS [Invalid Increment]`, `IncPriceThread`).

- **BR-PRICE-034 — Slot‑2 is the US/Mexico base slot.** `UpdatePricesThread` and the `us_`/`mexico_` import paths always write **slot 2** (`BasePrice2` / `IncrementalPrice2`), independent of `BasePriceRef` (`PriceMaintenance.cs:3315`, `UpdatePricesThread.cs:258`,`:447`).

- **BR-PRICE-035 — Fabric options priced by band.** For `IsFabric` values, inc price is resolved through `FabricBands.PriceBand` + `Application`, not per individual value (Q‑PRICE‑060, `IncPriceThread`). Fabric type = `IsFabric 1`, fabric colour = `IsFabric 2`, non‑fabric = `0`.

- **BR-PRICE-036 — CustomPricePerm permutation maths** (`CustomPricePerm.cs`, orphaned — see §7). For each option‑value permutation row:
  - **GBP** (`getPriceLineGBPandEUR`): each option inc `row[n]` is upifted: `value = row[n] * ((100 + d2)/100)` where `d2` = the item’s GBP `FirstPrice`; summed; plus the uplifted base `num2 * ((100 + d2)/100)`. Result cast to `int`.
  - **EUR**: sum the **raw** incs `num23 = Σ row[n]`, add EUR base `num`, then `num26 = (num19 * ((100 + d)/100)) * euroExchange` where `d` = EUR `FirstPrice` and `euroExchange` = GBP→EUR `BuyRate` (Q‑PRICE‑098). Result cast to `int`.
  - Base‑slot variant `getLine` uses `CASE WHEN BasePriceRef = 1 THEN Item.BasePrice WHEN 2 THEN BasePrice2 WHEN 3 THEN BasePrice3 END` and `IncrementalPrice[n]` accordingly.

### Filtering / scope

- **BR-PRICE-010 — Site 20 excluded.** `WHERE SiteId NOT IN (20)` in every site query; on export site 20 → 1.
- **BR-PRICE-011 — Product‑code override precedence.** `CASE WHEN Item.ProductCodeIdOverride IS NOT NULL THEN Item.ProductCodeIdOverride ELSE Product.ProductCodeId END` (Q‑PRICE‑020).
- **BR-PRICE-012 — Catalogue scope.** Items filtered to `CatalogueItems` ∪ `CatalogueItemsUnreleased` for the selected catalogue ∪ `IsSuperItem = 1`.
- **BR-PRICE-013 — Newest effective record wins.** `ORDER BY EffectiveDate DESC` for both `PriceFormula` and `ExchangeRate`; the calculation uses `EffectiveDate <= target` (or `DATEDIFF(DAY, …) >= 0`).
- **BR-PRICE-014 — Catalogue 81 = all‑items scope.** When the selected catalogue id = **81** ("Spares & Parts"), the catalogue restriction is dropped and the update applies to all items. Explicitly surfaced in UI text ("Select the 'Spares & Parts' catalogue … to extend the update scope to all items").
- **BR-PRICE-015 — US category routing.** `ProductCategory.USCategory = 1` (Q‑PRICE‑005) routes reads/writes to `US*` tables; otherwise the main `Item`/`ItemOptionValues` tables.
- **BR-PRICE-016 — Currency `OGC` excluded** from the Financial currency list (`Currency.PriceCode <> 'OGC'`).
- **BR-PRICE-017 — pCon price list `default` excluded** from selection; `_` in a price‑list label is translated to SQL `%` wildcard when matching (`pricelist.Replace("_","%")`).

### File / import validation

- **BR-PRICE-020 — Base CSV format** = `[item],[list_price]`; only rows where the value passes `isNumericalValue` are accepted (`PriceMaintenance.cs:3128`).
- **BR-PRICE-021 — Inc CSV format** = `[item],[option_display_order OR option_id],[option_order_code],[incremental_list_price]`; requires value 1 & 4 numeric and value 3 non‑empty.
- **BR-PRICE-022 — Filename prefix drives target.** `us_`‑prefixed file → US base slot‑2 update (site Singapore + USD enforced); `mexico_`‑prefixed → Mexico slot‑2 (site Mexico + USD enforced, items get `mexico_` prefix to avoid clobbering USD).
- **BR-PRICE-023 — display_selector meaning.** `0` = update **BasePrice** (reverse‑uplift applied via `getBasePrice`); `1` = update **ListPrice** directly (no reverse uplift; currency shown).
- **BR-PRICE-024 — SQL length guard.** When the generated count SQL exceeds **100 000** chars it is split at the next `" OR "` boundary and run in two parts (`PriceMaintenance.cs:3560`).
- **BR-PRICE-025 — Order‑code match is case/`#`‑insensitive.** Inc import matches order codes via `ToLower().Replace("#","")` on both sides; also accepts a trailing `#` variant in US lookups.
- **BR-PRICE-026 — Ambiguity rejection.** If an option code resolves to more than one option value (`num12 > 1` / `num10 > 1`) the row is rejected with "unable to find unique optval".
- **BR-PRICE-027 — Option position vs id.** Inc import matches on `OptionId` **or** `DisplayOrder`, but the `DisplayOrder` match is disallowed when the supplied position equals `8` (`… CompareObjectNotEqual(arrayList6[j], 8) …`) — a hard‑coded exclusion.

### Duplicate / null / no‑op

- **BR-PRICE-040 — No‑op skip (base).** If the new value equals the existing slot value (or both are effectively zero/NULL) the update is skipped and counted as "unchanged" (`updateItemBasePrice`, `flag = true`).
- **BR-PRICE-041 — Zero → NULL.** A supplied `"0"` is converted to `NULL` before writing (`if (basestr == "0") basestr = "NULL"`), for both base and inc prices.
- **BR-PRICE-042 — NULL inc insert skipped.** When no `ItemOptionValues` row exists and the new inc price is `NULL`, no row is inserted (`updateItemOptIncPrice`, `flag = true`).
- **BR-PRICE-043 — Empty‑row cleanup.** Rows with all three inc slots NULL are deleted (Q‑PRICE‑097).

### Read‑only / permissions

- **BR-PRICE-050 — Catalogue read‑only flag.** `PDMUserCatalogues.ReadOnly` (`puc.ReadOnly`) accompanies each catalogue (Q‑PRICE‑003); per the inverted convention documented in `02_User_Permissions.md`, it gates editability. (Enforcement in UI event handlers; exact per‑control gating `UNKNOWN` beyond the flag being loaded.)
- **BR-PRICE-051 — `ReadOnlyFinancial`.** A distinct permission flag (`AuthenticateUser.ReadOnlyFinancial`, `AuthenticateUser.cs:67`) that (with `ExchangeRates`, `SiteMaintenance`, `CurrencyMaintenance`, `ProductCodeMaintenance`, `FormulaMaintenance`) governs visibility of the financial/static maintenance menu group (`MainMenu.cs:3054`).
- **BR-PRICE-052 — Financial form entry is right‑click‑gated.** `FinancialMaintenance` opens only on **right‑click** of the Static Maintenance button; left‑click opens `StaticDataMaintenance` (`MainMenu.cs:2867`).
- **BR-PRICE-053 — `FormulaMaintenance`** flag gates price‑formula editing surfaces in `StaticDataMaintenance` (`:2187`, `:3187`, `:3266`, `:3335`, `:3351`).
- **BR-PRICE-054 — `PriceMaintenance` / `CurrencyMaintenance` / `ExchangeRates`** are independent boolean privileges loaded from `PDMUserPrivileges` (`AuthenticateUser.cs:100/106/110`).

### Audit

- **BR-PRICE-060 — Every changed base price is audited.** `Transactions` header + `ItemPriceUpdates` before/after row written before the `UPDATE Item` (Q‑PRICE‑041/042).
- **BR-PRICE-061 — Every PriceFormula insert/update/delete is audited** into `PDMAudit.dbo.PFUpdates` with `Prev*` columns (Q‑PRICE‑073).
- **BR-PRICE-062 — Audit disabled on `eoscloud`.** All audit inserts are skipped when `Global.connectedServer.ToLower().IndexOf("eoscloud") == -1` is false (i.e. audit only runs off‑cloud). On non‑eoscloud, `updateItemBasePrice` opens a **second, separate** hard‑coded connection to the `PDMAudit` database (`Persist Security Info=False;Integrated Security=SSPI;database=PDMAudit;server=<connectedServer>;`).

### Defaults / hardcoded

- **BR-PRICE-070 — `FirstBase` default `'P1'`** on every new PriceFormula (Q‑PRICE‑074).
- **BR-PRICE-071 — Default currency = 1.** `AuthenticateUser.DefaultCurrencyId = 1` (GBP by id).
- **BR-PRICE-072 — Hard‑coded pCon date/currency gate (defeated).** `showPConButtons` builds a gate (dates `07-Jan-2019`/`04-Jun-2019`/`06-Jan-2020`/`05-Jan-2021`, site 1, `CADMaintenance` privilege, EUR/GBP) but then **unconditionally sets `result = true;`** on the next line — the gate is dead; the button is always shown. (§7)
- **BR-PRICE-073 — Special item prefixes.** `UpdatePConItemPrice` special‑cases `RBK123.06`, `RBK173.06`, `RBK212.06`, `RBK262.06`, `RBK313.06`, `RBK322.06`, `RBK363.06`, `RBK372.06` (article = `%` + first 6 chars). `DWEV`‑prefixed items derive a width from chars 5‑6.
- **BR-PRICE-074 — CustomPricePerm hard‑coded ids.** Catalogue 4 (GBP/EUR seating), catalogue 30 (Singapore/USD); `AE`‑prefixed items exclude option values `292, 299, 300, 253, 254, 262`; option‑group array sized `[51]` (max 50 options) and permutation column array `[1001]` (`CustomPricePerm.cs`).

### Edge cases / error handling

- **BR-PRICE-080 — Missing‑link diagnostics.** `validateProductLineCode` and the importers emit specific messages for each missing join: no product line code, no `PriceMatrix` entry, no `PriceFormula` factor — including a note that a missing formula "may be intentional (a zero uplift on the base price in the domestic currency for a newly introduced product line)".
- **BR-PRICE-081 — `getLine` guards.** Returns false (skips item) if base price is DBNull **or negative** (`BasePrice < 0`) or no price row found (`CustomPricePerm.cs`).
- **BR-PRICE-082 — Prefix length cap.** Item `Notes` prefix length is only honoured when `≤ 20` (`UpdatePriceThread.cs:161`).
- **BR-PRICE-083 — Errors surface via MsgBox / debug_form.** Most catch blocks show `Interaction.MsgBox` or a `debug_form`; exceptions do not roll back already‑committed audit/price rows (no transactions used).

---

## 7. Hidden Logic

- **CustomPricePerm is dead / orphaned code.** The class is never instantiated anywhere in the solution (only its own constructor at `CustomPricePerm.cs:650` and class decl reference it). Its GBP/EUR/USD price‑permutation exports (`ExecuteSeating`, `getPriceLineGBPandEUR`, `getLine`, `SingaporeExecute`) — including the entire BR‑PRICE‑036 maths — are unreachable from the running app. Documented for completeness only.
- **`showPConButtons` gate is defeated** (BR‑PRICE‑072): an elaborate conditional is computed then immediately overwritten by `result = true;`. Effect: the "Update pCon Prices" button is always visible.
- **Audit path forks on server name** (BR‑PRICE‑062): the presence of the substring `eoscloud` in the connected server name silently disables all price auditing and changes which database connection is used.
- **`getBasePrice` reuse across modules.** `SIFImport.cs:9009`/`:9499` call the **public static** `PriceMaintenance.getBasePrice` to reverse‑uplift SIF‑imported inc/base prices — the pricing maths leaks into the import module.
- **Malformed but tolerated SQL.** `CustomPricePerm` Q‑PRICE‑099 uses `INNER JOIN ItemComponents INNER JOIN Item ON …` (unusual bracket‑free chained join order) and column `ItemPRiceCode` (odd casing); preserved verbatim. Because the form is dead this never executes.
- **`display_selector` silently changes semantics** (BR‑PRICE‑023): the same import button either reverse‑upifts to a base price or writes a raw list price depending on a combobox index — with no separate confirmation of which table column is targeted beyond message text.
- **Hidden right‑click on pCon button** (`_button_update_pcon_MouseDown`): a right‑click branch (`populateMissingPConIncrements()`) exists but is guarded by `((e.Button == MouseButtons.Right ? 1u : 0u) & 0u) != 0` — i.e. `& 0` makes it **always false**; the right‑click feature is effectively disabled (dead branch).
- **Note‑field overloading.** `Item.Notes` doubles as a numeric variant‑prefix length for pCon (comma‑delimited), an implicit data contract not enforced by schema.

---

## 8. UI Behaviour

- **PriceMaintenance** presents up to **16 data grids** (`DataGrid1..16`) plus selectors: site, currency, catalogue, category, display (`display_selector`: 0=base, 1=list), and an effective‑date picker (`EffDatePicker`) + a projected‑date picker (`projected_picker`).
- Grid population is **threaded** (`IncPriceThread`, `SqlDataAdapter.Fill`) with `CommandTimeout = 300` (5 min) to tolerate slow fabric‑band permutation queries.
- Import flows are **multi‑confirm**: format‑preview MsgBox → count MsgBox → final confirm, before any write. Exception lists (>10) are copied to the clipboard.
- Long imports run on a background thread (`UpdatePricesThread`) with `lockControls()` disabling the form; status text updates via events.
- **FinancialMaintenance** is a list/edit grid for `PriceFormula` with Insert / Insert‑and‑next / Delete buttons and an Excel update path; delete requires an OK/Cancel confirmation quoting the selected count.
- **PConPriceUpdate** offers "Update Article Pricing (and Upcharges)" and "Update Global Pricing (and Upcharges)" buttons; global update asks Yes(selected)/No(all)/Cancel.
- **Cursor** switches to `WaitCursor` during synchronous DB work; error UI is either a `MsgBox` or a scrollable `debug_form`.

---

## 9. Dependencies

- **`ConnectionFactory`** — all SQL connections; plus a **second hard‑coded `SqlConnection`** to `PDMAudit` in `updateItemBasePrice`/`updateItemOptIncPrice`.
- **`AuthenticateUser`** — privilege flags (`PriceMaintenance`, `CurrencyMaintenance`, `ExchangeRates`, `ReadOnlyFinancial`, `FormulaMaintenance`, `CADMaintenance`, `PDMAdministrator`), `DefaultCurrencyId`.
- **`Global`** — `connectedServer`, `connectedDB` (audit routing / eoscloud fork).
- **`CADMaintenance.pConPath`** — filesystem path to the pCon workspace MDBs.
- **DB functions** `fnGetListPrice`, `fnGetListPriceByItem`, `fnGetFabricBandOrderCodes`; **stored procs** `PricePermutation`, `PDMOptionDataReport`, `PDMOptionDataReportWithIncList`.
- **Jet / OLE DB** (`Microsoft.Jet.OLEDB.4.0`) for the pCon `pcr_data_com_ocd.mdb` files (32‑bit dependency).
- **Cross‑module:** `SIFImport` (reuses `getBasePrice`), `OFDAExport`/`SytelineExport`/`ClippingsExport`/`CADMaintenance` (consume `fnGetListPrice*`), `ItemPriceExport` (uses `PDMOptionDataReportWithIncList`), module 21 OCD (`ocdPrice`).
- **Tables:** `PriceFormula`, `PriceMatrix`, `Currency`, `ExchangeRate`, `Site`, `Item`, `ItemOptionValues`, `Product`, `Product_Code`, `ProductCategory`, `ProductRange`, `Catalogue`, `CatalogueItems`, `CatalogueItemsUnreleased`, `CatalogueOptionValues`, `FabricBands`, `DependentOptionValues`, `[Option]`, `OptionValue`, `US*` shadow set; `PDMAudit` (`Transactions`, `ItemPriceUpdates`, `IncrementalPriceUpdates`, `PFUpdates`); pCon `tCOMd_*`.

---

## 10. Risks

1. **SQL injection everywhere** (`BR-PRICE-100`): item codes, order codes, currency/site selector text and CSV values are concatenated straight into SQL and OLE DB commands. A crafted item code or CSV entry can alter/destroy data. **High.**
2. **No transactions.** Audit rows, base/inc updates, and multi‑part length‑split queries are separate statements; a mid‑run failure leaves audit and data inconsistent (audit written but price not, or vice versa).
3. **Reverse‑uplift precision.** `getBasePrice` returns a raw `double` with no rounding; repeated list↔base round‑trips accumulate floating error, and CustomPricePerm casts results to `int` (truncation). Base prices can drift.
4. **Slot ambiguity.** Three base/inc slots keyed off `BasePriceRef`, but the US/Mexico paths always hit slot 2 regardless — a misconfigured `BasePriceRef` silently prices from the wrong slot with no validation.
5. **Defeated gate + always‑on pCon button** (BR‑PRICE‑072) means the external pCon MDB can be overwritten at any date/site/currency by any user with `CADMaintenance` — writes go to a shared file via Jet with no locking beyond `_button_update_pcon.Enabled`.
6. **Audit fork on server‑name substring** (`eoscloud`): auditing silently disappears in cloud deployments; the hard‑coded off‑cloud `PDMAudit` connection string uses `Integrated Security=SSPI` and assumes a co‑located `PDMAudit` DB.
7. **Jet/OLE DB 32‑bit dependency** for pCon: requires a 32‑bit process and the legacy `Microsoft.Jet.OLEDB.4.0` provider; a migration blocker.
8. **Magic numbers** (catalogue 81, site 20, category `USCategory`, option position `8`, ids `292/299/300/253/254/262`, RBK/DWEV item lists) are hard‑coded in logic — fragile, undocumented business assumptions.
9. **DB‑side pricing formula (`fnGetListPrice*`) is invisible here** — the forward uplift + rounding rules must be recovered from SQL before any re‑implementation; behaviour is `UNKNOWN` from application source.
10. **Dead code carrying business logic** (`CustomPricePerm`, orphaned; right‑click `populateMissingPConIncrements` unreachable) risks being mistaken for live rules during migration.
```