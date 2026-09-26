# 07 — Relation Object / Configuration Model (Evidence-Based)

**Status:** Forensic investigation. No code changed. FACT / INFERENCE / UNKNOWN
labelling as in file 02; see that file for the shared table-inventory and stale-
docs caveat (§0 there) — it is not repeated in full here.

---

## 1. What `tCOMd_RelObj` / `tCOMd_Relation` / `tCOMd_RelObjRel` are (spec + MDB schema)

### 1.1 OCD spec model (the wire format)

**FACT**, from `docs/pcon_reference/ocd_4.3_en.md:1807-2002` (§2.15–2.16):

- **`RelationObj`** table: one row per relation binding —
  `RelObjID` (num, >0), `Position` (evaluation order), `RelName` (the name that
  links to `Relation.RelationName`), `Type` (1=Precondition, 2=Selection
  condition, 3=Action, 4=Constraint, 5=Reaction, 6=Post-Reaction), `Domain`
  (C=Configuration, P=Price, BOI=Bill of items, PCKG=Packaging, TAX=Taxation).
- **`Relation`** table: `RelationName`, `BlockNr`, `CodeBlock` — the actual
  logic body, chunked into numbered blocks and concatenated at evaluation time
  (`ocd_4.3_en.md:2004-2008`). Linked to `RelationObj` **by name**, not by a
  numeric join table.
- **Binding is NOT stored in `RelationObj` itself** — the *entity being bound*
  (article / property class / property / property value / BOI part) is
  identified by that entity's own row carrying a `RelObjID` foreign key back
  to `RelationObj.RelObjID` (spec text: "the number ... serves as a key to
  access the relational object in the table RelationObj",
  `ocd_4.3_en.md:1727`, and the per-entity `RelObjID` field callouts at
  `ocd_4.3_en.md:625,682,1094,1143,1195,1210,1240,1273,1672,1708`, one for each
  of the entities the spec allows preconditions/actions on).
- **Legality matrix** (`ocd_4.3_en.md:1955-1963,1988-1996`): which
  (relation type × domain × data entity) combinations are legal. Notably:
  Precondition is legal on Property class, Property, Property value, and BOI
  part (not Article); Action is legal on nearly everything including Article
  and Property class; Selection condition is legal only on Property (domain
  C); Reaction/Post-Reaction are legal only on Article/Property (domain C);
  Constraint is legal only on Article (domain C); relations in domains
  P/PCKG/TAX can **only** be of type Action (`ocd_4.3_en.md:1945`).

### 1.2 MDB schema (the manufacturer's Access normalization)

**FACT**, from `services/ocd_export_service.py` and
`services/mdb_reverse_engineering_service.py`:

- `tCOMd_RelObj` — one row per named relation object: `com_RelObjID` (PK),
  `com_RelObjName`, `com_PackageID` (`ocd_export_service.py:671-673`). Note:
  **no `Type`/`Domain`/`Position` columns here** — those moved to the join
  table.
- `tCOMd_Relation` — one row per relation body: `com_RelationID` (PK),
  `com_RelationName`, `com_RelationBody`, `com_PackageID`
  (`ocd_export_service.py:674-677`). Unlike the spec's `Relation` table, the
  MDB schema stores the **whole body in one field** (`com_RelationBody`), not
  chunked into `BlockNr`/`CodeBlock` rows — that chunking is XOCD-CSV-specific
  (`_CODE_BLOCK_MAX = 255`, `xocd_export_service.py:61,515-519`), needed only
  because CSV cells have a practical size limit; the MDB's memo/text column
  presumably has no such constraint (**INFERENCE** — not independently
  confirmed against the live Access column type).
