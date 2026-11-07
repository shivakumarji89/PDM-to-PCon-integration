# Package Investigation — `p-bk_1.14.4_Installer.zip`

**Status:** CURRENT · **Date:** 2026-11-02 · **Scope:** what the supplied pCon package contains, how repository data is actually fetched in this project, and what that means for the standalone Article OBX Generator.

**Bottom line:** the package is a **binary installer for pCon.basket, not source code**. It contains no repository reader, no CSV/`inp_descr` handling and no catalogue-discovery logic that could be inspected, reused or ported. Nothing in the standalone reader was taken from it. The reader behaviour is reproduced from the OCD data on disk, the OCD specification already in the project, and the project's own engine (`services/ocd_engine`).

Conventions: **Verified** = read in a file or run against real data in this session. **Not verified** = could not be checked; stated, not assumed.

---

## 1. What the package actually contains

Extracted (zip only, nothing executed) to a temporary directory outside the project: `%TEMP%\pbk_investigation`. The installer and the extracted files were not modified.

```
p-bk_1.14.4_Installer.zip                 126,403,648 bytes
├── locations.ini                          84 bytes
├── pCon.basket_installer.exe              127,405,304 bytes   (PE executable, "MZ")
├── plugins/
│   └── ConceptOffice/
│       ├── plugin.xml                     4,593 bytes
│       └── bskprops.xml                   5,360 bytes
└── addfiles/                              (empty directory)
```

| File | What it is (Verified) | Relevance to repository reading |
|---|---|---|
| `pCon.basket_installer.exe` | Windows PE installer, ≈127 MB. A byte scan found **no** installer-framework signature (no NSIS, Inno Setup, MSI/WiX, 7z, zip or CAB marker) and **no** occurrence of `ocd_article`, `inp_descr`, `ocd_property`, `pdata`, `CodeScheme` or `manufacturer`. The payload is compressed/packed. Only 2 mentions of `EasternGraphics` and 1 of `OFML` exist in the readable bytes. | None provable. The payload cannot be inspected without running the installer, which was deliberately **not** done (untrusted binary, and it would install software). |
| `locations.ini` | One section, `[Commercial]`, key `Currencies=` (empty), comment "add currency iso shortcuts and separate them with ';'". | None. Basket currency configuration only. |
| `plugins/ConceptOffice/plugin.xml` | `<plugin id="plugin::scBuero1" type="obs">` with `<obsClient id="SWCWawi579kxncki0lm" autoAS="0"/>`; actions `plugin::scBuero1::LookupArticle`, `LookupArticleHistory`, `LookupPartsList`, `LookupText`, … limited to `<modules enabled="basket"/>`. ISO-8859-1. | None. It is an **ERP/"Warenwirtschaft" (merchandise-management) connector for Concept Office** that looks up articles in an external database. It does not read OCD repositories. |
| `plugins/ConceptOffice/bskprops.xml` | Basket item property definitions (`@TextOnOffer`, `@TextOnOrderConfirmation`, …) with `propName`/`valueName` per language and `storeAs path="BasketItem:SoftwareConcept"`. | None. Basket item properties, unrelated to OCD `ocd_property`. |
| `addfiles/` | Empty. | None. |

### What the package does **not** contain (all Verified by the listing above)

- No Python, C#, C++, Java or script source of any kind.
- No `ocd_*.csv` repository data and no `pdata.*.inp_descr` descriptors.
- No documentation or examples of the repository layout.
- No class, function or file that discovers manufacturer / program / series.

## 2. Consequences for the questions in the task

| Question | Answer from the package | Where the answer actually comes from |
|---|---|---|
| How does it discover manufacturer, program, series? | **Not determinable.** No readable code. | Project data: program = range folder, manufacturer/series = columns of `ocd_article` ([REPOSITORY_DATA_MODEL.md](./REPOSITORY_DATA_MODEL.md) §1–2), implemented in `services/ocd_engine/catalogue.py`. |
| How does it read repository data / locate and parse CSV? | **Not determinable.** | `services/ocd_engine/csv_loader.py` (`OcdCsvLoader`), verified on real data. |
| Semicolon-delimited? Headers? | Not from the package. | **Verified on real data:** semicolon-delimited, **no header row**; column names come from `pdata.ocd_<table>.inp_descr`. |
| Role of `pdata.*.inp_descr` | Not from the package. | **Verified:** tab-separated descriptor (`table`, `fields`, `field <n> <name> <type> … delim ;`); parsed by `services/ocd_engine/schema_loader.py`. |
| Table relationships | Not from the package. | `csv_loader.build_article_model` and the OCD specification (`docs/04_Reference/pCon/Specifications`). |
| Data types, empty values, encodings, missing files, malformed rows | Not from the package. | Implemented/verified in the project (§3.3). |
| Reusable implementation | **None.** | — |
| Behaviour to reproduce | Everything, from project data and specs. | — |
| Requires pCon / plugin / compiled DB | Nothing in this package. | See §4. |

