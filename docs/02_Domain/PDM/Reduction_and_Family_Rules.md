# PDM Reduction and Family Rules

**Status:** Read-only investigation, partially implemented in a read-only compatibility layer. `EngineeringReductionService` has **not** been replaced.
**Related:** [Family_Boundary_Findings.md](./Family_Boundary_Findings.md) · [SKU_Configuration_Decode.md](./SKU_Configuration_Decode.md)

## Purpose

Define, from real legacy PDM source (not from the 591-row sample dataset), how legacy PDM derives a base article/order code from a Product and its selected configuration — the inverse of which is "reduction": going from a full article back to its base identity and configurable selections. This document consolidates three earlier investigation passes (business-rule findings, the full reduction-engine model, and implementation status) into one canonical reference.

## Proven legacy model

Legacy PDM does **not** determine a base article by fixed character positions or a `code[:N]` prefix rule. The forward process is:

```text
PDM Product
  + Product/ProductRange OrderCodeFormatString (OCFS)
  + selected ProductAttributeValues / BaseAttributeValues
  + selected ProductOptionValues / ItemOptionValues
  + AttributeValue/OptionValue OrderCodeValue
  + exclusions / catalogue eligibility
        |
        v
  final article/order code
```

The inverse reduction must therefore be:

```text
final article
   -> identify PDM Item/Product
   -> identify Product.Product (identity/base)
   -> identify selected attribute/value IDs and option/value IDs
   -> determine which selections are configurable
   -> produce reduced representation
```

`services/engineering/engineering_reduction_service.py` currently uses materialised article-set lengths, prefix slicing (`code[:base_len]`), and width calculations. This is a known **implementation assumption**, not established legacy business logic, and must not be trusted as the final generic rule.

## Rules recovered from legacy source

1. **Product identity is part of the article.** `Product.Product` is not merely a display label — investigation of a real item showed article characters can originate from the Product identity itself. Functional attributes with no `OrderCodeValue` can affect Product identity rather than contributing a suffix segment.
2. **Order-code token sequence comes from the OCFS**, not from `Attribute.DisplayOrder`/`Option.DisplayOrder`:
   ```text
   Product.OrderCodeFormatString
       if non-null
           otherwise ProductRange.OrderCodeFormatString
   ```
   The legacy parser replaces selector tokens in this existing format string.
3. **Values are PDM entities, not inferred characters.** A configurable segment must be traced through `Attribute/Option -> AttributeValue/OptionValue -> OrderCodeValue -> OCFS token`. IDs must be retained where possible; names/character patterns are not sufficient identifiers.
4. **Filtering has eligibility rules**: product membership, catalogue membership, attribute/value availability, attribute value exclusions, dependent attributes/options, and physical vs. functional attributes. A mathematically possible character combination is not automatically a valid PDM configuration — the legacy permutation path explicitly rejects a selected value that conflicts with `AttributeValueExclusions`, and only uses catalogue-eligible attribute values that have an `OrderCodeValue` (archived `PDMMaintenance` permutation logic).
5. **The product filter is selection-driven, not article-prefix-driven.** The archived `ProductSelector` (`DPS/HermanMiller.EOS.UI/ProductSelector.cs`) does not derive a Product by slicing an article string — it sends the current selected attribute/value state to a stored procedure.
6. **`AttributeValidator.cs` treats attribute values as explicit PDM relationships**, not article-string positions. The Product Attribute Value list is loaded by joining `ProductAttributeValues -> AttributeValue -> Attribute` (ordered by `Attribute.DisplayOrder, AttributeValue.DisplayOrdinal`); the Item Attribute Value list joins `BaseAttributeValues -> AttributeValue -> Attribute` with the same ordering. `AttributeType == 0` is explicitly a functional attribute value — it can distinguish Product identity without contributing a literal suffix token. `AttributeValidator` also verifies Product/Item compatibility by comparing selected Product Attribute Value IDs against the Item's Base Attribute Value IDs before allowing values to be copied between them — PDM relationship data, not string similarity, is authoritative.

## Exact UI-to-filter contract (legacy filter boundary)

The archived `ProductSelector` is the direct caller of the legacy product filter. For a normal range it invokes:

```text
ProductsList(@ProductRangeId, @LanguageId, @SelAttribValuesXml)
```

For a US range:

```text
USProductsList(@productCategoryId, @languageId, @selAttribValuesXml)
```

Both return `ProductId`, `short_desc`, `ImageFile`, `OrderCode`. The non-US call uses a 300-second command timeout.

The attribute-selection XML is constructed by `TemplateContainer.AttributeXml`:

```xml
<attributes>
  <attribute attributeid="..." attributevalueid="..."/>
  ...
</attributes>
```

Only selectors with an actual `AttributeValueId` are emitted as active `<attribute>` elements; disabled selectors appear separately as `DISABLED_attribute`. `AttributeSelector` obtains its `OrderCodeFormatKey` via `AttributeOrderCodeFormatKeyGet` and its selected `OrderCodeValue` directly from `AttributeValue.OrderCodeValue`.

