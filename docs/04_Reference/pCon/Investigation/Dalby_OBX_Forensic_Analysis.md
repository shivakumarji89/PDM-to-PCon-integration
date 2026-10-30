# Dalby OBX Forensic Analysis

**Status:** Phase 1 evidence report (read-only investigation) · **Date:** 2026-10-30
**Companion:** [OCD_Engine_Technical_Specification.md](OCD_Engine_Technical_Specification.md) (architecture; cites this report)
**Reproduce:** `python -I evidence/dalby_obx_forensics.py "C:\Users\siaoca\Downloads\Dalby_OBX_Files" "C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx\dalby\ANY\1\db" evidence` — output in `evidence/run_output.txt`; extracted data in `evidence/*.csv`.

Evidence labels: **[C]** Confirmed (reproduced from files by script) · **[S]** Strongly supported · **[H]** Hypothesis · **[U]** Unknown.

**Inputs read:** every file in `C:\Users\siaoca\Downloads\Dalby_OBX_Files` (26 OBX, 2 CSV, 1 XLSX); Dalby OCD CSVs + descriptors (`...\hmx\dalby\ANY\1\db`); Dalby/Lino OAM; Lino OCD (scheme only); `C:\Users\siaoca\Desktop\MK_OFML_Testsuite` (read, not executed); Workbench `ui/pages/obx_validation_page.py`, `services/sif_validation_service.py` (read only).

**Headline result.** The 56-article puzzle is solved arithmetically: **56 = 14 Top_Finish × 2 Frame_Finish × 2 base articles (NODLE150, NODLE160)**. The reference OBX is a *selected subset*, not an exhaustive OCD enumeration (the OCD data allows 30 Top_Finish values). What the OBX does prove is a large set of encoding, cascade and pricing rules, all reproduced on 1,242 Dalby articles (plus 2,352 Lino articles for encoding) with **zero exceptions** — see §5–§7.

---

## 1. OBX inventory

| # | File | KB | Producer | Articles | Unique final | Dup | Base articles | Cur | Price date |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1_Dalby_Circular_Table_Euro.obx | 544 | pCon.planner_ME 8.11 | 111 | 111 | 0 | NODLE100 NODLE110 NODLE130 NODLE140 | EUR | 2025-10-27 |
| 2 | 1_Dalby_Circular_Table_GBP.obx | 432 | pCon.planner_ME 8.11 | 83 | 83 | 0 | NODLE100 NODLE110 NODLE140 | GBP | 2025-10-27 |
| 3 | 1_Dalby_Circular_Table_GBP_Price_Mismatch.obx | 440 | (no versionInfo) | 83 | 83 | 0 | NODLE100 NODLE110 NODLE140 | GBP | 2025-10-27 |
| 4 | 2_Dalby_Side_Table_Euro.obx | 298 | pCon.planner_ME 8.11 | 56 | 56 | 0 | NODLE150 NODLE160 | EUR | 2025-10-27 |
| 5 | 2_Dalby_Side_Table_GBP.obx | 298 | pCon.planner_ME 8.11 | 56 | 56 | 0 | NODLE150 NODLE160 | GBP | 2025-10-27 |
| 6 | 2_Dalby_Side_Table_GBP_Price_Mismatch.obx | 303 | (no versionInfo) | 56 | 56 | 0 | NODLE150 NODLE160 | GBP | 2025-10-27 |
| 7 | 3_Dalby_Cafe_Table_Euro.obx | 298 | pCon.planner_ME 8.11 | 56 | 56 | 0 | NODLE210 NODLE230 | EUR | 2025-10-27 |
| 8 | 3_Dalby_Cafe_Table_GBP.obx | 298 | pCon.planner_ME 8.11 | 56 | 56 | 0 | NODLE210 NODLE230 | GBP | 2025-10-27 |
| 9 | 3_Dalby_Cafe_Table_GBP_Price_Mismatch.obx | 304 | (no versionInfo) | 56 | 56 | 0 | NODLE210 NODLE230 | GBP | 2025-10-27 |
| 10 | 4_Dalby_Circular_Table_Euro.obx | 449 | pCon.planner_ME 8.11 | 76 | 76 | 0 | NODLE300 NODLE310 NODLE320 | EUR | 2025-10-27 |
| 11 | 4_Dalby_Circular_Table_GBP.obx | 449 | pCon.planner_ME 8.11 | 76 | 76 | 0 | NODLE300 NODLE310 NODLE320 | GBP | 2025-10-27 |
| 12 | 4_Dalby_Circular_Table_GBP_Price_Mismatch.obx | 457 | (no versionInfo) | 76 | 76 | 0 | NODLE300 NODLE310 NODLE320 | GBP | 2025-10-27 |
| 13 | 5_Dalby_Rectangular_Table_Euro.obx | 979 | pCon.planner_ME 8.11 | 168 | 168 | 0 | NODLE400 NODLE410 NODLE420 NODLE430 NODLE440 NODLE450 | EUR | 2025-10-27 |
| 14 | 5_Dalby_Rectangular_Table_GBP.obx | 979 | pCon.planner_ME 8.11 | 168 | 168 | 0 | NODLE400 NODLE410 NODLE420 NODLE430 NODLE440 NODLE450 | GBP | 2025-10-27 |
| 15 | 5_Dalby_Rectangular_Table_GBP_Price_Mismatch.obx | 997 | (no versionInfo) | 168 | 168 | 0 | NODLE400 NODLE410 NODLE420 NODLE430 NODLE440 NODLE450 | GBP | 2025-10-27 |
| 16 | 6_Dalby_Bar_Height_Table_GBP.obx | 648 | pCon.planner_ME 8.11 | 112 | 112 | 0 | NODLE500 NODLE510 NODLE520 NODLE530 | GBP | 2025-10-27 |
| 17 | 6_Dalby_Bar_Height_Table_GBP_Price_Mismatch.obx | 483 | (no versionInfo) | 81 | 81 | 0 | NODLE500 NODLE510 NODLE520 | GBP | 2025-10-27 |
| 18 | 6_Dalby_Bar_Height_Table_Snappers.obx | 647 | pCon.planner_ME 8.11 | 112 | 112 | 0 | NODLE500 NODLE510 NODLE520 NODLE530 | EUR | 2025-10-27 |
| 19 | 7_Dalby_6-Leg_Table_Euro.obx | 336 | pCon.planner_ME 8.11 | 56 | 56 | 0 | NODLE600 NODLE610 | EUR | 2025-10-27 |
| 20 | 7_Dalby_6-Leg_Table_GBP.obx | 336 | pCon.planner_ME 8.11 | 56 | 56 | 0 | NODLE600 NODLE610 | GBP | 2025-10-27 |
| 21 | Lino_Stool_snappers_27Aug26_Euro.obx | 1192 | pCon.planner_ME 8.15 | 168 | 168 | 0 | MI7E3 | EUR | 2026-09-07 |
| 22 | Lino_Stool_snappers_27Aug26_GBP.obx | 1192 | pCon.planner_ME 8.15 | 168 | 168 | 0 | MI7E3 | GBP | 2026-09-07 |
| 23 | Lino_Task_Chair_KD_snappers_27Aug26_Euro.obx | 3556 | pCon.planner_ME 8.15 | 504 | 504 | 0 | MI2E3 | EUR | 2026-09-07 |
| 24 | Lino_Task_Chair_KD_snappers_27Aug26_GBP.obx | 3556 | pCon.planner_ME 8.15 | 504 | 504 | 0 | MI2E3 | GBP | 2026-09-07 |
| 25 | Lino_Task_Chair_snappers_27Aug26_Euro.obx | 3543 | pCon.planner_ME 8.15 | 504 | 504 | 0 | MI1E3 | EUR | 2026-09-07 |
| 26 | Lino_Task_Chair_snappers_27Aug26_GBP.obx | 3543 | pCon.planner_ME 8.15 | 504 | 504 | 0 | MI1E3 | GBP | 2026-09-07 |

