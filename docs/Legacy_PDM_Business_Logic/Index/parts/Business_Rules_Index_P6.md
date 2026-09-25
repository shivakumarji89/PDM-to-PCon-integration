## BR-OCD — OCD Export → [doc](../../21_OCD.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-OCD-001 | **Orphaned export.** `OCDExport` is instantiated but its worker (`ocdThread`) is never initialised/executed. | `OCDExport()`, `execThread`, `startExport` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-002 | Constructor defaults: `_exportDirectory = "C:\"`, etc. | `OCDExport()` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-003 | `initParams` derives the export root by truncating the path. | `initParams` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-004 | `ocd_version.csv` is a fixed manifest string written verbatim. | `writeData` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-005 | Catalogue lead time drives a synthetic baseline lead-time value. | `initParams` | Q-OCD-001 | Catalogue | [21_OCD](../../21_OCD.md) |
| BR-OCD-010 | Export-all (`productCodeId == -1`) enumerates only product-code items. | `initParams` | Q-OCD-002 | Product_Code, Product, Item, CatalogueItems | [21_OCD](../../21_OCD.md) |
| BR-OCD-011 | The main item query runs twice per category group (count pass, then build). | `startExport` | Q-OCD-009 | Item, Product, ProductCategory, ProductRange | [21_OCD](../../21_OCD.md) |
| BR-OCD-012 | Only released items are exported (`Item.Status = 1`, hardcoded). | `startExport` | Q-OCD-009 | Item | [21_OCD](../../21_OCD.md) |
| BR-OCD-013 | Catalogue-specific filter: `_catalogueId == 258` adds an extra condition. | `startExport` | Q-OCD-009 | Item | [21_OCD](../../21_OCD.md) |
| BR-OCD-014 | Only option values in `CatalogueOptionValues` for the catalogue are exported. | `startExport` | Q-OCD-004 | CatalogueOptionValues | [21_OCD](../../21_OCD.md) |
| BR-OCD-015 | Only `Status == 1` (ACT) option rows are processed. | `startExport` (PDMOptionDataReport) | Q-OCD-012 | PDMOptionDataReport (proc) | [21_OCD](../../21_OCD.md) |
| BR-OCD-016 | Order codes containing `#` are dropped everywhere they are used. | `startExport` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-017 | The literal order-code value `"C7"` is excluded from property values. | `startExport` | — | OptionValue | [21_OCD](../../21_OCD.md) |
| BR-OCD-018 | Property-value `valueFrom` = `OrderCodeValue2` with spaces→underscores. | property build loop | Q-OCD-012 | OptionValue | [21_OCD](../../21_OCD.md) |
| BR-OCD-019 | Fabric handling: `LF_SEATTYPE` gets a special two-value treatment. | property build loop | Q-OCD-015 | [Option] | [21_OCD](../../21_OCD.md) |
| BR-OCD-020 | `_paramSeries` = last 2 characters of `Product_Code`. | `initParams` | Q-OCD-003 | Product_Code | [21_OCD](../../21_OCD.md) |
| BR-OCD-021 | Attribute names become property names prefixed `G` and stripped of non-alpha. | `removeNonAlphaStrict`, meta build | Q-OCD-011 | Attribute, AttributeValue, BaseAttributeValues | [21_OCD](../../21_OCD.md) |
| BR-OCD-021b | Property/property-value description indices are resolved against the description arrays. | desc collection | Q-OCD-013, Q-OCD-014, Q-OCD-016, Q-OCD-017 | OtherDescription, [Option], OptionValue | [21_OCD](../../21_OCD.md) |
| BR-OCD-022 | Items starting `AU1`/`AE7` get an `_ARMS`/tilt/arm suffix. | `startExport` (code munging) | — | Item | [21_OCD](../../21_OCD.md) |
| BR-OCD-023 | `DTW1/DTW4/DTW5` codes are rewritten to product handles. | `startExport` (code munging) | — | Item | [21_OCD](../../21_OCD.md) |
| BR-OCD-024 | `AERONTSKCHR_A/_B/_C` article ids have the `_A/_B/_C` suffix handled specially. | `startExport` (code munging) | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-025 | Non-series products fall back to `Product` with `.` removed. | `startExport` | — | Product | [21_OCD](../../21_OCD.md) |
| BR-OCD-026 | Every article emits `ocdArticle(articleID, "C", "HM", series, …)`. | `ocdArticle` ctor | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-027 | `metaArticles` (`go_articles`) manufacturer is hardcoded (`hmx`). | `metaArticles` ctor | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-028 | Four constant `go_types` functional properties are added per article. | `addMetaType` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-029 | `addMetaType` dedups by `product\|propertyName`. | `addMetaType` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-030 | A synthetic `LEADTIME` property class + `ARTICLECODE` property is appended. | LEADTIME synthesis | Q-OCD-018 | Catalogue | [21_OCD](../../21_OCD.md) |
| BR-OCD-031 | Lead-time value list `{45,25,15}` is hardcoded under a condition. | LEADTIME synthesis | Q-OCD-018 | Catalogue | [21_OCD](../../21_OCD.md) |
| BR-OCD-031b | Old format instead emits a single `<leadtime>_DAY` property class. | LEADTIME synthesis | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-032 | New-format lead-time tables (`t_lt_<key>_tbl.csv`) map lead times. | `startExport`, `writeData` | Q-OCD-005, Q-OCD-006, Q-OCD-007, Q-OCD-008 | Item, [Option], OptionValue, CatalogueOptionValues, CatalogueItems | [21_OCD](../../21_OCD.md) |
| BR-OCD-033 | Sort override: `_catalogueId == 264 AND productCodeId == 776` changes ordering. | `startExport` | Q-OCD-009 | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-034 | `AU900*` items force a shorter article-code truncation length. | `startExport` | — | Item | [21_OCD](../../21_OCD.md) |
| BR-OCD-035 | Short descriptions are deduped in `_shortDescriptions`. | `addShortDesc` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-036 | DE/NL descriptions fall back to the English short description. | `startExport` | Q-OCD-009 | ProductDescription | [21_OCD](../../21_OCD.md) |
| BR-OCD-037 | Long-text rows are split on `>` markers into multiple lines. | long-desc collect | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-038 | Text is emitted quoted with embedded quotes doubled. | `ocdArtDesc` build | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-039 | `.sr` symbol-resource files: the first `metaDescriptionData` drives the header. | `writeData` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-040 | Base price: each article emits an `ocdPrice` base row. | `addOCDPrice`, `ocdPrice` | Q-OCD-009 (fnGetListPriceByItem) | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-041 | Surcharge price: each priced option value emits a surcharge `ocdPrice` row. | `addOCDPrice` | Q-OCD-019 | ItemOptionValues | [21_OCD](../../21_OCD.md) |
| BR-OCD-042 | Price slot is chosen by `Product_Code.BasePriceRef`. | `startExport` | Q-OCD-019 | Product_Code | [21_OCD](../../21_OCD.md) |
| BR-OCD-043 | `addOCDPrice` dedups by the full pipe-joined price signature. | `addOCDPrice` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-050 | For each priced value a `$VARCOND` relation is generated. | `ocdRelation`/`ocdRelationObj` build | Q-OCD-019 | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-051 | Option-name → relation-name mapping: `TYPE` → `COLOUR` unless overridden. | VARCOND build | Q-OCD-020 | DependentOptionValues, OptionValue | [21_OCD](../../21_OCD.md) |
| BR-OCD-052 | Dedup guards use string keys (`_propertyClassData`, etc.). | build loop | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-053 | Variant order-code formatting: an 8-char value is split. | VARCOND build | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-054 | Uniqueness suffixing: colliding varconds get `~2` (or the next index). | VARCOND build | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-055 | **Hardcoded relation blocks** are appended per series. | `startExport` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-056 | Fabric-set `relObjID` remapping by order-code prefix. | `startExport` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-057 | When an item has no priced options, the varcond block is skipped. | VARCOND build | Q-OCD-019 | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-058 | Output directory tree is built per group. | `writeData` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-059 | `go_*` and `.sr` files are redirected out of the `db` folder. | `writeData` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-060 | A row is skipped if, after stripping `;`/spaces/CR/LF, it is empty. | `writeData` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-061 | In new format, lead-time relation rows are appended to the relation set. | `startExport` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-062 | `initParams`, `startExport`, `writeData`, `execThread` form the (uncalled) pipeline entrypoints. | `initParams`, `startExport`, `writeData`, `execThread` | — | — | [21_OCD](../../21_OCD.md) |
| BR-OCD-063 | Progress is logged to `ocd_export\OCD_log.txt` (append unless reset). | `startExport` | — | UNKNOWN (log file, not a table) | [21_OCD](../../21_OCD.md) |

