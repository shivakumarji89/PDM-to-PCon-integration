# tCOMd_DistributionRegion

**Cross-refs:** [tCOMd_Package.md](./tCOMd_Package.md) · [../WriteOrder.md](../WriteOrder.md)

- **Purpose:** Distribution region lookup for packages (market/region scope). Fixed value in the
  current pipeline (`DistributionRegionID = 5`).
- **Primary Key:** `com_DistributionRegionID`.
- **Foreign Keys:** none.
- **Referenced By:** `tCOMd_Package` (`com_DistributionRegionID`).
- **Depends On:** nothing (root).
- **Important Columns:** `com_DistributionRegionID`, region label/code (`UNKNOWN` exact name).
- **Builder Table source:** none (packaging constant).
- **Generation stage:** Package Builder (ensured first).
- **Consumer services:** `helpers/mdb_helper.py::ensure_distribution_region_exists`.
- **Business rules:** region 5 is the fixed HMX distribution region; ensured to exist before Package.
- **Example record:** `{ com_DistributionRegionID: 5, label: "..." }`.
- **Typical row count:** very small (handful of regions).
- **Generation order:** 1 (before ComGroup/Package).
