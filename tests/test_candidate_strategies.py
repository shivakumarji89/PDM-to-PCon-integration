"""Fallback candidate strategies, their merge rule, and how a winner is picked.

The primary grouping (property structure within one ProductRange) stays the
reduction engine's own. These tests cover the additions: proposing extra
groupings from the other legacy PDM evidence, merging them, and resolving an
article that several confirmed candidates cover.

Nothing here talks to a database - the PDM rows each strategy reads are
scripted, so the RULES are under test rather than one dataset.
"""
import unittest
from types import SimpleNamespace

from services.engineering.candidate_strategy_service import (
    PRIMARY_STRATEGY,
    STRATEGY_BASE_PREFIX,
    STRATEGY_FUNCTIONAL_SIGNATURE,
    STRATEGY_HANDBOOK_GROUP,
    CandidateStrategyService,
    StrategyCandidate,
)
from models.article import Article
from models.engineering import Engineering
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering.engineering_reduction_service import (
    ArticleSetValidation,
    EngineeringReductionService,
)
from services.engineering.pdm_family_reduction_service import FamilyValidation

RANGE_ID = "6511"
RANGE_NAME = "Desks"


def population(*products):
    """``(product id, code)`` pairs as eligible-population rows."""
    return [
        SimpleNamespace(
            ProductId=product_id,
            ProductRangeId=RANGE_ID,
            RangeName=RANGE_NAME,
            Product=code,
        )
        for product_id, code in products
    ]


def attribute_row(product_id, value_id, functional=True):
    return SimpleNamespace(
        ProductId=product_id,
        AttributeId="10",
        AttributeValueId=value_id,
        AttributeType=0 if functional else 1,
        OrderCodeFormatKey=None if functional else "{WD}",
        OrderCodeValue="" if functional else "12",
        ModelSuffix=None,
    )


def handbook_row(product_id, group_id, mask, range_id=RANGE_ID):
    return SimpleNamespace(
        HandbookId="956",
        ProductGroupId=group_id,
        GroupName="Desks>Standard",
        ProductListEntry=mask,
        ProductId=product_id,
        ProductRangeId=range_id,
    )


class FakeRepository:
    def __init__(self, pop=(), attributes=(), handbook=()):
        self._pop, self._attributes, self._handbook = pop, attributes, handbook
        self.connections = []

    def get_connection(self):
        connection = SimpleNamespace(closed=False)
        connection.close = lambda: setattr(connection, "closed", True)
        self.connections.append(connection)
        return connection

    def fetch_range_population_for_products(self, product_ids, connection=None):
        return list(self._pop)

    def fetch_products_filter_attributes(self, product_ids, connection=None):
        return list(self._attributes)

    def fetch_handbook_groups(self, product_ids, connection=None):
        return list(self._handbook)


def build_service(repository):
    service = CandidateStrategyService.__new__(CandidateStrategyService)
    service.context = SimpleNamespace()
    service.repository = repository
    return service


def snapshot_of(*product_ids):
    return SimpleNamespace(
        articles=[
            SimpleNamespace(id=f"a{p}", product_id=p, code=f"C{p}")
            for p in product_ids
        ]
    )


