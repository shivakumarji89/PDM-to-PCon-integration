"""Lino MI1E3 (two article sets, one base) and sparse BaseAttributeValues edge cases."""
from __future__ import annotations

from types import SimpleNamespace

from models.article import Article
from models.article_set import ArticleSet, SetAttribute, SetValue
from models.option import Option
from models.option_value import OptionValue
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering.engineering_class_service import EngineeringClassService


def _service(entries) -> EngineeringClassService:
    xocd = SimpleNamespace(base_code_entries=lambda snapshot: entries)
    picking = SimpleNamespace(ensure_package_defaults=lambda snapshot: None)
    return EngineeringClassService(
        SimpleNamespace(xocd_export_service=xocd, material_picking_service=picking))


def _by_name(snap):
    return {c.name: c for c in snap.engineering.classes}


def _props(cls):
    return {a.property_id: a for a in cls.properties}


def _check_integrity(snap):
    """No duplicate names/ids; every assignment/value resolves to the snapshot (no orphans)."""
    names = [c.name.casefold() for c in snap.engineering.classes]
    assert len(names) == len(set(names)), "duplicate class names"
    ids = [c.id for c in snap.engineering.classes]
    assert len(ids) == len(set(ids)), "duplicate class ids"
    prop_values = {p.id: {str(v.id) for v in p.values} | {
        str(v.id) for v in snap.property_values if v.property_id == p.id} for p in snap.properties}
    opt_values = {o.id: {str(v.id) for v in o.values} for o in snap.options}
    visual = {d.id for d in snap.engineering.properties}
    for cls in snap.engineering.classes:
        seen = [a.property_id for a in cls.properties]
        assert len(seen) == len(set(seen)), f"{cls.name}: property assigned twice"
        for a in cls.properties:
            if a.property_id in visual:
                continue
            allowed = prop_values.get(a.property_id)
            if allowed is None:
                allowed = opt_values.get(a.property_id)
            assert allowed is not None, f"{cls.name}: orphan property {a.property_id}"
            for v in a.values:
                assert v.value_id in allowed, f"{cls.name}/{a.property_id}: foreign value {v.value_id}"


# ---------------------------------------------------------------- Lino MI1E3

def _lino() -> Snapshot:
    snap = Snapshot()
    snap.properties = [Property(id="p1", name="Colour", values=[]),
                       Property(id="p2", name="Arms", values=[])]
    snap.property_values = [
        PropertyValue(id="c1", property_id="p1", code="A", value="Black"),
        PropertyValue(id="c2", property_id="p1", code="F", value="Frost"),
        PropertyValue(id="a1", property_id="p2", code="1", value="Fixed"),
        PropertyValue(id="a2", property_id="p2", code="2", value="Height"),
    ]
    for p in snap.properties:
        p.values = [v for v in snap.property_values if v.property_id == p.id]
    snap.options = [Option(id="o1", name="Castors", values=[])]
    snap.option_values = [OptionValue(id="ov1", option_id="o1", code="H", value="Hard")]
    snap.options[0].values = list(snap.option_values)
    # Set 1 = products 61753/61749 (Colour only); set 2 = product 61741 (Colour + Arms).
    snap.articles = [
        Article(id="1", product_id="61753", code="MI1E325AA"),
        Article(id="2", product_id="61749", code="MI1E325HA"),
        Article(id="3", product_id="61741", code="MI1E335NA"),
    ]
    snap.article_property_value_ids = {"1": ["c1"], "2": ["c2"], "3": ["c1", "a1"]}
    snap.product_option_value_ids = {"61753": ["ov1"], "61749": ["ov1"], "61741": ["ov1"]}
    snap.article_sets = [
        ArticleSet(id="s1", base_code="MI1E3", article_ids=["1", "2"],
                   properties=[SetAttribute(id="p1", name="Colour", values=[
                       SetValue(id="c1", article_ids=["1"]), SetValue(id="c2", article_ids=["2"])])]),
        ArticleSet(id="s2", base_code="MI1E3", article_ids=["3"],
                   properties=[SetAttribute(id="p1", name="Colour", values=[
                       SetValue(id="c1", article_ids=["3"])]),
                       SetAttribute(id="p2", name="Arms", values=[
                           SetValue(id="a1", article_ids=["3"])])]),
    ]
    return snap


LINO = [("1", "MI1E3"), ("2", "MI1E3"), ("3", "MI1E3")]


