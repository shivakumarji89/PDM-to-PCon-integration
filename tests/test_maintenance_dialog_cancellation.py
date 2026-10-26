"""Real Qt worker cancellation, overlap prevention, destruction and retry."""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent, QThreadPool
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from core.cancellation import checkpoint, current_token
from services.version_update_service import VersionUpdateService
from ui.dialogs.base_length_check_dialog import BaseLengthCheckDialog
from ui.dialogs.price_rollover_dialog import PriceRolloverDialog
from ui.dialogs.version_update_dialog import VersionUpdateDialog
from ui.workers.background_task import task_host


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def _pump(predicate):
    deadline = time.monotonic() + 5
    while not predicate():
        assert time.monotonic() < deadline, "Qt worker timed out"
        QCoreApplication.processEvents()
        time.sleep(0.002)


class _Service:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = 0
        self.tokens = []
        self.registry_writes = 0

    def _discover_packages(self, *_):
        return [Path.cwd()]

    def load_special_map(self):
        return {}

    def registry_path(self, *_):
        return Path.cwd() / "unused-registry.csv"

    def write_base_length_registry(self, *_):
        self.registry_writes += 1
        return "unused-registry.csv"

    def series_folders(self, *_):
        return [Path.cwd()]

    def _work(self):
        self.calls += 1
        self.tokens.append(current_token())
        if self.calls == 1:
            self.started.set()
            assert self.release.wait(5)
        checkpoint()
        return []

    def build_base_length_registry(self, *_args, **_kwargs):
        return self._work()

    def read_series(self, *_args, **_kwargs):
        return self._work()

    def update(self, *_args, **_kwargs):
        return self._work()

    def run_batch(self, *_args, **_kwargs):
        self._work()
        return SimpleNamespace(packages=[], error=None)

    parse_version = staticmethod(VersionUpdateService.parse_version)


def _dialog(workflow, svc, monkeypatch, outcomes):
    context = SimpleNamespace(
        price_update_service=svc,
        price_list_service=SimpleNamespace(_day_before=lambda _: "20251231"),
        config=SimpleNamespace(catalogue_region="UK"),
    )
    if workflow.startswith("price"):
        dialog = PriceRolloverDialog(context, str(Path.cwd()))
        dialog._compute.setChecked(False)
        dialog._token.setText("2026")
        monkeypatch.setattr(dialog, "_on_result", lambda *args: outcomes.append(args))
        start = lambda: dialog._run(apply=workflow == "price_apply")
    elif workflow == "base":
        dialog = BaseLengthCheckDialog(context, str(Path.cwd()))
        monkeypatch.setattr(dialog, "_on_ready", lambda *args: outcomes.append(args))
        start = dialog._on_check
    else:
        dialog = VersionUpdateDialog(svc, str(Path.cwd()))
        if workflow == "version_apply":
            dialog._version.setText("1.2.3")
            monkeypatch.setattr(dialog, "_checked_series", lambda: [object()])
            monkeypatch.setattr(dialog, "_on_applied", outcomes.append)
            start = dialog._on_apply
        else:
            monkeypatch.setattr(dialog, "_on_scanned", outcomes.append)
            start = dialog._on_scan
    return dialog, start


