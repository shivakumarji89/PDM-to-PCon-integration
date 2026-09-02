# 05 — Products (Super Products)

**Module prefix:** BR-PROD
**Primary legacy source:** `PDMMaintenance/SuperProductMaintenance.cs` (~5973 lines), `PDMMaintenance/SuperProductVarCondRelation.cs` (~1603 lines)
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

This module maintains **Super Product** definitions. A *Super Product* is a standard PDM
`Product` whose `Item` records act as a **bundle (BOM-like assembly)** of other component
`Item` records. The many-to-many parent→component links are stored in the `ItemComponents`
table (`ItemId` = parent Super Product item, `SubItemId` = component item), together with a
`Quantity`, an ordering `ComponentSequence`, and a pipe-delimited `FeaturePositionString`
that maps parent Options onto component positions.

Two forms make up the cluster:

| Form | Responsibility |
|------|----------------|
| `SuperProductMaintenance` | Full CRUD of Super Product component definitions per Catalogue → Category → Product → Item → Component → Option. Bulk CSV import/export, cloning, price-report XLS generation, background validation, and automatic maintenance of the `Product.IsSuperProduct` flag. |
| `SuperProductVarCondRelation` | Generates pCon "VARCOND" price relations (`PA_<prefix>`) for Super Product items and exports them into the pCon commerce workspace MDB (`pcr_data_com_ocd.mdb`, `tCOMd_*` tables). |

**Distinction (critical, as found in code):**
- A **Super Product** is a `Product` with `Product.IsSuperProduct = 1` whose item(s) have rows in `ItemComponents`. It is *not* a separate table — it is a flag + BOM rows on an ordinary product/item.
- A **component** is itself an ordinary `Item` (referenced via `ItemComponents.SubItemId`). A component that also exists as a standalone product cannot be deleted (see BR-PROD-041).
- A **Super Item** is an `Item` with `IsSuperItem = 1` (used when deleting components, line 4205). `UNKNOWN`: full semantics of `IsSuperItem` are not defined in this cluster.
- The **article** and **product code scheme** concepts are documented in `06_Articles.md`.

---

## 2. Entry Points

| Entry point | File / line | Trigger |
|-------------|-------------|---------|
| `SuperProductMaintenance_Load` | `SuperProductMaintenance.cs:5251` | Form load — adds download/import/validate picture-box buttons and date picker. |
| `initialiseArrays()` | `SuperProductMaintenance.cs:2413` (`internal`) | Populates catalogue/site/currency selectors; called externally after construction. |
| `SuperProductVarCondRelation_Load` | `SuperProductVarCondRelation.cs:1092` | Form load → `initArrays()`. |
| Menu context items (`ComponentContextMenu`, `OptionContextMenu`) | various `menu*_Click` | Right-click add/remove/replace/delete component or option. |
| Toolbar picture-boxes | wired in `_Load` | Download SP defs (`downloadSPDefs`), Excel import (`importSPDefs`), Validate (`validateSPs`). |

`AuthenticateUser.SuperProductMaintenance` permission flag gates whether this form is reachable
from the main menu (foundation fact — permission enforcement is upstream, not re-checked inside
this form). Inside the form, edit capability is instead gated on **catalogue read-only** state.

---

## 3. Call Hierarchy

```
Form: SuperProductMaintenance
 └─ Load → initialiseArrays()
      ├─ SQL Q-PROD-002 (catalogues for user)   → catalogue_selector, _readOnlyCatalogues
      ├─ SQL Q-PROD-003 (sites, excl 20)         → site_selector
      ├─ SQL Q-PROD-004 (currencies)             → currency_selector
      └─ updateSPCompList() → Q-PROD-001         → spcomp_list (all component items)
 catalogue_selector_SelectedIndexChanged
      └─ updateCatalogueList() → Q-PROD-005       → category_selector (excl cat 1,128,129,999)
 category_selector_SelectedIndexChanged
      ├─ updateCategoryOptionList() → Q-PROD-006  → _categoryOptionIdList
      └─ updateProductList(filter) → Q-PROD-007   → product_list (released UNION unreleased)
 product_list_SelectedIndexChanged
      └─ updateItemList() → Q-PROD-009            → item_list
           ├─ updateSPOptionList() → SP PDMOptionDataReport
           └─ updateFeatureCount() → getFeatureCount() → SP PDMOptionDataReport
 item_list_SelectedIndexChanged
      ├─ updateComponentList() → Q-PROD-013       → component_list, seq_list, qty_list
      ├─ updateProgrammaticPanel()
      └─ pcode lookups → Q-PROD-011, Q-PROD-012   → pcode_list2 (programmatic panel)
 component_list_SelectedIndexChanged
      └─ updateOptionList() → Q-PROD-021,022      → option_list, pos_list
 SubmitButton_Click → Q-PROD-014..016 (UPDATE ItemComponents + resequence)
 menuAdd/Replace/Delete component → createNewItem()/menuDeleteComponent_Click
      └─ Q-PROD-018..020, Q-PROD-030..034 + updateSPFlag()
 updateSPFlag() → Q-PROD-035 → conditional UPDATE Product SET IsSuperProduct
 DeleteButton_Click → Q-PROD-039
 ReportButton_Click → generateXLSReport() → Q-PROD-024,025 (Excel COM)
 downloadSPDefs → Q-PROD-026 (CSV export)
 importSPDefs → Q-PROD-027 (CSV import)
 CloneButton_Click → Q-PROD-036..038 (CSV clone)
 validateSPs → ValidateThread (background)

Form: SuperProductVarCondRelation
 └─ Load → initArrays() → Q-PROD-002, Q-PROD-005b
      updateItemList() → Q-PROD-042 → list_relations ("PA_<prefix>")
 ExportButton_Click → VarCondThread → exportPendingRelations()
      → OleDb into pCon MDB: Q-PROD-043..047 (tCOMd_Relation, tCOMd_RelObj, tCOMd_RelObjRel)
```

**There is no service/repository layer** — event handlers build inline string-concatenated SQL
and execute it directly via `ConnectionFactory.CreateNewConnection` + `SqlCommand`. Model objects
are `System.Collections.ArrayList` index-parallel lists (e.g. `_itemIdList`, `_componentIdList`),
not typed entities.

---

## 4. SQL Analysis

> All SQL is inline, string-concatenated (SQL-injection prone — foundation fact). IDs assigned `Q-PROD-NNN`.

### SuperProductMaintenance.cs

**Q-PROD-001** — all reusable component items (line 2391):
```sql
SELECT DISTINCT Item.ItemId, Item.Item FROM Item
INNER JOIN ItemComponents itco ON Item.ItemId = itco.SubItemId
ORDER BY Item.Item
```
*WHY:* populate `spcomp_list` with every item that is used somewhere as a component (i.e. valid components to add).

