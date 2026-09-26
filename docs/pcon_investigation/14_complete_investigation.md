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

**FACT (doc 01 §2-4, doc 04 Q2-Q3):** `Final Article Number = Article code + VarCodeSep +
Variant Code`, where the Variant Code is assembled from the currently-selected/visible
Configuration-scoped property values, governed by the `CodeScheme`'s `Visibility`,
`ValueSep`, `InVisibleChar`/`UnselectChar`, `Trim`, and multi-option separator/bracket
fields. Since OCD 4.0, value combination tables can also drive user-defined article-code
schemes without an additional relation. **This is a generated identity, never a second
stored database row** (doc 04, "Bottom line" section) — the one system in this whole
picture that *does* materialize a row per final configuration is PDM's own `Item` table,
which is a genuine structural divergence MK Workbench must account for (doc 04 Q5).

## 3. Can one property have multiple options/values?

**FACT (doc 05 Q1, Q4):** yes, and it is the normal case — `PropertyValue` is a table of
rows keyed by `(PropertyClass, PropertyName, OpFrom, ValueFrom, OpTo, ValueTo, Raster)`, and
real PDM data (Nevi/DWE4, `AER1A11*`) routinely carries 10+ simultaneous properties per SKU.
However, per doc 05 Q2-Q3, **within a single Configuration-scoped property, only one value
can be selected at runtime today** — the manual explicitly states "Configurable multivalued
properties are currently not supported in OFML runtime applications," and neither the legacy
PDM exporter nor MK Workbench's current exporter has ever emitted a multi-value selection or
an interval-typed value in practice (both always emit exact-match, `OpFrom="EQ"` values).

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

**FACT, doc 01 §9-10, doc 07 §1.1:** a Relation Object is `(RelObjID, Position, RelName,
Type, Domain)`, bound to exactly one entity (Article, Property class, Property, Property
value, or BOI part) via that entity's own `RelObjID` foreign key. Six types exist
(Precondition, Selection condition, Action, Constraint, Reaction, Post-Reaction) across five
domains (Configuration, Pricing, BOI, Packaging, Taxation), each with a documented legality
matrix (e.g. Constraint is legal only on Article/domain-C; domains P/PCKG/TAX must be
Action-only). **The current MK Workbench generator only ever produces 2 of 6 types
(Precondition, Action) in 2 of 5 domains (C, P), and only ever binds at the PropertyValue
level** — Article-, Property-class-, and Property-level bindings are schema-ready
(`com_RelObjID` columns exist) but always written `None` (doc 02 §2 rows 6/10/13, doc 07
§2.3, §3). Selection condition, Constraint (beyond the value-combination-table pattern),
Reaction, Post-Reaction, and the BOI/Packaging/Tax domains are **never generated** by this
codebase (doc 07 §3, doc 02 §3.1) — this is the single largest confirmed export-coverage gap
in the whole investigation.

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

**FACT, doc 09 (full file), doc 01 §0.3/§15-16:** "MDF" does not appear anywhere in the
pCon.creator 2.22 manual, in any of the sections read in full (Commercial data development,
Import of commercial data, Import of catalog data, Management of registration data). The
real formats are **OCD** (CSV commercial-data import/export contract, field-level documented
in full for OCD 4.0 in doc 09 §2), **XOCD** (an OCD variant/extension, table-name-only
coverage in this investigation), **XCF** (catalog exchange format, doc 09 §3), the internal
**MDB** (Access package, established by pre-existing local analysis, not the manual itself),
and **EBASE** (release-distribution database format, doc 09 §4). OCD's structural model
matches MDB's field-for-field except for the relation-object join-table normalization noted
in Q6. It is **UNKNOWN** whether "MDF" was a misnomer for MDB or refers to some other
artifact never covered by the manual sections read (doc 13 U2) — this investigation treats
it as settled (not a real pCon/OFML term) for all internal purposes, per explicit
instruction, while flagging the terminology question itself as unresolved with whoever
commissioned it.

## 8. What can we derive automatically from our existing PDM data?

