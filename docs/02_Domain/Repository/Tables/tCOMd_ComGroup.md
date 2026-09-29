# tCOMd_ComGroup

**Cross-refs:** [tCOMd_Package.md](./tCOMd_Package.md) · [../../ComGroup.md](../../ComGroup.md)

- **Purpose:** Top-level commercial group (brand/program container) that owns packages.
- **Primary Key:** `com_ComGroupID` (autonumber).
- **Foreign Keys:** `com_ManufacturerID` (→ manufacturer lookup).
- **Referenced By:** `tCOMd_Package` (`com_ComGroupID`).
- **Depends On:** manufacturer (implicit).
- **Important Columns:** `com_ComGroupID`, `com_ComGroupCode` (natural key, upper), `com_ComGroupLabel`,
  `com_ManufacturerID`.
- **Builder Table source:** derived from category name (`PDMToMDBService.build_com_group`).
- **Generation stage:** Package Builder (skeleton).
- **Consumer services:** `helpers/mdb_helper.py::get_or_create_com_group`; read by `MDBService`.
- **Business rules:** resolved by `com_ComGroupCode` first (get-or-create); code = `category_name.upper()`.
- **Example record:** `{ com_ComGroupID: 12, com_ComGroupCode: "SEATING", com_ComGroupLabel: "Seating" }`.
- **Typical row count:** small (one per brand/program group).
- **Generation order:** 2.
