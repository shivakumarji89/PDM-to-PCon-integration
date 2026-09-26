# 00 — pCon/PDM/MDB Investigation Index

**Status:** Forensic, evidence-only investigation. No production code changed, nothing
committed. Labels used throughout: **FACT** (documented/observed), **INFERENCE** (derived,
not itself written down), **UNKNOWN** (insufficient evidence). "MDF" is settled as not a
real pCon.creator/OCD term anywhere in this investigation — see file 01 §0.3/§15 and file
09 §0; the real formats are **OCD** (CSV), **XOCD**, **XCF**, **MDB** (Access,
`pcr_data_com_ocd.mdb`), and **EBASE** (release distribution).

## Reading order

1. **[01 — pCon.creator 2.22.2 Investigation](01_pcon_creator_2_22_2_investigation.md)** —
   what the pCon.creator manual documents for Article/Base Article/Variant/Properties/
   Options/Classes/Relation Objects/Relations/Restrictions/Pricing/Text; establishes "MDF"
   does not exist as a term.
2. **[02 — MDB Structure and Relationships](02_mdb_structure_and_relationships.md)** — the
   *current* MK Workbench exporter code's actual table inventory, FK chain, and write
   coverage; flags the stale `docs/pcon_reference/database_relationships/` tree.
3. **[03 — PDM ↔ pCon Concept Mapping](03_pdm_to_pcon_mapping.md)** — the master mapping
   table between PDM concepts and pCon.creator concepts, including the explicit
   non-mappings (Option, Relation Object).
4. **[04 — Base Article / Variant / Configuration Article Model](04_base_article_variant_configuration.md)**
   — proves there is no stored base↔final-article parent-child relationship anywhere;
   final article number is always a generated runtime string.
5. **[05 — Property / Option Cardinality](05_property_option_cardinality.md)** —
   zero/one/multiple values per property, multi-value-selection support (none at runtime),
   and dependency-chain handling.
6. **[06 — Dependency & Exclusion Model](06_dependency_and_exclusion_model.md)** — the six
   PDM dependency/exclusion mechanisms, sorted into availability / exclusion / scope-filter
   categories, mapped (or not) onto OCD constructs.
7. **[07 — Relation Object / Configuration Model](07_relation_object_configuration_model.md)**
   — the OCD spec's relation model vs. the MDB schema's join-table normalization vs. what
   the current generator actually produces (2 of 6 types, 1 of 5 binding levels).
8. **[08 — Nevi End-to-End Trace](08_nevi_end_to_end_trace.md)** — real production SKU
   `DWE42AN4YSNBADNN` traced from PDM through ConfigCode; breaks into GAP from
   Options/Dependencies/RelationObject/MDB/pCon Creator onward (no live query run).
9. **[09 — "MDF" Export/Import Requirements](09_mdf_export_import_requirements.md)** —
   full field-level OCD 4.0 import contract, XCF catalog contract, and pCon.creator's
   export/release-dataset shape; the primary source for the "MDF isn't real" finding.
10. **[10 — Canonical Model](10_canonical_model.md)** — proposes the canonical engineering
    model (built on the existing `Snapshot` architecture), with both requested flow
    diagrams and a reuse/extend/missing breakdown per component.
11. **[11 — Automation Strategy](11_automation_strategy.md)** — classifies every mapping
    from docs 03-08 into deterministic (A) / conditionally deterministic (B) / ambiguous,
    Review Required (C) / unsupported (D).
12. **[12 — Round-Trip Validation](12_round_trip_validation.md)** — per-entity-type
    validation plan for PDM→MK Workbench→MDB/OCD→pCon Creator→MDB/OCD→MK Workbench, aware
    that current export coverage is incomplete (2/6 relation types, no Option table, etc.).
13. **[13 — Unknowns & Decisions Register](13_unknowns_and_decisions.md)** — one register
    row per UNKNOWN/GAP/disagreement raised across files 01-12, with resolving evidence and
    whether it blocks automation or is a pure decision. Does not resolve anything.
14. **[14 — Complete Investigation (Executive Summary)](14_complete_investigation.md)** —
    answers all 14 brief questions concisely, citing which prior doc each answer comes from.

## Single most important finding

Current MK Workbench relation-object generation covers only **2 of 6 OCD relation types**
(Precondition, Action) in **2 of 5 domains** (Configuration, Pricing), and only ever binds
at the **PropertyValue** level even though Article/Property-class/Property-level bindings
are schema-ready and already expected by the reverse-engineering reader. Several PDM-side
dependency/exclusion mechanisms that plausibly need Constraint-type relations
(`AttributeValueExclusions`, `CatalogueProductOptionExclusions`,
`CatalogueItemOptionExclusions`) are not confirmed wired into export at all. See files 07,
11, and 13 (register row U20) for the full evidence trail.
