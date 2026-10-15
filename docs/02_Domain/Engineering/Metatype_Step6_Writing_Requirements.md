# Metatype Step 6 (writing half) — Requirements and Dependencies

**Status: preparation only (2026-10-15). Nothing here is implemented.** No writer service exists, no file in the
HMX repository was touched, no build tool was run. This document records what the authoritative template says
about writing, what the confirmed specification can supply, what is unknown, and what must be decided before
any code may write to the repository.

Sources: `POLYMORPHIC_METATYPE_CREATION_TEMPLATE_04092026.md` (authoritative; `C:\Users\siaoca\Downloads\`),
`Verus_Metatype_Prompt_TEST.md` (supplementary, same folder), `docs/02_Domain/Engineering/Metatype.md` (§3.2 schema,
§4 relationships, §5.4 modes, §6 gaps, §10 open decisions) and the MT 1.18.0 manual extract cited there.
Labels: **TEMPLATE** = stated by the template; **VERUS** = only in the Verus prompt; **MANUAL** = MT manual;
**REPO** = observed in the HMX data; **UNKNOWN** = no source.

## 1. What the template says about writing — in full

Step 6, second sentence: *"Only after explicit confirmation, proceed to implement (edit `go_types.csv`,
`go_propvalues.csv`, `go_proporder.csv`, `go_children.csv`, `go_actions.csv` etc. as needed, following the series'
existing conventions identified in Step 1)."*

That is the whole instruction. The template gives **no row layouts, no mapping from answers to rows, no ordering,
no backup/rollback, no validation after writing, and no build step**. "As needed" and "etc." leave the file set
open; "following the series' existing conventions" delegates every format decision to Step 1's findings.

Consequences for this project:
- Confirming the specification (implemented) is the template's precondition, not an authorisation to modify the
  repository by itself. Writing needs its own owner approval (§5).
- The ten-file list in earlier project documents comes from the Verus prompt, not from the template.

## 2. Files the template names, and what each would need

"Spec" = the confirmed answers (Steps 3, 4, 4a, 5). Polymorphism branch only; the Childs branch does not exist.

| File (table) | Named by | Columns (MANUAL / REPO agree) | What a row needs from the specification | Mapping status | Missing input / blocker |
|---|---|---|---|---|---|
| `go_types.csv` | TEMPLATE | id, name, format, default, mode, filter | `name` ← Step 3 property name | **Partly documented.** name: documented (Step 3). | **id** (which Metatype receives the property) not asked: open owner decision. **format** (`ch`, `chf`, `chi`, …) not asked. **default** value not asked. **mode** unresolved (manual: bit 4 "controls the variant code"; real polymorphic examples such as atlas `GATLAS_Type` are 131 with no bit 4; Verus also 131). **filter** not asked. Also the manual's one-row-per-(metatype, property) rule cannot be checked without the id. |
| `go_propvalues.csv` | TEMPLATE | id, name, value, condition | Step 4a rows (value → articles or "all") | **Mechanism documented, mapping unknown.** TEMPLATE: 4a "is normally realized as a per-article value filter/whitelist in `go_propvalues.csv`… follow whatever mechanism the series already uses". MANUAL: requires mode 8192 on the property in `go_types`. | How an *article* is expressed in the `condition` BoolExpr is not documented. REPO (atlas): conditions reference value tokens (`@ATLAS_Type_SG`, …), not article numbers. Also depends on the unresolved mode (8192 would have to be added to the mode). No source says whether "all" rows are written or omitted. |
| `go_proporder.csv` | TEMPLATE | value, number | the value names (Step 4a) | **Partly documented.** MANUAL: needs mode 128; positive integers < 1000, no duplicates in a list. | Sort order is not collected. "Spaced by 10" is a project convention (VERUS), not a rule. Mode 128 again depends on the mode decision. |
| `go_children.csv` | TEMPLATE | child_key, manufacturer, program, article_nr, variant, pos_x/y/z, rot_x/y/z, condition | — | **Not applicable to the Polymorphism branch.** The template's child questions exist only in the Childs branch. | None for polymorphism; do not write. (Named in the template's list because it covers both branches.) |
| `go_actions.csv` | TEMPLATE | id, own_key, foreign_key, direction, condition, action, param_1, param_2, text | — | **Not required by any Polymorphism answer.** The template mentions it only as a *check* (4a: a `go_propvalues` filter must not make the default unreachable against `go_actions` gates). | Writing nothing is consistent with the template. The reachability check itself needs the default value, which is not collected. VERUS uses `go_actions` for the child case only. |
| "etc." | TEMPLATE | — | — | **Unspecified.** | The template does not say which other files "as needed" means. |

Files the template does **not** name but the work obviously touches (all VERUS/REPO, not TEMPLATE):

| File | Why it comes up | Columns | Status |
|---|---|---|---|
| `go_texts.csv` | Step 5 collects EN/DE/FR/NL. Template Step 5 never names a file. | key, language, text | **Key mapping is documented** (REPO: property/value identifiers appear as `go_texts.key`, en/de/fr/nl rows). **Encoding is an open owner decision**: 40 of 49 observed files are not valid UTF-8 and `go_info.csv` is empty everywhere, so the manual says system code page; the code page is unconfirmed. Existing keys/collisions are unchecked. |
| `go_properties.csv` | REPO: in atlas the article switch *is* realised here — each `go_articles` row names a parameter set (`prm_key`) and `go_properties` assigns the polymorphic property a different value per set. | id, key, name, value, variant_code, variant_value | **Not in the template. Not collected:** no step asks which value each article takes (4a asks which values are *valid* per article, not which one an article uses). Without it the article switch cannot be produced. |
| `go_articles.csv` | Articles listed in Step 4 may be new (the Step 4 check only warns). | id, manufacturer, program, article_nr, prm_key, chprm_key | Not collected for new articles (manufacturer, program, parameter-set key). Also an open question: VERUS mentions a `configid` that the manual's schema lacks (Metatype.md §6 item 3). |
| `go_propclasses.csv` | VERUS lists it. | id, prop_name, prop_class | Class name not collected. |
| `go_setup.csv` | VERUS lists it. | id, key, value | No Polymorphism answer maps to it. |
| build (`ebmkdb.exe mt.inp_descr <series>.ebase`) | VERUS only; **not a template step**. | — | Approval is an open owner decision; `make_ebase.bat` must never be run (blocking `pause`). |

## 3. Information the confirmed specification does and does not provide

| Provided by the confirmed specification | Used for (if a mapping were decided) |
|---|---|
| Property technical name, EN label | `go_types.name`; `go_texts` key + EN row |
| Property/value DE, FR, NL labels | `go_texts` rows |
| Values (typed in 4a, with EN text from Step 5) | `go_propvalues.value`, `go_proporder.value`, `go_texts` keys |
| Step 4 article list | which articles are involved |
| 4a per-value article validity ("all" or list) | `go_propvalues` whitelist rows |
| Step 4 scope (unconditional / scoped, free text) | unknown: conditions are kept as the user's text, never parsed |

| **Not** provided (would have to be asked or decided; none is guessed) |
|---|
| Target Metatype id (`go_types.id`) — open owner decision |
| Property format, default value, `filter`, **mode** (encoding unresolved) |
| Value → article binding (`go_properties` value per parameter set) |
| Sort numbers for `go_proporder` |
| How an article / a scope text becomes an OFML `condition` expression |
| `go_articles` fields for new articles; property class; setup flags |
| The text encoding for `go_texts` |
| Row order, comment headers and line endings to keep (follow the series' conventions — Step 1 summarises prefixes, formats and mode usage but not file layout) |

## 4. Mappings: documented versus unknown

| Mapping | Status |
|---|---|
| property name → `go_types.name` | documented |
| property/value identifier → `go_texts.key`, language rows en/de/fr/nl | documented (REPO relationship) |
| property + values → `go_proporder.value` | documented (REPO: 8/8 match in atlas); numbers unknown |
| 4a article list → `go_propvalues` rows | mechanism documented (TEMPLATE, MANUAL); row content **unknown** |
| polymorphic property value per article → `go_properties` | observed in atlas (REPO); not in template; **not collected** |
| mode value (4 / 131 / 8192 / 128 combination) | **unknown** — unresolved owner decision |
| target Metatype → `id` columns in every table | **unknown** — unresolved owner decision |
| scope conditions → `condition` columns | **unknown** |
| answers → `go_children` / `go_actions` rows | none required for Polymorphism |

## 5. Owner decisions that block safe writing

1. **Polymorphism mode encoding** (Metatype.md §6 item 9). Blocks `go_types.mode` and the gating bits for
   `go_propvalues` (8192) and `go_proporder` (128).
2. **Which Metatype receives the property.** Blocks every `id` column.
3. **`go_texts` encoding.** Blocks any `go_texts` write; a wrong code page corrupts non-ASCII DE/FR/NL text.
4. **Mapping of the answers to rows.** The template supplies none; someone must specify (or approve) the row
   layouts for `go_types`, `go_propvalues`, `go_proporder`, and decide the `go_properties` binding and the missing
   inputs in §3.
5. **Authorisation to modify the repository.** Confirming the specification is not that authorisation.
   Also unanswered: who may approve, and whether a staging copy must be used first. Note the configured root
   `C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx` is inside a **Subversion working copy** (metadata
   found at `...\Staging\HermanMiller`), so a write creates local modifications to a version-controlled tree.
6. **Build-tool approval** (`ebmkdb.exe`, never `make_ebase.bat`) — blocks the only machine check of the result.
7. **Whether Step 4a may be skipped / whether Step 2 stays auto-selected** — they change what the specification
   contains.
8. Unchanged background decisions: the "few" threshold, `hmx/layout`, grouping of unprefixed `fn` properties.

## 6. Safeguards that would be required before any write (proposed — none is in the template)

These are engineering requirements for a future writer, not template rules. Each addresses a risk observed in
this repository.

**Before writing**
- Re-check that the confirmation is current (`confirmation_is_current()`), the series was loaded through the
  existing loader, and the source files are unchanged since loading (`stale_sources`: size and mtime).
- Build the proposed result **in memory** from the current bytes, never from the stale snapshot; show a row-level
  diff (added rows per table) for approval. Writing begins only for the tables and rows shown.
- Run the existing relationship resolver (21 reference + 7 duplicate rules; **unverified against practice**,
  Metatype.md §8.7) on the proposed tables; any new error blocks. Add the template's own checks: default value
  reachable under every article's whitelist (4a); every new technical value has EN/DE/FR/NL rows (Step 5);
  (metatype, property) unique in `go_types`.
- Refuse tables with problems the loader already reports (decode errors, malformed rows, unreadable files), and
  refuse any file that is a symlink or outside the series' numbered directory.
- Preserve each file's encoding, line endings (`\r\n` observed) and comment lines byte-for-byte except the
  appended rows; reject a `go_texts` write until the encoding decision exists.
- Block unless the owner decisions in §5 items 1–5 are recorded.

**While writing**
- Back up every file to be changed, with its SHA-256, in a manifest outside the repository. (REPO shows `.bak`
  siblings were made by hand; they must not be relied on or created implicitly inside the repository.)
- Write each file to a temporary file in the same directory and replace it atomically; stop on the first failure.
- Never touch files outside the shown diff; never delete.

**After writing**
- Re-read through the loader and compare: every pre-existing row unchanged, only the approved rows added.
- Re-run the inspector and resolver on the result.
- Only then, if approved, run `ebmkdb.exe mt.inp_descr <series>.ebase` (exit code 0 and a fresh timestamp are
  the only stated success criterion; no content-level validation exists in any source — Metatype.md §10 item 9).

**Rollback**
- Automatic: on any failure, restore each file from the manifest after verifying the backup hash and the current
  file hash, and report exactly what was restored.
- Manual fallback: the version-control working copy (Subversion) can revert local modifications; whether the tool
  may invoke it is an owner decision, and nothing here runs it.
- A completed write that the user later regrets is a version-control matter, not something the tool should undo
  silently.

**Gate behaviour** — `6w` stays "not implemented", and child Metatypes stay locked, until a writer exists that
satisfies the above **and** the Childs branch is implemented.

## 7. What was verified in the confirmation half (for the record)

Audit run 2026-10-15 against the implemented Step 6 confirmation (service-level, real session): the summary
contains all six template items; viewing/refreshing/status calls never confirm; changing any of Step 3 label,
property or value DE/FR/NL/EN, Step 4a articles / "all" / value names, Step 4 scope or article list makes the
confirmation stale; re-submitting identical Step 3/4a/5 content keeps it valid; re-submitting identical Step 4
forces 4a to be re-confirmed (existing 4a behaviour) and the confirmation is valid again afterwards; loading any
series (including the same one) resets it; confirming writes nothing (repository hashes unchanged), derives no
mode, and leaves children locked. No defect was found; the only change was one extra test for a reachable branch
(`SPEC_PROPERTY_CHANGED`).
