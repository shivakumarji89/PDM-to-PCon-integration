"""Tests for the isolated Article OBX generation module."""
import unittest
import xml.etree.ElementTree as ET

from models.article import Article
from models.article_set import ArticleSet
from models.option import Option
from models.option_value import OptionValue
from models.product import Product
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.article_obx.article_obx_models import ArticleObxRow, ArticlePrice
from services.article_obx.article_obx_service import ArticleObxService
from services.article_obx.article_permutation_service import ArticlePermutationService


class _Context:
    active_snapshot = None


class ArticleObxPermutationTests(unittest.TestCase):
    def test_uses_real_articles_not_cartesian_product(self):
        snapshot = Snapshot(
            product=Product(id="p1", name="Test"),
            articles=[
                Article(id="a1", product_id="p1", code="BASE-A"),
                Article(id="a2", product_id="p1", code="BASE-B"),
            ],
            properties=[
                Property(id="finish", name="Finish"),
            ],
            property_values=[
                PropertyValue(id="oak", property_id="finish", value="Oak", code="OAK"),
                PropertyValue(id="walnut", property_id="finish", value="Walnut", code="WAL"),
            ],
            article_property_value_ids={
                "a1": ["oak"],
                "a2": ["walnut"],
            },
        )

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual([p.final_article for p in permutations], ["BASE-A", "BASE-B"])
        self.assertEqual(permutations[0].properties[0].code, "OAK")
        self.assertEqual(permutations[1].properties[0].code, "WAL")

    def test_uses_materialized_article_set_base_code(self):
        snapshot = Snapshot(
            product=Product(id="p1", name="Test"),
            articles=[
                Article(id="a1", product_id="p1", code="BASE123-OAK"),
            ],
            article_sets=[
                ArticleSet(
                    id="set1",
                    base_code="BASE123",
                    article_ids=["a1"],
                )
            ],
        )

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(permutations[0].base_code, "BASE123")
        self.assertEqual(permutations[0].final_article, "BASE123-OAK")

    def test_does_not_treat_product_option_offers_as_selected_options(self):
        option = Option(id="o1", name="Finish")
        option.values = [
            OptionValue(id="ov1", option_id="o1", value="Blue", code="BLU")
        ]
        snapshot = Snapshot(
            product=Product(id="p1", name="Test"),
            articles=[Article(id="a1", product_id="p1", code="BASE-A")],
            options=[option],
            option_values=list(option.values),
            product_option_value_ids={"p1": ["ov1"]},
        )

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(permutations[0].options, ())


class ArticleObxXmlTests(unittest.TestCase):
    def test_render_contains_effective_price_date(self):
        snapshot = Snapshot(product=Product(id="p1", name="Test"))
        service = ArticleObxService(_Context())
        permutation = ArticlePermutationService(_Context()).build(
            Snapshot(
                product=snapshot.product,
                articles=[Article(id="a1", product_id="p1", code="BASE-A", name="Article")],
            )
        )[0]
        price = ArticlePrice(
            article_id="a1",
            article_code="BASE-A",
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
