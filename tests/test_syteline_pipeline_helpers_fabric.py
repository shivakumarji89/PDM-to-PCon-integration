"""Tests for HelpersFabricMixin (ExportThread.cs 814-984, 1090-1557).

All fixtures are SYNTHETIC. Expected values are derived from the C# (line numbers cited), not from the port.
"""
from __future__ import annotations

import pytest

from core.cancellation import OperationCancelled
from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.helpers_fabric import HelpersFabricMixin
from services.syteline_export.pipeline.run_base import ExportRunBase


class H(HelpersFabricMixin, ExportRunBase):
    pass


def make(script=None) -> H:
    return H(ScriptedExportDb(script or {}))


# ---------------------------------------------------------------- isInteger (949-984)
def test_is_integer():
    h = make()
    assert h.is_integer("") is False            # 956-959
    assert h.is_integer(None) is False          # VB CompareString(null,"")==0
    assert h.is_integer("12-3") is True         # only "0123456789-" allowed
    assert h.is_integer("-") is True
    assert h.is_integer("1a") is False          # 966-969
    assert h.is_integer("1.5") is False
    assert h.errors == []


# ---------------------------------------------------------------- getTranslation (1090-1121)
def test_get_translation():
    h = make()
    descs = ["d0", "d1", "d2"]
    ids = [10, 11]                   # shorter than descs: index 2 has no id (1099)
    trans = ["t10", ""]
    trans_ids = [10, 11]
    assert h.get_translation(descs, ids, trans, trans_ids, 0) == "t10"   # 1105-1109
    assert h.get_translation(descs, ids, trans, trans_ids, 1) == "d1"    # empty translation keeps desc (1106)
    assert h.get_translation(descs, ids, trans, trans_ids, 2) == "d2"    # index >= len(ids)
    assert h.get_translation(descs, ids, trans, trans_ids, 5) == ""      # index >= both counts
    assert h.get_translation(descs, [99, 98], trans, trans_ids, 0) == "d0"  # IndexOf -> -1
    assert h.errors == []


def test_get_translation_swallows_bad_data():
    h = make()
    # non numeric id: Conversions.ToInteger throws (1101) -> caught (1113), result keeps desc
    assert h.get_translation(["d0"], ["abc"], [], [], 0) == "d0"
    assert len(h.errors) == 1
    # negative index throws ArgumentOutOfRange in C#, not python wrap-around
    h2 = make()
    assert h2.get_translation(["d0"], ["1"], [], [], -1) == ""
    assert len(h2.errors) == 1


# ---------------------------------------------------------------- getItemSequence (1123-1197)
def test_get_item_sequence():
    h = make()
    assert h.get_item_sequence("P1", "A") == 2      # new parent (1128-1139)
    assert h.get_item_sequence("P1", "A") == 2      # existing code -> stored index (1153-1165)
    assert h.get_item_sequence("P1", "B") == 3      # new code: Count(1)+2 (1179)
    assert h.get_item_sequence("P1", "C") == 4
    assert h.get_item_sequence("P1", "B") == 3
    assert h.get_item_sequence("P2", "A") == 2      # separate parent
    assert h.sequenceForItems == ["P1", "P2"]
    assert h.sequenceForItemsOrderCodes == [["A", "B", "C"], ["A"]]
    assert h.sequenceForItemsIndexes == [[2, 3, 4], [2]]
    assert h.errors == []


def test_get_item_sequence_inconsistent_state_swallowed():
    h = make()
    h.sequenceForItems = ["P"]          # no matching order-code list -> ArgumentOutOfRange (1142)
    assert h.get_item_sequence("P", "A") == 2
    assert len(h.errors) == 1


# ---------------------------------------------------------------- updateChildFeatureLength... (814-861)
def test_update_child_feature_length():
    h = make()
    h._convertedList = ["M1", "M2"]
    h._convertChildFeatLen = [-1, -1]
    h.update_child_feature_length_for_material_on_item_tab("M2", "AA-3", False)   # 829-836
    assert h._convertChildFeatLen == [-1, 3]
    h.update_child_feature_length_for_material_on_item_tab("M1", "AA-{x}4", False)  # '}' stripped 832-835
    assert h._convertChildFeatLen == [4, 3]
    h.update_child_feature_length_for_material_on_item_tab("M1", "AA", True)        # no '-' -> 2 (828)
    assert h._convertChildFeatLen == [2, 3]
    assert h.errors == []


