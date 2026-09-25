# 15 — File Formats

**Source:** OFML specifications, style guides & application notes (EasternGraphics/IBA), consolidated for the MK Product Workbench Engineering Handbook.
**Status:** Consolidated from specification docs; unclear items marked `UNKNOWN`.

This chapter catalogues **every physical file / data format and table structure** across
the OFML ecosystem. It is the format reference behind the domain chapters:
[06_OFML](06_OFML.md) · [07_OCD](07_OCD.md) · [08_ODB](08_ODB.md) ·
[09_OAP](09_OAP.md) · [10_Metatype](10_Metatype.md) · [13_Naming_Standards](13_Naming_Standards.md) ·
[19_Glossary](19_Glossary.md). Generation is described in [14_Generation_Process](14_Generation_Process.md).

---

## 1. The general OFML CSV convention

OCD, ODB, OAP and Metatype/GO all share one physical exchange model: **one table per
`.csv` file**, with a domain-specific lowercase prefix. The rules differ only in
**character set** and a few lexical details.

| Rule | OCD (`ocd_`) | ODB (`odb_`)¹ | OAP (`oap_`) | Metatype (`go_`) | Source doc |
|------|------|------|------|------|------|
| File name | `ocd_<table>.csv` | `odb_<table>.csv`¹ | `oap_<table>.csv` | `go_<table>.csv` | ocd_4.3, odb_2.4, oap_1.6.1, MT_1.18.0 |
| Table name | lowercase | lowercase | lowercase | lowercase | all |
| One record | one line, `\n` (or `CR+LF`) | one line | one line | one line | all |
| Field separator | `;` (semicolon `U+003B`) | `;` | `;` | `;` | all |
| Comment lines | start with `#` | start with `#` | start with `#` | start with `#` | all |
| Blank lines | ignored | ignored | ignored | ignored | all |
| Character set | **ISO-8859-1 (Latin-1)** | **ISO-8859-1** | **UTF-8** (optional BOM) | **UTF-8 or ASCII** | ocd/odb/oap/MT |
| Quoting | field with `;` wrapped in `"`; `""` = literal `"` | same | same | same | all |

¹ The ODB 2.4 text literally states the prefix `ocd_` for its table files — this is a
known **spec copy-paste error**; ODB tables conventionally use the `odb_` prefix. Marked
`UNKNOWN` where the authoritative prefix cannot be confirmed from the text alone.

### 1.1 Field data types

| Domain | Types | Notes | Source doc |
|--------|-------|-------|------------|
| OCD | `Char`, `Num`, `Bool` (`1`/`0`), `Date` (`YYYYMMDD`) | Each field spec: Number, Name, Key?, Type, Max length, Obligatory? | ocd_4.3 §1 |
| Metatype | `ID`, `ID_List`, `Text`, `Char`, `Int`, `Num`, `NumExpr`, `BoolExpr` | `ID` = ASCII alnum + `_`, not starting with a digit; expressions follow OFML Part III | MT_1.18.0 §2 |
| OAP | scalars, `NumTripel`, expressions (see App. A of oap) | expression grammar defined in oap_1.6.1 App. A/B | oap_1.6.1 §3 |
| ODB | names, levels, flags, offsets/rotations/scales, `ctor`, `attrib` | table-column expressions in **Reverse Polish Notation** | odb_2.4 §1 |

### 1.2 Units

OCD unit fields follow **openTRANS / UN/ECE Recommendation 20 Common Code** (e.g. `C62`
piece, `MTR` metre, `MTK` m², `KGM` kg). See [13_Naming_Standards](13_Naming_Standards.md).

---

## 2. OCD tables (`ocd_*.csv`) — OFML Part IV, commercial data

Physical format: ISO-8859-1 CSV, one file per table. Full field-level detail is in
[07_OCD](07_OCD.md); configuration semantics in [16_Configuration](16_Configuration.md).

