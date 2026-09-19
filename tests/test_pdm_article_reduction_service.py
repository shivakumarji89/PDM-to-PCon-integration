"""The enforced production reduction path.

``EngineeringReductionService.apply_validated_reduction`` is the step that
actually collapses a family. These tests drive it end to end - property
classification, article-set materialisation, candidate derivation, the legacy
``ProductsList`` call, the verdict, and the resulting
``member.reduced_article`` - stubbing only the PDM rows the compatibility
repository would have read.

The rule under test: a candidate that asserts a cross-Product base collapses
only when ``ProductsList``, given the candidate's common functional
(non-order-code) AttributeValueIds, returns EXACTLY the candidate's
ProductIds. Anything else - a missing Product, an extra Product, a split
ProductRange, a failed check - leaves the family expanded.
"""
import unittest
from types import SimpleNamespace

from models.article import Article
from models.engineering import Engineering
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering.engineering_member_service import EngineeringMemberService
from services.engineering.engineering_reduction_service import (
    EngineeringReductionService,
)
from services.engineering.pdm_family_reduction_service import (
    PDMFamilyReductionService,
)

RANGE_ID = "6511"
OTHER_RANGE_ID = "6515"
US_CATEGORY_ID = "318"


class FakeConnection:
    def close(self):
        pass


class FakePDM:
    """Scripted PDM rows. ``filtered`` is what ``ProductsList`` returns.

    ``range_population`` is the complete legacy-eligible population of the
    range (``NewProduct = 1 OR an Item with Status = 1``); ``ranges`` maps a
    ProductId to its ProductRangeId.
    """

    def __init__(
        self, filtered, range_population, ranges=None, us_range=False,
        attributes=None, fail=None,
    ):
        self._filtered = filtered
        self._range_population = range_population
        self._ranges = ranges or {}
        self._us_range = us_range
        self._attributes = attributes if attributes is not None else DEFAULT_ATTRIBUTES
        self._fail = fail
        self.filter_calls = []

    def get_connection(self):
        if self._fail == "connection":
            raise OSError("PDM server unreachable")
        return FakeConnection()

    def fetch_products_range_info(self, product_ids, connection=None):
        return [
            SimpleNamespace(
                ProductId=pid, Product=f"P{pid}",
                ProductRangeId=self._ranges.get(str(pid), RANGE_ID),
                Status=1, NewProduct=0,
            )
            for pid in product_ids
            if str(pid) in self._ranges or not self._ranges
        ]

    def range_scope(self, product_range_id, connection=None):
        return US_CATEGORY_ID, self._us_range

    def fetch_range_product_ids(self, product_range_id, connection=None):
        return [
            SimpleNamespace(ProductId=pid)
            for pid in self._range_population.get(str(product_range_id), ())
        ]

    def fetch_products_filter_attributes(self, product_ids, connection=None):
        wanted = {str(p) for p in product_ids}
        return [
            SimpleNamespace(
                ProductId=pid, AttributeId=aid, AttributeValueId=vid,
                AttributeType=0, OrderCodeFormatKey=key,
                OrderCodeValue="", ModelSuffix="",
            )
            for pid, aid, vid, key in self._attributes
            if pid in wanted
        ]

    def fetch_legacy_filtered_products(
        self, product_range_id, language_id, xml, connection=None
    ):
        if self._fail == "filter":
            raise RuntimeError("ProductsList timed out")
        self.filter_calls.append((product_range_id, language_id, xml))
        return [
            SimpleNamespace(ProductId=pid)
            for pid in self._filtered.get(str(product_range_id), ())
        ]


#: Two Products sharing one functional value (100) and differing only in an
#: order-code-bearing attribute (SIZE), which must never define the family.
DEFAULT_ATTRIBUTES = [
    ("1", "10", "100", ""),
    ("2", "10", "100", ""),
    ("1", "20", "201", "SIZE"),
    ("2", "20", "202", "SIZE"),
]


