"""Additional candidate families, for the cases the primary grouping misses.

The primary grouping is and stays
:meth:`~services.engineering.engineering_reduction_service.EngineeringReductionService.classify_by_properties`
- Products of ONE ProductRange whose property STRUCTURE (the set of attributes
they carry) is identical. That rule is right, but it is not the only family
boundary legacy PDM represents, and where the two disagree the primary
candidate is rejected with nothing to fall back on.

The concrete case that motivated this (``docs/pdm-family-boundary.md`` 5):
five Nevi Products are missing their ``Power cutout`` row in
``ProductAttributeValues``, so the primary rule puts them in their own
structure class, while ``dbo.ProductsList`` - a pure containment filter, which
cannot express "lacks attribute A" - keeps them in the main family. The primary
candidate is then rejected by exactly those five Products out of 1,728.

So this service proposes ADDITIONAL groupings from the other evidence legacy
PDM actually offers. Each one is a proposal only:

* nothing here decides a reduction;
* every proposal goes through the unchanged
  :class:`~services.engineering.pdm_family_reduction_service.PDMFamilyReductionService`
  boundary and must be returned EXACTLY by ``ProductsList``;
* a proposal from a partly loaded ProductRange stays ``unresolved`` like any
  other.

A wrong proposal therefore costs a round trip and nothing else - it can never
be applied. That is what makes it safe to propose from curated data.

**Deliberately NOT implemented:** a "closure" strategy that asks
``ProductsList`` what it would return and proposes that back as the candidate.
It would be self-fulfilling - the closure is idempotent, so it always
validates - and it would turn the boundary from a check into a rubber stamp.
The strategies below all derive a grouping from independent evidence and then
submit it to be judged.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence
from uuid import uuid4

from repositories.legacy_pdm_compat_repository import LegacyPDMCompatRepository
from services.base_service import BaseService
from services.engineering.pdm_family_reduction_service import (
    PDMFamilyReductionService,
)

#: The primary grouping - the property-structure classes the reduction engine
#: derives. Not a strategy of this service; named here so precedence has one
#: vocabulary, and because the primary grouping always outranks a fallback.
PRIMARY_STRATEGY = "primary"

STRATEGY_BASE_PREFIX = "base-prefix"
STRATEGY_FUNCTIONAL_SIGNATURE = "functional-signature"
STRATEGY_HANDBOOK_GROUP = "handbook-group"

#: Strategy identifiers, in the order they are offered to the boundary. The
#: order is also the PRECEDENCE used when two validated candidates cover the
#: same article: the primary grouping first, then these in turn. It is a
#: declared order, not a score.
STRATEGY_ORDER: tuple[str, ...] = (
    STRATEGY_BASE_PREFIX,
    STRATEGY_FUNCTIONAL_SIGNATURE,
    STRATEGY_HANDBOOK_GROUP,
)


@dataclass(frozen=True)
class StrategyCandidate:
    """One proposed grouping: these ProductIds may share one base article."""

    strategy: str = ""
    product_range: str = ""
    product_ids: tuple[str, ...] = ()
    #: Why this strategy proposed this grouping, for the verdict report.
    reason: str = ""
    id: str = field(default_factory=lambda: uuid4().hex)


class CandidateStrategyService(BaseService):
    """Propose additional candidate families from legacy PDM evidence.

    Read-only: it reads PDM and the snapshot, and returns proposals. It never
    writes, never validates, and never reduces.
    """

    def __init__(self, context) -> None:
        super().__init__(context)
        self.repository = LegacyPDMCompatRepository(context)

    # -- entry point -------------------------------------------------------
    def propose(
        self,
        snapshot,
        primary_product_id_sets: Iterable[Sequence[str]] = (),
        primary_bases: Iterable[tuple[str, str]] = (),
        connection: Any = None,
    ) -> tuple[StrategyCandidate, ...]:
        """Additional candidates for ``snapshot``, already merged and deduped.

        ``primary_product_id_sets`` are the ProductId sets the primary grouping
        already produced, and ``primary_bases`` the ``(base code, range name)``
        pairs it derived. Both are inputs, not things this service may change:
        they are used to seed the structure strategy and to drop any proposal
        that would add nothing.

        A proposal is dropped when it is a SUBSET of a primary candidate. Such
        a proposal can only ever re-describe Products the primary grouping
        already covers, and the primary grouping outranks it, so submitting it
        would spend a ``ProductsList`` round trip on a verdict that could not
        change an outcome. Only a proposal that reaches Products the primary
        candidate does not have can rescue one.
        """
        if snapshot is None:
            return ()
        loaded = sorted({
            str(getattr(a, "product_id", "") or "")
            for a in getattr(snapshot, "articles", []) or []
            if getattr(a, "product_id", None)
        })
        if not loaded:
            return ()

        own_connection = connection is None
        if own_connection:
            connection = self.repository.get_connection()
        try:
            population = self.repository.fetch_range_population_for_products(
                loaded, connection=connection
            )
            proposals: list[StrategyCandidate] = []
            proposals.extend(
                self._by_base_prefix(population, primary_bases, loaded)
            )
            proposals.extend(
                self._by_functional_signature(population, loaded, connection)
            )
            proposals.extend(
                self._by_handbook_group(population, loaded, connection)
            )
        finally:
            if own_connection:
                connection.close()

        return self._merge(proposals, primary_product_id_sets)

    # -- strategies --------------------------------------------------------
    @staticmethod
    def _by_base_prefix(
        population: Iterable[Any],
        primary_bases: Iterable[tuple[str, str]],
        loaded: Sequence[str],
    ) -> list[StrategyCandidate]:
        """Strategy ``base-prefix`` - Product/article STRUCTURE.

        Every eligible Product of a ProductRange whose product code starts with
        a base the primary grouping derived.

        Evidence (``docs/pdm-family-boundary.md`` 1.3): PDM's own maintainers
        record a family's base in ``HandbookProducts.ProductListEntry`` as a
        masked product code, and across the 6,841 multi-product masked entries
        in the database that mask's first ``_`` equals the members' common code
        prefix in 72.2% of cases and is never TIGHTER than it in all but 18. A
        shared code prefix is therefore the structural form a legacy base
        actually takes, measured rather than assumed.

        This is the strategy that reaches Products the structure rule split off
        for a missing attribute row: their codes still carry the family's base.
        """
        # (range id, base) -> range name, so one proposal per distinct base.
        wanted: dict[tuple[str, str], str] = {}
        name_of_range: dict[str, str] = {}
        code_of_product: dict[str, str] = {}
        by_range: dict[str, list[str]] = defaultdict(list)
        for row in population:
            product_id = str(getattr(row, "ProductId", "") or "")
            range_id = str(getattr(row, "ProductRangeId", "") or "")
            name_of_range[range_id] = (
                getattr(row, "RangeName", "") or ""
            ).strip()
            code_of_product[product_id] = (getattr(row, "Product", "") or "")
            by_range[range_id].append(product_id)

        loaded_set = set(loaded)
        for base, range_name in primary_bases:
            base = (base or "").strip()
            if not base:
                continue
            # Resolve the range by NAME, the only range key a snapshot holds.
            for range_id, name in name_of_range.items():
                if name == (range_name or "").strip():
                    wanted[(range_id, base)] = name

        proposals: list[StrategyCandidate] = []
        for (range_id, base), range_name in sorted(wanted.items()):
            members = sorted(
                product_id for product_id in by_range.get(range_id, ())
                if code_of_product.get(product_id, "").startswith(base)
                and product_id in loaded_set
            )
            if len(members) < 2:
                continue
            proposals.append(
                StrategyCandidate(
                    strategy=STRATEGY_BASE_PREFIX,
                    product_range=range_name,
                    product_ids=tuple(members),
                    reason=(
                        f"Every eligible Product of ProductRange {range_id} "
                        f"whose code starts with the derived base {base!r} "
                        f"({len(members)} Products)."
                    ),
                )
            )
        return proposals

    def _by_functional_signature(
        self,
        population: Iterable[Any],
        loaded: Sequence[str],
        connection: Any,
    ) -> list[StrategyCandidate]:
        """Strategy ``functional-signature`` - PDM property values.

        Products of one ProductRange whose FUNCTIONAL (non-order-code)
        ``ProductAttributeValues`` set is identical.

        This is the grouping rule the compatibility layer already used for
        cross-range diagnostics (``scripts/validate_pdm_family_reduction.py``
        ``--discover``), promoted here so production can use it. It is the
        value-level counterpart of the primary rule, which compares only the
        attribute NAMES a Product carries: two Products with an identical
        functional value set are indistinguishable to ``ProductsList``, so if
        a grouping of them is not closed nothing is.

        Functionality is decided by
        :meth:`PDMFamilyReductionService.is_functional` - the same four legacy
        tests the selector itself is built from, not a second opinion.
        """
        range_of: dict[str, str] = {}
        name_of_range: dict[str, str] = {}
        for row in population:
            product_id = str(getattr(row, "ProductId", "") or "")
            range_id = str(getattr(row, "ProductRangeId", "") or "")
            range_of[product_id] = range_id
            name_of_range[range_id] = (
                getattr(row, "RangeName", "") or ""
            ).strip()

        loaded_set = {str(p) for p in loaded}
        rows = self.repository.fetch_products_filter_attributes(
            sorted(loaded_set), connection=connection
        )
        functional: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            if PDMFamilyReductionService.is_functional(row):
                functional[str(getattr(row, "ProductId", "") or "")].add(
                    str(getattr(row, "AttributeValueId", "") or "")
                )

        by_signature: dict[tuple[str, frozenset], list[str]] = defaultdict(list)
        for product_id, values in functional.items():
            if not values or product_id not in loaded_set:
                continue
            by_signature[(range_of.get(product_id, ""), frozenset(values))].append(
                product_id
            )

        proposals: list[StrategyCandidate] = []
        for (range_id, signature), members in sorted(
            by_signature.items(), key=lambda kv: sorted(kv[1])
        ):
            if len(members) < 2:
                continue
            proposals.append(
                StrategyCandidate(
                    strategy=STRATEGY_FUNCTIONAL_SIGNATURE,
                    product_range=name_of_range.get(range_id, ""),
                    product_ids=tuple(sorted(members)),
                    reason=(
                        f"{len(members)} Products of ProductRange {range_id} "
                        f"share an identical functional AttributeValue set "
                        f"({len(signature)} values)."
                    ),
                )
            )
        return proposals

    def _by_handbook_group(
        self,
        population: Iterable[Any],
        loaded: Sequence[str],
        connection: Any,
    ) -> list[StrategyCandidate]:
        """Strategy ``handbook-group`` - the curated pricebook grouping.

        Products a handbook publishes under one ``ProductListEntry`` base mask
        within one ProductGroup. This is the only place legacy PDM records a
        human judgement of "one family, one base article"
        (``docs/pdm-family-boundary.md`` 1.3).

        It is hand-authored and demonstrably inconsistent, so it is offered
        last and, like everything else here, only as a proposal: a handbook
        group that is not closed under ``ProductsList`` is simply rejected.
        Groups spanning more than one ProductRange are dropped outright, since
        the boundary cannot answer across ranges.
        """
        range_of: dict[str, str] = {}
        name_of_range: dict[str, str] = {}
        for row in population:
            product_id = str(getattr(row, "ProductId", "") or "")
            range_id = str(getattr(row, "ProductRangeId", "") or "")
            range_of[product_id] = range_id
            name_of_range[range_id] = (
                getattr(row, "RangeName", "") or ""
            ).strip()

        loaded_set = {str(p) for p in loaded}
        rows = self.repository.fetch_handbook_groups(
            sorted(loaded_set), connection=connection
        )
        groups: dict[tuple, list[str]] = defaultdict(list)
        labels: dict[tuple, str] = {}
        for row in rows:
            product_id = str(getattr(row, "ProductId", "") or "")
            if product_id not in loaded_set:
                continue
            key = (
                str(getattr(row, "HandbookId", "") or ""),
                str(getattr(row, "ProductGroupId", "") or ""),
                (getattr(row, "ProductListEntry", "") or "").strip(),
            )
            groups[key].append(product_id)
            labels[key] = (getattr(row, "GroupName", "") or "").strip()

        proposals: list[StrategyCandidate] = []
        for key, members in sorted(groups.items()):
            members = sorted(set(members))
            if len(members) < 2:
                continue
            ranges = {range_of.get(m, "") for m in members}
            if len(ranges) != 1:
                continue  # ProductsList cannot answer across ranges
            range_id = next(iter(ranges))
            handbook_id, group_id, mask = key
            proposals.append(
                StrategyCandidate(
                    strategy=STRATEGY_HANDBOOK_GROUP,
                    product_range=name_of_range.get(range_id, ""),
                    product_ids=tuple(members),
                    reason=(
                        f"Handbook {handbook_id} group {group_id} "
                        f"({labels.get(key, '')!r}) publishes these "
                        f"{len(members)} Products under base mask {mask!r}."
                    ),
                )
            )
        return proposals

    # -- merge / dedupe ----------------------------------------------------
    @staticmethod
    def _merge(
        proposals: Iterable[StrategyCandidate],
        primary_product_id_sets: Iterable[Sequence[str]],
    ) -> tuple[StrategyCandidate, ...]:
        """Drop duplicates and proposals that cannot change an outcome.

        Two proposals naming the same ProductIds are one proposal; the earlier
        strategy in :data:`STRATEGY_ORDER` keeps it. A proposal that is a
        subset of a primary candidate is dropped, because the primary grouping
        outranks it for every article it covers.
        """
        primary = [frozenset(str(p) for p in ids) for ids in primary_product_id_sets]
        seen: set[frozenset] = set()
        kept: list[StrategyCandidate] = []
        rank = {name: index for index, name in enumerate(STRATEGY_ORDER)}
        for proposal in sorted(
            proposals,
            key=lambda c: (rank.get(c.strategy, len(rank)), sorted(c.product_ids)),
        ):
            ids = frozenset(proposal.product_ids)
            if len(ids) < 2 or ids in seen:
                continue
            if any(ids <= existing for existing in primary):
                continue
            seen.add(ids)
            kept.append(proposal)
        return tuple(kept)
