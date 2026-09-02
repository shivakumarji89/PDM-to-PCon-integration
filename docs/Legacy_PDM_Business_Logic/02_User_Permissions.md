# 02 — User Permissions

**Module prefix:** `BR-PERM`
**Primary legacy source:** `AuthenticateUser.cs`, `UserAdmin.cs`, `MainMenu.cs`
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

Defines the **permission model**: the set of per-user capability flags, the per-catalogue access grants,
and how those flags **gate the main-menu feature buttons**. Permissions are stored in the database and
administered through the `UserAdmin` form.

Authentication (identity resolution) is covered in [01_Authentication](01_Authentication.md); this
document covers *authorization*.

---

## 2. Entry Points

| Entry point | Source | Purpose |
|-------------|--------|---------|
| `UserAdmin` form | `UserAdmin.cs` | CRUD UI for user privileges, catalogue access, and Syteline views |
| `MainMenu` init (~3004–3090) | `MainMenu.cs` | Reads `AuthenticateUser.*` flags → builds `enabledButtons` |
| `AdminButton` | `MainMenu.cs` | Opens user administration (visible to admins + special users) |
| `DeleteItemsToolStripMenuItem` | `MainMenu.cs` | Visible only to `PDMAdministrator` |

---

## 3. Call Hierarchy

```
Admin edits permissions:
  UserAdmin form
     ↓ (checkbox toggle per capability)
  UPDATE PDMUserPrivileges SET <Flag> = <0|1> WHERE UserId = <id>
  INSERT/UPDATE/DELETE PDMUserCatalogues   (per-catalogue read/full/none)
  INSERT/DELETE SL7UserViews               (Syteline view grants)

Runtime enforcement:
  MainMenu init
     ↓
  AuthenticateUser.setUserPrivileges(user)   → loads flags
     ↓
  MainMenu evaluates each flag → enabledButtons.Add("<Button>")
     ↓
  Buttons not added remain hidden/disabled
```

---

## 4. SQL Analysis

### Q-PERM-001 — Load a user's full profile (UserAdmin)
**Type:** `SELECT`. **Source:** `UserAdmin.cs` ~2434.
Selects `FullName, SkypeName, UserId, Default*`, all capability flags, and `BOMManager`
(via the same correlated-subquery + `CROSS JOIN (SELECT NULL AS BOMManager)` pattern as authentication)
`FROM PDMUserPrivileges p1 WHERE p1.UserId = <num>`.
**Why:** populate the admin editor for a selected user.

### Q-PERM-002 — List users
**Type:** `SELECT`. **Source:** `UserAdmin.cs` ~2573.
```sql
SELECT UserId, UserName,
       CASE WHEN FullName Is NULL THEN UserName ELSE FullName END AS FullName
FROM PDMUserPrivileges WHERE <criteria>
```
**Why:** populate the user list; display `FullName` falling back to `UserName` when null.

### Q-PERM-003 — Toggle a capability flag
**Type:** `UPDATE`. **Source:** `UserAdmin.cs` (many, ~2837–3466).
Pattern: `UPDATE PDMUserPrivileges SET <Flag> = <0|1> WHERE UserId = <id>` (or `WHERE UserName = ...`).
Flags updated individually include: `CoreMaintenance, DescriptionMaintenance, CatalogueMaintenance,
ProductMaintenance, ItemMaintenance, PriceMaintenance, SuperProductMaintenance, CommodityMaintenance,
SiteMaintenance, CurrencyMaintenance, FormulaMaintenance, HandbookPublication, ProductCodeMaintenance,
SytelineExport, PDMImport, PDMAuditer, PDMTester, ExchangeRates, CADMaintenance, BOMManager,
ReadOnlyFinancial, DescriptionEdit`.
**Why:** each capability is toggled by its own statement.

### Q-PERM-004 — Grant/revoke catalogue access
**Type:** `INSERT` / `UPDATE` / `DELETE`. **Source:** `UserAdmin.cs` ~2702–2708.
```sql
-- Read-only grant (list "catalogues_read")
INSERT INTO PDMUserCatalogues (UserId, CatalogueId, ReadOnly) VALUES (<uid>, <cid>, 0)
UPDATE PDMUserCatalogues SET ReadOnly = 0 WHERE UserId = <uid> AND CatalogueId = <cid>
-- Full grant (list "catalogues_full")
INSERT INTO PDMUserCatalogues (UserId, CatalogueId, ReadOnly) VALUES (<uid>, <cid>, 1)
UPDATE PDMUserCatalogues SET ReadOnly = 1 WHERE UserId = <uid> AND CatalogueId = <cid>
-- Revoke
DELETE FROM PDMUserCatalogues WHERE UserId = <uid> AND CatalogueId = <cid>
```
**Why:** per-user, per-catalogue access control with a read-only vs full distinction.
> ⚠️ Note the **counter-intuitive `ReadOnly` semantics**: `ReadOnly = 1` is used for the **"full"** list and
> `ReadOnly = 0` for the **"read"** list (see BR-PERM-009 / Hidden Logic).

