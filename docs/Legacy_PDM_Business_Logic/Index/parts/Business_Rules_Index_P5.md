## BR-CFG — Configuration (CAD / Web Configurator) → [11_Configuration](../../11_Configuration.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-CFG-001 | CAD Maintenance button shows only if `AuthenticateUser.CADMaintenance`. | `MainMenu` button gate | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-002 | Web Configurator button shows only if `AuthenticateUser.CoreMaintenance`. | `MainMenu` button gate | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-003 | Only one OFDA Export Manager **or** Web Configurator instance may be open. | `Global.ofdaManagerOrWebConfigActive` guard | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-004 | Editing is allowed only when the selected catalogue is not read-only. | read-only gate (`_readOnlyCatalogues[idx]==0`) | Q-CFG-001 | PDMUserCatalogues | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-005 | A hardcoded pCon-creator allow-list (`_pConCreatorUsers`) governs pCon-creation controls. | `initArrays` (`_pConCreatorUsers`) | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-006 | A synthetic `< SP Components >` category (id 999) is always appended. | `categorySelection` | Q-CFG-005 | ItemComponents, Item | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-007 | Unreleased items are excluded unless `UnreleasedCheck` is ticked. | `categorySelection` (UnreleasedCheck) | Q-CFG-003, Q-CFG-004 | CatalogueItems, CatalogueItemsUnreleased | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-008 | Item filter: a trailing `+` switches to a range/prefix match. | `item_filter` (Items tab) | Q-CFG-004 | Item | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-009 | Category ordering uses `DisplayOrder` with `-1 → 9999` (unassigned last), English. | `categorySelection` | Q-CFG-002 | CatalogueProductCategories, OtherDescription | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-010 | The attribute list always includes the sentinel `-1` in its linked-attribute set. | `attributeSelection` | Q-CFG-008 | Attribute | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-011 | `[Option]`/`[Attribute]` are bracket-quoted (T-SQL reserved words). | (pervasive SQL quoting) | Q-CFG-010, Q-CFG-008 | Option, Attribute | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-012 | In the Products tab only, global fabric handling applies. | `optionSelection` (Products tab) | Q-CFG-010 | Option | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-013 | A value "needs CAD attention" (Products tab) when it has no model/material. | `optionValueSelection` | Q-CFG-016 | OptionValue (CADMaterial, ImageFile, IsFabric) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-014 | `CADMaterial` is stored per value in `<Attribute\|Option>Value.CADMaterial`. | `SelectMaterial`, generic material writer | Q-CFG-017, Q-CFG-018 | AttributeValue, OptionValue (CADMaterial) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-015 | Model references are pipe-delimited strings (`Product.ModelList`). | `updateProductModels` | Q-CFG-020, Q-CFG-021 | Product (ModelList), Item (CADImage3D) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-016 | `Item.CADImage2D = 'master'` marks the master item of a category. | `GetPconPackageIdOnly` (master lookup) | Q-CFG-050 | Item (CADImage2D) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-017 | Add-model dialogs reject files not `.dwg` or outside the allowed root. | add-model dialog handlers | — | Product (ModelList) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-018 | Adding a model to a Super Product prompts a confirmation warning. | `updateProductModels` (SP guard) | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-020 | `LayerNameList` is a pipe-delimited layer-key list per Attribute/Option. | `UpdateLayers` | Q-CFG-030, Q-CFG-031 | LayerNameList, ProductCategory (CADPlanning) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-021 | New group-code descriptions get a `DescriptionId` via max+1. | group-code editor (`BaseMaterialsAdd/Update`) | Q-CFG-035 | OtherDescription (RelatedTable='GroupCode') | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-041 | "Apply to all" copies a value's `CADSuffix` to every non-obsolete value. | `ApplyDomainsToAll` | Q-CFG-042 | AttributeValue, OptionValue (CADSuffix) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-042 | `HideByDefault` write for options guards `AND HideByDefault <= 9`. | `option_display_SelectedIndexChanged` | Q-CFG-043 | Option (HideByDefault) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-043 | Base materials are stored pipe-delimited in `Product.CADPlaceProgram`. | `SetBaseButton_Click` / remove | Q-CFG-044 | Product (CADPlaceProgram) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-050 | `CADSchemes.Version` is the resolved pCon package id (scheme keyed on it). | `updateBaseMaterials`, `BaseMaterialsAdd/Update/Remove` | Q-CFG-040 | CADSchemes (Version) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-051 | pCon article-prefix length comes from the first comma-token of `Item.Notes`. | `getArticlePrefixLength`, `getPConPrefixLengthByCategory` | Q-CFG-050 | Item (Notes) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-052 | If the resolved prefix length exceeds the item length, a warning is shown. | `getArticlePrefixLength` (length guard) | — | Item | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-053 | `GetPconPackageIdOnly` resolves a package id by matching each category master-item. | `GetPconPackageIdOnly` | O-CFG-001, O-CFG-002, Q-CFG-050 | tGEOd_* (MDB), tCOMd_* (MDB) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-060 | `getPConWorkspace`: `"auto"` preference resolves the workspace automatically. | `getPConWorkspace` | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-061 | `CreateNode` caches created geometry node ids by key. | `CreateNode` | O-CFG-011..014 | tGEOd_Node2D, tGEOd_Node3D (MDB) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-062 | Translation-driven class-ref nodes: a `GoYLT…:param` translation creates a node. | `CreateNode` | O-CFG-011..014 | tGEOd_* (MDB) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-063 | Node manufacturer/package refs are hardcoded (OFML class refs). | `CreateNode` | O-CFG-011..014 | tGEOd_* (MDB) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-070 | `ClonePConPropertyClassOCD` deep-copies `tCOMd_Class → tCOMd_Property → …`. | `ClonePConPropertyClassOCDToolStripMenuItem_Click` | O-CFG-020..026 | tCOMd_Class, tCOMd_Property, tCOMd_PropValue (MDB) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-071 | `GenerateVARCONDForPAPRICING` opens the pricing UI rather than building VARCOND SQL itself. | `GenerateVARCONDForPAPRICING` (opens `SuperProductVarCondRelation`) | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-072 | Program codes for the current catalogue are obtained from the catalogue programs query. | `PriceMaintenance.getPConProgramCodes` | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-073 | The pCon-data XLS import auto-picks up sibling language files. | `UpdatePConDataFile` | — | OtherDescription (langs 1/2/5/9) | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-080 | `initialiseGui` colour-codes the form background by connected DB/server. | `initialiseGui` | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-081 | Default catalogue selection = `DefaultCatalogueId` if present in the list. | `initArrays` (default select) | Q-CFG-001 | Catalogue, PDMUserCatalogues | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-082 | Revit auto-assign (`RevitCheck`) is made visible only for user `dbacw8`. | tab visibility (Products tab) | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-090 | Items tab (idx 1) shows the pCon panels and metatype data. | `TabControl1_SelectedIndexChanged` | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-091 | Products tab (idx 0) is the inverse of 090 — shows CET controls and category tools. | `TabControl1_SelectedIndexChanged` | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-092 | In the Items tab, a non-`"auto"` workspace whose folder is missing is handled/guarded. | `TabControl1_SelectedIndexChanged` | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-901 | Web Configurator Apply requires a non-empty product filter and template, else warn. | `ApplyButton_Click` (Web Configurator) | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-902 | Filter transforms: `*` → `%`; a ` !` token splits off an exclusion. | `ApplyButton_Click` (filter transform) | O-CFG (UNKNOWN) | Item | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-903 | `UNION SELECT -1` is appended so the `IN (…)` set is never empty. | `ApplyButton_Click` | UNKNOWN | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-904 | The built URL is a fixed Web Configurator address. | `updateWebConfigTemplate` | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-905 | Feature dependency: `selectFeatureValue` shows/hides and re-stacks downstream features. | `selectFeatureValue` | — | — | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-906 | Features whose element is an Attribute-with-children are rendered specially. | `featureIsAttributeWithChildren`, `updateWebConfigTemplate` | — | Attribute | [11_Configuration](../../11_Configuration.md) |
| BR-CFG-907 | The `>>>` button opens the URL specifically in `chrome.exe` (hardcoded). | `>>>` button handler | — | — | [11_Configuration](../../11_Configuration.md) |

