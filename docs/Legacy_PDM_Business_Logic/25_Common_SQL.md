# 25 — Common SQL Patterns

**Status:** Synthesis of verified module extractions; unproven items marked `UNKNOWN`.

**Module prefix:** `BR-SQL` (cross-cutting; no new source read — this file only aggregates the
already-extracted module docs [00](00_System_Architecture.md)–[24](24_Utilities.md)).

---

## 1. Purpose

Legacy PDM has **no data-access layer**. Every form builds SQL inline, as string concatenation, and
executes it through an ad-hoc `SqlCommand` (SQL Server) or `OleDbCommand` (Jet/Access MDB) obtained from
`ConnectionFactory.CreateNewConnection(...)`. Because the same idioms are copy-pasted across ~140 source
files, the *same* correctness and security defects recur everywhere.

This document catalogues the **cross-cutting SQL patterns** that appear in more than one module, so that a
rebuild (MK Product Workbench) can address each once — as a class of problem — rather than rediscovering it
per screen. Each pattern below has: a short description, a verbatim example quoted from a module doc, and
backlinks to every module doc where the pattern was observed. A consolidated **Stored Procedures &
Functions Index** and a **risk summary** follow.

> Anything not provable from the module extractions is marked `UNKNOWN`. In particular, the bodies of all
> stored procedures and scalar functions are `UNKNOWN` because they live in the SQL Server database, not in
> the C# source tree that was extracted.

---

## 2. Cross-cutting SQL patterns

### P-SQL-01 — Inline string-concatenation (SQL injection)

**Description.** The dominant pattern. SQL is assembled with `+` / `Operators.ConcatenateObject` (or, in
the search dialog, `String.Replace("{text}", userInput)`), interpolating identifiers, ids, filter text and
even whole CSV cell contents directly into the command text. There is **no parameterisation** on these
paths (the only systematically parameterised paths are the `SqlDataAdapter`-backed grids in
[07_Attributes](07_Attributes.md) and [24_Utilities](24_Utilities.md); see P-SQL-04). Even the very first
query the app runs — the privilege load — is concatenated:

```sql
-- 01_Authentication Q-AUTH-001
... WHERE p1.UserName = '" + username + "'"
```

The search module is the most exposed, because the injected value is genuine end-user text from a search
box, and comment markers are deliberately preserved:

> **BR-SRCH-002** — The search value replaces `{text}` via `String.Replace` (DataQuery.cs:1414) with **no
> parameterization or escaping**. Both `LIKE '%{text}%'` and unquoted `= {text}` (numeric-id searches) are
> injectable. — [14_Search](14_Search.md)

**Occurs in:** effectively every module —
[01_Authentication](01_Authentication.md), [02_User_Permissions](02_User_Permissions.md),
[03_Catalogues](03_Catalogues.md), [04_Product_Categories](04_Product_Categories.md),
[05_Products](05_Products.md), [06_Articles](06_Articles.md), [07_Attributes](07_Attributes.md),
[08_Property_Values](08_Property_Values.md), [09_Options](09_Options.md),
[10_Option_Values](10_Option_Values.md), [11_Configuration](11_Configuration.md),
[12_Translations](12_Translations.md), [13_Descriptions](13_Descriptions.md), [14_Search](14_Search.md),
[15_Filtering](15_Filtering.md), [16_Ordering](16_Ordering.md), [18_Pricing](18_Pricing.md),
[22_Export](22_Export.md), [23_Generation](23_Generation.md), [24_Utilities](24_Utilities.md).

---

### P-SQL-02 — Correlated subquery + `CROSS JOIN (SELECT NULL AS X)`

**Description.** A recurring, unusual idiom in which the outer column list is kept resolvable by
cross-joining a one-row constant table `(SELECT NULL AS <Name>) x`, and the real value is supplied by a
**correlated subquery** with the same name. It is used two ways:

1. **Privilege loading** — to always project a `BOMManager` column even though it is read/interpreted
   specially:

   ```sql
   -- 01_Authentication Q-AUTH-001 / 02_User_Permissions Q-PERM-001
   ...,
   ( SELECT BOMManager FROM PDMUserPrivileges p2 WHERE p2.UserId = p1.UserId ) AS BOMManager
   FROM PDMUserPrivileges p1
   CROSS JOIN ( SELECT NULL AS BOMManager ) x
   WHERE p1.UserName = '<username>'
   ```

