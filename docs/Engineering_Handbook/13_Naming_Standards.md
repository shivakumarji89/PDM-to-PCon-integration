# 13 — Naming Standards

**Source:** OFML style guides + specifications (EasternGraphics/IBA), consolidated for the MK Product Workbench Engineering Handbook.
**Status:** Consolidated from specification docs; unclear items marked `UNKNOWN`.

This chapter consolidates all naming conventions and standards across the OFML corpus.
Cross-reference the domain chapters:
[06_OFML](06_OFML.md) · [07_OCD](07_OCD.md) · [08_ODB](08_ODB.md) ·
[09_OAP](09_OAP.md) · [10_Metatype](10_Metatype.md) · [11_Product_Model](11_Product_Model.md) ·
[19_Glossary](19_Glossary.md). Companion validation rules: [12_Validation_Rules](12_Validation_Rules.md).

> Legend: `SE_` = series identifier, `MAN` = manufacturer identifier, `<...>` = placeholder,
> `[...]` = optional segment.

---

## 1. Core identity naming (program IDs, article numbers, variant codes)

| Element | Rule | Example | Source doc |
| --- | --- | --- | --- |
| Program ID | Unambiguous ID identifying an OFML library; alphanumeric library/series identifier. | `OFFICE2` | ofml_glossary_1.1_en.md · OLAYERS_1.3.1_en.md |
| Manufacturer ID | OFML manufacturer identifier (DSR key `manufacturer`). | `EGR` | OLAYERS_1.3.1_en.md · dsr-3.7_en.md |
| Series / library ID | OFML identifier of library/series (DSR key `program`); unambiguous within manufacturer. | `OFFICE2` | ofml_glossary_1.1_en.md · dsr-3.7_en.md |
| Commercial series ID | Code unambiguously identifying a commercial series within the manufacturer. | `UNKNOWN` (manufacturer-defined) | ofml_glossary_1.1_en.md |
| Basic article number | Alphanumeric code uniquely identifying the (unconfigured) product; sometimes unique only within a series. | `VP2003` | ofml_glossary_1.1_en.md · article_interface_1.4_en.md |
| Final article number | Normally = basic article number + variant code (DB-dependent). | `VP2003+<varcode>` | article_interface_1.4_en.md |
| Variant code | Encodes values of configurable characteristics; may be empty or partial. Manufacturer-specific (`@VarCode`) or manufacturer-independent OFML variant code (`@OFMLVarCode`). | `UNKNOWN` (data-specific) | article_interface_1.4_en.md |
| Property variant code (PVC) | `<key>=<value>` pairs separated by `;`; property keys **without** leading `@`; values as literal OFML constants. | `Width=1200;Color=green` | oap_1.6.1-en.md |

---

## 2. General identifier rules (per format)

| Element | Rule | Example | Source doc |
| --- | --- | --- | --- |
| MT identifier (`ID`) | ASCII alphanumerics + `_`; **must not start with a digit**; same spelling (case-sensitive) everywhere. | `SE_StandardDesk` | MT_1.18.0_en.md |
| OCD property-class identifier | Alphanumerics + underscore; **first character must not be numeric**. | `PC_Measures` | ocd_4.3_en.md |
| OCD property name | Symbolic, **language-independent** identifier. | `Width` | ocd_4.3_en.md |
| OAP `ID` | ASCII alphanumerics + `-` + `_`; same spelling everywhere. | `addableChildren` | oap_1.6.1-en.md |
| OAP `Symbol` / identifier | Alphanumerics + `_`; **first character not numeric**; camelCase preferred for readability. | `mainPropsForTP` | oap_1.6.1-en.md · OAP-Styleguide_en.md |
| OAP `OID` | Simple `ID` or period-separated hierarchical name (parent.child). | `Father.Leg` | oap_1.6.1-en.md |
| Language code | ISO 639-1 two lowercase letters; optional ISO 3166-1 alpha-2 region (uppercase) after `-`. | `en-US`, `de` | oap_1.6.1-en.md · property_interface_2.9_en.md |

---

## 3. Metatype naming (MT-StyleGuide 1.2 — complete)

