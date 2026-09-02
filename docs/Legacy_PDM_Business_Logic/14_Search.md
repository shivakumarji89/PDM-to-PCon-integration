# 14 — Search / Ad-hoc Data Query

**Module prefix:** BR-SRCH
**Primary legacy source:** `PDMMaintenance/DataQuery.cs` (~2797 lines); dispatch/entry SQL in `PDMMaintenance/MainMenu.cs` (the *"Query …"* menu, `DataQueryToolStripMenuItem`, 42 sub-items).
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

`DataQuery.cs` is a **single reusable search / lookup / drill-down dialog form** — **NOT** a generic free-text SQL runner. The caller (almost always `MainMenu.cs`) fully constructs the SQL as string literals and passes it in; the end user only supplies a *search value* and picks combo-box filters. The form:

- Runs one caller-supplied `SELECT` (or the `PDMOptionDataReport` stored proc) with token substitution, and renders the first column into a `ListBox` (`list_results`) with remaining columns shown as a details pane.
- Provides **drill-down** hyperlinks (`label_catalogues`, `label_products`, `label_item`) that spawn *new* `DataQuery` instances with different pre-built SQL.
- Doubles as a lightweight **maintenance tool**: it also performs *writes* — reassign Product Line Code (`ApplyButton`/`ApplyToAllButton`), reactivate products (`ReactivateButton`), delete option-increment rows (`DeleteButton`), and toggle `Product.HideInEOSCloud`.
- Hosts a few non-`DataQuery` utilities on the same menu (CSV financial/price-band exports, bulk item delete, statistics) — those are separate handlers in `MainMenu.cs`.

Because the search term is spliced into the SQL by `String.Replace` with no parameterization, **every search is an inline string-concat SQL statement and is injectable** (see §10).

The menu item **`[Custom Function / Query]`** (`CustomFunctionQueryToolStripMenuItem_Click`, MainMenu.cs:5066) is a developer hook that currently does nothing — it just shows `MsgBox("no function currently assigned")`. It is **not** a generic SQL console.
The menu item **`pCon mdb query …`** (`PConMdbQueryToolStripMenuItem_Click`, MainMenu.cs:4996) opens a *different* form, `MDBQuery` (Jet/Access query tool over the pCon `.mdb`) — out of scope for this module but noted as the nearest thing to a generic query runner.

---

## 2. Entry Points

All under the MainMenu **“Query …”** drop-down (`DataQueryToolStripMenuItem`, 42 items, MainMenu.cs:2321). Items that construct a `DataQuery` (form Title set via `dataQuery.Text = …`, which then *drives behaviour*):

| Menu text | Handler (MainMenu.cs) | Form Title | Primary query |
|---|---|---|---|
| Search for Item | `SearchForItemToolStripMenuItem_Click` (3922) | `Search for PDM Item` | Q-SRCH-005 |
| Items by Catalogue | `ItemsByCatalogueToolStripMenuItem_Click` (3931) | `Display Items by Catalogue` | Q-SRCH-007 |
| Items by Product Line Code | `ItemsByProductLineToolStripMenuItem_Click` (3940) | `Display Items by Product Line Code` | Q-SRCH-008 |
| Items by Product Line Code Group | `ItemsByProductLineCodeGroupToolStripMenuItem_Click` (3949) | `Display Items by Product Line Code Group` | Q-SRCH-009 |
| Catalogues by Item | `CataloguesByItemToolStripMenuItem_Click` | `Display Catalogues by Item` | Q-SRCH-010 |
| Catalogues by Product Line Code | `CataloguesByProductLineToolStripMenuItem_Click` | `Display Catalogues by Product Line Code` | Q-SRCH-011 |
| Catalogues by Fabric | `CataloguesByFabricToolStripMenuItem_Click` | `Display Catalogues by Fabric` | Q-SRCH-012 |
| Categories by Product Line Code | `CategoriesByProductLineToolStripMenuItem_Click` | `Display Categories by Product Line Code` | Q-SRCH-013 |
| Search for AttributeValue | `SearchForAttributeValueToolStripMenuItem_Click` | `Search for Attribute Value` | Q-SRCH-014 |
| Search for OptionValue | `SearchForOptionValueToolStripMenuItem_Click` | `Search for Option Value` | Q-SRCH-015 |
| Products by AttributeId | `ProductsByAttributeIdToolStripMenuItem_Click` | `Display Products by AttributeId` | Q-SRCH-016 |
| Products by AttributeValueId | `ProductsByAttributeValueIdToolStripMenuItem_Click` | `Display Products by AttributeValueId` | Q-SRCH-017 |
| Products by OptionId | `ProductsByOptionIdToolStripMenuItem_Click` | `Display Products by OptionId` | Q-SRCH-018 |
| Products by OptionValueId | `ProductsByOptionValueIdToolStripMenuItem_Click` | `Display Products by OptionValueId` | Q-SRCH-019 |
| Products by OptionValueId (ex dep) | `ProductsByOptionValueIdExDepToolStripMenuItem_Click` | `…(excluding dependencies)` | Q-SRCH-020 |
| Products by Option Order Code | `ProductsByOptionOrderCodeToolStripMenuItem_Click` | `Display Products by Option Order Code` | Q-SRCH-021 |
| SuperProducts by Component | `SuperProductsByComponentToolStripMenuItem_Click` | `Display SuperProducts by Component Item` | Q-SRCH-024 |
| Item Option Data Report | `ItemOptionDataReportToolStripMenuItem_Click` | `Item Option Data Report` | Q-SRCH-025 (stored proc) |
| Catalogues by AttributeValueId | `CataloguesByAttributeValueIdToolStripMenuItem_Click` | `Display Catalogues by AttributeValueId` | Q-SRCH-022 |
| Catalogues by OptionValueId | `CataloguesByOptionValueIdToolStripMenuItem_Click` | `Display Catalogues by OptionValueId` | Q-SRCH-023 |
| Non-Active Products | `NonActiveProductsToolStripMenuItem_Click` | `Non-Active Products` | Q-SRCH-026 |
| Item Option Increments | `ItemOptionIncrementsToolStripMenuItem_Click` | `Item Option Increments` | Q-SRCH-027 |
| Unresolved Product Images | `UnresolvedProductImagesToolStripMenuItem_Click` | `Unresolved Product Images` | Q-SRCH-028 (validate thread) |
| Unresolved EOS Cloud Images | `UnresolvedEOSCloudImagesToolStripMenuItem_Click` | `Unresolved EOS Cloud Images` | Q-SRCH-028 |
| Empty Product Application Text | `EmptyProductApplicationTextToolStripMenuItem_Click` | `Empty Product Application Text` | Q-SRCH-030 |

