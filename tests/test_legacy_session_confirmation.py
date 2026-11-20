"""Legacy MDB export session: explicit workspace-type confirmation before any export.

A session saved before ``attached_existing`` existed has an UNKNOWN workspace type. The UI must ask the
user (shared dialog), record the answer through ``declare_attachment`` and only then let an export run;
Cancel records nothing and writes nothing. The service layer refuses legacy sessions as a backstop.
"""
from __future__ import annotations

import inspect
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from core.application_context import ApplicationContext
from core.modules import WorkbenchModule
from models.article import Article
from models.mdb_export_session import MdbExportSession
from models.product import Product
from models.snapshot import Snapshot
from services import mdb_export_session_service as session_module
from services.mdb_export_session_service import ExportSessionError, MdbExportSessionService
from ui.dialogs import workspace_type_dialog as dialog
from ui.pages.class_creation_page import ClassCreationPage
from ui.pages.relation_page import RelationPage
from ui.pages.text_page import TextPage


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


def _snapshot() -> Snapshot:
    snap = Snapshot()
    snap.metadata.source = "PDM"
    snap.product = Product(id="p1", code="P1", name="Product")
    snap.articles = [Article(id="a1", code="ABC")]
    return snap


def _legacy_file(store, mdb) -> dict:
    """A session file written by the earlier version: no attached_existing / attached_flag_known keys."""
    data = {"product_key": "id:p1", "mdb_path": str(mdb), "package_id": 1}
    service = MdbExportSessionService(SimpleNamespace())
    service.store_dir = store
    service._file("id:p1").parent.mkdir(parents=True, exist_ok=True)
    service._file("id:p1").write_text(json.dumps(data), encoding="utf-8")
    return data


@pytest.fixture
def env(tmp_path):
    mdb = tmp_path / "x.mdb"
    mdb.touch()
    store = tmp_path / "store"
    store.mkdir()
    sessions = MdbExportSessionService(SimpleNamespace())
    sessions.store_dir = store
    return SimpleNamespace(mdb=mdb, store=store, sessions=sessions, snapshot=_snapshot())


def _persisted(env) -> dict:
    return json.loads(env.sessions._file("id:p1").read_text(encoding="utf-8"))


# -- model and service ---------------------------------------------------------------------------

def test_old_metadata_is_legacy_and_reload_keeps_it_unknown(env):
    _legacy_file(env.store, env.mdb)
    session = env.sessions.load(env.snapshot)
    assert session.attached_flag_known is False
    # re-saving the loaded session must not turn "unknown" into a known template session
    env.sessions.save(session)
    again = env.sessions.load(env.snapshot)
    assert again.attached_flag_known is False and again.attached_existing is False
    assert dialog.is_legacy_session(again)


@pytest.mark.parametrize("choice", [True, False])
def test_declaration_persists_and_survives_restart(env, choice):
    _legacy_file(env.store, env.mdb)
    session = env.sessions.load(env.snapshot)
    env.sessions.declare_attachment(session, choice)
    assert session.attached_existing is choice and session.attached_flag_known
    restarted = MdbExportSessionService(SimpleNamespace())
    restarted.store_dir = env.store
    recovered = restarted.get_active(env.snapshot)
    assert recovered.attached_existing is choice and recovered.attached_flag_known
    assert not dialog.is_legacy_session(recovered)


def test_known_session_cannot_be_reclassified(env):
    session = MdbExportSession(product_key="id:p1", mdb_path=str(env.mdb), attached_existing=True)
    env.sessions.save(session)
    with pytest.raises(ExportSessionError):
        env.sessions.declare_attachment(session, False)
    assert env.sessions.load(env.snapshot).attached_existing is True


def test_persistence_failure_is_reported_and_leaves_session_unknown(env, monkeypatch):
    _legacy_file(env.store, env.mdb)
    before = _persisted(env)
    session = env.sessions.load(env.snapshot)

    def broken(_session):
        raise OSError("disk full")

    monkeypatch.setattr(env.sessions, "save", broken)
    with pytest.raises(ExportSessionError, match="disk full"):
        env.sessions.declare_attachment(session, True)
    assert session.attached_flag_known is False and session.attached_existing is False
    assert _persisted(env) == before


