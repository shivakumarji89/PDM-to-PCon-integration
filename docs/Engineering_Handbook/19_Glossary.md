# 19 — Glossary

**Source:** OFML glossary + specifications (EasternGraphics/IBA), consolidated for the MK Product Workbench Engineering Handbook.
**Status:** Consolidated from specification docs; unclear items marked `UNKNOWN`.

Exhaustive alphabetical A–Z glossary. It includes **every** term from the authoritative
*OFML glossary* (v1.1) plus acronyms/terms harvested from the OFML, OCD, ODB, OAP, OAM,
OAS, XCF, MT/Metatype, GO, OMATS, OLAYERS and DSR specifications and the pCon support
application note. Format:

`**Term** (synonyms) — definition. → [doc](NN_Name.md)`

Where a term is used across specs but not explicitly defined, it is marked `UNKNOWN`.
Quick reference: [04 — Core Terminology](04_Core_Terminology.md); conceptual model:
[03 — Engineering Concepts](03_Engineering_Concepts.md).

---

## A

**Action** — An OAP operation executed on an event (e.g. activation of an interactor, use of an attach area). Parameter types include Choice, PropChange, PropEdit2, DimChange, CreateObj, MethodCall, Message, ExtMedia. → [09](09_OAP.md)

**Active planning element** — In an insert/delete/move operation, the element being inserted, deleted or moved (plays the active role); its active attach areas apply. Contrast passive planning element. → [09](09_OAP.md)

**Aggregation** — Relationship in the OFML conceptual model (drawn as a diamond) denoting contained entities, e.g. a product library aggregates commercial/graphical/mapping/catalog data. → [03](03_Engineering_Concepts.md)

**AN (Application Note)** — EasternGraphics/IBA supplementary document clarifying or extending a specification (e.g. AN-2023-01 on OFML support in pCon applications). → [02](02_Architecture.md)

**Article** (synonym: product) — A commodity/service produced or offered for sale by a manufacturer/supplier; differentiated by constructive, material and other characteristics. → [03](03_Engineering_Concepts.md)

**Article configuration** (synonym: article variant) — The specific values of a configurable article's properties. → [16](16_Configuration.md)

**Article identification table** — OCD table mapping article numbers to alternative identifications. → [07](07_OCD.md)

**Article interface** — OFML Part III interface `Article` (and `CompositeArticle`) exposing an article's codes, product data, features/variant text, persistence and consistency to the application. → [11](11_Product_Model.md)

**Article number** — Alphanumeric code uniquely identifying a product within the leading PPS (occasionally unique only within a commercial series). Basic article number = configurable product; final/extended article number = configured product, embedding the variant code. → [11](11_Product_Model.md)

**Article representation** (synonyms: planning element, object) — The object that graphically represents an article in a planning/configuration system. → [09](09_OAP.md)

**Article table** — Core OCD table listing articles and their base attributes. → [07](07_OCD.md)

**Article variant** (synonym: article configuration) — A configurable article with specific property values chosen by the user; encoded in the variant code / PropVarCode. → [16](16_Configuration.md)

**Attach area** (smart attach area) — OAP extension of the conventional OFML attach point: an area that can be linked with actions and used for snapping; may be active, passive, or both. → [09](09_OAP.md)

**Attach point** — Conventional OFML geometric connection point on an object, used for snapping/concatenation (extended by OAP attach areas). → [09](09_OAP.md)

## B

**Base library** (OFML base library) — OFML classes/data per the standard (Part III) without reference to a concrete commercial series; the development basis for product libraries. → [06](06_OFML.md)

**Basic article number** — The article number identifying a *configurable* product (before variant selection). Contrast final article number. → [11](11_Product_Model.md)

**Basket instance** — In EAIWS online apps, the commercial representation of an article held in the server basket (distinct from the client planning element). → [09](09_OAP.md)

**Bill of items** — OCD table describing the item components of a composite article. → [07](07_OCD.md)

**Block mapping** — OMATS texture-mapping method projecting a texture as a 3D block. → [08](08_ODB.md)

**BSO** (Verband Büro-, Sitz- und Objektmöbel e.V.) — Former German industry association under whose auspices the OFML/GO standard (parts I–III) was developed; predecessor context to IBA. → [06](06_OFML.md)

## C

**Catalog** — Instrument for presenting all or part of a manufacturer's products to a buyer; printed or electronic. Electronic catalogs also insert a selected article into a plan/article list. → [02](02_Architecture.md)

**Catalog data** — Data for an electronic catalog; in EasternGraphics systems the proprietary XCF format. A catalog may span multiple commercial series. → [02](02_Architecture.md)