**FACT, doc 11 (Class A in full):** Property→PropertyValue rows; the PDM Option→pCon
Property(Usage=Configuration) collapse; value-level Preconditions for combination-classified
values; value→code Actions for numeric/parametric properties; price variant-condition Action
relations (a like-for-like port of PDM's own legacy `VarCondThread` logic); base-article/
ArtBase value classification; `DependentOptionValues`→value-combination-table+Constraint
generation (confirmed implemented end-to-end); and the `TextID`-indirection shape for text
blocks. These are described in doc 11 as fully mechanical given their inputs — "deterministic"
describes the transformation logic, not necessarily the completeness of the input data (see
Q9).

## 9. What information is genuinely missing?

**FACT, doc 11 (Class D), doc 13 (register):** interval-typed PropertyValues (no PDM
interval concept ever surfaced); real multi-value-per-Configuration-property runtime support
(explicitly unsupported by OFML runtime per the manual); `CatalogueItemOptionExclusions`
(no fetch/model/export exists, and no clean pCon target exists even if it did — no
per-final-article restriction mechanism); Selection condition/Constraint(article-level)/
Reaction/Post-Reaction relation generation (no source data anywhere captures the required
editorial intent); BOI/Packaging/Tax domain relations beyond price (source-of-truth
UNKNOWN); and, concretely, the back half of the real Nevi/DWE4 trace (Options, Dependencies,
Relation Objects, MDB, pCon Creator — doc 08, GAP for all five, no live query executed in
this pass). Also genuinely missing: a real PDM-side source for **Property Class**
grouping — pCon requires it as mandatory, and PDM has never populated a real source (doc 03
Class row); current MK Workbench synthesizes class names from property text as a stand-in,
not a sourced value.

## 10. What should the canonical MK Workbench model contain?

**INFERENCE, doc 10 (full file):** the existing `Snapshot`-centered architecture (`models/
snapshot.py` + `services/engineering/*` generators + the two exporters +
`mdb_reverse_engineering_service.py`) already **is** a format-neutral canonical model
sitting between PDM/pCon/MDB/OCD-XOCD — this investigation does not propose replacing it.
Reusable as-is: `EngineeringClassService`, `EngineeringArtbaseService`,
`EngineeringRelationService`'s existing value-level generation, `PricingRelationService`/
`varcond_service.py`, and `EngineeringValueTableService`'s `DependentOptionValues` pattern
(as a template to extend). Needs extension: consuming `attribute_option_dependencies` and
`attribute_value_exclusions`; writing property-/article-/class-level `RelObjID` bindings
(the reverse-engineering reader already expects them — only the writer is missing).
Genuinely missing, net-new: an explicit **Option-collapse layer** (today implicit inside
shared property/value builder code, distinguished only by an internal marking) that states
its own collapse rule and provenance-preservation contract; a **Constraint generator** for
negative exclusion rules; and fetch+generation paths for the two Catalogue*Exclusions
mechanisms. See doc 10 §5 for explicit non-goals (no `FinalArticle` entity, no first-class
`Option` write target, no assumption that MDB's join-table relation shape or `ArtBase`'s
string-keying generalizes).

## 11. What should be automated?

**INFERENCE, doc 11 (Classes A and, conditionally, B):** everything in Q8's list should
remain or become always-auto-generated (Class A). Additionally, several mappings should be
auto-generated **once named evidence is confirmed** (Class B): Product/Item→Article base
identity (once the canonical PDM source field is confirmed), `DependentAttributeValues`
consumption (once confirmed wired or newly wired), dependency-chain round-trip fidelity
(once tested against a real chained family), property-level Preconditions mirroring
ArtBase-style restrictions (a natural low-risk extension of already-computed co-occurrence
data), `CatalogueProductOptionExclusions`→`ArtBase` (once a fetch path exists), and
variant-code/config-code round-trip equivalence (once verified once, per doc 13 U9-U10).

## 12. Where must we require Review Required?

**INFERENCE, doc 11 (Class C):** `AttributeValueExclusions`'s implementation strategy
(explicit Constraint vs. implicit omission — a genuine design choice, not just a data
gap); the variant-condition/variant-code/variant-key string-identity ambiguities (the
manual's own wording is not crisp); the Post-Reaction and Taxation-domain-code
ambiguities in the `RelationObj` table (documentation gaps in the target format itself);
whether `RelObjRel`'s many-to-many generality is ever really used; manually curated/edited
relation objects (by design, must stay human-authored); the "preserve if already imported"
all-or-nothing guard's interaction with newly-added values (a live, currently-unverified
regression risk, doc 13 U24); and Property-Class sourcing (whether text-inferred class
names are an acceptable permanent rule, or a real PDM source must be found — a product
decision, not a data question).

## 13. What must change in MK Workbench eventually (describe only, do not implement)?

**INFERENCE, doc 10 §4, doc 11, doc 13:** (a) an explicit, named Option-collapse layer
with a documented provenance contract; (b) extension of `EngineeringValueTableService` (or
a sibling service following its pattern) to consume `attribute_option_dependencies` and
`attribute_value_exclusions`, the latter requiring new negative-polarity logic, not just new
inputs; (c) new repository fetch methods and a generator for
`CatalogueProductOptionExclusions`/`CatalogueItemOptionExclusions`, with the latter
requiring a genuinely new mechanism (no per-final-article restriction target exists in
OCD/MDB today); (d) writing (not just reading) property-/article-/class-level `RelObjID`
bindings in `EngineeringRelationService`/the exporters; (e) replacing the all-or-nothing
"preserve if already imported" guard with a real per-relation merge strategy once doc 13
U24's risk is confirmed; (f) resolving Property-Class sourcing (either formalize the
text-inference rule explicitly and reviewably, or find a real PDM source); (g) building the
missing automated test coverage for `import_snapshot`'s relation FK-chain parsing (doc 02 §4
item 8, doc 13 U23).

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
