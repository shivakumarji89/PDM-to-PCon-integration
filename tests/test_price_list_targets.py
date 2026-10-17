"""Target price-list naming, matching and date applicability (pure, no MDB)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.price_list_targets import (
    computation_date, default_names, label_key, normalize_mdb_date, resolve_targets, validate_name,
)
from models.price_record import PriceRecord


def ms(day):
    """The bridge's /Date(ms)/ for local midnight of ``YYYYMMDD`` (timezone independent)."""
    from datetime import datetime
    return f"/Date({int(datetime.strptime(day, '%Y%m%d').timestamp() * 1000)})/"


def L(pid, label, ccy, start=None, end="/Date(253402194600000)/"):
    """An MDB list row as the bridge returns it (2026-09-07 .. open end by default)."""
    start = start or ms("20260907")
    return {"com_PriceListID": pid, "com_PriceListLabel": label, "sys_ISOCurrencyCode": ccy,
            "com_PriceValidFrom": start, "com_PriceValidTo": end}


def iso(day):  # a list row with plain YYYYMMDD bounds
    return day


def test_name_validation():
    assert validate_name("EURO_2027_2") == ""
    assert validate_name("EURO 2027") == ""
    for bad in ("", "  ", "x" * 51, "EURO/2027", "_EURO", "default", "Default"):
        assert validate_name(bad), bad


def test_label_key_ignores_case_space_underscore_hyphen():
    assert label_key("euro 2026_2") == label_key("EURO_2026_2") == label_key("Euro-2026-2")


@pytest.mark.parametrize("value, expected", [
    ("/Date(253402194600000)/", ("99991230", "99991231")), ("2026-10-16", ("20261016",)),
    ("20261016", ("20261016",)), ("#2026-10-16 00:00:00#", ("20261016",)), ("", ("",)), (None, ("",)),
])
def test_date_normalization(value, expected):
    assert normalize_mdb_date(value, "") in expected


def test_computation_date_is_the_records_date_and_never_today():
    recs = [PriceRecord(valid_from="2026-10-16"), PriceRecord(valid_from="2026-10-16"), PriceRecord(valid_from="2026-01-01")]
    assert computation_date(recs) == "20261016"
    assert computation_date([PriceRecord(valid_from="")]) == ""


def test_default_names_use_year_and_the_sole_mid_year_suffix():
    lists = [L(19, "EURO_2026", "EUR", "20260101", "20260906"), L(20, "GBP_2026", "GBP", "20260101", "20260906")]
    # base-year list exists but ends before the computation date -> _2
    assert default_names(["EUR", "GBP"], "20261016", lists) == {"EUR": "EURO_2026_2", "GBP": "GBP_2026_2"}
    # base list covers the date -> reuse the base name
    assert default_names(["EUR"], "20260601", lists) == {"EUR": "EURO_2026"}
    # nothing exists for the year -> plain base name
    assert default_names(["EUR", "GBP"], "20270105", lists) == {"EUR": "EURO_2027", "GBP": "GBP_2027"}
    # a list the snapshot already names wins (spaces become the MDB's underscores)
    named = [SimpleNamespace(label="EURO 2027_2", id="x", currency="EUR")]
    assert default_names(["EUR"], "20270705", lists, named) == {"EUR": "EURO_2027_2"}


def test_default_names_skip_occupied_suffixes_and_other_currency_names():
    lists = [
        L(19, "EURO_2026", "EUR", "20260101", "20260906"),
        L(20, "EURO_2026_2", "EUR", "20260101", "20260906"),
        L(21, "GBP_2027", "EUR"),
    ]

    assert default_names(["EUR"], "20261016", lists) == {"EUR": "EURO_2026_3"}
    assert default_names(["EUR"], "20270105", lists) == {"EUR": "EURO_2027"}
    assert default_names(["GBP"], "20270105", lists) == {"GBP": "GBP_2027_2"}


def test_reuse_existing_list_covering_the_date():
    plan = resolve_targets({"EUR": "EURO_2026_2"}, [L(21, "EURO_2026_2", "EUR")], {"21"}, "20261016")["EUR"]
    assert (plan.action, plan.list_id, plan.ok, plan.linked) == ("reuse", 21, True, True)
    assert plan.date_from == "20260907"


def test_space_vs_underscore_matches_the_existing_list_instead_of_creating_another():
    plan = resolve_targets({"EUR": "EURO 2026_2"}, [L(21, "EURO_2026_2", "EUR")], {"21"}, "20261016")["EUR"]
    assert plan.action == "reuse" and plan.list_id == 21


