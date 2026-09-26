# 06 — Dependency & Exclusion Model (PDM mechanisms → pCon/OCD targets)

**Status:** Forensic, evidence-only. No code changed. Investigates
`DependentAttributeValues`, `DependentOptionValues`, `AttributeValueExclusions`,
`CatalogueOptionValues`, `CatalogueProductOptionExclusions`, `CatalogueItemOptionExclusions`
(plus related tables surfaced along the way), using the legacy PDM docs, live DPS source
excerpts (`docs/DPS_Original_Extraction_SQL.md`), the current MK Workbench repository/service
code, and file 07's Relation Object findings. **Per task instruction: no 1:1 mapping to a
single pCon Relation Object is assumed** — each mechanism is evaluated on its own semantics
and mapped to whatever mix of pCon/OCD constructs actually fits.

---

## 0. Summary table (read this first)

| PDM mechanism | What it actually represents | pCon/OCD target(s) it maps to | MK Workbench status |
|---|---|---|---|
| `DependentOptionValues` | **UI availability rule**: selecting a parent option value *makes an additional option value available/enabled* for selection (not a hard requirement, not an exclusion) | OCD **value-combination table** (`TABLE()` Constraint, relation type 4/domain C) — file 07 confirms Constraint is legal on Article (domain C) and this is exactly what `EngineeringValueTableService` generates | **Implemented** — `build_dependency_tables` converts this into per-parent-option combination tables |
| `DependentAttributeValues` | **UI availability rule, cross-kind**: selecting an attribute value enables an *option* value (attribute→option, not option→option) | Same target family as above (value-combination table / Constraint), but MK Workbench's current `build_dependency_tables` only reads `option_option_dependencies`, not `attribute_option_dependencies` — **UNKNOWN/GAP** whether this edge kind is consumed at all today | **Modeled in-memory** (`snapshot.attribute_option_dependencies`) but **not confirmed wired into export** |
| `AttributeValueExclusions` | **Valid-configuration rule (mutual exclusion)**: a symmetric pair of attribute values that cannot co-exist on the same product/configuration | OCD **Constraint** `Restrictions:` clause (the only OCD mechanism that expresses "these values must not both hold" as a validity rule — file 07 §1.1) — this is **type 4 (Constraint)**, never Precondition, since it is a joint-validity rule over two properties, not a single value's existence condition | **Modeled in-memory** (`snapshot.attribute_value_exclusions`) — **no exporter code observed converting this into a Constraint or value-combination table** (see §4 below); likely **GAP** |
| `CatalogueOptionValues` | **Catalogue-scoped availability**: which option values are visible/orderable *at all* in a given catalogue (a static membership filter, evaluated before configuration even starts) | Not a runtime OCD relation at all — this is **generation-time filtering** (which PropertyValue rows get exported/emitted in the first place), analogous to pCon's own `Export filter` field on Property/PropertyValue (`01_...md` §5-6) | **Implemented** implicitly — MK Workbench's snapshot/export pipeline only ever includes values sourced from a specific catalogue scope; not a relation-generation concern |
| `CatalogueProductOptionExclusions` | **Article-generation rule / mandatory requirement, product-scoped**: a specific product is *disallowed* from offering a specific option value, even though the option value is otherwise catalogue-visible | OCD **ArtBase** restriction (a per-article fixed/restricted property-value list — `01_...md` §12) is the closest fit, since this is an article(product)-level exclusion, not a configuration-time relation; alternatively a Precondition scoped by `$BAN` if expressed as relation code | **Not confirmed implemented** — no service was found reading `CatalogueProductOptionExclusions` in the current MK Workbench codebase (only in the legacy DPS/PDM source, `docs/DPS_Original_Extraction_SQL.md`) |
| `CatalogueItemOptionExclusions` | **Article-generation rule / mandatory requirement, item(SKU)-scoped** — same as above but scoped to a specific `Item`, not the whole `Product` | Same target family as `CatalogueProductOptionExclusions`, but at finer (Item, i.e. closer to pCon's *final article*) granularity — since pCon has no per-final-article-number restriction mechanism (file 04), this would have to collapse to the same base-article `ArtBase` restriction, **losing per-Item granularity** unless a Precondition/Constraint keyed on the decoded variant code is used instead | **Not confirmed implemented** — same as above |

**Headline finding (FACT):** the six PDM mechanisms fall into **three semantically distinct
categories** that must not be conflated:
1. **Cross-value dependency/availability** (`DependentOptionValues`,
   `DependentAttributeValues`) — a *positive* enabling rule, evaluated during configuration.
2. **Cross-value exclusion** (`AttributeValueExclusions`) — a *negative* joint-validity rule,
   evaluated during configuration.
3. **Scope/generation-time filtering** (`CatalogueOptionValues`,
   `CatalogueProductOptionExclusions`, `CatalogueItemOptionExclusions`) — decide *what even
   gets exported/offered* for a catalogue/product/item, evaluated **before** any relation
   logic runs, not a runtime configuration-relation concern at all.

None of these six is a 1:1 match for a single pCon Relation Object; (1) and (2) map onto
OCD's Constraint/value-combination-table mechanism (relation type 4, domain C — file 07
§1.1), while (3) maps onto generation-time export scoping (which rows exist at all), not a
relation.

