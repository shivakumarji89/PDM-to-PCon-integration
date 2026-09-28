"""Tests for repository-driven Article OBX permutation and generation."""
import unittest
import xml.etree.ElementTree as ET

from models.article import Article
from models.price_record import PriceRecord
from models.product import Product
from models.property import Property, PropertyValue
from models.snapshot import Snapshot
from models.engineering import Engineering
from models.engineering_class import EngineeringClass, ClassPropertyAssignment
from services.article_obx.article_obx_models import ArticleObxRow, ArticlePrice
from services.article_obx.article_obx_service import ArticleObxService
from services.article_obx.article_permutation_service import ArticlePermutationService


class _Context:
    active_snapshot = None
    repository_snapshot = None


def _base_snapshot() -> Snapshot:
    finish = Property(id="finish", name="Finish", display_order=1)
    finish.values = [
        PropertyValue(id="oak", property_id="finish", value="Oak", code="A"),
        PropertyValue(id="walnut", property_id="finish", value="Walnut", code="B"),
    ]

    color = Property(id="color", name="Color", display_order=2)
    color.values = [
        PropertyValue(id="blue", property_id="color", value="Blue", code="C"),
        PropertyValue(id="red", property_id="color", value="Red", code="D"),
    ]

    engineering_class = EngineeringClass(id="mdb:class:1", name="Article")
    engineering_class.properties = [
        ClassPropertyAssignment(property_id="finish", property_name="Finish"),
        ClassPropertyAssignment(property_id="color", property_name="Color"),
    ]

    return Snapshot(
        product=Product(id="mdb:package:1", code="TEST", name="Test"),
        articles=[
            Article(
                id="mdb:article:100",
                product_id="mdb:package:1",
                code="BASE",
                name="Base article",
                source="MDB",
            )
        ],
        properties=[finish, color],
        property_values=finish.values + color.values,
        article_class_ids={"mdb:article:100": ["mdb:class:1"]},
        article_code_scheme_ids={"mdb:article:100": "scheme-1"},
        code_schemes={
            "scheme-1": {
                "name": "BASE",
                "body": "Article:Finish,Article:Color",
            }
        },
        engineering=Engineering(classes=[engineering_class]),
    )


