# 06 — OFML: The Office Furniture Modelling Language

**Source:** OFML specifications (EasternGraphics/IBA), consolidated for the MK Product Workbench Engineering Handbook.
**Status:** Consolidated from specification docs; unclear items marked `UNKNOWN`.

---

## 1. What OFML Is

**OFML** = **O**ffice **F**urniture **M**odelling **L**anguage — a *standardized data
description format of the office furniture industry*. It is a manufacturer- and
software-vendor-independent standard for describing furniture products so they can be
presented, configured, priced, planned and ordered inside sales systems.

- **Governance / ownership:** The standard is issued on behalf of the industry
  association — historically the *Verband Büro-, Sitz- und Objektmöbel e.V. (BSO)*,
  today the **Industrieverband Büro und Arbeitswelt e.V. (IBA)**. Parts I–III were
  developed by **EasternGraphics GmbH** on behalf of the association; the remaining
  parts are specified by the association's standardization committee.
- **Intellectual origin:** The OFML object model (scene architecture, rules, base
  interfaces) originates with Dr.-Ing. habil. Ekkehard Beier (TU Ilmenau). Basic syntax
  and semantics derive from the **Cobra** programming language (EasternGraphics).
- **Current reference version:** OFML 2.0, 3rd revised edition (Nov 2015).

### 1.1 Why OFML Exists (Motivation)

Traditional CAD-based solutions could not meet the industry's needs:

- enormous data size and costly licensing,
- poor parameterizability and configurability,
- insufficient coverage of product *logic* (configuration rules),
- insufficient interactive display quality and complicated operation.

OFML was created to give an *unlimited number* of software vendors a common, platform-
and vendor-independent format — avoiding monopolization and enabling **technological
uniformity between manufacturer, trade and end-user systems**. It does not replace CAD;
it aims at *coexistence* with CAD via compatible formats/conversion.

### 1.2 Core Features / Design Goals

- Consistent application of the **object-oriented paradigm**.
- **Semantic modelling** so virtual objects match actual products.
- A **holistic data model** combining geometric, visual, interactive and semantic
  features of real products.
- Mapping of **real configuration logic and parametrics**.
- Independence of system/interface platforms and of any concrete runtime environment.

---

## 2. The OFML Parts (I–VII)

The standard is divided into **Parts**, each covering a different aspect of data
creation or an application process. The parts are linked chiefly by cross-reference
(article numbers and type identifiers).

| Part | Name | Abbrev. | Role |
|------|------|---------|------|
| I | OFML Database | **ODB** | Table-based interface describing hierarchical **2D/3D geometries** → see [08_ODB](08_ODB.md) |
| II | Generic Office Library | **GO** | Class library of basic office-furniture functionality (interactions, scaling, accessory placement) |
| III | Object Model | *(core)* | The OFML programming language, base interfaces, rule reasons, global functions, base types, **product-data-management interface** → see [11_Product_Model](11_Product_Model.md) |
| IV | OFML Commercial Data | **OCD** | Tables for **commercial product data** — configuration, pricing, offer/order forms → see [07_OCD](07_OCD.md) |
| V | OFML Article Selection | **OAS** | Format for structured representation/selection of articles in digital catalogs *(specified but currently not used in practice)* |
| VI | OFML Article Mappings | **OAM** | Tables defining complex relationships between data created under other OFML parts (the standardized **mapping data** format since Sept 2004) |
| VII | OFML Business Data Exchange | **OEX** | Format for electronic exchange of business documents (purchase orders, invoices) |

> Note on naming: OFML's own numbered "Parts" (I–VII above) come from the OFML standard
> document. This handbook's file numbering (06, 07, 08 …) is independent.

**Part III is the heart of OFML** — the OFML standard document itself describes only
Part III in detail; all other parts have their own specifications. On the basis of the
Part III object model, *arbitrarily complex data* can be created and *external
commercial data* can be integrated.

---

## 3. The Object / Class Model (Part III)

OFML defines a full object-oriented programming language plus a scene/object model.

### 3.1 Core Concepts