## BR-EXP — Export (Syteline / OFDA / SIF / CSI) → [doc](../../22_Export.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-EXP-001 | "Export PDM Data" is enabled only for the right permission/context. | `SLExportButton_Click` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-002 | "PDM Data Import" is enabled only for the right permission/context. | `PDMImportButton_Click` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-003 | Left-clicking "PDM Data Import" opens the `SIFImport` form. | `PDMImportButton_Click` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-004 | "Import Materials in to CSI" is disabled unless the user has the required privilege. | `ImportMaterialsInToCSIToolStripMenuItem_Click` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-005 | The scheduler button branches on identity: `dbacw8` gets a different path. | `button_scheduler_Click` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-006 | Output type is chosen by flags (`millerCAD` → `b-<site><ccy>.asc`, etc.). | `ExportSL8Data` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-007 | **Site 20 is remapped to site 1 ("uk")** for SL8 export. | `ExportSL8Data` | — | Site | [22_Export](../../22_Export.md) |
| BR-EXP-008 | Export parameters may come from the UI or a queue-param row. | `ExportSL8Data` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-009 | When min-item == max-item the `{max}` placeholder is dropped. | `ExportSL8Data` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-010 | `SuperProductCombo` selection maps to mutually-exclusive modes. | `ExportSL8Data` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-011 | `_millerCAD \| (_syteline & !_exportBasePrices)` condition drives a branch. | `ExportSL8Data` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-012 | Super-product BOM is exported by UNION-ing the base item query with the component query. | `ExportThread.execThread` | Q-EXP-006 | ItemComponents, Item | [22_Export](../../22_Export.md) |
| BR-EXP-013 | `check_includeURL` lowers the minimum option-value status to 0. | `ExportCSIData` | Q-EXP-007 | CatalogueOptionValues, OptionValue | [22_Export](../../22_Export.md) |
| BR-EXP-014 | CSI writes up to six satellite CSVs (items, product_items, …). | `SytelineCSIExport.execThread` | Q-EXP-008 | Item, Product | [22_Export](../../22_Export.md) |
| BR-EXP-015 | Feature order-code max length is queried per option. | `ExportCSIData` | Q-EXP-006 | ItemComponents, Item | [22_Export](../../22_Export.md) |
| BR-EXP-016 | Selecting catalogue 360 without 362 auto-adds catalogue 392. | `ExportOFDA` | — | Catalogue | [22_Export](../../22_Export.md) |
| BR-EXP-017 | Multiple catalogues are sorted by descending `LeadTime`. | `ExportOFDA` | Q-EXP-012 | Catalogue | [22_Export](../../22_Export.md) |
| BR-EXP-018 | Site 2 ("Japan") and currency JPY are forced to the end of their lists. | `ExportOFDA` | — | Site, Currency | [22_Export](../../22_Export.md) |
| BR-EXP-019 | Language 10 (English) is forced to the front of the language list. | `ExportOFDA` | — | Language | [22_Export](../../22_Export.md) |
| BR-EXP-020 | `UnreleasedDataCheck` sets `minStatus = 0`; default OFDA export uses active only. | `ExportOFDA` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-021 | The exported "series" is derived from a hard-coded mapping. | `OFDAExport.initArrays` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-022 | `excludeImaginePanels` suppresses Imagine panel items. | `OFDAExport` | — | Item | [22_Export](../../22_Export.md) |
| BR-EXP-023 | `naughtoneCatalogCode` rewrites the catalogue code to a Naughtone-specific value. | `OFDAExport` | Q-EXP-012 | Catalogue | [22_Export](../../22_Export.md) |
| BR-EXP-024 | Fabric option values map to hard-coded OptionId feature refs. | `OFDAExport` | Q-EXP-015 | [Option], OptionValue | [22_Export](../../22_Export.md) |
| BR-EXP-025 | Model-specific suffixes are emitted with `_` replaced by the US token. | `OFDAExport` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-026 | The OFDA file is always named `PDMExport_OFDA_latest.xml` unless overridden. | `writeXmlDataFile` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-027 | On OFDA export the previous file is rotated to `_prev.xml`. | `writeXmlDataFile` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-028 | `_webconfig` mode replaces `"<root>"` selection descriptions. | `OFDAExport` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-029 | OFDA price dates/units follow the OCD convention (unit `C62`). | `OFDAExport` | Q-EXP-013 | ItemOptionValues, Product_Code | [22_Export](../../22_Export.md) |
| BR-EXP-030 | PBOM export connects to **SyteLine LIVE** for unit costs; site 20 handled. | `BOMExport.ExportMaterials` | Q-EXP-009 | item / item_mst (SyteLine LIVE) | [22_Export](../../22_Export.md) |
| BR-EXP-031 | Only material rows with `DeleteStatus = 0` are exported. | `BOMExport` | Q-EXP-010 | MaterialData, Material, MaterialCriteria | [22_Export](../../22_Export.md) |
| BR-EXP-032 | Output is semicolon-delimited (not tab) with several fixed columns. | `BOMExport` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-033 | Developer-only diagnostic: `isDeveloper` enables a raw SQL log. | `BOMExport` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-034 | `ImportMaterialsInToCSI`/`ResolveCriteria` parse Excel-style criteria. | `BOMExport.ResolveCriteria` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-035 | SIF export writes three files from one base name (`.top`, …). | `SIFExportThread.execThread` | Q-EXP-016 | CatalogueProductCategories, Catalogue | [22_Export](../../22_Export.md) |
| BR-EXP-036 | `°` in category/range names is replaced with a safe token. | `SIFExportThread` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-037 | `#`-suffixed order codes are stripped of `#` when written. | `SIFExportThread` | — | OptionValue | [22_Export](../../22_Export.md) |
| BR-EXP-038 | A missing/`-1` incremental price is written as `O1=0.00`. | `SIFExportThread` | — | ItemOptionValues | [22_Export](../../22_Export.md) |
| BR-EXP-039 | `CatalogueProductCategories.DisplayOrder = -1` is normalised to 9999. | `SIFExportThread` | Q-EXP-016 | CatalogueProductCategories | [22_Export](../../22_Export.md) |
| BR-EXP-040 | Import accepts two source families: SIF `.top`/`.n01` and others. | `button_import_update_Click` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-041 | SIF `.top` import also looks for sibling `.key` and `.opt` files. | `button_import_update_Click` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-042 | New options are created with a camelCase, US→UK-English normalised name. | `createOption` | — | [Option] | [22_Export](../../22_Export.md) |
| BR-EXP-043 | An option name containing `"kvadrat"` (fabric type) gets special handling. | `createOption` | — | [Option] | [22_Export](../../22_Export.md) |
| BR-EXP-044 | Fabric-type option values get a `#`-suffixed order code. | `createOption` | — | OptionValue | [22_Export](../../22_Export.md) |
| BR-EXP-045 | Order-code `{KEY}` tokens are stripped out of the stored value. | `createOption` | — | OptionValue | [22_Export](../../22_Export.md) |
| BR-EXP-046 | The new-format key is appended to the range's format string. | `createOption` | Q-EXP-017 | ProductRange | [22_Export](../../22_Export.md) |
| BR-EXP-047 | Item option increments are upserted (update if the row exists, else insert). | `createOption` | Q-EXP-018 | ItemOptionValues | [22_Export](../../22_Export.md) |
| BR-EXP-048 | Fabric imports create paired "Fabric type" + "Fabric colour" options. | `createOption` | — | [Option], OptionValue | [22_Export](../../22_Export.md) |
| BR-EXP-049 | PIP import can set `CatalogueProductCategories.PSTemplateFile`. | `button_import_update_Click` | — | CatalogueProductCategories | [22_Export](../../22_Export.md) |
| BR-EXP-050 | Financial export requires at least one of PLC / Matrix / Formula. | `ExportFinanicalDataToolStripMenuItem_Click` | Q-EXP-001, Q-EXP-002, Q-EXP-003 | Product_Code, PriceMatrix, PriceFormula | [22_Export](../../22_Export.md) |
| BR-EXP-051 | The three financial files are derived from one save name. | `ExportFinanicalDataToolStripMenuItem_Click` | Q-EXP-001 | — | [22_Export](../../22_Export.md) |
| BR-EXP-052 | Price-band export includes only `OptionValue.status < 2`. | `ExportPriceBandDataToolStripMenuItem_Click` | Q-EXP-004 | OptionValue, FabricBands | [22_Export](../../22_Export.md) |
| BR-EXP-053 | Static-data XML `Rounding` column is deliberately commented out. | `okButton_Click` | Q-EXP-022 | Product_Code | [22_Export](../../22_Export.md) |
| BR-EXP-054 | Static-data XML aborts if no site is selected. | `okButton_Click` | — | Site | [22_Export](../../22_Export.md) |
| BR-EXP-055 | The scheduler category list excludes categories 1, 128, 129, 999. | `ScheduleExport` | — | CatalogueProductCategories | [22_Export](../../22_Export.md) |
| BR-EXP-056 | The scheduler site list excludes site 20. | `ScheduleExport` | Q-EXP-020 | Site, PDMUserCatalogues, Catalogue | [22_Export](../../22_Export.md) |
| BR-EXP-057 | A pending schedule row can only be deleted while pending. | `ScheduleExport` | Q-EXP-019 | ExportSchedule | [22_Export](../../22_Export.md) |
| BR-EXP-058 | Publication only copies files to the network under the right condition. | `ExportDPSDBThread.execThread` | Q-EXP-023 | DPSDB | [22_Export](../../22_Export.md) |
| BR-EXP-059 | A DTS failure raises "DTS package failed to execute successfully". | `ExportDPSDBThread.execThread` | — | — | [22_Export](../../22_Export.md) |
| BR-EXP-060 | Publication files land in a timestamped subfolder. | `ExportDPSDBThread.execThread` | — | — | [22_Export](../../22_Export.md) |

