# Metatype

**Status:** Forensic investigation findings, consolidated from 8 prior investigation-session
documents; workflow/design sections are PROPOSED and unimplemented unless stated otherwise.

This document is a companion to, and does not duplicate, the OCD/XOCD/MDB/EBASE-focused
`Article_Encoding` and repository docs elsewhere in `docs/02_Domain/` — it never mentions
Metatype or any `go_*` table (confirmed by cross-check during the original investigation). The
Metatype/`go_*` table family is a structurally distinct domain, native to the OFML `hmx`
repository, and is documented here on its own terms.

**Evidentiary labeling** (carried over from the original investigation and preserved throughout
this document so the strength of each claim stays visible):
- **DOCUMENTED FACT** — stated in `MT_1.18.0_en.md` (OFML Metatype spec, v1.18.0, EasternGraphics), section cited.
- **PROJECT PROCESS FACT** — stated in the polymorphic-creation template or Verus prompt, doc cited.
- **REPOSITORY FACT** — observed directly in `hmx\*` files, path/values cited.
- **CODE FACT** — observed directly in this repo's `.py` files, file:line cited.
- **INFERENCE** — logically derived, reasoning given.
- **UNKNOWN** — gap explicitly flagged, not silently resolved.

**Sources originally read in full**, three parallel investigation legs:
1. **Manual + process docs** — `MT_1.18.0_en.md` (OFML Metatype spec, v1.18.0, 3977 md lines /
   47 pages, EasternGraphics), `POLYMORPHIC_METATYPE_CREATION_TEMPLATE_04092026.md`,
   `Verus_Metatype_Prompt_TEST.md`, `oap_metatype2type.csv`, `Metatype-Inspector_3.0_History_EN.pdf`.
2. **hmx repository** — `C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx` (14 GB),
   102 directories inspected structurally, 6 families inspected in file-content depth
   (cyclade_Tables, aeron, atlas built; comma, knot, hush unbuilt).
3. **Existing codebase** — `C:\01 Projects\mk_product_workbench` (branch `main`), full grep
   sweep + targeted reads of `services/mdb_service.py`, `services/mdb_reverse_engineering_service.py`,
   `models/snapshot.py`, `services/engineering/*`, plus a cross-check against the OCD-focused
   investigation tree. **Discovery made during this leg**: the repo already contained a substantial
   internal reference chapter, `docs/04_Reference/Engineering_Reference/10_Metatype.md` (plus
   `13_Naming_Standards.md`, `14_Generation_Process.md`, `15_File_Formats.md`, and a vendor spec
   reprint `docs/04_Reference/pCon/Specifications/MT_1.18.0_en.md`). That handbook was treated as prior documentation
   to cross-check, not as ground truth — every claim below was independently re-derived from the
   manual/repository/code and labeled per the convention above.

---

## 1. Purpose and Scope

### 1.1 What a Metatype is

**DOCUMENTED FACT** [MT §go_types intro]: "The table go_types defines the metatypes or metatype
instances of a manufacturer. Such a metatype represents a set of article numbers defined in the
table go_articles." I.e. **Metatype = an abstract, configurable product type**; a manufacturer
binds it to concrete article numbers via `go_articles`.

**DOCUMENTED FACT** [MT §1]: The Metatype concept enables two things beyond plain graphic-data
modeling:
(a) **configuration on inter-product level** — a property change that swaps the *basic article
number itself* (not just intra-product properties), e.g. switching program/collection;
(b) concatenation/attachment rules for child parts, described by properties in an
article-dependent way.

### 1.2 "Polymorphic Metatype" — project terminology, not spec terminology

**The phrase "Polymorphic Metatype" never appears anywhere in `MT_1.18.0_en.md`.** It is
MillerKnoll project terminology (used in `POLYMORPHIC_METATYPE_CREATION_TEMPLATE_04092026.md`)
for what the manual calls **article polymorphism** — mechanism (a) above. The project doc's own
Step 2 in fact distinguishes two patterns, both loosely called "polymorphic Metatype work" in
practice:

1. **"Polymorphism Metatype"** — articles switch/swap via a Metatype property, no parent/child
   structure. Maps to the manual's article-polymorphism mechanism: a mode-4 ("controls the
   variant code") `ch`/`chi` property, `go_info.configuration` (series-wide
   consistent/inconsistent/serial recovery behavior), and `go_propvalues`/`go_actions` gating
   which values are valid/visible per active article.
2. **"Metatype with Childs"** — a parent metatype attaches/controls child articles. Maps to
   mode-8 ("controls a sub-item/child") properties driving the
   `go_articles → go_childprops → go_children` chain (§4 below).

**Status: FOUND.** Both patterns are exercised together in the worked
`Verus_Metatype_Prompt_TEST.md` example (parent-article switching among PIA1Z/PIA2Z/PIA4SZ/PIA7Z
AND a conditionally-attached `CH_Headrest` child) — see §6.

### 1.3 Scope of this investigation

This investigation covers the `go_*` table family (the OFML "Metatype" mechanism) exclusively: its
physical file format, confirmed data relationships, the manual↔repository↔code concept mapping, a
reconstructed creation workflow, a proposed (unimplemented) Python workflow, and a validation plan
for that proposed workflow. It is a companion to — and does not duplicate — the existing
OCD/XOCD/MDB/EBASE-focused documentation elsewhere in `docs/02_Domain/` (Article Encoding,
Property Model, Relation Model, Dependency Model, Repository/OBX docs), which never reference
Metatype or any `go_*` table.

**No production code was changed, no branch created, nothing committed** during the original
investigation. It was read-only and evidence-only throughout.

---

## 2. Repository Structure Findings

Root: `C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx` (14 GB). **REPOSITORY FACT**
throughout unless noted; read-only investigation, nothing modified.

### 2.1 Root listing

112 entries total: **102 directories + 10 loose files**.

Loose files at root (not product families): `green.jpg`/`green.mat`, `ground.jpg`/`ground.mat`
(shared material/texture pair), `basics.7z` (~809 MB, presumably packages the `basics`/`basicsn1`
shared geometry family), `REP_symbol.7z` (~39 MB, likely a packaged export of `symbol`),
`basics_readme.txt`, `input.txt` (130 KB, not opened), `summary.txt` (128 KB, not opened),
`release_summary_SVN.bat` (SVN release/export driver, not opened in depth).

Of the 102 directories:
- **`dlm`** is completely empty (no subfolders at all).
- **`catalogue`** and **`info`** are NOT product families — they use a different internal layout
  (`<currency>/1/...` — ANY/EURO/GBP/NOPRICE) holding catalog-price exports and marketing
  documents (.docx/.pdf), no `go_*` files anywhere.
- **`symbol`** is a genuine product family (has `go_*` files) that *also* carries the same
  currency/catalog side-structure as catalogue/info.
- All other **99 directories** are real product families, each following the same skeleton:
  `<family>/1/` (real OFML data + geometry) plus `<family>/{ANY,EURO,GBP,NOPRICE}/1/`
  (currency/catalog-price variant exports) — confirmed directly on 6 sampled families
  (cyclade_Tables, aeron, comma, atlas, knot, hush; all five show exactly this five-subfolder
  shape).

### 2.2 Built vs. unbuilt families — the key structural finding

**Only 53 of the ~99 real family folders have actually been "compiled"**: populated `go_*.csv`
files, a family-specific `<family>.ebase`, and a `make_ebase.bat`. The other ~48 (including
`comma`, `knot`, `hush` — three of the six families sampled) contain **only geometry**
(`.dwg`/`.egms`/`.geo`/`.obj`/`.vnm`), the shared `odb.ebase`/`ofml.ebase`, `.inp_descr` schema
files, `funcs.csv`, and an **empty** `attpt.csv` — zero `go_*.csv` files, no family `.ebase`, no
build script. This means: geometry/CAD authoring exists for these ~48 families but the
product-logic (Metatype) layer has not yet been authored for them in this snapshot.

