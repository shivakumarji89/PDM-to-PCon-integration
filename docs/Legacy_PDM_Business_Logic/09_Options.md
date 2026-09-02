# 09 — Options

**Module prefix:** BR-OPT
**Primary legacy source:** `OptionClass.cs`, `OptionGroup.cs`, `SIFExportThread.cs`, `ProductDescriptions.cs`, `CADMaintenance.cs`, `SIFImport.cs`, `AddNewData.cs`, `MainMenu.cs`, `OFDAExport.cs`, `SytelineExport.cs`, `OCDExport.cs` (stored proc `PDMOptionDataReport`)
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

An **Option** is the *definition* of a configurable choice attached to a product/super‑product — e.g. "Fabric Type", "Fabric Colour", "Base Colour", "Arm Style". It is the container/grouping level; the individual selectable values it holds ("Black", "Chrome", a specific fabric) are **Option Values** (see [10_Option_Values.md](10_Option_Values.md)).

Options are **DB‑backed maintenance entities** persisted in the SQL table `[Option]`. They are *not* purely export DTOs. However, three in‑process helper classes share the "Option" name and are pure in‑memory holders used only by exporters:

- `OptionClass` — an export/grouping DTO (one option + its parallel value arrays) used by SIF export.
- `OptionGroup` — an export/permutation DTO (one option + its order codes / incremental prices) used by SyteLine price‑permutation export.
- `OptionData` — a bulk column‑array DTO fed from `PDMOptionDataReport`; documented in [10_Option_Values.md](10_Option_Values.md) because it is value‑centric.

> **Clarification (per task):** `OptionClass` and `OptionGroup` are **export DTOs**, NOT database tables. The database‑backed maintenance entity is the `[Option]` table (this module) and the `OptionValue` table (module 10). `OptionData` is likewise an export DTO.

The central read path for *both* options and option values is the stored procedure **`PDMOptionDataReport`** (and its priced variants), which returns a flattened join of `[Option]` + `OptionValue` (+ parent relationships) for a given item / super‑product.

---

## 2. Entry Points

| # | Trigger | Location | Kind |
|---|---------|----------|------|
| E1 | Menu **Item Option Data Report** | `MainMenu.cs:4098` `ItemOptionDataReportToolStripMenuItem_Click` → `DataQuery.initDataQuery("PDMOptionDataReport '{text}'")` | Read‑only report (option+value dump for an item) |
| E2 | Product Descriptions context menu **Set EOS Lite Display Order** (Option branch) | `ProductDescriptions.cs:5494` | Option maintenance (UPDATE) |
| E3 | Product Descriptions context menu **Set SyteLine Feature Length** | `ProductDescriptions.cs:5523` | Option maintenance (UPDATE) |
| E4 | Product Descriptions context menu **Set Order Code Format Key** | `ProductDescriptions.cs:5587` | Option maintenance (UPDATE) |
| E5 | CAD Maintenance option list — **Hide By Default** | `CADMaintenance.cs:15859` | Option maintenance (UPDATE) |
| E6 | CAD Maintenance option list — **EOS Lite Display Order** | `CADMaintenance.cs:25098` / `25111` | Option maintenance (UPDATE) |
| E7 | SIF Import — auto‑create option during import | `SIFImport.cs:9073` `createOption`‑style block | Option creation (INSERT `[Option]`) |
| E8 | Export consumers (read only) | `OFDAExport.cs:4425/4459`, `SytelineExport.cs:4924/5336`, `SIFExportThread.cs:713/1129`, `OCDExport.cs:1889/1913`, `SuperProductMaintenance.cs:2675/2920`, `PriceMaintenance.cs:5911/9714`, `UpdatePricesThread.cs:326`, `ValidateThread.cs:178`, `ValidateSIFThread.cs:729` | Read via `PDMOptionDataReport*` |

There is **no dedicated "Option Maintenance" form**. Option definition editing is surfaced piecemeal through right‑click context menus in `ProductDescriptions` and `CADMaintenance`, and through bulk SIF import.

---

## 3. Call Hierarchy

Read report path (E1):