**Non-`DataQuery` items on the same menu (separate handlers, not this form):** Export Financial Data (Q-SRCH-EXP-A/B/C), Export Price Band Data (Q-SRCH-EXP-D), Delete Items … (bulk CSV delete), Launch DPS dll, PDM Statistics, SyteLine Extended Item Report, Download Assets, Validate XML, pCon mdb query (→ `MDBQuery`), **[Custom Function / Query] (disabled stub)**, Import Materials in to CSI, Resolve Knoll EU Item Mapping, Prepare SIF files for US Price Rise, Cross Reference Item Details.

**Programmatic re-entry (not menu):**
- `DataQuery.ItemInfoButton_Click` → opens a nested `Search for PDM Item` (DataQuery.cs:2442).
- `DataQuery.label_catalogues_Click` / `label_products_Click` → nested drill-down `DataQuery` (DataQuery.cs:2682 / 2783).
- `ProductDescriptions` reuses the same query patterns (cross-module; see 13_Descriptions).

**Public parameterisation API:** `internal void initDataQuery(string mysql, string combosql, string defaultselection)` (DataQuery.cs:1088). `mysql` = main SELECT (may contain tokens `{text}`, `{combo_val}`, `{site_val}`, `{status}`); `combosql` = SQL to fill `ComboBox1`; `defaultselection` = default combo text. Behaviour is further branched by `this.Text` (the form Title) and label texts.

---

## 3. Call Hierarchy

```
MainMenu."Query …" item _Click
  └─ new DataQuery()
       ├─ .Text = "<title>"                      // drives all behaviour switches
       ├─ .Label1/.Label2 .Text = "<prompt>"
       ├─ initDataQuery(mysql, combosql, default) // DataQuery.cs:1088
       │    ├─ ConnectionFactory.CreateNewConnection(autoOpen:true)
       │    ├─ (Site combo)   Q-SRCH-001
       │    ├─ (PLC override)  updatePLCOverrideList → Q-SRCH-002   [Search for PDM Item only]
       │    └─ updateComboBox() → runs {combosql}   (ComboBox1 fill)
       └─ .Show()  /  .processQuery()

DataQuery.processQuery()                          // DataQuery.cs:1323  (the engine)
  ├─ token rewrites  ({text}→search, * → %, {status}, {combo_val}, {site_val})
  ├─ ComboBox3 status filter injection            // BR-SRCH-005
  ├─ SqlCommand(text).ExecuteReader()             // runs caller SQL
  ├─ column loop → list_results + _descList + _detailsList + id lists
  └─ updateButtons()

Row selection (list_results_SelectedIndexChanged) → updateList()
Combo change (ComboBox1/2/3_SelectedIndexChanged)  → processQuery()/updateComboBox()

Buttons / links (all in DataQuery.cs):
  SearchButton_Click            → processQuery()
  text_search_KeyPress (Enter)  → processQuery()
  ApplyButton_Click (2052)      → PLC reassign + PDMAudit (Q-SRCH-031)
  ApplyToAllButton_Click (2138) → bulk PLC reassign + override (Q-SRCH-032)
  ReactivateButton_Click (1975) → Product.Status=1 (Q-SRCH-033)
  DeleteButton_Click (2463)     → delete ItemOptionValues w/ perm check (Q-SRCH-034)
  ItemInfoButton_Click (2367)   → Validate Images thread / Validate App Text / nested search
  label_item.Click → showApplicationText (1868)   → Q-SRCH-029
  label_catalogues_Click (2682) / label_products_Click (2783) → nested DataQuery
  label_export_Click (2592)     → CSV export of current results
  check_hideInEOSCloud_CheckChanged (1248) → Q-SRCH-003 / Q-SRCH-004
```

---

## 4. SQL Analysis

> All SQL is built by inline string concatenation and executed through `ConnectionFactory.CreateNewConnection` → `SqlConnection`/`SqlCommand`. Tokens are substituted with `String.Replace` — **no `SqlParameter` is used anywhere in this module**.

### Infrastructure / combo queries

**Q-SRCH-001** — Site combo (`initDataQuery`, DataQuery.cs:1143). *WHY:* populate `ComboBox2` (site filter) and map index→SiteId; default = `AuthenticateUser.DefaultSiteId`.
```sql
SELECT SiteId, Description FROM Site
```

**Q-SRCH-002** — PLC-override combo (`updatePLCOverrideList`, DataQuery.cs:1065). *WHY:* only for `Search for PDM Item`; lets the user pick a per-item Product-Code override. Prepends synthetic `[ no override ]` = id `-1`.
```sql
SELECT ProductCodeId, Product_Code FROM Product_Code WHERE SiteId = {site} AND Status = 1 ORDER BY Product_Code
```

**Q-SRCH-003 / Q-SRCH-004** — Hide-in-EOS toggle (`check_hideInEOSCloud_CheckChanged`, DataQuery.cs:1260/1276). *WHY:* read current flag by item then flip `Product.HideInEOSCloud`.
```sql
SELECT DISTINCT Product.ProductId, Product.HideInEOSCloud FROM Product INNER JOIN Item ON Product.ProductId = Item.ProductId WHERE Item.Item = '<item>'
UPDATE Product SET HideInEOSCloud = <0|1> WHERE ProductId = <id>
```

