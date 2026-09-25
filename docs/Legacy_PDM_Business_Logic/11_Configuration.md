# 11 — Configuration
**Module prefix:** BR-CFG
**Primary legacy source:** CADMaintenance.cs, WebConfigurator.cs
**Status:** Verified from source unless marked `UNKNOWN`.

> **Coverage note (read first).** `CADMaintenance.cs` is the single largest source file in the
> application (~26,152 lines in the current copy — larger than the ~25,380 originally estimated).
> It was **not** read end-to-end. This document was assembled by grepping the whole file for SQL
> (`SELECT|INSERT|UPDATE|DELETE`, ~318 hits), OLE DB / `tCOMd_`/`tGEOd_` usage (~225 hits), event
> handlers (~256 hits) and public method signatures (~237 hits), then reading targeted ranges for
> the highest-value logic:
> - Entry / GUI setup: `initialiseGui`, `initArrays`, `catalogueSelection`, `categorySelection`,
>   `TabControl1_SelectedIndexChanged`, `optionSelection` (fabric block).
> - pCon linkage: `getPConWorkspace`, `GetPconPackageIdOnly`/`GetPconPackageId`,
>   `getPConPrefixLengthByCategory`, `getArticlePrefixLength`, `CreateNode`,
>   `UpdatePConDataFileToolStripMenuItem_Click` (head), `ClonePConPropertyClassOCD` (SQL).
> - `WebConfigurator.cs` was read in full for its handlers.
>
> **Prioritised as requested:** (a) what CAD/config data is maintained, (b) how variant
> conditions / relations are built, (c) CAD material / geometry handling, (d) the pCon / OFML
> linkage. WebConfigurator is captured separately (§ throughout, tagged **[WC]**).
>
> **Explicitly NOT fully traced (marked `UNKNOWN` where they appear):** the full bodies of the
> very large menu handlers — `UpdatePConDataFileToolStripMenuItem_Click` (XLS→PDM import loop,
> ~18046–18607, only the head read), `UpdatePCon3D/2DModelReferences` (~19366–19978),
> `ConvertOBXToSIF` (~19978–20893), `ExportPConMetatypeData` and its `go_*` helper cluster
> (~22161–24200), `ExportItemModelReferencespCon`/`ImportItemModelReferencespCon`,
> `CreateGmaterialsXMLButton_Click`, `UpdateGMaterials`, the two embedded worker classes
> `PreviewThread`/`RevitThread` (image + Revit-family parsing, ~31–835), and `InitializeComponent`
> (designer, ~6162–8418). Their **existence, entry point and headline purpose** are recorded; their
> internal branch-by-branch rules are `UNKNOWN` and would need line-range reads to verify.

---

## 1. Purpose

`CADMaintenance` is the **CAD / OFML configuration workbench** of PDM. It is a single very large
WinForms form (`public class CADMaintenance : Form`) reached from the main menu **"CAD Maintenance"**
button. It lets a user, per **Catalogue → Product Category → Product/Item → Attribute/Option →
Value**, maintain everything that ties PDM catalogue data to 3-D/2-D CAD geometry and to the pCon /
OFML configurator:

- **Model references** — associate `.dwg` (AutoCAD) and Revit family files with Products, Items,
  Attribute Values and Option Values (`Product.ModelList`, `Item.CADImage3D`, `Item.CADImage2D`).
- **CAD materials / geometry** — `CADMaterial`, `CADSuffix`, `ModelSpecific`, `ProductMaskValue`,
  `ProductMaskKey`, layer key lists (`LayerNameList`), fixed layers and base materials, chromatic
  ordering.
- **CAD layer schemes** — the `CADSchemes` table (per catalogue + pCon package version).
- **Group codes** — `AttributeGroupCodes` / `OptionGroupCodes` (grouping/container/context of
  features for the planner).
- **pCon / OFML integration** — read/write the pCon "creator" MDB databases (Jet/Access via OLE DB):
  geometry (`tGEOd_*`) and commercial/-condition (`tCOMd_*`) tables; resolve pCon package IDs;
  push PDM price / feature data into pCon via an Excel round-trip; clone property classes and model
  references; export OFML metatype (`go_*`) data; and generate VARCOND strings for PA_PRICING.
- A grab-bag of **maintenance utilities** exposed on a menu strip (image validation/archival,
  gMaterials XML, price-rise, visibility categories, OFDA XML validation, OBX→SIF conversion).

The form has **two primary modes**, selected by `TabControl1`:
- **Tab index 0 — Products / "CET"** mode: model refs at Product level plus legacy CET tooling.
- **Tab index 1 — Items / "pCon"** mode: model refs at Item level plus the full pCon toolset (the
  pCon panels, metatype export, VARCOND generation, 2D/3D reference push).

**[WC] `WebConfigurator`** is a much smaller, separate form ("Web Configurator" tool). Its purpose is
to take an **OFDA export XML**, present each product's configurable features as dropdowns, build a
"web DPS" configuration template string + a live `hermanmiller.com` web-configurator URL, and
optionally write that template to `Product.WebDPSProduct` for a filtered set of items. It is **not**
part of the CAD form; it is launched from a different main-menu button and gated by a different
permission (see §2).

---

## 2. Entry Points

### CADMaintenance
| # | Trigger | Code | Notes |
|---|---------|------|-------|
| E-1 | Main-menu **CAD Maintenance** button | `MainMenu.CADButton_Click` (MainMenu.cs:2882) → `new CADMaintenance()`, `initialiseGui()`, `initArrays()`, `Show()` | Button only added to the menu when `AuthenticateUser.CADMaintenance` privilege is true (MainMenu.cs:3058). |
| E-2 | Form load | `CADMaintenance_Load` (CADMaintenance.cs:12218) | Sets `_loaded`, disables editing if `Global.readOnlyDBConnection`. |
| E-3 | `catalogue_selector` change | `catalogue_selector_SelectedIndexChanged` (9128) → `catalogueSelection` (9080) | Repopulates category list. |
| E-4 | `category_selector` change | `category_selector_SelectedIndexChanged` (9323) → `categorySelection` (9153) | Repopulates product/item list. |
| E-5 | `TabControl1` change | `TabControl1_SelectedIndexChanged` (20921) | Switches Products↔Items mode, shows/hides pCon panels & menu items. |
| E-6 | Product/Item/Attribute/Option/Value list selections | `product_list_SelectedIndexChanged` (10052), `attribute_list_SelectedIndexChanged` (10393), `option_list_SelectedIndexChanged` (10627), `atval_list_SelectedIndexChanged` (12472), `optval_list_SelectedIndexChanged` (12651) | Drive `productSelection`/`attributeSelection`/`optionSelection`/`attributeValueSelection`/`optionValueSelection`. |
| E-7 | Model add/replace/remove buttons | `AddModelButton_Click` (11431), `ReplaceModelButton_Click` (11411), `RemoveModelButton_Click` (11406), plus `*Atval*`/`*Optval*` variants (13782–13858) | Update `Product.ModelList` / `Item.CADImage3D` / value `ModelSpecific`. |
| E-8 | Menu strip items | `UpdatePConDataFileToolStripMenuItem_Click` (18046), `UpdatePCon3DModelReferencesToolStripMenuItem_Click` (19366), `UpdatePCon2DModelReferencesToolStripMenuItem_Click` (19434), `ConvertOBXToSIFToolStripMenuItem_Click` (19978), `GenerateVARCONDForPAPRICINGToolStripMenuItem_Click` (21942), `ClonePConPropertyClassOCDToolStripMenuItem_Click` (21635), `ClonePConModelReferencesToolStripMenuItem_Click` (21825), `ExportPConMetatypeDataToolStripMenuItem_Click` (22688), `ValidateProductImagesToolStripMenuItem_Click` (16982), `GetMaterialsToolStripMenuItem_Click` (16500), `UpdateGMaterialsToolStripMenuItem_Click` (17317), `CreateGmaterialsXMLButton_Click` (17647), `ApplyPriceRiseToolStripMenuItem_Click` (17956), `UpdateVisibilityCategoriesToolStripMenuItem_Click` (18009), `ValidateOFDAXmlToolStripMenuItem_Click` (20893) | Utility & pCon operations. |
| E-9 | Base-material / group-code / scheme editors | `SetBaseButton_Click` (14828), `BaseMaterialsAddButton_Click` (15205), `BaseMaterialsUpdateButton_Click` (14994), `BaseMaterialsRemoveButton_Click` (15560), `FixedLayersApplyButton_Click` (14406) | Maintain `CADSchemes`, `*GroupCodes`, `CADSuffix`, `ProductMaskKey`. |

