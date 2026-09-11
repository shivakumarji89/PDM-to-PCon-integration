# Generic PDM reduction investigation

## Status

This document records the business-rule findings before changing the reduction engine.

## Proven legacy model

The archived permutation/filtering code builds valid configurations from PDM metadata. It distinguishes physical values (those with `OrderCodeValue`) from functional values, applies attribute-value exclusions, and checks catalogue membership before constructing the final article code.

The legacy order-code parser uses the existing Product/ProductRange `OrderCodeFormatString` as the template and replaces attribute/option format keys with their selected `OrderCodeValue`. Therefore token position is metadata-driven, not a universal character-position rule.

## Additional proof from AttributeValidator.cs

The archived `DPS/AttributeValidator.cs` confirms that the legacy system treats Product Attribute Values and Item Base Attribute Values as explicit PDM relationships, rather than deriving them from article-string character positions.

The Product Attribute Value list is loaded by joining `ProductAttributeValues -> AttributeValue -> Attribute`, and is ordered by `Attribute.DisplayOrder, AttributeValue.DisplayOrdinal`. The Item Attribute Value list is loaded by joining `BaseAttributeValues -> AttributeValue -> Attribute`, using the same ordering. The UI also reads each value's `OrderCodeValue` when reconstructing the current item representation. `AttributeType == 0` is explicitly treated as a functional attribute value. fileciteturn213file0

This is important for reduction: a value can be part of the product's functional definition without contributing a literal suffix token. Therefore the reducer cannot assume that every configurable property must be represented by characters in the article number. The Product identity itself can carry distinctions that are not encoded as an `OrderCodeValue`.

`AttributeValidator` also verifies compatibility by comparing the selected Product Attribute Value IDs with the Item's Base Attribute Value IDs. It checks that Product and Item belong to the same article/product relationship before allowing values to be copied between them. This reinforces that PDM relationship data, not string similarity, is the authoritative source for configuration membership. fileciteturn213file0

## Reduction consequence

The generic reducer must not use a fixed prefix length, fixed character positions, or series-specific patterns. The base identity must be derived from the PDM Product/ProductRange relationship and the configurable attribute/option selections that distinguish products.

The correct direction for the generic engine is therefore:

`PDM Product + PDM configuration selections -> legacy order-code construction -> full article`

and the reduction operation must work backwards from the full article set to the PDM Product/configuration dimensions that can safely be represented as configurable properties.

A candidate reduction is valid only when it preserves the same PDM selection space: filtering the original articles using the resulting configuration criteria must select exactly the same Product/Item population as the legacy filter logic.

## Current Python repository gap

The current PDM repository already retrieves Product identity, Product Attribute Values, Attribute/AttributeValue metadata, OrderCodeFormatKey, OrderCodeValue, DisplayOrder/DisplayOrdinal, product options, and catalogue-gated option relationships. However, the reduction implementation does not yet have a proven generic reconstruction path that combines the full Product/ProductRange `OrderCodeFormatString` with item-level `BaseAttributeValues` and item-level option values.

Those missing pieces must be resolved before changing `services/engineering/engineering_reduction_service.py`.

## Validation dataset

The supplied 591-row dataset is validation data only. It must not define the algorithm. Different article lengths and multiple configuration families demonstrate why fixed slicing is insufficient.

## Implementation gate

Do not replace the current EngineeringReductionService until the legacy filter selection path and its stored-procedure inputs/outputs are fully mapped. The current service's `code[:base_length]` behavior is known to be an implementation assumption, not established legacy business logic.