def build_snapshot(codes=None, product_range=None, product_values=None):
    """Two Products, one shared property structure, one candidate family.

    ``codes`` maps article id -> article code; the default pair differs only
    after the shared ``BASE`` prefix and carries distinct after-dot suffixes.
    """
    codes = codes or {"a1": "BASE1.ABCD", "a2": "BASE2.EFGH"}
    product_of = {"a1": "1", "a2": "2"}

    series = Property(id="10", code="", name="Series")  # code == OrderCodeFormatKey
    series.values = [PropertyValue(id="100", property_id="10", value="Nevi", code="")]
    size = Property(id="20", code="SIZE", name="Size")
    size.values = [
        PropertyValue(id="201", property_id="20", value="Small", code="A"),
        PropertyValue(id="202", property_id="20", value="Large", code="B"),
    ]

    snapshot = Snapshot(id="s1")
    snapshot.articles = [
        Article(id=aid, product_id=product_of[aid], code=code)
        for aid, code in codes.items()
    ]
    snapshot.properties = [series, size]
    snapshot.property_values = series.values + size.values
    snapshot.product_property_value_ids = product_values or {
        "1": ["100", "201"], "2": ["100", "202"],
    }
    if product_range is not None:
        snapshot.product_range = product_range
    snapshot.engineering = Engineering(
        families=[
            EngineeringFamily(
                id="default", name="Default Family",
                members=[
                    MemberArticle(id=f"m{a.id}", article_id=a.id, family_id="default")
                    for a in snapshot.articles
                ],
            )
        ]
    )
    return snapshot


def build_context(pdm):
    """The real services, wired as the application wires them, minus the DB."""
    context = SimpleNamespace()
    validator = PDMFamilyReductionService.__new__(PDMFamilyReductionService)
    validator.context = context
    validator.repository = pdm
    context.pdm_family_reduction_service = validator
    context.engineering_member_service = EngineeringMemberService(context)
    service = EngineeringReductionService(context)
    context.engineering_reduction_service = service
    return context, service


def bases(snapshot):
    return {
        m.article_id: m.reduced_article
        for m in snapshot.engineering.families[0].members
    }


class ValidatedFamilyCollapsesTests(unittest.TestCase):
    def test_exact_products_list_match_applies_the_reduction(self):
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2"]},
            range_population={RANGE_ID: ["1", "2"]},
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()

        result = service.apply_validated_reduction(snapshot)

        self.assertEqual([v.status for v in result.validations], ["validated"])
        self.assertEqual(result.applied_members, 2)
        self.assertEqual(result.blocked_members, 0)
        # Both members collapsed onto the ONE shared base.
        self.assertEqual(bases(snapshot), {"a1": "BASE", "a2": "BASE"})

    def test_complete_range_population_allows_validation(self):
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2"]},
            range_population={RANGE_ID: ["1", "2"]},
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()

        verdict = service.apply_validated_reduction(snapshot).validations[0]

        self.assertTrue(verdict.snapshot_covers_range)
        self.assertEqual(verdict.unloaded_range_product_count, 0)
        self.assertTrue(verdict.is_legacy_equivalent)

    def test_products_list_is_asked_with_the_functional_selector_only(self):
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2"]},
            range_population={RANGE_ID: ["1", "2"]},
        )
        _ctx, service = build_context(pdm)

        service.apply_validated_reduction(build_snapshot())

        range_id, language_id, xml = pdm.filter_calls[0]
        self.assertEqual(range_id, RANGE_ID)
        self.assertEqual(language_id, 1)
        self.assertEqual(
            xml,
            '<attributes><attribute attributeid="10" '
            'attributevalueid="100"/></attributes>',
        )


