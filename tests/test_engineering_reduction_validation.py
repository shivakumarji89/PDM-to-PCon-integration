"""The integrated flow: candidate families from the existing reduction engine,
proven against the legacy ``ProductsList`` boundary.

These tests drive the REAL chain -
``EngineeringReductionService.classify_by_properties`` ->
``materialize_article_sets`` -> ``candidate_families`` ->
``PDMFamilyReductionService.validate_families`` - and stub only the database
rows the compatibility repository would have read. Nothing here supplies a
grouping: every candidate family is the one the reduction engine derived.
"""
import unittest
from copy import deepcopy
from types import SimpleNamespace

from models.article import Article
from models.engineering import Engineering
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering.engineering_reduction_service import (
    EngineeringReductionService,
)
from services.engineering.pdm_family_reduction_service import (
    PDMFamilyReductionService,
)

RANGE_ID = "5416"


class FakeConnection:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeCompatRepository:
    """Scripted PDM rows; no database and no network."""

    def __init__(self, filtered_ids, range_population, raise_on_filter=False):
        self._filtered_ids = filtered_ids
        self._range_population = range_population
        self._raise_on_filter = raise_on_filter
        self.connections = []
        self.filter_calls = []

    def get_connection(self):
        connection = FakeConnection()
        self.connections.append(connection)
        return connection

    def fetch_products_range_info(self, product_ids, connection=None):
        return [
            SimpleNamespace(
                ProductId=pid, Product=f"P{pid}", ProductRangeId=RANGE_ID,
                Status=1, NewProduct=0,
            )
            for pid in product_ids
            if str(pid) in {"1", "2", "3"}
        ]

    def range_scope(self, product_range_id, connection=None):
        return "90", False

    def fetch_range_product_ids(self, product_range_id, connection=None):
        return [SimpleNamespace(ProductId=pid) for pid in self._range_population]

    def fetch_products_filter_attributes(self, product_ids, connection=None):
        wanted = {str(p) for p in product_ids}
        rows = [
            # Functional (no OrderCodeFormatKey) - shared family identity.
            ("1", "10", "100", ""),
            ("2", "10", "100", ""),
            # Order-code bearing - drives the after-dot suffix, never identity.
            ("1", "20", "201", "SIZE"),
            ("2", "20", "202", "SIZE"),
        ]
        return [
            SimpleNamespace(
                ProductId=pid, AttributeId=aid, AttributeValueId=vid,
                AttributeType=0, OrderCodeFormatKey=key,
                OrderCodeValue="", ModelSuffix="",
            )
            for pid, aid, vid, key in rows
            if pid in wanted
        ]

    def fetch_legacy_filtered_products(
        self, product_range_id, language_id, xml, connection=None
    ):
        if self._raise_on_filter:
            raise RuntimeError("ProductsList unavailable")
        self.filter_calls.append((product_range_id, language_id, xml))
        return [SimpleNamespace(ProductId=pid) for pid in self._filtered_ids]


def build_snapshot(single_product=False):
    """Two Products sharing one property structure, three articles.

    Codes carry the ``.`` boundary so the reduced base stays pre-dot and the
    after-dot suffix is visible to the assertions.
    """
    series = Property(id="10", code="", name="Series")  # code == OrderCodeFormatKey
    series.values = [PropertyValue(id="100", property_id="10", value="Nevi", code="")]
    size = Property(id="20", code="SIZE", name="Size")
    size.values = [
        PropertyValue(id="201", property_id="20", value="Small", code="A"),
        PropertyValue(id="202", property_id="20", value="Large", code="B"),
    ]

    articles = [
        Article(id="a1", product_id="1", code="RY3XTDAB.A"),
        Article(id="a2", product_id="1", code="RY3XTDAB.B"),
    ]
    product_values = {"1": ["100", "201"]}
    if not single_product:
        articles.append(Article(id="a3", product_id="2", code="RY3XTDAC.A"))
        product_values["2"] = ["100", "202"]

    snapshot = Snapshot(id="s1")
    snapshot.articles = articles
    snapshot.properties = [series, size]
    snapshot.property_values = series.values + size.values
    snapshot.product_property_value_ids = product_values
    snapshot.engineering = Engineering(
        families=[
            EngineeringFamily(
                id="default", name="Default Family",
                members=[
                    MemberArticle(id=f"m{a.id}", article_id=a.id, family_id="default")
                    for a in articles
                ],
            )
        ]
    )
    return snapshot


