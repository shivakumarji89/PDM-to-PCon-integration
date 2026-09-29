# Legacy PDM Handbook — Searchable Index

*Navigation layer over the [Legacy PDM Business Logic Handbook](../README.md). These documents let you locate any
business rule, method, class, SQL query, table, feature, or dependency without manually searching the module docs.*

**These are index/navigation documents only** — they cross-reference the handbook and do **not** duplicate or
replace the numbered module documents (`../00`–`../28`).

---

## Find things fast

| I want to find… | Open | Search tip |
|-----------------|------|------------|
| A **business rule** (`BR-…`) | [Business_Rules_Index](Business_Rules_Index.md) → part files | Ctrl+F the rule id, e.g. `BR-PROD-042` |
| A **method** | [Method_Index](Method_Index.md) | Ctrl+F the method name, e.g. `getBasePrice` |
| A **class** | [Class_Index](Class_Index.md) | Ctrl+F the class, e.g. `CADMaintenance` |
| A **SQL query** | [SQL_Index](SQL_Index.md) | Grouped by domain; Ctrl+F a `Q-…`/`O-…` id or table |
| A **table** | [Table_Index](Table_Index.md) | Ctrl+F the table, e.g. `OptionValue` |
| An **engineering feature** | [Feature_Index](Feature_Index.md) | e.g. `pCon`, `Var Conditions`, `Lead Time` |
| **Hidden logic / magic values** | [Engineering_Features](Engineering_Features.md) | e.g. hardcoded IDs, special users |
| **Execution flow** | [Call_Hierarchy](Call_Hierarchy.md) | Startup → … → Export, plus UI round-trip |
| **Who depends on what** | [Dependency_Map](Dependency_Map.md) | Hub classes, shared helpers, externals |
| **What's ready to migrate** | [Migration_Checklist](Migration_Checklist.md) | Per-module go/no-go + blockers |

---

## The 10 index documents

1. [Business_Rules_Index](Business_Rules_Index.md) — all 769 `BR-*` rules → module, description, methods, SQL, tables (split into [parts/](parts/))
2. [Method_Index](Method_Index.md) — methods → class, purpose, calls, called-by, module
3. [Class_Index](Class_Index.md) — classes → purpose, responsibilities, methods, dependencies
4. [SQL_Index](SQL_Index.md) — queries grouped by domain → purpose, tables, callers, rules
5. [Table_Index](Table_Index.md) — tables → PK/FK, used-by classes/SQL, modules
6. [Feature_Index](Feature_Index.md) — engineering features → class, methods, SQL, rules
7. [Call_Hierarchy](Call_Hierarchy.md) — high-level + UI round-trip execution flow
8. [Dependency_Map](Dependency_Map.md) — dependency graph, shared helpers, externals
9. [Engineering_Features](Engineering_Features.md) — hidden logic, magic numbers, hardcoded IDs, flags
10. [Migration_Checklist](Migration_Checklist.md) — per-module migration readiness tracker

---

## Source of truth

The **authoritative** rule statements, SQL citations, and data model remain in the numbered handbook docs:
[27_Business_Rules_Index](../27_Business_Rules_Index.md), [28_Call_Hierarchy](../28_Call_Hierarchy.md),
[25_Common_SQL](../25_Common_SQL.md), [26_Data_Model](../26_Data_Model.md), and the module docs `../00`–`../24`.
Where a mapping is not provable from source it is marked **`UNKNOWN`**; `—` means "not explicitly mapped".
