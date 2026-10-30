"""Snapshot-path integration of the OCD engine: relations, VARCOND pricing, OBX XML.

The synthetic tests exercise ``ArticlePermutationService`` / ``ArticlePriceService`` /
``ArticleObxService`` through the controlled adapter; the Dalby test feeds real OCD data
through the same Snapshot path and compares with real pCon-resolved OBX files (skipped
when those are not on the machine).
"""
import glob
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest

from models.article import Article
from models.engineering import Engineering
from models.engineering_class import ClassPropertyAssignment, EngineeringClass
from models.price_record import PriceRecord
from models.product import Product
from models.property import Property, PropertyValue
from models.snapshot import Snapshot
from services.article_obx.article_obx_service import (
    FINAL_OMIT, FINAL_PREDICTED, FINAL_SENTINEL, ArticleObxService,
)
from services.article_obx.article_permutation_service import ArticlePermutationService
from services.article_obx.article_price_service import ArticlePriceRequest, ArticlePriceService
from services.obx_service import OBX_SENTINEL, OBXService
from services.ocd_engine import diagnostics as dg


class _Context:
    active_snapshot = None
    mdb_import_snapshot = None
    qa_snapshot = None


def relation(body, type_code="1", domain="C", value_id="", property_id="", name="R", order=10, **extra):
    return SimpleNamespace(body=body, type_code=type_code, domain=domain, value_id=value_id,
                           property_id=property_id, name=name, order=order, **extra)


def snapshot(props, relations=(), prices=(), scheme=None, base="BASE"):
    """``props`` = ``{name: [(value_id, value, code), ...]}`` in display order."""
    scheme = scheme or ",".join(f"Article:{name}" for name in props)
    properties = []
    for index, (name, values) in enumerate(props.items()):
        prop = Property(id=name.lower(), name=name, display_order=index)
        prop.values = [PropertyValue(id=vid, property_id=name.lower(), value=value, code=code)
                       for vid, value, code in values]
        properties.append(prop)
    cls = EngineeringClass(id="c1", name="Article")
    cls.properties = [ClassPropertyAssignment(property_id=p.id, property_name=p.name) for p in properties]
    return Snapshot(
        product=Product(id="p1", code="TEST", name="Test"),
        articles=[Article(id="a1", product_id="p1", code=base, name="Base", source="MDB")],
        properties=properties, property_values=[v for p in properties for v in p.values],
        article_class_ids={"a1": ["c1"]}, article_code_scheme_ids={"a1": "s1"},
        code_schemes={"s1": {"name": "S", "body": scheme}},
        engineering=Engineering(classes=[cls]), relation_objects=list(relations), price_records=list(prices),
    )


def build(snap, **attrs):
    service = ArticlePermutationService(_Context())
    for key, value in attrs.items():
        setattr(service, key, value)
    return service.build(snap), service


def configs(perms):
    return {tuple(v.value for v in p.properties) for p in perms}


TWO_BY_TWO = {"Top": [("t1", "Q75", "Q75"), ("t2", "OAK", "OAK")],
              "Mat": [("m1", "MDF", "MDF"), ("m2", "OAK", "OAK")]}


