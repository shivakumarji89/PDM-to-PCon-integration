# 11 — Automation Strategy

**Status:** Forensic synthesis, evidence-only. No code changed. Classifies every
relationship/mapping identified in files 03-08 into four buckets. Labels as established in
file 01 §0 (FACT/INFERENCE/UNKNOWN) are used for the *justification* of each classification,
not as a fifth axis.

**Classification key:**
- **A — 100% deterministic.** Auto-generate always; no missing input, no judgment call.
- **B — Deterministic conditionally.** Auto-generate, but only when named supporting
  evidence is present; falls back to Review Required (or is skipped) otherwise.
- **C — Ambiguous.** Review Required; name why (missing intent, unresolved manual
  ambiguity, unverified live behavior, etc.).
- **D — Unsupported / insufficient information.** Do not generate; name what's missing.

---

## A — 100% deterministic

| Mapping | Why it's fully deterministic | Evidence |
|---|---|---|
| Property → PropertyValue rows | Straight `(property, value)` fetch → `tCOMd_Property`/`tCOMd_PropValue` write; already implemented, mechanical | Doc 03 Property/Property Value rows; doc 02 §2 rows 11-16 |
| PDM Option/OptionValue → pCon Property (Usage=Configuration)/PropertyValue | Confirmed non-mapping resolved into a single deterministic collapse rule already implemented by both exporters (`com_PropTypeCode` marking) | Doc 03 Option/Option Value rows, "FACT, explicit non-mapping"; doc 02 §1, §3.1/§3.2 |
| Value-level Precondition for combination-classified values | "Fully mechanical/deterministic from article-set co-occurrence data" — doc 07's own words | Doc 07 §5 item 1, `engineering_relation_service.py:208-299` |
| Value→code Action for numeric/parametric properties | "Purely a lookup/mapping from source value codes" | Doc 07 §5 item 2, `engineering_relation_service.py:90-112` |
| Price variant-condition Action relations (`PA_PRICING`/`PA_<prefix>`) | "As close to already proven safe as anything in this codebase" — like-for-like port of PDM's own `VarCondThread`/`SuperProductVarCondRelation` | Doc 07 §5 item 3; doc 03 Price row |
| Base-article/ArtBase value classification (generic/base/combination split) | Deliberate, working division of labour already verified against real data | Doc 07 §2.2 item 3; doc 03 Article restriction row, "one of the more solid, verified mappings" |
| `DependentOptionValues` → value-combination table + Constraint relation object | Confirmed implemented end-to-end, chain-aware, deterministic from dependency-edge data | Doc 06 §1, doc 05 Q5/Q7 |
| Text-block `TextID` indirection shape | Pattern (not content) maps cleanly; a well-understood localization pattern | Doc 03 Text row |

**Caveat applying to all of A:** "deterministic" here means *the transformation logic is
mechanical given its inputs*, not that the inputs are complete. Several A-rated items still
depend on PDM providing real data (e.g. real multilingual text — see D below) even though
the *transformation* itself needs no judgment call.

---

## B — Deterministic only with complete supporting evidence

| Mapping | Required evidence to auto-generate | What happens if evidence is missing | Evidence |
|---|---|---|---|
| PDM Product/Item → pCon Article (base article number) | Confirmed which PDM field is the canonical base-article-number source, and that it is stable/unique per base | Currently an INFERENCE, not a proven 1:1 — doc 03 flags "Needs verification" | Doc 03 Product/Article row, doc 04 Q5 |
| `DependentAttributeValues` (cross-kind availability, Attribute value → Option value) → value-combination table/Constraint | Confirmation that `EngineeringValueTableService.build_dependency_tables` (or another service) actually consumes `snapshot.attribute_option_dependencies` | Currently UNKNOWN whether this edge kind reaches export at all — could be silently dropped | Doc 05 Q6, doc 06 §2 |
| Dependency chains (A depends on B depends on C) round-tripping identically between PDM's legacy chain logic and MK Workbench's per-level table generation | A concrete side-by-side test: legacy SIF exporter output vs. `build_dependency_tables` output for the same real chained family | Both sides "explicitly anticipate multi-hop dependencies," but "not proven to produce identical output for the same chain" | Doc 05 Q7 |
| Property-level Precondition mirroring an existing ArtBase-style restriction | A concrete decision to extend `_classify_and_bodies`-style logic to property scope, using the same head-property/base co-occurrence data already computed | Not currently implemented; doc 07 calls it "a natural, low-risk extension... not an evaluation of a concrete implementation" | Doc 07 §5 item 4 |
| `CatalogueProductOptionExclusions` → `ArtBase` restriction | A repository fetch method for this table (none exists today) plus confirmation the base-article grain matches `ArtBase`'s grain | Currently not fetched/modeled/exported at all | Doc 06 §5 |
| Variant code (pCon Code Scheme output) vs. PDM's decoded `config_value_codes` | A round-trip test proving byte-for-byte equivalence for at least one real family | "No round-trip verified" between the two independently-derived encodings | Doc 03 Configuration code row, doc 04 Q3 |
| Multilingual Class/Property text | Real PDM `OtherDescription`/`ProductDescription` rows sourced per language, replacing the current synthesized defaults | Currently "synthesized on write, not carried from PDM" | Doc 03 Text row |

---

## C — Ambiguous / Review Required

