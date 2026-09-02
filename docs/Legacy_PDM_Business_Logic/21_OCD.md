# 21 — OCD
**Module prefix:** BR-OCD
**Primary legacy source:** OCDExport.cs, ocd*.cs
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

**OCD = OFML Commercial Data.** OFML (Office Furniture Modelling Language) is
the German furniture-industry standard for exchanging configurable-product
catalogue data between manufacturers and CAD/quotation planning tools (e.g.
pCon). The *commercial* half of OFML (OCD) describes, for each orderable
article: its variant properties, the values those properties may take, the
price surcharge per option value, the textual descriptions in multiple
languages, and the logical relations/constraints between options.

This module (`OCDExport.cs`) generates a complete OCD data package on disk from
the PDM SQL database. Concretely the export produces, per Product Code, a
directory tree of semicolon-delimited CSV files that together form one OFML/OCD
"database" plus the Herman Miller proprietary `go_*` metadata files and `.sr`
symbol-resource text files. The output set is:

- **`ocd_version.csv`** — OCD format manifest / version header.
- **`ocd_article`** — the orderable articles (article id, type, series, text refs).
- **`ocd_artbase`** — article → property-class base assignments (new format only).
- **`ocd_artshorttext` / `ocd_artlongtext`** — short/long article descriptions per language.
- **`ocd_property` / `ocd_propertyclass` / `ocd_propertyvalue`** — the variant property model.
- **`ocd_propertytext` / `ocd_propvaluetext`** — property and property-value description text.
- **`ocd_price`** — base and surcharge prices keyed by article / variant condition.
- **`ocd_relation` / `ocd_relationobj`** — variant-condition relations (constraints) and their bindings.
- **`ocd_codescheme`** — article-code scheme templates.
- **`go_articles` / `go_types` / `go_properties`** — Herman Miller "go" metadata layer.
- **`<series>_<lang>.sr`** and **`t_lt_<key>_tbl.csv`** — symbol-resource description tables and lead-time tables.

The physical layout is `...\ocd_export\<CatalogueName>\<ProductCode>\hmx\<series>\ANY\1\db\` for OCD files
and `...\hmx\<series>\1\` for `go_*` and `.sr` files (writeData, OCDExport.cs:333–460).

> **Important status finding:** the entire OCD export is **orphaned / dead in
> the current build.** `OCDExport` is constructed once
> (`ocdThread = new OCDExport();`, SytelineExport.cs:1531) but neither
> `initParams(...)` nor `execThread()` is ever called from anywhere in the
> workspace. See BR-OCD-001 and §7.

---

## 2. Entry Points

| Entry point | Location | Notes |
|---|---|---|
| `OCDExport()` constructor | OCDExport.cs:147 | Sets defaults: `_exportDirectory="C:\\"`, `_paramSeries="CE"`, `_siteId=1`, `_catalogueId=-1`, `_leadtime=99`, `_currency="EUR"`, `_effectiveDate="GetUTCDate()"`, `_newformat=true`. Calls `InitializeComponent()`. |
| `internal void initParams(exportpath, siteId, catalogueId, productCodeId, currency, effectiveDate, newformat)` | OCDExport.cs:225 | Public-ish initializer. Resolves catalogue name/lead time and the product-code list. **No live caller.** |
| `internal void execThread()` | OCDExport.cs:3101 | Thread body — calls `startExport()` then `MsgBox("OCD Export Complete")`. **No live caller.** |
| `private void startExport()` | OCDExport.cs:795 | The actual export driver. |
| `private void writeData(groupfilter, productcode)` | OCDExport.cs:333 | Serializes the assembled `OCDTables` to CSV files. |
| `private void Button1_Click(object, EventArgs)` | OCDExport.cs:3097 | Empty stub. |

`OCDExport` derives from `Form` (OCDExport.cs:18) and exposes two events,
`UpdateStatusText` and `UpdateExportTimer` (OCDExport.cs:143–145), intended for a
host form's progress UI — but no host ever subscribes to `ocdThread`'s events.

---

## 3. Call Hierarchy

```
[No live Form/menu entry — orphaned]
SytelineExport (host)                                  SytelineExport.cs
  └─ ctor: ocdThread = new OCDExport()                 SytelineExport.cs:1531
         (never wired to a button/queue/menu)

INTENDED (dead) flow, per implemented code:
OCDExport.execThread()                                 OCDExport.cs:3101
  └─ startExport()                                     OCDExport.cs:795
       ├─ ConnectionFactory.CreateNewConnection() ×3   (3 SqlConnections)
       ├─ Q-OCD-004 CatalogueOptionValues (in-scope OptionValueIds)
       ├─ Q-OCD-005/006 Items for catalogues 58 / 57   (lead-time reference sets)
       ├─ Q-OCD-007/008 Option/OptionValue for cat 58/57
       ├─ FOR each ProductCodeId
       │    ├─ Q-OCD-009 main Item query (per category, group-filter placeholder)
       │    └─ FOR each ProductCategory / group
       │         ├─ resetArrays()                        OCDExport.cs:724
       │         ├─ FOR each Item row:
       │         │    ├─ series-specific code munging (AU1/AE7/DTW…)
       │         │    ├─ GetProductOptionCount (Q-OCD-010, stored proc, OUT @optcount)
       │         │    ├─ addShortDesc / long-desc collect
       │         │    ├─ new ocdArticle(...)             → arrayList10
       │         │    ├─ addOCDPrice(new ocdPrice(...GS/B base price))
       │         │    ├─ new metaArticles(...) + addMetaType(GType/GMode/GSetup/GAlign)
       │         │    ├─ Q-OCD-011 Attribute/AttributeValue → metaProperties + meta desc
       │         │    ├─ PDMOptionDataReport (Q-OCD-012) ×3 passes:
       │         │    │     pass1 count options/fabrics; pass2 build property model
       │         │    │     (ocdPropertyClass/ocdProperty/ocdPropertyValue),
       │         │    │     Q-OCD-013..017 option/optionvalue DE+NL descriptions,
       │         │    │     Q-OCD-015 SLFeatureLength
       │         │    ├─ LEADTIME synthesis (Q-OCD-018) + lead-time tables/relations
       │         │    ├─ Q-OCD-019 incremental price union → ocdPrice(GS/X surcharge)
       │         │    │     + ocdRelation/ocdRelationObj VARCOND build,
       │         │    │     Q-OCD-020 DependentOptionValues
       │         │    └─ hardcoded HM relation blocks (AE_FINISH, RY_FRAMEFINISH,
       │         │         LF_BACKFINISH, LF_SEATTYPE, 8M*/1A70* remapping)
       │         ├─ build ocdArtDesc rows for short/long/property/propvalue text
       │         ├─ assemble OCDTables (fixed order, OCDExport.cs:3044–3072)
       │         └─ writeData(_paramSeries, productCode)   OCDExport.cs:333
       │              ├─ create dir tree hmx\<series>\ANY\1\db\
       │              ├─ write ocd_version.csv (static header)
       │              ├─ late-bound loop over OCDTables:
       │              │     row.fileName + ".csv"; row.getAllProperties() joined by ';'
       │              │     (go_* / .sr redirected to hmx\<series>\1\, .sr in CP1252)
       │              └─ write t_lt_<key>_tbl.csv lead-time tables (new format)
       └─ MsgBox("OCD Export Complete")
