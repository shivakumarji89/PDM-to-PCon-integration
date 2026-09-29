# 15 — UI Grouping / Filtering (UI Groups & Layout Features)

**Module prefix:** BR-FILT
**Primary legacy source:** `PDMMaintenance/UIGroupMaintenance.cs` (~6026 lines); launched from `PDMMaintenance/MainMenu.cs` (`LayoutButton`, **dead**) and `PDMMaintenance/CADMaintenance.cs` (`UIGroupsButton_Click`, **live**).
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

`UIGroupMaintenance.cs` maintains **“UI Groups”** (a.k.a. *Layout Features* / *UI Group Icons*) — the icon-based grouping/filtering scheme used by the downstream online configurator / OFML layout (OFDA/EOS). A UI Group is a per-**Catalogue** + per-**Product Category** bucket, defined by a set of **functional-attribute values** (`Attribute.Name=AttributeValue.Name`), that gathers matching products under one selectable icon.

The form lets a maintainer:
1. **Filter** the product universe down a hierarchy: **Catalogue → Product Category → Product Range** (plus “Multiple Catalogues …”, “[ All Ranges ]”, and a **Redundant** toggle).
2. See, for the filtered scope, the **UI Group icons** and which products are **Assigned** vs **Unassigned** to a group (the core matching in `getUIGroupIdForProduct`).
3. **Create / rename / redefine / delete** UI Groups (`CatalogueUIGroups` table), reorder them (`Sequence`), and attach an **image** by drag-and-drop.
4. Assign a **placement type** to products (`Product.CADPlaceProgram`).

It operates in **two data modes** (BR-FILT-003): the normal **PDM database** mode (reads/writes `CatalogueUIGroups`) and an **OFDA-XML** mode where an imported OFDA file drives an in-memory product list and a **local flat file `groupdata.txt`** is the store instead of the DB. The OFDA-mode features (`Load…`, `PDMButton`, `OtherButton`, Import/Export menu) are restricted to user `dbacw8`.

This is **grouping/filtering maintenance**, not a query tool. It complements 14_Search (which *finds* records) by defining how products are *grouped and filtered in the configurator UI*.

---

## 2. Entry Points

**Live entry — `CADMaintenance` → “UI Groups” button** (`CADMaintenance.UIGroupsButton_Click`, CADMaintenance.cs:15777):
```
new UIGroupMaintenance().Show();
```
Reached from the CAD Maintenance form, which itself is gated by `AuthenticateUser.CADMaintenance` (MainMenu.cs:3058, `CADButton`). So **effective gate = `CADMaintenance` privilege**.

**Dead entry — MainMenu “Layout XML” button** (`LayoutButton_Click`, MainMenu.cs:2893):
```
new UIGroupMaintenance() { StartPosition = CenterScreen }.Show();
```
`LayoutButton.Visible = false` is set in `InitializeComponent` (MainMenu.cs:2555) and the button is **never added to the `menuButtons` collection** that `RefreshPermissions` toggles, so it is never made visible/enabled. **This entry point is unreachable in the built app.**

**Form lifecycle:** `UIGroupMaintenance_Load` (2459) → `updateGroupInfo(-1)` → dbacw8 gate → `loadPDMData()` → `initArrays()` → default multi-catalogue selection (57, 58, 42, 4) → `updateGroups()`.

**dbacw8-only controls** (2478-2486): `PDMButton`, `OtherButton` become visible; `ImportLayoutFromCatalogueToolStripMenuItem` and `ExportPDMLayoutDataToolStripMenuItem` stay hidden for everyone else.

---

## 3. Call Hierarchy

