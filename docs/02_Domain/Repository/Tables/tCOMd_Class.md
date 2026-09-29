# tCOMd_Class

**Cross-refs:** [tCOMd_ArticleClass.md](./tCOMd_ArticleClass.md) · [tCOMd_Property.md](./tCOMd_Property.md)

- **Purpose:** Property/article class (metatype behaviour grouping) that articles are members of.
- **Primary Key:** `com_ClassID` (autonumber).
- **Foreign Keys:** `com_TextID` (→ Text, class label).
- **Referenced By:** `tCOMd_ArticleClass` (`com_ClassID`).
- **Depends On:** `tCOMd_Text`.
- **Important Columns:** `com_ClassID`, `com_ClassName` (natural key), `com_TextID`.
- **Builder Table source:** property class grouping / `product_configuration_features`.
- **Generation stage:** Package Builder (Class Builder).
- **Consumer services:** `helpers/mdb_helper.py::get_or_create_class`;
  read by `MDBService.get_class_names`.
- **Business rules:** get-or-create by `com_ClassName`; class role can be overridden
  (`class_role_overrides`, `classify_class_role`).
- **Example record:** `{ com_ClassID: 21, com_ClassName: "Fabric", com_TextID: 4600 }`.
- **Typical row count:** moderate (one per class).
- **Generation order:** 6.
