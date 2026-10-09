"""Maintenance PDM/MDB source tabs: page-local, read-only MDB view."""
import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QTableWidgetItem

from core.application_context import ApplicationContext
from core.modules import WorkbenchModule
from models.article import Article
from models.price_record import PriceRecord
from models.relation_object import RelationObject
from models.snapshot import Snapshot
from models.text_block import TextBlock
from ui.pages.articles_page import ArticlesPage
from ui.pages.class_creation_page import ClassCreationPage
from ui.pages.pricing_page import PricingPage
from ui.pages.pricing_relation_page import PricingRelationPage
from ui.pages.relation_page import RelationPage
from ui.pages.text_page import TextPage
from ui.widgets.maintenance_source_tabs import MDB_NOT_LOADED_TEXT

PAGES = (
    ArticlesPage, ClassCreationPage, TextPage,
    RelationPage, PricingPage, PricingRelationPage,
)


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


def _snapshot(source: str) -> Snapshot:
    snap = Snapshot()
    snap.metadata.source = source
    snap.articles = [Article(id=f"{source}:1", code="ABC123")]
    snap.text_blocks = [TextBlock(name=f"{source}_text", type_code="article", en="x")]
    snap.relation_objects = [
        RelationObject(name="PA_IMPORTED", type_code="3", domain="P", body="x = 1"),
        RelationObject(name="B_IMPORTED", type_code="1", domain="C", body="y = 2"),
    ]
    snap.price_records = [PriceRecord(article_code="ABC123", value=5.0, currency="GBP")]
    return snap


def _context(with_mdb: bool = True) -> ApplicationContext:
    ctx = ApplicationContext()
    ctx.register_pdm_snapshot(_snapshot("PDM"))
    if with_mdb:
        ctx.register_mdb_import_snapshot(_snapshot("MDB"))
    ctx.activate_snapshot_source("pdm")
    return ctx


def _page(cls, ctx, module=WorkbenchModule.MAINTENANCE):
    page = cls(ctx)
    page._active_module = module  # the page is its own top-level window here
    page.refresh()
    return page


def _select(page, source):
    page._source_tabs.set_source(source)


@pytest.mark.parametrize("cls", PAGES)
def test_tab_resolves_to_matching_snapshot(cls):
    ctx = _context()
    page = _page(cls, ctx)
    assert page.source_snapshot() is ctx.pdm_snapshot
    _select(page, "mdb")
    assert page.source_snapshot() is ctx.mdb_import_snapshot
    _select(page, "pdm")
    assert page.source_snapshot() is ctx.pdm_snapshot


@pytest.mark.parametrize("cls", PAGES)
def test_switching_does_not_change_global_state(cls):
    ctx = _context()
    page = _page(cls, ctx)
    pdm, mdb = ctx.pdm_snapshot, ctx.mdb_import_snapshot
    active, source = ctx.active_snapshot, ctx.snapshot_source
    for target in ("mdb", "pdm", "mdb", "pdm"):
        _select(page, target)
        assert ctx.active_snapshot is active
        assert ctx.snapshot_source == source
        assert page._active_module == WorkbenchModule.MAINTENANCE
    assert ctx.pdm_snapshot is pdm
    assert ctx.mdb_import_snapshot is mdb


@pytest.mark.parametrize("cls", PAGES)
def test_opening_mdb_does_not_mutate_snapshots(cls):
    ctx = _context()
    page = _page(cls, ctx)
    before_mdb = copy.deepcopy(ctx.mdb_import_snapshot)
    before_pdm = copy.deepcopy(ctx.pdm_snapshot)
    _select(page, "mdb")
    page.refresh()
    if hasattr(page, "on_enter"):
        page.on_enter()
    mdb = ctx.mdb_import_snapshot
    assert mdb == before_mdb
    assert mdb.relation_objects == before_mdb.relation_objects
    assert mdb.text_blocks == before_mdb.text_blocks
    assert mdb.price_records == before_mdb.price_records
    assert mdb.engineering.classes == before_mdb.engineering.classes
    assert ctx.pdm_snapshot == before_pdm


@pytest.mark.parametrize("cls", PAGES)
def test_development_has_no_source_tabs(cls):
    ctx = _context()
    page = _page(cls, ctx, module=WorkbenchModule.DEVELOPMENT)
    page.show()
    assert not page._source_tabs.isVisible()
    assert page.current_source() is None
    assert page.source_snapshot() is ctx.active_snapshot
    maint = _page(cls, ctx)
    maint.show()
    assert maint._source_tabs.isVisible()


