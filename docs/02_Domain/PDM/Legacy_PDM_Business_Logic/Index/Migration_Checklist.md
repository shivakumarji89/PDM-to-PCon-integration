# Migration Checklist

> **Purpose:** Single go/no-go tracker for rebuilding each Legacy PDM module inside **MK Product Workbench**. This is a *navigation/planning* document — it does **not** restate module content. All rule counts, SQL, and dependency facts are cross-referenced to the completed handbook docs (relative links use `../`). Where a fact cannot be proven from source it is marked **UNKNOWN**.
>
> Authoritative sources: [../README.md](../README.md) (status table, headline findings, §6 priority), [../27_Business_Rules_Index.md](../27_Business_Rules_Index.md) (rule counts), [../25_Common_SQL.md](../25_Common_SQL.md) (stored-proc index + UNKNOWN bodies), [../26_Data_Model.md](../26_Data_Model.md) (tables).

---

## Master module tracker

Doc status is **Complete** for every module (all 29 handbook docs complete per [../README.md](../README.md) §8). Migration status is **Not started** (pre-implementation) unless the module is dead/orphaned. "Blocked" reasons are cross-referenced, not duplicated.

| Module | Handbook doc | Doc status | Business rules (count) | SQL captured | Dependencies captured | Migration status | Ready for MK Workbench? | Key UNKNOWNs |
|---|---|---|---:|---|---|---|---|---|
| 00 System Architecture | [../00_System_Architecture.md](../00_System_Architecture.md) | Complete | 9 | Yes | Yes | Not started | **Ready** (with security remediation) | Hardcoded creds/server names to replace with secrets |
| 01 Authentication | [../01_Authentication.md](../01_Authentication.md) | Complete | 8 | Yes | Yes | Not started | **Ready** | Special-user hardcoding (`RMAFYT`, `dbacw8`) semantics |
| 02 User Permissions | [../02_User_Permissions.md](../02_User_Permissions.md) | Complete | 15 | Yes | Yes | Not started | **Ready** | Inverted `PDMUserCatalogues.ReadOnly` (1 = full) must be re-modelled |
| 03 Catalogues | [../03_Catalogues.md](../03_Catalogues.md) | Complete | 19 | Yes | Yes | Not started | **Blocked** — catalogue CRUD lives in external `DPS.exe` (in-app form is a dead shell) | `DPS.exe maintenanceCAT` internals |
| 04 Product Categories | [../04_Product_Categories.md](../04_Product_Categories.md) | Complete | 13 | Yes | Yes | Not started | **Ready** | Reserved category ids `1/128/129/999` rationale |
| 05 Products | [../05_Products.md](../05_Products.md) | Complete | 70 | Yes | Yes | Not started | **Blocked** — depends on UNKNOWN procs | `PDMOptionDataReport`, `fnGetListPrice`/`ByItem`, `fnGetSPComponentCount`; `SiteId 20` exclusion meaning |
| 06 Articles | [../06_Articles.md](../06_Articles.md) | Complete | 18 | Yes | Yes | Not started | **Blocked** — depends on UNKNOWN proc | `GetProductOptionCount`; `LF_SEATTYPE` F/A branch meaning |
| 07 Attributes | [../07_Attributes.md](../07_Attributes.md) | Complete | 32 | Yes | Yes | Not started | **Ready** | `HSCode` edit is dead/commented; `SiteId 20` exclusion |
| 08 Property Values | [../08_Property_Values.md](../08_Property_Values.md) | Complete | 33 | Yes | Yes | Not started | **Blocked** — depends on UNKNOWN proc | `PDMOptionDataReport`; hardcoded `"C7"`/allowed-set source |
| 09 Options | [../09_Options.md](../09_Options.md) | Complete | 30 | Yes | Yes | Not started | **Blocked** — depends on UNKNOWN procs | `PDMOptionDataReport(+WithIncList)`; `TertiayOption` proc column |
| 10 Option Values | [../10_Option_Values.md](../10_Option_Values.md) | Complete | 30 | Yes | Yes | Not started | **Blocked** — depends on UNKNOWN procs | `PDMOptionDataReport(+WithIncList)`; hardcoded option ids 8/28 |
| 11 Configuration | [../11_Configuration.md](../11_Configuration.md) | Complete | 48 | Partial (CADMaintenance ~26k lines; field-level MDB writes UNKNOWN) | Partial | Not started | **Blocked** — 32-bit Jet/OLE DB pCon dependency | Per-field CAD/MDB write paths; pCon package resolution |
| 12 Translations | [../12_Translations.md](../12_Translations.md) | Complete | 30 | Yes | Yes | Not started | **Ready** | — |
| 13 Descriptions | [../13_Descriptions.md](../13_Descriptions.md) | Complete | 37 | Yes | Yes | Not started | **Ready** | — |
| 14 Search | [../14_Search.md](../14_Search.md) | Complete | 45 | Yes | Yes | Not started | **Blocked** — depends on UNKNOWN proc + SQL-injection remediation | `PDMOptionDataReport`; `{text}` injection paths to parameterise |
| 15 Filtering | [../15_Filtering.md](../15_Filtering.md) | Complete | 41 | Yes | Yes | Not started | **Ready** | — |
| 16 Ordering | [../16_Ordering.md](../16_Ordering.md) | Complete | 19 | Yes | Yes | Not started | **Ready** | Per-catalogue ordering path is dead code |
| 17 Images | [../17_Images.md](../17_Images.md) | Complete | 42 | Yes | Yes | Not started | **Ready** | — |
| 18 Pricing | [../18_Pricing.md](../18_Pricing.md) | Complete | 45 | Yes | Yes | Not started | **Blocked** — depends on UNKNOWN procs/functions | `fnGetListPrice`/`ByItem`, `PricePermutation`, `fnGetFabricBandOrderCodes`, `PDMOptionDataReport*`; `CustomPricePerm` is dead |
| 19 OAP | [../19_OAP.md](../19_OAP.md) | Complete | 6 | Partial (CADMaintenance large-file; MDB tables UNKNOWN) | Partial | Not started | **Blocked** — 32-bit Jet/OLE DB (`pcr_data_sel_oas.mdb`) | "OAP" label/terminology; selection MDB table structure |
| 20 ODB | [../20_ODB.md](../20_ODB.md) | Complete | 9 | Partial (CADMaintenance ~26k lines; geometry MDB internals UNKNOWN) | Partial | Not started | **Blocked** — 32-bit Jet/OLE DB (`pcr_data_geo_odb.mdb`) | Geometry MDB columns/keys; ODB exclude-flag column name |
| 21 OCD | [../21_OCD.md](../21_OCD.md) | Complete | 55 | Yes | Yes | **Orphaned / dead** (export path unreachable in current build) | **Blocked** — dead code + UNKNOWN procs | `PDMOptionDataReport`, `fnGetListPriceByItem`, `GetProductOptionCount`; whether export is intended to be revived |
| 22 Export | [../22_Export.md](../22_Export.md) | Complete | 60 | Yes | Yes | Not started (ClippingsExport orphaned/dead) | **Blocked** — depends on UNKNOWN procs | `PDMOptionDataReport*`, `fnGetListPrice*`; DPSDB detach/copy DTS internals |
| 23 Generation | [../23_Generation.md](../23_Generation.md) | Complete | 20 | Yes | Yes | Not started | **Blocked** — depends on UNKNOWN proc + server-side renderer | `PDMPriceListReportForProductGroup`; server-side publication renderer (out of source) |
| 24 Utilities | [../24_Utilities.md](../24_Utilities.md) | Complete | 35 | Yes | Partial (DTS package internals UNKNOWN) | Not started | **Blocked** — `xp_cmdshell`/DTS + 32-bit Jet MDB tooling | `Export_PDM2004_to_DPSDB` DTS package; `dtsrun` behaviour |
| **Total** | | **All Complete** | **769** | | | | **10 Ready / 15 Blocked** | |