```
CADMaintenance.UIGroupsButton_Click → new UIGroupMaintenance().Show()
  └─ UIGroupMaintenance_Load
       ├─ updateGroupInfo(-1)                     // clears info panel
       ├─ [dbacw8?] show PDM/Other buttons + Import/Export menu
       ├─ loadPDMData → initArrays               // catalogue list (Q-FILT-001) + SP-component list (Q-FILT-002)
       ├─ preselect Multiple-Catalogues 57,58,42,4
       └─ updateGroups                            // category list (Q-FILT-003) + PLC group codes (Q-FILT-004)

catalogue_selector_SelectedIndexChanged → updateGroups
category_selector_SelectedIndexChanged  → updateRange
   └─ updateRange                                // product list (Q-FILT-005) → loadUIGroups(-1)
range_selector_SelectedIndexChanged     → updateRange
RedundantCheck_CheckedChanged           → loadUIGroups(-1)

loadUIGroups(selectedId)                          // 3211  builds icons + assigned/unassigned split
   ├─ (DB)  Q-FILT-006  SELECT … FROM CatalogueUIGroups …
   │   (OFDA) parse local groupdata.txt
   ├─ for each product: getUIGroupIdForProduct(...)  // 3038  CORE MATCH
   │        └─ Q-FILT-007 functional-attribute query
   └─ render PictureBox icons (Click/DragOver/DragDrop)

product_list_SelectedIndexChanged → Q-FILT-008 (funcattr_list)  + UIPanel.Invalidate
UIPanel_Paint → getUIGroupIdForProduct → position UIGroupMarker
clickUIGroup / updateGroupInfo(groupId) → Q-FILT-009  (info + description + sequence)

Mutations:
  AddIconButton_Click   (3769) → Q-FILT-010 INSERT OtherDescription + INSERT CatalogueUIGroups
  RemoveIconButton_Click(3977) → Q-FILT-011 reorder Sequence + DELETE CatalogueUIGroups
  ModifyButton_Click    (4441) → Q-FILT-012 UPDATE CatalogueUIGroups.UIGroups
  SubmitButton_Click    (4325) → Q-FILT-013 UPDATE OtherDescription.ShortDescription (+ Sequence reorder Q-FILT-014)
  UIGroupIcon_DragDrop  (4752) → updateGroupImage → Q-FILT-015 UPDATE CatalogueUIGroups.ImageFile
  ApplyButton_Click     (4999) → Q-FILT-016 UPDATE Product.CADPlaceProgram  (placement)

OFDA/dbacw8:
  LoadButton_Click → LoadOFDAThread (parse OFDA xml into _ofda* lists)
  PDMButton_Click  → loadPDMData
  OtherButton_Click→ UpdateSIFOFDAThread
  ExportPDMLayoutDataToolStripMenuItem_Click → Q-FILT-017 dump CatalogueUIGroups → groupdata.txt
  ImportLayoutFromCatalogueToolStripMenuItem_Click → EMPTY (dead)
```

---

## 4. SQL Analysis

> All DB reads use `WITH (NOLOCK)`. All statements are inline string-concat through `ConnectionFactory.CreateNewConnection` → `SqlConnection`/`SqlCommand`; **no `SqlParameter` anywhere**. In OFDA mode the same operations target the local `groupdata.txt` pipe-delimited file instead of SQL.

**Q-FILT-001** — Catalogue list for the user (`initArrays`, UIGroupMaintenance.cs:2312). *WHY:* populate `catalogue_selector` + `list_multi_catalogue`, capturing `ReadOnly`.
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly
FROM PDMUserCatalogues puc WITH (NOLOCK) INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId
WHERE puc.UserId = <UserId> AND Catalogue.Status = 1 ORDER BY Catalogue.Name
```
A synthetic `Multiple Catalogues ...` entry (id `-1`) is appended.

**Q-FILT-002** — Stand-alone + SuperProduct-component product set (`initArrays`, 2331). *WHY:* used later to allow SP-components (category 999) to match groups.
```sql
SELECT DISTINCT Product.ProductId, Product.Product
FROM Product WITH (NOLOCK) INNER JOIN Item ON Product.ProductId = Item.ProductId
     INNER JOIN ItemComponents itco ON Item.ItemId = itco.SubItemId
WHERE Product.ProductRangeId <> 999 ORDER BY Product.Product
```

**Q-FILT-003** — Category list for the selected catalogue(s) (`updateGroups`, 2560). *WHY:* fill `category_selector`; exclude system categories; `DisplayOrder -1 → 9999` for sorting.
```sql
SELECT DISTINCT pc.ProductCategoryId, cpc.Name,
       CASE WHEN cpc.DisplayOrder = -1 THEN 9999 ELSE cpc.DisplayOrder END AS cpcDO
FROM ProductCategory pc WITH (NOLOCK)
     INNER JOIN CatalogueProductCategories cpc ON pc.ProductCategoryId = cpc.ProductCategoryId
WHERE cpc.CatalogueId IN (<catList>) AND cpc.ProductCategoryId NOT IN (1, 128, 129, 999)
      AND pc.Status < 2 AND cpc.Status < 2 ORDER BY cpc.Name
```
For a *single* catalogue the code strips `DISTINCT` and re-sorts `ORDER BY cpcDO` (display order) (2571-2574). A synthetic `< SP Components >` (id 999) is appended.

**Q-FILT-004** — PLC group codes present in the catalogue(s) (`updateGroups`, 2576). *WHY:* fill `group_selector`; UNION of released + unreleased catalogue items, `pc.SiteId IN (-1, 1)`.
```sql
SELECT DISTINCT pc.GroupCode FROM Product_Code pc WITH (NOLOCK)
   INNER JOIN Product ON Product.ProductCodeId = pc.ProductCodeId
   INNER JOIN Item ON Product.ProductId = Item.ProductId
   INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId
WHERE pc.SiteId IN (-1, 1) AND ci.CatalogueId IN (<catList>)
UNION SELECT DISTINCT pc.GroupCode FROM Product_Code pc WITH (NOLOCK)
   INNER JOIN Product … INNER JOIN Item … INNER JOIN CatalogueItemsUnreleased ci ON Item.ItemId = ci.ItemId
