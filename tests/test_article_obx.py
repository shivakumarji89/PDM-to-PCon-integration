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

    def test_relation_action_computes_referenced_property_code(self):
        # Mirrors the real Aeron CodeScheme grammar (docs/02_Domain/
        # Article_Encoding/Article_Encoding.md Finding 3c): the scheme
        # references a standalone computed property ("Code") whose value is
        # produced entirely by a relation action, not by any selected
        # property/option. A configuration where no action clause matches
        # leaves the computed property unresolved, so it is not a valid
        # permutation for a scheme that requires it.
        snapshot = _base_snapshot()
        snapshot.code_schemes["scheme-1"]["body"] = "Article:Code,Article:Color"
        snapshot.relation_objects = [
            type(
                "Relation",
                (),
                {
                    "type_code": "3",
                    "domain": "C",
                    "value_id": "",
                    "order": 10,
                    "body": "Code = 'Z' IF Finish = 'Oak'",
                    "name": "Aeron_Code",
                },
            )()
        ]

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        finals = [p.final_article for p in permutations]
        self.assertEqual(finals, ["BASEZC", "BASEZD"])

    def test_computed_code_uses_substr_and_self_reference(self):
        # A scaled-down instance of the real Aeron formula grammar quoted in
        # Article_Encoding.md Finding 3c: SUBSTR($BAN, start, len) for a
        # base-article prefix, then self-referencing accumulation
        # ("Code = Code + ..."), gated by an AND/IN-style condition.
        snapshot = _base_snapshot()
        snapshot.code_schemes["scheme-1"]["body"] = "Article:Code"
        snapshot.relation_objects = [
            type(
                "Relation",
                (),
                {
                    "type_code": "3",
                    "domain": "C",
                    "value_id": "",
                    "order": 10,
                    "body": (
                        "Code = SUBSTR($BAN,0,3) IF Finish IN ('Oak','Walnut'),"
                        "Code = Code + Color IF Color = 'Blue'"
                    ),
                    "name": "Computed_Code",
                },
            )()
        ]

        permutations = ArticlePermutationService(_Context()).build(snapshot)
        finals = [p.final_article for p in permutations]

        # Two semantically distinct configurations (Oak vs Walnut) that don't
        # feed the CodeScheme at all legitimately encode to the same visible
        # final article; both must be kept, not merged as duplicates.
        self.assertEqual(len(permutations), 4)
        self.assertEqual(finals.count("BASEBASC"), 2)
        self.assertEqual(finals.count("BASEBAS"), 2)

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

    def test_user_defined_scheme_base_placeholder_encodes_base_characters(self):
        snapshot = _base_snapshot()
        # '@' placeholders consume base-article characters one at a time; the
        # remaining segments carry the variant-code property references.
        snapshot.code_schemes["scheme-1"]["body"] = "@,@,@,@,Article:Finish,Article:Color"

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(
            [p.final_article for p in permutations],
            ["BASEAC", "BASEAD", "BASEBC", "BASEBD"],
        )
        self.assertEqual(permutations[0].variant_code, "AC")

    def test_user_defined_scheme_preserves_literal_space_segment(self):
        snapshot = _base_snapshot()
        snapshot.code_schemes["scheme-1"]["body"] = "Article:Finish, ,Article:Color"

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(
            [p.final_article for p in permutations],
            ["BASEA C", "BASEA D", "BASEB C", "BASEB D"],
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

        self.assertNotIn("BASEAD", [p.final_article for p in permutations])
        self.assertNotIn("BASEBD", [p.final_article for p in permutations])

    def test_parent_child_property_hierarchy_prunes_invalid_combinations(self):
        # (SPECIFIED Parent) AND (Parent IN ('B')) — the real validity-relation
        # grammar (Article_Encoding.md Finding 11) — gates a child value so it
        # is only ever generated alongside its required parent selection.
        snapshot = _base_snapshot()
        parent = Property(id="parent", name="Parent", display_order=0)
        parent.values = [
            PropertyValue(id="parent-a", property_id="parent", value="A", code="PA"),
            PropertyValue(id="parent-b", property_id="parent", value="B", code="PB"),
        ]
        child = Property(id="child", name="Child", display_order=1)
        child.values = [
            PropertyValue(id="child-x", property_id="child", value="X", code="CX"),
            PropertyValue(id="child-y", property_id="child", value="Y", code="CY"),
        ]
        snapshot.properties = [parent, child]
        snapshot.property_values = parent.values + child.values
        engineering_class = EngineeringClass(id="mdb:class:1", name="Article")
        engineering_class.properties = [
            ClassPropertyAssignment(property_id="parent", property_name="Parent"),
            ClassPropertyAssignment(property_id="child", property_name="Child"),
        ]
        snapshot.engineering = Engineering(classes=[engineering_class])
        snapshot.code_schemes["scheme-1"]["body"] = "Article:Parent,Article:Child"
        snapshot.relation_objects = [
            type(
                "Relation",
                (),
                {
                    "type_code": "2",
                    "domain": "C",
                    "value_id": "child-y",
                    "order": 5,
                    "body": "Restrictions:\r\n  (SPECIFIED Parent) AND (Parent IN ('B')).",
                    "name": "Child_Requires_Parent_B",
                },
            )()
        ]

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        configs = {
            (p.properties[0].value, p.properties[1].value) for p in permutations
        }
        self.assertEqual(configs, {("A", "X"), ("B", "X"), ("B", "Y")})

    def test_transitive_option_dependency_resolves_full_chain(self):
        from models.option import Option
        from models.option_value import OptionValue

        snapshot = _base_snapshot()
        opt_a = Option(id="opt-a", name="OptA", display_order=1)
        opt_a.values = [OptionValue(id="opt-a-v", option_id="opt-a", value="A", code="OA")]
        opt_b = Option(id="opt-b", name="OptB", display_order=2)
        opt_b.values = [OptionValue(id="opt-b-v", option_id="opt-b", value="B", code="OB")]
        opt_c = Option(id="opt-c", name="OptC", display_order=3)
        opt_c.values = [OptionValue(id="opt-c-v", option_id="opt-c", value="C", code="OC")]
        snapshot.options = [opt_a, opt_b, opt_c]
        snapshot.product_option_value_ids = {
            "mdb:package:1": ["opt-a-v", "opt-b-v", "opt-c-v"]
        }
        # oak -> opt-a-v -> (chain) opt-b-v -> opt-c-v
        snapshot.attribute_option_dependencies = {"oak": ["opt-a-v"]}
        snapshot.option_option_dependencies = {
            "opt-a-v": ["opt-b-v"],
            "opt-b-v": ["opt-c-v"],
        }
        snapshot.code_schemes["scheme-1"]["body"] = (
            "Article:Finish,Article:Color,Article:OptA,Article:OptB,Article:OptC"
        )

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        oak_perms = [p for p in permutations if p.properties[0].value == "Oak"]
        self.assertTrue(oak_perms)
        for perm in oak_perms:
            option_names = {v.name for v in perm.options}
            self.assertEqual(option_names, {"OptA", "OptB", "OptC"})
        walnut_perms = [p for p in permutations if p.properties[0].value == "Walnut"]
        for perm in walnut_perms:
            self.assertEqual(perm.options, ())

    def test_varcond_extraction_sets_variant_condition(self):
        snapshot = _base_snapshot()
        snapshot.relation_objects = [
            type(
                "Relation",
                (),
                {
                    "type_code": "3",
                    "domain": "P",
                    "value_id": "",
                    "order": 1,
                    "body": "$VARCOND = 'AF'",
                    "name": "Price_VarCond",
                },
            )()
        ]

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertTrue(permutations)
        self.assertTrue(all(p.variant_condition == "AF" for p in permutations))

    def test_build_is_deterministic_across_runs(self):
        snapshot = _base_snapshot()

        first = ArticlePermutationService(_Context()).build(snapshot)
        second = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(
            [(p.final_article, tuple(v.value_id for v in p.properties)) for p in first],
            [(p.final_article, tuple(v.value_id for v in p.properties)) for p in second],
        )

    def test_no_duplicate_configuration_identities(self):
        snapshot = _base_snapshot()

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        keys = [
            (tuple(v.value_id for v in p.properties), tuple(v.value_id for v in p.options))
            for p in permutations
        ]
        self.assertEqual(len(keys), len(set(keys)))

    def test_article_with_no_properties_yields_single_permutation(self):
        snapshot = _base_snapshot()
        snapshot.properties = []
        snapshot.property_values = []
        snapshot.code_schemes = {}
        snapshot.article_code_scheme_ids = {}

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(len(permutations), 1)
        self.assertEqual(permutations[0].properties, ())
        self.assertEqual(permutations[0].options, ())
        self.assertEqual(permutations[0].final_article, "BASE")

    def test_multiple_articles_use_their_own_code_scheme(self):
        snapshot = _base_snapshot()
        snapshot.articles = [
            Article(id="mdb:article:100", product_id="mdb:package:1", code="ONE", source="MDB"),
            Article(id="mdb:article:200", product_id="mdb:package:1", code="TWO", source="MDB"),
        ]
        snapshot.article_class_ids = {
            "mdb:article:100": ["mdb:class:1"],
            "mdb:article:200": ["mdb:class:1"],
        }
        snapshot.article_code_scheme_ids = {
            "mdb:article:100": "scheme-1",
            "mdb:article:200": "scheme-2",
        }
        snapshot.code_schemes["scheme-2"] = {"name": "TWO", "body": "Article:Color"}

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        one_finals = {p.final_article for p in permutations if p.base_code == "ONE"}
        two_finals = {p.final_article for p in permutations if p.base_code == "TWO"}
        self.assertEqual(one_finals, {"ONEAC", "ONEAD", "ONEBC", "ONEBD"})
        self.assertEqual(two_finals, {"TWOC", "TWOD"})

    def test_malformed_relation_action_is_skipped_not_fatal(self):
        # A SUBSTR call with non-numeric arguments cannot be evaluated; the
        # clause must be skipped, not crash the whole build or the whole
        # article — other, unrelated permutations still generate normally.
        snapshot = _base_snapshot()
        snapshot.relation_objects = [
            type(
                "Relation",
                (),
                {
                    "type_code": "3",
                    "domain": "C",
                    "value_id": "",
                    "order": 1,
                    "body": "Code = SUBSTR($BAN,x,y) IF Finish = 'Oak'",
                    "name": "Malformed_Code",
                },
            )()
        ]

        try:
            permutations = ArticlePermutationService(_Context()).build(snapshot)
        except Exception as error:  # pragma: no cover - the point of the test
            self.fail(f"build() must not raise on a malformed relation: {error}")

        # The scheme doesn't reference the malformed "Code" property, so every
        # permutation is unaffected.
        self.assertEqual(len(permutations), 4)


class ArticleObxRealCodeSchemeFidelityTests(unittest.TestCase):
    """Validate the encoding grammar against a real repository CodeScheme
    string, not a synthetic one.

    The scheme body below is quoted verbatim from a real, reachable Herman
    Miller OFML repository's Cosm ``ocd_codescheme.csv`` row (SchemeID
    ``U00000000000006297``), as recorded in
    docs/02_Domain/Article_Encoding/Article_Encoding.md Finding 3b:

        @,@,@,COSM_NORMAL:Assembly_Option,COSM_NORMAL:Back_Height,
        COSM_NORMAL:Height_Adjustment,COSM_NORMAL:Tilt,COSM_NORMAL:Seat_Depth,
        COSM_NORMAL:Arms, ,COSM_NORMAL:Frame_Finish, ,COSM_NORMAL:Chassis_Finish,
        , COSM_NORMAL:Base_Finish, ,COSM_NORMAL:Castors_Glides,
        ,COSM_NORMAL:Armpad_Finish_H, ,COSM_NORMAL:Intercept_Finish

    (only the leading ``Scheme`` column of the CSV row; the base article code
    and property codes below are illustrative, since no real Cosm article/
    property CSV rows were available to this session — the *grammar* is real
    evidence, the *data* is a minimal stand-in for it.)
    """

    _SCHEME_BODY = (
        "@,@,@,"
        "COSM_NORMAL:Assembly_Option,COSM_NORMAL:Back_Height,"
        "COSM_NORMAL:Height_Adjustment,COSM_NORMAL:Tilt,COSM_NORMAL:Seat_Depth,"
        "COSM_NORMAL:Arms, ,COSM_NORMAL:Frame_Finish, ,COSM_NORMAL:Chassis_Finish,"
        " ,COSM_NORMAL:Base_Finish, ,COSM_NORMAL:Castors_Glides,"
        " ,COSM_NORMAL:Armpad_Finish_H, ,COSM_NORMAL:Intercept_Finish"
    )

    @staticmethod
    def _single_value_property(name: str, code: str) -> Property:
        prop = Property(id=name.lower(), name=name)
        prop.values = [PropertyValue(id=f"{name.lower()}-v", property_id=name.lower(), value=name, code=code)]
        return prop

    def _cosm_like_snapshot(self) -> Snapshot:
        names_codes = [
            ("Assembly_Option", "A1"), ("Back_Height", "B1"),
            ("Height_Adjustment", "H1"), ("Tilt", "T1"), ("Seat_Depth", "D1"),
            ("Arms", "R1"), ("Frame_Finish", "F1"), ("Chassis_Finish", "C1"),
            ("Base_Finish", "S1"), ("Castors_Glides", "G1"),
            ("Armpad_Finish_H", "M1"), ("Intercept_Finish", "I1"),
        ]
        properties = [self._single_value_property(name, code) for name, code in names_codes]

        engineering_class = EngineeringClass(id="mdb:class:cosm", name="COSM_NORMAL")
        engineering_class.properties = [
            ClassPropertyAssignment(property_id=prop.id, property_name=prop.name)
            for prop in properties
        ]

        return Snapshot(
            product=Product(id="mdb:package:cosm", code="COSM", name="Cosm"),
            articles=[
                Article(
                    id="mdb:article:cosm",
                    product_id="mdb:package:cosm",
                    code="COS",
                    name="Cosm base article",
                    source="MDB",
                )
            ],
            properties=properties,
            property_values=[v for prop in properties for v in prop.values],
            article_class_ids={"mdb:article:cosm": ["mdb:class:cosm"]},
            article_code_scheme_ids={"mdb:article:cosm": "scheme-cosm"},
            code_schemes={"scheme-cosm": {"name": "COSM_NORMAL", "body": self._SCHEME_BODY}},
            engineering=Engineering(classes=[engineering_class]),
        )

    def test_real_cosm_codescheme_grammar_encodes_correctly(self):
        snapshot = self._cosm_like_snapshot()

        permutations = ArticlePermutationService(_Context()).build(snapshot)

        self.assertEqual(len(permutations), 1)
        permutation = permutations[0]
        # 3x '@' consumes "C", "O", "S" from the base code; the next six
        # properties concatenate with no separator; each remaining property
        # is preceded by the scheme's own literal space token.
        self.assertEqual(
            permutation.final_article,
            "COSA1B1H1T1D1R1 F1 C1 S1 G1 M1 I1",
        )
        self.assertEqual(
            permutation.variant_code,
            "A1B1H1T1D1R1 F1 C1 S1 G1 M1 I1",
        )


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

    def test_generate_runs_full_permutation_price_obx_pipeline(self):
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

        result = ArticleObxService(context).generate(
            currency="EUR", effective_date="20260903", series_id="TEST"
        )

        self.assertEqual(result.warnings, [])
        self.assertEqual(len(result.rows), 4)
        codes = {row.permutation.final_article for row in result.rows}
        self.assertEqual(codes, {"BASEAC", "BASEAD", "BASEBC", "BASEBD"})
        root = ET.fromstring(result.xml)
        self.assertEqual(len(root.findall("./items/bskArticle")), 4)


if __name__ == "__main__":
    unittest.main()