**Q-PROD-002** — user's editable catalogues (line 2427):
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly
FROM PDMUserCatalogues puc INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId
WHERE puc.UserId = <AuthenticateUser.UserId> AND Catalogue.Status = 1
ORDER BY Catalogue.Name
```
*WHY:* only catalogues the current user is assigned to and that are active (`Status = 1`). `ReadOnly` cached for edit gating.

**Q-PROD-003** — sites (line 2449):
```sql
SELECT SiteId, Site, Description FROM Site WHERE SiteId NOT IN (20)
```
*WHY:* selectable sites; **site 20 is hard-excluded** (see BR-PROD-007).

**Q-PROD-004** — currencies (line 2471):
```sql
SELECT Currency_ID, Currency, Currency /*+ ' (' + Symbol + ')'*/ AS Description FROM Currency
```
*WHY:* currency list for price report. The `Symbol` concatenation is commented out (dead intent).

**Q-PROD-005** — categories for catalogue (line 2543, `updateCatalogueList`):
```sql
SELECT pc.ProductCategoryId, od.ShortDescription,
  CASE WHEN cpc.DisplayOrder = -1 THEN 9999 ELSE cpc.DisplayOrder END AS cpcDO
FROM ProductCategory pc
INNER JOIN CatalogueProductCategories cpc ON pc.ProductCategoryId = cpc.ProductCategoryId
INNER JOIN OtherDescription od ON cpc.DescriptionId = od.DescriptionId AND od.LanguageId = 1
WHERE cpc.CatalogueId = <catalogueId> AND cpc.ProductCategoryId NOT IN (1, 128, 129, 999)
ORDER BY cpcDO
```
*WHY:* categories in the selected catalogue, English (`LanguageId = 1`), sorted by display order with `-1` treated as last (`9999`). **Categories 1, 128, 129, 999 are excluded** (BR-PROD-008).

**Q-PROD-006** — category options (line 2616, `updateCategoryOptionList`):
```sql
SELECT OptionId, Name FROM [Option] WHERE ProductCategoryId = <categoryId> ORDER BY DisplayOrder
```
*WHY:* base option list offered when adding options to a component.

**Q-PROD-007** — product list, released + unreleased (line 2723, `updateProductList`):
```sql
SELECT DISTINCT Product.ProductId, Product.Product, Product.ProductCodeId, Product.IsSuperProduct, 1 AS Status
FROM Product
INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
INNER JOIN Item ON Product.ProductId = Item.ProductId
INNER JOIN BaseAttributeValues bav ON Item.ItemId = bav.ItemId
INNER JOIN CatalogueAttributeValues cav ON bav.AttributeValueId = cav.AttributeValueId
INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId AND ci.CatalogueId = <catalogueId>
[INNER JOIN ItemComponents itco ON Item.ItemId = itco.ItemId]   -- only if NonSuperCheck.Checked
WHERE pr.ProductCategoryId = <categoryId>
AND (Product.Product Like '%<FILTER>%' OR '<FILTER>' LIKE Product.Product + '%')
UNION SELECT DISTINCT ... , 0 AS Status ... CatalogueItemsUnreleased ciu ... (same WHERE)
ORDER BY Product.Product, Status DESC
```
*WHY:* products in category that have catalogued items; `Status = 1` = released (`CatalogueItems`), `Status = 0` = unreleased (`CatalogueItemsUnreleased`). When `NonSuperCheck` is ticked, an extra join to `ItemComponents` restricts to products that already have components. `ORDER BY ... Status DESC` prefers the released row when a product appears in both (dedup on `product_list.Items.Contains`).

**Q-PROD-009** — items for product (line 2856, `updateItemList`):
```sql
SELECT DISTINCT Product.Product, Item.Item, Item.ItemId, Item.ProductId, Item.Status
FROM Product
INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
INNER JOIN Item ON Product.ProductId = Item.ProductId
[INNER JOIN ItemComponents itco ON Item.ItemId = itco.ItemId]   -- only if HideCheck.Checked
INNER JOIN BaseAttributeValues bav ON Item.ItemId = bav.ItemId
INNER JOIN CatalogueAttributeValues cav ON bav.AttributeValueId = cav.AttributeValueId
WHERE Product.ProductId = <productId>
[AND Item.Status = 1]                                            -- only if URLCheck.Checked
[AND Item.Item LIKE '%<product_filter>%']                        -- only if product_filter set
ORDER BY Item.Item
```
*WHY:* items belonging to the selected product. `HideCheck` = only items that already have components; `URLCheck` = only released (`Status = 1`) items.

**Q-PROD-010** — option-report stored procedure (`updateSPOptionList` line ~2680, `getFeatureCount` line 2915):
```sql
EXEC PDMOptionDataReport @cataloguedesc = '<item>'   -- CommandType.StoredProcedure, CommandTimeout = 300
```
*WHY:* returns the parent SP item's option set (`OptionId`, `Option2`). Results **cached** in static `cachedOptDataItems / cachedOptDataOptionIds / cachedOptDataOptionNames`.

**Q-PROD-011** — product code for item (line 3424, `item_list_SelectedIndexChanged`):
```sql
SELECT pc.Product_Code FROM Product_Code pc
WHERE pc.ProductCodeId = <productCodeId> And pc.SiteId = <siteId>
```
**Q-PROD-012** — programmatic-panel matching product codes (line 3441):
```sql
SELECT pc.ProductCodeId, pc.Product_Code FROM Product_Code pc
WHERE SUBSTRING(pc.Product_Code, 1, <n>) = '<prefix>' AND pc.SiteId = <siteId>
```
*WHY:* find product codes sharing the first up-to-5 chars of the item's own code, for the programmatic transposition panel.

**Q-PROD-013** — component list for item (line 3096, `updateComponentList`):
```sql
SELECT itco.SubItemId, compitems.Item AS Item, itco.ComponentSequence AS Sequence,
       itco.Quantity, itco.SubItemId, pc.Product_Code, pc.Description, pc.ProductCodeId, itco.FeaturePositionString
FROM Item
CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x
INNER JOIN ItemComponents itco ON Item.ItemId = itco.ItemId
INNER JOIN Item compitems ON itco.SubItemId = compitems.ItemId
INNER JOIN Product ON compitems.ProductId = Product.ProductId
INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL
      THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId )
      ELSE Product.ProductCodeId END = pc.ProductCodeId
   AND pc.SiteId = <siteId>