@pytest.mark.parametrize("cls", PAGES)
def test_no_mdb_loaded_shows_empty_state(cls):
    ctx = _context(with_mdb=False)
    page = _page(cls, ctx)
    _select(page, "mdb")
    page.refresh()
    assert page.source_snapshot() is None
    assert page._source_tabs._indicator.text() == MDB_NOT_LOADED_TEXT
    assert ctx.mdb_import_snapshot is None


def test_mdb_text_is_read_only(monkeypatch):
    ctx = _context()
    page = _page(TextPage, ctx)
    _select(page, "mdb")
    calls = []
    monkeypatch.setattr(ctx.snapshot_manager, "mark_modified", lambda: calls.append(1))
    before = copy.deepcopy(ctx.mdb_import_snapshot)
    assert not page._fill_btn.isEnabled()
    page._fill_btn.setEnabled(True)  # page code re-enabling must not stick
    assert not page._fill_btn.isEnabled()
    page._on_fill_from_en()
    page._on_rebuild()
    page._on_item_changed(QTableWidgetItem("edited"))
    assert calls == []
    assert ctx.mdb_import_snapshot == before
    _select(page, "pdm")
    assert page._fill_btn.isEnabled()


def test_mdb_relation_does_not_ensure_or_rebuild(monkeypatch):
    ctx = _context()
    page = _page(RelationPage, ctx)
    calls = []
    for svc, names in (
        (ctx.engineering_relation_service, ("ensure_relation_objects", "rebuild_relation_objects")),
        (ctx.engineering_value_table_service, ("ensure_value_tables", "rebuild_value_tables")),
    ):
        for name in names:
            monkeypatch.setattr(svc, name, lambda *a, _n=name, **k: calls.append(_n))
    _select(page, "mdb")
    page.on_enter()
    page._on_rebuild()
    page._on_new()
    page._on_delete()
    assert calls == []
    assert [r.name for r in page._all_relations] == ["PA_IMPORTED", "B_IMPORTED"]


def test_mdb_pricing_cannot_compute_or_edit(monkeypatch):
    ctx = _context()
    page = _page(PricingPage, ctx)
    _select(page, "mdb")
    calls = []
    monkeypatch.setattr(ctx.snapshot_manager, "mark_modified", lambda: calls.append(1))
    before = copy.deepcopy(ctx.mdb_import_snapshot)
    assert not page._compute_btn.isEnabled()
    assert not page._pricelists_btn.isEnabled()
    page._on_compute()
    page._on_manage_price_lists()
    page._on_pricing_finished(type("R", (), {"records": []})())
    assert calls == [] and ctx.mdb_import_snapshot == before
    assert len(page._records) == 1


def test_mdb_pricing_relation_never_generates(monkeypatch):
    ctx = _context()
    page = _page(PricingRelationPage, ctx)
    generated = []
    from services.pricing_relation_service import PricingRelationService

    for name in ("generate", "commit", "commit_split", "generate_component_relations"):
        monkeypatch.setattr(
            PricingRelationService, name, lambda *a, _n=name, **k: generated.append(_n)
        )
    _select(page, "mdb")
    page.on_enter()
    page._on_generate()
    assert generated == []
    assert "PA_IMPORTED" in page._editor.toPlainText()
    assert "B_IMPORTED" not in page._editor.toPlainText()
    assert [r.name for r in ctx.mdb_import_snapshot.relation_objects] == [
        "PA_IMPORTED", "B_IMPORTED"
    ]


def test_mdb_class_creation_skips_ensure_standard_classes(monkeypatch):
    ctx = _context()
    page = _page(ClassCreationPage, ctx)
    calls = []
    monkeypatch.setattr(
        ctx.engineering_class_service, "ensure_standard_classes",
        lambda *a, **k: calls.append(1) or [],
    )
    _select(page, "mdb")
    assert calls == []
    page.refresh()
    assert calls == []
    _select(page, "pdm")
    assert calls == [1]  # PDM behaviour unchanged


def test_mdb_articles_does_not_reduce(monkeypatch):
    ctx = _context()
    page = _page(ArticlesPage, ctx)
    calls = []
    monkeypatch.setattr(
        ctx.engineering_reduction_service, "validate_article_sets",
        lambda *a, **k: calls.append(1) or [],
    )
    _select(page, "mdb")
    page._on_apply_base_length()
    assert calls == []
    assert not page._apply_len_btn.isEnabled()
