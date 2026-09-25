# tCOMd_OfmlType

**Cross-refs:** [tCOMd_Article.md](./tCOMd_Article.md) · [../WriteOrder.md](../WriteOrder.md)

- **Purpose:** OFML type/render classification for articles (how an article is realized in OFML/PCon).
- **Primary Key:** `com_OfmlTypeID`.
- **Foreign Keys:** none observed.
- **Referenced By:** `tCOMd_Article` (`com_OfmlTypeID`).
- **Depends On:** nothing (lookup).
- **Important Columns:** `com_OfmlTypeID`, type code/label (`UNKNOWN` exact names).
- **Builder Table source:** none (packaging/render metadata); resolved from article defaults.
- **Generation stage:** Article Builder (resolved before articles).
- **Consumer services:** `helpers/mdb_helper.py::resolve_ofml_type_id`, `get_existing_article_defaults`.
- **Business rules:** a default OFML type is resolved per package/article defaults; used for every
  created article.
- **Example record:** `{ com_OfmlTypeID: 3, code: "..." }`.
- **Typical row count:** small (few OFML types).
- **Generation order:** 3 (before Article).
