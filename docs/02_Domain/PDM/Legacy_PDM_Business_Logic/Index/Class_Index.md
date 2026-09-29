# Class Index

*Navigation layer for the legacy PDM Maintenance handbook: every significant class named across the
module docs (00–28), what it is for, its major responsibilities, its important methods, the modules it
relates to, and its key dependencies. This is a lookup/cross-reference layer — full proof lives in each
linked module doc. Dead/orphaned classes are flagged explicitly. `UNKNOWN` marks anything not provable
from the docs or source. Module links use `../NN_Name.md`; method detail is in
[Method_Index.md](Method_Index.md).*

> **Kinds:** **Form** = WinForms UI; **Static/module** = VB.NET `StandardModule` (global singleton);
> **Thread** = background worker; **DTO** = in-memory data holder for export serialisation (no DB access).

---

## 1. Application shell, session & security

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `MainMenu` (Form) | The application shell and permission-gated launcher | Build `enabledButtons` from 30 flags; host the top menu; launch every maintenance form; run the ~42-item Query menu; Publish DB trigger | `RefreshPermissions`, `SLExportButton_Click`, `PriceMaintButton_Click`, `PhysDataButton_Click`, `PDMImportButton_Click`, `*ToolStripMenuItem_Click` | 00, 02, and every feature module | `AuthenticateUser`, `Global`, `ConnectionFactory`, all feature forms; `Process.Start("DPS.exe")` |
| `Global` (Static/module) | Process-wide mutable session state | Hold connected server/DB, site, catalogue, category, product, currency, language, effective date; hard-coded server names & file paths (`filePaths`, `imageUnavailable`) | *(fields only)* | 00 (foundation, used everywhere) | none (referenced by all) |
| `AuthenticateUser` (Static/module) | Windows-identity authentication + authorization flags | Load the single `PDMUserPrivileges` row; expose 30 static capability flags; defaults on missing row | `setUserPrivileges(username)` | 01, 02 | `ConnectionFactory`, `PDMUserPrivileges` (`Q-AUTH-001`) |
| `ConnectionFactory` (Static/module) | Central DB connection construction | Choose connection string by server-name substring match; retry/backoff; forced read-only; SyteLine variant; password masking | `CreateNewConnection`, `CreateNewConnectionSyteLine`, `PingHost`, `HidePassword` | 00 (used by all) | SQL Server, SyteLine ERP |
| `UserAdmin` (Form) | Permission administration UI | CRUD of `PDMUserPrivileges`, per-catalogue grants (`PDMUserCatalogues`), SyteLine view grants (`SL7UserViews`) | flag-toggle / grant handlers | 02 | `ConnectionFactory`, `AuthenticateUser` (`Q-PERM-001..006`) |

---

## 2. Catalogues, categories & ordering

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `CatalogueMaintenance` (Form) — **DEAD SHELL** | In-app catalogue form that is never opened | Menu launches external `DPS.exe` instead; contains an always-true single-instance guard and a dead `AlphaButton` | *(unreached)* | 03 (`BR-CAT-002`, `BR-CAT-019`) | `Process.Start("DPS.exe")` (external) |
| `OrderCategories` (Form) | Reusable display-order (ordinal) editor | Edit `Catalogue.DisplayOrder` (`catalogueId==-1`, live) or `CatalogueProductCategories.DisplayOrder` (`>0`, **dead path**) | `OrderCategories_Load`, `SubmitButton_Click` | 16, 03, 04 | `ConnectionFactory`; launched by `ProductDescriptions.SortButton_Click` |
| `OrderCategories` (category path) — **DEAD** | Category-ordering branch | Only caller passes `-1`; branch never invoked; query has a missing-space SQL defect | — | 04, 16 (`BR-CATEG-010/011`, `BR-ORD-011/013`) | — |

---

