# 03 — Catalogues

**Module prefix:** BR-CAT
**Primary legacy source:**
- `PDMMaintenance/CatalogueMaintenance.cs` (~889 lines — decompiled UI shell)
- `PDMMaintenance/MainMenu.cs` (`CatMaintButton_Click`, menu gating)
- `PDMMaintenance/ProductDescriptions.cs` (`initialiseCatalogues`, catalogue flags, sort entry points)
- `PDMMaintenance/CADMaintenance.cs` (user-catalogue load query)
- `PDMMaintenance/OrderCategories.cs` (catalogue display-order editor — see also `16_Ordering.md`)
- `PDMMaintenance/AuthenticateUser.cs` (`CatalogueMaintenance` privilege flag, `DefaultCatalogueId`)

**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

Catalogues are the top-level publishing containers in PDM. A catalogue groups product categories, items, option values and attribute values that are published together (e.g. per brand / market). This module covers:

- How the user reaches "Catalogue Maintenance".
- How the list of catalogues a user may work with is loaded and filtered (active vs obsolete, per-user permission).
- Catalogue-level metadata: `Name`, `DisplayOrder`, `CatalogueType`, `Status`, `CatalogueFlags`, `DescriptionId`, `PrimarySiteId`, `ImageFile`.
- Catalogue display ordering (delegated to the shared `OrderCategories` form — documented in `16_Ordering.md`).

> **Critical structural finding:** The WinForms `CatalogueMaintenance` form (`CatalogueMaintenance.cs`) is a **dead / orphaned UI shell**. It is never instantiated anywhere in the solution (`grep "new CatalogueMaintenance"` → 0 hits) and contains **no event handlers and no SQL** — only auto-generated designer code (`InitializeComponent`) plus an empty constructor. The button labelled *"Catalogue Maintenance"* on the main menu launches an **external executable, `DPS.exe`**, not this form (see BR-CAT-002). The form is retained here because its designer defines the *intended* catalogue-maintenance UI vocabulary (status values, remove-catalogue, product configuration display), which is useful migration signal.

---

## 2. Entry Points

| Entry point | Location | Trigger |
|---|---|---|
| **"Catalogue Maintenance" menu button** (`CatMaintButton`) | `MainMenu.cs` line ~2696 `CatMaintButton_Click` | User clicks the main-menu button. Visible only if `AuthenticateUser.CatalogueMaintenance == true` (MainMenu.cs ~3025). Launches external `DPS.exe`, **not** the `CatalogueMaintenance` form. |
| **`CatalogueMaintenance` form** | `CatalogueMaintenance.cs` | **No caller** — dead shell. Constructor (line ~455) only calls `InitializeComponent()`. |
| **Catalogue selector combo** (`catalogue_selector`) | `ProductDescriptions.cs` `initialiseCatalogues` (line ~4580) | Populated on form load / on `ShowOBSCatalogueCheck` change. Drives all downstream product/description work. |
| **"Sort" button** (`SortButton`) | `ProductDescriptions.cs` `SortButton_Click` (line ~13106) | Opens `OrderCategories` with `catalogueId = -1` → catalogue-level display ordering. See `16_Ordering.md`. |
| **"Alpha" button** (`AlphaButton`) | `ProductDescriptions.cs` `AlphaButton_Click` (line ~13124) | Prompts "sort all catalogues alphabetically" — but the confirmed branch is **empty** (dead feature, BR-CAT-014). |
| **EOS catalogue label checkbox** (`EOSCatalogueLabelCheck`) | `ProductDescriptions.cs` `EOSCatalogueLabelCheck_Changed` (line ~13159) | Toggles the `{NoLabel}` marker inside `Catalogue.CatalogueFlags`. |
| **Context menu (designer only)** | `CatalogueMaintenance.cs` `InitializeComponent` (~line 730+) | Defines intended actions: *Collapse All*, *Catalogue → Remove*, *Set Status → Unreleased (URL) / Active / Obsolete (OBS) / On Hold*. **No handlers wired** — intent only. |

---

## 3. Call Hierarchy

