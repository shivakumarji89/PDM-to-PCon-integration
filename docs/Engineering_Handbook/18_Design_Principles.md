# 18 — Design Principles

**Source:** OFML specifications (EasternGraphics/IBA), consolidated for the MK Product Workbench Engineering Handbook.
**Status:** Consolidated from specification docs; unclear items marked `UNKNOWN`.

---

## 1. Purpose

This document distils the **engineering philosophy and design principles** expressed
across the OFML specifications, and reframes them as **principles the MK Product
Workbench development should follow**. Each principle is grounded in the standard and
cross-referenced to the relevant handbook document.

---

## 2. Principle 1 — Standardization under Industry Governance

**From the specs.** OFML is a *standardized* data description format issued on behalf of
the industry association (BSO, now **IBA**), with Parts I–III developed by
EasternGraphics and the remaining parts specified by the standardization committee. A
single, governed standard is what lets *an unlimited number of software vendors* build
interoperable systems and avoids monopolization.

**For the Workbench.**
- Treat the published OFML/OCD/MT/OAP/ODB specifications as the **authoritative
  contract**; do not invent divergent local conventions.
- Track **spec versions** explicitly (OCD 2.1…5.0, OAP 1.x, MT 1.18, DSR 3.x, XCF) and
  the application support matrix (see [06_OFML](06_OFML.md) §12).
- Prefer standardized formats over proprietary ones where a standard exists.

---

## 3. Principle 2 — Separation of Commercial and Graphical Data

**From the specs.** OFML deliberately splits **commercial data** (non-graphical selling
data — texts, configuration, pricing; OCD) from **graphical data** (2D/3D geometry,
materials) and joins them through explicit **mapping data** (OAM). Commercial data can
even come from an *external* product database via the Part III generic PDM interface.

**For the Workbench.**
- Keep commercial concerns (price, article texts, configuration relations) **decoupled**
  from geometry/material concerns in code and data models.
- Model the **mapping** between the two domains as a first-class, explicit artifact — not
  an implicit assumption.
- Design so an external/non-OFML commercial source can be substituted behind the same
  interface.
- See [02_Architecture](02_Architecture.md) §4, [07_OCD](07_OCD.md).

---

## 4. Principle 3 — Manufacturer & Platform Independence

**From the specs.** A core OFML goal is *independence of system/interface platforms and
of any concrete runtime environment*, and vendor independence so many applications stay
data-compatible despite different orientation. This yields technological uniformity
between manufacturer, trade and end-user systems.

**For the Workbench.**
- Do not hard-code assumptions tied to a single manufacturer, sales app, or OS.
- Encode manufacturer specifics as **data** (DSR keys, program IDs), not as branching
  logic.
- Keep the core engine free of pCon-specific coupling; consume/produce standard formats.

---

## 5. Principle 4 — Unambiguous Identification

**From the specs.** OFML relies on **unambiguous identifiers** throughout:

- **Program ID** identifies an OFML library/program.
- **Article number** unambiguously identifies a product (within PPS, or at least within
  a commercial series). A **basic article number** identifies a configurable product; the
  **final article number** adds the **variant code** encoding the chosen characteristic
  values.
- **DSR manufacturer key** (`<MAN>`) and **program/series key** (`<SERIES>`) identify
  manufacturer and library and flow into **OLAYERS** layer names.
- Type identifiers + article numbers are the **cross-reference glue** between OFML parts.
- A *(manufacturer ID, series ID, article number)* triple must resolve to exactly one
  product library.

**For the Workbench.**
- Make identifiers **explicit, validated and stable**; never overload or reuse them.
- Preserve the **basic vs final** article-number distinction and treat the **variant
  code** as the canonical encoding of a configuration.
- Enforce the resolution-triple uniqueness as an invariant.
- See [11_Product_Model](11_Product_Model.md), [13_Naming_Standards](13_Naming_Standards.md),
  [12_Validation_Rules](12_Validation_Rules.md).

---

## 6. Principle 5 — Backward Compatibility & Explicit Versioning

**From the specs.** OFML packages carry **unique version numbers**; OMATS **auto-converts
OMATS1 materials to OMATS2** to guarantee downward-compatible processing; the
application-support matrix tracks exactly which format versions each release accepts.

**For the Workbench.**
- Version every distribution/installation unit; never ship an unversioned artifact.
- Provide **forward-migration/conversion** paths rather than breaking older data.
- Validate input against the **declared** spec version; degrade gracefully when a
  consumer supports only older versions.
- See [16_Configuration](16_Configuration.md), [14_Generation_Process](14_Generation_Process.md).

---

## 7. Principle 6 — Reuse via Libraries & Base Classes

**From the specs.** OFML is built on the object-oriented paradigm with **single
inheritance** and layered libraries: **base libraries** provide series-independent
classes that form the development basis for **product libraries**; **GO (Part II)**
supplies ready-made interaction/behaviour building blocks; abstract types capture
generalizations while concrete types are instantiable.

