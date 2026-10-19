"""Tests for stage_p08_postprocess (ExportThread.cs 5749-6325).

All fixtures are SYNTHETIC. Expected values are derived by hand from the C# (line numbers cited).
"""
import pytest

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.netsem import LegacyFormatError, LegacyRangeError
from services.syteline_export.pipeline.run_base import ExportRunBase
from services.syteline_export.pipeline.stage_p08_postprocess import P08Mixin

DEP_SQL = "FROM OptionValue optval WITH (NOLOCK)"
TAB_DEF_P = "DEF\t1\t0\tEA\t\tP\t\tno\t\t\t\t\t0\t0\t\t\t"  # text195 (6054)
TAB_DEF_M = "DEF\t1\t0\tEA\t\tM\t\tno\t\t\t\tBOC\t0\t0\t\t"  # text197 prefix (6065)


class H(P08Mixin, ExportRunBase):
    pass


def make(materials, arrayList=(), arrayList2=(), text6="ZZZ", script=None, **attrs):
    h = H(ScriptedExportDb(script or {}))
    h._syteline = True
    h._formatCSI = False
    h._catalogueId = 1
    h.materialsWritten = list(materials)
    h.v.text6 = text6
    h.v.arrayList = list(arrayList)
    h.v.arrayList2 = list(arrayList2)
    for k, val in attrs.items():
        setattr(h, k, val)
    return h


def test_gate_formatcsi_or_not_syteline_skips_everything():  # 5749
    for csi, sy in ((True, True), (False, False)):
        h = make(["P\t1\tc\td\te\tf\tg\th"], arrayList2=["keep"], _formatCSI=csi, _syteline=sy)
        assert h.p08_postprocess() is None
        assert h.v.arrayList2 == ["keep"]
        assert h.v.arrayList93 == []
        assert h.db.calls == []


def test_stage33_34_plain_rows_trim_dedupe_and_axox_skip():
    # AX..OX row is skipped in the 30c loop (5787-5794) but still flows through stage 33/34.
    rows = ["P\t1\tc\td\te\tf\tg\th", "AXOX1\t1\tc\td\te\tf\tg\th"]
    h = make(rows, arrayList2=["stale"])
    h.p08_postprocess()
    # 94 empty -> 102 := materialsWritten (6095-6102); stage 34 replaces arrayList2 (6157)
    assert h.v.arrayList2 == rows
    assert h._additionalMaterialsWritten == rows
    assert h.v.arrayList == [] and h._additionalItemsWritten == []  # arrayList93 empty -> no items
    assert h.db.calls == []


def test_stage33_clone_appends_while_cloning_and_trims_tabs_crlf():
    # Fabric lookup sets arrayList94 non-empty (cloned from arrayList2 at 5846-5853), then stage 33
    # appends the trimmed copy of every element (6103-6113) to the same list (6111).
    h = make(
        ["P\t1\tc\td\te\tf\tg\th"],
        arrayList2=["X\t"],
    )
    # force arrayList94 population through the 32.1 clone: needs a fabric match, so do it directly instead
    h.skippedFabricColours = []
    h.p08_postprocess()
    # arrayList94 stayed empty (no fabric path) -> 102 from materialsWritten; check trimming:
    h2 = make(["P\t1\tc\td\te\tf\tg\th\t\r\n"])
    h2.p08_postprocess()
    assert h2.v.arrayList2 == ["P\t1\tc\td\te\tf\tg\th"]  # \r\n removed, '\t' trimmed (6106-6107)


def _dependent_setup():
    # row0 looks up "RED"; row1 ("BLU") finds row0's list containing "BLU#" (5800-5818)
    rows = [
        "P1\t1\t9-FAB-F01-02-RED\t07\t1\t1\t0\t0",
        "P2\t1\t9-FAB-F02-02-BLU\t07\t1\t1\t0\t0",
    ]
    m = "9-FAB-F01-02-RED\t1\t9-FAB-F02-02-BLU\t07\t1\t1\t0\t" + "P2\t1\t9-FAB-F02-02-BLU\t07\t1\t1\t0\t0"
    item = "9-FAB-F01-02-RED\tBOCX\tF02-02\t\tend"
    script = {DEP_SQL: lambda c, s, p: [{"OrderCodeValue": "BLU#"}] if p == ("RED#",) else []}
    return rows, m, item, script