```
MainMenu (Form)
 └─ CatMaintButton_Click                       [MainMenu.cs ~2696]
      └─ Process.Start("DPS.exe",
             "<isReadOnly> maintenanceCAT <connectedDB> <connectedServer>")   ← external app, out of scope

ProductDescriptions (Form)                     [the de-facto catalogue-consuming UI]
 └─ initialiseGui / initialiseCatalogues       [ProductDescriptions.cs ~4580]
      └─ ConnectionFactory.CreateNewConnection(autoOpen:true)
           └─ SqlCommand (Q-CAT-001) → PDMUserCatalogues ⋈ Catalogue
                └─ populate catalogue_selector + _catalogueIdList + _readOnlyCatalogues
                     └─ default-select AuthenticateUser.DefaultCatalogueId
 └─ EOSCatalogueLabelCheck_Changed             [ProductDescriptions.cs ~13159]
      └─ SqlCommand (Q-CAT-004) read CatalogueFlags
      └─ SqlCommand (Q-CAT-005) write CatalogueFlags (toggle {NoLabel})
 └─ SortButton_Click → new OrderCategories(catalogueId=-1)   → see 16_Ordering.md
 └─ AlphaButton_Click → MsgBox → (empty)       [dead]

CADMaintenance (Form)
 └─ (catalogue combo load)                     [CADMaintenance.cs ~8692]
      └─ SqlCommand (Q-CAT-006) → PDMUserCatalogues ⋈ Catalogue (Status=1, incl. CatalogueType)

CatalogueMaintenance (Form)   ← DEAD: constructor → InitializeComponent only, no SQL, no events
```

There is **no Controller/Service/Repository layer**. Every query is inline ADO.NET `SqlCommand` with string-concatenated SQL built directly inside form event handlers (injection-prone; consistent with the foundation facts).

---

## 4. SQL Analysis

All SQL is inline, string-concatenated, executed via `SqlCommand` on a connection from `ConnectionFactory.CreateNewConnection(autoOpen:true)`.

### Q-CAT-001 — Load user's catalogues (SELECT)
**Source:** `ProductDescriptions.cs` `initialiseCatalogues`, line ~4587–4591
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly
FROM PDMUserCatalogues puc
INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId
WHERE puc.UserId = <AuthenticateUser.UserId>
  AND Catalogue.Status = 1        -- (or "= 2" when ShowOBSCatalogueCheck.Checked)
ORDER BY Catalogue.Name
```
**WHY:** Populates the catalogue dropdown with only the catalogues the current user is permitted to see (`PDMUserCatalogues`), applying an active/obsolete filter and carrying the per-catalogue `ReadOnly` flag for downstream write-gating.

### Q-CAT-002 — Load catalogues for ordering (SELECT)
**Source:** `OrderCategories.cs` `OrderCategories_Load` (`catalogueId == -1` branch), line ~117
```sql
SELECT CatalogueId, DisplayOrder,
       CASE WHEN od.ShortDescription IS NULL THEN Catalogue.Name
            ELSE od.ShortDescription END AS ShortDescription
FROM Catalogue
LEFT OUTER JOIN OtherDescription od
     ON Catalogue.DescriptionId = od.DescriptionId
    AND od.LanguageId = <languageId>