Full per-family table (`go_count` = number of `go_*`-prefixed files present in `<family>/1/`,
including `.bak`/variant files; `family_ebase` = 1 if `<family>/1/<family>.ebase` exists):

| Family | go_count | ebase | Family | go_count | ebase |
|---|---|---|---|---|---|
| Bolster | 0 | 0 | mimo | 25 | 1 |
| accessories | 8 | 0 | mirra_refresh | 32 | 1 |
| aeron | 25 | 1 | morse_tables | 34 | 1 |
| ali | 0 | 0 | morse_tables_accessories/byo/rectangle/round/work | 0 | 0 |
| always | 0 | 0 | nelson_lamps | 28 | 1 |
| atlas | 33 | 1 | nevi_enhanced | 27 | 1 |
| atlas_storage | 27 | 1 | oe1 | 28 | 1 |
| basics / basicsn1 | 0 | 0 | oe1_boundary/micropacks/storage/tables/workbox | 0 | 0 |
| bay_work_pod | 32 | 1 | oe1_sit_stand_tables | 27 | 1 |
| betwixt | 29 | 1 | para | 30 | 1 |
| bevel | 28 | 1 | passport | 27 | 1 |
| bound_screens | 27 | 1 | penny_stools | 27 | 1 |
| capelli | 0 | 0 | percy / pinch / pippin_chair / portrait / pronta | 0 | 0 |
| caper | 30 | 1 | polly | 27 | 1 |
| chadwick_module | 34 | 1 | power_units | 27 | 1 |
| civic_tables | 30 | 1 | pullman | 27 | 1 |
| civic_tables_oval/round/soft_square/square_rectangular/teardrop_trapezoid | 0 | 0 | pullman_modular | 0 | 0 |
| comma | 0 | 0 | ratio_rebuild | 26 | 1 |
| cosm | 25 | 1 | revive | 25 | 1 |
| crosshatch | 29 | 1 | rhyme / riley | 0 | 0 |
| cyclade_Tables | 33 | 1 | ruby | 28 | 1 |
| dalby | 29 | 1 | saiba | 34 | 1 |
| dlm | (empty) | — | sayl | 0 | 0 |
| em | 30 | 1 | scissor_chair | 27 | 1 |
| ever / everywhere | 0 / 24 | 0 / 1 | setu_refresh | 27 | 1 |
| fin | 0 | 0 | sideboard / sled_chair / spot_stool | 0 | 0 |
| fold | 27 | 1 | striad | 33 | 1 |
| hatch | 27 | 1 | sweep | 27 | 1 |
| hudson / hue / hush | 0 | 0 | symbol | 27 | 1 |
| knot | 0 | 0 | taper | 0 | 0 |
| kumi | 32 | 1 | tier | 26 | 1 |
| lasso | 0 | 0 | trace / truffle / tuxedo | 0 | 0 |
| layout_studio | 28 | 1 | tun | 27 | 1 |
| leeway | 28 | 1 | verus | 27 | 1 |
| lino / lotti | 0 | 0 | viv | 31 | 1 |
| luva | 30 | 1 | wilkes / wireframe | 0 | 0 |
| | | | zeph | 26 | 1 |

53 built, 48 unbuilt (+ `dlm` empty, `catalogue`/`info` non-product) = 102.

### 2.3 Build toolchain (how a family goes from unbuilt to built)

Not documented in the manual at all (see §5.5); recovered empirically:

1. **`mt.inp_descr`** ("GO III (MT) Input Description, Version 1.16", EasternGraphics) — the
   authoritative field-level schema for every `go_*.csv` table, present in every family folder
   (built or not). This is the source used for every column list in §3.
2. Author/edit the `go_*.csv` files by hand per that schema.
3. **`ebmkdb.exe`** (identical 49,152-byte binary, copied into every family folder) compiles
   `mt.inp_descr` + the `go_*.csv` files into a family-specific `<family>.ebase` (binary compiled
   database).
4. **`make_ebase.bat`** — a 10-line batch script that invokes
   `ebmkdb.exe mt.inp_descr <family>.ebase`. Only present in built families; its absence in
   comma/knot/hush is consistent with those families never having been compiled.
   **PROJECT PROCESS FACT** [Verus_Metatype_Prompt_TEST.md]: run `ebmkdb.exe` directly rather
   than `make_ebase.bat`, because the `.bat` contains a blocking `pause` that hangs non-interactive
   execution; success = exit code 0 + a fresh timestamp on the output `.ebase`.

Two other compiled databases exist **independent of the go_* layer** and are present even in
unbuilt families: `odb.ebase` (geometry/attachment-point/2D-3D object database, built from
`odb.inp_descr`) and `ofml.ebase` (base OFML framework metadata). Neither is Metatype-specific.

### 2.4 Not verified / not opened

`input.txt`, `summary.txt` (root), `.dwg`/`.egms`/`.geo`/`.vnm`/`.obj`/`.alb` binary geometry
content, `odb2d_infix.csv`/`odb3d_infix.csv` content, `sbmetatype.cls`/`sbplanning.cls`,
`go_context.ofml` (present in `symbol/1/`, not part of the `mt.inp_descr` schema, origin
unconfirmed), `basics.7z`/`REP_symbol.7z` archive contents, `catalogue`/`info` subfolder contents
beyond one level. Flagged, not guessed.

---

## 3. `go_*.csv` Physical File Format Inventory

### 3.1 Physical format

**DOCUMENTED FACT** [MT §2]: one file per table, `go_<tablename>.csv`, lowercase, UTF-8/ASCII,
semicolon (`;`) separated, one record per line, `#`-prefixed lines are comments, blank lines
ignored. Column types: **ID** (alphanumeric+underscore, not starting with a digit, case-sensitive),
**ID_List** (comma-separated IDs), **Text** (Unicode), **Char** (ASCII), **Int**, **Num**,
**NumExpr** (evaluates to Num), **BoolExpr** (evaluates true/false, symbolic values need `@`
prefix in certain tables). **REPOSITORY FACT**: confirmed on disk — every sampled `go_*.csv` is
semicolon-delimited, matches this exactly.

"All tables must be present. Unused tables should be empty." [MT §2] — **REPOSITORY FACT**
confirms this: even unpopulated tables exist as 0-byte files in every built family.

### 3.2 Master schema table

Column definitions below are **DOCUMENTED FACT** from `MT_1.18.0_en.md`, cross-checked against
each family's own `mt.inp_descr` (**REPOSITORY FACT** — the two agree everywhere checked).
"(obsolete)" = explicitly marked obsolete in the manual.

