# SyteLine export: legacy behavior inventory and implementation status

Reference: `PDMMaintenance/ExportThread.cs` (7,483 lines), `SytelineExport.cs`, `SytelineBOMExport.cs`,
`SytelineCSIExport.cs` (verified local copy `C:\Users\siaoca\Desktop\PDM\PDMMaintenance\`; the project targets
`net40`, i.e. .NET Framework). Python: `services/syteline_export/`, `ui/pages/syteline_export_page.py`.

## 1. What now exists

`services/syteline_export/pipeline/` is a **literal transliteration** of `ExportThread.execThread` and the
helpers it calls (see `PORTING_CONVENTIONS.md` there): one mixin per contiguous C# range
(P00 2096-2473 setup, P01 2475-2606, P02 2607-2875, P03 2876-3578, P04 3587-4191, P05 4192-5008,
P06 5009-5425, P07 5427-5748, P08 5749-6325, P09 6326-6779, P10 6780-7032, P11 7033-7483), plus
`helpers_fabric.py` (814-985, 1090-1557), `helpers_misc.py` (709-751, 1559-2095), `io_output.py`
(293-708, 752-812, 986-1088) and `bom_export.py` (all of `SytelineBOMExport.cs`). `run.py` composes them and
reproduces the `execThread` control flow. `job.py` wraps a run with validation, the site lock, staged output
and one explicit result status. `ui/pages/syteline_export_page.py` starts it on a worker thread.

Reachable from the UI: the **SyteLine tab** (`ExportSL8Data(syteline: true)`), after an explicit confirmation.
The `millerCAD` / `itemreport` / `formatCSI` branches inside `ExportThread` are ported and unit-tested but have
no UI entry (they are only reachable through the legacy queue or other tabs).

NOT ported: the **SyteLine CSI tab** (`SytelineCSIExport.cs`, 2,056 lines, CSV output - a different exporter
from `ExportThread`'s `formatCSI` branch), the **OFDA/CET tab** (`OFDAExport.cs`), the "Other" tab, the
legacy queue/scheduler, and Excel COM output (replaced, see deviation D6). Their Export buttons stay disabled.

## 2. Verification status - read this before relying on the output

| Level | Status |
|---|---|
| Statement-for-statement equivalence to the C# | Independently reviewed by six reviewers (see section 4); confirmed defects fixed. Not proof. |
| Behaviour of each stage | ~420 unit tests per stage with **synthetic** fixtures; expected values derived by reading the C#. |
| Stages working together | 6 end-to-end scenarios on a **synthetic** scripted database (`tests/test_syteline_pipeline_end_to_end.py`). |
| Equality with **genuine legacy output** | **NOT VERIFIED.** The only genuine legacy outputs available are the header-only files in `Desktop\temp`. No populated legacy item/material/BOM file or real database result set was available, and no database was queried. |
| SQL against the real schema | **NOT VERIFIED** (no database access; SQL is the legacy text with bound parameters). |
| Driver value types (pyodbc vs SqlClient) | **NOT VERIFIED**; see blocker B2. |

## 3. Intentional deviations from legacy (register)

Each: observed legacy -> port -> why -> impact -> protecting test.

| # | Legacy | Port | Why | Impact | Test |
|---|---|---|---|---|---|
| D1 | Increment entries matched by substring `IndexOf(token+"\|")` then `double.Parse(Replace(...))` (ExportThread.cs 3269/3316/3362): `XABC\|4` throws, `2ABC\|4` silently sums 24 | Entry belongs to a token only if it starts with `token\|`; a matching entry with a malformed amount still raises | Both outcomes are defects; no valid entry changes meaning | `test_syteline_pipeline_stage_p03.py::test_intentional_deviation_*`, `::test_increment_helpers_anchor_the_token`; `test_syteline_material_conversion.py` |
| D2 | SQL built by string concatenation (item codes with `'` break it) | All values bound as parameters; structure unchanged | Safety; legacy fails (SQL error) on such values, port succeeds | Strictly more inputs work; no output change for valid data | every stage test asserts bound params; `test_syteline_workflow_contracts.py` |
| D3 | Concurrent-extract guard disabled by `& 0u` (2233); lock always overwritten; released only if it was empty at start | Job refuses to start when `Site.ExtractUser` is set (explicit take-over option clears it first); lock released only by the run that took it | The legacy message shows the intended rule; a stale lock needs a human decision | A second run on a site is blocked instead of silently interleaving | `test_syteline_job.py` (blocked, take-over, release) |
| D4 | Writes straight into the output folder; a crash leaves partial files, overwriting the previous export | Writes into a hidden staging folder; publishes only on success/completed-with-errors; discards on failure/cancel | Atomicity, previous output preserved | Output appears only after the run ends | `test_syteline_job.py` |
| D5 | Swallowed exceptions behind modal `MsgBox`/`debug_form` (blocks the worker thread, often ends "Export Complete") | Recorded in `run.errors`; any exception reaching the outer catch makes the run `failed` and publishes nothing; swallowed per-step errors give `completed_with_errors` | Non-blocking, truthful status | UI distinguishes success / errors / failed / cancelled / blocked | `test_syteline_pipeline_end_to_end.py`, `test_syteline_job.py`, `test_syteline_export_page_run.py` |
| D6 | Excel COM builds `<name>.xls` | openpyxl writes `<name>.xlsx` (same sheets/order, text-forced Materials column, control characters stripped, cells kept as strings) | No Excel dependency; xlsx content under `.xls` name warns in Excel | Downstream consumers of the `.xls` need the `.xlsx` (or text files, unchanged) | `test_syteline_pipeline_io_output.py` |
| D7 | `Environment.UserName`/culture-sensitive string ops | Windows account name; ordinal string comparison | Culture-sensitive .NET `IndexOf/StartsWith` only differ for ignorable Unicode characters | None expected | accepted, documented |
| D8 | `debug*` flags (all false) and developer-only paths (`dbacw8`, `C:\Downloads`) | Omitted | Never active in the shipped build | None | n/a |
| D9 | `double.ToString()` (15 digits, .NET Framework) | Reproduced (`.15g`, `E+nn` exponent) | Fidelity | n/a | `test_syteline_pipeline_review_fixes.py` |
| D10 | Effective date passed as `dd-MMM-yyyy` literal | Same format, bound parameter | Language-independent date parsing on SQL Server | none | `test_syteline_job.py` |
| D11 | Legacy dedupe/`Replace("")` throws `ArgumentException`; ported code mirrors the throw | Same (explicit guard) | Python would silently corrupt the text | n/a | review fix in P05 |
| D12 | Exclude-superproducts item query exposes parent status (existing `item_selection_query.py`, pre-existing) | unchanged | Needs product-owner sign-off (not part of the pipeline run path, which uses the transliterated query) | none for the pipeline | documented |
| D13 | Trade-net discount cache keyed by product code, errors silently zero the price | Ported literally; errors are also recorded as warnings | Legacy business rule unknown | prices could be silently 0 if the trade-net DB is unreachable | `test_syteline_pipeline_stage_p01.py` |

## 4. Fidelity review outcome (six independent read-only reviews)

Confirmed and fixed: operator-precedence bug at C# 4316 (`!a | b`), .NET Framework 15-digit `double`/`Decimal`
conversion, millerCAD `:f2` rounding, empty-`Replace` guard, `long.Parse` whitespace set, UTF-8 writer
substitution, pyodbc row-count results before a SELECT, XLSX control characters, 2100-parameter limit,
date literals, lock username. No other output-changing divergence was reported for P00-P11 or the helpers.
Reviewer claims that proved wrong were dropped (e.g. an over-applied 292/299/300 exclusion).

## 5. Remaining blockers (cannot be closed offline)

* **B1 Genuine reference output.** Needs known-good legacy `PDMExport_item/material/superprod/description_data`
  (and BOM sheet) for representative catalogues/items, produced by the real PDM against a **non-production**
  copy of the database (the exporter writes `Site.ExtractUser`). With it, add golden comparison tests.
* **B2 Driver type fidelity.** Legacy compares `FSCCompliant`, `IsSuperProduct` etc. through VB late binding
  on SqlClient types. If a column is `bit`, SqlClient returns Boolean and `True = 1` is false in VB (ported
  literally: the `#` suffix is then never added); pyodbc must return the same Python type. Verify column types.
* **B3 Real-schema SQL check.** Run the pipeline read-only against the **PDM Test** database copy.
* **B4 Unported exporters.** CSI (`SytelineCSIExport`), OFDA/CET, queue/scheduler.
* **B5 Trade-net contract UI** is disabled in the page (legacy Contract combo not wired), so `send_contract`
  and `send_tradenet` stay empty.
* **B6 Output extension.** Downstream expectations of `.xls` vs `.xlsx` (D6).

---
# Appendix: pre-implementation reviewer inventories (historical, line-referenced)
Parts A-E were written before the port existed; statements about Python parity inside them are historical.
Part A = lines 1-2095, B = 2096-3605, C = 3600-5110, D = 5110-6353, E = 6330-7483.

# Part A


Source: C:\Users\siaoca\Desktop\PDM\PDMMaintenance\ExportThread.cs (read fully, 1-2095; `execThread` starts at 2096, out of scope).
Ports compared (all in C:\01 Projects\mk_product_workbench\services\syteline_export\): legacy_output.py (LO), auxiliary_output_service.py (AUX), material_conversion.py (MC), item_record_formatter.py (IRF). Status: IMPL / PARTIAL / MISSING / DIFFERS.
General legacy pattern: nearly every method wraps its body in try/catch that calls `Interaction.MsgBox(ex)` (modal UI, swallowed; method returns a default). In a headless Python port this must become raise/log.

## 1. Fields / ctor / initThread / abort / clearArrays

| Item | Lines | Behavior | Python |
|---|---|---|---|
| Fields | 25-197 | ~100 private fields: option flags, 7 temp-file paths, ~20 parallel ArrayLists (_convertedList, _convertedDesc, _convertedOtherDesc, _convertIsFab, _convertIsDepOpt, _convertHasSuperParent, _convertFeaturePos, _convertStatus, _convertFeatLen, _convertOptionId, _convertChildFeatLen), caches (_SPFeatureItems/_SPFeatureCount, cachedItemOptFeatKeys/Lens, asiaUniveralScreenRoots), fabric colour state (allFabricColours/Sequences, allSPFabricColours*, materialstr, preConv, ConvCount). Events UpdateStatusLabel / UpdateExportTimer (199-201). | PARTIAL: MC `ConvertedMaterial` + `LegacyMaterialConversionRegistry` model the convert* arrays as records; fabric-colour state (allFabricColours etc.), SP feature cache, asia roots not modelled. |
| ctor defaults | 203-291 | `_numFeatureSlots=20`, `_site="uk"`, `_currency="GBP"`, `_length5Feats=true`, `_exportBasePrices=true`, `_maxDescriptionLength=200`, `_exportMaterialsForPDMReport=true`, `_exportSPComponentMaterials=true`, `_prevConvertFeatLen=-1`, ids -1, `_exportDirectory` = exe dir + "Export\\" (208). `materialsWritten=null` (288: getParentStartPos NRE if not set). | PARTIAL: defaults partly mirrored in config.py (UNVERIFIED, not read). MC registry defaults previous_feature_length=2, legacy uses -1 (230) -> DIFFERS (see addMaterialToItemTab). |
| initThread | 387-430 | Calls clearArrays then copies 35 params. `_maxDescriptionLength=40` if millerCAD (421-424), else 200 stays. Does NOT reset `_abortThread`, `materialstr`, `preConv`, `ConvCount`, `_prevConvertFeatLen`, `cachedItemOptFeatKeys/Lens`, `_SPFeatureItems/Count`, `asiaUniveralScreenRoots`, `bocfab*` (clearArrays 357-385 omits them) -> stale state on reuse of a thread instance (legacy defect, UNVERIFIED whether instance is reused). | MISSING as a unit; config.py builds params (formatCSI flag at config.py:166). 40-char description cap for millerCAD: MISSING in IRF (description not truncated). |
| abortThread | 432-435 | Sets `_abortThread = true`; cooperative flag, only consulted in execThread (outside range, UNVERIFIED). No lock/volatile. | MISSING in ported files (no cancellation hook). |
| clearArrays | 357-385 | Re-news convert*, items written, price/product code lists, fabric colour lists, sequenceForItems*. | PARTIAL: registry is per-instance. |

## 2. allocateFiles (437-466)
- millerCAD: item=`<dir>b-<site lower><currency>.asc`, material=`<dir>o-...asc`; if `_exportFileName != "b-<site><cur>"` appends `_` + name with that prefix removed and TrimStart('_') (441-447). No directory creation, other 5 paths untouched, returns.
- else: `_csi` suffix if `_formatCSI`; creates `<dir>temp\` (455-458); 7 files `<name>_<kind>_data[_csi].txt` (459-465).
- Side effect: Directory.CreateDirectory only.
- Python LO `allocate_legacy_output_paths` (35-67): IMPL for naming. Differs: no mkdir (by design); Python `str.replace(default_name,"")` replaces all occurrences, same as C# Replace. Note legacy site lower-cased but currency NOT lower-cased; Python same. `.lstrip("_")` == TrimStart('_'). IMPL.

## 3. removeNonStandardCharacters (293-331) / writeToStream (333-355)
- Allow-list `0-9a-zA-Z-+=_!"£$%^&*()[]<>,./?#~{}:;@'`|\ ` + space, plus \r \n \t; all else (incl. non-ASCII, e.g. en dash, accented letters, `–` used in formatCSI line 1842) dropped silently. O(n^2) string concat. Exception -> MsgBox, returns partial.
- writeToStream: strip, then `Replace("\r\n\r\n","\r\n")` (single pass: 4 consecutive CRLF become 2), debug mode wraps in `<ctx>...</ctx>` tags (339-341, `SytelineExport.debugDuplicateLines`). Exceptions swallowed.
- Python LO `remove_legacy_nonstandard_characters` (70-76): IMPL (same allow-list incl. £; single-pass replace). Debug wrapper MISSING (fine). NOTE: `£` in Python str is U+00A3; C# source encoding of that literal UNVERIFIED (file may be cp1252). Also removal of non-ASCII drops `–` from the CSI literal "Lot – Lot Number" (1842) -> output becomes "Lot  Lot Number" (double space): legacy defect/quirk, port must reproduce.

## 4. writeData (752-787) dedupe
- If data starts with "9-F": key = text before first `\t`; `mydata.IndexOf("\t")` returns -1 for tab-less data -> Substring(0,-1) throws -> swallowed + MsgBox, record NOT written (defect). If key in `_materialsOnItemTab` -> return (skip); else add. (Applies to items too, not just materials.)
- If isItem: whole-line dedupe via `_itemsWritten.Contains(mydata)` (ArrayList, O(n) per lookup = O(n^2)); skip dupes.
- If contains "BOCFAB-OF" AND "2-HAR": `Replace("-BOCFAB-","-")` (773-776).
- Then `Replace("HAR-F","H-F")` (777), writeToStream, `Flush()` per record (slow).
- Dedupe sets are shared between writes (the 9-F check uses `_materialsOnItemTab`, same list addMaterialToItemTab consults at 882).
- Python LO `LegacyRecordDeduplicator.accept` + `normalize_legacy_record`: IMPL. Differences: (a) Python `data.split("\t",1)[0]` for tab-less 9-F lines accepts the whole line as key whereas legacy throws and drops the record -> DIFFERS (edge). (b) Python normalize applies HAR-F replace then char filter; legacy filter happens inside writeToStream after replacements: same net order. (c) Dedupe of 9-F uses a set: same semantics. (d) Python dedupes by pre-normalization string, same as legacy (dedupe before replace). IMPL.

## 5. logMessage (789-812)
Public static. Writes `[timestamp] msg` to hard-coded `C:\Downloads\log.txt` only if `SytelineExport.logOutput` AND `Environment.UserName.ToLower()=="dbacw8"`. Developer-only debug; note `&` (non-short-circuit) used. Opening a StreamWriter per call. Python: MISSING / not needed (recommend drop). Defect: hard-coded user + path.

## 6. WriteToSheetSlow / WriteToSheet / ConvertToXLS (468-707)
- WriteToSheetSlow (468-485): per-cell write with status label; unused in range (UNVERIFIED callers). `Split('\t')`, strips `\r`.
- WriteToSheet (487-521): no-op on empty. Column count taken from FIRST line only (`dataLines[0].Split('\t').Length`); longer later rows silently truncated (`Math.Min`, 503); shorter rows leave null cells. For context "Materials", column index 3 (4th column) prefixed with `'` to force text (506-509) — also applied to the header row (i=0) and to trailing empty line produced by `Split('\n')`. Bulk Range.Value assignment. Note array sized `[num-1+1, num2-1+1]` fine.
- ConvertToXLS (523-707): Excel COM via CLSID 00024500..., Visible=false, DisplayAlerts=false, SheetsInNewWorkbook=1. Reads `_itemFile` and `_materialFile` with ReadToEnd (StreamReader reassigned at 540 without closing first -> first handle leaked until GC; defect). Branches:
  - `_syteline && !_formatCSI`: sheets Descriptions (descriptionFile), Planning Data (planningFile), SPextract (superprodFile).
  - `_syteline && _formatCSI`: no extra sheets.
  - else (non-syteline, i.e. millerCAD/other): SPextract, ProductCode, PriceFormula.
  - Always Materials then Items (`Split('\n')` of whole text; trailing blank/`\r` remain -> a final row with one empty cell and `\r` kept in last column since only `\n` split; \r not stripped in fast path). Items sheet added last, AutoFit on columns, selects A1, deletes "Sheet1", `FileSystem.Kill` existing `<dir><name>.xls` (607-611) then SaveAs (default format = .xls via extension, `.xls` extension on Excel>=2007 saves per default FileFormat; UNVERIFIED).
  - Cleanup in finally: ReleaseComObject for each sheet; `worksheet`/`worksheet2` released without null check (627,638) -> ArgumentNullException swallowed if earlier failure; `obj` Quit/Release not guarded (701-702) -> NRE masks original error if CreateInstance failed.
  - Any error -> MsgBox only; caller gets no failure signal (swallowed).
  - Sheet order quirk: Excel adds sheets before the active; final order is Items, Materials, then others reversed.
  - Excel cell-value coercion: numerics like "00123" or dates in item data become numbers/dates except Materials col 4 (defect risk).
- Python: MISSING (no XLS/Excel conversion in the four files; `.xls` not generated; UNVERIFIED whether another module does it — grep for xls found none in services/).

## 7. getFeatureCount (709-750)
SQL by string concat: `Item.Item = '<superproduct>'` (723) — injection / apostrophe breaks. Query: max count of `|` in `ItemComponents.FeaturePositionString` for the item. Caches in `_SPFeatureItems/_SPFeatureCount`. Null/empty -> 0. Failure -> MsgBox, returns 0 (cached? no: cache write is inside try after reader; on exception not cached). Python: MISSING.

## 8. updateChildFeatureLengthForMaterialOnItemTab (814-861)
Finds `myitem` in `_convertedList`; sets `_convertChildFeatLen[i]` = 2 default; if `myfeature` contains "-": take text after first "-", strip through "}" if present, `int.Parse` (throws on non-numeric -> swallowed MsgBox, so child length remains -1). If not found: MsgBox listing entire `_convertedList` (modal UI in export loop, defect). Parameter `verbose` unused. Note `myfeature` mutated inside loop but loop breaks after first match. Python: MISSING (MC has `child_feature_length=-1` field only; no setter).

## 9. addMaterialToItemTab (863-947)
Inputs: material, description, otherdescription, status, dependentoption, issuper, feature, info, featlen, childoptIds, stage.
- logMessage; `childoptIds[0]` -> option id (throws ArgumentOutOfRange if empty -> swallowed MsgBox, material silently NOT added; Python raises ValueError -> differs in being loud, acceptable).
- `#` in material -> isFab flag; `#` stripped (877-881).
- Skip if material already in `_materialsOnItemTab` OR `_convertedList` (882).
- Description prefix `text2` = text after last "-"; override "5-5"/"5-6" if EndsWith; `9-FAB-5-5*`/`9-FAB-5-6*` StartsWith -> strip "9-FAB-" (889-903; note EndsWith checks precede, so the StartsWith branch is reachable only when not ending in 5-5/5-6); MRFN/9-MRFN containing "-AJ-" -> "AJ" (908-911).
- `_convertedDesc` = `prefix|description`; `_convertedOtherDesc` = "" if other trimmed empty else `prefix|other`.
- featlen == -1 -> `_prevConvertFeatLen` (initially -1, 230). `_convertChildFeatLen` = -1.
- Debug MsgBoxes under `debugItemsAndOptionsVerbose`.
- Python MC `LegacyMaterialConversionRegistry.add` (154-206): IMPL for dedupe, prefix rules, other-description, `#`->fabric. DIFFERS: (a) `previous_feature_length` default 2 vs legacy -1; and Python's `_previous_feature_length` is never updated (legacy updates `_prevConvertFeatLen` in addFabricColour 1521) -> PARTIAL. (b) `_description_key` Python stores key and description separately instead of `key|description` strings (equivalent if serialised later; UNVERIFIED). (c) `info`/`stage` params not carried (logging only). (d) The registry `_seen` dedupe uses normalized names; legacy compares normalized material to both lists too -> same.

## 10. isInteger (949-984)
Accepts non-empty strings of chars from "0123456789-" (so "-", "1-2", "--" count as integers; later `int.Parse` would throw). Python: MISSING (no helper; used by getParentStartPos only).

## 11. writePriceFormulaData (986-1036)
- Opens `StreamWriter(_priceformulaFile, append:false)` BEFORE the try (989) -> creation failure unhandled (crash). Creates new SqlConnection then overwrites.
- Header: `Site\tCustPriceCode\tItemPriceCode\tPriceFormula\tPriceFactor\tEffectiveDate\r\n`.
- If `_priceCodes.Count>0`: SQL with string concat of `_priceCodes[i]` into OR chain `pm.ItemPriceCode = '...'` (1006) (SQL injection / apostrophe); `WHERE Site.SiteId = <siteId>`; `ORDER BY pm.CustPriceCode, pf.EffectiveDate DESC`; `FirstPrice` written as PriceFactor; EffDate = `CONVERT(VARCHAR(11), EffectiveDate, 106)` ("dd Mon yyyy"). Rows `\t`-joined, no quoting/sanitizing (tabs/newlines in values corrupt TSV; not passed through removeNonStandardCharacters). Null values -> `DBNull.ToString()` = "".
- With empty `_priceCodes`: header only. Double `streamWriter.Close()` ok.
- Python AUX `price_formula_rows` / `write_price_formula` (45-61, 134-135): IMPL (parameterized, same SELECT/ORDER BY/header). Differences: Python dedupes + strips codes (`dict.fromkeys`, strip) -> legacy does not (DIFFERS benignly); no `NOLOCK`-difference; atomic temp-file replace; encoding utf-8 (legacy StreamWriter default UTF-8 no BOM, same). Python does not apply the char allow-list to rows (matches legacy, which writes directly). `_priceCodes` source (populated in execThread) UNVERIFIED/MISSING. Python raises ValueError for site_id<1; legacy would emit `SiteId = -1` and write header only.

## 12. writeProductCodeData (1038-1088)
- Same structure. Header has 5 columns (`...PriceCode\tUnitCode`) but rows write only 4 values (Site, Product_Code, Description, PriceCode) -> UnitCode column always absent (legacy defect, ragged TSV). SQL concat `pc.Product_Code = '<code>'` (1058). `ORDER BY pc.Product_Code`.
- Python AUX `product_code_rows`/`write_product_codes` (63-77, 137-140): IMPL incl. ragged shape preserved (comment 138-139). Same benign DIFFERS (dedupe/strip, ValueError site<1). Note: `_write_tsv` joins `row` tuple as-is: 4 values (OK).

## 13. getTranslation (1090-1121)
Inputs: parallel lists optvaldescs / optvaldescIds / optvaldesctrans / optvaldesctransIds, index. Result = `optvaldescs[index]` if in range else ""; if `index < optvaldescIds.Count`: look up id via `optvaldesctransIds.IndexOf(id)` (boxed int equality; ArrayList IndexOf uses Equals: int vs int OK, but int vs long/string mismatch fails silently); if found and translated text non-empty -> use it. Empty translation falls back to base. Exceptions (e.g., `ToInteger(null)`, null desc `.ToString()`) -> MsgBox, returns partial result. Python: MISSING.

## 14. getItemSequence (1123-1197)
Per parent item keeps list of order codes and parallel list of sequence indexes. First time item seen: sequence 2 for the first order code. Known item+known order code: returns stored sequence. Known item+new order code: appends code, new sequence = (count of indexes) + 2, i.e. 3,4,... Uses late-bound VB calls (slow, ByRef copy-back). State in `sequenceForItems*` (cleared in clearArrays). Item compare via `IndexOf` (case-sensitive ordinal; ArrayList Equals). Exception -> MsgBox, returns 2.
Python MC `LegacyDependencyMaterialSequencer.next_sequence` (500-509): DIFFERS/PARTIAL. It implements a different rule (per 9- material: seq = last+1, starting at 2, every call increments) tied to stage 16.5, and explicitly rejects non-9- materials. Legacy `getItemSequence` is keyed by (parentItem, orderCode) and is idempotent per pair (repeat call returns same number). Python increments on every call -> would produce different numbers for repeated order codes. Whether stage 16.5 in execThread (outside lines read) uses a different inline counter is UNVERIFIED. `getItemSequence` itself: MISSING.

## 15. GetKnollFabricOrderCode (1199-1282)
- SQL string-concat of ints only (safe from injection since ints). Joins OptionValue with DependentOptionValues; `colour=false` -> filter on fabric-type value (optval_FT) and takes first row (breaks); `colour=true` -> filter on colour value, last row wins (loop continues; `FT_code/FC_code` overwritten) -> nondeterministic w/o ORDER BY.
- Only if both FT and FC non-empty: switch on FT code. Group 1 ("DR#","CRO#","FED#","H0#","PE#","TEX#","WE#","ALP#","CP#","CI#","CUR#","ESO#","EX#","IS#","T#","VI#","D#","FI#","H#","HL#","MOO#","TOS#","AN#","COL#"): result = `" "` (single space) when !colour, else FC code unchanged. "EVA#": !colour -> "1"; colour -> FC.Substring(1) (throws if empty; guarded non-empty). "HER#": !colour -> " "; colour -> FC.Substring(1). default: if colour: remove from FC the FT code with replacements VOX->VO, ADY->AD, VPY->VP, AUY->AU, "0Y"->"0", then "#" removed (1261-1264); if !colour returns originalCode unchanged.
- Opens a new DB connection per call (no pooling reuse in loop of addFabricColour -> chatty). Failure -> MsgBox, returns original code. No SQL parameterisation needed. Python: MISSING (hard-coded ID/code lists, requires DB).

## 16. addFabricColour (1284-1557)
Purpose: for a fabric-type option value, enumerate fabric colour option values (IsFabric=2) and emit material lines + item-tab materials.
- Strips `{DEBUG..}` token from `converted` (1293-1298; `IndexOf("}")` on substring ok).
- Parses length digits: finds "-05#","-04#","-03#" else "-02#"; reads 2 chars immediately before marker via `int.Parse(Substring(idx-2,2))` then `+5/+4/+3/+2` -> `text4` zero-padded 2 digits (1301-1322). If none of the markers exist `IndexOf("-02#")=-1` -> Substring(-3) throws -> swallowed MsgBox, nothing added (crash on malformed `converted`). Single-digit/non-numeric prefix likewise throws.
- `text5` = text after last "-" of `converted`; "-5-5"/"-5-6" suffix overrides (1324-1332).
- SQL (1333-1397): string concat of `text5` (with replacements ALP->AL, VOX->VO, ADY->AD, VPY->VP, 0Y->0) into `LIKE '<text5>%'` -> injection/apostrophe risk (values come from DB order codes). Parent restricted to `fabrictypeoptvalId`, with hard-coded CRB aliases: parent 278577 when fabrictype 276392 (ZB3#), 278576 when 276673 (ZNC#) (1333). `opt.IsFabric = 2`, `OrderCodeValue NOT LIKE '%#'`, `od.LanguageId = _languageId`, order by OptionId, DisplayOrdinal.
- Knoll catalogue (`SytelineCSIExport.IsKnollCatalogue(_catalogueId)`): adds `OR LIKE '%<text5 replaced>'` plus `opt.OptionId IN (8513,8525,8625)` and exclusion list ('1103AL','1107AL','1114AL','584TES','991TES') and per-prefix extra filters (CUR, CU, MOO, MO, ALP, AL, H0, H, VOX, ADY, VPY, AUY exclusion lists, 1347-1394). The paren-building via `") AND ..."` relies on balanced text; fragile.
- Fallback (1400-1414): if no rows, re-query WITHOUT dependent-option join (LEFT OUTER JOIN) and with `od.LanguageId = 1` hard-coded. Note: fallback `text6` appended only if Knoll; for non-Knoll it works; for Knoll `text6` content begins `OR ... ) AND ... NOT IN (...` and unbalanced pieces closed by following `")"` (works only by construction).
- Row loop: requires `optvals.Contains(OptionValueId)` (ArrayList of ints; selected option values). Takes only first option id encountered (`num2` -> subsequent different OptionId rows `continue`, 1426-1429).
- If `!ignorecolour`: colour code `text9`: Knoll options 8513/8525/8625 -> GetKnollFabricOrderCode(colour:true); else strip prefix chars by length: parent_code length 5 with "-05#" -> Substring(5), "-04#" & len5 -> Substring(4), ("-03#" or "-04#") & len4 -> Substring(3), else Substring(2) (only if code Length>2; no guard against Substring beyond length => e.g. length-3 code with Substring(5) throws; guarded only by len>2 check, UNVERIFIED data). Then `ConvCount` logic: same `converted` as previous call -> ++ else reset to 2 (1467-1475); `text8` feature length suffix "-05" default, "-04" for -03#/-04#, `!_length5Feats` and SLFeatureLength>2 -> `-0<len>` with cap 4 for -03#/-04# (1484-1492), "-05" if -05#. Appends line to `materialstr`: `converted \t F<pos> \t 9-FAB-<code> \t colour \t 0 \t 1 \t 0 \t ConvCount \t \t \t 10 \t` (1498) — 12 tab-fields; `debugFeaturePos(text4+text8,"AA")`. Updates allFabricColours / allFabricColourSequences (sequence overwritten with later count if material seen again; debugMaterialSequence markers).
- `_convertFeatLen` last entry fixed from -1 to parsed length (1517-1519); `_prevConvertFeatLen` updated (1521). NOTE: this block runs even when `ignorecolour` (text8 default "-05" -> 5) -> uses 5 when colour ignored (UNVERIFIED intent).
- Description: ShortDescription with `>` -> space; append ` (SupplierCode)` if non-empty. `addMaterialToItemTab(9-FAB-<code>, desc, "", Status, false,false,"", " [none]", len, {-1}, threadStage)`.
- Debug dialogs (`debguFabricColourAddition`) = modal ShowDialog from worker thread (UI interaction).
- Error: MsgBox with SQL text; connection closed; data reader not closed on exception (leak until GC).
- Python: MISSING (no SQL, no fabric colour enumerate; only `add()` bookkeeping + dedupe). High-risk gap: hard-coded option ids (8513/8525/8625, 276392/278577, 276673/278576) and exclusion lists are un-ported.

## 17. GetShortProductCode (1559-1628)
- Lazy-loads `asiaUniveralScreenRoots` (distinct root prefixes `SUBSTRING(Product, 1, CHARINDEX('.',Product))` for products using option ids 9277,9275,9313,9281,9279,9325,9285,9283,9327,9289,9287,9329). Cached for the thread lifetime. Empty result set re-queries every call (Count==0 check).
- If `rootproduct.StartsWith(prefix)` (first matching): code = `FRPD:` + ("B" if rootproduct ends with "B." else "S").
- Else if root starts with GHG/GHS: `FRGH:` + ("M" if root contains "M" else "D") (IndexOf("M") anywhere, including product name chars).
- Else: remove "-" from `prodcode`, truncate to 4 chars.
- Empty-string prefix in roots (product without '.', CHARINDEX=0 -> SUBSTRING(...,0)="") makes StartsWith("") true for everything -> FRPD for all products (UNVERIFIED data-dependent defect).
- Error -> MsgBox, returns prodcode as-is. Python: MISSING.

## 18. getParentStartPos (1630-1722)
Inputs: prefix, suffix, reverse, ref parentlength, ref substitutedoptcode; uses `materialsWritten` (null by default -> NRE swallowed, returns 1 without message beyond MsgBox).
- Iterates lines of `materialsWritten` forward or reverse (loop with sign-bit trick `(num6>>31)^i`).
- Line match: contains `"\t"+prefix`. Take substring from that tab; remove `{DEBUGAA/BB/CC/DD/EE/FF/II/ii}` tokens (case-sensitive; BB.. etc.).
- Attempt 1: if text contains `-<suffix>\t` -> truncate before it; if contains `]-F` take after it; if still contains "-": parentlength = int after "-" (if isInteger), result = int before "-" (if isInteger). Note isInteger accepts "-" chars so int.Parse can throw -> swallowed MsgBox. Attempt 2 (num7==2): if suffix in {ON,DE,ES,FI,ST,WH,LB,LE,PE} and line has "-AT\t" -> suffix = "AT", substitutedoptcode="AT" (mutates suffix permanently for all later lines/iterations, 1670-1674). BUT the do-while: attempt 1 `break`s when found; if not found, num7 becomes 2; attempt 2 re-evaluates with possibly substituted suffix; if flag false loop ends. Quirk: `if (flag) break;` unreachable meaning aside.
- `flag` stays true across lines but loop doesn't break outer for-loop on found (only inner do-while) -> later lines overwrite `result`/`parentlength` (last match wins for forward, first-in-file for reverse => reverse means "latest written line"). If outer loop doesn't stop, `reverse=false` returns the LAST matching line, reverse=true returns the FIRST in reverse iteration order only if no further earlier matches override… i.e. also continues to earlier lines and overwrites -> reverse effectively returns the earliest match (defect/quirk; UNVERIFIED intent). 
- Default result 1 when not found; debug dialog when not found and any debug flag.
- Python: MISSING (MC `build_legacy_dependency_material` covers dependency code only).

## 19. parseOptCode (1724-1742)
Removes all lowercase "m" and "c" characters from `optcode` (not just prefix: any 'm'/'c' anywhere, e.g. "cream" -> "ream" and also corrupts lowercase codes) — matches the prefix added by MC `_OPTION_VALUE_PREFIXES` (m/c) but strips ALL occurrences (defect). If optionId in {8512,8524,8624} -> GetKnollFabricOrderCode(colour:false). Python: PARTIAL: MC adds the m/c prefix (26-33, 57) but no removal (`parseOptCode`) and no Knoll translation. Missing.

## 20. formatCSIData (1744-1996)
- Builds a fixed-width row of ~230 literal columns for CSI item import; variable fields: col1 `myitem`, col2 `shortdesc`, col6 `myitem` again, col11 `UM`, col13 `Purchased` if PM=="P" else `Manufactured`, col14 productcode, weight (col 21; double -> `ToString()` culture-sensitive), commcode (col ~110), `template.Replace("X","&")` (col ~158), later PM again (1957-1964), literals incl. `Lot – Lot Number` (non-ASCII en dash dropped by char filter if routed through writeToStream/writeData; if written directly it stays). `issuper`, `statusflag`, `reasoncode`, `volume` params are UNUSED (statusflag/reasoncode/volume/issuper never inserted) -> all CSI items get "Active" regardless of status (1843).
- Output joined with `\t`, final `\r\n`. Exceptions -> MsgBox, returns "".
- Python: MISSING (IRF handles the non-CSI standard item row only; config.py has export_mode "csi" -> formatCSI=true flag but no formatter). Needs a column-by-column port (230 positions listed at lines 1752-1975).

## 21. GetProductDescription (1998-2029)
SQL concat `Item.Item = '<myitem>'` (injection/apostrophe). Selects attribute values whose ShortDescription matches `LIKE '% [[]%'` ordered by attribute DisplayOrder (DISTINCT). For each, extracts text between " [" and "]" and appends ` <text>` to shortdesc. `IndexOf("]")` -1 -> Substring(0,-1) throws -> swallowed (remaining rows skipped, partial desc returned). Language = `_languageId`. Python: MISSING (IRF accepts a pre-resolved `description`).

## 22. getFeatureLengthForItemOption (2031-2094)
Default 2. Cache key `item~optcodedesc`. Runs stored procedure `PDMOptionDataReport '<item>'` (string concat injection, 2055). `optcodedesc` may be `code|name`; matches first row with `ParentOptValCode == code` and (`ParentOptvalName == name` or name empty); then `SELECT SLFeatureLength FROM [Option] WHERE OptionId = n`; `int.Parse` (throws on NULL -> swallowed MsgBox, returns 2 and NOT cached). Caches result (incl. default 2 if not found). New connection per cache miss. Python: MISSING (MC `resolve_legacy_feature_length` ports a different stage-20 rule, not this procedure lookup).

## 23. Python modules: capabilities not tied to a line-range method
- IRF `format_syteline_item_record`: ports the standard item row (execThread section after 2096; UNVERIFIED against source here since execThread is outside the range). Not verifiable from this file range. Note: IRF does not truncate `description` to `_maxDescriptionLength` (200 / 40 millerCAD, set 270, 421-424 in this file) -> likely GAP (the truncation site is in execThread, UNVERIFIED).
- MC functions (`normalize_legacy_option_report_rows`, `order_legacy_option_report_rows`, `reconcile_legacy_option_child_ids`, `resolve_legacy_parent_material`, `assign_legacy_feature_positions`, `sum/normalize_legacy_increment*`) map to execThread (2096+); out of scope here, no status assigned.
- LO `write_header_only_outputs` (AUX 104-132): description and planning files written header only; consistent with a claim about execThread (outside range, UNVERIFIED).

## 24. Cross-cutting legacy defects (summary)
1. SQL built by string concatenation: lines 723, 1006, 1058, 1333-1411 (LIKE text5), 2005, 2055. Apostrophes in item codes or option codes break/injection.
2. `try/catch -> MsgBox` swallow everywhere (modal dialog from worker thread; no failure propagation): 326, 352, 619, 742, 784, 805, 857, 943, 978, 1027, 1079, 1117, 1193, 1274, 1549, 1619, 1717, 1738, 1991, 2021, 2086.
3. Crash/swallow on malformed data: addFabricColour no marker (1318), `Substring(5)` on short code (1447), writeData tab-less 9-F (758), GetProductDescription missing "]" (2012), updateChildFeatureLength int.Parse (836), isInteger permits "-" (962), `childoptIds[0]` empty (871).
4. Resource handling: StreamWriter opened outside try (989, 1041); unclosed data readers on exception; StreamReader reassigned (540); worksheet release w/o null guard (627, 638); Excel instance quit unguarded (701).
5. Non-thread-safe `_abortThread` (159, 435); UI interaction from worker (debug_form.ShowDialog 1419, 1542, 1709; MsgBox).
6. Performance: O(n^2) ArrayList.Contains for dedupe (759, 767, 882); string concat in loops (293-320, 1979-1983); connection per call (1205, 1299, 1570, 2046).
7. Hard-coded magic IDs: option ids 8512/8524/8624, 8513/8525/8625, 9275-9329 list, parent value ids 276392/278577/276673/278576 and exclusion code lists; dev log path `C:\Downloads\log.txt` and user `dbacw8` (791-798).
8. Culture-sensitive `double.ToString()` for weight/num4 (1779, 1498) -> decimal comma on non-en locales (UNVERIFIED locale).
9. State not reset in initThread (see section 1).

## 25. Status roll-up
| Item | Status |
|---|---|
| allocateFiles | IMPL (LO) |
| removeNonStandardCharacters / writeToStream | IMPL (LO); debug wrapper not needed |
| writeData dedupe + HAR/BOCFAB replace | IMPL (LO), edge DIFFERS for tab-less 9-F |
| writePriceFormulaData | IMPL (AUX), parameterized, minor DIFFERS |
| writeProductCodeData | IMPL (AUX), ragged header preserved |
| addMaterialToItemTab | PARTIAL (MC), prev-length default/update differs |
| getItemSequence | MISSING (MC sequencer DIFFERS) |
| updateChildFeatureLengthForMaterialOnItemTab | MISSING |
| getTranslation | MISSING |
| GetKnollFabricOrderCode | MISSING |
| addFabricColour | MISSING |
| GetShortProductCode | MISSING |
| getParentStartPos / isInteger | MISSING |
| parseOptCode | PARTIAL (prefix only, no strip, no Knoll) |
| formatCSIData | MISSING |
| GetProductDescription | MISSING |
| getFeatureLengthForItemOption | MISSING |
| getFeatureCount | MISSING |
| WriteToSheet / ConvertToXLS | MISSING (no XLS writer in these four files) |
| logMessage | MISSING (intentionally droppable) |
| abortThread / cancellation | MISSING |
| initThread state reset / millerCAD 40-char cap | MISSING |


# Part B


Source: C:\Users\siaoca\Desktop\PDM\PDMMaintenance\ExportThread.cs (read in full 2096-3605; the range ends mid stage 17 at 3605, the requested "16.15b" ends at 3572).
Conventions: `_x` are fields set by initThread. Decompiled names: text=current SQL; arrayListNN are parallel arrays (names below inferred, UNVERIFIED where noted).
Parallel-array legend (per item, option-report rows): 45/48 = OptionValueId; 47 = OptionId; 49 = IsFabric; 50 = Option2 name; 51 = OptDescId; 52 = optval name (+"#" if fsccompliant); 53 = optvalDescId; 54 = SLFeatureLength; 55 = "<featureIdx>|<OrderCodeValue2 sans #>"; 56 = Status; 57 = ParentOptValId; 58 = ParentOptValCode; 59 = "parent unavailable" flag; 60 = OptChildCount; 61 = child option id lists; 62 = identity keys (dedupe).
Global (cross-item) arrays: 16 = catalogue option values (cov); 17 = catalogue option ids; 18 = active option values (Status=1); 19 = product~optval exclusions; 20 = item~optval exclusions; 21/22 = '#' fabric exclusion helpers; 27/28 = product-code discount cache; 29/30 = description cache (lang); 31/32 = description cache (other lang); 33/34 = feature-length cache; 43/44 = parent-item cache; 9/10/11 = per-parent-item materials/components already added; 14/15 = counter for "9-" materials; 12/13 = skipped-parent bookkeeping.

## Stage 0 (2096-2194): setup
- Capability: init state, open output files, write TSV headers.
- Sets threadStage="0", `_abortThread=false`, UI label "Thread Executing"; if `!_parent.processingQueue` resets/starts export timer (2105-2109). Calls `allocateFiles()` (2110, not in range).
- Test-opens `_itemFile` for write (truncates). On exception: MsgBox with path, stop timer, return (2113-2133). Note: file is truncated here; no cancel-safe handling.
- Builds `text2` = "\tFeat1..\tFeatN" for `_numFeatureSlots` (2136-2141). UNVERIFIED where used (outside range).
- If `!_millerCAD && !_formatCSI`: opens superprod, planning, description files; writes header rows with `writeToStream(..., "cccccc"/"dddddd")` (2145-2153). Planning file is closed immediately (2151). Headers: superprod 19 cols (Item..FP12); planning 22 cols; description 3 cols (Lang, Item, Description). The third arg ("cccccc"/"dddddd") is an UNVERIFIED mode token (see writeToStream, out of range).
- Initialises ~40 ArrayLists, `materialsWritten`, `_itemsWritten`, `_materialsOnItemTab`, `skippedFabricColours`, `sequenceForItems(+Indexes)`.
- Defects: streamWriter2/4 are never closed in this range on early return paths (2130-2133 returns before they are opened, OK, but later exceptions are in try/finally outside range; UNVERIFIED). Item file opened then closed in finally (2126-2129), so it is only a writability probe. Files opened with no try/finally for superprod/desc writers within this range.

## Stage 1 (2196-2223): connections
- Opens 5 SqlConnections via `ConnectionFactory.CreateNewConnection(autoOpen:true)`, re-opens if Closed. Status "Connecting to Database" then "Connection OK".
- Defects: no using/disposal visible in range; if the 3rd open throws, earlier ones leak (UNVERIFIED, catch outside range).

## Stage 2 (2224-2242): extract lock
- SQL (concatenated): `SELECT ExtractUser FROM Site WITH (NOLOCK) WHERE SiteId = <siteId>` (2225). Reads ExtractUser into text4.
- Concurrency guard is DISABLED: condition `((text4 != "") ? 1 : 0) & 0` is always 0 (2233). So the "X is currently extracting" MsgBox and return are dead code. Only-one-extract rule is not enforced.
- Stage 2 SQL (concatenated, side-effect WRITE): `UPDATE Site SET ExtractUser = '<Environment.UserName>' WHERE SiteId = <siteId>` (2240). No parameters; username is injected into SQL (UserName rarely contains quotes; low risk). Cleared elsewhere (UNVERIFIED, outside range).

## Stage 3 (2248-2269): catalogue option values (only if `_syteline`)
- Status "Initialising SL8 Export ..".
- SQL (concat catalogueId): `SELECT DISTINCT optval.OptionValueId, optval.OptionId FROM CatalogueOptionValues cov WITH (NOLOCK) INNER JOIN OptionValue optval ON cov.OptionValueId = optval.OptionValueId WHERE cov.CatalogueId = <id>` (2251).
- Output: arrayList16 (value ids), arrayList17 (distinct option ids).
- Business rule: if `SytelineCSIExport.IsKnollCatalogue(_catalogueId)`, remove OptionValueIds 284979, 286214, 286909 from the allowed list (2264-2269). Hardcoded ids. `ArrayList.Remove` removes only first occurrence (values are DISTINCT so fine).

## Stage 4 (2270-2278)
- SQL: `SELECT OptionValueId FROM OptionValue WITH (NOLOCK) WHERE Status = 1` -> arrayList18 (active option values). Used in stage 17 filter (3590).

## Stage 5 (2279-2329): product-level option exclusions
- SQL (concat catalogueId, no params): `SELECT cpoe.ProductId, optval.OptionValueId, optval.Name, optval.OrderCodeValue, optval_colours.OptionValueId AS colourId, ... FROM CatalogueProductOptionExclusions cpoe INNER JOIN OptionValue optval ... LEFT JOIN DependentOptionValues dov ON optval.OptionValueId = dov.OptionValueId AND optval.OrderCodeValue LIKE '%#' LEFT JOIN OptionValue optval_colours ON dov.AdditionalOptionValueId = optval_colours.OptionValueId WHERE cpoe.CatalogueId = <id> ORDER BY optval.OptionId, optval.DisplayOrdinal` (2282).
- Logic: for each row add "ProductId~OptionValueId" to arrayList19 (dedupe). If code ends with "#" add to arrayList21. If a fabric colour exists add "ProductId~colourId" too. Special pair rule: code "0Y#" while arrayList21 already contains "0#" (or vice versa) -> that colour key is recorded in arrayList22 (2312-2322). After the loop, all keys in arrayList22 are REMOVED from the exclusion list (2325-2329), i.e. colours shared by both 0# and 0Y# exclusions are un-excluded.
- Order dependence defect: the "0Y# and 0# both present" test uses the rows read so far (arrayList21 is filled incrementally), so a pair is only detected when the second code appears after the first; 0#-then-0Y# and 0Y#-then-0# are both handled but a colour first excluded by an earlier 0Y# row before 0# is seen is only caught on the later row of the colour (the colour row for 0Y# earlier is not added to 22). UNVERIFIED impact (2312-2322).
- Debug: `SytelineExport.debugExclusions` shows modal debug_form (2284-2289) - UI side effect, blocks thread.

## Stage 6 (2330-2338)
- SQL: `SELECT ItemId, OptionValueId FROM CatalogueItemOptionExclusions WHERE CatalogueId = <id>` -> arrayList20 "ItemId~OptionValueId". No NOLOCK.

## Stage 7 (2339-2349)
- SQL (concat, quoted): `SELECT CultureCode FROM Language WITH (NOLOCK) WHERE Language_Id = '<otherLanguageId>'` on connection 5 -> text3 (culture code). Used later (outside range; UNVERIFIED). The id is numeric but quoted.
- End of the `if (_syteline)` block (2349).

## Stage 8 (2350-2442): item selection query + load
- Capability: build and execute the item list SELECT; first pass collects LongItem list for progress denominators.
- SQL fully string-concatenated (ints via ToString; strings `_currency`, `_minItem`, `_maxItem`, `_itemList[k]`, `_effectiveDate` embedded without escaping: SQL injection / quote-break risk, e.g. item codes with apostrophes, 2353, 2368-2372, 2386).
- Columns: `SELECT DISTINCT Item.Item AS LongItem, Item.Notes, Item.LegacyItem, Height, Width, Depth, CASE WHEN len(Item.Item)>22 THEN substring(Item.Item,1,22) ELSE Item.Item END AS Item, Item.Status, FSCCompliant, WeightKilos, VolumeLitres, Product.Product, IsSuperProduct, ItemId, <ShortDescription CASE>, AltDescription, MyBasePrice (BasePriceRef 1/2/3 -> BasePrice/2/3)` (2350).
- ShortDescription: item_desc (OtherDescription join on `_languageId`) if non-empty, else pd.ShortDescription (substring to `_maxDescriptionLength`), else Item.Item. AltDescription from alt_desc ProductDescription with `_otherlanguageId`. (Note alt_desc is joined off pd.DescriptionId, so null when product has no description.)
- `ListPrice` column appended only if `_millerCAD || (_syteline && !_exportBasePrices)`: `dbo.fnGetListPriceByItem(Item.Item, '<currency>', '<effectiveDate>', <siteId>, NULL)` (2351-2354). Note it is passed the SHORT 22-char Item.Item, not LongItem, though Item here binds to the table column (the alias "Item" is not yet in scope): UNVERIFIED which is passed; in T-SQL `Item.Item` resolves to the table column (full length).
- FROM/JOIN: `Item WITH(NOLOCK) CROSS JOIN (SELECT NULL AS ProductCodeIdOverride) x INNER JOIN Product INNER JOIN ProductRange INNER JOIN Product_Code pc ON CASE WHEN (subselect ProductCodeIdOverride from Item i2) IS NOT NULL THEN ... ELSE Product.ProductCodeId END = pc.ProductCodeId LEFT JOIN ProductDescription pd (LanguageId=_languageId) LEFT JOIN OtherDescription item_desc (LanguageId=_languageId)`. Legacy oddity: ProductCodeIdOverride is a literal NULL via the CROSS JOIN x but the subselect reads `i2.ProductCodeIdOverride` from Item (2355). The override is effectively resolved per Item.
- `if (_syteline|_millerCAD|_itemreport)`: `INNER JOIN CatalogueItems`; `_millerCAD`: `INNER JOIN Catalogue`. Then `LEFT JOIN ProductDescription alt_desc ... LanguageId=_otherlanguageId`; `WHERE pc.SiteId = <siteId>`.
- Scope branches (exclusive if/else chain):
  - productCheck: `AND pc.ProductCodeId=<id> AND CatalogueItems.CatalogueId=<id>` (2368). NOTE: if not `_syteline/_millerCAD/_itemreport`, CatalogueItems is not joined -> invalid SQL (legacy defect, caller UNVERIFIED).
  - rangeCheck: if min=="BRW" && max=="BRW" special hardcoded list of 8 browning items (BREF.CL, BRWBTEENONN.AAM, BRWLEELDLEFHN.AAMM [listed twice], BRWUPMEELSBRSGN.AAMWM, BRWLEELDLEFHN.AAWM, BREUBLL., BREUBLR.); else `(Item.Item > min OR Item.Item LIKE 'min%') AND (Item.Item < max OR Item.Item LIKE 'max%')` (2372); then `AND CatalogueItems.CatalogueId=<id>` only if `_syteline` (2373-2376). Range with `LIKE` and no escaping of `%`/`_`.
  - listCheck: if `_itemList.Count>0` => `AND (Item.Item = 'a' OR ...)`; if list empty NO filter is added, i.e. whole site is selected (2378-2394, defect: empty list = unfiltered). No catalogue filter in list mode.
  - else `_syteline`: `AND CatalogueItems.CatalogueId=<id>`.
  - else `_millerCAD`: `_exportAllCataloguesInSite` ? `AND Catalogue.PrimarySiteId=<siteId>` : `AND CatalogueItems.CatalogueId=<id>`.
  - else `_itemreport`: if `_activeOnly` CatalogueItems filter; else replace the CatalogueItems inner join with LEFT JOINs of CatalogueItems and CatalogueItemsUnreleased and `AND (CI.CatalogueId=<id> OR CIU.CatalogueId=<id>)` (2403-2413).
- `_activeOnly`: `AND Product.Status = 1 AND Item.Status = 1` (2415-2418).
- UNION: base = text13. If `!_activeOnly`: `text13 UNION text13.Replace("CatalogueItems","CatalogueItemsUnreleased").Replace("Item.Status","0 AS Status")` (2420-2423). Textual replace also changes the `CatalogueItemsUnreleased` already in item-report LEFT JOIN text (double-replacement -> "CatalogueItemsUnreleasedUnreleased") - UNVERIFIED but likely breakage in item-report non-active mode. Replace also hits `Item.Status, Item.FSCCompliant` in the select list (intended).
- Second UNION when `_excludeSuperProducts && _activeOnly`: substitutes the CatalogueItems join with a join through ItemComponents -> sp_item (so a component sub-item is pulled in via its super parent), with textual Replace of `Item.Item ` -> `sp_item.Item ` and several corrections; appends `AND sp_item.Status = 1` AFTER `text13` has been unioned (2424-2430). Note appended after the whole UNION and before ORDER BY, so the final `AND sp_item.Status = 1` binds only to the last branch (correct since it's last).
- `ORDER BY Item.Item` (2431). Note after UNION, ORDER BY must reference an output column; works as alias `Item` exists (the 22-char-truncated column), so ordering is by short item (UNVERIFIED).
- Timeout 600s (2434). Pass 1 (2437-2442): fills arrayList23 with LongItem for progress "n of count". Query is EXECUTED TWICE (2437 and 2473), without a snapshot; item set could change between passes; the count includes items later skipped by super-product filters (progress counter is `num5` which counts skipped ones too? num5++ occurs before the skip check, 2476, so counts are consistent).
- Cancellation: loop condition `while (reader.Read() && !_abortThread)` (2474). Abort checked only once per item.

## Stage 8 loop per item (2474-2516): per-item filter and state reset
- Flag4 (`MK1*O` items): `Item` startswith "MK1" and endswith "O" -> treated as NOT super product for the superproduct exclusion and downstream (2478-2481). Hardcoded.
- Skip rules: `(IsSuperProduct && _excludeSuperProducts && !flag4) || (!IsSuperProduct && _superProductsOnly)` -> continue (2489).
- Progress: `UpdateStatusLabel(LongItem + "\r\n(n of N)")` (2493).
- For a new Product (different from previous `right`) and super product: `num3 = getFeatureCount(LongItem)` (2494-2497; helper outside range). Caches by product name only; if product differs but remains same name different range - UNVERIFIED.
- Captures height/width/depth, rootproduct, prodcode; `text6` = `"BOCFAB"` or `"BOCFAB[" + GetShortProductCode(prodcode, rootproduct) + "]"` when `!(catalogueId==229 || !flag3)` where flag3 is always true (line 2191, never changed in range): so non-229 catalogues use "BOCFAB[xx]" (2504). Hardcoded catalogue id 229.
- Per-item resets of arrays 3-7, 45, 46, `materialstr`, text19, num6, text20.

## Stage 9 (2517-2582): trade-net contract discount (if `_exportMaterialsForPDMReport && !_superProductsOnly`)
- Per product code cache (arrayList27/28). Cache miss: opens a NEW SqlConnection with a hard-coded Integrated Security connection string to `_tradeNet` database on `Global.connectedServer` (2548).
- SQL (concat): `SELECT DISTINCT Contract_ID, Product_Code, Purchase_Discount FROM dbo.Contract WITH (NOLOCK) WHERE Product_Code='<pc>' AND Contract_ID='<_contract>'` (2550).
- Rule: for each row, if Purchase_Discount != 0 OR != DBNull (the OrObject is effectively "NOT NULL OR not 0": always true when non-null, and compare of DBNull to 0 is UNVERIFIED), discount factor = 1 - disc/100; `num4` = IsDBNull(MyBasePrice) ? 0 : Round(MyBasePrice * factor, 2) (2556-2564). The result is cached BY PRODUCT CODE, but computed from the FIRST item's MyBasePrice: defect, later items of the same product code reuse another item's discounted price (2537-2540, 2580-2581). Math.Round default is banker's rounding.
- Errors: any exception -> num4=0 and Debug.WriteLine only; the zero is cached (2568-2575, 2580): tradenet outage silently zero-prices. Connection closed in finally.
- Result `num4` is consumed later (outside range; UNVERIFIED) as component cost.

## Stage 10 (2583-2806): option data report per item
- SQL (concat LongItem inside quotes; item code with apostrophe breaks): creates temp table `#temptable` (29 columns) via `INSERT INTO #temptable execute PDMOptionDataReport '<LongItem>'` (2583). Then optional (flattenFabrics) T-SQL cursor C1 over rows with `ParentOptValId IS NOT NULL AND IsFabric=2 AND OrderCodeValue2 NOT LIKE '%#'`, re-parenting each colour to the grandparent and setting IsFabric=1 (2584-2587).
- Final SELECT DISTINCT joins `OptionValue`, LEFT `DependentOptionValues`, LEFT `OptionValue child_optval`; computes OrderCodeValue2 with prefixes by ParentOptValId: m/c prefix for Worksurface (149730,195468 m; 194397,195469 c), Wooden Panel (197074,197077 m; 197075,197076 c), Shelf (197237,197329 m; 197238,197240 c); `OptChildCount` = 1 if name contains 'customers own' else `dbo.fnOptionChildCount(OptionValueId)`; `child_optval.OptionId AS OptChildId`, optval.fsccompliant, len(OrderCodeValue2) (2588).
- ORDER BY `Range2, Product2, DisplayOrder, len(OrderCodeValue2) DESC, DisplayOrdinal`; DROP TABLE #temptable (2589). For items starting "OF": `len(OrderCodeValue2)` -> `len(REPLACE(OrderCodeValue2,'9B','9B__'))` (2590-2593).
- Connection 2, CommandTimeout 900 (2605). Debug modal (2594-2599).
- SQL batch with `DROP TABLE` after SELECT in same batch; error mid-batch leaves temp table until connection closes.

### Stage 10.1 (2615-2619): flatten fabrics skip
- `if (!(!endsWith("#") | !_flattenFabrics)) continue;` -> if flattenFabrics and order code ends with '#', skip the row. FSC marker: text24 = optval_name + "#" if fsccompliant==1 (2611-2614, computed before skip).

### Stage 10.2 (2620-2623): availability filter and identity key
- Include row only if (`syteline`: optval in catalogue list (arr16) AND product~optval not excluded (arr19) AND item~optval not excluded (arr20)) OR `!_syteline` (2620). Else append to debug text22 (2795-2798) only (no effect on output).
- Dedupe key text25 = `OptionValueId|OptionId|IsFabric|OptDescId|optvalDescId|OrderCodeValue2|ParentOptValId|OptChildCount|` (2623). Rows with the same key but different OptChildId are merged by replacing `-2` with the real child id (10.6/10.9/10.14: 2678-2682, 2731-2735, 2788-2792). Rows sharing a key but arriving after... note the first-seen child list uses `-2` default or 8512 for "customers own".

### Stages 10.3-10.14 (2624-2794): feature-order assignment by catalogue/item
- `_catalogueId != 30` (2624): 
  - Item startswith "AE" (10.4-10.6, 2628-2685): add row only if OptionValueId not in {292, 299, 300} (2635); `text23` debug list always appended with code.
  - Other items (10.7-10.10, 2686-2737): all option values added (no 292/299/300 exclusion).
  - Both: `num7` increments when OptionId changes from previous (`num8`) = "feature position" per option. Entries pushed on arrays 47..61. `itemHasFabrics` (static) gets LongItem if IsFabric>0. `arrayList55` = `num7|code-without-#`.
  - Note the AE branch records `text23` (debug) BEFORE applying the 292/299/300 exclusion, so debug text lists excluded values.
- `_catalogueId == 30` (10.11-10.14, 2739-2793): only values not in {292,299,300} are taken; `text23` not updated.
- Hardcoded ids: 292, 299, 300 (option values), 8512 (customers-own child option), -2 sentinel.
- Defect: the "10.1 continue" bypasses stage-name resets; the stage string is left at 10.x.
- Defect: `Operators.CompareObjectNotEqual(OptionValueId, 292)` compares object; fine. `continue` (2684, 2737) inside both branches means everything after stage 10.14 inside the loop is dead for this iteration, correct.
- Dedupe weakness: key includes OptChildCount but not OptChildId so duplicates collapse by design.

## Stage 11 (2807-2826): primary-language descriptions
- Per distinct optvalDescId (arrayList53) not in cache arr30: SQL (concat) `SELECT SUBSTRING(ShortDescription,1,<maxDescLen>) AS ShortDescription FROM OtherDescription WITH (NOLOCK) WHERE DescriptionId = <id> AND LanguageId = <_languageId>` on connection 2 (2815). Concatenates all rows (text27 += ...), replaces `>` with space. Caches (arr29 text, arr30 id). Missing -> "" cached.
- Defect: loop `for l` checks arr30 only; duplicates inside arr53 within the same item are cached after the first (index check precedes the add), OK. Empty-string descriptions are cached; multi-row descriptions concatenated with no separator.

## Stage 12 (2827-2846)
- Same as 11 for `_otherlanguageId` into arr31/arr32. `SELECT SUBSTRING(...) as ShortDescription ...`. Executed even when `_otherlanguageId` equals primary or is 0. Note: caches arr29/30 are shared across items and never invalidated.

## Stage 13 (2847-2871): feature lengths
- For each OptionId in arr47: cache arr33/34 else SQL (concat) `SELECT SLFeatureLength FROM [Option] WITH (NOLOCK) WHERE OptionId = <id>`; default 2; `int.Parse(SLFeatureLength)` throws on NULL (no catch in range) (2864). Result list arr54 = lengths (per position). Note arr54 is appended to again each time (arr54 is declared per item at 2523, ok).
- Defect: NULL SLFeatureLength -> int.Parse("") FormatException aborting whole export (UNVERIFIED catch outside range).

## Stage 14-15 (2872-2981): incremental prices per option value
- For each option value (arr45[num19]) one query:
  - Standard (2883-2888): `SELECT DISTINCT Item.Item, CASE BasePriceRef 1/2/3 -> itov.IncrementalPrice/2/3 AS MyIncrementalPrice [, dbo.fnGetListPrice('<cur>', <incr>, pc.PriceCode, '<effdate>', 'DMY', pm.Rounding, <siteId>, NULL) AS IncList if millerCAD or (syteline && !exportBasePrices)] FROM ItemOptionValues itov ... INNER JOIN Item ... Product ... Product_Code pc (+ pc.SiteId=<siteId>) INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency='<cur>' WHERE OptionValueId = <v> AND Item.ItemId = <itemId>` (concatenated).
  - Super product (non MK1..O) (2889-2897): same but `subitem.Item` via ItemComponents (`itco.ItemId = <itemId>`, subitem = component).
  - Stage 14 executed (conn 2, timeout 600). Result entries added to `arrayList66` as `"<Item>|<amount>"` (list price `IncList` for millerCAD or syteline-with-list-price, else MyIncrementalPrice) only when the value string is non-empty; `double.Parse` culture-dependent (2912, 2919, 2924) - decimal comma locale risk. `double` used for money (precision).
  - Stage 14.1/14.2-15 fallback (2929-2981): if super product and no increment found and option is not fabric (IsFabric==0): searches increments by ORDER CODE rather than option value id: `WHERE optval.OptionValueId=<v>` or, when `_extendSPOpts`, `((optval.OrderCodeValue='<code>' AND subproduct.ProductRangeId <> 999) OR (optval.OptionValueId=<v> AND subproduct.ProductRangeId = 999))`, plus `AND Item.ItemId=<itemId>`; hardcoded range 999 for standard SP components. Order code is concatenated into SQL.
  - Note stage 15 query: `Item` in SELECT list is `subitem.Item`.
  - Unreferenced / dead: the `text8` debug variables (SytelineExport.debugIncrements) hold queries.
  - `sqlDataReader7` is reassigned at 2953 without closing earlier one (it was closed at 2927 so OK). If an exception occurs readers are left open (no try/finally here).
- Defect: one query PER option value PER item (N+1; slow).
- Defect: the first query is run with `text` re-concatenated each time; no parameters.

## Stage 16 (2982-3073): parent item resolution for super products
- Defaults `myparentitem` text30 = text31 = `Item` (short 22-char), flag5 unused.
- If super product and not MK1..O (2987): loops num20 = 1..2 (two passes): feature position `num21` = option id from arr47 (2993) except on pass 2 where option name == "access flap finish" -> hard-coded option id 1142 (2994-2997). Cache key `"<ItemId>~<optionId>"` (arr44/43).
  - Stage 16.1 SQL (concat): `SELECT sub_item.Item AS parentitem FROM ItemComponents itco INNER JOIN Item sub_item ON itco.SubItemId = sub_item.ItemId WHERE itco.ItemId = <itemId> AND (CHARINDEX(convert(varchar,<optId>)+'|', itco.FeaturePositionString)=1 OR CHARINDEX('|'+convert(varchar,<optId>)+'|', itco.FeaturePositionString)>0) ORDER BY itco.ComponentSequence` (3008). Result: `text32 = item1|item2|...|` (3016). Hmm: FeaturePositionString holds OPTION ids ("feature position" semantic is UNVERIFIED).
  - If found (flag6): `text30=text31=text32`; split on '|': index 0 (first component) becomes `text30` (primary parent); remaining become `arrayList67` entries `"<comp><<optionId>>"` and optionId added to arr26 (3035-3053). Break out of the do/while.
  - Cache is only populated if found (3021-3025); not-found is re-queried each time. Bug: `flag6` is not reset between the two passes and break exits, fine; but on pass 2 uses `num21` possibly 1142.
  - Defect: first element `array[0]` is skipped if empty -> `text30` stays as full pipe string if array[0]=="" (continue at 3039 without assignment). Edge.
- Stage 16.2-16.4 (3060-3117): parent availability for dependent options:
  - If ParentOptValId (arr57) non-empty: search arr63 (parent option value ids already processed in this item) for the parent; when found (flag7) and any of: parent's material (arr64[idx]) contains `text30`, OR option is fabric colour (IsFabric==2), OR option id in {9275, 9313, 9279, 9325, 9283, 9327, 9287, 9329}, OR (parent item starts "GHS"/"GHG" and option id in {8, 9487}) -> `text30 = arr64[idx]` (the parent's material) (3085-3092). Hardcoded ids list. Then every arr67 entry whose short name is contained in arr64[idx] is replaced with arr64[idx] (3093-3106; note it iterates ALL matches of parent id).
  - If `!text30.StartsWith("9-")`, mark option as "unavailable" (arr59[num19]=true) (3108-3111), meaning no resolvable parent -> later non-super items skip. Note this occurs whether or not the parent was found (flag7 false also marks unavailable).
  - Defect: arr59 for numeric overload: `int.Parse(arrayList57[num19])` throws for non-numeric.

## Stage 16.5 (3148-3175): sequence numbering
- text36 = "_#_" if `arr67.Count>0` or (`text30 != Item` and superproduct and !flag4) (3144-3147).
- If `text30` starts with "9-" (dependency material): counter per material in arr14/15 starting at 2, +1 per subsequent occurrence; `text33` (seq) = that (3149-3160). With `debugMaterialSequence` prefix "vvvvvv".
- Else `text33 = getItemSequence(text30, arr55[num19])` (db-backed helper outside range; side effects unknown, UNVERIFIED) and sets text14/text15 for later (3168-3174). Note `text14 = text30 + text35` where text35 = "" (3118) so text35 is always empty (dead code).

## Stage 16.6 (3176-3181): dependency material code
- `text37 = "9-"`; if option is not fabric (IsFabric != 1) AND `!_ignoreOptDeps` AND OptChildCount > 0: append `<superitem-or-Item>-` where superproduct && !flag4 uses `text30` else `Item` (3178-3181). Resulting code: `9-<parent>-[optN]-<ordercode with spaces->_>`.
- 16.7 (3186-3191): `text37 += "[opt<num29>]-" + code (spaces->_)`; num29 = integer prefix of arr55 (the feature number). If parent starts "MRFN"/"9-MRFN" and OptionValueId in {300464, 300563, 300564, 300565, 300566, 300567}: append `-<ParentOptValCode>`. Hardcoded.
- Defect: when OptChildCount>0 is false, text37 is only `9-[optN]-code` i.e. no parent in code (ambiguity between items) (3177-3187).
- UNVERIFIED: LateGet of `arrayList55.IndexOf`/`Substring` suggests VB late-binding (arr55 held as object).

## Stage 16.8 (3193-3277): increment sum for this option
- `num30` = sum of increments from arr66 whose entry contains `<myparentitemshort>|`. `myparentitemshort` (text39) = text30 without "9-" prefix; if it contains "-": replace Item (if Item itself has "-") with its "_" form, else replace parts of text31 with "~"; cut at first "-"; restore (3216-3259). `IndexOf(text39+"|") > -1` substring match (not StartsWith): an entry such as `XX-ITEM|4` would match "ITEM|" and then `double.Parse("XX-ITEM|4".Replace(...))` can throw (3269-3272). Also sums every match (could double count if token is a suffix of another item code).
- 16.9-16.10 (3279-3375): builds the MATERIAL line(s) (`text38`):
  - num30==0 (16.10a, 3288-3333) or !=0 (16.10b, 3334-3375): line = `<parentItem>\t[opt<_#_><n>]\t<text37 with [opt -> [opt<_#_>>\t<parseOptCode(code, OptionValueId, OptionId)>[|<translation>]\t<increment>\t1\t0\t<seq-field>\t\t\t<10>\t\r\n`. Seq field: when `text36` non-empty: `[opt<_#_>n]` with "_"->"~" followed by `[seq]` + text33; else `text33`. Backflush/operation columns `\t\t\t10\t`; text41="10" is a constant ("10" = operation?). Output has 12 columns (matches `LEGACY_TSV_HEADERS["material"]`: Parent Item, Feature, Component, Opt code, Inc. price, Matl Qty=1, Scrap fact=0, Seq, Effect Date="", Obs Date="", Oper Num=10, BackFlush="").
  - For each extra super-product component (arr67) in REVERSE order (`for ... step -1`) an extra material line is added: parent `<comp>`, feature `[opt_<k>_<n>]`, increment recomputed per component (3300-3332 and 3346-3374). Difference between the 16.10a and 16.10b loops: in `a`, `num30` is only added when `text42 != ""` AND the remainder non-empty (3316-3323); in `b` neither check (3362-3365) -> `double.Parse("")`-type crash possible, but guarded by remainder (not guarded here). The two branches are otherwise duplicated code (num30==0 vs !=0 differ only by this guard; copy/paste defect).
  - `text36` ("_#_") included in the translation tail: `|` + `getTranslation(arr52, arr53, arr29, arr30, idx)` only for super products with components (3293-3296).
  - A line number mismatch: `num39 + 1` vs `num43 + 1` identical semantics.
  - `text41`="10" is not applied in component lines (they use literal `10`).

## Stage 16.12-16.15a (3376-3556): material registration and dedup
- 16.13 (3385-3556): enter block if `text30` startsWith "9-" OR ParentOptValId == "" (independent option) OR option marked unavailable (arr59 true) (3386). Else: logs `IGNORED myparentitem` (3576) i.e. dependent option under non-9 parent is dropped.
- text45 = `parent|[optN]|code` material key; per-parent-item lists arr9/10/11 (materials / components added) (3388-3394). text46 = text37 with `[opt` -> `[opt<_#_>`.
- Fabric colour handling: IsFabric==2 -> skip=true (3397-3401). IsFabric 1 or 2 -> record `"<arr55>:<name>~<num>"` in `skippedFabricColours` (3402-3410) (consumed later; UNVERIFIED).
- `_ignoreOptDeps` (3411-3455): skip unless NOT already in arr65 (material list for item) AND (components not previously present OR mismatch) AND not in arr11 [per parent]... The compound expression (3415-3432) is hard to verify (ConditionalCompare/late-binding); the intended rule: when ignoring option deps, add the line only once per parent. UNVERIFIED exact truth table. Also the debug branches (3436-3454) contain unreachable/duplicate `else if (arrayList64.Contains(text46))` conditions (copy/paste) and write a boolean into text20 via `CompareString(...) != 0` (3444, 3452): debug-only defect.
- Non-super product with unavailable parent: skip (3456-3460).
- Stage 16.15a (3489-3555) when not skipped: append to `arrayList65`, arr11, `materialstr += text38.Replace(Item+"\t", LongItem+"\t")` (replace short with long item in first column; also replaces all occurrences, including component rows where the first column equals the short item; 3501). Record parallel arrays 3 (material text), 4 (`[optN]`), 63/64 (value id <-> material text, replicated per component with `[opt_0`/`[opt_#` renumbered to component index 3519-3529), 10 (components added). Descriptions: arr5 = primary-language description (cached text29/else option name) ; arr6 = other-language description; arr7 = status (3531-3554). `continue` -> next option.
- 16.15b (3557-3572) when skipped: for each item in `text31` split on '|' (skipped parents), if not already in arr12 and IsFabric<2: add item to arr12 and feature `arr55[num19]` to arr13 (skipped parents bookkeeping; used outside range; UNVERIFIED).
- Defects: `arrayList63`/`64` are appended per component entry in a different count than `arrayList3` (parallel-array desync risk), arr63 gets component entries without matching arr3/4/5/6/7 entries.

## Stage 17 start (3579-3605)
- Begins `[optdata]` text construction: for options passing `arrayList18.Contains(optval) | !_syteline` (active option values only when syteline), emit `optIds(x) = <optid>, prevoptid = <prev>` lines (3594-3599); truncates feature codes longer than 5 chars to first 3 (3600-3605+). Continues beyond requested range.

## Cross-cutting
- Cancellation: `_abortThread` checked only in the outer item loop (2474). Long inner loops (10-16) and the 600/900s queries are not cancellable. No Cancel on SqlCommand.
- Error handling in this range: only for file open (2117) and trade-net (2568); everything else relies on an outer try/catch (outside range; UNVERIFIED). Readers on connections 1/2 are not closed on exceptions.
- Progress: only `UpdateStatusLabel` per item and at setup; timer via `UpdateExportTimer`. No percent progress.
- Debug-modal dialogs (`debug_form.ShowDialog`) block the worker thread when debug flags are on (2284, 2594, 2803).
- All SQL is string-concatenated (no SqlParameter). Strings: `_currency`, `_effectiveDate`, `_minItem`, `_maxItem`, `_itemList`, LongItem, Product_Code, `_contract`, order codes, user name.

---------------------------------------------------------------------------
# Comparison to Python ports (C:\01 Projects\mk_product_workbench\services\syteline_export\)

Legend: IMPL = implemented; PART = partial; MISSING; DIFF = differs.

| # | Legacy item | Status | Evidence |
|---|---|---|---|
| 0 | File open/headers for superprod/planning/description | PART | `config.py` LEGACY_TSV_HEADERS has all three header sets matching 2148-2153 (superprod 19, planning 22, description 3). No writer in these files (writer is `legacy_output.py`/`auxiliary_output_service.py`, not requested). Probe-open/truncate of item file MISSING. |
| 0 | MillerCAD/CSI skip of side files | MISSING | `config.py` has `export_mode`, `miller_cad`, but no gating of header creation in the files reviewed. |
| 1 | 5 connections | DIFF | `item_source_service._connect` opens one connection per call (new connection per fetch), no pool of 5; acceptable but no lifecycle handling for long export. |
| 2 | ExtractUser guard + UPDATE Site | MISSING | no code in reviewed files; legacy check is dead code (2233) so behaviour equals "no check" but the UPDATE write (2240) is also not ported. |
| 3 | catalogue option values arr16 + Knoll removal (284979, 286214, 286909) | MISSING | no reference in any file; `fetch_staged_option_features` takes an explicit `allowed_option_ids` (item_source_service.py) and says caller must supply the allowlist, so the cov list, IsKnollCatalogue removal and 292/299/300 filter are only partially covered (292/299/300 only in `assign_legacy_feature_positions`, material_conversion.py:360). |
| 4 | active option values (Status=1) | MISSING | no query. |
| 5 | CatalogueProductOptionExclusions, `#` / 0Y#-0# colour pair logic | MISSING | no query or logic. |
| 6 | CatalogueItemOptionExclusions | MISSING | no query. |
| 7 | CultureCode lookup | MISSING | no code. |
| 8 | Item selection SQL | PART/IMPL | `item_selection_query.py` ports select list, joins, scope chain, BRW list, UNION with Unreleased, active filter, exclude-SP union, ORDER BY, with bound parameters (parameterisation is a deliberate improvement over concatenation). Differences below. |
| 8a | description language joins | IMPL | item_desc and pd use `language_id`, alt uses `other_language_id` (lines match 2355, 2364). |
| 8b | ListPrice column condition | IMPL | `miller_cad or (syteline and not export_base_prices)` matches 2351. Date is bound as text instead of a quoted literal; legacy always quoted `'<effectiveDate>'` including empty -> `''`. Python passes `list_price_effective_date` default "" (equivalent). `text9` is identical. |
| 8c | list scope with empty list | DIFF | Legacy adds no filter (all items; 2380). Python rejects empty/duplicate/blank lists (`ValueError`). Safer; behavioural difference. Also `config.validate` rejects duplicates and `min_item > max_item`, which legacy did not. |
| 8d | range min>max, blank endpoints | DIFF | Python validates; legacy does not (added validation). Case/collation: `min_item > max_item` Python string compare is case-sensitive and codepoint-based; SQL Server compare is collation-based (UNVERIFIED mismatch). |
| 8e | product scope | IMPL | `AND pc.ProductCodeId = ? AND CatalogueItems.CatalogueId = ?`. Python does not guard against missing CatalogueItems join when syteline/millerCAD/itemreport all false (same latent defect, but it raises "valid catalogue ID" only when catalogue invalid). |
| 8f | item-report non-active LEFT JOIN rewrite | PART | Ported with `.replace(...)` (line "fields = [sql]"). The later `replace("CatalogueItems","CatalogueItemsUnreleased")` double-rewrites "CatalogueItemsUnreleased" -> "CatalogueItemsUnreleasedUnreleased" just as the legacy text replace would (same latent defect, retained; UNVERIFIED not tested). |
| 8g | `Item.Status` -> `0 AS Status` replace | IMPL | same text replace. |
| 8h | exclude-superproducts union | DIFF | Python additionally rewrites `Item.Status,` to `sp_item.Status AS Status,` in the alternate branch (its comment); legacy keeps `Item.Status` (the component's status). Deliberate deviation: output Status differs for that branch. Also Python duplicates params correctly for that branch. |
| 8i | Item.Status/ORDER BY in UNION | IMPL | `ORDER BY Item.Item` appended identically (UNVERIFIED valid in T-SQL after UNION; legacy same). |
| 8j | CommandTimeout 600 | IMPL | `fetch_items` sets cursor.timeout = 600. |
| 8k | Two-pass reading (count then loop) | MISSING | `fetch_items` reads once (fine) but no progress / count. |
| 8l | IsSuperProduct exclusion / superproducts-only / MK1*O exception | MISSING | `exclude_superproducts` only affects the UNION; the per-row skip rules (2489) and MK1/O flag4 are not in these files. |
| 8m | getFeatureCount for super products | MISSING | not in reviewed files. |
| 8n | BOCFAB prefix per catalogue 229 / GetShortProductCode | PART | `item_record_formatter.py` has `feature_prefix: str = "BOCFAB"` default but no catalogue-229 / short product code logic. |
| 9 | Tradenet contract discount | MISSING | `config.py` carries `send_tradenet`/`send_contract` only; no query, no rounding, no first-item-cache defect modelled. |
| 10 | PDMOptionDataReport load | PART | `fetch_option_report` executes `EXEC PDMOptionDataReport ?` with parameter, timeout 900. DIFF: legacy stores into `#temptable` and runs a custom SELECT (join to OptionValue/DependentOptionValues, `OptChildCount` via `fnOptionChildCount`, `OptChildId`, `fsccompliant`, m/c prefix, OF 9B ordering). Python does the m/c prefix in `normalize_legacy_option_report_rows` (IMPL, ids match 26-33), the OF ordering in `order_legacy_option_report_rows` (IMPL), but raw proc rows will NOT contain `OptChildCount`, `OptChildId`, `fsccompliant`, `IsFabric`(?) unless the proc returns them: the proc's 29 temp columns do not include OptChildCount/OptChildId/fsccompliant, so the Python raw fetch lacks those derived columns (they come from the legacy post-SELECT with joins and `dbo.fnOptionChildCount`). `normalize` reads `row.get("OptChildCount")` / `"OptChildId"` which would be None -> -2 sentinel. DIFF/MISSING (major). |
| 10 | flatten fabrics cursor (re-parenting grandparent, IsFabric 2 -> 1) | MISSING | Python only drops `#` rows (`flatten_fabrics and order_value.endswith("#")`), no re-parenting. Also legacy applies prefix before the `#` check? Legacy order: SQL CASE adds prefix, then C# EndsWith("#") skip; Python prefixes first then checks: same. |
| 10 | fabric `#` marker in name for FSC | IMPL | `DisplayName` adds "#" if fsccompliant==1. |
| 10.2 | availability filter (cov & !cpoe & !ciove | !syteline) | MISSING | no function (`fetch_staged_option_features` filters only by supplied allowed option ids on OptionId, not OptionValueId). |
| 10.x | AE / catalogue 30 branches | MISSING | `assign_legacy_feature_positions` excludes 292/299/300 for all items (legacy: only AE and catalogue 30, not for other items 2686-2737). DIFF: over-exclusion for non-AE items. |
| 10.x | child option reconcile (-2 replaced by real, 8512 for customers own) | IMPL | `reconcile_legacy_option_child_ids` (identity key = text25 fields). Differs: legacy merging is by arrayList62 key and REPLACES `-2` with the new id (Remove(-2); Add) only when OptChildId non-empty; Python also adds additional distinct child ids (matches legacy Add semantic). OK. Note Python identity key includes `optval_name`? no: matches text25. |
| 10.x | feature index `num7` increments on OptionId change | IMPL | `assign_legacy_feature_positions` (last_option_id). Note legacy `num8` is not updated for skipped (292/299/300) rows; Python also `continue`s before updating (line 361). OK. Output format `n|code-without-#` matches arr55. |
| 11 | description fetch (primary lang, '>' -> ' ') | MISSING | not in reviewed services (`metadata_service.py` not reviewed). `item_record_formatter` replaces '>' only in item description. |
| 12 | description fetch (other language) | MISSING | same. `other_description` blank-trim is in `LegacyMaterialConversionRegistry.add` only. |
| 13 | SLFeatureLength per option (default 2) | PART | `fetch_legacy_option_feature_length_rows` reads from a different, stage-20 style catalogue-scoped query and `resolve_legacy_feature_length` (stage 20). Stage 13's simple `SELECT SLFeatureLength FROM [Option]` and its cache / default 2 / NULL crash are not ported (registry default `previous_feature_length=2`). |
| 14-15 | incremental price queries (standard + SP + order-code fallback + extendSPOpts + range 999) | MISSING | No query. Only pure summing helpers: `sum_legacy_increment_entries`, `normalize_legacy_increment_parent_token`, `calculate_legacy_increment_total`. |
| 14 | `double.Parse` culture, IncList vs MyIncrementalPrice choice | MISSING | `float(...)` with `isfinite` check; selection of IncList vs MyIncrementalPrice not in code. |
| 16 | parent-item resolution via ItemComponents.FeaturePositionString, 2-pass with 1142 | MISSING | not present. |
| 16.2-16.3 | parent material substitution | IMPL | `resolve_legacy_parent_material` ports the id set {9275,...,9329}, GHS/GHG with {8, 9487}, and "material in parent_material". DIFF: legacy also includes `IsFabric == 2` as a trigger (3085) - Python has no is_fabric parameter, so fabric colour substitution is MISSING. Also legacy substitutes ALL matching arr63 entries and replaces arr67 (component) list, and continues loop (no early return); Python returns on first match with `return material, True`. DIFF. |
| 16.2 | "unavailable" flag (arr59) when parent not 9- | MISSING | not modelled. |
| 16.5 | sequencing | PART | `LegacyDependencyMaterialSequencer` ports the 9- branch (start 2, +1) precisely; non-9 branch `getItemSequence` is explicitly rejected (ValueError). MISSING. |
| 16.6-16.7 | dependency code `9-<parent>-[optN]-code` + MRFN suffix | IMPL (PART) | `build_legacy_dependency_material` reproduces ids {300464, 300563..300567} and the 9- construction. DIFF: legacy condition uses `IsFabric != 1` (so IsFabric==2 colours still get a parent prefix) while Python returns None for any truthy `is_fabric` (bool); a value of 2 may be coerced to True: DIFF. Python also returns None (no material) when child_count<=0, whereas legacy still builds `9-[optN]-code` in that case (3177-3187) -> DIFF (documented as "no dependency", but legacy emits the 9- code). Python raises on missing `|`, legacy would throw too. |
| 16.8 | increment sum + parent token normalization | IMPL (DIFF deliberate) | `normalize_legacy_increment_parent_token` matches 3203-3259. `sum_legacy_increment_entries` uses `startswith(token|)` instead of legacy substring `IndexOf`; documented as a defect fix (legacy matches suffix/substring and can throw). Result differs when substring-only matches exist (legacy would crash/overcount). |
| 16.10 | material line format `text38` | MISSING | `config.LEGACY_TSV_HEADERS['material']` only. No builder for the 12-column line, `_#_`/`[seq]`/`[opt_k_n]` components, `parseOptCode`, `getTranslation`, reverse component loop. |
| 16.13-16.15 | dedupe/registration | PART | `LegacyMaterialConversionRegistry.add`: dedupe by normalized name among `_materials_on_item_tab`, previously converted, seen. Legacy dedupe differs (text45 key `parent|[opt]|code`, per-parent lists arr9/10/11, `_ignoreOptDeps` rules, arr63/64 per-component replication, `materialstr` accumulation, skippedFabricColours, arr12/13 skipped-parent tracking) - these are MISSING; `description_key`, `feature_length == -1` and `child_feature_length` fields are from outside this range (stage 18+) UNVERIFIED. |
| 17 | `[optdata]` text | MISSING | out of scope of reviewed files. |
| - | Cancellation `_abortThread` | MISSING | no cancellation hooks in services. |
| - | Progress reporting | MISSING | none in reviewed files. |
| - | Item record (type M/P, X marker, status code) | PART | `item_record_formatter.py` formats the item row; the inputs from this range (price selection base vs list, negative price clamp) are partly in; component cost (num4 tradenet) unverified. Out of the stage range of this inventory. |
| - | Config flags | IMPL | `legacy_thread_arguments()` maps the 33 initThread arguments (`config.py`). Missing from config: `_numFeatureSlots`, `_maxDescriptionLength` (`ItemSelection.max_description_length`, default 200), `_tradeNet` db name, `_exportMaterialsForPDMReport`, `_itemreport` is present. Defaults: `ItemSelection.active_only=False`, `export_base_prices=True`. `_maxDescriptionLength` default UNVERIFIED vs legacy (set by caller). |

## Top gaps/defects
1. Option-report SELECT is not ported: PDMOptionDataReport raw rows lack OptChildCount/OptChildId/fsccompliant (legacy joins DependentOptionValues + fnOptionChildCount, 2588), so Python child-id logic always yields -2.
2. Availability filtering (stage 3-6: catalogue values, product/item exclusions, `#` colour exceptions, Knoll removals 284979/286214/286909) completely missing.
3. Incremental price queries (stages 14-15 incl. SP fallback, range 999, extendSPOpts) missing; only summing helpers exist.
4. Parent-item resolution via ItemComponents.FeaturePositionString (stage 16.1, option 1142 special case) missing; `resolve_legacy_parent_material` drops the IsFabric==2 trigger and early-returns on the first match.
5. 292/299/300 exclusion is applied to all items in Python but legacy only applies it to AE items and catalogue 30.
6. Material line builder (16.10a/b) and `getItemSequence` are missing; sequencer rejects non-"9-" materials.
7. Dependency code: Python returns None for child_count<=0 / IsFabric truthy, legacy still builds `9-[optN]-code` (3177-3187).
8. Legacy defects to avoid or document: dead extract-user guard (2233), empty list = unfiltered (2380), trade-net discount cached by product code from first item's price and silently zero on error (2537-2581), substring increment match (3269), copy/paste divergence between 16.10a/16.10b guards, hardcoded ids (catalogue 229/30, options 9275.., 1142, 8512, range 999), N+1 queries, double for money, culture-sensitive parse.
9. Python SQL-exclude-SP branch changes status column (`sp_item.Status`) vs legacy `Item.Status`; list/range validation stricter than legacy (intentional, but needs sign-off).
10. No cancellation, progress, ExtractUser write, descriptions (stages 11-12) or feature-length stage 13 in the Python services reviewed.


# Part C


Source: C:\Users\siaoca\Desktop\PDM\PDMMaintenance\ExportThread.cs (decompiled VB; names are arrayListNN). Whole range read in 5 chunks.
Port status: IMPL / PARTIAL / MISSING / DIFFERS. Python = services/syteline_export/material_conversion.py (MC) and item_source_service.py (ISS).
The range starts mid-way through the stage-17 per-option loop; the loop head and variable initialisation (before 3600) were not read: UNVERIFIED where noted.

## Key state (decompiled names)
- arrayList47 = OptionId per slot; 45 = option name; 48 = arg to parseOptCode; 49 = fabopts (0 normal, 1 fabric, 2 fabric colour replacement); 54 = configured default feature length; 55 = order-code string; 57 = parentoptvalIds ("" = no parent); 59 = parentunavailable; 60 = unique-component flag; 61 = child option ids per slot; 63 = colour arg; 3/5/6/7 = componentsListed + desc/other desc/status; 65/4 = feature lookup pair; 46 = feature slot tokens for the item row; 68 = aeron finish materials; 16 = selected option value ids; 26 = tokens stripped from materialstr.
- text6 = fabric prefix token (BOCFAB[..]); text19 = feature template string ("XXXXX-..."); num6 = running feature position; num7 = running [optN] counter; num8 = previous OptionId; materialstr = tab-delimited BOM text containing [optN] placeholders.
- Flags: _flattenFabrics, _length5Feats, _uniqueComponents, _plcPhantoms, _millerCAD, _syteline, _formatCSI, _exportBasePrices, _exportSPComponentMaterials, _superProductsOnly, _numFeatureSlots; flag4 (meaning UNVERIFIED, set before 3600; used as "SP component pass" in conditions IsSuperProduct && flag4); flag9 = unique-convert flag.

## Stage 17 loop head, dedup, slot record (3600-3633)
- 3600-3613: text55 = arrayList55[i]; Length>5 -> first 3 chars, Length>4 -> first 2 chars. A debug line (option id, name, 52, 55) is appended to text53 when the key differs from the previous key. Debug text only.
- 3614-3619: `continue` when the OptionId equals the previous OptionId (num8). Otherwise num8 = OptionId and num7++ so [optN] increments once per distinct consecutive option.
- 3622: text56 = two-digit zero-padded running position num6.
- 3625-3633: ignorecolour flag10 = true when i>0 and fabopts[i]==2.
- Port: MISSING. MC.assign_legacy_feature_positions is the stage-10 assignment, a different mechanism.

## 17.1 / 17.1a fabric option (fabopts==1) template (3635-3787)
- parseOptCode(arrayList55[i], arrayList48[i], arrayList47[i]) returns "x|code"; num54 = len(code). parseOptCode body is outside the range: UNVERIFIED.
- 3640: len==2 && code=="9B" && Item startsWith "OF" -> len=3.
- 3644-3647: OptionId 8512/8524/8624 force len = (_flattenFabrics ? 8 : 5); OptionId 8513/8525/8625 force it only when _flattenFabrics (operator grouping: Or(Or(8512,8524,8624), And(Or(8513,8525,8624?...), flatten))).
- len 5: slot = text6 + "-F" + pos + "-05#"; num6 += 10; text19 += "XXXXXXXXXX-" (10 X). Note: position advances 10 for a len-5 fabric slot.
- len 8: text6 reassigned to "FAB"; slot "FAB-Fpp-08" (no #); num6 += 8; text19 += "XXXXXXXX-"; only for Item 420KIT or 420KS is the slot added to arrayList46 (3662-3665).
- len 4: slot text6-Fpp-04#; when parent=="" the slot (without #) is added to arrayList46 and "XXXXXXXX-" appended (8 X); num6 += 8 regardless.
- len 3: slot text6-Fpp-03#; Item starts "OF" and ends "2": position 8 or 14 -> "BOCFAB-" replaced by "bocfab-HAR-", else "BOCFAB-"+Item+"-HAR-"; when parent=="" slot added and "XXXXXXX-" (7 X); num6 += 7.
- default length: defaults total=7, parent len=2, child=5. If !_length5Feats: cache (lists 35/36/37 keyed by OptionId) else SQL (stage 17.2a): SELECT MAX(parent_opt.SLFeatureLength) AS parent_featlen, MAX(child_opt.SLFeatureLength) AS child_featlen FROM [Option] child_opt WITH (NOLOCK) JOIN OptionValue optval ON child_opt.OptionId=optval.OptionId JOIN DependentOptionValues dov ON optval.OptionValueId=dov.AdditionalOptionValueId JOIN OptionValue parent_optval ON dov.OptionValueId=parent_optval.OptionValueId JOIN [Option] parent_opt ON parent_optval.OptionId=parent_opt.OptionId WHERE parent_opt.OptionId = <optId>. total = parent+child; slot = text6-Fpp[debug]-0<parentLen>#; OF*2 HAR rename repeated; when parent=="" slot added and total X's + "-"; num6 += total. With _length5Feats the SQL is skipped (total 7, parent 2).
- Errors: SQL exception -> modal MsgBox(ex + SQL) and swallow (17.2a); defaults stay and the cache is still appended with the defaults. NULL MAX -> int.Parse("") FormatException, same catch.
- Port: MISSING (all length 3/4/5/8 rules, 8512-family forcing, FAB reset, 420KIT/420KS, HAR renames, X templates). ISS has no parent/child featlen query.

## 17.1b / 17.2b / 17.2c non-fabric option (fabopts != 1 and !ignorecolour) (3788-3842)
- 17.2b (3792-3810): code len >2 AND _length5Feats: code contains a space -> "Fpp-10", num6 += 10, "XXXXXXXXXX-"; else "Fpp-05", num6 += 5, "XXXXX-". Debug "featstr(BB)".
- 17.2c (3811-3832): num62 = int(arrayList54[i]); if ==2 and code len >2 -> code len; if >2 and _length5Feats -> 5. slot "Fpp-0<len>", num6 += len, len X (via debugFeatureTemplate wrapper, body UNVERIFIED) + "-".
- _uniqueComponents (3833-3841): tag = "[" + Product_Code with "-" and "_" removed + "]"; if slot lacks Item+"-" and tag+"-" and arrayList60[i]==0, prefix with Item+"-" (or tag+"-" when _plcPhantoms); flag9 = true.
- Defect: "-0" + len yields "-010" for len>=10 (also at 4850, 4962).
- Port: MC.resolve_legacy_feature_length reproduces only the "max>len==2 -> max" and "non-fabric >2 && length5 -> 5" parts, and only as a stage-20 helper. 17.2b space rule, num6 progression, unique-component prefix: MISSING.

## 17.3 Aeron finish materials collection (3844-3885)
- Item startsWith "AER" and OptionId == 6431: add "9-<Item>-<slot>-" + CRB, VPR, G1 always; BK (id 272082), MG1 (276007), MCR (276008), MVR (276009), MBL (276217), DN2 (307282), DJ2 (307283), MN2 (307284), MJ2 (307285) when arrayList16 contains the id.
- Defect: `!StartsWith("notAER1G")` is always true for an item that startsWith AER (dead check, also at 3924).
- Port: MISSING.

## 17.4 feature slot registration (3886-3915)
- If parentoptvalIds[i]=="" OR (parentunavailable && IsSuperProduct && !flag4): logMessage and arrayList46.Add(slot).
- else-if (parent=="" && !parentunavailable && fabopts!=2) is unreachable (first branch already covers parent==""): dead code that would have stripped "{..}" and appended N X of the trailing "-N".
- Port: MISSING.

## 17.5 / 17.6 placeholder substitution (3916-3921)
- arrayList24.Add(Item+"|[optN]"), arrayList25.Add(slot); materialstr.Replace("[optN]", slot); then Replace("\t"+text6+"-", "\t") removes the fabric prefix at every column start in the whole string.
- Port: PARTIAL at most. MC.build_legacy_dependency_material builds the "9-<parent>-[optN]-<code>" token (stage 16); the replacement by the feature position is MISSING.

## 17.6 / 17.7 Aeron rewrite (3922-4111)
- Item AER*: flag2 = true. If OptionId == 6437: pick finish materials from list 68 by suffix and Item substring.
- For CRB, VPR, DN2, DJ2 find the row "Item\t<slot>\t9-<slot>-DCR|DVP|DN4|DJ4\t" and replace the first column with the finish material; when the M-variant exists append a cloned row with suffix -MCR/-MVR/-MN2/-MJ2.
- BK/G1: rewrite "...-BK\t" row, clones replacing hard-coded "-F04-03-G1" with -BK, -MG1, -MBL, -MN2, -MJ2 (assumes position 04 length 03). text89 and text90 are identical strings.
- Loop 10..99: "DCR|DVP|DN4|DJ4|BK\t0\t1\t0\t<NN>" -> "...\t4"; then 23101/23102/23103 "\t0\t1\t0\t4" -> "...\t5". Magic numbers.
- Port: MISSING.

## 17.8-17.10 component expansion per option (4113-4191)
- Skip (`continue`) unless IsSuperProduct==0 OR flag4 OR _exportSPComponentMaterials. Resets preConv/ConvCount.
- 17.9: for each componentsListed entry containing "[optN]": converted = entry with slot substituted; feature = arrayList4 entry via list 65 (if the entry contains "-Item-" it substring-scans and the LAST match wins; else exact IndexOf).
- ignoreconvert flag12 = converted contains text6+"-" but not "9-"+text6+"-".
- 17.10 gate skips when _convertedList contains converted minus "#", or converted minus "FAB-" and "#", or converted[0:2]+text6+"-"+converted[2:], or flag12. Else dependentoption flag13 = (!flag9 || firstChildId>0) && converted contains "-Item-"; addMaterialToItemTab(converted, desc, otherdesc, status, flag13, IsSuperProduct && flag4, feature, debugInfo, -1, childIds list, stage). If converted contains -02#/-03#/-04#/-05# and _syteline: addFabricColour(converted, arrayList63[j], arrayList45, flag10).
- After loop: materialstr "-02#" -> "-02" ... "-05#" -> "-05".
- Port: PARTIAL/DIFFERS. MC.LegacyMaterialConversionRegistry.add resembles addMaterialToItemTab (body outside range, UNVERIFIED): dedups only on '#'-stripped material vs item-tab/previously-converted/seen (legacy tests three variants plus flag12); -1 length handled via previous_feature_length (plausible match); raises ValueError on empty child ids (legacy passes list as-is). flag13 and addFabricColour MISSING.

## 17.11-17.12 item header fields (4199-4265)
- text5 = "yes" only when IsSuperProduct && !flag4; that also clears text19 and arrayList46 (no feature slots on the SP itself).
- Notes containing "X" overrides text19 with Notes; else LegacyItem containing "X" does.
- Status 1 -> "A"; else "O" with text94: 0 URL, 2 OBS, 3 ON HOLD, others "". 
- left13 yes/no by text19 length; trailing "-" trimmed; "no" -> right3 "P", right4 "", text19 ""; else "M"/"BOC".
- Weight/Volume ""->0 (NULL becomes "" via ToString). Description = GetProductDescription(LongItem, ShortDescription); FSCCompliant==1 appends "#".
- Port: MISSING.

## 17.13 _millerCAD fixed width (4267-4314)
- Rewrites materialstr rows: drops 3rd column, fixed widths 30/8/8 + qty `f2` zero padded to 8 (truncating). For SP rows re-prefixes with Item. No guards when tabs missing (IndexOf -1 Substring exceptions). Port: MISSING.

## 17.14-17.16 item row output (4316-4491)
- Branch A (4316-4349): SP item and (!_exportSPComponentMaterials || _superProductsOnly): CAD fixed row + "[bitmap][feats]"; Syteline tab row with fixed literals (0,0,35,SUP,1,0,EA,CommodityCode,"P","no"); _formatCSI -> formatCSIData; AltDescription != NULL && !_formatCSI && _languageId != _otherlanguageId -> writeData(streamWriter4, translation row); non-Syteline: priceCodes/productCodes sets.
- Branch B (4350-4484): CAD: widths 30/10/30/10/_maxDescriptionLength, 10-flag slot indicator, 80-char slot list with "BOCFAB-" removed. Syteline: price = MyBasePrice if _exportBasePrices else ListPrice, negatives clamped to 0; fields ... right3 (M/P), text19 template, right4 (BOC); then feature slots (text6+"-" stripped; "bocfab" slots blank; "-HAR-" tail kept) tab separated up to _numFeatureSlots; then text16/17/18. Non-Syteline: price code row.
- Defect: slot loop assumes count <= _numFeatureSlots (no truncation). {1111}/{2222} logMessage lines; modal debug forms.
- Port: MISSING (no row emitter in MC/ISS; item selection query is in item_selection_query.py, not reviewed).

## 17.17-20 dependency feature position renumber (4492-4870)
Condition (4492): !_formatCSI && IsSuperProduct && !flag4 && !_superProductsOnly. Processes materialstr rows containing "\t[opt".
- Per row: component code = text before "\t[opt"; "<n>" suffix -> num97 (feature filter) removed; "9-" prefix stripped and "-[opt.." trimmed; placeholder text110; "[seq]" value text111; order-code suffix text114 after last "]-"; default len num98 = position of "|" in column 4 (min 2).
- Stage 18 SQL: SELECT itco.FeaturePositionString FROM Item WITH (NOLOCK) JOIN ItemComponents itco ON Item.ItemId=itco.ItemId JOIN Item sub_item ON itco.SubItemId=sub_item.ItemId WHERE Item.Item='<LongItem>' AND sub_item.Item='<comp>' (string concat; quote risk). FeaturePositionString split on "|" into OptionIds (filtered by num97).
- Stage 19 SQL: SELECT optval.OptionId FROM OptionValue optval WITH (NOLOCK) WHERE optval.OptionId = <id> AND (optval.OrderCodeValue='<code>' OR optval.OrderCodeValue='<code>#'); picks option index; fallback index = (placeholder lacks "#_1" && count>1) ? 1 : 0. Quirk: filters on the very id already known, so it only tests code existence.
- Stage 20 SQL (4643): catalogue-scoped CASE query returning SLFeatureLength, MAX(LEN(REPLACE(OrderCodeValue,'#',''))) AS max_length, IsFabric, preferring dependent fabric option when present, HAVING opt.OptionId=<id>. Rules: len = SLFeatureLength; max_length > len and len==2 -> len = max_length; IsFabric==1 -> flag15 (fabric replacement); last row wins; cached in lists 38/39/40. Then `!flag15 && len>2 && _length5Feats` -> 5.
- Position accumulation (lists 69-77): first sight of a component starts at 1 (for "9-" components whose base component text116 was seen, inherits base position and adds base's previous length once, guarded by list 77). Re-sight with a different placeholder: prev length num110: 4 && fabric -> 8; else if previous placeholder fabric -> 7; else for non-"9-" components, look for "9-<comp>" entries whose "_N" placeholder minus 1 equals the previous one and take that entry's length; position += num110; stored length = current.
- Output: text120 = ["BOCFAB[" + GetShortProductCode(prodcode, rootproduct) + "]-"] + "F" + 2-digit pos + "-0" + len. materialstr.Replace(placeholder "_"->"~" + "[seq]" + seq, debug marker ^^^^^^ or seq), Replace(placeholder, text120); if fabric strip "\t"+"BOCFAB[..]-".
- Defects: text107 always "" so flag14 conditions are constant true; lists 74/75 never read; unguarded int.Parse (4599, 4799); global string Replace on materialstr; "-0"+len for len>=10; seen-order dependent (first-seen positions).
- Port: stage-20 length rule IMPL: MC.resolve_legacy_feature_length (lines 4650-4677 logic) and ISS.fetch_legacy_option_feature_length_rows (SQL matches 4643). DIFFERS: Python raises on negative values and returns all candidate rows (legacy last row wins, NULL raises FormatException); caller must supply is_fabric. Stage 18/19 queries, option index choice, accumulation (4 -> 8, 7, interim "_N-1"), text120/[seq] rewriting, BOCFAB[ShortProductCode] prefix: MISSING. LegacyDependencyMaterialSequencer is a stage-16.5 sequence helper, not the [seq] rewrite here.

## 20.7-20.83 missing-component rows (4872-5008)
- Strips arrayList26 "<x>" tokens. Per row (item, feat, comp, desc columns): if comp<>"" && len(feat)>1:
  - flag18 = comp[5]=='-'. If !(comp startsWith "9-F" && flag18) && no "BOCFAB": dependentoption = true; feat after last "-F"; pos = int(feat[1:3]) + int(feat[4:6]); nextFeature = "F"+pos+"-0"+getFeatureLengthForItemOption(LongItem, desc) (DB routine body UNVERIFIED).
  - elif item "9-" && comp "9-F": updateChildFeatureLengthForMaterialOnItemTab(item, feat, flag) (body UNVERIFIED).
  - elif item "9-" && comp "9-BOCFAB[": child ids [8512] when SytelineCSIExport.IsKnollCatalogue(_catalogueId) else [8]; feature = feat.
  - addMaterialToItemTab(comp, desc after "|", "", 1, dependentoption, IsSuperProduct && flag4, feature, " <missing>", len (default 2), childIds default [-1]).
- If desc contains "|": replace with the part before "|" in materialstr (try/catch: MsgBox, swallow).
- Defects: Substring(1,2)/(4,2)+int.Parse on non-"Fxx-0y" feat throws uncaught; flag17/text125 debug is dead (text125 always "").
- Port: MISSING. Related knowledge only: MC.reconcile_legacy_option_child_ids maps "customers own" -> 8512 and unknown -> -2 (origin outside range, UNVERIFIED).

## 20.9 write-out (5015-5060)
- Pops materialstr by "\r\n"; sets includesCOM = true when a line has "BOCFAB" and "-CM01\t"; skips empty/"\r\n" and lines already in materialsWritten; appends the rest to arrayList2 and materialsWritten. Port: MISSING (registry _seen dedups materials, not final text lines).

## 21 super product component rows (5062-5115)
- Guard: continue unless !_formatCSI && _syteline.
- SQL: Item/Product/ProductDescription columns, ComponentSequence AS Seq, itm2 weight/volume/commodity, Quantity, FeaturePositionString, description CASE (pd2.ShortDescription, od.ShortDescription RelatedTable='SPComponent', prod2.Name), MyBasePrice by pc.BasePriceRef 1/2/3 (BasePrice, BasePrice2, BasePrice3), plus dbo.fnGetListPriceByItem(itm2.Item,'<_currency>',<text9>,<_siteId>,NULL) when _millerCAD or (_syteline && !_exportBasePrices), pc.Product_Code, pc.PriceCode, prod2.DescriptionId; JOIN Product_Code pc ON (ProductCodeIdOverride of Item else prod2.ProductCodeId) = pc.ProductCodeId AND pc.SiteId=<_siteId>; WHERE Item.ItemId=<ItemId> ORDER BY Seq. The CROSS JOIN (SELECT NULL AS ProductCodeIdOverride) x is unused: odd.
- Row loop to 5110 (continues past range, UNVERIFIED beyond): FeaturePositionString non-empty -> "M", "yes", "BOC"; parse "|" segments into distinct option ids (list 80) and 1-based positions (list 81); per option id query (5112, on sqlConnection3) over OptionValue/Option/CatalogueOptionValues with both language descriptions and dependent parent id.
- Port: MISSING.

## Cross-cutting legacy defects
1. Dead code: `num55>5 && num55<6` (3754); unreachable else-if at 3892; "notAER1G" negation; flag14/text107/text125 constants.
2. text6 = "FAB" (3658) leaks to later options.
3. String-concatenated SQL in 17.2a, 18, 19, 20, 21; 17.2a errors only MsgBox + swallow with poisoned cache.
4. Modal MsgBox/debug_form in worker thread.
5. "-0"+len breaks at len>=10.
6. Position advance (5->+10, 4->+8, 3->+7) differs from slot length; stage 20 re-derives lengths separately.
7. Whole-string Replace on materialstr; hard-coded Aeron literals ("-F04-03-G1", ids 6431/6437, 272082, 276007-9, 276217, 307282-5, 23101-3, OF*2, 420KIT/420KS, 8512 family).
8. Unguarded Parse/Substring in CAD formatting and 20.82.

## Port matrix
| Item | Status | Evidence |
|---|---|---|
| 17 option dedup / [optN] counter | MISSING | no MC/ISS counterpart |
| 17.1a fabric templates | MISSING | none |
| 17.2a parent/child featlen SQL | MISSING | ISS has only stage-20 SQL |
| 17.2b/c, unique components | MISSING | |
| 17.3, 17.6-17.7 Aeron | MISSING | |
| 17.4 slot registration | MISSING | |
| 17.5 [optN] substitution | MISSING (token build PARTIAL) | MC.build_legacy_dependency_material |
| 17.9/17.10 convert + dedup | PARTIAL/DIFFERS | MC.LegacyMaterialConversionRegistry.add |
| 17.11-17.16 row output | MISSING | |
| 17.17-20 renumbering | length rule IMPL, rest MISSING | MC.resolve_legacy_feature_length, ISS.fetch_legacy_option_feature_length_rows |
| 20.8 missing rows | MISSING | |
| 20.9 write-out | MISSING | |
| 21 SP components | MISSING | |


# Part D


Source: C:\Users\siaoca\Desktop\PDM\PDMMaintenance\ExportThread.cs (read in full, 5110-6353).
Port dir: C:\01 Projects\mk_product_workbench\services\syteline_export\ (all 8 modules read).
Legend: IMPL = implemented, PART = partial, MISSING, DIFF = differs. UNVERIFIED = cannot be proven from this range.

## 0. Context / variables (decoded names; defined before 5110, so UNVERIFIED)
- `sqlDataReader` = outer product/item row (LongItem, ItemId). `sqlDataReader2` = current component/BOM row (Item, Component, Description, Quantity, ListPrice, MyBasePrice, Product_Code, PriceCode, CommodityCode, VolumeLitres, WeightKilos, DescriptionId, "Super Description", Seq).
- `arrayList` = item-sheet records (item file). `arrayList8` = item rows already added (dedupe key, without trailing tabs). `arrayList2` = material-sheet records. `materialsWritten` = material rows written so far. `arrayList45` = allowed OptionValueIds (UNVERIFIED source). `arrayList80` = option ids for this component (UNVERIFIED). `arrayList81` = superproduct feature columns (UNVERIFIED). `arrayList12/13` = component -> feature-position list (13 holds "n|code") (UNVERIFIED). `text3` = description-file key prefix (UNVERIFIED). `text6` = root product short code (UNVERIFIED; used as "-"+text6+"-"). `right6` = item type "M"/"P", `right7` = brand "BOC"/"" (UNVERIFIED, defined earlier).
- Output files: item (`arrayList`), material (`arrayList2`), superprod (`streamWriter2`), description (`streamWriter4`).
- Flags: _syteline, _formatCSI, _millerCAD, _superProductsOnly, _flattenFabrics, _length5Feats, _ignoreOptDeps, _uniqueComponents, _plcPhantoms, _exportBasePrices, _abortThread, _catalogueId (229 = HRB special), _languageId/_otherlanguageId, _numFeatureSlots, includesCOM.

---------------------------------------------------------------------
## Stage 22: option-value fetch and feature-material row build (5110-5237)
Lines 5110-5237 (loop `for num133 over arrayList80` = options of the component; `num131` running feature offset, starts earlier).

SQL (5112, threadStage "22" set at 5113 AFTER the string is built, so the stage marker is for the Command only):
```
SELECT opt.IsFabric, optval.OptionValueId, opt.SLFeatureLength, optval.OrderCodeValue,
  MAX(LEN(REPLACE(optval.OrderCodeValue,'#',''))) AS max_length,
  CASE WHEN od1.ShortDescription IS NULL THEN optval.Name ELSE od1.ShortDescription END AS Name,
  optval.DisplayOrdinal, dov.AdditionalOptionValueId,
  CASE WHEN parent.OptionId IS NULL THEN -1 ELSE parent.OptionId END AS parent_optid,
  od2.ShortDescription
FROM OptionValue optval WITH (NOLOCK) JOIN [Option] opt ON optval.OptionId=opt.OptionId
 JOIN CatalogueOptionValues cov ON optval.OptionValueId=cov.OptionValueId AND cov.CatalogueId=<_catalogueId>
 LEFT JOIN DependentOptionValues dov ON optval.OptionValueId=dov.AdditionalOptionValueId
 LEFT JOIN OptionValue parent ON dov.OptionValueId=parent.OptionValueId
 LEFT JOIN OtherDescription od1 ON optval.DescriptionId=od1.DescriptionId AND od1.LanguageId=<_languageId>
 LEFT JOIN OtherDescription od2 ON optval.DescriptionId=od2.DescriptionId AND od2.LanguageId=<_otherlanguageId>
GROUP BY ... HAVING optval.OptionId = <arrayList80[i]>
```
Logic:
1. Row kept only if OptionValueId in `arrayList45` (5127). Per kept row collect: OrderCodeValue (85), SLFeatureLength (86), Name/short desc in language 1 (88), IsFabric (89), dependent flag = AdditionalOptionValueId non-empty (90), other-language ShortDescription or "" (92), DisplayOrdinal (91, never used). `num134` = max of max_length, floor 2 (5124-5140).
2. Per-code feature length (87) = SLFeatureLength if > num134 else num134 (5162-5169). Debug text `text139` built but only informational (UNVERIFIED if later logged; not in this range).
3. If no codes: `continue` (5172) - skips num131 advance and template.
4. Slot length num138 = length of FIRST code only (arrayList87[0]); if first IsFabric==0 and >2 and _length5Feats -> 5; if first IsFabric==2 and ==5 -> 4 (5176-5185).
5. Feature position text140 = "F" + 2-digit(num131) + "-0" + num138, passed through debugPostProcessedFeaturePos("FF") (5186-5189). Added to feature-slot list `arrayList82` only if first row NOT dependent (5190).
6. Template text136 (used later as item-row "notes/marker" column): IsFabric==1: Knoll -> flatten? "XXXXXXXX"(8) : "XXXXXXXXXX"(10); non-Knoll -> contains "CM01#" ? 8 X : 7 X. IsFabric==0: num138 "X" chars. IsFabric==2: nothing. Append "-" between options (5206) (trailing "-" stripped at 5249). Wrapped via debugFeatureTemplate(...).
7. For each code: material key text141 = "9-" + text140 + "-" + code; IsFabric==2 -> "9-FAB-" + code (5213-5217).
8. Material record text142 (tab separated, 5218): key, "no", code|Name, "A", "", "", "0", "", "0", "", "", "", "ZZ-ZZ", "", "0", "", "0", "", "yes", "35", "0", "0", "", "", "", "", "DEF", "1", "0", "EA", "", "P", "", "", "no", "", "", "", "", "", "0", "0". (Exact tab count is only reproducible from the source nesting; see text.) If not already in `arrayList83` (dedupe on full record) -> add to arrayList83, and arrayList84 receives `key\t<otherLangShortDesc>` or "".
9. num131 += num138; if num138==4 and codes contain "CM01#" then += 4 more (5232-5236).
Outputs: arrayList82 (feature slots), arrayList83 (material rows candidate), arrayList84 (description rows), text136 (template).
Errors/side effects: int.Parse of SLFeatureLength/IsFabric/max_length with no null guard (throws on NULL; the CASE/LEFT JOIN doesn't protect SLFeatureLength). Reader closed manually (no using) - leaks on exception.
Defects: (a) only first code's length/IsFabric drives slot width and fabric type (mixed values silently ignored). (b) `num138` of 10 (Knoll SLFeatureLength) would print "-010" (always prefixes "-0"). (c) `text139` built but unused here. (d) num133 `-` separator uses arrayList80.Count even when earlier options `continue`d; trailing handled by 5249. (e) SQL via string concat of ints (not injectable, ids numeric). (f) max_length is a per-group MAX over a GROUP BY that already includes OrderCodeValue, so it is just LEN of that code (effectively no-op aggregate). (g) OtherDescription joined even when _languageId==_otherlanguageId.
Python: MISSING. No module queries OptionValue/CatalogueOptionValues in this shape; `resolve_legacy_feature_length` (material_conversion.py:376) ports stage 20, whose rule (`max>len and len==2 -> max`; non-fabric >2 with length5 -> 5) DIFFERS from stage 22 (per-code max(SLFeatureLength,num134); first-row-only; IsFabric==2 5->4). `assign_legacy_feature_positions` (343) is stage 10 not "F01-03" position text. The X-template (text136), CM01# +4 offset, 9-/9-FAB- material key and the 40-field material template are not present anywhere.

## Stage 23 / 23.1 / 23.2 / 23.3: superproduct row, item row (5253-5373)
23 (5253-5254): `num3 = getFeatureCount(LongItem)` (UNVERIFIED body; defined elsewhere).
23.1-23.2 (5256-5267): superprod-file record:
`Item \t Super Description \t Seq \t Component \t Quantity \t Description \t featureCount \t` + arrayList81 values joined by TAB, + CRLF. Written with `writeToStream(streamWriter2, ..., "gggggg")` => file `_superprod_data`.
23.3 (5269): `if _superProductsOnly continue;` skips item/material work for this component.
Item row `text144` (5273-5390), two branches:
- `_syteline` (5284-5370): `Component \t no \t Description \t A \t \t` then price + `\t` (price = MyBasePrice if _exportBasePrices else ListPrice; blank->0; negative->0). Then feature-slot allocation for component found in arrayList12: take `13[idx]`, strip up to "|"; len n (n>2 & _length5Feats -> 5); next position from last slot `text137` ("Fxx-yy" -> xx+yy) else 1; "F"+2digit + "-" + 2digit via debugPostProcessedFeaturePos("GG"); fill FIRST empty slot of arrayList82; also appends "-" + n x debugFeatureTemplate("X","5") to text136; slot set to position if _ignoreOptDeps else "" (5337-5358). Then the long row: `+ "0\t\t\t" + Product_Code \t VolumeLitres \t WeightKilos \t no \t 35 \t 0 \t 0 \t \t \t \t \t 1 \t 0 \t EA \t CommodityCode \t right6 \t "" \t no \t text136 \t \t \t right7 \t 0 \t 0 \t \t` then arrayList82 slots joined by TAB (padded to _numFeatureSlots at 5243-5248).
- non-syteline (5371-5391): `Component \t no \t Description \t A \t basePrice \t Product_Code \t PriceCode`, records distinct PriceCode into `_priceCodes` and Product_Code into `_productCodes` (feeds priceformula/productcode aux files).
Dedup/emit (5392-5409): if text144 not in arrayList8 -> add; `arrayList.Add(text144 + "\t\t\t\t")` (4 trailing tabs, dedupe key lacks them); logMessage {3333}.
Defects: base price rule uses MyBasePrice only when flag set, the not-flag branch ignores currency; `double.Parse` culture-dependent; `double` price printed via VB ToString (R format); `text137.Substring(...IndexOf("-"))` throws if text137 malformed; first-empty-slot search silently drops allocation if all slots full (no error); text136 grows even when slot not found? (only inside found branch, ok); superprod row written BEFORE the _superProductsOnly check, and even if item row duplicate.
Python:
- `format_syteline_item_record` (item_record_formatter.py:56) PART/DIFF. It matches the field order up to commodity/type/""/"no"/marker/brand/0/0/"" and price rule (negative->0, base vs list switch), but: (1) Between the second "0" and "1" legacy has 4 empty fields; Python emits 4 "" + a "SUP"/"" cell (5 empties) - UNVERIFIED whether 5360 is the full row for superproducts; a diff test against real output is needed. (2) Between marker (text136) and brand legacy has 2 empty cells (`text136 \t \t \t right7`); Python has 3. (3) Python takes already-resolved `feature_codes` and truncates to 20 and strips "BOCFAB-"/"-HAR-"; legacy at this stage uses the slot positions array padded to `_numFeatureSlots` (not 20) and no stripping. (4) Python appends height/width/depth + "" (not in this range; UNVERIFIED stage). (5) Python status/status-desc columns "A"/"O" are not in the 23.3 row (legacy hardcodes "A",""); Python's `description.replace(">"," ")` and `component_cost` field not visible here. (6) Legacy trailing `"\t\t\t\t"` append (5396) not modeled. (7) No arrayList8 de-dup; `LegacyRecordDeduplicator.accept` (legacy_output.py:93) is an approximation of writeData, not of arrayList8.
- Superprod-file record: MISSING (nothing writes superprod rows; `allocate_legacy_output_paths` only names the file; `write_header_only_outputs` in auxiliary_output_service.py:105 writes header only).
- Slot allocation (arrayList82/12/13, text137, GG), template text136, _priceCodes/_productCodes collection: MISSING (auxiliary service takes the code lists as caller input: `write_price_formula`/`write_product_codes` auxiliary_output_service.py:134,137, IMPL for the file write, but not the collection).

## Stage 24: other-language product description (5397-5409)
SQL (5400): `SELECT ShortDescription FROM ProductDescription WITH (NOLOCK) WHERE LanguageId = <_otherlanguageId> AND DescriptionId = <sqlDataReader2.DescriptionId>`. Run only when DescriptionId not DBNull and the item row was new (inside the arrayList8 gate).
Output: if rows and `_languageId != _otherlanguageId`: `writeData(streamWriter4, text3 + "\t" + Component + "\t" + ShortDescription + CRLF, isItem:false)` -> description file.
Defects: query executes even when languages equal (wasted); reader `sqlDataReader5.Read()` result not checked beyond HasRows; no handling of NULL ShortDescription value (ToString gives "").
Python: MISSING (no ProductDescription query anywhere; description output only has path naming + header, auxiliary_output_service.py:105-132). 

## Material rows -> item sheet (5410-5423, unnamed stage 23.x, markers "{4444}")
For each arrayList83 record not in arrayList8 and WITHOUT "#" anywhere: add to arrayList8 and arrayList (item sheet; i.e. generated feature materials are written into the ITEM file, with the 40-column template from stage 22), and description line `text3 \t arrayList84[i] CRLF` to description file if non-empty and languages differ.
Defects: records containing "#" (fabric codes) are silently dropped here (fabric later handled in stage 25 via _convertedList). Description written only when material row is new.
Python: MISSING.

## Stage 25: _convertedList expansion (5428-5745)
Gate: `!_abortThread & !_millerCAD`. Builds `text147` = all materialsWritten joined by CRLF (used in 26b), and a debug log `text148`. For each converted material `_convertedList[i]` (parallel arrays _convertIsFab, _convertIsDepOpt, _convertHasSuperParent, _convertStatus, _convertedDesc, _convertedOtherDesc, _convertOptionId, _convertFeatLen, _convertChildFeatLen):
- Skip (5442) if material contains "--" or (starts with "9-" and _superProductsOnly).
- planflag text152: "yes" default; "no" when !IsFab AND (!IsDepOpt OR (HasSuperParent AND !allowSPoptiondependencies)); `flag19` is hard-coded true, so effectively: "no" for any non-fabric, non-dependent-option material (5450-5454).
- Defaults: type text153 "M", right8 "", right9 "BOC" (brand). If planflag "no": type "P", right8 "", right9 "", feature slot text154 "".
Python: PART. `LegacyMaterialConversionRegistry.add` (material_conversion.py:154) models the registry arrays (material, desc key, status, is_fabric = "#" in material, dependent_option, has_super_parent, feature_position, feature_length, option_id) and its dedupe; `child_feature_length` hard-coded -1 and no `convertStatus` semantic beyond int. The plan flag / type "P"/"M" / brand BOC rule is MISSING. Note Python flags `is_fabric = "#" in material` - legacy fabric flag source is not in this range (UNVERIFIED).

### Stage 26a: fabric material feature slot (5461-5512)
No SQL. For fabric materials: pattern "FAB-F" (or "-HAR-F" if no FAB-F and HAR present); alt `FAB[<ShortProductCode>]-F`; parse two 2-digit ints after the marker (start index and offset; offset at +3 chars), num168=start+offset; text154 = "F"+2digit(num168) + "-0" + featlen where featlen = 7-offset (Knoll 10-offset); if offset==4 and includesCOM -> 4; capped at 5; debug "II" (5495-5511).
Defects: `Substring(IndexOf(...)+len, 2)` throws if marker is at end of string; when neither marker present IndexOf=-1 -> bogus Substring; hard-coded 7/10/4/5 constants.
Python: MISSING.

### Stage 26b: dependent option material feature slot (5513-5610)
SQL (only when option id > -1 and not cached in arrayList33/34): `SELECT SLFeatureLength FROM [Option] WITH (NOLOCK) WHERE OptionId = <_convertOptionId>` (5540). Flatten fabrics hard-codes option ids 8512, 8524, 8624 -> length 8 (5548-5551). Cache arrayList33(length)/34(optionId).
Logic: take material minus first 2 chars; strip `{...}` block; split last "-" token; find last "-F" (index<4 and len>5 -> search after 4); parse 2 ints (start, offset) after it; if not cached length: use _convertChildFeatLen if > -1 else _convertFeatLen; _length5Feats -> 5 if >2; non-Knoll with "-m"/"-c"/ends "-M"/"-C" -> 3; position = "F"+2digit(start+offset)+"-0"+len, via debugFeaturePos. Then search text147 (all prior material rows) for rows beginning `material \t [uniqueComponentsPrefix]F` and collect distinct feature tokens (`text155`, tab separated) (5586-5609).
Defects: `int.Parse(text158.Substring(num171+2,2))` throws on non-numeric; `text161.IndexOf("\t")` can be -1 (throws) inside while; `Substring(text158.LastIndexOf("-"))` throws if no "-" ; reuses `sqlDataReader2` and `text` variables, i.e. CLOBBERS the outer component reader/variable (5541-5547: `sqlDataReader2 = sqlCommand.ExecuteReader()` and Close), which is dangerous because the outer loop's sqlDataReader2 was already closed at 5425 so ok here, but pattern is fragile (UNVERIFIED re outer loop state).
Python: MISSING (`resolve_legacy_feature_length` 376 and sequencer 489 are other stages).

### Stage 26c: other materials (5611-5626)
Take 6-char window around "-05-", then "-04-", then "-03-" (last match wins) as position text154.
Defects: Substring(IndexOf-3,6) throws if index <3. Later overwrite semantics (03 beats 04 beats 05) probably unintended.
Python: MISSING.

After 26 (5627-5649): `text154.Replace(text6+"-","")`; if planflag "no" -> type "P", brand "", slot "". `text155` (slot list) = text154 unless set in 26b; special case for `9-BOCFAB-OF` + `2-HAR-F`: "F04-04" -> "F04-04\tF08-03"; "F10-04" -> "F10-04\tF14-03" (hard-coded).
Python: MISSING (marker string only in legacy_output.py:20 `BOCFAB-OF`/`2-HAR` constants used for the write normalization, not slot generation).

### Stage 27 (5650-5702): slot length constant and BOCFAB fallback
num176 = 7 (8 if includesCOM; Knoll: 10, or 8 if flatten). If text155 empty and material contains "BOCFAB": parse `-F<nn>-<mm>-` -> text155 = "F"+2d(nn+mm) + "-" + 2d(num176-mm), debug "JJ".
Then status (5688-5703): _convertStatus != 1 -> text149 "O"; text150 = 0:"URL", 2:"OBS", 3:"ON HOLD" (other values -> "" ; case 1 -> "A").
Python: status mapping IMPL in item_record_formatter.py:73-77 (same map, but applied to items not materials); BOCFAB fallback MISSING.

### Stage 28 (5704-5745): material row emission to item sheet
syteline row: `material \t no \t desc \t status(A/O) \t statusDesc \t 0 \t 0 \t \t \t ZZ-ZZ \t 0(num179) \t 0(num180) \t yes \t 35 \t 0 \t 0 \t \t \t \t \t DEF \t 1 \t 0 \t EA \t \t type(M/P) \t right8 \t no \t "" \t \t \t brand(BOC/"") \t 0 \t 0 \t \t text155` then 5 more tabs (loop `do..while ≤4`), CRLF. Non-syteline: `material \t no \t desc \t A \t 0 \t ZZ-ZZ \t ""`. `_formatCSI`: uses `formatCSIData(...)` instead (UNVERIFIED body). `_flattenFabrics` and row starts "9-FAB-F": shorten key to first 5 chars + last "-x" segment when last "-" index >5 (5725-5737).
Emit: logMessage {5555}; `arrayList.Add(text167)` (item sheet; NO dedupe vs arrayList8 here); other-language desc to description file `text3 \t material \t otherDesc` when non-empty and languages differ.
Defects: no dedupe gate; material rows go to the ITEM file (with `9-` style codes); the `text155` slot list can contain several tab-separated slots so column count varies; flatten shortening can create colliding keys (UNVERIFIED).
Python: DIFF/MISSING. Only `normalize_legacy_record` (legacy_output.py:79) reproduces the late `HAR-F`->`H-F` and `-BOCFAB-`->`-` rewrite that happens in writeData (not in this range). CSI formatter MISSING; fabric flatten of the row key is only in `normalize_legacy_option_report_rows(flatten_fabrics)` for option values (material_conversion.py:39,58), a different place.

---------------------------------------------------------------------
## Stage "POST" / 29: additional-materials post-processing (5746-6171)
Entry condition (5749-5751): `!_formatCSI & _syteline`; `_catalogueId != 229` -> general path (stages 30-34); `== 229` -> HRB path. Else nothing.
`arrayList93` = working copy of the item sheet (arrayList), `arrayList94` = working copy of material sheet (arrayList2), both lazily cloned on first use.

### Stage 30a-30c: parse materialsWritten (5758-5790)
For each materialsWritten row (tab fields: parent[172], component[173]? see below). Vars: text172 = parent item, text173 = feature/field2, text174 = component material, text175 = opt code, text176..text178 = qty/price fields, text179 = next field (seq/backflush). Order = first 8 TAB fields. UpdateStatusLabel event raised per row with "matl: x (n of N)".
Skip rows where parent starts "AX" and contains "OX" (5787-5794).
Defects: any malformed row (fewer than 7 tabs) throws ArgumentOutOfRange; UI status invoked in loop for every material (perf, thread marshaling UNVERIFIED).
### Stage 30d/30e: dependent fabric-style parent lookup (5795-5834)
Condition: component text174 contains `-<text6>-`. value7 = text174 up to last "-"; text180 = code after last "-". Loop cached lists (arrayList95 = checked components, arrayList96 = lists of dependent codes): if a cached dependent-code list contains text180 (ignoring "#"), and the cached component does not start with value7, and pair (parent_cached) not used -> text170 = cached component (record used pair in arrayList97).
SQL 30e (5822), only if text170 still empty and component not cached:
`SELECT DISTINCT optval.OrderCodeValue FROM OptionValue optval WITH (NOLOCK) JOIN DependentOptionValues dov ON optval.OptionValueId=dov.AdditionalOptionValueId JOIN OptionValue parent_optval ON dov.OptionValueId=parent_optval.OptionValueId WHERE parent_optval.OrderCodeValue='<text180>#' AND optval.OrderCodeValue LIKE '%#'`.
Defects: string-concatenated SQL with text180 from data (SQL injection / apostrophes break); REUSES `sqlDataReader`/`sqlConnection` which is the OUTER item reader (closed at 5427 so ok) - but note same object reassigned.
### Stage 30f (5835-5902): remap parent for dependent materials
When text170 found: clone arrayList->93 and arrayList2->94 if empty. Find item row in 93 starting `text170\t`; if it contains "BOC": featpos = text174 minus `9-text6-` minus `-text175` (ZZ debug); if BOC tail lacks featpos, find last "F" token in tail and replace `Ftoken\t\t` with `Ftoken\tfeatpos\t` (adds slot). In 94 find the row starting `text170\ttext173\ttext174\ttext175\t` and replace the legacy row's parent/text179 with `text170 ... \t1` (sets last column to 1).
Defects: string Replace rather than positional edit may alter multiple rows; the `Substring(0, text183.IndexOf("\t"))` can throw.
### Stage 31 (5903-5907): if text170 found -> `continue` (skip fabric-colour logic).
### Stage 32a-32.9 (5908-6082): skipped-fabric-colours remap
For each `skippedFabricColours` entry "x|code[~n][:altOpt]": code length <4 and material ends with "-code" and material does NOT contain `-text6-`; only when material contains "-F01-" and n==1; itemHasFabrics must contain the item part (9-ITEM-...) else skip. New key text188 = "9-"+text6+"-F01-"+len(code)(2d)+"-"+code. Replace material key in arrayList94 row `parent\ttext173\ttext174\ttext175\t...` with text188; remember text174 in arrayList98 once; if `arrayList93.IndexOf(text174+"\t") > -1` (NOTE: ArrayList.IndexOf on an object equals-match of a full string, so it is -1 unless an element equals exactly text174+"\t": appears to be a logic bug, the StartsWith loop at 6018 is never reached in most cases - UNVERIFIED how often) compute slot text189 ("F"+2d(a+b)+"-05", "KK"/"kk" debug), find item row starting text174\t in arrayList93, and for BOC rows add the slot like 30f; otherwise replace the P-template tail `DEF\t1\t0\tEA\t\tP\t\tno\t\t\t\t\t0\t0\t\t\t` with the M/BOC tail `DEF\t1\t0\tEA\t\tM\t\tno\t\t\t\tBOC\t0\t0\t\t<slot>\t` and key text188.
Defects: `ArrayList.IndexOf(string)` used as a "contains-prefix" test (6000, 5998); O(n^2) scans over arrays with stage name set per iteration (threadStage string churn); `int.Parse(text185.Substring(~))` may throw; literal-string tail matching is brittle to any column change (e.g. adding a column breaks it silently).
### Stage 33 / 33.5 (6084-6137): dedupe and flatten
arrayList102 = copy of arrayList94 (or materialsWritten if 94 empty); each element CR/LF-stripped and tab-trimmed; if new it is ADDED to arrayList94 (the same list being cloned from). Result: arrayList94 contains the original (CRLF-bearing / untrimmed) rows AND the trimmed copies; both survive until the exact-string `_additionalMaterialsWritten` check at 34 (different strings) -> duplicates unless writeData dedupes later (UNVERIFIED).
33.5: if _flattenFabrics, rewrite "9-FAB-F..." key: first 5 chars + last "-" segment when last "-" index > 5.
### Stage 34 (6138-6170): publish additional rows
arrayList93 rows not in `_additionalItemsWritten` (cross-item set) are added to it, to `arrayList` (item sheet) and log "{POST}". arrayList94 rows not in `_additionalMaterialsWritten` become the NEW `arrayList2` (material sheet for this item; resets arrayList2).
Defects: arrayList93 is a full clone of the item sheet, so unchanged rows are re-added to `arrayList` unless already in `_additionalItemsWritten` (only added once, but the second copy of this item's own rows is already in `arrayList`) -> duplicates of every item row (UNVERIFIED if writeData `isItem` dedupe at the end removes them; Python's accept() does for exact strings). arrayList2 is only replaced when arrayList94 non-empty. Output variables text202/text204 built but unused.
Python: stages 29-34 MISSING entirely (no `skippedFabricColours`, `itemHasFabrics`, `_additionalItemsWritten`, `_additionalMaterialsWritten`, dependent-fabric SQL, F01 remap). `LegacyRecordDeduplicator` only models writeData dedupe.

## HRB branch: catalogue 229 (6172-6324, threadStage "HRB")
No SQL. Operates on materialsWritten rows (parent text209, component text210, text211 (feature field), text212 (qty/field 4)).
- Parent starting "OF" tracked as text207; list arrayList108 cleared on change of OF parent.
- text210 normalized: remove `parent-` and `bocfab-`.
- If component starts "HAR-": if contains F01-03 or F07-03: register text211 in arrayList104 (+text212 in arrayList106) and arrayList108; else register `OFparent~text211` in arrayList105 (+qty arrayList107). Header line "Parent Item\tFeature\tComponent\tOpt code\tInc. price\tMatl Qty\tScrap fact\tSeq\tEffect Date\tObs Date\tOper Num\tBackFlush" added to arrayList103 once (6230) as first row.
- If arrayList108 non-empty and header exists: rewrite row (a) F01-03/F07-03: drop parent prefix on component, qty `...\t1\t0` -> `0\t1\t0`; (b) `bocfab-HAR-F08-03`/`F14-03`: replace parent+component with `arrayList108[0]\tHAR-F08-03` etc., `qty\t0\t0` -> `qty\t1\t0`, last field reduced by arrayList108.Count (`int.Parse` of last tab field); then `\tHAR-F` -> `\tF`, remove `-text6-` and `-BOCFAB-`; add to arrayList103. Else row appended to text206.
- text206 rows (split on '\r', reversed insertion at index 1, order preserved but elements keep leading '\n') inserted after the header.
- If arrayList104 and arrayList103 non-empty: arrayList2 = arrayList103 with `HAR-F`->`H-F`, `-bocfab-`->`-BOCFAB-`; then for each arrayList104[1..] (index 0 skipped) cross-join arrayList105 entries whose key starts with the parent short code: new row `feature \t HARpart \t component \t lastSegment \t min(qty) \t 1 \t 0 \t (index+102) \t \t \t 10 \t`, apply BOCFAB-OF/2-HAR key shortening, same replacements, appended to arrayList2.
Defects: `for num234 = 1` skips arrayList104[0] (probably an off-by-one, or intentional because [0] is the header-ish first; UNVERIFIED); `Substring(IndexOf)` chains throw on malformed rows; `double.Parse` of qty; literal sequence `num236+102` ties numbering to arrayList105 order; header row is injected into the material sheet (arrayList2) so downstream writers must tolerate a header line; `text215` lookup `Replace("\t\t\t10\t","")` brittle; leading "\n" artefacts from Split('\r').
Python: MISSING. Only constants `BOCFAB-OF` and `2-HAR` (legacy_output.py:20-22) and the `-BOCFAB-`->`-`, `HAR-F`->`H-F` writeData replacement (legacy_output.py:79-83) exist, which duplicate only the last replacements (the writer-level ones, whose legacy location is outside this range, UNVERIFIED). Catalogue-229 handling does not exist (no `229` reference in the port).

## Stage 35 beginning (6326-6353, partially in range; continues beyond 6330)
`if _uniqueComponents`: for each item-sheet row: text222 = key before first "-" (strip leading "9-"); if row contains `\t<text222>-` replace with `\t`; if _plcPhantoms and row contains `\t[` strip `[x]-`; special-case 9-FLC row with `0\t0\t\tF07-03\tF10-03` (continues past 6353; UNVERIFIED rest).
Python: MISSING (no `_uniqueComponents`/`_plcPhantoms` usage; config has flags? only `flatten_fabrics` found by grep in config.py:121 - other flags are parsed in config.py UNVERIFIED by me).

---------------------------------------------------------------------
## Cross-cutting legacy defects (this range)
1. Hard-coded magic numbers/ids: option ids 8512/8524/8624, CM01#, "F04-04"/"F10-04" special slots, 102 seq base, 7/8/10/5/4 slot lengths.
2. Tail-string `Replace`/`StartsWith`/`IndexOf` editing of tab-delimited records in 30f/32 (brittle; ArrayList.IndexOf misuse at 5998/6000).
3. Unprotected Substring/int.Parse/double.Parse across 26a-26c, 30, HRB (throws on edge data; no try/catch in range, error surfaces as global stage-tag via SytelineExport.threadStage).
4. SQL built by string concatenation (30e uses data value; others ints).
5. Reader/Command reuse of outer variables (sqlDataReader, sqlDataReader2, text) in nested SQL; readers never in `using`.
6. Duplicate generation: arrayList93 clone re-added (34), arrayList94 appended while cloned (33).
7. Only first-option-value length/IsFabric used per option (22).
8. `flag19` constant true; `_convertedList` indexOf "indexof" late-bound call.
9. writeToStream called with a junk tag "gggggg" (debug).

## Port-gap summary (this range)
| Stage | Capability | Python |
|---|---|---|
| 22 | option value query, feature lengths, X template, material 40-col row | MISSING (stage 20 length helper DIFFERS) |
| 23.1 | superprod file row | MISSING |
| 23.3 | item row + slot allocation + price codes | PART/DIFF (`format_syteline_item_record`, 2 column-count differences) |
| 24 | other-language ProductDescription | MISSING |
| 25-28 | convertedList -> material rows, slots, status, CSI, flatten | PART (registry), rest MISSING |
| 29-34 | additional-materials post-processing | MISSING |
| HRB | cat 229 | MISSING |
| 35 | unique components/PLC phantoms | MISSING |


# Part E


Source: C:\Users\siaoca\Desktop\PDM\PDMMaintenance\ExportThread.cs (read in full, 6330-7483; helpers ConvertToXLS 524-707, writePriceFormulaData 986-1036, writeProductCodeData 1038-1088 also read for context).
Ports: C:\01 Projects\mk_product_workbench\services\syteline_export\*.py (all 9 files; only legacy_output.py, auxiliary_output_service.py, config.py, material_conversion.py are relevant here).
Vocabulary: arrayList = sheet1Data (Items rows, tab-joined strings); arrayList2 = sheet2Data (Materials rows); arrayList109 = temp "extra rows" list; arrayList93 = existing item rows (item-tab lookup); flag2 = (unnamed; gates a catalogue-specific block at 6783 -- UNVERIFIED which catalogue, set earlier than 6330).

Port verdict summary: NONE of stages 35-42 string post-processing, fabric expansion (37/38), item-row feature-column repacking (39), BOM generation (40/41), item/material file writing with dedup, XLS conversion, or ExtractUser release is implemented in the Python package. Only the per-record writer helpers (legacy_output.py) and the price-formula / product-code writers (auxiliary_output_service.py) exist, as standalone units not wired to any execThread equivalent. There is NO export orchestrator in the Python port (no thread, status, abort, timer, completion, or catch-all).

---------------------------------------------------------------------
## Stage "35" tail (6330-6406) - material/item row clean-up of generated rows
Capability: normalize generated item rows (arrayList) and material rows (arrayList2) by stripping redundant parent prefixes from component codes; phantom-bracket stripping; hard-coded catalogue patches; append staged extras.
- Block 6330-6396 (enclosing `if` begins before 6330 -- UNVERIFIED condition, likely a catalogue/format flag).
  - Item rows (6331-6358): key = text before first tab. If key starts "9-": drop "9-", then cut at next "-" (so "9-ABC-F01-03" -> "ABC"). If row contains "\t<key>-" replace with "\t" (removes "<key>-" prefix from the next fields). If `_plcPhantoms` and row contains "\t[": take text between "\t[" and "]" and replace "\t[x]-" with "\t". Special: row containing "9-FLC" AND "0\t0\t\tF07-03\tF10-03" -> "0\t0\t\tF04-03\tF10-03" (hard-coded FLC feature-position rewrite).
  - Material rows (6359-6387): same prefix logic; if row starts "9-FLC" AND contains "-F01-03-" AND "\tF07-03" -> "-F01-03-" becomes "-F04-03-".
  - 6388-6395: if arrayList109 non-empty, append all its rows to arrayList2 (materials). (arrayList109 content origin earlier -- UNVERIFIED.)
- 6397-6406 (unconditional): item rows starting "CQND58" with "F01-03\tF10-07" -> "F01-03\tF07-03\tF10-07".
- Errors: none locally; any substring/IndexOf exception falls to the global catch (6432). `text221.Substring(0, IndexOf("\t"))` throws ArgumentOutOfRange if a row has no tab (legacy defect: whole export aborts on a malformed row).
- Defects: string-level patching of tab-joined records by position text is fragile; `Replace` hits all occurrences; `text223.Substring(0, IndexOf("]"))` throws if "]" missing (6349, 6378). The key-prefix removal `Replace("\t"+key+"-","\t")` also mutates unrelated later columns.
- Python: MISSING. No equivalent in any file (grep for FLC/CQND58/plcPhantoms: no hits).

## Stage "35.1" (6407-6472) - Beck/Nico CRB "c" variants
- 6409-6419: scans arrayList for rows starting MG1/SR1/SR2/SR3/SR4 setting flag24, then **`flag24 = false;` at 6419 unconditionally overwrites it** -> the whole CRB duplication blocks (6420-6436, 6445-6472) are dead code. APPARENT LEGACY DEFECT / intentionally disabled. A port should NOT implement the body (behavior = no-op) but must record this.
- Live part: arrayList109 reset to empty (6408); 6437-6444 appends arrayList109 to arrayList (always empty -> no-op).
- Dead body (for reference only): "9-BOCFAB" rows with -ZB3\t / -ZNC\t cloned with "-ZB3c"/"-ZNCc" and "Beck (CRB) ZB3"/"Nico (CRB) ZNC"; material rows renamed analogously.
- Python: n/a (correctly absent); no doc note of dead-code status. UNVERIFIED that no other code sets flag24 between 6419 and 6420 (none seen).

## Stage "36" (6473-6492) - debug dialogs + init of fabric sequence vars
- 6474-6485: if debugIncrements / debugItemFeatureTemplateResolutionForMaterials -> modal debug_form ShowDialog (blocking; with `_runAsService` this would hang a service -- legacy defect; no `_runAsService` guard).
- 6486-6491: text231 = "2" (sequence string; "<default>2" in debugMaterialSequence); right10 = "" (last-material key).
- Gate for fabric expansion (6492): `!_formatCSI && text5 == "yes"` (text5 = fabric flag; origin UNVERIFIED, before 6330).
- Python: MISSING (no fabric-skip list, no debug facility; debug dialogs correctly not needed in a port, but no equivalent logging hook).

## Stages "37.i-N", "37.i-N.j~k", "38.i", "38.i.j-M" (6511-6779) - generate fabric colour materials from skippedFabricColours
Capability: for each skipped fabric colour entry "x|code[:desc~...]" generate 9-FAB-<code> material rows (arrayList2), and matching item rows (arrayList, 9-FAB item definitions) when not already present.
Inputs: skippedFabricColours (list of "prefix|CODE[:name~..]"), allSPFabricColours/allSPFabricColourCodes/allSPFabricColourSequences (per feature-position key sequence trackers), allFabricColours/allFabricColourSequences (global sequences), arrayList93 (existing item rows), text6 (superproduct short code), _catalogueId, _additionalMaterialsWritten/_additionalItemsWritten (HashSet-like dedupe), arrayList110 (local "done" list).
Logic:
1. Per entry (6516-6772): skip entries without "|" (6520). code = part after "|"; if has ":" split -> text234 = code, text235 = display name (up to "~"). Skip if "9-FAB-"+code already in arrayList110 ("IGNORING", 6770) -- NOTE arrayList110 only ever receives *material row strings* (6729), never "9-FAB-<code>" strings, so this de-dup check at 6535 never triggers -> APPARENT DEFECT (dedup is actually done by _additionalMaterialsWritten at 6725). Skip codes shorter than 4 chars (6538).
2. Parent code search (6545-6568): scans all entries for shorter codes that are prefixes of this code; keeps LAST such prefix (text236) and counts matches (num264). If none, parent = code minus last 2 chars, count=1 (6572). Loop runs once per matching parent (6576).
3. Feature position (6580-6608): text240 = "9-"+text6+"-"; width num269 = len(parent) (3 for "CM0100" 6582); num260 is a monotonic running MAX of widths across ALL entries (never reset per entry; declared 6512, initial 2) -> later entries inherit earlier widths: order-dependent output (likely defect, UNVERIFIED if intentional). `getParentStartPos("9-"+text6, parent, reverse(j>1), ref parentlength, ref substituted)` (defined elsewhere; not in this range) supplies start pos and may substitute the option code. featpos = "F"+pos(00)+"-"+width(00), passed through SytelineExport.debugPostProcessedFeaturePos(...,"LL") (debug hook; no-op unless debug), text240 += featpos+"-"+parent+"\t".
4. Sequence number (6609-6691), two branches on text240 != right10 (last key):
   - New key: seq reset "2". Look up key in allSPFabricColours; if absent, add (codes list [code], sequence 2). If present: `NewLateBinding LateGet Contains(code)`; if code NOT in the list, append and increment stored sequence, seq = stored. Note `if (array4[0])` by-ref copy-back replaces text234 with the value returned from the by-ref array (harmless).
   - Same key as previous: if absent: strip leading "<...>" debug prefix, `int.Parse(seq)+1` (INC_2). If present and code not listed: add code, ++sequence, seq=stored.
   right10 = text240 (6692). If the code IS already in the list, seq is unchanged (duplicates reuse seq).
   Progress: threadStage "38.i"; UpdateStatusLabel "fabric: i+1 of N" (6694).
5. Material row (6695-6722): second feature pos "F"+(parentStartPos+num260)(00)+"-"+(num259-num260)(00); num259 = 10 for Knoll catalogues (SytelineCSIExport.IsKnollCatalogue(_catalogueId)), else 8 when num260==4, else keeps previous (initial 7; sticky across iterations -> defect-prone). Fed through debugPostProcessedFeaturePos(...,"MM"). Row = parentRow + feat2 + "\t" + "9-FAB-"+code + "\t" + code.Substring(len(parent)) + "\t" + "0" (price inc) + "\t1\t0\t" + seq + "\t\t\t10". If allFabricColours already has "9-FAB-"+code, seq is OVERRIDDEN with the global stored sequence (6710-6714).
   - Excluded when row contains "9-FAB-CM01\t" (6723/6764 "EXCLUDED: 9-FAB-CM01" -- debug only).
   - Added to arrayList2 only if not in _additionalMaterialsWritten (6725); recorded in set and arrayList110.
6. Item row for the fabric (6731-6743, 6744-6760): fixed ~190-column template: `9-FAB-code\tno\t<code>|<name>\tA\t\t0\t0\t\t\tZZ-ZZ\t0\t0\tyes\t35\t0\t0\t\t\t\tDEF\t1\t0\tEA\t\tP\t\tno\t\t\t\t\t0\t0\t\t` + 20 empty feature columns + 3 trailing tabs. Added to arrayList only when no existing arrayList93 row starts with "9-FAB-code\t" AND not already in _additionalItemsWritten; logMessage("{6666} sheet1Data.Add(...)").
- Debug: debugSkippedFabricColours builds text232 and ShowDialog (blocking) pre/post (6495-6510, 6773-6778).
- Errors: `int.Parse(text231)` (6660) throws FormatException if seq contains non-digit (e.g. when `<...>` prefix handling fails); `Substring(text236.Length)` (6719) throws if code shorter than parent. All go to global catch -> abort (see below).
- Defects: arrayList110 dedup by wrong key (above); num260/num259 sticky state; nested linear scans O(n^2..n^3); dependency on `text5=="yes"` string flag.
- Python: MISSING. material_conversion.py has `LegacyMaterialConversionRegistry`, `LegacyDependencyMaterialSequencer` (9- sequences start at 2, +1 per repeat; differs: legacy increments only when a *new code* joins the key's list, port increments per call) and `resolve_legacy_feature_length` (stage 20), but nothing for fabric colour expansion, F-position construction, Knoll width 10/8 rule, FAB item-row template, CM01 exclusion, or sticky widths.

## Stage "39" (6780-6883) - catalogue patches, CN1 patches, item-row feature-column repack
- 6783-6803 `if (flag2)` (UNVERIFIED which condition; defined before 6330): on every item row: F23-02->F23-03; F25-05->F26-04; several multi-feature tab sequences collapsed ("F01-03\tF04-03\tF07-03\tF10-03\tF13-03\tF23-03" -> "F01-03\tF04-03\tF13-03\tF23-03\t\t\t", similarly F16-05 variants, F04/F13/F16-05 variants); "\t\tF16-07\t" -> "\t\tF07-03\tF16-07"; "\t\tF21-07\t" -> "\t\tF07-03\tF16-05\tF21-07"; "\t\tF16-05\tF21-07\t" -> ... On material rows: F23-02->F23-03; **F25-04->F26-04** (note item rows use F25-05 but material rows F25-04 -- possible typo/defect, UNVERIFIED).
- 6805-6812: item rows containing 9-CN1G/9-CN1L/9-CN1R AND "-F05-03-" AND "F08-03" but NOT "F14-03": "F08-03\t" -> "F08-03\tF14-03" (note: inserts F14-03 without a trailing tab -> merges with next column text; likely defect, UNVERIFIED because the consuming split at 6848 still counts tabs). The odd late-bound `.indexof` call is VB late binding, case-insensitive.
- 6813-6883 REPACK of every item row (`continue` if row starts with tab, 6818): key = first field. Scan ALL material rows (arrayList2) with that parent; collect distinct 2nd-field feature codes in order (text246, count num285) -> O(items x materials). Then split item row: first 34 tab-separated fields kept (text248; do-while up to 34, `if flag25` = fewer than 34 tabs -> row left UNCHANGED, 6859); skip the next up-to-20 feature columns (6864-6872); remaining tail text249 = remainder; new row = first 34 fields + feature codes from materials + padding tabs up to 20 columns (loop from num285+2 to 20, i.e. 21-num285-... adds tabs) + tail. => Item feature columns (Feat1..Feat20) are REBUILT from the material tab's feature codes, overwriting earlier feature positions. UNVERIFIED: exact off-by-one in padding (loop `num285+2..20` inserts 19-num285 tabs while the code list already ends with one tab per feature; verify with real output; if num285>=20 no padding and >20 features silently overflow into tail columns).
- Defects: no cap on feature count > 20 (overflow shifts later columns); 34-field/20-feature layout assumed for both CSI and non-CSI formats.
- Python: MISSING. config.py only lists headers for aux files; item row layout is not defined anywhere (config.py comment: "item schema deliberately not guessed").

## Stages "40" / "41" (6884-7032) - BOM data generation (only when `!_formatCSI && _exportBOMData`)
Capability: tag each material row with the option-value id so SytelineBOMExport.generateBOMData can build BOM sheets.
Per material row (arrayList2), build parallel lists arrayList114 (item label), arrayList115 (OptionValueId) :
- Parse parent: first field; if contains "BOCFAB" -> text14 (the superproduct item; origin UNVERIFIED); else if starts "9-" take second hyphen segment (6904-6910). Parse fields: opt code (3rd, text254; if 3rd field contains "9-FAB-" opt code = it minus "9-FAB-"), price increment (5th field, `double.Parse` 6929 -- throws FormatException/OverflowException on non-numeric; culture-sensitive), feature field text252.
- Stage 40 SQL (6940): `SELECT ItemId FROM Item WHERE Item = '<text253>'` (string concatenation, SQL-injection/quote bug: item codes with `'` break). Reads all rows, last wins. If not found (-1): modal debug_form "unable to establish itemId for [..]" (6007-6009) and CONTINUES (value12 "[undefined]", id -1) -- blocks in service mode.
- Stage 41: when parent changes (left14 != parent) calls stored proc `PDMOptionDataReportWithIncBase(@item = parent, @siteId = _siteId)` (CommandType.StoredProcedure, 6956-6975; the `text258` string is unused). Result columns: OptionValueId (int), OrderCodeValue2, IncPriceBase (blank -> 0). Lists arrayList116/117/118 cached per parent (only valid when consecutive rows share a parent; rows are NOT sorted by parent -> repeated proc calls, perf defect).
- Match (6978-6998): two passes: opt code equals OrderCodeValue2; second pass also tries code+"#"; AND price equals IncPriceBase (`ConditionalCompareObjectEqual(double, boxed int/double)` -- float equality). Hit -> label = parent item and OptionValueId; miss -> "[undefined]" and -1. `left14 = text253` set only when itemId found (so repeated debug dialogs for a missing item).
- Rows whose feature field contains "9-FAB-" get label "[generic]" (7012-7015); always append arrayList115 value (7020).
- Then `new SytelineBOMExport{sheet1Data,sheet2Data,sheet2Items,sheet2OptValIds}.generateBOMData()`; if returns true, sheet1Data/sheet2Data replaced by its output (7027-7031); if false, silently keeps originals. generateBOMData's behavior is outside this range (UNVERIFIED).
- Errors: exceptions -> global catch. Cursors closed manually (no using) -> leak on exception (connections closed in finally). sqlConnection2 used.
- Python: MISSING entirely (no proc call, no ItemId lookup, no BOM generator). Only `normalize_legacy_option_report_rows` ports part of a *different* option-report SELECT.

## Item file write (inside try at 7033-7370) - `_itemFile`
- `new StreamWriter(_itemFile, append:false)` (7036): default encoding UTF-8 without BOM in .NET StreamWriter(string) ctor; line endings written explicitly "\r\n". Overwrites the file.
- Header (skipped when `_millerCAD`): if `_syteline`:
  - `_formatCSI`: 206-ish column CSI item header list (7044-7253, "Item","Description","Revision",... "C(IsBOMExistedStatic)"; includes duplicate names "Attribute Group" x2, "Tax Mode" x2, "Source" x2, "Country" and "Country Of Origin"). Exact count not asserted (UNVERIFIED count; ~210 by line span).
  - non-CSI: "Item","Super Prod","Description","Status","Reason Code","Eurobase","Cost","Curr","Vendor","P/L","Cube","Weight","Stocked","Lead Time","Pre-EngineeringLeadtime","Pre-ProductionLeadtime","Drawing","Handbook","CNCItem","Planner","Days supply","Man Offset","UM","Commodity Code","P/M","Manu Master","Phantom","Template","ECO no.","ECO date","Work Centre","Queue","Run time","Family Code","Feat1".."Feat20","Height","Width","Depth","DockToStock","Feature String","ItemType","Modvatable","Design Source","Mfg Part Number","Mfg Part Drawing Number","Mfg Part Revision","HSN Code","Sequencing Material","Board Store Type","Grained","Material Origin","Material Type","NCM","Gender","Item Notes","Back Flush","Backflush Locn","Alternate Item","Order Minimum","Order Multiple","Carton/Box Counting","Enabled Roundup Control","Issue UOM Precision","One Off Product","Jig/Hole Requirements","Oke Programme" (7257-7328). Total = 34 + 20 + 34-ish; non-CSI Feat20 ends at column 54; confirms 34 fixed fields before Feat1 as assumed in stage 39.
  - Each header cell written via `writeData(..., isItem:false)` separated by "\t" via writeData, newline "\r\n". (writeData applies dedupe + legacy char filtering; see legacy_output.py.)
  - non-SyteLine branch (7343): "Item\tSuper Prod\tDescription\tStatus\tEurobase\tP/L\tPriceCode\r\n".
- Rows (7346-7358): dedupe by `removeNonAlphaNumeric(row)` (so rows differing only in punctuation/whitespace/tabs are treated as duplicates and the later one dropped -- potentially lossy: e.g. rows differing only by tab placement, or by "-" characters, collapse. APPARENT DEFECT/quirk, O(n^2) via ArrayList.Contains); blank rows (Trim()=="") skipped but still added to seen list; written via `writeToStream(sw, row+"\r\n","sheet1Data")` (which does the legacy nonstandard-character filter).
- Error handling (7360-7366): catch Exception -> modal `Interaction.MsgBox("myWriter1 error: " + ex)` (blocking, even in `_runAsService` mode) and continue; finally closes writer. The export then proceeds as if successful (no abort flag, no failure status) -> a truncated item file can ship and "Export Complete" is reported. DEFECT.
- Python: PARTIAL. legacy_output.py implements path allocation (`allocate_legacy_output_paths`: temp\{name}_item_data[_csi].txt etc.), char filter (`remove_legacy_nonstandard_characters`, `normalize_legacy_record`) and `LegacyRecordDeduplicator` (the writeData two-level dedupe). MISSING: the item header lists (CSI and non-CSI; config.py explicitly omits item), the removeNonAlphaNumeric-based row dedupe + blank skip, header written through writeData (so a header row can itself be de-duped/filtered), the myWriter1 error reporting, and no `_millerCAD` header suppression. DIFFERS: `parse_legacy_tsv` accepts an empty item file as valid, whereas legacy always writes a header (non-millerCAD).

## Material file write (7371-7404) - `_materialFile`
- Same try/catch/finally pattern, "myWriter2 error: ". Header (skipped for `_millerCAD`) written through writeToStream: "Parent Item\tFeature\tComponent\tOpt code\tInc. price\tMatl Qty\tScrap fact\tSeq\tEffect Date\tObs Date\tOper Num\tBackFlush". Rows deduped via removeNonAlphaNumeric(row) with the same blank-skip, written as row+"\r\n" via writeToStream("sheet2Data"). (`text259` is always "" -- vestigial.)
- Python: PARTIAL. Header matches config.py LEGACY_TSV_HEADERS["material"] exactly (verified word-for-word). Row-writing/dedupe by removeNonAlphaNumeric: MISSING. Error reporting: MISSING.
- Note: items header goes through writeData while material header goes through writeToStream -- different filter/dedupe paths (a legacy inconsistency).

## Post-write (7405-7430)
- 7405-7406: close streamWriter2 and streamWriter4 (the superprod and description/planning writers opened earlier -- exact identities UNVERIFIED since they are declared before 6330). streamWriter3 closed only in finally (7458).
- 7407-7413 `if (!_abortThread & !_millerCAD)` (non-short-circuit `&`, both evaluated): `writePriceFormulaData()`, `writeProductCodeData()`, status "Exporting to Excel", `ConvertToXLS()`.
  - writePriceFormulaData (986): opens its own connection; ALWAYS writes header "Site\tCustPriceCode\tItemPriceCode\tPriceFormula\tPriceFactor\tEffectiveDate\r\n"; if `_priceCodes` non-empty runs `SELECT Site.Site, pm.CustPriceCode, pm.ItemPriceCode, pf.PriceFormula, pf.FirstPrice, CONVERT(VARCHAR(11), pf.EffectiveDate, 106) AS EffDate FROM PriceFormula pf WITH (NOLOCK) INNER JOIN PriceMatrix pm ON pf.PriceFormula = pm.PriceFormula INNER JOIN Site ON pf.SiteId = Site.SiteId WHERE Site.SiteId = <siteId> AND (pm.ItemPriceCode = '..' OR ...) ORDER BY pm.CustPriceCode, pf.EffectiveDate DESC` (string-built, un-escaped). Error -> modal MsgBox(ex) and continue.
  - writeProductCodeData (1038): header "Site\tProductCode\tDescription\tPriceCode\tUnitCode" but rows only 4 values; SQL `SELECT Site.Site, pc.Product_Code, pc.Description, pc.PriceCode FROM Product_Code pc WITH (NOLOCK) INNER JOIN Site ... WHERE Site.SiteId=<siteId> AND (pc.Product_Code='..' OR ...) ORDER BY pc.Product_Code`. Same error handling.
  - ConvertToXLS (524): launches Excel COM (CLSID 00024500-...), invisible, DisplayAlerts off, builds workbook: SyteLine non-CSI -> sheets "Descriptions","Planning Data","SPextract" (from superprod/planning/description files); non-SyteLine -> "SPextract","ProductCode","PriceFormula"; always "Materials" (material file split on '\n') and "Items" (item file split on '\n') via WriteToSheet (helper not in range); autofit; deletes default "Sheet1"; if `<exportDir><exportFileName>.xls` exists it is `Kill`ed ("deleting prev instance"), status "saving file as xls", SaveAs. Note SyteLine CSI mode produces only Items+Materials sheets. Errors: MsgBox("ERROR during XLS export"); finally releases COM sheets/workbook (swallowed), `Quit` and ReleaseComObject on app (NOT in try -> NRE possible if Excel failed to start, masks original error), GC.Collect. Requires Excel installed; not available on service hosts -- XLS failure does not change completion status.
  - The `item_file`/`material_file` streams are read in ConvertToXLS via `new StreamReader` that are re-assigned without closing the first (leak of handle on _itemFile until finalizer -> `FileSystem.Kill`/overwrite issues).
- Python: PARTIAL/DIFFERS. auxiliary_output_service.py: `price_formula_rows` and `product_code_rows` reproduce both SELECTs (same columns, joins, NOLOCK, ORDER BY) but use parameterized `IN (?)` instead of OR-concatenation (improvement; equivalent), dedupe+strip codes, raise ValueError if site_id<1 (legacy would just run), return [] for no codes. `_write_tsv` writes header always and rows `\r\n`, UTF-8, atomic temp+replace (differs: legacy non-atomic, truncating). PRODUCT_CODE_HEADER keeps 5 columns / 4 data values (matches legacy). EffDate: Python writes SQL-produced string (style 106 `dd mon yyyy`) as-is = same. MISSING: XLS conversion (no .xls/.xlsx writer in package; grep `xls` shows only unrelated scripts), the `_abortThread`/`_millerCAD` gating, status messages ("Exporting to Excel"), delete-prev-xls, and the price-code/product-code *collection* (`_priceCodes`/`_productCodes` are inputs the caller must supply; nothing derives them from item rows). `write_header_only_outputs` correctly writes planning + description header-only files (matches legacy that never writes data rows; headers per config.py; legacy header literals for these are in code before 6330 -- UNVERIFIED here).

## Completion / abort reporting (7414-7430)
- `UpdateExportTimer?.Invoke(this,"stop")`.
- If `_abortThread` (set by UI cancel; checked ONLY here and at 7407 in this range -- earlier stages may check it, UNVERIFIED; during stages 35-41 and file writes there is NO cancellation check, so Cancel is ignored until writing finishes): status "Export Aborted"; if `!_runAsService` modal MsgBox "PDM Data Export Aborted" (title "Export Aborted", SystemModal). Note when aborted the item/material files are still fully written and left on disk (no cleanup/deletion of partial output).
- Else status "Export Complete"; MsgBox "PDM Data Export Complete" only if `!_runAsService && _parent.currentExportQueue.Count == 0` (so no popup mid-queue).
- Python: MISSING (no abort flag, status events, queue, or service flag).

## Global catch (7432-7454)
- Any exception in the whole execThread try (not only this range): builds debug text = ex.ToString + "\r\n\r\n" + threadStage + "\r\n\r\n" + text (text = last SQL statement) [+ text8 (increments debug) if debugIncrements]; `debug_form14.ShowDialog()` -- MODAL, blocks the worker thread until closed, even when `_runAsService` (service deadlock; legacy defect). Then timer "stop"; if `_runAsService` status "Export ERROR" else MsgBox "PDM Data Export Aborted" (title "Export Aborted"). The message to the user does not state error; the details are in the debug form only. ProjectData.ClearProjectError.
- No retry anywhere; no partial-output cleanup; no log write besides logMessage in specific spots; failed export in service mode yields only status label (no exit code propagated -- UNVERIFIED how the caller reads status).
- threadStage strings (e.g. "38.4.7-120") are the only progress/diagnostic location markers; set globally on SytelineExport (static, shared by all threads -> racy if concurrent exports; legacy defect).
- Python: MISSING (no orchestrator, no error report path).

## finally (7455-7480) - cleanup
- Close streamWriter2/3/4 (null-safe; double close ok).
- Stage "42": only if `text4 == ""` (text4 = a "do not release lock/ExtractUser preserved" string; UNVERIFIED meaning, set earlier, probably the pre-existing ExtractUser value / "locked by another" flag): `UPDATE Site SET ExtractUser = NULL WHERE SiteId = <_siteId>` via sqlConnection; exceptions swallowed silently (7469-7474) -> a stale lock (ExtractUser) can persist undetected and block next export. The `text` var is reassigned to this SQL so the global catch's SQL echo may be stale (the catch runs before finally, so OK).
- Close sqlConnection, sqlConnection2/3/4 (null-safe; Close() on a connection with an open reader fine). Not a `using`; any exception in Close() would escape (unlikely).
- No deletion of temp files (temp\*_data.txt remain), no Excel process kill if hung.
- Python: MISSING. Grep for ExtractUser across *.py: no hits -> no lock acquisition or release, so no concurrency guard against two exporters on the same site.

---------------------------------------------------------------------
## Top gaps / defects (summary)
1. No orchestrator in Python: stages 35-42 (post-processing, fabric expansion, BOM tagging, writes, XLS, completion, catch, finally) are entirely absent; only helpers exist.
2. Item and material row post-processing (prefix stripping, hard-coded FLC/CQND58/CN1/F23/F25 rewrites, feature-column repack from the material tab) not ported; item row schema (34 fixed + Feat1-20 + tail) is not defined in config.py (item header lists, CSI ~210 col and non-CSI 74-col, missing).
3. Fabric colour material/item generation (37/38) missing, including sticky width state, Knoll width-10 rule, CM01 exclusion, `9-FAB-` item template, sequence override.
4. BOM stage 40/41 (ItemId lookup + `PDMOptionDataReportWithIncBase(@item,@siteId)` + SytelineBOMExport) missing; legacy SQL string concatenation (quote bug) and un-sorted proc re-calls.
5. Dedup by `removeNonAlphaNumeric(row)` (lossy) not ported; port has only writeData-style dedupe.
6. XLS (Excel COM) conversion missing; no .xls/.xlsx output. Legacy failure there is only a MsgBox and does not fail the export.
7. Site.ExtractUser release (stage 42, swallowed errors) and the corresponding acquisition lock missing -> no mutual exclusion.
8. Legacy defects to NOT replicate blindly: dead CRB block (flag24 forced false, 6419); myWriter1/2 errors swallowed behind a MsgBox then "Export Complete" reported; modal debug dialog on error even in service mode; abort not checked during writes and partial files left; arrayList110 dedupe on wrong key; `F25-04`/`F25-05` asymmetry; "F14-03" insertion without tab; int.Parse/Substring crash points.
9. Divergence: `LegacyDependencyMaterialSequencer` increments per call whereas fabric sequencing increments only when a new code joins the key list.
10. Aux writers are implemented but unwired, atomic/parameterized (intentional improvement), and ValueError on site_id<1 differs from legacy.
