"""Tests for stage_p09_patches (ExportThread.cs 6326-6779). All fixtures are synthetic.

Expected strings are derived from the C# rewrite rules (line numbers cited), not from running the port.
"""
import pytest

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.netsem import LegacyRangeError
from services.syteline_export.pipeline.run_base import ExportRunBase
from services.syteline_export.pipeline.stage_p09_patches import P09Mixin


class H(P09Mixin, ExportRunBase):
    parent_calls: list

    def get_parent_start_pos(self, prefix, suffix, reverse, parentlength, substitutedoptcode):
        # stand-in for ExportThread.getParentStartPos (another range): scripted result
        self.parent_calls.append((prefix, suffix, reverse))
        return self.parent_result(reverse, suffix)


def make(rows=(), mats=(), a93=(), text5="no", text6="T", **fields):
    h = H(ScriptedExportDb({}))
    h.parent_calls = []
    h.parent_result = lambda reverse, suffix: (3, 0, suffix)
    h.v.arrayList = list(rows)
    h.v.arrayList2 = list(mats)
    h.v.arrayList93 = list(a93)
    h.v.text5 = text5
    h.v.text6 = text6
    for k, val in fields.items():
        setattr(h, k, val)
    return h


# ---------------------------------------------------------------- stage 35
def test_unique_components_prefix_stripping_items():
    # 6333-6346: text222 "ABC"; "\tABC-" removed
    h = make(rows=["ABC\tABC-foo\tbar"], _uniqueComponents=True)
    assert h.p09_item_material_patches() is None
    assert h.v.arrayList == ["ABC\tfoo\tbar"]


def test_unique_components_9_prefix_stripped_to_first_dash():
    # 6335-6341: "9-X1-Y" -> "X1-Y" -> "X1"
    h = make(rows=["9-X1-Y\tX1-a"], _uniqueComponents=True)
    h.p09_item_material_patches()
    assert h.v.arrayList == ["9-X1-Y\ta"]


def test_plc_phantoms_bracket_removed_only_when_flag_set():
    # 6347-6352
    h = make(rows=["A\t[PLC1]-B"], _uniqueComponents=True, _plcPhantoms=True)
    h.p09_item_material_patches()
    assert h.v.arrayList == ["A\tB"]
    h = make(rows=["A\t[PLC1]-B"], _uniqueComponents=True, _plcPhantoms=False)
    h.p09_item_material_patches()
    assert h.v.arrayList == ["A\t[PLC1]-B"]


def test_flc_item_rewrite():
    # 6353-6356
    row = "9-FLC-Q\t0\t0\t\tF07-03\tF10-03"
    h = make(rows=[row], _uniqueComponents=True)
    h.p09_item_material_patches()
    assert h.v.arrayList == ["9-FLC-Q\t0\t0\t\tF04-03\tF10-03"]


def test_flc_material_rewrite_and_material_prefix_strip():
    # 6382-6385 and 6372-6375
    h = make(mats=["9-FLC-F01-03-X\tF07-03", "M1\tM1-z"], _uniqueComponents=True)
    h.p09_item_material_patches()
    assert h.v.arrayList2 == ["9-FLC-F04-03-X\tF07-03", "M1\tz"]


def test_flc_material_rewrite_requires_all_three_conditions():
    h = make(mats=["9-FLC-F01-03-X\tF08-03"], _uniqueComponents=True)
    h.p09_item_material_patches()
    assert h.v.arrayList2 == ["9-FLC-F01-03-X\tF08-03"]


def test_plc_material_bracket():
    h = make(mats=["A\t[P]-B"], _uniqueComponents=True, _plcPhantoms=True)
    h.p09_item_material_patches()
    assert h.v.arrayList2 == ["A\tB"]


def test_unique_components_off_leaves_rows_but_cqnd58_still_applies():
    # 6397-6406 run regardless of _uniqueComponents
    h = make(rows=["ABC\tABC-foo", "CQND58\tx\tF01-03\tF10-07", "XQND58\tF01-03\tF10-07"],
             mats=["ABC\tABC-foo"])
    h.p09_item_material_patches()
    assert h.v.arrayList == ["ABC\tABC-foo", "CQND58\tx\tF01-03\tF07-03\tF10-07", "XQND58\tF01-03\tF10-07"]
    assert h.v.arrayList2 == ["ABC\tABC-foo"]


def test_row_without_tab_throws_when_unique_components():
    # 6334: Substring(0, -1)
    h = make(rows=["NOTAB"], _uniqueComponents=True)
    with pytest.raises(LegacyRangeError):
        h.p09_item_material_patches()


def test_plc_bracket_without_close_throws():
    # 6350: Substring(0, IndexOf("]") == -1)
    h = make(rows=["A\t[PLC"], _uniqueComponents=True, _plcPhantoms=True)
    with pytest.raises(LegacyRangeError):
        h.p09_item_material_patches()