## 3. Products, super products & articles

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `SuperProductMaintenance` (Form) | Super Product (BOM-like) definition CRUD | Maintain `ItemComponents` per Catalogue→Category→Product→Item→Component→Option; CSV import/export, cloning, price-report XLS, background validation; maintain `Product.IsSuperProduct` | `initialiseArrays`, `updateSPFlag`, `evalulateQuantity`, `updateSPCompList` | 05 | `ConnectionFactory`, `PDMOptionDataReport` |
| `SuperProductVarCondRelation` (Form) | Generate pCon VARCOND price relations | Build `PA_<prefix>` variant-condition relations and export into pCon commerce MDB (`tCOMd_*`) | `SuperProductVarCondRelation_Load`, `initArrays` | 05, 11 | `CADMaintenance.GetPconPackageIdOnly`, pCon `pcr_data_com_ocd.mdb` |
| `ProductCodeEntry` (Form/dialog) | Add a per-site `Product_Code` | Validate & insert order code, price code, unit code, base-price ref | `ProductCodeEntry_Load`, `AddButton_Click` | 06 | opened from `StaticDataMaintenance`; `Product_Code` table |
| `metaArticles` (DTO) | OFML `go_articles` serialisation holder | Carry article fields; emit positionally | ctor, `getAllProperties()` | 06, 21 | populated by `OCDExport` |
| `codeScheme` (DTO) | Product-code scheme holder | Carry code-scheme template fields for `ocd_codescheme` | ctor, `getAllProperties()` | 06, 21 | populated by `OCDExport` |

---

## 4. Attributes & OCD/GO property model

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `PhysicalMaintenance` (Form) | Physical/logistics item-attribute maintenance | Edit weight/volume/dimensions/freight/commodity/FSC on `Item`; WebEOS restrictions; delivery offsets; commodity-code tree | `PhysicalMaintenance_Load`, `PhysicalItemChange`, `SubmitButton_Click`, `CheckTables` | 07 | `ConnectionFactory`, `Item` + physical side-tables |
| `metaProperties` (DTO) | OFML `go_properties` serialisation holder | Carry 6 property-assignment fields; emit as CSV row | ctor, `getAllProperties()` | 07, 08 | populated by `OCDExport` (no DB) |
| `ocdProperty` / `ocdPropertyClass` / `ocdPropertyValue` (DTOs) | OCD variant-property model rows | Serialise `ocd_property` / `ocd_propertyclass` / `ocd_propertyvalue` files | ctor, `getAllProperties()` | 07, 08, 21 | populated by `OCDExport` |

---

## 5. Options & option values

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `OptionClass` (DTO) | SIF-export grouping holder | One option + its parallel value arrays | ctor | 09, 22 | `SIFExportThread` |
| `OptionGroup` (DTO) | SyteLine price-permutation holder | One option + its order codes / incremental prices | ctor | 09, 18, 22 | permutation export |
| `OptionData` (DTO) | Bulk column-array holder | Columns fed from `PDMOptionDataReport` | ctor | 10, 09 | `PDMOptionDataReport` |
| `AddNewData` (Form/dialog) | Generic add-new-record picker | Context-driven SQL; may `INSERT` fabrics/options/product-group codes | `submitData()` | 09, 10, 24 | `ConnectionFactory` |
| `AddDataList` (Form/dialog) | Generic list picker | Multi/single select with context-driven SQL | list handlers | 09, 10, 24 | `ConnectionFactory` |

> There is **no dedicated Option Maintenance form** — option definition editing is surfaced via
> `ProductDescriptions`/`CADMaintenance` context menus and SIF import.

---

## 6. Configuration / CAD / pCon

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `CADMaintenance` (Form) — **hub, largest file (~26k lines)** | CAD/OFML configuration workbench | Model references (`.dwg`/Revit); CAD materials/geometry; CAD layer schemes; group codes; full pCon/OFML integration (MDB read/write, package-id resolution, XLS round-trip, VARCOND, metatype export); image validation utilities | `GetPconPackageId`, `GetPconPackageIdOnly`, `CreateNode`, `GenerateVARCONDForPAPRICINGToolStripMenuItem_Click`, `ClonePConPropertyClassOCDToolStripMenuItem_Click`, `UIGroupsButton_Click` | 11, 04, 09, 15, 17, 19, 20 | `ConnectionFactory`, pCon Jet MDBs (`tCOMd_*`/`tGEOd_*`), `GetImage`, `MDBQuery`; embeds `PreviewThread`/`RevitThread` |
| `WebConfigurator` (Form) | Web-DPS configurator template builder | From an OFDA export XML, present features as dropdowns, build a web-DPS template + `hermanmiller.com` URL, optionally write `Product.WebDPSProduct` | feature-dropdown / write handlers | 11 | `ConnectionFactory`, OFDA XML |

---

