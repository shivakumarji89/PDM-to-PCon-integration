"""Maintenance PDM/MDB tabs must consume the snapshot of their own source.

Regressions covered:
  * a PDM snapshot loaded through the Family / Project paths was never
    registered as ``context.pdm_snapshot`` (Articles showed an empty table);
  * snapshot-implicit services (articles / properties / options) were bound to
    the *global* active snapshot, so a tab could count or list another
    source's data (Class Creation, Articles status).
"""
import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from core.application_context import ApplicationContext
from core.enums import SnapshotStatus
from core.modules import WorkbenchModule
from models.article import Article
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from ui.pages.articles_page import ArticlesPage
from ui.pages.class_creation_page import ClassCreationPage
from ui.pages.pricing_page import PricingPage
from ui.pages.pricing_relation_page import PricingRelationPage
from ui.pages.relation_page import RelationPage
from ui.pages.text_page import TextPage
from ui.widgets.maintenance_source_tabs import SourceContext

PAGES = (
    ArticlesPage, ClassCreationPage, TextPage,
    RelationPage, PricingPage, PricingRelationPage,
)


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


def _snapshot(ctx, source: str, count: int) -> Snapshot:
    snap = Snapshot(id=source)
    snap.metadata.source = source
    snap.articles = [
        Article(id=f"{source}:{i}", code=f"{source}{i:03d}", description=f"{source} {i}")
        for i in range(count)
    ]
    snap.properties = [
        Property(
            id=f"{source}:P",
            name=f"{source}Prop",
            values=[PropertyValue(id=f"{source}:V", property_id=f"{source}:P", value=f"{source}Val")],
        )
    ]
    ctx.engineering_initialization_service.initialize(snap)
    return snap


def _context(pdm_count=5, mdb_count=2) -> ApplicationContext:
    ctx = ApplicationContext()
    ctx.register_pdm_snapshot(_snapshot(ctx, "PDM", pdm_count))
    ctx.register_mdb_import_snapshot(_snapshot(ctx, "MDB", mdb_count))
    ctx.activate_snapshot_source("pdm")
    return ctx


def _page(cls, ctx):
    page = cls(ctx)
    page._active_module = WorkbenchModule.MAINTENANCE
    page.refresh()
    return page


def _codes(page):
    return {
        page._table.item(r, 0).text() for r in range(page._table.rowCount())
    }


# -- shared source wrapper --------------------------------------------------
def test_source_context_binds_snapshot_services_to_the_tab_source():
    ctx = _context()
    wrapper = SourceContext(ctx)
    wrapper.source = "mdb"
    assert [a.id for a in wrapper.article_service.get_articles()] == ["MDB:0", "MDB:1"]
    assert [p.id for p in wrapper.property_service.get_properties()] == ["MDB:P"]
    wrapper.source = "pdm"
    assert len(wrapper.article_service.get_articles()) == 5
    assert [p.id for p in wrapper.property_service.get_properties()] == ["PDM:P"]
    wrapper.source = None  # Development / other modules: untouched global service
    assert wrapper.article_service is ctx.article_service
    # The global context is never switched.
    assert ctx.active_snapshot is ctx.pdm_snapshot
    assert ctx.snapshot_source == "pdm"


def test_snapshot_service_binding_is_cached_per_wrapper():
    wrapper = SourceContext(_context())
    wrapper.source = "pdm"
    assert wrapper.article_service is wrapper.article_service


# -- Articles -----------------------------------------------------------------
def test_articles_pdm_and_mdb_rows_and_status_follow_their_snapshot():
    ctx = _context()
    page = _page(ArticlesPage, ctx)
    page._group_check.setChecked(False)
    assert _codes(page) == {f"PDM{i:03d}" for i in range(5)}
    assert page._s_loaded.text() == "5"
    assert page._sets_tree.topLevelItemCount() >= 2  # "All sets" + a real set
    page._source_tabs.set_source("mdb")
    assert _codes(page) == {"MDB000", "MDB001"}
    assert page._s_loaded.text() == "2"
    page._source_tabs.set_source("pdm")
    assert _codes(page) == {f"PDM{i:03d}" for i in range(5)}
    assert page._s_loaded.text() == "5"


