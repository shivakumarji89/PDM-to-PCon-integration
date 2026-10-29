"""Pins where ``8=`` (Fabric Type) is read and where ``28=`` (mapped colour option) is introduced.

Mocked logic tests, NOT compiled-PDM evidence. Compiled-PDM evidence is in
docs/03_Workflows/cross_series_pricing_parity_report.md: legacy matches the MDB's ``8=`` rows under
``layout_studio`` / ``nevi_enhanced`` and never produced ``28=`` rows for Revive.
"""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from repositories.pdm_repository import PDMRepository
from services.pricing_service import PriceParams, PricingService
from tests.test_pricing_fabric_targets import FAMILIES, ITEM, relation, source_rows


def _fetch(program):
    """Run the production fetch against a fake PDM; the colour relationship exists for every program."""
    rows = source_rows()
    repo = PDMRepository(MagicMock())

    def execute(query, params, connection=None):
        if "AS TargetOptionId" in query:
            return [relation(vid, colour) for _, vid, colour, _, _ in FAMILIES]
        if "AS NewPrice" in query:
            return [SimpleNamespace(Item=ITEM, NewPrice=next(r.IncPrice for r in rows if r.OptionValueId == params[6]))]
        return [SimpleNamespace(Item=r.Item, OptionId=r.OptionId, OptionValueId=r.OptionValueId,
                                OrderCodeValue=r.SourceCode, RawIncrement=r.RawIncrement, PriceBand=None)
                for r in rows]

    repo._execute = execute
    return repo.fetch_global_option_increment_prices(
        [ITEM], "EUR", "25-Oct-2026", 1, object(), catalogue_id=658, program_code=program)


def _records(program):
    return PricingService.build_records(
        [], _fetch(program), {ITEM}, {}, PriceParams(currency="EUR", program_code=program))[0]


@pytest.mark.parametrize("program", ["layout_studio", "nevi_enhanced"])
def test_explicit_layout_and_nevi_keep_fabric_type_8_target(program):
    recs = _records(program)
    assert [r.variant_condition for r in recs] == [f"{ITEM} 8={f[0]}" for f in FAMILIES]
    assert all(r.pdm_lookup_code.startswith(f"{ITEM} 8=") for r in recs)


@pytest.mark.parametrize("program", ["revive", ""])
def test_revive_and_blank_program_route_target_to_colour_28_but_keep_8_source(program):
    recs = _records(program)
    assert [r.variant_condition for r in recs] == [f"{ITEM} 28={f[0]}" for f in FAMILIES]
    # The priced source option stays 8 (source lookup), only the target changes.
    assert all(r.pdm_lookup_code.startswith(f"{ITEM} 8=") for r in recs)


def test_source_prices_are_identical_whatever_the_program():
    prices = {p: [(r.OptionValueId, r.OptionId, r.IncPrice) for r in _fetch(p)]
              for p in ("layout_studio", "nevi_enhanced", "revive", "")}
    assert prices["layout_studio"] == prices["nevi_enhanced"] == prices["revive"] == prices[""]
    assert {option for _, option, _ in prices[""]} == {8}


def test_blank_program_routing_is_reported_and_explicit_program_is_silent():
    warn = PricingService._blank_program_routing_warning
    assert "because no Program is set" in warn(_records(""), "")
    assert warn(_records("revive"), "revive") == ""
    assert warn(_records("layout_studio"), "layout_studio") == ""


def test_blank_program_is_not_made_mandatory():
    assert PriceParams().require_program is False
    assert PricingService._resolve_program(PriceParams(), SimpleNamespace(generation_program="")) == ""
