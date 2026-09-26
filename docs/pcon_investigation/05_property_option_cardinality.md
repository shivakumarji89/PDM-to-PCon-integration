# 05 — Property / Option Cardinality

**Status:** Forensic, evidence-only. No code changed. Cross-references all three evidence
sources per task instructions: pCon manual (`01_pcon_creator_2_22_2_investigation.md`),
MDB structure (`02_mdb_structure_and_relationships.md`), and PDM docs
(`docs/Legacy_PDM_Business_Logic/07_Attributes.md`, `09_Options.md`, `10_Option_Values.md`,
`11_Configuration.md`, `docs/SKU_Config_Decode_Findings.md`).

---

## Q1. Can one Property have zero/one/multiple options?

Reframe per file 03's established non-mapping: pCon has no "Option" object distinct from
Property — a Property's "options" **are** its PropertyValues (`01_...md` §5-7). So this
question becomes: can one Property have zero/one/multiple values?

- **Zero values: FACT, yes, structurally possible** — nothing in the manual's Property
  fields (`01_...md` §5) requires at least one value to exist before a Property is created;
  however a Property with zero values would be practically unusable at runtime (no
  documented explicit prohibition found, but also no explicit "zero is fine" statement —
  **UNKNOWN** whether the OCD import validates a minimum of 1 value).
- **One value: FACT, yes** — e.g. `01_...md` §5 numeric-type caveat: *"OCD does not support
  optional numeric properties... always mandatory at runtime"* implies a numeric Property
  can be a single-value/range without alternatives.
- **Multiple values: FACT, yes, the common case** — `PropertyValue` (`ocd_propertyvalue.csv`)
  is a table of rows keyed by `(PropertyClass, PropertyName, OpFrom, ValueFrom, OpTo,
  ValueTo, Raster)` (`09_...md` §2.5), i.e. one Property routinely has many PropertyValue
  rows.

**PDM side (FACT):** `Attribute` 1—* `AttributeValue` and `[Option]` 1—* `OptionValue`
(`26_Data_Model.md` §3 ER diagram; `07_Attributes.md` §5.2; `09_Options.md` §5 "Table
`[Option]`"). Both PDM tables allow arbitrary cardinality of values per attribute/option —
no PDM-side minimum/maximum count constraint was found in any module doc.

**Confidence: FACT** on cardinality being 0..N on both sides; **UNKNOWN** on any enforced
minimum.

## Q2. Can a configuration select multiple values of the same property?

- **pCon manual (FACT, `01_...md` §5):** the `Multivalued` field exists on Property, but
  *"Configurable multivalued properties are currently not supported in OFML runtime
  applications"* (manual p.102, verbatim) — Multivalued is documented as usable **only**
  for scope `Relation`, not `Configuration`. Separately, `Multioption` on `ocd_property.csv`
  (`09_...md` §2.4) is a distinct field described as "Multiple values selectable" but is
  explicitly **"imported but not evaluated by OFML runtime in OCD 4.0 stage 1"** (manual
  p.377, `09_...md` §2.4). So: **for a Configuration-scoped property, a single value is
  the only supported runtime selection**, even though the schema has fields that gesture at
  multi-select.
- **MDB/current exporter (FACT, file 02 §2 row 14 area; `08_Property_Values.md` BR-PVAL-023):**
  the legacy PDM exporter (`OCDExport.cs`) and the current MK Workbench exporter both only
  ever emit exact-match single values (`opFrom="EQ"`, no interval, no multi-value row) — so
  in practice, neither generator side has ever exercised multi-value selection even where
  the schema nominally allows fields for it.
- **PDM side (FACT):** PDM's `BaseAttributeValues`/`ProductAttributeValues`/`ItemOptionValues`
  are all `(entity, valueId)` composite-key join tables with **no cardinality constraint**
  visible in any module doc — an Item can in principle carry many `AttributeValueId`s for
  the *same* `AttributeId` if such rows existed, but `SKU_Config_Decode_Findings.md` §9
  states the practical PDM filtering model is: *"Each product = a unique combination of its
  functional attribute values"* — i.e. real product data is one value per attribute per
  product in the concrete example set traced (`AER1A11*` family: `Type`, `Assembly`, `Size`,
  `Height`, `Tilt` each carry exactly one value per product). **No PDM example of a single
  attribute carrying two simultaneously-selected values on one Item was found.**

**Confidence: FACT** that pCon.creator's Configuration domain does not support multi-value
selection at runtime today (explicit manual caveat); **FACT** that PDM's real data (per the
one concrete family traced) is single-value-per-attribute-per-product; **UNKNOWN** whether
PDM's schema *could* represent multi-value-per-attribute in some other family not traced.

