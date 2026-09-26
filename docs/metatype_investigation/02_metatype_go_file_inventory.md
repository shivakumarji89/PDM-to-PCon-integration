# 02 — go_*.csv File Inventory

Physical format (**DOCUMENTED FACT**, [MT §2]): one file per table, `go_<tablename>.csv`,
lowercase, UTF-8/ASCII, semicolon (`;`) separated, one record per line, `#`-prefixed lines are
comments, blank lines ignored. Column types: **ID** (alphanumeric+underscore, not starting with a
digit, case-sensitive), **ID_List** (comma-separated IDs), **Text** (Unicode), **Char** (ASCII),
**Int**, **Num**, **NumExpr** (evaluates to Num), **BoolExpr** (evaluates true/false, symbolic
values need `@` prefix in certain tables). **REPOSITORY FACT**: confirmed on disk — every sampled
`go_*.csv` is semicolon-delimited, matches this exactly.

"All tables must be present. Unused tables should be empty." [MT §2] — **REPOSITORY FACT**
confirms this: even unpopulated tables exist as 0-byte files in every built family.

## Master schema table

Column definitions below are **DOCUMENTED FACT** from `MT_1.18.0_en.md`, cross-checked against
each family's own `mt.inp_descr` (**REPOSITORY FACT** — the two agree everywhere checked).
"(obsolete)" = explicitly marked obsolete in the manual.

| Table | Columns | Purpose |
|---|---|---|
| **go_info** | key, value | Series-global control flags: `configuration` (consistent/inconsistent/serial polymorphism-recovery mode), `pindex` (obsolete), `skip_FAN`, `skipVC2MT`, `updateGMode`, `utf8` |
| **go_types** | id, name, format, default, mode, filter | One row per property per metatype. `format` ∈ {ch, chf, chi, f, i, fn, na, th, cp, lb}. `mode` = 14-bit bitmask (editable, global-mod, controls-variant-code, controls-child, invisible, inherited, etc. — full table in file 04). `filter` = comma-list of dependent properties |
| **go_articles** | id, manufacturer, program, article_nr, prm_set(`prm_key` on disk), chprm_set(`chprm_key` on disk) | Binds a metatype `id` to a concrete basic `article_nr`; `prm_key`→go_properties.key, `chprm_key`→go_childprops.key |
| **go_properties** | id, key, name, value, variant_code, variant_value | Property values bound to a `go_articles` parameter-set `key` |
| **go_propindex** (obsolete) | id, key, value1..valueN | Column-oriented alternative to go_properties |
| **go_propmapping** (obsolete) | id, key1..keyN | Column order for go_propindex |
| **go_childprops** | key, name, value, child_key | Property/value combination that creates a sub-position; `child_key`→go_children |
| **go_children** | child_key, manufacturer, program, article_nr, variant, pos_x/y/z, rot_x/y/z, condition | A concrete child article, its position/rotation (NumExpr, parametric), and the BoolExpr condition under which it's attached |
| **go_propvalues** | id, name, value, condition | Per-context value-validity whitelist; **requires mode 8192 on the property in go_types** |
| **go_proporder** | value, number | Explicit sort position for choice-list values; **requires mode 128** |
| **go_noproperties** | key, name (ID_List) | Native properties NOT carried over from the native article |
| **go_inhproperties** | id, pid, property | Explicit inheritance-control entries |
| **go_nativeproperties** | id, pid(or `_ANY`), mode(INCL/EXCL), identifier(or `_ALL`/`_DEFAULT`), value1, value2 | Native-property inheritance filter (algorithm in file 04) |
| **go_resetnativeprops** | id(or `*`), key, trigger(ID_List) | Whether native props reset to commercial defaults on base-article change (not in `mt.inp_descr` schema but present on disk in several families) |
| **go_actions** | id, own_key, foreign_key, direction, condition, action, param_1, param_2, text | The event/action matrix — direction ∈ {CREATE, INI, INS, REM, CON, AP, PROXY, CH_ADD, CH_DEL, INTERACTOR}; action ∈ {SET_PROP, ADD_CHILD, DEL_CHILD, CH_PROP, CON_PROP, CON_CH_PROP, CON_AP, RECREATE_CH, UPDATE_CH_POS} |
| **go_attpt** | id, key, direction, condition, pos_x/y/z, rot_y | Attachment points; special key `_GO_CHILD`; direction ∈ {L,R,F,B,T,D,CH,CH_REL,MP} |
| **go_interactors** (obsolete) | id, type, key, condition, pos_x/y/z, image, hint | SELECT/ACTION/RESIZE/METHOD interactors |
| **go_itemplates** (obsolete) | id(or `*`), template, condition, parameter, pos_x/y/z, rot_y | Predefined geometry templates |
| **go_feedback** (obsolete) | id, ch_artnr, attpt_key, condition, mode, command, parameter | Legacy feedback-mode child creation |
| **go_classes** | id(or `*`), class | Maps metatype id to an OFML Tcl class (must derive from `::ofml::go::GoMetaType`) |
| **go_propclasses** | id(optional), prop_name, prop_class | Property-editor grouping label |
| **go_setup** | id, key, value | Behavior flags — replacement for legacy `GSetup`/`GXSetup` bitmasks (full flag table in file 04) |
| **go_texts** | key, language(optional 2-char), text | i18n label table; language empty = language-independent |
| **go_symbolicpropvalues** | key(or `*`), symbol, number | Symbolic-to-numeric value mapping (new in MT 1.17.3) |
| **go_childmoving** | id, key, condition, mode, command, parameter | Interactive child repositioning rules |
| **go_freenumeric** | name, format(i/f/L/A), minimum, maximum, raster, expr, child, mode | Parametrizes `fn`-format properties |
| **go_metainfo** (obsolete) | id, mode, width/height/depth, condition, value_1, value_2 | AutoDecoration / AccCategory metadata |
| **go_attptgeo** (obsolete) | key, id(optional), pos_x/y/z, rot_dir, rot, type, arg1-3 | Attachment-point geometry rendering |
| **go_attptsorder** | key, id(optional), plandir, number | Processing-order for attachment points |

