# 14 — Complete Investigation: Executive Summary

**Status:** Forensic synthesis, evidence-only. No code changed. Answers the 14 questions
posed for this investigation, pulling directly from files 01-13 with FACT/INFERENCE/UNKNOWN
discipline (file 01 §0). Each answer cites which prior doc(s) it comes from. This file does
not introduce new evidence — see files 01-13 for full citations into source manuals, specs,
and code.

---

## 1. What does pCon Creator actually consider an Article, Base Article and Variant?

**FACT (doc 01 §1-3, doc 04 Q1-Q4):** pCon.creator has exactly **one** database/dialog
object, `Article`, with a single `Article code` field described as "contains the base
article number." There is no separate "Final Article" or "Variant" table/dialog. A
**Variant** is a *variant code* — a runtime-computed string assembled from currently
selected property values via a named `CodeScheme`'s grammar (separators, visibility mode,
placeholder characters), concatenated onto the base article number to form the **final
article number**. "Base Article" is not a first-class named UI concept either — it is
**INFERENCE**, derived from the manual's field-level usage, that this label is useful for
MK Workbench's own terminology even though the manual itself never gives it a separate
dialog.

## 2. How does configuration become a final article?

**FACT (doc 01 §2-4, doc 04 Q2-Q3):** the final article number is assembled at runtime from
the article code plus a `CodeScheme`-generated variant code — **a generated identity, never
a second stored database row** (doc 04, "Bottom line" section). The one system in this whole
picture that *does* materialize a row per final configuration is PDM's own `Item` table,
which is a genuine structural divergence MK Workbench must account for (doc 04 Q5). See
[PCon_Creator_Investigation.md §4](./PCon_Creator_Investigation.md#4-article-number--configuration-code)
for the full formula and `CodeScheme` field list.

## 3. Can one property have multiple options/values?

**FACT (doc 05 Q1, Q4):** yes at the data-model level — `PropertyValue` is a table of rows,
and real PDM data routinely carries 10+ simultaneous properties per SKU. However, per doc 05
Q2-Q3, **within a single Configuration-scoped property, only one value can be selected at
runtime today**, and neither the legacy PDM exporter nor MK Workbench's current exporter has
ever emitted a multi-value selection or an interval-typed value in practice. See
[PCon_Creator_Investigation.md §5](./PCon_Creator_Investigation.md#5-properties) for the
verbatim manual quote and the numeric-property-mandatory finding.

## 4. How do property and option dependencies actually work?

**FACT, doc 06 (full file), doc 05 Q5-Q7:** PDM has **three semantically distinct**
mechanisms that must not be conflated: (1) **positive availability**
(`DependentOptionValues`, `DependentAttributeValues`) — selecting a parent value makes
another value *available* for selection; (2) **negative mutual exclusion**
(`AttributeValueExclusions`) — a pair of values that must never both hold; (3)
**generation-time scope filtering** (`CatalogueOptionValues`,
`CatalogueProductOptionExclusions`, `CatalogueItemOptionExclusions`) — decides what even
gets exported/offered at all, evaluated before any relation logic runs. Only mechanism (1),
specifically `DependentOptionValues`, is **confirmed implemented end-to-end** — converted
into OCD value-combination tables + Constraint relation objects by
`services/engineering/engineering_value_table_service.py`. The cross-kind variant
(`DependentAttributeValues`) is modeled in-memory but its export consumption is **UNKNOWN**
(doc 05 Q6, doc 13 U15); `AttributeValueExclusions` is modeled but has **no confirmed
consumer** (doc 06 §3, doc 13 U16); the two Catalogue*Exclusions tables are **not fetched or
modeled at all** in the current codebase (doc 06 §5, doc 13 U17). Dependency **chains**
(A→B→C) are explicitly handled by name in both the legacy PDM exporter and the current
`build_dependency_tables` (one table per chain level), though the two are not proven to
produce identical output (doc 05 Q7).

## 5. How are Relation Objects supposed to represent configuration logic?

**FACT, doc 01 §9-10, doc 07 §1.1:** a Relation Object spec defines six types across five
domains, each bound to one of several entity levels. The current MK Workbench generator only
ever produces 2 of the 6 types, in 2 of the 5 domains, and only ever binds at the
PropertyValue level — the single largest confirmed export-coverage gap in the whole
investigation. This is restated as the investigation's headline finding in
[README.md](./README.md#single-most-important-finding-from-the-original-00-14-arc); the full
evidence trail (table/type/domain breakdown, code citations) is in
[`../../../02_Domain/Engineering/Relation_Model.md`](../../../02_Domain/Engineering/Relation_Model.md).

## 6. How does MDB represent these concepts?

**FACT, doc 02 (full file), doc 07 §1.2:** the live write path is
`services/ocd_export_service.py` (direct MDB) and `services/xocd_export_service.py`
(CSV/XOCD), reading a shared `Snapshot`. MDB normalizes relations into a **3-table join**
(`tCOMd_RelObj` / `tCOMd_Relation` / `tCOMd_RelObjRel`) not present in the OCD spec itself,
which links by name instead. Structural chain: `Package →{Article, Class, RelObj, Relation,
Text}`; `Class → Property → PropValue`; `Article ↔ Class` via `ArticleClass` (join);
`Article → ArtBase` (restriction rows, **string-keyed by class/property/value name**, unlike
every other ID-keyed table); `PropValue → RelObj` is the **only** relation binding the
generator ever populates. Options/OptionValues are **never written** as separate tables —
folded into `Property`/`PropValue` with an internal `com_PropTypeCode` marking. Value
combination tables (`Table`/`TableColumn`/`TableLine`) are name-joined, not surrogate-key
joined (doc 02 §2 row 30, flagged UNKNOWN/INFERENCE, needs live confirmation — doc 13 U21).

## 7. How does OCD/XOCD represent these concepts (note: brief said "MDF", settled as not a real format)?

**FACT, doc 09 (full file), doc 01 §0.3/§15-16:** "MDF" is not a real pCon.creator/OCD term —
the real formats are **OCD**, **XOCD**, **XCF**, the internal **MDB**, and **EBASE**. See
[PCon_Creator_Investigation.md §0.3](./PCon_Creator_Investigation.md#03-what-was-not-found-anywhere)
for the full manual-search evidence and the still-open terminology question (doc 13 U2).

## 8. What can we derive automatically from our existing PDM data?

**FACT, doc 11 (Class A in full):** a fixed set of mappings (property/value rows, the
Option→Property collapse, value-level Preconditions/Actions, pricing relations, ArtBase
classification, `DependentOptionValues`→value-combination-table generation, text-block
shape) are already fully mechanical given their inputs. See
[Canonical_Model_Proposal.md §4](./Canonical_Model_Proposal.md#4-reuse--extend--missing--per-component)
("Reuse as-is" rows) for the component-by-component breakdown and citations.

## 9. What information is genuinely missing?

**FACT, doc 11 (Class D), doc 13 (register):** several inputs and generation paths simply
do not exist yet in either PDM or MK Workbench — interval-typed values, multi-value
Configuration-property runtime support, the two Catalogue*Exclusions mechanisms, several
Relation Object types/domains, a real PDM source for Property Class, and the back half of
the Nevi/DWE4 trace. See
[Canonical_Model_Proposal.md §4](./Canonical_Model_Proposal.md#4-reuse--extend--missing--per-component)
("Missing" rows) for the full list with citations.

## 10. What should the canonical MK Workbench model contain?

**INFERENCE, doc 10 (full file):** the existing `Snapshot`-centered architecture already
**is** a format-neutral canonical model sitting between PDM/pCon/MDB/OCD-XOCD — this
investigation does not propose replacing it, only extending specific parts of it and adding
a small number of genuinely missing components. See
[Canonical_Model_Proposal.md §2-5](./Canonical_Model_Proposal.md#2-flow-1--pdm--canonical-engineering-model--pconocd-exporter-mdb-exporter)
for the full reuse/extend/missing breakdown, the flow diagrams, and the explicit non-goals
(§5: no `FinalArticle` entity, no first-class `Option` write target, no assumption that
MDB's join-table relation shape or `ArtBase`'s string-keying generalizes).

## 11. What should be automated?

**INFERENCE, doc 11 (Classes A and, conditionally, B):** everything in Q8's list should
remain or become always-auto-generated (Class A). A further set of mappings should be
auto-generated once specific named evidence is confirmed (Class B) — e.g. Product/Item→
Article base identity, `DependentAttributeValues` consumption, dependency-chain round-trip
fidelity, and `CatalogueProductOptionExclusions`→`ArtBase`. See
[Canonical_Model_Proposal.md §4](./Canonical_Model_Proposal.md#4-reuse--extend--missing--per-component)
for the components each of these corresponds to.

## 12. Where must we require Review Required?

**INFERENCE, doc 11 (Class C):** a handful of items are genuine design choices or
documentation-gap ambiguities rather than data gaps — notably `AttributeValueExclusions`'s
implementation strategy, several relation-object domain/type wording ambiguities, the
"preserve if already imported" guard's interaction with newly-added values, and Property-Class
sourcing. See
[Canonical_Model_Proposal.md §4](./Canonical_Model_Proposal.md#4-reuse--extend--missing--per-component)
and §5 for the components these attach to.

## 13. What must change in MK Workbench eventually (describe only, do not implement)?

**INFERENCE, doc 10 §4, doc 11, doc 13:** a short list of concrete extensions and new
components — an explicit Option-collapse layer, extending the value-combination-table
service to cover the two currently-unconsumed dependency/exclusion mechanisms, new
fetch+generator paths for the two Catalogue*Exclusions tables, writing (not just reading)
property-/article-/class-level relation bindings, replacing the all-or-nothing "preserve if
already imported" guard, resolving Property-Class sourcing, and adding missing test
coverage. See
[Canonical_Model_Proposal.md §4](./Canonical_Model_Proposal.md#4-reuse--extend--missing--per-component)
for the specific services/components and justification for each.

## 14. What should the implementation sequence be (describe only, do not implement)?

**INFERENCE, synthesizing docs 10-13:**
1. **Close the confirmation unknowns first, cheaply.** Grep-confirm whether
   `attribute_option_dependencies` and `attribute_value_exclusions` are consumed anywhere
   today (doc 13 U15-U16) — this determines whether steps 2-3 are "wire up" or "build new."
2. **Run the Stage-1 self-consistency round-trip** (file 12 §2) for at least one real family
   (Nevi/DWE4 recommended, since real identifiers already exist per doc 08) to establish a
   baseline and resolve the foundational base/final-article-number round-trip unknowns
   (doc 13 U9-U10).
3. **Build the explicit Option-collapse layer** (doc 10 §4) — this formalizes existing
   behavior rather than changing it, so it is lower-risk to do early and gives every
   subsequent extension a clearer place to attach provenance logic.
4. **Extend `EngineeringValueTableService`-family logic** to consume the two currently-
   unconfirmed/unimplemented dependency and exclusion mechanisms (`DependentAttributeValues`,
   `AttributeValueExclusions`), resolving the Class-C design ambiguity (Constraint vs.
   omission) as an explicit decision before writing code.
5. **Add the property-/article-/class-level `RelObjID` write paths**, since the reader
   already supports them — this closes the one-way capability gap named in doc 07 §7 with
   comparatively low new-surface-area risk.
6. **Fetch and model `CatalogueProductOptionExclusions`** (maps cleanly to `ArtBase`,
   reusing existing base-article-scoped machinery); treat `CatalogueItemOptionExclusions`
   as a separate, harder follow-on since it has no clean existing target.
7. **Only after 1-6:** attempt Stage-2 (hand-authored-MDB-in) and Stage-3 (real
   pCon.creator human pass) round-trip validation (file 12 §2) to test the "preserve if
   already imported" guard's real-world behavior (doc 13 U24) and the currently-unreachable
   relation types/domains — these require the most external setup (a hand-authored MDB or a
   live pCon.creator session) and depend on 1-6 being in place to produce a meaningful diff.
8. **Selection condition / Constraint(article-level) / Reaction / Post-Reaction / BOI /
   Packaging / Tax generation remain out of scope for automation** throughout this sequence
   (doc 11 Class D) unless and until a live PDM data source or explicit business
   requirement is identified that supplies the missing editorial intent — this is a
   standing decision to revisit, not a task to schedule.
