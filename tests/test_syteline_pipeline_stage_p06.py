"""Tests for stage_p06_item_tail (ExportThread.cs 5009-5425). All fixtures are SYNTHETIC.

Expected values are derived by reading the C# (line numbers cited), not from the port's output.
"""
from __future__ import annotations

import pytest

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.netsem import LegacyFormatError
from services.syteline_export.pipeline.run_base import ExportRunBase, Flow
from services.syteline_export.pipeline.stage_p06_item_tail import P06Mixin

STAGE21 = "ComponentSequence AS Seq"
STAGE22 = "HAVING optval.OptionId"
STAGE24 = "FROM ProductDescription WITH (NOLOCK) WHERE LanguageId"


class H(P06Mixin, ExportRunBase):
    def __init__(self, db):
        super().__init__(db)
        self.streams = []
        self.written = []
        self.fc_args = []

    def write_to_stream(self, sw, data, debugcontext):
        self.streams.append((sw, data, debugcontext))

    def write_data(self, mywriter, mydata, isItem):
        self.written.append((mywriter, mydata, isItem))

    def get_feature_count(self, superproduct):
        self.fc_args.append(superproduct)
        return 3


def comp_row(**kw):
    row = {
        "Item": "SP1", "Super Description": "SuperD", "Seq": 1, "Component": "C1", "Quantity": 2,
        "Description": "Comp", "FeaturePositionString": "", "VolumeLitres": None, "WeightKilos": "1.5",
        "CommodityCode": "CC", "MyBasePrice": "10.5", "Product_Code": "PC", "PriceCode": "P1",
        "DescriptionId": None,
    }
    row.update(kw)
    return row


def opt_row(ov, code, ml, length, name, fab=0, addl=None, short=None, ordinal=1):
    return {"IsFabric": fab, "OptionValueId": ov, "SLFeatureLength": length, "OrderCodeValue": code,
            "max_length": ml, "Name": name, "DisplayOrdinal": ordinal, "AdditionalOptionValueId": addl,
            "parent_optid": -1, "ShortDescription": short}


def make(script, **flags):
    h = H(ScriptedExportDb(script))
    h._syteline = True
    h._exportBasePrices = True
    h._siteId = 4242
    h._languageId = 1
    h._otherlanguageId = 1
    h._catalogueId = 55
    h.materialsWritten = []
    for k, val in flags.items():
        setattr(h, k, val)
    v = h.v
    v.sqlDataReader = {"ItemId": 777, "LongItem": "SP1"}
    v.p05_else_branch = True
    v.arrayList2 = []
    v.arrayList = []
    v.arrayList8 = []
    v.arrayList12 = []
    v.arrayList13 = []
    v.arrayList45 = [101, 102, 103, 104, 105]
    v.text3 = "CAT"
    v.streamWriter2 = "S2"
    v.streamWriter4 = "S4"
    return h


def item_fields_row(text144_prefix, pc, vol, wt, commodity, right6, text136, right7, slots):
    # derived from the token list of C# line 5360
    fields = [pc, vol, wt, "no", "35", "0", "0", "", "", "", "", "1", "0", "EA", commodity, right6, "", "no",
              text136, "", "", right7, "0", "0", ""]
    return text144_prefix + "0\t\t\t" + "\t".join(fields + slots)


def mat_row(text141, code, name):
    # derived from the token list of C# line 5218
    fields = [code + "|" + name, "A", "", "0", "0", "", "", "ZZ-ZZ", "0", "0", "yes", "35", "0", "0", "", "", "",
              "DEF", "1", "0", "EA", "", "P", "", "no", "", "", "", "", "0", "0"]
    return text141 + "\tno\t" + "\t".join(fields)


# ---------------------------------------------------------------- 20.9 (5015-5060)
def test_materialstr_writeout_dedupes_and_flags_com():
    h = make({})
    h._formatCSI = True  # 5062: leave right after 20.9
    h.materialstr = "a\r\nb\tBOCFAB-X-CM01\t1\r\na\r\nlast"
    assert h.p06_item_tail() is Flow.NEXT_ITEM
    assert h.v.arrayList2 == ["a", "b\tBOCFAB-X-CM01\t1", "last"]
    assert h.materialsWritten == ["a", "b\tBOCFAB-X-CM01\t1", "last"]
    assert h.includesCOM is True
    assert h.materialstr == ""
    assert h.threadStage == "20.9"
    assert h.db.calls == []


