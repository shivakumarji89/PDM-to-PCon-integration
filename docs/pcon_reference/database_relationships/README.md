# OCD MDB (`tCOMd_*`) Database Relationships — Knowledge Base

**Status:** Reverse-engineered reference. Documentation only — no OCD data is generated here.
**Purpose:** Enable a future **MDB Writer** to create a brand-new OCD database without re-inspecting
the PDM/DPS source. Grounded in `helpers/mdb_helper.py` (write), `services/mdb_service.py` (read),
`services/workspace_snapshot_builder.py` (read-back), and `services/pdm_to_mdb_service.py` (payload).

**Parent KB:** [../README.md](../README.md) · [../OCDTables.md](../OCDTables.md) · [../PackagingPipeline.md](../PackagingPipeline.md)

## Contents

| Document | Covers |
|---|---|
| [ERDiagram.md](./ERDiagram.md) | Full ER diagram: PKs, FKs, cardinality, optional/required |
| [DependencyGraph.md](./DependencyGraph.md) | Insertion-order dependency graph + rationale |
| [RelationshipMatrix.md](./RelationshipMatrix.md) | Parent/child/field/type/stage/consumer matrix |
| [WriteOrder.md](./WriteOrder.md) | Safe write sequence for a new OCD DB, ID generation, rollback |
| [ReadOrder.md](./ReadOrder.md) | Optimal import/read sequence + relationship rebuild |
| [BuilderTableMapping.md](./BuilderTableMapping.md) | Builder Table model → tCOMd, transformation, validation |
| [ServiceMapping.md](./ServiceMapping.md) | Per-service reads/writes/models/stage |
| [ValidationRules.md](./ValidationRules.md) | Required/optional records, integrity checks |
| [tables/](./tables/) | One file per important `tCOMd_*` table |

## Tables Covered

Structural: `tCOMd_ComGroup`, `tCOMd_DistributionRegion`, `tCOMd_OfmlType`, `tCOMd_Package`,
`tCOMd_Text`, `tCOMd_Article`, `tCOMd_Class`, `tCOMd_ArticleClass`, `tCOMd_ArtBase`,
`tCOMd_Property`, `tCOMd_PropValue`.
Pricing (item-level, generation stage): `tCOMd_Price`, `tCOMd_PriceList2`.

## Ground-Truth Anchors

- Write: `helpers/mdb_helper.py` — `create_handbook_base`, `get_or_create_com_group`,
  `ensure_distribution_region_exists`, `resolve_ofml_type_id`, `get_or_create_package`,
  `get_or_create_text`, `get_or_create_article`, `get_or_create_class`, `get_or_create_property`,
  `get_or_create_prop_value`, `get_or_create_article_class`, `get_or_create_art_base`.
- Read: `services/mdb_service.py::get_article_property_summary`, `get_rows`, `get_class_names`,
  `get_property_definitions`.
- Read-back: `services/workspace_snapshot_builder.py`.
- Payload: `services/pdm_to_mdb_service.py`, `services/generate_payload_service.py`.
