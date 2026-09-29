# tCOMd_PriceList2

**Cross-refs:** [tCOMd_Price.md](./tCOMd_Price.md) · [../../PriceGeneration.md](../../PriceGeneration.md)

- **Purpose:** Named price list (e.g. `EUR...2019`) grouping prices for a market/currency/period.
- **Primary Key:** `com_PriceListID`.
- **Foreign Keys:** none observed.
- **Referenced By:** `tCOMd_Price` (`com_PriceListID`).
- **Depends On:** nothing (lookup).
- **Important Columns:** `com_PriceListID`, `com_PriceListLabel`.
- **Builder Table source:** none (price stage metadata; **not** product-centric engineering data).
- **Generation stage:** Price Generator (item-level).
- **Consumer services:** `PDMMaintenance/MDBQuery.cs` (read example); future `PConPriceGenerator`.
- **Business rules:** a price references exactly one price list; lists are created/selected before prices.
- **Example record:** `{ com_PriceListID: 14, com_PriceListLabel: "EUR List 2019" }`.
- **Typical row count:** small (one per market/currency/period).
- **Generation order:** 12 (before Price).
