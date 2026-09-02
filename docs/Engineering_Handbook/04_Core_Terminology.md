# 04 — Core Terminology

**Source:** OFML glossary + specifications (EasternGraphics/IBA), consolidated for the MK Product Workbench Engineering Handbook.
**Status:** Consolidated from specification docs; unclear items marked `UNKNOWN`.

A curated, categorized quick-reference of the **most important** terms, grouped by domain.
For each term: a crisp definition, synonyms (in parentheses), and the handbook chapter
where it is detailed. This is the fast lookup; the exhaustive alphabetical list is
[19 — Glossary](19_Glossary.md), and the conceptual "how it fits" narrative is
[03 — Engineering Concepts](03_Engineering_Concepts.md).

---

## A. Products & Classification

| Term (synonyms) | Definition | Detailed in |
|---|---|---|
| **Product** (article) | A commodity/service produced or offered for sale by a manufacturer/supplier; differentiated by constructive, material and other characteristics. | [03](03_Engineering_Concepts.md) |
| **Configurable product** | A product for which some characteristics can be specified by the buyer/user. | [11](11_Product_Model.md), [16](16_Configuration.md) |
| **Article number** | Alphanumeric code uniquely identifying a product within the PPS. Basic = configurable product; final/extended = configured product (embeds variant code). | [11](11_Product_Model.md) |
| **Variant code** | Portion of the final article number encoding the values of the configurable characteristics. | [07](07_OCD.md), [11](11_Product_Model.md) |
| **Article variant** (article configuration) | The specific property values of a configurable article. | [16](16_Configuration.md) |
| **Product classification** | Organizing products into classes by differentiation criteria; may be multi-level (super/subclasses). | [03](03_Engineering_Concepts.md) |
| **Product group** (commodity group, class of goods) | A class per a manufacturer-specific classification, often used for rebates. | [07](07_OCD.md) |
| **Commercial series** (collection, product line) | A group of products governing distribution; obligatory for an OFML sales system; assignment must not change during the article life cycle. | [07](07_OCD.md) |

## B. Data Domains

| Term (synonyms) | Definition | Detailed in |
|---|---|---|
| **Product data** | Broad: all data to present/configure/order/produce/supply a product. Narrow: synonym for commercial data. | [03](03_Engineering_Concepts.md) |
| **Commercial data** (OCD data) | Non-graphical, sales-relevant data: presentation, configuration, pricing. Standardized in OFML Part IV. | [07](07_OCD.md) |
| **Graphical data** | All data used to visualize a product in 2D/3D (OFML Parts I–III). | [08](08_ODB.md), [06](06_OFML.md) |
| **Mapping data** (OAM) | Connections between commercial, graphical and catalog data. OFML Part VI. | [02](02_Architecture.md) |
| **Catalog data** | Data for a catalog (presentation/selection instrument); in EG systems the XCF format. | [02](02_Architecture.md) |

## C. Libraries & Packaging

| Term (synonyms) | Definition | Detailed in |
|---|---|---|
| **OFML library** (OFML program) | A unit of OFML classes/data identified by a unique **program ID**. Three forms below. | [03](03_Engineering_Concepts.md) |
| **Base library** | OFML classes/data per the standard, without reference to a concrete commercial series; basis for product libraries. | [06](06_OFML.md) |
| **Product library** (OFML series) | Aggregation of commercial + graphical + mapping + (optional) catalog data of one/more commercial series. | [03](03_Engineering_Concepts.md) |
| **Catalog library** | Contains only catalog data referencing articles in other product libraries. | [03](03_Engineering_Concepts.md) |
| **OFML package** | Distribution/installation unit of a library for a **sales region**, with a unique **version number**. | [18](18_Design_Principles.md) |
| **Program ID** | Unique identifier of an OFML library/program. | [03](03_Engineering_Concepts.md) |
| **Product database** | Database holding commercial data of one/more commercial series. | [07](07_OCD.md) |
| **DSR** (Data Structure and Registration) | Spec governing the directory structure of OFML product/catalog data and its registration (data & catalog profiles). | [18](18_Design_Principles.md) |

## D. Commercial / OCD

