# 07 — Validation & Independent Test Plan

Each proposed step from file 06 §6 must be connected and tested one at a time (investigation
brief rules 12/15/16) — no big-bang implementation. Tests below are boundaries, not
implementations.

**Test 1 — Repository discovery**
Given the real `hmx\` root (or a fixture copy), `discover_repository()` returns exactly the
built/unbuilt classification independently confirmed in file 01 §2 (53 built, ~48 unbuilt, `dlm`
empty, `catalogue`/`info` excluded as non-product). Regression fixture: a small synthetic tree
with one built, one unbuilt, one empty, one non-product folder.

**Test 2 — Repository structure validation**
Given a series folder, confirm the five-subfolder skeleton (`1`, `ANY`, `EURO`, `GBP`, `NOPRICE`)
is detected correctly and that a folder missing subfolders is reported, not silently skipped.

**Test 3 — go_* file discovery**
Given a series' `1/` folder, glob for `go_*.csv` and correctly exclude/flag known anomaly
patterns found in file 02 §"Anomaly files" (`.bak`, `.new`, `__new.csv`, `_myne`, `_ORIG_MANUAL`,
`.zip`, prefix-less `Copy.csv`) rather than silently ingesting them as live tables.

**Test 4 — CSV schema loading**
Given one `go_*.csv` file per table type (fixtures drawn from the real cyclade_Tables/atlas
samples captured in file 02), parse per the semicolon/`#`-comment/quoting rules in [MT §2] and
assert the exact column set matches the `mt.inp_descr`-confirmed schema (file 02 master table).
Include a fixture for an always-empty table (asserting zero rows is a pass, not an error) and a
fixture for a multi-language `go_texts.csv`.

**Test 5 — Relationship resolution**
Using the atlas/cyclade_Tables fixtures, assert every confirmed FK chain from file 03 resolves:
`go_articles.prm_key→go_properties.key`, `go_articles.chprm_key→go_childprops.key→
go_childprops.child_key→go_children.child_key`, `go_properties/go_types/go_propclasses.name→
go_texts.key`, `go_propvalues.condition` tokens ↔ `go_proporder.value`. Include a negative fixture
with a dangling `child_key` to confirm it's caught, not silently dropped.

**Test 6 — Article-polymorphism reconstruction (mode 4 / go_info.configuration)**
Using a fixture modeled on Verus's parent-article switching (PIA1Z/PIA2Z/PIA4SZ/PIA7Z via
`GVERUS_Type`), confirm the model correctly identifies which property drives article switching
and which `go_actions` rows hide/reset dependent properties per article.

**Test 7 — Child-attachment reconstruction (mode 8)**
Using the Verus `CH_Headrest` fixture, confirm the model correctly resolves which value of
`GVERUS_Headrest` attaches which child, at which position, under which condition — and that the
"only articles 1Z/2Z attach the headrest" gating condition round-trips correctly.

**Test 8 — go_propvalues/go_proporder consistency**
Confirm every `@Token` referenced in a `go_propvalues.condition` has a matching `go_proporder.value`
entry where mode 128 is set (file 03 evidence e), and separately confirm mode 8192 is actually set
on any property that has `go_propvalues` rows (file 04 §2's documented prerequisite).

**Test 9 — Reachability validation (the STEP 4a bug class)**
Construct a fixture where a `go_propvalues` filter excludes a property's declared default value
for one article, while `go_actions` sets that article's default without adjusting the filter —
assert the validator flags this as unreachable, matching the exact bug class the process doc
warns about (file 05 STEP 4a).

**Test 10 — Output generation (write path)**
Given a validated in-memory model, assert `generate_output()` produces byte-identical-format CSV
(semicolon-delimited, correct quoting) that a human editor would have produced by hand, checked
against one of the real `.bak`→live diffs captured in file 02/03 as a regression fixture (the
`cyclade_Tables` program-rename diff is a ready-made before/after pair).

**Test 11 — Build/compile verification**
Mocked `ebmkdb.exe` subprocess call: assert `verify_output()` correctly interprets exit code 0 +
timestamp change as success, and non-zero exit / missing binary as failure, without ever invoking
`make_ebase.bat` (blocking `pause` risk, file 05 STEP 7).

**Explicitly out of scope for this test plan** (real content unknown, flagged not guessed):
Metatype-Inspector 3.0 integration (its rules are undocumented, file 04 §8 item 4) and any
functional/runtime OFML-viewer verification of the compiled `.ebase`.

## Sequencing

Tests 1-4 (pure read, no relationships) → Test 5 (relationships) → Tests 6-9 (semantic
reconstruction + validation, read-only) → Test 10 (write path, only after 1-9 are solid) → Test
11 (external tool integration, last). This mirrors "one step → test → verify → connect next step
→ test again" (investigation brief rule 16) and keeps the highest-risk capability (writing to a
real OFML repository) last and best-guarded.
