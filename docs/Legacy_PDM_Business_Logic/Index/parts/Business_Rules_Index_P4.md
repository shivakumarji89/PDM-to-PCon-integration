## BR-DESC — Descriptions → [doc](../../13_Descriptions.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-DESC-001 | The active entity type is determined entirely by `TabSelector.SelectedIndex` → table mapping. | `getTableNameFromTabIndex()`, `getTableName()`, `TabSelector_SelectedIndexChanged` | — | Product, ProductDescription, OtherDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-002 | Product text persists via `submitData()`; all other tabs via `modifyOtherDescription()`. | `submitData()`, `modifyOtherDescription()` | Q-DESC-022, Q-DESC-030 | ProductDescription, OtherDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-003 | Every grid `LEFT OUTER JOIN`s the description table so untranslated entities still appear. | `updateDataGrid()` | Q-DESC-001..010 | Product, ProductDescription, OtherDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-004 | Category picker/grid always display English names, independent of editing language. | `initialiseComboBoxes` | Q-DESC-007, Q-DESC-014 | CatalogueProductCategories, OtherDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-005 | `cpc.DisplayOrder = -1` is coerced to `9999` for sorting. | `updateDataGrid()` | Q-DESC-007, Q-DESC-014 | CatalogueProductCategories | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-006 | Grid filter radios (All/Blank/Missing) rebuild the grid using the outer-join null. | `RadioAll/RadioBlank/RadioMissing_CheckedChanged`, `updateDataGrid(0)` | Q-DESC-001..010 | ProductDescription, OtherDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-007 | "Show All Products" widens beyond catalogue scope and enables `Product.Name` sync on submit. | `submitData()` (`ShowAllCheck`) | Q-DESC-001, Q-DESC-026 | Product | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-008 | Short-description length is live; > 40 chars turns the counter red (soft warning). | `selectRow` / row-select (`countText`) | — | ProductDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-009 | For pCon a hard 50-char short-description limit is enforced (product skipped). | pCon propagation (`ProductDescriptions.cs:11618`) | — | ProductDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-010 | Application text has 3 scopes: Default / Catalogue / Pricebook (`-1 * CatalogueId`). | `apptext_selector_SelectedIndexChanged`, `submitData()` | Q-DESC-023, Q-DESC-024, Q-DESC-025 | ProductDescription, CatalogueApplicationText | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-011 | On row-select the app-text scope auto-defaults by catalogue name/permission/existing text. | row-select handler | Q-DESC-020 | ProductDescription, CatalogueApplicationText, Catalogue | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-012 | Saving empty app text DELETEs the override row; a WHERE-less delete is explicitly blocked. | `submitData()` | Q-DESC-023..025 | CatalogueApplicationText | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-013 | Empty short/long/app text is written as SQL `NULL`, not empty strings. | `submitData()` | Q-DESC-022 | ProductDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-014 | Description text is stored as Unicode (`N'…'`); some name-sync writes use non-`N` literals. | `submitData()`, `modifyOtherDescription()` | Q-DESC-022, Q-DESC-026, Q-DESC-030 | ProductDescription, OtherDescription, Product, Handbook | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-015 | CR/LF are stripped from product short/long text on submit. | `submitData()` | Q-DESC-022 | ProductDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-016 | Single-quote escaping is inconsistent (`'`→backtick in some paths, `'`→`''` in others). | `submitData()`, `modifyOtherDescription()` | Q-DESC-022, Q-DESC-023..025, Q-DESC-051 | ProductDescription, OtherDescription, CatalogueApplicationText | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-017 | English attribute/option text is camel-cased, except attribute `"Size"` / `ignoreCamelCase`. | `modifyOtherDescription()`, `SIFImport.camelCase(...)` | Q-DESC-030 | OtherDescription, Attribute, AttributeValue, [Option] | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-018 | Fixed content substitutions on save: `&`→`and`; Cut-Out variants→`Cutout`; CR/LF removed. | `modifyOtherDescription()` | Q-DESC-030 | OtherDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-019 | Editing a shared `OtherDescription` may spawn a new `DescriptionId` and re-point the entity. | `modifyOtherDescription()` | Q-DESC-022 (new-id), Q-TRAN-010 | OtherDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-020 | Option descriptions interact with a `ProductCategoryMask` for fixed option ids (8/28/3344/3346/6790/6791). | `modifyOtherDescription()` | — | ProductCategory, [Option], OtherDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-021 | Lifestyle/marketing text is read-only here and always English. | row-select handler | Q-DESC-020 | ProductDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-022 | Products resolve `currentDescriptionId` from lang 1 even when the selected row is missing (id fallback, not text). | row-select handler | Q-DESC-020, Q-DESC-021 | ProductDescription, Product | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-023 | Product-name sync runs only for English edits with a non-empty short description + checks. | `submitData()` | Q-DESC-026 | Product | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-024 | On non-product tabs, English edits also update the owning entity's `Name`. | `modifyOtherDescription()` | Q-DESC-030 | Attribute, AttributeValue, [Option], OptionValue, ProductRange | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-025 | Saving an English category name prompts whether to also update `ProductCategory.Name`. | `modifyOtherDescription()` | Q-DESC-030 | CatalogueProductCategories, ProductCategory | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-026 | Programmatic descriptions use a token template (`{id}`/`#{id}`/`~{id}`); unresolved `{` blocks the update. | `generateProgrammaticDescription()` | Q-DESC-040, Q-TRAN-012 | ProductDescription, Attribute, AttributeValue | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-027 | A retain-case list restores casing; abbreviation mode maps `Back-to-back`→`B2B`, `Single Sided`→`SS`. | `generateProgrammaticDescription()` | — | — | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-028 | Bulk programmatic apply updates `LongDescription`, inserting a row for missing `lang > 1`. | `button_prog_update_Click` | Q-DESC-041 | ProductDescription, Product | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-029 | The Sort button opens `OrderCategories` for the catalogue with `catalogueId = -1`. | `SortButton_Click` → `OrderCategories` | — | CatalogueProductCategories, Catalogue | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-030 | The Alpha sort button is a **dead** stub (confirm dialog, does nothing). | Alpha sort handler (`ProductDescriptions.cs:13126`) | — | — | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-031 | Find & Replace is a separate Product-only dialog with positional language. | `TranslationButton_Click` → `DescriptionsFindReplace` | Q-DESC-050, Q-TRAN-015/016 | ProductDescription | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-032 | Read-only: editable when `ReadOnly==0` and not a read-only connection; `DescriptionEdit`/admin/`shacu9` force editable. | `catalogueIsReadOnly()` | Q-DESC-013 | PDMUserCatalogues, Catalogue | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-033 | Switching catalogue/category/language with unsaved edits is blocked and reverted (unless read-only). | `catalogue_selector_SelectedIndexChanged`, `category_selector_SelectedIndexChanged` | — | — | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-034 | Closing with unsaved edits prompts "Are you sure you want to exit?"; No cancels. | form-close handler (`ProductDescriptions.cs:10419`) | — | — | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-035 | Fabric tabs support incremental keyboard search of the grid by typed prefix. | fabric tab key handler (`ProductDescriptions.cs:10497`) | — | OptionValue | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-036 | DPS/"Other" reconciliation dedupes on English text with quote normalisation. | "Other" import/dedupe | Q-DESC-051 | OtherDescription, DPSText | [13_Descriptions](../../13_Descriptions.md) |
| BR-DESC-037 | `metaDescriptions` is an inert DTO participating in no persistence. | `metaDescriptions` (DTO) | — | — | [13_Descriptions](../../13_Descriptions.md) |

