# Metatype Write Contract — Decisions and Evidence

**Status: 2026-10-20.** Resolves, from evidence, what can be decided about writing Metatype data, and states exactly
what still needs the owner. Supersedes the open items of `Metatype_Step6_Writing_Requirements.md` where noted.
**Nothing was written to the HMX repository or its Subversion working copy** while producing this document; all
repository access was read-only (repository hashes were compared before and after each survey).

Labels: **VERIFIED** = observed in the real repository, the manual extract or a passing test, with the source named.
**RECOMMENDATION** = proposed answer the evidence supports but does not force. **OWNER DECISION** = no source can settle it.

Evidence base: the template `POLYMORPHIC_METATYPE_CREATION_TEMPLATE_04092026.md` (158 lines, read in full);
`Verus_Metatype_Prompt_TEST.md` (supplementary, a worked example, *not* authoritative); `docs/02_Domain/Engineering/Metatype.md`
(MT 1.18.0 manual extract, cited as [MT]); the real repository
`C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx` — 50 series with `mt.inp_descr` (surveys are read-only
and reproducible from the counts quoted below).

## 0. Summary

| # | Decision | Status | Implemented |
|---|---|---|---|
| D1 | The property belongs to the Metatype named by the Step 4 articles' `go_articles.id` | VERIFIED | `owner_resolution.py` + 4 tests |
| D2 | Which value each article takes (`go_properties` binding) | **OWNER DECISION** — the interview never asks | blocked |
| D3 | Row layouts of `go_types`, `go_properties`, `go_propvalues`, `go_proporder`, `go_texts` | VERIFIED (layouts) / see D2, D4, D6 for the content | not written |
| D4 | Mode policy for the new property | RECOMMENDATION (3, +128, +8192) → **OWNER DECISION** to confirm | blocked |
| D5 | `go_texts` encoding | VERIFIED for existing files; **OWNER DECISION** for empty/ASCII-only files | blocked |
| D6 | Property format / default / filter | RECOMMENDATION (`ch`, first value, empty) → **OWNER DECISION** | blocked |
| D7 | MetatypeID / ConfigID / ChildParentID | VERIFIED: real `go_articles.csv` fields (`id` / `prm_key` / `chprm_key`) | implemented + tests |
| D8 | Modifying the Subversion working copy | **OWNER DECISION** (authorisation) | blocked |
| D9 | Uniqueness, relationship, validation rules | VERIFIED subset implemented; rest recommended | partly implemented |
| D10 | Running the build tool | **OWNER DECISION** | not run |

## D7. MetatypeID, ConfigID, ChildParentID are `go_articles.csv` fields — VERIFIED

**Correction of earlier findings.** `Metatype.md` §6 item 3 and `Metatype_Step6_Writing_Requirements.md` §2 recorded
"`go_articles` has no `configid` column" and treated the three names as another model. That was wrong in a precise way:
the names are *comment labels* in the file header, not schema names, which is why `mt.inp_descr` never declares them.

Evidence (survey of all 50 series):

| Fact | Count / source |
|---|---|
| Declared layout of `go_articles` | `id, manufacturer, program, article_nr, prm_key, chprm_key` in every `mt.inp_descr` ([MT] §go_articles; e.g. `atlas/1/mt.inp_descr` lines 16-23) |
| Header comment over the data | 30× exactly `#[metatypeid];[manufacturer];[program];[article];[configid];[childparentid]`; 7× with `[propertyid]` instead of `[configid]`; 1× `[man.]` and `[propertyid]`; 1× `[childparent i d]` — 39 of 50 files carry a label line, e.g. `accessories/1/go_articles.csv` |
| Position of each label | col 1 = `[metatypeid]` = `id`; col 5 = `[configid]`/`[propertyid]` = `prm_key`; col 6 = `[childparentid]` = `chprm_key` |
| Col 1 is a Metatype | 822 of 822 rows name an id that owns `go_types` rows |
| Col 5 is a key into `go_properties` | `go_properties` header is `#[metatypeid];[configid];[property];[propvalue];...` (29×, `[propertyid]` 10×); col 5 resolves to a `go_properties.key` in every row of 36 of the 39 labelled series; across all 50 series **29 rows do not** (e.g. `bound_screens` `GF1NGBFB.`, `dalby` `CFG_NODLE200`, `nevi_enhanced` `MT_NV_DWE3MBD`) |
| Col 6 is a (comma) list of `go_childprops` keys | 108 rows hold a list (`pullman`: `CHP_POWER_UNIT, CHP_TV_BRACKET`); 27 of 518 tokens do not resolve |
| ConfigID is **not derivable from the article** | atlas `MT_ATLAS_Table__UPXSGA`, pullman `CFG_NOPUL2`, cyclade `CFG_FE1L`, verus plain `PIA1Z`. The Verus prompt's "plain article number" rule is one series' convention and contradicts atlas/pullman |

