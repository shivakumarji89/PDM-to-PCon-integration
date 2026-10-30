"""Logic-level regression tests for the cross-series pricing parity work.

These are MOCKED tests: they pin routing rules and harness classification. They are not compiled-PDM
evidence; that lives in docs/03_Workflows/cross_series_pricing_parity_report.md (scripts/pdm_differential/
cross_series.py runs).
"""
from __future__ import annotations

import subprocess
from decimal import Decimal
from types import SimpleNamespace

import pytest

from models.price_record import PriceRecord
from repositories.pdm_repository import GlobalOptionPriceRow
from scripts.pdm_differential import cross_series, differential
from services.pricing_service import PriceParams, PricingService

ITEM = "GESNNU.105508F"


def _row(target):
    return GlobalOptionPriceRow(
        ITEM, 148810, 8, "1FD#", f"{ITEM}_1FD#", f"{ITEM} 8=1FD#", Decimal("58"), None, Decimal("58"),
        TargetOptionId=target,
    )


def _records(target, program):
    return PricingService.build_records([], [_row(target)], {ITEM}, {}, PriceParams(program_code=program))[0]


# ---- source identity stays separate from target identity ---------------------------------------------
def test_unrouted_series_keep_the_priced_option_id_for_condition_and_lookup():
    for program in ("layout_studio", "nevi_enhanced"):
        (record,) = _records(None, program)
        assert record.variant_condition == f"{ITEM} 8=1FD"
        assert record.pdm_lookup_code == f"{ITEM} 8=1FD#"


def test_routed_rows_carry_target_in_condition_and_source_in_lookup():
    (record,) = _records(28, "revive")
    assert record.variant_condition == f"{ITEM} 28=1FD"
    assert record.pdm_lookup_code == f"{ITEM} 8=1FD#"  # never rewritten to the target


# ---- blank-program routing is explicit, never silent -------------------------------------------------
def test_blank_program_routing_produces_a_warning_naming_the_fix():
    warning = PricingService._blank_program_routing_warning(_records(28, ""), "")
    assert warning.startswith("1 global price record(s) were routed")
    assert "Set the series program" in warning


@pytest.mark.parametrize("records,program", [
    (_records(28, "revive"), "revive"),          # explicit program: documented Revive routing, no warning
    (_records(None, ""), ""),                    # blank but nothing routed
    ([PriceRecord(is_global=False, article_code="A", variant_condition=" 8=1FD", level="X", value=1.0,
                  currency="GBP")], ""),         # article rows are never routed
])
def test_no_warning_when_nothing_was_routed_by_a_blank_program(records, program):
    assert PricingService._blank_program_routing_warning(records, program) == ""


def test_compute_surfaces_the_warning_to_the_pricing_page(monkeypatch):
    service = PricingService(SimpleNamespace())
    snapshot = SimpleNamespace(price_records=[], price_lists=[], generation_program="")
    monkeypatch.setattr(service, "_price_plan", lambda s: ([ITEM], {ITEM}))
    monkeypatch.setattr(service, "_prefix_by_item", lambda s: {})
    monkeypatch.setattr(PricingService, "_global_catalogue", staticmethod(lambda s, p: 660))
    monkeypatch.setattr(PricingService, "_attach_product_codes", staticmethod(lambda *a: None))

    class Repo:
        def __init__(self, _ctx): pass
        def get_connection(self): return SimpleNamespace(close=lambda: None)
        def fetch_item_base_prices(self, *a, **k): return []
        def fetch_global_option_increment_prices(self, *a, **k): return [_row(28)]

    monkeypatch.setattr("services.pricing_service.PDMRepository", Repo)
    result = service.compute(PriceParams(mydate="16-Oct-2026"), snapshot)
    assert any("because no Program is set" in w for w in result.warnings)
    snapshot.generation_program = "layout_studio"
    monkeypatch.setattr(Repo, "fetch_global_option_increment_prices", lambda self, *a, **k: [_row(None)])
    result = service.compute(PriceParams(mydate="16-Oct-2026", program_code="layout_studio"), snapshot)
    assert not any("Program" in w for w in result.warnings)
    assert all(r.variant_condition == f"{ITEM} 8=1FD" for r in result.records)


# ---- harness classification: a failed or blocked run is never a PASS ----------------------------------
CLEAN = {"only_in_pdm_result": [], "only_in_pricing_result": [], "lists_equal": True, "texts_equal": True}


def test_variant_status_classification():
    assert cross_series._variant_status({"ok": True}, CLEAN, []) == "PASS"
    assert cross_series._variant_status({"ok": False}, CLEAN, []) == "INCOMPLETE"  # blocked export: vacuous diff
    assert cross_series._variant_status({"ok": True}, {**CLEAN, "only_in_pricing_result": ["x"]}, []) == "FAIL"
    assert cross_series._variant_status({"ok": True}, {**CLEAN, "texts_equal": False}, []) == "FAIL"
    assert cross_series._variant_status({"ok": True}, CLEAN, ["ITEM"]) == "FAIL"
    # legacy never priced these items, so an identical end state proves nothing
    assert cross_series._variant_status({"ok": True}, CLEAN, [], legacy_unresolved=312) == "INCOMPLETE"


def test_run_pdm_nonzero_exit_is_not_reported_as_executed(monkeypatch, tmp_path):
    work = tmp_path
    (work / "t").mkdir()

    class Watcher:
        def kill(self): pass

    monkeypatch.setattr(differential.subprocess, "Popen", lambda *a, **k: Watcher())

    def fake_run(cmd, **kwargs):
        out = work / "t" / "out.json"
        out.write_text('{"finished": true, "status": []}', encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 1, "", "boom")

    monkeypatch.setattr(differential.subprocess, "run", fake_run)
    result = differential.run_pdm(work, tmp_path, "t", "article", ["X"], "GBP", 1, "L")
    assert result["returncode"] == 1 and result["executed"] is False
    assert result["stderr"] == "boom"
