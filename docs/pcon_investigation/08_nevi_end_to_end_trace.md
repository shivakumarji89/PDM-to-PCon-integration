# 08 — Nevi End-to-End Trace (PDM → OCD/MDB → pCon.creator)

**Status:** Forensic, evidence-only. No code changed.

**Real Nevi data found:** yes, partially. `docs/SKU_Config_Decode_Findings.md` contains
real, previously-verified facts about the Nevi (`DWE4`) product family from a live PDM
investigation (PDMTEST/PDMLive databases, sessions 2026-08-03/04). **No live PDM database
query was executed in *this* investigation pass** (the "live PDM DB" mentioned in this
repo's memory file was not re-queried here — this file reuses the already-recorded findings
from `SKU_Config_Decode_Findings.md` rather than re-deriving them). Where the trace needs
detail beyond what that file recorded (e.g. exact `AttributeId`/`OptionValueId` numeric
values, exact OCD/MDB row contents for this specific family), it is marked **GAP** with what
evidence would close it — per task instructions, no identifiers are invented.

---

## Real facts available (from `docs/SKU_Config_Decode_Findings.md`)

- **Product family:** `DWE4` (69 active products, PDM Live). Real SKU example:
  **`DWE42AN4YSNBADNN`** (§4, §9).
- **Category:** ProductCategory id **1239**, name **"Nevi Dach"** (§4).
- **Sibling family:** `DWE3` — structurally identical `Product`/`ProductRange`/`Attribute`
  columns; `DWE4` has **zero** `HandbookProducts` rows (never templated) but inherits
  attribute ordering through category 1239's `HandbookAttributes` (via the `DWE3` B2B
  group) (§4).
- **Head/tail split confirmed for this SKU:** `DWE42AN4YSNBADNN` decodes to **10 functional
  (head) attribute values / 8 physical (tail) attribute values** (§9, "Universal" table).
- **Position-based decode result (§6):** `DWE42AN4YSNBADNN` resolves **3/3** correctly under
  the position-based decoder (cited as a "no regression" validation result alongside
  `DWE36DT4YSNMNDL` 5/5).

---

## Trace

### 1. PDM Product

**FACT:** `Product` row(s) in `ProductRange` under `ProductCategoryId = 1239` ("Nevi Dach"),
family code `DWE4` (`SKU_Config_Decode_Findings.md` §4; schema per
`docs/Legacy_PDM_Business_Logic/26_Data_Model.md` §2.3: `Product.ProductId`,
`Product.Product`, `Product.ProductRangeId`).

**GAP:** exact `ProductId` / `Product.Product` string for the product that generates SKU
`DWE42AN4YSNBADNN` was not recorded in the source finding — the finding operates at the
family/SKU level, not the individual `ProductId` level. **Evidence needed:** a live query
`SELECT ProductId, Product FROM Product WHERE ProductRangeId IN (SELECT ProductRangeId FROM
ProductRange WHERE ProductCategoryId = 1239)` against PDM Live/Test.

### 2. PDM Item / article (the SKU)

**FACT:** `Item.Item = "DWE42AN4YSNBADNN"` (a real, verified SKU string,
`SKU_Config_Decode_Findings.md` §6, §9). Per the SKU model (§1 of that file): `head =
code.split(".")[0]`; since no `.` is shown in this example, the full string
`DWE42AN4YSNBADNN` is (or resolves entirely within) the head, or the tail was omitted in
the cited example. **UNKNOWN** whether this specific example string has a `.tail` suffix
not captured in the finding — the finding's §9 table lists it as `DWE42AN4YS…` (truncated
with ellipsis) for the functional/physical count example, so the **exact full string used
for the 3/3 decode validation is `DWE42AN4YSNBADNN`** (§6) but the **exact split point
between head and tail** for this specific SKU was not restated verbatim in the file.
**Evidence needed:** re-run `decode_config_codes_by_position` (or read
`config_value_codes`) for this exact Item in a live session to get the head/tail boundary.

### 3. Properties (PDM Attributes)

**FACT (structural, from §9 "Universal" table):** `DWE42AN4YS…` decodes to **10 functional
+ 8 physical attributes** — i.e. 18 distinct `Attribute` rows contribute to this one SKU.
Functional = `AttributeType = 0`, `AttributeValue.ModelSuffix IS NULL`, empty
`OrderCodeValue` (head/positional); physical = has a stored `OrderCodeValue` (tail/parametric)
(`SKU_Config_Decode_Findings.md` §9, cross-referenced to `15_Filtering.md` Q-FILT-007/008).

