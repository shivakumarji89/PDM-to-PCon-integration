"""Class Creation's ``base_article`` grouping basis: canonical bases -> exact-token classes."""
from __future__ import annotations

import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from models.article import Article
from models.engineering_class import EngineeringClass
from services.class_creation_selection_service import build_class_creation_scope, classes_for_article
from services.engineering import class_naming
from services.engineering.engineering_class_service import (
    BASE_ARTICLE_BASIS, CLASS_AMBIGUOUS, CLASS_FOUND, CLASS_MISSING, EngineeringClassService,
)
from test_base_article_classes import ENTRIES, _service, _snapshot


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


def _base_snap(entries=ENTRIES):
    snap = _snapshot()
    snap.split_classes_by_group = True
    snap.class_group_basis = BASE_ARTICLE_BASIS
    return snap, _service(entries)


def _names(snap):
    return sorted(c.name for c in snap.engineering.classes)


def _state(snap):
    return [(c.id, c.name, [(a.property_id, a.width, a.type, a.usage) for a in c.properties])
            for c in snap.engineering.classes]


# -- grouping == the canonical resolver --------------------------------------------------
def test_groups_match_the_canonical_resolver_entries():
    snap, svc = _base_snap()
    groups = svc.resolve_class_groups(snap, "Cat")
    assert [g.name for g in groups] == ["AAA", "BBB", "CCC"]
    assert [g.name for g in groups] == [g.name for g in svc.base_article_groups(snap)]


def test_groups_follow_the_live_resolver_not_a_stored_list():
    snap, svc = _base_snap()
    assert [g.name for g in svc.resolve_class_groups(snap, "Cat")] == ["AAA", "BBB", "CCC"]
    svc.context.xocd_export_service.base_code_entries = lambda s: [("a1", "ZZZ"), ("a3", "BBB")]
    assert [g.name for g in svc.resolve_class_groups(snap, "Cat")] == ["ZZZ", "BBB"]


def test_other_bases_keep_their_historical_groups():
    snap, svc = _base_snap()
    snap.class_group_basis = "range"
    assert [g.name for g in svc.resolve_class_groups(snap, "Cat")] != ["AAA", "BBB", "CCC"]
    snap.split_classes_by_group = False
    assert [g.name for g in svc.resolve_class_groups(snap, "Cat")] == ["Cat"]


# -- exact tokens ------------------------------------------------------------------------
SPECIAL = [("a1", "AB.12-X"), ("a2", "AB.12-X"), ("a3", "C 7/z"), ("a4", "CCC")]


def test_exact_tokens_with_special_characters():
    snap, svc = _base_snap(SPECIAL)
    svc.ensure_classes_for_basis(snap, "Cat")
    assert {"AB.12-X_ATTRIBUTE", "AB.12-X_OPTION", "AB.12-X_VISUAL",
            "C 7/z_ATTRIBUTE", "C 7/z_OPTION", "C 7/z_VISUAL"} <= set(_names(snap))
    assert svc.token_for_group(snap, "AB.12-X") == "AB.12-X"
    assert svc._group_token("AB.12-X") == "AB12X"  # what the old spelling would have produced
    assert svc.find_standard_class(snap.engineering.classes, "AB.12-X", "attribute") is not None


def test_token_for_group_is_historical_outside_the_base_basis():
    snap, svc = _base_snap()
    snap.class_group_basis = "range"
    assert svc.token_for_group(snap, "Wire Management") == "WireManagement"


# -- ATTRIBUTE / OPTION / VISUAL ---------------------------------------------------------
def test_attribute_option_visual_created_per_base_with_the_base_content():
    snap, svc = _base_snap()
    svc.ensure_classes_for_basis(snap, "Cat")
    by = {c.name: c for c in snap.engineering.classes}
    assert sorted(by) == sorted(f"{b}_{k}" for b in ("AAA", "BBB", "CCC")
                                for k in ("ATTRIBUTE", "OPTION", "VISUAL"))
    assert {a.property_id for a in by["AAA_ATTRIBUTE"].properties} == {"p1", "p2"}
    assert [a.property_id for a in by["AAA_OPTION"].properties] == ["o1"]
    assert [a.property_id for a in by["AAA_VISUAL"].properties] == ["d1"]
    assert [a.property_id for a in by["CCC_ATTRIBUTE"].properties] == ["p2"]
    lookups = svc.resolve_base_class_sets(snap)
    assert all(c.state == CLASS_FOUND for cells in lookups.values() for c in cells.values())


