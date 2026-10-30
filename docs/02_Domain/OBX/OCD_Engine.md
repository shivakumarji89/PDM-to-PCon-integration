# OCD Engine (`services/ocd_engine`)

**Status:** implemented and validated against real reference data; see *Limits* and *Decisions needed* before relying on it beyond what is listed as verified.
**Supersedes:** the "known gap" notes in [../Article_Encoding/Article_Encoding.md](../Article_Encoding/Article_Encoding.md) §16 and [../Permutation/Permutation_Gap_Analysis.md](../Permutation/Permutation_Gap_Analysis.md) (kept as the historical record).
**Design background:** [../../04_Reference/pCon/Investigation/OCD_Engine_Technical_Specification.md](../../04_Reference/pCon/Investigation/OCD_Engine_Technical_Specification.md).

A standalone, stdlib-only engine that reproduces OCD configuration behaviour: it loads OCD data (or is fed a neutral model), evaluates relations with three-valued logic, enumerates valid configurations with early pruning, computes properties and `$VARCOND`, encodes final article numbers from the CodeScheme, and prices a configuration. It imports nothing from the UI, Snapshot, PDM or repository layers.

## Modules

| Module | Responsibility |
|---|---|
| `schema_loader.py` | `pdata.ocd_*.inp_descr` → column names/types; OCD 4.3 defaults when absent. Columns are read **by name**. |
| `csv_loader.py` | `OcdCsvLoader` (latin-1, quoting, numeric trim, non-ASCII reported once), `OcdDataset` indexes, `build_article_model()` (classes, properties, values, ArtBase, relations) |
| `model.py` | Neutral model: `ArticleModel`, `PropertyDef`, `ValueDef`, `RelationRef`, `Assignment` |
| `relation_parser.py` | Lexer + recursive-descent parser → immutable AST; `assemble_relation_text` (blocks, `*` comments); compile cache |
| `relation_evaluator.py` | `Tri` logic, expressions, conditions, `run_actions`, `run_constraint`, per-type verdict helpers |
| `computed_property_engine.py` | Action execution in spec order (article → classes → properties → values) |
| `varcond_engine.py` | Price-domain relations → list of `$VARCOND` keys + pricing factors (isolated from the configuration) |
| `configuration_engine.py` | `ConfigurationEngine.enumerate / finalize / generate`; limits, progress, cancellation |
| `codescheme_engine.py` | Tokenizer + encoder for user-defined and predefined schemes |
| `pricing.py` | `PriceCalculator` on `Decimal`: base/extra/discount, date, currency, scale, rounding rules |
| `obx_serialization.py`, `obx_reference.py` | `ofmlvarcode` serializer; reader for pCon-resolved OBX (comparison only) |
| `diagnostics.py` | `Diagnostic`, `DiagnosticSink` (exact counts, bounded records) |

Repository integration is a controlled adapter, `services/article_obx/ocd_engine_adapter.py`; `ArticlePermutationService`, `ArticlePriceService` and `ArticleObxService` keep their public interfaces.

## Semantics implemented

* **Three-valued logic** (TRUE/FALSE/UNDEFINED). Precondition violated only if FALSE; selection condition met only if TRUE; action `IF` fires only on TRUE; an assignment with an undefined right side has no effect; a constraint restriction that is FALSE *or* UNDEFINED is violated. `NOT(UNDEFINED)=UNDEFINED` is an assumption (spec states AND/OR only).
* **Grammar:** nested AND/OR/NOT, parentheses, `= <> < <= > >= EQ NE LT LE GT GE =>`, `IN`/`NOT IN`, `SPECIFIED`, `$ BAN`, `+ - * /`, `SUBSTR STRING SIZE TOUPPER TOLOWER TRIM RTRIM LTRIM` and the appendix-F math functions, `TABLE()` in conditions/constraints/schemes, `Objects/Condition/Restrictions/Inferences` constraints, `$SET_PRICING_FACTOR`. Multi-parent relations are ordinary conditions. Identifiers and string equality are case-insensitive; ordering is lexicographic (a string literal makes a comparison a string comparison: `'900' > '1000'`).
* **Enumeration:** dependency-ordered depth-first search; each value is offered only if its preconditions are not violated by what is already chosen; a property whose precondition is FALSE is *hidden* (no value); a property with no valid value is left unset (`NO_VALID_VALUE`, info) - this is what the Dalby data requires. Constraints are checked as soon as all their inputs are chosen. `finalize` re-verifies the complete configuration (computed properties can change visibility), runs actions, constraints and price relations.
* **Distinct configurations are never merged** by their encoded number.
* **CodeScheme:** user-defined (`@` consumes the next base character, `Class:Property`, literals including space and dot, `TABLE`) and predefined `KeyValueList`/`ValueList` (VarCodeSep, ValueSep, visibility 0/1, invisible/unselect characters, trim, multi-option separator and brackets). Computed properties (Aeron `Code`) are read like any other property. Final-article encoding is separate from `ofmlvarcode`.
* **Pricing:** base + one extra-charge item per `$VARCOND` key (+ unconditioned items), valid-on-date, requested currency (never substituted), scale quantity, latest `DateFrom`, percentage items relative to the base, rounding rules `DOWN/UP/COM/ECOM`, joker article `*`, pricing factors, `Decimal` throughout.
* **Safeguards:** `EnumerationLimits(max_configurations, max_nodes)`; on a hit the engine emits `ENUMERATION_TRUNCATED` (error) - never a silent partial result. `ArticlePermutationService.max_permutations_per_article` defaults to 250,000 and is shown in the generator page status. Cancellation checkpoints every 256 nodes; progress callback.

