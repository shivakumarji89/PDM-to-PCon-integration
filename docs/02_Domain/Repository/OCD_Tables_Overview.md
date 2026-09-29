# OCD Tables (`tCOMd_*`) — At a Glance

**Cross-refs:** [Repository_Model.md](./Repository_Model.md) (complete, evidence-graded table/FK inventory — authoritative) · [Tables/](./Tables/) (one reference file per table) · [ComGroup_Model.md](./ComGroup_Model.md)

> **2026-09-27 correction:** this document previously cited `services/pdm_to_mdb_service.py` and a `mdb_helper`-based write mechanism, neither of which exists in the current codebase, and its table list omitted `tCOMd_RelObj`/`tCOMd_Relation`/`tCOMd_RelObjRel`/`tCOMd_CodeScheme`/`tCOMd_Package2Mat`/`tCOMd_Article2Mat`/`tCOMd_Table`/`tCOMd_TableColumn`/`tCOMd_TableLine`/`tCOMd_GlobalPrice` — all of which the current exporter does write. The table below is corrected against `services/ocd_export_service.py`, `services/xocd_export_service.py`, and `services/mdb_reverse_engineering_service.py` (2026-09-27). **This page is a quick-reference summary, not the source of truth** — [Repository_Model.md](./Repository_Model.md) is, and carries the full evidence-graded FK list and per-row citations; this page intentionally does not repeat that detail.

The OCD commercial database (`pcr_data_com_ocd.mdb`) holds all `tCOMd_*` tables. Field names use the `com_` prefix.

| Table | Purpose | Primary key | Layer |
|---|---|---|---|
| `tCOMd_ComGroup` | Top-level commercial group (brand/program container); template-owned, only relabeled | `com_ComGroupID` | Packaging |
| `tCOMd_Package` | Program/series package under a ComGroup; template-owned, only relabeled | `com_PackageID` | Packaging |
| `tCOMd_Class` | Property classes, scoped to a package | `com_ClassID` | Engineering source |
| `tCOMd_Article` | Articles (article codes) | `com_ArticleID` | Packaging (id) / Engineering (code) |
| `tCOMd_ArticleClass` | Article ↔ Class join | (`com_ArticleID`,`com_ClassID`) | Packaging |
| `tCOMd_ArtBase` | Per-article allowed-value restrictions; **string-keyed** (`com_ClassName`/`com_PropName`/`com_PropValue`), not surrogate-key FKs — a documented divergence from every other table here | `com_ArtBaseID` | Packaging |
| `tCOMd_Property` | Properties (attributes and options are both folded in here — there is no separate `tCOMd_Option` write path) | `com_PropertyID` | Engineering source |
| `tCOMd_PropValue` | Property values | `com_PropValueID` | Engineering source |
| `tCOMd_Text` | Localized text (labels/descriptions); shared lookup referenced by most other tables | `com_TextID` | Packaging (display) |
| `tCOMd_CodeScheme` | Variant-code/final-article-number grammar per article | `com_CodeSchemeID` | Engineering source |
| `tCOMd_RelObj` / `tCOMd_Relation` / `tCOMd_RelObjRel` | Relation objects/bodies and their join; only the `PropValue→RelObj` binding is ever populated by the current generator | `com_RelObjID` / `com_RelationID` / `com_RelObjRelID` | Engineering source |
| `tCOMd_Package2Mat` / `tCOMd_Article2Mat` | Package/article material-selection links | `com_Package2MatID` / `com_Article2MatID` | Packaging |
| `tCOMd_Table` / `tCOMd_TableColumn` / `tCOMd_TableLine` | Value-combination tables; name-joined to package, not surrogate-key-joined to Property/PropValue | `com_TableID` / `com_TableColumnID` / `com_TableLineID` | Engineering source |
| `tCOMd_Price` / `tCOMd_GlobalPrice` | Article / package-level prices | `com_PriceID` / `com_GlobalPriceID` | Item-level (Price stage) |
| `tCOMd_PriceList2` | Price lists; read from the template, never generated | `com_PriceListID` | Item-level (Price stage) |

**Not written by either current exporter:** `tCOMd_Option` / `tCOMd_OptionValue` — options are folded into `tCOMd_Property`/`tCOMd_PropValue`. See [Repository_Model.md §1](./Repository_Model.md) for the full write/read coverage matrix (which tables each of `OcdExportService`, `XocdExportService`, and `MdbReverseEngineeringService` actually touch) and [§2](./Repository_Model.md) for the complete FK list with source citations.
