"""Standardised per-base-article classes: ``{BASE}_ATTRIBUTE/_OPTION/_VISUAL``."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from models.article import Article
from models.option import Option
from models.option_value import OptionValue
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering import class_naming
from services.engineering.engineering_class_service import EngineeringClassService
from services.xocd_export_service import XocdExportService


def _snapshot() -> Snapshot:
    snap = Snapshot()
    snap.properties = [
        Property(id="p1", name="Colour", values=[]),
        Property(id="p2", name="Size", values=[]),
    ]
    snap.property_values = [
        PropertyValue(id="pv1", property_id="p1", code="R", value="Red"),
        PropertyValue(id="pv2", property_id="p1", code="B", value="Blue"),
        PropertyValue(id="pv3", property_id="p2", code="S", value="Small"),
    ]
    for prop in snap.properties:
        prop.values = [v for v in snap.property_values if v.property_id == prop.id]
    snap.options = [Option(id="o1", name="Fabric", values=[])]
    snap.option_values = [OptionValue(id="ov1", option_id="o1", code="F1", value="Wool")]
    snap.options[0].values = list(snap.option_values)
    snap.articles = [
        Article(id="a1", product_id="prod1", code="AAA1"),
        Article(id="a2", product_id="prod1", code="AAA2"),   # 2nd variant of base AAA
        Article(id="a3", product_id="prod2", code="BBB1"),   # base BBB: identical properties
        Article(id="a4", product_id="prod3", code="CCC1"),   # base CCC: only Size
    ]
    snap.product_property_value_ids = {
        "prod1": ["pv1", "pv2", "pv3"], "prod2": ["pv1", "pv2", "pv3"], "prod3": ["pv3"],
    }
    snap.product_option_value_ids = {"prod1": ["ov1"], "prod2": ["ov1"], "prod3": []}
    snap.engineering.properties = [SimpleNamespace(id="d1", name="Visual Def")]
    return snap


def _service(entries) -> EngineeringClassService:
    xocd = SimpleNamespace(base_code_entries=lambda snapshot: entries)
    picking = SimpleNamespace(ensure_package_defaults=lambda snapshot: None)
    ctx = SimpleNamespace(xocd_export_service=xocd, material_picking_service=picking)
    return EngineeringClassService(ctx)


ENTRIES = [("a1", "AAA"), ("a2", "AAA"), ("a3", "BBB"), ("a4", "CCC")]


def _by_name(snap):
    return {c.name: c for c in snap.engineering.classes}


def test_exact_names_per_base_article():
    snap = _snapshot()
    names = _service(ENTRIES).standardise_by_base_article(snap)
    assert names["AAA"] == {
        "attribute": "AAA_ATTRIBUTE", "option": "AAA_OPTION", "visual": "AAA_VISUAL",
    }
    assert sorted(_by_name(snap)) == sorted(
        f"{b}_{k}" for b in ("AAA", "BBB", "CCC") for k in ("ATTRIBUTE", "OPTION", "VISUAL")
    )


def test_variants_share_one_base_class_set():
    snap = _snapshot()
    _service(ENTRIES).standardise_by_base_article(snap)
    # a1 and a2 are both base AAA: exactly one AAA class set, not one per variant.
    assert [c.name for c in snap.engineering.classes].count("AAA_ATTRIBUTE") == 1


def test_identical_bases_do_not_share_classes():
    snap = _snapshot()
    _service(ENTRIES).standardise_by_base_article(snap)
    classes = _by_name(snap)
    assert classes["AAA_ATTRIBUTE"] is not classes["BBB_ATTRIBUTE"]
    assert classes["AAA_ATTRIBUTE"].id != classes["BBB_ATTRIBUTE"].id
    assert [a.property_id for a in classes["AAA_ATTRIBUTE"].properties] == \
           [a.property_id for a in classes["BBB_ATTRIBUTE"].properties]


def test_properties_options_values_assigned_to_right_classes():
    snap = _snapshot()
    _service(ENTRIES).standardise_by_base_article(snap)
    classes = _by_name(snap)
    attr = classes["AAA_ATTRIBUTE"]
    assert {a.property_id for a in attr.properties} == {"p1", "p2"}
    colour = next(a for a in attr.properties if a.property_id == "p1")
    assert {v.value_id for v in colour.values} == {"pv1", "pv2"}
    assert [a.property_id for a in classes["AAA_OPTION"].properties] == ["o1"]
    assert [a.property_id for a in classes["AAA_VISUAL"].properties] == ["d1"]
    # base CCC carries only Size and no options
    assert [a.property_id for a in classes["CCC_ATTRIBUTE"].properties] == ["p2"]
    assert classes["CCC_OPTION"].properties == []


def test_selection_limits_generation_to_selected_bases():
    snap = _snapshot()
    _service(ENTRIES).standardise_by_base_article(snap, {"a3"})
    assert {c.name.split("_")[0] for c in snap.engineering.classes} == {"BBB"}


def test_rebuild_is_idempotent_and_migrates_legacy_names():
    snap = _snapshot()
    svc = _service(ENTRIES)
    legacy = svc.create_class(snap, "AAA_Options")
    svc.standardise_by_base_article(snap)
    first = len(snap.engineering.classes)
    assert legacy.name == "AAA_OPTION"             # renamed in place, same class id
    svc.standardise_by_base_article(snap)
    assert len(snap.engineering.classes) == first


def test_case_insensitive_base_collision_is_rejected():
    snap = _snapshot()
    with pytest.raises(ValueError):
        _service([("a1", "AAA"), ("a3", "aaa")]).standardise_by_base_article(snap)


def test_relation_article_class_links_follow_the_new_names():
    snap = _snapshot()
    rel = SimpleNamespace(article_classes=[("AAA", "Desk_Attribute"), ("BBB", "Desk_Options")])
    snap.relation_objects = [rel]
    _service(ENTRIES).standardise_by_base_article(snap)
    assert rel.article_classes == [("AAA", "AAA_ATTRIBUTE"), ("BBB", "BBB_OPTION")]


def test_naming_helpers_are_case_insensitive_and_legacy_aware():
    assert class_naming.class_kind("X_Options") == "option"
    assert class_naming.class_kind("X_OPTION") == "option"
    assert class_naming.class_kind("X_Attribute") == "attribute"
    assert class_naming.class_kind("Misc") is None
    assert class_naming.class_token("A_B_ATTRIBUTE") == "A_B"


def test_downstream_group_token_resolves_each_base_to_its_own_classes():
    snap = _snapshot()
    _service(ENTRIES).standardise_by_base_article(snap)
    xocd = XocdExportService(SimpleNamespace())
    xocd._base_codes = lambda snapshot, selected=None: ["AAA", "BBB", "CCC"]
    xocd._price_base_of = lambda snapshot: {}
    tokens = xocd._group_token_by_base(snap, snap.engineering.classes)
    assert tokens == {"AAA": "AAA", "BBB": "BBB", "CCC": "CCC"}


def test_no_links_and_several_bases_is_refused_not_guessed():
    snap = _snapshot()
    snap.product_property_value_ids = {}
    snap.product_option_value_ids = {}
    with pytest.raises(ValueError, match="no per-article"):
        _service(ENTRIES).standardise_by_base_article(snap)
    assert snap.engineering.classes == []


def test_no_links_and_a_single_base_takes_the_product_wide_lists():
    snap = _snapshot()
    snap.product_property_value_ids = {}
    snap.product_option_value_ids = {}
    _service([("a1", "AAA"), ("a2", "AAA")]).standardise_by_base_article(snap)
    classes = _by_name(snap)
    assert {a.property_id for a in classes["AAA_ATTRIBUTE"].properties} == {"p1", "p2"}
    assert [a.property_id for a in classes["AAA_OPTION"].properties] == ["o1"]
