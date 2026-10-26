from __future__ import annotations

import ast
from pathlib import Path
from threading import Event, Thread

import pytest
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent, QObject
from PySide6.QtWidgets import QApplication

from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope
from services.syteline_export.job import ExportJob
from services.syteline_export.pipeline.db import PyodbcExportDb
from services.syteline_export.pipeline.run import ExportRun
from tests.test_syteline_job import LOCK_SQL, make_config, make_job, staging_dirs
from ui.pages.syteline_export_worker import ExportSignals, ExportWorker


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def test_job_adopts_current_token_and_prestart_cancel_does_not_touch_db(tmp_path):
    token = CancellationToken()
    with cancellation_scope(token):
        _original, db = make_job(tmp_path)
        job = ExportJob(make_config(tmp_path), db)
    assert job.cancellation_token is token
    job.cancel()
    job.cancel()
    assert job.execute().status == "cancelled"
    assert db.calls == [] and db.closed
    assert staging_dirs(tmp_path) == []


@pytest.mark.parametrize("policy", ["refuse", "take_over"])
def test_cancel_during_lock_check_never_modifies_locks(tmp_path, policy):
    job, db = make_job(tmp_path, lock_policy=policy)

    def lock_state(*_args):
        job.cancel()
        return [{"ExtractUser": "alice"}]

    db.script[LOCK_SQL] = lock_state
    result = job.execute()
    assert result.status == "cancelled"
    assert len(db.calls) == 1 and db.calls[0][3] == "lock-check"
    assert staging_dirs(tmp_path) == []


def test_cancel_during_lock_acquisition_releases_only_acquired_lock(tmp_path):
    job, db = make_job(tmp_path)
    execute = db.execute

    def cancel_after_acquire(conn, sql, params=(), *, stage=""):
        result = execute(conn, sql, params, stage=stage)
        if sql.startswith("UPDATE Site SET ExtractUser = ?"):
            job.cancel()
        return result

    db.execute = cancel_after_acquire
    result = job.execute()
    assert result.status == "cancelled"
    updates = [call[1] for call in db.calls if call[1].startswith("UPDATE Site")]
    assert len(updates) == 2
    assert " = ?" in updates[0] and " = NULL" in updates[1]
    assert staging_dirs(tmp_path) == [] and db.closed


def test_cancel_after_successful_drive_never_publishes_staged_output(tmp_path, monkeypatch):
    job, _db = make_job(tmp_path)
    drive = job._drive

    def finish_then_cancel(run):
        outcome = drive(run)
        assert outcome == "success"
        job.cancel()
        return outcome

    monkeypatch.setattr(job, "_drive", finish_then_cancel)
    result = job.execute()
    assert result.status == "cancelled" and result.files == ()
    assert list(tmp_path.iterdir()) == []


def test_cancel_in_publication_commit_window_keeps_previous_output(tmp_path):
    class CancelBeforeCommit(CancellationToken):
        def commit(self):
            self.request_cancel()
            super().commit()

    job, db = make_job(tmp_path)
    old = tmp_path / "temp"
    old.mkdir()
    target = old / "PDMExport_item_data.txt"
    target.write_text("previous", encoding="utf-8")
    job = ExportJob(make_config(tmp_path), db, cancellation_token=CancelBeforeCommit())
    result = job.execute()
    assert result.status == "cancelled" and not result.published
    assert target.read_text(encoding="utf-8") == "previous"
    assert staging_dirs(tmp_path) == []


def test_publication_commit_rejects_late_cancel_without_partial_result(tmp_path, monkeypatch):
    import services.syteline_export.job as module
    job, _db = make_job(tmp_path)
    replace = module.os.replace
    replaced = []

    def replace_then_cancel(source, target):
        replace(source, target)
        replaced.append(target)
        job.cancel()

    monkeypatch.setattr(module.os, "replace", replace_then_cancel)
    result = job.execute()
    assert result.status == "success" and len(result.files) == len(replaced) > 1
    assert not job.cancellation_token.is_cancelled()
    assert all(Path(name).exists() for name in result.files)


def test_stage_dispatch_stops_before_the_next_stage_and_still_closes_db(tmp_path):
    job, db = make_job(tmp_path)
    entered = []

    class Run(ExportRun):
        def p07_converted_rows(self):
            entered.append("p07")
            job.cancel()

        def p08_postprocess(self):
            entered.append("p08")

    job._run_factory = Run
    result = job.execute()
    assert result.status == "cancelled" and entered == ["p07"]
    assert db.closed and staging_dirs(tmp_path) == []


@pytest.mark.parametrize("native_supported", [True, False])
def test_export_db_native_cursor_cancel_never_closes_busy_connection(native_supported):
    token = CancellationToken()
    entered, release = Event(), Event()
    errors, cancelled, closed = [], [], []

    class Cursor:
        timeout = 0
        description = [("value",)]

        def execute(self, *_args):
            entered.set()
            assert release.wait(5)
            if native_supported:
                raise RuntimeError("driver cancellation")

        def cancel(self):
            cancelled.append(True)
            if native_supported:
                release.set()
            else:
                raise NotImplementedError()

        def fetchall(self):
            return [(1,)]

        def close(self):
            pass

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            closed.append(True)

    db = PyodbcExportDb(Connection)

    def work():
        try:
            with cancellation_scope(token):
                db.query("c1", "SELECT 1")
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    worker = Thread(target=work)
    worker.start()
    try:
        assert entered.wait(5)
        token.request_cancel()
        db.cancel_active_operation()
        if not native_supported:
            assert worker.is_alive() and closed == []
    finally:
        release.set()
        worker.join(5)
    assert not worker.is_alive()
    assert cancelled == [True] and closed == [True]
    assert len(errors) == 1 and isinstance(errors[0], OperationCancelled)


def test_every_pipeline_cpu_loop_has_a_checkpoint():
    root = Path("services") / "syteline_export" / "pipeline"
    checked = 0
    for path in root.glob("*.py"):
        if path.name in {"db.py", "run_base.py"}:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            for method in cls.body:
                if not isinstance(method, ast.FunctionDef) or method.name == "p11_finally":
                    continue
                for loop in ast.walk(method):
                    if not isinstance(loop, (ast.For, ast.While)):
                        continue
                    calls = [node for node in ast.walk(loop.body[0]) if isinstance(node, ast.Call)]
                    assert any(
                        isinstance(call.func, ast.Attribute) and call.func.attr == "check_abort"
                        or isinstance(call.func, ast.Name) and call.func.id == "checkpoint"
                        for call in calls
                    ), f"{path.name}:{loop.lineno}"
                    checked += 1
    assert checked > 170


def test_destroyed_export_owner_cancels_but_keeps_signals_until_worker_finishes(tmp_path):
    owner = QObject()
    job, db = make_job(tmp_path)
    signals = ExportSignals()
    signals.bind(job, owner)
    results = []
    signals.finished.connect(results.append)
    owner.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert job.cancellation_token.is_cancelled()
    assert shiboken6.isValid(signals)
    ExportWorker(job, signals).run()
    assert [result.status for result in results] == ["cancelled"]
    assert db.calls == []
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert not shiboken6.isValid(signals)


def test_export_worker_maps_shared_cancellation_to_cancelled_not_failed():
    class Job:
        def execute(self):
            raise OperationCancelled("stop")

    signals = ExportSignals()
    results = []
    signals.finished.connect(results.append)
    ExportWorker(Job(), signals).run()
    assert [result.status for result in results] == ["cancelled"]
