# MK Product Workbench — Engineering Handbook

> **The primary technical engineering reference for the MK Product Workbench and every engineering
> component built within it** — Explorer, Dashboard, Workspace, MDB integration, OCD, ODB, OAP, Metatype,
> OFML, the Snapper generator, validation, and all future engineering modules.

This handbook consolidates the authoritative **OFML** (Office Furniture Modelling Language) engineering
specifications published by **EasternGraphics / IBA** into a single, cross-referenced knowledge base. The
source documents are **not** application-specific — they define the industry engineering standards the whole
ecosystem follows. Everything MK Product Workbench builds should conform to them.

---

## Start here

1. **[00_Engineering_Overview](00_Engineering_Overview.md)** — what OFML is and how the ecosystem fits together.
2. **[01_Document_Map](01_Document_Map.md)** — source→handbook mapping, reading order, knowledge hierarchy.
3. **[19_Glossary](19_Glossary.md)** — the language of OFML (A–Z).

---

## Contents

| # | Document | Purpose |
|---|----------|---------|
| — | [README](README.md) | This index |
| 00 | [Engineering Overview](00_Engineering_Overview.md) | Ecosystem at a glance, core concepts, end-to-end flow |
| 01 | [Document Map](01_Document_Map.md) | Source mapping, reading order, knowledge hierarchy, cross-refs |
| 02 | [Architecture](02_Architecture.md) | Layered OFML architecture, Parts I–VI, data domains, pCon consumption |
| 03 | [Engineering Concepts](03_Engineering_Concepts.md) | System concepts + the OFML conceptual model |
| 04 | [Core Terminology](04_Core_Terminology.md) | Curated quick-reference terms by domain |
| 05 | [Engineering Workflows](05_Engineering_Workflows.md) | Every workflow: purpose, inputs, outputs, deps, rules, results |
| 06 | [OFML](06_OFML.md) | The core standard: object model, packages, layers, materials, GO, DSR |
| 07 | [OCD](07_OCD.md) | Commercial Data — articles, properties, options, relations, prices, texts |
| 08 | [ODB](08_ODB.md) | OFML Database — geometry / object description |
| 09 | [OAP](09_OAP.md) | OFML Aided Planning — planning behaviour, methods, data creation |
| 10 | [Metatype](10_Metatype.md) | Metatype tables — inter-product configuration & generation |
| 11 | [Product Model](11_Product_Model.md) | Product / article / property / option models |
| 12 | [Validation Rules](12_Validation_Rules.md) | Every validation / constraint / dependency / ordering rule (VR-*) |
| 13 | [Naming Standards](13_Naming_Standards.md) | Identifiers, program IDs, article numbers, table/style naming |
| 14 | [Generation Process](14_Generation_Process.md) | Metatype / GO / Snapper-OBX / OCD-OAP data generation |
| 15 | [File Formats](15_File_Formats.md) | OCD/ODB/OAP/GO tables, OMATS, OLAYERS, XCF, OBX formats |
| 16 | [Configuration](16_Configuration.md) | Configuration model — properties, values, relations, variants |
| 17 | [Best Practices](17_Best_Practices.md) | Data-creation & engineering best practices, common patterns |
| 18 | [Design Principles](18_Design_Principles.md) | Engineering philosophy & principles to follow |
| 19 | [Glossary](19_Glossary.md) | Exhaustive A–Z glossary of engineering terms |

---

## The domains at a glance

| Acronym | Full name | Role | Doc |
|---------|-----------|------|-----|
| **OFML** | Office Furniture Modelling Language | The core standard (object model, geometry, materials, layers) | [06](06_OFML.md) |
| **OCD** | OFML Commercial Data (Part IV) | Commercial/configuration data: articles, properties, options, relations, prices, texts | [07](07_OCD.md) |
| **ODB** | OFML Database | Declarative geometry / object description | [08](08_ODB.md) |
| **OAP** | OFML Aided Planning | Planning behaviour (interactors, actions, methods) | [09](09_OAP.md) |
| **Metatype (MT)** | OFML Metatypes | Tables enabling inter-product configuration & generation | [10](10_Metatype.md) |
| **GO** | Generic Objects | Parametric/generated object tables | [06](06_OFML.md), [14](14_Generation_Process.md) |
| **OMATS** | OFML Materials | Material (PBR) definitions | [06](06_OFML.md), [15](15_File_Formats.md) |
| **OLAYERS** | OFML Layers | Layer grammar & tags | [06](06_OFML.md), [15](15_File_Formats.md) |

---

## Using this handbook in MK Product Workbench

- Treat these specifications as **authoritative**. Where the running implementation and a spec disagree, the
  spec wins — reconcile toward it.
- When designing any engineering feature (Explorer/Dashboard/Workspace/MDB/OCD/ODB/OAP/Metatype/Snapper/
  validation), consult the relevant domain doc **plus** [12_Validation_Rules](12_Validation_Rules.md),
  [13_Naming_Standards](13_Naming_Standards.md), and [18_Design_Principles](18_Design_Principles.md).
- Items that could not be proven from the source specifications are marked **`UNKNOWN`** throughout — resolve
  these against the original specs (or a domain owner) before relying on them.

---

## Sources & scope

Consolidated from **24 OFML specification documents** (~35,000 lines) and OBX product-data examples in
`MK_OFML_Testsuite/Docs/`. Application-specific design docs (`Docs/superpowers/`) and tooling folders are
**out of scope** — see [01_Document_Map](01_Document_Map.md) for the complete source→handbook mapping.

*Copyright of the underlying specifications remains with EasternGraphics GmbH / IBA. This handbook is an
internal engineering reference that reorganizes and cross-references that material; it does not replace the
original specifications.*