> Rule counts reconcile to [../27_Business_Rules_Index.md](../27_Business_Rules_Index.md) (769 total, 25 module prefixes). Doc-level status mirrors [../README.md](../README.md) §8.

---

## Cross-cutting blockers

These affect multiple modules and must be resolved centrally rather than per screen.

1. **UNKNOWN stored-procedure / function bodies (10)** — live only in SQL Server, not in the extracted C# source ([../25_Common_SQL.md](../25_Common_SQL.md) §3). Every dependent module stays **Blocked** until the proc/function bodies are obtained:
   - [ ] `PDMOptionDataReport` (most-depended-on object)
   - [ ] `PDMOptionDataReportWithIncList`
   - [ ] `PDMOptionDataReportWithIncBase`
   - [ ] `PricePermutation`
   - [ ] `PDMPriceListReportForProductGroup`
   - [ ] `fnGetListPrice`
   - [ ] `fnGetListPriceByItem`
   - [ ] `fnGetFabricBandOrderCodes`
   - [ ] `fnGetSPComponentCount`
   - [ ] `GetProductOptionCount`
2. **External `DPS.exe` catalogue maintenance** — real catalogue CRUD is outside the app; internals UNKNOWN ([../03_Catalogues.md](../03_Catalogues.md)).
3. **32-bit Jet / OLE DB pCon dependency** — `pcr_data_{com_ocd,geo_odb,sel_oas,typ_cls}.mdb` via `Microsoft.Jet.OLEDB.4.0`; blocks 11/19/20/24 ([../11_Configuration.md](../11_Configuration.md), [../19_OAP.md](../19_OAP.md), [../20_ODB.md](../20_ODB.md)).
4. **Hardcoded credentials / server names** — must be replaced with a secrets mechanism; never reproduced ([../00_System_Architecture.md](../00_System_Architecture.md)).
5. **SQL-injection remediation** — pervasive inline string-concatenated SQL; parameterise on rebuild ([../25_Common_SQL.md](../25_Common_SQL.md) P-SQL-01).
6. **Inverted `ReadOnly` semantics** — `PDMUserCatalogues.ReadOnly = 1` means *full access*; re-model explicitly ([../02_User_Permissions.md](../02_User_Permissions.md)).
7. **Special-user hardcoding** — `RMAFYT` / `dbacw8` bypass privilege flags; replace with role model ([../01_Authentication.md](../01_Authentication.md), [../02_User_Permissions.md](../02_User_Permissions.md)).
8. **Orphaned / dead code** — `OCDExport`, `ClippingsExport`, `CustomPricePerm`, `CatalogueMaintenance` shell; confirm intended scope before porting (UNKNOWN if any should be revived) ([../21_OCD.md](../21_OCD.md), [../22_Export.md](../22_Export.md)).

