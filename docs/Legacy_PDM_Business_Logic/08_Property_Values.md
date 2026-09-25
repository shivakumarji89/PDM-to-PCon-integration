# 08 — Property Values (OCD Property / PropertyClass / PropertyValue Export DTOs)

**Module prefix:** BR-PVAL
**Primary legacy source:** `ocdProperty.cs`, `ocdPropertyClass.cs`, `ocdPropertyValue.cs` (OCD export DTOs). Build and serialization logic in `OCDExport.cs` (the *only* constructor/consumer). Descriptive text via `OtherDescription`; value source via the `PDMOptionDataReport` stored procedure and `OptionValue`/`Attribute` tables.
**Status:** Verified from source unless marked `UNKNOWN`.

> **Are `ocd*` classes table-backed or DTOs?** They are **pure export DTOs (serialization holders)**. Each class:
> - has only `internal string` fields plus a public `fileName`,
> - is constructed exclusively inside `OCDExport.cs`,
> - performs **no** database access and **no** validation,
> - exposes `getAllProperties()` which returns an `ArrayList` of its fields in a fixed order (the CSV column order), and
> - sets `fileName` to the target OCD CSV table name.
>
> There is **no** `ocd_property` / `ocd_propertyclass` / `ocd_propertyvalue` **database table** — those are output **CSV files** in the EasternGraphics OCD interface format. The DB-side "property values" are actually rows in `AttributeValue` / `OptionValue`, transformed here into OCD property structures.

---

## 1. Purpose

These three DTOs model the EasternGraphics **OCD (Order and Configuration Data)** property structures emitted by the PDM→OFML/OCD exporter:

- **`ocdPropertyClass`** → `ocd_propertyclass.csv` — declares a *property class* (a named group of properties) attached to an article.
- **`ocdProperty`** → `ocd_property.csv` — declares a *property* (a configurable characteristic) within a property class, with type/length/obligation/restriction metadata.
- **`ocdPropertyValue`** → `ocd_propertyvalue.csv` — declares an allowed *value* of a property, with a comparison operator and value bounds (`opFrom`/`valueFrom`/`opTo`/`valueTo`).

`OCDExport.cs` reads the PDM configuration model (options, option values, attributes) and materializes it into these DTO collections, which are then serialized to CSV alongside the other OCD tables (`ocd_version`, `ocd_article`, `ocd_relation`, etc.). This is a **Herman Miller-specific** export: it is heavily branched by hardcoded article/series prefixes.

---

## 2. Entry Points

- **Definition:** `ocdProperty` (`ocdProperty.cs:5`), `ocdPropertyClass` (`ocdPropertyClass.cs:5`), `ocdPropertyValue` (`ocdPropertyValue.cs:5`). Each has one `internal` constructor and one public `getAllProperties()`.
- **Construction (the only call sites, all in `OCDExport.cs`):**
  - `new ocdPropertyClass(...)` — `OCDExport.cs:1973`, `2372`, `2411`.
  - `new ocdProperty(...)` — `OCDExport.cs:1984`, `2051`, `2378`, `2385`, `2415`.
  - `new ocdPropertyValue(...)` — `OCDExport.cs:2126`, `2397`, `2421`.
- **Aggregation:** `arrayList13` (property classes), `arrayList11` (properties), `arrayList12` (property values) are declared at `OCDExport.cs:923-925` and added to `OCDTables` at `OCDExport.cs:3058-3060`.
- **Serialization:** the OCD writer loop (`OCDExport.cs:399-618`) iterates `OCDTables`, and for each DTO calls `getAllProperties()`, joins the fields with `;`, and writes one CSV line to `<fileName>.csv`.
- **Export trigger:** launched from the OCD export flow (`OCDExport` form / `ExportThread`); see 21_OCD / 22_Export for the outer trigger. The property build sits inside the per-article loop driven by the `PDMOptionDataReport` stored procedure.

---

## 3. Call Hierarchy

