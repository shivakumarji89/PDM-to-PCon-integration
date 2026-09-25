# 07 — Attributes (Physical Item Attributes & GO Property Holders)

**Module prefix:** BR-ATTR
**Primary legacy source:** `PhysicalMaintenance.cs` (physical item attribute maintenance form), `metaProperties.cs` (OFML `go_properties` serialization holder). Supporting evidence for the real DB attribute tables drawn from `OCDExport.cs`, `ProductDescriptions.cs`, `CADMaintenance.cs`, `SIFImport.cs`, `MainMenu.cs`, `AuthenticateUser.cs`.
**Status:** Verified from source unless marked `UNKNOWN`.

> **Scope note / naming disambiguation.** This module covers two *different* things that the legacy code loosely calls "attributes/properties":
> 1. **`PhysicalMaintenance.cs`** — a maintenance form for **physical item attributes** (weight, volume, dimensions, freight category, commodity/HS code, FSC compliance, WebEOS stock restrictions, delivery offsets). It operates on the `Item` table and physical/logistics side-tables. It does **NOT** touch the `Attribute`/`AttributeValue` metadata tables.
> 2. **`metaProperties.cs`** — a pure in-memory **OFML/OCD serialization holder (DTO)** whose only job is to carry six string fields and emit them as a CSV row into the `go_properties` export file. It is **NOT** table-backed and performs **no** database access.
>
> The **real** configurable-product `Attribute` / `AttributeValue` metadata tables (which drive GO/OCD property generation in module 08) are *read* here to document the data model, but their maintenance UI lives in other modules (`CADMaintenance`, `ProductDescriptions`, `SIFImport`) and is out of scope for this file.

---

## 1. Purpose

`PhysicalMaintenance.cs` provides a WinForms maintenance screen for the **physical / logistics attributes of items**, split across three tabs:

- **Physical tab** — edit per-`Item` `WeightKilos`, `VolumeLitres`, `FreightCategory`, `CommodityCode`, `FSCCompliant`, and (via CSV import) `Height`/`Width`/`Depth`.
- **WebEOS tab** — edit `WebEOSItemRestrictions` (per item/site/catalogue web-order quantity caps). Tab only appears if the table exists.
- **Delivery tab** — edit `CPCDeliveryOffsets` and `CPCSourceCountries` (per catalogue/product-category delivery lead-time offsets and source countries).

It also hosts a **Commodity Code tree editor** (add/edit/delete rows in the `CommodityCode` reference table) and an **item option incremental-volume** editor (`ItemOptionValues.IncrementalVolume`).

`metaProperties.cs` is a data-transfer object used only by the OFML "GO" export (`OCDExport.cs`). Each instance holds one property assignment (`product`, `articleID`, `propertyName`, `propertyValue`, `variantCode`, `variantValue`) and is serialized to the `go_properties.csv` output table. See §5 and module 08 for the export pipeline.

---

## 2. Entry Points

### PhysicalMaintenance form
- **Launch:** `MainMenu.PhysDataButton_Click` (`MainMenu.cs:2924`) constructs `new PhysicalMaintenance()`, calls `initialiseGui()` then `initialiseArrays()`, centres the form, and `Show()`s it.
- **Menu gating:** the `PhysDataButton` is only added to the enabled-buttons list when `AuthenticateUser.CommodityMaintenance` is `true` (`MainMenu.cs:3070`). → BR-ATTR-001.
- **Constructor:** `PhysicalMaintenance()` (`PhysicalMaintenance.cs:1170`) wires `base.Load += PhysicalMaintenance_Load`, sets `selectedTab = 1`, and builds the designer control tree (all action buttons start `Enabled = false`).
- **Load event:** `PhysicalMaintenance_Load` (`PhysicalMaintenance.cs:1812`) creates connections/adapters, sets the base `Item` select/update commands, calls `CheckTables()`, `WebEOSUpdate()`, `DeliveryUpdate()`, `PhysicalItemChange("*")`, then `UpdateCategory()`.
- **Excel import trigger:** an `excel_icon.png` PictureBox added in `_Load` fires `importData` on click (`PhysicalMaintenance.cs:1855` area).

### metaProperties DTO
- **Construction:** `new metaProperties(...)` at `OCDExport.cs:1856` (inside the GO/OCD build loop).
- **Consumption:** added to `metaPropertyData`, which is added to `OCDTables` at `OCDExport.cs:3046` and serialized by the OCD writer loop (`OCDExport.cs:399-618`).

---

## 3. Call Hierarchy

### PhysicalMaintenance (Form → Event → Controller → Service → Repository → SQL → Model → UI)
```
MainMenu (Form)
  └─ PhysDataButton_Click (Event)                     [gated by CommodityMaintenance]
       └─ new PhysicalMaintenance().initialiseGui()/initialiseArrays()/Show()
            └─ PhysicalMaintenance_Load (Event)
                 ├─ ConnectionFactory.CreateNewConnection  (Service/Repository)
                 ├─ CheckTables()        → SQL Q-ATTR-010 (sysobjects) → remove WebEOSTab
                 ├─ WebEOSUpdate()       → SQL Q-ATTR-008 (adapter select)
                 ├─ DeliveryUpdate()     → SQL Q-ATTR-009 (adapter select)
                 ├─ initialiseArrays()   → SQL Q-ATTR-001 catalogues, Q-ATTR-002 freight, Q-ATTR-003 sites
                 ├─ UpdateCategory()     → SQL Q-ATTR-011 (categories)
                 └─ PhysicalItemChange() → SQL Q-ATTR-012/014 (item + physical grid) → DataTable → grid (UI)
       ├─ catalogue_selector_SelectedIndexChanged (Event) → PhysicalItemChange
       ├─ SubmitButton_Click (Event)   → adapter UPDATE Q-ATTR-005 (Item, optimistic concurrency)
       ├─ ApplyButton_Click / WebEOS save (Event) → SQL Q-ATTR-015 (delete/insert/update WebEOS)
       ├─ Delivery save (Event)        → SQL Q-ATTR-017 (CPCDeliveryOffsets / CPCSourceCountries)
       ├─ Commodity tree events        → SQL Q-ATTR-018 (CommodityCode CRUD)
       └─ importData (Event)           → SQL Q-ATTR-019 (UPDATE Item dims from CSV)
```