### Main search queries (passed to `initDataQuery`)

**Q-SRCH-005** — *Search for PDM Item* (MainMenu.cs:3926). *WHY:* master item finder joining Product/Product_Code (with `ProductCodeIdOverride` correlated sub-select), category/range, and CASE-decoded Product/Item status. **Hardcodes `Product_Code.SiteId = 1`.**
```sql
SELECT Item.Item, Product.Product, Item.ProductId, Product.Name As Description, Product.ProductCodeId,
       Item.ProductCodeIdOverride, Product_Code.Product_Code + ' (' + convert(varchar, Product_Code.ProductCodeId) + ')' AS [Product Code],
       pc.ProductCategoryId AS CategoryId, pc.Name AS Category, pr.ProductRangeId AS RangeId, pr.Name AS Range,
       Product.IsSuperProduct,
       CASE WHEN Product.Status = 0 THEN 'Unreleased' WHEN Product.Status = 1 THEN 'Active' WHEN Product.Status = 2 THEN 'Obsolete' WHEN Product.Status = 3 THEN 'On Hold' END AS [Product Status],
       CASE WHEN Item.Status = 0 THEN 'Unreleased' WHEN Item.Status = 1 THEN 'Active' WHEN Item.Status = 2 THEN 'Obsolete' WHEN Item.Status = 3 THEN 'On Hold' END AS [Item Status]
FROM Item CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x
     INNER JOIN Product ON Item.ProductId = Product.ProductId
     LEFT OUTER JOIN Product_Code ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL
                                          THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId )
                                          ELSE Product.ProductCodeId END = Product_Code.ProductCodeId AND Product_Code.SiteId = 1
     INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
     INNER JOIN ProductCategory pc ON pr.ProductCategoryId = pc.ProductCategoryId
WHERE Item.Item Like '%{text}%' ORDER BY Item.Item
```
**Q-SRCH-006** — its combo: `SELECT ProductCodeId, Product_Code + ' | ' + Description FROM Product_Code WHERE SiteId = {site_val} ORDER BY Product_Code`.
`check_byname` swaps `WHERE Item.Item Like '%{text}%'` ↔ `WHERE Product.Name Like '%{text}%'` (DataQuery.cs:1359-1367).

**Q-SRCH-007** — *Items by Catalogue* (MainMenu.cs:3934): UNION of `CatalogueItems` + `CatalogueItemsUnreleased`, filtered `Catalogue.CatalogueId = {combo_val}`, PLC via override CASE, `pc.SiteId = {site_val}`. *WHY:* list every item in the chosen catalogue (released + unreleased).

**Q-SRCH-008** — *Items by Product Line Code* (MainMenu.cs:3944): `WHERE pc.ProductCodeId = {combo_val}` with override CASE, `pc.SiteId = {site_val}`.

**Q-SRCH-009** — *Items by Product Line Code Group* (MainMenu.cs:3956): DISTINCT UNION over `ProductGroupCodes pgc` (self-join to parent) filtered `pgc.ProductGroupCodeId = {combo_val} AND Product.Status {status} AND Item.Status {status}`. `{status}` = `< 2` normally or `>= 0` when *Include OBS data* checked (BR-SRCH-011). Second UNION branch carries the inline comment `/* DO NOT USE PLC OVERRIDE HERE -> TOO COMPLEX FOR LARGE SUPER PRODUCT SETS */`.

**Q-SRCH-010** — *Catalogues by Item* (MainMenu.cs:3970; also rebuilt inside `processQuery`, DataQuery.cs:1381/1385, with `check_URL` = *Include URL data*). Non-URL variant (released only):
```sql
SELECT DISTINCT Catalogue.Name, od.ShortDescription As Description, Catalogue.LeadTime As [Lead Time],
       pc.ProductCategoryId As CategoryId, pc.Name As Category, pr.ProductRangeId As RangeId, pr.Name As Range, Catalogue.DisplayOrder
FROM Catalogue INNER JOIN CatalogueItems ci ON Catalogue.CatalogueId = ci.CatalogueId
     INNER JOIN Item ON ci.ItemId = Item.ItemId INNER JOIN Product ON Item.ProductId = Product.ProductId
     INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
     INNER JOIN ProductCategory pc ON pr.ProductCategoryId = pc.ProductCategoryId
     INNER JOIN OtherDescription od ON Catalogue.DescriptionId = od.DescriptionId And od.LanguageId = 1
WHERE Item.Item Like '<w>{text}<w>' ORDER BY Catalogue.Name
```
The URL variant adds a second `UNION` over `CatalogueItemsUnreleased`. `<w>` = `%` unless the typed value is an *exact* existing item (existence probe `SELECT Item FROM Item WHERE Item = '<typed>'`, DataQuery.cs:1371) in which case `<w>` = empty (exact match) (BR-SRCH-009).

**Q-SRCH-011** — *Catalogues by Product Line Code* (MainMenu.cs:3982): `WHERE pc.ProductCodeId = {combo_val}`, override CASE, `pc.SiteId = {site_val}`.

**Q-SRCH-012** — *Catalogues by Fabric* (MainMenu.cs:3990):
```sql
… FROM Catalogue INNER JOIN CatalogueOptionValues cov … INNER JOIN OptionValue optval … INNER JOIN [Option] opt …
   INNER JOIN ProductCategory pc ON opt.ProductCategoryId = pc.ProductCategoryId
   INNER JOIN OtherDescription od ON optval.DescriptionId = od.DescriptionId AND od.LanguageId = 1
WHERE optval.OrderCodeValue LIKE '{text}%' AND opt.IsFabric >= 1 ORDER BY Catalogue.Name
```
*WHY:* find catalogues containing a fabric order-code; `opt.IsFabric >= 1` restricts to fabric options.

