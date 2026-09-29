# Documentation Cleanup Report

This restructuring executed the plan from the prior audit (now archived at [`99_Archive/Historical/DOCUMENTATION_CONSOLIDATION_PLAN.md`](./99_Archive/Historical/DOCUMENTATION_CONSOLIDATION_PLAN.md)). It reorganizes `docs/` around **what the system is and does**, not around investigation history. No application source code was touched — only files under `docs/` and `README.md` (root).

## Before

Total documentation files under `docs/`: **169** (across the old `docs/Engineering_Handbook/`, `docs/Legacy_PDM_Business_Logic/`, `docs/PDM_MDB_Engineering/`, `docs/pcon_reference/`, `docs/metatype_investigation/`, `docs/pcon_investigation/` + `pcon_investigation/pcon_planner/`, and several loose top-level files).

## After

Total documentation files under `docs/`: **186** (net +17: 14 new folder-level `README.md` navigation files, 3 new canonical synthesis documents — `Snapshot.md`, `Reduction_and_Family_Rules.md`, `Metatype.md` — offsetting 1 file removed outright).

## Deleted

| File | Reason |
|---|---|
| `docs/legacy-pdm-reduction-engine.md` | Superseded by the merged canonical [`02_Domain/PDM/Reduction_and_Family_Rules.md`](./02_Domain/PDM/Reduction_and_Family_Rules.md); its content was folded into that document, not lost |

No other documentation file was deleted outright. `project_structure.txt` (repo root, a mechanical/garbled `tree` dump) was considered for deletion but is already excluded from version control via `.gitignore` ("Local project inspection file") — it was left untouched since it is not part of the tracked documentation set.

## Merged

| Old documents | New canonical document | Information preserved |
|---|---|---|
| `docs/reduction-investigation.md`, `docs/legacy-pdm-implementation-status.md`, `docs/legacy-pdm-reduction-engine.md` | [`02_Domain/PDM/Reduction_and_Family_Rules.md`](./02_Domain/PDM/Reduction_and_Family_Rules.md) | Full proven legacy model, exact UI-to-filter contract (`ProductsList`/`USProductsList`, `TemplateContainer.AttributeXml`), all 5 recovered rules, the 4-phase generic reduction algorithm, the read-only compatibility-layer implementation status, the required acceptance run, and the 591-row-dataset caveat |
| 8 files in `docs/metatype_investigation/` (00–07) | [`02_Domain/Engineering/Metatype.md`](./02_Domain/Engineering/Metatype.md) | Real HMX repository structure (14GB, 102 dirs, `basics.7z`), full `go_*.csv` format inventory, confirmed `go_articles`/`go_properties`/`go_childprops` relationships with literal CSV examples, the manual↔repository↔code concept mapping, the reconstructed polymorphic-Metatype workflow, the proposed (unimplemented) Python workflow design with exact code citations, the validation plan, and a consolidated open-questions list |

The two merged-source groups above were **archived, not deleted** — see below — so their original evidence trail remains inspectable.

## Moved

Every file not listed above as deleted/merged was relocated (via `git mv` where tracked) into the new structure. Representative highlights (full mapping is mechanical — old numbered investigation files became descriptively-named domain or reference documents):