## BR-GEN — Generation (Handbook Designer) → [doc](../../23_Generation.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-GEN-001 | The Handbook Designer button is enabled only for the right permission/context. | `HandbookButton_Click` | — | — | [23_Generation](../../23_Generation.md) |
| BR-GEN-002 | With `Global.connectedDB = 'PDMPublished'` the catalogue picker is scoped accordingly. | `HandbookDesigner_Load` | Q-GEN-001 | DealerCatalogues, PDMUserCatalogues, Catalogue | [23_Generation](../../23_Generation.md) |
| BR-GEN-003 | Catalogue read-only state comes from `PDMUserCatalogues.ReadOnly`. | `HandbookDesigner_Load` | Q-GEN-001 | PDMUserCatalogues, Catalogue | [23_Generation](../../23_Generation.md) |
| BR-GEN-004 | Site 20 is excluded from the site picker. | `HandbookDesigner_Load` | Q-GEN-002 | Site | [23_Generation](../../23_Generation.md) |
| BR-GEN-005 | Inserting a group shifts existing `ProductGroupId` values up. | `menuAddNewGroup`, `menuRemoveGroup` | Q-GEN-005 | HandbookProducts | [23_Generation](../../23_Generation.md) |
| BR-GEN-006 | "Add group (clone)" copies an existing group's rows into the new group. | `menuAddNewGroupClone`, `menuImportGroup` | — | HandbookProducts | [23_Generation](../../23_Generation.md) |
| BR-GEN-007 | A negative `HandbookOptions.OptNum` hides that option from the handbook. | option hide/show handler | Q-GEN-007 | HandbookOptions | [23_Generation](../../23_Generation.md) |
| BR-GEN-008 | Memory guard: a publish selection over **500 products / 1000 items** is blocked (unless pricebook). | `checkGroupLimit` | Q-GEN-003, Q-GEN-004 | HandbookProducts, Item, CatalogueItems | [23_Generation](../../23_Generation.md) |
| BR-GEN-009 | Only groups with `HandbookProducts.PublishCategory = 1` are published. | `HandbookDesigner_Load` | Q-GEN-003, Q-GEN-004 | HandbookProducts | [23_Generation](../../23_Generation.md) |
| BR-GEN-010 | `PublishCheck` toggles `PublishCategory` for the group. | `PublishCheck_MouseUp` | — | HandbookProducts | [23_Generation](../../23_Generation.md) |
| BR-GEN-011 | `SeparateIncrements` per group controls increment splitting. | `GroupList_SelectedIndexChanged` | Q-GEN-005 | HandbookProducts | [23_Generation](../../23_Generation.md) |
| BR-GEN-012 | Increment preview is produced by `PDMPriceListReportForProductGroup`. | `GroupList_SelectedIndexChanged` (IncData load) | Q-GEN-008 | PDMPriceListReportForProductGroup (proc) | [23_Generation](../../23_Generation.md) |
| BR-GEN-013 | The `incdata` result has `"_"` replaced with CRLF and cleanup applied. | IncData load | Q-GEN-008 | — | [23_Generation](../../23_Generation.md) |
| BR-GEN-014 | The `content_selector` value controls the price-list content mode. | IncData load | Q-GEN-008 | — | [23_Generation](../../23_Generation.md) |
| BR-GEN-015 | `HandbookIncrementDesc.SubstituteDescription` lets an author override a description. | `AddSubButton`, `SubDescCheck` | — | HandbookIncrementDesc | [23_Generation](../../23_Generation.md) |
| BR-GEN-016 | The exclusion dialog operates on a **dynamic table name** (`HBExclusions`). | `HBExclusions.initValues` | Q-GEN-010, Q-GEN-011 | HandbookAttributeExclusions, HandbookOptionExclusions | [23_Generation](../../23_Generation.md) |
| BR-GEN-017 | Adding an exclusion inserts one row per selected value. | `HBExclusions` add | Q-GEN-010 | HandbookAttributeExclusions, HandbookOptionExclusions | [23_Generation](../../23_Generation.md) |
| BR-GEN-018 | Removing an exclusion deletes exactly the matching row. | `HBExclusions` remove | Q-GEN-011 | HandbookAttributeExclusions, HandbookOptionExclusions | [23_Generation](../../23_Generation.md) |
| BR-GEN-019 | Exclusion candidates are ordered by attribute/option display order. | `HBExclusions.initValues` | Q-GEN-009 | Attribute, AttributeValue, Option, OptionValue | [23_Generation](../../23_Generation.md) |
| BR-GEN-020 | All handbook edits run **synchronously on the UI thread** against the DB. | all context-menu handlers | — | — | [23_Generation](../../23_Generation.md) |

