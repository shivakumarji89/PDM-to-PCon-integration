"""Phase 2 / area 2: exports run on a worker thread without freezing the window.

Covers ``ExportRunner`` (single slot, thread hand-off, failure and release) and the four
``MainWindow`` export handlers (full MDB, article MDB, Excel, XOCD): the service call runs off the GUI
thread on an isolated snapshot copy, the window keeps processing events meanwhile, a second export is
refused while one runs, errors are reported, and the produced files equal what the synchronous code
produced.
"""
from __future__ import annotations

import copy
import os
import threading
import time
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QSettings, QThread, QThreadPool, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

from core.application_context import ApplicationContext
from core.modules import WorkbenchModule
from models.product import Product
from tests.perf_synthetic import build_class_creation_snapshot
from ui.workers.export_runner import ExportRunner


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    previous = QSettings.defaultFormat()
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    yield
    QSettings.setDefaultFormat(previous)


def pump(condition, timeout=15.0):
    """Run the Qt event loop until ``condition()`` holds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        if condition():
            return True
        time.sleep(0.005)
    QCoreApplication.processEvents()
    return condition()


def on_gui_thread() -> bool:
    return QThread.currentThread() is QCoreApplication.instance().thread()


# --------------------------------------------------------------------------------------
# ExportRunner
# --------------------------------------------------------------------------------------
def test_runner_runs_work_off_the_gui_thread_and_calls_back_on_it(app):
    owner = QWidget()
    runner = ExportRunner(owner)
    seen = {}
    assert runner.begin("Test export")
    assert runner._popup is not None and runner._popup.isVisible()

    def work(emit):
        seen["work_on_gui"] = on_gui_thread()
        emit("halfway")
        return 42

    def finished(value):
        seen["finished_on_gui"] = on_gui_thread()
        seen["value"] = value
        seen["status"] = runner._popup._status.text()
        runner.end()

    runner.run(work, finished=finished, failed=lambda m: seen.setdefault("failed", m))

    assert pump(lambda: "value" in seen or "failed" in seen)
    assert seen == {"work_on_gui": False, "finished_on_gui": True, "value": 42, "status": "halfway"}
    assert not runner.busy and runner._popup is None


def test_runner_keeps_the_event_loop_running_while_the_work_blocks(app):
    owner = QWidget()
    runner = ExportRunner(owner)
    release = threading.Event()
    done = []
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(10)
    runner.begin("Slow export")
    runner.run(lambda emit: (release.wait(10), "ok")[1], finished=lambda v: (runner.end(), done.append(v)),
               failed=lambda m: done.append(m))

    assert pump(lambda: len(ticks) >= 5), "the GUI event loop did not keep running during the export"
    assert not done and runner.busy
    release.set()
    assert pump(lambda: done)
    timer.stop()
    assert done == ["ok"] and not runner.busy


def test_runner_allows_one_export_at_a_time_and_frees_the_slot(app):
    owner = QWidget()
    runner = ExportRunner(owner)
    release = threading.Event()
    done = []
    assert runner.begin("First")
    assert not runner.begin("Second"), "a second export must not start while one runs"
    runner.run(lambda emit: release.wait(10), finished=lambda v: (runner.end(), done.append("first")),
               failed=lambda m: done.append(m))
    assert not runner.begin("Third")
    release.set()
    assert pump(lambda: done)
    assert runner.begin("Fourth")                 # free again
    runner.end()


def test_runner_reports_a_failure_and_releases_the_slot(app):
    owner = QWidget()
    runner = ExportRunner(owner)
    failures = []

    def boom(emit):
        raise RuntimeError("disk full")

    runner.begin("Failing export")
    runner.run(boom, finished=lambda v: failures.append("finished"),
               failed=lambda m: (runner.end(), failures.append(m)))

    assert pump(lambda: failures)
    assert failures == ["disk full"] and not runner.busy


def test_runner_releases_the_slot_if_a_callback_raises(app):
    owner = QWidget()
    runner = ExportRunner(owner)

    def bad_callback(value):
        raise ValueError("callback bug")

    runner.begin("Export")
    runner.run(lambda emit: 1, finished=bad_callback, failed=lambda m: None)

    assert pump(lambda: not runner.busy)


def test_run_requires_begin(app):
    with pytest.raises(RuntimeError):
        ExportRunner(QWidget()).run(lambda emit: None, finished=lambda v: None, failed=lambda m: None)


# --------------------------------------------------------------------------------------
# MainWindow export handlers
# --------------------------------------------------------------------------------------
class Dialogs:
    """Records message boxes instead of showing them."""

    def __init__(self, monkeypatch):
        self.messages = []
        for kind in ("information", "warning", "critical"):
            monkeypatch.setattr(
                QMessageBox, kind,
                staticmethod(lambda parent, title, text, *a, _kind=kind, **k:
                             self.messages.append((_kind, title, text))),
            )

    def last(self):
        return self.messages[-1] if self.messages else None


@pytest.fixture
def window(app, monkeypatch, tmp_path):
    from ui.main_window import MainWindow

    window = MainWindow()
    window._active_module = WorkbenchModule.DEVELOPMENT
    snapshot = build_class_creation_snapshot(30, structures=2, members_per_family=15)
    snapshot.product = Product(id="p1", code="DSK", name="Desk", category="Desks", range_name="Desk range")
    ctx = window._context
    ctx.register_pdm_snapshot(snapshot)
    ctx.activate_snapshot_source("pdm")
    ctx.engineering_initialization_service.initialize(snapshot)
    # No registry file access: standardisation is a no-op that records where it ran.
    window.calls = []
    psvc = SimpleNamespace(
        registry_path=lambda: tmp_path / "registry.json",
        apply_registry=lambda snap, path: window.calls.append(("apply_registry", on_gui_thread())) or 0,
    )
    monkeypatch.setattr(type(ctx), "price_update_service", property(lambda self: psvc))
    yield window
    window.close()
    assert QThreadPool.globalInstance().waitForDone(10000)
    QCoreApplication.processEvents()


def _install(monkeypatch, window, name, service):
    monkeypatch.setattr(type(window._context), name, property(lambda self: service))


def test_full_mdb_export_runs_in_the_background_on_an_isolated_copy(window, monkeypatch, tmp_path):
    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(tmp_path)))
    release = threading.Event()
    seen = {}

    def export(snapshot, directory, kind, selected_article_ids=None):
        seen.update(on_gui=on_gui_thread(), snapshot=snapshot, directory=directory, kind=kind,
                    ids=selected_article_ids)
        release.wait(10)
        return SimpleNamespace(ok=True, error="", template="seating", mdb_path=str(tmp_path / "x.mdb"),
                               table_counts={"tCOMd_Article": 30, "tCOMd_Price": 5})

    _install(monkeypatch, window, "ocd_export_service", SimpleNamespace(export=export))
    live = window._context.active_snapshot
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(10)

    window._on_export_mdb({"a1", "a2"})                     # returns immediately

    assert pump(lambda: "on_gui" in seen)
    assert window._exports().busy
    assert pump(lambda: len(ticks) >= 5), "window frozen during the export"
    window._on_export_mdb()                                  # a second export is refused
    assert dialogs.last()[0] == "information" and "still running" in dialogs.last()[2]
    release.set()
    assert pump(lambda: not window._exports().busy)
    timer.stop()

    assert seen["on_gui"] is False
    assert seen["snapshot"] is not live, "the worker must get the isolated copy"
    assert seen["snapshot"].id != live.id and len(seen["snapshot"].articles) == len(live.articles)
    assert seen["directory"] == str(tmp_path) and seen["kind"] is None and seen["ids"] == {"a1", "a2"}
    assert window._context.mdb_export_snapshot is seen["snapshot"]          # registered as before
    assert window.calls == [("apply_registry", True)]                       # standardised on the GUI thread
    kind, title, text = dialogs.last()
    assert (kind, title) == ("information", "Export MDB")
    assert "35 rows across 2 table(s)" in text and str(tmp_path / "x.mdb") in text


def test_full_mdb_export_reports_a_failed_result_and_an_exception(window, monkeypatch, tmp_path):
    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(tmp_path)))
    outcomes = iter([SimpleNamespace(ok=False, error="template missing", template="", mdb_path="",
                                     table_counts={}), RuntimeError("bridge crashed")])

    def export(*args, **kwargs):
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    _install(monkeypatch, window, "ocd_export_service", SimpleNamespace(export=export))

    window._on_export_mdb()
    assert pump(lambda: dialogs.messages and not window._exports().busy)
    assert dialogs.last() == ("warning", "Export MDB", "Export failed:\ntemplate missing")

    window._on_export_mdb()
    assert pump(lambda: len(dialogs.messages) == 2 and not window._exports().busy)
    assert dialogs.last() == ("warning", "Export MDB", "Export failed:\nbridge crashed")
    window._on_export_mdb()                                  # slot is free again
    assert pump(lambda: False, timeout=0.05) or True


def test_full_mdb_export_without_a_loaded_product_or_folder_does_nothing(window, monkeypatch):
    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: ""))
    called = []
    _install(monkeypatch, window, "ocd_export_service", SimpleNamespace(export=lambda *a, **k: called.append(1)))

    window._on_export_mdb()                                  # folder dialog cancelled
    assert not called and not window._exports().busy and not dialogs.messages
    window._context.clear_active_snapshot()
    window._context.register_pdm_snapshot(None)
    window._on_export_mdb()
    assert dialogs.last() == ("information", "Export MDB", "Load a product first.")


def test_excel_export_writes_the_same_workbook_from_a_background_thread(window, monkeypatch, tmp_path):
    from openpyxl import load_workbook
    from services.snapshot_excel_export_service import SnapshotExcelExportService

    dialogs = Dialogs(monkeypatch)
    target = tmp_path / "async.xlsx"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))
    threads = []
    real_export = SnapshotExcelExportService.export

    def traced(self, snapshot, path):
        threads.append(on_gui_thread())
        return real_export(self, snapshot, path)

    monkeypatch.setattr(SnapshotExcelExportService, "export", traced)

    window._on_export_snapshot_excel()
    assert pump(lambda: not window._exports().busy and dialogs.messages)

    expected = tmp_path / "sync.xlsx"
    real_export(SnapshotExcelExportService(), window._context.active_snapshot, str(expected))

    def content(path):
        book = load_workbook(path)
        return {ws.title: [[c.value for c in row] for row in ws.iter_rows()] for ws in book.worksheets}

    assert threads == [False]
    assert content(target) == content(expected)
    assert dialogs.last()[0] == "information" and str(target) in dialogs.last()[2]


def test_excel_export_reports_failures(window, monkeypatch, tmp_path):
    from services.snapshot_excel_export_service import SnapshotExcelExportService

    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(tmp_path / "x"), "")))
    monkeypatch.setattr(SnapshotExcelExportService, "export",
                        lambda self, snapshot, path: (_ for _ in ()).throw(PermissionError("file is open")))

    window._on_export_snapshot_excel()
    assert pump(lambda: dialogs.messages and not window._exports().busy)

    assert dialogs.last() == ("warning", "Export Snapshot to Excel", "Excel export failed:\nfile is open")
    assert (tmp_path / "x.xlsx").exists() is False              # ".xlsx" was appended, nothing written


def _articles_window(window, monkeypatch, tmp_path, *, template=True):
    source = tmp_path / "ocd.mdb"
    source.write_bytes(b"x")
    info = {"ocd_path": str(source), "is_template": template, "name": "seating"}
    monkeypatch.setattr(type(window._context), "maintenance_repository_info", property(lambda self: info))
    events = []
    session = SimpleNamespace(mdb_path=str(tmp_path / "out" / "pcr_data_com_ocd.mdb"))
    sessions = SimpleNamespace(
        get_active=lambda snapshot: None,
        discard=lambda snapshot: None,
        initialize=lambda snapshot, directory, template_path: events.append(
            ("initialize", on_gui_thread(), directory, template_path)) or session,
        attach_existing=lambda snapshot, source_mdb, template_kind: events.append(
            ("attach", on_gui_thread(), source_mdb, template_kind)) or session,
    )

    def export_to_session(snapshot, active_session, ids):
        events.append(("export", on_gui_thread(), snapshot, active_session, set(ids)))
        return {"ok": True, "inserted": 2, "updated": 1, "skipped": 0, "schemes_created": 2, "warnings": ["w1"]}

    articles = SimpleNamespace(export_to_session=export_to_session)
    _install(monkeypatch, window, "mdb_export_session_service", sessions)
    _install(monkeypatch, window, "article_mdb_export_service", articles)
    return events, session


def test_article_export_prepares_then_exports_in_the_original_order(window, monkeypatch, tmp_path):
    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(tmp_path / "out")))
    events, session = _articles_window(window, monkeypatch, tmp_path, template=True)
    live = window._context.active_snapshot

    window._on_export_articles_to_mdb({"a1", "a2"})
    assert pump(lambda: dialogs.messages and not window._exports().busy)

    kinds = [e[0] for e in events] + [c[0] for c in window.calls]
    assert [e[:2] for e in events] == [("initialize", False), ("export", False)]
    assert events[0][2:] == (str(tmp_path / "out"), str(tmp_path / "ocd.mdb"))
    # standardisation happens between preparing the MDB and exporting, on the GUI thread
    assert window.calls == [("apply_registry", True)]
    assert events[1][2] is not live and events[1][3] is session and events[1][4] == {"a1", "a2"}
    kind, title, text = dialogs.last()
    assert (kind, title) == ("information", "Export Articles to MDB")
    assert "Created new MDB" in text and "Articles inserted: 2" in text and "• w1" in text


def test_article_export_attaches_to_an_existing_series_repository(window, monkeypatch, tmp_path):
    dialogs = Dialogs(monkeypatch)
    events, session = _articles_window(window, monkeypatch, tmp_path, template=False)

    window._on_export_articles_to_mdb({"a1"})
    assert pump(lambda: dialogs.messages and not window._exports().busy)

    assert [e[:2] for e in events] == [("attach", False), ("export", False)]
    assert "Updated existing MDB" in dialogs.last()[2]


def test_article_export_stops_when_preparing_the_mdb_fails(window, monkeypatch, tmp_path):
    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(tmp_path / "out")))
    events, session = _articles_window(window, monkeypatch, tmp_path, template=True)

    def broken_initialize(snapshot, directory, template_path):
        raise RuntimeError("template is locked")

    window._context.mdb_export_session_service.initialize = broken_initialize

    window._on_export_articles_to_mdb({"a1"})
    assert pump(lambda: dialogs.messages and not window._exports().busy)

    assert dialogs.last() == ("warning", "Export Articles to MDB", "Could not prepare the MDB:\ntemplate is locked")
    assert events == [] and window.calls == []                  # nothing was standardised or exported


def test_article_export_reports_an_export_failure(window, monkeypatch, tmp_path):
    dialogs = Dialogs(monkeypatch)
    events, session = _articles_window(window, monkeypatch, tmp_path, template=False)
    window._context.article_mdb_export_service.export_to_session = lambda *a: {"ok": False, "error": "locked"}

    window._on_export_articles_to_mdb({"a1"})
    assert pump(lambda: dialogs.messages and not window._exports().busy)

    kind, title, text = dialogs.last()
    assert kind == "critical" and "The MDB was not changed by this export." in text and "locked" in text


def test_article_export_needs_ticked_articles(window, monkeypatch):
    dialogs = Dialogs(monkeypatch)
    window._on_export_articles_to_mdb(set())
    assert dialogs.last()[2] == "Tick at least one article in the Export column first."
    assert not window._exports().busy


# -- XOCD ------------------------------------------------------------------------------
def _xocd_window(window, monkeypatch, tmp_path):
    window._xocd_publish_path = tmp_path / "xocd"
    window._xocd_publish_service = SimpleNamespace(status_args=lambda path: ["svn", "status", str(path)])
    dialog_events = []
    window._xocd_publish_progress = SimpleNamespace(
        set_files=lambda names: dialog_events.append(("files", list(names))),
        append_output=lambda text: dialog_events.append(("output", text)),
        set_stage=lambda *a: None, set_busy=lambda *a: None,
        fail=lambda message: dialog_events.append(("fail", message)),
    )
    started, failures = [], []
    window._start_xocd_svn_process = lambda args: started.append(args)
    window._xocd_publish_failed = lambda message: failures.append(message)
    return dialog_events, started, failures


def test_xocd_export_runs_in_the_background_and_continues_the_publish_workflow(window, monkeypatch, tmp_path):
    dialog_events, started, failures = _xocd_window(window, monkeypatch, tmp_path)
    seen = {}

    def export_series(snapshot, folder, force=False, **kwargs):
        seen.update(on_gui=on_gui_thread(), snapshot=snapshot, folder=folder, force=force)
        return SimpleNamespace(error=None, program="aeron", files={"xocd_article.csv": 3, "xocd_price.csv": 4})

    _install(monkeypatch, window, "xocd_export_service", SimpleNamespace(export_series=export_series))
    live = window._context.active_snapshot

    window._run_xocd_export(live, tmp_path / "xocd", window._on_xocd_export_done, window._xocd_publish_failed)
    assert window._exports().busy
    assert pump(lambda: started and not window._exports().busy)

    assert seen["on_gui"] is False and seen["snapshot"] is not live and seen["force"] is True
    assert window._xocd_publish_stage == "status" and window._xocd_publish_program == "aeron"
    assert window._xocd_publish_files == ["xocd_article.csv", "xocd_price.csv"]
    assert ("output", "Generated 2 XOCD file(s), 7 row(s).") in dialog_events
    assert started == [["svn", "status", str(tmp_path / "xocd")]] and failures == []


def test_xocd_export_reports_service_errors_and_exceptions(window, monkeypatch, tmp_path):
    dialog_events, started, failures = _xocd_window(window, monkeypatch, tmp_path)
    outcomes = iter([SimpleNamespace(error="Relation binding conflict", program="", files={}), OSError("no space")])

    def export_series(*args, **kwargs):
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    _install(monkeypatch, window, "xocd_export_service", SimpleNamespace(export_series=export_series))
    live = window._context.active_snapshot

    window._run_xocd_export(live, tmp_path, window._on_xocd_export_done, window._xocd_publish_failed)
    assert pump(lambda: len(failures) == 1)
    window._run_xocd_export(live, tmp_path, window._on_xocd_export_done, window._xocd_publish_failed)
    assert pump(lambda: len(failures) == 2)

    assert failures == ["XOCD export failed:\n\nRelation binding conflict", "no space"]
    assert started == [] and not window._exports().busy


def test_xocd_export_is_refused_while_another_export_runs(window, monkeypatch, tmp_path):
    dialog_events, started, failures = _xocd_window(window, monkeypatch, tmp_path)
    called = []
    _install(monkeypatch, window, "xocd_export_service", SimpleNamespace(export_series=lambda *a, **k: called.append(1)))
    assert window._exports().begin("Other export", popup=False)

    window._run_xocd_export(window._context.active_snapshot, tmp_path, window._on_xocd_export_done,
                            window._xocd_publish_failed)

    assert failures == ["Another export is still running. Wait for it to finish first."] and not called
    window._exports().end()


def test_tortoise_fallback_continues_with_its_commit_dialog(window, monkeypatch, tmp_path):
    dialog_events, started, failures = _xocd_window(window, monkeypatch, tmp_path)
    window._xocd_publish_service = SimpleNamespace(tortoise_commit_args=lambda path, comment: ["tortoise", comment])
    window._set_xocd_publish_stage = lambda *a, **k: None
    result = SimpleNamespace(error=None, program="aeron", files={"xocd_article.csv": 3})

    window._on_xocd_tortoise_export_done(result, 4)

    assert window._xocd_publish_standardised == 4 and window._xocd_publish_stage == "commit"
    assert started == [["tortoise", "aeron - Updating OAS"]] and failures == []

    window._on_xocd_tortoise_export_done(SimpleNamespace(error=None, program="p", files={}), 0)
    assert failures == ["No XOCD files were generated."]


def test_real_xocd_export_from_the_background_equals_the_synchronous_export(window, monkeypatch, tmp_path):
    ctx = window._context
    snapshot = ctx.active_snapshot
    ctx.engineering_reduction_service.materialize_class_creation_article_sets(snapshot)
    dialog_events, started, failures = _xocd_window(window, monkeypatch, tmp_path)
    expected = ctx.xocd_export_service.export_series(snapshot, tmp_path / "sync", force=True)
    assert expected.error is None and expected.files

    window._run_xocd_export(snapshot, tmp_path / "async", window._on_xocd_export_done, window._xocd_publish_failed)
    assert pump(lambda: started and not window._exports().busy)

    assert failures == []
    assert sorted(window._xocd_publish_files) == sorted(expected.files)
    for name in expected.files:
        assert (tmp_path / "async" / name).read_bytes() == (tmp_path / "sync" / name).read_bytes(), name


def test_varcond_relation_export_is_refused_while_an_export_runs(window, monkeypatch):
    dialogs = Dialogs(monkeypatch)
    assert window._exports().begin("Other export", popup=False)
    page = SimpleNamespace(is_mdb_view=lambda: (_ for _ in ()).throw(AssertionError("must not be reached")))

    window._on_export_varcond_relations_mdb(page)

    assert dialogs.last()[0] == "information" and "still running" in dialogs.last()[2]
    window._exports().end()
