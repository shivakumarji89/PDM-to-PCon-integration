# Table Index

Table-centric cross-reference of every table cited in the legacy PDM handbook: one row
per **distinct table**, mapping it to the queries that touch it, the classes/forms that
use it, and the module docs that document it. This is a **navigation layer only**.

> **Source of truth for the data model** — key annotations, the ER diagram, and the full
> status/flag legend — is [../26_Data_Model.md](../26_Data_Model.md). Keys marked
> **(inferred)** are not proven by a `PRIMARY KEY`/`FOREIGN KEY` DDL in the source; they
> are deduced from join/usage patterns. `UNKNOWN` = not determinable from the handbook.
> Query IDs resolve in [SQL_Index.md](SQL_Index.md).

**Store legend**
- **SQL Server** — PDMLive / PDMPublished working database.
- **PDMAudit** — separate SQL Server audit DB (three-part `PDMAudit.dbo.*` names; audit
  disabled on eoscloud servers).
- **SyteLine LIVE** — external ERP database read for PBOM/cost export (not a PDM table).
- **pCon MDB** — per-workspace 32-bit Jet/Access files (`pcr_data_*.mdb`, `tCOMd_*` /
  `tGEOd_*`), reached via `Microsoft.Jet.OLEDB.4.0` (`O-*` queries).

---

## 1. SQL Server — Security

| Table | Purpose | PK | FK | Used by classes | Used by SQL | Modules |
|---|---|---|---|---|---|---|
| PDMUserPrivileges | Per-user capability flags | UserId | — | `AuthenticateUser`, `UserAdmin` | Q-AUTH-001, Q-PERM-001…003, Q-PERM-006 | [01](../01_Authentication.md), [02](../02_User_Permissions.md) |
| PDMUserCatalogues | User↔catalogue grants (**ReadOnly inverted**) | UserId + CatalogueId | UserId→PDMUserPrivileges, CatalogueId→Catalogue | `UserAdmin`, `ProductDescriptions`, `CADMaintenance`, `ScheduleExport`, `HandbookDesigner` | Q-PERM-004, Q-CAT-001/006, Q-PROD-002/002b, Q-EXP-020, Q-GEN-001 | [02](../02_User_Permissions.md), [03](../03_Catalogues.md), [23](../23_Generation.md) |
| SL7UserViews | User↔SyteLine view grants **(inferred)** | UserId + ViewName (inferred) | UserId→PDMUserPrivileges (inferred) | `UserAdmin` | Q-PERM-005 | [02](../02_User_Permissions.md) |
| sysobjects | System catalog (view enumeration) | *(system)* | — | `UserAdmin` | Q-PERM-006 | [02](../02_User_Permissions.md) |
| sysusers | System catalog (user enumeration) | *(system)* | — | `UserAdmin` | Q-PERM-006 | [02](../02_User_Permissions.md) |

---

## 2. SQL Server — Catalogue & Category

