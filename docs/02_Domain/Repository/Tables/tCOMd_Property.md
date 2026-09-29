# tCOMd_Property

**Cross-refs:** [tCOMd_PropValue.md](./tCOMd_PropValue.md) · [tCOMd_Text.md](./tCOMd_Text.md)

- **Purpose:** Property definition (a configurable dimension: attribute or option name).
- **Primary Key:** `com_PropertyID` (autonumber).
- **Foreign Keys:** `com_TextID` (→ Text, property label).
- **Referenced By:** `tCOMd_PropValue` (`com_PropertyID`).
- **Depends On:** `tCOMd_Text`.
- **Important Columns:** `com_PropertyID`, `com_PropertyName` (natural key), `com_TextID`.
- **Builder Table source:** `product_attributes` (Attribute name) and `product_options` (Option name).
- **Generation stage:** Package Builder (Property Builder).
- **Consumer services:** `helpers/mdb_helper.py::get_or_create_property`,
  `normalize_property_column_name`, `build_property_text_name`;
  read by `MDBService.get_property_definitions`, `get_article_property_summary`.
- **Business rules:** get-or-create by normalized property name; created before its values.
- **Example record:** `{ com_PropertyID: 310, com_PropertyName: "Fabric colour", com_TextID: 4610 }`.
- **Typical row count:** moderate (one per distinct property).
- **Generation order:** 7.