| Table | Columns | Purpose |
|---|---|---|
| **go_info** | key, value | Series-global control flags: `configuration` (consistent/inconsistent/serial polymorphism-recovery mode), `pindex` (obsolete), `skip_FAN`, `skipVC2MT`, `updateGMode`, `utf8` |
| **go_types** | id, name, format, default, mode, filter | One row per property per metatype. `format` ∈ {ch, chf, chi, f, i, fn, na, th, cp, lb}. `mode` = 14-bit bitmask (editable, global-mod, controls-variant-code, controls-child, invisible, inherited, etc. — full table in §5.2). `filter` = comma-list of dependent properties |
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
| **go_nativeproperties** | id, pid(or `_ANY`), mode(INCL/EXCL), identifier(or `_ALL`/`_DEFAULT`), value1, value2 | Native-property inheritance filter (algorithm in §5.3) |
| **go_resetnativeprops** | id(or `*`), key, trigger(ID_List) | Whether native props reset to commercial defaults on base-article change (not in `mt.inp_descr` schema but present on disk in several families) |
| **go_actions** | id, own_key, foreign_key, direction, condition, action, param_1, param_2, text | The event/action matrix — direction ∈ {CREATE, INI, INS, REM, CON, AP, PROXY, CH_ADD, CH_DEL, INTERACTOR}; action ∈ {SET_PROP, ADD_CHILD, DEL_CHILD, CH_PROP, CON_PROP, CON_CH_PROP, CON_AP, RECREATE_CH, UPDATE_CH_POS} |
| **go_attpt** | id, key, direction, condition, pos_x/y/z, rot_y | Attachment points; special key `_GO_CHILD`; direction ∈ {L,R,F,B,T,D,CH,CH_REL,MP} |
| **go_interactors** (obsolete) | id, type, key, condition, pos_x/y/z, image, hint | SELECT/ACTION/RESIZE/METHOD interactors |
| **go_itemplates** (obsolete) | id(or `*`), template, condition, parameter, pos_x/y/z, rot_y | Predefined geometry templates |
| **go_feedback** (obsolete) | id, ch_artnr, attpt_key, condition, mode, command, parameter | Legacy feedback-mode child creation |
| **go_classes** | id(or `*`), class | Maps metatype id to an OFML Tcl class (must derive from `::ofml::go::GoMetaType`) |
| **go_propclasses** | id(optional), prop_name, prop_class | Property-editor grouping label |
| **go_setup** | id, key, value | Behavior flags — replacement for legacy `GSetup`/`GXSetup` bitmasks (full flag table in §5.4) |
| **go_texts** | key, language(optional 2-char), text | i18n label table; language empty = language-independent |
| **go_symbolicpropvalues** | key(or `*`), symbol, number | Symbolic-to-numeric value mapping (new in MT 1.17.3) |
| **go_childmoving** | id, key, condition, mode, command, parameter | Interactive child repositioning rules |
| **go_freenumeric** | name, format(i/f/L/A), minimum, maximum, raster, expr, child, mode | Parametrizes `fn`-format properties |
| **go_metainfo** (obsolete) | id, mode, width/height/depth, condition, value_1, value_2 | AutoDecoration / AccCategory metadata |
| **go_attptgeo** (obsolete) | key, id(optional), pos_x/y/z, rot_dir, rot, type, arg1-3 | Attachment-point geometry rendering |
| **go_attptsorder** | key, id(optional), plandir, number | Processing-order for attachment points |

Obsolete tables (explicitly marked in the manual): `go_propindex`, `go_propmapping`,
`go_metainfo`, `go_feedback`, `go_attptgeo`, `go_itemplates`, `go_interactors`.

### 3.3 Actual on-disk population (REPOSITORY FACT)

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

### 3.4 Anomaly files found on disk

The original task brief hypothesized a `go_attptsorder`/`go_attptsorter` spelling inconsistency —
searched for explicitly (`grep -rl attptsorter` across the whole tree) and **not found**; only
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

### 3.5 Supporting non-go_ files

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

---

## 4. Confirmed Data Relationships

All relationships below are **REPOSITORY FACT** — confirmed by literal string matches on values
actually read from the CSVs (cited by exact file/family), not inferred from column-name
similarity alone. Source family unless noted: `cyclade_Tables/1` and `atlas/1`.

### 4.1 Confirmed relationship table

| Source File | Source Key | Target File | Target Key | Meaning | Evidence |
|---|---|---|---|---|---|
| go_articles | `prm_key` (e.g. `CFG_FE1L`) | go_properties | `key` | article's standard-property parameter set | `cyclade_Tables/1`: `go_articles` row `...;FE1L;CFG_FE1L;CHP_FE21` ↔ `go_properties` row `MT_CYCLADE;CFG_FE1L;GTABLE_Type;Cyclade_Table_Low;;` |
| go_articles | `chprm_key` (e.g. `CHP_FE21`) | go_childprops | `key` | article's child-property parameter set | same rows as above |
| go_childprops | `child_key` (e.g. `CH_FE21`) | go_children | `child_key` | which concrete child article this value creates | `go_childprops` row `CHP_FE21;GGLASS_BOWL;GLASS_BOWL_YES;CH_FE21` ↔ `go_children` row `CH_FE21;hmx;cyclade_tables;FE21;...` |
| go_properties/go_types/go_propclasses | `name` / `prop_name` | go_texts | `key` | i18n label lookup | `GTABLE_Type`, `Cyclade_Table_Low`, `GGLASS_BOWL`, `GLASS_BOWL_YES`, `GLASS_BOWL_NO` all present as both property/value identifiers AND as `go_texts.key` rows (en/de/fr/nl) |
| go_attpt | `pos_x`/`pos_z` NumExpr (e.g. `GATLAS_OffsetX * 0.001`) | go_freenumeric | `name` | attachment-point position parametrized by a free-numeric property | `atlas/1/go_attpt.csv` references `GATLAS_OffsetX`/`GATLAS_OffsetZ`; `atlas/1/go_freenumeric.csv` declares exactly those two names |
| go_propvalues | `condition` `@Token` references | go_proporder | `value` | value-validity condition branches on a value that also has a declared sort position | `atlas/1/go_propvalues.csv` conditions reference `@ATLAS_Type_SG/_PT/_CR/_SA/_PR/_ME/_CL/_TP` (8 tokens); `atlas/1/go_proporder.csv` enumerates exactly those 8 values — 8/8 matched |
| go_types / go_articles / go_setup / go_propclasses | `id` (metatype id, e.g. `MT_CYCLADE`) | (shared join key, not a separate target file) | `id` | unifies every table describing one metatype | same `MT_CYCLADE` (and sibling `MT_CYCLADE_B`) appears as column 1 in all four tables in `cyclade_Tables/1` |
| go_classes | `id` | go_types | `id` | maps metatype to implementing OFML class | `layout_studio/1/go_classes.csv`: `MT_LS_Desk;::hmx::layout_studio::lsMetaType` — id matches a `go_types.id` |
| go_articles.csv vs. go_articles.csv.bak | `program` column | — | — | evidences a family rename over time | `.bak`: `program=cyclade`, empty `chprm_key`; live: `program=cyclade_tables`, populated `chprm_key` — direct field diff, not inferred |

### 4.2 Primary / foreign identifiers, by role

- **Primary identifiers**: `go_types.id` + `go_types.name` (metatype id + property name, one row
  per pair) is the master key for property definitions. `go_articles.id` + `go_articles.article_nr`
  is the master key for concrete articles (both indexed per `mt.inp_descr`).
- **Foreign identifiers**: `go_articles.prm_key`/`chprm_key` (→ go_properties/go_childprops),
  `go_childprops.child_key` (→ go_children), property `name`/value identifiers (→ go_texts.key,
  go_propvalues.name, go_proporder.value, go_types.filter entries).
- **Parent/child relationships**: realized through the `go_articles→go_childprops→go_children`
  chain (a value assigned to a child-controlling property, mode bit 8, creates/attaches a
  concrete child article) — this is structurally distinct from OCD's `tCOMd_RelObj`/`Relation`
  relation-object model used elsewhere in this codebase (see §7.3g).
- **Article/class relationships**: `go_classes.id → go_types.id`, binding a metatype to its OFML
  implementing class (defaults to `::ofml::go::GoMetaType` if no row exists).
- **Property/value relationships**: `go_types.name` (property) ↔ `go_propvalues.name`/`value`
  (validity restriction, gated by mode 8192) ↔ `go_proporder.value` (display order, gated by mode
  128) ↔ `go_texts.key` (label).