class BasePrefixStrategyTests(unittest.TestCase):
    """Strategy C - every eligible Product of the range whose code carries the
    base the primary grouping derived."""

    def test_reaches_the_products_the_structure_rule_split_off(self):
        repository = FakeRepository(
            pop=population(
                ("1", "DWE36AC4Y."), ("2", "DWE36AT4Y."), ("3", "DWE36AR4Y."),
                ("9", "DWE36RT4Y."),          # a different base
            )
        )
        service = build_service(repository)

        proposals = service.propose(
            snapshot_of("1", "2", "3", "9"),
            primary_product_id_sets=[("1", "2")],   # 3 was split off
            primary_bases=[("DWE36A", RANGE_NAME)],
        )

        prefix = [p for p in proposals if p.strategy == STRATEGY_BASE_PREFIX]
        self.assertEqual(len(prefix), 1)
        # 3 joins 1 and 2 - its code carries the same base; 9 does not.
        self.assertEqual(prefix[0].product_ids, ("1", "2", "3"))
        self.assertEqual(prefix[0].product_range, RANGE_NAME)

    def test_only_products_the_session_loaded_are_proposed(self):
        repository = FakeRepository(
            pop=population(("1", "DWE36AC."), ("2", "DWE36AT."), ("3", "DWE36AR."))
        )
        service = build_service(repository)

        proposals = service.propose(
            snapshot_of("1", "2"),               # 3 exists in PDM, not loaded
            primary_product_id_sets=[("1",)],
            primary_bases=[("DWE36A", RANGE_NAME)],
        )

        self.assertEqual(
            [p.product_ids for p in proposals if p.strategy == STRATEGY_BASE_PREFIX],
            [("1", "2")],
        )

    def test_a_base_from_another_range_proposes_nothing(self):
        repository = FakeRepository(pop=population(("1", "DWE36AC."), ("2", "DWE36AT.")))
        service = build_service(repository)

        proposals = service.propose(
            snapshot_of("1", "2"),
            primary_product_id_sets=[("1",)],
            primary_bases=[("DWE36A", "Some Other Range")],
        )

        self.assertEqual(
            [p for p in proposals if p.strategy == STRATEGY_BASE_PREFIX], []
        )

    def test_connection_is_opened_once_and_released(self):
        repository = FakeRepository(pop=population(("1", "A."), ("2", "A.")))
        service = build_service(repository)

        service.propose(snapshot_of("1", "2"), [("1",)], [("A", RANGE_NAME)])

        self.assertEqual(len(repository.connections), 1)
        self.assertTrue(repository.connections[0].closed)


class FunctionalSignatureStrategyTests(unittest.TestCase):
    """Strategy B - Products whose functional AttributeValue set is identical."""

    def test_identical_functional_values_are_proposed_together(self):
        repository = FakeRepository(
            pop=population(("1", "A1."), ("2", "A2."), ("3", "B1.")),
            attributes=[
                attribute_row("1", "100"), attribute_row("2", "100"),
                attribute_row("3", "200"),
            ],
        )
        service = build_service(repository)

        proposals = [
            p for p in service.propose(snapshot_of("1", "2", "3"))
            if p.strategy == STRATEGY_FUNCTIONAL_SIGNATURE
        ]

        self.assertEqual([p.product_ids for p in proposals], [("1", "2")])

    def test_order_code_values_never_define_the_signature(self):
        # 1 and 2 agree only on an ORDER-CODE value, which drives the after-dot
        # suffix and is never family identity.
        repository = FakeRepository(
            pop=population(("1", "A1."), ("2", "A2.")),
            attributes=[
                attribute_row("1", "100"), attribute_row("2", "200"),
                attribute_row("1", "900", functional=False),
                attribute_row("2", "900", functional=False),
            ],
        )
        service = build_service(repository)

        self.assertEqual(
            [p for p in service.propose(snapshot_of("1", "2"))
             if p.strategy == STRATEGY_FUNCTIONAL_SIGNATURE],
            [],
        )


class HandbookStrategyTests(unittest.TestCase):
    """Strategy D - the curated pricebook grouping, proposed but never trusted."""

    def test_one_handbook_group_under_one_mask_is_proposed(self):
        repository = FakeRepository(
            pop=population(("1", "A1."), ("2", "A2."), ("3", "A3.")),
            handbook=[
                handbook_row("1", "57", "A_."), handbook_row("2", "57", "A_."),
                handbook_row("3", "58", "A_."),      # a different group
            ],
        )
        service = build_service(repository)

        proposals = [
            p for p in service.propose(snapshot_of("1", "2", "3"))
            if p.strategy == STRATEGY_HANDBOOK_GROUP
        ]

        self.assertEqual([p.product_ids for p in proposals], [("1", "2")])
        self.assertIn("956", proposals[0].reason)

    def test_a_group_spanning_ranges_is_dropped(self):
        # ProductsList answers within one ProductRange, so it could not judge it.
        repository = FakeRepository(
            pop=[
                SimpleNamespace(ProductId="1", ProductRangeId="6511",
                                RangeName="A", Product="A1."),
                SimpleNamespace(ProductId="2", ProductRangeId="6512",
                                RangeName="B", Product="B1."),
            ],
            handbook=[handbook_row("1", "57", "A_."), handbook_row("2", "57", "A_.")],
        )
        service = build_service(repository)

        self.assertEqual(
            [p for p in service.propose(snapshot_of("1", "2"))
             if p.strategy == STRATEGY_HANDBOOK_GROUP],
            [],
        )