**Q-SRCH-013** — *Categories by Product Line Code* (MainMenu.cs:3998): `WHERE ProductCategory.ProductCategoryId <> 999 AND ProductCategory.ProductCategoryId <> 1000 AND pc.ProductCodeId = {combo_val}` (BR-SRCH-038).

**Q-SRCH-014** — *Search for AttributeValue* (MainMenu.cs:4006):
```sql
SELECT DISTINCT attr.Name + ' - ' + atval.Name AS Product, … , atval.AttributeValueId, atval.OrderCodeValue,
       pc.ProductCategoryId AS CategoryId, pc.Name AS Category, attr.AttributeId, atval.Status
FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId
     INNER JOIN ProductCategory pc ON attr.ProductCategoryId = pc.ProductCategoryId
WHERE atval.Status > -1 AND atval.Name LIKE '%{text}%' OR atval.OrderCodeValue LIKE '%{text}%'
ORDER BY attr.Name + ' - ' + atval.Name, attr.AttributeId
```
**Missing parentheses** around the `AND … OR …` predicate — see BR-SRCH-035.

**Q-SRCH-015** — *Search for OptionValue* (MainMenu.cs:4014): same shape over `OptionValue`/`[Option]`, same precedence bug.

**Q-SRCH-016** — *Products by AttributeId* (MainMenu.cs:4022): `… ProductAttributeValues pav … WHERE attr.AttributeId = {text}` (`{text}` used **unquoted** — numeric id).

**Q-SRCH-017** — *Products by AttributeValueId* (MainMenu.cs:4030): `… WHERE pav.AttributeValueId = {text}`.

**Q-SRCH-018** — *Products by OptionId* (MainMenu.cs:4038): **3-branch UNION** — direct `ProductOptionValues`, via `ProductAttributeValues → DependentAttributeValues → AdditionalOptionValueId`, and via `ProductOptionValues → DependentOptionValues`. Carries `[Parent AttributeValueId]`/`[Parent OptionValueId]` marker columns. *WHY:* surface products that get the option *through dependency chains*, not just directly.

**Q-SRCH-019** — *Products by OptionValueId* (MainMenu.cs:4046): same 3-branch UNION filtered on `OptionValueId = {text}`.

**Q-SRCH-020** — *Products by OptionValueId (ex dep)* (MainMenu.cs:4054): single branch, direct `ProductOptionValues` only, `WHERE pov.OptionValueId = {text}`.

**Q-SRCH-021** — *Products by Option Order Code* (MainMenu.cs:4062): 3-branch UNION, `WHERE optval.OrderCodeValue LIKE '{text}'`.

**Q-SRCH-022** — *Catalogues by AttributeValueId* (MainMenu.cs; also rebuilt in `label_catalogues_Click`): `… CatalogueAttributeValues cav … WHERE cav.AttributeValueId = {text}` with `atval.Name AS atval_desc, atval.OrderCodeValue AS atval_code`.

**Q-SRCH-023** — *Catalogues by OptionValueId*: `… CatalogueOptionValues cov … WHERE cov.OptionValueId = {text}` with `optval.… AS optval_desc/optval_code`.

**Q-SRCH-024** — *SuperProducts by Component* (MainMenu.cs:4088):
```sql
… FROM Product INNER JOIN Item ON Product.ProductId = Item.ProductId
   INNER JOIN ItemComponents itco ON Item.ItemId = itco.ItemId
   INNER JOIN Item subitem ON itco.SubItemId = subitem.ItemId …
WHERE subitem.Item LIKE '%{text}%' ORDER BY Product.Product
```
*WHY:* reverse-lookup — which SuperProducts contain a given component item.

**Q-SRCH-025** — *Item Option Data Report* (MainMenu.cs:4098): **stored procedure call**, not a SELECT.
```sql
PDMOptionDataReport '{text}'
```
Proc body `UNKNOWN` (see 21_OCD / 22_Export — same central proc). Result columns include `Option2`, `optval_name`, `ParentOptId/Name/ValName`, `DisplayOrder` and receive special row formatting (BR-SRCH-016).

**Q-SRCH-026** — *Non-Active Products* (MainMenu.cs:4106): `… WHERE Product.Status <> 1 AND Product.Product LIKE '%{text}%'`; default `text_search.Text = "*"` (BR-SRCH-037). `ReactivateButton` is shown for this title.

**Q-SRCH-027** — *Item Option Increments* (MainMenu.cs:4130): builds a single formatted string column with `IncrementalPrice/2/3` and returns `Item.ItemId`, `itov.OptionValueId` for the delete path; `WHERE Item.Item LIKE '%{text}%'`. `list_results.SelectionMode = MultiExtended`.

**Q-SRCH-028** — *Unresolved (EOS Cloud) Images* combo (MainMenu.cs:5018/5031): `SELECT CatalogueId, Name FROM Catalogue WHERE Status < 2 ORDER BY Name`. The `mysql` argument is the literal sentinel string `"Unresolved Product Images"` / `"Unresolved EOS Cloud Images"` — no SELECT; work is done by `ValidateImageThread` on the network image directory `\\wechip01v\HMEURONET\PDM\Images\` (DataQuery.cs:2412).

**Q-SRCH-029** — Application-text popup (`showApplicationText`, DataQuery.cs:1882): `SELECT Name, Product, ImageFile, pd.ApplicationText FROM Product INNER JOIN ProductDescription pd ON Product.DescriptionId = pd.DescriptionId WHERE Product.ProductId = <id> AND pd.LanguageId = 1`.

**Q-SRCH-030** — *Empty Product Application Text* validation (`ItemInfoButton_Click`, DataQuery.cs:2381):
```sql
SELECT Product.Product FROM Product INNER JOIN ProductDescription pd ON Product.DescriptionId = pd.DescriptionId AND pd.LanguageId = 1
   [INNER JOIN Item … INNER JOIN CatalogueItems ci … AND ci.CatalogueId = <combo>]   -- only when combo > 0