| Table | Purpose | PK | FK | Used by classes | Used by SQL | Modules |
|---|---|---|---|---|---|---|
| Catalogue | Catalogue master (negative id = pricebook) | CatalogueId | — | `ProductDescriptions`, `CADMaintenance`, `OrderCategories`, `AddDataList`, exporters, `HandbookDesigner` | Q-CAT-001…009, Q-CATEG-006, Q-EXP-012/016/020, Q-GEN-001, Q-OCD-001, Q-IMG-001 | [03](../03_Catalogues.md), [17](../17_Images.md), [22](../22_Export.md), [23](../23_Generation.md) |
| CatalogueProductCategories (CPC) | Catalogue↔category link + display order | CatalogueId + ProductCategoryId | CatalogueId→Catalogue, ProductCategoryId→ProductCategory | `CADMaintenance`, `OrderCategories`, `SuperProductMaintenance`, exporters | Q-CATEG-001…005, Q-PROD-005/005b, Q-ORD-002/004, Q-EXP-016, Q-IMG-002 | [04](../04_Product_Categories.md), [16](../16_Ordering.md) |
| CatalogueItems | Released item↔catalogue membership | CatalogueId + ItemId (inferred) | CatalogueId→Catalogue, ItemId→Item | `SuperProductMaintenance`, `HandbookDesigner`, exporters | Q-PROD-007/026/036…038/042, Q-GEN-004, Q-OCD-007…010 | [05](../05_Products.md), [21](../21_OCD_Export.md), [23](../23_Generation.md) |
| CatalogueItemsUnreleased | Unreleased item↔catalogue membership | CatalogueId + ItemId (inferred) | CatalogueId→Catalogue, ItemId→Item | `SuperProductMaintenance` | Q-PROD-007/026/036…038/042 | [05](../05_Products.md) |
| CatalogueOptionValues | Released option-value scope for a catalogue | CatalogueId + OptionValueId (inferred) | CatalogueId→Catalogue, OptionValueId→OptionValue | `OptionMaintenance`, `OptionValueMaintenance`, exporters | Q-OPT-008, Q-OVAL-007, Q-EXP-007, Q-OCD-014…018 | [09](../09_Options.md), [10](../10_Option_Values.md), [21](../21_OCD_Export.md) |
| CatalogueAttributeValues | Released attribute-value scope | CatalogueId + AttributeValueId (inferred) | CatalogueId→Catalogue, AttributeValueId→AttributeValue | `AttributeMaintenance`, `SuperProductMaintenance` | Q-ATTR-012, Q-PROD-007/009 | [07](../07_Attributes.md), [05](../05_Products.md) |
| CatalogueTranslations | Per-catalogue attribute/option/value text | CatalogueId + key (inferred) | CatalogueId→Catalogue | `Translations`, `AttributeMaintenance`, `OptionMaintenance` | Q-TRAN-002…007/012/015/016, Q-ATTR-017, Q-OPT-013, Q-OVAL-014 | [11](../11_Translations.md) |
| CatalogueApplicationText | Pricebook application text (negative CatalogueId) | CatalogueId + key (inferred) | — | `Translations`, `ProductDescriptions` | Q-TRAN-010, Q-DESC-030 | [11](../11_Translations.md), [12](../12_Descriptions.md) |
| CatalogueUIGroups | UI grouping for catalogue display | UNKNOWN | CatalogueId→Catalogue (inferred) | `CADMaintenance` | *(read-only; no specific Q id transcribed)* | [03](../03_Catalogues.md) |
| CatalogueProductRanges | Catalogue↔product-range link | CatalogueId + ProductRangeId (inferred) | CatalogueId→Catalogue, ProductRangeId→ProductRange | `CADMaintenance` | *(read-only; no specific Q id transcribed)* | [03](../03_Catalogues.md) |

---

## 3. SQL Server — Product & Item

| Table | Purpose | PK | FK | Used by classes | Used by SQL | Modules |
|---|---|---|---|---|---|---|
| Product | Product master | ProductId | — | `SuperProductMaintenance`, `Search`, exporters, `HandbookDesigner` | Q-PROD-007/009/013/024…027/030…038/046, Q-SRCH-*, Q-EXP-008, Q-IMG-003 | [05](../05_Products.md), [14](../14_Search.md), [22](../22_Export.md) |
| ProductRange | Product-range master | ProductRangeId | — | `SuperProductMaintenance`, `SIFImport` | Q-PROD-007/009/026/042, Q-EXP-017 | [05](../05_Products.md), [22](../22_Export.md) |
| ProductCategory | Category master | ProductCategoryId | — | `CADMaintenance`, `SuperProductMaintenance`, `OrderCategories` | Q-CATEG-001/005, Q-PROD-005/005b | [04](../04_Product_Categories.md), [05](../05_Products.md) |
| Item | Item master (`ProductCodeIdOverride`) | ItemId | ProductId→Product | `SuperProductMaintenance`, `Search`, exporters, `HandbookDesigner` | Q-PROD-001/007/009/013/018/024…040/042…046, Q-SRCH-*, Q-EXP-006/008/010, Q-GEN-004, Q-OCD-007…010 | [05](../05_Products.md), [14](../14_Search.md), [21](../21_OCD_Export.md), [22](../22_Export.md) |
| ItemComponents | Super-product BOM (self-ref; `FeaturePositionString`) | ItemId + SubItemId | ItemId→Item, SubItemId→Item | `SuperProductMaintenance`, `Search`, exporters | Q-PROD-001/007/009/013…016/019…023/030…040, Q-EXP-006, Q-SRCH-EXP-D | [05](../05_Products.md), [22](../22_Export.md) |
| ItemOptionValues | Per-item option surcharges (IncrementalPrice1/2/3) | ItemId + OptionValueId | ItemId→Item, OptionValueId→OptionValue | `OptionValueMaintenance`, `PriceMaintenance`, exporters, `SIFImport` | Q-OVAL-009, Q-PRICE-020…023/040…047/070…077, Q-EXP-013/018, Q-OCD-019/020, Q-PROD-025 | [10](../10_Option_Values.md), [18](../18_Pricing.md), [22](../22_Export.md) |
| Product_Code | Product-code / pricing anchor (BasePriceRef 1/2/3) | ProductCodeId (caller-supplied) | SiteId→Site | `ProductCodeEntry`, `StaticDataMaintenance`, `SuperProductMaintenance`, exporters | Q-ART-002, Q-UTIL-016/017/025, Q-PROD-011…013/024/025, Q-EXP-001/013/022, Q-OCD-002…006 | [06](../06_Product_Codes.md), [24](../24_Utilities.md), [22](../22_Export.md) |