class MergeTests(unittest.TestCase):
    """Merging and de-duplicating proposals before any of them is submitted."""

    def test_the_same_product_set_is_proposed_once(self):
        merged = CandidateStrategyService._merge(
            [
                StrategyCandidate(strategy=STRATEGY_HANDBOOK_GROUP, product_ids=("1", "2")),
                StrategyCandidate(strategy=STRATEGY_BASE_PREFIX, product_ids=("1", "2")),
            ],
            primary_product_id_sets=[],
        )

        self.assertEqual(len(merged), 1)
        # The earlier strategy in the declared order keeps it.
        self.assertEqual(merged[0].strategy, STRATEGY_BASE_PREFIX)

    def test_a_subset_of_a_primary_candidate_is_dropped(self):
        merged = CandidateStrategyService._merge(
            [StrategyCandidate(strategy=STRATEGY_BASE_PREFIX, product_ids=("1", "2"))],
            primary_product_id_sets=[("1", "2", "3")],
        )

        # It could only re-describe Products the primary candidate already
        # covers, and the primary grouping outranks it, so asking about it
        # could not change any outcome.
        self.assertEqual(merged, ())

    def test_a_proposal_reaching_further_than_the_primary_is_kept(self):
        merged = CandidateStrategyService._merge(
            [StrategyCandidate(strategy=STRATEGY_BASE_PREFIX, product_ids=("1", "2", "3"))],
            primary_product_id_sets=[("1", "2")],
        )

        self.assertEqual([c.product_ids for c in merged], [("1", "2", "3")])

    def test_a_single_product_proposal_is_dropped(self):
        merged = CandidateStrategyService._merge(
            [StrategyCandidate(strategy=STRATEGY_BASE_PREFIX, product_ids=("1",))],
            primary_product_id_sets=[],
        )

        self.assertEqual(merged, ())

    def test_merging_is_deterministic(self):
        proposals = [
            StrategyCandidate(strategy=STRATEGY_HANDBOOK_GROUP, product_ids=("3", "4")),
            StrategyCandidate(strategy=STRATEGY_BASE_PREFIX, product_ids=("1", "2")),
            StrategyCandidate(strategy=STRATEGY_FUNCTIONAL_SIGNATURE, product_ids=("5", "6")),
        ]
        first = CandidateStrategyService._merge(proposals, [])
        second = CandidateStrategyService._merge(list(reversed(proposals)), [])

        self.assertEqual(
            [(c.strategy, c.product_ids) for c in first],
            [(c.strategy, c.product_ids) for c in second],
        )


def verdict(strategy, status, base, articles, products=("1", "2")):
    return ArticleSetValidation(
        base_code=base,
        product_ids=tuple(products),
        article_ids=tuple(articles),
        strategy=strategy,
        status=status,
    )


