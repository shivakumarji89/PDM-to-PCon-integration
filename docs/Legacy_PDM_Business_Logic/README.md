# Legacy PDM — Business Logic Migration Handbook

> **Status:** In progress (living document)
> **Purpose:** Authoritative specification for rebuilding the Legacy PDM system inside **MK Product Workbench**.
> **Scope:** Business-logic extraction only. No code is migrated, refactored, or implemented here.

---

## 1. What this handbook is

This handbook is the result of a **Business Logic Extraction** project against the Legacy PDM
application source code. It captures *verified behaviour only*. Where behaviour cannot be proven
from the source, it is explicitly marked **`UNKNOWN`**.

It is **not**:

- a code migration,
- a refactoring plan,
- an implementation.

It **is** the reference specification that all future MK Product Workbench development should follow.

---

## 2. Source under analysis

| Item | Value |
|------|-------|
| Legacy application | PDM Maintenance (Herman Miller / Knoll PDM) |
| Language / stack | C# (decompiled from VB.NET), .NET WinForms |
| Source root | `c:\Users\siaoca\Desktop\PDM\` |
| Main project | `PDMMaintenance\` |
| Approx. size | ~147 source files, ~190,000 lines |
| Database access | Direct ADO.NET (`System.Data.SqlClient`) against SQL Server |
| Primary DB (default) | Server `DBCHIP12v`, Database `PDMLive` (see [00_System_Architecture](00_System_Architecture.md)) |

> ⚠️ The decompiled source contains **hardcoded credentials and server names**. These are recorded
> in this handbook as *verified legacy facts* and are flagged as **security risks** — they must
> **not** be reproduced in MK Product Workbench.

---

## 3. Folder structure

```
docs/
  Legacy_PDM_Business_Logic/
    README.md                     ← this file
    00_System_Architecture.md
    01_Authentication.md
    02_User_Permissions.md
    03_Catalogues.md
    04_Product_Categories.md
    05_Products.md
    06_Articles.md
    07_Attributes.md
    08_Property_Values.md
    09_Options.md
    10_Option_Values.md
    11_Configuration.md
    12_Translations.md
    13_Descriptions.md
    14_Search.md
    15_Filtering.md
    16_Ordering.md
    17_Images.md
    18_Pricing.md
    19_OAP.md
    20_ODB.md
    21_OCD.md
    22_Export.md
    23_Generation.md
    24_Utilities.md
    25_Common_SQL.md
    26_Data_Model.md
    27_Business_Rules_Index.md    ← aggregated index of every BR-* rule
    28_Call_Hierarchy.md          ← end-to-end execution flow
```

---

## 4. Module summary

| Doc | Module | Primary legacy source | Focus |
|-----|--------|-----------------------|-------|
| 00 | System Architecture | `Global.cs`, `ConnectionFactory.cs`, `MainMenu.cs`, `PDMService.cs` | App startup, DB connectivity, global state |
| 01 | Authentication | `AuthenticateUser.cs`, `MainMenu.cs` | Windows-identity login, privilege load |
| 02 | User Permissions | `AuthenticateUser.cs`, `UserAdmin.cs`, `MainMenu.cs` | Permission flags → menu gating |
| 03 | Catalogues | `CatalogueMaintenance.cs` | Catalogue CRUD, selection state |
| 04 | Product Categories | `OrderCategories.cs`, `metaTypes.cs` | Category tree, ordering |
| 05 | Products | `SuperProductMaintenance.cs`, `metaArticles.cs` | Product/super-product maintenance |
| 06 | Articles | `metaArticles.cs`, `ocdArticle.cs`, `ocdArtBase.cs` | Article records |
| 07 | Attributes | `metaProperties.cs`, `PhysicalMaintenance.cs` | Property/attribute definitions |
| 08 | Property Values | `ocdPropertyValue.cs`, `ocdProperty.cs`, `ocdPropertyClass.cs` | Property value assignment |
| 09 | Options | `OptionClass.cs`, `OptionGroup.cs`, `OptionData.cs` | Option definitions |
| 10 | Option Values | `OptionData.cs` | Option value data |
| 11 | Configuration | `CADMaintenance.cs`, `WebConfigurator.cs` | Configuration / variant conditions |
| 12 | Translations | `metaDescriptions.cs`, `ProductDescriptions.cs` | Language handling |
| 13 | Descriptions | `ProductDescriptions.cs`, `metaDescriptions.cs`, `DescriptionsFindReplace.cs` | Description maintenance |
| 14 | Search | `DataQuery.cs`, `MainMenu.cs` | Lookup / find |
| 15 | Filtering | `UIGroupMaintenance.cs` | UI grouping / filters |
| 16 | Ordering | `OrderCategories.cs` | Sort/priority order |
| 17 | Images | `GetImage.cs`, `ValidateImages.cs`, `ValidateImageThread.cs` | Image resolution/validation |
| 18 | Pricing | `PriceMaintenance.cs`, `FinancialMaintenance.cs`, `PConPriceUpdate.cs`, `CustomPricePerm.cs` | Price data & permissions |
| 19 | OAP | *(to be confirmed in source)* | OAP export/format |
| 20 | ODB | *(to be confirmed in source)* | ODB export/format |
| 21 | OCD | `OCDExport.cs`, `ocd*.cs` family | OCD data model & export |
| 22 | Export | `OFDAExport.cs`, `SytelineExport.cs`, `SIFImport.cs`, `ExportThread.cs`, `BOMExport.cs` | Export/import pipelines |
| 23 | Generation | `HandbookDesigner.cs` | Handbook / document generation |
| 24 | Utilities | `StaticDataMaintenance.cs`, helper classes | Static/reference data & tooling |
| 25 | Common SQL | *(cross-cutting)* | Shared query patterns |
| 26 | Data Model | *(cross-cutting)* | Tables, keys, relationships |
| 27 | Business Rules Index | *(aggregated)* | Every `BR-*` rule with backlinks |
| 28 | Call Hierarchy | *(aggregated)* | Whole-application execution flow |

> Modules **19_OAP** and **20_ODB** are listed in the required output set. Their exact legacy source
> files must be confirmed during extraction; until proven, their contents are marked **`UNKNOWN`**.

---

## 5. Data flow (high level)

```
Windows user identity (Environment.UserName)
        ↓
