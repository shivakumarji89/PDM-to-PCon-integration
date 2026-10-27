# Maintenance VARCOND incremental relations

Scope: **Maintenance → Pricing Relation → Article VARCOND Relations** only.
Development keeps `VarCondService.generate_live`.

## Defect

`$VARCOND = '<component> 8=' + Fabric_Type IF …` was missing from generated
relations (for example `PA_GESCRNNP/S/U.105508F`). `generate_live` read increments
with `PDMRepository.fetch_item_option_increments`, whose
`OrderCodeValue NOT LIKE '%#'` filter drops every Fabric type (option 8) value:
all of `GESNNU.105508F`'s option-8 codes are `#`-suffixed (`Z1C#`, `V26#`, …), so
the query returned 0 rows. Reduction, exclusion, substitution and the UI were not
involved.

## Legacy behaviour (compiled `PDMMaintenance.exe` 1.0.9686.24988, IL)

`PriceMaintenance.getOptionIncrementSuffixes(myproduct, memo, names, ids, verbose,
optionIdFilter)` - read with a read-only metadata/IL decoder; the executable was
not run:

1. **Item resolution.** A dotless code that does not end in `F` and does not start
   with `MET` becomes `SELECT TOP 1 Item … LIKE '<code>%F' AND Status = 1 ORDER BY
   Item`. A code containing `-` becomes the last parent super-item holding it.
2. **Procedure call.** `EXEC PDMOptionDataReportWithIncBase @item, @siteId,
   @excludeFabricColours` with **`@siteId = 1` and `@excludeFabricColours = 1`
   hard-coded** (`ldc.i4.1` boxed for both). The legacy form has no site selector,
   so the Workbench has none either. Output depends on the site (only sites 1 and
   19 return the option-8 increment for these articles), which is why the constant
   matters.
3. **Rows.** Rows with a non-empty `IncPriceBase` (and matching `optionIdFilter`,
   `-1` = all) contribute `(OptionId, Option2)`. The `Component` column is **not**
   compared.
4. **Cache** keyed `<item>~<optionIdFilter>`.
5. `VarCondThread.execThread` runs `ParsePConPropertyName(Option2)`, applies the
   HZ13/HZ14 fabric rename, de-duplicates by property name and emits
   `'<component> <optionId>=' + <name>` after the component's base and
   `$SET_PRICING_FACTOR` lines.

Verified output (live PDM, 2026-10-27): only `GESNNU.105508F` and `GESNNS.105508F`
produce `8=' + Fabric_Type`; `GESG.`, `GESU.`, `GESY.`, `GEST.` produce none.

## Implementation

`services/maintenance_varcond_service.py`: raw rows per parent (attributes, BOM
with `FeaturePositionString`, per-component procedure rows) are loaded once and
cached in memory; prefix, exclusion and substitution edits run locally on the
cached data. PDM is read again only for a parent not yet loaded, on explicit
**Generate / Refresh**, or when the product snapshot changes.

Not ported: the family-specific fallbacks `execThread` runs when the first lookup
returns nothing (RYMPSH, RYT, RY3VNN…HW, RY2U). They stay in `VarCondService`'s
opt-in `legacy_exact` mode.

Tests: `tests/test_maintenance_varcond.py`. No end-to-end run of the legacy tool
was performed; the comparison is against the legacy procedure's live output and
the IL-derived rules above.
