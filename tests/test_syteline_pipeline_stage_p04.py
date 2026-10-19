"""Tests for stage_p04_feature_templates (ExportThread.cs 3587-4191). All fixtures are synthetic.

Expected values are derived from the C# (line numbers cited), not from running the port.
"""
import pytest

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.netsem import LegacyFormatError, LegacyRangeError
from services.syteline_export.pipeline.run_base import ExportRunBase
from services.syteline_export.pipeline.stage_p04_feature_templates import P04Mixin


class H(P04Mixin, ExportRunBase):
    """Harness with scripted stand-ins for helpers owned by other agents."""

    def parse_opt_code(self, code, a, b):
        return self.parse_result(code, a, b)

    def add_material_to_item_tab(self, *args):
        self.mat_calls.append(args)

    def add_fabric_colour(self, *args):
        self.fab_calls.append(args)


def make(parsed="X|AB", opt_id=100, fab=0, optcode="AB", featlen=2, parent="", script=None,
         item="ITEM1", sp=False, length5=True, **fields):
    """One option (index 0) unless lists are overridden afterwards."""
    h = H(ScriptedExportDb(script or {}))
    h.parse_result = lambda code, a, b: parsed
    h.mat_calls, h.fab_calls = [], []
    v = h.v
    v.sqlDataReader = {"Item": item, "IsSuperProduct": sp, "Product_Code": "PC-1_x"}
    v.num6, v.num7, v.num8 = 1, 0, -1
    v.text6, v.text19, v.flag2, v.flag4 = "BOCFAB", "", False, False
    v.arrayList45 = ["opt"]; v.arrayList18 = ["opt"]
    v.arrayList47 = [opt_id]; v.arrayList48 = [7]; v.arrayList49 = [fab]
    v.arrayList54 = [featlen]; v.arrayList55 = [optcode]; v.arrayList57 = [parent]
    v.arrayList59 = [False]; v.arrayList60 = [0]; v.arrayList61 = [[]]
    v.arrayList16 = []; v.arrayList46 = []; v.arrayList24 = []; v.arrayList25 = []
    v.arrayList35 = []; v.arrayList36 = []; v.arrayList37 = []
    v.arrayList3 = []; v.arrayList4 = []; v.arrayList5 = []; v.arrayList6 = []; v.arrayList7 = []
    v.arrayList63 = []; v.arrayList65 = []
    h._syteline = True
    h._length5Feats = length5
    for k, val in fields.items():
        setattr(h if k.startswith("_") or k in ("materialstr",) else v, k, val)
    return h


# ---- length5 rule, non-fabric (17.1b/17.2b/17.2c, C# 3792-3832) ---------------------------------------
@pytest.mark.parametrize("parsed,featlen,length5,expect,adv", [
    ("x|ABC", 2, True, "F01-05", 5),     # 3792: len>2 & length5 -> 05 (3804)
    ("x|AB C", 2, True, "F01-10", 10),   # 3796: space -> 10 (3798)
    ("x|AB", 2, True, "F01-02", 2),      # 3814-3823: num62 = 2
    ("x|AB", 3, True, "F01-05", 5),      # 3819: >2 & length5 -> 5
    ("x|AB", 3, False, "F01-03", 3),     # no length5: keeps 3
    ("x|ABC", 2, False, "F01-03", 3),    # 3815: num62==2 & len>2 -> len (3)
    ("x|ABCD", 2, False, "F01-04", 4),
    ("x|ABCD", 2, True, "F01-05", 5),    # 3792 branch (len>2 & length5)
])
def test_length5_matrix(parsed, featlen, length5, expect, adv):
    h = make(parsed=parsed, featlen=featlen, length5=length5)
    assert h.p04_feature_templates() is None
    assert h.v.arrayList25 == [expect]
    assert h.v.num6 == 1 + adv
    assert h.v.text19.endswith("-") and set(h.v.text19[:-1]) == {"X"}
    assert len(h.v.text19) == adv + 1
    assert h.v.arrayList24 == ["ITEM1|[opt1]"]
    assert h.v.num7 == 1 and h.v.num8 == 100