| Format/Table | Purpose | Structure / key columns | Domain doc |
|--------------|---------|--------------------------|------------|
| `Article` | Master table of all articles (root) | **ArticleID**, ArticleType (`P`/`C`/`CS`), ManufacturerID, SeriesID, ShortTextID, RelObjID, SchemeID | ocd_4.3 §2.2 |
| `ArticleIdentification` | Extra ID numbers per article/variant | **ArticleID**, **VariantCode**, SchemeID, IdentKey | ocd_4.3 §2.3 |
| `Classification` / `ClassificationData` | Classify articles (eCl@ss, UNSPSC, manufacturer) | **ArticleID**, **System**, ClassID | ocd_4.3 §2.4 |
| `Packaging` | Packaging dims / weights / volumes (variant = delta) | **ArticleID**, **Variantcondition**, W/H/D, Volume, TaraWeight, NetWeight, PackUnits | ocd_4.3 §2.5 |
| `Composite` | General attributes of composite articles | **CompositeID**, IsFixedSet, Configurable, PriceMode, BasketMode, TextMode | ocd_4.3 §2.6 |
| `BillOfItems` | Sub-items of composite articles | **CompositeID**, **Position**, ItemID, RelObjID, Quantity, QuantUnit | ocd_4.3 §2.7 |
| `PropertyClass` | Property classes assigned to articles | **ArticleID**, **Position**, Name, TextID, RelObjID | ocd_4.3 §2.8 |
| `Property` | Properties of each class | **PropertyClass**, **PropertyName**, Type, Digits, Obligatory, MultiOption, Scope, TxtControl | ocd_4.3 §2.9 |
| `PropertyIdentification` | Extra ID numbers per property | **PropertyClass**, **PropertyName**, IdentKey | ocd_4.3 §2.10 |
| `Article2PropGroup` / `PropertyGroup` | Property groups for the editor | PropGroupID, PropGroupText, Position | ocd_4.3 §2.11 |
| `ArtBase` | Article-specific fixed/allowed values | **ArticleID**, **PropertyClass**, **PropertyName**, PropertyValue | ocd_4.3 §2.12 |
| `PropertyValue` | All possible values per property | **PropertyClass**, **PropertyName**, **Position**, TextID, OpFrom/ValueFrom/OpTo/ValueTo, Raster | ocd_4.3 §2.13 |
| `PropValueIdentification` | Extra ID numbers per value | **PropertyClass**, **PropertyName**, **PropertyValue**, IdentKey | ocd_4.3 §2.14 |
| `RelationObj` | Binds relations to relational objects | **RelObjID**, **Position**, RelName, Type, Domain | ocd_4.3 §2.15 |
| `Relation` | Relationship-knowledge code blocks | **RelationName**, **BlockNr**, CodeBlock | ocd_4.3 §2.16 |
| `Price` | Base prices, extra charges, discounts | ArticleID, Variantcondition, Type, PriceValue, Currency, DateFrom/To, ScaleQuantity | ocd_4.3 §2.17 |
| `Rounding` | Rounding rules | **RoundingID**, Type, Precision, Minimum, Maximum, Rule | ocd_4.3 §2.18 |
| `Series` | Commercial-series registration | **SeriesID**, TextID, CatalogFormat, CatalogDir | ocd_4.3 §2.19 |
| Text tables (`ArtShortText`, `ArtLongText`, `PropClassText`, `PropertyText`, `PropValueText`, `PropHintText`, `SeriesText`, `PriceText`, `BillOfItemsText`, `ClassificationText`) | Language-specific texts | **TextID**, Language, LineNr, Textline, TxtControl | ocd_4.3 §2.20 |
| `<name>_tbl` | Value-combination tables (relation knowledge) | LineNr, PropertyName, Value | ocd_4.3 §2.21 |
| `Identification` | Actual additional identification numbers | **EntityID**, **Type**, IdentNr | ocd_4.3 §2.22 |
| `Version` | Format/database version metadata | **FormatVersion**, RelCoding, DataVersion, Region, Tables | ocd_4.3 §2.23 |
| `CodeScheme` | Codification schemes for final article numbers | **SchemeID**, Scheme, VarCodeSep, ValueSep, Trim | ocd_4.3 §2.24 |
| `ArticleTaxes` / `TaxScheme` | Taxation-scheme assignment | ArticleID, TaxID, Country, Region, TaxType, TaxCategory | ocd_4.3 §2.25 |

> Configuration tables (`PropertyClass`, `Property`, `PropertyValue`, `RelationObj`,
> `Relation`) may be **omitted** for text/price-only databases.

