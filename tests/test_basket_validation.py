"""Basket Validation runner/dialog against a FAKE step18 script (the real automation is exercised manually)."""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import textwrap
from pathlib import Path

import pytest

from services.basket_validation import runner
from services.basket_validation.runner import AutomationConfig, BasketValidationUnavailable

CHECKS = list(runner.CHECK_LABELS)

FAKE = textwrap.dedent('''
    import json, os, sys
    from pathlib import Path
    src, date = Path(sys.argv[1]), sys.argv[2]
    out = Path(sys.argv[sys.argv.index("--run-root") + 1]); out.mkdir(parents=True, exist_ok=True)
    mode = os.environ.get("FAKE_MODE", "pass")
    if os.environ.get("FAKE_TOUCH"):
        Path(os.environ["FAKE_TOUCH"]).write_text("tampered")
    if mode == "crash":
        print("boom"); sys.exit(3)
    if mode == "auth":
        print("ERROR BATCH ABORTED: not authenticated in headless profile")
        (out / "step18_batch_report.json").write_text(json.dumps({"results": []})); sys.exit(0)
    results = []
    for f in sorted(src.glob("*.obx")):
        print(f"[{f.stem}] phase: import"); print(f"[{f.stem}] phase: export")
        checks = {k: True for k in %r}
        status = "PASS"
        if mode == "fail":
            checks["export_count_and_numbers"] = False; status = "FAIL"
        if mode == "liar":                      # claims PASS although a check failed
            checks["cleanup"] = False
        results.append({"filename": f.name, "status": status, "status_reason": "x", "checks": checks, "errors": [],
                        "evidence_dir": str(out / "batch_runs" / f.stem), "export_file": "", "seconds_total": 1.0})
    (out / "step18_batch_report.json").write_text(json.dumps({"update_date_runtime_argument": date, "results": results}))
''' % CHECKS)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    root = tmp_path / "auto"
    root.mkdir()
    (root / runner.SCRIPT_NAME).write_text(FAKE, encoding="utf-8")
    obx = tmp_path / "gen" / "Muecke_Tables_GBP.obx"
    obx.parent.mkdir()
    obx.write_text("<bskArticleList/>", encoding="utf-8")
    cfg = AutomationConfig(automation_root=root, python_exe=Path(sys.executable), runs_dir=tmp_path / "runs", update_date="11/16/2026")
    monkeypatch.delenv("FAKE_TOUCH", raising=False)
    return cfg, obx


def test_pass_reports_all_checks_and_leaves_the_original_untouched(setup, monkeypatch):
    cfg, obx = setup
    before = runner.sha256_of(obx)
    seen = []
    result = runner.run_validation([obx], cfg, lambda m, p=None: seen.append((m, p)))
    assert result.overall == "PASS" and result.passed
    assert result.originals_unchanged is True and runner.sha256_of(obx) == before
    f, = result.files
    assert f.filename == obx.name and f.status == "PASS" and list(f.checks) == CHECKS and all(f.checks.values())
    assert [p for _, p in seen if p] == ["import", "export"]                      # progress parsed from the automation log
    assert (result.run_dir / "input" / obx.name).read_bytes() == obx.read_bytes()  # ran on a copy
    assert (result.run_dir / "workbench_result.json").is_file() and (result.run_dir / "console.log").is_file()


def test_fail_is_reported_with_the_failing_check(setup, monkeypatch):
    cfg, obx = setup
    monkeypatch.setenv("FAKE_MODE", "fail")
    result = runner.run_validation([obx], cfg)
    assert result.overall == "FAIL" and not result.passed
    assert result.files[0].checks["export_count_and_numbers"] is False


def test_pass_is_never_trusted_when_a_check_is_false(setup, monkeypatch):
    cfg, obx = setup
    monkeypatch.setenv("FAKE_MODE", "liar")
    assert runner.run_validation([obx], cfg).overall == "FAIL"


def test_crash_and_missing_report_are_errors_not_pass(setup, monkeypatch):
    cfg, obx = setup
    monkeypatch.setenv("FAKE_MODE", "crash")
    result = runner.run_validation([obx], cfg)
    assert result.overall == "ERROR" and "exit code 3" in result.message and result.files == []


def test_not_authenticated_gives_a_helpful_message(setup, monkeypatch):
    cfg, obx = setup
    monkeypatch.setenv("FAKE_MODE", "auth")
    result = runner.run_validation([obx], cfg)
    assert result.overall == "ERROR" and "not logged in" in result.message
    assert result.files == [] or result.files[0].status == "ERROR"


