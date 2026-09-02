# tCOMd_Price

**Cross-refs:** [tCOMd_PriceList2.md](./tCOMd_PriceList2.md) · [tCOMd_Article.md](./tCOMd_Article.md) · [../../PriceGeneration.md](../../PriceGeneration.md) · [../../VariantConditions.md](../../VariantConditions.md)

- **Purpose:** Price for an article/option combination, keyed by a variant condition and price list.
- **Primary Key:** `com_PriceID`.
- **Foreign Keys:** `com_ArticleID` (→ Article), `com_PriceListID` (→ PriceList2).
- **Referenced By:** none.
- **Depends On:** `tCOMd_Article`, `tCOMd_PriceList2`.
- **Important Columns:** `com_PriceID`, `com_ArticleID`, `com_PriceListID`, `com_VariantCondition`,
  `com_PriceValue`.
- **Builder Table source:** **none directly** — pricing is **item-level** (`Item.BasePrice*`,
  `ItemOptionValues.IncrementalPrice*`), intentionally excluded from the Builder Table.
- **Generation stage:** Price Generator (item-level; item enumeration happens here).
- **Consumer services:** `PDMMaintenance/MDBQuery.cs` (read example); future `PConPriceGenerator`.
- **Business rules:** `com_VariantCondition` is generated from option order codes (see
  [VariantConditions](../../VariantConditions.md)); article + price list must exist first; pricing
  varies per item (~18% base, ~24% incremental) so it cannot be product-collapsed.
- **Example record:** `{ com_PriceID: 30012, com_ArticleID: 5001, com_PriceListID: 14, com_VariantCondition: "...", com_PriceValue: 249.00 }`.
- **Typical row count:** very large (article × variant × price list).
- **Generation order:** 13 (last; after PriceList2).
