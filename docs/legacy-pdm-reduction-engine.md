# Legacy PDM Reduction Engine

This document describes the isolated reduction-discovery engine on `feature/reduction-engine-2026-09-16`.

## Purpose

The implementation separates two concerns:

1. **Legacy PDM filter semantics**: a candidate Product matches selected AttributeValueIds when every selected value is present on that Product, subject to scope and eligibility.
2. **New reduction policy**: discovery and deterministic selection of Product groups that can share a reduced representation.

The second part is new policy; it is not presented as a recovered legacy Product-to-base algorithm.

## Proven filter model

For standard `ProductsList` behavior, selected AttributeValueIds are matched to `ProductAttributeValues` and a Product is returned only when all selected values are present. Product range and legacy eligibility are applied.

For `USProductsList`, the same all-selected-value mechanism is applied to `USItemAttributeValues`, with ProductCategory scope.

`legacy_match()` implements this common AND-membership rule.

## Reduction discovery

`discover_exact_groups()` builds value-to-product postings, intersects them for a Product's complete AttributeValue set, revalidates the candidate set through `legacy_match()`, and records common AttributeValueIds. Groups with fewer than two Products are discarded.

## Group selection

The legacy database procedures define filtering semantics, not how a new reduced catalogue should choose among overlapping groups. `select_non_overlapping_groups()` is therefore explicit new policy: larger groups are selected first, deterministically, and overlapping groups are skipped.

## Scope

The engine does not replace the existing production `EngineeringReductionService`. It is intended for read-only discovery and validation until the groups are validated against the real PDM data and business requirements.
