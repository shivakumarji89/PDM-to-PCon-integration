# 19 — OAP / OAS (pCon Selection Data)

**Module prefix:** `BR-OAP`
**Primary legacy source:** `CADMaintenance.cs`, `MDBQuery.cs`
**Status:** Verified from source unless marked `UNKNOWN`.

> ⚠️ **Naming note (important):** The required module list names this document **"OAP"**. **No `OAP`
> identifier exists anywhere in the legacy source** (verified by full-text search of `PDMMaintenance\*.cs`).
> The nearest — and almost certainly intended — legacy concept is **`OAS`**, the pCon **selection** data
> domain stored in `pcr_data_sel_oas.mdb`. This document therefore covers **OAS**, and explicitly flags the
> `OAP` label itself as **`UNKNOWN`/unconfirmed terminology**. If "OAP" refers to a different, external
> artifact, that artifact is **not present** in this codebase.

---

## 1. Purpose

**OAS** ("Object/Article Selection") is the **pCon/OFML selection domain** — the data that drives how a
configurable article's **selectable features/options** are presented and chosen in the pCon/OFML runtime.
Like the other pCon domains it is stored per workspace as a Microsoft **Jet/Access MDB**:
`pcr_data_sel_oas.mdb` (verified in `MDBQuery.cs` and `CADMaintenance.cs`).

The four sibling pCon domains (verified from the `MDBQuery` database selector `{ "OCD", "ODB", "OAS", "CLS" }`):

| Selector | MDB file | Domain | Handbook doc |
|----------|----------|--------|--------------|
| `OCD` | `pcr_data_com_ocd.mdb` | Commercial data | [21_OCD](21_OCD.md) |
| `ODB` | `pcr_data_geo_odb.mdb` | Geometry data | [20_ODB](20_ODB.md) |
| `OAS` | `pcr_data_sel_oas.mdb` | **Selection data** (this doc) | 19 (this) |
| `CLS` | `pcr_data_typ_cls.mdb` | Type/class data | see [11_Configuration](11_Configuration.md) |

---

## 2. Entry Points

| Entry point | Source | Purpose |
|-------------|--------|---------|
| CAD Maintenance form (pCon tab) | `CADMaintenance.cs` | Host for all pCon-domain operations (gated by `CADMaintenance` privilege) |
| Generic MDB browser (`database_selector` → `"OAS"`) | `MDBQuery.cs` | Ad-hoc query of `pcr_data_sel_oas.mdb` |
| pCon package resolution | `CADMaintenance.cs` (`GetPconPackageId`) | Resolve the selection package for a catalogue/category |

> There is **no dedicated "OAS/OAP maintenance" form**. Selection data is reached only through the shared
> CAD Maintenance pCon tooling and the `MDBQuery` browser.

---

## 3. Call Hierarchy

```
CAD Maintenance form (pCon tab)   [CADMaintenance.cs]
   ↓  (catalogue → category selection)
GetPconPackageId("sel_oas" | context, …)     ← resolve selection package  [see 11_Configuration]
   ↓
OLE DB (Microsoft.Jet.OLEDB.4.0) open on:
   <pConPath>WS\<workspace>\pcr_data_sel_oas.mdb
   ↓
Read/inspect selection tables
   ↓
UI grid displays selection data
```

> The write/update paths for selection data inside `CADMaintenance.cs` are **`UNKNOWN`** (large-file
> coverage limit — see [11_Configuration](11_Configuration.md)). Only the connection/resolution is verified.

---

## 4. SQL Analysis

### O-OAS-001 — Open selection MDB (MDBQuery browser)
**Type:** OLE DB connection. **Source:** `MDBQuery.cs`.
```text
Provider=Microsoft.Jet.OLEDB.4.0;Data Source=<CADMaintenance.pConPath>WS\<workspace>\pcr_data_sel_oas.mdb
```
Selected when `_database == "OAS"`. **Why:** ad-hoc inspection/query of the selection store.