def test_articles_status_ignores_a_diverged_global_active_snapshot():
    """Loaded count must come from the tab's snapshot, not the global one."""
    ctx = _context()
    other = _snapshot(ctx, "OTHER", 36)
    ctx.snapshot_manager.load_snapshot(other)  # global active != pdm_snapshot
    page = _page(ArticlesPage, ctx)
    assert page._s_loaded.text() == "5"
    assert ctx.active_snapshot is other


def test_articles_switch_leaks_no_stale_selection_or_filter():
    ctx = _context()
    page = _page(ArticlesPage, ctx)
    page._group_check.setChecked(False)
    page._table.selectRow(0)
    page._source_tabs.set_source("mdb")
    assert page._table.rowCount() == 2
    assert not (_codes(page) & {f"PDM{i:03d}" for i in range(5)})
    assert page._active_set_ids is None


def test_articles_mdb_stays_read_only():
    ctx = _context()
    page = _page(ArticlesPage, ctx)
    page._source_tabs.set_source("mdb")
    before = [(m.reduced_article, m.short_description)
              for f in ctx.mdb_import_snapshot.engineering.families for m in f.members]
    page._base_len_spin.setValue(3)
    page._on_apply_base_length()
    page._on_clear_short()
    after = [(m.reduced_article, m.short_description)
             for f in ctx.mdb_import_snapshot.engineering.families for m in f.members]
    assert before == after
    assert ctx.mdb_import_snapshot.status != SnapshotStatus.MODIFIED


# -- Class Creation -----------------------------------------------------------
def test_class_creation_reads_properties_of_the_selected_source():
    ctx = _context()
    page = _page(ClassCreationPage, ctx)
    assert page.source_snapshot() is ctx.pdm_snapshot
    assert [p.id for p in page._context.property_service.get_properties()] == ["PDM:P"]
    page._source_tabs.set_source("mdb")
    assert page.source_snapshot() is ctx.mdb_import_snapshot
    assert [p.id for p in page._context.property_service.get_properties()] == ["MDB:P"]
    page._source_tabs.set_source("pdm")
    assert [p.id for p in page._context.property_service.get_properties()] == ["PDM:P"]


# -- every workflow ------------------------------------------------------------
@pytest.mark.parametrize("cls", PAGES)
def test_every_page_resolves_each_tab_from_its_registered_snapshot(cls):
    ctx = _context()
    # Simulate a Family load: the global active snapshot was replaced by a new
    # PDM snapshot that must then be registered as the PDM source.
    family = _snapshot(ctx, "FAM", 36)
    ctx.snapshot_manager.load_snapshot(family)
    ctx.adopt_loaded_pdm_snapshot()
    assert ctx.pdm_snapshot is family
    page = _page(cls, ctx)
    assert page.source_snapshot() is family
    page._source_tabs.set_source("mdb")
    assert page.source_snapshot() is ctx.mdb_import_snapshot
    page._source_tabs.set_source("pdm")
    assert page.source_snapshot() is family
    assert ctx.snapshot_source == "pdm"


# -- registration of loaded PDM snapshots --------------------------------------
def test_adopt_registers_active_snapshot_as_pdm_and_keeps_mdb():
    ctx = _context()
    mdb = ctx.mdb_import_snapshot
    loaded = _snapshot(ctx, "FAM", 36)
    ctx.snapshot_manager.load_snapshot(loaded)
    assert ctx.pdm_snapshot is not loaded  # the bug: never registered
    assert ctx.adopt_loaded_pdm_snapshot() is loaded
    assert ctx.pdm_snapshot is loaded
    assert ctx.active_snapshot is loaded
    assert ctx.mdb_import_snapshot is mdb


def test_adopt_while_mdb_source_active_restores_the_mdb_snapshot():
    ctx = _context()
    ctx.activate_snapshot_source("mdb_import")
    mdb = ctx.mdb_import_snapshot
    loaded = _snapshot(ctx, "FAM", 36)
    ctx.snapshot_manager.load_snapshot(loaded)  # PDMService does this on load
    ctx.adopt_loaded_pdm_snapshot()
    assert ctx.pdm_snapshot is loaded
    assert ctx.snapshot_source == "mdb_import"
    assert ctx.active_snapshot is mdb