class ResolutionTests(unittest.TestCase):
    """Which confirmed candidate wins an article, and what stays blocked."""

    def test_the_primary_grouping_outranks_a_confirmed_fallback(self):
        winner, blocked = EngineeringReductionService._resolve((
            verdict(PRIMARY_STRATEGY, "validated", "AB", ["a1"]),
            verdict(STRATEGY_BASE_PREFIX, "validated", "A", ["a1"]),
        ))

        self.assertEqual(winner["a1"].strategy, PRIMARY_STRATEGY)
        self.assertEqual(blocked, set())

    def test_a_fallback_rescues_an_article_the_primary_lost(self):
        winner, blocked = EngineeringReductionService._resolve((
            verdict(PRIMARY_STRATEGY, "rejected", "AB", ["a1"]),
            verdict(STRATEGY_BASE_PREFIX, "validated", "A", ["a1"]),
        ))

        self.assertEqual(winner["a1"].strategy, STRATEGY_BASE_PREFIX)
        self.assertEqual(winner["a1"].base_code, "A")
        self.assertEqual(blocked, set())

    def test_an_article_no_candidate_confirmed_stays_blocked(self):
        winner, blocked = EngineeringReductionService._resolve((
            verdict(PRIMARY_STRATEGY, "rejected", "AB", ["a1"]),
            verdict(STRATEGY_BASE_PREFIX, "rejected", "A", ["a1"]),
        ))

        self.assertEqual(winner, {})
        self.assertEqual(blocked, {"a1"})

    def test_an_unresolved_fallback_never_releases_an_article(self):
        winner, blocked = EngineeringReductionService._resolve((
            verdict(PRIMARY_STRATEGY, "rejected", "AB", ["a1"]),
            verdict(STRATEGY_BASE_PREFIX, "unresolved", "A", ["a1"]),
        ))

        self.assertEqual(blocked, {"a1"})

    def test_the_widest_confirmed_family_wins(self):
        # The narrower family is a strict subset of the wider one and both are
        # proven, so collapsing to the wider base loses nothing and keeps the
        # family on ONE base article.
        winner, _blocked = EngineeringReductionService._resolve((
            verdict(STRATEGY_BASE_PREFIX, "validated", "ABCD", ["a1"],
                    products=("1", "2")),
            verdict(STRATEGY_BASE_PREFIX, "validated", "A", ["a1"],
                    products=("1", "2", "3", "4")),
        ))

        self.assertEqual(winner["a1"].base_code, "A")

    def test_equally_wide_confirmed_families_fall_back_to_the_longer_base(self):
        winner, _blocked = EngineeringReductionService._resolve((
            verdict(STRATEGY_BASE_PREFIX, "validated", "A", ["a1"]),
            verdict(STRATEGY_BASE_PREFIX, "validated", "ABCD", ["a1"]),
        ))

        self.assertEqual(winner["a1"].base_code, "ABCD")

    def test_a_single_product_candidate_still_applies(self):
        # No cross-Product claim, so nothing for the boundary to prove - and
        # nothing to block either.
        winner, blocked = EngineeringReductionService._resolve((
            verdict(PRIMARY_STRATEGY, "unresolved", "AB", ["a1"], products=("1",)),
        ))

        self.assertEqual(winner["a1"].base_code, "AB")
        self.assertEqual(blocked, set())

    def test_a_confirmed_family_beats_a_candidate_with_nothing_to_prove(self):
        # The single-Product candidate asserts no family; the fallback proved
        # one. Proof wins, even though the primary rule proposed the other.
        winner, blocked = EngineeringReductionService._resolve((
            verdict(PRIMARY_STRATEGY, "unresolved", "ABCDE", ["a1"], products=("1",)),
            verdict(STRATEGY_BASE_PREFIX, "validated", "AB", ["a1"]),
        ))

        self.assertEqual(winner["a1"].strategy, STRATEGY_BASE_PREFIX)
        self.assertEqual(winner["a1"].base_code, "AB")
        self.assertEqual(blocked, set())

    def test_resolution_does_not_depend_on_verdict_order(self):
        verdicts = (
            verdict(STRATEGY_HANDBOOK_GROUP, "validated", "A", ["a1"]),
            verdict(PRIMARY_STRATEGY, "rejected", "ABC", ["a1"]),
            verdict(STRATEGY_BASE_PREFIX, "validated", "AB", ["a1"]),
        )
        first, _ = EngineeringReductionService._resolve(verdicts)
        second, _ = EngineeringReductionService._resolve(tuple(reversed(verdicts)))

        self.assertEqual(first["a1"].strategy, second["a1"].strategy)
        self.assertEqual(first["a1"].strategy, STRATEGY_BASE_PREFIX)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


# --------------------------------------------------------------------------
# End to end: the reduction engine offering fallbacks to the boundary.
# --------------------------------------------------------------------------
class StubStrategyService:
    """Stands in for the strategy service at the seam the context provides."""

    def __init__(self, proposals=(), error=None):
        self._proposals, self._error = proposals, error
        self.calls = []

    def propose(self, snapshot, primary_product_id_sets=(), primary_bases=()):
        self.calls.append((list(primary_product_id_sets), list(primary_bases)))
        if self._error is not None:
            raise self._error
        return tuple(self._proposals)