def build_context(repository):
    """A context wired exactly as the app wires it, minus the database."""
    context = SimpleNamespace()
    validator = PDMFamilyReductionService.__new__(PDMFamilyReductionService)
    validator.context = context
    validator.repository = repository
    context.pdm_family_reduction_service = validator
    service = EngineeringReductionService(context)
    context.engineering_reduction_service = service
    return context, service


class CandidateFamilyTests(unittest.TestCase):
    def test_candidates_are_the_materialised_article_sets(self):
        _ctx, service = build_context(FakeCompatRepository(["1", "2"], ["1", "2"]))
        snapshot = build_snapshot()

        candidates = service.candidate_families(snapshot)

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        # The grouping came from the reduction engine, not from the validator.
        self.assertEqual(candidate.product_ids, ("1", "2"))
        self.assertEqual(candidate.article_ids, ("a1", "a2", "a3"))
        self.assertEqual(candidate.base_code, "RY3XTDA")
        self.assertEqual(candidate.set_id, snapshot.article_sets[0].id)
        self.assertEqual(snapshot.article_sets[0].article_ids, ["a1", "a2", "a3"])

    def test_two_product_ranges_are_two_article_sets_from_the_start(self):
        _ctx, service = build_context(FakeCompatRepository(["1", "2"], ["1", "2"]))
        snapshot = build_snapshot()
        # One property structure, two ProductRanges. PDM keeps the order-code
        # template per range and ProductsList only answers per range, so these
        # are two families - and they are separated during classification, not
        # by slicing a mixed set afterwards.
        snapshot.product_range = {"1": "Nevi", "2": "Nevi Screens"}

        candidates = service.candidate_families(snapshot)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            {(c.product_range, c.product_ids) for c in candidates},
            {("Nevi", ("1",)), ("Nevi Screens", ("2",))},
        )
        # Each range owns its own ArticleSet, so each derives its base length
        # from its own codes instead of sharing one across two templates.
        self.assertEqual(len(snapshot.article_sets), 2)
        self.assertEqual(
            {tuple(s.article_ids) for s in snapshot.article_sets},
            {("a1", "a2"), ("a3",)},
        )
        self.assertEqual(
            {c.set_id for c in candidates},
            {s.id for s in snapshot.article_sets},
        )

    def test_classification_carries_the_range_it_belongs_to(self):
        _ctx, service = build_context(FakeCompatRepository(["1", "2"], ["1", "2"]))
        snapshot = build_snapshot()
        snapshot.product_range = {"1": "Nevi", "2": "Nevi Screens"}

        classes = service.classify_by_properties(snapshot)

        self.assertEqual(
            {(c.product_range, c.article_ids) for c in classes},
            {("Nevi", ("a1", "a2")), ("Nevi Screens", ("a3",))},
        )
        # Same property structure on both sides - only the range separates them.
        self.assertEqual(len({c.signature for c in classes}), 1)

    def test_whole_set_mode_asks_about_each_set_unlabelled(self):
        _ctx, service = build_context(FakeCompatRepository(["1", "2"], ["1", "2"]))
        snapshot = build_snapshot()
        snapshot.product_range = {"1": "Nevi", "2": "Nevi Screens"}

        candidates = service.candidate_families(snapshot, per_product_range=False)

        # Sets are already single-range, so asking about the whole set changes
        # only the label, never the membership.
        self.assertEqual(len(candidates), 2)
        self.assertEqual({c.product_ids for c in candidates}, {("1",), ("2",)})
        self.assertEqual({c.product_range for c in candidates}, {""})