| Old path | New path |
|---|---|
| `docs/Engineering_Handbook/` (21 files) | `docs/04_Reference/Engineering_Reference/` (unchanged internally — numbering here is an intentional reading order, not investigation history) |
| `docs/Legacy_PDM_Business_Logic/` (41 files incl. `Index/`) | `docs/02_Domain/PDM/Legacy_PDM_Business_Logic/` (unchanged internally) |
| `docs/PDM_MDB_Engineering/01_MDB_Engineering_Workflow.md` … `08_Migration_Roadmap.md` | `docs/02_Domain/PDM/PDM_MDB_Bridge/*.md` (numeric prefixes dropped) |
| `docs/PDM_MDB_Engineering/07_Builder_Workspace.md` | `docs/01_Architecture/Workflow_Architecture.md` |
| `docs/pcon_reference/Architecture.md` | `docs/01_Architecture/System_Architecture.md` |
| `docs/pcon_reference/GeneratorArchitecture.md` | `docs/01_Architecture/Module_Architecture.md` |
| `docs/pcon_reference/OCDTables.md` | `docs/02_Domain/Repository/OCD_Tables_Overview.md` |
| `docs/pcon_reference/BuilderTableMapping.md` | `docs/02_Domain/Repository/Builder_To_OCD_Mapping.md` |
| `docs/pcon_reference/database_relationships/BuilderTableMapping.md` | `docs/02_Domain/Repository/Database_Relationships/Builder_To_tCOMd_Mapping.md` (**renamed to resolve the filename collision** flagged in the prior audit) |
| `docs/pcon_reference/ComGroup.md` | `docs/02_Domain/Repository/ComGroup_Model.md` |
| `docs/pcon_reference/Relationships.md` | `docs/02_Domain/OBX/Contains_Relationship_Graph.md` (corrected domain — this covers the generated `contains` relationship graph, not table FKs) |
| `docs/pcon_reference/PriceGeneration.md` | `docs/02_Domain/Pricing/Pricing_Model.md` |
| `docs/pcon_reference/VariantConditions.md` | `docs/02_Domain/Pricing/Variant_Condition.md` |
| `docs/pcon_reference/PackagingPipeline.md` | `docs/02_Domain/OBX/OBX_Generation.md` |
| `docs/pcon_reference/Summary.md` | `docs/02_Domain/OBX/Generator_Roadmap.md` |
| `docs/pcon_reference/database_relationships/` (9 files) | `docs/02_Domain/Repository/Database_Relationships/` |
| `docs/pcon_reference/database_relationships/tables/` (14 files) | `docs/02_Domain/Repository/Tables/` |
| `docs/pcon_reference/*_en.md`, `GO_1.12.0.md`, `AN-*.md`, `AppNote_*.md`, etc. (27 vendor spec files) | `docs/04_Reference/pCon/Specifications/` (unchanged filenames — external spec versions, not investigation numbers) |
| `docs/pcon_reference/README.md` | `docs/04_Reference/pCon/README.md` (rewritten to reflect the new split between `Specifications/` and `Investigation/`) |
| `docs/DPS_Original_Extraction_SQL.md` | `docs/04_Reference/Legacy/DPS_SQL_Extraction.md` |
| `docs/SKU_Config_Decode_Findings.md` | `docs/02_Domain/PDM/SKU_Configuration_Decode.md` |
| `docs/pdm-family-boundary.md` | `docs/02_Domain/PDM/Family_Boundary_Findings.md` |
| `docs/pcon_investigation/02_mdb_structure_and_relationships.md` | `docs/02_Domain/Repository/Repository_Model.md` |
| `docs/pcon_investigation/04_base_article_variant_configuration.md` | `docs/02_Domain/Product/Article_Configuration_Model.md` |
| `docs/pcon_investigation/05_property_option_cardinality.md` | `docs/02_Domain/Engineering/Property_Model.md` |
| `docs/pcon_investigation/06_dependency_and_exclusion_model.md` | `docs/02_Domain/Engineering/Dependency_Model.md` |
| `docs/pcon_investigation/07_relation_object_configuration_model.md` | `docs/02_Domain/Engineering/Relation_Model.md` |
| `docs/pcon_investigation/08_nevi_end_to_end_trace.md` | `docs/02_Domain/Article_Encoding/Variant_Code_and_Final_Article_Number.md` |
| `docs/pcon_investigation/11_automation_strategy.md` | `docs/02_Domain/Permutation/Permutation_Model.md` |
| `docs/pcon_investigation/12_round_trip_validation.md` | `docs/03_Workflows/QA_Validation.md` |
| `docs/pcon_investigation/pcon_planner/24_article_encoding_findings.md` (untracked) | `docs/02_Domain/Article_Encoding/Article_Encoding.md` (**now committed**) |
| `docs/pcon_investigation/pcon_planner/19_mk_workbench_mapping.md` (untracked) | `docs/02_Domain/Permutation/Permutation_Gap_Analysis.md` (**now committed**) |
| `docs/pcon_investigation/00_investigation_index.md`, `01_pcon_creator_2_22_2_investigation.md`, `03_pdm_to_pcon_mapping.md`, `10_canonical_model.md`, `13_unknowns_and_decisions.md`, `14_complete_investigation.md` | `docs/04_Reference/pCon/Investigation/README.md`, `PCon_Creator_Investigation.md`, `PDM_to_pCon_Mapping.md`, `Canonical_Model_Proposal.md`, `Open_Questions_and_Decisions.md`, `Investigation_Summary.md` |

## Archived