Other files: `7_Dalby_6-Leg_Table_Euro_EUR_27-Oct-2025.csv` (56 rows, PDM vs OBX price comparison, all `VALID`, PDM = OBX price on all 56), `Lino_Stool_snappers_27Aug26_Euro.csv` (20 rows, same format), `obx_extracted.xlsx` (sheets `SKU_PLC`, `SKU_Price_Date`, 1,242 rows each = exactly the 1,242 non-`Price_Mismatch` Dalby articles, all dated 2025-10-27).

Findings on the inventory:
- **[C]** All 26 files are valid UTF-8, contain no duplicate final article numbers within a file, and no duplicate `basketId` within a file. (An earlier suspicion of duplicates came from my own tooling, not from the files.)
- **[C]** 20 Dalby files + 6 Lino files. Dalby files are `pCon.planner_ME 8.11`, bsk XML 1.8.9, price date **2025-10-27**, `progId=@hmx_dalby`, region `ANY`. Lino files are `pCon.planner_ME 8.15`, price date **2026-09-07**, `progId=@hmx_lino`. **No Dalby export from 8.15 and none from PRO exists in the folder** [C]; the 8.15 files are *ME* and *Lino*, so version and program are confounded.
- **[C]** Euro/GBP pairs are separate exports of the *same* configurations with the currency switched (files 2, 3, 4, 5, 7: identical final-number sets; file 1 differs, see §2.3; file 6 GBP vs "Snappers": identical set, but the "Snappers" file carries **EUR** prices — the name does not indicate currency).
- **[C]** The six `*_Price_Mismatch.obx` files are **not pCon exports**: root `<root>` instead of `<cutBuffer>`, no `versionInfo`, double-quoted attributes. The Workbench OBX-validation page writes files with exactly this suffix (`ui/pages/obx_validation_page.py:1415`, `export_filtered_obx`). **[S]** they are the Workbench's filtered re-exports of rows it flagged; for all six, every article that they share with their GBP counterpart has identical sale price, price components and price date, so the file content itself does not show *why* it was flagged **[U]** (a plausible reason is validation against PDM prices at a different date than 2025-10-27 — **[H]**, not testable without the validation run). They add no independent evidence and are excluded from the counts below (1,242 = 1,242 articles in the 14 genuine Dalby exports).
- **[C]** Only one article per file carries a long `manufacturer`/`series` name block; later articles use empty `<manufacturer id='HM'/>`, and later entries may reference earlier localised text by `feature.N` ids instead of repeating it (seen on the NODLE130 articles in file 1 Euro). An OBX reader must resolve these references; a writer is free to repeat the full text.

---

## 2. Article-level reconstruction

### 2.1 Extracted fields per `bskArticle` (all [C], first article of `2_Dalby_Side_Table_GBP.obx`)

| Field | Value |
|---|---|
| `artNr base` / `final` | `NODLE150` / `NODLE150 WLN Q75` |
| `artNr varcode` | `NODLE150 WLN Q75@WLN Q75` |
| `artNr ofmlvarcode` | `DALBY_OPT.Frame_Finish=WLN;DALBY_OPT.Top_Finish=Q75` |
| manufacturer / series | `HM` / `DALBY` |
| `pdInfo` | `pdbType=ocd pkgName=::ofml::oi manufacturerId=HM seriesId=DALBY progId=@hmx_dalby region=ANY` |
| `metaType` | `MT_DALBY` |
| `catalogInfo` | `id=@hmx_seating version=1.14.0 artNr=NODLE150 varCode=''` |
| features | `Series, TTSH, TTSZ, Table_type` (empty, flags 0); `Frame_Finish=WLN`, `Top_Finish=Q75` (flags **1**); `Bottom_Material_G=MDF`, `Bottom_WFT=MDF`, `PLC=SE-NO-DL` (flags 0); `Bottom_Stright_Edge` omitted |
| `propVarCode` | `Series="";TTSH="";TTSZ="";Table__type="";Frame__Finish=@WLN;Top__Finish=@Q75;Bottom__Material__G=@MDF;Bottom__Stright__Edge=@VOID;Bottom__WFT=@MDF;PLC=@SE-NO-DL` (a second `aggr='1'` variant is prefixed with `GDALBY_Series/TTSH/TTSZ=@…` entries) |
| `itemPrice` | `purchase` and `sale`, each with `pd='1'` and without, all `GBP 1156.0` |
| `priceComponents` | `baseprice` 75.173 %, `Surcharge for Frame finish` 3.720 %, `Surcharge for Top finish` 21.107 % (`currency='%'`) |
| `priceDate` | `2025-10-27` |
| `addStateCode` | `type=OiOdbPlElement` `[[@Meta,"GDALBY_Series='Symbol(\"DALBY_Series_SID\")',GDALBY_TTSH=…,GDALBY_TTSZ=…"]]` and `type=ChildProps aggr=1` |
| `geometryChecksum` | `w03fYlZo6Go8WbBGJVsHhg` |