```
OCDExport (Export Form / Thread)                                    [Form]
  └─ export run (per group/catalogue)                              [Event]
       └─ per-article build loop                                   [Controller]
            ├─ SqlCommand "PDMOptionDataReport" (stored proc)      [Repository/SQL  Q-PVAL-001]
            │     reads: OptionId, OptionValueId, Option2, optval_name,
            │            OrderCodeValue2, IsFabric, Status, ProductRangeId,
            │            ProductCategoryId, Item, attr_name, atval_name
            ├─ OtherDescription lookups (DE=5 / NL=9)              [SQL  Q-PVAL-002/004]
            ├─ [option].SLFeatureLength lookup                      [SQL  Q-PVAL-003]
            ├─ build property class → new ocdPropertyClass(...)     [Model/DTO  arrayList13]
            ├─ build property      → new ocdProperty(...)           [Model/DTO  arrayList11]
            ├─ build value         → new ocdPropertyValue(...)      [Model/DTO  arrayList12]
            ├─ synthetic LEADTIME class/property/values             [Model/DTO]
            └─ post-process ocdPropertyValue.relObjID (_FS/_AS)     [Controller  OCDExport.cs:2886-2985]
       └─ OCDTables.Add(arrayList13/11/12)                          (OCDExport.cs:3058-3060)
            └─ OCD writer loop → getAllProperties() → ";"-joined CSV row  (OCDExport.cs:589-608)
                 └─ files ocd_propertyclass.csv / ocd_property.csv / ocd_propertyvalue.csv
```
The DTOs themselves are leaf models: no events, services, or repositories of their own.

---

## 4. SQL Analysis

> The property/propertyclass/propertyvalue build is driven primarily by a **stored procedure**, with inline concatenated description lookups. Concatenated queries interpolate reader values directly (injection risk is lower here because inputs are DB-sourced IDs, not free user text, but still string-built).

**Q-PVAL-001** — Option data driver (`OCDExport.cs`, called repeatedly, e.g. lines ~1893, 1912, 1935)
```sql
EXEC PDMOptionDataReport @cataloguedesc = <text3>
```
*Why:* the master reader for building property classes/properties/values. It is executed multiple times over the same catalogue: (1) to count distinct non-fabric options (`num11`) and max `IsFabric` (`num12`), and (2) to iterate rows and emit DTOs. Key columns consumed: `OptionId`, `OptionValueId`, `Option2` (option name), `optval_name` (value name), `OrderCodeValue2` (order code, used as `valueFrom`), `IsFabric`, `Status`, `ProductRangeId`, `ProductCategoryId`, `Item`. → BR-PVAL-001, BR-PVAL-002, BR-PVAL-010, BR-PVAL-011.

**Q-PVAL-002** — Property (option) DE/NL short descriptions (`OCDExport.cs:1993`, `2001`)
```sql
SELECT ShortDescription FROM OtherDescription od WITH (NOLOCK)
INNER JOIN [Option] opt ON od.DescriptionId = opt.DescriptionId
WHERE opt.OptionId = <OptionId> AND LanguageId = 5   -- 5 = DE
-- and again with LanguageId = 9 (NL)
```
*Why:* fetch localized property descriptions for `addDescription(...)` (EN default from `Option2`, DE, NL). → BR-PVAL-012.

**Q-PVAL-003** — Property length from option feature length (`OCDExport.cs:2035`)
```sql
select SLFeatureLength from [option] where optionid=<OptionId>
```
*Why:* sets the `ocdProperty.digits` (character length `num17`) from `Option.SLFeatureLength`, defaulting to `OrderCodeValue2.Length`. Overridden to `5` for `FABRICCOLOUR` and `11` for `SAYLVISCHR_SB_U`. → BR-PVAL-013, BR-PVAL-014.

**Q-PVAL-004** — Property value (option value) DE/NL short descriptions (`OCDExport.cs:2071`, `2081`)
```sql
SELECT ShortDescription FROM OtherDescription od WITH (NOLOCK)
INNER JOIN OptionValue optval ON od.DescriptionId = optval.DescriptionId
WHERE optval.OptionValueId = <OptionValueId> AND LanguageId = 5   -- 5 = DE
-- and again with LanguageId = 9 (NL)
```
*Why:* localized value descriptions (appended with `" - " + OrderCodeValue2`). → BR-PVAL-015.

**Q-PVAL-005** — OA option-price feed (context, `OCDExport.cs:2988`) — used to attach price/leadtime data around the same loop; not a property table itself. Documented in 18_Pricing / 22_Export. Cited here only to note the property loop is interleaved with pricing reads.

