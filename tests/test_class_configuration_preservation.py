"""Base-article standardisation keeps Class-workflow configuration; full export honours it."""
from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace

from core.application_context import ApplicationContext
from models.engineering_class import ClassPropertyAssignment, EngineeringClass
from services.engineering import class_naming
from services.ocd_export_service import OcdExportResult, OcdExportService

from test_base_article_classes import ENTRIES, _service, _snapshot


def _classes(snap):
    return {c.name: c for c in snap.engineering.classes}


def _category_class(snap, svc, name="Desk_ATTRIBUTE"):
    cls = svc.create_class(snap, name)
    a = svc.assign_property(snap, cls.id, "p1", "Colour", width=2)
    a.type, a.usage, a.relation_object, a.text_block = "L", "Graphic", "B_Colour", "Custom_TB"
    return cls


def _settings(a):
    return (a.width, a.type, a.usage, a.relation_object, a.text_block)


def _prop(cls, pid):
    return next(a for a in cls.properties if a.property_id == pid)


# -- 1. category configuration transfer --------------------------------------

def test_category_settings_move_to_every_base_that_carries_the_property():
    snap, svc = _snapshot(), _service(ENTRIES)
    _category_class(snap, svc)
    svc.standardise_by_base_article(snap)
    by = _classes(snap)
    expected = (2, "L", "Graphic", "B_Colour", "Custom_TB")
    assert _settings(_prop(by["AAA_ATTRIBUTE"], "p1")) == expected
    assert _settings(_prop(by["BBB_ATTRIBUTE"], "p1")) == expected


def test_settings_are_not_copied_to_properties_or_bases_that_do_not_carry_them():
    snap, svc = _snapshot(), _service(ENTRIES)
    _category_class(snap, svc)
    svc.standardise_by_base_article(snap)
    by = _classes(snap)
    assert _settings(_prop(by["AAA_ATTRIBUTE"], "p2")) == (0, "", "", "", "")
    assert [a.property_id for a in by["CCC_ATTRIBUTE"].properties] == ["p2"]  # CCC has no p1


def test_ambiguous_sources_are_not_guessed():
    snap, svc = _snapshot(), _service(ENTRIES)
    for name, kind in (("Desk_ATTRIBUTE", "L"), ("Chair_ATTRIBUTE", "N")):
        cls = svc.create_class(snap, name)
        svc.assign_property(snap, cls.id, "p1", "Colour").type = kind
    svc.standardise_by_base_article(snap)
    assert _prop(_classes(snap)["AAA_ATTRIBUTE"], "p1").type == ""


def test_settings_follow_the_source_group_that_overlaps_the_base():
    snap, svc = _snapshot(), _service(ENTRIES)
    desk = svc.create_class(snap, "Desk_ATTRIBUTE")      # carries p1 + p2 (matches AAA/BBB)
    svc.assign_property(snap, desk.id, "p1", "Colour").type = "L"
    svc.assign_property(snap, desk.id, "p2", "Size")
    chair = svc.create_class(snap, "Chair_ATTRIBUTE")    # carries only p2 (matches CCC)
    svc.assign_property(snap, chair.id, "p2", "Size").type = "N"
    svc.standardise_by_base_article(snap)
    by = _classes(snap)
    assert _prop(by["CCC_ATTRIBUTE"], "p2").type == "N"
    assert _prop(by["AAA_ATTRIBUTE"], "p2").type == ""   # Desk's own p2 carries no type


def test_existing_base_class_configuration_is_never_overwritten():
    snap, svc = _snapshot(), _service(ENTRIES)
    _category_class(snap, svc)
    own = svc.create_class(snap, "AAA_ATTRIBUTE")
    a = svc.assign_property(snap, own.id, "p1", "Colour", width=5)
    a.type = "N"
    svc.standardise_by_base_article(snap)
    assert _settings(_prop(_classes(snap)["AAA_ATTRIBUTE"], "p1"))[:2] == (5, "N")


