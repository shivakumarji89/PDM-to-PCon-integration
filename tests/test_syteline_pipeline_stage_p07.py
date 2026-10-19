"""Tests for stage P7 (ExportThread.cs 5427-5745). All fixtures are synthetic; expectations derived from the C#.

Row layout of the _syteline row (5707): field 3 status flag, 4 reason, 24 M/P type, 30 brand, 34 slots.
Note (5451): a row is plan-flag "no" (type P, no brand, no slots) whenever it is neither fab nor dependent option.
"""
from __future__ import annotations

import pytest

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.netsem import LegacyFormatError, LegacyRangeError
from services.syteline_export.pipeline.run_base import ExportRunBase
from services.syteline_export.pipeline.stage_p07_converted_rows import P07Mixin


class H(P07Mixin, ExportRunBase):
    # helpers owned by other modules are stubbed
    def get_short_product_code(self, prodcode, rootproduct):
        return "XX"

    def is_integer(self, value):  # ExportThread.cs:949
        return value != "" and all(c in "0123456789-" for c in value)

    @staticmethod
    def log_message(msg, append=True):
        return

    def write_data(self, w, data, is_item):
        self.written.append((w, data, is_item))

    def format_csi_data(self, *a):
        return "CSI\t" + "|".join(str(x) for x in a)


def make(items, script=None, **fields):
    h = H(ScriptedExportDb(script or {}))
    h.written = []
    h.materialsWritten = []
    for it in items:
        h._convertedList.append(it["item"])
        h._convertIsFab.append(it.get("fab", False))
        h._convertIsDepOpt.append(it.get("dep", False))
        h._convertHasSuperParent.append(it.get("sp", False))
        h._convertedDesc.append(it.get("desc", "d"))
        h._convertedOtherDesc.append(it.get("other", ""))
        h._convertStatus.append(it.get("status", 1))
        h._convertOptionId.append(it.get("optid", -1))
        h._convertFeatLen.append(it.get("featlen", 3))
        h._convertChildFeatLen.append(it.get("childlen", -1))
    v = h.v
    v.arrayList = []
    v.arrayList33, v.arrayList34 = [], []
    v.streamWriter4 = "W4"
    v.text3 = "en"
    v.text6 = "BOCFAB"
    v.prodcode = "PC"
    v.rootproduct = "RP"
    for k, val in fields.items():
        setattr(h, k, val)
    return h


def slots(h, i=0):
    return h.v.arrayList[i].split("\t")[34]


def test_plain_row_non_syteline_and_stage():  # 5716-5720
    h = make([{"item": "9-AB-03-X", "desc": "d1"}])
    assert h.p07_converted_rows() is None
    assert h.v.arrayList == ["9-AB-03-X\tno\td1\tA\t0\tZZ-ZZ\t\r\n"]
    assert h.threadStage == "29"


def test_syteline_row_layout_plan_no():  # 5451-5454, 5628-5634, 5707-5714
    h = make([{"item": "9-AB-03-X", "desc": "d"}], _syteline=True)
    h.p07_converted_rows()
    fields = ["9-AB-03-X", "no", "d", "A", "", "0", "0", "", "", "ZZ-ZZ", "0", "0", "yes", "35", "0", "0",
              "", "", "", "DEF", "1", "0", "EA", "", "P", "", "no", "", "", "", "", "0", "0", "", ""]
    assert h.v.arrayList[0] == "\t".join(fields) + "\t" * 5 + "\r\n"


def test_26c_malformed_throws():  # 5616 unguarded Substring: fewer than 3 chars before "-05-"
    h = make([{"item": "A-05-"}])
    with pytest.raises(LegacyRangeError):
        h.p07_converted_rows()
    assert h.threadStage == "26c"


def test_skip_double_dash_and_superproducts():  # 5442
    h = make([{"item": "A--B"}, {"item": "9-X-03-1"}, {"item": "8-Y-03-1"}], _superProductsOnly=True)
    h.p07_converted_rows()
    assert len(h.v.arrayList) == 1 and h.v.arrayList[0].startswith("8-Y-03-1\t")
    h2 = make([{"item": "9-X-03-1"}])
    h2.p07_converted_rows()
    assert len(h2.v.arrayList) == 1


