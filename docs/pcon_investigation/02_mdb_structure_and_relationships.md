# 02 — MDB/OCD Structure and Relationships (Evidence-Based)

**Status:** Forensic investigation. No code changed. Every claim is labelled
**FACT** (directly observed in a file, with citation), **INFERENCE** (deduced
from naming/usage but not textually confirmed), or **UNKNOWN** (not
determinable from the repo as it stands).

**Scope note:** This file is one track of a larger pCon/MDB translation-layer
investigation. `docs/Legacy_PDM_Business_Logic/` and `docs/PDM_MDB_Engineering/`
are the PDM-side baseline and were only skimmed for orientation, not redone
here. This file's job is the MDB/OCD structural model and what the *current*
exporter code (`services/ocd_export_service.py`, `services/xocd_export_service.py`)
actually emits.

---

## 0. Headline finding: two conflicting descriptions of the MDB write path exist in this repo

**FACT.** `docs/pcon_reference/database_relationships/*.md` and
`docs/PDM_MDB_Engineering/06_OCD_Integration.md` describe a write pipeline built
around `helpers/mdb_helper.py::create_handbook_base`,
`services/workspace_snapshot_builder.py`, `services/workspace_service.py`,
`services/pdm_to_mdb_service.py`, `services/ocd_payload_service.py`,
`services/conflict_detection_service.py`, `services/workspace_mapping_service.py`,
`services/workspace_import_service.py`, `services/workspace_pipeline_service.py`,
and `core/workspace_snapshot.py`.

**FACT.** None of those files exist in this repository as it stands today:

```
$ find . -iname "mdb_helper.py" -o -iname "workspace_snapshot_builder.py" \
         -o -iname "workspace_service.py" -o -iname "pdm_to_mdb_service.py"
(no output)
```

**INFERENCE.** These docs describe either (a) a prior architecture that was
replaced by the current `services/ocd_export_service.py` +
`services/xocd_export_service.py` pair, or (b) a planned/aspirational
architecture that was never built as described. Either way, **the
`docs/pcon_reference/database_relationships/` tree (ERDiagram, RelationshipMatrix,
DependencyGraph, BuilderTableMapping, ServiceMapping, ValidationRules, ReadOrder,
WriteOrder, and the per-table files under `tables/`) is stale relative to the
current codebase** and should not be used as-is to plan the translation layer.
It is useful only as directional evidence for column names and cardinality,
cross-checked against the current code below.

**FACT.** The current, live write path is:
- Direct MDB writer: `services/ocd_export_service.py` (`OcdExportService.export` /
  `.preview`, calling `MDBService.execute_batch` — a 32-bit ADODB PowerShell
  bridge, `services/mdb_service.py:76-122`).
- CSV/XOCD writer: `services/xocd_export_service.py`
  (`XocdExportService.export_series`), which is what pCon.creator's "OCD Import"
  module actually consumes.
- Read/reverse-engineering path: `services/mdb_reverse_engineering_service.py`
  (`MdbReverseEngineeringService.read` / `.import_snapshot`), which is
  non-mutating and reads a fixed, current, allow-listed table set
  (`STRUCTURAL_TABLES`/`PRICE_TABLES`/`PACKAGE_TABLES`,
  `services/mdb_reverse_engineering_service.py:36-64`).

Also stale: none of the reference docs (ERDiagram, RelationshipMatrix,
BuilderTableMapping, the `tables/*.md` files) mention `tCOMd_RelObj`,
`tCOMd_Relation`, or `tCOMd_RelObjRel` at all — yet the current exporter writes
all three, and the current reverse-engineering reader parses the FK chain
between them explicitly. See §3.

---

## 1. Table inventory actually touched by the current code

**FACT**, from `services/ocd_export_service.py:56-76` (`_PRODUCT_TABLES`, `_PK`)
and `services/mdb_reverse_engineering_service.py:36-64` (`STRUCTURAL_TABLES` /
`PRICE_TABLES` / `PACKAGE_TABLES`):

