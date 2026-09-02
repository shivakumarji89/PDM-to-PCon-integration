## BR-ARCH — System Architecture → [doc](../../00_System_Architecture.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-ARCH-001 | Connects to a SQL Server whose server/database default to the `DBCHIP12v` / `PDMLive` pair. | `CreateNewConnection`, `Global` | — | — | [00_System_Architecture](../../00_System_Architecture.md) |
| BR-ARCH-002 | The connection string is chosen at runtime by substring-matching the server name. | `CreateNewConnection` | — | — | [00_System_Architecture](../../00_System_Architecture.md) |
| BR-ARCH-003 | Connections retry up to 5 times with linear backoff `2000 ms × attempt`. | `CreateNewConnection` | — | — | [00_System_Architecture](../../00_System_Architecture.md) |
| BR-ARCH-004 | Using a read-only credential sets `Global.readOnlyDBConnection = true`, forcing app-wide read-only. | `CreateNewConnection` | — | — | [00_System_Architecture](../../00_System_Architecture.md) |
| BR-ARCH-005 | On server `DBIA02SQLLV.knoll.dom` the app always connects with the read-only/dev credential. | `CreateNewConnection` | — | — | [00_System_Architecture](../../00_System_Architecture.md) |
| BR-ARCH-006 | If `Global.connectedDB == "DPSDB"` the database name is forced to `"DPSDB"`. | `CreateNewConnection` | — | — | [00_System_Architecture](../../00_System_Architecture.md) |
| BR-ARCH-007 | The Syteline export uses a separate connection factory. | `CreateNewConnectionSyteLine` | — | — | [00_System_Architecture](../../00_System_Architecture.md) |
| BR-ARCH-008 | Passwords are masked (`********`) via `HidePassword()` before appearing in any error text. | `HidePassword` | — | — | [00_System_Architecture](../../00_System_Architecture.md) |
| BR-ARCH-009 | All primary session context lives in mutable global static state. | `Global` (static fields) | — | — | [00_System_Architecture](../../00_System_Architecture.md) |

## BR-AUTH — Authentication → [doc](../../01_Authentication.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-AUTH-001 | The user is identified solely by the Windows account (`Environment.UserName`); there is no login prompt. | `setUserPrivileges`, `Environment.UserName` | Q-AUTH-001 | PDMUserPrivileges | [01_Authentication](../../01_Authentication.md) |
| BR-AUTH-002 | Privileges load from a single `PDMUserPrivileges` row matched on the Windows user. | `setUserPrivileges` | Q-AUTH-001 | PDMUserPrivileges | [01_Authentication](../../01_Authentication.md) |
| BR-AUTH-003 | If no matching row exists, no flags are set and defaults apply. | `setUserPrivileges` | Q-AUTH-001 | PDMUserPrivileges | [01_Authentication](../../01_Authentication.md) |
| BR-AUTH-004 | Boolean flags are parsed with `bool.Parse`; a non-boolean value throws and is swallowed. | `setUserPrivileges` | Q-AUTH-001 | PDMUserPrivileges | [01_Authentication](../../01_Authentication.md) |
| BR-AUTH-005 | `BOMManager` is parsed specially: empty → `false`; integer `1` → `true`. | `setUserPrivileges` | Q-AUTH-001 | PDMUserPrivileges | [01_Authentication](../../01_Authentication.md) |
| BR-AUTH-006 | Default identity values when unset: `UserId = -1`, `DefaultDealerNum = 1`, etc. | `setUserPrivileges` (field initialisers) | — | PDMUserPrivileges | [01_Authentication](../../01_Authentication.md) |
| BR-AUTH-007 | Authentication errors are non-fatal: caught, shown via `MsgBox`, execution continues. | `setUserPrivileges` | — | — | [01_Authentication](../../01_Authentication.md) |
| BR-AUTH-008 | The privilege query runs on the connection from `CreateNewConnection(true)`. | `setUserPrivileges`, `CreateNewConnection` | Q-AUTH-001 | PDMUserPrivileges | [01_Authentication](../../01_Authentication.md) |

