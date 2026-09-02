# Dependency Map

*Navigation view of the major class/module dependencies in the legacy PDM Maintenance application: which forms depend on which shared helpers, where the external systems sit, and which classes are the high-coupling hubs. Only edges evidenced in the module docs are drawn. Detailed proof lives in each linked module doc and in [28_Call_Hierarchy](../28_Call_Hierarchy.md).*

---

## 1. Major dependency graph

```mermaid
flowchart TD
    MM[MainMenu<br/>shell + permission gates]
    AU[AuthenticateUser<br/>identity + flags]
    CF[ConnectionFactory<br/>connection strings]
    GL[Global<br/>static session state]

    MM --> AU
    MM --> GL
    AU --> CF

    MM --> PD[ProductDescriptions<br/>descriptions / translations / catalogue selector]
    MM --> SPM[SuperProductMaintenance<br/>BOM / products]
    MM --> CAD[CADMaintenance<br/>configuration / options / images]
    MM --> PM[PriceMaintenance / FinancialMaintenance]
    MM --> SDM[StaticDataMaintenance]
    MM --> SE[SytelineExport<br/>export driver]
    MM --> HB[Handbook Designer]
    MM --> DQ[DataQuery<br/>search / query dialogs]
    MM -. Process.Start .-> DPS[[DPS.exe — external]]
    MM --> PUB[PublishDatabase]

    PD --> CF
    SPM --> CF
    CAD --> CF
    PM --> CF
    SDM --> CF
    SE --> CF
    DQ --> CF
    CF --> SQL[(SQL Server<br/>PDMLive / DPSDB)]
    CF -.-> SL[(SyteLine ERP<br/>CreateNewConnectionSyteLine)]

    CAD <--> MDB[[pCon Jet MDBs<br/>tCOMd_* / tGEOd_* via OLE DB]]
    CAD --> MQ[MDBQuery]
    MQ --> MDB
    CAD --> GI[GetImage]
    PD --> GI
    GI --> IMG[[UNC image share / HTTP]]

    SE --> ET[ExportThread / SytelineCSIExport / OFDAExport / SIFExportThread]
    ET --> FILES[[Output files<br/>.xls/.asc/.csv/.xml/.top/.key/.opt]]
    PUB --> DT[ExportDPSDBThread]
    DT --> PT[ProgressThread]
    PT -. xp_cmdshell dtsrun .-> AUD2[(DPSDB)]

    PM --> UPT[UpdatePricesThread / UpdatePriceThread]
    UPT --> MDB

    SQL --- AUDIT[(PDMAudit.dbo.Transactions<br/>audit rows)]
    CAD -. chrome.exe .-> WEB[[Web configurator URL]]
```

> **ProductDescriptions** and **CADMaintenance** are drawn as hubs: they are referenced as primary or secondary sources across many module docs (catalogues, categories, options, option values, translations, descriptions, images).

## 2. Shared helper classes

| Helper | Purpose | Used by | Module doc |
|---|---|---|---|
| `ConnectionFactory` | Builds `SqlConnection` (connection string chosen by server-name substring match; retry/backoff; SyteLine variant) | Every maintenance form + export/import worker | [00_System_Architecture](../00_System_Architecture.md) |
| `Global` | Process-wide static session state (site, catalogue, category, product, currency, language, effective date; hardcoded server names & file paths) | Entire application | [00_System_Architecture](../00_System_Architecture.md) |
| `AuthenticateUser` | Loads Windows-identity privilege row; exposes 30 static permission flags | `MainMenu`, `UserAdmin`, and every gated form | [01_Authentication](../01_Authentication.md), [02_User_Permissions](../02_User_Permissions.md) |
| `DataQuery` | Title-switched query/search dialog; also launches image validation | Search, image validation, ad-hoc query menu items | [14_Search](../14_Search.md), [17_Images](../17_Images.md) |
| `MDBQuery` | pCon Jet/Access MDB query & "find" tool (OLE DB) | `CADMaintenance` and pCon configuration paths | [24_Utilities](../24_Utilities.md), [11_Configuration](../11_Configuration.md) |
| `GetImage` | Resolves an `ImageFile` string to a bitmap by probing base paths (UNC / EOS / HTTP) | Any UI needing an icon/photo/swatch; `CADMaintenance`, `ProductDescriptions` | [17_Images](../17_Images.md) |
| `ProgressThread` | Background worker driving `xp_cmdshell dtsrun` for the DPS DB publish | `ExportDPSDBThread` / Publish DB | [24_Utilities](../24_Utilities.md) |
| `DelayThread` | 500 ms debounce timer | `CADMaintenance` category filter | [24_Utilities](../24_Utilities.md) |
| `TimerThread` | Elapsed `HH:MM:SS` label for long operations | Long-running export/import forms | [24_Utilities](../24_Utilities.md) |
| `InputForm` / `EditDialog` / `ApplicationText` | Generic input / single-value edit / read-only text+image dialogs | Many forms on demand | [24_Utilities](../24_Utilities.md) |
| `AddDataList` / `AddNewData` | Generic list picker / add-new-record dialogs (context-driven SQL, may INSERT) | Options, option values, fabrics, product group codes | [24_Utilities](../24_Utilities.md), [09_Options](../09_Options.md), [10_Option_Values](../10_Option_Values.md) |
| `debug_form` | Generic scrollable text output window | Diagnostics across forms | [24_Utilities](../24_Utilities.md) |