class AdapterRelationTests(unittest.TestCase):
    def test_cascade_binds_via_value_ids_with_multi_parent_condition(self):
        extra = dict(TWO_BY_TWO, Edge=[("e1", "BSE", "BSE"), ("e2", "WSE", "WSE")])
        rels = [relation("(SPECIFIED Top) AND (Top IN ('Q75'))", value_id="m1", property_id="mat"),
                relation("(SPECIFIED Top) AND (Top IN ('OAK')) AND Edge = 'BSE'", value_id="m2", property_id="mat")]
        perms, _ = build(snapshot(extra, rels))
        got = {tuple(sorted((v.name, v.value) for v in p.properties)) for p in perms}

        def cfg(top, edge, mat=None):
            items = [("Top", top), ("Edge", edge)] + ([("Mat", mat)] if mat else [])
            return tuple(sorted(items))

        # MDF needs Top=Q75; OAK needs Top=OAK *and* Edge=BSE (two parents); otherwise Mat has no valid value
        self.assertEqual(got, {cfg("Q75", "BSE", "MDF"), cfg("Q75", "WSE", "MDF"),
                               cfg("OAK", "BSE", "OAK"), cfg("OAK", "WSE")})

    def test_property_level_precondition_hides_property(self):
        rels = [relation("$BAN IN ('OTHER')", property_id="mat")]
        perms, _ = build(snapshot(TWO_BY_TWO, rels))
        self.assertEqual(len(perms), 2)                              # Mat hidden: one Top choice each
        self.assertTrue(all(len(p.properties) == 1 for p in perms))

    def test_or_and_not_in_are_supported(self):
        rels = [relation("Top NOT IN ('Q75') OR Top = 'Q75'", value_id="m1", property_id="mat"),
                relation("Top NOT IN ('Q75')", value_id="m2", property_id="mat")]
        perms, _ = build(snapshot(TWO_BY_TWO, rels))
        self.assertEqual(configs(perms), {("Q75", "MDF"), ("OAK", "MDF"), ("OAK", "OAK")})

    def test_article_codes_binding_restricts_a_relation_to_its_articles(self):
        rels = [relation("$BAN IN ('NOPE')", value_id="m2", property_id="mat", article_codes=["OTHER"])]
        perms, _ = build(snapshot(TWO_BY_TWO, rels))
        self.assertEqual(len(perms), 4)                              # bound to another article: ignored here

    def test_unparsable_relation_is_reported_not_fatal(self):
        rels = [relation("Top = = 'x'", value_id="m1", property_id="mat", name="BROKEN")]
        perms, service = build(snapshot(TWO_BY_TWO, rels))
        self.assertEqual(len(perms), 4)
        self.assertEqual([d.relation for d in service.last_diagnostics.by_code(dg.RELATION_PARSE_ERROR)], ["BROKEN"])

    def test_constraint_with_table_call(self):
        table = SimpleNamespace(name="T1", lines=[{"COL_TOP": "Q75", "COL_MAT": "MDF"}, {"COL_TOP": "OAK", "COL_MAT": "OAK"}])
        body = "Objects:\r\n  x IS_A Article.\r\nRestrictions:\r\n  TABLE T1 ( COL_TOP = x.Top, COL_MAT = x.Mat )."
        snap = snapshot(TWO_BY_TWO, [relation(body, type_code="4")])
        snap.value_tables = [table]
        perms, _ = build(snap)
        self.assertEqual(configs(perms), {("Q75", "MDF"), ("OAK", "OAK")})