@pytest.mark.parametrize("workflow", [
    "price_scan", "price_apply", "base", "version_scan", "version_apply",
])
@pytest.mark.parametrize("destroy", [False, True])
def test_cancel_overlap_retry_and_owner_destruction(workflow, destroy, monkeypatch):
    errors, failures, outcomes, cancelled = [], [], [], []
    monkeypatch.setattr(sys, "excepthook", lambda _t, value, _tb: errors.append(value))
    monkeypatch.setattr(sys, "unraisablehook", lambda info: errors.append(info.exc_value))
    monkeypatch.setattr(QMessageBox, "information", lambda *_: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *_: failures.append("warning"))
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.Yes)
    svc = _Service()
    dialog, start = _dialog(workflow, svc, monkeypatch, outcomes)
    monkeypatch.setattr(dialog, "_on_cancelled", cancelled.append)
    try:
        start()
        first = dialog._run_task
        _pump(svc.started.is_set)
        assert first.active
        assert first.reporter.parent() is first
        assert first.parent() is task_host()
        start()
        assert dialog._run_task is first
        assert svc.calls == 1
        if destroy:
            shiboken6.delete(dialog)
        else:
            dialog._monitor.cancel_requested.emit()
        assert svc.tokens[0].is_cancelled()
        svc.release.set()
        _pump(lambda: not first.active)
        assert outcomes == failures == []
        assert len(cancelled) == (0 if destroy else 1)
        assert svc.registry_writes == 0
        if not destroy:
            start()
            second = dialog._run_task
            _pump(lambda: not second.active)
            assert second is not first
            assert svc.tokens[1] is not svc.tokens[0]
            assert not svc.tokens[1].is_cancelled()
            assert len(outcomes) == 1
            assert len(cancelled) == 1
            assert failures == []
        assert errors == []
    finally:
        svc.release.set()
        QThreadPool.globalInstance().waitForDone(5000)
        if shiboken6.isValid(dialog):
            shiboken6.delete(dialog)
        QCoreApplication.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_rollover_special_followup_cancel_preserves_bulk_completion_message(monkeypatch):
    svc = _Service()
    svc.scan_special_articles = lambda *_: svc._work()
    context = SimpleNamespace(
        price_update_service=svc,
        price_list_service=SimpleNamespace(_day_before=lambda _: "20251231"),
        config=SimpleNamespace(catalogue_region="UK"),
    )
    dialog = PriceRolloverDialog(context, str(Path.cwd()))
    cancelled, outcomes = [], []
    monkeypatch.setattr(dialog, "_on_cancelled", cancelled.append)
    monkeypatch.setattr(dialog, "_on_special_scanned", lambda *args: outcomes.append(args))
    result = SimpleNamespace(packages=[
        SimpleNamespace(package="one.mdb", special_carried=["ABC_X"])])
    try:
        assert dialog._handle_special_articles(result)
        run = dialog._run_task
        _pump(svc.started.is_set)
        dialog._monitor.cancel_requested.emit()
        svc.release.set()
        _pump(lambda: not run.active)
        assert not outcomes
        assert len(cancelled) == 1
        assert "1 package(s) already rolled over" in cancelled[0]
    finally:
        svc.release.set()
        QThreadPool.globalInstance().waitForDone(5000)
        shiboken6.delete(dialog)
        QCoreApplication.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_base_registry_alternate_location_is_cancellable_and_retryable(monkeypatch):
    svc = _Service()

    def write(path, _rows):
        svc._work()
        return path

    svc.write_base_length_registry = write
    dialog = BaseLengthCheckDialog(SimpleNamespace(price_update_service=svc))
    cancelled, ready, remembered = [], [], []
    monkeypatch.setattr(dialog, "_on_cancelled", cancelled.append)
    monkeypatch.setattr(dialog, "_on_ready", lambda *args: ready.append(args))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: ("registry.csv", "CSV"))
    settings = SimpleNamespace(setValue=lambda *args: remembered.append(args))
    try:
        dialog._write_registry(svc, "unwritable.csv", [], settings, "denied")
        first = dialog._run_task
        _pump(svc.started.is_set)
        dialog._monitor.cancel_requested.emit()
        svc.release.set()
        _pump(lambda: not first.active)
        assert len(cancelled) == 1
        assert ready == remembered == []
        dialog._write_registry(svc, "unwritable.csv", [], settings, "denied")
        second = dialog._run_task
        _pump(lambda: not second.active)
        assert second is not first
        assert ready == [([], "registry.csv")]
        assert len(remembered) == 1
    finally:
        svc.release.set()
        QThreadPool.globalInstance().waitForDone(5000)
        shiboken6.delete(dialog)
        QCoreApplication.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
