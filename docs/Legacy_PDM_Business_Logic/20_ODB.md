# 20 — ODB (pCon Geometry Data)

**Module prefix:** `BR-ODB`
**Primary legacy source:** `CADMaintenance.cs`, `MDBQuery.cs`, `ExportLayoutStyleThread.cs`
**Status:** Verified from source unless marked `UNKNOWN`.

> **Cross-reference:** ODB is one of the four pCon/OFML data domains. Its commercial sibling is
> documented in [21_OCD](21_OCD.md); the shared configuration host form is documented in
> [11_Configuration](11_Configuration.md). This document isolates the **geometry (ODB)** concern.

---

## 1. Purpose

**ODB** ("Object/Geometry Data Base") is the **pCon/OFML geometry domain**. In the legacy PDM it
represents the **2D/3D CAD model references** attached to items and the flags that control whether an
item's geometry is exported. The physical store is a Microsoft **Jet/Access MDB** per pCon workspace:
`pcr_data_geo_odb.mdb` (verified in `CADMaintenance.cs` / `MDBQuery.cs`).

The application does **not** author geometry itself; it **maps PDM items to pCon geometry packages**,
assigns 2D/3D model references, and marks items for inclusion/exclusion in the ODB extract.

---

## 2. Entry Points

| Entry point | Source | Purpose |
|-------------|--------|---------|
| CAD Maintenance form (Items/pCon tab) | `CADMaintenance.cs` | Hosts all ODB/geometry actions (gated by `CADMaintenance` privilege — see [02_User_Permissions](02_User_Permissions.md)) |
| `Update pCon 3D model references (ODB export)` menu item | `CADMaintenance.cs` (`UpdatePCon3DModelReferencesToolStripMenuItem`) | Refresh 3D model references from geometry MDB |
| `Update pCon 2D model references (ODB export)` menu item | `CADMaintenance.cs` (`UpdatePCon2DModelReferencesToolStripMenuItem`) | Refresh 2D model references |
| `Exclude Item from ODB Export` / `Exclude Item from ODB Extract` checkbox | `CADMaintenance.cs` (`check_excludefromexport`) | Per-item ODB export opt-out |
| `Apply ODB / Trans / Visibility Flags to all instances…` button | `CADMaintenance.cs` (`ApplyVisFlagToAllButton`) | Bulk-apply ODB/transparency/visibility flags across all instances of a model within the current item scope (filter-based) |
| `Auto Assign NA Revit Families` button | `CADMaintenance.cs` (`AutoAssignRevitButton`) | Assign North-American Revit family references (visible only when `RevitCheck.Checked`) |
| Generic MDB browser | `MDBQuery.cs` | Ad-hoc query of `pcr_data_geo_odb.mdb` when `database == "ODB"` |
| Layout/style export worker | `ExportLayoutStyleThread.cs` | Background export touching geometry/layout (**internals `UNKNOWN`** — not deeply read) |

---

## 3. Call Hierarchy

```
CAD Maintenance form (Items / pCon tab)   [CADMaintenance.cs]
   ↓  (user selects catalogue → category → item)
GetPconPackageId("geo_odb", <catalogue>, <categoryId>, suppress)   ← resolves the pCon geometry package
   ↓
OLE DB (Microsoft.Jet.OLEDB.4.0) open on:
   <pConPath>WS\<workspace>\pcr_data_geo_odb.mdb
   ↓
Read/assign 2D/3D model references (tGEOd_* geometry tables)
   ↓
Apply ODB / transparency / visibility flags per model instance (filter scope)
   ↓
check_excludefromexport toggles per-item ODB export inclusion
   ↓
UI grid updated; changes persisted back to the geometry MDB / PDM item record
```

> The precise write-back statements inside the large `CADMaintenance.cs` handlers are **partially
> `UNKNOWN`** (see [11_Configuration](11_Configuration.md) coverage note); the geometry package
> resolution and MDB connection strings are verified.

---

## 4. SQL Analysis

