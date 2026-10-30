"""Maintenance pricing must carry an explicit program; a blank one is never treated as Revive."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from repositories.pdm_repository import GlobalOptionPriceRow, PDMRepository
from services.price_mdb_export_service import PriceMdbExportService
from services.pricing_program import PricingProgramError, validate_pricing_program
from services.pricing_service import PriceParams, PricingService

ITEM = "GESNNU.105508F"


def _row(target):
    return GlobalOptionPriceRow(
        ITEM, 148810, 8, "1FD#", f"{ITEM}_1FD#", f"{ITEM} 8=1FD#", Decimal("58"), None, Decimal("58"),
        TargetOptionId=target,
    )


@pytest.mark.parametrize("value,expected", [
    ("layout_studio", "layout_studio"), ("Layout Screens", "layout_studio"),
    ("nevi_enhanced", "nevi_enhanced"), ("Nevi Screens", "nevi_enhanced"),
    ("revive", "revive"), (" Revive ", "revive"),
])
def test_supported_programs_resolve(value, expected):
    assert validate_pricing_program(value) == expected


@pytest.mark.parametrize("value", ["", "   ", None])
def test_blank_program_is_rejected_not_defaulted_to_revive(value):
    with pytest.raises(PricingProgramError, match="not treated as Revive"):
        validate_pricing_program(value)


def test_unsupported_program_is_rejected():
    with pytest.raises(PricingProgramError, match="Unsupported Program 'aeron'"):
        validate_pricing_program("aeron")


def _service(monkeypatch, captured, target_for):
    service = PricingService(SimpleNamespace())
    monkeypatch.setattr(service, "_price_plan", lambda s: ([ITEM], {ITEM}))
    monkeypatch.setattr(service, "_prefix_by_item", lambda s: {})
    monkeypatch.setattr(PricingService, "_global_catalogue", staticmethod(lambda s, p: 660))
    monkeypatch.setattr(PricingService, "_attach_product_codes", staticmethod(lambda *a: None))

    class Repo:
        def __init__(self, _ctx): pass
        def get_connection(self): return SimpleNamespace(close=lambda: None)
        def fetch_item_base_prices(self, *a, **k): return []
        def fetch_global_option_increment_prices(self, *a, program_code="", **k):
            captured.append(program_code)
            return [_row(target_for(program_code))]

    monkeypatch.setattr("services.pricing_service.PDMRepository", Repo)
    return service


@pytest.mark.parametrize("program,target,condition", [
    ("layout_studio", None, f"{ITEM} 8=1FD"),
    ("nevi_enhanced", None, f"{ITEM} 8=1FD"),
    ("revive", 28, f"{ITEM} 28=1FD"),
])
def test_selected_program_reaches_repository_and_routing(monkeypatch, program, target, condition):
    captured: list[str] = []
    service = _service(monkeypatch, captured, lambda p: target)
    snapshot = SimpleNamespace(price_records=[], price_lists=[], articles=[], generation_program=program)
    params = PriceParams(mydate="16-Oct-2026", program_code=program, require_program=True)
    result = service.compute(params, snapshot)
    assert set(captured) == {program}
    assert {r.variant_condition for r in result.records} == {condition}
    streamed = service.compute_streaming(params, snapshot, on_batch=lambda *_: None)
    assert {r.variant_condition for r in streamed.records} == {condition}


@pytest.mark.parametrize("program", ["", "aeron"])
def test_maintenance_compute_blocks_before_any_pdm_query(monkeypatch, program):
    captured: list[str] = []
    service = _service(monkeypatch, captured, lambda p: 28)
    snapshot = SimpleNamespace(price_records=[], price_lists=[], articles=[], generation_program=program)
    params = PriceParams(mydate="16-Oct-2026", require_program=True)
    with pytest.raises(PricingProgramError):
        service.compute(params, snapshot)
    with pytest.raises(PricingProgramError):
        service.compute_streaming(params, snapshot, on_batch=lambda *_: None)
    assert captured == []


def test_development_behaviour_unchanged_when_program_not_required(monkeypatch):
    captured: list[str] = []
    service = _service(monkeypatch, captured, lambda p: 28)
    snapshot = SimpleNamespace(price_records=[], price_lists=[], generation_program="")
    result = service.compute(PriceParams(mydate="16-Oct-2026"), snapshot)
    assert set(captured) == {""}
    assert result.records


def test_repository_still_routes_blank_like_revive_only_when_not_validated():
    # Documents why Maintenance must validate upstream: the repository keeps legacy blank==revive.
    assert PDMRepository._global_source_prefix(ITEM, "layout_studio") == f"{ITEM}_"


@pytest.mark.parametrize("program", ["", "bogus"])
def test_export_is_blocked_for_blank_or_unsupported_program(tmp_path, program):
    mdb = tmp_path / "x.mdb"
    mdb.write_bytes(b"")
    snapshot = SimpleNamespace(price_records=[object()], generation_program=program)
    result = PriceMdbExportService(SimpleNamespace()).export(snapshot, mdb, require_program=True)
    assert result["ok"] is False
    assert "Program" in result["error"]


# ---- blank Program resolved from the linked repository (Maintenance) --------------------------------------
from services.pricing_program import program_from_linked_repository  # noqa: E402


def _state(snapshot, code):
    return SimpleNamespace(pdm_snapshot=snapshot,
                           mdb_import_snapshot=SimpleNamespace(product=SimpleNamespace(code=code)))


@pytest.mark.parametrize("code,expected", [
    ("layout_studio", "layout_studio"), ("nevi_enhanced", "nevi_enhanced"), ("revive", "revive"),
    ("NEVI", ""), ("aeron", ""), ("", ""),            # unrecognised / unknown series: nothing guessed
])
def test_linked_repository_program_only_when_it_is_a_routing_program(code, expected):
    snap = SimpleNamespace()
    assert program_from_linked_repository(_state(snap, code), snap) == expected


def test_linked_repository_ignored_for_another_snapshot_or_no_link():
    snap = SimpleNamespace()
    assert program_from_linked_repository(_state(SimpleNamespace(), "revive"), snap) == ""
    assert program_from_linked_repository(None, snap) == ""