### WebConfigurator **[WC]**
| # | Trigger | Code | Notes |
|---|---------|------|-------|
| WE-1 | Main-menu **Web Configurator** button | `MainMenu.WebConfigButton_Click` (MainMenu.cs:2977) → `new WebConfigurator()`, `Show()` | Guarded by `Global.ofdaManagerOrWebConfigActive` (single instance). Button added only when `AuthenticateUser.CoreMaintenance` **and** connected server is **not** eoscloud (MainMenu.cs:3078). |
| WE-2 | **Load OFDA xml file…** | `button_loadOFDA_Click` (WebConfigurator.cs:815) → `loadOFDAXML` → `OFDAExportManager.LoadThread` | Parses an OFDA export XML on a background thread. |
| WE-3 | Product list select | `list_products_OFDA_SelectedIndexChanged` (1367) → `getOFDAFeaturesForProduct` | Builds feature label/combo controls dynamically. |
| WE-4 | Feature combo change | `selectFeatureValue` (1098) → `updateWebConfigTemplate` | Recomputes template + URL, shows/hides dependent features. |
| WE-5 | **>>>** browse button | `button_web_Click` (1385) → `Process.Start("chrome.exe", text_parsed.Text)` | Opens the built URL in Chrome. |
| WE-6 | **Apply Template** | `ApplyButton_Click` (1385+) | Writes `Product.WebDPSProduct` for a filtered item set (Q-CFG-901). |
| WE-7 | Form closing | `WebVonfiguration_Closing` (847) | Clears `Global.ofdaManagerOrWebConfigActive`. |

---

## 3. Call Hierarchy (Form → Event → Controller → Service → Repository → SQL → Model → UI)

```
MainMenu (CADButton)                          MainMenu (WebConfigButton)  [WC]
  └─ CADButton_Click                            └─ WebConfigButton_Click
       └─ CADMaintenance.initialiseGui()             └─ new WebConfigurator().Show()
       └─ CADMaintenance.initArrays()  ── SQL Q-CFG-001 (catalogue list)
       └─ Show()
            │
   ┌────────┴─── Event handlers (SelectedIndexChanged / _Click) ───────────┐
   │                                                                        │
catalogueSelection() ─ SQL Q-CFG-002 (categories, DisplayOrder -1→9999)     │
categorySelection()  ─ SQL Q-CFG-003/004 (products or items by catalogue)   │
optionSelection()    ─ SQL Q-CFG-010..014 (+ hardcoded fabric options 8/28) │
attributeSelection() ─ SQL Q-CFG-008/009                                    │
value selections     ─ SQL Q-CFG-015..018 (CADMaterial/ModelSpecific)       │
model buttons        ─ SQL Q-CFG-020..026 (ModelList/CADImage3D)            │
group-code/base-mat  ─ SQL Q-CFG-030..045 (*GroupCodes, CADSchemes, mask)   │
   │                                                                        │
   └── pCon toolset (Items tab) ───────────────────────────────────────────┘
         getPConWorkspace(cataloguename) ─ pure string mapping
         GetPconPackageIdOnly() ─ SQL Q-CFG-050 (master item)  +  OLE DB O-CFG-001/002
         CreateNode()          ─ OLE DB O-CFG-010..014 (tGEOd_Node2D/3D)
         ClonePConPropertyClassOCD ─ OLE DB O-CFG-020..026 (tCOMd_Class/Property/PropValue)
         UpdatePConDataFile()  ─ Excel COM + SQL/OLE DB (UNKNOWN internals)
         GenerateVARCOND       ─ delegates to  SuperProductVarCondRelation form (see 05_Products)

WebConfigurator  [WC]
  button_loadOFDA_Click → loadOFDAXML → OFDAExportManager.LoadThread
  list_products_OFDA_SelectedIndexChanged → getOFDAFeaturesForProduct
        └─ OFDAExportManager.getOFDAFeautuesByProductXML(...)   (feature model)
  selectFeatureValue → updateWebConfigTemplate → text_template / text_parsed (URL)
  ApplyButton_Click → SQL Q-CFG-901 (UPDATE Product.WebDPSProduct)
```

There is **no repository/service layer**: every handler builds SQL inline and executes it directly
against a `SqlConnection` from `ConnectionFactory.CreateNewConnection(autoOpen: true)`, or against an
`OleDbConnection` for the pCon MDB files. "Models" are `ArrayList` parallel arrays held on the form
(e.g. `_catalogueIdList`, `_categoryIdList`, `_productIdList`, `_optionIdList`, `_atvalIdList`,
`_optvalIdList`, `_readOnlyCatalogues`, `_catalogueTypes`) — indexes are kept in lock-step with the
list-box item order.

---

## 4. SQL Analysis

> Convention: `Q-CFG-nnn` = SQL Server (`SqlCommand`). `O-CFG-nnn` = pCon **OLE DB / Jet MDB**
> (`OleDbCommand`). All statements are built by **string concatenation** with user/DB values inline —
> **SQL-injection-prone** (see §10). Only representative/keystone queries are quoted; many are
> near-identical `SELECT x / UPDATE x` pairs on the same table that differ only by column name.

### 4.1 SQL Server queries

**Q-CFG-001 — Catalogue picklist (per-user, active only)** — `initArrays` (CADMaintenance.cs:8692)
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly, Catalogue.CatalogueType
FROM PDMUserCatalogues puc INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId
WHERE puc.UserId = <AuthenticateUser.UserId> AND Catalogue.Status = 1
ORDER BY Catalogue.Name
```
WHY: builds the catalogue dropdown limited to catalogues the current user is granted, only `Status=1`
(active). `puc.ReadOnly` is cached in `_readOnlyCatalogues` and gates all edits (0 = editable — see
BR-CFG-004). `CatalogueType` cached for later pCon program-code lookups.

**Q-CFG-002 — Product categories for a catalogue** — `catalogueSelection` (9092)
```sql
SELECT DISTINCT pc.ProductCategoryId, od.ShortDescription,
  CASE WHEN cpc.DisplayOrder = -1 THEN 9999 ELSE cpc.DisplayOrder END AS cpcDO
FROM ProductCategory pc
  INNER JOIN CatalogueProductCategories cpc ON pc.ProductCategoryId = cpc.ProductCategoryId
  INNER JOIN OtherDescription od ON cpc.DescriptionId = od.DescriptionId AND od.LanguageId = 1
WHERE cpc.CatalogueId = <catalogueId>
ORDER BY cpcDO
```
WHY: category dropdown, English (`LanguageId=1`) descriptions, ordered by `DisplayOrder` with the
`-1` sentinel mapped to `9999` (sorts unassigned categories last — same rule as module 04). A
synthetic `< SP Components >` entry mapped to category **999** is appended in code (BR-CFG-006).

**Q-CFG-003 — Products list (Products tab, idx 0)** — `categorySelection` (9165 base; 9200 catalogue filter)
```sql
SELECT DISTINCT Product.ProductId, Product.Product, Product.ModelList, '' AS CADImage2D, Product.IsSuperProduct
FROM Product INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
WHERE pr.ProductCategoryId = <categoryId> AND Product.Product LIKE '%'
  AND (Product.ProductId IN (SELECT DISTINCT ProductId FROM Item
        INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId WHERE ci.CatalogueId = <catalogueId>) )
ORDER BY Product.Product
```
WHY: populate products in the chosen category that have released items in the catalogue. If
`UnreleasedCheck` is ticked an `OR … CatalogueItemsUnreleased …` clause is appended (BR-CFG-007).

**Q-CFG-004 — Items list (Items tab, idx 1)** — `categorySelection` (9168)
```sql
SELECT DISTINCT Item.ItemId AS ProductId, Item.Item AS Product, Item.CADImage3D AS ModelList,
       Item.CADImage2D, Product.IsSuperProduct
FROM Product INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
  INNER JOIN Item ON Product.ProductId = Item.ProductId
WHERE pr.ProductCategoryId = <categoryId> AND Product.Product LIKE '%'
  AND (Item.ItemId IN (SELECT ItemId FROM CatalogueItems WHERE CatalogueId = <catalogueId>) )
  AND Item.Status < 2
ORDER BY Item.Item
```
WHY: item-level list; `Item.Status < 2` excludes obsolete/held items; `item_filter` text can add
`AND Item.Item LIKE '%…%'` (or a `> '<x>'` range when the filter ends in `+`, BR-CFG-008). Note the
`ItemId` is aliased to `ProductId` so the same `_productIdList` array serves both tabs.

**Q-CFG-005 — SP Components pseudo-category (999)** — `categorySelection` (9180)
```sql
… INNER JOIN ItemComponents itco ON Item.ItemId = itco.SubItemId
  INNER JOIN Item parent_item ON itco.ItemId = parent_item.ItemId
  LEFT OUTER JOIN CatalogueProductRanges cpr ON pr.ProductRangeId = cpr.ProductRangeId AND cpr.CatalogueId = <catalogueId>
