# Engineering Features (Hidden / Non-Obvious Logic)

*A cross-cutting index of the hidden, magic, and non-obvious engineering behaviour already surfaced in
the "Hidden Logic" and "Risks" sections of the handbook module docs (`00`–`28`). This document
**summarises and links** — it does not duplicate whole sections. Each item gives a short description, the
module doc link(s), and the business-rule id(s) where applicable. `UNKNOWN` marks anything not provable
from source. Module links use `../NN_Name.md`.*

---

## 1. Magic numbers

- **Synthetic lead time** `LEADTIME = Catalogue.LeadTime + 5` — baseline for the OFML lead-time class.
  → [../21_OCD.md](../21_OCD.md) (`BR-OCD-030`), [../06_Articles.md](../06_Articles.md) (`BR-ART-017`).
- **DisplayOrder sentinel** `-1 → 9999` when sorting categories/options.
  → [../04_Product_Categories.md](../04_Product_Categories.md), [../16_Ordering.md](../16_Ordering.md).
- **Property length overrides**: default = `OrderCodeValue2.Length`; forced `5` for `FABRICCOLOUR`,
  `11` for `SAYLVISCHR_SB_U`. → [../08_Property_Values.md](../08_Property_Values.md) (`BR-PVAL-013/014`).
- **Group-size guards**: warn when a handbook group has `>500` products or `>1000` items (unless
  `pricebook`). → [../23_Generation.md](../23_Generation.md).
- **Image scale** to `180w × 160h × 1.3`; **URL timeout `100 ms`**; connection **retry 5×**, backoff
  `2000 * i` ms. → [../17_Images.md](../17_Images.md), [../00_System_Architecture.md](../00_System_Architecture.md).
- **AER special-case**: trim last 2 chars, truncate short/long text at `" / "` / `" >"` before pCon push.
  → [../12_Translations.md](../12_Translations.md) (`BR-TRAN-024`).
- **`AU900*` / `MQ`/`MR` + `7Q`** article-code shortening and `relObjID="9999"` remap.
  → [../21_OCD.md](../21_OCD.md) (`BR-OCD-034`), [../08_Property_Values.md](../08_Property_Values.md) (`BR-PVAL-027`).

## 2. Hardcoded IDs

- **Catalogue ids**: `1/128/129/999` excluded (`999` = SP Components); `4 → {45,25,15}`; `57`/`58` =
  lead-time bands; `81` = all-items pricing scope; `258` = base-price-not-null; `264`+`776` = SP sort;
  `360 → add 392`; `615` image truncation. → [../06_Articles.md](../06_Articles.md),
  [../21_OCD.md](../21_OCD.md), [../18_Pricing.md](../18_Pricing.md), [../22_Export.md](../22_Export.md),
  [../17_Images.md](../17_Images.md) (`BR-IMG-072`).
- **Option ids**: `8` = fabric type, `28` = fabric colour, `3344`/`3346` = secondary fabric, `6790`/`6791`
  — all bypass the normal owning-entity name update via `ProductCategoryMask`.
  → [../13_Descriptions.md](../13_Descriptions.md) (`BR-DESC-020`), [../11_Configuration.md](../11_Configuration.md).
- **Site `20`** excluded across products/pricing/utilities.
  → [../06_Articles.md](../06_Articles.md), [../18_Pricing.md](../18_Pricing.md), [../24_Utilities.md](../24_Utilities.md).
- **Suppliers** `8513`/`8525`/`8625`, `kvadrat SupplierId=2` — **UNKNOWN** exact semantics; cited in SIF/OFDA
  handling. → [../22_Export.md](../22_Export.md).
- **Product code / category** `805`/`1009`/`615` image-path truncation; OFDA cat→productline map.
  → [../17_Images.md](../17_Images.md), [../22_Export.md](../22_Export.md) (`BR-EXP-023`).

## 3. Special users

- **`RMAFYT`** — Admin button visible regardless of `PDMAdministrator`. → [../02_User_Permissions.md](../02_User_Permissions.md) (`BR-PERM-013`).
- **`dbacw8`** — admin override; only user allowed OFDA `groupdata.txt` mode, SIF scheduler right-branch,
  `ImportMaterialsInToCSI`. → [../02_User_Permissions.md](../02_User_Permissions.md) (`BR-PERM-014`),
  [../15_Filtering.md](../15_Filtering.md), [../22_Export.md](../22_Export.md).
- **`_pConCreatorUsers`** — hardcoded user list that **bypasses read-only** catalogue gating in pCon tooling.
  → [../11_Configuration.md](../11_Configuration.md).

## 4. Feature flags / environment gates