class StubValidator:
    """Answers each candidate from a ProductId-set -> status table."""

    def __init__(self, table):
        self._table = table
        self.asked = []

    def validate_families(self, candidates, language_id=1, known_product_ids=None):
        results = []
        for candidate in candidates:
            ids = frozenset(str(p) for p in candidate.product_ids)
            self.asked.append(sorted(ids))
            status = self._table.get(ids, "rejected")
            results.append(
                FamilyValidation(
                    base=candidate.base,
                    intended_product_ids=tuple(sorted(ids)),
                    filtered_product_ids=(
                        tuple(sorted(ids)) if status == "validated" else ()
                    ),
                    status=status,
                    range_population_complete=True,
                )
            )
        return tuple(results)


def integration_snapshot():
    """Three Products, two structure classes: 1+2 carry Size, 3 does not.

    Codes all share the base ``BASE`` - exactly the shape of a Product whose
    attribute row is missing: the structure rule splits it off, the code still
    carries the family's base.
    """
    size = Property(id="20", code="SIZE", name="Size")
    size.values = [
        PropertyValue(id="201", property_id="20", value="Small", code="A"),
        PropertyValue(id="202", property_id="20", value="Large", code="B"),
    ]
    snapshot = Snapshot(id="s1")
    snapshot.articles = [
        Article(id="a1", product_id="1", code="BASEX.A"),
        Article(id="a2", product_id="2", code="BASEY.A"),
        Article(id="a3", product_id="3", code="BASEZ.A"),
    ]
    snapshot.properties = [size]
    snapshot.property_values = list(size.values)
    snapshot.product_property_value_ids = {"1": ["201"], "2": ["202"], "3": []}
    snapshot.product_range = {"1": RANGE_NAME, "2": RANGE_NAME, "3": RANGE_NAME}
    snapshot.engineering = Engineering(
        families=[
            EngineeringFamily(
                id="default", name="Default",
                members=[
                    MemberArticle(id=f"m{a.id}", article_id=a.id, family_id="default")
                    for a in snapshot.articles
                ],
            )
        ]
    )
    return snapshot


def integration_context(strategy_service, validator):
    context = SimpleNamespace(
        candidate_strategy_service=strategy_service,
        pdm_family_reduction_service=validator,
        engineering_member_service=SimpleNamespace(
            set_reduced_article=lambda member, base: setattr(
                member, "reduced_article", base
            )
        ),
    )
    service = EngineeringReductionService(context)
    context.engineering_reduction_service = service
    return context, service


def bases(snapshot):
    return {
        m.article_id: m.reduced_article
        for f in snapshot.engineering.families for m in f.members
    }


