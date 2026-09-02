# 23 — Generation (Handbook / Pricebook Designer)
**Module prefix:** BR-GEN
**Primary legacy source:** HandbookDesigner.cs, HBExclusions.cs, MainMenu.cs (trigger)
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

This module is the **Handbook / Pricebook Designer** — the tool that authors the
*definitions* of printed/PDF pricing handbooks (a.k.a. price lists / pricebooks)
that Herman Miller publishes to dealers. A "handbook" is a curated, ordered
selection of catalogue products, the attributes and options shown for each, the
increment (surcharge) data to display, and per-group exclusions.

Crucially, `HandbookDesigner` is a **metadata editor**, not a document renderer.
Everything the user does in this form ultimately reads from / writes to a family
of `Handbook*` SQL tables. The only "generation" call issued from the client is a
**stored-procedure preview** (`PDMPriceListReportForProductGroup`) that returns
the increment-data text for one product group so the designer can review it. The
actual rendering of the finished handbook/pricebook document (PDF/print) is
performed **server-side** by a separate publication process that consumes the
`Handbook*` definition tables and the `PublishCategory` flag — that renderer is
**not present in this source tree** and is therefore `UNKNOWN` (see §7 and §10).

`HBExclusions` is the companion dialog that manages per-group attribute/option
exclusion lists for a handbook.

The form window title is set to **"PDM Handbook / Pricebook Designer"**
(HandbookDesigner.cs, constructor region).

---

## 2. Entry Points

| Trigger | Handler | Permission gate | Launches |
|---|---|---|---|
| **"Handbook Designer"** button (`HandbookButton`) | `HandbookButton_Click` (MainMenu.cs:2902) | `AuthenticateUser.HandbookPublication` **and** connected server not `"eoscloud"` (MainMenu.cs:3092) | `HandbookDesigner` form |
| Group context-menu ▸ **exclusions** | `menuAttributeExclusions_Click` / `menuOptionExclusions_Click` | inside `HandbookDesigner` | `HBExclusions` form (`initValues("Attribute"/"Option", …)`) |

`HandbookDesigner` constructor is at HandbookDesigner.cs:1604; the form-load
population runs in `HandbookDesigner_Load` (HandbookDesigner.cs:2384).

`HBExclusions` is entered via `initValues(table, catalogueId, categoryId,
handbookId, groupId)` (HBExclusions.cs:254) where `table` is `"Attribute"` or
`"Option"`.

---

## 3. Call Hierarchy

```
MainMenu (Form)
└─ HandbookButton_Click ─────────────► HandbookDesigner (Form)
     └─ HandbookDesigner_Load
         ├─ populate catalogue/site/language/currency selectors (SQL reads)
         ├─ handbook_selector.SelectedIndexChanged ─► load HandbookProducts / groups
         ├─ category_selector / GroupList ─► load HandbookAttributes / HandbookOptions
         └─ context-menu handlers (no worker thread — direct ADO on the UI thread):
             ├─ menuAddNewGroup / menuAddNewGroupClone ─► INSERT HandbookProducts (+ShiftGroups)
             ├─ menuAddProduct                          ─► INSERT HandbookProducts
             ├─ menuAddAttribute                        ─► INSERT HandbookAttributes
             ├─ menuAddOption                           ─► INSERT HandbookOptions
             ├─ menuRemoveGroup / menuRemoveProduct     ─► DELETE + renumber ProductGroupId
             ├─ menuRenameGroup                         ─► UPDATE HandbookProducts.GroupName
             ├─ menuImportGroup                         ─► INSERT (copy group rows)
             ├─ PublishCheck_MouseUp                    ─► UPDATE HandbookProducts.PublishCategory
             ├─ (option hide/show)                      ─► UPDATE HandbookOptions SET OptNum = OptNum * -1
             ├─ menuAttributeExclusions / menuOptionExclusions ─► HBExclusions.initValues → INSERT/DELETE Handbook{Attribute,Option}Exclusions
             └─ GroupList_SelectedIndexChanged / IncData load
                   └─ EXEC PDMPriceListReportForProductGroup (SqlDataReader "incdata")  ── preview only
                                                             │
                                                             └─ (proc body UNKNOWN — server-side generation)

[server-side, OUT OF SOURCE] publication renderer ──► reads Handbook* + PublishCategory=1 ──► PDF / pricebook (UNKNOWN)
```

