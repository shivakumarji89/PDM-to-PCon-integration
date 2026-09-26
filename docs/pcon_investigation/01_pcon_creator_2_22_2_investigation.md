# pCon.creator 2.22.2 — Concept Investigation

**Status:** Forensic, evidence-only. No code touched. No mapping to PDM asserted — only
"possible parallel, needs verification" flags for the downstream mapping track.

**Labeling convention used throughout:** every statement is tagged
**FACT** (explicitly documented / directly observed in a primary source),
**INFERENCE** (logically derived from FACTs, not itself written down anywhere), or
**UNKNOWN** (insufficient evidence either way).

---

## 0. Sources actually used

### 0.1 The manual — version caveat (read this before anything else)

- **Requested:** pCon.creator **2.22.2** manual.
- **Searched locally first:** `Glob`/`Grep` across the whole repo for `creator`, `pcon*manual`,
  and the literal strings `2.22.2` / `pCon.creator` / `pCon Creator`. **FACT:** no pCon.creator
  manual, and no hit on version `2.22.2`, exists anywhere under
  `C:\01 Projects\mk_product_workbench` (the only `2.22.2`-adjacent hit was an unrelated
  `AN-2017-01_PriceLists_DataCreation-EN.md` reference, not a manual).
- **Web search** (`docs.pcon-solutions.com`) returned manual PDFs for pCon.creator **2.21.0**
  and **2.22.1**, plus System Requirements documents explicitly labelled **2.22.2**
  (`pCon.creator_2.22.2_System_Requirements_EN.pdf`, dated 2026‑08‑04). **No manual PDF
  filename containing the exact string `2.22.2` was found or returned by search.**
- I fetched `https://docs.pcon-solutions.com/pCon/creator/release/2.22.1/pCon.creator_2.22.1_Manual_EN.pdf`.
  The PDF's own cover/imprint pages read **"Manual pCon.creator 2.22"**, copyright **2003‑2026
  EasternGraphics**, stamped **Version 2.22.0.125, January 2026** — i.e. this is a *2.22-line*
  manual (minor version 2.22.0), served from the `2.22.1` release path, not a build stamped
  `2.22.2`.
  - **CAVEAT (explicit, per task instructions):** the manual actually used is the closest
    available official pCon.creator 2.22-series documentation (build 2.22.0.125), **not**
    confirmed to be a 2.22.2-specific manual. EasternGraphics documentation practice appears
    to keep one manual per minor line (`2.22`) and only version-stamp System Requirements
    docs per patch (`2.22.2`). Whether the *manual content itself* changed between 2.22.0 and
    2.22.2 is **UNKNOWN** — no changelog was located. Any downstream work that assumes a
    2.22.2-specific behavior not present in this manual must re-verify against the running
    2.22.2 application.
  - Source URL used:
    `docs.pcon-solutions.com/pCon/creator/release/2.22.1/pCon.creator_2.22.1_Manual_EN.pdf`
    (referred to below simply as **"the manual"**), all page numbers below are manual page
    numbers.

### 0.2 Local reference material read for orientation (already-existing repo knowledge, not re-derived here)

- `docs/pcon_reference/README.md`, `Architecture.md`, `OCDTables.md`, `Relationships.md`,
  `VariantConditions.md`, `BuilderTableMapping.md` (skimmed as pointed to in the task; this
  material documents the **PDM → OCD/MDB generator** side, which is a *different* direction
  than "what pCon.creator's own manual documents" — see §6 for how the two relate).
- `docs/PDM_MDB_Engineering/02_PDM_Data_Model.md`, `03_Engineering_Object_Mapping.md` — read
  only to identify what PDM-side concepts already exist, so this document can flag possible
  parallels without asserting them.
- `docs/pcon_reference/ocd_4.3_en.md`, `xocd_4.3.2_en.md`, `odb_2.4_en.md`, `ofml_20r3_en.md`,
  `ofml_glossary_1.1_en.md`, `property_interface_2.10_en.md`, `article_interface_1.4_en.md`,
  `docs/Engineering_Handbook/06_OFML.md`, `07_OCD.md`, `08_ODB.md`, `09_OAP.md`, `10_Metatype.md`,
  `15_File_Formats.md`, `16_Configuration.md`, `19_Glossary.md` were **available and listed**
  in the task; given the manual itself turned out to be extremely explicit and field-level for
  every concept in scope (§2), these were used only as secondary cross-checks for
  terminology consistency (OCD/OFML naming), not as primary sources for concept definitions —
  the manual is the primary source per the task's Step 1/2 instructions.

### 0.3 What was NOT found anywhere

- **FACT:** the term **"MDF"** does not appear in the pCon.creator 2.22 manual's table of
  contents, in any of the sections read (Overview, User interface, Main functions, Datasheet
  functions, Commercial data development §5 in full incl. all Relations/Constraints/Article
  encoding subsections, Import of commercial data §10 in full field-by-field, Import of catalog
  data §11 in full, Management of registration data §8 incl. release dataset / data containers).
- **FACT:** the only "MDF" hits anywhere in the `mk_product_workbench` repo are unrelated —
  SQL Server `.MDF`/`.LDF` database files in the legacy PDM/DPS export pipeline
  (`docs/Legacy_PDM_Business_Logic/22_Export.md`, `25_Common_SQL.md`, Index files). This is
  Microsoft SQL Server's own file extension, unconnected to pCon/OFML.
- See **§5 "MDF" caveat** and **file 09** for the full treatment — this is the single most
  important finding for the downstream mapping task and it is flagged loudly there.