class ReductionWithFallbacksTests(unittest.TestCase):
    def test_a_fallback_is_appended_after_the_primary_candidates(self):
        strategy = StubStrategyService([
            StrategyCandidate(
                strategy=STRATEGY_BASE_PREFIX, product_range=RANGE_NAME,
                product_ids=("1", "2", "3"), reason="shared base",
            )
        ])
        _ctx, service = integration_context(strategy, StubValidator({}))
        snapshot = integration_snapshot()

        candidates = service.candidate_families(snapshot)

        primary = [c for c in candidates if c.strategy == PRIMARY_STRATEGY]
        fallback = [c for c in candidates if c.strategy == STRATEGY_BASE_PREFIX]
        # The primary grouping is returned untouched...
        self.assertEqual(
            sorted(c.product_ids for c in primary), [("1", "2"), ("3",)]
        )
        # ...and the fallback is an ADDITIONAL question, carrying the base its
        # own members' codes share.
        self.assertEqual([c.product_ids for c in fallback], [("1", "2", "3")])
        self.assertEqual(fallback[0].base_code, "BASE")
        self.assertEqual(fallback[0].article_ids, ("a1", "a2", "a3"))

    def test_the_strategy_service_is_told_what_the_primary_grouping_produced(self):
        strategy = StubStrategyService()
        _ctx, service = integration_context(strategy, StubValidator({}))

        service.candidate_families(integration_snapshot())

        sets, primary_bases = strategy.calls[0]
        self.assertEqual(sorted(sets), [("1", "2"), ("3",)])
        # Product 3 is alone in its structure class, so its own base is its
        # whole code - which is exactly why a wider grouping is worth asking
        # about.
        self.assertEqual(
            sorted(primary_bases), [("BASE", RANGE_NAME), ("BASEZ", RANGE_NAME)]
        )

    def test_a_fallback_rescues_what_the_primary_candidate_lost(self):
        strategy = StubStrategyService([
            StrategyCandidate(
                strategy=STRATEGY_BASE_PREFIX, product_range=RANGE_NAME,
                product_ids=("1", "2", "3"),
            )
        ])
        # The primary 1+2 over-selects; the wider grouping is exact.
        validator = StubValidator({frozenset({"1", "2", "3"}): "validated"})
        _ctx, service = integration_context(strategy, validator)
        snapshot = integration_snapshot()

        result = service.apply_validated_reduction(snapshot)

        self.assertEqual(bases(snapshot), {"a1": "BASE", "a2": "BASE", "a3": "BASE"})
        self.assertEqual(result.blocked_members, 0)
        self.assertEqual(result.applied_members, 3)

    def test_the_primary_base_still_wins_when_both_are_confirmed(self):
        strategy = StubStrategyService([
            StrategyCandidate(
                strategy=STRATEGY_BASE_PREFIX, product_range=RANGE_NAME,
                product_ids=("1", "2", "3"),
            )
        ])
        validator = StubValidator({
            frozenset({"1", "2"}): "validated",
            frozenset({"1", "2", "3"}): "validated",
        })
        _ctx, service = integration_context(strategy, validator)
        snapshot = integration_snapshot()

        service.apply_validated_reduction(snapshot)

        # a1/a2 keep the primary candidate's base, which is derived from the
        # property structure rather than from a code prefix.
        stamped = bases(snapshot)
        self.assertEqual(stamped["a1"], "BASE")
        self.assertEqual(stamped["a2"], "BASE")

    def test_nothing_confirmed_leaves_every_article_blocked(self):
        strategy = StubStrategyService([
            StrategyCandidate(
                strategy=STRATEGY_BASE_PREFIX, product_range=RANGE_NAME,
                product_ids=("1", "2", "3"),
            )
        ])
        _ctx, service = integration_context(strategy, StubValidator({}))
        snapshot = integration_snapshot()

        service.apply_validated_reduction(snapshot)

        self.assertEqual(bases(snapshot)["a1"], "")
        self.assertEqual(bases(snapshot)["a2"], "")

    def test_a_failing_strategy_service_never_breaks_the_primary_flow(self):
        strategy = StubStrategyService(error=RuntimeError("PDM unavailable"))
        validator = StubValidator({frozenset({"1", "2"}): "validated"})
        _ctx, service = integration_context(strategy, validator)
        snapshot = integration_snapshot()

        service.apply_validated_reduction(snapshot)

        # The fallback is an extra chance to prove a family; losing it must not
        # cost the reduction the families it could already prove.
        self.assertEqual(bases(snapshot)["a1"], "BASE")

    def test_without_the_strategy_service_only_primary_candidates_exist(self):
        context = SimpleNamespace(pdm_family_reduction_service=StubValidator({}))
        service = EngineeringReductionService(context)
        context.engineering_reduction_service = service

        candidates = service.candidate_families(integration_snapshot())

        self.assertEqual({c.strategy for c in candidates}, {PRIMARY_STRATEGY})

    def test_the_whole_set_diagnostic_view_asks_no_fallbacks(self):
        strategy = StubStrategyService([
            StrategyCandidate(strategy=STRATEGY_BASE_PREFIX, product_ids=("1", "2", "3"))
        ])
        _ctx, service = integration_context(strategy, StubValidator({}))

        candidates = service.candidate_families(
            integration_snapshot(), per_product_range=False
        )

        self.assertEqual({c.strategy for c in candidates}, {PRIMARY_STRATEGY})
        self.assertEqual(strategy.calls, [])
