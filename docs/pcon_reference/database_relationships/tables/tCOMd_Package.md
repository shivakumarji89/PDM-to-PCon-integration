# tCOMd_Package

**Cross-refs:** [tCOMd_ComGroup.md](./tCOMd_ComGroup.md) · [tCOMd_Article.md](./tCOMd_Article.md) · [../../ComGroup.md](../../ComGroup.md)

- **Purpose:** Program/series package under a ComGroup; owns articles.
- **Primary Key:** `com_PackageID` (autonumber).
- **Foreign Keys:** `com_ComGroupID` (→ ComGroup), `com_DistributionRegionID` (→ DistributionRegion).
- **Referenced By:** `tCOMd_Article` (`com_PackageID`).
- **Depends On:** `tCOMd_ComGroup`, `tCOMd_DistributionRegion`.
- **Important Columns:** `com_PackageID`, `com_PackageCode`/`ProgramCode` (natural key, lower),
  `com_PackageLabel`/`ProgramLabel`, `com_ComGroupID`, `com_DistributionRegionID`, `MaterialMF="hmx"`,
  `MaterialPK="basics"`.
- **Builder Table source:** derived from category name (`PDMToMDBService.build_package`).
- **Generation stage:** Package Builder (skeleton).
- **Consumer services:** `helpers/mdb_helper.py::get_or_create_package`; read by `MDBService`.
- **Business rules:** resolved by package code (get-or-create); `create_handbook_base` locks
  `PackageID` to prevent stale IDs; region 5 ensured.
- **Example record:** `{ com_PackageID: 88, ProgramCode: "seating", ComGroupID: 12, DistributionRegionID: 5 }`.
- **Typical row count:** small (one per program/series).
- **Generation order:** 4.
