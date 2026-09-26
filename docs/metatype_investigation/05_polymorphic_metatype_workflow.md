# 05 — Polymorphic Metatype Creation Workflow (Reconstructed)

Built from three sources, each explicitly attributed: the manual's initialization-order and
build-step facts (**DOCUMENTED FACT**), the interactive process
(`POLYMORPHIC_METATYPE_CREATION_TEMPLATE_04092026.md`, **PROJECT PROCESS FACT**), and the fully
worked Verus example (`Verus_Metatype_Prompt_TEST.md`, **PROJECT PROCESS FACT**, cited as
"Verus"). This is a reconstruction, not a proposal — no code has been written from it yet.

## STEP 1 — Read repo/series data first
**Input:** target series name (e.g. `atlas`, `pullman`, `verus`).
**Processing:** inspect the target series' own `go_types.csv` (existing naming
pattern/prefixes/mode conventions), `go_propvalues.csv` + `go_proporder.csv` (existing
properties/value structure), `go_children.csv` (existing parent/child patterns), any prior
`docs/*.md` notes in-series.
**Repository data:** if the target series is sparse/unbuilt (48 of ~99 families are, per file
01), fall back to a reference built series (`atlas`, `pullman`, `layout_studio` are named in
POLY-TEMPLATE) for structural patterns — but adapt to the target series' own prefix, don't copy
verbatim.
**Output:** a summary of the target series' existing conventions, presented to the user before
proceeding.
**Validation:** none automated; human confirmation that the summary is accurate.
**Evidence:** [POLY-TEMPLATE Step 1].