### O-OAS-002 — Generic context-templated open
**Type:** OLE DB connection. **Source:** `CADMaintenance.cs`.
```text
Provider=Microsoft.Jet.OLEDB.4.0;Data Source=<pConPath>WS\<workspace>\pcr_data_<context>.mdb
```
With `context == "sel_oas"` this opens the selection MDB. **Why:** unified access across pCon domains.

> Table-level `SELECT/INSERT/UPDATE` statements against the selection tables are **`UNKNOWN`** — not
> recovered from the source within coverage limits.

---

## 5. Data Model

### pCon selection MDB — `pcr_data_sel_oas.mdb` (Jet/Access, per workspace)

The internal table/column structure of the selection MDB is **`UNKNOWN`** from the source read to date.
By OFML convention it holds article-selection / feature-choice definitions, but **no specific table or
column has been verified** in the legacy code beyond the file identity itself. Marked `UNKNOWN` rather than
guessed.

---

## 6. Business Rules

- **BR-OAP-001** — pCon **selection** data is stored per workspace in `pcr_data_sel_oas.mdb`, accessed via
  `Microsoft.Jet.OLEDB.4.0`. *Source:* `MDBQuery.cs`, `CADMaintenance.cs`.
- **BR-OAP-002** — The `MDBQuery` browser exposes exactly four pCon domains — `OCD`, `ODB`, `OAS`, `CLS` —
  each mapping to a fixed MDB filename. *Source:* `MDBQuery.cs` (`database_selector` items).
- **BR-OAP-003** — The selection MDB path follows the same `<pConPath>WS\<workspace>\pcr_data_sel_oas.mdb`
  convention as the other pCon domains. *Source:* `MDBQuery.cs`, `CADMaintenance.cs`.
- **BR-OAP-004** — Access to selection data requires the `CADMaintenance` privilege (whole form gate).
  *Source:* `MainMenu.cs` ~3058.
- **BR-OAP-005** — There is **no standalone OAS/OAP maintenance UI**; selection data is only reachable via
  the shared CAD Maintenance pCon tooling and the `MDBQuery` browser. *Source:* `CADMaintenance.cs`, `MDBQuery.cs`.
- **BR-OAP-006 (`UNKNOWN`)** — The meaning of the label **"OAP"** in the required module list is
  **unconfirmed**; the legacy source contains only **"OAS"**. Any OAP-specific behaviour is `UNKNOWN`.

---

## 7. Hidden Logic

- **Domain selector is a fixed 4-item list** (`OCD/ODB/OAS/CLS`) — pCon domains are hardcoded, not discovered.
- **32-bit Jet/OLE DB dependency** (as with ODB/OCD) — x86-only, deprecated provider.
- **Terminology drift:** the handbook's requested "OAP" vs the code's "OAS" is a genuine naming mismatch and
  a migration trap — do not assume they are different systems without external confirmation.

---

## 8. UI Behaviour

- Selection data is viewed through the CAD Maintenance pCon tab or the `MDBQuery` browser after choosing
  the `OAS` domain; results display in a grid.
- No auto-refresh; access is explicit and read-oriented in the paths verified.

---

## 9. Dependencies

| Kind | Item |
|------|------|
| Form | `CADMaintenance` |
| Helper | `MDBQuery`, `GetPconPackageId` |
| Data (external) | Jet MDB `pcr_data_sel_oas.mdb` |
| Provider | `Microsoft.Jet.OLEDB.4.0` (32-bit) |
| Permission | `CADMaintenance` flag |

---

## 10. Risks

- **High — Undefined scope.** Because "OAP" is not in the source and the OAS internals are `UNKNOWN`, this is
  the **least-verified** module. Migration must first **confirm what "OAP" means** with a domain owner before
  any rebuild; otherwise scope is guesswork (explicitly avoided here).
- **High — 32-bit Jet/OLE DB lock-in** (shared with ODB/OCD).
- **Medium — No dedicated UI / no verified writes** means the true maintenance workflow (if any) may live
  entirely inside `CADMaintenance.cs` or in an external pCon tool outside this codebase.
- **Medium — Hardcoded domain list and workspace paths** couple behaviour to a specific share layout.