## BR-SRCH — Search (DataQuery) → [doc](../../14_Search.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-SRCH-001 | `DataQuery` is one reusable dialog whose behaviour is switched on the form Title/label texts. | `initDataQuery()`, `processQuery()` | — | — | [14_Search](../../14_Search.md) |
| BR-SRCH-002 | The search value replaces `{text}` via `String.Replace` with **no** parameterization/escaping (injectable). | `processQuery()` | Q-SRCH-005..027 | Item, Product, Attribute, [Option] | [14_Search](../../14_Search.md) |
| BR-SRCH-003 | Wildcard translation `*`→`%` after substitution, protecting `/*`/`*/` comment markers. | `processQuery()` | — | — | [14_Search](../../14_Search.md) |
| BR-SRCH-004 | A query runs only when the search box is non-empty or the SQL has no `{text}` token. | `processQuery()` | — | — | [14_Search](../../14_Search.md) |
| BR-SRCH-005 | For `SELECT Item.Item` queries, an item-status filter is injected by rewriting `WHERE `. | `processQuery()` (`ComboBox3`) | Q-SRCH-007..009 | Item | [14_Search](../../14_Search.md) |
| BR-SRCH-006 | `{combo_val}`/`{site_val}` come from the combo/site id lists. | `processQuery()`, `updateComboBox()` | Q-SRCH-001, Q-SRCH-002 | Site, Product_Code | [14_Search](../../14_Search.md) |
| BR-SRCH-007 | Default site index = position of `DefaultSiteId`, else 0. | `initDataQuery()` | Q-SRCH-001 | Site | [14_Search](../../14_Search.md) |
| BR-SRCH-008 | "Search by name" toggles the WHERE between `Item.Item` and `Product.Name` LIKE. | `processQuery()` (`check_byname`) | Q-SRCH-005 | Item, Product | [14_Search](../../14_Search.md) |
| BR-SRCH-009 | Catalogues-by-item probes existence to decide exact vs contains wildcard. | `processQuery()` | Q-SRCH-010 | Item, Catalogue, CatalogueItems | [14_Search](../../14_Search.md) |
| BR-SRCH-010 | `check_URL` visible only for specific titles; includes unreleased union / widens status. | `processQuery()` (`check_URL`) | Q-SRCH-010, Q-SRCH-009 | CatalogueItems, CatalogueItemsUnreleased | [14_Search](../../14_Search.md) |
| BR-SRCH-011 | For "…by PLC Group", `{status}` = `< 2` default, or `>= 0` with "Include OBS data". | `processQuery()` | Q-SRCH-009 | ProductGroupCodes, Product, Item | [14_Search](../../14_Search.md) |
| BR-SRCH-012 | Status codes decode to `0→URL, 1→ACT, 2→OBS, 3→HLD` in the details pane. | `updateList()` | — | Product, Item | [14_Search](../../14_Search.md) |
| BR-SRCH-013 | Result rendering: col 0 → list; other columns → `name: value`, suppressing helper columns. | `updateList()` | — | — | [14_Search](../../14_Search.md) |
| BR-SRCH-014 | `ProductId`/`Description`/`ProductCodeId[Override]` columns are captured into id lists (blank override → -1). | `processQuery()` | — | Product, Product_Code, Item | [14_Search](../../14_Search.md) |
| BR-SRCH-015 | `DisplayOrder` is read for ordering but never shown as a detail line. | `updateList()` | — | Catalogue | [14_Search](../../14_Search.md) |
| BR-SRCH-016 | Item Option Data Report uses bespoke formatting (`Option2 - optval_name`, `Parent:` prefix). | `processQuery()`, `updateList()` | Q-SRCH-025 | PDMOptionDataReport (proc) | [14_Search](../../14_Search.md) |
| BR-SRCH-017 | `Category`/`Range` detail lines append the id in parentheses. | `updateList()` | — | ProductCategory, ProductRange | [14_Search](../../14_Search.md) |
| BR-SRCH-018 | PLC-override column: blank → `-1`; current combo compared to detect a pending change. | `updateButtons()` | — | Item, Product_Code | [14_Search](../../14_Search.md) |
| BR-SRCH-019 | `ApplyButton` enables only when the selected PLC/override differs from the stored value. | `updateButtons()`, `ApplyButton_Click` | — | Product, Item | [14_Search](../../14_Search.md) |
| BR-SRCH-020 | `ApplyButton` writes an audit pair **before** `UPDATE Product SET ProductCodeId` (audit not gated here). | `ApplyButton_Click` | Q-SRCH-031 | Product, PDMAudit.dbo.Transactions, PDMAudit.dbo.ProdCodeUpdates | [14_Search](../../14_Search.md) |
| BR-SRCH-021 | `ApplyToAllButton` updates `ProductCodeId` **and** `ProductCodeIdOverride` for every result row (no confirmation). | `ApplyToAllButton_Click` | Q-SRCH-032 | Product, Item, PDMAudit.dbo.Transactions, PDMAudit.dbo.ProdCodeUpdates | [14_Search](../../14_Search.md) |
| BR-SRCH-022 | `ReactivateButton` (Non-Active title) forces `Product.Status = 1` regardless of prior status. | `ReactivateButton_Click` | Q-SRCH-033 | Product | [14_Search](../../14_Search.md) |
| BR-SRCH-023 | `DeleteButton` deletes `ItemOptionValues` only for catalogues the user can write (or admin). | `DeleteButton_Click` | Q-SRCH-034 | ItemOptionValues, CatalogueItems, PDMUserCatalogues | [14_Search](../../14_Search.md) |
| BR-SRCH-024 | `DeleteButton` visible only for Option-Increment title **and** `PriceMaintenance`. | `DeleteButton_Click` | — | ItemOptionValues | [14_Search](../../14_Search.md) |
| BR-SRCH-025 | The EOS-hide checkbox flips `Product.HideInEOSCloud` on check-change with no confirmation. | `check_hideInEOSCloud_CheckChanged` | Q-SRCH-003, Q-SRCH-004 | Product, Item | [14_Search](../../14_Search.md) |
| BR-SRCH-026 | Drill-down scrapes the parent id from the details text, not a bound field. | `label_catalogues_Click`, `label_products_Click` | Q-SRCH-022, Q-SRCH-023 | CatalogueAttributeValues, CatalogueOptionValues | [14_Search](../../14_Search.md) |
| BR-SRCH-027 | For `SELECT Item.Item` queries, `label_item` becomes a hyperlink to the Application-Text popup. | `label_item.Click`, `showApplicationText` | Q-SRCH-029 | Product, ProductDescription | [14_Search](../../14_Search.md) |
| BR-SRCH-028 | Validate Images runs a background thread scoped to the catalogue combo; requires the UNC image dir. | `ItemInfoButton_Click` → `ValidateImageThread` | Q-SRCH-028 | Catalogue, Product | [14_Search](../../14_Search.md) |
| BR-SRCH-029 | Empty Product Application Text validator dumps offenders to a `debug_form`. | `ItemInfoButton_Click` | Q-SRCH-030 | Product, ProductDescription, CatalogueItems | [14_Search](../../14_Search.md) |
| BR-SRCH-030 | CSV export writes `list;desc;<detail values>` with a Title-derived filename. | `label_export_Click` | — | — | [14_Search](../../14_Search.md) |
| BR-SRCH-031 | Item Option Increments uses `MultiExtended` selection for multi-row delete. | `processQuery()` | Q-SRCH-027 | ItemOptionValues, Item | [14_Search](../../14_Search.md) |
| BR-SRCH-032 | `[Custom Function / Query]` is a disabled developer stub (`MsgBox("no function currently assigned")`) — **dead**. | `CustomFunctionQueryToolStripMenuItem_Click` | — | — | [14_Search](../../14_Search.md) |
| BR-SRCH-033 | `pCon mdb query …` opens a separate `MDBQuery` form, not `DataQuery`. | `PConMdbQueryToolStripMenuItem_Click` → `MDBQuery` | — | — | [14_Search](../../14_Search.md) |
| BR-SRCH-034 | Catalogues-by-Fabric relabels the details `Status:` line to `Catalogue Status:`. | `processQuery()`, `updateList()` | Q-SRCH-012 | Catalogue, CatalogueOptionValues, [Option] | [14_Search](../../14_Search.md) |
| BR-SRCH-035 | Operator-precedence **defect**: unparenthesised `AND…OR…` returns any-status order-code matches. | — | Q-SRCH-014, Q-SRCH-015 | AttributeValue, OptionValue | [14_Search](../../14_Search.md) |
| BR-SRCH-036 | Search-for-PDM-Item and the app-text validator hardcode `SiteId = 1` for the PLC join. | `SearchForItemToolStripMenuItem_Click`, `ItemInfoButton_Click` | Q-SRCH-005, Q-SRCH-030 | Product_Code | [14_Search](../../14_Search.md) |
| BR-SRCH-037 | Non-Active Products / Item Option Increments pre-seed `text_search = "*"` and hide the status combo. | `NonActiveProductsToolStripMenuItem_Click`, `ItemOptionIncrementsToolStripMenuItem_Click` | Q-SRCH-026, Q-SRCH-027 | Product, ItemOptionValues | [14_Search](../../14_Search.md) |
| BR-SRCH-038 | Categories-by-PLC excludes `ProductCategoryId` 999 and 1000. | `CategoriesByProductLineToolStripMenuItem_Click` | Q-SRCH-013 | ProductCategory | [14_Search](../../14_Search.md) |
| BR-SRCH-039 | Hover cue: `label_item` turns blue only for `SELECT Item.Item`; the others always turn blue. | label hover handlers | — | — | [14_Search](../../14_Search.md) |
| BR-SRCH-040 | Empty `_descList` with results collapses detail panes into a list-only mode. | `updateList()` | — | — | [14_Search](../../14_Search.md) |
| BR-SRCH-041 | Column-0 rendering: `Option2 - optval_name` for the Option Data Report, else the raw first column. | `updateList()` | Q-SRCH-025 | PDMOptionDataReport (proc) | [14_Search](../../14_Search.md) |
| BR-SRCH-042 | No-result handling shows title-specific, upper-cased messages. | `processQuery()` | — | — | [14_Search](../../14_Search.md) |
| BR-SRCH-043 | Result count is shown; Copy/Export appear only when `N > 0`. | `processQuery()` | — | — | [14_Search](../../14_Search.md) |
| BR-SRCH-044 | Every DB call opens/closes a fresh connection; multi-statement writes are non-transactional. | `ConnectionFactory.CreateNewConnection` | Q-SRCH-031, Q-SRCH-032 | PDMAudit.dbo.Transactions, Product, Item | [14_Search](../../14_Search.md) |
| BR-SRCH-045 | On exception the full SQL **and** stack trace are shown in a MsgBox (information disclosure). | `processQuery()` (catch) | — | — | [14_Search](../../14_Search.md) |

