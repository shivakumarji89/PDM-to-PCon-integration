"""Every article-or-product value fallback follows the agreed rule.

Article-level BaseAttributeValues win for a whole product once any article has them; an article
without rows carries nothing; the product menu is used only when no article has rows.
"""
from __future__ import annotations

from types import SimpleNamespace

from models.article import Article
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering.article_value_links import carried_value_ids, products_with_article_links
from services.engineering.engineering_class_service import EngineeringClassService
from services.engineering.engineering_reduction_service import EngineeringReductionService


def _snap() -> Snapshot:
    snap = Snapshot()
    colour = [PropertyValue(id=i, property_id="p1", code="", value=n)
              for i, n in (("c1", "Red"), ("c2", "Blue"), ("c3", "Cyan"))]
    size = [PropertyValue(id="s1", property_id="p2", code="S", value="Small")]
    snap.properties = [Property(id="p1", name="Colour", values=colour),
                       Property(id="p2", name="Size", values=size)]
    snap.property_values = colour + size
    snap.articles = [
        Article(id="x1", product_id="X", code="ABR1"), Article(id="x2", product_id="X", code="ABB1"),
        Article(id="y1", product_id="Y", code="YYY1"),
    ]
    snap.product_property_value_ids = {"X": ["c1", "c2", "c3", "s1"], "Y": ["c1", "c2", "c3", "s1"]}
    return snap


# ------------------------------------------------------------- shared helper

def test_helper_rule():
    art = {"x1": ["c1"]}
    prod = {"X": ["c1", "c2"], "Y": ["c1", "c2"]}
    articles = [Article(id="x1", product_id="X"), Article(id="x2", product_id="X"),
                Article(id="y1", product_id="Y")]
    linked = products_with_article_links(articles, art)
    assert linked == {"X"}
    assert carried_value_ids("x1", "X", art, prod, linked) == (["c1"], False)
    assert carried_value_ids("x2", "X", art, prod, linked) == ([], False)      # sibling has rows
    assert carried_value_ids("y1", "Y", art, prod, linked) == (["c1", "c2"], True)


# ------------------------------------------------- reduction: classify_by_properties

def _classify(snap):
    svc = EngineeringReductionService(SimpleNamespace())
    return {c.article_ids: {n for n, _ in c.signature} for c in svc.classify_by_properties(snap)}


def test_classify_unlinked_article_beside_linked_sibling_has_empty_signature():
    snap = _snap()
    snap.article_property_value_ids = {"x1": ["c1"]}
    got = _classify(snap)
    assert got[("x1",)] == {"Colour"}
    assert got[("x2",)] == set()                    # not the whole X menu (Colour + Size)
    assert got[("y1",)] == {"Colour", "Size"}       # Y has no rows anywhere -> its own menu


def test_classify_product_without_rows_uses_menu_for_all_its_articles():
    snap = _snap()
    snap.article_property_value_ids = {}
    got = _classify(snap)
    assert got[("x1", "x2", "y1")] == {"Colour", "Size"}


# ------------------------------------------------------ reduction: _set_attributes

def _value_lookup(snap):
    return {str(v.id): (v.property_id, "n", v.value, v.code) for v in snap.property_values}


def test_set_attributes_article_without_rows_adds_no_values_to_set():
    snap = _snap()
    product_of = {"x1": "X", "x2": "X", "y1": "Y"}
    attrs = EngineeringReductionService._set_attributes(
        ["x1", "x2"], product_of, snap.product_property_value_ids, _value_lookup(snap),
        article_value_ids={"x1": ["c1"]})
    carried = {v.id: v.article_ids for a in attrs for v in a.values}
    assert carried == {"c1": ["x1"]}                # no c2/c3/s1 invented for x2


def test_set_attributes_product_without_rows_uses_menu_and_options_stay_product_level():
    snap = _snap()
    product_of = {"x1": "X", "x2": "X", "y1": "Y"}
    attrs = EngineeringReductionService._set_attributes(
        ["y1"], product_of, snap.product_property_value_ids, _value_lookup(snap),
        article_value_ids={"x1": ["c1"]})            # rows exist only for product X
    assert {v.id for a in attrs for v in a.values} == {"c1", "c2", "c3", "s1"}
    # Options pass no article links: product-level resolution is unchanged.
    opts = EngineeringReductionService._set_attributes(
        ["x1", "x2"], product_of, {"X": ["ov1"]}, {"ov1": ("o1", "Fabric", "Wool", "W")})
    assert [(v.id, v.article_ids) for a in opts for v in a.values] == [("ov1", ["x1", "x2"])]


# --------------------------------------------- reduction: resolve_variant_condition

def test_variant_condition_carried_properties_ignore_the_menu_for_unlinked_article():
    from models.engineering_class import ClassPropertyAssignment, ClassValue, EngineeringClass
    snap = _snap()
    snap.article_property_value_ids = {"x1": ["c1"]}
    snap.engineering.classes = [EngineeringClass(id="k", name="X_ATTRIBUTE", properties=[
        ClassPropertyAssignment(property_id="p1", property_name="Colour", width=1, values=[
            ClassValue(value_id=i, code=c, value=n) for i, c, n in
            (("c1", "R", "Red"), ("c2", "B", "Blue"), ("c3", "C", "Cyan"))]),
        ClassPropertyAssignment(property_id="p2", property_name="Size", width=1)])]
    svc = EngineeringReductionService(SimpleNamespace(
        engineering_class_service=EngineeringClassService(SimpleNamespace())))
    for v, code in zip(snap.properties[0].values, "RBC"):
        v.code = code
    linked = svc.resolve_variant_condition(snap, "x1", 2)
    unlinked = svc.resolve_variant_condition(snap, "x2", 2)
    assert [c[0] for c in linked.consumed] == ["p1"] and linked.remaining == "1"
    # x2 (code ABB1) has no rows: the X menu must not make it consume Colour "B".
    assert unlinked.consumed == () and unlinked.unassigned == "B1"


# ----------------------------------------------- class service: config-code decoding

def _decode(snap):
    return EngineeringClassService(SimpleNamespace())._decode_config_codes_by_value_id(snap)


def test_decode_is_not_disturbed_by_an_unlinked_article_in_a_linked_product():
    snap = _snap()
    snap.properties = [snap.properties[0]]
    snap.articles = [Article(id="x1", product_id="X", code="ABR1"),
                     Article(id="x2", product_id="X", code="ABB1"),
                     Article(id="x3", product_id="X", code="ABC1"),
                     Article(id="x4", product_id="X", code="ABR2")]     # x4 has no rows
    snap.article_property_value_ids = {"x1": ["c1"], "x2": ["c2"], "x3": ["c3"]}
    snap.product_property_value_ids = {"X": ["c1", "c2", "c3"]}
    assert _decode(snap) == {"p1": {"c1": "R", "c2": "B", "c3": "C"}}