- **Template relationships**: `go_itemplates.id/template` (obsolete, always empty in this
  snapshot) — no evidence any current family uses ITemplates.
- **Inheritance relationships**: `go_inhproperties.id/pid/property` (explicit inherit-from-ancestor
  entries) and `go_nativeproperties.id/pid/mode/identifier` (native-property inclusion/exclusion
  filter, resolution algorithm documented in §5.3) — both **always empty** in this repository
  snapshot (§3.3), so no concrete on-disk example of either mechanism exists to cross-check
  against the manual's algorithm.
- **Geometry-related relationships**: `go_attpt.pos_*`/`rot_y` NumExpr fields reference
  `go_freenumeric.name` identifiers (confirmed, atlas); `odb2d.csv`/`odb3d.csv` (non-go_* files)
  separately link geometry-choice rows to actual `.egms`/`.dwg` filenames — this is a **different,
  lower ("ODB") layer**, not part of the go_* schema itself, and should not be conflated with it.
- **Metadata relationships**: `go_setup.id → go_types.id` (per-metatype behavior flags),
  `go_propclasses.id/prop_name → go_types.id/name` (property-editor grouping).
- **Polymorphic relationships**: no separate "polymorphism table" exists — polymorphism is
  realized entirely through the ordinary tables above (mode-4/mode-8 flags on `go_types` rows,
  `go_propvalues` gating, `go_actions` CON_PROP/SET_PROP rows) rather than a dedicated schema
  construct. See §5.1 and §6.

### 4.3 What was NOT found

- No relationship evidence at all for the always-empty tables (`go_inhproperties`,
  `go_nativeproperties`, `go_propindex`, `go_propmapping`, `go_metainfo`, `go_feedback`,
  `go_attptgeo`, `go_interactors`, `go_itemplates`, `go_resetnativeprops`) — their FK behavior as
  documented in the manual (§3.2, §5.3) is **DOCUMENTED FACT only, not REPOSITORY FACT** — no live
  example exists anywhere sampled to confirm it operates as described.
- `go_childmoving` was found non-empty only as a comment-only template (97-byte header, no data
  rows) in every family checked (accessories, atlas_storage, kumi, para) — so its condition/mode/
  command relationship structure is likewise DOCUMENTED FACT only in this snapshot.

---

## 5. Manual ↔ Repository ↔ Code Concept Mapping

### 5.1 What exactly is a Metatype, and what is "Polymorphic Metatype"? (recap with mapping)

See §1.1–1.2 for the concept definitions. The mapping below records status against the actual
codebase.

### 5.2 Manual concept → repository → code status table

| Concept | Manual reference | Repository file(s) | Column(s) | Example (repo/process doc) | Code representation | Status |
|---|---|---|---|---|---|---|
| Metatype instance | [MT §go_types] | go_types | id, name | `MT_CYCLADE`, `MT_VERUS` | none | **NOT FOUND** (no `Snapshot` field, no Metatype model) |
| Article binding | [MT §go_articles] | go_articles | id, article_nr, prm_key, chprm_key | `MT_CYCLADE;...;FE1L;CFG_FE1L;CHP_FE21` | none | **NOT FOUND** |
| Article polymorphism (mode 4 + go_info.configuration) | [MT §go_types mode; §go_info] | go_types, go_info | mode, go_info.configuration | Verus: parent articles switch on `GVERUS_Type` | none | **NOT FOUND** |
| Child/sub-item creation (mode 8) | [MT §go_types mode 8; §go_children/childprops] | go_childprops, go_children | child_key, pos_x/y/z, condition | Verus: `CH_Headrest` attached via `GVERUS_Headrest` | `models/relation_object.py` covers a *different* relation domain (OCD tCOMd_RelObj) — **not directly applicable** (§7.3g confirms) | **PARTIALLY FOUND** (analogous OCD relation concept exists in code, but not this one) |
| Property value whitelist (go_propvalues, mode 8192) | [MT §go_propvalues] | go_propvalues | id, name, value, condition | `atlas/1/go_propvalues.csv`; Verus Step 4a "per-article value filter" | none | **NOT FOUND** |
| Value display order (go_proporder, mode 128) | [MT §go_proporder] | go_proporder | value, number | `atlas/1/go_proporder.csv`, spaced-by-10 convention (project convention, not spec) | none | **NOT FOUND** |
| i18n labels (go_texts) | [MT §go_texts] | go_texts | key, language, text | en/de/fr/nl rows keyed by property/value id | Existing `Snapshot`/OCD text handling (`text_blocks`, `tCOMd_Text`) is a **different, OCD-specific** text model | **PARTIALLY FOUND** (parallel OCD mechanism exists, not this one) |
| Attachment points (go_attpt) | [MT §go_attpt] | go_attpt | key, direction, pos_x/y/z, rot_y | `atlas/1/go_attpt.csv`, `_GO_CHILD` special key | none | **NOT FOUND** |
| OFML class mapping (go_classes) | [MT §go_classes] | go_classes | id, class | `layout_studio`: `MT_LS_Desk;::hmx::layout_studio::lsMetaType` | none — and this is **conceptually distinct** from the current codebase's "Class Creation" (OCD property-class) workflow, a naming collision to avoid (§7.3d) | **NOT FOUND** |
| Behavior flags (go_setup / legacy GSetup) | [MT §go_setup] | go_setup | id, key, value | Verus: `NoMTOrderRep=1, HideOrderNo=1, ...` | none | **NOT FOUND** |
| Action/event matrix (go_actions) | [MT §go_actions] | go_actions | id, direction, action, condition, param_1/2 | Verus: CON_PROP/SET_PROP rows hiding/resetting `GVERUS_Headrest` per article | none | **NOT FOUND** |
| Build/compile step (mt.inp_descr → ebmkdb.exe → .ebase) | [MT §5, abstractly: "or file mt.ebase if compiled"] | mt.inp_descr, ebmkdb.exe, make_ebase.bat | — | Verus: `ebmkdb.exe mt.inp_descr verus.ebase` | none | **NOT FOUND** (not even documented precisely by the manual — recovered only from the repository + Verus prompt) |
| MDB access (unrelated but adjacent) | n/a | n/a (go_* is pure CSV, never MDB) | — | — | `services/mdb_service.py` | **N/A to Metatype** — confirmed go_* has no MDB involvement anywhere sampled |
| Canonical in-memory model | n/a | n/a | — | — | `models/snapshot.py` (extension target per prior canonical-model investigation) | **PARTIALLY FOUND** (right container, zero Metatype fields yet — §7.3b) |

### 5.3 Property formats (all DOCUMENTED FACT, [MT §go_types Format])

`ch` (symbolic choice), `chf`/`chi` (float/int choice), `f`/`i` (plain float/int), `fn` (free
numeric, parametrized by `go_freenumeric`), `na` (native-property wrapper, name = native name +
`G` prefix), `th` (thru property, transfers value predecessor→successor in concatenation, **not**
part of article polymorphism), `cp` (child-position representation, 2-digit mode = coordinate +
alignment), `lb` (read-only label).

### 5.4 Property mode bitmask (all DOCUMENTED FACT, [MT §go_types Mode]) — full 14-bit table

| Bit | Meaning |
|---|---|
| 1 | editable |
| 2 | considered for global modification |
| 4 | controls the variant code (article polymorphism) |
| 8 | controls a sub-item/child (mutually exclusive with 4) |
| 16 | invisible |
| 32 | inherited initially from parent/predecessor (both must be metatypes) |
| 64 | suppress filter-adaptation dialog (needs `ShowPolyPropFilterMsg` in go_setup) |
| 128 | explicit sort order via go_proporder |
| 256 | re-create main child's 2D/3D geometry after modification |
| 512 | force removal+recreation of own children after modification |
| 1024 | reposition main child's geometry after modification |
| 2048 | reposition own children after modification, filter lists affected child props — **"only needed for na and fn properties and works only there"** [MT], see §5.6 item 1 below for a documented contradiction |
| 4096 | standard collision detection on property change |
| 8192 | validity limited via go_propvalues |

