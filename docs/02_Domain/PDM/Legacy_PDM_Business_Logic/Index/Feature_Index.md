# Feature Index

*Navigation layer for the legacy PDM Maintenance handbook (docs `00`–`28`). One row per
engineering feature: what it does, the main class(es) and method(s) that implement it, the SQL query
IDs that back it, the governing business-rule IDs, and the handbook doc where the full proof lives.
This is a cross-reference index — it does **not** restate the module docs. Module links use `../NN_Name.md`.
`UNKNOWN` / `—` marks anything not proven from the docs; nothing here is invented.*

> **Legend:** `Q-*` = SQL Server query; `O-*` = pCon/Jet OLE DB query; `BR-*` = business rule (see
> [../27_Business_Rules_Index.md](../27_Business_Rules_Index.md)). Method/class detail:
> [Method_Index.md](Method_Index.md), [Class_Index.md](Class_Index.md). SQL detail:
> [SQL_Index.md](SQL_Index.md). Tables: [Table_Index.md](Table_Index.md).

---

## 1. Feature matrix

| Feature | Purpose | Main class | Main methods | SQL (query IDs) | Business rules | Handbook doc |
|---|---|---|---|---|---|---|
| **Order Code Length / Truncation** | Assemble/limit an order code from the format key + per-site truncation and feature length | `ProductCodeEntry`, `Option` maint (`ProductDescriptions`), `OCDExport` | `AddButton_Click`, `parseOrderCodeFormatKey`, `getNextDisplayOrder` | `Q-ART-002`, `Q-OPT-002..010`, `Q-PVAL-002/003` | `BR-ART-005`, `BR-OPT-014`, `BR-OPT-016`, `BR-PVAL-013`, `BR-OCD-034` | [../06_Articles.md](../06_Articles.md), [../09_Options.md](../09_Options.md), [../08_Property_Values.md](../08_Property_Values.md), [../21_OCD.md](../21_OCD.md) |
| **Attribute Properties** | Maintain physical/configurable attributes and their values | `PhysicalMaintenance`, `ProductDescriptions`, `metaProperties` (DTO) | `initialiseGui`, `initialiseArrays`, `getAllProperties` | `Q-ATTR-001..036`, `Q-DESC-002` | `BR-ATTR-001..036` | [../07_Attributes.md](../07_Attributes.md) |
| **CET** | Product-level model refs + legacy CET tooling; feed OFDA/CET Designer | `CADMaintenance` (tab 0 Products/CET), `OFDAExport` | `AddModelButton_Click`, `ReplaceModelButton_Click` | `Q-CFG-*`, `Q-EXP-*` | `BR-CFG-*`, `BR-EXP-*` | [../11_Configuration.md](../11_Configuration.md), [../22_Export.md](../22_Export.md) |
| **pCon integration** | Read/write the pCon "creator" Jet MDBs (commercial/geometry/selection/class) via OLE DB | `CADMaintenance`, `PConPriceUpdate`, `MDBQuery` | `GetPconPackageId`, `getPConWorkspace`, `CreateNode`, `ClonePConPropertyClassOCD` | `O-CFG-001..026`, pCon price `Q-PRICE-*` | `BR-CFG-050..063`, `BR-PRICE-*` | [../11_Configuration.md](../11_Configuration.md), [../19_OAP.md](../19_OAP.md), [../20_ODB.md](../20_ODB.md), [../21_OCD.md](../21_OCD.md) |
| **Base Finish / secondary finish (`_C`/`_D`)** | Duplicate base-material nodes: `_C`/`_D` map to `_A`/`_B` and add a `_secondary` node for secondary finishes | `CADMaintenance` | `CreateNode`, `SetBaseButton_Click`, `BaseMaterials*Button_Click` | `O-CFG-020..026` (Jet node tree) | `BR-CFG-061`, `BR-CFG-062` | [../11_Configuration.md](../11_Configuration.md) |
| **Images** | Resolve, validate and rewrite image file references across all image-bearing entities | `GetImage`, `ValidateImages`, `ValidateImageThread`, `CADMaintenance` | `GetImage`, `SafeImageFromFile`, `URLExists`, `ValidateProductImages` | `Q-IMG-001..013`, `Q-OVAL-007` | `BR-IMG-001..072` | [../17_Images.md](../17_Images.md) |
| **Generation (Handbook)** | Author handbook/pricebook definition metadata; trigger report proc | `HandbookDesigner`, `HBExclusions` | `PDMPriceListReportForProductGroup` (proc call) | `Q-GEN-001..`, proc `PDMPriceListReportForProductGroup` (body UNKNOWN) | `BR-GEN-001..020` | [../23_Generation.md](../23_Generation.md) |
| **GO (`go_*` files)** | Emit Herman Miller OFML "go" metadata (articles/types/properties) | `metaArticles`, `metaTypes`, `metaProperties` (DTOs), `OCDExport` | `getAllProperties`, writer loop | `Q-OCD-*` (context) | `BR-ART-013`, `BR-CATEG-013`, `BR-OCD-*` | [../06_Articles.md](../06_Articles.md), [../07_Attributes.md](../07_Attributes.md), [../21_OCD.md](../21_OCD.md) |
| **OCD** | Export OFML Commercial Data CSVs (article/property/price/relation/codescheme) | `OCDExport` + `ocd*` DTOs | `initParams`, `startExport`, `writeData` (**orphaned — no live caller**) | `Q-OCD-001..020` | `BR-OCD-001..063` | [../21_OCD.md](../21_OCD.md) |
| **OAP / OAS** | pCon **selection** data domain (`pcr_data_sel_oas.mdb`) — no `OAP` identifier exists in source | `CADMaintenance`, `MDBQuery` | `GetPconPackageId` | `O-*` (Jet, `pcr_data_sel_oas.mdb`) | `BR-OAP-*` | [../19_OAP.md](../19_OAP.md) |
| **ODB** | pCon **geometry** domain (`pcr_data_geo_odb.mdb`): 2D/3D model refs + export flags | `CADMaintenance`, `MDBQuery`, `ExportLayoutStyleThread` | `UpdatePCon3D/2DModelReferences*`, `ApplyVisFlagToAllButton`, `check_excludefromexport` | `O-*` (Jet, `pcr_data_geo_odb.mdb`) | `BR-ODB-001..009` | [../20_ODB.md](../20_ODB.md) |
| **Search** | Templated search **dialogs** run from the ~42-item Query menu (not a generic runner) | `DataQuery`, `MainMenu` | `initDataQuery`, `*ToolStripMenuItem_Click` | `Q-SRCH-001..034` | `BR-SRCH-001..045` | [../14_Search.md](../14_Search.md) |
| **Filtering (UI Groups)** | Build OFML/OFDA configurator UI groups; full-coverage product→group match | `UIGroupMaintenance` | `getUIGroupIdForProduct`, `UIGroupsButton_Click` | `Q-FILT-001..018` | `BR-FILT-001..041` | [../15_Filtering.md](../15_Filtering.md) |
| **Ordering (DisplayOrder)** | Edit catalogue/category display ordinals | `OrderCategories` | `OrderCategories_Load`, `SubmitButton_Click` | `Q-ORD-*` | `BR-ORD-001..019` (category path + `AlphaButton` **dead**) | [../16_Ordering.md](../16_Ordering.md) |
| **Translations** | Multi-language text + Find&Replace across languages; push to pCon | `ProductDescriptions`, `DescriptionsFindReplace` | `TranslationButton_Click`, `language2update`, `getRSDescription` | `Q-TRAN-001..030`, `Q-DESC-*` | `BR-TRAN-001..030` | [../12_Translations.md](../12_Translations.md) |
| **Descriptions** | Short/long/application/marketing descriptions per entity/catalogue/pricebook | `ProductDescriptions` (mega-form) | `submitData`, `modifyOtherDescription`, `generateProgrammaticDescription` | `Q-DESC-001..037` | `BR-DESC-001..037` | [../13_Descriptions.md](../13_Descriptions.md) |
| **Pricing (reverse uplift)** | Derive base price from list via reverse uplift; forward via DB fns | `PriceMaintenance`, `FinancialMaintenance`, `PConPriceUpdate` | `getBasePrice` (`:6040`, public static), `showListPrices`, `importPricesFromExcel` | `Q-PRICE-003..`, `fnGetListPrice`/`fnGetListPriceByItem` (body UNKNOWN) | `BR-PRICE-010..103` | [../18_Pricing.md](../18_Pricing.md) |
| **Permissions** | 30 capability flags from `PDMUserPrivileges`; admin overrides | `AuthenticateUser`, `UserAdmin` | `setUserPrivileges`, grant/toggle handlers | `Q-AUTH-001`, `Q-PERM-001..006` | `BR-AUTH-001..008`, `BR-PERM-001..015` | [../01_Authentication.md](../01_Authentication.md), [../02_User_Permissions.md](../02_User_Permissions.md) |
| **Read-Only logic** | `PDMUserCatalogues.ReadOnly` **inverted** (1=full, 0=read); `DescriptionEdit` overrides | `AuthenticateUser`, `ProductDescriptions`, `CADMaintenance` | `_readOnlyCatalogues` capture, edit gating | `Q-PERM-*`, `Q-PRICE-003`, `Q-CFG-001` | `BR-PERM-*`, `BR-CFG-004`, `BR-DESC-*` | [../02_User_Permissions.md](../02_User_Permissions.md), [../11_Configuration.md](../11_Configuration.md), [../13_Descriptions.md](../13_Descriptions.md) |
| **Lead Time** | `Catalogue.LeadTime` + synthetic `LEADTIME = LeadTime + 5`; lead-time bands from cat 57/58 | `OCDExport` | `writeData` (LEADTIME synthesis) | `Q-OCD-001`, `Q-OCD-018` | `BR-OCD-030`, `BR-OCD-032`, `BR-ART-017` | [../21_OCD.md](../21_OCD.md), [../08_Property_Values.md](../08_Property_Values.md), [../06_Articles.md](../06_Articles.md) |
| **OBS / status (URL/ACT/OBS/HLD)** | `OptionValue.Status` 0=URL / 1=ACT / 2=OBS / 3=HLD lifecycle | `ProductDescriptions` (Option-value ctx menu) | `contextMenu_Click "(ACT)/(OBS)/(HLD)/(URL)"` | `Q-OVAL-*` | `BR-OVAL-*` | [../10_Option_Values.md](../10_Option_Values.md) |
| **EOS / EOSLite** | EOS-cloud gating + `EOSLiteDisplayOrder` ordering (stored negated in CAD path) | `ProductDescriptions`, `CADMaintenance` | `Set EOS Lite Display Order` handlers | `Q-OPT-004`, `Q-OPT-009`, `Q-CFG-011` | `BR-OPT-016` | [../09_Options.md](../09_Options.md), [../11_Configuration.md](../11_Configuration.md) |
| **Var Conditions (VARCOND)** | Generate pCon `PA_<prefix>` price relations for Super Product items | `SuperProductVarCondRelation`, `CADMaintenance` (menu delegate) | `ExportButton_Click` → `VarCondThread` → `exportPendingRelations`, `GenerateVARCONDForPAPRICING` | `Q-PROD-*`, pCon `tCOMd_Relation*` writes | `BR-PROD-061`, `BR-CFG-071`, `BR-OCD-041/050` | [../05_Products.md](../05_Products.md), [../11_Configuration.md](../11_Configuration.md), [../21_OCD.md](../21_OCD.md) |
| **Product Relations (`ocdRelation`/`DependentOptionValues`)** | Build option dependency relations + OCD relation objects | `OCDExport` (`ocdRelation`/`ocdRelationObj`), `AddNewData`/`StaticDataMaintenance` | writer relation build; `INSERT DependentOptionValues` | `Q-OCD-*`, `Q-UTIL-*` | `BR-OCD-041..050`, `BR-UTIL-056` | [../21_OCD.md](../21_OCD.md), [../10_Option_Values.md](../10_Option_Values.md) |
| **Fabric handling (option 8/28)** | Global fabric options: id 8=type, 28=colour, 3344/3346=secondary; `IsFabric` 0/1/2 | `CADMaintenance`, `ProductDescriptions`, `Option`/`OptionValue` maint | fabric-option handlers, mask rewrite | `Q-CFG-011`, `Q-DESC-*`, fabric-band `Q-EXP-*` | `BR-DESC-020`, `BR-CFG-*` | [../11_Configuration.md](../11_Configuration.md), [../10_Option_Values.md](../10_Option_Values.md), [../09_Options.md](../09_Options.md) |
| **Revit families** | Auto-assign North-American Revit family references (gated by `RevitCheck`) | `CADMaintenance`, `RevitThread` | `AutoAssignRevitButton`, `RevitThread` | `O-*` / `Q-CFG-*` | `BR-ODB-007` | [../20_ODB.md](../20_ODB.md), [../11_Configuration.md](../11_Configuration.md) |
| **SIF import / export** | Import `.top/.n01` SIF (+ PIP/OFDA xls/xml); export top/key/opt files | `SIFImport`, `SIFExportThread` | `createOption` (`INSERT [Option]/OptionValue/ItemOptionValues`), `execThread` | `Q-EXP-*` (SIF) | `BR-EXP-*` | [../22_Export.md](../22_Export.md) |
| **Syteline export** | Central export driver: SL8 xls, CSI csv, PBOM/Item-price csv | `SytelineExport`, `ExportThread`, `SytelineCSIExport` | `execThread`, tab handlers | `Q-EXP-001..060` | `BR-EXP-001..060` | [../22_Export.md](../22_Export.md) |
| **DPSDB publication** | Detach DPSDB, copy MDF/LDF to network, reattach, log | `PublishDatabase`, `ExportDPSDBThread`, `ProgressThread` | `execThread`, `xp_cmdshell dtsrun` | `Q-EXP-*`, `xp_cmdshell dtsrun` | `BR-EXP-*`, `BR-UTIL-057` | [../22_Export.md](../22_Export.md), [../24_Utilities.md](../24_Utilities.md) |

---

## 2. Notes

- **Dead / orphaned features** (do not migrate as-is): `CatalogueMaintenance` in-app form (menu launches
  `DPS.exe`), `OCDExport`/`ClippingsExport` orphaned threads, `CustomPricePerm` never instantiated,
  `OrderCategories` category path + `AlphaButton`, MainMenu Layout XML button (hidden). See
  [Class_Index.md](Class_Index.md) and [../28_Call_Hierarchy.md](../28_Call_Hierarchy.md).
- Deeper hidden/engineering detail for each feature is collected in
  [Engineering_Features.md](Engineering_Features.md).