class RejectedFamilyStaysExpandedTests(unittest.TestCase):
    def test_extra_product_id_rejects_and_does_not_apply(self):
        # ProductsList also selects Product 3 - the base over-selects. The
        # loaded set IS the whole eligible range, so this is a real
        # disagreement with the grouping, not a coverage gap.
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2", "3"]},
            range_population={RANGE_ID: ["1", "2"]},
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()

        result = service.apply_validated_reduction(snapshot)

        verdict = result.validations[0]
        self.assertEqual(verdict.status, "rejected")
        self.assertEqual(verdict.extra_in_filter, ("3",))
        self.assertTrue(verdict.blocks_reduction)
        self.assertEqual(result.applied_members, 0)
        self.assertEqual(result.blocked_members, 2)
        self.assertEqual(bases(snapshot), {"a1": "", "a2": ""})

    def test_missing_product_id_rejects_and_does_not_apply(self):
        # ProductsList does not reach Product 2 - the base under-selects.
        pdm = FakePDM(
            filtered={RANGE_ID: ["1"]},
            range_population={RANGE_ID: ["1", "2"]},
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()

        result = service.apply_validated_reduction(snapshot)

        verdict = result.validations[0]
        self.assertEqual(verdict.status, "rejected")
        self.assertEqual(verdict.missing_from_filter, ("2",))
        self.assertEqual(result.applied_members, 0)
        self.assertEqual(bases(snapshot), {"a1": "", "a2": ""})

    def test_a_rejected_family_cannot_keep_an_earlier_base(self):
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2", "3"]},
            range_population={RANGE_ID: ["1", "2", "3"]},
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()
        for member in snapshot.engineering.families[0].members:
            member.reduced_article = "BASE"  # a collapse applied earlier

        service.apply_validated_reduction(snapshot)

        self.assertEqual(bases(snapshot), {"a1": "", "a2": ""})

    def test_unchecked_family_is_blocked_not_assumed_valid(self):
        pdm = FakePDM(
            filtered={}, range_population={RANGE_ID: ["1", "2"]}, fail="filter",
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()

        result = service.apply_validated_reduction(snapshot)

        verdict = result.validations[0]
        self.assertEqual(verdict.status, "error")
        self.assertIn("ProductsList timed out", verdict.reason)
        self.assertTrue(verdict.blocks_reduction)
        self.assertEqual(bases(snapshot), {"a1": "", "a2": ""})

    def test_unreachable_pdm_blocks_every_family(self):
        pdm = FakePDM(
            filtered={}, range_population={RANGE_ID: ["1", "2"]}, fail="connection",
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()

        result = service.apply_validated_reduction(snapshot)

        self.assertEqual([v.status for v in result.validations], ["error"])
        self.assertIn("PDM server unreachable", result.validations[0].reason)
        self.assertEqual(bases(snapshot), {"a1": "", "a2": ""})


class ProductRangeBoundaryTests(unittest.TestCase):
    def test_products_of_different_ranges_never_form_one_validated_family(self):
        # One property structure, but the two Products sit in different
        # ProductRanges: ProductsList is ProductRange-scoped, so each slice is
        # asked separately and neither can assert the combined base.
        pdm = FakePDM(
            filtered={RANGE_ID: ["1"], OTHER_RANGE_ID: ["2"]},
            range_population={RANGE_ID: ["1"], OTHER_RANGE_ID: ["2"]},
            ranges={"1": RANGE_ID, "2": OTHER_RANGE_ID},
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot(
            product_range={"1": "Nevi Desks", "2": "Screen with Brackets"}
        )

        result = service.apply_validated_reduction(snapshot)

        self.assertEqual(len(result.validations), 2)
        for verdict in result.validations:
            self.assertEqual(len(verdict.product_ids), 1)
            self.assertFalse(verdict.is_legacy_equivalent)
        # No verdict ever claimed both Products as one legacy family.
        self.assertFalse(
            any(set(v.product_ids) == {"1", "2"} for v in result.validations)
        )

    def test_unsliced_multi_range_candidate_is_unresolved_never_validated(self):
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2"]},
            range_population={RANGE_ID: ["1", "2"]},
            ranges={"1": RANGE_ID, "2": OTHER_RANGE_ID},
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()  # no snapshot.product_range -> one candidate

        verdicts = service.validate_article_sets(snapshot)

        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0].status, "unresolved")
        self.assertIn("multiple ProductRangeIds", verdicts[0].reason)
        self.assertTrue(verdicts[0].blocks_reduction)

    def test_us_range_is_unresolved_not_filtered_through_productslist(self):
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2"]},
            range_population={RANGE_ID: ["1", "2"]},
            us_range=True,
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()

        result = service.apply_validated_reduction(snapshot)

        verdict = result.validations[0]
        self.assertEqual(verdict.status, "unresolved")
        self.assertTrue(verdict.blocks_reduction)
        self.assertEqual(verdict.product_category_id, US_CATEGORY_ID)
        # The legacy US selector answers in USItemIds against
        # USItemAttributeValues, so there is nothing to compare a Product set
        # with - and ProductsList must NOT be used as a stand-in.
        self.assertEqual(pdm.filter_calls, [])
        self.assertEqual(verdict.filtered_product_ids, ())
        self.assertIn("USProductsList", verdict.reason)
        self.assertIn("USItemId", verdict.reason)
        self.assertIn(US_CATEGORY_ID, verdict.reason)
        self.assertEqual(bases(snapshot), {"a1": "", "a2": ""})


class FunctionalVersusOrderCodeTests(unittest.TestCase):
    def test_a_shared_order_code_value_never_defines_the_family(self):
        # Both Products carry the SAME order-code-bearing value (300). It must
        # stay out of the selector even though it is common to the family.
        attributes = [
            ("1", "30", "300", "FINISH"),
            ("2", "30", "300", "FINISH"),
            ("1", "10", "100", ""),
            ("2", "10", "100", ""),
        ]
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2"]},
            range_population={RANGE_ID: ["1", "2"]},
            attributes=attributes,
        )
        _ctx, service = build_context(pdm)

        verdict = service.validate_article_sets(build_snapshot())[0]

        self.assertEqual(verdict.functional_attribute_value_ids, ("100",))
        self.assertNotIn("300", verdict.functional_attribute_value_ids)
        self.assertNotIn('attributevalueid="300"', pdm.filter_calls[0][2])

    def test_only_order_code_values_in_common_leaves_nothing_to_prove(self):
        attributes = [
            ("1", "30", "300", "FINISH"),
            ("2", "30", "300", "FINISH"),
            ("1", "10", "100", ""),
            ("2", "10", "199", ""),  # functional values differ
        ]
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2"]},
            range_population={RANGE_ID: ["1", "2"]},
            attributes=attributes,
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()

        result = service.apply_validated_reduction(snapshot)

        self.assertEqual(result.validations[0].status, "unresolved")
        self.assertIn("No shared non-order-code", result.validations[0].reason)
        self.assertEqual(pdm.filter_calls, [])
        self.assertEqual(bases(snapshot), {"a1": "", "a2": ""})


class IncompleteSnapshotTests(unittest.TestCase):
    """A partly loaded ProductRange is an incomplete question, never a pass.

    ``dbo.ProductsList`` filters the COMPLETE eligible population of a range.
    A candidate drawn from a subset of that range therefore cannot be compared
    against it at all - the Products nobody loaded come back as over-matches
    whatever the grouping is. That is reported as ``unresolved`` (which still
    blocks the collapse), never as ``validated``, and never as a ``rejected``
    that blames the grouping.
    """

    def test_an_incomplete_snapshot_is_never_reported_as_equivalent(self):
        # The snapshot holds Products 1 and 2; the range really holds four, and
        # ProductsList selects two of the unloaded ones as well.
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2", "3", "4"]},
            range_population={RANGE_ID: ["1", "2", "3", "4"]},
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()

        verdict = service.apply_validated_reduction(snapshot).validations[0]

        self.assertEqual(verdict.status, "unresolved")
        self.assertFalse(verdict.is_legacy_equivalent)
        self.assertTrue(verdict.blocks_reduction)
        self.assertFalse(verdict.snapshot_covers_range)
        self.assertEqual(verdict.unloaded_range_product_count, 2)
        self.assertIn("only partly loaded", verdict.reason)
        # The over-match is invisible to the snapshot - only the live boundary
        # could reveal it, which is exactly why the check is not done locally.
        self.assertEqual(verdict.extra_outside_snapshot, ("3", "4"))
        self.assertEqual(bases(snapshot), {"a1": "", "a2": ""})

    def test_partial_range_blocks_even_when_the_loaded_scope_agrees(self):
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2"]},
            range_population={RANGE_ID: ["1", "2", "3"]},
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()

        verdict = service.apply_validated_reduction(snapshot).validations[0]

        # Everything the snapshot can see agrees - but Product 3 was never
        # loaded, so the range has to be completed before the comparison means
        # anything. Agreement within a partial view is not proof.
        self.assertEqual(verdict.status, "unresolved")
        self.assertTrue(verdict.blocks_reduction)
        self.assertFalse(verdict.snapshot_covers_range)
        self.assertEqual(verdict.unloaded_range_product_count, 1)
        self.assertIn(
            "Inside the loaded scope ProductsList returned exactly the "
            "candidate", verdict.reason,
        )
        self.assertEqual(bases(snapshot), {"a1": "", "a2": ""})

    def test_a_complete_range_is_validated_and_applied(self):
        # The same agreement, once the range is complete, IS proof.
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2"]},
            range_population={RANGE_ID: ["1", "2"]},
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()

        result = service.apply_validated_reduction(snapshot)

        verdict = result.validations[0]
        self.assertEqual(verdict.status, "validated")
        self.assertTrue(verdict.snapshot_covers_range)
        self.assertEqual(verdict.unloaded_range_product_count, 0)
        self.assertEqual(result.blocked_members, 0)


class AfterDotIsPreservedTests(unittest.TestCase):
    def test_suffixes_survive_reduction_byte_for_byte(self):
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2"]},
            range_population={RANGE_ID: ["1", "2"]},
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot(codes={"a1": "BASE1.ABCD", "a2": "BASE2.EFGH"})
        before = {a.id: a.code for a in snapshot.articles}

        service.apply_validated_reduction(snapshot)

        # BASE1.ABCD / BASE2.EFGH -> base 'BASE', suffixes untouched.
        self.assertEqual(bases(snapshot), {"a1": "BASE", "a2": "BASE"})
        self.assertEqual({a.id: a.code for a in snapshot.articles}, before)
        for article in snapshot.articles:
            self.assertEqual(
                article.code.split(".", 1)[1], before[article.id].split(".", 1)[1]
            )

    def test_a_base_never_reaches_past_the_dot(self):
        # Codes share everything up to and beyond the '.', so the derived base
        # would otherwise swallow part of the order-code suffix.
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2"]},
            range_population={RANGE_ID: ["1", "2"]},
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot(codes={"a1": "BASE.ABCD", "a2": "BASE.ABCH"})

        service.apply_validated_reduction(snapshot)

        for article_id, base in bases(snapshot).items():
            code = next(a.code for a in snapshot.articles if a.id == article_id)
            self.assertLessEqual(len(base), code.index(".") + 1)
            self.assertTrue(code.startswith(base))
            self.assertTrue(code[len(base):].lstrip(".").isalnum())

    def test_blocked_family_leaves_articles_completely_unchanged(self):
        pdm = FakePDM(
            filtered={RANGE_ID: ["1", "2", "3"]},
            range_population={RANGE_ID: ["1", "2", "3"]},
        )
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()
        before = {a.id: a.code for a in snapshot.articles}

        service.apply_validated_reduction(snapshot)

        self.assertEqual({a.id: a.code for a in snapshot.articles}, before)


class SingleProductCandidateTests(unittest.TestCase):
    """One Product's own articles collapsing onto one base is not a
    cross-Product family claim, so the boundary is not consulted and the
    reduction is not blocked for want of a proof it cannot give."""

    def test_single_product_candidate_applies_without_a_products_list_call(self):
        pdm = FakePDM(filtered={}, range_population={})
        _ctx, service = build_context(pdm)
        snapshot = build_snapshot()
        # Both articles belong to one Product.
        for article in snapshot.articles:
            article.product_id = "1"
        snapshot.product_property_value_ids = {"1": ["100", "201"]}

        result = service.apply_validated_reduction(snapshot)

        self.assertEqual(pdm.filter_calls, [])
        self.assertEqual(result.validations[0].status, "unresolved")
        self.assertFalse(result.validations[0].blocks_reduction)
        self.assertEqual(result.applied_members, 2)
        self.assertEqual(bases(snapshot), {"a1": "BASE", "a2": "BASE"})


if __name__ == "__main__":
    unittest.main()