## BR-PRICE — Pricing → [18_Pricing](../../18_Pricing.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-PRICE-010 | Site 20 excluded (`SiteId NOT IN (20)`); on export site 20 → 1. | `initialiseArrays` | Q-PRICE-001 | Site | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-011 | Product-code override precedence: `ProductCodeIdOverride` else `Product.ProductCodeId`. | (Q-PRICE-020 CASE) | Q-PRICE-020 | Item, Product, Product_Code | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-012 | Catalogue scope = `CatalogueItems` ∪ `CatalogueItemsUnreleased` ∪ `IsSuperItem = 1`. | import validation | Q-PRICE-020 | CatalogueItems, CatalogueItemsUnreleased, Item | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-013 | Newest effective record wins (`EffectiveDate DESC`, `<= target`). | `getBasePrice` | Q-PRICE-020, Q-PRICE-032 | PriceFormula, ExchangeRate | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-014 | Catalogue 81 ("Spares & Parts") drops the catalogue restriction (all items). | import validation | Q-PRICE-020 | Catalogue | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-015 | `ProductCategory.USCategory = 1` routes reads/writes to `US*` tables. | `isUSCategory` | Q-PRICE-005 | ProductCategory (USCategory) | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-016 | Currency `OGC` is excluded from the Financial currency list. | financial currency list | — | Currency | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-017 | pCon price list `default` excluded; `_` in a label maps to SQL `%`. | pCon price-list selection | Q-PRICE-091 | tCOMd_PriceList2 (MDB) | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-020 | Base CSV = `[item],[list_price]`; only `isNumericalValue`-passing rows accepted. | base import (`isNumericalValue`) | Q-PRICE-020 | Item | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-021 | Inc CSV = `[item],[order display/id],[order_code],[inc_list_price]` with checks. | inc import | Q-PRICE-020 | ItemOptionValues | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-022 | Filename prefix drives target: `us_` → US slot-2 (Singapore+USD); `mexico_` → Mexico slot-2. | `UpdatePricesThread` | Q-PRICE-095 | Item (BasePrice2) | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-023 | `display_selector`: 0 = update BasePrice (reverse-uplift), 1 = update ListPrice directly. | `getBasePrice` | Q-PRICE-030..032 | Item | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-024 | When the count SQL exceeds 100,000 chars it is split at the next `" OR "` and run in two parts. | base import (SQL length guard) | Q-PRICE-020 | — | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-025 | Order-code match is case/`#`-insensitive (`ToLower().Replace("#","")`). | inc import (order-code match) | — | ItemOptionValues, OptionValue | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-026 | An option code resolving to more than one value is rejected ("unable to find unique optval"). | inc import (ambiguity check) | — | OptionValue | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-027 | Inc import matches on OptionId or DisplayOrder, but DisplayOrder match is disallowed for position `8`. | inc import (position vs id) | — | Option, ItemOptionValues | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-030 | Reverse-uplift (`getBasePrice`) computes base from list (inverse of the DB uplift). | `getBasePrice` | Q-PRICE-030, Q-PRICE-031, Q-PRICE-032 | Site, ExchangeRate, PriceMatrix, PriceFormula | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-031 | Forward uplift (base→list) is DB-side via `fnGetListPrice`/`fnGetListPriceByItem` (formula UNKNOWN). | `getListPrice`, `fnGetListPrice*` | Q-PRICE-050, Q-PRICE-051 | (SQL functions — internals UNKNOWN) | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-032 | Rounding override: product code `zz-zz` forces rounding mode 2. | `getListPrice` | Q-PRICE-050 | — | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-033 | Base/inc slot chosen by `BasePriceRef` (1/2/3); other → invalid. | `IncPriceThread` | Q-PRICE-020, Q-PRICE-043 | Item, Product_Code (BasePriceRef) | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-034 | Slot-2 (`BasePrice2`/`IncrementalPrice2`) is the US/Mexico base slot, independent of `BasePriceRef`. | `UpdatePricesThread` | Q-PRICE-095, Q-PRICE-096 | Item (BasePrice2), ItemOptionValues (IncrementalPrice2) | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-035 | Fabric options priced by `FabricBands.PriceBand` + `Application`, not per value. | `IncPriceThread` | Q-PRICE-060 | FabricBands, CatalogueOptionValues | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-036 | `CustomPricePerm` permutation maths (orphaned — never instantiated; see §7). | `getPriceLineGBPandEUR`, `getLine` | Q-PRICE-098, Q-PRICE-099 | ExchangeRate, PriceFormula, PriceMatrix | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-040 | No-op skip: if the new base equals the existing slot (or both ~zero/NULL) it is counted "unchanged". | `updateItemBasePrice` | Q-PRICE-040, Q-PRICE-043 | Item | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-041 | A supplied `"0"` is converted to `NULL` before writing (base and inc). | `updateItemBasePrice`, `updateItemOptIncPrice` | Q-PRICE-043, Q-PRICE-047 | Item, ItemOptionValues | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-042 | When no `ItemOptionValues` row exists and the new inc is `NULL`, no row is inserted. | `updateItemOptIncPrice` | Q-PRICE-046, Q-PRICE-047 | ItemOptionValues | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-043 | Rows with all three inc slots NULL are deleted (empty-row cleanup). | inc housekeeping | Q-PRICE-097 | ItemOptionValues | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-050 | `PDMUserCatalogues.ReadOnly` is loaded to gate editability (inverted convention). | catalogue load | Q-PRICE-003 | PDMUserCatalogues | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-051 | `ReadOnlyFinancial` (with other flags) governs the financial/static maintenance menu group. | `MainMenu` menu gate | — | PDMUserPrivileges | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-052 | `FinancialMaintenance` opens only on right-click of the Static Maintenance button. | Static Maintenance button (right-click) | — | — | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-053 | `FormulaMaintenance` gates price-formula editing surfaces in `StaticDataMaintenance`. | `StaticDataMaintenance` gates | — | PDMUserPrivileges | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-054 | `PriceMaintenance`/`CurrencyMaintenance`/`ExchangeRates` are independent boolean privileges. | `AuthenticateUser` | — | PDMUserPrivileges | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-060 | Every changed base price is audited (`Transactions` + `ItemPriceUpdates`) before the UPDATE. | `updateItemBasePrice` | Q-PRICE-041, Q-PRICE-042, Q-PRICE-042b | Transactions, ItemPriceUpdates | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-061 | Every PriceFormula change is audited into `PDMAudit.dbo.PFUpdates` with `Prev*` columns. | `FinancialMaintenance` | Q-PRICE-073 | PDMAudit.dbo.PFUpdates | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-062 | Audit is disabled on `eoscloud`; off-cloud, a second hard-coded `PDMAudit` connection is opened. | `updateItemBasePrice` (audit connection) | — | PDMAudit | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-070 | `FirstBase` defaults to `'P1'` on every new PriceFormula. | `FinancialMaintenance` insert | Q-PRICE-074 | PriceFormula | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-071 | Default currency = 1 (GBP by id). | `AuthenticateUser` (DefaultCurrencyId) | — | — | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-072 | `showPConButtons` builds a date/currency gate but then unconditionally sets `result = true` — dead gate. | `showPConButtons` | — | — | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-073 | `UpdatePConItemPrice` special-cases specific `RBK…` items and `DWEV`-prefixed width derivation. | `UpdatePConItemPrice`, `UpdatePriceThread` | Q-PRICE-090..094 | tCOMd_Price, tCOMd_GlobalPrice, Item (Notes) | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-074 | `CustomPricePerm` hard-coded ids (catalogues 4/30, `AE` exclusions, sized arrays). | `CustomPricePerm` | Q-PRICE-098, Q-PRICE-099 | ExchangeRate, PriceFormula | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-080 | Missing-link diagnostics emit specific messages per missing PLC/PriceMatrix/PriceFormula join. | `validateProductLineCode` | Q-PRICE-021, Q-PRICE-022, Q-PRICE-023 | Product_Code, PriceMatrix, PriceFormula | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-081 | `getLine` skips an item if base price is DBNull, negative, or no price row found. | `getLine` | Q-PRICE-099 | Item | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-082 | Item `Notes` prefix length is honoured only when `≤ 20`. | `UpdatePriceThread` | Q-PRICE-090 | Item (Notes) | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-083 | Errors surface via MsgBox/`debug_form`; no transactions, so committed rows are not rolled back. | catch blocks (MsgBox / `debug_form`) | — | — | [18_Pricing](../../18_Pricing.md) |
| BR-PRICE-100 | **SQL injection everywhere**: item/order codes, selector text and CSV values concatenated straight into SQL/OLE DB. | (all inline query builders) | — | — | [18_Pricing](../../18_Pricing.md) |