### metaProperties (export DTO path)
```
OCDExport build loop
  └─ (per item) SQL Q-ATTR-021 (Attribute/AttributeValue/BaseAttributeValues)  [Repository/SQL]
       └─ new metaProperties(product, articleID, propertyName, propertyValue,"","")  [Model/DTO]
            └─ metaPropertyData.Add(...)
                 └─ OCDTables.Add(metaPropertyData)              (OCDExport.cs:3046)
                      └─ OCD writer loop reads DTO.getAllProperties() → CSV row  (OCDExport.cs:589-608)
                           └─ file "go_properties.csv"  (from DTO.fileName)
```
`metaProperties` has **no** UI, service, or repository layer of its own — it is a leaf model object.

---

## 4. SQL Analysis

> All queries below are **inline string-concatenated** unless explicitly noted as *parameterised adapter command*. Concatenated queries interpolate values directly and are injection-prone (see §10).

### PhysicalMaintenance queries

**Q-ATTR-001** — Catalogue picker with per-user read-only flag (`PhysicalMaintenance.cs:1556`)
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly
FROM PDMUserCatalogues puc
INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId
WHERE puc.UserId = <AuthenticateUser.UserId> AND Catalogue.Status = 1
ORDER BY Catalogue.Name
```
*Why:* populate the catalogue selector to only catalogues the current user is assigned to (`PDMUserCatalogues`) that are active (`Catalogue.Status = 1`), and remember each catalogue's `ReadOnly` flag for edit-gating. → BR-ATTR-002, BR-ATTR-011.

**Q-ATTR-002** — Freight categories (`PhysicalMaintenance.cs:1575`)
```sql
SELECT FreightCategory, Description From FreightCategory
```
*Why:* fill the freight-category dropdown. → BR-ATTR-012.

**Q-ATTR-003** — Site list excluding site 20 (`PhysicalMaintenance.cs:1594`)
```sql
SELECT Description, SiteId FROM Site WHERE SiteId NOT IN (20)
```
*Why:* populate the WebEOS site selector; site 20 is hard-excluded. → BR-ATTR-013.

**Q-ATTR-004** — Base item adapter select (parameterised adapter, `PhysicalMaintenance.cs:1824`)
```sql
SELECT ItemId, Item, WeightKilos, VolumeLitres, CommodityCode, FSCCompliant FROM dbo.Item
```
*Why:* the `SqlDataAdapter` select backing the physical-attribute update. → BR-ATTR-014.

**Q-ATTR-005** — Item physical update with optimistic concurrency (**parameterised** adapter command, `PhysicalMaintenance.cs:1826`)
```sql
UPDATE dbo.Item SET WeightKilos = @WeightKilos, VolumeLitres = @VolumeLitres,
  FreightCategory = @FreightCategory, CommodityCode = @CommodityCode, FSCCompliant = @FSCCompliant
WHERE (ItemId = @Original_ItemId)
  AND (CommodityCode = @Original_CommodityCode OR @Original_CommodityCode IS NULL AND CommodityCode IS NULL)
  AND (FreightCategory = @Original_FreightCategory OR @Original_FreightCategory IS NULL AND FreightCategory IS NULL)
  AND (VolumeLitres = @Original_VolumeLitres OR @Original_VolumeLitres IS NULL AND VolumeLitres IS NULL)
  AND (WeightKilos = @Original_WeightKilos OR @Original_WeightKilos IS NULL AND WeightKilos IS NULL)
  AND (FSCCompliant = @Original_FSCCompliant OR @Original_FSCCompliant IS NULL);
SELECT WeightKilos, VolumeLitres, FreightCategory, CommodityCode, FSCCompliant, ItemId
FROM dbo.Item WHERE (ItemId = @ItemId)
```
*Why:* saves edited physical attributes only if the row still matches every original value (optimistic concurrency — prevents last-writer-wins overwrites), then reselects the saved row. This is the **one genuinely parameterised** write path in the form. → BR-ATTR-015, BR-ATTR-016.

**Q-ATTR-006** — Item option incremental-volume select (adapter, `PhysicalMaintenance.cs:1840` / `3380`)
```sql
SELECT dbo.OptionValue.OrderCodeValue, dbo.OptionValue.Name, dbo.ItemOptionValues.IncrementalVolume,
       dbo.Item.Item, dbo.ItemOptionValues.OptionValueId
FROM dbo.Item
INNER JOIN dbo.ItemOptionValues ON dbo.Item.ItemId = dbo.ItemOptionValues.ItemId
INNER JOIN dbo.OptionValue ON dbo.ItemOptionValues.OptionValueId = dbo.OptionValue.OptionValueId
ORDER BY dbo.Item.Item
```
*Why:* backing grid for editing per-item-option incremental volume. → BR-ATTR-017.

**Q-ATTR-007** — Item option incremental-volume update (adapter, `PhysicalMaintenance.cs:1842`)
```sql
Update ItemOptionValues SET IncrementalVolume = @IncrementalVolume
WHERE (ItemId = @Original_ItemId) AND (OptionValueId = @Original_OptionValueId)
```
*Why:* persists incremental-volume edits keyed by item+option. → BR-ATTR-017.

**Q-ATTR-008** — WebEOS restrictions select (adapter, `PhysicalMaintenance.cs:1866`)
```sql
SELECT ItemId, SiteId, CatalogueId, WebEOSQuantity FROM dbo.WebEOSItemRestrictions
```
*Why:* backing adapter for the WebEOS tab. → BR-ATTR-018.

**Q-ATTR-009** — Delivery offsets select (adapter, `PhysicalMaintenance.cs:1875`)
```sql
SELECT CatalogueId, ProductCategoryId, cpc.Name, SourceCountry, DeliveryCountry, ShipVia, DeliveryOffset
FROM CPCDeliveryOffsets
```
*Why:* backing adapter for the Delivery tab. → BR-ATTR-019.

**Q-ATTR-010** — WebEOS table existence probe (`PhysicalMaintenance.cs:1883`)
```sql
SELECT name FROM sysobjects WHERE name = 'WebEOSItemRestrictions'
```
*Why:* if the table does not exist in the connected DB, the WebEOS tab is removed at runtime. → BR-ATTR-020.

**Q-ATTR-011** — Product-category list for the selected catalogue (`PhysicalMaintenance.cs:1968`)
```sql
SELECT pc.ProductCategoryId, od.ShortDescription,
       CASE WHEN cpc.DisplayOrder = -1 THEN 9999 ELSE cpc.DisplayOrder END AS cpcDO