def test_materialstr_trailing_crlf_and_lone_cr_split_and_blank_lines():
    h = make({})
    h._formatCSI = True
    # 5026-5035: split on lone '\r', strip '\n', skip empties; trailing CRLF -> materialstr = "" (5043)
    h.materialstr = "x\ry\r\n\r\n"
    h.p06_item_tail()
    assert h.v.arrayList2 == ["x", "y"]
    assert h.includesCOM is False


def test_materialstr_last_segment_com_detection_and_already_written():
    h = make({})
    h._formatCSI = True
    h.materialsWritten = ["dup"]
    h.materialstr = "dup\r\nBOCFAB-1-CM01\tq"  # 5049-5058
    h.p06_item_tail()
    assert h.v.arrayList2 == ["BOCFAB-1-CM01\tq"]
    assert h.includesCOM is True


def test_materialstr_skipped_when_else_branch_not_taken():
    h = make({})
    h._formatCSI = True
    h.v.p05_else_branch = False
    h.materialstr = "keep\r\n"
    assert h.p06_item_tail() is Flow.NEXT_ITEM
    assert h.materialstr == "keep\r\n" and h.v.arrayList2 == []


def test_materials_written_none_raises():
    h = make({})
    h._formatCSI = True
    h.materialsWritten = None
    h.materialstr = "a\r\n"
    with pytest.raises(TypeError):
        h.p06_item_tail()


# ---------------------------------------------------------------- 5062
@pytest.mark.parametrize("csi,sl", [(True, True), (False, False), (True, False)])
def test_continue_when_not_syteline_non_csi(csi, sl):
    h = make({})
    h._formatCSI, h._syteline = csi, sl
    assert h.p06_item_tail() is Flow.NEXT_ITEM
    assert h.db.calls == []


# ---------------------------------------------------------------- stage 21 / 23 plain component
def test_plain_component_rows():
    h = make({STAGE21: [comp_row()]})
    assert h.p06_item_tail() is None
    assert h.fc_args == ["SP1"]  # 5254
    assert h.v.num3 == 3
    # 5256 / 5267: superprod row, no option positions
    assert h.streams == [("S2", "SP1\tSuperD\t1\tC1\t2\tComp\t3\t\r\n", "gggggg")]
    slots = [""] * 20
    row = item_fields_row("C1\tno\tComp\tA\t\t10.5\t", "PC", "0", "1.5", "CC", "P", "", "", slots)
    assert h.v.arrayList == [row + "\t\t\t\t"]
    assert h.v.arrayList8 == [row]
    assert h.written == []  # DescriptionId is null: no stage 24


def test_negative_price_clamped_and_duplicate_component_row_not_repeated():
    h = make({STAGE21: [comp_row(MyBasePrice="-3"), comp_row(MyBasePrice="-3")]})
    h.p06_item_tail()
    assert len(h.v.arrayList) == 1  # 5392 dedupe
    assert h.v.arrayList[0].startswith("C1\tno\tComp\tA\t\t0\t0\t\t\tPC")  # 5294: -3 -> 0.0 -> "0"
    assert len(h.streams) == 2  # superprod row is written for every row (5267)


def test_list_price_used_when_not_export_base_prices():
    h = make({STAGE21: [comp_row(ListPrice="7.25")]}, _exportBasePrices=False)
    h.p06_item_tail()
    assert h.v.arrayList[0].startswith("C1\tno\tComp\tA\t\t7.25\t0\t\t\tPC")  # 5303-5311
    sql = h.db.calls[0][1]
    assert "fnGetListPriceByItem(itm2.Item, ?, ?, ?, NULL)" in sql
    assert h.db.calls[0][2][:3] == ("GBP", "", 4242)  # currency, effectiveDate, siteId


def test_super_products_only_stops_after_superprod_row():
    h = make({STAGE21: [comp_row(DescriptionId=9)]}, _superProductsOnly=True)
    h.p06_item_tail()
    assert len(h.streams) == 1  # 23.2 written, 5271 continue
    assert h.v.arrayList == [] and h.v.arrayList8 == []
    assert [c[0] for c in h.db.calls] == ["c2"]


