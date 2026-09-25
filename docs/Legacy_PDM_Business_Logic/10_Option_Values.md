# 10 — Option Values

**Module prefix:** BR-OVAL
**Primary legacy source:** `OptionData.cs`, `OptionGroup.cs`, `ProductDescriptions.cs`, `AddNewData.cs`, `SIFImport.cs`, `CADMaintenance.cs`, `PriceMaintenance.cs`, `OFDAExport.cs`, `SytelineExport.cs`, `UpdatePricesThread.cs`, `ValidateSIFThread.cs` (stored proc `PDMOptionDataReport*`)
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

An **Option Value** is a single *selectable/assignable value* belonging to an Option — e.g. for the "Fabric Colour" option, values like "Black", "Ivory", a specific fabric SKU. It is persisted in the SQL table `OptionValue` (FK `OptionId → [Option].OptionId`).

Option values carry the bulk of maintainable product configuration data: order code, status (active/obsolete/hold/URL), CAD material/suffix, image file, supplier, composition/application/standards, display ordinal, and (via `ItemOptionValues`) per‑item incremental prices. Value‑to‑value relationships (dependencies) are stored in `DependentOptionValues`, and catalogue membership in `CatalogueOptionValues`.

> **Clarification (per task):**
> - **Option** (module 09) = the *definition/container* (`[Option]` table).
> - **Option Value** (this module) = an *assignable value* under an option (`OptionValue` table).
> - `OptionData` and `OptionGroup` are **in‑memory export DTOs**, NOT database tables. `OptionData` is a bulk column‑array holder filled from `PDMOptionDataReport`; `OptionGroup` is a permutation holder.

---

## 2. Entry Points

| # | Trigger | Location | Kind |
|---|---------|----------|------|
| E1 | Product Descriptions context menu — **status** `(URL)`/`(ACT)`/`(OBS)`/`(HLD)` | `ProductDescriptions.cs:5787‑5825` | Value maintenance (UPDATE Status) |
| E2 | Product Descriptions — **Exclude from Fabric Index** toggle | `ProductDescriptions.cs:5460` | Value maintenance (UPDATE) |
| E3 | Product Descriptions — **Composition / Application / Standards** edit | `ProductDescriptions.cs:9201`, `:6014` | Value maintenance (UPDATE) |
| E4 | Product Descriptions — **Supplier / SupplierCode / ImageFile** edit | `ProductDescriptions.cs:9015`, `:9139`, `:9159` | Value maintenance (UPDATE) |
| E5 | Product Descriptions — remove value from catalogue | `ProductDescriptions.cs:5780` (`DELETE FROM CatalogueOptionValues`) | Catalogue membership |
| E6 | CAD Maintenance — **CADSuffix / CADMaterial / ModelSpecific / ChromaticSequence / ImageFile** | `CADMaintenance.cs:13745`, `:15183`, `:16369`, `:16842`, `:17343` | Value maintenance (UPDATE) |
| E7 | Price Maintenance — **ExcludeFromValidation**, `ItemOptionValues` inc price | `PriceMaintenance.cs:8022`, `:6385` | Value/price maintenance |
| E8 | Add New Data — bulk add fabric/option values | `AddNewData.cs:997`, `:1387` (`INSERT INTO OptionValue`) | Value creation |
| E9 | SIF Import — auto‑create values + increments | `SIFImport.cs:9193`, `:9270`, `:9379` | Value creation / status / inc price |
| E10 | Validate SIF — create fabric colour value (opt 28) | `ValidateSIFThread.cs:184` | Value creation |
| E11 | Update Prices thread — `ItemOptionValues.IncrementalPrice2` | `UpdatePricesThread.cs:447` | Inc price maintenance |
| E12 | Export/read consumers | `OFDAExport.cs:4399‑4620`, `SytelineExport.cs`, `PriceMaintenance.cs` | Read via `PDMOptionDataReport*` |

---

## 3. Call Hierarchy

Status maintenance (E1):