WHERE pd.ApplicationText IS NULL AND Product.Status < 2 ORDER BY Product.Product
```

### Write / maintenance queries

**Q-SRCH-031** — `ApplyButton_Click` (DataQuery.cs:2070+): read `SELECT ProductCodeId FROM Product WHERE ProductId = <id>`, then audit + update:
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('<user>', GetUTCDate(), '<Global.connectedDB>')
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '<user>' ORDER BY TransactionId DESC
INSERT INTO PDMAudit.dbo.ProdCodeUpdates (TransactionId, ProductId, PrevProdCodeId, NewProdCodeId, SiteId) VALUES (…)
UPDATE Product SET ProductCodeId = <new> WHERE ProductId = <id>
```

**Q-SRCH-032** — `ApplyToAllButton_Click` (DataQuery.cs:2187+): iterates every result row; same audit + `UPDATE Product SET ProductCodeId = …`, and additionally reads/writes the per-item override: `SELECT ProductCodeIdOverride FROM Item WHERE Item = '…'` then `UPDATE Item SET ProductCodeIdOverride = …`.

**Q-SRCH-033** — `ReactivateButton_Click` (DataQuery.cs:1989/2005): `SELECT Status, Product FROM Product WHERE ProductId = <id>` then `UPDATE Product SET Status = 1 WHERE ProductId = <id>`.

**Q-SRCH-034** — `DeleteButton_Click` (DataQuery.cs:2484/2494): permission probe then delete:
```sql
SELECT ci.CatalogueId FROM CatalogueItems ci INNER JOIN PDMUserCatalogues puc ON ci.CatalogueId = puc.CatalogueId AND puc.UserId = <UserId> AND puc.ReadOnly = 0 WHERE ci.ItemId = <id>
UNION SELECT ci.CatalogueId FROM CatalogueItemsUnreleased ci INNER JOIN PDMUserCatalogues puc ON … puc.ReadOnly = 0 WHERE ci.ItemId = <id>
-- if any row returned OR AuthenticateUser.PDMAdministrator:
DELETE FROM ItemOptionValues WHERE ItemId = <id> AND OptionValueId = <optval>
```

### Non-`DataQuery` menu handlers (same menu, for completeness)
**Q-SRCH-EXP-A/B/C** — *Export Financial Data* (MainMenu.cs): `Product_Code`, `PriceMatrix`, `PriceFormula` tab-delimited extracts per site. **Q-SRCH-EXP-D** — *Export Price Band Data*: `OptionValue` × `FabricBands` where `optval.status < 2`. (These belong to 18_Pricing / 22_Export; listed here only because they share the menu.)

---

## 5. Data Model

Read/lookup tables referenced by this module:

| Table | Role in search |
|---|---|
| `Item` | Master item; `Item`, `ItemId`, `ProductId`, `Status`, `ProductCodeIdOverride` |
| `Product` | `Product`, `ProductId`, `Name`, `DescriptionId`, `ProductCodeId`, `ProductRangeId`, `IsSuperProduct`, `Status`, `HideInEOSCloud`, `CADPlaceProgram` |
| `Product_Code` | PLC: `ProductCodeId`, `Product_Code`, `Description`, `SiteId`, `Status`, `GroupCode`, `PriceCode`, `UnitCode`, `BasePriceRef` |
| `ProductGroupCodes` | `ProductGroupCodeId`, `GroupCode`, `ParentGroupCodeId` (self-referencing hierarchy) |
| `ProductCategory` / `ProductRange` | grouping; ids 999/1000 special-cased |
| `Catalogue` | `CatalogueId`, `Name`, `DescriptionId`, `LeadTime`, `DisplayOrder`, `Status`, `PrimarySiteId` |
| `CatalogueItems` / `CatalogueItemsUnreleased` | catalogue↔item membership (released vs unreleased) |
| `CatalogueAttributeValues` / `CatalogueOptionValues` | catalogue-scoped attr/option values (incl. fabrics) |
| `OtherDescription` / `ProductDescription` | `ShortDescription`, `ApplicationText`, `LanguageId` (1 = English UK) |
| `Attribute` / `AttributeValue` | `AttributeId`, `AttributeValueId`, `Name`, `OrderCodeValue`, `Status`, `ProductCategoryId` |
| `Option` (`[Option]`) / `OptionValue` | `OptionId`, `OptionValueId`, `Name`, `OrderCodeValue`, `Status`, `IsFabric`, `DescriptionId` |
| `ProductAttributeValues` / `ProductOptionValues` | product↔value links |
| `DependentAttributeValues` (`AttributeValueId`,`AdditionalOptionValueId`) / `DependentOptionValues` (`OptionValueId`,`AdditionalOptionValueId`) | dependency chains used by *Products by Option…* UNIONs |
| `ItemComponents` (`ItemId`,`SubItemId`) | SuperProduct BOM, used by *SuperProducts by Component* |
| `ItemOptionValues` (`ItemId`,`OptionValueId`,`IncrementalPrice`/`2`/`3`) | option-increment rows (viewed + deleted) |
| `FabricBands` | price-band export |
| `Site` | site combo; `SiteId`, `Site`, `Description` |
| `PDMUserCatalogues` (`UserId`,`CatalogueId`,`ReadOnly`) | delete-permission gate (`ReadOnly = 0` ⇒ writable) |
| `PDMAudit.dbo.Transactions` / `PDMAudit.dbo.ProdCodeUpdates` | audit trail for PLC reassignment |
| **Stored proc** `PDMOptionDataReport '<item>'` | Item Option Data Report (body `UNKNOWN`) |

