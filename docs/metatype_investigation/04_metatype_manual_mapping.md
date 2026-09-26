# 04 — Manual ↔ Repository ↔ Code Concept Mapping

## 1. What exactly is a Metatype, and what is "Polymorphic Metatype"?

**DOCUMENTED FACT** [MT §go_types intro]: "The table go_types defines the metatypes or metatype
instances of a manufacturer. Such a metatype represents a set of article numbers defined in the
table go_articles." I.e. **Metatype = an abstract, configurable product type**; a manufacturer
binds it to concrete article numbers via `go_articles`.

**DOCUMENTED FACT** [MT §1]: The Metatype concept enables two things beyond plain graphic-data
modeling: (a) **configuration on inter-product level** — a property change that swaps the *basic
article number itself* (not just intra-product properties), e.g. switching program/collection;
(b) concatenation/attachment rules for child parts, described by properties in an
article-dependent way.

**The phrase "Polymorphic Metatype" does not appear anywhere in `MT_1.18.0_en.md`.** It is
MillerKnoll project terminology (used in `POLYMORPHIC_METATYPE_CREATION_TEMPLATE_04092026.md`)
for what the manual calls **article polymorphism** — mechanism (a) above. The project doc's own
Step 2 in fact distinguishes two patterns, both loosely called "polymorphic Metatype work" in
practice:

1. **"Polymorphism Metatype"** — articles switch/swap via a Metatype property, no parent/child
   structure. Maps to the manual's article-polymorphism mechanism: a mode-4 ("controls the
   variant code") `ch`/`chi` property, `go_info.configuration` (series-wide
   consistent/inconsistent/serial recovery behavior), and `go_propvalues`/`go_actions` gating
   which values are valid/visible per active article.
2. **"Metatype with Childs"** — a parent metatype attaches/controls child articles. Maps to
   mode-8 ("controls a sub-item/child") properties driving the
   `go_articles→go_childprops→go_children` chain (file 03).

**Status: FOUND.** Both patterns are exercised together in the worked
`Verus_Metatype_Prompt_TEST.md` example (parent-article switching among PIA1Z/PIA2Z/PIA4SZ/PIA7Z
AND a conditionally-attached `CH_Headrest` child) — see file 05.

## 2. Manual concept → repository → code status table

| Concept | Manual reference | Repository file(s) | Column(s) | Example (repo/process doc) | Code representation | Status |
|---|---|---|---|---|---|---|
| Metatype instance | [MT §go_types] | go_types | id, name | `MT_CYCLADE`, `MT_VERUS` | none | **NOT FOUND** (no `Snapshot` field, no Metatype model) |
| Article binding | [MT §go_articles] | go_articles | id, article_nr, prm_key, chprm_key | `MT_CYCLADE;...;FE1L;CFG_FE1L;CHP_FE21` | none | **NOT FOUND** |
| Article polymorphism (mode 4 + go_info.configuration) | [MT §go_types mode; §go_info] | go_types, go_info | mode, go_info.configuration | Verus: parent articles switch on `GVERUS_Type` | none | **NOT FOUND** |
| Child/sub-item creation (mode 8) | [MT §go_types mode 8; §go_children/childprops] | go_childprops, go_children | child_key, pos_x/y/z, condition | Verus: `CH_Headrest` attached via `GVERUS_Headrest` | `models/relation_object.py` covers a *different* relation domain (OCD tCOMd_RelObj) — **not directly applicable** (file 06 §3g confirms) | **PARTIALLY FOUND** (analogous OCD relation concept exists in code, but not this one) |
| Property value whitelist (go_propvalues, mode 8192) | [MT §go_propvalues] | go_propvalues | id, name, value, condition | `atlas/1/go_propvalues.csv`; Verus Step 4a "per-article value filter" | none | **NOT FOUND** |
| Value display order (go_proporder, mode 128) | [MT §go_proporder] | go_proporder | value, number | `atlas/1/go_proporder.csv`, spaced-by-10 convention (project convention, not spec) | none | **NOT FOUND** |
| i18n labels (go_texts) | [MT §go_texts] | go_texts | key, language, text | en/de/fr/nl rows keyed by property/value id | Existing `Snapshot`/OCD text handling (`text_blocks`, `tCOMd_Text`) is a **different, OCD-specific** text model | **PARTIALLY FOUND** (parallel OCD mechanism exists, not this one) |
| Attachment points (go_attpt) | [MT §go_attpt] | go_attpt | key, direction, pos_x/y/z, rot_y | `atlas/1/go_attpt.csv`, `_GO_CHILD` special key | none | **NOT FOUND** |
| OFML class mapping (go_classes) | [MT §go_classes] | go_classes | id, class | `layout_studio`: `MT_LS_Desk;::hmx::layout_studio::lsMetaType` | none — and this is **conceptually distinct** from the current codebase's "Class Creation" (OCD property-class) workflow, a naming collision to avoid (file 06 §3d) | **NOT FOUND** |
| Behavior flags (go_setup / legacy GSetup) | [MT §go_setup] | go_setup | id, key, value | Verus: `NoMTOrderRep=1, HideOrderNo=1, ...` | none | **NOT FOUND** |
| Action/event matrix (go_actions) | [MT §go_actions] | go_actions | id, direction, action, condition, param_1/2 | Verus: CON_PROP/SET_PROP rows hiding/resetting `GVERUS_Headrest` per article | none | **NOT FOUND** |
| Build/compile step (mt.inp_descr → ebmkdb.exe → .ebase) | [MT §5, abstractly: "or file mt.ebase if compiled"] | mt.inp_descr, ebmkdb.exe, make_ebase.bat | — | Verus: `ebmkdb.exe mt.inp_descr verus.ebase` | none | **NOT FOUND** (not even documented precisely by the manual — recovered only from the repository + Verus prompt) |
| MDB access (unrelated but adjacent) | n/a | n/a (go_* is pure CSV, never MDB) | — | — | `services/mdb_service.py` | **N/A to Metatype** — confirmed go_* has no MDB involvement anywhere sampled |
| Canonical in-memory model | n/a | n/a | — | — | `models/snapshot.py` (extension target per `docs/pcon_investigation/10_canonical_model.md`) | **PARTIALLY FOUND** (right container, zero Metatype fields yet — file 06 §3b) |