```
ProductDescriptions (Form)
  └─ contextMenu_Click "(ACT)/(OBS)/(HLD)/(URL)" (Event)
       └─ inline handler (Controller)
            └─ ConnectionFactory → SqlConnection (Service/Repository)
                 └─ SQL: UPDATE OptionValue SET Status = <n> WHERE OptionValueId = <ctx>
                      └─ PDMAudit.dbo.Transactions insert (Model/audit)
                           └─ grid reload (UI)
```

Value creation (E8/E9):

```
AddNewData / SIFImport (Form/Thread)
  └─ add/import loop (Event)
       └─ createOtherDescription + getNextDisplayOrder (Service)
            └─ SQL: INSERT INTO OtherDescription ; INSERT INTO OptionValue ; SELECT OptionValueId
                 └─ INSERT DependentOptionValues / CatalogueOptionValues (relationships)
                      └─ updaterequired = true → reload (UI)
```

Read/export (E12):

```
OFDAExport / SytelineExport (Thread)
  └─ EXEC PDMOptionDataReport '<item>'   (Repository/SQL)
       └─ fill OptionData column arrays (Model DTO)
            └─ getCADSuffix / fabric flag accumulation (business logic)
                 └─ write export rows (UI/output)
```

---

## 4. SQL Analysis

> All queries are **inline string‑concatenated** (injection‑prone; foundation fact).

### Q-OVAL-001 — Read option values (via option report)
`ProductDescriptions.cs:6624`, `OFDAExport.cs:4433`, etc.
```sql
PDMOptionDataReport '<item>'
```
**Why:** Returns each option value row (`OptionValueId, optval_name, OrderCodeValue2, Status, DisplayOrdinal, IsFabric, ImageFile, PriceBand, ProductCategoryId, optvalDescId`, plus parent‑value columns). Primary read for value display and export.

### Q-OVAL-002 — Priced value report (increments)
`SIFExportThread.cs:713`, `ItemPriceExport.cs:287`, `ValidateSIFThread.cs:730`
```sql
EXEC PDMOptionDataReportWithIncList '<item>', <siteId>, '<currency>', '<effectiveDate>'
```
**Why:** As Q‑OVAL‑001 plus an `IncPrice` per value for the requested site/currency/date, used to emit priced option values.

### Q-OVAL-003 — Set value status
`ProductDescriptions.cs:5791` (and `5800/5809/5818`)
```sql
UPDATE OptionValue SET Status = 0 WHERE OptionValueId = <ctx>   -- URL
UPDATE OptionValue SET Status = 1 WHERE OptionValueId = <ctx>   -- ACT (active)
UPDATE OptionValue SET Status = 2 WHERE OptionValueId = <ctx>   -- OBS (obsolete)
UPDATE OptionValue SET Status = 3 WHERE OptionValueId = <ctx>   -- HLD (hold)
```
**Why:** The context menu labels `(URL)/(ACT)/(OBS)/(HLD)` map 1:1 to `Status` values `0/1/2/3`. Only active (`1`) values are exported (BR‑OVAL‑003).

### Q-OVAL-004 — Toggle exclude‑from‑fabric‑index
`ProductDescriptions.cs:5460`
```sql
UPDATE OptionValue SET ExcludeFromFabricIndex =
  CASE WHEN ExcludeFromFabricIndex = 1 THEN 0 ELSE 1 END
WHERE OptionValueId = <ctx>
```
**Why:** Boolean flip (no separate on/off actions) controlling whether the value appears in the fabric index output.

### Q-OVAL-005 — Composition / Application / Standards
`ProductDescriptions.cs:9201`, and clear at `:6014`
```sql
UPDATE OptionValue SET Composition = '<c>', Application = '<a>', Standards = '<s>'
WHERE OptionValueId = <id>

UPDATE OptionValue SET Composition = NULL WHERE OptionValueId = <id>   -- clear
```
**Why:** Stores fabric technical metadata; a blank composition writes `NULL` (BR‑OVAL‑012).