## BR-PERM — User Permissions → [doc](../../02_User_Permissions.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-PERM-001 | The permission model is 30 capability flags on `PDMUserPrivileges`. | `setUserPrivileges`, `UserAdmin` | Q-PERM-001 | PDMUserPrivileges | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-002 | Publish DB requires `DatabasePublication` AND the connected DB matches the publish target. | `MainMenu` init | — | PDMUserPrivileges | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-003 | Product Maintenance requires `ProductMaintenance` OR `BOMManager`. | `MainMenu` init | — | PDMUserPrivileges | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-004 | PDM Import requires `PDMImport` AND a non-`eoscloud` server. | `MainMenu` init | — | PDMUserPrivileges | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-005 | Handbook requires `HandbookPublication` AND a non-`eoscloud` server. | `MainMenu` init | — | PDMUserPrivileges | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-006 | Audit requires `PDMAuditer` AND DB not `(local)` AND DB not `POSH`. | `MainMenu` init | — | PDMUserPrivileges | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-007 | Web Configurator requires `CoreMaintenance` AND a non-`eoscloud` server. | `MainMenu` init | — | PDMUserPrivileges | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-008 | Static Maintenance shows if any financial flag is set. | `MainMenu` init | — | PDMUserPrivileges | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-009 | Catalogue access is `PDMUserCatalogues.ReadOnly` where `1` = full access (inverted convention). | `UserAdmin` | Q-PERM-004 | PDMUserCatalogues | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-010 | Revoking catalogue access deletes the `PDMUserCatalogues` row (no flag clear). | `UserAdmin` | Q-PERM-004 | PDMUserCatalogues | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-011 | Each capability flag is toggled by its own dedicated `UPDATE` statement. | `UserAdmin` | Q-PERM-003 | PDMUserPrivileges | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-012 | Display name uses `FullName`, falling back to `UserName` when `FullName IS NULL`. | `UserAdmin` | Q-PERM-002 | PDMUserPrivileges | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-013 | The Admin button is visible if `PDMAdministrator` OR the Windows user is `RMAFYT`. | `MainMenu` init | — | PDMUserPrivileges | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-014 | Windows user `dbacw8` is unconditionally granted Admin-button visibility (second gate). | `MainMenu` init | — | — | [02_User_Permissions](../../02_User_Permissions.md) |
| BR-PERM-015 | Delete Items menu item is visible only when `PDMAdministrator` is true. | `MainMenu` init | — | PDMUserPrivileges | [02_User_Permissions](../../02_User_Permissions.md) |

