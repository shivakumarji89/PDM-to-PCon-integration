# Business Rules Index

*Searchable, cross-referenced index of every business rule (`BR-*`) in the Legacy PDM handbook.*
*Each rule is mapped to its **module, short description, source document, related methods, related SQL, and related tables**.*

**Status:** Navigation layer over the handbook. The authoritative rule statements live in
[27_Business_Rules_Index](../27_Business_Rules_Index.md); this index adds the method/SQL/table
cross-references and splits the 769 rows into per-module-group part files for fast lookup.

> **How to use:** find your module prefix in the table below, open its part file, and use your editor's
> in-file search (Ctrl+F) on the Rule ID (e.g. `BR-PROD-042`). Every row links back to the module doc that
> proves the rule with code/query citations. Related methods/SQL/tables are best-effort mappings drawn from
> the module docs; `—` means "not explicitly mapped", `UNKNOWN` means "not provable from source".

---

## Totals

| Metric | Value |
|---|---|
| **Total enumerated business rules** | **769** |
| **Module prefixes indexed** | **25** |
| Referenced-but-not-enumerated ids (excluded) | `BR-PVAL-001`, `BR-PVAL-002`, `BR-CFG-070-flag` |

---

## Where to find each module (part files)

| Part file | Modules (prefix) | Rules | Module docs |
|-----------|------------------|------:|-------------|
| [Part 1](parts/Business_Rules_Index_P1.md) | `BR-ARCH`, `BR-AUTH`, `BR-PERM`, `BR-CAT`, `BR-CATEG`, `BR-ORD` | 83 | [00](../00_System_Architecture.md), [01](../01_Authentication.md), [02](../02_User_Permissions.md), [03](../03_Catalogues.md), [04](../04_Product_Categories.md), [16](../16_Ordering.md) |
| [Part 2](parts/Business_Rules_Index_P2.md) | `BR-PROD`, `BR-ART`, `BR-ATTR` | 120 | [05](../05_Products.md), [06](../06_Articles.md), [07](../07_Attributes.md) |
| [Part 3](parts/Business_Rules_Index_P3.md) | `BR-PVAL`, `BR-OPT`, `BR-OVAL`, `BR-TRAN` | 123 | [08](../08_Property_Values.md), [09](../09_Options.md), [10](../10_Option_Values.md), [12](../12_Translations.md) |
| [Part 4](parts/Business_Rules_Index_P4.md) | `BR-DESC`, `BR-SRCH`, `BR-FILT`, `BR-IMG` | 165 | [13](../13_Descriptions.md), [14](../14_Search.md), [15](../15_Filtering.md), [17](../17_Images.md) |
| [Part 5](parts/Business_Rules_Index_P5.md) | `BR-CFG`, `BR-PRICE`, `BR-OAP`, `BR-ODB` | 108 | [11](../11_Configuration.md), [18](../18_Pricing.md), [19](../19_OAP.md), [20](../20_ODB.md) |
| [Part 6](parts/Business_Rules_Index_P6.md) | `BR-OCD`, `BR-EXP`, `BR-GEN`, `BR-UTIL` | 170 | [21](../21_OCD.md), [22](../22_Export.md), [23](../23_Generation.md), [24](../24_Utilities.md) |

---

## Summary by module