def test_flag24_dead_block_never_applies():
    # 6419 forces flag24 = false: BOCFAB / CRB rewrites must not happen even when MG1 rows exist
    h = make(rows=["MG1\tx", "9-BOCFAB-ZB3\tBeck ZB3-ZB3\t"], mats=["x-CRB\t-ZB3\tZB3\t"])
    h.p09_item_material_patches()
    assert h.v.arrayList == ["MG1\tx", "9-BOCFAB-ZB3\tBeck ZB3-ZB3\t"]
    assert h.v.arrayList2 == ["x-CRB\t-ZB3\tZB3\t"]


# ---------------------------------------------------------------- stages 36-38
ITEM_TAIL = (
    "A\t" "\t0\t0\t" "\t" "\tZZ-ZZ\t"
    "0\t0\tyes\t35\t0\t0\t" "\t" "\t" "\t"
    "DEF\t1\t0\tEA\t" "\tP\t" "\t"
    "no\t" "\t" "\t" "\t" "\t0\t0\t" "\t"
    + "\t" * 20 + "\t\t\t"
)


def test_fabric_not_generated_when_text5_not_yes_or_csi():
    h = make(text5="no")
    h.skippedFabricColours = ["X|ABCD"]
    h.p09_item_material_patches()
    assert h.v.arrayList2 == [] and h.parent_calls == []
    h = make(text5="yes", _formatCSI=True)
    h.skippedFabricColours = ["X|ABCD"]
    h.p09_item_material_patches()
    assert h.v.arrayList2 == [] and h.parent_calls == []


def test_fabric_basic_generation():
    h = make(text5="yes", text6="T")
    h.skippedFabricColours = ["X|ABCD", "nopipe"]
    labels = []
    h._status_callback = labels.append
    h.p09_item_material_patches()
    # 6572: parent "AB"; 6606: F03-02 (stub pos 3, num260 2); 6695-6704: F05-05; 6719: "CD"; 6720-6722
    assert h.parent_calls == [("9-T", "AB", False)]
    mat = "9-T-F03-02-AB\tF05-05\t9-FAB-ABCD\tCD\t0\t1\t0\t2\t\t\t10"
    assert h.v.arrayList2 == [mat]
    assert h._additionalMaterialsWritten == [mat]
    item = "9-FAB-ABCD\tno\tABCD|ABCD\t" + ITEM_TAIL
    assert h.v.arrayList == [item] and h._additionalItemsWritten == [item]
    assert h.allSPFabricColours == ["9-T-F03-02-AB\t"]
    assert h.allSPFabricColourCodes == [["ABCD"]] and h.allSPFabricColourSequences == [2]
    assert labels == ["fabric: 1 of 2"]


def test_fabric_knoll_width_ten_and_colon_tilde_parsing():
    # 6696-6699: Knoll catalogue -> num259 = 10 -> width 10-2 = 08 ; 6526-6533 colon/tilde
    h = make(text5="yes", _catalogueId=649)
    h.skippedFabricColours = ["X|ABCD:Red~9"]
    h.p09_item_material_patches()
    assert h.v.arrayList2 == ["9-T-F03-02-AB\tF05-08\t9-FAB-ABCD\tCD\t0\t1\t0\t2\t\t\t10"]
    assert h.v.arrayList == ["9-FAB-ABCD\tno\tABCD|Red\t" + ITEM_TAIL]


def test_fabric_width_eight_when_parent_length_four():
    # 6700-6703: num260 == 4 -> num259 = 8 ; parentlength 4 raises num260
    h = make(text5="yes")
    h.skippedFabricColours = ["X|ABCDEF"]
    h.parent_result = lambda reverse, suffix: (3, 4, suffix)
    h.p09_item_material_patches()
    # parent "ABCD" (len 4 from "ABCDEF"[0:-2]); num269 = 4 -> num260 4; featpos "F03-04"; F07-04
    assert h.v.arrayList2 == ["9-T-F03-04-ABCD\tF07-04\t9-FAB-ABCDEF\tEF\t0\t1\t0\t2\t\t\t10"]


def test_fabric_cm01_excluded():
    # 6723/6762-6764
    h = make(text5="yes")
    h.skippedFabricColours = ["X|CM01"]
    h.p09_item_material_patches()
    assert h.v.arrayList2 == [] and h.v.arrayList == [] and h._additionalMaterialsWritten == []


