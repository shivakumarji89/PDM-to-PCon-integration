# Integration Plan — Legacy PDM Reduction Engine

## 1. Keep the current production reducer unchanged

Do not replace `EngineeringReductionService` yet. The new engine is an isolated read-only discovery component.

## 2. Load PDM truth data

Provide Products with ProductId, Product identity, ProductRange, eligibility, and the complete set of ProductAttributeValueIds. When reconstructing actual Items, also load Item/BaseAttributeValues and option selections.

## 3. Validate legacy filter semantics

For each proposed selected AttributeValueId set, reproduce the proven all-selected-values filter semantics and compare its ProductId set with the real PDM stored procedure where a live database connection is available.

Before production use, correct the compatibility layer's known details:

- `USProductsList` receives ProductCategoryId, not ProductRangeId.
- Product OCFS fallback is NULL-based: Product.OrderCodeFormatString falls back to ProductRange.OrderCodeFormatString only when the Product value is NULL, not when it is an empty string.

## 4. Reconstruct articles

Use effective OCFS plus PDM AttributeValue/OptionValue OrderCodeValue metadata to expand the stored configuration and verify that the generated article exactly equals the original article.

## 5. Discover candidate groups

Run `LegacyPDMReductionEngine.discover_exact_groups()` against the PDM Product model. Candidate groups are generated from exact Product sets inducible by the legacy all-values filter semantics.

## 6. Apply new grouping policy

Use `select_non_overlapping_groups()` only after the candidate groups have been inspected. This policy is intentionally separate from legacy filtering so that business decisions can be changed without changing PDM compatibility.

## 7. Cross-series validation

Validate on multiple Product series and code structures. The 591-row sample remains a regression fixture, not the source of the generic algorithm.

## 8. Production integration gate

Only after the round-trip and filter-equivalence tests pass should the new engine be wired into the production reduction path. The first production integration should be feature-gated and preserve an audit/report mode for mismatches.