### 2.1 Text control (`TxtControl`)

Text processing (bill of items etc.) is steered by the **`TxtControl`** control code in
`Property`/text tables; combined with `PropValueText` it controls how property values are
rendered into forms. See ocd_4.3 §5 and [12_Validation_Rules](12_Validation_Rules.md).
Language sets are declared per `Version` region / language appendices (OCD_1..OCD_4, SAP_LOVC).

---

## 3. ODB tables (`odb_*.csv`) — OFML Part I, geometry & object description

ISO-8859-1 CSV. A run of consecutive rows with the same base ODB name forms an **ODB
block**. Column expressions use **Reverse Polish Notation**. Detail in [08_ODB](08_ODB.md).

| Format/Table | Purpose | Structure / key columns | Domain doc |
|--------------|---------|--------------------------|------------|
| `odb_2d` | 2D geometry primitives per object | odb_name, level, visible, x/y_offs, rot, x/y_scale, ctor, attrib | odb_2.4 §2 |
| `odb_3d` | 3D geometry primitives per object | odb_name, level, visible, x/y/z_offs, x/y/z_rot, x/y_scale, ctor, mat, attrib, link | odb_2.4 §3 |
| `odb_funcs` | User-defined functions used in RPN expressions | name, body | odb_2.4 §5 |
| `odb_layer` | Optional 3D layer definitions | layer_name, attributes | odb_2.4 §6 |
| `odb_attpt` | Attachment points | odb_name, name, select, text_idx, x/y/z_pos, direction, rotation, mode | odb_2.4 §4 |
| `odb_oppattpt` | Opposite / matching attach points | odb_name, select, opposite, direction, att_points | odb_2.4 §4 |
| `odb_stdattpt` | Standard attach-point presets | odb_name, has_stdattpts, prep_stdattpts, stdattpts | odb_2.4 §4 |
| External geometry `.geo` | Complex external geometry referenced by `imp`/`ctor` | binary/record file, `.geo` extension, local coordinate system | odb_2.4 §2.7, §3.6 |

Primitives: `hline`, `vline`, `dline`, `quadrat`, `circle`, `arc`, … (2D) and 3D unit
primitives; attributes include colour, line width, line style, material (`mat`).
**CSG** (Constructive Solid Geometry) combines primitives (odb_2.4 §3.8).

---

## 4. OAP tables (`oap_*.csv`) — OFML Aided Planning

UTF-8 CSV (optional BOM). Field/expression detail in [09_OAP](09_OAP.md); expression
grammar in oap_1.6.1 App. A/B.

| Format/Table | Purpose | Structure / key columns | Domain doc |
|--------------|---------|--------------------------|------------|
| `Type` | OAP planning types | ID, … (oap types) | oap_1.6.1 §4.1 |
| `Article2Type` | Map article → OAP type | Article, Type | oap_1.6.1 §4.1 |
| `Metatype2Type` | Map metatype → OAP type | Metatype, Type | oap_1.6.1 §4.1 |
| `NumTripel` | Named numeric triples (positions/vectors) | ID, x, y, z | oap_1.6.1 §4.2 |
| `Interactor` | Interactive handles in the scene | ID, type, key, condition, pos, image, hint | oap_1.6.1 §4.6 |
| `SymbolDisplay` | Symbol / icon display for interactors | ID, symbol, … | oap_1.6.1 §4.6 |
| `Action` | Actions triggered by interactors/events | ID, condition, action, params | oap_1.6.1 §4.7 |
| `ActionList` | Ordered lists of actions | ID, action refs | oap_1.6.1 §4.8 |
| `PropEdit2` / `PropEditProps` / `PropEditClasses` | Property-editor configuration | ID, property/class refs, layout | oap_1.6.1 §4.8 |
| `Object` | Object definitions (OID hierarchy) | OID (`parent.child`), … | oap_1.6.1 §4.9 |
| `Text` | Language-specific OAP texts | ID, language, text | oap_1.6.1 §4.10 |
| `Image` | Image references | ID, file | oap_1.6.1 §4.11 |
| `Version` | OAP version information | FormatVersion, … | oap_1.6.1 §4.12 |

