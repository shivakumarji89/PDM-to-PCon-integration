# Maintenance pricing: end-to-end legacy parity plan

Scope: Maintenance module only. Do not change Development, shared snapshot
loading, or production export behavior while investigating.

## Principle

PDM is not a single pricing method. The comparison must follow the complete
path from source fetch through calculation, variant-condition construction,
text-block resolution and MDB export. A match in the SQL fetch alone does not
prove the final pCon rows match. Likewise, the Price Relation / VARCOND worker
is a separate path and must not be treated as the authority for price records.

## PDM paths to compare

| Stage | PDM reference | Workbench reference | Required evidence |
|---|---|---|---|
| Article price pull | UpdatePriceThread.execThread -> PriceMaintenance.UpdatePConItemPrice / article base and surcharge queries | PDMRepository.fetch_item_base_prices, fetch_item_option_increment_prices, PricingService | Same item, date, currency and site; compare raw source rows and computed values |
| Super-product/global price pull | UpdatePriceThread.execThread -> PriceMaintenance.UpdatePConItemIncrementalPrice | PDMRepository.fetch_global_option_increment_prices, PricingService | Same catalogue, program, site, option-value rows, selected raw increment, price and source lookup |
| Option/variant condition | PDM worker's condition construction and existing-row lookup keys | PricingService.build_records and source/target fields on PriceRecord | Compare source option ID/code, target option ID/code, condition text, order and duplicates |
| Standard global price text block | PriceMaintenance.AddMissingGlobalPricingRecords | services/price_text_blocks.py, PriceMdbExportService | Existing text lookup, text-name/display-name rule, package scope, language columns, com_TextID link and preservation of existing links |
| Article price row export | PDM article-price update/insert path | PriceMdbExportService -> tCOMd_Price | Article identity, base/upcharge level, condition, price, currency/list and validity |
| Super-product/global row export | PDM global-price update/placeholder path | PriceMdbExportService -> tCOMd_GlobalPrice | Row matching, insertion condition, level X, price, list and text link |
| Repeat run | PDM second invocation | second Workbench export | No unintended second-run changes or duplicate rows |
| Price Relation / VARCOND | Separate PDM relation worker / export handler | PricingRelationService and its Maintenance UI | Compare separately; never conflate relation text with price-row text blocks |

## Existing evidence to reuse

- scripts/pdm_differential/differential.py runs the compiled legacy price
  update and the Workbench export against separate copies of the same backup
  MDB, then compares price rows, global rows, lists and text rows. Its scenarios
  already include article, global/super-product, placeholder, text reuse/create,
  text-name collision and repeat-run cases.
- docs/03_Workflows/pdm_differential_report.json records previously captured
  outcomes. Treat each scenario's status and limitations as evidence only for
  that scenario; do not extrapolate to all option types.
- scripts/pdm_differential/fetch_parity.py and
  docs/03_Workflows/pdm_ui_tool_fetch_parity.md cover bounded source-fetch
  parity for article and global prices. Those source-equivalent SQL comparisons
  are not a substitute for actual UI/MDB parity.
- docs/03_Workflows/pricing_pdm_parity.md documents the legacy export rules
  and text-block semantics.

## Option-type investigation matrix

Run the same source item set through the legacy and Workbench paths, retaining
all rows and duplicates. Include examples for Fabric Type, Fabric Colour,
Trim, Finish, and ordinary options, across article and global/super-product
pricing where the PDM UI supports each path.

For each output row capture:

1. source item and component item;
2. source OptionId, OptionValueId, raw option code and raw selected increment;
3. selected/calculated price and price band;
4. generated condition and the condition used to find an existing MDB row;
5. article/global table, level, list, currency and validity dates;
6. text name, display label, com_TextID, whether the text was reused/created,
   and whether an existing text link was preserved;
7. missing, extra, duplicate and reordered rows;
8. second-run changes.

Do not assume all option families should map from one option to another.
For every remapping, prove the legacy rule and keep the original price-source
identity separate from any export-target identity. A difference is fixed only
after it is classified as a source-fetch issue, calculation issue, condition /
lookup issue, text-block issue, or MDB export issue.

## Safety and completion gates

- Use the installed legacy binary from a copy and an explicitly approved
  non-production SQL target.
- Use a backup MDB copied separately for PDM and Workbench. Never point the
  harness at the live OCD: PDM has no transaction or rollback.
- Keep the normal Workbench production path unchanged until the mismatch has
  reproducible input/output evidence and regression tests.
- Unit tests that mock the legacy process are adapter tests, not proof that the
  legacy worker ran.
- Do not claim full parity until the affected fetch path, final MDB rows,
  standard text blocks and repeat-run behavior are all compared for the
  relevant option families.
