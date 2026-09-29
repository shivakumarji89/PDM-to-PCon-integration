# Pricing Domain

**Confirmed finding:** repository/OCD pricing resolves via `Base Article + Variant Condition`, **not** a simple `Final Article Number → Price` lookup, unless source evidence explicitly supports that for a specific case.

| Document | Covers |
|---|---|
| [Pricing_Model.md](./Pricing_Model.md) | Current pricing model; why pricing is item-level and deliberately excluded from the Builder Table |
| [Variant_Condition.md](./Variant_Condition.md) | `com_VariantCondition` generation from order codes |

For the legacy PDM pricing system in full (formulas, permutation, maintenance UI), see [`../PDM/Legacy_PDM_Business_Logic/18_Pricing.md`](../PDM/Legacy_PDM_Business_Logic/18_Pricing.md). For the `tCOMd_Price`/`tCOMd_PriceList2` table structure, see [`../Repository/Tables/`](../Repository/Tables/).