Consequences, all implemented:
- `metatypeid` = `id` (editable), `configid` = `prm_key` (**read-only**, never generated; a dangling value is a *warning*),
  `childparentid` = `chprm_key` (editable, comma list). `ArticleReconciliation.roles` carries the mapping.
- The alias is applied **only** when a series declares exactly the manual's six columns in that order
  (`ARTICLE_LAYOUT`). A literal column named `metatypeid`/`configid`/`childparentid` still wins. Other layouts get no
  alias — the existing test "a schema without mapping fields never maps `id`" (4-column layout) still holds.
- Before this change every real series displayed as "mapping unavailable" and nothing was editable. Now 50 of 50 series
  with rows load with all three roles; verified by `test_every_real_series_loads_with_aliases...` and a full
  read-only run (50/50 aliased, 50/50 planned and verified).

Tests: `tests/test_metatype_write_contract.py::test_manual_layout_aliases_the_three_roles`,
`test_configid_prm_key_is_read_only_and_never_generated`, `test_other_layouts_get_no_alias`,
`test_page_shows_role_labels_and_planned_output`, `test_every_real_series_loads_with_aliases_and_plans_verify_in_memory`.

## D1. Which Metatype owns the selected property — VERIFIED

[MT] §go_types: one row per (Metatype, property); the real `go_articles.id` of an article is its Metatype (D7, 822/822).
Template Step 4 names the articles the property switches between, hence the owner is the single `go_articles.id` those
articles share. Rule, implemented in `services/metatype/owner_resolution.py`:

- all listed articles exist and name one Metatype → that id;
- an article is not in `go_articles` (new article) → **not resolved**, the missing articles are listed;
- the articles name several Metatypes → **not resolved**, the candidates are listed (a `go_types` row would be needed on each);
- no articles / no `metatypeid` role → not resolved.

Never guessed. Tests: `tests/test_metatype_owner_resolution.py` (4). *Remaining*: the UI does not yet ask the user to
choose when it is unresolved (the property-creation writer is not built; see D2).

## D3. Record layouts — VERIFIED (layouts only)

Layouts read from `mt.inp_descr` ([MT] and real files) and sample rows. Row *content* depends on D2/D4/D6.

| File | Columns | Real example (`atlas/1`) | Header-comment label | Gate |
|---|---|---|---|---|
| `go_types.csv` | `id;name;format;default;mode;filter` (`mode` uint16) | `MT_ATLAS_Table ; GATLAS_Type ; ch ; ATLAS_Type_SG ; 131 ;` | `#[metatypeid];[property];[format];[default];[mode];[filter]` (37 files) | — |
| `go_properties.csv` | `id;key;name;value;variant_code;variant_value` | `MT_ATLAS_Table ; MT_ATLAS_Table__UPXSGA ; GATLAS_Type ; ATLAS_Type_SG ; ;` | `#[metatypeid];[configid];[property];[propvalue];[variantcode];[variantvalue]` | — |
| `go_propvalues.csv` | `id;name;value;condition` | `MT_ATLAS_Table ;GATLAS_Screen;ATLAS_Screen_Single_Sided;GATLAS_Type == @ATLAS_Type_SG \|\| GATLAS_Type == @ATLAS_Type_PT` | `#[metatypeid];[property];[value];[condition]` (1 file) | property mode **8192** [MT] |
| `go_proporder.csv` | `value;number` (**number is `uint8`**) | `ATLAS_Type_SG;  10` | none | property mode **128** [MT] |
| `go_texts.csv` | `key;language;text` | `GATLAS_Type\t\t\t;en;Type` | none | — |

Observations that constrain the writer:
- `go_propvalues.condition` is a BoolExpr over **other property values** (`@Token` references), 407 rows with a condition,
  2 without — *not* a list of article numbers. A per-article restriction (Template Step 4a) is therefore expressed through
  the selector property's value that selects that article (as in the `GATLAS_Type == @...` rows above), which needs D2.
