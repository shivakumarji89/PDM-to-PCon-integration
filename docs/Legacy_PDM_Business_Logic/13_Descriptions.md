# 13 — Descriptions (Description Maintenance UI)

**Module prefix:** BR-DESC
**Primary legacy source:** `PDMMaintenance\ProductDescriptions.cs` (~13003 lines), `PDMMaintenance\DescriptionsFindReplace.cs` (~561 lines), `PDMMaintenance\metaDescriptions.cs` (20 lines)
**Status:** Verified from source unless marked `UNKNOWN`.

> Scope split: this document covers the **description-maintenance user interface** — the multi-tab `ProductDescriptions` form, how each entity's descriptions are listed/filtered/edited, the text-content rules (casing, character replacements, escaping, length limits), application-text handling, programmatic/template descriptions, and the Find & Replace mechanics. **Multi-language storage, language selection, and fallback** are documented in [12_Translations.md](12_Translations.md); this file cross-references them (`Q-TRAN-*` / `BR-TRAN-*`) rather than repeating.

---

## 1. Purpose

`ProductDescriptions` is the central **description maintenance** screen. It is a single mega-form hosting a `TabControl` (`TabSelector`) whose ~15 tabs each maintain the descriptive text of a different PDM entity — products, attributes, attribute values, options, option values, ranges, catalogue categories, catalogues, fabrics, "other" (DPSText), handbooks, handbook groups, super-product components and items. It lets a user:

- Pick a **catalogue** and (optionally) a **category** context, then browse a grid of entities.
- Filter the grid (all / blank / missing / show-all-products / by fabric band, etc.).
- Edit `ShortDescription`, `LongDescription` and `ApplicationText` (per language) and submit them to the DB.
- Apply catalogue- or pricebook-specific application text overrides.
- Generate descriptions programmatically from an attribute-token template.
- Find & replace text across a product list.
- Manage adjacent product metadata reachable from the same grid (images, fabric bands, option/fabric status, supplier, composition) — those are secondary and only summarised here.

`metaDescriptions.cs` is an inert 3-field DTO and holds no UI logic (`metaDescriptions.cs:1-20`).

---

## 2. Entry Points

| Entry point | Location | Trigger |
|---|---|---|
| `ProductDescriptions` constructor / `Load` | `ProductDescriptions.cs:3090+` | Main Menu **Product Descriptions** button (`MainMenu.cs:2743`), gated by `DescriptionMaintenance` (`MainMenu.cs:3029`). |
| `initialiseComboBoxes` / load block | `ProductDescriptions.cs:4580-4767` | Populates catalogue, category, language, site, supplier, fabric-band dropdowns. |
| `TabSelector_SelectedIndexChanged` | `ProductDescriptions.cs:7412` | Switches entity type; reconfigures buttons and reloads the grid. |
| `catalogue_selector_SelectedIndexChanged` | `ProductDescriptions.cs:1150`→`catalogueSelection` | Changes catalogue context. |
| `category_selector_SelectedIndexChanged` | `ProductDescriptions.cs:7297` | Changes category context. |
| `updateDataGrid(int)` | `ProductDescriptions.cs:~6120` | Rebuilds the entity grid for the current tab/filters. |
| `selectRow` / row-select handler | `ProductDescriptions.cs:~7760-7935` | Loads the selected entity's descriptions into the edit boxes. |
| `submitData()` | `ProductDescriptions.cs:8920` | Persists product-tab edits (`ProductDescription`, `CatalogueApplicationText`, `Product.Name`, images). |
| `modifyOtherDescription(...)` | `ProductDescriptions.cs:8512` | Persists non-product-tab edits (`OtherDescription` + owning entity `Name`). |
| `AppTextButton_Click` | `ProductDescriptions.cs:1209` | "Translated Application Text". |
| `apptext_selector_SelectedIndexChanged` | `ProductDescriptions.cs:713` | Switches Default / Catalogue / Pricebook application text. |
| `TranslationButton_Click` | `ProductDescriptions.cs:10543` | Opens Find & Replace dialog (see 12_Translations, BR-TRAN-020). |
| `button_prog_update_Click` | `ProductDescriptions.cs:~13360` | Applies template-generated descriptions in bulk. |
| `generateProgrammaticDescription(...)` | `ProductDescriptions.cs:~13255` | Builds a description from an attribute-token template. |
| `SortButton_Click` | `ProductDescriptions.cs:13105` | Opens `OrderCategories` (catalogue ordering; see 16_Ordering). |
| `RadioAll/RadioBlank/RadioMissing_CheckedChanged` | `ProductDescriptions.cs:10405-10416` | Grid filter radios. |