# ---------------------------------------------------------------- stage 22 options
def option_script(per_option):
    def run(conn, sql, params):
        assert conn == "c3"
        return per_option[params[-1]]
    return run


def test_options_features_and_material_rows():
    opt5 = [
        opt_row(101, "A#", 1, 3, "Alpha", short="Alfa"),
        opt_row(102, "B#", 1, 3, "Beta"),
        opt_row(999, "Q#", 1, 3, "NotInCatalogue"),  # 5127: filtered out
        opt_row(105, "ZZ", 2, 3, "Zed", short="Zedd"),
    ]
    opt7 = [
        opt_row(103, "CM01#", 4, 4, "Fab", fab=1, addl="55"),
        opt_row(104, "XY#", 2, 2, "Y", fab=2),
    ]
    h = make({
        STAGE21: [comp_row(FeaturePositionString="5||7|", DescriptionId=77)],
        STAGE22: option_script({5: opt5, 7: opt7}),
        STAGE24: [{"ShortDescription": "OtherDesc"}],
    }, _otherlanguageId=2)
    h.v.arrayList12 = ["C1"]
    h.v.arrayList13 = ["x|ABC"]
    h.p06_item_tail()
    # option position string "5||7|": ids 5, 7 at positions 1 and 3 (5094-5107); 5 and 7 are queried
    assert [c[2][-1] for c in h.db.calls if c[0] == "c3"] == [5, 7]
    # 23.1: positions appended after num3 and tab (5256-5265)
    assert h.streams[0][1] == "SP1\tSuperD\t1\tC1\t2\tComp\t3\t1\t3\r\n"
    # option 5: max_length 2 -> num134 = 2; lengths max(3,2)=3 -> 5 (length5Feats, fabric 0, >2): "F01-05"
    # option 7: num134 = 4, [0] is fabric 1 -> feature length 4 -> "F06-04" (dependent: not in slot list)
    # template: "XXXXX" + "-" + "XXXXXXXX"(CM01# present) then component C1 in arrayList12: slot 1 empty -> "-XXXXX"
    text136 = "XXXXX-XXXXXXXX-XXXXX"
    slots = ["F01-05"] + [""] * 19
    item = item_fields_row("C1\tno\tComp\tA\t\t10.5\t", "PC", "0", "1.5", "CC", "M", text136, "BOC", slots)
    # materials: '#' rows are in arrayList83 but never added to arrayList8/arrayList (5413)
    zz = mat_row("9-F01-05-ZZ", "ZZ", "Zed")
    assert h.v.arrayList8 == [item, zz]
    assert h.v.arrayList == [item + "\t\t\t\t", zz]
    # 24: component description then the material's other-language row (5405, 5420)
    assert h.written == [
        ("S4", "CAT\tC1\tOtherDesc\r\n", False),
        ("S4", "CAT\t9-F01-05-ZZ\tZedd\r\n", False),
    ]
    assert h.threadStage == "24"


def test_fabric_row_naming_and_ignore_opt_deps_slot():
    opt5 = [opt_row(101, "A#", 1, 3, "Alpha")]
    opt7 = [opt_row(103, "CM01#", 4, 4, "Fab", fab=1, addl="55"), opt_row(104, "XY", 2, 2, "Y", fab=2)]
    h = make({
        STAGE21: [comp_row(FeaturePositionString="5|7|")],
        STAGE22: option_script({5: opt5, 7: opt7}),
    }, _ignoreOptDeps=True)
    h.v.arrayList12 = ["C1"]
    h.v.arrayList13 = ["ABC"]  # no '|' -> text145 = "ABC" -> 3 -> 5
    h.p06_item_tail()
    # slot 1 filled with F(1+5)=F06-05 because _ignoreOptDeps (5348-5351)
    item = h.v.arrayList8[0]
    assert item.endswith("\t".join(["F01-05", "F06-05"] + [""] * 18))
    # fabric type 2 row is named 9-FAB-<code> (5214-5217); first-row fabric 1 gives F06-04 for the others
    assert mat_row("9-FAB-XY", "XY", "Y") in h.v.arrayList8