def test_abort_and_millercad_skip():  # 5436
    h = make([{"item": "9-X-03-1"}], _abortThread=True)
    h.p07_converted_rows()
    assert h.v.arrayList == [] and h.threadStage == "29"
    h = make([{"item": "9-X-03-1"}], _millerCAD=True)
    h.p07_converted_rows()
    assert h.v.arrayList == []


def test_fab_26a_slots_and_feature_length():  # 5461-5511
    # text157="FAB[XX]-F"; Substring(+0,2)="10", Substring(+3,2)="02"; 12 -> F12; 7-2=5
    h = make([{"item": "9-FAB[XX]-F10-02-1", "fab": True}], _syteline=True, _catalogueId=1)
    h.p07_converted_rows()
    row = h.v.arrayList[0].split("\t")
    assert row[34] == "F12-05" and row[24] == "M" and row[30] == "BOC"


def test_fab_26a_knoll_com_and_clamp():  # 5496-5509
    item = "9-FAB[XX]-F10-04-1"
    h = make([{"item": item, "fab": True}], _syteline=True, _catalogueId=649, includesCOM=True)
    h.p07_converted_rows()
    assert slots(h) == "F14-04"  # knoll 10-4=6, then COM and num169==4 -> 4
    h = make([{"item": item, "fab": True}], _syteline=True, _catalogueId=649)
    h.p07_converted_rows()
    assert slots(h) == "F14-05"  # 6 clamped to 5
    h = make([{"item": item, "fab": True}], _syteline=True, _catalogueId=1)
    h.p07_converted_rows()
    assert slots(h) == "F14-03"  # 7-4
    h = make([{"item": item, "fab": True}], _syteline=True, _catalogueId=1, includesCOM=True)
    h.p07_converted_rows()
    assert slots(h) == "F14-04"


def test_fab_26a_har_fallback():  # 5466-5469, 5485-5492
    h = make([{"item": "9-2-HAR-F08-03-9", "fab": True}], _syteline=True, _catalogueId=1)
    h.p07_converted_rows()
    assert slots(h) == "F11-04"  # 8+3, 7-3


def test_fab_26a_non_integer_leaves_zero_and_short_throws():  # 5485-5492, 5474
    h = make([{"item": "9-FAB-Fxx-yy-1", "fab": True}], _syteline=True)
    h.p07_converted_rows()
    assert slots(h) == "F00-05"
    h = make([{"item": "9-FAB-F", "fab": True}])
    with pytest.raises(LegacyRangeError):
        h.p07_converted_rows()


def test_fab_26a_integer_with_dash_throws_on_parse():  # isInteger allows "-", int.Parse does not (5476)
    h = make([{"item": "9-FAB[XX]-F1-2-1", "fab": True}])
    with pytest.raises(LegacyFormatError):
        h.p07_converted_rows()


def test_depopt_26b_query_cached_and_parameterised():  # 5530-5555, 5556-5582
    # text154="ABCD-F10-02-X"; text158="ABCD-F10-02"; num171=4; 10+2 -> F12; DB length 3 -> 5 (length5Feats)
    script = {"SLFeatureLength": [{"SLFeatureLength": "3"}]}
    items = [{"item": "9-ABCD-F10-02-X", "dep": True, "optid": 5}, {"item": "9-ABCD-F10-02-Y", "dep": True, "optid": 5}]
    h = make(items, script, _syteline=True)
    h.p07_converted_rows()
    assert [r.split("\t")[34] for r in h.v.arrayList] == ["F12-05", "F12-05"]
    assert [r.split("\t")[24] for r in h.v.arrayList] == ["M", "M"]  # plan flag stays yes
    calls = h.db.calls
    assert len(calls) == 1 and calls[0][0] == "c2" and calls[0][2] == (5,) and "5" not in calls[0][1]
    assert h.v.arrayList33 == [3] and h.v.arrayList34 == [5]