## BR-OAP — OAP / pCon Selection Data → [19_OAP](../../19_OAP.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-OAP-001 | pCon selection data is stored per workspace in `pcr_data_sel_oas.mdb` (Jet). | `MDBQuery`, `CADMaintenance` | O-OAS-001, O-OAS-002 | pcr_data_sel_oas.mdb (MDB, tables UNKNOWN) | [19_OAP](../../19_OAP.md) |
| BR-OAP-002 | `MDBQuery` exposes exactly four pCon domains — `OCD`, `ODB`, `OAS`, `CLS`. | `MDBQuery` (`database_selector`) | — | pcr_data_com_ocd/geo_odb/sel_oas/typ_cls.mdb (MDB) | [19_OAP](../../19_OAP.md) |
| BR-OAP-003 | The selection MDB path follows `<pConPath>WS\<workspace>\pcr_data_sel_oas.mdb`. | `CADMaintenance`, `MDBQuery` | O-OAS-002 | pcr_data_sel_oas.mdb (MDB) | [19_OAP](../../19_OAP.md) |
| BR-OAP-004 | Access to selection data requires the `CADMaintenance` privilege (whole-form gate). | `MainMenu` gate | — | — | [19_OAP](../../19_OAP.md) |
| BR-OAP-005 | There is no standalone OAS/OAP maintenance UI; selection data is only reachable via `MDBQuery`. | `CADMaintenance`, `MDBQuery` | — | — | [19_OAP](../../19_OAP.md) |
| BR-OAP-006 | UNKNOWN: the doc's "OAP" naming vs the code's "OAS" domain label may be an inconsistency. | UNKNOWN | UNKNOWN | UNKNOWN | [19_OAP](../../19_OAP.md) |