| Table | Written by `OcdExportService`? | Read by `MdbReverseEngineeringService`? | Autonumber PK column (evidence) |
|---|---|---|---|
| `tCOMd_ComGroup` | updated (label/code only, not wiped) | yes (`PACKAGE_TABLES`) | `com_ComGroupID` (not in `_PK`; template-owned) |
| `tCOMd_Package` | updated (label/code only, not wiped) | yes (`PACKAGE_TABLES`) | `com_PackageID` (template-owned) |
| `tCOMd_Text` | yes | yes | `com_TextID` |
| `tCOMd_RelObj` | yes | yes | `com_RelObjID` |
| `tCOMd_Relation` | yes | yes | `com_RelationID` |
| `tCOMd_RelObjRel` | yes | yes | `com_RelObjRelID` |
| `tCOMd_CodeScheme` | yes | yes | `com_CodeSchemeID` |
| `tCOMd_Class` | yes | yes | `com_ClassID` |
| `tCOMd_Property` | yes | yes | `com_PropertyID` |
| `tCOMd_PropValue` | yes | yes | `com_ValueID` |
| `tCOMd_Article` | yes | yes | `com_ArticleID` |
| `tCOMd_ArticleClass` | yes | yes | `com_ArticleClassID` |
| `tCOMd_ArtBase` | yes | yes | `com_ArtBaseID` |
| `tCOMd_Package2Mat` | yes | no (not in reverse-eng allow-list) | `com_Package2MatID` |
| `tCOMd_Article2Mat` | yes | no | `com_Article2MatID` |
| `tCOMd_Table` / `tCOMd_TableColumn` / `tCOMd_TableLine` | yes | yes | `com_TableID` / `com_TableColumnID` / `com_TableLineID` |
| `tCOMd_Price` / `tCOMd_GlobalPrice` | yes (item-level) | yes, opt-in (`include_prices`) | `com_PriceID` / `com_GlobalPriceID` |
| `tCOMd_PriceList2` | read only (template-kept) | yes, opt-in | n/a (kept, not generated) |
| `tCOMd_Option` / `tCOMd_OptionValue` | **never written** (per stale doc `06_OCD_Integration.md:121-140`, and no code path in current `ocd_export_service.py` writes these tables either) | not in reverse-eng allow-list | — |

**INFERENCE.** The Options/OptionValues write-gap noted in the stale
`06_OCD_Integration.md` (§5 there) still appears true of the *current* exporter:
`ocd_export_service.py` folds options into `tCOMd_Property`/`tCOMd_PropValue`
via the shared `_properties`/`_property_values` builders (comment at
`xocd_export_service.py:1-19`: "OCD unifies options into properties"), and
there is no `tCOMd_Option`/`tCOMd_OptionValue` table in `_PRODUCT_TABLES` or
`_PK`. This is consistent with the stale doc's conclusion by coincidence, not
because the doc was re-verified.

---

## 2. FK relationships — verified against current code, not assumed

Each row states: source table.column → target table.column, meaning,
FACT/INFERENCE/UNKNOWN, and citation.

