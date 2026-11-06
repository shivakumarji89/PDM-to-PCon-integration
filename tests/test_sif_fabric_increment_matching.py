"""Fabric increments map to parent pricing groups by SKU position, not colour occurrence."""

from types import SimpleNamespace

import pytest

from repositories.pdm_repository import _IncPriceRow
from services.obx_validation_service import ObxLine
from services.sif_validation_service import SifValidationService
from tests.test_sif_obx_validation_parity import _eligible_validation_repo_methods

match = SifValidationService._match_inc_groups

# NOHAN120L2: two fabric parent groups (PDM order 3344, 8). Both offer the same
# colour list, so every colour is eligible under both groups.
BASE = 2436.0
GROUPS = {"7001": {"R00": (0.0, 1)}}
FABRIC_GROUPS = {"3344": {"40G#": 82.0}, "8": {"1HA#": 113.0}}
SHARED_TARGETS = {"40G01": ["3344", "8"], "1HA01": ["3344", "8"]}
ORDER = ["3344", "8"]


def test_two_different_colours_price_two_separate_groups():
    upcharge = match(GROUPS, ["R00", "40G01", "1HA01"], FABRIC_GROUPS, SHARED_TARGETS, ORDER)

    assert upcharge == 82.0 + 113.0
    assert BASE + upcharge == 2631.0


def test_same_colour_selected_twice_prices_both_groups():
    groups = {"3344": {"40G#": 82.0}, "8": {"40G#": 113.0}}
    targets = {"40G01": ["3344", "8"]}

    assert match({}, ["40G01", "40G01"], groups, targets, ORDER) == 195.0


def test_single_fabric_selection():
    assert match(GROUPS, ["R00", "40G01"], FABRIC_GROUPS, SHARED_TARGETS, ORDER) == 82.0


def test_longest_band_prefix_wins_inside_the_selected_group():
    groups = {"3344": {"40#": 10.0, "40G#": 82.0}}

    assert match({}, ["40G01"], groups, {"40G01": ["3344"]}, ["3344"]) == 82.0


def test_non_fabric_matching_is_unchanged_by_fabric_positions():
    groups = {"10": {"RED": (20.0, 1)}, "20": {"RED": (35.0, 1)}, "30": {"WFK": (6.0, 2)}}

    assert match(groups, ["RED", "RED", "WFK"]) == 20.0 + 35.0 + 12.0
    assert match(groups, ["RED", "40G01", "RED"], FABRIC_GROUPS, SHARED_TARGETS, ORDER) == 55.0 + 82.0
    assert match({"10": {"RED": (5.0, 1)}}, ["RED", "RED"]) == 5.0


def test_missing_fabric_order_falls_back_to_fabric_group_order():
    assert match(GROUPS, ["40G01", "1HA01"], FABRIC_GROUPS, SHARED_TARGETS) == 195.0
    assert match(GROUPS, ["40G01", "1HA01"], FABRIC_GROUPS, SHARED_TARGETS, []) == 195.0


def test_missing_fabric_metadata_adds_no_fabric_increment():
    # No targets: the code is an ordinary option and finds no priced group.
    assert match(GROUPS, ["R00", "40G01"], FABRIC_GROUPS, None, ORDER) == 0.0
    assert match(GROUPS, ["R00", "40G01"], FABRIC_GROUPS, {}, ORDER) == 0.0
    # Known colour but no priced bands at all.
    assert match(GROUPS, ["R00", "40G01"], {}, SHARED_TARGETS, ORDER) == 0.0
    assert match(GROUPS, ["R00", "40G01"], None, SHARED_TARGETS, ORDER) == 0.0


def test_positional_group_that_does_not_list_the_colour_uses_its_eligible_group():
    targets = {"1HA01": ["8"], "40G01": ["3344", "8"]}

    assert match({}, ["1HA01", "40G01"], FABRIC_GROUPS, targets, ORDER) == 195.0


def test_colour_with_no_eligible_unused_group_is_ignored_safely():
    targets = {"40G01": ["3344"], "1HA01": ["3344"], "ZZZ01": ["99"]}

    # Second colour has no unused eligible group; the third targets a group with no bands.
    assert match({}, ["40G01", "1HA01", "ZZZ01"], FABRIC_GROUPS, targets, ORDER) == 82.0


def test_more_fabric_colours_than_groups_ignores_the_extras():
    targets = {"40G01": ["3344", "8"]}

    assert match({}, ["40G01", "40G01", "40G01"], {"3344": {"40G#": 82.0}, "8": {"40G#": 113.0}}, targets, ORDER) == 195.0


def test_position_does_not_depend_on_unpriced_fabric_group_when_order_is_supplied():
    groups = {"8": {"1HA#": 113.0}}  # group 3344 exists but has no priced band
    targets = {"1HA01": ["3344", "8"]}

    # positional group 3344 is eligible but unpriced: the colour is consumed there
    assert match({}, ["1HA01"], groups, targets, ["3344", "8"]) == 0.0


def _row(article, group, value_id, code, is_fabric, price=None, parent=None, parent_code=None, parent_value=None):
    return _IncPriceRow(article, SimpleNamespace(
        OptionId=group, OptionValueId=value_id, OrderCodeValue2=code, Status=1,
        IncPrice=price, IsFabric=is_fabric, Quantity=1, ParentOptId=parent,
        ParentOptValCode=parent_code, ParentOptValId=parent_value,
    ))


def _nohan_option_rows(article):
    rows = [_row(article, 7001, 70010, "R00", 0, 0.0)]
    for group, band, price in ((3344, "40G#", 82.0), (8, "1HA#", 113.0)):
        rows.append(_row(article, group, group * 10, band, 1, price))
        for colour in ("40G01", "1HA01"):
            rows.append(_row(
                article, group + 1000, group * 10 + len(rows), colour, 2,
                parent=group, parent_code=band, parent_value=group * 10,
            ))
    return rows


@pytest.mark.parametrize("sku_options, expected", [
    ("R00 40G01 1HA01", 2631.0),
    ("R00 40G01", 2518.0),
])
def test_nohan120l2_validation_prices_both_fabric_groups(monkeypatch, sku_options, expected):
    article = "NOHAN120L2"
    service = SifValidationService(None)
    monkeypatch.setattr(service, "_fetch_plc", lambda *args: {})
    repo = SimpleNamespace(
        **_eligible_validation_repo_methods(),
        fetch_validation_get_price_ext_base_prices=lambda *args, **kwargs: [
            SimpleNamespace(Item=article, price=BASE)
        ],
        fetch_item_validation_options=lambda *args: _nohan_option_rows(article),
    )
    line = ObxLine(
        seq=1, base_article=article, final_article=f"{article} {sku_options}",
        currency="GBP", obx_price=expected,
    )

    results = service._validate_group(
        "GBP", [line], 1, repo, None, "2026-11-03", [0], 1, None, None, obx=True
    )

    assert results[0].pdm_price == expected
    assert results[0].status == "ok", results[0].message