### Q-OVAL-006 — Supplier / SupplierCode / ImageFile
`ProductDescriptions.cs:9015`, `:9139`, `:9159`, `:11348`
```sql
UPDATE OptionValue SET SupplierId  = <supplierId> WHERE OptionValueId = <id>
UPDATE OptionValue SET SupplierCode = '<code>'    WHERE OptionValueId = <id>
UPDATE OptionValue SET ImageFile   = '<path>'     WHERE OptionValueId = <id>
```
**Why:** Associates a value with a supplier and product image.

### Q-OVAL-007 — Bulk image path rewrites
`CADMaintenance.cs:16842`, `:17132`, `ProductDescriptions.cs:11067`
```sql
UPDATE OptionValue SET ImageFile = REPLACE(ImageFile, 'Images\Products\<old>', 'Images\Products\<new>')
WHERE ImageFile LIKE '%<old>%'
```
**Why:** Re‑points image references when product folders are renamed; `LIKE` scope means it touches every matching value.

### Q-OVAL-008 — CAD attributes
`CADMaintenance.cs:13745`, `:15183`, `:16369`, `:17343`
```sql
UPDATE OptionValue SET ModelSpecific     = '<v>' WHERE OptionValueId = <id>
UPDATE OptionValue SET CADSuffix         = '<v>' WHERE OptionValueId = <id>   -- or NULL to clear
UPDATE OptionValue SET ChromaticSequence = <v>   WHERE OptionValueId = <id>
UPDATE OptionValue SET CADMaterial       = '<v>' WHERE OptionValueId = <id>
```
**Why:** CAD‑specific per‑value metadata used by geometry/material generation.

### Q-OVAL-009 — Exclude from validation (option‑wide)
`PriceMaintenance.cs:8022`
```sql
UPDATE OptionValue SET ExcludeFromValidation = <0|1> WHERE OptionId = <optionId>
```
**Why:** Note the filter is `OptionId` (not `OptionValueId`) — sets the flag on **all values** of an option at once (BR‑OVAL‑013).

### Q-OVAL-010 — Create option value (Add New Data, fabric)
`AddNewData.cs:997` (existence check `:975`, description insert `:995`)
```sql
SELECT OptionValueId FROM OptionValue WHERE OrderCodeValue = '<code>' AND OptionId = <optId>

SELECT TOP 1 DescriptionId FROM OtherDescription ORDER BY DescriptionId DESC
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable)
  VALUES (<descId>, 1, '<name>', 'OptionValue')

INSERT INTO OptionValue (OptionId, Name, OrderCodeValue, DescriptionId, Status, ImageFile, CADMaterial
                         [, SupplierCode])
VALUES (<optId>, '<name>', '<code>', <descId>, 1,
        'Images\Options\Fabrics\[Knoll\]<code>.jpg', 'S_T150_<code>.gm' [, '<supplierCode>'])
```
**Why:** Idempotent create — only inserts if the (`OrderCodeValue`,`OptionId`) pair does not already exist. New values default `Status = 1` (active), get a synthesised image path and CAD material `S_T150_<code>.gm`.

### Q-OVAL-011 — Link new value: dependency + catalogue
`AddNewData.cs:1020`, `:1023`
```sql
INSERT INTO DependentOptionValues (OptionValueId, AdditionalOptionValueId) VALUES (<parentId>, <newId>)
INSERT INTO CatalogueOptionValues  (CatalogueId, OptionValueId)            VALUES (<catId>, <newId>)
```
**Why:** Registers the new colour as dependent on its parent fabric value and makes it visible in the current catalogue.

### Q-OVAL-012 — Create option value (SIF import)
`SIFImport.cs:9193` (existence `:9166`, next display order `:9190`)
```sql
SELECT OptionValueId, Status FROM OptionValue WHERE OrderCodeValue = <code|NULL> AND OptionId = <optId>

INSERT INTO OptionValue (Name, OptionId, DisplayOrdinal, DescriptionId
                         [, ImageFile][, OrderCodeValue][, SupplierCode])
VALUES ('<name>', <optId>, <nextDisplayOrdinal>, <descId> [, '<img>'][, '<code>'][, '<suppCode>'])
```
**Why:** Import‑time create. Columns are conditionally included: `ImageFile` only if provided, `OrderCodeValue` only if non‑NULL, `SupplierCode` only if a parenthesised code was parsed from the name (BR‑OVAL‑016).