## 7. Descriptions & translations

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `ProductDescriptions` (Form) — **hub** | Central multi-tab description maintenance | ~15 entity tabs; browse/filter grid; edit short/long/application text per language; catalogue/pricebook app-text overrides; programmatic descriptions; launch Find & Replace, Ordering | `submitData`, `modifyOtherDescription`, `generateProgrammaticDescription`, `getRSDescription`, `showTranslatedStatus`, `updateDataGrid` | 12, 13, 03, 04, 08, 10, 16, 17 | `ConnectionFactory`, `GetImage`, `DescriptionsFindReplace`, `OrderCategories` |
| `metaDescriptions` (DTO) | Inert 3-field data holder | `language`, `propertyValue`, `propertyDescription` — no persistence, no UI | ctor | 12, 13 | none (documented to record inertness) |
| `DescriptionsFindReplace` (Form/dialog) | Cross-language find & replace | Read primary-language `ShortDescription`; write replaced text into secondary language (Product tab only) | `sendData`, `FindNext`, `InsertButton_Click` | 12 | `ConnectionFactory` |

---

## 8. Search & filtering

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `DataQuery` (Form) — **shared** | Reusable search / lookup / drill-down dialog | Run a caller-supplied `SELECT` (token-substituted, injectable); drill-down hyperlinks; also performs writes (reassign PLC, reactivate, delete increments, hide-in-cloud); launches image validation | `initDataQuery`, `ApplyButton`/`ReactivateButton`/`DeleteButton` handlers | 14, 09, 17 | `ConnectionFactory`; driven by ~42 `MainMenu` handlers |
| `UIGroupMaintenance` (Form) | UI Groups / Layout Features maintenance | Filter Catalogue→Category→Range; match products to UI-group icons; create/rename/redefine/delete `CatalogueUIGroups`; OFDA-XML mode via `groupdata.txt` (dbacw8) | `getUIGroupIdForProduct`, `loadUIGroups`, `updateGroups`, `updateRange` | 15, 11 | `ConnectionFactory`; launched live from `CADMaintenance.UIGroupsButton_Click`; **dead** MainMenu Layout XML entry |

---

## 9. Images

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `GetImage` | Image path resolver / loader | Turn an `ImageFile` token into a bitmap by probing UNC/EOS/HTTP base paths; token expansion; HTTP fetch | `GetImage`, `URLExists`, `GetImageFromURL`, `SafeImageFromFile` | 17 (used app-wide) | `Global.filePaths`, `WebClient`, file share |
| `ValidateImages` | Publish-time image reference check | Verify `WFImageFile` refs exist; auto-null broken refs (silent) | `validateImages()` | 17 | called by `ExportDPSDB` |
| `ValidateImageThread` (Thread) | Interactive unresolved-image report | Background scan of product/attribute/option image refs; `debug_form` report | `InitThread`, `ExecThread` | 17 | launched by `DataQuery` ("Unresolved…" titles) |

---

## 10. Pricing

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `PriceMaintenance` (Form) | Base/incremental price grid maintenance | View/edit base (`BasePrice1/2/3`) and incremental prices per site/currency/catalogue; CSV import; permutation export; reverse-uplift maths | `getBasePrice`, `importPricesFromExcel`, `importIncPricesFromExcel`, `submitData`, `showListPrices` | 18 | `ConnectionFactory`, `PriceFormula`/`PriceMatrix`/`ExchangeRate`, `UpdatePricesThread`, `IncPriceThread` |
| `FinancialMaintenance` (Form) | Price-formula CRUD | Insert/update/delete `PriceFormula` with full audit | `updateOrInsertPriceFormula`, `deletePriceFormula`, `SubmitButton_Click` | 18 | `ConnectionFactory`, `PDMAudit` |
| `PConPriceUpdate` (Form) | pCon price push | Copy PDM list prices into external pCon MDB (`tCOMd_*`) | opens `UpdatePriceThread.execThread` | 18, 11 | pCon Jet MDB, `UpdatePriceThread` |
| `CustomPricePerm` (Form) — **ORPHANED, never instantiated** | Bespoke price-permutation export | Permutation maths for a flat price file — unreachable | `ExecuteSeating`, `getPriceLineGBPandEUR`, `getLine` | 18 (`BR-PRICE-036/074`) | none (dead) |
| `ocdPrice` (DTO) | OCD `ocd_price` row holder | In-memory price surcharge row | ctor, `getAllProperties()` | 18, 21 | populated by `OCDExport` |

---