**For the Workbench.**
- Factor **series-independent logic into reusable base components**; derive product-
  specific data from them.
- Prefer **composition of standard building blocks** (GO-style) over bespoke
  re-implementation of common interactions.
- Model shared concepts as **abstract types**; keep instantiable, concrete data thin.
- See [06_OFML](06_OFML.md) §3, §8; [14_Generation_Process](14_Generation_Process.md).

---

## 8. Principle 7 — Generic, Interface-Based Product-Data Access (Part III)

**From the specs.** Part III defines a **generic product-data-management interface**
(`OiPDManager`, `OiProductDB`) so applications reach commercial data through one abstract
interface — whether the source is OCD or an external product database mapped to the Part
III data model.

**For the Workbench.**
- Program against a **generic product-data interface**, not a concrete storage format.
- Keep the data model at the boundary aligned with the Part III commercial-data model so
  alternative back-ends remain pluggable.
- See [11_Product_Model](11_Product_Model.md), [07_OCD](07_OCD.md).

---

## 9. Principle 8 — Semantic, Holistic Modelling

**From the specs.** OFML applies **semantic modelling** so virtual objects match real
products, and combines geometric, visual, interactive and semantic features in **one
holistic data model**, capturing **real configuration logic and parametrics** (rules,
properties, relations).

**For the Workbench.**
- Model products by their **real-world semantics and configuration rules**, not merely
  their geometry.
- Keep **rules/relations** between characteristics first-class and enforce them
  consistently across configuration, pricing and visualization.
- See [16_Configuration](16_Configuration.md), [11_Product_Model](11_Product_Model.md).

---

## 10. Principle 9 — Consistent Naming & Registration Discipline

**From the specs.** Names must be **globally unique** (type names unique within module
and globally, via prefixes/namespaces); **OLAYERS** enforces a strict layer-name grammar
(`72_<MAN>_<SERIES>_<MOD>[_<TAG>]`, case-insensitive); **DSR** centrally registers
manufacturers, concerns and packages with defined keys and directory structures.

**For the Workbench.**
- Adopt **strict, grammar-driven naming** and validate it automatically.
- Centralize **registration/registry** of manufacturers, programs and packages; derive
  names from registered keys.
- Treat naming violations as **errors**, not warnings.
- See [13_Naming_Standards](13_Naming_Standards.md), [12_Validation_Rules](12_Validation_Rules.md),
  [15_File_Formats](15_File_Formats.md).

---

## 11. Principle 10 — Coexistence, Not Replacement

**From the specs.** OFML explicitly aims at **coexistence with existing CAD** solutions
via compatible formats / conversion tools rather than wholesale replacement.

**For the Workbench.**
- Favour **interoperability and conversion** with adjacent systems over closed
  replacement.
- Provide import/export bridges to established formats where feasible.

---

## 12. Principle Summary

| # | Principle | Primary source concepts | Handbook links |
|---|-----------|-------------------------|----------------|
| 1 | Standardization / IBA governance | governed standard, versioned parts | [06_OFML](06_OFML.md) |
| 2 | Commercial ⟂ graphical separation | OCD vs graphical + OAM mapping | [02_Architecture](02_Architecture.md), [07_OCD](07_OCD.md) |
| 3 | Manufacturer/platform independence | vendor/platform independence | [02_Architecture](02_Architecture.md) |
| 4 | Unambiguous identification | program ID, article/variant code, DSR keys | [11_Product_Model](11_Product_Model.md), [13_Naming_Standards](13_Naming_Standards.md) |
| 5 | Backward compatibility & versioning | package versions, OMATS auto-convert | [16_Configuration](16_Configuration.md) |
| 6 | Reuse via libraries/base classes | base→product libraries, GO, inheritance | [06_OFML](06_OFML.md), [14_Generation_Process](14_Generation_Process.md) |
| 7 | Generic product-data interface | Part III PDM interface | [11_Product_Model](11_Product_Model.md) |
| 8 | Semantic, holistic modelling | rules, properties, parametrics | [16_Configuration](16_Configuration.md) |
| 9 | Naming & registration discipline | namespaces, OLAYERS, DSR | [13_Naming_Standards](13_Naming_Standards.md) |
| 10 | Coexistence, not replacement | CAD coexistence | [02_Architecture](02_Architecture.md) |

---

## 13. Related Handbook Documents

- [02_Architecture](02_Architecture.md) — the architecture these principles shape.
- [06_OFML](06_OFML.md) — the standard the principles derive from.
- [11_Product_Model](11_Product_Model.md), [12_Validation_Rules](12_Validation_Rules.md),
  [13_Naming_Standards](13_Naming_Standards.md), [19_Glossary](19_Glossary.md).