ORDER BY DisplayOrder
```
**WHY:** Builds the editable list of all catalogues with their current `DisplayOrder` so the user can renumber them. Localized name via `OtherDescription`, falling back to `Catalogue.Name`. (Full analysis in `16_Ordering.md` / Q-ORD-002.)

### Q-CAT-003 — Persist catalogue display order (UPDATE)
**Source:** `OrderCategories.cs` `SubmitButton_Click` (`catalogueId == -1` branch), line ~193
```sql
UPDATE Catalogue SET DisplayOrder = <textBox.Text> WHERE CatalogueId = <textBox.Tag>
```
**WHY:** Saves the user-entered ordinal for each catalogue. (See `16_Ordering.md` / Q-ORD-003.)

### Q-CAT-004 — Read catalogue flags (SELECT)
**Source:** `ProductDescriptions.cs` `EOSCatalogueLabelCheck_Changed`, line ~13169
```sql
SELECT CatalogueFlags FROM Catalogue WHERE CatalogueId = <selected CatalogueId>
```
**WHY:** Reads the current free-text `CatalogueFlags` string so the `{NoLabel}` marker can be toggled without losing other flags.

### Q-CAT-005 — Write catalogue flags (UPDATE)
**Source:** `ProductDescriptions.cs` `EOSCatalogueLabelCheck_Changed`, line ~13182
```sql
UPDATE Catalogue SET CatalogueFlags = '<text>' WHERE CatalogueId = <selected CatalogueId>
```
where `<text>` = existing flags with `{NoLabel}` stripped, then re-prefixed with `{NoLabel}` only if the checkbox is **unchecked**.
**WHY:** Persists the "show/suppress EOS catalogue label" preference as an embedded token inside `CatalogueFlags`.

### Q-CAT-006 — Load user catalogues for CAD (SELECT)
**Source:** `CADMaintenance.cs`, line ~8692
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly, Catalogue.CatalogueType
FROM PDMUserCatalogues puc
INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId
WHERE puc.UserId = <AuthenticateUser.UserId>
  AND Catalogue.Status = 1
ORDER BY Catalogue.Name
```
**WHY:** Same per-user catalogue gating as Q-CAT-001, but additionally selects `CatalogueType` (used by CAD maintenance to branch behaviour) and hard-filters to `Status = 1` (active only — no OBS toggle here).

### Q-CAT-007 — Read catalogue/site flags (SELECT)
**Source:** `ProductDescriptions.cs`, line ~4890
```sql
SELECT PrimarySiteId, CatalogueFlags FROM Catalogue WHERE CatalogueId = <selected CatalogueId>
```
**WHY:** Loads the catalogue's primary site and flags when a catalogue is selected; `{NoLabel}` presence sets the EOS-label checkbox state (line ~4900).

### Q-CAT-008 — Catalogue image lookup (SELECT)
**Source:** `CADMaintenance.cs`, line ~8230
```sql
SELECT ImageFile FROM Catalogue WHERE CatalogueId = <objectId>
```
**WHY:** Retrieves the catalogue's associated image file for display.

### Q-CAT-009 — Alphabetical catalogue sort (NONE — dead)
**Source:** `ProductDescriptions.cs` `AlphaButton_Click`, line ~13124
No SQL is executed. The confirm dialog's `Yes` branch is an **empty block** (`if (msgBoxResult != MsgBoxResult.Yes) { }`). See BR-CAT-014.

> **Injection note:** Every query above concatenates identifiers/values (`UserId`, `CatalogueId`, `CatalogueFlags` text) directly into SQL. Q-CAT-005 concatenates the free-text `CatalogueFlags` value inside single quotes with no escaping — a stored/second-order injection vector if flag text ever contains a quote.

---

## 5. Data Model

### `Catalogue`
| Column | Type (inferred) | Notes |
|---|---|---|
| `CatalogueId` | int PK | Primary key; sentinel `-1` used by callers to mean "all catalogues" (see `16_Ordering.md`). |
| `Name` | string | Fallback display name when no localized description. |
| `DisplayOrder` | int | User-defined ordinal; `-1` treated as `9999` (last) by consuming sort queries (see 04). |
| `DescriptionId` | int FK → `OtherDescription.DescriptionId` | Localized name source. |
| `CatalogueType` | int/string | Branches CAD behaviour. Exact value meanings `UNKNOWN` (not resolved in read scope). |
| `Status` | int | `1` = Active, `2` = Obsolete (OBS). `< 2` used as a selection predicate elsewhere. Other status codes `UNKNOWN`. |
| `CatalogueFlags` | string | Free-text token bag; known token `{NoLabel}` = suppress EOS catalogue label. |
| `PrimarySiteId` | int FK → `Site.SiteId` | Catalogue's primary site. |
| `ImageFile` | string | Catalogue image filename. |

### `PDMUserCatalogues`
| Column | Notes |
|---|---|
| `UserId` | FK → user (see `02_User_Permissions.md`). |
| `CatalogueId` | FK → `Catalogue`. |
| `ReadOnly` | **INVERTED flag** (foundation fact): documented elsewhere as `1 = full access, 0 = read`. Carried into `_readOnlyCatalogues` to gate writes. Verify polarity per consumer. |