```

The final serialization is fully **late-bound / reflection driven**: `writeData`
never references the DTO types directly; it calls `Item`, `fileName`, `Count`
and `getAllProperties` via `NewLateBinding.LateGet`/`LateCall` on whatever
objects sit in `OCDTables` (OCDExport.cs:400–618). Each DTO's `getAllProperties()`
returns an `ArrayList` of the column values in file order.

---

## 4. SQL Analysis

All queries are **inline string-concatenation SQL** (SQL-injection-prone; see
§10). Server connections come from `ConnectionFactory.CreateNewConnection`.
All read queries use `WITH (NOLOCK)`.

### Q-OCD-001 — Catalogue name + lead time (initParams, OCDExport.cs:260)
```sql
SELECT Name, LeadTime FROM Catalogue WITH (NOLOCK) WHERE CatalogueId = <_catalogueId>
```
**Why:** seeds `_cataloguedesc` (used in the export folder path) and
`_leadtime = LeadTime + 5` (the synthetic lead-time baseline; BR-OCD-030).

### Q-OCD-002 — Product-code list for a whole catalogue (initParams, OCDExport.cs:275)
```sql
SELECT DISTINCT pc.Product_Code, pc.ProductCodeId FROM Product_Code WITH (NOLOCK) pc
INNER JOIN Product ON pc.ProductCodeId = Product.ProductCodeId
INNER JOIN Item ON Product.ProductId = Item.ProductId
INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId
WHERE ci.CatalogueId = <_catalogueId> AND pc.SiteId = <siteId> AND pc.OCDExport = 1
ORDER BY pc.Product_Code
```
**Why:** when `productCodeId == -1` (export-all), enumerate every product code in
the catalogue that is flagged `Product_Code.OCDExport = 1` at the given site.

### Q-OCD-003 — Single product-code lookup (initParams, OCDExport.cs:288)
```sql
SELECT Product_Code FROM Product_Code WITH (NOLOCK)
WHERE ProductCodeId = <productCodeId> AND SiteId = <siteId>
```
**Why:** when a specific `productCodeId` is requested, fetch its display code.

### Q-OCD-004 — In-scope catalogue option values (startExport, OCDExport.cs:813)
```sql
SELECT OptionValueId FROM CatalogueOptionValues WITH (NOLOCK) WHERE CatalogueId = <_catalogueId>
```
**Why:** builds the whitelist `arrayList` of OptionValueIds that belong to the
catalogue. This whitelist gates which option values are emitted as properties
and priced (BR-OCD-014).

### Q-OCD-005 — Lead-time reference items, catalogue 58 (startExport, OCDExport.cs:823)
```sql
SELECT Item FROM Item WITH (NOLOCK)
INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId WHERE ci.CatalogueId = 58
```
### Q-OCD-006 — Lead-time reference items, catalogue 57 (startExport, OCDExport.cs:831)
```sql
SELECT Item FROM Item WITH (NOLOCK)
INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId WHERE ci.CatalogueId = 57
```
**Why (005/006):** builds `arrayList3` (cat 58) and `arrayList2` (cat 57) of
`"ARTICLECODE;<Item>"` strings used to decide, per lead-time band, whether an
article-code row participates in a longer lead time (BR-OCD-032). Catalogue IDs
57 and 58 are **hardcoded** (§7).

### Q-OCD-007 — Option/value pairs, catalogue 58 (startExport, OCDExport.cs:841)
```sql
SELECT opt.Name, optval.OrderCodeValue FROM [Option] opt WITH (NOLOCK)
INNER JOIN OptionValue optval ON opt.OptionId = optval.OptionId
INNER JOIN CatalogueOptionValues cov ON optval.OptionValueId = cov.OptionValueId
WHERE cov.CatalogueId = 58 ORDER BY opt.Name, optval.OrderCodeValue
```
### Q-OCD-008 — Option/value pairs, catalogue 57 (startExport, OCDExport.cs:850)
```sql
SELECT opt.Name, optval.OrderCodeValue FROM [Option] opt WITH (NOLOCK)
INNER JOIN OptionValue optval ON opt.OptionId = optval.OptionId
INNER JOIN CatalogueOptionValues cov ON optval.OptionValueId = cov.OptionValueId
WHERE cov.CatalogueId = 57 ORDER BY opt.Name, optval.OrderCodeValue
```
**Why (007/008):** builds `arrayList4` (58) / `arrayList5` (57) of
`"<UPPER,despaced Name>;<OrderCodeValue>"` used as the second lead-time band
membership test (BR-OCD-032).

### Q-OCD-009 — Main item query (startExport, OCDExport.cs:864) — *the export spine*
```sql
SELECT Product.Product, Product.WebDPSProduct, Product.IsSuperProduct, Product.ProductRangeId,
       ProductCategory.ProductCategoryId, ProductCategory.Name AS pc_name, pc.Product_Code,
       Item.ItemId, Item.Item,
       dbo.fnGetListPriceByItem(Item.Item, '<_currency>', <_effectiveDate>, <Global.globalSiteId>, NULL) AS ListPrice,
       pd.ShortDescription,
       CASE WHEN pd_de.ShortDescription IS NULL THEN pd.ShortDescription ELSE pd_de.ShortDescription END AS de_desc,
       CASE WHEN pd_nl.ShortDescription IS NULL THEN pd.ShortDescription ELSE pd_nl.ShortDescription END AS nl_desc