ODB data access is **OLE DB against Jet MDB**, not SQL Server. Verified connection construction:

### O-ODB-001 — Open geometry MDB (MDBQuery browser)
**Type:** OLE DB connection. **Source:** `MDBQuery.cs`.
```text
Provider=Microsoft.Jet.OLEDB.4.0;Data Source=<CADMaintenance.pConPath>WS\<workspace>\pcr_data_geo_odb.mdb
```
Selected when the browser's `_database == "ODB"`. **Why:** ad-hoc inspection/query of the geometry store.

### O-ODB-002 — Open geometry MDB (CAD maintenance geometry ops)
**Type:** OLE DB connection. **Source:** `CADMaintenance.cs`.
```text
Provider=Microsoft.Jet.OLEDB.4.0;Data Source=<pConPath>WS\<workspace>\pcr_data_geo_odb.mdb
```
Also constructed generically as `...pcr_data_<context>.mdb` where `context == "geo_odb"`.
**Why:** read/write geometry package + model-reference data for the selected item.

### O-ODB-003 — Package resolution
**Type:** query via helper `GetPconPackageId("geo_odb", <catalogueName>, <categoryId>, suppress)`.
**Source:** `CADMaintenance.cs`. **Why:** determine which pCon geometry **package** corresponds to the
selected PDM catalogue/category before reading geometry. (Resolution algorithm — "most-matches-wins"
voting against master items — is documented in [11_Configuration](11_Configuration.md).)

> The `tGEOd_*` table read/write column lists are enumerated in [11_Configuration](11_Configuration.md)
> §Data Model. Field-level UPDATE/INSERT statements within the 26k-line form are **`UNKNOWN`** beyond
> what is captured there.

---

## 5. Data Model

### pCon geometry MDB — `pcr_data_geo_odb.mdb` (Jet/Access, per workspace)

| Table (as referenced) | Role |
|-----------------------|------|
| `tGEOd_Package` | Geometry package header (unit of geometry distribution) |
| `tGEOd_Object` | Geometry objects within a package |
| `tGEOd_Node2D` / `tGEOd_Node3D` | 2D / 3D geometry nodes (model references) |
| `tGEOd_Layer` | Geometry layer definitions |

> Exact columns/keys are Jet-internal; those observed via `CreateNode`/reference assignment are listed in
> [11_Configuration](11_Configuration.md). Anything not observed is **`UNKNOWN`**.

### PDM-side item fields relevant to ODB (SQL Server `Item`)

| Field | Meaning (verified/observed) |
|-------|------------------------------|
| `CADImage3D` | 3D model reference for the item |
| `CADImage2D` | 2D model reference; value `'master'` designates a master item used for package voting |
| `Notes` | Holds master-item prefixes used in package resolution |
| *(ODB exclude flag)* | Backing column for `check_excludefromexport` — **name `UNKNOWN`** (UI text "Exclude Item from ODB Export/Extract") |

---

## 6. Business Rules

- **BR-ODB-001** — ODB (geometry) data is stored in per-workspace Jet MDB files named
  `pcr_data_geo_odb.mdb`, accessed via `Microsoft.Jet.OLEDB.4.0`. *Source:* `CADMaintenance.cs`, `MDBQuery.cs`.
- **BR-ODB-002** — The geometry MDB path is `<pConPath>WS\<workspace>\pcr_data_geo_odb.mdb`; `<workspace>`
  is resolved from the selected catalogue (see [11_Configuration](11_Configuration.md)). *Source:* `CADMaintenance.cs`.
- **BR-ODB-003** — The correct geometry **package** for a catalogue/category is resolved by
  `GetPconPackageId("geo_odb", …)` before any geometry read. *Source:* `CADMaintenance.cs`.
- **BR-ODB-004** — Items may be **individually excluded** from the ODB export via the
  `check_excludefromexport` toggle (UI text "Exclude Item from ODB Export" / "…Extract"). *Source:* `CADMaintenance.cs`.