---

## 3. Call Hierarchy

```
MainMenu (ProdDescButton, gated by DescriptionMaintenance)
  └─> ProductDescriptions (form)                                   [Form]
        ├─ Load ─> initialise dropdowns (catalogue/category/language/site/…)   [Q-DESC-013..]
        │
        ├─ TabSelector_SelectedIndexChanged   [Event]  (choose entity type)
        │     └─ updateDataGrid()             [Controller]
        │           └─ per-tab list SELECT (Products / Attributes / Options / …)  [Q-DESC-001..012]
        │
        ├─ row-select                          [Event]
        │     ├─ product text fetch (+catalogue/pricebook app text, lifestyle)    [Q-DESC-020]
        │     └─ secondary-language fetch (see 12_Translations Q-TRAN-002/003)
        │
        ├─ Submit / SubmitNext                 [Event]
        │     ├─ TabSelector==0 → submitData()                     [Controller]
        │     │     ├─ ProductDescription UPSERT                   [Q-DESC-021/022]
        │     │     ├─ CatalogueApplicationText INSERT/UPDATE/DELETE [Q-DESC-023..025]
        │     │     ├─ Product.Name sync (English only)            [Q-DESC-026]
        │     │     └─ Product images UPDATE                       [Q-DESC-027]
        │     └─ TabSelector>0  → modifyOtherDescription()         [Controller]
        │           ├─ OtherDescription UPSERT / new-id spawn      [Q-TRAN-007..010]
        │           └─ owning entity Name UPDATE                   [Q-DESC-030]
        │
        ├─ apptext_selector_SelectedIndexChanged  [Event]  (Default/Catalogue/Pricebook)
        ├─ TranslationButton_Click               → DescriptionsFindReplace (see 12_Translations)
        └─ button_prog_update_Click            [Event]
              └─ generateProgrammaticDescription() → bulk UPDATE ProductDescription  [Q-DESC-040/041]
```

No Service/Repository layer: handlers build inline SQL and execute directly.

---

## 4. SQL Analysis

All SQL is inline-concatenated (injection-prone). Language id comes from `_languageIdList[...]` (see 12_Translations). Only the description-centric queries are listed; image/fabric-band/status queries are cross-referenced to 09/10/17 and not re-quoted in full.

### Q-DESC-001 — Products grid (Products tab)
`ProductDescriptions.cs:6130` (base), joined per filter
```sql
SELECT DISTINCT Product.ProductId, Product.Product, Product.Name AS Description, Product.NewProduct
FROM Product
INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
INNER JOIN Item ON Product.ProductId = Item.ProductId
LEFT OUTER JOIN ProductDescription pd ON Product.DescriptionId = pd.DescriptionId
       AND pd.LanguageId = <primaryLanguageId>            -- appended at 6137/6153/6168
```
**WHY:** Lists products for the selected category/catalogue with their current primary-language description via a `LEFT OUTER JOIN` (so products lacking a translation still appear — supports the "Missing" filter). `DISTINCT` collapses multiple `Item` rows per product.

### Q-DESC-002..010 — Non-product entity grids
Base pattern `SELECT DISTINCT <id>, <displayorder>, <name> … LEFT OUTER JOIN OtherDescription od ON <entity>.DescriptionId = od.DescriptionId AND od.LanguageId = <primaryLanguageId>`:

| Q-ID | Tab | Line | Entity |
|---|---|---|---|
| Q-DESC-002 | Attributes | 6268 | `Attribute` (+`WebMenuAttribute`, `EOSLiteDisplayOrder`) |
| Q-DESC-003 | AttributeValues | 6322 | `AttributeValue` (+`CatalogueAttributeValues`) |
| Q-DESC-004 | Options | 6362 | `[Option]` (UNION default+catalogue) |
| Q-DESC-005 | OptionValues | 6414 | `OptionValue` (+`CatalogueOptionValues`, `FSCCompliant`) |
| Q-DESC-006 | Range | 6484 | `ProductRange` (+`CatalogueProductRanges`) |
| Q-DESC-007 | Category | 6522 | `CatalogueProductCategories` (DisplayOrder −1→9999) |
| Q-DESC-008 | Catalogue | 6563 | `Catalogue` |
| Q-DESC-009 | FabType/FabColours | 6638 / 6815 | `OptionValue` fabric variants |
| Q-DESC-010 | Other | 6942 | `SELECT DISTINCT DPSTextId, Description AS Text FROM DPSText` |