### Q-PERM-005 — Grant/revoke Syteline views
**Type:** `INSERT` / `DELETE`. **Source:** `UserAdmin.cs` ~2780–2785.
```sql
INSERT INTO SL7UserViews (UserId, ViewName) VALUES (<uid>, '<view>')
DELETE FROM SL7UserViews WHERE UserId = <uid> AND ViewName = '<view>'
```
**Why:** controls which Syteline SQL views a user may access.

### Q-PERM-006 — Database view/permission enumeration
**Type:** `SELECT` over system catalog. **Source:** `UserAdmin.cs` ~2389.
Queries `sysobjects` (type `'V'`, name like `HM_%`) joined with `PDMUserPrivileges`/`sysusers`.
**Why:** map SQL Server views (named `HM_*`) to user grants. Exact projection **`UNKNOWN`** (line truncated).

---

## 5. Data Model

### Table: `PDMUserPrivileges`
See [01_Authentication](01_Authentication.md) §5 for the full column list. Additional column observed here:
`FullName` (nullable; falls back to `UserName` for display).

### Table: `PDMUserCatalogues`
| Column | Meaning |
|--------|---------|
| `UserId` (FK → `PDMUserPrivileges.UserId`) | User granted access |
| `CatalogueId` (FK → catalogue) | Catalogue the grant applies to |
| `ReadOnly` (bit) | **`1` = full-access list, `0` = read list** (see BR-PERM-009) |

Composite key inferred: (`UserId`, `CatalogueId`).

### Table: `SL7UserViews`
| Column | Meaning |
|--------|---------|
| `UserId` (FK) | User granted the view |
| `ViewName` | Name of the Syteline SQL view (e.g. `HM_*`) |

---

## 6. Business Rules

### Capability flags (complete list — verified)

- **BR-PERM-001** — The permission model is the following **30 capability flags** on `PDMUserPrivileges`:
  `PDMAdministrator, DatabasePublication, HandbookPublication, SytelineExport, CoreMaintenance,
  ItemMaintenance, FormulaMaintenance, CurrencyMaintenance, ProductCodeMaintenance, SiteMaintenance,
  ProductMaintenance, SuperProductMaintenance, PriceMaintenance, CatalogueMaintenance,
  DescriptionMaintenance, PDMAuditer, PDMTester, CommodityMaintenance, PDMImport, ExchangeRates,
  CADMaintenance, ReadOnlyFinancial, DescriptionEdit, BOMManager` (plus `Default*` context values).
  *Source:* `AuthenticateUser.cs`, `UserAdmin.cs`.

### Menu gating (verified from `MainMenu.cs` ~3016–3087)

- **BR-PERM-002** — **Publish DB** button requires `DatabasePublication` **AND** the connected DB equals
  `Global.primaryPDMDatabase` (`PDMLive`). *Source:* `MainMenu.cs` ~3017.
- **BR-PERM-003** — **Product Maintenance** button requires `ProductMaintenance` **OR** `BOMManager`.
  *Source:* `MainMenu.cs` ~3021.
- **BR-PERM-004** — **PDM Import** button requires `PDMImport` **AND** the server is **not** an `eoscloud`
  server. *Source:* `MainMenu.cs` ~3041.
- **BR-PERM-005** — **Handbook** button requires `HandbookPublication` **AND** non-`eoscloud` server.
  *Source:* `MainMenu.cs` ~3062.
- **BR-PERM-006** — **Audit** button requires `PDMAuditer` **AND** DB not `(local)` **AND** DB not `POSH`
  **AND** server not `eoscloud`. *Source:* `MainMenu.cs` ~3066.
- **BR-PERM-007** — **Web Configurator** button requires `CoreMaintenance` **AND** non-`eoscloud` server;
  when `CoreMaintenance` is false, `ImportMaterialsInToCSIToolStripMenuItem` is disabled.
  *Source:* `MainMenu.cs` ~3078–3087.
- **BR-PERM-008** — **Static Maintenance** button is shown if **any** of `ExchangeRates, ReadOnlyFinancial,
  SiteMaintenance, CurrencyMaintenance, ProductCodeMaintenance, FormulaMaintenance` is true.
  *Source:* `MainMenu.cs` ~3054.