- `tCOMd_RelObjRel` — the **join table** the spec does not have: one row per
  (RelObj, Relation) pair, carrying `com_RelObjID`, `com_RelationID`,
  `com_RelObjTypeCode` (the spec's Type), `com_RelObjDomainCode` (the spec's
  Domain), and `com_RelationOrder` (the spec's Position)
  (`ocd_export_service.py:678-682`). So the MDB schema **relocates** Type/
  Domain/Position from `RelationObj` onto this join row.
- Binding to an entity is still via the entity's own `com_RelObjID` column,
  exactly as the spec describes — confirmed present (schema-wise) on
  `tCOMd_Article`, `tCOMd_ArticleClass`, `tCOMd_Property`, `tCOMd_PropValue`
  (`ocd_export_service.py:786,895,917,945`).

**INFERENCE.** The MDB's `RelObj`↔`Relation` split into a many-to-many
`RelObjRel` join, versus the spec's simple by-name link, suggests the MDB
schema supports (or intends to support) **one relation object carrying
multiple relation bodies of different type/domain**, or one relation body
being reused by multiple relation objects. The current code never exercises
that generality: `ocd_export_service.py._relations` (§2.2 below) always
creates a 1:1:1 triple (one `RelObj`, one `Relation`, one `RelObjRel` row per
`RelationObject` domain model instance, indexed by the same loop counter `i`,
`ocd_export_service.py:670-685`). Whether real hand-authored MDB packages use
the join table's full many-to-many generality is **UNKNOWN** (not observed;
would require inspecting a live, hand-authored `pcr_data_com_ocd.mdb`).

---

## 2. What the current relation service (`engineering_relation_service.py`) actually represents

### 2.1 Domain model in memory

**FACT**, `models/relation_object.py:31-51` — `RelationObject` carries:
`name`, `type_code`, `domain`, `order`, `body`, `class_name` (unused by any
writer found — see gap list), `property_id`/`value_id` (the *authoring-time*
binding target, i.e. which property/value this relation is *for*), and
`rel_obj_id`/`relation_id`/`relation_name` (populated only when the object was
**imported** from a real MDB, so a round-trip can preserve the original keys —
`mdb_reverse_engineering_service.py:379-390`).

### 2.2 What `EngineeringRelationService` derives

**FACT**, `services/engineering/engineering_relation_service.py:45-129`
(`build_relation_objects`):

1. **`A_Code_<Prop>` (Action, domain C, type `"3"`)** — for every property
   in canonical order, one action mapping each value to its order code, but
   **only for values whose code differs from the value token itself**
   (numeric/parametric properties). Choice-style properties whose values are
   already their own code get no action (`engineering_relation_service.py:
   90-112`).
2. **`B_<Prop>_<Value>` (Precondition, domain C, type `"1"`)** — emitted
   **only** for a value classified as `"combination"` — i.e. gated by a
   head/code property, not merely confined to a base article
   (`_add_value_preconditions`, `engineering_relation_service.py:131-154`).
   Generic values (present on every article) and pure base-scoped values
   (handled instead via `tCOMd_ArtBase`, see
   `services/engineering/engineering_artbase_service.py:50-51,59`) get **no**
   relation at all.