def test_original_modified_during_run_is_detected(setup, monkeypatch):
    cfg, obx = setup
    monkeypatch.setenv("FAKE_TOUCH", str(obx))
    result = runner.run_validation([obx], cfg)
    assert result.overall == "ERROR" and result.originals_unchanged is False and "SHA-256" in result.message


def test_each_run_gets_a_fresh_folder(setup):
    cfg, obx = setup
    a, b = runner.run_validation([obx], cfg), runner.run_validation([obx], cfg)
    assert a.run_dir != b.run_dir and a.run_dir.parent == b.run_dir.parent


@pytest.mark.parametrize("breakage", ["root", "script", "python", "nofile", "notobx", "dupe", "date"])
def test_unavailable_automation_or_input_raises_a_readable_error(setup, tmp_path, breakage):
    cfg, obx = setup
    files = [obx]
    if breakage == "root":
        cfg = AutomationConfig(automation_root=tmp_path / "nope", python_exe=cfg.python_exe, runs_dir=cfg.runs_dir)
    elif breakage == "script":
        (cfg.automation_root / runner.SCRIPT_NAME).unlink()
    elif breakage == "python":
        cfg = AutomationConfig(automation_root=cfg.automation_root, python_exe=tmp_path / "no_python.exe", runs_dir=cfg.runs_dir)
    elif breakage == "nofile":
        files = [tmp_path / "missing.obx"]
    elif breakage == "notobx":
        txt = tmp_path / "a.txt"
        txt.write_text("x")
        files = [txt]
    elif breakage == "dupe":
        other = tmp_path / "other" / obx.name
        other.parent.mkdir()
        other.write_text("y")
        files = [obx, other]
    elif breakage == "date":
        cfg = AutomationConfig(automation_root=cfg.automation_root, python_exe=cfg.python_exe, runs_dir=cfg.runs_dir, update_date="2026-11-16")
    with pytest.raises(BasketValidationUnavailable):
        runner.run_validation(files, cfg)
    assert not list(cfg.runs_base.glob("*")) if cfg.runs_base.exists() else True   # nothing staged on a failed preflight


def test_default_config_points_at_pcon_automation_and_today(monkeypatch):
    for k in (runner.ENV_ROOT, runner.ENV_PYTHON, runner.ENV_RUNS):
        monkeypatch.delenv(k, raising=False)
    cfg = AutomationConfig.from_environment()
    assert cfg.automation_root == Path(r"C:\pcon_automation") and cfg.script.name == "step18_batch_obx.py"
    assert cfg.python == Path(r"C:\pcon_automation\.venv\Scripts\python.exe")
    assert len(cfg.date_text) == 10 and cfg.date_text[2] == "/"
    monkeypatch.setenv(runner.ENV_ROOT, r"D:\x")
    assert AutomationConfig.from_environment().automation_root == Path(r"D:\x")


def test_dialog_runs_in_a_qthread_and_shows_results(setup, monkeypatch):
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ui.dialogs.basket_validation_dialog import BasketValidationDialog
    cfg, obx = setup
    monkeypatch.setenv("FAKE_MODE", "fail")
    dialog = BasketValidationDialog([obx], cfg)
    assert dialog._worker.isRunning() or dialog._worker.isFinished()
    assert dialog.wait(30000)
    for _ in range(20):
        app.processEvents()
    assert dialog.result is not None and dialog.result.overall == "FAIL"
    assert "FAIL" in dialog.overall_label.text()
    top = dialog.tree.topLevelItem(0)
    assert top.childCount() == len(CHECKS)
    assert [top.child(i).text(1) for i in range(top.childCount())].count("FAIL") == 1
    assert dialog.evidence_button.isEnabled() and dialog.evidence_folder() == dialog.result.run_dir
    dialog.close()


def test_dialog_shows_unavailable_error(setup, tmp_path):
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ui.dialogs.basket_validation_dialog import BasketValidationDialog
    cfg, obx = setup
    bad = AutomationConfig(automation_root=tmp_path / "nope", runs_dir=cfg.runs_dir)
    dialog = BasketValidationDialog([obx], bad)
    assert dialog.wait(30000)
    for _ in range(20):
        app.processEvents()
    assert dialog.result is None and "automation folder not found" in dialog.overall_label.text()
    assert not dialog.evidence_button.isEnabled()
    dialog.close()