def test_export_mdb_choice_is_keyed_by_property_so_it_follows_into_base_classes():
    snap, svc = _snapshot(), _service(ENTRIES)
    _category_class(snap, svc)
    snap.mdb_export_property_overrides["p2"] = False
    svc.standardise_by_base_article(snap)
    assert snap.mdb_export_property_overrides == {"p2": False}
    kept = [a.property_id for c in OcdExportService._mdb_export_classes(snap) for a in c.properties]
    assert "p2" not in kept and "p1" in kept


# -- 3. pruning ----------------------------------------------------------------

def test_superseded_category_class_is_pruned_once_its_properties_are_carried():
    snap, svc = _snapshot(), _service(ENTRIES)
    _category_class(snap, svc)
    svc.standardise_by_base_article(snap)
    assert "Desk_ATTRIBUTE" not in _classes(snap)


def test_superseded_class_with_an_uncarried_property_is_kept():
    snap, svc = _snapshot(), _service(ENTRIES)
    cls = _category_class(snap, svc)
    svc.assign_property(snap, cls.id, "orphan", "Orphan")
    svc.standardise_by_base_article(snap)
    assert "Desk_ATTRIBUTE" in _classes(snap)


def test_partial_selection_keeps_unselected_bases_and_their_configuration():
    snap, svc = _snapshot(), _service(ENTRIES)
    _category_class(snap, svc)
    svc.standardise_by_base_article(snap)
    bbb = _classes(snap)["BBB_ATTRIBUTE"]
    bbb_id = bbb.id
    _prop(bbb, "p1").width = 9
    svc.standardise_by_base_article(snap, {"a1"})
    by = _classes(snap)
    assert {"AAA_ATTRIBUTE", "BBB_ATTRIBUTE", "BBB_OPTION", "BBB_VISUAL", "CCC_ATTRIBUTE"} <= set(by)
    assert by["BBB_ATTRIBUTE"].id == bbb_id
    assert _prop(by["BBB_ATTRIBUTE"], "p1").width == 9


def test_partial_selection_from_scratch_does_not_touch_other_bases_classes():
    snap, svc = _snapshot(), _service(ENTRIES)
    other = svc.create_class(snap, "CCC_ATTRIBUTE")
    svc.assign_property(snap, other.id, "p2", "Size", width=3)
    svc.standardise_by_base_article(snap, {"a1"})
    by = _classes(snap)
    assert by["CCC_ATTRIBUTE"].id == other.id and _prop(by["CCC_ATTRIBUTE"], "p2").width == 3
    assert "CCC_OPTION" not in by


def test_unrelated_and_manually_named_classes_survive():
    snap, svc = _snapshot(), _service(ENTRIES)
    custom = svc.create_class(snap, "MyHandCraftedClass")
    svc.assign_property(snap, custom.id, "p1", "Colour", width=4)
    svc.standardise_by_base_article(snap)
    assert _classes(snap)["MyHandCraftedClass"].id == custom.id


def test_repeated_standardisation_is_stable_and_keeps_ids():
    snap, svc = _snapshot(), _service(ENTRIES)
    _category_class(snap, svc)
    svc.standardise_by_base_article(snap)
    first = {c.name: (c.id, [(a.property_id, _settings(a)) for a in c.properties])
             for c in snap.engineering.classes}
    svc.standardise_by_base_article(snap)
    svc.standardise_by_base_article(snap)
    second = {c.name: (c.id, [(a.property_id, _settings(a)) for a in c.properties])
              for c in snap.engineering.classes}
    assert first == second


def test_relation_article_class_links_and_settings_survive_together():
    snap, svc = _snapshot(), _service(ENTRIES)
    _category_class(snap, svc)
    rel = SimpleNamespace(article_classes=[("AAA", "Desk_ATTRIBUTE")])
    snap.relation_objects = [rel]
    svc.standardise_by_base_article(snap)
    assert rel.article_classes == [("AAA", "AAA_ATTRIBUTE")]
    assert _prop(_classes(snap)["AAA_ATTRIBUTE"], "p1").relation_object == "B_Colour"


# -- snapshot isolation / background export ------------------------------------

