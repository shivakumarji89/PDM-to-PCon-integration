# 12 — Translations (Multi-Language Handling)

**Module prefix:** BR-TRAN
**Primary legacy source:** `PDMMaintenance\ProductDescriptions.cs` (~13003 lines), `PDMMaintenance\DescriptionsFindReplace.cs` (~561 lines), `PDMMaintenance\metaDescriptions.cs` (20 lines), `PDMMaintenance\AuthenticateUser.cs`, `PDMMaintenance\MainMenu.cs`
**Status:** Verified from source unless marked `UNKNOWN`.

> Scope split: this document covers **how PDM stores and chooses a language** — the `Language` table, per-language description rows (`ProductDescription`, `OtherDescription`), the "translated" flag per catalogue (`CatalogueTranslations`), the primary/secondary language comparison workflow, the cross-language Find & Replace tool, propagation to the pCon database, and the (limited) fallback logic. The *description maintenance UI, text-editing rules, and find/replace mechanics* are documented in [13_Descriptions.md](13_Descriptions.md). Where behaviour is shared, this file cross-references rather than duplicates.

---

## 1. Purpose

PDM is a multi-language product catalogue. Every descriptive string (product short/long descriptions, application text, and the "name" of every catalogue entity — attribute, option, range, category, etc.) can exist in more than one language. The system:

- Loads the list of languages from the `Language` table into two dropdowns (a **primary** editing language and a **secondary** comparison/translation-target language).
- Stores product-level text in `ProductDescription` (one row per `DescriptionId` + `LanguageId`) and everything else in `OtherDescription` (one row per `DescriptionId` + `LanguageId`, tagged with a `RelatedTable`).
- Tracks, per catalogue and per language, whether that catalogue has been "translated" (`CatalogueTranslations`).
- Provides a **Find & Replace Translations** helper (`DescriptionsFindReplace`) that reads text in the primary language and writes the translated result into the secondary language.
- Pushes English/French/German/Dutch descriptions out to the external pCon (`tCOMd_Text`) database.

`metaDescriptions.cs` is **not** a translation engine — it is a 3-field data holder (`language`, `propertyValue`, `propertyDescription`) with a single constructor and no persistence logic (`metaDescriptions.cs:1-20`). It is documented here only to record that fact.

---

## 2. Entry Points

| Entry point | Location | Trigger |
|---|---|---|
| `ProductDescriptions` form constructor / load | `ProductDescriptions.cs` (form `.ctor`) | Opened from Main Menu **Product Descriptions** button (`MainMenu.cs:2743`), gated by `DescriptionMaintenance` privilege (`MainMenu.cs:3029`). |
| Language dropdown population | `ProductDescriptions.cs:4734-4757` | Runs during form load; fills `language_selector` (primary) and `language_selector2` (secondary) from the `Language` table. |
| `language_selector_SelectedIndexChanged` | `ProductDescriptions.cs:7383` | Changing the primary editing language. |
| `language_selector2_SelectedIndexChanged` | `ProductDescriptions.cs:10290` | Changing the secondary comparison language → calls `showTranslatedStatus()`. |
| `languageselector_KeyPress` / `languageselector2_KeyPress` | `ProductDescriptions.cs:10487-10495` | Both suppress keyboard input (`e.Handled = true`) so the language cannot be typed, only picked. |
| `showTranslatedStatus()` | `ProductDescriptions.cs:10244` | Refreshes the secondary-language text boxes and the "Catalogue Translated" checkbox. |
| `language2update()` | `ProductDescriptions.cs:10298` | Loads the secondary-language text for the selected grid row. |
| `TranslatedCheck_CheckedChanged` | `ProductDescriptions.cs:10800` | Toggles the `CatalogueTranslations` row for the current catalogue + secondary language. |
| `TranslationButton_Click` | `ProductDescriptions.cs:10543` | Opens the `DescriptionsFindReplace` dialog (Product tab only). |
| `DescriptionsFindReplace.sendData(...)` | `DescriptionsFindReplace.cs:286` | Initialises the Find & Replace dialog with the product id list and the two language ids. |
| `DescriptionsFindReplace.FindNext()` | `DescriptionsFindReplace.cs:~347` | Searches the **primary** language `ShortDescription`. |
| `DescriptionsFindReplace.InsertButton_Click` | `DescriptionsFindReplace.cs:512` | Writes the replaced text into the **secondary** language row. |
| pCon description push | `ProductDescriptions.cs:11554-11660` (`UpdatePConButton`) | Propagates descriptions to the external pCon `tCOMd_Text` database for languages 1/2/5/9. |

---

## 3. Call Hierarchy