| Element | Rule | Example | Source doc |
| --- | --- | --- | --- |
| Metatype name (`go_types`) | `MT_` + `[SE_]` series id + Name; upper/lower case, **each word starts uppercase**. | `MT_SE_StandardDesk` | MT-StyleGuide_1.2_en.md |
| `GType` entry | Same as the Metatype name **without** the leading `MT_`. | `SE_StandardDesk` | MT-StyleGuide_1.2_en.md |
| Property name (`go_properties`) | `G` + series id + `_`; composite words with **no separators**, first letter of each word uppercase; remainder arbitrary. | `GSE_Width` | MT-StyleGuide_1.2_en.md |
| Article ID (`go_articles`) | Metatype ID + `_` + article number + optional `_`extension; if multiple property sets for one article, append a distinguishing number. | `MT_SE_Table_VP2004_1` | MT-StyleGuide_1.2_en.md |
| Child-oriented property key | `CHP_` + `SE_` + alphanumerics; **each word starts uppercase**. | `CHP_SE_Legs` | MT-StyleGuide_1.2_en.md |
| Child created by property (`go_childprops`) | `SE_` + name (upper/lower, arbitrary sequence). | `SE_OrgBridge` | MT-StyleGuide_1.2_en.md |
| Attachment point (`go_attpt`) | `Ap` + `SE_` + (child point: additional `CH_`) + Name starting uppercase. | `ApSE_TableL`, `ApSE_CH_AddOn` | MT-StyleGuide_1.2_en.md |
| Property class (`go_propclasses`) | `PC_` + `SE_` + arbitrary upper/lower sequence. | `PC_SE_Measures` | MT-StyleGuide_1.2_en.md |
| Action message (`go_actions`) | `msg` + `SE_` + arbitrary upper/lower sequence. | `msgSE_notPossible` | MT-StyleGuide_1.2_en.md |
| Dimension unit | Dimensions given in the **measurement unit used in the paper price list**; internal name arbitrary (follows `go_types` rules). | `UNKNOWN` (unit per pricelist) | MT-StyleGuide_1.2_en.md |

---

## 4. OAP naming (OAP-Styleguide — key prefixes)

Basic rule: IDs may be chosen freely as long as they are alphanumeric and **do not start with a digit**; **camelCase preferred**. Each key is prefixed by a unique letter combination indicating its table.

| Element | Rule (prefix) | Example | Source doc |
| --- | --- | --- | --- |
| ActionChoice | `ACH_` | `ACH_addableChildren` | OAP-Styleguide_en.md |
| ActionList | `ACL_` | `ACL_addableChildren` | OAP-Styleguide_en.md |
| Action | `AC_` | `AC_...` | OAP-Styleguide_en.md |
| CreateObj-Action | `AC_CO_` | `AC_CO_Table` | OAP-Styleguide_en.md |
| DimChange-Action | `AC_DC_` | `AC_DC_Width` | OAP-Styleguide_en.md |
| Delete-Action | `AC_DL_` | `AC_DL_Table` | OAP-Styleguide_en.md |
| PropertyChange-Action | `AC_PC_` | `AC_PC_colorGreen` | OAP-Styleguide_en.md |
| PropEdit-Action | `AC_PE_` | `AC_PE_Colors` | OAP-Styleguide_en.md |
| ShowMedia-Action | `AC_SM_` | `AC_SM_Video` | OAP-Styleguide_en.md |
| SelectObj-Action | `AC_SO_` | `AC_SO_Father` | OAP-Styleguide_en.md |
| MethodCall-Action | `AC_call_` (mirror the MethodCall ID with `MC` replaced by `AC_call`) | `AC_call_setPropValue_Color_green` | OAP-Styleguide_en.md |
| ActionChoice-Action | `AC_choice_` | `AC_choice_colors` | OAP-Styleguide_en.md |
| CreateObject | `CO_` | `CO_Table12345` | OAP-Styleguide_en.md |
| DimChange | `DC_` | `DC_Width` | OAP-Styleguide_en.md |
| ExtMedia | `XM_` | `XM_Video` | OAP-Styleguide_en.md |
| Interactor | `IA_` | `IA_addTableR` | OAP-Styleguide_en.md |
| Image | `IMG_` | `IMG_AttachTableTop` | OAP-Styleguide_en.md |
| MethodCalls | `MC_` | `MC_doSomething` | OAP-Styleguide_en.md |
| Message | `MSG_` | `MSG_info` | OAP-Styleguide_en.md |
| NumTriple | `NT_` | `NT_leftArmRest` | OAP-Styleguide_en.md |
| OAP-Type | `OAP_` | `OAP_Table` | OAP-Styleguide_en.md |
| Object | `OB_` | `OB_self` | OAP-Styleguide_en.md |
| PropChange | `PC_` | `PC_addArmRest` | OAP-Styleguide_en.md |
| PropEdit (deprecated) | `PE_` | `PE_mainPropsForTP` | OAP-Styleguide_en.md |
| PropEdit2 | `PE_` | `PE_mainPropsForTP` | OAP-Styleguide_en.md |
| PropEditProp | `PE_PR_` | `PE_PR_Color` | OAP-Styleguide_en.md |
| PropEditClass | `PE_CL_` | `PE_CL_Dimension` | OAP-Styleguide_en.md |
| Text | `TXT_` | `TXT_AttachTableTop` | OAP-Styleguide_en.md |
| Text for title | `TXT_Title_` | `TXT_Title_Properties` | OAP-Styleguide_en.md |