AuthenticateUser.setUserPrivileges(username)   ← SQL: PDMUserPrivileges
        ↓
MainMenu builds menu, enables features by permission flag
        ↓
User opens a maintenance form (Catalogue / Product / Article / Price / …)
        ↓
Form loads data via direct ADO.NET SqlCommand against SQL Server
        ↓
User edits in DataGrid-style UI
        ↓
Save writes back via INSERT/UPDATE/DELETE (often dynamic SQL)
        ↓
Export/Generation modules read the maintained data and emit OFDA / SIF / OCD / Syteline / Handbook outputs
```

---

## 6. Migration priority (recommended)

Priority is derived from **dependency order** and **risk**. See each module's *Risks* section and
[28_Call_Hierarchy](28_Call_Hierarchy.md) for justification.

1. **Foundation** — 00 Architecture, 01 Authentication, 02 Permissions, 26 Data Model, 25 Common SQL
2. **Core domain** — 03 Catalogues → 04 Categories → 05 Products → 06 Articles
3. **Attributes & values** — 07 Attributes → 08 Property Values → 09 Options → 10 Option Values
4. **Descriptive layer** — 12 Translations → 13 Descriptions → 17 Images
5. **Commercial layer** — 18 Pricing
6. **Configuration** — 11 Configuration
7. **Discovery** — 14 Search → 15 Filtering → 16 Ordering
8. **Outputs** — 21 OCD → 19 OAP → 20 ODB → 22 Export → 23 Generation
9. **Support** — 24 Utilities

---

## 7. Conventions used in every module

Each module document contains the following fixed sections:

1. **Purpose**
2. **Entry Points** (forms, controls, buttons, menus, events, commands)
3. **Call Hierarchy** (Form → Event → Controller → Service → Repository → SQL → Model → UI)
4. **SQL Analysis** (every SELECT / INSERT / UPDATE / DELETE / SP / view / temp table / dynamic SQL, and *why* it exists)
5. **Data Model** (tables, columns, PKs, FKs, relationships, status/flag values, field meanings)
6. **Business Rules** (every rule, uniquely identified `BR-<MODULE>-NNN`)
7. **Hidden Logic** (magic numbers, hardcoded IDs, special users/products, workarounds, tech debt)
8. **UI Behaviour** (what the user sees; refresh/selection/loading/enable-disable rules)
9. **Dependencies** (classes, services, repositories, helpers, tables, configuration)
10. **Risks** (migration risk, complexity, hidden coupling, performance, concurrency, potential bugs)

### Business Rule ID scheme

`BR-<MODULE>-NNN` — e.g. `BR-AUTH-001`, `BR-CAT-001`, `BR-ART-001`, `BR-PRICE-001`.
Module prefixes are defined at the top of each document and collected in
[27_Business_Rules_Index](27_Business_Rules_Index.md).

### Evidence & `UNKNOWN` policy

- Every rule and query is traceable to a **file and construct** in the legacy source.
- Where behaviour depends on data/config not present in source, or on code not yet analysed,
  it is recorded verbatim as **`UNKNOWN`** rather than guessed.

---

## 8. Extraction status

**All 29 module documents complete.** ~769 business rules extracted across 25 module prefixes.

| Doc | Status | Rules |
|-----|--------|-------|
| README | ✅ Complete | — |
| 00_System_Architecture | ✅ Complete (self-verified) | BR-ARCH ×9 |
| 01_Authentication | ✅ Complete (self-verified) | BR-AUTH ×8 |
| 02_User_Permissions | ✅ Complete (self-verified) | BR-PERM ×15 |
| 03_Catalogues | ✅ Complete | BR-CAT ×19 |
| 04_Product_Categories | ✅ Complete | BR-CATEG ×13 |
| 05_Products | ✅ Complete | BR-PROD ×70 |
| 06_Articles | ✅ Complete | BR-ART ×18 |
| 07_Attributes | ✅ Complete | BR-ATTR ×36 |
| 08_Property_Values | ✅ Complete | BR-PVAL ×35 |
| 09_Options | ✅ Complete | BR-OPT ×30 |
| 10_Option_Values | ✅ Complete | BR-OVAL ×30 |
| 11_Configuration | ✅ Complete | BR-CFG ×60 |
| 12_Translations | ✅ Complete | BR-TRAN ×30 |
| 13_Descriptions | ✅ Complete | BR-DESC ×37 |
| 14_Search | ✅ Complete | BR-SRCH ×45 |
| 15_Filtering | ✅ Complete | BR-FILT ×41 |
| 16_Ordering | ✅ Complete | BR-ORD ×19 |
| 17_Images | ✅ Complete | BR-IMG ×39 |
| 18_Pricing | ✅ Complete | BR-PRICE ×45 |
| 19_OAP | ✅ Complete (⚠ "OAP" not in source; covers OAS) | BR-OAP ×6 |
| 20_ODB | ✅ Complete | BR-ODB ×9 |
| 21_OCD | ✅ Complete (⚠ export path is orphaned/dead) | BR-OCD ×55 |
| 22_Export | ✅ Complete | BR-EXP ×60 |
| 23_Generation | ✅ Complete | BR-GEN ×20 |
| 24_Utilities | ✅ Complete | BR-UTIL ×40 |
| 25_Common_SQL | ✅ Complete (synthesis) | — |
| 26_Data_Model | ✅ Complete (synthesis, ~58 tables) | — |
| 27_Business_Rules_Index | ✅ Complete (aggregated, 769 rules) | — |
| 28_Call_Hierarchy | ✅ Complete (aggregated) | — |

### Headline findings (see individual docs for evidence)

- **No interactive login** — identity is the Windows account; privileges load from `PDMUserPrivileges`.
  Two hardcoded special users (`RMAFYT`, `dbacw8`) bypass the flags. → [01](01_Authentication.md), [02](02_User_Permissions.md)
- **Plaintext DB credentials + per-user SQL-login mapping** are embedded in `ConnectionFactory.cs`. → [00](00_System_Architecture.md)
- **`CatalogueMaintenance.cs` is a dead shell** — real catalogue CRUD is an **external `DPS.exe`** launched with `maintenanceCAT`. → [03](03_Catalogues.md)
- **The OCD export (`OCDExport.cs`) is orphaned/dead** in the current build; `ClippingsExport` and `CustomPricePerm` are also dead. → [21](21_OCD.md), [22](22_Export.md), [18](18_Pricing.md), [28](28_Call_Hierarchy.md)
- **`metaTypes/metaProperties/metaDescriptions/ocd*/OptionClass/OptionGroup/OptionData` are export DTOs, not tables.** → [21](21_OCD.md)
- **pCon/OFML data lives in 32-bit Jet MDBs** (`pcr_data_{com_ocd,geo_odb,sel_oas,typ_cls}.mdb`). → [11](11_Configuration.md), [19](19_OAP.md), [20](20_ODB.md)
- **Pervasive inline string-concatenated SQL** (injection) and **inverted `PDMUserCatalogues.ReadOnly`** (1 = full). → [25](25_Common_SQL.md), [02](02_User_Permissions.md)
- **10 stored procedures/functions are referenced but their bodies are not in the source** (e.g. `PDMOptionDataReport`, `fnGetListPrice*`, `PDMPriceListReportForProductGroup`) — marked `UNKNOWN`. → [25](25_Common_SQL.md)

> This table is the single source of truth for extraction status. Note: rule counts reflect the
> per-doc figures reconciled in [27_Business_Rules_Index](27_Business_Rules_Index.md), which is authoritative.