**Catalog library** (OFML catalog library) — An OFML library containing only catalog data that references articles in other product libraries. → [03](03_Engineering_Concepts.md)

**Catalog profile** — DSR registration entry (via `app.gf.data.catalogs`) describing available catalog data. → [18](18_Design_Principles.md)

**Class of goods** (synonyms: product group, commodity group) — A product class per a manufacturer classification, often used for rebates. → [07](07_OCD.md)

**Classification table** — OCD table assigning articles to classification classes. → [07](07_OCD.md)

**Cobra** — EasternGraphics programming language on whose basic syntax and semantics OFML is based. → [06](06_OFML.md)

**Code scheme table** — OCD table defining code schemes used in article/variant coding. → [07](07_OCD.md)

**Collection** (synonyms: commercial series, product line) — A manufacturer's distribution-governing group of products. → [07](07_OCD.md)

**ComGroup** (commercial group / package group) — Grouping of OFML packages/commercial data used in registration and delivery. `UNKNOWN` (referenced in DSR/registration context; precise definition not fixed in the read specs). → [18](18_Design_Principles.md)

**Commercial data** — All non-graphical, sales-relevant data of a product: presentation (texts), configuration (properties + relations), pricing (base price + surcharges). Standardized in OCD (OFML Part IV). → [07](07_OCD.md)

**Commercial series** (synonyms: collection, product line) — A group of products, per a manufacturer-specific classification, that governs distribution. Obligatory for an OFML sales system; identified by an ID; assignment must not change during the article life cycle. → [07](07_OCD.md)

**Commodity group** (synonyms: product group, class of goods) — See product group. → [07](07_OCD.md)

**Complex** — OFML Part III base interface for objects composed of sub-objects (complex objects). → [06](06_OFML.md)

**Composite article** — An article assembled from multiple component articles; described by the OCD composite-articles table and the `CompositeArticle` interface. → [11](11_Product_Model.md)

**Configurable product** (configurable article) — A product for which some characteristics can be specified by the buyer/user of the sales system. → [16](16_Configuration.md)

**Configuration** — Process of choosing values for a configurable article's properties, driven by OCD relations and property interface methods. → [16](16_Configuration.md)

**Connection** (synonym: proximity) — Relationship between two planning elements whose attach areas match logically and geometrically. → [09](09_OAP.md)

**CSV table** — Comma/semicolon-separated value file used as the physical exchange format for OCD, OAP and Metatype tables (UTF-8/ASCII, `;` field separator, `#` comment lines). → [15 `UNKNOWN` (File Formats chapter not yet written)]

## D

**Data profile** — DSR registration entry (via `app.gf.data.profile`) describing installed OFML product data, its settings and paths. → [18](18_Design_Principles.md)

**Description tables** — OCD tables holding short/long descriptive texts for articles and properties. → [07](07_OCD.md)

**DimChange** — OAP action parameter type that changes a dimension of an object. → [09](09_OAP.md)

**DSR** (Data Structure and Registration) — EasternGraphics specification governing the directory structure of OFML product/catalog data and its registration (data & catalog profiles, packages of a group). → [18](18_Design_Principles.md)

## E

**EAI / EAIWS** (Enterprise Application Integration Web Server) — Server component behind pCon online applications that manages the basket and creates temporary OFML instances. → [09](09_OAP.md)

**EAN.UCC** — International article-coding system whose codes may additionally apply to a product beyond the article number. → [11](11_Product_Model.md)

**eCl@ss** — Manufacturer-independent standardized product classification model. → [03](03_Engineering_Concepts.md)

**EGM** (OFML Metafile Format) — OFML's geometry metafile format (EasternGraphics copyright). → [08](08_ODB.md)

**Element rule** — Predefined OFML rule reason category governing element creation/insertion. → [06](06_OFML.md)

**Entity** — OFML core concept: an instantiable object in the OFML scene/object model. → [06](06_OFML.md)

**ExtMedia** — OAP action parameter type referencing external media. → [09](09_OAP.md)

## F

**Final article number** (extended final article number) — Article number identifying a product *as configured*, containing the variant code. Generated per OCD schemes (predefined or user-defined). → [07](07_OCD.md)

**Final article number generation** — OCD process building the final article number from the base number plus variant code; supports multivalued properties. → [07](07_OCD.md)

**FAPI** — OFML processing library/interface referenced in the pCon support matrix (e.g. FAPI 4.3.1). `UNKNOWN` (version listed but not specified in read docs). → [02](02_Architecture.md)

## G