## BR-CAT — Catalogues → [doc](../../03_Catalogues.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-CAT-001 | "Catalogue Maintenance" button is visible only when `AuthenticateUser.CatalogueMaintenance`. | `CatMaintButton_Click`, MainMenu gating | — | PDMUserPrivileges | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-002 | The button launches the external `DPS.exe`, not an in-app form (dead shell). | `CatMaintButton_Click` | — | — | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-003 | The `isReadOnly` arg to `DPS.exe` is `true` unless the user has `CoreMaintenance`. | `CatMaintButton_Click` | — | PDMUserPrivileges | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-004 | The DPS single-instance guard is `if (0 == 0)` — an always-true dead check. | `CatMaintButton_Click` | — | — | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-005 | The catalogue dropdown lists only catalogues granted via `PDMUserCatalogues`. | `initialiseCatalogues` | Q-CAT-001 | PDMUserCatalogues, Catalogue | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-006 | Default list shows only active catalogues (`Catalogue.Status = 1`). | `initialiseCatalogues` | Q-CAT-001 | Catalogue | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-007 | `ShowOBSCatalogueCheck` replaces the list with obsolete-only (`Status = 2`), not additive. | `initialiseCatalogues` | Q-CAT-001 | Catalogue | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-008 | Catalogues are ordered alphabetically by `Catalogue.Name`. | `initialiseCatalogues` | Q-CAT-001 | Catalogue | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-009 | Auto-selects `DefaultCatalogueId` if present, else index 0. | `initialiseCatalogues` | Q-CAT-001 | Catalogue, PDMUserPrivileges | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-010 | Per-user `ReadOnly` is captured into `_readOnlyCatalogues` to gate writes. | `initialiseCatalogues` | Q-CAT-001 | PDMUserCatalogues | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-011 | The CAD-maintenance catalogue list is always active-only and also reads `CatalogueType`. | CADMaintenance catalogue load | Q-CAT-006 | Catalogue, PDMUserCatalogues | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-012 | The EOS-label checkbox reflects the `{NoLabel}` token in `Catalogue.CatalogueFlags`. | `EOSCatalogueLabelCheck_Changed` | Q-CAT-004, Q-CAT-007 | Catalogue | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-013 | Toggling the EOS label rewrites the whole `CatalogueFlags` string, preserving other tokens. | `EOSCatalogueLabelCheck_Changed` | Q-CAT-005 | Catalogue | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-014 | "Sort catalogues alphabetically" (`AlphaButton`) is a dead stub (confirms, does nothing). | `AlphaButton_Click` | Q-CAT-009 (none) | — | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-015 | Catalogue re-ordering delegates to shared `OrderCategories` with `catalogueId = -1`. | `SortButton_Click` | Q-CAT-002, Q-CAT-003 | Catalogue | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-016 | EOS-label read/write only runs when a catalogue is selected and the form is not loading. | `EOSCatalogueLabelCheck_Changed` | Q-CAT-004, Q-CAT-005 | Catalogue | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-017 | On SQL error in `initialiseCatalogues`, the raw exception and full SQL are shown to the user. | `initialiseCatalogues` | Q-CAT-001 | — | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-018 | Localized catalogue names come from `OtherDescription`, falling back to `Catalogue.Name`. | `OrderCategories_Load` | Q-CAT-002 | Catalogue, OtherDescription | [03_Catalogues](../../03_Catalogues.md) |
| BR-CAT-019 | The dead `CatalogueMaintenance` form documents the intended status vocabulary but implements nothing. | `CatalogueMaintenance` (form) | — | — | [03_Catalogues](../../03_Catalogues.md) |

## BR-CATEG — Product Categories → [doc](../../04_Product_Categories.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-CATEG-001 | Categories are the `CatalogueProductCategories` rows for a `CatalogueId`, joined to `ProductCategory`. | CADMaintenance category load | Q-CATEG-001 | CatalogueProductCategories, ProductCategory | [04_Product_Categories](../../04_Product_Categories.md) |
| BR-CATEG-002 | Displayed via localized `OtherDescription` (lang 1), falling back to `ProductCategory.Name`/`cpc.Name`. | CADMaintenance category load | Q-CATEG-001, Q-CATEG-002 | OtherDescription, ProductCategory | [04_Product_Categories](../../04_Product_Categories.md) |
| BR-CATEG-003 | Sort by `cpc.DisplayOrder` with `-1 → 9999` so unordered categories sort last. | CADMaintenance category load | Q-CATEG-001, Q-CATEG-005 | CatalogueProductCategories | [04_Product_Categories](../../04_Product_Categories.md) |
| BR-CATEG-004 | Duplicate descriptions are disambiguated by appending `" (<ProductCategoryId>)"`. | CADMaintenance category load | — | CatalogueProductCategories | [04_Product_Categories](../../04_Product_Categories.md) |
| BR-CATEG-005 | A synthetic "< SP Components >" entry (id `999`) is always appended. | CADMaintenance category load | — | — (synthetic) | [04_Product_Categories](../../04_Product_Categories.md) |
| BR-CATEG-006 | After loading, the first category is auto-selected if any exist. | CADMaintenance category load | — | — | [04_Product_Categories](../../04_Product_Categories.md) |
| BR-CATEG-007 | Category loads use `SELECT DISTINCT` to collapse duplicate CPC rows. | CADMaintenance category load | Q-CATEG-001, Q-CATEG-005 | CatalogueProductCategories | [04_Product_Categories](../../04_Product_Categories.md) |
| BR-CATEG-008 | Category images are per-catalogue: keyed by `(ProductCategoryId, CatalogueId)`. | CADMaintenance image lookup | Q-CATEG-004 | CatalogueProductCategories | [04_Product_Categories](../../04_Product_Categories.md) |
| BR-CATEG-009 | Category loading always filters by the selected `CatalogueId`; no "all catalogues" view. | CADMaintenance category load | Q-CATEG-001 | CatalogueProductCategories | [04_Product_Categories](../../04_Product_Categories.md) |
| BR-CATEG-010 | Per-catalogue category re-ordering (`catalogueId > 0` path) is dead code — only caller passes `-1`. | `OrderCategories_Load`, `SubmitButton_Click` | Q-CATEG-002, Q-CATEG-003 | CatalogueProductCategories | [04_Product_Categories](../../04_Product_Categories.md) |
| BR-CATEG-011 | The dead category-ordering query has a missing-space SQL concat defect (`CatalogueId``ORDER BY`). | `OrderCategories_Load` | Q-CATEG-002 | CatalogueProductCategories | [04_Product_Categories](../../04_Product_Categories.md) |
| BR-CATEG-012 | CAD loads hardcode `LanguageId = 1`; `OrderCategories` uses the caller-supplied language. | CADMaintenance category load, `OrderCategories_Load` | Q-CATEG-001, Q-CATEG-002 | OtherDescription | [04_Product_Categories](../../04_Product_Categories.md) |
| BR-CATEG-013 | `metaTypes` is not part of the category model — it is an OFML metatype (`go_types`) record. | `metaTypes` (`getAllProperties`) | — | — | [04_Product_Categories](../../04_Product_Categories.md) |

