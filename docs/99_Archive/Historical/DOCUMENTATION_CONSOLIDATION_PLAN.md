**STATUS: ARCHIVED**
**SUPERSEDED BY:** [`../../DOCUMENTATION_CLEANUP_REPORT.md`](../../DOCUMENTATION_CLEANUP_REPORT.md)

This was the pre-restructuring audit. The restructuring it proposed has since been executed; the paths and file inventory below describe the **old** documentation tree, not the current one. Kept here as the historical record of the audit reasoning.

---

# Documentation Consolidation Plan (historical — pre-restructuring audit)

**Status:** Audit / planning only. No files have been moved, renamed, merged, or deleted as part of this pass.
**Scope:** Full repository documentation tree (173 files: 169 under `docs/`, plus `README.md`, `project_structure.txt`, `.pytest_cache/README.md`, `repo_sync_agent/README.md` at other locations). `services/`, `ui/`, `workflow/`, `tests/`, and `main.py` contain no documentation files and were not touched. No `MK_OFML_Testsuite/` directory exists inside this repository (it is only referenced as an external sibling project inside some investigation docs).

This document is descriptive, not destructive. It records what exists, groups it by subject, flags duplication/overlap, and proposes (but does not execute) a target structure.

---

## 1. Inventory Summary

| Area | File count | Total size (approx.) | Nature |
|---|---|---|---|
| Root loose files | 4 | ~64 KB (dominated by `project_structure.txt`) | Mixed (1 stale README, 1 mechanical artifact, 2 dependency manifests — not doc content) |
| `.pytest_cache/README.md`, `repo_sync_agent/README.md` | 2 | <1 KB | Tool-generated / utility notes |
| `docs/` loose top-level files | 7 | ~330 KB | PDM reduction-engine investigation trio + 2 standalone investigations |
| `docs/Engineering_Handbook/` | 21 | ~340 KB | Curated OFML/OCD/ODB/OAP industry reference |
| `docs/Legacy_PDM_Business_Logic/` (+ `Index/`, `Index/parts/`) | 41 | ~1.1 MB | Legacy C# PDM reverse-engineering handbook (authoritative) |
| `docs/PDM_MDB_Engineering/` | 8 | ~75 KB | Current Python/PySide6 codebase PDM↔MDB/OCD analysis |
| `docs/pcon_reference/` (architecture docs + vendor specs + `database_relationships/` + `tables/`) | 66 | several MB | Vendor OFML/OCD/OAP/MT spec corpus + hand-built architecture/table reference |
| `docs/metatype_investigation/` | 8 | ~65 KB | Forensic Metatype (`go_*`) investigation against real HMX repo |
| `docs/pcon_investigation/` (00–14) | 15 | ~285 KB | Forensic pCon/OCD/MDB investigation (main arc) |
| `docs/pcon_investigation/pcon_planner/` (19, 24) | 2 | ~43 KB | **Untracked.** Newest, most actionable article-encoding/CodeScheme findings |

Total: **173 documentation files** considered.

---

## 2. Documents Grouped by Subject

### A. Overall MK Workbench architecture
- `README.md` (root) — stale, describes an early Phase-1 scaffold
- `project_structure.txt` — mechanical `tree` dump, not prose
- `docs/PDM_MDB_Engineering/07_Builder_Workspace.md`
- `docs/pcon_reference/Architecture.md`, `GeneratorArchitecture.md`

### B. PDM investigation
- `docs/pdm-family-boundary.md`
- `docs/reduction-investigation.md`
- `docs/legacy-pdm-reduction-engine.md`
- `docs/legacy-pdm-implementation-status.md`
- `docs/SKU_Config_Decode_Findings.md`
- `docs/pcon_investigation/03_pdm_to_pcon_mapping.md`
- `docs/PDM_MDB_Engineering/02_PDM_Data_Model.md`

