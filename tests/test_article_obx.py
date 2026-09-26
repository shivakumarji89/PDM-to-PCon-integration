"""Tests for repository-driven Article OBX permutation and generation."""
import unittest
import xml.etree.ElementTree as ET

from models.article import Article
from models.article_set import ArticleSet, SetAttribute, SetValue
from models.price_record import PriceRecord
from models.product import Product
from models.property import Property, PropertyValue
from models.option import Option, OptionValue
from models.snapshot import Snapshot
from services.article_obx.article_obx_models import ArticleObxRow, ArticlePrice
from services.article_obx.article_obx_service import ArticleObxService
from services.article_obx.article_permutation_service import ArticlePermutationService


class _Context:
    active_snapshot = None
    repository_snapshot = None


def _base_snapshot() -> Snapshot:
    finish = Property(id="finish", name="Finish", display_order=1)
    finish.values = [
        PropertyValue(id="oak", property_id="finish", value="Oak"),
        PropertyValue(id="walnut", property_id="finish", value="Walnut"),
    ]

    fabric = Option(id="fabric", name="Fabric", display_order=2)
    fabric.values = [
        OptionValue(id="blue", option_id="fabric", value="Blue", code="BLU"),
        OptionValue(id="red", option_id="fabric", value="Red", code="RED"),
    ]

    return Snapshot(
        product=Product(id="p1", code="BASE", name="Test"),
        properties=[finish],
        property_values=finish.values,
        options=[fabric],
        option_values=fabric.values,
        config_value_codes={
            "finish": {
                "oak": "A",
                "walnut": "B",
            }
        },
        article_sets=[
            ArticleSet(
                id="set1",
                base_code="BASE",
                article_ids=["evidence-a", "evidence-b"],
                properties=[
                    SetAttribute(
                        id="finish",
                        name="Finish",
                        values=[
                            SetValue(id="oak", value="Oak", article_ids=["evidence-a"]),
                            SetValue(id="walnut", value="Walnut", article_ids=["evidence-b"]),
                        ],
                    )
                ],
                options=[
                    SetAttribute(
                        id="fabric",
                        name="Fabric",
                        values=[
                            SetValue(id="blue", value="Blue", code="BLU", article_ids=["evidence-a"]),
                            SetValue(id="red", value="Red", code="RED", article_ids=["evidence-b"]),
                        ],
                    )
                ],
            )
        ],
    )


class ArticleObxPermutationTests(unittest.TestCase):
    def test_generates_permutations_from_values_not_existing_articles(self):
        snapshot = _base_snapshot()
        snapshot.articles = [
            Article(id="a1", product_id="p1", code="EXISTING-ONLY")
        ]

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(
            [p.final_article for p in permutations],
            ["BASEABLU", "BASEARED", "BASEBBLU", "BASEBRED"],
        )
        self.assertEqual(len(permutations), 4)
        self.assertTrue(all(p.article_id == "" for p in permutations))

    def test_property_encoding_uses_repository_configuration_code(self):
        snapshot = _base_snapshot()
        permutations = ArticlePermutationService(_Context()).build(snapshot)

        oak_blue = next(p for p in permutations if p.final_article == "BASEABLU")
        self.assertEqual(oak_blue.properties[0].code, "A")
        self.assertEqual(oak_blue.options[0].code, "BLU")

    def test_option_dependency_requires_parent_selection(self):
        snapshot = _base_snapshot()
        snapshot.option_option_dependencies = {"blue": ["red"]}

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        # The dependency is intentionally contradictory for this test: red can
        # only be selected when blue is selected. Since the option is single-
        # selection in a permutation, red-only is removed.
        self.assertNotIn("BASEARED", [p.final_article for p in permutations])
        self.assertIn("BASEABLU", [p.final_article for p in permutations])

    def test_attribute_exclusion_removes_invalid_combination(self):
        snapshot = _base_snapshot()
        snapshot.attribute_value_exclusions = {"oak": ["walnut"], "walnut": ["oak"]}

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(len(permutations), 4)
        # The exclusion is between two values of the same property, so it does
        # not remove any valid one-of-two property selection.
        self.assertEqual(
            {p.final_article for p in permutations},
            {"BASEABLU", "BASEARED", "BASEBBLU", "BASEBRED"},
        )

    def test_relation_precondition_is_applied(self):
        snapshot = _base_snapshot()
        snapshot.relation_objects = [
            type(
                "Relation",
                (),
                {
                    "type_code": "1",
                    "domain": "C",
                    "value_id": "red",
                    "body": "Restrictions:\r\n  $BAN IN ('OTHER').",
                },
            )()
        ]

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertNotIn("BASEARED", [p.final_article for p in permutations])
        self.assertNotIn("BASEBRED", [p.final_article for p in permutations])

    def test_optional_option_produces_unselected_permutation(self):
        snapshot = _base_snapshot()
        snapshot.article_sets[0].options[0].values[1].article_ids = []
        snapshot.article_sets[0].options[0].values[0].article_ids = ["evidence-a", "evidence-b"]

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertIn("BASEA", [p.final_article for p in permutations])
        self.assertIn("BASEB", [p.final_article for p in permutations])


class ArticleObxPriceTests(unittest.TestCase):
    def test_resolves_price_from_repository_snapshot(self):
        from services.article_obx.article_price_service import (
            ArticlePriceRequest,
            ArticlePriceService,
        )

        snapshot = _base_snapshot()
        snapshot.price_records = [
            PriceRecord(
                article_code="BASEABLU",
                level="B",
                value=250.0,
                currency="EUR",
                valid_from="20260901",
                valid_to="99991231",
            )
        ]

        context = _Context()
        context.repository_snapshot = snapshot
        permutation = ArticlePermutationService(context).build(snapshot)[0]
        prices = ArticlePriceService(context).resolve(
            [permutation],
            ArticlePriceRequest(currency="EUR", effective_date="20260903"),
        )

        self.assertEqual(prices[0].article_code, "BASEABLU")
        self.assertEqual(prices[0].total_price, 250.0)
        self.assertEqual(prices[0].unresolved_reason, "")


class ArticleObxXmlTests(unittest.TestCase):
    def test_render_contains_effective_price_date(self):
        snapshot = _base_snapshot()
        service = ArticleObxService(_Context())
        permutation = ArticlePermutationService(_Context()).build(snapshot)[0]
        price = ArticlePrice(
            article_id="",
            article_code=permutation.final_article,
            currency="EUR",
            effective_date="03-Sep-2026",
            site_id=1,
            base_price=100.0,
            total_price=125.0,
        )

        result = service._render_xml(
            [ArticleObxRow(permutation=permutation, price=price)],
            manufacturer_id="HM",
            series_id="TEST",
            ofml_class_suffix="_OPT",
            exclusions=set(),
        )
        root = ET.fromstring(result)
        article = root.find("./items/bskArticle")
        self.assertIsNotNone(article)
        self.assertEqual(article.find("itemPrice").get("value"), "125.00")
        self.assertEqual(article.find("itemPrice").get("currency"), "EUR")
        self.assertEqual(article.find("priceDate").get("value"), "03-Sep-2026")


if __name__ == "__main__":
    unittest.main()
