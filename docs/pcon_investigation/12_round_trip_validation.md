# 12 — Round-Trip Validation Strategy

**Status:** Forensic synthesis, evidence-only. No code changed. Designs a validation
approach for **PDM → MK Workbench → MDB/OCD → pCon Creator → exported MDB/OCD → MK
Workbench**, explicitly aware — per files 02, 06, 07 — that the *current* MK Workbench
exporters are known-incomplete (2 of 6 relation types, no `tCOMd_Option` write path, no
`AttributeValueExclusions`/`CatalogueProductOptionExclusions`/`CatalogueItemOptionExclusions`
export). This is a plan for validating what exists and for detecting silently-dropped or
silently-altered data — it is not a "the file opens in pCon.creator" smoke test.

---

## 0. The round-trip stages, restated with real components

```
PDM (live DB)
  │  repositories/pdm_repository.py fetch_*
  ▼
MK Workbench Snapshot (canonical model, file 10)
  │  services/engineering/* generators
  ▼
MDB/OCD export ── ocd_export_service.py (MDB) / xocd_export_service.py (CSV)
  │
  ▼
pCon.creator import (manual §10/§11) ── EDITED / GENERATED / RE-EXPORTED by a human
  │  "Export to OFML" (manual §5.3.21) / release dataset (§8.3.2, EBASE + ZIP)
  ▼
Exported MDB/OCD (post-pCon.creator)
  │  mdb_reverse_engineering_service.py .read() / .import_snapshot()
  ▼
MK Workbench Snapshot (re-imported)
```

Because stage 3→4 (pCon.creator import/edit/re-export) happens **outside** this codebase,
a full closed-loop automated round-trip cannot be executed by MK Workbench alone. The
validation strategy below therefore splits into: (a) checks MK Workbench can run
end-to-end without a human touching pCon.creator (stages 1-3, 5-6), and (b) checks that
require a human-in-the-loop pCon.creator pass (stage 3→4), each named explicitly.

---

## 1. Per-entity-type validation plan

For each entity, the table gives: what to compare, how a mismatch is detected, and the
gap-awareness note (what's *already known* to be incomplete, so a "mismatch" there is
expected, not a bug).

### 1.1 Articles (base article)

- **Compare:** `com_ArticleCode`, `com_CodeSchemeID`, `com_PackageID`, `com_ComGroupID`,
  `com_ShortTextID`/`com_LongTextID` before export vs. after re-import.
- **Detection:** exact string/FK equality on re-import; `mdb_reverse_engineering_service.py`
  already reads this table (`STRUCTURAL_TABLES`, file 02 §1) — diff the reconstructed
  `Snapshot.articles` against the pre-export `Snapshot`.
- **Gap-awareness:** `com_RelObjID` on Article is **always written `None`** by the current
  exporter (file 02 §2 row 6) — a round-trip test must not expect an article-level relation
  binding to survive, because none was ever written. This is a known limitation, not a
  round-trip failure to chase.

### 1.2 Base Article Number vs. Final Article Number

- **Compare:** there is **no separate final-article row to compare** (file 04 bottom line)
  — the only thing to validate is that the base article number is preserved exactly, and
  that a *generated* final article number (base + `VarCodeSep` + variant code, per
  `CodeScheme`) can be reproduced from the re-imported `CodeScheme`/`Property`/`PropValue`
  rows using the same grammar.
- **Detection:** for at least one real family, compute the final article number twice —
  once from the pre-export `Snapshot`'s `config_value_codes` + `CodeScheme` fields, once
  from the re-imported equivalent — and diff the strings.
- **Gap-awareness:** doc 03/04 flag this as **UNKNOWN, never round-tripped** even once
  ("no round-trip test was performed in any prior track"). This is priority #1 for a first
  real validation run, since it is foundational and currently has zero test coverage.

### 1.3 Config codes / variant codes