### C. Repository / MDB model
- `docs/PDM_MDB_Engineering/01_MDB_Engineering_Workflow.md`, `03_Engineering_Object_Mapping.md`, `04_Compatibility_Layer.md`
- `docs/pcon_investigation/02_mdb_structure_and_relationships.md`
- `docs/pcon_reference/database_relationships/` (all 9 files) + `tables/` (14 files)
- `docs/pcon_reference/BuilderTableMapping.md` **and** `docs/pcon_reference/database_relationships/BuilderTableMapping.md` (name collision — see §4)

### D. Snapshot
- No dedicated document exists. Snapshot is referenced only in passing inside `PDM_MDB_Engineering` and `pcon_reference/database_relationships`. **Gap — see §9.**

### E. Product / Article / Class model
- `docs/Legacy_PDM_Business_Logic/06_Articles.md`, `05_Products.md`, `04_Product_Categories.md`
- `docs/pcon_investigation/04_base_article_variant_configuration.md`
- `docs/Engineering_Handbook/11_Product_Model.md`
- `docs/pcon_reference/OCDTables.md`, `docs/pcon_reference/database_relationships/tables/tCOMd_Article.md`, `tCOMd_ArtBase.md`, `tCOMd_ArticleClass.md`, `tCOMd_Class.md`

### F. Property / PropertyValue model
- `docs/Legacy_PDM_Business_Logic/07_Attributes.md`, `08_Property_Values.md`, `09_Options.md`, `10_Option_Values.md`
- `docs/pcon_investigation/05_property_option_cardinality.md`
- `docs/pcon_reference/database_relationships/tables/tCOMd_Property.md`, `tCOMd_PropValue.md`
- `docs/pcon_reference/property_interface_2.10_en.md` (vendor spec)

### G. Relation / Dependency / Exclusion model
- `docs/pcon_investigation/06_dependency_and_exclusion_model.md`, `07_relation_object_configuration_model.md`
- `docs/Engineering_Handbook/12_Validation_Rules.md`

### H. Permutation generation
- `docs/pcon_investigation/pcon_planner/24_article_encoding_findings.md` (deepest, most current evidence)
- `docs/pcon_investigation/pcon_planner/19_mk_workbench_mapping.md` (gap/action summary)
- `docs/pcon_investigation/11_automation_strategy.md`

### I. Article Encoding / CodeScheme
- `docs/pcon_investigation/pcon_planner/24_article_encoding_findings.md` — **primary, authoritative** (real HMX CSV evidence: Aeron, Cosm, Atlas, Civic_tables, Lino, Hush, Fold)
- `docs/pcon_investigation/pcon_planner/19_mk_workbench_mapping.md` — gap table derived from file 24
- `docs/pcon_investigation/09_mdf_export_import_requirements.md` (older pass, title retained for history but content already clarifies no "MDF" term exists)

### J. Variant Code / K. Final Article Number
- `docs/pcon_investigation/04_base_article_variant_configuration.md`
- `docs/pcon_investigation/08_nevi_end_to_end_trace.md`
- `docs/pcon_investigation/pcon_planner/19_mk_workbench_mapping.md` (item 7/8 in its gap table)

### L. Pricing
- `docs/Legacy_PDM_Business_Logic/18_Pricing.md`
- `docs/pcon_reference/PriceGeneration.md`
- `docs/pcon_reference/database_relationships/tables/tCOMd_Price.md`, `tCOMd_PriceList2.md`
- `docs/pcon_reference/AN-2017-01_PriceLists_DataCreation-EN.md` (vendor)
- `docs/pcon_investigation/pcon_planner/19_mk_workbench_mapping.md` (item 9 — confirms no change needed)

### M. OBX generation
- `docs/Legacy_PDM_Business_Logic/23_Generation.md`
- `docs/pcon_reference/PackagingPipeline.md`
- `docs/pcon_investigation/pcon_planner/24_article_encoding_findings.md` §16 (diffs current OBX code against real grammar)

### N. QA / validation
- `docs/Engineering_Handbook/12_Validation_Rules.md`
- `docs/pcon_investigation/12_round_trip_validation.md`
- `docs/metatype_investigation/07_metatype_validation_plan.md`

