# 06 — Articles

**Module prefix:** BR-ART
**Primary legacy source:** `PDMMaintenance/metaArticles.cs`, `PDMMaintenance/ocdArticle.cs`, `PDMMaintenance/ocdArtBase.cs`, `PDMMaintenance/ocdArtDesc.cs`, `PDMMaintenance/ocdCodeScheme.cs`, `PDMMaintenance/codeScheme.cs`, `PDMMaintenance/ProductCodeEntry.cs`; consumer/populator `PDMMaintenance/OCDExport.cs`
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

This module defines the **article model** — the OFML/OCD representation of a sellable/orderable
thing — and the maintenance of **product codes** that articles carry.

Three distinct concepts appear in this cluster, and the code keeps them separate:

| Concept | Where it lives | Meaning (as found in code) |
|---------|----------------|----------------------------|
| **Article** | `ocdArticle`, `ocdArtBase`, `ocdArtDesc`, `metaArticles` DTOs | An OFML/OCD "article" record generated from a PDM `Item` during export. It is a *serialisation format object*, not a database table — each DTO carries a `fileName` naming its target OCD/meta output file (`ocd_article`, `ocd_artbase`, `ocd_artdesc`, `go_articles`). Populated by `OCDExport.cs`. |
| **Product Code Scheme** | `ocdCodeScheme`, `codeScheme` DTOs | An OCD *code scheme* (`ocd_codescheme`) — the template/grammar describing how an article's order code is assembled from property fields. |
| **Product Code** | `ProductCodeEntry` form + `Product_Code` table | A concrete per-**site** product/order code with its price code, unit code, base-price reference, etc. Referenced by `Product.ProductCodeId` and used throughout Products (`05_Products.md`). |

**Distinction vs. Super Products (`05_Products.md`):** a *super product* is a `Product` flagged
`IsSuperProduct = 1` whose `Item`s carry a BOM in `ItemComponents`. An *article* is the exported
OCD/OFML record derived from an `Item` (super or not). A *product code* is the order-code string
attached to a product per site. The DTOs here are the **output shape** of the export, whereas
`Product_Code` is a real editable table.

The DTO classes are almost pure data holders: each has a constructor that initialises all fields
to `""`, then assigns the passed values, plus a single `getAllProperties()` returning an
`ArrayList` of the fields in fixed order (the export writer emits these positionally).

---

## 2. Entry Points

| Entry point | File / line | Trigger |
|-------------|-------------|---------|
| `ProductCodeEntry` (form) | `ProductCodeEntry.cs` | Opened as a dialog from `StaticDataMaintenance.cs:5032` (`new ProductCodeEntry()`) to add a new `Product_Code`. |
| `ProductCodeEntry_Load` | `ProductCodeEntry.cs:435` | Populates the site selector. |
| `AddButton_Click` | `ProductCodeEntry.cs:468` | Inserts the new product code. |
| `metaArticles(...)` ctor | `metaArticles.cs:20` | Constructed by `OCDExport.cs` (lines 1710, 1714). |
| `ocdArticle(...)` ctor | `ocdArticle.cs:27` | Constructed by `OCDExport.cs` (lines 1626, 1630). |
| `ocdArtBase(...)` ctor | `ocdArtBase.cs:17` | Constructed by `OCDExport.cs` (lines 1987, 1991, 2404). |
| `ocdArtDesc(...)` ctor | `ocdArtDesc.cs:17` | Constructed by `OCDExport.cs` (lines 580, 2993–3040). |
| `ocdCodeScheme(...)` / `codeScheme(...)` ctors | resp. files | Constructed by `OCDExport.cs` (lines 2312, 919). |

The DTOs have no event handlers; they are instantiated and later serialised by the export engine.
`ProductCodeEntry` is the only interactive form in this cluster.

---

## 3. Call Hierarchy