- **Compare:** `config_value_codes` (property_id → value_id → code) before vs. after.
- **Detection:** since these are generated from `EngineeringClassService`'s position-based
  decode (file 03 Configuration code row), re-run the decode against the re-imported
  `Property`/`PropValue` rows and diff against the original.
- **Gap-awareness:** doc 08 shows this decode has only been spot-checked (3/3, 5/5 on two
  real SKUs) — round-trip validation should use those same two already-verified SKUs first
  (`DWE42AN4YSNBADNN`, `DWE36DT4YSNMNDL`) before extending to unverified families.

### 1.4 Properties

- **Compare:** `com_PropertyID`→`com_ClassID` FK, `Type`, `Digits`/`DecDigits`,
  `Obligatory`, `AddValues`, `Restrictable`, `Multioption`, `Scope`.
- **Detection:** row-for-row diff after re-import (`STRUCTURAL_TABLES`, file 02 §1).
- **Gap-awareness:** `com_RelObjID` and `com_HintTextID` on Property are **always written
  `None`** (file 02 §2 rows 13-14) — expect them null; a re-imported MDB that has real
  values there (e.g. hand-authored by pCon.creator) is exactly the "one-way capability gap"
  doc 07 §7 already names: MK Workbench's own exports will never populate them, so any
  round-trip test using an MK-Workbench-originated MDB will trivially match (both `None`),
  while a round-trip test using a **hand-authored** MDB is the one that actually exercises
  this gap and should be run separately.

### 1.5 Property Values

- **Compare:** composite key `(PropertyClass, PropertyName, OpFrom, ValueFrom, OpTo,
  ValueTo, Raster)`, `IsDefault`, `com_RelObjID`.
- **Detection:** row diff.
- **Gap-awareness:** doc 01 §6/doc 03 confirm **neither generator ever emits an interval**
  (`OpFrom` is always `"EQ"`, no `OpTo`/`ValueTo`/`Raster`). A round-trip test must use
  exact-match values only for anything MK-Workbench-originated; testing interval round-trip
  requires a hand-authored MDB as the *source* of the interval, since MK Workbench cannot
  currently produce one to test against itself.

### 1.6 Options-as-properties (the collapse)

- **Compare:** that a PDM `Option`/`OptionValue` pair, after passing through
  `tCOMd_Property`/`tCOMd_PropValue` with `com_PropTypeCode` marking, still resolves back
  to "this was originally a PDM Option" on re-import (provenance), not just "this is *a*
  property value."
- **Detection:** this is the item file 10 §4 flags as the missing explicit Option-collapse
  layer — until that layer exists and states its own provenance-preservation contract,
  there is **no defined comparison to perform here beyond generic Property/PropertyValue
  equality** (§1.4/§1.5 above). Recommend: do not attempt to validate Option-specific
  round-trip fidelity until the collapse layer (file 10 §4) is built and its provenance
  contract is written down.
- **Gap-awareness:** `tCOMd_Option`/`tCOMd_OptionValue` themselves are **never written** by
  either exporter (file 02 §1) — do not test round-trip of those two tables; they are out
  of scope by design, not a bug to find.

### 1.7 Dependencies

- **Compare:** for `DependentOptionValues`-sourced value-combination tables — that the same
  parent/dependent value sets reconstruct after re-import; for `DependentAttributeValues`
  and `AttributeValueExclusions` — **there is currently nothing to compare**, because
  neither is confirmed to reach export (files 05 Q6, 06 §2-3).
- **Detection:** for `DependentOptionValues`: diff `snapshot.option_option_dependencies`-
  derived table rows before vs. after re-import of `tCOMd_Table`/`TableColumn`/`TableLine`.
  Note per file 02 §2 row 30 these are **name-joined, not surrogate-key-joined** — a
  round-trip test must match on `com_ColumnName`/`com_TableLineValue` strings, not IDs.
