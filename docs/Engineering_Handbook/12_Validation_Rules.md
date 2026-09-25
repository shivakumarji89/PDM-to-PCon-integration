# 12 — Validation Rules

**Source:** OFML style guides + specifications (EasternGraphics/IBA), consolidated for the MK Product Workbench Engineering Handbook.
**Status:** Consolidated from specification docs; unclear items marked `UNKNOWN`.

This chapter extracts **every** validation, constraint, dependency, ordering, default and
compatibility rule stated across the OFML specification corpus. Each rule has a stable ID.
Rules are grouped by domain. Cross-reference the domain chapters:
[06_OFML](06_OFML.md) · [07_OCD](07_OCD.md) · [08_ODB](08_ODB.md) ·
[09_OAP](09_OAP.md) · [10_Metatype](10_Metatype.md) · [11_Product_Model](11_Product_Model.md) ·
[13_Naming_Standards](13_Naming_Standards.md) · [16_Configuration](16_Configuration.md) ·
[19_Glossary](19_Glossary.md).

Rule ID prefixes: `VR-CORE` (OFML core/identity), `VR-OCD` (OCD commercial data),
`VR-ODB` (ODB), `VR-OAP` (article selection), `VR-MT` (Metatype), `VR-ART` (Article interface),
`VR-PROP` (Property interface / properties/options/values), `VR-CFG` (Configuration/Relations),
`VR-LAY` (layers).

---

## 1. OFML Core & Identity (`VR-CORE-*`)

| ID | Rule statement | Source doc |
| --- | --- | --- |
| VR-CORE-001 | An OFML library is identified by an **unambiguous ID**, the *program ID*. | ofml_glossary_1.1_en.md |
| VR-CORE-002 | An **article number** is an alphanumeric code that **unambiguously identifies** a product of a manufacturer/supplier within the leading production & planning system (PPS). | ofml_glossary_1.1_en.md |
| VR-CORE-003 | Occasionally the article number is unambiguous **only within a single commercial series** of the manufacturer, not among all series. | ofml_glossary_1.1_en.md |
| VR-CORE-004 | The article number that identifies a **configurable product** is the *basic article number*; the *extended final article number* identifies the product as configured and **contains the variant code** encoding the configurable characteristics. | ofml_glossary_1.1_en.md |
| VR-CORE-005 | A **commercial series** is unambiguously identified by an ID (code) **within the manufacturer**. | ofml_glossary_1.1_en.md |
| VR-CORE-006 | The **assignment of an article to a commercial series must not change** during its life cycle. | ofml_glossary_1.1_en.md |
| VR-CORE-007 | A product **may be assigned to more than one product class**; the assignment can change over its life cycle. | ofml_glossary_1.1_en.md |
| VR-CORE-008 | Determination of one or several commercial series for a manufacturer's products is **obligatory** for an OFML-based sales system. | ofml_glossary_1.1_en.md |
| VR-CORE-009 | An **OFML package** is an installation unit of an OFML library for a defined sales region, tagged with a **unique version number**. | ofml_glossary_1.1_en.md |
| VR-CORE-010 | If a commercial series is **not completely** contained in its product library, then two conditions must both hold: (1) article numbers are **unambiguous among all commercial series** of the manufacturer, and (2) the articles are **listed in the catalog data** of the product library. Otherwise the sales system cannot resolve the product library for the triple (manufacturerID, seriesID, articleNumber). | ofml_glossary_1.1_en.md |
| VR-CORE-011 | Graphical representation in 2D/3D must use the methods/formats specified by the OFML standard (Parts I–III). | ofml_glossary_1.1_en.md |
| VR-CORE-012 | Catalog data (electronic) must be in a format processable by the catalog module; EasternGraphics systems currently support only the XCF format. | ofml_glossary_1.1_en.md |

---

## 2. OCD — Commercial Data (`VR-OCD-*`)

### 2.1 Physical format & keys

