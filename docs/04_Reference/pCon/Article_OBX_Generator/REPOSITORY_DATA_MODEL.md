# OCD Repository Data Model (as read by the Article OBX Generator)

**Status:** CURRENT · **Date:** 2026-11-02 · **Scope:** the on-disk OCD repository the standalone generator reads, how its tables connect, and how one selected article becomes an engine `ArticleModel`.

**Evidence:** the real repository `C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx` (102 folders), `pdata.ocd_*.inp_descr` descriptors, `services/ocd_engine/*.py`, and the OCD specification under `docs/04_Reference/pCon/Specifications`. The supplied pCon package contributes **nothing** to this model ([PACKAGE_INVESTIGATION.md](./PACKAGE_INVESTIGATION.md)).

Column meanings below are taken from the descriptor field names and from how `csv_loader` / the engine use them. A column marked **unverified** is read but not interpreted by the generator, or its meaning is not confirmed by data in this project.

---

## 1. Folder layout

```
<root>/                       AppConfig.metatype_repository_root  (…\_repository\hmx)
└── <program>/                one range folder  (e.g. dalby, aeron, lino)
    └── <region>/             ANY, EURO, GBP, NOPRICE, … (see §6)
        └── <version>/        digits only ("1"); highest is used
            └── db/           ocd_*.csv, pdata.ocd_*.inp_descr, pdata.ebase, pdata.inp_descr
```

Survey of the real root (Verified, `find_db_dir` over all folders):

| Fact | Result |
|---|---|
| Folders under the root | 102 |
| Folders with an OCD `db` (`ocd_article.csv` present) | **81** (the other 21 are reported as "skipped" in the catalogue status, never as an error) |
| Table delimiter in every descriptor | `;` — **1,866 of 1,866** table schemas |
| Header row in `ocd_article.csv` | **none** in 81 of 81 (first cell is data) |
| Descriptor field list vs. the 11 built-in default layouts | **identical in all 81 ranges** |
| Tables per range | 22 standard OCD tables in all 81; one range additionally has `article2propgroup`, `propertygroup`, `propgrouptext` |

`db_dir` selection (`catalogue.find_db_dir`): regions sorted with `ANY` first, then alphabetical; within a region the highest numeric version folder that contains `ocd_article.csv`.

## 2. Hierarchy shown to the user

| UI level | Source (Verified) |
|---|---|
| **Manufacturer** | distinct `manufacturer` column of `ocd_article` (e.g. `HM`) |
| **Program** | the range **folder name** under the root (e.g. `dalby`); one folder can hold several manufacturers → one `OcdProgram` per (folder, manufacturer) |
| **Series** | distinct `series` column of `ocd_article` (e.g. `DALBY`); may be empty |
| **Article** | `article_nr`; first row wins for a duplicated number; label = short text of `short_textnr`, language preference `en, en-us, en-gb, de`, else the first language present |

OCD carries **no pCon "variant code"**; the article table's "Variant Code" column therefore always shows `—`.

## 3. File format

- Semicolon-delimited, **no header row**; quote character `"`; the descriptor can override the delimiter.
- ISO-8859-1 (`latin-1`) text; CRLF line ends tolerated.
- Column names/types come from `pdata.ocd_<table>.inp_descr`: tab-separated lines `table <name> <file> mscsv`, `fields <n>`, `field <index> <name> <type> [<size>] delim ; [hidx|link]`. Index/link flags are parsed past, not used.
- Without a descriptor, the OCD 4.3 default layouts in `schema_loader._defaults()` apply (11 tables). The three **text tables have no default**, so a missing descriptor makes their labels empty (never an error).
- Numeric types (`uint…`, `int…`, `float…`) are whitespace-stripped on read; everything else is kept verbatim.

## 4. Tables, columns and relationships

Names are exactly the descriptor field names (Verified against `dalby`; identical layouts in all 81 ranges for the 11 default tables).