- `go_proporder.number` is declared `uint8` (max 255); [MT] says "positive integers < 1000". Real values: 341 rows,
  1..220, none > 255. **Discrepancy: the schema wins** — a writer must not emit a number above 255.
- Line endings are CRLF in atlas `go_types.csv` (182 CRLF, 0 bare LF, ends with a newline) and in 46/46 non-empty `go_texts.csv`.
- `go_children.csv`, `go_actions.csv`, `go_propclasses.csv`, `go_setup.csv`: **not** produced by the polymorphism branch.
  The template names `go_children`/`go_actions` for both branches; `go_actions` is only a reachability check (Step 4a), and
  the Verus prompt's `go_propclasses`/`go_setup` rows are not template requirements.

## D2. Value → article binding — OWNER DECISION

Atlas realises the article switch in `go_properties`: each `go_articles` row names a parameter set (`prm_key`), and
`go_properties` gives the polymorphic property a value for that set (e.g. `MT_ATLAS_Table__UPXSGA` → `ATLAS_Type_SG`).
Template Step 4 asks *which articles* the property switches between and Step 4a asks which values are *valid* per
article — **no step asks which value an article takes**, so the `go_properties` rows (and the `go_propvalues` conditions
built on them) cannot be produced from the interview answers. Needed: a new interview question ("for each article, which
value does it take?") or an owner statement that it is out of scope. Not guessed.

## D4. Polymorphism mode encoding and allowed values — RECOMMENDATION, owner to confirm

Facts (survey of 1,893 `go_types` rows, 435 of format `ch`):
- **Bit 4 ("controls the variant code") is set on 0 rows.** `Metatype.md` §6 item 9 is confirmed: the "mode 4 = polymorphism"
  reading is the project's gloss, not what the data does.
- A *polymorphic selector* (a property given more than one distinct value across the parameter sets) occurs at least 135
  times; the modes of those found are `3` ×75, `131` ×49, `19` ×4, `147` ×2, `8323` ×2, `2689`, `2`, `130` ×1 each. Every one is format `ch`.
- `ch` property modes overall: `3` ×206, `907` ×51, `131` ×49, `19` ×25, `8331` ×13, `8329` ×12, `8587` ×10, `11` ×9.
- Bits: 1 editable, 2 global modification, 128 sort order via `go_proporder`, 8192 validity via `go_propvalues` ([MT] §5.4).
  The gates are not always paired in practice (e.g. `mimo` has a mode-8192 property and no `go_propvalues` rows).

Recommended policy: `3` (editable + global modification); add `128` only when `go_proporder` rows are written; add `8192` only
when `go_propvalues` rows are written; never set bit 4 or 2048 (2048 is documented as `na`/`fn`-only and unresolved for `ch`,
`Metatype.md` §6 item 1). This reproduces the two most common real selector modes (3 and 131). **Owner to confirm.**

## D5. Translations and `go_texts` encoding — VERIFIED / OWNER DECISION

Facts (46 non-empty `go_texts.csv` files of 50):
- Layout `key;language;text`, languages exactly `en` 1813, `nl` 1699, `fr` 1690, `de` 1687 rows — matches the template's EN/DE/FR/NL.
- **40 files are not valid UTF-8**; their non-ASCII bytes are single-byte Windows-1252 (`B\xfcrostuhl Gr\xf6\xdfe A`,
  `Ausf\xfchrung` → *Bürostuhl Größe A*, *Ausführung*). 4 files are pure ASCII; 2 are valid UTF-8 with non-ASCII text
  (`layout_studio`, `pullman`). `go_info.csv` is empty in every series, so the manual's `utf8` switch is never set.
- The shared loader decodes strict UTF-8 and reports `DECODE_ERROR` on the 40 cp1252 files unless a fallback is opted into.
  Reading `go_texts` through the loader therefore needs `fallback_encoding="cp1252"`; this was not changed.

Recommended rule: **preserve each file's own encoding** (strict UTF-8 first, else Windows-1252; refuse text that does not
encode). Owner decision still needed for an empty or ASCII-only `go_texts.csv` receiving non-ASCII German/French text
(recommend Windows-1252: 40 of 42 non-ASCII files use it, and [MT] points to the system code page).