### Q-OVAL-013 — Reactivate existing value on import
`SIFImport.cs:9270`
```sql
UPDATE OptionValue SET Status = 1 WHERE OptionValueId = <existingId>
```
**Why:** If a value already exists but is inactive, import re‑activates it rather than duplicating.

### Q-OVAL-014 — Per‑item incremental price upsert
`SIFImport.cs:9379`, `UpdatePricesThread.cs:447`, `ValidateSIFThread.cs:864`, `PriceMaintenance.cs:6385`
```sql
UPDATE ItemOptionValues SET <priceCol> = <inc>
  WHERE ItemId = <itemId> AND OptionValueId = <ovId>
-- else --
INSERT INTO ItemOptionValues (ItemId, OptionValueId, <priceCol>)
  VALUES (<itemId>, <ovId>, <inc>)
```
**Why:** Manual upsert (SELECT‑then‑UPDATE‑or‑INSERT) of a value's incremental price for a specific item. Columns seen: `IncrementalPrice2`, and a dynamic `<text16>` price column in `SIFImport`.

### Q-OVAL-015 — Create fabric‑colour value under option 28 (Validate SIF)
`ValidateSIFThread.cs:184`
```sql
INSERT INTO OptionValue (OptionId, Name, OrderCodeValue, DescriptionId)
VALUES (28, '<name>', '<code>', <descId>)
```
**Why:** Auto‑creates a missing fabric‑colour value under the **hardcoded** fabric‑colour option id `28` during SIF validation (BR‑OVAL‑017).

### Q-OVAL-016 — Remove value from catalogue
`ProductDescriptions.cs:5780`
```sql
DELETE FROM CatalogueOptionValues WHERE CatalogueId = <catId> AND OptionValueId = <ctx>
```
**Why:** Removes catalogue visibility of a value without deleting the value; audited via `AuditReport.AuditTransaction("COVUpdates", …, "REMOVED", …)`.

### Q-OVAL-017 — Dependent‑value resolution (export)
`SIFExportThread.cs:1149` (see also Q‑OPT‑013)
```sql
SELECT DISTINCT DependentOptionValues.AdditionalOptionValueId, OptionValue.OptionId
FROM DependentOptionValues
INNER JOIN OptionValue ON DependentOptionValues.OptionValueId = OptionValue.OptionValueId
WHERE AdditionalOptionValueId IN (<ids>)
  AND AdditionalOptionValueId IN (SELECT OptionValueId FROM CatalogueOptionValues WHERE CatalogueId = <catId>)
  AND OptionId = <optId>
ORDER BY OptionId, AdditionalOptionValueId
```
**Why:** Finds catalogue‑scoped additional values that depend on a parent value.

### Q-OVAL-018 — Direct value back‑fill (OFDA fabric fallback)
`OFDAExport.cs:4544`
```sql
SELECT DISTINCT opt.OptionId, opt.DescriptionId AS optDescId, opt.DisplayOrder, opt.IsFabric,
  optval.OptionValueId, optval.DescriptionId AS optvalDescId, optval.DisplayOrdinal,
  optval.OrderCodeValue AS OrderCodeValue2, optval.ImageFile, optval.CADMaterial, optval.Status,
  <catId> AS ProductCategoryId, NULL AS ParentOptValId
FROM OptionValue optval WITH (NOLOCK)
INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId
WHERE optval.OptionValueId = <parentOptValId>
ORDER BY opt.DisplayOrder, optval.DisplayOrdinal
```
**Why:** Reads a single value directly (bypassing the proc) to back‑fill a missing parent fabric value (BR‑OVAL‑018; see BR‑OPT‑010).

---

## 5. Data Model

### Table `OptionValue`