| Table (file) | Columns | Purpose / use by the generator |
|---|---|---|
| `article` (`ocd_article.csv`) | `article_nr`, `art_type`, `manufacturer`, `series`, `short_textnr`, `long_textnr`, `rel_obj`, `fast_supply`, `discountable`, `order_unit`, `scheme_id` | Base articles. `rel_obj` → article-level relations (e.g. price relation); `scheme_id` → `codescheme`. `art_type`, `long_textnr`, `fast_supply`, `discountable`, `order_unit`: read, **unused**. |
| `artshorttext` (descriptor only) | `textnr`, `language`, `line_nr`, `line_fmt`, `text` | Short article text. `line_fmt` **unverified/unused**. |
| `propertyclass` | `article_nr`, `pos_class`, `prop_class`, `textnr`, `rel_obj` | Which property classes an article has, in `pos_class` order; class-level relations via `rel_obj`. |
| `property` | `prop_class`, `property`, `pos_prop`, `prop_textnr`, `rel_obj`, `prop_type`, `digits`, `dec_digits`, `need_input`, `add_values`, `restrictable`, `multi_option`, `scope`, `txt_control`, `hint_text_id` | Properties of a class in `pos_prop` order. Used: `prop_textnr` (label), `rel_obj`, `digits` (code length), `need_input` (`""`/`0` ⇒ optional), `restrictable`, `multi_option`, `scope`. `prop_type`, `dec_digits`, `add_values`, `txt_control`, `hint_text_id`: **unused**. |
| `propertyvalue` | `prop_class`, `property`, `pos_pval`, `pval_textnr`, `rel_obj`, `is_default`, `suppress_txt`, `op_from`, `value_from`, `op_to`, `value_to`, `raster`, `date_from`, `date_to` | Values of a property in `pos_pval` order. Enumerable only when `op_from = EQ` and `op_to` empty; others are recorded as `UNSUPPORTED_SYNTAX` (INFO). `value_from` is the value relations see and the code used in encoding. `is_default` is shown in the UI and drives the *Default value* rule. `suppress_txt`, `raster`, `date_from`, `date_to`: **unused** (date validity of values is **not** applied — unverified whether any repository relies on it). |
| `artbase` | `article_nr`, `prop_class`, `property`, `prop_value` | Per-article value restriction. If a (class, property) has rows, only those values are allowed (a missing value is added so a fixed singleton is not lost). |
| `relationobj` | `rel_obj`, `position`, `rel_name`, `rel_type`, `rel_domain` | A relation object groups relations; referenced from article, class, property or value `rel_obj`. `rel_type`: 1 precondition, 2 selection condition, 3 action, 4 constraint, 5 reaction, 6 post-reaction (OCD 2.15). `rel_domain`: `C` (configuration) or `P` (price) as used by the engine. |
| `relation` | `rel_name`, `rel_blocknr`, `rel_block` | Relation source split into numbered blocks; assembled in block order, `*` comment lines removed (`relation_parser.assemble_relation_text`). |
| `codescheme` | `scheme_id`, `scheme`, `varcode_sep`, `value_sep`, `visibility`, `invisible_char`, `unselect_char`, `trim`, `mo_sep`, `mo_bracket` | Final-article encoding (`CodeSchemeEncoder`). Predefined schemes and user-defined strings (`@`, literals, `Class:Property`). |
| `price` | `article_nr`, `var_cond`, `price_type`, `price_level`, `price_rule`, `price_textnr`, `price`, `is_fix`, `currency`, `date_from`, `date_to`, `scale_quantity`, `rounding_id` | Price rows (`price_type` `S` = sales, `P` = purchase; `price_level` `B` base, `X` extra charge, `D` discount — the *level* is the `B`, not the type). Rows are keyed by `article_nr` (or the joker `*` for article-independent `X`/`D` rows) and by `var_cond`, a variant condition the price relations assign to `$VARCOND`. See §5a for the three layouts found in the real repository. `D` is applied from the spec text only; flagged unverified. |
| `propertytext`, `propvaluetext` (descriptor only) | `textnr`, `language`, `line_nr`, `line_fmt`, `text` | Property and value labels. |
| `rounding` | `id`, `nr`, `min`, `max`, `type`, `precision`, `add_before`, `add_after` | Present but **not used** by the generator (see Limitations). |
| `version` | `format_version`, `rel_coding`, `data_version`, `date_from`, `date_to`, `region`, `varcond_var`, `placeholder_on`, `tables`, `comment` | Read-only metadata; not interpreted. Dalby: `4.2;OCD_4;1.34.7;20200106;99991231;ANY;;0;<22 tables>;`. |
| `articletaxes`, `artlongtext`, `classification`, `packaging`, `pricetext`, `propclasstext`, `prophinttext`, `taxscheme`, `usermessage` | — | Present; **not read**. |

