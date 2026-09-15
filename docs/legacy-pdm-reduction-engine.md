# Legacy PDM Reduction Engine — Read-Only Investigation

## Purpose

Define the generic reduction model before changing `EngineeringReductionService`.
This document is intentionally independent of the 591-row sample. The sample is validation data only.

## Proven legacy model

The legacy PDM system does not determine a base article by fixed character positions.
The forward process is:

```text
PDM Product
  + Product/ProductRange OrderCodeFormatString
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

## Rules recovered from legacy code

### 1. Product identity is part of the article

`Product.Product` is not merely a display label. Investigation of a real item showed that article characters can originate from the Product identity itself. Functional attributes with no `OrderCodeValue` can therefore affect the Product identity rather than contributing a suffix segment.

### 2. Order-code token sequence comes from OCFS

The sequence is defined by:

```text
Product.OrderCodeFormatString
    if non-null
        otherwise ProductRange.OrderCodeFormatString
```

The legacy parser replaces selector tokens in that existing format string. `Attribute.DisplayOrder` and `Option.DisplayOrder` are UI/evaluation ordering metadata, not a universal replacement for the OCFS sequence.

### 3. Values are PDM entities, not inferred characters

A configurable segment must be traced through:

```text
Attribute/Option
    -> AttributeValue/OptionValue
    -> OrderCodeValue
    -> OCFS token
```

The reducer must retain IDs where possible. Names and character patterns are not sufficient identifiers.

### 4. Filtering has eligibility rules

The legacy permutation path considers:

- product membership
- catalogue membership
- attribute/value availability
- attribute value exclusions
- dependent attributes/options
- physical versus functional attributes

Therefore a mathematically possible character combination is not automatically a valid PDM configuration.

## Generic reduction algorithm to implement

### Phase A — Build the PDM truth model

For each Product/ProductRange relevant to the selected catalogue/category, load:

1. ProductId
2. Product/ProductRange identity
3. effective OCFS (Product override, otherwise ProductRange)
4. ProductAttributeValues
5. Attribute metadata
6. AttributeValue metadata
7. AttributeValue.OrderCodeValue
8. AttributeValue exclusions
9. Product/Range option values
10. catalogue-gated/dependent option values
11. Item/BaseAttributeValues when reconstructing an existing article
12. ItemOptionValues when present

### Phase B — Reconstruct each existing article

For an existing Item:

1. resolve `Item.ProductId`;
2. resolve `Product.Product`;
3. load the item's BaseAttributeValues;
4. load item-level options;
5. map selected IDs to their PDM attributes/options;
6. apply the effective OCFS;
7. expand the selected `OrderCodeValue` tokens;
8. verify the generated article equals the original article.

This round-trip check is mandatory. An article that cannot be reconstructed exactly must not be reduced silently.

### Phase C — Determine reduction/base identity

The base is derived from PDM semantics, not from `code[:N]`.

A candidate base is valid only when all articles assigned to that base share the same PDM Product identity/identity-defining configuration after configurable attribute/value selections are removed from the representation.

The algorithm must support:

- different article lengths;
- different numbers of configurable attributes;
- attributes with multi-character codes;
- attributes with one-character codes;
- attributes without OrderCodeValue;
- Product-level OCFS overrides;
- different token order between series;
- dependent options;
- exclusions;
- special products whose Product identity carries functional configuration.

### Phase D — Prove the reduction by filtering

For every proposed reduced master:

```text
reduced master selections
        -> execute equivalent PDM filtering
        -> obtain candidate Product/Items
```

The candidate set must equal the legacy PDM filter result.

The reducer must also satisfy the reverse direction:

```text
legacy PDM filter result
        -> reduced master
        -> same candidate set
```

No character-prefix heuristic is accepted as the final rule unless PDM metadata independently proves that rule for that series.

## Current implementation that must not be trusted as final logic

`services/engineering/engineering_reduction_service.py` currently contains logic based on materialised article-set lengths and prefix slicing, including `code[:base_len]` and width calculations. That logic may remain temporarily for UI compatibility, but it must not be treated as the final generic PDM reduction algorithm.

## Remaining legacy evidence required before production implementation

1. Exact body/semantics of legacy `ProductsList` / `USProductsList` stored procedures.
2. Complete relevant filtering path in `AttributeValidator.cs` where current attribute selections are converted into candidate Products.
3. Complete item-level BaseAttributeValues/ItemOptionValues extraction in the current Python PDM repository.
4. A live/database-backed round-trip test over multiple product series, not just the 591-row sample.

## Validation strategy

The 591-row dataset is one regression fixture only. It must not define the algorithm.

The real acceptance test is a cross-series PDM round trip:

```text
PDM filter -> Product/Item -> article reconstruction
article -> PDM configuration -> PDM filter
```

Both directions must agree for representative products from multiple series, including products with different code lengths and different OCFS structures.

## Current conclusion

The generic business model is now clear enough to design the replacement, but production code should remain unchanged until the exact legacy filter semantics and item-level configuration path are recovered. The next implementation step is a read-only PDM compatibility layer that reproduces the legacy selection semantics and reports mismatches; it should be tested across product series before it replaces the current reduction service.