### `OtherDescription`
| Column | Notes |
|---|---|
| `DescriptionId` | Join key from `Catalogue.DescriptionId`. |
| `LanguageId` | Language filter; `1` = base/English (repeated hardcode). |
| `ShortDescription` | Localized catalogue name. |

**Relationships**
```
Catalogue 1───* PDMUserCatalogues *───1 (User)
Catalogue *───1 OtherDescription        (via DescriptionId + LanguageId)
Catalogue 1───* CatalogueProductCategories   (see 04_Product_Categories.md)
Catalogue *───1 Site                    (via PrimarySiteId)
```

### Catalogue status vocabulary (from `CatalogueMaintenance` designer menu, intent only)
| Menu text | Code hint |
|---|---|
| Unreleased (URL) | status label "URL" |
| Active | maps to `Status = 1` |
| Obsolete (OBS) | maps to `Status = 2` |
| On Hold | code `UNKNOWN` |

> These four are declared as `MenuItem` text in the dead form; there is **no code** setting these statuses. Numeric mapping for URL / On Hold is `UNKNOWN`.

---

## 6. Business Rules

- **BR-CAT-001** — The main-menu "Catalogue Maintenance" button is visible **only** when `AuthenticateUser.CatalogueMaintenance == true`. Source: `MainMenu.cs` ~3025 (`enabledButtons.Add("CatMaintButton")`).
- **BR-CAT-002** — Clicking "Catalogue Maintenance" does **not** open an in-app form; it launches the external process `DPS.exe` with arguments `"<isReadOnly> maintenanceCAT <Global.connectedDB> <Global.connectedServer>"`. Source: `MainMenu.cs` `CatMaintButton_Click` ~2696.
- **BR-CAT-003** — The `isReadOnly` argument passed to `DPS.exe` is `true` when the user does **not** have `AuthenticateUser.CoreMaintenance`; otherwise `false`. Source: `MainMenu.cs` ~2705 (`if (!AuthenticateUser.CoreMaintenance) flag = true`).
- **BR-CAT-004** — Only one instance of DPS may run; the code guards with `if (0 == 0)` (always-true, effectively dead guard) and otherwise would show "Only one instance of DPS can be loaded at any given time". The single-instance check is **not actually implemented** (constant condition). Source: `MainMenu.cs` ~2703.
- **BR-CAT-005** — The catalogue dropdown lists only catalogues explicitly granted to the current user via `PDMUserCatalogues` (join on `UserId`). Source: Q-CAT-001.
- **BR-CAT-006** — By default the catalogue list shows only **active** catalogues (`Catalogue.Status = 1`). Source: Q-CAT-001 (`ShowOBSCatalogueCheck` unchecked branch).
- **BR-CAT-007** — When `ShowOBSCatalogueCheck` is checked, the list shows **only obsolete** catalogues (`Catalogue.Status = 2`) — it is a *replace*, not an *add*: active catalogues disappear. Source: `ProductDescriptions.cs` ~4590.
- **BR-CAT-008** — Catalogues in the dropdown are ordered alphabetically by `Catalogue.Name`. Source: Q-CAT-001 `ORDER BY Catalogue.Name`.
- **BR-CAT-009** — After loading, the dropdown auto-selects the user's `AuthenticateUser.DefaultCatalogueId` if present in the list; otherwise it selects index `0`. Source: `ProductDescriptions.cs` ~4602–4608.
- **BR-CAT-010** — Each catalogue's per-user `ReadOnly` flag is captured into `_readOnlyCatalogues` in parallel with the id list, to gate write operations per catalogue. Source: `ProductDescriptions.cs` ~4598.
- **BR-CAT-011** — The CAD-maintenance catalogue list is **always** active-only (`Status = 1`) with no obsolete toggle, and additionally reads `CatalogueType`. Source: Q-CAT-006.
- **BR-CAT-012** — The "EOS catalogue label" checkbox reflects and controls the `{NoLabel}` token inside `Catalogue.CatalogueFlags`: token present ⇒ label suppressed ⇒ checkbox **unchecked**. Source: `ProductDescriptions.cs` ~4900, ~13176–13181.
- **BR-CAT-013** — Toggling the EOS label writes the whole `CatalogueFlags` string back: the code strips any existing `{NoLabel}`, then re-prepends `{NoLabel}` only when the checkbox is unchecked, preserving other flag tokens. Source: `ProductDescriptions.cs` `EOSCatalogueLabelCheck_Changed`.
- **BR-CAT-014** — "Sort catalogues alphabetically" (AlphaButton) is a **non-functional / dead** feature: it prompts for confirmation ("This will sort all catalogues alphabetically, overriding current order") but performs **no action** on `Yes`. Source: `ProductDescriptions.cs` `AlphaButton_Click` (empty branch).
- **BR-CAT-015** — Catalogue display re-ordering is delegated to the shared `OrderCategories` form invoked with `catalogueId = -1`. Source: `ProductDescriptions.cs` `SortButton_Click` ~13111. (Behaviour in `16_Ordering.md`.)
- **BR-CAT-016** — The EOS-label read/write only runs when a catalogue is selected **and** the form is not in its `loading` phase: `if ((catalogue_selector.SelectedIndex > -1) & !loading)`. Source: `ProductDescriptions.cs` ~13165.
- **BR-CAT-017** — On any SQL error in `initialiseCatalogues`, the raw exception **and the full SQL text** are shown to the user via `MsgBox` (`ex.ToString() + "\r\n\r\n" + text`). Source: `ProductDescriptions.cs` ~4614. (Leaks schema/SQL to end users.)
- **BR-CAT-018** — Localized catalogue names come from `OtherDescription` filtered by `LanguageId`, falling back to `Catalogue.Name` when no translation exists (`CASE WHEN od.ShortDescription IS NULL THEN Catalogue.Name`). Source: Q-CAT-002.
- **BR-CAT-019** — The dead `CatalogueMaintenance` form documents the *intended* catalogue-status vocabulary — Unreleased (URL), Active, Obsolete (OBS), On Hold — and a "Catalogue → Remove" action, but none of these are implemented in this codebase (handled by external `DPS.exe`). Source: `CatalogueMaintenance.cs` `InitializeComponent` menu items.