FROM ProductCategory pc
INNER JOIN CatalogueProductCategories cpc ON pc.ProductCategoryId = cpc.ProductCategoryId
INNER JOIN OtherDescription od ON cpc.DescriptionId = od.DescriptionId AND od.LanguageId = 1
WHERE cpc.CatalogueId = <catalogueId> AND cpc.ProductCategoryId NOT IN (1, 128, 129, 999)
ORDER BY cpcDO
```
*Why:* category selector; `DisplayOrder = -1` (unsorted sentinel) is coalesced to `9999` (sort last); categories 1/128/129/999 are hard-excluded (system/reserved categories). `LanguageId = 1` = English. → BR-ATTR-021, BR-ATTR-022, BR-ATTR-023.

**Q-ATTR-012** — Item list for physical grid, filtered by catalogue/range (`PhysicalMaintenance.cs:2133` and `2185`)
```sql
-- 2185 (base variant):
SELECT DISTINCT Item.ItemId, Item.Item
FROM Item
INNER JOIN Product ON Item.ProductId = Product.ProductId
INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
-- 2133 variant additionally joins CatalogueItems ci to scope by catalogue
```
*Why:* determine which items to show for the current catalogue/category selection. → BR-ATTR-024.

**Q-ATTR-013** — WebEOS grid join (per site + catalogue) (`PhysicalMaintenance.cs:2311`, `2349`)
```sql
SELECT Item.ItemId, we.SiteId, we.CatalogueId, we.WebEOSQuantity,
       Item.Item, Item.Height, Item.Width, Item.Depth
FROM Item
LEFT OUTER JOIN WebEOSItemRestrictions we
  ON Item.ItemId = we.ItemId AND we.SiteId = '<siteId>' AND we.CatalogueId = '<catalogueId>'
WHERE ( ... )
```
*Why:* show each item's current WebEOS quantity (LEFT JOIN so items with no restriction still appear). **Note:** the `2349` variant has a missing-space bug (`'WHERE`), see §7. → BR-ATTR-025.

**Q-ATTR-014** — Physical attribute grid select (`PhysicalMaintenance.cs:2499`)
```sql
SELECT ItemId, Item, WeightKilos, VolumeLitres, FreightCategory, CommodityCode, FSCCompliant FROM Item
```
*Why:* the visible physical grid (extended with a `WHERE` built from the item filter). → BR-ATTR-014.

**Q-ATTR-015** — WebEOS save: delete-then-insert / update (`PhysicalMaintenance.cs:2613`, `2620`, `2647`, `2650`, `2655`)
```sql
-- lookup ItemId from Item text:
SELECT ItemId From Item WHERE Item = '<item>'
-- clear:
DELETE FROM WebEOSItemRestrictions WHERE <keys>
-- existence check:
SELECT ItemId, SiteId, CatalogueId FROM WebEOSItemRestrictions
  WHERE ItemId = <id> AND SiteId = <siteId> AND CatalogueId = <catalogueId>
-- insert:
INSERT INTO WebEOSItemRestrictions (ItemId, SiteId, CatalogueId, WebEOSQuantity)
  VALUES (<id>, <siteId>, <catalogueId>, <qty>)
-- dimension update (Height/Width/Depth) also issued here:
UPDATE Item SET Height = ...
```
*Why:* persist WebEOS quantity edits and item dimensions from the WebEOS tab. → BR-ATTR-025, BR-ATTR-026.

**Q-ATTR-016** — Delivery grid select (`PhysicalMaintenance.cs:2410`, `2450`) and category list (`2438`)
```sql
-- 2438:
SELECT ProductCategoryId, Name FROM CatalogueProductCategories WHERE CatalogueId = <id> ORDER BY DisplayOrder
-- 2410/2450 join cpcsc / Country to show source-country + offset per CPC
SELECT cpcsc.CatalogueId, cpcsc.ProductCategoryId, cpc.Name, Country.CountryName AS SourceCountry, CASE WHEN cpc...
```
*Why:* populate the Delivery tab grid. → BR-ATTR-019, BR-ATTR-027.

**Q-ATTR-017** — Delivery save (`PhysicalMaintenance.cs:2695`, `2712`, `2726`, `2729`)
```sql
-- clear all offsets for this catalogue first:
DELETE FROM CPCDeliveryOffsets WHERE CatalogueId = <catalogueId>
-- country lookup:
SELECT CountryId, CountryName FROM Country
-- existence check on source-country row:
SELECT CatalogueId, ProductCategoryId FROM CPCSourceCountries
  WHERE CatalogueId = <catId> AND ProductCategoryId = <pcId>
-- insert source country:
INSERT INTO CPCSourceCountries (CatalogueId, ProductCategoryId, SourceCountryId) VALUES (<catId>, <pcId>, ...)
```
*Why:* replace-all persistence of delivery offsets/source countries for the catalogue. **Delete-then-reinsert** pattern (not diff-based). → BR-ATTR-027, BR-ATTR-028.

