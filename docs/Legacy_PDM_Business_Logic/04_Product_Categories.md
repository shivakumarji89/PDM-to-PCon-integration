# 04 — Product Categories

**Module prefix:** BR-CATEG
**Primary legacy source:**
- `PDMMaintenance/OrderCategories.cs` (product-category ordering path — `catalogueId > 0`)
- `PDMMaintenance/CADMaintenance.cs` (category selector load, lines ~9092, ~6522)
- `PDMMaintenance/ProductDescriptions.cs` (category-related catalogue context)
- `PDMMaintenance/AddDataList.cs` (`initialiseDataList(catalogueId, categoryId, ...)`)
- `PDMMaintenance/metaTypes.cs` (**not** a category type — see §7 / clarification)

**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

A **product category** groups product ranges/products within a catalogue (e.g. "Seating", "Tables"). In PDM, categories are modelled by two tables:

- `ProductCategory` — the master list of categories (`ProductCategoryId`, `Name`).
- `CatalogueProductCategories` (a.k.a. **CPC**) — the association of a category to a specific catalogue, carrying per-catalogue presentation data: `DisplayOrder`, `Name`, `DescriptionId`, `ImageFile`.

This module covers how categories are loaded into selectors (with localized descriptions and display-order sorting), the fallback ordering convention (`DisplayOrder = -1 → 9999`), the special synthetic "SP Components" category (`id 999`), and the (never-invoked) per-catalogue category re-ordering path in `OrderCategories`.

> **Clarification (module 16 note):** `metaTypes.cs` is *not* a product-category type. It is a small OFML/GO data holder (`fileName = "go_types"`) for metatype property definitions (`product`, `propertyName`, `propertyFormat`, `defaultValue`, `propertyMode`, `propertyParent`). It belongs to the OFML/generation domain, not categories. See `16_Ordering.md` §7.

---

## 2. Entry Points

| Entry point | Location | Trigger |
|---|---|---|
| **Category selector combo** (`category_selector`) | `CADMaintenance.cs` ~9085–9110 | Populated when a catalogue is selected; lists that catalogue's product categories ordered by display order. |
| **Category list (context/report)** | `CADMaintenance.cs` ~6522 | Builds category list with `DisplayOrder = -1 → 9999` fallback for display. |
| **`OrderCategories` form (category path)** | `OrderCategories.cs` `OrderCategories_Load` (`catalogueId > 0` branch) | Would order product categories within a catalogue. **Never invoked** — the only caller passes `catalogueId = -1` (BR-CATEG-010). |
| **`AddDataList.initialiseDataList(catalogueId, categoryId, …)`** | `AddDataList.cs` ~344 | Data-picker scoped by catalogue + category. |
| **Image lookup** | `CADMaintenance.cs` ~8227 | Reads `CatalogueProductCategories.ImageFile` for a category. |

---

## 3. Call Hierarchy

```
CADMaintenance (Form)
 └─ (catalogue selected) → load categories        [CADMaintenance.cs ~9085]
      └─ ConnectionFactory.CreateNewConnection(autoOpen:true)
           └─ SqlCommand (Q-CATEG-001)
                → ProductCategory ⋈ CatalogueProductCategories ⋈ OtherDescription
                → ORDER BY (DisplayOrder=-1 → 9999)
                └─ populate category_selector + _categoryIdList
                     └─ append synthetic "< SP Components >" = id 999
 └─ image lookup (Q-CATEG-004)                     [CADMaintenance.cs ~8227]

OrderCategories (Form)                             [see 16_Ordering.md]
 └─ OrderCategories_Load
      ├─ catalogueId == -1 → order Catalogue        (see 03 / 16)
      └─ catalogueId  >  0 → order CatalogueProductCategories   ← DEAD (never called)
           └─ SqlCommand (Q-CATEG-002)
 └─ SubmitButton_Click
      └─ catalogueId > 0 → UPDATE CatalogueProductCategories    ← DEAD
           └─ SqlCommand (Q-CATEG-003)
```

No Controller/Service/Repository layer — inline ADO.NET, string-concatenated SQL in form code.

---

## 4. SQL Analysis