def test_ensure_is_idempotent():
    snap, svc = _base_snap()
    svc.ensure_classes_for_basis(snap, "Cat")
    before = _state(snap)
    svc.ensure_classes_for_basis(snap, "Cat")
    assert _state(snap) == before


# -- missing / ambiguous (read-only lookup) ------------------------------------------------
def test_lookup_is_read_only_and_reports_missing():
    snap, svc = _base_snap()
    assert snap.engineering.classes == []
    sets = svc.resolve_base_class_sets(snap)
    assert snap.engineering.classes == []  # nothing created to populate the lookup
    assert {c.state for cells in sets.values() for c in cells.values()} == {CLASS_MISSING}
    assert sets["AAA"]["attribute"].expected == "AAA_ATTRIBUTE"


def test_lookup_reports_partial_missing_and_legacy_spelling():
    snap, svc = _base_snap()
    svc.ensure_classes_for_basis(snap, "Cat")
    snap.engineering.classes = [c for c in snap.engineering.classes if c.name != "BBB_OPTION"]
    next(c for c in snap.engineering.classes if c.name == "AAA_OPTION").name = "AAA_Options"
    sets = svc.resolve_base_class_sets(snap)
    assert sets["BBB"]["option"].state == CLASS_MISSING
    assert sets["AAA"]["option"].state == CLASS_FOUND and sets["AAA"]["option"].names == ("AAA_Options",)


def test_lookup_reports_ambiguous_duplicates_and_case_colliding_bases():
    snap, svc = _base_snap()
    svc.ensure_classes_for_basis(snap, "Cat")
    snap.engineering.classes.append(EngineeringClass(id="dup", name="aaa_attribute"))
    assert svc.resolve_base_class_sets(snap)["AAA"]["attribute"].state == CLASS_AMBIGUOUS

    snap2, svc2 = _base_snap(ENTRIES + [("a5", "aaa")])
    snap2.articles.append(Article(id="a5", product_id="prod1", code="aaa9"))
    sets = svc2.resolve_base_class_sets(snap2)
    assert {c.state for c in sets["AAA"].values()} == {CLASS_AMBIGUOUS}
    assert "collide" in svc2.base_basis_error(snap2)


def test_unusable_basis_degrades_to_flat_and_creates_no_base_classes():
    snap, svc = _base_snap(ENTRIES + [("a5", "aaa")])
    snap.articles.append(Article(id="a5", product_id="prod1", code="aaa9"))
    assert [g.name for g in svc.resolve_class_groups(snap, "Cat")] == ["Cat"]
    svc.ensure_classes_for_basis(snap, "Cat")
    assert not any(n.startswith(("AAA_", "aaa_")) for n in _names(snap))
    assert svc.token_for_group(snap, "Cat") == "Cat"


# -- no unintended pruning across bases ------------------------------------------------------
def _flat_classes(svc, snap, category="Cat"):
    snap.split_classes_by_group = False
    svc.ensure_classes_for_basis(snap, category)
    snap.split_classes_by_group = True


def test_switching_to_base_basis_keeps_the_flat_classes():
    snap, svc = _base_snap()
    _flat_classes(svc, snap)
    flat = {"Cat_ATTRIBUTE", "Cat_OPTION", "Cat_VISUAL"}
    assert set(_names(snap)) == flat
    svc.ensure_classes_for_basis(snap, "Cat")
    assert flat <= set(_names(snap))
    assert {"AAA_ATTRIBUTE", "BBB_VISUAL", "CCC_OPTION"} <= set(_names(snap))


def test_switching_away_from_base_basis_keeps_the_base_classes():
    snap, svc = _base_snap()
    svc.ensure_classes_for_basis(snap, "Cat")
    base_names = set(_names(snap))
    for basis, split in (("range", True), ("article_set", True), ("range", False)):
        snap.class_group_basis, snap.split_classes_by_group = basis, split
        svc.ensure_classes_for_basis(snap, "Cat")
        assert base_names <= set(_names(snap)), (basis, split)