## 3. How repository data is fetched and interpreted in this project (Verified)

### 3.1 Layout on disk

Configured root (`AppConfig.metatype_repository_root`, default `C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx`):

```
<root>/<program>/<region>/<version>/db/   ocd_*.csv + pdata.ocd_*.inp_descr (+ pdata.ebase, pdata.inp_descr)
```

Real data on this machine: 102 range folders; for example `dalby/` has regions `ANY`, `EURO`, `GBP`, `NOPRICE`, each `1/db`. `dalby/ANY/1/db/ocd_price.csv` has 3,918 lines = `EURO` (1,959) + `GBP` (1,959); `NOPRICE` has an empty price file. (Line counts only; row-level equality was not compared.)

### 3.2 Code that does the work today

| Concern | Code | Notes |
|---|---|---|
| Schemas | `services/ocd_engine/schema_loader.py` — `parse_descriptor`, `load_schemas`, `TableSchema`, `DEFAULT_SCHEMAS` | Columns bound **by name**; descriptor beats default; defaults cover 11 tables only (no `artshorttext`, `propertytext`, `propvaluetext`). |
| CSV reading | `services/ocd_engine/csv_loader.py` — `OcdCsvLoader.load`, `.read_table`, `_read`; `OcdDataset` (indexes) | `csv.reader`, delimiter from the descriptor, ISO-8859-1 (`latin-1`), short rows padded with `""`, numeric columns stripped. |
| Model building | `csv_loader.build_article_model` | OCD tables → `model.ArticleModel`. |
| Catalogue | `services/ocd_engine/catalogue.py` — `OcdCatalogueService.scan`, `.list_articles`, `find_db_dir`, `texts_by_number` | New in this work stream (uncommitted at session start; extended here). |
| Relations | `relation_parser.py`, `relation_evaluator.py` | Three-valued evaluation; OCD 2.15 relation types. |
| Enumeration | `configuration_engine.ConfigurationEngine.enumerate/finalize/generate` | Dependency-ordered DFS with pruning; limits; cancellation checkpoints. |
| Final number | `codescheme_engine.CodeSchemeEncoder` | Predefined and user-defined schemes. |
| Price | `pricing.PriceCalculator`, `PriceRow` | Decimal; B/X/D levels; requires currency and date. |
| `ofmlvarcode` | `obx_serialization.ofml_varcode` | Verified against 1,242 Dalby and 2,352 Lino pCon-resolved articles (existing parity tests). |
| OBX XML | `services/article_obx/article_obx_service.ArticleObxService` | The repository Article OBX writer; reused unchanged except two additive hooks (§5). |

### 3.3 Handling of types, empties, encodings, missing and malformed data (Verified by tests)

| Case | Behaviour | Test |
|---|---|---|
| Missing table file | Table absent from `dataset.tables`; `OcdCsvLoader.load` adds a `MISSING_TABLE` diagnostic for `article`, `property`, `propertyvalue`, `price`; `read_table` returns `[]`. `OcdArticleGenerator.dataset` raises `GenerationError` naming the missing `ocd_*` tables (price may be missing — see below). | `test_missing_folder_and_missing_tables_are_reported`, `test_missing_data_tables_are_reported` (page) |
| Missing price table | Not fatal for browsing or inspection. Generation cannot pick a currency automatically (`GenerationError: Choose a currency; the repository has no prices.`); if one is typed, every SKU is `unpriced` and excluded from the OBX with a warning. | Behaviour read from `OcdArticleGenerator.resolve_currency` / `_price_calculator`; the unpriced path is covered by `test_price_date_outside_validity_leaves_skus_unpriced` and `test_generation_reports_duplicates_and_unpriced_skus` (page). No test removes the price file itself. |
| Short rows | Padded with empty strings. | `test_ocd_loader.py` |
| Empty values | Kept as `""`; `rel_obj` of `""`/`0` means "no relation". | `csv_loader._relations` |
| Encoding | ISO-8859-1; non-ASCII reported once as an INFO diagnostic. | `test_non_ascii_text_is_decoded_as_latin1_and_reported_once` |
| Non-numeric value in a numeric position column (e.g. `pos_class = "x"`) | `build_article_model` raises `ValueError`; the generator converts it to `GenerationError("Malformed OCD data for article X: …")`. Other articles are unaffected. | `test_malformed_article_data_is_a_clear_error` |
| Malformed price number | `GenerationError("Malformed price table …")`. | `test_malformed_price_row_is_a_clear_error` |
| Unsupported syntax (interval values, unknown relation types) | Recorded as diagnostics, never guessed. | `test_model_builds_…` |