def test_dependent_fabric_lookup_remap_and_clones():
    rows, m, item, script = _dependent_setup()
    h = make(rows, arrayList=[item], arrayList2=[m], text6="FAB", script=script)
    h.p08_postprocess()
    # 30e: queried once (row1 matched from the cache), value bound not concatenated (5822)
    assert [(c[0], c[2]) for c in h.db.calls] == [("c1", ("RED#",))]
    assert "RED" not in h.db.calls[0][1] and "?" in h.db.calls[0][1]
    # 30f (5867-5883): featpos = "F02-02-BLU"; BOC text gets featpos inserted after last "F" token
    value8 = "9-FAB-F01-02-RED\tBOCX\tF02-02\tF02-02-BLU\tend"
    # 5900: arrayList94 element rewritten
    mod = ("9-FAB-F01-02-RED\t1\t9-FAB-F02-02-BLU\t07\t1\t1\t0\t"
           "9-FAB-F01-02-RED\t1\t9-FAB-F02-02-BLU\t07\t1\t1\t0\t1")
    # 6139-6154: arrayList93 element appended to arrayList (6150); 6155-6169 arrayList2 rebuilt
    assert h.v.arrayList93 == [value8]
    assert h.v.arrayList == [item, value8]
    assert h._additionalItemsWritten == [value8]
    # arrayList94 = [mod]; stage 33 appends trimmed copy (same string) -> [mod, mod]; stage 34 dedupes
    assert h.v.arrayList2 == [mod]


def test_stage34_dedupes_against_already_written_and_rebinds_arraylist2():
    rows, m, item, script = _dependent_setup()
    h = make(rows, arrayList=[item], arrayList2=[m], text6="FAB", script=script)
    old = h.v.arrayList2
    h._additionalItemsWritten = ["9-FAB-F01-02-RED\tBOCX\tF02-02\tF02-02-BLU\tend"]
    h._additionalMaterialsWritten = ["already"]
    h.p08_postprocess()
    assert h.v.arrayList == [item]  # 6146: already written -> not appended
    assert h.v.arrayList2 is not old  # `arrayList2 = new ArrayList()` (6157)


def test_dependent_lookup_empty_result_caches_and_continues_to_stage31():
    rows = ["P1\t1\t9-FAB-F01-02-RED\t07\t1\t1\t0\t0"]
    h = make(rows, text6="FAB", script={DEP_SQL: []})
    h.p08_postprocess()
    assert len(h.db.calls) == 1  # 5831-5832 cached after the query
    assert h.v.arrayList2 == rows


def _stage32(item_has=("ITM",), skipped=("xx|RD",), arrayList=None, arrayList2=None):
    row = "P3\t1\t9-ITM-F01-02-RD\tRD\t1\t1\t0\t0"
    a2 = arrayList2 if arrayList2 is not None else [row + "\textra"]
    a = arrayList if arrayList is not None else [
        "9-ITM-F01-02-RD\t",
        "9-ITM-F01-02-RD\t" + TAB_DEF_P,
    ]
    h = make([row], arrayList=a, arrayList2=a2, text6="FAB")
    h.skippedFabricColours = list(skipped)
    h.itemHasFabrics = list(item_has)
    return h, row


def test_stage32_skipped_fabric_remap_to_F01_code_and_feature_def():
    h, row = _stage32()
    h.p08_postprocess()
    # 5975: text188 = "9-FAB-F01-" + "02" + "-RD" ; 5992 rewrite of the arrayList94 element
    new94 = "P3\t1\t9-FAB-F01-02-RD\tRD\t1\t1\t0\t0\textra"
    # text189 = "F01-02" -> 1+2 -> "F03-05" (6003-6009); 6080 replacement of the DEF-P row
    new93 = "9-FAB-F01-02-RD\t" + TAB_DEF_M + "F03-05\t"
    assert h.v.arrayList93 == ["9-ITM-F01-02-RD\t", new93]
    assert h.v.arrayList == ["9-ITM-F01-02-RD\t", "9-ITM-F01-02-RD\t" + TAB_DEF_P, "9-ITM-F01-02-RD\t", new93]
    assert h.v.arrayList2 == [new94]