class VarcondPricingTests(unittest.TestCase):
    PRICE = relation("$VARCOND = '6695=' + Top, $VARCOND = '6699=' + Mat", type_code="3", domain="P")

    @staticmethod
    def price(variant_condition="", level="B", value=100.0, currency="EUR", start="20250101"):
        return PriceRecord(article_code="BASE", variant_condition=variant_condition, level=level, value=value,
                           currency=currency, valid_from=start, valid_to="99991231")

    def test_every_varcond_key_is_collected_in_assignment_order(self):
        perms, _ = build(snapshot(TWO_BY_TWO, [self.PRICE]))
        first = next(p for p in perms if p.properties[0].value == "Q75" and p.properties[1].value == "MDF")
        self.assertEqual(first.variant_conditions, ("6695=Q75", "6699=MDF"))
        self.assertEqual(first.variant_condition, "6695=Q75 6699=MDF")

    def test_price_is_base_plus_one_increment_per_key_and_per_permutation(self):
        prices = [self.price(), self.price("6695=Q75", "X", 10.0), self.price("6695=OAK", "X", 25.0),
                  self.price("6699=MDF", "X", 1.5)]
        snap = snapshot(TWO_BY_TWO, [self.PRICE], prices)
        context = _Context()
        context.qa_snapshot = snap
        perms = ArticlePermutationService(context).build(snap)
        resolved = ArticlePriceService(context).resolve(
            perms, ArticlePriceRequest(currency="EUR", effective_date="20260101"))
        totals = {tuple(v.value for v in p.properties): r.total_price for p, r in zip(perms, resolved)}
        self.assertEqual(totals, {("Q75", "MDF"): 111.5, ("Q75", "OAK"): 110.0,
                                  ("OAK", "MDF"): 126.5, ("OAK", "OAK"): 125.0})

    def test_generate_gives_each_permutation_its_own_price(self):
        # regression: prices were keyed by article id, so all configurations got the last one's price
        prices = [self.price(), self.price("6695=Q75", "X", 10.0), self.price("6695=OAK", "X", 25.0)]
        context = _Context()
        context.qa_snapshot = snapshot(TWO_BY_TWO, [self.PRICE], prices)
        result = ArticleObxService(context).generate(currency="EUR", effective_date="20260101", series_id="TEST")
        by_top = {row.permutation.properties[0].value: row.price.total_price for row in result.rows}
        self.assertEqual(by_top, {"Q75": 110.0, "OAK": 125.0})

    def test_effective_date_and_currency_select_the_row(self):
        prices = [self.price(value=100.0, start="20240101"), self.price(value=120.0, start="20260101"),
                  self.price(value=999.0, currency="GBP")]
        context = _Context()
        context.qa_snapshot = snapshot({"Top": [("t1", "Q75", "Q75")]}, [], prices)
        perm = ArticlePermutationService(context).build(context.qa_snapshot)
        svc = ArticlePriceService(context)
        self.assertEqual(svc.resolve(perm, ArticlePriceRequest("EUR", "20250601"))[0].total_price, 100.0)
        self.assertEqual(svc.resolve(perm, ArticlePriceRequest("EUR", "20260601"))[0].total_price, 120.0)
        self.assertIn("could not be resolved", svc.resolve(perm, ArticlePriceRequest("USD", "20260601"))[0].unresolved_reason)

    def test_missing_base_price_is_reported_unresolved(self):
        context = _Context()
        context.qa_snapshot = snapshot({"Top": [("t1", "Q75", "Q75")]}, [], [self.price("6695=Q75", "X", 5.0)])
        perm = ArticlePermutationService(context).build(context.qa_snapshot)
        resolved = ArticlePriceService(context).resolve(perm, ArticlePriceRequest("EUR", "20260101"))
        self.assertIsNone(resolved[0].total_price)
        self.assertEqual(resolved[0].unresolved_reason, "Repository base price could not be resolved")

    def test_price_domain_assignment_never_reaches_the_configuration(self):
        perms, _ = build(snapshot(TWO_BY_TWO, [relation("Top = 'x'", type_code="3", domain="P")]))
        self.assertEqual(len(perms), 4)


class SafeguardTests(unittest.TestCase):
    BIG = {"A": [(f"a{i}", f"V{i}", f"{i}") for i in range(10)], "B": [(f"b{i}", f"W{i}", f"{i}") for i in range(10)]}

    def test_permutation_limit_is_reported_not_silent(self):
        perms, service = build(snapshot(self.BIG), max_permutations_per_article=30)
        self.assertEqual(len(perms), 30)
        (diag,) = service.last_diagnostics.by_code(dg.ENUMERATION_TRUNCATED)
        self.assertIs(diag.severity, dg.Severity.ERROR)

    def test_generate_surfaces_truncation_as_a_warning(self):
        context = _Context()
        context.qa_snapshot = snapshot(self.BIG, [], [VarcondPricingTests.price()])
        original = ArticlePermutationService.max_permutations_per_article
        ArticlePermutationService.max_permutations_per_article = 12
        try:
            result = ArticleObxService(context).generate(currency="EUR", effective_date="20260101", series_id="T")
        finally:
            ArticlePermutationService.max_permutations_per_article = original
        self.assertTrue(any("ENUMERATION_TRUNCATED" in w for w in result.warnings))

    def test_limit_none_disables_the_safeguard(self):
        perms, service = build(snapshot(self.BIG), max_permutations_per_article=None)
        self.assertEqual(len(perms), 100)
        self.assertEqual(service.last_diagnostics.count(dg.ENUMERATION_TRUNCATED), 0)

    def test_cancellation_stops_the_build(self):
        from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope

        token = CancellationToken()
        with cancellation_scope(token):
            token.request_cancel()
            with self.assertRaises(OperationCancelled):
                build(snapshot(self.BIG))