WHERE itco.ItemId = <itemId>
ORDER BY convert(INT, itco.ComponentSequence)
```
*WHY:* list the components (with product code) of the selected SP item, ordered by numeric sequence. See Hidden Logic re `ProductCodeIdOverride`.

**Q-PROD-014** — update edited component (line 3771, `SubmitButton_Click`):
```sql
UPDATE ItemComponents SET SubItemId = <newSubItemId>, ComponentSequence = <seq>, Quantity = <qty>
WHERE ItemId = <itemId> AND SubItemId = <oldSubItemId>
```
**Q-PROD-015** — read sequence to normalise (line 3717/3774):
```sql
SELECT SubItemId, ComponentSequence FROM ItemComponents WHERE ItemId = <itemId>
ORDER BY CONVERT(INT, ComponentSequence)
```
**Q-PROD-016** — reassign sequence (line 3725/3791/3800/3810):
```sql
UPDATE ItemComponents SET ComponentSequence = <n> WHERE ItemId = <itemId> AND SubItemId = <subItemId>
```
*WHY:* keep `ComponentSequence` contiguous 1..N after an insert/edit.

**Q-PROD-018** — item lookup for add/replace (line 4035, `createNewItem`):
```sql
SELECT ItemId FROM Item WHERE /*IsSuperItem = 1 AND*/ Item = '<code>'
```
*WHY:* resolve the component item id (the `IsSuperItem = 1` restriction is commented out — see Hidden Logic).

**Q-PROD-019** — duplicate-component guard (line 4048):
```sql
SELECT ItemId FROM ItemComponents WHERE ItemId = <parentId> AND SubItemId = <subId>
```
**Q-PROD-020** — insert component (line 4058, add) / (line 4068, replace):
```sql
INSERT INTO ItemComponents (ItemId, SubItemId, Quantity, ComponentSequence)
VALUES (<parentId>, <subId>, <qty>, (dbo.fnGetSPComponentCount(<parentId>) + 1))   -- add path
-- replace path deletes ComponentSequence = <replace+1> then inserts at same sequence
```
*WHY:* append a component at the next free sequence via UDF `fnGetSPComponentCount`, or overwrite the sequence slot when replacing.

**Q-PROD-021** — read FeaturePositionString (line 4436/4642, `updateOptionList`/`applyFilterToComponents`):
```sql
SELECT FeaturePositionString FROM ItemComponents WHERE ItemId = <itemId> AND SubItemId = <subId>
```
**Q-PROD-022** — option name lookup (line 4461):
```sql
SELECT Name FROM [Option] WHERE OptionId = <optionId>
```
*WHY:* the `FeaturePositionString` is a pipe-delimited list of `OptionId`s by position; resolve names for display.

**Q-PROD-023** — feature-string write (line 4289 `submitFeatureString`, 4697 `applyFilterToComponents`):
```sql
UPDATE ItemComponents SET FeaturePositionString = '<pipe-string>' | NULL
[, Quantity = <qty>]                             -- only if check_qty.Checked (bulk apply)
WHERE ItemId = <itemId> AND SubItemId = <subId>  -- (single)
WHERE SubItemId = <subId> [AND ItemId IN (-1, ...)]   -- (bulk apply, filter)
```

**Q-PROD-024** — price-report component rows (line 5035, `generateXLSReport`):
```sql
SELECT item_comp.Item, pc.Product_Code, sp.Name,
  CASE WHEN pc.BasePriceRef = 1 THEN item_comp.BasePrice
       WHEN pc.BasePriceRef = 2 THEN item_comp.BasePrice2
       WHEN pc.BasePriceRef = 3 THEN item_comp.BasePrice3 END AS BasePrice,
  dbo.fnGetListPriceByItem(item_comp.Item, '<currency>', '<date>', <siteId>, NULL) AS ListPrice,
  itco.Quantity
FROM Item CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x
INNER JOIN Product sp ON Item.ProductId = sp.ProductId
INNER JOIN ItemComponents itco ON Item.ItemId = itco.ItemId
INNER JOIN Item item_comp ON itco.SubItemId = item_comp.ItemId
INNER JOIN Product ON item_comp.ProductId = Product.ProductId
INNER JOIN Product_Code pc ON <ProductCodeIdOverride CASE> = pc.ProductCodeId AND pc.SiteId = <siteId>
WHERE Item.Item = '<spItem>' ORDER BY itco.ComponentSequence
```
**Q-PROD-025** — price-report option increments (line 5052):
```sql
SELECT DISTINCT itov.OptionValueId, itco.Quantity AS Quauntity, opt.DisplayOrder, ov.DisplayOrdinal,
  Item.Item, ov.OrderCodeValue AS order_code, ov.OptionId,
  CASE WHEN pc.BasePriceRef = 1 THEN itov.IncrementalPrice ... END AS inc_price,
  CASE WHEN pc.BasePriceRef = 1 THEN dbo.fnGetListPrice('<cur>', itov.IncrementalPrice, pc.PriceCode, '<date>', 'DMY', pm.Rounding, <siteId>, NULL) ... END AS list_price
FROM ItemOptionValues itov CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x
INNER JOIN OptionValue ov ON itov.OptionValueId = ov.OptionValueId
INNER JOIN [Option] opt ON ov.OptionId = opt.OptionId
INNER JOIN ItemComponents itco ON itov.ItemId = itco.SubItemId
INNER JOIN Item ON itco.SubItemId = Item.ItemId
INNER JOIN Item parentitem ON itco.ItemId = parentitem.ItemId
INNER JOIN Product ON Item.ProductId = Product.ProductId
INNER JOIN Product_Code pc ON <override CASE> = pc.ProductCodeId AND pc.SiteId = <siteId>
INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode
INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode
WHERE parentitem.Item = '<spItem>' AND Item... AND Currency.Currency = '<cur>'
ORDER BY opt.DisplayOrder, ov.DisplayOrdinal
```
*WHY:* build a per-component base + list price and per-option increment table for the XLS report; list prices via UDFs `fnGetListPriceByItem` / `fnGetListPrice`. `BasePriceRef` (1/2/3) selects which of the three base/incremental price columns applies (BR-PROD-025).

**Q-PROD-026** — CSV download (line 5451, `downloadSPDefs`):
```sql
SELECT DISTINCT Item.Item, sub_item.Item AS comp, itco.Quantity AS qty,
  itco.FeaturePositionString AS feat, CONVERT(INT, itco.ComponentSequence)
FROM Item
INNER JOIN ItemComponents itco ON Item.ItemId = itco.ItemId
INNER JOIN Item sub_item ON itco.SubItemId = sub_item.ItemId
INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId AND ci.CatalogueId = <catalogueId>
INNER JOIN Product ON Item.ProductId = Product.ProductId
INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
WHERE pr.ProductCategoryId = <categoryId>
[UNION ... CatalogueItemsUnreleased ...]         -- only if URLExportCheck.Checked
ORDER BY Item.Item, CONVERT(INT, itco.ComponentSequence)
```

**Q-PROD-027** — CSV import resolution (lines 5788, 5815, 5837, 5891, 5903, 5907, `importSPDefs`):
```sql
SELECT ItemId FROM Item WHERE Item = '<item>'                    -- 5788 pre-check exists
SELECT ItemId, ProductId FROM Item WHERE Item = '<item>'         -- 5815 resolve SP parent
SELECT ItemId FROM Item WHERE Item = '<component>'               -- 5837 resolve component
DELETE FROM ItemComponents WHERE ItemId = <spId>                 -- 5891 wipe existing def
INSERT INTO ItemComponents (ItemId, SubItemId, Quantity, ComponentSequence, FeaturePositionString)
   VALUES (<spId>, <subId>, <qty>, <n+1>, <feat|NULL>)           -- 5903