def test_stage32_boc_branch_inserts_feature_and_continues():
    boc = "9-ITM-F01-02-RD\tBOCX\tF02-02\t\tend"
    h, row = _stage32(arrayList=[boc, "9-ITM-F01-02-RD\t"])
    h.p08_postprocess()
    # 6035-6050: text193 = "F02-02"; "F03-05" inserted
    assert h.v.arrayList93[0] == "9-ITM-F01-02-RD\tBOCX\tF02-02\tF03-05\tend"
    assert h.v.arrayList93[1] == "9-ITM-F01-02-RD\t"  # untouched (continue at 6050)


def test_stage32_itemHasFabrics_gate_blocks_remap():
    h, row = _stage32(item_has=())
    h.p08_postprocess()  # flag23 -> continue (5971)
    assert h.v.arrayList2 == [row + "\textra"]
    assert "9-FAB-F01-02-RD" not in "".join(h.v.arrayList2)


def test_stage32_non_one_count_and_missing_pipe_and_length_gate():
    # continue at 5913 / 5931 happens before arrayList94 is cloned -> stage 33 uses materialsWritten
    for sk in ("nopipe", "xx|LONGER"):
        h, row = _stage32(skipped=(sk,))
        h.p08_postprocess()
        assert h.v.arrayList2 == [row], sk
    # continue at 5953 happens after the clone from arrayList2 (5944-5951)
    h, row = _stage32(skipped=("xx|RD~2",))
    h.p08_postprocess()
    assert h.v.arrayList2 == [row + "\textra"]
    # ":" form is consumed (5925-5929) and text185 shortened: "RD:Q" -> RD
    h, row = _stage32(skipped=("xx|RD:Q",))
    h.p08_postprocess()
    assert "9-FAB-F01-02-RD" in h.v.arrayList2[0]


def test_stage32_bad_tilde_number_raises_format_error():
    h, _ = _stage32(skipped=("xx|RD~zz",))
    with pytest.raises(LegacyFormatError):  # int.Parse (5922)
        h.p08_postprocess()


def test_stage32_text189_bad_int_raises():
    h, row = _stage32()
    row2 = "P3\t1\t9-ITM-F01-02-RD\tZZ\t1\t1\t0\t0"
    h.materialsWritten = [row2]
    h.v.arrayList2 = [row2 + "\textra"]
    with pytest.raises(LegacyFormatError):
        h.p08_postprocess()


def test_malformed_material_row_raises_range_error():
    h = make(["no tabs here"])
    with pytest.raises(LegacyRangeError):  # Substring(0, -1) at 5764
        h.p08_postprocess()


def test_flatten_fabrics_stage_33_5():
    row = "P\t1\t9-FAB-F01-02-RED\t07\t1\t1\t0\t0"
    h = make([row], text6="ZZZ", _flattenFabrics=True)
    h.p08_postprocess()
    # 6121-6133: "9-FAB-F01-02-RED" -> "9-FAB" + "-RED"; both copies identical -> deduped at stage 34
    assert h.v.arrayList2 == ["P\t1\t9-FAB-RED\t07\t1\t1\t0\t0"]


def test_status_label_and_stage_markers():
    msgs = []
    h = make(["P\t1\tc\td\te\tf\tg\th"])
    h._status_callback = msgs.append
    h.p08_postprocess()
    assert msgs == ["matl: P\r\n(1 of 1)"]  # 5765
    assert h.threadStage == "34"


# ---------------------------------------------------------------- HRB (catalogue 229)
HRB_ROWS = [
    "OF1\tOF1-X\tQ\tw\t1\t1\t0",  # not HAR, nothing yet -> text206 (6258)
    "OF1\tOF1-HAR-F01-03\tCOMPA\tx\t5\t1\t0",  # A
    "OF1\tOF1-HAR-F02-05\tCOMPA2-HAR-F5-Q9\ty\t3\t1\t0",  # B
    "OF1\tbocfab-HAR-F08-03\tCOMPA3-HAR-F8-Q7\tz\t2\t0\t0\t\t\t10\t4",  # C
    "OF1\tOF1-HAR-F07-03\t9-BOCFAB-OF1-HAR-X\tx\t4\t1\t0",  # D
]


