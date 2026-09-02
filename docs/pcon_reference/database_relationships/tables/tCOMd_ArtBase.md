# tCOMd_ArtBase

**Cross-refs:** [tCOMd_Article.md](./tCOMd_Article.md) · [../../BuilderTableMapping.md](../../BuilderTableMapping.md)

- **Purpose:** Article base / base-configuration record (series base, base model) for an article.
- **Primary Key:** `com_ArtBaseID` (autonumber; `UNKNOWN` exact name).
- **Foreign Keys:** `com_ArticleID` (→ Article).
- **Referenced By:** none.
- **Depends On:** `tCOMd_Article`.
- **Important Columns:** `com_ArtBaseID`, `com_ArticleID`, base config fields
  (order-code/model-derived; `UNKNOWN` exact names).
- **Builder Table source:** `product_engineering_metadata` (`OrderCodeFormatString`, `ModelList`,
  `ProductMaskKey`).
- **Generation stage:** Package Builder (ArtBase Builder).
- **Consumer services:** `helpers/mdb_helper.py::get_or_create_art_base`;
  read by `MDBService.get_article_property_summary`.
- **Business rules:** get-or-create per article; encodes the base configuration used to derive variants.
- **Example record:** `{ com_ArtBaseID: 7001, com_ArticleID: 5001 }`.
- **Typical row count:** ~one per article.
- **Generation order:** 11.