### 2.2 All 56 articles of `2_Dalby_Side_Table_GBP.obx` (inspected individually)

| # | Final article | Frame | Top | Bottom_Material_G | Bottom_Stright_Edge | Bottom_WFT | GBP | Price components, % of total (OBX order) |
|---|---|---|---|---|---|---|---|---|
| 1 | NODLE150 WLN Q75 | WLN | Q75 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 2 | NODLE160 WLN WRC | WLN | WRC | WRC | (omitted) | WRC | 912 | 95.285|4.715 |
| 3 | NODLE150 OAK Q23 | OAK | Q23 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 4 | NODLE150 WLN Q72 | WLN | Q72 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 5 | NODLE160 OAK Q79 | OAK | Q79 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 6 | NODLE160 OAK OAK | OAK | OAK | OAK | (omitted) | OAK | 890 | 97.640|2.360 |
| 7 | NODLE160 OAK WRC | OAK | WRC | WRC | (omitted) | WRC | 869 | (none) |
| 8 | NODLE150 OAK WRC | OAK | WRC | WRC | (omitted) | WRC | 869 | (none) |
| 9 | NODLE150 WLN WRC | WLN | WRC | WRC | (omitted) | WRC | 912 | 95.285|4.715 |
| 10 | NODLE150 WLN WLN | WLN | WLN | WLN | (omitted) | WLN | 933 | 93.140|4.609|2.251 |
| 11 | NODLE150 WLN BRC | WLN | BRC | BRC | (omitted) | BRC | 912 | 95.285|4.715 |
| 12 | NODLE150 WLN Q55 | WLN | Q55 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 13 | NODLE150 WLN Q76 | WLN | Q76 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 14 | NODLE150 WLN Q66 | WLN | Q66 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 15 | NODLE150 WLN OAK | WLN | OAK | OAK | (omitted) | OAK | 933 | 93.140|4.609|2.251 |
| 16 | NODLE150 WLN Q23 | WLN | Q23 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 17 | NODLE150 WLN Q32 | WLN | Q32 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 18 | NODLE150 OAK WLN | OAK | WLN | WLN | (omitted) | WLN | 890 | 97.640|2.360 |
| 19 | NODLE150 OAK Q72 | OAK | Q72 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 20 | NODLE150 OAK Q66 | OAK | Q66 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 21 | NODLE150 OAK BSE | OAK | BSE | (omitted) | BSE | BSE | 869 | (none) |
| 22 | NODLE160 WLN Q75 | WLN | Q75 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 23 | NODLE160 WLN OAK | WLN | OAK | OAK | (omitted) | OAK | 933 | 93.140|4.609|2.251 |
| 24 | NODLE160 WLN Q72 | WLN | Q72 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 25 | NODLE160 WLN Q79 | WLN | Q79 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 26 | NODLE160 WLN Q66 | WLN | Q66 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 27 | NODLE160 WLN Q55 | WLN | Q55 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 28 | NODLE160 WLN Q23 | WLN | Q23 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 29 | NODLE150 WLN BSE | WLN | BSE | (omitted) | BSE | BSE | 912 | 95.285|4.715 |
| 30 | NODLE150 WLN WSE | WLN | WSE | (omitted) | WSE | WSE | 912 | 95.285|4.715 |
| 31 | NODLE150 OAK Q79 | OAK | Q79 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 32 | NODLE150 OAK Q76 | OAK | Q76 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 33 | NODLE160 OAK WLN | OAK | WLN | WLN | (omitted) | WLN | 890 | 97.640|2.360 |
| 34 | NODLE160 OAK Q66 | OAK | Q66 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 35 | NODLE160 OAK BSE | OAK | BSE | (omitted) | BSE | BSE | 869 | (none) |
| 36 | NODLE160 OAK Q55 | OAK | Q55 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 37 | NODLE160 OAK Q23 | OAK | Q23 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 38 | NODLE150 OAK OAK | OAK | OAK | OAK | (omitted) | OAK | 890 | 97.640|2.360 |
| 39 | NODLE150 OAK Q32 | OAK | Q32 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 40 | NODLE150 OAK BRC | OAK | BRC | BRC | (omitted) | BRC | 869 | (none) |
| 41 | NODLE150 OAK Q55 | OAK | Q55 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 42 | NODLE160 OAK Q75 | OAK | Q75 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 43 | NODLE160 WLN WSE | WLN | WSE | (omitted) | WSE | WSE | 912 | 95.285|4.715 |
| 44 | NODLE160 OAK Q76 | OAK | Q76 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 45 | NODLE150 WLN Q79 | WLN | Q79 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 46 | NODLE160 WLN WLN | WLN | WLN | WLN | (omitted) | WLN | 933 | 93.140|4.609|2.251 |
| 47 | NODLE160 WLN Q76 | WLN | Q76 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 48 | NODLE160 WLN Q32 | WLN | Q32 | MDF | (omitted) | MDF | 1156 | 75.173|3.720|21.107 |
| 49 | NODLE150 OAK Q75 | OAK | Q75 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 50 | NODLE160 WLN BRC | WLN | BRC | BRC | (omitted) | BRC | 912 | 95.285|4.715 |
| 51 | NODLE160 WLN BSE | WLN | BSE | (omitted) | BSE | BSE | 912 | 95.285|4.715 |
| 52 | NODLE160 OAK Q72 | OAK | Q72 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |
| 53 | NODLE160 OAK BRC | OAK | BRC | BRC | (omitted) | BRC | 869 | (none) |
| 54 | NODLE160 OAK WSE | OAK | WSE | (omitted) | WSE | WSE | 869 | (none) |
| 55 | NODLE150 OAK WSE | OAK | WSE | (omitted) | WSE | WSE | 869 | (none) |
| 56 | NODLE160 OAK Q32 | OAK | Q32 | MDF | (omitted) | MDF | 1113 | 78.077|21.923 |