```
MainMenu (Form)
  └─ ItemOptionDataReportToolStripMenuItem_Click (Event)
       └─ DataQuery.initDataQuery("PDMOptionDataReport '{text}'")  (Controller/UI)
            └─ SQL: EXEC PDMOptionDataReport '<item>'              (Repository/SQL)
                 └─ grid bind (UI)
```

Option maintenance path (E2–E6):

```
ProductDescriptions / CADMaintenance (Form)
  └─ <context-menu>_Click (Event)
       └─ inline handler (Controller)
            └─ ConnectionFactory.CreateNewConnection → SqlConnection (Service/Repository)
                 └─ SQL: UPDATE [Option] SET <col> = <val> WHERE OptionId = <ctx>
                      └─ PDMAudit.dbo.Transactions insert (audit)  (Model)
                           └─ RefreshDescriptions()/reload grid (UI)
```

Option creation path (E7):

```
SIFImport (Form/Thread)
  └─ import loop (Event)
       └─ createOption helper (Controller)
            └─ parseOrderCodeFormatKey / getNextDisplayOrder / createOtherDescription (Service)
                 └─ SQL: INSERT INTO [Option] (...) ; SELECT OptionId ...
                      └─ ProductRange.OrderCodeFormatString append (Model)
```

Export/grouping path (E8, SIF):

```
SIFExportThread (Thread)
  └─ RunKeyOpt → CreateOpt(item)   (Controller)
       └─ SQL: EXEC PDMOptionDataReportWithIncList @item,@siteId,@currency,@effectivedate
            └─ builds OptionClass list (Model DTO)
                 └─ SortClasses / CheckDependents / OutputPOs / CheckDuplicate / ProcessGlobal (business logic)
                      └─ OutputOpt(file) → .opt / .key files (UI/output)
```

---

## 4. SQL Analysis

> All SQL below is **inline string‑concatenated** and therefore SQL‑injection‑prone (foundation fact — not re‑explained per query).

### Q-OPT-001 — Item option data report (read)
`MainMenu.cs:4098`, and the same proc at `ProductDescriptions.cs:6624`, `SuperProductMaintenance.cs:2675`, etc.
```sql
PDMOptionDataReport '<item>'
```
**Why:** Central read that returns the full option + option‑value tree for one item/super‑product, including parent option relationships, display order, fabric flags, order codes and image files. Consumed by nearly every export.

### Q-OPT-002 — Priced report variants
`SIFExportThread.cs:713` (`PDMOptionDataReportWithIncList`), `ExportThread.cs:6958` / `PriceMaintenance.cs:9788` (`PDMOptionDataReportWithIncBase`), `ItemPriceExport.cs:287`.
```sql
EXEC PDMOptionDataReportWithIncList  @item, @siteId, @currency, @effectivedate
EXEC PDMOptionDataReportWithIncBase  '<item>', <siteId>
```
**Why:** Same option tree as Q‑OPT‑001 but augmented with incremental prices resolved for a site/currency/effective date. `WithIncList` returns per‑value increments; `WithIncBase` returns base‑variant increments used by pricing/permutation.

### Q-OPT-003 — Read an option's name by id
`ProductDescriptions.cs:5449` (and hardcoded ids 8, 28 for fabric type/colour).
```sql
SELECT Name FROM [Option] WHERE OptionId = 8      -- Fabric Type  (hardcoded id)
SELECT Name FROM [Option] WHERE OptionId = 28     -- Fabric Colour(hardcoded id)
SELECT Name FROM [Option] WHERE OptionId = <contextId>
```
**Why:** Resolve the display label for the "Set Alternate Product Description" context action; fabric type/colour options are addressed by **hardcoded ids 8 and 28**.

### Q-OPT-004 — Set EOS Lite Display Order (option)
`ProductDescriptions.cs:5494`
```sql
UPDATE [Option] SET EOSLiteDisplayOrder = <value> WHERE OptionId = <contextId>
```
**Why:** Controls ordering of the option in the EOS‑Lite catalogue output. Same menu also targets `Attribute` when the row is an attribute (branch on menu text containing "Attribute").