def test_update_child_feature_length_not_found_and_malformed():
    h = make()
    h._convertedList = ["M1"]
    h._convertChildFeatLen = [-1]
    h.update_child_feature_length_for_material_on_item_tab("ZZ", "A-1", False)   # 842-851 MsgBox
    assert len(h.errors) == 1 and "_convertedList does NOT contain: [ZZ]" in h.errors[0] and "M1" in h.errors[0]
    h.update_child_feature_length_for_material_on_item_tab("M1", "A-xx", False)   # int.Parse throws 836 -> 853
    assert len(h.errors) == 2 and "LegacyFormatError" in h.errors[1]
    assert h._convertChildFeatLen == [-1]


# ---------------------------------------------------------------- addMaterialToItemTab (863-947)
def _add(h, material, **kw):
    args = dict(description="desc", otherdescription="", status=1, dependentoption=False, issuper=False,
                feature="F", info="i", featlen=3, childoptIds=[7], stage="s")
    args.update(kw)
    h.add_material_to_item_tab(material, args["description"], args["otherdescription"], args["status"],
                               args["dependentoption"], args["issuper"], args["feature"], args["info"],
                               args["featlen"], args["childoptIds"], args["stage"])


def test_add_material_basic_columns():
    h = make()
    _add(h, "9-FAB-AB#", otherdescription="other", status=2, dependentoption=True, issuper=True, childoptIds=["7"])
    assert h._convertedList == ["9-FAB-AB"]              # '#' removed (881)
    assert h._convertIsFab == [True]                      # 877-880
    assert h._convertedDesc == ["AB|desc"]                # prefix after last '-' (891)
    assert h._convertedOtherDesc == ["AB|other"]          # 919
    assert h._convertStatus == [2]
    assert h._convertIsDepOpt == [True]
    assert h._convertHasSuperParent == [True]
    assert h._convertFeaturePos == ["F"]
    assert h._convertFeatLen == [3]
    assert h._convertChildFeatLen == [-1]
    assert h._convertOptionId == [7]                      # ToInteger("7")


def test_add_material_prefix_rules_and_filters():
    h = make()
    _add(h, "X-5-5")
    _add(h, "X-5-6")
    _add(h, "9-FAB-5-5Q")           # StartsWith 9-FAB-5-5, not EndsWith -> Replace (900-903)
    _add(h, "MRFN-AJ-12")           # 908-911
    _add(h, "9-MRFN-AJ-12")
    _add(h, "MRFN-ZZ-12")           # no -AJ-
    assert h._convertedDesc == ["5-5|desc", "5-6|desc", "5-5Q|desc", "AJ|desc", "AJ|desc", "12|desc"]
    assert h._convertedOtherDesc == [""] * 6   # blank other description (913-916)
    assert h._convertIsFab == [False] * 6


def test_add_material_duplicates_ignored_and_featlen_minus_one():
    h = make()
    h._prevConvertFeatLen = 4
    _add(h, "A-1", featlen=-1)
    assert h._convertFeatLen == [4]                       # 926-929
    _add(h, "A-1")                                        # already in _convertedList (882)
    h._materialsOnItemTab.append("B-1")
    _add(h, "B-1")                                        # already on item tab
    _add(h, "#B-1")                                       # '#' removed -> still on item tab, ignored
    assert h._convertedList == ["A-1"]
    assert len(h._convertStatus) == 1


def test_add_material_swallows_errors():
    h = make()
    _add(h, "A-1", childoptIds=[])         # childoptIds[0] throws (871) -> caught 939
    assert h._convertedList == [] and len(h.errors) == 1
    _add(h, "A-1", childoptIds=["x"])       # ToInteger("x") throws
    assert h._convertedList == [] and len(h.errors) == 2


# ---------------------------------------------------------------- GetKnollFabricOrderCode (1199-1282)
def _knoll(rows):
    return make({"optval_FT": rows})


def test_knoll_order_code_cases():
    r = [{"FT_code": "DR#", "FC_code": "XYZ"}]
    assert _knoll(r).get_knoll_fabric_order_code(1, 2, "orig", True) == "XYZ"      # 1250
    assert _knoll(r).get_knoll_fabric_order_code(1, 2, "orig", False) == " "
    r = [{"FT_code": "EVA#", "FC_code": "B12"}]
    assert _knoll(r).get_knoll_fabric_order_code(1, 2, "orig", True) == "12"       # 1253
    assert _knoll(r).get_knoll_fabric_order_code(1, 2, "orig", False) == "1"
    r = [{"FT_code": "HER#", "FC_code": "B12"}]
    assert _knoll(r).get_knoll_fabric_order_code(1, 2, "orig", True) == "12"       # 1256
    assert _knoll(r).get_knoll_fabric_order_code(1, 2, "orig", False) == " "
    r = [{"FT_code": "VOX5#", "FC_code": "VO5123"}]                                  # default branch 1261-1264
    assert _knoll(r).get_knoll_fabric_order_code(1, 2, "orig", True) == "123"
    assert _knoll(r).get_knoll_fabric_order_code(1, 2, "orig", False) == "orig"
    r = [{"FT_code": "ADY1#", "FC_code": "AD1xx"}, ]
    assert _knoll(r).get_knoll_fabric_order_code(1, 2, "orig", True) == "xx"