Checks on these 56 (and on all 1,242 genuine Dalby articles) — **[C]**, from `run_output.txt`:
- 56 distinct `(base, Frame, Top)`; bases NODLE150 ×28 and NODLE160 ×28; 14 distinct Top_Finish; 2 distinct Frame_Finish (28 each).
- Access_Cutout / Cable_leg never appear for NODLE150/160 (see §4.1).

### 2.3 Coverage differences between files (selection is not constant)

| Observation | Evidence |
|---|---|
| `1_…Circular_Table_GBP.obx` contains NODLE100, 110, 140 but **not NODLE130**; the Euro file contains NODLE130 (28 articles). | **[C]** OCD has GBP *and* EUR base prices for NODLE130 (e.g. 1014 GBP in 2025-02-04…2026-04-05), so a missing price is not the reason. |
| NODLE140 has **27** articles in both file-1 variants; `NODLE140 OAK BRC` is the missing combination. | **[C]** missing combination; **[U]** reason — BRC is valid for every base but NODLE320 per the OCD preconditions, and prices exist. |
| NODLE320 has 20 articles (10 Top_Finish × 2 Frame) in files 4 Euro/GBP; all other bases with the same selection have 28. The four dropped Top_Finish values are exactly BRC, BSE, WRC, WSE. | **[C]** counts; **[S]** cause: `ocd_propertyvalue` gives those four values rel_obj 19569 = `$ BAN NOT IN ('NODLE320')`, which evaluates to FALSE for NODLE320 and TRUE for every other base. This independently confirms the precondition and `$ BAN` semantics. |
| `6_…Bar_Height_Table_GBP_Price_Mismatch.obx` has 81 articles vs 112. | **[C]** (it is a filtered subset, §1). |

---

## 3. Top_Finish reconciliation (NODLE150, `2_Dalby_Side_Table_GBP.obx`)

The OCD data defines **30** Top_Finish values for DALBY_OPT; **14** appear in the OBX; **16** are absent: Q01–Q05, Q07–Q12 (11 values), Q54, Q74, Q77, Q83, Q84. **[C]** (matches the earlier report).

| Top_Finish | value rel_obj | In 2_GBP OBX | OBX articles | English text contains "forbo" | GBP 6695 row @2025-10-27 | EUR 6695 row @2025-10-27 |
|---|---|---|---|---|---|---|
| BRC | 19569 | yes | 4 | False | none | none |
| BSE | 19569 | yes | 4 | False | none | none |
| OAK | 0 | yes | 4 | False | 21 | 27 |
| Q01 | 0 | **no** | 0 | True | 244 | 306 |
| Q02 | 0 | **no** | 0 | True | 244 | 306 |
| Q03 | 0 | **no** | 0 | True | 244 | 306 |
| Q04 | 0 | **no** | 0 | True | 244 | 306 |
| Q05 | 0 | **no** | 0 | True | 244 | 306 |
| Q07 | 0 | **no** | 0 | True | 244 | 306 |
| Q08 | 0 | **no** | 0 | True | 244 | 306 |
| Q09 | 0 | **no** | 0 | True | 244 | 306 |
| Q10 | 0 | **no** | 0 | True | 244 | 306 |
| Q11 | 0 | **no** | 0 | True | 244 | 306 |
| Q12 | 0 | **no** | 0 | True | 244 | 306 |
| Q23 | 0 | yes | 4 | False | 244 | 306 |
| Q32 | 0 | yes | 4 | False | 244 | 306 |
| Q54 | 0 | **no** | 0 | True | 244 | 306 |
| Q55 | 0 | yes | 4 | False | 244 | 306 |
| Q66 | 0 | yes | 4 | False | 244 | 306 |
| Q72 | 0 | yes | 4 | False | 244 | 306 |
| Q74 | 0 | **no** | 0 | True | 244 | 306 |
| Q75 | 0 | yes | 4 | False | 244 | 306 |
| Q76 | 0 | yes | 4 | False | 244 | 306 |
| Q77 | 0 | **no** | 0 | True | 244 | 306 |
| Q79 | 0 | yes | 4 | False | 244 | 306 |
| Q83 | 0 | **no** | 0 | True | 244 | 306 |
| Q84 | 0 | **no** | 0 | True | 244 | 306 |
| WLN | 0 | yes | 4 | False | 21 | 27 |
| WRC | 19569 | yes | 4 | False | none | none |
| WSE | 19569 | yes | 4 | False | none | none |

Classification of every value, using the categories requested:

| Category | Values | Count | Status |
|---|---|---|---|
| 1. In OCD and in OBX | BRC, BSE, OAK, Q23, Q32, Q55, Q66, Q72, Q75, Q76, Q79, WLN, WRC, WSE | 14 | **[C]** |
| 2. In OCD, absent from OBX | Q01–Q05, Q07–Q12, Q54, Q74, Q77, Q83, Q84 | 16 | **[C]** |
| 3. Rejected by an OCD relation (for NODLE150) | none | 0 | **[C]** — the only value precondition on Top_Finish is 19569 (`BAN NOT IN NODLE320`), TRUE for NODLE150; the 16 absent values have no precondition at all (rel_obj 0) |
| 4. Unavailable through a property dependency | none | 0 | **[C]** — Top_Finish has no property precondition and is itself the *parent* of the dependencies |
| 5. Missing from the price conditions | none | 0 | **[C]** — every absent Q-value has a `6695=<value>` row in GBP (244 for 2025-02-04…2026-04-05; 255 afterwards) and EUR (306), for the 2025-10-27 price date; the price relation 568154 emits `6695=` for every Top_Finish value |
| 6. Excluded by an external export selection | all 16 | 16 | **[S]** — see §9: the generator that produced such OBX files builds a cartesian product of *user-ticked* values; the same 14 values are used for **every** Dalby base article |
| 7. Unresolved | the *reason* the 16 were not ticked | – | **[U]** |

