# 24 — Utilities

**Module prefix:** BR-UTIL
**Primary legacy source:** `StaticDataMaintenance.cs` (~5245); shared helper classes: `ApplicationText.cs`, `InputForm.cs`, `EditDialog.cs`, `AddDataList.cs`, `AddNewData.cs`, `ProgressThread.cs`, `DelayThread.cs`, `TimerThread.cs`, `debug_form.cs`, `MDBQuery.cs`. Related: `MainMenu.cs` (launch + gate), `AuthenticateUser.cs`, `Global.cs`, `ConnectionFactory.cs`, `SDXmlExport.cs`.
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

Two concerns:

1. **Reference / static data maintenance** — `StaticDataMaintenance` (form caption **"Financial Data Maintenance"**) is a 7‑tab grid editor for the app's foundational lookup tables: **Currency, Site, Exchange Rate, Language, Product Code, Price Formula, Price Matrix**. Each tab is a `DataGrid` bound to a `SqlDataAdapter` with hand‑written `Select/Insert/Update` commands; edits are committed on **Update**. Which tabs appear (and whether they are editable) is driven by financial‑permission flags.
2. **Shared helper dialogs & threads** — small reusable UI/worker classes used across the whole application: input/edit dialogs (`InputForm`, `EditDialog`, `ApplicationText`), generic list pickers (`AddDataList`, `AddNewData`), background/worker threads (`ProgressThread`, `DelayThread`, `TimerThread`), a generic text output window (`debug_form`), and the pCon Access‑MDB query tool (`MDBQuery`).

---

## 2. Entry Points

| Entry point | Trigger | Source |
|---|---|---|
| `new StaticDataMaintenance()` → shown | MainMenu **Static / Financial Data Maintenance** button | `MainMenu.cs:2876`; gate `MainMenu.cs:3054` |
| `StaticDataMaintenance` Load | Builds grids, sets SQL, removes tabs per permission | `StaticDataMaintenance.cs` Load (~1990‑2210) |
| `updateButton_Click` | Commit grid edits to DB (+ audit) | `StaticDataMaintenance.cs:3555` |
| `ApplyFactors_Click` / `CalculateFactors` | Recalculate Price Formula `FirstPrice` from exchange rates or a % | `StaticDataMaintenance.cs:3434 / 3402` |
| `exportButton_Click` → `SDXmlExport` | Export static data to XML (module 22) | `StaticDataMaintenance.cs:4851` |
| `ImportStaticData` (importButton) | Import static data from CSV | `StaticDataMaintenance.cs:2158` (wired), body ~4170+ |
| `PLCFilterButton_Click`, filter combos | Filter grids (by DomCurrCode, PLC, price code) | `StaticDataMaintenance.cs:2214` etc. |
| Helper dialogs (`InputForm`, `EditDialog`, `ApplicationText`, `AddDataList`, `AddNewData`) | Instantiated on demand by many forms | see §6 sub‑sections |
| Worker threads (`ProgressThread`, `DelayThread`, `TimerThread`, `MDBQuery`) | Started by their owning forms | see §6 sub‑sections |

**Menu gate (Q‑UTIL guard)** — the button is enabled only if the user holds at least one financial privilege (`MainMenu.cs:3054`):
```
AuthenticateUser.ExchangeRates | AuthenticateUser.ReadOnlyFinancial | AuthenticateUser.SiteMaintenance
| AuthenticateUser.CurrencyMaintenance | AuthenticateUser.ProductCodeMaintenance | AuthenticateUser.FormulaMaintenance
```

---

## 3. Call Hierarchy

```
MainMenu (StaticMaintenance button, gated)
  └─ new StaticDataMaintenance()
       ├─ SetSQL()                       // builds Select/Insert/Update per entity
       ├─ AuthenticateUser.setUserPrivileges(Environment.UserName.ToLower())
       ├─ tab removal by permission (BR-UTIL-020..024)
       ├─ updateDataGrid() / fillgridN() // load active tab into DataGrid
       ├─ updateButton_Click
       │     ├─ SqlDataAdapter.Update(...)         // Currency/Site/Lang/ExRate/PriceMatrix/ProductCode
       │     └─ PriceFormula path: PDMAudit Transactions + PFUpdates, INSERT new / DELETE old formula
       ├─ ApplyFactors_Click → CalculateFactors → getExRate(...)   // recompute FirstPrice
       ├─ exportButton_Click → SDXmlExport (static data XML)
       └─ ImportStaticData (CSV → grids)

Shared helpers (used app-wide):
  InputForm         → commodity/HS code entry (validation)
  EditDialog        → single value edit
  ApplicationText   → read-only application text + image
  AddDataList       → multi/single select list (context-driven SQL)
  AddNewData        → add fabrics/options/product group codes (may INSERT)
  ProgressThread    → xp_cmdshell dtsrun (DPS DB export) for ExportDPSDBThread
  DelayThread       → 500ms debounce for CADMaintenance category filter
  TimerThread       → elapsed HH:MM:SS label
  debug_form        → generic scrollable text output
  MDBQuery          → pCon Jet/Access MDB query & "find"
```