| Concept | Meaning |
|---------|---------|
| **Type** (= class) | Combination of entities of the same kind. Defines a set of *methods*, *rules*, *instance variables* and exactly **one initialization function**. Single inheritance only (one direct super-type). May be *abstract* (no instances) or *concrete*. |
| **Interface** | A descriptive tool resembling a type, but not necessarily a type; interfaces are not derived from one another and take no name prefix. |
| **Instance** (= object / entity) | A concrete embodiment of a type, identified by a **hierarchical name**; owns its own copy of the instance variables. |
| **Children** | An instance lives in the namespace of a *father* object. Children are created/modified/deleted at runtime; deleting a father deletes its children. A child inherits its father's global space modelling. |
| **Scene topology** | The father–child relations form a **set of trees**. |
| **Element** | A special child whose generation/removal is controlled via *rules* — used for user-accessible components of a complex instance (non-elements are hidden combined components). |
| **Property** | A configurable characteristic of an object (with format/definition specifications) → see [11_Product_Model](11_Product_Model.md). |
| **Method** | Behaviour defined on a type. |
| **Rule** | Constraint/logic; OFML defines predefined **rule reasons** (element, selection, move, persistence and other rules). |
| **Category** | Classification of interfaces/materials/planning constructs. |
| **Interactor** | An object enabling interactive manipulation in the scene. |

### 3.2 Base Interfaces

The concrete standard types build on base interfaces: **MObject**, **Base**,
**Material**, **Property**, **Complex**, and **Article** (the interface representing a
sellable/orderable product within a scene).

### 3.3 Notable Type Groups (Part III)

- **Geometric types:** `OiBlock`, `OiCylinder`, `OiEllipsoid`, `OiFrame`, `OiHole`,
  `OiPolygon`/`OiHPolygon`, `OiRotation`, `OiSphere`, `OiSweep`, `OiSurface`,
  `OiImport`, etc.
- **Global Planning Types:** `OiPlanning`, `OiProgInfo`, `OiPlElement`, `OiPart`,
  `OiPropertyObj`, `OiOdbPlElement`.
- **Product-Data-Management types:** `OiPDManager`, `OiProductDB` — used to access
  external product data (the *generic product-data interface*).
- **Planning-environment types:** `OiLevel`, `OiWall`, `OiWallSide` (the wall
  interface).

### 3.4 Programming Language & Modules

Part III specifies lexical structure, types, statements, expressions, classes and
**packages & namespaces**. Global (type-independent) functions have an `oi…` prefix
(e.g. `oiClone()`, `oiCopy()`, `oiCollision()`, `oiTable()`, `oiOutput()`). A type name
must be unique within its defining module *and* globally — achieved via a uniform name
prefix or by integration into a namespace.

---

## 4. Packages, Namespaces & Program IDs

- **Package / namespace (Part III sense):** hierarchical name space used to keep type
  names globally unique. *This is distinct from an "OFML package" (see below).*
- **Program ID:** the unambiguous ID that identifies an **OFML library / program**.
- **Type identifiers + article numbers** are the primary cross-reference mechanism that
  binds the OFML parts together.

---

## 5. OFML Libraries, Packages & the Product Database

An **OFML library** (synonym: *OFML program*) is identified by a unique **program ID**.
There are three forms:

| Library form | Contents |
|--------------|----------|
| **OFML base library** | OFML classes and other data per Part III, **without** reference to a concrete commercial series. Forms the development basis for product libraries. |
| **OFML product library** (= *OFML series*) | Aggregation of the **commercial + graphical + mapping (+ optionally catalog)** data of one or several commercial series of a manufacturer. A commercial series should be *completely* contained. |
| **OFML catalog library** | Contains **only catalog data**, referencing articles held in other product libraries. |

- **OFML package:** an actual *distribution and installation unit* of an OFML library
  for a defined sales region, tagged with a unique **version number**. It is **not** the
  same as a Part III namespace-package.
- **Product database:** logically, an OFML product library always contains a dedicated
  product database (the commercial data) for its series; physically, one database may
  serve several product libraries (especially with external, non-OFML systems).

For the resolution rule — a *(manufacturer ID, series ID, article number)* triple must
unambiguously identify one product library — see [11_Product_Model](11_Product_Model.md)
and [19_Glossary](19_Glossary.md).

---

## 6. Data Domains: How 2D/3D + Commercial Data Combine

OFML deliberately **separates commercial data from graphical data** and binds them via
mapping data:

