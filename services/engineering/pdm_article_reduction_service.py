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
        """Discover exact prefix/filter groups from an already loaded snapshot.

        A group is accepted only when its product-code prefix can be reproduced
        exactly by a conjunction of functional PDM AttributeValueIds.  Functional
        values are identified by the legacy PDM rule: ``AttributeType == 0`` and
        an empty ``OrderCodeValue``.  Dimension/order-code values are therefore
        excluded from reduction and remain part of the existing article tail.

        No PDM query is performed here.  ``snapshot.product_property_value_ids``
        is the product-level PAV source already populated by LoadingEngine.
        """
        if snapshot is None or not snapshot.articles:
            return PDMReductionResult()

        value_is_functional = self._functional_value_ids(snapshot)
        product_values = self._product_functional_values(snapshot, value_is_functional)
        product_codes = self._product_pre_dot_codes(snapshot)
        range_by_product = {
            str(pid): str(name or "")
            for pid, name in (getattr(snapshot, "product_range", {}) or {}).items()
        }

        products = {
            pid
            for pid in product_codes
            if product_values.get(pid)
        }
        if len(products) < 2:
            return PDMReductionResult(uncovered_product_ids=tuple(sorted(products)))

        postings = self._posting_index(product_values)
        prefix_groups = self._prefix_groups(product_codes, products)

        candidates: list[PDMReductionGroup] = []
        for prefix, prefix_products in prefix_groups:
            if len(prefix_products) < 2:
                continue
            ranges = {range_by_product.get(pid, "") for pid in prefix_products}
            # A legacy ProductsList filter is range-scoped.  A prefix spanning
            # multiple known ranges cannot be validated as one legacy group.
            if len(ranges) != 1:
                continue
            range_name = next(iter(ranges))

            common = self._common_values(prefix_products, product_values)
            selected = self._find_exact_filter(
                prefix_products,
                products,
                common,
                postings,
                range_by_product,
                range_name,
            )
            if selected is None:
                continue
            candidates.append(
                PDMReductionGroup(
                    base_article=prefix,
                    product_ids=tuple(sorted(prefix_products)),
                    filter_attribute_value_ids=tuple(sorted(selected)),
                    product_range=range_name,
                )
            )

        # Prefer the broadest validated families first.  This is a reduction
        # policy, not a claim about legacy PDM behavior: legacy PDM only defines
        # the filter result, not how a new reduced catalogue chooses overlapping
        # families.
        candidates.sort(
            key=lambda group: (
                -len(group.product_ids),
                len(group.base_article),
                group.product_range,
                group.base_article,
            )
        )
        selected_groups: list[PDMReductionGroup] = []
        covered: set[str] = set()
        for group in candidates:
            ids = set(group.product_ids)
            if covered & ids:
                continue
            selected_groups.append(group)
            covered.update(ids)

        uncovered = tuple(sorted(products - covered))
        return PDMReductionResult(
            groups=tuple(selected_groups),
            uncovered_product_ids=uncovered,
        )

    def apply(self, snapshot: Snapshot | None) -> PDMReductionResult:
        """Apply validated reduced pre-dot articles to engineering members.

        Only ``MemberArticle.reduced_article`` is changed.  The source
        ``Article.code`` and its post-dot configuration are never changed.
        Existing reductions are cleared first so the operation is idempotent.
        """
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
        """Return AttributeValue ids that are functional for reduction."""
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
        cls,
        snapshot: Snapshot,
        functional_value_ids: set[str],
    ) -> dict[str, frozenset[str]]:
        source = getattr(snapshot, "product_property_value_ids", {}) or {}
        return {
            str(product_id): frozenset(
                str(value_id)
                for value_id in value_ids
                if str(value_id) in functional_value_ids
            )
            for product_id, value_ids in source.items()
        }

    @staticmethod
    def _product_pre_dot_codes(snapshot: Snapshot) -> dict[str, str]:
        """Return one pre-dot Product/Item code per product.

        The source article is the already loaded Item article.  Only its prefix
        before the first ``.`` is read; everything after the dot is ignored.
        """
        result: dict[str, str] = {}
        for article in snapshot.articles:
            product_id = str(article.product_id or "")
            if not product_id or product_id in result:
                continue
            code = (article.code or "").strip()
            if not code:
                continue
            result[product_id] = code.split(".", 1)[0]
        return result

    @staticmethod
    def _posting_index(
        product_values: dict[str, frozenset[str]],
    ) -> dict[str, set[str]]:
        postings: dict[str, set[str]] = {}
        for product_id, values in product_values.items():
            for value_id in values:
                postings.setdefault(value_id, set()).add(product_id)
        return postings

    @staticmethod
    def _prefix_groups(
        product_codes: dict[str, str],
        products: set[str],
    ) -> list[tuple[str, set[str]]]:
        groups: dict[str, set[str]] = {}
        for product_id in products:
            code = product_codes.get(product_id, "")
            # A full product code is not a reduction.  We need a shorter common
            # pre-dot base so at least one variable/configuration character is
            # actually removed.
            for length in range(1, len(code)):
                prefix = code[:length]
                groups.setdefault(prefix, set()).add(product_id)
        return [
            (prefix, ids)
            for prefix, ids in groups.items()
            if len(ids) >= 2
        ]

    @staticmethod
    def _common_values(
        product_ids: Iterable[str],
        product_values: dict[str, frozenset[str]],
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
        cls,
        target: set[str],
        products: set[str],
        common_values: set[str],
        postings: dict[str, set[str]],
        range_by_product: dict[str, str],
        range_name: str,
    ) -> set[str] | None:
        """Find a functional value conjunction whose result is exactly target.

        Start with the eligible products in the target's range.  Every candidate
        value is known to occur on every target product, so intersecting its
        posting set can never remove a target member.  If an exact legacy filter
        exists, repeatedly adding any common value that shrinks the current set
        will eventually reach the target.
        """
        scoped = {
            product_id
            for product_id in products
            if range_by_product.get(product_id, "") == range_name
        }
        current = set(scoped)
        selected: set[str] = set()
        # Smaller postings first usually reaches the target with fewer values and
        # keeps the generated filter compact.  The result is deterministic.
        ordered_values = sorted(
            common_values,
            key=lambda value_id: (len(postings.get(value_id, set())), value_id),
        )
        while current != target:
            best_value = None
            best_next = current
            for value_id in ordered_values:
                if value_id in selected:
                    continue
                next_set = current & postings.get(value_id, set())
                if target.issubset(next_set) and len(next_set) < len(best_next):
                    best_value = value_id
                    best_next = next_set
            if best_value is None:
                return None
            selected.add(best_value)
            current = best_next
        return selected