def test_lino_two_article_sets_resolve_to_one_class_set():
    snap = _lino()
    names = _service(LINO).standardise_by_base_article(snap)
    assert list(names) == ["MI1E3"]
    classes = _by_name(snap)
    assert sorted(classes) == ["MI1E3_ATTRIBUTE", "MI1E3_OPTION", "MI1E3_VISUAL"]
    attrs = _props(classes["MI1E3_ATTRIBUTE"])
    assert set(attrs) == {"p1", "p2"}                       # union of both sets
    assert {v.value_id for v in attrs["p1"].values} == {"c1", "c2"}
    assert {v.value_id for v in attrs["p2"].values} == {"a1"}   # a2 is carried by nobody
    assert [a.property_id for a in classes["MI1E3_OPTION"].properties] == ["o1"]
    _check_integrity(snap)


def test_lino_legacy_set_classes_and_relation_bindings_are_remapped_not_duplicated():
    snap = _lino()
    svc = _service(LINO)
    legacy1 = svc.create_class(snap, "MI1E3_Attribute")
    svc.assign_property(snap, legacy1.id, "p1", "Colour")
    legacy2 = svc.create_class(snap, "MI1E3_2_Attribute")      # second set's old class
    svc.assign_property(snap, legacy2.id, "p2", "Arms")
    legacy_opt = svc.create_class(snap, "MI1E3_Options")
    rel_a = SimpleNamespace(article_classes=[("MI1E3", "MI1E3_Attribute"), ("MI1E3", "MI1E3_Options")])
    rel_b = SimpleNamespace(article_classes=[("MI1E3", "MI1E3_2_Attribute"), ("OTHER", "Foo_Attribute")])
    snap.relation_objects = [rel_a, rel_b]
    svc.standardise_by_base_article(snap)
    classes = _by_name(snap)
    assert sorted(classes) == ["MI1E3_ATTRIBUTE", "MI1E3_OPTION", "MI1E3_VISUAL"]
    assert classes["MI1E3_ATTRIBUTE"].id == legacy1.id          # renamed in place
    assert classes["MI1E3_OPTION"].id == legacy_opt.id
    assert legacy2 not in snap.engineering.classes               # no orphan
    assert rel_a.article_classes == [("MI1E3", "MI1E3_ATTRIBUTE"), ("MI1E3", "MI1E3_OPTION")]
    assert rel_b.article_classes == [("MI1E3", "MI1E3_ATTRIBUTE"), ("OTHER", "Foo_Attribute")]
    for rel in snap.relation_objects:                            # no dangling reference
        for code, cname in rel.article_classes:
            if code == "MI1E3":
                assert cname in classes
    _check_integrity(snap)
    first = {n: [(a.property_id, [v.value_id for v in a.values]) for a in c.properties]
             for n, c in classes.items()}
    svc.standardise_by_base_article(snap)                        # idempotent
    again = {c.name: [(a.property_id, [v.value_id for v in a.values]) for a in c.properties]
             for c in snap.engineering.classes}
    assert again == first


def test_lino_values_stay_out_of_unrelated_bases():
    snap = _lino()
    snap.articles.append(Article(id="9", product_id="99999", code="ZZ1"))
    snap.article_property_value_ids["9"] = ["c2"]
    _service(LINO + [("9", "ZZ1")]).standardise_by_base_article(snap)
    classes = _by_name(snap)
    assert {a.property_id for a in classes["ZZ1_ATTRIBUTE"].properties} == {"p1"}
    assert {v.value_id for v in _props(classes["ZZ1_ATTRIBUTE"])["p1"].values} == {"c2"}
    assert classes["ZZ1_OPTION"].properties == []                # product 99999 has no options
    _check_integrity(snap)


# --------------------------------------------------- sparse BaseAttributeValues

def _single_base(snap, ids):
    _service([(i, "BASE") for i in ids]).standardise_by_base_article(snap)
    return _by_name(snap)


def test_property_with_no_values_gets_no_invented_values():
    snap = _lino()
    snap.article_property_value_ids = {}
    snap.product_property_value_ids = {}
    snap.product_option_value_ids = {}        # no carried value of any kind in the base
    # An article set declares Colour for the base but none of its articles carries a value.
    snap.article_sets = [ArticleSet(id="s", base_code="BASE", article_ids=["1"], properties=[
        SetAttribute(id="p1", name="Colour", values=[SetValue(id="c1", article_ids=["other"])])])]
    classes = _single_base(snap, ["1"])
    assert _props(classes["BASE_ATTRIBUTE"])["p1"].values == []   # not all of Colour's PDM values
    _check_integrity(snap)


