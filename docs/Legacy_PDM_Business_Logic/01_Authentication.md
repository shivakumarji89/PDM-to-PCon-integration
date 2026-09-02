# 01 — Authentication

**Module prefix:** `BR-AUTH`
**Primary legacy source:** `AuthenticateUser.cs`, `MainMenu.cs`
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

Establishes *who the current user is* and *what they are allowed to do*. The Legacy PDM application does
**not** present a username/password login screen. Instead it authenticates implicitly using the **Windows
identity** of the running process and loads a per-user privilege record from the database.

---

## 2. Entry Points

| Entry point | Source | Trigger |
|-------------|--------|---------|
| `AuthenticateUser.setUserPrivileges(username)` | `AuthenticateUser.cs` | Called from `MainMenu` during initialization (`MainMenu.cs` ~line 3016) |
| `Environment.UserName` | .NET runtime | Supplies the current Windows account name (lower-cased) |

There is **no interactive login form**. Identity = the Windows account under which the app runs.

---

## 3. Call Hierarchy

```
MainMenu init
   ↓
AuthenticateUser.setUserPrivileges(Environment.UserName.ToLower())   [MainMenu.cs ~3016]
   ↓
ConnectionFactory.CreateNewConnection(autoOpen: true)               [00_System_Architecture]
   ↓
SqlCommand: SELECT ... FROM PDMUserPrivileges p1 ... WHERE p1.UserName = '<username>'
   ↓
SqlDataReader loop → populate static fields on AuthenticateUser
   ↓
Reader/connection closed
   ↓
MainMenu reads AuthenticateUser.* flags to build the menu   [02_User_Permissions]
```

---

## 4. SQL Analysis

### Q-AUTH-001 — Load user privileges

**Type:** `SELECT` (single row expected, via `SqlDataReader`).
**Source:** `AuthenticateUser.setUserPrivileges`.

```sql
SELECT UserId, SkypeName, DefaultDealerNum, DefaultSiteId, DefaultLanguageId,
       DefaultCurrencyId, DefaultCatalogueId, PDMAdministrator, DatabasePublication,
       HandbookPublication, SytelineExport, CoreMaintenance, ItemMaintenance,
       FormulaMaintenance, CurrencyMaintenance, ProductCodeMaintenance, SiteMaintenance,
       ProductMaintenance, SuperProductMaintenance, PriceMaintenance, CatalogueMaintenance,
       DescriptionMaintenance, PDMAuditer, PDMTester, CommodityMaintenance, PDMImport,
       ExchangeRates, CADMaintenance, ReadOnlyFinancial, DescriptionEdit,
       ( SELECT BOMManager FROM PDMUserPrivileges p2 WHERE p2.UserId = p1.UserId ) AS BOMManager
FROM PDMUserPrivileges p1
CROSS JOIN ( SELECT NULL AS BOMManager ) x
WHERE p1.UserName = '<username>'
```

**Why it exists:** loads the entire permission profile for the logged-in Windows user in one round trip.

**Notable construction details (verified):**

- The query is built by **string concatenation** with the raw username → **SQL injection risk**
  (`... WHERE p1.UserName = '" + username + "'"`).
- `BOMManager` is fetched via a **correlated subquery** joined through a `CROSS JOIN (SELECT NULL AS BOMManager)`.
  This is a defensive pattern so the outer column list always resolves even if `BOMManager` handling differs;
  the real value is read from the correlated subquery. The reader then interprets it specially (see BR-AUTH-005).
- All other flags are read with `bool.Parse(reader["Flag"].ToString())`.

---

## 5. Data Model

### Table: `PDMUserPrivileges`

One row per user. Columns consumed by authentication:

| Column | Type (inferred) | Meaning |
|--------|-----------------|---------|
| `UserId` | int (PK) | Internal user id. Loaded into `AuthenticateUser.UserId`. |
| `UserName` | string | Windows account name; **lookup key** (compared to `Environment.UserName.ToLower()`). |
| `SkypeName` | string | Stored into `AuthenticateUser.Preferences` (field is reused; see Hidden Logic). |
| `DefaultDealerNum` | int | Default dealer. Default `1`. |
| `DefaultSiteId` | int | Default site. Default `1`. |
| `DefaultLanguageId` | int | Default language. Default `1`. |
| `DefaultCurrencyId` | int | Default currency. Default `1`. |
| `DefaultCatalogueId` | int | Default catalogue. Default `1`. |
| `PDMAdministrator` … `DescriptionEdit` | bit | Permission flags — see [02_User_Permissions](02_User_Permissions.md). |
| `BOMManager` | bit/int | Special-cased flag (string→`1`→true, else false). |

**Primary key:** `UserId` (inferred). **Lookup key:** `UserName`.

---