**Q-ATTR-018** — Commodity Code reference CRUD (`PhysicalMaintenance.cs:3000`, `3038`, `3050`, `3078`, `3099`, `3144`, `3161`, `3242`)
```sql
-- add (no HS code):
INSERT INTO CommodityCode(CommodityCode, Description) VALUES ('<code>', '<desc>')
-- duplicate-parent check (first 4 chars):
SELECT CommodityCode FROM CommodityCode WHERE (CommodityCode = '<code[0..4]>')
-- add (with HS code):
INSERT INTO CommodityCode(CommodityCode, Description, HSCode) VALUES ('<code>', '<desc>', '<hs>')
-- edit (HSCode assignment commented out in source):
UPDATE CommodityCode SET Description = '<desc>'/*, HSCode = '<hs>'*/ WHERE CommodityCode = '<code>'
-- delete:
DELETE FROM CommodityCode WHERE (CommodityCode = '<code>')
-- tree load parents (len = 4) then children (len > 4):
SELECT CommodityCode, Description FROM CommodityCode WHERE len(CommodityCode) = 4 ORDER BY CommodityCode
SELECT CommodityCode, Description FROM CommodityCode WHERE len(CommodityCode) > 4 ORDER BY CommodityCode
-- validate description on save:
SELECT Description FROM CommodityCode WHERE (CommodityCode = '<code>')
```
*Why:* maintain the commodity-code hierarchy (4-char headings, >4-char detail codes). → BR-ATTR-029, BR-ATTR-030, BR-ATTR-031, BR-ATTR-032.

**Q-ATTR-019** — CSV import: dimension/weight/volume update (`PhysicalMaintenance.cs:1765`)
```sql
UPDATE Item SET WeightKilos = <w>, VolumeLitres = <v>, Height = <h>, Width = <wd>, Depth = <d>
WHERE Item = '<item>'
```
*Why:* bulk update physical values from a CSV file. Only columns whose CSV value is `> 0` are included (partial update). → BR-ATTR-033, BR-ATTR-034, BR-ATTR-035.

**Q-ATTR-020** — Option incremental-volume grid (per selected item) (`PhysicalMaintenance.cs:3380`, `3428`)
```sql
SELECT ... FROM dbo.Item INNER JOIN dbo.ItemOptionValues ... WHERE Item.Item = '<item>' ORDER BY dbo.Item.Item
UPDATE ItemOptionValues SET IncrementalVolume = <v> WHERE (ItemId = <id>) AND (OptionValueId = <ovId>)
```
*Why:* per-item incremental-volume editing grid + save. → BR-ATTR-017.

### metaProperties / real Attribute-table source query

**Q-ATTR-021** — GO property source (real `Attribute`/`AttributeValue`/`BaseAttributeValues` join, `OCDExport.cs:1720`)
```sql
SELECT attr.Name AS attr_name, atval.Name AS atval_name,
  CASE WHEN atval.OrderCodeValue IS NULL THEN atval.Name ELSE atval.OrderCodeValue END AS OrderCodeValue,
  CASE WHEN attr.WebMenuAttribute = 1 THEN 'True' ELSE 'False' END AS IsFunctional,
  de_atval.ShortDescription AS de_atval, de_attr.ShortDescription AS de_attr,
  nl_atval.ShortDescription AS nl_atval, nl_attr.ShortDescription AS nl_attr
FROM AttributeValue atval WITH (NOLOCK)
INNER JOIN BaseAttributeValues bav ON atval.AttributeValueId = bav.AttributeValueId
INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId
LEFT OUTER JOIN OtherDescription de_atval ON atval.DescriptionId = de_atval.DescriptionId AND de_atval.LanguageId = 5
LEFT OUTER JOIN OtherDescription de_attr  ON attr.DescriptionId  = de_attr.DescriptionId  AND de_attr.LanguageId  = 5
LEFT OUTER JOIN OtherDescription nl_atval ON atval.DescriptionId = nl_atval.DescriptionId AND nl_atval.LanguageId = 9
LEFT OUTER JOIN OtherDescription nl_attr  ON attr.DescriptionId  = nl_attr.DescriptionId  AND nl_attr.LanguageId  = 9
WHERE bav.ItemId = <itemId> /*AND atval.OrderCodeValue IS NOT NULL*/
ORDER BY attr.DisplayOrder, atval.DisplayOrdinal
```
*Why:* for a given item, read its **base attribute values** and the parent attribute metadata, then build `metaProperties` (GO property) and `metaTypes` rows. Notes: `OrderCodeValue` falls back to `Name` when null; `WebMenuAttribute = 1` marks the attribute as *functional*; DE = `LanguageId 5`, NL = `LanguageId 9`; ordering is by `Attribute.DisplayOrder` then `AttributeValue.DisplayOrdinal`; the `OrderCodeValue IS NOT NULL` filter is **commented out** in source. → BR-ATTR-004, BR-ATTR-005, BR-ATTR-006, BR-ATTR-007, BR-ATTR-036.

> **Cross-module note:** the `Attribute`/`AttributeValue` tables are also queried in `AddDataList.cs:436`, `CADMaintenance.cs:9801/10223/10274`, `ProductDescriptions.cs:6268/6322`, `SIFImport.cs:5992/6004/6014/8736`, `MainMenu.cs:3998/4016`, `OFDAExport.cs`, `ExportThread.cs:2005`, etc. Those are catalogued in §5 for the data model but their business logic belongs to their own modules.

---

## 5. Data Model

### 5.1 Physical / logistics tables (owned/edited by PhysicalMaintenance)