```
Form: ProductCodeEntry (dialog)
 └─ Load → ProductCodeEntry_Load
      └─ SQL Q-ART-001 (sites) → siteselector
 AddButton_Click
      ├─ sanitise inputs (strip ', CR, LF; trim)
      ├─ validate all required fields present
      └─ SQL Q-ART-002 INSERT INTO Product_Code   → sets inserted = true

Article model (data holders, no controllers):
 OCDExport.exportThread (see 21_OCD / 22_Export)
   ├─ builds ocdArticle  → getAllProperties() → ocd_article file rows
   ├─ builds ocdArtBase  → getAllProperties() → ocd_artbase file rows
   ├─ builds ocdArtDesc  → getAllProperties() → ocd_artdesc file rows (quoted text)
   ├─ builds ocdCodeScheme/codeScheme → ocd_codescheme file rows
   └─ builds metaArticles → getAllProperties() → go_articles file rows
```

There is **no service/repository layer**. `ProductCodeEntry` builds one inline INSERT.
The article DTOs are constructed directly by `OCDExport` from its result-set loops.

---

## 4. SQL Analysis

> Only `ProductCodeEntry` contains SQL in this cluster; the DTO classes contain none.
> The article-building SQL lives in `OCDExport.cs` and is documented in the OCD/Export module;
> the article-relevant fragments are cross-referenced below.