Status enum (decoded in-app, BR-SRCH-012): `0 = Unreleased (URL)`, `1 = Active (ACT)`, `2 = Obsolete (OBS)`, `3 = On Hold (HLD)`.

---

## 6. Business Rules

**BR-SRCH-001** — `DataQuery` is a single reusable dialog; **behaviour is switched on the form Title (`this.Text`)** and on label texts (`Search for `, `Products by `, `Catalogues by`, `ValueId`, `Option Increment`, `Item Option Data Report`, `Non-Active`, `Unresolved`, `Application Text`, etc.). The caller must set `Text` before/after `initDataQuery` or the wrong branch runs.

**BR-SRCH-002** — The search value replaces `{text}` via `String.Replace` (DataQuery.cs:1414) with **no parameterization or escaping**. Numeric-id searches (`= {text}`) and string searches (`LIKE '%{text}%'`) are both injectable (see §10 / OWASP A03).

**BR-SRCH-003** — Wildcard translation: after `{text}` substitution the SQL is `*`→`%` translated, but `/*` and `*/` are first protected (`/*`→`/~`, `*/`→`~/`, translate, restore) so block-comment markers survive (DataQuery.cs:1416-1419).

**BR-SRCH-004** — A query only runs when `text_search.Text <> ""` **or** the SQL contains no `{text}` token (DataQuery.cs:1406). Empty-with-token ⇒ nothing runs. *Item Option Increments* additionally requires a non-blank item (else `MsgBox`, DataQuery.cs:1349).

**BR-SRCH-005** — When the query starts with `SELECT Item.Item`, is **not** `Search for PDM Item`, and `ComboBox3.SelectedIndex > 0`, an item-status filter is injected by rewriting `WHERE ` → `WHERE Item.Status = 1 AND ` (index 1 = Active) or `Item.Status = 0 AND ` (index 2 = Unreleased) (DataQuery.cs:1421-1430).

**BR-SRCH-006** — `{combo_val}` ← `_comboValues[ComboBox1.SelectedIndex]`; `{site_val}` ← `_siteIdList[ComboBox2.SelectedIndex]` (DataQuery.cs:1445/1449). Combos are refilled by `updateComboBox`/`updatePLCOverrideList` when the site changes.

**BR-SRCH-007** — Default site index = position of `AuthenticateUser.DefaultSiteId` in the site list, else 0 (DataQuery.cs:1155).

**BR-SRCH-008** — *Search for PDM Item* only: `check_byname` (“Search by name (instead of code)”) toggles the `WHERE` clause between `Item.Item Like '%{text}%'` and `Product.Name Like '%{text}%'` (DataQuery.cs:1359).

**BR-SRCH-009** — *Catalogues by Item*: an existence probe (`SELECT Item FROM Item WHERE Item = '<typed>'`) decides the wildcard: exact hit ⇒ no `%` (exact match); miss ⇒ `%…%` contains-match (DataQuery.cs:1371-1379).

**BR-SRCH-010** — `check_URL` (“Include URL data”) is visible only for *Display Catalogues by Item* and *…by Product Line Code Group*. Checked ⇒ include `CatalogueItemsUnreleased` UNION (Catalogues by Item) or widen status (BR-SRCH-011).

**BR-SRCH-011** — For *…by Product Line Code Group* the `{status}` token becomes `< 2` (released/active) by default, or `>= 0` (all, incl. OBS) when *Include OBS data* is checked (DataQuery.cs:1435-1441). Note the check-box label text is swapped to “Include OBS data” for that title (DataQuery.cs:1099).

**BR-SRCH-012** — Status codes are decoded to text in the details pane: `0→Unreleased (URL)`, `1→Active (ACT)`, `2→Obsolete (OBS)`, `3→On Hold (HLD)` (DataQuery.cs:1590-1594).

**BR-SRCH-013** — Result rendering: column 0 → `list_results`; remaining columns become `name: value` detail lines, **except** the suppressed names `atval_code`, `optval_code`, `atval_desc`, `optval_desc`, `CategoryId`, `RangeId`, and `DisplayOrder`, plus blank values (DataQuery.cs:1548-1560).

**BR-SRCH-014** — A column literally named `ProductId` is captured into `_productIdList` (used for reactivate / app-text / PLC apply). A `Description`/`optval_name` column → `_descList`; `ProductCodeId`/`ProductCodeIdOverride` → their id lists (override blank ⇒ `-1` sentinel) (DataQuery.cs:1518-1544).

**BR-SRCH-015** — `DisplayOrder` is read for ordering but never shown as a detail line.

**BR-SRCH-016** — *Item Option Data Report* uses bespoke formatting: list label = `Option2 - optval_name`; detail lines prefix `Parent: <ParentOptName> - <ParentOptValName>`, append `/ DisplayOrder: …` to the option, and strip `2` suffixes / `DescId` / `DisplayOrder` helper columns (DataQuery.cs:1481-1510).

**BR-SRCH-017** — `Category`/`Range` detail lines append the corresponding id in parentheses (e.g. `Category: Seating (12)`) by re-reading `<name>Id` (DataQuery.cs:1568-1571).

**BR-SRCH-018** — PLC-override column: blank → `-1`; the current combo selection is compared to detect a pending change (BR-SRCH-019).

**BR-SRCH-019** — `ApplyButton` is enabled only when the selected `ComboBox1` PLC differs from the row’s stored `ProductCodeId`, **or** the chosen override differs from the stored override (DataQuery.cs:1633-1645 / `updateButtons` 1770).

**BR-SRCH-020** — `ApplyButton` writes an audit pair (`PDMAudit.dbo.Transactions` + `ProdCodeUpdates`) **before** `UPDATE Product SET ProductCodeId` (Q-SRCH-031). Audit is **not** gated here (contrast 18_Pricing where audit is disabled on eoscloud).

**BR-SRCH-021** — `ApplyToAllButton` iterates **every** current result row and updates both `Product.ProductCodeId` and the per-item `Item.ProductCodeIdOverride` (Q-SRCH-032). No per-row confirmation.

