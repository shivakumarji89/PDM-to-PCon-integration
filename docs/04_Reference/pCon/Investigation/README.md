# pCon/PDM/MDB Investigation — Reading Order & Index

**Status:** Forensic, evidence-only investigation. No production code was changed by this investigation. Labels used throughout the investigation set: **FACT** (documented/observed), **INFERENCE** (derived, not itself written down), **UNKNOWN** (insufficient evidence). "MDF" is settled as **not** a real pCon.creator/OCD term anywhere; the real formats are **OCD** (CSV), **XOCD**, **XCF**, **MDB** (Access, `pcr_data_com_ocd.mdb`), and **EBASE** (release distribution) — see [PCon_Creator_Investigation.md §0.3](./PCon_Creator_Investigation.md#03-what-was-not-found-anywhere) for the full derivation.

This investigation's findings have since been split two ways:

- Findings that became **current, canonical domain knowledge** were extracted into `docs/02_Domain/` (linked below per item).
- Findings that remain **investigation narrative / synthesis** (not a single domain concept) stay in this folder.

## Reading order

1. **pCon.creator 2.22.2 Investigation** — [PCon_Creator_Investigation.md](./PCon_Creator_Investigation.md) *(stays here — narrative)*. What the pCon.creator manual documents for Article/Base Article/Variant/Properties/Options/Classes/Relation Objects/Relations/Restrictions/Pricing/Text; establishes "MDF" does not exist as a term.
2. **MDB Structure and Relationships** → [`../../../02_Domain/Repository/Repository_Model.md`](../../../02_Domain/Repository/Repository_Model.md) *(promoted to canonical Repository domain doc)*. The current MK Workbench exporter code's actual table inventory, FK chain, and write coverage.
3. **PDM ↔ pCon Concept Mapping** — [PDM_to_pCon_Mapping.md](./PDM_to_pCon_Mapping.md) *(stays here — narrative)*. Master mapping table between PDM concepts and pCon.creator concepts, including explicit non-mappings (Option, Relation Object).
4. **Base Article / Variant / Configuration Article Model** → [`../../../02_Domain/Product/Article_Configuration_Model.md`](../../../02_Domain/Product/Article_Configuration_Model.md) *(promoted to canonical Product domain doc)*. Proves there is no stored base↔final-article parent-child relationship anywhere; final article number is always a generated runtime string.
5. **Property / Option Cardinality** → [`../../../02_Domain/Engineering/Property_Model.md`](../../../02_Domain/Engineering/Property_Model.md) *(promoted to canonical Engineering domain doc)*. Zero/one/multiple values per property, multi-value-selection support, dependency-chain handling.
6. **Dependency & Exclusion Model** → [`../../../02_Domain/Engineering/Dependency_Model.md`](../../../02_Domain/Engineering/Dependency_Model.md) *(promoted)*. The six PDM dependency/exclusion mechanisms, mapped (or not) onto OCD constructs.
7. **Relation Object / Configuration Model** → [`../../../02_Domain/Engineering/Relation_Model.md`](../../../02_Domain/Engineering/Relation_Model.md) *(promoted)*. The OCD spec's relation model vs. the MDB schema vs. what the current generator actually produces (2 of 6 types, 1 of 5 binding levels).
8. **Nevi End-to-End Trace** → [`../../../02_Domain/Article_Encoding/Variant_Code_and_Final_Article_Number.md`](../../../02_Domain/Article_Encoding/Variant_Code_and_Final_Article_Number.md) *(promoted)*. Real production SKU `DWE42AN4YSNBADNN` traced from PDM through ConfigCode.
9. **"MDF" Export/Import Requirements** → [`../../../99_Archive/Superseded/MDF_Export_Import_Requirements.md`](../../../99_Archive/Superseded/MDF_Export_Import_Requirements.md) *(archived — encoding-specific claims superseded by [Article_Encoding.md](../../../02_Domain/Article_Encoding/Article_Encoding.md); general export/import contract material still valid)*.
10. **Canonical Model** — [Canonical_Model_Proposal.md](./Canonical_Model_Proposal.md) *(stays here — narrative synthesis)*. Proposes the canonical engineering model (built on the existing `Snapshot` architecture).
11. **Automation Strategy** → [`../../../02_Domain/Permutation/Permutation_Model.md`](../../../02_Domain/Permutation/Permutation_Model.md) *(promoted to canonical Permutation domain doc)*. Classifies every mapping into deterministic (A) / conditionally deterministic (B) / ambiguous (C) / unsupported (D).
12. **Round-Trip Validation** → [`../../../03_Workflows/QA_Validation.md`](../../../03_Workflows/QA_Validation.md) *(promoted to canonical QA workflow doc)*. Per-entity-type validation plan for PDM→MK Workbench→MDB/OCD→pCon Creator→MDB/OCD→MK Workbench.
13. **Unknowns & Decisions Register** — [Open_Questions_and_Decisions.md](./Open_Questions_and_Decisions.md) *(stays here — narrative register)*. One row per UNKNOWN/GAP/disagreement raised across items 1-12. **Note:** does not yet include the newer gap list from `Article_Encoding.md` §17 — see that document directly for the freshest open items on encoding.
14. **Complete Investigation (Executive Summary)** — [Investigation_Summary.md](./Investigation_Summary.md) *(stays here — narrative summary)*. Answers the original 14 brief questions concisely.

## Newest follow-on investigation (deeper article-encoding pass)

A later, more evidence-dense pass went specifically into Article Encoding/CodeScheme using real HMX repository CSV data, and produced a ranked, actionable gap list against the current generator code. These are the freshest and most actionable documents from the whole investigation arc:

- [`../../../02_Domain/Article_Encoding/Article_Encoding.md`](../../../02_Domain/Article_Encoding/Article_Encoding.md) — real CodeScheme grammar findings (Aeron, Cosm, Atlas, Civic_tables, Lino, Hush, Fold)
- [`../../../02_Domain/Permutation/Permutation_Gap_Analysis.md`](../../../02_Domain/Permutation/Permutation_Gap_Analysis.md) — 9-item ranked gap/fix-priority table derived from it

## Single most important finding (from the original 00-14 arc)

Current MK Workbench relation-object generation covers only **2 of 6 OCD relation types**
(Precondition, Action) in **2 of 5 domains** (Configuration, Pricing), and only ever binds
at the **PropertyValue** level even though Article/Property-class/Property-level bindings
are schema-ready and already expected by the reverse-engineering reader. Several PDM-side
dependency/exclusion mechanisms that plausibly need Constraint-type relations
(`AttributeValueExclusions`, `CatalogueProductOptionExclusions`,
`CatalogueItemOptionExclusions`) are not confirmed wired into export at all. See
[Relation_Model.md](../../../02_Domain/Engineering/Relation_Model.md),
[Permutation_Model.md](../../../02_Domain/Permutation/Permutation_Model.md), and
[Open_Questions_and_Decisions.md](./Open_Questions_and_Decisions.md) (register row U20) for the full evidence trail.
