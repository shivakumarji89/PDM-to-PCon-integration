# SQL Index

Cross-reference of **every documented query** in the legacy PDM handbook, grouped by
business domain. Each row links back to the module doc where the query's full SQL,
`file:line` origin, and "why" note live. This file is a **navigation layer only** —
it does not re-transcribe SQL bodies.

> **Cross-cutting patterns** (injection surface, `NOLOCK`, three-part audit names,
> Jet/OLE-DB access, identity round-trips, hard-coded ids) are catalogued once in
> [../25_Common_SQL.md](../25_Common_SQL.md) as `P-SQL-01 … P-SQL-11`. Stored procedures
> and functions are listed in the [Stored Procedures & Functions](#stored-procedures--functions) section below.

**Query-ID conventions**
- `Q-XXX-NNN` — SQL Server query (`SqlCommand`, PDMLive / PDMPublished / PDMAudit).
- `O-XXX-NNN` — OLE DB / Jet query against a per-workspace pCon Access MDB (`OleDbCommand`).
- Tables in **bold** are pCon Jet MDB (`tCOMd_*` / `tGEOd_*`); `PDMAudit.dbo.*` are the audit DB.
- "Related BRs" cites business-rule ids from [Business_Rules_Index.md](Business_Rules_Index.md) where documented; `—` = none recorded in source.

---

## Auth / Permissions

Source: [../01_Authentication.md](../01_Authentication.md), [../02_User_Permissions.md](../02_User_Permissions.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-AUTH-001 | Load logged-in user's privilege row + capability flags | PDMUserPrivileges | `AuthenticateUser.setUserPrivileges` | BR-AUTH-005 | [../01](../01_Authentication.md) |
| Q-PERM-001 | Load a user's full privilege profile for editing | PDMUserPrivileges | `UserAdmin` | BR-PERM-002 | [../02](../02_User_Permissions.md) |
| Q-PERM-002 | List all users | PDMUserPrivileges | `UserAdmin` | — | [../02](../02_User_Permissions.md) |
| Q-PERM-003 | Toggle a capability flag on a user | PDMUserPrivileges | `UserAdmin` | BR-PERM-002 | [../02](../02_User_Permissions.md) |
| Q-PERM-004 | Grant / revoke catalogue access (insert/delete) | PDMUserCatalogues | `UserAdmin` | BR-PERM-009 | [../02](../02_User_Permissions.md) |
| Q-PERM-005 | Grant / revoke SyteLine view access | SL7UserViews | `UserAdmin` | — | [../02](../02_User_Permissions.md) |
| Q-PERM-006 | Enumerate DB views/objects for the view-grant UI | sysobjects, sysusers | `UserAdmin` | — | [../02](../02_User_Permissions.md) |

---

## Catalogues & Categories

Source: [../03_Catalogues.md](../03_Catalogues.md), [../04_Product_Categories.md](../04_Product_Categories.md)
*(Not one of the mandated domain buckets, but these queries are documented and must be indexed.)*

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-CAT-001 | Load the current user's accessible catalogues | PDMUserCatalogues, Catalogue | `ProductDescriptions.initialiseCatalogues` | BR-CAT-003, BR-PERM-009 | [../03](../03_Catalogues.md) |
| Q-CAT-002 | Load catalogues for the ordering screen | Catalogue, OtherDescription | `OrderCategories_Load` | see Q-ORD-002 | [../03](../03_Catalogues.md) |
| Q-CAT-003 | Persist catalogue display order | Catalogue | `OrderCategories.SubmitButton_Click` | — | [../03](../03_Catalogues.md) |
| Q-CAT-004 | Read catalogue flags | Catalogue | `ProductDescriptions.EOSCatalogueLabelCheck_Changed` | — | [../03](../03_Catalogues.md) |
| Q-CAT-005 | Write catalogue flags | Catalogue | `ProductDescriptions.EOSCatalogueLabelCheck_Changed` | BR-CAT (2nd-order injection) | [../03](../03_Catalogues.md) |
| Q-CAT-006 | Load user catalogues for CAD maintenance | PDMUserCatalogues, Catalogue | `CADMaintenance` | BR-PERM-009 | [../03](../03_Catalogues.md) |
| Q-CAT-007 | Read catalogue / site flags | Catalogue | `ProductDescriptions` | — | [../03](../03_Catalogues.md) |
| Q-CAT-008 | Catalogue image-file lookup | Catalogue | `CADMaintenance` | — | [../03](../03_Catalogues.md) |
| Q-CAT-009 | Alphabetical catalogue sort (dead / unwired) | — | `ProductDescriptions.AlphaButton_Click` | BR-CAT-014 | [../03](../03_Catalogues.md) |
| Q-CATEG-001 | Load a catalogue's product categories | ProductCategory, CatalogueProductCategories, OtherDescription | `CADMaintenance` | BR-CATEG-004 | [../04](../04_Product_Categories.md) |
| Q-CATEG-002 | Load categories for ordering (dead) | CatalogueProductCategories, OtherDescription | `OrderCategories_Load` | BR-CATEG-011 | [../04](../04_Product_Categories.md) |
| Q-CATEG-003 | Persist category display order (dead) | CatalogueProductCategories | `OrderCategories.SubmitButton_Click` | BR-CATEG-010 | [../04](../04_Product_Categories.md) |
| Q-CATEG-004 | Category image-file lookup | CatalogueProductCategories | `CADMaintenance` | — | [../04](../04_Product_Categories.md) |
| Q-CATEG-005 | Category list for report / tree | CatalogueProductCategories, ProductCategory | `CADMaintenance` | — | [../04](../04_Product_Categories.md) |
| Q-CATEG-006 | Category name for the data-picker | Catalogue | `AddDataList` | — | [../04](../04_Product_Categories.md) |

---

## Products

Source: [../05_Products.md](../05_Products.md) — callers are `SuperProductMaintenance.cs` (SPM)
and `SuperProductVarCondRelation.cs` (VarCond) unless noted.

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-PROD-001 | Reusable component items list | Item, ItemComponents | SPM `:2391` | — | [../05](../05_Products.md) |
| Q-PROD-002 | User's editable catalogues | PDMUserCatalogues, Catalogue | SPM `:2427` | BR-PERM-009 | [../05](../05_Products.md) |
| Q-PROD-003 | Sites (excl. site 20) | Site | SPM `:2449` | BR-PROD-007 | [../05](../05_Products.md) |
| Q-PROD-004 | Currency list | Currency | SPM `:2471` | — | [../05](../05_Products.md) |
| Q-PROD-005 | Categories for catalogue (excl. 1,128,129,999) | ProductCategory, CatalogueProductCategories, OtherDescription | SPM `updateCatalogueList:2543` | BR-PROD-008 | [../05](../05_Products.md) |
| Q-PROD-006 | Options for a category | [Option] | SPM `:2616` | — | [../05](../05_Products.md) |
| Q-PROD-007 | Product list (released + unreleased) | Product, ProductRange, Item, ItemComponents, BaseAttributeValues, CatalogueAttributeValues, CatalogueItems, CatalogueItemsUnreleased | SPM `updateProductList:2723` | — | [../05](../05_Products.md) |
| Q-PROD-009 | Items for a product | Product, ProductRange, Item, ItemComponents, BaseAttributeValues, CatalogueAttributeValues | SPM `updateItemList:2856` | — | [../05](../05_Products.md) |
| Q-PROD-010 | Option-data report for an item | *(proc `PDMOptionDataReport`)* | SPM `updateSPOptionList` | — | [../05](../05_Products.md) |
| Q-PROD-011 | Product code for an item | Product_Code | SPM `:3424` | P-SQL-02 | [../05](../05_Products.md) |
| Q-PROD-012 | Matching product codes by prefix | Product_Code | SPM `:3441` | — | [../05](../05_Products.md) |
| Q-PROD-013 | Component list for an item | Item, ItemComponents, Product, Product_Code | SPM `updateComponentList:3096` | P-SQL-02 (ProductCodeIdOverride) | [../05](../05_Products.md) |
| Q-PROD-014 | Update an edited component row | ItemComponents | SPM `:3771` | — | [../05](../05_Products.md) |
| Q-PROD-015 | Read component sequence to normalise | ItemComponents | SPM `:3717` | — | [../05](../05_Products.md) |
| Q-PROD-016 | Reassign component sequence | ItemComponents | SPM | — | [../05](../05_Products.md) |
| Q-PROD-018 | Item lookup for add / replace | Item | SPM `createNewItem:4035` | — | [../05](../05_Products.md) |
| Q-PROD-019 | Duplicate-component guard | ItemComponents | SPM `:4048` | BR-PROD-019 | [../05](../05_Products.md) |
| Q-PROD-020 | Insert a component | ItemComponents *(fn `fnGetSPComponentCount`)* | SPM `:4058` | — | [../05](../05_Products.md) |
| Q-PROD-021 | Read `FeaturePositionString` | ItemComponents | SPM `:4436` | — | [../05](../05_Products.md) |
| Q-PROD-022 | Option-name lookup | [Option] | SPM `:4461` | — | [../05](../05_Products.md) |
| Q-PROD-023 | Write `FeaturePositionString` | ItemComponents | SPM `:4289` | — | [../05](../05_Products.md) |
| Q-PROD-024 | Price-report component rows | Item, Product, ItemComponents, Product_Code *(fn `fnGetListPriceByItem`)* | SPM `generateXLSReport:5035` | BR-PROD-025 | [../05](../05_Products.md) |
| Q-PROD-025 | Price-report option increments | ItemOptionValues, OptionValue, [Option], ItemComponents, Item, Product, Product_Code, PriceMatrix, Currency *(fn `fnGetListPrice`)* | SPM `:5052` | BR-PROD-025 | [../05](../05_Products.md) |
| Q-PROD-026 | Download super-product defs (CSV export) | Item, ItemComponents, CatalogueItems, CatalogueItemsUnreleased, Product, ProductRange | SPM `downloadSPDefs:5451` | — | [../05](../05_Products.md) |
| Q-PROD-027 | Import super-product defs (resolution) | Item, ItemComponents, Product | SPM `importSPDefs` | — | [../05](../05_Products.md) |
| Q-PROD-030…034 | Delete-component flow (lookup → delete → resequence) | Item, ItemComponents, Product | SPM `menuDeleteComponent_Click:4205` | BR-PROD-041 | [../05](../05_Products.md) |
| Q-PROD-035 | Recompute `IsSuperProduct` flag | Product, ProductRange, Item, ItemComponents | SPM `updateSPFlag:4864` | BR-PROD-030 | [../05](../05_Products.md) |
| Q-PROD-036…038 | Clone super-product flow | Item, CatalogueItems, CatalogueItemsUnreleased, ItemComponents | SPM `CloneButton_Click:5991` | — | [../05](../05_Products.md) |
| Q-PROD-039 | Delete super-product definition | ItemComponents | SPM `DeleteButton_Click:4924` | — | [../05](../05_Products.md) |
| Q-PROD-040 | Bulk-apply candidate items | Item, ItemComponents | SPM | — | [../05](../05_Products.md) |
| Q-PROD-002b / 005b | Catalogue + category loaders (VarCond variant) | PDMUserCatalogues, Catalogue, ProductCategory, CatalogueProductCategories | VarCond `:910` / `:956` | — | [../05](../05_Products.md) |
| Q-PROD-042 | Super-product items for price relations | Item, Product, ProductRange, CatalogueItems, CatalogueItemsUnreleased | VarCond `:1009` | — | [../05](../05_Products.md) |
| Q-PROD-043 | Insert pCon variant-condition relation | **tCOMd_Relation** | VarCond `:1354` (OleDb) | P-SQL-07 | [../05](../05_Products.md) |
| Q-PROD-044 | Resolve new relation id | **tCOMd_Relation** | VarCond `:1359` | — | [../05](../05_Products.md) |
| Q-PROD-045 | Item note lookup | Item | VarCond `:1382` | — | [../05](../05_Products.md) |
| Q-PROD-046 | Master-item fallback note | Item, Product | VarCond `:1414` | — | [../05](../05_Products.md) |
| Q-PROD-047 | pCon rel-object linkage | **tCOMd_RelObj, tCOMd_RelObjRel** | VarCond `:1456` | — | [../05](../05_Products.md) |
| Q-PROD-048 | Clear relations before export | **tCOMd_Relation** | VarCond `ExportButton_Click:1542` | — | [../05](../05_Products.md) |

---

## Articles

Source: [../06_Product_Codes.md](../06_Product_Codes.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-ART-001 | Site list for product-code entry | Site | `ProductCodeEntry_Load` | — | [../06](../06_Product_Codes.md) |
| Q-ART-002 | Insert a new product code | Product_Code | `ProductCodeEntry.AddButton_Click` | BR-ART-014 | [../06](../06_Product_Codes.md) |

> Article/product-code option counts also invoke the `GetProductOptionCount` stored
> proc (OUT param) — see [Stored Procedures & Functions](#stored-procedures--functions).

---

## Attributes

Source: [../07_Attributes.md](../07_Attributes.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-ATTR-001 | Load attribute list | Attribute | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-002 | Load attribute values for an attribute | AttributeValue | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-003 | Insert attribute | Attribute | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-004 | Update attribute | Attribute | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-005 | Delete attribute | Attribute | `AttributeMaintenance` | BR-ATTR (cascade) | [../07](../07_Attributes.md) |
| Q-ATTR-006 | Insert attribute value | AttributeValue | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-007 | Update attribute value | AttributeValue | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-008 | Delete attribute value | AttributeValue | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-009 | Base attribute values for an item | BaseAttributeValues, AttributeValue | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-010 | Product attribute values | ProductAttributeValues | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-011 | Dependent attribute values | DependentAttributeValues | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-012 | Catalogue attribute values | CatalogueAttributeValues | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-013 | Attribute group codes | AttributeGroupCodes | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-014 | Display-order read/normalise | Attribute, AttributeValue | `AttributeMaintenance` | DisplayOrder -1→9999 | [../07](../07_Attributes.md) |
| Q-ATTR-015 | Reorder attributes | Attribute | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-016 | Reorder attribute values | AttributeValue | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-017 | Attribute translations | CatalogueTranslations | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-018 | Fabric-type attribute (hard-coded id 8) | Attribute, AttributeValue | `AttributeMaintenance` | P-SQL-08 (id 8) | [../07](../07_Attributes.md) |
| Q-ATTR-019 | Fabric-colour attribute (hard-coded id 28) | Attribute, AttributeValue | `AttributeMaintenance` | P-SQL-08 (id 28) | [../07](../07_Attributes.md) |
| Q-ATTR-020 | Insert base attribute value | BaseAttributeValues | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |
| Q-ATTR-021 | Delete base attribute value | BaseAttributeValues | `AttributeMaintenance` | — | [../07](../07_Attributes.md) |

---

## Property Values

Source: [../08_Property_Values.md](../08_Property_Values.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-PVAL-001 | Load property values | ProductOptionValues, OptionValue | `PropertyValueMaintenance` | — | [../08](../08_Property_Values.md) |
| Q-PVAL-002 | Option-data report (property expansion) | *(proc `PDMOptionDataReport`)* | `PropertyValueMaintenance` | — | [../08](../08_Property_Values.md) |
| Q-PVAL-003 | Insert property value | ProductOptionValues | `PropertyValueMaintenance` | — | [../08](../08_Property_Values.md) |
| Q-PVAL-004 | Update property value | ProductOptionValues | `PropertyValueMaintenance` | — | [../08](../08_Property_Values.md) |
| Q-PVAL-005 | Delete property value | ProductOptionValues | `PropertyValueMaintenance` | — | [../08](../08_Property_Values.md) |
| Q-PVAL-006 | Dependent property-value resolution | DependentOptionValues | `PropertyValueMaintenance` | — | [../08](../08_Property_Values.md) |

---

## Options

Source: [../09_Options.md](../09_Options.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-OPT-001 | Load option list | [Option] | `OptionMaintenance` | reserved-word bracketing | [../09](../09_Options.md) |
| Q-OPT-002 | Insert option | [Option] | `OptionMaintenance` | — | [../09](../09_Options.md) |
| Q-OPT-003 | Update option | [Option] | `OptionMaintenance` | — | [../09](../09_Options.md) |
| Q-OPT-004 | Delete option | [Option] | `OptionMaintenance` | — | [../09](../09_Options.md) |
| Q-OPT-005 | Option values for an option | OptionValue | `OptionMaintenance` | — | [../09](../09_Options.md) |
| Q-OPT-006 | Product option values | ProductOptionValues | `OptionMaintenance` | — | [../09](../09_Options.md) |
| Q-OPT-007 | Dependent option values | DependentOptionValues | `OptionMaintenance` | — | [../09](../09_Options.md) |
| Q-OPT-008 | Catalogue option values | CatalogueOptionValues | `OptionMaintenance` | — | [../09](../09_Options.md) |
| Q-OPT-009 | Option group codes | OptionGroupCodes | `OptionMaintenance` | — | [../09](../09_Options.md) |
| Q-OPT-010 | Option-data report | *(proc `PDMOptionDataReport` / `…WithIncList` / `…WithIncBase`)* | `OptionMaintenance` | — | [../09](../09_Options.md) |
| Q-OPT-011 | Display-order read / normalise | [Option] | `OptionMaintenance` | DisplayOrder -1→9999 | [../09](../09_Options.md) |
| Q-OPT-012 | Reorder options | [Option] | `OptionMaintenance` | — | [../09](../09_Options.md) |
| Q-OPT-013 | Option translations | CatalogueTranslations | `OptionMaintenance` | — | [../09](../09_Options.md) |
| Q-OPT-014 | CAD scheme link | CADSchemes | `OptionMaintenance` | — | [../09](../09_Options.md) |
| Q-OPT-015 | Product-option-count (OUT param) | *(proc `GetProductOptionCount`)* | `OptionMaintenance` | — | [../09](../09_Options.md) |

---

## Option Values

Source: [../10_Option_Values.md](../10_Option_Values.md)
*(Not a mandated bucket, but documented — indexed here for completeness.)*

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-OVAL-001 | Load option values | OptionValue | `OptionValueMaintenance` | Status 0/1/2/3 legend | [../10](../10_Option_Values.md) |
| Q-OVAL-002 | Insert option value | OptionValue | `OptionValueMaintenance` | — | [../10](../10_Option_Values.md) |
| Q-OVAL-003 | Update option value | OptionValue | `OptionValueMaintenance` | — | [../10](../10_Option_Values.md) |
| Q-OVAL-004 | Delete option value | OptionValue | `OptionValueMaintenance` | — | [../10](../10_Option_Values.md) |
| Q-OVAL-005 | Option-data report | *(proc `PDMOptionDataReport` / `…WithIncList`)* | `OptionValueMaintenance` | — | [../10](../10_Option_Values.md) |
| Q-OVAL-006 | Dependent option values | DependentOptionValues | `OptionValueMaintenance` | — | [../10](../10_Option_Values.md) |
| Q-OVAL-007 | Catalogue option values | CatalogueOptionValues | `OptionValueMaintenance` | — | [../10](../10_Option_Values.md) |
| Q-OVAL-008 | Product option values | ProductOptionValues | `OptionValueMaintenance` | — | [../10](../10_Option_Values.md) |
| Q-OVAL-009 | Item option values (increments) | ItemOptionValues | `OptionValueMaintenance` | BasePriceRef 1/2/3 | [../10](../10_Option_Values.md) |
| Q-OVAL-010 | Fabric band membership | FabricBands, OptionValue | `OptionValueMaintenance` | — | [../10](../10_Option_Values.md) |
| Q-OVAL-011 | Order-code value read/write | OptionValue | `OptionValueMaintenance` | — | [../10](../10_Option_Values.md) |
| Q-OVAL-012 | Display-order read / normalise | OptionValue | `OptionValueMaintenance` | DisplayOrder -1→9999 | [../10](../10_Option_Values.md) |
| Q-OVAL-013 | Reorder option values | OptionValue | `OptionValueMaintenance` | — | [../10](../10_Option_Values.md) |
| Q-OVAL-014 | Option-value translations | CatalogueTranslations | `OptionValueMaintenance` | — | [../10](../10_Option_Values.md) |
| Q-OVAL-015 | Status transition (URL/ACT/OBS/HLD) | OptionValue | `OptionValueMaintenance` | Status legend | [../10](../10_Option_Values.md) |
| Q-OVAL-016 | Group-code assignment | OptionGroupCodes | `OptionValueMaintenance` | — | [../10](../10_Option_Values.md) |
| Q-OVAL-017 | CAD scheme link | CADSchemes | `OptionValueMaintenance` | — | [../10](../10_Option_Values.md) |
| Q-OVAL-018 | Fabric type/colour hard-coded id use (8/28) | OptionValue | `OptionValueMaintenance` | P-SQL-08 | [../10](../10_Option_Values.md) |

---

## Attributes / Options / Descriptions overlap — Translations

Source: [../11_Translations.md](../11_Translations.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-TRAN-001 | Load languages | Language | `Translations` | LanguageId map | [../11](../11_Translations.md) |
| Q-TRAN-002 | Load catalogue translations | CatalogueTranslations | `Translations` | — | [../11](../11_Translations.md) |
| Q-TRAN-003 | Insert catalogue translation | CatalogueTranslations | `Translations` | — | [../11](../11_Translations.md) |
| Q-TRAN-004 | Update catalogue translation | CatalogueTranslations | `Translations` | — | [../11](../11_Translations.md) |
| Q-TRAN-005 | Delete catalogue translation | CatalogueTranslations | `Translations` | — | [../11](../11_Translations.md) |
| Q-TRAN-006 | Attribute translation resolve | CatalogueTranslations, AttributeValue | `Translations` | — | [../11](../11_Translations.md) |
| Q-TRAN-007 | Option translation resolve | CatalogueTranslations, OptionValue | `Translations` | — | [../11](../11_Translations.md) |
| Q-TRAN-008 | Product description translation | ProductDescription | `Translations` | — | [../11](../11_Translations.md) |
| Q-TRAN-009 | Other description translation | OtherDescription | `Translations` | RelatedTable tag | [../11](../11_Translations.md) |
| Q-TRAN-010 | Catalogue application text | CatalogueApplicationText | `Translations` | negative CatalogueId | [../11](../11_Translations.md) |
| Q-TRAN-011 | Language-filtered read (LanguageId) | ProductDescription, OtherDescription | `Translations` | LanguageId map | [../11](../11_Translations.md) |
| Q-TRAN-012 | Missing-translation report | CatalogueTranslations | `Translations` | — | [../11](../11_Translations.md) |
| Q-TRAN-013 | pCon text read | **tCOMd_Text** | `Translations` (SQL Server side) | — | [../11](../11_Translations.md) |
| Q-TRAN-013a | pCon text read (OLE DB variant) | **tCOMd_Text** | `Translations` (OleDb) | P-SQL-07 | [../11](../11_Translations.md) |
| Q-TRAN-014 | pCon text write | **tCOMd_Text** | `Translations` (OleDb) | P-SQL-07 | [../11](../11_Translations.md) |
| Q-TRAN-015 | Bulk translation import | CatalogueTranslations | `Translations` | — | [../11](../11_Translations.md) |
| Q-TRAN-016 | Bulk translation export | CatalogueTranslations, Language | `Translations` | — | [../11](../11_Translations.md) |

---

## Descriptions

Source: [../12_Descriptions.md](../12_Descriptions.md), and description helpers cited in
[../13_Find_Replace.md](../13_Find_Replace.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-DESC-001 | Load product descriptions | ProductDescription, Language | `ProductDescriptions` | LanguageId map | [../12](../12_Descriptions.md) |
| Q-DESC-002…010 | Per-field description read/write set | ProductDescription, OtherDescription | `ProductDescriptions` | RelatedTable tag; P-SQL-02 | [../12](../12_Descriptions.md) |
| Q-DESC-010 | DPS text read | DPSText | `ProductDescriptions` | — | [../12](../12_Descriptions.md) |
| Q-DESC-011 | Insert product description | ProductDescription | `ProductDescriptions` | — | [../12](../12_Descriptions.md) |
| Q-DESC-012 | Update product description | ProductDescription | `ProductDescriptions` | — | [../12](../12_Descriptions.md) |
| Q-DESC-013 | Delete product description | ProductDescription | `ProductDescriptions` | — | [../12](../12_Descriptions.md) |
| Q-DESC-014 | Insert other description | OtherDescription | `ProductDescriptions` | — | [../12](../12_Descriptions.md) |
| Q-DESC-015 | Update other description | OtherDescription | `ProductDescriptions` | — | [../12](../12_Descriptions.md) |
| Q-DESC-020 | Find matching descriptions | ProductDescription, OtherDescription | `DescriptionsFindReplace` | — | [../13](../13_Find_Replace.md) |
| Q-DESC-021…025 | Find/Replace apply set (product + other) | ProductDescription, OtherDescription | `DescriptionsFindReplace` | 2nd-order injection | [../13](../13_Find_Replace.md) |
| Q-DESC-026 | Language-scoped find | ProductDescription | `DescriptionsFindReplace` | LanguageId map | [../13](../13_Find_Replace.md) |
| Q-DESC-027 | Preview affected rows | ProductDescription, OtherDescription | `DescriptionsFindReplace` | — | [../13](../13_Find_Replace.md) |
| Q-DESC-030 | Catalogue application-text description | CatalogueApplicationText | `ProductDescriptions` | negative CatalogueId | [../12](../12_Descriptions.md) |
| Q-DESC-040 | Increment description read | HandbookIncrementDesc | `ProductDescriptions` | — | [../12](../12_Descriptions.md) |
| Q-DESC-041 | Increment description write | HandbookIncrementDesc | `ProductDescriptions` | — | [../12](../12_Descriptions.md) |
| Q-DESC-050 | Description usage report | ProductDescription | `ProductDescriptions` | — | [../12](../12_Descriptions.md) |
| Q-DESC-051 | Orphan-description report | ProductDescription, OtherDescription | `ProductDescriptions` | — | [../12](../12_Descriptions.md) |

---

## Find / Replace

Covered in the **Descriptions** group above (`Q-DESC-020 … Q-DESC-027`),
source [../13_Find_Replace.md](../13_Find_Replace.md).

---

## Search

Source: [../14_Search.md](../14_Search.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-SRCH-001…034 | Faceted search over products / items / options / descriptions | Product, ProductRange, Item, ItemComponents, ItemOptionValues, OptionValue, [Option], AttributeValue, Attribute, ProductDescription, OtherDescription, CatalogueItems, CatalogueOptionValues, ProductGroupCodes | `Search` / `AddDataList` | dynamic `WHERE`, injection surface (P-SQL-01) | [../14](../14_Search.md) |
| Q-SRCH-EXP-A | Option-data report during search | *(proc `PDMOptionDataReport`)* | `Search` | — | [../14](../14_Search.md) |
| Q-SRCH-EXP-B | Option-data report w/ increment list | *(proc `PDMOptionDataReportWithIncList`)* | `Search` | — | [../14](../14_Search.md) |
| Q-SRCH-EXP-C | Option-data report w/ increment base | *(proc `PDMOptionDataReportWithIncBase`)* | `Search` | — | [../14](../14_Search.md) |
| Q-SRCH-EXP-D | Group-count / roll-up expansion | Item, ItemComponents | `Search` | — | [../14](../14_Search.md) |

> `Q-SRCH-001 … Q-SRCH-034` are enumerated individually in
> [../14_Search.md](../14_Search.md) §4; they share the same dynamic-`WHERE`
> construction and are indexed here as a block to avoid duplicating that section.

---

## Filtering

Source: [../15_Filtering.md](../15_Filtering.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-FILT-001…018 | Combo / grid filter population and predicate builders | Site, Currency, ProductCategory, CatalogueProductCategories, OptionValue, AttributeValue, Product_Code, PriceMatrix | filter dialogs / grid views | `'abcx'` blank sentinel (see Q-UTIL-011); DomCurrCode filters | [../15](../15_Filtering.md) |

> The 18 filter queries are listed individually in [../15_Filtering.md](../15_Filtering.md) §4.

---

## Ordering

Source: [../16_Ordering.md](../16_Ordering.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-ORD-001 | Load orderable catalogues | Catalogue, OtherDescription | `OrderCategories_Load` | see Q-CAT-002 | [../16](../16_Ordering.md) |
| Q-ORD-002 | Load orderable categories | CatalogueProductCategories, OtherDescription | `OrderCategories_Load` | DisplayOrder -1→9999 | [../16](../16_Ordering.md) |
| Q-ORD-003 | Persist catalogue display order | Catalogue | `OrderCategories.SubmitButton_Click` | see Q-CAT-003 | [../16](../16_Ordering.md) |
| Q-ORD-004 | Persist category display order | CatalogueProductCategories | `OrderCategories.SubmitButton_Click` | see Q-CATEG-003 | [../16](../16_Ordering.md) |

---

## Images

Source: [../17_Images.md](../17_Images.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-IMG-001 | Catalogue image lookup | Catalogue | `CADMaintenance` / image dialogs | — | [../17](../17_Images.md) |
| Q-IMG-002 | Category image lookup | CatalogueProductCategories | `CADMaintenance` | — | [../17](../17_Images.md) |
| Q-IMG-003 | Product image lookup | Product | image dialogs | — | [../17](../17_Images.md) |
| Q-IMG-004 | Item image lookup | Item | image dialogs | — | [../17](../17_Images.md) |
| Q-IMG-005 | Option-value image lookup | OptionValue | image dialogs | — | [../17](../17_Images.md) |
| Q-IMG-006 | Attribute-value image lookup | AttributeValue | image dialogs | — | [../17](../17_Images.md) |
| Q-IMG-007…013 | Image-path read/write set across the above entities | Catalogue, ProductCategory/CatalogueProductCategories, Product, Item, OptionValue, AttributeValue | image dialogs | ImageFile columns | [../17](../17_Images.md) |

---

## Pricing

Source: [../18_Pricing.md](../18_Pricing.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-PRICE-001…005 | Load price formulas / matrix / codes | PriceFormula, PriceMatrix, Product_Code, Currency | `PriceMaintenance` | BasePriceRef 1/2/3 | [../18](../18_Pricing.md) |
| Q-PRICE-020…023 | List-price resolution (item / product) | ItemOptionValues, Item, Product_Code *(fn `fnGetListPrice`, `fnGetListPriceByItem`)* | `PriceMaintenance` | — | [../18](../18_Pricing.md) |
| Q-PRICE-030…032 | Fabric-band price resolution | FabricBands, OptionValue *(fn `fnGetFabricBandOrderCodes`)* | `PriceMaintenance` | id 8/28 | [../18](../18_Pricing.md) |
| Q-PRICE-040…047 | Incremental-price read/write (slots 1/2/3) | ItemOptionValues, PriceMatrix, PriceFormula | `PriceMaintenance` / `CustomPricePerm` | BasePriceRef | [../18](../18_Pricing.md) |
| Q-PRICE-050…051 | Exchange-rate application | ExchangeRate, Currency | `PriceMaintenance` | excl. currency 'OGC' | [../18](../18_Pricing.md) |
| Q-PRICE-060 | Price-permutation build | *(proc `PricePermutation`)* | `CustomPricePerm` | — | [../18](../18_Pricing.md) |
| Q-PRICE-070…077 | Custom price-permutation edits | ItemOptionValues, PriceMatrix, OptionValue | `CustomPricePerm` | — | [../18](../18_Pricing.md) |
| Q-PRICE-090…094 | Push prices to pCon MDB | **tCOMd_Price, tCOMd_GlobalPrice, tCOMd_PriceList2** | `PriceMaintenance` (OleDb) | P-SQL-07 | [../18](../18_Pricing.md) |
| Q-PRICE-095…099 | Price audit + validation | PDMAudit.dbo.ItemPriceUpdates, PDMAudit.dbo.IncrementalPriceUpdates, PDMAudit.dbo.Transactions | `PriceMaintenance` | P-SQL-03 (audit) | [../18](../18_Pricing.md) |

> Individual `Q-PRICE-NNN` ids and full SQL are in [../18_Pricing.md](../18_Pricing.md) §4;
> grouped here by function to keep the index readable.

---

## Configuration (pCon / CAD)

Source: [../19_OAP_Export.md](../19_OAP_Export.md) (OAP), and the CAD/pCon
configuration queries documented across the CAD maintenance modules.

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-CFG-001…070 | CAD scheme / configuration read + write (SQL Server side) | CADSchemes, [Option], OptionValue, DependentOptionValues, ProductOptionValues, Item, ItemComponents | `CADMaintenance` and related dialogs | — | [../19](../19_OAP_Export.md) |
| Q-CFG-901 | Configuration validation / roll-up | Item, ItemComponents, OptionValue | `CADMaintenance` | — | [../19](../19_OAP_Export.md) |
| O-CFG-001…030 | pCon MDB configuration reads/writes | **tCOMd_Article, tCOMd_ArticleClass, tCOMd_Class, tCOMd_Property, tCOMd_PropValue, tCOMd_Package, tCOMd_Relation, tCOMd_RelObj, tCOMd_RelObjRel** | pCon export/import (OleDb) | P-SQL-07 | [../19](../19_OAP_Export.md) |

> The individual `Q-CFG-NNN` / `O-CFG-NNN` ids are enumerated in the CAD/OAP module
> docs; they share the pCon Jet-MDB access pattern (`P-SQL-07`). Where a specific
> `tCOMd_*` table statement was not transcribable from source it is marked **UNKNOWN**
> in [../26_Data_Model.md](../26_Data_Model.md) §2.10.

---

## OAP / ODB (pCon exporters)

Source: [../19_OAP_Export.md](../19_OAP_Export.md), [../20_ODB_Export.md](../20_ODB_Export.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| O-OAS-001 | Open OAP (sel_oas) MDB connection | *(connection only — table statements UNKNOWN)* | `OAPExport` (OleDb) | P-SQL-07 | [../19](../19_OAP_Export.md) |
| O-OAS-002 | OAP article/selection read | **sel_oas internal tables (UNKNOWN)** | `OAPExport` | — | [../19](../19_OAP_Export.md) |
| O-ODB-001 | Open ODB (geometry) MDB connection | *(connection only)* | `ODBExport` (OleDb) | P-SQL-07 | [../20](../20_ODB_Export.md) |
| O-ODB-002 | ODB geometry object read | **tGEOd_Object, tGEOd_Node2D, tGEOd_Node3D** | `ODBExport` | — | [../20](../20_ODB_Export.md) |
| O-ODB-003 | ODB package / layer read | **tGEOd_Package, tGEOd_Layer** | `ODBExport` | — | [../20](../20_ODB_Export.md) |

---

## OCD (pCon catalogue export)

Source: [../21_OCD_Export.md](../21_OCD_Export.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-OCD-001 | Catalogue lead-time / header | Catalogue, OtherDescription | `OCDExport` | — | [../21](../21_OCD_Export.md) |
| Q-OCD-002…006 | Product-code list + resolution | Product_Code, Site, PriceMatrix | `OCDExport` | BasePriceRef | [../21](../21_OCD_Export.md) |
| Q-OCD-007…010 | Article / item enumeration | Item, ItemComponents, Product, CatalogueItems | `OCDExport` | — | [../21](../21_OCD_Export.md) |
| Q-OCD-011…013 | Option-data report EXEC | *(proc `PDMOptionDataReport`, `…WithIncList`, `…WithIncBase`)* | `OCDExport` | — | [../21](../21_OCD_Export.md) |
| Q-OCD-014…018 | Attribute / option value export | AttributeValue, OptionValue, CatalogueAttributeValues, CatalogueOptionValues | `OCDExport` | — | [../21](../21_OCD_Export.md) |
| Q-OCD-019…020 | Incremental price export | ItemOptionValues, PriceMatrix | `OCDExport` | BasePriceRef | [../21](../21_OCD_Export.md) |

> Each `Q-OCD-NNN` id is listed individually in [../21_OCD_Export.md](../21_OCD_Export.md) §4.

---

## Export / Import

Source: [../22_Export.md](../22_Export.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-EXP-001 | Financial export — product-code sheet | Product_Code, Site | `MainMenu.cs:4201` | — | [../22](../22_Export.md) |
| Q-EXP-002 | Financial export — price-matrix sheet | PriceMatrix, Product_Code | `MainMenu.cs:4213` | — | [../22](../22_Export.md) |
| Q-EXP-003 | Financial export — price-formula sheet | PriceFormula, Site | `MainMenu.cs:4225` | — | [../22](../22_Export.md) |
| Q-EXP-004 | Price-band export | OptionValue, FabricBands | `MainMenu.cs:4269` | status < 2 (URL/ACT) | [../22](../22_Export.md) |
| Q-EXP-005 | SL8 export — price-formula helper | PriceFormula, PriceMatrix, Site | `ExportThread.cs:1002` | NOLOCK | [../22](../22_Export.md) |
| Q-EXP-006 | SL8 export — super-product feature count | ItemComponents, Item | `ExportThread.cs:723` | — | [../22](../22_Export.md) |
| Q-EXP-007 | CSI export — catalogue option-value scope | CatalogueOptionValues, OptionValue | `SytelineCSIExport.cs:642` | NOLOCK | [../22](../22_Export.md) |
| Q-EXP-008 | CSI export — item / description root | Item, Product, ProductDescription | `SytelineCSIExport.cs:1150` | — | [../22](../22_Export.md) |
| Q-EXP-009 | PBOM material master pull (SyteLine LIVE) | item, item_mst | `BOMExport.cs:455` | site-20 special-case | [../22](../22_Export.md) |
| Q-EXP-010 | PBOM material / criteria join | Item, MaterialProductId, MaterialData, Material, MaterialCriteria | `BOMExport.cs:1258` | — | [../22](../22_Export.md) |
| Q-EXP-011 | PBOM sub-job (recursive BOM) | MaterialSubJob, Material | `BOMExport.cs:1121` | — | [../22](../22_Export.md) |
| Q-EXP-012 | OFDA export — catalogue header | Catalogue, OtherDescription | `OFDAExport.cs:2748` | NOLOCK | [../22](../22_Export.md) |
| Q-EXP-013 | OFDA export — price resolution | ItemOptionValues, Product_Code | `OFDAExport.cs:1050` | BasePriceRef 1/2/3 | [../22](../22_Export.md) |
| Q-EXP-014 | OFDA export — exchange-rate lookup | ExchangeRate | `OFDAExport.cs:1528` | NOLOCK | [../22](../22_Export.md) |
| Q-EXP-015 | OFDA / BOM central option report | *(proc `PDMOptionDataReport`)* | `OFDAExport.cs:4425`, `BOMExport.cs:832` | body UNKNOWN | [../22](../22_Export.md) |
| Q-EXP-016 | SIF export — category tree | Catalogue, CatalogueProductCategories, OtherDescription | `SIFExportThread.cs:223` | DisplayOrder -1→9999 | [../22](../22_Export.md) |
| Q-EXP-017 | SIF import — product-range order-code update | ProductRange | `SIFImport.cs:9114` | — | [../22](../22_Export.md) |
| Q-EXP-018 | SIF import — item-option increment upsert | ItemOptionValues | `SIFImport.cs:9379` | BasePriceRef | [../22](../22_Export.md) |
| Q-EXP-019 | Scheduled-export insert | ExportSchedule | `ScheduleExport.cs:899` | — | [../22](../22_Export.md) |
| Q-EXP-020 | Scheduled-export catalogue list (read-only aware) | PDMUserCatalogues, Catalogue | `ScheduleExport.cs:643` | inverted ReadOnly | [../22](../22_Export.md) |
| Q-EXP-021 | Static-data XML — exchange rates | ExchangeRate, Currency, Site | `SDXmlExport.cs:356` | — | [../22](../22_Export.md) |
| Q-EXP-022 | Static-data XML — product codes | Product_Code, Site | `SDXmlExport.cs:398` | Rounding commented out | [../22](../22_Export.md) |
| Q-EXP-023 | DPSDB publication — DB file swap | DPSDB (`sp_detach_db`/`sp_attach_db`) | `ExportDPSDBThread.cs:92+` | see procs table | [../22](../22_Export.md) |

---

## Generation

Source: [../23_Generation.md](../23_Generation.md)

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-GEN-001 | Load accessible catalogues | PDMUserCatalogues, Catalogue | `HandbookDesigner.cs:2242` | BR-GEN-002 (DealerCatalogues when PDMPublished) | [../23](../23_Generation.md) |
| Q-GEN-002 | Sites list (excl. 20) | Site | `HandbookDesigner.cs:2273` | site-20 special-case | [../23](../23_Generation.md) |
| Q-GEN-003 | Products flagged for publication | HandbookProducts | `HandbookDesigner.cs:2465` | PublishCategory=1 | [../23](../23_Generation.md) |
| Q-GEN-004 | Items in publishable groups | Item, CatalogueItems, HandbookProducts | `HandbookDesigner.cs:2489` | BR-GEN-008 (memory guard) | [../23](../23_Generation.md) |
| Q-GEN-005 | Group list for a category | HandbookProducts | `HandbookDesigner.cs:2820` | — | [../23](../23_Generation.md) |
| Q-GEN-006 | Create a new handbook | Handbook | `HandbookDesigner.cs:2739` | — | [../23](../23_Generation.md) |
| Q-GEN-007 | Toggle option visibility (OptNum sign flip) | HandbookOptions | `HandbookDesigner.cs:3214` | negative OptNum = hidden | [../23](../23_Generation.md) |
| Q-GEN-008 | Increment-data preview / generation proc | *(proc `PDMPriceListReportForProductGroup`)* | `HandbookDesigner.cs:3306` | body UNKNOWN; CommandTimeout=300 | [../23](../23_Generation.md) |
| Q-GEN-009 | Exclusion candidate list (dynamic Attribute/Option) | Attribute, AttributeValue, [Option], OptionValue | `HBExclusions.cs:275` | — | [../23](../23_Generation.md) |
| Q-GEN-010 | Add an exclusion | HandbookAttributeExclusions / HandbookOptionExclusions | `HBExclusions.cs:340` | — | [../23](../23_Generation.md) |
| Q-GEN-011 | Remove an exclusion | HandbookAttributeExclusions / HandbookOptionExclusions | `HBExclusions.cs:379` | — | [../23](../23_Generation.md) |

> Handbook group/product/attribute/option add-remove-rename-import-reorder handlers
> issue further `INSERT`/`UPDATE`/`DELETE` against `HandbookProducts` /
> `HandbookAttributes` / `HandbookOptions` with `ProductGroupId` shift arithmetic
> (BR-GEN-005/006); these follow the Q-GEN-006/007 pattern and are not separately
> transcribed — see coverage limits in [../23_Generation.md](../23_Generation.md) §10.

---

## Utilities

Source: [../24_Utilities.md](../24_Utilities.md) — all in `StaticDataMaintenance.cs`
unless noted. Currency/Site/ExchangeRate/Language/Product-Code/Price-Formula/Price-Matrix
CRUD uses **parameterised** `SqlCommand`s (`@Param` + `@Original_*` optimistic concurrency);
ad-hoc filter/helper queries are string-concatenated.

| Query ID | Purpose | Tables | Called by | Related BRs | Source |
|---|---|---|---|---|---|
| Q-UTIL-001 | Load currency list | Currency | `:1802` | — | [../24](../24_Utilities.md) |
| Q-UTIL-002 | Insert currency + identity refresh | Currency | `:1804` | @@IDENTITY | [../24](../24_Utilities.md) |
| Q-UTIL-003 | Update currency (optimistic concurrency) | Currency | `:1811` | @Original_* | [../24](../24_Utilities.md) |
| Q-UTIL-004 | Load sites (excl. 20) | Site | `:1833` | site-20 special-case | [../24](../24_Utilities.md) |
| Q-UTIL-005 | Insert site + identity refresh | Site | `:1835` | @@IDENTITY | [../24](../24_Utilities.md) |
| Q-UTIL-006 | Update site (concurrency) | Site | `:1840` | @Original_* | [../24](../24_Utilities.md) |
| Q-UTIL-007 | Exchange-rate flat list | ExchangeRate | `:1858` | — | [../24](../24_Utilities.md) |
| Q-UTIL-008 | Latest exchange rate per pair | ExchangeRate | `:1860` | MAX(EffectiveDate) | [../24](../24_Utilities.md) |
| Q-UTIL-009 | Insert exchange rate + identity | ExchangeRate | `:1861` | @@IDENTITY | [../24](../24_Utilities.md) |
| Q-UTIL-010 | Update exchange rate (concurrency) | ExchangeRate | `:1869` | @Original_* | [../24](../24_Utilities.md) |
| Q-UTIL-011 | Blank-grid sentinel (`'abcx'`) | ExchangeRate | `:2813`/`:2851` | empty-result trick | [../24](../24_Utilities.md) |
| Q-UTIL-012 | Effective BuyRate for factor recompute | ExchangeRate | `getExRate:3374` | string-concat | [../24](../24_Utilities.md) |
| Q-UTIL-013 | Load languages | Language | `:1893` | LanguageId map | [../24](../24_Utilities.md) |
| Q-UTIL-014 | Insert language + identity | Language | `:1895` | @@IDENTITY | [../24](../24_Utilities.md) |
| Q-UTIL-015 | Update language (concurrency) | Language | `:1899` | @Original_* | [../24](../24_Utilities.md) |
| Q-UTIL-016 | Load product codes (joined to site) | Product_Code, Site | `:1915` | Rounding commented out | [../24](../24_Utilities.md) |
| Q-UTIL-017 | Insert / update product code (+ max-id, existence) | Product_Code | `:1917`/`:1930`/`:3635`/`:3646` | LTRIM/RTRIM normalise | [../24](../24_Utilities.md) |
| Q-UTIL-018 | Load price formulas (blank/filter variants) | PriceFormula | `:1962`/`:3122`/`:3161` | `'abcx'` sentinel | [../24](../24_Utilities.md) |
| Q-UTIL-019 | Insert / update price formula | PriceFormula | `:1964`/`:1972`/`:2027`/`:2037` | @@IDENTITY, @Original_* | [../24](../24_Utilities.md) |
| Q-UTIL-020 | Audit + insert-new/delete-old on formula change | PriceFormula, PDMAudit.dbo.Transactions, PDMAudit.dbo.PFUpdates | `updateButton_Click:3743` | P-SQL-03 (audit); history-preserving | [../24](../24_Utilities.md) |
| Q-UTIL-021 | Load price matrix (blank/filter variants) | PriceMatrix | `:1996`/`:3294`/`:3298` | — | [../24](../24_Utilities.md) |
| Q-UTIL-022 | Insert / update / upsert price-matrix row | PriceMatrix | `:1998`/`:2005`/`:4722` | — | [../24](../24_Utilities.md) |
| Q-UTIL-023 | DomCurrCode filter combo | Site | `:2123`/`:3196` | — | [../24](../24_Utilities.md) |
| Q-UTIL-024 | Currency / site / cust-price-code combos | Currency, Site, PriceMatrix | `:2490`/`:2562`/`:2580` | — | [../24](../24_Utilities.md) |
| Q-UTIL-025 | Referential validation before matrix save | Currency, Product_Code, PriceFormula | `:4558`/`:4588`/`:4618` | — | [../24](../24_Utilities.md) |
| Q-UTIL-026 | Product-group-code lookups | ProductGroupCodes, OtherDescription | `:3515`/`:4257` | LanguageId=1; ParentGroupCodeId indent | [../24](../24_Utilities.md) |

> External-process publication utilities (`xp_cmdshell`, `dtsrun`, the
> `Export_PDM2004_to_DPSDB` DTS package) are catalogued in the
> [Stored Procedures & Functions](#stored-procedures--functions) section — their
> internals live outside the source tree.

---

## Stored Procedures & Functions

Reproduced from [../25_Common_SQL.md](../25_Common_SQL.md) §3. **No proc/function body is
present in the legacy source tree** — every entry below is invoked by name only, so all
bodies are **UNKNOWN** (except the two OS/built-in entries marked *N/A*).

| Object | Type | Referenced from (modules) | Body available? |
|---|---|---|---|
| `PDMOptionDataReport` | stored proc | 05, 08, 09, 10, 14, 18, 21, 22 | **UNKNOWN** |
| `PDMOptionDataReportWithIncList` | stored proc | 09, 10, 18, 22 | **UNKNOWN** |
| `PDMOptionDataReportWithIncBase` | stored proc | 09, 18, 22 | **UNKNOWN** |
| `PricePermutation` | stored proc | 18 | **UNKNOWN** |
| `PDMPriceListReportForProductGroup` | stored proc | 23 | **UNKNOWN** |
| `fnGetListPrice` | scalar function | 05, 18, 21, 22 | **UNKNOWN** |
| `fnGetListPriceByItem` | scalar function | 05, 18, 21, 22 | **UNKNOWN** |
| `fnGetFabricBandOrderCodes` | scalar function | 18 | **UNKNOWN** |
| `fnGetSPComponentCount` | scalar function | 05 | **UNKNOWN** |
| `GetProductOptionCount` | stored proc (OUT param) | 06, 21 | **UNKNOWN** |
| `xp_cmdshell` | system XP | 22, 24 | *N/A (SQL Server built-in)* |
| `dtsrun` (via `xp_cmdshell`) | external exe | 24 | *N/A (OS tool)* |
| `Export_PDM2004_to_DPSDB` | DTS package | 24 | **UNKNOWN** (DTS internals) |
| DPSDB detach/copy/reattach | `sp_detach_db`/`sp_attach_db` | 22 | *N/A (SQL Server built-in)* |

**UNKNOWN-body stored procedures / functions: 10** (the ten application objects above
— `PDMOptionDataReport`, `…WithIncList`, `…WithIncBase`, `PricePermutation`,
`PDMPriceListReportForProductGroup`, `fnGetListPrice`, `fnGetListPriceByItem`,
`fnGetFabricBandOrderCodes`, `fnGetSPComponentCount`, `GetProductOptionCount`).
`xp_cmdshell`, `dtsrun`, and the `sp_*_db` calls are built-in/OS and not counted as
UNKNOWN application objects; the `Export_PDM2004_to_DPSDB` DTS package is a separate
artefact whose internals are likewise absent.

---

## See also

- [../25_Common_SQL.md](../25_Common_SQL.md) — cross-cutting SQL patterns (`P-SQL-01…11`) & risk summary
- [../26_Data_Model.md](../26_Data_Model.md) — table catalogue & ER diagram (source of truth)
- [Table_Index.md](Table_Index.md) — table-centric view (table → queries → modules)
- [Business_Rules_Index.md](Business_Rules_Index.md) — business-rule catalogue (`BR-*`)
- [Call_Hierarchy.md](Call_Hierarchy.md), [Dependency_Map.md](Dependency_Map.md)