Obsolete tables (explicitly marked in the manual): `go_propindex`, `go_propmapping`,
`go_metainfo`, `go_feedback`, `go_attptgeo`, `go_itemplates`, `go_interactors`.

## Actual on-disk population (REPOSITORY FACT)

Row counts for the three built families inspected in depth — `0` = declared-but-empty:

| Table | cyclade_Tables | aeron | atlas |
|---|---|---|---|
| go_actions | 4 | 39 | 199 |
| go_articles | 1 (+ commented) | 73 | 73 (+ .bak variant) |
| go_attpt | 0 | 0 | 1 (+ blank lines) |
| go_attptgeo | 0 | 0 | 0 |
| go_attptsorder | 0 | 0 | 0 |
| go_childmoving | 0 | 0 | 0 |
| go_childprops | 2 | 14 | 91 |
| go_children | 1 | 19 | 149 |
| go_classes | 0 | 0 | 0 |
| go_feedback | 0 | 0 | 0 |
| go_freenumeric | 0 | 0 | 5 |
| go_info | 0 | 0 | 0 |
| go_inhproperties | 0 | 0 | 0 |
| go_interactors | 0 | 0 | 0 |
| go_itemplates | 0 | 0 | 0 |
| go_metainfo | 0 | 0 | 0 |
| go_nativeproperties | 0 | 0 | 0 |
| go_noproperties | 0 | 0 | 0 |
| go_propclasses | 4 | 17 | 24 |
| go_properties | 1 | 229 | 73 |
| go_propindex/go_propmapping | 0 | (not present) | 0 |
| go_proporder | 0 | 3 | 13 |
| go_propvalues | 0 | 0 | 55 |
| go_setup | 14 | 22 | 49 |
| go_texts | 40 (4 languages) | 258 | 618 |
| go_types | 22 | 72 | 182 |