**WHY:** Each tab maps to a table via `getTableNameFromTabIndex()` (`8463-8511`) / `getTableName(tabname)` (`8514-8562`); the grid always shows the entity's primary-language `OtherDescription.ShortDescription`, `LEFT OUTER` so untranslated entities still list. `CatalogueProductCategories.DisplayOrder = -1` is mapped to `9999` to sort last (`CASE WHEN cpc.DisplayOrder = -1 THEN 9999 ELSE cpc.DisplayOrder END`).

### Q-DESC-011 — Handbook groups grid
`ProductDescriptions.cs:7002` — `SELECT DISTINCT hbp.ProductGroupId, hbp.GroupName AS ProductGroup, hbp.ProductListEntry AS PrimaryProduct FROM …` (HandbookProducts).
### Q-DESC-012 — SP components / items grids
`ProductDescriptions.cs:7029` (products via `Item`), `7056` (`Item.ItemId, Item.Item`), plus a placeholder single-row form `SELECT '<id>' AS Id, … AS Description` (`7100`) and the `ItemId = -1` empty guard (`7108`).

### Q-DESC-013 — Catalogue dropdown (with per-user read-only)
`ProductDescriptions.cs:4589`
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly
FROM PDMUserCatalogues puc INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId
WHERE puc.UserId = <UserId>
```
**WHY:** Fills `catalogue_selector` and the parallel `_readOnlyCatalogues` list. In **this module** `ReadOnly == 0` is treated as **editable** (`catalogueIsReadOnly` returns `false`) — literal interpretation (see Risks / BR-DESC-032).

### Q-DESC-014 — Category dropdown for the catalogue
`ProductDescriptions.cs:4849`
```sql
SELECT DISTINCT pc.ProductCategoryId, od.ShortDescription,
  CASE WHEN cpc.DisplayOrder = -1 THEN 9999 ELSE cpc.DisplayOrder END AS cpcDO
FROM ProductCategory pc
INNER JOIN CatalogueProductCategories cpc ON pc.ProductCategoryId = cpc.ProductCategoryId
INNER JOIN OtherDescription od ON cpc.DescriptionId = od.DescriptionId AND od.LanguageId = 1
WHERE <catalogue filter>
```
**WHY:** Category names are always shown in English (`od.LanguageId = 1`) in the picker; ordering uses the −1→9999 rule.

### Q-DESC-015 — Language dropdowns
See [12_Translations.md](12_Translations.md) Q-TRAN-001.

### Q-DESC-020 — Load a product's descriptions on row-select
`ProductDescriptions.cs:7808`
```sql
SELECT pd.DescriptionId, pd.ShortDescription, pd.LongDescription, pd.ApplicationText,
       cat.ApplicationText AS CatalogueApplicationText,
       pricebook.ApplicationText AS PricebookAppText,
       pd1.MarketingDescription AS Lifestyle
FROM ProductDescription pd
INNER JOIN Product ON pd.DescriptionId = Product.DescriptionId
LEFT OUTER JOIN CatalogueApplicationText cat ON Product.ProductId = cat.ProductId
       AND cat.LanguageId = <primaryLanguageId> AND cat.CatalogueId = <catalogueId>
LEFT OUTER JOIN CatalogueApplicationText pricebook ON Product.ProductId = pricebook.ProductId
       AND pricebook.LanguageId = <primaryLanguageId> AND pricebook.CatalogueId = (-1 * <catalogueId>)
