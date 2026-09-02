# 22 — Export & Import Pipelines
**Module prefix:** BR-EXP
**Primary legacy source:** SytelineExport.cs, ExportThread.cs, OFDAExport.cs, OFDAExportManager.cs, SytelineCSIExport.cs, SytelineBOMExport.cs, SyteLineExportValidator.cs, SIFExport.cs, SIFExportThread.cs, SIFImport.cs, BOMExport.cs, ClippingsExport.cs, ScheduleExport.cs, ExportQueueManager.cs, ExportDPSDB.cs, ExportDPSDBThread.cs, SDXmlExport.cs, MainMenu.cs (menu triggers)
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

This module documents every **outbound data-export pipeline** and **inbound
data-import pipeline** in legacy PDM. PDM is a Product Data Management hub: the
authoritative catalogue/pricing/option data lives in the PDM SQL database, and
this module ships that data out to the downstream systems that actually sell,
plan and manufacture the furniture, and pulls supplier/OFDA data back in.

The pipelines fall into these families:

| Family | Consumer / purpose | Output format |
|---|---|---|
| **SL8 export** | SyteLine 8 ERP item/BOM load | `.xls` (tab-delimited) + helper files |
| **millerCAD (ASC)** | legacy CAD item/material load | `b-*.asc` / `o-*.asc` |
| **CSI export** | SyteLine CSI configurable-item load | multiple `.csv` files |
| **OFDA export** | CET Designer / OFDA planning tool | OFDA-XML |
| **PBOM material export** | production BOM analysis | `PDM_material_export.csv` (`;`-delimited) |
| **Item price export** | price extract (see [18_Pricing.md](18_Pricing.md)) | `PDM_item_price_export.csv` |
| **SIF export** | OFDA/DPS SIF option catalogue | `.top` / `.key` / `.opt` |
| **SIF import / PIP / OFDA import** | pull supplier fabric/option data into PDM | writes to PDM DB |
| **Financial / price-band export** | ad-hoc financial data dumps | `.txt` (tab-delimited) |
| **Static-data XML export** | site / rate / product-code / formula dump | `.xml` |
| **Clippings export** | *(ORPHANED — see §7)* | XML |
| **DPSDB publication** | detach/copy the published `DPSDB` database | `.MDF` / `.LDF` + `change_log.txt` |
| **Scheduled export** | queue products for later SL export | `ExportSchedule` table rows |

The OCD export (`OCDExport.cs`) is documented separately in
[21_OCD.md](21_OCD.md) and is itself orphaned in this build.

---

## 2. Entry Points

All export/import entry points are reached from the main menu
([MainMenu.cs](../../../Users/siaoca/Desktop/PDM/PDMMaintenance/MainMenu.cs)).

| Trigger | Handler | Permission gate | Launches |
|---|---|---|---|
| **"Export PDM Data"** button (`SLExportButton`) | `SLExportButton_Click` (MainMenu.cs:2761) | `AuthenticateUser.SytelineExport` (MainMenu.cs:3037) | `SytelineExport` form |
| **"PDM Data Import"** button (`PDMImportButton`) left-click | `PDMImportButton_Click` (MainMenu.cs:3886) | `AuthenticateUser.PDMImport & connectedServer !contains "eoscloud"` (MainMenu.cs:3097) | `SIFImport` form |
| **"PDM Data Import"** button right-click (user `dbacw8`) | `PDMImportButton_Click` (MainMenu.cs:3892) | hard-coded to user `dbacw8` | `importSytelineCSIData()` (import Syteline→CSI) |
| **Tools ▸ "Export Financial Data"** | `ExportFinanicalDataToolStripMenuItem_Click` (MainMenu.cs:4115) | *(menu visibility only)* | inline `.txt` writer |
| **Tools ▸ "Export Price Band Data"** | `ExportPriceBandDataToolStripMenuItem_Click` (MainMenu.cs:4259) | *(menu visibility only)* | inline `.txt` writer |
| **Tools ▸ "Import Materials in to CSI"** | `ImportMaterialsInToCSIToolStripMenuItem_Click` (MainMenu.cs:5090) | enabled only if `AuthenticateUser.CoreMaintenance` (MainMenu.cs:3087); code body additionally requires user `dbacw8` | `BOMExport.ResolveCriteria` (`=IF()` parser) |
| **Static Data Maintenance ▸ XML export** | `okButton_Click` (SDXmlExport.cs:250) | via `StaticDataMaintenance` (StaticDataMaintenance.cs:4853) | `SDXmlExport` form |
| **Publish Database** | `ExportDPSDB` (PublishDatabase.cs:398) | via `PublishDBButton` (`DatabasePublication` + primary DB) | `ExportDPSDB` / `ExportDPSDBThread` |

Within the **`SytelineExport`** form, the single **`ExportButton_Click`**
(SytelineExport.cs:5459) dispatches on the active tab:

| `TabControl1.SelectedIndex` | Method | Output |
|---|---|---|
| 0 | `ExportSL8Data(syteline:true,…)` (SytelineExport.cs:3604) | `PDMExport.xls` / `PDMItemReport.xls` / `b-<site><ccy>.asc` |
| 1 | `ExportCSIData()` (SytelineExport.cs:3865) | `PDMExport_CSI.csv` (+ satellites) |
| 2 | `ExportOFDA()` (SytelineExport.cs:4102) | `PDMExport_OFDA.xml` |
| 3 | Item-Price or PBOM-Material branch (SytelineExport.cs:5526) | `PDM_item_price_export.csv` / `PDM_material_export.csv` |

The form's **scheduler** button (`button_scheduler_Click`, SytelineExport.cs:6652):
for user `dbacw8` it opens `SIFExport` (SIF `.top` export); for every other user
it opens `ScheduleExport` (queue for later).