def test_knoll_order_code_row_iteration_and_empty():
    rows = [{"FT_code": "DR#", "FC_code": "A"}, {"FT_code": "EVA#", "FC_code": "B12"}]
    assert _knoll(rows).get_knoll_fabric_order_code(1, 2, "orig", False) == " "    # break after first (1216)
    assert _knoll(rows).get_knoll_fabric_order_code(1, 2, "orig", True) == "12"    # last row wins (colour)
    assert _knoll([]).get_knoll_fabric_order_code(1, 2, "orig", True) == "orig"
    assert _knoll([{"FT_code": "", "FC_code": "A"}]).get_knoll_fabric_order_code(1, 2, "orig", True) == "orig"
    assert _knoll([{"FT_code": "DR#", "FC_code": None}]).get_knoll_fabric_order_code(1, 2, "orig", True) == "orig"


def test_knoll_order_code_sql_parameterised_and_errors():
    h = _knoll([{"FT_code": "DR#", "FC_code": "A"}])
    h.get_knoll_fabric_order_code(8513, 91234, "o", True)
    conn, sql, params, _ = h.db.calls[0]
    assert params == (8513, 91234) and "8513" not in sql and "91234" not in sql
    assert "WHERE optval.OptionId = ? AND optval.OptionValueId = ?" in sql      # colour 1209
    h.get_knoll_fabric_order_code(1, 2, "o", False)
    assert "WHERE optval_FT.OptionId = ? AND optval_FT.OptionValueId = ?" in h.db.calls[1][1]
    bad = _knoll([{"FT_code": "EVA#"}])            # missing column -> KeyError swallowed (1270)
    assert bad.get_knoll_fabric_order_code(1, 2, "orig", True) == "orig"
    assert len(bad.errors) == 1


# ---------------------------------------------------------------- addFabricColour (1284-1557)
def _fab_row(vid=101, oid=5000, code="ABCDE", supplier="", status=1, desc="Red>Fabric", parent="ABCD", slfl=2):
    return {"OptionValueId": vid, "OptionId": oid, "Name": "n", "OrderCodeValue": code, "SupplierCode": supplier,
            "Status": status, "ShortDescription": desc, "parent_code": parent, "SLFeatureLength": slfl}


def _fab_h(rows1, rows2=None, knoll=None):
    def fabric(conn, sql, params):
        if "LEFT OUTER" in sql:
            return rows2 or []
        return rows1
    script = {"WITH (NOLOCK)": fabric}
    if knoll is not None:
        script["optval_FT"] = knoll
    return make(script)


def test_add_fabric_colour_main_path():
    rows = [_fab_row(), _fab_row(vid=999, oid=5000, code="NOPE"), _fab_row(vid=102, oid=6000, code="OTHER")]
    h = _fab_h(rows)
    h.add_fabric_colour("X-10-02#", 7, [101, 102], False)
    # num = 10+2 (1318-1319) -> "12"; text5 = "02#"; no marker -> Substring(2) (1462); text8 "-05"
    assert h.materialstr == "X-10-02#\tF12-05\t9-FAB-ABCDE\tCDE\t0\t1\t0\t2\t\t\t10\t\r\n"
    assert h.allFabricColours == ["9-FAB-ABCDE"] and h.allFabricColourSequences == ["2"]
    assert h._convertedList == ["9-FAB-ABCDE"]
    assert h._convertedDesc == ["ABCDE|Red Fabric"]          # '>' -> ' ' (1523)
    assert h._convertFeatLen == [5] and h._convertStatus == [1] and h._convertOptionId == [-1]
    assert h.ConvCount == 2 and h.preConv == "X-10-02#"
    # second call with same converted: ConvCount++ (1469), sequence replaced (1512), material not duplicated
    h.add_fabric_colour("X-10-02#", 7, [101], False)
    assert h.ConvCount == 3 and h.allFabricColourSequences == ["3"]
    assert h._convertedList == ["9-FAB-ABCDE"]
    assert h._prevConvertFeatLen == 5
    assert h.errors == []


