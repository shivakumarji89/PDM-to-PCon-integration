# PDM Order-File Validation

**Status:** Implemented from source references and exercised read-only against PDMLive on 2026-09-29. Full legacy UI parity remains unverified.

## Current Flow

SIF validation and OBX repricing converge on `SifValidationService._validate_group`. OBX parsing, sale/`pd=1` price selection, and deduplication remain owned by `ObxValidationService`. Validation pricing is separate from product snapshot catalogue loading and from price-generation workflows.

For normal `Item` records, validation uses the current currency-to-site resolver, then reads active catalogues for that resolved site in lead-time order. Eligibility requires the item/catalogue relationship, an active catalogue product category, and the product-range relationship. Item status and a complete site/currency price matrix are checked before pricing. Missing or incomplete context is unresolved.

Normal base pricing uses the isolated `fetch_validation_get_price_ext_base_prices` query. It applies item product-code overrides, `BasePriceRef`, `PriceMatrix.Rounding`, and SQL Server `fnGetListPrice`. The general-purpose `fetch_item_base_prices` method is unchanged.

Normal selected options are retrieved from `PDMOptionDataReportWithIncList`. Validation matches exact codes first, then the longest matching `#` prefix, ignores inactive values and the procedure's `IsFabric = 2` dependent-colour rows, and consumes each `OptionId` group once. The complete result, including dependent-colour rows, remains available as the shared increment source. SIF retains its existing explicit-`OL` increment behavior; selected codes without `OL` are validated but do not gain a standard SIF increment. OBX continues through the shared validation path.

SuperProducts use a distinct component path: component base prices are resolved through each component's price matrix, multiplied by BOM quantity, reconciled against the BOM, and left unresolved if any component price is missing. Component increments use component position metadata, display/tertiary positions, and the source-audited family display overrides. This path does not change generator pricing.

USdata is a separate domain. A normal `Item` record wins when a code exists in both `Item` and `USItem`; only USItem-only codes use the US base and direct/dependent increment queries. USItem-only validation bypasses the normal catalogue and VerifyOptions branches. Site ID alone never selects USdata.

Validation dates reuse one normalizer for UI dates (`DD-Mon-YYYY`), server dates (`DD Mon YYYY`), ISO dates, explicit DMY slash dates, and date/datetime values. Invalid or timezone-ambiguous inputs are rejected. Base, component, and US price queries construct the legacy SQL datetime using `DATEADD`/`DATEDIFF` around `CAST(? AS datetime)`.

## Audit Boundaries

Catalogue selection intentionally follows the current main site's resolved `SiteId`; the parity branch's hard-coded regional site-ID lists were not copied. Current main's currency regions were checked against PDMLive `Site.Site` codes and descriptions; lookup prefers the code and retains the known description as a fallback.

### Read-only PDMLive observations

- G1: `MM.RV1.BF` uses `BasePriceRef = 2` and `BasePrice2 = 550`; both the isolated `fnGetListPrice` path and existing `fnGetListPriceByItem` API returned 495 GBP. A rounding-2 item returned 24.39. No active UK/GBP `BasePriceRef = 3` item was found.
- G1/G6: item `10008210901` has a GBP formula effective 2026-11-03. The isolated API returned 51.00 on 2026-10-15 and 2026-11-02, then 53.00 on 2026-11-03 and 2026-11-15.
- G2/G3: normal item `AER1B33DW-AERON-FAST01` resolved to catalogue 37; the procedure returned 14 option rows. Selecting its active `ALP` code completed validation with `ok` at 1938.00.
- G4: SuperProduct `1205C5BQ` resolved two BOM rows and two component prices. Their quantity-weighted total was 15587.00, and service validation returned `ok` when checked against that total.
- G5: `CJ111AASC` exists in `USItem` only. Its USD base was 764.00; direct option `AJ` was 45.00. Dependent option `8M06` was returned but its common increment was NULL; the combined service result was 809.00 and `ok`. A read-only scan found no non-NULL dependent common increments for the selected USD/SG USItem scope.

These checks prove that the implemented SQL executes against PDMLive and exercise representative rows. They do not compare every result to an interactive legacy GetPrice/VerifyOptions execution. In particular, positive US dependent-option pricing and `BasePriceRef = 3` remain without a representative live case.

The source audit documents NOCLE7/NOCLE8 repeated-code scanning and the NODL/OAK duplicate allowance as requiring validation-case testing. Those exceptions are not implemented. Standard increment quantity/group behavior, the current OBX parser, and catalogue snapshot loading are intentionally unchanged.

## Source References

- G1 base/date: `46c4632`, `405f3c0`, `8ad7e4c`, `f7a9e37`.
- G2 catalogue/context: `6471be0`, `15e1713`, `17aeead`, `78047db`, `39b0232`, `ab7da90`.
- G3 option verification: `fb37de4`, `807b200`, `7dd4c19`, `463c11a`, `0938b6c`.
- G4 SuperProduct pricing: `09f933d`, `7029c8f`, `4feaca5`, `9c3036e`, `dfa4c71`, `0836978`, `ef77e83`, `bb57b8b`, `387759c`, `36dd33e`.
- G5 USdata: `9f325f9`, `f59143a`, `4d85897`, `5a9c130`, `5343608`, `036994a`, `7c9746f`, `61efb43`.
- G6 date handling: `8ad7e4c`, `f7a9e37`.

Before parity can be frozen, representative normal, BasePriceRef, rounding, future-date, catalogue, VerifyOptions, SuperProduct, and USItem/direct/dependent cases still need read-only comparison against the configured PDM database.