| Domain | What it is | Standard |
|--------|-----------|----------|
| **Commercial data** | All *non-graphical* selling data: presentation text (short/long description), configuration (configurable characteristics + relations/conditions), pricing (base price + surcharges). | **OCD** (Part IV); may also be supplied via external product DBs mapped to the Part III data model → [07_OCD](07_OCD.md) |
| **Graphical data** | Everything for visual representation in 2D/3D views. | OFML Parts I–III (ODB geometry, GO, materials) |
| **Catalog data** | Presentation/selection of products to buyers; lets a selected article be inserted into a plan / article list. | XCF (EasternGraphics) in practice; OAS (Part V) standardized but unused |
| **Mapping data** | Connects commercial ↔ graphical ↔ catalog data so a catalog selection finds the right graphics and links to commercial data. | **OAM** (Part VI) |

See [02_Architecture](02_Architecture.md) for the domain diagram.

---

## 7. Geometry: The OFML Database (ODB, Part I)

**ODB** provides a **table-based interface** for describing **hierarchical geometries in
both 2D and 3D**. It is the geometric backbone consumed by the object model. Full
treatment in [08_ODB](08_ODB.md). External geometry/material/font formats and archives
are documented in the OFML standard's appendices.

---

## 8. Generic Office Library (GO, Part II)

**GO** (Generic Office Library) is a **class library providing basic functionality for
the office-furniture domain**. It supplies ready-made building blocks so manufacturer
data need not re-implement common behaviour:

- **Elementary interaction types** — constrained rotations/translations along local or
  global axes: `GOXRot`/`GOYRot`/`GOZRot`, `GOXTrans`/`GOYTrans`/`GOZTrans`, local
  variants (`GOXLRot`, `GOYLTrans`, …) and combinations.
- **Complex interaction types** — e.g. drawer interlocks (anti-tilt/extension lock),
  hinged-door cabinets with L/R door locking, horizontal/vertical roller-shutter
  cabinets (straight and curved, profiled and unprofiled fronts), synchronized sliding
  along X/Y/Z, height adjustment for A-frame tables, fold-in flaps.
- **Other types** — `GoAccParameters` (accessory-placement parameters), `GoScaling`
  (scaling node).

GO is *skimmed* here for its role; it underpins the interactive/parametric behaviour of
generated products. See [14_Generation_Process](14_Generation_Process.md).

---

## 9. Materials (OMATS)

**OMATS** = *OFML-compatible Materials* — defines the material models used to represent
object surfaces, for both **real-time** and **photorealistic** rendering.

- Two models: **OMATS1** (older) and **OMATS2** (newer, based on **Physically Based
  Rendering / PBR**). OMATS2 uses a more compact description, gives more realistic
  real-time output, and improves editor usability (fewer parameters/dependencies).
- Backward compatibility: OMATS1 materials are **auto-converted** to the new model.
- Covers **texture-mapping methods** (plane mapping, block mapping, texture
  coordinates) and the **OFML data format for material definition files**.
- References ODB (Part I) for integration.

Material file forms and details are catalogued in [15_File_Formats](15_File_Formats.md).

---

## 10. Layers (OLAYERS + Tags)

**OLAYERS** = *OFML-compatible Layers* — an OFML-compatible layer structure (adapting
older FOS layer concepts) that identifies manufacturer and product series within
CAD/geometry data. It is a *living* specification; uniform tag proposals live in the
companion **OLAYERS-TAGS** document.

### 10.1 Generic Layer Name

```
72_<MAN>_<SERIES>_<MOD>[_<TAG>]
```

| Token | Meaning |
|-------|---------|
| `72` | AutoDesk qualification for **furniture** (followed by `_` to distinguish from FOS). |
| `<MAN>` | OFML manufacturer identifier (**DSR** *manufacturer* key). |
| `<SERIES>` | OFML library/series identifier (**DSR** *program* key). |
| `<MOD>` | A specific **mode** (see below). |
| `<TAG>` | Data-specific qualifier; availability depends on `<MOD>`. |

Example: `72_EGR_OFFICE2_D3_ANY` → manufacturer *EGR*, series *OFFICE2*, 3D geometry,
tag *ANY*. **Layer names are case-insensitive** (upper case in practice; names may not
differ only by case).

### 10.2 Layer Modes (selected)