class ArticleSetValidationTests(unittest.TestCase):
    def test_exact_products_list_match_is_validated(self):
        repository = FakeCompatRepository(["1", "2"], ["1", "2"])
        _ctx, service = build_context(repository)

        results = service.validate_article_sets(build_snapshot())

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.status, "validated")
        self.assertTrue(result.is_legacy_equivalent)
        self.assertEqual(result.base_code, "RY3XTDA")
        self.assertEqual(result.product_range_id, RANGE_ID)
        self.assertEqual(result.product_ids, ("1", "2"))
        # Only the shared non-order-code value is used as the selector.
        self.assertEqual(result.functional_attribute_value_ids, ("100",))
        self.assertTrue(result.snapshot_covers_range)
        self.assertEqual(result.unloaded_range_product_count, 0)

    def test_selector_xml_carries_the_owning_attribute_id(self):
        repository = FakeCompatRepository(["1", "2"], ["1", "2"])
        _ctx, service = build_context(repository)

        service.validate_article_sets(build_snapshot())

        _range_id, _language, xml = repository.filter_calls[0]
        self.assertEqual(
            xml,
            '<attributes><attribute attributeid="10" '
            'attributevalueid="100"/></attributes>',
        )
        # The order-code attribute never enters the selector.
        self.assertNotIn('attributevalueid="201"', xml)
        self.assertNotIn('attributevalueid="202"', xml)

    def test_partly_loaded_range_is_unresolved_never_rejected(self):
        # ProductsList also returns Product 3, which lives in the range but was
        # never loaded. The procedure filters the WHOLE range, so this is an
        # incomplete question rather than a wrong grouping: unresolved, and
        # still not a pass.
        repository = FakeCompatRepository(["1", "2", "3"], ["1", "2", "3"])
        _ctx, service = build_context(repository)

        result = service.validate_article_sets(build_snapshot())[0]

        self.assertEqual(result.status, "unresolved")
        self.assertFalse(result.is_legacy_equivalent)
        self.assertTrue(result.blocks_reduction)
        self.assertIn("only partly loaded", result.reason)
        self.assertIn("1 of its 3", result.reason)
        # The evidence is still reported, so the gap can be acted on.
        self.assertFalse(result.snapshot_covers_range)
        self.assertEqual(result.unloaded_range_product_count, 1)
        self.assertEqual(result.extra_in_filter, ("3",))
        self.assertEqual(result.extra_outside_snapshot, ("3",))
        self.assertEqual(result.missing_from_filter, ())

    def test_over_selection_inside_a_complete_range_is_rejected(self):
        # The loaded set IS the whole eligible range, so an extra ProductId in
        # the filter result is a real disagreement with the grouping.
        repository = FakeCompatRepository(["1", "2", "3"], ["1", "2"])
        _ctx, service = build_context(repository)

        result = service.validate_article_sets(build_snapshot())[0]

        self.assertEqual(result.status, "rejected")
        self.assertFalse(result.is_legacy_equivalent)
        self.assertTrue(result.snapshot_covers_range)
        self.assertEqual(result.extra_in_filter, ("3",))
        self.assertIn("0 missing, 1 extra", result.reason)

    def test_incomplete_range_population_is_reported_not_assumed(self):
        repository = FakeCompatRepository(["1", "2"], ["1", "2", "3"])
        _ctx, service = build_context(repository)

        result = service.validate_article_sets(build_snapshot())[0]

        self.assertFalse(result.snapshot_covers_range)
        self.assertEqual(result.unloaded_range_product_count, 1)

    def test_single_product_set_is_unresolved_never_validated(self):
        repository = FakeCompatRepository(["1"], ["1"])
        _ctx, service = build_context(repository)

        result = service.validate_article_sets(build_snapshot(single_product=True))[0]

        self.assertEqual(result.status, "unresolved")
        self.assertFalse(result.is_legacy_equivalent)
        self.assertIn("Fewer than two Products", result.reason)
        # No cross-Product claim, so nothing to prove and nothing to block.
        self.assertFalse(result.makes_legacy_claim)
        self.assertFalse(result.blocks_reduction)

    def test_one_verdict_per_range_each_labelled(self):
        repository = FakeCompatRepository(["1", "2"], ["1", "2"])
        _ctx, service = build_context(repository)
        snapshot = build_snapshot()
        snapshot.product_range = {"1": "Nevi", "2": "Nevi Screens"}

        results = service.validate_article_sets(snapshot)

        self.assertEqual(
            sorted(r.product_range for r in results), ["Nevi", "Nevi Screens"]
        )
        self.assertEqual(
            {r.set_id for r in results}, {s.id for s in snapshot.article_sets}
        )
        # Each slice holds one Product here, so neither slice can be proven -
        # reported as unresolved, never quietly passed.
        self.assertEqual([r.status for r in results], ["unresolved", "unresolved"])
        self.assertFalse(any(r.is_legacy_equivalent for r in results))

    def test_boundary_failure_is_surfaced_not_swallowed(self):
        repository = FakeCompatRepository([], ["1", "2"], raise_on_filter=True)
        _ctx, service = build_context(repository)

        result = service.validate_article_sets(build_snapshot())[0]

        self.assertEqual(result.status, "error")
        self.assertFalse(result.is_legacy_equivalent)
        self.assertIn("ProductsList unavailable", result.reason)

    def test_missing_validator_service_raises(self):
        context = SimpleNamespace()
        service = EngineeringReductionService(context)

        with self.assertRaises(AttributeError):
            service.validate_article_sets(build_snapshot())

    def test_connection_is_released(self):
        repository = FakeCompatRepository(["1", "2"], ["1", "2"])
        _ctx, service = build_context(repository)

        service.validate_article_sets(build_snapshot())

        self.assertEqual(len(repository.connections), 1)
        self.assertTrue(repository.connections[0].closed)


