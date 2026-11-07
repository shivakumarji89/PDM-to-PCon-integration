# Article OBX Generator (OCD Engine) — Architecture

**Status:** CURRENT · **Date:** 2026-11-02 · **Scope:** `QA → Article OBX Generator (OCD Engine)` (`WorkflowStep.PCON_ARTICLE_OBX_GENERATOR`). Sibling documents: [PACKAGE_INVESTIGATION.md](./PACKAGE_INVESTIGATION.md), [REPOSITORY_DATA_MODEL.md](./REPOSITORY_DATA_MODEL.md). Engine internals: `docs/02_Domain/OBX/OCD_Engine.md`.

The generator is **standalone**: it reads an OCD repository folder, enumerates valid SKUs with the existing OCD Engine, prices them and writes an OBX with the existing serializer. It needs no pCon plugin, job folder, heartbeat or running pCon.planner. The supplied `p-bk_1.14.4_Installer.zip` contributed no code (it is a binary installer).

### Independence from pCon / EasternGraphics

The OCD Engine, SKU enumeration, relation and price processing, and OBX generation/validation are **pure Python** and
need no EasternGraphics plugin, SDK, licence, hash registration or .NET build. The Workbench ships and runs without any
C# component for this workflow. The earlier pCon plugin (`tools/pcon_obx_plugin`) and its job-folder bridge
(`services/pcon_sdk_obx`) were removed; they remain in Git history.

There is **no** pCon launcher, *Launch pCon.planner* button or other pCon runtime hook. `tests/test_independence.py`
asserts that the engine, OBX services and application shell load no pCon code and that the build files reference no
plugin or SDK. The only remaining pCon/EasternGraphics strings are data: the `vendorKey` fields the OBX serializer
writes (part of the OBX format) and the optional *Compare with Reference OBX* feature, which reads an OBX that
pCon.planner produced independently.

`tools/legacy_varcond_bridge` (a .NET Framework helper for PDM VARCOND parity checks) is unrelated to pCon and is
retained unchanged.

---

## 1. Data flow

```
 AppConfig.metatype_repository_root
          │
          ▼
 OcdCatalogueService.scan()            ── Load Catalogue ──▶ manufacturers / programs (range folder) / series
          │  (ocd_article, per range; OcdCsvLoader.read_table)
          ▼
 OcdCatalogueService.list_articles()   ── Load Articles ───▶ articles (+ short-text labels)
 OcdArticleGenerator.currencies()                            currency list from ocd_price
          │
          ▼
 OcdArticleGenerator.describe(article) ── Inspect ─────────▶ properties, values, defaults, relations
          │
          ▼
 OcdArticleGenerator.generate(...)     ── Generate ────────▶ GenerationOutcome (SKUs + counters)
    OcdCsvLoader.load → OcdDataset → build_article_model → ConfigurationEngine.enumerate/finalize
    → CodeSchemeEncoder → PriceCalculator → ofml_varcode
          │
          ▼
 ocd_repository_obx.export_obx(...)    ── Export OBX ──────▶ .obx file (atomic) + read-back check
    GeneratedSku → ArticlePermutation/ArticlePrice → ArticleObxService.render → ObxValidationService.parse_obx
```

## 2. Components