### 5.5 Inheritance-control algorithm (DOCUMENTED FACT, [MT §go_nativeproperties]) — always empty in repo, never cross-checked against live data

1. Filter entries to matching ancestor `pid`, else fall back to `_ANY` entries only.
2. INCL+`_ALL` → inherit all native properties from that ancestor.
3. Else EXCL+`_ALL` → inherit none.
4. Else INCL+`_DEFAULT` → inherit all except EXCL-matched identifiers.
5. Else EXCL+`_DEFAULT` → exclude all except INCL-matched identifiers.
6. Else (no entries / table absent) → inherit all.

`na` properties are always excluded from this regardless of the above.

### 5.6 go_setup / GSetup flag reference (DOCUMENTED FACT, [MT §go_setup]) — abbreviated to flags actually seen populated in the repository (cyclade_Tables/Verus)

`NoMTOrderRep` (&1, metatype not a separate order-list node), `ChildOrderRep` (&2, children
become sub-items of main child), `HideOrderNo` (&16, hide auto-created article-number property),
`HideFilterMsg` (&32, suppress filter-change display), `PropClassNA` (&32768, legacy na-property
display grouping). Full ~25-flag table (including obsolete `Feedback3D`/GXSetup flags) is in the
manual; not reproduced in full here since none beyond the above five were observed populated in
any sampled family.

### 5.7 Build toolchain — again noted for concept-mapping completeness

(See §2.3.) The build step's own build toolchain (`ebmkdb.exe`/`mt.inp_descr`) is not documented
by the manual beyond a passing mention that data "if compiled to EBASE format" produces
`mt.ebase` — it was recovered entirely from the repository and the Verus prompt's exact
invocation.

---

## 6. Explicit Disagreements / Extensions / Gaps — Process Docs vs. Manual

1. **Mode 2048 restriction contradiction (unresolved).** [MT]: mode 2048 "is only needed for na
   and fn properties and works only there." But `Verus_Metatype_Prompt_TEST.md` assigns mode 2051
   (1+2+2048) to `GHeightAdjustment`, a plain `ch`-format property (values `@V2`/`@V3`), with
   `filter=GVERUS_Headrest` — not documented as `na`/`fn` anywhere in that doc. Possible
   explanations, none resolvable from the docs alone: (a) implementation tolerates 2048 on `ch`
   properties despite the documented restriction; (b) the Verus example itself deviates from
   spec and `GHeightAdjustment` should be `na`/`fn`-typed; (c) mode 512 (unconditional child
   recreation, no na/fn restriction) may be the spec-correct choice here instead. **Flag to a
   human OFML expert before using this as a template — do not treat it as validated by the
   manual.**
2. **go_propvalues per-article whitelist pattern** — real repository mechanism (mode 8192 gate),
   but the *operational* pattern ("value filter" per article + the specific bug class where a
   `go_propvalues` filter conflicts with a `go_actions` enable/default gate, making the default
   value unreachable) is pure MillerKnoll project knowledge, not in the EasternGraphics spec.
3. **`go_articles.configid` (gap)** — `Verus_Metatype_Prompt_TEST.md` states "configid = plain
   article number (not `MT_VERUS__PIA1Z`)" for `go_articles.csv`, but the manual's documented
   `go_articles` schema has no `configid` column (`id, manufacturer, program, article_nr,
   prm_set, chprm_set`). **UNKNOWN** whether this is an OAP/MillerKnoll-tooling-specific column,
   an internal alias for `article_nr`, or a real schema extension beyond base MT — not
   confirmable from the source docs read.
4. **"global" folder vs. per-series folder** — manual default: metatype tables live in a shared
   `global`/`meta` series folder (explicitly noted as renameable). MillerKnoll's actual practice
   (confirmed by both the Verus folder path `hmx/verus/1/` and the repository structure in §2) is
   **per-series** metatype tables — allowed by the manual's own "alternative names possible" note,
   so not a contradiction, but an unstated operational choice.
5. **Build toolchain** (`ebmkdb.exe`/`mt.inp_descr`) — the manual only says data "if compiled to
   EBASE format" produces `mt.ebase`, without naming the tool. Recovered entirely from the
   repository (§2.3) and the Verus prompt's exact invocation.
6. **"No underscores" property-naming house style** — Verus prompt's explicit rule is stricter
   than the manual's own naming rule (G-prefix + capitalized words, no umlauts/special
   chars/spaces — underscore isn't technically forbidden by the general ID type). A local style
   convention layered on a looser spec rule, not a contradiction.
7. **go_proporder spacing-by-10 convention** — practical convention (Verus: 10/20/30/40), not
   required by the manual (which only requires positive integers < 1000, no duplicates within a
   list).
8. **Agreement, worth noting for confidence**: every table name referenced in either process doc
   (`go_types`, `go_propvalues`, `go_proporder`, `go_children`, `go_actions`, `go_propclasses`,
   `go_properties`, `go_texts`, `go_setup`, `go_childprops`) is a currently-valid, non-obsolete
   table per the manual — no invented or incorrect table name was found in either process doc.

---

## 7. Reconstructed Polymorphic Metatype Creation Workflow

Built from three sources, each explicitly attributed: the manual's initialization-order and
build-step facts (**DOCUMENTED FACT**), the interactive process
(`POLYMORPHIC_METATYPE_CREATION_TEMPLATE_04092026.md`, **PROJECT PROCESS FACT**), and the fully
worked Verus example (`Verus_Metatype_Prompt_TEST.md`, **PROJECT PROCESS FACT**, cited as
"Verus"). This is a reconstruction of an existing manual process, not a proposal — no code has
been written from it.

### STEP 1 — Read repo/series data first
**Input:** target series name (e.g. `atlas`, `pullman`, `verus`).
**Processing:** inspect the target series' own `go_types.csv` (existing naming
pattern/prefixes/mode conventions), `go_propvalues.csv` + `go_proporder.csv` (existing
properties/value structure), `go_children.csv` (existing parent/child patterns), any prior
in-series notes.
**Repository data:** if the target series is sparse/unbuilt (48 of ~99 families are, per §2.2),
fall back to a reference built series (`atlas`, `pullman`, `layout_studio` are named in
POLY-TEMPLATE) for structural patterns — but adapt to the target series' own prefix, don't copy
verbatim.
**Output:** a summary of the target series' existing conventions, presented to the user before
proceeding.
**Validation:** none automated; human confirmation that the summary is accurate.
**Evidence:** [POLY-TEMPLATE Step 1].