---

## 4. SQL Analysis

All commands below are in `StaticDataMaintenance.cs`. `Select/Insert/Update` per entity are configured in `SetSQL()` (~1800‑2040). These use **parameterised** `SqlCommand`s (`@Param` + `@Original_*` optimistic‑concurrency checks) — a marked contrast to the string‑concat SQL elsewhere in the app. Ad‑hoc filter/helper queries (further down) are string‑concatenated.

### Currency (tab "Currency")

**Q-UTIL-001** (`:1802`)
```sql
SELECT Currency_ID, Currency, PriceCode, DecimalPlaces, Description, Symbol FROM Currency ORDER BY Currency_ID
```
*WHY:* Load the currency list for editing.

**Q-UTIL-002** (`:1804`)
```sql
INSERT INTO Currency (Currency, PriceCode, DecimalPlaces, Description, Symbol)
VALUES (@Currency, @PriceCode, @DecimalPlaces, @Description, @Symbol);
SELECT Currency_ID, Currency, PriceCode, DecimalPlaces, Description, Symbol FROM Currency WHERE (Currency_ID = @@IDENTITY)
```
*WHY:* Insert a new currency and re‑read it (identity round‑trip to refresh the grid row).

**Q-UTIL-003** (`:1811`) — `UPDATE Currency SET … WHERE Currency_ID = @Original_Currency_ID AND (original‑value checks) …` *WHY:* Optimistic‑concurrency update of a currency.

### Site (tab "Site")

**Q-UTIL-004** (`:1833`)
```sql
SELECT SiteId, Description, Site, DomCurrCode FROM Site WHERE SiteId NOT IN (20) ORDER BY SiteId
```
*WHY:* Load editable sites. **SiteId 20 is excluded** (reserved/special site, hidden from maintenance).

**Q-UTIL-005** (`:1835`) `INSERT INTO Site(Description, Site, DomCurrCode) … ; SELECT … WHERE SiteId = @@IDENTITY` — insert + refresh.
**Q-UTIL-006** (`:1840`) `UPDATE Site SET … WHERE SiteId = @Original_SiteId AND (original checks)` — concurrency‑guarded update.

### Exchange Rate (tab "Exchange Rate")

**Q-UTIL-007** (`:1858`) `SELECT ExchangeRateId, CurrCode, EffectiveDate, BuyRate, SellRate, UserCode, DomCurrCode FROM dbo.ExchangeRate ORDER BY DomCurrCode` — flat list.

**Q-UTIL-008** (`:1860`, the actually‑used latest‑rate view)
```sql
SELECT ExchangeRate.CurrCode, ExchangeRate.DomCurrCode, ExchangeRate.EffectiveDate, ExchangeRate.BuyRate,
       ExchangeRate.SellRate, ExchangeRate.ExchangeRateId
FROM ExchangeRate
INNER JOIN (SELECT CurrCode, DomCurrCode, MAX(EffectiveDate) AS ED FROM ExchangeRate GROUP BY CurrCode, DomCurrCode) D
  ON D.CurrCode = ExchangeRate.CurrCode AND D.DomCurrCode = ExchangeRate.DomCurrCode AND D.ED = ExchangeRate.EffectiveDate
ORDER BY ExchangeRate.DomCurrCode, ExchangeRate.EffectiveDate DESC
```
*WHY:* Show only the **latest** (max `EffectiveDate`) rate per (CurrCode, DomCurrCode) pair.

**Q-UTIL-009** (`:1861`) insert exchange rate + identity refresh; **Q-UTIL-010** (`:1869`) concurrency‑guarded update.

**Q-UTIL-011** (`:2813` / `:2851`) — deliberate empty‑result trick:
```sql
SELECT … FROM dbo.ExchangeRate WHERE DomCurrCode = 'abcx' ORDER BY DomCurrCode
```
*WHY:* `'abcx'` is a sentinel that matches nothing — used to blank the grid before applying a real filter. (Same pattern for Price Formula, Q‑UTIL‑018.)