## 11. OCD export (orphaned) & OCD DTOs

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `OCDExport` (Form) — **ORPHANED / DEAD** | OFML Commercial Data export engine | Build a full OCD/GO package per Product Code; constructed once by `SytelineExport` but `initParams`/`execThread` **never called** | `initParams`, `execThread`, `startExport`, `writeData` | 21, 06, 07, 08 (`BR-OCD-001`) | `ConnectionFactory`, all `ocd*`/`meta*` DTOs, `PDMOptionDataReport` |
| `ocdArticle` / `ocdArtBase` / `ocdArtDesc` (DTOs) | OCD article rows | `ocd_article` / `ocd_artbase` / `ocd_artdesc` serialisation | ctor, `getAllProperties()` | 06, 21 | populated by `OCDExport` |
| `ocdCodeScheme` (DTO) | OCD code-scheme row | `ocd_codescheme` serialisation | ctor, `getAllProperties()` | 06, 21 | populated by `OCDExport` |
| `ocdRelation` / `ocdRelationObj` (DTOs) | OCD variant-condition relations | `ocd_relation` / `ocd_relationobj` constraint rows + bindings | ctor, `getAllProperties()` | 21 | populated by `OCDExport` |

---

## 12. Export & import pipelines

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `SytelineExport` (Form) | Central export driver | Tab-dispatch SL8 / CSI / OFDA / item-price / PBOM; scheduler button; constructs the (orphaned) `OCDExport` | `ExportButton_Click`, `ExportSL8Data`, `ExportCSIData`, `ExportOFDA`, `button_scheduler_Click` | 22, 21 | `ExportThread`, `SytelineCSIExport`, `OFDAExport`, `ItemPriceExport`, `BOMExport` |
| `ExportThread` (Thread) | SL8/millerCAD export worker | Stream `.xls`/`.asc` + helper files; BOM branch | `initThread`, `execThread`, `writeData` | 22 | `ConnectionFactory`, `SytelineBOMExport` |
| `SytelineBOMExport` (Thread) | SL8 BOM export | Item/BOM stream for SyteLine load | `execThread` | 22 | `ConnectionFactory` |
| `SytelineCSIExport` (Thread) | CSI configurable-item export | Satellite `.csv` files (items/materials/prices) | `initParams`, `execThread` | 22 | `ConnectionFactory` |
| `SyteLineExportValidator` | Pre-export validation | Validate SL export data integrity | validation methods (UNKNOWN detail) | 22 | `ConnectionFactory` |
| `OFDAExport` (Thread) | OFDA-XML export | Build `PDMExport_OFDA_latest.xml` from per-item SQL + `PDMOptionDataReport` + `fnGetListPrice` | `initParams`, `execThread`, `initArrays`, `writeXmlDataFile` | 22 | `ConnectionFactory`, `OFDAExportManager` |
| `OFDAExportManager` | OFDA export orchestration | Coordinate OFDA export runs | UNKNOWN | 22 | `OFDAExport` |
| `SIFImport` (Form) | SIF/PIP/OFDA inbound import | Read `.top`/`.sif`/Excel/XML; create options/values/increments; update ranges/categories | `button_import_update_Click`, `createOption` | 22 | `ConnectionFactory`, `PriceMaintenance.getBasePrice` |
| `SIFExport` / `SIFExportThread` (Form/Thread) | SIF outbound export | Write `.top`/`.key`/`.opt` option catalogue | `StartExport`, `execThread` | 22 | `ConnectionFactory` |
| `BOMExport` | PBOM material export | `=IF()` criteria parse; PBOM material export using SyteLine live connection | `ResolveCriteria`, `ExportMaterials` | 22 | `CreateNewConnectionSyteLine` |
| `ExportDPSDB` / `ExportDPSDBThread` (Thread) | DPSDB publication | Detach/copy published DPSDB; validate images | via `ProgressThread` | 22, 24, 17 | `ProgressThread`, `ValidateImages`, `xp_cmdshell dtsrun` |
| `SDXmlExport` (Form) | Static-data XML export | Dump site/rate/product-code/formula to `.xml` | `okButton_Click` | 22, 24 | launched by `StaticDataMaintenance` |
| `ClippingsExport` — **ORPHANED** | Clippings XML export | Not wired to any live path | UNKNOWN | 22 (§7) | none (dead) |
| `ScheduleExport` (Form) | Queue products for later SL export | Insert/delete `ExportSchedule` rows | schedule handlers | 22 | `ConnectionFactory`, `ExportSchedule` |
| `ExportQueueManager` | Export queue management | Manage queued export jobs | UNKNOWN | 22 | `ExportSchedule` |

---

## 13. Generation (Handbook / Pricebook Designer)

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `HandbookDesigner` (Form) | Handbook/pricebook **metadata editor** (not a renderer) | Author `Handbook*` definitions: groups, products, attributes, options, exclusions, publish flags; preview increment data via stored proc | `HandbookDesigner_Load`, `submitData`, `menuAdd*`/`menuRemove*` handlers, `GroupList_SelectedIndexChanged` | 23 | `ConnectionFactory`, `HBExclusions`, `PDMPriceListReportForProductGroup` (server-side render UNKNOWN) |
| `HBExclusions` (Form/dialog) | Per-group exclusion lists | Manage `Handbook{Attribute,Option}Exclusions` | `initValues(table, catalogueId, categoryId, handbookId, groupId)` | 23 | `ConnectionFactory` |