## Q3. Can a configuration select multiple options of the same property?

Same answer as Q2 under the established non-mapping (Option = Property with
`Usage=Configuration`): **no**, per the same `Multivalued`/`Multioption` runtime-unsupported
caveat (`01_...md` §5). PDM's `IsFabric` model (`09_Options.md` BR-OPT-002) treats fabric
**type** and fabric **colour** as two *separate* options (a parent/sub-option pair via
`HideByDefault`-as-linked-id / `DependentOptionValues`), not one option with two
simultaneously-selected values — consistent with "one value per option per selection" being
the real-world pattern on both sides.

**Confidence: FACT** (manual caveat) + **INFERENCE** (PDM fabric type/colour pattern is
structurally consistent with single-value selection, not counter-evidence).

## Q4. Can a configuration select values from multiple properties simultaneously?

**FACT, yes — this is the normal case on both sides.** pCon: an Article has multiple
Property Classes, each with multiple Properties (`01_...md` §8); a Configuration is exactly
the simultaneous set of current values across all of an article's configurable properties
(manual §5.3.11.7 "Configuration" domain, `01_...md` §9). PDM: `ProductAttributeValues`
per `SKU_Config_Decode_Findings.md` §9 — *"Each product = a unique combination of its
functional attribute values"* with the concrete `AER1A11*` example carrying `Type`,
`Assembly`, `Size`, `Height`, `Tilt`, `Arms`, `Armpads` simultaneously, and the Nevi `DWE4`
example (`SKU_Config_Decode_Findings.md` §4, §9) carrying **10 functional + 8 physical**
attributes simultaneously on one SKU (`DWE42AN4YS…`).

**Confidence: FACT**, directly evidenced with real data on the PDM side.

## Q5. Can an Option depend on another Option?

**FACT, yes, on the PDM side — this is a first-class, populated mechanism.**
`DependentOptionValues (OptionValueId, AdditionalOptionValueId)` — "AdditionalOptionValueId
becomes available (dependent) when OptionValueId is selected" (`26_Data_Model.md` §2.4;
`10_Option_Values.md` §5 "Relationship tables"; confirmed live in DPS source,
`docs/DPS_Original_Extraction_SQL.md` `DependencyManager.cs#7`:
`INSERT INTO DependentOptionValues (OptionValueId, AdditionalOptionValueId) VALUES (...)`).
Fabric type→colour is the concrete recurring example: `09_Options.md` BR-OPT-002/BR-OPT-004
— fabric-colour options (`IsFabric=2`) are sub-options of fabric-type options (`IsFabric=1`),
linked via a synthetic sub-option reference built from the fabric-type order code.

**pCon side (INFERENCE, not directly modeled as "Option depends on Option" since Option
doesn't exist as a concept):** the closest pCon equivalent is a **Precondition** relation on
a Property or PropertyValue (`01_...md` §9-10) — "Boolean expression describing the
condition under which a property or property value can be selected." MK Workbench's current
implementation (`services/engineering/engineering_value_table_service.py:171-264`,
`build_dependency_tables`) converts PDM's `DependentOptionValues` edges (surfaced in-memory
as `snapshot.option_option_dependencies`) into **OCD value-combination tables** (`TABLE()`
constraints, relation type `"4"` domain `"C"`), one table per parent option with dependents
— **not** into per-value Precondition relations. This is a real, working, verified
translation already implemented in the codebase (see file 06 for full detail).

**Confidence: FACT** (PDM mechanism exists and is populated with real fabric data);
**FACT** (MK Workbench's current translation target is Constraint/value-combination-table,
not Precondition) — cited directly from source at
`services/engineering/engineering_value_table_service.py:171-217`.

## Q6. Can a Property/Attribute value depend on an Option value (or vice versa)?