WHERE (pr.ProductCategoryId = 999 OR (999 = 999 AND cpr.ProductRangeId IS NULL)) …
```
WHY: when the user picks `< SP Components >` (id 999) the query walks `ItemComponents` to find
sub-items whose parent item is in the catalogue — i.e. components used inside Super Products
(BR-CFG-006). Consistent with module 04's "999 = SP Components" convention.

**Q-CFG-006 — Category CAD-planning override** — `categorySelection` (9298) & `CADMaintenance` (many)
```sql
SELECT CADPlanning FROM ProductCategory WHERE ProductCategoryId = <categoryId>
```
WHY: reads the per-category CAD planning prefix into `text_category_override`. Written back via
`button_update_category_override_Click`/`UpdateLayers` → `UPDATE ProductCategory SET CADPlanning = …`
(Q-CFG-031). Used as the CAD-layer prefix (BR-CFG-020).

**Q-CFG-008 — Attribute list for product** — `attributeSelection` (9801) with linked-attribute UNION (9807)
```sql
SELECT DISTINCT '0' AS linked, attr.AttributeId, attr.DisplayOrder, attr.AttributeType,
       attr.LayerNameList, attr.HideByDefault, attr.HasDependentOptions,
       CASE WHEN od.ShortDescription IS NULL THEN attr.Name ELSE od.ShortDescription END AS attr_name
FROM Attribute attr LEFT OUTER JOIN OtherDescription od
     ON attr.DescriptionId = od.DescriptionId AND od.LanguageId = 1 …
UNION SELECT DISTINCT '1' AS linked, … WHERE attr.AttributeId IN (-1, <text_linked_attr.Text>)
```
WHY: attributes applicable to the product, plus any explicitly *linked* attributes (`linked=1`). The
`-1` sentinel guarantees a valid `IN (…)` list even when no linked ids are entered (BR-CFG-010).

**Q-CFG-010 — Options for category** — `optionSelection` (9902)
```sql
SELECT DISTINCT opt.OptionId, opt.Name, opt.DisplayOrder
FROM OptionValue optval
  INNER JOIN CatalogueOptionValues cov ON optval.OptionValueId = cov.OptionValueId AND cov.CatalogueId = <catalogueId>
  INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId
WHERE opt.ProductCategoryId IN (<categoryId>, -1) AND optval.Status > -1
ORDER BY opt.DisplayOrder
```
WHY: options that have catalogue-scoped values in this category (or global category `-1`), excluding
values with `Status = -1`. Fabric global options are then force-added in code (BR-CFG-012).

**Q-CFG-011 — Option layer/hide/EOSlite** — `optionSelection` (9948)
```sql
SELECT opt.LayerNameList, pc.CADPlanning, opt.HideByDefault, opt.EOSLiteDisplayOrder
FROM [Option] opt LEFT OUTER JOIN ProductCategory pc ON pc.ProductCategoryId = <num6>
WHERE opt.OptionId = <optionId>
```
WHY: per-option CAD layer list + category planning prefix + default-hidden flag + EOS-lite ordering.
`[Option]` is bracket-quoted because `Option` is a reserved word.

**Q-CFG-012 — ModelSpecific/GroupCode-count probes** — `optionSelection` (9981, 9992)
```sql
SELECT COUNT(*) As cnt FROM OptionValue WHERE ModelSpecific IS NOT NULL AND OptionId = <optionId>
SELECT COUNT(*) As cnt FROM OptionGroupCodes WHERE OptionId = <optionId>
```
WHY: used to flag (in list drawing) whether an option already has model-specific data / group codes.

**Q-CFG-015 — Attribute-value list** — `attributeValueSelection` (10272)
```sql
SELECT DISTINCT atval.DisplayOrdinal, atval.AttributeValueId, atval.OrderCodeValue, atval.ModelSuffix,
       atval.ModelSpecific, atval.ProductMaskValue, atval.CADMaterial, atval.NewStatus, …
FROM AttributeValue atval …
```
**Q-CFG-016 — Option-value list (fabric-aware)** — `optionValueSelection` (10519)
```sql
SELECT DISTINCT optval.OptionId, optval.DisplayOrdinal, optval.OptionValueId, optval.OrderCodeValue,
       optval.ModelSpecific, …, optval.CADMaterial, optval.ImageFile, opt.IsFabric
FROM OptionValue optval INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId
  INNER JOIN CatalogueOptionValues … WHERE …
```
WHY: value grids carrying the CAD-relevant columns. In the Products tab the code flags values that
have **no** CAD material and are not `#`-suffixed and are not fabric-with-image, and are not
"castor"/"back support" by name, as needing attention (BR-CFG-013, line 10537).

**Q-CFG-017/018 — Read/write `CADMaterial`** — `SelectMaterial` (13206/13214), generic (14336/14370)
```sql
SELECT CADMaterial FROM <context>Value WHERE <context>ValueId = <id>          -- context = "Attribute" | "Option"
UPDATE <context>Value SET CADMaterial = '<mat>' WHERE <context>ValueId = <id>  -- or SET CADMaterial = NULL
```
WHY: the CAD material assignment for a value. `<context>` is concatenated from `"Attribute"` or
`"Option"` so one code path drives both `AttributeValue`/`OptionValue` (BR-CFG-014).

**Q-CFG-019 — Read/write `ModelSpecific`** — value model handlers (12372, 13499/13507, 13737/13745, generic 14127)
```sql
SELECT ModelSpecific, CADMaterial FROM AttributeValue WHERE AttributeValueId = <id>
UPDATE AttributeValue SET ModelSpecific = '<pipe-list>' WHERE AttributeValueId = <id>   -- OptionValue variant identical
```
WHY: `ModelSpecific` is a pipe-delimited model reference override at value level.

**Q-CFG-020 — Product model list read/write** — `updateProductModels` (11167, 11348, 11356)
```sql
SELECT Product.ModelList, pc.GroupCode
FROM Product INNER JOIN /* no override check required */ Product_Code pc ON Product.ProductCodeId = pc.ProductCodeId
WHERE Product.ProductId = <productId>
…
UPDATE Product SET ModelList = '<dwg1|dwg2|…>' WHERE ProductId = <productId>
```
**Q-CFG-021 — Item 3-D image read/write** — `updateProductModels` (11335/11343), `RemoveAllButton_Click` (12127/12135)
```sql
SELECT CADImage3D FROM Item WHERE ItemId = <itemId>
UPDATE Item SET CADImage3D = '<dwg…>' WHERE ItemId = <itemId>   -- or = NULL to clear
```
WHY: model references are stored as a **`|`-delimited string** in `Product.ModelList` (product level)
or `Item.CADImage3D` (item level). The list is edited by add/replace/remove buttons. The
`/* no override check required */` comment is preserved from source.

**Q-CFG-022 — LegacyItem lookup** — `label_infobar_DoubleClick`/`messageHandler` (9451)
```sql
SELECT LegacyItem FROM Item WHERE Item = '<item>'
```

**Q-CFG-030 — Layer scheme name read/write** — `UpdateLayers` (11607/11643)
```sql
SELECT LayerNameList FROM [<table>] WHERE <table>Id = <id>        -- table = Attribute | Option
UPDATE [<table>] SET LayerNameList = '<pipe-list>' WHERE <table>Id = <id>
```
**Q-CFG-031 — Category CADPlanning write** — `UpdateLayers` (11658)
```sql
UPDATE ProductCategory SET CADPlanning = '<first-2-chars-upper>' WHERE ProductCategoryId = <categoryId>
```
WHY: layer key assignment writes the pipe-delimited `LayerNameList`; the category prefix is forced to
the first 2 uppercase characters (BR-CFG-020).

**Q-CFG-035 — Group-code editor** — `BaseMaterialsAddButton_Click`/`Update`/`Remove` (15064, 15326, 15378, 15600/15626)
```sql
SELECT gc.GroupCode, od.ShortDescription, gc.DescriptionId
FROM <context>GroupCodes gc LEFT OUTER JOIN OtherDescription od ON od.DescriptionId = gc.DescriptionId AND od.LanguageId = 1
WHERE gc.Container = '<container>' AND gc.GroupCode = '<code>'
…
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable)
       VALUES (<newId>, 1, '<desc>', 'GroupCode')
INSERT INTO <context>GroupCodes (<context>Id, GroupCode, …) …
DELETE FROM OptionGroupCodes  WHERE OptionId    = <id> AND GroupCode = '<code>'
DELETE FROM AttributeGroupCodes WHERE AttributeId = <id> AND GroupCode = '<code>'
```
WHY: full CRUD over `AttributeGroupCodes` / `OptionGroupCodes` (feature grouping into named
containers/tabs for the planner). New descriptions get a fresh `DescriptionId` via
`SELECT TOP 1 DescriptionId FROM OtherDescription ORDER BY DescriptionId DESC` +1 (BR-CFG-021 — a
non-atomic max-id pattern; injection/race risk).