def test_position_prefix_two_digits_and_ten():
    h = make(parsed="x|ABC")
    h.v.num6 = 12   # 3622: >=10 -> no leading zero
    h.p04_feature_templates()
    assert h.v.arrayList25 == ["F12-05"] and h.v.num6 == 17


def test_non_fab_17_4_adds_slot_when_no_parent():
    h = make(parsed="x|ABC", parent="")
    h.p04_feature_templates()
    assert h.v.arrayList46 == ["F01-05"]        # 3887-3890


def test_non_fab_17_4_not_added_with_parent():
    h = make(parsed="x|ABC", parent="55")
    h.p04_feature_templates()
    assert h.v.arrayList46 == []                # 3887 false; 3892 branch needs parent=="" so unreachable


def test_17_4_super_product_branch_parses_bool_always():
    h = make(parsed="x|ABC", parent="5", sp="bogus")
    with pytest.raises(LegacyFormatError):      # 3887 bool.Parse is evaluated even when other operands decide
        h.p04_feature_templates()
    h = make(parsed="x|ABC", parent="5", sp=True)
    h.v.arrayList59 = [True]
    h.p04_feature_templates()
    assert h.v.arrayList46 == ["F01-05"]        # parentunavailable & SP & !flag4


def test_unique_components_prefix_and_flag():
    h = make(parsed="x|AB", featlen=2, _uniqueComponents=True)
    h.p04_feature_templates()
    assert h.v.arrayList25 == ["ITEM1-F01-02"]   # 3836-3838
    h = make(parsed="x|AB", featlen=2, _uniqueComponents=True, _plcPhantoms=True)
    h.p04_feature_templates()
    assert h.v.arrayList25 == ["[PC1x]-F01-02"]  # Product_Code PC-1_x -> PC1x (3835)
    h = make(parsed="x|AB", featlen=2, _uniqueComponents=True)
    h.v.arrayList60 = [3]                        # arrayList60 != 0: no prefix
    h.p04_feature_templates()
    assert h.v.arrayList25 == ["F01-02"]


def test_ignorecolour_skips_non_fab_branch():
    h = make(fab=2)
    h.v.arrayList45 = ["a", "b"]; h.v.arrayList18 = ["a", "b"]
    h.v.arrayList47 = [100, 101]; h.v.arrayList48 = [1, 1]; h.v.arrayList49 = [0, 2]
    h.v.arrayList54 = [2, 2]; h.v.arrayList55 = ["AB", "AB"]; h.v.arrayList57 = ["", ""]
    h.v.arrayList59 = [False, False]; h.v.arrayList60 = [0, 0]; h.v.arrayList61 = [[], []]
    h.p04_feature_templates()
    # option 1: fab==2 and index>0 -> flag10 (3628); 3788 `else if (!flag10)` skipped -> text57 stays ""
    assert h.v.arrayList25 == ["F01-02", ""]


# ---- fabric branch (17.1a, C# 3635-3787) -----------------------------------------------------------
@pytest.mark.parametrize("parsed,opt,flatten,expect,adv,x", [
    ("x|ABCD", 100, False, "BOCFAB-F01-04#", 8, "XXXXXXXX-"),   # case 4 (3676-3687)
    ("x|ABC", 100, False, "BOCFAB-F01-03#", 7, "XXXXXXX-"),     # case 3
    ("x|AB", 8512, False, "BOCFAB-F01-05#", 10, "XXXXXXXXXX-"), # 3644: forced 5
    ("x|AB", 8513, False, "BOCFAB-F01-02#", 7, "XXXXXXX-"),     # 8513 only forced when flattening -> default
    ("x|AB", 8513, True, "FAB-F01-08", 8, "XXXXXXXX-"),         # flatten: 8, text6 becomes FAB (3658)
])
def test_fabric_cases(parsed, opt, flatten, expect, adv, x):
    h = make(parsed=parsed, opt_id=opt, fab=1, _flattenFabrics=flatten)
    h.p04_feature_templates()
    assert h.v.arrayList25 == [expect]
    assert h.v.num6 == 1 + adv
    assert h.v.text19 == x