```
MainMenu (ProdDescButton, gated by DescriptionMaintenance)
  └─> ProductDescriptions (form)                              [Form]
        ├─ form load ──> "SELECT Language_ID, Language FROM Language"   [Q-TRAN-001]
        │                fills language_selector + language_selector2
        │                default primary = AuthenticateUser.DefaultLanguageId (else index 0)
        │
        ├─ language_selector_SelectedIndexChanged  [Event]      (primary edit language)
        │     └─ updateDescriptions() / updateDataGrid()  → tab SELECTs (see 13_Descriptions)
        │
        ├─ language_selector2_SelectedIndexChanged [Event]      (secondary compare language)
        │     └─ showTranslatedStatus()            [Controller]
        │           ├─ language2update()           [Controller]
        │           │     ├─ ProductDescription fetch (tab 0)          [Q-TRAN-002]
        │           │     └─ OtherDescription fetch (tabs 1-11)        [Q-TRAN-003]
        │           └─ CatalogueTranslations existence check          [Q-TRAN-004]
        │
        ├─ TranslatedCheck_CheckedChanged          [Event]
        │     ├─ INSERT INTO CatalogueTranslations                    [Q-TRAN-005]
        │     └─ DELETE FROM CatalogueTranslations                    [Q-TRAN-006]
        │
        ├─ submitData() / modifyOtherDescription() [Controller]  (write per-language rows)
        │     ├─ SELECT existing lang>1 rows                          [Q-TRAN-007]
        │     ├─ UPDATE OtherDescription (selected language)          [Q-TRAN-008]
        │     ├─ INSERT OtherDescription (selected language)          [Q-TRAN-009]
        │     └─ INSERT OtherDescription (copy base + translations)   [Q-TRAN-010]
        │
        ├─ TranslationButton_Click                 [Event]
        │     └─> DescriptionsFindReplace (dialog)  [Form]
        │           ├─ sendData ──> "SELECT Language_ID, Language FROM Language"  [Q-TRAN-001]
        │           ├─ FindNext() ─> primary-language ShortDescription LIKE       [Q-TRAN-016]
        │           └─ InsertButton_Click ─> secondary-language UPDATE/INSERT     [Q-TRAN-015]
        │
        └─ UpdatePConButton (pCon push)            [Event]
              ├─ per-language English-fallback fetch                  [Q-TRAN-013]
              └─ UPDATE tCOMd_Text (en/fr/de/nl columns)             [Q-TRAN-014]
```

There is no Service/Repository layer: every event handler builds inline, string-concatenated SQL and executes it directly against a `SqlConnection` from `ConnectionFactory.CreateNewConnection(autoOpen: true)`.

---

## 4. SQL Analysis

All SQL below is built with inline string concatenation (`Operators.ConcatenateObject` / `+`) and is therefore **SQL-injection-prone** (see Risks). Language id is taken from `_languageIdList[...]` (primary) or `_languageIdList2[...]` (secondary), which mirror the `Language` table's `Language_ID` values.

### Q-TRAN-001 — Load the language list
`ProductDescriptions.cs:4734` and `DescriptionsFindReplace.cs:293`
```sql
SELECT Language_ID, Language FROM Language
```
**WHY:** Populates both language dropdowns. In `ProductDescriptions` it fills `language_selector`/`_languageIdList` and `language_selector2`/`_languageIdList2` in the same loop (`4737-4743`). In `DescriptionsFindReplace.sendData` it fills `Lang1Combo`, `Lang2Combo` and `langArray` (`296-303`). No `ORDER BY` — display order is whatever the table returns.

### Q-TRAN-002 — Secondary-language product text (Products tab)
`ProductDescriptions.cs:10318` (inside `language2update`)
```sql
SELECT pd.DescriptionId, ShortDescription, LongDescription, ApplicationText
FROM ProductDescription pd
INNER JOIN Product ON pd.DescriptionId = Product.DescriptionId
WHERE Product.ProductId = <num> AND pd.LanguageId = <language2>
```
**WHY:** Loads the *secondary* comparison language (`language2 = _languageIdList2[language_selector2.SelectedIndex]`) into the right-hand text boxes (`TextBox6/5/4`) so the translator can compare against the primary language. If no row exists, all three boxes are blanked (`10353-10358`) — **no fallback** to English here.

### Q-TRAN-003 — Secondary-language "other" text (tabs 1-11)
`ProductDescriptions.cs:10363` onward (switch on `TabSelector.SelectedIndex`)
```sql
SELECT od.DescriptionId, ShortDescription FROM OtherDescription od
  <INNER JOIN entity table on od.DescriptionId>  -- per tab
WHERE <entity>.Id = <num> [AND catalogue/category/handbook filters]
AND od.LanguageId = <language2>
```
Representative joins by tab index (`10363-10430`): 1=`Attribute`, 2=`AttributeValue`, 3=`[Option]`, 4/8/9=`OptionValue`, 5=`ProductRange`, 6=`CatalogueProductCategories` (+`CatalogueId`), 7=`Catalogue`, 10=`DPSText`, 11=`HandbookProducts` (+`ProductCategoryId`+`HandbookId`).
**WHY:** All non-product entities keep their translations in `OtherDescription`; this loads the secondary language for the selected row. Tab 11 (Handbook name) short-circuits and blanks the boxes before the query (`10307-10313`).