WHERE pc.SiteId IN (-1, 1) AND ci.CatalogueId IN (<catList>) ORDER BY pc.GroupCode
```

**Q-FILT-005** — Product list for the Catalogue×Category×Range scope (`updateRange`, 2762). *WHY:* fill `product_list` (the filtered universe). Two shapes:
- **Normal category:**
```sql
SELECT DISTINCT Product.ProductId, Product.Product FROM Product WITH (NOLOCK)
   INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
   INNER JOIN ProductCategory pc ON pr.ProductCategoryId = pc.ProductCategoryId
   INNER JOIN CatalogueProductRanges cpr ON pr.ProductRangeId = cpr.ProductRangeId AND cpr.CatalogueId IN (<catList>)
   INNER JOIN CatalogueProductCategories cpc ON pc.ProductCategoryId = cpc.ProductCategoryId AND cpc.CatalogueId IN (<catList>)
   INNER JOIN Item ON Product.ProductId = Item.ProductId
   INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId AND ci.CatalogueId IN (<catList>)
WHERE pc.ProductCategoryId = <catId> AND (pr.ProductRangeId = <rangeId> OR -1 = <rangeId>) ORDER BY Product.Product
```
- **SP Components (category 999):** walks `ItemComponents` up to the parent item/product.
```sql
SELECT DISTINCT Product.ProductId, Product.Product FROM Product WITH (NOLOCK)
   INNER JOIN Item ON Product.ProductId = Item.ProductId
   INNER JOIN ItemComponents itco ON Item.ItemId = itco.SubItemId
   INNER JOIN Item parent_item ON itco.ItemId = parent_item.ItemId
   INNER JOIN Product parent_product ON parent_item.ProductId = parent_product.ProductId
   INNER JOIN ProductRange pr … INNER JOIN ProductCategory pc …
   INNER JOIN CatalogueProductCategories cpc ON pc.ProductCategoryId = cpc.ProductCategoryId AND cpc.CatalogueId IN (<catList>)
   INNER JOIN CatalogueItems ci ON parent_item.ItemId = ci.ItemId AND ci.CatalogueId IN (<catList>)
ORDER BY Product.Product
```

**Q-FILT-006** — UI Groups for the scope (`loadUIGroups`, 3331). *WHY:* the icons; `Sequence` order.
```sql
SELECT cui.UIGroupId, cui.Name, cui.UIGroups, cui.DefaultedGroups, cui.ImageFile,
       CASE WHEN od.ShortDescription IS NULL THEN cui.Name ELSE od.ShortDescription END AS ShortDescription,
       cui.Sequence, cui.ProductCategoryId, cui.ProductRangeId
FROM CatalogueUIGroups cui WITH (NOLOCK)
     LEFT OUTER JOIN OtherDescription od ON cui.DescriptionId = od.DescriptionId AND LanguageId = 1
WHERE cui.CatalogueId IN (<catList>) AND cui.ProductCategoryId = <catId> ORDER BY Sequence
```
(A commented-out `CHARINDEX('_', cui.Name)` expression shows `Sequence` used to be derived from the name suffix.)

**Q-FILT-007** — A product’s functional attributes, used by the matcher (`getUIGroupIdForProduct`, 3073). *WHY:* the set of `Attr=Value` tokens a product carries.
```sql
SELECT Product.Product, attr.Name + '=' + REPLACE(REPLACE(atval.Name, ',', '/'), '&', 'and') AS UIGroup,
       pc.ProductCategoryId, pr.ProductRangeId
FROM Product WITH (NOLOCK)
     INNER JOIN ProductRange pr … INNER JOIN ProductCategory pc …
     INNER JOIN ProductAttributeValues pav ON Product.ProductId = pav.ProductId
     INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId
     INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId
WHERE pav.ProductId = <productId> AND attr.AttributeType = 0 AND atval.ModelSuffix IS NULL
ORDER BY attr.DisplayOrder, atval.DisplayOrdinal
```

**Q-FILT-008** — Functional-attribute picker for the selected product (`product_list_SelectedIndexChanged`, 3587): same predicate as Q-FILT-007 but also returns `attr.AttributeId, atval.AttributeValueId` (stored as `AttributeId~AttributeValueId` in `_funcattrIdList`) to seed new-group creation.

**Q-FILT-009** — Group info panel (`updateGroupInfo`, 2958): `SELECT cui.Name, cui.UIGroups, cui.DefaultedGroups, <ShortDescription>, cui.Sequence FROM CatalogueUIGroups cui … WHERE cui.CatalogueId IN (<catList>) AND cui.UIGroupId = <groupId>`.

**Q-FILT-010** — Create UI Group (`AddIconButton_Click`, 3902-3948). *WHY:* new group from the selected functional attributes.
```sql
SELECT TOP 1 DescriptionId FROM OtherDescription WITH (NOLOCK) ORDER BY DescriptionId DESC        -- next id = max+1
SELECT TOP 1 Name FROM CatalogueUIGroups WITH (NOLOCK) WHERE CatalogueId IN (<catList>) AND ProductCategoryId = <catId>
SELECT TOP 1 Sequence FROM CatalogueUIGroups WITH (NOLOCK) WHERE … ORDER BY Sequence DESC          -- next seq = max+1
SELECT ProductRangeId FROM Product WHERE Product = '<selected product>'
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable)
       VALUES (<newDescId>, 1, '<name>', 'CatalogueUIGroups')