| Layer | Module | Responsibility | Status |
|---|---|---|---|
| Schemas | `services/ocd_engine/schema_loader.py` | Parse `pdata.*.inp_descr`, defaults | existing, unchanged |
| CSV reader | `services/ocd_engine/csv_loader.py` — `OcdCsvLoader`, `OcdDataset`, `build_article_model` | Read tables by column name; build `ArticleModel` | existing; `read_table` added earlier in this work stream |
| Catalogue | `services/ocd_engine/catalogue.py` — `OcdCatalogueService`, `OcdProgram`, `OcdArticle`, `CatalogueScan`, `CatalogueError`, `find_db_dir`, `texts_by_number` | Discover manufacturer/program/series, list articles. `texts_by_number` (new here) is the shared label resolver for all OCD text tables | existing, extended |
| Engine | `relation_parser`, `relation_evaluator`, `configuration_engine`, `codescheme_engine`, `computed_property_engine`, `varcond_engine`, `pricing`, `obx_serialization` | Relations/conditions (3-valued), SKU enumeration, final number, price, `ofmlvarcode` | existing, **unchanged** — no second engine |
| Orchestration | **`services/ocd_engine/generator.py`** — `OcdArticleGenerator`, `PropertyRule`, `PropertyInfo`, `ValueInfo`, `RelationInfo`, `ArticleDescription`, `GeneratedSku`, `GenerationOutcome`, `GenerationError` | `describe`, `estimate`, `generate`, `currencies`; applies user rules; duplicate and invalid accounting; pricing | **new** |
| Export adapter | **`services/article_obx/ocd_repository_obx.py`** — `build_rows`, `export_obx`, `compare_with_reference`, `ObxExportError`, `ObxExportSummary`, `ReferenceComparison` | `GeneratedSku` → serializer rows; atomic write; read-back; reference diff | **new** |
| Serializer | `services/article_obx/article_obx_service.ArticleObxService` | XML rendering (same writer as the repository Article OBX) | existing; 3 additive, default-neutral hooks (see §5) |
| UI | `ui/pages/pcon_article_obx_generator_page.py` — `PconArticleObxGeneratorPage` | The six actions, background tasks, progress/cancel | rewired |

`services/ocd_engine` stays stdlib-only and imports no application module; the OBX serializer dependency sits in `services/article_obx`, not in the engine.

## 3. UI flow

| Control | Action | Backend | Plugin? |
|---|---|---|---|
| **Load Catalogue** | `_load_catalogue` | `OcdCatalogueService.scan` (progress per range folder) | no |
| Manufacturer → Program → Series | `_on_manufacturer_changed` / `_on_program_changed` / `_on_series_changed` | in-memory `CatalogueScan`; any upstream change clears loaded articles | no |
| **Load Articles** | `_load_articles` | `OcdCatalogueService.list_articles` + `OcdArticleGenerator.currencies()` (fills the *Currency* box) | no |
| Filter | `_populate_articles` | in-memory | no |
| **Inspect Properties** | `_inspect_properties` (first selected article) | `OcdArticleGenerator.describe` → table: key, label, default value, mode, fixed value, #choices, #relations (tooltip lists relation kind/name/text per property and per value; the article-level relations are in the status tooltip) | no |
| Mode / Fixed value | `_current_rules` → `PropertyRule` (*Vary*, *Fixed value*, *Default value*) | applied by `generator._apply_rules` | no |
| **Generate Valid SKUs** | `_generate` | `OcdArticleGenerator.generate(articles, rules, currency, price_date, max_configurations, reporter)`; results table, counters | no |
| **Export OBX** | `_export_obx` | `export_obx`; output path field / *Browse…* / file dialog if empty; overwrite confirmation | no |
| Compare with Reference OBX… | `_compare_reference` | `compare_with_reference` | no |
| Open Output Folder | `_open_output_folder` | `explorer` | no |

Removed/never reintroduced: connection status, heartbeat, job folder, *Check Connection*, *Install Plugin*, *Discard unsaved pCon.planner planning*. Verified by `test_page_has_no_plugin_connection_controls`, `test_page_module_reaches_the_plugin_package_only_to_launch_the_planner`, and the `no_plugin` fixture, which makes **any** construction of `PconPluginBridge` fail the test during the full workflow tests.