## BR-ORD — Ordering → [doc](../../16_Ordering.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-ORD-001 | `OrderCategories` defaults to `catalogueId = -1`, `languageId = 1` on construction. | `OrderCategories` ctor | — | — | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-002 | `catalogueId == -1` orders catalogues ("Order Catalogues"); else product categories. | `OrderCategories_Load` | Q-ORD-002, Q-ORD-001 | Catalogue, CatalogueProductCategories | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-003 | The catalogue path lists all catalogues with no per-user permission filter. | `OrderCategories_Load` | Q-ORD-002 | Catalogue | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-004 | Rows are initially listed in current `DisplayOrder` order. | `OrderCategories_Load` | Q-ORD-002 | Catalogue | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-005 | Each row shows a localized description, falling back to `Name`. | `OrderCategories_Load` | Q-ORD-002 | OtherDescription, Catalogue | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-006 | The description textbox is read-only; only the ordinal textbox is editable. | `OrderCategories_Load` | — | — | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-007 | Each ordinal textbox stores its entity id in `Tag`. | `OrderCategories_Load` | — | — | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-008 | On Submit, only textboxes whose `Tag` parses to `> 0` are written. | `SubmitButton_Click` | — | — | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-009 | The ordinal written is the raw text with no validation, range check, or de-duplication. | `SubmitButton_Click` | Q-ORD-003 | Catalogue | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-010 | Submit disables its button first and writes one UPDATE per edited row (no transaction). | `SubmitButton_Click` | Q-ORD-003 | Catalogue | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-011 | The category-ordering path is dead: the only caller always sets `catalogueId = -1`. | `SortButton_Click` | Q-ORD-001, Q-ORD-004 | CatalogueProductCategories | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-012 | The "sort alphabetically" (`AlphaButton`) action is a dead stub (confirms, does nothing). | `AlphaButton_Click` | — | — | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-013 | The dead category query has a missing-space SQL defect before `ORDER BY`. | `OrderCategories_Load` | Q-ORD-001 | CatalogueProductCategories | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-014 | Sort launches only when a catalogue is selected (though the query orders all catalogues). | `SortButton_Click` | — | — | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-015 | The form widens itself and its panel by +20px on every load. | `OrderCategories_Load` | — | — | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-016 | Rows are laid out at a fixed 20px vertical pitch (240px description, 60px ordinal). | `OrderCategories_Load` | — | — | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-017 | Focusing/clicking an ordinal textbox selects all its text for quick overtyping. | `dispbox_Enter`, `dispbox_MouseUp` | — | — | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-018 | On any load/submit exception the raw exception is shown and swallowed (no rollback). | `OrderCategories_Load`, `SubmitButton_Click` | — | — | [16_Ordering](../../16_Ordering.md) |
| BR-ORD-019 | Connections always close in a `finally`; `checked` arithmetic is used for row counters. | `SubmitButton_Click`, `OrderCategories_Load` | — | — | [16_Ordering](../../16_Ordering.md) |