UPDATE Product SET IsSuperProduct = 1|0 WHERE ProductId = <prodId>   -- 5907
```

**Q-PROD-030..034** — delete-component flow (`menuDeleteComponent_Click`, lines 4205–4234):
```sql
SELECT ItemId, ProductId FROM Item WHERE Item = '<code>' AND IsSuperItem = 1   -- 4205
SELECT COUNT(*) AS cnt FROM ItemComponents WHERE SubItemId = <itemId>          -- 4216
DELETE FROM ItemComponents WHERE SubItemId = <itemId>                          -- 4228
DELETE FROM Item WHERE ItemId = <itemId>                                       -- 4231
DELETE FROM Product WHERE ProductId = <productId>                              -- 4234
```
*WHY:* fully remove a Super-Item component (its `ItemComponents` links, its `Item`, and its `Product`) — but **only if it is a Super Item** (`IsSuperItem = 1`); if it also exists as a standard product the delete is refused (BR-PROD-041).

**Q-PROD-035** — recompute IsSuperProduct flag (line 4864, `updateSPFlag`):
```sql
SELECT DISTINCT Product.ProductId, Product.IsSuperProduct, COUNT(DISTINCT itco.ItemId) AS cnt
FROM Product
INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
INNER JOIN Item ON Product.ProductId = Item.ProductId
LEFT OUTER JOIN ItemComponents itco ON Item.ItemId = itco.ItemId
WHERE pr.ProductCategoryId = <categoryId>
GROUP BY Product.ProductId, Product.IsSuperProduct
-- then: UPDATE Product SET IsSuperProduct = <0|1> WHERE ProductId = <id>   (only where flag mismatched)
```
*WHY:* set `IsSuperProduct = 1` iff the product has ≥1 item with components, else 0 (BR-PROD-030).

**Q-PROD-036..038** — clone flow (`CloneButton_Click`, lines 5991–6152):
```sql
SELECT COUNT(*) AS cnt FROM Item WHERE (ItemId IN (SELECT ItemId FROM CatalogueItems WHERE CatalogueId = <cat>)
   OR ItemId IN (SELECT ItemId FROM CatalogueItemsUnreleased WHERE CatalogueId = <cat>)) AND (Item = '..' OR ...)  -- 5991 count
SELECT ItemId FROM Item WHERE Item = '<newItem>'                                          -- 6100
DELETE FROM ItemComponents WHERE ItemId = <newId>                                         -- 6113 (overwrite=Yes)
SELECT COUNT(*) AS cnt FROM ItemComponents WHERE ItemId = <newId>                         -- 6119 (overwrite=No check)
SELECT SubItemId, Quantity, ComponentSequence, FeaturePositionString FROM ItemComponents itco
   INNER JOIN Item ON itco.ItemId = Item.ItemId WHERE Item.Item = '<sourceItem>'
   ORDER BY CONVERT(INT, ComponentSequence)                                               -- 6134
INSERT INTO ItemComponents (ItemId, SubItemId, Quantity, ComponentSequence, FeaturePositionString)
   VALUES (<newId>, <subId>, <qty>, '<seq>', '<feat>')                                    -- 6150
```

**Q-PROD-039** — delete SP definition (line 4924, `DeleteButton_Click`):
```sql
DELETE FROM ItemComponents WHERE ItemId = <itemId>
```
*WHY:* remove all component rows (deletes the *definition* only; the parent item/product remain) then `updateSPFlag()`.

**Q-PROD-040** — bulk-apply candidate items (line 3882/3912/4761):
```sql
SELECT Item.ItemId, Item.Item FROM Item [INNER JOIN ItemComponents itco ...]
WHERE Item.ProductId IN (<all products in filter>) AND Item LIKE '%' ORDER BY Item
```

### SuperProductVarCondRelation.cs

**Q-PROD-002b/005b** — same catalogue + category loaders (lines 910, 956) as Q-PROD-002/005 but category query uses `DISTINCT` and **does not** apply the `NOT IN (1,128,129,999)` exclusion.

**Q-PROD-042** — SP items for price relations (line 1009, `updateItemList`):
```sql
SELECT Item.Item FROM Item
INNER JOIN Product ON Item.ProductId = Product.ProductId
INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId AND pr.ProductCategoryId = <cat>
INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId AND ci.CatalogueId = <cat>
WHERE Item.Item LIKE '<filter>%'
[UNION ... CatalogueItemsUnreleased ...]          -- only if UnreleasedCheck.Checked
ORDER BY Item.Item
```
*WHY:* build the `PA_<prefix>` relation list; prefix length driven by `num_prefix_length`.

**Q-PROD-043** — insert pCon relation (OleDb → MDB, line 1354):
```sql
INSERT INTO tCOMd_Relation (com_PackageID, com_RelationName, com_RelationBody)
VALUES (<pkgId>, '<PA_ref>', '<body>')
```
**Q-PROD-044** — resolve new relation id (line 1359):
```sql
SELECT com_RelationID FROM tCOMd_Relation
WHERE com_PackageID = <pkgId> AND com_RelationName = '<PA_ref>' AND com_RelationBody = '<body>'
```
**Q-PROD-045** — item note lookup for prefix length (SQL Server, line 1382):
```sql
SELECT Notes FROM Item WHERE Item = '<item>'
```
**Q-PROD-046** — master-item fallback note (line 1414):
```sql
SELECT DISTINCT Item.Item, Item.Notes FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId
WHERE '<item>' LIKE Product.Product + '%' AND Item.CADImage2D = 'master' ORDER BY Item.Item
```
**Q-PROD-047** — pCon rel-object linkage (OleDb, lines 1456, 1471, 1490):
```sql
SELECT com_RelObjID FROM tCOMd_RelObj WHERE com_PackageID = <pkgId> AND com_RelObjName = '<P_prefix>'
SELECT com_RelationOrder, com_RelationID FROM tCOMd_RelObjRel WHERE com_RelObjID = <relObjId>
INSERT INTO tCOMd_RelObjRel (com_RelObjID, com_RelationID, com_RelObjTypeCode, com_RelObjDomainCode, com_RelationOrder)
   VALUES (<relObjId>, <relationId>, 3, 'P', <maxOrder+10>)