def test_fabric_9B_on_OF_item_is_three():
    h = make(parsed="x|9B", fab=1, item="OF123")   # 3640
    h.p04_feature_templates()
    assert h.v.arrayList25 == ["BOCFAB-F01-03#"]
    assert h.v.arrayList46 == ["BOCFAB-F01-03"]


def test_fabric_OF_item_ending_2_har_rename():
    h = make(parsed="x|ABC", fab=1, item="OF12")   # 3690-3692: pos 01 not 8/14 -> BOCFAB-<item>-HAR-
    h.p04_feature_templates()
    assert h.v.arrayList25 == ["BOCFAB-OF12-HAR--F01-03#".replace("HAR--", "HAR-")] or \
        h.v.arrayList25 == ["BOCFAB-OF12-HAR-F01-03#"]
    h = make(parsed="x|ABC", fab=1, item="OF12")
    h.v.num6 = 8                                    # 3692: position 8 -> bocfab-HAR-
    h.p04_feature_templates()
    assert h.v.arrayList25 == ["bocfab-HAR-F08-03#"]


def test_fabric_420KIT_flatten_adds_slot():
    h = make(parsed="x|AB", opt_id=8513, fab=1, item="420KIT", _flattenFabrics=True)
    h.p04_feature_templates()
    assert h.v.arrayList46 == ["FAB-F01-08"]        # 3662-3665


def test_fabric_parent_set_suppresses_slot_and_template():
    h = make(parsed="x|ABCD", fab=1, parent="9")
    h.p04_feature_templates()
    assert h.v.arrayList46 == [] and h.v.text19 == ""    # 3678/3683
    assert h.v.num6 == 9


def test_fabric_default_length5_true_uses_two_and_seven():
    h = make(parsed="x|AB", fab=1)
    h.p04_feature_templates()
    assert h.v.arrayList25 == ["BOCFAB-F01-02#"]     # 3706-3764: num56=2 num55=7
    assert h.v.num6 == 8 and h.v.text19 == "XXXXXXX-"
    assert h.v.arrayList46 == ["BOCFAB-F01-02"]


def test_fabric_length5_false_queries_and_caches():
    sql_hit = {"MAX(parent_opt.SLFeatureLength)": [{"parent_featlen": 3, "child_featlen": 4}]}
    h = make(parsed="x|AB", fab=1, length5=False, script=sql_hit)
    h.p04_feature_templates()
    assert h.v.arrayList25 == ["BOCFAB-F01-03#"]      # num56=num57=3, num55=7
    assert h.v.num6 == 8 and h.v.text19 == "XXXXXXX-"
    assert (h.v.arrayList36, h.v.arrayList37, h.v.arrayList35) == ([100], [3], [4])
    conn, sql, params, stage = h.db.calls[0]
    assert conn == "c7" and params == (100,) and "100" not in sql and stage == "17.2a"
    # second run with the cache: no further SQL
    h2 = make(parsed="x|AB", fab=1, length5=False, script=sql_hit)
    h2.v.arrayList36, h2.v.arrayList37, h2.v.arrayList35 = [100], [1], [2]
    h2.p04_feature_templates()
    assert h2.db.calls == [] and h2.v.arrayList25 == ["BOCFAB-F01-01#"] and h2.v.num6 == 4


def test_fabric_length5_false_null_lengths_swallowed_and_cached_with_defaults():
    h = make(parsed="x|AB", fab=1, length5=False,
             script={"MAX(parent_opt": [{"parent_featlen": None, "child_featlen": None}]})
    h.p04_feature_templates()                           # int.Parse("") throws, caught at 3737
    assert len(h.errors) == 1
    assert h.v.arrayList37 == [2] and h.v.arrayList35 == [5]   # 3748-3750 still cache defaults
    assert h.v.arrayList25 == ["BOCFAB-F01-02#"] and h.v.num6 == 1 + 7