class ObxXmlTests(unittest.TestCase):
    def generate(self, **kwargs):
        context = _Context()
        context.qa_snapshot = snapshot(TWO_BY_TWO, [VarcondPricingTests.PRICE],
                                       [VarcondPricingTests.price(), VarcondPricingTests.price("6695=Q75", "X", 10.0)])
        return ArticleObxService(context).generate(currency="EUR", effective_date="20260101", series_id="TEST", **kwargs)

    def test_document_structure_and_required_metadata(self):
        root = ET.fromstring(self.generate().xml)                    # well-formed
        self.assertEqual(root.tag, "cutBuffer")
        self.assertEqual([c.tag for c in root], ["versionInfo", "items"])
        self.assertTrue({"vendorKey", "appKey", "appVersion", "bskXmlVersion"} <= set(root.find("versionInfo").attrib))
        articles = root.findall("./items/bskArticle")
        self.assertEqual(len(articles), 4)
        a = articles[0]
        self.assertEqual(a.get("itemType"), "BasketAggregate")
        self.assertEqual(a.find("manufacturer").get("id"), "HM")
        self.assertEqual(a.find("series").get("id"), "TEST")
        self.assertEqual(a.find("itemPrice").get("currency"), "EUR")
        self.assertIsNotNone(a.find("priceDate"))
        self.assertEqual(len(a.findall("itemPriceComponents")), 2)
        self.assertEqual(a.find("pdInfo").get("seriesId"), "TEST")
        self.assertEqual([f.get("name") for f in a.findall("feature")], ["Top", "Mat"])

    def test_default_keeps_predicted_final_and_never_writes_varcode(self):
        root = ET.fromstring(self.generate().xml)
        for a in root.findall("./items/bskArticle"):
            kinds = [n.get("type") for n in a.findall("artNr")]
            self.assertEqual(kinds, ["base", "final", "ofmlvarcode"])    # 'varcode' is pCon's resolved output
            self.assertTrue(a.find("artNr[@type='ofmlvarcode']").text.startswith("TEST_OPT.Top="))

    def test_omit_mode_is_input_style_base_plus_ofmlvarcode_only(self):
        root = ET.fromstring(self.generate(final_article_mode=FINAL_OMIT).xml)
        for a in root.findall("./items/bskArticle"):
            self.assertEqual([n.get("type") for n in a.findall("artNr")], ["base", "ofmlvarcode"])

    def test_sentinel_mode_is_compatible_with_snapper_cleanup(self):
        xml = self.generate(final_article_mode=FINAL_SENTINEL).xml
        self.assertEqual(xml.count(OBX_SENTINEL), 4)
        cleaned, kept, removed = OBXService.clean_obx(xml)
        self.assertEqual((kept, removed), (0, 4))

    def test_unknown_final_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            self.generate(final_article_mode="bogus")

    def test_special_characters_are_escaped_and_parse_back(self):
        snap = snapshot({"Top": [("t1", "A & B <1>", 'C"D')]}, [], [VarcondPricingTests.price()])
        context = _Context()
        context.qa_snapshot = snap
        xml = ArticleObxService(context).generate(currency="EUR", effective_date="20260101", series_id="T").xml
        feature = ET.fromstring(xml).find("./items/bskArticle/feature")
        self.assertEqual(feature.get("value"), 'C"D')
        self.assertEqual(feature.find("descrField1").text, "A & B <1>")


# ---------------------------------------------------------------- real Dalby through the Snapshot path
ROOT = Path("C:/HermanMillerOFMLSVN/Staging/HermanMiller/_repository/hmx/dalby/ANY/1/db")
REFERENCE = Path("C:/Users/siaoca/Downloads/Dalby_OBX_Files")