## D6. Property format, default, filter — RECOMMENDATION

`ch` (every real polymorphic selector is `ch`). `default` is the value the property starts with (atlas: the first value,
`ATLAS_Type_SG`); `filter` is empty for a selector (atlas row above). The interview collects neither; recommended default:
first value of Step 4a, with the user able to change it. **Owner to confirm.** Reachability check from the template Step 4a
note (a `go_propvalues` filter must not make the default unreachable) needs the default and D2.

## D8. Modifying the Subversion working copy — OWNER DECISION

Facts: the configured root lies inside an SVN working copy (`C:\HermanMillerOFMLSVN\Staging\HermanMiller\.svn`, `wc.db`,
`format` = 12, i.e. Subversion 1.8 or newer). No `svn` command-line client is on the PATH of this machine (TortoiseSVN's GUI
is installed). Hand-made `.bak` siblings exist (`go_articles.csv.bak`, `go_types.csv.bak`, …), so the team already edits
these files in place. The application never invokes Subversion.

Recommended contract (not authorised): write only the files shown in the reviewed plan; refuse a file that changed since
load; back up each file with its SHA-256 outside the repository; write to a temporary file in the same directory and replace
atomically; stop on the first failure and restore from the backup; verify by re-reading; **never** run `svn add/commit/revert`
— the developer reviews the working-copy diff in TortoiseSVN and commits themselves. Requires from the owner: (1) permission to
modify the working copy at all, (2) whether a staging copy must be used first, (3) who may approve.

**Until that is given, `can_create()` stays `False`.** What exists instead is a *plan*: `plan_article_edits` computes and verifies
the exact new bytes of `go_articles.csv` in memory (see D9) and the Review shows the line-by-line diff, so the owner can inspect
precisely what would be written.

## D9. Uniqueness, relationship and validation rules

| Rule | Status | Source | Where |
|---|---|---|---|
| Article identity is (manufacturer, program, article); duplicates are ambiguous and not editable | VERIFIED | existing reconciliation + tests | `metatype_article_service`, `article_edit_session` |
| MetatypeID should be a `go_types.id` | VERIFIED as *usual*, so **warning**: 822/822 rows hold it, but a new Metatype's `go_types` row does not exist yet | D7 | `METATYPEID_NOT_IN_GO_TYPES` |
| ConfigID should be a `go_properties.key` | warning: 29 real rows violate it | D7 | `CONFIGID_NOT_IN_GO_PROPERTIES` |
| each ChildParentID token should be a `go_childprops.key` | warning: 27 of 518 real tokens violate it | D7 | `CHILDPARENTID_NOT_IN_GO_CHILDPROPS` |
| A reference is judged only if its table was read | VERIFIED design | tests | `ArticleReconciliation.references` |
| Value must not contain `;`, `"`, CR/LF; a first-column value must not start with `#` | VERIFIED (CSV structure, loader quoting rule) | `split_fields`, comment rule | errors `INVALID_CHARACTER`, `COMMENT_PREFIX` |
| An empty MetatypeID is never written | VERIFIED-derived (`id` binds the article; 822/822 rows non-empty) | D7 | planner refuses |
| Only the edited field changes; padding, comments, blank lines, terminators, BOM, other fields stay byte-identical | VERIFIED by re-parse | `article_write_plan.verify_file_plan` | tested incl. tampering |
| Encoding: strict UTF-8 like the loader; otherwise refuse | VERIFIED (loader rule; real `go_articles.csv` are ASCII) | | planner |
| Quoted lines and mapping fields stored in another table are refused | design | | planner |
| A file that changed since load is refused (line must equal the loaded record) | design | | planner |
| `(Metatype, property)` unique in `go_types` | [MT] documented, **not enforced** until a `go_types` writer exists | | — |
| MetatypeID / ChildParentID naming format or global uniqueness | **no source** — not enforced | | — |
| Many articles may share one MetatypeID | VERIFIED (822 rows, far fewer Metatypes) | | not flagged as duplicate |

## D10. Build tool — OWNER DECISION

`ebmkdb.exe mt.inp_descr <series>.ebase` exists in each built series folder and the Verus prompt names it. It is not a
template step, has no content-level validation, and `make_ebase.bat` contains a blocking `pause`. Not run; approval needed.

## What changed in the code (this phase)