def test_adopt_with_nothing_loaded_is_a_no_op():
    ctx = ApplicationContext()
    assert ctx.adopt_loaded_pdm_snapshot() is None
    assert ctx.pdm_snapshot is None


# -- three-snapshot architecture / export preservation --------------------------
def test_adopt_never_registers_the_mdb_baseline_as_pdm():
    ctx = _context()
    pdm = ctx.pdm_snapshot
    ctx.activate_snapshot_source("mdb_import")
    assert ctx.adopt_loaded_pdm_snapshot() is None  # active snapshot is the MDB one
    assert ctx.pdm_snapshot is pdm
    assert ctx.mdb_import_snapshot is not ctx.pdm_snapshot


def test_adopting_the_already_registered_pdm_keeps_the_export_snapshot():
    """Add-Family merges into the same object: valid export state survives."""
    ctx = _context()
    export = ctx.prepare_mdb_export_snapshot(ctx.pdm_snapshot)
    assert ctx.adopt_loaded_pdm_snapshot() is ctx.pdm_snapshot
    assert ctx.mdb_export_snapshot is export


def test_adopting_a_different_pdm_invalidates_only_the_export_snapshot():
    ctx = _context()
    mdb, qa = ctx.mdb_import_snapshot, ctx.prepare_qa_snapshot()
    ctx.prepare_mdb_export_snapshot(ctx.pdm_snapshot)
    ctx.snapshot_manager.load_snapshot(_snapshot(ctx, "FAM", 3))
    ctx.adopt_loaded_pdm_snapshot()
    assert ctx.mdb_export_snapshot is None  # stale copy of the replaced PDM
    assert ctx.mdb_import_snapshot is mdb
    assert ctx.qa_snapshot is qa


def test_module_switching_keeps_every_registered_snapshot():
    ctx = _context()
    pdm, mdb = ctx.pdm_snapshot, ctx.mdb_import_snapshot
    export = ctx.prepare_mdb_export_snapshot(pdm)
    for source in ("pdm", "mdb_import", "pdm", "mdb_import", "pdm"):
        ctx.activate_snapshot_source(source)
        assert ctx.pdm_snapshot is pdm
        assert ctx.mdb_import_snapshot is mdb
        assert ctx.mdb_export_snapshot is export
    assert ctx.active_snapshot is pdm


def test_page_source_switching_does_not_touch_registered_snapshots():
    ctx = _context()
    pdm, mdb = ctx.pdm_snapshot, ctx.mdb_import_snapshot
    export = ctx.prepare_mdb_export_snapshot(pdm)
    for cls in PAGES:
        page = _page(cls, ctx)
        for source in ("mdb", "pdm", "mdb"):
            page._source_tabs.set_source(source)
    assert ctx.pdm_snapshot is pdm and ctx.mdb_import_snapshot is mdb
    assert ctx.mdb_export_snapshot is export


def test_development_services_stay_global_and_unwrapped():
    ctx = _context()
    page = _page(ArticlesPage, ctx)
    page._active_module = WorkbenchModule.DEVELOPMENT
    page.refresh()
    assert page.current_source() is None
    assert page._context.article_service is ctx.article_service
    assert page._context.active_snapshot is ctx.active_snapshot


# -- PDM variants vs MDB base articles (Bolster, verified against live data) ----
_BOLSTER_PDM = [
    "AL1C1000S", "AL1C1002AS", "AL1C1002LS", "AL1C1002RS", "AL1C1002S",
    "AL1C1003AS", "AL1C1003LS", "AL1C1003RS", "AL1C1003S",
    "AL1C1004LS", "AL1C1004RS", "AL1C1005S",
]
_BOLSTER_MDB = ["AL1C0400", "AL1C1000", "AL1C1002", "AL1C1003", "AL1C1004", "AL1C1005"]