---

## 4. SQL Server — Option & Attribute

| Table | Purpose | PK | FK | Used by classes | Used by SQL | Modules |
|---|---|---|---|---|---|---|
| [Option] | Option master (reserved word — bracketed) | OptionId | — | `OptionMaintenance`, `SuperProductMaintenance`, `HBExclusions` | Q-OPT-001…004/011/012, Q-PROD-006/022, Q-GEN-009 | [09](../09_Options.md), [05](../05_Products.md), [23](../23_Generation.md) |
| OptionValue | Option-value master (Status 0/1/2/3) | OptionValueId | OptionId→[Option] | `OptionValueMaintenance`, exporters, `PriceMaintenance` | Q-OVAL-001…018, Q-OPT-005, Q-EXP-004/007, Q-OCD-014…018, Q-PRICE-030…032, Q-IMG-005 | [10](../10_Option_Values.md), [18](../18_Pricing.md), [22](../22_Export.md) |
| DependentOptionValues | Option-value dependency graph | OptionValueId + DependsOnId (inferred) | →OptionValue | `OptionMaintenance`, `OptionValueMaintenance`, `PropertyValueMaintenance` | Q-OPT-007, Q-OVAL-006, Q-PVAL-006 | [09](../09_Options.md), [10](../10_Option_Values.md), [08](../08_Property_Values.md) |
| ProductOptionValues | Product↔option-value scope **(inferred)** | ProductId + OptionValueId (inferred) | →Product, →OptionValue | `OptionMaintenance`, `PropertyValueMaintenance` | Q-OPT-006, Q-OVAL-008, Q-PVAL-001/003…005 | [09](../09_Options.md), [08](../08_Property_Values.md) |
| Attribute | Attribute master | AttributeId | — | `AttributeMaintenance`, `HBExclusions` | Q-ATTR-001/003…005/014/015/018/019, Q-GEN-009 | [07](../07_Attributes.md), [23](../23_Generation.md) |
| AttributeValue | Attribute-value master | AttributeValueId | AttributeId→Attribute | `AttributeMaintenance`, `Translations`, exporters | Q-ATTR-002/006…009/016/018/019, Q-TRAN-006, Q-OCD-014…018, Q-IMG-006 | [07](../07_Attributes.md), [21](../21_OCD_Export.md) |
| BaseAttributeValues | Per-item base attribute values | ItemId + AttributeValueId | ItemId→Item, AttributeValueId→AttributeValue | `AttributeMaintenance`, `SuperProductMaintenance` | Q-ATTR-009/020/021, Q-PROD-007/009 | [07](../07_Attributes.md), [05](../05_Products.md) |
| ProductAttributeValues | Product↔attribute-value scope **(inferred)** | ProductId + AttributeValueId (inferred) | →Product, →AttributeValue | `AttributeMaintenance` | Q-ATTR-010 | [07](../07_Attributes.md) |
| DependentAttributeValues | Attribute-value dependency graph **(inferred)** | AttributeValueId + DependsOnId (inferred) | →AttributeValue | `AttributeMaintenance` | Q-ATTR-011 | [07](../07_Attributes.md) |
| AttributeGroupCodes | Attribute grouping codes | UNKNOWN | AttributeId→Attribute (inferred) | `AttributeMaintenance` | Q-ATTR-013 | [07](../07_Attributes.md) |
| OptionGroupCodes | Option grouping codes | UNKNOWN | OptionId→[Option] (inferred) | `OptionMaintenance`, `OptionValueMaintenance` | Q-OPT-009, Q-OVAL-016 | [09](../09_Options.md), [10](../10_Option_Values.md) |
| CADSchemes | CAD scheme ↔ option/value links | UNKNOWN | →[Option]/OptionValue (inferred) | `OptionMaintenance`, `OptionValueMaintenance`, `CADMaintenance` | Q-OPT-014, Q-OVAL-017, Q-CFG-001…070 | [09](../09_Options.md), [19](../19_OAP_Export.md) |