**`Item`** (physical columns only; full table documented in 06_Articles)
| Column | Meaning | Notes |
|---|---|---|
| `ItemId` | PK | |
| `Item` | item order code (business key) | used as text key in inline SQL |
| `WeightKilos` | decimal(16,3) weight kg | update only if CSV value > 0 |
| `VolumeLitres` | decimal(16,3) volume L | |
| `FreightCategory` | varchar(2) FK → `FreightCategory.FreightCategory` | |
| `CommodityCode` | varchar(8) FK → `CommodityCode.CommodityCode` | |
| `FSCCompliant` | int flag (FSC timber compliance) | `UNKNOWN` exact domain; treated as int |
| `Height`, `Width`, `Depth` | mm dimensions | set only via CSV import / WebEOS tab |

**`FreightCategory`** — `FreightCategory` (PK, varchar(2)), `Description`.

**`CommodityCode`** — `CommodityCode` (PK, varchar(8)), `Description`, `HSCode`. Hierarchy encoded by string length: `len = 4` → heading/parent node; `len > 4` → detail/child node. `HSCode` edit is **disabled** (commented out) in the update path.

**`Site`** — `SiteId` (PK), `Description`. Site `20` is hard-excluded from the WebEOS site selector.

**`WebEOSItemRestrictions`** — composite key (`ItemId`, `SiteId`, `CatalogueId`), `WebEOSQuantity`. Per item/site/catalogue web-order quantity cap. Table may be **absent** in some databases (see BR-ATTR-020).

**`CPCDeliveryOffsets`** — (`CatalogueId`, `ProductCategoryId`, `SourceCountry`, `DeliveryCountry`, `ShipVia`, `DeliveryOffset`), plus `cpc.Name` via join to `CatalogueProductCategories`. Per catalogue-product-category delivery lead-time offset.

**`CPCSourceCountries`** — (`CatalogueId`, `ProductCategoryId`, `SourceCountryId`). Source country per CPC.

**`Country`** — `CountryId` (PK), `CountryName`.

**`ItemOptionValues`** — (`ItemId`, `OptionValueId`) with `IncrementalVolume` (and `IncrementalPrice*` used elsewhere).

**`PDMUserCatalogues`** — (`UserId`, `CatalogueId`, `ReadOnly`). `ReadOnly` semantics here: value `0` = editable, non-zero = read-only (see BR-ATTR-011). *(This is the same table whose `ReadOnly` flag is documented as INVERTED for the catalogue picker in 02_User_Permissions; in PhysicalMaintenance the `catalogueIsReadOnly()` test treats `ReadOnly == 0` as editable.)*

**`Catalogue`** — `CatalogueId` (PK), `Name`, `Status` (=1 active), `DisplayOrder`.

**`CatalogueProductCategories`** (`cpc`) — (`CatalogueId`, `ProductCategoryId`), `Name`, `DisplayOrder`, `DescriptionId`. `DisplayOrder = -1` = unsorted sentinel (→ 9999).

**`ProductCategory`** — `ProductCategoryId` (PK), `Name`. Reserved IDs `1, 128, 129, 999` excluded from category pickers.

### 5.2 Configurable-product attribute metadata tables (read to build GO/OCD properties)

These are the **real** attribute tables. Column lists are aggregated from queries across the codebase (see §4 cross-module note); each column is cited where first observed.

**`Attribute`** — attribute definition (a configurable characteristic, e.g. "Arms", "Base finish")
| Column | Meaning | Evidence |
|---|---|---|
| `AttributeId` | PK | Q-ATTR-021 |
| `Name` | attribute name | Q-ATTR-021 |
| `DescriptionId` | FK → `OtherDescription` | Q-ATTR-021 |
| `DisplayOrder` | sort order (also 1 = "primary" attribute in image/OFDA joins) | Q-ATTR-021; `OFDAExport.cs:1139` `attr.DisplayOrder = 1` |
| `WebMenuAttribute` | bit; 1 = *functional* attribute (drives config) | Q-ATTR-021; `ProductDescriptions.cs:6268` `WebAttr` |
| `ProductCategoryId` | FK → `ProductCategory` | `AddDataList.cs:436`, `SIFImport.cs:8736` |
| `OrderCodeFormatKey` | order-code format key | `ProductDescriptions.cs:5546`, `SIFImport.cs:8453` |
| `EOSLiteDisplayOrder` | EOS-lite display order | `ProductDescriptions.cs:6268` |
| `AttributeType` | attribute type code | `SIFImport.cs:8736`, `CADMaintenance.cs:9801` |
| `LayerNameList` | CAD layer name list | `CADMaintenance.cs:9801/10223` |
| `HideByDefault` | bit; hide attribute by default | `CADMaintenance.cs:9801` |
| `HasDependentOptions` | bit; attribute contributes dependent option chars | `CADMaintenance.cs:9801`; `UpdateThread.cs:290` `SUM(ABS(attr2.HasDependentOptions))` |

**`AttributeValue`** (`atval`) — a selectable value of an attribute
| Column | Meaning | Evidence |
|---|---|---|
| `AttributeValueId` | PK | Q-ATTR-021 |
| `AttributeId` | FK → `Attribute` | Q-ATTR-021 |
| `Name` | value name | Q-ATTR-021 |
| `OrderCodeValue` | order-code fragment (nullable; falls back to `Name`) | Q-ATTR-021 |
| `DescriptionId` | FK → `OtherDescription` | Q-ATTR-021 |
| `DisplayOrdinal` | sort order within attribute | Q-ATTR-021 |
| `Status` | status flag (1 = active) | `MainMenu.cs:3998` |
| `AttributeValueType` | value type (`> 0` filter in OFDA) | `OFDAExport.cs:1139` |
| `ModelSpecific` | CAD model-specific flag | `CADMaintenance.cs:12372/13332` |
| `CADMaterial` | CAD material | `CADMaintenance.cs:12372` |
| `ImageFile` | value image file | `ExportLayoutStyleThread.cs:160`, `ValidateImageThread.cs:71` |