**GO** (Generic Office Library, OFML Part II) — OFML class library providing base functionality for the office-furniture domain: elementary interaction types (rotations, translations) and complex interaction behaviours (cabinets, roller shutters, height adjustment, synchronized moves). → [06](06_OFML.md)

**go_*.csv** — Metatype exchange tables: files named with prefix `go_`, the lowercase table name, and suffix `.csv`. → [10](10_Metatype.md)

**Graphical data** — All data used to visualize a product in 2D/3D; formats/methods per OFML Parts I–III. → [08](08_ODB.md)

## H

**Hierarchy level** — ODB attribute defining the nesting/level of a 2D geometry object. → [08](08_ODB.md)

## I

**IBA** (Industrieverband Büro und Arbeitswelt e.V.) — German industry association that publishes/maintains the OFML specifications (formerly BSO). → [02](02_Architecture.md)

**IAON** (Industrielle Aspekte der OFML-Normung) — Working group responsible for OLAYERS and related industrial-aspect standards. → [18](18_Design_Principles.md)

**Identification table** — OCD table providing identifications/keys for data records. → [07](07_OCD.md)

**Initialization** — OFML core concept and article-interface phase in which an article instance is set up with its codes. → [11](11_Product_Model.md)

**Interactor** — OAP two-dimensional (or 3D) graphical symbol drawn over an object and linked to one or more actions performed when selected (activated). Object-specific; may have visibility areas. → [09](09_OAP.md)

**Inter-product configuration** — Metatype capability to change configuration across products, including changes to the basic article number (e.g. selecting another program/collection). → [10](10_Metatype.md)

**Intra-product property** — A configurable property whose change keeps the basic article number unchanged. Contrast inter-product configuration. → [10](10_Metatype.md)

## L

**Layer** — Organizational grouping of geometry; OLAYERS defines OFML-compatible layer names (general, 3D, 2D, snapping). → [18](18_Design_Principles.md)

**Life cycle** — The span over which a product exists; classification assignments may change over it, but commercial-series assignment must not. → [03](03_Engineering_Concepts.md)

## M

**Mapping data** — Data describing the connections between commercial, graphical and catalog data, used to find the graphical representation for a selected article and link it to its commercial data. Standardized in OAM (OFML Part VI). → [02](02_Architecture.md)

**Marketing system** (synonym: sales system) — Software system supporting a dealer with sales procedures. → [03](03_Engineering_Concepts.md)

**Material** — OFML Part III base interface (and OMATS domain) describing surface material of geometry. → [06](06_OFML.md)

**Material group** — A product class in the conceptual model; a grouping of products (see product group). → [07](07_OCD.md)

**MethodCall** — OAP action parameter type invoking a method on an object. → [09](09_OAP.md)

**Metatype** (MT) — OFML modelling concept, defined by CSV tables, enhancing traditional graphic-data modelling with inter-product configuration and concatenation/attachment rules; implemented via `::ofml::go`. → [10](10_Metatype.md)

**MObject** — The root OFML Part III base interface from which OFML objects derive. → [06](06_OFML.md)

**Move rule** — Predefined OFML rule reason category governing object movement. → [06](06_OFML.md)

## N

**NumTripel table** — OAP table mapping number triples (e.g. manufacturer/series/article context). → [09](09_OAP.md)

## O

**OAM** (OFML Article Mappings, OFML Part VI) — Standard (since 2004) for mapping data connecting commercial, graphical and catalog data. → [02](02_Architecture.md)

**OAP** (OFML Aided Planning) — Specification for interactive planning behaviour data: types, mappings, attach areas, interactors and actions; largely OFML-part-independent metadata. → [09](09_OAP.md)

**OAS** (OFML Article Selection, OFML Part V) — Standard format for catalog data; currently not used in practice (XCF used instead). → [02](02_Architecture.md)

**Object** (synonyms: article representation, planning element) — The graphical representation of an article in a planning system. → [09](09_OAP.md)

**OCD** (OFML Commercial Data, OFML Part IV) — Standardized CSV-table format for commercial data: articles, classification, packaging, properties, relations, prices, rounding, series, descriptions, taxation, etc. → [07](07_OCD.md)

**OCD_1 / OCD_2** — Language definitions used within OCD (constraints, table calls in preconditions). → [07](07_OCD.md)

**ODB** (OFML Database, OFML Part I) — Table format describing 2D/3D geometry: object creation, hierarchy, offset/rotation/scaling, and attributes (color, line width/style, fonts). → [08](08_ODB.md)

**OEX** (OFML Business Data Exchange) — OFML specification for business data exchange, referenced by the article interface. `UNKNOWN` (referenced only; not read in detail). → [02](02_Architecture.md)

