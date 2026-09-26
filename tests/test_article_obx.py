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
from models.price_record import PriceRecord
from services.article_obx.article_obx_models import ArticleObxRow, ArticlePrice
from services.article_obx.article_obx_service import ArticleObxService
from services.article_obx.article_permutation_service import ArticlePermutationService


class _Context:
    active_snapshot = None
    repository_snapshot = None


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

    def test_resolves_unique_option_selection_from_article_suffix(self):
        option = Option(id="o1", name="Finish", display_order=1)
        option.values = [
            OptionValue(id="ov1", option_id="o1", value="Blue", code="BLU"),
            OptionValue(id="ov2", option_id="o1", value="Red", code="RED"),
        ]
        snapshot = Snapshot(
            product=Product(id="p1", name="Test"),
            articles=[Article(id="a1", product_id="p1", code="BASEBLU")],
            article_sets=[ArticleSet(id="set1", base_code="BASE", article_ids=["a1"])],
            options=[option],
            option_values=list(option.values),
            product_option_value_ids={"p1": ["ov1", "ov2"]},
        )

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual([v.value_id for v in permutations[0].options], ["ov1"])
        self.assertEqual(permutations[0].options[0].code, "BLU")

    def test_optional_unselected_option_is_allowed(self):
        finish = Option(id="o1", name="Finish", display_order=1)
        finish.values = [
            OptionValue(id="ov1", option_id="o1", value="Blue", code="BLU"),
        ]
        frame = Option(id="o2", name="Frame", display_order=2)
        frame.values = [
            OptionValue(id="ov2", option_id="o2", value="Black", code="BLK"),
        ]
        snapshot = Snapshot(
            product=Product(id="p1", name="Test"),
            articles=[Article(id="a1", product_id="p1", code="BASEBLU")],
            article_sets=[ArticleSet(id="set1", base_code="BASE", article_ids=["a1"])],
            options=[finish, frame],
            option_values=finish.values + frame.values,
            product_option_value_ids={"p1": ["ov1", "ov2"]},
        )

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual([v.value_id for v in permutations[0].options], ["ov1"])

    def test_option_dependency_allows_child_only_with_selected_parent(self):
        parent = Option(id="o1", name="Fabric", display_order=1)
        parent.values = [
            OptionValue(id="p1", option_id="o1", value="Standard", code="STD"),
        ]
        child = Option(id="o2", name="Finish", display_order=2)
        child.values = [
            OptionValue(id="c1", option_id="o2", value="Special", code="SPC"),
        ]
        snapshot = Snapshot(
            product=Product(id="p1", name="Test"),
            articles=[Article(id="a1", product_id="p1", code="BASESTDSPC")],
            article_sets=[ArticleSet(id="set1", base_code="BASE", article_ids=["a1"])],
            options=[parent, child],
            option_values=parent.values + child.values,
            product_option_value_ids={"p1": ["p1", "c1"]},
            option_option_dependencies={"p1": ["c1"]},
        )

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(
            [v.value_id for v in permutations[0].options],
            ["p1", "c1"],
        )

    def test_ambiguous_option_code_does_not_guess(self):
        option = Option(id="o1", name="Finish", display_order=1)
        option.values = [
            OptionValue(id="ov1", option_id="o1", value="Blue 1", code="BLU"),
            OptionValue(id="ov2", option_id="o1", value="Blue 2", code="BLU"),
        ]
        snapshot = Snapshot(
            product=Product(id="p1", name="Test"),
            articles=[Article(id="a1", product_id="p1", code="BASEBLU")],
            article_sets=[ArticleSet(id="set1", base_code="BASE", article_ids=["a1"])],
            options=[option],
            option_values=list(option.values),
            product_option_value_ids={"p1": ["ov1", "ov2"]},
        )

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(permutations[0].options, ())

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


class ArticleObxPriceTests(unittest.TestCase):
    def test_resolves_price_from_repository_snapshot(self):
        from services.article_obx.article_price_service import (
            ArticlePriceRequest,
            ArticlePriceService,
        )

        snapshot = Snapshot(
            product=Product(id="p1", name="Test"),
            articles=[
                Article(id="a1", product_id="p1", code="SUPER-1", is_super_item=True)
            ],
            price_records=[
                PriceRecord(
                    article_code="SUPER-1",
                    level="B",
                    value=250.0,
                    currency="EUR",
                    valid_from="20260901",
                    valid_to="99991231",
                ),
            ],
        )

        context = _Context()
        context.repository_snapshot = snapshot
        permutation = ArticlePermutationService(context).build(snapshot)[0]
        prices = ArticlePriceService(context).resolve(
            [permutation],
            ArticlePriceRequest(currency="EUR", effective_date="20260903"),
        )

        self.assertEqual(prices[0].total_price, 250.0)
        self.assertEqual(prices[0].unresolved_reason, "")


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