INSERT INTO CatalogueUIGroups (CatalogueId, Name, UIGroups, DefaultedGroups, ImageFile, DescriptionId, Sequence, ProductCategoryId, ProductRangeId)
       VALUES (<catId0>, '<groupName>', '<selectedAttrs>', <NULL|'<unselectedAttrs>'>, NULL, <newDescId>, <newSeq>, <catId>, <productRangeId>)
```
`UIGroups` = comma-list of the **selected** funcattr tokens; `DefaultedGroups` = comma-list of the **unselected** ones (or `NULL`).

**Q-FILT-011** — Delete UI Group (`RemoveIconButton_Click`, 4098-4104): read the group’s `Sequence`, decrement `Sequence` of all higher groups, then delete.
```sql
UPDATE CatalogueUIGroups SET Sequence = <seq-1> WHERE UIGroupId = <id>   -- for each higher group
DELETE FROM CatalogueUIGroups WHERE UIGroupId = <groupId>
```

**Q-FILT-012** — Redefine UI Group value set (`ModifyButton_Click`, 4540): `UPDATE CatalogueUIGroups SET UIGroups = '<newValue>' WHERE UIGroupId = <id>` (trailing/leading comma normalised; must contain `=`).

**Q-FILT-013** — Rename UI Group (`SubmitButton_Click`, 4413): `SELECT DescriptionId FROM CatalogueUIGroups … WHERE UIGroupId = <id>` then `UPDATE OtherDescription SET ShortDescription = '<text>' WHERE DescriptionId = <id> AND LanguageId = 1`.

**Q-FILT-014** — Re-sequence (`SubmitButton_Click`, 4290-4305): when the sequence value changes, shift the intervening groups’ `Sequence` up/down and then `UPDATE CatalogueUIGroups SET Sequence = <newSeq> WHERE UIGroupId = <id>`.

**Q-FILT-015** — Attach image (`updateGroupImage`, 4717): copy the dropped file into `Images\`, then `UPDATE CatalogueUIGroups SET ImageFile = '<fileName>' WHERE UIGroupId = <groupId>`.

**Q-FILT-016** — Assign placement type (`ApplyButton_Click`, 5034): for each selected assigned product,
```sql
SELECT ProductId, CADPlaceProgram FROM Product WITH (NOLOCK) WHERE Product = '<name>'
UPDATE Product SET CADPlaceProgram = CASE WHEN CADPlaceProgram IS NULL THEN '' ELSE REPLACE(CADPlaceProgram, '[<old>]', '') END + '[<new>]' WHERE ProductId = <id>
```

**Q-FILT-017** — Export all layout data (`ExportPDMLayoutDataToolStripMenuItem_Click`, dbacw8, 4901): dumps every group to `groupdata.txt`.
```sql
SELECT cui.*, Catalogue.OFMLManufacturer, od.ShortDescription
FROM CatalogueUIGroups cui WITH (NOLOCK)
     INNER JOIN Catalogue ON cui.CatalogueId = Catalogue.CatalogueId
     INNER JOIN OtherDescription od ON cui.DescriptionId = od.DescriptionId AND od.LanguageId = 1