### Q-CATEG-001 — Load a catalogue's product categories (SELECT)
**Source:** `CADMaintenance.cs` ~9092
```sql
SELECT DISTINCT pc.ProductCategoryId, od.ShortDescription,
       CASE WHEN cpc.DisplayOrder = -1 THEN 9999 ELSE cpc.DisplayOrder END AS cpcDO
FROM ProductCategory pc
INNER JOIN CatalogueProductCategories cpc ON pc.ProductCategoryId = cpc.ProductCategoryId
INNER JOIN OtherDescription od ON cpc.DescriptionId = od.DescriptionId AND od.LanguageId = 1
WHERE cpc.CatalogueId = <selected CatalogueId>
ORDER BY cpcDO
```
**WHY:** Lists the product categories that belong to the selected catalogue, using the localized `ShortDescription`, and sorts by display order with `-1` pushed to the end (`9999`). `DISTINCT` guards against duplicate CPC rows.

### Q-CATEG-002 — Load categories for ordering (SELECT, DEAD path)
**Source:** `OrderCategories.cs` `OrderCategories_Load` (`catalogueId > 0` branch), line ~112
```sql
SELECT cpc.ProductCategoryId, cpc.DisplayOrder,
       CASE WHEN od.ShortDescription IS NULL THEN cpc.Name
            ELSE od.ShortDescription END AS ShortDescription
FROM CatalogueProductCategories cpc
LEFT OUTER JOIN OtherDescription od
     ON cpc.DescriptionId = od.DescriptionId AND od.LanguageId = <languageId>
WHERE cpc.CatalogueId = <catalogueId>ORDER BY cpc.DisplayOrder
```
**WHY:** Intended to build the editable ordinal list for a catalogue's categories. **Never executed** because no caller passes `catalogueId > 0`. Note the **missing space** before `ORDER BY` (`= <catalogueId>ORDER BY`) — this would produce invalid SQL (`= 5ORDER BY`) if ever run (BR-CATEG-011, R-CATEG-3).

### Q-CATEG-003 — Persist category display order (UPDATE, DEAD path)
**Source:** `OrderCategories.cs` `SubmitButton_Click` (`catalogueId != -1` branch), line ~201
```sql
UPDATE CatalogueProductCategories
SET DisplayOrder = <textBox.Text>
WHERE ProductCategoryId = <textBox.Tag>
  AND CatalogueId = <catalogueId>
```
**WHY:** Would save reordered category ordinals scoped to one catalogue. Never reached (BR-CATEG-010).

### Q-CATEG-004 — Category image lookup (SELECT)
**Source:** `CADMaintenance.cs` ~8227
```sql
SELECT ImageFile FROM CatalogueProductCategories
WHERE ProductCategoryId = <objectId> AND CatalogueId = <selected CatalogueId>
```
**WHY:** Retrieves the per-catalogue image for a product category.

### Q-CATEG-005 — Category list (report/tree, SELECT)
**Source:** `CADMaintenance.cs` ~6522
```sql
SELECT DISTINCT cpc.ProductCategoryId,
       CASE WHEN cpc.DisplayOrder = -1 THEN 9999 ELSE cpc.DisplayOrder END AS cpcDO,
       pc.Name AS Category
FROM CatalogueProductCategories cpc
INNER JOIN ProductCategory pc ON cpc.ProductCategoryId = pc.ProductCategoryId
... (further WHERE/ORDER built by concatenation)
```
**WHY:** Alternate category listing (raw `pc.Name`, not localized) with the same `-1 → 9999` order fallback.

### Q-CATEG-006 — Category name for data picker (SELECT)
**Source:** `AddDataList.cs` ~358 (context of `initialiseDataList(catalogueId, categoryId, …)`)
```sql
SELECT Name FROM Catalogue WHERE CatalogueId = <catalogueId>
```
**WHY:** Resolves the owning catalogue name to scope/label a category-driven data picker.

> **Injection note:** All queries concatenate `CatalogueId` / `ProductCategoryId` / `objectId` directly into SQL text.

---

## 5. Data Model

### `ProductCategory` (master)
| Column | Notes |
|---|---|
| `ProductCategoryId` | int PK. |
| `Name` | Raw (non-localized) category name; fallback display. |