def test_flat_pruning_is_unchanged_for_non_base_classes():
    snap, svc = _base_snap()
    snap.split_classes_by_group = False
    svc.ensure_classes_for_basis(snap, "Cat")
    snap.engineering.classes.append(EngineeringClass(id="old", name="Old_ATTRIBUTE"))
    svc.ensure_classes_for_basis(snap, "Cat")
    assert "Old_ATTRIBUTE" not in _names(snap)  # historical stale-class pruning still applies


def test_unprotected_flat_creation_would_have_pruned_base_classes():
    """Documents why ``protect_base_classes`` exists (the old call deletes them)."""
    snap, svc = _base_snap()
    svc.ensure_classes_for_basis(snap, "Cat")
    snap.split_classes_by_group = False
    svc.ensure_standard_classes(snap, "Cat")
    assert "AAA_ATTRIBUTE" not in _names(snap)


def test_unresolvable_bases_prune_nothing():
    snap, svc = _base_snap()
    svc.ensure_classes_for_basis(snap, "Cat")
    before = _names(snap)

    def boom(_s):
        raise ValueError("identity conflict")

    svc.context.xocd_export_service.base_code_entries = boom
    snap.split_classes_by_group = False
    svc.ensure_classes_for_basis(snap, "Cat")
    assert set(before) <= set(_names(snap))


def test_prune_false_never_removes_a_class():
    snap, svc = _base_snap()
    snap.engineering.classes.append(EngineeringClass(id="x", name="Stale_ATTRIBUTE"))
    svc.ensure_standard_classes(snap, "Cat", prune=False)
    assert "Stale_ATTRIBUTE" in _names(snap)


# -- class settings through creation and export ----------------------------------------------
def test_first_creation_inherits_settings_from_the_flat_class_it_supersedes():
    snap, svc = _base_snap()
    _flat_classes(svc, snap)
    flat = next(c for c in snap.engineering.classes if c.name == "Cat_ATTRIBUTE")
    for a in flat.properties:
        a.width, a.type, a.usage = 7, "C", "X"
    svc.ensure_classes_for_basis(snap, "Cat")
    aaa = next(c for c in snap.engineering.classes if c.name == "AAA_ATTRIBUTE")
    assert {(a.width, a.type, a.usage) for a in aaa.properties} == {(7, "C", "X")}


def test_user_edited_base_class_settings_survive_export_standardisation():
    snap, svc = _base_snap()
    svc.ensure_classes_for_basis(snap, "Cat")
    aaa = next(c for c in snap.engineering.classes if c.name == "AAA_ATTRIBUTE")
    aaa.properties[0].width, aaa.properties[0].type, aaa.properties[0].usage = 9, "N", "Z"
    edited = copy.deepcopy(aaa.properties[0])
    export_copy = copy.deepcopy(snap)  # what prepare_mdb_export_snapshot hands the exporter
    svc.standardise_by_base_article(export_copy)
    out = next(c for c in export_copy.engineering.classes if c.name == "AAA_ATTRIBUTE")
    got = next(a for a in out.properties if a.property_id == edited.property_id)
    assert (got.width, got.type, got.usage) == (9, "N", "Z")
    assert sorted(c.name for c in export_copy.engineering.classes) == _names(snap)


def test_export_does_not_touch_the_development_snapshot():
    snap, svc = _base_snap()
    _flat_classes(svc, snap)
    svc.ensure_classes_for_basis(snap, "Cat")
    before = _state(snap)
    svc.standardise_by_base_article(copy.deepcopy(snap))
    assert _state(snap) == before


# -- selection service ----------------------------------------------------------------------------
def test_scope_group_names_are_the_canonical_bases():
    snap, svc = _base_snap()
    base_of = {a: b for a, b in ENTRIES}
    scope = build_class_creation_scope(snap, {"a1", "a3"}, base_of=base_of)
    assert scope.group_names == frozenset({"AAA", "BBB"})


def test_classes_for_article_selects_exactly_that_bases_classes():
    snap, svc = _base_snap(SPECIAL)
    svc.ensure_classes_for_basis(snap, "Cat")
    base_of = {a: b for a, b in SPECIAL}
    got = classes_for_article(snap, snap.engineering.classes, "a1", base_of=base_of)
    assert {c.name for c in got} <= {f"AB.12-X_{k}" for k in ("ATTRIBUTE", "OPTION", "VISUAL")}
    assert {class_naming.class_kind(c.name) for c in got} >= {"attribute", "option"}
    assert classes_for_article(snap, snap.engineering.classes, "a3", base_of=base_of)[0].name.startswith("C 7/z_")


