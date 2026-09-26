# 04 — Base Article / Variant / Configuration Article Model

**Status:** Forensic, evidence-only. No code changed. Builds on
`01_pcon_creator_2_22_2_investigation.md` (§1-4), `09_mdf_export_import_requirements.md`,
`02_mdb_structure_and_relationships.md`, and the PDM legacy baseline
(`docs/Legacy_PDM_Business_Logic/05_Products.md`, `06_Articles.md`, `26_Data_Model.md`,
`docs/SKU_Config_Decode_Findings.md`). Every claim labeled FACT/INFERENCE/UNKNOWN.

---

## Q1. Does pCon store base and final article separately?

**FACT, no.** The pCon.creator manual models exactly **one** database/dialog object —
`Article` — with a single field `Article code` described as "contains the base article
number" (manual p.86, `01_...md` §1). There is no separate "Final Article" dialog, table,
or OCD import row. The **final article number** is not stored anywhere as a discrete
record; it is *computed at runtime/order-time* by concatenating the base article number
with a variant code, per an associated `CodeScheme` (manual §5.3.12 p.129: "A codification
scheme defines how the final article number will be built from the base article number and
the so-called variant code" — `01_...md` §2).

**INFERENCE:** this means "base article" and "final article" are not two entities in a
parent-child relationship in the database sense — they are two *readings* of the same
`Article` row: the stored `ArticleID` (base), and a derived string (final) that exists only
as an assembled output. Do not model a `FinalArticle` table/entity in MK Workbench unless a
generation-time cache is explicitly desired (see Q3).

## Q2. Is the final article a DB entity or a generated identity?

**FACT: generated identity, not a DB entity.** Evidence:
- `ocd_article.csv` (`Article` table) has exactly one identity field, `ArticleID`, described
  as "Base article number" (manual p.373, `01_...md` §1, `09_...md` §2.1).
- `CodeScheme`/`ocd_codescheme.csv` fields (`VarCodeSep`, `ValueSep`, `Visibility`,
  `InVisibleChar`, `UnselectChar`, `Trim`, `MO_Sep`, `MO_Bracket`) are pure *grammar*
  parameters, not article rows (manual pp.387-388, `01_...md` §4, `09_...md` §2.13).
- The MDB schema mirrors this exactly: `tCOMd_Article` has a `com_ArticleCode` (single
  string) and an FK `com_CodeSchemeID → tCOMd_CodeScheme` (file 02 §2 row 4:
  `ocd_export_service.py:911-917`, `_code_schemes` at `ocd_export_service.py:689-732`).
  There is no second `tCOMd_FinalArticle` table anywhere in the current exporter, the stale
  reference docs, or the OCD spec sections read.

**Confidence: FACT** on both the manual side and the current MK Workbench MDB-writer side.

## Q3. How is the final article number generated?

**FACT** (manual §5.3.12, `01_...md` §2, §4):
```
Final Article Number = Article code + VarCodeSep + Variant Code
```
where the **Variant Code** is itself assembled from the currently-selected/visible
property values, governed by the Code Scheme's:
- `Visibility` (`0` = only current valid/visible properties are encoded, `1` = all
  configurable properties are always encoded — manual p.387),
- `ValueSep` (separator between per-property value tokens within the variant code),
- `InVisibleChar`/`UnselectChar` (placeholder characters for hidden/unselected properties),
- `Trim` (whether trailing placeholders are trimmed),
- `MO_Sep`/`MO_Bracket` (multi-option value separators/brackets, for `Multioption`
  properties).
- Since OCD 4.0, **value combination tables** can also drive user-defined article-code
  schemes without an additional relation (manual p.119, `01_...md` §4).

**INFERENCE (cross-checked, not contradicted):** this is architecturally the same
head/tail positional-encoding model that `docs/SKU_Config_Decode_Findings.md` reverse-engineers
from the PDM side (see Q5) — a fixed-position or separator-delimited concatenation of
per-property tokens onto a base code — but the pCon Code Scheme and the PDM SKU format are
**not proven to be the same grammar** (no round-trip test was performed in any prior track).

## Q4. What identifies the base vs. the configuration?

**FACT:**
- **Base** = the `Article.ArticleID` value itself (a fixed string, e.g. what
  `docs/SKU_Config_Decode_Findings.md` calls the "head" — "the product base + positional
  configuration codes"), reused verbatim as the FK target from `ArtBase`, `Price`,
  `Packaging`, `ArticleTaxes` (all keyed on `(Base) article number` — `09_...md` §2.2, §2.6,
  §2.14).
- **Configuration** = the currently-selected set of Property/PropertyValue assignments
  (scope=Configuration properties, per `01_...md` §5), which is *not* itself a stored row —
  it is transient runtime/session state that gets *encoded* into the variant code at
  generation/order time.
- The `$BAN` variable (manual §5.3.11.1 p.110, `01_...md` §2) exists specifically so relation
  code can test "the current base article number" during evaluation — i.e. relations can
  branch on which base an in-progress configuration belongs to, confirming the base/config
  split is meaningful at the relation-language level too.

**Confidence: FACT.**

## Q5. How does PDM represent this?

**FACT** (`docs/SKU_Config_Decode_Findings.md` §1, cross-checked against
`docs/Legacy_PDM_Business_Logic/05_Products.md`, `06_Articles.md`, `26_Data_Model.md`):
- PDM's analogue of "base" is **not a named table** — it is the structural invariant:
  "Attributes that never vary within the structure = identity, baked into the base (DPS
  `$BAN` model), no code" (`SKU_Config_Decode_Findings.md` §6). PDM's SKU has an explicit
  **head.tail** split (`head = code.split(".")[0]`): head = positional configuration codes
  (Type, Leg style, Control switch, ...) with `AttributeValue.OrderCodeValue = NULL` — the
  code exists *only positionally*, nowhere stored as data; tail = parametric attributes
  (Width, Depth, Material, ...) with a real stored `OrderCodeValue` and a token
  (`Attribute.OrderCodeFormatKey`, e.g. `{WD}`).
- `ProductRange.OrderCodeFormatString` is PDM's analogue of pCon's Code Scheme template —
  an ordered `{TOKEN}` string defining tail slice order (`SKU_Config_Decode_Findings.md` §2).
- PDM's `Item` table is the closest analogue of a "final article" **row** — it *is* a
  concrete DB entity (unlike pCon's generated final article number), one row per orderable
  SKU (`26_Data_Model.md` §2.3: `Item.Item` = the code). This is a **structural
  divergence**: PDM materializes every valid final configuration as a real `Item` row,
  whereas pCon.creator computes the final article number on demand and does not require a
  pre-existing row per variant.
- PDM's `Product`/`ProductRange` is the closest analogue of pCon's Article/base-article
  grouping — `05_Products.md` §1 describes a *Super Product* as "a `Product` whose `Item`
  records act as a bundle... of other component `Item` records," and separately (§1) notes
  "the article and product code scheme concepts are documented in `06_Articles.md`."
- **PDM's own legacy article-generation code (`OCDExport.cs`, `06_Articles.md` BR-ART-012)
  hardcodes `articleType = "C"` (configurable) for every emitted article and always emits
  the `ocdArticle` DTO fields positionally** — i.e. even PDM's own legacy exporter follows
  the same base-article + article-type model pCon.creator's manual describes, which is
  reassuring cross-validation that the concept transfers rather than being reinterpreted.

**Confidence: FACT** for the structural facts cited; **INFERENCE** that PDM's `Item` ≈
pCon's realized final-article-number is a reasonable structural parallel, not a proven
1:1 (no evidence any PDM `Item.Item` code is literally reused, unmodified, as a pCon final
article number — separators/schemes could differ).

## Q6. How does pricing reference the article?

**FACT** (`01_...md` §13, `09_...md` §2.6): `Price`/`ocd_price.csv` keys on
`ArticleID` (described explicitly as "(Base) article number") **plus** a
`Variantcondition` field (Char 80) — i.e. price rows are scoped to (base article,
variant condition) pairs, not to a final article number string directly. The variant
condition is a separate assigned/computed runtime string (`$VARCOND`, manual §5.3.11.8
p.125, `01_...md` §3), activated by Pricing-domain Action relations, not the same string
as the Code-Scheme-generated variant code (the manual itself does not crisply state
whether they're identical — `01_...md` §3, "UNKNOWN whether these are the same value").
MK Workbench's own `tCOMd_Price.com_ArticleID → tCOMd_Article.com_ArticleID` FK (file 02
§2 row 26) confirms the same base-article-keyed, not final-article-keyed, pattern in the
current exporter.

**Confidence: FACT** that pricing keys on base article + variant condition, not final
article number; **UNKNOWN** whether variant condition and variant code are the same string
in all cases (flagged already in `01_...md` §3, not resolved here).

## Q7. How does MDB represent this?

**FACT** (file 02 §2 rows 2-4, 17, 22, 26-29): `tCOMd_Article.com_ArticleCode` (base
article, string) with FK `com_CodeSchemeID → tCOMd_CodeScheme` (variant-code grammar,
never itself an article row); `tCOMd_ArtBase.com_ArticleID` (base-article-scoped
restriction rows, string-keyed on class/property/value **names**, not surrogate IDs — a
documented divergence from every other table); `tCOMd_Price.com_ArticleID` +
`com_Variantcondition` (base-article + variant-condition keyed, not final-article-number
keyed). **There is no `tCOMd_FinalArticle` table or column anywhere in the schema evidence
gathered across files 01, 02, 07, or 09.**

**Confidence: FACT.**

## Q8. How does OCD/XOCD represent this (since MDF doesn't exist)?

**FACT** (`09_...md` §2.1, §2.13, §1): the OCD/XOCD CSV import contract is field-identical
to the MDB conceptual model above — `ocd_article.csv` (`ArticleID` = base article number,
`SchemeID` FK to `ocd_codescheme.csv`), `ocd_codescheme.csv` (grammar only), `ocd_artbase.csv`
(base-article-scoped restrictions), `ocd_price.csv` (base article + variant condition).
XOCD is described as "an OCD variant/extension" with the same table shape
(`09_...md` §0.3 table, `xocd_4.3.2_en.md` not read field-by-field in prior tracks).
**One documented ambiguity carries over unresolved:** the XCF (catalog, not commercial-data)
`Variant.csv` table has a `Variant codes` field whose content is "dependent on the sales
product data. It may contain the variant code or the final article code" (manual p.423,
`01_...md` §3, `09_...md` §3) — i.e. even the OCD/XCF ecosystem itself is not fully crisp
about whether a *catalog-level* variant key is always the same string as the commercial-data
variant code. This is a manual-documented ambiguity, not a MK Workbench gap.

**Confidence: FACT** for the OCD/XOCD commercial-data contract; **UNKNOWN** (manual's own
wording) for the XCF `Variant codes` field's exact content in all cases.

---

## Bottom line (no invented parent-child relationship)

There is **no evidence anywhere** — manual, OCD spec citations, MDB schema, current
exporter code, or PDM baseline — of a stored parent-child table relationship between a
"base article" row and a "final article" row. The correct model, confirmed independently
by the pCon manual (§1-4), the MDB/OCD table schemas (§7-8), and PDM's own legacy exporter
(`OCDExport.cs`, Q5), is:

**one Article record per base**, with the final, orderable identity being a **runtime
string computed from (base article code) + (Code Scheme separators) + (currently selected
property-value tokens)** — never a second database row. PDM's own `Item` table is the one
place in this whole picture that *does* materialize a row per final variant, which is a
genuine structural difference MK Workbench must account for if it intends to keep
generating one `Item`-per-SKU while target-side pCon/OCD expects generation-time
computation instead of storage.
