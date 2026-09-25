# tCOMd_ArticleClass

**Cross-refs:** [tCOMd_Article.md](./tCOMd_Article.md) · [tCOMd_Class.md](./tCOMd_Class.md)

- **Purpose:** Many-to-many join linking an article to a class (article's class membership).
- **Primary Key:** composite (`com_ArticleID`, `com_ClassID`) (or surrogate; `UNKNOWN`).
- **Foreign Keys:** `com_ArticleID` (→ Article), `com_ClassID` (→ Class).
- **Referenced By:** none.
- **Depends On:** `tCOMd_Article`, `tCOMd_Class`.
- **Important Columns:** `com_ArticleID`, `com_ClassID`.
- **Builder Table source:** article ↔ property-class membership.
- **Generation stage:** Package Builder (Class link).
- **Consumer services:** `helpers/mdb_helper.py::get_or_create_article_class`;
  read by `MDBService.get_article_property_summary`.
- **Business rules:** both endpoints must exist first; get-or-create avoids duplicate links.
- **Example record:** `{ com_ArticleID: 5001, com_ClassID: 21 }`.
- **Typical row count:** large (article × class links).
- **Generation order:** 10.