def dalby_snapshot(article):
    from services.ocd_engine.csv_loader import OcdCsvLoader, build_article_model

    dataset = OcdCsvLoader().load(ROOT)
    model = build_article_model(dataset, article)
    props, rels, art_base = [], [], {}
    for pdef in model.properties:
        prop = Property(id=pdef.key, name=pdef.name, display_order=pdef.order)
        prop.values = [PropertyValue(id=v.key, property_id=pdef.key, value=v.value, code=v.value,
                                     display_order=i) for i, v in enumerate(pdef.values)]
        props.append(prop)
        for r in pdef.relations:
            rels.append(relation(r.text, str(r.rel_type), r.domain, property_id=pdef.key, name=r.name, order=r.order))
        for v in pdef.values:
            for r in v.relations:
                rels.append(relation(r.text, str(r.rel_type), r.domain, value_id=v.key, property_id=pdef.key,
                                     name=r.name, order=r.order))
        if pdef.allowed_keys is not None:
            art_base.setdefault(article, {})[pdef.key] = sorted(pdef.allowed_keys)
    for r in model.article_relations:
        rels.append(relation(r.text, str(r.rel_type), r.domain, name=r.name, order=r.order))
    cls = EngineeringClass(id="c1", name="DALBY")
    cls.properties = [ClassPropertyAssignment(property_id=p.id, property_name=p.name) for p in props]
    prices = [PriceRecord(article_code=r["article_nr"], variant_condition=r["var_cond"], level=r["price_level"],
                          value=float(r["price"]), currency=r["currency"], valid_from=r["date_from"],
                          valid_to=r["date_to"]) for r in dataset.tables["price"] if r["article_nr"] == article]
    snap = Snapshot(
        product=Product(id="p1", code="DALBY", name="Dalby"),
        articles=[Article(id="a1", product_id="p1", code=article, name=article, source="MDB")],
        properties=props, property_values=[v for p in props for v in p.values],
        article_class_ids={"a1": ["c1"]}, article_code_scheme_ids={"a1": "s1"},
        code_schemes={"s1": {"name": "S", "body": dataset.code_scheme(model.scheme_id).scheme}},
        engineering=Engineering(classes=[cls]), relation_objects=rels, price_records=prices, art_base=art_base,
    )
    return snap


@pytest.mark.skipif(not (ROOT.exists() and REFERENCE.exists()), reason="real Dalby data not available")
def test_dalby_through_the_snapshot_path_matches_the_pcon_reference():
    from services.ocd_engine.obx_reference import read_reference_obx

    references = {}
    for path in glob.glob(f"{REFERENCE}/*Dalby*.obx"):
        if "Mismatch" in path:
            continue
        for ref in read_reference_obx(path):
            references.setdefault((ref.base, ref.currency, ref.price_date), {})[ref.final] = ref
    (article, currency, date), refs = next(
        (k, v) for k, v in sorted(references.items()) if k[0] == "NODLE150" and k[1] == "GBP")
    context = _Context()
    context.qa_snapshot = dalby_snapshot(article)
    result = ArticleObxService(context).generate(
        currency=currency, effective_date=date, series_id="DALBY", final_article_mode=FINAL_PREDICTED)
    assert result.warnings == [] and len(result.rows) == 60
    generated = {row.permutation.final_article: row for row in result.rows}
    for final, ref in refs.items():
        assert final in generated, final
        assert f"{generated[final].price.total_price:.2f}" == f"{float(ref.price):.2f}"
    assert all(" " in final for final in generated)                  # real scheme literals reached the number


def test_generator_page_surfaces_engine_warnings_and_errors_only():
    from ui.pages.article_obx_generator_page import ArticleObxGeneratorPage

    sink = dg.DiagnosticSink()
    sink.add(dg.NO_VALID_VALUE, "informational only", dg.Severity.INFO)
    sink.add(dg.ENUMERATION_TRUNCATED, "limit reached; incomplete", dg.Severity.ERROR, article="BASE")
    context = SimpleNamespace(article_permutation_service=SimpleNamespace(last_diagnostics=sink))
    issues = ArticleObxGeneratorPage._generation_issues(SimpleNamespace(_context=context))
    assert len(issues) == 1 and "ENUMERATION_TRUNCATED" in issues[0]
    assert ArticleObxGeneratorPage._generation_issues(SimpleNamespace(_context=SimpleNamespace())) == []


def test_service_limit_equal_to_result_size_is_not_a_truncation():
    perms, service = build(snapshot(TWO_BY_TWO), max_permutations_per_article=4)
    assert len(perms) == 4 and service.last_diagnostics.count(dg.ENUMERATION_TRUNCATED) == 0
    perms, service = build(snapshot(TWO_BY_TWO), max_permutations_per_article=3)
    assert len(perms) == 3 and service.last_diagnostics.count(dg.ENUMERATION_TRUNCATED) >= 1