FROM Item WITH (NOLOCK)
[INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId AND ci.CatalogueId = <_catalogueId>]   -- only if _catalogueId > -1
INNER JOIN Product ON Item.ProductId = Product.ProductId
INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
INNER JOIN ProductCategory ON pr.ProductCategoryId = ProductCategory.ProductCategoryId
INNER JOIN ProductDescription pd ON Product.DescriptionId = pd.DescriptionId AND pd.LanguageId = 1
LEFT OUTER JOIN ProductDescription pd_de ON Product.DescriptionId = pd_de.DescriptionId AND pd_de.LanguageId = 5
LEFT OUTER JOIN ProductDescription pd_nl ON Product.DescriptionId = pd_nl.DescriptionId AND pd_nl.LanguageId = 9
INNER JOIN /* note: this join does not currently honour Item PLC overrides */ Product_Code pc ON Product.ProductCodeId = pc.ProductCodeId
WHERE Item.Status = 1 AND pc.SiteId = <Global.globalSiteId>
  [AND Product.ProductCodeId = <productCodeId>]        -- only if productCodeId > -1
  [group filter]                                       -- placeholder, blanked on first pass
  AND (Item.Item NOT LIKE 'AE9%') AND (Item.Item NOT LIKE 'AU9%')
  AND (Item.Item NOT LIKE 'CJ1%F')
  [AND item.baseprice is not null]                     -- only if _catalogueId == 258
ORDER BY ProductCategory.ProductCategoryId, Item.Item
        -- OR (if _catalogueId==264 AND productCodeId==776):
        -- ORDER BY ProductCategory.ProductCategoryId, Product.IsSuperProduct, Item.Item
```
**Why:** the driving query. It selects released items (`Item.Status = 1`) at the
current site, joins the English (lang 1) short description with DE (lang 5) and
NL (lang 9) fallbacks, and computes the item list price via
`dbo.fnGetListPriceByItem` (body **UNKNOWN** — SQL function, not in workspace).
The `[group filter]` token is replaced with `""` for the category-collection
pass and with a real group predicate on the emit pass (BR-OCD-011).
See BR-OCD-012 for the hardcoded item-code exclusions and BR-OCD-013/033 for the
catalogue-258 / catalogue-264 special cases.

### Q-OCD-010 — Product option count (startExport, OCDExport.cs:1612)
```
EXEC GetProductOptionCount @product = <Item.Item>, @optcount OUTPUT   (stored proc; body UNKNOWN)
```
**Why:** returns `@optcount`, the number of options for the article. (The value
`num9` is read but its downstream use is limited; captured here as a dependency.)

### Q-OCD-011 — Attribute values for an item (startExport, OCDExport.cs:1720)
```sql
SELECT attr.Name AS attr_name, atval.Name AS atval_name,
       CASE WHEN atval.OrderCodeValue IS NULL THEN atval.Name ELSE atval.OrderCodeValue END AS OrderCodeValue,
       CASE WHEN attr.WebMenuAttribute = 1 THEN 'True' ELSE 'False' END AS IsFunctional,
       de_atval.ShortDescription AS de_atval, de_attr.ShortDescription AS de_attr,
       nl_atval.ShortDescription AS nl_atval, nl_attr.ShortDescription AS nl_attr
FROM AttributeValue atval WITH (NOLOCK)
INNER JOIN BaseAttributeValues bav ON atval.AttributeValueId = bav.AttributeValueId
INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId
LEFT OUTER JOIN OtherDescription de_atval ON atval.DescriptionId = de_atval.DescriptionId AND de_atval.LanguageId = 5
LEFT OUTER JOIN OtherDescription de_attr  ON attr.DescriptionId  = de_attr.DescriptionId  AND de_attr.LanguageId = 5
LEFT OUTER JOIN OtherDescription nl_atval ON atval.DescriptionId = nl_atval.DescriptionId AND nl_atval.LanguageId = 9
LEFT OUTER JOIN OtherDescription nl_attr  ON attr.DescriptionId  = nl_attr.DescriptionId  AND nl_attr.LanguageId = 9
WHERE bav.ItemId = <ItemId> /*AND atval.OrderCodeValue IS NOT NULL*/
ORDER BY attr.DisplayOrder, atval.DisplayOrdinal
```
**Why:** the item's *base* attribute values (fixed characteristics) → emitted as
`metaProperties` (`go_properties`) and as `metaTypes` (`go_types`) functional
properties, with DE/NL description strings. `WebMenuAttribute` flags an attribute
as "functional" (`IsFunctional`). Attribute name is prefixed `G` and stripped to
alphanumerics via `removeNonAlphaStrict` (BR-OCD-021).

### Q-OCD-012 — Central option-data report (startExport, OCDExport.cs:1889, 1913)
```
EXEC PDMOptionDataReport @cataloguedesc = <Item.Item>   (stored proc; BODY UNKNOWN — not in workspace)
```
**Why:** the heart of the property model. Executed up to three times per item:
(1) a counting pass (count non-fabric options `num11`, max fabric flag `num12`),
(2) the property-model build pass. Consumed columns include `OptionId`,
`OptionValueId`, `IsFabric`, `Status`, `OrderCodeValue`, `OrderCodeValue2`,
`Option2`, `optval_name`. The single parameter passed is the item code, despite
being named `@cataloguedesc`. `Status` semantics: **0=URL / 1=ACT / 2=OBS /
3=HLD**; only `Status == 1` (ACT) rows are processed (BR-OCD-015).

### Q-OCD-013 — Option DE description (OCDExport.cs:1995)
```sql
SELECT ShortDescription FROM OtherDescription od WITH (NOLOCK)
INNER JOIN [Option] opt ON od.DescriptionId = opt.DescriptionId
WHERE opt.OptionId = <OptionId> AND LanguageId = 5
```
### Q-OCD-014 — Option NL description (OCDExport.cs:2004)
```sql
SELECT ShortDescription FROM OtherDescription od WITH (NOLOCK)
INNER JOIN [Option] opt ON od.DescriptionId = opt.DescriptionId
WHERE opt.OptionId = <OptionId> AND LanguageId = 9
```
### Q-OCD-015 — SLFeatureLength (OCDExport.cs:2014)
```sql
select SLFeatureLength from [option] where optionid=<OptionId>
```
### Q-OCD-016 — OptionValue DE description (OCDExport.cs:2093)
```sql
SELECT ShortDescription FROM OtherDescription od WITH (NOLOCK)
INNER JOIN OptionValue optval ON od.DescriptionId = optval.DescriptionId
WHERE optval.OptionValueId = <OptionValueId> AND LanguageId = 5
```
### Q-OCD-017 — OptionValue NL description (OCDExport.cs:2102)
```sql
SELECT ShortDescription FROM OtherDescription od WITH (NOLOCK)
INNER JOIN OptionValue optval ON od.DescriptionId = optval.DescriptionId
WHERE optval.OptionValueId = <OptionValueId> AND LanguageId = 9
```
**Why (013–017):** supply the German (lang 5) and Dutch (lang 9) translation
text for property (option) and property-value (option value) descriptions, plus
the seat/feature length used in `LF_SEATTYPE` handling.

### Q-OCD-018 — Catalogue lead time for LEADTIME synthesis (OCDExport.cs:2325)
```sql
SELECT LeadTime FROM Catalogue WITH (NOLOCK) WHERE CatalogueId = <_catalogueId>
```
**Why:** builds the synthetic LEADTIME property value list (`LeadTime + 5` days),
unless `_catalogueId == 4` where it is hardcoded to `{45, 25, 15}` (BR-OCD-031).

### Q-OCD-019 — Incremental (surcharge) price query (OCDExport.cs:2431 / 2449 / 2477)
```sql
SELECT DISTINCT pc.Product_Code, Item.Item, opt.Name, optval.OrderCodeValue, optval.OptionValueId,
       opt.DisplayOrder, optval.DisplayOrdinal,
       dbo.fnGetListPrice('<_currency>',
            CASE WHEN pc.BasePriceRef = 1 THEN itov.IncrementalPrice
                 WHEN pc.BasePriceRef = 2 THEN itov.IncrementalPrice2
                 WHEN pc.BasePriceRef = 3 THEN itov.IncrementalPrice3 END,
            pc.PriceCode, <_effectiveDate>, 'DMY', pm.Rounding, <Global.globalSiteId>, NULL) AS IncList
