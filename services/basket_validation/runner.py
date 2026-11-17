"""Runs the existing standalone pCon.basket CE automation (``step18_batch_obx.py``) on COPIES of OBX files.

Pure Python (no Qt, no OCD Engine, no Playwright import): the automation is launched as a subprocess with its own
interpreter, so none of its code loads into the Workbench. Nothing here decides PASS - the verdict is read back from the
automation's own report (``step18_batch_report.json``) and anything missing or inconsistent is reported as not passed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Sequence

DEFAULT_AUTOMATION_ROOT = Path(r"C:\pcon_automation")
SCRIPT_NAME = "step18_batch_obx.py"
ENV_ROOT, ENV_PYTHON, ENV_RUNS = "MK_BASKET_AUTOMATION_ROOT", "MK_BASKET_AUTOMATION_PYTHON", "MK_BASKET_RUNS_DIR"

# The 11 checks of step18 (order as in the script), with readable labels. Unknown keys are still shown.
CHECK_LABELS = {
    "import_count_and_numbers": "Import: article count and numbers match",
    "all_selected": "All imported articles selected",
    "checkboxes_verified_unchecked": "Header Data checkboxes unchecked",
    "update_clicked_once": "Update articles clicked once",
    "popup_captured_and_closed": "Update result popup captured and closed",
    "popup_updated_equals_selected": "Popup: updated count equals selected",
    "export_valid": "OBX export succeeded",
    "export_count_and_numbers": "Export: article count and numbers match",
    "export_descriptions_mfr_series_match": "Export: descriptions, manufacturer, series unchanged",
    "export_price_date_all_updated": "Export: price date updated for all articles",
    "cleanup": "Session closed without saving",
}
PHASES = ["open", "import", "verify_import", "update_options", "update_running", "final_popup", "export", "validate_export", "done"]
PHASE_LABELS = {"open": "Opening pCon.basket CE", "import": "Importing OBX", "verify_import": "Verifying import",
                "update_options": "Preparing article update", "update_running": "Updating articles",
                "final_popup": "Reading update result", "export": "Exporting OBX", "validate_export": "Validating export",
                "done": "File finished"}
_PHASE_LINE = re.compile(r"\[(?P<file>[^\]]+)\] phase: (?P<phase>\w+)")

PASS, FAIL, NOT_VERIFIED, ERROR = "PASS", "FAIL", "NOT VERIFIED", "ERROR"


class BasketValidationUnavailable(RuntimeError):
    """The automation cannot be started (missing folder/interpreter/script/input). Carries a user-readable message."""


@dataclass(frozen=True)
class AutomationConfig:
    automation_root: Path = DEFAULT_AUTOMATION_ROOT
    python_exe: Path | None = None            # default: <automation_root>\.venv\Scripts\python.exe
    runs_dir: Path | None = None              # default: %LOCALAPPDATA%\MK Product Workbench\basket_validation
    update_date: str | None = None            # MM/DD/YYYY; default: today

    @classmethod
    def from_environment(cls) -> "AutomationConfig":
        env = os.environ
        return cls(automation_root=Path(env.get(ENV_ROOT) or DEFAULT_AUTOMATION_ROOT),
                   python_exe=Path(env[ENV_PYTHON]) if env.get(ENV_PYTHON) else None,
                   runs_dir=Path(env[ENV_RUNS]) if env.get(ENV_RUNS) else None)

    @property
    def script(self) -> Path:
        return Path(self.automation_root) / SCRIPT_NAME

    @property
    def python(self) -> Path:
        return Path(self.python_exe) if self.python_exe else Path(self.automation_root) / ".venv" / "Scripts" / "python.exe"

    @property
    def runs_base(self) -> Path:
        if self.runs_dir:
            return Path(self.runs_dir)
        base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        return Path(base) / "MK Product Workbench" / "basket_validation"

    @property
    def date_text(self) -> str:
        return self.update_date or date.today().strftime("%m/%d/%Y")


@dataclass
class FileResult:
    filename: str
    status: str                                # PASS / FAIL / NOT VERIFIED / ERROR
    reason: str = ""
    checks: dict[str, bool] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    evidence_dir: str = ""
    export_file: str = ""
    seconds: float | None = None


@dataclass
class ValidationResult:
    overall: str                               # PASS / FAIL / NOT VERIFIED / ERROR / CANCELLED
    message: str
    run_dir: Path | None = None
    files: list[FileResult] = field(default_factory=list)
    originals_unchanged: bool | None = None
    hashes_before: dict[str, str] = field(default_factory=dict)
    exit_code: int | None = None

    @property
    def passed(self) -> bool:
        return self.overall == PASS

    @property
    def evidence_dir(self) -> Path | None:
        return self.run_dir


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _preflight(obx_paths: Sequence[Path], config: AutomationConfig) -> list[Path]:
    if not Path(config.automation_root).is_dir():
        raise BasketValidationUnavailable(f"pCon.basket automation folder not found: {config.automation_root}")
    if not config.script.is_file():
        raise BasketValidationUnavailable(f"Automation script not found: {config.script}")
    if not config.python.is_file():
        raise BasketValidationUnavailable(f"Automation Python interpreter not found: {config.python}")
    if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", config.date_text):
        raise BasketValidationUnavailable(f"Update date must be MM/DD/YYYY, got {config.date_text!r}")
    paths = [Path(p) for p in obx_paths]
    if not paths:
        raise BasketValidationUnavailable("No OBX file selected.")
    for p in paths:
        if p.suffix.lower() != ".obx" or not p.is_file():
            raise BasketValidationUnavailable(f"OBX file not found: {p}")
    names = [p.name.lower() for p in paths]
    if len(set(names)) != len(names):
        raise BasketValidationUnavailable("Two selected OBX files share the same file name; validate them separately.")
    return paths


def _new_run_dir(base: Path) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
    run_dir.mkdir()                                   # never reused: a fresh staging + run folder per execution
    return run_dir


def _friendly_failure(console: str) -> str:
    low = console.lower()
    if "not authenticated" in low:
        return ("pCon.basket CE is not logged in for the automation profile. Log in once using the automation's browser "
                "profile (C:\\pcon_automation, step2_auth_check.py) and run again.")
    if "err_name_not_resolved" in low or "err_internet_disconnected" in low or "net::err" in low:
        return "pCon.basket CE could not be reached (network error). Check the connection to basket.pcon-solutions.com."
    if "profile" in low and ("in use" in low or "singleton" in low or "already" in low):
        return "The automation browser profile is already in use. Close other pCon automation browser windows and run again."
    return ""


def parse_report(report_path: Path, expected: Sequence[str]) -> list[FileResult]:
    """Per-file results from the automation's own report. A file without a result is ERROR, never PASS."""
    data = json.loads(Path(report_path).read_text(encoding="utf-8"))
    by_name = {r.get("filename"): r for r in data.get("results", [])}
    out: list[FileResult] = []
    for name in expected:
        r = by_name.get(name)
        if r is None:
            out.append(FileResult(name, ERROR, "The automation produced no result for this file."))
            continue
        checks = {k: bool(v) for k, v in (r.get("checks") or {}).items()}
        status = str(r.get("status") or ERROR)
        if status == PASS and (not checks or not all(checks.values())):
            status = FAIL                              # never trust a PASS without every check confirmed
        out.append(FileResult(name, status, str(r.get("status_reason") or ""), checks, [str(e) for e in r.get("errors") or []],
                              str(r.get("evidence_dir") or ""), str(r.get("export_file") or ""), r.get("seconds_total")))
    return out