# ---- loop control ---------------------------------------------------------------------------------
def test_option_not_in_list_skipped_only_when_syteline():
    h = make(); h.v.arrayList18 = []
    h.p04_feature_templates()
    assert h.v.arrayList25 == [] and h.v.num7 == 0       # 3590-3593
    h = make(); h.v.arrayList18 = []; h._syteline = False
    h.p04_feature_templates()
    assert h.v.arrayList25 == ["F01-02"]


def test_repeated_option_id_skipped():
    h = make()
    h.v.arrayList45 = ["a", "b"]; h.v.arrayList18 = ["a", "b"]
    h.v.arrayList47 = [100, 100]; h.v.arrayList48 = [1, 1]; h.v.arrayList49 = [0, 0]
    h.v.arrayList54 = [2, 2]; h.v.arrayList55 = ["AB", "AB"]; h.v.arrayList57 = ["", ""]
    h.v.arrayList59 = [False, False]; h.v.arrayList60 = [0, 0]; h.v.arrayList61 = [[], []]
    h.p04_feature_templates()
    assert h.v.arrayList25 == ["F01-02"] and h.v.num7 == 1   # 3614


def test_malformed_feature_length_raises():
    h = make(featlen="zz")
    with pytest.raises(LegacyFormatError):               # 3814 int.Parse
        h.p04_feature_templates()


def test_materialstr_substitution_17_5():
    h = make(materialstr="A\t[opt1]\tBOCFAB-Q\t[opt2]")
    h.p04_feature_templates()
    assert h.materialstr == "A\tF01-02\tBOCFAB-Q\t[opt2]".replace("\tBOCFAB-", "\t")  # 3920-3921


# ---- Aeron (17.3 / 17.6-17.7, C# 3844-4111) --------------------------------------------------------
def _aeron():
    h = make(parsed="x|ABC", item="AER1", opt_id=6431)
    v = h.v
    v.arrayList45 = ["a", "b"]; v.arrayList18 = ["a", "b"]
    v.arrayList47 = [6431, 6437]; v.arrayList48 = [1, 1]; v.arrayList49 = [0, 0]
    v.arrayList54 = [2, 2]; v.arrayList55 = ["ABC", "ABC"]; v.arrayList57 = ["", ""]
    v.arrayList59 = [False, False]; v.arrayList60 = [0, 0]; v.arrayList61 = [[], []]
    v.arrayList16 = [272082]
    return h


def test_aeron_6431_collects_frame_finishes_and_6437_rewrites():
    h = _aeron()
    h.materialstr = "AER1\tF06-05\t9-F06-05-DCR\t0\t1\t0\t12\r\n"
    h.p04_feature_templates()
    assert h.v.flag2 is True                              # 3926
    # 6431 -> text57 F01-05; CRB entry; 6437 -> text57 F06-05; text69 = 9-AER1-F01-05-CRB (3846,3959,4002-4013)
    # then the 10..99 fix-up (4097-4107) turns the trailing 12 into 4
    assert h.materialstr == "9-AER1-F01-05-CRB\tF06-05\t9-F06-05-DCR\t0\t1\t0\t4\r\n"


def test_aeron_6437_malformed_line_without_crlf_raises():
    h = _aeron()
    h.materialstr = "AER1\tF06-05\t9-F06-05-DCR\t0"       # no \r\n: Substring(0,-1) at 4006
    with pytest.raises(LegacyRangeError):
        h.p04_feature_templates()


def test_aeron_23103_fixup():
    h = _aeron()
    h.materialstr = "23103\t0\t1\t0\t4"
    h.p04_feature_templates()
    assert h.materialstr == "23103\t0\t1\t0\t5"            # 4108


def test_aeron_not_applied_for_notAER1G():
    h = _aeron(); h.v.sqlDataReader["Item"] = "notAER1G1"
    h.p04_feature_templates()
    assert h.v.flag2 is False


# ---- 17.8 .. 17.10 conversion / dedupe --------------------------------------------------------------
def _conv(**kw):
    h = make(parsed="x|ABC", **kw)
    v = h.v
    v.arrayList3 = ["CMP-[opt1]"]; v.arrayList4 = []; v.arrayList5 = ["a"]; v.arrayList6 = ["b"]
    v.arrayList7 = [3]; v.arrayList63 = ["4"]; v.arrayList65 = []
    return h


