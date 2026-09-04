# PDM Pricing Parity Scope

The validation engine follows the legacy PDM flow for standard items:

1. Resolve site and currency.
2. Resolve and order validation catalogues.
3. Validate item status and price matrix.
4. Validate catalogue eligibility.
5. Retrieve ordered option rows using PDMOptionDataReportWithIncList.
6. Verify selected codes and consume OptionId groups.
7. Price base using the GetPriceExt fnGetListPrice query.
8. Add option increments using the same OptionId consumption behavior.
9. Compare final PDM price to SIF or OBX source price.

SuperProducts additionally use ItemComponents and component quantities for parent base pricing.

The legacy getListPrice implementation contains product-family-specific exceptions and interactive warning behavior. Those exceptions must be isolated from generic validation rather than applied globally.
