"""PDM-driven article reduction.

This service is the production-side implementation of the reduction model proved
against the legacy PDM ProductSelector filter.  It intentionally works from the
already loaded :class:`Snapshot` instead of opening another PDM connection.

The algorithm has two separate concerns:

1. **Legacy filter semantics** - a candidate filter is the intersection of the
   products carrying its selected AttributeValueIds, scoped to the same product
   range.  This is the same AND-by-AttributeValueId rule used by ProductsList.
2. **Reduction policy** - a product-code prefix is accepted as a reduction group
   only when a functional-only PDM filter can reproduce exactly that prefix's
   product set.  The prefix becomes the reduced pre-dot article.

Only the pre-dot portion of an article is considered here.  The existing
post-dot article/configuration pipeline is deliberately untouched.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from models.snapshot import Snapshot
from services.base_service import BaseService


@dataclass(frozen=True)
class PDMReductionGroup:
    """One validated reduced pre-dot article family."""

    base_article: str
    product_ids: tuple[str, ...]
    filter_attribute_value_ids: tuple[str, ...]
    product_range: str = ""


@dataclass(frozen=True)
class PDMReductionResult:
    """Read-only result of PDM-driven reduction discovery."""

    groups: tuple[PDMReductionGroup, ...] = ()
    uncovered_product_ids: tuple[str, ...] = ()


class PDMArticleReductionService(BaseService):
    """Discover and apply PDM-validated pre-dot article reductions."""

    def discover(self, snapshot: Snapshot | None) -> PDMReductionResult:
        """Discover exact prefix/filter groups from an already loaded snapshot."""
        if snapshot is None or not snapshot.articles:
            return PDMReductionResult()

        value_is_functional = self._functional_value_ids(snapshot)
        product_values = self._product_functional_values(snapshot, value_is_functional)
        product_codes = self._product_pre_dot_codes(snapshot)
        range_by_product = {
            str(pid): str(name or "")
            for pid, name in (getattr(snapshot, "product_range", {}) or {}).items()
        }

        products = {pid for pid in product_codes if product_values.get(pid)}
        if len(products) < 2:
            return PDMReductionResult(uncovered_product_ids=tuple(sorted(products)))

        candidates: list[PDMReductionGroup] = []
        for prefix, prefix_products in self._prefix_groups(product_codes, products):
            ranges = {range_by_product.get(pid, "") for pid in prefix_products}
            if len(prefix_products) < 2 or len(ranges) != 1:
                continue
            range_name = next(iter(ranges))
            common = self._common_values(prefix_products, product_values)
            selected = self._find_exact_filter(
                prefix_products, products, common, product_values,
                range_by_product, range_name,
            )
            if selected is not None:
                candidates.append(PDMReductionGroup(
                    base_article=prefix,
                    product_ids=tuple(sorted(prefix_products)),
                    filter_attribute_value_ids=tuple(sorted(selected)),
                    product_range=range_name,
                ))

        # If several prefixes describe the same ProductId set, keep the most
        # specific (longest) prefix. This prevents an ancestor such as "AB"
        # from hiding the more useful exact family "ABC". Different product sets
        # remain separate and are resolved by specificity before overlap.
        by_product_set: dict[tuple[str, ...], PDMReductionGroup] = {}
        for group in candidates:
            key = group.product_ids
            previous = by_product_set.get(key)
            if previous is None or len(group.base_article) > len(previous.base_article):
                by_product_set[key] = group
        candidates = list(by_product_set.values())

        # More-specific validated families get first claim on their products.
        # Parent families can still be used when they do not overlap a selected
        # child family. Legacy PDM defines membership, not this reduction hierarchy.
        candidates.sort(key=lambda group: (
            -len(group.base_article),
            -len(group.product_ids),
            group.product_range,
            group.base_article,
        ))
        selected_groups: list[PDMReductionGroup] = []
        covered: set[str] = set()
        for group in candidates:
            ids = set(group.product_ids)
            if covered & ids:
                continue
            selected_groups.append(group)
            covered.update(ids)

        return PDMReductionResult(
            groups=tuple(selected_groups),
            uncovered_product_ids=tuple(sorted(products - covered)),
        )

    def apply(self, snapshot: Snapshot | None) -> PDMReductionResult:
        """Apply validated reduced pre-dot articles to engineering members."""
        result = self.discover(snapshot)
        if snapshot is None or snapshot.engineering is None:
            return result

        base_by_product = {
            pid: group.base_article
            for group in result.groups
            for pid in group.product_ids
        }
        article_product = {
            str(article.id): str(article.product_id or "")
            for article in snapshot.articles
        }
        for family in snapshot.engineering.families:
            for member in family.members:
                product_id = article_product.get(str(member.article_id), "")
                member.reduced_article = base_by_product.get(product_id, "")
        return result

    @staticmethod
    def _functional_value_ids(snapshot: Snapshot) -> set[str]:
        result: set[str] = set()
        for prop in snapshot.properties:
            if prop.attribute_type != 0:
                continue
            for value in prop.values:
                if not (value.code or "").strip():
                    result.add(str(value.id))
        return result

    @classmethod
    def _product_functional_values(
        cls, snapshot: Snapshot, functional_value_ids: set[str]
    ) -> dict[str, frozenset[str]]:
        source = getattr(snapshot, "product_property_value_ids", {}) or {}
        return {
            str(product_id): frozenset(
                str(value_id) for value_id in value_ids
                if str(value_id) in functional_value_ids
            )
            for product_id, value_ids in source.items()
        }

    @staticmethod
    def _product_pre_dot_codes(snapshot: Snapshot) -> dict[str, str]:
        result: dict[str, str] = {}
        for article in snapshot.articles:
            product_id = str(article.product_id or "")
            if not product_id or product_id in result:
                continue
            code = (article.code or "").strip()
            if code:
                result[product_id] = code.split(".", 1)[0]
        return result

    @staticmethod
    def _prefix_groups(product_codes: dict[str, str], products: set[str]):
        groups: dict[str, set[str]] = {}
        for product_id in products:
            code = product_codes.get(product_id, "")
            for length in range(1, len(code)):
                groups.setdefault(code[:length], set()).add(product_id)
        return [(prefix, ids) for prefix, ids in groups.items() if len(ids) >= 2]

    @staticmethod
    def _common_values(
        product_ids: Iterable[str], product_values: dict[str, frozenset[str]]
    ) -> set[str]:
        ids = list(product_ids)
        if not ids:
            return set()
        common = set(product_values.get(ids[0], ()))
        for product_id in ids[1:]:
            common &= set(product_values.get(product_id, ()))
            if not common:
                break
        return common

    @classmethod
    def _find_exact_filter(
        cls, target: set[str], products: set[str], common_values: set[str],
        product_values: dict[str, frozenset[str]],
        range_by_product: dict[str, str], range_name: str,
    ) -> set[str] | None:
        # Every valid selected value is common to the target. Therefore the full
        # target intersection is the strongest possible conjunction. If it still
        # returns a superset, no subset can be exact.
        scoped = {
            product_id for product_id in products
            if range_by_product.get(product_id, "") == range_name
        }
        current = set(scoped)
        for value_id in common_values:
            current = {
                product_id for product_id in current
                if value_id in product_values.get(product_id, ())
            }
        return set(common_values) if current == target else None
