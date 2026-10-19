"""Tests for HelpersMiscMixin (ExportThread.cs getFeatureCount, GetShortProductCode, getParentStartPos,
parseOptCode, formatCSIData, GetProductDescription, getFeatureLengthForItemOption).

All fixtures are synthetic. Expected values are derived from the C# (line numbers cited), not from running the port.
"""
import pytest

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.helpers_misc import HelpersMiscMixin
from services.syteline_export.pipeline.run_base import ExportRunBase


class H(HelpersMiscMixin, ExportRunBase):
    knoll_calls = None

    def is_integer(self, value):  # ExportThread.cs:949 (digits and '-' only, non-empty)
        return value != "" and all(c in "0123456789-" for c in value)

    def get_knoll_fabric_order_code(self, optionId, optvalId, originalCode, colour):  # stub of cs:1199
        self.knoll_calls = (optionId, optvalId, originalCode, colour)
        return "K" + originalCode


def make(script=None):
    db = ScriptedExportDb(script or {})
    return H(db), db


# ---------------------------------------------------------------- getFeatureCount (709)
def test_feature_count_queries_then_caches():
    h, db = make({"FROM ItemComponents": [{"optcount": 3}]})
    assert h.get_feature_count("SP1") == 3
    assert h._SPFeatureItems == ["SP1"] and h._SPFeatureCount == [3]       # cs:734-735
    assert h.get_feature_count("SP1") == 3                                 # cached, cs:715-719
    assert len(db.calls) == 1
    assert db.calls[0][2] == ("SP1",) and "SP1" not in db.calls[0][1]      # parameterised


def test_feature_count_null_optcount_gives_zero_and_is_cached():
    h, _ = make({"FROM ItemComponents": [{"optcount": None}]})             # cs:728 "" check
    assert h.get_feature_count("X") == 0
    assert h._SPFeatureItems == ["X"]


def test_feature_count_bad_data_is_swallowed_and_not_cached():
    h, _ = make({"FROM ItemComponents": [{"optcount": "abc"}]})            # int.Parse throws -> cs:738
    assert h.get_feature_count("X") == 0
    assert h.errors and h._SPFeatureItems == []


def test_feature_count_cached_bad_value_swallowed():
    h, _ = make()
    h._SPFeatureItems = ["A"]
    h._SPFeatureCount = ["zz"]
    assert h.get_feature_count("A") == 0 and h.errors


# ---------------------------------------------------------------- GetShortProductCode (1559)
ROOTS_SQL = "RootProductPrefix"


def test_short_code_asia_screen_root_s_and_b():
    h, db = make({ROOTS_SQL: [{"RootProductPrefix": "AB."}, {"RootProductPrefix": "CD."}]})
    assert h.get_short_product_code("ZZ-1234", "CD.X") == "FRPD:S"         # cs:1586-1591
    assert h.get_short_product_code("ZZ-1234", "CD.XB.") == "FRPD:B"       # cs:1587
    assert h.asiaUniveralScreenRoots == ["AB.", "CD."]
    assert len(db.calls) == 1                                              # roots loaded once (cs:1568)


def test_short_code_gh_m_or_d():
    h, _ = make({ROOTS_SQL: []})
    assert h.get_short_product_code("P", "GHG1M") == "FRGH:M"              # cs:1596-1603
    assert h.get_short_product_code("P", "GHS1") == "FRGH:D"


def test_short_code_default_strips_dash_and_truncates():
    h, _ = make({ROOTS_SQL: []})
    assert h.get_short_product_code("AB-CDEFG", "OTHER") == "ABCD"         # cs:1608-1612
    assert h.get_short_product_code("A-B", "OTHER") == "AB"


def test_short_code_error_returns_prodcode_untouched():
    h, _ = make({ROOTS_SQL: None})                                         # no result set -> RuntimeError
    assert h.get_short_product_code("AB-CDEFG", "X") == "AB-CDEFG" and h.errors


# ---------------------------------------------------------------- getParentStartPos (1630)
def test_parent_start_pos_forward_finds_last_matching_material():
    h, _ = make()
    h.materialsWritten = [
        "x\t9-BOC[A]-F3-12-ON\tdesc",     # matches, but the loop does not break the for: later ones override
        "y\t9-OTHER-ON\t",
        "z\t9-BOC[A]-F5-20-ON\td",
    ]
    r = h.get_parent_start_pos("9-BOC", "ON", False, 0, "ON")
    assert r == (5, 20, "ON")                                              # cs:1695 flag only breaks do-while


def test_parent_start_pos_reverse_iterates_from_end():
    h, _ = make()
    h.materialsWritten = ["a\t9-BOC[A]-F3-12-ON\t", "b\t9-BOC[A]-F5-20-ON\t"]
    assert h.get_parent_start_pos("9-BOC", "ON", True, 0, "ON") == (3, 12, "ON")   # cs:1641-1646: last visited = idx 0