| File | Change |
|---|---|
| `models/metatype_articles.py` | `ArticleReconciliation.roles`, `.references` |
| `services/metatype/metatype_article_service.py` | verified role aliases (`ARTICLE_LAYOUT`), reference sets from the loaded tables |
| `services/metatype/article_edit_session.py` | roles from the reconciliation, header labels, dangling-reference warnings, `#`/quote errors, new blocker text |
| `services/metatype/article_write_plan.py` (new) | in-memory write plan + verifier; never writes |
| `services/metatype/owner_resolution.py` (new) | D1 |
| `ui/pages/metatype_article_table.py`, `metatype_creation_page.py` | role labels; Review shows the planned output |
| tests | `test_metatype_write_contract.py` (20), `test_metatype_owner_resolution.py` (4); worktable test updated for the new blocker wording |

## Decisions needed from the owner (exact)

1. **D8** — authorise writing to the Subversion working copy (and say whether a staging copy comes first). *Unlocks* applying
   the verified `go_articles.csv` plan.
2. **D2** — add the "which value does each article take" question, or declare the `go_properties` binding out of scope.
3. **D4** — confirm the mode policy (3, +128 with sort order, +8192 with `go_propvalues`; never bit 4/2048).
4. **D5** — encoding for new text in an empty or ASCII-only `go_texts.csv` (recommend Windows-1252).
5. **D6** — confirm `ch`, default = first value, empty filter.
6. **D10** — whether `ebmkdb.exe` may be run after writing.

Items 2-5 gate only *new polymorphic property creation*. Item 1 alone gates *saving MetatypeID/ChildParentID edits*.

## Phase 2 (2026-10-20): owner selection, guarded staging writer, property rules

Implemented and tested; **no real repository was modified** (real data only read; hashes compared before/after).

| Item | Result | Where |
|---|---|---|
| D1 UI | Unique / multiple / none states, evidence per candidate, explicit choice only, validation (candidate, go_types rows, property already defined, new-article warning); cancel keeps pending edits and any earlier choice | `owner_selection.py`, `ui/pages/metatype_owner_dialog.py`, page button *Choose owner Metatype...* |
| D8 persistence | Writer exists but is **off**: needs `metatype_staging_root` AND `metatype_staging_authorised_by` in `AppConfig` (both empty by default), a staging root in a different working copy from the repository root, targets inside it, identical source hashes, a confirmation token bound to the exact bytes, backups with SHA-256 outside both trees, atomic replace, re-read verification, automatic rollback on failure and explicit `rollback`. Never touches `.svn`, never runs svn | `staged_writer.py`, page button *Apply to staging...* |
| D10 | Separate `plan_build` / `run_build`: needs staging authorisation, `metatype_build_authorised`, a confirmation token bound to the command and the existing `.ebase` hash; runs `ebmkdb.exe` directly (not the `pause` batch). Not wired to a button and never run | `build_step.py` |
| D2 | `ArticleValueTable`: explicit per-article values, none invented or broadcast, value must be in the property's values, ConfigID must already exist (never inferred), one ConfigID cannot carry two values. No UI table or writer yet - the go_properties writer is not built | `property_rules.py` |
| D4 | `encode_mode`: bit 4 and 2048 refused (bit 4 on 0 of 1,893 rows), uint16 enforced, policy `confirmed=False` by default so the mode is **unusable** until the owner confirms. New survey: bits 128/8192 are not consistently paired with `go_proporder`/`go_propvalues` (134 of 180 / 12 of 56 unpaired) - pairing stays a policy | `property_rules.py` |
| D5 | `append_text_lines`: preserves BOM, encoding (UTF-8 / cp1252), line endings and all existing bytes; refuses ambiguous encodings, mixed endings, unencodable text, and non-ASCII text for an empty/ASCII-only file until the owner picks an encoding | `text_encoding.py` |
| D6 | `build_property_format`: `ch`; the default must be chosen explicitly and be one of the values (139 of 174 real selectors; so *not* assumed to be the first value); filter optional (empty in 118 of 174, otherwise comma list of property names) | `property_rules.py` |

