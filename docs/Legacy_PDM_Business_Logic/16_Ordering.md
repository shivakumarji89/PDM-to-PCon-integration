# 16 — Ordering (Display Order of Catalogues & Product Categories)

**Module prefix:** BR-ORD
**Primary legacy source:**
- `PDMMaintenance/OrderCategories.cs` (~206 lines — the display-order editor form)
- `PDMMaintenance/ProductDescriptions.cs` (`SortButton_Click` ~13106, `AlphaButton_Click` ~13124 — the only launch points)
- `PDMMaintenance/metaTypes.cs` (**not** ordering — clarified in §7)

**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

"Ordering" here means the user-controlled **presentation order** (`DisplayOrder` ordinal) of two entity kinds:

1. **Catalogues** — the order catalogues appear in downstream browsers/exports.
2. **Product categories within a catalogue** — the order categories appear inside a catalogue.

Both are edited through a **single reusable modal form, `OrderCategories`**, which switches its behaviour based on the `catalogueId` field:

- `catalogueId == -1` → edit `Catalogue.DisplayOrder` (order the catalogues).
- `catalogueId > 0` → edit `CatalogueProductCategories.DisplayOrder` for that catalogue (order the categories).

The form renders one row per entity: a read-only description textbox plus an editable ordinal textbox; **Submit Changes** writes every edited ordinal back with individual `UPDATE` statements.

> **Scope reality:** Only the **catalogue** path (`catalogueId == -1`) is actually reachable — the sole caller passes `-1`. The category path is present but never invoked (see BR-ORD-011, and `04_Product_Categories.md` BR-CATEG-010). The alphabetical-sort alternative is a dead stub (BR-ORD-012).

---

## 2. Entry Points

| Entry point | Location | Trigger |
|---|---|---|
| **"Sort" button** (`SortButton`) | `ProductDescriptions.cs` `SortButton_Click` ~13106 | If a catalogue is selected, opens `OrderCategories` modally with `catalogueId = -1`, `languageId = <selected language>`. |
| **`OrderCategories` form load** | `OrderCategories.cs` `OrderCategories_Load` ~103 | Builds the row list (catalogues or categories) from SQL. |
| **"Submit Changes" button** (`SubmitButton`) | `OrderCategories.cs` `SubmitButton_Click` ~178 | Writes each edited ordinal back to the DB. |
| **Ordinal textbox events** | `dispbox_Enter` ~161, `dispbox_MouseUp` ~167 | Select-all on focus/click for quick overtype. |
| **"Alpha" button** (`AlphaButton`) | `ProductDescriptions.cs` `AlphaButton_Click` ~13124 | Confirm dialog only; **no action** (dead — BR-ORD-012). |

The category path (`catalogueId > 0`) has **no entry point** (BR-ORD-011).

---

## 3. Call Hierarchy

```
ProductDescriptions (Form)
 └─ SortButton_Click                              [ProductDescriptions.cs ~13106]
      └─ if (catalogue_selector.SelectedIndex > -1)
           └─ new OrderCategories()
                orderCategories.catalogueId = -1
                orderCategories.languageId  = <_languageIdList[language_selector.SelectedIndex]>
                orderCategories.ShowDialog(this)          ← modal

OrderCategories (Form)
 ├─ ctor: catalogueId = -1, languageId = 1                [OrderCategories.cs ~59]
 ├─ OrderCategories_Load                                   [~103]
 │    └─ ConnectionFactory.CreateNewConnection(autoOpen:true)
 │         ├─ catalogueId == -1 → Q-ORD-002 (Catalogue)   → title "Order Catalogues"
 │         └─ catalogueId  >  0 → Q-ORD-001 (CPC)  DEAD    → title "Order Product Categories"
 │    └─ foreach row: add read-only desc TextBox + editable ordinal TextBox (Tag = id)
 └─ SubmitButton_Click                                     [~178]
      └─ ConnectionFactory.CreateNewConnection(autoOpen:true)
           └─ foreach TextBox in Panel1 where Tag > 0:
                ├─ catalogueId == -1 → Q-ORD-003 UPDATE Catalogue
                └─ catalogueId  >  0 → Q-ORD-004 UPDATE CatalogueProductCategories  DEAD
```

No Controller/Service/Repository layer — inline ADO.NET, string-concatenated SQL directly in the form.

---

## 4. SQL Analysis