class USRangeTests(unittest.TestCase):
    """A US range reaches the engineering layer as an explicit non-answer."""

    def test_us_range_blocks_reduction_and_names_the_category(self):
        class USRepository(FakeCompatRepository):
            def range_scope(self, product_range_id, connection=None):
                return "318", True

        repository = USRepository(["1", "2"], ["1", "2"])
        _ctx, service = build_context(repository)

        result = service.validate_article_sets(build_snapshot())[0]

        self.assertEqual(result.status, "unresolved")
        self.assertTrue(result.blocks_reduction)
        self.assertFalse(result.is_legacy_equivalent)
        self.assertEqual(result.product_category_id, "318")
        self.assertEqual(repository.filter_calls, [])
        self.assertEqual(result.functional_attribute_value_ids, ())


class BaseArticleTests(unittest.TestCase):
    """The base article ends where the set starts to CONFIGURE, not where its
    first head property happens to sit.

    A head property carrying one value for every product in the set configures
    nothing here: it is set identity and belongs in the base (PDM's ``$BAN``
    rule). Counting it as configurable cut the base back to the first head
    position any member merely carried - which on a real Nevi desk family left
    ``DWE`` where PDM's own handbook records ``DWE36A``.
    """

    #: Two head properties with no stored order code: "Type" occupies head
    #: positions 3-5, "Leg type" position 6.
    LAYOUT = {"30": {"position": 3, "width": 3}, "40": {"position": 6, "width": 1}}

    @staticmethod
    def build(products):
        """``products`` = [(product id, code, type value id, leg value id)]."""
        kind = Property(id="30", code="", name="Type")
        kind.values = [
            PropertyValue(id="300", property_id="30", value="Rectangular"),
            PropertyValue(id="301", property_id="30", value="Rectangular return"),
        ]
        leg = Property(id="40", code="", name="Leg type")
        leg.values = [
            PropertyValue(id="400", property_id="40", value="Circular"),
            PropertyValue(id="401", property_id="40", value="T-foot"),
        ]

        snapshot = Snapshot(id="s-base")
        snapshot.articles = [
            Article(id=f"a{index}", product_id=pid, code=code)
            for index, (pid, code, _t, _l) in enumerate(products)
        ]
        snapshot.properties = [kind, leg]
        snapshot.property_values = kind.values + leg.values
        snapshot.product_property_value_ids = {
            pid: [type_id, leg_id] for pid, _code, type_id, leg_id in products
        }
        context = SimpleNamespace(
            engineering_class_service=SimpleNamespace(
                config_code_layout=lambda _s: BaseArticleTests.LAYOUT
            )
        )
        return snapshot, EngineeringReductionService(context)

    def test_a_constant_head_property_stays_in_the_base(self):
        snapshot, service = self.build([
            ("1", "DWE36AC4Y.0812", "300", "400"),
            ("2", "DWE36AT4Y.0812", "300", "401"),
        ])

        article_set = service.materialize_article_sets(snapshot)[0]

        # "Type" is the same value for both products, so its characters (36A)
        # are identity. The base ends at "Leg type" - the first head position
        # this set actually configures.
        self.assertEqual(article_set.base_length, 6)
        self.assertEqual(article_set.base_code, "DWE36A")

    def test_the_earliest_varying_head_property_ends_the_base(self):
        snapshot, service = self.build([
            ("1", "DWE36AC4Y.0812", "300", "400"),
            ("2", "DWE36RC4Y.0812", "301", "400"),
        ])

        article_set = service.materialize_article_sets(snapshot)[0]

        # Now "Leg type" is constant and "Type" varies, so the base stops at
        # "Type" instead. The rule follows the data, not the property order.
        self.assertEqual(article_set.base_length, 3)
        self.assertEqual(article_set.base_code, "DWE")

    def test_with_nothing_varying_the_whole_head_is_the_base(self):
        snapshot, service = self.build([
            ("1", "DWE36AC4Y.0812", "300", "400"),
            ("1", "DWE36AC4Y.0814", "300", "400"),
        ])

        article_set = service.materialize_article_sets(snapshot)[0]

        # One product, two sizes: no head property configures anything, so the
        # base is the whole head - everything in front of the "." - and the
        # order-code suffix stays outside it.
        self.assertEqual(article_set.base_code, "DWE36AC4Y")
        self.assertNotIn(".", article_set.base_code)