---

## 14. Utilities, static data & worker threads

| Class | Purpose | Major responsibilities | Important methods | Related modules | Dependencies |
|---|---|---|---|---|---|
| `StaticDataMaintenance` (Form) | Reference/static data editor ("Financial Data Maintenance") | 7-tab grid editor for Currency/Site/ExchangeRate/Language/ProductCode/PriceFormula/PriceMatrix; **notable parameterised-SQL exception**; tab visibility by permission | `SetSQL`, `updateButton_Click`, `ApplyFactors_Click`, `CalculateFactors`, `ImportStaticData` | 24, 18, 06 | `ConnectionFactory`, `SDXmlExport`, `ProductCodeEntry`, `PDMAudit` |
| `MDBQuery` (Form) | pCon Jet/Access MDB query & "find" tool | OLE DB query over pCon `.mdb`; nearest thing to a generic query runner | query/find handlers | 24, 11 | `OleDbCommand`, pCon MDBs |
| `ProgressThread` (Thread) | DPS DB publish worker | Drive `xp_cmdshell 'dtsrun … Export_PDM2004_to_DPSDB'` (hard-coded server/package) | `execThread` | 24, 22 (`BR-UTIL-057`) | `ExportDPSDBThread`, SQL Server |
| `DelayThread` (Thread) | 500 ms debounce timer | Debounce the CADMaintenance category filter | thread body | 24, 11 | `CADMaintenance` |
| `TimerThread` (Thread) | Elapsed-time label | `HH:MM:SS` label for long operations | thread body | 24 | export/import forms |
| `UpdatePriceThread` / `UpdatePricesThread` (Threads) | pCon / bulk price push workers | Copy PDM list prices into pCon MDB; slot-2 base import | `execThread` | 18, 11 | pCon Jet MDB |
| `IncPriceThread` (Thread) | Async grid price population | Load incremental prices into the Price grid | `execThread` | 18 | `ConnectionFactory` |
| `UpdateThread` (Thread) | pCon node/model push worker | Push CAD nodes/model references (calls `CADMaintenance.CreateNode`) | `execThread` | 11 | `CADMaintenance.CreateNode` |
| `ExportLayoutStyleThread` (Thread) | Layout-style export worker | Duplicate `getUIGroupIdForProduct` matcher during export | `getUIGroupIdForProduct`, `execThread` | 15, 22 | `ConnectionFactory` |
| `PreviewThread` / `RevitThread` (Threads, embedded in CADMaintenance) | Image preview / Revit-family parsing | Background image + Revit-family processing (bodies **UNKNOWN**) | thread bodies | 11, 17 | `CADMaintenance` |
| `InputForm` / `EditDialog` / `ApplicationText` / `debug_form` (Forms) | Generic dialogs | Input / single-value edit / read-only text+image / scrollable text output | dialog handlers | 24 | on-demand across forms |

---

## Dead / orphaned classes — quick reference

| Class | Status | Proof | Module doc |
|---|---|---|---|
| `CatalogueMaintenance` | **Dead shell** — in-app form never opened; menu launches external `DPS.exe` | `BR-CAT-002`, `BR-CAT-019` | [../03](../03_Catalogues.md) |
| `OCDExport` | **Orphaned** — constructed once by `SytelineExport`, `initParams`/`execThread` never called | `BR-OCD-001`, `BR-OCD-062` | [../21](../21_OCD.md) |
| `ClippingsExport` | **Orphaned** — not wired to any live path | 22_Export §7 | [../22](../22_Export.md) |
| `CustomPricePerm` | **Orphaned** — never instantiated; permutation maths unreachable | `BR-PRICE-036`, `BR-PRICE-074` | [../18](../18_Pricing.md) |
| `OrderCategories` category branch | **Dead** — only caller passes `catalogueId = -1` | `BR-CATEG-010/011`, `BR-ORD-011/013` | [../16](../16_Ordering.md) |

---

*End of Class Index. For per-method detail see [Method_Index.md](Method_Index.md); for queries see
[SQL_Index.md](SQL_Index.md); for tables see [Table_Index.md](Table_Index.md); for flow see
[Call_Hierarchy.md](Call_Hierarchy.md) and [../28_Call_Hierarchy.md](../28_Call_Hierarchy.md).*