---

## 1. Article

- **What the docs say (FACT):** "Dialog Article master" (manual §5.3.6, p.86) — the article
  record has fields: `Article code` (**"contains the base article number"**), `Commercial
  product line`, `Type`, `Order unit`, `Discountable`, `Short-text-block`, `Long-text-block`,
  `Relation object`, `Code scheme`, `Export filter`, `OFML type`, `ODB manufacturer`, `ODB
  product line`, `ODB name`, `ODB parameters`.
- **Article types (FACT, manual p.87):** `Configurable` ("The article has configurable
  properties") vs. `Primitive` ("The article cannot be configured").
- **Representation (FACT):** OCD import table `Article` / file `ocd_article.csv` (manual
  p.373): key field `ArticleID` (Char 80, "Base article number"), plus `ArticleType` (`C`
  configurable / `P` plain), `ManufacturerID`, `SeriesID`, `ShortTextID`, `LongTextID`,
  `RelObjID`, `FastSupply`, `Discountable`, `OrderUnit`, `SchemeID`. In the internal MDB, this
  is `tCOMd_Article` (local reference doc `docs/pcon_reference/OCDTables.md`, cross-checked —
  **FACT** per that doc, table `com_ArticleID`).
- **Documented vs. inferred:** FACT — this is a fully documented dialog + fully documented
  import table with field-level types/lengths/obligations.
- **Possible PDM parallel (flag only, unverified):** PDM's `Product`/`Item` concept
  (`docs/Legacy_PDM_Business_Logic/05_Products.md`, `06_Articles.md`) looks structurally
  similar — "base article number" plausibly parallels a PDM base Product/Item code — but the
  PDM baseline distinguishes Product vs. Item vs. ProductRange in ways this document does not
  verify against pCon's single "Article" concept. **Needs verification by the mapping task.**
- **New MK Workbench concept needed?** Likely yes — an "Article" entity distinct from
  whatever PDM entity it maps from, since pCon.creator's Article carries pCon-specific fields
  (OFML type, ODB manufacturer/product line/name/parameters, code scheme) that have no
  PDM equivalent observed in `docs/PDM_MDB_Engineering/02_PDM_Data_Model.md` (which explicitly
  lists "Geometry / 3D / CAD data" and "OFML type from PDM" as **gaps**).

## 2. Base Article

- **What the docs say (FACT):** the manual does not use the literal phrase "base article" as
  a named dialog concept; it uses **"base article number"** (the value of the `Article code`
  field, manual p.86) and **"the current base article number"** as the variable `$BAN` usable
  in relation code (manual §5.3.11.1, p.110: *"With the help of this variable the current base
  article number can be evaluated in expressions."*).
- **Representation (FACT):** `ArticleID` in `ocd_article.csv` (manual p.373) — described
  explicitly as "Base article number". Also reused as the key in `ocd_artbase.csv` (`ArtBase`
  table, manual p.374, field `ArticleID` = "Article number") and in `ocd_price.csv`
  (`ArticleID` = "(Base) article number", manual p.379).
- **Relationship to "final article number" (FACT, manual §5.3.12, p.129):** *"A codification
  scheme defines how the final article number will be built from the base article number and
  the so-called variant code, which specifies the configuration of the article."* I.e.
  **Base Article Number + Variant Code → Final Article Number**, via a named `CodeScheme`
  (`SchemeID` field on the article, `ocd_codescheme.csv` table, manual pp.129, 387‑388).
- **Documented vs. inferred:** FACT for the base-article-number ↔ final-article-number
  relationship; the label "Base Article" itself as a first-class named concept is
  **INFERENCE** from the manual's field-level usage (the manual never gives it a dialog of
  its own — it's a property of `Article`, not a separate object type in the UI).
- **Possible PDM parallel (flag only):** looks structurally like PDM's `Product` (immutable
  base) vs. `Item` (a specific configured/orderable variant) split described in
  `docs/Legacy_PDM_Business_Logic/05_Products.md` / `06_Articles.md`. **Needs verification** —
  in particular whether PDM's Product↔Item split is 1:1 with pCon's
  BaseArticle↔FinalArticleNumber split, or whether pCon's "final article number" is closer to
  PDM's SKU/order-code concept (`docs/SKU_Config_Decode_Findings.md` exists locally and looks
  relevant to that question but was not read in depth here — out of scope for this pass).
- **New MK Workbench concept needed?** Possibly not as a separate entity — likely expressible
  as a field/derivation on whatever Article entity is created (§1), following the manual's own
  modeling (no separate dialog/table for "Base Article").

## 3. Variant / Configuration

- **What the docs say (FACT):** "the so-called variant code, which specifies the configuration
  of the article" (manual p.129). Variant conditions (`com_VariantCondition`, referred to in
  manual as `$VARCOND`) are the mechanism that ties a **price** or **packaging entry** to a
  specific option/property combination (manual §5.3.11.8 "Pricing relations", p.125; §5.3.11.9
  "Packaging relations", p.126). Example (FACT, verbatim from manual p.125):
  ```
  $VARCOND = 'PG1_0800' IF PG = 'PG1' AND WIDTH = 800,
  $VARCOND = 'PG2_1000' IF PG = 'PG2' AND WIDTH = 1000
  ```