**Q-ART-001** — site list (line 441, `ProductCodeEntry_Load`):
```sql
SELECT SiteId, Description FROM Site ORDER BY SiteId
```
*WHY:* populate the site selector for the new product code. (Note: unlike Products' Q-PROD-003, **no exclusion of site 20** here.)

**Q-ART-002** — insert product code (line 487, `AddButton_Click`):
```sql
INSERT INTO Product_Code
  (ProductCodeId, SiteId, Product_Code, Description, PriceCode, UnitCode, BasePriceRef, Truncation, OCDExport, Status)
VALUES
  (<prodCodeIdText>, <siteId>, '<productCode>', '<description>', '<priceCode>', '<unitCode>', <basePriceRef>, 0, 0, 1)
```
*WHY:* create a new product/order code for a site with defaults `Truncation = 0`, `OCDExport = 0`, `Status = 1`. `BasePriceRef` comes from `basepriceCombo`. `ProductCodeId` is supplied by the caller via `prodCodeIdText` (see BR-ART-014, Risks).

**Cross-reference — article-build SQL in `OCDExport.cs`** (documented fully in OCD/Export module):
- `EXEC GetProductOptionCount @product OUT @optcount` (line ~1615) — option count feeding article generation.
- Attribute pull for article base rows (line ~1720): `SELECT attr.Name, atval.Name, ... FROM AttributeValue atval INNER JOIN BaseAttributeValues bav ... WHERE bav.ItemId = <id> ORDER BY attr.DisplayOrder, atval.DisplayOrdinal` — drives `ocdArtBase` properties.
- `SELECT LeadTime FROM Catalogue WITH (NOLOCK) WHERE CatalogueId = <id>` (line ~2325) — lead-time article variants.

---

## 5. Data Model

### 5.1 Article DTOs (OFML/OCD serialisation objects)

**`ocdArticle`** → output file `ocd_article` (`getAllProperties` order):
| # | Field | Meaning |
|---|-------|---------|
| 1 | `articleID` | Unique article code. |
| 2 | `articleType` | OCD article type. Observed value `"C"` (configurable) at `OCDExport.cs:1620`. |
| 3 | `manufacturerID` | Manufacturer. Hardcoded `"HM"` at construction (OCDExport 1626/1630). |
| 4 | `seriesID` | Series. `_paramSeries` (new format) or `_paramSeries + _leadtime` (old format). |
| 5 | `shortTextID` | 1-based index into the collected short-description list. |
| 6 | `longTextID` | Long-text id (`num6` in export). |
| 7 | `relObjID` | Relation-object id. Emitted empty `""`. |
| 8 | `fastSupply` | Fast-supply flag. Hardcoded `"0"`. |
| 9 | `orderUnit` | Order unit. Hardcoded `"C62"` (UN/ECE code for "one/piece"). |
| 10 | `schemeID` | Code-scheme id linking the article to its `ocd_codescheme`. |

**`ocdArtBase`** → output file `ocd_artbase`:
| # | Field | Meaning |
|---|-------|---------|
| 1 | `articleID` | Owning article. |
| 2 | `propertyClass` | Property class name. |
| 3 | `propertyName` | Property name. |
| 4 | `reference` | Reference/value. |

Observed constructions: `("<art>", "<class>", "LF_SEATTYPE", "F"|"A")` (OCDExport 1987/1991) and
`("<art>", "LEADTIME", "ARTICLECODE", "<art>")` (line 2404).

**`ocdArtDesc`** → output file `ocd_artdesc`:
| # | Field | Meaning |
|---|-------|---------|
| 1 | `textID` | Text id (1-based index into the description list). |
| 2 | `language` | Language code: `"en"`, `"de"`, `"nl"` (constructed per language, OCDExport 2993–3040). |
| 3 | `lineNr` | Line number within the text (observed `"1"`). |
| 4 | `textline` | The description text. |

**Field semantics note:** `ocdArtDesc.getAllProperties()` returns the 4th element **already
quoted and escaped**: `"\"" + textline.Replace("\"", "\"\"") + "\""` — i.e. wrapped in double
quotes with internal quotes doubled (CSV-style escaping). The other three are raw.

**`ocdCodeScheme`** → output file `ocd_codescheme`:
| # | Field | Meaning |
|---|-------|---------|
| 1 | `schemeID` | Scheme id. |
| 2 | `schemeTemplate` | Template grammar string. |
| 3–8 | `field1..field6` | Scheme fields. Observed literal defaults `"\" \""`, `"\" \""`, `"1"`, `"\"-\""`, `"\"X\""`, `"0"` (OCDExport 2312). |

**`codeScheme`** → output file `ocd_codescheme` (an 8-value variant, same target file):
| # | Field |
|---|-------|
| 1–8 | `value1..value8` |
Observed default seed: `("U00000000000000001", "ValueList", "\" \"", "\" \"", "1", "\"-\"", "\"X\"", "0")` (OCDExport 913/919).

**`metaArticles`** → output file `go_articles`:
| # | Field | Meaning |
|---|-------|---------|
| 1 | `product` | Product/type code. |
| 2 | `manufacturerID` | Manufacturer. Hardcoded `"hmx"` (OCDExport 1710/1714). |
| 3 | `productLine` | `_paramSeries.ToLower()` (+ `_leadtime` in old format). |
| 4 | `item` | The source `Item.Item`. |
| 5 | `articleID` | Article id (`text22` = `<code>_<index>` in export). |
| 6 | `dependentProperties` | Dependent property string. Emitted empty `""` in observed calls. |

### 5.2 `Product_Code` table (maintained by `ProductCodeEntry`)

| Column | Type/role | Notes |
|--------|-----------|-------|
| `ProductCodeId` | PK | Supplied by caller (`prodCodeIdText`), not auto-generated in this INSERT. |
| `SiteId` | FK → `Site` | Which site the code belongs to. |
| `Product_Code` | text | The order/product code string. |
| `Description` | text | Human description. |
| `PriceCode` | text | Links to `PriceMatrix.ItemPriceCode` (see Products pricing). |
| `UnitCode` | text | Unit of measure code. |
| `BasePriceRef` | int (1/2/3) | Selects `BasePrice`/`BasePrice2`/`BasePrice3` and incremental columns. |
| `Truncation` | int | Defaulted `0` on insert. |
| `OCDExport` | int/bit | Defaulted `0` on insert. |
| `Status` | int | Defaulted `1` (active) on insert. |

### 5.3 `Site` table (read)

| Column | Role |
|--------|------|
| `SiteId` (PK), `Description` | Site selector source (Q-ART-001). |

`UNKNOWN`: authoritative column list / constraints of `Product_Code` beyond those written here
(no CREATE TABLE in scope). `UNKNOWN`: the OCD output-file record layouts beyond field order.

---

## 6. Business Rules

### Product code entry (`ProductCodeEntry`)
- **BR-ART-001** The site combo is populated from all sites ordered by `SiteId`, and index 0 is auto-selected if any exist (Q-ART-001, `ProductCodeEntry_Load`).
- **BR-ART-002** The site, rounding and base-price combos are read-only for typing: their `KeyPress` handlers set `e.Handled = true` (lines 523, 528, 533) — selection only.
- **BR-ART-003** *Input sanitisation:* PriceCode, Description, Product_Code and UnitCode are each stripped of single-quotes, CR and LF and trimmed before use (`AddButton_Click`, line 474+).
- **BR-ART-004** *Required-field validation:* an insert proceeds only if a site is selected **and** PriceCode, Product_Code and Description are all non-empty; otherwise *"Please enter all of the required Product Code data"* is shown. (UnitCode is **not** required.)
- **BR-ART-005** On insert, `Truncation`, `OCDExport` are defaulted to `0` and `Status` to `1` (active) (Q-ART-002).
- **BR-ART-006** `BasePriceRef` is taken from `basepriceCombo.Text` parsed as an integer (`int.Parse`) — a non-numeric selection would throw (caught by the handler's catch).
- **BR-ART-007** On success, `inserted = true` is set (so the caller `StaticDataMaintenance` can detect a change) and a confirmation message naming the code and site is shown.
- **BR-ART-008** On failure, the message advises *"Please ensure this Product Code does not already exist for the Site"* — i.e. a duplicate `(Product_Code, SiteId)` is the assumed cause; the raw exception text is appended **only if** `AuthenticateUser.PDMAdministrator` is true (line ~500).
- **BR-ART-009** During the operation the Add and Close buttons are disabled and re-enabled in `finally`.
- **BR-ART-010** The form does not exclude any site (contrast Products BR-PROD-007 which hides site 20).

### Article model construction (observed in `OCDExport`, defining article semantics)
- **BR-ART-011** Every article DTO is created with all fields initialised to empty string in its constructor before assignment (defensive default — no `null` fields emitted).
- **BR-ART-012** `ocdArticle` is emitted with fixed manufacturer `"HM"`, order unit `"C62"`, `fastSupply = "0"`, empty `relObjID`, and `articleType = "C"`; `seriesID` includes the lead-time suffix only in the **old** (`!_newformat`) format (OCDExport 1626/1630).
- **BR-ART-013** `metaArticles` (go_articles) is emitted with fixed manufacturer `"hmx"`; `productLine` is the lower-cased series, with the lead-time appended only in old format (OCDExport 1710/1714). In new format the product code is truncated at the first `"_"` before use.
- **BR-ART-014** `ocdArtDesc` text is emitted per language `en`/`de`/`nl` in that order, each as line `1`, with the text field CSV-quoted (internal `"`→`""`).
- **BR-ART-015** The default seed code scheme is `codeScheme("U00000000000000001", "ValueList", " ", " ", "1", "-", "X", "0")` added once per group (OCDExport 913/919); article-specific schemes are added as `ocdCodeScheme` only if not already present (`_codeSchemeData.Contains` guard, line 2306).
- **BR-ART-016** `ocdArtBase` `LF_SEATTYPE` reference is `"F"` or `"A"` depending on the branch taken (OCDExport 1987/1991) — a fixed enumeration of seat-type references. `UNKNOWN`: full meaning of `F`/`A`.
- **BR-ART-017** A `LEADTIME`/`ARTICLECODE` `ocdArtBase` row is added per article keyed by the article code itself (`ocdArtBase(text3, "LEADTIME", "ARTICLECODE", text3)`, line 2404), guarded by `_artBaseData.Contains` de-duplication.
- **BR-ART-018** Duplicate suppression across the export uses parallel string keys (`_codeSchemeData`, `_artBaseData`, `_propertyData`, etc.) so each distinct scheme/base/property row is emitted once.

---

## 7. Hidden Logic / Magic Numbers

- **`fileName` is a hidden output-file selector:** every DTO sets `fileName` in its constructor (`ocd_article`, `ocd_artbase`, `ocd_artdesc`, `ocd_codescheme`, `go_articles`). Both `codeScheme` and `ocdCodeScheme` target the **same** file `ocd_codescheme` — two shapes writing one file.
- **Hardcoded manufacturer ids:** `"HM"` for OCD articles vs `"hmx"` for meta (go) articles — different casings/values for the same conceptual manufacturer.
- **Hardcoded order unit `"C62"`** on every article (UN/ECE unit code for "piece").
- **Hardcoded article type `"C"`** (configurable) for all articles in the observed path.
- **Seed scheme id `"U00000000000000001"`** — a fixed 18-char placeholder scheme id.
- **Literal scheme fields `" "`, `"-"`, `"X"`, `"1"`, `"0"`** repeated as code-scheme defaults.
- **`Product_Code` insert hardcodes** `Truncation=0`, `OCDExport=0`, `Status=1` — new codes are always active and never OCD-exported/truncated by default.
- **`ProductCodeId` is caller-supplied**, not identity-generated in this INSERT (`prodCodeIdText`) — the id origin is external (see Risks).
- **Admin-only error detail:** raw exception text is surfaced only when `AuthenticateUser.PDMAdministrator` (BR-ART-008) — a role-gated diagnostic.
- **`ocdArtDesc` quoting asymmetry:** only the 4th (`textline`) property is quoted/escaped; a downstream writer must treat the others as raw — an implicit, undocumented contract.
- **`_catalogueId == 4`** special-cases lead times to `45/25/15` in the article lead-time build (OCDExport 2317) — a catalogue-specific hardcode affecting article variants. `UNKNOWN`: which catalogue id 4 is.

---

## 8. UI Behaviour

- **`ProductCodeEntry`** is a small modal dialog: on load it fills the site combo (auto-select first); the site/rounding/base-price combos reject keyboard entry (selection only); Add disables both buttons while inserting and re-enables them in `finally`; Close simply closes the dialog.
- Success and failure are communicated via `Interaction.MsgBox`; there is no in-form list refresh — the parent (`StaticDataMaintenance`) reads the `inserted` flag to decide whether to refresh its own view.
- The article DTO classes have **no UI**; they are constructed and serialised headlessly by the export engine (progress/UI belongs to `OCDExport` — see OCD/Export module).

---

## 9. Dependencies

- `ConnectionFactory.CreateNewConnection(autoOpen)` — SQL Server connection for `ProductCodeEntry` (foundation fact).
- `AuthenticateUser.PDMAdministrator` — gates verbose error text.
- `StaticDataMaintenance.cs` — the sole opener of `ProductCodeEntry` (line 5032).
- `OCDExport.cs` — the sole constructor/consumer of all article DTOs (`ocdArticle`, `ocdArtBase`, `ocdArtDesc`, `ocdCodeScheme`, `codeScheme`, `metaArticles`); it also supplies `_paramSeries`, `_leadtime`, `_newformat`, description collections and the de-dup key lists.
- `Product`/`Item`/`Product_Code`/`Site`/`Catalogue`/`Attribute`/`AttributeValue` tables (article source data — detailed in Products / OCD modules).
- OCD/OFML output files: `ocd_article`, `ocd_artbase`, `ocd_artdesc`, `ocd_codescheme`, `go_articles`.

---

## 10. Risks

- **SQL injection (`ProductCodeEntry`):** the INSERT is string-concatenated; only single-quotes/CR/LF are stripped from the text fields. `ProductCodeId` and `BasePriceRef` are interpolated without quoting and rely on `int.Parse`/caller trust — a non-numeric `prodCodeIdText` would produce malformed SQL.
- **Caller-supplied primary key:** `ProductCodeId` is not generated by the INSERT; if the caller computes it incorrectly or races another insert, a PK/unique collision occurs (handled only by the generic catch → duplicate message).
- **No transaction / no existence check:** duplicates are detected only by the DB throwing on insert; the user sees a generic "may already exist" message rather than a validated result.
- **Silent defaults:** every new product code is forced `Status=1`, `OCDExport=0`, `Truncation=0` with no UI to set them — later behaviour (e.g. whether the code is OCD-exported) cannot be configured at creation.
- **Article DTOs are format-fragile:** `getAllProperties()` emits fields positionally with mixed quoting rules (only `ocdArtDesc.textline` is escaped). Any consumer that quotes/escapes differently will corrupt the OCD output; there is no schema validation.
- **Hardcoded catalogue/manufacturer/lead-time constants** (`HM`/`hmx`, `C62`, catalogue id 4 → 45/25/15) bake business data into code; onboarding a new manufacturer, unit, or catalogue requires source changes.
- **Dual writers to one file:** `codeScheme` and `ocdCodeScheme` both write `ocd_codescheme` with different field counts (8 vs 8 but different semantics) — ordering/consistency depends entirely on `OCDExport` orchestration; a mismatch would yield inconsistent scheme rows.
- **`UnitCode` optional but interpolated:** it is not required (BR-ART-004) yet still concatenated into SQL; an empty unit code is stored silently, which may be invalid for downstream OCD export.