## BR-ODB — ODB / Geometry Data → [20_ODB](../../20_ODB.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-ODB-001 | ODB (geometry) data is stored in per-workspace Jet MDB files. | `MDBQuery`, `CADMaintenance` | O-ODB-001, O-ODB-002 | pcr_data_geo_odb.mdb (MDB) | [20_ODB](../../20_ODB.md) |
| BR-ODB-002 | Geometry MDB path = `<pConPath>WS\<workspace>\pcr_data_geo_odb.mdb`. | `CADMaintenance` | O-ODB-002 | pcr_data_geo_odb.mdb (MDB) | [20_ODB](../../20_ODB.md) |
| BR-ODB-003 | The correct geometry package per catalogue/category is resolved by package lookup. | `GetPconPackageId("geo_odb", …)` | O-ODB-003 | tGEOd_Package (MDB) | [20_ODB](../../20_ODB.md) |
| BR-ODB-004 | Items may be individually excluded from the ODB export. | `check_excludefromexport` | — | Item (ODB exclude flag — name UNKNOWN) | [20_ODB](../../20_ODB.md) |
| BR-ODB-005 | 2D and 3D model references are updated by separate menu actions. | `UpdatePCon2D/3DModelReferencesToolStripMenuItem` | — | tGEOd_Node2D, tGEOd_Node3D (MDB), Item (CADImage2D/3D) | [20_ODB](../../20_ODB.md) |
| BR-ODB-006 | ODB/transparency/visibility flags can be bulk-applied to all instances of a model. | `ApplyVisFlagToAllButton` | — | tGEOd_* (MDB) | [20_ODB](../../20_ODB.md) |
| BR-ODB-007 | Revit family auto-assignment is available only when `RevitCheck.Checked`. | `AutoAssignRevitButton` | — | — | [20_ODB](../../20_ODB.md) |
| BR-ODB-008 | An item with `CADImage2D == 'master'` is treated as a master item. | package-resolution voting | O-ODB-003 | Item (CADImage2D) | [20_ODB](../../20_ODB.md) |
| BR-ODB-009 | All ODB access requires the `CADMaintenance` privilege (whole-form gate). | `MainMenu` gate | — | — | [20_ODB](../../20_ODB.md) |