## 3. Property formats (all DOCUMENTED FACT, [MT §go_types Format])

`ch` (symbolic choice), `chf`/`chi` (float/int choice), `f`/`i` (plain float/int), `fn` (free
numeric, parametrized by `go_freenumeric`), `na` (native-property wrapper, name = native name +
`G` prefix), `th` (thru property, transfers value predecessor→successor in concatenation, **not**
part of article polymorphism), `cp` (child-position representation, 2-digit mode = coordinate +
alignment), `lb` (read-only label).

## 4. Property mode bitmask (all DOCUMENTED FACT, [MT §go_types Mode]) — full 14-bit table

| Bit | Meaning |
|---|---|
| 1 | editable |
| 2 | considered for global modification |
| 4 | controls the variant code (article polymorphism) |
| 8 | controls a sub-item/child (mutually exclusive with 4) |
| 16 | invisible |
| 32 | inherited initially from parent/predecessor (both must be metatypes) |
| 64 | suppress filter-adaptation dialog (needs `ShowPolyPropFilterMsg` in go_setup) |
| 128 | explicit sort order via go_proporder |
| 256 | re-create main child's 2D/3D geometry after modification |
| 512 | force removal+recreation of own children after modification |
| 1024 | reposition main child's geometry after modification |
| 2048 | reposition own children after modification, filter lists affected child props — **"only needed for na and fn properties and works only there"** [MT], see §7 item 1 below for a documented contradiction |
| 4096 | standard collision detection on property change |
| 8192 | validity limited via go_propvalues |

## 5. Inheritance-control algorithm (DOCUMENTED FACT, [MT §go_nativeproperties]) — always empty in repo, never cross-checked against live data

1. Filter entries to matching ancestor `pid`, else fall back to `_ANY` entries only.
2. INCL+`_ALL` → inherit all native properties from that ancestor.
3. Else EXCL+`_ALL` → inherit none.
4. Else INCL+`_DEFAULT` → inherit all except EXCL-matched identifiers.
5. Else EXCL+`_DEFAULT` → exclude all except INCL-matched identifiers.
6. Else (no entries / table absent) → inherit all.

`na` properties are always excluded from this regardless of the above.

## 6. go_setup / GSetup flag reference (DOCUMENTED FACT, [MT §go_setup]) — abbreviated to flags actually seen populated in the repository (cyclade_Tables/Verus)

`NoMTOrderRep` (&1, metatype not a separate order-list node), `ChildOrderRep` (&2, children
become sub-items of main child), `HideOrderNo` (&16, hide auto-created article-number property),
`HideFilterMsg` (&32, suppress filter-change display), `PropClassNA` (&32768, legacy na-property
display grouping). Full ~25-flag table (including obsolete `Feedback3D`/GXSetup flags) is in the
manual; not reproduced in full here since none beyond the above five were observed populated in
any sampled family.