Still blocked (owner): D8 authorisation and the name of a staging working copy (the only working copies on this machine are
`C:\HermanMillerOFMLSVN\Staging\HermanMiller` - the configured repository - and `HermanMiller_old`; neither was designated
as staging); D4 policy confirmation; D5 encoding for empty/ASCII `go_texts`; D2 whether the interview gains the per-article value
question; D10 permission. The writers for `go_types`, `go_properties`, `go_propvalues`, `go_proporder` and `go_texts` rows are not
built, so *creating* a property remains disabled (`can_create()` is `False`); only the `go_articles.csv` edit path can be persisted.

## Phase 3 (2026-10-20): creation writers, value table, persisted state, gating

Implemented and tested on temporary fixtures; **no real repository or working copy was written** (the real-data test only reads).

**What the evidence settled (implemented):**

| Rule | Evidence | Where |
|---|---|---|
| The five tables are appended to, never rewritten; a series whose declared columns differ from the D3 layout is refused | `mt.inp_descr` of every series (D3) | `table_append.py` |
| A value's `go_texts` key is the value token itself (`ATLAS_Type_SG;...;en;Single Desk`), like the property name | `atlas/1/go_texts.csv` | `property_creation_plan.py` |
| New `go_texts` rows are grouped by language (all `en`, then `de`, `fr`, `nl`) | tail of real files holds the `nl` block; counts per language in D5 | same |
| New rows copy the padding of the file's last data row; an unterminated last line gets the file's own terminator; an empty/terminator-less file uses CRLF (46 of 46 real `go_texts` files) | atlas `go_texts`/`go_proporder` bytes | `table_append.py` |
| `go_proporder.number` 1..255 (`uint8`), `go_types.mode` 0..65535 (`uint16`) | schema | `validate_row` |
| A key already present is a conflict, not an overwrite (`go_types` id+name, `go_properties` id+key+name, `go_propvalues` id+name+value, `go_proporder` value, `go_texts` key+language) | [MT] one row per (Metatype, property); `go_proporder` is keyed by value only | `KEY_COLUMNS` |
| A `go_properties` row exists per article ConfigID (`prm_key`); the ConfigID is never inferred and one ConfigID cannot hold two values | atlas realises the article switch this way (D2) | `ArticleValueTable` |

**What stays blocked until the owner decides (each is a visible creation blocker, never a default):**

| Decision | State | How to release it |
|---|---|---|
| D4 mode policy | `metatype_mode_policy_confirmed` is `False`; bit 4 and 2048 stay rejected | owner sets it to `True` after confirming 3 (+128 with sort numbers, +8192 with conditions) |
| D5 non-ASCII text into an empty/ASCII-only `go_texts` | `metatype_text_fallback_encoding` is empty; existing UTF-8/cp1252 files are preserved without any decision | owner sets `cp1252` or `utf-8` |
| D8 staging | `metatype_staging_root` and `metatype_staging_authorised_by` are empty; neither existing working copy is chosen | owner names a staging copy in a *different* working copy |
| D10 | `ebmkdb.exe` is not part of creation | separate opt-in `build_step.py`, own authorisation |
| `go_propvalues` conditions | A condition is a BoolExpr over *other* property values and cannot be derived; when Step 4a recorded exceptions and none is typed, creation is blocked | user types `value;condition` lines |
| Sort numbers | only the user's numbers are written (atlas steps by 10, but that is one series' habit); if any is given every value needs one | user types `value;number` lines |
| D2 | The per-article table is explicit (nothing pre-filled or copied); whether `go_properties` is the right binding for *other* series than atlas is still the owner's call | owner confirmation |
| Property values (D6) | the interview collects values only when Step 4a has exceptions, so the creation form asks for them; default must be chosen explicitly (it is one of the values in 139 of 174 real selectors, not always the first) | user input |

**Persisted state.** The Articles table now distinguishes `source` (loaded snapshot, never modified), `pending`, `written`
(verified in staging: destination bytes re-read and re-parsed) and `failed` (pending, last write failed or rolled back). A
refresh keeps `written` values while the reloaded source still differs and drops the overlay once the source catches up.

**Creation gate** (`MetatypeCreationPage.can_create`, with specific reasons from `creation_blockers`): a verified multi-file plan,
a valid owner, explicit per-article values, validated mandatory fields, supported layouts and encodings, no unresolved policy
(D4/D5), a valid authorised staging copy, and - at the moment of writing - review and confirmation of the exact plan.
`ArticleEditSession.can_create()` is unchanged (`False`): it only knows the `go_articles` edits, not the property inputs.