2. **A stubbed `ProductCodeIdOverride` extension point** — a hardcoded `NULL` constant cross-joined in,
   with a correlated `CASE` that would read `Item.ProductCodeIdOverride`. As written the constant is
   `NULL`, so the override branch is **inert**:

   ```sql
   -- 05_Products Q-PROD-013
   FROM Item
   CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x
   ...
   INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2
        WHERE i2.ItemId = Item.ItemId ) IS NOT NULL
        THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId )
        ELSE Product.ProductCodeId END = pc.ProductCodeId
   ```

**Occurs in:** [01_Authentication](01_Authentication.md) (`BOMManager`),
[02_User_Permissions](02_User_Permissions.md) (`BOMManager`),
[05_Products](05_Products.md) (`ProductCodeIdOverride`, Q-PROD-013/024/025),
[14_Search](14_Search.md) (`ProductCodeIdOverride`, Q-SRCH product-code query).

> Note: the `Item.ProductCodeIdOverride` column referenced by the correlated `CASE` is a real column
> ([14_Search](14_Search.md) Q-SRCH-032 writes `UPDATE Item SET ProductCodeIdOverride = …`), but the
> cross-joined constant shadows it with `NULL`, so most read queries never use the override. This is a
> genuine latent bug / dead extension point — `UNKNOWN` whether it was ever intended to be live.

---

### P-SQL-03 — Identity recovery by re-`SELECT` on natural key (no `SCOPE_IDENTITY`)

**Description.** After an `INSERT`, the code recovers the new primary key **not** with `SCOPE_IDENTITY()`
or `OUTPUT`, but by issuing a second `SELECT` — either re-matching on the natural key just inserted, or
taking `SELECT TOP 1 <IdCol> ... ORDER BY <IdCol> DESC`. The latter also serves as a home-grown "next id"
generator: read the current max id, add 1, and insert that value. Both are **non-atomic and racy** under
concurrency.

```sql
-- 10_Option_Values Q-OVAL-010 — home-grown next-id, then insert
SELECT TOP 1 DescriptionId FROM OtherDescription ORDER BY DescriptionId DESC
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES (<descId>, 1, '<name>', 'OptionValue')
```

```sql
-- 14_Search Q-SRCH-031 — audit header insert, then recover its id by TOP 1 DESC
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('<user>', GetUTCDate(), '<Global.connectedDB>')
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '<user>' ORDER BY TransactionId DESC
```

A **natural-key** variant (re-select the row you just inserted, matching on all inserted columns) is used
when creating options during SIF import:

> The re-`SELECT` recovers the identity of the just-inserted row (no `SCOPE_IDENTITY`; matches on all
> inserted columns). — [09_Options](09_Options.md) (Q-OPT-011)

**Occurs in:** [09_Options](09_Options.md) (natural-key re-select),
[10_Option_Values](10_Option_Values.md) (`TOP 1 … DESC` next-id),
[11_Configuration](11_Configuration.md) (`SELECT TOP 1 DescriptionId … DESC` +1, BR-CFG-021),
[12_Translations](12_Translations.md) (Q-TRAN-010 new-`DescriptionId` spawning),
[13_Descriptions](13_Descriptions.md) (Q-DESC-022 `SELECT TOP 1 DescriptionId FROM ProductDescription … DESC`),
[14_Search](14_Search.md) (audit id, Q-SRCH-031), [15_Filtering](15_Filtering.md) (Q-FILT next-id),
[18_Pricing](18_Pricing.md) (audit id, Q-PRICE-041/042/071/072),
[24_Utilities](24_Utilities.md) (audit id, Q-UTIL PFUpdates).

> **Related `@@IDENTITY` variant.** [24_Utilities](24_Utilities.md) is the exception that *does* use
> identity — but via the deprecated, scope-unsafe `@@IDENTITY` to re-select the freshly inserted row for
> grid refresh:
> ```sql
> -- 24_Utilities Q-UTIL-004/005
> SELECT Currency_ID, Currency, PriceCode, DecimalPlaces, Description, Symbol FROM Currency WHERE (Currency_ID = @@IDENTITY)
> INSERT INTO Site(Description, Site, DomCurrCode) … ; SELECT … WHERE SiteId = @@IDENTITY
> ```

---

### P-SQL-04 — Optimistic-concurrency `UPDATE` (`@Original_*` predicates)

