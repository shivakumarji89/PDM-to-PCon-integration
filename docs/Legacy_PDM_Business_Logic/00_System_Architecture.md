# 00 — System Architecture

**Module prefix:** `BR-ARCH`
**Primary legacy source:** `Global.cs`, `ConnectionFactory.cs`, `MainMenu.cs`, `PDMService.cs`, `AuthenticateUser.cs`
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

Defines how the Legacy PDM application starts, connects to its SQL Server database, holds global
session state, and routes the authenticated user into feature areas via the main menu. There is no
formal layered architecture: the application is a **WinForms desktop client that talks directly to
SQL Server** using inline ADO.NET.

---

## 2. Entry Points

| Entry point | Source | Notes |
|-------------|--------|-------|
| Application main form | `MainMenu.cs` | Hosts the top menu and launches all maintenance forms |
| Global session state | `Global.cs` (`[StandardModule]`) | Static, process-wide mutable state |
| DB connection factory | `ConnectionFactory.cs` | Static methods returning `SqlConnection` |
| Privilege bootstrap | `AuthenticateUser.setUserPrivileges()` | Called during menu init (`MainMenu.cs` ~line 3016) |

> `Global` and `AuthenticateUser` are VB.NET `StandardModule`s — i.e. **static singletons**. All
> state is global and mutable, with no encapsulation.

---

## 3. Call Hierarchy

```
Process start
   ↓
MainMenu (form load / init)
   ↓
AuthenticateUser.setUserPrivileges(Environment.UserName.ToLower())   [MainMenu.cs ~3016]
   ↓  (SQL: SELECT ... FROM PDMUserPrivileges WHERE UserName = '<user>')
Permission flags populated on AuthenticateUser (static)
   ↓
MainMenu enables/shows menu items per flag   [MainMenu.cs ~3004–3087]
   ↓
User selects a feature → new <Feature>Maintenance() form → ShowDialog()
   ↓
Feature form calls ConnectionFactory.CreateNewConnection(true)
   ↓
Inline SqlCommand executes against Global.connectedServer / Global.connectedDB
   ↓
Data bound to grid; edits saved via INSERT/UPDATE/DELETE
```

---

## 4. SQL Analysis

The architecture layer itself issues one query directly (privilege load — documented in
[01_Authentication](01_Authentication.md)). Its main responsibility is **connection construction**.

### Connection construction (`ConnectionFactory.CreateNewConnection`)

Verified behaviour (`ConnectionFactory.cs`):

- Reads target from `Global.connectedServer` and `Global.connectedDB`.
- Builds a connection string chosen by **server-name string matching**:
  - Server contains `eoscloud` →
    - non `-uat-` / non `-dev-` → `User ID=Administrator;Password=********` (live cloud password)
    - `-uat-` or `-dev-` → `User ID=Administrator;Password=********` (lower-env password)
  - Server contains `DBIA01SQLSV.knoll.dom` **or** `DBIA08SQPDMLV.knoll.dom` →
    - For a **hardcoded list of Windows usernames**, a **specific SQL login** is substituted
      (per-user credential mapping — see Hidden Logic).
    - Otherwise: `Integrated Security=SSPI` (Windows auth), unless read-only/retry → `ReadOnlyDev` login.
  - Server contains `DBIA02SQLLV.knoll.dom` → always `ReadOnlyDev` login.
  - Otherwise → `Integrated Security=SSPI`, unless read-only/retry → `ReadOnlyDev` login.
    - Special case: if `Global.connectedDB == "DPSDB"`, database is forced to `"DPSDB"`.
- Retries up to `maxRetries` (default **5**) with backoff `Thread.Sleep(2000 * i)` between attempts.
- On total failure, prompts the user "Try again?" (`MsgBox`) and loops if Yes.
- If the resulting connection string contains `readonly`, sets `Global.readOnlyDBConnection = true`.

### Syteline connection (`ConnectionFactory.CreateNewConnectionSyteLine`)

- Chooses live vs test via `Global.SytelineLive*` / `Global.SytelineTest*`.
- Server `DBHONP*` → `ReadOnlyDev` login.
- Same **per-user SQL login substitution** for the hardcoded username list (adds `kbd3op → k.bohan-pitt`).
- Otherwise `Integrated Security=SSPI`.

### Helpers

- `PingHost(nameOrAddress)` — ICMP ping test; returns bool. Used to test host reachability.
- `HidePassword(connectionString)` — masks the `Password=` value with `********` before display in error dialogs.

---

## 5. Data Model (architecture-relevant)

| Table | Used by | Notes |
|-------|---------|-------|
| `PDMUserPrivileges` | `AuthenticateUser.setUserPrivileges` | One row per user; permission flags. See [02_User_Permissions](02_User_Permissions.md). |

Global session identifiers (`Global.cs`) that act as implicit foreign keys across the app:

| Global field | Default | Meaning |
|--------------|---------|---------|
| `globalSiteId` | `1` | Active site |
| `globalCatalogueId` | `-1` | Active catalogue (`-1` = none/invalid) |
| `globalCatalogueName` | `""` | Active catalogue name |
| `globalSchemeId` | `-1` | Active code scheme |
| `globalCategoryId` | `-1` | Active product category |
| `globalProductId` | `-1` | Active product |
| `globalCurrencyId` | `-1` | Active currency |
| `globalCurrencySymbol` | `""` | Currency symbol |
| `globalLanguageId` | `1` | Active language (default 1) |
| `globalEffectiveDate` | `""` | Effective date for price/data queries |
| `InvalidId` (const) | `-1` | Canonical "invalid/none" id sentinel |

---

## 6. Business Rules