def test_some_articles_with_values_others_with_product_link_only():
    snap = _lino()
    snap.article_property_value_ids = {"1": ["c1"]}            # article 2 has no BAV rows
    snap.product_property_value_ids = {"61749": ["c2"]}         # its own product's link only
    snap.article_sets = []
    classes = _single_base(snap, ["1", "2"])
    attrs = _props(classes["BASE_ATTRIBUTE"])
    assert set(attrs) == {"p1"}
    assert {v.value_id for v in attrs["p1"].values} == {"c1", "c2"}   # nothing from p2 / a2
    _check_integrity(snap)


def test_article_without_any_links_contributes_nothing():
    snap = _lino()
    snap.article_property_value_ids = {"1": ["c1"]}
    snap.product_property_value_ids = {}
    snap.product_option_value_ids = {}
    snap.article_sets = []
    classes = _single_base(snap, ["1", "2"])                    # 2 carries nothing
    assert {v.value_id for v in _props(classes["BASE_ATTRIBUTE"])["p1"].values} == {"c1"}
    assert classes["BASE_OPTION"].properties == []


def test_missing_property_value_links_do_not_create_properties_or_values():
    snap = _lino()
    snap.article_property_value_ids = {"1": ["c1", "ghost-value"]}   # ghost-value is in no property
    snap.product_option_value_ids = {"61753": ["ghost-option-value"]}
    snap.article_sets = []
    classes = _single_base(snap, ["1"])
    attrs = _props(classes["BASE_ATTRIBUTE"])
    assert set(attrs) == {"p1"} and [v.value_id for v in attrs["p1"].values] == ["c1"]
    assert classes["BASE_OPTION"].properties == []
    _check_integrity(snap)


def test_linked_value_unavailable_does_not_drop_the_available_ones():
    snap = _lino()
    # c2 is linked but its PropertyValue row is gone from the snapshot entirely.
    snap.property_values = [v for v in snap.property_values if v.id != "c2"]
    snap.properties[0].values = [v for v in snap.properties[0].values if v.id != "c2"]
    snap.article_property_value_ids = {"1": ["c1", "c2"], "2": ["c2"]}
    snap.article_sets = []
    classes = _single_base(snap, ["1", "2"])
    assert [v.value_id for v in _props(classes["BASE_ATTRIBUTE"])["p1"].values] == ["c1"]
    _check_integrity(snap)


def test_value_only_in_flat_property_values_is_not_silently_dropped():
    snap = _lino()
    # c2 exists in snapshot.property_values (flat) but not in Property.values.
    snap.properties[0].values = [v for v in snap.properties[0].values if v.id != "c2"]
    snap.article_property_value_ids = {"1": ["c1", "c2"]}
    snap.article_sets = []
    classes = _single_base(snap, ["1"])
    got = {v.value_id for v in _props(classes["BASE_ATTRIBUTE"])["p1"].values}
    assert got == {"c1", "c2"}


# ------------------------------------------------------------ option assignment

def test_product_options_go_to_every_base_of_that_product():
    snap = _lino()
    snap.articles = [Article(id="1", product_id="P", code="AAA1"),
                     Article(id="2", product_id="P", code="BBB1"),
                     Article(id="3", product_id="Q", code="CCC1")]
    snap.article_property_value_ids = {"1": ["c1"], "2": ["a1"], "3": ["c2"]}
    snap.product_option_value_ids = {"P": ["ov1"], "Q": []}
    snap.article_sets = []
    _service([("1", "AAA"), ("2", "BBB"), ("3", "CCC")]).standardise_by_base_article(snap)
    classes = _by_name(snap)
    assert [a.property_id for a in classes["AAA_OPTION"].properties] == ["o1"]
    assert [a.property_id for a in classes["BBB_OPTION"].properties] == ["o1"]
    assert classes["CCC_OPTION"].properties == []                 # Q has none: nothing invented
    assert {a.property_id for a in classes["AAA_ATTRIBUTE"].properties} == {"p1"}
    assert {a.property_id for a in classes["BBB_ATTRIBUTE"].properties} == {"p2"}
