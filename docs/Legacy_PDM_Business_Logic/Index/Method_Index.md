# Method Index

*Navigation layer for the legacy PDM Maintenance handbook: the important methods named across the
module docs (00–28), each cross-linked back to the doc that proves it and, where needed, confirmed
against the legacy C# source (`PDMMaintenance\*.cs`). This file does **not** re-transcribe method
bodies — it is a lookup table. `Calls` / `Called By` are filled only where evidenced in the docs or
source; unproven entries are marked `UNKNOWN`. Module links use `../NN_Name.md`.*

> Legend: **Called By** lists the concrete caller(s) proven in source/handbook; **Calls** lists the
> notable downstream methods/queries. Signatures are the actual legacy declarations where confirmed.

---

## Architecture & Connection — `ConnectionFactory`, `AuthenticateUser`

Source docs: [../00_System_Architecture.md](../00_System_Architecture.md), [../01_Authentication.md](../01_Authentication.md), [../02_User_Permissions.md](../02_User_Permissions.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `CreateNewConnection(bool autoOpen)` → `SqlConnection` | `ConnectionFactory` | Build/open a SQL Server connection; connection string chosen by server-name substring match, with retry/backoff and forced read-only on some servers | `PingHost`, `HidePassword` (UNKNOWN exact wiring) | Nearly every maintenance form, export/import worker, and helper (`AuthenticateUser`, `PriceMaintenance`, `CADMaintenance`, `DataQuery`, `ExportThread`, …) | 00 | [../00](../00_System_Architecture.md) |
| `CreateNewConnectionSyteLine(bool autoOpen, bool live)` → `SqlConnection` | `ConnectionFactory` | Build/open a connection to the **SyteLine ERP** database (live vs. non-live) | UNKNOWN | `BOMExport` (`:450`), `MainMenu` (`:5163`, CSI import) | 00 / 22 | [../00](../00_System_Architecture.md) |
| `PingHost(string nameOrAddress)` → `bool` | `ConnectionFactory` | Reachability probe of a DB server before connecting | UNKNOWN | `CreateNewConnection` (server selection) — exact call UNKNOWN | 00 | [../00](../00_System_Architecture.md) |
| `HidePassword(string connectionString)` → `string` | `ConnectionFactory` | Mask the password in a connection string (for logging/diagnostics) | — | Connection/diagnostic paths — UNKNOWN | 00 | [../00](../00_System_Architecture.md) |
| `setUserPrivileges(string username)` (internal static) | `AuthenticateUser` | Load the Windows user's `PDMUserPrivileges` row and populate the 30 static permission flags (`Q-AUTH-001`) | `ConnectionFactory.CreateNewConnection` | `MainMenu` init (`MainMenu.cs:~3016`); `StaticDataMaintenance` | 01 / 02 | [../01](../01_Authentication.md) |

---

## Products / Super Products — `SuperProductMaintenance`, `SuperProductVarCondRelation`

Source doc: [../05_Products.md](../05_Products.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `initialiseArrays()` (internal) | `SuperProductMaintenance` | Populate catalogue / site / currency selectors on form open | `updateSPCompList` (`Q-PROD-001..004`) | Form host after construction | 05 | [../05](../05_Products.md) |
| `updateSPFlag()` | `SuperProductMaintenance` | Maintain `Product.IsSuperProduct` after component edits | inline `UPDATE Product` | `SubmitButton_Click` component upsert | 05 | [../05](../05_Products.md) |
| `evalulateQuantity(string number)` → `int` (private) | `SuperProductMaintenance` | Parse/evaluate a component quantity string (legacy spelling preserved) | — | component add / CSV import (`:4019`) | 05 | [../05](../05_Products.md) |
| `GenerateVARCONDForPAPRICINGToolStripMenuItem_Click` (VARCOND generation) | `CADMaintenance` / `SuperProductVarCondRelation` | Build pCon **VARCOND** price-relation strings (`PA_<prefix>`) and push into the pCon commerce MDB | `CADMaintenance.GetPconPackageIdOnly` | Menu **Generate VARCOND for PA_PRICING**; `SuperProductVarCondRelation` | 05 / 11 | [../05](../05_Products.md), [../11](../11_Configuration.md) |

---

## Articles / Product Codes — `ProductCodeEntry`, `metaArticles`, `ocd*` DTOs

Source doc: [../06_Articles.md](../06_Articles.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `ProductCodeEntry_Load` | `ProductCodeEntry` | Populate the site selector (`Q-ART-001`) | inline SQL | Form load (dialog) | 06 | [../06](../06_Articles.md) |
| `AddButton_Click` | `ProductCodeEntry` | Validate inputs and `INSERT Product_Code` | inline `INSERT` | Opened from `StaticDataMaintenance.cs:5032` | 06 | [../06](../06_Articles.md) |
| `getAllProperties()` → `ArrayList` | `metaArticles`, `ocdArticle`, `ocdArtBase`, `ocdArtDesc`, `ocdCodeScheme`, `codeScheme` | Emit the DTO's fields positionally for OCD/GO serialisation | — | `OCDExport` writer loop | 06 / 21 | [../06](../06_Articles.md) |

---

## Physical Attributes — `PhysicalMaintenance`, `metaProperties`

Source doc: [../07_Attributes.md](../07_Attributes.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `PhysicalMaintenance_Load` | `PhysicalMaintenance` | Wire adapters and load physical/logistics grids | `CheckTables`, `WebEOSUpdate`, `DeliveryUpdate`, `initialiseArrays`, `PhysicalItemChange`, `UpdateCategory` | `PhysDataButton_Click` (`MainMenu.cs:2924`) | 07 | [../07](../07_Attributes.md) |
| `PhysicalItemChange(string)` | `PhysicalMaintenance` | Reload the item + physical-attribute grid (`Q-ATTR-012/014`) | inline SQL | `_Load`, `catalogue_selector_SelectedIndexChanged` | 07 | [../07](../07_Attributes.md) |
| `SubmitButton_Click` | `PhysicalMaintenance` | Optimistic-concurrency `UPDATE Item` of physical attributes (`Q-ATTR-005`) | `SqlDataAdapter.Update` | Save button | 07 | [../07](../07_Attributes.md) |

---

## Property / Option Values & Options — `AddNewData`, `OptionClass`, `OptionGroup`

Source docs: [../08_Property_Values.md](../08_Property_Values.md), [../09_Options.md](../09_Options.md), [../10_Option_Values.md](../10_Option_Values.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `initDataQuery("PDMOptionDataReport '{text}'")` | `DataQuery` | Item Option Data Report — dump options+values for an item via the shared stored proc | `EXEC PDMOptionDataReport` | `ItemOptionDataReportToolStripMenuItem_Click` (`MainMenu.cs:4098`) | 09 | [../09](../09_Options.md) |
| `submitData()` → `bool` (private) | `AddNewData` | Insert a new record (fabric / option / product-group code) from the generic add dialog | inline `INSERT` | Add-new dialogs across forms | 09 / 10 / 24 | [../24](../24_Utilities.md) |

> `OptionClass`, `OptionGroup`, `OptionData` are export DTOs (no maintenance methods) — see [Class_Index.md](Class_Index.md).

---

## Configuration / pCon (CAD) — `CADMaintenance`, `WebConfigurator`

Source doc: [../11_Configuration.md](../11_Configuration.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `GetPconPackageId(string context, string cataloguename, int categoryId, bool suppress)` → `int` (private) | `CADMaintenance` | Resolve the pCon package id for a catalogue/category context (instance form of the lookup) | inline OLE DB / SQL | `CADMaintenance` pCon panels (`:14592/14853/15226/15579`) | 11 | [../11](../11_Configuration.md) |
| `GetPconPackageIdOnly(string context, string cataloguename, int categoryId, bool suppress, ref string packagename)` → `int` (public static) | `CADMaintenance` | Static variant that also returns the pCon package **name** by ref | inline OLE DB / SQL | `SuperProductVarCondRelation` (`:1340`) | 11 / 05 | [../11](../11_Configuration.md) |
| `CreateNode(string cataloguename, int objectId, string nodename, string itemparams, int parentId, string prevsql, bool macro, bool export2D, …)` → `int` (public static) | `CADMaintenance` | Create a pCon geometry/config node row for a catalogue tree | inline SQL / OLE DB | `UpdateThread` (`:786/816`) | 11 | [../11](../11_Configuration.md) |
| `ClonePConPropertyClassOCDToolStripMenuItem_Click` | `CADMaintenance` | Clone a pCon property class (variant model) via SQL | inline SQL | Menu **Clone pCon Property Class OCD** | 11 | [../11](../11_Configuration.md) |
| `getPConWorkspace`, `GetPconPackageIdOnly`, `getPConPrefixLengthByCategory`, `getArticlePrefixLength` | `CADMaintenance` | pCon MDB workspace / prefix-length resolution helpers | inline OLE DB | pCon export/import handlers | 11 | [../11](../11_Configuration.md) |
| `UpdatePConDataFileToolStripMenuItem_Click` (head only) | `CADMaintenance` | XLS→PDM price/feature round-trip import (body large, **partly UNKNOWN**) | UNKNOWN | Menu **Update pCon Data File** | 11 | [../11](../11_Configuration.md) |

---

## Translations & Descriptions — `ProductDescriptions`, `DescriptionsFindReplace`

Source docs: [../12_Translations.md](../12_Translations.md), [../13_Descriptions.md](../13_Descriptions.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `submitData()` (private) | `ProductDescriptions` | Persist product-tab edits: `ProductDescription`, `CatalogueApplicationText`, `Product.Name`, images (`Q-DESC-021..027`) | inline UPSERTs | Submit / SubmitNext (`TabSelector==0`) | 13 | [../13](../13_Descriptions.md) |
| `modifyOtherDescription(string tabname, string originId, int descId, string description, bool ignoreCamelCase)` → `bool` (private) | `ProductDescriptions` | Persist non-product entity descriptions to `OtherDescription` + owning entity `Name` (`Q-TRAN-007..010`) | inline UPSERTs | Submit for `TabSelector>0` | 12 / 13 | [../13](../13_Descriptions.md) |
| `generateProgrammaticDescription(int productId, bool abbreviate)` → `string` (private) | `ProductDescriptions` | Build a description from an attribute-token template (`Q-DESC-040/041`) | inline SELECTs | `button_prog_update_Click` | 13 | [../13](../13_Descriptions.md) |
| `getRSDescription(string rsvalue, int languageId)` → `string` (private) | `ProductDescriptions` | Resolve range/attribute (`RS`) value description text for a language | inline SELECT | row-select / edit-box population (`:7099/7786/7787`) | 13 | [../13](../13_Descriptions.md) |
| `showTranslatedStatus()`, `language2update()` | `ProductDescriptions` | Refresh secondary-language text + "Catalogue Translated" state (`Q-TRAN-002..004`) | inline SELECTs | `language_selector2_SelectedIndexChanged` | 12 | [../12](../12_Translations.md) |
| `sendData(...)`, `FindNext()`, `InsertButton_Click` | `DescriptionsFindReplace` | Find (primary language) / replace (secondary language) across a product list (`Q-TRAN-015/016`) | inline SELECT/UPDATE | `TranslationButton_Click` | 12 | [../12](../12_Translations.md) |

---

## Search / Ad-hoc Query — `DataQuery`

Source doc: [../14_Search.md](../14_Search.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `initDataQuery(sql)` / query run | `DataQuery` | Run a caller-supplied `SELECT` (token-substituted, injectable) and render results; also drives writes (reassign PLC, reactivate, delete increments) | inline SQL (`Q-SRCH-*`) | ~42 `MainMenu` "Query …" handlers (`MainMenu.cs:2321+`) | 14 | [../14](../14_Search.md) |
| `ApplyButton` / `ApplyToAllButton` / `ReactivateButton` / `DeleteButton` handlers | `DataQuery` | Maintenance writes triggered from the search dialog | inline UPDATE/DELETE | Search dialog buttons | 14 | [../14](../14_Search.md) |

---

## UI Grouping / Filtering — `UIGroupMaintenance`, `ExportLayoutStyleThread`

Source doc: [../15_Filtering.md](../15_Filtering.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `getUIGroupIdForProduct(int productId, ArrayList uiGroupIds, uiGroupVals, uiGroupProductCategoryIds, uiGroupProductRangeIds, defaultedGroups)` → `int` (private) | `UIGroupMaintenance` | **Core match** — decide which UI Group a product belongs to from its functional-attribute values (`Q-FILT-007`) | inline SELECT | `loadUIGroups`, `UIPanel_Paint` | 15 | [../15](../15_Filtering.md) |
| `getUIGroupIdForProduct(…)` (same signature) | `ExportLayoutStyleThread` | Duplicate matcher used during layout-style export | inline SELECT | export thread body | 15 / 22 | [../15](../15_Filtering.md) |
| `loadUIGroups(int selectedId)` | `UIGroupMaintenance` | Build icons + assigned/unassigned split (`Q-FILT-006`) | `getUIGroupIdForProduct` | selector-change events | 15 | [../15](../15_Filtering.md) |

---

## Ordering — `OrderCategories`

Source doc: [../16_Ordering.md](../16_Ordering.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `OrderCategories_Load` | `OrderCategories` | Build the ordinal-edit row list (catalogues when `catalogueId==-1`; categories path is dead) (`Q-CAT-002` / `Q-CATEG-002`) | inline SELECT | opened by `ProductDescriptions.SortButton_Click` | 16 | [../16](../16_Ordering.md) |
| `SubmitButton_Click` | `OrderCategories` | Write each edited `DisplayOrder` back (`Q-CAT-003`) | inline `UPDATE` | Submit Changes button | 16 | [../16](../16_Ordering.md) |
| `AlphaButton_Click` | `ProductDescriptions` | **Dead stub** — confirm dialog only, no action (`BR-ORD-012`) | — | Alpha button | 16 | [../16](../16_Ordering.md) |

---

## Images — `GetImage`, `ValidateImages`, `ValidateImageThread`

Source doc: [../17_Images.md](../17_Images.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `GetImage(imageFile, materialpath, safeload, noscale)` | `GetImage` | Resolve an `ImageFile` token to a bitmap by probing base paths (UNC / EOS / HTTP) | `URLExists`, `GetImageFromURL`, `SafeImageFromFile` | `MainMenu`, `ProductDescriptions`, `CADMaintenance`, many forms | 17 | [../17](../17_Images.md) |
| `URLExists(string url)` → `bool` (public static) | `GetImage` | HTTP reachability probe before loading an image over the web | `WebClient` | `GetImage` (http base path) | 17 | [../17](../17_Images.md) |
| `GetImageFromURL(string url)` (private) | `GetImage` | Load an image over HTTP (`WebClient.OpenRead` → `Image.FromStream`) | — | `GetImage` | 17 | [../17](../17_Images.md) |
| `SafeImageFromFile(string path, bool noscale)` (public static) | `GetImage` | Load a bitmap without locking the source file | — | `GetImage` (when `safeload`) | 17 | [../17](../17_Images.md) |
| `validateImages()` | `ValidateImages` | Publish-time check that `WFImageFile` refs exist; auto-null broken refs | inline SELECT/UPDATE | `ExportDPSDB.cs:215` | 17 | [../17](../17_Images.md) |
| `ExecThread()` / `InitThread(catalogueId, cloud)` | `ValidateImageThread` | Interactive "Unresolved Images" report from the query dialog | inline SELECT + `File.Exists` | `DataQuery` (title starts `"Unresolved"`, `:2428`) | 17 | [../17](../17_Images.md) |

---

## Pricing — `PriceMaintenance`, `FinancialMaintenance`, `PConPriceUpdate`

Source doc: [../18_Pricing.md](../18_Pricing.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `getBasePrice(double listprice, string pricecode, int basepriceref, DateTime effdate, int siteId, string currency)` → `double` (public static) | `PriceMaintenance` | Reverse-uplift: derive a base price from a list price using Site → ExchangeRate → PriceMatrix/PriceFormula (`Q-PRICE-030..032`) | `SELECT Site` / `ExchangeRate` / `PriceMatrix` | `importPricesFromExcel`, `importIncPricesFromExcel`; **cross-module** `SIFImport` (`:9009/9499`) | 18 | [../18](../18_Pricing.md) |
| `importPricesFromExcel` / `importIncPricesFromExcel` | `PriceMaintenance` | Bulk base / incremental price CSV import | `getBasePrice`, `updateItemBasePrice` | Import buttons | 18 | [../18](../18_Pricing.md) |
| `updateOrInsertPriceFormula` / `deletePriceFormula` | `FinancialMaintenance` | `PriceFormula` CRUD with full audit | inline SQL + audit | `SubmitButton_Click` / `DeleteButton_Click` | 18 | [../18](../18_Pricing.md) |
| `ExecuteSeating`, `getPriceLineGBPandEUR`, `getLine` | `CustomPricePerm` | Bespoke price-permutation export — **ORPHANED, never instantiated** (`BR-PRICE-074`) | inline SQL | none (dead) | 18 | [../18](../18_Pricing.md) |

---

## OCD Export — `OCDExport` (orphaned)

Source doc: [../21_OCD.md](../21_OCD.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `initParams(exportpath, siteId, catalogueId, productCodeId, currency, effectiveDate, newformat)` (internal) | `OCDExport` | Resolve catalogue name / lead time / product-code list before export | inline SELECT | **none — orphaned** (`BR-OCD-001`) | 21 | [../21](../21_OCD.md) |
| `execThread()` (internal) | `OCDExport` | Thread body → `startExport()` then completion `MsgBox` | `startExport` | **none — orphaned** | 21 | [../21](../21_OCD.md) |
| `startExport()` (private) | `OCDExport` | The actual OCD export driver (3 connections, per-ProductCode loop) | `ConnectionFactory.CreateNewConnection`, `writeData`, `Q-OCD-004..` | `execThread` (dead) | 21 | [../21](../21_OCD.md) |
| `writeData(string groupfilter, string productcode)` (private) | `OCDExport` | Serialise the assembled `OCDTables` to the semicolon-delimited OCD/GO CSV files | `StreamWriter` | `startExport` | 21 | [../21](../21_OCD.md) |

---

## Export & Import Pipelines — `SytelineExport`, `ExportThread`, `SIF*`, `BOMExport`, `ExportDPSDB*`

Source doc: [../22_Export.md](../22_Export.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `ExportButton_Click` | `SytelineExport` | Central export dispatch on active tab (SL8 / CSI / OFDA / price / PBOM) | `ExportSL8Data`, `ExportCSIData`, `ExportOFDA`, `ItemPriceExport.ExportItemPrices`, `BOMExport.ExportMaterials` | `SLExportButton_Click` (`MainMenu.cs:2761`) | 22 | [../22](../22_Export.md) |
| `initThread(...)` / `execThread()` | `ExportThread` | SL8 background export worker → `.xls`/`.asc` + helper files | `writeData`, SQL | `ExportSL8Data` | 22 | [../22](../22_Export.md) |
| `writeData(StreamWriter mywriter, string mydata, bool isItem)` (private) | `ExportThread` | Write one line to the SL8 export stream | `StreamWriter.Write` | `execThread` (`:4334/4483/5405/5420/5742`) | 22 | [../22](../22_Export.md) |
| `initParams(...)` / `execThread()` | `SytelineCSIExport` | CSI export worker → satellite `.csv` files | SQL, `StreamWriter` | `ExportCSIData` | 22 | [../22](../22_Export.md) |
| `initParams(...)` / `execThread()` | `OFDAExport` | OFDA-XML export worker → `PDMExport_OFDA_latest.xml` | `initArrays`, `PDMOptionDataReport`, `fnGetListPrice`, `writeXmlDataFile` | `ExportOFDA` | 22 | [../22](../22_Export.md) |
| `StartExport()` / `execThread()` | `SIFExport` / `SIFExportThread` | SIF `.top`/`.key`/`.opt` export worker | SQL, `StreamWriter` | `button_scheduler_Click` (dbacw8) | 22 | [../22](../22_Export.md) |
| `createOption` | `SIFImport` | Import path: `INSERT [Option]`/`OptionValue`/`ItemOptionValues` (+ range/category updates) | `PriceMaintenance.getBasePrice` | `button_import_update_Click` | 22 | [../22](../22_Export.md) |
| `ResolveCriteria` / `ExportMaterials` | `BOMExport` | `=IF()` criteria parse + PBOM material export (uses SyteLine live conn) | `CreateNewConnectionSyteLine` | Tools menu / tab3 | 22 | [../22](../22_Export.md) |
| `ExportDPSDB` / `ExportDPSDBThread` | `ExportDPSDB`, `ExportDPSDBThread` | Publish DPSDB (detach/copy) driven by `ProgressThread` → `xp_cmdshell dtsrun` | `ValidateImages.validateImages`, `ProgressThread` | Publish Database button | 22 / 24 | [../22](../22_Export.md) |

---

## Generation (Handbook Designer) — `HandbookDesigner`, `HBExclusions`

Source doc: [../23_Generation.md](../23_Generation.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `HandbookDesigner_Load` | `HandbookDesigner` | Populate selectors and load `Handbook*` definition rows | inline SELECTs | `HandbookButton_Click` (`MainMenu.cs:2902`) | 23 | [../23](../23_Generation.md) |
| `submitData()` (private) | `HandbookDesigner` | Persist handbook metadata edits | inline SQL | context-menu / edit handlers | 23 | [../23](../23_Generation.md) |
| `initValues(string table, int catalogueId, int categoryId, int handbookId, int groupId)` | `HBExclusions` | Manage per-group attribute/option exclusion lists | `INSERT`/`DELETE Handbook{Attribute,Option}Exclusions` | `menuAttributeExclusions_Click` / `menuOptionExclusions_Click` | 23 | [../23](../23_Generation.md) |
| `GroupList_SelectedIndexChanged` → `EXEC PDMPriceListReportForProductGroup` | `HandbookDesigner` | Preview increment-data text for one group (proc body server-side, **UNKNOWN**) | stored proc | Group selection | 23 | [../23](../23_Generation.md) |

---

## Utilities — `StaticDataMaintenance`, `MDBQuery`, worker threads

Source doc: [../24_Utilities.md](../24_Utilities.md)

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `SetSQL()` | `StaticDataMaintenance` | Build parameterised Select/Insert/Update commands per reference table (rare parameterised path) | — | constructor | 24 | [../24](../24_Utilities.md) |
| `updateButton_Click` | `StaticDataMaintenance` | Commit grid edits (+ audit; `PriceFormula` insert-new/delete-old) | `SqlDataAdapter.Update` | Update button (`:3555`) | 24 | [../24](../24_Utilities.md) |
| `ApplyFactors_Click` / `CalculateFactors` | `StaticDataMaintenance` | Recompute `PriceFormula.FirstPrice` from exchange rates or a % | `getExRate` | Apply Factors button | 24 | [../24](../24_Utilities.md) |
| `execThread()` (`ProgressThread`) | `ProgressThread` | Drive `xp_cmdshell 'dtsrun … Export_PDM2004_to_DPSDB'` for the DPS publish (`BR-UTIL-057`) | `xp_cmdshell` | `ExportDPSDBThread` | 24 | [../24](../24_Utilities.md) |
| `MDBQuery` query/find | `MDBQuery` | pCon Jet/Access MDB query & "find" tool (OLE DB) | `OleDbCommand` | `CADMaintenance`; `PConMdbQueryToolStripMenuItem_Click` | 24 / 11 | [../24](../24_Utilities.md) |

---

## Out of legacy scope

| Method | Class | Purpose | Calls | Called By | Module | Handbook doc |
|---|---|---|---|---|---|---|
| `build_product_explorer` | *(new Python app — MetatypeWizardStarter)* | Belongs to the **new** migration codebase, not the legacy C# PDM Maintenance handbook | UNKNOWN | UNKNOWN | — (not a legacy module) | UNKNOWN |

---

*End of Method Index. For the classes that own these methods see [Class_Index.md](Class_Index.md); for queries see
[SQL_Index.md](SQL_Index.md); for the end-to-end flow see [Call_Hierarchy.md](Call_Hierarchy.md).*