def test_classes_for_article_never_guesses_an_unresolved_base():
    snap, svc = _base_snap()
    svc.ensure_classes_for_basis(snap, "Cat")
    assert classes_for_article(snap, snap.engineering.classes, "a1") == []


def test_classes_for_article_ignores_base_of_outside_the_base_basis():
    snap, svc = _base_snap()
    snap.class_group_basis = "range"
    snap.split_classes_by_group = False
    svc.ensure_classes_for_basis(snap, "Cat")
    plain = classes_for_article(snap, snap.engineering.classes, "a1")
    with_map = classes_for_article(snap, snap.engineering.classes, "a1", base_of={"a1": "AAA"})
    assert [c.name for c in plain] == [c.name for c in with_map]


# -- Class Creation page: dynamic refresh, source/snapshot switches ----------------------------------
def _page_ctx():
    from test_maintenance_snapshot_consistency import _context

    ctx = _context()
    snap = ctx.pdm_snapshot
    snap.article_property_value_ids = {a.id: ["PDM:V"] for a in snap.articles}
    snap.split_classes_by_group = True
    snap.class_group_basis = BASE_ARTICLE_BASIS
    members = [m for f in snap.engineering.families for m in f.members]
    for i, m in enumerate(members):
        m.reduced_article = "PDM.A" if i < 2 else f"PDM-{i}"
    return ctx, snap


def _page(ctx):
    from core.modules import WorkbenchModule
    from ui.pages.class_creation_page import ClassCreationPage

    page = ClassCreationPage(ctx)
    page._active_module = WorkbenchModule.MAINTENANCE  # Development re-materialises the sets
    page.refresh()
    return page


def test_page_creates_exact_base_classes_and_titles_the_cards_with_the_base():
    ctx, snap = _page_ctx()
    page = _page(ctx)
    names = {c.name for c in snap.engineering.classes}
    assert {"PDM.A_ATTRIBUTE", "PDM.A_OPTION", "PDM.A_VISUAL", "PDM-2_ATTRIBUTE"} <= names
    assert page._basis_combo.currentData() == BASE_ARTICLE_BASIS
    assert page._basis_combo.styleSheet() == ""
    assert page._active_token() in {"PDM.A", "PDM-2", "PDM-3", "PDM-4"}


def test_page_refreshes_after_an_articles_reduction():
    ctx, snap = _page_ctx()
    page = _page(ctx)
    before_sig = page._render_signature()
    member = next(m for f in snap.engineering.families for m in f.members if m.reduced_article == "PDM-2")
    member.reduced_article = "PDM.A"          # the Articles page folds this article into PDM.A
    assert page._render_signature() != before_sig
    page.refresh()
    assert [g.name for g in page._active_groups()] == ["PDM.A", "PDM-3", "PDM-4"]
    assert "PDM.A_ATTRIBUTE" in {c.name for c in snap.engineering.classes}
    assert "PDM-2_ATTRIBUTE" in {c.name for c in snap.engineering.classes}  # never pruned


def test_page_signature_sees_basis_and_length_override_changes():
    ctx, snap = _page_ctx()
    page = _page(ctx)
    sig = page._render_signature()
    snap.base_length_overrides = {"PDM:0": 3}
    assert page._render_signature() != sig
    sig = page._render_signature()
    snap.class_group_basis = "range"
    assert page._render_signature() != sig


def test_page_source_switch_does_not_leak_or_create_classes_in_the_mdb_view():
    ctx, snap = _page_ctx()
    page = _page(ctx)
    pdm_classes = {c.name for c in snap.engineering.classes}
    mdb_classes = [c.name for c in ctx.mdb_import_snapshot.engineering.classes]
    page._source_tabs.set_source("mdb")
    assert [c.name for c in ctx.mdb_import_snapshot.engineering.classes] == mdb_classes
    page._source_tabs.set_source("pdm")
    assert {c.name for c in snap.engineering.classes} == pdm_classes