### Q-TRAN-004 — Is this catalogue+language "translated"?
`ProductDescriptions.cs:10266` (inside `showTranslatedStatus`)
```sql
SELECT CatalogueId FROM CatalogueTranslations
WHERE CatalogueId = <catalogueId> AND LanguageId = <num>
```
**WHY:** Existence of a row means the checkbox "Catalogue Translated" is ticked for the selected catalogue + secondary language. If the secondary language is `1` (English), the checkbox is forced checked and disabled (`10249-10253`) — English is treated as always translated.

### Q-TRAN-005 — Mark catalogue as translated
`ProductDescriptions.cs:10817`
```sql
INSERT INTO CatalogueTranslations (CatalogueId, LanguageId) VALUES (<catalogueId>, <num>)
```

### Q-TRAN-006 — Un-mark catalogue as translated
`ProductDescriptions.cs:10823`
```sql
DELETE FROM CatalogueTranslations WHERE CatalogueId = <catalogueId> AND LanguageId =  <num>
```
**WHY (005/006):** `TranslatedCheck_CheckedChanged` toggles the flag row. Guarded so it only fires when `num > 1` (never for English) and not while the UI is refreshing (`updatingtranslatedstatus`) — see BR-TRAN-014. Note the double space before `<num>` in the DELETE is a harmless literal artefact.

### Q-TRAN-007 — Read existing non-English rows for a description
`ProductDescriptions.cs:8609` (inside `modifyOtherDescription`)
```sql
SELECT LanguageId, ShortDescription FROM OtherDescription
WHERE DescriptionId = <descId> AND LanguageId > 1
```
**WHY:** Before creating a brand-new `DescriptionId`, the existing non-English translations are captured so they can be copied onto the new id (see Q-TRAN-010 / BR-TRAN-018).

### Q-TRAN-008 — Update the selected-language OtherDescription
`ProductDescriptions.cs:8629`
```sql
UPDATE OtherDescription SET ShortDescription = N'<description>'
WHERE DescriptionId = <descId> AND LanguageId = <primaryLanguageId>
```

### Q-TRAN-009 — Insert the selected-language OtherDescription
`ProductDescriptions.cs:8635`
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable)
VALUES (<descId>, <primaryLanguageId>, N'<description>', '<getTableName(tabname)>')
```
**WHY (008/009):** When editing an entity in a non-English language (or `descId > 1`), the code first tries `UPDATE`; if `rowcount == 0` it falls back to `INSERT` (`8624-8639`). This is a manual UPSERT.

### Q-TRAN-010 — Copy base English + existing translations to a new DescriptionId
`ProductDescriptions.cs:8691`, `8704`, `8710`
```sql
-- base English row for the new id
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable)
VALUES (<num2+1>, 1, N'<description>', '<relatedTable>')

-- selected-language row (translation of the new text)
INSERT INTO OtherDescription  (DescriptionId, LanguageId, ShortDescription, RelatedTable)
VALUES (<num2+1>, <langId>, N'<description>', '<relatedTable>')

-- carry-over of every OTHER existing non-English translation unchanged
INSERT INTO OtherDescription   (DescriptionId, LanguageId, ShortDescription, RelatedTable)
VALUES (<num2+1>, <langId>, N'<original translation>', '<relatedTable>')
```
**WHY:** When a shared/default description is edited it may spawn a new `DescriptionId` (`num2 + 1` where `num2` is `SELECT TOP 1 DescriptionId FROM OtherDescription ORDER BY DescriptionId DESC`). All previously-existing translations for the old id are re-attached to the new id so no language is lost (BR-TRAN-018). The multiple spaces after `OtherDescription` distinguish the three literals but are otherwise cosmetic.

### Q-TRAN-011 — Language-id → language-name map (in code, NOT SQL)
`ProductDescriptions.cs:7232-7270` (`getRSDescription`)
```
1 -> "englishuk"   6 -> "spanish"
2 -> "french"      7 -> "chinese"
3 -> "italian"     8 -> "portuguese"
4 -> "japanese"    9 -> "dutch"
5 -> "german"      10 -> "english"
```
**WHY:** Used to parse a language-specific string out of a developer `*.rs` file. This is the only place in these modules that hardcodes the `LanguageId` → human-name mapping (the `Language` table itself is data-driven, so display names come from the DB — see BR-TRAN-002). Documented as evidence of the canonical id assignments.

### Q-TRAN-012 — Attribute description with English fallback (programmatic descriptions)
`ProductDescriptions.cs:~13268` (`generateProgrammaticDescription`)
```sql
SELECT atval.AttributeId,
       CASE WHEN od.ShortDescription IS NOT NULL THEN od.ShortDescription
            ELSE od1.ShortDescription END AS ShortDescription