def test_parent_start_pos_at_substitution_on_second_pass():
    h, _ = make()
    h.materialsWritten = ["a\t9-BOC[A]-F4-7-AT\t"]
    assert h.get_parent_start_pos("9-BOC", "ON", False, 0, "ON") == (4, 7, "AT")   # cs:1670-1674


def test_parent_start_pos_debug_markers_removed():
    h, _ = make()
    h.materialsWritten = ["a\t9-BOC{DEBUGAA}[A]-F{DEBUGii}2-9-FI\t"]
    assert h.get_parent_start_pos("9-BOC", "FI", False, 0, "FI") == (2, 9, "FI")   # cs:1659-1666


def test_parent_start_pos_no_match_returns_defaults():
    h, _ = make()
    h.materialsWritten = ["a\tnothing\t"]
    assert h.get_parent_start_pos("9-BOC", "ON", False, 4, "S") == (1, 4, "S")
    h.materialsWritten = []
    assert h.get_parent_start_pos("9-BOC", "ON", True, 4, "S") == (1, 4, "S")


def test_parent_start_pos_no_f_marker_still_ok_and_non_integer_ignored():
    h, _ = make()
    h.materialsWritten = ["a\t9-BOC-ON\t"]                                  # no "]-F" -> result stays 1 (cs:1678)
    assert h.get_parent_start_pos("9-BOC", "ON", False, 0, "ON") == (1, 0, "ON")
    h.materialsWritten = ["a\t9-BOC[A]-F3-ab-ON\t"]                          # text3 'ab' not integer (cs:1684)
    assert h.get_parent_start_pos("9-BOC", "ON", False, 0, "ON") == (3, 0, "ON")


def test_parent_start_pos_lone_dash_throws_inside_and_is_swallowed():
    h, _ = make()
    # text3 == "-" is "integer" per isInteger but int.Parse throws (cs:1686) -> caught at 1713, result stays 1
    h.materialsWritten = ["a\t9-BOC[A]-F3---ON\t"]
    assert h.get_parent_start_pos("9-BOC", "ON", False, 0, "ON") == (1, 0, "ON")
    assert h.errors


def test_parent_start_pos_materials_none_swallowed():
    h, _ = make()
    assert h.get_parent_start_pos("9-BOC", "ON", False, 0, "ON") == (1, 0, "ON")
    assert h.errors


# ---------------------------------------------------------------- parseOptCode (1724)
def test_parse_opt_code_strips_m_and_c_only():
    h, _ = make()
    assert h.parse_opt_code("amcb", 1, 100) == "ab"                        # cs:1728
    assert h.knoll_calls is None


@pytest.mark.parametrize("option_id", [8512, 8524, 8624])
def test_parse_opt_code_knoll_options(option_id):
    h, _ = make()
    assert h.parse_opt_code("1mc2", 77, option_id) == "K12"                # cs:1729-1731
    assert h.knoll_calls == (option_id, 77, "12", False)


def test_parse_opt_code_knoll_failure_swallowed_returns_stripped():
    h, _ = make()

    def boom(*a):
        raise RuntimeError("x")
    h.get_knoll_fabric_order_code = boom
    assert h.parse_opt_code("1m", 1, 8512) == "1" and h.errors             # cs:1734-1741


# ---------------------------------------------------------------- formatCSIData (1744)
def csi(h, **kw):
    args = dict(myitem="ITEM1", issuper="no", shortdesc="Short desc", statusflag="A", reasoncode="R",
                productcode="PC", volume=9.5, weight=2.5, UM="EA", commcode="CC", PM="P", template="1X2X")
    args.update(kw)
    return h.format_csi_data(**args)


def test_format_csi_column_count_and_positions():
    h, _ = make()
    out = csi(h)
    assert out.endswith("\r\n") and out.count("\r\n") == 1
    cols = out[:-2].split("\t")
    # 212 Add() calls (cs:1752-1975) of which two are the else branches of PM -> 210 columns
    assert len(cols) == 210
    # 0-based positions counted from the Add() sequence
    assert cols[0] == "ITEM1" and cols[1] == "Short desc" and cols[5] == "ITEM1"       # 1752,1753,1757
    assert cols[3] == "0" and cols[9] == "1"
    assert cols[10] == "EA" and cols[11] == "Material"                                 # 1762-1763
    assert cols[12] == "Purchased"                                                     # 1766
    assert cols[13] == "PC" and cols[14] == "C" and cols[15] == "Actual" and cols[16] == "Specific"
    assert cols[20] == "2.5"                                                           # weight, 1779
    assert cols[40] == "Job" and cols[63] == "Lead Time" and cols[78] == "&N"
    assert cols[83] == "Lot – Lot Number" and cols[84] == "Active"
    assert cols[101] == "CC"                                                           # commcode, 1860
    assert cols[114] == "Never" and cols[115] == "Prompt"
    assert cols[122] == "1&2&"                                                         # template X->&, 1881
    assert cols[160] == "None" and cols[167] == "No-Pull-Up" and cols[188] == "-1"
    assert cols[191:197] == ["No", "Yes", "No", "No", "No", "No"]                      # 1950-1955
    assert cols[198] == "Purchased"                                                    # 1959
    assert cols[199] == "Item" and cols[200] == "30" and cols[201] == "I"
    assert cols[203] == "No" and cols[208] == "No" and cols[209] == "Yes"
    # arguments that legacy ignores
    assert "9.5" not in cols and "A" not in cols and "R" not in cols and "no" not in cols[:5]