**OFML** (Standardized Data Description Format of the Office Furniture Industry) — The overall standard (v2.0, 3rd rev.); a multi-part object model, language (Cobra-based) and data formats for presenting, configuring and visualizing products. → [06](06_OFML.md)

**OFML instance** (OFML article instance) — The OFML object created (often temporarily and invisibly) to configure an article and determine texts, prices and other article information. → [11](11_Product_Model.md)

**OFML library** (synonym: OFML program) — Unit of OFML classes/data identified by a unique program ID; exists as base, product or catalog library. → [03](03_Engineering_Concepts.md)

**OFML package** — Actual distribution/installation unit of an OFML library for a defined sales region, tagged with a unique version number (not a Part III namespace package). → [18](18_Design_Principles.md)

**OFML program** (synonym: OFML library) — See OFML library; identified by program ID. → [03](03_Engineering_Concepts.md)

**OFML series** (synonym: OFML product library) — See product library. → [03](03_Engineering_Concepts.md)

**OI / XOI** — OFML processing/interface libraries listed in the pCon support matrix (e.g. OI 1.46.0, XOI 1.64.0). `UNKNOWN` (versions listed; not specified in read docs). → [02](02_Architecture.md)

**OLAYERS** (OFML-compatible Layers) — Specification of a generic layer-naming scheme for OFML data (general, 3D, 2D and snapping layers); authored under IAON. → [18](18_Design_Principles.md)

**OLAYERS-TAGS** — Companion specification defining tag names for OFML-compatible layers. → [18](18_Design_Principles.md)

**OMATS** (OFML compatible Materials) — Specification of material models, texture-mapping methods (plane, block, texture coordinates) and the OFML material data format, including PBR. → [06](06_OFML.md)

**Other rule** — Predefined OFML rule reason category not covered by element/selection/move/persistence rules. → [06](06_OFML.md)

## P

**Package** (namespace) — In OFML Part III, a hierarchical namespace for classes; distinct from an OFML (distribution) package. → [06](06_OFML.md)

**Package (distribution)** — See OFML package. → [18](18_Design_Principles.md)

**Packaging table** — OCD table describing packaging data (used in determination of packaging data). → [07](07_OCD.md)

**Passive planning element** — In an insert/delete/move operation, an element other than the one being acted upon (plays the passive role); its passive attach areas apply. → [09](09_OAP.md)

**PBR** (Physically Based Rendering) — Material-modelling paradigm introduced in newer OMATS versions. → [06](06_OFML.md)

**Persistence rule** — Predefined OFML rule reason category governing object persistence. → [06](06_OFML.md)

**Planning element** (synonyms: article representation, object) — Client-side graphical representation of an article in a plan. → [09](09_OAP.md)

**Plane mapping** — OMATS texture-mapping method projecting a texture onto a plane. → [08](08_ODB.md)

**PPS** (production and planning system) — The leading manufacturer system within which an article number is unambiguous. → [11](11_Product_Model.md)

**Price / price table** — OCD constructs and table defining base prices and surcharges for price determination. → [07](07_OCD.md)

**Price factor** — OCD element influencing computed price during price determination. → [07](07_OCD.md)

**Print catalog** — A catalog presented in printed form (vs electronic catalog). → [02](02_Architecture.md)

**Product** (synonym: article) — A commodity/service produced or offered for sale by a manufacturer/supplier. → [03](03_Engineering_Concepts.md)

**Product classification** — Organizing products into classes by differentiation criteria (function, design, price group, statistics…); may be multi-level; a product may belong to several classes. → [03](03_Engineering_Concepts.md)

**Product class** — A class resulting from product classification; superclass of commercial series and material group in the conceptual model. → [03](03_Engineering_Concepts.md)

**Product data** — Broad: all data to present/configure/order/produce/supply a product. In a sales system only commercial + graphical data are relevant; narrow sense = commercial data. → [03](03_Engineering_Concepts.md)

**Product database** — Database holding the commercial data of one or more commercial series; logically dedicated to a product library, physically possibly shared. → [07](07_OCD.md)

**Product group** (synonyms: commodity group, class of goods) — A product class per a manufacturer-specific classification, often used for rebates. → [07](07_OCD.md)

**Product library** (synonym: OFML series) — Aggregation of commercial + graphical + mapping + (optional) catalog data of one or more commercial series; built on a base library. → [03](03_Engineering_Concepts.md)

**Product line** (synonyms: commercial series, collection) — See commercial series. → [07](07_OCD.md)

**Program ID** — Unique identifier of an OFML library/program. → [03](03_Engineering_Concepts.md)