## STEP 2 — Choose pattern
**Input:** user decision.
**Processing:** ask user to choose between **Polymorphism Metatype** (articles switch/swap via a
property, no parent/child structure — maps to manual's article polymorphism, mode 4) vs.
**Metatype with Childs** (parent metatype attaches/controls child articles — mode 8).
**Output:** chosen pattern, drives STEP 4 branching.
**Evidence:** [POLY-TEMPLATE Step 2]; manual basis in file 04 §1.

## STEP 3 — Property identity
**Input:** user decision.
**Processing:** ask for (1) technical property name matching the series' `G<SERIES>_...`
convention (e.g. `GATLAS_...`, `GPULLMAN_...`, `GVERUS_...`), (2) English display label.
**Output:** property name + label, feeding go_types.name and go_texts rows.
**Validation:** name must follow [MT §go_types Property Name] rules — `G`-prefix, each word
capitalized, no umlauts/special chars/spaces (project convention additionally forbids
underscores in the property name itself, file 04 §7 item 6).
**Evidence:** [POLY-TEMPLATE Step 3]; [MT §go_types Property Name].

## STEP 4 — Branch by pattern
**Input:** STEP 2 choice + STEP 3 property.
**Processing (Polymorphism branch):** which articles the property switches between; is the
switch unconditional or scoped (parent property/region); does every article accept every value
or are there exceptions → STEP 4a.
**Processing (Metatype-with-Childs branch):** which child-defining property to use/create + its
label; all possible values; are all values valid for every parent article or are there
exceptions → STEP 4a; for each value, which article(s) it attaches as a child; optional
positioning/offset behavior per child (only if user raises it, else reuse the series' existing
`go_children.csv` conditional pattern).
**Output:** full value/article mapping table.
**Evidence:** [POLY-TEMPLATE Step 4].

## STEP 4a — Value-validity-per-article exceptions
**Input:** STEP 4 output.
**Processing:** ask explicitly whether all articles accept the full value set, or whether
exceptions exist; if so, go **value by value** (not article by article), building
`Value | Valid for article(s)` (unstated values default to "all").
**Repository mechanism:** normally realized as a per-article value whitelist in
`go_propvalues.csv` (mode 8192 must be set on the property in `go_types` — a prerequisite not
called out in the process doc itself, confirmed only by cross-referencing the manual, file 04 §2)
— not by disabling the value globally; follow the series' existing mechanism.
**Validation:** explicit warning — check that a `go_propvalues.csv` filter does not conflict with
an enable/default gate in `go_actions.csv`, which would make the default value unreachable in
some article context. This is a known real bug class per the project doc, not a hypothetical.
**Evidence:** [POLY-TEMPLATE Step 4a]; [MT §go_propvalues] (mode 8192 gate).

## STEP 5 — Translations (always last)
**Input:** every technical value/property/label introduced in STEPs 3-4a.
**Processing:** produce EN → DE → FR → NL for each, presented as a table for confirmation, in
that fixed order.
**Output:** rows for `go_texts.csv` (single multi-language file with a `language` column per
Verus's actual practice, not one file per language).
**Evidence:** [POLY-TEMPLATE Step 5]; [Verus go_texts.csv description].

## STEP 6 — Confirmation, then implementation
**Input:** the complete spec assembled across STEPs 1-5.
**Processing:** present a full summary (pattern, property name+labels, values+labels, article
mapping, STEP 4a exceptions table, scoping conditions) for explicit user confirmation. **Only
after confirmation** may files be edited.
**Repository data written:** `go_types.csv`, `go_propvalues.csv`, `go_proporder.csv`,
`go_children.csv`, `go_actions.csv`, `go_childprops.csv`, `go_propclasses.csv`,
`go_properties.csv`, `go_setup.csv`, `go_texts.csv` — following the series' existing conventions
identified in STEP 1.
**Evidence:** [POLY-TEMPLATE Step 6].

## STEP 7 — Build / compile (recovered from repository + Verus, not documented by the manual as a concrete command)
**Input:** the edited `go_*.csv` set.
**Processing:** `cd hmx/<series>/1`; run `ebmkdb.exe mt.inp_descr <series>.ebase` directly
(**not** `make_ebase.bat`, which contains a blocking `pause` unsuitable for non-interactive
execution).
**Output:** `<series>.ebase` with a fresh timestamp.
**Validation:** exit code 0 + fresh timestamp on the output file is the stated success criterion.
No content-level validation step is described anywhere in the supplied materials — this is a
genuine gap (see file 07).
**Evidence:** [Verus "Build step"]; file 01 §3.

## Worked example cross-check (Verus, both patterns combined)

Series `verus` (manufacturer `hmx`), parent metatype `MT_VERUS`, child metatype
`MT_VERUS_Headrest`. Parent articles PIA1Z/PIA2Z (headrest-capable) vs. PIA4SZ/PIA7Z
(headrest hidden) — this is the **Polymorphism** pattern applied to `GVERUS_Type` deciding which
article is active, combined with the **Metatype-with-Childs** pattern applied to
`GVERUS_Headrest` (mode 11 = 1+2+8, controls the `CH_Headrest` sub-item) deciding whether/where
the headrest child attaches. Every file touched (`go_articles`, `go_types`, `go_propclasses`,
`go_properties`, `go_proporder`, `go_childprops`, `go_children`, `go_actions`, `go_texts`,
`go_setup`) and every row's exact content is documented in file 04's mode-arithmetic decode and in
the raw findings; not re-duplicated here.

## How the final output can be verified

1. **Structural**: `ebmkdb.exe` exit code 0 (compile-time validation — catches schema violations,
   malformed CSV, dangling FK-like references the compiler checks).
2. **Reachability** (project-specific, not spec-required): for every article, confirm the
   property's default value is not excluded by a `go_propvalues` filter for that article's
   context — the exact bug class STEP 4a warns about.
3. **i18n completeness**: every technical value/property introduced has EN/DE/FR/NL rows in
   `go_texts.csv` (STEP 5's explicit fixed order).
4. **UNKNOWN**: no functional/runtime validation step (e.g. loading the compiled `.ebase` into an
   actual OFML-conformant viewer/configurator) is described in any of the 5 source documents —
   Metatype-Inspector 3.0 is the obvious candidate tool for this but its validation behavior is
   undocumented in the supplied materials (file 04 §8 item 4).
