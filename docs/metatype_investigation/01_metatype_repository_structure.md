# 01 — hmx Repository Structure

Root: `C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx` (14 GB). **REPOSITORY FACT**
throughout unless noted; read-only investigation, nothing modified.

## 1. Root listing

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
  (cyclade_Tables, aeron, comma, atlas, knot, hush; all five show exactly this five-subfolder shape).

## 2. Built vs. unbuilt families — the key structural finding

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

## 3. Build toolchain (how a family goes from unbuilt to built)

Not documented in the manual at all (see file 04 §7 item 5) — recovered empirically:

1. **`mt.inp_descr`** ("GO III (MT) Input Description, Version 1.16", EasternGraphics) — the
   authoritative field-level schema for every `go_*.csv` table, present in every family folder
   (built or not). This is the source used for every column list in file 02.
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

## 4. Not verified / not opened

`input.txt`, `summary.txt` (root), `.dwg`/`.egms`/`.geo`/`.vnm`/`.obj`/`.alb` binary geometry
content, `odb2d_infix.csv`/`odb3d_infix.csv` content, `sbmetatype.cls`/`sbplanning.cls`,
`go_context.ofml` (present in `symbol/1/`, not part of the `mt.inp_descr` schema, origin
unconfirmed), `basics.7z`/`REP_symbol.7z` archive contents, `catalogue`/`info` subfolder contents
beyond one level. Flagged, not guessed.
