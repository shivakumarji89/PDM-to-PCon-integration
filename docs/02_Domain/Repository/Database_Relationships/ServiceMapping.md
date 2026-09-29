# Service Mapping

**Cross-refs:** [BuilderTableMapping](./BuilderTableMapping.md) · [../Architecture.md](../Architecture.md) · [WriteOrder](./WriteOrder.md) · [ReadOrder](./ReadOrder.md)

Per Python service: tables read, tables written, Builder Table models consumed, and pipeline stage.
This is a service-ownership view (which Python service touches which table) — for the actual table
read *sequence*, see [ReadOrder.md](./ReadOrder.md); for the write sequence, see
[WriteOrder.md](./WriteOrder.md).

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
| `MDBService` | `tCOMd_*` structural tables (the 7-table `get_article_property_summary` set — see [ReadOrder.md](./ReadOrder.md) for the full list/order); price via `MDBQuery` | delegates writes to helper | payload | Write / Read |
| `helpers/mdb_helper.py` | `tCOMd_*` (lookups) | **`tCOMd_ComGroup/DistributionRegion/OfmlType/Package/Text/Class/Property/PropValue/Article/ArticleClass/ArtBase`** | payload | Write (32-bit) |
| `WorkspaceSnapshotBuilder` | `tCOMd_*` (read-back, same set as [ReadOrder.md](./ReadOrder.md)) | — | — | Read-back / validation |
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