| Prefix | Module doc | Rules | ID range (as present) | Part |
|---|---|---:|---|---|
| `BR-ARCH` | [00_System_Architecture](../00_System_Architecture.md) | 9 | 001–009 | [P1](parts/Business_Rules_Index_P1.md) |
| `BR-AUTH` | [01_Authentication](../01_Authentication.md) | 8 | 001–008 | [P1](parts/Business_Rules_Index_P1.md) |
| `BR-PERM` | [02_User_Permissions](../02_User_Permissions.md) | 15 | 001–015 | [P1](parts/Business_Rules_Index_P1.md) |
| `BR-CAT` | [03_Catalogues](../03_Catalogues.md) | 19 | 001–019 | [P1](parts/Business_Rules_Index_P1.md) |
| `BR-CATEG` | [04_Product_Categories](../04_Product_Categories.md) | 13 | 001–013 | [P1](parts/Business_Rules_Index_P1.md) |
| `BR-ORD` | [16_Ordering](../16_Ordering.md) | 19 | 001–019 | [P1](parts/Business_Rules_Index_P1.md) |
| `BR-PROD` | [05_Products](../05_Products.md) | 70 | 001–070 | [P2](parts/Business_Rules_Index_P2.md) |
| `BR-ART` | [06_Articles](../06_Articles.md) | 18 | 001–018 | [P2](parts/Business_Rules_Index_P2.md) |
| `BR-ATTR` | [07_Attributes](../07_Attributes.md) | 32 | 001–036 (no 003/008/009/012) | [P2](parts/Business_Rules_Index_P2.md) |
| `BR-PVAL` | [08_Property_Values](../08_Property_Values.md) | 33 | 003–035 (001/002 referenced only) | [P3](parts/Business_Rules_Index_P3.md) |
| `BR-OPT` | [09_Options](../09_Options.md) | 30 | 001–030 | [P3](parts/Business_Rules_Index_P3.md) |
| `BR-OVAL` | [10_Option_Values](../10_Option_Values.md) | 30 | 001–030 | [P3](parts/Business_Rules_Index_P3.md) |
| `BR-TRAN` | [12_Translations](../12_Translations.md) | 30 | 001–030 | [P3](parts/Business_Rules_Index_P3.md) |
| `BR-DESC` | [13_Descriptions](../13_Descriptions.md) | 37 | 001–037 | [P4](parts/Business_Rules_Index_P4.md) |
| `BR-SRCH` | [14_Search](../14_Search.md) | 45 | 001–045 | [P4](parts/Business_Rules_Index_P4.md) |
| `BR-FILT` | [15_Filtering](../15_Filtering.md) | 41 | 001–041 | [P4](parts/Business_Rules_Index_P4.md) |
| `BR-IMG` | [17_Images](../17_Images.md) | 42 | 001–012, 020–024, 030–031, 040–043, 050–059, 070–076, 080–081 | [P4](parts/Business_Rules_Index_P4.md) |
| `BR-CFG` | [11_Configuration](../11_Configuration.md) | 48 | 001–018, 020–021, 041–043, 050–053, 060–063, 070–073, 080–082, 090–092, 901–907 | [P5](parts/Business_Rules_Index_P5.md) |
| `BR-PRICE` | [18_Pricing](../18_Pricing.md) | 45 | 010–017, 020–027, 030–036, 040–043, 050–054, 060–062, 070–074, 080–083, 100 | [P5](parts/Business_Rules_Index_P5.md) |
| `BR-OAP` | [19_OAP](../19_OAP.md) | 6 | 001–006 | [P5](parts/Business_Rules_Index_P5.md) |
| `BR-ODB` | [20_ODB](../20_ODB.md) | 9 | 001–009 | [P5](parts/Business_Rules_Index_P5.md) |
| `BR-OCD` | [21_OCD](../21_OCD.md) | 55 | 001–063 (gaps) + `021b`, `031b` | [P6](parts/Business_Rules_Index_P6.md) |
| `BR-EXP` | [22_Export](../22_Export.md) | 60 | 001–060 | [P6](parts/Business_Rules_Index_P6.md) |
| `BR-GEN` | [23_Generation](../23_Generation.md) | 20 | 001–020 | [P6](parts/Business_Rules_Index_P6.md) |
| `BR-UTIL` | [24_Utilities](../24_Utilities.md) | 35 | 001–003, 020–041, 050–062 | [P6](parts/Business_Rules_Index_P6.md) |
| **Total** | | **769** | | |

---

## Related indexes

- **Methods** referenced by rules → [Method_Index](Method_Index.md)
- **SQL** query IDs (`Q-*` / `O-*`) referenced by rules → [SQL_Index](SQL_Index.md)
- **Tables** referenced by rules → [Table_Index](Table_Index.md)
- **Features** grouping related rules → [Feature_Index](Feature_Index.md)
- **Execution flow** → [Call_Hierarchy](Call_Hierarchy.md) · **Dependencies** → [Dependency_Map](Dependency_Map.md)
- **Migration readiness** per module → [Migration_Checklist](Migration_Checklist.md)
- **Authoritative rule statements** → [27_Business_Rules_Index](../27_Business_Rules_Index.md)