---

## 5. SQL Server — Description & Translation

| Table | Purpose | PK | FK | Used by classes | Used by SQL | Modules |
|---|---|---|---|---|---|---|
| ProductDescription | Language-keyed product descriptions | DescriptionId + LanguageId | LanguageId→Language | `ProductDescriptions`, `DescriptionsFindReplace`, `Translations`, exporters | Q-DESC-001…013/026/027/050/051, Q-TRAN-008/011, Q-EXP-008 | [12](../12_Descriptions.md), [13](../13_Find_Replace.md), [11](../11_Translations.md) |
| OtherDescription | Generic description (RelatedTable tag) | DescriptionId + LanguageId | LanguageId→Language | `ProductDescriptions`, `CADMaintenance`, `OrderCategories`, exporters | Q-DESC-002…010/014/015/020…027/051, Q-CATEG-001/002, Q-EXP-012/016, Q-UTIL-026, Q-OCD-001 | [12](../12_Descriptions.md), [04](../04_Product_Categories.md), [22](../22_Export.md) |
| Language | Language reference (LanguageId map) | Language_ID | — | `StaticDataMaintenance`, `Translations`, `ProductDescriptions` | Q-UTIL-013…015, Q-TRAN-001/016, Q-DESC-001 | [24](../24_Utilities.md), [11](../11_Translations.md) |
| DPSText | DPS publication text | UNKNOWN | — | `ProductDescriptions` | Q-DESC-010 | [12](../12_Descriptions.md) |

---

## 6. SQL Server — Pricing

| Table | Purpose | PK | FK | Used by classes | Used by SQL | Modules |
|---|---|---|---|---|---|---|
| PriceFormula | Uplift formulas (FirstPrice, EffectiveDate) | PriceFormulaId | SiteId→Site | `StaticDataMaintenance`, `PriceMaintenance`, exporters | Q-UTIL-018…020, Q-PRICE-001…005/040…047, Q-EXP-003/005 | [24](../24_Utilities.md), [18](../18_Pricing.md), [22](../22_Export.md) |
| PriceMatrix | Cust×item price → formula matrix **(inferred keys)** | PriceMatrixId | ItemPriceCode→Product_Code.PriceCode (inferred) | `StaticDataMaintenance`, `PriceMaintenance`, exporters | Q-UTIL-021/022/025, Q-PRICE-001…005/040…047/070…077, Q-EXP-002, Q-OCD-002…006 | [24](../24_Utilities.md), [18](../18_Pricing.md) |
| Currency | Currency reference (excl. 'OGC') | Currency_ID | — | `StaticDataMaintenance`, `PriceMaintenance`, exporters | Q-UTIL-001…003/024/025, Q-PRICE-050/051, Q-PROD-004/025, Q-EXP-021 | [24](../24_Utilities.md), [18](../18_Pricing.md) |
| ExchangeRate | Effective-dated FX rates **(inferred keys)** | ExchangeRateId | CurrCode→Currency, DomCurrCode→Site (inferred) | `StaticDataMaintenance`, exporters, `PriceMaintenance` | Q-UTIL-007…012, Q-PRICE-050/051, Q-EXP-014/021 | [24](../24_Utilities.md), [18](../18_Pricing.md), [22](../22_Export.md) |
| FabricBands | Option-value → price-band (Application = site) | UNKNOWN | OptionValueId→OptionValue | `PriceMaintenance`, `OptionValueMaintenance`, exporters | Q-OVAL-010, Q-PRICE-030…032, Q-EXP-004 | [18](../18_Pricing.md), [10](../10_Option_Values.md), [22](../22_Export.md) |

---

## 7. SQL Server — Static / Reference

