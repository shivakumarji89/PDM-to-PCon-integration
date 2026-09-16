"""Legacy-PDM-compatible reduction discovery engine.

This module deliberately separates the proven legacy PDM filter semantics from
new reduction policy. The legacy filter is represented by ``legacy_match``:
a candidate product matches selected AttributeValueIds when all selected
values belong to the product, the product is in scope, and it is eligible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, List, Mapping, Sequence, Set, Tuple


@dataclass(frozen=True)
class ReductionProduct:
    """Minimal PDM product representation needed by the reduction engine."""

    product_id: int
    product: str
    product_range_id: int
    attribute_value_ids: FrozenSet[int]
    eligible: bool = True


@dataclass(frozen=True)
class ReductionGroup:
    """A proposed generic group validated against legacy filter semantics."""

    product_ids: Tuple[int, ...]
    common_attribute_value_ids: Tuple[int, ...]
    product_range_id: int


@dataclass(frozen=True)
class ReductionAnalysis:
    """Result of reduction discovery."""

    groups: Tuple[ReductionGroup, ...]
    uncovered_product_ids: Tuple[int, ...]


class LegacyPDMReductionEngine:
    """Discover reduction groups using proven legacy PDM filter semantics.

    ``legacy_match`` models the standard ProductsList/USProductsList behavior
    proven during the legacy trace: every selected AttributeValueId must occur
    on the candidate product, and the candidate must satisfy scope/eligibility.
    The grouping strategy itself is new policy and is intentionally kept
    separate from the legacy filter implementation.
    """

    def legacy_match(
        self,
        product: ReductionProduct,
        selected_attribute_value_ids: Iterable[int],
        *,
        product_range_id: int | None = None,
    ) -> bool:
        selected = frozenset(selected_attribute_value_ids)
        if product_range_id is not None and product.product_range_id != product_range_id:
            return False
        if not product.eligible:
            return False
        return selected.issubset(product.attribute_value_ids)

    def _posting_index(
        self, products: Sequence[ReductionProduct]
    ) -> Dict[int, Set[int]]:
        index: Dict[int, Set[int]] = {}
        for product in products:
            if not product.eligible:
                continue
            for attribute_value_id in product.attribute_value_ids:
                index.setdefault(attribute_value_id, set()).add(product.product_id)
        return index

    def _intersect_postings(
        self,
        selected_values: Iterable[int],
        posting_index: Mapping[int, Set[int]],
        candidates: Set[int] | None = None,
    ) -> Set[int]:
        selected = list(dict.fromkeys(selected_values))
        if not selected:
            return set(candidates or ())
        posting_sets = [posting_index.get(value, set()) for value in selected]
        if any(not values for values in posting_sets):
            return set()
        result = set.intersection(*(set(values) for values in posting_sets))
        if candidates is not None:
            result &= candidates
        return result

    def discover_exact_groups(
        self,
        products: Sequence[ReductionProduct],
    ) -> Tuple[ReductionGroup, ...]:
        """Discover exact product-set groups inducible by legacy filters.

        Each product is assigned to the exact set of eligible products that
        would be returned by a filter containing all of its attribute values.
        Groups are validated again through ``legacy_match``. Only groups with
        at least two products are emitted.
        """

        if not products:
            return ()

        by_id = {product.product_id: product for product in products}
        posting_index = self._posting_index(products)
        groups: Dict[Tuple[int, ...], ReductionGroup] = {}

        for product in products:
            if not product.eligible:
                continue
            selected = tuple(sorted(product.attribute_value_ids))
            matched_ids = self._intersect_postings(
                selected,
                posting_index,
                {p.product_id for p in products if p.product_range_id == product.product_range_id and p.eligible},
            )
            if len(matched_ids) < 2:
                continue

            # The SQL filter joins on AttributeValueId, not AttributeId. Re-run
            # the final membership check with the same AND semantics.
            validated = tuple(
                sorted(
                    candidate_id
                    for candidate_id in matched_ids
                    if self.legacy_match(
                        by_id[candidate_id],
                        selected,
                        product_range_id=product.product_range_id,
                    )
                )
            )
            if len(validated) < 2:
                continue

            common = set(selected)
            for candidate_id in validated:
                common &= set(by_id[candidate_id].attribute_value_ids)

            key = validated
            groups[key] = ReductionGroup(
                product_ids=validated,
                common_attribute_value_ids=tuple(sorted(common)),
                product_range_id=product.product_range_id,
            )

        return tuple(
            sorted(
                groups.values(),
                key=lambda group: (-len(group.product_ids), group.product_range_id, group.product_ids),
            )
        )

    def select_non_overlapping_groups(
        self,
        groups: Sequence[ReductionGroup],
    ) -> Tuple[ReductionGroup, ...]:
        """Select deterministic non-overlapping groups.

        This method is intentionally policy, not legacy behavior: the legacy
        database procedures define filtering semantics, not how a new reduced
        catalogue should choose among overlapping candidate groups.
        """

        selected: List[ReductionGroup] = []
        occupied: Set[int] = set()
        for group in sorted(
            groups,
            key=lambda item: (-len(item.product_ids), item.product_range_id, item.product_ids),
        ):
            group_ids = set(group.product_ids)
            if occupied & group_ids:
                continue
            selected.append(group)
            occupied.update(group_ids)
        return tuple(selected)

    def analyze(self, products: Sequence[ReductionProduct]) -> ReductionAnalysis:
        groups = self.discover_exact_groups(products)
        selected = self.select_non_overlapping_groups(groups)
        covered = {product_id for group in selected for product_id in group.product_ids}
        uncovered = tuple(sorted(product.product_id for product in products if product.product_id not in covered))
        return ReductionAnalysis(groups=selected, uncovered_product_ids=uncovered)


def products_from_pdm_rows(rows: Iterable[Mapping[str, object]]) -> Tuple[ReductionProduct, ...]:
    """Build engine inputs from flat PDM rows.

    Expected keys are ``ProductId``, ``Product``, ``ProductRangeId``,
    ``AttributeValueId`` and optional ``Eligible``. Repeated rows for the same
    product are merged into one product record.
    """

    aggregated: Dict[int, Dict[str, object]] = {}
    for row in rows:
        product_id = int(row["ProductId"])
        entry = aggregated.setdefault(
            product_id,
            {
                "product": str(row.get("Product", "")),
                "product_range_id": int(row["ProductRangeId"]),
                "attribute_value_ids": set(),
                "eligible": bool(row.get("Eligible", True)),
            },
        )
        entry["attribute_value_ids"].add(int(row["AttributeValueId"]))
        entry["eligible"] = bool(entry["eligible"]) and bool(row.get("Eligible", True))

    return tuple(
        ReductionProduct(
            product_id=product_id,
            product=str(values["product"]),
            product_range_id=int(values["product_range_id"]),
            attribute_value_ids=frozenset(values["attribute_value_ids"]),
            eligible=bool(values["eligible"]),
        )
        for product_id, values in sorted(aggregated.items())
    )