## 6. Business Rules

- **BR-AUTH-001** — The current user is identified by the **Windows account** (`Environment.UserName`),
  lower-cased, with **no interactive login**. *Source:* `MainMenu.cs` ~3016.
- **BR-AUTH-002** — User privileges are loaded from a **single `PDMUserPrivileges` row** matched by
  `UserName`. *Source:* `AuthenticateUser.setUserPrivileges`.
- **BR-AUTH-003** — If no matching row exists, **no flags are set** (the reader loop does not execute) and
  all permissions retain their **default field values** (see BR-AUTH-006). *Source:* `AuthenticateUser.cs`.
- **BR-AUTH-004** — All boolean permission flags are parsed with `bool.Parse` from the row; a non-boolean
  value would throw and be swallowed by the surrounding `try/catch` (which shows a `MsgBox`). *Source:* `AuthenticateUser.setUserPrivileges`.
- **BR-AUTH-005** — `BOMManager` is interpreted specially: empty string → `false`; the integer `1` → `true`;
  any other value → `false`. Unlike the other flags it is **not** parsed as a .NET boolean. *Source:* `AuthenticateUser.setUserPrivileges`.
- **BR-AUTH-006** — Default identity/permission values when unset: `UserId = -1`, `DefaultDealerNum = 1`,
  `DefaultSiteId = 1`, `DefaultLanguageId = 1`, `DefaultCurrencyId = 1`, `DefaultCatalogueId = 1`, and all
  permission booleans `false`. *Source:* `AuthenticateUser.cs` field initialisers.
- **BR-AUTH-007** — Authentication errors are **non-fatal**: exceptions are caught and shown via `MsgBox`,
  after which the app continues with whatever flags were set. *Source:* `AuthenticateUser.setUserPrivileges`.
- **BR-AUTH-008** — The privilege query runs on the connection returned by
  `ConnectionFactory.CreateNewConnection(true)`, i.e. against `Global.connectedServer/connectedDB`.
  *Source:* `AuthenticateUser.setUserPrivileges`.

---

## 7. Hidden Logic

- **No password authentication at all.** Trust is entirely delegated to Windows / SQL Server integrated
  security. A user with a `PDMUserPrivileges` row and DB access is authenticated.
- **`SkypeName` → `Preferences` field reuse.** The DB column `SkypeName` is loaded into a field named
  `Preferences`. The column name and the field name disagree; downstream meaning is **`UNKNOWN`** without
  further extraction.
- **SQL injection exposure.** `UserName` is concatenated directly into the SQL text. In practice the value
  comes from `Environment.UserName`, but this is still an unsafe pattern to carry forward.
- **Special admin override (in `MainMenu`, not in `AuthenticateUser`):** the Windows user `RMAFYT` is granted
  visibility of the Admin button regardless of the `PDMAdministrator` flag
  (`AdminButton.Visible = PDMAdministrator | (UserName.ToUpper() == "RMAFYT")`). *Source:* `MainMenu.cs` ~3004.
  (Cross-referenced in [02_User_Permissions](02_User_Permissions.md).)
- **`UserId = -1` sentinel** indicates "unidentified user".

---

## 8. UI Behaviour

- Authentication is **silent** — the user sees no login prompt; the main menu simply appears with the
  feature set their account allows.
- If the privilege query throws, the user sees a raw exception `MsgBox`, then the menu loads with default
  (mostly disabled) permissions.
- No "log out" / "switch user" concept exists; identity is fixed to the Windows session.

---

## 9. Dependencies

| Kind | Item |
|------|------|
| Class | `AuthenticateUser` (`[StandardModule]`) |
| Connectivity | `ConnectionFactory.CreateNewConnection` |
| Global state | `Global.connectedServer`, `Global.connectedDB` |
| Runtime | `Environment.UserName`, `Microsoft.VisualBasic` (`Interaction.MsgBox`) |
| DB | `PDMUserPrivileges` |
| Consumer | `MainMenu` (reads the populated flags) |

---

## 10. Risks

- **CRITICAL — SQL injection** via string-concatenated `UserName`. Must be parameterised in the rebuild.
- **High — Identity == Windows account** with no application-level auth. Porting to a web/multi-user
  Workbench requires a real authentication model; the 1:1 assumption breaks.
- **High — Silent fallback to defaults** on missing row / error means a misconfigured user may silently get
  a degraded (or, via defaults, unexpectedly permissive `DefaultCatalogueId = 1`) session.
- **Medium — Hardcoded special user `RMAFYT`** couples admin access to a specific person's account.
- **Medium — Inconsistent flag parsing** (`BOMManager` vs all others) is an easy source of migration bugs.
- **Low — `SkypeName`/`Preferences` naming mismatch** obscures the field's true purpose.