**Q-UTIL-012** (`getExRate`, `:3374`)
```sql
SELECT BuyRate, EffectiveDate FROM ExchangeRate
WHERE (DomCurrCode = '<dcc>') AND (CurrCode = '<cc>') AND (EffectiveDate >= '<OldDate>') ORDER BY EffectiveDate DESC
```
*WHY:* Fetch the effective `BuyRate` (first row ≤ `NewDate`) used by `CalculateFactors` to re‑derive formulas. **String‑concatenated** (injection surface, though inputs are internal codes/dates).

### Language (tab "Language")

**Q-UTIL-013** (`:1893`) `SELECT Language_ID, Language, CultureCode FROM Language ORDER BY Language_ID`.
**Q-UTIL-014** (`:1895`) insert + identity refresh; **Q-UTIL-015** (`:1899`) concurrency update.

### Product Code (tab "Product Code")

**Q-UTIL-016** (`:1915`)
```sql
SELECT Product_Code.ProductCodeId, Product_Code.Product_Code, Product_Code.Description, Product_Code.PriceCode,
       Product_Code.UnitCode, Product_Code.BasePriceRef, Product_Code.Truncation, Product_Code.InterCompanyDisc,
       Product_Code.OCDExport, /*Product_Code.Rounding,*/ Product_Code.GroupCode, Site.Description as SiteDesc, Product_Code.SiteId
FROM Product_Code INNER JOIN Site ON Product_Code.SiteId = Site.SiteId
ORDER BY SiteDesc, Product_Code
```
*WHY:* Load product codes joined to their site. Note `Rounding` is commented out of the projection (schema drift).

**Q-UTIL-017** (`:1917`) insert product code; (`:1930`) update product code — the update `LTRIM(RTRIM(REPLACE(...)))`‑normalises `Product_Code` server‑side. Filtered variants at `:2942`/`:2950` add `WHERE SiteId = …` and active flags. Max‑id helper `SELECT MAX(ProductCodeId) AS MaxCode FROM dbo.Product_Code` (`:3635`) and existence check by `Product_Code` (`:3646`).

### Price Formula (tab "Price Formula")

**Q-UTIL-018** (`:1962` / filtered `:3122`, `:3161`)
```sql
SELECT PriceFormulaId, SiteId, DomCurrCode, EffectiveDate, FirstBase, FirstPrice, PriceFormula FROM dbo.PriceFormula
```
*WHY:* Load formulas (with `WHERE DomCurrCode='abcx'` blanking / `WHERE SiteId=…` filtering variants).

**Q-UTIL-019** (`:1964` / `:2027`) insert formula + identity refresh; (`:1972` / `:2037`) concurrency update.