Further evidence:
- **[C]** The same 14 Top_Finish values × {OAK, WLN} occur for every Dalby base article in all files (10 for NODLE320 due to 19569). A per-article or per-price-file difference would be expected if prices or relations drove the subset; they do not.
- **[C]** All 30 values survive their value preconditions for NODLE150 (and all but BRC/BSE/WRC/WSE for NODLE320). The MDF value precondition (rel 568112) lists all 24 Q-values, so each of the 16 absent values resolves to `Bottom_Material_G=MDF` exactly like the 8 present Q-values.
- **[C, observation only]** The 14 selected values are *exactly* the values whose English text does **not** contain "forbo" (8 Q-values without it, plus BRC, BSE, OAK, WLN, WRC, WSE; all 16 absent Q-values contain "forbo"). This is a perfect but uninterpreted correlation. **[H]** The person assembling the export may have ticked non-Forbo finishes; no selection record exists. Do not encode it as an engine rule.
- **[C]** The data are from one OCD data version (`ocd_version` 4.2, OCD_4, 1.34.7, valid 20200106–99991231); prices are dated windows in that version. Whether ME 8.11's data on 2025-10-27 equals the staged CSVs today **[U]** — but the recomputed prices match exactly (§7), which is strong evidence that the 2025 price rows are unchanged.
- **Conclusion:** the reference OBX is **not exhaustive** and its missing values are **not** invalid. Valid-for-OCD and selected-for-export must be separate concepts, as the spec already requires.

---

## 4. Dependency cascades

### 4.1 Observed behaviour (all 1,242 Dalby articles) — [C]

| Top_Finish | Bottom_Material_G | Bottom_Stright_Edge | Bottom_WFT | Articles |
|---|---|---|---|---|
| Q01…Q84 (the 8 selected Q-values) | MDF | *omitted* (`@VOID`) | MDF | 720 |
| OAK | OAK | omitted | OAK | 90 |
| WLN | WLN | omitted | WLN | 90 |
| BRC | BRC | omitted | BRC | 84 |
| WRC | WRC | omitted | WRC | 86 |
| BSE | *omitted* (`@VOID`) | BSE | BSE | 86 |
| WSE | *omitted* (`@VOID`) | WSE | WSE | 86 |

- **Rule check:** against the OCD-derived expectation (MDF ⇔ Top_Finish in the 24-value Q list; OAK/WLN/BRC/WRC ⇔ same-named Top_Finish; Bottom_Stright_Edge ⇔ BSE/WSE) there are **0 violations in 1,242** for Bottom_Material_G and for Bottom_Stright_Edge. `Bottom_Material_G=OAK` with a Q top never occurs.
- **Omitted property** (precondition FALSE): absent from `<features>`, written as `@VOID` in `propVarCode`, contributes nothing to the final article number, not in `ofmlvarcode`. **Not** `VOID` as a feature value.
- **Single resolved value:** each dependent property that is visible has exactly one value across the whole dataset, which matches the OCD value preconditions (each Top_Finish selects exactly one Bottom_Material_G/Bottom_Stright_Edge value). The sets are singletons by OCD design here **[S]**, so "can there be more than one valid value" is answered *no for Dalby*, not for OCD in general.
- **`Bottom_WFT`** always equals the visible material/edge value. No relation in `ocd_relation` mentions `Bottom_WFT` **[C]** (searched); its value table repeats the material/edge values with the same preconditions, so exactly one value is valid at any time. **[S]** it is resolved by "single valid value" semantics, **[U]** whether pCon/OFML assigns it by another route.
- **Effect on final SKU:** none. The final number uses only Access_Cutout, Cable_leg, Frame_Finish, Top_Finish (code scheme), so Bottom_* never appears in `final`/`varcode`. **[C]**
- **Effect on `propVarCode`:** all properties appear, in OCD class/property order, with the Bottom_* resolved values (§5.3). **[C]**
- **Which properties are *input*:** the OFML variable code (`ofmlvarcode`) lists **only** features with `flags='1'` (Access_Cutout, Cable_leg, Frame_Finish, Top_Finish). These are the `scope C` properties in `ocd_property`; Bottom_* are `scope RG` (flags 0). **[C]** for Dalby (14/14 properties consistent); **[H]** that flags=1 ⇔ scope C in general.
- **Hidden scope-C properties vs hidden RG properties** differ in `propVarCode`: for NODLE100–230 (Access_Cutout and Cable_leg precondition FALSE) the two properties are *absent* from the features **and** from `propVarCode` entirely, while hidden RG properties appear as `@VOID`. **[C]** observation; **[H]** the explanation is whether the property exists in the OFML property list.
- **OCD-specified vs observed.** OCD §2.15 says a property whose precondition is violated is not available. The OBX shows this as omission/`@VOID`; the OBX says nothing about *undefined* results (all Dalby preconditions use `SPECIFIED … AND …`, so they are always definite). Three-valued-logic behaviour is therefore **not exercised** by this dataset **[U]**.

### 4.2 Access_Cutout / Cable_leg (NODLE3xx–6xx)

- **[C]** In all 11 bases that expose the properties (NODLE300–NODLE610) every article has `Access_Cutout=NC` and `Cable_leg=WSL`. OCD permits more: Access_Cutout ∈ {NC, FT, FD} for 3xx–5xx and {NC, 1FT, 2FT, 1FD, 2FD} for 6xx; Cable_leg additionally allows WCL when `Access_Cutout NOT IN ('OFT','NC')` (rel 19542). So **none of the reference files exercises** the `6821=` and `7030=` price keys or the Cable_leg ↔ Access_Cutout dependency. **[C]**