| Table | Purpose | PK | FK | Used by classes | Used by SQL | Modules |
|---|---|---|---|---|---|---|
| Site | Site reference (site 20 excluded/special) | SiteId | — | `StaticDataMaintenance`, `SuperProductMaintenance`, exporters, `HandbookDesigner` | Q-UTIL-004…006/023/024, Q-ART-001, Q-PROD-003, Q-GEN-002, Q-EXP-001/003/005/009/021/022, Q-OCD-002…006 | [24](../24_Utilities.md), [06](../06_Product_Codes.md), [22](../22_Export.md) |
| FreightCategory | Freight categorisation | UNKNOWN | — | static-data screens | *(reference; no specific Q id transcribed)* | [24](../24_Utilities.md) |
| CommodityCode | Commodity codes | UNKNOWN | — | static-data screens | *(reference; no specific Q id transcribed)* | [24](../24_Utilities.md) |
| Country | Country reference | UNKNOWN | — | static-data / CPC screens | *(reference; no specific Q id transcribed)* | [24](../24_Utilities.md) |
| WebEOSItemRestrictions | Web/EOS item restriction flags | UNKNOWN | ItemId→Item (inferred) | export/publication | *(reference; no specific Q id transcribed)* | [22](../22_Export.md) |
| CPCDeliveryOffsets | Per-CPC delivery offsets | UNKNOWN | →CPC (inferred) | static-data screens | *(reference; no specific Q id transcribed)* | [24](../24_Utilities.md) |
| CPCSourceCountries | Per-CPC source countries | UNKNOWN | →CPC, →Country (inferred) | static-data screens | *(reference; no specific Q id transcribed)* | [24](../24_Utilities.md) |
| ExportSchedule | Queued scheduled exports | UNKNOWN | ProductId→Product, CatalogueId→Catalogue (inferred) | `ScheduleExport` | Q-EXP-019 | [22](../22_Export.md) |
| ProductGroupCodes | Product-group-code hierarchy | UNKNOWN | ParentGroupCodeId→self, DescriptionId→OtherDescription (inferred) | `StaticDataMaintenance`, `Search` | Q-UTIL-026, Q-SRCH-* | [24](../24_Utilities.md), [14](../14_Search.md) |

---

## 8. SQL Server — Handbook / Publication

| Table | Purpose | PK | FK | Used by classes | Used by SQL | Modules |
|---|---|---|---|---|---|---|
| Handbook | Handbook master | UNKNOWN (HandbookId) | CatalogueId→Catalogue (inferred) | `HandbookDesigner` | Q-GEN-006 | [23](../23_Generation.md) |
| HandbookProducts | Products/groups in a handbook (PublishCategory) | HandbookId + ProductId + ProductGroupId (inferred) | HandbookId→Handbook, ProductId→Product | `HandbookDesigner` | Q-GEN-003…005 | [23](../23_Generation.md) |
| HandbookGroups | Handbook group definitions | UNKNOWN | HandbookId→Handbook (inferred) | `HandbookDesigner` | *(via group handlers, BR-GEN-005/006)* | [23](../23_Generation.md) |
| HandbookAttributes | Handbook attribute selection | UNKNOWN | HandbookId→Handbook (inferred) | `HandbookDesigner` | *(via attribute handlers)* | [23](../23_Generation.md) |
| HandbookOptions | Handbook option selection (negative OptNum = hidden) | UNKNOWN | HandbookId→Handbook (inferred) | `HandbookDesigner` | Q-GEN-007 | [23](../23_Generation.md) |
| HandbookAttributeExclusions | Excluded attribute-values per group | HandbookId + ProductGroupId + AttributeValueId | →Handbook, →AttributeValue | `HBExclusions` | Q-GEN-009…011 | [23](../23_Generation.md) |
| HandbookOptionExclusions | Excluded option-values per group | HandbookId + ProductGroupId + OptionValueId | →Handbook, →OptionValue | `HBExclusions` | Q-GEN-009…011 | [23](../23_Generation.md) |
| HandbookIncrementDesc | Increment descriptions | UNKNOWN | →Handbook (inferred) | `ProductDescriptions`, `HandbookDesigner` | Q-DESC-040/041 | [12](../12_Descriptions.md), [23](../23_Generation.md) |
| DealerCatalogues | Dealer-visible catalogues (PDMPublished mode) | UNKNOWN | CatalogueId→Catalogue (inferred) | `HandbookDesigner` | *(replaces Q-GEN-001 when PDMPublished, BR-GEN-002)* | [23](../23_Generation.md) |

---

## 9. PDMAudit — Audit DB (`PDMAudit.dbo.*`)

Audit is **disabled on eoscloud servers**; three-part names are used everywhere (P-SQL-03).