| Column | Type (observed) | Meaning |
|--------|-----------------|---------|
| `OptionValueId` | INT (PK) | Identity of the value. |
| `OptionId` | INT (FK → `[Option]`) | Owning option. |
| `Name` | varchar | Display name (camel‑cased / US→UK converted on insert). |
| `OrderCodeValue` | varchar(20) | Order code fragment; may end with `#`; `NULL` allowed. Aliased `OrderCodeValue2` in reports. |
| `DescriptionId` | INT (FK → `OtherDescription`) | Multilingual description. |
| `Status` | INT | `0` = URL, `1` = ACT (active), `2` = OBS (obsolete), `3` = HLD (hold). |
| `ImageFile` | varchar(255) | Relative image path (e.g. `Images\Options\Fabrics\<code>.jpg`). |
| `CADMaterial` | varchar | CAD material file (e.g. `S_T150_<code>.gm`). |
| `CADSuffix` | varchar | CAD geometry suffix; nullable. |
| `ModelSpecific` | varchar | CAD model‑specific flag/value. |
| `ChromaticSequence` | INT | CAD colour ordering. |
| `ExcludeFromValidation` | INT (0/1) | Excludes value from SIF validation. |
| `ExcludeFromFabricIndex` | INT (0/1) | Excludes value from fabric index output. |
| `Composition` | varchar | Fabric composition text; nullable. |
| `Application` | varchar | Fabric application text. |
| `Standards` | varchar | Fabric standards text. |
| `SupplierId` | INT (FK → supplier `UNKNOWN`) | Supplier association. |
| `SupplierCode` | varchar | Supplier's own code. |
| `DisplayOrdinal` | BIGINT | Sort order within the option (report casts to `long`). |

> Other `OptionValue` columns may exist but are **not referenced** in the paths read → `UNKNOWN`.

### Relationship tables

| Table | Columns | PK/keys | Meaning |
|-------|---------|---------|---------|
| `DependentOptionValues` | `OptionValueId`, `AdditionalOptionValueId` | (both FK → `OptionValue`) | `AdditionalOptionValueId` becomes available (dependent) when `OptionValueId` is selected. |
| `CatalogueOptionValues` | `CatalogueId`, `OptionValueId` | composite | Catalogue membership / visibility of a value. |
| `ItemOptionValues` | `ItemId`, `OptionValueId`, `IncrementalPrice2` (and dynamic price cols) | composite | Per‑item incremental price for a value. |

### Status enumeration (verified)

| `Status` | Menu label | Meaning |
|----------|-----------|---------|
| `0` | `(URL)` | URL / non‑orderable marker |
| `1` | `(ACT)` | Active — the only status exported |
| `2` | `(OBS)` | Obsolete |
| `3` | `(HLD)` | Hold |

Source: `ProductDescriptions.cs:5787‑5825`.

### DTOs (in‑memory, NOT tables)

**`OptionData`** (`OptionData.cs`) — 30+ parallel `ArrayList`s filled row‑for‑row from `PDMOptionDataReport`:
`productIdList, productList, itemList, rangeList, productCategoryIdList, optIdList, optDescIdList, optNameList, ocfkList, optDisplayOrderList, optvalIdList, optvalDescIdList, optvalNameList, optvalCodeList, optvalStatusList, optvalDisplayOrdinalList, parentOptIdList, parentOptDescIdList, parentOptNameList, parentOptValIdList, parentOptValDescIdList, parentOptValNameList, parentOptValCodeList, parentOptIsFabricList, parentOptDisplayOrderList, EOSLiteDisplayOrderList, tertiaryOptionList, isFabricList, imageFileList, priceBandList, incPriceList, componentItemList, componentQtyList`. All default empty. Index alignment across lists is assumed (no per‑row object).

**`OptionGroup`** (`OptionGroup.cs`) — permutation holder: `OptionId`, `OrderCode` (ArrayList), `IncPrice` (ArrayList), `Total` (auto‑incremented). See BR‑OPT documentation for late‑binding behaviour.

---

## 6. Business Rules

