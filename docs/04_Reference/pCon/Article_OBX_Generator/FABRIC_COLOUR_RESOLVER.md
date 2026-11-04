# Fabric colour resolver (OCD engine)

One resolver (`services/ocd_engine/fabric.py` discovery + `services/ocd_engine/fabric_resolver.py`) decides which fabric
colour a configuration uses. It replaces the earlier name-based rule (`*Fabric*Type` / `*Fabric*Colo(u)r`), which only
worked where the property names happened to match.

## Data evidence (real repository, `C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx\<range>\ANY\1\db`)

OCD has no group, relation-operand or "Name" tables: the tables that matter are `ocd_property`, `ocd_propertyvalue`
(`value_from` = the code, `is_default`, `pos_pval`, `rel_obj`), `ocd_relationobj`, `ocd_relation` and `ocd_propvaluetext`
(`textnr, language, line_nr, line_fmt, text`). The "Name" of a value is `value_from`; its description is the language
text, which in all three series reads `<description> - <code>` (`Curacao - 7O005`, `Medley 1HA - 1HA`). Languages present:
de, en, nl, fr (every value has all four in these series).

| | Lino (`lino`) | Tun (`tun`) | Bay Work Pod (`bay_work_pod`) |
|---|---|---|---|
| Manufacturer / series | HM / LINO | HM / TUN | HM / BAY_WORK_POD |
| Base articles | MI1E3, MI2E3, MI7E3 | NOTUN420, NOTUN620, NOTUN920 | PEP100, PEP200 |
| Type property | `LINO_OPT:Seat_Fabric_Type` (34 values) | `TUN_OPT:Upholstered_Base_Fabric` (52) - **no "Type" in the name** | `BAY_POD_OPT:Exterior_Fabric_Type` (1) |
| Colour property | `Fabric_Colour` (1,308) | `Upholstered_Base_Fabric_Colour` (3,239) | `Exterior_Fabric_Colour` (8) |
| Mechanism | colour-value precondition | colour-value precondition | colour-value precondition |
| Relation text on a colour | `Seat_Fabric_Type = '7O'` (1,258 values); `$ BAN IN ('1')` on 50 (withdrawn) | `(SPECIFIED T) AND (T IN ('Z3'))` (2,836), `T = '611'` (367), `$ BAN IN (...)` (36) | `(SPECIFIED T) AND (T IN ('1HS'))` (8) |
| Relation attached to | property **value** (type 1, domain C) | property value; the colour **property** also has `(SPECIFIED Base_Material) AND (Base_Material NOT IN ('ST'))` | property value |
| Group / relation-operand tables | none (not part of OCD) | none | none |
| Explicit default flag | none | none on colours; the **type** `1HA` is flagged | colour `1HS10` (7th of 8) |
| Code relation to type | colour code = type code + suffix (`7O` -> `7O005`) | same (`Z3` -> `Z302`) | same (`1HS` -> `1HS01`) |
| Price relations (domain P) read | the **type** only: `... + ' 8=' + Seat_Fabric_Type` | the **type** only: `Base_Material + ' 8=' + Upholstered_Base_Fabric` | no fabric property (320 domain-P relations checked) |

Other repository series show the remaining patterns: `comma` (one type, 35 colours) and `always`
(`Chair_Fabric_Type` + 3,241 colours) carry **no colour relations at all**; their colours are tied to types only by code
prefix and by the value texts - the value-text fallback. (`always` additionally cannot be generated today because a
constraint reads a value combination table, `CHAIR_FABRIC`, that is not loaded; that failure is independent of this work.)

## Root cause of all-colour enumeration, per series

* **Lino** - none in the engine as committed: the names matched (`Seat_Fabric_Type`, `Fabric_Colour`), so one colour per
  valid type was already chosen (21 SKUs vs 751 with the rule off, other properties pinned). Unchanged by this work.
* **Tun** - the type property is called `Upholstered_Base_Fabric`. The name rule needs `fabric.*type`, found no type, and
  `fabric_colours()` returned `[]` *because it requires a type property*: the colour was an ordinary property, so every
  relation-valid colour of the selected type was expanded (2,128 SKUs, up to 112 colours per type, with the other
  properties pinned). This is the all-colour case.
* **Bay Work Pod** - none: names matched and a flagged colour exists; one SKU. (The name rule would also have chosen
  correctly only because a colour is flagged.)
* Not part of the three but fixed by the same change: series without colour relations (`always`, `atlas` felt, `comma`).
  The name rule treated *every* colour as valid for every type and picked the first colour **overall** for each type,
  a wrong colour rather than all colours.

## Discovery (no name-only classification)

A (type, colour) pair is a fabric when the data shows one of

1. `relation` - at least half of the colour values name type literals in their own preconditions (`T = 'x'`,
   `T IN ('x', ...)`), at least 90% of those literals are leading characters of the colour code (and shorter), and some
   type owns two or more colours; or
2. `prefix_text` - no such relations, but at least half of the colour codes extend exactly one type code, some type owns
   two or more, and at least 90% of the values of both properties have a language text ending `- <their own code>`.

and a keyword candidate is one of the two properties.

**Keyword discovery.** A property is a *fabric candidate* when `fabric` or `upholstery` (regex `fabric|upholstery|upholster`,
so `Upholstered_Base_Fabric` matches) occurs in its name **or in any language of its Property-text**
(`ocd_propertytext`, loaded into `PropertyDef.labels`). No full phrase ("Fabric Type") is needed. A keyword hit is discovery
only: it never decides a role and never reduces values by itself (`Fabric_Care` with values X|Y stays fully enumerated). The
structure above decides type/colour/group roles, so `Upholstered_Base_Fabric` is found and `everywhere`
`Edge_Type -> Material_Type` (same relation shape, no keyword) is **reported (`FABRIC_PAIR_UNCONFIRMED`, info) and left alone**.
Thresholds are constants in `fabric.py` (`MIN_MAPPED`, `MIN_EXTENDING`, `MIN_TEXT_CONFIRMED`) and were chosen against the
repository, not derived from a spec.