### Q-ORD-001 — Load categories to order (SELECT, DEAD path)
**Source:** `OrderCategories.cs` `OrderCategories_Load`, line ~112 (built as the default `cmdText`, overwritten when `catalogueId == -1`)
```sql
SELECT cpc.ProductCategoryId, cpc.DisplayOrder,
       CASE WHEN od.ShortDescription IS NULL THEN cpc.Name
            ELSE od.ShortDescription END AS ShortDescription
FROM CatalogueProductCategories cpc
LEFT OUTER JOIN OtherDescription od
     ON cpc.DescriptionId = od.DescriptionId AND od.LanguageId = <languageId>
WHERE cpc.CatalogueId = <catalogueId>ORDER BY cpc.DisplayOrder
```
**WHY:** Intended to list a catalogue's categories with current ordinals for editing. **Never executed** (no caller sets `catalogueId > 0`). Contains a **missing-space bug** before `ORDER BY` (`<catalogueId>ORDER BY`) → invalid SQL if run (BR-ORD-013).

### Q-ORD-002 — Load catalogues to order (SELECT) — the live path
**Source:** `OrderCategories.cs` `OrderCategories_Load` (`catalogueId == -1` branch), line ~117
```sql
SELECT CatalogueId, DisplayOrder,
       CASE WHEN od.ShortDescription IS NULL THEN Catalogue.Name
            ELSE od.ShortDescription END AS ShortDescription
FROM Catalogue
LEFT OUTER JOIN OtherDescription od
     ON Catalogue.DescriptionId = od.DescriptionId AND od.LanguageId = <languageId>
ORDER BY DisplayOrder
```
**WHY:** Lists **all** catalogues (no permission filter here) with current `DisplayOrder`, localized name falling back to `Catalogue.Name`, sorted by current order for editing.

### Q-ORD-003 — Persist catalogue order (UPDATE) — the live path
**Source:** `OrderCategories.cs` `SubmitButton_Click` (`catalogueId == -1` branch), line ~193
```sql
UPDATE Catalogue SET DisplayOrder = <textBox.Text> WHERE CatalogueId = <textBox.Tag>
```
**WHY:** Writes the user-entered ordinal for one catalogue. Executed once per edited row (`Tag > 0`).

### Q-ORD-004 — Persist category order (UPDATE, DEAD path)
**Source:** `OrderCategories.cs` `SubmitButton_Click` (`catalogueId != -1` branch), line ~201
```sql
UPDATE CatalogueProductCategories
SET DisplayOrder = <textBox.Text>
WHERE ProductCategoryId = <textBox.Tag>
  AND CatalogueId = <catalogueId>
```
**WHY:** Would write a reordered category ordinal scoped to a catalogue. Never reached (BR-ORD-011).

> **Injection note:** `textBox.Text` (the ordinal) and `textBox.Tag` (the id) are concatenated raw into the `UPDATE`. `textBox.Text` is a **free-text** field with no numeric validation before it is written into `SET DisplayOrder = <text>` — an injection/data-integrity vector (BR-ORD-009, R-ORD-2).

---

## 5. Data Model

### `Catalogue` (ordered by Q-ORD-002/003)
| Column | Notes |
|---|---|
| `CatalogueId` | int PK; also the row `Tag`. |
| `DisplayOrder` | int ordinal being edited. |
| `Name` | Fallback display name. |
| `DescriptionId` | FK → `OtherDescription`. |

### `CatalogueProductCategories` (ordered by Q-ORD-001/004 — dead)
| Column | Notes |
|---|---|
| `ProductCategoryId` | Row `Tag` in the category path. |
| `CatalogueId` | Scope filter for the UPDATE. |
| `DisplayOrder` | int ordinal. |
| `Name` | Fallback display name. |
| `DescriptionId` | FK → `OtherDescription`. |

### `OtherDescription`
| Column | Notes |
|---|---|
| `DescriptionId` | Join key. |
| `LanguageId` | Caller-supplied `languageId` (defaults to `1`). |
| `ShortDescription` | Localized name. |

**Relationships:** see `03_Catalogues.md` and `04_Product_Categories.md`. Ordering is a property (`DisplayOrder`) on these existing tables — no dedicated ordering table.

### In-memory row model (per UI row)
| Control | Data |
|---|---|
| `TextBox` (read-only, `Tag = 0`) | Description text (`ShortDescription`). |
| `TextBox` (editable) | `DisplayOrder` text; `Tag` = `CatalogueId` (catalogue path) or `ProductCategoryId` (category path). |

---

## 6. Business Rules