**Tables found empty (0 bytes) in every family checked, across the entire repository** — not
just the 6 sampled: `go_attptsorder`, `go_feedback`, `go_info`, `go_inhproperties`,
`go_interactors`, `go_itemplates`, `go_metainfo`, `go_nativeproperties`, `go_noproperties`,
`go_propindex`, `go_propmapping`, plus the non-schema `go_resetnativeprops`. These exist as
declared/reserved slots but hold zero data anywhere sampled in this snapshot. A Metatype workflow
implementation should treat these as "must exist, safe to leave/write empty," not as dead code to
skip creating.

## Anomaly files found on disk (real, not the hypothesized `attptsorder`/`attptsorter` variance)

The task brief hypothesized a `go_attptsorder`/`go_attptsorter` spelling inconsistency — searched
for explicitly (`grep -rl attptsorter` across the whole tree) and **not found**; only
`go_attptsorder` exists anywhere. Real anomalies found instead, cited by exact path:

| Path | Note |
|---|---|
| `betwixt/1/go_texts.csv.new`, `caper/1/go_texts.csv.new`, `em/1/go_texts.csv.new`, `leeway/1/go_texts.csv.new` | staged replacement copies |
| `caper/1/go_texts__new.csv` | second, differently-named staged-replacement variant |
| `civic_tables/1/go_attpt_myne.csv`, `luva/1/go_attpt_myne.csv`, `oe1/1/go_attpt_myne.csv` | non-standard `_myne` suffix |
| `civic_tables/1/go_propvalues_backup_with_old_power_units.csv` | descriptive manual backup |
| `kumi/1/go_{articles,properties,texts,types}_ORIG_MANUAL._sv` | truncated/garbled backup extension |
| `ratio_rebuild/1/go_resetnativeprops_.csv` | trailing underscore |
| `ruby/1/go_texts.zip` | zipped variant alongside the live CSV |
| `para/1/Copy.csv` | no `go_` prefix at all — likely an accidental "Copy of go_????.csv" that lost its prefix |

`.bak` companions exist only for `go_articles`, `go_propclasses`, `go_properties`, `go_setup`,
`go_texts`, `go_types` (in both cyclade_Tables and atlas) — i.e. only for tables that were ever
populated; the always-empty tables never have `.bak` files. A concrete diff of
`cyclade_Tables/1/go_articles.csv` vs. its `.bak` shows `program` changed from `cyclade` to
`cyclade_tables` and `chprm_key` went from empty to populated — real evidence of an in-place
rename + a later-added child relationship, not a guess.

## Supporting non-go_ files (role determined from content, not filename alone)

`mt.inp_descr` (authoritative schema, see above), `<family>.ebase` (compiled DB, built families
only), `odb.ebase`/`ofml.ebase` (geometry/framework DBs, present in ALL families incl. unbuilt),
`ebmkdb.exe` (compiler, identical binary everywhere), `make_ebase.bat` (build script, built
families only), `odb2d.csv`/`odb3d.csv` (geometry-file references + position/rotation, links
go_*-layer choices to actual `.egms`/`.dwg` files by name), `funcs.csv`/`funcs_infix.csv`
(Tcl-like macro definitions used inside odb2d/odb3d expressions), `epdfproductdb.csv` (small
per-family boolean/int flag file, e.g. `@SafePropertyNames;;1`), `.alb`/`.inp_list` files
(geometry-bundle manifests, not opened as binary content), `sbmetatype.cls`/`sbplanning.cls`
(likely Tcl class implementations referenced by `go_classes.class`, not opened),
`go_context.ofml` (shared OFML expression context per the manual [MT §3], present in `symbol/1/`,
not opened this pass).