Companion data-creation guidance: `AppNote_OAP_DataCreation_EN.md`, method reference
`methods4OAP.md`. Style: `OAP-Styleguide_en.md` (see [17_Best_Practices](17_Best_Practices.md)).

---

## 5. Metatype / GO tables (`go_*.csv`) — parametric product model

UTF-8 or ASCII CSV. **All tables must be present**; unused tables should be empty.
Expressions (`NumExpr`/`BoolExpr`) follow OFML Part III and may reference property keys.
Detail in [10_Metatype](10_Metatype.md); GO base library in [06_OFML](06_OFML.md).

| Format/Table | Purpose | Structure / key columns | Domain doc |
|--------------|---------|--------------------------|------------|
| `go_types` | Defines metatypes / instances & their properties | id, name, format, default, mode, filter | MT_1.18.0 §2 |
| `go_freenumeric` | Parametrises free-numeric (`fn`) properties | name, format, minimum, maximum, raster, expr, child, mode | MT_1.18.0 |
| `go_info` | Series-wide settings (e.g. `pindex`, `utf8`) | key, value | MT_1.18.0 |
| `go_texts` | Language-specific texts | key, language, text | MT_1.18.0 |
| `go_inhproperties` | Inherited properties | id, pid, property | MT_1.18.0 |
| `go_propvalues` | Property values with conditions | id, name, value, condition | MT_1.18.0 |
| `go_propclasses` | Property → property-class assignment | id, prop_name, prop_class | MT_1.18.0 |
| `go_nativeproperties` | Native (OCD/OFML) property mapping | id, pid, mode, identifier, value1, value2 | MT_1.18.0 |
| `go_properties` | Map MT property values ↔ OFML variant codes | id, key, name, value, variant_code, variant_value | MT_1.18.0 |
| `go_propmapping` | Property-indexed polymorphism mapping | id, key1…keyN | MT_1.18.0 |
| `go_propindex` | Property-indexed polymorphism index | id, key, value1…valueN | MT_1.18.0 |
| `go_proporder` | Explicit ordering of values | value, number | MT_1.18.0 |
| `go_noproperties` | Properties suppressed from display | key, name | MT_1.18.0 |
| `go_symbolicpropvalue` | Symbolic ↔ numeric value mapping | key, symbol, number | MT_1.18.0 |
| `go_articles` | Article numbers realised by a metatype | id, manufacturer, program, article_nr, prm_set, chprm_set | MT_1.18.0 |
| `go_children` | Child objects & their placement | child_key, manufacturer, program, article_nr, variant, pos, rot, condition | MT_1.18.0 |
| `go_childprops` | Child-controlling properties | key, name, value, child_key | MT_1.18.0 |
| `go_classes` | Class assignment | id, class | MT_1.18.0 |
| `go_childmoving` | Child moving behaviour | id, key, condition, mode, command, parameter | MT_1.18.0 |
| `go_attpt` | Attachment points | id, key, direction, condition, pos, rot_y | MT_1.18.0 |
| `go_attptsorder` | Order of attachment points | key, id, plandir, number | MT_1.18.0 |
| `go_attptgeo` | Attachment-point geometry | key, id, pos, rot_dir, rot, type, arg1..arg3 | MT_1.18.0 |
| `go_setup` | Feature activation / setup | id, key, value | MT_1.18.0 |
| `go_interactors` | Interactors | id, type, key, condition, pos, image, hint | MT_1.18.0 |
| `go_itemplates` | Instantiation templates | id, template, condition, parameter, pos, rot_y | MT_1.18.0 |
| `go_feedback` | Feedback from children | id, ch_artnr, attpt_key, condition, mode, command, parameter | MT_1.18.0 |
| `go_actions` | Action / message rules | id, own_key, foreign_key, direction, condition, action, param_1/2, text | MT_1.18.0 |
| `go_metainfo` | Meta info referenced by GO `AccID` | (accessory/meta records) | GO_1.12.0 §3 |

---

## 6. OMATS material files — materials & PBR

Materials use the **OMATS1** (legacy) and **OMATS2** (Physically Based Rendering) models.
A material = a set of space-separated **key + arguments** parameters (all optional).