**Property** — A configurable characteristic of an article; OFML Part III base interface and OCD tables define its attributes, value ranges and choice lists. → [11](11_Product_Model.md)

**Property class** — OCD grouping of properties (property class table). → [16](16_Configuration.md)

**Property group** — Presentation grouping of properties within a property class. → [07](07_OCD.md)

**Property interface** — OFML Part III interface `Property` exposing property setup, activation, value ranges/choice lists, values, classes/groups and client support to the application. → [11](11_Product_Model.md)

**Property value table** — OCD table listing allowable property values. → [07](07_OCD.md)

**Property variant code** (PropVarCode) — Encoding of the current OFML property values of an article variant as `<Property>=<Value>;<Property>=<Value>;...`. → [09](09_OAP.md)

**PropChange** — OAP action parameter type that changes a property value. → [09](09_OAP.md)

**PropEdit2** — OAP action parameter type for editing a property. → [09](09_OAP.md)

**Proximity** (synonym: connection) — Relationship between two planning elements whose attach areas match logically and geometrically. → [09](09_OAP.md)

## R

**Rebate** — Discount often applied at the product-group level. → [07](07_OCD.md)

**Relational object table** — OCD table representing relational objects used by relationship knowledge. → [16](16_Configuration.md)

**Relationship knowledge table** — OCD table encoding constraints/conditions (relations) between property values that drive configuration logic. → [16](16_Configuration.md)

**Rounding rule table** — OCD table defining rounding rules applied in price determination. → [07](07_OCD.md)

**Rule** — OFML core concept: constraint/behaviour applied to entities; predefined rule reasons include element, selection, move, persistence and other rules. → [06](06_OFML.md)

## S

**Sales region** — The market/region for which an OFML package is built and delivered. → [18](18_Design_Principles.md)

**Sales system** (synonym: marketing system) — Software system supporting a dealer with sales procedures; the frame for all OFML concepts. → [03](03_Engineering_Concepts.md)

**Selection rule** — Predefined OFML rule reason category governing object selection. → [06](06_OFML.md)

**Series** (commercial series) — See commercial series; also the OCD series table. → [07](07_OCD.md)

**Series table** — OCD table describing commercial series. → [07](07_OCD.md)

**Smart attach area** — See attach area; OAP extension supporting action linkage and snapping. → [09](09_OAP.md)

**Snapping layer** — OLAYERS layer type used to control snapping geometry. → [18](18_Design_Principles.md)

**Superclass / subclass** — Levels in a multi-level classification system. → [03](03_Engineering_Concepts.md)

## T

**Tax category** — OCD taxation construct classifying an article's tax treatment (OCD_TaxCategories). → [07](07_OCD.md)

**Taxation scheme** — OCD construct describing the tax scheme applied to articles. → [07](07_OCD.md)

**Texture coordinates** — OMATS mechanism specifying how a texture maps onto geometry. → [08](08_ODB.md)

**Texture mapping** — Applying a texture to geometry via plane mapping, block mapping and texture coordinates. → [08](08_ODB.md)

**Type** — OFML core concept: the classification of entities/values in the object model and languages. → [06](06_OFML.md)

**Type table** — OAP table defining OAP types. → [09](09_OAP.md)

## U

**UN/SPSC** — Manufacturer-independent standardized product classification standard. → [03](03_Engineering_Concepts.md)

## V

**Value combination tables** — OCD tables constraining allowable combinations of property values. → [16](16_Configuration.md)

**Variant code** — The portion of the final article number that encodes the values of the configurable characteristics; multiple coding schemes may apply. → [07](07_OCD.md)

**Version information table** — OCD/OAP table recording version metadata for the data set. → [07](07_OCD.md)

**Version number** — Unique version tag of an OFML package. → [18](18_Design_Principles.md)

**Visibility** — ODB attribute controlling whether a 2D geometry object is shown; also OAP interactor visibility areas. → [08](08_ODB.md)

## X

**XCF** (Extensible Catalog Format) — EasternGraphics proprietary catalog data format (v2.10) used for electronic catalogs in EG systems. → [02](02_Architecture.md)

**XOI** — See OI / XOI. `UNKNOWN` (processing library; version-listed only). → [02](02_Architecture.md)

---

**Approximate term count:** ~150 entries (including synonyms and cross-listed forms).

**`UNKNOWN` items:** ComGroup, FAPI, OEX, OI/XOI, XOI, the CSV/File-Formats chapter link
(15), and forward references to not-yet-written chapters — flagged inline above.

### See also
- [03 — Engineering Concepts](03_Engineering_Concepts.md) · [04 — Core Terminology](04_Core_Terminology.md)