def test_standardising_the_export_copy_never_touches_the_development_snapshot():
    snap, svc = _snapshot(), _service(ENTRIES)
    _category_class(snap, svc)
    before = [(c.id, c.name, [_settings(a) for a in c.properties]) for c in snap.engineering.classes]
    ctx = SimpleNamespace(register_mdb_export_snapshot=lambda s: None)
    export = ApplicationContext.prepare_mdb_export_snapshot(ctx, snap)
    svc.standardise_by_base_article(export)
    after = [(c.id, c.name, [_settings(a) for a in c.properties]) for c in snap.engineering.classes]
    assert export is not snap and export.id != snap.id
    assert before == after
    assert "AAA_ATTRIBUTE" in _classes(export) and "AAA_ATTRIBUTE" not in _classes(snap)


# -- 4. Export MDB in the real _build -------------------------------------------

def _build_service(snap, captured):
    xocd = SimpleNamespace(
        _value_code_map=lambda s: {"pv1": "R", "pv2": "B", "pv3": "S", "ov1": "F1"},
        _value_lengths=lambda s: {"p1": 1, "p2": 1, "o1": 2},
        _base_codes=lambda s, ids=None: ["AAA"],
        _group_token_by_base=lambda s, classes: {},
    )
    ctx = SimpleNamespace(
        engineering_class_service=SimpleNamespace(get_classes=lambda s: s.engineering.classes),
        xocd_export_service=xocd,
        material_picking_service=SimpleNamespace(prop_info_pic_prefix=lambda *a: ""),
    )
    svc = OcdExportService(ctx)
    svc._text = lambda *a: ([], {})
    svc._relations = lambda *a, **k: ([], [], [], {}, {})
    svc._code_schemes = lambda *a: ([], {}, {})
    svc._articles = lambda *a, **k: ([], {})
    svc._article_text_keys = lambda *a: {}
    svc._article_classes = lambda base_codes, token_by_base, classes, *a, **k: (
        captured.append([c.name for c in classes]) or [])
    svc._artbase = lambda *a: []
    svc._material_mappings = lambda *a: ([], [])
    svc._value_tables = lambda *a: ([], [], [])
    svc._prices = lambda *a: ([], [])
    return svc


def _run_build(snap):
    captured: list = []
    svc = _build_service(snap, captured)
    protos = defaultdict(dict)
    sequence = dict(svc._build(snap, 1, 1, "S", protos, {}, None, OcdExportResult()))
    return sequence, captured


def _export_snapshot():
    snap, svc = _snapshot(), _service(ENTRIES)
    cls = svc.create_class(snap, "AAA_ATTRIBUTE")
    for pid, name in (("p1", "Colour"), ("p2", "Size")):
        svc.assign_property(snap, cls.id, pid, name)
    opt = svc.create_class(snap, "AAA_OPTION")
    svc.assign_property(snap, opt.id, "o1", "Fabric")
    return snap


def _names(rows):
    return [r["com_PropName"] for r in rows]


def test_real_build_exports_every_property_when_nothing_is_overridden():
    sequence, _ = _run_build(_export_snapshot())
    assert _names(sequence["tCOMd_Property"]) == ["Colour", "Size", "Fabric"]


def test_real_build_excludes_unchecked_and_keeps_checked_properties():
    snap = _export_snapshot()
    snap.mdb_export_property_overrides = {"p2": False, "p1": True}
    sequence, _ = _run_build(snap)
    assert _names(sequence["tCOMd_Property"]) == ["Colour", "Fabric"]
    values = {r["com_PropertyID"] for r in sequence["tCOMd_PropValue"]}
    assert values and len(values) == 2          # Size's value rows are gone with the property
    assert [c.name for c in snap.engineering.classes] == ["AAA_ATTRIBUTE", "AAA_OPTION"]
    assert len(snap.engineering.classes[0].properties) == 2   # live class untouched


def test_real_build_empty_value_property_stays_empty_and_option_values_unchanged():
    snap = _export_snapshot()
    snap.property_values = [v for v in snap.property_values if v.property_id != "p2"]
    sequence, _ = _run_build(snap)
    size_id = next(r["com_PropertyID"] for r in sequence["tCOMd_Property"] if r["com_PropName"] == "Size")
    assert size_id not in {r["com_PropertyID"] for r in sequence["tCOMd_PropValue"]}
    fabric_id = next(r["com_PropertyID"] for r in sequence["tCOMd_Property"] if r["com_PropName"] == "Fabric")
    assert [r["com_PropValueFrom"] for r in sequence["tCOMd_PropValue"]
            if r["com_PropertyID"] == fabric_id] == ["F1"]


