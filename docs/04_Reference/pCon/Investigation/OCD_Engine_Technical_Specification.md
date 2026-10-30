# Independent OCD Configuration / SKU / OBX Engine — Technical Specification

**Status:** Phase 1 complete pending your review (revision 2: updated with the Dalby reference OBX evidence). **No application code has been written or changed.**
**Date:** 2026-10-30
**Evidence report (detail, per-article data, reproducible script):** [Dalby_OBX_Forensic_Analysis.md](Dalby_OBX_Forensic_Analysis.md) and `evidence/`.

Labels: **[C]** Confirmed (read in data/spec or reproduced by script) · **[S]** Strongly supported · **[H]** Hypothesis · **[U]** Unknown.

---

## 0. What changed since revision 1

| Revision 1 statement | Now |
|---|---|
| "56 articles cannot be reconciled with 14 × 4" **[U]** | **Resolved [C]:** 56 = 14 Top_Finish × 2 Frame_Finish × 2 base articles (NODLE150 and NODLE160, 28 each). |
| The reference OBX is a selected subset | **[S]** User-ticked cartesian selection (Snapper generator design), unrecorded; the OCD data permit 30 Top_Finish values, all priced and valid. Reason for the 14 stays **[U]**. |
| `final`/`varcode` derivation reproduces the example **[S]** | **[C]** `final` = scheme token walk, 3,594/3,594 articles (Dalby 1,242 + Lino 2,352). `varcode` suffix rule corrected (see §3.4); my earlier "final minus base" shortcut is **refuted**. |
| 869 + 43 + 244 present in raw data **[C]** | Extended **[C]**: 1,242/1,242 Dalby totals reproduced from `ocd_price` using the OBX's own price date and currency. |
| `addStateCode`/`geometryChecksum` probably not derivable **[H]** | **[S]** runtime-dependent (OFML/geometry), characterised in §3.6. |
| Dalby OBX unavailable | Available: 26 OBX files; **no Dalby export from 8.15 or PRO** is among them. |

All other revision-1 findings (relation-text syntax, NODLE150 structure, price windows) are retained and were re-confirmed.

---

## 1. Evidence base