**Q-CFG-036 — Base-material domains** — `updateBaseMaterials` (14635/14666)
```sql
SELECT agc.GroupCode, od.ShortDescription, agc.Container, agc.Context
FROM AttributeGroupCodes agc LEFT OUTER JOIN OtherDescription od ON agc.DescriptionId = od.DescriptionId AND od.LanguageId = 1
WHERE agc.AttributeId = <id>
SELECT ogc.GroupCode, od.ShortDescription, ogc.Container, ogc.Context, ogc.DependentAttributeValueId, ogc.DependentOptionValueId
FROM OptionGroupCodes ogc … WHERE ogc.OptionId = <id>
```
WHY: shows group codes with their `Container`, `Context` and (for options) dependent value links.

**Q-CFG-040 — CAD schemes CRUD** — `updateBaseMaterials`/`BaseMaterialsAdd/Update/Remove` (14596, 15230, 15251, 15259, 15581)
```sql
SELECT SchemeName, SchemeId FROM CADSchemes WHERE CatalogueId = <catId> AND (Version = <pkgId> OR Version = <num2>)
INSERT INTO CADSchemes (SchemeId, CatalogueId, Version, SchemeName) VALUES (<id>, <catId>, <ver>, '<name>')
UPDATE CADSchemes SET SchemeName = '<name>' WHERE SchemeId = <id> AND CatalogueId = <catId> AND Version = <ver>
DELETE FROM CADSchemes WHERE SchemeId = <id> AND (Version = <pkgId> OR Version = <num3>) AND SchemeName = '<name>' AND CatalogueId = <catId>
```
WHY: `CADSchemes` maps a CAD layer scheme name to a `(CatalogueId, Version=pCon packageId)` pair.
`Version` is the resolved pCon package id (BR-CFG-050).

**Q-CFG-041 — Feature-domain suffixes / product mask** — (14709/14742, 15447/15466, 15490/15504, 15651/15665, 15683/15693)
```sql
SELECT ProductMaskKey FROM Attribute      WHERE AttributeId    = <id>
UPDATE Attribute      SET ProductMaskKey = '<key>'  WHERE AttributeId    = <id>   -- or NULL
SELECT CADSuffix      FROM OptionValue     WHERE OptionValueId  = <id>
UPDATE OptionValue    SET CADSuffix     = '<sfx>'  WHERE OptionValueId  = <id>   -- or NULL
```
WHY: `ProductMaskKey` (attribute) and `CADSuffix` (option value) drive OFML feature-domain suffixing.

**Q-CFG-042 — CADSuffix propagation across an option's values** — `ApplyDomainsToAll` (15140, 15150, 15175/15183)
```sql
SELECT opt.OptionId, opt.Name, optval.CADSuffix FROM OptionValue optval INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE optval.OptionValueId = <id>
SELECT optval.OptionValueId FROM OptionValue optval WHERE optval.OptionId = <optId> AND optval.Status < 2
UPDATE OptionValue SET CADSuffix = '<sfx>' WHERE OptionValueId = <id>
```
WHY: "Apply to all" copies one value's `CADSuffix` to every non-obsolete value (`Status < 2`) of the
same option (BR-CFG-041).

**Q-CFG-043 — HideByDefault write** — `attribute_display_SelectedIndexChanged` (15819), `option_display_…` (15859)
```sql
UPDATE Attribute SET HideByDefault = <idx> WHERE AttributeId = <id>
UPDATE [Option]  SET HideByDefault = <idx> WHERE OptionId    = <id> AND HideByDefault <= 9
```
WHY: default-visibility flag (0–9). The option variant guards `AND HideByDefault <= 9` (BR-CFG-042).

**Q-CFG-044 — CADPlaceProgram (product base materials list)** — `SetBaseButton_Click`/remove (14770, 15530/15540, 15709/15718)
```sql
SELECT CADPlaceProgram FROM Product WHERE ProductId = <productId>
UPDATE Product SET CADPlaceProgram = '<pipe-list>' WHERE ProductId = <productId>
```
WHY: `Product.CADPlaceProgram` holds a pipe-delimited list of default/base materials for placement.

**Q-CFG-045 — Material library / chromatic sequence** — `MaterialLibraryButton_Click` (16294, 16297, 16326, 16342, 16369)
```sql
UPDATE MaterialLibrary SET AdditionalRef = NULL
SELECT DISTINCT MaterialLibraryId, ImageFile FROM MaterialLibrary ORDER BY MaterialLibraryId
UPDATE MaterialLibrary SET AdditionalRef = '<ref>' WHERE MaterialLibraryId = <id>
SELECT optval.OptionValueId, optval.ImageFile FROM OptionValue optval INNER JOIN CatalogueOptionValues cov ON … WHERE optval.Status = 1
UPDATE OptionValue SET ChromaticSequence = <seq> WHERE OptionValueId = <id>
```
WHY: rebuilds `MaterialLibrary.AdditionalRef` and assigns `OptionValue.ChromaticSequence` (colour
ordering) from image order.

**Q-CFG-050 — Master-item package resolution helper** — `GetPconPackageIdOnly` (18872), `getPConPrefixLengthByCategory` (19054)
```sql
SELECT Item.ItemId, Product.Product, Item.Notes, Item.Item
FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId
  INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
WHERE pr.ProductCategoryId = <categoryId> AND Item.CADImage2D = 'master'
```
WHY: finds the **master item** of a category (`Item.CADImage2D = 'master'`). `Item.Notes` (a
comma-list) yields the **article prefix length** used to compute the pCon article/geometry lookup key
(BR-CFG-051/052).

**Q-CFG-060 — Image validation/archival** — `ValidateProductImages`/`Archive…` (17000, 16720, 16834–16874, 17124–17148)
```sql
SELECT DISTINCT Product.ProductId, Product.Product, Product.ImageFile, pr.ProductCategoryId, Product.ProductCodeId
FROM Product INNER JOIN ProductRange pr ON …
UPDATE Product           SET ImageFile          = REPLACE(ImageFile, 'Images\Products\<old>', 'Images\Products\<new>') WHERE ImageFile LIKE '%<old>%'
UPDATE AttributeValue    SET ImageFile          = … ; UPDATE OptionValue SET ImageFile = … ;
UPDATE CatalogueProductCategories SET ImageFile = … ; UPDATE Catalogue SET ImageFile = … ;
UPDATE ProductRange      SET ImageFile          = … ; UPDATE HandbookProducts SET AlternateImageFile = …
```
WHY: bulk image-path maintenance across all image-bearing tables. `LIKE '%<old>%'` + `REPLACE` is
literal path substitution.

**Q-CFG-070 — Get materials (T150 finishes)** — `GetMaterialsToolStripMenuItem_Click` (16525), `UpdateGMaterials` (17329)
```sql
SELECT DISTINCT CADMaterial FROM OptionValue WHERE CADMaterial LIKE '%S_T150%' ORDER BY CADMaterial
SELECT DISTINCT optval.OptionValueId, optval.ImageFile, optval.CADMaterial
FROM OptionValue optval INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId
WHERE opt.IsFabric = 2 AND optval.ImageFile IS NOT NULL ORDER BY optval.ImageFile
```
WHY: `IsFabric = 2` = **colour** options (see 09_Options); used to sync gMaterials.

### 4.2 pCon OLE DB / Jet MDB queries

All use `Provider=Microsoft.Jet.OLEDB.4.0;Data Source=<pConPath>WS\<workspace>\pcr_data_<db>.mdb`
where `<db>` ∈ {`geo_odb`, `com_ocd`}, `pConPath = C:\HermanMillerOFML\Staging\HermanMiller\`,
and `<workspace>` from `getPConWorkspace` (BR-CFG-060).

**O-CFG-001 — Geometry package id by object name** — `GetPconPackageIdOnly` (18936)
```sql
SELECT obj.geo_PackageID, pkg.reg_ProgramCode
FROM tGEOd_Object obj INNER JOIN tGEOd_Package pkg ON obj.geo_PackageID = pkg.geo_PackageID
WHERE obj.geo_ObjectName LIKE 'W_<itemPrefix>%'
```
**O-CFG-002 — Commercial package id by article code** — `GetPconPackageIdOnly` (18960)
```sql
SELECT art.com_PackageID, pkg.reg_ProgramCode
FROM tCOMd_Article art INNER JOIN tCOMd_Package pkg ON art.com_PackageID = pkg.com_PackageID
WHERE art.com_ArticleCode LIKE '<articleCode>%'
```
WHY: resolve the pCon **package id** (and its `reg_ProgramCode` name) either from geometry objects
(context `geo_odb`, object prefixed `W_`) or from commercial articles (context anything else). The id
chosen is the **most frequently matched** across the category's master-item prefixes (BR-CFG-053).

**O-CFG-010 — Layer list for a package** — `FixedLayers…`/`updateBaseMaterials` (14609)
```sql
SELECT geo_LayerId, geo_LayerName FROM tGEOd_Layer WHERE geo_PackageID = <pconPackageId>
```

**O-CFG-011..014 — Geometry node create/lookup** — `CreateNode` (19180 ff.)
```sql
SELECT node.geo<2D|3D>_NodeID FROM tGEOd_Object obj INNER JOIN tGEOd_Node<2D|3D> node
  ON obj.geo_ObjectID = node.geo_ObjectID