- **BR-ODB-005** — 2D and 3D model references are updated by **separate** menu actions
  ("Update pCon 2D/3D model references (ODB export)"). *Source:* `CADMaintenance.cs`.
- **BR-ODB-006** — ODB / transparency / visibility flags can be **bulk-applied** to *all instances* of a
  selected model within the current item scope, constrained by the active UI filter. *Source:* `CADMaintenance.cs` (`ApplyVisFlagToAllButton`).
- **BR-ODB-007** — The **Revit** family auto-assignment action is only available when `RevitCheck.Checked`
  is true; the button targets **North-American ("NA") Revit families**. *Source:* `CADMaintenance.cs`.
- **BR-ODB-008** — An item with `CADImage2D == 'master'` is treated as a **master item** and participates
  in package resolution voting. *Source:* `CADMaintenance.cs` (cross-ref [11_Configuration](11_Configuration.md)).
- **BR-ODB-009** — All ODB access requires the `CADMaintenance` privilege (the whole form is gated by it).
  *Source:* `MainMenu.cs` ~3058 (see [02_User_Permissions](02_User_Permissions.md)).

> Additional per-field geometry rules inside `CADMaintenance.cs` are **`UNKNOWN`** pending deeper extraction
> of that 26k-line file.

---

## 7. Hidden Logic

- **32-bit Jet/OLE DB dependency.** `Microsoft.Jet.OLEDB.4.0` is 32-bit only — the whole ODB path requires
  an x86 process and an installed Jet provider. This is an implicit deployment constraint.
- **`context`-templated MDB name.** The connection string is built generically as
  `pcr_data_<context>.mdb`; `context == "geo_odb"` selects geometry. The same code path can therefore open
  `com_ocd`, `sel_oas`, `typ_cls` by changing `context` (see [19_OAP](19_OAP.md), [21_OCD](21_OCD.md)).
- **`'master'` sentinel** in `CADImage2D` overloads a geometry-reference column with a role marker.
- **"NA Revit" hardcoding** ties an action to a North-American Revit family convention.

---

## 8. UI Behaviour

- ODB actions live on the **Items/pCon tab** of the CAD Maintenance form; the user picks
  catalogue → category → item, and the grid shows model references and flags.
- 2D/3D reference refresh and flag application are **explicit button/menu actions** (no auto-refresh).
- The Revit auto-assign button **appears/disappears** with the `RevitCheck` checkbox.
- Read-only enforcement follows the CAD form's `ReadOnly == 0` convention plus the `_pConCreatorUsers`
  allow-list (see [11_Configuration](11_Configuration.md)).

---

## 9. Dependencies

| Kind | Item |
|------|------|
| Form | `CADMaintenance` |
| Helper | `MDBQuery` (ad-hoc MDB browser), `GetPconPackageId`, `CreateNode` |
| Worker | `ExportLayoutStyleThread` (**internals UNKNOWN**) |
| Data (external) | Jet MDB `pcr_data_geo_odb.mdb` (`tGEOd_*` tables) |
| Data (SQL) | `Item` (`CADImage2D`, `CADImage3D`, `Notes`) |
| Provider | `Microsoft.Jet.OLEDB.4.0` (32-bit) |
| Permission | `CADMaintenance` flag |

---

## 10. Risks

- **High — 32-bit Jet/OLE DB lock-in.** Geometry access cannot run in a 64-bit process and depends on a
  deprecated provider; a rebuild needs a different geometry-data strategy.
- **High — Large-form coverage gap.** The authoritative geometry write logic sits inside `CADMaintenance.cs`
  (~26k lines) and is only partially extracted; migration must re-verify each geometry handler.
- **Medium — File/workspace path coupling.** Behaviour depends on `pConPath` and per-workspace MDB layout on
  a specific share; environment changes silently break geometry resolution.
- **Medium — Overloaded columns/sentinels** (`CADImage2D == 'master'`) obscure intent.
- **Unknown — ODB exclude flag column** name/semantics and `ExportLayoutStyleThread` behaviour remain `UNKNOWN`.
