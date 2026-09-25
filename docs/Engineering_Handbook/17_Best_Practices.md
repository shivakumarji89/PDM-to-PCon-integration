# 17 — Best Practices

**Source:** OFML specifications, style guides & application notes (EasternGraphics/IBA), consolidated for the MK Product Workbench Engineering Handbook.
**Status:** Consolidated from specification docs; unclear items marked `UNKNOWN`.

Consolidated engineering patterns from the OFML style guides, application notes and fact
sheets. Grouped by theme; each practice cites its source document. Companion chapters:
[05_Engineering_Workflows](05_Engineering_Workflows.md) · [12_Validation_Rules](12_Validation_Rules.md) ·
[13_Naming_Standards](13_Naming_Standards.md) · [14_Generation_Process](14_Generation_Process.md) ·
[18_Design_Principles](18_Design_Principles.md).

---

## 1. Separation of concerns (commercial vs graphical)

| Practice | Rationale | Source doc |
|----------|-----------|------------|
| Keep **commercial data (OCD)** separate from **catalog data**. OCD is *not* a catalog format; the link is made by the software **via article number**. | Independent maintenance of price/config vs presentation. | ocd_4.3 §1 |
| Keep **geometry (ODB / GO)** separate from **commercial logic (OCD)** and **interaction (OAP)**; each layer has its own tables. | Layered OFML model; parallel maintenance & reuse. | ocd_4.3, odb_2.4, oap_1.6.1 |
| Split article data across many OCD tables rather than one wide record; leave optional info out. | Increases clarity, eases extensibility & incremental exchange. | ocd_4.3 §2 |
| Model **materials** independently (`.mat`) and reference them; use base materials + modifiers instead of duplicating. | Reuse, consistent appearance, smaller data. | omats_2.2 §4 |

See [18_Design_Principles](18_Design_Principles.md) for the layering rationale.

---

## 2. Reuse of base libraries & parametric modelling

| Practice | Rationale | Source doc |
|----------|-----------|------------|
| Build products on the **GO (Generic Office) base library** and the general Metatypes (e.g. reference `GO_TABLE` / `desk`) rather than modelling from scratch. | Standard interactions, attach behaviour and geometry for free. | MT_1.18.0 §2, GO_1.12.0 |
| Define a **metatype once** (`go_types`) and realise many article numbers through `go_articles` (`prm_set`). | One parametric definition covers a whole article range. | MT_1.18.0 §2 |
| Reference external geometry (`.geo`) or ODB blocks instead of repeating primitives; prefer ODB primitives over external files when efficiency matters. | Reuse vs runtime cost trade-off. | odb_2.4 §2.7, §3.6 |
| Use **base material + inline modifiers** for finish variants. | Avoids near-duplicate `.mat` files. | omats_2.2 §4 |

---

## 3. Naming & style best practices

| Practice | Rule | Source doc |
|----------|------|------------|
| Metatype names: `MT_` + `[SE_]`series + Name, each word capitalised; `GType` = name without `MT_`. | Consistent, parseable identifiers. | MT-StyleGuide_1.2 |
| Property names: `G` + series id + `_` + CamelCase, no separators. | Uniqueness across series. | MT-StyleGuide_1.2 |
| `go_articles` id = Metatype ID + `_` + article number (+ optional `_ext`); add a distinguishing number for multiple property sets of one article. | Guarantees unique article naming. | MT-StyleGuide_1.2 |
| Attach points `Ap` + `SE_` (+ `CH_` for child) + Name; property classes `PC_` + `SE_`; action messages `msg` + `SE_`. | Predictable prefixes. | MT-StyleGuide_1.2 |
| OAP identifiers: alnum + `_`/`-`, not starting with a digit; **camelCase** for readability; action `ID` should correspond to what it does. | Traceable OAP data. | OAP-Styleguide_en |
| Identifiers must use the **same spelling everywhere** (case-sensitive). | Cross-table integrity. | MT_1.18.0, oap_1.6.1 |
| Give dimensions in the **unit used in the paper price list**. | Data matches the commercial source. | MT-StyleGuide_1.2 |

Full catalogue: [13_Naming_Standards](13_Naming_Standards.md).

---

## 4. Article-text data-creation best practices

Based on the IBA "Uniform customer-oriented article descriptions" recommendation.

| Practice | Detail | Source doc |
|----------|--------|------------|
| Provide **three text types**: short, long, variant. | Short = 1 line ≤ 50 chars; long = full description understandable on its own; variant = configured properties. | fact_sheet_ocd_article_texts |
| Long text must stand alone (independent of short text). | Only one of short/long is shown by default. | fact_sheet_ocd_article_texts |
| Long-text lines are **paragraphs**; each new line forces a line break (continuous text otherwise). | Predictable form rendering. | fact_sheet_ocd_article_texts |
| Put fixed dimensions at the **end** of the long text if not in the variant text; order **W × D × H**; unit mm (DE) / cm (else) / inch (US). | Consistent measurement presentation. | fact_sheet_ocd_article_texts |
| **Describe** variant properties textually — do **not** use codes/abbreviations for characteristic or value. | Human-readable offers. | fact_sheet_ocd_article_texts, OCD_ArticleDescription_1.2 |
| Steer text assembly via **`TxtControl`** rather than duplicating text. | Central control of form output. | ocd_4.3 §5 |

---

## 5. Pricing & multiple-price-list data creation

