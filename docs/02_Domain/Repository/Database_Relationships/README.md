# OCD MDB (`tCOMd_*`) Database Relationships — Knowledge Base

**Status: HISTORICAL / STALE.** This subtree describes a write/read pipeline built on `helpers/mdb_helper.py`, `services/workspace_snapshot_builder.py`, and `services/pdm_to_mdb_service.py`. **None of those files exist in the current codebase** (verified [Repository_Model.md](../Repository_Model.md) §0, re-confirmed 2026-09-27). The current, live write path is `services/ocd_export_service.py` + `services/xocd_export_service.py`; the current read path is `services/mdb_reverse_engineering_service.py`. **Treat the FK/table content below only as directional evidence for column names and cardinality, cross-checked against [Repository_Model.md](../Repository_Model.md) — do not use it as ground truth on its own.** It is kept rather than deleted because it still has value as historical evidence of the schema shape, and because several of its FK/cardinality facts have been independently re-confirmed against current code in `Repository_Model.md`.

**Parent KB:** [../README.md](../README.md) · [Repository_Model.md](../Repository_Model.md) (current, authoritative structural model)

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