**Q-PVAL-006** — Real attribute-value source (shared with module 07): the `Attribute`/`AttributeValue`/`BaseAttributeValues` join at `OCDExport.cs:1720` (see 07_Attributes Q-ATTR-021). This feeds `metaProperties` (GO), and the same article context drives the `ocd*` property build. *(Cross-referenced, not re-quoted.)*

> The **OCD version header** written before the tables (`OCDExport.cs:397`) enumerates the table set that the property files belong to:
> ```
> 2.1;OCD_2;1.0.0;20050727;99991231;DE;article,artlongtext,artshorttext,price,property,propertyclass,propertytext,propertyvalue,propvaluetext,relation,relationobj,version;
> ```

---

## 5. Data Model

> None of these DTOs are database tables. The tables below describe the **CSV output row layout** (from `getAllProperties()` field order) and the **DB source** of each field.

### 5.1 `ocdPropertyClass` → `ocd_propertyclass.csv`
Constructor: `ocdPropertyClass(_articleID, _position, _name, _textID, _relObjID)`; `fileName = "ocd_propertyclass"`.
| Idx | Field | Meaning | Typical source |
|---|---|---|---|
| 0 | `articleID` | owning article/product code | `text3` (article/product) |
| 1 | `position` | ordinal of the class within the article | `num15` counter (increments per distinct class key) |
| 2 | `name` | property-class name | `text31` (built class key, e.g. `<series>_CLS_<range>_...`) or `"LEADTIME"` / `"<n>_DAY"` |
| 3 | `textID` | description text id | usually `""` |
| 4 | `relObjID` | related-object id | `""` or `"0"` |

### 5.2 `ocdProperty` → `ocd_property.csv`
Constructor: `ocdProperty(_propertyClass, _propertyName, _position, _textID, _relObjID, _type, _digits, _decDigits, _obligatory, _addValues, _restrictable, _scope, _txtControl)`; `fileName = "ocd_property"`.
| Idx | Field | Meaning | Notes / observed values |
|---|---|---|---|
| 0 | `propertyClass` | owning class name | matches an `ocdPropertyClass.name` |
| 1 | `propertyName` | property name | e.g. `<series>_<Option2>`, `LF_SEATTYPE`, `LEADTIME`, `ARTICLECODE` |
| 2 | `position` | ordinal within class | `num14*10 + num18` (spacing leaves gaps for inserts) |
| 3 | `textID` | description index | `_propertyDescriptions.IndexOf(...) + 1` (1-based) |
| 4 | `relObjID` | related-object id | `""` or `"0"` |
| 5 | `type` | property data type | observed `"C"` (character) |
| 6 | `digits` | length | from `SLFeatureLength` / order-code length (Q-PVAL-003) |
| 7 | `decDigits` | decimal digits | observed `"0"` |
| 8 | `obligatory` | mandatory flag | observed `"1"` |
| 9 | `addValues` | allow additional values | observed `"0"` |
| 10 | `restrictable` | restrictable flag | observed `"0"` / `"1"` |
| 11 | `scope` | scope code | observed `"R"` (restrict?), `"C"` (choice?), `"RV"` — exact meanings `UNKNOWN` |
| 12 | `txtControl` | text control code | observed `"0"` / `"4"` |

### 5.3 `ocdPropertyValue` → `ocd_propertyvalue.csv`
Constructor: `ocdPropertyValue(_propertyClass, _propertyName, _position, _textID, _relObjID, _isDefault, _suppressText, _opFrom, _valueFrom, _opTo, _valueTo)`; `fileName = "ocd_propertyvalue"`.
| Idx | Field | Meaning | Notes / observed values |
|---|---|---|---|
| 0 | `propertyClass` | owning class | |
| 1 | `propertyName` | owning property | |
| 2 | `position` | value ordinal | `num19` running counter per (class|property), or computed for LEADTIME |
| 3 | `textID` | value description index | `_propvalueDescriptions.IndexOf(...) + 1` (1-based) |
| 4 | `relObjID` | related-object id | usually `""`; **rewritten** in FS/AS post-processing (see BR-PVAL-020) |
| 5 | `isDefault` | default-value flag | `num16` (1 when first value of a new option) or `"0"` |
| 6 | `suppressText` | suppress text flag | observed `"0"` |
| 7 | `opFrom` | lower comparison operator | observed `"EQ"` |
| 8 | `valueFrom` | lower/exact value | `OrderCodeValue2.Replace(" ", "_")` or the leadtime value |
| 9 | `opTo` | upper comparison operator | usually `""` |
| 10 | `valueTo` | upper value | usually `""` |