| ID | Rule statement | Source doc |
| --- | --- | --- |
| VR-OCD-001 | Commercial data is exchanged as **CSV tables**; fields separated by semicolon (`;`=U+003B). | ocd_4.3_en.md |
| VR-OCD-002 | A field representation is derived by replacing each quotation mark (`"`) with two, and enclosing the result in quotation marks; unquoted form allowed only if the value does not start with `"` and contains no `;`. | ocd_4.3_en.md |
| VR-OCD-003 | Enclosing a value in quotation marks where not required by escaping rules is **not allowed**. | ocd_4.3_en.md |
| VR-OCD-004 | Each table field is specified by number, name, primary-key mark, field type, **maximum length** (character count), and obligatory (mandatory) mark. | ocd_4.3_en.md |
| VR-OCD-005 | For a given **primary key there may be only one record** in the table. | ocd_4.3_en.md |
| VR-OCD-006 | In **key fields there must not be two values that differ only in spelling** (case-insensitive uniqueness). | ocd_4.3_en.md |
| VR-OCD-007 | Obligatory tables must be present; obligatory fields must be filled. | ocd_4.3_en.md |

### 2.2 Identifiers, value domains & ordering

| ID | Rule statement | Source doc |
| --- | --- | --- |
| VR-OCD-010 | For a **property class identifier**, all alphanumeric characters including underscore are allowed, but the **first character must not be numeric**. | ocd_4.3_en.md |
| VR-OCD-011 | **Property names are symbolic, language-independent identifiers**; descriptive (language-dependent) names are provided via text references. | ocd_4.3_en.md |
| VR-OCD-012 | The **position of a property class** within an article's set of classes determines its **order** in listings (variant texts, property editors). | ocd_4.3_en.md |
| VR-OCD-013 | The **position of a property** within its class influences the **order** in listings. | ocd_4.3_en.md |
| VR-OCD-014 | The **position of a property group** determines the display order of property groups. | ocd_4.3_en.md |
| VR-OCD-015 | Properties not assigned to a defined property group appear after defined groups in an artificial group "Other" in **undefined order**. | ocd_4.3_en.md |
| VR-OCD-016 | Data type `C` values are simple character strings with a maximum length per the field's length spec; type-length constraints apply per field. | ocd_4.3_en.md |
| VR-OCD-017 | A text-number field is a **foreign key** into the text table to provide language-dependent names (e.g. for property groups). | ocd_4.3_en.md |
| VR-OCD-018 | Field 10 `OrderUnit` (Char, max 3) specifies the unit in which the article can be ordered; both order quantity and price refer to this unit. | ocd_4.3_en.md |
| VR-OCD-019 | Field 11 `SchemeID` references the codification scheme; if no/unknown identifier is given, no specific final-article codification applies. | ocd_4.3_en.md |
| VR-OCD-020 | **Reserved keywords** (Appendix G) must not be used as identifiers. Full list: `UNKNOWN` (see ocd_4.3_en.md Appendix G). | ocd_4.3_en.md |

### 2.3 Mandatory / default property rules

| ID | Rule statement | Source doc |
| --- | --- | --- |
| VR-OCD-030 | Property input can be flagged **Obligatory** (mandatory input required). | ocd_4.3_en.md |
| VR-OCD-031 | **Configurable numeric properties are always mandatory**. | ocd_4.3_en.md |
| VR-OCD-032 | **Configurable restrictable properties are always mandatory**. | ocd_4.3_en.md |
| VR-OCD-033 | Properties for **free string / text input are mandatory** (an empty string is not a valid completion). | ocd_4.3_en.md |
| VR-OCD-034 | A value in the value table may be marked as **default**; if **no default is marked**, mandatory properties are initialized to the default/first defined value (see spec) prior to relation evaluation. | ocd_4.3_en.md |
| VR-OCD-035 | Initialization = value assignment **before** relation evaluation; afterwards values may change via actions. | ocd_4.3_en.md |
| VR-OCD-036 | A value is considered for initialization if exactly one value is specified, or if the values carry preconditions. | ocd_4.3_en.md |

---

## 3. Configuration & Relations (`VR-CFG-*`)