There is **no worker thread** in this module (unlike Export) and **no file /
`StreamWriter` output** anywhere in `HandbookDesigner` or `HBExclusions`
(verified by grep). All generation output is either DB rows or the
proc-returned preview string.

---

## 4. SQL Analysis

All SQL is inline string-concatenation on the UI thread (see §10).

**Q-GEN-001** — Load accessible catalogues (HandbookDesigner.cs:2242 region):
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly
FROM PDMUserCatalogues puc INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId
WHERE puc.UserId = <UserId> AND Catalogue.Status = 1 ORDER BY Catalogue.Name
```
WHY: restricts the catalogue picker to catalogues the user may access (active
catalogues only). When `Global.connectedDB = 'PDMPublished'` this is replaced by a
`DealerCatalogues`-based query (see BR-GEN-002).

**Q-GEN-002** — Sites list, excluding site 20 (HandbookDesigner.cs:2273 region):
```sql
SELECT SiteId, Description FROM Site WHERE SiteId NOT IN (20) ORDER BY Description
```
WHY: site 20 is excluded from handbook publication (same site-20 special-casing as
[22_Export.md](22_Export.md)).

**Q-GEN-003** — Products flagged for publication (HandbookDesigner.cs:2465):
```sql
SELECT DISTINCT ProductId, PublishCategory, ProductGroupId
FROM HandbookProducts WHERE HandbookId = <handbookId>
```
WHY: enumerates the products in the handbook and which groups are flagged
`PublishCategory = 1` (publishable).

**Q-GEN-004** — Items belonging to publishable groups (HandbookDesigner.cs:2489):
```sql
SELECT DISTINCT Item.ItemId, Item.ProductId, hbp.ProductGroupId, hbp.PublishCategory
FROM Item INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId AND ci.CatalogueId = <catalogueId>
INNER JOIN HandbookProducts hbp ON Item.ProductId = hbp.ProductId AND hbp.HandbookId = <handbookId>
…
```
WHY: counts the items that will be generated, to enforce the memory-capacity
guards (BR-GEN-008) — only rows with `PublishCategory = 1` are counted.

**Q-GEN-005** — Group list for a category (HandbookDesigner.cs:2820):
```sql
SELECT DISTINCT ProductGroupId, GroupName, PublishCategory, SeparateIncrements
FROM HandbookProducts WHERE HandbookId = <handbookId> AND ProductCategoryId = <categoryId>
ORDER BY ProductGroupId
```
WHY: populates the `GroupList` tree with each group's publish/separate-increments state.

**Q-GEN-006** — Create a new handbook (HandbookDesigner.cs:2739 region):
```sql
INSERT INTO Handbook (HandbookName, CatalogueId) VALUES ('<name>', <catalogueId>)
```
WHY: creates the top-level handbook record.

**Q-GEN-007** — Toggle option visibility (HandbookDesigner.cs:3214):
```sql
UPDATE HandbookOptions SET OptNum = OptNum * -1 WHERE HandbookId = <h> AND ProductGroupId = <g> AND OptionId = <o>
```
WHY: a **negative `OptNum` hides an option** from the generated handbook without
deleting the row (sign flip = show/hide toggle).

**Q-GEN-008** — Increment-data preview / generation proc (HandbookDesigner.cs:3306):
```sql
DECLARE @mydate datetime SET @mydate = GetUTCDate()
EXEC PDMPriceListReportForProductGroup
     <handbookId>, <groupId>, <siteId>, <catalogueId>, <categoryId>,
     '<currency> ', <languageId>, @mydate , '<content>'