## The one manual option: Fabric property

Article OBX Generator page, *Load Articles* dialog, next to **Done**: `Fabric property: [Automatic | <Name - Property-text label> ...]`
(keyword candidates first). It is the only manual control - no type, colour, group, relation or direction selectors.

* `Automatic` (default) = the discovery above. Choosing it again restores the automatic result exactly.
* A chosen property is an **input to the same discovery/resolver** (`discover(model, selected)`): the structural pairs the
  property belongs to are confirmed without needing a keyword, and the roles (type, colour, group-like chain) are read from
  the relations, code prefixes and value texts - the choice may be either side of the pair. It is *added* to the automatic
  result, so selecting an already-detected property changes nothing, and it never switches automatic detection off.
* It does not bypass validation: colours are still evaluated by the engine's relation evaluator (see below).
* If no valid structure involves the property, or it fits several types equally well, generation stops with a
  `GenerationError` naming the property (`FABRIC_OVERRIDE_UNRESOLVED`, engine `FabricOverrideError`) **before anything is
  enumerated** - it is never turned into "offer every colour". An article that simply lacks the chosen property (multi-article
  runs) uses automatic discovery and gets a warning.

## Resolution per configuration

1. selected type value from the configuration state (the type is ordered before the colour; the candidate cache is keyed
   on it, also when no relation reads it);
2. candidates in `pos_pval` order, de-duplicated by code (first occurrence wins); in the fallback only colours that extend
   the type code unambiguously (a colour extending two type codes, `7O576` under `7O` and `7O5`, is *ambiguous* and offered
   to neither);
3. every type-1 / domain-C relation of the candidate is evaluated by the engine's own evaluator (`ConfigurationEngine._tri_checked`);
   property and class preconditions are applied earlier by the engine (Tun's `Base_Material NOT IN ('ST')` hides the colour);
4. rejected: precondition FALSE; relation unparsable/unevaluable (never read as valid); a selection condition (type 2) on a
   value, which OCD allows on a property only; in the fallback, not mapped / ambiguous;
5. selected: first valid `is_default` colour, else first valid colour; none valid while the type is selected -> the
   configuration is rejected (`NO_FABRIC_COLOUR` with the candidate/rejection summary).

The colour node therefore offers one value, so colours are never expanded and then filtered. Diagnostics:
`engine.fabric_resolutions` (type, mechanism, candidates, valid, rejected with reasons, selected, explicit-default vs
first-valid), `GenerationOutcome.fabric_notes`, and sink codes `FABRIC_COLOUR_RESOLVED` (info), `FABRIC_COLOUR_UNCERTAIN`
and `NO_FABRIC_COLOUR` (warning). `generate(..., fabric_default_only=False)` keeps every valid colour.

## Several independent fabric sets in one article

Discovery yields at most one `(type, colour)` scheme per colour property, and the engine resolves each colour property
on its own: at that colour node it reads *its* type from the configuration, evaluates only *its* colours' relations and
keeps one colour (flagged default, else first valid in source order) before any other colour is expanded. Sets are
therefore multiplied, not merged: Seat type x Back type x ... with one colour each (Hush NOHUE2: 2,471,839 SKUs
unreduced, 2,304 = 48 x 48 reduced). Direct, value-level and group-chain relations, the value-text fallback, the
manual Fabric property (it only *adds* its own pair; the other sets stay as they are) and `fabric_default_only=False`
all work per set (`tests/ocd_engine/test_ocd_fabric_multi_set.py`).

**No guessing between types.** If a colour property fits two or more type properties equally well (same evidence rank,
e.g. Always: `Chair_Fabric_Colour` and `Seat_Pad_Fabric_Colour` share one 3,241-value code space with two identical type
lists and no colour relations; Pinch: `Fabric_Colour` fits three types), no pair is built. The colour property keeps all
its valid colours and the engine reports `FABRIC_PAIR_AMBIGUOUS` (warning); `Discovery.ambiguous` lists the tied
types. Earlier versions took the first tied type, which cross-paired `Seat_Pad_Fabric_Colour` with `Chair_Fabric_Type`.
Selecting a tied property as the manual Fabric property is refused, as before. Consequence: such articles are
enumerated unreduced until the data (or an owner decision) says which type each colour set follows.

## AND/OR semantics

Not decided by the resolver. A colour's relations are separate relation objects; the evaluator (three-valued, a
precondition is violated only when definitely FALSE) is applied to each and a colour must satisfy all, as for any value.
Colours with several relations are rare in the three series (at most one type-1 relation per colour value).

## Not validated / open

* The "first valid colour" and "flagged default wins" rules are the agreed rule, **not checked against pCon output**.
* A colour that carries no relation naming the type (e.g. only a `$ BAN` relation that is TRUE) is valid for every type by
  OCD semantics and can be the first valid colour; none of the three series does this for its own articles.
* Group-to-colour structures exist only through ordinary intermediate properties in OCD; no inspected series has one. The
  synthetic tests treat the group as a sub-type (it is reduced the same way); whether pCon reduces it is unverified.
* The type value itself is not reduced (Tun flags type `1HA` as default; every valid type is still enumerated).
* Real-data SKU counts are measured with all other properties pinned to the first valid configuration; the unpinned
  product of Tun/Lino/Bay is too large to enumerate here.