---

## 7. Hidden Logic

- **`DPS.exe` external hand-off** — All real catalogue CRUD lives in a separate executable (`DPS.exe`), invoked with the magic argument literal `"maintenanceCAT"`. This WinForms solution only *reads* catalogue metadata; it never creates/edits/deletes catalogues itself. Source: `MainMenu.cs` ~2711.
- **Constant single-instance guard** — `if (0 == 0)` is always true; the "only one instance of DPS" message is unreachable. Source: `MainMenu.cs` ~2703.
- **`{NoLabel}` magic token** — Feature flags are embedded as substrings inside the free-text `CatalogueFlags` column rather than as columns. Only `{NoLabel}` is handled in read scope; other tokens may exist (`UNKNOWN`).
- **Status magic numbers** — `1` = Active, `2` = Obsolete throughout; `< 2` used as an "active-ish" predicate in some sibling queries (e.g. `ProductDescriptions.cs` ~4794 `WHERE Status < 2`). URL / On Hold numeric codes are `UNKNOWN`.
- **`LanguageId = 1` hardcode** — Base language is repeatedly hardcoded as `1` in catalogue-related joins.
- **Sentinel `-1` for `CatalogueId`** — Passed to `OrderCategories` to mean "operate on catalogues, not product categories".
- **Dead alphabetical-sort feature** — UI present, logic absent (BR-CAT-014).
- **Dead form** — `CatalogueMaintenance.cs` exists but is never used (BR-CAT-019).

---

## 8. UI Behaviour

