# PDM Domain

Covers both the **legacy** Windows Forms C# PDM system (business-logic migration reference) and the **current** Python/PySide6 codebase's PDM↔MDB/OCD bridge.

| Document | Covers |
|---|---|
| [Legacy_PDM_Business_Logic/](./Legacy_PDM_Business_Logic/) | Full legacy-system reverse-engineering handbook (29 modules + navigation index), source-cited against the archived C# (`PDMMaintenance/*.cs`, `Global.cs`). Authoritative for legacy business rules (`BR-*` rule IDs). |
| [PDM_MDB_Bridge/](./PDM_MDB_Bridge/) | How the *current* codebase's PDM↔MDB/OCD compatibility layer works: workflow, data model, engineering-object mapping, compatibility layer, ODB/OCD integration, migration roadmap |
| [Reduction_and_Family_Rules.md](./Reduction_and_Family_Rules.md) | Canonical model for how legacy PDM derives a base article/order code from a Product + selected configuration, and the read-only compatibility layer that reproduces it |
| [Family_Boundary_Findings.md](./Family_Boundary_Findings.md) | Live-database investigation: legacy PDM has **no single family algorithm** — three separate mechanisms approximate it |
| [SKU_Configuration_Decode.md](./SKU_Configuration_Decode.md) | How a MillerKnoll SKU encodes configuration (`head.tail` format); investigation that became an implemented fix |

**Source of truth:** for legacy business rules, `Legacy_PDM_Business_Logic/`; for base-article derivation, `Reduction_and_Family_Rules.md`; for the current-codebase bridge, `PDM_MDB_Bridge/`.