- **BR-OVAL-001** — An OptionValue belongs to exactly one Option via `OptionId`; values are read for an item through `PDMOptionDataReport` and rendered under their parent option. (`OFDAExport.cs:4480`.)
- **BR-OVAL-002** — `Status` is a 4‑state enum: `0=URL`, `1=ACT`, `2=OBS`, `3=HLD`, set from context‑menu labels `(URL)/(ACT)/(OBS)/(HLD)`. (`ProductDescriptions.cs:5787‑5825`.)
- **BR-OVAL-003** — Only values with `Status = 1` (active) **and** present in `_catalogueOptionValues` are exported to `.opt`. Non‑active/non‑catalogue values are skipped. (`SIFExportThread.cs:CreateOpt`.)
- **BR-OVAL-004** — New option values default to `Status = 1` (active) on creation. (`AddNewData.cs:997`, `SIFImport.cs`.)
- **BR-OVAL-005** — Value creation is **idempotent** on the natural key (`OrderCodeValue` + `OptionId`): existing rows are reused (and only their existence counted), never duplicated. (`AddNewData.cs:975`, `SIFImport.cs:9166`.)
- **BR-OVAL-006** — On creation, a matching `OtherDescription` row is inserted first with `RelatedTable = 'OptionValue'`, `LanguageId = 1`, and `DescriptionId` = current max + 1; the value then references it. (`AddNewData.cs:988‑996`.)
- **BR-OVAL-007** — For fabric values in Add New Data, the image path is `Images\Options\Fabrics\<code>.jpg`, except for option ids `8513`, `8525`, `8625` (Knoll) which use `Images\Options\Fabrics\Knoll\<code>.jpg`. (`AddNewData.cs:1006`.)
- **BR-OVAL-008** — For fabric values in Add New Data, `CADMaterial` is synthesised as `S_T150_<code>.gm`. (`AddNewData.cs:1008`.)
- **BR-OVAL-009** — `OrderCodeValue` may carry a trailing `#`; on `.opt` export and elsewhere the `#` is stripped. Fabric‑type codes are stored **with** `#` appended when they don't already end in `#`. (`AddNewData.cs` code build, `SIFExportThread.cs:OutputOpt`.)
- **BR-OVAL-010** — `OrderCodeValue` may embed a `{…}` format token which is stripped out (substring removal) before storing the code. (`SIFImport.cs:9150`.)
- **BR-OVAL-011** — `ExcludeFromFabricIndex` is a toggle (`CASE WHEN =1 THEN 0 ELSE 1`), not an explicit set. (`ProductDescriptions.cs:5460`.)
- **BR-OVAL-012** — Clearing composition writes `NULL` (not empty string); a non‑blank edit writes the three fabric fields (Composition/Application/Standards) together. (`ProductDescriptions.cs:6014`, `:9201`.)
- **BR-OVAL-013** — `ExcludeFromValidation` is set by `OptionId` (affects **all** values of the option), unlike the other per‑value flags keyed by `OptionValueId`. (`PriceMaintenance.cs:8022`.)
- **BR-OVAL-014** — Incremental prices are stored per (`ItemId`,`OptionValueId`) in `ItemOptionValues` via manual upsert (SELECT → UPDATE existing else INSERT). No unique‑constraint‑based upsert is used. (`SIFImport.cs:9379`, `UpdatePricesThread.cs:447`.)
- **BR-OVAL-015** — An `IncPrice` of `-1` (or DBNull) is interpreted as "no increment"; `GetIncPrice` returns `-1` when the value isn't found or the increment table is empty. (`SIFExportThread.cs:GetIncPrice`.)
- **BR-OVAL-016** — On SIF import, `OptionValue` INSERT columns are conditionally built: `ImageFile` only if a filename is supplied, `OrderCodeValue` only if non‑NULL, `SupplierCode` only if a `(…)`‑parenthesised code ≤10 chars with no space is parsed from the name. (`SIFImport.cs:9160‑9200`.)
- **BR-OVAL-017** — Fabric‑colour values are created under the **hardcoded** option id `28`; fabric‑type values under id `8`. (`ValidateSIFThread.cs:184`, `OFDAExport.cs`.)
- **BR-OVAL-018** — If a fabric‑colour value (option 28) is present but its parent fabric‑type value is missing from the report, the parent value is read directly from `OptionValue`+`[Option]` and **inserted at the front** (`Insert(0, …)`) of the `OptionData` lists so it precedes its children. (`OFDAExport.cs:4520‑4600`.)
- **BR-OVAL-019** — OFDA also appends a synthetic master‑template value (`OrderCodeValue = '<MT>'`) for the category to `OptionData`. (`OFDAExport.cs:4560`.)
- **BR-OVAL-020** — Removing a value from a catalogue is a `DELETE` on `CatalogueOptionValues` only; the `OptionValue` row is preserved and the removal is audited as a `COVUpdates` "REMOVED" transaction. (`ProductDescriptions.cs:5780`.)
- **BR-OVAL-021** — Bulk `ImageFile` `REPLACE` updates use `LIKE '%<old>%'`, so they affect **every** value whose path matches, not a single row. (`CADMaintenance.cs:16842`, `ProductDescriptions.cs:11067`.)
- **BR-OVAL-022** — `CADSuffix` is set to `NULL` when the supplied suffix is empty, otherwise to the quoted value. (`CADMaintenance.cs:15665`.)
- **BR-OVAL-023** — Fabric‑colour value names are augmented with a supplier code (lowercased name + " " + code) during SIF export when the value's name is contained in its parent's name and `IsFabric = 2`. (`SIFExportThread.cs:CreateOpt`.)
- **BR-OVAL-024** — `DisplayOrdinal` for a new value is the next ordinal from `getNextDisplayOrder(optionId, "OptionValue")`; `[Option].DisplayOrder` for a new option likewise from `getNextDisplayOrder(categoryId, "[Option]")`. (`SIFImport.cs:9190`.)
- **BR-OVAL-025** — `IsFabric` on the value row drives sub‑option handling: `1` registers a sub‑option ref, `2` strips the fabric prefix from the code; neither adds an empty `SubOptions` entry. (`SIFExportThread.cs:CreateOpt`.)
- **BR-OVAL-026** — When option id `28` values exist without id `8` (`optIdList.Contains(28) & !optIdList.Contains(8)`) and the parent value isn't already in `optvalIdList`, back‑fill (BR‑OVAL‑018) is triggered. (`OFDAExport.cs:4521`.)
- **BR-OVAL-027** — Every catalogue‑affecting value UPDATE is stamped in `PDMAudit.dbo.Transactions` (Windows user, UTC, `Global.connectedDB`) and status changes additionally log the previous/next status label. (`ProductDescriptions.cs:5826`.)
- **BR-OVAL-028** — Import re‑activation: an existing value found during import has `Status` forced to `1`, ensuring re‑imported values become active. (`SIFImport.cs:9270`.)
- **BR-OVAL-029** — A new dependent (colour) value is always linked to both its parent (`DependentOptionValues`) and the active catalogue (`CatalogueOptionValues`) immediately after creation. (`AddNewData.cs:1020‑1023`.)
- **BR-OVAL-030** — Value names are normalised on insert: `camelCase`, `convertUSEnglishToEnglish`, apostrophes removed/escaped, carriage returns removed. (`SIFImport.cs:9188`, `AddNewData.cs`.)

