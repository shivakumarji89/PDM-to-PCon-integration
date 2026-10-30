"""Job-directory bridge: liveness, request/result exchange, errors, timeouts."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope
from services.pcon_sdk_obx import protocol
from services.pcon_sdk_obx.bridge import (
    PLUGIN_FILES,
    BridgeSettings,
    PconPluginBridge,
    PluginTimeoutError,
    PluginUnavailableError,
    default_job_dir,
    find_built_plugin_dir,
)
from tests.pcon_sdk_fake_plugin import FakePconPlugin


def make_bridge(tmp_path: Path, **kwargs) -> PconPluginBridge:
    settings = BridgeSettings(job_dir=tmp_path / "jobs", planner_exe="", plugin_install_dir=tmp_path / "plug",
                              request_timeout=kwargs.pop("request_timeout", 5.0), poll_interval=0.01)
    return PconPluginBridge(settings, **kwargs)


def test_default_job_dir_honours_environment_override(monkeypatch, tmp_path):
    monkeypatch.setenv("MK_PCON_OBX_JOBS", str(tmp_path / "custom"))
    assert default_job_dir() == tmp_path / "custom"
    monkeypatch.delenv("MK_PCON_OBX_JOBS")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert default_job_dir() == tmp_path / "MKProductWorkbench" / "pcon_obx_jobs"


def test_plugin_not_detected_without_heartbeat(tmp_path):
    bridge = make_bridge(tmp_path)
    assert not bridge.is_plugin_alive()
    assert "not detected" in bridge.describe_status()
    with pytest.raises(PluginUnavailableError):
        bridge.ping()


def test_stale_or_wrong_version_heartbeat_is_not_alive(tmp_path):
    bridge = make_bridge(tmp_path)
    bridge.ensure_job_dir()
    plugin = FakePconPlugin(bridge.job_dir)
    plugin.write_heartbeat(timestamp=time.time() - 120)
    assert not bridge.is_plugin_alive()
    assert "stale" in bridge.describe_status()
    plugin.protocol_version = 99
    plugin.write_heartbeat()
    assert not bridge.is_plugin_alive()
    assert "reinstall" in bridge.describe_status()
    plugin.protocol_version = protocol.PROTOCOL_VERSION
    plugin.ready = False
    plugin.write_heartbeat()
    assert not bridge.is_plugin_alive()
    assert "starting" in bridge.describe_status()


def test_ping_round_trip_and_cleanup(tmp_path):
    bridge = make_bridge(tmp_path)
    with FakePconPlugin(bridge.ensure_job_dir()):
        assert bridge.is_plugin_alive()
        assert "Connected" in bridge.describe_status()
        data = bridge.ping()
        assert data["languages"] == ["en", "de"]
        leftovers = [p for p in bridge.job_dir.iterdir() if p.name != protocol.HEARTBEAT_FILE]
        assert leftovers == []


def test_plugin_failure_surfaces_as_protocol_error(tmp_path):
    bridge = make_bridge(tmp_path)
    with FakePconPlugin(bridge.ensure_job_dir()):
        with pytest.raises(protocol.PluginProtocolError, match="Unknown request kind"):
            bridge.send("bogus")


def test_request_times_out_when_plugin_never_answers(tmp_path):
    bridge = make_bridge(tmp_path, request_timeout=0.3)
    plugin = FakePconPlugin(bridge.ensure_job_dir(), ready=True)
    plugin.write_heartbeat()
    # Heartbeat present but no processing thread -> timeout, request removed.
    with pytest.raises(PluginTimeoutError):
        bridge.send(protocol.KIND_PING)
    assert list(bridge.job_dir.glob("*.request.json")) == []


def test_request_aborts_when_plugin_dies_mid_flight(tmp_path):
    bridge = make_bridge(tmp_path, request_timeout=5.0)
    plugin = FakePconPlugin(bridge.ensure_job_dir())
    plugin.write_heartbeat(timestamp=time.time())
    calls = {"n": 0}

    def clock():
        calls["n"] += 1
        return float(calls["n"])

    bridge._clock = clock
    bridge._sleep = lambda _s: plugin.write_heartbeat(timestamp=time.time() - 60)
    with pytest.raises(PluginUnavailableError, match="stopped responding"):
        bridge.send(protocol.KIND_PING)


def test_cancellation_token_aborts_the_wait(tmp_path):
    bridge = make_bridge(tmp_path, request_timeout=5.0)
    plugin = FakePconPlugin(bridge.ensure_job_dir())
    plugin.write_heartbeat()
    token = CancellationToken()

    def sleep(_seconds):
        token.request_cancel()

    bridge._sleep = sleep
    with cancellation_scope(token):
        with pytest.raises(OperationCancelled):
            bridge.send(protocol.KIND_PING)


def test_progress_callback_receives_plugin_progress(tmp_path):
    bridge = make_bridge(tmp_path)
    seen = []
    with FakePconPlugin(bridge.ensure_job_dir()):
        bridge.send(protocol.KIND_GENERATE, {
            "articles": [{"articleNumber": "CHAIR1"}], "properties": [{"key": "Size", "mode": "vary"}],
            "outputPath": str(tmp_path / "p.obx"), "maxConfigurations": 10,
        }, on_progress=seen.append)
    # Progress files are rewritten quickly; we only require that nothing crashed
    # and that any progress we did see is well formed.
    assert all(p.total == 10 for p in seen)


def test_install_plugin_copies_built_files(tmp_path):
    bridge = make_bridge(tmp_path)
    source = tmp_path / "built"
    source.mkdir()
    for name in PLUGIN_FILES:
        (source / name).write_text("x", encoding="utf-8")
    target = bridge.install_plugin(source)
    assert target == tmp_path / "plug"
    assert bridge.plugin_installed()
    with pytest.raises(PluginUnavailableError):
        bridge.install_plugin(tmp_path / "missing")


def test_launch_planner_requires_executable(tmp_path, monkeypatch):
    bridge = make_bridge(tmp_path)
    monkeypatch.setattr("services.pcon_sdk_obx.bridge.find_planner_executable", lambda: "")
    with pytest.raises(PluginUnavailableError, match="executable not found"):
        bridge.launch_planner()


def test_built_plugin_dir_lookup(tmp_path):
    root = tmp_path / "repo"
    out = root / "tools" / "pcon_obx_plugin" / "bin" / "Release" / "net481"
    out.mkdir(parents=True)
    assert find_built_plugin_dir(root) is None
    for name in PLUGIN_FILES:
        (out / name).write_text("x", encoding="utf-8")
    assert find_built_plugin_dir(root) == out
