# "MDF" Export / Import Requirements — Evidence Report

**Status:** Forensic, evidence-only. No code touched. No PDM↔pCon field mapping asserted —
only documented facts about each side, contract tables, and explicit UNKNOWN flags for the
downstream mapping task.

**Labeling convention:** **FACT** (explicitly documented / directly observed),
**INFERENCE** (derived, not itself written down), **UNKNOWN** (insufficient evidence).

---

## 0. Headline finding — read this first

**FACT:** The string **"MDF"** does not appear anywhere in the pCon.creator 2.22 manual
(EasternGraphics, version 2.22.0.125, January 2026 — see
`01_pcon_creator_2_22_2_investigation.md` §0.1 for the full version-caveat on why this manual,
not a confirmed 2.22.2-exact build, was used). Every relevant section of the manual was read
in full for this check: the complete table of contents (parts I–XII), all of "Commercial data
development" (§5, pp.61‑159, including every relation/constraint/pricing/packaging/tax
subsection and the article-encoding/code-scheme section), all of "Import of commercial data"
(§10, pp.349‑409, all 15 OCD-4.0 data tables plus the OCD 2.1/4.1/4.2/4.3/XOCD table lists),
all of "Import of catalog data" (§11, pp.411‑427, all 6 XCF tables), and "Management of
registration data" §8.3.2 (pp.297‑300, release dataset / OFML data containers / EBASE
databases / ZIP containers).

**FACT:** The only "MDF" hits anywhere in the `mk_product_workbench` repository are unrelated:
Microsoft SQL Server `.MDF`/`.LDF` physical database files in the legacy PDM/DPS export
pipeline (`docs/Legacy_PDM_Business_Logic/22_Export.md`, `25_Common_SQL.md`, and the
`Index/` files) — e.g. `sp_attach_db DPSDB,'C:\Databases\DPSDB_Data.MDF'`. This is Microsoft's
own SQL Server data-file extension and has no documented connection to pCon/OFML/OCD.

**What the pCon.creator ecosystem actually calls its file formats (FACT, all directly
observed in the manual and cross-checked against the already-existing local
`docs/pcon_reference/` analysis):**

| Format | What it is (FACT) | Where documented |
|---|---|---|
| **OCD** (Open Catalogue Data) | CSV table set, the commercial-data exchange format; also the schema of the internal Access package | Manual §10 (Import of commercial data), pp.349‑409; local `docs/pcon_reference/ocd_4.3_en.md`, `OCDTables.md` |
| **XOCD** | An OCD variant/extension (table names listed, manual pp.393‑408; not read field-by-field in this pass) | Manual §10.4.6‑10.4.10; local `docs/pcon_reference/xocd_4.3.2_en.md` |
| **XCF** (catalog exchange format) | CSV table set for catalog structure/article/variant/text/resource data | Manual §11 (Import of catalog data), pp.411‑427 |
| **MDB** (Microsoft Access) | The internal package/database file pCon.creator's workspace and the OCD generator target use | **Not named as such in the manual sections read here** — established by pre-existing local analysis: `docs/pcon_reference/README.md` (*"…writes it as OCD tCOMd_* rows into an Access MDB (pcr_data_com_ocd.mdb)…"*) |
| **EBASE** | A database format the *release dataset* converts OCD/ODB/OAM/Metatype/etc. CSVs into for distribution | Manual §8.3.2.1, p.298 (table: OCD→`pdata.ebase`, ODB→`odb.ebase`, OAM→`oam.ebase`, etc.) |
| **ZIP containers** | `xcf.zip`, `image.zip`, `mat.zip` — bundled release-dataset payloads | Manual §8.3.2.1, p.299 |
| **DSR** (Distribution Structure/Registration) | The directory/registration structure the export target conforms to | Manual §5.3.21, p.151 ("storage structure defined in DSR Specification"); local `docs/pcon_reference/dsr-3.7_en.md` |