FROM ItemOptionValues itov WITH (NOLOCK)
INNER JOIN Item ON itov.ItemId = Item.ItemId            -- (or via ItemComponents for SuperProducts / OA)
[INNER JOIN CatalogueItems ci ... AND ci.CatalogueId = <_catalogueId>]
INNER JOIN Product ON Item.ProductId = Product.ProductId
INNER JOIN /* note: this join does not currently honour Item PLC overrides */ Product_Code pc ON Product.ProductCodeId = pc.ProductCodeId
INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode
INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode
INNER JOIN OptionValue optval ON itov.OptionValueId = optval.OptionValueId
[INNER JOIN CatalogueOptionValues cov ... AND cov.CatalogueId = <_catalogueId>]
INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId
WHERE Currency.Currency = '<_currency>' AND pc.SiteId = <Global.globalSiteId>
  [AND Product.ProductCodeId = <productCodeId>]
  AND optval.OptionValueId IN (-1, <whitelisted OptionValueIds…>)
ORDER BY pc.Product_Code, opt.DisplayOrder, optval.DisplayOrdinal
```
For series `OA` a two-arm `UNION` variant (direct + via `ItemComponents`) is
built and wrapped as `SELECT DISTINCT * FROM ( … ) a WHERE a.OptionValueId IN (…)`
(OCDExport.cs:2431–2476). `SqlCommand.CommandTimeout = 300`.
**Why:** computes the option-value surcharge (`IncList`) via `dbo.fnGetListPrice`
(body **UNKNOWN**) using the price slot chosen by `Product_Code.BasePriceRef`
(1/2/3 → `IncrementalPrice`/`2`/`3`). Rows with empty `IncList` are skipped
(BR-OCD-040). Each priced value emits an `ocdPrice(GS/X surcharge)` and a
`$VARCOND` relation (BR-OCD-041/050).

### Q-OCD-020 — Dependent option values (OCDExport.cs:2601)
```sql
SELECT optval.OrderCodeValue FROM OptionValue optval WITH (NOLOCK)
INNER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId
INNER JOIN OptionValue parent_optval ON dov.OptionValueId = parent_optval.OptionValueId
AND parent_optval.OrderCodeValue = '<text59>' AND parent_optval.OptionValueId IN (-1, <whitelist…>)
```
**Why:** resolves option-value dependencies so a variant condition maps to the
correct child order code, feeding the `PELLICLE`/`TYPE→COLOUR` relation naming
(BR-OCD-051).

---

## 5. Data Model

### 5.1 Output files → producing DTO class → fields

The `writeData` loop serializes each object in `OCDTables` by calling
`getAllProperties()` and joining values with `;`. `fileName` is the base name;
`.csv` is appended (except `.sr` files, which are written then renamed to drop
`.csv`). Column order below is exactly the `getAllProperties()` order.

| Output file | Producing class | Fields (in order) | Source |
|---|---|---|---|
| `ocd_version.csv` | *(none — static string)* | fixed OCD manifest line (see BR-OCD-004) | OCDExport.cs:396 |
| `ocd_article` | `ocdArticle` | articleID; articleType; manufacturerID; seriesID; shortTextID; longTextID; relObjID; fastSupply; orderUnit; schemeID | ocdArticle.cs |
| `ocd_artbase` | `ocdArtBase` | articleID; propertyClass; propertyName; reference | ocdArtBase.cs |
| `ocd_artshorttext` | `ocdArtDesc` (fileName overridden) | textID; language; lineNr; `"`textline`"` (quotes doubled) | ocdArtDesc.cs; OCDExport.cs:2993 |
| `ocd_artlongtext` | `ocdArtDesc` (fileName overridden) | textID; language; lineNr; quoted textline | OCDExport.cs:3006 |
| `ocd_propertytext` | `ocdArtDesc` (fileName overridden) | textID; language; lineNr; quoted textline | OCDExport.cs:3021 |
| `ocd_propvaluetext` | `ocdArtDesc` (fileName overridden) | textID; language; lineNr; quoted textline | OCDExport.cs:3034 |
| `ocd_property` | `ocdProperty` | propertyClass; propertyName; position; textID; relObjID; type; digits; decDigits; obligatory; addValues; restrictable; scope; txtControl | ocdProperty.cs |
| `ocd_propertyclass` | `ocdPropertyClass` | articleID; position; name; textID; relObjID | ocdPropertyClass.cs |
| `ocd_propertyvalue` | `ocdPropertyValue` | propertyClass; propertyName; position; textID; relObjID; isDefault; suppressText; opFrom; valueFrom; opTo; valueTo | ocdPropertyValue.cs |
| `ocd_price` | `ocdPrice` | articleID; variantCondition; type; level; rule; textID; priceValue; fixValue; currency; dateFrom; dateTo | ocdPrice.cs |
| `ocd_relation` | `ocdRelation` | relationName; blockNr; codeBlock | ocdRelation.cs |
| `ocd_relationobj` | `ocdRelationObj` | relObjID; relationName; type; domain | ocdRelationObj.cs |
| `ocd_codescheme` | `codeScheme` *(old fmt)* / `ocdCodeScheme` *(new fmt)* | 8 fields: value1..value8 / schemeID; schemeTemplate; field1..field6 | codeScheme.cs; ocdCodeScheme.cs |
| `go_articles` | `metaArticles` | product; manufacturerID; productLine; item; articleID; dependentProperties | metaArticles.cs |
| `go_types` | `metaTypes` | product; propertyName; propertyFormat; defaultValue; propertyMode; propertyParent | metaTypes.cs |
| `go_properties` | `metaProperties` | product; articleID; propertyName; propertyValue; variantCode; variantValue | metaProperties.cs |
| `<series>_en/de/nl.sr` | *(raw strings in `metaDescriptionData`/DE/NL)* | first element is the `.sr` filename; remaining are `@KEY=value` text lines | OCDExport.cs:1640–1648 |
| `t_lt_<key>_tbl.csv` | *(raw strings in `leadtimeTables`)* | `<band>;COL_ARTICLECODE;<code>` / `<band>;COL_LEADTIME;<days>` | OCDExport.cs:657 |

> **Note:** two code-scheme DTOs coexist. `codeScheme` (codeScheme.cs) sets
> `fileName="ocd_codescheme"` and is only added to `OCDTables` in **old** format
> (`!_newformat`, OCDExport.cs:3050). `ocdCodeScheme` (ocdCodeScheme.cs) also sets
> `fileName="ocd_codescheme"` and is emitted via `arrayList15` in **new** format.
> `metaDescriptions` (metaDescriptions.cs) is a bare struct with **no `fileName`
> and no `getAllProperties()`** — it is *not* serialized by the writer loop; the
> `.sr` content is instead carried as raw strings.

### 5.2 `OCDTables` assembly order (OCDExport.cs:3044–3072)

```
metaArticleData, metaTypeData, metaPropertyData,
metaDescriptionData, metaDEDescriptionData, metaNLDescriptionData,
[codeScheme]                       (only if !_newformat),
arrayList10 (ocdArticle), priceData (ocdPrice),
arrayList43 (ocd_artshorttext), arrayList44 (ocd_artlongtext),
arrayList13 (ocdPropertyClass), arrayList11 (ocdProperty), arrayList12 (ocdPropertyValue),
arrayList45 (ocd_propertytext), arrayList46 (ocd_propvaluetext),
arrayList28 (ocdRelation), arrayList29 (ocdRelationObj),
[arrayList14 (ocdArtBase), arrayList15 (ocdCodeScheme)]   (only if _newformat)
```

### 5.3 Source database tables read

`Catalogue`, `Product_Code`, `Product`, `Item`, `CatalogueItems`,
`CatalogueOptionValues`, `[Option]`, `OptionValue`, `ProductRange`,
`ProductCategory`, `ProductDescription`, `OtherDescription`, `Attribute`,
`AttributeValue`, `BaseAttributeValues`, `ItemOptionValues`, `ItemComponents`,
`PriceMatrix`, `Currency`, `DependentOptionValues`.
SQL functions/procs (bodies **UNKNOWN**): `fnGetListPriceByItem`,
`fnGetListPrice`, `GetProductOptionCount`, `PDMOptionDataReport`.

---

## 6. Business Rules

### Lifecycle & scoping
- **BR-OCD-001** — *Orphaned export.* `OCDExport` is instantiated
  (`ocdThread = new OCDExport()`, SytelineExport.cs:1531) but `initParams()` and
  `execThread()` have **no caller anywhere in the workspace**. The export is dead
  code in the current build; it is documented here for completeness/migration.
- **BR-OCD-002** — Constructor defaults: `_exportDirectory="C:\"`,
  `_paramSeries="CE"`, `_siteId=1`, `_catalogueId=-1`, `_leadtime=99`,
  `_currency="EUR"`, `_effectiveDate="GetUTCDate()"`, `_newformat=true`
  (OCDExport.cs:147–181).
