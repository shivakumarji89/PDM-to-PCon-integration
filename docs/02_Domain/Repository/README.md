# Repository Domain

The repository (MDB/OCD) model — how the Access-based OCD package (`pcr_data_com_ocd.mdb`) is structured, read, and written.

| Document | Covers |
|---|---|
| [Snapshot.md](./Snapshot.md) | **Canonical.** `Snapshot` — the in-memory repository representation MK Workbench uses everywhere. Do not introduce a competing model. |
| [Repository_Model.md](./Repository_Model.md) | **Canonical, evidence-graded.** The verified MDB/OCD structural model (table inventory, FK relationships, write/read coverage) against the *current* exporter code. This is the authoritative source for table structure and FKs — other documents in this folder should link to it rather than maintain an independent copy. |
| [OCD_Tables_Overview.md](./OCD_Tables_Overview.md) | Every important `tCOMd_*` table at a glance (quick-reference summary; defers to `Repository_Model.md` for full detail) |
| [Tables/](./Tables/) | One reference file per real `tCOMd_*` table (fields, PK/FK, generation stage) |
| [Database_Relationships/](./Database_Relationships/) | ERD, dependency graph, read/write order, validation rules. **Historical/stale:** per `Repository_Model.md` §0, this subtree describes a prior architecture (`mdb_helper.py`/`workspace_snapshot_builder.py`/`workspace_service.py`) that no longer exists in the current codebase. Kept only as directional evidence for column names/cardinality — cross-check anything from here against `Repository_Model.md` before relying on it. |
| [Builder_To_OCD_Mapping.md](./Builder_To_OCD_Mapping.md) | Builder Table model → PDM tables → OCD tables mapping (general) |
| [ComGroup_Model.md](./ComGroup_Model.md) | ComGroup/Package constants and the current template-relabel flow |

**Source of truth for Snapshot:** `Snapshot.md`. **Source of truth for table structure and FKs:** `Repository_Model.md` (evidence-graded against current code); `Tables/` for per-table field reference. `Database_Relationships/` is historical — see note above.
