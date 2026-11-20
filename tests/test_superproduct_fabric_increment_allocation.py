"""SuperProduct component fabric increments respect FeaturePositionString.

Fixture mirrors the live PDM component increment rows (GBP, site 1,
2026-11-20) for ``GH1SPGANU.0816S1MD 8Q 8Q 8Q UBK 1HS01 T2HS01``: each desk
component carries option 9487 (``1HS#`` / ``T2RE#``, 73) and option 8
(``T2HS#``, 145) but its feature string lists only option 8.
"""

from types import SimpleNamespace

from services.sif_validation_service import SifValidationService

match = SifValidationService._match_component_increments
ITEM = "GH1SPGANU.0816S1MD"
CODES = "8Q 8Q 8Q UBK 1HS01 T2HS01".split()
DESK_FPS = "||9602||9632|9633|8|28|"


def _row(component, seq, sub_id, code, option_id, price, fps, display=5, ovid=1):
    return SimpleNamespace(
        ParentItem=ITEM, Quantity=1, SubItemId=sub_id, ComponentSequence=seq,
        CompItem=component, DisplayOrder=display, TertiaryOption=0,
        OptionValueId=ovid, FeaturePositionString=fps, DisplayOrdinal=1,
        OrderCodeValue2=code, OptionId=option_id, IncPrice=price,
    )


def _desk(component, seq, sub_id, fps=DESK_FPS):
    return [
        _row(component, seq, sub_id, "1HS#", 9487, 73.0, fps, 5, 306701),
        _row(component, seq, sub_id, "T2RE#", 9487, 73.0, fps, 5, 307085),
        _row(component, seq, sub_id, "T2HS#", 8, 145.0, fps, 1000, 306957),
    ]


def _live_rows(fps=DESK_FPS):
    return _desk("GHGSLDT.14000800", "2", 4384110, fps) + _desk(
        "GHGSRDT.14000800", "3", 4384112, fps
    )


def test_option_absent_from_feature_string_is_not_priced():
    # 1HS01 alone can only match option 9487, which neither desk lists.
    assert match(_live_rows(), CODES[:5], ITEM) == 0.0


def test_t2hs01_prices_option_8_on_both_desk_components():
    assert match(_live_rows(), CODES, ITEM) == 290.0
    assert 4109.0 + match(_live_rows(), CODES, ITEM) == 4399.0


def test_each_component_occurrence_is_priced_separately():
    one_desk = _desk("GHGSLDT.14000800", "2", 4384110)

    assert match(one_desk, CODES, ITEM) == 145.0
    assert match(_live_rows(), CODES, ITEM) == 2 * 145.0


def test_wildcard_band_cannot_bypass_component_eligibility():
    rows = _live_rows()

    assert match(rows, ["T2RE01"], ITEM) == 0.0
    assert match(rows, ["1HS01", "T2RE01"], ITEM) == 0.0


def test_two_fabric_selections_price_their_own_eligible_groups():
    fps = "|9487|8|"
    rows = _live_rows(fps)

    # With 9487 listed, 1HS01 -> option 9487 (73) and T2HS01 -> option 8 (145).
    assert match(rows, CODES, ITEM) == 2 * (73.0 + 145.0)


def test_other_option_groups_stay_available_after_an_increment():
    comp = "PART"
    rows = [
        _row(comp, "1", 1, "RED", 10, 5.0, "10|20|", 1, 1),
        _row(comp, "1", 1, "BLUE", 10, 6.0, "10|20|", 1, 2),
        _row(comp, "1", 1, "GREEN", 20, 7.0, "10|20|", 2, 3),
    ]

    assert match(rows, ["RED", "GREEN"], "SUPER") == 12.0


def test_missing_feature_string_keeps_legacy_wildcard_matching():
    rows = _live_rows(fps=None)

    # No metadata: nothing excludes option 9487, so the first matching band wins.
    assert match(rows, CODES[:5], ITEM) == 146.0
    assert match(_live_rows(fps=""), CODES[:5], ITEM) == 146.0