**Description.** The **only** genuinely defensive write pattern in the codebase, confined to the
`SqlDataAdapter`-generated commands behind a few grids. The `UPDATE`'s `WHERE` clause re-asserts *every*
original column value (with explicit `NULL`-handling), so the write fails if any field changed since load
(last-writer-wins is prevented). The command then re-`SELECT`s the saved row. These paths are also the
rare **parameterised** ones.

```sql
-- 07_Attributes Q-ATTR-005 (PhysicalMaintenance item physical update)
UPDATE dbo.Item SET WeightKilos = @WeightKilos, VolumeLitres = @VolumeLitres,
  FreightCategory = @FreightCategory, CommodityCode = @CommodityCode, FSCCompliant = @FSCCompliant
WHERE (ItemId = @Original_ItemId)
  AND (CommodityCode = @Original_CommodityCode OR @Original_CommodityCode IS NULL AND CommodityCode IS NULL)
  AND (FreightCategory = @Original_FreightCategory OR @Original_FreightCategory IS NULL AND FreightCategory IS NULL)
  AND (VolumeLitres = @Original_VolumeLitres OR @Original_VolumeLitres IS NULL AND VolumeLitres IS NULL)
  AND (WeightKilos = @Original_WeightKilos OR @Original_WeightKilos IS NULL AND WeightKilos IS NULL)
  AND (FSCCompliant = @Original_FSCCompliant OR @Original_FSCCompliant IS NULL);
SELECT WeightKilos, VolumeLitres, FreightCategory, CommodityCode, FSCCompliant, ItemId FROM dbo.Item WHERE (ItemId = @ItemId)
```

> **BR-UTIL-033** — All entity `Select/Insert/Update` commands are **parameterised** with `@Param` and
> optimistic-concurrency `@Original_*` predicates (unusual for this codebase). Insert commands re-`SELECT …
> WHERE Id = @@IDENTITY` to refresh the grid row. — [24_Utilities](24_Utilities.md)

**Occurs in:** [07_Attributes](07_Attributes.md) (Q-ATTR-005 item physical, Q-ATTR-007 incremental volume),
[24_Utilities](24_Utilities.md) (Site / Language / Currency / ExchangeRate / Product_Code / PriceFormula /
PriceMatrix adapters, `SetSQL`).

> **Contrast:** every *hand-written inline* `UPDATE` elsewhere (options, option values, descriptions,
> catalogue flags, pricing) is **last-writer-wins** with no concurrency guard — see the P-SQL-01 module
> list. E.g. [03_Catalogues](03_Catalogues.md) R-CAT-9 explicitly notes concurrent editors overwrite each
> other's `CatalogueFlags`.

---

### P-SQL-05 — PDMAudit cross-database audit ("second-connection" audit)

**Description.** Sensitive writes (price changes, product-code reassignments, price-formula edits) are
audited into a **separate `PDMAudit` database**, referenced by three-part names (`PDMAudit.dbo.<table>`).
The idiom is always the same triple: insert an audit **header** into `Transactions`, recover its
`TransactionId` via the P-SQL-03 `SELECT TOP 1 … ORDER BY TransactionId DESC`, then insert one or more
**detail** rows capturing before/after values. Auditing is **disabled when the connected server is an
`eoscloud` server**.

```sql
-- 18_Pricing Q-PRICE-041/042 + 042b (only when server is NOT eoscloud)
INSERT INTO Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('<user>', GetUTCDate(), '<connectedDB>')
SELECT TOP 1 TransactionId FROM Transactions WHERE UserName = '<user>' ORDER BY TransactionId DESC
INSERT INTO ItemPriceUpdates
 (TransactionId, ItemId, PrevBasePrice, PrevBasePrice2, PrevBasePrice3, NewBasePrice, NewBasePrice2, NewBasePrice3)
VALUES (<tx>, <itemId>, <prev1|NULL>, <prev2|NULL>, <prev3|NULL>, <new/prev per priceref>)
```

Detail tables observed: `Transactions` (header), `ItemPriceUpdates`, `IncrementalPriceUpdates`,
`PFUpdates` (price-formula before/after), `ProdCodeUpdates` (product-code reassignment before/after).

