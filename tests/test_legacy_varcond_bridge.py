"""Contract tests for the opt-in legacy VARCOND subprocess client."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from services.legacy_varcond_bridge import (
    LegacyVarCondError,
    LegacyVarCondRequest,
    generate_with_legacy,
)


def _request(tmp_path: Path) -> LegacyVarCondRequest:
    helper = tmp_path / "LegacyVarCondBridge.exe"
    assembly = tmp_path / "PDMMaintenance.exe"
    helper.touch()
    assembly.touch()
    return LegacyVarCondRequest(
        helper_exe=str(helper),
        legacy_assembly=str(assembly),
        item_codes=["ABC.123"],
        category_id=12,
        filter="ABC",
    )


def test_rejects_missing_helper(tmp_path: Path) -> None:
    request = _request(tmp_path)
    Path(request.helper_exe).unlink()
    with pytest.raises(LegacyVarCondError, match="bridge executable not found"):
        generate_with_legacy(request)


def test_requires_nonempty_filter(tmp_path: Path) -> None:
    request = _request(tmp_path)
    request = LegacyVarCondRequest(**{**request.__dict__, "filter": "  "})
    with pytest.raises(LegacyVarCondError, match="non-empty filter"):
        generate_with_legacy(request)


def test_parses_successful_json_response(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request(tmp_path)

    def fake_run(*args, **kwargs):
        assert args[0][0].endswith("LegacyVarCondBridge.exe")
        assert kwargs["shell"] is False
        payload = json.loads(kwargs["input"])
        assert payload["itemCodes"] == ["ABC.123"]
        return subprocess.CompletedProcess(
            args[0], 0,
            stdout=json.dumps({"ok": True, "generatedText": "$VARCOND = 'ABC.123' IF X='Y'", "statuses": ["complete"]}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = generate_with_legacy(request)
    assert result.generated_text == "$VARCOND = 'ABC.123' IF X='Y'"
    assert result.statuses == ["complete"]


def test_surfaces_legacy_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request(tmp_path)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0], 1, stdout=json.dumps({"ok": False, "error": "database unavailable"}), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(LegacyVarCondError, match="database unavailable"):
        generate_with_legacy(request)


def test_timeout_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request(tmp_path)

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(LegacyVarCondError, match="timed out"):
        generate_with_legacy(request)