def _map_bolster(pdm_codes):
    from services.maintenance_alignment_service import MaintenanceAlignmentService as A

    mdb = Snapshot()
    mdb.articles = [Article(id=c, code=c) for c in _BOLSTER_MDB]
    by_code = A._mdb_by_code(mdb)
    matched: dict[str, list[str]] = {}
    unresolved = []
    for code in pdm_codes:
        base, _reason = A.resolve_released_base(Article(id=code, code=code), by_code)
        if base is None:
            unresolved.append(code)
        else:
            matched.setdefault(base.code, []).append(code)
    return matched, unresolved, sorted(set(_BOLSTER_MDB) - set(matched))


def test_pdm_variants_map_to_mdb_bases_without_guessing():
    matched, unresolved, mdb_only = _map_bolster(_BOLSTER_PDM)
    assert unresolved == []
    assert {b: len(v) for b, v in matched.items()} == {
        "AL1C1000": 1, "AL1C1002": 4, "AL1C1003": 4, "AL1C1004": 2, "AL1C1005": 1,
    }
    # The one MDB base without a loaded PDM article: its PDM product (an
    # inactive Ottoman outside every Explorer catalogue) is not in the session.
    assert mdb_only == ["AL1C0400"]


def test_complete_range_leaves_no_mdb_only_or_unresolved_articles():
    matched, unresolved, mdb_only = _map_bolster(_BOLSTER_PDM + ["AL1C0400"])
    assert unresolved == [] and mdb_only == []
    assert matched["AL1C0400"] == ["AL1C0400"]


# -- MDB base length adopted by the Maintenance PDM view -------------------------
from types import SimpleNamespace

from models.article_set import ArticleSet
from services.maintenance_alignment_service import MaintenanceAlignmentService

# (code, expected reduced base). MDB bases: ABC100, ABC102 (6) + DEF (3) + QQ and
# QQ5 (nested -> ambiguous). ZZZ900X has no MDB base at all.
_ADOPT_PDM = [
    ("ABC100S", "ABC100"), ("ABC102S", "ABC102"), ("ABC102LS", "ABC102"),
    ("DEF77S", "DEF"), ("ZZZ900X", ""), ("QQ5A", ""),
]
_ADOPT_MDB = ["ABC100", "ABC102", "DEF", "QQ", "QQ5"]


def _adopt_context(blocked=False):
    ctx = ApplicationContext()
    pdm = Snapshot(id="PDM")
    pdm.articles = [Article(id=f"p{i}", code=c) for i, (c, _b) in enumerate(_ADOPT_PDM)]
    # A set-level length that differs from every MDB length: MDB must win.
    pdm.article_sets = [
        ArticleSet(id="S1", base_length=4, article_ids=[a.id for a in pdm.articles])
    ]
    ctx.engineering_initialization_service.initialize(pdm)
    mdb = Snapshot(id="MDB")
    mdb.articles = [Article(id=f"m{i}", code=c) for i, c in enumerate(_ADOPT_MDB)]
    ctx.engineering_initialization_service.initialize(mdb)
    ctx.register_pdm_snapshot(pdm)
    ctx.register_mdb_import_snapshot(mdb)
    ctx.activate_snapshot_source("pdm")
    service = ctx.engineering_reduction_service
    verdicts = ()
    if blocked:
        verdicts = (SimpleNamespace(
            blocks_reduction=True, snapshot_covers_range=False,
            unloaded_range_product_count=1, product_range="Bolster Sofa Group",
            product_range_id=1, status="unresolved", reason="partial range",
        ),)
    service.validate_article_sets = lambda snapshot, *a, **k: verdicts
    service.blocked_article_ids = lambda snapshot, v=None, *a, **k: (
        frozenset(a.id for a in snapshot.articles) if blocked else frozenset()
    )
    return ctx


def _reduced(ctx):
    article_code = {a.id: a.code for a in ctx.pdm_snapshot.articles}
    return {
        article_code[m.article_id]: m.reduced_article
        for f in ctx.pdm_snapshot.engineering.families for m in f.members
    }