| # | Source.Column | Target.Column | Meaning | Status | Evidence |
|---|---|---|---|---|---|
| 1 | `tCOMd_Package.com_ComGroupID` | `tCOMd_ComGroup.com_ComGroupID` | Package belongs to a commercial group | INFERENCE (template-owned; exporter only updates label/code, never sets this FK) | `ocd_export_service.py:143-149` reads both ids from the template row as a pair; never re-parents |
| 2 | `tCOMd_Article.com_PackageID` | `tCOMd_Package.com_PackageID` | Article belongs to package | FACT | `ocd_export_service.py:914-921` (`_articles`) sets `com_PackageID: package_id` |
| 3 | `tCOMd_Article.com_ComGroupID` | `tCOMd_ComGroup.com_ComGroupID` | Article also directly carries its com group | FACT | `ocd_export_service.py:914-921` sets `com_ComGroupID: comgroup_id` on the Article row itself (i.e. Article has a *direct* FK to ComGroup, not only via Package — not shown in the stale ERDiagram at all) |
| 4 | `tCOMd_Article.com_CodeSchemeID` | `tCOMd_CodeScheme.com_CodeSchemeID` | Article's variant-code grammar | FACT | `ocd_export_service.py:911-917`, scheme built per base code in `_code_schemes` (`ocd_export_service.py:689-732`) |
| 5 | `tCOMd_Article.com_ShortTextID` / `com_LongTextID` | `tCOMd_Text.com_TextID` | Article display text | FACT | `ocd_export_service.py:918-919` |
| 6 | `tCOMd_Article.com_RelObjID` | `tCOMd_RelObj.com_RelObjID` | Article-level precondition/action binding | FACT (column written, always `None` in current generator) | `ocd_export_service.py:917` sets `"com_RelObjID": None` explicitly — the column exists and is wired for a future article-level relation, but the current generator never populates it |
| 7 | `tCOMd_Class.com_PackageID` | `tCOMd_Package.com_PackageID` | Class scoped to package | FACT | `ocd_export_service.py:744-746` (`_classes`) |
| 8 | `tCOMd_ArticleClass.com_ArticleID` | `tCOMd_Article.com_ArticleID` | join: article↔class | FACT | `ocd_export_service.py:924-948` (`_article_classes`) |
| 9 | `tCOMd_ArticleClass.com_ClassID` | `tCOMd_Class.com_ClassID` | join: article↔class | FACT | same |
| 10 | `tCOMd_ArticleClass.com_RelObjID` | `tCOMd_RelObj.com_RelObjID` | class-membership precondition/action | FACT (column written, always `None`) | `ocd_export_service.py:945` `"com_RelObjID": None` |
| 11 | `tCOMd_Property.com_ClassID` | `tCOMd_Class.com_ClassID` | property belongs to a class | FACT | `ocd_export_service.py:749-790` (`_properties`), `com_ClassID: class_pk` |
| 12 | `tCOMd_Property.com_TextID` | `tCOMd_Text.com_TextID` | property label | FACT | `ocd_export_service.py:778-786` |
| 13 | `tCOMd_Property.com_RelObjID` | `tCOMd_RelObj.com_RelObjID` | property-level precondition/action | FACT (column written, **always `None`** in the current generator) | `ocd_export_service.py:786` `"com_RelObjID": None` — **the exporter never binds a property to a relation object directly**, even though the reverse-engineering reader explicitly expects and parses this FK (see §3) |
| 14 | `tCOMd_Property.com_HintTextID` | `tCOMd_Text.com_TextID` | property hint text | FACT (column written, always `None`) | `ocd_export_service.py:786` |
| 15 | `tCOMd_PropValue.com_PropertyID` | `tCOMd_Property.com_PropertyID` | value belongs to property | FACT | `ocd_export_service.py:856-899` (`_property_values`) |
| 16 | `tCOMd_PropValue.com_TextID` | `tCOMd_Text.com_TextID` | value label | FACT | `ocd_export_service.py:889-895` |
| 17 | `tCOMd_PropValue.com_RelObjID` | `tCOMd_RelObj.com_RelObjID` | value precondition (B_ relations) | FACT, and the **only** relation FK the current exporter actually populates | `ocd_export_service.py:895`, sourced from `value_relobj` built in `_relations` (`ocd_export_service.py:658-685`) |
| 18 | `tCOMd_RelObj.com_PackageID` | `tCOMd_Package.com_PackageID` | relation object scoped to package | FACT | `ocd_export_service.py:671-673` |
| 19 | `tCOMd_RelObjRel.com_RelObjID` | `tCOMd_RelObj.com_RelObjID` | join: relation object → its relation link(s) | FACT (both write and read sides agree) | write: `ocd_export_service.py:678-682`; read: `mdb_reverse_engineering_service.py:299-344` (explicit doc-comment of the chain) |
| 20 | `tCOMd_RelObjRel.com_RelationID` | `tCOMd_Relation.com_RelationID` | join: relation object → relation body | FACT | same citations |
| 21 | `tCOMd_Relation.com_PackageID` | `tCOMd_Package.com_PackageID` | relation body scoped to package | FACT | `ocd_export_service.py:674-677` |
| 22 | `tCOMd_ArtBase.com_ArticleID` | `tCOMd_Article.com_ArticleID` | per-article allowed-value restriction | FACT | `ocd_export_service.py:950-987` (`_artbase`); note this table has **no** `com_ClassID`/`com_PropertyID`/`com_ValueID` numeric FKs at all — it stores `com_ClassName` and `com_PropName` and `com_PropValue` as **strings**, not surrogate-key FKs (see §4) |
| 23 | `tCOMd_Article2Mat.com_ArticleID` | `tCOMd_Article.com_ArticleID` | article material-selection link | FACT | `ocd_export_service.py:792-854` (`_material_mappings`) |
| 24 | `tCOMd_Article2Mat.com_Val2MatMapID` | `tCOMd_Val2MatMap.com_Val2MatMapID` | which material map applies | FACT | same; `com_Val2MatMapID` resolved in `_material_map_id` (`ocd_export_service.py:355-365`), a template-owned table never written by this exporter |
| 25 | `tCOMd_Package2Mat.com_PackageID` | `tCOMd_Package.com_PackageID` | package-level material default | FACT | `ocd_export_service.py:819-833` |
| 26 | `tCOMd_Price.com_ArticleID` | `tCOMd_Article.com_ArticleID` | article price | FACT | `ocd_export_service.py:1053-1100` (`_prices`) |
| 27 | `tCOMd_Price.com_PriceListID` | `tCOMd_PriceList2.com_PriceListID` | price list membership | FACT | same; price lists are **read from the template, never generated** (`_price_lists_by_currency`, `ocd_export_service.py:1031-1051`) |
| 28 | `tCOMd_Price.com_TextID` | `tCOMd_Text.com_TextID` | surcharge label | FACT | `ocd_export_service.py:1078` |
| 29 | `tCOMd_GlobalPrice.com_PackageID` | `tCOMd_Package.com_PackageID` | package-level (non-article) global price | FACT | `ocd_export_service.py:1089-1092` |
| 30 | `tCOMd_Table` / `tCOMd_TableColumn` / `tCOMd_TableLine` chain | (self-contained value-combination tables) | value combination tables, keyed to `com_PackageID` only | FACT | `ocd_export_service.py:991-1027` — **no FK back to `tCOMd_Property`/`tCOMd_PropValue`**; column/line binding is by `com_ColumnName`/`com_TableLineValue` **string** matching, not surrogate keys (INFERENCE: this is a naming-based join, confirm at runtime against a live MDB if precise semantics matter) |