---

## 5. SKU encoding

### 5.1 Reproduced rules — [C]

| Rule | Result |
|---|---|
| `final` = walk of the `ocd_codescheme.scheme` string: `@` consumes the next character of the base article number; `Class:Property` emits the property's value (empty if omitted/VOID); any other token is a literal | **1,242/1,242 Dalby** (schemes `…6335`, `…6336`) and **2,352/2,352 Lino** (scheme `…6320`, `@`×5, literal spaces, 8 properties) |
| `varcode` = `final` + `@` + **space-joined values of the `ofmlvarcode` properties, in order** | **3,594/3,594** (Dalby + Lino). In Dalby this equals the tail of `final`; in Lino it does not (Lino `varcode` = `MI7E315AF AJ 68 BB 4RM01 1FD01@7E3 1 5 A F AJ 68 BB 4RM01 1FD 1FD01`, the tail contains `Chair_Type` and `Seat_Fabric_Type`, which are not scheme tokens). The "final minus base" shortcut I used earlier is therefore **wrong in general**; the ofmlvarcode-values rule is the one that holds. |
| `ofmlvarcode` = `Class.Property=Value` for flags=1 features, `;`-separated, class from `ocd_propertyclass`/`ocd_property` | **[C]** on 3,594 (Dalby classes `DALBY_ATTR`, `DALBY_OPT`; Lino `LINO_ATTR`, `LINO_OPT`) |

### 5.2 Worked examples — [C]

| base | scheme tokens (abridged) | inputs | final |
|---|---|---|---|
| NODLE150 | `@×8, ,[Access_Cutout][Cable_leg][Frame_Finish], ,[Top_Finish]` (`…6335`) | Access/Cable *omitted*, WLN, Q75 | `NODLE150` + `" "` + `""` + `""` + `WLN` + `" "` + `Q75` = `NODLE150 WLN Q75` |
| NODLE600 | `@×8, ,[Access_Cutout], ,[Cable_leg], ,[Frame_Finish], ,[Top_Finish]` (`…6336`) | NC, WSL, OAK, BRC | `NODLE600 NC WSL OAK BRC` |
| MI7E3 | `@×5,[Height_Adjustment][Tilt][Tilt_MI7E3][Arms][Seat_Depth], ,[Back_Support], ,[Base_Frame_Finish], ,[Castors_Glides], ,[Duo_Suspension_Material], ,[Fabric_Colour]` (`…6320`) | Height_Adjustment=1, Tilt *absent*, Tilt_MI7E3=5, Arms=A, Seat_Depth=F, AJ, 68, BB, 4RM01, 1FD01 | `MI7E3`+`1`+`5`+`A`+`F` + ` AJ 68 BB 4RM01 1FD01` = `MI7E315AF AJ 68 BB 4RM01 1FD01` |

Note the 2 Dalby schemes differ only in whether literal spaces precede *each* property (6336) or only the groups (6335); the scheme is selected per article via `ocd_article.scheme_id` **[C]**.

### 5.3 `propVarCode` — [C], 40,786 value tokens + 4,968 empty tokens + 1,242 VOID tokens checked
- Property order = OCD class order then property position; **all** properties present for the article are listed (including flags 0).
- Property names: each `_` doubled (`Bottom__Material__G`). Values: `@` + value, **with a `_` prefix when the value starts with a digit** (`@_7E3`, `@_1FD01`, vs `@WLN`, `@Q75`). Empty/unset: `""`. Not applicable (precondition FALSE): `@VOID`.
- A second `propVarCode aggr='1'` carries extra child-property entries (`GDALBY_Series=@DALBY_Series_SID;…`) taken from OFML `addStateCode`/ChildProps; these are **runtime-derived** (§8) and not producible from OCD.

### 5.4 Which code-scheme flags are tested — important limits

| Field | Values seen | Tested? |
|---|---|---|
| `scheme` grammar: `@`, literal `' '`, `Class:Property` | all three | **tested** (3,594 articles, 2 programs) |
| `varcode_sep`, `value_sep`, `mo_sep`, `mo_bracket` | always empty `""` | **untested** — no non-empty value in Dalby or Lino |
| `visibility` | always `0` | **untested** for other values |
| `invisible_char` / `unselect_char` | always `-` / `X`; never appear in output | **untested** — the characters never occur because hidden properties yield empty, not `-` |
| `trim` | always `1`; Dalby NODLE150 output has no leading/trailing spaces anyway | **partly**: output with trim=1 matches; trim=0 is untested |
| Multi-option properties | none | **untested** |
| `TableCall` tokens | none | **untested** |
| Computed (`R`-type) properties / script schemes | none in Dalby/Lino | **untested** (see gap analysis for Aeron) |
| `@VOID` as *final-code* content | does not occur (VOID only in propVarCode) | n/a |

Do **not** claim a general code-scheme implementation: only the all-empty-flags subset is proven. Test data for the others must come from other programs (the gap analysis names Aeron/Cosm/Atlas).

---

## 6. Cross-file checks

- **[C]** Euro vs GBP files with the same name prefix contain the same configurations (files 2, 3, 4, 5, 7 identical sets; file 1 GBP lacks NODLE130; 6 GBP vs 6 "Snappers" identical sets). Final article numbers, varcodes, ofmlvarcodes and propVarCodes are therefore **currency-independent**; only `itemPrice`, `priceComponents` and `pdInfo`-related price fields differ.
- **[C]** The 1,242 articles of the 14 genuine Dalby exports equal the 1,242 rows of `obx_extracted.xlsx` (sheet `SKU_PLC`, `SKU_Price_Date`; the sheet lists the file names of the genuine exports only).
- **[C]** `7_Dalby_6-Leg_Table_Euro_EUR_27-Oct-2025.csv`: 56 of 56 rows `VALID`, PDM price = OBX price. This is the Workbench's own PDM-vs-OBX validation; it agrees with the independent OCD recomputation in §7.
- **[C]** The same final article number always has the same `geometryChecksum` across files and currencies (635 groups, 0 conflicts).