**Q-UTIL-020** — audit + replace on formula change (`updateButton_Click`, `:3743`‑`:3855`):
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected)
  VALUES ('<user>', GetUTCDate(), '<connectedDB>');
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '<user>' ORDER BY TransactionId DESC;
INSERT INTO PDMAudit.dbo.PFUpdates (SiteId, DomCurrCode, EffectiveDate, FirstBase, FirstPrice, PriceFormula, …) VALUES (…);
SELECT PriceFormulaId FROM PriceFormula WHERE SiteId = … AND DomCurrCode = '…' AND EffectiveDate = '…' AND FirstBase = '…' AND FirstPrice = … AND PriceFormula = '…';
DELETE FROM PriceFormula WHERE PriceFormulaId = '<old>'
```
*WHY:* Price‑formula edits are audited (a `Transactions` header + one `PFUpdates` row per change) and applied as **insert‑new + delete‑old** rather than in‑place update, preserving history. All string‑concatenated.

### Price Matrix (tab "Price Matrix")

**Q-UTIL-021** (`:1996` / filtered `:3294`, `:3298`)
```sql
SELECT PriceMatrixId, CustPriceCode, ItemPriceCode, PriceFormula, Rounding, MidpointRounding FROM dbo.PriceMatrix ORDER BY ItemPriceCode
```
**Q-UTIL-022** (`:1998`) insert matrix row + identity refresh; (`:2005`) concurrency update. Direct upsert path in `DoneButton_Click` (`:4722`‑`:4748`): `SELECT … FROM PriceMatrix WHERE CustPriceCode=… AND ItemPriceCode=…` then `UPDATE` if present else `INSERT`.

### Cross‑cutting lookup / validation queries

- **Q-UTIL-023** (`:2123`, `:3196` etc.) `SELECT DISTINCT DomCurrCode, SiteId FROM Site ORDER BY SiteId` — populate DomCurrCode filter combo.
- **Q-UTIL-024** (`:2490`) `SELECT Currency FROM Currency ORDER BY Currency`; (`:2562`) `SELECT Description, SiteId FROM Site ORDER BY Description`; (`:2580`, `:3313`) `SELECT DISTINCT CustPriceCode FROM PriceMatrix ORDER BY CustPriceCode` — combo population.
- **Q-UTIL-025** (`:4558`) `SELECT PriceCode FROM Currency WHERE PriceCode = '<x>'`; (`:4588`) `SELECT PriceCode FROM Product_Code WHERE PriceCode = '<x>'`; (`:4618`) `SELECT PriceFormula FROM PriceFormula WHERE PriceFormula = '<x>'` — referential validation before saving a Price Matrix row.
- **Q-UTIL-026** (`:3515`, `:4257`) `SELECT … FROM ProductGroupCodes pgc INNER JOIN OtherDescription od ON pgc.DescriptionId = od.DescriptionId AND od.LanguageId = 1 ORDER BY pgc.DisplayOrder …` — product‑group‑code lookups (indent child rows where `ParentGroupCodeId > 0`).

---

## 5. Data Model

Static/reference tables maintained by `StaticDataMaintenance`:

| Entity / Table | Key columns | Permission gate |
|---|---|---|
| **Currency** | `Currency_ID` PK, `Currency`, `PriceCode`, `DecimalPlaces`, `Description`, `Symbol` | `CurrencyMaintenance` |
| **Site** | `SiteId` PK, `Description`, `Site`, `DomCurrCode`; **SiteId 20 excluded** | `SiteMaintenance` |
| **ExchangeRate** | `ExchangeRateId` PK, `CurrCode`, `EffectiveDate`, `BuyRate`, `SellRate`, `UserCode`, `DomCurrCode` | `ExchangeRates` |
| **Language** | `Language_ID` PK, `Language`, `CultureCode` | `CoreMaintenance` (tab only present with Core) |
| **Product_Code** | `ProductCodeId` PK, `SiteId`, `Product_Code`, `Description`, `PriceCode`, `UnitCode`, `BasePriceRef`, `Truncation`, `InterCompanyDisc`, `OCDExport`, `GroupCode`, `Readonly` | `ProductCodeMaintenance` (tab always visible; read‑only without) |
| **PriceFormula** | `PriceFormulaId` PK, `SiteId`, `DomCurrCode`, `EffectiveDate`, `FirstBase`, `FirstPrice`, `PriceFormula` | `FormulaMaintenance` |
| **PriceMatrix** | `PriceMatrixId` PK, `CustPriceCode`, `ItemPriceCode`, `PriceFormula`, `Rounding`, `MidpointRounding` | `FormulaMaintenance` |

Audit tables written: `PDMAudit.dbo.Transactions` (header), `PDMAudit.dbo.PFUpdates` (price‑formula change rows).
Supporting/read tables: `ProductGroupCodes`, `OtherDescription` (group‑code labels).

Tab controls (`StaticDataMaintenance.cs:1389‑1492`): `SiteTab`, `LangTab`, `CurrTab`, `ExRateTab`, `ProdTab` ("Product Code"), `PrFormTab`, `PrMatrixTab`.

Globals used: `Global.readOnlyDBConnection` (adds "(read only)" caption), `Global.connectedDB` (audit `DatabaseEffected`), `Environment.UserName.ToLower()` (audit user + privilege lookup).

---

## 6. Business Rules

### StaticDataMaintenance — form & permissions

- **BR-UTIL-001** — Form caption is "Financial Data Maintenance"; if `Global.readOnlyDBConnection` the caption gets `"   (read only)"` appended. (`:2102‑2106`)
- **BR-UTIL-002** — On load the form recomputes privileges via `AuthenticateUser.setUserPrivileges(Environment.UserName.ToLower())` (Windows account, lower‑cased). (`:2162`)
- **BR-UTIL-003** — The launching **menu button** is enabled only if the user holds any of `ExchangeRates | ReadOnlyFinancial | SiteMaintenance | CurrencyMaintenance | ProductCodeMaintenance | FormulaMaintenance`. (`MainMenu.cs:3054`)
- **BR-UTIL-020** — **ReadOnlyFinancial** path: if `ReadOnlyFinancial` is set, the `Site` and `Language` tabs are removed (the remaining Currency/ExchangeRate/ProductCode/Formula/Matrix tabs are shown for viewing). (`:2163‑2167`)
- **BR-UTIL-021** — Otherwise, if **not** `CoreMaintenance`: remove `CurrTab` unless `CurrencyMaintenance`; remove `SiteTab` unless `SiteMaintenance`; remove `ExRateTab` unless `ExchangeRates`; **always** remove `LangTab`. (`:2170‑2185`)
- **BR-UTIL-022** — `Language` maintenance therefore requires `CoreMaintenance` (there is no dedicated Language privilege; the tab is only kept when the user has Core and is not ReadOnlyFinancial). (`:2185`)
- **BR-UTIL-023** — If **not** `FormulaMaintenance`: remove both `PrFormTab` (Price Formula) **and** `PrMatrixTab` (Price Matrix). Price Formula and Price Matrix are gated by the single `FormulaMaintenance` flag. (`:2187‑2191`)
- **BR-UTIL-024** — The **Product Code** tab (`ProdTab`) is **never removed**; instead, without `ProductCodeMaintenance` the grid is made read‑only: `updateButton.Enabled = false`, `DataGrid2/3.Visible = false`, `TableStyle.ReadOnly = true`, and `DefaultView.AllowNew = false`. With the privilege, `updateButton.Enabled = true`. (`:3033‑3053`)
- **BR-UTIL-025** — Product Code grids never allow row **delete**: `PrimaryDataTable.DefaultView.AllowDelete = false`. (`:3047`)
- **BR-UTIL-026** — Currency edits are additionally gated by `CurrencyMaintenance` inside the currency handlers (`:2383`, `:2399`); Site edits by `SiteMaintenance` (`:2450`, `:2466`, `:2524`, `:2539`); Exchange Rate by `ExchangeRates` (`:2879`, `:2911`); Formula/Matrix by `FormulaMaintenance` (`:3187`, `:3266`, `:3335`, `:3351`). (Defense‑in‑depth: even if a tab is visible, the action re‑checks the flag.)

### StaticDataMaintenance — data behaviour

- **BR-UTIL-030** — Site list hides `SiteId 20` everywhere (`NOT IN (20)`). (Q‑UTIL‑004)
- **BR-UTIL-031** — Exchange Rate grid shows only the latest rate per (CurrCode, DomCurrCode) via the MAX(EffectiveDate) self‑join. (Q‑UTIL‑008)
- **BR-UTIL-032** — `'abcx'` DomCurrCode is a deliberate no‑match sentinel used to clear a grid prior to applying a real filter (Exchange Rate and Price Formula). (Q‑UTIL‑011, `:2813/2851/3122`)
- **BR-UTIL-033** — All entity `Select/Insert/Update` commands are **parameterised** with `@Param` and optimistic‑concurrency `@Original_*` predicates (unusual for this codebase). Insert commands re‑`SELECT … WHERE Id = @@IDENTITY` to refresh the grid row. (`SetSQL`, `:1800‑2040`)
- **BR-UTIL-034** — Price‑formula changes are **audited**: a `PDMAudit.dbo.Transactions` header (UTC date, `Global.connectedDB`) plus one `PDMAudit.dbo.PFUpdates` row per change. (BR shared with module 18.) (`:3743‑3781`)
- **BR-UTIL-035** — A price‑formula change is applied as **insert‑new‑then‑delete‑old** (`INSERT PriceFormula …; SELECT new id; DELETE old id`) rather than in‑place `UPDATE`, keeping the prior formula recoverable/auditable. (`:3810‑3855`)
- **BR-UTIL-036** — `Product_Code` on update is normalised server‑side with `LTRIM(RTRIM(REPLACE(...)))`. `Rounding` is commented out of the Product Code projection (schema drift — column may be unused/removed). (`:1915`, `:1930`)
- **BR-UTIL-037** — `CalculateFactors` recomputes each Price Formula `FirstPrice` from exchange rates: `FirstPrice = ((100 + oldFirstPrice)/CurrCode * BuyRate) * (1 + SellRate/100) - 100`, rounded to 5 dp; a special branch when `CurrCode = "0"` drops the `SellRate` term and yields 0 if `BuyRate = 0`. (`:3402‑3432`)
- **BR-UTIL-038** — `ApplyFactors_Click` has two modes via radio buttons: `FormRadioButton` → `CalculateFactors()` (exchange‑rate recompute); `PriceCodeRadioButton` → `fillgrid5()` applies a flat `PercentNumeric`% uplift and sets `enableUpdatePrForm = true`. `FormRadioButton` is defaulted checked on load. (`:3434‑3450`, `:2196‑2199`)
- **BR-UTIL-039** — Price Matrix save validates references first: the `CustPriceCode` must exist in `Currency.PriceCode`, the `ItemPriceCode` in `Product_Code.PriceCode`, and the `PriceFormula` in `PriceFormula.PriceFormula` (Q‑UTIL‑025) before an `INSERT`/`UPDATE`. (`:4558‑4748`)
- **BR-UTIL-040** — Static data can be exported to XML (`exportButton` → `SDXmlExport`, module 22) and imported from CSV (`importButton` → `ImportStaticData`). `importButton` is created hidden and only surfaced in specific contexts. (`:2154‑2160`, `:4851`)
- **BR-UTIL-041** — Errors throughout are surfaced via `Interaction.MsgBox` (or `Debug.WriteLine` for some diagnostics); connections are closed in `finally`. (`:2202‑2210`, passim)

### Shared helper: ApplicationText.cs

- **BR-UTIL-050** — Read‑only modal `Form` showing a product's **application text** (`app_box`, `ReadOnly`), its description, and a `ProductImage` picture box. `AppText_Focus` immediately moves focus to Close (keeps the box non‑editable); `CloseButton` just `Hide()`s. Purely a display dialog for catalogue/application text. Used where product application text is previewed. (`ApplicationText.cs`)

### Shared helper: InputForm.cs — Commodity / HS code entry

- **BR-UTIL-051** — Dialog for entering a **Commodity Code** (+ optional 8‑digit **HS code**). Constructor `InputForm(sendType, sendCode, sendDesc, sendHSCode="")`; `Type 2` pre‑fills code (edit code), `Type 3` pre‑fills code+description and disables the code box (edit description only). (`InputForm.cs` ctor)
- **BR-UTIL-052** — Validation on submit (`SubmitData`): `Type 1` (category) → code must be **exactly 4 digits** and a positive integer; `Type 2` (item) → code must be **> 4 digits** and a positive integer; if an HS code is supplied it must be **exactly 8 digits**. On success `Type` is set to `99` (accepted) and the form closes; Cancel sets `Type = -99`. Uses `CADMaintenance.isInteger(...)`. (`InputForm.cs` SubmitData / CloseButton)

### Shared helper: EditDialog.cs

- **BR-UTIL-053** — Generic single‑value edit dialog: shows the current value (`existval_disp`, read‑only, blue) and an editable `newval_disp`, with a `prop_label` naming the property ("Please enter a new value for the property …"). On load it selects‑all and focuses the new‑value box. OK/Cancel simply `Close()` (the caller reads `newval_disp.Text`). Used for ad‑hoc property edits across forms. (`EditDialog.cs`)

### Shared helper: AddDataList.cs

- **BR-UTIL-054** — Generic **multi/single‑select list** dialog (`initialiseDataList(catalogueId, categoryId, existingList, selectionMode, optionalList)`). The SQL it runs is chosen by the form's `Text`/`Label1` context, e.g.:
  - Products in a catalogue+category: `SELECT DISTINCT Product.ProductId, Product.Product FROM Product … CatalogueItems ci … WHERE ci.CatalogueId=… AND pr.ProductCategoryId=… AND Product.Status=1 AND Item.Status=1` (with a `UNION` against `CatalogueItemsUnreleased`). (`:405‑420`)
  - Attributes: `SELECT DISTINCT attr.AttributeId, attr.Name, attr.DisplayOrder FROM Attribute … CatalogueAttributeValues cav WHERE cav.CatalogueId=… AND attr.ProductCategoryId=…`. (`:436`)
  - Options: `SELECT DISTINCT opt.OptionId, opt.Name, opt.DisplayOrder FROM [Option] … CatalogueOptionValues cov WHERE cov.CatalogueId=… AND opt.ProductCategoryId=…`. (`:466`)
  - Catalogue name lookup: `SELECT Name FROM Catalogue WHERE CatalogueId=…`. (`:358`)
  - Special contexts recognised by title: "Add Option to Item Component", "Price Band Maintenance", "Composition Maintenance", "Select a User", "Add Linked Attribute", handbook product groups. (`:370‑383`, `:530`)
  `existingList` items are appended into the `WHERE` to exclude already‑selected rows. Used app‑wide as a picker for products/attributes/options/users/etc. (`AddDataList.cs`)

### Shared helper: AddNewData.cs

- **BR-UTIL-055** — Generic **add‑data** dialog (`initArrays(...)`, `initSQL(mysql)`) for adding fabrics/options/product‑group codes and downloadable assets. Context (again driven by `Label1`/`Text`) selects the query, e.g. product‑group codes (`SELECT od.ShortDescription, pgc.ProductGroupCodeId FROM ProductGroupCodes pgc INNER JOIN OtherDescription od … WHERE pgc.ParentGroupCodeId < 0 ORDER BY pgc.DisplayOrder`, `:604`), existing fabrics (`… opt.OptionId = 8 …`, `:698`), fabric colours, catalogue fabric options (`opt.IsFabric = 1 AND cov.CatalogueId=…`, `:739`).
- **BR-UTIL-056** — When adding a new option value it can **write** to the DB: `SELECT TOP 1 DescriptionId FROM OtherDescription ORDER BY DescriptionId DESC` → `INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES (…, 1, '…', 'OptionValue')` → `INSERT INTO OptionValue (OptionId, Name, OrderCodeValue, DescriptionId, Status, ImageFile, CADMaterial …)` → optionally `INSERT INTO DependentOptionValues (OptionValueId, AdditionalOptionValueId) VALUES (…)`. (`:986‑1020`)

### Shared helper: ProgressThread.cs

- **BR-UTIL-057** — Worker thread owned by `ExportDPSDBThread`. Runs the DTS package to publish PDM to the DPS database via **`exec master.dbo.xp_cmdshell 'dtsrun -E -Sdbchip02 -N"Export_PDM2004_to_DPSDB"'`** (`CommandTimeout = 600`). It streams `xp_cmdshell` output into `myparent.exportLog`; sets `myparent.terminate = false` only when a line starts with `"DTSRun:  Package execution complete"`, and `exportComplete = true` at the end. Server `dbchip02` and package name are hard‑coded. (`ProgressThread.cs`)

### Shared helper: DelayThread.cs

- **BR-UTIL-058** — Debounce timer for the CAD Maintenance category filter. `initThread(requestId, delay)` (default delay 500 ms). `execThread` sleeps, then fires `UpdateStatus("filter_category")` **only if** `_requestId == CADMaintenance.delayedRequestId` — i.e. the request is still the most recent (superseded keystrokes are dropped). (`DelayThread.cs`)

### Shared helper: TimerThread.cs

- **BR-UTIL-059** — Elapsed‑time display thread. States: `"Start"` (tick every 1000 ms, increment seconds→minutes→hours, `Application.DoEvents()`, raise `UpdateTimerLabel`), `"Stop"` (idle, sleep 2000 ms), `"Terminate"` (exit). Formats `"Elapsed Time: HH:MM:SS"` with zero‑padding. Hard cap at `_elapsedSeconds < 1000000`. `resetTimer()` zeroes it. (`TimerThread.cs`)

### Shared helper: debug_form.cs

- **BR-UTIL-060** — Generic scrollable text output window (`debug_text` TextBox + a button). Reused throughout as the app's "report/console" surface — e.g. image‑validation results (module 17), missing‑application‑text lists, missing‑image lists. Supports a `relocateWindow` flag and a resize handler. (`debug_form.cs`)

### Shared helper: MDBQuery.cs

- **BR-UTIL-061** — pCon **Access/Jet MDB** query & search tool. `initThread(mysql, database, workspace)` selects the target file under `CADMaintenance.pConPath + "WS\<workspace>\"`: default `pcr_data_com_ocd.mdb`; `database = "ODB"` → `pcr_data_geo_odb.mdb`; `"OAS"` → `pcr_data_sel_oas.mdb`; `"CLS"` → `pcr_data_typ_cls.mdb`. Connects via `Provider=Microsoft.Jet.OLEDB.4.0`. (`MDBQuery.cs:56‑70`)
- **BR-UTIL-062** — Supports a `"find <term>"` command that enumerates all tables (`GetOleDbSchemaTable`), builds a per‑table `SELECT * … WHERE <stringcol> LIKE '%term%' OR …` across every string column, and reports matching rows with table names and a per‑table hit summary; single quotes in the term are treated as `%` wildcards. Otherwise it executes the raw SQL and dumps the result grid as text with a header row. (`MDBQuery.cs:72‑200+`)