- **BR-ORD-001** — `OrderCategories` defaults to `catalogueId = -1` and `languageId = 1` on construction. Source: `OrderCategories.cs` ctor ~59.
- **BR-ORD-002** — When `catalogueId == -1`, the form orders **catalogues** and sets its title to **"Order Catalogues"**; otherwise it orders **product categories** with title **"Order Product Categories"**. Source: `OrderCategories_Load` ~116 / `InitializeComponent` default text.
- **BR-ORD-003** — The catalogue path lists **all** catalogues with **no per-user permission filter** (unlike the catalogue dropdown in `03_Catalogues.md` Q-CAT-001). Any user who can open the Sort dialog can reorder every catalogue. Source: Q-ORD-002 (no `PDMUserCatalogues` join).
- **BR-ORD-004** — Rows are initially listed in current `DisplayOrder` order (`ORDER BY DisplayOrder`). Source: Q-ORD-002 (and Q-ORD-001 for the dead path).
- **BR-ORD-005** — Each row shows a localized description (`OtherDescription.ShortDescription` for the given `LanguageId`), falling back to the entity's `Name` when no translation exists. Source: Q-ORD-002 `CASE WHEN od.ShortDescription IS NULL`.
- **BR-ORD-006** — The description textbox is **read-only** (`ReadOnly = true`); only the ordinal textbox is editable. Source: `OrderCategories_Load` ~133.
- **BR-ORD-007** — Each editable ordinal textbox stores its entity id in `Tag` (catalogue → `CatalogueId`; category → `ProductCategoryId`). Source: `OrderCategories_Load` ~140–147.
- **BR-ORD-008** — On Submit, only textboxes whose `Tag` parses to an integer **> 0** are written; the read-only description boxes (`Tag = 0`) and any non-`TextBox` controls are skipped. Source: `SubmitButton_Click` ~184–190.
- **BR-ORD-009** — The ordinal value written is the **raw textbox text** with no numeric validation, range check, or de-duplication — the user may enter any string, and duplicate ordinals are permitted. Source: `SubmitButton_Click` (`SET DisplayOrder = <textBox.Text>`).
- **BR-ORD-010** — Submit disables the Submit button first (`SubmitButton.Enabled = false`) to prevent double-submit, and writes one `UPDATE` per edited row (no transaction/batch). Source: `SubmitButton_Click` ~181.
- **BR-ORD-011** — The **category-ordering path is dead**: the only caller (`ProductDescriptions.SortButton_Click`) always sets `catalogueId = -1`. `Q-ORD-001`/`Q-ORD-004` never execute. Source: `ProductDescriptions.cs` ~13111.
- **BR-ORD-012** — The alternative **"sort alphabetically"** action (`AlphaButton`) is a **dead stub**: it confirms with the user then executes nothing. Source: `ProductDescriptions.cs` `AlphaButton_Click` (empty `Yes` branch).
- **BR-ORD-013** — The dead category query (Q-ORD-001) has a **missing space** before `ORDER BY`, so it would raise a SQL error if the category path were ever enabled. Source: `OrderCategories.cs` ~112.
- **BR-ORD-014** — Sort can only be launched when a catalogue is currently selected (`if (catalogue_selector.SelectedIndex > -1)`). Source: `ProductDescriptions.cs` `SortButton_Click` ~13109. (Note: the selected catalogue is irrelevant to the query — the form orders *all* catalogues regardless.)
- **BR-ORD-015** — The form widens itself and its panel by +20px on load (`base.Width += 20; Panel1.Width += 20`) — a layout workaround executed every open. Source: `OrderCategories_Load` ~108.
- **BR-ORD-016** — Rows are laid out at fixed 20px vertical pitch (`Location = new Point(6, 20 * num)` / `(246, 20 * num)`); the description box is 240px wide, the ordinal box 60px. Source: `OrderCategories_Load` ~135–150.
- **BR-ORD-017** — Focusing or clicking an ordinal textbox selects all its text (`dispbox_Enter` / `dispbox_MouseUp` → `SelectAll()`) for quick overtyping. Source: `OrderCategories.cs` ~161–171.
- **BR-ORD-018** — On any load/submit exception the raw exception string is shown via `Interaction.MsgBox(ex.ToString())` and swallowed (`ClearProjectError`); the operation is not rolled back. Source: `OrderCategories_Load` catch ~152, `SubmitButton_Click` catch.
- **BR-ORD-019** — Connections are always closed in a `finally` (`sqlConnection?.Close()`); the `checked` arithmetic context is used for the row-counter increments. Source: `OrderCategories.cs` ~104/172.

---

## 7. Hidden Logic