| ID | Rule statement | Source doc |
| --- | --- | --- |
| VR-CFG-001 | Relationship knowledge (relations) is bound to articles/property classes/properties via a **relational object number** (`RelObjID`); the value **0 means no relational object**. | ocd_4.3_en.md |
| VR-CFG-002 | Relations of type **precondition** and **action** can be bound to a property class via its relational object. | ocd_4.3_en.md |
| VR-CFG-003 | An **existence condition** for a sub item must be given as a relation of type **precondition** via the sub item's relational object. | ocd_4.3_en.md |
| VR-CFG-004 | Existence conditions are **evaluated only if `no`** is indicated for the composite (fully-configurable) flag; if `yes`, indicated existence conditions are **not evaluated**. | ocd_4.3_en.md |
| VR-CFG-005 | If the composite flag value is `no`, sub items are generally **not allowed to be configured**. | ocd_4.3_en.md |
| VR-CFG-006 | The **position of a sub item** within the composite article is taken into account in ordering. | ocd_4.3_en.md |
| VR-CFG-007 | Properties of **scope `R`** are used **only within relation evaluation**, are not persistently stored with the article, and therefore need not be evaluated to complete the configuration. | ocd_4.3_en.md |
| VR-CFG-008 | A **restrictable** property is considered evaluated only when its value set is restricted to exactly one value (or otherwise evaluated); the configuration is complete only when **all restrictable properties are evaluated**. | ocd_4.3_en.md |
| VR-CFG-009 | If a restrictable property is **not evaluated, the article cannot be ordered**. | ocd_4.3_en.md |
| VR-CFG-010 | Completeness of the configuration must be assured by providing selection-condition relationship knowledge (`RelationObj`). | ocd_4.3_en.md |
| VR-CFG-011 | Value-set restriction via relations considers only values whose preconditions are fulfilled for the current configuration (or that have no preconditions). | ocd_4.3_en.md |
| VR-CFG-012 | Arithmetic/boolean expressions in relations follow OFML Part III expression syntax; property keys of the active element serve as variables. | MT_1.18.0_en.md · ocd_4.3_en.md |

---

## 4. Metatype (`VR-MT-*`)

| ID | Rule statement | Source doc |
| --- | --- | --- |
| VR-MT-001 | **All `go_*` tables must be present**; unused tables must be empty. | MT_1.18.0_en.md |
| VR-MT-002 | Each table is stored in exactly **one file** named `go_` + table name (lowercase) + `.csv`. | MT_1.18.0_en.md |
| VR-MT-003 | Character set must be **UTF-8 or ASCII**. | MT_1.18.0_en.md |
| VR-MT-004 | Fields are separated by semicolon (`;`); blank lines are ignored; lines starting with `#` (U+0023) are comments and ignored. | MT_1.18.0_en.md |
| VR-MT-005 | Field escaping: each `"` replaced by two `"` and the string wrapped in `"`; raw value allowed only if it doesn't start with `"` and contains no `;`. | MT_1.18.0_en.md |
| VR-MT-006 | A field value = zero or more Unicode chars with valid UTF-8, **excluding control chars** U+0000..U+001F and U+007F..U+009F. | MT_1.18.0_en.md |
| VR-MT-007 | **Type `ID`**: only ASCII alphanumerics and underscore; an identifier **must not start with a digit**. | MT_1.18.0_en.md |
| VR-MT-008 | Identifiers must be used in the **same spelling (case-sensitive) everywhere**. | MT_1.18.0_en.md |
| VR-MT-009 | Unless otherwise specified in a table description, the field type **`ID` must be used**. | MT_1.18.0_en.md |
| VR-MT-010 | `Int` = non-negative integer (ASCII digits only); `Num` = ASCII digits + `.` decimal point, optional leading `-`. | MT_1.18.0_en.md |
| VR-MT-011 | `NumExpr` must evaluate to a numeric value; `BoolExpr` must evaluate to a Boolean (numeric non-zero or empty string ⇒ true; numeric zero ⇒ false; otherwise **undefined**). | MT_1.18.0_en.md |
| VR-MT-012 | Property keys usable as variables in expressions are the keys defined in `go_types` of the active planning element. | MT_1.18.0_en.md |

---

