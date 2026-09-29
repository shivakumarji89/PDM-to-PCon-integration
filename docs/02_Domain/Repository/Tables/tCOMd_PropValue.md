# tCOMd_PropValue

**Cross-refs:** [tCOMd_Property.md](./tCOMd_Property.md) · [tCOMd_Text.md](./tCOMd_Text.md)

- **Purpose:** Property value (a selectable value under a property: attribute value or option value).
- **Primary Key:** `com_PropValueID` (autonumber).
- **Foreign Keys:** `com_PropertyID` (→ Property), `com_TextID` (→ Text, value label).
- **Referenced By:** (logically by article configurations / prices via variant conditions).
- **Depends On:** `tCOMd_Property`, `tCOMd_Text`.
- **Important Columns:** `com_PropValueID`, `com_PropertyID`, value code (`OrderCodeValue`-derived,
  normalized), `com_TextID`.
- **Builder Table source:** `product_attributes` values and `product_options` values (with `Code`).
- **Generation stage:** Package Builder (PropValue Builder).
- **Consumer services:** `helpers/mdb_helper.py::get_or_create_prop_value`,
  `normalize_prop_value_code`, `build_prop_value_text_name`, `build_propvalue_text_value`;
  read by `MDBService.get_article_property_summary`.
- **Business rules:** get-or-create by (property, normalized value code); property must exist first;
  option `Code` (`OrderCodeValue`) is retained for variant/price keying.
- **Example record:** `{ com_PropValueID: 9902, com_PropertyID: 310, code: "RED", com_TextID: 4611 }`.
- **Typical row count:** large (one per property value).
- **Generation order:** 8.