| Document | Reason |
|---|---|
| `docs/99_Archive/Superseded/Reduction_Investigation_Notes.md` (was `docs/reduction-investigation.md`) | Merged into `Reduction_and_Family_Rules.md`; kept as original evidence trail |
| `docs/99_Archive/Superseded/Legacy_PDM_Implementation_Status.md` (was `docs/legacy-pdm-implementation-status.md`) | Merged into `Reduction_and_Family_Rules.md`; kept as original evidence trail |
| `docs/99_Archive/Superseded/MDF_Export_Import_Requirements.md` (was `docs/pcon_investigation/09_mdf_export_import_requirements.md`) | Its CodeScheme/encoding claims are superseded by the real-HMX-evidence findings in `Article_Encoding.md`; its general export/import contract analysis (non-encoding) remains a valid reference, so the whole file is archived (not deleted) with a note distinguishing the two |
| `docs/99_Archive/Historical/Metatype_Investigation/00`–`07` (was `docs/metatype_investigation/`) | Consolidated into `02_Domain/Engineering/Metatype.md`; kept in full as the original forensic evidence trail (real CSV examples, code citations) |
| `docs/99_Archive/Historical/DOCUMENTATION_CONSOLIDATION_PLAN.md` | The pre-restructuring audit; describes the old (now superseded) documentation tree — kept as the historical record of the audit reasoning |

Every archived file above carries a `STATUS: ARCHIVED` / `SUPERSEDED BY: <canonical doc>` header.

## Sources of Truth