### 5.4 DB source tables (read to build the DTOs)
- **`Option`** (`[Option]`) — `OptionId` (PK), `Name`, `DescriptionId`, `DisplayOrder`, `SLFeatureLength`, `ProductCategoryId`, `OrderCodeFormatKey`. Provides property (class member) definitions.
- **`OptionValue`** (`optval`) — `OptionValueId` (PK), `OptionId` (FK), `Name`, `OrderCodeValue`, `DescriptionId`, `DisplayOrdinal`, `Status`. Provides the property values.
- **`ItemOptionValues`** — (`ItemId`, `OptionValueId`) with `IncrementalPrice*`/`IncrementalVolume` (used by the interleaved price feed).
- **`OtherDescription`** — `DescriptionId`, `LanguageId` (EN default, DE = 5, NL = 9), `ShortDescription`.
- **`Attribute` / `AttributeValue` / `BaseAttributeValues`** — see 07_Attributes §5.2 (feed the parallel GO/`metaProperties` build in the same loop).
- **`PDMOptionDataReport`** — stored procedure; exact body `UNKNOWN` (not in source tree), but its projected columns are enumerated in Q-PVAL-001.

---

## 6. Business Rules

> IDs unique within module 08. "Verified" = provable from cited source; otherwise `UNKNOWN`.

### DTO structure / serialization
- **BR-PVAL-003** — Each DTO serializes to exactly one CSV row via `getAllProperties()`, fields joined with `;` in the fixed declared order (`OCDExport.cs:594-608`). Field order is the CSV column order (see §5). *(Verified.)*
- **BR-PVAL-004** — The target CSV filename is the DTO's `fileName`: `ocd_propertyclass`, `ocd_property`, `ocd_propertyvalue` (constructors). The writer appends `.csv` (`OCDExport.cs:403`). *(Verified.)*
- **BR-PVAL-005** — DTOs perform **no** validation, defaulting, or persistence; all logic lives in the `OCDExport` build loop. Empty/blank rows (all fields blank after stripping `;`/space/CR/LF) are skipped by the writer (`OCDExport.cs:610`). *(Verified.)*
- **BR-PVAL-006** — Text/description references are stored as **1-based indices** into the description arrays (`IndexOf(...) + 1`), not inline text; the actual text is emitted to the separate `propertytext`/`propvaluetext` OCD tables. *(Verified.)*

### Property-class construction
- **BR-PVAL-007** — A property class is only emitted once per unique key: the build checks `_propertyClassData.Contains(<key>)` before `arrayList13.Add(new ocdPropertyClass(...))` (`OCDExport.cs:1971-1974`, `2370-2373`). Duplicate suppression key = `<article>|<position>|<name>||<rel>`. *(Verified.)*
- **BR-PVAL-008** — Class `position` (`num15`) increments only when the class key (`text31`) changes from the previous row (`left2`) (`OCDExport.cs:2028-2031`). *(Verified.)*
- **BR-PVAL-009** — Property-class **naming** is built from `<_paramSeries>_CLS_` + `ProductRangeId`/`ProductCategoryId` + fabric/option suffixes, with many hardcoded per-item overrides (e.g. `_UPHB_FABRIC`, `_UPH_FABRIC`, `_OTT` for OAW104/200/204, AE72 option 59, AS option 28) (`OCDExport.cs:1955-1970`). Exact suffix matrix is data/series-specific. *(Verified; enumerated inline.)*