def test_real_build_keeps_visual_definitions_when_overrides_exist():
    snap = _export_snapshot()
    visual = EngineeringClass(id="v", name="AAA_VISUAL", properties=[
        ClassPropertyAssignment(property_id="d1", property_name="Visual Def")])
    snap.engineering.classes.append(visual)
    snap.mdb_export_property_overrides = {"p2": False}
    sequence, _ = _run_build(snap)
    names = _names(sequence["tCOMd_Property"])
    assert names == ["Colour", "Fabric", "Visual_Def"] and "Size" not in names and any("isual" in n for n in names)


# -- 5. Article Export checkbox vs full series ------------------------------------

def test_article_export_checkbox_feeds_only_the_incremental_article_export():
    from ui.pages.articles_page import ArticlesPage

    calls = []
    window = SimpleNamespace(
        _on_export_articles_to_mdb=lambda selected_article_ids=None: calls.append(("articles", selected_article_ids)),
        _on_export_mdb=lambda selected_article_ids=None: calls.append(("full", selected_article_ids)),
    )
    page = SimpleNamespace(selected_export_article_ids=lambda: {"a1", "a2"}, window=lambda: window)
    ArticlesPage._on_export_component_mdb(page)
    assert calls == [("articles", {"a1", "a2"})]


def test_full_series_export_defaults_to_all_articles():
    import inspect
    from ui.main_window import MainWindow

    assert inspect.signature(MainWindow._on_export_mdb).parameters["selected_article_ids"].default is None


# -- 6. article text lookup -----------------------------------------------------------

def _text_service(entries):
    return OcdExportService(SimpleNamespace(
        xocd_export_service=SimpleNamespace(base_code_entries=lambda s: entries)))


def _text_snapshot(members):
    return SimpleNamespace(
        articles=[SimpleNamespace(id="a1", code="AER1A11AF")],
        engineering=SimpleNamespace(families=[SimpleNamespace(members=members)]))


def test_text_found_through_member_key_when_price_base_differs():
    member = SimpleNamespace(article_id="a1", reduced_article="AER1A11AF")
    index = {("artshort", "AER1A11AF"): 7, ("artlong", "AER1A11AF"): 8}
    svc = _text_service([("a1", "AER")])
    keys = svc._article_text_keys(_text_snapshot([member]), ["AER"], index)
    assert keys == {"AER": "AER1A11AF"}
    rows, _ = svc._articles(["AER"], 1, 1, index, {}, {}, {}, None, keys)
    assert (rows[0]["com_ShortTextID"], rows[0]["com_LongTextID"]) == (7, 8)


def test_text_keyed_by_the_base_itself_is_unchanged():
    member = SimpleNamespace(article_id="a1", reduced_article="AER")
    index = {("artshort", "AER"): 3, ("artlong", "AER"): 4}
    svc = _text_service([("a1", "AER")])
    keys = svc._article_text_keys(_text_snapshot([member]), ["AER"], index)
    assert keys == {}
    rows, _ = svc._articles(["AER"], 1, 1, index, {}, {}, {}, None, keys)
    assert (rows[0]["com_ShortTextID"], rows[0]["com_LongTextID"]) == (3, 4)


def test_text_block_under_base_wins_over_member_key():
    member = SimpleNamespace(article_id="a1", reduced_article="AER1A11AF")
    index = {("artshort", "AER"): 1, ("artshort", "AER1A11AF"): 2}
    keys = _text_service([("a1", "AER")])._article_text_keys(_text_snapshot([member]), ["AER"], index)
    assert keys == {}


def test_missing_text_stays_empty():
    member = SimpleNamespace(article_id="a1", reduced_article="AER1A11AF")
    svc = _text_service([("a1", "AER")])
    keys = svc._article_text_keys(_text_snapshot([member]), ["AER"], {})
    rows, _ = svc._articles(["AER"], 1, 1, {}, {}, {}, {}, None, keys)
    assert rows[0]["com_ShortTextID"] is None