> **UNKNOWN** — the docs describe UI/DataGrid editing via `SqlDataAdapter` bindings within each form; a dedicated named DataGrid helper class is not separately evidenced, so grid behaviour is attributed to the owning forms (e.g. `StaticDataMaintenance`).

## 3. Hub classes / high coupling

| Hub class | Why it is a hub | Evidence |
|---|---|---|
| `ConnectionFactory` | Single choke-point for **all** DB access; every form and worker calls `CreateNewConnection`. Server-name substring logic makes it a brittle central dependency. | [00_System_Architecture](../00_System_Architecture.md) §4 |
| `Global` | Process-wide mutable static state consumed everywhere; order-dependent behaviour and concurrency risk with worker threads. | [00_System_Architecture](../00_System_Architecture.md) §5, BR-ARCH-009 |
| `AuthenticateUser` | 30 permission flags read by `MainMenu` and every gated feature; the authorization backbone. | [01_Authentication](../01_Authentication.md), [02_User_Permissions](../02_User_Permissions.md) |
| `ProductDescriptions` | Catalogue selector + descriptions/translations/options entry point; cited as a source across many module docs (03, 04, 09, 10, 12, 13). | [13_Descriptions](../13_Descriptions.md), [12_Translations](../12_Translations.md) |
| `CADMaintenance` | Configuration, UI Groups, ODB/OAP, options and image validation; the bridge between SQL Server and the pCon MDBs; also launches `chrome.exe` web configurator. | [11_Configuration](../11_Configuration.md), [19_OAP](../19_OAP.md), [20_ODB](../20_ODB.md), [21_OCD](../21_OCD.md) |
| `MainMenu` | Application shell; instantiates every feature form and enforces the permission gates. | [02_User_Permissions](../02_User_Permissions.md), [28_Call_Hierarchy](../28_Call_Hierarchy.md) |
| `SytelineExport` | Central export driver; mode flags fan out to all `*Thread` export workers. | [22_Export](../22_Export.md) |

## 4. External dependencies

| External system | Nature / access | Evidenced in |
|---|---|---|
| **SQL Server** (`PDMLive` on `DBCHIP12v` default; also `DPSDB`, `eoscloud`, dev servers) | Primary datastore; inline ADO.NET; connection string by server-name substring match | [00_System_Architecture](../00_System_Architecture.md) |
| **PDMAudit DB** (`PDMAudit.dbo.Transactions`, `PFUpdates`) | Audit trail for catalogue-affecting writes; **disabled on `eoscloud`** | [24_Utilities](../24_Utilities.md), [28_Call_Hierarchy §3](../28_Call_Hierarchy.md) |
| **pCon Jet MDBs** (`tCOMd_*`, `tGEOd_*`; OAP/ODB/OCD `pcr_data_*.mdb`) | Access/Jet databases accessed via **32-bit OLE DB**; read/write configuration + price relations | [11_Configuration](../11_Configuration.md), [19_OAP](../19_OAP.md), [20_ODB](../20_ODB.md), [21_OCD](../21_OCD.md), [05_Products](../05_Products.md) |
| **External `DPS.exe`** | Launched via `Process.Start` from the Catalogue Maintenance button (the in-app `CatalogueMaintenance` form is a dead shell) | [03_Catalogues](../03_Catalogues.md) |
| **SyteLine ERP** | Separate connection via `ConnectionFactory.CreateNewConnectionSyteLine`; live/test selection; `SL7UserViews` grants; PBOM/material export uses SyteLine-live SQL | [00_System_Architecture](../00_System_Architecture.md), [02_User_Permissions](../02_User_Permissions.md), [22_Export](../22_Export.md) |
| **`chrome.exe`** | `Process.Start("chrome.exe", url)` from `CADMaintenance` web-configurator browse button | [11_Configuration](../11_Configuration.md) |
| **`xp_cmdshell` / `dtsrun`** | Publish DB runs `xp_cmdshell 'dtsrun … -Sdbchip02 -N"Export_PDM2004_to_DPSDB"'` (hard-coded server/package) via `ProgressThread` | [24_Utilities](../24_Utilities.md) |
| **UNC image share / HTTP** (`\\wechip01v\HMEURONET\PDM\`, EOS path, `http://www.hmeuronet.com/PDM/`) | `GetImage` base paths probed to resolve image files | [17_Images](../17_Images.md), [00_System_Architecture](../00_System_Architecture.md) |
| Output files (`.xls`, `.asc`, `.csv`, `.xml`, `.top`, `.key`, `.opt`) | Written by export workers to the file system | [22_Export](../22_Export.md) |

> **UNKNOWN** — exact SyteLine server/database targets beyond the `DBHONP*` / live-vs-test selection convention are not fully enumerated; some external file destinations are configuration-driven and unproven.

---

*See [28_Call_Hierarchy](../28_Call_Hierarchy.md) for execution flow, [00_System_Architecture](../00_System_Architecture.md) for connection internals, and [27_Business_Rules_Index](../27_Business_Rules_Index.md) for cited rules.*