```
**Q-PROD-048** — clear existing relations before export (line 1542, `ExportButton_Click`):
```sql
DELETE FROM tCOMd_Relation WHERE com_PackageID = <pkgId> AND com_RelationName LIKE 'PA_<filter>%'
```

---

## 5. Data Model

| Table | Key columns (used here) | Role |
|-------|-------------------------|------|
| `Product` | `ProductId` (PK), `Product`, `ProductRangeId` (FK→ProductRange), `ProductCodeId` (FK→Product_Code), `IsSuperProduct` (bit) | Product master; `IsSuperProduct` toggled by this module. |
| `ProductRange` | `ProductRangeId` (PK), `ProductCategoryId` (FK→ProductCategory) | Links product to category. |
| `ProductCategory` | `ProductCategoryId` (PK) | Category; some ids excluded (1,128,129,999). |
| `Item` | `ItemId` (PK), `Item`, `ProductId` (FK), `Status`, `IsSuperItem` (bit), `Notes`, `CADImage2D`, `BasePrice`/`BasePrice2`/`BasePrice3` | The configurable item (a "variant"). |
| `ItemComponents` | `ItemId` (parent, FK→Item), `SubItemId` (component, FK→Item), `Quantity`, `ComponentSequence`, `FeaturePositionString` | **The Super-Product BOM.** Composite (ItemId, SubItemId). |
| `Product_Code` | `ProductCodeId` (PK), `SiteId` (FK→Site), `Product_Code`, `Description`, `PriceCode`, `UnitCode`, `BasePriceRef`, `Truncation`, `OCDExport`, `Status` | Per-site product/order code (maintained in `06_Articles`). `BasePriceRef` ∈ {1,2,3}. |
| `Site` | `SiteId` (PK), `Site`, `Description` | Site; **site 20 excluded** from selector. |
| `Currency` | `Currency_ID` (PK), `Currency`, `PriceCode`, `Symbol` | Currency; joins `PriceMatrix.CustPriceCode`. |
| `Catalogue` | `CatalogueId` (PK), `Name`, `Status` | Catalogue; `Status = 1` = active. |
| `PDMUserCatalogues` | `UserId`, `CatalogueId`, `ReadOnly` | User↔catalogue with read-only flag. |
| `CatalogueProductCategories` | `CatalogueId`, `ProductCategoryId`, `DescriptionId`, `DisplayOrder` | Category ordering per catalogue; `DisplayOrder = -1` → sorted last. |
| `CatalogueItems` / `CatalogueItemsUnreleased` | `CatalogueId`, `ItemId` | Released vs unreleased item membership. |
| `BaseAttributeValues` / `CatalogueAttributeValues` | `ItemId`, `AttributeValueId` | Attribute joins used to constrain items to valid catalogue attributes. |
| `[Option]` | `OptionId` (PK), `Name`, `ProductCategoryId`, `DisplayOrder`, `HideByDefault` | Feature/Option; `HideByDefault` doubles as a *linked option id* pointer (see Hidden Logic). |
| `OptionValue` | `OptionValueId` (PK), `OptionId`, `DisplayOrdinal`, `OrderCodeValue` | Option values. |
| `ItemOptionValues` | `ItemId`, `OptionValueId`, `IncrementalPrice`/`2`/`3` | Per-item option pricing. |
| `PriceMatrix` | `ItemPriceCode`, `CustPriceCode`, `Rounding` | Price/rounding matrix for list-price calc. |
| `OtherDescription` | `DescriptionId`, `LanguageId`, `ShortDescription` | Localised descriptions (`LanguageId=1` English). |
| `tCOMd_Relation`, `tCOMd_RelObj`, `tCOMd_RelObjRel` | `com_PackageID`, `com_RelationID`, `com_RelObjID`, `com_RelationName`, `com_RelationBody`, `com_RelationOrder`, `com_RelObjTypeCode`, `com_RelObjDomainCode` | **pCon commerce (OCD) MDB** tables (Jet/OleDb), price-relation export target. |
| Stored proc `PDMOptionDataReport` | `@cataloguedesc` | Returns option set (`OptionId`, `Option2`) for an SP item. |
| Stored proc `GetProductOptionCount` | `@product`, `@optcount OUT` | Option count (used by OCDExport, referenced here indirectly). |
| UDFs | `fnGetSPComponentCount(itemId)`, `fnGetListPriceByItem(...)`, `fnGetListPrice(...)` | Component count; list-price calculations. |

**Status / flag meanings:**
- `Item.Status`: `1` = released, `0` = unreleased (per released/unreleased catalogue tables).
- `Catalogue.Status`: `1` = active (only these listed).
- `Product.IsSuperProduct`: `1` = has component definition, `0` = not.
- `Item.IsSuperItem`: `1` = a super-item component (deletable via delete-component flow).
- `PDMUserCatalogues.ReadOnly`: `0` = editable, non-zero = read-only (**inverted-feel**, but here `0`=editable is checked directly — see BR-PROD-005).
- `Product_Code.BasePriceRef`: `1|2|3` selects `BasePrice`/`BasePrice2`/`BasePrice3` and `IncrementalPrice`/`2`/`3`.
- `FeaturePositionString`: `"<optId>|<optId>||<optId>|"` — pipe-delimited option ids, position = slot index; empty slot = `||`; must end with `|`.

---

## 6. Business Rules

### Catalogue / Site / Category / Product selection
- **BR-PROD-001** Only catalogues where `PDMUserCatalogues.UserId = current user` AND `Catalogue.Status = 1` are shown, ordered by name (Q-PROD-002).
- **BR-PROD-002** On load, the catalogue selector defaults to `AuthenticateUser.DefaultCatalogueId` if the user is assigned to it; otherwise index 0 (`initialiseArrays`).
- **BR-PROD-003** Site selector defaults to `AuthenticateUser.DefaultSiteId` if present, else index 0. Currency selector defaults to `AuthenticateUser.DefaultCurrencyId` if present, else index 0.
- **BR-PROD-004** A `KeyPress` handler sets `e.Handled = true` on the site combo so the user cannot type into it (`siteselector_KeyPress`, line 4262). (Same pattern in `ProductCodeEntry`.)
- **BR-PROD-005** *Read-only rule:* `catalogueIsReadOnly()` returns `false` (editable) **only if** the selected catalogue's cached `ReadOnly == 0` **AND** `Global.readOnlyDBConnection` is false; otherwise the catalogue is treated as read-only (line 2511).
- **BR-PROD-006** When the catalogue is read-only: `LandscapeButton`, `CloneButton`, `DeleteButton` disabled and the Excel-import icon hidden; otherwise enabled (`catalogue_selector_SelectedIndexChanged`).
- **BR-PROD-007** Site `SiteId = 20` is hard-excluded from the site list (Q-PROD-003). `UNKNOWN`: business meaning of site 20.
- **BR-PROD-008** Categories `1, 128, 129, 999` are hard-excluded from the category list in `SuperProductMaintenance` (Q-PROD-005). (In `SuperProductVarCondRelation` this exclusion is **not** applied — Q-PROD-005b.)
- **BR-PROD-009** Category display order uses `CASE WHEN cpc.DisplayOrder = -1 THEN 9999` so unordered categories sort last (Q-PROD-005/005b).
- **BR-PROD-010** Duplicate category short-descriptions are disambiguated by appending `" (<ProductCategoryId>)"` (`updateCatalogueList`).
- **BR-PROD-011** Category selector auto-selects index 0 after (re)loading categories.
- **BR-PROD-012** Only English descriptions are loaded for categories (`od.LanguageId = 1`).

### Product / item filtering
- **BR-PROD-013** Product filter matches on either `Product LIKE '%<filter>%'` (uppercased) **OR** `'<filter>' LIKE Product + '%'` (prefix), across released and unreleased items (Q-PROD-007).
- **BR-PROD-014** Products appearing in both released and unreleased sets are de-duplicated, preferring the released (`Status = 1`) row via `ORDER BY ... Status DESC` + `Items.Contains` guard.
- **BR-PROD-015** `NonSuperCheck` restricts the product list to products that already have components (adds `INNER JOIN ItemComponents`).
- **BR-PROD-016** After filtering, if the trimmed filter is non-empty, the first product whose name contains the filter, or which is a prefix of the filter, is auto-selected (loop after Q-PROD-007). `UNKNOWN`: exact auto-select index resolution beyond first match.
- **BR-PROD-017** `HideCheck` restricts the item list to items that already have components; `URLCheck` restricts to released items (`Item.Status = 1`) (Q-PROD-009).
- **BR-PROD-018** `product_filter` text additionally filters items via `Item LIKE '%<filter>%'` (Q-PROD-009).
- **BR-PROD-019** After loading items, index 0 is auto-selected and its option list / feature count refreshed.

### Component definition (BOM)
- **BR-PROD-020** Component list is ordered by numeric sequence (`CONVERT(INT, ComponentSequence)`), not string (Q-PROD-013).
- **BR-PROD-021** Component product code is resolved for the current site; if `Item.ProductCodeIdOverride` were non-null it would override the product's default code — but the override is fed a constant `NULL` (see BR-PROD-047 / Hidden Logic).
- **BR-PROD-022** *Duplicate guard on submit:* a component (SubItemId) cannot appear twice in the same SP definition; submit is rejected with a message identifying the existing sequence (`SubmitButton_Click`, line 3760).
- **BR-PROD-023** On submit, after updating the edited component, sequences are normalised to a contiguous 1..N ordering (Q-PROD-015/016 resequencing loop).
- **BR-PROD-024** New components are appended at `ComponentSequence = fnGetSPComponentCount(parent) + 1` (Q-PROD-020, add path).
- **BR-PROD-025** A component item can only be **added** if it already exists as a standalone `Item` (Q-PROD-018); if not found, the add is refused with *"Please ensure this configuration exists as a stand-alone Product … mandatory for Parametric BOMs"* (line 4075).
- **BR-PROD-026** Add-existing is skipped if the parent already links that component (duplicate guard Q-PROD-019).
- **BR-PROD-027** *Replace* deletes the existing row at `ComponentSequence = replace+1` then inserts the replacement at the same sequence (Q-PROD-020 replace path).
- **BR-PROD-028** *Multiple add/replace* presents an `AddNewData` multi-select dialog listing candidate items for the current products (Q-PROD-040); a confirmation is shown when >1 component will be added.
- **BR-PROD-029** Delete of a single component removes the `ItemComponents` row (`ItemId`+`SubItemId`), then refreshes the SP flag (`menuRemoveComponent_Click`, line 4149).

### IsSuperProduct flag maintenance
- **BR-PROD-030** `updateSPFlag()` sets `Product.IsSuperProduct = 1` for every product in the category that has ≥1 item with components, and `= 0` otherwise — but only issues an `UPDATE` where the current flag disagrees (Q-PROD-035).
- **BR-PROD-031** `updateSPFlag()` runs after add/replace/delete-component, import, and delete-definition operations, and re-selects the previously selected item afterwards.

### Options / FeaturePositionString
- **BR-PROD-032** The parent SP item's available options come from stored proc `PDMOptionDataReport` (Q-PROD-010), cached statically per item to avoid repeat calls (`updateSPOptionList`, `getFeatureCount`).
- **BR-PROD-033** `pos_num.Maximum` is set to the parent's feature count (min 1) — you cannot assign a component option to a position beyond the parent's feature count (`updateFeatureCount`).
- **BR-PROD-034** The `FeaturePositionString` is built by iterating positions 1..max: each position holds the mapped option id or is blank (`|`); positions must be contiguous and terminated with `|` (`submitFeatureString`).
- **BR-PROD-035** Adding an option appends it at position `last+1`; options are re-sorted and the feature string rewritten (`menuAddOption_Click` → `submitFeatureString`).
- **BR-PROD-036** Removing an option removes its `option_list` / `_optionIdList` / `pos_list` entries in lockstep and rewrites the feature string (`menuRemoveOption_Click`).
- **BR-PROD-037** Changing a position value triggers `reorderOptionList()` which re-sorts by position and rewrites the feature string, then re-selects the moved option (`pos_num_ValueChanged`).
- **BR-PROD-038** *Feature-position string validation* (`featurePositionStringValid`, line 5609): valid only if it contains **only** the chars `|0123456789`, contains at least one digit, and **ends with `|`**. Used during import to reject/ignore malformed feature strings.
- **BR-PROD-039** Bulk *Apply to all* (`applyFilterToComponents`): finds all components matching `opt_filter` (`Item LIKE '<filter>'`), optionally restricted to selected parent items, and copies the current feature string (and optionally quantity if `check_qty`) to every matching `ItemComponents.SubItemId` (Q-PROD-021/022/023). Confirms the affected-count first; refuses if none match.
- **BR-PROD-040** The bulk apply uses `AND ItemId IN (-1, ...)` — the seed `-1` guarantees valid SQL when no parent items are chosen (empty selection safely matches nothing extra).

### Delete
- **BR-PROD-041** *Delete component (across catalogues):* only allowed when the component resolves as `IsSuperItem = 1` (Q-PROD-030). It reports how many SP definitions reference it (Q-PROD-031), and on confirmation deletes its `ItemComponents`, its `Item`, and its `Product` (Q-PROD-032/033/034). If it is **not** a super item, it is refused: *"This component cannot be deleted - it also exists as a standard product!"* (line 4243).
- **BR-PROD-042** *Delete SP definition* (`DeleteButton_Click`) requires Yes confirmation, then deletes all `ItemComponents` for the item (Q-PROD-039) and recomputes the flag; the item/product themselves are kept.

### Import / Export / Clone
- **BR-PROD-043** CSV **export** writes one row per SP item with up to `maxComponents = 20` (Component/Qty/Features triples); shorter definitions are right-padded with empty triples (`downloadSPDefs`). Optionally includes unreleased items (`URLExportCheck`).
- **BR-PROD-044** CSV **import** (`importSPDefs`): the literal first cell `"Super Product"` marks a header row and is skipped; up to `maxComponents` component triples are parsed per line.
- **BR-PROD-045** Import special-cases component codes starting with `"MEH"`: a trailing `"01"` or `"02"` is stripped (line 5745).
- **BR-PROD-046** Import treats a feature cell of `"Y"` as empty; and codes `"MEHB.0000"` / `"MEHB.000000"` are accepted as blank-quantity placeholders (no warning) (lines 5723, 5764).
- **BR-PROD-047** Import validates each feature string with `featurePositionStringValid`; invalid ones are logged and blanked, not imported (line 5729).
- **BR-PROD-048** Import is **all-or-nothing per pre-check**: if any SP parent item cannot be resolved (Q-PROD-027 @5788), the whole import is aborted and the unresolved items listed (`flag2 = false`).
- **BR-PROD-049** During commit, an unresolved *component* prompts an abort-or-continue dialog; quantities must be positive integers (else abort prompt); `MEHB.0000/000000` components are skipped silently (lines 5860–5920).
- **BR-PROD-050** Import replaces a definition wholesale: `DELETE FROM ItemComponents` then re-`INSERT` all rows with contiguous `ComponentSequence = n+1`, then sets `IsSuperProduct = 1` if ≥1 component was written else `0` (Q-PROD-027).
- **BR-PROD-051** **Clone** (`CloneButton_Click`) reads a CSV of `existing_SP_item,new_SP_item` pairs; only items belonging to the **selected catalogue** are eligible (Q-PROD-036 counts catalogue membership).
- **BR-PROD-052** Clone batches the existence-count SQL every 1000 rows (`arrayList3.Count % 1000 == 0`) to avoid oversized `OR` chains.
- **BR-PROD-053** Clone offers *overwrite all* (Yes) / *skip existing* (No) / Cancel. With No, a target that already has a definition is skipped and logged; with Yes its existing components are deleted first (Q-PROD-037/038).
- **BR-PROD-054** Clone logs per-item exceptions (source has no definition / target missing / target already defined) and truncates the displayed list to 10 (+ "and N others").

### Price report
- **BR-PROD-055** The XLS price report requires a selected item **with at least one component**; otherwise *"Please select a super product to export a price report"* (line 4965).
- **BR-PROD-056** Report file name = `<siteCode-lower>_<currency>_<item with '.'→'_' and '/'→'-'>.xlsx`, written to `C:\Temp` (created if missing) else `U:\Temp` (line 4972+).
- **BR-PROD-057** Report prices use `BasePriceRef` to pick `BasePrice`/`BasePrice2`/`BasePrice3` and the matching incremental columns; list prices via `fnGetListPriceByItem` / `fnGetListPrice` at the `dtp` date (Q-PROD-024/025, BR-PROD-025 pricing selector).
- **BR-PROD-058** The report builds an Excel SUM formula over component list-prices × quantities in the total cell (`text10` formula construction).

### Validation & unsaved-change guard
- **BR-PROD-059** `validateSPs` runs a background `ValidateThread` over the current category; if the product filter is `*` or empty it validates all, otherwise only the filtered products. It optionally validates feature-position/option counts (Yes/No prompt).
- **BR-PROD-060** *Unsaved-change guard* (`DiscardChanges`, line 3662): when a definition is modified and not yet submitted, changing catalogue/site/product/item prompts *"discard the changes?"*; choosing No reverts the selector to the previous index and sets the label to `*Submission Required*` / `<Preserving Changes>`.

### VarCond price relations (SuperProductVarCondRelation)
- **BR-PROD-061** Relation names are `"PA_" + <item prefix>`; the prefix length is `num_prefix_length` (items shorter than the value keep their full code) (`updateItemList`).
- **BR-PROD-062** Relation list is de-duplicated (`!list_relations.Items.Contains`).
- **BR-PROD-063** Text-filter changes debounce via a 1500 ms `DelayThread` before refreshing (`text_filter_TextChanged`).
- **BR-PROD-064** Export is enabled only when `text_relation` is non-empty **and** there is no warning text (`updateExportButtonState`).
- **BR-PROD-065** Export target MDB path = `<pConPath>WS\<workspace(catalogue)>\pcr_data_com_ocd.mdb` via `Microsoft.Jet.OLEDB.4.0` (`exportPendingRelations`, `ExportButton_Click`).
- **BR-PROD-066** Before export, existing `PA_<filter>%` relations for the package are deleted (Q-PROD-048).
- **BR-PROD-067** For each relation, the rel-object name is `"P_" + <derived prefix>`; items starting with `"RY3X"` or `"RYCX"` use only the first 5 chars (`"P_" + text2.Substring(0,5)`) (line 1436+).
- **BR-PROD-068** The relation-order for a new `tCOMd_RelObjRel` row = `max(existing order, seeded 90) + 10`, with fixed `com_RelObjTypeCode = 3`, `com_RelObjDomainCode = 'P'` (Q-PROD-047).
- **BR-PROD-069** The item's `Notes` field first token (before a comma), if an integer, is used as the prefix length for the relation object code (Q-PROD-045); falls back to the `CADImage2D = 'master'` item's notes (Q-PROD-046), then to the raw prefix.
- **BR-PROD-070** Config **save/load** (`SaveButton_Click`/`LoadButton_Click`) persists `<subs>`/`<exclusions>` blocks to a `.cfg` file named after the category (+ filter), only if subs/exclusions are non-empty.

---

## 7. Hidden Logic / Magic Numbers

- **`evalulateQuantity(string)` is dead code** (line 5201): its `try` body is empty; it **always returns 1** regardless of input, and swallows nothing. Any quantity-from-expression feature (`char_list`, `ExpText`, programmatic qty=0 path at line 4019) therefore silently yields quantity 1. **Tech debt / latent bug.**
- **`ProductCodeIdOverride` is a hardcoded `NULL`**: queries Q-PROD-013/024/025 `CROSS JOIN (SELECT NULL AS ProductCodeIdOverride) x` and a correlated `CASE` that reads `Item.ProductCodeIdOverride`. As written the cross-joined constant is `NULL`, so the override branch is effectively inert — a stubbed extension point.
- **Hardcoded option ids** in `menuAddOption_Click` appended to the "show all" list (line ~4360): `3344` (Internal fabric type), `3346` (Internal fabric colour), `8` (Fabric type), `28` (Fabric colour), `6790` (Tertiary fabric type), `6791` (Tertiary fabric colour), `1142` (Finish MM-FLAP01).
- **`HideByDefault` doubles as a linked-option pointer**: `updateOptionRefs` (Q at line 2967) treats a positive `[Option].HideByDefault` value as *another OptionId* ("LinkedId"), not a boolean — a semantic overload.
- **`maxComponents = 20`** hardcoded (set at line 1692) — caps CSV import/export component columns.
- **Prefix substring `5`** hardcoded for programmatic product-code matching (Q-PROD-012, `num = 5`).
- **`-1` seed in `IN (-1, ...)`** lists (bulk apply, Q-PROD-040) — sentinel to keep SQL valid on empty selections.
- **Commented-out `IsSuperItem = 1`** filter in Q-PROD-018 (`/*IsSuperItem = 1 AND*/`) — a relaxed lookup; any item with the code matches, not just super items.
- **`MEH` / `MEHB.0000(00)` special codes** — vendor-specific product code handling in import (BR-PROD-045/046).
- **Fixed pCon literals**: `com_RelObjTypeCode = 3`, `com_RelObjDomainCode = 'P'`, order seed `90`, increment `10` (Q-PROD-047).
- **`RY3X` / `RYCX` prefixes** get 5-char truncation in VarCond (BR-PROD-067).
- **Temp dirs `C:\Temp` then `U:\Temp`** hardcoded for the XLS report.
- **`GetProductOptionCount` output param** default value string `"1.0"` passed to `SqlParameter` (cosmetic; ADO ignores).
- **`Interaction.InputBox` component entry** strips backticks and single-quotes and upper-cases input (`createNewItem`, line ~3865) — a crude injection/format guard.

---

## 8. UI Behaviour

- **Load order:** `SuperProductMaintenance_Load` only adds toolbar controls; the real data load is `initialiseArrays()` (catalogue→site→currency→component list), then cascades catalogue→category→product→item→component→option via `SelectedIndexChanged` handlers.
- **Refresh triggers:** changing catalogue reloads categories + edit-gating; changing category reloads options + product list; changing product reloads items; changing item reloads components + programmatic panel + feature count + product-code list; changing component reloads option list.
- **Selection defaults:** each list auto-selects index 0 after loading (categories, items, components, options).
- **Enable/disable:** `setComponentControls()` disables all component/option editors when no component is selected, multiple products/items are selected, the catalogue is read-only, or the item list is empty. `ApplyAllCompButton` is enabled only when `opt_filter` has text.
- **Read-only feedback:** on a read-only DB connection the form title gains `"   (read only)"`; context-menu items and pcode combo are disabled per `catalogueIsReadOnly()`.
- **Modified-state label:** `RequiredLabel` shows `*Submission Required*` while a definition is dirty; `<Preserving Changes>` transient during a reverted selector change; the Submit button is enabled only while dirty.
- **Cursor:** long queries (`updateProductList`, `updateItemList`, `updateCatalogueList`, clone, import) set `Cursors.WaitCursor` and restore in `finally`.
- **Background work:** validation (`ValidateThread`) and VarCond generation (`VarCondThread`) run on worker threads and marshal status text back via `updateStatusEvent`/`Invoke`; the validate button shows live status and shrinks its font.
- **VarCond form:** `lockControls()`/`releaseControls()` disable the whole panel during export; a debounced filter refreshes the relation list.

---

## 9. Dependencies

- `ConnectionFactory.CreateNewConnection(autoOpen)` — SQL Server connection (foundation fact).
- `AuthenticateUser` — `UserId`, `DefaultCatalogueId/SiteId/CurrencyId`, `PDMAdministrator`, and the `SuperProductMaintenance` permission flag.
- `Global.readOnlyDBConnection` — global read-only gate.
- `CADMaintenance` — `pConPath`, `pConWorkspace`, `getPConWorkspace()`, `GetPconPackageIdOnly()`, `isInteger()`, `delayedRequestId`, `isInteger` (shared static helpers).
- Threads: `ValidateThread`, `VarCondThread`, `DelayThread`.
- Dialog forms: `AddNewData`, `AddDataList`, `debug_form`, `GetImage`.
- `Microsoft.Office.Interop.Excel` — XLS price report generation (COM automation).
- `System.Data.OleDb` + `Microsoft.Jet.OLEDB.4.0` — pCon MDB access (VarCond export).
- Stored procs `PDMOptionDataReport`, `GetProductOptionCount`; UDFs `fnGetSPComponentCount`, `fnGetListPriceByItem`, `fnGetListPrice`.
- Consumers of the SP definition: `OCDExport.cs` (article/OFML generation — see `06_Articles.md`).

---

## 10. Risks

- **SQL injection (high):** every query is string-concatenated with user/data values (item codes, filters, CSV cell contents) directly into SQL. Import/clone read arbitrary CSV cells straight into `SELECT`/`INSERT` text. Only crude `'`/backtick stripping in a few spots.
- **No transactions:** multi-statement flows (import delete+insert, delete-component across 3 tables, resequencing, clone) run as independent auto-committed commands on one connection; a mid-flow failure leaves partial state (orphaned `ItemComponents`, half-imported definitions, wrong `IsSuperProduct`).
- **Dead `evalulateQuantity`:** quantity-from-expression always returns 1 — silent data quality bug for any feature relying on it.
- **Inert `ProductCodeIdOverride`:** the override mechanism is stubbed to `NULL`; any expectation that per-item code overrides apply is unmet.
- **Cross-catalogue deletes:** delete-component removes `Item`/`Product` globally ("Removes across all Catalogues/Sites" per menu text) — irreversible and catalogue-agnostic despite the catalogue-scoped UI.
- **Excel COM automation:** requires desktop Excel; leaks COM objects if exceptions bypass the `finally` release; writes to hardcoded `C:\Temp`/`U:\Temp` and uses the clipboard (`Clipboard.SetDataObject`) — brittle and machine-specific.
- **Jet/OLEDB dependency:** `Microsoft.Jet.OLEDB.4.0` is 32-bit-only and deprecated; VarCond export writes into a shared `.mdb` with no locking/transaction safety.
- **Category/site magic exclusions** (1,128,129,999 / site 20) are undocumented; a data reorg could silently hide or expose categories.
- **`IsSuperProduct` drift:** the flag is only reconciled for the current category when an edit occurs; categories never opened can hold stale flags.
- **Import abort semantics:** partial commits are possible because the pre-check (all parents resolvable) and the component-level abort are evaluated at different stages with per-row commits.
- **Silent swallowing:** most handlers wrap in `try/catch` → `MsgBox(ex.ToString())`; failures are shown but not logged/rolled back, and cached option data (`cachedOptData*`) is never invalidated within a session (stale option lists after edits).
