import unittest
from types import SimpleNamespace

from services.engineering.engineering_reduction_service import (
    EngineeringReductionService,
)


class PDMReductionParityTests(unittest.TestCase):
    def test_item_level_attribute_values_override_product_values_per_attribute(self):
        snapshot = SimpleNamespace(
            properties=[
                SimpleNamespace(
                    id="A",
                    name="Side A",
                    has_dependent_options=False,
                    values=[
                        SimpleNamespace(id="A1", value="Single", code=""),
                        SimpleNamespace(id="A2", value="Back", code=""),
                    ],
                ),
                SimpleNamespace(
                    id="B",
                    name="Side B",
                    has_dependent_options=False,
                    values=[
                        SimpleNamespace(id="B1", value="Single", code=""),
                        SimpleNamespace(id="B2", value="Back", code=""),
                    ],
                ),
            ],
            product_property_value_ids={"P1": ["A1", "B1"]},
            article_property_value_ids={
                "I1": ["A1"],
                "I2": ["A2", "B2"],
            },
            articles=[
                SimpleNamespace(id="I1", product_id="P1"),
                SimpleNamespace(id="I2", product_id="P1"),
            ],
        )

        service = EngineeringReductionService.__new__(EngineeringReductionService)
        classes = service.classify_by_properties(snapshot)

        signatures = {tuple(c.property_names): tuple(c.article_ids) for c in classes}
        self.assertIn(("Side A",), signatures)
        self.assertIn(("Side A", "Side B"), signatures)
        self.assertEqual(signatures[("Side A",)], ("I1",))
        self.assertEqual(signatures[("Side A", "Side B")], ("I2",))

    def test_set_attributes_uses_item_values_and_product_fallback(self):
        result = EngineeringReductionService._set_attributes(
            ["I1"],
            {"I1": "P1"},
            {"P1": ["A1", "B1"]},
            {
                "A1": ("A", "Side A", "Single", ""),
                "A2": ("A", "Side A", "Back", ""),
                "B1": ("B", "Side B", "Single", ""),
                "B2": ("B", "Side B", "Back", ""),
            },
            article_value_ids={"I1": ["A2", "B2"]},
        )

        self.assertEqual([p.name for p in result], ["Side A", "Side B"])
        self.assertEqual([v.value for v in result[0].values], ["Back"])
        self.assertEqual([v.value for v in result[1].values], ["Back"])

    def test_pdm_article_prefix_length_is_used_before_heuristic_length(self):
        snapshot = SimpleNamespace(
            properties=[],
            articles=[
                SimpleNamespace(id="I1", product_id="P1", code="ABC123"),
                SimpleNamespace(id="I2", product_id="P1", code="ABC456"),
            ],
            product_property_value_ids={"P1": []},
            article_property_value_ids={"I1": [], "I2": []},
            product_option_value_ids={},
            article_prefix_length={"I1": 3, "I2": 3},
            base_length_overrides={},
            article_sets=[],
            engineering_class_service=None,
        )
        snapshot.engineering_class_service = SimpleNamespace(config_code_layout=lambda _s: {})

        service = EngineeringReductionService.__new__(EngineeringReductionService)
        service.context = snapshot

        sets = service.materialize_article_sets(snapshot)

        self.assertEqual(len(sets), 1)
        self.assertEqual(sets[0].base_length, 3)
        self.assertEqual(sets[0].base_code, "ABC")


if __name__ == "__main__":
    unittest.main()