### Relationship diagram

```
article ──scheme_id──────────────▶ codescheme
   │ └─rel_obj──┐
   │            ▼
   ├─article_nr▶ propertyclass ──prop_class──▶ property ──(prop_class,property)──▶ propertyvalue
   │              │ rel_obj ┐                    │ rel_obj ┐                         │ rel_obj ┐
   │              ▼         │                    ▼         │                         ▼         │
   │          relationobj ◀─┴────────────────────┴─────────┴─────────────────────────┴─────────┘
   │          (rel_obj ▶ rel_name)
   │                │
   │                ▼
   │             relation (rel_name ▶ blocks ▶ text)
   ├─article_nr▶ artbase  (restricts propertyvalue per article)
   └─article_nr▶ price    (var_cond keys come from $VARCOND assigned by relations)
text tables: artshorttext(short_textnr) · propertytext(prop_textnr) · propvaluetext(pval_textnr)
```

## 5. From a selected article to the engine

For `article_nr = A` (`build_article_model`, then `OcdArticleGenerator`):

1. `article[A]` → identity, `scheme_id`, article relations (`rel_obj`).
2. `propertyclass` rows of `A`, sorted by `pos_class` → `ClassDef`s (class relations via `rel_obj`).
3. For each class, `property` rows sorted by `pos_prop` → `PropertyDef` (`key = "<class>:<property>"`), flags from §4.
4. For each property, `propertyvalue` rows sorted by `pos_pval`, `op_from = EQ` only → `ValueDef(value = value_from, relations = …)`.
5. `artbase` rows of `A` → `allowed_keys` (restriction) per property.
6. Relations: `rel_obj` → `relationobj` rows → `relation` blocks → `RelationRef(name, rel_type, domain, order, text)`.
7. **Enumeration** (`ConfigurationEngine`): dependency-ordered depth-first search; a value is offered only if its precondition is not definitely FALSE; a property whose own/class precondition is FALSE is *hidden*; constraints are checked as soon as their inputs are chosen; `finalize` re-verifies the complete configuration, runs actions (computed properties, `$VARCOND`).
8. **Final article** = `CodeSchemeEncoder.encode(A, view)` with the scheme of step 1.
9. **Price** = `PriceCalculator.price(A, varconds, price_date, currency, factors)`.
10. **`ofmlvarcode`** = `ofml_varcode(assignments, model)`: scope-`C` properties that currently have a value, in class/property order, as `Class.Property=Value;…` (matches 1,242 Dalby / 2,352 Lino pCon-resolved articles; the equivalence *scope C ⇔ configurable* is a hypothesis beyond those two programs).

User rules (UI → `PropertyRule`): *Vary* (default), *Fixed value* (restrict the property to one value), *Default value* (restrict to the `is_default` value). A rule only narrows the value list — relations and constraints are still evaluated, and if the pinned value is excluded by the data the configuration is rejected (counted as *invalid*) instead of being emitted with the property unassigned.

## 5a. Price lookup (verified against pCon reference prices)

