"""The committed PDM differential report is the evidence for the parity claims: keep it honest."""
from __future__ import annotations

import json
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1] / "docs" / "03_Workflows" / "pdm_differential_report.json"


def _report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_every_recorded_scenario_executed_in_real_pdm_and_is_explained():
    report = _report()
    assert report["unexplained"] == []
    for sc in report["scenarios"]:
        assert all(o["executed"] for o in sc["pdm_output"]), sc["scenario"]
        assert sc["verification_status"] in {"MATCH", "DIFFERENCE_EXPLAINED"}, sc["scenario"]
        assert sc["pdm_output"][0]["pdmVersion"], sc["scenario"]


def test_report_records_the_pdm_build_and_isolation():
    app = _report()["pdm_application"]
    assert app["assembly_version"]
    assert "UpdatePriceThread.execThread" in app["entry_point"]


def test_core_parity_scenarios_match_exactly():
    by_name = {s["scenario"]: s for s in _report()["scenarios"]}
    for name in ("S1_article_gbp", "S2_article_eur", "S3_article_first_price_for_existing_article",
                 "S6_placeholders_then_global_reuse_text", "S7_placeholders_then_global_create_text",
                 "S9_global_surcharge_text_creation"):
        assert by_name[name]["verification_status"] == "MATCH", name


def test_every_difference_has_a_reason_and_classification():
    for sc in _report()["scenarios"]:
        if sc["verification_status"] == "DIFFERENCE_EXPLAINED":
            assert sc["classification"] in {"intentional", "intentional_protective", "negative_control"}, sc["scenario"]
            assert len(sc["resolution"]) > 40, sc["scenario"]


def test_idempotent_second_runs_were_executed_where_recorded():
    runs = [s["second_run_idempotency"] for s in _report()["scenarios"] if "second_run_idempotency" in s]
    assert runs
    for run in runs:
        assert run["pricing_changed_rows"] is False and run["pricing_texts_changed"] is False
        assert run["pdm_changed_rows"] is False