def test_page_degrades_with_a_visible_reason_when_bases_cannot_be_told_apart():
    ctx, snap = _page_ctx()
    snap.article_property_value_ids = {}
    page = _page(ctx)
    assert "cannot be assigned" in page._basis_combo.toolTip()
    assert page._basis_combo.styleSheet()
    assert not any("PDM.A_" in c.name for c in snap.engineering.classes)


def test_articles_page_buckets_rows_by_canonical_base():
    from core.modules import WorkbenchModule
    from ui.pages.articles_page import ArticlesPage

    ctx, snap = _page_ctx()
    page = ArticlesPage(ctx)
    page._active_module = WorkbenchModule.MAINTENANCE
    page.refresh()
    buckets = dict((name, len(rows)) for name, rows in page._article_class_groups(page._rows))
    assert buckets == {"PDM.A": 2, "PDM-2": 1, "PDM-3": 1, "PDM-4": 1}


# -- export selection with a base that resolves ONLY through the price tier ------------------
def _price_tier_snap():
    """Members carry no reduced article and there is no length override: tiers 1-2 are empty,
    so each base comes solely from the price-base map (tier 3)."""
    from types import SimpleNamespace

    snap, svc = _base_snap()
    members = [SimpleNamespace(id=f"m-{aid}", article_id=aid, reduced_article="") for aid, _b in ENTRIES]
    snap.engineering.families = [SimpleNamespace(members=members)]
    code_by_id = {a.id: a.code for a in snap.articles}
    price_base_of = {code_by_id[aid]: base for aid, base in ENTRIES}
    return snap, svc, price_base_of


def test_price_tier_base_is_resolved_by_the_canonical_resolver():
    from services.engineering.base_identity import SOURCE_PRICE_BASE, resolve_base_identities

    snap, _svc, price_base_of = _price_tier_snap()
    without = resolve_base_identities(snap)
    assert [b for _a, b in without.entries] == ["", "", "", ""]      # tiers 1-2 alone resolve nothing
    resolved = resolve_base_identities(snap, price_base_of)
    assert resolved.entries == ENTRIES
    assert set(resolved.sources.values()) == {SOURCE_PRICE_BASE}


def test_export_selection_keeps_price_tier_base_class_associations():
    from services.engineering.base_identity import resolve_base_identities
    from services.properties_values_mdb_export_service import PropertiesValuesMdbExportService

    snap, svc, price_base_of = _price_tier_snap()
    svc.ensure_classes_for_basis(snap, "Cat")
    classes = snap.engineering.classes
    base_of = {str(a): b for a, b in resolve_base_identities(snap, price_base_of).entries}   # what exports now hold

    # Selection-only resolution cannot see the price tier: it stays empty (never guesses a base).
    assert classes_for_article(snap, classes, "a1") == []
    assert PropertiesValuesMdbExportService._assignment_union(snap, classes, {"a1"}) == {}

    # With the context-aware map the article gets exactly its own base's classes.
    got = classes_for_article(snap, classes, "a1", base_of=base_of)
    assert {c.name for c in got} == {"AAA_ATTRIBUTE", "AAA_OPTION", "AAA_VISUAL"}
    assert {class_naming.class_kind(c.name) for c in got} == {"attribute", "option", "visual"}
    union = PropertiesValuesMdbExportService._assignment_union(snap, classes, {"a1", "a3"}, base_of=base_of)
    assert {"AAA_ATTRIBUTE", "BBB_ATTRIBUTE"} <= set(union)
    assert not any(name.startswith("CCC_") for name in union)       # unselected base stays out


def test_unresolved_article_stays_empty_even_with_a_base_map():
    snap, svc, price_base_of = _price_tier_snap()
    svc.ensure_classes_for_basis(snap, "Cat")
    assert classes_for_article(snap, snap.engineering.classes, "a1", base_of={"a1": ""}) == []
    assert classes_for_article(snap, snap.engineering.classes, "a1", base_of={}) == []


def test_explicit_tiers_still_win_without_a_base_map():
    from types import SimpleNamespace

    snap, svc, _price = _price_tier_snap()
    snap.engineering.families[0].members[0].reduced_article = "AAA"      # tier 1 for a1
    svc.ensure_classes_for_basis(snap, "Cat")
    got = classes_for_article(snap, snap.engineering.classes, "a1")
    assert {c.name for c in got} == {"AAA_ATTRIBUTE", "AAA_OPTION", "AAA_VISUAL"}