```
WHY: **the generation engine.** Returns an `incdata` column that is displayed in
`IncDataBox` (with `_` → CRLF substitution). `CommandTimeout = 300`. The stored
procedure **body is UNKNOWN** (not in the source tree) — it is the mechanism that
assembles the price-list content for a product group. Note the trailing space
after `<currency>` and after `PDMPriceListReportForProductGroup` args are
literal in the source.

**Q-GEN-009** — Exclusion candidate list (HBExclusions.cs:275):
```sql
SELECT DISTINCT atval.<table>ValueId, attr.DisplayOrder, attr.Name AS attr_name,
       atval.DisplayOrdinal, atval.Name AS atval_name
FROM <table> attr INNER JOIN <table>Value atval ON attr.<table>Id = atval.<table>Id
…  ORDER BY attr.DisplayOrder, atval.DisplayOrdinal
```
WHERE `<table>` is `"Attribute"` or `"Option"`, so the query targets
`Attribute`/`AttributeValue` or `Option`/`OptionValue` dynamically.
WHY: lists the attribute-values / option-values available to exclude for a group.

**Q-GEN-010** — Add an exclusion (HBExclusions.cs:340):
```sql
INSERT INTO Handbook<table>Exclusions (HandbookId, ProductGroupId, <table>ValueId)
VALUES (<handbookId>, <groupId>, <valueId>)
```
WHY: excludes an attribute-value/option-value from a handbook group. Resolves to
`HandbookAttributeExclusions` or `HandbookOptionExclusions`.

**Q-GEN-011** — Remove an exclusion (HBExclusions.cs:379):
```sql
DELETE FROM Handbook<table>Exclusions
WHERE HandbookId = <handbookId> AND ProductGroupId = <groupId> AND <table>ValueId = <valueId>
```
WHY: re-includes a previously-excluded value.

> Group/product/attribute/option **add, remove, rename, import, and reorder**
> handlers each issue their own `INSERT`/`UPDATE`/`DELETE` against the
> `HandbookProducts` / `HandbookAttributes` / `HandbookOptions` tables with
> `ProductGroupId` shift arithmetic (see BR-GEN-005/006). These follow the same
> pattern as Q-GEN-006/007 and are not individually transcribed here — see
> coverage limits in §10.

---

## 5. Data Model

The entire module is a metadata layer over these **`Handbook*` tables**:

| Table | Key columns (verified from SQL usage) | Role |
|---|---|---|
| **`Handbook`** | `HandbookId`, `HandbookName`, `CatalogueId` | top-level handbook record |
| **`HandbookProducts`** | `HandbookId`, `ProductGroupId`, `ProductCategoryId`, `GroupName`, `ProductOrder`, `ProductId`, `PrimaryProduct`, `ProductListEntry`, `DefaultAttributes`, `SeparateIncrements`, `DescriptionId`, `AlternateImageFile`, `PublishCategory` | the ordered product groups & their members |
| **`HandbookAttributes`** | `HandbookId`, `ProductGroupId`, `AttrNum`, `AttributeId`, `ColIndex`, `GroupCodeOffset`, `PriceListDelimiter` | attributes shown per group |
| **`HandbookOptions`** | `HandbookId`, `ProductGroupId`, `OptNum`, `OptionId`, `ColIndex`, `AltName`, `ShowDependencies`, `OutputExample` | options shown per group (`OptNum` sign = show/hide) |
| **`HandbookAttributeExclusions`** | `HandbookId`, `ProductGroupId`, `AttributeValueId` | attribute-values hidden per group |
| **`HandbookOptionExclusions`** | `HandbookId`, `ProductGroupId`, `OptionValueId` | option-values hidden per group |
| **`HandbookIncrementDesc`** | `ItemListData`, `SubstituteDescription` (+ handbook/group keys) | manual increment-description overrides |

### Source tables (read-only reference)
`Catalogue`, `PDMUserCatalogues`, `DealerCatalogues`, `Site`, `Language`,
`Currency`, `Item`, `CatalogueItems`, `Attribute`, `AttributeValue`, `Option`,
`OptionValue`.

### Generation input/output
- **Input to generation:** the `Handbook*` definition rows + `PublishCategory = 1`
  flag + the selected site/language/currency/content parameters.
- **Client-side output:** the `incdata` preview string from
  `PDMPriceListReportForProductGroup` (Q-GEN-008), shown in `IncDataBox`.
- **Server-side output:** the rendered handbook/pricebook document (PDF/print) —
  produced by an external publication process, **format & mechanism UNKNOWN**
  (not in source).

---

## 6. Business Rules

### Permission / access
- **BR-GEN-001** The Handbook Designer button is enabled only when
  `AuthenticateUser.HandbookPublication` is true **and** the connected server name
  does not contain `"eoscloud"` (MainMenu.cs:3092) — disabled on the cloud DB.
- **BR-GEN-002** When `Global.connectedDB = 'PDMPublished'` the catalogue picker is
  populated from `DealerCatalogues` (dealer-facing published DB) instead of
  `PDMUserCatalogues` (HandbookDesigner.cs:2230 region).
- **BR-GEN-003** Catalogue read-only state comes from `PDMUserCatalogues.ReadOnly`
  (Q-GEN-001); read-only catalogues restrict editing (same inverted `ReadOnly`
  semantics as [02_User_Permissions.md](02_User_Permissions.md)).

### Structure editing
- **BR-GEN-004** Site 20 is excluded from the site picker
  (`WHERE SiteId NOT IN (20)`, Q-GEN-002).
- **BR-GEN-005** Inserting a group **shifts** existing `ProductGroupId` values up
  by 1, and removing a group shifts them down by 1, to keep the ordering dense
  (HandbookDesigner.cs group add/remove handlers).
- **BR-GEN-006** "Add group (clone)" copies an existing group's rows into the new
  `ProductGroupId` (menuAddNewGroupClone), and "Import group" copies group rows
  from another handbook (menuImportGroup).
- **BR-GEN-007** A **negative `HandbookOptions.OptNum`** hides that option from the
  generated output (toggle via `OptNum = OptNum * -1`, Q-GEN-007) — the row is
  retained, not deleted.

### Publication flags & capacity guards
- **BR-GEN-008** Memory-capacity guard: if a publish selection exceeds **500
  products** or **1000 items** the user is warned
  *"This will likely exceed the server memory capacity. Please separate the offer
  in to multiple handbooks."* — **unless** the handbook name/type indicates a
  *"pricebook"*, in which case the limit is not enforced (`checkGroupLimit` /
  `productGroupLimit` / `itemGroupLimit`, HandbookDesigner.cs:3358 region + counts
  from Q-GEN-003/Q-GEN-004).
- **BR-GEN-009** Only groups with `HandbookProducts.PublishCategory = 1` are
  included in the publishable set (Q-GEN-003, Q-GEN-004; the publishable-group
  query filters `AND hbp.PublishCategory = 1`, HandbookDesigner.cs:2564).
- **BR-GEN-010** The `PublishCheck` checkbox toggles `PublishCategory` for the
  selected group via `PublishCheck_MouseUp` (HandbookDesigner.cs:1102 wiring).
- **BR-GEN-011** `SeparateIncrements` per group (Q-GEN-005) controls whether
  increment data is broken out separately in generation (flag surfaced but the
  downstream rendering behaviour is server-side/UNKNOWN).

### Increment-data preview / generation
- **BR-GEN-012** Increment preview is produced by
  `EXEC PDMPriceListReportForProductGroup` (Q-GEN-008) with `@mydate = GetUTCDate()`
  and a `CommandTimeout` of **300 seconds** (large reports are expected).
- **BR-GEN-013** The `incdata` result has `"_"` replaced with CRLF and any
  resulting double-CRLF collapsed to single, before display
  (HandbookDesigner.cs:3312) — i.e. `_` is the proc's line delimiter.
- **BR-GEN-014** The `content_selector` value (e.g. price-list content mode) is
  passed as the final `'<content>'` argument to the proc (Q-GEN-008) and thus
  changes what the generation returns.
- **BR-GEN-015** `HandbookIncrementDesc.SubstituteDescription` lets an author
  override the auto-generated increment text for a given `ItemListData` key
  (Sub-description grid, `SubDescCheck` / `AddSubButton`).

### Exclusions (HBExclusions)
- **BR-GEN-016** The exclusion dialog operates on a **dynamic table name**:
  `"Attribute"` → `HandbookAttributeExclusions`, `"Option"` →
  `HandbookOptionExclusions` (HBExclusions.cs:340, 379) — the same code path
  handles both by string substitution.
- **BR-GEN-017** Adding an exclusion inserts one row per selected value
  (HandbookId, ProductGroupId, ValueId) and de-duplicates against the already-loaded
  `_exclusionList` (HBExclusions.cs:288, 340).
- **BR-GEN-018** Removing an exclusion deletes exactly the matching
  (HandbookId, ProductGroupId, ValueId) row (HBExclusions.cs:379).
- **BR-GEN-019** Exclusion candidates are ordered by attribute/option
  `DisplayOrder` then value `DisplayOrdinal` (Q-GEN-009) — matches the display
  ordering used elsewhere in PDM.

### Data-access convention
- **BR-GEN-020** All handbook edits run **synchronously on the UI thread** against
  a fresh `ConnectionFactory.CreateNewConnection(autoOpen:true)` opened and closed
  per operation (e.g. HandbookDesigner.cs:3305) — no worker thread, no transaction
  spanning multiple statements.

---

## 7. Hidden Logic

- **The real handbook/pricebook renderer is NOT in this source tree.**
  `HandbookDesigner` only *defines* handbooks and *previews* increment data via
  `PDMPriceListReportForProductGroup`. The process that turns `PublishCategory = 1`
  groups into a finished PDF/pricebook runs **server-side / externally** and is
  **UNKNOWN** — do not assume this client renders the document.
- **`OptNum` sign is a hidden show/hide switch** (BR-GEN-007) — a maintainer
  reading the table would not obviously know negative = hidden.
- **`_` is a hidden line delimiter** in the proc's `incdata` output (BR-GEN-013).
- **`"pricebook"` name/type bypasses the memory-capacity guard** (BR-GEN-008) — a
  soft, string-driven feature flag.
- **`GroupCodeOffset` / `PriceListDelimiter`** on `HandbookAttributes` and
  **`OutputExample` / `ShowDependencies`** on `HandbookOptions` are stored by the
  designer but consumed by the (UNKNOWN) server renderer — their exact effect is
  not provable from this source.
- **`DealerCatalogues` swap** (BR-GEN-002) silently changes the catalogue source
  depending on which database the client is connected to.

---

## 8. UI Behaviour

- The form is titled **"PDM Handbook / Pricebook Designer"** and is laid out as a
  cascade of selectors: `handbook_selector` → `category_selector` → `GroupList`,
  with `site_selector`, `language_selector`, `currency_selector`, and
  `content_selector` feeding the increment preview.
- The main working area is a **tree/list of groups** (`GroupList`) with a
  **context menu** (`menuAddNewGroup`, `menuAddNewGroupClone`, `menuAddProduct`,
  `menuAddAttribute`, `menuAddOption`, `menuRemoveGroup`, `menuRenameGroup`,
  `menuImportGroup`, `menuRemoveProduct`, attribute/option exclusions) — right-click
  driven editing of the handbook definition.
- `GroupList_MouseMove` shows a tooltip with the group name and its
  `ProductGroupId` (HandbookDesigner.cs:3330).
- Selecting a group loads its increment data into `IncDataBox` via the proc
  (Q-GEN-008); `IncDataBox.Text = "Loading ..."` and the cursor switches to
  `WaitCursor` during the (potentially long) call.
- Increment-substitution grids (`IncDataGrid`, `SubDataGrid`, `SubDescCheck`,
  `AddSubButton`) let the author override increment descriptions
  (`HandbookIncrementDesc`).
- The **`PublishCheck`** checkbox marks the current group publishable
  (`PublishCategory`), guarded by the capacity warning (BR-GEN-008).
- The **exclusions** dialog (`HBExclusions`) is a two-list add/remove picker
  ("Exclusions:") that commits immediately on Add/Remove.

---

## 9. Dependencies

- **`ConnectionFactory.CreateNewConnection`** — PDM DB access (see
  [00_System_Architecture.md](00_System_Architecture.md)).
- **`Global`** — `connectedDB` (`'PDMPublished'` switch), `connectedServer`
  (eoscloud gate).
- **`AuthenticateUser`** — `HandbookPublication` gate, `UserId`.
- **`PDMPriceListReportForProductGroup`** stored procedure — the generation engine;
  **body UNKNOWN**.
- **`HBExclusions`** child form.
- **`Handbook*` SQL tables** (§5) plus reference tables `Catalogue`,
  `PDMUserCatalogues`, `DealerCatalogues`, `Site`, `Attribute`/`AttributeValue`,
  `Option`/`OptionValue`, `Item`, `CatalogueItems`.
- **External / UNKNOWN:** the server-side publication renderer that consumes the
  handbook definitions.

---

## 10. Risks

- **SQL injection.** Every statement (handbook name, group name, IDs, currency,
  content) is string-concatenated into SQL — e.g.
  `INSERT INTO Handbook (HandbookName, CatalogueId) VALUES ('<name>', …)`. A
  handbook name containing a quote can break or inject SQL.
- **Black-box generation.** The load-bearing generation logic lives in
  `PDMPriceListReportForProductGroup` (and the server-side renderer), neither of
  which is in the source tree. Migrating handbook generation requires
  reverse-engineering that procedure and the publication process from the database.
- **UI-thread, non-transactional edits** (BR-GEN-020). Multi-step operations
  (e.g. group insert + `ProductGroupId` shift) are separate statements with no
  transaction — an interruption can leave group ordering inconsistent.
- **Magic conventions** (negative `OptNum`, `_` delimiter, `"pricebook"` name
  bypass) are undocumented and easy to break in a migration.
- **Capacity guard is advisory only** (BR-GEN-008) — a warning, not an
  enforcement; a user can still attempt an over-large publish that the server may
  fail on.
- **Database-dependent behaviour** (`DealerCatalogues` when
  `connectedDB = 'PDMPublished'`) means the same UI behaves differently against
  the published vs authoring databases.

### Coverage limits
`HandbookDesigner.cs` is ~5800 lines and `HBExclusions.cs` ~402 lines. This
document fully captures: the **trigger/permission**, the **complete `Handbook*`
data model**, the **generation/preview mechanism** (`PDMPriceListReportForProductGroup`),
the **exclusion mechanism**, and the significant hard-coded rules
(publish flag, capacity guard, `OptNum` toggle, site-20/eoscloud/`PDMPublished`
gates). The **individual `INSERT`/`UPDATE`/`DELETE` bodies** of the many
group/product/attribute/option context-menu handlers follow the patterns in
Q-GEN-006/007/010/011 and are not each transcribed verbatim. The **server-side
publication renderer** and the **body of `PDMPriceListReportForProductGroup`** are
**not present in the source** and are marked `UNKNOWN` — the actual document
(PDF/pricebook) format and rendering rules cannot be verified from this client.