**BR-SRCH-022** — `ReactivateButton` is visible only when the Title contains `Non-Active`; it forces `Product.Status = 1` regardless of prior status (Q-SRCH-033).

**BR-SRCH-023** — `DeleteButton` (Item Option Increments) deletes `ItemOptionValues` only if the item belongs to a catalogue the user can write (`PDMUserCatalogues.ReadOnly = 0`) **or** `AuthenticateUser.PDMAdministrator`; otherwise the row is skipped and counted as “insufficient catalogue permissions” (DataQuery.cs:2504-2508).

**BR-SRCH-024** — `DeleteButton` is visible only when the Title contains `Option Increment` **and** `AuthenticateUser.PriceMaintenance` (DataQuery.cs:2534-2544).

**BR-SRCH-025** — The EOS-hide checkbox (`check_hideInEOSCloud`) exists only for `Search for PDM Item` and directly flips `Product.HideInEOSCloud` on check-change with no confirmation (Q-SRCH-003/004).

**BR-SRCH-026** — Drill-down: clicking `label_catalogues` opens *Catalogues by Item/AttributeValueId/OptionValueId*; clicking `label_products` opens *Products by AttributeValueId/OptionValueId*. The parent id is scraped from the details text (`AttributeValueId: `/`OptionValueId: ` substring parse), not from a bound field (DataQuery.cs:2726-2778 / 2800-2820).

**BR-SRCH-027** — For any `SELECT Item.Item` query the `label_item` becomes a hyperlink (blue on hover, hand cursor) that opens the Application-Text popup (Q-SRCH-029) (DataQuery.cs:1432 / 1936).