def test_derived_lengths_reuse_the_single_resolver():
    ctx = _adopt_context()
    lengths, unresolved = MaintenanceAlignmentService.derived_base_lengths(
        ctx.pdm_snapshot, ctx.mdb_import_snapshot
    )
    by_code = {a.code: lengths.get(a.id) for a in ctx.pdm_snapshot.articles}
    assert by_code == {
        "ABC100S": 6, "ABC102S": 6, "ABC102LS": 6, "DEF77S": 3,
        "ZZZ900X": None, "QQ5A": None,
    }
    reasons = dict(unresolved)
    assert set(reasons) == {"ZZZ900X", "QQ5A"}
    assert "Ambiguous" in reasons["QQ5A"] and "No released MDB base" in reasons["ZZZ900X"]


@pytest.mark.parametrize("blocked", [False, True])
def test_articles_pdm_view_adopts_mdb_base_length_per_variant(blocked):
    ctx = _adopt_context(blocked=blocked)
    pdm_before = copy.deepcopy(ctx.pdm_snapshot)
    mdb_before = copy.deepcopy(ctx.mdb_import_snapshot)
    page = _page(ArticlesPage, ctx)
    expected = dict(_ADOPT_PDM)
    assert _reduced(ctx) == expected  # mapped -> MDB length; unmapped -> untouched
    note = page._s_reduction.text()
    assert "applied to 4 of 6" in note and "ZZZ900X" in note and "QQ5A" in note
    if blocked:  # partial range still reported, not treated as complete
        assert "only part of Bolster Sofa Group" in note
    # Source data is untouched: codes, ids, descriptions, MDB snapshot as a whole.
    assert [(a.id, a.code, a.description) for a in ctx.pdm_snapshot.articles] == [
        (a.id, a.code, a.description) for a in pdm_before.articles
    ]
    assert ctx.mdb_import_snapshot == mdb_before
    assert ctx.pdm_snapshot.relation_objects == pdm_before.relation_objects


def test_articles_adoption_is_pdm_only_and_survives_source_switching():
    ctx = _adopt_context()
    page = _page(ArticlesPage, ctx)
    reduced = _reduced(ctx)
    page._source_tabs.set_source("mdb")
    assert page._mdb_mapping is None  # MDB view derives nothing
    assert page._s_reduction.text() == "Consistent"
    assert _reduced(ctx) == reduced
    assert all(not m.reduced_article for f in ctx.mdb_import_snapshot.engineering.families
               for m in f.members)
    page._source_tabs.set_source("pdm")
    assert _reduced(ctx) == reduced


def test_development_does_not_adopt_mdb_lengths():
    ctx = _adopt_context()
    page = ArticlesPage(ctx)
    page._active_module = WorkbenchModule.DEVELOPMENT
    page.refresh()
    assert page._mdb_mapping is None
    # Legacy set-level length (4) applies, never the MDB per-variant length.
    reduced = _reduced(ctx)
    assert reduced["ABC100S"] == "ABC1" and reduced["DEF77S"] == "DEF7"


def test_no_mdb_loaded_means_no_adoption():
    ctx = _adopt_context()
    ctx.register_mdb_import_snapshot(None)
    page = _page(ArticlesPage, ctx)
    assert page._mdb_mapping is None


def test_scope_overlay_is_restored_and_never_persisted(tmp_path):
    ctx = _adopt_context()
    original = dict(ctx.pdm_snapshot.base_length_overrides)
    service = MaintenanceAlignmentService(ctx)
    assert service.prepare_pdm_scope(ctx.pdm_snapshot, ctx.mdb_import_snapshot) == 4
    overlay = ctx.pdm_snapshot.base_length_overrides
    assert overlay["ABC100S"] == 6 and "ZZZ900X" not in overlay and "QQ5A" not in overlay
    # A project saved while the overlay is active carries the pre-scope values.
    ctx.snapshot_manager.load_snapshot(ctx.pdm_snapshot)
    path = ctx.project_service.save_project(tmp_path / "p.mkproj")
    import json
    saved = json.loads(path.read_text(encoding="utf-8"))["snapshot"]
    assert saved["base_length_overrides"] == original
    assert ctx.pdm_snapshot.base_length_overrides == overlay  # live overlay kept
    assert service.restore_pdm_scope() is True
    assert ctx.pdm_snapshot.base_length_overrides == original