### O. pCon.planner investigation
- `docs/pcon_investigation/01_pcon_creator_2_22_2_investigation.md`
- `docs/pcon_investigation/pcon_planner/19_mk_workbench_mapping.md`, `24_article_encoding_findings.md`
- `docs/pcon_investigation/00_investigation_index.md`, `13_unknowns_and_decisions.md`, `14_complete_investigation.md`

### P. HMX repository investigation
- `docs/metatype_investigation/01_metatype_repository_structure.md`, `02_metatype_go_file_inventory.md`, `03_metatype_data_relationships.md`
- `docs/pcon_investigation/pcon_planner/24_article_encoding_findings.md` (independent, later HMX read focused on `ocd_*` not `go_*`)

### Q. MK_OFML_Testsuite comparison
- No documents exist; no Testsuite directory exists in this repo. **Gap — not applicable here.**

### R. UI/workflow architecture
- `docs/PDM_MDB_Engineering/07_Builder_Workspace.md`
- No dedicated `ui/`/`workflow/` design docs exist elsewhere. **Gap — see §9.**

### S. Historical investigation / abandoned approaches
- `docs/legacy-pdm-implementation-status.md`, `docs/legacy-pdm-reduction-engine.md`, `docs/reduction-investigation.md` (three passes at the same question — see §4)
- `docs/metatype_investigation/05_polymorphic_metatype_workflow.md`, `06_metatype_python_workflow_design.md` (proposed, unimplemented)

### T. Open questions / unresolved items
- `docs/pcon_investigation/13_unknowns_and_decisions.md` (consolidated register — authoritative)
- `docs/pcon_investigation/pcon_planner/24_article_encoding_findings.md` §17 (its own gap list, not yet merged into file 13)
- `docs/metatype_investigation/07_metatype_validation_plan.md`

---

## 3. Consolidation / Classification Table

Legend: KEEP / MERGE / ARCHIVE / DUPLICATE / SUPERSEDED / REFERENCE_ONLY / TEMPORARY