**GAP:** the specific **names** of those 18 attributes for the Nevi/DWE4 family (e.g.
whether they include "Type," "Leg style," "Control switch" as in the generic model, or
Nevi-specific attribute names) were not recorded in the source finding — only the
count (10/8) and the mechanism were verified. **Evidence needed:** `SELECT attr.Name,
attr.AttributeType FROM Attribute attr WHERE attr.ProductCategoryId = 1239 ORDER BY
attr.DisplayOrder` against a live PDM DB.

### 4. Property values (PDM AttributeValues)

**FACT (mechanism only):** each of the 18 attributes contributes exactly one selected
`AttributeValue` to this SKU (per `SKU_Config_Decode_Findings.md` §9: *"Each product = a
unique combination of its functional attribute values"* — no multi-value-per-attribute
example was found for any family, Nevi included; see file 05 Q2).

**GAP:** the specific `AttributeValueId`s / `AttributeValue.Name` strings selected for
`DWE42AN4YSNBADNN` were not recorded — only the mechanism (position-based decode of the
head string into attribute spans) is documented. **Evidence needed:** a live run of
`resolve_config_codes`/`config_value_codes` for this product, or a direct
`BaseAttributeValues`/`ProductAttributeValues` query scoped to this `ProductId`
(pending resolution of GAP in step 1).

### 5. Options / Option values

**UNKNOWN** whether the Nevi/DWE4 family uses PDM's separate `[Option]`/`OptionValue`
mechanism (fabric type/colour etc., per `docs/Legacy_PDM_Business_Logic/09_Options.md`,
`10_Option_Values.md`) at all, or whether — like the "Product-coded families (Bolster,
Always)" noted in §9 of `SKU_Config_Decode_Findings.md` as having "zero physical/tail" —
Nevi expresses everything through `Attribute`/`AttributeValue` alone. The 10/8
functional/physical split recorded for Nevi is stated purely in terms of *Attributes*
(§9), with no Option/OptionValue count given for this family specifically, unlike (for
example) some families where fabric options are separately counted. **Evidence needed:**
`SELECT DISTINCT [Option].OptionId, [Option].Name FROM [Option] WHERE ProductCategoryId
= 1239` (or the global-category fabric options `8`/`28`, per `09_Options.md`
BR-OPT-002/BR-CFG-012, if Nevi has fabric-selectable components) against a live PDM DB.

### 6. Dependencies

**UNKNOWN** whether `DependentOptionValues`/`DependentAttributeValues`/
`AttributeValueExclusions` rows exist for any of the 18 Nevi attributes or their values —
no dependency-edge data for this specific family was recorded in
`SKU_Config_Decode_Findings.md` (which focused on SKU decode, not dependency-graph
content). The *mechanisms* are real and populated in PDM generally (file 06), but **whether
Nevi/DWE4 specifically has populated dependency/exclusion rows is UNKNOWN** from the
evidence gathered in this pass. **Evidence needed:** `fetch_option_option_dependencies` /
`fetch_attribute_option_dependencies` / `fetch_attribute_value_exclusions` (per
`repositories/pdm_repository.py:681-744`) run against the Nevi product id(s), once step 1's
GAP is resolved.

### 7. Configuration / order code

**FACT:** the position-based decoder (file `services/engineering/engineering_class_service.py`
`decode_config_codes_by_position`, per `SKU_Config_Decode_Findings.md` §6) resolves
`DWE42AN4YSNBADNN` correctly at **3/3** matched attributes in the validation run cited — the
only concrete "configuration code" result recorded for this exact SKU. The general
mechanism: group same-head-length products, find which head positions flip for
single-attribute-differing pairs, assign ownership by ≥90% flip consistency, and read each
value's code from its owned contiguous position span (§6 in full).