def test_format_csi_manufactured_branch_and_other_values():
    h, _ = make()
    cols = csi(h, PM="M", weight=0.0, template="").rstrip("\r\n").split("\t")
    assert len(cols) == 210
    assert cols[12] == "Manufactured" and cols[198] == "Manufactured"                  # cs:1770, 1963
    assert cols[20] == "0" and cols[122] == ""
    cols2 = csi(h, PM="X").rstrip("\r\n").split("\t")                                  # only "P" is Purchased
    assert cols2[12] == "Manufactured"


def test_format_csi_weight_uses_dotnet_double_tostring():
    h, _ = make()
    assert csi(h, weight=1e-05).split("\t")[20] == "1E-05"


def test_format_csi_template_non_string_swallowed():
    h, _ = make()
    assert csi(h, template=None) == "" and h.errors                                   # cs:1881 NRE -> cs:1987


# ---------------------------------------------------------------- GetProductDescription (1998)
def test_product_description_appends_bracketed_text():
    h, db = make({"FROM Item INNER JOIN BaseAttributeValues": [
        {"ShortDescription": "Colour [Red] x"}, {"ShortDescription": "Size [XL]"}]})
    h._languageId = 5
    assert h.get_product_description("IT1", "Chair") == "Chair Red XL"     # cs:2010-2013
    assert db.calls[0][2] == (5, "IT1") and "IT1" not in db.calls[0][1]


def test_product_description_bad_row_keeps_prior_appends_and_reports():
    h, _ = make({"FROM Item INNER JOIN BaseAttributeValues": [
        {"ShortDescription": "A [One]"}, {"ShortDescription": "A [Two"}, {"ShortDescription": "B [Three]"}]})
    assert h.get_product_description("IT1", "D") == "D One"                # IndexOf("]") = -1 -> throws cs:2012
    assert h.errors


def test_product_description_no_rows():
    h, _ = make({"FROM Item INNER JOIN BaseAttributeValues": []})
    assert h.get_product_description("IT1", "D") == "D"


# ---------------------------------------------------------------- getFeatureLengthForItemOption (2031)
OPT = [
    {"ParentOptValCode": "AA", "ParentOptvalName": "Alpha", "OptionId": 11},
    {"ParentOptValCode": "AA", "ParentOptvalName": "Beta", "OptionId": 12},
]


def test_feature_length_matches_name_after_pipe_and_caches():
    h, db = make({"PDMOptionDataReport": OPT, "SLFeatureLength": [{"SLFeatureLength": 4}]})
    assert h.get_feature_length_for_item_option("IT", "AA|Beta") == 4      # cs:2049-2062
    assert h.cachedItemOptFeatKeys == ["IT~AA|Beta"] and h.cachedItemOptFeatLens == [4]
    assert db.calls[0][2] == ("IT",) and db.calls[1][2] == (12,)           # OptionId 12 matched Beta
    assert h.get_feature_length_for_item_option("IT", "AA|Beta") == 4
    assert len(db.calls) == 2


def test_feature_length_empty_name_matches_first_code():
    h, db = make({"PDMOptionDataReport": OPT, "SLFeatureLength": [{"SLFeatureLength": "6"}]})
    assert h.get_feature_length_for_item_option("IT", "AA") == 6            # text2 == "" (cs:2060)
    assert db.calls[1][2] == (11,)


def test_feature_length_no_match_default_two_and_cached():
    h, db = make({"PDMOptionDataReport": OPT})
    assert h.get_feature_length_for_item_option("IT", "ZZ") == 2           # num3 stays -1 (cs:2067)
    assert h.cachedItemOptFeatLens == [2] and len(db.calls) == 1


def test_feature_length_bad_data_swallowed_not_cached():
    h, _ = make({"PDMOptionDataReport": OPT, "SLFeatureLength": [{"SLFeatureLength": None}]})
    assert h.get_feature_length_for_item_option("IT", "AA") == 2           # int.Parse("") throws cs:2074
    assert h.errors and h.cachedItemOptFeatKeys == []
    h2, _ = make({"PDMOptionDataReport": [{"ParentOptValCode": "AA", "ParentOptvalName": "", "OptionId": "x"}]})
    assert h2.get_feature_length_for_item_option("IT", "AA") == 2 and h2.errors


def test_feature_length_cached_value_used_without_sql():
    h, db = make()
    h.cachedItemOptFeatKeys = ["IT~AA"]
    h.cachedItemOptFeatLens = [9]
    assert h.get_feature_length_for_item_option("IT", "AA") == 9
    assert db.calls == []