def test_component_converted_and_added_with_args():
    h = _conv(); h.v.arrayList61 = [[7]]
    h.p04_feature_templates()
    assert h.preConv == "" and h.ConvCount == 0
    (args,) = h.mat_calls
    # 4172: text91, str, str, int, flag13, SP&&flag4, feature, trace, -1, list, stage
    assert args[0] == "CMP-F01-05" and args[1:4] == ("a", "b", 3)
    assert args[4] is False                                # text91 lacks "-ITEM1-"
    assert args[5] is False and args[6] == ""
    assert args[7] == "CMP-[opt1]>>opt,100,AB,0,,[ITEM1]"
    assert args[8] == -1 and args[9] == [7] and args[10] == "17.105"
    assert h.fab_calls == []


def test_component_dependentoption_flag():
    h = _conv()
    h.v.arrayList3 = ["CMP-ITEM1-[opt1]"]; h.v.arrayList61 = [[7]]
    h.p04_feature_templates()
    assert h.mat_calls[0][4] is True     # num75=7>0 and text91 contains -ITEM1-  (4166)
    h = _conv(); h.v.arrayList3 = ["CMP-ITEM1-[opt1]"]
    h.p04_feature_templates()
    assert h.mat_calls[0][4] is True     # !flag9 -> true


def test_component_fabric_colour_when_hash_suffix():
    h = _conv(); h.v.arrayList3 = ["CMP-[opt1]-05#"]
    h.p04_feature_templates()
    (c,) = h.fab_calls
    assert c[0] == "CMP-F01-05-05#" and c[1] == 4 and c[2] is h.v.arrayList45 and c[3] is False  # 4173-4175
    assert h.materialstr == ""


def test_component_already_converted_is_ignored():
    h = _conv(); h._convertedList = ["CMP-F01-05"]          # 4157
    h.p04_feature_templates()
    assert h.mat_calls == []


def test_component_ignoreconvert_when_contains_text6():
    h = _conv(); h.v.arrayList3 = ["BOCFAB-[opt1]"]          # 4146: contains "BOCFAB-" and not "9-BOCFAB-"
    h.p04_feature_templates()
    assert h.mat_calls == []
    h = _conv(); h.v.arrayList3 = ["9-BOCFAB-[opt1]"]
    h.p04_feature_templates()
    assert len(h.mat_calls) == 1


def test_component_not_matching_tag_ignored():
    h = _conv(); h.v.arrayList3 = ["CMP-[opt2]"]
    h.p04_feature_templates()
    assert h.mat_calls == []


def test_component_feature_lookup_exact_and_item_forms():
    h = _conv(); h.v.arrayList65 = ["CMP-[opt1]"]; h.v.arrayList4 = ["feat-[opt1]"]
    h.p04_feature_templates()
    assert h.mat_calls[0][6] == "feat-F01-05"                 # 4141-4143
    h = _conv(); h.v.arrayList3 = ["CMP-ITEM1-[opt1]"]
    h.v.arrayList65 = ["zzCMP-ITEM1-[opt1]|q", "CMP-ITEM1-[opt1]"]
    h.v.arrayList4 = ["f1-[opt1]", "f2-[opt1]"]
    h.p04_feature_templates()
    assert h.mat_calls[0][6] == "f1-F01-05"                   # 4130-4139: only the entry with '|' counts


def test_sp_component_continue_at_4117():
    h = _conv(sp=True, _exportSPComponentMaterials=False)    # IsSuperProduct != 0, !flag4, !export
    h.p04_feature_templates()
    assert h.mat_calls == []
    h = _conv(sp=False, _exportSPComponentMaterials=False)   # IsSuperProduct == 0 passes
    h.p04_feature_templates()
    assert len(h.mat_calls) == 1


def test_no_sql_when_length5_true_and_params_bound():
    h = make(parsed="x|AB", fab=1)
    h.p04_feature_templates()
    assert h.db.calls == []
