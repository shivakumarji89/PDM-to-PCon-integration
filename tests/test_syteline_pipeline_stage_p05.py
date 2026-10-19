"""Tests for P05Mixin (ExportThread.cs 4192-5008). All fixtures are synthetic.

Expected values are derived by reading the C# (line numbers cited), not by running the port.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.netsem import LegacyFormatError, LegacyRangeError
from services.syteline_export.pipeline.run_base import ExportRunBase
from services.syteline_export.pipeline.stage_p05_item_row import P05Mixin


class H(P05Mixin, ExportRunBase):
    """Harness: records calls to the helpers that live in other mixins."""

    def __init__(self, db):
        super().__init__(db)
        self.written = []
        self.csi_calls = []
        self.added = []
        self.child_calls = []
        self.featlen = 3

    def write_data(self, writer, data, is_item):
        self.written.append((writer, data, is_item))

    def format_csi_data(self, *args):
        self.csi_calls.append(args)
        return "CSI-ROW"

    def get_product_description(self, longitem, shortdesc):
        return shortdesc

    def get_short_product_code(self, prodcode, rootproduct):
        return "PC"

    def get_feature_length_for_item_option(self, item, desc):
        return self.featlen

    def update_child_feature_length_for_material_on_item_tab(self, item, feat, verbose):
        self.child_calls.append((item, feat, verbose))

    def add_material_to_item_tab(self, *args):
        self.added.append(args)


def base_row(**kw):
    row = {
        "LongItem": "ITEM-LONG", "Item": "ITEM1", "IsSuperProduct": False, "Notes": "", "LegacyItem": "",
        "Status": 1, "WeightKilos": "2", "VolumeLitres": "", "ShortDescription": "Short>Desc",
        "FSCCompliant": None, "Product_Code": "PCODE", "PriceCode": "PRC", "CommodityCode": "COMM",
        "MyBasePrice": "12.5", "ListPrice": "20", "Description": "LISTDESC", "AltDescription": None,
    }
    row.update(kw)
    return row


def make(row=None, script=None, **flags):
    h = H(ScriptedExportDb(script or {}))
    v = h.v
    v.sqlDataReader = row or base_row()
    v.flag4 = False
    v.text19 = ""
    v.arrayList = []
    v.arrayList46 = []
    v.arrayList26 = []
    v.arrayList38, v.arrayList39, v.arrayList40, v.arrayList41, v.arrayList42 = [], [], [], [], []
    v.num4 = Decimal("7.50")
    v.text3 = "LANG"
    v.text6 = "BOCFAB"
    v.text16, v.text17, v.text18 = "H", "W", "D"
    v.streamWriter4 = "W4"
    v.prodcode, v.rootproduct = "pc", "root"
    for k, val in flags.items():
        setattr(h, k, val)
    return h


def expected_syteline_prefix():
    # fields 0..33 per ExportThread.cs:4385-4417 (derived by counting the concatenation), plain item
    return ["ITEM-LONG", "no", "Short Desc", "A", "", "12.5", "7.50", "", "", "PCODE", "0", "2", "no", "35",
            "0", "0", "", "", "", "", "1", "0", "EA", "COMM", "P", "", "no", "", "", "", "",
            "0", "0", ""]


# ---------------------------------------------------------------- item row, SyteLine
def test_syteline_item_row_58_tabs_and_columns():
    h = make(_syteline=True)
    h.v.arrayList46 = ["BOCFAB-A", "B"]
    assert h.p05_item_row_and_renumber() is None
    assert h.v.p05_else_branch is True
    (line,) = h.v.arrayList
    assert line.endswith("\t\r\n")
    parts = line[:-2].split("\t")
    # 34 header fields + 20 feature slots (4417-4450) + "" + H + W + D + trailing "" (4451) = 59 parts
    assert len(parts) == 59 and line[:-2].count("\t") == 58
    assert parts[:34] == expected_syteline_prefix()
    assert parts[34:54] == ["A", "B"] + [""] * 18   # "BOCFAB-" is stripped via text6 + "-" (4421)
    assert parts[54:] == ["", "H", "W", "D", ""]
    assert h.threadStage == "17.16"


def test_syteline_item_row_exactly_20_features_loses_one_separator():
    # 4434/4439: the i == 19 slot has no tab and no padding loop -> one column fewer (legacy quirk)
    h = make(_syteline=True)
    h.v.arrayList46 = [f"f{i}" for i in range(20)]
    h.p05_item_row_and_renumber()
    parts = h.v.arrayList[0][:-2].split("\t")
    assert len(parts) == 58
    assert parts[34:54] == [f"f{i}" for i in range(20)]
    assert parts[54:] == ["H", "W", "D", ""]


def test_feature_text_rules_bocfab_lowercase_and_har():
    h = make(_syteline=True)
    h.v.arrayList46 = ["xx-bocfab-yy", "A-HAR-F01-02"]   # 4426 case-sensitive "bocfab" skip; 4428 HAR cut
    h.p05_item_row_and_renumber()
    parts = h.v.arrayList[0][:-2].split("\t")
    assert parts[34] == ""            # contains "bocfab" -> nothing written, tab still written
    assert parts[35] == "F01-02"


def test_status_variants_and_header_fields():
    for status, flag, reason in ((0, "O", "URL"), (1, "A", ""), (2, "O", "OBS"), (3, "O", "ON HOLD"), (7, "O", "")):
        h = make(base_row(Status=status), _syteline=True)
        h.p05_item_row_and_renumber()
        parts = h.v.arrayList[0].split("\t")
        assert (parts[3], parts[4]) == (flag, reason)   # 4216-4233


def test_notes_legacyitem_override_and_trailing_dash():
    h = make(base_row(Notes="ABX-"), _syteline=True)
    h.p05_item_row_and_renumber()
    parts = h.v.arrayList[0].split("\t")
    assert parts[27] == "ABX" and parts[24] == "M" and parts[30] == "BOC"   # 4207, 4239-4244

    h = make(base_row(Notes="none", LegacyItem="QX"), _syteline=True)       # 4211
    h.p05_item_row_and_renumber()
    parts = h.v.arrayList[0].split("\t")
    assert parts[27] == "QX" and parts[24] == "M"

    h = make(base_row(), _syteline=True)
    h.v.text19 = "LEFTOVER"          # 4235-4250: text19 non-empty keeps "M"
    h.p05_item_row_and_renumber()
    assert h.v.arrayList[0].split("\t")[24] == "M"

    h = make(base_row(), _syteline=True)
    h.p05_item_row_and_renumber()
    parts = h.v.arrayList[0].split("\t")
    assert (parts[24], parts[27], parts[30]) == ("P", "", "")


def test_weight_volume_and_fsc_hash_and_price_clamp():
    h = make(base_row(WeightKilos="1.5", VolumeLitres="0.25", FSCCompliant=1, MyBasePrice="-3"), _syteline=True)
    h.p05_item_row_and_renumber()
    parts = h.v.arrayList[0].split("\t")
    assert parts[2] == "Short Desc#"           # 4262-4265
    assert (parts[10], parts[11]) == ("0.25", "1.5")
    assert parts[5] == "0"                     # 4393 clamp

    h = make(base_row(FSCCompliant=2), _syteline=True)
    h.p05_item_row_and_renumber()
    assert h.v.arrayList[0].split("\t")[2] == "Short Desc"


def test_list_price_used_when_not_exporting_base_prices():
    h = make(base_row(ListPrice="-4"), _syteline=True, _exportBasePrices=False)
    h.p05_item_row_and_renumber()
    assert h.v.arrayList[0].split("\t")[5] == "0"
    h = make(base_row(ListPrice=""), _syteline=True, _exportBasePrices=False)
    h.p05_item_row_and_renumber()
    assert h.v.arrayList[0].split("\t")[5] == "0"
    h = make(base_row(ListPrice="3.5"), _syteline=True, _exportBasePrices=False)
    h.p05_item_row_and_renumber()
    assert h.v.arrayList[0].split("\t")[5] == "3.5"


def test_super_product_row_marked_sup_and_text19_reset():
    h = make(base_row(IsSuperProduct=True), _syteline=True)
    h.v.text19 = "OLD"
    h.v.arrayList46 = ["junk"]
    h.p05_item_row_and_renumber()                 # 4201-4206: text5 yes, text19 "", arrayList46 cleared
    parts = h.v.arrayList[0].split("\t")
    assert parts[1] == "yes" and parts[19] == "SUP" and parts[27] == ""
    assert h.v.arrayList46 == []
    assert h.v.text5 == "yes"


def test_alt_description_goes_through_write_data_not_item():
    h = make(base_row(AltDescription="Alt>D"), _syteline=True, _languageId=1, _otherlanguageId=2)
    h.p05_item_row_and_renumber()
    assert h.written == [("W4", "LANG\tITEM-LONG\tAlt D\r\n", False)]          # 4481-4484
    h = make(base_row(AltDescription="Alt"), _syteline=True, _languageId=1, _otherlanguageId=1)
    h.p05_item_row_and_renumber()
    assert h.written == []
    h = make(base_row(AltDescription="Alt"), _syteline=True, _languageId=1, _otherlanguageId=2, _formatCSI=True)
    h.p05_item_row_and_renumber()
    assert h.written == []


def test_csi_row_replaces_item_row():
    h = make(_syteline=True, _formatCSI=True)
    h.p05_item_row_and_renumber()
    assert h.v.arrayList == ["CSI-ROW"]
    # 4477: (item, text5, desc, status, reason, productcode, volume, weight, "EA", commodity, "P", "")
    assert h.csi_calls == [("ITEM-LONG", "no", "Short Desc", "A", "", "PCODE", 0.0, 2.0, "EA", "COMM", "P", "")]


def test_non_syteline_non_cad_row_has_7_fields():
    h = make(_syteline=False, _millerCAD=False)
    h.p05_item_row_and_renumber()
    (line,) = h.v.arrayList
    assert line == "ITEM-LONG\tno\tShort Desc\tA\t12.5\tPCODE\tPRC\r\n"        # 4463-4474
    assert len(line[:-2].split("\t")) == 7
    assert h._priceCodes == ["PRC"] and h._productCodes == ["PCODE"]
    h.p05_item_row_and_renumber()
    assert h._priceCodes == ["PRC"]                                              # no duplicates (4455)


# ---------------------------------------------------------------- SP-skip branch (17.14 if)
def test_sp_components_skipped_syteline_row_has_34_tabs_no_crlf():
    h = make(base_row(IsSuperProduct=True), _syteline=True, _exportSPComponentMaterials=False)
    h.p05_item_row_and_renumber()
    assert h.v.p05_else_branch is False
    (line,) = h.v.arrayList
    assert line.count("\t") == 34 and not line.endswith("\n")
    parts = line.split("\t")
    # 4325: fields 5,6 = "0","0"; 7,8 empty; 9 code; 10 vol; 11 weight; 19 SUP ... 24 P, 26 no, 31/32 "0"
    assert parts[:9] == ["ITEM-LONG", "yes", "Short Desc", "A", "", "0", "0", "", ""]
    assert parts[9:12] == ["PCODE", "0", "2"]
    assert parts[12:19] == ["no", "35", "0", "0", "", "", ""]
    assert parts[19:25] == ["SUP", "1", "0", "EA", "COMM", "P"]
    assert parts[25:] == ["", "no", "", "", "", "", "0", "0", "", ""]
    assert len(parts) == 35


def test_sp_skip_csi_and_non_syteline_and_alt_description():
    h = make(base_row(IsSuperProduct=True, AltDescription="A"), _syteline=True, _formatCSI=True,
             _exportSPComponentMaterials=False)
    h.p05_item_row_and_renumber()
    assert h.v.arrayList == ["CSI-ROW"] and h.csi_calls[0][1] == "yes" and h.written == []

    h = make(base_row(IsSuperProduct=True, AltDescription="A"), _syteline=True, _superProductsOnly=True,
             _languageId=1, _otherlanguageId=2)
    h.p05_item_row_and_renumber()
    assert h.written == [("W4", "LANG\tITEM-LONG\tA\r\n", False)]               # 4334

    h = make(base_row(IsSuperProduct=True), _syteline=False, _exportSPComponentMaterials=False)
    h.p05_item_row_and_renumber()
    # 4347: 7 fields, empty 5th, no CRLF
    assert h.v.arrayList == ["ITEM-LONG\tyes\tShort Desc\tA\t\tPCODE\tPRC"]
    assert h._priceCodes == ["PRC"]


# ---------------------------------------------------------------- millerCAD
def test_millercad_item_row_fixed_width_211():
    h = make(_millerCAD=True, _maxDescriptionLength=40)
    h.v.arrayList46 = ["BOCFAB-X", "Y", "Z"]
    h.p05_item_row_and_renumber()
    (line,) = h.v.arrayList
    assert line.endswith("\r\n")
    body = line[:-2]
    assert len(body) == 30 + 10 + 30 + 10 + 40 + 11 + 80 == 211
    assert body[:30] == "ITEM-LONG".ljust(30) and body[30:40] == "PCODE".ljust(10)
    assert body[40:70] == "LISTDESC".ljust(30)
    assert body[70:80] == "0000020.00"                      # 4361 {20:f2}.PadLeft(10,'0')
    assert body[80:120] == "Short Desc".ljust(40)
    assert body[120:131] == "1" + "111" + "0000000"           # 4362-4370
    assert body[131:] == "X Y Z ".ljust(80)                   # 4375-4381 (BOCFAB- stripped, space after each)


def test_millercad_sp_skip_row_is_135_chars_with_markers():
    h = make(base_row(IsSuperProduct=True), _millerCAD=True, _maxDescriptionLength=40,
             _exportSPComponentMaterials=False)
    h.p05_item_row_and_renumber()
    (line,) = h.v.arrayList
    assert len(line) == 30 + 10 + 30 + 10 + 40 + len("[bitmap][feats]") == 135   # 4321
    assert line.endswith("[bitmap][feats]") and line[70:80] == "0000020.00"


def test_millercad_materialstr_rewrite():
    h = make(_millerCAD=True, _maxDescriptionLength=40)
    h.materialstr = "ITEM\tA\tB\tQTY\t2.5\ttrail\r\n"
    h.p05_item_row_and_renumber()
    # 4275-4283 drop 3rd field and keep 4 fields; 4296-4302 pad 30/8/8 and f2 left-padded to 8
    assert h.materialstr == "ITEM".ljust(30) + "A".ljust(8) + "QTY".ljust(8) + "00002.50" + "\r\n"


def test_millercad_materialstr_malformed_raises():
    h = make(_millerCAD=True)
    h.materialstr = "ITEM\tA\tB\tQTY\r\n"      # text101 ends up without a tab -> Substring(0, -1) at 4296
    with pytest.raises(LegacyRangeError):
        h.p05_item_row_and_renumber()
    h = make(_millerCAD=True)
    h.materialstr = "ITEM\tA\tB\tQTY\tnotnum\ttrail\r\n"      # double.Parse at 4302
    with pytest.raises(LegacyFormatError):
        h.p05_item_row_and_renumber()


def test_millercad_super_product_materialstr_item_prefix():
    h = make(base_row(IsSuperProduct=True), _millerCAD=True, _maxDescriptionLength=40)
    h.materialstr = "ITEM\tA\tB\tQTY\t2.5\ttrail\r\n"
    h.p05_item_row_and_renumber()
    base = "ITEM".ljust(30) + "A".ljust(8) + "QTY".ljust(8) + "00002.50"
    # 4303-4310: IndexOf(" ")=4 < len("ITEM1")=5 -> num83 = 1; "ITEM1 " + base[6:] + CRLF, then + CRLF (4312)
    assert h.materialstr == "ITEM1 " + base[6:] + "\r\n" + "\r\n"


# ---------------------------------------------------------------- malformed data
def test_malformed_status_and_bool_and_numbers_raise():
    with pytest.raises(LegacyFormatError):
        make(base_row(Status="x"), _syteline=True).p05_item_row_and_renumber()
    with pytest.raises(LegacyFormatError):
        make(base_row(IsSuperProduct="maybe"), _syteline=True).p05_item_row_and_renumber()
    with pytest.raises(LegacyFormatError):
        make(base_row(WeightKilos="abc"), _syteline=True).p05_item_row_and_renumber()
    with pytest.raises(LegacyFormatError):
        make(base_row(MyBasePrice="abc"), _syteline=True).p05_item_row_and_renumber()


# ---------------------------------------------------------------- stages 17.17-20.83
def super_harness(materialstr, script=None, **flags):
    flags.setdefault("_syteline", True)
    h = make(base_row(IsSuperProduct=True), script=script, **flags)
    h.materialstr = materialstr
    return h


Q18 = "SELECT itco.FeaturePositionString"
Q19 = "SELECT optval.OptionId"
Q20 = "SLFeatureLength, CASE"


def lookup_script(positions="|5|", sl=2, mx=2, fab=0, optid=5):
    return {
        Q18: [{"FeaturePositionString": positions}],
        Q19: [{"OptionId": optid}],
        Q20: [{"SLFeatureLength": sl, "max_length": mx, "IsFabric": fab}],
    }


def q20_calls(h):
    return [c for c in h.db.calls if "HAVING" in c[1]]


def test_renumber_and_missing_component_row():
    h = super_harness("SUB\t[opt5_1]\tCOMP\tDESC|X\t\r\n", lookup_script())
    h.p05_item_row_and_renumber()
    # 4688-4750: first sight of SUB -> position 1, feature length 2 -> "F01-02" (4850)
    # 20.83 (4996): "DESC|X" -> "DESC" ; 20.82: F03-03 from 1 + 2 and featlen 3 (4955-4962)
    assert h.materialstr == "SUB\tF01-02\tCOMP\tDESC\t\r\n"
    assert h.added == [("COMP", "X", "", 1, True, False, "F03-03", " <missing>", 3, [-1], "20.825")]
    assert h.v.p05_else_branch is True


def test_sql_is_parameterised_and_on_c2():
    h = super_harness("SUB\t[opt5_1]\tCOMP\tDESC|X\t\r\n", lookup_script())
    h.p05_item_row_and_renumber()
    calls = h.db.calls
    assert [c[0] for c in calls] == ["c2", "c2"]
    assert calls[0][2] == ("ITEM-LONG", "SUB") and "ITEM-LONG" not in calls[0][1] and "'SUB'" not in calls[0][1]
    assert calls[1][2] == (h._catalogueId, 5)
    assert "= ?" in calls[1][1]
    assert [c[3] for c in calls] == ["18", "20"]
    assert h.threadStage == "20.81"   # trailing array9 element re-enters 20.81 (4931)


def test_text114_lookup_query19_params():
    h = super_harness("SUB\t[opt5_1]-AB\tCOMP\tD\t\r\n", lookup_script(positions="|7|5|", optid=5))
    h.p05_item_row_and_renumber()
    q19 = [c for c in h.db.calls if Q19 in c[1]]
    # 4607-4625: option 7 is queried first and returns OptionId 5 -> IndexOf = 1 -> break
    assert q19[0][2] == (7, "AB", "AB#") and q19[0][3] == "19" and len(q19) == 1
    assert "AB" not in q19[0][1]
    assert q20_calls(h)[0][2] == (h._catalogueId, 5)           # myOptIds[1]


def test_default_option_index_rule_two_candidates():
    # 4629: no "#_1" in the placeholder and more than one candidate -> index 1
    h = super_harness("SUB\t[opt5_2]\tC\tD\t\r\n", lookup_script(positions="|7|5|"))
    h.p05_item_row_and_renumber()
    assert q20_calls(h)[0][2][1] == 5
    h = super_harness("SUB\t[opt5#_1]\tC\tD\t\r\n", lookup_script(positions="|7|5|"))
    h.p05_item_row_and_renumber()
    assert q20_calls(h)[0][2][1] == 7


def test_filter_by_num97_from_angle_brackets():
    h = super_harness("SUB<5>\t[opt5_1]\tC\tD\t\r\n", lookup_script(positions="|7|5|"))
    h.p05_item_row_and_renumber()
    assert q20_calls(h)[0][2][1] == 5                 # 4599: only option id 5 kept
    assert h.db.calls[0][2] == ("ITEM-LONG", "SUB")   # "<5>" stripped from text108 (4522)


def test_feature_length_rules():
    # 4651: max_length > SLFeatureLength only when SLFeatureLength == 2; 4674: length5 rule
    h = super_harness("SUB\t[opt5_1]\tC\tD\t\r\n", lookup_script(sl=2, mx=6), _length5Feats=True)
    h.p05_item_row_and_renumber()
    assert h.materialstr.startswith("SUB\tF01-05\t")
    h = super_harness("SUB\t[opt5_1]\tC\tD\t\r\n", lookup_script(sl=2, mx=6), _length5Feats=False)
    h.p05_item_row_and_renumber()
    assert h.materialstr.startswith("SUB\tF01-06\t")
    h = super_harness("SUB\t[opt5_1]\tC\tD\t\r\n", lookup_script(sl=4, mx=6), _length5Feats=False)
    h.p05_item_row_and_renumber()
    assert h.materialstr.startswith("SUB\tF01-04\t")
    h = super_harness("SUB\t[opt5_1]\tC\tD\t\r\n", lookup_script(sl=2, mx=2), _length5Feats=True)
    h.p05_item_row_and_renumber()
    assert h.materialstr.startswith("SUB\tF01-02\t")
    assert h.v.arrayList38 == [2] and h.v.arrayList39 == [False] and h.v.arrayList40 == [5]


def test_feature_length_cache_skips_query20():
    h = super_harness("SUB\t[opt5_1]\tC\tD\t\r\n", lookup_script())
    h.v.arrayList38, h.v.arrayList39, h.v.arrayList40 = [4], [False], [5]
    h.p05_item_row_and_renumber()
    assert q20_calls(h) == []
    assert h.materialstr.startswith("SUB\tF01-05\t")      # cached 4 > 2 -> length5 rule -> 5


def test_fabric_replacement_prefix_and_strip():
    h = super_harness("SUB\t[opt5_1]\tBOCFAB-X\tD\t\r\n", lookup_script(sl=2, mx=6, fab=1), _length5Feats=True)
    h.p05_item_row_and_renumber()
    # flag15 -> text121 "BOCFAB[PC]-" (4847), no length5 rule for fabric (4674) -> 6; prefix removed after tab (4863)
    assert h.materialstr == "SUB\tF01-06\tBOCFAB-X\tD\t\r\n"
    assert h.v.arrayList39 == [True] and h.v.arrayList42 == [True]
    # component contains BOCFAB -> no dependent option (4942) ; arrayList79 == [-1]
    assert h.added[0][4] is False and h.added[0][6] == "" and h.added[0][9] == [-1]


def test_second_option_on_same_item_advances_position():
    ms = "SUB\t[opt5_1]\tC1\tD\t\r\nSUB\t[opt6_1]\tC2\tD\t\r\n"
    h = super_harness(ms, lookup_script())
    h.featlen = 2
    h.p05_item_row_and_renumber()
    # 4744-4820: second placeholder differs -> pos = 1 + prevfeatlen(2) = 3 ; length from cache = 2
    assert "SUB\tF01-02\tC1\t" in h.materialstr and "SUB\tF03-02\tC2\t" in h.materialstr


def test_knoll_and_9bocfab_branch():
    ms = "9-ITEM\tFEAT01\t9-BOCFAB[x]-Q\tD\t\r\n"
    h = super_harness(ms, lookup_script(), _catalogueId=649)
    h.p05_item_row_and_renumber()
    # 4973-4983: Knoll catalogue -> 8512 ; feature2 = text128
    assert h.added[0][6] == "FEAT01" and h.added[0][9] == [8512] and h.added[0][4] is False
    h = super_harness(ms, lookup_script(), _catalogueId=1)
    h.p05_item_row_and_renumber()
    assert h.added[0][9] == [8]


def test_9F_component_calls_update_child_length():
    ms = "9-ITEM\tF01-02\t9-F01-X\tD\t\r\n"   # text129[5] == "-" -> flag18 True; startswith 9-F -> first cond false
    h = super_harness(ms, lookup_script())
    h.p05_item_row_and_renumber()
    assert h.child_calls == [("9-ITEM", "F01-02", False)]               # 4969-4972
    assert h.added[0][4] is False and h.added[0][9] == [-1] and h.added[0][6] == ""


def test_malformed_feature_text_raises():
    h = super_harness("9-ITEM\tFEAT01\t9-FABC-Q\tD\t\r\n", lookup_script())
    with pytest.raises(LegacyFormatError):     # 4955: int.Parse("EA")
        h.p05_item_row_and_renumber()


def test_short_feature_adds_nothing():
    h = super_harness("SUB\tF\tCOMP\tDESC\t\r\n", {})
    h.p05_item_row_and_renumber()
    assert h.added == [] and h.materialstr == "SUB\tF\tCOMP\tDESC\t\r\n"   # len(feature) == 1 (4933)


def test_arraylist26_tags_removed():
    h = super_harness("SUB\t[opt5_1]\tCOMP\t<ZZ>DESC\t\r\n", lookup_script())
    h.v.arrayList26 = ["ZZ"]
    h.p05_item_row_and_renumber()
    assert "<ZZ>" not in h.materialstr                                   # 4885-4889


def test_not_run_when_formatcsi_or_flag4_or_superproductsonly():
    for kw in ({"_formatCSI": True}, {"_superProductsOnly": True}):
        h = super_harness("SUB\t[opt5_1]\tCOMP\tD\t\r\n", {}, **kw)
        h.p05_item_row_and_renumber()
        assert h.db.calls == [] and h.materialstr == "SUB\t[opt5_1]\tCOMP\tD\t\r\n"
    h = super_harness("SUB\t[opt5_1]\tCOMP\tD\t\r\n", {})
    h.v.flag4 = True
    h.p05_item_row_and_renumber()
    assert h.db.calls == []
    assert h.v.text5 == "no"                    # 4201: IsSuperProduct && !flag4


def test_no_candidate_options_skips_query20():
    # no candidate option ids: num101 = 0 is not < Count (4633) -> length stays from the "|" scan (2 here)
    h = super_harness("SUB\t[opt5_1]\tC\tD\t\r\n", {Q18: [{"FeaturePositionString": ""}]})
    h.p05_item_row_and_renumber()
    assert h.materialstr.startswith("SUB\tF01-02\t")
    assert q20_calls(h) == []


def test_bad_feature_position_string_raises():
    h = super_harness("SUB\t[opt5_1]\tC\tD\t\r\n", {Q18: [{"FeaturePositionString": "|x|"}]})
    with pytest.raises(LegacyFormatError):     # 4599/4601
        h.p05_item_row_and_renumber()