| Term (synonyms) | Definition | Detailed in |
|---|---|---|
| **OCD** (OFML Commercial Data, Part IV) | Standardized CSV-table format for commercial data: articles, properties, relations, prices, texts, taxation. | [07](07_OCD.md) |
| **Property class** | Grouping construct for properties in OCD (property class table). | [07](07_OCD.md), [16](16_Configuration.md) |
| **Property group** | Presentation grouping of properties within a class. | [07](07_OCD.md) |
| **Relation / relationship knowledge** | OCD constraints (conditions) between property values driving configuration logic. | [16](16_Configuration.md) |
| **Price / price factor / rounding rule** | OCD pricing constructs: base price, surcharges, factors and rounding rules used in price determination. | [07](07_OCD.md) |
| **Taxation scheme / tax category** | OCD constructs describing tax treatment of articles. | [07](07_OCD.md) |
| **Final article number generation** | OCD schemes (predefined or user-defined) that build the final article number from the variant code. | [07](07_OCD.md) |

## E. Geometry / ODB

| Term (synonyms) | Definition | Detailed in |
|---|---|---|
| **ODB** (OFML Database, Part I) | Table format describing 2D/3D geometry: objects, hierarchy, transforms, attributes. | [08](08_ODB.md) |
| **EGM** (OFML Metafile Format) | OFML's geometry metafile format. | [08](08_ODB.md) |
| **Attach point** | Conventional OFML connection point on geometry (extended by OAP smart attach areas). | [09](09_OAP.md) |
| **Layer** (OLAYERS) | OFML-compatible layer naming scheme for 2D/3D/snapping geometry organization. | [18](18_Design_Principles.md) |

## F. Planning / OAP

| Term (synonyms) | Definition | Detailed in |
|---|---|---|
| **OAP** (OFML Aided Planning) | Data format for interactive planning behaviour: interactors, actions, attach areas. | [09](09_OAP.md) |
| **Article representation** (planning element, object) | The object graphically representing an article in a planning/configuration system. | [09](09_OAP.md) |
| **OFML instance** (OFML article instance) | The (often temporary, non-visible) OFML object used to configure an article and determine texts/prices. | [09](09_OAP.md), [11](11_Product_Model.md) |
| **Basket instance** | Commercial representation of an article in the server basket (EAIWS online apps). | [09](09_OAP.md) |
| **Interactor** | 2D/3D graphical symbol drawn over an object, linked to actions triggered on selection. | [09](09_OAP.md) |
| **Attach area** (smart attach area) | Extended attach point that can be linked with actions and used for snapping; may be active/passive. | [09](09_OAP.md) |
| **PropVarCode** (property variant code) | Encoding of current OFML property values as `<Property>=<Value>;...`. | [09](09_OAP.md) |
| **Proximity** (connection) | Relationship between two planning elements whose attach areas match logically & geometrically. | [09](09_OAP.md) |

## G. Metatype / GO

| Term (synonyms) | Definition | Detailed in |
|---|---|---|
| **Metatype** (MT) | Table-driven modelling concept enabling inter-product configuration and concatenation/attachment rules on top of GO. | [10](10_Metatype.md) |
| **GO** (Generic Office Library, Part II) | OFML class library providing base functionality for the office-furniture domain (interaction types, complex behaviours). | [06](06_OFML.md), [14](14_Generation_Process.md) |
| **go_*.csv tables** | CSV exchange tables of Metatype data (prefix `go_`, lowercase table name, `.csv`). | [10](10_Metatype.md), [15 — File Formats `UNKNOWN` (not yet written)] |
| **Inter-product configuration** | Configuration that may change the basic article number (e.g. selecting another program/collection). | [10](10_Metatype.md) |

## H. Materials / Layers

| Term (synonyms) | Definition | Detailed in |
|---|---|---|
| **OMATS** (OFML compatible Materials) | Spec for material models, texture mapping and the OFML material data format. | [06](06_OFML.md) |
| **PBR** (Physically Based Rendering) | Material model paradigm introduced in newer OMATS versions. | [06](06_OFML.md) |
| **Texture mapping** (plane/block) | Methods for applying textures to geometry (plane mapping, block mapping, texture coordinates). | [08](08_ODB.md) |
| **OLAYERS** | OFML-compatible layer naming (general, 3D, 2D, snapping layers). | [18](18_Design_Principles.md) |

---

### See also

- Conceptual model & narrative → [03 — Engineering Concepts](03_Engineering_Concepts.md)
- Exhaustive A–Z → [19 — Glossary](19_Glossary.md)

> Chapters referenced as `(not yet written)` are placeholders in the handbook plan and
> are marked `UNKNOWN` until authored.