def test_exact_label_wins_over_lookalike_and_lookalike_is_reported():
    lists = [L(21, "EURO_2026_2", "EUR"), L(24, "EURO 2026_2", "EUR")]
    plan = resolve_targets({"EUR": "EURO_2026_2"}, lists, {"21"}, "20261016")["EUR"]
    assert plan.list_id == 21 and plan.ignored_ids == [24] and plan.ok
    assert any("ignored" in w for w in plan.warnings)
    # the operator can still choose the other spelling explicitly - and is warned it is unlinked
    other = resolve_targets({"EUR": "EURO 2026_2"}, lists, {"21"}, "20261016")["EUR"]
    assert other.list_id == 24 and any("not linked" in w for w in other.warnings)


def test_ambiguity_without_exact_or_unique_linked_match_stops():
    lists = [L(30, "EURO 2026_2", "EUR"), L(31, "Euro_2026_2", "EUR")]
    plan = resolve_targets({"EUR": "EURO-2026-2"}, lists, set(), "20261016")["EUR"]
    assert plan.action == "blocked" and not plan.ok and "matches 2" in plan.errors[0]
    both_linked = resolve_targets({"EUR": "EURO-2026-2"}, lists, {"30", "31"}, "20261016")["EUR"]
    assert not both_linked.ok


def test_unique_linked_list_resolves_a_non_exact_ambiguity():
    lists = [L(30, "EURO 2026_2", "EUR"), L(31, "Euro_2026_2", "EUR")]
    plan = resolve_targets({"EUR": "EURO-2026-2"}, lists, {"31"}, "20261016")["EUR"]
    assert plan.ok and plan.list_id == 31


def test_missing_list_is_created_with_the_chosen_name_currency_and_dates():
    plan = resolve_targets({"GBP": "GBP_2027"}, [L(22, "GBP_2026_2", "GBP")], {"22"}, "20270105")["GBP"]
    assert (plan.action, plan.name, plan.date_from, plan.date_to, plan.list_id) == (
        "create", "GBP_2027", "20270105", "99991231", None)
    assert any("not linked" in w for w in plan.warnings)


def test_new_list_overlapping_an_existing_one_is_warned_not_blocked():
    plan = resolve_targets({"EUR": "EURO_2026_3"}, [L(21, "EURO_2026_2", "EUR")], {"21"}, "20261016")["EUR"]
    assert plan.ok and any("overlaps" in w for w in plan.warnings)


def test_label_owned_by_another_currency_is_blocked_not_duplicated():
    plan = resolve_targets({"EUR": "GBP_2026_2"}, [L(22, "GBP_2026_2", "GBP")], {"22"}, "20261016")["EUR"]
    assert not plan.ok and "another currency" in plan.errors[0]


def test_eur_and_gbp_may_not_share_a_name():
    plans = resolve_targets({"EUR": "PRICES_2027", "GBP": "prices 2027"}, [], set(), "20270105")
    assert plans["EUR"].ok and not plans["GBP"].ok


@pytest.mark.parametrize("comp, ok", [
    ("20260906", False),   # day before the list starts
    ("20260907", True),    # first valid day
    ("20261016", True),
    ("20270101", True),    # open-ended list covers any later date
])
def test_validity_boundaries_with_an_open_ended_list(comp, ok):
    plan = resolve_targets({"EUR": "EURO_2026_2"}, [L(21, "EURO_2026_2", "EUR")], {"21"}, comp)["EUR"]
    assert plan.ok is ok
    if not ok:
        assert "does not cover" in plan.errors[0]


@pytest.mark.parametrize("comp, ok", [("20260405", False), ("20260406", True), ("20260906", True), ("20260907", False)])
def test_validity_boundaries_with_a_closed_list(comp, ok):
    closed = L(19, "EURO_2026", "EUR", ms("20260406"), ms("20260906"))
    plan = resolve_targets({"EUR": "EURO_2026"}, [closed], {"19"}, comp)["EUR"]
    assert plan.ok is ok


def test_competing_lists_are_resolved_by_the_chosen_name_not_by_date_alone():
    lists = [L(19, "EURO_2026", "EUR", "20260101", "20260906"), L(21, "EURO_2026_2", "EUR", "20260907", "99991231")]
    assert resolve_targets({"EUR": "EURO_2026_2"}, lists, set(), "20261016")["EUR"].list_id == 21
    stale = resolve_targets({"EUR": "EURO_2026"}, lists, set(), "20261016")["EUR"]
    assert not stale.ok          # an older list is never silently used for a later date


def test_missing_computation_date_blocks():
    plan = resolve_targets({"EUR": "EURO_2026_2"}, [L(21, "EURO_2026_2", "EUR")], set(), "")["EUR"]
    assert not plan.ok and "computation date" in plan.errors[0]