---

## 7. Hidden Logic

- **HL-UTIL-1** — `StaticDataMaintenance` uniquely uses parameterised commands with optimistic concurrency (`@Original_*`), so a concurrent edit by another user causes the update's `WHERE` to match zero rows (silent no‑op) rather than a last‑writer‑wins overwrite.
- **HL-UTIL-2** — Price‑formula edits never `UPDATE` in place; they insert a new row and delete the old (BR‑UTIL‑035). Any external reference to a `PriceFormulaId` becomes stale after an "edit".
- **HL-UTIL-3** — The `'abcx'` sentinel (BR‑UTIL‑032) is a magic value; a real DomCurrCode of `abcx` would silently break grid loads.
- **HL-UTIL-4** — Language maintenance is reachable **only** with `CoreMaintenance` — there is no `LanguageMaintenance` privilege; a user could have every other financial flag and still never see the Language tab.
- **HL-UTIL-5** — `ProgressThread` inverts the usual meaning of `terminate`: it sets `myparent.terminate = true` up front and only clears it to `false` on the "Package execution complete" line — the owning thread uses this as a completion signal, not a cancel flag.
- **HL-UTIL-6** — `DelayThread` uses a shared static `CADMaintenance.delayedRequestId` as a "latest request wins" token; stale timers simply do nothing when they wake.
- **HL-UTIL-7** — `MDBQuery` depends on `CADMaintenance.pConPath` and a live pCon workspace directory; without a configured pCon staging area the MDB paths won't resolve.
- **HL-UTIL-8** — The Product Code projection silently omits `Rounding` (commented out), so that column can't be edited here even though it exists in the pricing model (module 18).