- **Gap-awareness (must be stated in the test report, not silently passed over):** a
  round-trip test that finds *zero* `AttributeValueExclusions`- or
  `CatalogueProductOptionExclusions`/`CatalogueItemOptionExclusions`-derived rows in the
  exported MDB is **expected, given known gaps**, not evidence the round-trip "passed" for
  those mechanisms. The validation report must distinguish "matched because both sides
  correctly have nothing" from "matched because the check wasn't capable of finding a
  real difference."

### 1.8 Relation Objects / Relation bodies

- **Compare:** `(RelObjID, RelName, Type, Domain)` + linked `Relation.CodeBlock`/
  `com_RelationBody`, and the entity-binding column that references each `RelObjID`
  (`PropValue.com_RelObjID` — the only one ever populated).
- **Detection:** diff the `RelObj`/`Relation`/`RelObjRel` triple's structural shape
  (file 07 §1.2) before vs. after; for XOCD, diff by `RelName`==`RelationName` linkage
  (file 02 §3.2) since there is no join table on that side.
- **Gap-awareness (critical — this is the single most consequential gap for validation
  design):** only **type codes 1 (Precondition) and 3 (Action)**, domains **C and P**, are
  ever generated (file 02 §3.1, file 07 §3). A round-trip test comparing MK-Workbench-
  originated exports against themselves will **never exercise** Selection condition (2),
  Constraint (4), Reaction (5), Post-Reaction, or BOI/PCKG/TAX domains — because neither
  side of that comparison ever produces them. **This must be tested with a hand-authored
  or third-party MDB as the *input*, not an MK-Workbench-generated one**, specifically to
  exercise the "preserve if already imported/edited" all-or-nothing guard (file 07 §7,
  `ocd_export_service.py:663-665`): import a hand-authored MDB with exotic relation types
  → confirm `Snapshot.relation_objects` contains them → re-export → confirm they survive
  unchanged (the guard should pass them through) → **then** add a new PDM value to the same
  snapshot and re-export again → confirm whether the new value's canonical Precondition/
  Action relation is added, or whether (per the "all-or-nothing" risk named in file 07 §7)
  the entire canonical-derivation step is skipped because `relation_objects` is non-empty.
  This last check is the one place round-trip validation can find a **real, currently-
  unverified regression risk**, not just an already-known gap.
- **Post-Reaction and Taxation-domain-letter ambiguity (doc 01 §10, doc 09 §6):** a
  round-trip test cannot resolve these — they are **documentation** ambiguities in the
  target format itself. The validation plan should record "not testable without a live OCD
  4.3 export sample" rather than attempting to assert a pass/fail here.

### 1.9 Classes (Property Classes)

- **Compare:** `com_ClassID`→`com_PackageID`, `Position`, `Name`, `TextID`, `com_RelObjID`.
- **Detection:** row diff.
- **Gap-awareness:** `class_name` on the PDM side is inferred from property text, not
  sourced (file 03 Class row) — a round-trip test comparing MK-Workbench-exported class
  names against themselves will trivially "pass" regardless of whether the inferred names
  are actually correct/stable business-wise. This is a case where round-trip equality is
  **not** sufficient evidence of correctness — flag it explicitly in the test report, and
  treat class-name correctness as a separate Review Required check (file 11, class C),
  not a round-trip check.

### 1.10 Prices

- **Compare:** `(ArticleID, Variantcondition, Type, Level)` composite key, `PriceValue`,
  `FixValue`, `Currency`, `Rule`, `RoundingID`.
- **Detection:** row diff, opt-in per `include_prices` flag (file 02 §1).
- **Gap-awareness:** `ScaleQuantity` is documented as "not evaluated by OFML runtime in OCD
  4.0 stage 1... won't be imported" (doc 09 §2.6) — do not treat its absence/blankness on
  re-import as a mismatch; it is a documented no-op field, not a round-trip failure.
  `tCOMd_PriceList2` is template-kept, never generated (file 02 §2 row 27) — exclude it
  from any generated-content diff.

### 1.11 Text