def test_add_fabric_colour_sql_parameterised():
    h = _fab_h([_fab_row()])
    h._languageId = 4242
    h.add_fabric_colour("X-10-02#", 7, [101], False)
    conn, sql, params, _ = h.db.calls[0]
    assert params == (7, 7, 7, "02#%", 4242)
    assert "02#" not in sql.replace("%#", "") and "4242" not in sql
    assert "LIKE ?" in sql and "od.LanguageId = ?" in sql


def test_add_fabric_colour_fallback_query():
    h = _fab_h([], rows2=[_fab_row(code="ZZ")])
    h.add_fabric_colour("X-10-02#", 7, [101], False)
    assert len(h.db.calls) == 2
    sql2, params2 = h.db.calls[1][1], h.db.calls[1][2]
    assert "LEFT OUTER JOIN" in sql2 and "od.LanguageId = 1" in sql2   # 1403-1411
    assert params2 == ("02#%",)
    assert h._convertedList == ["9-FAB-ZZ"]
    # len(text9) > 2 is False for "ZZ": text9 stays "ZZ" (1443)
    assert "\tZZ\t" in h.materialstr


def test_add_fabric_colour_knoll_catalogue():
    h = _fab_h([_fab_row(oid=8513, code="ABC12")], knoll=[{"FT_code": "DR#", "FC_code": "KNL"}])
    h._catalogueId = 649   # Knoll catalogue
    h.add_fabric_colour("X-10-02#", 7, [101], False)
    sql, params = h.db.calls[0][1], h.db.calls[0][2]
    assert "optval.OrderCodeValue LIKE ?" in sql and "OptionId IN (8513, 8525, 8625)" in sql   # 1339-1346
    assert params == (7, 7, 7, "02#%", "%02#", -1)
    assert "\t9-FAB-ABC12\tKNL\t" in h.materialstr    # GetKnollFabricOrderCode colour (1438)
    assert h.db.calls[1][2] == (8513, 101)


def test_add_fabric_colour_knoll_special_suffixes():
    # text5 = "CUR" (after last '-'): 1339-1350
    h = _fab_h([_fab_row()])
    h._catalogueId = 649
    h.add_fabric_colour("X-10-02#-CUR", 7, [101], False)
    sql, params = h.db.calls[0][1], h.db.calls[0][2]
    assert params == (7, 7, 7, "CUR%", "%CU", -1)
    assert ") AND (optval.OrderCodevalue LIKE '%CU'" in sql
    # text5 = "VOX": Replace VOX->VO in both LIKEs, NOT IN list (1379-1382)
    h = _fab_h([_fab_row()])
    h._catalogueId = 649
    h.add_fabric_colour("X-10-02#-VOX", 7, [101], False)
    sql, params = h.db.calls[0][1], h.db.calls[0][2]
    assert params == (7, 7, 7, "VO%", "%VO", -1)
    assert "NOT IN ('VO785', 'VO947', 'VOBLK'" in sql
    # non-Knoll catalogue: no extra clauses
    h = _fab_h([_fab_row()])
    h.add_fabric_colour("X-10-02#-VOX", 7, [101], False)
    assert "8513" not in h.db.calls[0][1] and h.db.calls[0][2] == (7, 7, 7, "VO%", -1)


def test_add_fabric_colour_marker_variants():
    # -05#: num = nn+5, parent_code len 5 -> Substring(5) (1445-1449), text8 forced "-05" (1493)
    h = _fab_h([_fab_row(code="ABCDEFG", parent="ABCDE")])
    h.add_fabric_colour("X-10-05#", 7, [101], False)
    assert h.materialstr == "X-10-05#\tF15-05\t9-FAB-ABCDEFG\tFG\t0\t1\t0\t2\t\t\t10\t\r\n"
    # -04#: num+4, parent len 5 -> Substring(4); text8 "-04" (1480)
    h = _fab_h([_fab_row(code="ABCDEFG", parent="ABCDE")])
    h.add_fabric_colour("X-10-04#", 7, [101], False)
    assert h.materialstr == "X-10-04#\tF14-04\t9-FAB-ABCDEFG\tEFG\t0\t1\t0\t2\t\t\t10\t\r\n"
    # -03#: num+3, parent len 4 -> Substring(3); text8 "-04" (1476)
    h = _fab_h([_fab_row(code="ABCDEFG", parent="ABCD")])
    h.add_fabric_colour("X-10-03#", 7, [101], False)
    assert h.materialstr == "X-10-03#\tF13-04\t9-FAB-ABCDEFG\tDEFG\t0\t1\t0\t2\t\t\t10\t\r\n"
    # num < 10 -> zero padded (1322)
    h = _fab_h([_fab_row()])
    h.add_fabric_colour("X-03-02#", 7, [101], False)
    assert h.materialstr.startswith("X-03-02#\tF05-05\t")