def test_depopt_26b_flatten_override_and_m_c_rule():  # 5548-5551, 5578-5581
    script = {"SLFeatureLength": [{"SLFeatureLength": "3"}]}
    h = make([{"item": "9-ABCD-F10-02-X", "dep": True, "optid": 8512}], script, _syteline=True,
             _flattenFabrics=True, _length5Feats=False)
    h.p07_converted_rows()
    assert h.v.arrayList33 == [8] and slots(h) == "F12-08"
    script = {"SLFeatureLength": [{"SLFeatureLength": "4"}]}
    h = make([{"item": "9-ABCD-F10-02-m-X", "dep": True, "optid": 5}], script, _syteline=True, _length5Feats=False)
    h.p07_converted_rows()
    assert slots(h) == "F12-03"  # "-m" present, non-Knoll -> 3
    h = make([{"item": "9-ABCD-F10-02-m-X", "dep": True, "optid": 5}], script, _syteline=True,
             _length5Feats=False, _catalogueId=649)
    h.p07_converted_rows()
    assert slots(h) == "F12-04"


def test_depopt_26b_child_len_and_featlen_without_option():  # 5563-5571
    h = make([{"item": "9-ABCD-F10-02-X", "dep": True, "optid": -1, "childlen": 4, "featlen": 2}],
             _syteline=True, _length5Feats=False)
    h.p07_converted_rows()
    assert slots(h) == "F12-04"
    h = make([{"item": "9-ABCD-F10-02-X", "dep": True, "optid": -1, "featlen": 2}], _syteline=True)
    h.p07_converted_rows()
    assert slots(h) == "F12-02"
    assert h.db.calls == []


def test_depopt_26b_brace_strip_and_parse_throw():  # 5518-5521, 5558
    h = make([{"item": "9-AB{x}CD-F10-02-X", "dep": True, "optid": -1, "featlen": 2}], _syteline=True)
    h.p07_converted_rows()
    assert slots(h) == "F12-02"
    h = make([{"item": "9-ABCD-Fxx-02-X", "dep": True, "optid": -1}])
    with pytest.raises(LegacyFormatError):
        h.p07_converted_rows()


def test_depopt_26b_text6_prefix_removed():  # 5627 (num171 == -1 keeps text158 as is)
    h = make([{"item": "9-ZZ1-A-X", "dep": True}], _syteline=True)
    h.v.text6 = "ZZ1"
    h.p07_converted_rows()
    assert slots(h) == "A"


def test_depopt_26b_slots_from_written_materials():  # 5586-5609 (uniqueComponents False)
    item = "9-ABCD-F10-02-X"
    mk = lambda mats, **kw: make([{"item": item, "dep": True, "optid": -1, "featlen": 2}], _syteline=True, **kw)
    h = mk(None)
    h.materialsWritten = [item + "\tF12-05\tx"]
    h.p07_converted_rows()
    assert h.v.arrayList[0].endswith("\tF12-05\t" + "\t" * 5 + "\r\n")
    h = mk(None)
    h.materialsWritten = [item + "\tF12-05\tx", item + "\tF14-04\ty", item + "\tF12-05\tz"]
    h.p07_converted_rows()
    assert slots(h) == "F12-05"  # first split field; check the whole value below
    assert h.v.arrayList[0].split("\t")[34:36] == ["F12-05", "F14-04"]


def test_depopt_26b_unique_components_prefix():  # 5589-5596
    item = "9-ABCD-F10-02-X"
    h = make([{"item": item, "dep": True, "optid": -1, "featlen": 2}], _syteline=True, _uniqueComponents=True)
    # text162 = "ABCD-"; text163 = item + "\t" + "ABCD-" + "F"
    h.materialsWritten = [item + "\tABCD-F07-01\tx", item + "\tF99-99\tx"]
    h.p07_converted_rows()
    # second line lacks the "ABCD-" so is ignored; text161 -> "F07-01\tx..." -> text164 "F07-01"
    assert h.v.arrayList[0].split("\t")[34] == "F07-01"


def test_depopt_26b_no_tab_throws():  # 5603 unguarded Substring(0, -1)
    item = "9-ABCD-F10-02-X"
    h = make([{"item": item, "dep": True, "optid": -1, "featlen": 2}])
    h.materialsWritten = [item + "\tF12-05"]
    with pytest.raises(LegacyRangeError):
        h.p07_converted_rows()