- **BR-OCD-003** — `initParams` derives the export root by truncating
  `exportpath` at the first `\` and writes a human instruction file
  `ocdexport.txt` ("Please compress the export in zip format…", OCDExport.cs:243).
- **BR-OCD-004** — `ocd_version.csv` is a fixed manifest string, written verbatim
  and unconditionally, listing the 12 OCD file types:
  `2.1;OCD_2;1.0.0;20050727;99991231;DE;article,artlongtext,artshorttext,price,property,propertyclass,propertytext,propertyvalue,propvaluetext,relation,relationobj,version;`
  (OCDExport.cs:396–397). Format/date/language `DE` are hardcoded.
- **BR-OCD-005** — Catalogue lead time drives a **synthetic** baseline
  `_leadtime = Catalogue.LeadTime + 5` (OCDExport.cs:266).

### Product-code selection
- **BR-OCD-010** — Export-all (`productCodeId == -1`) enumerates only product
  codes with `Product_Code.OCDExport = 1` at the site (Q-OCD-002). Specific
  product-code mode bypasses that flag (Q-OCD-003).
- **BR-OCD-011** — The main item query runs **twice** per category group: first
  with `[group filter]` blanked (to collect distinct `ProductCategoryId`s and
  names), then with the group predicate substituted for the emit pass
  (OCDExport.cs:884–917, 940–953).

### Item filtering (Q-OCD-009)
- **BR-OCD-012** — Only released items are exported: `Item.Status = 1`. Hardcoded
  item-code exclusions: `Item.Item NOT LIKE 'AE9%'`, `NOT LIKE 'AU9%'`,
  `NOT LIKE 'CJ1%F'` (OCDExport.cs:876–878).
- **BR-OCD-013** — Catalogue-specific filter: when `_catalogueId == 258`, add
  `AND item.baseprice is not null` (OCDExport.cs:880).
- **BR-OCD-033** — Sort override: when `_catalogueId == 264 AND productCodeId == 776`,
  order by `ProductCategoryId, Product.IsSuperProduct, Item` instead of the
  default `ProductCategoryId, Item` (OCDExport.cs:882).
- **BR-OCD-014** — Only option values in `CatalogueOptionValues` for the catalogue
  are eligible (whitelist `arrayList` from Q-OCD-004); the surcharge query filters
  `optval.OptionValueId IN (-1, <whitelist>)` (OCDExport.cs:2508 / 2431).

### Series / article-code transforms (HM-specific)
- **BR-OCD-020** — `_paramSeries` = last 2 characters of `Product_Code`
  (OCDExport.cs). Series-conditional logic runs only for the whitelist
  `AE, AV, CE, CN, CP, MR, RY, OA, LF, RV, IV` (OCDExport.cs:975).
- **BR-OCD-021** — Attribute names become property names prefixed `G` and stripped
  to `[A-Za-z0-9]` via `removeNonAlphaStrict` (OCDExport.cs:749, 1738). A `GType`
  attribute is renamed `G<series>Type` (OCDExport.cs:1740).
- **BR-OCD-022** — For items starting `AU1`/`AE7`, an `_ARMS`/tilt/arm suffix is
  synthesized from characters at positions 4 and 5 of the code
  (`1→NOTILT, 2→LTR, 3→LTRFWD`; `N→_NOARMS, P→_FIXARMS, H→_ADJ, A→_FADJ`), padded
  with `"xxxxxxxx"` to avoid index overflow (OCDExport.cs:983–1010).
- **BR-OCD-023** — `DTW1/DTW4/DTW5` codes are rewritten to product handles
  `EWTableSH/EWTableOcc/EWTableFT` with a positional suffix (6 or 8 chars
  depending on `DTW*CP./DTW*CX.` prefixes) (OCDExport.cs:1590–1614).
- **BR-OCD-024** — `AERONTSKCHR_A/_B/_C` article ids have the `_A/_B/_C`
  suffix stripped back to `AERONTSKCHR` (OCDExport.cs:1690–1704).
- **BR-OCD-025** — Non-series products fall back to `Product` with `.` removed
  (OCDExport.cs:1608, 1852).
- **BR-OCD-034** — `AU900*` items force a shorter article-code truncation length
  `num49 = 6` (OCDExport.cs). Per-series truncation lengths: AE=10, MR=8, CE=9,
  AV=9, CP=6, RY=7, CN=7, LF=10, IV=15, RV=12, OA=11 (OCDExport.cs:2648–2695).

### Article & go_* metadata emission
- **BR-OCD-026** — Every article emits `ocdArticle(articleID, "C", "HM", series,
  shortTextIdx, longTextIdx, "", "0", "C62", scheme)`. Manufacturer is hardcoded
  `"HM"`, article type `"C"`, order unit `"C62"`, fast-supply `"0"`
  (OCDExport.cs:1626/1630). In **old** format the series id is suffixed with
  `_leadtime`.
- **BR-OCD-027** — `metaArticles` (`go_articles`) manufacturer is hardcoded
  `"hmx"`; productLine = `series.ToLower()` (old format appends `_leadtime`)
  (OCDExport.cs:1846/1849).
- **BR-OCD-028** — Four constant `go_types` functional properties are added per
  product: `GType=MT_<code>`, `GMode=OCD`, `GSetup=17`, `GAlign=NNN`
  (OCDExport.cs:1852–1855).
- **BR-OCD-029** — `addMetaType` dedups by `product|propertyName`; when
  `overrideZeroFlag`, `propertyMode` is forced to `0`. `GType` override is applied
  unless series `AV` (with per-series carve-outs for RY/SETUTSKCHR and
  OA/SWOOPCHR/SWOOPOTTOMAN, and forced for KIT/SAYLTSKCHR)
  (OCDExport.cs:767–784, 1746–1770).

### Descriptions & text
- **BR-OCD-035** — Short descriptions are deduped in `_shortDescriptions`; the
  index+1 is used as `shortTextID`. `getShortDesc` extracts the substring between
  the first two `>` markers, replacing `>` with a space (OCDExport.cs:688–701, 703).
- **BR-OCD-036** — DE/NL descriptions fall back to the English short description
  when the localized `ProductDescription` row is NULL (Q-OCD-009 `CASE WHEN … IS
  NULL`).
- **BR-OCD-037** — Long-text rows are split on `>` markers into multiple
  `ocd_artlongtext` lines with incrementing `lineNr`; the writer inserts extra
  `ocdArtDesc` rows on the fly (OCDExport.cs:520–585).
- **BR-OCD-038** — Text is emitted quoted with embedded quotes doubled:
  `"\"" + textline.Replace("\"","\"\"") + "\""` (ocdArtDesc.cs getAllProperties).
- **BR-OCD-039** — `.sr` symbol-resource files: the first `metaDescriptionData`
  element is the filename `<series.ToLower()>[<leadtime>]_<lang>.sr`; subsequent
  elements are `@KEY=value` translation lines. `.sr` files are written in
  **Windows-1252** encoding (`Encoding.GetEncoding(1252)`), then the `.csv`
  extension is stripped by rename (OCDExport.cs:412, 640–648, 1640–1648).

### Property model (from PDMOptionDataReport)
- **BR-OCD-015** — Only `Status == 1` (ACT) option rows are processed. Status
  codes: 0=URL, 1=ACT, 2=OBS, 3=HLD (OCDExport.cs:2646).
- **BR-OCD-016** — Order codes containing `#` are **dropped** everywhere they are
  tested (`OrderCodeValue2.IndexOf("#") == -1`), e.g. OCDExport.cs:1898, 1908.