@pytest.mark.parametrize("module_path, cls, kwargs", [
    ("services.article_mdb_export_service", "ArticleMdbExportService", {}),
    ("services.class_creation_mdb_export_service", "ClassCreationMdbExportService", {}),
    ("services.properties_values_mdb_export_service", "PropertiesValuesMdbExportService", {}),
    ("services.text_mdb_export_service", "TextMdbExportService", {}),
    ("services.relation_mdb_export_service", "RelationMdbExportService", {}),
    ("services.relation_mdb_export_service", "RelationMdbExportService", {"workflow": "pricing_relation"}),
])
@pytest.mark.parametrize("dry_run", [True, False])
def test_every_incremental_service_refuses_a_legacy_session(env, module_path, cls, kwargs, dry_run):
    import importlib
    service_cls = getattr(importlib.import_module(module_path), cls)
    ctx = SimpleNamespace(
        mdb_export_session_service=env.sessions,
        mdb_service=SimpleNamespace(is_available=lambda: pytest.fail("MDB must not be touched")),
    )
    session = MdbExportSession.from_dict({"product_key": "id:p1", "mdb_path": str(env.mdb)})
    result = service_cls(ctx).export_to_session(
        env.snapshot, session, {"a1"}, dry_run=dry_run, **kwargs)
    assert result["ok"] is False and result.get("legacy_session") is True
    assert "Confirm MDB Workspace Type" in result["error"]


# -- shared dialog helper ------------------------------------------------------------------------

def _ask(monkeypatch, answer):
    calls = []
    monkeypatch.setattr(dialog, "ask_workspace_type", lambda parent: calls.append(1) or answer)
    return calls


@pytest.mark.parametrize("answer", [True, False])
def test_helper_records_the_choice(env, monkeypatch, answer):
    _legacy_file(env.store, env.mdb)
    session = env.sessions.load(env.snapshot)
    calls = _ask(monkeypatch, answer)
    assert dialog.ensure_workspace_type_known(None, env.sessions, session) is True
    assert _persisted(env)["attached_existing"] is answer and _persisted(env)["attached_flag_known"] is True
    # a second stage re-reads the persisted session and never prompts again
    assert dialog.ensure_workspace_type_known(None, env.sessions, env.sessions.get_active(env.snapshot))
    assert len(calls) == 1


def test_helper_cancel_changes_nothing(env, monkeypatch):
    _legacy_file(env.store, env.mdb)
    before = _persisted(env)
    session = env.sessions.load(env.snapshot)
    _ask(monkeypatch, None)
    assert dialog.ensure_workspace_type_known(None, env.sessions, session) is False
    assert _persisted(env) == before and session.attached_flag_known is False


def test_helper_reports_a_save_failure_and_stops(env, monkeypatch):
    _legacy_file(env.store, env.mdb)
    before = _persisted(env)
    session = env.sessions.load(env.snapshot)
    _ask(monkeypatch, True)
    shown = []
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a: shown.append(a[2])))
    monkeypatch.setattr(env.sessions, "save", lambda s: (_ for _ in ()).throw(OSError("locked")))
    assert dialog.ensure_workspace_type_known(None, env.sessions, session, "T") is False
    assert shown and "locked" in shown[0]
    assert _persisted(env) == before


@pytest.mark.parametrize("session", [
    MdbExportSession(product_key="k", mdb_path="x"),                           # new template session
    MdbExportSession(product_key="k", mdb_path="x", attached_existing=True),   # attach_existing()
])
def test_known_sessions_never_prompt(env, monkeypatch, session):
    calls = _ask(monkeypatch, True)
    assert dialog.ensure_workspace_type_known(None, env.sessions, session) is True
    assert calls == []


def test_dialog_has_the_required_wording_and_no_default_choice(monkeypatch):
    assert dialog.TITLE == "Confirm MDB Workspace Type"
    assert dialog.EXISTING_LABEL == "Existing Production Workspace"
    assert dialog.TEMPLATE_LABEL == "Newly Initialized Template Workspace"
    assert "earlier version of MK Product Workbench" in dialog.MESSAGE
    seen = {}

    def fake_exec(box):
        seen["default"] = box.defaultButton().text()
        seen["escape"] = box.escapeButton().text()
        seen["texts"] = [b.text() for b in box.buttons()]
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    assert dialog.ask_workspace_type(None) is None          # nothing clicked = cancelled
    assert seen["default"] == seen["escape"] == "Cancel"
    assert seen["texts"] == [dialog.EXISTING_LABEL, dialog.TEMPLATE_LABEL, "Cancel"]


# -- entry points ----------------------------------------------------------------------------------