### Q-OPT-005 — Set SyteLine Feature Length
`ProductDescriptions.cs:5523`
```sql
UPDATE [Option] SET SLFeatureLength = <value> WHERE OptionId = <contextId>
```
**Why:** Stores the character length used to slice this option's feature code in SyteLine exports.

### Q-OPT-006 — Read current Order Code Format Key + collect used keys
`ProductDescriptions.cs:5540`, `:5546`
```sql
SELECT OrderCodeFormatKey FROM [Option] WHERE OptionId = <contextId>

SELECT DISTINCT OrderCodeFormatKey FROM Attribute WHERE ProductCategoryId = <catId>
UNION
SELECT DISTINCT OrderCodeFormatKey FROM [Option]  WHERE ProductCategoryId = <catId>
```
**Why:** First reads the current key; the UNION gathers every key already used by attributes/options in the category so the new key can be uniqueness‑checked (BR‑OPT‑012).

### Q-OPT-007 — Set Order Code Format Key + propagate to ProductRange
`ProductDescriptions.cs:5587`, plus range read `:5568` and range update `:5593`
```sql
SELECT ProductRangeId, OrderCodeFormatString FROM ProductRange WITH (NOLOCK)
  WHERE ProductCategoryId = <catId>

UPDATE [Option] SET OrderCodeFormatKey = '<newKey>' WHERE OptionId = <contextId>

UPDATE ProductRange SET OrderCodeFormatString = '<replaced>' WHERE ProductRangeId = <id>
```
**Why:** Changing an option's format key must also rewrite every range's `OrderCodeFormatString` (which embeds the old key token) so generated order codes stay consistent. Each affected range write is audited (Q‑OPT‑010).

### Q-OPT-008 — Hide By Default (CAD)
`CADMaintenance.cs:15859`
```sql
UPDATE [Option] SET HideByDefault = <selectedIndex> WHERE OptionId = <id> AND HideByDefault <= 9
```
**Why:** Sets a CAD/visibility flag (0–9). The `AND HideByDefault <= 9` guard prevents overwriting sentinel/locked values above 9 (BR‑OPT‑015).

### Q-OPT-009 — EOS Lite Display Order (CAD, negate / clear)
`CADMaintenance.cs:25098`, `:25111`
```sql
UPDATE [Option] SET EOSLiteDisplayOrder = <-1 * num> WHERE OptionId = <id>   -- set (stored negated)
UPDATE [Option] SET EOSLiteDisplayOrder = 0          WHERE OptionId = <id>   -- clear
```
**Why:** CAD path stores the display order **negated** (`-1 * num`); `0` clears it. (Behavioural difference vs Q‑OPT‑004 which stores the raw positive value — see BR‑OPT‑016.)

### Q-OPT-010 — Audit transaction stamp
`ProductDescriptions.cs:5595` (and repeated across maintenance)
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected)
VALUES ('<windowsUser>', GetUTCDate(), '<Global.connectedDB>')
```
**Why:** Records who changed catalogue‑affecting data; keyed off the Windows account identity (foundation fact).

### Q-OPT-011 — Create option (SIF import)
`SIFImport.cs:9073`
```sql
INSERT INTO [Option] (Name, ProductCategoryId, OrderCodeFormatKey, DisplayOrder, DescriptionId
                      [, SupplierId])
VALUES ('<camelCasedName>', <categoryId>, '{<parsedKey>}', <nextDisplayOrder>, <descId>
        [, <supplierId>])

SELECT OptionId FROM [Option]
  WHERE Name = '<name>' AND ProductCategoryId = <catId>
    AND OrderCodeFormatKey = '{<key>}'    -- or "OrderCodeFormatKey IS NULL"
    AND DisplayOrder = <nextDisplayOrder> AND DescriptionId = <descId>
```
**Why:** Auto‑creates a missing option during SIF import. `SupplierId` column is only included when a supplier is inferred (name contains "kvadrat" & a fabric‑type context → `SupplierId = 2`, BR‑OPT‑009). The re‑`SELECT` recovers the identity of the just‑inserted row (no `SCOPE_IDENTITY`; matches on all inserted columns).

### Q-OPT-012 — Append format key token to range format string (SIF import)
`SIFImport.cs` (immediately after Q‑OPT‑011)
```sql
SELECT OrderCodeFormatString FROM ProductRange WHERE ProductRangeId = <rangeId>