**Link / assignment tables** (which attribute values apply where)
| Table | Key | Meaning |
|---|---|---|
| `BaseAttributeValues` | (`ItemId`, `AttributeValueId`) | base config: value applies to an item. INSERT/exists-check in `SIFImport.cs:6004/6014`. |
| `CatalogueAttributeValues` | (`CatalogueId`, `AttributeValueId`) | value enabled for a catalogue |
| `ProductAttributeValues` | (`ProductId`, `AttributeValueId`) | value applies at product level |
| `DependentAttributeValues` | (`AttributeValueId`, `AdditionalOptionValueId`) | dependency: selecting a value implies an additional option value (`CADMaintenance.cs:9884`) |
| `MaterialProductIdValues` | (`MaterialProductId`, `AttributeValueId`) | BOM material-product ↔ attribute value (`BOMExport.cs:185`) |

**`OtherDescription`** — localized text: `DescriptionId`, `LanguageId`, `ShortDescription`. LanguageIds observed: `1` = EN (default), `5` = DE, `9` = NL.

### 5.3 metaProperties DTO field layout (`go_properties.csv` row)

`metaProperties` is a DTO, **not a table**. `getAllProperties()` returns the fields in this fixed order (the CSV column order):
| Idx | Field | Populated from (Q-ATTR-021 build) |
|---|---|---|
| 0 | `product` | `text21` = product/article root code |
| 1 | `articleID` | `text22` = `<product>_<seq>` article id |
| 2 | `propertyName` | `text23` = `"G" + removeNonAlphaStrict(attr_name)` (GO property name) |
| 3 | `propertyValue` | `text24` = `removeNonAlphaStrict(attr_name) + removeNonAlphaStrict(OrderCodeValue)` |
| 4 | `variantCode` | always `""` at the only call site |
| 5 | `variantValue` | always `""` at the only call site |

Constant: `fileName = "go_properties"` (set in constructor). No PK/FK — pure serialization holder.

---

## 6. Business Rules

> IDs are unique within module 07. "Verified" = provable from cited source; otherwise `UNKNOWN`.

### Permissions / access
- **BR-ATTR-001** — The Physical Data screen is only reachable when the current user has the `CommodityMaintenance` privilege (`MainMenu.cs:3070` gates `PhysDataButton`). The flag is loaded in `AuthenticateUser.cs:99` from `PDMUserPrivileges.CommodityMaintenance`. *(Verified.)*
- **BR-ATTR-002** — The catalogue selector only lists catalogues assigned to the current user (`PDMUserCatalogues.UserId = <UserId>`) whose `Catalogue.Status = 1`, ordered by name (Q-ATTR-001). *(Verified.)*
- **BR-ATTR-011** — Edit gating: `catalogueIsReadOnly()` (`PhysicalMaintenance.cs:1626`) returns **editable** (`false`) only when `_readOnlyCatalogues[selectedCatalogue] == 0` **AND** `Global.readOnlyDBConnection` is false; otherwise the catalogue is treated as read-only. Note the `ReadOnly == 0` = editable convention here. *(Verified.)*
- **BR-ATTR-036** — A read-only database connection (`Global.readOnlyDBConnection`) forces every catalogue read-only regardless of per-user `ReadOnly` (part of BR-ATTR-011 predicate). *(Verified.)*

### Filtering / exclusions
- **BR-ATTR-013** — Site `20` is always excluded from the WebEOS site selector (`WHERE SiteId NOT IN (20)`, Q-ATTR-003). Rationale `UNKNOWN` (likely a non-sellable/internal site). *(Verified filter; rationale UNKNOWN.)*
- **BR-ATTR-021** — Reserved product categories `1, 128, 129, 999` are excluded from the category selector (Q-ATTR-011). (Consistent with 04_Product_Categories: 999 = SP Components.) *(Verified.)*
- **BR-ATTR-022** — Category `DisplayOrder = -1` (unsorted sentinel) is coalesced to `9999` so unordered categories sort **last** (Q-ATTR-011 `CASE WHEN cpc.DisplayOrder = -1 THEN 9999`). *(Verified.)*
- **BR-ATTR-023** — Category descriptions are taken from `OtherDescription` at `LanguageId = 1` (English) (Q-ATTR-011). *(Verified.)*
- **BR-ATTR-024** — The physical item grid is populated from items joined via `Product → ProductRange` (and optionally `CatalogueItems` for catalogue scoping) (Q-ATTR-012). *(Verified.)*

### Physical attribute editing / persistence
- **BR-ATTR-014** — The physical grid shows `ItemId, Item, WeightKilos, VolumeLitres, FreightCategory, CommodityCode, FSCCompliant` (Q-ATTR-004 / Q-ATTR-014). *(Verified.)*
- **BR-ATTR-015** — Physical-attribute saves use optimistic concurrency: the UPDATE only applies if **all** original values (`ItemId`, `CommodityCode`, `FreightCategory`, `VolumeLitres`, `WeightKilos`, `FSCCompliant`) still match, including null-safe comparisons (Q-ATTR-005). *(Verified.)*
- **BR-ATTR-016** — After a successful physical UPDATE, the row is immediately re-selected (`SELECT ... WHERE ItemId = @ItemId`) to refresh the grid with persisted values (Q-ATTR-005 second statement). *(Verified.)*
- **BR-ATTR-017** — Per-item option incremental volume is edited via `ItemOptionValues.IncrementalVolume`, keyed by (`ItemId`, `OptionValueId`) (Q-ATTR-006/007/020). *(Verified.)*

### WebEOS
- **BR-ATTR-018** — WebEOS restrictions are keyed by (`ItemId`, `SiteId`, `CatalogueId`) with a single `WebEOSQuantity` (Q-ATTR-008). *(Verified.)*
- **BR-ATTR-020** — The WebEOS tab is only shown if the `WebEOSItemRestrictions` table exists in the connected database; `CheckTables()` probes `sysobjects` and removes the tab if absent (Q-ATTR-010, `PhysicalMaintenance.cs:1889`). *(Verified.)*
- **BR-ATTR-025** — WebEOS grid uses a LEFT OUTER JOIN so items without a restriction still appear (with null quantity) (Q-ATTR-013). *(Verified.)*
- **BR-ATTR-026** — WebEOS save resolves the `ItemId` from the item text, DELETEs matching restriction rows, then INSERTs the new quantity (delete-then-insert, not in-place update). Dimension edits (`Height`) are issued in the same save path (Q-ATTR-015). *(Verified.)*