**GAP:** the *specific* 3 attribute/value pairs and their resolved position spans for this
SKU were not restated in the source finding (only the aggregate "3/3" pass count). **Evidence
needed:** re-run `EngineeringClassService.config_code_layout` for this product/SKU and read
`snapshot.config_value_codes` (per §7 of `SKU_Config_Decode_Findings.md`, "Stored filter
relation — `config_value_codes`").

### 8. Base / final article

**INFERENCE (per file 04's established model):** the "base article" for this SKU is the
`DWE4`-prefixed identity shared by all 69 active products in the family (the part of the
head that "never varies within the structure," per `SKU_Config_Decode_Findings.md` §6),
and the "final article number" would be the pCon-side Code-Scheme-generated concatenation
of that base with a variant code derived from the same 18 attribute values already decoded
in steps 3-7. **No pCon-side generation was performed or observed for this SKU** — this is
an inference from file 04's general model, not a fact specific to Nevi. **GAP: UNKNOWN**
whether `DWE4` (or a longer prefix) is the actual base-article boundary for this family, and
whether a `CodeScheme` has ever been authored/exported for Nevi at all. **Evidence needed:**
inspect `tCOMd_Article`/`tCOMd_CodeScheme` rows (if any pCon MDB workspace exists for the
Nevi/DWE4 program) or `Product_Code`/`ProductRange.OrderCodeFormatString` for category 1239.

### 9. Relation Object

**GAP, entirely unresolved for this specific family.** No Relation Object (`tCOMd_RelObj`/
`tCOMd_Relation`/`tCOMd_RelObjRel`) content for Nevi/DWE4 was found or generated in any
evidence gathered — this would only exist once (a) the family's attribute/option data is
loaded into an MK Workbench snapshot and (b) `EngineeringRelationService.build_relation_objects`
/ `EngineeringValueTableService.build_dependency_tables` are run against it (mechanisms
documented generically in files 06/07, never traced against Nevi specifically in this pass).
**Evidence needed:** load the DWE4 family into an MK Workbench snapshot (via
`PDMSnapshotService.build_snapshot`, per `docs/PDM_MDB_Engineering/02_PDM_Data_Model.md`)
and inspect `snapshot.relation_objects` and `snapshot.value_tables` after running the
generators.

### 10. MDB

**GAP.** No live `pcr_data_com_ocd.mdb` (or Nevi-specific workspace) content was read in
this investigation. If step 9's snapshot were exported via `OcdExportService.export`, the
resulting `tCOMd_Article`/`tCOMd_Class`/`tCOMd_Property`/`tCOMd_PropValue`/`tCOMd_ArtBase`
rows would be the MDB-side landing point per file 02's general structural model — but this
was not executed or observed for Nevi. **Evidence needed:** run the export pipeline against
a loaded DWE4 snapshot and inspect the resulting MDB tables (or query a real
Herman Miller/Nevi `pcr_data_com_ocd.mdb` workspace if one exists on the pCon side).

### 11. pCon Creator concept

**GAP.** No pCon.creator UI session or manual example specific to Nevi/DWE4 was available
in any source read across all four investigation tracks (01/02/07/09) or this one — the
manual (`01_...md`) is generic/EasternGraphics-authored, not Herman Miller/Nevi-specific.
Once step 10's MDB rows exist, the pCon.creator "Article properties"/"Property classes"/
"Relations" dialogs (per `01_...md` §1, §8-10) would be how a human editor would see this
same Nevi configuration surfaced inside the tool. **Evidence needed:** open a real
pCon.creator workspace containing Nevi/DWE4 data (if one exists in the Herman Miller pCon
environment) and screenshot/document the Article/Property Class/Relation dialogs for this
family.

---

## Summary of where the trace breaks

| Step | Status | What's needed to close the gap |
|---|---|---|
| 1. PDM Product | GAP (exact ProductId) | Live query scoped to ProductCategoryId 1239 |
| 2. Item/SKU | FACT (string), GAP (head/tail split point) | Live decode run against this exact Item |
| 3. Properties | FACT (count: 10 functional + 8 physical), GAP (names) | Live Attribute query for category 1239 |
| 4. Property values | FACT (mechanism: 1 value/attribute), GAP (actual values) | Live decode/config_value_codes run |
| 5. Options/Option values | UNKNOWN (whether Nevi uses Options at all) | Live `[Option]` query for category 1239 |
| 6. Dependencies | UNKNOWN (whether populated for Nevi) | Live dependency-table queries scoped to Nevi products |
| 7. Configuration code | FACT (3/3 decode pass), GAP (specific spans) | Re-run `config_code_layout` for this SKU |
| 8. Base/final article | INFERENCE only | Inspect CodeScheme/Product_Code for category 1239 |
| 9. Relation Object | GAP (not generated/observed) | Load DWE4 into a snapshot, run generators |
| 10. MDB | GAP (not generated/observed) | Run export pipeline, inspect MDB rows |
| 11. pCon Creator | GAP (no session/example available) | Open a real Nevi-populated pCon workspace |

**Bottom line:** real Nevi identifiers exist and anchor the first half of this trace (real
SKU `DWE42AN4YSNBADNN`, real category "Nevi Dach"/1239, real family `DWE4`, a verified
10-functional/8-physical attribute split, and a verified 3/3 position-decode result) — this
is genuine production data, not invented. The second half of the trace (Options,
Dependencies, Relation Object, MDB, pCon Creator) could not be completed with real Nevi data
in this pass because no live PDM/MDB/pCon query was executed here; those steps are marked
GAP with the specific query/action that would close each one, rather than filled with
placeholder or invented identifiers.