LEFT OUTER JOIN ProductDescription pd1 ON pd.DescriptionId = pd1.DescriptionId AND pd1.LanguageId = 1
WHERE Product.ProductId = <objectId> AND pd.LanguageId = <primaryLanguageId>
```
**WHY:** Single query that gathers, for the primary language: base app text, catalogue-specific app text (`cat`), pricebook app text (negative catalogue id, `pricebook`), and the lifestyle text (always English via `pd1`). Drives the `apptext_selector` default choice (BR-DESC-021).

### Q-DESC-021 — Product description exists? (submit)
`ProductDescriptions.cs:8835` — `SELECT DescriptionId FROM ProductDescription WHERE DescriptionId = <id> AND LanguageId = <primaryLanguageId>` (decides UPDATE vs INSERT).
### Q-DESC-022 — Product description UPSERT
`ProductDescriptions.cs:8862` (UPDATE) / `8943` (INSERT) / `8931` new-id (`SELECT TOP 1 DescriptionId FROM ProductDescription ORDER BY DescriptionId DESC`) / `8951` (`UPDATE Product SET DescriptionId = …`).
```sql
UPDATE ProductDescription SET ShortDescription = N'…', LongDescription = N'…' [, ApplicationText = N'…']
WHERE DescriptionId = <id> AND LanguageId = <primaryLanguageId>
-- or
INSERT INTO ProductDescription (DescriptionId, LanguageId, ShortDescription, LongDescription, ApplicationText)
VALUES (<id>, <primaryLanguageId>, N'…', N'…', N'…')
```
**WHY:** Manual UPSERT; empty text boxes become `NULL` (BR-DESC-013). New products allocate `MAX(DescriptionId)+1` and back-link `Product.DescriptionId`.

### Q-DESC-023..025 — Catalogue / Pricebook application text
`ProductDescriptions.cs:8875` (INSERT catalogue), `8895` (INSERT pricebook, `-1 * CatalogueId`), `8879`/`8899` (`DELETE FROM CatalogueApplicationText …`), plus in-place `UPDATE CatalogueApplicationText SET ApplicationText = N'…'`.
```sql
INSERT INTO CatalogueApplicationText (CatalogueId, ProductId, LanguageId, ApplicationText)
VALUES (<catId | -1*catId>, <productId>, <primaryLanguageId>, N'<text>')
```
**WHY:** `apptext_selector`: **0 = Default** (writes `ProductDescription.ApplicationText`), **1 = Catalogue** (positive `CatalogueId`), **2 = Pricebook** (`-1 * CatalogueId`). Empty text triggers a DELETE of the override (BR-DESC-023). A guard prevents executing a bare `DELETE FROM CatalogueApplicationText` with no WHERE (`8914`).

### Q-DESC-026 — Sync `Product.Name` from the English short description
`ProductDescriptions.cs:8921`
```sql
UPDATE Product SET Name = '<TextBox1 trimmed>' WHERE ProductId = <selectedId>
```
**WHY:** Only when editing **English** (`LanguageId = 1`) **and** the "Show All Products" / "Update Product Name Column" check is set and short text is non-empty (BR-DESC-026).

### Q-DESC-027 — Product images
`ProductDescriptions.cs:8957` — `UPDATE Product SET ImageFile = …, WFImageFile = …, DimImageFile = … WHERE ProductId = …`. (Image handling → 17_Images.)

### Q-DESC-030 — Owning-entity name sync (non-product tabs)
`ProductDescriptions.cs:8641, 8755, 8783` (`modifyOtherDescription`)
```sql
UPDATE <entityTable> SET Name = '<description>' WHERE <entity>Id = <originId>
```
plus special cases: `Handbook.HandbookName` (`8620`), `CatalogueProductCategories.Name` with an optional "update default category name too?" prompt (`8768-8779`), `HandbookProducts.GroupName` (`8779`). See 12_Translations Q-TRAN-007..010 for the `OtherDescription` writes.

### Q-DESC-040 — Programmatic description from attribute template
`ProductDescriptions.cs:~13255` (`generateProgrammaticDescription`) — see 12_Translations **Q-TRAN-012** (English-fallback attribute fetch). Template tokens `{id}` / `#{id}` / `~{id}` are replaced with attribute-value text.
### Q-DESC-041 — Bulk apply generated descriptions
`ProductDescriptions.cs:~13400`
```sql
UPDATE ProductDescription SET LongDescription = '<gen>' WHERE DescriptionId = <id> AND LanguageId = <lang>
-- if 0 rows and lang>1:
INSERT INTO ProductDescription (DescriptionId, LanguageId, ShortDescription, LongDescription)
VALUES (<id>, <lang>, '<gen>', '<gen>')
-- optionally ShortDescription + Product.Name (English) when ProgUpdateShortCheck set
```
**WHY:** Bulk template application across the filtered product list; short-desc/name updates are opt-in via `ProgUpdateShortCheck` (English-only for `Product.Name`).

### Q-DESC-050 — Find & Replace (product short description)
See [12_Translations.md](12_Translations.md) Q-TRAN-015/016 (`DescriptionsFindReplace`).

### Q-DESC-051 — "Other" descriptions bulk import/dedupe
`ProductDescriptions.cs:11156, 11173, 11196, 11219, 11227` — `SELECT DISTINCT ShortDescription FROM OtherDescription WHERE RelatedTable = '<tag>' AND LanguageId = 1 …` and matching/dedup by `LTRIM(REPLACE(ShortDescription, '''', '`'))`.
**WHY:** Reconciles free-text "Other"/DPS descriptions, deduping on English text with quote normalisation.