---

## 7. Hidden Logic

- **HL-OVAL-1** — The `OptionData` DTO relies on **positional alignment** of ~30 separate `ArrayList`s; a single mismatched `Add`/`Insert` corrupts every downstream value silently. Back‑fill uses `Insert(0,…)` on all lists to keep alignment (BR‑OVAL‑018).
- **HL-OVAL-2** — Status semantics are encoded only in menu labels (`(ACT)` etc.), not in the schema; the numeric `Status` meaning is invisible without the UI code.
- **HL-OVAL-3** — Image path and CAD material are *synthesised from the order code* on insert (BR‑OVAL‑007/008), so files must be named to match or images/materials silently 404.
- **HL-OVAL-4** — `ExcludeFromValidation` keyed by `OptionId` (BR‑OVAL‑013) is an easy foot‑gun: an edit intended for one value flips the flag for the whole option.
- **HL-OVAL-5** — Trailing `#` on `OrderCodeValue` is significant (fabric‑type marker) and is added/stripped in several places; its presence changes grouping and export.
- **HL-OVAL-6** — `ItemOptionValues` increments are stored per item, so the same value can have different prices per item; there is no single "value price".
- **HL-OVAL-7** — Hardcoded Knoll option ids `8513/8525/8625` change the image folder (BR‑OVAL‑007) — an undocumented supplier special‑case.

