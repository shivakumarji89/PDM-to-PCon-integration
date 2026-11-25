"""Price-tier-only bases must get their ATTRIBUTE/OPTION/VISUAL classes through the export selection.

A base resolved only by the price tier (no reduced article, no length override) cannot be
named by ``classes_for_article`` without the context-aware canonical map. Every exporter
resolves ``xocd.base_code_entries`` once and passes it as ``base_of``.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

import pytest

from services import relation_mdb_export_service as relation_module
from services import text_mdb_export_service as text_module
from services.class_creation_mdb_export_service import ClassCreationMdbExportService
from services.class_creation_selection_service import _explicit_base_of, classes_for_article
from services.engineering import class_naming
from services.engineering.engineering_class_service import BASE_ARTICLE_BASIS
from services.properties_values_mdb_export_service import PropertiesValuesMdbExportService
from services.relation_mdb_export_service import RelationMdbExportService
from services.text_mdb_export_service import TextMdbExportService
from test_base_article_classes import ENTRIES, _service, _snapshot

PRICE_TIER = {a: b for a, b in ENTRIES}   # no reduced article / override anywhere


def _price_tier_snapshot():
    snap = _snapshot()                      # has no engineering families: nothing explicit
    snap.split_classes_by_group = True
    snap.class_group_basis = BASE_ARTICLE_BASIS
    svc = _service(ENTRIES)
    svc.ensure_classes_for_basis(snap, "Cat")
    return snap


# -- the selection service -------------------------------------------------------------------
def test_price_tier_base_is_not_explicit():
    snap = _price_tier_snapshot()
    assert {_explicit_base_of(snap, a) for a in PRICE_TIER} == {""}


def test_context_free_selection_never_guesses_a_price_tier_base():
    snap = _price_tier_snapshot()
    assert classes_for_article(snap, snap.engineering.classes, "a1") == []


@pytest.mark.parametrize("article,base", [("a1", "AAA"), ("a2", "AAA"), ("a3", "BBB"), ("a4", "CCC")])
def test_price_tier_base_gets_attribute_option_and_visual(article, base):
    snap = _price_tier_snapshot()
    got = classes_for_article(snap, snap.engineering.classes, article, base_of=PRICE_TIER)
    names = {c.name for c in got}
    assert names <= {f"{base}_ATTRIBUTE", f"{base}_OPTION", f"{base}_VISUAL"}
    kinds = {class_naming.class_kind(n) for n in names}
    assert {"attribute", "visual"} <= kinds
    if base != "CCC":                       # CCC carries no options
        assert "option" in kinds


def test_exact_token_for_special_characters_in_a_price_tier_base():
    snap = _snapshot()
    snap.split_classes_by_group, snap.class_group_basis = True, BASE_ARTICLE_BASIS
    entries = [("a1", "AB.12-X"), ("a2", "AB.12-X"), ("a3", "C 7/z"), ("a4", "CCC")]
    _service(entries).ensure_classes_for_basis(snap, "Cat")
    got = classes_for_article(snap, snap.engineering.classes, "a1", base_of=dict(entries))
    assert {c.name for c in got} <= {"AB.12-X_ATTRIBUTE", "AB.12-X_OPTION", "AB.12-X_VISUAL"} and got


def test_unmapped_article_is_not_guessed_even_when_other_bases_are_mapped():
    snap = _price_tier_snapshot()
    assert classes_for_article(snap, snap.engineering.classes, "a1", base_of={"a3": "BBB"}) == []


def test_base_of_is_ignored_outside_the_base_basis():
    snap = _price_tier_snapshot()
    for basis, split in (("range", False), ("range", True), ("article_set", True)):
        snap.class_group_basis, snap.split_classes_by_group = basis, split
        plain = classes_for_article(snap, snap.engineering.classes, "a1")
        mapped = classes_for_article(snap, snap.engineering.classes, "a1", base_of=PRICE_TIER)
        assert [c.name for c in plain] == [c.name for c in mapped], (basis, split)


# -- call sites -------------------------------------------------------------------------------
def test_class_creation_export_links_price_tier_base_classes(tmp_path):
    from test_class_creation_mdb_export_service import _fixture

    snapshot, session, context, db, classes = _fixture(tmp_path)
    classes[0].name, classes[1].name = "BASE_ATTRIBUTE", "BASE_OPTION"
    snapshot.split_classes_by_group, snapshot.class_group_basis = True, BASE_ARTICLE_BASIS

    result = ClassCreationMdbExportService(context).export_to_session(snapshot, session, {"a1", "a2"})

    assert result["ok"], result
    assert {r["com_ClassName"] for r in db.data["classes"]} == {"BASE_ATTRIBUTE", "BASE_OPTION"}
    assert result["counts"]["article_classes_inserted"] == 2


def test_properties_values_union_uses_the_price_tier_base():
    from test_properties_values_mdb_export_service import _snapshot_and_classes

    snapshot, classes = _snapshot_and_classes()
    for cls in classes:
        cls.name = "BASE_ATTRIBUTE"
    snapshot.split_classes_by_group, snapshot.class_group_basis = True, BASE_ARTICLE_BASIS
    union = PropertiesValuesMdbExportService._assignment_union(
        snapshot, classes, {"a1", "a2"}, base_of={"a1": "BASE", "a2": "BASE"})
    assert set(union) == {"BASE_ATTRIBUTE"}
    assert PropertiesValuesMdbExportService._assignment_union(snapshot, classes, {"a1", "a2"}) == {}


def test_relation_and_text_exporters_hand_the_price_tier_map_to_the_selection(monkeypatch, tmp_path):
    import test_relation_link_preservation as rel
    import test_text_preservation as txt

    seen: list[dict] = []

    def spy(_snapshot, _classes, article_id, base_of=None):
        seen.append(dict(base_of or {}))
        return []

    scope = SimpleNamespace(property_ids=[], option_ids=[], property_value_ids={}, option_value_ids={})
    monkeypatch.setattr(relation_module, "classes_for_article", spy)
    monkeypatch.setattr(relation_module, "build_class_creation_scope", lambda *_a, **_k: scope)
    service, _db, session, _rel = rel._world(None)
    service.export_to_session(rel.SNAPSHOT, session, {"a1"}, workflow="pricing_relations")
    assert seen and seen[-1] == {"a1": "NODLE100"}

    seen.clear()
    monkeypatch.setattr(text_module, "classes_for_article", spy)
    monkeypatch.setattr(text_module, "build_class_creation_scope", lambda *_a, **_k: scope)
    txt._run(tmp_path, txt._rows(), True)
    assert seen and all(m == {"a1": "BASE"} for m in seen)
