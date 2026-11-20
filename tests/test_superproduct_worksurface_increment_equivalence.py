"""SuperProduct component options that twin a listed parent slot stay eligible.

Regression for the QA price loss on GH1SPGNND/GH1SPSNNU articles (GBP, site 1,
2026-11-19). Each worktop component (``GHTGNN.*``/``GHTSNN.*``) carries option
9484 'Worksurface finish' (HFK/WFK/BFK) while its FeaturePositionString lists
the parent slots ``9597|9598|`` (9597 is also 'Worksurface finish', non-fabric).
Treating 9484 as absent from the feature string dropped the worksurface
increment (-79/-87/-79/-58/-54). PDM's ``FeatureEquivalent`` flag marks it as
the twin of the listed 9597, so it is priced; options with no listed twin are
still ineligible, and fabric twins (9487 -> 9632) keep working.

Base prices are the live PDM list prices; the 0812/0712 GNND items do not exist
in the live PDM, so their rows mirror the structurally identical 0816 items.
"""

from types import SimpleNamespace

import pytest

from services.sif_validation_service import SifValidationService

match = SifValidationService._match_component_increments

TOP_FPS = "9597|9598|"
FABRIC_FPS = "||9602||3344|3346|"


def _row(parent, comp, seq, sub_id, code, option_id, price, fps, display, ovid,
        equivalent=0):
    return SimpleNamespace(
        ParentItem=parent, Quantity=1, SubItemId=sub_id, ComponentSequence=seq,
        CompItem=comp, DisplayOrder=display, TertiaryOption=0, OptionValueId=ovid,
        FeaturePositionString=fps, DisplayOrdinal=1, OrderCodeValue2=code,
        OptionId=option_id, IncPrice=price, FeatureEquivalent=equivalent,
    )


def _item(parent, top, finish_price, end_comp):
    rows = [
        _row(parent, top, "1", 1, code, 9484, finish_price, TOP_FPS, 1, 100 + n, 1)
        for n, code in enumerate(("HFK", "WFK", "BFK"))
    ]
    for seq, sub_id in (("2", 2), ("3", 3)):
        for n, code in enumerate(("1HS#", "T2RE#")):
            rows.append(_row(parent, f"{end_comp}{seq}", seq, sub_id, code, 3344,
                             73.0, FABRIC_FPS, 900, 200 + n, 1))
    return rows


# parent, top comp, worksurface price, end comp, final article, base, OBX, finish
CASES = [
    ("GH1SPGNND.0816S1MM", "GHTGNN.0816S1M", 79.0, "GHGS",
     "GH1SPGNND.0816S1MM HFK HFK G1 UBK 7V03", 4030.0, 4109.0),
    ("GH1SPGNND.0816S1MM", "GHTGNN.0816S1M", 79.0, "GHGS",
     "GH1SPGNND.0816S1MM HFK HFK 98 UBK 7V03", 4030.0, 4109.0),
    ("GH1SPGNND.0818S1MM", "GHTGNN.0818S1M", 87.0, "GHGS",
     "GH1SPGNND.0818S1MM HFK HFK G1 UBK 7V03", 4085.0, 4172.0),
    ("GH1SPGNND.0812S1MM", "GHTGNN.0812S1M", 58.0, "GHGS",
     "GH1SPGNND.0812S1MM WFK WFK 98 UBK 7V03", 3903.0, 3961.0),
    ("GH1SPGNND.0712S1MM", "GHTGNN.0712S1M", 54.0, "GHGS",
     "GH1SPGNND.0712S1MM WFK WFK 98 UBK 7V03", 3793.0, 3847.0),
]
# Passing comparison articles: no worksurface code, base price only.
PASSING = [
    ("GH1SPSNNU.0716S1MM", "GHTSNN.0716S1M", 76.0,
     "GH1SPSNNU.0716S1MM FJD FJD 98 UBK 7V03", 3919.0, 3919.0),
    ("GH1SPGNND.0816S1MM", "GHTGNN.0816S1M", 79.0,
     "GH1SPGNND.0816S1MM FJD FJD 98 UBK 7V03", 4030.0, 4030.0),
]


@pytest.mark.parametrize("parent,top,price,end,article,base,obx", CASES)
def test_worksurface_increment_is_priced_once(parent, top, price, end, article, base, obx):
    codes = article.split()[1:]
    upcharge = match(_item(parent, top, price, end), codes, parent)

    assert upcharge == price  # exactly one worksurface increment, no fabric rows
    assert round(base + upcharge, 2) == obx


@pytest.mark.parametrize("parent,top,price,article,base,obx", PASSING)
def test_articles_without_a_worksurface_code_keep_base_price(parent, top, price, article, base, obx):
    codes = article.split()[1:]
    upcharge = match(_item(parent, top, price, "GHGS"), codes, parent)

    assert upcharge == 0.0
    assert base + upcharge == obx


def test_option_without_listed_twin_is_still_ineligible():
    parent = "GH1SPGNND.0816S1MM"
    rows = [_row(parent, "GHTGNN.0816S1M", "1", 1, "HFK", 9484, 79.0, TOP_FPS, 1, 1,
                 equivalent=0)]

    assert match(rows, ["HFK"], parent) == 0.0


def test_missing_feature_metadata_keeps_legacy_pricing():
    parent = "GH1SPGNND.0816S1MM"
    rows = [_row(parent, "GHTGNN.0816S1M", "1", 1, "HFK", 9484, 79.0, None, 1, 1)]

    assert match(rows, ["HFK"], parent) == 79.0


def test_worksurface_and_fabric_groups_price_together_without_duplicates():
    parent = "GH1SPGNND.0816S1MM"
    rows = _item(parent, "GHTGNN.0816S1M", 79.0, "GHGS")

    # HFK -> worksurface (79); 1HS01 -> each end component's fabric group (73x2).
    assert match(rows, ["HFK", "HFK", "1HS01"], parent) == 79.0 + 2 * 73.0
    assert match(rows, ["HFK", "HFK", "1HS01", "T2RE01"], parent) == 79.0 + 2 * 73.0
