# Article Encoding / CodeScheme

**Status:** CURRENT — canonical source of truth for Article Encoding and CodeScheme. Empirical, evidence-only. No decompilation, no runtime tracing.
**Related:** [Variant_Code_and_Final_Article_Number.md](./Variant_Code_and_Final_Article_Number.md) · [Permutation_Model.md](../Permutation/Permutation_Model.md) · [Permutation_Gap_Analysis.md](../Permutation/Permutation_Gap_Analysis.md) · [OBX_Generation.md](../OBX/OBX_Generation.md)

Sources used:
1. OCD spec `C:\Users\siaoca\Desktop\MK_OFML_Testsuite\Docs\ocd_4.3_en.md` (§2.2, §2.24, §4.1-4.3).
2. **Real, reachable OCD repository data** — `C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx\{aeron,cosm,atlas,civic_tables,lino,hush,fold}\ANY\1\db\*.csv`. This is a live Herman Miller OFML repository present on this machine (not previously catalogued in the earlier investigation) and it contains real `ocd_codescheme.csv`, `ocd_relation.csv`, `ocd_relationobj.csv`, `ocd_property.csv`, `ocd_article.csv` files. **No `hmx/cloud` (Cloud chair) directory exists in this repository** — re-confirms the prior "no HMX Cloud OFML package installed" finding; Cloud's own CodeScheme could not be verified from real data.
3. `C:\KnollSVN\Staging\HermanMiller\WS\KnollStudio\saarinen` exists but only as compiled `.mdb` workspace databases (`pcr_data_com_ocd.mdb`), not exported CSV — Saarinen's CodeScheme content was **not** independently re-verified in CSV form (see item 17).
4. `MK_OFML_Testsuite` sibling repo, worktree `feat-sku-importer` (branch not merged to main in that repo): `modules/sku_importer/decoder.py`, `modules/sku_importer/script_decoder.py`, `Docs/superpowers/specs/2026-03-31-sku-importer-design.md`. This worktree is a genuine, already-working attempt at exactly this problem (SKU → property decode via real CodeScheme grammar) and its design doc's claims are now cross-checked against real data below.
5. `MK_OFML_Testsuite` main branch: `modules/snapper/{generator.py,reader.py,hierarchy.py,seed_parser.py}`.
6. MK Workbench: `services/article_obx/article_permutation_service.py`, `services/article_obx/article_obx_service.py`, `services/article_obx/article_price_service.py`.

---

## 1. What is an Article Encoding / CodeScheme?

**CONFIRMED (spec + real data).** `CodeScheme` is a table (`ocd_codescheme.csv`) of named grammars, each identified by a `SchemeID`. An `Article` row (`ocd_article.csv`) references exactly one `SchemeID` via its 11th field (0-indexed column 10). The scheme's `Scheme` field (2nd column) is either a **predefined** scheme name (`KeyValueList` or `ValueList`, OCD §4.1) or a **user-defined** scheme description string (OCD §4.2). The scheme, evaluated against a configuration's current property values, produces the article's **final article number**.

Evidence — OCD §2.2 (`ocd_4.3_en.md:613-721`), field 11: *"The identifier indicated in the 11th field serves to reference the codification scheme from the table CodeScheme (section 2.24)... If no identifier is indicated or an identifier, which is not referenced in the scheme table, no specific final article number will be generated."*

Real data confirms the column position directly — `ocd_article.csv` row for Aeron:
```
AER1A11;C;HM;AERON;000000000000065651;000000000000168058;22130;0;1;C62;U00000000000006418
```
(0-indexed) column 10 = `U00000000000006418`, which is exactly the `SchemeID` key of a row in the same range's `ocd_codescheme.csv`:
```
U00000000000006418;AERON_OPTIONS:Code;"";"";1;"-";"X";1;"";""
```

