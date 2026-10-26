# Legacy VARCOND parity review

Status: **source-level review only; runtime parity is not yet proven**.

Scope: legacy `PDMMaintenance.VarCondThread.execThread` compared with the Workbench `services/varcond_service.py` super-product generator. This is not a comparison of the separate non-super-product PA_PRICING algorithm in `services/pricing_relation_service.py`.

## How legacy PDM pulls relation inputs

The legacy worker receives an article list from its caller, opens a SQL connection through the legacy `ConnectionFactory`, then for each selected parent article:

1. Queries `ItemComponents` joined to `Item` to load sub-items and quantities, ordered by numeric `ComponentSequence`.
2. Reads the parent's ordered `BaseAttributeValues` / `AttributeValue` / `Attribute` rows. It uses `OrderCodeValue` for ordinary attributes and slices parametric codes from the parent article number for attributes with `HasDependentOptions`.
3. Normalises property names through `CADMaintenance.parseAttributeNameAsPConProperty`, removes dots from order codes, then applies property exclusions and substitutions.
4. Builds a shared IF expression and emits a `$VARCOND` rule per BOM sub-item. For quantity greater than one it also emits `$SET_PRICING_FACTOR`.
5. Calls `PriceMaintenance.getOptionIncrementSuffixes` for sub-item option increments. The legacy code includes product-family exceptions for `HZ13`, `HZ14`, `RYMPSH`, `RY3VNN...HW`, `RYT`, and `RY2U`.
6. Emits the complete text through the `UpdateStatus` event with the `VARCOND:` prefix.

The legacy worker's `_myfilter` is not a SQL filter in this method; it is used to guard the empty-filter confirmation. The supplied article list controls the parent items processed. The category ID is stored but does not appear to affect the shown generation queries.

## Source-level differences found

| Area | Legacy PDM | Workbench Python | Assessment |
|---|---|---|---|
| Option-increment family exceptions | Explicit HZ13/HZ14 fabric-property remapping and RYMPSH/RY3VNN/RYT/RY2U fallback rules | Python service documents these family-specific suffix rules as not ported | **Known mismatch risk** |
| Component-specific IF properties | Reuses the parent's built IF expression for each BOM sub-item | Python optionally filters parent properties using `component_head_attrs` for each component | **Potential mismatch**; confirm intended behavior against golden output |
| Duplicate BOM component rules | Adds each BOM row to the output arrays; no final identical-rule deduplication in this worker | Deduplicates identical generated rule text | **Known output difference** when BOM rows produce duplicate rules |
| Quantity / pricing factor | Emits factor when quantity > 1 | Also emits factor when quantity > 1 | Similar in the ordinary path; duplicate/order cases still need runtime comparison |
| Attribute name and order-code handling | Legacy helper methods and SQL result order | Python ports helper rules and snapshot ordering | Needs golden-output comparison |
| Data source | Live SQL queries via legacy connection policy | Active Workbench snapshot | Inputs may differ if snapshot loading omits or normalises fields |
| Non-super product pricing | This worker's logic is BOM/super-product oriented | Workbench has a separate non-super `PricingRelationService` path | **Not comparable using this bridge alone** |

## Bridge correction

The legacy `initThread` method requires a `.NET ArrayList`. The bridge now explicitly converts the JSON article list to `ArrayList` before reflection invocation; passing a generic `List<string>` would fail reflection argument binding.

## What is required to establish parity

1. Build the helper on Windows against the actual legacy runtime dependencies.
2. Use a verified non-production PDM database and a small, known super-product article list.
3. Capture legacy output without changing it and generate Python output from a snapshot loaded from the same data.
4. Compare exact text and a normalised rule-level diff, recording missing, extra, duplicate, and reordered rules.
5. Add the observed legacy cases as regression fixtures before enabling any UI integration.

Until these steps pass, do not claim that the Python generator or bridge matches legacy PDM exactly. The bridge is intended to expose the legacy output for comparison; it does not currently write to MDB.