### `CatalogueProductCategories` (CPC — catalogue↔category association)
| Column | Notes |
|---|---|
| `ProductCategoryId` | FK → `ProductCategory`. Part of composite key with `CatalogueId`. |
| `CatalogueId` | FK → `Catalogue`. Part of composite key. |
| `DisplayOrder` | int ordinal; **`-1` = "unordered" sentinel**, mapped to `9999` (last) by consuming sort queries. |
| `Name` | Per-catalogue category name (fallback when no `OtherDescription`). |
| `DescriptionId` | FK → `OtherDescription.DescriptionId` for localized `ShortDescription`. |
| `ImageFile` | Per-catalogue category image filename. |

### `OtherDescription`
| Column | Notes |
|---|---|
| `DescriptionId` | Join key. |
| `LanguageId` | `1` = base language (hardcoded in category loads). |
| `ShortDescription` | Localized category name. |

**Relationships**
```
Catalogue 1───* CatalogueProductCategories *───1 ProductCategory
CatalogueProductCategories *───1 OtherDescription   (via DescriptionId + LanguageId)
```

### Special / synthetic categories
| Id | Meaning |
|---|---|
| `999` | Synthetic **"< SP Components >"** entry appended in-code to the category selector (not a DB row). Represents SuperProduct components. Source: `CADMaintenance.cs` ~9108. |
| `-1` (DisplayOrder) | "Unordered" sentinel → treated as `9999` for sorting (not an id). |

---

## 6. Business Rules

- **BR-CATEG-001** — A catalogue's product categories are the set of `CatalogueProductCategories` rows for that `CatalogueId`, joined to `ProductCategory` for identity. Source: Q-CATEG-001.
- **BR-CATEG-002** — Categories are displayed using the localized `OtherDescription.ShortDescription` for `LanguageId = 1`, falling back to `ProductCategory.Name` / `cpc.Name` when absent. Source: Q-CATEG-001, Q-CATEG-002.
- **BR-CATEG-003** — Category sort order is `CatalogueProductCategories.DisplayOrder`, with `-1` treated as `9999` so "unordered" categories sort **last**. Source: Q-CATEG-001, Q-CATEG-005 (`CASE WHEN cpc.DisplayOrder = -1 THEN 9999`).
- **BR-CATEG-004** — Duplicate category descriptions are disambiguated in the UI by appending the id in parentheses: `"<desc> (<ProductCategoryId>)"` when the selector already contains that description text. Source: `CADMaintenance.cs` ~9101.
- **BR-CATEG-005** — A synthetic **"< SP Components >"** entry with id `999` is always appended after the real categories in the category selector. Source: `CADMaintenance.cs` ~9108–9109.
- **BR-CATEG-006** — After loading, if the category selector has any items, the first is auto-selected (`if (category_selector.Items.Count > 0) category_selector.SelectedIndex = ...`). Source: `CADMaintenance.cs` ~9110+ (`UNKNOWN` exact default index — verify; code selects index 0 region).
- **BR-CATEG-007** — Category loads use `SELECT DISTINCT` to collapse duplicate CPC rows for the same category. Source: Q-CATEG-001, Q-CATEG-005.
- **BR-CATEG-008** — Category images are per-catalogue: looked up by `(ProductCategoryId, CatalogueId)` from `CatalogueProductCategories.ImageFile`. Source: Q-CATEG-004.
- **BR-CATEG-009** — Category loading always filters by the currently selected `CatalogueId`; there is no "all catalogues" category view in this scope. Source: Q-CATEG-001.
- **BR-CATEG-010** — Per-catalogue category **re-ordering** (the `OrderCategories` `catalogueId > 0` path, Q-CATEG-002/003) is **dead code**: the only instantiation of `OrderCategories` passes `catalogueId = -1`. Categories cannot currently be reordered through this UI. Source: `ProductDescriptions.cs` ~13111 (`orderCategories.catalogueId = -1`).
- **BR-CATEG-011** — The dead category-ordering query (Q-CATEG-002) contains a **SQL concatenation defect** — no space between the `CatalogueId` value and `ORDER BY` — so it would fail if ever executed. Source: `OrderCategories.cs` ~112.
- **BR-CATEG-012** — The base language for category description joins is hardcoded to `LanguageId = 1` in `CADMaintenance` loads (Q-CATEG-001, Q-CATEG-005), whereas `OrderCategories` uses the caller-supplied `languageId`. Source: compare Q-CATEG-001 vs Q-CATEG-002.
- **BR-CATEG-013** — `metaTypes` is **not** part of the product-category model; it is an OFML metatype property record (`go_types`). No category logic depends on it. Source: `metaTypes.cs`.