---

## 5. OCD table & column naming

| Element | Rule | Example | Source doc |
| --- | --- | --- | --- |
| Table name | Fixed spec-defined table names (e.g. `Article`, `Property`, `PropertyClass`, `RelationObj`). | `Property` | ocd_4.3_en.md |
| Column name | Fixed spec-defined field names per table position. | `PropertyName`, `RelObjID` | ocd_4.3_en.md |
| Property-class column | Alphanumerics + `_`; first character not numeric. | `PC_Dimension` | ocd_4.3_en.md |
| Property-name column | Symbolic, language-independent identifier. | `Color` | ocd_4.3_en.md |
| Order unit | `OrderUnit` value ≤ 3 characters (Char). | `Pcs` | ocd_4.3_en.md |
| Reserved keywords | Identifiers listed in Appendix G must not be used as names. Full list: `UNKNOWN`. | `UNKNOWN` | ocd_4.3_en.md |

---

## 6. Layer & tag naming (OLAYERS)

| Element | Rule | Example | Source doc |
| --- | --- | --- | --- |
| Generic layer name | `72_<MAN>_<SERIES>_<MOD>[_<TAG>]`; underscores separate every segment; `72` = AutoDesk furniture qualification. | `72_EGR_OFFICE2_D3_ANY` | OLAYERS_1.3.1_en.md |
| Layer case rule | Case-insensitive; use uppercase; names differing **only** by case are not allowed. | `72_EGR_OFFICE2_D3` | OLAYERS_1.3.1_en.md |
| General-layer modes | `*_DIMENSIONS_MM`, `*_TEXT_<LANG>`, `*_ARTICLE_INFO`, `*_ARTICLE_INFO_DPOS`, `*_SPECIAL`, `*_MISC`. `<LANG>` = ISO 639-1. | `72_EGR_OFFICE2_TEXT_EN` | OLAYERS_1.3.1_en.md |
| 3D-layer modes | `*_D3_<TAG>`, `*_D3FRONT_<TAG>` (TAG mandatory); `*_ACOUSTICS_<TAG>` (TAG optional). | `72_EGR_OFFICE2_D3_TB_FOOT` | OLAYERS_1.3.1_en.md |
| 2D-layer mode | `*_D2_<TAG>` (TAG mandatory). | `72_EGR_OFFICE2_D2_ANY` | OLAYERS_1.3.1_en.md |
| Geometry tags | Standardized tag names, e.g. `ANY` (unspecified) and table tags `TB_*` (`TB_FOOT`, `TB_FRAME`, `TB_GLASS`, `TB_CASTORS`, ...). | `TB_BACKPLANE` | OLAYERS-TAGS_1.2.md |

---

## 7. File & folder naming

| Element | Rule | Example | Source doc |
| --- | --- | --- | --- |
| Metatype table file | `go_` + table name (lowercase) + `.csv`, one table per file. | `go_types.csv`, `go_articles.csv` | MT_1.18.0_en.md |
| MT/OCD/OAP encoding | UTF-8 (MT also allows ASCII); OAP allows optional BOM; NFC normalization recommended. | — | MT_1.18.0_en.md · oap_1.6.1-en.md · ocd_4.3_en.md |
| Comment lines | Lines starting with `#` are comments (MT tables). | `# comment` | MT_1.18.0_en.md |
| OCD / OAP table files | CSV, semicolon-separated, spec-defined table file names. | `UNKNOWN` (per spec table list) | ocd_4.3_en.md · oap_1.6.1-en.md |
| Package / namespace naming | OFML package = distribution unit tagged with a unique version number; hierarchical package name space per OFML Part III. Detailed naming scheme: `UNKNOWN`. | `UNKNOWN` | ofml_glossary_1.1_en.md |

---

## `UNKNOWN` summary

- Commercial series ID format, dimension unit and variant-code structure are manufacturer/data-specific.
- OCD Appendix G reserved-keyword list not enumerated.
- OFML package/namespace naming scheme not fully specified here.
- OCD/OAP full table-file naming lists not enumerated.