---

## 3. Call Hierarchy

```
MainMenu (Form)
├─ SLExportButton_Click ─────────────► SytelineExport (Form)
│    └─ ExportButton_Click (tab dispatch)
│        ├─ tab0 ExportSL8Data ──► ExportThread.initThread ──► new Thread(expThread.execThread)
│        │                             └─ SQL (Item/ItemComponents/Price…) ──► StreamWriter .xls/.asc + helper files
│        │        └─ (BOM branch) ──► SytelineBOMExport (ExportThread.cs:7022)
│        ├─ tab1 ExportCSIData ──► SytelineCSIExport.initParams ──► new Thread(csiThread.execThread)
│        │                             └─ SQL ──► StreamWriter *_items.csv / *_product_items.csv /
│        │                                        *_phantom_items.csv / *_item_price.csv /
│        │                                        *_materials.csv / *_current_materials.csv
│        ├─ tab2 ExportOFDA ──► ofdaThread.initParams ──► new Thread(ofdaThread.execThread)   [OFDAExport]
│        │                             └─ initArrays → per-item SQL + PDMOptionDataReport + fnGetListPrice
│        │                                ──► writeXmlDataFile (StreamWriter) ──► PDMExport_OFDA_latest.xml
│        └─ tab3 ├─ ItemPriceExport.ExportItemPrices ──► PDM_item_price_export.csv   (see 18_Pricing)
│               └─ BOMExport.ExportMaterials ──► SyteLine-live SQL + PDM SQL ──► PDM_material_export.csv
│    └─ button_scheduler_Click
│        ├─ (dbacw8) SIFExport.StartExport ──► SIFExportThread.execThread ──► .top/.key/.opt
│        └─ (else)   ScheduleExport (Form) ──► INSERT/DELETE ExportSchedule
│
├─ PDMImportButton_Click ────────────► SIFImport (Form)
│    └─ button_import_update_Click ──► StreamReader(.top/.sif) | Excel/XML(PIP/OFDA)
│        └─ createOption ──► INSERT [Option] / OptionValue / ItemOptionValues (+ UPDATE ProductRange, CatalogueProductCategories)
│
├─ ExportFinanicalDataToolStripMenuItem_Click ──► inline SQL ──► StreamWriter *_PLC/_PM/_PF .txt
├─ ExportPriceBandDataToolStripMenuItem_Click ──► inline SQL ──► StreamWriter .txt
├─ ImportMaterialsInToCSIToolStripMenuItem_Click ──► BOMExport.ResolveCriteria (=IF() parser)
│
StaticDataMaintenance ──► SDXmlExport.okButton_Click ──► XmlTextWriter ──► .xml
PublishDatabase ──► ExportDPSDB ──► ExportDPSDBThread.execThread ──► DTS package + sp_detach_db/sp_attach_db + File.Copy
```