**Do NOT assume the naive `Article→ArtBase→Class→Property→PropValue→RelObj→
Relation` chain.** The verified chain is actually:
`Package →{Article, Class, RelObj, Relation, Text}`; `Class → Property`;
`Property → PropValue`; `Article ↔ Class` via `ArticleClass` (join, not a
direct FK); `Article → ArtBase` (1→N, restriction rows, string-keyed not
ID-keyed); `RelObj ↔ Relation` via `RelObjRel` (join); `PropValue → RelObj`
(the only currently-populated relation binding); `Property → RelObj` and
`Article → RelObj` and `ArticleClass → RelObj` are **schema-present but
always-null** in the current generator (rows #6, #10, #13 above).

---

## 3. What the current exporters actually emit vs. what OCD/MDB expects

### 3.1 Direct-MDB path (`ocd_export_service.py`)

**FACT — write sequence** (`ocd_export_service.py:555-578`, `_build`):
`tCOMd_Text` → `tCOMd_RelObj` → `tCOMd_Relation` → `tCOMd_CodeScheme` →
`tCOMd_Class` → `tCOMd_Property` → `tCOMd_PropValue` → `tCOMd_Article` →
`tCOMd_ArticleClass` → `tCOMd_ArtBase` → `tCOMd_Package2Mat` →
`tCOMd_Article2Mat` → `tCOMd_RelObjRel` → `tCOMd_Table/TableColumn/TableLine`
→ `tCOMd_Price`/`tCOMd_GlobalPrice`.

**INFERENCE.** `tCOMd_RelObjRel` is inserted *after* `Article`/`ArticleClass`/
`ArtBase`, i.e. well after `RelObj`/`Relation` themselves and after the rows
that reference `RelObjID` (`PropValue`). This works because nothing besides
`RelObjRel` itself depends on a `RelObjRel` row existing yet, but it is a
stylistic oddity worth flagging if a future maintainer assumes insert order
mirrors FK dependency order throughout (it mostly does, except here).

**FACT — delete sequence** (`ocd_export_service.py:56-63`, `_PRODUCT_TABLES`,
used both to wipe the template and to re-derive review inputs): children-first
order deletes `RelObjRel` before `PropValue/Property/Article/Class`, and those
in turn before `Relation`/`RelObj` — correctly respecting the FK direction in
reverse.

**Gap vs. spec — relation coverage.** The OCD spec (`ocd_4.3_en.md:1809-1996`,
§2.15–2.16) supports six relation types (Precondition, Selection condition,
Action, Constraint, Reaction, Post-Reaction) across five domains
(Configuration/Price/BOI/Packaging/Tax) and *five* data entities (Article,
Property class, Property, Property value, BOI part). The current exporter
only ever populates **one** binding target: `PropValue.com_RelObjID`
(row #17 above). Article-, ArticleClass(=property-class)-, and Property-level
relation bindings are schema-ready (`com_RelObjID` columns exist and are
explicitly set to `None`) but never populated by
`services/engineering/engineering_relation_service.py` (see file 07 for detail)
or by any other generator found in this repo. **FACT** confirmed by grep: no
`.com_RelObjID` assignment other than `None` appears for `Article`/
`ArticleClass`/`Property` anywhere in `ocd_export_service.py`.

**Gap vs. spec — relation types actually generated.** Only type codes `"1"`
(Precondition) and `"3"` (Action) are ever constructed by
`engineering_relation_service.py` (`RELATION_TYPE_LABELS` in
`models/relation_object.py:12-19` documents all six, but
`build_relation_objects`/`_add_value_preconditions` in
`engineering_relation_service.py:68-155` only ever sets `type_code="3"` for
code-actions and `type_code="1"` for value preconditions) plus type `"3"`/
domain `"P"` Action relations from `services/pricing_relation_service.py:114-125`
(PA_PRICING). Selection condition, Constraint, Reaction, Post-Reaction, and
BOI/Packaging/Tax-domain relations are **never generated** by this codebase.
Whether the manufacturer's real MDB packages need them is **UNKNOWN** — not
verified against a live PDM/MDB database in this investigation (per repo
memory, a live PDM DB is reachable in another investigation track; not used
here).

**Gap — `tCOMd_ArtBase` string-keyed, not ID-keyed.** `ocd_export_service.py:
950-987` writes `com_ClassName`, `com_PropName`, `com_PropValue` as strings
(matching by *name*, not by the surrogate `com_ClassID`/`com_PropertyID`
integer keys used everywhere else). **INFERENCE**: this is presumably the
manufacturer's own real MDB schema convention for `tCOMd_ArtBase` (matching
`tCOMd_ArtBase.md` under `docs/pcon_reference/database_relationships/tables/`,
which the writer of this file did not re-verify against a live schema — see
§0 caveat about that whole subtree being stale) but it is a documented
divergence from the ID-based FK pattern used by every other `tCOMd_*` table
in this exporter, and is worth confirming against a live MDB schema before
building a translation layer that assumes uniform ID-based joins.

**Gap — Options.** Confirmed still true (see §1): options are folded into
`tCOMd_Property`/`tCOMd_PropValue` with `com_PropTypeCode` marking; there is
no separate `tCOMd_Option`/`tCOMd_OptionValue` write path in the current
exporter.

### 3.2 XOCD/CSV path (`xocd_export_service.py`)

**FACT.** XOCD's `xocd_relationobj.csv` / `xocd_relation.csv` shape
(`xocd_export_service.py:494-523`, `_relations`) matches the OCD *spec* table
shape far more closely than the MDB schema does: one row per
`(Program, RelObjID, Position, RelName, Type, Domain)` for `RelationObj`, and
`(Program, RelationName, BlockNr, CodeBlock)` for `Relation` — i.e. **no
RelObjRel join table** in XOCD; the relation is linked to its object **by
name** (`RelName == RelationName`, per the module docstring at
`xocd_export_service.py:1-19`, "XOCD links a relation object to its knowledge
by NAME"). This matches `ocd_4.3_en.md` exactly (RelationObj.RelName +
Relation.RelationName, no numeric join). **The MDB schema's `tCOMd_RelObjRel`
join table is therefore an MDB-specific normalization not present in the
canonical OCD wire format** — a structural divergence between the two export
paths that any translation layer must account for explicitly (INFERENCE:
reasoned from comparing the two writers' table shapes and the OCD spec; not
independently confirmed against a live pCon.creator import).

**FACT.** XOCD deliberately excludes pricing (`xocd_export_service.py:16-18,
495`: "Pricing is intentionally owned by the MDB export path and is not
emitted to XOCD"), so the two exporters are not full duplicates of each other
— they are complementary, and a consumer must combine both if it wants a
complete OCD package from this codebase alone. This split is a design choice
documented in the file header, not a gap.

**FACT.** Options are folded into properties the same way as the MDB path
(`_TEXT_TYPE_OCD` comment, `xocd_export_service.py:50-52`) and `xocd_option.csv`/
`xocd_optionvalue.csv` are never emitted (absent from the `_plan` table list,
`xocd_export_service.py:196-222`) — same Options gap as §3.1, confirmed
independently in the second writer.

---

## 4. Summary of gaps a downstream mapping task must account for

1. **Stale reference docs.** `docs/pcon_reference/database_relationships/*`
   and `docs/PDM_MDB_Engineering/06_OCD_Integration.md` describe a
   `helpers/mdb_helper.py`-based pipeline that does not exist in this repo.
   Do not use them as ground truth for the current exporter; use them only as
   secondary corroboration for OCD column names, cross-checked against
   `ocd_export_service.py`/`xocd_export_service.py`/
   `mdb_reverse_engineering_service.py` directly.
2. **Relation-object binding coverage is narrow.** Only `PropValue→RelObj` is
   ever populated by the generator; `Article`, `ArticleClass`
   (=property-class), and `Property` level relation bindings are schema-ready
   but always null (see file 07 for the full relation-model analysis).
3. **Relation type coverage is narrow.** Only Precondition (`"1"`) and Action
   (`"3"`) are generated; Selection condition/Constraint/Reaction/
   Post-Reaction and the BOI/Packaging/Tax domains are never produced.
4. **MDB vs XOCD relation shape differs.** MDB uses a 3-table join
   (`RelObj`/`Relation`/`RelObjRel`); XOCD uses the spec's native 2-table,
   name-linked shape. A translation layer touching relations must handle both.
5. **`tCOMd_ArtBase` is string-keyed** (class/property/value **names**, not
   surrogate IDs) while every other structural table is ID-keyed — an
   inconsistency worth explicit handling.
6. **Options/OptionValues are never written** by either exporter (folded into
   Property/PropValue); `tCOMd_Option`/`tCOMd_OptionValue` are read-only
   artifacts elsewhere in the ecosystem (per the stale doc; not independently
   re-verified in this pass, since neither current exporter touches them at
   all — see §1).
7. **Value-combination tables (`tCOMd_Table`/`Column`/`Line`) are name-joined**,
   not surrogate-key-joined to Property/PropValue — confirm against a live
   schema before assuming otherwise.
8. **No automated test exercises `import_snapshot`'s relation FK-chain
   resolution** (`tests/test_mdb_reverse_engineering_service.py` only tests
   `read`, not `import_snapshot`) — the RelObj/RelObjRel/Relation parsing logic
   in `mdb_reverse_engineering_service.py:299-390` is currently unverified by
   any test in this repo (**FACT**, confirmed by grep returning no matches for
   `RelObj`/`Relation` in that test file).