**FACT, yes — a second, distinct PDM mechanism exists for this cross-kind case.**
`DependentAttributeValues (AttributeValueId, AdditionalOptionValueId)` — *"selecting a
value implies an additional option value"* (`07_Attributes.md` §5.2 link table;
`26_Data_Model.md` §2.4). Confirmed live in DPS source
(`docs/DPS_Original_Extraction_SQL.md` `DependencyManager.cs#7`:
`INSERT INTO DependentAttributeValues (AttributeValueId, AdditionalOptionValueId) VALUES (...)`),
and in `repositories/pdm_repository.py:699-710` (`fetch_attribute_option_dependencies`,
docstring: *"attribute value -> the option value it additionally enables (DPS
dependency)"*). This is a **directional, cross-kind** dependency (Attribute value →
Option value), distinct from the Option→Option case in Q5.

**MK Workbench (FACT):** `snapshot.attribute_option_dependencies` field exists
(`models/snapshot.py:117-118`, comment: *"DPS dependency edges: a selected value
additionally ENABLES option values"*), separate from `option_option_dependencies`.
**UNKNOWN/GAP** whether `EngineeringValueTableService.build_dependency_tables` (which only
reads `snapshot.option_option_dependencies`, per the code read in this pass) also consumes
`attribute_option_dependencies` — the method signature and body inspected
(`engineering_value_table_service.py:171-217`) only references
`snapshot.option_option_dependencies`; no reference to `attribute_option_dependencies` was
observed in the portion read. This would need a targeted grep/read of the full file to
confirm definitively — flagged here as **UNKNOWN**, not asserted either way.

**pCon side:** no distinct "Attribute" vs "Option" kind exists (per file 03), so this
PDM-side kind-distinction has **no pCon-side counterpart at all** — both PDM mechanisms
(Q5 and Q6) target the same pCon Property/PropertyValue space once exported.

**Confidence: FACT** for the PDM mechanism's existence and population; **UNKNOWN** for
whether MK Workbench's current generator fully consumes both dependency kinds.

## Q7. Can a dependency chain exist (A depends on B depends on C)?

**FACT, yes, explicitly designed for on the PDM/legacy-export side.**
`docs/Legacy_PDM_Business_Logic/09_Options.md` BR-OPT-021: *"`CheckDependents` propagates
dependency PO links between adjacent option classes: an option whose `DependPOs` all point
to a single PO is chained to the option whose `PO == num2`, swapping dependency
references"* (`SIFExportThread.cs:CheckDependents`) — i.e. the legacy SIF exporter has
explicit multi-hop dependency-chain-following logic. BR-OPT-023/024 (`ProcessGlobal`,
`CreateDependent`) further show **recursive** dependent-option-class creation
(`CheckGlobalDepend`/`FindMatch`/`CheckPassMatch`, "Dependent options are matched
recursively").

**MK Workbench (FACT, partial):** `EngineeringValueTableService.build_dependency_tables`
docstring states: *"one table per parent option that has dependents (chains yield one
table per parent level)"* (`engineering_value_table_service.py:171-181`) — i.e. the current
implementation is aware of and explicitly handles chains by producing one value-combination
table per level of the chain, not by flattening or rejecting multi-hop dependencies.

**pCon side (FACT):** the OCD relation language supports arbitrary relation chaining
implicitly — Reactions "are always evaluated first," Post-Reactions "evaluated last," with
ordinary Preconditions/Actions/Constraints evaluated in between per `Position` (manual
p.109, `01_...md` §10) — so a chain of preconditions (A gates B gates C) is expressible,
though MK Workbench's current generator does not produce multi-level Precondition chains
(only flat value-level Preconditions per combination-classified value, file 07 §2.2 item 2).

**Confidence: FACT** — chains are explicitly handled by name in both the legacy PDM export
code and the current MK Workbench value-table builder; the two are not proven to produce
identical output for the same chain, but both explicitly anticipate multi-hop dependencies
rather than assuming a flat one-level model.

---

## Concrete example (real data)

From `docs/SKU_Config_Decode_Findings.md` §4, §9 — the Nevi `DWE4` family, category 1239
("Nevi Dach"), example SKU `DWE42AN4YSNBADNN`: **10 functional (head) attributes selected
simultaneously** (Type, Assembly, Size, Height, Tilt-equivalent positional codes, etc.) **+
8 physical (tail) attributes** (Width, Depth, Material, ...), all on one `Item` row —
directly evidencing Q4 (multiple properties selected simultaneously) with real production
data, not a schematic example. See file 08 for the full end-to-end trace of this example.