Every long-running export runs on its **own worker thread** (`*Thread.cs` or the
form's `execThread`) so the UI stays responsive; progress is reported back via
`UpdateStatusLabel` / `UpdateStatusText` / `UpdateExportTimer` events.

---

## 4. SQL Analysis

SQL throughout this module is **inline string-concatenation** (SQL-injection
exposure — see §10). Representative queries (the OFDA/CSI/SL8 workers each issue
dozens of per-item queries; a full enumeration is beyond the coverage limits
noted in §10, but the load-bearing queries are captured here).

**Q-EXP-001** — Financial export, Product-Code sheet (MainMenu.cs:4201):
```sql
SELECT pc.ProductCodeId, pc.Product_Code, pc.Description, pc.PriceCode, pc.UnitCode, pc.BasePriceRef, Site.Site
FROM Product_Code pc INNER JOIN Site ON pc.SiteId = Site.SiteId
WHERE Site.SiteId = <n> ORDER BY pc.Product_Code
```
WHY: dumps the product-code → price/unit/base-price mapping for a chosen site.

**Q-EXP-002** — Financial export, Price-Matrix sheet (MainMenu.cs:4213):
```sql
SELECT pm.PriceMatrixId, pm.CustPriceCode, pm.ItemPriceCode, pm.PriceFormula, pm.Rounding, pm.MidpointRounding
FROM PriceMatrix pm INNER JOIN Product_Code pc ON pm.ItemPriceCode = pc.PriceCode
WHERE pc.SiteId = <n> ORDER BY pm.ItemPriceCode, pm.CustPriceCode
```
WHY: exports the customer-price × item-price → formula matrix for the site.

**Q-EXP-003** — Financial export, Price-Formula sheet (MainMenu.cs:4225):
```sql
SELECT pf.PriceFormulaId, pf.PriceFormula, pf.FirstPrice, Site.Site, pf.EffectiveDate, pf.DomCurrCode
FROM PriceFormula pf INNER JOIN Site ON pf.SiteId = Site.SiteId
WHERE Site.SiteId = <n> ORDER BY pf.PriceFormula, pf.EffectiveDate
```
WHY: exports uplift factors (`FirstPrice`) per formula/effective-date.

**Q-EXP-004** — Price-band export (MainMenu.cs:4269):
```sql
SELECT DISTINCT optval.Name, optval.OrderCodeValue, fb.PriceBand, fb.Application AS SiteId
FROM OptionValue optval INNER JOIN FabricBands fb ON optval.OptionValueId = fb.OptionValueId
WHERE optval.status < 2 ORDER BY fb.Application, fb.PriceBand, optval.OrderCodeValue
```
WHY: exports fabric price-band membership; `status < 2` = only URL(0)/ACT(1) option
values (excludes OBS(2)/HLD(3)). `fb.Application` doubles as the site key.

**Q-EXP-005** — SL8 export, price-formula helper (ExportThread.cs:1002):
```sql
SELECT Site.Site, pm.CustPriceCode, pm.ItemPriceCode, pf.PriceFormula, pf.FirstPrice,
       CONVERT(VARCHAR(11), pf.EffectiveDate, 106) AS EffDate
FROM PriceFormula pf WITH (NOLOCK)
INNER JOIN PriceMatrix pm ON pf.PriceFormula = pm.PriceFormula
INNER JOIN Site ON pf.SiteId = Site.SiteId
WHERE Site.SiteId = <n> AND ( … )
```
WHY: writes the `_priceformula` helper file that accompanies the SL8 `.xls`.

**Q-EXP-006** — SL8 export, super-product feature-count (ExportThread.cs:723):
```sql
SELECT max(len(itco.FeaturePositionString) - len(replace(itco.FeaturePositionString, '|', ''))) AS optcount
FROM ItemComponents itco INNER JOIN Item ON itco.ItemId = Item.ItemId
WHERE Item.Item = '<superproduct>'
```
WHY: counts `|`-separated feature positions to size the super-product BOM columns.

**Q-EXP-007** — CSI export, catalogue option-value scope (SytelineCSIExport.cs:642, mirrored ExportThread.cs:2251):
```sql
SELECT DISTINCT optval.OptionValueId, optval.OptionId
FROM CatalogueOptionValues cov WITH (NOLOCK)
INNER JOIN OptionValue optval ON cov.OptionValueId = optval.OptionValueId
WHERE cov.CatalogueId = <n>
```
WHY: restricts the exported option values to those released in the catalogue.

**Q-EXP-008** — CSI export, item/description root query (SytelineCSIExport.cs:1150):
```sql
SELECT DISTINCT Item.Item, Product.Product,
  CASE WHEN pd.DescriptionId IS NOT NULL THEN pd.ShortDescription ELSE … END …
```
WHY: builds the item master rows with resolved short descriptions (truncated for length; full body verified present in source).

**Q-EXP-009** — BOM/PBOM material master pull from **SyteLine LIVE** (BOMExport.cs:455):
```sql
-- non-site-20:
SELECT DISTINCT item, description, unit_cost, stat FROM item ORDER BY item
-- site 20:
SELECT DISTINCT item, description, unit_cost, stat FROM item_mst
WHERE site_ref = '<Global.SytelineSite>' ORDER BY item
```
WHY: PBOM export reads live SyteLine item costs via
`ConnectionFactory.CreateNewConnectionSyteLine(live:true)`; site 20 reads the
multi-site `item_mst` table, all others the single-site `item` view.

**Q-EXP-010** — PBOM material/criteria join (BOMExport.cs:1258):
```sql
SELECT DISTINCT Item.Item, mp.MaterialProductId, Material.MaterialId, Material.Material, md.*, mc.*
FROM Item
INNER JOIN MaterialProductId mp ON mp.MaterialProductId = <n>
INNER JOIN MaterialData md ON mp.MaterialProductId = md.MaterialProductId AND md.DeleteStatus = 0
INNER JOIN Material ON md.MaterialId = Material.MaterialId
INNER JOIN MaterialCriteria mc ON md.MaterialCriteriaId = mc.MaterialCriteriaId
```
WHY: resolves the parametric-BOM material rows and their attribute-value criteria.

**Q-EXP-011** — PBOM sub-job (recursive BOM) resolution (BOMExport.cs:1121):
```sql
SELECT Material.Material, subjob.MaterialId, subjob.Formula, subjob.ScrapFactor, subjob.OperNum,
       subjob.IsSubJob, subjob.EffectiveDate, subjob.ObsDate, subjob.CreateBy, subjob.CreateDate
FROM MaterialSubJob subjob INNER JOIN Material ON subjob.MaterialId = Material.MaterialId
WHERE subjob.SubjobMaterialId = <n> AND subjob.SiteId = <n> AND subjob.DeleteStatus = 0
```
WHY: walks the material sub-job tree (formula, scrap, operation) for each material.

**Q-EXP-012** — OFDA export, catalogue header (OFDAExport.cs:2748):
```sql
SELECT DISTINCT Catalogue.OFMLManufacturer, '' AS CatalogCode, Catalogue.CatalogueFlags,
       Catalogue.ImageFile, CASE WHEN od.ShortDescription IS NOT NULL THEN od.ShortDescription ELSE Catalogue.Name END AS Name,
       Catalogue.DescriptionId, Catalogue.LeadTime, Catalogue.CatalogueType, Catalogue.OrderType
FROM Catalogue WITH (NOLOCK) LEFT OUTER JOIN OtherDescription od ON …
```
WHY: reads the OFML manufacturer code / lead time / flags that head each OFDA catalogue block.

**Q-EXP-013** — OFDA export, price resolution (OFDAExport.cs:1050):
```sql
SELECT CASE WHEN pc.BasePriceRef = 2 THEN itov.IncrementalPrice2
            WHEN pc.BasePriceRef = 3 THEN itov.IncrementalPrice3 … END …
```
WHY: picks the incremental-price slot (1/2/3) per the product code's `BasePriceRef`
(same slot logic as [18_Pricing.md](18_Pricing.md)).

**Q-EXP-014** — OFDA export, exchange-rate lookup (OFDAExport.cs:1528):
```sql
SELECT TOP 1 BuyRate FROM ExchangeRate WITH (NOLOCK)
WHERE DomCurrCode = '<dom>' AND CurrCode = '<currency>' AND EffectiveDate <= '<effdate>'
ORDER BY EffectiveDate DESC
```
WHY: converts base prices into the export currency at the effective date.

**Q-EXP-015** — OFDA / BOM central option report (stored proc, OFDAExport.cs:4425, BOMExport.cs:832):
```sql
PDMOptionDataReport '<item>'
```
WHY: the central procedure returning the fully-expanded option/order-code set for
an item. **Proc body UNKNOWN** (not in source tree).

**Q-EXP-016** — SIF export, category tree (SIFExportThread.cs:223):
```sql
SELECT DISTINCT CASE WHEN od.ShortDescription IS NULL THEN cpc.Name ELSE od.ShortDescription END AS Name,
       cpc.ProductCategoryId, CASE WHEN cpc.DisplayOrder = -1 THEN 9999 ELSE cpc.DisplayOrder END AS cpcDO
FROM Catalogue WITH (NOLOCK) INNER JOIN CatalogueProductCategories cpc ON Catalogue.CatalogueId = cpc.CatalogueId
```
WHY: builds the `.top` SIF category hierarchy; `DisplayOrder = -1 → 9999` pushes
un-ordered categories to the end (same convention as
[04_Product_Categories.md](04_Product_Categories.md)).

**Q-EXP-017** — SIF import, product-range order-code string update (SIFImport.cs:9114):
```sql
UPDATE ProductRange SET OrderCodeFormatString =
  CASE WHEN OrderCodeFormatString IS NULL THEN '' ELSE OrderCodeFormatString END + '{KEY}'
WHERE ProductRangeId = <n>
```
WHY: appends the new option's format key to the range's order-code template.

**Q-EXP-018** — SIF import, item-option increment upsert (SIFImport.cs:9379):
```sql
-- update existing:
UPDATE ItemOptionValues SET IncrementalPrice<n> = <price> WHERE ItemId = <i> AND OptionValueId = <ov>
-- else insert:
INSERT INTO ItemOptionValues (ItemId, OptionValueId, IncrementalPrice<n>) VALUES (<i>, <ov>, <price>)
```
WHY: writes imported per-item option surcharges back into PDM.

**Q-EXP-019** — Scheduled export insert (ScheduleExport.cs:899):
```sql
INSERT INTO ExportSchedule (ProductId, Product, SiteId, LanguageId, OtherLanguageId, CatalogueId, Categoryid, PBom, ScheduleDate) VALUES ( … )
```
WHY: queues a product for a later (service-driven) SL export.

**Q-EXP-020** — Scheduled-export catalogue list, honours read-only (ScheduleExport.cs:643):
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly
FROM PDMUserCatalogues puc INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId
WHERE puc.UserId = <UserId> AND Catalogue.Status = 1 ORDER BY Catalogue.Name
```
WHY: only shows catalogues the user may access (`PDMUserCatalogues` — note the
inverted `ReadOnly` semantics documented in [02_User_Permissions.md](02_User_Permissions.md)).

**Q-EXP-021** — Static-data XML, exchange rates (SDXmlExport.cs:356):
```sql
SELECT ExchangeRate.CurrCode, ExchangeRate.BuyRate, ExchangeRate.EffectiveDate, Currency.PriceCode
FROM ExchangeRate INNER JOIN Currency ON ExchangeRate.CurrCode = Currency.Currency
INNER JOIN Site ON ExchangeRate.DomCurrCode = Site.DomCurrCode WHERE Site.Site = '<site>'
```
WHY: emits `<ExchangeRate>` nodes for the selected site's currency rates.

**Q-EXP-022** — Static-data XML, product codes (SDXmlExport.cs:398):
```sql
SELECT Product_Code.Product_Code, Product_Code.PriceCode, Product_Code.Description, Product_Code.InterCompanyDisc
FROM Product_Code INNER JOIN Site ON Product_Code.SiteId = Site.SiteId WHERE Site.Site = '<site>'
```
WHY: emits `<ProdCode>` nodes (`Rounding` column is commented out in the SELECT).

**Q-EXP-023** — DPSDB publication, database file swap (ExportDPSDBThread.cs:92+):
```sql
sp_detach_db DPSDB
sp_attach_db DPSDB,'C:\Databases\DPSDB_Data.MDF'
sp_attach_db DPSDB,'C:\Databases\DPSDB_Data.MDF','C:\Databases\DPSDB_Log.LDF'
```
WHY: detaches the freshly-built `DPSDB`, copies the MDF/LDF to the network
publication folder, then re-attaches — the publication *is* the raw database files.

---

## 5. Data Model

### Source tables (read)
`Item`, `Product`, `Product_Code`, `ProductRange`, `ProductCategory`,
`CatalogueProductCategories`, `Catalogue`, `CatalogueItems`,
`CatalogueItemsUnreleased`, `CatalogueOptionValues`, `CatalogueAttributeValues`,
`CatalogueItemOptionExclusions`, `CatalogueItemExclusions`, `ItemComponents`
(super-product BOM: `ItemId`, `SubItemId`, `Quantity`, `ComponentSequence`,
`FeaturePositionString`), `[Option]`, `OptionValue`, `ItemOptionValues`
(`IncrementalPrice1/2/3`), `DependentOptionValues`, `Attribute`,
`AttributeValue`, `BaseAttributeValues`, `ProductAttributeValues`,
`DependentAttributeValues`, `OtherDescription`, `ProductDescription`,
`Language`, `Site`, `Currency`, `ExchangeRate`, `PriceFormula`, `PriceMatrix`,
`FabricBands`, `MaterialLibrary`, `MaterialProductId`, `MaterialData`,
`MaterialCriteria`, `MaterialSubJob`, `Material`, `ExportSchedule`,
`PDMUserCatalogues`, `DealerCatalogues`.

### External sources
- **SyteLine LIVE** (`item` / `item_mst`) via
  `ConnectionFactory.CreateNewConnectionSyteLine(live:true)` — PBOM unit costs.
- **PDMOptionDataReport** stored procedure — central option expansion (body UNKNOWN).
- **`fnGetListPrice` / `fnGetListPriceByItem`** SQL functions — forward pricing (bodies UNKNOWN).

### Target tables (write — import side)
`[Option]`, `OptionValue`, `ItemOptionValues`, `ProductRange`
(`OrderCodeFormatString`), `CatalogueProductCategories` (`PSTemplateFile`),
`ExportSchedule` (insert/delete), `DPSDB` (detach/attach).

### Output file formats
| Pipeline | File(s) | Structure |
|---|---|---|
| SL8 | `PDMExport.xls` / `PDMItemReport.xls` | tab-delimited "Excel" text |
| millerCAD | `b-<site><ccy>.asc`, `o-<site><ccy>.asc` | fixed ASC item/material load |
| SL8 helpers | `_priceformula`, `_productcode`, super-product, planning, description files | tab-delimited headers (ExportThread.cs:989/1041/2148/2150/2153) |
| CSI | `*_items.csv`, `*_product_items.csv`, `*_phantom_items.csv`, `*_item_price.csv`, `*_materials.csv`, `*_current_materials.csv` | tab-delimited CSV (SytelineCSIExport.cs:1445-1946) |
| OFDA | `PDMExport_OFDA_latest.xml` | OFDA-XML (`<Schema>/<Envelope>/<Enterprise>/<ExternalReference>` + `<Feature>/<FeatureRef>/<ProductRef>` blocks) |
| PBOM material | `PDM_material_export.csv` | **`;`-delimited**, header `MaterialGroup;Option;ParentItem;Material;OptionCode;Description;Qty;ScrapFactor;Operation;IsSubJob;Cost;Level;TestStatus;LiveStatus;FamilyCode;RGIDDescription;OperationDescription;EffDate;ObsDate;CreatedBy;CreateDate` (BOMExport.cs:1668) |
| SIF | `<name>.top`, `.key`, `.opt` | line-oriented `KK=value` SIF format (`SL=`, `CR=`, `PO=`, `OG=`, `ON=`, `OD=`, `O1=`) |
| Financial | `PDM_financial_extract_PLC_<site>.txt` (+ `_PM`, `_PF`) | tab-delimited |
| Price band | `PDM_price_band_extract.txt` | tab-delimited |
| Static data | `*.xml` | `<PDM-Data>` / `<Site>` / `<ExchangeRate>` / `<ProdCode>` / `<Formula>` |
| DPSDB | `DPSDB_Data.MDF`, `DPSDB_Log.LDF`, `change_log.txt` | raw SQL-Server files |

### OFDA-XML external-reference block (OFDAExport.cs:9068)
Hard-coded UNC resource dirs are embedded in the header:
`CETTexturesDir = \\FSCHIP01v\PDM Resources\Materials\`,
`CETSymbolsDir  = \\FSCHIP01v\PDM Resources\Symbols\<resourcePath>`,
`CETThumbnailsDir = \\WECHIP01v\HMEURONET\PDM\Images\Products\`,
`<UnitMeasure>mm</UnitMeasure>`.

---

## 6. Business Rules

### Permission / trigger gates
- **BR-EXP-001** The "Export PDM Data" button is only enabled when
  `AuthenticateUser.SytelineExport` is true (MainMenu.cs:3037-3039).
- **BR-EXP-002** The "PDM Data Import" button is enabled only when
  `AuthenticateUser.PDMImport` **and** the connected server name does **not**
  contain `"eoscloud"` (MainMenu.cs:3097) — import is blocked on the cloud DB.
- **BR-EXP-003** Left-clicking "PDM Data Import" opens the `SIFImport` form
  (MainMenu.cs:3896); **right-clicking as user `dbacw8`** instead runs
  `importSytelineCSIData()` (MainMenu.cs:3892) — a developer-only branch.
- **BR-EXP-004** "Import Materials in to CSI" is disabled unless the user has
  `CoreMaintenance` (MainMenu.cs:3087), and its handler body additionally does
  nothing unless the Windows user name contains `dbacw8` (MainMenu.cs:5099) —
  effectively a developer-only tool.
- **BR-EXP-005** The scheduler button branches on identity: user `dbacw8` gets
  the raw SIF `.top` export (`SIFExport`); all others get the `ScheduleExport`
  queue dialog (SytelineExport.cs:6656 vs 6692).

### SL8 export rules (`ExportSL8Data`, ExportThread)
- **BR-EXP-006** Output type is chosen by flags: `millerCAD` → `b-<site><ccy>.asc`;
  `syteline` → `PDMExport.xls`; otherwise item report → `PDMItemReport.xls`
  (and `itemreport` is forced true) (SytelineExport.cs:3652-3665).
- **BR-EXP-007** **Site 20 is remapped to site 1 ("uk")** for SL8 export
  (SytelineExport.cs:3822: `if (num == 20) { num = 1; text2 = "uk"; }`).
- **BR-EXP-008** Export parameters may come from the UI or from a queue-param
  string; the queue path builds the file name from `{site}{catalogue}{PLC}{min}{max}{currency}`
  placeholders (SytelineExport.cs:3736).
- **BR-EXP-009** When min-item == max-item the `{max}` placeholder is dropped
  from the file name (SytelineExport.cs:3767) — single-item exports get a shorter name.
- **BR-EXP-010** The `SuperProductCombo` selection maps to mutually-exclusive
  flags: index 0 → `excludeSuperProducts`, index 1 → `superProductsOnly`
  (SytelineExport.cs:3721-3727).
- **BR-EXP-011** The `_millerCAD | (_syteline & !_exportBasePrices)` condition
  switches the item master query variant (ExportThread.cs:2351).
- **BR-EXP-012** Super-product BOM is exported by UNION-ing the base item query
  with an `ItemComponents`-joined variant that swaps `Item` for `sp_item`
  (ExportThread.cs:2426).

### CSI export rules (`ExportCSIData`, SytelineCSIExport)
- **BR-EXP-013** `check_includeURL` lowers the minimum option-value status to 0
  (`minStatus = 0`), i.e. include un-released (URL) values (SytelineExport.cs:3986).
- **BR-EXP-014** CSI writes up to six satellite CSVs (items, product_items,
  phantom_items, item_price, materials, current_materials) — the phantom/product/
  price files are only written when the corresponding branch runs
  (SytelineCSIExport.cs:1468-1495).
- **BR-EXP-015** Feature order-code max length is queried per option
  (`SELECT MAX(LEN(OrderCodeValue)) … WHERE Status < 2`) to size CSI columns
  (SytelineCSIExport.cs:290) — obsolete/held values excluded from the width calc.

### OFDA export rules (`ExportOFDA`, OFDAExport)
- **BR-EXP-016** Selecting catalogue 360 without 362 auto-adds catalogue **392**
  (SytelineExport.cs:4426) — StoragePlus companion catalogue.
- **BR-EXP-017** Multiple catalogues are **sorted by descending `LeadTime`**
  before export (insertion sort, SytelineExport.cs:4383-4410).
- **BR-EXP-018** Site **2 ("Japan")** and currency **JPY** are forced to the end
  of their respective multi-select lists (SytelineExport.cs:4440, 4497).
- **BR-EXP-019** Language **10 (English)** is forced to the **front** of the
  language list (SytelineExport.cs:4470) so it is the primary export language.
- **BR-EXP-020** `UnreleasedDataCheck` sets `minStatus = 0`; default OFDA export
  is `minStatus = maxStatus = 1` (ACT only) (SytelineExport.cs:4123, 4544).
- **BR-EXP-021** The exported product-line "series" is derived from a **hard-coded
  catalogue-ID → name map** (OFDAExport.cs:9089-9150): 239/420/394/277→LayoutStudio,
  436/404→Sabha, 422→Memo, 405→Augment, 420/251/252→Unity, 465→Atlas,
  360/392→StoragePlus, 478→Civic, 361/362/432/451/462/539→Imagine, 365/383→Optimis,
  507→Catena, 519/520/536/537→Nevi, 502→Port, 617→OE1, 605→Byne; anything else
  falls back to the item-name prefix.
- **BR-EXP-022** `excludeImaginePanels` suppresses Imagine panel items at
  multiple join points (OFDAExport.cs:3205-3474).
- **BR-EXP-023** `naughtoneCatalogCode` rewrites the catalogue code to a
  `_NAUGHTONE_` variant (OFDAExport.cs:2722-2733); a warning is shown if it
  cannot be assigned.
- **BR-EXP-024** Fabric option values map to hard-coded OptionId `<FeatureRef>`
  prefixes (28 / 9278 / 9276 / 9314 / 9282 / 9280 / 9326 / 9347 / 9286 / 9284 /
  9328 / 9349 / 9290 / 9288) (OFDAExport.cs:5714-5766).
- **BR-EXP-025** Model-specific suffixes are emitted with `_` replaced by `<us>`
  markup inside `[…]` brackets (OFDAExport.cs:4079, 4944).
- **BR-EXP-026** The OFDA file is always named `PDMExport_OFDA_latest.xml` unless
  an explicit filename was passed — the timestamp is computed but then overwritten
  with the literal `"latest"` (OFDAExport.cs:8878-8882). *Hidden — see §7.*
- **BR-EXP-027** On OFDA export the previous file is rotated to `_prev.xml`
  / `_prev<n>.xml` and a backup copy taken (SytelineExport.cs:4343-4363).
- **BR-EXP-028** `_webconfig` mode replaces `"<root>"` selection descriptions with
  the real root-product descriptions in the finished XML (OFDAExport.cs:8870).
- **BR-EXP-029** OFDA price dates / units follow the OCD convention (unit `C62`,
  effective/obsolete date span) — cross-reference [21_OCD.md](21_OCD.md).

### PBOM material export rules (`ExportMaterials`, BOMExport)
- **BR-EXP-030** PBOM export connects to **SyteLine LIVE** for unit costs; site 20
  reads `item_mst` filtered by `Global.SytelineSite`, all other sites read `item`
  (BOMExport.cs:455).
- **BR-EXP-031** Only material rows with `DeleteStatus = 0` are exported
  (BOMExport.cs:1121, 1258).
- **BR-EXP-032** The output is **semicolon-delimited** (not tab) with several
  always-blank columns (`Option`, `TestStatus`, `FamilyCode`, `RGIDDescription`,
  `OperationDescription`) reserved but not populated (BOMExport.cs:1670-1697).
- **BR-EXP-033** Developer-only diagnostic: when `isDeveloper`, a raw SQL log is
  written to `C:\Users\DBACW8\Desktop\PBOM exports\sql_log.txt` (BOMExport.cs:1645) —
  hard-coded developer path.
- **BR-EXP-034** `ImportMaterialsInToCSI` / `ResolveCriteria` parse Excel-style
  `=IF(OR(…),…,…)` criteria strings into ordered criteria/result lists
  (MainMenu.cs:5105, BOMExport.ResolveCriteria).

### SIF export rules (SIFExportThread)
- **BR-EXP-035** SIF export writes three files from one base name: `.top`
  (category tree), `.key` (`RunKeyOpt`), `.opt` (option data) (SIFExportThread.cs:172-177).
- **BR-EXP-036** `°` (degree sign) in category/range names is replaced with the
  literal `" degree"` in the `.top` file (SIFExportThread.cs:235, 251).
- **BR-EXP-037** `#`-suffixed order codes are stripped of the `#` when written as
  `ON=` lines in the `.opt` file (SIFExportThread.cs:483).
- **BR-EXP-038** A missing/`-1` incremental price is written as `O1=0.00`;
  otherwise the price is rounded to 2 dp (SIFExportThread.cs:485-496).
- **BR-EXP-039** `CatalogueProductCategories.DisplayOrder = -1` is normalised to
  `9999` (sort-last) in the SIF category query (SIFExportThread.cs:223).

### SIF import rules (SIFImport)
- **BR-EXP-040** Import accepts two source families: SIF `.top`/`.n01`
  (read as `iso-8859-1`) or PIP/OFDA `.xls`/`.xml` (SIFImport.cs:6313, 6357).
- **BR-EXP-041** SIF `.top` import also looks for sibling `.key` and `.opt` files
  by replacing `"top"` in the file name (SIFImport.cs:995, 1078).
- **BR-EXP-042** New options are created with a **camelCase, US→UK-English
  converted** name (SIFImport.cs:9071), a generated `OrderCodeFormatKey`, a
  `DisplayOrder` from `getNextDisplayOrder`, and a new `OtherDescription` created
  at language **10** (SIFImport.cs:9066).
- **BR-EXP-043** If the option name contains `"kvadrat"` and it is a fabric type,
  `SupplierId` is set to **2** (SIFImport.cs:9068-9070) — hard-coded supplier.
- **BR-EXP-044** Fabric-type option values are given a `#`-suffixed order code
  (unless already `#`-terminated) when `fabricTypeId > -1 && fabricColourId == -1`
  (SIFImport.cs:9165).
- **BR-EXP-045** Order-code `{KEY}` tokens are stripped out of the stored
  `OrderCodeValue` (SIFImport.cs:9160).
- **BR-EXP-046** The new format key is appended to
  `ProductRange.OrderCodeFormatString` only if not already present (Q-EXP-017).
- **BR-EXP-047** Item option increments are **upserted** (update if the row
  exists, else insert) (Q-EXP-018).
- **BR-EXP-048** Fabric imports create paired "Fabric type" + "Fabric colour"
  options with fixed global option ids **8** (type) and **28** (colour)
  (SIFImport.cs:3343-3349) — matches the CAD fabric globals in
  [11_Configuration.md](11_Configuration.md).
- **BR-EXP-049** PIP import can set `CatalogueProductCategories.PSTemplateFile`
  (SIFImport.cs:3404).

### Financial / price-band / static-data export rules
- **BR-EXP-050** Financial export requires at least one of PLC / Matrix / Formula
  checkboxes; otherwise it aborts with a message (MainMenu.cs:4177).
- **BR-EXP-051** The three financial files are derived from one save name by
  substituting `PLC`→`PM`→`PF` (with `_PM`/`_PF` fallbacks if the token is absent)
  (MainMenu.cs:4189-4198).
- **BR-EXP-052** Price-band export includes only `OptionValue.status < 2`
  (URL/ACT) (Q-EXP-004).
- **BR-EXP-053** Static-data XML `Rounding` column is deliberately commented out
  of the product-code SELECT (SDXmlExport.cs:398).
- **BR-EXP-054** Static-data XML aborts if no site is selected (SDXmlExport.cs:254).

### Scheduled-export rules
- **BR-EXP-055** The scheduler category list excludes categories 1, 128, 129, 999
  (ScheduleExport.cs:734) — same "system" categories excluded elsewhere
  ([04_Product_Categories.md](04_Product_Categories.md)).
- **BR-EXP-056** The scheduler site list excludes site 20 (`WHERE SiteId NOT IN (20)`)
  (ScheduleExport.cs:663).
- **BR-EXP-057** A pending schedule row can only be deleted while
  `ExecutionDate IS NULL` (not yet run) (ScheduleExport.cs:1005).

### DPSDB publication rules
- **BR-EXP-058** Publication only copies files to the network when
  `publishToNetwork` is set; the DTS package build always runs first
  (ExportDPSDBThread.cs:85).
- **BR-EXP-059** A DTS failure raises "DTS package failed to execute successfully"
  and dumps the export log to a debug form (ExportDPSDBThread.cs:74).
- **BR-EXP-060** Publication files land in a timestamped subfolder
  `\\fschip01\…\Database Publications\<dd_MM_yyyy_HHhMMmSSs>\` with a
  `change_log.txt` recording publisher + log (ExportDPSDBThread.cs:139-146).

---

## 7. Hidden Logic

- **ClippingsExport is ORPHANED / DEAD CODE.** `SytelineExport` instantiates it
  (`clipThread = new ClippingsExport();`, SytelineExport.cs:1533) but **never**
  calls `initParams` or `execThread` — verified: the only two references in the
  whole solution are the field declaration (SytelineExport.cs:220) and that `new`
  (grep across `*.cs`). The full clippings XML builder (ClippingsExport.cs, ~2372
  lines, produces `<Key>CLIPPINGS-…</Key>` XML) is therefore unreachable in this
  build — mirroring the orphaned `OCDExport`/`ocdThread` documented in
  [21_OCD.md](21_OCD.md).
- **OFDA filename timestamp is dead.** The code computes a date-stamped filename
  then unconditionally overwrites it with `"latest"` (OFDAExport.cs:8878-8882), so
  every non-explicit OFDA export overwrites `PDMExport_OFDA_latest.xml`.
- **`serviceExport`** (SytelineExport.cs:4655) is a headless SL8 export path
  (`runAsService: true`) driven by the scheduled-export service, not the UI.
- **Developer-only branches** are gated on the literal Windows user name
  `dbacw8` (import-Syteline-CSI, SIF `.top` export, import-materials) — these are
  invisible to normal users.
- **`C:\Downloads\sql.txt` / `C:\Downloads\log.txt`** debug SQL logs are written
  by `SytelineExport`/`ExportThread` when logging is enabled (SytelineExport.cs:2384,
  ExportThread.cs:798) — hard-coded local paths.
- **Hard-coded UNC resource paths** are baked into the OFDA XML header (§5) and
  into DPSDB publication (§6) — these will break outside the original network.

---

## 8. UI Behaviour

- `SytelineExport` is a **tabbed** form (`TabControl1`): tab 0 = SL8/Syteline,
  tab 1 = CSI, tab 2 = OFDA, tab 3 = PBOM/Item-Price. The single `ExportButton`
  acts on the active tab (§2).
- During export the form **locks its controls** (`lockControls`,
  SytelineExport.cs:4687: disables tabs, export/validate/queue buttons, checkboxes)
  and shows an `AbortButton`; `releaseControls` restores them on completion.
- A **queue** (`ExportQueueManager` + `button_queue`) lets the user batch several
  export configurations and run them sequentially via `ProcessNextInQueue`; the
  queue button label shows progress `Queue (n of m)` (SytelineExport.cs:5425).
- Multi-select popups (`list_multi_site`, `list_multi_catalogue`,
  `list_multi_currency`, `list_multi_language`, `list_multi_PLC`) toggle visibility
  and drive the "Multiple …" combo entries.
- OFDA export on the full **Seating** catalogue with no PLC/range filter prompts a
  confirmation ("The entire Seating catalogue will be exported …", SytelineExport.cs:5516).
- Progress is surfaced through `label_status` / timer via the worker events;
  `SytelineExport_Closing` guards against closing mid-export.
- `SIFImport` is a large form with buttons: "Import / Update Data …",
  "Update Product Description (selected/all)", "Update Item List Price (selected/all)".

---

## 9. Dependencies

- **`ConnectionFactory`** — `CreateNewConnection` (PDM DB) and
  `CreateNewConnectionSyteLine(live/test)` (SyteLine ERP) — see
  [00_System_Architecture.md](00_System_Architecture.md).
- **`Global`** — `primaryPDMServer`, `SytelineSite`, `connectedServer`,
  `connectedDB`, `testMode`.
- **`AuthenticateUser`** — permission flags (`SytelineExport`, `PDMImport`,
  `CoreMaintenance`, `UserId`, `DefaultDealerNum`).
- **`PDMOptionDataReport`** stored proc + **`fnGetListPrice`/`fnGetListPriceByItem`**
  functions — bodies UNKNOWN.
- Worker classes: `ExportThread`, `OFDAExport`, `SytelineCSIExport`,
  `SytelineBOMExport`, `BOMExport`, `ItemPriceExport`, `SIFExportThread`,
  `ClippingsExport` (dead), `ExportDPSDBThread`, `ProgressThread`, `TimerThread`.
- **`SyteLineExportValidator`** — validates export context (`validator.exportContext`).
- **DTS / SSIS package** (external) for DPSDB build.
- **Excel interop** (`Microsoft.Office.Interop.Excel`) for PIP `.xls` import (SIFImport).
- Downstream consumers: SyteLine 8, CET Designer / OFDA, DPS, pCon.

---

## 10. Risks

- **SQL injection everywhere.** All queries are string-concatenated with UI text
  (item names, min/max, catalogue codes) with no parameterisation — e.g.
  `WHERE Item.Item = '<myitem>'`. A crafted item name/order code could inject SQL.
- **Hard-coded infrastructure.** UNC paths (`\\FSCHIP01v`, `\\WECHIP01v`,
  `\\fschip01`, `\\<primaryPDMServer>`), local paths (`C:\Databases`,
  `C:\Downloads`, `C:\Users\DBACW8\Desktop`), and server-name substring checks
  make these pipelines non-portable.
- **Identity-gated developer branches** (`dbacw8`) hide functionality and behave
  differently per operator — fragile and undocumented for end users.
- **DPSDB detach/attach** takes the published database offline and copies raw MDF/LDF
  over the network; a failure mid-swap can leave `DPSDB` detached.
- **Dead code** (`ClippingsExport`, OCD, OFDA timestamp) increases maintenance
  surface and can mislead a migration ("we still export clippings" — we do not).
- **Proc/function black boxes.** `PDMOptionDataReport`, `fnGetListPrice*` and the
  DTS package encapsulate load-bearing logic that is **not in the source tree**;
  their behaviour must be reverse-engineered from the database to fully migrate
  OFDA/CSI/PBOM/price outputs.
- **OFDA hard-coded catalogue maps** (BR-EXP-021/024) mean every new catalogue or
  fabric option requires a code change, not data — a significant migration constraint.

### Coverage limits
Given file sizes (OFDAExport.cs ~12.5k, SIFImport.cs ~10.2k, ExportThread.cs ~7.5k,
SytelineExport.cs ~7.2k, SytelineCSIExport.cs ~2k, ClippingsExport.cs ~2.4k), this
document prioritises, per pipeline: the **trigger/permission**, **what is read**,
**what file/format is produced**, and the **load-bearing transforms and hard-coded
rules**. The per-item XML/CSV **field-level assembly loops** inside `OFDAExport`,
`ExportThread` and `SytelineCSIExport` (hundreds of concatenation steps each) are
**not exhaustively transcribed**; the representative queries and rules above cover
the structurally significant behaviour. Anything not directly provable from source
is marked `UNKNOWN` (notably `PDMOptionDataReport`, `fnGetListPrice*`, the DTS
package, and `importSytelineCSIData` internals).