**Correction to the sibling repo's own design doc:** `2026-03-31-sku-importer-design.md:47` claims column 10 in `ocd_article.csv` is used "for ranges that store the codescheme ID in ocd_article.csv column 10 (all Knoll ranges)" — implying this is Knoll-specific. Real Herman Miller data (Aeron, above) shows this is the **general OCD-spec-mandated field position for every range**, HM included, not a Knoll-only convention. `modules/sku_importer/decoder.py:5` (`CODESCHEME_COL = 10`) is correct as written; the design doc's framing of it as Knoll-specific is an overstatement not supported by the spec or by HM data.

---

## 2. Where is it stored in the repository?

**CONFIRMED.** `{manufacturer}/{range}/ANY/1/db/ocd_codescheme.csv` (per-range file), referenced from `{same db}/ocd_article.csv` column 10. Both are semicolon-delimited CSV, exactly the shape `modules/snapper/reader.py:_read_csv` and `modules/sku_importer/decoder.py:read_codescheme` already parse. Verified present and non-empty for Aeron, Cosm, Atlas, Civic_tables, Lino, Hush, Fold in the real HM repository at `C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx\`.

---

## 3. What is the grammar?

**CONFIRMED, two distinct grammars exist (OCD §4.1 vs §4.2), and they are NOT interchangeable:**

### 3a. Predefined schemes (OCD §4.1, `ocd_4.3_en.md:2977-3011`)
`Scheme` field is literally `KeyValueList` or `ValueList`. In this case:
```
Final Article Number = Article code + VarCodeSep + Variant Code
```
where `VarCodeSep` (field 3) is a literal separator string, and the variant code is built from fields 4-10 (`ValueSep`, `Visibility`, `InVisibleChar`, `UnselectChar`, `Trim`, `MO_Sep`, `MO_Bracket`) per §4.1/§4.3. **No real predefined-scheme row was found in the 7 HM ranges sampled** (Aeron, Cosm, Atlas, Civic_tables, Lino, Hush, Fold all use user-defined schemes) — this style is CONFIRMED FROM SPEC TEXT ONLY, not independently observed in real repository data in this pass.

### 3b. User-defined schemes (OCD §4.2, `ocd_4.3_en.md:3015-3057`) — the style actually observed in every real range sampled
`Scheme` field syntax (verbatim from spec, `ocd_4.3_en.md:3019`):
```
<Scheme> := [<PropertyClass>:<PropertyName> | <TableCall> | @ | <Char>,] 1:n
```
Evaluated **left to right**, replacing each comma-separated segment:
- `<PropertyClass>:<PropertyName>` → current property value (formatted per fields 5-10 of CodeScheme, and per the Property table's length field)
- `<TableCall>` → looked up via a value-combination table's `$FAN` result (not observed in any sampled range's codescheme string, though value-combination *tables* i.e. `*_tbl.csv` files exist and are used for other purposes — see Finding 10)
- `@` → the **next character of the base article number**, consumed left to right
- any other single `<Char>` (not `,` or `@`) → inserted literally, unchanged

**Critically, for user-defined schemes there is no separate "base + VarCodeSep + variant code" step** — the entire final article number, including the reconstructed base-article characters, is produced by walking this one grammar string. This refines (does not contradict, since §4.1 is a distinct case) the generalized formula in `docs/02_Domain/Product/Article_Configuration_Model.md:47-49`, which states the base+sep+variant-code model as if universal; it is universal only for the two *predefined* scheme names, and every real range sampled here uses the *user-defined* form instead.

Real example, Cosm (normal finish variant), `ocd_codescheme.csv`:
```
U00000000000006297;@,@,@,COSM_NORMAL:Assembly_Option,COSM_NORMAL:Back_Height,COSM_NORMAL:Height_Adjustment,COSM_NORMAL:Tilt,COSM_NORMAL:Seat_Depth,COSM_NORMAL:Arms, ,COSM_NORMAL:Frame_Finish, ,COSM_NORMAL:Chassis_Finish, ,COSM_NORMAL:Base_Finish, ,COSM_NORMAL:Castors_Glides, ,COSM_NORMAL:Armpad_Finish_H, ,COSM_NORMAL:Intercept_Finish;"";"";0;"-";"X";1;"";""
```
Segment-by-segment: 3× `@` (consume 3 base-article chars) → 6 property values concatenated directly with **no separator** (`Assembly_Option`, `Back_Height`, `Height_Adjustment`, `Tilt`, `Seat_Depth`, `Arms`) → **literal space** (` `) → `Frame_Finish` → **literal space** → `Chassis_Finish` → **literal space** → `Base_Finish` → **literal space** → `Castors_Glides` → **literal space** → `Armpad_Finish_H` → **literal space** → `Intercept_Finish`.

### 3c. Aeron: script-adjacent user-defined scheme with a computed `Code` property
`ocd_codescheme.csv`: `U00000000000006418;AERON_OPTIONS:Code;"";"";1;"-";"X";1;"";""` — a single `Class:Property` segment (no commas, matching `detect_style()` in `decoder.py:96-98`: "no comma → script style"). `Code` (property `AERON_OPTIONS.Code`) is itself a **computed property** (`ocd_property.csv` row 37: `AERON_OPTIONS;Code;17;;22138;C;1;0;1;0;0;0;R;0;` — type `R` = relation-computed, `relation_id=22138`). Its value is not stored, it is derived by a formula in `ocd_relation.csv`, bridged via `ocd_relationobj.csv` (short id `22138` → long id `000000000000570755`):
```
Code = SUBSTR($BAN,0,3) IF Aeron_Type IN ('A','B','C'),
Code = Code + Assembly_Option + Aeron_Type + Height_Adjustment + Tilt_Option + Arms + Armpads + ' ' + Back_Support + ' ' + Frame_Finish + ' ' + Chassis_Finish + ' ' + Base_Finish + ' ' + Castors_Glides + ' ' + Armpad_Finish + ' ' + Pellicle IF Armpads = 'W' AND Aeron_Type IN ('A','B','C'),
Code = Code + Assembly_Option + Aeron_Type + Height_Adjustment + Tilt_Option + Arms + Armpads + ' ' + Back_Support + ' ' + Frame_Finish + ' ' + Chassis_Finish + ' ' + Base_Finish + ' ' + Castors_Glides + ' ' + Pellicle + ' ' + Armpad_Finish IF Armpads = 'F' AND Aeron_Type IN ('A','B','C'),
Code = Code + Assembly_Option + Aeron_Type + Height_Adjustment + Tilt_Option + Arms + Armpads + ' ' + Back_Support + ' ' + Frame_Finish + ' ' + Chassis_Finish + ' ' + Base_Finish + ' ' + Castors_Glides + ' ' + Pellicle IF Armpads = 'N' AND Aeron_Type IN ('A','B','C'),
Code = SUBSTR($BAN,0,3) IF Aeron_Type IN ('S'),
Code = Code + Assembly_Option + Height_Adjustment + Tilt_Option + Arms + Armpads + ' ' + Back_Support + ' ' + Frame_Finish + ' ' + Chassis_Finish + ' ' + Base_Finish + ' ' + Castors_Glides + ' ' + Armpad_Finish + ' ' + Pellicle IF Armpads = 'W' AND Aeron_Type IN ('S'),
Code = Code + Assembly_Option + Height_Adjustment + Tilt_Option + Arms + Armpads + ' ' + Back_Support + ' ' + Frame_Finish + ' ' + Chassis_Finish + ' ' + Base_Finish + ' ' + Castors_Glides + ' ' + Pellicle + ' ' + Armpad_Finish IF Armpads = 'F' AND Aeron_Type IN ('S'),
Code = Code + Assembly_Option + Height_Adjustment + Tilt_Option + Arms + Armpads + ' ' + Back_Support + ' ' + Frame_Finish + ' ' + Chassis_Finish + ' ' + Base_Finish + ' ' + Castors_Glides + ' ' + Pellicle IF Armpads = 'N' AND Aeron_Type IN ('S')
```
(source: `C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx\aeron\ANY\1\db\ocd_relation.csv`, long id `000000000000570755`). This is a **real, currently-shipping, multi-branch, multi-group encoding formula** with: `SUBSTR($BAN, start, len)` (base-article slicing), self-reference (`Code = Code + ...`), multiple `IF`/`IN` branches (last matching branch wins, per the evaluator in `script_decoder.py:evaluate_formula`), string-literal-space concatenation as a group separator, and conditional selection of which properties appear at all (`Armpads='W'` vs `'F'` vs `'N'` reorders/adds/drops `Armpad_Finish`).

---

## 4. How are properties referenced?

**CONFIRMED.** By `PropertyClass:PropertyName` in template-style schemes (e.g. `COSM_NORMAL:Frame_Finish`), or by bare `PropertyName` inside a script-style `Code` formula (e.g. `Assembly_Option`, `Back_Support`). The property class maps to `ocd_property.csv` column 1; the property name to column 2. `AERON_OPTIONS.Code` at `ocd_property.csv:37` shows the referenced-in-scheme property (`AERON_OPTIONS:Code`) can itself be a *computed* (`type=R`, i.e. relation-derived) property rather than a raw configurable one — property reference and property *storage* are not the same thing.

## 5. How are values referenced?

**CONFIRMED.** The property's *currently selected* value string, taken from `ocd_propertyvalue.csv` (column 8/last-non-empty column per `modules/snapper/reader.py:139-155`), formatted per the property's declared length (Property table) and, for template segments, the CodeScheme's `InVisibleChar`/`UnselectChar`/`Trim` fields (5-8) when the property is currently invalid/unselected — CONFIRMED FROM SPEC TEXT (`ocd_4.3_en.md:2594-2621`), not independently observed acting on a real invisible/unselected property in this pass (all sampled example rows show only "currently visible & selected" states).

## 6. How are literals represented?

**CONFIRMED.** Any character in a user-defined `Scheme` string other than `,` and `@` is a literal, inserted unchanged (OCD §4.2: *"`<Char>` is not replaced... All printable characters... except ',' and '@'."*). Real data shows single-character literals used both as **separators between groups** (space, see Finding 3b/3c) and as **structural delimiters within a segment position** (`.` in Atlas/Civic_tables/Fold templates, e.g. `ATTR:PowerEntryCord,.,ATTR:Depth_Code` — a literal dot between an attribute group and a dimension group).

## 7. How are spaces represented?

**CONFIRMED — the single most consequential finding for MK Workbench.** A literal space character is a first-class scheme token, appearing as its own comma-delimited segment (` `) in template schemes, or as a quoted string literal (`' '`) inside script formulas. It is used specifically to delimit **finish/option groups** from each other — e.g. Cosm's `COSM_NORMAL:Arms, ,COSM_NORMAL:Frame_Finish` (space between the "attribute" group and the start of the "finish" group), and Aeron's `Armpads + ' ' + Back_Support + ' ' + Frame_Finish + ' ' + Chassis_Finish + ' ' + Base_Finish + ' ' + Castors_Glides + ' ' + Armpad_Finish + ' ' + Pellicle` (a space before **every** subsequent finish property). This directly explains the previously-observed Cloud OBX `varcode`/`final` structure (`NOCLE410 R00 1HA02 1HA01` — four space-separated groups) as a plausible instance of the same pattern, though Cloud's own scheme string could not be read from real data (Finding 3, item 2 in Sources).

`modules/sku_importer/decoder.py:parse_template_segments` already implements this correctly: a comma-only segment or a segment that strips to empty is preserved as a literal `" "` (lines 108-112).

## 8. How are separators represented?

**PARTIALLY CONFIRMED.** Two distinct separator mechanisms exist and must not be conflated:
- **`VarCodeSep` (CodeScheme field 3):** the separator between base article number and variant code, meaningful **only for predefined schemes** (§4.1). Not observed acting in any real user-defined-scheme range sampled, since user-defined schemes reconstruct the base characters via `@` inline rather than appending a separately-joined variant code (Finding 3b).
- **Inline literal characters** (Finding 6/7) inside the user-defined `Scheme` string itself — this is the separator mechanism actually exercised by every real range sampled (space, dot).
`ValueSep` (field 4) and `MO_Sep`/`MO_Bracket` (fields 9-10, for multivalued properties, §4.3) were not observed acting in any sampled scheme string either (all sampled CodeScheme rows have `""` in fields 3/4/9/10) — CONFIRMED FROM SPEC TEXT ONLY for these three fields.

## 9. How are groups represented?

**CONFIRMED.** A "group" (e.g. "attribute codes" vs "frame finish" vs "base finish" vs "fabric") is not a first-class scheme construct — it emerges purely from the placement of literal-space (or literal-dot) tokens between runs of `Class:Property` segments. Cosm's scheme shows 3 groups (attributes with no separator; then repeated `finish-property, space` pairs — each finish property gets its **own** leading space, not one space per group boundary). Atlas/Civic_tables show a `.` used once as a group boundary between the "attribute code" run and the "dimension code" run, then spaces before each subsequent option/finish property.

## 10. How are repeated finish groups handled?

**PARTIALLY CONFIRMED.** No single real scheme sampled had two properties of the *same* semantic type repeated back-to-back inside one CodeScheme string (e.g. two independent "fabric colour" picks in a row) — the closest observed pattern is Aeron's *conditional reordering*: depending on `Armpads`'s value (`W`/`F`/`N`), the formula emits a **different ordering and a different count** of trailing finish properties (`Back_Support, Frame_Finish, Chassis_Finish, Base_Finish, Castors_Glides, Armpad_Finish, Pellicle` vs the same list with `Pellicle`/`Armpad_Finish` swapped, vs the same list with `Armpad_Finish` dropped entirely for `Armpads='N'`). This proves the grammar supports **conditional group membership and group ordering**, driven by relation/formula branches, not a fixed template — a materially different mechanism from MK Workbench's current fixed-order-only encoding (see Finding 16). A genuine "same property type repeated" case (e.g. Knoll Saarinen's multi-market suffix, referenced in the sibling repo's design doc `2026-03-31-sku-importer-design.md:171`) could not be independently re-verified — Saarinen's real OCD data on this machine is CSV-inaccessible (Finding, Sources item 3).

## 11. How does relation resolution affect valid configurations?

**BEHAVIOR CONFIRMED, IMPLEMENTATION INTERNAL UNKNOWN.** Two separate relation-consuming mechanisms exist in real data and in the sibling repo's working code, and they must not be conflated:
- **Validity relations** (`ocd_relation.csv` rows referenced from `ocd_propertyvalue.csv`'s `relation_id` column) gate whether a given property *value* is currently selectable at all, typically expressed as `(SPECIFIED Parent) AND (Parent IN ('val'))` (parsed by `modules/snapper/hierarchy.py:_CONDITION_PATTERN`, confirmed against real Aeron-style hierarchy relations in the same file's docstring examples) or `Parent = 'val'` (the "Fin"-range simple-equality variant, per `hierarchy.py:_SIMPLE_EQUALITY_PATTERN` comment). These relations do **not** produce a value — they only gate which parent/child value combinations are legal.
- **Computed-property relations** (e.g. Aeron's `Code`, or `i*`-prefixed intermediate properties referenced by `decoder.py:invert_computed_property`) *do* produce a value, by formula evaluation over already-valid/selected properties — these feed directly into encoding (Finding 12).

## 12. How does a valid configuration feed encoding?

**CONFIRMED for script-style, PARTIALLY CONFIRMED for template-style.** For script-style ranges (Aeron), the *entire* final-article code is one computed property (`Code`), meaning relation evaluation and encoding are **the same step** — there is no separate "assemble variant code from selected properties" pass; the CodeScheme merely says "print the value of this one computed property" (`AERON_OPTIONS:Code`). For template-style ranges (Cosm, Atlas, etc.), each `Class:Property` segment is evaluated independently (its own currently-selected value, or an `i*`-computed value inverted back from a relation per `decoder.py:170-194`) and then positionally concatenated per the literal/space structure of the scheme string — encoding is a separate, later pass over an already-resolved property set.

## 13. How is Variant Code produced?

**CONFIRMED for predefined schemes (spec only), CONFIRMED for user-defined schemes (spec + real data — but see caveat).** For user-defined schemes there is, strictly, no separately-identifiable "variant code" substring at all — the scheme string interleaves base-article `@`-characters with property values and literals in one pass, so "variant code" is better understood as *"the final article number minus whatever the `@` segments reconstructed,"* not a value pCon computes as an independent artifact before concatenation. This matters directly for MK Workbench's `<artNr type='varcode'>` field (Finding 15/16): a real pCon-resolved OBX output does write a distinct `varcode` value (`NOCLE410 R00 1HA02 1HA01@10 R00 1HA 1HA02 1HA 1HA01` — base+final-code, `@`, then the full un-filtered code list), suggesting pCon's *runtime* internally does still track a "variant code" concept even for user-defined-style output, but this exact pairing could not be reproduced from the Cloud range's own CodeScheme (unavailable) — labelled **UNKNOWN** how pCon derives this two-part `varcode` string mechanically from a user-defined CodeScheme string.

## 14. How is Final Article produced?

**CONFIRMED** per Findings 3a/3b/3c above — depends entirely on scheme style; there is no single universal formula. For every real user-defined scheme sampled, Final Article = left-to-right walk of the `Scheme` string, replacing `@` with the next base-article character, `Class:Property` with the current/computed property value, and any other character with itself, subject to conditional branch selection when the referenced property is itself relation-computed (Aeron `Code`).

## 15. What does OBX contain for base/varcode/final?

**BEHAVIOR CONFIRMED** (from the two real Cloud OBX captures established in the prior investigation pass, re-confirmed unchanged here — no new OBX captures were read in this pass beyond what was already established):
- Unresolved **input** OBX: only `<artNr type="base">` and `<artNr type="ofmlvarcode">` (the OFML property=value varcode input syntax, `Class.Property=Value;...` — matching `modules/snapper/generator.py:build_varcode`/`build_varcode_multi` exactly). No `type="final"`, no `type="varcode"`.
- pCon-**resolved output** OBX additionally contains `<artNr type="final">` (the computed final article number string) and `<artNr type="varcode">` (a two-part `base+finalcode@fullcode` string), plus `<feature>` elements and `<propVarCode>`.
This confirms real pCon *input* files never carry `type="final"` or `type="varcode"` — those are pCon's own resolved-output fields, never something a producer of input OBX (MK Workbench or the sibling `sku_importer`/`snapper` tools) should be writing into an OBX meant to be handed to pCon for resolution.

## 16. What does MK Workbench currently do differently?

**CONFIRMED** (`services/article_obx/article_permutation_service.py:439-481`, read in full this pass):
```python
return base_code + "".join(tokens)
```
`tokens` is an ordered list of raw property-value codes (ordering driven by `_scheme_property_order`, itself derived from `code_schemes[...]["body"]` — i.e. the *order* of properties in the scheme string is honoured, but nothing else about the scheme string is parsed). Concretely, MK Workbench:
- Never parses `@`, literal characters, or comma-segment structure out of the CodeScheme `body` at all — only extracts a property name **ordering** from it.
- Never inserts literal separators (no spaces, no dots) between property-value tokens — contradicting every real user-defined scheme sampled (Findings 3b/3c/7/9).
- Never re-derives base-article characters via `@` — it always prepends the whole `base_code` verbatim once, at the front, which happens to be correct only if the scheme's `@` segments are contiguous and equal in count to `len(base_code)` and occur before all property segments (true for the samples inspected — Aeron script-style consumes `$BAN` wholesale via `SUBSTR`, Cosm/Atlas/etc. consume exactly enough `@`s to cover the base code prefix before any property segment) — but this is coincidental alignment, not a parsed rule, and would silently break for any scheme interleaving `@` segments *between* property segments (not observed in the 7 ranges sampled, but the grammar explicitly permits it per §4.2).
- Never evaluates script-style/computed-property (`Code`) formulas at all — `code_schemes[...]["body"]` for an Aeron-style range would presumably be `AERON_OPTIONS:Code`, a single token with no comma, which `_scheme_property_order` would almost certainly not resolve into a real per-property order the way `decoder.py`'s script-vs-template branch does.
- `services/article_obx/article_obx_service.py` writes `type="base"` and `type="final"` (from `p.final_article`, i.e. MK Workbench's own no-separator concatenation) plus `type="ofmlvarcode"` — **confirmed it does NOT write `type="varcode"`** (verified by reading the full `_render_xml` method; only `base`, `final`, `ofmlvarcode` `<artNr>` elements are emitted). Per Finding 15, this is actually *correct* behavior for an input OBX (real pCon input files never carry `varcode` either) — **but** MK Workbench's `type="final"` value is very likely wrong given Finding 16's concatenation gap, and per Finding 15 real pCon input OBX files never carry `type="final"` at all, only `type="base"` + `type="ofmlvarcode"` — meaning MK Workbench may be writing a *speculative*, generally-incorrect `final` article number into a file whose only job (per every real captured input OBX) is to hand pCon the base + raw property assignments and let pCon's own Update step compute `final`/`varcode` itself.
- `services/article_obx/article_price_service.py` (lines ~87-160) keys price lookups by `article_id` + `variant_condition` — this **does** match the OCD `Price` table's real key structure (`ocd_price.csv` columns `article_nr;var_cond;price_type;price_level;...`, confirmed against `pdata.ocd_price.inp_descr` and a real Aeron price row `AER1A11;AF;S;B;...`), so pricing-key logic is **not** part of the gap; it is already aligned.

## 17. What exact information is still unknown?

**UNKNOWN / explicitly not resolved in this pass:**
- Cloud (NOCLE4)'s own real `ocd_codescheme.csv`/`ocd_relation.csv` content — the range is not present in the one real HM OFML repository reachable from this machine (`C:\HermanMillerOFMLSVN\...\hmx\`), so whether Cloud is template-style or script-style, and its exact scheme grammar, remains inferred-only from the two OBX captures, not confirmed from source data.
- Saarinen (Knoll)'s real `ocd_codescheme.csv` content in CSV form — only compiled `.mdb` workspace files were found (`C:\KnollSVN\Staging\HermanMiller\WS\KnollStudio\saarinen\pcr_data_com_ocd.mdb`), which were not opened (out of scope: no MDB-reading tool was used in this pass, and doing so was not requested). The sibling repo's own tests (`tests/sku_importer/test_decoder.py:19-21,38-41,176-185`) reference `C:\KnollOFMLSVN\Staging\_repository` as the expected real-data path for Saarinen, but that exact path **does not exist** on this machine (`/c/KnollOFMLSVN` — not found; the actual Knoll path found is `C:\KnollSVN\...`, a different root) — so those particular sibling-repo tests would currently fail/be skipped here, and the "22 script-style / 96 template-style across 118 ranges" statistic in the sibling design doc could not be independently re-counted against real data in this pass (only 7 HM ranges were sampled directly).
- Whether any real range's CodeScheme uses a genuine `<TableCall>` segment (§4.2's third alternative) — not observed in any of the 7 sampled ranges' `ocd_codescheme.csv` strings, though `*_tbl.csv` files do exist in some ranges' `db/` folders for other purposes (parent/child value tables, per `modules/snapper/hierarchy.py:detect_hierarchy_from_tables`) and could theoretically be TableCall targets in a range not sampled here.
- Whether `ValueSep`, `MO_Sep`, `MO_Bracket`, or a non-empty `VarCodeSep` are ever populated in any real range's `ocd_codescheme.csv` — every sampled row across 7 ranges had all of fields 3/4/9/10 empty (`""`).
- The exact mechanical relationship between a resolved OBX's two-part `<artNr type='varcode'>` value (`base+finalcode@fullcode`) and the source CodeScheme string, given Cloud's own scheme is unavailable (see above) — labelled UNKNOWN in Finding 13.
- Whether MK Workbench's `code_schemes[...]["body"]` field, as currently populated by its own MDB/OCD reverse-engineering pipeline, actually stores the raw, unparsed `Scheme` string (2nd CSV column) verbatim, or some already-transformed/partial representation — this was out of scope to verify in this pass (would require reading `services/mdb_reverse_engineering_service.py` in full, which the task scope limited to citing for pricing-key logic only, not re-auditing the scheme-body ingestion path).