---

## 7. Hidden Logic

- **`DisplayOrder = -1 → 9999` convention** — `-1` is a magic "unordered / send to bottom" sentinel, re-expressed as `9999` in `ORDER BY` via `CASE`. Appears in multiple files (CADMaintenance ~9092, ~6522), so it is a cross-module convention, not a local hack.
- **Synthetic id `999` = "< SP Components >"** — A hardcoded pseudo-category injected into the selector, representing SuperProduct components; it has no `ProductCategory`/`CatalogueProductCategories` row. Downstream code must special-case `999`.
- **Duplicate-name disambiguation** — Appending `(id)` to repeated descriptions is a UI workaround for non-unique localized names.
- **Dead reorder path** — Category-level ordering is fully coded but unreachable (BR-CATEG-010) and additionally broken (BR-CATEG-011).
- **`metaTypes.cs` misfiling risk** — Named suggestively but unrelated to categories; it is an OFML/GO `go_types` property holder. Documented here to prevent mis-association.

---

## 8. UI Behaviour

- Selecting a catalogue repopulates `category_selector` (clears items + `_categoryIdList`, re-queries Q-CATEG-001). Source: `CADMaintenance.cs` ~9089.
- The "< SP Components >" entry always appears at the bottom of the category list (BR-CATEG-005).
- Categories appear sorted by display order, with unordered ones (`-1`) sinking to the end (BR-CATEG-003).
- Duplicate category names show a trailing `(id)` to distinguish them (BR-CATEG-004).
- On category selection the code hides `GroupBox1`, `GroupBox2`, `list_dwglayers` while rebuilding the list (transient UI reset). Source: `CADMaintenance.cs` ~9087.
- There is **no in-app category create/rename/delete/reorder** reachable here; category re-ordering UI exists but is never opened (BR-CATEG-010). Category master maintenance is presumed handled by the external `DPS.exe` (see `03_Catalogues.md` BR-CAT-002) — exact location `UNKNOWN`.

---

## 9. Dependencies

| Dependency | Role |
|---|---|
| `ConnectionFactory.CreateNewConnection(autoOpen:true)` | Opens the `SqlConnection`. |
| `Global` | Server/DB target for the connection. |
| `CADMaintenance` form | Primary category consumer (selector, image, report). |
| `OrderCategories` form | Dead category-reorder path (module 16). |
| `AddDataList` | Category-scoped data picker (`initialiseDataList`). |
| DB tables | `ProductCategory`, `CatalogueProductCategories`, `OtherDescription`, `Catalogue`. |
| Related tables | `Handbook`/`HandbookProducts` (join to CPC in AddDataList ~383), `ProductRange` (categorized via `pr.ProductCategoryId`, see BOMExport). |

---

## 10. Risks

- **R-CATEG-1 (High, feature gap):** No functional in-app product-category reorder or CRUD — the coded reorder path is dead (BR-CATEG-010) and broken (BR-CATEG-011); master category maintenance likely lives in external `DPS.exe`. Migration cannot fully derive category CRUD from this repo.
- **R-CATEG-2 (High, security):** SQL injection via concatenated `CatalogueId` / `ProductCategoryId` / `objectId` in every category query.
- **R-CATEG-3 (Medium, latent bug):** Q-CATEG-002 has a missing-space concatenation defect; if the dead path is ever revived, it throws. Do not port verbatim.
- **R-CATEG-4 (Medium, correctness):** The `-1 → 9999` sentinel and synthetic id `999` are implicit contracts spread across files; any new code must replicate both or categories mis-sort / SP components vanish.
- **R-CATEG-5 (Medium, i18n):** `LanguageId = 1` is hardcoded in CADMaintenance category loads, so non-base-language users may see English category names regardless of locale.
- **R-CATEG-6 (Low, data quality):** Non-unique localized category names are patched at the UI layer with `(id)` suffixes rather than fixed in data — masks underlying duplication.
- **R-CATEG-7 (Low, coupling):** Downstream code must special-case category id `999`; missing that branch breaks SuperProduct-component handling.
- **R-CATEG-8 (Low, misclassification):** `metaTypes.cs` naming invites confusion with categories; keep OFML metatype logic in the generation module (16 §7 / OFML docs), not here.