UPDATE ProductRange
SET OrderCodeFormatString = CASE WHEN OrderCodeFormatString IS NULL THEN '' ELSE OrderCodeFormatString END
    + '{<key>}'
WHERE ProductRangeId = <rangeId>
```
**Why:** Ensures the range's format string contains the new option's key token so its order code can be assembled.

### Q-OPT-013 — Dependent‑option lookup (SIF export dependent build)
`SIFExportThread.cs:1149`
```sql
SELECT DISTINCT DependentOptionValues.AdditionalOptionValueId, OptionValue.OptionId
FROM DependentOptionValues
INNER JOIN OptionValue ON DependentOptionValues.OptionValueId = OptionValue.OptionValueId
WHERE AdditionalOptionValueId IN (<optValIds…>)
  AND AdditionalOptionValueId IN (SELECT OptionValueId FROM CatalogueOptionValues WHERE CatalogueId = <catId>)
  AND OptionId = <optionId>
ORDER BY OptionId, AdditionalOptionValueId
```
**Why:** Resolves which option‑values in the current catalogue are *additional/dependent* on a parent option‑value, so the exporter can emit dependent option groups. Combines `DependentOptionValues` with catalogue membership.

### Q-OPT-014 — SyteLine option grouping temp table (priced permutations)
`SytelineExport.cs:4924` (and `:5336` — duplicate)
```sql
CREATE TABLE #temptable (Range2 varchar(100), ProductId INT, Product2 varchar(100),
  Option2 varchar(100), OptDescId INT, OptionId INT, OrderCodeFormatKey varchar(10),
  OptionValueId INT, OrderCodeValue2 varchar(20), Status INT, ParentOptValName varchar(100),
  ParentOptValCode varchar(20), ParentOptIsFabric INT, ParentDisplayOrder INT, DisplayOrder INT,
  EOSLiteDisplayOrder INT, DisplayOrdinal INT, TertiayOption INT, IsFabric INT,
  optval_name varchar(100), optvalDescId INT, ImageFile varchar(255),
  ProductCategoryId INT, PriceBand INT)
INSERT INTO #temptable EXECUTE pdmoptiondatareport '<item>'
SELECT DISTINCT Range2, ProductId, Product2, Option2, OptDescId, OptionId, OrderCodeFormatKey,
  OptionValueId, OrderCodeValue2, Status, DisplayOrder, DisplayOrdinal, TertiayOption, IsFabric,
  optval_name, optvalDescId, ImageFile, ProductCategoryId, PriceBand
FROM #temptable
ORDER BY Range2, Product2, DisplayOrder, DisplayOrdinal
DROP TABLE #temptable
```
**Why:** Captures the proc's result set into a temp table so it can be re‑`SELECT`ed/ordered and consumed by the `OptionGroup[]` permutation builder (`GetSMXLine`). Note `TertiayOption` misspelling (BR‑OPT‑017 / Risks).

### Q-OPT-015 — Fallback option/value lookup when Fabric Colour (opt 28) present without Fabric Type (opt 8)
`OFDAExport.cs:4544` (and MT variant `:4560`)
```sql
SELECT DISTINCT opt.OptionId, opt.DescriptionId AS optDescId, opt.DisplayOrder, opt.IsFabric,
  optval.OptionValueId, optval.DescriptionId AS optvalDescId, optval.DisplayOrdinal,
  optval.OrderCodeValue AS OrderCodeValue2, optval.ImageFile, optval.CADMaterial, optval.Status,
  <productCategoryId> AS ProductCategoryId, NULL AS ParentOptValId