## BR-FILT — Filtering (UI Groups) → [doc](../../15_Filtering.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-FILT-001 | A UI Group is a per-catalogue+category bucket keyed by functional-attribute selectors. | `loadUIGroups`, `getUIGroupIdForProduct` | Q-FILT-006 | CatalogueUIGroups, OtherDescription | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-002 | Live only via CAD Maintenance → UI Groups (`CADMaintenance` priv); the MainMenu Layout XML button is permanently hidden — **dead entry point**. | `UIGroupsButton_Click`, `LayoutButton_Click` (dead) | — | — | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-003 | Dual data mode: OFDA in-memory lists + `groupdata.txt` if loaded, else the PDM DB. | `loadUIGroups`, `loadPDMData`, `LoadOFDAThread` | Q-FILT-006 | CatalogueUIGroups (else groupdata.txt) | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-004 | Catalogue list scoped to the user's `PDMUserCatalogues` and `Status = 1`. | `initArrays` | Q-FILT-001 | PDMUserCatalogues, Catalogue | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-005 | Default catalogue = `DefaultCatalogueId` else "Multiple Catalogues…"; Load pre-selects 57/58/42/4. | `initArrays`, `UIGroupMaintenance_Load` | Q-FILT-001 | Catalogue | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-006 | "Multiple Catalogues…" (id -1) enables multi-select and `CatalogueId IN (…)`. | `updateGroups`, `updateRange` | Q-FILT-003, Q-FILT-005 | CatalogueProductCategories, CatalogueItems | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-007 | Category filter excludes 1/128/129/999, requires `Status < 2`, and appends synthetic 999. | `updateGroups` | Q-FILT-003 | ProductCategory, CatalogueProductCategories | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-008 | Category sort `-1 → 9999`; single catalogue orders by display order, multiple by name. | `updateGroups` | Q-FILT-003 | CatalogueProductCategories | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-009 | Range filter from `CatalogueProductRanges`; `[ All Ranges ]` (-1) shows all; `RedundantCheck` only then. | `updateRange`, `RedundantCheck_CheckedChanged` | Q-FILT-005 | CatalogueProductRanges, ProductRange | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-010 | Product universe scoped by Catalogue×Category×Range; SP-Components (999) traverses `ItemComponents`. | `updateRange` | Q-FILT-005 | Product, CatalogueProductRanges, CatalogueItems, ItemComponents | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-011 | Functional attributes = `AttributeType = 0` and `ModelSuffix IS NULL`, ordered by display order. | `getUIGroupIdForProduct`, `product_list_SelectedIndexChanged` | Q-FILT-007, Q-FILT-008 | Attribute, AttributeValue, ProductAttributeValues | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-012 | `getUIGroupIdForProduct` returns the first group (by sequence) the product satisfies, else -1. | `getUIGroupIdForProduct` | Q-FILT-007 | CatalogueUIGroups, ProductAttributeValues | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-013 | A group is considered only when its category/range equals the product's or is -1 (with 999 SP allowance). | `getUIGroupIdForProduct` | — | CatalogueUIGroups | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-014 | Match: every product token must be covered by the group's list, a prefix wildcard, or DefaultedGroups. | `getUIGroupIdForProduct` | — | CatalogueUIGroups, ProductAttributeValues | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-015 | DefaultedGroups: a token whose attribute name appears in `DefaultedGroups` is satisfied implicitly. | `getUIGroupIdForProduct` | — | CatalogueUIGroups | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-016 | A `UIGroups` entry containing `{` is truncated at `{` and used as a `StartsWith` prefix match. | `getUIGroupIdForProduct` | — | CatalogueUIGroups | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-017 | Products are placed in Assigned (`> -1`) or Unassigned (`-1`); counts shown in labels. | `loadUIGroups` | — | CatalogueUIGroups, Product | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-018 | A redundant (no-product) group icon is Crimson only with `[ All Ranges ]` + `RedundantCheck`. | `loadUIGroups` | — | CatalogueUIGroups | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-019 | Create requires a product with no group assignment and ≥1 selected functional attribute. | `AddIconButton_Click`, `getUIGroupIdForProduct` | Q-FILT-010 | CatalogueUIGroups, OtherDescription | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-020 | On create, `UIGroups` = selected tokens, `DefaultedGroups` = unselected, `ImageFile` = NULL. | `AddIconButton_Click` | Q-FILT-010 | CatalogueUIGroups, OtherDescription | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-021 | Delete decrements the `Sequence` of groups above the removed one, then DELETEs. | `RemoveIconButton_Click` | Q-FILT-011 | CatalogueUIGroups | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-022 | Modify redefines the selector string via InputBox (must contain `=`); trailing comma enforced. | `ModifyButton_Click` | Q-FILT-012 | CatalogueUIGroups | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-023 | Submit renames the group via `OtherDescription.ShortDescription` (lang 1); blank = no-op. | `SubmitButton_Click` | Q-FILT-013 | CatalogueUIGroups, OtherDescription | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-024 | Submit applies the sequence change by shifting groups between old and new positions. | `SubmitButton_Click` | Q-FILT-014 | CatalogueUIGroups | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-025 | Apply placement sets `Product.CADPlaceProgram` (strips old `[…]`, appends new). | `ApplyButton_Click` | Q-FILT-016 | Product | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-026 | Assigned products without a valid placement type are drawn in red. | `products_assigned_DrawItem`, `productHasValidPlacementType` | — | Product | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-027 | Dragging an image onto a group icon copies it to `Images\` and updates `ImageFile`. | `UIGroupIcon_DragDrop`, `updateGroupImage` | Q-FILT-015 | CatalogueUIGroups | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-028 | The relative image folder (`Images\`) is auto-created on load if missing. | `UIGroupMaintenance_Load` | — | — | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-029 | dbacw8-only features: PDM/Other buttons and Import/Export layout menu items. | `UIGroupMaintenance_Load` | — | — | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-030 | `ExportPDMLayoutData` (dbacw8) serialises all UI groups into pipe-delimited `groupdata.txt`. | `ExportPDMLayoutDataToolStripMenuItem_Click` | Q-FILT-017 | CatalogueUIGroups, Catalogue, OtherDescription | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-031 | In OFDA mode, Add/Remove/Modify/Submit edit `groupdata.txt` in place instead of SQL. | `AddIconButton_Click`, `RemoveIconButton_Click`, `ModifyButton_Click`, `SubmitButton_Click` | — | groupdata.txt | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-032 | `ImportLayoutFromCatalogue` is an **empty stub** (dead menu item). | `ImportLayoutFromCatalogueToolStripMenuItem_Click` | Q-FILT-018 | — | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-033 | Apostrophe escaping (`'`→backtick) is inconsistent across handlers. | `AddIconButton_Click`, `SubmitButton_Click`, `ModifyButton_Click` | Q-FILT-010..013 | CatalogueUIGroups, OtherDescription | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-034 | The multi-catalogue list is pre-seeded with hardcoded catalogue ids 57/58/42/4. | `UIGroupMaintenance_Load` | — | Catalogue | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-035 | Product names are concatenated **unescaped** into several statements (injectable). | `AddIconButton_Click`, `ApplyButton_Click` | Q-FILT-005, Q-FILT-010, Q-FILT-016 | Product | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-036 | `_readOnlyCatalogues` is captured but **never enforced** — read-only catalogues remain editable (authorization gap). | `initArrays` | Q-FILT-001 | PDMUserCatalogues | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-037 | All DB reads use `WITH (NOLOCK)` (dirty reads). | all read handlers | Q-FILT-001..009 | CatalogueUIGroups, ProductCategory, Product | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-038 | `UIPanel_Paint` re-runs the matcher per icon to position the marker and gate RemoveIcon. | `UIPanel_Paint`, `getUIGroupIdForProduct` | Q-FILT-007 | CatalogueUIGroups | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-039 | SP-Components source requires `ProductRangeId <> 999` and joins `ItemComponents`. | `initArrays`, `updateRange` | Q-FILT-002, Q-FILT-005 | Product, Item, ItemComponents | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-040 | Every handler shows `MsgBox(ex.ToString())` (disclosure) with no rollback. | all handlers (catch) | — | — | [15_Filtering](../../15_Filtering.md) |
| BR-FILT-041 | `Ctrl+A` selects all items in the assigned-products list. | `ProcessCmdKey` override | — | — | [15_Filtering](../../15_Filtering.md) |