- The catalogue dropdown is (re)populated by `initialiseCatalogues` on GUI init and whenever `ShowOBSCatalogueCheck` changes (`ShowOBSCatalogueCheck_Changed` → `initialiseCatalogues`). Source: `ProductDescriptions.cs` ~13154.
- Toggling "Show OBS" **replaces** the whole list (active ↔ obsolete), it does not merge them (BR-CAT-007). This is a surprising UX: checking the box hides all active catalogues.
- Selecting a catalogue triggers a flags read (Q-CAT-007) which sets the EOS-label checkbox state; the label toggle then writes immediately on change (no explicit Save), but only when not in `loading` state (BR-CAT-016).
- "Sort" opens a modal (`ShowDialog`) catalogue-ordering window; on close the parent list is not auto-refreshed in the read scope (`UNKNOWN` whether the caller re-queries).
- "Alpha" shows a Yes/No confirmation then does nothing (BR-CAT-014) — user sees no effect.
- The main-menu button set is rebuilt each time privileges are evaluated; buttons are all hidden first, then re-added based on flags (`CatMaintButton` among them). Source: `MainMenu.cs` ~3000–3040.
- The `CatalogueMaintenance` form's designer defines a `DataTree` (TreeView), a properties panel (Name / Data Type / Ordinal / Status / Order Code / Image / Image DLL / Has Dependency), three product list boxes (Products in PDM / Potential Products / Invalid Products) and a product-configuration attribute grid — but since the form is never shown, none of this renders at runtime.

---

## 9. Dependencies

| Dependency | Role |
|---|---|
| `ConnectionFactory.CreateNewConnection(autoOpen:true)` | Builds/open the `SqlConnection` against `Global.connectedServer` / `Global.connectedDB`. |
| `Global` (static singleton) | `connectedServer`, `connectedDB` used in SQL target + DPS args. |
| `AuthenticateUser` (static) | `CatalogueMaintenance` (menu gate), `CoreMaintenance` (DPS read-only arg), `UserId` (catalogue filter), `DefaultCatalogueId` (default selection). |
| `DPS.exe` (external process) | Actual catalogue maintenance application. |
| `OrderCategories` form | Catalogue display-order editor (module 16). |
| `ProductDescriptions` form | De-facto catalogue-consuming UI (list, flags, sort entry points). |
| `CADMaintenance` form | Alternate catalogue consumer (adds `CatalogueType`). |
| DB tables | `Catalogue`, `PDMUserCatalogues`, `OtherDescription`, `Site` (via `PrimarySiteId`). |
| DB tables (related) | `CatalogueProductCategories`, `CatalogueItems`, `CatalogueOptionValues`, `CatalogueApplicationText` (used by siblings; see 04 / other modules). |

---

## 10. Risks

- **R-CAT-1 (High, migration blocker):** Core catalogue CRUD is **outside this codebase** — it lives in `DPS.exe` (`maintenanceCAT` mode). Any migration must locate and reverse `DPS.exe` separately; this repo cannot fully specify catalogue creation/edit/delete/status transitions. Status codes for URL / On Hold are `UNKNOWN` here.
- **R-CAT-2 (High, security):** SQL injection throughout (Q-CAT-001…008 concatenate values). Q-CAT-005 concatenates unescaped free-text `CatalogueFlags` inside quotes → second-order injection risk.
- **R-CAT-3 (Medium, correctness):** `{NoLabel}` and other feature flags are packed into a single free-text column (`CatalogueFlags`) with no schema. Token collisions / partial-match bugs are possible; migration should normalise to real columns/flags.
- **R-CAT-4 (Medium, UX/data):** "Show OBS" replaces rather than augments the catalogue list — easy to mistake for "all catalogues gone". Confirm intended behaviour before re-implementing.
- **R-CAT-5 (Medium, information disclosure):** On error, `initialiseCatalogues` shows the full SQL + exception to end users (BR-CAT-017).
- **R-CAT-6 (Low, tech debt):** Dead `CatalogueMaintenance` form and dead AlphaButton feature — do **not** port as-is; they encode intent, not behaviour.
- **R-CAT-7 (Low, correctness):** The `if (0 == 0)` single-instance guard is a no-op; multiple DPS instances could be spawned.
- **R-CAT-8 (Medium, coupling):** The per-catalogue `ReadOnly` flag has inverted polarity (foundation fact: `1 = full`, `0 = read`). Mis-porting the polarity silently grants or denies write access.
- **R-CAT-9 (Low, concurrency):** Catalogue flag writes (Q-CAT-005) are last-writer-wins with no optimistic concurrency; concurrent editors overwrite each other's flags.