---

## Recommended implementation order

Refines [../README.md](../README.md) §6. Foundation modules are unblocked; blocked outputs come last, gated on the stored-proc bodies.

- [ ] **1. Foundation** — 00 Architecture, 01 Authentication, 02 Permissions, 26 Data Model, 25 Common SQL *(resolve cross-cutting blockers 4–7 here)*
- [ ] **2. Core domain** — 03 Catalogues → 04 Categories → 05 Products → 06 Articles *(03/05/06 need blockers 1–2)*
- [ ] **3. Attributes & values** — 07 Attributes → 08 Property Values → 09 Options → 10 Option Values *(08/09/10 need `PDMOptionDataReport`)*
- [ ] **4. Descriptive layer** — 12 Translations → 13 Descriptions → 17 Images *(all Ready)*
- [ ] **5. Commercial layer** — 18 Pricing *(needs pricing procs/functions)*
- [ ] **6. Configuration** — 11 Configuration *(needs Jet-MDB replacement strategy)*
- [ ] **7. Discovery** — 14 Search → 15 Filtering → 16 Ordering *(14 needs proc + injection fix)*
- [ ] **8. Outputs** — 21 OCD → 19 OAP → 20 ODB → 22 Export → 23 Generation *(all Blocked; confirm dead-code scope)*
- [ ] **9. Support** — 24 Utilities *(needs DTS/xp_cmdshell replacement)*

---

## Definition of Done (per module)

A module is **Done** for MK Product Workbench only when all boxes are ticked:

- [ ] **Rules ported** — every `BR-<MODULE>-NNN` from the handbook doc implemented or explicitly deferred with rationale.
- [ ] **SQL parameterised** — all inline/concatenated SQL replaced with parameterised queries (no injection paths; see P-SQL-01).
- [ ] **Dependencies resolved** — classes, tables, helpers, and cross-module dependencies mapped to MK equivalents.
- [ ] **UNKNOWNs resolved** — every UNKNOWN in the module doc closed (proc bodies obtained, MDB tables mapped, magic-number meanings confirmed) or formally accepted as out-of-scope.
- [ ] **Security remediated** — no hardcoded credentials/special-users; inverted-flag semantics re-modelled where relevant.
- [ ] **Dead code confirmed** — orphaned paths (OCD/Clippings/CustomPricePerm/DPS shell) either revived deliberately or dropped.
- [ ] **Tests** — unit/integration tests cover the ported rules and the previously-defective behaviours (identity recovery, ordering, filtering).

---

*Mark items UNKNOWN where unprovable from source. This checklist cross-references the handbook; it must not duplicate module content.*