> **"Second connection":** the audit writes target a *different database* (`PDMAudit`) from the working
> `PDMLive` database. In the extracted paths this is achieved via **three-part names on the working
> connection** (e.g. `PDMAudit.dbo.Transactions`); whether any path opens a genuinely distinct
> `SqlConnection` to `PDMAudit` is `UNKNOWN` from the module extractions. The behavioural contract — a
> separate audit store, gated off in cloud — is what matters for migration.

**Occurs in:** [09_Options](09_Options.md) (Q-OPT-010 `PDMAudit.dbo.Transactions`),
[10_Option_Values](10_Option_Values.md) (audit on status/value edits),
[14_Search](14_Search.md) (Q-SRCH-031/032 `Transactions` + `ProdCodeUpdates`),
[18_Pricing](18_Pricing.md) (Q-PRICE-041/042/071/072/073 `Transactions`, `ItemPriceUpdates`,
`IncrementalPriceUpdates`, `PFUpdates`; disabled on eoscloud),
[24_Utilities](24_Utilities.md) (PriceFormula path `Transactions` + `PFUpdates`).

---

### P-SQL-06 — Stored procedures & functions referenced but not in source

**Description.** Core read/report/pricing logic is delegated to SQL Server **stored procedures** and
**scalar functions** whose bodies are **not** in the C# source tree. The application only supplies the
call site and parameters; the semantics (joins, PLC overrides, rounding, uplift) are `UNKNOWN`. These are
the highest-risk migration gaps because the actual business logic is invisible here.

```sql
-- 09_Options Q-OPT-001 / 08_Property_Values Q-PVAL-001 — the central option/value read
EXEC PDMOptionDataReport @cataloguedesc = '<item>'          -- CommandType.StoredProcedure, CommandTimeout = 300

-- 09_Options Q-OPT-002 — priced variants
EXEC PDMOptionDataReportWithIncList @item, @siteId, @currency, @effectivedate
EXEC PDMOptionDataReportWithIncBase '<item>', <siteId>

-- 18_Pricing Q-PRICE-050/051 — forward list-price functions (bodies UNKNOWN)
SELECT dbo.fnGetListPrice('<currency>', <basePrice>, '<itemPriceCode>', '<effDate>', 'DMY', <rounding>, <siteId>, NULL) AS ListPrice
SELECT dbo.fnGetListPriceByItem('<item>', '<currency>', '<effDate>', <siteId>, NULL) AS ListPrice

-- 23_Generation — the only handbook generation call
EXEC PDMPriceListReportForProductGroup <handbookId>, <groupId>, <siteId>, <catId>, <categoryId>, <currency>, <langId>, @date, @content
```

> All bodies are `UNKNOWN` (SQL-side). `PDMOptionDataReport` is the single most-depended-on object,
> consumed by nearly every export and maintenance path ([05](05_Products.md), [08](08_Property_Values.md),
> [09](09_Options.md), [10](10_Option_Values.md), [18](18_Pricing.md), [21](21_OCD.md), [22](22_Export.md)).

See the **Stored Procedures & Functions Index** (§3) for the full list and where each is referenced.

---

### P-SQL-07 — OLE DB / Jet MDB access (`pcr_data_*.mdb`)

**Description.** The pCon/OFML integration does **not** go through SQL Server. It opens per-workspace
Microsoft **Jet/Access MDB** files via the 32-bit `Microsoft.Jet.OLEDB.4.0` provider, with the filename
templated by a pCon "context" token. Four domains share one code path:

```text
-- 20_ODB O-ODB-001 / 19_OAP O-OAS-002 / 11_Configuration O-CFG-*
Provider=Microsoft.Jet.OLEDB.4.0;Data Source=<pConPath>WS\<workspace>\pcr_data_<context>.mdb
```

| `context` | MDB file | Domain | Doc |
|-----------|----------|--------|-----|
| `com_ocd` | `pcr_data_com_ocd.mdb` | Commercial (`tCOMd_*`) | [21_OCD](21_OCD.md) |
| `geo_odb` | `pcr_data_geo_odb.mdb` | Geometry (`tGEOd_*`) | [20_ODB](20_ODB.md) |
| `sel_oas` | `pcr_data_sel_oas.mdb` | Selection | [19_OAP](19_OAP.md) |
| `typ_cls` | `pcr_data_typ_cls.mdb` | Type/class | [11_Configuration](11_Configuration.md) |

The commercial MDB (`tCOMd_*` tables) is written when pushing prices and generating VARCOND relations;
the geometry MDB (`tGEOd_*`) holds model-reference nodes.

