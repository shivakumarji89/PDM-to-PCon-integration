"""Contract tests for the opt-in legacy VARCOND subprocess client."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from services.legacy_varcond_bridge import (
    LegacyVarCondError,
    LegacyVarCondRequest,
    generate_with_legacy,
    verify_legacy_binding,
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
        server="DBCHIP08v",
        database="PDM_Prototipo_Test",
        confirm_non_production=True,
    )


def test_rejects_missing_helper(tmp_path: Path) -> None:
    request = _request(tmp_path)
    Path(request.helper_exe).unlink()
    with pytest.raises(LegacyVarCondError, match="bridge executable not found"):
        generate_with_legacy(request)


def test_requires_explicit_test_database(tmp_path: Path) -> None:
    request = _request(tmp_path)
    request = LegacyVarCondRequest(**{**request.__dict__, "database": "PDMLive"})
    with pytest.raises(LegacyVarCondError, match="clearly identify a test/dev"):
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


def test_rejects_non_object_bridge_response(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request(tmp_path)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="[]", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(LegacyVarCondError, match="JSON object"):
        generate_with_legacy(request)


def _replace(request: LegacyVarCondRequest, **changes) -> LegacyVarCondRequest:
    return LegacyVarCondRequest(**{**request.__dict__, **changes})


def test_requires_operator_attestation(tmp_path: Path) -> None:
    request = _replace(_request(tmp_path), confirm_non_production=False)
    with pytest.raises(LegacyVarCondError, match="confirm_non_production"):
        generate_with_legacy(request)


def test_rejects_live_marker_even_inside_a_test_name(tmp_path: Path) -> None:
    request = _replace(_request(tmp_path), database="PDMTestLive")
    with pytest.raises(LegacyVarCondError, match="live/production"):
        generate_with_legacy(request)


def test_aborted_legacy_run_is_never_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request(tmp_path)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0], 0,
            stdout=json.dumps({"ok": True, "generatedText": "", "statuses": ["GENERATE_VARCOND_ABORTED"]}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(LegacyVarCondError, match="GENERATE_VARCOND_ABORTED"):
        generate_with_legacy(request)


def test_request_carries_attestation_to_helper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request(tmp_path)
    seen = {}

    def fake_run(*args, **kwargs):
        seen.update(json.loads(kwargs["input"]))
        return subprocess.CompletedProcess(
            args[0], 0,
            stdout=json.dumps({"ok": True, "generatedText": "x", "statuses": [], "legacyAssemblyVersion": "1.2.3"}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    response = generate_with_legacy(request)
    assert seen["confirmNonProduction"] is True
    assert response.legacy_assembly_version == "1.2.3"


def test_verify_binding_uses_dry_run_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request(tmp_path)

    def fake_run(*args, **kwargs):
        payload = json.loads(kwargs["input"])
        assert payload["dryRun"] is True and "server" not in payload and "database" not in payload
        return subprocess.CompletedProcess(
            args[0], 0, stdout=json.dumps({"ok": True, "dryRun": {"assemblyVersion": "9"}}), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert verify_legacy_binding(request.helper_exe, request.legacy_assembly) == {"assemblyVersion": "9"}


@pytest.mark.skipif(
    not (os.environ.get("LEGACY_VARCOND_HELPER") and os.environ.get("LEGACY_PDM_ASSEMBLY")),
    reason="needs the built helper (LEGACY_VARCOND_HELPER) and a COPY of the legacy assembly (LEGACY_PDM_ASSEMBLY)",
)
def test_real_legacy_assembly_binding_dry_run() -> None:
    """Runtime check against the real assembly. Never connects to a database."""
    details = verify_legacy_binding(os.environ["LEGACY_VARCOND_HELPER"], os.environ["LEGACY_PDM_ASSEMBLY"])
    assert details["processIs64Bit"] is False
    assert details["initThreadParameters"][0].startswith("ArrayList")
    assert details["globalHasConnectedServer"] and details["globalHasConnectedDB"]