## Verified against real evidence

All of the following run as tests (`tests/ocd_engine/test_ocd_reference_parity.py`, `tests/test_article_obx_engine_integration.py`) and skip when the files are not on the machine.

| Dataset | Result |
|---|---|
| Dalby, 1,242 pCon-resolved articles (23 base articles) | final article, `ofmlvarcode`, sale price (exact), and price-component percentages (to 1e-20) **all match** |
| Dalby cascades | Q75+MDF valid, Q75+OAK invalid, OAK+OAK valid, WLN+WLN valid; **every** Top_Finish (30) yields the expected `Bottom_Material_G`/`Bottom_Stright_Edge`/`Bottom_WFT` (independent table transcribed from `ocd_relation.csv`); NODLE150 = 60 configurations; NODLE320 loses exactly BRC/BSE/WRC/WSE |
| Dalby through the Snapshot path | NODLE150: 60 permutations; every reference final present; prices equal |
| Lino, 2,352 pCon-resolved articles (3 bases) | each reference configuration is valid under the engine and reproduces the reference final and `ofmlvarcode` (references pin the configuration; enumeration completeness is not claimed) |
| Cosm real CodeScheme `U00000000000006297` | scheme string equals the task's, 3 `@`, 6 literal spaces; encoded numbers equal an independently composed expectation |
| Aeron computed `Code` (real relation, all branches) | engine value equals a hand-written oracle for every article × Armpads W/F/N combination tested (33 articles, 3,738 configurations, types A/B/C/S) |

## OBX serialization vs pCon files

The generator writes an *input-style* OBX (format taken from the legacy Snapper flow: EAI-Server `bskXmlVersion 1.8.10`). The only pCon files available here are pCon.planner ME 8.11 / 8.15 **resolved** exports; the `Tool generated obx cloud.obx` input sample cited by earlier docs is not on this machine, so the input schema itself could not be re-checked.

| Element | Generated | pCon-resolved reference | Status |
|---|---|---|---|
| `cutBuffer` / `versionInfo` / `items` / `bskArticle` (`itemType=BasketAggregate`) | yes | yes | structure present; `appKey`/versions differ by design (EAI-Server input vs pCon.planner_ME output) |
| `manufacturer`, `series` | `id` only | `id` + localized `name` | pCon fills names on Update |
| `artNr base` | yes | yes | equal |
| `artNr ofmlvarcode` | `<SERIES><suffix>.<prop>=<code>;…` | `Class.Property=Value;…`, scope-`C` only | **engine path matches reference exactly; Snapshot path does not** (see Limits) |
| `artNr final` | predicted (mode-dependent) | resolved | predicted value verified equal on 3,594 reference articles; see Decisions |
| `artNr varcode` | never | present | intentional: pCon output only |
| `feature` | `name/value/flags` + `descrField0/1` children | inside `<features>`, with `nameText/valueText/descrText` | input subset; pCon rebuilds |
| `itemPrice` | one `purchase` element, `value="%.2f"`, `currency` | four elements (`purchase`/`sale`, with and without `pd`) | totals **equal** the reference sale price on 1,242/1,242 |
| `itemPriceComponents` / `priceComponents` | empty `itemPriceComponents` | `priceComponents` with `%` values | percentages computed by `PriceResult.percentages()` and equal the reference to 1e-20 but are **not yet written** into the OBX |
| `priceDate` | caller's string (`effective_date`) | ISO `YYYY-MM-DD` | unchanged |
| `pdInfo` | stub (`pdbType=undef`) | package registration data | runtime/package-derived; not generated |
| `taxInfos`, `packInfos`, `artCalc`, texts, `addStateCode`, `propVarCode`, `geometryChecksum`, `appData`, `catalogInfo`, `metaType` | no | yes | not generated; never fabricated |

## Limits (not verified, or unsupported)