| Mapping | Why it's ambiguous (not just missing evidence) | Evidence |
|---|---|---|
| `AttributeValueExclusions` → Constraint `Restrictions:` clause / omitted value-combination rows | Two structurally different implementation choices exist (explicit Constraint vs. implicit omission) with no stated preference in any source, and no consumer exists yet to prefer either | Doc 06 §3, §6 |
| Whether "variant condition" ($VARCOND) and "variant code" (Code-Scheme-generated) are the same string | The manual itself is not crisp ("may contain... or...") — this is a genuine documentation ambiguity in the *target* system, not a PDM-side data gap | Doc 01 §3, doc 04 Q6, doc 09 §3 item 5 |
| Whether "variant code" and XCF's "variant key" are the same string in all cases | Same manual-sourced ambiguity, different table (`variant.csv` `Variant codes` field) | Doc 01 §3, doc 09 §3 |
| Post-Reaction relation-type export code | Manual names six types in prose but the `RelationObj.Type` field table enumerates only five codes — genuinely unresolved by the documentation available, requires a live OCD 4.3 export or spec reconciliation | Doc 01 §10, doc 09 §6 item 2 |
| Taxation domain code letter on `RelationObj.Domain` | Same class of documentation gap — Taxation is a named UI domain with no listed code letter | Doc 01 §9, doc 09 §6 item 3 |
| Whether real manufacturer MDB packages ever exercise `RelObjRel`'s many-to-many generality (one RelObj with multiple Relations, or vice versa) | Current generator always emits 1:1:1 triples; whether this is a real limitation or matches real-world usage is unverified without inspecting a live hand-authored MDB | Doc 07 §1.2 |
| Manually curated/edited relation objects | "By definition these represent a human override" — the whole point of the escape hatch is that it must stay human-authored; auto-generation would defeat its purpose | Doc 07 §6 item 4 |
| The "preserve if already imported/edited" all-or-nothing guard's interaction with newly-added PDM values/properties after import | Whether stale exotic relations should be refreshed and new canonical relations added when a snapshot already has *some* relation objects is a product decision, not a data question | Doc 07 §7, doc 10 §3 |
| Property-Class sourcing/grouping | PDM has no populated source; MK Workbench currently infers class names from property text. Whether that inference is "good enough" to keep as a permanent rule, or must be replaced by a real PDM-side source, is a product/business decision, not resolvable from evidence gathered here | Doc 03 Class row |

---

## D — Unsupported / insufficient information (do not generate)

| Mapping | What's missing | Evidence |
|---|---|---|
| Selection condition (type 2) relations | No source data anywhere carries "this property needs a Selection condition rather than nothing" — this is editorial intent about optional-property enforcement, not present in PDM attributes/options/dependencies | Doc 07 §3 item 2, §6 item 1 |
| Article-level / Property-class-level Constraint, Reaction, Post-Reaction | Same category — "None of that intent is captured anywhere in the current source data." Explicitly flagged as requiring invented behavioural intent if auto-generated | Doc 07 §6 item 1 |
| BOI / Packaging / Tax domain relations (beyond price variant-condition Actions) | "Their source-of-truth is UNKNOWN" — no packaging determination logic or tax-category rules exist anywhere in the PDM/Builder-Table source surfaced in this investigation | Doc 07 §6 item 3, doc 02 §3.1 |
| `CatalogueItemOptionExclusions` (Item/SKU-scoped mandatory exclusion) | No repository/service reads this table at all, AND no clean pCon target exists even if it were fetched (no per-final-article restriction mechanism in OCD/MDB) | Doc 06 §5, doc 04 Q7-Q8 |
| Interval-typed PropertyValues (`Op.from`/`Op.to`/`Raster`) | Neither the legacy PDM exporter nor the current MK Workbench exporter has ever emitted anything but exact-match single values; no PDM interval concept has been surfaced at all | Doc 01 §6, doc 03 Property Value row, doc 05 Q1 |
| Multivalued/Multioption Configuration-scope selection | Manual states this is unsupported at runtime today regardless of schema fields; auto-generating multi-value Configuration selections would target a runtime capability that does not exist | Doc 01 §5, doc 05 Q2-Q3 |
| Exact `ProductId`/attribute names/selected values for the Nevi/DWE4 trace (steps 1, 3, 4, 5, 6, 8-11) | A live PDM/MDB/pCon query was never executed in this investigation pass; every downstream step depends on it | Doc 08, full summary table |
| Whether Nevi/DWE4 specifically has populated dependency/exclusion rows | No dependency-edge content for this family was recorded anywhere; the mechanisms are real and populated *elsewhere* in PDM, but this family's own data is unexamined | Doc 08 step 6 |
| OCD 4.1/4.2/4.3 field-level deltas against the OCD 4.0 table set reproduced in doc 09 | Manual TOC-only coverage for 4.1-4.3; not reconciled against the local `ocd_4.3_en.md` spec in this pass | Doc 09 §2.15 note, §6 item 4 |
| `tCOMd_RelObjRel`/MDB memo-field size behavior for very large relation bodies | Whether the MDB's single-field `com_RelationBody` truly has no size constraint (vs. XOCD's forced 255-char block chunking) is inferred, not independently confirmed against a live Access column type | Doc 07 §1.2 |

---

## Cross-cutting note

Several A/B items above are safe *transformations* whose completeness still depends on
D-classified missing PDM inputs elsewhere (e.g. real multilingual text). The classification
in this file grades the mapping's logic, not the current completeness of every input feed —
file 12 (round-trip validation) and file 13 (unknowns register) track input completeness
separately.