| Source | Used for |
|---|---|
| `docs/04_Reference/pCon/Specifications/ocd_4.3_en.md` (§2.12–2.17, §3, App. A–B) | relation types/domains, language semantics |
| Real Dalby OCD CSVs + `pdata.ocd_*.inp_descr` (`…\hmx\dalby\ANY\1\db\`), Dalby/Lino OAM, Lino scheme | schemas, relations, prices, schemes |
| `C:\Users\siaoca\Downloads\Dalby_OBX_Files` (26 OBX, 2 CSV, 1 XLSX) | golden examples (see report §1) |
| `C:\Users\siaoca\Desktop\MK_OFML_Testsuite` (Snapper generator; read only) | export-driver investigation |
| `docs/02_Domain/Permutation/Permutation_Gap_Analysis.md` | known encoding gaps |
| `docs/04_Reference/pCon/SDK_Article_OBX_Generator.md`, `tools/pcon_obx_plugin/` (read only) | runtime-validation route |

**Not available:** a Dalby export from pCon 8.15/PRO; the selection record behind the 14 values; programs exercising constraints, multi-option properties, non-empty code-scheme flags, rounding, scale/discount prices.

---

## 2. Confirmed OCD source-data facts

### 2.1 Layout, schema, encoding
- **[C]** OCD tables in `dalby\ANY\1\db\`; `oam\` in `EURO|GBP|NOPRICE\1\oam\`. Loader must resolve program+region across both.
- **[C]** Schema comes from `pdata.ocd_<table>.inp_descr` (`field <n> <name> <type> … delim ;`). Columns used (names as in descriptors):
  `article`: article_nr, art_type, manufacturer, series, short_textnr, long_textnr, rel_obj, fast_supply, discountable, order_unit, scheme_id ·
  `artbase`: article_nr, prop_class, property, prop_value ·
  `propertyclass` (no descriptor-fixed name seen in my read; positional: article_nr; pos; class; text; relobj) — **take names from its descriptor** ·
  `property`: prop_class, property, pos_prop, prop_textnr, rel_obj, prop_type, digits, dec_digits, need_input, add_values, restrictable, multi_option, scope, txt_control, hint_text_id ·
  `propertyvalue`: prop_class, property, pos_pval, pval_textnr, rel_obj, is_default, suppress_txt, op_from, value_from, op_to, value_to, raster, date_from, date_to ·
  `relationobj`: rel_obj, position, rel_name, rel_type, rel_domain · `relation`: rel_name, rel_blocknr, rel_block ·
  `price`: article_nr, var_cond, price_type, price_level, price_rule, price_textnr, price, is_fix, currency, date_from, date_to, scale_quantity, rounding_id ·
  `codescheme`: scheme_id, scheme, varcode_sep, value_sep, visibility, invisible_char, unselect_char, trim, mo_sep, mo_bracket.
- **[C]** CRLF, `;`, quotes only where needed; numeric fields may carry a leading space (`; 1;`). Dalby files are ASCII only. The OBX files are valid UTF-8. **ISO-8859-1 for OCD CSVs remains [U]** (the repo's other ranges, not Dalby, must be checked); decode with latin-1 as the spec says, and report any byte ≥ 0x80 once so the assumption becomes testable.
- **[C]** `ocd_version`: OCD 4.2, `OCD_4`, data 1.34.7, valid 20200106–99991231; table list given. Language OCD_4 ⇒ OCD_2 semantics (`SPECIFIED` = restricted to one value, string `+`, `TRUE/FALSE`) apply, per spec App. B.
- **[C]** Relation expression = all `ocd_relation` rows for `rel_name` ordered by block number and concatenated (spec §2.16). Names are zero-padded 18-digit strings.

### 2.2 Relation syntax observed in real data (all [C])
1. `*` comment lines (`"***** …"`, `"* Incremental prices"`), also commented-out code (`"****** $ BAN IN ('1')"`).
2. Empty blocks (`""`) as spacing.
3. Trailing commas separating action statements; none after the last.
4. `+` string concatenation (`'6821=' + Access_Cutout`).
5. Duplicate literals in `IN` lists (`'NODLE440', 'NODLE440'`).
6. `$ BAN IN (...)` and `$ BAN NOT IN (...)`.
7. `(SPECIFIED Top_Finish) AND (Top_Finish IN (...))` — parenthesised, with `SPECIFIED`.
8. `SPECIFIED Access_Cutout AND Access_Cutout NOT IN ('OFT','NC')` (rel 19542) — unparenthesised mix of a special condition and a comparison.
9. **Identifier case varies**: `SPECIFIED TOP_Finish … TOP_Finish IN ('BRC')` (rel 19531) vs `Top_Finish` elsewhere. Spec App. A: keywords and property identifiers are case-insensitive; **string values are not** (`'A' < 'a'`). The lexer/evaluator must normalise identifiers only.
10. P-domain action relation attached to the *article* (`ocd_article.rel_obj = 19573`, type 3, domain P).

Only preconditions (type 1) and a P-domain action (type 3) occur in Dalby; constraints/reactions/TABLE() are **not exercised** [C].

### 2.3 NODLE150 structure (hand-reconstructed, then confirmed against 1,242 OBX articles)
- Article `NODLE150`, scheme `U…6335`, price relation 19573; artbase fixes `PLC=SE-NO-DL`; property classes `DALBY_ATTR` (73219), `DALBY_OPT` (73220).
- Properties/preconditions: `Access_Cutout` (19527) and `Cable_leg` (19528): `$ BAN IN ('NODLE300'…'NODLE630')` → FALSE for NODLE100–230 → hidden. `Frame_Finish` {OAK, WLN}, `Top_Finish` 30 values, no property precondition. `Bottom_Material_G` (19530) and `Bottom_Stright_Edge` (19536): Top_Finish-dependent; `Bottom_WFT`: no property precondition, value preconditions identical to the material/edge ones.
- Value preconditions: Top_Finish BRC/BSE/WRC/WSE → 19569 `$ BAN NOT IN ('NODLE320')`; Bottom_Material_G MDF (24 Q-values) / OAK / WLN / BRC / WRC; Bottom_Stright_Edge BSE/WSE; Cable_leg WCL → 19542.
- `scope`: Access_Cutout, Cable_leg, Frame_Finish, Top_Finish = `C`; Bottom_*, Series, TTSH, TTSZ, Table_type, PLC = `RG`.

---

## 3. What the reference OBX files establish

(Full tables and counts: forensic report.)

### 3.1 Scope of the 56 / the 14-of-30 question
- **[C]** 56 = 14 × 2 × 2. 16 Top_Finish values absent (Q01–Q05, Q07–Q12, Q54, Q74, Q77, Q83, Q84); all 30 values are valid for NODLE150, all have `6695=` price rows in GBP and EUR at 2025-10-27; none is rejected by a relation or dependency.
- **[C]** The same 14 values × 2 frames are used for every Dalby base; NODLE320 has 10 × 2 because `$ BAN NOT IN ('NODLE320')` removes BRC/BSE/WRC/WSE — an independent confirmation of that relation.
- **[S]** Driver: the OFML Testsuite *Snapper File Generator* builds `articles × ticked values` and emits `base + ofmlvarcode` only; pCon *Update* resolves the rest. Selection is manual and unrecorded. **[U]** why those 14 (they are exactly the values whose English text lacks "forbo" — an uninterpreted correlation, **not** an engine rule).
- **Design consequence:** result sets carry two independent attributes: `valid_in_ocd` and `selected_by_scope`. The engine never infers scope from a reference OBX.

### 3.2 Cascades — [C]
`Bottom_Material_G` = MDF for the 24-value Q list, = OAK/WLN/BRC/WRC for the same Top_Finish, omitted for BSE/WSE; `Bottom_Stright_Edge` = BSE/WSE only for those tops; `Bottom_WFT` = whichever of the two is visible. **0 violations in 1,242 articles.** Omitted ⇒ absent from `<features>`, `@VOID` in `propVarCode`, absent from `ofmlvarcode`, no effect on the final number. Each visible dependent property had a single valid value (a Dalby design property, not an OCD rule **[S]**). Three-valued *undefined* results never occur here (every precondition uses `SPECIFIED … AND …`) — **not exercised [U]**.

### 3.3 Final article number — [C] for the all-empty-flags subset
Walk the `scheme`: `@` consumes the next character of the base number; `Class:Property` emits the value (empty if omitted/VOID/unset); any other token is a literal. Verified on Dalby (schemes 6335 and 6336, with space literals) and Lino (6320, `@`×5). Worked example: `NODLE150` + `" "` + `""` + `""` + `WLN` + `" "` + `Q75` = `NODLE150 WLN Q75`.

### 3.4 varcode, ofmlvarcode, propVarCode — [C]
- `ofmlvarcode` = `Class.Property=Value;…` for the **flags=1 (scope C) properties that have a value**, in class/property order. [C] for Dalby and Lino; **[H]** flags=1 ⇔ scope C in general.
- `varcode` = `final + "@" + space-joined values of the ofmlvarcode properties` (3,594/3,594). In Dalby it coincides with the final's tail; in Lino it does not.
- `propVarCode`: every property, OCD order; name with `_`→`__`; `@value` with a `_` prefix if the value starts with a digit; `""` for empty; `@VOID` if the precondition is FALSE. Hidden scope-C properties (Access_Cutout/Cable_leg on NODLE1xx–2xx) are *omitted entirely*, hidden RG properties appear as `@VOID` **[C]**, reason **[H]**.

### 3.5 Pricing — [C]
Total = Σ `ocd_price` rows with article = base, `var_cond` ∈ {'' + VARCOND keys}, type `S`, OBX currency, `date_from ≤ priceDate ≤ date_to`, scale 1 — **1,242/1,242**. Component list = one entry per matching surcharge row, base first; values are **percentages of the total** (`currency='%'`, 34 significant digits); a key without row ⇒ no component; base-only article ⇒ empty `priceComponents`. `purchase` = `sale` (no `P` rows). Untested: rounding, percent/scale/discount prices, joker article, price types other than S, VARCOND keys 6821/7030 (all reference articles use Access_Cutout=NC, Cable_leg=WSL).

### 3.6 Fields the engine cannot derive
`geometryChecksum` (runtime/geometry; deterministic per configuration, 26 distinct values per 28 configurations), `addStateCode` (`OiOdbPlElement`, `ChildProps`: per **base article**, constant across configurations, OFML symbols like `DALBY_TTSHa_Circular`), `appData` (per-instance CAD handle). Absent from all six Lino 8.15 files: `addStateCode`, `metaType`. `catalogInfo`/`pdInfo`/`metaType` come from package registration/OAM, not OCD. Classification: **runtime-dependent / unsupported for independent generation**; generator emits an *input-style* OBX (`base` + `ofmlvarcode`, as the Snapper does) as the realistic target; whether pCon accepts an output-style OBX without these fields is **[U]**.

---

## 4. Architecture

Proposed package (unchanged names, now with contracts): `services/ocd_engine/{loader,domain,relations,configuration,encoding,pricing,obx,diagnostics,reference}`; tests in `tests/ocd_engine/`. Nothing imports `services.article_obx`, `legacy_*`, `maintenance_*`, `*varcond*`, `pdm_*`, snapshot, repository or `ui`. Pure Python (stdlib only: `csv`, `decimal`, `xml.etree`); no `eval`.

### 4.1 Loader (`loader/`)
- `DescriptorParser.parse(path) -> TableSchema(name, file, fields:[Field(name, type, delimiters)])`. Columns by **name**.
- `OcdCsvLoader.load(db_dir, oam_dirs=(), encoding="latin-1") -> OcdDataset`. Each record keeps `(file, line)` as `SourceRef`. Numeric fields stripped. Tables listed in `ocd_version` but empty/missing are valid; **obligatory** missing tables ⇒ diagnostic `MISSING_TABLE`.
- `DataValidator.validate(dataset) -> ValidationReport`. Link checks: article→relobj, article→scheme, article→artbase, propertyclass→property, property→relobj, value→relobj, relobj→relation, price→article, scheme tokens→property, `oam` article→`ocd_article`. Codes distinguish `MISSING_RELATION`, `MISSING_PROPERTY`, `MISSING_VALUE`, `MISSING_SCHEME`, `ORPHAN_*`. Dalby expectation: `ocd_propertyclass` rel_obj columns (73219/73220) are **not** in `ocd_relationobj` — decide from the descriptor whether that column is a relation or a text id; do not guess.
- Indices built once (dict by key); parsing is lazy-free but single pass (Dalby `ocd_price` = 3,918 rows; real programs larger).

### 4.2 Domain model (`domain/`)
Frozen dataclasses: `Article(nr, type, manufacturer, series, rel_obj, scheme_id)`, `ArtBase(article_nr, class, property, value)`, `PropertyClass(article_nr, pos, name, rel_obj)`, `Property(cls, name, pos, rel_obj, type, scope, restrictable, multi_option, …)`, `PropertyValue(cls, prop, pos, rel_obj, value | interval, default, date_from, date_to)`, `RelationObj(id, position, name, type: RelType, domain: RelDomain)`, `Relation(name, text)`, `CodeScheme(id, tokens, varcode_sep, value_sep, visibility, invisible_char, unselect_char, trim, mo_sep, mo_bracket)`, `PriceRow(...)`. `RelType` {PRECONDITION=1, SELECTION=2, ACTION=3, CONSTRAINT=4, REACTION=5, POST_REACTION=6}; `RelDomain` {C,P,BOI,PCKG,TAX}. Unknown enum values ⇒ diagnostic, not exception.

### 4.3 Relation language (`relations/`)
- **Lexer**: tokens `IDENT` (case-insensitive, `$`-prefixed specials `$BAN`, `$VARCOND`), `STRING` (single-quoted, `''` escape), `NUMBER`, operators `= <> < <= > >= EQ NE LT LE GT GE`, `+ - * /`, `( ) ,`, keywords `AND OR NOT IN SPECIFIED IF TRUE FALSE`, and constraint keywords later. Block assembly: sort by block number, drop lines whose first non-blank char is `*`, drop empty lines, join with a newline (a trailing comma is a separator, never part of an expression).
- **AST**: `Or, And, Not, Compare(op), In(value_set, negated), Specified(prop), Const, PropRef, BanRef, Concat, Arith, Assign(target, expr, cond=None), Block(statements)`; later `Constraint`, `TableCall`. `$ BAN` is a variable reference whose value is the base article number (spec App. A).
- **Parser**: precedence `NOT` > comparison/`IN`/`SPECIFIED` > `AND` > `OR`; parentheses; `IN (list)` accepts duplicates (stored as a set); `NOT IN` is its own form; `SPECIFIED x` binds as a unary condition, so `SPECIFIED a AND b NOT IN (…)` parses as `(SPECIFIED a) AND (b NOT IN (…))`. A relation that fails to parse yields `RELATION_PARSE_ERROR` with relation name, block, column, and is **never** silently treated as TRUE or FALSE; the owning entity is marked `UNEVALUABLE`.
- **Three-valued logic** (`Tri`): AND is FALSE if any FALSE, else UNDEFINED if any UNDEFINED, else TRUE; OR is TRUE if any TRUE, else UNDEFINED if any UNDEFINED, else FALSE; NOT(UNDEFINED)=UNDEFINED (spec states AND/OR rules; NOT(undefined) is **[H]**, treated as UNDEFINED until a runtime test). Comparison/IN on a property that is missing or has no value ⇒ UNDEFINED; `SPECIFIED` ⇒ TRUE/FALSE only (OCD_2+: TRUE only if the value set is restricted to exactly one value; for non-restrictable properties: has a value).
- **Per-type verdicts** (spec §2.15, App. A): precondition violated iff FALSE; multiple preconditions ANDed; none ⇒ valid; class precondition evaluated before property, property before its values (value preconditions evaluated only if the property is valid). Selection condition violated unless TRUE; several selection conditions ⇒ property must be evaluated if any is met. Action `IF` fires only on TRUE; an assignment whose right side is UNDEFINED has no effect.
- **Evaluator** receives an immutable `ConfigState` (per-property value or value set, base article). Each relation parsed once, cached by name; evaluation memoised per `(relation, state-fingerprint)` in the enumerator.
- **Supported (tested on Dalby):** items 1–10 of §2.2; comparisons; `AND/OR/NOT`; `IN`/`NOT IN`; `SPECIFIED`; `$BAN`; `+` on strings; P-domain `$VARCOND = expr` actions with commas. **Parse-supported, behaviour unverified:** numeric arithmetic, `IF` conditions, `TRUE/FALSE`, `STRING()`. **Unsupported until test data exists (diagnostic `UNSUPPORTED_SYNTAX`, never skipped silently):** Constraints (`Objects/Condition/Restrictions/Inferences`), `TABLE()` calls, multi-valued property semantics (OCD_3), multilevel configuration, `SET PRICING FACTOR`, reactions/post-reactions, SAP_LOVC/OCD_4 extensions.

### 4.4 Configuration and enumeration (`configuration/`)
- `ConfigurationResolver.resolve(article, selections) -> ResolvedConfiguration` with `property_states` (`VISIBLE|HIDDEN|UNEVALUABLE`), `value_sets`, `values`, `trace` (every precondition evaluated, with Tri result and source ref).
- Algorithm: load classes and properties by position; apply artbase fixed values; evaluate class → property → value preconditions with the current state; value set = values whose precondition is not violated; a property with exactly one valid value and no user choice is assigned that value **[S]** (explains `Bottom_WFT`; the OCD initial-value rules in spec §2.12 must be implemented from the text, §2.12 lines ~1500–1525); apply the candidate selection; **re-evaluate to a fixed point** (bounded iterations; non-convergence ⇒ `NON_CONVERGENT`); reject if any precondition of a *set* value is violated, or a selection condition/constraint is violated.
- `PermutationEngine.enumerate(article, scope) -> Iterator[ConfigurationResult]`: depth-first over the properties named in `SelectionScope.vary`, ordered by position; at each node only values still valid under the current state are offered; dependent properties are resolved, not enumerated, unless scope says to vary them. `ConfigurationResult` = `values`, `valid_in_ocd: bool`, `selected_by_scope: bool`, `trace`, `warnings`. Rejected candidates are emitted to a rejection stream with the violated relation — never dropped silently.
- `SelectionScope` (serialisable): `articles`, `vary: {property: [values] | ALL}`, `pin`, `exclude`, `max_configurations`, `cancel_token`, `progress_cb`. **There is no default scope** — the caller states it, because the reference selection is manual and unknown.
- Truncation ⇒ `ENUMERATION_TRUNCATED` with counts. Deterministic order: article, then property position, then value position.

### 4.5 Encoding (`encoding/`)
- `SchemeTokenizer.tokenize(scheme) -> [AtToken | LiteralToken | PropToken(cls, prop)]` (split on `,`; a literal is any other segment, including `" "`; a segment that contains `:` is a property token). Unknown token shapes ⇒ `UnsupportedEncoding`.
- `ArticleNumberEncoder.encode(article, scheme, config) -> str` implements §3.3. **Only** the verified subset: empty `varcode_sep/value_sep/mo_sep/mo_bracket`, `visibility=0`, `trim=1`, `invisible_char='-'`, `unselect_char='X'`. Any other flag value ⇒ `UnsupportedEncoding(flag=…)` diagnostic and no number is emitted for that article. Multi-option properties and TableCall tokens likewise.
- `VarcodeEncoder` (`final@values`, §3.4), `OfmlVarcodeEncoder` (`Class.Property=Value;…` for scope-C properties with a value), `PropVarcodeEncoder` (`_`→`__`, digit-leading `@_value`, `""`, `@VOID`; the `aggr='1'` variant is **runtime-derived and not generated**).
- Computed (`R`-type) properties and script-style schemes (Aeron pattern) — unsupported, diagnostic `UNSUPPORTED_COMPUTED_PROPERTY`.

### 4.6 Pricing (`pricing/`)
- `PriceRelationEngine.varconds(article, config) -> [VarCond]`: run the article's domain-P relations in position order; collect **every** `$VARCOND` assignment (list, not overwrite); evaluate `+` string concatenation; skip assignments whose operands are undefined (diagnostic `VARCOND_UNDEFINED`).
- `PriceCalculator.price(article, varconds, *, price_date, currency, price_type="S", quantity=1) -> PriceResult`. `price_date` and `currency` are **required keyword arguments with no default**; `PriceResult.components=[(key, level, amount, text_id, row_ref)]`, `total`, `window_used` per component, and diagnostics `NO_PRICE_FOR_KEY`, `AMBIGUOUS_PRICE_WINDOW` (>1 row), `NO_BASE_PRICE`, `PRICE_DATE_OUTSIDE_ALL_WINDOWS`. A price from a different currency/date is never substituted. Joker article `*`, `D`-level discounts, percentage (`is_fix=0`) and scale prices, and rounding rules: implemented per spec §2.17–2.18 **only when test data exists**; until then `UNSUPPORTED_PRICE_FEATURE`.
- Component percentages for the OBX: `amount / total × 100` with `decimal.Context(prec=34)` — matches the observed 34-digit values **[C]** shape, **[H]** decimal128 arithmetic; base-only ⇒ no components.
- Money in `Decimal`, never float.

### 4.7 OBX (`obx/`)
- `ObxBuilder.build(configs, *, style) -> ObxDocument`; styles: **`INPUT`** (`bskArticle` with `manufacturer`, `series`, `artNr base`, `artNr ofmlvarcode`, short/long description — what the Snapper emits and pCon *Update* completes; **[S]**), and **`REFERENCE`** (adds `final`, `varcode`, `features`, `propVarCode`, `itemPrice`, `priceComponents`, `priceDate`, `pdInfo`, `catalogInfo`, texts). `REFERENCE` **omits** `geometryChecksum`, `addStateCode`, `appData`, and records them as `UNSUPPORTED_RUNTIME_FIELD` in the report; they are never fabricated. `addStateCode` copying from a pCon export keyed by base article is an optional, explicit, *labelled* feature (**[S]** constant per base article).
- `ObxSerializer.write(doc, path)`: `cutBuffer/versionInfo/items`, one `bskArticle` per configuration, deterministic ordering and `basketId`s (UUID5 over `(base, final)` — testable; pCon uses random UUIDs, **[C]** irrelevant for comparison), UTF-8, no duplicate `final` (global per document).
- `ObxValidator.validate(path | doc) -> ValidationReport`: well-formed XML; required elements; `final` unique; `varcode` and `propVarCode` consistent with `ofmlvarcode`/features; price components sum; reports `UNSUPPORTED_RUNTIME_FIELD`.
- `ObxReader` must resolve `feature.N` text references and empty `<manufacturer id='HM'/>` entries (seen in file 1 Euro).

### 4.8 Reference comparison (`reference/`)
`ReferenceObxReader` + `ReferenceComparer.compare(generated, reference, *, fields) -> DiffReport`, keyed by `(base, final)`, per-field results `MATCH | MISMATCH | NOT_COMPARABLE(runtime field)`; and a **selection-scope inspector** that reports which values the reference uses *without* turning that into a rule. The comparer reads **pCon exports only** (`cutBuffer` root + `versionInfo`), warns on the Workbench's `_Price_Mismatch/_Failed` re-exports.

### 4.9 Diagnostics (`diagnostics/`)
`Diagnostic(code, severity, article?, property?, value?, relation?, source: SourceRef?, message, evidence_class)`. Mandatory distinct codes: `INVALID_CONFIGURATION`, `UNDEFINED_RELATION_RESULT`, `MISSING_RELATION`, `MISSING_PROPERTY`, `MISSING_VALUE`, `MISSING_SCHEME`, `NO_PRICE_FOR_KEY`, `UNSUPPORTED_ENCODING`, `UNSUPPORTED_SYNTAX`, `UNSUPPORTED_PRICE_FEATURE`, `UNSUPPORTED_RUNTIME_FIELD`, `ENUMERATION_TRUNCATED`, `RELATION_PARSE_ERROR`, `NON_CONVERGENT`. Rule: **no configuration is skipped without a diagnostic**; engine functions return `(result, diagnostics)`; exceptions are for programmer errors, never for data problems.

### 4.10 Error-handling rules
Parse error ⇒ entity `UNEVALUABLE` + diagnostic, enumeration continues, results touching it are flagged `valid_in_ocd = UNKNOWN` (tri-state, not false). Missing optional tables ⇒ info. Missing base price ⇒ no `PriceResult.total`. Unsupported flag ⇒ no article number for that article. All outputs carry the evidence class of the rule used where it is not `[C]`.

---

## 5. Test strategy

- **Unit (no data files):** truth tables for AND/OR/NOT over {T,F,U}; precondition/selection/action verdicts; lexer/parser cases for each §2.2 item including case-folded identifiers, comment/empty blocks, trailing commas, duplicate `IN` values, `NOT IN`, `SPECIFIED … AND … NOT IN`.
- **Golden (Dalby, hermetic fixtures):** copy `dalby\ANY\1\db` CSVs (≈300 KB) and the reference OBX *extracts* (`evidence/dalby_articles.csv`) into test fixtures; assert: all 1,242 final/varcode/ofmlvarcode/propVarCode; 1,242 prices with the OBX's own date+currency; `NODLE320` loses exactly BRC/BSE/WRC/WSE; `Bottom_*` cascades; the 56-article `2_Dalby_Side_Table_GBP` set reproduced when given the matching `SelectionScope`; unconstrained NODLE150 yields 60 valid configurations (30 Top × 2 Frame; each with its resolved Bottom_* values) **[H] — to be computed by the engine and compared to the OCD hand count; not yet verified**.
- **Cross-program (Lino):** `final` walk on 2,352 articles; picks up `@`×5 + literal spaces.
- **Negative:** `Bottom_Material_G=OAK` with `Top_Finish=Q75` rejected with the violated relation; unsupported flags produce diagnostics, not numbers.
- **Differential (optional, marked):** Workbench `ArticlePermutationService` and the SDK plugin used as *oracles for disagreement reports*, not as dependencies.
- **Live tests** (`C:\HermanMillerOFMLSVN`, `Downloads\Dalby_OBX_Files`) are marked and skipped when absent.
- **Runtime parity (Phase 7):** PRO 8.15 export of Dalby articles; SDK plugin run once its hash/licence problem is resolved.

## 6. Performance

Single-pass CSV load into dicts (`(prop_class, property)` → values, `rel_obj` → relobj list, `rel_name` → blocks); relations parsed once (AST cache); evaluation memoised on the subset of properties a relation references (compute referenced names at parse time, key the cache on those only); dependency-aware DFS prunes at every node; iterator-based output with `max_configurations`, cancellation checked per node, progress callback every N nodes; `Decimal` only in pricing. Expected Dalby cost is trivial; large programs are bounded by the scope cap and reported when truncated.

## 7. Source-data requirements

OCD CSV folder + all `pdata.ocd_*.inp_descr`; for OBX `REFERENCE` style also text tables (`artshorttext`, `artlongtext`, `propertytext`, `propvaluetext`, `pricetext`) and OAM + package registration for `pdInfo`/`catalogInfo`. Price date and currency supplied by the caller. A seed/reference OBX only for comparison.

## 8. Known limitations (carried into the technical document)

1. Only preconditions and P-domain price actions are verified against real data; constraints, TABLE(), reactions, multi-valued properties, computed properties are unsupported.
2. Code-scheme flags other than the all-default set are untested (`varcode_sep, value_sep, mo_sep, mo_bracket, visibility, invisible_char, unselect_char, trim=0`).
3. Rounding, discount, percentage, scale and joker prices untested.
4. `geometryChecksum`, `addStateCode`, `appData` not derivable.
5. The Dalby reference is ME 8.11; Lino is ME 8.15; no PRO export, so 8.15 behaviour for Dalby is unverified.
6. The selection behind the reference OBX is unknown; the engine will never claim to reproduce it without an explicit scope.
7. ISO-8859-1 handling unverified on non-ASCII data.
8. NOT(UNDEFINED) semantics inferred, not tested.

---

## 9. Phase plan (revised)

| Phase | Deliverable | Entry condition |
|---|---|---|
| 2 Loader + validator + domain | `loader/`, `domain/`, `diagnostics/`, tests on Dalby + Lino folders | your approval; new files only |
| 3 Relation engine | lexer/parser/evaluator, truth tables, Dalby relations 100 % parsed | none |
| 4 Configuration/enumeration | resolver, enumerator, rejection trace, scope; golden tests | explicit `SelectionScope` in tests |
| 5 Encoding + pricing | tokenizer/encoders, VARCOND, calculator; 1,242 articles | — |
| 6 OBX | `INPUT`/`REFERENCE` builders, serializer, validator, comparer | decision on runtime fields (§3.6) |
| 7 Runtime parity & integration proposal | PRO 8.15 comparison, SDK plugin, integration design | a Dalby PRO 8.15 export; working pCon |

## 10. Decisions needed before Phase 2

1. **Approve Phase 2** creating `services/ocd_engine/` and `tests/ocd_engine/` (new files only).
2. Confirm that `price_date` and `currency` are **required** inputs (recommended).
3. Confirm that `INPUT`-style OBX (base + ofmlvarcode, as the Snapper) is the first generation target, with `REFERENCE` style minus the runtime fields second.
4. Optional but valuable: a PRO 8.15 export of 2–3 Dalby articles; and, if available, the seed/queue behind the 14 Top_Finish values.