---

## 8. UI Behaviour

- `StaticDataMaintenance` is a tabbed grid form; tabs present depend on privileges (BR‑UTIL‑020..024). Read‑only DB connection appends "(read only)" to the caption.
- Grids use custom `CGrid`/`CGridTextBoxStyle`/`CGridCheckBoxStyle` styling; Product Code rows disallow add/delete without privilege and the whole grid becomes read‑only.
- Filter combos (DomCurrCode `Filter2ComboBox` with `*ALL*`, `PLCFilterText`, `FilterComboBox`) are positioned dynamically and shown/hidden per tab.
- `Update` commits and (for formulas) writes audit rows; `Apply Factors` recomputes formula prices in the grid before Update.
- Helper dialogs are modal (`ShowDialog`) pickers/editors; `debug_form` is the shared text‑report window.
- `TimerThread`/`ProgressThread` drive progress labels/logs during long DPS export operations.

---

## 9. Dependencies

- `AuthenticateUser` — `setUserPrivileges`, flags `ReadOnlyFinancial`, `CoreMaintenance`, `CurrencyMaintenance`, `SiteMaintenance`, `ExchangeRates`, `FormulaMaintenance`, `ProductCodeMaintenance`.
- `ConnectionFactory.CreateNewConnection(autoOpen)` — all DB access.
- `Global` — `readOnlyDBConnection`, `connectedDB`.
- `PDMAudit` database — `Transactions`, `PFUpdates`.
- `SDXmlExport` (module 22) — static‑data XML export; `ImportStaticData` — CSV import.
- `CADMaintenance` — `pConPath`, `delayedRequestId`, `isInteger` (used by `MDBQuery`, `DelayThread`, `InputForm`).
- `ExportDPSDBThread` — owns `ProgressThread`; DTS server `dbchip02`, package `Export_PDM2004_to_DPSDB`, `xp_cmdshell` enabled on the SQL server.
- pCon Jet/Access MDBs under `<pConPath>\WS\<workspace>\` (`Microsoft.Jet.OLEDB.4.0`).
- `Microsoft.VisualBasic` (`Interaction.MsgBox`, `InputBox`, `Operators`, `Conversions`) — decompiled‑from‑VB idioms throughout.

---

## 10. Risks

- **SQL injection** — the parameterised entity commands are safe, but the surrounding helper/filter queries string‑concatenate values: `getExRate` (Q‑UTIL‑012), the price‑formula audit/replace block (Q‑UTIL‑020), Price Matrix validation (Q‑UTIL‑025), product‑group‑code lookups (Q‑UTIL‑026), and `AddDataList`/`AddNewData` context SQL (§6) all build SQL from values (codes, descriptions, filenames). Descriptions/user text with a quote can break or inject.
- **`xp_cmdshell`** — `ProgressThread` runs an OS command (`dtsrun`) through `xp_cmdshell`, requiring that dangerous feature to be enabled; command and server (`dbchip02`) are hard‑coded and unvalidated.
- **Insert‑delete formula edits** — an interruption between the `INSERT` and `DELETE` (BR‑UTIL‑035) could leave duplicate formulas; a failed lookup between them could delete the wrong/none.
- **Silent concurrency no‑ops** — optimistic‑concurrency updates that match zero rows report success without changing anything (HL‑UTIL‑1); users may believe an edit saved when it didn't.
- **Permission coupling** — Language gated behind `CoreMaintenance` and Formula+Matrix behind a single `FormulaMaintenance` flag conflate distinct responsibilities; over‑ or under‑granting is easy.
- **Magic sentinels / hard‑coding** — `'abcx'` DomCurrCode, `SiteId 20` exclusion, server/package names, pCon paths and MDB filenames are all compile‑time constants.
- **Jet/OLEDB dependency** — `MDBQuery` needs the legacy 32‑bit `Microsoft.Jet.OLEDB.4.0` provider and Access MDBs; unavailable on modern 64‑bit stacks.
- **Schema drift** — commented‑out `Rounding` column (BR‑UTIL‑036) indicates the code and DB schema have diverged; edits here may not cover all live columns.
