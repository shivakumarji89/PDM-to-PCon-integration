# Legacy PDM Reduction — Implementation Status

## Completed in the isolated compatibility layer

The generic investigation has been converted into read-only implementation without changing `EngineeringReductionService`.

### 1. Item-level PDM truth

`LegacyPDMCompatRepository` reads:

- `ItemOptionValues`
- `BaseAttributeValues`
- `ProductAttributeValues`
- `Product.OrderCodeFormatString`
- `ProductRange.OrderCodeFormatString`
- Product/Item identity

### 2. Effective OCFS

The legacy rule is implemented exactly:

```text
Product.OrderCodeFormatString when present
otherwise ProductRange.OrderCodeFormatString
```

### 3. Article reconstruction

`LegacyPDMReductionService` reconstructs an Item as:

```text
Product.Product + OCFS token expansion
```

Each token is resolved through the PDM `OrderCodeFormatKey` -> `OrderCodeValue` relationship. No fixed article length, character position, prefix slicing, or series-specific rule is used.

The result is compared with the real `Item.Item`. Failed reconstruction is reported and is never silently reduced.

### 4. Legacy filter boundary

The compatibility repository can invoke the actual database procedure:

```text
ProductsList(ProductRangeId, LanguageId, AttributeXml)
USProductsList(...)
```

The XML is generated in the same selector shape:

```xml
<attributes>
  <attribute attributeid="..." attributevalueid="..."/>
</attributes>
```

This means the Python layer does not guess or reimplement the hidden stored-procedure filtering semantics when the real PDM database is available.

### 5. Generic candidate representation

The analysis result records:

- ProductId
- Product code
- ProductRangeId
- ItemIds and Item codes
- configurable attribute IDs
- configurable AttributeValue IDs
- the ProductId set returned by the actual legacy filter

This is the correct evidence set for the eventual generic reducer.

## Production reducer status

`EngineeringReductionService` has **not** been replaced. Its existing prefix/length behaviour remains untouched until database-backed validation is completed.

## Final validation still required

The remaining step is execution against the real PDM SQL Server, because the exact body of `ProductsList` / `USProductsList` is database-side and is not contained in the archive repository.

Required acceptance run:

1. Select representative Products from multiple series.
2. Reconstruct every selected Item.
3. Require exact `reconstructed Item == Item.Item`.
4. Send the reconstructed AttributeId/AttributeValueId XML to the actual legacy procedure.
5. Compare returned ProductId sets with the expected legacy selection.
6. Only after that replace the current reduction algorithm.

The 591-row dataset remains a regression fixture, not the source of business rules.