---

## 5. Data Model

Description storage tables (`ProductDescription`, `OtherDescription`, `CatalogueApplicationText`, `Language`, `CatalogueTranslations`) are defined in [12_Translations.md](12_Translations.md) §5. Description-UI-relevant facts:

- **Tab → table mapping** (`getTableNameFromTabIndex` `8463`, `getTableName` `8514`):
  | Tab idx | Tab text | Table |
  |---|---|---|
  | 0 | Products | `Product` / `ProductDescription` |
  | 1 | Attributes | `Attribute` |
  | 2 | AttributeValues | `AttributeValue` |
  | 3 | Options | `[Option]` |
  | 4 | OptionValues | `OptionValue` |
  | 5 | Range | `ProductRange` |
  | 6 | Category | `CatalogueProductCategories` |
  | 7 | Catalogue | `Catalogue` |
  | 8 / 9 | FabType / FabColours | `OptionValue` |
  | 10 | Other | `DPSText` |
  | 11 | Handbook | `Handbook` |
  | 12 | HBGroups | `HandbookProducts` |
  | 13 | SPComps | `Product` |
  | 14 | Items | `Item` |
- **`Product`**: `ProductId`, `Product` (code), `Name` (denormalised English short desc), `DescriptionId`, `NewProduct`, `ImageFile`/`WFImageFile`/`DimImageFile`, `ProductRangeId`.
- **Edit text boxes:** `TextBox1`=Short, `TextBox2`=Long, `TextBox3`=Application (primary language); `TextBox6/5/4`=Short/Long/App (secondary language, read-only compare).
- **`apptext_selector`** index: 0=Default, 1=Catalogue, 2=Pricebook.
- **`RelatedTable`** special tags written: `'[Option]'`, `'OptionCategoryMask'`, `'SPComponent'`, plus literal table names.

---

## 6. Business Rules