- Single-flag gates (verified): `CatalogueMaintenance→CatMaintButton`, `DescriptionMaintenance→ProdDescButton`,
  `PriceMaintenance→PriceMaintButton`, `SytelineExport→SLExportButton`, `ItemMaintenance→DPSItemEntryButton`,
  `SuperProductMaintenance→SuperProdButton`, `CADMaintenance→CADButton`, `CommodityMaintenance→PhysDataButton`,
  `PDMTester→ValidationButton`. The `DPSBrowserButton` is **always** added (no flag). *Source:* `MainMenu.cs` ~3021–3078.

### Administration

- **BR-PERM-009** — Catalogue access is stored in `PDMUserCatalogues.ReadOnly` where **`1` = full-access**
  grant and **`0` = read grant** — the flag value is inverted relative to its name. *Source:* `UserAdmin.cs` ~2702–2705.
- **BR-PERM-010** — Revoking catalogue access **deletes** the `PDMUserCatalogues` row rather than clearing a flag.
  *Source:* `UserAdmin.cs` ~2708.
- **BR-PERM-011** — Each capability flag is toggled by its **own dedicated `UPDATE` statement** (there is no
  single "save all" statement). *Source:* `UserAdmin.cs` ~2837–3466.
- **BR-PERM-012** — User display name uses `FullName`, falling back to `UserName` when `FullName IS NULL`.
  *Source:* `UserAdmin.cs` ~2573.

### Special-user overrides (verified from `MainMenu.cs` ~3004–3009)

- **BR-PERM-013** — The **Admin button** is visible if `PDMAdministrator` **OR** the Windows user is
  `RMAFYT` (case-insensitive). *Source:* `MainMenu.cs` ~3004.
- **BR-PERM-014** — The Windows user `dbacw8` is **unconditionally** granted Admin-button visibility (a second,
  separate override). *Source:* `MainMenu.cs` ~3006.
- **BR-PERM-015** — **Delete Items** menu item is visible only when `PDMAdministrator` is true.
  *Source:* `MainMenu.cs` ~3005.

---

## 7. Hidden Logic

- **Inverted `ReadOnly` semantics** (BR-PERM-009): the column named `ReadOnly` holds `1` for *full* access.
  This is a genuine trap for migration.
- **Hardcoded special users** `RMAFYT` and `dbacw8` receive admin capabilities in code, bypassing the DB flags.
- **Environment coupling in authorization:** several buttons are gated not only by permission but by the
  **connected server/database** (`eoscloud`, `POSH`, `(local)`, `PDMLive`). Authorization is therefore
  *environment-sensitive*, not purely user-based.
- **`HM_%` view convention:** Syteline/DB views are identified by a `HM_` name prefix (`sysobjects` query).
- **`BOMManager`** continues to be special-cased (string/int rather than bool) — see [01_Authentication](01_Authentication.md) BR-AUTH-005.

---

## 8. UI Behaviour

- The main menu shows **only** the buttons whose gate conditions pass; all menu buttons are first hidden,
  then selectively re-enabled (`enabledButtons.Add(...)`). *Source:* `MainMenu.cs` ~3011–3090.
- `UserAdmin` presents per-capability checkboxes and dual list boxes (`catalogues_read` / `catalogues_full`)
  plus a Syteline views list; each toggle issues its own SQL immediately.
- Changing a user's permissions does **not** live-refresh that user's running session — flags are read once at
  menu init (**`UNKNOWN`** whether any refresh path exists elsewhere).

---

## 9. Dependencies

| Kind | Item |
|------|------|
| Classes | `AuthenticateUser`, `UserAdmin`, `MainMenu` |
| Tables | `PDMUserPrivileges`, `PDMUserCatalogues`, `SL7UserViews`, `sysobjects`, `sysusers` |
| Global state | `Global.connectedServer`, `Global.connectedDB`, `Global.primaryPDMDatabase` |
| Connectivity | `ConnectionFactory` |
| Runtime | `Environment.UserName`, `Microsoft.VisualBasic` |

---

## 10. Risks

- **CRITICAL — SQL injection** throughout `UserAdmin` (ids and view names concatenated into SQL).
- **High — Hardcoded special users** (`RMAFYT`, `dbacw8`) grant privilege outside the data model; easy to miss
  in migration and a security concern.
- **High — Inverted `ReadOnly` flag** will cause access-control bugs if copied literally.
- **High — Environment-sensitive authorization** (server/DB name checks) mixes deployment topology with
  permissions; the Workbench needs an explicit environment/config abstraction.
- **Medium — Per-flag `UPDATE` statements** are chatty and non-transactional; partial failures can leave
  inconsistent permission sets.
- **Medium — No session refresh** of permissions; changes take effect only on restart (assumed).
- **Low/Unknown — `HM_%` view grant projection** (Q-PERM-006) not fully extracted.