def test_incomplete_range_warning_does_not_load_inactive_products():
    """The partial-range warning is informational: no automatic completion."""
    ctx = _adopt_context(blocked=True)
    calls = []
    ctx.pdm_service.complete_product_ranges = lambda *a, **k: calls.append(a)
    ctx.pdm_service.add_family_to_session = lambda *a, **k: calls.append(a)
    page = _page(ArticlesPage, ctx)
    assert "only part of Bolster Sofa Group" in page._blocked_reason
    assert calls == []


def test_pdm_partial_range_warning_does_not_leak_into_the_mdb_tab():
    ctx = _adopt_context(blocked=True)
    page = _page(ArticlesPage, ctx)
    assert "only part of Bolster Sofa Group" in page._s_reduction.text()
    page._source_tabs.set_source("mdb")
    assert page._s_reduction.text() == "Consistent"
    page._source_tabs.set_source("pdm")
    assert "only part of Bolster Sofa Group" in page._s_reduction.text()


# -- shared Maintenance scope: Class Creation, Open Project, mixed sets, remap --
import json

from services.snapshot_serialization import snapshot_to_dict


def _scope_context(mixed=False):
    """PDM variants whose MDB bases have lengths 6 and (mixed) 4 in ONE structure."""
    ctx = ApplicationContext()
    pdm = Snapshot(id="PDM")
    codes = ["ABC100LS", "ABC100RS", "DEF7LS", "DEF7RS"] if mixed else [
        "ABC100LS", "ABC100RS", "ABC102LS", "ABC102RS"
    ]
    pdm.articles = [Article(id=f"p{i}", code=c, product_id="1") for i, c in enumerate(codes)]
    ctx.engineering_initialization_service.initialize(pdm)
    mdb = Snapshot(id="MDB")
    bases = ["ABC100", "DEF7"] if mixed else ["ABC100", "ABC102"]
    mdb.articles = [Article(id=f"m{i}", code=c) for i, c in enumerate(bases)]
    ctx.engineering_initialization_service.initialize(mdb)
    ctx.register_pdm_snapshot(pdm)
    ctx.register_mdb_import_snapshot(mdb)
    ctx.activate_snapshot_source("pdm")
    # Hermetic: the legacy ProductsList check would otherwise query live PDM.
    ctx.engineering_reduction_service.validate_article_sets = lambda *a, **k: ()
    ctx.engineering_reduction_service.blocked_article_ids = lambda *a, **k: frozenset()
    return ctx


def _members(ctx):
    code = {a.id: a.code for a in ctx.pdm_snapshot.articles}
    return {code[m.article_id]: m.reduced_article
            for f in ctx.pdm_snapshot.engineering.families for m in f.members}


def test_class_creation_opened_first_sees_the_adopted_lengths():
    """Central scope: no dependence on the Articles page having run."""
    ctx = _scope_context(mixed=True)
    page = _page(ClassCreationPage, ctx)  # Articles never opened
    assert _members(ctx) == {
        "ABC100LS": "ABC100", "ABC100RS": "ABC100", "DEF7LS": "DEF7", "DEF7RS": "DEF7",
    }
    assert sorted(s.base_length for s in ctx.pdm_snapshot.article_sets) == [4, 6]
    assert sorted(r[0] for r in page._split_members()) == sorted(_members(ctx))


def test_class_creation_pdm_mdb_pdm_keeps_overlay_off_the_mdb_snapshot():
    ctx = _scope_context()
    mdb_before = copy.deepcopy(ctx.mdb_import_snapshot)
    active = ctx.active_snapshot
    page = _page(ClassCreationPage, ctx)
    adopted = _members(ctx)
    sets = [(s.base_length, tuple(s.article_ids)) for s in ctx.pdm_snapshot.article_sets]
    for source in ("mdb", "pdm", "mdb", "pdm"):
        page._source_tabs.set_source(source)
        assert page.source_snapshot() is (
            ctx.mdb_import_snapshot if source == "mdb" else ctx.pdm_snapshot
        )
    assert _members(ctx) == adopted
    assert sets == [(s.base_length, tuple(s.article_ids)) for s in ctx.pdm_snapshot.article_sets]
    mdb = ctx.mdb_import_snapshot
    assert mdb == mdb_before
    assert not mdb.base_length_overrides and mdb.base_length_overrides_original is None
    assert not mdb.scope_reduced_articles
    assert ctx.active_snapshot is active and ctx.snapshot_source == "pdm"