- **BR-ARCH-001** — The application connects to a SQL Server database whose server/database default to
  `Global.primaryPDMServer = "DBCHIP12v"` and `Global.primaryPDMDatabase = "PDMLive"`.
  *Source:* `Global.cs`.
- **BR-ARCH-002** — The connection string is selected at runtime by **substring-matching the server name**
  (`eoscloud`, `DBIA01SQLSV.knoll.dom`, `DBIA08SQPDMLV.knoll.dom`, `DBIA02SQLLV.knoll.dom`).
  *Source:* `ConnectionFactory.CreateNewConnection`.
- **BR-ARCH-003** — Database connections retry up to **5** times with a linear backoff of `2000 ms × attempt`
  before prompting the user to retry. *Source:* `ConnectionFactory.CreateNewConnection`.
- **BR-ARCH-004** — When a read-only credential is used, `Global.readOnlyDBConnection` is set `true`
  (detected by the substring `readonly` in the connection string). *Source:* `ConnectionFactory.CreateNewConnection`.
- **BR-ARCH-005** — On the `DBIA02SQLLV.knoll.dom` server the application **always** connects with the
  read-only `ReadOnlyDev` login. *Source:* `ConnectionFactory.CreateNewConnection`.
- **BR-ARCH-006** — If `Global.connectedDB == "DPSDB"`, the database name is forced to `"DPSDB"` in the
  default connection branch. *Source:* `ConnectionFactory.CreateNewConnection`.
- **BR-ARCH-007** — The Syteline export uses a **separate** connection factory
  (`CreateNewConnectionSyteLine`) with live/test selection driven by `Global.Syteline*` fields.
  *Source:* `ConnectionFactory.cs`.
- **BR-ARCH-008** — Passwords are masked (`********`) via `HidePassword()` before being shown in any error
  dialog. *Source:* `ConnectionFactory.cs`.
- **BR-ARCH-009** — All primary session context (site, catalogue, category, product, currency, language,
  effective date) is stored as **global mutable static state** on `Global`, initialised with `-1`/`1`/`""`
  sentinels. *Source:* `Global.cs`.

---

## 7. Hidden Logic

- **Hardcoded server names:** `PDMServer = "wechip01v"`, `primaryPDMServer = "DBCHIP12v"`,
  `primaryPDMDatabase = "PDMLive"`. *Source:* `Global.cs`.
- **Hardcoded file paths** (`Global.filePaths`): local `C:\Projects\DPS\bin\`, UNC `\\wechip01v\HMEURONET\PDM\`,
  Program Files EOS path, and an `http://www.hmeuronet.com/PDM/` URL. `defaultFilePathIndex = 1` (the UNC path).
- **Hardcoded database credentials** appear in plaintext in `ConnectionFactory.cs` (cloud `Administrator`
  passwords, `ReadOnlyDev/D3v3l0p3r`, per-user `Changem3`). **Security risk — must not be reproduced.**
- **Per-user SQL login substitution:** a hardcoded map of Windows usernames → SQL logins exists for the
  `DBIA01SQLSV` / `DBIA08SQPDMLV` servers:
  `dbacw8→d.bevan`, `dcacqu→d.chen`, `tybjbf→c.yin`, `ggafnn→b.ganiger`, `lzbdnk→l.zhu`, `edami2→e.dwyer`
  (Syteline path additionally maps `kbd3op→k.bohan-pitt`). *Source:* `ConnectionFactory.cs`.
- **Magic sentinel** `-1` (`Global.InvalidId`) denotes "none/invalid" for all id fields.
- **`testMode`** and **`ofdaManagerOrWebConfigActive`** are global boolean flags whose full effect is
  spread across the app — **`UNKNOWN`** in this doc beyond their declaration in `Global.cs`.

---

## 8. UI Behaviour

- The main menu (`MainMenu.cs`) is the shell. After privilege load it **enables/shows** top-level menu
  entries strictly by permission flag (see [02_User_Permissions](02_User_Permissions.md)).
- Feature areas open as **modal dialogs** (`new <Feature>Maintenance().ShowDialog()`).
- DB connection failures surface as **blocking `MsgBox`** dialogs with an optional retry loop.
- There is no global async/loading model at the architecture layer; long operations use dedicated
  `*Thread.cs` worker classes (e.g. `ExportThread`, `ValidateThread`).

---

## 9. Dependencies

| Kind | Item |
|------|------|
| Global state | `Global` (`[StandardModule]`) |
| Auth | `AuthenticateUser` |
| Connectivity | `ConnectionFactory`, `System.Data.SqlClient`, `System.Net.NetworkInformation.Ping` |
| Shell | `MainMenu` |
| DB | SQL Server (`PDMLive` on `DBCHIP12v` by default), `PDMUserPrivileges` table |
| VB runtime | `Microsoft.VisualBasic`, `Microsoft.VisualBasic.CompilerServices` |

---

## 10. Risks

- **CRITICAL — Plaintext credentials in source.** Multiple SQL passwords and an admin cloud password are
  hardcoded. Any MK Product Workbench implementation must use a secrets manager / integrated auth and must
  **never** port these literals.
- **High — Global mutable static state.** `Global`/`AuthenticateUser` singletons make behaviour
  order-dependent and hard to test; concurrency (worker threads) can race on shared globals.
- **High — Server selection by substring matching** is brittle; renaming/moving servers silently changes
  auth mode. Should be replaced by explicit configuration.
- **Medium — Direct inline SQL everywhere** (no repository layer) implies SQL logic is duplicated across
  forms; extraction must be exhaustive to avoid missing edge-case queries.
- **Medium — Blocking `MsgBox` retry loops** couple data access to the UI thread.
- **Low/Unknown — `testMode` / `ofdaManagerOrWebConfigActive`** semantics require further extraction.
