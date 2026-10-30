"""File-based client for the MK OBX Generator plugin hosted in pCon.planner.

Why files: the pCon.planner Plugin SDK offers no out-of-process entry point.
A plugin is loaded at application start and can only be driven from inside
pCon.planner (ribbon actions, events, timers). The plugin therefore polls a
job directory; the Workbench drops ``<id>.request.json`` and waits for the
matching ``<id>.result.json``. Requests are written to a ``.pending`` file and
renamed into place so the plugin never reads a half-written document.

This module owns only transport, liveness and process bookkeeping. SDK
semantics live in the plugin; result interpretation lives in the services.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from core.cancellation import OperationCancelled, checkpoint
from services.pcon_sdk_obx import protocol
from services.pcon_sdk_obx.protocol import (
    JobProgress,
    PluginHeartbeat,
    PluginProtocolError,
    PROTOCOL_VERSION,
)

#: Default locations. The plugin uses the same default job directory unless
#: the ``MK_PCON_OBX_JOBS`` environment variable overrides it on both sides.
JOB_DIR_ENV = "MK_PCON_OBX_JOBS"
PLUGIN_NAME = "MKObxGenerator"
PLUGIN_FILES = (f"{PLUGIN_NAME}.dll", f"{PLUGIN_NAME}.xml", f"{PLUGIN_NAME}.ui")

_PLANNER_CANDIDATES = (
    r"C:\Program Files\EasternGraphics\pCon.planner PRO\bin\planner_pro.exe",
    r"C:\Program Files\EasternGraphics\pCon.planner\bin\planner.exe",
)
#: Heartbeats older than this are treated as a dead plugin.
HEARTBEAT_MAX_AGE_SECONDS = 15.0


class PluginUnavailableError(RuntimeError):
    """The plugin is not running inside pCon.planner (no fresh heartbeat)."""


class PluginTimeoutError(RuntimeError):
    """The plugin did not answer within the allowed time."""


def default_job_dir() -> Path:
    override = os.environ.get(JOB_DIR_ENV, "").strip()
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "MKProductWorkbench" / "pcon_obx_jobs"


def default_user_plugin_dir() -> Path:
    """User plugin folder documented in *Getting Started* section 4."""
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "EasternGraphics" / "pCon.planner Pro" / "plugins" / PLUGIN_NAME


def find_planner_executable() -> str:
    for candidate in _PLANNER_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return ""


def find_built_plugin_dir(repo_root: Path | None = None) -> Path | None:
    """Locate the compiled plugin output inside the repository, if built."""
    root = repo_root or Path(__file__).resolve().parents[2]
    plugin_root = root / "tools" / "pcon_obx_plugin"
    for candidate in (
        plugin_root / "bin" / "Release" / "net481",
        plugin_root / "bin" / "Debug" / "net481",
        plugin_root / "dist",
    ):
        if all((candidate / name).is_file() for name in PLUGIN_FILES):
            return candidate
    return None


@dataclass
class BridgeSettings:
    """Mutable settings for one bridge instance (page persists them)."""

    job_dir: Path = field(default_factory=default_job_dir)
    planner_exe: str = field(default_factory=find_planner_executable)
    plugin_install_dir: Path = field(default_factory=default_user_plugin_dir)
    request_timeout: float = 120.0
    generate_timeout: float = 3600.0
    poll_interval: float = 0.25


class PconPluginBridge:
    """Send one request at a time to the plugin and collect its result."""

    def __init__(self, settings: BridgeSettings | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.settings = settings or BridgeSettings()
        self._clock = clock
        self._sleep = sleep
        self._process: subprocess.Popen | None = None

    # -- liveness ---------------------------------------------------------
    @property
    def job_dir(self) -> Path:
        return Path(self.settings.job_dir)

    def ensure_job_dir(self) -> Path:
        self.job_dir.mkdir(parents=True, exist_ok=True)
        return self.job_dir

    def read_heartbeat(self) -> PluginHeartbeat | None:
        path = self.job_dir / protocol.HEARTBEAT_FILE
        data = None
        for _attempt in range(5):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                break
            except FileNotFoundError:
                return None
            except (OSError, json.JSONDecodeError):
                # The plugin replaces the file atomically every few seconds;
                # a read can collide with that rename on Windows.
                self._sleep(0.01)
        if data is None:
            return None
        if not isinstance(data, dict):
            return None
        return PluginHeartbeat.from_dict(data)

    def heartbeat_age(self, heartbeat: PluginHeartbeat | None = None) -> float | None:
        """Seconds since the plugin last wrote its heartbeat (wall clock)."""
        beat = heartbeat or self.read_heartbeat()
        if beat is None or not beat.timestamp:
            return None
        return max(0.0, time.time() - beat.timestamp)

    def is_plugin_alive(self) -> bool:
        beat = self.read_heartbeat()
        if beat is None or not beat.planner_ready:
            return False
        if beat.protocol_version != PROTOCOL_VERSION:
            return False
        age = self.heartbeat_age(beat)
        return age is not None and age <= HEARTBEAT_MAX_AGE_SECONDS

    def describe_status(self) -> str:
        beat = self.read_heartbeat()
        if beat is None:
            return "Plugin not detected: no heartbeat in the job folder."
        age = self.heartbeat_age(beat)
        if beat.protocol_version != PROTOCOL_VERSION:
            return (f"Plugin protocol {beat.protocol_version} does not match the Workbench "
                    f"({PROTOCOL_VERSION}); reinstall the plugin.")
        if age is None or age > HEARTBEAT_MAX_AGE_SECONDS:
            return f"Plugin heartbeat is stale ({age:.0f}s); pCon.planner may have closed."
        if not beat.planner_ready:
            return "pCon.planner is starting; plugin loaded but not ready yet."
        planner = f" (pCon.planner {beat.planner_version})" if beat.planner_version else ""
        return f"Connected to MK OBX Generator plugin {beat.plugin_version}{planner}."

    # -- process management ------------------------------------------------
    def planner_is_running(self) -> bool:
        if self._process is not None and self._process.poll() is None:
            return True
        return self.is_plugin_alive()

    def launch_planner(self) -> bool:
        """Start pCon.planner if we are not already managing an instance."""
        if self.planner_is_running():
            return True
        exe = self.settings.planner_exe or find_planner_executable()
        if not exe or not Path(exe).is_file():
            raise PluginUnavailableError(
                "pCon.planner executable not found. Set the path in the connection settings."
            )
        env = dict(os.environ)
        env[JOB_DIR_ENV] = str(self.ensure_job_dir())
        self._process = subprocess.Popen([exe], cwd=str(Path(exe).parent), env=env)
        return True

    def wait_for_plugin(self, timeout: float = 90.0) -> PluginHeartbeat:
        deadline = self._clock() + timeout
        while self._clock() < deadline:
            checkpoint()
            if self.is_plugin_alive():
                beat = self.read_heartbeat()
                if beat is not None:
                    return beat
            self._sleep(min(1.0, self.settings.poll_interval * 4))
        raise PluginUnavailableError(
            "The MK OBX Generator plugin did not report ready. Check that it is installed "
            "in the pCon.planner plugin folder and licensed to load."
        )

    # -- plugin installation -----------------------------------------------
    def install_plugin(self, source_dir: Path | None = None) -> Path:
        """Copy the built plugin into the user plugin folder (section 4 of Getting Started)."""
        source = Path(source_dir) if source_dir else find_built_plugin_dir()
        if source is None or not all((source / name).is_file() for name in PLUGIN_FILES):
            raise PluginUnavailableError(
                "Built plugin not found. Build tools/pcon_obx_plugin first (see its README)."
            )
        target = Path(self.settings.plugin_install_dir)
        target.mkdir(parents=True, exist_ok=True)
        for entry in source.iterdir():
            if entry.is_file():
                shutil.copy2(entry, target / entry.name)
        return target

    def plugin_installed(self) -> bool:
        target = Path(self.settings.plugin_install_dir)
        return all((target / name).is_file() for name in PLUGIN_FILES)

    # -- requests ----------------------------------------------------------
    def send(self, kind: str, payload: dict[str, Any] | None = None, *,
             timeout: float | None = None,
             on_progress: Callable[[JobProgress], None] | None = None) -> dict[str, Any]:
        """Write a request and block until its result arrives.

        ``checkpoint()`` is honoured while waiting so the shared cancellation
        machinery can abort a long generate run from the UI.
        """
        if not self.is_plugin_alive():
            raise PluginUnavailableError(self.describe_status())
        job_dir = self.ensure_job_dir()
        job_id = uuid.uuid4().hex
        request = protocol.build_request(job_id, kind, payload)
        pending = job_dir / f"{job_id}{protocol.PENDING_SUFFIX}"
        final = job_dir / f"{job_id}{protocol.REQUEST_SUFFIX}"
        pending.write_text(protocol.encode(request), encoding="utf-8")
        os.replace(pending, final)

        result_path = job_dir / f"{job_id}{protocol.RESULT_SUFFIX}"
        progress_path = job_dir / f"{job_id}{protocol.PROGRESS_SUFFIX}"
        cancel_path = job_dir / f"{job_id}{protocol.CANCEL_SUFFIX}"
        limit = timeout if timeout is not None else self.settings.request_timeout
        deadline = self._clock() + limit
        last_progress: tuple[int, int, str] | None = None
        try:
            while True:
                checkpoint()
                if result_path.is_file():
                    text = self._read_complete(result_path)
                    if text is not None:
                        data = protocol.parse_result(text, job_id)
                        return data
                if on_progress is not None and progress_path.is_file():
                    progress = self._read_progress(progress_path)
                    if progress is not None:
                        key = (progress.processed, progress.total, progress.message)
                        if key != last_progress:
                            last_progress = key
                            on_progress(progress)
                if self._clock() >= deadline:
                    raise PluginTimeoutError(
                        f"pCon.planner plugin did not answer the {kind} request within {limit:.0f}s."
                    )
                if not self.is_plugin_alive():
                    raise PluginUnavailableError(
                        "pCon.planner stopped responding while the request was running."
                    )
                self._sleep(self.settings.poll_interval)
        except OperationCancelled:
            # Tell the plugin to stop the running job; it removes the marker
            # itself once it has written its (cancelled) result.
            try:
                cancel_path.write_text("cancel", encoding="utf-8")
            except OSError:
                pass
            raise
        finally:
            # The plugin removes the cancel marker when it sees it; if the job
            # finished before the marker was noticed, remove it here instead.
            for path in (final, pending, progress_path, result_path, cancel_path):
                try:
                    path.unlink()
                except OSError:
                    pass

    @staticmethod
    def _read_complete(path: Path) -> str | None:
        """Return the file text once the writer has finished (valid JSON)."""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None
        if not text.strip():
            return None
        try:
            json.loads(text)
        except json.JSONDecodeError:
            return None
        return text

    @staticmethod
    def _read_progress(path: Path) -> JobProgress | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return JobProgress.from_dict(data) if isinstance(data, dict) else None

    def ping(self) -> dict[str, Any]:
        return self.send(protocol.KIND_PING, timeout=min(30.0, self.settings.request_timeout))


__all__ = [
    "BridgeSettings",
    "HEARTBEAT_MAX_AGE_SECONDS",
    "JOB_DIR_ENV",
    "PLUGIN_FILES",
    "PLUGIN_NAME",
    "PconPluginBridge",
    "PluginProtocolError",
    "PluginTimeoutError",
    "PluginUnavailableError",
    "default_job_dir",
    "default_user_plugin_dir",
    "find_built_plugin_dir",
    "find_planner_executable",
]
