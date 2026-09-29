# tCOMd_Article

**Cross-refs:** [tCOMd_Package.md](./tCOMd_Package.md) · [tCOMd_ArticleClass.md](./tCOMd_ArticleClass.md) · [tCOMd_ArtBase.md](./tCOMd_ArtBase.md)

- **Purpose:** An article (article code) under a package — the sellable/configurable unit.
- **Primary Key:** `com_ArticleID` (autonumber).
- **Foreign Keys:** `com_PackageID` (→ Package), `com_OfmlTypeID` (→ OfmlType),
  `com_ShortTextID` (→ Text).
- **Referenced By:** `tCOMd_ArticleClass` (`com_ArticleID`), `tCOMd_ArtBase` (`com_ArticleID`),
  `tCOMd_Price` (`com_ArticleID`).
- **Depends On:** `tCOMd_Package`, `tCOMd_OfmlType`, `tCOMd_Text`.
- **Important Columns:** `com_ArticleID`, `com_ArticleCode` (natural key = `Product.Product`),
  `com_ShortTextID`, `com_PackageID`, `com_OfmlTypeID`.
- **Builder Table source:** article identity (`Product.Product`) + `product_engineering_metadata`.
- **Generation stage:** Package Builder (Article Builder).
- **Consumer services:** `helpers/mdb_helper.py::get_or_create_article`, `get_existing_article_defaults`,
  `prune_package_article_set`; read by `MDBService.get_article_property_summary`,
  `article_service.load_articles`.
- **Business rules:** get-or-create by article code within package; `ReplaceArticleSet` prunes the
  existing set first (destructive); empty article code → blocked.
- **Example record:** `{ com_ArticleID: 5001, com_ArticleCode: "NOALE191", com_PackageID: 88 }`.
- **Typical row count:** large (one per article code in the package).
- **Generation order:** 9.