ORDER BY cui.UIGroupId
```
Pipe-delimited fields written: `UIGroupId|OFMLManufacturer|Name|ProductCategoryId|Sequence|UIGroups|DefaultedGroups|ImageFile|ShortDescription|`.

**Q-FILT-018** — (dead) `ImportLayoutFromCatalogueToolStripMenuItem_Click` (4952): body is empty — no SQL.

**Also referenced (read):** `SELECT CADPlaceProgram FROM Product … WHERE ProductId = <id>` / `… WHERE Product = '<name>'` (`productHasValidPlacementType` 3170, `products_assigned_SelectedIndexChanged` 3635) to check/parse the current placement token.

---

## 5. Data Model

| Table | Role |
|---|---|
| `CatalogueUIGroups` | **the UI-Group table.** Cols: `UIGroupId` PK, `CatalogueId` FK, `Name`, `UIGroups` (comma-list of `Attr=Value` selectors), `DefaultedGroups` (comma-list of defaulted selectors), `ImageFile`, `DescriptionId` FK→`OtherDescription`, `Sequence` (ordinal), `ProductCategoryId` FK, `ProductRangeId` FK |
| `OtherDescription` | localized group label (`DescriptionId`, `LanguageId`=1, `ShortDescription`, `RelatedTable`='CatalogueUIGroups') |
| `PDMUserCatalogues` | `UserId`, `CatalogueId`, `ReadOnly` — used to list the user’s catalogues (BR-FILT-004) |
| `Catalogue` | `CatalogueId`, `Name`, `Status`, `OFMLManufacturer` |
| `CatalogueProductCategories` (`CatalogueId`,`ProductCategoryId`,`Name`,`DisplayOrder`,`Status`) | category filter source |
| `CatalogueProductRanges` (`CatalogueId`,`ProductRangeId`) | range filter source |
| `CatalogueItems` / `CatalogueItemsUnreleased` | membership for product/PLC scoping |
| `ProductCategory` / `ProductRange` | `Status`, `DisplayOrder`; category ids 1/128/129/999/1000 special |
| `Product` | `ProductId`, `Product`, `ProductRangeId`, `ProductCodeId`, `CADPlaceProgram` (placement tokens `[X]`) |
| `Product_Code` | `ProductCodeId`, `GroupCode`, `SiteId`, `Status` |
| `Item` / `ItemComponents` (`ItemId`,`SubItemId`) | SP-component traversal |
| `Attribute` (`AttributeId`,`Name`,`AttributeType`,`DisplayOrder`) | functional attrs where `AttributeType = 0` |
| `AttributeValue` (`AttributeValueId`,`Name`,`ModelSuffix`,`DisplayOrdinal`) | value; only `ModelSuffix IS NULL` used |
| `ProductAttributeValues` (`ProductId`,`AttributeValueId`) | product↔funcattr link |

**Local file store (OFDA mode):** `groupdata.txt` — pipe-delimited, one line per group, field indices (1-based, via `getProperty`): `1`=UIGroupId, `2`=OFMLManufacturer, `3`=Name/Catalogue, `4`=ProductCategoryId, `5`=Sequence, `6`=UIGroups, `7`=DefaultedGroups, `8`=ImageFile, `9`=ShortDescription.

**Selector value grammar:** a `UIGroups`/`DefaultedGroups` entry is `Attr=Value` (value with `,`→`/` and `&`→`and`). A trailing `{`…`}` marks a **prefix wildcard** (matches any product attr token starting with the text before `{`).

---

## 6. Business Rules

**BR-FILT-001** — A UI Group is a per-`CatalogueId`+`ProductCategoryId` bucket keyed by functional-attribute selectors (`UIGroups`), owned in `CatalogueUIGroups`, labelled via `OtherDescription` (lang 1), ordered by `Sequence`, optionally illustrated by `ImageFile`.

**BR-FILT-002** — **Entry gating:** live only through `CADMaintenance` → *UI Groups* button ⇒ effective privilege `AuthenticateUser.CADMaintenance`. The MainMenu *Layout XML* button is permanently hidden (`Visible=false`, never re-enabled) ⇒ **dead entry point**.

**BR-FILT-003** — **Dual data mode:** if `_ofdaProductList.Count > 0` (an OFDA XML was loaded) the form works against the in-memory OFDA lists and the local `groupdata.txt`; otherwise it reads/writes the PDM DB (`CatalogueUIGroups`). Every read/write branch checks this flag.

**BR-FILT-004** — Catalogue list is scoped to the user’s `PDMUserCatalogues` **and** `Catalogue.Status = 1` (active). `ReadOnly` is captured into `_readOnlyCatalogues` (but see BR-FILT-036).

**BR-FILT-005** — Default catalogue selection = index of `AuthenticateUser.DefaultCatalogueId` if present, else the appended “Multiple Catalogues …” entry (initArrays, 2340-2347). `Load` additionally pre-selects catalogues **57, 58, 42, 4** in the multi-catalogue list (UIGroupMaintenance.cs:2492-2496).

**BR-FILT-006** — “Multiple Catalogues …” (id `-1`) enables the `list_multi_catalogue` multi-select; all scope queries then build a comma list and use `CatalogueId IN (<list>)`.

**BR-FILT-007** — Category filter (Q-FILT-003) **excludes** ProductCategoryIds `1, 128, 129, 999`, and requires `pc.Status < 2 AND cpc.Status < 2`. A synthetic **`< SP Components >`** entry (id `999`) is appended to represent SuperProduct components.

**BR-FILT-008** — Category sort: `CatalogueProductCategories.DisplayOrder = -1` is treated as `9999` (sinks to bottom). For a **single** catalogue the query drops `DISTINCT` and orders by `cpcDO` (display order); for **multiple** it orders by `Name`.

**BR-FILT-009** — Range filter comes from `CatalogueProductRanges`; a `[ All Ranges ]` pseudo-entry (id `-1`) shows every range. `RedundantCheck` is visible **only** when `[ All Ranges ]` is selected (BR-FILT-018).

**BR-FILT-010** — Product universe (Q-FILT-005) is Catalogue×Category×Range–scoped through `CatalogueProductCategories`+`CatalogueProductRanges`+`CatalogueItems`; the range clause is `(pr.ProductRangeId = <rangeId> OR -1 = <rangeId>)` so `-1` = all. The **SP-Components** category (999) instead traverses `ItemComponents` to the parent product.

**BR-FILT-011** — Functional attributes are `Attribute.AttributeType = 0` **and** `AttributeValue.ModelSuffix IS NULL`, ordered by `attr.DisplayOrder, atval.DisplayOrdinal`. The display/selector token is `Attr.Name + '=' + Value.Name` with `,`→`/` and `&`→`and` normalisation (Q-FILT-007/008).

**BR-FILT-012** — **Core matcher** `getUIGroupIdForProduct` returns the `UIGroupId` of the **first** group (in `Sequence`/list order) that the product satisfies, else `-1` (unassigned). It iterates groups and breaks on the first match (3084-3145).

**BR-FILT-013** — **Scope gate for a match:** a group is only considered for a product when the group’s category/range equals the product’s **or** is `-1` (wildcard), with a special allowance: if the product is in `_productStandaloneAndSuperProductComponents` and the group’s category is `999`, it qualifies (SP-component grouping) (3103 condition).

**BR-FILT-014** — **Match test:** the product matches a group only if **every** functional-attribute token the product carries is either (a) present in the group’s `UIGroups` list (`"<token>," ` containment), (b) a prefix-wildcard hit (`<prefix>{` in the group vals), or (c) covered by `DefaultedGroups` (attribute defaulted). If any product token is left uncovered, the group is rejected (`flag2=false ⇒ num=-1; break`).

**BR-FILT-015** — **DefaultedGroups semantics:** a token whose attribute name appears in `DefaultedGroups` at the **start** (`"<attr>="` at index 0, for non-first tokens) or embedded (`",<attr>="`) is treated as satisfied without needing an explicit `UIGroups` entry (3108).

**BR-FILT-016** — **Wildcard suffix:** a `UIGroups` entry containing `{` is truncated at `{` and used as a `StartsWith` prefix match against the product’s tokens (3113-3122).

**BR-FILT-017** — After matching, each product is placed in **Products Assigned** (matcher `> -1`) or **Products Unassigned** (`-1`); counts are shown in the group-box labels (`loadUIGroups`, 3434-3470).

**BR-FILT-018** — A group icon with **no** assigned product (“redundant”) is drawn `Crimson` **only** when `[ All Ranges ]` is selected **and** `RedundantCheck` is checked; otherwise redundant groups are hidden from the panel (3437-3448).

**BR-FILT-019** — **Create (AddIcon)** requires a selected product that currently has **no** group assignment (`getUIGroupIdForProduct == -1`) and ≥1 selected functional attribute; else it warns (“already has an UI Group assignment” / “select one or more functional attributes”). New `DescriptionId` = `MAX(DescriptionId)+1`, new `Sequence` = `MAX(Sequence)+1` for the catalogue/category (Q-FILT-010).

**BR-FILT-020** — On create, `UIGroups` = the **selected** funcattr tokens (comma-list), `DefaultedGroups` = the **unselected** ones (or `NULL`); `ImageFile` = `NULL`; the group `Name` inherits the first existing group’s `Name` for that catalogue/category, else the category name (3944-3947).

**BR-FILT-021** — **Delete (RemoveIcon)** decrements the `Sequence` of every group above the removed one, then `DELETE`s the group (Q-FILT-011). It requires the info panel to point at a valid `UIGroupId`.

**BR-FILT-022** — **Modify** redefines the `UIGroups` selector string via an `InputBox`; the new value **must contain `=`** (else warn). Trailing comma is enforced and a leading comma stripped before `UPDATE` (Q-FILT-012).

**BR-FILT-023** — **Submit** renames the group by updating `OtherDescription.ShortDescription` (lang 1) for the group’s `DescriptionId`; blank description ⇒ no-op (Q-FILT-013).

**BR-FILT-024** — **Submit** also applies the `sequence_value` change: groups between old and new sequence are shifted by ±1, then the target group’s `Sequence` is set (Q-FILT-014). This is an in-memory shift of `_uiGroupSequences` mirrored by per-group `UPDATE`s.

**BR-FILT-025** — **Apply placement** sets `Product.CADPlaceProgram` for each selected *assigned* product to `<existing minus [old]> + [<newPlacement>]` (the previous `[...]` token is stripped first) (Q-FILT-016). Requires a `placement_selector` selection.

**BR-FILT-026** — In the assigned list, a product **without** a valid placement type is drawn in red (`productHasValidPlacementType` parses the `[...]` token from `CADPlaceProgram` against `placement_selector`) (`products_assigned_DrawItem`, 5104).

**BR-FILT-027** — Dragging an image file onto a group icon copies it into `Images\` and updates `CatalogueUIGroups.ImageFile` (drag handlers 4737/4752 → `updateGroupImage` Q-FILT-015).

**BR-FILT-028** — The image folder (`imagefilePath = "Images\\"`, a **relative** path) is auto-created on load if missing (`UIGroupMaintenance_Load`, 2473).

**BR-FILT-029** — **dbacw8-only** features: `PDMButton`/`OtherButton` visible and `ImportLayoutFromCatalogue`/`ExportPDMLayoutData` menu items visible only when `Environment.UserName.ToLower() == "dbacw8"` (2478-2486). Non-dbacw8 users see only the DB-backed maintenance.

**BR-FILT-030** — `ExportPDMLayoutData` (dbacw8) serialises **all** `CatalogueUIGroups` (joined to `Catalogue.OFMLManufacturer` + `OtherDescription`) into the pipe-delimited `groupdata.txt` (Q-FILT-017).

**BR-FILT-031** — In **OFDA mode** the same Add/Remove/Modify/Submit operations edit `groupdata.txt` in place (read-all, string-replace the matching pipe line, write-all) instead of SQL — including sequence renumbering (RemoveIcon 3990-4060).

**BR-FILT-032** — `ImportLayoutFromCatalogue` is an **empty stub** (dead) — the menu item does nothing (4952).

**BR-FILT-033** — String escaping: apostrophes in names/descriptions are replaced `'` → `` ` `` before concatenation into SQL/`groupdata.txt` (e.g. AddIcon 3941, Submit 4413, Modify — none escaped there). Escaping is inconsistent across handlers (Modify/ApplyPlacement concatenate raw product names).

**BR-FILT-034** — On load, the multi-catalogue list is pre-seeded with catalogue ids **57, 58, 42, 4** (matched by `_catalogueIdList.IndexOf`) — hardcoded defaults (2492-2496).

**BR-FILT-035** — Product names are concatenated **unescaped** into several statements (`SELECT ProductRangeId FROM Product WHERE Product = '<name>'` in AddIcon 3897; `WHERE Product = '<name>'` in Apply/placement/assigned handlers) — injectable via a product name with a quote.

**BR-FILT-036** — **`_readOnlyCatalogues` is captured but never enforced.** The array is populated (2320) yet **no** write handler (Add/Remove/Modify/Submit/ApplyPlacement/image) reads it. A user with a read-only catalogue can still create/rename/redefine/delete its UI Groups and change placements. (Contrast 13_Descriptions where read-only is enforced.) **Authorization gap.**

**BR-FILT-037** — All DB reads use `WITH (NOLOCK)` (dirty reads) — acceptable for a maintenance UI but can show uncommitted group edits.

**BR-FILT-038** — `UIPanel_Paint` re-runs the matcher per icon to position the red `UIGroupMarker` over the group the selected product belongs to, and enables `RemoveIcon` only when an icon has focus (`BorderStyle.FixedSingle`) (2828-2870).

**BR-FILT-039** — The SP-Components product source (category 999) requires `Product.ProductRangeId <> 999` on the component set (Q-FILT-002) and joins `ItemComponents` (subitem → parent) for the range query (Q-FILT-005 SP branch).

**BR-FILT-040** — Error handling: every handler wraps work in try/catch and shows `MsgBox(ex.ToString())` (raw exception) — information disclosure and no rollback (writes are individual `ExecuteNonQuery` calls, no transaction).

**BR-FILT-041** — `Ctrl+A` in the assigned-products list selects all items (`ProcessCmdKey` override, 5090) — bulk placement convenience.

---

## 7. Hidden Logic

- **The matcher is the whole business logic.** `getUIGroupIdForProduct` encodes the grouping semantics (scope gate + full-coverage test + wildcard + defaulted). It is invoked from `loadUIGroups`, `UIPanel_Paint`, and `AddIconButton_Click` — so display, marker painting, and the “already assigned?” guard all share one algorithm.
- **Coverage, not intersection.** A product matches a group only if *all* of the product’s functional tokens are covered — a group with fewer selectors than the product carries will **not** match (unless the extras are defaulted/wildcarded). This is subtle and easy to get wrong when redefining `UIGroups`.
- **Sequence is a dense ordinal** maintained by hand (max+1 on insert, ±1 shifts on delete/reorder). There is no unique constraint enforced in-app; concurrent edits can collide.
- **`DescriptionId = MAX+1`** (Q-FILT-010) is a race condition — two concurrent creates can pick the same id.
- **Two stores, one UI.** OFDA mode silently swaps the persistence layer to a local text file; the same buttons mean “edit DB” or “edit file” depending on a hidden flag.
- **Relative `Images\` path** — image resolution depends on the process working directory.
- **Commented-out name-suffix sequence** (`CHARINDEX('_', Name)`) reveals `Sequence` was historically derived from the group name; now it is an explicit column.
- **Placement token grammar** — `CADPlaceProgram` stores placement as an embedded `[TOKEN]`; Apply does a string `REPLACE` to swap it, so malformed existing values can duplicate/leak tokens.

---

## 8. UI Behaviour

- Three cascading combos — `catalogue_selector` → `category_selector` → `range_selector` — each change re-runs the next stage (`updateGroups` → `updateRange` → `loadUIGroups`). `list_multi_catalogue` appears for “Multiple Catalogues …”.
- `RedundantCheck` (only with All Ranges) toggles display of empty/redundant group icons (crimson).
- The **UI Group Icons** panel renders one `PictureBox` per group (image or gray placeholder with the description drawn on it); clicking an icon selects it (blue border) and shows its info/description/sequence with **Submit**/**Modify** buttons; a selected product paints a red marker over its matching group.
- **Products Assigned / Unassigned** lists split the filtered universe; assigned products lacking a valid placement type are drawn red; `Ctrl+A` selects all assigned.
- Buttons: **Add** (new group from funcattrs), **Remove** (delete focused icon), **Apply** (placement), image **drag-drop** onto an icon.
- `WaitCursor` during the heavy `updateRange`/`loadUIGroups` passes (they run the matcher for every product).
- dbacw8 sees extra `PDM`/`Other`/`Load` buttons and the Import/Export menu; a status label reports OFDA load progress.
- Errors surface as modal `MsgBox` with the raw exception.

---

## 9. Dependencies

- **`CADMaintenance`** — sole live launcher (UI Groups button); gated by `CADMaintenance` privilege.
- **`ConnectionFactory.CreateNewConnection`** → `SqlConnection` (PDM DB).
- **`AuthenticateUser`** — `UserId`, `DefaultCatalogueId`; note `_readOnlyCatalogues` captured but unused (BR-FILT-036).
- **`Environment.UserName`** — `dbacw8` feature gate.
- **`GetImage.SafeImageFromFile`** — icon rendering.
- **`LoadOFDAThread` / `UpdateSIFOFDAThread`** — OFDA XML import/update threads (dbacw8).
- **Local files** — `Images\` (icon store), `groupdata.txt` (OFDA-mode store / export target).
- **DB tables** — see §5 (esp. `CatalogueUIGroups`, `OtherDescription`, `CatalogueProductCategories/Ranges`, `ProductAttributeValues`).
- **Downstream consumer** — the OFDA/EOS configurator that reads `CatalogueUIGroups` to render layout-feature icons (`UNKNOWN` here; server-side).

---

## 10. Risks

- **Authorization gap (OWASP A01).** BR-FILT-036: the read-only catalogue flag is loaded but never checked, so any user who can open the form (CAD Maintenance privilege) can mutate UI Groups and product placements in catalogues they should only be able to view.
- **SQL injection (OWASP A03).** BR-FILT-035: product names (and, in OFDA mode, file content) are concatenated unescaped into `SELECT/UPDATE` statements; apostrophe-escaping is inconsistent (only some handlers do `'`→`` ` ``). A product named with a quote breaks or subverts the query.
- **Race conditions.** `DescriptionId = MAX+1` and dense `Sequence` maintenance (BR-FILT-024) are non-atomic; concurrent maintainers can collide, duplicate ids, or scramble ordering. No transactions wrap multi-statement reorders (BR-FILT-040) — a mid-loop failure leaves sequences inconsistent.
- **Fragile grouping semantics.** The “full-coverage” match (BR-FILT-014) plus wildcard/defaulted rules are non-obvious; an incorrect `UIGroups` redefinition (BR-FILT-022) can silently unassign large product sets with no validation.
- **Environment coupling.** Relative `Images\` path and local `groupdata.txt` depend on the process working directory; hardcoded default catalogue ids `57,58,42,4` (BR-FILT-034) and category exclusions `1,128,129,999,1000` bake business config into code.
- **Dead / hidden paths.** MainMenu *Layout XML* entry is dead (BR-FILT-002); `ImportLayoutFromCatalogue` is an empty stub (BR-FILT-032) — future maintainers may assume they work.
- **Information disclosure (OWASP A09).** Raw exceptions shown in `MsgBox` (BR-FILT-040).
- **`UNKNOWN`:** the OFDA XML schema and how the downstream configurator consumes `CatalogueUIGroups`; whether `Sequence`/`DescriptionId` have DB-level uniqueness constraints; exact contents produced by `LoadOFDAThread`/`UpdateSIFOFDAThread`.
