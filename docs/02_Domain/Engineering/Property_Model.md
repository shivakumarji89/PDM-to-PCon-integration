# 05 — Property / Option Cardinality

**Status:** Forensic, evidence-only. No code changed. Cross-references all three evidence
sources per task instructions: pCon manual (`docs/04_Reference/pCon/Investigation/PCon_Creator_Investigation.md`),
MDB structure (`docs/02_Domain/Repository/Repository_Model.md`), and PDM docs
(`docs/02_Domain/PDM/Legacy_PDM_Business_Logic/07_Attributes.md`, `09_Options.md`, `10_Option_Values.md`,
`11_Configuration.md`, `docs/02_Domain/PDM/SKU_Configuration_Decode.md`).

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
  the *same* `AttributeId` if such rows existed, but `SKU_Configuration_Decode.md` §9
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
per `SKU_Configuration_Decode.md` §9 — *"Each product = a unique combination of its
functional attribute values"* with the concrete `AER1A11*` example carrying `Type`,
`Assembly`, `Size`, `Height`, `Tilt`, `Arms`, `Armpads` simultaneously, and the Nevi `DWE4`
example (`SKU_Configuration_Decode.md` §4, §9) carrying **10 functional + 8 physical**
attributes simultaneously on one SKU (`DWE42AN4YS…`).

**Confidence: FACT**, directly evidenced with real data on the PDM side.

## Q5. Can an Option depend on another Option?

Matters for cardinality because it means an Option Value's *availability* — not just its
existence — can be conditional on another Option Value being selected elsewhere, which
constrains which value combinations a Configuration can legally end up with.

See [Dependency_Model.md §1](./Dependency_Model.md) for the full mechanism
(`DependentOptionValues`), code mapping (`engineering_value_table_service.py:171-264`,
`AttributeSelector.cs#7`, `DependencyManager.cs#7`), and conclusion (maps to an OCD
value-combination table / Constraint type `"4"` domain `"C"`, not a Precondition).

## Q6. Can a Property/Attribute value depend on an Option value (or vice versa)?

Matters for cardinality because it is a second, cross-kind dependency channel (Attribute
value → Option value) that can further constrain legal value combinations independently of
the Option→Option case in Q5.

See [Dependency_Model.md §2](./Dependency_Model.md) for the full mechanism
(`DependentAttributeValues`), code mapping, and the open **UNKNOWN** flag on whether
`attribute_option_dependencies` is ever consumed by `build_dependency_tables`.

## Q7. Can a dependency chain exist (A depends on B depends on C)?

**FACT, yes, explicitly designed for on the PDM/legacy-export side.**
`docs/02_Domain/PDM/Legacy_PDM_Business_Logic/09_Options.md` BR-OPT-021: *"`CheckDependents` propagates
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

See Q4 above for the Nevi `DWE4` SKU `DWE42AN4YSNBADNN` example (10 functional + 8 physical
attributes selected simultaneously on one `Item` row); see file 08 for the full end-to-end
trace.