### Fabric / option counting
- **BR-PVAL-010** — Only rows with `Status = 1` are processed for property values (`OCDExport.cs:1932` `if (int.Parse(sqlDataReader2["Status"].ToString()) == 1)`). *(Verified.)*
- **BR-PVAL-011** — Rows whose `OrderCodeValue2` contains `#` are ignored entirely (`IndexOf("#") == -1` guard, `OCDExport.cs:1895`, `1918`). *(Verified.)*
- **BR-PVAL-016** — A running count of distinct non-fabric options (`num11`) and the max `IsFabric` value (`num12`) is computed in a first pass and used in the class naming (`OCDExport.cs:1908-1922`). *(Verified.)*
- **BR-PVAL-017** — Hardcoded value `"C7"` is excluded from property-value emission (`arrayList25.Add("C7")` then `!arrayList25.Contains(OrderCodeValue2)`) (`OCDExport.cs:1936-1938`). Rationale `UNKNOWN`. *(Verified filter; rationale UNKNOWN.)*
- **BR-PVAL-018** — A value is only added if its `OptionValueId` is in the allowed set `arrayList` (`arrayList.Contains(OptionValueId)`) (`OCDExport.cs:1937`). The membership source is `UNKNOWN` from this excerpt (built earlier in the run). *(Verified guard; source UNKNOWN.)*

### Property construction
- **BR-PVAL-012** — Property description = EN from `Option2`, DE from Q-PVAL-002 (LanguageId 5), NL from Q-PVAL-002 (LanguageId 9); registered via `addDescription(...)` (`OCDExport.cs:1990-2012`). *(Verified.)*
- **BR-PVAL-013** — Property length (`digits`) defaults to `OrderCodeValue2.Length`, then overridden by `Option.SLFeatureLength` if present (Q-PVAL-003, `OCDExport.cs:2032-2040`). *(Verified.)*
- **BR-PVAL-014** — Length hard-overrides: `5` when property name contains `FABRICCOLOUR`; `11` when the group contains `SAYLVISCHR_SB_U` (`OCDExport.cs:2041-2047`). *(Verified.)*
- **BR-PVAL-019** — Property `position` = `num14*10 + num18`, where `num18` is bumped for specific property-name substrings (`MR_SUPPORTBOW`, `MR_LUMBARSTRAP`, `ARMFINISHGLIDEFINISH`, and `MR_BACKFINISH` when `num14 == 2`) to force ordering gaps (`OCDExport.cs:2048-2055`). *(Verified.)*
- **BR-PVAL-021** — Properties are de-duplicated via `_propertyData.Contains(text35)` before add; the composite key is `class|prop|position|textid||C|digits|0|1|0|0|C|0` (`OCDExport.cs:2049-2052`). *(Verified.)*
- **BR-PVAL-022** — When `_newformat` is on, each emitted property also generates OFML "SPECIFIED"/`COL_` relation lines (`arrayList21/22/23/24`) for the leadtime/relation tables (`OCDExport.cs:2053-2070`). *(Verified.)*

### Property-value construction
- **BR-PVAL-015** — Value description = `optval_name + " - " + OrderCodeValue2` (EN), with DE/NL from Q-PVAL-004; registered via `addDescription(...)` (`OCDExport.cs:2100-2112`). *(Verified.)*
- **BR-PVAL-023** — `valueFrom` = `OrderCodeValue2` with spaces replaced by underscores; `opFrom` = `"EQ"`; `opTo`/`valueTo` empty (single exact-match value) (`OCDExport.cs:2126`). *(Verified.)*
- **BR-PVAL-024** — Value `position` (`num19`) is a running counter per (`class|prop`) key, tracked in parallel arrays `arrayList16`/`arrayList17` (`OCDExport.cs:2114-2120`). *(Verified.)*
- **BR-PVAL-025** — `isDefault` (`num16`) is set to `1` for the first value of a newly-encountered option (`OptionId` change), else `0` (`OCDExport.cs:1943-1948`). *(Verified.)*
- **BR-PVAL-026** — Values are de-duplicated via `_propertyValueData.Contains(text37)` before add (`OCDExport.cs:2123-2127`). *(Verified.)*
- **BR-PVAL-027** — `relObjID` is set to `"9999"` when the article starts with `MQ`/`MR` and `OrderCodeValue2` starts with `7Q` (`OCDExport.cs:2120-2122`). *(Verified.)*
- **BR-PVAL-028** — Fabric special-case: for `UPHB_FABRIC` classes whose `OrderCodeValue2` does **not** start with `8M`, value emission is **suppressed** (`flag2 = true` skips the value block) (`OCDExport.cs:2091-2094`). *(Verified.)*