---

## 7. Price reconciliation

Method (independent of the Workbench): for each article, collect VARCOND keys as in relation 568154 (`6821=Access_Cutout`, `7030=Cable_leg`, `6699=Frame_Finish`, `6695=Top_Finish`; keys with no value omitted), then sum the `ocd_price` rows with `(article_nr = base, var_cond ∈ {'' , keys}, price_type S, currency = OBX currency, date_from ≤ **priceDate from the OBX** ≤ date_to, scale_quantity 1)`.

| Check | Result |
|---|---|
| Total sale price equals the sum, per article | **1,242/1,242** [C] (EUR and GBP files both) |
| No ambiguous window (more than one row per key) | **0** ambiguities [C] |
| `priceComponents` equal each component's % of the total | **1,242/1,242** [C] |
| `purchase` price equals `sale` price | **1,242/1,242** (no `P`-type row exists in `ocd_price`) [C] |
| Known example `NODLE150 WLN Q75` | 869 + 43 + 244 = **1,156 GBP** [C] — base `''`, `6699=WLN`, `6695=Q75` rows with window 2025-02-04…2026-04-05 |

Additional evidence:
- **Price date is a hard input.** All Dalby files carry `priceDate 2025-10-27`; the same keys have different values in other windows (e.g. `6695=Q75` 234 / 244 / 255, `6699=WLN` 41 / 43 / 45). The recomputation matches only because it uses the OBX's own date. **[C]** Neither currency nor date may default silently.
- **Currency:** both GBP and EUR present, same configuration lists; currency is an independent input, not tied to the `ANY` region folder. **[C]**
- **Component naming and form:** names come from `ocd_pricetext` (`Surcharge for Frame finish`, `Surcharge for Top finish`; `baseprice` for the base row); values are **percentages of the total** (`currency='%'`) with **34 significant digits** (e.g. `75.17301038062283737024221453287197` = 869/1156 in decimal128-like precision). **[C]** for the shape; **[H]** that pCon uses decimal128 arithmetic. A text for the Access-cutout surcharge exists (`Surcharge for Access cutout`) but no such component appears in any reference article.
- **Zero-value / missing components:** a key with no price row (e.g. `6699=OAK`, `6821=NC`, `6695=BRC`) yields **no** component; an article with only a base price (170 of 1,242) has an **empty** `priceComponents` list rather than a 100 % base component. **[C]**
- **Rounding:** `ocd_rounding.csv` is empty; all totals are whole numbers. **Rounding is untested** **[U]**.
- **Other price types/levels:** only `S`/`B` and `S`/`X` rows are exercised; discounts (`D`), percentage surcharges (`is_fix=0`), scale prices (`scale_quantity>1`) and the joker article `*` do not appear. **[C]** (absence), untested.
- **Dates before/after the window:** not exercised by any reference OBX other than 2025-10-27 (Dalby) and 2026-09-07 (Lino).

---

## 8. OBX fields not derivable from the OCD CSVs

| Field | Present | Behaviour observed | Source / classification |
|---|---|---|---|
| `geometryChecksum` | 1,242/1,242 Dalby, all Lino | 26 distinct values per base article for 28 configurations (e.g. in NODLE150, `WLN Q75`/`WLN Q76` and `OAK Q75`/`OAK Q76` pairs share a checksum); changes with Frame and Top; identical for the *same* final number across files and currencies (635/635 groups) | **Runtime-dependent**, probably geometry/ODB output. **[S]** deterministic given the configuration, **[U]** algorithm. Not derivable from OCD. |
| `addStateCode` `OiOdbPlElement` | present on 1,214 Dalby articles; **absent** on the 28 NODLE130 articles in file 1 Euro (the compact/`feature.N`-reference entries) and absent from all six Lino 8.15 files (0 `addStateCode`, 0 `metaType` elements; `geometryChecksum` present on every article) | Content is per **base article** (`GDALBY_Series/TTSH/TTSZ` symbols, e.g. `DALBY_Series_SID`, `DALBY_TTSHa_Circular`, `DALBY_TTSZa_350`), constant across all configurations of a base, **independent of Frame/Top** | **Runtime/OFML** (OFML `getAddStateCode()`; `GDALBY_*` are OFML class variables from the ODB/`go_*`). Not in OCD. **[S]** it can be copied from a pCon export per base article but not generated; **[U]** whether the `go_*` tables could derive it. |
| `addStateCode` `ChildProps` | same as above | `[[PS,GDALBY_Series,1],[PL,…],…,[MT,RtAxis,2],[MT,TrAxis,5]]` | as above |
| `metaType` (`MT_DALBY`) | Dalby yes, **Lino no** | OFML metatype registration | **[C]** present/absent; metatype data in `go_*`/MT tables (memory note: write contract blocked on owner decisions). **[U]** how to resolve for new programs. |
| `catalogInfo` | all | `@hmx_seating` v1.14.0 (Dalby), `@hmx_catalogue` v1.35.1 (Lino); `artNr` = base | **[C]** copied from the OFML package registration, not OCD |
| `appData` (`fandc/xcad` `Entity handles`) | all | per-instance CAD handle, differs by article | **Runtime-only**, drop |
| `pdInfo` | all | `pkgName ::ofml::oi`, `progId @hmx_dalby`, region `ANY`, `salesOnly=false`, `aggrSalesOnly=false` (the latter only when present) | **[C]** from package registration + OAM (`::ofml::oi::OiOdbPlElement`) |
| `description short/long/features`, `nameText`, `valueText`, `descrText` | all (localised en/de/fr/nl) | from `ocd_artshorttext/longtext/propertytext/propvaluetext/…` | **[S]** OCD text tables; formatting rules for `features` text (newline-joined `<name>: <value text>`) are visible but need a dedicated test |
| `docCalculationChanges`, `quantity` | not in ME 8.15 Lino output | 8.11 has `quantity` | version/program-dependent **[U]** |
| ME 8.11 vs ME 8.15 structure | tag-set difference: 8.11 Dalby has `addStateCode`, `metaType`, `quantity`; 8.15 Lino has none of them | confounded with program (Dalby vs Lino) | **[U]** — needs a Dalby export from 8.15/PRO |

