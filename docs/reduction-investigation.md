# Generic PDM reduction investigation

## Status

This document records the business-rule findings before changing the reduction engine.

## Proven legacy model

The archived permutation/filtering code builds valid configurations from PDM metadata. It distinguishes physical values (those with `OrderCodeValue`) from functional values, applies attribute-value exclusions, and checks catalogue membership before constructing the final article code.

The legacy order-code parser uses the existing Product/ProductRange `OrderCodeFormatString` as the template and replaces attribute/option format keys with their selected `OrderCodeValue`. Therefore token position is metadata-driven, not a universal character-position rule.

## Reduction consequence

The generic reducer must not use a fixed prefix length, fixed character positions, or series-specific patterns. The base identity must be derived from the PDM Product/ProductRange relationship and the configurable attribute/option selections that distinguish products.

## Validation dataset

The supplied 591-row dataset is validation data only. It must not define the algorithm. Different article lengths and multiple configuration families demonstrate why fixed slicing is insufficient.

## Implementation gate

Do not replace the current EngineeringReductionService until the legacy filter selection path and its stored-procedure inputs/outputs are fully mapped. The current service's `code[:base_length]` behavior is known to be an implementation assumption, not established legacy business logic.