def test_fabric_cm0100_parent_length_three():
    # 6582-6585: parent CM0100 -> num269 = 3
    h = make(text5="yes")
    h.skippedFabricColours = ["X|CM0100", "X|CM0100AB"]
    h.p09_item_material_patches()
    # entry 1 (parent "CM01", len 4) raises num260 to 4, which persists (6512, 6586-6589); entry 2 has
    # parent CM0100 (num269 = 3 < 4): featpos F03-04, num260 == 4 -> num259 = 8 -> F07-04 (6700-6704)
    assert h.parent_calls[-1] == ("9-T", "CM0100", False)
    assert "9-T-F03-04-CM0100\tF07-04\t9-FAB-CM0100AB\tAB\t0\t1\t0\t2\t\t\t10" in h.v.arrayList2


def test_fabric_two_parents_second_pass_reverse_same_key_no_duplicate():
    # 6563-6566: parents AB and ABC -> text236 "ABC", num264 2; pass 2 reverse=True (6591)
    h = make(text5="yes")
    h.skippedFabricColours = ["X|AB", "X|ABC", "X|ABCD"]
    h.p09_item_material_patches()
    assert h.parent_calls == [("9-T", "ABC", False), ("9-T", "ABC", True)]
    # same key twice: 2nd pass hits 6651 branch, code already present -> sequence untouched, row deduped
    assert h.v.arrayList2 == ["9-T-F03-03-ABC\tF06-04\t9-FAB-ABCD\tD\t0\t1\t0\t2\t\t\t10"]
    assert h.allSPFabricColourSequences == [2]


def test_fabric_existing_key_new_code_increments_sequence():
    # 6625-6648: key exists, code absent -> append code, sequence+1, text231 = "3"
    h = make(text5="yes")
    h.skippedFabricColours = ["X|ABCD"]
    h.allSPFabricColours = ["9-T-F03-02-AB\t"]
    h.allSPFabricColourCodes = [["ZZZZ"]]
    h.allSPFabricColourSequences = [2]
    h.p09_item_material_patches()
    assert h.allSPFabricColourCodes == [["ZZZZ", "ABCD"]] and h.allSPFabricColourSequences == [3]
    assert h.v.arrayList2 == ["9-T-F03-02-AB\tF05-05\t9-FAB-ABCD\tCD\t0\t1\t0\t3\t\t\t10"]


def test_fabric_existing_key_known_code_keeps_sequence_two():
    h = make(text5="yes")
    h.skippedFabricColours = ["X|ABCD"]
    h.allSPFabricColours = ["9-T-F03-02-AB\t"]
    h.allSPFabricColourCodes = [["ABCD"]]
    h.allSPFabricColourSequences = [7]
    h.p09_item_material_patches()
    assert h.allSPFabricColourSequences == [7]
    assert h.v.arrayList2[0].endswith("\t0\t1\t0\t2\t\t\t10")


def test_fabric_sequence_taken_from_allFabricColours():
    # 6710-6714
    h = make(text5="yes")
    h.skippedFabricColours = ["X|ABCD"]
    h.allFabricColours = ["9-FAB-ABCD"]
    h.allFabricColourSequences = [5]
    h.p09_item_material_patches()
    assert h.v.arrayList2 == ["9-T-F03-02-AB\tF05-05\t9-FAB-ABCD\tCD\t0\t1\t0\t5\t\t\t10"]


def test_fabric_item_not_added_when_already_on_item_tab_or_written():
    # 6745-6760
    h = make(text5="yes", a93=["other\tx", "9-FAB-ABCD\tfoo"])
    h.skippedFabricColours = ["X|ABCD"]
    h.p09_item_material_patches()
    assert len(h.v.arrayList2) == 1 and h.v.arrayList == []
    h = make(text5="yes")
    h.skippedFabricColours = ["X|ABCD"]
    pre = "9-FAB-ABCD\tno\tABCD|ABCD\t" + ITEM_TAIL
    h._additionalItemsWritten = [pre]
    h.p09_item_material_patches()
    assert h.v.arrayList == []


def test_fabric_material_already_written_not_duplicated():
    h = make(text5="yes")
    h.skippedFabricColours = ["X|ABCD"]
    mat = "9-T-F03-02-AB\tF05-05\t9-FAB-ABCD\tCD\t0\t1\t0\t2\t\t\t10"
    h._additionalMaterialsWritten = [mat]
    h.p09_item_material_patches()
    assert h.v.arrayList2 == []


def test_fabric_bad_substituted_code_throws():
    # 6719: Substring(text236.Length) beyond text234
    h = make(text5="yes")
    h.skippedFabricColours = ["X|ABCD"]
    h.parent_result = lambda reverse, suffix: (3, 0, "ABCDEFG")
    with pytest.raises(LegacyRangeError):
        h.p09_item_material_patches()


def test_no_sql_issued_and_stage_set():
    h = make(text5="yes", a93=["z"])
    h.skippedFabricColours = ["X|ABCD"]
    h.p09_item_material_patches()
    assert h.db.calls == []
    assert h.threadStage.startswith("38.0.1-1")