**Consequence for independent generation:** the engine can produce `artNr` ×4, `features`, `propVarCode` (non-aggr), `itemPrice`, `priceComponents`, `priceDate`, `pdInfo`, localised texts. It **cannot** produce `geometryChecksum`, `addStateCode`, `appData`; these must be (a) omitted, (b) copied from a pCon export keyed by base article (`addStateCode` only), or (c) filled by a pCon/SDK step. pCon's "Update" step evidently accepts an OBX that contains only `base` + `ofmlvarcode` (that is what the Snapper generator emits, §9) and fills in all of these. **[S]** — an independently generated *input-style* OBX (base + ofmlvarcode) is a realistic first target; a full output-style OBX is not independently reproducible. Whether pCon accepts a hand-built output-style OBX without checksums **[U]** (needs a runtime test).

---

## 9. Export-driver findings

- **[C]** The driver is **not stored with the OBX files**; no queue file, allow-list, script output or log was found in the folder. `C:\Users\siaoca\Desktop\MK_OFML_Testsuite` contains no Dalby-specific data (grep for `dalby`, `Top_Finish`, `NODLE` over its `.py/.md/.json/.bat/.csv/.txt`: no hits).
- **[C]** That project (OFML Testsuite → *Snapper File Generator*, `CLAUDE.md`, `modules/snapper/generator.py`) is a tool that: (1) takes a seed OBX exported from pCon, (2) reads valid values from OCD, (3) lets the user **tick values per property**, (4) computes the **cartesian product of articles × ticked values** (`compute_permutations`), (5) emits an OBX containing only `artNr base` and `artNr ofmlvarcode` (+ a long description), (6) the user imports it into pCon and runs **Update**, which resolves final numbers, prices, descriptions, cascades.
- **[S]** The reference files are Snapper-style outputs after pCon Update: the `ofmlvarcode` of every Dalby article lists exactly the user-set properties; 28 articles per base = 14 ticked Top_Finish × 2 ticked Frame_Finish; the same 14/2 values are used for all bases; the cascade-driven properties are resolved by pCon, not specified. Naming (`…_snappers_27Aug26…`, `6_Dalby_Bar_Height_Table_Snappers.obx`) supports this.
- **[C]** Consequence of that design for NODLE320: the Cartesian input would contain `NODLE320 … BRC/BSE/WRC/WSE`; the output has none. So pCon (or a later step) **rejected/dropped** the four combinations that rel 19569 forbids **[S]** (cannot tell whether pCon refused them at import or the user removed them).
- **[S]** The selection is therefore **manual (user-ticked) and unrecorded**; it is **not** an OCD-derived enumeration and not a general rule. It is not evidence of an allow-list file; none exists in the evidence.
- **[U]** Why those 14 values; why NODLE130 is absent from the GBP file 1 but present in the Euro file; why `NODLE140 OAK BRC` is missing; which seed OBX was used; whether the five-line selection was edited by hand after generation.
- **[C]** I did **not** execute any script; the Testsuite and Workbench were only read.

---

## 10. Evidence classification summary

| Statement | Class |
|---|---|
| 56 = 14 Top_Finish × 2 Frame_Finish × 2 bases (NODLE150/160) | **Confirmed** |
| OCD allows 30 Top_Finish values for NODLE150; 16 absent from the OBX are valid and priced | **Confirmed** |
| The reference OBX is a user-selected subset, not an enumeration | **Strongly supported** (generator design + constancy across bases); reason for the 14 **Unknown** |
| Bottom_Material_G / Bottom_Stright_Edge / Bottom_WFT cascades obey the OCD preconditions (0 violations / 1,242) | **Confirmed** |
| `$ BAN NOT IN ('NODLE320')` removes BRC/BSE/WRC/WSE for NODLE320 | **Confirmed** (OCD relation + OBX counts agree) |
| `final` = code-scheme token walk; `varcode` = `final@` + ofmlvarcode values; `propVarCode` escaping rules | **Confirmed** (3,594 articles, 2 programs) for the all-empty-flags subset |
| `varcode` suffix = `final` minus base | **Refuted** (Lino) |
| Price = Σ matching `ocd_price` rows for the OBX's own date and currency | **Confirmed** (1,242/1,242) |
| `geometryChecksum`, `addStateCode`, `appData` not derivable from OCD | **Strongly supported** (derivable only via the runtime/OFML) |
| `visibility`, `invisible_char`, `unselect_char`, separators, multi-option, rounding, scale/discount prices, three-valued undefined results, constraints | **Untested** by all reference data |
| 8.15/PRO behaviour for Dalby | **Unknown** (no export) |

## 11. Remaining unknowns

1. Why exactly 14 Top_Finish values (and NODLE130-GBP absent, NODLE140 OAK BRC absent) — needs the person who built the export, or the seed/queue.
2. A Dalby export from PRO 8.15 for the version question; ME 8.15 Lino cannot settle it.
3. Algorithm of `geometryChecksum`; whether `addStateCode` content can be derived from OFML/ODB data; whether pCon accepts OBX without them.
4. The non-empty code-scheme flags, multi-option, TableCall, computed schemes — need test data from other programs.
5. Constraints (type 4), reactions, undefined (three-valued) results in practice — Dalby has only preconditions and price actions.
6. Rounding, percentage/scale/discount prices.
7. How `propVarCode` decides to omit hidden scope-C properties vs `@VOID` for RG properties.
8. Purpose/trigger of the `_Price_Mismatch` files (the validation run, not the files themselves, holds the answer).
9. `flags='1'` ⇔ scope C in general.
