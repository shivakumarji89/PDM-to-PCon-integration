## BR-PROD — Products (SuperProduct) → [doc](../../05_Products.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-PROD-001 | Only catalogues granted to the user (`PDMUserCatalogues`) and `Status = 1`, ordered by name. | `initialiseArrays()` | Q-PROD-002 | PDMUserCatalogues, Catalogue | [05_Products](../../05_Products.md) |
| BR-PROD-002 | Catalogue selector defaults to `DefaultCatalogueId` if assigned, else index 0. | `initialiseArrays()` | — | PDMUserCatalogues | [05_Products](../../05_Products.md) |
| BR-PROD-003 | Site/currency selectors default to the user's default ids if present, else index 0. | `initialiseArrays()` | Q-PROD-003, Q-PROD-004 | Site, Currency | [05_Products](../../05_Products.md) |
| BR-PROD-004 | The site combo swallows `KeyPress` so it cannot be typed into (selection only). | `siteselector_KeyPress` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-005 | Editable only if the catalogue's cached `ReadOnly == 0` AND `Global.readOnlyDBConnection` is false. | `catalogueIsReadOnly()` | — | PDMUserCatalogues | [05_Products](../../05_Products.md) |
| BR-PROD-006 | Read-only catalogue disables Landscape/Clone/Delete and hides the Excel-import icon. | `catalogue_selector_SelectedIndexChanged` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-007 | Site `SiteId = 20` is hard-excluded from the site list (meaning UNKNOWN). | `initialiseArrays()` | Q-PROD-003 | Site | [05_Products](../../05_Products.md) |
| BR-PROD-008 | Categories `1, 128, 129, 999` are excluded in `SuperProductMaintenance` (not in VarCond). | `updateCatalogueList()` | Q-PROD-005 | ProductCategory, CatalogueProductCategories | [05_Products](../../05_Products.md) |
| BR-PROD-009 | Category display order uses `DisplayOrder = -1 → 9999` (unordered last). | `updateCatalogueList()` | Q-PROD-005 | CatalogueProductCategories | [05_Products](../../05_Products.md) |
| BR-PROD-010 | Duplicate short-descriptions are disambiguated by appending `" (<ProductCategoryId>)"`. | `updateCatalogueList()` | — | OtherDescription | [05_Products](../../05_Products.md) |
| BR-PROD-011 | Category selector auto-selects index 0 after (re)loading. | `updateCatalogueList()` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-012 | Only English category descriptions are loaded (`od.LanguageId = 1`). | `updateCatalogueList()` | Q-PROD-005 | OtherDescription | [05_Products](../../05_Products.md) |
| BR-PROD-013 | Product filter = `Product LIKE '%<f>%'` (uppercased) OR `'<f>' LIKE Product + '%'`. | `updateProductList()` | Q-PROD-007 | Product | [05_Products](../../05_Products.md) |
| BR-PROD-014 | Products in both sets are de-duplicated, preferring the released row (`Status DESC`). | `updateProductList()` | Q-PROD-007 | CatalogueItems, CatalogueItemsUnreleased | [05_Products](../../05_Products.md) |
| BR-PROD-015 | `NonSuperCheck` restricts to products that already have components (joins `ItemComponents`). | `updateProductList()` | Q-PROD-007 | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-016 | After filtering, the first product matching (contains/prefix) the filter is auto-selected. | `updateProductList()` | Q-PROD-007 | Product | [05_Products](../../05_Products.md) |
| BR-PROD-017 | `HideCheck` restricts items to those with components; `URLCheck` restricts to released items. | `updateItemList()` | Q-PROD-009 | Item, ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-018 | `product_filter` additionally filters items via `Item LIKE '%<f>%'`. | `updateItemList()` | Q-PROD-009 | Item | [05_Products](../../05_Products.md) |
| BR-PROD-019 | After loading items, index 0 is auto-selected and its options/feature count refreshed. | `updateItemList()` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-020 | Component list is ordered by numeric `CONVERT(INT, ComponentSequence)`, not string. | `updateComponentList()` | Q-PROD-013 | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-021 | Component code resolves for the current site; `ProductCodeIdOverride` fed a constant `NULL`. | `updateComponentList()` | Q-PROD-013 | Product_Code, Item | [05_Products](../../05_Products.md) |
| BR-PROD-022 | Duplicate-guard on submit: a `SubItemId` cannot appear twice in one SP definition. | `SubmitButton_Click` | Q-PROD-019 | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-023 | On submit, sequences are normalised to a contiguous 1..N ordering. | `SubmitButton_Click` | Q-PROD-015, Q-PROD-016 | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-024 | New components append at `ComponentSequence = fnGetSPComponentCount(parent) + 1`. | `createNewItem()` | Q-PROD-020 | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-025 | A component can only be added if it exists as a standalone `Item`; else refused. | `createNewItem()` | Q-PROD-018 | Item | [05_Products](../../05_Products.md) |
| BR-PROD-026 | Add-existing is skipped if the parent already links that component. | `createNewItem()` | Q-PROD-019 | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-027 | Replace deletes the row at `sequence = replace+1` then inserts the replacement at same seq. | `createNewItem()` | Q-PROD-020 | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-028 | Multiple add/replace uses an `AddNewData` multi-select dialog; >1 add prompts confirmation. | `menuAdd*` / `AddNewData` | Q-PROD-040 | Item | [05_Products](../../05_Products.md) |
| BR-PROD-029 | Delete of a single component removes the `ItemComponents` row then refreshes the SP flag. | `menuRemoveComponent_Click` | — | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-030 | `updateSPFlag()` sets `Product.IsSuperProduct` per has-components, `UPDATE`-ing only on mismatch. | `updateSPFlag()` | Q-PROD-035 | Product, ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-031 | `updateSPFlag()` runs after add/replace/delete/import and re-selects the prior item. | `updateSPFlag()` | Q-PROD-035 | Product | [05_Products](../../05_Products.md) |
| BR-PROD-032 | Parent SP options come from `PDMOptionDataReport`, cached statically per item. | `updateSPOptionList()`, `getFeatureCount()` | Q-PROD-010 | PDMOptionDataReport (proc) | [05_Products](../../05_Products.md) |
| BR-PROD-033 | `pos_num.Maximum` = parent feature count (min 1); you cannot map beyond it. | `updateFeatureCount()` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-034 | `FeaturePositionString` iterates positions 1..max; contiguous, terminated with `|`. | `submitFeatureString()` | — | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-035 | Adding an option appends at `last+1`, re-sorts, and rewrites the feature string. | `menuAddOption_Click`, `submitFeatureString()` | Q-PROD-023 | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-036 | Removing an option removes its list/id/pos entries in lockstep and rewrites the string. | `menuRemoveOption_Click` | — | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-037 | Changing a position triggers `reorderOptionList()` (re-sort + rewrite + re-select). | `pos_num_ValueChanged`, `reorderOptionList()` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-038 | Feature-position string valid only if chars ⊂ `|0123456789`, ≥1 digit, ends with `|`. | `featurePositionStringValid()` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-039 | Bulk "Apply to all" copies the feature string (and optionally qty) to every match. | `applyFilterToComponents()` | Q-PROD-021, Q-PROD-022, Q-PROD-023 | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-040 | Bulk apply uses `AND ItemId IN (-1, …)` — the `-1` seed keeps SQL valid on empty selection. | `applyFilterToComponents()` | Q-PROD-040 | Item | [05_Products](../../05_Products.md) |
| BR-PROD-041 | Cross-catalogue delete only when component resolves as `IsSuperItem = 1`; else refused. | `menuDeleteComponent_Click` | Q-PROD-030…034 | ItemComponents, Item, Product | [05_Products](../../05_Products.md) |
| BR-PROD-042 | Delete SP definition deletes all `ItemComponents` (item/product kept) and recomputes flag. | `DeleteButton_Click` | Q-PROD-039 | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-043 | CSV export writes one row per SP item with up to `maxComponents = 20` triples, right-padded. | `downloadSPDefs()` | Q-PROD-026 | ItemComponents, CatalogueItems | [05_Products](../../05_Products.md) |
| BR-PROD-044 | CSV import treats the literal first cell `"Super Product"` as a header row and skips it. | `importSPDefs()` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-045 | Import strips a trailing `"01"`/`"02"` from component codes starting `"MEH"`. | `importSPDefs()` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-046 | Import treats a feature cell `"Y"` as empty; `MEHB.0000`/`MEHB.000000` as blank placeholders. | `importSPDefs()` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-047 | Import validates each feature string; invalid ones are logged and blanked, not imported. | `importSPDefs()`, `featurePositionStringValid()` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-048 | Import is all-or-nothing per pre-check: any unresolved SP parent aborts the whole import. | `importSPDefs()` | Q-PROD-027 | Item | [05_Products](../../05_Products.md) |
| BR-PROD-049 | On commit, an unresolved component prompts abort-or-continue; qty must be positive integer. | `importSPDefs()` | Q-PROD-027 | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-050 | Import replaces a definition wholesale (DELETE then re-INSERT with contiguous sequences). | `importSPDefs()` | Q-PROD-027 | ItemComponents, Product | [05_Products](../../05_Products.md) |
| BR-PROD-051 | Clone reads CSV `existing,new` pairs; only items in the selected catalogue are eligible. | `CloneButton_Click` | Q-PROD-036 | CatalogueItems, CatalogueItemsUnreleased | [05_Products](../../05_Products.md) |
| BR-PROD-052 | Clone batches the existence-count SQL every 1000 rows to avoid oversized `OR` chains. | `CloneButton_Click` | Q-PROD-036 | Item | [05_Products](../../05_Products.md) |
| BR-PROD-053 | Clone offers overwrite-all / skip-existing / cancel; overwrite deletes existing first. | `CloneButton_Click` | Q-PROD-037, Q-PROD-038 | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-054 | Clone logs per-item exceptions and truncates the display to 10 (+ "and N others"). | `CloneButton_Click` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-055 | The XLS price report requires a selected item with ≥1 component. | `generateXLSReport()` | — | ItemComponents | [05_Products](../../05_Products.md) |
| BR-PROD-056 | Report file name = `<site>_<currency>_<item…>.xlsx`, written to `C:\Temp` else `U:\Temp`. | `generateXLSReport()` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-057 | Report prices use `BasePriceRef`; list prices via `fnGetListPrice[ByItem]` at `dtp`. | `generateXLSReport()` | Q-PROD-024, Q-PROD-025 | Product_Code, ItemOptionValues (fnGetListPrice) | [05_Products](../../05_Products.md) |
| BR-PROD-058 | Report builds an Excel SUM formula over component list-prices × quantities. | `generateXLSReport()` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-059 | `validateSPs` runs a background `ValidateThread` over the category (all if filter `*`/empty). | `validateSPs()`, `ValidateThread` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-060 | Unsaved-change guard prompts "discard the changes?" and reverts the selector on No. | `DiscardChanges()` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-061 | VarCond relation names are `"PA_" + <item prefix>` (short items keep full code). | `updateItemList()` (VarCond) | Q-PROD-042 | Item | [05_Products](../../05_Products.md) |
| BR-PROD-062 | Relation list is de-duplicated. | `updateItemList()` (VarCond) | Q-PROD-042 | — | [05_Products](../../05_Products.md) |
| BR-PROD-063 | Text-filter changes debounce via a 1500 ms `DelayThread`. | `text_filter_TextChanged`, `DelayThread` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-064 | Export is enabled only when `text_relation` is non-empty and there is no warning text. | `updateExportButtonState()` | — | — | [05_Products](../../05_Products.md) |
| BR-PROD-065 | Export target = `<pConPath>WS\<workspace>\pcr_data_com_ocd.mdb` via Jet OLE DB. | `exportPendingRelations()`, `ExportButton_Click` | Q-PROD-043 | tCOMd_Relation | [05_Products](../../05_Products.md) |
| BR-PROD-066 | Before export, existing `PA_<filter>%` relations for the package are deleted. | `exportPendingRelations()` | Q-PROD-048 | tCOMd_Relation | [05_Products](../../05_Products.md) |
| BR-PROD-067 | Rel-object name = `"P_" + <prefix>`; `RY3X`/`RYCX` items use only the first 5 chars. | `exportPendingRelations()` | Q-PROD-047 | tCOMd_RelObj | [05_Products](../../05_Products.md) |
| BR-PROD-068 | New `tCOMd_RelObjRel` order = `max(existing, 90) + 10`, type code 3, domain `'P'`. | `exportPendingRelations()` | Q-PROD-047 | tCOMd_RelObjRel | [05_Products](../../05_Products.md) |
| BR-PROD-069 | Prefix length from item `Notes` first token, else master item's notes, else raw prefix. | `exportPendingRelations()` | Q-PROD-045, Q-PROD-046 | Item | [05_Products](../../05_Products.md) |
| BR-PROD-070 | Config save/load persists `<subs>`/`<exclusions>` to a `.cfg` file named after the category. | `SaveButton_Click`, `LoadButton_Click` | — | — | [05_Products](../../05_Products.md) |