- **BR-DESC-001** — The form is a single mega-form; the active entity type is entirely determined by `TabSelector.SelectedIndex`, mapped to a table by `getTableNameFromTabIndex()`/`getTableName()`. (`ProductDescriptions.cs:8463-8562`)
- **BR-DESC-002** — Product text is edited/persisted via `submitData()`; **all other tabs** persist via `modifyOtherDescription()`. (`ProductDescriptions.cs:8920` / `8512`)
- **BR-DESC-003** — Every grid lists entities via a **`LEFT OUTER JOIN`** to the description table so entities without a translation still appear (enables the "Missing"/"Blank" filters). (Q-DESC-001..010)
- **BR-DESC-004** — Category picker and category grid always display **English** names (`od.LanguageId = 1`), independent of the editing language. (`Q-DESC-014`, `6522`)
- **BR-DESC-005** — `CatalogueProductCategories.DisplayOrder = -1` is coerced to `9999` for sorting (categories with no explicit order sink to the bottom). (`Q-DESC-007`, `Q-DESC-014`)
- **BR-DESC-006** — Grid filter radios: **All** / **Blank** / **Missing** rebuild the grid (`updateDataGrid(0)`). "Missing"/"Blank" rely on the outer-join null description. (`ProductDescriptions.cs:10405-10416`)
- **BR-DESC-007** — "Show All Products" (`ShowAllCheck`) widens the product list beyond the catalogue scope and, together with "Update Product Name Column", enables `Product.Name` sync on submit. (`ProductDescriptions.cs:3878`, `8916-8925`)
- **BR-DESC-008** — Product short description length is surfaced live in `countText`; **> 40 characters** turns the counter **red** (soft warning, not enforced). (`ProductDescriptions.cs:7831-7840`)
- **BR-DESC-009** — For pCon propagation a **hard 50-character** limit on short descriptions is enforced (product skipped with a warning) — see 12_Translations BR-TRAN-023. (`ProductDescriptions.cs:11618`)
- **BR-DESC-010** — Application text has three scopes selected by `apptext_selector`: **0 Default** → `ProductDescription.ApplicationText`; **1 Catalogue** → `CatalogueApplicationText` with positive `CatalogueId`; **2 Pricebook** → `CatalogueApplicationText` with `-1 * CatalogueId`. (`ProductDescriptions.cs:8862-8912`)
- **BR-DESC-011** — On row-select the app-text scope auto-defaults: Pricebook if the catalogue name contains `"Pricebook"`, else Pricebook if user has `DescriptionEdit & ReadOnlyFinancial`, else Catalogue if catalogue-specific text exists, else Default. (`ProductDescriptions.cs:7843-7862`)
- **BR-DESC-012** — Saving empty application text **DELETES** the catalogue/pricebook override row (and resets the selector to Default); a bare `DELETE FROM CatalogueApplicationText` with no WHERE is explicitly blocked. (`ProductDescriptions.cs:8879-8914`)
- **BR-DESC-013** — Empty `ShortDescription`/`LongDescription`/`ApplicationText` are written as SQL `NULL`, not empty strings. (`ProductDescriptions.cs:8863-8945`)
- **BR-DESC-014** — All persisted description text is stored as **Unicode** (`N'…'`) for descriptions; some name-sync writes use non-`N` string literals (e.g. `Product.Name`, `Handbook.HandbookName`). (`8629/8635` vs `8921/8620`)
- **BR-DESC-015** — CR/LF are stripped from product short/long text on submit (`Replace("\r","").Replace("\n","").Trim()`). (`ProductDescriptions.cs:8865-8869`)
- **BR-DESC-016** — Single quotes are escaped inconsistently: some paths use `'` → backtick (`Replace("'","`")`), others use `'` → `''` (`Replace("'","''")`). This is per-call, not centralised. (`ProductDescriptions.cs:9006, 8865-8912, 5095`)
- **BR-DESC-017** — For **English** attribute/option descriptions, text is normalised to camel-case via `SIFImport.camelCase(description, onlyFirstLetterUppercase: true, removeCarriageReturns: true)` — **except** when the attribute is named `"Size"` (`flag` skips it) and unless `ignoreCamelCase` is set. (`ProductDescriptions.cs:8579-8596`)
- **BR-DESC-018** — Description text has fixed content substitutions applied on save: `&` → `and`; `Cut-Out`/`Cut-out`/`Cut Out`/`Cut out` → `Cutout`; and `\r`/`\n` removed. (`ProductDescriptions.cs:8601-8607`)
- **BR-DESC-019** — Editing a shared/default `OtherDescription` may **spawn a new `DescriptionId`** (`SELECT TOP 1 … ORDER BY DescriptionId DESC` + 1) and re-point the owning entity, carrying existing translations across — full mechanics in 12_Translations BR-TRAN-018 / Q-TRAN-010. (`ProductDescriptions.cs:8649-8760`)
- **BR-DESC-020** — Option descriptions interact with a `ProductCategory.ProductCategoryMask` string (`descids:8=-1,28=-1,3344=-1,3346=-1,6790=-1,6791=-1`). For the fixed option ids 8/28/3344/3346/6790/6791 the mask is initialised if empty and rewritten so the option points at the new `DescriptionId`; those ids bypass the normal owning-entity `Name` update. (`ProductDescriptions.cs:8665-8760`)
- **BR-DESC-021** — Lifestyle/marketing text is read-only in this screen and always English (12_Translations BR-TRAN-009). (`Q-DESC-020`)
- **BR-DESC-022** — Products still get a `currentDescriptionId` resolved from `LanguageId = 1` even when the selected language row is missing, so a subsequent save attaches to the correct base id (this is an id-resolution fallback, **not** a text fallback — the boxes are still blanked). (`ProductDescriptions.cs:7908-7920`)
- **BR-DESC-023** — Product-name sync (`UPDATE Product SET Name`) only runs for **English** edits with a non-empty short description and the appropriate check set. (`ProductDescriptions.cs:8916-8925`)
- **BR-DESC-024** — On non-product tabs, editing the entity in **English** also updates the owning entity's `Name` column (Attribute/AttributeValue/Option/etc.), keeping the denormalised name aligned; non-English edits touch only `OtherDescription`. (`ProductDescriptions.cs:8624-8646, 8755-8783`)
- **BR-DESC-025** — For `CatalogueProductCategories`, saving an English name prompts "Update the default description for this Category in addition to the Catalogue instance?" (Yes updates `ProductCategory.Name`; Cancel skips the catalogue-instance update). (`ProductDescriptions.cs:8768-8779`)
- **BR-DESC-026** — Programmatic descriptions are built from a token template (`text_update_template`): `{id}` → lower-cased attribute-value text, `#{id}` → numeric-only value, `~{id}` → verbatim value; unresolved `{` blocks the bulk update with "At least one attribute key could not be resolved". (`ProductDescriptions.cs:13268-13290, ~13366`)
- **BR-DESC-027** — Programmatic "retain-case" list (`text_update_retain`, comma-separated) restores exact casing for listed words after lower-casing; abbreviation mode maps `Back-to-back`→`B2B`, `Single Sided`→`SS` (case variants). (`ProductDescriptions.cs:13278-13300`)
- **BR-DESC-028** — Bulk programmatic apply updates `LongDescription`; if no row for the language and `lang > 1`, it **inserts** a new `ProductDescription` (short = long = generated); optionally updates `ShortDescription` and (English only) `Product.Name` when `ProgUpdateShortCheck` is set. (`ProductDescriptions.cs:~13400-13430`)
- **BR-DESC-029** — The **Sort** button opens `OrderCategories` for the current catalogue with `catalogueId = -1` and the primary language id (catalogue-ordering path; see 16_Ordering). (`ProductDescriptions.cs:13107-13114`)
- **BR-DESC-030** — The **Alpha** sort button is a **dead stub**: it only shows a confirm dialog and does nothing on "Yes". (`ProductDescriptions.cs:13126-13143`)
- **BR-DESC-031** — Find & Replace is a separate dialog, Product-only, positional-language; details in 12_Translations BR-TRAN-011/020. (`ProductDescriptions.cs:10543-10560`)
- **BR-DESC-032** — Read-only determination (`catalogueIsReadOnly`): a catalogue is editable when its stored `PDMUserCatalogues.ReadOnly == 0` **and** `Global.readOnlyDBConnection` is false; `DescriptionEdit` privilege forces editable; with no catalogue selected, `PDMAdministrator` or user `shacu9` are editable. (`ProductDescriptions.cs:4818-4837`)
- **BR-DESC-033** — Switching catalogue/category/language with unsaved edits (`submitRequired`) is blocked by a modal and the selector reverts — unless the catalogue is read-only. (`ProductDescriptions.cs:7387-7394, 7300-7308`)
- **BR-DESC-034** — Closing the form with `submitRequired` set prompts "modified data outstanding … Are you sure you want to exit?"; **No** cancels the close. (`ProductDescriptions.cs:10419-10430`)
- **BR-DESC-035** — Fabric tabs (FabType/FabColours) support incremental keyboard search of the grid by typed prefix against column 5. (`ProductDescriptions.cs:10497-10535`)
- **BR-DESC-036** — DPS/"Other" description reconciliation dedupes on English text with quote normalisation `LTRIM(REPLACE(ShortDescription, '''', '`'))`. (`Q-DESC-051`, `11173`)
- **BR-DESC-037** — `metaDescriptions` is an inert DTO; it participates in no description persistence. (`metaDescriptions.cs:1-20`)

---

## 7. Hidden Logic

- **New-id spawning (BR-DESC-019/BR-TRAN-018)** silently creates and re-links `DescriptionId`s; the user sees a normal edit. Applies to both `OtherDescription` and the product path (`Q-DESC-022`).
- **`ProductCategoryMask` parsing (BR-DESC-020)** couples option-description edits to a delimited string on `ProductCategory`; the fixed id list (8, 28, 3344, 3346, 6790, 6791) is hardcoded fabric/finish option ids that receive special treatment (mask redirection, no `Name` update).
- **App-text scope auto-selection (BR-DESC-011)** depends on catalogue **name text** containing `"Pricebook"` and on a financial permission combination — non-obvious side effects when renaming catalogues or changing roles.
- **Name denormalisation:** editing English text quietly rewrites the owning entity's `Name`/`Product.Name`/`HandbookName`/`GroupName` (BR-DESC-024/025) — descriptions and names can silently diverge for non-English edits.
- **Inconsistent escaping (BR-DESC-016)** means the persisted text differs (`'` becomes backtick in some fields, `''` in others), so round-tripping a description through different tabs is not lossless.
- **`camelCase` exception for "Size" (BR-DESC-017)** is easy to miss and only applies to English attribute values whose parent attribute is literally named `Size`.
- **Soft vs hard length limits diverge:** 40-char red warning in the UI (BR-DESC-008) vs 50-char hard reject only at pCon export (BR-DESC-009) — the DB itself is not length-guarded here.

---

## 8. UI Behaviour

- **Tab strip** (`TabSelector`) selects the entity type; on change, buttons are reconfigured (`SortButton`, `UpdatePConButton`, `EOSCatalogueLabelCheck`, `button_programmatic` visibility). (`ProductDescriptions.cs:7412-7460`)
- **Context selectors:** catalogue, category, primary language, secondary (compare) language, site, supplier, fabric bands.
- **Grid** (`DataGrid1`) lists entities; row select loads the edit boxes. Filters: All / Blank / Missing radios, "Show All Products", fabric-band/composition filters.
- **Edit panel:** `TextBox1` Short, `TextBox2` Long, `TextBox3` Application (with Default/Catalogue/Pricebook selector); read-only compare boxes for the secondary language; live char counter (`countText`, red > 40).
- **Buttons:** Submit / Submit&Next, Undo, Sort (→ OrderCategories), Alpha (dead), Translated Application Text, Update pCon Desc, "Update Descriptions" (programmatic panel), Translation (Find & Replace).
- **Programmatic panel** (`panel_programmatic_update`): template box, retain-case box, product list, live preview (`text_update_result`), short-desc/abbreviation checkboxes.
- **Guards:** unsaved-edit modal on context switch (BR-DESC-033); exit-confirm on close (BR-DESC-034).
- **Read-only catalogues** disable submit/edit buttons via `catalogueIsReadOnly()` (`4985-4989`), unless `DescriptionEdit` grants override (BR-DESC-032).

---

## 9. Dependencies

- **`ConnectionFactory.CreateNewConnection(autoOpen: true)`** — all SQL.
- **`AuthenticateUser`** — `UserId`, `DefaultLanguageId`, `DefaultDealerNum`, privileges `DescriptionMaintenance` (menu gate), `DescriptionEdit` (read-only override), `ReadOnlyFinancial`, `PDMAdministrator`.
- **`Global`** — `readOnlyDBConnection`, `connectedDB`.
- **`MainMenu`** — launcher (`2743`, gated `3029`).
- **`DescriptionsFindReplace`** — Find & Replace child dialog (see 12_Translations).
- **`OrderCategories`** — opened by `SortButton` (see 16_Ordering).
- **`SIFImport.camelCase(...)`** — English name normalisation.
- **`PriceMaintenance.GetPConTextColumnNamePrefixForWorkspace(...)`**, **`CADMaintenance.pConPath`** — pCon export (see 12_Translations).
- **Tables:** `ProductDescription`, `OtherDescription`, `CatalogueApplicationText`, `CatalogueTranslations`, `Language`, `Product`, `PDMUserCatalogues`, `Catalogue`, `ProductCategory`, `CatalogueProductCategories`, `Attribute`, `AttributeValue`, `[Option]`, `OptionValue`, `ProductRange`, `DPSText`, `Handbook`, `HandbookProducts`, `Item`, and (image/fabric adjuncts) `FabricBands`, `FabricSuppliers`, `Site`.
- **External:** pCon MS Access DB via OLE DB (see 12_Translations).

---

## 10. Risks

- **SQL injection (critical):** every description/name/app-text write is inline-concatenated user text with only ad-hoc `'`-escaping (BR-DESC-016). A description containing a backtick-then-quote or unescaped `%`/`'` can alter the statement. No parameterisation. (e.g. `8629, 8862, 8921, 11173`)
- **Silent `DescriptionId` re-allocation and re-linking** (BR-DESC-019/020) is racy (`MAX+1`) and hard to audit; concurrent editors can collide, and the `ProductCategoryMask` rewrite can leave options pointing at the wrong description.
- **Name/description divergence:** English edits rewrite denormalised `Name` columns while non-English edits do not (BR-DESC-024); the `Product.Name`, category and handbook names can drift out of sync with `*Description` tables.
- **Inconsistent quote escaping** produces non-round-trippable text and different stored values depending on which tab/handler saved it.
- **Length limits mismatch** (40 soft UI vs 50 hard pCon, DB unguarded) — long descriptions save fine in PDM but silently fail to export.
- **`ReadOnly` semantics are literal here** (`ReadOnly == 0` = editable, BR-DESC-032) which conflicts with the inverted `PDMUserCatalogues.ReadOnly` convention noted elsewhere in the codebase — verify per environment before relying on it. Marked as a discrepancy to confirm (`UNKNOWN` which convention the live schema uses).
- **Hardcoded ids** (option ids 8/28/3344/3346/6790/6791; special user `shacu9`; catalogue-name string `"Pricebook"`) embed business config in code (BR-DESC-011/020/032).
- **Broad `try/catch` with `MsgBox(ex.ToString())`** leaks SQL/schema to the user and, in `language2update`, swallows exceptions entirely (12_Translations Risks).
- **Dead/decorative controls:** Alpha sort (BR-DESC-030) and the Find & Replace Match Case / Match whole word checkboxes (12_Translations §8) do nothing — misleading to operators.