def test_development_never_sees_the_overlay_after_leaving_maintenance():
    ctx = _scope_context()
    _page(ClassCreationPage, ctx)
    pdm = ctx.pdm_snapshot
    assert pdm.base_length_overrides_original is not None
    original = dict(pdm.base_length_overrides_original)
    MaintenanceAlignmentService(ctx).restore_pdm_scope()  # ProductPage.set_module does this
    assert pdm.base_length_overrides == original
    assert pdm.base_length_overrides_original is None and not pdm.scope_reduced_articles
    assert all(not v for v in _members(ctx).values())


def test_open_project_in_maintenance_prepares_scope_centrally(tmp_path):
    ctx = _scope_context()
    # A Development-style project file for the same PDM snapshot.
    ctx.snapshot_manager.load_snapshot(ctx.pdm_snapshot)
    path = ctx.project_service.save_project(tmp_path / "dev.mkproj")
    ctx.register_pdm_snapshot(None)
    ctx.project_service.load_project(path)  # adopts the project as the PDM snapshot
    assert ctx.pdm_snapshot is not None and ctx.pdm_snapshot.base_length_overrides_original is None
    page = _page(ClassCreationPage, ctx)  # first page opened is NOT Articles
    pdm = ctx.pdm_snapshot
    assert pdm.base_length_overrides_original is not None
    assert pdm.base_length_overrides.get("ABC100LS") == 6
    assert set(_members(ctx).values()) == {"ABC100", "ABC102"}
    # Saving while the overlay is live writes neither overrides nor reductions.
    saved = json.loads(
        ctx.project_service.save_project(tmp_path / "maint.mkproj").read_text(encoding="utf-8")
    )["snapshot"]
    assert saved["base_length_overrides"] == {}
    reduced = [m["reduced_article"] for f in saved["engineering"]["families"] for m in f["members"]]
    assert reduced and all(r == "" for r in reduced)
    assert pdm.base_length_overrides.get("ABC100LS") == 6  # live view untouched
    assert page.is_mdb_view() is False


def test_every_serializer_path_omits_the_overlay(tmp_path):
    from services.snapshot_store import SnapshotStore

    ctx = _scope_context()
    _page(ArticlesPage, ctx)
    pdm = ctx.pdm_snapshot
    assert pdm.base_length_overrides  # overlay live
    target = SnapshotStore(tmp_path).save(pdm, tmp_path / "s.json")
    stored = json.loads(target.read_text(encoding="utf-8"))
    assert stored["base_length_overrides"] == {}
    assert snapshot_to_dict(pdm)["base_length_overrides"] == {}


def test_mixed_length_set_is_split_not_reduced_to_the_minimum():
    ctx = _scope_context(mixed=True)
    _page(ArticlesPage, ctx)
    pdm = ctx.pdm_snapshot
    by_len = {s.base_length: sorted(s.article_ids) for s in pdm.article_sets}
    assert by_len == {6: ["p0", "p1"], 4: ["p2", "p3"]}
    masters = {
        m.base: m.base_length
        for m in ctx.engineering_reduction_service.merge_sets_by_base(pdm)
    }
    assert masters == {"ABC100": 6, "DEF7": 4}  # was ABC1 / DEF7 at the set minimum
    # Without the scope (Development) the engine behaves exactly as before.
    MaintenanceAlignmentService(ctx).restore_pdm_scope()
    assert len(pdm.article_sets) == 1