WHERE obj.geo_ObjectID = <objId> AND node.geo<2D|3D>_NodeName = '<name>'
  AND node.geo<2D|3D>_ParentNodeID = <parentId>
  [AND node.geo<2D|3D>_NodeType<2D|3D> = 'macro' AND …NodeRefMF='hmx' AND …NodeRefPK='<pkg>' AND …NodeRefName='M_<name>']
INSERT INTO tGEOd_Node<2D|3D> (geo_ObjectID, geo<2D|3D>_ParentNodeID, geo<2D|3D>_NodeName [, geo<2D|3D>_Visibility]
       [, …NodeType, …NodeRefMF, …NodeRefPK, …NodeRefName]) VALUES (…)
-- plus OFML class-ref nodes: NodeType='clsref', NodeRefMF='ofml', NodeRefPK='go', NodeRefName='<GoY…>', NodeRefParam='<param>'
```
WHY: `CreateNode` builds the pCon geometry node tree (2-D or 3-D) — top nodes, `clsref` nodes that
reference OFML `go` classes (for translations `GoYLTransSynchr…`), and `macro` nodes referencing HM
manufacturer packages (`hmx`). Successful ids are cached in `cached2DNodeKeys/Ids`,
`cached3DNodeKeys/Ids` (BR-CFG-061). `_C`/`_D` suffixes map to `_A`/`_B` and add a `_secondary`
node for secondary finishes (BR-CFG-062).

**O-CFG-020..026 — Clone a pCon property class (OCD)** — `ClonePConPropertyClassOCDToolStripMenuItem_Click` (21663 ff.)
```sql
SELECT cls.com_ClassID, pkg.com_PackageID FROM tCOMd_Class cls INNER JOIN tCOMd_Package pkg ON cls.com_PackageID = pkg.com_PackageID
  WHERE cls.com_ClassName = '<src>' AND pkg.reg_ProgramCode = '<programCode>'
SELECT cls.com_ClassID FROM tCOMd_Class cls WHERE cls.com_ClassName = '<dst>' AND cls.com_PackageID = <pkgId>
INSERT INTO tCOMd_Class (com_PackageID, com_ClassName) VALUES (<pkgId>, '<dst>')
SELECT com_PropertyID, com_PropName, com_PropPosition, com_TextID, com_PropDigits FROM tCOMd_Property WHERE com_ClassID = <srcClassId>
INSERT INTO tCOMd_Property (com_ClassID, com_PropName, com_PropPosition, com_TextID, com_PropDigits) VALUES (<dstClassId>, '<name>', <pos>, <textId>, <digits>)
SELECT com_PropValPosition, com_TextID, com_RelObjID, com_PropValueFrom FROM tCOMd_PropValue WHERE com_PropertyID = <srcPropId>
INSERT INTO tCOMd_PropValue (com_PropertyID, com_PropValPosition, com_TextID, …) …
```
WHY: deep-copies a commercial property class (class → properties → property values) inside the
`com_ocd` MDB, so a new variant-condition class can be seeded from an existing one (BR-CFG-070). This
is the clearest **variant-condition build** path in the file.

**O-CFG-030 — Property-class name lookup for a property** — `getLinkedAttributeValueData`/helpers (22460, 22545)
```sql
SELECT art.com_ArticleCode, class.com_ClassName, prop.com_PropName
FROM ((tCOMd_Article art INNER JOIN tCOMd_ArticleClass ac ON art.com_ArticleID = ac.com_ArticleID)
  INNER JOIN tCOMd_Class class ON ac.com_ClassID = class.com_ClassID)
  INNER JOIN tCOMd_Property prop ON class.com_ClassID = prop.com_ClassID
SELECT cls.com_ClassName FROM tCOMd_Property prop INNER JOIN tCOMd_Class cls ON prop.com_ClassID = cls.com_ClassID
  WHERE prop.com_PropName = '<name>' AND cls.com_PackageID = <ocdPackageId>
```
WHY: resolves which article/class/property a feature belongs to, used by the metatype exporter.

### 4.3 WebConfigurator SQL **[WC]**

**Q-CFG-901 — Apply web template to products** — `ApplyButton_Click` (WebConfigurator.cs ~1410)
```sql
UPDATE Product SET WebDPSProduct = '<template>' WHERE ProductId IN (
  SELECT ProductId FROM Item WHERE Item LIKE '<filter>' [AND Item NOT LIKE '<exclude>']
       [AND Item NOT LIKE '%-%']
  UNION SELECT -1)
```
WHY: writes the generated configuration template to `Product.WebDPSProduct` for every product whose
item matches the filter. `*`→`%`; a ` !` token splits an exclusion; if the filter has no `-`, items
containing `-` are excluded; `UNION SELECT -1` guarantees a valid (never-empty) `IN` list
(BR-CFG-901..904).

---

## 5. Data Model

### 5.1 SQL Server tables (CAD-relevant columns)

| Table | Key columns (as used here) | Meaning / CAD role |
|-------|----------------------------|--------------------|
| `Catalogue` | `CatalogueId` PK, `Name`, `Status` (1=active), `CatalogueType`, `ImageFile` | Catalogue picklist source. |
| `PDMUserCatalogues` | `UserId`, `CatalogueId`, `ReadOnly` | Per-user grant; `ReadOnly = 0` ⇒ **editable** (see §6). |
| `ProductCategory` | `ProductCategoryId` PK, `Name`, `CADPlanning` | `CADPlanning` = 2-char CAD layer prefix override. |
| `CatalogueProductCategories` | `CatalogueId`, `ProductCategoryId`, `DescriptionId`, `DisplayOrder`(-1→9999), `ImageFile` | Category ordering + description. |
| `ProductRange` | `ProductRangeId` PK, `ProductCategoryId`, `ImageFile` | Links product→category. |
| `Product` | `ProductId` PK, `Product`, `ProductRangeId`, `ProductCodeId`, `IsSuperProduct`, **`ModelList`** (pipe-list of dwg refs), **`CADPlaceProgram`** (pipe-list base materials), `ImageFile`, `DescriptionId`, **`WebDPSProduct`** (web template) | Product-level CAD + web config. |
| `Product_Code` | `ProductCodeId` PK, `GroupCode` | Group code join for model naming. |
| `Item` | `ItemId` PK, `Item`, `ProductId`, `Status`(<2 shown), **`CADImage3D`** (pipe-list 3-D dwg), **`CADImage2D`** (`'master'` flags the master item), `Notes` (comma-list; prefix length), `LegacyItem` | Item-level CAD; `Notes` carries the pCon article-prefix length. |
| `ItemComponents` | `ItemId`, `SubItemId` | BOM walk for SP Components (cat 999). |
| `CatalogueItems` / `CatalogueItemsUnreleased` | `CatalogueId`, `ItemId` | Catalogue membership (released / unreleased). |
| `Attribute` | `AttributeId` PK, `Name`, `DisplayOrder`, `AttributeType`, **`LayerNameList`** (pipe-list), `HideByDefault`(0–9), `HasDependentOptions`, **`ProductMaskKey`**, `DescriptionId` | Attribute CAD layers + mask key. |
| `AttributeValue` | `AttributeValueId` PK, `AttributeId`, `OrderCodeValue`, `DisplayOrdinal`, **`CADMaterial`**, **`ModelSpecific`** (pipe-list), **`ModelSuffix`**, **`ProductMaskValue`**, `NewStatus`, `ImageFile`, `Name` | Value-level CAD material / model override. |
| `[Option]` | `OptionId` PK, `Name`, `ProductCategoryId`(-1=global), `DisplayOrder`, **`LayerNameList`**, `HideByDefault`(≤9), `EOSLiteDisplayOrder`, **`IsFabric`** (0/1=type/2=colour) | Bracket-quoted (reserved word). |
| `OptionValue` | `OptionValueId` PK, `OptionId`, `OrderCodeValue`(may end `#`), `DisplayOrdinal`, `Status`(<2 shown), **`CADMaterial`**, **`CADSuffix`**, **`ModelSpecific`**, **`ChromaticSequence`**, `ImageFile`, `Name` | Value-level CAD material / suffix / colour order. |
| `CatalogueOptionValues` / `CatalogueAttributeValues` | `CatalogueId`, `OptionValueId`/`AttributeValueId` | Catalogue-scoped value membership. |
| `AttributeGroupCodes` | `AttributeId`, `GroupCode`, `Container`, `Context`, `DescriptionId`, `DisplayOrder`, `ContainerDescriptionId` | Feature grouping (planner tabs). |
| `OptionGroupCodes` | `OptionId`, `GroupCode`, `Container`, `Context`, `DescriptionId`, `DependentAttributeValueId`, `DependentOptionValueId`, `DisplayOrder` | As above + dependency links. |
| `CADSchemes` | `SchemeId`, `CatalogueId`, `Version` (= pCon packageId), `SchemeName` | CAD layer-scheme naming per catalogue+package version. |
| `OtherDescription` | `DescriptionId`, `LanguageId`(1=English), `ShortDescription`, `RelatedTable`('GroupCode') | Description store for group codes etc. |
| `MaterialLibrary` | `MaterialLibraryId` PK, `ImageFile`, `AdditionalRef` | Material library / gMaterials source. |
| `FabricBands` | `OptionValueId`, `Application`, `PriceBand` | Referenced by pCon price push (Q-CFG in UpdatePConData). |
| `HandbookProducts` | `AlternateImageFile` | Image-path maintenance target. |
| `PDMUserPrivileges` | `UserId`, `SkypeName` (reused as pCon workspace **preferences** string) | `SkypeName` column is repurposed to store the user's pCon workspace path prefs (`readPConWorkspaceSettings`, 24299). |