## BR-IMG — Images → [doc](../../17_Images.md)

*(Non-contiguous: ranges are 001–012, 020–024, 030–031, 040–043, 050–059, 070–076, 080–081.)*

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-IMG-001 | Default signature `GetImage(imageFile, materialpath="", safeload=true, noscale=false)`. | `GetImage.GetImage` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-002 | With `materialpath == ""`, all backslashes in `imageFile` are stripped first. | `GetImage.GetImage` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-003 | Token expansion: a fixed ordered set of `Replace` calls restores collapsed tokens to sub-paths. | `GetImage.GetImage` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-004 | Candidate path = `Global.filePaths[i] + imageFile` per base index. | `GetImage.GetImage` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-005 | If the base starts `"http"`, backslashes become forward slashes. | `GetImage.GetImage`, `GetImageFromURL` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-006 | Any candidate containing `"C:\"` is skipped unless `testMode`; so `filePaths[0]`/`[2]` are **dead** in production. | `GetImage.GetImage` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-007 | Non-http base: if the file exists, load via `SafeImageFromFile` (or `Image.FromFile`), then break. | `GetImage.GetImage`, `SafeImageFromFile` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-008 | http base: `GetImageFromURL(text)`; non-null ⇒ success. | `GetImageFromURL` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-009 | With `materialpath != ""` the candidate is `materialpath + imageFile` (base array bypassed). | `GetImage.GetImage` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-010 | Total-failure fallback = `Global.imageUnavailable`, which is **never assigned** ⇒ always `null`. | `GetImage.GetImage` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-011 | An outer re-index loop runs once unless `filePaths.Length` changes mid-iteration. | `GetImage.GetImage` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-012 | Exceptions are swallowed; OOM ignored, others pop a diagnostic MsgBox. | `GetImage.GetImage` (catch) | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-020 | `SafeImageFromFile` loads via a FileStream + `new Bitmap(stream)` (avoids file lock). | `SafeImageFromFile` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-021 | Target display width is 180px with aspect factor 1.3 and reference height 160. | `SafeImageFromFile` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-022 | Scaling picks the dominant ratio using `HighQualityBilinear` interpolation. | `SafeImageFromFile` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-023 | `noscale = true` bypasses resizing (native size). | `SafeImageFromFile` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-024 | On any exception the error is shown in a MsgBox and `null` returned. | `SafeImageFromFile` (catch) | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-030 | `HttpWebRequest.Timeout = 100 ms` — extremely short; slow servers reported unreachable. | `URLExists` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-031 | Reachability returns `true` by default; only a non-empty `WebException` sets `false`. | `URLExists` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-040 | No-op guard: missing `wwwroot\PDM\Images` share ⇒ return immediately. | `ValidateImages.validateImages()` | — | Product | [17_Images](../../17_Images.md) |
| BR-IMG-041 | Only `Product.WFImageFile` is checked, against the `wwwroot` share. | `ValidateImages.validateImages()` | Q-IMG-001 | Product | [17_Images](../../17_Images.md) |
| BR-IMG-042 | Broken references are **silently auto-nulled** (no confirmation) during DPS publish. | `ValidateImages.validateImages()` | Q-IMG-002 | Product | [17_Images](../../17_Images.md) |
| BR-IMG-043 | Errors surface via MsgBox; connection always closed in `finally`. | `ValidateImages.validateImages()` | — | Product | [17_Images](../../17_Images.md) |
| BR-IMG-050 | Two modes by `_cloud` flag (title contains "EOS Cloud"): cloud validates catalogue+attr images, standard validates products. | `ValidateImageThread.ExecThread()` | Q-IMG-003, Q-IMG-004, Q-IMG-005 | Catalogue, Product, AttributeValue | [17_Images](../../17_Images.md) |
| BR-IMG-051 | `_catalogueId > 0` restricts to a catalogue's items; `= 0` validates all. | `ValidateImageThread.ExecThread()` | Q-IMG-003, Q-IMG-004, Q-IMG-005 | CatalogueItems, Item | [17_Images](../../17_Images.md) |
| BR-IMG-052 | Active filter `Status < 2` on catalogue/product/range/attribute value. | `ValidateImageThread.ExecThread()` | Q-IMG-003, Q-IMG-004, Q-IMG-005 | Catalogue, Product, ProductRange, AttributeValue | [17_Images](../../17_Images.md) |
| BR-IMG-053 | Product ranges `999` and `1000` are excluded from image validation. | `ValidateImageThread.ExecThread()` | Q-IMG-004, Q-IMG-005 | Product, ProductRange | [17_Images](../../17_Images.md) |
| BR-IMG-054 | Existence check uses the `HMEURONET` share (contrast `ValidateImages` `wwwroot`). | `ValidateImageThread.ExecThread()` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-055 | Unresolved if the file is missing **or** the path ends with `\na.jpg` (placeholder). | `ValidateImageThread.ExecThread()` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-056 | Catalogue rows stored as `-1 * CatalogueId` with the label `"<Catalogue Image>"`. | `ValidateImageThread.ExecThread()` | Q-IMG-003 | Catalogue | [17_Images](../../17_Images.md) |
| BR-IMG-057 | Duplicate attribute values skipped (each swatch validated once). | `ValidateImageThread.ExecThread()` | Q-IMG-004 | AttributeValue | [17_Images](../../17_Images.md) |
| BR-IMG-058 | Cancellable via the `terminate` flag; on terminate returns without reporting. | `ValidateImageThread.ExecThread()` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-059 | Unresolved references are listed in a `debug_form` with a total footer; else a MsgBox confirms. | `ValidateImageThread.ExecThread()` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-070 | Canonical product image path = `Images\Products\<sanitized>.jpg` under the HMEURONET base. | CADMaintenance Validate Product Images | Q-IMG-006 | Product | [17_Images](../../17_Images.md) |
| BR-IMG-071 | Filename sanitisation: trailing `/` removed; `/`→`-`; `.`→`-`; leading/trailing `-` trimmed. | CADMaintenance Validate Product Images | — | Product | [17_Images](../../17_Images.md) |
| BR-IMG-072 | Special case: categories 615 / product codes 805/1009 truncate the code at the first `.`. | CADMaintenance Validate Product Images | — | Product, ProductRange, Product_Code | [17_Images](../../17_Images.md) |
| BR-IMG-073 | Codes starting `SFAB`/`SFSA`/`SFSB` with `-` are truncated at the first `-` (shared fabric image). | CADMaintenance Validate Product Images | — | Product, Product_Code | [17_Images](../../17_Images.md) |
| BR-IMG-074 | `Images\Temp\na.jpg` is the recognised placeholder; still-pointing products reported missing. | CADMaintenance Validate Product Images | Q-IMG-006 | Product | [17_Images](../../17_Images.md) |
| BR-IMG-075 | Non-canonical files are physically moved to the canonical name (existing renamed `_prev[N]`). | CADMaintenance Validate Product Images | — | Product | [17_Images](../../17_Images.md) |
| BR-IMG-076 | After moves, all `ImageFile` references are rewritten with a per-entity count report. | CADMaintenance Validate Product Images | Q-IMG-007..013 | Product, AttributeValue, OptionValue, CatalogueProductCategories, Catalogue, ProductRange, HandbookProducts | [17_Images](../../17_Images.md) |
| BR-IMG-080 | The HTTP placeholder form is `http://www.hmeuronet.com/PDM/Images/Temp/na.jpg`. | `ClippingsExport` | — | — | [17_Images](../../17_Images.md) |
| BR-IMG-081 | Layout/OFDA exports strip the `na.jpg` placeholder (app-wide "no image" sentinel). | `ExportLayoutStyleThread`, `OFDAExport` | — | — | [17_Images](../../17_Images.md) |