### STEP 2 — Choose pattern
**Input:** user decision.
**Processing:** ask user to choose between **Polymorphism Metatype** (articles switch/swap via a
property, no parent/child structure — maps to manual's article polymorphism, mode 4) vs.
**Metatype with Childs** (parent metatype attaches/controls child articles — mode 8).
**Output:** chosen pattern, drives STEP 4 branching.
**Evidence:** [POLY-TEMPLATE Step 2]; manual basis in §5.1.

### STEP 3 — Property identity
**Input:** user decision.
**Processing:** ask for (1) technical property name matching the series' `G<SERIES>_...`
convention (e.g. `GATLAS_...`, `GPULLMAN_...`, `GVERUS_...`), (2) English display label.
**Output:** property name + label, feeding go_types.name and go_texts rows.
**Validation:** name must follow [MT §go_types Property Name] rules — `G`-prefix, each word
capitalized, no umlauts/special chars/spaces (project convention additionally forbids
underscores in the property name itself, §6 item 6).
**Evidence:** [POLY-TEMPLATE Step 3]; [MT §go_types Property Name].

### STEP 4 — Branch by pattern
**Input:** STEP 2 choice + STEP 3 property.
**Processing (Polymorphism branch):** which articles the property switches between; is the
switch unconditional or scoped (parent property/region); does every article accept every value
or are there exceptions → STEP 4a.
**Processing (Metatype-with-Childs branch):** which child-defining property to use/create + its
label; all possible values; are all values valid for every parent article or are there
exceptions → STEP 4a; for each value, which article(s) it attaches as a child; optional
positioning/offset behavior per child (only if user raises it, else reuse the series' existing
`go_children.csv` conditional pattern).
**Output:** full value/article mapping table.
**Evidence:** [POLY-TEMPLATE Step 4].

### STEP 4a — Value-validity-per-article exceptions
**Input:** STEP 4 output.
**Processing:** ask explicitly whether all articles accept the full value set, or whether
exceptions exist; if so, go **value by value** (not article by article), building
`Value | Valid for article(s)` (unstated values default to "all").
**Repository mechanism:** normally realized as a per-article value whitelist in
`go_propvalues.csv` (mode 8192 must be set on the property in `go_types` — a prerequisite not
called out in the process doc itself, confirmed only by cross-referencing the manual, §5.2)
— not by disabling the value globally; follow the series' existing mechanism.
**Validation:** explicit warning — check that a `go_propvalues.csv` filter does not conflict with
an enable/default gate in `go_actions.csv`, which would make the default value unreachable in
some article context. This is a known real bug class per the project doc, not a hypothetical.
**Evidence:** [POLY-TEMPLATE Step 4a]; [MT §go_propvalues] (mode 8192 gate).

### STEP 5 — Translations (always last)
**Input:** every technical value/property/label introduced in STEPs 3-4a.
**Processing:** produce EN → DE → FR → NL for each, presented as a table for confirmation, in
that fixed order.
**Output:** rows for `go_texts.csv` (single multi-language file with a `language` column per
Verus's actual practice, not one file per language).
**Evidence:** [POLY-TEMPLATE Step 5]; [Verus go_texts.csv description].

### STEP 6 — Confirmation, then implementation
**Input:** the complete spec assembled across STEPs 1-5.
**Processing:** present a full summary (pattern, property name+labels, values+labels, article
mapping, STEP 4a exceptions table, scoping conditions) for explicit user confirmation. **Only
after confirmation** may files be edited.
**Repository data written:** `go_types.csv`, `go_propvalues.csv`, `go_proporder.csv`,
`go_children.csv`, `go_actions.csv`, `go_childprops.csv`, `go_propclasses.csv`,
`go_properties.csv`, `go_setup.csv`, `go_texts.csv` — following the series' existing conventions
identified in STEP 1.
**Evidence:** [POLY-TEMPLATE Step 6].

### STEP 7 — Build / compile (recovered from repository + Verus, not documented by the manual as a concrete command)
**Input:** the edited `go_*.csv` set.
**Processing:** `cd hmx/<series>/1`; run `ebmkdb.exe mt.inp_descr <series>.ebase` directly
(**not** `make_ebase.bat`, which contains a blocking `pause` unsuitable for non-interactive
execution).
**Output:** `<series>.ebase` with a fresh timestamp.
**Validation:** exit code 0 + fresh timestamp on the output file is the stated success criterion.
No content-level validation step is described anywhere in the supplied materials — this is a
genuine gap (see §9).
**Evidence:** [Verus "Build step"]; §2.3.

### Worked example cross-check (Verus, both patterns combined)

Series `verus` (manufacturer `hmx`), parent metatype `MT_VERUS`, child metatype
`MT_VERUS_Headrest`. Parent articles PIA1Z/PIA2Z (headrest-capable) vs. PIA4SZ/PIA7Z
(headrest hidden) — this is the **Polymorphism** pattern applied to `GVERUS_Type` deciding which
article is active, combined with the **Metatype-with-Childs** pattern applied to
`GVERUS_Headrest` (mode 11 = 1+2+8, controls the `CH_Headrest` sub-item) deciding whether/where
the headrest child attaches. Every file touched (`go_articles`, `go_types`, `go_propclasses`,
`go_properties`, `go_proporder`, `go_childprops`, `go_children`, `go_actions`, `go_texts`,
`go_setup`) and every row's exact content is documented in §5's mode-arithmetic decode and in the
raw findings; not re-duplicated here.

### How the final output can be verified

1. **Structural**: `ebmkdb.exe` exit code 0 (compile-time validation — catches schema violations,
   malformed CSV, dangling FK-like references the compiler checks).
2. **Reachability** (project-specific, not spec-required): for every article, confirm the
   property's default value is not excluded by a `go_propvalues` filter for that article's
   context — the exact bug class STEP 4a warns about.
3. **i18n completeness**: every technical value/property introduced has EN/DE/FR/NL rows in
   `go_texts.csv` (STEP 5's explicit fixed order).
4. **UNKNOWN**: no functional/runtime validation step (e.g. loading the compiled `.ebase` into an
   actual OFML-conformant viewer/configurator) is described in any of the source documents —
   Metatype-Inspector 3.0 is the obvious candidate tool for this but its validation behavior is
   undocumented in the supplied materials (§6.4 above / §9 item 4 below).

---

## 8. Proposed Python Workflow Design (PROPOSED / UNIMPLEMENTED)

> Everything in this section is a proposal only. **Nothing described here has been implemented.**
> This section answers "what already exists / what can be reused / what's missing" and then, only
> after that, sketches the proposed workflow shape.

### 8.1 What already exists (CODE FACT, file:line cited)

- **`services/mdb_service.py:76-139`** — the sole Access-`.mdb` I/O gateway (32-bit PowerShell
  bridge, `resources/mdb_bridge.ps1`, because the app runs 64-bit and has no in-process ACE
  provider). Every other MDB consumer in the repo goes through it. **go_* data is pure CSV and
  never touches MDB anywhere sampled in the repository (§2/§3) — this service is only relevant to
  Metatype work if some future package/registration metadata ends up MDB-backed; it must not be
  duplicated if so.**
- **`services/mdb_reverse_engineering_service.py:1-15,36-64,163-459`** — reads an allow-listed set
  of `tCOMd_*` OCD tables and reconstructs a `Snapshot` via `import_snapshot()`. Its own docstring
  explicitly names "future Metatype work" as a beneficiary of this layer's design — but its
  `READABLE_TABLES` allow-list contains zero `go_*` names. **This is the right pattern to mirror
  (allow-list → normalize → write into Snapshot), not directly reusable code (CSV vs MDB).**
- **`models/snapshot.py:1-238`** — "the single source of truth for all engineering data held in
  memory... fields and relationships only, no logic." Already holds OCD-specific extensions
  (`text_blocks`, `relation_objects`, `value_tables`, `art_base`, `prog_info_rows`,
  `material_manufacturer_code` defaulting to `"hmx"`). Per a prior canonical-model investigation,
  this is the confirmed canonical model to extend, not replace. **Zero fields exist today for any
  Metatype concept** (no child/attachment-point/OFML-class-mapping equivalent).
- **`services/engineering/engineering_repository.py:1-50`** — a **naming collision to avoid**:
  this class means an in-memory read-only query layer over `snapshot.engineering.families`, NOT a
  filesystem/OFML repository tree. A Metatype design must pick a different term (e.g. "OFML
  Repository" / "hmx Repository").
- **Repository browser scaffolding** — `core/config.py:46-51`
  (`repository_browser_roots`, currently hardcoded to two published `WS\...` roots) →
  `ui/pages/product_page.py:747-796` (`_load_repository_browser`, lists immediate series folders
  only, two levels deep) → `services/maintenance_repository_link_service.py:63-96`
  (`inspect_repository`, checks only for `pcr_data_com_ocd.mdb`, reads only `tCOMd_Package`).
  **Real, reusable scaffolding (persisted-link registry, tree-walk shape), but currently
  MDB-file-only and points at the published `WS\...` tree, not the `_repository\hmx\<series>`
  engineering tree that actually holds `go_*.csv` files.**
- **`"hmx"` manufacturer constant** — live in current code, not just docs:
  `services/ocd_export_service.py:35`, `services/xocd_export_service.py:45`,
  `services/engineering/material_picking_service.py:22`, `models/snapshot.py:180`,
  `services/snapshot_serialization.py:1062`. Directly reusable.
- **PDM connection/presets** — `core/config.py:11-17,32-37,53-81`
  (`PDM_DATABASE_PRESETS`, `AppConfig.pdm_connection_string()`). Generic, format-neutral, reusable
  as-is if a future Metatype generator needs PDM source data.
- **Internal documentation (real, substantial, already present)** —
  `docs/04_Reference/Engineering_Reference/10_Metatype.md` (table-graph + field descriptions),
  `13_Naming_Standards.md`, `14_Generation_Process.md`, `15_File_Formats.md`, plus vendor spec
  reprints `docs/04_Reference/pCon/Specifications/MT_1.18.0_en.md` / `MT-StyleGuide_1.2_en.md`, and legacy-C#-exporter
  forensics in `docs/02_Domain/PDM/Legacy_PDM_Business_Logic/06_Articles.md` / `07_Attributes.md` / `21_OCD.md`
  describing how the *old* exporter built `go_articles`/`go_properties` DTOs
  (`metaArticles.cs`/`metaProperties.cs`, explicitly "not table-backed, no DB access") and wrote
  them to `hmx\<series>\1\`. **This investigation independently re-derived the same schema/
  workflow facts from the manual/repository rather than trusting that handbook — the two agree
  everywhere cross-checked, which raises confidence in both.**

### 8.2 What can be reused as-is

`MDBService` (only if MDB involvement ever arises — currently N/A), the PDM connection/preset
stack, the `"hmx"` constant, and the persisted repository-link registry pattern
(`MaintenanceRepositoryLinkService`, JSON-backed via `core/config.py:44
repository_connection_registry`).

### 8.3 What is partially implemented

The repository browser (two-level tree, but MDB-file-only and wrong root — needs extending to
recurse into a series' `1/` subfolder and glob `go_*.csv`, and to target
`_repository\hmx\<series>` as an additional/alternate root alongside the existing `WS\...` roots).
The `mdb_reverse_engineering_service.py` shape (allow-list → import_snapshot) is a proven pattern
to mirror for a parallel CSV-based reader — but would be new code, not an extension of that file,
since it's a structurally different I/O path (plain CSV, not MDB).

### 8.4 What is missing entirely

Any Python code reading or writing a `go_*.csv` table (grep-confirmed zero hits repo-wide outside
`docs/`). Any `Snapshot` fields for Metatype concepts (children/attachment-points/OFML-class
mapping/setup-flags/actions). Any workflow/UI page analogous to Class Creation/Articles/Relation
for Metatype. Any validation tool integration (Metatype-Inspector 3.0's actual checks are
undocumented in the supplied materials — §9 item 4).

### 8.5 Do-not-duplicate list

- Do not build a second MDB access path — go through `MDBService` if MDB is ever involved.
- Do not reuse `models/relation_object.py` for `go_attpt`/`go_children`/`go_childprops` — per the
  existing Relation Model documentation, that model deliberately abstracts only over OCD's two
  relation wire-shapes (MDB join-table vs. XOCD name-linked); the Metatype attachment-point/
  child-creation graph is a third, structurally distinct relationship domain and needs its own
  model(s), though it can follow the same "abstract over multiple wire formats" design principle.
- Do not name a new class "Engineering Repository" — that name is taken by
  `services/engineering/engineering_repository.py` for an unrelated in-memory concept.
- Do not build a new PDM access layer or a new folder-tree browser from scratch — extend the
  existing ones (§8.1/§8.3 above).

### 8.6 Proposed Python workflow shape (conceptual only — not implemented, not to be built in one step)

Following the reconstructed process in §7, and mirroring the reuse/extend shape established by
`mdb_reverse_engineering_service.py` for the OCD/MDB side:

```
MetatypeWorkflow
    discover_repository(root)          # find hmx\<series> folders, classify built vs. unbuilt (§2.2)
    inspect_series(series)             # STEP 1: read go_types/go_propvalues/go_proporder/go_children for a target series
    load_go_tables(series)             # parse every go_*.csv per the mt.inp_descr-confirmed schema (§3)
    resolve_relationships(tables)      # build the FK graph from §4 (prm_key/chprm_key/child_key/id chains)
    construct_metatype_model(tables)   # populate new Snapshot-adjacent fields (not yet defined) mirroring OCD extensions
    validate_metatype(model)           # mode/format compatibility checks, go_propvalues vs go_actions reachability (STEP 4a bug class)
    generate_output(model, series)     # write go_*.csv per series conventions identified in inspect_series()
    verify_output(series)              # invoke ebmkdb.exe, check exit code + timestamp (STEP 7)
```

Per method:

| Method | Purpose | Inputs | Outputs | Existing service to reuse | New logic required | Validation | Failure conditions | Evidence |
|---|---|---|---|---|---|---|---|---|
| `discover_repository` | enumerate hmx series folders, classify built/unbuilt | root path | list of series + built-flag | folder-browser scaffolding pattern (§8.1) | recursive walk + `go_*` glob (doesn't exist today) | root exists, is a directory | root missing/inaccessible | §2 |
| `inspect_series` | STEP 1 evidence gathering | series name | conventions summary (prefix, existing values) | none directly; new CSV parser | yes — CSV read | series folder exists; if unbuilt, fall back to reference series | series not found anywhere, including reference series | §7 STEP 1 |
| `load_go_tables` | parse all go_*.csv per schema | series, tables list | typed rows per table | none | yes — schema-driven CSV parser (semicolon, `#` comments, quoting rules per [MT §2]) | column count/type per `mt.inp_descr`-derived schema (§3) | malformed CSV, unknown column count | §3 |
| `resolve_relationships` | build FK graph | parsed tables | linked model | none | yes | every `chprm_key`/`prm_key`/`child_key` resolves to an existing row (§4) | dangling reference | §4 |
| `construct_metatype_model` | populate canonical model | linked tables | new Snapshot-adjacent structure | `models/snapshot.py` as extension target (§8.1) | yes — new fields/model, mirroring how `relation_objects`/`text_blocks` were added | — | — | §8.1 |
| `validate_metatype` | catch known bug classes + spec rules | model | pass/fail + findings | none | yes | mode 8192 has a go_propvalues entry; default value reachable under every article's filter (STEP 4a); mode/format compatibility (§5.3/§5.4) | default value unreachable, missing i18n row, mode/format mismatch | §7 STEP 4a; §6 item 1 (flag mode-2048-on-ch as a warning, not a hard failure, given the unresolved contradiction) |
| `generate_output` | write go_*.csv | model, series | updated CSV files on disk | none | yes | only after explicit user confirmation (STEP 6) | write conflicts with unsaved manual edits (`.bak`/`.new` files observed in §3 show this already happens by hand) | §7 STEP 6 |
| `verify_output` | compile + sanity-check | series | ebase build result | none (shell out to `ebmkdb.exe`, not a Python reimplementation) | yes — subprocess wrapper | exit code 0, fresh `.ebase` timestamp | non-zero exit, `make_ebase.bat`'s blocking `pause` if invoked by mistake | §7 STEP 7 |

These method names/signatures are illustrative, not a commitment — actual design should happen in
a follow-up planning step, one connected piece at a time, starting with
`discover_repository`/`load_go_tables` (read-only, lowest risk, and independently testable per §9)
before any write path is attempted.

---

## 9. Validation Plan for the Proposed Workflow

Each proposed step from §8.6 must be connected and tested one at a time — no big-bang
implementation. Tests below are boundaries, not implementations.

**Test 1 — Repository discovery**
Given the real `hmx\` root (or a fixture copy), `discover_repository()` returns exactly the
built/unbuilt classification independently confirmed in §2.2 (53 built, ~48 unbuilt, `dlm`
empty, `catalogue`/`info` excluded as non-product). Regression fixture: a small synthetic tree
with one built, one unbuilt, one empty, one non-product folder.

**Test 2 — Repository structure validation**
Given a series folder, confirm the five-subfolder skeleton (`1`, `ANY`, `EURO`, `GBP`, `NOPRICE`)
is detected correctly and that a folder missing subfolders is reported, not silently skipped.

**Test 3 — go_* file discovery**
Given a series' `1/` folder, glob for `go_*.csv` and correctly exclude/flag known anomaly
patterns found in §3.4 (`.bak`, `.new`, `__new.csv`, `_myne`, `_ORIG_MANUAL`, `.zip`,
prefix-less `Copy.csv`) rather than silently ingesting them as live tables.

**Test 4 — CSV schema loading**
Given one `go_*.csv` file per table type (fixtures drawn from the real cyclade_Tables/atlas
samples captured in §3), parse per the semicolon/`#`-comment/quoting rules in [MT §2] and
assert the exact column set matches the `mt.inp_descr`-confirmed schema (§3.2 master table).
Include a fixture for an always-empty table (asserting zero rows is a pass, not an error) and a
fixture for a multi-language `go_texts.csv`.

**Test 5 — Relationship resolution**
Using the atlas/cyclade_Tables fixtures, assert every confirmed FK chain from §4 resolves:
`go_articles.prm_key→go_properties.key`, `go_articles.chprm_key→go_childprops.key→
go_childprops.child_key→go_children.child_key`, `go_properties/go_types/go_propclasses.name→
go_texts.key`, `go_propvalues.condition` tokens ↔ `go_proporder.value`. Include a negative fixture
with a dangling `child_key` to confirm it's caught, not silently dropped.

**Test 6 — Article-polymorphism reconstruction (mode 4 / go_info.configuration)**
Using a fixture modeled on Verus's parent-article switching (PIA1Z/PIA2Z/PIA4SZ/PIA7Z via
`GVERUS_Type`), confirm the model correctly identifies which property drives article switching
and which `go_actions` rows hide/reset dependent properties per article.

**Test 7 — Child-attachment reconstruction (mode 8)**
Using the Verus `CH_Headrest` fixture, confirm the model correctly resolves which value of
`GVERUS_Headrest` attaches which child, at which position, under which condition — and that the
"only articles 1Z/2Z attach the headrest" gating condition round-trips correctly.

**Test 8 — go_propvalues/go_proporder consistency**
Confirm every `@Token` referenced in a `go_propvalues.condition` has a matching `go_proporder.value`
entry where mode 128 is set (§4.1 evidence row 6), and separately confirm mode 8192 is actually
set on any property that has `go_propvalues` rows (§5.2's documented prerequisite).

**Test 9 — Reachability validation (the STEP 4a bug class)**
Construct a fixture where a `go_propvalues` filter excludes a property's declared default value
for one article, while `go_actions` sets that article's default without adjusting the filter —
assert the validator flags this as unreachable, matching the exact bug class the process doc
warns about (§7 STEP 4a).

**Test 10 — Output generation (write path)**
Given a validated in-memory model, assert `generate_output()` produces byte-identical-format CSV
(semicolon-delimited, correct quoting) that a human editor would have produced by hand, checked
against one of the real `.bak`→live diffs captured in §3/§4 as a regression fixture (the
`cyclade_Tables` program-rename diff is a ready-made before/after pair).

**Test 11 — Build/compile verification**
Mocked `ebmkdb.exe` subprocess call: assert `verify_output()` correctly interprets exit code 0 +
timestamp change as success, and non-zero exit / missing binary as failure, without ever invoking
`make_ebase.bat` (blocking `pause` risk, §7 STEP 7).

**Explicitly out of scope for this test plan** (real content unknown, flagged not guessed):
Metatype-Inspector 3.0 integration (its rules are undocumented, §9 item 4 below) and any
functional/runtime OFML-viewer verification of the compiled `.ebase`.

### Sequencing

Tests 1-4 (pure read, no relationships) → Test 5 (relationships) → Tests 6-9 (semantic
reconstruction + validation, read-only) → Test 10 (write path, only after 1-9 are solid) → Test
11 (external tool integration, last). This mirrors "one step → test → verify → connect next step
→ test again" and keeps the highest-risk capability (writing to a real OFML repository) last and
best-guarded.

---

## 10. Open Questions / Unknowns

Collected from across all source material, not resolved by this investigation:

1. Does mode 2048 actually function on `ch`-format properties, or is the Verus example
   non-compliant with the spec? (§6 item 1)
2. What exactly is `go_articles.configid` relative to `article_nr`/`id`? (§6 item 3)
3. `oap_metatype2type.csv` columns 4–5 semantics — file maps a metatype `id` to an OAP "type"
   code (e.g. `MT_LS_Desk → OAP_DESK`), referenced only by footnote in the manual ("OAP OFML
   Aided Planning Version 1.4 §4.8.4") — not confirmable from supplied materials.
4. Metatype-Inspector 3.0's actual validation rules are unknown — the supplied history PDF is a
   1-page changelog stating only "first official release (2025-11-14)," no functional detail.
5. The exact 6-scenario basket-order-position mapping ([MT §4], a diagram on manual page 34) is
   lossy in the markdown conversion used for this investigation; the flag/value rows are
   preserved but the outcome-per-scenario mapping is not fully reconstructable from the .md file.
6. Relationship (if any) to `MK_Workbench_Phase1_Test.spec` or other untracked git-status
   artifacts — out of scope for this investigation, not read.
7. No live example exists anywhere sampled to confirm the documented FK behavior of the
   always-empty tables (`go_inhproperties`, `go_nativeproperties`, `go_propindex`,
   `go_propmapping`, `go_metainfo`, `go_feedback`, `go_attptgeo`, `go_interactors`,
   `go_itemplates`, `go_resetnativeprops`) actually operates as the manual describes (§4.3).
8. `go_childmoving`'s condition/mode/command relationship structure is DOCUMENTED FACT only in
   this snapshot — every sampled family's file is a comment-only template with no data rows
   (§4.3).
9. No functional/runtime validation step (e.g. loading a compiled `.ebase` into an actual
   OFML-conformant viewer/configurator) is described in any of the source documents (§7,
   "How the final output can be verified," item 4).
10. Several supporting non-`go_*` files were not opened in depth and their exact role is inferred
    from context/filename only: `input.txt`, `summary.txt` (root), binary geometry content
    (`.dwg`/`.egms`/`.geo`/`.vnm`/`.obj`/`.alb`), `odb2d_infix.csv`/`odb3d_infix.csv` content,
    `sbmetatype.cls`/`sbplanning.cls`, `go_context.ofml`'s exact origin, and the contents of
    `basics.7z`/`REP_symbol.7z` (§2.4).