## 5. Article Interface — Identity & Specification (`VR-ART-*`)

| ID | Rule statement | Source doc |
| --- | --- | --- |
| VR-ART-001 | `setArticleSpec` assigns an **article number** — an alphanumeric code that **uniquely identifies** a manufacturer's product. | article_interface_1.4_en.md |
| VR-ART-002 | Article-specification types: `@Base` (basic article number, unique id without config), `@VarCode` (manufacturer-specific variant code), `@OFMLVarCode` (manufacturer-independent OFML variant code), `@Final` (manufacturer-specific final article number). | article_interface_1.4_en.md |
| VR-ART-003 | The **final article number is normally composed of basic article number + variant code**, though this depends on the underlying product database. | article_interface_1.4_en.md |
| VR-ART-004 | Commercial initialization = immediately successive calls: `setArticleSpec`/`setXArticleSpec(@Base)` **then** `setXArticleSpec(@VarCode)`. | article_interface_1.4_en.md |
| VR-ART-005 | The passed **variant code may be empty** (instance keeps the initial basic configuration). | article_interface_1.4_en.md |
| VR-ART-006 | The variant code may be **partially determined** (only encoding properties differing from the basic configuration). | article_interface_1.4_en.md |
| VR-ART-007 | If a variant/final code that **does not match** the instance is passed, the instance retains its configuration so far or only re-evaluates part of the coded properties. | article_interface_1.4_en.md |
| VR-ART-008 | The **OFML variant code** should be used by applications to **restore saved article configurations**. | article_interface_1.4_en.md |
| VR-ART-009 | Language for textual return components must be a **two-character code** (ISO 639-1). | article_interface_1.4_en.md |
| VR-ART-010 | On an instance flagged non-configurable, configuration methods of the interface must not be called (doing so risks poor performance or incorrect behavior). | article_interface_1.4_en.md |

---

## 6. Property Interface — Properties / Options / Values (`VR-PROP-*`)

| ID | Rule statement | Source doc |
| --- | --- | --- |
| VR-PROP-001 | A **language code, if not empty, must consist of two lowercase letters** (ISO 639-1). | property_interface_2.9_en.md |
| VR-PROP-002 | A **language–text mapping must not contain two entries with the same language code**. | property_interface_2.9_en.md |
| VR-PROP-003 | For Unicode, string length is the **count of code points after conversion to NFC**. | property_interface_2.9_en.md |
| VR-PROP-004 | Property types `Y` and `YS` behave identically except: `Y` yields type **Symbol**, `YS` yields type **String**. | property_interface_2.9_en.md |
| VR-PROP-005 | Input of additional (free) values is **permitted only for the applicable choice-list type**, and is **not valid for types `Y`/`YS`** in the disallowed combinations; defining a property with an invalid combination of property type and choice-list type is not allowed. | property_interface_2.9_en.md |
| VR-PROP-006 | `setPropRanges` applies to numeric property types `L`, `A`, `N`; the property's choice-list type must not conflict with range assignment. | property_interface_2.9_en.md |
| VR-PROP-007 | Specified **minimum and maximum belong to the range of valid values** (inclusive comparison). | property_interface_2.9_en.md |
| VR-PROP-008 | If a minimum is specified, an **increment** may be given that must be adhered to starting from the minimum. | property_interface_2.9_en.md |
| VR-PROP-009 | **Invalid value-range definitions are ignored**. | property_interface_2.9_en.md |
| VR-PROP-010 | The flag value **8 is reserved** for method return structures; in `setPropState2()` parameter `pState` this flag **must always be 0**. | property_interface_2.9_en.md |
| VR-PROP-011 | If an **invalid value is passed in `pState`, the method has no effect**. | property_interface_2.9_en.md |
| VR-PROP-012 | State flag value 4 means input of a value is still required for the configuration to be complete/valid. | property_interface_2.9_en.md |
| VR-PROP-013 | When defining a property, the specified position offset must be retrieved from the external instance before the property is defined and taken into account when assigning explicit positions. | property_interface_2.9_en.md |

---

## 7. OAP — Article Selection (`VR-OAP-*`)