- **Sentinel `catalogueId = -1` = "order catalogues, not categories"** — the entire form mode switch hinges on this magic value.
- **`languageId` default `1`** — base language fallback baked into the ctor.
- **`Tag`-as-id / `Tag = 0`-as-marker** — the ordinal box carries the entity id in `Tag`; the read-only description box uses `Tag = 0` so Submit skips it. Overloading `Tag` for two meanings.
- **Layout `+20px` hack** — width bump on every open (BR-ORD-015); likely a decompilation-era fix for a clipped panel.
- **Dead category path + dead alpha-sort** — two coded-but-unreachable features (BR-ORD-011, BR-ORD-012); the category path is also latently broken (BR-ORD-013).
- **No permission filter on catalogue ordering** — unlike every other catalogue query in the app (BR-ORD-003) — an implicit privilege gap.
- **`metaTypes.cs` is unrelated** — despite living near "ordering/category" code, `metaTypes` (`fileName = "go_types"`) holds OFML metatype property definitions (`product`, `propertyName`, `propertyFormat`, `defaultValue`, `propertyMode`, `propertyParent`) via `getAllProperties()`. It has **no SQL and no ordering behaviour**. It belongs to the OFML/GO generation domain, not this module. Documented here only to record that the file was examined and found **not** to implement ordering or categories.

---

## 8. UI Behaviour

- The Sort dialog opens modally (`ShowDialog`) over `ProductDescriptions`; the parent is blocked until it closes.
- One row per catalogue: a wide read-only name box (left) and a narrow editable ordinal box (right), stacked at 20px pitch inside an auto-scrolling `Panel1`.
- Entering/clicking an ordinal box selects all text for immediate overtype (BR-ORD-017).
- "Submit Changes" disables itself, then applies each edited ordinal via a separate `UPDATE`; there is **no** progress bar, no success confirmation, and no auto-close in the read scope (`UNKNOWN` whether the form closes after submit).
- New ordinals take effect only after the consuming views re-query (`DisplayOrder`), e.g. next time catalogues are listed; the ordering form itself does not refresh the parent.
- Because the form lists **all** catalogues (BR-ORD-003), the catalogue the user had selected in the parent has no special role — it merely had to be non-empty to enable the button (BR-ORD-014).
- Duplicate or non-numeric ordinals are accepted silently (BR-ORD-009), so the resulting sort can be arbitrary/unstable.

---

## 9. Dependencies

| Dependency | Role |
|---|---|
| `ConnectionFactory.CreateNewConnection(autoOpen:true)` | Opens the `SqlConnection`. |
| `Global` | Server/DB target for the connection. |
| `ProductDescriptions` form | Sole launcher (`SortButton`), supplies `languageId`. |
| `Microsoft.VisualBasic` (`Conversions`, `Interaction`, `ProjectData`) | Decompiled VB runtime: string conversion, `MsgBox`, error plumbing. |
| DB tables | `Catalogue` (live), `CatalogueProductCategories` (dead path), `OtherDescription`. |
| Consumers of `DisplayOrder` | `03_Catalogues.md` (Q-CAT-002), `04_Product_Categories.md` (Q-CATEG-001/005), plus browsers/exports that `ORDER BY DisplayOrder`. |

---

## 10. Risks

- **R-ORD-1 (High, security/authorization):** Catalogue ordering has **no per-user permission filter** (BR-ORD-003) — any user reaching the Sort dialog reorders **all** catalogues globally, unlike every other catalogue operation. Privilege-escalation-flavoured design gap.
- **R-ORD-2 (High, security/integrity):** The ordinal value is unvalidated free text concatenated into `UPDATE ... SET DisplayOrder = <text>` (BR-ORD-009) — SQL injection and non-numeric corruption of `DisplayOrder`.
- **R-ORD-3 (Medium, data quality):** Duplicate ordinals are allowed and no gap/normalisation is enforced, so sort order can be non-deterministic; combined with the `-1 → 9999` convention (see 04) results can surprise.
- **R-ORD-4 (Medium, latent bug):** The category-ordering path is dead **and** broken (missing-space SQL, BR-ORD-013); reviving it requires a fix, not just wiring a caller.
- **R-ORD-5 (Medium, concurrency):** Per-row `UPDATE`s with no transaction (BR-ORD-010) — a mid-submit failure leaves ordering partially applied; concurrent editors are last-writer-wins.
- **R-ORD-6 (Low, UX):** Dead "sort alphabetically" button (BR-ORD-012) misleads users into thinking a bulk sort exists.
- **R-ORD-7 (Low, migration mapping):** `metaTypes.cs` is easily mis-scoped into this module by name; keep OFML metatype handling in the generation/OFML docs, not ordering (§7).
- **R-ORD-8 (Low, i18n):** Description fallback relies on `OtherDescription`/`languageId`; if `languageId` defaults to `1` (ctor) and the caller forgets to set it, users see base-language names regardless of locale.