3. **Classification** (`_classify_and_bodies`,
   `engineering_relation_service.py:208-248`): every value is bucketed
   `generic` / `base` / `combination`. Only `combination` gets a relation;
   the split against `ArtBase` is deliberate and cross-referenced
   (`engineering_artbase_service.py:8-10,50-51`: "A value scoped to a subset
   of bases is expressed here [ArtBase], not as a `$BAN` precondition"). This
   is a genuine, working division of labour between the two OCD mechanisms
   for restricting values (ArtBase table vs. relation-based precondition).
4. **Body grammar**: `$BAN IN ('<base>')` for base-gated branches, OR'd
   together, with `(SPECIFIED <Prop>) AND (<Prop> IN (...))` conditions added
   when a base's carriers are a proper subset of that base's articles
   (`_combination_body`, `engineering_relation_service.py:258-299`). This is
   a **fixed, deterministic, one-size-fits-all authoring standard** applied
   identically to every product (module docstring,
   `engineering_relation_service.py:1-22`: "to ONE canonical standard,
   applied identically to every product (no per-product editorial variance)").
5. **Manual curation is additive**: `add_relation`/`remove_relation`/
   `set_name`/`set_type`/`set_domain`/`set_body` let a user hand-add or edit
   relation objects on top of the derived set
   (`engineering_relation_service.py:392-454`), but nothing re-validates a
   hand-edited relation against the OCD legality matrix (§1.1) — see gap list.
6. **Price-domain relations come from a different service entirely**:
   `services/pricing_relation_service.py:103-125` (`PricingRelationService.
   commit`) builds an Action/domain-P `RelationObject` (`PA_PRICING` /
   `PA_<prefix>` family) and appends it directly onto
   `snapshot.relation_objects` — bypassing `EngineeringRelationService`
   entirely but landing in the same list that both exporters read
   generically. **FACT.**

### 2.3 What both exporters do with `relation_objects`

**FACT.** `ocd_export_service.py._relations` (`ocd_export_service.py:658-685`)
and `xocd_export_service.py._relations` (`xocd_export_service.py:494-523`)
both iterate `snapshot.relation_objects` **generically** — they do not care
whether a given `RelationObject` came from `EngineeringRelationService` or
`PricingRelationService`; they just emit whatever `type_code`/`domain`/`body`/
`value_id` is present. This means the export layer is agnostic to origin, but
also means **nothing at export time re-checks OCD legality** (e.g. that a
domain-`P` relation is Action-only, or that a Precondition is bound to a
legal entity) — that check exists only implicitly, by construction, in
whichever generator produced the `RelationObject` in the first place.

**FACT — the only entity binding actually wired at export time is
`PropValue → RelObj`.** Both exporters read `rel.value_id` and use it purely
to set `PropValue.com_RelObjID` (`ocd_export_service.py:683-684,895`;
`xocd_export_service.py:521-522,488`). `rel.property_id` is recorded on the
in-memory `RelationObject` (used for `classify_values`/`related_value_ids`
book-keeping, `engineering_relation_service.py:373-382`) but is **never**
written to `tCOMd_Property.com_RelObjID` by either exporter — that column is
always `None` (see file 02 §2 row #13, §3.1). So even though the domain model
carries a `property_id`, the export layer only materializes the *value-level*
binding, not a property-level one.

---

## 3. What the current relation service does NOT represent

1. **Property-level and Article-level and Property-class-level bindings.**
   The spec allows Precondition/Action/etc. on Article, Property class,
   Property, and BOI part, not just Property value (§1.1). The current
   generator only ever produces value-level Preconditions and (implicitly,
   via property iteration) property-scoped Actions whose *binding column*
   still only lands on `PropValue` at export — see §2.3. **Article-level**
   Constraint/Reaction/Post-Reaction, **Property-class-level** Precondition,
   and **BOI-part** Precondition are entirely absent from the generator.
   (**FACT** — grep of `engineering_relation_service.py` shows no
   `type_code="4"|"5"|"6"` and no article/class-level relation construction.)
2. **Selection conditions (type 2).** Never generated. These are the
   mechanism OCD uses to force the user to evaluate an optional/free-text
   property during order-list generation (`ocd_4.3_en.md:1893-1899`). Not
   present anywhere in this codebase (**FACT** by grep for `type_code="2"` —
   no matches in `services/`).
3. **Non-Configuration domains besides Price.** BOI, Packaging (PCKG), and
   Taxation (TAX) domain relations are never generated (**FACT**, no
   `domain="BOI"|"PCKG"|"TAX"` assignment anywhere in `services/`).
4. **`RelationObject.class_name` is dead data.** The field exists on the
   model (`models/relation_object.py:40`) but no producer in
   `engineering_relation_service.py` or `pricing_relation_service.py` ever
   sets it to a non-default value, and neither exporter reads it. **INFERENCE**
   — likely a placeholder for a future property-class-level precondition that
   was never completed.
5. **Position/evaluation-order nuance beyond a flat default.** Every relation
   the generator emits uses `order=100` (`engineering_relation_service.py:
   105-112,146-154`; `pricing_relation_service.py:118`). The spec's `Position`
   field is meant to let same-type/same-domain relations on one object be
   evaluated in a defined ascending sequence when there is more than one
   (`ocd_4.3_en.md:1930-1933`). Since the generator never produces more than
   one relation per `(type, domain, entity)` combination for a given object,
   this limitation is currently inert, but it means the generator could not
   correctly express a hand-authored *multi-step* rule sequence without
   further work.
6. **Re-validation of manually edited relations.** `set_type`/`set_domain`
   (`engineering_relation_service.py:440-454`) accept any string; there is no
   check against the OCD legality matrix (§1.1) when a user hand-edits a
   relation's type/domain via the UI-facing curation API. **FACT** (no
   validation call in either setter; `validate_relation_body` at
   `engineering_relation_service.py:34-42` only checks balanced parens/quotes,
   not legality of type/domain/entity combination).

---

## 4. What pCon/OCD expects (recap, cross-referenced to the above)

From `ocd_4.3_en.md` §2.15–2.16 (already cited): a relation object is a
`(RelObjID, Position, RelName, Type, Domain)` tuple bound to exactly one kind
of entity via that entity's own `RelObjID` column, whose logic lives in a
same-named `Relation` row (or rows, if chunked). Domain P/PCKG/TAX relations
must be Action-only and, per `ocd_4.3_en.md:1946-1950`, may only assign
**internal (auxiliary) properties** — they must not affect the current
configuration or influence subsequent configuration-relation evaluation. This
constrains what `PricingRelationService`-style domain-P generation is allowed
to touch: **INFERENCE** — worth flagging as a rule the `PA_PRICING`/`PA_<prefix>`
Action bodies (`pricing_relation_service.py`) need to keep honouring (assigning
only auxiliary/pricing-scoped properties, never a real configuration property)
even though nothing in this codebase currently enforces that rule
programmatically; it appears to be honoured only by the hand-written
generation logic's intent, not by any guard.

---

## 5. Which rules could be auto-generated from source data (safe candidates)

1. **Value-level Preconditions for combination-classified values** — already
   done, and the logic (`_classify_and_bodies`/`_combination_body`) is fully
   mechanical/deterministic from article-set co-occurrence data
   (`engineering_relation_service.py:208-299`). Low risk to extend.
2. **Value→code Actions** for numeric/parametric properties — already done,
   purely a lookup/mapping from source value codes
   (`engineering_relation_service.py:90-112`).
3. **Price variant-condition Actions (`PA_PRICING`/`PA_<prefix>`)** — already
   done, ported directly from PDM's own `VarCondThread`/`SuperProductVarCondRelation`
   logic (`services/varcond_service.py`, `services/pricing_relation_service.py`),
   which is itself a faithful, mechanical transcription of existing PDM
   business rules over BOM/attribute data. This is as close to "already
   proven safe" as anything in this codebase, since it is a like-for-like
   port rather than a new invention.
4. **Property-level Precondition mirroring an existing ArtBase-style
   restriction** *could* plausibly be mechanically derived the same way
   value-level combination preconditions are (same source data: article-set
   co-occurrence), but this is **not currently implemented** — it would be a
   natural, low-risk extension of the existing `_classify_and_bodies`
   machinery rather than a new invention, since the head-property/base
   co-occurrence data it needs is already computed. (**INFERENCE** — this is
   a design suggestion based on pattern-matching the existing mechanism, not
   an evaluation of a concrete implementation.)

## 6. Which rules cannot be safely automated

1. **Selection conditions, Constraints, Reactions, Post-Reactions** — these
   encode editorial/business judgment about *when* and *how* a configuration
   step should behave (e.g. "warn if this optional property is left
   unevaluated," "assign a value once at article-initialization time and
   never again"). None of that intent is captured anywhere in the current
   source data (PDM attributes/options/dependencies model contains no
   analogue of "this needs a Reaction, not an Action"). Auto-generating these
   would require inventing behavioural intent the source data does not carry.
   **UNKNOWN whether PDM's legacy relation bodies (in the live PDM DB
   referenced in this repo's memory as a separate investigation track)
   encode this distinction some other way** — not examined here, out of
   scope for this MDB/OCD-structure-focused pass.
2. **Property-class-level and BOI-part-level Preconditions** — these require
   knowing which *classes* (not just properties/values) should be hidden as a
   unit, and which BOI components are conditionally included — neither is
   modelled in the current `EngineeringClass`/`article_components` structures
   in a way that maps cleanly to "generate this automatically" without a new,
   separate design decision about class-level visibility rules.
3. **Domain P/PCKG/TAX relations beyond price variant conditions** — Taxation
   and Packaging relations require domain knowledge (tax category rules,
   packaging determination logic) not present in the Builder-Table/PDM source
   data surfaced anywhere in this repo. Confirmed absent by grep (§3.3); their
   source-of-truth is **UNKNOWN**.
4. **Manually curated/edited relations** — by definition these represent a
   human override of the canonical standard (module docstring,
   `engineering_relation_service.py:1-22`, explicitly designs for
   "no per-product editorial variance" as the *default*, with manual curation
   as an escape hatch) and must stay human-authored.

---

## 7. Is current relation classification sufficient for export/import round-trip?

**Partially.**

- **Export → real MDB, structural fidelity: yes, for what it covers.** The
  `RelObj`/`Relation`/`RelObjRel` triple the exporter writes is internally
  consistent (same loop-counter `i` used as the surrogate key across all
  three tables, `ocd_export_service.py:670-682`) and the value-level
  `PropValue.com_RelObjID` binding round-trips correctly: the reverse-engineering
  reader reconstructs the exact same chain
  (`mdb_reverse_engineering_service.py:299-390`) and explicitly resolves
  property/value bindings from `tCOMd_Property.com_RelObjID`/
  `tCOMd_PropValue.com_RelObjID` — i.e. **the reader is more general than the
  writer**: it is written to expect and correctly parse a property-level
  binding (`prop_relobj`, `mdb_reverse_engineering_service.py:346-351`) that
  the current writer will never actually produce (§2.3). This asymmetry is
  not a bug today (nothing breaks), but it means a hand-authored or
  third-party MDB with property-level relation bindings would import fine
  into a `Snapshot`, while a Snapshot exported by this codebase would never
  itself produce that shape — a **one-way capability gap**, not a round-trip
  bug.
- **Export → XOCD path: yes, matches spec shape.** Because XOCD's relation
  shape mirrors the OCD spec (name-linked, no join table — file 02 §3.2),
  what little the generator does produce (value Precondition, code Action,
  price Action) is spec-legal by construction (domain C/P, type
  Precondition/Action only — both legal per the matrix in §1.1).
- **Insufficient for anything beyond the current authoring standard.**
  Because only Precondition/Action in domain C, plus Action in domain P, are
  ever produced, this classification is **not** sufficient to round-trip a
  real manufacturer MDB package that uses Selection conditions, Constraints,
  Reactions, Post-Reactions, or BOI/Packaging/Tax domain relations — those
  would either (a) be silently dropped if reached through a path this
  investigation didn't examine, or (b) more likely, per the reverse-engineering
  reader's code (§2.3 above, `mdb_reverse_engineering_service.py:360-390`),
  **be imported into `Snapshot.relation_objects` faithfully** (the reader
  does not filter by type/domain — it round-trips whatever `com_RelObjTypeCode`/
  `com_RelObjDomainCode`/`com_RelationBody` it finds) but then **cannot be
  regenerated identically on re-export**, because
  `EngineeringRelationService.build_relation_objects` would overwrite them
  with the canonical derived set unless `ensure_relation_objects`'s
  "preserve if already imported/edited" guard is honoured
  (`ocd_export_service.py:663-665`: "Preserve relation objects already
  imported or edited in the active snapshot. Derive canonical relations only
  when the snapshot has none."). **FACT**: that guard is a simple non-empty
  check (`if not snapshot.relation_objects`,
  `engineering_relation_service.py:53-57`) — so an imported MDB's exotic
  relation types **would** survive an immediate re-export (since the list is
  non-empty, the canonical derivation is skipped entirely), but only as an
  all-or-nothing pass-through; there is no per-relation merge between
  "preserve what was imported" and "regenerate what changed," which is a risk
  if engineering data changes after import (stale exotic relations would
  never be refreshed, and new canonical relations for newly-added
  values/properties would never be added either, since the whole derivation
  is skipped once *any* relation object exists).

**Bottom line for a downstream mapping task:** current relation classification
is sufficient and safe for the narrow authoring standard this codebase
targets (Precondition/value + Action/code + Action/price), but a translation
layer that must interoperate with hand-authored or legacy MDB packages using
the fuller OCD relation vocabulary needs to treat "snapshot already has
relation_objects" as an all-or-nothing fork, not a safe default, and should
budget for building real support for property/article/class-level bindings
and the missing relation types before claiming full round-trip fidelity.
