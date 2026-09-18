# PDM Pricing Parity Audit

## Audited against
- DPS/GetPrice.cs
- GetPrice.getListPrice
- Standard GetPriceExt flow

## Implemented controls
- site/currency/effective-date propagation
- catalogue eligibility and ordering
- item and price-matrix validation
- ordered option retrieval
- exact and prefix order-code matching
- OptionId consumption
- SuperProduct component base totals
- component quantities
- FeaturePositionString / TertiaryOption / DisplayOrder matching
- product-family display overrides
- NOCLE7/NOCLE8 third-position repeated-code scan
- NODL third-position OAK duplicate allowance
- OF...2 OptionId 3344/8 deferred increment behavior
- component-row conflict removal after consumption

## Separate legacy branch identified
The original GetPrice.cs has a USdata path. That path queries:
- USItem
- USItemOptionValues
- USOptionValue
- USDependentOptionValues

Dependent options are not part of the normal non-US PDM query. A dedicated repository method has been added, but it must only be invoked when the source flow positively resolves to the legacy USdata branch. SiteId alone is not assumed to mean USdata.

## Remaining verification requirement
Runtime parity must be tested with identical:
- item
- option sequence
- site
- currency
- effective date

for legacy GetPrice output versus the Python validator. Static source parity alone cannot prove every database-data edge case.