- **Compare:** `TextID`, `Language`, `LineNr`, `Textline` across all seven text tables.
- **Detection:** row diff, sorted by `(TextID, Language, LineNr)` per the manual's explicit
  ordering requirement (doc 09 §2.12) — an unordered diff could produce false mismatches.
- **Gap-awareness:** `LineFormat` is documented as "not evaluated by OFML runtime in OCD
  4.0 stage 1, not imported" (doc 09 §2.12) — exclude from pass/fail. Multilingual text is
  currently synthesized on write, not sourced from real PDM descriptions (doc 03 Text row)
  — a round-trip test will show perfect self-consistency (synthesized text survives
  re-import unchanged) without validating that the synthesized text is *correct* business
  content; this must be flagged as a separate content-quality concern, not conflated with
  round-trip structural fidelity.

### 1.12 Article Restrictions (`ArtBase`)

- **Compare:** `(ArticleID, PropertyClass, PropertyName, PropertyValue)` rows.
- **Detection:** row diff, matching on the **string** fields (`com_ClassName`,
  `com_PropName`, `com_PropValue`), not surrogate IDs — file 02 §2 row 22/§4 item 5
  explicitly flags `ArtBase` as the one table that is name-keyed, not ID-keyed. A
  round-trip comparison tool that assumes uniform ID-based joins (as it may for every
  other table) will silently fail to match `ArtBase` rows correctly unless coded for this
  divergence specifically.
- **Gap-awareness:** none beyond the naming-collision caveat itself (doc 01 §12: "Article
  Base" ≠ "ArtBase table" — make sure the validation report uses "ArtBase table restriction"
  consistently to avoid conflating with base-article-number identity, §1.2 above).

### 1.13 Value combination tables

- **Compare:** `Table`/`TableColumn`/`TableLine` triple, name-joined to
  `com_PackageID` only (no FK back to `Property`/`PropValue` — file 02 §2 row 30).
- **Detection:** row diff on `com_ColumnName`/`com_TableLineValue` strings.
- **Gap-awareness:** confirm this string-based join, not assumed — file 02 explicitly
  flags it as INFERENCE ("confirm at runtime against a live MDB if precise semantics
  matter"). This is itself a round-trip validation task: the first real round-trip run
  should confirm or refute this INFERENCE and update file 02/13 with the result.

---

## 2. Test sequencing recommendation

1. **Stage 1 (self-consistency, no pCon.creator needed):** PDM → Snapshot → MDB export →
   `mdb_reverse_engineering_service.read()` → diff. Exercises §1.1-§1.6, §1.9-§1.13 fully;
   exercises §1.7-§1.8 only for the two implemented mechanisms (`DependentOptionValues`,
   Precondition/Action-domain-C/P).
2. **Stage 2 (hand-authored-MDB-in):** take (or construct, if none exists) a hand-authored
   or third-party `pcr_data_com_ocd.mdb` using Selection condition/Constraint/Reaction/
   Post-Reaction/BOI/PCKG/TAX, import via `mdb_reverse_engineering_service.import_snapshot`,
   re-export, diff. This is the only way to exercise §1.4 (property-level `RelObjID`
   round-trip), §1.6 interval values, and §1.8's "preserve" guard interaction with new
   values (file 07 §7's flagged risk).
3. **Stage 3 (real pCon.creator human pass):** export a real family (Nevi/DWE4 recommended,
   since it already has verified real identifiers per doc 08) to MDB, open in pCon.creator,
   make no changes, re-export/release, re-import, diff. This validates the one link no
   automated test can reach — that pCon.creator itself accepts and returns the MK Workbench
   export unchanged. Doc 08 confirms this has **never been executed** for Nevi/DWE4 to date.
4. Record every gap-aware "expected non-match" (this file, throughout) in a fixed checklist
   so that future test runs distinguish "known incomplete, not a regression" from "new
   regression" — do not let the two categories blur across test runs.