FROM ProductAttributeValues pav
INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId
INNER JOIN OtherDescription od1 ON atval.DescriptionId = od1.DescriptionId AND od1.LanguageId = 1
LEFT OUTER JOIN OtherDescription od ON atval.DescriptionId = od.DescriptionId AND od.LanguageId = <primaryLanguageId>
WHERE pav.ProductId = <productId>
```
**WHY:** This is a **real language fallback**: use the selected language's attribute-value description if present, otherwise fall back to English (`LanguageId = 1`). Confirms fallback-to-English exists for programmatically generated descriptions.

### Q-TRAN-013 — Product description with English fallback (pCon push)
`ProductDescriptions.cs:11576`
```sql
SELECT
  CASE WHEN pd2.ShortDescription IS NULL OR pd2.ShortDescription = '' THEN pd1.ShortDescription
       ELSE pd2.ShortDescription END AS ShortDescription,
  CASE WHEN pd2.LongDescription IS NULL OR pd2.LongDescription = '' THEN pd1.LongDescription
       ELSE pd2.LongDescription END AS LongDescription
FROM Product
INNER JOIN ProductDescription pd1 ON Product.DescriptionId = pd1.DescriptionId AND pd1.LanguageId = 1
LEFT OUTER JOIN ProductDescription pd2 ON Product.DescriptionId = pd2.DescriptionId AND pd2.LanguageId = <num8>
WHERE Product.Product = '<productCode>'
```
**WHY:** A second **real fallback**: when pushing a translation to pCon, if the target language row is missing/blank, the English (`LanguageId = 1`) text is used instead.

### Q-TRAN-014 — Write description into pCon per-language text columns
`ProductDescriptions.cs:11628`, `11631`, `11634`, `11637` (short text) and `11642`..`11650` (long text)
```sql
UPDATE tCOMd_Text SET <prefix>_en = '<text>' WHERE com_TextID = <id>   -- lang 1
UPDATE tCOMd_Text SET <prefix>fr  = '<text>' WHERE com_TextID = <id>   -- lang 2
UPDATE tCOMd_Text SET <prefix>de  = '<text>' WHERE com_TextID = <id>   -- lang 5
UPDATE tCOMd_Text SET <prefix>nl  = '<text>' WHERE com_TextID = <id>   -- lang 9
```
(`<prefix> = PriceMaintenance.GetPConTextColumnNamePrefixForWorkspace(workspace)`; the `com_TextID`s come from `tCOMd_Article` — `Q-TRAN-013a`.)
**WHY:** pCon stores each language in a dedicated column (`_en`/`fr`/`de`/`nl`), not per-row. Only PDM languages **1, 2, 5, 9** are propagated (BR-TRAN-021). Note the short-text English column literal is `<prefix>_en` while the long-text English literal is `<prefix>en` (`11642`) — an asymmetry preserved from source.

`Q-TRAN-013a` — locate the pCon text ids (OLE DB, MS Access): `SELECT com_ShortTextID, com_LongTextID FROM tCOMd_Article WHERE com_ArticleCode LIKE '<code>%'` (`ProductDescriptions.cs:11596`).

### Q-TRAN-015 — Find & Replace: write into the target (secondary) language
`DescriptionsFindReplace.cs:517` (check) and `524` / `531` (write)
```sql
-- existence check in target language
SELECT ShortDescription FROM ProductDescription
WHERE (DescriptionId = <currentDescId>) AND (LanguageId = <Lang2Combo.SelectedIndex + 1>)

-- if it exists: overwrite
UPDATE ProductDescription SET ShortDescription = '<newText>'
WHERE (DescriptionId = <currentDescId>) AND (LanguageId = <Lang2Combo.SelectedIndex + 1>)

