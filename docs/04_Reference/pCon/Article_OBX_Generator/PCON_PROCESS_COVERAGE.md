# Article OBX Generator - pCon process coverage matrix

Evidence base: `services/ocd_engine/*`, tests under `tests/ocd_engine` and `tests/test_article_obx_large_results.py`, and the
real Betwixt repository `...\hmx\betwixt\ANY\1\db` (article **LN10**). Verified 2026-11-03.

## Real OCD facts (LN10)

* `ocd_article`: one row, `LN10`, `scheme_id = U00000000000000001`.
* `ocd_artbase`: one row, `LN10;PLC;PLC;LN` - ArtBase restricts 1 of the article's 14 properties.
* `ocd_propertyclass`: `LN10` -> `FEATURES`, `FINISHES`, `CODE`, `PLC`. Options/finishes are not a separate table: they are the
  properties of assigned classes (`FINISHES` = Frame/Seat/Back/Arm finish, fabric types, fabric colours).
* Encoding has **two cooperating mechanisms**: `ocd_codescheme` `U00000000000000001 = CODE:Code` (direct article encoding) reads the
  property `Code`, which is computed by a type-3 *code relation* (relation 80: `Code = $BAN + Frame + Seat + Back + ' ' + ...`).
  Neither replaces the other here; a scheme that reads only ordinary properties needs no code relation.
* Fabric: 17 fabric types x 448 colours per side. The type->colour link is **not a table**: each colour value carries a precondition
  (`Seat_Fabric_Type = '172'`), 18 distinct groups. `ocd_propertyvalue.is_default` is **0 on every Betwixt row**; 65 other ranges
  do set it.

## Matrix

| Step | Existing implementation | Evidence | Gap | Correction | Status |
| --- | --- | --- | --- | --- | --- |
| 1 Base article | `OcdCsvLoader` / `build_article_model` / catalogue | `test_ocd_loader`, `test_ocd_catalogue` | none | - | Fully implemented and verified |
| 2 ArtBase | `build_article_model` -> `PropertyDef.allowed_keys` | `test_ocd_artbase_enumeration` (real semantics checked on 80+ ranges) | none | - | Fully implemented and verified |
| 3 Article encoding (scheme and code relation) | `CodeSchemeEncoder`, `ComputedPropertyEngine` | LN10 encodes through both; `test_ocd_codescheme`, `test_ocd_resolved_configuration` | No explicit report of *which* mechanism applies to an article | `structure.trace_article` -> `EncodingSource.mechanisms` | Implemented; trace added |
| 4 Classes -> properties | `build_article_model` via `ocd_propertyclass` | LN10 structure test | Chain was implicit | `ArticleStructure` (Base -> Encoding -> Classes -> Properties) | Implemented; made explicit and tested |
| 5 Property values | `ocd_propertyvalue` per (class, property), ArtBase-restricted; never a global product | `test_values_do_not_leak_between_bases_sharing_a_class` | none | - | Fully implemented and verified |
| 6 Options and finishes | Same class mechanism (no separate OCD table) | LN10 `FINISHES` class | Not documented | Documented above and in trace (by class) | Implemented; documented |
| 7 Fabric default colour | Absent: every valid colour was enumerated | LN10 had 448 colours x 2 sides enumerated | **Not implemented** | `fabric.py` + `ConfigurationEngine(fabric_default_only=True)`: a fabric colour is offered as its `is_default` value only; type->colour read from relations | Implemented: first relation-valid colour in source order; LN10 254,043 -> 432 |
| 8 Relations | Parser/evaluator (3-valued), preconditions, selections, constraints, actions, `$VARCOND`; candidate cache | `test_ocd_relation_*`, `test_ocd_configuration_engine` | `USER_MESSAGE` (reaction) is skipped with a warning | none - unsupported constructs stay diagnostics | Implemented; reactions unsupported |
| Dedup / price key / ResolvedConfiguration | `generator.generate`, `resolved.py` | `test_ocd_price_equivalence` | none | - | Fully implemented and verified |
| UI responsiveness, progress, cancellation | `SkuResultsModel`, worker reporter, `checkpoint()` | `test_article_obx_large_results` | none | - | Fully implemented and verified |

## Fabric default - first relation-valid colour (updated)

Rule implemented: for each configuration the engine filters a fabric colour's values with the normal relation evaluator
(`_filter_values`: every precondition of the value, so the selected type and any other property it reads), keeps them in OCD source
order (`pos_pval`) and offers only the first; a value flagged `is_default` wins when it is valid. No valid colour while a fabric type
is selected rejects the configuration (`NO_FABRIC_COLOUR` warning, counted in `pruned`); a hidden colour property is untouched.
The candidate cache is keyed on exactly the property values the colour relations read, so it never crosses configurations that differ
in them. Switch off with `generate(..., fabric_default_only=False)`.

Verified on LN10 (Betwixt): `pos_pval` order = file order = lexical order, **not** numeric; every colour has exactly one relation, a
type precondition, except one withdrawn group (`1=2`, never valid); `is_default` is never set. Result: 432 SKUs (was 254,043), an
exact subset of the old set, every colour the first of its type.

**Not verified:** that pCon itself picks the first valid colour in `pos_pval` order when nothing is flagged. That is the stated
requirement and consistent with the data, but no pCon output for Betwixt was available to compare.

## Removed stale expectations

`max_configurations` is no longer a cap: `generate()` accepts only `None` and raises otherwise. Tests that expected a 500-SKU /
"Stopped at the limit" behaviour were updated to the verified no-cap behaviour.