## BR-UTIL — Utilities / Static Data / Shared Helpers → [doc](../../24_Utilities.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-UTIL-001 | `StaticDataMaintenance` form caption/tabs are gated by financial privileges. | `StaticDataMaintenance` Load | — | — | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-002 | Static-data reads/writes use parameterised commands (contrast the rest of the app). | `SetSQL` | Q-UTIL-001–Q-UTIL-022 | Currency, Site, ExchangeRate, Language, Product_Code, PriceFormula, PriceMatrix | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-003 | Static-data grids load from parameterised `SELECT`s by entity type. | `updateDataGrid`, `fillgridN` | Q-UTIL-001, Q-UTIL-004, Q-UTIL-007, Q-UTIL-013, Q-UTIL-016, Q-UTIL-018, Q-UTIL-021 | Currency, Site, ExchangeRate, Language, Product_Code, PriceFormula, PriceMatrix | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-020 | Financial Data Maintenance tabs/gates are driven by specific privilege flags. | `StaticDataMaintenance` Load | — | — | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-021 | `ApplicationText` maintenance edits language-keyed application text. | `ApplicationText` | — | UNKNOWN (display dialog; no direct table) | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-022 | `InputForm` is a reusable prompt dialog used across maintenance flows. | `InputForm.SubmitData` | — | — | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-023 | `EditDialog` is a reusable edit surface bound to a single record. | `EditDialog` | — | — | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-024 | `AddDataList` is a reusable multi-select add dialog. | `AddDataList.initialiseDataList` | context-driven | Product, Attribute, [Option], Catalogue | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-025 | `AddNewData` creates new option values (and supporting description rows). | `AddNewData.initSQL` | — | ProductGroupCodes, OtherDescription, OptionValue | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-026 | Language maintenance is reachable only with `CoreMaintenance` (no dedicated privilege). | `StaticDataMaintenance` Load | — | Language | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-030 | Static-data edits use optimistic concurrency (`@Original_*`) — concurrent edits silently no-op. | `SetSQL`, `updateButton_Click` | Q-UTIL-003, Q-UTIL-006, Q-UTIL-010 | Currency, Site, ExchangeRate | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-031 | Currency/site/exchange-rate maintenance validates numeric fields before writing. | `updateButton_Click` | — | Currency, Site, ExchangeRate | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-032 | A `'abcx'` sentinel `DomCurrCode` is a magic value used in grid loads. | grid-load filters | Q-UTIL-011 | ExchangeRate, PriceFormula | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-033 | Shared SQL helpers (e.g. `getNextDisplayOrder`) centralise common id/order lookups. | `getNextDisplayOrder` | — | UNKNOWN | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-034 | Price-formula maintenance edits `PriceFormula` rows with audit. | `updateButton_Click` | Q-UTIL-020 | PriceFormula, PDMAudit.Transactions, PDMAudit.PFUpdates | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-035 | Price-formula edits never `UPDATE` in place — insert new + delete old (stale ids result). | `updateButton_Click` | Q-UTIL-020 | PriceFormula | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-036 | Product-code maintenance edits `Product_Code` records. | `updateButton_Click` | Q-UTIL-016, Q-UTIL-017 | Product_Code, Site | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-037 | Rounding-mode maintenance edits the rounding lookup. | `updateButton_Click` | UNKNOWN | UNKNOWN (Rounding column commented out) | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-038 | Base-price-reference maintenance edits the base-price-ref lookup. | `updateButton_Click` | Q-UTIL-016 | Product_Code (BasePriceRef) | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-039 | Site maintenance edits `Site` records with validation. | `updateButton_Click` | Q-UTIL-004, Q-UTIL-005, Q-UTIL-006 | Site | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-040 | Currency maintenance edits `Currency` records with validation. | `updateButton_Click` | Q-UTIL-001, Q-UTIL-002, Q-UTIL-003 | Currency | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-041 | Exchange-rate maintenance edits effective-dated `ExchangeRate` rows. | `updateButton_Click` | Q-UTIL-007, Q-UTIL-008, Q-UTIL-009, Q-UTIL-010 | ExchangeRate | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-050 | Static-data add/edit flows resolve `DescriptionId` via max+1. | `AddNewData` | — | OtherDescription | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-051 | Add flows insert an `OtherDescription` row before the owning entity. | `AddNewData` | — | OtherDescription | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-052 | Delete flows remove the entity and (where applicable) its description. | delete handlers | — | OtherDescription | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-053 | Grid edits normalise text (quotes/CR/LF) before writing. | `updateButton_Click` | Q-UTIL-017 | Product_Code | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-054 | List loads apply active-status filters where applicable. | `AddDataList.initialiseDataList` | — | Product, [Option], Attribute | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-055 | Add-new-data validates the natural key before insert. | `DoneButton_Click` | Q-UTIL-025 | Currency, Product_Code, PriceFormula | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-056 | Adding a new option value writes `OtherDescription` → `OptionValue` → optional `DependentOptionValues`. | `AddNewData` | — | OtherDescription, OptionValue, DependentOptionValues | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-057 | `ProgressThread` runs the DPS publish DTS via `xp_cmdshell 'dtsrun … -Sdbchip02 …'` (hard-coded server/package). | `ProgressThread.execThread` | xp_cmdshell (dtsrun) | UNKNOWN (DTS package, not a table) | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-058 | `DelayThread` debounces the CAD category filter (default 500 ms), dropping superseded requests. | `DelayThread.execThread` | — | — | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-059 | `TimerThread` displays elapsed time (`HH:MM:SS`), capped under 1,000,000 seconds. | `TimerThread.execThread` | — | — | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-060 | `debug_form` is the app's generic scrollable text/report console. | `debug_form` | — | — | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-061 | `MDBQuery` selects the pCon Jet MDB by domain (OCD/ODB/OAS/CLS) under the workspace folder. | `MDBQuery.initThread` | Jet/OLEDB (Access MDB) | UNKNOWN (external pCon MDB) | [24_Utilities](../../24_Utilities.md) |
| BR-UTIL-062 | `MDBQuery` `"find <term>"` searches every string column of every table (single quotes → `%`). | `MDBQuery` find | Jet/OLEDB (Access MDB) | UNKNOWN (external pCon MDB) | [24_Utilities](../../24_Utilities.md) |