## BR-ART — Articles → [doc](../../06_Articles.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-ART-001 | The site combo is populated from all sites by `SiteId`; index 0 auto-selected if any exist. | `ProductCodeEntry_Load` | Q-ART-001 | Site | [06_Articles](../../06_Articles.md) |
| BR-ART-002 | Site/rounding/base-price combos swallow `KeyPress` (selection only). | KeyPress handlers | — | — | [06_Articles](../../06_Articles.md) |
| BR-ART-003 | PriceCode/Description/Product_Code/UnitCode are stripped of quotes/CR/LF and trimmed. | `AddButton_Click` | — | — | [06_Articles](../../06_Articles.md) |
| BR-ART-004 | Insert requires a site plus non-empty PriceCode/Product_Code/Description (UnitCode optional). | `AddButton_Click` | — | Product_Code | [06_Articles](../../06_Articles.md) |
| BR-ART-005 | On insert, `Truncation`/`OCDExport` default to `0` and `Status` to `1` (active). | `AddButton_Click` | Q-ART-002 | Product_Code | [06_Articles](../../06_Articles.md) |
| BR-ART-006 | `BasePriceRef` = `int.Parse(basepriceCombo.Text)`; non-numeric throws (caught). | `AddButton_Click` | Q-ART-002 | Product_Code | [06_Articles](../../06_Articles.md) |
| BR-ART-007 | On success, `inserted = true` and a confirmation naming code+site is shown. | `AddButton_Click` | — | — | [06_Articles](../../06_Articles.md) |
| BR-ART-008 | On failure, a duplicate `(Product_Code, SiteId)` is assumed; raw error only to `PDMAdministrator`. | `AddButton_Click` | — | Product_Code | [06_Articles](../../06_Articles.md) |
| BR-ART-009 | Add/Close buttons are disabled during the operation and re-enabled in `finally`. | `AddButton_Click` | — | — | [06_Articles](../../06_Articles.md) |
| BR-ART-010 | The form excludes no site (contrast Products which hides site 20). | `ProductCodeEntry_Load` | Q-ART-001 | Site | [06_Articles](../../06_Articles.md) |
| BR-ART-011 | Every article DTO initialises all fields to empty string in its constructor (no null fields). | DTO constructors | — | — | [06_Articles](../../06_Articles.md) |
| BR-ART-012 | `ocdArticle` uses fixed mfr `"HM"`, order unit `"C62"`, `fastSupply="0"`, `articleType="C"`. | `ocdArticle(...)` ctor (OCDExport) | — | ocd_article (output) | [06_Articles](../../06_Articles.md) |
| BR-ART-013 | `metaArticles` uses fixed mfr `"hmx"`; `productLine` = lower-cased series (new format truncates at `_`). | `metaArticles(...)` ctor (OCDExport) | — | go_articles (output) | [06_Articles](../../06_Articles.md) |
| BR-ART-014 | `ocdArtDesc` emits per language `en`/`de`/`nl` (each line 1), CSV-quoted (`"`→`""`). | `ocdArtDesc(...)` ctor (OCDExport) | — | ocd_artdesc (output) | [06_Articles](../../06_Articles.md) |
| BR-ART-015 | Default seed `codeScheme` added once per group; article-specific schemes added if not present. | `codeScheme`/`ocdCodeScheme` ctors (OCDExport) | — | ocd_codescheme (output) | [06_Articles](../../06_Articles.md) |
| BR-ART-016 | `ocdArtBase` `LF_SEATTYPE` reference is `"F"` or `"A"` by branch (meaning UNKNOWN). | `ocdArtBase(...)` ctor (OCDExport) | — | ocd_artbase (output) | [06_Articles](../../06_Articles.md) |
| BR-ART-017 | A `LEADTIME`/`ARTICLECODE` `ocdArtBase` row is added per article, de-duplicated. | `ocdArtBase(...)` ctor (OCDExport) | — | ocd_artbase (output) | [06_Articles](../../06_Articles.md) |
| BR-ART-018 | Export-wide duplicate suppression uses parallel string keys so each row emits once. | OCDExport de-dup key lists | — | — | [06_Articles](../../06_Articles.md) |