def test_add_fabric_colour_length5feats_false():
    # 1484-1492: SLFeatureLength > 2 and not _length5Feats -> "-0<len>", capped at 4 for -03#/-04#
    h = _fab_h([_fab_row(slfl=3)])
    h._length5Feats = False
    h.add_fabric_colour("X-10-02#", 7, [101], False)
    assert "\tF12-03\t" in h.materialstr and h._convertFeatLen == [3]
    h = _fab_h([_fab_row(slfl=6, parent="ABCD")])
    h._length5Feats = False
    h.add_fabric_colour("X-10-04#", 7, [101], False)
    assert "\tF14-04\t" in h.materialstr


def test_add_fabric_colour_ignorecolour_and_featlen_update():
    h = _fab_h([_fab_row(supplier="SUP")])
    h._convertFeatLen = [-1]
    h.add_fabric_colour("X-10-02#", 7, [101], True)
    assert h.materialstr == "" and h.allFabricColours == []         # whole 1433-1514 block skipped
    assert h._convertFeatLen == [5, 5] and h._prevConvertFeatLen == 5   # 1517-1521 then add appends 5
    assert h._convertedDesc == ["ABCDE|Red Fabric (SUP)"]            # supplier suffix (1524-1527)
    h2 = _fab_h([_fab_row()])
    h2._convertFeatLen = [3]
    h2.add_fabric_colour("X-10-02#", 7, [101], True)
    assert h2._convertFeatLen == [3, 5]


def test_add_fabric_colour_first_option_group_only():
    # num2 locks onto the first matching OptionId (1426-1429, 1530)
    rows = [_fab_row(vid=101, oid=5000, code="AAAAA"), _fab_row(vid=102, oid=5000, code="BBBBB"),
            _fab_row(vid=103, oid=6000, code="CCCCC")]
    h = _fab_h(rows)
    h.add_fabric_colour("X-10-02#", 7, [101, 102, 103], True)
    assert h._convertedList == ["9-FAB-AAAAA", "9-FAB-BBBBB"]


def test_add_fabric_colour_debug_marker_stripped():
    h = _fab_h([_fab_row()])
    h.add_fabric_colour("X-10-02#{DEBUG:1}", 7, [101], False)       # 1293-1297
    assert h.materialstr.startswith("X-10-02#\tF12-05")
    assert h.preConv == "X-10-02#"


def test_add_fabric_colour_legacy_throws_are_swallowed():
    # {DEBUG without '}' -> Substring(0,0) == "" -> string.Replace("") throws ArgumentException (1297)
    h = _fab_h([_fab_row()])
    h.add_fabric_colour("X-10-02#{DEBUG", 7, [101], False)
    assert len(h.errors) == 1 and "ValueError" in h.errors[0] and h.db.calls == []
    # no -0N# marker -> Substring(-3, 2) throws (1318)
    h = _fab_h([_fab_row()])
    h.add_fabric_colour("ABC", 7, [101], False)
    assert len(h.errors) == 1 and "LegacyRangeError" in h.errors[0]
    # '&' is non-short-circuit: int.Parse(SLFeatureLength) runs even when _length5Feats is true (1484)
    h = _fab_h([_fab_row(slfl=None)])
    h.add_fabric_colour("X-10-02#", 7, [101], False)
    assert len(h.errors) == 1 and "LegacyFormatError" in h.errors[0]
    assert h._convertedList == []
    # the error message carries the SQL text (1549)
    assert "SELECT optval.OptionValueId" in h.errors[0]
    # non numeric OptionValueId (1423)
    h = _fab_h([_fab_row(vid="x")])
    h.add_fabric_colour("X-10-02#", 7, [101], False)
    assert len(h.errors) == 1


def test_abort_stops_fabric_work_before_query_or_conversion():
    h = _fab_h([_fab_row()])
    h._abortThread = True
    with pytest.raises(OperationCancelled):
        h.add_fabric_colour("X-10-02#", 7, [101], False)
    assert h._convertedList == []
    assert h.db.calls == []