**Occurs in:** [05_Products](05_Products.md) (Q-PROD-043..047 `tCOMd_Relation/RelObj/RelObjRel`),
[11_Configuration](11_Configuration.md) (`CreateNode` → `tGEOd_Node2D/3D`; `ClonePConPropertyClassOCD` →
`tCOMd_Class/Property/PropValue`), [12_Translations](12_Translations.md) (Q-TRAN-014 `tCOMd_Text`),
[18_Pricing](18_Pricing.md) (pCon price push, `tCOMd_*`), [19_OAP](19_OAP.md), [20_ODB](20_ODB.md),
[24_Utilities](24_Utilities.md) (`MDBQuery` browser).

> **Deployment constraint:** `Microsoft.Jet.OLEDB.4.0` is **x86-only and deprecated** — the whole pCon path
> requires a 32-bit host process ([20_ODB](20_ODB.md) R, [19_OAP](19_OAP.md) R).

---

### P-SQL-08 — `xp_cmdshell` / `dtsrun` shell-out from SQL

**Description.** The DPS-DB publication/export utility drives an out-of-process DTS package by calling the
SQL Server extended stored procedure `xp_cmdshell` to run `dtsrun` on a specific server. This runs OS
commands under the SQL Server service account.

> **ProgressThread** — `dtsrun Export_PDM2004_to_DPSDB` via `xp_cmdshell` on `dbchip02`. —
> [24_Utilities](24_Utilities.md) (BR-UTIL, `ProgressThread`)

Related but distinct: the database-publication flow in [22_Export](22_Export.md) (ExportDPSDB /
`PublishDatabase.cs`) runs a **DTS package** to detach `DPSDB`, copy the MDF/LDF to a network share, and
reattach — an OS/file-system-level operation orchestrated from the app.

**Occurs in:** [24_Utilities](24_Utilities.md) (`xp_cmdshell` + `dtsrun`),
[22_Export](22_Export.md) (DTS-based `ExportDPSDBThread`).

> `xp_cmdshell` is disabled by default on modern SQL Server and is a well-known privilege-escalation
> surface — must not be reproduced (see §4).

---

### P-SQL-09 — Missing-space concatenation bugs

**Description.** Because clauses are concatenated without a leading space, some queries produce malformed
SQL when a value abuts the next keyword. Two verified instances:

```sql
-- 04_Product_Categories Q-CATEG-002 / 16_Ordering Q-ORD (DEAD path)
... WHERE cpc.CatalogueId = <catalogueId>ORDER BY cpc.DisplayOrder     -- e.g. "= 5ORDER BY" → invalid
```

```sql
-- 07_Attributes Q-ATTR-013 (PhysicalMaintenance.cs:2349 variant)
... AND we.CatalogueId = '<catalogueId>'WHERE Item.Item = ...          -- "'…'WHERE" — tolerated only by luck
```

The category-ordering instance is **latent** (the containing path is dead code, only ever called with
`catalogueId = -1`), so it never actually executes; the WebEOS instance runs but happens to be tolerated
because SQL Server accepts `'`-then-`WHERE`.

**Occurs in:** [04_Product_Categories](04_Product_Categories.md) (BR-CATEG-011, R-CATEG-3),
[16_Ordering](16_Ordering.md) (BR-ORD-013), [07_Attributes](07_Attributes.md) (HL-ATTR-4).

---

### P-SQL-10 — Quote-escaping inconsistencies (`'` → backtick vs `''`)