class ArticleObxPermutationTests(unittest.TestCase):
    def test_generates_permutations_from_repository_values(self):
        snapshot = _base_snapshot()

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(
            [p.final_article for p in permutations],
            ["BASEAC", "BASEAD", "BASEBC", "BASEBD"],
        )
        self.assertEqual(len(permutations), 4)
        self.assertEqual(permutations[0].article_id, "mdb:article:100")

    def test_uses_code_scheme_property_order_for_encoding(self):
        snapshot = _base_snapshot()
        snapshot.code_schemes["scheme-1"]["body"] = "Article:Color,Article:Finish"

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(
            [p.final_article for p in permutations],
            ["BASECA", "BASECB", "BASEDA", "BASEDB"],
        )

    def test_codescheme_preserves_literal_separator(self):
        snapshot = _base_snapshot()
        snapshot.code_schemes["scheme-1"]["body"] = "Article:Finish,-,Article:Color"

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(
            [p.final_article for p in permutations],
            ["BASEA-C", "BASEA-D", "BASEB-C", "BASEB-D"],
        )
        self.assertEqual(permutations[0].variant_code, "A-C")

    def test_predefined_codescheme_uses_repository_separators(self):
        snapshot = _base_snapshot()
        snapshot.code_schemes["scheme-1"] = {
            "name": "PREDEFINED",
            "VarCodeSep": " ",
            "ValueSep": ".",
        }

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(
            [p.final_article for p in permutations],
            ["BASE A.C", "BASE A.D", "BASE B.C", "BASE B.D"],
        )
        self.assertEqual(permutations[0].variant_code, "A.C")

    def test_relation_action_changes_encoded_code(self):
        snapshot = _base_snapshot()
        snapshot.relation_objects = [
            type(
                "Relation",
                (),
                {
                    "type_code": "3",
                    "domain": "C",
                    "value_id": "",
                    "order": 10,
                    "body": "CodeFinish = 'Z' IF Finish = 'Oak'",
                    "name": "A_Code_Finish",
                },
            )()
        ]

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertIn("BASEZC", [p.final_article for p in permutations])
        self.assertIn("BASEZD", [p.final_article for p in permutations])

    def test_independent_option_is_not_hidden_by_another_option_dependency(self):
        from models.option import Option
        from models.option_value import OptionValue

        snapshot = _base_snapshot()
        fr_option = Option(id="fr-option", name="FR_Option", display_order=3)
        fr_option.values = [
            OptionValue(id="fr", option_id="fr-option", value="FR", code="FR"),
        ]
        fabric_colour = Option(id="fabric-colour", name="Fabric_Colour", display_order=4)
        fabric_colour.values = [
            OptionValue(id="fabric-red", option_id="fabric-colour", value="Red", code="R1"),
            OptionValue(id="fabric-blue", option_id="fabric-colour", value="Blue", code="B1"),
        ]
        snapshot.options = [fr_option, fabric_colour]
        snapshot.product_option_value_ids = {
            "mdb:package:1": ["fr", "fabric-red", "fabric-blue"]
        }
        # FR is specifically an enabled FR_Option value. Fabric_Colour is an
        # independently offered option and must remain a separate dimension.
        snapshot.attribute_option_dependencies = {"oak": ["fr"]}
        snapshot.option_option_dependencies = {}

        snapshot.code_schemes["scheme-1"]["body"] = (
            "Article:Finish,Article:Color,Article:FR_Option,Article:Fabric_Colour"
        )

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(
            [p.final_article for p in permutations],
            [
                "BASEACFRB1",
                "BASEACFRR1",
                "BASEADFRB1",
                "BASEADFRR1",
                "BASEBCFRB1",
                "BASEBCFRR1",
                "BASEBDFRB1",
                "BASEBDFRR1",
            ],
        )
        self.assertTrue(
            all(
                {value.name for value in p.options}
                == {"FR_Option", "Fabric_Colour"}
                for p in permutations
            )
        )

    def test_dependent_option_values_follow_selected_property(self):
        from models.option import Option
        from models.option_value import OptionValue

        snapshot = _base_snapshot()
        fabric = Option(id="fabric", name="Fabric", display_order=3)
        fabric.values = [
            OptionValue(id="fabric-a", option_id="fabric", value="Fabric A", code="F1"),
            OptionValue(id="fabric-b", option_id="fabric", value="Fabric B", code="F2"),
        ]
        snapshot.options = [fabric]
        snapshot.product_option_value_ids = {
            "mdb:package:1": ["fabric-a", "fabric-b"]
        }
        snapshot.attribute_option_dependencies = {
            "oak": ["fabric-a"],
            "walnut": ["fabric-b"],
        }
        snapshot.code_schemes["scheme-1"]["body"] = "Article:Finish,Article:Color,Article:Fabric"

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        finals = [p.final_article for p in permutations]
        self.assertEqual(
            finals,
            ["BASEACF1", "BASEADF1", "BASEBCF2", "BASEBDF2"],
        )
        self.assertTrue(all(p.options for p in permutations))

    def test_artbase_restriction_limits_values(self):
        snapshot = _base_snapshot()
        snapshot.art_base = {
            "BASE": {
                "finish": ["oak"],
                "color": ["blue", "red"],
            }
        }

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(
            [p.final_article for p in permutations],
            ["BASEAC", "BASEAD"],
        )

    def test_attribute_exclusion_removes_invalid_combination(self):
        snapshot = _base_snapshot()
        snapshot.attribute_value_exclusions = {
            "oak": ["red"],
            "red": ["oak"],
        }

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertNotIn("BASEAD", [p.final_article for p in permutations])
        self.assertIn("BASEAC", [p.final_article for p in permutations])

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

        self.assertNotIn("BASEAD", [p.final_article for p in permutations])
        self.assertNotIn("BASEBD", [p.final_article for p in permutations])


class ArticleObxPriceTests(unittest.TestCase):
    def test_resolves_price_from_repository_snapshot(self):
        from services.article_obx.article_price_service import (
            ArticlePriceRequest,
            ArticlePriceService,
        )

        snapshot = _base_snapshot()
        snapshot.price_records = [
            PriceRecord(
                article_code="BASE",
                variant_condition="",
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

        self.assertEqual(prices[0].article_code, "BASEAC")
        self.assertEqual(prices[0].total_price, 250.0)
        self.assertEqual(prices[0].unresolved_reason, "")


class ArticleObxXmlTests(unittest.TestCase):
    def test_render_contains_effective_price_date(self):
        snapshot = _base_snapshot()
        service = ArticleObxService(_Context())
        permutation = ArticlePermutationService(_Context()).build(snapshot)[0]
        price = ArticlePrice(
            article_id=permutation.article_id,
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