So the legacy filter boundary is:

```text
UI selector state
    -> selected AttributeId + AttributeValueId XML
    -> ProductsList / USProductsList
    -> candidate ProductId + Product + OrderCode
```

The exact XML selection contract is known; the remaining unknown is the internal SQL implementation of the stored procedures (they are database-side, not in the archived repository).

## Generic reduction algorithm

**Phase A — Build the PDM truth model.** For each relevant Product/ProductRange, load: ProductId; Product/ProductRange identity; effective OCFS (Product override, else ProductRange); ProductAttributeValues; Attribute/AttributeValue metadata; `AttributeValue.OrderCodeValue`; AttributeValue exclusions; Product/Range option values; catalogue-gated/dependent option values; `BaseAttributeValues`/`ItemOptionValues` when reconstructing an existing article.

**Phase B — Reconstruct each existing article.** Resolve `Item.ProductId` → `Product.Product` → item BaseAttributeValues → item-level options → map selected IDs to PDM attributes/options → apply the effective OCFS → expand selected `OrderCodeValue` tokens → verify the generated article equals the original. **This round-trip check is mandatory** — an article that cannot be reconstructed exactly must not be silently reduced.

**Phase C — Determine reduction/base identity.** The base is derived from PDM semantics, never from `code[:N]`. A candidate base is valid only when all articles assigned to it share the same PDM Product identity/identity-defining configuration once configurable attribute/value selections are removed. The algorithm must support: different article lengths; different numbers of configurable attributes; multi-character and one-character `OrderCodeValue`s; attributes without an `OrderCodeValue`; Product-level OCFS overrides; different token order between series; dependent options; exclusions; and special products whose Product identity itself carries functional configuration.

**Phase D — Prove the reduction by filtering.** For every proposed reduced master, executing the equivalent PDM filter must return the same candidate Product/Item set as the legacy filter — in both directions (reduced master → candidate set, and legacy filter result → reduced master → same candidate set). No character-prefix heuristic is accepted as final unless PDM metadata independently proves it for that series.

## Implementation status — read-only compatibility layer

The generic model above has been converted into a **read-only** implementation, without changing `EngineeringReductionService`:

1. **Item-level PDM truth** — `LegacyPDMCompatRepository` reads `ItemOptionValues`, `BaseAttributeValues`, `ProductAttributeValues`, `Product.OrderCodeFormatString`, `ProductRange.OrderCodeFormatString`, and Product/Item identity.
2. **Effective OCFS** — implemented exactly as `Product.OrderCodeFormatString` when present, otherwise `ProductRange.OrderCodeFormatString`.
3. **Article reconstruction** — `LegacyPDMReductionService` reconstructs an Item as `Product.Product + OCFS token expansion`, resolving each token through `OrderCodeFormatKey -> OrderCodeValue`. No fixed length, character position, prefix slicing, or series-specific rule is used. The result is compared against the real `Item.Item`; failed reconstruction is reported, never silently reduced.
4. **Legacy filter boundary** — the compatibility repository can invoke the real `ProductsList(ProductRangeId, LanguageId, AttributeXml)` / `USProductsList(...)` procedures against the live PDM database, generating the same selector-shaped XML, so the Python layer never guesses the hidden stored-procedure filtering semantics when the real database is available.
5. **Generic candidate representation** — the analysis result records ProductId, Product code, ProductRangeId, ItemIds/Item codes, configurable attribute IDs, configurable AttributeValue IDs, and the ProductId set returned by the actual legacy filter — the evidence set for the eventual generic reducer.

`EngineeringReductionService`'s existing prefix/length behavior remains untouched until database-backed validation (below) is completed.

## Required acceptance run before replacing the production reducer

1. Select representative Products from multiple series.
2. Reconstruct every selected Item; require exact `reconstructed Item == Item.Item`.
3. Send the reconstructed AttributeId/AttributeValueId XML to the actual legacy `ProductsList`/`USProductsList` procedure.
4. Compare the returned ProductId set with the expected legacy selection.
5. Only after both directions agree across multiple series (different code lengths, different OCFS structures) — replace the current reduction algorithm.

## Validation dataset caveat

The supplied 591-row dataset is a regression fixture only — it must never define the algorithm. Different article lengths and multiple configuration families are exactly why fixed slicing is insufficient.

## Remaining legacy evidence required

1. Exact body/semantics of `ProductsList` / `USProductsList` (database-side, not in the archived repository).
2. Complete relevant filtering path in `AttributeValidator.cs` converting current attribute selections into candidate Products.
3. Complete item-level `BaseAttributeValues`/`ItemOptionValues` extraction in the current Python PDM repository.
4. A live/database-backed round-trip test over multiple product series, not just the 591-row sample.

## Current conclusion

The generic business model is clear enough to design the replacement, and the legacy UI-to-stored-procedure filter boundary is proven. Production code should remain unchanged until the exact stored-procedure filtering semantics and complete item-level configuration path are recovered. The next step is exercising the existing read-only PDM compatibility layer across multiple product series before it replaces `EngineeringReductionService`.