- **BR-OCD-017** — The literal order-code value `"C7"` is excluded from property
  emission (`arrayList25.Add("C7")` guard, OCDExport.cs:2652–2653).
- **BR-OCD-018** — Property-value `valueFrom` = `OrderCodeValue2` with spaces
  replaced by underscores; comparison op `EQ`; `isDefault` derived from the
  report (OCDExport.cs:2126).
- **BR-OCD-019** — Fabric handling: `LF_SEATTYPE` gets a special two-value
  property (`F`/`A`) with `ocdArtBase` references; `IsFabric` from the report
  ranks fabric type (>0) and drives the `_FS`/`_AS` fabric-set property classes
  (OCDExport.cs:1973–1995, 2900+).
- **BR-OCD-021b** — Property/property-value description indices are resolved
  against `_propertyDescriptions` / `_propvalueDescriptions` (deduped lists);
  index+1 is the emitted `textID` (OCDExport.cs:1984, 2126, etc.).
- **BR-OCD-052** — Dedup guards use string keys: `_propertyClassData`,
  `_propertyData`, `_propertyValueData`, `_artBaseData`, `_codeSchemeData`,
  `ocdPriceAdded`, `metaTypesAdded` all prevent duplicate rows
  (OCDExport.cs:703–793, and `_..Data.Contains(...)` guards throughout).