**BR-SRCH-028** — *Unresolved (EOS Cloud) Images*: `ItemInfoButton` (relabelled “Validate Images”) starts a background `ValidateImageThread` scoped to the selected catalogue combo (id 0 = all); requires the UNC image dir `\\wechip01v\HMEURONET\PDM\Images\` — missing dir ⇒ `MsgBox` abort. `DoneButton` doubles as *Cancel* while running (DataQuery.cs:2412-2440 / 1301).

**BR-SRCH-029** — *Empty Product Application Text*: `ItemInfoButton` (relabelled “Validate Application Text”) runs Q-SRCH-030 scoped by the combo catalogue (>0 joins `CatalogueItems`; 0 = all) and dumps offenders to a `debug_form` (DataQuery.cs:2381-2405).

**BR-SRCH-030** — CSV export (`label_export`, shown when there are results): writes `list + ';' + desc + ';' + <detail values>`; the file name is derived from the Title + sanitized search/combo/site text (DataQuery.cs:2620-2670). Detail lines are reduced to their value (substring after `: `).

**BR-SRCH-031** — *Item Option Increments* sets `list_results.SelectionMode = MultiExtended` so multiple rows can be deleted at once (DataQuery.cs:1616).

**BR-SRCH-032** — The **`[Custom Function / Query]`** menu item is a disabled developer stub: it only shows `MsgBox("no function currently assigned")` (MainMenu.cs:5066). It is *not* an admin SQL console.

**BR-SRCH-033** — **`pCon mdb query …`** opens a separate `MDBQuery` form (Access/Jet query tool over the pCon `.mdb`), not `DataQuery` (MainMenu.cs:4996). Its generic-query semantics are covered elsewhere (11_Configuration).

**BR-SRCH-034** — *Display Catalogues by Fabric* relabels the details `Status:` line to `Catalogue Status:` (to disambiguate from the fabric’s status) (DataQuery.cs:1645 / 1740).

**BR-SRCH-035** — **Operator-precedence defect** in Q-SRCH-014 / Q-SRCH-015: `WHERE atval.Status > -1 AND atval.Name LIKE '%{text}%' OR atval.OrderCodeValue LIKE '%{text}%'` has no parentheses, so SQL binds it as `(Status > -1 AND Name LIKE …) OR (OrderCode LIKE …)` — an order-code match returns values of **any** status (including `-1`). Documented as-is; likely unintended.

**BR-SRCH-036** — *Search for PDM Item* and the Application-Text validator hardcode `SiteId = 1` for the PLC join (DataQuery.cs:3926 / 2444), independent of the site combo.

**BR-SRCH-037** — *Non-Active Products* and *Item Option Increments* pre-seed `text_search.Text = "*"` and hide `ComboBox3`/`Label4` (MainMenu.cs:4110 / 4134).

**BR-SRCH-038** — *Categories by Product Line Code* excludes `ProductCategoryId` 999 and 1000.

**BR-SRCH-039** — Hover cue: `label_item` turns blue only when `_mysql` starts with `SELECT Item.Item`; `label_catalogues`/`label_products` always turn blue on hover (DataQuery.cs:1934/1947/1957).

**BR-SRCH-040** — When `_descList` is empty but there are results, the layout collapses the detail panes and shrinks the font (list-only mode) (DataQuery.cs:1601-1610).

**BR-SRCH-041** — Column-0 rendering: for *Item Option Data Report* it prints `Option2 - optval_name`; otherwise the raw first column (BR-SRCH-016).

**BR-SRCH-042** — No-result handling shows title-specific messages: “No item containing '<X>' exists in any active PDM catalogue …” (Catalogues by Item) or “… exists in PDM” (Search for PDM Item), upper-cased search term (DataQuery.cs:1626-1635).

**BR-SRCH-043** — Result count is shown (`Results: N`) and the *Copy* / *Export* labels appear only when `N > 0` (DataQuery.cs:1597-1601).

**BR-SRCH-044** — Every DB call opens a fresh `ConnectionFactory.CreateNewConnection(autoOpen:true)` and closes it in a `finally`; there is no shared/pooled command object and no transaction around the multi-statement writes (Q-SRCH-031/032) — a partial failure can leave audit rows without the matching `UPDATE` (or vice-versa).

**BR-SRCH-045** — On any exception the handler shows `MsgBox(text + "\r\n\r\n" + ex.ToString())` — i.e. **the full SQL and stack trace are shown to the user** (DataQuery.cs:1652 and throughout). Information-disclosure risk (OWASP A09).

---

## 7. Hidden Logic

- **Title-string dispatch.** There is no enum/strategy object; the entire behaviour tree keys off `this.Text` and label texts via `IndexOf`/`CompareString`. Renaming a menu title silently changes/breaks logic (e.g. the `SELECT Item.Item` prefix test, `Non-Active`, `Option Increment`).
- **`SELECT Item.Item` prefix contract.** Status-filter injection (BR-SRCH-005) and the app-text hyperlink (BR-SRCH-027) only fire if the SQL literally *starts with* `SELECT Item.Item`. A whitespace/case change disables them.
- **Comment-marker preservation.** The `* → %` translation deliberately round-trips `/*`…`*/` so a search value containing them is not corrupted — an odd concession that also means a user can smuggle SQL comments through the search box.
- **Details-text scraping for drill-down.** `label_catalogues_Click`/`label_products_Click` parse the *rendered* details string for `AttributeValueId: `/`OptionValueId: ` rather than reading a stored id — brittle if the detail formatting changes.
- **`-1` sentinel** for “no PLC override” both in the combo (`[ no override ]`) and in `_productCodeIdOverrideList`.
- **Site 1 hardcode** inside otherwise site-parameterised queries (BR-SRCH-036).
- **`GetImage` scaling** in the app-text popup contains a magic aspect factor `1.125`.
- **Nested self-instantiation:** the form frequently `new DataQuery()`s itself for drill-downs; each nested form runs its own `initDataQuery`/`processQuery` and connections.

---

## 8. UI Behaviour

- Layout: `text_search` + `SearchButton`, up to three combos (`ComboBox1` value filter, `ComboBox2` site, `ComboBox3` item-status), `list_results` list, `label_item`/`text_desc`/`text_details` detail panes, and context buttons (`Apply`, `Apply To All`, `Reactivate`, `Item Info`, `Delete`, `Done`).
- Enter in the search box triggers `processQuery` (`text_search_KeyPress`).
- Changing any combo re-runs `processQuery` (or `updateComboBox` when site drives combo1) — live filtering.
- `WaitCursor` during queries; buttons disabled while running.
- `Done` becomes **Cancel** during image validation; closing the form terminates the validate thread (`DataQuery_Closing`).
- `Apply`/`Apply To All` visibility is tied to whether `ComboBox1` (PLC) is enabled for the selected row.
- Multi-select list only for *Item Option Increments*.
- Result count, *Copy* and *Export* labels appear only with results.
- Errors surface as modal `MsgBox` containing SQL + exception (BR-SRCH-045).

---

## 9. Dependencies

- **`ConnectionFactory.CreateNewConnection`** → `SqlConnection` (PDM DB). See 00_System_Architecture.
- **`AuthenticateUser`** — `UserId`, `DefaultSiteId`, `PDMAdministrator`, `PriceMaintenance` (gates), and the `PDMUserCatalogues.ReadOnly` model.
- **`Global`** — `connectedDB` (written into `PDMAudit.dbo.Transactions`).
- **`MainMenu`** — builds all query strings and owns the “Query …” menu.
- **`ValidateImageThread`** — background image-existence check (Unresolved Images).
- **`ApplicationText`, `GetImage`, `debug_form`** — popups.
- **`MDBQuery`** — separate pCon `.mdb` query tool (via the pCon-mdb menu item).
- **Stored proc `PDMOptionDataReport`** — Item Option Data Report (body `UNKNOWN`).
- **DB tables** — see §5.
- **Network share** `\\wechip01v\HMEURONET\PDM\Images\` for image validation.

---

## 10. Risks

- **SQL injection (OWASP A03) — module-wide.** Every search term is concatenated via `String.Replace('{text}', userInput)` with no parameterization or escaping (BR-SRCH-002). Both `LIKE '%{text}%'` and unquoted `= {text}` (numeric-id searches) are exploitable from the search box; the deliberate `/* */` preservation (BR-SRCH-003) even lets comment markers through. A crafted value can read/alter any data the app’s SQL login can reach (and this login also performs `UPDATE`/`DELETE`).
- **Unconfirmed bulk writes.** `Apply To All` (BR-SRCH-021) rewrites `Product.ProductCodeId` **and** `Item.ProductCodeIdOverride` for *all* current results with no per-row confirmation; a broad search + click is destructive.
- **Non-transactional audit+update.** BR-SRCH-044: audit `INSERT`s and the `UPDATE` are separate statements on separate `SqlCommand`s with no transaction — partial failures desynchronise the audit trail.
- **Information disclosure (OWASP A09).** BR-SRCH-045: raw SQL + full exception shown in modal dialogs.
- **Authorization gaps.** Reactivate (BR-SRCH-022) and Hide-in-EOS (BR-SRCH-025) have **no permission check** beyond the menu being visible; only Delete (BR-SRCH-023/024) checks catalogue write rights.
- **Precedence defect** (BR-SRCH-035) makes attribute/option-value searches return obsolete/invalid rows on order-code matches — silent data-quality/UX bug.
- **Brittle string-dispatch** (§7): titles double as control flow; UI text changes can silently disable status filters, hyperlinks, delete/reactivate visibility.
- **Hardcoded `SiteId = 1`** (BR-SRCH-036) can mis-resolve PLCs for non-UK sites in the master item search.
- **Environment coupling** to a specific UNC image path for image validation (fails outside the corporate network).
- **`UNKNOWN`:** body of `PDMOptionDataReport`; exact schema of `PDMAudit.*`; whether the SQL login is least-privileged (assume not, given the inline DML).