**Description.** There is no central escaping helper. Single quotes in user/data text are sanitised
**per-call**, inconsistently: some paths replace `'` with a backtdilde/backtick (`Replace("'", "`")`),
others double it to `''` (`Replace("'", "''")`), others (with `N'…'` literals) double it, and a few crude
paths simply strip `'`, CR and LF. The result is that the same logical value can be stored differently
depending on which screen wrote it, and matching/dedup logic must itself normalise (e.g. `LTRIM(REPLACE(
ShortDescription, '''', '`'))`).

> **BR-DESC-016** — Single quotes are escaped inconsistently: some paths use `'` → backtick
> (`Replace("'","`")`), others use `'` → `''` (`Replace("'","''")`). This is per-call, not centralised. —
> [13_Descriptions](13_Descriptions.md)

Additional crude sanitisers observed:
- Strip `'`, CR, LF and trim ([06_Articles](06_Articles.md) BR-ART-003;
  [05_Products](05_Products.md) `createNewItem` strips backticks/`'` and upper-cases).
- Unescaped free-text stored inside quotes → **second-order injection** if the value later contains a quote
  ([03_Catalogues](03_Catalogues.md) Q-CAT-005 `CatalogueFlags`).

**Occurs in:** [03_Catalogues](03_Catalogues.md), [05_Products](05_Products.md),
[06_Articles](06_Articles.md), [12_Translations](12_Translations.md), [13_Descriptions](13_Descriptions.md).

---

### P-SQL-11 — Supporting idioms (cross-cutting, lower risk)

These appear repeatedly and are worth normalising, though they are not defects per se:

- **`DisplayOrder = -1 → 9999` sort fallback.** A `CASE WHEN <col>.DisplayOrder = -1 THEN 9999 ELSE
  DisplayOrder END` coalesces the "unordered" sentinel to sort last. Cross-module convention.
  [04_Product_Categories](04_Product_Categories.md), [05_Products](05_Products.md),
  [07_Attributes](07_Attributes.md), [11_Configuration](11_Configuration.md),
  [13_Descriptions](13_Descriptions.md), [18_Pricing](18_Pricing.md), [22_Export](22_Export.md).
- **`WITH (NOLOCK)` hints** on many reads (dirty reads accepted for speed). e.g.
  [06_Articles](06_Articles.md), [08_Property_Values](08_Property_Values.md),
  [09_Options](09_Options.md), [15_Filtering](15_Filtering.md), [22_Export](22_Export.md).
- **Delete-then-reinsert (replace-all) persistence** instead of diffing. e.g.
  [05_Products](05_Products.md) (SP defs), [07_Attributes](07_Attributes.md) (WebEOS, delivery offsets),
  [23_Generation](23_Generation.md) (handbook groups).
- **Raw SQL + exception leaked to the end user** in a `MsgBox` on error (schema/SQL disclosure).
  [03_Catalogues](03_Catalogues.md) BR-CAT-017; [06_Articles](06_Articles.md) BR-ART-008 (admin-gated).
- **Hardcoded magic ids inside SQL** — excluded sites (`SiteId NOT IN (20)`), excluded categories
  (`NOT IN (1,128,129,999)`), synthetic category `999`, hardcoded option ids `8`/`28` (fabric type/colour).
  [05_Products](05_Products.md), [07_Attributes](07_Attributes.md), [09_Options](09_Options.md).

---

## 3. Stored Procedures & Functions Index

All bodies are **`UNKNOWN`** — they exist only in the SQL Server database, not in the extracted C# source.
"Referenced from" lists the module docs where a call site was observed.

| Name | Type | Referenced from (module docs) | Body available? |
|------|------|-------------------------------|-----------------|
| `PDMOptionDataReport` | stored proc | [05](05_Products.md), [08](08_Property_Values.md), [09](09_Options.md), [10](10_Option_Values.md), [14](14_Search.md), [18](18_Pricing.md), [21](21_OCD.md), [22](22_Export.md) | **UNKNOWN** (not in source) |
| `PDMOptionDataReportWithIncList` | stored proc | [09](09_Options.md), [10](10_Option_Values.md), [18](18_Pricing.md), [22](22_Export.md) | **UNKNOWN** |
| `PDMOptionDataReportWithIncBase` | stored proc | [09](09_Options.md), [18](18_Pricing.md), [22](22_Export.md) | **UNKNOWN** |
| `PricePermutation` | stored proc | [18](18_Pricing.md) | **UNKNOWN** |
| `PDMPriceListReportForProductGroup` | stored proc | [23](23_Generation.md) | **UNKNOWN** |
| `fnGetListPrice` | scalar function | [05](05_Products.md), [18](18_Pricing.md), [21](21_OCD.md), [22](22_Export.md) | **UNKNOWN** |
| `fnGetListPriceByItem` | scalar function | [05](05_Products.md), [18](18_Pricing.md), [21](21_OCD.md), [22](22_Export.md) | **UNKNOWN** |
| `fnGetFabricBandOrderCodes` | scalar function | [18](18_Pricing.md) | **UNKNOWN** |
| `fnGetSPComponentCount` | scalar function | [05](05_Products.md) (Q-PROD-020, append at next sequence) | **UNKNOWN** |
| `GetProductOptionCount` | stored proc (OUT param) | [06](06_Articles.md) (Q-ART cross-ref), [21](21_OCD.md) (Q-OCD-010) | **UNKNOWN** |
| `xp_cmdshell` | system XP | [22](22_Export.md), [24](24_Utilities.md) | N/A (SQL Server built-in) |
| `dtsrun` (via `xp_cmdshell`) | external exe | [24](24_Utilities.md) | N/A (OS tool) |

> Not stored procs but worth noting as external logic invoked from SQL/DTS: the **DTS packages**
> `Export_PDM2004_to_DPSDB` ([24_Utilities](24_Utilities.md)) and the DPSDB detach/copy/reattach package
> ([22_Export](22_Export.md)) — both `UNKNOWN` internals.

---

## 4. Security & correctness risks summary

| # | Risk | Pattern | Severity | Notes |
|---|------|---------|----------|-------|
| R-SQL-1 | **SQL injection (OWASP A03)** — end-user/CSV text concatenated into commands; comment markers preserved; the app login also performs `UPDATE`/`DELETE`. | P-SQL-01, P-SQL-10 | **Critical** | Worst in [14_Search](14_Search.md); pervasive everywhere. Rebuild must use parameterised queries / an ORM. |
| R-SQL-2 | **Plaintext credentials & per-user SQL login map** hardcoded in `ConnectionFactory`; server chosen by substring matching. | (P-SQL-01 context) | **Critical** | See [00_System_Architecture](00_System_Architecture.md) §7/§10. Never port literals; use a secrets manager. |
| R-SQL-3 | **`xp_cmdshell` / `dtsrun` OS shell-out** under the SQL service account. | P-SQL-08 | **High** | Privilege-escalation surface; replace with a controlled job/ETL service. |
| R-SQL-4 | **Racy identity generation** — `SELECT TOP 1 … DESC` +1 and `@@IDENTITY` are non-atomic; concurrent inserts collide or mis-attribute. | P-SQL-03 | **High** | Use `IDENTITY`/sequences + `OUTPUT`/`SCOPE_IDENTITY`. Affects descriptions, translations, options, audit ids. |
| R-SQL-5 | **Last-writer-wins writes** on all hand-written `UPDATE`s (no concurrency guard), while only adapter grids use `@Original_*`. | P-SQL-04 (absence) | **High** | Concurrent editors silently overwrite (e.g. `CatalogueFlags`, prices, descriptions). |
| R-SQL-6 | **Invisible business logic** — core pricing/option/report semantics live in `UNKNOWN`-body procs/functions. | P-SQL-06 | **High** | Migration cannot be specified from C# alone; the SQL objects must be extracted separately. |
| R-SQL-7 | **32-bit Jet/OLE DB lock-in** for all pCon MDB access. | P-SQL-07 | **High** | Deprecated x86 provider; needs a new geometry/commercial-data strategy. |
| R-SQL-8 | **Second-order injection** — free-text stored unescaped inside quotes, then re-read/concatenated. | P-SQL-10 | **Medium** | e.g. [03_Catalogues](03_Catalogues.md) `CatalogueFlags`. |
| R-SQL-9 | **Malformed-SQL latent bugs** from missing-space concatenation. | P-SQL-09 | **Medium** | One dead ([04](04_Product_Categories.md)/[16](16_Ordering.md)), one live-but-tolerated ([07](07_Attributes.md)). Do not port verbatim. |
| R-SQL-10 | **Schema/SQL disclosure** — raw SQL + exception shown to end users on error. | P-SQL-11 | **Medium** | [03_Catalogues](03_Catalogues.md) BR-CAT-017. |
| R-SQL-11 | **Inconsistent escaping** produces divergent stored values across screens. | P-SQL-10 | **Medium** | Requires normalisation on read (`REPLACE(...,'''','`')`). |
| R-SQL-12 | **Audit gap on cloud** — `PDMAudit` writes are skipped on `eoscloud` servers. | P-SQL-05 | **Medium** | Price/product-code changes are unaudited in the cloud environment. |
| R-SQL-13 | **`NOLOCK` dirty reads** on export/report paths. | P-SQL-11 | **Low/Medium** | Can export uncommitted/partial data. |

> Everything above is provable from the cited module extractions. Where a claim could not be verified from
> those extractions (e.g. whether the audit path opens a genuinely separate `SqlConnection`), it is marked
> `UNKNOWN` inline rather than asserted.