def test_manual_edit_survives_refresh_until_the_mapping_changes():
    ctx = _scope_context()
    page = _page(ArticlesPage, ctx)
    member = next(m for f in ctx.pdm_snapshot.engineering.families for m in f.members
                  if m.article_id == "p0")
    member.reduced_article = "ABC1"  # deliberate manual boundary
    page.refresh()
    assert member.reduced_article == "ABC1"  # not silently overwritten
    # Repository changes: different MDB base -> mapping signature changes.
    mdb2 = Snapshot(id="MDB2")
    mdb2.articles = [Article(id="n0", code="ABC10")]  # shorter base, covers both
    ctx.engineering_initialization_service.initialize(mdb2)
    ctx.register_mdb_import_snapshot(mdb2)
    page.refresh()
    assert _members(ctx)["ABC100LS"] == "ABC10"  # re-derived from the new MDB
    assert _members(ctx)["ABC102LS"] == "ABC10"


def test_remap_clears_lengths_of_articles_that_become_unmapped():
    ctx = _scope_context()
    page = _page(ArticlesPage, ctx)
    assert _members(ctx)["ABC102LS"] == "ABC102"
    mdb2 = Snapshot(id="MDB2")
    mdb2.articles = [Article(id="n0", code="ABC100")]  # no base for ABC102*
    ctx.engineering_initialization_service.initialize(mdb2)
    ctx.register_mdb_import_snapshot(mdb2)
    page.refresh()
    reduced = _members(ctx)
    assert reduced["ABC100LS"] == "ABC100"
    assert reduced["ABC102LS"] == "" and reduced["ABC102RS"] == ""
    assert "ABC102LS" in page._s_reduction.text()


def test_clearing_the_repository_restores_the_pdm_view():
    ctx = _scope_context()
    page = _page(ArticlesPage, ctx)
    original = dict(ctx.pdm_snapshot.base_length_overrides_original)
    # RepositoryWorkspace.clear_repository: restore, then drop the MDB snapshot.
    MaintenanceAlignmentService(ctx).restore_pdm_scope()
    ctx.register_mdb_import_snapshot(None)
    assert ctx.pdm_snapshot.base_length_overrides == original
    assert ctx.pdm_snapshot.base_length_overrides_original is None
    assert all(not v for v in _members(ctx).values())  # MDB-derived lengths gone
    page.refresh()
    assert page._mdb_mapping is None  # no MDB: plain PDM view, nothing adopted
    assert ctx.pdm_snapshot.base_length_overrides_original is None


def test_restore_and_saves_return_to_the_pre_scope_reductions(tmp_path):
    """Reductions made before the overlay (e.g. by Development) come back."""
    ctx = _scope_context()
    for family in ctx.pdm_snapshot.engineering.families:
        for member in family.members:
            member.reduced_article = "ABC"  # pre-scope Development value
    _page(ArticlesPage, ctx)
    assert set(_members(ctx).values()) == {"ABC100", "ABC102"}
    # A save while the overlay is live carries the pre-scope value, not the MDB view.
    document = snapshot_to_dict(ctx.pdm_snapshot)
    saved = {m["reduced_article"] for f in document["engineering"]["families"]
             for m in f["members"]}
    assert saved == {"ABC"}
    # Leaving Maintenance / clearing the repository restores it exactly.
    MaintenanceAlignmentService(ctx).restore_pdm_scope()
    assert set(_members(ctx).values()) == {"ABC"}
    assert not ctx.pdm_snapshot.scope_reduced_articles


def test_unmapped_articles_cleared_by_the_scope_are_restored_afterwards():
    ctx = _scope_context()
    for family in ctx.pdm_snapshot.engineering.families:
        for member in family.members:
            member.reduced_article = "ABC"
    mdb2 = Snapshot(id="MDB2")
    mdb2.articles = [Article(id="n0", code="ABC100")]  # ABC102* unmapped
    ctx.engineering_initialization_service.initialize(mdb2)
    ctx.register_mdb_import_snapshot(mdb2)
    for family in ctx.pdm_snapshot.engineering.families:
        for member in family.members:
            member.reduced_article = "ABC"
    _page(ArticlesPage, ctx)
    reduced = _members(ctx)
    assert reduced["ABC100LS"] == "ABC100" and reduced["ABC102LS"] == ""
    MaintenanceAlignmentService(ctx).restore_pdm_scope()
    assert set(_members(ctx).values()) == {"ABC"}