- **Representation (FACT):** `Variantcondition` field, Char 80, on the `Price` table
  (`ocd_price.csv`, manual p.379) and on the `Packaging` table (`ocd_packaging.csv`,
  `Variantcondition` Char 90, manual p.390). In the XCF catalog format there is also a
  separate, apparently distinct, `Variant key` concept (`variant.csv`, `Variant` table, manual
  p.423) with a field `Variant codes` described as *"dependent on the sales product data. It
  may contain the variant code or the final article code"* — i.e. the manual itself is not
  fully crisp about whether "variant code" (pricing/packaging activation string) and "variant
  key" (catalog entry identity) are the same string in all cases. **UNKNOWN** whether these
  are the same value or two related-but-distinct strings; the manual's own wording ("may
  contain… or…") suggests they can vary by implementation.
- **Local reference cross-check (FACT, already in repo, not re-derived):**
  `docs/pcon_reference/VariantConditions.md` independently confirms, from the PDM/DPS source
  side: *"PDM has zero columns named `*VariantCondition*` — there is no raw
  variant-condition table in PDM. It is a derived OFML/OCD construct, computed at export time
  from option order codes + the product/range order-code format rules."* This is consistent
  with (does not contradict) the manual's description of `$VARCOND` as an assigned/computed
  runtime variable, not a stored PDM field.
- **Possible PDM parallel (flag only):** PDM's `Item`/order-code/`OptionValue.OrderCodeValue`
  concept (per `docs/PDM_MDB_Engineering/02_PDM_Data_Model.md` and
  `docs/pcon_reference/VariantConditions.md`) is the **raw material** consumed to *compose*
  a variant condition string — but the composed string itself has no PDM-side equivalent.
  **Needs verification**: whether MK Workbench should treat "variant condition" as a
  generation-time derived artifact (as the PDM-MDB generator docs already assume) or attempt
  to store/round-trip it.
- **New MK Workbench concept needed?** Yes for the *generation* of variant condition strings
  (already anticipated by the existing PDM_MDB_Engineering docs — this is not new information,
  just confirmation from the pCon side that the target format's semantics match what was
  already inferred).

## 4. Article Number / Configuration Code

- Covered above in §2 and §3. Restated crisply (**FACT**, manual §5.3.12 pp.129 and its
  sub-fields):
  - **Article code** = base article number (on the Article record).
  - **Variant code** = the configuration-dependent suffix, generated per a **Code scheme**
    (`CodeScheme` table, manual p.387‑388) which defines: `VarCodeSep` (separator between
    base number and variant code), `ValueSep` (separator between property values within the
    variant code), `Visibility` (`0` = only current valid/visible properties, `1` = all
    configurable properties), `InVisibleChar`/`UnselectChar` (placeholder characters),
    `Trim`, multi-option separators/brackets (`MO_Sep`, `MO_Bracket`).
  - **Final article number** = Article code + `VarCodeSep` + variant code, per the active
    scheme.