| Table | Purpose | PK | FK | Used by classes | Used by SQL | Modules |
|---|---|---|---|---|---|---|
| PDMAudit.dbo.Transactions | Audit header (user, date, DB) | TransactionId | — | `StaticDataMaintenance`, `PriceMaintenance` | Q-UTIL-020, Q-PRICE-095…099 | [24](../24_Utilities.md), [18](../18_Pricing.md) |
| PDMAudit.dbo.ItemPriceUpdates | Item price-change audit rows | UNKNOWN | TransactionId→Transactions (inferred) | `PriceMaintenance` | Q-PRICE-095…099 | [18](../18_Pricing.md) |
| PDMAudit.dbo.IncrementalPriceUpdates | Incremental-price audit rows | UNKNOWN | TransactionId→Transactions (inferred) | `PriceMaintenance` | Q-PRICE-095…099 | [18](../18_Pricing.md) |
| PDMAudit.dbo.PFUpdates | Price-formula change audit rows | UNKNOWN | TransactionId→Transactions (inferred) | `StaticDataMaintenance` | Q-UTIL-020 | [24](../24_Utilities.md) |
| PDMAudit.dbo.ProdCodeUpdates | Product-code change audit rows | UNKNOWN | TransactionId→Transactions (inferred) | `StaticDataMaintenance` | *(audit path; no specific Q id transcribed)* | [24](../24_Utilities.md) |

---

## 10. SyteLine LIVE / PBOM (external ERP)

Read for PBOM/cost export via `ConnectionFactory.CreateNewConnectionSyteLine(live:true)`.
These are **not PDM tables**; keys are per the SyteLine schema and `UNKNOWN` here.

| Table | Purpose | PK | FK | Used by classes | Used by SQL | Modules |
|---|---|---|---|---|---|---|
| item | Single-site item cost/status view | UNKNOWN | — | `BOMExport` | Q-EXP-009 | [22](../22_Export.md) |
| item_mst | Multi-site item master (site 20) | UNKNOWN | — | `BOMExport` | Q-EXP-009 | [22](../22_Export.md) |
| MaterialProductId | PBOM material-product mapping | UNKNOWN | — | `BOMExport` | Q-EXP-010 | [22](../22_Export.md) |
| MaterialData | PBOM material data (DeleteStatus) | UNKNOWN | MaterialProductId, MaterialId, MaterialCriteriaId (inferred) | `BOMExport` | Q-EXP-010 | [22](../22_Export.md) |
| Material | PBOM material master | MaterialId (inferred) | — | `BOMExport` | Q-EXP-010/011 | [22](../22_Export.md) |
| MaterialCriteria | PBOM attribute-value criteria | MaterialCriteriaId (inferred) | — | `BOMExport` | Q-EXP-010 | [22](../22_Export.md) |
| MaterialSubJob | PBOM recursive sub-job tree (formula, scrap) | UNKNOWN | MaterialId→Material (inferred) | `BOMExport` | Q-EXP-011 | [22](../22_Export.md) |

> `MaterialProductIdValues` is **omitted** — cited nowhere with a transcribable query
> (see [../26_Data_Model.md](../26_Data_Model.md) §5). `DPSDB` is the detach/attach
> publication database (Q-EXP-023), not a table.

---

## 11. pCon Jet MDB (`tCOMd_*` / `tGEOd_*`)

32-bit Jet/Access files per workspace (`pcr_data_com_ocd.mdb`, `pcr_data_geo_odb.mdb`,
etc.); reached with `Microsoft.Jet.OLEDB.4.0` via `O-*` (and some `Q-*` OleDb) queries.
All keys are `UNKNOWN` (no DDL in source). See [../26_Data_Model.md](../26_Data_Model.md) §2.10.