## BR-ATTR — Attributes → [doc](../../07_Attributes.md)

*(Non-contiguous: no 003, 008, 009, 012.)*

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-ATTR-001 | The Physical Data screen requires the `CommodityMaintenance` privilege. | `PhysDataButton_Click` | — | PDMUserPrivileges | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-002 | The catalogue selector lists only the user's catalogues with `Status = 1`, by name. | `initialiseArrays()` | Q-ATTR-001 | PDMUserCatalogues, Catalogue | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-004 | GO/OCD properties are built from `BaseAttributeValues` joined to `Attribute`/`AttributeValue`, by display order. | OCDExport build loop | Q-ATTR-021 | BaseAttributeValues, Attribute, AttributeValue | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-005 | `OrderCodeValue` falls back to the value `Name` when null. | OCDExport build loop | Q-ATTR-021 | AttributeValue | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-006 | An attribute is *functional* (`IsFunctional='True'`) when `Attribute.WebMenuAttribute = 1`. | `addMetaType(...)` | Q-ATTR-021 | Attribute | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-007 | `metaProperties.propertyName = "G" + removeNonAlphaStrict(attr)`; variant fields empty. | `metaProperties(...)` ctor | Q-ATTR-021 | — | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-010 | `metaProperties` performs no validation, DB access, or defaulting (passive holder). | `metaProperties` DTO | — | — | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-011 | Editable only when `_readOnlyCatalogues[cat] == 0` AND `Global.readOnlyDBConnection` is false. | `catalogueIsReadOnly()` | — | PDMUserCatalogues | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-013 | Site `20` is always excluded from the WebEOS site selector (rationale UNKNOWN). | `initialiseArrays()` | Q-ATTR-003 | Site | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-014 | The physical grid shows Item, WeightKilos, VolumeLitres, FreightCategory, CommodityCode, FSCCompliant. | `PhysicalItemChange()` | Q-ATTR-004, Q-ATTR-014 | Item | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-015 | Physical saves use optimistic concurrency (UPDATE only if all original values match, null-safe). | `SubmitButton_Click` | Q-ATTR-005 | Item | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-016 | After a physical UPDATE the row is re-selected to refresh the grid with persisted values. | `SubmitButton_Click` | Q-ATTR-005 | Item | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-017 | Per-item option incremental volume edited via `ItemOptionValues.IncrementalVolume` by `(ItemId, OptionValueId)`. | option-volume grid handlers | Q-ATTR-006, Q-ATTR-007, Q-ATTR-020 | ItemOptionValues, OptionValue, Item | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-018 | WebEOS restrictions keyed by `(ItemId, SiteId, CatalogueId)` with a single `WebEOSQuantity`. | `WebEOSUpdate()` | Q-ATTR-008 | WebEOSItemRestrictions | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-019 | Delivery offsets keyed by (Catalogue, Category, SourceCountry, DeliveryCountry, ShipVia). | `DeliveryUpdate()` | Q-ATTR-009 | CPCDeliveryOffsets | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-020 | The WebEOS tab shows only if `WebEOSItemRestrictions` exists (probed via `sysobjects`). | `CheckTables()` | Q-ATTR-010 | sysobjects, WebEOSItemRestrictions | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-021 | Reserved categories `1, 128, 129, 999` are excluded from the category selector. | `UpdateCategory()` | Q-ATTR-011 | ProductCategory, CatalogueProductCategories | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-022 | Category `DisplayOrder = -1` is coalesced to `9999` (sorts last). | `UpdateCategory()` | Q-ATTR-011 | CatalogueProductCategories | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-023 | Category descriptions are taken from `OtherDescription` at `LanguageId = 1`. | `UpdateCategory()` | Q-ATTR-011 | OtherDescription | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-024 | The physical item grid is populated via `Product → ProductRange` (optionally `CatalogueItems`). | `PhysicalItemChange()` | Q-ATTR-012 | Item, Product, ProductRange, CatalogueItems | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-025 | WebEOS grid uses a LEFT OUTER JOIN so items without a restriction still appear. | WebEOS grid load | Q-ATTR-013 | Item, WebEOSItemRestrictions | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-026 | WebEOS save is delete-then-insert (not in-place); dimension edits issued in the same path. | WebEOS save handler | Q-ATTR-015 | WebEOSItemRestrictions, Item | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-027 | Delivery save is replace-all per catalogue (DELETE then reinsert); source countries exists-checked. | Delivery save handler | Q-ATTR-017 | CPCDeliveryOffsets, CPCSourceCountries, Country | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-028 | Delivery category list ordered by `CatalogueProductCategories.DisplayOrder`. | Delivery tab load | Q-ATTR-016 | CatalogueProductCategories | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-029 | Commodity codes form a length-based hierarchy: len 4 = heading, len > 4 = detail. | Commodity tree load | Q-ATTR-018 | CommodityCode | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-030 | On add, a duplicate check runs against the first 4 chars of the new code. | Commodity add handler | Q-ATTR-018 | CommodityCode | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-031 | Add supports an optional `HSCode` (3-column INSERT if present, else 2-column). | Commodity add handler | Q-ATTR-018 | CommodityCode | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-032 | Commodity-code edit does not update `HSCode` — the assignment is commented out (latent/dead). | Commodity edit handler | Q-ATTR-018 | CommodityCode | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-033 | Import expects `[item],[weight],[volume],[height],[width],[depth]`; all whitespace stripped first. | `importData()` | — | — | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-034 | Each numeric field validated by `isNumericalValue` (no negatives); a malformed line aborts import. | `importData()`, `isNumericalValue()` | — | — | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-035 | Import is partial: a column set only if its parsed value is `> 0`; item matched by `Item = '<item>'`. | `importData()` | Q-ATTR-019 | Item | [07_Attributes](../../07_Attributes.md) |
| BR-ATTR-036 | A read-only DB connection forces every catalogue read-only regardless of per-user `ReadOnly`. | `catalogueIsReadOnly()` | — | PDMUserCatalogues | [07_Attributes](../../07_Attributes.md) |