- **General / 2D:** `*_DIMENSIONS_MM` (dimension text, W×D×H in mm), `*_TEXT_<LANG>`
  (extra text per ISO 639-1), `*_ARTICLE_INFO` (usually commercial article number),
  `*_ARTICLE_INFO_DPOS` (drawing position linking CAD article ↔ bill of materials /
  basket), `*_SPECIAL` (special-article info), `*_MISC` (optional/accessories without
  3D geometry).
- **3D:** `*_D3_<TAG>` (3D info, tag mandatory), `*_D3FRONT_<TAG>` (front elements,
  filterable/hideable), `*_ACOUSTICS_<TAG>` (acoustic representation geometry for
  acoustic evaluation).
- **2D:** `*_D2_<TAG>` (2D info, tag mandatory).
- **Snapping layer** — for snap geometry.

### 10.3 OLAYERS-TAGS

Companion catalog of standardized **tag identifiers** grouped by furniture type, e.g.
`ANY` (unspecified), and table tags `TB_ATTACH`, `TB_BACKPLANE` (modesty panel),
`TB_CABLE_DUCT`, `TB_CASTORS`, `TB_CLIPBOARD`, `TB_CONNECTOR`, `TB_COVER`, `TB_EDGE`,
`TB_FOOT`, `TB_FRAME`/`TB_FRAME_PART`, `TB_GLASS`, `TB_HOLDER`, `TB_INLAY`,
`TB_ORGA_FRAME`/`TB_ORGA_PANEL`/`TB_ORGA_PARTS`, etc. Tags drive material assignment and
application-level filtering. Layer/tag file conventions → [15_File_Formats](15_File_Formats.md).

---

## 11. DSR — Data Structure and Registration

**DSR** (*OFML Data Structure and Registration*, EasternGraphics) defines the on-disk
**directory structure** of OFML product and catalog data and the **registration** of
manufacturers, concerns and OFML packages in a central registration database.

- Defines **data profiles** (`app.gf.data.profile`) and **catalog profiles**
  (`app.gf.data.catalogs`), settings/paths, descriptions and package groupings.
- Provides the canonical **manufacturer key** (`<MAN>`) and **program key**
  (`<SERIES>`) used by OLAYERS and throughout OFML identification.
- Registers **OFML packages** (distribution/installation units) with version numbers and
  language-dependent keys.

DSR is *skimmed* here for its role: it is the registration/registry backbone that makes
program IDs, manufacturer IDs and packages resolvable by applications.

---

## 12. How OFML Is Consumed (pCon Applications)

OFML data is consumed by EasternGraphics **pCon** applications. Application Note
**AN-2023-01** tracks which OFML formats/versions each pCon release supports:

- **Configurator / online:** `pCon.configurator Online (EAIWS)`, `pCon.basket Online`,
  `pCon.facts`, `pCon.box`, `pCon.ui`, `pCon.roomplanner`, `pCon.planner web`,
  `pCon.catalog`.
- **Desktop:** `pCon.basket`, `pCon.xcad`, `pCon.planner`.
- Support is tracked per format: **OCD** (2.1 … 5.0), **XCF** (catalog), **OAP**
  (1.1 … 1.6), **MT** (Metatype 1.18), **DSR** (3.3 … 3.7), plus processing libraries
  (XOI, OI, GO, EAI, FAPI).

Not every application supports every format/version — e.g. some MT tables are
restricted in online apps. See [09_OAP](09_OAP.md) and [10_Metatype](10_Metatype.md).

---

## 13. Related Handbook Documents

- [02_Architecture](02_Architecture.md) — overall ecosystem architecture & part
  interrelations.
- [07_OCD](07_OCD.md) — commercial data (Part IV).
- [08_ODB](08_ODB.md) — geometry database (Part I).
- [09_OAP](09_OAP.md) — OFML Article Presets / OAP.
- [10_Metatype](10_Metatype.md) — Metatype (MT) data model.
- [11_Product_Model](11_Product_Model.md) — article & property interfaces (Part III PDM).
- [15_File_Formats](15_File_Formats.md) — file formats & directory conventions.
- [18_Design_Principles](18_Design_Principles.md) — engineering philosophy.
- [19_Glossary](19_Glossary.md) — foundational terminology.

> `UNKNOWN`: The OFML "MOL / Meta OFML Language" naming referenced in the handbook brief
> is not attested as a distinct term in these source specs; the Part III language is
> described simply as the *OFML object model / programming language*. Treat "MOL" as
> `UNKNOWN` until a source confirms it.