- Menu/behaviour gated by connected server/DB name: **`eoscloud`**, **`POSH`**, **`(local)`**, **`PDMLive`**
  (e.g. Audit requires DB not `(local)` and not `POSH`; pCon push / audit disabled on `eoscloud`).
  → [../00_System_Architecture.md](../00_System_Architecture.md), [../02_User_Permissions.md](../02_User_Permissions.md)
  (`BR-PERM-006`), [../18_Pricing.md](../18_Pricing.md).
- **`Global.testMode`** (`Global.cs:65`, default `false`) — relaxes image path filtering; **`ofdaManagerOrWebConfigActive`**
  single-instance guard; full effect partly **UNKNOWN**. → [../17_Images.md](../17_Images.md),
  [../00_System_Architecture.md](../00_System_Architecture.md).

## 5. Read-only & inverted flags

- **`PDMUserCatalogues.ReadOnly` is INVERTED**: `1` = full edit, `0` = read-only. `_readOnlyCatalogues`
  captures the raw value; `0 = editable`. → [../02_User_Permissions.md](../02_User_Permissions.md),
  [../11_Configuration.md](../11_Configuration.md) (`BR-CFG-004`), [../13_Descriptions.md](../13_Descriptions.md),
  [../18_Pricing.md](../18_Pricing.md) (`BR-PRICE-050`).
- **`DescriptionEdit`** privilege **overrides** a read-only catalogue for description edits.
  → [../13_Descriptions.md](../13_Descriptions.md).
- **`EOSLiteDisplayOrder` stored negated** in the CAD path, raw in ProductDescriptions (inconsistency).
  → [../09_Options.md](../09_Options.md) (`BR-OPT-016`).
- **`_readOnlyCatalogues` captured but never enforced** in UI Group maintenance (authz gap).
  → [../15_Filtering.md](../15_Filtering.md).

## 6. Boolean / parse special cases

- **`BOMManager`** projected via correlated subquery + `CROSS JOIN (SELECT NULL AS BOMManager)`; parsed
  specially: empty → `false`, integer `1` → `true`. → [../01_Authentication.md](../01_Authentication.md)
  (`BR-AUTH-005`), [../02_User_Permissions.md](../02_User_Permissions.md), [../25_Common_SQL.md](../25_Common_SQL.md).
- **Product Maintenance** requires `ProductMaintenance` **OR** `BOMManager`.
  → [../02_User_Permissions.md](../02_User_Permissions.md) (`BR-PERM-003`).

## 7. Background workers (`*Thread`)

- `ExportThread`, `SIFExportThread`, `ExportDPSDBThread`, `ProgressThread` (`xp_cmdshell dtsrun`),
  `UpdatePriceThread`/`IncPriceThread`/`UpdatePricesThread`, `VarCondThread`, `RevitThread`/`PreviewThread`,
  `ValidateImageThread`, `DelayThread` (500 ms debounce), `TimerThread`, `ExportLayoutStyleThread`
  (internals **UNKNOWN**). → [../22_Export.md](../22_Export.md), [../24_Utilities.md](../24_Utilities.md),
  [../18_Pricing.md](../18_Pricing.md), [../11_Configuration.md](../11_Configuration.md),
  [../17_Images.md](../17_Images.md), [../20_ODB.md](../20_ODB.md), [../28_Call_Hierarchy.md](../28_Call_Hierarchy.md).

## 8. Caching / lazy loading

- Static per-session caches: SP option data (`cachedOptDataItems/OptionIds/OptionNames`), pCon node ids
  (`cached2DNodeKeys/Ids`, `cached3DNodeKeys/Ids`), catalogue `ReadOnly`/`CatalogueType`.
  → [../05_Products.md](../05_Products.md), [../11_Configuration.md](../11_Configuration.md) (`BR-CFG-061`).
- A generic reusable lazy-loading framework: **UNKNOWN** (none observed beyond the ad-hoc static caches above).

## 9. Hidden dialogs, stubs & dead code

- **`CatalogueMaintenance`** in-app form is a dead shell — menu launches external `DPS.exe`.
  → [../03_Catalogues.md](../03_Catalogues.md) (`BR-CAT-002/019`).
- **`OCDExport`** and **`ClippingsExport`** instantiated in `SytelineExport` (`:1531`/`:1533`) but
  `initParams`/`execThread` never called → dead in build. → [../21_OCD.md](../21_OCD.md), [../22_Export.md](../22_Export.md).
- **`CustomPricePerm`** never instantiated (dead). → [../18_Pricing.md](../18_Pricing.md).
- Dead stubs: `OrderCategories` category path + `AlphaButton`, MainMenu Layout XML button (`Visible=false`),
  Custom Function/Query stub, `ImportLayoutFromCatalogue` empty stub, `showPConButtons` gate defeated
  (returns `true`), pricing pCon date gate dead, `evalulateQuantity` (returns 1).
  → [../16_Ordering.md](../16_Ordering.md), [../15_Filtering.md](../15_Filtering.md),
  [../14_Search.md](../14_Search.md), [../11_Configuration.md](../11_Configuration.md),
  [../18_Pricing.md](../18_Pricing.md), [../06_Articles.md](../06_Articles.md), [../28_Call_Hierarchy.md](../28_Call_Hierarchy.md).