def run_validation(obx_paths: Sequence[Path | str], config: AutomationConfig | None = None,
                   on_progress: Callable[[str, str | None], None] | None = None,
                   cancel: threading.Event | None = None) -> ValidationResult:
    """Copy the OBX files to a fresh staging folder, run the automation on the copies, read back its verdict.

    Raises :class:`BasketValidationUnavailable` when it cannot start. Never modifies the original files; their SHA-256
    is compared before/after and a change makes the overall result ERROR.
    """
    config = config or AutomationConfig.from_environment()
    emit = on_progress or (lambda _m, _p=None: None)
    paths = _preflight(obx_paths, config)
    run_dir = _new_run_dir(config.runs_base)
    staging, out_root = run_dir / "input", run_dir / "run"
    staging.mkdir()
    before = {str(p): sha256_of(p) for p in paths}
    for p in paths:
        shutil.copy2(p, staging / p.name)
    emit(f"Staged {len(paths)} OBX file(s) in {staging}", None)

    command = [str(config.python), str(config.script), str(staging), config.date_text, "--run-root", str(out_root)]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    console: list[str] = []
    cancelled = False
    creation = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    try:
        proc = subprocess.Popen(command, cwd=str(config.automation_root), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", creationflags=creation)
    except OSError as exc:
        raise BasketValidationUnavailable(f"Could not start the automation: {exc}") from exc

    def watch_cancel() -> None:
        nonlocal cancelled
        while proc.poll() is None:
            if cancel is not None and cancel.wait(0.3):
                cancelled = True
                proc.terminate()
                return
            if cancel is None:
                return

    if cancel is not None:
        threading.Thread(target=watch_cancel, daemon=True).start()
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        console.append(line)
        m = _PHASE_LINE.search(line)
        if m:
            emit(f"{m['file']}: {PHASE_LABELS.get(m['phase'], m['phase'])}", m["phase"])
    exit_code = proc.wait()
    (run_dir / "console.log").write_text("\n".join(console), encoding="utf-8")

    after = {str(p): sha256_of(p) for p in paths if p.is_file()}
    unchanged = after == before
    expected = [p.name for p in paths]
    result = ValidationResult(overall=ERROR, message="", run_dir=run_dir, originals_unchanged=unchanged, hashes_before=before, exit_code=exit_code)
    report = out_root / "step18_batch_report.json"
    if cancelled:
        result.overall, result.message = "CANCELLED", "Basket Validation was cancelled; no result is claimed."
    elif exit_code != 0 or not report.is_file():
        result.message = (_friendly_failure("\n".join(console)) or
                          f"The automation failed (exit code {exit_code}, "
                          f"{'no report written' if not report.is_file() else 'report present'}). See {run_dir / 'console.log'}.")
    else:
        try:
            result.files = parse_report(report, expected)
        except (OSError, ValueError) as exc:
            result.message = f"The automation report could not be read: {exc}"
        else:
            statuses = {f.status for f in result.files}
            if statuses == {PASS}:
                result.overall, result.message = PASS, f"All {len(result.files)} file(s) passed every check."
            else:
                friendly = _friendly_failure("\n".join(console)) if ERROR in statuses else ""
                result.overall = FAIL if FAIL in statuses else (NOT_VERIFIED if NOT_VERIFIED in statuses else ERROR)
                bad = [f"{f.filename}: {f.status}" for f in result.files if f.status != PASS]
                result.message = friendly or ("Not passed - " + "; ".join(bad))
    if not unchanged:
        result.overall = ERROR
        result.message = "Original OBX file(s) changed during validation (SHA-256 mismatch)! " + result.message
    summary = {"overall": result.overall, "message": result.message, "originals_unchanged": unchanged, "sha256_before": before,
               "sha256_after": after, "update_date": config.date_text, "command": command, "exit_code": exit_code,
               "files": [f.__dict__ for f in result.files]}
    (run_dir / "workbench_result.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return result