### Delivery
- **BR-ATTR-019** — Delivery offsets are stored in `CPCDeliveryOffsets` keyed by (`CatalogueId`, `ProductCategoryId`, `SourceCountry`, `DeliveryCountry`, `ShipVia`) with a `DeliveryOffset` value (Q-ATTR-009). *(Verified.)*
- **BR-ATTR-027** — Delivery save is **replace-all** per catalogue: `DELETE FROM CPCDeliveryOffsets WHERE CatalogueId = <id>` then reinsert; source countries maintained in `CPCSourceCountries` with an exists-check before insert (Q-ATTR-017). *(Verified.)*
- **BR-ATTR-028** — Delivery category list is ordered by `CatalogueProductCategories.DisplayOrder` (Q-ATTR-016, `2438`). *(Verified.)*

### Commodity codes
- **BR-ATTR-029** — Commodity codes form a two-level hierarchy by string length: `len(CommodityCode) = 4` = heading node, `len > 4` = detail node; each level loaded and sorted separately (Q-ATTR-018 tree loads). *(Verified.)*
- **BR-ATTR-030** — On add, a duplicate check is run against the first 4 characters of the new code (`WHERE CommodityCode = '<code[0..4]>'`) (Q-ATTR-018, `3038`). *(Verified.)*
- **BR-ATTR-031** — Add supports an optional `HSCode`: if `inputForm.HSCode` is non-empty the 3-column INSERT is used, otherwise the 2-column INSERT (Q-ATTR-018, `3050`). *(Verified.)*
- **BR-ATTR-032** — Commodity code **edit does not update `HSCode`**: the `HSCode` assignment in the UPDATE is commented out in source (`UPDATE CommodityCode SET Description = '...'/*, HSCode = '...'*/`) (Q-ATTR-018, `3078`). This is a latent/disabled feature. *(Verified.)*

### CSV import (physical bulk)
- **BR-ATTR-033** — Import expects CSV lines of exactly `[item],[weight_kilos],[volume_litres],[height_mm],[width_mm],[depth_mm]`; whitespace is stripped from the whole file before parsing (`text.Replace(" ", "")`, `PhysicalMaintenance.cs:1700`). *(Verified.)*
- **BR-ATTR-034** — Each of the five numeric fields is validated by `isNumericalValue(value, allownegative:false)` (digits + `.` only, non-empty, no negatives). A malformed line aborts the whole import with a format error message (`flag = false; break`). *(Verified.)*
- **BR-ATTR-035** — Import performs **partial** updates: for each row, a column is added to `UPDATE Item SET ...` **only if its parsed value is > 0** (`double.Parse(...) > 0.0`); rows with all-zero values produce no update. The item is matched by `WHERE Item = '<item>'` (Q-ATTR-019). *(Verified.)*

### GO property generation (metaProperties)
- **BR-ATTR-004** — GO/OCD properties are built per item from `BaseAttributeValues` joined to `Attribute`/`AttributeValue`, ordered by `Attribute.DisplayOrder` then `AttributeValue.DisplayOrdinal` (Q-ATTR-021). *(Verified.)*
- **BR-ATTR-005** — `OrderCodeValue` falls back to the value `Name` when null (`CASE WHEN atval.OrderCodeValue IS NULL THEN atval.Name ELSE atval.OrderCodeValue`) (Q-ATTR-021). *(Verified.)*
- **BR-ATTR-006** — An attribute is flagged *functional* (`IsFunctional = 'True'`) when `Attribute.WebMenuAttribute = 1`; this flag drives `addMetaType(..., functional, ...)` (Q-ATTR-021, `OCDExport.cs:1836`). *(Verified.)*
- **BR-ATTR-007** — `metaProperties.propertyName = "G" + removeNonAlphaStrict(attr_name)` and `propertyValue = removeNonAlphaStrict(attr_name) + removeNonAlphaStrict(OrderCodeValue)`; `variantCode`/`variantValue` are always empty at the sole call site (`OCDExport.cs:1856`). *(Verified.)*
- **BR-ATTR-010** — `metaProperties` performs **no** validation, no DB access, and no defaulting; it is a passive holder. Any data quality rules are enforced upstream by Q-ATTR-021 and the OCD build loop. *(Verified.)*

---

## 7. Hidden Logic

- **HL-ATTR-1 — Runtime tab removal.** The WebEOS tab is conditionally removed at load if the table is missing (BR-ATTR-020); the visible tab set therefore differs between databases.
- **HL-ATTR-2 — `ReadOnly == 0` means editable.** Counter-intuitive polarity in `catalogueIsReadOnly()` (`PhysicalMaintenance.cs:1629`). A value of `0` grants edit; any other value denies it. Easy to misread during migration.
- **HL-ATTR-3 — Disabled HSCode edit.** The commodity-code edit silently ignores `HSCode` because the assignment is commented out (BR-ATTR-032). The UI may present an HS field that never persists on edit (only on add).
- **HL-ATTR-4 — Missing-space SQL bug (WebEOS).** At `PhysicalMaintenance.cs:2349` the concatenation produces `...CatalogueId = '<id>'WHERE Item.Item = ...` (no space before `WHERE`). Works only because SQL Server tolerates `'`-then-`WHERE`; brittle. → also a Risk.
- **HL-ATTR-5 — Whole-file whitespace strip on import.** `streamReader.ReadToEnd().Replace(" ", "")` removes **all** spaces, so item codes or values containing spaces would be corrupted silently (BR-ATTR-033).
- **HL-ATTR-6 — Partial-update "0 means skip".** A legitimate zero weight/volume/dimension cannot be imported because `> 0.0` excludes it (BR-ATTR-035). Zero is indistinguishable from "no change".
- **HL-ATTR-7 — Commented-out OrderCodeValue filter.** Q-ATTR-021 contains `/*AND atval.OrderCodeValue IS NOT NULL*/`; values with null order codes are currently included (fallback to Name via BR-ATTR-005). Toggling this comment changes export contents.
- **HL-ATTR-8 — `removeNonAlphaStrict` normalization.** GO property names/values are stripped of non-alphabetic characters before use (BR-ATTR-007); two differently-punctuated attribute names could collide into the same GO property name. Collision behavior `UNKNOWN`.
- **HL-ATTR-9 — `selectedTab` initialised to 1** in the constructor (`PhysicalMaintenance.cs:1199`) while `TabControl.SelectedIndex = 0`; the field and the control can disagree until an index-changed event fires.