-- else: create
INSERT INTO ProductDescription (DescriptionId, LanguageId, ShortDescription)
VALUES (<currentDescId>, <Lang2Combo.SelectedIndex + 1>, '<newText>')
```
**WHY:** The replaced text is committed to the **secondary** language row (manual UPSERT). The target `LanguageId` is derived positionally as `SelectedIndex + 1` (BR-TRAN-011), **not** from `langArray`.

### Q-TRAN-016 — Find & Replace: search the source (primary) language
`DescriptionsFindReplace.cs:~347` (`FindNext`, `type == "Product"`)
```sql
SELECT ProductDescription.DescriptionId, ProductDescription.ShortDescription, Product.Product
FROM Product
INNER JOIN ProductDescription ON Product.DescriptionId = ProductDescription.DescriptionId
WHERE (Product.ProductId = <productId>)
  AND (ProductDescription.LanguageId = <Lang1Combo.SelectedIndex + 1>)
  AND (ProductDescription.ShortDescription LIKE '%<findText>%')
```
**WHY:** Iterates the passed-in product id list, finding the next product whose **primary**-language `ShortDescription` contains the search text. The `type == "Other"` branch is an **empty stub** (`DescriptionsFindReplace.cs:~333-336`) — Find & Replace only works for Products (BR-TRAN-020).

---

## 5. Data Model

### `Language`
| Column | Notes |
|---|---|
| `Language_ID` | Integer id; matches `LanguageId` used everywhere else. Value `1` = the default/English base. |
| `Language` | Display name shown in the dropdowns. |

Canonical id assignments observed in `getRSDescription` (Q-TRAN-011): 1=English (UK), 2=French, 3=Italian, 4=Japanese, 5=German, 6=Spanish, 7=Chinese, 8=Portuguese, 9=Dutch, 10=English (generic). The actual dropdown text comes from the `Language.Language` column, so these names are the *code's* assumption of the ids, not necessarily the DB labels.

### `ProductDescription` (product text, one row per language)
| Column | Notes |
|---|---|
| `DescriptionId` | Links to `Product.DescriptionId`. |
| `LanguageId` | FK → `Language.Language_ID`. |
| `ShortDescription`, `LongDescription`, `ApplicationText` | Per-language text; may be `NULL`. |
| `MarketingDescription` | "Lifestyle" text; **always read from `LanguageId = 1`** regardless of selected language (`ProductDescriptions.cs:7808`, inline comment in source). |

### `OtherDescription` (all non-product entities, one row per language)
| Column | Notes |
|---|---|
| `DescriptionId` | Referenced by the owning entity's `DescriptionId` column (Attribute, AttributeValue, [Option], OptionValue, ProductRange, Catalogue, CatalogueProductCategories, DPSText, HandbookProducts, …). |
| `LanguageId` | FK → `Language.Language_ID`. |
| `ShortDescription` | Per-language text. |
| `RelatedTable` | String tag naming the owning entity type. Values written by this module include the literal entity table names plus the special tags `'[Option]'`, `'OptionCategoryMask'`, `'SPComponent'` (`ProductDescriptions.cs:5095, 8683, 8688`). |

### `CatalogueTranslations` (translated flag)
| Column | Notes |
|---|---|
| `CatalogueId` | FK → `Catalogue`. |
| `LanguageId` | FK → `Language`. |
| — | **Row existence == "this catalogue is translated into this language".** No status column; presence/absence is the flag. |

### `CatalogueApplicationText` (per-catalogue, per-language application text)
| Column | Notes |
|---|---|
| `CatalogueId` | Positive = normal catalogue instance; **`-1 * CatalogueId` = "Pricebook" variant** (`ProductDescriptions.cs:8843-8851`, `8895`). |
| `ProductId`, `LanguageId`, `ApplicationText` | Per product + language override text. |

Detailed handling of application text belongs to [13_Descriptions.md](13_Descriptions.md); it is listed here because it is language-keyed.

### External: pCon `tCOMd_Text` / `tCOMd_Article` (MS Access / OLE DB)
Language stored as columns `<prefix>_en` / `<prefix>fr` / `<prefix>de` / `<prefix>nl` (Q-TRAN-014). Reached via `Microsoft.Jet.OLEDB.4.0` against `pcr_data_com_ocd.mdb` (`ProductDescriptions.cs:11541`).

---

## 6. Business Rules

> IDs are unique within this module (BR-TRAN-###). "Verified" = directly readable in source at the cited line.

- **BR-TRAN-001** — Two independent language selections exist: a **primary** editing language (`language_selector` / `_languageIdList`) and a **secondary** comparison/translation-target language (`language_selector2` / `_languageIdList2`). Both are loaded from the same `Language` query in one loop. (`ProductDescriptions.cs:4737-4743`)
- **BR-TRAN-002** — Language display names are **data-driven** from `Language.Language`; the dropdown order is the natural row order of `SELECT Language_ID, Language FROM Language` (no `ORDER BY`). (`Q-TRAN-001`)
- **BR-TRAN-003** — The default primary language is `AuthenticateUser.DefaultLanguageId` when that id is present in the list, otherwise the first item (index 0). (`ProductDescriptions.cs:4745-4752`)
- **BR-TRAN-004** — `AuthenticateUser.DefaultLanguageId` defaults to `1` and is overwritten from `PDMUserPrivileges.DefaultLanguageId` at login. (`AuthenticateUser.cs:19, 88`)
- **BR-TRAN-005** — The secondary language defaults to index 0 on load. (`ProductDescriptions.cs:4753-4757`)
- **BR-TRAN-006** — Language cannot be typed into either combo; `KeyPress` is swallowed (`e.Handled = true`) forcing selection only. (`ProductDescriptions.cs:10487-10495`)
- **BR-TRAN-007** — Product text lives in `ProductDescription`; **all other entity text lives in `OtherDescription`**, keyed by `DescriptionId` + `LanguageId`. (Q-TRAN-002/003, `getTableName` mapping `ProductDescriptions.cs:8514-8562`)
- **BR-TRAN-008** — `LanguageId = 1` is the **base/English language**: it is the fallback source (BR-TRAN-016/017), the copy source for new ids (Q-TRAN-010), and the always-translated language (BR-TRAN-013).
- **BR-TRAN-009** — Marketing/"Lifestyle" text is **always** read from `LanguageId = 1`, never the selected language (source carries an explicit comment). (`ProductDescriptions.cs:7808`)
- **BR-TRAN-010** — Changing the primary language while there are unsaved edits is blocked: the user is told to submit or undo, and the selector is reverted to `_prevLanguageIndex` — **unless** the catalogue is read-only. (`ProductDescriptions.cs:7387-7394`)
- **BR-TRAN-011** — In `DescriptionsFindReplace`, the target/source `LanguageId` is computed **positionally** as `ComboBox.SelectedIndex + 1`, not from `langArray`. This assumes `Language_ID` values are contiguous starting at 1. (`DescriptionsFindReplace.cs:347, 517, 524, 531`)
- **BR-TRAN-012** — A catalogue's translated state per language is represented purely by **row presence** in `CatalogueTranslations` (no status flag). (Q-TRAN-004/005/006)
- **BR-TRAN-013** — When the secondary language is English (`LanguageId = 1`), "Catalogue Translated" is forced **checked and disabled** — English needs no translation flag. (`ProductDescriptions.cs:10249-10253`)
- **BR-TRAN-014** — The translated flag toggle (`TranslatedCheck_CheckedChanged`) only writes when `LanguageId > 1` **and** the UI is not mid-refresh (`updatingtranslatedstatus == false`), preventing spurious inserts during load. (`ProductDescriptions.cs:10802-10805`)
- **BR-TRAN-015** — The "Catalogue Translated" checkbox is only editable when the catalogue is not read-only; otherwise it is display-only. (`ProductDescriptions.cs:10256-10259`)
- **BR-TRAN-016** — **Fallback (programmatic descriptions):** attribute-value text uses the selected language if present, else English (`CASE WHEN od.ShortDescription IS NOT NULL … ELSE od1(LanguageId=1)`). (`Q-TRAN-012`)
- **BR-TRAN-017** — **Fallback (pCon push):** product short/long text uses the target language if non-null/non-empty, else English (`CASE WHEN pd2 … IS NULL OR = '' THEN pd1(LanguageId=1)`). (`Q-TRAN-013`)
- **BR-TRAN-018** — When editing spawns a **new** `DescriptionId`, all previously existing non-English translations for the old id are re-inserted against the new id so no language is lost; the just-edited language is written with the new text and the others are carried over verbatim. (`Q-TRAN-007`, `Q-TRAN-010`, `ProductDescriptions.cs:8688-8715`)
- **BR-TRAN-019** — Writes to per-language rows are **manual UPSERTs**: try `UPDATE`, and if `rowcount == 0` `INSERT`. Applies to `OtherDescription` (`8624-8639`), `ProductDescription` find/replace (`DescriptionsFindReplace.cs:517-534`), and product submit (`13_Descriptions`).
- **BR-TRAN-020** — The Find & Replace tool is **Product-only**: `sendData` is always called with `type = "Product"` (`ProductDescriptions.cs:10558`), and the `type == "Other"` branch in `FindNext` is an empty stub — a dead/unimplemented path. (`DescriptionsFindReplace.cs` `FindNext`)
- **BR-TRAN-021** — pCon receives only **four** languages: PDM `LanguageId` 1→`_en`, 2→`fr`, 5→`de`, 9→`nl`. Any other id triggers `"unexpected pCon languageId … expecting 1, 2, 5 or 9"`. English (1) is always pushed; French/German/Dutch are added only if the user answers **Yes** to "Update all languages in pCon database?". (`ProductDescriptions.cs:11550-11560, 11628-11660`)
- **BR-TRAN-022** — When the Products tab is on tab index 9, the pCon "all languages?" prompt is **skipped** and only English is pushed (`if (TabSelector.SelectedIndex != 9)` guard). (`ProductDescriptions.cs:11552`)
- **BR-TRAN-023** — pCon short descriptions longer than 50 characters are **rejected per product** with a warning and skipped. (`ProductDescriptions.cs:11618-11621`)
- **BR-TRAN-024** — For product codes starting with `"AER"`, the code trims the last 2 characters of the code and truncates the short/long text at `" / "` / `" >"` before pushing to pCon (special-case). (`ProductDescriptions.cs:11586-11592`)
- **BR-TRAN-025** — pCon long descriptions have `>` replaced with a CR/LF before writing. (`ProductDescriptions.cs:~11651`)
- **BR-TRAN-026** — English (`LanguageId = 1`) rows in `OtherDescription` are the source that is copied when a new id is created; **non-English rows equal to the just-edited language are replaced with the new text**, all others carried verbatim (guarded by comparing `text4`'s language id to the selected language). (`ProductDescriptions.cs:8700-8713`)
- **BR-TRAN-027** — `CatalogueApplicationText` is language-keyed and supports a **negative-catalogue-id "Pricebook" variant** (`-1 * CatalogueId`) as a separate language override set. (`ProductDescriptions.cs:8843-8851, 8895`)
- **BR-TRAN-028** — Permission `DescriptionMaintenance` gates whether the Product Descriptions screen appears on the Main Menu at all. (`MainMenu.cs:3029-3031`)
- **BR-TRAN-029** — Permission `DescriptionEdit` **overrides catalogue read-only status**: if set, `catalogueIsReadOnly()` returns `false` (translator can edit even locked catalogues), unless the caller passes `ignoreDescriptionEditPermission: true`. (`ProductDescriptions.cs:4827-4830`)
- **BR-TRAN-030** — `metaDescriptions` is an inert 3-field data holder (`language`, `propertyValue`, `propertyDescription`); it performs **no** language selection, persistence, or fallback. (`metaDescriptions.cs:1-20`)

---

## 7. Hidden Logic

- **English-fallback is real but partial.** It exists only in `generateProgrammaticDescription` (Q-TRAN-012) and the pCon push (Q-TRAN-013), plus the in-memory `getRSDescription` fallback (`languageId == 1` empty → retry with `"english"`, `ProductDescriptions.cs:7275-7284`). It does **NOT** exist in `language2update`/`showTranslatedStatus`: missing translations simply show blank text boxes (BR-TRAN-016/017 vs Q-TRAN-002/003). Any assumption that the editor always shows English when a translation is missing is **false**.
- **Positional language ids.** `DescriptionsFindReplace` and the primary `Q-TRAN-016`/`Q-TRAN-015` queries use `SelectedIndex + 1` as the `LanguageId`. This silently assumes `Language_ID` is a dense sequence starting at 1 and matching combo order; a gap or re-ordering in the `Language` table would write to the wrong language. `langArray` (holding the true ids) is loaded but **never used** for the read/write id in `FindNext`/`InsertButton_Click`.
- **New-id spawning is invisible to the user.** Editing what looks like a single description can create a fresh `DescriptionId` (`SELECT TOP 1 … ORDER BY DescriptionId DESC` + 1) and rewire the owning entity, carrying translations across (Q-TRAN-010). This is racy under concurrency (see Risks).
- **Special `RelatedTable` remaps.** Options can be re-tagged `'OptionCategoryMask'` and products `'SPComponent'` when writing `OtherDescription`, and a `ProductCategoryMask` string (`descids:8=-1,28=-1,…`) is parsed/rewritten to redirect which `DescriptionId` an option points to. (`ProductDescriptions.cs:8665-8760`)
- **English-always-translated.** Secondary language 1 forces the translated checkbox on and disabled (BR-TRAN-013), so English catalogues never appear "untranslated".
- **pCon column-name asymmetry.** Short-text English column is built as `<prefix>_en`; long-text English column as `<prefix>en` (missing underscore). Preserved from source; may be intentional pCon schema or a latent bug. Marked here, not "corrected".

---

## 8. UI Behaviour

- **Two dropdowns:** `language_selector` (edit language) and `language_selector2` (compare/target language). Selecting the compare language refreshes the right-hand text boxes (`TextBox6/5/4`) and the "Catalogue Translated" check via `showTranslatedStatus`.
- **Keyboard disabled** on both language combos (BR-TRAN-006).
- **Unsaved-edit guard:** switching the primary language with pending edits raises a modal "Please submit … or Undo" and reverts the selection (BR-TRAN-010).
- **"Catalogue Translated" checkbox** (`TranslatedCheck`, caption "Catalogue Translated"): reflects/edits `CatalogueTranslations`; forced-on/disabled for English; disabled when catalogue is read-only.
- **Find & Replace Translations dialog** (`DescriptionsFindReplace`, window title "Find & Replace Translations"): `Lang1Combo` (from) / `Lang2Combo` (to), "Find what"/"Replace with" text boxes, "Match Case"/"Match whole word" checkboxes (present but see BR note), "Find Next", "Replace && Next". The English source box (`EngDescTextBox`) is read-only. On exhausting the list it shows `"End of List"`. (`DescriptionsFindReplace.cs:264-421`)
  - **Match Case / Match whole word checkboxes are UI-only decoration:** `FindNext` searches with a case-insensitive `LIKE '%…%'` and `IndexOf(...ToLower())` and never reads `CheckBox1`/`CheckBox2`. Marked `UNKNOWN` whether they were ever wired — no code path consumes them.
- **pCon push** prompts "Update all languages in pCon database? Yes = English, French, German and Dutch / No = English ONLY" before propagating (BR-TRAN-021).

---

## 9. Dependencies

- **`ConnectionFactory.CreateNewConnection(autoOpen: true)`** — every query; foundation data-access (see 00_System_Architecture).
- **`AuthenticateUser`** — `DefaultLanguageId`, `UserId`, `DefaultDealerNum`, and privileges `DescriptionMaintenance` / `DescriptionEdit` / `ReadOnlyFinancial`. (`AuthenticateUser.cs`)
- **`Global`** — `connectedDB`, `readOnlyDBConnection` (forces read-only). (`Global.cs`)
- **`MainMenu`** — launches the form, gated by `DescriptionMaintenance`. (`MainMenu.cs:2743, 3029`)
- **`DescriptionsFindReplace`** — child dialog launched by `TranslationButton_Click`. (`ProductDescriptions.cs:10557-10559`)
- **`PriceMaintenance.GetPConTextColumnNamePrefixForWorkspace(...)`** — pCon column prefix per workspace. (`ProductDescriptions.cs:11628`)
- **`CADMaintenance.pConPath`** — path to the pCon `.mdb`. (`ProductDescriptions.cs:11541`)
- **`SIFImport.camelCase(...)`** — text normalisation for English attribute/option names (shared with 13_Descriptions). (`ProductDescriptions.cs:8595`)
- **External DB:** SQL Server (`PDM*`) plus MS Access (`pcr_data_com_ocd.mdb`) via `Microsoft.Jet.OLEDB.4.0`.
- **Table `Language`, `ProductDescription`, `OtherDescription`, `CatalogueTranslations`, `CatalogueApplicationText`, `Product`, and per-entity tables** (Attribute/AttributeValue/[Option]/OptionValue/ProductRange/Catalogue/CatalogueProductCategories/DPSText/HandbookProducts).

---

## 10. Risks

- **SQL injection (critical):** every query is inline string concatenation. Description text is user-entered and only partially escaped (`'` → backtick or `''`), so a crafted description or product code can break out of the string (`ProductDescriptions.cs:8629, 8635, 11576, DescriptionsFindReplace.cs:524`). No parameterised commands anywhere in these modules.
- **Positional language ids (BR-TRAN-011):** `SelectedIndex + 1` assumes contiguous `Language_ID` starting at 1. A new or deleted language, or a non-1-based `Language_ID`, would silently write translations to the wrong language. `langArray` holds the correct ids but is unused for read/write.
- **Race in new-id allocation:** `SELECT TOP 1 DescriptionId … ORDER BY DescriptionId DESC` + 1 (Q-TRAN-010, and the product path in 13_Descriptions) is not atomic; two concurrent editors can collide on the same new `DescriptionId`.
- **Silent blanking, no fallback in the editor:** missing translations show empty boxes (Q-TRAN-002/003). A translator could overwrite/delete assuming "no text" when the English base actually exists — data-loss risk.
- **pCon language coverage is hardcoded:** only ids 1/2/5/9 propagate (BR-TRAN-021); any additional PDM language will never reach pCon and only logs a message.
- **pCon English column asymmetry** (`_en` vs `en`, Hidden Logic) may write English long text to the wrong column depending on the real pCon schema — `UNKNOWN` whether this is intentional.
- **Broad exception swallowing:** most handlers wrap the body in `try/catch` that either `MsgBox`es the raw exception (leaking SQL/schema) or silently clears it (`language2update` swallows into an unused local), masking failures. (`ProductDescriptions.cs:10473-10479`)
- **Match Case / Match whole word do nothing** (UI-only) — users may believe a whole-word or case-sensitive replace occurred when it did not.
- **Cross-module coupling to `ProductCategoryMask` string parsing** (`descids:…`) makes translation edits for Options fragile and hard to reason about.