| Table | Purpose | Used by classes | Used by SQL | Modules |
|---|---|---|---|---|
| tCOMd_Article | pCon article records | pCon export/import, `SuperProductVarCondRelation` | O-CFG-*, Q-ART-* cross-refs | [19](../19_OAP_Export.md), [05](../05_Products.md) |
| tCOMd_ArticleClass | Article↔class link | pCon export/import | O-CFG-* | [19](../19_OAP_Export.md) |
| tCOMd_Class | pCon class definitions | pCon export/import | O-CFG-* | [19](../19_OAP_Export.md) |
| tCOMd_Property | pCon property definitions | pCon export/import | O-CFG-* | [19](../19_OAP_Export.md) |
| tCOMd_PropValue | pCon property values | pCon export/import | O-CFG-* | [19](../19_OAP_Export.md) |
| tCOMd_Package | pCon package records (commercial) | pCon export/import | O-CFG-* | [19](../19_OAP_Export.md) |
| tCOMd_Text | pCon text / translation | `Translations` | Q-TRAN-013/013a/014 | [11](../11_Translations.md) |
| tCOMd_Relation | pCon variant-condition relations | `SuperProductVarCondRelation` | Q-PROD-043/044/048 | [05](../05_Products.md) |
| tCOMd_RelObj | pCon relation objects | `SuperProductVarCondRelation` | Q-PROD-047 | [05](../05_Products.md) |
| tCOMd_RelObjRel | pCon relation-object links | `SuperProductVarCondRelation` | Q-PROD-047 | [05](../05_Products.md) |
| tCOMd_Price | pCon per-item price | `PriceMaintenance` | Q-PRICE-090…094 | [18](../18_Pricing.md) |
| tCOMd_GlobalPrice | pCon global price | `PriceMaintenance` | Q-PRICE-090…094 | [18](../18_Pricing.md) |
| tCOMd_PriceList2 | pCon price-list | `PriceMaintenance` | Q-PRICE-090…094 | [18](../18_Pricing.md) |
| tGEOd_Object | pCon geometry objects | `ODBExport` | O-ODB-002 | [20](../20_ODB_Export.md) |
| tGEOd_Node2D | pCon 2D geometry nodes | `ODBExport` | O-ODB-002 | [20](../20_ODB_Export.md) |
| tGEOd_Node3D | pCon 3D geometry nodes | `ODBExport` | O-ODB-002 | [20](../20_ODB_Export.md) |
| tGEOd_Package | pCon geometry package | `ODBExport` | O-ODB-003 | [20](../20_ODB_Export.md) |
| tGEOd_Layer | pCon geometry layers | `ODBExport` | O-ODB-003 | [20](../20_ODB_Export.md) |
| sel_oas internal tables | OAP selection MDB internals | `OAPExport` | O-OAS-001/002 | [19](../19_OAP_Export.md) |
| typ_cls internal tables | pCon type/class MDB internals | pCon export | *(UNKNOWN statements)* | [19](../19_OAP_Export.md) |

---

## 12. Status / flag legend (summary)

Full definitions live in [../26_Data_Model.md](../26_Data_Model.md) §4 — the key encodings
below are reproduced only as a quick lookup for the tables above.

- **OptionValue.Status** — `0`=URL (unreleased), `1`=ACT (active), `2`=OBS (obsolete),
  `3`=HLD (hold). Exports typically filter `status < 2` (URL/ACT only).
- **Catalogue.Status** — `1`=Active, `2`=Obsolete. Negative `CatalogueId` = pricebook.
- **PDMUserCatalogues.ReadOnly** — **inverted**: `1`=full access, `0`=read-only.
- **DisplayOrder / DisplayOrdinal** — `-1` is coalesced to `9999` (sorts last).
- **Product_Code.BasePriceRef** — `1`→BasePrice, `2`→IncrementalPrice2, `3`→IncrementalPrice3.
- **LanguageId map** — `1`=EN-UK, `2`=FR, `3`=IT, `4`=JP, `5`=DE, `6`=ES, `7`=CN, `8`=PT,
  `9`=NL, `10`=EN-generic.
- **Category exclusions** — `NOT IN (1,128,129,999)`; category `999`=SP Components.
- **Site exclusion** — SiteId `20` excluded from maintenance / handbook / special-cased in export.
- **Currency exclusion** — code `'OGC'` excluded.
- **Hard-coded option ids** — `8`=Fabric Type, `28`=Fabric Colour (P-SQL-08).
- **`'abcx'` sentinel** — deliberate no-match filter used to blank a grid before applying
  a real filter (Q-UTIL-011, Q-UTIL-018).

---

## See also

- [../26_Data_Model.md](../26_Data_Model.md) — data-model source of truth (keys, ER diagram, full legend)
- [../25_Common_SQL.md](../25_Common_SQL.md) — cross-cutting SQL patterns & stored-proc index
- [SQL_Index.md](SQL_Index.md) — query-centric view (query → tables → modules)
- [Business_Rules_Index.md](Business_Rules_Index.md), [Call_Hierarchy.md](Call_Hierarchy.md), [Dependency_Map.md](Dependency_Map.md)