def _wire_page(monkeypatch, env, cls):
    ctx = ApplicationContext()
    snap = env.snapshot
    ctx.register_pdm_snapshot(snap)
    ctx.activate_snapshot_source("pdm")
    monkeypatch.setattr(ApplicationContext, "mdb_export_session_service", property(lambda self: env.sessions))
    page = cls(ctx)
    page._active_module = WorkbenchModule.MAINTENANCE
    page._pages = {"articles": SimpleNamespace(selected_export_article_ids=lambda: {"a1"})}
    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    return page


def _record_exports(monkeypatch, module_path, cls):
    import importlib
    calls = []

    def fake(self, snapshot, session, *args, **kwargs):
        calls.append({"dry": bool(kwargs.get("dry_run")), "known": session.attached_flag_known})
        return {"ok": True, "counts": {}, "warnings": []}

    monkeypatch.setattr(getattr(importlib.import_module(module_path), cls), "export_to_session", fake)
    return calls


ENTRY_POINTS = [
    ("Class Creation", ClassCreationPage, "_on_export_component_mdb",
     "services.class_creation_mdb_export_service", "ClassCreationMdbExportService"),
    ("Text", TextPage, "_on_export_component_mdb",
     "services.text_mdb_export_service", "TextMdbExportService"),
    ("Relation Object", RelationPage, "_on_export_component_mdb",
     "services.relation_mdb_export_service", "RelationMdbExportService"),
    ("Properties", ClassCreationPage, "_on_export_properties_values_mdb",
     "services.properties_values_mdb_export_service", "PropertiesValuesMdbExportService"),
]


@pytest.mark.parametrize("component, cls, handler, module_path, service", ENTRY_POINTS)
def test_legacy_cancel_performs_no_export_and_keeps_metadata(
        env, monkeypatch, component, cls, handler, module_path, service):
    _legacy_file(env.store, env.mdb)
    before = _persisted(env)
    page = _wire_page(monkeypatch, env, cls)
    page._maintenance_export_component = component
    calls = _record_exports(monkeypatch, module_path, service)
    asked = _ask(monkeypatch, None)
    getattr(page, handler)()
    assert asked == [1] and calls == []
    assert _persisted(env) == before


@pytest.mark.parametrize("answer", [True, False])
@pytest.mark.parametrize("component, cls, handler, module_path, service", ENTRY_POINTS)
def test_legacy_choice_is_recorded_then_export_proceeds_without_reprompt(
        env, monkeypatch, component, cls, handler, module_path, service, answer):
    _legacy_file(env.store, env.mdb)
    page = _wire_page(monkeypatch, env, cls)
    page._maintenance_export_component = component
    calls = _record_exports(monkeypatch, module_path, service)
    asked = _ask(monkeypatch, answer)
    getattr(page, handler)()
    assert asked == [1]
    assert calls and all(c["known"] for c in calls)           # preview ran only after the decision
    assert _persisted(env)["attached_existing"] is answer
    getattr(page, handler)()                                   # next stage / restarted app: same file
    assert asked == [1]


@pytest.mark.parametrize("component, cls, handler, module_path, service", ENTRY_POINTS)
def test_known_and_new_sessions_do_not_prompt(
        env, monkeypatch, component, cls, handler, module_path, service):
    env.sessions.save(MdbExportSession(product_key="id:p1", mdb_path=str(env.mdb)))
    page = _wire_page(monkeypatch, env, cls)
    page._maintenance_export_component = component
    calls = _record_exports(monkeypatch, module_path, service)
    asked = _ask(monkeypatch, True)
    getattr(page, handler)()
    assert asked == [] and calls


def test_articles_varcond_and_pricing_entry_points_resolve_before_acting():
    """Their handlers need a full main window / price worker, so assert the ordering structurally:
    the shared confirmation sits after the session is fetched and before any preview, write or worker."""
    from ui.main_window import MainWindow
    from ui.pages.pricing_page import PricingPage

    def order(func, *later):
        source = inspect.getsource(func)
        gate = source.index("ensure_workspace_type_known(")
        assert source.index("get_active(") < gate
        for marker in later:
            assert gate < source.index(marker), marker

    order(MainWindow._on_export_articles_to_mdb, "prepare = None", "runner.begin(", "export_step")
    order(MainWindow._on_export_varcond_relations_session,
          "prepare_relation_export(", "runner.begin(", "RelationMdbExportService(")
    order(PricingPage._start_export_workflow, "selected_export_article_ids", "mdb_path = session.mdb_path")


def test_session_module_exposes_declare_attachment_as_the_only_decision_path():
    assert hasattr(session_module.MdbExportSessionService, "declare_attachment")
    assert "declare_attachment" in inspect.getsource(dialog.ensure_workspace_type_known)