class ValidationIsReadOnlyTests(unittest.TestCase):
    """Validation must not move the base split nor the after-dot suffix."""

    def test_article_codes_bases_and_reduced_articles_are_untouched(self):
        repository = FakeCompatRepository(["1", "2", "3"], ["1", "2"])
        _ctx, service = build_context(repository)
        snapshot = build_snapshot()
        service.materialize_article_sets(snapshot)
        # Reduce first, exactly as the Articles workflow does.
        base_length = snapshot.article_sets[0].base_length
        for member in snapshot.engineering.families[0].members:
            code = next(a.code for a in snapshot.articles if a.id == member.article_id)
            member.reduced_article = code[:base_length]

        before_codes = [a.code for a in snapshot.articles]
        before_suffixes = [a.code.split(".", 1)[1] for a in snapshot.articles]
        before_sets = deepcopy(snapshot.article_sets)
        before_reduced = [
            m.reduced_article for m in snapshot.engineering.families[0].members
        ]

        # A rejected verdict must still change nothing on the snapshot.
        result = service.validate_article_sets(snapshot)[0]
        self.assertEqual(result.status, "rejected")

        self.assertEqual([a.code for a in snapshot.articles], before_codes)
        self.assertEqual(
            [a.code.split(".", 1)[1] for a in snapshot.articles], before_suffixes
        )
        self.assertEqual(snapshot.article_sets, before_sets)
        self.assertEqual(
            [m.reduced_article for m in snapshot.engineering.families[0].members],
            before_reduced,
        )

    def test_reduced_base_stays_in_front_of_the_dot(self):
        _ctx, service = build_context(FakeCompatRepository(["1", "2"], ["1", "2"]))
        snapshot = build_snapshot()

        article_set = service.materialize_article_sets(snapshot)[0]

        self.assertEqual(article_set.base_code, "RY3XTDA")
        self.assertNotIn(".", article_set.base_code)
        for article in snapshot.articles:
            self.assertTrue(article.code.startswith(article_set.base_code))
            # The base may end AT the '.', never past it: the order-code
            # suffix generated after the dot stays whole.
            dot = article.code.index(".")
            self.assertLessEqual(article_set.base_length, dot + 1)
            self.assertEqual(
                article.code[article_set.base_length:].lstrip("."),
                article.code.split(".", 1)[1],
            )


if __name__ == "__main__":
    unittest.main()