**UNKNOWN / open question that the downstream mapping task must resolve before proceeding:**
is "MDF" in the task title a **misnomer/mix-up with MDB** (the format this repo's existing
`docs/pcon_reference/` material already centers all analysis on), or does it refer to some
other EasternGraphics artifact not covered by the manual sections read in this pass (e.g. a
"Model/Metadata Description Format" used elsewhere in the pCon ecosystem, such as
pCon.planner or a plugin)? **This report does not guess.** Everything below is written against
the **actually-documented** formats (OCD / XOCD / XCF / MDB / EBASE), on the assumption — to
be verified — that "MDF" was intended to mean **MDB**, since that is the format the rest of
this repository's pCon investigation (`docs/pcon_reference/`) already treats as the
PDM-generator's output target.

---

## 1. The six requested flows, restated against actual formats

The task asked for requirements for: PDM→MDF, MDF→pCon Creator, pCon Creator→MDF,
MDF→MK Workbench, MDB→MK Workbench, MK Workbench→MDB. Given §0, these six collapse (pending
the MDF/MDB resolution above) onto the following **evidenced** flows:

| Requested flow | Evidenced equivalent flow | Direction relative to pCon.creator |
|---|---|---|
| PDM → MDF | PDM → **OCD (CSV import tables)** → pCon.creator's internal **MDB** | Input to pCon.creator |
| MDF → pCon Creator | **OCD/XCF import** into pCon.creator (Import of commercial data §10 / Import of catalog data §11) | Input to pCon.creator |
| pCon Creator → MDF | pCon.creator **Export to OFML** (§5.3.21) → release dataset (EBASE + ZIP containers, §8.3.2) | Output from pCon.creator |
| MDF → MK Workbench | **MDB → MK Workbench** (see below; treated as the same flow under the MDF/MDB assumption) | Output from pCon.creator's package, input to MK Workbench |
| MDB → MK Workbench | Reading `tCOMd_*` rows out of `pcr_data_com_ocd.mdb` (already-existing local analysis: `WorkspaceSnapshotBuilder`, per `docs/pcon_reference/Architecture.md`) | Read-back |
| MK Workbench → MDB | Writing `tCOMd_*` rows into `pcr_data_com_ocd.mdb` (already-existing local analysis: `PDMToMDBService`/`MDBService`/`mdb_helper`, per `docs/pcon_reference/README.md`) | Write |

**Important scoping note (FACT):** the manual documents the **OCD/XCF CSV import contract**
(§10, §11) precisely and field-by-field — this is genuinely "PDM/ERP → pCon.creator," per the
manual's own framing (§10 title: "Import of commercial data"; the manual doesn't say the
source is PDM specifically, but describes a generic ERP/external-system import, consistent
with the local `docs/pcon_reference/README.md` framing: *"pCon.creator can be embedded into
complex data entry processes using external data sources like ERP systems or AutoCAD"* —
**FACT, cover page of the manual itself, p.3**). It does **not** document the MDB's internal
binary/table structure at the Access-driver level — that is exactly what the existing local
`docs/pcon_reference/OCDTables.md` and `docs/PDM_MDB_Engineering/` material already covers
from the generator-code side, and is **not re-derived here**.

---

## 2. PDM → OCD (import contract) — field-level, from the manual

This is the most concretely documented flow in the entire investigation. Below is every field
of every OCD 4.0 import table the manual specifies (manual §10.4.2, pp.373‑391), with
Key/Type/Length/Obligation exactly as printed. All entries are **FACT** unless marked.

### 2.1 `Article` (`ocd_article.csv`) — manual p.373

| Field | Key | Type | Length | Required | Notes |
|---|---|---|---|---|---|
| ArticleID | Y | Char | 80 | Y | Base article number |
| ArticleType | | Char | 1 | Y | `C` configurable / `P` plain |
| ManufacturerID | | Char | 16 | Y | Sales Manufacturer ID |
| SeriesID | | Char | 16 | Y | Sales Series ID |
| ShortTextID | | Char | 80 | Y | |
| LongTextID | | Char | 80 | N | |
| RelObjID | | Num | | N | Relational object number |
| FastSupply | | Num | | N | Fast supply counter |
| Discountable | | Bool | 1 | N | |
| OrderUnit | | Char | 3 | N | |
| SchemeID | | Char | 30 | N | Code scheme identifier for final article number generation |

### 2.2 `ArtBase` (`ocd_artbase.csv`) — manual p.374