---

## 1. `DependentOptionValues` — availability, not exclusion

**PDM semantics (FACT):** `DependentOptionValues (OptionValueId, AdditionalOptionValueId)` —
"AdditionalOptionValueId becomes available (dependent) when OptionValueId is selected"
(`docs/Legacy_PDM_Business_Logic/26_Data_Model.md` §2.4; `10_Option_Values.md` §5). This is
confirmed as a **positive enabling** rule by live DPS source: `DependencyManager.cs#7`
(`docs/DPS_Original_Extraction_SQL.md`): `INSERT INTO DependentOptionValues (OptionValueId,
AdditionalOptionValueId) VALUES (...)`, maintained via a dedicated `DependencyManager` UI
form. It is also read at **runtime selection time** by `OptionSelector.cs`
(`docs/DPS_Original_Extraction_SQL.md` `HermanMiller.EOS.UI\OptionSelector.cs`) and by
`repositories/pdm_repository.py:225-281` (`_OPTIONS_CTE`, "DPS parity
(OptionSelector.LoadOptionValues, B1)") — i.e. this is a **UI-availability** mechanism: it
controls which option values *appear as selectable* once a parent value is chosen, not
which combinations are ultimately valid at generation time (though the two overlap in
practice).

**Fabric type→colour is the canonical example (FACT):** `09_Options.md` BR-OPT-002/BR-OPT-003
— fabric-colour options (`IsFabric=2`) become available only once their parent fabric-type
value (`IsFabric=1`) is selected.

**MK Workbench mapping (FACT, implemented, verified from source):**
`services/engineering/engineering_value_table_service.py:171-264` (`build_dependency_tables`)
reads `snapshot.option_option_dependencies` (populated from `DependentOptionValues` via
`repositories/pdm_repository.py:712-723` `fetch_option_option_dependencies` /
`:725-744` `fetch_products_option_dependencies`) and builds **one OCD value-combination
table per parent option that has dependents**, with "a logical row per parent value and a
value SET per dependent (child) option" (module docstring, lines 1-11). Each table is then
bound to the article via a synthetic `C_<TABLE>` **Constraint relation object** (type `"4"`,
domain `"C"`) created by `_sync_constraint_relations`
(`engineering_value_table_service.py:59-74`). This is **not** a Precondition — it is a
Constraint, per the OCD legality matrix in file 07 §1.1 (*"Constraint is legal only on
Article (domain C)"*), which matches the code's own domain/type choice.

**Is this a 1:1 Relation Object mapping?** **No** — one `DependentOptionValues` edge does
not become one Relation Object. Multiple edges sharing a parent option collapse into **one**
value-combination table + **one** Constraint relation object; edges are also scoped by base
article (`COL_BAN` column) when the family has been reduced (`_offered_values_by_base`,
lines 266-282). This is exactly the "not 1:1" caveat the task requires: many PDM dependency
rows → one generated table+constraint pair.

## 2. `DependentAttributeValues` — cross-kind availability

**PDM semantics (FACT):** `DependentAttributeValues (AttributeValueId,
AdditionalOptionValueId)` — *"selecting a value implies an additional option value"*
(`07_Attributes.md` §5.2). Confirmed live: `DependencyManager.cs#7` inserts into this table
alongside `DependentOptionValues` in the same dependency-authoring UI
(`docs/DPS_Original_Extraction_SQL.md` lines 2136, 2211 — add/remove pair), and
`AttributeSelector.cs#7` reads it at runtime: *"SELECT OptionValue.OptionId ... FROM
OptionValue INNER JOIN DependentAttributeValues ON OptionValue.OptionValueId =
DependentAttributeValues.AdditionalOptionValueId INNER JOIN AttributeValue ON
DependentAttributeValues.AttributeValueId = AttributeValue.AttributeValueId WHERE
AttributeValue.AttributeId = ..."* — i.e. this is queried to find which *options* become
available given a selected *attribute* value, the cross-kind analogue of §1.

**MK Workbench mapping (FACT/UNKNOWN):** the field exists in the domain model
(`models/snapshot.py:116-118`, `attribute_option_dependencies`, comment: *"DPS dependency
edges: a selected value additionally ENABLES option values"*) and is fetched
(`repositories/pdm_repository.py:699-710` `fetch_attribute_option_dependencies`). **However,**
`EngineeringValueTableService.build_dependency_tables`
(`engineering_value_table_service.py:171-217`, the portion read in this investigation) only
references `snapshot.option_option_dependencies` — no reference to
`attribute_option_dependencies` was observed in that method. **This is flagged as UNKNOWN,
not asserted as a confirmed gap** — a full grep of every consumer of
`attribute_option_dependencies` across the codebase was not performed in this pass; it is
possible another service consumes it. **Recommendation for a follow-up:** grep
`attribute_option_dependencies` across `services/` to confirm whether this edge kind ever
reaches an OCD Constraint/table, or whether cross-kind (Attribute→Option) dependencies are
currently silently dropped from export.

## 3. `AttributeValueExclusions` — mutual exclusion (a negative rule, not an availability rule)

**PDM semantics (FACT):** *"a pair (AttributeValueId, ExcludedAttributeValueId) that cannot
co-exist"* (`repositories/pdm_repository.py:681-696`, `fetch_attribute_value_exclusions`
docstring: *"DPS parity: a pair ... that cannot co-exist. Scoped so BOTH values belong to
this product."*). Confirmed live in DPS source
(`docs/DPS_Original_Extraction_SQL.md` `DependencyManager.cs#5/#6/#21`:
`SELECT ExcludedAttributeValueId FROM AttributeValueExclusions WHERE ...`; `INSERT INTO
AttributeValueExclusions (AttributeValueId, ExcludedAttributeValueId) VALUES (...)`; `DELETE
FROM AttributeValueExclusions WHERE ...`), and read at runtime by
`AttributeSelector.cs#5/#9` and `PermutateThread.cs#3` (*"SELECT AttributeValueId,
ExcludedAttributeValueId FROM AttributeValueExclusions ORDER BY ExcludedAttributeValueId,
AttributeValueId"* — used during the legacy SIF **permutation/export** pass, i.e. this
mechanism is consulted both at UI-selection time *and* at export-generation time).

**This is semantically different from §1/§2:** it is a **negative** joint-validity rule
("these two values must never both be true"), not a positive enabling rule. Per file 07
§1.1, the OCD mechanism for joint-validity rules over multiple properties is the
**Constraint**'s `Restrictions:` clause (*"the actual property dependencies that must hold...
for the configuration to be considered valid"* — manual p.120-124), or equivalently a
value-combination table that simply never lists the excluded combination as a valid row
(the "TABLE() constraint" pattern already used for §1).

**MK Workbench mapping (FACT: modeled; UNKNOWN/likely GAP: not exported):** the field
exists (`models/snapshot.py:112-114`, `attribute_value_exclusions`, comment: *"DPS
AttributeValueExclusions: attribute value id -> excluded value ids (symmetric); a
combination pairing an excluded value is invalid"*) and is fetched
(`repositories/pdm_repository.py:681-696`). **No code was found in this investigation pass
consuming `snapshot.attribute_value_exclusions`** to generate either a Constraint relation
object or to *omit* excluded rows from `EngineeringValueTableService`'s value-combination
tables. This is flagged as a **likely GAP**, not confirmed absolute (a targeted grep of
`attribute_value_exclusions` across all `services/` files was not exhaustively performed),
but no consuming reference surfaced during the reads done for files 02/07/this file.

**Is this a 1:1 Relation Object mapping?** **No, by design even if implemented** — a set of
pairwise exclusions over N values does not correspond to one Relation Object; it would
naturally collapse into either (a) one Constraint whose `Restrictions:` clause lists all
mutually-exclusive pairs, or (b) implicit exclusion via a value-combination table that
simply never enumerates the invalid combination as a row (the same mechanism as §1, used
in the opposite sense — omission instead of enablement).

## 4. `CatalogueOptionValues` — generation-time scope, not a runtime relation

**PDM semantics (FACT):** catalogue-scoped option-value membership — *"Catalogue membership
/ visibility of a value"* (`26_Data_Model.md` §2.4). Read constantly throughout the codebase
to filter which option values are even candidates for a given catalogue
(`repositories/pdm_repository.py` `_OPTIONS_CTE`, gated by `CatalogueOptionValues` per its
own comment: *"gated by the catalogue via CatalogueOptionValues"*).

**This is not a dependency or exclusion rule at all** — it is a **static membership filter**
answering "does this option value exist in this catalogue's universe," evaluated once,
before any per-product/per-configuration logic runs. Its pCon/OCD analogue is not a
Relation Object of any type — it is closer to the **generation-time decision of which
PropertyValue rows to emit into the OCD export at all** (i.e. which values MK Workbench's
snapshot/export pipeline includes in `tCOMd_PropValue` in the first place), or, loosely, to
the `Export filter` field the manual documents on Property/PropertyValue (`01_...md` §5-6)
which likewise governs whether a value is exported for a given target, not a runtime
configuration rule.

**MK Workbench mapping (INFERENCE):** the snapshot-building pipeline is already
catalogue/family-scoped at the point PDM data is fetched (per `docs/PDM_MDB_Engineering/02_PDM_Data_Model.md`,
`PDMService.get_products_for_category(..., catalogue_id=None, ...)`) — i.e. catalogue
scoping happens by **which rows are fetched from PDM in the first place**, not by a
generated relation. This is architecturally consistent with the PDM mechanism's own
semantics (a filter, not a rule), so no gap is asserted here — just a category clarification
per the task's requirement not to force a Relation Object mapping where none is
appropriate.

## 5. `CatalogueProductOptionExclusions` / `CatalogueItemOptionExclusions` — article-generation-time mandatory exclusion, at two granularities

**PDM semantics (FACT):** both tables record "this option value must not be offered for
this specific Product / Item, in this catalogue" — confirmed live in DPS source:
- Product-scoped: `DependencyManager.cs#3/#4/#30/#31`, `DataList.cs#65/#66/#95`,
  `Maintenance.cs#22`, `VerifyOptions.cs#4` (`docs/DPS_Original_Extraction_SQL.md`) — e.g.
  `INSERT INTO CatalogueProductOptionExclusions (CatalogueId, ProductId, OptionValueId)
  VALUES (...)`, and read at runtime by `repositories/pdm_repository.py`
  `_OPTIONS_EXCLUSION_FILTER` (*"AND ov.OptionValueId NOT IN (SELECT OptionValueId FROM
  CatalogueProductOptionExclusions WHERE CatalogueId = ? AND ProductId = ?)"*).
- Item-scoped: `AttributeSelector.cs#8`, `OptionSelector.cs#4`, `Maintenance.cs#21`,
  `VerifyOptions.cs#5` (`docs/DPS_Original_Extraction_SQL.md`) — e.g. `SELECT
  OptionValueId FROM CatalogueItemOptionExclusions WHERE ItemId = ... AND CatalogueId = ...`.

Both are read at **the same point** in the DPS UI (`OptionSelector`) as the availability
mechanisms in §1-2, but their semantics are **exclusionary and article/item-scoped**, not
value-to-value dependency-scoped: they answer "is this option value even legal for *this
specific product/item*, in *this catalogue*" — closer to a per-article restriction than a
cross-value rule.

**pCon/OCD target (INFERENCE):** since this is a per-article (Product-scoped) or
per-final-article (Item-scoped) restriction on which values are legal, the natural OCD
analogue is **`ArtBase`** — *"Article properties... lets an article restrict the
property-value list of a property-class property to a subset valid for that specific
article"* (`01_...md` §12, manual p.90). Critically:
- `CatalogueProductOptionExclusions` (Product-scoped) maps cleanly onto `ArtBase`, since
  both are keyed at the **base-article** granularity (file 04 established that pCon's
  `Article`/`ArtBase` is a base-article concept, and PDM's `Product` is the closest analogue
  of base article, per file 03).
- `CatalogueItemOptionExclusions` (Item-scoped, i.e. a specific *final* SKU) has **no clean
  pCon target** — pCon's `ArtBase` is base-article-scoped, and pCon has no per-final-article
  restriction table (file 04 Q7-Q8: no `tCOMd_FinalArticle`). Expressing an Item-level
  exclusion in pCon would require either (a) collapsing it up to the base article (losing
  granularity — all variants of that base would then share the restriction, which is
  **wrong** if the exclusion was really meant for one specific Item/SKU only), or (b)
  encoding it as a Precondition/Constraint keyed on the decoded variant code/`$BAN`-plus-value
  combination (the same "combination"-classified value mechanism `EngineeringRelationService`
  already uses for base-scoped value gating, file 07 §2.2 item 2-3).

**MK Workbench mapping (UNKNOWN/GAP):** **no service or repository method reading
`CatalogueProductOptionExclusions` or `CatalogueItemOptionExclusions` was found anywhere in
the current MK Workbench codebase** during this investigation pass (both tables surfaced
only in `docs/DPS_Original_Extraction_SQL.md`, i.e. the legacy DPS/PDM source, not in
`repositories/pdm_repository.py` or `services/`). This is a genuine, currently-unaddressed
gap: **article-generation-time mandatory exclusions from the live PDM system are not
currently fetched, modeled, or exported by MK Workbench at all**, as distinct from the
dependency/availability mechanisms (§1-2) and the value-mutual-exclusion mechanism (§3),
which are at least partially modeled in `models/snapshot.py` even where export is unproven.

---

## 6. Explicit non-1:1 statement (per task requirement)

None of the six mechanisms investigated maps onto a single pCon Relation Object:
- `DependentOptionValues` → **one value-combination table + one Constraint relation object
  per parent option** (many PDM rows → one generated pair; implemented).
- `DependentAttributeValues` → same target family, cross-kind, **consumption by the
  generator is unconfirmed (UNKNOWN)**.
- `AttributeValueExclusions` → **Constraint `Restrictions:` clause or omitted
  value-combination rows** (opposite polarity from the above); **not currently exported
  (likely GAP)**.
- `CatalogueOptionValues` → **not a relation at all** — a generation-time row-inclusion
  filter, already handled by scoping the PDM fetch itself.
- `CatalogueProductOptionExclusions` → **`ArtBase` restriction** (base-article-scoped);
  **not currently fetched/modeled/exported (GAP)**.
- `CatalogueItemOptionExclusions` → **no clean pCon target exists** (no per-final-article
  restriction mechanism in OCD/MDB); would require a Precondition/Constraint keyed on
  decoded variant code if implemented; **not currently fetched/modeled/exported (GAP)**.