## 4. What requires pCon, a plugin, compiled databases or unavailable dependencies

| Item | Status |
|---|---|
| Reading `ocd_*.csv` and descriptors | **Nothing needed** — plain files, stdlib `csv`. |
| `pdata.ebase`, `pdata.inp_descr` (compiled database/index files next to the CSVs) | Present in real folders but **not read**; the CSVs are read directly and are complete (the `tables` column of `ocd_version.csv` lists all 22 tables). |
| pCon.planner / pCon.basket / the Plugin SDK | **Not needed** for catalogue, inspection, enumeration or export. Nothing in the Workbench touches pCon at runtime (the former *Launch pCon.planner* bridge was removed). |
| Region-specific folders (`EURO`, `GBP`, …) | Not read. See [REPOSITORY_DATA_MODEL.md](./REPOSITORY_DATA_MODEL.md) §6. |

## 5. Reuse versus reproduction

- **Reused from the package:** nothing (there is nothing reusable).
- **Reused from the project (unchanged):** `OcdCsvLoader`, `schema_loader`, `build_article_model`, `ConfigurationEngine`, relation parser/evaluator, `CodeSchemeEncoder`, `PriceCalculator`, `ofml_varcode`, `ArticleObxService` XML rendering, `ObxValidationService.parse_obx`.
- **Reproduced / newly written here:** `services/ocd_engine/generator.py` (orchestration), `services/article_obx/ocd_repository_obx.py` (adapter + export + read-back + reference compare), the page wiring.
- **Additive hooks in shared code** (default-neutral, existing callers unaffected): `ArticlePermutation.ofml_varcode` and `.series_id` (both default `""`), `ArticleObxService._varcode` uses `ofml_varcode` when set, `_render_xml` uses the per-row series when set, new public `ArticleObxService.render`.

## 6. Limitations

1. The installer payload is opaque; **nothing is claimed about how pCon.basket reads repositories.**
2. Only the repository folders and the OCD specification are evidence for the reader.
3. Region folders other than the preferred one are ignored (REPOSITORY_DATA_MODEL §6).
4. Behaviour of unsupported constructs (reactions, value-set restriction, scale/percent prices, discounts) is reported as diagnostics, not approximated — see `docs/02_Domain/OBX/OCD_Engine.md`.

---

# Addendum — `EGR-LocalTestBox.zip` (2026-11-02, pricing investigation)

Extracted (nothing executed, no installer run) into a scratch folder outside the project. 48 entries.

## Verified: what it contains
* `LocalTestBox.exe` / `LocalTestBox.dll` (.NET 8 WPF) + `.pdb`, `.deps.json`, `.runtimeconfig.json`, `.dll.config` (user settings: window size, selected profile, `AutoStart`, …) and ~30 .NET runtime assemblies.
* `docs/EGR-LocalTestBox_Manual.pdf` (EN) and `_Anleitung.pdf` (DE), `legal/` licence PDFs.
* **Purpose (manual):** a local launcher for the EasternGraphics EAIWS server plus pCon.box / pCon.basket online / pCon.update DataClient, used to *test OFML data for online platforms before publishing*. It registers OFML data through data profiles (`app.gf.data.profile`, `app.gf.data.profile.registration=…\test.profiles`, `app.basket.currencies=currencies`).
* No source, no OCD/OFML CSV, no repository reader, no price code. A byte scan of `LocalTestBox.dll` finds no occurrence of `price`, `currency`, `VarCond` or `ocd_` (ASCII or UTF-16).

## Verified: what it says about pricing (all of it)
* pCon.basket online "can be used to test extra charges in the OFML data" and checks price validity dates (manual §2 / DE text).
* "Item prices are not displayed" → cause named: incorrect or outdated **licences**.
* The basket currency list is configured by the property `app.basket.currencies`.

## Conclusion
EGR-LocalTestBox gives **no evidence about price-key construction, price types, level `B`, currency or date filtering, or OFML price-relation behaviour**. It is a launcher around a server whose price logic is not in the package. Nothing in the generator was changed on its authority. Pricing remains verified only against the repository CSVs, the OCD specification and pCon reference OBX files (see `REPOSITORY_DATA_MODEL.md` §5a). Running the EAIWS against the registered data (a possible future cross-check of prices) was **not done** and is unverified.