- Value-combination-table-driven code schemes are also supported since OCD 4.0 (manual p.119:
  *"value combination tables can be used in user defined article code schemes... no addtional
  [sic] relation is required"*).
- **Documented vs. inferred:** FACT, fully field-level documented.
- **Possible PDM parallel (flag only):** SKU/order-code decode work already exists locally at
  `docs/SKU_Config_Decode_Findings.md` — this looks like the natural counterpart to verify
  against, but was not opened in this pass (task scope was pCon-side only).
- **New MK Workbench concept needed?** A "Code Scheme" concept (separators, visibility mode,
  placeholder chars) does not appear to have any documented PDM equivalent in the baseline —
  likely new.

## 5. Properties

- **What the docs say (FACT, manual §5.3.8.1, pp.101‑104):** Properties live inside **Property
  classes** (a property class is a named, ordered group of properties, manual §5.3.8 p.101 —
  name must be "a valid OFML identifier"). Property fields: `Position`, `Name` (unique,
  language-independent, OFML-identifier rules), `Type` (`character`, `number`, `length`,
  `text` — manual p.103), `Usage`/scope (`Configuration`, `Relation`, `Graphic`, `Display` —
  manual p.104), `Relation object`, `Text block`, `Print settings` (`Standard`, `L1:
  <Value>`, `L1: <Property>`, `L1: suppress`, `no text`), `#tot.`/`#post` (total/decimal digit
  counts), `EA position` (digit position within the article-number coding scheme
  `EAPos`), `Obligatory`, `Add values`, `Restrict.` (restrictable in constraints), `Multivalued`
  (currently only for scope `Relation`; **FACT**, manual p.102: *"Configurable multivalued
  properties are currently not supported in OFML runtime applications"*).
- **Important documented caveat (FACT, manual p.103):** *"OCD does not support optional
  numeric properties. Properties which are of numeric type are always mandatory at runtime
  regardless if the field 'Obligatory' is true or false."*
- **Representation (FACT):** `Property` table / `ocd_property.csv` (manual p.376‑377):
  `PropertyClass`, `PropertyName` (composite key), `Position`, `TextID`, `RelObjID`, `Type`,
  `Digits`, `DecDigits`, `Obligatory`, `AddValues`, `Restrictable`, `Multioption`, `Scope`,
  `TxtControl`, `HintTextID`.
- **Possible PDM parallel (flag only):** PDM's `Attribute` concept
  (`docs/Legacy_PDM_Business_Logic/07_Attributes.md`) is the obvious candidate; PDM's
  `AttributeValue.Property`/`.Value` shape (per `docs/PDM_MDB_Engineering/02_PDM_Data_Model.md`)
  already produces rows keyed by `(property, value)`, which the existing PDM→MDB generator
  docs (`docs/PDM_MDB_Engineering/03_Engineering_Object_Mapping.md`) map onto
  `tCOMd_Property`/`tCOMd_PropValue`. That existing mapping is **not re-derived here** — it is
  pre-existing analysis. What this document adds is the *manual's own* definition of scope
  (`Configuration`/`Relation`/`Graphic`/`Display`), obligatory-numeric rule, and multivalued
  restriction, which the existing PDM-side docs do not appear to discuss (flagged there as
  `UNKNOWN`/gap: *"Data type / units — UNKNOWN"*). **Needs verification**: does PDM's
  Attribute model have anything corresponding to the four `Usage` scopes?
- **New MK Workbench concept needed?** Likely yes for the `Usage`/scope enum and the
  `Restrictable`/`Multioption` flags — the existing PDM_MDB_Engineering mapping table
  explicitly lists "Data type / units — UNKNOWN" as a gap on the `Property` row, consistent
  with this.

## 6. Property Values

- **What the docs say (FACT, manual §5.3.8.2, pp.105‑106):** a property's value list is a set
  of individual values and/or intervals: `Position`, `Default` (suggestion value),
  `Op. from`/`Value from`/`Op. to`/`Value to` (interval operators+bounds), `Raster` (step size
  within an interval), `Relation object`, `Text block`, `no text`, `Export filter`, `Valid
  from`/`Valid to` (**requires OCD 4.2**, manual p.105). **FACT:** *"The value `VOID` is
  reserved and thus not permitted."* **FACT:** *"only one interval is allowed to be visible on
  the property at runtime... assigning several intervals[,] this has to be assured by
  appropriate preconditions excluding each other."*
- **Representation (FACT):** `PropertyValue` table / `ocd_propertyvalue.csv` (manual p.378):
  composite key `(PropertyClass, PropertyName, OpFrom, ValueFrom, OpTo, ValueTo, Raster)`,
  plus `Position`, `TextID`, `RelObjID`, `IsDefault`, `SuppressTxt`.
- **Possible PDM parallel (flag only):** PDM's `Option Values` (`docs/Legacy_PDM_Business_Logic/10_Option_Values.md`) and/or attribute value rows. **Needs verification** whether PDM
  models value *ranges/intervals* at all, since the manual's interval mechanism (`Op.
  from`/`Op. to`/`Raster`) looks materially richer than a flat discrete value list.
- **New MK Workbench concept needed?** Likely yes for interval-typed property values — no
  PDM interval concept was surfaced in the PDM baseline docs skimmed here.

## 7. Options / Option Values

- **What the docs say (FACT):** the manual's **Commercial data development** module does not
  give "Option" a separate named dialog distinct from `Property`/`Property value` — options
  are modeled as properties with `Usage` scope, per §5 above. There is no `Dialog Option` or
  `Dialog Option class` in the table of contents (manual pp.5‑11, checked in full). The word
  "Option" appears in the manual mainly in the context of value combination tables and the
  `Configuration` relation domain (*"Relations of this domain are evaluated during generation
  as well as during each configuration step. They define the configuration options"* —
  manual p.108, emphasis on "options" as a plain-English word, not a distinct schema object).
- **Contrast with local PDM/OCD generator docs (FACT, already in repo):**
  `docs/pcon_reference/OCDTables.md` and `docs/PDM_MDB_Engineering/03_Engineering_Object_Mapping.md`
  both discuss a distinct `tCOMd_Option` / `tCOMd_OptionValue` pair as part of the **OCD table
  schema** (not the pCon.creator manual) — and flag it as a **write-coverage GAP**: *"Option —
  tCOMd_Option ... Not written — no tCOMd_Option insert in create_handbook_base... GAP.
  Snapshot reads tCOMd_Option but nothing writes it."* This is pre-existing analysis, not
  re-derived here.
- **Reconciling the two (INFERENCE):** the pCon.creator *manual* does not surface
  `tCOMd_Option`/`tCOMd_OptionValue` as end-user dialogs — they may be a lower-level OCD schema
  detail that pCon.creator's UI abstracts away entirely behind `Property`/`Usage=Configuration`.
  **UNKNOWN** whether pCon.creator internally ever writes those two tables, or whether they are
  vestigial/legacy OCD tables not exercised by the current UI at all. This is exactly the kind
  of discrepancy the downstream mapping task needs to resolve before assuming PDM `Option` →
  pCon `tCOMd_Option` is a valid target.
- **Possible PDM parallel (flag only):** PDM's `Options`/`Option Values`
  (`docs/Legacy_PDM_Business_Logic/09_Options.md`, `10_Option_Values.md`). **Needs
  verification**, and the open question above (does pCon.creator ever populate
  `tCOMd_Option`?) should be resolved first.
- **New MK Workbench concept needed?** UNKNOWN pending the above.

## 8. Classes

- **What the docs say (FACT):** **Property classes** (manual §5.3.8, p.101) group properties;
  a property class name must be a valid OFML identifier. **Article classes** are the
  assignment of a property class to an article (manual §5.3.6.1, p.87: *"This tab allows you
  to assign different property classes to an article... A property class can only be assigned
  once to an article"*), with an optional `Relation object` bound at the class level ("of the
  'action' type") and an optional `Text block` used to group properties in the property editor
  at runtime. **Property groups** (manual §5.3.9, p.107) are a separate, purely
  presentation-layer re-grouping/re-ordering of properties across classes for a
  "sales-oriented view" — explicitly **not** a place to define new properties (*"It is not
  possible to define new properties in property groups!"*) and require OCD 4.3.0+ export
  format to be exported at all.
- **Representation (FACT):** `PropertyClass` table / `ocd_propertyclass.csv` (manual p.375):
  `ArticleID`, `Position`, `Name`, `TextID`, `RelObjID`.
- **Possible PDM parallel (flag only):** unclear — PDM's Attribute grouping concept is
  **flagged as a gap already** in the existing analysis: `docs/PDM_MDB_Engineering/02_PDM_Data_Model.md`
  states *"Property classes — class_name is read... but no analyzed service was observed
  populating it... effective value appears empty. UNKNOWN / likely gap"* and
  `03_Engineering_Object_Mapping.md` states *"class_name on PDM rows is generally empty; class
  names are inferred from the property text, not sourced."* This document's contribution is
  confirming, from the pCon.creator manual side, that **Property Class** is a first-class,
  fully specified, mandatory-to-populate concept on the target side (an article's properties
  cannot be organized without one) — meaning the existing PDM-side gap is a real gap against a
  real, well-specified requirement, not a documentation oversight on the PDM side.
- **New MK Workbench concept needed?** Yes, very likely — "Property Class" (and possibly
  "Property Group") appear to need an explicit MK Workbench concept, since the PDM side
  currently has no populated source for it (per the existing gap analysis).

## 9. Relation Objects

- **What the docs say (FACT, manual §5.3.10, p.108):** *"Relational objects group one or
  several relations. The type of using the relations is determined here."* Fields:
  `Relation object` (unique name), `Pos` (order), `Domain`, `Type`, `Relation` (reference to
  the actual relation logic by name).
- **Domain (FACT, manual p.108) — four values:**
  | Domain | Meaning (verbatim, condensed) |
  |---|---|
  | `Configuration` | evaluated during generation and each configuration step; defines configuration options |
  | `Pricing` | evaluated to calculate price for current configuration; relations must be type `Action` |
  | `Packaging` | evaluated to determine packaging info; relations must be type `Action` |
  | `Taxation` | evaluated while determining tax; relations must be type `Action`; can change tax category depending on configuration |
- **Type (FACT, manual p.109) — six values**, see §10 (Relations) below — `Precondition`,
  `Select condition`, `Action`, `Constraint`, `Reaction`, `Post-Reaction`.
- **Representation (FACT):** `RelationObj` table / `ocd_relationobj.csv` (manual p.383):
  `RelObjID` (numeric, >0), `Position`, `RelName`, `Type` (`1`‑`5` for the five relation types
  — note the manual's UI lists six named types on p.109 but the *table* enumerates only five
  codes on p.383, omitting a distinct code for `Select condition` vs `Precondition`; **UNKNOWN**
  whether `Select condition` shares code `1` with `Precondition` or is not exportable —
  not resolved by the manual text read), `Domain` (`C`=Configuration, `P`=Pricing,
  `PCKG`=Packaging; note **taxation domain has no code letter shown in this table** — manual
  p.383 lists only C/P/PCKG; **UNKNOWN**/possible gap, or taxation relations may not need a
  `RelationObj` domain code distinct from `Action`-typed configuration relations — not resolved
  here).
- **Possible PDM parallel (flag only):** none obvious in the PDM baseline surveyed
  (`docs/Legacy_PDM_Business_Logic/` has no "relation object" equivalent visible from the
  index files skimmed). **Needs verification** — this may be entirely new territory for MK
  Workbench, closest to PDM's `Dependencies`/`Exclusions` machinery conceptually but not
  structurally.
- **New MK Workbench concept needed?** Yes, very likely.

## 10. Relations (and their five/six sub-types)

- **What the docs say (FACT, manual §5.3.11, p.110 onward — this is the largest, most
  detailed section of the commercial-data chapter, pp.110‑129):**
  - A **Relation** = `Relation` (unique name) + `Relation code` (the logic, in a
    product-line-specific coding language "dependent on the coding language which has been
    selected for each product line").
  - **Variables & constants (FACT p.110):** `FALSE` (logical false), `$BAN` (current base
    article number).
  - **Operators / Builtin functions (FACT, referenced pp.111‑115, not itself transcribed in
    full field-by-field here since it is a language reference, not a concept list — flagged
    as read but not exhaustively reproduced).
  - **`ABORT()` (FACT, p.116):** usable in Reactions/Post-Reactions since OCD 4.1; aborts
    relation execution at runtime under a condition, resetting article state to pre-change.
  - **Conditions (FACT, p.116):** comparisons, negations, special conditions (e.g. the
    `SPECIFIED` operator to test whether a possibly-hidden property currently has a value —
    manual example: `SPECIFIED FRONTTYPE AND FRONTTYPE = 'glass'`).
  - **Value assignments (FACT, p.117):** `=` operator; multiple assignments in one action
    comma-separated; each assignment can carry its own `IF <condition>`; assignments with the
    same condition can be grouped in curly braces since OCD 4.1.
  - **Table calls (FACT, p.118‑119):** `TABLE <TableName> (<Column>=<Variable>, ...)` — used
    inside actions (assign a value, `$SELF.` prefix), inside pricing-relation actions (assign
    `$VARCOND`), inside constraints (`Restrictions:` — check consistency / restrict value
    range / assign a value), and inside preconditions (table access must resolve to exactly one
    row or the precondition is undefined).
  - **Constraints (FACT, p.120‑124):** a distinct, more complex language construct with four
    named parts, each keyword-introduced and period-terminated:
    - `Objects:` — declares typed variables via `<Var> IS_A <PropertyClass>` (optional since
      OCD 4.0), optionally scoped further with `WHERE <Var> = <Property>`.
    - `Condition:` — optional boolean guard for when the constraint is evaluated at all.
    - `Restrictions:` — the actual property dependencies that must hold (comparisons, value
      range checks, or value-combination-table lookups) for the configuration to be
      considered valid; **FACT:** *"The OFML runtime environment ensures that the article
      cannot be ordered or that a configuration step which leads to an inconsistent state
      cannot be executed."*
    - `Inferences:` — names which properties get a value assigned or restricted by the
      Restrictions clause.
    - **FACT (p.122):** *"The constraint will not be evaluated if one of the property classes
      declared in the paragraph Objects has not been assigned to the article."* Also:
      *"Properties whose value ranges are restricted[] have to be marked as restrictable in
      the property table"* (ties back to §5's `Restrictable` field).
  - **The five (or six?) relation-object `Type` values, restated with their manual
    definitions verbatim (p.109), cross-checked against the `RelationObj` table's 5-code
    enum (p.383):**

    | Type (UI label, p.109) | Definition (verbatim, condensed) | Code in `ocd_relationobj.csv` (p.383) |
    |---|---|---|
    | Precondition | Boolean expression describing the condition under which a property or property value can be selected; if false, the property "does not exist and won't be displayed" | `1` |
    | Select condition | Boolean expression describing the condition under which the user *must* assign a value to an optional property | not separately coded (**UNKNOWN** — see caveat above) |
    | Action | Assigns values to properties; not evaluated if the property is hidden by a precondition; on property values, only executed if that value is selected | `3` |
    | Constraint | Complex language construct (see above) to check article-configuration consistency and/or assign/restrict property values; can only be assigned to relation objects used **at article level** | `4` |
    | Reaction | Assigns a value to a property, evaluated right after the user changes that property's value (if bound to a property) or once at article creation (if bound to an article); reactions are **always evaluated first**, before all other relations | `5`* |
    | Post-Reaction | Like Reaction but evaluated **last**, after all other relations | *(no distinct FACT code found — table shows 5 total codes 1‑5 for 6 named types; exact code-to-type mapping for Reaction vs Post-Reaction not fully disambiguated from the pages read)* |

    **FACT caveat, restated for emphasis:** the manual names **six** relation types in prose
    (p.109: Precondition, Select condition, Action, Constraint, Reaction, Post-Reaction) but
    the `ocd_relationobj.csv` field table (p.383) enumerates only **five** numeric codes
    (`1`‑`5`: Pre-Condition, Selection condition, Action, Constraint, Reaction). Re-reading
    p.383 the five codes actually *do* include "Selection condition" as code `2` — so the
    apparent mismatch is that **Post-Reaction has no distinct code shown on p.383**. This is
    left as **UNKNOWN**: either Post-Reaction is not independently exportable at the
    `RelationObj` level (perhaps encoded some other way, e.g. via `Position`/ordering), or the
    manual page captured is incomplete. **The downstream mapping/generation task must verify
    this against a real OCD 4.3 export or the OCD 4.3 spec (`docs/pcon_reference/ocd_4.3_en.md`)
    before assuming Post-Reaction round-trips.**
  - **Pricing relations (FACT, p.125‑126):** activate a price by assigning its
    `com_VariantCondition` string to `$VARCOND`; `$SET_PRICING_FACTOR(<VariantCondition>,
    <Factor>)` multiplies an activated price component.
  - **Packaging relations (FACT, p.126‑127):** same `$VARCOND` activation pattern for
    packaging records; `$SET_PCKG_FACTOR(<VariantCondition>, <Field>, <Factor>)` where
    `<Field>` ∈ `NETWEIGHT`, `TARAWEIGHT`, `DEPTH`, `HEIGHT`, `WIDTH`, `VOLUME`,
    `ITEMSPERUNIT`, `PACKUNITS`.
  - **Tax calculations (FACT, p.128):** `SET_TAX_CATEGORY(<tax type>, <tax category>)`,
    requires OCD 4.3.0+ export enabled.
- **Representation (FACT):** `Relation` table / `ocd_relation.csv` (manual p.384):
  `RelationName`, `BlockNr` (code block number), `CodeBlock` — **records must be sorted by
  `RelationName`, `BlockNr`** (an explicit, easy-to-violate import constraint).
- **Documented vs. inferred:** overwhelmingly **FACT** — this is the single most thoroughly
  documented mechanism in the whole manual. The Post-Reaction code ambiguity above is the one
  explicit **UNKNOWN** left in this section.
- **Possible PDM parallel (flag only):** PDM's `Dependencies`/exclusion-rule machinery
  (`product_dependencies`, `product_option_exclusion_rules` per
  `docs/PDM_MDB_Engineering/02_PDM_Data_Model.md`) is the natural candidate for
  Precondition/Constraint, and PDM pricing tables
  (`get_pricing_tables`/fabric pricing, flagged as *"not wired into build_product_payload"* in
  the same doc) for Pricing relations. **Both are explicitly flagged as unverified/gaps
  already in the existing PDM-side analysis** — this document does not resolve them, only
  confirms that the *target* side (pCon) has a rich, precisely specified language that PDM's
  side does not yet demonstrably populate. `docs/PDM_MDB_Engineering/03_Engineering_Object_Mapping.md`
  states plainly: *"Relationships — single 'contains' type only; richer OCD relations are
  UNKNOWN."* This is exactly the Precondition/Action/Constraint/Reaction/Post-Reaction
  richness this document has now made explicit on the target side.
- **New MK Workbench concept needed?** Yes, almost certainly — a relations/constraints
  authoring and storage model with at least the five-or-six typed sub-kinds above appears to
  have no PDM equivalent at all today (PDM only emits a flat `contains` graph, per the
  existing analysis).

## 11. Dependencies

- Not a separately named pCon.creator dialog/table. Per the docs (FACT), "dependency" as a
  concept is expressed entirely through the **Constraint** relation type's `Restrictions:`
  clause (§10) — i.e. pCon.creator does not model "a dependency" as a first-class object;
  it models "a constraint that restricts a property's value range or existence given other
  properties' values."
- **Possible PDM parallel (flag only):** PDM's explicit `product_dependencies` /
  `product_option_exclusion_rules` engineering models (named as first-class objects,
  per `docs/PDM_MDB_Engineering/02_PDM_Data_Model.md`) look like a **more explicit,
  first-class version** of what pCon folds into Constraint relation code. **Needs
  verification**: whether MK Workbench should keep Dependencies as an explicit
  first-class object (as PDM does) and *generate* Constraint relation code from it (as
  the existing PDM→MDB generator architecture already implies it should — see
  `docs/pcon_reference/README.md`'s stated purpose: *"Enable future implementation of the
  PCon Generator"*), which this document's findings support rather than contradict.
- **New MK Workbench concept needed?** No new concept — this reinforces (does not
  contradict) the already-planned direction in `docs/pcon_reference/GeneratorArchitecture.md`
  of generating Constraint-relation code from PDM's existing Dependency/Exclusion models.

## 12. Article Restrictions

- **What the docs say (FACT):** "Restrictable" is a per-property boolean field (§5), and
  "Restrictions:" is a named clause inside a Constraint (§10) — the manual uses "restriction"
  only in these two senses; there is no separate "Article Restriction" object. `Article
  properties` (manual §5.3.6.3, p.90) is the closest distinct dialog: it lets an article
  **restrict** the property-value list of a property-class property to a subset valid for
  that specific article, or fix it to a constant value. Key rule (**FACT**, p.90): *"Article
  properties cannot be used to define additional article specific properties... only be used
  to define it as a fixed attribute with a constant value or to restrict its property value
  list."*
- **Representation (FACT):** the `ArtBase` table (`ocd_artbase.csv`, manual p.374):
  `ArticleID`, `PropertyClass`, `PropertyName`, `PropertyValue` — this is literally named
  "article base" in OCD/MDB terms (matches `tCOMd_ArtBase` in the local
  `docs/pcon_reference/OCDTables.md`, described there as *"Article base / base configuration
  (series base)"* — **FACT**, cross-checked, consistent).
  - **Possible naming trap flagged for the mapping task:** the manual's own dialog is called
    "Article properties" (not "Article base"), but its underlying OCD table is `ArtBase`
    (`tCOMd_ArtBase`). MK Workbench documentation/terminology should not assume "Article Base"
    (§2 above, base article number) and "ArtBase table" (this section, fixed/restricted
    article-specific property values) are the same concept — **they are two different things
    that happen to share the word "base."** This is an **explicit terminology-collision
    caveat**, not asserted anywhere in the source docs but is an **INFERENCE** worth flagging
    because it is easy to conflate.
- **Possible PDM parallel (flag only):** unclear; PDM's per-Item attribute overrides
  (if any) would be the natural candidate — not verified here.
- **New MK Workbench concept needed?** Likely yes, distinct from Base Article (§2).

## 13. Pricing

- **What the docs say (FACT, manual §5.3.6.2 pp.87‑89, and Pricing relations p.125‑126):**
  three price **levels**: Base-price, Upcharge, Discount (manual p.88: *"Prices are divided
  into the following price levels: Base-prices / Upcharges / Discounts"*). Fields: `Variant
  condition`, `Price`, `Currency` (a literal `%` value is allowed "to generate a relative
  price"), `Type` (references the price-list Type, p.70 — not itself detailed in the pages
  read here), `Text block`, `Rounding` (references a named Rounding rule), `Valid
  from`/`Valid to`, `Rule` (calculation rule — `1` "in relation to the base price" or `2` "in
  relation to the price accumulated during price calculation"; **FACT p.88:** *"No
  calculation rules are supported for base prices and upcharges. For discounts a rule has to
  be specified."*).
- **Index prices (FACT, p.89):** an alternative, non-standard, explicitly discouraged
  mechanism — abstract integer price index looked up in an *external* table; **FACT verbatim
  caveat**: *"Currently it is not recommended to use index prices in standard data creation
  and distribution processes... Index prices and the mentioned external tables are not part
  of the OCD specification... just a special extension to realize special requirements of the
  German living furniture market."*
- **Representation (FACT):** `Price` table / `ocd_price.csv` (manual p.379): `ArticleID`,
  `Variantcondition`, `Type` (`S` sales / `P` purchase), `Level` (`B` base / `X` extra-charge
  / `D` discount), `Rule`, `TextID`, `PriceValue`, `FixValue` (bool: fixed amount vs.
  percentage), `Currency`, `DateFrom`, `DateTo`, `ScaleQuantity` (**FACT: explicitly not
  evaluated by OFML runtime in OCD 4.0 stage 1 — "won't be imported"**), `RoundingID`. Also
  `Rounding` table / `ocd_rounding.csv` (p.381: `ID`, `Number`, `Minimum`, `Maximum`, `Type`
  [`DOWN`/`UP`/`COM` commercial/`ECOM` banker's], `Precision`, `AddBefore`, `AddAfter`) and tax
  tables `TaxScheme`/`ArticleTaxes` (p.382).
- **Possible PDM parallel (flag only):** local doc `docs/pcon_reference/PriceGeneration.md`
  (not opened in this pass, but its existence and the README's summary — *"Pricing and
  variant conditions are item-level generation-time concerns, deliberately kept out of the
  Builder Table"* — is consistent with the manual's own framing of pricing as
  configuration/variant-condition-driven rather than stored per Product). **Needs
  verification** by whoever works `PriceGeneration.md` directly against this section.
- **New MK Workbench concept needed?** Rounding rules and the Base/Upcharge/Discount
  three-level split with calculation `Rule` do not appear to have a documented PDM
  equivalent surfaced in this pass — flag for verification.

## 14. Text

- **What the docs say (FACT):** **Text blocks** (`Dialog Text blocks`, manual §5.3.7, p.95;
  fields not individually enumerated in the pages read but referenced throughout as the
  labeling mechanism for articles, property classes, properties, property values, and prices)
  are language-keyed collections of lines, referenced everywhere by a `TextID`/`*TextID`
  foreign-key-like string field (e.g. `ShortTextID`/`LongTextID` on Article, `TextID` on
  PropertyClass/Property/PropertyValue/Price). **Representation (FACT):** description tables
  (manual p.385‑386) — `ArtShortText` (`ocd_artshorttext.csv`), `ArtLongText`
  (`ocd_artlongtext.csv`), `PropClassText`, `PropertyText`, `PropHintText`, `PropValueText`,
  `PriceText`, `UserMessage` — all sharing the same field shape: `TextID` (Char 80),
  `Language` (Char 2, ISO-639), `LineNr`, `LineFormat` (**FACT: not evaluated by OFML runtime
  in OCD 4.0 stage 1, not imported**), `Textline`. **FACT:** records must be sorted by
  `TextID, Language, LineNr`.
- **Possible PDM parallel (flag only):** PDM's `Translations`/`Descriptions`
  (`docs/Legacy_PDM_Business_Logic/12_Translations.md`, `13_Descriptions.md`) look like the
  obvious source. **Needs verification.**
- **New MK Workbench concept needed?** Probably not conceptually new (translation/localized
  text is a well-understood pattern) but the specific `TextID` indirection + multi-line +
  per-language-line-number storage shape should be checked against whatever PDM already has.

## 15. MDF Export / MDF Import

- **See file `09_mdf_export_import_requirements.md` for the full treatment.** Summary
  (**FACT**, restated from §0.3): the string "MDF" does not occur anywhere in the pCon.creator
  2.22 manual (all sections read: full table of contents, all of Commercial data development
  §5, all of Import of commercial data §10, all of Import of catalog data §11, Management of
  registration data §8 including release dataset/data containers). The manual's own vocabulary
  for the relevant export/import operations is: **OCD** (CSV table set — "Import of commercial
  data", §10; and "Export to OFML" dialog, §5.3.21, producing OFML data containers per §8.3.2),
  **XOCD** (an OCD variant, referenced in table-of-contents only, not read in depth in this
  pass), **XCF** (catalog exchange format — "Import of catalog data", §11; also produced as a
  "supplement export" test catalog per §5.3.21.1), and the internal **MDB** (Microsoft Access
  database — this is *inferred/cross-checked* from the local `docs/pcon_reference/` material,
  not from the manual itself, which never names the file format of its "workspace" explicitly
  in the pages read). The release/distribution dataset (§8.3.2, pp.297‑300) uses **EBASE**
  databases (`pdata.ebase`, `odb.ebase`, etc.) and **ZIP containers** (`xcf.zip`, `image.zip`,
  `mat.zip`) — again, no "MDF" anywhere.
  - **UNKNOWN / open question for the mapping task:** is "MDF" (as used in the task title
    `09_mdf_export_import_requirements.md`) a misnomer/mix-up with **MDB** (the Access
    database format this repo's existing `docs/pcon_reference/` material centers on), or a
    reference to some other EasternGraphics artifact (e.g. a "Model/Metadata Description
    Format") not covered by the 2.22 manual sections read? This document does **not** guess —
    it flags the discrepancy and defers resolution to whoever commissioned the "MDF" framing.

## 16. MDB-related concepts

- **What the local reference material already establishes (FACT, pre-existing, not
  re-derived):** `pcr_data_com_ocd.mdb` is the Access-database package format that the
  existing PDM→OCD generator writes to (`docs/pcon_reference/README.md`,
  `docs/pcon_reference/Architecture.md`, `docs/pcon_reference/OCDTables.md`). The manual's own
  chapter numbering (§X "Import of commercial data", §XI "Import of catalog data") describes
  the *table/CSV* shape of that data, consistent with what would be loaded into such an MDB,
  but the manual sections read here **do not themselves say "MDB"** in those chapters — the
  MDB-specific framing is entirely the local `docs/pcon_reference/` analysis, which this
  document treats as a given per task instructions (not re-derived).
- **What this document adds (FACT):** the manual's own "workspace" and "directory structures
  in data creation projects" section (manual §1.5, p.21 — table of contents only, not read in
  full in this pass) is the likely bridge between the manual's CSV-table-level description and
  the local docs' MDB-level description; **UNKNOWN** — not verified in this pass, flagged for
  a follow-up read if the mapping task needs the exact workspace→MDB mechanics.