| Field | Key | Type | Length | Required |
|---|---|---|---|---|
| ArticleID | Y | Char | 80 | Y |
| PropertyClass | | Char | 50 | Y |
| PropertyName | | Char | 50 | Y |
| PropertyValue | | Char | 30 | Y |

### 2.3 `PropertyClass` (`ocd_propertyclass.csv`) — manual p.375

| Field | Key | Type | Length | Required |
|---|---|---|---|---|
| ArticleID | Y | Char | 80 | Y |
| Position | | Num | | Y |
| Name | Y | Char | 50 | Y |
| TextID | | Char | 80 | N |
| RelObjID | | Num | | N |

### 2.4 `Property` (`ocd_property.csv`) — manual pp.376‑377

| Field | Key | Type | Length | Required | Notes |
|---|---|---|---|---|---|
| PropertyClass | Y | Char | 50 | Y | |
| PropertyName | Y | Char | 50 | Y | |
| Position | | Num | | Y | |
| TextID | | Char | 80 | N | |
| RelObjID | | Num | | N | |
| Type | | Char | 1 | Y | Data type (`character`/`number`/`length`/`text`, per manual §5.3.8.1) |
| Digits | | Num | | Y | Total digit count |
| DecDigits | | Num | | N | Decimal digit count |
| Obligatory | | Bool | | Y | **Numeric properties are always mandatory at runtime regardless of this flag (FACT, p.103)** |
| AddValues | | Bool | | Y | User may add values beyond the value list |
| Restrictable | | Bool | | Y | Value range restrictable by constraints |
| Multioption | | Bool | | Y | Multiple values selectable — **imported but not evaluated by OFML runtime in OCD 4.0 stage 1 (FACT, p.377)** |
| Scope | | Char | 2 | Y | `Configuration` / `Relation` / `Graphic` / `Display` |
| TxtControl | | Num | | Y | Print control code |
| HintTextID | | Char | 80 | N | **imported but not evaluated in OCD 4.0 stage 1 (FACT, p.377)** |

### 2.5 `PropertyValue` (`ocd_propertyvalue.csv`) — manual p.378

| Field | Key | Type | Length | Required |
|---|---|---|---|---|
| PropertyClass | Y | Char | 50 | Y |
| PropertyName | Y | Char | 50 | Y |
| Position | | Num | | Y |
| TextID | | Char | 80 | N |
| RelObjID | | Num | | N |
| IsDefault | | Bool | 1 | Y |
| SuppressTxt | | Bool | 1 | N |
| OpFrom | Y | Char | 2 | Y |
| ValueFrom | Y | Char | 30 | Y |
| OpTo | Y | Char | 2 | N |
| ValueTo | Y | Char | 30 | N |
| Raster | Y | Char | 30 | N |

### 2.6 `Price` (`ocd_price.csv`) — manual pp.379‑380

| Field | Key | Type | Length | Required | Notes |
|---|---|---|---|---|---|
| ArticleID | Y | Char | 80 | Y | (Base) article number |
| Variantcondition | Y | Char | 80 | Y | |
| Type | Y | Char | 1 | Y | `S` sales / `P` purchase |
| Level | | Char | 1 | Y | `B` base / `X` extra-charge / `D` discount |
| Rule | | Char | 10 | N | Required for Discount level (FACT p.88) |
| TextID | | Char | 80 | N | |
| PriceValue | | Num | | Y | |
| FixValue | | Bool | 1 | Y | Fixed amount vs. percentage |
| Currency | | Char | 3 | conditional | |
| DateFrom | | Date | 8 | Y | |
| DateTo | | Date | 8 | Y | |
| ScaleQuantity | | Num | | N | **Not evaluated / not imported in OCD 4.0 stage 1 (FACT, p.380)** |
| RoundingID | | Char | | N | |

### 2.7 `Rounding` (`ocd_rounding.csv`) — manual p.381

| Field | Key | Type | Length | Required | Notes |
|---|---|---|---|---|---|
| ID | Y | Char | 50 | Y | |
| Number | Y | Num | | Y | |
| Minimum | Y | Char | | N | |
| Maximum | | Char | | N | |
| Type | | Char | 4 | Y | `DOWN`/`UP`/`COM`/`ECOM` |
| Precision | | Num | | Y | |
| AddBefore | | Num | | Y | |
| AddAfter | | Num | | Y | |