### LEADTIME synthesis
- **BR-OCD-030** — A synthetic `LEADTIME` property class + `ARTICLECODE` and
  `LEADTIME` properties are injected per article, with description "Lead time"
  (DE "Lieferprogramm", NL "Leveringstermijn") (OCDExport.cs:2372–2404).
- **BR-OCD-031** — Lead-time value list: `{45,25,15}` hardcoded when
  `_catalogueId == 4`; otherwise `Catalogue.LeadTime + 5` (Q-OCD-018). The
  property-value position is `floor(firstDigit/2)+1` (OCDExport.cs:2308–2400).
- **BR-OCD-032** — New-format lead-time **tables** (`t_lt_<key>_tbl.csv`) map
  each article code / option value to a lead-time band by testing membership in
  the cat-57 (`arrayList4/5`) and cat-58 (`arrayList2/3`) reference sets
  (OCDExport.cs:2334–2370). `COL_LEADTIME;45` is string-replaced with the band's
  actual days.
- **BR-OCD-031b** — Old format instead emits a single `<leadtime>_DAY` property
  class with one value (OCDExport.cs:2411–2421).

### Prices
- **BR-OCD-040** — Base price: each article emits
  `ocdPrice(articleID, "", "GS", "B", "", "", ListPrice, "1", currency,
  "20090303", "99991231")`. `dateFrom`/`dateTo` are hardcoded 2009-03-03 →
  9999-12-31 (OCDExport.cs:1632).
- **BR-OCD-041** — Surcharge price: each priced option value emits
  `ocdPrice("*", varcond, "GS", "X", "", "", IncList, "1", currency,
  "20090303", "99991231")` (OCDExport.cs:2714). Rows with blank `IncList` are
  skipped (OCDExport.cs:2519).
- **BR-OCD-042** — Price slot is chosen by `Product_Code.BasePriceRef`
  (1→IncrementalPrice, 2→IncrementalPrice2, 3→IncrementalPrice3) inside
  `fnGetListPrice` (Q-OCD-019). List price uses `fnGetListPriceByItem` (Q-OCD-009).
- **BR-OCD-043** — `addOCDPrice` dedups by the full pipe-joined price signature
  (OCDExport.cs:785–793).

### Relations / variant conditions
- **BR-OCD-050** — For each priced value a `$VARCOND` relation is generated:
  `$VARCOND='<varcond>' if <series>_<OPTIONNAME> = '<value>'`, paired with an
  `ocdRelationObj(id, relName, "3", "P")`; the article's `relObjID` is bound to
  the relation block (OCDExport.cs:2762–2763). Relations are deduped by
  name+codeBlock (OCDExport.cs:2735–2745).
- **BR-OCD-051** — Option-name → relation-name mapping: `TYPE` → `COLOUR` unless
  the name contains `PELLICLE` (then `TYPE` is removed). Dependent option values
  (Q-OCD-020) refine the target code (OCDExport.cs:2616–2620).
- **BR-OCD-053** — Variant order-code formatting: an 8-char value is split
  `4_4`; a 10-char value is split `5_5` (insert `_`) (OCDExport.cs:2725–2732).
- **BR-OCD-054** — Uniqueness suffixing: colliding varconds get `~2` (or the last
  numeric digit incremented) appended (OCDExport.cs:2640).
- **BR-OCD-055** — **Hardcoded relation blocks** are appended per series (fixed
  constraint catalogues), e.g.:
  `PC_AE_FINISH_NOT_XT`/`PC_AE_FINISH_XT` (`AE_FINISH <> 'XT'` / `= 'XT'`),
  `PC_RY_FRAMEFINISH_NOT_G1` (`RY_FRAMEFINISH <> 'G1'`),
  `PC_LF_BACKFINISH_*` (G1, SG, DTR, ZK, ZS, 97, 98, BRN),
  `PC_LF_SEATTYPE_A`/`PC_LF_SEATTYPE_F` (OCDExport.cs:2822–2885).
- **BR-OCD-056** — Fabric-set `relObjID` remapping by order-code prefix:
  `8M25/8M23/8M22/8M26/8M10/8M24` and `1A701..1A708` values are pointed at
  specific relation-object offsets (`num58+3..+8`, `+11`, `+12`), differentiated
  by `_FS` vs `_AS` property-class suffix (OCDExport.cs:2900–2990).
- **BR-OCD-057** — When an item has no priced options (`arrayList30.Count == 0`),
  empty placeholder `ocdPrice`, `ocdRelation`, `ocdRelationObj` rows are added
  (OCDExport.cs:2696–2698); the writer drops all-empty rows anyway (BR-OCD-060).