### relObjID post-processing (FS/AS arms & fabric relation objects)
- **BR-PVAL-020** — After the main loop, `ocdPropertyValue` rows are rewritten: `relObjID` is set from `valueFrom` order-code prefixes. Fabric codes `8M25→+3`, `8M23→+4`, `8M22→+5`, `8M26→+6`, `8M10→+7`, `8M24→+8` (offsets from base `num58`) (`OCDExport.cs:2886-2930`). *(Verified.)*
- **BR-PVAL-029** — For classes whose name contains `_FS` (front support?): `valueFrom` in {`1A701`,`1A703`} sets `relObjID = num58 + 12` (`OCDExport.cs:2930-2942`). *(Verified.)*
- **BR-PVAL-030** — For classes whose name contains `_AS` (arm support?): `valueFrom` in {`1A701`..`1A708`} sets `relObjID = num58 + 11` (`OCDExport.cs:2943-2985`). *(Verified.)*
> Exact semantics of `_FS`/`_AS` and the numeric offsets are Herman Miller domain-specific and `UNKNOWN` beyond the code.

### Synthetic LEADTIME property
- **BR-PVAL-031** — A synthetic `LEADTIME` property class is appended per article (position `num15 + 1`), with duplicate suppression via `_propertyClassData` (`OCDExport.cs:2370-2374`). *(Verified.)*
- **BR-PVAL-032** — LEADTIME class gets a fixed `ARTICLECODE` property (`type C`, `digits 80`, `scope R`) and a `LEADTIME` property (`type C`, `digits 2`, `restrictable 1`, `scope C`, `txtControl 4`) (`OCDExport.cs:2378-2388`). *(Verified.)*
- **BR-PVAL-033** — One `ocdPropertyValue` is emitted per distinct lead-time (`arrayList26`); value `position` = `floor(firstDigit/2) + 1`; description = `<n> days` / `<n> Tage` / `<n> Dagen` (`OCDExport.cs:2389-2400`). *(Verified.)*
- **BR-PVAL-034** — Alternate (non-`_newformat`) branch emits a single `<leadtime>_DAY` class with one `LEADTIME` property (`scope RV`) and one value (`OCDExport.cs:2408-2423`). *(Verified.)*

### Ordering / grouping
- **BR-PVAL-035** — Property values inherit the option ordering from `PDMOptionDataReport` (driven by `OptionId` grouping); there is no explicit ORDER BY applied to the DTO collections after build — CSV order = insertion order. *(Verified by absence of re-sort before serialization.)*

---

## 7. Hidden Logic

- **HL-PVAL-1 — Late-bound serialization.** The writer uses `NewLateBinding.LateGet(...,"getAllProperties",...)` and `...,"fileName",...` (reflection-style) rather than typed calls (`OCDExport.cs:459`, `589-608`). Any DTO exposing `getAllProperties()`/`fileName` is treated uniformly; renaming those members silently breaks export with no compile error.
- **HL-PVAL-2 — `_FS`/`_AS`/`8M*`/`1A70*` magic codes.** Property values are rewritten based on hardcoded order-code substrings (BR-PVAL-020/029/030). These encode Herman Miller arm/fabric relation objects; not discoverable from schema.
- **HL-PVAL-3 — Position gaps by ×10.** Property positions use `num14 * 10` (BR-PVAL-019) so manual insertions have room; the `+num18` bumps are triggered by specific product feature names.
- **HL-PVAL-4 — "C7" and "#" silent drops.** Value `C7` (BR-PVAL-017) and any `OrderCodeValue2` containing `#` (BR-PVAL-011) are silently excluded — data present in DB will be missing from export.
- **HL-PVAL-5 — Suppressed non-8M fabric values.** `UPHB_FABRIC` non-`8M` values are dropped (BR-PVAL-028); the property still exists but has fewer values than the DB.
- **HL-PVAL-6 — `overrideZeroFlag` / metaTypes coupling.** The same loop that builds `ocd*` properties also builds `metaTypes`/`metaProperties` (module 07) with an `overrideZeroFlag` computed from a large hardcoded article-prefix switch (`OCDExport.cs:1740-1830`). Property emission and GO-type emission are entangled.
- **HL-PVAL-7 — Multiple passes over the stored proc.** `PDMOptionDataReport` is executed 3+ times per catalogue (count pass, then build passes). Result-set stability across executions is assumed (BR-PVAL-016).
- **HL-PVAL-8 — DTO fields are `internal`, `fileName` is `public`.** Only `fileName` is public; the value fields are `internal` and are read via late binding, not property getters. Post-processing (BR-PVAL-020) mutates `ocdPropertyValue` instances **in place** in `arrayList12`.