## 7. Explicit disagreements / extensions / gaps — process docs vs. manual

1. **Mode 2048 restriction contradiction (unresolved).** [MT]: mode 2048 "is only needed for na
   and fn properties and works only there." But `Verus_Metatype_Prompt_TEST.md` assigns mode 2051
   (1+2+2048) to `GHeightAdjustment`, a plain `ch`-format property (values `@V2`/`@V3`), with
   `filter=GVERUS_Headrest` — not documented as `na`/`fn` anywhere in that doc. Possible
   explanations, none resolvable from the docs alone: (a) implementation tolerates 2048 on `ch`
   properties despite the documented restriction; (b) the Verus example itself deviates from
   spec and `GHeightAdjustment` should be `na`/`fn`-typed; (c) mode 512 (unconditional child
   recreation, no na/fn restriction) may be the spec-correct choice here instead. **Flag to a
   human OFML expert before using this as a template — do not treat it as validated by the
   manual.**
2. **go_propvalues per-article whitelist pattern** — real repository mechanism (mode 8192 gate),
   but the *operational* pattern ("value filter" per article + the specific bug class where a
   `go_propvalues` filter conflicts with a `go_actions` enable/default gate, making the default
   value unreachable) is pure MillerKnoll project knowledge, not in the EasternGraphics spec.
3. **`go_articles.configid` (gap)** — `Verus_Metatype_Prompt_TEST.md` states "configid = plain
   article number (not `MT_VERUS__PIA1Z`)" for `go_articles.csv`, but the manual's documented
   `go_articles` schema has no `configid` column (`id, manufacturer, program, article_nr,
   prm_set, chprm_set`). **UNKNOWN** whether this is an OAP/MillerKnoll-tooling-specific column,
   an internal alias for `article_nr`, or a real schema extension beyond base MT — not
   confirmable from the 5 source docs read.
4. **"global" folder vs. per-series folder** — manual default: metatype tables live in a shared
   `global`/`meta` series folder (explicitly noted as renameable). MillerKnoll's actual practice
   (confirmed by both the Verus folder path `hmx/verus/1/` and the repository structure in file
   01) is **per-series** metatype tables — allowed by the manual's own "alternative names
   possible" note, so not a contradiction, but an unstated operational choice.
5. **Build toolchain** (`ebmkdb.exe`/`mt.inp_descr`) — the manual only says data "if compiled to
   EBASE format" produces `mt.ebase`, without naming the tool. Recovered entirely from the
   repository (file 01 §3) and the Verus prompt's exact invocation.
6. **"No underscores" property-naming house style** — Verus prompt's explicit rule is stricter
   than the manual's own naming rule (G-prefix + capitalized words, no umlauts/special
   chars/spaces — underscore isn't technically forbidden by the general ID type). A local style
   convention layered on a looser spec rule, not a contradiction.
7. **go_proporder spacing-by-10 convention** — practical convention (Verus: 10/20/30/40), not
   required by the manual (which only requires positive integers < 1000, no duplicates within a
   list).
8. **Agreement, worth noting for confidence**: every table name referenced in either process doc
   (`go_types`, `go_propvalues`, `go_proporder`, `go_children`, `go_actions`, `go_propclasses`,
   `go_properties`, `go_texts`, `go_setup`, `go_childprops`) is a currently-valid, non-obsolete
   table per the manual — no invented or incorrect table name was found in either process doc.

## 8. Consolidated open questions

1. Does mode 2048 actually function on `ch`-format properties, or is the Verus example
   non-compliant with the spec? (§7 item 1)
2. What exactly is `go_articles.configid` relative to `article_nr`/`id`? (§7 item 3)
3. `oap_metatype2type.csv` columns 4–5 semantics — file maps a metatype `id` to an OAP "type"
   code (e.g. `MT_LS_Desk → OAP_DESK`), referenced only by footnote in the manual ("OAP OFML
   Aided Planning Version 1.4 §4.8.4") — not confirmable from supplied materials.
4. Metatype-Inspector 3.0's actual validation rules are unknown — the supplied history PDF is a
   1-page changelog stating only "first official release (2025-11-14)," no functional detail.
5. The exact 6-scenario basket-order-position mapping ([MT §4], a diagram on manual page 34) is
   lossy in the markdown conversion used for this investigation; the flag/value rows are
   preserved but the outcome-per-scenario mapping is not fully reconstructable from the .md file.
6. Relationship (if any) to `MK_Workbench_Phase1_Test.spec` or other untracked git-status
   artifacts — out of scope for this investigation, not read.