* **No pCon parity claim beyond the table above.** Dalby is pCon ME 8.11; no PRO export exists for it. `geometryChecksum`, `addStateCode`, `appData`, `catalogInfo`, `metaType`, `propVarCode`, `taxInfos`, `artCalc`, texts are runtime/package-derived and are not generated.
* `ofmlvarcode` = scope-`C` properties with a value is confirmed for Dalby and Lino only (`flags=1 ⇔ scope C` elsewhere is a hypothesis).
* Never exercised by any reference data: predefined schemes (`KeyValueList`/`ValueList`) with populated flags, `trim=0`, multi-option separators/brackets, invisible/unselect characters acting on a real property, `TABLE` in a scheme, constraints with value-set restriction, `Inferences` over restrictable properties, reactions and post-reactions, discounts (computed from the spec text and flagged `UNSUPPORTED_PRICE_FEATURE`), scale prices, joker articles, percentage prices, rounding rules, `$SET_PRICING_FACTOR`. They are implemented from OCD 4.3 and unit-tested, not validated against pCon.
* Reactions/post-reactions (types 5/6), BOI/PCKG/TAX domains, multi-valued property semantics (OCD_3), multilevel configuration, `USER_MESSAGE()`/`ABORT()`: not evaluated; an unparsable or unsupported clause is reported (`RELATION_PARSE_ERROR` / `UNSUPPORTED_SYNTAX`), never guessed.
* Value-set **restriction** by constraints is not modelled (such a restriction never fails and is not applied).
* Interval/free-input property values are not enumerable (reported at info level).
* Cyclic property dependencies fall back to declaration order (`CYCLIC_DEPENDENCY`); results are re-verified at `finalize`.
* The Snapshot path inherits repository limits: the MDB import keeps only `name` and `body` of a code scheme (not its visibility/replacement/trim fields), so those default to the values every sampled real scheme carries (`visibility 0`, trim on, `-`, `X`); `ofmlvarcode` there is still `<SERIES><suffix>.<property>=<code>` for every non-excluded property, whereas real data uses the actual property class (`DALBY_ATTR`/`DALBY_OPT`) and only configurable properties.

## Behaviour changes in the repository generator

1. Full relation grammar replaces the single-parent regex; property-level relations (bound to a property, no value) now apply; `article_codes` bindings restrict a relation to its articles.
2. A hidden property is omitted; a property with no valid value is left unset instead of discarding the whole branch (the legacy service returned **0** permutations for real Dalby cascades).
3. An undefined operand makes an assignment a no-op (spec) instead of contributing `""`.
4. Value-bound actions/price relations fire only when that value is selected (they previously fired for every configuration).
5. `ArticleObxService.generate` priced every permutation of an article with the **last** permutation's price (results were keyed by article id). Prices are now resolved per permutation.
6. Prices use one row per `$VARCOND` key (OCD 3.2) instead of requiring the combined key string to equal one price row; `ArticlePermutation.variant_conditions` carries the list (`variant_condition` is the space-joined form).

## Decisions needed (owner)

1. **`artNr type="final"` in generated OBX.** Evidence: every pCon *input* OBX described in the investigation carries only `base` + `ofmlvarcode`; the Snapper flow writes a sentinel `final` that `OBXService.clean_obx` later drops. Real pCon *resolved* files (all of the supplied Dalby/Lino files) carry `final` and `varcode`. The default is unchanged (`final_article_mode="predicted"`, now verified correct for Dalby/Lino); `"omit"` is the input-style form and `"sentinel"` the Snapper-compatible form. `artNr type="varcode"` is never written. Choose the default once the pCon import workflow is confirmed.
2. **User-defined scheme without `@`.** OCD 4.2 says the scheme produces the whole number (Aeron relies on this); the repository generator still prefixes the base article (`legacy_base_prefix_without_at = True`) because existing tests encode that behaviour. The standalone engine follows the spec.
3. Whether to import the full CodeScheme row (visibility, replacement characters, trim, separators) into the Snapshot (shared MDB loading, untouched here).
4. The legacy single-parent methods in `ArticlePermutationService` (`_property_combinations` and helpers) are no longer used by `build()`; they are retained only because `tests/test_cancellation_workflow_surfaces.py` exercises them. Retarget that test and delete them when convenient.

## Performance

Measured on this machine (Python 3.12, single thread).

| Case | Before (legacy service) | After (engine) |
|---|---|---|
| 7 properties × 6 values, chained value relations (raw product 279,936, valid 6), Snapshot path | 6 permutations, 7.3 ms | 6 permutations, 7.2 ms |
| Real Dalby NODLE150 / 300 / 600 via Snapshot path | **0** permutations (cascade branches discarded) | 60 / 300 / 540 permutations, 31 / 132 / 230 ms |
| Aeron AER1A11 (raw product 21,772,800), standalone | n/a | 14,112 valid configurations, 71,461 nodes visited, 4.3 s |
| Cosm FLC142 (raw product 124,416), standalone | n/a | 1,296 valid, 4,331 nodes, 0.31 s |
| Dalby, all 1,242 reference articles: enumerate + price + compare | n/a | ≈ 4 s |

Relations are parsed once (compile cache keyed by type and text), CodeSchemes tokenized once (`lru_cache`), values are filtered per node, constraints run at the first depth where their inputs exist.
