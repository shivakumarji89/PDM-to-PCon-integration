from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from services.legacy_pricing_engine import (
    LegacyPricingEngineError,
    LegacyPricingEngineRequest,
    run_legacy_pricing_engine,
)


def request(tmp_path: Path, **overrides):
    pdm = tmp_path / "pdm"
    pdm.mkdir(exist_ok=True)
    (pdm / "PDMMaintenance.exe").write_bytes(b"test placeholder")
    root = tmp_path / "sandbox"
    mdb = root / "WS" / "Layout_Studio" / "pcr_data_com_ocd.mdb"
    mdb.parent.mkdir(parents=True)
    mdb.write_bytes(b"isolated MDB placeholder")
    harness = tmp_path / "run_pdm_price_update.ps1"
    harness.write_text("# test harness", encoding="utf-8")
    values = dict(
        pdm_dir=str(pdm), pcon_root=str(root), workspace="Layout_Studio",
        mode="global", items=["TEST.ARTICLE"], program_code="revive",
        site_id=1, catalogue_id=658, mydate="27-Oct-2026",
        prevdate="26-Oct-2026", currency="EUR", price_list_id=26,
        price_list_label="EURO_2026_2", package_id=240,
        isolated_mdb_confirmed=True,
    )
    values.update(overrides)
    return LegacyPricingEngineRequest(**values), harness


def test_refuses_to_run_without_isolated_mdb_confirmation(tmp_path):
    req, harness = request(tmp_path, isolated_mdb_confirmed=False)
    with pytest.raises(LegacyPricingEngineError, match="disposable MDB copy"):
        run_legacy_pricing_engine(req, harness=harness)


@pytest.mark.parametrize("mode", ["", "unknown", "all"])
def test_rejects_unsupported_mode_before_launch(tmp_path, mode):
    req, harness = request(tmp_path, mode=mode)
    with pytest.raises(LegacyPricingEngineError, match="mode must be"):
        run_legacy_pricing_engine(req, harness=harness)


def test_requires_expected_isolated_mdb_path(tmp_path):
    req, harness = request(tmp_path, pcon_root=str(tmp_path / "missing"))
    with pytest.raises(LegacyPricingEngineError, match="isolated MDB copy"):
        run_legacy_pricing_engine(req, harness=harness)


def test_invokes_legacy_harness_and_parses_result(tmp_path, monkeypatch):
    req, harness = request(tmp_path)
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        out_path = Path(command[command.index("-OutPath") + 1])
        out_path.write_text(json.dumps({
            "finished": True, "pdmVersion": "1.0.9686.24988",
            "mode": "global", "variableincs": True,
            "status": ["Pricing completed"], "noPDMprice": [],
            "notfound": ["NOT_FOUND_ITEM"],
        }), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("services.legacy_pricing_engine.subprocess.run", fake_run)
    result = run_legacy_pricing_engine(req, harness=harness)

    assert result.finished is True
    assert result.pdm_version == "1.0.9686.24988"
    assert result.variableincs is True
    assert result.notfound == ["NOT_FOUND_ITEM"]
    assert seen["kwargs"]["shell"] is False
    assert seen["kwargs"]["timeout"] == req.timeout_seconds
    assert "-File" in seen["command"]
    job_path = Path(seen["command"][seen["command"].index("-JobPath") + 1])
    payload = json.loads(job_path.read_text(encoding="utf-8"))
    assert payload["programCode"] == "revive"
    assert payload["catalogueId"] == 658
    assert payload["packageId"] == 240
    assert payload["items"] == ["TEST.ARTICLE"]


def test_worker_failure_is_not_reported_as_success(tmp_path, monkeypatch):
    req, harness = request(tmp_path)

    def fake_run(command, **kwargs):
        Path(command[command.index("-OutPath") + 1]).write_text(json.dumps({
            "finished": False, "status": ["EXCEPTION: legacy error"],
        }), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("services.legacy_pricing_engine.subprocess.run", fake_run)
    with pytest.raises(LegacyPricingEngineError, match="did not finish"):
        run_legacy_pricing_engine(req, harness=harness)