Inputs added for standalone pricing: **Currency** (editable; filled from the repository's price table, auto-selected when there is exactly one, otherwise generation asks for a choice) and **Price date** (defaults to today). Nothing about currency or date is hard-coded.

## 4. Generation semantics

`OcdArticleGenerator.generate`, per article, in order:

1. Build the model (`build_article_model`); apply rules (§4.1).
2. `ConfigurationEngine.enumerate` — values pruned by preconditions as the walk proceeds; hidden properties; early constraint pruning. Node budget `MAX_NODES = 5,000,000` (reported if reached).
3. Pinned property unassigned → **invalid** (§4.1). Otherwise `finalize` (full relation re-check, computed properties, constraints, `$VARCOND`). Failure → **invalid**, counted.
4. `CodeSchemeEncoder.encode` → final article. An article without a code scheme gets its base number as final number plus a warning.
5. **Duplicate SKUs**: a valid configuration whose final article number was already produced (in this run, across all selected articles) is dropped and counted in `duplicates`. First wins. (The repository permutation service keeps semantically distinct configurations that encode to the same number; the standalone generator removes them because an OBX line is identified by its final number — this is a deliberate difference.)
6. **Limit**: when the next valid unique SKU would exceed *Max SKUs*, generation stops, `truncated = True`, warning `Stopped at the limit of N SKU(s).` Exactly N SKUs is not flagged.
7. Price: `PriceCalculator.price(base, varconds, price_date, currency, factors)`. No base price → status `unpriced`, message from the calculator; such SKUs appear in the result table but are **not exported** (the serializer needs a price); the count is reported.

### 4.1 Rules

- *Fixed value*: restricts the property's (ArtBase-filtered) values to the chosen one; a value the article does not offer raises `GenerationError`.
- *Default value*: the `is_default` value; a property without one is varied and a warning is added (the UI disables the option for such properties).
- A rule for a property an article does not have is skipped with a warning (several articles can be selected).
- A pinned property that ends up with no valid value because a relation excludes it makes the configuration **invalid** rather than leaving the property blank. (Found by `test_fixed_and_default_rules_restrict_values_without_bypassing_relations`: the engine's documented "no valid value ⇒ left unassigned" behaviour would otherwise have produced SKU `CHAIR1 M ` for Metal + Large.)

## 5. OBX serialization

`export_obx` converts each priced `GeneratedSku` into the existing `ArticlePermutation` / `ArticlePrice` and calls `ArticleObxService(None).render(...)` (`ArticleObxService._render_xml`, the writer the repository Article OBX uses). Because OCD class names are not always `<SERIES>_OPT`, three **additive, default-neutral** fields/hooks were added to shared code:

| Change | Effect when unset |
|---|---|
| `ArticlePermutation.ofml_varcode: str = ""` | `_varcode` derives `Series_OPT.Name=Code` as before |
| `ArticlePermutation.series_id: str = ""` | the serializer's single `series_id` is used as before |
| `ArticleObxService.render(...)` public wrapper | none (`generate` is unchanged) |

Output properties:
- `ofmlvarcode` is the engine's verified `ofml_varcode` (per-class), written verbatim.
- `artNr type="final"` is the **predicted** number (default `final_article_mode="predicted"`; owner decision (1) in the OCD engine notes is still open), `artNr type="varcode"` is never written.
- Price is written as `itemPrice type="purchase"` with `priceDate` = the chosen date; `feature` elements come from the scope-`C` assignments; names in `_DEFAULT_EXCLUSIONS` are suppressed exactly as in the repository Article OBX.
- Atomic: written to `<name>.obx.tmp`, then `os.replace`; the temp file is removed on failure.
- Read-back: the file is parsed with `ObxValidationService.parse_obx`; every exported final number must be present and the line count must match, otherwise the summary has `problems` and the page shows it in red.

## 6. Error handling and cancellation

| Situation | Behaviour |
|---|---|
| No / missing repository root | `CatalogueError` → status line + critical dialog; *Load Catalogue* stays enabled |
| Folder without OCD data | listed under "skipped", not an error |
| Missing `ocd_article` / `ocd_property` / `ocd_propertyvalue` | `GenerationError` naming the files |
| Malformed numeric position / price number | `GenerationError("Malformed OCD data for article X …")` / `("Malformed price table …")`; the page recovers |
| Unknown article, rule value not offered, no currency chosen, no price date, limit ≤ 0 | `GenerationError` with a specific message |
| Relation parse/eval problems, unsupported syntax | engine diagnostics; non-INFO ones are listed as warnings under the results |
| Export problems (extension, unwritable target, read-back mismatch) | `ObxExportError` / summary `problems` |
| **Cancellation** | all long actions run in `ReportedTask` with the shared progress dialog. The engine calls `core.cancellation.checkpoint()` every 256 nodes; `OperationCancelled` propagates and the page shows the cancel message. **Partial results are not shown** after a cancel (the old plugin path returned them). |

## 7. Plugin independence

- Catalogue, articles, properties, enumeration, pricing and export use only: `services/ocd_engine/*`, `services/article_obx/ocd_repository_obx.py`, `ArticleObxService`, `ObxValidationService`.
- The page imports nothing from any pCon plugin, SDK or launcher module, and has no pCon button.
- `services/pcon_sdk_obx`, `tools/pcon_obx_plugin` and the launcher were removed (see the independence note above); they remain only in Git history.

## 8. Tests

| File | Covers |
|---|---|
| `tests/ocd_engine/ocd_repo_fixture.py` | synthetic repository (relation, price relation, two code schemes, duplicates, malformed article; no ArtBase rows) with hand-derived expectations |
| `tests/ocd_engine/test_ocd_generator.py` | describe, relation semantics, rules, duplicates, limit, cancellation, pricing/currency, malformed/missing data, descriptor column order; **real Dalby** (60 / 260 SKUs, varcode) and a **real pCon reference OBX** check — skipped when the data is absent |
| `tests/ocd_engine/test_ocd_price_lookup.py` | real layout-studio price rows (fixture) priced to pCon's 1856.00 GBP, key derivation, currency, validity date, no match, malformed data, keyed-base and extra-charge-only layouts, generator + export price identity, diagnostics; live parity over 67 pCon references (skipped without the data) |
| `tests/ocd_engine/test_ocd_repository_obx.py` | export content, per-row series, unpriced handling, extension/unwritable target, atomic write, reference compare |
| `tests/ocd_engine/test_ocd_catalogue.py` | discovery (existing) |
| `tests/test_pcon_sdk_obx_page.py` | workflow registration, no-plugin guarantees, catalogue cascade, complete standalone workflow, inspect/pin, duplicates/unpriced/limit/currency, error recovery, export dialogs, reference compare |

Results of the final runs are in [§9](#9-verification-record).

## 9. Verification record

Run on 2026-11-02 on the developer machine (real Herman Miller OCD repository and Dalby reference OBX files present):

| Command | Result |
|---|---|
| `python -m pytest tests/ocd_engine/test_ocd_generator.py tests/ocd_engine/test_ocd_repository_obx.py tests/test_pcon_sdk_obx_page.py tests/ocd_engine/test_ocd_catalogue.py -rs` | 66 passed, 0 skipped (the real-data tests ran) |
| focused set: `tests/ocd_engine`, the four `test_pcon_sdk_obx_*` files, `test_article_obx*.py`, `test_workflow_shell.py`, `test_workflow_layout_components.py`, `test_maintenance_snapshot_consistency.py` | 385 passed |
| `python -m pytest` (whole suite) | **4967 passed, 13 skipped, 22 subtests passed** in 263.9 s; the 13 skips were not itemized and none are in the files above |

The four UI failures recorded earlier as pre-existing baseline (`test_maintenance_source_lock[ArticlesPage]`, the `test_workflow_layout_components` glyph test, two `test_workflow_shell` articles tests) did not fail in this run; the working tree they were measured on contained uncommitted changes, so no claim is made about which change fixed them.

## 10. Known limitations

1. Only the preferred region folder (`ANY`, else alphabetical) per range is read ([REPOSITORY_DATA_MODEL.md](./REPOSITORY_DATA_MODEL.md) §6).
2. Price `rounding` table, value validity dates, multi-option encoding, reactions, scale/percent prices and discounts are not (fully) supported — see the engine document.
3. `ofmlvarcode` equivalence *scope C ⇔ configurable* is verified for Dalby and Lino only.
4. `artNr type="final"` is predicted, not resolved by pCon.
5. Cancellation discards partial results.
6. One `OcdArticleGenerator` (and a fully loaded dataset) is cached per program folder for the page's lifetime; very large ranges cost memory until the page is closed.
7. Real-data tests run only where `C:\HermanMillerOFMLSVN\…` and `C:\Users\siaoca\Downloads\Dalby_OBX_Files` exist.
8. **Price amounts depend on the repository copy.** The staging `ocd_price.csv` files are dated 1 July; pCon exports made in July–September priced 2–5 % higher (Lino and Bay Work Pod: the same price components as pCon, higher amounts; Nevi: higher amounts, components not compared). Prices are exact only where the repository and the pCon reference share a price list (Dalby, Layout Studio).
9. An article with no base row is priced as the sum of its matching extra-charge rows (verified against pCon for Layout Studio, 1,295/1,295). If the sum is zero it is reported as unpriced rather than as 0.00 (a choice, not something pCon was observed to do).