### 5.2 pCon (Access/Jet MDB via OLE DB) tables

Located under `C:\HermanMillerOFML\Staging\HermanMiller\WS\<workspace>\pcr_data_<db>.mdb`.
Two databases: **`geo_odb`** (geometry) and **`com_ocd`** (commercial / variant conditions).

| MDB / table | Key columns (as used) | Meaning |
|-------------|-----------------------|---------|
| `geo_odb` · `tGEOd_Package` | `geo_PackageID` PK, `reg_ProgramCode` | Geometry package registry; `reg_ProgramCode` = program/package name. |
| `geo_odb` · `tGEOd_Object` | `geo_ObjectID` PK, `geo_PackageID` FK, `geo_ObjectName` (`W_<item>…`) | Geometry object per item (name prefixed `W_`). |
| `geo_odb` · `tGEOd_Node2D` / `tGEOd_Node3D` | `geo2D_NodeID`/`geo3D_NodeID` PK, `geo_ObjectID` FK, `geo?D_ParentNodeID` (tree), `geo?D_NodeName`, `geo?D_NodeType?D` ('top'/'clsref'/'macro'), `geo?D_NodeRefMF` ('ofml'/'hmx'), `geo?D_NodeRefPK` ('go'/`<pkg>`), `geo?D_NodeRefName`, `geo?D_NodeRefParam`, `geo?D_Visibility` | Geometry node tree for a configured item; class-refs point at OFML `go` classes, macros at HM packages. |
| `geo_odb` · `tGEOd_Layer` | `geo_LayerId`, `geo_LayerName`, `geo_PackageID` FK | Layer catalogue per package. |
| `com_ocd` · `tCOMd_Package` | `com_PackageID` PK, `reg_ProgramCode` | Commercial package registry. |
| `com_ocd` · `tCOMd_Article` | `com_ArticleID` PK, `com_ArticleCode`, `com_PackageID` FK | Commercial article (order-code). |
| `com_ocd` · `tCOMd_ArticleClass` | `com_ArticleID` FK, `com_ClassID` FK | Article↔class link. |
| `com_ocd` · `tCOMd_Class` | `com_ClassID` PK, `com_PackageID` FK, `com_ClassName` | **Variant-condition / property class**. |
| `com_ocd` · `tCOMd_Property` | `com_PropertyID` PK, `com_ClassID` FK, `com_PropName`, `com_PropPosition`, `com_TextID`, `com_PropDigits` | Property (feature) of a class. |
| `com_ocd` · `tCOMd_PropValue` | `com_PropertyID` FK, `com_PropValPosition`, `com_TextID`, `com_RelObjID` (relation link), `com_PropValueFrom` | Property **value** rows; `com_RelObjID` links to a relation object — the **variant-condition relation** mechanism. |

**Relationships / flags of note**
- Geometry: `tGEOd_Package 1—* tGEOd_Object 1—* tGEOd_Node{2D,3D}` (self-referencing via `ParentNodeID`).
- Commercial: `tCOMd_Package 1—* tCOMd_Class 1—* tCOMd_Property 1—* tCOMd_PropValue`;
  `tCOMd_Article *—* tCOMd_Class` through `tCOMd_ArticleClass`.
- `com_RelObjID` on a property value is the **relation object** reference (variant condition). The
  full relation table (`tCOMd_Relation*`) structure is **UNKNOWN** — the code only reads/writes
  `com_RelObjID` as an int and does not otherwise touch a relation table in the ranges read.
- Node type triad: `top` (root), `clsref` (references an OFML `go` class + param), `macro`
  (references an HM `hmx` package macro). Manufacturer codes are hardcoded: `ofml`/`go` for OFML
  classes, `hmx` for Herman Miller macros.

---

## 6. Business Rules

> Every rule below is verified from a specific line unless tagged `UNKNOWN`. IDs are stable.

**Permissions & entry**
- **BR-CFG-001** The CAD Maintenance menu button is shown only if `AuthenticateUser.CADMaintenance`
  is true (MainMenu.cs:3058).
- **BR-CFG-002** The Web Configurator button is shown only if `AuthenticateUser.CoreMaintenance` is
  true **and** the connected server is **not** eoscloud (MainMenu.cs:3078). On eoscloud (and for
  non-Core users) `ImportMaterialsInToCSIToolStripMenuItem` is also disabled.
- **BR-CFG-003** Only one instance of the OFDA Export Manager **or** Web Configurator may be open at
  a time, enforced by `Global.ofdaManagerOrWebConfigActive` (MainMenu.cs:2979; cleared on close).
- **BR-CFG-004** Editing is allowed only when the selected catalogue is **not** read-only
  (`_readOnlyCatalogues[idx] == 0`) **and** `!Global.readOnlyDBConnection`. This compound test gates
  virtually every add/replace/remove/enable in the form (10009, 11481, 12444, 20971, 21029, …).
- **BR-CFG-005** A hardcoded **pCon-creator allow-list** (`_pConCreatorUsers` = `DBACW8, MRC4TP,
  KSBTG5, VSBBRW, SIAOCA, BSCDGU, SECQAF, AICI85, EHD2I1, RNAMH8, DJ1169`, initArrays:8680) lets
  those Windows accounts edit even in a read-only catalogue (`… OR _pConCreatorUsers.Contains(
  Environment.UserName.ToUpper())`, 10062). All other users obey BR-CFG-004.

**Catalogue / category / product selection**
- **BR-CFG-006** A synthetic **`< SP Components >`** category (id **999**) is always appended to the
  category list; selecting it walks `ItemComponents` to list sub-items whose parent item is in the
  catalogue (Q-CFG-005). Consistent with module 04.
- **BR-CFG-007** Unreleased items are excluded unless `UnreleasedCheck` is ticked, which appends
  `OR … CatalogueItemsUnreleased …` to the product/item query (9187/9195/9203).
- **BR-CFG-008** Item filter (`item_filter`, Items tab): trailing `+` switches to a range/prefix
  match `(Item LIKE '%x%' OR Item > 'x')`; otherwise `*`→`%` substring match (9640+). Items are also
  constrained to `Item.Status < 2`.
- **BR-CFG-009** Category ordering uses `DisplayOrder` with `-1 → 9999` (unassigned last), English
  descriptions only (`LanguageId = 1`). Duplicate category names are disambiguated by appending
  ` (ProductCategoryId)` (9101).
- **BR-CFG-010** The attribute list always includes the sentinel `-1` in its linked-attribute
  `IN (-1, …)` clause so the query is valid when no linked ids are entered (9807).

**Fabric / option special-casing**
- **BR-CFG-011** `[Option]` and `[Attribute]` are always bracket-quoted because `Option` is a T-SQL
  reserved word (pervasive).
- **BR-CFG-012** In the **Products tab only** (`TabControl1.SelectedIndex == 0`), global fabric
  options are force-added to the option list even if not returned by Q-CFG-010:
  **8 = "Fabric type (global)"**, **28 = "Fabric colour (global)"**; and when
  `SecondaryFabricCheck` is ticked, **3344 = "2nd fabric type"**, **3346 = "2nd fabric colour"**
  (optionSelection:9917-9945). Fabric-type additions (8, 3344) are suppressed when `RevitCheck` is
  ticked.
- **BR-CFG-013** A value is flagged as "needs CAD attention" (Products tab) when it has **no**
  `CADMaterial`, its `OrderCodeValue` does **not** end in `#`, it is not a fabric-with-image
  (`ImageFile` empty OR `IsFabric = 0`), and its name contains neither "castor" nor "back support"
  (10537). These name/`#` exclusions are hardcoded.
