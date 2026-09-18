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


## Legacy exception audit

The following are explicit display-position overrides in `GetPrice.getListPrice` and
are implemented only inside SuperProduct component increment matching:

- YH304/YH306/YH307 + OptionId 6733 -> position 3
- YI303/YI305 + OptionId 6768 -> position 3
- AS family position remapping (including AS4/AS5)
- NOFTE + OptionId 6820 -> position 1
- NODLE1/NODLE2 + OptionIds 6699/6695 -> positions 1/2
- EX1/EZ1 + OptionId 1206 -> position 3 when source is 1
- OAW30 + OptionIds 3278/3716 -> positions 1/2
- HE + OptionIds 3765/3761 -> positions 3/4
- OF...2 deferred OptionId 3344/8 calculation

NOCLE7/NOCLE8 repeated-code scanning and NODL/OAK duplicate charging are separate
control-flow exceptions and remain explicitly marked for validation-case testing.
