"""ProductRange completeness: the population a candidate family is drawn from.

``dbo.ProductsList`` filters the COMPLETE legacy-eligible population of one
ProductRange - every Product with at least one released Item, or flagged
``NewProduct``. A session that holds only part of a range therefore asks the
boundary a question it cannot answer: the Products nobody loaded come back as
over-matches no matter how correct the grouping is.

These tests cover the two halves of the fix: reporting the shortfall per range
(:meth:`PDMService.product_range_gaps`) and closing it through the ordinary
merge path (:meth:`PDMService.complete_product_ranges`).
"""
import unittest
from types import SimpleNamespace

from models.article import Article
from models.product import Product
from models.snapshot import Snapshot
from services.pdm_service import PDMService, ProductLoadResult


class FakeCompatRepository:
    """The eligible population of each range, without a database."""

    def __init__(self, population_by_range, range_of_product, names):
        self._population = population_by_range
        self._range_of = range_of_product
        self._names = names
        self.calls = []

    def fetch_range_population_for_products(self, product_ids, connection=None):
        self.calls.append(sorted(str(p) for p in product_ids))
        ranges = {
            self._range_of[str(pid)]
            for pid in product_ids
            if str(pid) in self._range_of
        }
        return [
            SimpleNamespace(
                ProductId=product_id,
                ProductRangeId=range_id,
                RangeName=self._names[range_id],
            )
            for range_id in sorted(ranges)
            for product_id in self._population[range_id]
        ]


def build_service(repository):
    """A PDMService with the compatibility read stubbed and no database."""
    service = PDMService.__new__(PDMService)
    service.context = SimpleNamespace()
    service._repository = None
    service.merged = []

    def add_family_to_session(products, family_name="", reporter=None):
        service.merged.append(
            (family_name, tuple(str(p.id) for p in products))
        )
        return ProductLoadResult(True, "merged", service.snapshot, [])

    service.add_family_to_session = add_family_to_session
    service._compat_repository = repository
    return service


def build_snapshot(product_ids):
    snapshot = Snapshot(id="s1")
    snapshot.product = Product(id=product_ids[0], catalogue_id="764")
    snapshot.articles = [
        Article(id=f"a{pid}", product_id=pid, code=f"C{pid}")
        for pid in product_ids
    ]
    return snapshot


class ProductRangeGapTests(unittest.TestCase):
    def setUp(self):
        # Range 6511 holds four eligible Products; range 5512 holds one.
        self.repository = FakeCompatRepository(
            population_by_range={"6511": ["1", "2", "3", "4"], "5512": ["9"]},
            range_of_product={
                "1": "6511", "2": "6511", "3": "6511", "4": "6511", "9": "5512",
            },
            names={"6511": "Nevi Desks", "5512": "Wire Management"},
        )

    def gaps(self, service, snapshot):
        return service.product_range_gaps(snapshot)

    def make(self, product_ids):
        service = build_service(self.repository)
        snapshot = build_snapshot(product_ids)
        service.snapshot = snapshot
        return service, snapshot

    def test_a_partly_loaded_range_reports_exactly_what_is_missing(self):
        service, snapshot = self.make(["1", "2"])

        gap = {g.product_range_id: g for g in self.gaps(service, snapshot)}["6511"]

        self.assertEqual(gap.range_name, "Nevi Desks")
        self.assertEqual(gap.loaded_product_ids, ("1", "2"))
        self.assertEqual(gap.missing_product_ids, ("3", "4"))
        self.assertEqual(gap.eligible_count, 4)
        self.assertFalse(gap.is_complete)

    def test_a_fully_loaded_range_is_complete(self):
        service, snapshot = self.make(["9"])

        gap = {g.product_range_id: g for g in self.gaps(service, snapshot)}["5512"]

        self.assertEqual(gap.missing_product_ids, ())
        self.assertTrue(gap.is_complete)

    def test_every_range_in_the_session_is_reported(self):
        service, snapshot = self.make(["1", "9"])

        gaps = self.gaps(service, snapshot)

        self.assertEqual(
            {g.product_range_id: g.is_complete for g in gaps},
            {"6511": False, "5512": True},
        )

    def test_an_empty_snapshot_reports_nothing(self):
        service, _snapshot = self.make(["1"])

        self.assertEqual(self.gaps(service, None), ())
        self.assertEqual(self.gaps(service, Snapshot(id="empty")), ())


class CompleteProductRangesTests(ProductRangeGapTests):
    def test_the_missing_products_are_merged_through_the_normal_path(self):
        service, snapshot = self.make(["1", "2"])

        result = service.complete_product_ranges(snapshot)

        self.assertTrue(result.ok)
        self.assertEqual(len(service.merged), 1)
        _name, merged_ids = service.merged[0]
        # Exactly the shortfall - nothing already loaded is loaded twice.
        self.assertEqual(merged_ids, ("3", "4"))
        self.assertIn("Nevi Desks", result.message)

    def test_a_completed_product_joins_the_sessions_catalogue(self):
        service, snapshot = self.make(["1", "2"])
        captured = []
        service.add_family_to_session = lambda products, family_name="", reporter=None: (
            captured.extend(products)
            or ProductLoadResult(True, "merged", snapshot, [])
        )

        service.complete_product_ranges(snapshot)

        # Catalogue-gated options must resolve the same way they did for the
        # Products already in the session.
        self.assertEqual({p.catalogue_id for p in captured}, {"764"})
        self.assertEqual({p.range_name for p in captured}, {"Nevi Desks"})

    def test_completion_can_be_limited_to_one_range(self):
        service, snapshot = self.make(["1", "9"])

        service.complete_product_ranges(snapshot, product_range_ids=["5512"])

        # 5512 is already complete and 6511 was not asked for, so there is
        # nothing to do - and nothing is merged speculatively.
        self.assertEqual(service.merged, [])

    def test_an_already_complete_session_loads_nothing(self):
        service, snapshot = self.make(["9"])

        result = service.complete_product_ranges(snapshot)

        self.assertTrue(result.ok)
        self.assertEqual(service.merged, [])
        self.assertIn("already complete", result.message)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