def test_knoll_catalogue_fabric_templates():
    opt = [opt_row(103, "FAB#", 3, 3, "Fab", fab=1)]
    for flatten, expected in ((False, "XXXXXXXXXX"), (True, "XXXXXXXX")):
        h = make({STAGE21: [comp_row(FeaturePositionString="7|")], STAGE22: option_script({7: opt})},
                 _catalogueId=649, _flattenFabrics=flatten)
        h.p06_item_tail()
        assert ("\t" + expected + "\t") in h.v.arrayList8[0]  # 5196


def test_fabric_five_to_four_and_cm01_position_advance():
    # fabric 2 with length 5 -> 4 (5182-5185); CM01# adds 4 more to the running position (5233-5236)
    opts = {5: [opt_row(101, "CM01#", 5, 5, "Fab", fab=2)], 7: [opt_row(102, "Z#", 2, 2, "Z", fab=0)]}
    h = make({STAGE21: [comp_row(FeaturePositionString="5|7|")], STAGE22: option_script(opts)})
    h.p06_item_tail()
    # option 5: num138 4 -> "F01-04"; position 1+4+4 = 9 -> option 7: length 2 -> "F09-02"
    item = h.v.arrayList8[0]
    assert item.endswith("\t".join(["F01-04", "F09-02"] + [""] * 18))


def test_option_with_no_matching_values_is_skipped():
    h = make({STAGE21: [comp_row(FeaturePositionString="5|")],
              STAGE22: option_script({5: [opt_row(999, "Q", 1, 3, "n")]})})
    h.p06_item_tail()
    item = h.v.arrayList8[0]
    assert item.endswith("\t".join([""] * 20))  # 5172: continue, nothing appended
    assert "\tM\t" in item and "\tBOC\t" in item


def test_dependent_option_not_in_feature_slots():
    h = make({STAGE21: [comp_row(FeaturePositionString="5|")],
              STAGE22: option_script({5: [opt_row(101, "A", 1, 3, "n", addl="9")]})})
    h.p06_item_tail()
    assert h.v.arrayList8[0].endswith("\t".join([""] * 20))  # 5190


def test_stage24_no_write_when_languages_equal_or_no_rows():
    h = make({STAGE21: [comp_row(DescriptionId=5)], STAGE24: [{"ShortDescription": "x"}]})
    h.p06_item_tail()  # _languageId == _otherlanguageId
    assert h.written == []
    h = make({STAGE21: [comp_row(DescriptionId=5)], STAGE24: []}, _otherlanguageId=2)
    h.p06_item_tail()
    assert h.written == []


# ---------------------------------------------------------------- malformed data / SQL binding
def test_bad_option_id_raises():
    h = make({STAGE21: [comp_row(FeaturePositionString="x|")]})
    with pytest.raises(LegacyFormatError):
        h.p06_item_tail()


def test_bad_volume_raises():
    h = make({STAGE21: [comp_row(VolumeLitres="abc")]})
    with pytest.raises(LegacyFormatError):
        h.p06_item_tail()


def test_bad_max_length_raises():
    h = make({STAGE21: [comp_row(FeaturePositionString="5|")],
              STAGE22: option_script({5: [opt_row(101, "A", "zz", 3, "n")]})})
    with pytest.raises(LegacyFormatError):
        h.p06_item_tail()


def test_sql_is_parameterised():
    h = make({STAGE21: [comp_row(FeaturePositionString="5|", DescriptionId=31337)],
              STAGE22: option_script({5: [opt_row(101, "A#", 1, 3, "n")]}),
              STAGE24: []},
             _millerCAD=True, _currency="ZZC", _effectiveDate="2099-01-01", _languageId=11, _otherlanguageId=12,
             _catalogueId=909)
    h.p06_item_tail()
    c2, c3, c5 = h.db.calls
    assert c2[0] == "c2" and c2[2] == ("ZZC", "2099-01-01", 4242, 4242, 11, 11, 11, 777)
    assert c3[0] == "c3" and c3[2] == (909, 11, 12, 5)
    assert c5[0] == "c5" and c5[2] == (12, 31337)
    for call in h.db.calls:
        for token in ("ZZC", "2099", "4242", "31337", "909", "777"):
            assert token not in call[1]