## 10. Hardcoded paths / credentials

- `ConnectionFactory` embeds server names and **hardcoded credentials** with password masking; server
  chosen by substring match. `Global` hardcodes `primaryPDMServer=DBCHIP12v`, `primaryPDMDatabase=PDMLive`,
  `PDMServer=wechip01v`, image base paths (`Global.filePaths`, e.g. `\\wechip01v\HMEURONET\PDM\`,
  `C:\Projects\DPS\bin\`, `http://www.hmeuronet.com/PDM/`). `Global.imageUnavailable` declared but **never
  assigned** (always null). → [../00_System_Architecture.md](../00_System_Architecture.md),
  [../17_Images.md](../17_Images.md).
- pCon path `C:\HermanMillerOFML\Staging\HermanMiller\WS\<workspace>\pcr_data_*.mdb`.
  → [../11_Configuration.md](../11_Configuration.md).

## 11. pCon / Jet 32-bit dependency

- All pCon domains use `Provider=Microsoft.Jet.OLEDB.4.0` against `.mdb` files — a **32-bit-only** Jet
  dependency. Domains: `com_ocd`, `geo_odb`, `sel_oas`, `typ_cls`. → [../11_Configuration.md](../11_Configuration.md),
  [../19_OAP.md](../19_OAP.md), [../20_ODB.md](../20_ODB.md), [../21_OCD.md](../21_OCD.md).

## 12. Order Code / Var Condition specifics

- Changing an `Option.OrderCodeFormatKey` must rewrite every range's `OrderCodeFormatString` (embeds the
  old key token) so generated codes stay consistent — each write audited.
  → [../09_Options.md](../09_Options.md) (`Q-OPT-010`).
- VarCond relation names are `"PA_" + <item prefix>` (short items keep full code); the menu
  `GenerateVARCONDForPAPRICING` opens the pricing UI rather than building SQL itself.
  → [../05_Products.md](../05_Products.md) (`BR-PROD-061`), [../11_Configuration.md](../11_Configuration.md) (`BR-CFG-071`).

## 13. Base finish node duplication

- In `CreateNode`, `_C`/`_D` node suffixes map to `_A`/`_B` and add a `_secondary` node for secondary
  finishes; successful node ids cached. → [../11_Configuration.md](../11_Configuration.md) (`BR-CFG-061/062`).

## 14. Fabric index rules

- Global fabric option ids `8`=type / `28`=colour / `3344`/`3346`=secondary; `IsFabric` 0/1(type)/2(colour);
  `OptionValue.ExcludeFromFabricIndex` and `ExcludeFromValidation` control index/validation participation;
  fabric bands (`FabricBands`) drive price bands. → [../11_Configuration.md](../11_Configuration.md),
  [../10_Option_Values.md](../10_Option_Values.md), [../18_Pricing.md](../18_Pricing.md), [../22_Export.md](../22_Export.md).

## 15. Lead-time synthesis

- Lead-time bands read from catalogues `57`/`58` (`"<UPPER despaced Name>;<OrderCodeValue>"`); synthetic
  `LEADTIME` class/property/values + per-article `LEADTIME`/`ARTICLECODE` `ocdArtBase` row (de-duplicated).
  → [../21_OCD.md](../21_OCD.md) (`BR-OCD-030/032`), [../08_Property_Values.md](../08_Property_Values.md),
  [../06_Articles.md](../06_Articles.md) (`BR-ART-017`).

## 16. Destructive file rewrites

- `OCDExport.writeData` **deletes and recreates** the `...\hmx\<groupfilter>\ANY\1\db\` output tree each run
  (existing folder removed; `.sr`/`go_` files relocated). → [../21_OCD.md](../21_OCD.md) (R-8),
  [../08_Property_Values.md](../08_Property_Values.md).
- `ExportDPSDBThread` detaches DPSDB and **overwrites** network MDF/LDF copies, then reattaches.
  → [../22_Export.md](../22_Export.md).
- Bulk image-path rewrites across every image-bearing entity (`Q-IMG-007..013`, `Q-OVAL-007`).
  → [../17_Images.md](../17_Images.md), [../10_Option_Values.md](../10_Option_Values.md).

---

*See also: [Feature_Index.md](Feature_Index.md), [../27_Business_Rules_Index.md](../27_Business_Rules_Index.md),
[../28_Call_Hierarchy.md](../28_Call_Hierarchy.md).*
