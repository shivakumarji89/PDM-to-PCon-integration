# Service Mapping

**Cross-refs:** [BuilderTableMapping](./BuilderTableMapping.md) · [../Architecture.md](../Architecture.md) · [WriteOrder](./WriteOrder.md)

Per Python service: tables read, tables written, Builder Table models consumed, and pipeline stage.

| Service | Reads | Writes | Builder Table models consumed | Stage |
|---|---|---|---|---|
| `PDMService` | PDM SQL (`Product`, `Option*`, `Attribute*`, dependency/exclusion, `LayoutFeatures`, `ItemComponents`, price tables) | — | — (produces them) | Engineering (source) |
| `PDMSnapshotService` | via `PDMService` | — | builds all snapshot keys | Engineering |
| `PDMFilterBuilderService` | — | — | `product_attributes` | Payload prep |
| `PDMArticleCodeService` | — | — | attribute/option codes | Payload prep |
| `PDMToMDBService` | — | (skeleton payload) | category name | Packaging (skeleton) |
| `GeneratePayloadService` | — | — | snapshot rows → payload | Packaging (payload) |
| `OCDPayloadService` | — | — | payload | Packaging (scope/preview) |
| `OCDPayloadValidationService` | — | — | payload | Validation (pre-write) |
| `MDBService` | `tCOMd_Article/Text/Property/PropValue/Class/ArticleClass/ArtBase` (read); price via `MDBQuery` | delegates writes to helper | payload | Write / Read |
| `helpers/mdb_helper.py` | `tCOMd_*` (lookups) | **`tCOMd_ComGroup/DistributionRegion/OfmlType/Package/Text/Class/Property/PropValue/Article/ArticleClass/ArtBase`** | payload | Write (32-bit) |
| `WorkspaceSnapshotBuilder` | `tCOMd_*` (read-back) | — | — | Read-back / validation |
| `WorkspaceSnapshot` | in-memory | — | — | Read-back model |
| `article_service` | `tCOMd_Article/Text` (via summary) | — | — | Read (UI) |

## Read vs Write Responsibility

- **Only `helpers/mdb_helper.py` writes** `tCOMd_*` rows (through `MDBService.create_handbook_base`).
- **`MDBService` and `WorkspaceSnapshotBuilder` read** `tCOMd_*` for summaries and conflict detection.
- **`PDMService` never touches OCD tables** — it is the engineering source (PDM SQL) only.

## Stage Membership

- **Engineering:** `PDMService`, `PDMSnapshotService`, `PDMFilterBuilderService`, `PDMArticleCodeService`.
- **Packaging/Payload:** `GeneratePayloadService`, `OCDPayloadService`, `PDMToMDBService`.
- **Validation:** `OCDPayloadValidationService` (pre), `WorkspaceSnapshotBuilder` (post).
- **Write:** `MDBService` → `mdb_helper`.