---

## 8. UI Behaviour

- Value maintenance is entirely via **context‑menu actions** on the descriptions grid (`ProductDescriptions`) and CAD grids (`CADMaintenance`); handlers branch on `menuItem.Text.IndexOf(...)`.
- Status changes `(URL)/(ACT)/(OBS)/(HLD)` are immediate single‑click UPDATEs followed by a grid reload and audit.
- Composition/Application/Standards edits use text boxes; supplier/image use selectors.
- Add New Data presents a grid‑driven bulk‑add of values (fabrics), inserting descriptions + values + catalogue/dependency links in one pass.
- No direct delete of an `OptionValue` row from the UI was observed — removal is catalogue‑scoped (`CatalogueOptionValues` delete) only.

---

## 9. Dependencies

- **Stored procedures:** `PDMOptionDataReport`, `PDMOptionDataReportWithIncBase`, `PDMOptionDataReportWithIncList` (bodies not in workspace → `UNKNOWN`).
- **Tables:** `OptionValue`, `[Option]`, `DependentOptionValues`, `CatalogueOptionValues`, `ItemOptionValues`, `OtherDescription`, `ProductRange`, `PDMAudit.dbo.Transactions`.
- **Helpers:** `createOtherDescription`, `getNextDisplayOrder`, `camelCase`, `convertUSEnglishToEnglish`, `parseOrderCodeFormatKey`, `getCADSuffix`, `GetIncPrice`, `AuditReport.AuditTransaction`.
- **Infra:** `ConnectionFactory` → `SqlConnection`; `Global.connectedDB`; Windows identity.
- **Consumers:** `OFDAExport`, `SytelineExport`, `SIFExportThread`, `SIFImport`, `ValidateSIFThread`, `UpdatePricesThread`, `PriceMaintenance`, `CADMaintenance`, `ProductDescriptions`, `OCDExport`.

---

## 10. Risks

- **R-OVAL-1 (SQL injection):** All value INSERT/UPDATE/DELETE and proc calls are inline‑concatenated; names, codes, composition text and image paths are unescaped user data.
- **R-OVAL-2 (Positional DTO fragility):** `OptionData`'s 30 parallel lists (HL‑OVAL‑1) have no structural guarantee of alignment.
- **R-OVAL-3 (Whole‑option flag):** `ExcludeFromValidation` by `OptionId` (BR‑OVAL‑013) can silently affect unintended values.
- **R-OVAL-4 (Broad LIKE updates):** Image `REPLACE … LIKE '%…%'` (BR‑OVAL‑021) can touch far more rows than intended.
- **R-OVAL-5 (Non‑atomic upsert):** `ItemOptionValues` SELECT‑then‑write (BR‑OVAL‑014) can double‑insert under concurrency (no unique constraint enforcement in code).
- **R-OVAL-6 (Hardcoded ids):** Fabric option ids `8`/`28` and Knoll ids `8513/8525/8625` are environment‑specific magic numbers.
- **R-OVAL-7 (Synthesised paths):** Image/CAD file names derived from order codes (BR‑OVAL‑007/008) break if asset naming conventions change.
- **R-OVAL-8 (Opaque proc):** Value filtering/pricing logic largely lives in `PDMOptionDataReport*`, absent from source here.
- **R-OVAL-9 (Identity recovery):** New value id is recovered by re‑`SELECT` on natural key, racy under concurrent inserts (as with options).
- **R-OVAL-10 (Column‑name inconsistency):** Report exposes `TertiayOption`/`TertiaryOption` inconsistently (see BR‑OPT‑017); value consumers relying on the wrong spelling read null.