FROM OptionValue optval WITH (NOLOCK)
INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId
WHERE optval.OptionValueId = <parentOptValId>            -- variant A
--   optval.OrderCodeValue = '<MT>' AND opt.ProductCategoryId = <catId>   -- variant B (MT default)
ORDER BY opt.DisplayOrder, optval.DisplayOrdinal
```
**Why:** When an item has fabric colour (option id 28) but the parent fabric‑type value (option id 8) is missing from the report, OFDA back‑fills the parent option/value row directly from `[Option]`+`OptionValue`. Variant B injects the `<MT>` "master template" default value. (BR‑OPT‑010, BR‑OPT‑011.)

---

## 5. Data Model

### Table `[Option]` (bracketed because `OPTION` is a reserved word)

| Column | Type (observed) | Meaning |
|--------|-----------------|---------|
| `OptionId` | INT (PK) | Identity of the option definition. |
| `Name` | varchar | Internal option name (camel‑cased on insert). |
| `ProductCategoryId` | INT (FK → `ProductCategory`) | Category the option belongs to. |
| `OrderCodeFormatKey` | varchar(10) | Token like `{KEY}` embedded in range `OrderCodeFormatString`; ≤5 chars incl. braces. May be `NULL`. |
| `DisplayOrder` | INT | Sort order of the option within its category/product. |
| `DescriptionId` | INT (FK → `OtherDescription`) | Multilingual description link. |
| `IsFabric` | INT | `0`/absent = normal option; `1` = fabric **type**; `2` = fabric **colour**. |
| `HideByDefault` | INT (0–9) | CAD/visibility flag; values >9 treated as locked (guarded). |
| `EOSLiteDisplayOrder` | INT | Ordering for EOS‑Lite output; CAD path stores it negated. |
| `SLFeatureLength` | INT | SyteLine feature‑code slice length. |
| `SupplierId` | INT (FK → supplier) `UNKNOWN` table name | Optional supplier association (set when name ⊃ "kvadrat"). |

> Additional `[Option]` columns may exist in the DB but are **not referenced** by the maintenance code paths read here → `UNKNOWN`.

### Hardcoded option ids

| Id | Meaning | Source |
|----|---------|--------|
| `8` | Fabric **Type** option | `ProductDescriptions.cs:5449`, `OFDAExport.cs` fabric logic |
| `28` | Fabric **Colour** option | `ProductDescriptions.cs:5449`, `OFDAExport.cs:4520` |

### `PDMOptionDataReport` result columns (as consumed)

`Range2, ProductId, Product2, Option2 (option name), OptDescId, OptionId, OrderCodeFormatKey, OptionValueId, OrderCodeValue2, Status, ParentOptId, ParentOptDescId, ParentOptName, ParentOptValId, ParentOptValDescId, ParentOptValName, ParentOptValCode, ParentOptIsFabric, ParentDisplayOrder, DisplayOrder, EOSLiteDisplayOrder, DisplayOrdinal, TertiaryOption/TertiayOption, IsFabric, optval_name, optvalDescId, ImageFile, ProductCategoryId, PriceBand` (and `IncPrice` in the `WithInc*` variants). Source: `OFDAExport.cs:4480‑4520`, `SytelineExport.cs:4924`.

The **procedure body itself is not in this workspace** → its filtering/join logic is `UNKNOWN` beyond the columns it returns.

### Export DTOs (in‑memory, NOT tables)

**`OptionClass`** (`OptionClass.cs`) — parallel arrays for one option:
`PO` (string permutation/output id), `OptId` (=`[Option].OptionId`, default −1), `OptName`, and `ArrayList`s: `OptValIds`, `OptValNames`, `OptCodes`, `DependPOs`, `SubOptions`, `ParentOptIds`, `IncPrices`. All lists default empty; `OptId=-1` sentinel.

**`OptionGroup`** (`OptionGroup.cs`) — late‑bound (VB) holder: `OptionId` (int), `OrderCode` (ArrayList), `IncPrice` (ArrayList), `Total` (auto‑incremented as order codes are added). Setters mutate via `Conversions`/`RuntimeHelpers` (decompiled VB late binding).

---

## 6. Business Rules

- **BR-OPT-001** — An Option is defined by the `[Option]` table row; its selectable values live in `OptionValue` (FK `OptionValue.OptionId → [Option].OptionId`). The two are always joined via `PDMOptionDataReport`. (`OFDAExport.cs:4544`.)
- **BR-OPT-002** — `IsFabric` classifies an option into three kinds: `1` = fabric type, `2` = fabric colour, anything else = normal. Fabric‑colour options (2) are treated as *sub‑options* of fabric‑type options (1). (`SIFExportThread.cs:CreateOpt`, `OFDAExport.cs:4506`.)
- **BR-OPT-003** — Fabric‑colour rows (`IsFabric = 2`) start a **new option group** when their order code does not start with the current fabric prefix (`text3`), even within the same `OptionId`. (`SIFExportThread.cs` `CreateOpt`, flag `flag2`.)
- **BR-OPT-004** — For fabric‑type rows (`IsFabric = 1`), a synthetic sub‑option reference is built as `<orderCode w/o '#'>_0` right‑padded to 10 chars with `'0'`, and registered in `subOptionValueIds/subOptionRefs`. (`SIFExportThread.cs` `CreateOpt`.)
- **BR-OPT-005** — When an option value has a `ParentOptValId`, the exporter substitutes the parent's sub‑option reference for the PO and, if that reference contains `'_'`, renames the option to `<prefix>_Colors`. (`SIFExportThread.cs` `CreateOpt`.)
- **BR-OPT-006** — The option name `"Fabric type"` is renamed to `"Fabric"` on `.opt` output (`OG=` line). (`SIFExportThread.cs:OutputOpt`.)
- **BR-OPT-007** — Order codes written to `.opt` (`ON=`) have all `'#'` characters stripped. (`SIFExportThread.cs:OutputOpt`.)
- **BR-OPT-008** — An option is only emitted for an item if at least one of its values is both in the catalogue (`_catalogueOptionValues.Contains`) **and** has `Status = 1` (active). (`SIFExportThread.cs:CreateOpt`.)
- **BR-OPT-009** — On SIF import, a new option whose name contains "kvadrat" (case‑insensitive) *and* which is created in a fabric‑type context gets `SupplierId = 2`; otherwise `SupplierId` is omitted. (`SIFImport.cs:9067`.)
- **BR-OPT-010** — In OFDA export, if the option set for an item contains fabric colour (option id 28) but **not** fabric type (option id 8), and the parent fabric‑type value is absent, the parent option/value is back‑filled directly from `[Option]`+`OptionValue`. (`OFDAExport.cs:4520`.)
- **BR-OPT-011** — OFDA also injects a master‑template default value (`OrderCodeValue = '<MT>'`) for the category's option. (`OFDAExport.cs:4560`.)
- **BR-OPT-012** — A new `OrderCodeFormatKey` must be: non‑empty, ≤6 chars trimmed (message says "less than 5"), start with `{` and end with `}`, uppercased, and **not already used** by any attribute or option in the category. Violations show a `MsgBox` and re‑prompt. (`ProductDescriptions.cs:5576‑5586`.)
- **BR-OPT-013** — Changing an option's `OrderCodeFormatKey` cascades: every `ProductRange.OrderCodeFormatString` in the category that embeds the old key token is rewritten (string `Replace`) and each change is audited. (`ProductDescriptions.cs:5588‑5600`.)
- **BR-OPT-014** — `EOSLiteDisplayOrder` and `SLFeatureLength` inputs must be **positive integers** (validated char‑by‑char against `"0123456789"`); non‑numeric input is rejected with a `MsgBox`. (`ProductDescriptions.cs:5480`, `:5510`.)
- **BR-OPT-015** — `HideByDefault` update only applies when the existing value is `≤ 9` (`AND HideByDefault <= 9`), protecting sentinel/locked options. (`CADMaintenance.cs:15859`.)
- **BR-OPT-016** — CAD path stores `EOSLiteDisplayOrder` **negated** (`-1 * num`) and clears it with `0`, whereas the ProductDescriptions path stores the raw positive value — an inconsistency between the two maintenance entry points. (`CADMaintenance.cs:25098` vs `ProductDescriptions.cs:5494`.)
- **BR-OPT-017** — The SyteLine grouping temp table (Q‑OPT‑014) exposes the proc column as `TertiayOption` (misspelled), while OFDA reads `TertiaryOption`; consumers must use whichever spelling the proc actually returns. (`SytelineExport.cs:4924` vs `OFDAExport.cs:4507`.) Actual proc column name = `UNKNOWN`.
- **BR-OPT-018** — On SIF import, a newly created option's key token is appended to the range's `OrderCodeFormatString` only if not already present (`IndexOf(...) == -1`). Existing‑token appends are skipped. (`SIFImport.cs` post‑insert block.)
- **BR-OPT-019** — Option identity after insert is recovered by re‑selecting on the full inserted column set (Name+Category+FormatKey+DisplayOrder+DescriptionId), with `OrderCodeFormatKey IS NULL` substituted when the key is NULL. No `SCOPE_IDENTITY`/`OUTPUT` is used. (`SIFImport.cs:9090`.)
- **BR-OPT-020** — Options are grouped/sorted for export by `OptionId` runs via `SortClasses`, which reorders `optionArray` so all classes sharing an `OptId` are contiguous. (`SIFExportThread.cs:SortClasses`.)
- **BR-OPT-021** — `CheckDependents` propagates dependency PO links between adjacent option classes: an option whose `DependPOs` all point to a single PO (`num2`) is chained to the option whose `PO == num2`, swapping dependency references. Runs while not `terminate`. (`SIFExportThread.cs:CheckDependents`.)
- **BR-OPT-022** — `CheckDuplicate(myopt)` treats two option classes as duplicates iff they share the same `OptId`, the same `DependPOs.Count`, and **every** value id in `myopt.OptValIds` also appears in the candidate's `OptValIds`; the duplicate's PO is reused. (`SIFExportThread.cs:CheckDuplicate`.)
- **BR-OPT-023** — Global de‑duplication (`ProcessGlobal`/`CheckGlobalDuplicate`) additionally requires matching `IncPrices` per value **and** matching "has‑dependency" state (an XOR of `DependPO != -1` flags must be false). Dependent options are matched recursively via `CheckGlobalDepend`/`FindMatch`/`CheckPassMatch`. (`SIFExportThread.cs:1210‑1560`.)
- **BR-OPT-024** — During `CreateDependent`, a dependent option class is created with a **globally incremented** PO (`globalPO++`), and only if `dataTable.Rows.Count > 0` does it recurse into further dependents. (`SIFExportThread.cs:1094‑1200`.)
- **BR-OPT-025** — `IncPrice` of `-1` is treated as "no increment" and written as `O1=0.00`; otherwise rounded to 2 dp with a `.00` suffix appended if no decimal point present. (`SIFExportThread.cs:OutputOpt`.)
- **BR-OPT-026** — When `_catalogueLeadTime == 99`, an `@` prefix is prepended to option‑value descriptions (`OD=@...`) and product descriptions. (`SIFExportThread.cs:OutputOpt`, `RunKeyOpt`.)
- **BR-OPT-027** — Lead‑time output lines `O4`/`O5` (and `P4`/`P5` for products) are always written as `<_catalogueLeadTime>.00`. (`SIFExportThread.cs:OutputOpt`.)
- **BR-OPT-028** — Every catalogue‑affecting option UPDATE writes a `PDMAudit.dbo.Transactions` row stamped with the Windows user, UTC date, and `Global.connectedDB`. (`ProductDescriptions.cs:5595`.)
- **BR-OPT-029** — Fabric‑type vs fabric‑colour option ids are accumulated into `fabricTypeOptionIds` (IsFabric=1) and `fabricColourOptionIds` (IsFabric=2) as the report is read, de‑duplicated by `Contains`. (`OFDAExport.cs:4506‑4514`.)
- **BR-OPT-030** — `Option2` (option display name) is captured from the report; parent option context is carried through `ParentOptId/ParentOptName/ParentOptDescId`. Empty parent string → `ParentOptIds` gets `-1`. (`SIFExportThread.cs:CreateOpt`, `OptionData` fill in `OFDAExport.cs`.)

---

## 7. Hidden Logic

- **HL-OPT-1** — Fabric options are entirely id‑driven: option id `8` = Fabric Type and `28` = Fabric Colour are hardcoded in multiple modules; renaming those options in the DB will not change the code's behaviour but relabelling their ids would break it silently.
- **HL-OPT-2** — There is no first‑class Option maintenance screen; option metadata (`EOSLiteDisplayOrder`, `SLFeatureLength`, `OrderCodeFormatKey`, `HideByDefault`) is only editable through right‑click context menus, so the surface is easy to miss.
- **HL-OPT-3** — The SIF exporter runs a bespoke permutation/de‑duplication engine (`OptionClass` PO chaining) that is invisible from the DB schema; option grouping/order in output files depends on runtime array ordering, not on any stored order.
- **HL-OPT-4** — CAD stores `EOSLiteDisplayOrder` negated (BR‑OPT‑016); a value read back positive in one screen can be the negation of what CAD wrote.
- **HL-OPT-5** — `OptionGroup` uses VB late‑binding setters where `SOrderCode`/`SIncPrice` *append* to internal lists and `SOrderCode` also increments `Total` — assigning a property has a side effect (list growth), not replacement.
- **HL-OPT-6** — The `<MT>` "master template" order code injects a synthetic default option value for a category during OFDA export (BR‑OPT‑011); it is not a real user selection.

---

## 8. UI Behaviour

- Option metadata edits are surfaced as **context‑menu items** in `ProductDescriptions` and `CADMaintenance` grids; the handler branches on `menuItem.Text.IndexOf("…")` substrings (fragile string matching).
- Numeric inputs (`EOSLiteDisplayOrder`, `SLFeatureLength`) use `Interaction.InputBox` and re‑prompt on invalid input with `Interaction.MsgBox`.
- Setting the Order Code Format Key loops on `InputBox` until a valid, unused key is entered or the user cancels (empty).
- The **Item Option Data Report** menu opens a generic `DataQuery` grid bound to the raw proc output (read‑only troubleshooting view).
- No inline grid editing of options; all writes go through modal prompts / context actions, then reload.

---

## 9. Dependencies

- **Stored procedures:** `PDMOptionDataReport`, `PDMOptionDataReportWithIncBase`, `PDMOptionDataReportWithIncList` (bodies not in workspace → filtering logic `UNKNOWN`).
- **Tables:** `[Option]`, `OptionValue`, `DependentOptionValues`, `CatalogueOptionValues`, `ProductRange`, `ProductCategory`, `Attribute`, `OtherDescription`, `PDMAudit.dbo.Transactions`.
- **Infra:** `ConnectionFactory` → `SqlConnection`; `Global.connectedDB`; Windows identity (`Environment.UserName.ToLower()`).
- **Consumers:** `SIFExportThread`, `OFDAExport`, `SytelineExport`, `SytelineCSIExport`, `OCDExport`, `PriceMaintenance`, `SuperProductMaintenance`, `UpdatePricesThread`, `ValidateThread`, `ValidateSIFThread`, `ItemPriceExport`, `ExportThread`.

---

## 10. Risks

- **R-OPT-1 (SQL injection):** All option UPDATE/INSERT and the `PDMOptionDataReport '<item>'` calls are inline string‑concatenated; item names, keys and descriptions are not parameterised.
- **R-OPT-2 (Hardcoded ids 8/28):** Fabric type/colour behaviour breaks silently if these option ids differ in another environment.
- **R-OPT-3 (Identity recovery race):** Post‑insert `SELECT` by column values (BR‑OPT‑019) can return the wrong id if a concurrent insert produces an identical natural key.
- **R-OPT-4 (Negated display order):** BR‑OPT‑016 inconsistency between CAD and ProductDescriptions can corrupt EOS‑Lite ordering.
- **R-OPT-5 (`TertiayOption` misspelling):** BR‑OPT‑017 — a downstream consumer using the other spelling will silently read null/zero.
- **R-OPT-6 (Duplicated SQL):** Q‑OPT‑014 exists twice verbatim in `SytelineExport.cs` (4924 & 5336); edits must be kept in sync.
- **R-OPT-7 (Opaque proc):** Core selection/filtering lives in `PDMOptionDataReport`, which is not in source control here; any migration must reverse‑engineer it from the DB.
- **R-OPT-8 (String‑match menu routing):** Context actions dispatched by `IndexOf` on menu text are brittle to label changes.
- **R-OPT-9 (No transaction scoping):** Multi‑step writes (option insert + range update + audit) are separate commands with no transaction; partial failure leaves inconsistent state.
