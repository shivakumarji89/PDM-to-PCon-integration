# 13 — Unknowns & Decisions Register

**Status:** Forensic register, evidence-only. No code changed. This file **consolidates**
every UNKNOWN/GAP/disagreement flagged across files 01-12 into one table. It resolves
nothing — it is a register, not a design document. "Blocks automation?" is derived from
file 11's classification (B/C/D items are blocked in the sense that generation cannot
proceed unconditionally; A items are not listed here at all unless a secondary ambiguity
was also flagged for them).

**Columns:** ID · What's unknown · Raised in · Evidence that would resolve it · Blocks
automation (per file 11) or is a pure decision.

---

| ID | What's unknown / gap | Raised in | Evidence that would resolve it | Blocks automation or needs a decision? |
|---|---|---|---|---|
| U1 | Whether the pCon.creator manual actually used (2.22.0.125) has any content differences from a true 2.22.2 build | Doc 01 §0.1 | An official 2.22.2-stamped manual or changelog, or direct verification against a running 2.22.2 application | Neither — a documentation-provenance caveat; affects confidence of everything downstream, not a specific automation decision |
| U2 | Whether "MDF" (task brief term) was a misnomer for MDB, or refers to a distinct EasternGraphics artifact never covered by the manual sections read | Doc 01 §0.3, §15; doc 09 §0, §6 item 1 | Ask whoever commissioned the original "MDF" framing; alternatively locate a EasternGraphics artifact literally named MDF | Decision — must be confirmed before any external-facing documentation uses "MDF" again (this investigation already treats it as settled internally: not a real format) |
| U3 | Whether pCon.creator ever internally writes/reads `tCOMd_Option`/`tCOMd_OptionValue` anywhere in its own ecosystem (vs. being vestigial/legacy tables) | Doc 01 §7 | Inspect a live pCon.creator-authored MDB or ask EasternGraphics support | Blocks automation (D) — do not build an Option write path until this is resolved, since building one against unused tables would be wasted/misleading effort |
| U4 | Whether "Select condition" (manual UI, prose) shares `RelationObj.Type` code `1` with Precondition, or is not exportable via this table at all | Doc 01 §10 | Live OCD 4.3 export sample, or a direct read of `docs/pcon_reference/ocd_4.3_en.md` §2.15-2.16 reconciled against the manual page | Blocks automation (C, doc 11) — cannot safely auto-generate Selection condition relations without knowing the correct type code |
| U5 | Post-Reaction relation-type export code — six types named in UI prose, only five codes shown in the `RelationObj.Type` field table | Doc 01 §10; doc 09 §6 item 2 | Same as U4 | Blocks automation (C) — same reason |
| U6 | Taxation domain code letter on `RelationObj.Domain` — no letter shown for a named UI domain | Doc 01 §9; doc 09 §6 item 3 | Live OCD 4.3 export sample or spec reconciliation | Blocks automation (D for Tax-domain relations generally) |
| U7 | Whether "variant condition" ($VARCOND, pricing/packaging activation string) and "variant code" (Code-Scheme-generated) are always the same string | Doc 01 §3; doc 04 Q6 | The manual's own wording is ambiguous ("may contain... or..."); would need a live example or EasternGraphics clarification | Decision-adjacent — affects whether MK Workbench should treat them as one derivation or two; classified C in doc 11 |
| U8 | Whether "variant code" and XCF's "variant key" (`Variant.csv`) are the same string in all cases | Doc 01 §3; doc 09 §3 item 5 | Same as U7 — concrete sample file or EasternGraphics clarification | Same as U7 |
| U9 | Whether PDM's `Item.Item` code is ever literally reused, unmodified, as a pCon final article number, or whether separators/schemes differ | Doc 04 Q5 | A round-trip test per file 12 §1.2 using a real family | Blocks automation (B, doc 11) — needed before auto-generating a `CodeScheme` that assumes PDM's own separators |
| U10 | Whether MK Workbench's decoded `config_value_codes` are byte-for-byte what a `CodeScheme`-driven pCon final-article-number would produce | Doc 03 Configuration code row | Same round-trip test as U9 | Same as U9 |
| U11 | Whether PDM's Attribute model has anything corresponding to pCon's four `Usage` scopes (Configuration/Relation/Graphic/Display) | Doc 01 §5 | A live PDM schema/business-rule read specifically targeting Attribute classification beyond Configuration-scope | Decision — affects whether Relation/Graphic/Display-scoped properties can ever be auto-classified, or must always be Review Required |
| U12 | Whether PDM models value *ranges/intervals* at all (vs. flat discrete values only) | Doc 01 §6; doc 05 Q1 | A live PDM schema read for any interval-shaped column on `AttributeValue`/`OptionValue` | Blocks automation (D, doc 11) for interval-typed PropertyValues |
| U13 | Whether OCD import validates a minimum of 1 PropertyValue per Property | Doc 05 Q1 | A live OCD import test with a zero-value property, or EasternGraphics documentation | Neither — low-impact edge case; decision if it ever becomes a real scenario |
| U14 | Whether PDM's schema *could* represent multi-value-per-attribute in some family not yet traced (all traced examples are single-value-per-attribute) | Doc 05 Q2 | A live PDM query across more product families specifically checking for `AttributeValueId` cardinality > 1 per `(Item, AttributeId)` | Decision-adjacent — if found, would require rethinking Q2/Q3's "no" answer entirely |
| U15 | Whether `EngineeringValueTableService.build_dependency_tables` (or any other service) consumes `snapshot.attribute_option_dependencies` (`DependentAttributeValues`-sourced edges) | Doc 05 Q6; doc 06 §2 | A full grep of every consumer of `attribute_option_dependencies` across `services/` (not exhaustively performed in this investigation) | Blocks automation (B, doc 11) — must confirm before claiming this mechanism is exported |
| U16 | Whether any code consumes `snapshot.attribute_value_exclusions` to generate a Constraint or omit invalid rows from a value-combination table | Doc 06 §3 | Same targeted grep, plus a design decision on which of the two implementation strategies (explicit Constraint vs. implicit omission) to use | Blocks automation (C, doc 11) — both a confirmation gap and a design ambiguity |
| U17 | Whether any service fetches/models `CatalogueProductOptionExclusions` or `CatalogueItemOptionExclusions` at all | Doc 06 §5 | A grep of `repositories/pdm_repository.py` and `services/` for these table names (none found in this pass) | Blocks automation (D, doc 11) — no fetch path exists yet, this is a build gap not just an export gap |
| U18 | Whether real manufacturer MDB packages ever exercise `tCOMd_RelObjRel`'s many-to-many generality (vs. the current generator's always-1:1:1 triples) | Doc 07 §1.2 | Inspect a live, hand-authored `pcr_data_com_ocd.mdb` | Decision — affects whether the canonical model's relation-binding shape needs to support many-to-many, or 1:1:1 is sufficient forever |
| U19 | Whether the MDB's `com_RelationBody` memo/text column truly has no size constraint (unlike XOCD's 255-char block chunking) | Doc 07 §1.2 | Inspect the live Access column type/definition | Neither — low-risk implementation detail, resolves itself on first real large-body test |
| U20 | Whether the current relation classification's narrow authoring standard (Precondition/value + Action/code + Action/price only) is sufficient for the manufacturer's *real* MDB packages, or whether Selection condition/Constraint/Reaction/Post-Reaction/BOI/Packaging/Tax are actually needed | Doc 02 §3.1 (explicit: "not verified against a live PDM/MDB database in this investigation") | Access the live PDM DB referenced in this repo's memory (separate investigation track) and/or inspect real manufacturer MDB packages | Blocks automation (D for the missing types, doc 11) — this is the single highest-leverage unknown for scoping future engineering work |
| U21 | Whether `Table`/`TableColumn`/`TableLine` are truly name-joined (not surrogate-key-joined) to `Property`/`PropValue` in all cases | Doc 02 §2 row 30 (flagged INFERENCE) | A live MDB read, or the first Stage-1 round-trip test per file 12 §1.13 | Decision-adjacent — affects how the canonical model represents value-combination-table bindings |
| U22 | Whether `tCOMd_ArtBase`'s string-keyed (not ID-keyed) convention is the manufacturer's real MDB schema convention, or an artifact of this exporter's own implementation choice | Doc 02 §4 item 4 | Inspect a live/hand-authored MDB's `ArtBase` table definition | Decision-adjacent — affects whether a future refactor could safely move `ArtBase` to ID-keying |
| U23 | Whether `mdb_reverse_engineering_service.import_snapshot`'s RelObj/RelObjRel/Relation FK-chain parsing logic is correct, since no automated test exercises it (only `.read()` is tested) | Doc 02 §4 item 8 | Write/execute the missing test, or run Stage 2 of file 12's validation sequencing | Blocks confidence in round-trip claims generally, not a specific mapping's automation status |
| U24 | Whether the "preserve if already imported/edited" all-or-nothing guard causes real regressions when new PDM values/properties are added to a snapshot that already has imported exotic relation objects | Doc 07 §7 | Run file 12 §1.8's Stage 2 test sequence (import exotic MDB → add new PDM value → re-export → check) | Decision — this is a live, currently-unverified risk requiring a product decision on merge behavior, not just a data gap |
| U25 | Exact `ProductId` for the product generating SKU `DWE42AN4YSNBADNN` | Doc 08 step 1 | Live query: `SELECT ProductId, Product FROM Product WHERE ProductRangeId IN (SELECT ProductRangeId FROM ProductRange WHERE ProductCategoryId = 1239)` | Blocks the rest of the Nevi trace (D, doc 08 summary table), not a general-automation blocker |
| U26 | Exact head/tail split boundary for SKU `DWE42AN4YSNBADNN` | Doc 08 step 2 | Live decode run for this exact Item | Same as U25 |
| U27 | Names of the 18 Attribute rows contributing to the Nevi/DWE4 family | Doc 08 step 3 | `SELECT attr.Name, attr.AttributeType FROM Attribute attr WHERE attr.ProductCategoryId = 1239 ORDER BY attr.DisplayOrder` | Same as U25 |
| U28 | Specific `AttributeValueId`s/names selected for SKU `DWE42AN4YSNBADNN` | Doc 08 step 4 | Live `config_value_codes`/`resolve_config_codes` run, pending U25 | Same as U25 |
| U29 | Whether Nevi/DWE4 uses PDM's `[Option]`/`OptionValue` mechanism at all | Doc 08 step 5 | `SELECT DISTINCT OptionId, Name FROM [Option] WHERE ProductCategoryId = 1239` | Same as U25 |
| U30 | Whether `DependentOptionValues`/`DependentAttributeValues`/`AttributeValueExclusions` rows exist for any Nevi/DWE4 attribute or value | Doc 08 step 6 | `fetch_option_option_dependencies`/`fetch_attribute_option_dependencies`/`fetch_attribute_value_exclusions` scoped to Nevi products, pending U25 | Same as U25 |
| U31 | Specific 3 attribute/value pairs and position spans resolved for SKU `DWE42AN4YSNBADNN`'s 3/3 decode pass | Doc 08 step 7 | Re-run `EngineeringClassService.config_code_layout`, read `snapshot.config_value_codes` | Same as U25 |
| U32 | Whether `DWE4` (or a longer prefix) is the actual base-article boundary for this family; whether a `CodeScheme` has ever been authored/exported for Nevi | Doc 08 step 8 | Inspect `tCOMd_Article`/`tCOMd_CodeScheme` rows for any existing Nevi pCon workspace, or `ProductRange.OrderCodeFormatString` for category 1239 | Same as U25 |
| U33 | Whether Nevi/DWE4's Relation Objects have ever been generated/observed | Doc 08 step 9 | Load DWE4 into an MK Workbench snapshot via `PDMSnapshotService.build_snapshot`, run generators, inspect `snapshot.relation_objects`/`value_tables` | Same as U25 |
| U34 | Whether Nevi/DWE4 has ever been exported to a live MDB | Doc 08 step 10 | Run the export pipeline against a loaded DWE4 snapshot, inspect resulting `tCOMd_*` rows | Same as U25 |
| U35 | Whether a real pCon.creator session/workspace exists containing Nevi/DWE4 data | Doc 08 step 11 | Open a real Herman Miller pCon environment workspace for Nevi/DWE4, if one exists | Same as U25 |
| U36 | Whether the pCon.creator "workspace" file format is confirmed as Access `.mdb` by the manual itself (vs. carried over from pre-existing local analysis, unverified against manual p.21 "Directory structures in data creation projects") | Doc 01 §16; doc 09 §6 item 6 | Read manual p.21 in full | Neither — documentation-provenance caveat, doesn't block any specific mapping |
| U37 | Whether a full round-trip (OCD CSV → MDB workspace → EBASE release → re-import) preserves every field, especially the "imported but not evaluated at runtime" ones (`ScaleQuantity`, `Multioption`, `HintTextID`, `LineFormat`) | Doc 09 §6 item 7 | Execute file 12's Stage 3 (real pCon.creator human pass) and diff | Decision-adjacent — "not evaluated at runtime" is a different claim than "preserved on re-export"; needs an actual test, not an assumption either way |
| U38 | Field-level deltas between the OCD 4.0 table set (fully reproduced in doc 09) and OCD 4.1/4.2/4.3 | Doc 09 §2.15 note, §6 item 4 | Read manual pp.392 (4.1-4.3 delta sections) and/or reconcile against `docs/pcon_reference/ocd_4.3_en.md` | Neither directly, but affects confidence of every OCD-4.0-sourced field claim in docs 01-12 if this codebase in fact targets 4.3 |
| U39 | Whether the local `docs/pcon_reference/database_relationships/*` and `docs/PDM_MDB_Engineering/06_OCD_Integration.md` describe a replaced-prior architecture or a never-built planned one | Doc 02 §0 | Git history / commit archaeology, or asking whoever wrote those docs | Neither — historical-provenance question; already resolved operationally (treat as stale, use live code) |
| U40 | Whether PDM's Product↔Item split is genuinely 1:1 with pCon's BaseArticle↔FinalArticleNumber split, or PDM's "final article number" is closer to a different concept entirely | Doc 01 §2; doc 03 Product/Article row | Direct comparison against `docs/SKU_Config_Decode_Findings.md` plus a live round-trip test (file 12 §1.2) | Blocks automation (B, doc 11) for the Product→Article mapping |

---

## Disagreements found during synthesis of this register

One internal tension across the prior docs is worth naming explicitly rather than
silently resolving, per the task's own instruction to document disagreement rather than
paper over it:

- **Doc 02 §3.1** states plainly that whether the manufacturer's real MDB packages need
  the missing relation types (Selection condition/Constraint/Reaction/Post-Reaction,
  BOI/Packaging/Tax domains) is "UNKNOWN — not verified against a live PDM/MDB database in
  this investigation," explicitly deferring to the separate live-PDM investigation track
  named in this repo's memory. **Doc 07 §6**, working from the same underlying codebase,
  goes further and asserts these types "cannot be safely automated" because "none of that
  intent is captured anywhere in the current source data" — a stronger, more definitive
  claim than doc 02's "unknown, unverified." These are not strictly contradictory (doc 07's
  claim is about whether the *data to auto-generate* exists; doc 02's is about whether the
  *output* is even needed) but they carry different weight, and a reader could come away
  with either "we don't know if this matters" (doc 02) or "this definitely needs a human"
  (doc 07). This register does not resolve which framing is correct — both are preserved as
  U20 above, tagged as the single highest-leverage unknown, precisely because the two docs'
  emphasis differs even though their underlying facts do not conflict.