`PriceCalculator.price(article, varconds, price_date, currency, factors)` looks up, per price level (`B`, `X`, `D`), one row for each key in `["", *varconds]`: the article's own rows with that `var_cond` (for `X`/`D` the joker `*` rows only if the article has none for that key), then keeps the rows that are fixed amounts (base only), valid on the price date, of scale quantity ≤ 1 and in the requested currency, and takes the latest `date_from`. A price in another currency is never substituted. `varconds` and the `$SET_PRICING_FACTOR` multipliers are what the engine's price relations assigned for the configuration (`GeneratedSku.varconds`, `.pricing_factors`).

The real repository holds three layouts (counted over the 81 programs' sales-type `B` rows; a program can mix layouts across its articles):

| Layout | Example row | Programs | Price of a configuration |
|---|---|---|---|
| Base without condition | `NODLE100;;S;B;;;1243;1;EUR;20260406;99991231;1;` | 11 use only this (Dalby, Em, Hudson, Percy, Pronta, Riley, Sweep, Viv …) | the `B` row + the `X` rows of the assigned conditions |
| Base **keyed by a variant condition** | `AER1A11;AF;S;B;;;2187;1;EUR;20260406;99991231;1;` | 46 use only this (Accessories, Ali, Bevel, Cosm, Bound Screens …); 21 mix it with the plain form (Aeron, Atlas, Pullman, Nevi …) | the `B` row(s) of the assigned conditions (usually one) + the `X` rows |
| **No base row** for the article (price is `X` rows, usually under the joker `*`) | `*;GEBR.12;S;X;;000000000000130313;74;1;GBP;20260406;20260906;1;` | 3 have no `B` row at all (Bay Work Pod, Civic Tables, Everywhere); individual articles of many more (Layout Studio, Atlas, Nevi, Bound Screens, Oe1 …) | the sum of the `X` rows of the assigned conditions |

The earlier code required an unconditioned `B` row and reported every other article as `no usable B price row for key (none)`, although the rows exist under other keys. Now:

* any `B` item found, keyed or not, is the base (`PriceResult.base` is their sum); percentage extra charges are relative to it;
* an article with **no `B` row of its own in any currency or date** is priced as the sum of the `X` items that matched, with an INFO diagnostic `PRICE_FROM_EXTRA_CHARGES` — only if at least one item matched and the sum is not zero;
* an article that **has** `B` rows but none applies stays unpriced, and the message names the first filter that emptied the list (no row for the key / only percentages / no window containing the date, listing the windows / no row in the currency, listing the currencies valid then / the base prices are keyed by other conditions, listing them).

Evidence: for Layout Studio the live repository reproduces **all 1,295 prices** of three pCon.planner exports (`Layout_MeetingTables_BasicQA_GBP` 67, `Layout_B2B_Desk_Extension_All_Euro` 331, `Layout_Single_Primary_Melamine_Euro_OLD` 897) to the cent, with the same seven (etc.) price components. For Bay Work Pod and Lino the component keys equal pCon's one for one, but the staging `ocd_price.csv` (written 1 July) is 2–5 % below the price list pCon used in July–September, so amounts cannot be compared there. Dalby's 1,242 references still pass.

**Reported failure `500 without price … no usable B price row for key (none) on 20261102 in EUR` — root cause (verified).** It was accessories / `NOCUS` (the figures 500 SKUs, 1017 nodes, 38852 pruned reproduce exactly). All 12 `S`/`B` rows of `NOCUS` are keyed by `var_cond` `1` (`NOCUS;1;S;B;;;162;1;EUR;20260406;99991231;1;`); there is no unconditioned B row. The price calculator at commit `58157b4` looked only for the key `(none)`, so it rejected every SKU although the relation-derived key `1` has a valid EUR row. The calculator now looks up every derived key and prices the first SKU `NOCUS1 1HA01` at **162.00 EUR** (test `test_live_nocus_generation_prices_every_sku_and_the_obx_agrees`). Genuinely unpriced articles remain unpriced: e.g. para `FN2CC.` has B rows only for 2021–2022 and its price relation emits keys (`FNACC.0804M`) that match no row. The reason now names both the assigned keys and the keys the article holds.

### Two price sources and how they combine

The "two methods" are not alternatives. Both read the same `ocd_price.csv` and are summed level by level (spec 3.1, 3.2); `PriceCalculator.price` implements exactly this.

| | Method A - rows of the article itself | Method B - rows reached through price relations (`$VARCOND`) |
|---|---|---|
| Row key | `article_nr` = the base article; `var_cond` empty, or a condition the article's own relations assign (NOCUS: `var_cond=1`) | `$VARCOND` values assigned by the article's / class's / property's / value's price relations (`rel_domain` `P`, type 3); rows under the article, or under the joker `*` for `X`/`D` |
| Levels | `B`, `X`, `D` | `B` (own rows only), `X`, `D` (own or joker) |
| Evidence | Dalby 1,242 reference articles exact; NOCUS (no pCon reference, repository row only) | Layout Studio 1,295 prices of three pCon exports exact, joker `*` `X` rows and `$SET_PRICING_FACTOR` |

Rules - **confirmed by the OCD 4.3 text and by the exact parity above**
1. Lookup keys = `""` plus every assigned `$VARCOND` (upper-cased). Each key is looked up per level B, X, D; totals accumulate in that order. Direct and relation-keyed items **both contribute**; neither overrides the other.
2. A joker `*` row is used only for `X`/`D` with a non-empty key **and only if the article has no row of its own for that key**. A joker row is never a base price.
3. Inside one (level, key): base rows must be fixed amounts; then date window, scale quantity <= order quantity, requested currency; the latest `date_from` wins; same-date rows with different values raise `AMBIGUOUS_PRICE_WINDOW`.
4. Price type `S` and `P` are separate lookups (generator uses `S`).
5. Percentage `X` rows are a percentage of the accumulated base; `$SET_PRICING_FACTOR` multiplies the item of its key.

Rules - **implementation choices, not spec** (kept deliberate)
* No currency fallback (spec 3.3 would fall back to all currencies; the generator reports the SKU unpriced instead).
* An article that has `B` rows but none applicable is unpriced even if `X` rows match; extra charges are never a stand-in for a missing base. An article with **no** `B` row at all is priced from its `X` sum (sum must be non-zero) with an INFO diagnostic.

Not established (left unchanged, no fallback invented)
* Discounts (`D`): no reference export contains one; applied from the spec text only and flagged `UNSUPPORTED_PRICE_FEATURE`.
* The spec leaves undefined whether a `$VARCOND` assigned by several relations is charged once or per relation.
* Region price lists (`EURO`/`GBP` vs `ANY`), and repository prices that are 2-5 % below a newer pCon export (Bay Work Pod, Lino): price freshness, not a calculation difference (the staging file predates the export).

**Price Diagnostics…** (button next to *Export OBX*) calls `OcdArticleGenerator.price_diagnostics`: repository folder, price file and rows loaded, the types/levels/currencies/date windows the table holds for the article (own and joker rows), the keys derived for the SKU, and per key the candidate count after each filter with the rejection reason. It never lists the table.

## 6. Open points (Not verified)

- **Regions.** `dalby` has `ANY`, `EURO`, `GBP`, `NOPRICE`. `ANY`'s price file has as many lines as `EURO` + `GBP`; the generator reads `ANY` only and offers the currencies found in its price table. Whether pCon would show a different price/article set per region is not verified here (see memory note on OCD price-list visibility).
- **Value validity dates** (`propertyvalue.date_from/date_to`) are not applied.
- **`rounding` table** is not loaded into `PriceCalculator`; the default commercial rounding is used (same as the existing repository Article OBX).
- **Multi-option properties** (`multi_option = 1`): the flag is carried into the model, but the enumerator offers one value at a time; multi-selection encoding is not exercised by the generator.
- **Reactions / value-set restriction / scale and percent prices / discounts**: unsupported or spec-only — surfaced as warnings (`docs/02_Domain/OBX/OCD_Engine.md`).
- Descriptor flags `hidx`/`link` and the compiled `pdata.ebase` are ignored.