def test_bocfab_of_har_two_slots():  # 5638-5648
    h = make([{"item": "9-BOCFAB-OF2-HAR-F02-02-1", "dep": True, "featlen": 4}], _syteline=True, _length5Feats=False)
    h.p07_converted_rows()
    assert h.v.arrayList[0].split("\t")[34:36] == ["F04-04", "F08-03"]
    h = make([{"item": "9-BOCFAB-OF2-HAR-F05-05-1", "dep": True, "featlen": 4}], _syteline=True, _length5Feats=False)
    h.p07_converted_rows()
    assert h.v.arrayList[0].split("\t")[34:36] == ["F10-04", "F14-03"]


def test_stage27_bocfab_fallback():  # 5651-5682
    # type P (plan no), text155 "" -> after "-F": "04-03-x" -> 4+3=7 -> F07, 7-3=4
    h = make([{"item": "9-BOCFAB-F04-03-x"}], _syteline=True)
    h.p07_converted_rows()
    assert slots(h) == "F07-04"
    for kw, base in [({"includesCOM": True}, 8), ({"_catalogueId": 649}, 10),
                     ({"_catalogueId": 649, "_flattenFabrics": True}, 8)]:
        h = make([{"item": "9-BOCFAB-F04-03-x"}], _syteline=True, **kw)
        h.p07_converted_rows()
        assert slots(h) == "F07-%02d" % (base - 3)
    h = make([{"item": "9-BOCFAB-Fxx-03-x"}], _syteline=True)
    h.p07_converted_rows()
    assert slots(h) == ""
    h = make([{"item": "9-BOCFAB-F04-99-x"}], _syteline=True, _catalogueId=1)
    h.p07_converted_rows()
    assert slots(h) == "F103--92"  # 4+99, 7-99 formatted "00" keeps the sign


def test_status_map():  # 5688-5703
    for st, flag, reason in [(1, "A", ""), (0, "O", "URL"), (2, "O", "OBS"), (3, "O", "ON HOLD"), (7, "O", ""),
                             ("2", "O", "OBS")]:
        h = make([{"item": "9-AB-03-X", "status": st}], _syteline=True)
        h.p07_converted_rows()
        f = h.v.arrayList[0].split("\t")
        assert (f[3], f[4]) == (flag, reason)


def test_status_unparsable_throws():  # 5691 int.Parse
    h = make([{"item": "9-AB-03-X", "status": "zz"}])
    with pytest.raises(LegacyFormatError):
        h.p07_converted_rows()


def test_format_csi_replaces_row():  # 5721-5724
    h = make([{"item": "9-AB-03-X", "desc": "dd", "status": 3}], _formatCSI=True, _syteline=True)
    h.p07_converted_rows()
    assert h.v.arrayList == ["CSI\t9-AB-03-X|no|dd|O|ON HOLD|ZZ-ZZ|0.0|0.0|EA||P|"]


def test_csi_output_without_tab_throws():  # 5738 Substring(0, IndexOf("\t")) evaluated as logMessage argument
    h = make([{"item": "9-AB-03-X"}], _formatCSI=True)
    h.format_csi_data = lambda *a: "no-tab-here"
    with pytest.raises(LegacyRangeError):
        h.p07_converted_rows()


def test_flatten_fab_f_rename():  # 5725-5736
    # text168="9-FAB-F12-02"; LastIndexOf("-")=9 > 5 -> "9-FAB" + "-02"
    h = make([{"item": "9-FAB-F12-02", "fab": True}], _flattenFabrics=True, _catalogueId=1)
    h.p07_converted_rows()
    assert h.v.arrayList[0].startswith("9-FAB-02\tno\t")
    h = make([{"item": "9-FAB-F"}], _flattenFabrics=True)  # last "-" at 5 -> unchanged
    h.p07_converted_rows()
    assert h.v.arrayList[0].startswith("9-FAB-F\t")


def test_other_description_written_when_languages_differ():  # 5740-5743
    h = make([{"item": "9-AB-03-X", "other": "fr|x"}], _languageId=1, _otherlanguageId=2)
    h.p07_converted_rows()
    assert h.written == [("W4", "en\t9-AB-03-X\tfr|x\r\n", False)]
    h = make([{"item": "9-AB-03-X", "other": "fr|x"}], _languageId=1, _otherlanguageId=1)
    h.p07_converted_rows()
    assert h.written == []
    h = make([{"item": "9-AB-03-X", "other": ""}], _languageId=1, _otherlanguageId=2)
    h.p07_converted_rows()
    assert h.written == []