| Format | Purpose | Structure | Domain doc |
|--------|---------|-----------|------------|
| Material definition file `.mat` | One complete material per file | parameters separated by end-of-line; filename = last component of the fully-qualified material name, lowercase | omats_2.2 §4 |
| Inline declaration | Material embedded in OFML/ODB | parameters separated by `;`; pure form starts with `$`; **modifier** form = base material name + overriding params | omats_2.2 §4 |
| Textures | Image maps for PBR/real-time | image files (max 4096×4096; recommended 256²–1024²); referenced by fully-qualified name if outside the series data directory | omats_2.2 §2–3 |

Material Type selects the shader and restricts which parameters apply. See
[06_OFML](06_OFML.md) and [18_Design_Principles](18_Design_Principles.md) for real-time vs
photorealistic separation. Older materials are auto-converted to OMATS2 on load.

---

## 7. OLAYERS & tags — layer identifiers

`OLAYERS-TAGS_1.2` is a companion to the OLAYERS specification defining **uniform tag
identifiers** for OFML-compatible layers, grouped by furniture domain.

| Format | Purpose | Structure | Domain doc |
|--------|---------|-----------|------------|
| Layer tags | Standardised layer/geometry tag names | `Group` → `Tag` (e.g. `TB_ATTACH`, `TB_EDGE`, `TB_FRAME`, `TB_INLAY`, `TB_TABLE_TOP`, `TB_TRAVERSE`, `ME_INLAY`) → purpose | OLAYERS-TAGS_1.2 |

Tag naming (prefixes like `TB_` = tables, `ME_` = …) is catalogued in
[13_Naming_Standards](13_Naming_Standards.md). Layer semantics: `OLAYERS_1.3.1_en.md`.

---

## 8. Catalog & basket formats

| Format | Purpose | Structure | Domain doc |
|--------|---------|-----------|------------|
| **XCF** (eXtensible Catalog Format) | Catalog data (article tree, presentation) — *not* commercial data | referenced via `Series.CatalogFormat`/`CatalogDir`; catalog↔product link is by **article number** | ocd_4.3 §1; OAS = OFML Part V |
| **OBX / `.obx`** | Basket / configured-product exchange (cutBuffer) | **XML** produced by the EAI-Server; see §8.1 | example `.obx` files |

### 8.1 OBX (`.obx`) XML basket structure

`.obx` is an **XML cut-buffer / basket** document (root `<cutBuffer>`), used to exchange
configured articles between pCon applications via the EAI-Server.

| Element | Purpose |
|---------|---------|
| `<cutBuffer>` | Root container |
| `<state sessionId=…>` | Session context |
| `<versionInfo vendorKey appKey appVersion bskXmlVersion>` | Producing app + basket-XML version (e.g. `EAI-Server`, `bskXmlVersion='1.8.10'`) |
| `<items>` → `<bskArticle basketId itemType updateState>` | One configured basket article |
| `<manufacturer id>` / `<series id>` | Manufacturer & commercial series (multi-language `<name>`) |
| `<artNr type='base'\|'final'\|'varcode'\|'ofmlvarcode'>` | Article numbers: base, final, manufacturer variant code, and OFML variant code (`Class.Prop=value;…`) |
| `<description type='short'\|'long'\|'features'>` | Multi-language texts (`<text lang=…>`) |
| price / `pdInfo` components | Price and product-data components `UNKNOWN` (schema not in the spec corpus) |

> Very large sample baskets (e.g. `snapper_CLOUD (3).obx`, >50 MB) could not be fully
> read → detailed element inventory beyond the above is `UNKNOWN`.

---

## 9. Format ↔ pCon-application compatibility

`AN-2023-01_OFML_Support_in_pCon_Applications.md` tabulates which OCD/XCF/OAP/MT/DSR
versions each pCon release supports (e.g. OCD 2.1→5.0, MT 1.18, DSR 3.3→3.7). Use it to
choose target format versions — see [17_Best_Practices](17_Best_Practices.md) §versioning.

---

## 10. `UNKNOWN` items

- ODB table file prefix: spec text says `ocd_`; authoritative value likely `odb_` — `UNKNOWN`.
- OBX price / `pdInfo` component schema — `UNKNOWN` (not in the spec corpus).
- Full element inventory of very large `.obx` samples — `UNKNOWN` (file too large to read).