---

## 8. UI Behaviour

- All action buttons (`WeightButton`, `VolumeButton`, `SubmitButton`, `ClearButton`, `FreightButton`, `CommodityButton`, `ApplyButton`, `site_selector`) start **disabled** and are enabled contextually as selections change (`PhysicalMaintenance.cs:1301-1416`).
- Three tabs: **Physical**, **WebEOS**, **Delivery** (`TabControl` at `PhysicalMaintenance.cs:1367-1369`), aligned to the bottom. WebEOS may be removed (HL-ATTR-1).
- Changing catalogue or category while unsaved edits exist triggers a save/confirm branch before reload (`PhysicalMaintenance.cs:1928`, `2002`), then disables `SubmitButton`.
- Grids are read into `DataTable`s with `DefaultView.AllowDelete = false` (e.g. `WebEOSDT`, `DeliveryDT`, `PhysicalDT`, `OptionDT`) — rows cannot be deleted directly from the grid.
- An Excel icon (`excel_icon.png`) PictureBox is injected at load and, when clicked, launches the CSV import (`importData`).
- Import shows an explicit format prompt (`[item],[weight_kilos],[volume_litres],[height_mm],[width_mm],[depth_mm]`) before the file dialog, and a format-error `MsgBox` on the first malformed line.
- `metaProperties` has **no UI** (export DTO only).

---

## 9. Dependencies

- **`AuthenticateUser`** — `UserId`, `DefaultCatalogueId`, `DefaultSiteId`, and the `CommodityMaintenance` privilege flag (entry gating).
- **`ConnectionFactory.CreateNewConnection`** — all `SqlConnection`s (foundation).
- **`Global`** — `readOnlyDBConnection` (edit gating), `connectedServer`/`connectedDB` (menu gating), `globalSiteId`.
- **`MainMenu`** — the only launcher (`PhysDataButton_Click`).
- **`GetImage`** — loads the Excel icon.
- **Tables:** `Item`, `FreightCategory`, `CommodityCode`, `Site`, `WebEOSItemRestrictions`, `CPCDeliveryOffsets`, `CPCSourceCountries`, `Country`, `ItemOptionValues`, `OptionValue`, `PDMUserCatalogues`, `Catalogue`, `CatalogueProductCategories`, `ProductCategory`, `OtherDescription`.
- **metaProperties consumers:** `OCDExport.cs` only (build loop + writer). Sibling DTOs: `metaTypes`, `metaArticles`, `metaDescriptions`, `ocdProperty`, `ocdPropertyClass`, `ocdPropertyValue` (module 08), `ocdArtBase`, `ocdArtDesc`.
- **Real attribute tables** (`Attribute`/`AttributeValue`/`BaseAttributeValues`/`CatalogueAttributeValues`/`ProductAttributeValues`/`DependentAttributeValues`) are shared with modules 06 (Articles), 08 (Property Values), 11 (Configuration/CAD), 13 (Descriptions) and the export threads.

---

## 10. Risks

- **R-ATTR-1 (High) — SQL injection.** Most PhysicalMaintenance writes (WebEOS, Delivery, CommodityCode, CSV import) build SQL by string concatenation with UI/file input (Q-ATTR-015/017/018/019). `CommodityCode`/`Description` come straight from an input form; a `'` in a description breaks or injects. Only Q-ATTR-005 (Item save) is parameterised.
- **R-ATTR-2 (Medium) — Replace-all persistence.** Delivery save deletes all `CPCDeliveryOffsets` for a catalogue before reinserting (BR-ATTR-027); a failure mid-save can leave the catalogue with **no** delivery offsets. Same delete-then-insert pattern for WebEOS.
- **R-ATTR-3 (Medium) — Silent data corruption on import.** Whole-file space stripping (HL-ATTR-5) and "0 = skip" partial updates (HL-ATTR-6) can silently drop or mangle legitimate data.
- **R-ATTR-4 (Medium) — Environment-dependent schema.** WebEOS features vanish when the table is missing (BR-ATTR-020); behavior differs across DBs and is not surfaced to the user.
- **R-ATTR-5 (Low) — Fragile SQL string building.** Missing-space bug (HL-ATTR-4) relies on SQL Server leniency; a stricter engine or migration to another DB would break it.
- **R-ATTR-6 (Low) — Read-only polarity confusion.** The `ReadOnly == 0 = editable` convention (BR-ATTR-011) plus a separate INVERTED convention noted in the catalogue picker (02_User_Permissions) is a documented foot-gun during migration.
- **R-ATTR-7 (Low) — Disabled/latent feature drift.** Commented-out HSCode edit (BR-ATTR-032) and OrderCodeValue filter (HL-ATTR-7) mean the running behavior differs from what the code appears to offer; a future "uncomment" changes exports/edits unexpectedly.
- **R-ATTR-8 (Info) — Hardcoded language IDs.** `LanguageId` 1/5/9 (EN/DE/NL) are hardcoded in Q-ATTR-011 and Q-ATTR-021; adding a language requires code changes.
```
