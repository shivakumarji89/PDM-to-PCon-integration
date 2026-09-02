# tCOMd_Text

**Cross-refs:** [tCOMd_Article.md](./tCOMd_Article.md) · [tCOMd_Property.md](./tCOMd_Property.md) · [../ReadOrder.md](../ReadOrder.md)

- **Purpose:** Shared localized-text lookup (labels/descriptions) referenced by many entities.
- **Primary Key:** `com_TextID` (autonumber).
- **Foreign Keys:** `com_TextTypeID` (→ text type; resolved by `resolve_text_type_code`).
- **Referenced By:** `tCOMd_Article` (`com_ShortTextID`), `tCOMd_Property` (`com_TextID`),
  `tCOMd_PropValue` (`com_TextID`), `tCOMd_Class` (`com_TextID`).
- **Depends On:** text type lookup.
- **Important Columns:** `com_TextID`, `com_TextName` (natural key), `com_Text_1_en` (English text),
  `com_TextTypeID`.
- **Builder Table source:** display names (property/value/article labels).
- **Generation stage:** Package Builder (on demand, before the referencing entity).
- **Consumer services:** `helpers/mdb_helper.py::get_or_create_text`, `build_*_text_*`;
  read by `article_service.load_articles`, `MDBService.get_article_property_summary`.
- **Business rules:** get-or-create by `com_TextName`; created before any entity that needs its ID;
  English text stored in `com_Text_1_en`.
- **Example record:** `{ com_TextID: 4501, com_TextName: "NOALE191", com_Text_1_en: "Always Bar stool" }`.
- **Typical row count:** large (one per distinct label).
- **Generation order:** 5 (on demand, interleaved before Class/Property/PropValue/Article).