def test_hrb_branch_full():
    h = make(HRB_ROWS, arrayList2=["old"], _catalogueId=229)
    h.p08_postprocess()
    header = ("Parent Item\tFeature\tComponent\tOpt code\tInc. price\tMatl Qty\tScrap fact\tSeq\t"
              "Effect Date\tObs Date\tOper Num\tBackFlush")
    expected = [
        header,
        HRB_ROWS[0],  # inserted at index 1 (6269); split on '\r' leaves "\n" element
        "\n",
        "OF1\tF01-03\tCOMPA\tx\t0\t1\t0",  # A: 6238/6240/6251
        "OF1\tOF1-H-F02-05\tCOMPA2-H-F5-Q9\ty\t3\t1\t0",  # B, 6279
        "COMPA\tF08-03\tCOMPA3-H-F8-Q7\tz\t2\t1\t0\t\t\t10\t4",  # C: 6246/6248/6251
        "OF1\tF07-03\t9-OF1-HAR-X\tx\t0\t1\t0",  # D: 6239/6240/6252 (-BOCFAB- -> -)
        # 6283-6323: num234 starts at 1 (D); match OF1~ entries B (num236=0) and C (num236=1)
        "9-OF1-HAR-X\tF5\tCOMPA2-H-F5-Q9\tQ9\t4\t1\t0\t102\t\t\t10\t",
        # C entry has "3-HAR" not "2-HAR" -> -BOCFAB- is kept (6310)
        "9-BOCFAB-OF1-HAR-X\tF8\tCOMPA3-H-F8-Q7\tQ7\t4\t1\t0\t103\t\t\t10\t",
    ]
    assert h.threadStage == "HRB"
    assert h.v.arrayList2 == expected
    assert h.db.calls == []


def test_hrb_no_f01_rows_leaves_arraylist2_untouched():
    h = make(["OF1\tOF1-X\tQ\tw\t1\t1\t0"], arrayList2=["old"], _catalogueId=229)
    with pytest.raises(LegacyRangeError):  # Insert(1) on empty ArrayList (6269)
        h.p08_postprocess()


def test_hrb_without_har_rows_and_empty_materials():
    h = make([], arrayList2=["old"], _catalogueId=229)
    h.p08_postprocess()
    assert h.v.arrayList2 == ["old"]  # 104 empty -> not rebuilt (6273)


def test_hrb_price_branch_takes_second_when_first_not_greater():
    rows = [
        "OF1\tOF1-HAR-F01-03\tCOMPA\tx\t1\t1\t0",
        "OF1\tOF1-HAR-F02-05\tCOMPB-HAR-F5-Q9\ty\t3\t1\t0",
        "OF1\tOF1-HAR-F07-03\t9-BOCFAB-OF1-HAR-X\tx\t2\t1\t0",
    ]
    h = make(rows, _catalogueId=229)
    h.p08_postprocess()
    # num237 = 2 (D), num238 = 3 (B): not (2 > 3) -> uses num238 = "3" (6308)
    assert h.v.arrayList2[-1] == "9-BOCFAB-OF1-HAR-X\tF5\tCOMPB-H-F5-Q9\tQ9\t3\t1\t0\t102\t\t\t10\t"


def test_hrb_bad_price_raises_format_error():
    rows = [
        "OF1\tOF1-HAR-F01-03\tCOMPA\tx\t1\t1\t0",
        "OF1\tOF1-HAR-F02-05\tCOMPB-HAR-F5-Q9\ty\tnotnum\t1\t0",
        "OF1\tOF1-HAR-F07-03\t9-BOCFAB-OF1-HAR-X\tx\t2\t1\t0",
    ]
    h = make(rows, _catalogueId=229)
    with pytest.raises(LegacyFormatError):  # double.Parse (6306)
        h.p08_postprocess()


def test_catalogue_229_does_not_run_non_hrb_branch_and_vice_versa():
    # non-HAR row only: the 229 branch runs (Insert(1) on empty list throws); stage 34 never runs
    h = make(["P\t1\tc\td\te\tf\tg\th"], arrayList2=["old"], _catalogueId=229)
    with pytest.raises(LegacyRangeError):
        h.p08_postprocess()
    assert h.threadStage == "HRB"
    assert h._additionalMaterialsWritten == []