| Practice | Detail | Source doc |
|----------|--------|------------|
| When a **new dataset / price list** is added, **do not change** existing entries in the price table; add new dated entries instead. | Preserves historical/still-valid prices. | AN-2017-01 |
| Correct a wrongly far-future `DateTo` only in the defined change scenarios. | Controlled validity windows. | AN-2017-01 §1–2 |
| For a variant that becomes/ceases to be price-relevant, add/limit price components by date rather than deleting; add a **hint in the property/value text**. | Traceability for users. | AN-2017-01 §2.4–2.6 |
| Prefer **global price components** over article-specific ones for extra charges where possible. | Less duplication, easier upkeep. | AN-2017-01 §2.8 |
| Model taxes abstractly via **tax categories / taxation schemes**, not hard-coded rates. | Portable across regions. | ocd_4.3 §2.25, OCD_TaxCategories_1.0 |

Workflow steps: [05_Engineering_Workflows](05_Engineering_Workflows.md).

---

## 6. OCD feature & control-data best practices

| Practice | Detail | Source doc |
|----------|--------|------------|
| Check the **supported-OCD-features** matrix before using newer OCD features. | Not every application supports every feature/version. | AN-2014-04 |
| Configure application behaviour through **control-data tables** (`proginfo`, `plelement`, `anyarticle`, `epdfproductdb`, planning-group tables) rather than ad-hoc means. | Standard extension points. | AN-2006-01 |
| Use `proginfo` options for 2D layer names, property-value pictures (`@VOID`), coding schemes and order generation. | Documented control knobs. | AN-2006-01 §2, §5 |

---

## 7. OAP data-creation best practices

| Practice | Detail | Source doc |
|----------|--------|------------|
| Follow the OAP style guide for `ID`/`Symbol`/`OID` naming; camelCase; action IDs mirror their effect. | Maintainable interaction data. | OAP-Styleguide_en |
| Reuse **`NumTripel`** named positions instead of repeating raw coordinates. | Single source for positions. | oap_1.6.1 §4.2 |
| Drive property editors through `PropEdit2` / `PropEditProps` / `PropEditClasses` configuration. | Consistent editor UX. | oap_1.6.1 §4.8 |
| Consult the OAP method reference and data-creation app note when authoring actions. | Correct method/parameter use. | methods4OAP, AppNote_OAP_DataCreation_EN |

---

## 8. Versioning & compatibility

| Practice | Detail | Source doc |
|----------|--------|------------|
| Pick **format versions supported by the target pCon applications** (OCD/XCF/OAP/MT/DSR compatibility matrix). | Data must load in the intended tools. | AN-2023-01 |
| Record format/data version in the OCD **`Version`** table; use validity dates (`DateFrom`/`DateTo`). | Reproducible, dated datasets. | ocd_4.3 §2.23 |
| Read the **history chapter** of each spec before adopting a new version. | Understand breaking changes. | AN-2023-01 |
| MT/GO expressions must match the OFML Part III grammar of the targeted runtime. | Runtime compatibility. | MT_1.18.0 §2 |

---

## 9. Validation before generation

| Practice | Detail | Source doc |
|----------|--------|------------|
| Prefer **descriptive, table-based** definitions (ODB/OCD/MT) that can be checked for consistency over hand-programmed logic. | Verifiable data. | odb_2.4 §1 |
| Enforce referential integrity: every `TextID`, `RelObjID`, `SchemeID`, `PropertyClass/PropertyName`, `child_key` must resolve. | Prevents broken configuration. | ocd_4.3, MT_1.18.0 |
| Ensure **all `go_*` tables exist** (empty if unused) and encoding matches `go_info` (`utf8`). | MT loader requires the full set. | MT_1.18.0 §2 |
| Provide a **base (no-variant) entry** before variant/delta entries (e.g. `Packaging`). | Deltas are relative to the base. | ocd_4.3 §2.5 |
| Validate identifiers do not start with a digit and are spelled identically everywhere. | Common load failure. | MT_1.18.0, ocd_4.3, oap_1.6.1 |

Rule catalogue with IDs: [12_Validation_Rules](12_Validation_Rules.md). Generation gate:
[14_Generation_Process](14_Generation_Process.md).

---

## 10. Common pitfalls to avoid

| Pitfall | Why it hurts | Source doc |
|---------|--------------|------------|
| Using OCD as a **catalog** format. | It is not one; catalog data must come from XCF/OAS. | ocd_4.3 §1 |
| Editing existing price entries when adding a new price list. | Corrupts historical validity; breaks offers. | AN-2017-01 |
| Codes/abbreviations in variant texts. | Unreadable customer offers. | fact_sheet_ocd_article_texts |
| Mixing measurement units between data and price list. | Wrong dimensions in forms. | MT-StyleGuide_1.2, fact_sheet |
| Inconsistent identifier spelling / leading-digit IDs. | Tables fail to link / load. | MT_1.18.0, oap_1.6.1 |
| Omitting the base entry before delta/variant entries. | Deltas have no reference → wrong values. | ocd_4.3 §2.5 |
| Duplicating materials/geometry instead of referencing base + modifiers/blocks. | Bloated, inconsistent data. | omats_2.2, odb_2.4 |
| Adopting a new format feature/version unsupported by the target app. | Data won't load. | AN-2014-04, AN-2023-01 |

---

## 11. `UNKNOWN` items

- Manufacturer-specific text length/format limits beyond the IBA short-text 50-char guide — `UNKNOWN`.
- `.obx` schema-level authoring rules — `UNKNOWN` (see [15_File_Formats](15_File_Formats.md) §10).