| Subject | Canonical document |
|---|---|
| Architecture | [`01_Architecture/System_Architecture.md`](./01_Architecture/System_Architecture.md) |
| PDM (legacy business logic) | [`02_Domain/PDM/Legacy_PDM_Business_Logic/`](./02_Domain/PDM/Legacy_PDM_Business_Logic/) |
| PDM (base-article reduction) | [`02_Domain/PDM/Reduction_and_Family_Rules.md`](./02_Domain/PDM/Reduction_and_Family_Rules.md) |
| Repository | [`02_Domain/Repository/Repository_Model.md`](./02_Domain/Repository/Repository_Model.md) |
| Snapshot | [`02_Domain/Repository/Snapshot.md`](./02_Domain/Repository/Snapshot.md) |
| Engineering (Property/Relation/Dependency) | [`02_Domain/Engineering/Property_Model.md`](./02_Domain/Engineering/Property_Model.md), [`Relation_Model.md`](./02_Domain/Engineering/Relation_Model.md), [`Dependency_Model.md`](./02_Domain/Engineering/Dependency_Model.md) |
| Relations | [`02_Domain/Engineering/Relation_Model.md`](./02_Domain/Engineering/Relation_Model.md) |
| Permutations | [`02_Domain/Permutation/Permutation_Model.md`](./02_Domain/Permutation/Permutation_Model.md) + [`Permutation_Gap_Analysis.md`](./02_Domain/Permutation/Permutation_Gap_Analysis.md) |
| Article Encoding | [`02_Domain/Article_Encoding/Article_Encoding.md`](./02_Domain/Article_Encoding/Article_Encoding.md) |
| CodeScheme | [`02_Domain/Article_Encoding/Article_Encoding.md`](./02_Domain/Article_Encoding/Article_Encoding.md) (same document — deliberately not split; see that domain's README) |
| Variant Code | [`02_Domain/Article_Encoding/Variant_Code_and_Final_Article_Number.md`](./02_Domain/Article_Encoding/Variant_Code_and_Final_Article_Number.md) |
| Pricing | [`02_Domain/Pricing/Pricing_Model.md`](./02_Domain/Pricing/Pricing_Model.md) |
| OBX | [`02_Domain/OBX/OBX_Generation.md`](./02_Domain/OBX/OBX_Generation.md) |
| QA | [`03_Workflows/QA_Validation.md`](./03_Workflows/QA_Validation.md) |
| Metatype | [`02_Domain/Engineering/Metatype.md`](./02_Domain/Engineering/Metatype.md) |
| pCon investigation | [`04_Reference/pCon/Investigation/README.md`](./04_Reference/pCon/Investigation/README.md) (narrative index; the concepts it originally covered now have their own canonical domain docs, linked from there) |

## Final Documentation Tree

```
docs/
├── README.md
├── DOCUMENTATION_CLEANUP_REPORT.md
├── 01_Architecture/
│   ├── README.md
│   ├── System_Architecture.md
│   ├── Module_Architecture.md
│   └── Workflow_Architecture.md
├── 02_Domain/
│   ├── README.md
│   ├── PDM/
│   │   ├── README.md
│   │   ├── Legacy_PDM_Business_Logic/        (README + 00-28 + Index/ + Index/parts/, 41 files)
│   │   ├── PDM_MDB_Bridge/                   (7 files)
│   │   ├── Reduction_and_Family_Rules.md
│   │   ├── Family_Boundary_Findings.md
│   │   └── SKU_Configuration_Decode.md
│   ├── Repository/
│   │   ├── README.md
│   │   ├── Snapshot.md
│   │   ├── Repository_Model.md
│   │   ├── OCD_Tables_Overview.md
│   │   ├── Builder_To_OCD_Mapping.md
│   │   ├── ComGroup_Model.md
│   │   ├── Database_Relationships/            (9 files)
│   │   └── Tables/                             (README + 13 tCOMd_* files)
│   ├── Engineering/
│   │   ├── README.md
│   │   ├── Property_Model.md
│   │   ├── Relation_Model.md
│   │   ├── Dependency_Model.md
│   │   └── Metatype.md
│   ├── Product/
│   │   ├── README.md
│   │   └── Article_Configuration_Model.md
│   ├── Permutation/
│   │   ├── README.md
│   │   ├── Permutation_Model.md
│   │   └── Permutation_Gap_Analysis.md
│   ├── Article_Encoding/
│   │   ├── README.md
│   │   ├── Article_Encoding.md
│   │   └── Variant_Code_and_Final_Article_Number.md
│   ├── Pricing/
│   │   ├── README.md
│   │   ├── Pricing_Model.md
│   │   └── Variant_Condition.md
│   └── OBX/
│       ├── README.md
│       ├── OBX_Generation.md
│       ├── Contains_Relationship_Graph.md
│       └── Generator_Roadmap.md
├── 03_Workflows/
│   ├── README.md
│   └── QA_Validation.md
├── 04_Reference/
│   ├── README.md
│   ├── Engineering_Reference/                 (README + 00-19, unchanged, 21 files)
│   ├── pCon/
│   │   ├── README.md
│   │   ├── Specifications/                    (27 vendor spec files, unchanged)
│   │   └── Investigation/                     (README + 5 narrative docs)
│   └── Legacy/
│       └── DPS_SQL_Extraction.md
└── 99_Archive/
    ├── README.md
    ├── Superseded/                             (3 files)
    ├── Historical/
    │   ├── DOCUMENTATION_CONSOLIDATION_PLAN.md
    │   └── Metatype_Investigation/              (8 files)
    └── Temporary/                               (empty — reserved)
```

## Validation

- **Duplicate check:** no exact-duplicate documents exist. The one filename collision flagged by the prior audit (`BuilderTableMapping.md` appearing twice) was resolved by renaming both to `Builder_To_OCD_Mapping.md` and `Builder_To_tCOMd_Mapping.md`.
- **Broken-link check:** all internal `docs/`-prefixed cross-references and same-directory relative links found across the non-archived, non-vendor-spec documentation were repointed to their new locations (reduction trio, PDM_MDB bridge sibling links, Legacy_PDM_Business_Logic references, pcon_reference/pcon_investigation/metatype_investigation path citations, Engineering_Handbook references). Vendor specification files (`04_Reference/pCon/Specifications/`) and the archived/historical documents in `99_Archive/` were **not** rewritten beyond adding their required archive headers — those preserve the original text as historical evidence. **Known residual, out of scope:** four Python source files (`models/distribution_region.py`, `repositories/legacy_pdm_compat_repository.py`, `services/distribution_region_service.py`, `services/engineering/candidate_strategy_service.py`) contain code comments citing old documentation paths (e.g. `docs/pdm-family-boundary.md`, `docs/pcon_reference/dsr-3.7_en.md`). These were **not** updated because doing so would require editing application source code, which this task explicitly excludes.
- **Missing-document check:** no canonical domain concept is left undocumented. The one true gap identified by the prior audit — no dedicated Snapshot document — was closed by writing [`02_Domain/Repository/Snapshot.md`](./02_Domain/Repository/Snapshot.md) from real service/class citations already present in the source material (`WorkspaceSnapshot`, `WorkspaceSnapshotBuilder`, `MDBService`).
- **Important-evidence preservation:** confirmed present in their new locations — the real HMX repository paths and CSV evidence (Article Encoding, Metatype), the Nevi/DWE4 end-to-end trace, the live `PDMLive` family-boundary findings, the full `BR-*` legacy business-rule set, and the complete vendor specification corpus. Nothing was paraphrased away during any merge; merged documents combined full sections from their sources rather than summarizing them.
