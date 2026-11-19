"""QA Validation: two-fabric SKUs validate in catalogue scope and price per fabric group.

Rows mirror live PDM GH1SPSNLD.0816S1MD: fabric band ``7V#`` is offered by a
top-level fabric group (9632) and, nested below it, by a second fabric group
(8). Colours exist once under each group, so two fabrics need two groups.
"""
from types import SimpleNamespace

import pytest

from services.sif_validation_service import SifValidationService

verify = SifValidationService._verify_selected_options
match = SifValidationService._match_inc_groups


def _row(value, group, code, fabric=0, parent=None):
    return SimpleNamespace(
        OptionValueId=value, OptionId=group, OrderCodeValue2=code, Status=1,
        IsFabric=fabric, IncPrice=0.0, Quantity=1,
        ParentOptId=parent[0] if parent else None,
        ParentOptValId=parent[1] if parent else None,
        ParentOptValCode=parent[2] if parent else None,
    )


def _rows():
    return [
        _row(1, 100, "WFK"), _row(2, 100, "98"),
        _row(4, 101, "WFK"), _row(5, 103, "UBK"), _row(6, 102, "98"),
        _row(10, 9632, "7V#", 1), _row(11, 9632, "1HS#", 1),
        _row(12, 9633, "7V03", 2, (9632, 10, "7V#")),
        _row(13, 9633, "7V05", 2, (9632, 10, "7V#")),
        _row(20, 8, "7V#", 1, (9632, 10, "7V#")),
        _row(21, 28, "7V03", 2, (8, 20, "7V#")),
        _row(22, 28, "7V05", 2, (8, 20, "7V#")),
    ]


SCOPE = {row.OptionValueId for row in _rows()}
ONE = ["WFK", "WFK", "98", "UBK", "7V03"]
TWO = ["WFK", "WFK", "98", "UBK", "7V03", "7V05"]


@pytest.mark.parametrize("scope", [None, SCOPE])
def test_single_fabric_passes(scope):
    assert verify(_rows(), ONE, catalogue_option_value_ids=scope) is None


@pytest.mark.parametrize("scope", [None, SCOPE])
def test_two_fabric_passes(scope):
    assert verify(_rows(), TWO, catalogue_option_value_ids=scope) is None


def test_invalid_fabric_code_still_rejected():
    error = verify(_rows(), ["WFK", "WFK", "98", "UBK", "9Z05"], catalogue_option_value_ids=SCOPE)
    assert error == "invalid option string in order code at position 5: 9Z05"


def test_third_fabric_colour_still_rejected_in_scope():
    error = verify(_rows(), TWO + ["7V03"], catalogue_option_value_ids=SCOPE)
    assert "position 7" in error


def test_invalid_option_position_rejected():
    error = verify(_rows(), ["WFK", "WFK", "XXX", "7V03"], catalogue_option_value_ids=SCOPE)
    assert "position 3: XXX" in error


def test_second_fabric_needs_the_nested_group_in_catalogue():
    scope = SCOPE - {21, 22}  # catalogue lacks the second-group colours
    assert "position 6" in verify(_rows(), TWO, catalogue_option_value_ids=scope)


def test_second_fabric_rejected_when_ancestor_band_not_selected():
    # 7V colours reachable only through the 7V# band: other colours must not borrow it.
    rows = [r for r in _rows() if r.OptionValueId not in (11,)]
    assert verify(rows, ["1HS01"], catalogue_option_value_ids=SCOPE) is not None


def test_two_fabric_increments_use_both_groups():
    fabric_groups = {"9632": {"7V#": 82.0}, "8": {"7V#": 113.0}}
    targets = {"7V03": ["9632", "8"], "7V05": ["9632", "8"]}
    assert match({}, ["7V03", "7V05"], fabric_groups, targets, ["9632", "8"]) == 195.0
    assert match({}, ["7V03"], fabric_groups, targets, ["9632", "8"]) == 82.0