### 2.8 `TaxScheme` / `ArticleTaxes` (`ocd_taxscheme.csv` / `ocd_articletaxes.csv`) — manual p.382

`TaxScheme`: `TaxID`(Y,Char), `Country`(Y,Char2,ISO-3166-1), `Region`(Y,Char3,ISO-3166-2),
`Number`(Y,Num), `TaxType`(Char8,e.g. `VAT`), `TaxCategory`(Char24, e.g.
`standard_rate`/`reduced_rate`/`super_reduced_rate`/`parking_rate`/`services`/`zero_rate`/`exemption`).
`ArticleTaxes`: `ArticleID`(Y), `TaxID`(Y), `DateFrom`(Y,Date8), `DateTo`(Date8).

### 2.9 `RelationObj` (`ocd_relationobj.csv`) — manual p.383

| Field | Key | Type | Length | Required | Notes |
|---|---|---|---|---|---|
| RelObjID | Y | Num | | Y | > 0 |
| Position | | Num | | Y | |
| RelName | | Char | 80 | Y | |
| Type | | Char | 1 | Y | `1` Pre-Condition, `2` Selection condition, `3` Action, `4` Constraint, `5` Reaction — **see UNKNOWN below re: Post-Reaction** |
| Domain | | Char | 4 | Y | `C` Configuration, `P` Pricing, `PCKG` Packaging — **Taxation has no listed code letter on this page; UNKNOWN whether it needs one** |

### 2.10 `Relation` (`ocd_relation.csv`) — manual p.384