### Serialization / writer loop
- **BR-OCD-058** — Output directory tree per group:
  `...\ocd_export\<CatalogueName>\<ProductCode>\hmx\<groupfilter>\ANY\1\db\`;
  the `ANY\1\db` sub-tree is deleted and recreated each run
  (OCDExport.cs:350–392). `groupfilter` is lower-cased; old format appends
  `_leadtime`.
- **BR-OCD-059** — `go_*` and `.sr` files are redirected out of the `db` folder
  into `hmx\<groupfilter>\1\` (OCDExport.cs:404–406).
- **BR-OCD-060** — A row is skipped if, after removing `;`, spaces, `\r`, `\n`,
  it is empty (OCDExport.cs:610–615). This silently drops the placeholder rows
  from BR-OCD-057.
- **BR-OCD-061** — In new format, lead-time relation rows are appended to
  `ocd_relation.csv` when `leadtimeTables.Count > 0` (OCDExport.cs:618–635).

### Error handling
- **BR-OCD-062** — `initParams`, `startExport`, `writeData`, `execThread`,
  `logMessage`, `addShortDesc` handling all swallow exceptions via
  `try/catch` + `ProjectData.SetProjectError/ClearProjectError`. `initParams`
  and `startExport` surface errors with `Interaction.MsgBox`; `writeData`'s
  catch shows the row/column indices (`[n=…, x=…]`). `logMessage`'s catch is
  silent (OCDExport.cs:236–258, 312–330, 668–685, 3101–3116).
- **BR-OCD-063** — Progress is logged to `ocd_export\OCD_log.txt` (append unless
  `clear`) and mirrored to the `UpdateStatusText` event; export start/complete
  markers are written with timestamps (OCDExport.cs:312–332, 807–3075).

---

## 7. Hidden Logic

- **Dead entry point (critical).** No live caller for `initParams`/`execThread`
  (BR-OCD-001). The whole module runs only if code elsewhere is wired to it — it
  is not in the current build.
- **Hardcoded catalogue IDs** encode business meaning with no lookup:
  `57`/`58` = lead-time reference catalogues (Q-OCD-005..008); `4` = fixed
  lead-time list `{45,25,15}`; `258` = base-price-not-null filter; `264`+`776` =
  special super-product sort. These are magic numbers (BR-OCD-013/031/032/033).
- **Misnamed stored-proc parameter.** `PDMOptionDataReport @cataloguedesc` is
  actually passed the **item code**, not a catalogue description (OCDExport.cs:1891).
- **Late-bound serialization.** `writeData` uses reflection (`NewLateBinding`) so
  any object exposing `fileName`/`getAllProperties`/`Count`/`Item` can be a
  "table". This hides which concrete types flow through and defeats static
  analysis of the output schema.
- **Empty-row suppression** (BR-OCD-060) silently removes placeholder rows and
  any row that collapses to punctuation — meaning some emitted DTOs never reach
  disk.
- **`GetUTCDate()` as a default `effectiveDate`** (constructor) is a raw SQL
  fragment injected into queries, not a bound parameter.
- **`metaDescriptions` class is inert** — no `fileName`, no serializer method; the
  `.sr` content is carried as raw strings, so this class is effectively unused by
  the export path.
- **`_propertyData` is reset twice** (in `resetArrays()` and again at
  OCDExport.cs after array init), and a large number of local `arrayListN`
  variables (up to `arrayList46`) carry the per-item state — a maintenance hazard.
- **Padding trick** `(code + "xxxxxxxx").Substring(...)` is used repeatedly to
  avoid `IndexOutOfRange` on short item codes (BR-OCD-022).

---

## 8. UI Behaviour

- `OCDExport` is a `Form` but its designer surface is trivial: a single
  `Button1` whose `Click` handler is **empty** (OCDExport.cs:3097). The form is
  never `Show()`n via the OCD path.
- Progress feedback is via two events, `UpdateStatusText(sender, text)` and
  `UpdateExportTimer(sender, action)` where `action ∈ {reset, start, stop}`
  (OCDExport.cs:143, 811–815, 3072, 3088). **No host subscribes** to `ocdThread`'s
  events (only `expThread`/`csiThread`/`ofdaThread` are wired in SytelineExport),
  so status output is discarded.
- Terminal user feedback is `Interaction.MsgBox` on completion/error only
  (BR-OCD-062).

---

## 9. Dependencies

**Internal classes:** `ConnectionFactory` (connections), `Global`
(`globalSiteId`), and the DTOs `ocdArticle`, `ocdArtBase`, `ocdArtDesc`,
`ocdProperty`, `ocdPropertyClass`, `ocdPropertyValue`, `ocdPrice`, `ocdRelation`,
`ocdRelationObj`, `ocdCodeScheme`, `codeScheme`, `metaArticles`, `metaTypes`,
`metaProperties`, `metaDescriptions`. Host: `SytelineExport` (holds the field).

**Database objects:** tables in §5.3; SQL functions `fnGetListPriceByItem`,
`fnGetListPrice` and stored procs `GetProductOptionCount`, `PDMOptionDataReport`
(all **UNKNOWN** bodies — not in workspace).

**Framework:** `Microsoft.VisualBasic` runtime (`Conversions`, `Operators`,
`NewLateBinding`, `Interaction`, `ProjectData`, `Versioned`) — confirms VB.NET
origin. `System.Data.SqlClient`, `System.IO` (StreamWriter/DirectoryInfo/FileInfo),
`System.Text.Encoding` (CP1252 for `.sr`).

**Filesystem:** writes under `<exportRoot>\ocd_export\...`; requires create/delete
rights on that tree.

---

## 10. Risks

- **R-1 (Dead code):** the module is unreachable in the current build
  (BR-OCD-001). Any migration must first confirm whether OCD output is still
  required; if so, the whole path needs re-wiring and re-validation.
- **R-2 (SQL injection / correctness):** every query is built by string
  concatenation of `_currency`, `_effectiveDate`, catalogue/product ids, and item
  codes (e.g. Q-OCD-009, Q-OCD-019). `_effectiveDate` is injected as a raw SQL
  expression (`GetUTCDate()`). No parameterization on the dynamic parts.
- **R-3 (Opaque business logic in DB):** `PDMOptionDataReport`,
  `fnGetListPrice(ByItem)`, and `GetProductOptionCount` hold significant rules
  (option selection, pricing, rounding) whose bodies are not in the workspace —
  the property model and prices cannot be fully reproduced without them.
- **R-4 (Pervasive HM hardcoding):** manufacturer `HM`/`hmx`, order unit `C62`,
  scheme constants, catalogue ids 4/57/58/258/264, price dates 2009-03-03,
  series whitelists, per-series truncation lengths, and dozens of literal
  relation blocks (AE_FINISH, RY_FRAMEFINISH, LF_BACKFINISH, LF_SEATTYPE,
  8M*/1A70* remapping) make this single-tenant and brittle. Re-targeting to
  another manufacturer requires rewriting large regions.
- **R-5 (Silent failures):** exceptions are swallowed; empty/placeholder rows are
  suppressed (BR-OCD-060/062). Partial or missing output can occur without a hard
  error, and only `OCD_log.txt` records progress.
- **R-6 (Reflection-based writer):** late-bound serialization (BR-OCD-058) is
  fragile to DTO shape changes and hides the true output schema from tooling.
- **R-7 (PLC override gap):** three separate joins carry the inline comment
  `/* note: this join does not currently honour Item PLC overrides */`
  (Q-OCD-009, Q-OCD-019) — a known correctness caveat in item→product-code
  resolution.
- **R-8 (Filesystem destructive step):** `writeData` deletes and recreates the
  `...\ANY\1\db` subtree each run (BR-OCD-058); an incorrect `_exportDirectory`
  could delete unintended folders.