- **BR-CFG-070-flag** `IsFabric`: `0` = non-fabric, `1` = fabric **type**, `2` = fabric **colour**
  (used by Get/UpdateGMaterials: `WHERE opt.IsFabric = 2`).

**CAD material / geometry storage**
- **BR-CFG-014** `CADMaterial` is stored per value in `<Attribute|Option>Value.CADMaterial`; the same
  code path handles both by concatenating the context word (`"Attribute"`/`"Option"`) into table and
  column names (Q-CFG-017). Setting empty writes `NULL`.
- **BR-CFG-015** Model references are stored as **pipe-delimited strings**: `Product.ModelList`
  (product), `Item.CADImage3D` (item 3-D), and value-level `ModelSpecific`. Add/replace/remove
  operations edit the string, not a child table.
- **BR-CFG-016** `Item.CADImage2D = 'master'` marks the **master item** of a category — the anchor
  used to resolve pCon package ids and article-prefix lengths (Q-CFG-050).
- **BR-CFG-017** Add-model dialogs **reject** files that are not `.dwg` or that do not reside under
  one of the sanctioned resource shares: `dwgRepository` (`\\FSCHIP01v\PDM Resources\Symbols\`),
  `dwgRepositoryZMap` (`Z:\Symbols\`), `revitRepositoryINTL` (`\\FSCHIP01v\PDM Resources\Revit\`),
  `revitRepositoryNA` (`\\NETSHARES\MKTGTECH$\…\Revit_Family\`) (11250, 13422, 13660). Paths are
  stored **relative** (the repository prefix is stripped, upper-cased).
- **BR-CFG-018** Adding a model to a **Super Product** prompts a confirmation warning that models
  should be associated at component level (11143).
- **BR-CFG-020** `LayerNameList` is a pipe-delimited layer-key list per Attribute/Option; the
  category `CADPlanning` prefix is forced to the **first two characters, upper-cased** (11658).
- **BR-CFG-021** New group-code descriptions get a `DescriptionId` via
  `SELECT TOP 1 DescriptionId … ORDER BY DescriptionId DESC` **+1** (non-atomic; 15053, 15317) and are
  inserted into `OtherDescription` with `RelatedTable = 'GroupCode'`, `LanguageId = 1`. A container
  needs **≥3 characters** or the add is rejected (15031, 15295).
- **BR-CFG-041** "Apply to all" copies a value's `CADSuffix` to every **non-obsolete**
  (`Status < 2`) value of the same option (Q-CFG-042).
- **BR-CFG-042** `HideByDefault` write for options guards `AND HideByDefault <= 9` (15859); the
  attribute variant has no guard.
- **BR-CFG-043** Base materials are stored pipe-delimited in `Product.CADPlaceProgram`; remove
  strips the selected token `+ "|"` (15718).

**pCon / OFML linkage**
- **BR-CFG-050** `CADSchemes.Version` **is** the resolved pCon package id; a scheme is keyed on
  `(SchemeId, CatalogueId, Version)` and matched against either the current package id or a second
  version (Q-CFG-040).
- **BR-CFG-051** pCon article-prefix length comes from `Item.Notes`: the first comma-token, and only
  if ≤2 chars and integer, is treated as the prefix length; a 1–2 char integer token anywhere in the
  comma-list is also accepted (`getArticlePrefixLength`, 19092-19112). Falls back to the category's
  master-item value (`getPConPrefixLengthByCategory`) when none found.
- **BR-CFG-052** If the resolved prefix length exceeds the item length, a warning box is shown and
  the whole item code is used instead (18898).
- **BR-CFG-053** `GetPconPackageIdOnly` resolves a package id by matching every category master-item
  prefix against the MDB (`W_<prefix>%` in geometry, or `<code>%` in commercial with a 2-pass `.`→`%`
  fallback) and picks the id with the **highest match count** (18990-19010). Returns `-1` when
  nothing matches; `-1` is only surfaced (debug box) for user `dbacw8` and only when not suppressed
  (19012).
- **BR-CFG-060** `getPConWorkspace`: if the user's `pConWorkspace` preference = `"auto"`, the
  workspace is `"Seating"` when the catalogue name (lower-cased) contains any of `seating`,
  `naughtone`, `collection`, `ancillary`, `paragraph`; otherwise `"Tables"`. A non-`auto` preference
  is used verbatim (24270).
- **BR-CFG-061** `CreateNode` caches created geometry node ids by key
  `objectId~parentId~nodename` in `cached2DNodeKeys/Ids` or `cached3DNodeKeys/Ids` to avoid
  re-inserting (19347-19357).
- **BR-CFG-062** Translation-driven class-ref nodes: a translation of the form `GoYLT…:param` is
  rewritten `GoYLT → GoYLTransSynchr`; suffixes `_C`/`_D` add a `_secondary` node and remap to
  `_A`/`_B` for the parent go-class ref (19183-19290).
- **BR-CFG-063** Node manufacturer/package refs are hardcoded: OFML class refs use
  `MF='ofml', PK='go'`; macro refs use `MF='hmx', PK='<packagename>'`, `NodeRefName = 'M_'+name`
  (prefix skipped if already present) (19236, 19300+).
- **BR-CFG-070** `ClonePConPropertyClassOCD` deep-copies `tCOMd_Class → tCOMd_Property →
  tCOMd_PropValue` within `com_ocd`; a new class must have a **unique name** or it is rejected
  ("New Property Class should have a unique name", 21809). `com_RelObjID` is copied only when non-empty
  (21750).
- **BR-CFG-071** `GenerateVARCONDForPAPRICING` does **not** itself build VARCOND SQL — it opens the
  `SuperProductVarCondRelation` form pre-seeded with the current `defaultCatalogueId`,
  `defaultCategoryId` and `UnreleasedCheck` state (21942-21950). The actual VARCOND relation build is
  in that form (documented in **05_Products**).
- **BR-CFG-072** Program codes for the current catalogue are obtained from
  `PriceMaintenance.getPConProgramCodes(catalogueName, "programCodes", catalogueType)` (19394, 21655,
  22722) — a cross-module dependency (body in module 18 Pricing).
- **BR-CFG-073** The pCon-data XLS import (`UpdatePConDataFile`) auto-picks up sibling language files:
  if the chosen file ends `_en.xls`, it also opens `_fr.xls`/`_de.xls`/`_nl.xls` when present, mapping
  them to `LanguageId` 2/5/9 respectively; the base English file is `LanguageId 1` (18081-18111).
  Files whose name (minus `_`) contains `priceexport` are treated as price files. Default open dir
  `C:\Projects\pCon\`. Full row-processing logic **UNKNOWN** (only the head was read).

**Environment / visual**
- **BR-CFG-080** `initialiseGui` colour-codes the form background by connected DB/server:
  `PDM_Prototipo_Test`→DarkSeaGreen; `DBCHIP08v`/`DBIA01SQLSV`/`DBIA08SQPDMLV`→LightGoldenrodYellow;
  primary PDM DB→system Control; `PDMPublished`→BurlyWood; `PDMFrozen`→LightBlue; `PDMPOSH`@`DBHONP06v`
  →LightGoldenrodYellow; any `eoscloud` server→Plum; else DarkSeaGreen (8631-8663). Pure visual cue
  of which environment is connected.
- **BR-CFG-081** Default catalogue selection: `AuthenticateUser.DefaultCatalogueId` if present in the
  user's list, else the first entry (8703-8713).
- **BR-CFG-082** Revit auto-assign (`RevitCheck`) is made **visible only for user `dbacw8`** in the
  Products tab (21023).

**Tab-mode visibility (all in `TabControl1_SelectedIndexChanged`, 20921)**
- **BR-CFG-090** Items tab (idx 1): shows the pCon panels (`PanelpCon*`, `panel_metatype_data`),
  the metatype/VARCOND/2D/3D-reference menu items, `item_filter`, `check_usemacros`,
  `check_multiplenodes`, `check_excludefromexport`; hides CET-only controls (`RevitCheck`,
  `FilterCheck`, `FabTypeCheck`, `MissingCADMaterialCheck`, `SecondaryFabricCheck`, `ReportButton`,
  optval model buttons, category-override editor).
- **BR-CFG-091** Products tab (idx 0): inverse of BR-CFG-090 — shows CET controls and category
  override; hides pCon toolset. Copy-model button text switches between
  "…Multiple Items" / "…Multiple Products".
- **BR-CFG-092** In the Items tab, if `pConWorkspace` is not `"auto"` and the workspace folder does
  not exist on disk, the workspace label is coloured dark red as a warning (20940).

**WebConfigurator [WC]**
- **BR-CFG-901** Apply requires a non-empty **product filter** and a non-empty **template**, else a
  message prompts for the missing one (ApplyButton_Click).
- **BR-CFG-902** Filter transforms: `*` → `%`; a ` !` token splits off an exclusion
  (`AND Item NOT LIKE '<x>'`); if the filter contains no `-`, hyphenated items are excluded
  (`AND Item NOT LIKE '%-%'`).
- **BR-CFG-903** `UNION SELECT -1` is appended so the `IN (…)` set is never empty.
- **BR-CFG-904** The built URL is fixed to
  `https://exdevl01.hermanmiller.com:8443/…/EMEA_SEATING_40_WEB/…/1-1010_EUR/product/<productXml>?<features>`;
  when `check_noconfig` is ticked, `&noconfig=1` is appended (updateWebConfigTemplate:1071-1085).
- **BR-CFG-905** Feature dependency: `selectFeatureValue` shows/hides and re-stacks downstream
  feature rows based on the currently selected feature's `{ssId}` group, so only compatible children
  remain visible (1098-1200).
- **BR-CFG-906** Features whose underlying element is an **Attribute with children** are rendered in
  **bold** (`featureIsAttributeWithChildren`, updateWebConfigTemplate:1010+).
- **BR-CFG-907** The **>>>** button opens the URL specifically in **`chrome.exe`** (hardcoded).

---

## 7. Hidden Logic

- **HL-1** The `<context>`-string trick (`"Attribute"` / `"Option"`) is used throughout to build
  both table **and** column names by concatenation (`<context>Value`, `<context>ValueId`,
  `<context>GroupCodes`). A single method services two entities — but it also means table/column
  identifiers are assembled from runtime strings.
- **HL-2** `Item.Notes` is silently overloaded to store the pCon **article-prefix length** (a small
  integer in a comma-list). There is no dedicated column; the meaning is entirely by convention
  (BR-CFG-051).
- **HL-3** `PDMUserPrivileges.SkypeName` is repurposed to hold the user's **pCon workspace path
  preferences** (`readPConWorkspaceSettings`, 24299) — a column name with nothing to do with its use.
- **HL-4** In Q-CFG-004 the item `ItemId`/`Item` are **aliased** to `ProductId`/`Product` so the same
  `_productIdList` array and downstream code serve both Product and Item tabs — the "product list"
  actually holds items in tab 1.
- **HL-5** pCon package-id resolution is a **most-frequent-wins vote** across all master-item prefixes
  in a category, not a deterministic lookup (BR-CFG-053).
- **HL-6** The commercial article match uses a **two-pass** strategy: first the raw code, then with
  every `.` replaced by `%` (wildcard) — so dotted article codes still resolve (19282-19296).
- **HL-7** `CreateNode` will, for `_C`/`_D` finish variants, silently create an extra `_secondary`
  geometry node and remap the go-class ref — a non-obvious secondary-finish geometry duplication
  (BR-CFG-062).
- **HL-8** `-1` return from `GetPconPackageIdOnly` is only visibly reported (debug dialog) for the
  single developer account `dbacw8` (19012) — other users get a silent no-op.
- **HL-9** Errors in `CreateNode`/exporters open a custom `debug_form` dialog dumping the failing SQL
  and all parameters (19352) rather than logging — a developer-diagnostic surfaced to end users.

---

## 8. UI Behaviour

- The form is a dense multi-panel workbench: catalogue/category/product selectors on the left,
  attribute/option lists, attribute-value/option-value grids, model-reference lists with drag-drop,
  and (Items tab) a pCon metatype panel. Many list boxes are **owner-drawn** (`*_DrawItem`,
  `*_MeasureItem`) to colour/annotate rows (e.g. products without models, attributes with layers).
- **Drag-and-drop** is used to add/remove model references and to move layer assignments between
  attribute/option layer lists (`*_DragOver`, `*_DragDrop`, `*_MouseDown`).
- The mode tabs (`TabControl1`) reshape the whole UI (BR-CFG-090/091); this is guarded by `_loaded`
  so it does nothing during construction.
- Editable buttons are enabled/disabled live by the BR-CFG-004 read-only test on every selection
  change.
- Long operations set `Cursor = Cursors.WaitCursor` and post progress through
  `updateStatusEvent`/`updateStatus`; special status prefixes (`VARCOND:`,
  `GENERATE_VARCOND_ABORTED`, `[update_img]…`, "Update complete", "OFDA update complete") drive label
  and image updates (8469-8620).
- Almost every handler wraps its body in `try/catch` that shows the raw exception via
  `Interaction.MsgBox(ex.ToString())` — a VB-style "show the stack trace to the user" pattern.
- **[WC]** WebConfigurator dynamically **generates** its feature Labels + ComboBoxes at runtime from
  the OFDA XML (`getOFDAFeaturesForProduct`), positions them by index, and re-lays them out as
  dependencies change. It uses heavy VB **late binding** (`NewLateBinding.LateGet/LateSet`) to talk to
  those controls.

---

## 9. Dependencies

- **Data access:** `ConnectionFactory.CreateNewConnection` (SQL Server); `System.Data.OleDb` +
  `Microsoft.Jet.OLEDB.4.0` (pCon MDB). Requires the **32-bit Jet OLE DB provider** and the pCon
  staging tree at `C:\HermanMillerOFML\Staging\HermanMiller\`.
- **Global state:** `Global.connectedDB`, `Global.connectedServer`, `Global.primaryPDMDatabase`,
  `Global.PDMServer`, `Global.readOnlyDBConnection`, `Global.ofdaManagerOrWebConfigActive`.
- **Identity/permissions:** `AuthenticateUser` (`UserId`, `DefaultCatalogueId`, `CADMaintenance`,
  `CoreMaintenance`, `Preferences`), `Environment.UserName`.
- **Cross-module calls:** `PriceMaintenance.getPConProgramCodes` (module 18);
  `SuperProductVarCondRelation` form (module 05); `OFDAExportManager.LoadThread` /
  `getOFDAFeautuesByProductXML` (module 22, used by WebConfigurator).
- **External processes / COM:** Microsoft **Excel Interop** (`Microsoft.Office.Interop.Excel`) for the
  pCon data XLS round-trip; `DPS.exe` (validation, launched elsewhere); `chrome.exe` (WebConfigurator
  URL). Revit/DWG parsing via embedded `PreviewThread`/`RevitThread` worker classes.
- **File shares:** `\\FSCHIP01v\PDM Resources\…`, `\\NETSHARES\MKTGTECH$\…`, `Z:\Symbols\`,
  `\\<PDMServer>\HMEURONET\PDM\Images\…`.
- **Reserved words:** `[Option]`, `[Attribute]` bracket-quoting required.

---

## 10. Risks

- **R-1 SQL injection (SQL Server & Jet).** Every query is string-concatenated with inline values
  (`'" + text + "'`), including free-text inputs like `input_layername`, container names, group codes,
  the WebConfigurator item filter, and the "Clone Property Class" name. Both the SQL Server **and**
  the pCon MDB paths are exploitable. This is the dominant risk of the module.
- **R-2 Jet/OLE DB obsolescence & bitness.** `Microsoft.Jet.OLEDB.4.0` is 32-bit-only and deprecated;
  the whole pCon toolset breaks under a 64-bit build or on a machine without the provider. Hardcoded
  local path `C:\HermanMillerOFML\Staging\HermanMiller\` must exist.
- **R-3 Non-atomic id generation.** `SELECT TOP 1 … ORDER BY … DESC` +1 for new `DescriptionId`
  (BR-CFG-021) and node/class inserts are race-prone under concurrent editing.
- **R-4 Data stored as delimited strings.** `ModelList`, `CADImage3D`, `ModelSpecific`,
  `CADPlaceProgram`, `LayerNameList` are pipe-delimited blobs and `Item.Notes` is a comma-list; no
  referential integrity, easy to corrupt, order-sensitive.
- **R-5 Heuristic package resolution.** Package id chosen by "most matches wins" (BR-CFG-053) can pick
  the wrong pCon package silently; `-1` failures are only surfaced to `dbacw8`.
- **R-6 Hardcoded everything.** Server names, share paths, fabric option ids (8/28/3344/3346), the
  pCon-creator user allow-list, the WebConfigurator URL, `chrome.exe`, category 999, `LanguageId 1`,
  language→id map (en/fr/de/nl = 1/2/5/9) are all literals in code.
- **R-7 Excel COM dependency.** `UpdatePConDataFile` drives Excel via COM; fragile (Excel must be
  installed, correct version, no orphaned processes) and its full logic is unverified here.
- **R-8 Errors shown as raw stack traces.** `MsgBox(ex.ToString())` leaks internal SQL/paths to end
  users and is not logged centrally.
- **R-9 Coverage risk.** Large handlers (pCon data import, 2D/3D reference push, OBX→SIF, metatype
  export, gMaterials) were not fully traced; undocumented rules may exist inside them (see coverage
  note). Treat their behaviour as `UNKNOWN` until line-range reads are done.
- **R-10 Permission bypass by allow-list.** `_pConCreatorUsers` (BR-CFG-005) hardcodes accounts that
  override the read-only catalogue guard — a static back-door list that must be maintained in code.
```