`RelationName`(Y,Char80), `BlockNr`(Y,Num,"Code block number"), `CodeBlock`(Char, "Code
block"). **FACT, explicit ordering requirement:** *"The records have to [be] sorted for the
fields RelationName and BlockNr."*

### 2.11 Value combination tables (`<Tablename>_tbl.csv`) — manual p.385

`LineNr`(Y,Num), `PropertyName`(Y,Char50, "Name the table column"), `Value`(Y,Char30). Table
name itself limited to 64 chars, must be a valid OFML identifier.

### 2.12 Description/text tables — manual pp.385‑386

Seven tables, all sharing one shape: `ArtShortText` (`ocd_artshorttext.csv`), `ArtLongText`,
`PropClassText`, `PropertyText`, `PropHintText`, `PropValueText`, `PriceText`, `UserMessage`.
Fields: `TextID`(Y,Char80), `Language`(Y,Char2,ISO-639), `LineNr`(Y,Num), `LineFormat`(Char1,
**not evaluated / not imported in OCD 4.0 stage 1**), `Textline`(Char80). **FACT, explicit
ordering requirement:** sorted by `TextID, Language, LineNr`.

### 2.13 `CodeScheme` (`ocd_codescheme.csv`) — manual pp.387‑388

`SchemeID`(Y,Char30), `Scheme`(Char), `VarCodeSep`(Char12), `ValueSep`(Char12),
`Visibility`(Char1: `0` current-valid-visible-only / `1` all-configurable),
`InVisibleChar`(Char1, default `-`), `UnselectChar`(Char1, default `X`), `Trim`(Bool1,Y),
`MO_Sep`(Char), `MO_Bracket`(Char 2*12, left/right bracket halves).

### 2.14 `Packaging` (`ocd_packaging.csv`) — manual pp.389‑390

`ArticleID`(Y,Char80), `Variantcondition`(Y,Char90), `Width`/`Height`/`Depth`(Num),
`MeasureUnit`(Char3, conditional: `CMT`/`FOT`/`INH`/`MMT`/`MTR`), `Volume`(Num),
`VolumeUnit`(Char3, conditional: `INH`/`LTR`/`MTR`), `TaraWeight`/`NetWeight`(Num),
`WeightUnit`(Char3, conditional: `KGM`/`LBR`/`MGM`), `ItemsPerUnit`(Num), `PackUnits`(Num).

### 2.15 `Version` (`ocd_version.csv`) — manual p.391

`FormatVersion`(Char14,Y, "Number of the used OCD format version"), `RelCoding`(Char16,Y,
"used language for relational knowledge"), `DataVersion`(Char,Y), `DateFrom`/`DateTo`(Date8,Y),
`Region`(Char32,Y, "Distribution region"), `VarCondVar`(Char16,N), `PlaceHolderOn`(Bool,Y),
`Tables`(Char,Y, "Included tables separated by a comma"), `Comment`(Char,N).

**INFERENCE:** this `Version` table is effectively the **manifest/header** of an OCD import
batch — it declares the format version and which of the above tables are present
(`Tables` field). Any PDM→OCD generator must emit this table correctly or (per its own field
semantics) the import cannot know which format version/table set it's reading. This is an
**obligatory-field, easy-to-miss requirement** worth flagging to whoever builds the generator.

**Note on which OCD version this table set represents (FACT):** the manual's table of
contents lists import formats for **OCD 2.1**, **OCD 4.0** (fully detailed above), **OCD 4.1**,
**OCD 4.2**, **OCD 4.3** (these three are covered by cross-reference only — "OCD 4.1 - Data
tables" etc. each occupy a single TOC line, p.10, suggesting they are documented as *deltas*
against 4.0 rather than full independent field lists — **not verified by re-reading those
pages in this pass**), plus **XOCD 2.1/4.0/4.1/4.2/4.3**. The local repo's own reference
material centers on **OCD 4.3** (`docs/pcon_reference/ocd_4.3_en.md`). **UNKNOWN**: exact
field-level deltas between the OCD 4.0 table set reproduced above and OCD 4.3 — flagged for a
follow-up read of manual pp.392 (OCD 4.1‑4.3 delta sections) and/or the local `ocd_4.3_en.md`
spec, which the task instructions indicate already exists and documents this in full (not
re-derived here to avoid duplicating existing analysis).

---

## 3. PDM → XCF (catalog import contract) — manual §11.4.1, pp.422‑427

| Table | Filename | Key fields (FACT) | Notes |
|---|---|---|---|
| `Article` | `article.csv` | ArticleNumber(Y), VariantKey(Y) | plus ArticleCategory/PositionNumber ("not processed" — **FACT, explicitly dead fields**), InsertionType(Y), Visibility(Y), Package (foreign package name) |
| `Variant` | `variant.csv` | ArticleNumber(Y), VariantKey(Y) | `Variant codes` field: **content is "dependent on the sales product data... may contain the variant code or the final article code"** — **UNKNOWN/ambiguous per manual's own wording**, see `01_...md` §3 |
| `Structure` | `structure.csv` | ArticleNumber(Y), VariantKey(Y) | Level(Y), Type(Y, "type of the structure entry") |
| `Text` | `text.csv` | ArticleNumber(Y), VariantKey(Y), Language(Y, ISO-639) | ArticleText |
| `Resource` | `resource.csv` | ArticleNumber(Y), VariantKey(Y), Language(Y) | Type(Y, "resource type"), Resource |
| Co-resource tables | `resource_AP.csv`, `resource_FM.csv`, `resource_ZN.csv` | same shape as `Resource` | purpose of AP/FM/ZN suffixes **UNKNOWN** — not expanded in manual text read |

**Codepage requirement (FACT, p.427):** OFML data supports only **ANSI ISO‑8859‑1 (Latin‑1 /
Windows‑1252)** by default; Unicode (UTF‑8 or UTF‑16LE, BOM-detected) is also supported for
XCF import specifically. Any generator must declare/match codepage correctly or import fails
silently-wrong (mojibake), per this section.

---

## 4. pCon.creator → OFML/release output — manual §5.3.21 (export) and §8.3.2 (release dataset)

**FACT, manual p.151:** "Export to OFML" can be launched at Module / Manufacturer /
Distribution region / Product line level; target is a directory conforming to **DSR
Specification** storage structure; **UNC paths are not supported** as export destination.

**FACT, partial-export scope list (p.153)** — i.e. the granular units pCon.creator can
export/re-export independently: Article master; Article codeschemes; Classes, properties and
values; Relation-objects and relations; Value combination tables; Texts; Rounding rules;
Article type mapping; ODB parameter mapping; Material mapping. **FACT caveat:** *"A product
line has to be exported completely before using a partial export the first time."*

**FACT, release dataset contents (p.297‑300):**
- **OFML data containers** ("Album"): graphic files, materials/textures, OFML class files,
  string resources — six reserved scopes: `geometry_2d`, `geometry_3d`, `ofmltype`,
  `material`, `stringres`, `addfiles`.
- **EBASE databases**: the CSV table formats above (OCD, ODB, OAM, Metatypes, Metaplanning,
  Metaplacement, Metadialog, "Data control tables"/OFML, OAP) are each converted into a
  corresponding `.ebase` database file for distribution.
- **ZIP containers**: `xcf.zip` (XCF catalog data), `image.zip` (catalog images), `mat.zip`
  (property-value preview images).
- **Copied files**: geometry/material/addfiles resources copied as-is into distribution-region
  subfolders (`html`, `etc`, `oap`, `ars`).
- **FACT, explicit non-guarantee:** *"Date [sic] release transfers only known files to release
  data set. Project specific additional files are not automatically transferred as long as
  they are not mentioned in one of the known partial content descriptor files."*

**INFERENCE:** this means "pCon Creator → MDF/MDB" as a single monolithic file is not quite
how the manual frames output — the true output of a full release is a **directory tree of
EBASE databases + ZIP containers + copied resource files**, not one file. Whether the
**internal working file** (the "workspace") pCon.creator edits while a project is open is
itself an `.mdb` was **not confirmed inside the manual sections read** (the manual's own
"Directory structures in data creation projects" section, p.21, was not read in this pass —
flagged as a follow-up if the exact workspace file format needs manual-sourced confirmation
rather than relying on the pre-existing local `docs/pcon_reference/` analysis, which already
asserts it is an Access `.mdb`).

---

## 5. Export/Import contract table (as requested by the task)

Columns: whether the item is present, and whether it is Required/Optional/Not-applicable, for
each of the six evidenced flows from §1. `R`=Required, `O`=Optional, `N/A`=not part of that
flow's documented contract, `?`=UNKNOWN (not resolved by sources read).

| Item | PDM→OCD (import) | OCD/XCF→pCon.creator | pCon.creator→Export/Release | Release→MK Workbench (read-back) | MK Workbench→MDB (write) |
|---|---|---|---|---|---|
| Base article number / Article identifier | R (`ArticleID`, §2.1) | R | R (unchanged) | R | R |
| Article type (configurable/plain) | R (`ArticleType`) | R | R | R | R |
| Manufacturer / Series ID | R (`ManufacturerID`,`SeriesID`) | R | R | R | R |
| Short text | R (`ShortTextID`) | R | R | R | R |
| Long text | O (`LongTextID`) | O | O | O | O |
| Relation object link | O (`RelObjID`) | O — required if article has any relations | R if relations exist | R if relations exist | R if relations exist |
| Code scheme (final article number rule) | O (`SchemeID`) | O | O | O | O |
| Property classes | R (own table, §2.3) | R | R | R | R |
| Properties (name/type/scope/digits/obligatory/restrictable/multioption) | R (§2.4) | R | R | R | R |
| Property values (incl. intervals, raster, default) | R (§2.5) | R | R | R | R |
| Article-specific property restrictions (`ArtBase`) | O (§2.2) | O | O | O | O |
| Prices (base/upcharge/discount, variant-condition-keyed) | O (§2.6) | O — required if article is priced | O | O | O |
| Rounding rules | O (§2.7) | O — required if any price references one | O | O | O |
| Tax scheme / article taxes | O (§2.8) | O | O | O | O |
| Relation objects (typed, domain-scoped) | O (§2.9) | O — required for any Configuration/Pricing/Packaging/Taxation logic | O | O | O |
| Relation code (the actual logic) | O (§2.10) | O, paired 1:1 with RelationObj | O | O | O |
| Value combination tables | O (§2.11) | O — required if any relation/constraint/code-scheme calls one | O | O | O |
| Text blocks (7 kinds) | O per-kind (§2.12) | O, but effectively R for any labeled/localized article | O | O | O |
| Code scheme detail (separators, visibility, trim, brackets) | O (§2.13) | O | O | O | O |
| Packaging data (dimensions/weight per variant condition) | O (§2.14) | O | O | O | O |
| Version/manifest record | R (§2.15) | R (governs which tables are read) | ? (not confirmed whether release dataset re-emits an equivalent manifest) | ? | ? |
| Catalog article/variant/structure/text/resource (XCF) | N/A (this is the catalog side, not commercial-data side) | R for catalog import (§3) | R for catalog export/test-catalog | R | N/A (XCF is catalog, not OCD/MDB commercial data) |
| Codepage declaration | N/A for OCD import (ANSI default; not itself a data field) | R for XCF import (§3) | ? | ? | ? |
| MDB internal table structure (`tCOMd_*`) | N/A (PDM emits OCD CSV, not MDB directly) | N/A (this is pCon.creator's *internal* representation, not documented in the manual sections read) | N/A (release output is EBASE/ZIP, not MDB, per §4) | **This column is where the existing local `docs/PDM_MDB_Engineering/` and `docs/pcon_reference/OCDTables.md` analysis lives — not re-derived here** | same |

**Reading note on the last row:** the manual (as read in this pass) documents pCon.creator's
**CSV-level import/export contract** and its **release-dataset output shape**. It does **not**
document the Access `.mdb` binary/table internals — that is precisely the subject of the
pre-existing `docs/pcon_reference/OCDTables.md` and `docs/PDM_MDB_Engineering/` material, which
this report defers to rather than duplicating.

---

## 6. Gaps and open questions for the downstream mapping task

1. **"MDF" terminology (§0) — must be resolved first.** Confirm with whoever wrote the task
   brief whether "MDF" means "MDB," and if not, identify the actual source of that term before
   any mapping work proceeds on the assumption made in this report.
2. **Post-Reaction relation-object code (§2.9 / `01_...md` §10)** — the manual's UI names six
   relation types but the `RelationObj` table's `Type` field enumerates only five codes.
   Unresolved whether Post-Reaction is exportable at all via this table, or encoded some other
   way. Needs verification against a live OCD 4.3 export or `docs/pcon_reference/ocd_4.3_en.md`.
3. **Taxation domain code letter (§2.9)** — `RelationObj.Domain` lists `C`/`P`/`PCKG` but no
   letter for Taxation, even though "Taxation" is a named relation domain in the UI (manual
   p.108). Needs verification.
4. **OCD 4.1/4.2/4.3 deltas (§2.15 note)** — this report reproduces the OCD **4.0** table set
   in full field-level detail (the only one given a full field listing in the manual pages
   read); 4.1/4.2/4.3 are TOC-only in the pages read. The local repo already has
   `docs/pcon_reference/ocd_4.3_en.md` which likely supersedes/extends this — **reconcile the
   two before treating this report's field list as final for a 4.3-target generator.**
5. **XCF `Variant codes` ambiguity (§3)** — manual's own wording ("may contain the variant
   code or the final article code") is not fully deterministic; needs a concrete sample file
   or EasternGraphics support clarification.
6. **Workspace/internal file format** — this report did not confirm from the manual itself
   (pages read) that the pCon.creator "workspace" is an Access `.mdb`; that fact is carried
   over as-is from the pre-existing local `docs/pcon_reference/README.md` analysis and was not
   independently re-verified against the manual's own "Directory structures in data creation
   projects" section (p.21, not read in this pass).
7. **Release dataset ↔ OCD-table-set correspondence** — confirmed that `.ebase` databases are
   generated *from* the same CSV table shapes as §2, but whether a full round-trip (OCD CSV →
   pCon.creator MDB workspace → EBASE release → re-import elsewhere) preserves every field
   above (especially the explicitly-not-yet-runtime-evaluated ones: `ScaleQuantity`,
   `Multioption`, `HintTextID`, `LineFormat`) is **UNKNOWN** — the manual flags these as
   "imported but not evaluated," which is a different claim than "preserved on re-export."
8. **Relationship between this report's OCD/XCF contract and PDM's actual current output** —
   deliberately **not compared** here; that comparison belongs to the mapping task and should
   use `docs/PDM_MDB_Engineering/02_PDM_Data_Model.md` / `03_Engineering_Object_Mapping.md`
   (already flags `tCOMd_Option`/`tCOMd_OptionValue` write gap, empty `class_name`, missing
   pricing wiring, single `"contains"` relationship type — all of which now have a concrete,
   field-level target contract to compare against, per §2 and §5 above).