| Existing File | Subject | Classification | Authoritative Target | Reason | Unique Evidence to Preserve |
|---|---|---|---|---|---|
| `README.md` (root) | A | MERGE | `README.md` (rewritten) | Describes a Phase-1 scaffold that no longer matches the codebase's actual scope | None — needs replacement, not extraction |
| `project_structure.txt` | A | TEMPORARY | — | Mechanical, garbled `tree` dump; regenerable on demand, not prose documentation | None |
| `.pytest_cache/README.md` | — | TEMPORARY | — | Stock pytest tool output; should be gitignored | None |
| `repo_sync_agent/README.md` | A | REFERENCE_ONLY | itself | Self-contained utility note; states the folder should live outside the repo — flag, don't merge | The relocation instruction itself |
| `docs/pdm-family-boundary.md` | B | KEEP | itself | Dated live-DB investigation (2026-09-19), confirms "no single family algorithm" — primary evidence | Live `PDMLive` (DBCHIP12V) query findings, 3-mechanism breakdown |
| `docs/reduction-investigation.md` | B | MERGE | `docs/legacy-pdm-reduction-engine.md` | Earlier/narrower pass over the same "how legacy PDM derives base articles" question | `OrderCodeFormatString` parser findings, attribute-value exclusion rules |
| `docs/legacy-pdm-reduction-engine.md` | B | KEEP (post-merge → becomes target) | itself | Most complete of the three; explicitly independent of the 591-row sample | Generic reduction model definition |
| `docs/legacy-pdm-implementation-status.md` | B | MERGE | `docs/legacy-pdm-reduction-engine.md` | Status tracker for the same effort, not a separate finding | Implementation-status checklist (LegacyPDMCompatRepository scope) |
| `docs/SKU_Config_Decode_Findings.md` | B/J | KEEP | itself | Investigation-turned-implemented-fix; heavily cross-referenced by pcon_investigation as ground truth | `head.tail` SKU decode logic, Nevi/DWE4 evidence |
| `docs/DPS_Original_Extraction_SQL.md` | B | REFERENCE_ONLY | itself | Mechanical, heuristic SQL extraction (908 statements, 46 files) underpinning Legacy_PDM_Business_Logic; not hand-curated prose | Every extracted SQL statement with source file/line |
| `docs/Engineering_Handbook/README.md` + `00`–`19` (21 files) | multiple (industry OFML/OCD/ODB/OAP reference) | KEEP | itself (whole set treated as one unit) | Internally consistent, cross-linked, explicitly industry-standard (not MK-specific); no overlap found with other trees | Full OFML/OCD/ODB/OAP/Metatype conceptual reference, validation-rule IDs, glossary |
| `docs/Legacy_PDM_Business_Logic/README.md` + `00`–`28` (29 files) | E, F, L, M, N (legacy C# system) | KEEP | itself (whole set) | Source-cited (`.cs` file/line references), `BR-*` rule-ID system, explicitly "verified from source unless UNKNOWN" | All `BR-*` business rules, class/method citations, SQL patterns, data model |
| `docs/Legacy_PDM_Business_Logic/Index/` (11 files) + `Index/parts/` (6 files) | navigation layer over above | KEEP | itself | Explicitly does not duplicate module docs — pure index/cross-reference | Migration_Checklist go/no-go status per module |
| `docs/PDM_MDB_Engineering/01`–`08` (8 files) | C, B (current codebase analysis) | KEEP | itself | Current-code-grounded (cites `services/mdb_service.py`, `PDMToMDBService`, etc.); distinct purpose from Legacy_PDM_Business_Logic (current vs. legacy system) and from pcon_investigation (what exists vs. what pCon requires) | Engineering-object↔PDM-object mapping, gap-closure roadmap |
| `docs/pcon_reference/README.md`, `Architecture.md`, `GeneratorArchitecture.md`, `PackagingPipeline.md`, `OCDTables.md`, `BuilderTableMapping.md`, `ComGroup.md`, `Relationships.md`, `VariantConditions.md`, `PriceGeneration.md`, `Summary.md` (11 files) | A, C, H, J, L, M | KEEP | itself | Hand-authored, current, cross-linked to specific service files; explicit purpose statement (avoid re-reading legacy C# source) | Builder→OCD table mapping, ComGroup/relation/variant-condition/pricing design notes |
| `docs/pcon_reference/BuilderTableMapping.md` vs `docs/pcon_reference/database_relationships/BuilderTableMapping.md` | C | KEEP both, RENAME to disambiguate (not done in this pass) | both, under distinct names | Same filename, different scope (general Builder→OCD vs. Builder→`tCOMd_*` specifically) — real content difference, not duplication, but name collision risks confusion | Both mapping directions must survive |
| `docs/pcon_reference/database_relationships/` (README + 8 files) | C | KEEP | itself | Reverse-engineered against `helpers/mdb_helper.py`, `services/mdb_service.py`, `services/workspace_snapshot_builder.py`; feeds a future "MDB Writer" | ERD, dependency graph, read/write order, validation rules |
| `docs/pcon_reference/database_relationships/tables/` (README + 13 `tCOMd_*` files) | C, E, F, L | KEEP | itself | One authoritative file per real OCD table, uniform template | PK/FK/Builder-source/generation-stage per table |
| `docs/pcon_reference/*_en.md` and app-note PDFs-as-markdown (27 vendor spec files: `ofml_20r3_en.md`, `ocd_4.3_en.md`, `MT_1.18.0_en.md`, `odb_2.4_en.md`, `oap_1.6.1-en.md`, `AppNote_OAP_DataCreation_EN.md`, `methods4OAP.md`, `article_interface_1.4_en.md`, `dsr-3.7_en.md`, `property_interface_2.10_en.md`, `GO_1.12.0.md`, `xocd_4.3.2_en.md`, `omats_2.2_en.md`, `OLAYERS_1.3.1_en.md`, `OLAYERS-TAGS_1.2.md`, `ofml_glossary_1.1_en.md`, `AN-2006-01_Control_Data_Tables-EN.md`, `AN-2014-04_OCD_Features-EN.md`, `AN-2017-01_PriceLists_DataCreation-EN.md`, `AN-2019-01_OCD_SAP_Support-EN.md`, `AN-2023-01_OFML_Support_in_pCon_Applications.md`, `MT-StyleGuide_1.2_en.md`, `OAP-Styleguide_en.md`, `OCD_ArticleDescription_1.2_en.md`, `OCD_TaxCategories_1.0_en.md`, `oex_export_plugin_1.6.0_en.md`, `spreadsheet_export_1.6.0_en.md`, `fact_sheet_ocd_article_texts_en.md`) | multiple | REFERENCE_ONLY | itself (do not paraphrase into other docs; cite instead) | External vendor specification, auto-converted for AI consumption — must stay verbatim/unmodified as ground truth citation source | Every spec's normative text; nothing to extract, only to cite |
| `docs/metatype_investigation/00`–`07` (8 files) | P, H (Metatype/`go_*` forensic) | KEEP | itself | Explicitly scoped as separate from and non-duplicative of pcon_investigation (covers `go_*`/Metatype, not OCD/XOCD/MDB/EBASE); still pre-implementation | `go_articles`/`go_properties`/`go_childprops` relationship evidence, polymorphic-Metatype workflow reconstruction |
| `docs/pcon_investigation/00_investigation_index.md` | O | KEEP | itself | Settles terminology ("MDF" is not real), gives reading order for the whole arc | Terminology ruling |
| `docs/pcon_investigation/01`–`08` (8 files) | O, E, F, G, J/K | KEEP | itself | Each builds on the previous with distinct scope (pCon.creator manual → MDB structure → PDM mapping → base/variant model → cardinality → dependency/exclusion → relation/relobj → Nevi trace); no internal duplication found | Real Nevi/DWE4 end-to-end trace, relation/relobj MDB schema, cardinality rules |
| `docs/pcon_investigation/09_mdf_export_import_requirements.md` | I | SUPERSEDED (partially) | `docs/pcon_investigation/pcon_planner/24_article_encoding_findings.md` | Older, summary-level pass on encoding/export requirements; file 24 supersedes its CodeScheme-specific claims with real HMX CSV evidence. Non-encoding content (general export/import requirements) still stands | Export/import requirement list not related to CodeScheme grammar |
| `docs/pcon_investigation/10_canonical_model.md` | O | KEEP | itself | Synthesis of files 01–09 into a proposed canonical engineering model | Canonical model proposal |
| `docs/pcon_investigation/11_automation_strategy.md` | H | KEEP | itself | A/B/C/D automation-confidence classification, distinct analytical purpose | Confidence-bucket classification per mapping |
| `docs/pcon_investigation/12_round_trip_validation.md` | N | KEEP | itself | Round-trip validation strategy, no overlap elsewhere | PDM→Workbench→MDB/OCD→pCon→export round-trip design |
| `docs/pcon_investigation/13_unknowns_and_decisions.md` | T | KEEP | itself — **must be updated** | Consolidated UNKNOWN/GAP register for files 01–12; does not yet include file 24's §17 gap list | Needs the pcon_planner findings merged in (see §9) |
| `docs/pcon_investigation/14_complete_investigation.md` | O | KEEP | itself | Executive summary of the 00–14 arc's original 14 questions | Closing synthesis |
| `docs/pcon_investigation/pcon_planner/19_mk_workbench_mapping.md` | H, I, J, K, L | KEEP — **highest priority, commit immediately** | itself | Untracked; freshest, most actionable, ranked gap/fix-priority table against real code (`services/article_obx/article_permutation_service.py`) | 9-item gap table with confidence ratings and ranked required-change list |
| `docs/pcon_investigation/pcon_planner/24_article_encoding_findings.md` | I, H, M | KEEP — **highest priority, commit immediately** | itself | Untracked; deepest real-HMX-CSV evidence (Aeron, Cosm, Atlas, Civic_tables, Lino, Hush, Fold); corrects a sibling doc's mislabeling of `SchemeID` as Knoll-specific | Full CodeScheme grammar findings, literal-separator evidence, Aeron 8-branch `Code` formula, §16 code diff, §17 open gaps |
| `requirements.txt`, `requirements-build.txt` | — | KEEP | itself | Trivial, current dependency manifests; not documentation subject to this audit | None |

**Note on completeness:** every file identified in the inventory (§1/§2) is covered above, either individually (unique/high-value docs) or as part of an explicitly-named group row (uniform, internally-consistent sets: Engineering_Handbook, Legacy_PDM_Business_Logic + Index, PDM_MDB_Engineering, pcon_reference architecture docs, pcon_reference vendor specs, database_relationships, tables, metatype_investigation, pcon_investigation 01–08). No file was silently dropped from consideration.

---

## 4. Duplication / Overlap Findings

1. **Reduction-engine trio** (`docs/reduction-investigation.md`, `docs/legacy-pdm-reduction-engine.md`, `docs/legacy-pdm-implementation-status.md`) — three documents produced across what appears to be sequential investigation sessions into the same question ("how does legacy PDM derive/reduce a base article, and what does our compat layer need to match"). Content is not contradictory, but it is fragmented: reduction-investigation.md is preliminary business-rule notes, legacy-pdm-reduction-engine.md is the fuller model, legacy-pdm-implementation-status.md is a narrow status tracker for one compatibility layer. **Recommendation: merge the first and third into the second**, which is the most complete and most recently framed as the authoritative model.

2. **`BuilderTableMapping.md` name collision** — `docs/pcon_reference/BuilderTableMapping.md` and `docs/pcon_reference/database_relationships/BuilderTableMapping.md` are two different documents (general Builder→OCD mapping vs. Builder→`tCOMd_*` specifically) sharing an identical filename in a nested path. Not duplicate content, but a naming risk. **Recommendation: rename one (e.g. `BuilderTableMapping_OCD.md` / `BuilderTableMapping_tCOMd.md`) in a later pass — not done here.**

3. **`09_mdf_export_import_requirements.md` vs. `pcon_planner/24_article_encoding_findings.md`** — file 09's CodeScheme/encoding claims are an earlier, shallower pass; file 24 is a later, evidence-backed correction (real HMX CSV data vs. inference). This is a **SUPERSEDED** relationship for the encoding-specific portions only — file 09's non-encoding export/import requirements are unaffected and remain valid.

4. **No exact duplicates found.** Every pair of documents that appears to cover the same subject (e.g. Engineering_Handbook's `07_OCD.md` vs. pcon_reference's vendor `ocd_4.3_en.md` vs. Legacy_PDM_Business_Logic's `21_OCD.md`) in fact serves a different purpose: industry-general reference vs. verbatim vendor spec vs. legacy-C#-specific rules. These are **complementary, not duplicative**, and should remain three separate documents.

---

## 5. Preserved Unique Evidence (explicitly flagged, must not be lost)

- Real HMX repository path: `C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx\` — confirmed reachable, containing real `ocd_article.csv`, `ocd_artbase.csv`, `ocd_codescheme.csv`, `ocd_property.csv`, `ocd_propertyvalue.csv`, `ocd_relation.csv`, `ocd_relationobj.csv`, `ocd_price.csv` for ranges Aeron, Cosm, Atlas, Civic_tables, Lino, Hush, Fold (`docs/pcon_investigation/pcon_planner/24_article_encoding_findings.md`).
- Finding that real CodeScheme encoding is **not** `base + concatenated property codes`; Cosm contains literal space segments; Aeron uses script-style/computed-property logic affecting ordering and grouping — all preserved verbatim in file 24, referenced (not duplicated) from file 19's gap table.
- `SKU_Config_Decode_Findings.md`'s `head.tail` decode logic and Nevi/DWE4 evidence, reused by `docs/pcon_investigation/08_nevi_end_to_end_trace.md`.
- `docs/pdm-family-boundary.md`'s live-DB finding that legacy PDM has **no single family algorithm** (three separate mechanisms).
- Every `BR-*` rule ID and source-code citation inside `Legacy_PDM_Business_Logic/` — none of this is duplicated elsewhere and must remain intact.
- `docs/metatype_investigation/03_metatype_data_relationships.md`'s confirmed `go_articles`↔`go_properties`↔`go_childprops` relationship with literal-value evidence — independent of, and not covered by, the OCD-side pcon_investigation.

---

## 6. Proposed Documentation Structure

This mirrors the five-tier structure the documents already form organically; it is a proposal for a **future** pass, not applied now.

```
docs/
├── README.md                          (rewritten index, replaces stale root README's doc-tree role)
├── architecture/                      (current: repo-root README + PDM_MDB_Engineering + pcon_reference architecture docs)
├── engineering_handbook/              (unchanged — already self-consolidated)
├── legacy_pdm_business_logic/         (unchanged — already self-consolidated, incl. Index/)
├── repository_model/                  (pcon_reference/database_relationships/ + tables/, BuilderTableMapping*)
├── article_encoding/                  (pcon_investigation/pcon_planner/24 as primary + 19 as summary, 09 marked superseded-in-part)
├── pdm_investigation/                 (pdm-family-boundary, reduction-engine trio merged to one file, SKU_Config_Decode_Findings)
├── pcon_investigation/                (00–14 unchanged, pcon_planner/ promoted to top-level or merged)
├── metatype_investigation/            (unchanged)
├── vendor_specs/                      (all *_en.md auto-converted PDFs — read-only reference corpus)
└── archive/                           (superseded portions only, e.g. old encoding claims from 09, kept for history)
```

**Not applied in this pass** — this is a proposal for review.

---

## 7. Sources of Truth (one per subject)

| Subject | Authoritative document |
|---|---|
| Overall architecture (current codebase) | `docs/PDM_MDB_Engineering/07_Builder_Workspace.md` + `docs/pcon_reference/Architecture.md` |
| Legacy PDM business logic (C# system) | `docs/Legacy_PDM_Business_Logic/` (whole handbook + Index) |
| PDM reduction / base-article derivation | `docs/legacy-pdm-reduction-engine.md` (after merging the other two) |
| Repository / MDB model | `docs/pcon_reference/database_relationships/` (+ `tables/`) |
| Snapshot | **none exists — gap, see §9** |
| Product / Article / Class model | `docs/pcon_investigation/04_base_article_variant_configuration.md` |
| Property / PropertyValue model | `docs/pcon_investigation/05_property_option_cardinality.md` |
| Relation / Dependency / Exclusion model | `docs/pcon_investigation/06_dependency_and_exclusion_model.md` + `07_relation_object_configuration_model.md` |
| Permutation generation | `docs/pcon_investigation/pcon_planner/19_mk_workbench_mapping.md` |
| Article Encoding / CodeScheme | `docs/pcon_investigation/pcon_planner/24_article_encoding_findings.md` |
| Variant Code / Final Article Number | `docs/pcon_investigation/08_nevi_end_to_end_trace.md` |
| Pricing | `docs/Legacy_PDM_Business_Logic/18_Pricing.md` (legacy) / `docs/pcon_reference/PriceGeneration.md` (current) |
| OBX generation | `docs/pcon_investigation/pcon_planner/24_article_encoding_findings.md` §16 (current gap) + `docs/pcon_reference/PackagingPipeline.md` (pipeline design) |
| QA / validation | `docs/pcon_investigation/12_round_trip_validation.md` |
| pCon.planner investigation | `docs/pcon_investigation/00_investigation_index.md` (entry point) → `14_complete_investigation.md` (summary) |
| HMX repository (Metatype/`go_*`) | `docs/metatype_investigation/` |
| Open questions / unresolved items | `docs/pcon_investigation/13_unknowns_and_decisions.md` **(needs update — see §9)** |

---

## 8. Contradictions

- **None found between authoritative documents.** The one apparent conflict — a sibling document (per file 24's own account, not present in this repo) mislabeling `SchemeID` as Knoll-specific — is already resolved *within* `docs/pcon_investigation/pcon_planner/24_article_encoding_findings.md`, which supersedes that claim with real cross-manufacturer OCD-spec evidence. No in-repo document currently makes the Knoll-specific claim.
- **Soft contradiction to flag:** `docs/pcon_investigation/09_mdf_export_import_requirements.md`'s CodeScheme/encoding assumptions predate and are less precise than file 24's findings. Not a hard contradiction (file 09 never claims `base + concatenated codes` as fact, only as a working assumption), but readers should be pointed to file 24 as the corrected version.

---

## 9. Missing Documentation

- **Snapshot**: no dedicated authoritative document exists anywhere in the tree, despite Snapshot being named in the task brief as an established canonical repository model. Referenced only in passing. **This is the most significant documentation gap found.**
- **UI / workflow architecture**: no dedicated document describing `ui/` or `workflow/` design exists; only `PDM_MDB_Engineering/07_Builder_Workspace.md` touches this tangentially.
- **`docs/pcon_investigation/13_unknowns_and_decisions.md`** has not yet absorbed the newer gap list from `pcon_planner/24_article_encoding_findings.md` §17 — the two open-questions registers are currently out of sync.
- **MK_OFML_Testsuite comparison**: no documentation exists because no such directory exists in this repository; if Testsuite comparison work happens elsewhere, it is not represented here at all.

---

## 10. Immediate Risk — Uncommitted Files

`docs/pcon_investigation/pcon_planner/` (containing `19_mk_workbench_mapping.md` and `24_article_encoding_findings.md`) is **untracked** per `git status`. These are the two most valuable, most current, most actionable documents in the entire audit — they contain a ranked, evidence-backed list of required engineering changes. They should be committed promptly so they are not lost; this plan does not commit them, per the "do not modify" constraint of this pass, but flags it as the top follow-up action.

---

## 11. Validation Checklist

- [x] Every documentation file in the repository was enumerated and classified or grouped (173 files; 169 under `docs/`, 4 elsewhere).
- [x] No major topic from the task's required category list (A–T) was left unaddressed — gaps are explicitly named in §9 rather than silently skipped.
- [x] No unique evidence identified in §5 is scheduled for deletion; all classifications preserving evidence are MERGE, KEEP, or REFERENCE_ONLY, not DUPLICATE.
- [x] No source code, `MK_OFML_Testsuite`, or configuration files were changed. Only `docs/DOCUMENTATION_CONSOLIDATION_PLAN.md` was created.
- [x] Historical/superseded material (§4 item 3) has an archive/reference strategy (§6 `archive/` folder, proposed not applied).
- [x] A source of truth is named for every major subject except Snapshot, which is explicitly logged as a gap rather than assigned a false authority.
- [x] pCon/CodeScheme findings are treated as one authoritative document (file 24) with file 19 as its derived summary — not duplicated into a third document.
- [x] Existing PDM/Snapshot investigations are not re-investigated by this plan; this pass is documentation-organization only.

---

## 12. Summary Counts

| Classification | Count |
|---|---|
| KEEP | ~150 (Engineering_Handbook ×21, Legacy_PDM_Business_Logic + Index ×41, PDM_MDB_Engineering ×8, pcon_reference architecture ×11, database_relationships + tables ×22, metatype_investigation ×8, pcon_investigation 00–08/10–14 ×13, pcon_planner ×2, pdm-family-boundary, SKU_Config_Decode_Findings, requirements×2, repo_sync_agent README) |
| MERGE | 3 (`reduction-investigation.md`, `legacy-pdm-implementation-status.md` → into `legacy-pdm-reduction-engine.md`; root `README.md` → rewrite) |
| ARCHIVE | 0 (proposed `archive/` folder is empty until the SUPERSEDED item below is formally split out) |
| DUPLICATE | 0 |
| SUPERSEDED | 1 (partial — `09_mdf_export_import_requirements.md`'s encoding-specific claims only; rest of the file stands) |
| REFERENCE_ONLY | ~28 (all vendor `*_en.md` specs + app notes, `DPS_Original_Extraction_SQL.md`) |
| TEMPORARY | 2 (`project_structure.txt`, `.pytest_cache/README.md`) |

Totals do not sum to a single clean 173 because several group rows in §3 represent multiple files under one classification; see §3 for the per-file/per-group breakdown.