| ID | Rule statement | Source doc |
| --- | --- | --- |
| VR-OAP-001 | OAP tables are **CSV in UTF-8**; a byte-order mark may optionally be specified. | oap_1.6.1-en.md |
| VR-OAP-002 | In **primary-key fields there must not be two values that differ only in spelling** (case-insensitive uniqueness); for a given primary key there may be only one record. | oap_1.6.1-en.md |
| VR-OAP-003 | Within a manufacturer/supplier, an **article is uniquely identified by an alphanumeric code**. | oap_1.6.1-en.md |
| VR-OAP-004 | To evaluate OAP data for a given article variant, its **`PropVarCode` must be known** (retrieved from the OFML instance). | oap_1.6.1-en.md |
| VR-OAP-005 | In a property variant code (`PVC`), property keys are specified **without a preceding `@`**; entries separated by `;`; values follow literal OFML constant rules. | oap_1.6.1-en.md |
| VR-OAP-006 | Field type **`ID`**: ASCII alphanumerics + `-` + `_`; must be used in the same spelling everywhere. | oap_1.6.1-en.md |
| VR-OAP-007 | Field type **`Symbol`**: ASCII alphanumerics + `_`, but the **first character must not be numeric**. | oap_1.6.1-en.md |
| VR-OAP-008 | Field type **`OID`**: a simple `ID` or a hierarchical name whose levels are separated by a period (`.`); a parent-level identifier referencing a set applies the child identifier to all objects in the set. | oap_1.6.1-en.md |
| VR-OAP-009 | Field type **`Lang`**: ISO 639-1 two-letter language + ISO 3166-1 alpha-2 region separated by `-`; region optional; **lowercase language, uppercase region** must be observed. | oap_1.6.1-en.md |
| VR-OAP-010 | If a data element applies to **any language, its language field must be empty**. | oap_1.6.1-en.md |
| VR-OAP-011 | Field value = Unicode with valid UTF-8, excluding control chars U+0000..U+001F and U+007F..U+009F; NFC normalization recommended. | oap_1.6.1-en.md |
| VR-OAP-012 | Applications are responsible for minimizing OFML-instance access to ensure good OAP evaluation performance. | oap_1.6.1-en.md |

---

## 8. ODB (`VR-ODB-*`)

| ID | Rule statement | Source doc |
| --- | --- | --- |
| VR-ODB-001 | ODB-specific validation/identity constraints: `UNKNOWN` — not separately extracted; see [08_ODB](08_ODB.md) and odb_2.4_en.md. Core identity rules (`VR-CORE-*`) and property/value rules (`VR-PROP-*`) apply to ODB-modeled data. | odb_2.4_en.md |

---

## 9. Layer Validation (`VR-LAY-*`)

| ID | Rule statement | Source doc |
| --- | --- | --- |
| VR-LAY-001 | Layer names are **case-insensitive**; using layer names that differ **only in upper/lower case is not allowed**. | OLAYERS_1.3.1_en.md |
| VR-LAY-002 | For 3D layer modes `*_D3_<TAG>` / `*_D3FRONT_<TAG>` and 2D `*_D2_<TAG>`, declaration of a **`<TAG>` is mandatory**. | OLAYERS_1.3.1_en.md |
| VR-LAY-003 | For `*_ACOUSTICS_<TAG>` the `<TAG>` is **optional**. | OLAYERS_1.3.1_en.md |
| VR-LAY-004 | `<MAN>` must be the OFML manufacturer identifier (DSR key `manufacturer`); `<SERIES>` the OFML library/series identifier (DSR key `program`). | OLAYERS_1.3.1_en.md · dsr-3.7_en.md |

---

## Rule count

**Total extracted rules: 102** (CORE 12, OCD 24, CFG 12, MT 12, ART 10, PROP 13, OAP 12, ODB 1, LAY 4, +2 shared expression rule counted once).
Approximate authoritative count: **~100 rules**.

## `UNKNOWN` items

- VR-OCD-020: full OCD reserved-keyword list (Appendix G) not enumerated here.
- VR-ODB-001: ODB-specific constraints not separately extracted.