---

## 8. UI Behaviour

- These DTOs have **no UI**. They are produced during a batch/threaded export.
- User-facing feedback comes from the surrounding `OCDExport` form/thread (progress, error `MsgBox` such as `"error :/"` at `OCDExport.cs:558`), documented in 21_OCD / 22_Export.
- Output is written to a directory tree `...\hmx\<groupfilter>\ANY\1\db\` (recreated each run; existing folder deleted) with `.sr`/`go_` files relocated to `...\hmx\<groupfilter>\1\` (`OCDExport.cs:380-410`). → relevant to Risks (destructive rebuild).

---

## 9. Dependencies

- **`OCDExport.cs`** — sole constructor, aggregator, serializer, and post-processor of all three DTOs.
- **Stored procedure `PDMOptionDataReport`** — primary data source (body not in source tree).
- **Tables:** `Option`, `OptionValue`, `ItemOptionValues`, `OtherDescription`, and (shared) `Attribute`/`AttributeValue`/`BaseAttributeValues`, `Product`, `ProductRange`, `ProductCategory`, `CatalogueItems`, `Currency`, `PriceMatrix`, `Product_Code`.
- **Sibling OCD/meta DTOs:** `metaProperties` (07), `metaTypes`, `metaArticles`, `metaDescriptions`, `ocdArticle`, `ocdArtBase`, `ocdArtDesc`, `ocdRelation`, `ocdCodeScheme`, `ocdPrice` — all serialized through the same `OCDTables` writer.
- **`ConnectionFactory`** — connections `sqlConnection`, `sqlConnection2`, `sqlConnection3` used across the nested readers.
- **`Global`** — `globalSiteId`, currency/effective-date context for the interleaved price feed; `_newformat` flag toggles relation-object emission.
- **VB runtime** — `Microsoft.VisualBasic` `Operators`/`Conversions`/`NewLateBinding` throughout (decompiled from VB.NET).

---

## 10. Risks

- **R-PVAL-1 (High) — Hardcoded product knowledge.** Dozens of article/series/order-code literals (`MIRRA`, `AERON`, `SAYL`, `EMBODY`, `SWOOP`, `LF`, `8M*`, `1A70*`, `C7`, `_FS`, `_AS`, `_UPHB_FABRIC`, catalogue-specific overrides) are baked into the build. Any new product requires code changes; migration must externalize this into data.
- **R-PVAL-2 (High) — Late-bound serialization fragility.** Reflection on `getAllProperties()`/`fileName` (HL-PVAL-1) means field-order or member-name changes fail silently at runtime, corrupting CSV column alignment.
- **R-PVAL-3 (Medium) — Silent data loss.** `#`-codes, `C7`, and non-`8M` `UPHB_FABRIC` values are dropped (HL-PVAL-4/5). Consumers cannot tell whether a value was intentionally absent or filtered out.
- **R-PVAL-4 (Medium) — Destructive output rebuild.** The export deletes and recreates the `...\ANY\1\db` directory each run (`OCDExport.cs:382-388`); an interrupted run leaves a partial OCD dataset.
- **R-PVAL-5 (Medium) — Stored-proc coupling & repeated execution.** All property structure depends on `PDMOptionDataReport` (body unknown) executed multiple times; changes to the proc or non-deterministic ordering would silently reshape properties (BR-PVAL-016/035).
- **R-PVAL-6 (Low) — In-place mutation of DTOs.** `relObjID` rewriting mutates shared list entries after construction (HL-PVAL-8); ordering of build vs post-process is significant and undocumented.
- **R-PVAL-7 (Low) — Undocumented field semantics.** `scope` (`R`/`C`/`RV`), `txtControl`, and `relObjID` offset meanings are `UNKNOWN` beyond observed literals; a faithful reimplementation needs the OCD spec.
- **R-PVAL-8 (Info) — Hardcoded language IDs.** DE = 5, NL = 9, EN default are hardcoded in Q-PVAL-002/004; adding a language requires code changes.
```
