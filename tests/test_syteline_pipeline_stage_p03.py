"""Tests for services/syteline_export/pipeline/stage_p03_materials.py (ExportThread.cs 2876-3578).

All fixtures are SYNTHETIC. Expected values are derived by reading the C# (line numbers cited), not by
running the port.
"""
from __future__ import annotations

import pytest

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.netsem import LegacyFormatError, LegacyRangeError
from services.syteline_export.pipeline.run_base import ExportRunBase
from services.syteline_export.pipeline.stage_p03_materials import P03Mixin

Q_NORMAL = "INNER JOIN Item ON itov.ItemId = Item.ItemId"                     # 2888
Q_SP14 = "INNER JOIN Item subitem ON itco.SubItemId = subitem.ItemId INNER JOIN Product ON subitem"  # 2896
Q_SP15 = "INNER JOIN OptionValue optval"                                       # 2946
Q_PARENT = "AS parentitem"                                                     # 3008


class H(P03Mixin, ExportRunBase):
    """Harness; the helpers owned by other agents are replaced by recording stubs."""

    def get_item_sequence(self, myparentitem, thisordercode):
        self.seq_calls.append((myparentitem, thisordercode))
        return 7

    def parse_opt_code(self, optcode, optvalId, optionId):
        self.poc_calls.append((optcode, optvalId, optionId))
        return "PC"

    def get_translation(self, a, b, c, d, index):
        return f"TR{index}"


def make(script=None, *, options=1, item="ABC", sp=False, flag4=False, **flags):
    """One item with ``options`` options; every parallel list defaulted (ExportThread.cs 2505-2771)."""
    h = H(ScriptedExportDb(script or {Q_NORMAL: []}))
    h.seq_calls, h.poc_calls = [], []
    for k, val in flags.items():
        setattr(h, k, val)
    v = h.v
    v.sqlDataReader = {"Item": item, "LongItem": "LONG" + item, "ItemId": 55, "IsSuperProduct": str(sp)}
    v.flag4 = flag4
    v.num18 = options - 1
    v.arrayList45 = [100 + i for i in range(options)]
    v.arrayList47 = [5 + i for i in range(options)]
    v.arrayList48 = [200 + i for i in range(options)]
    v.arrayList49 = [0] * options
    v.arrayList50 = ["Opt"] * options
    v.arrayList52 = [f"desc{i}" for i in range(options)]
    v.arrayList53 = [f"dd{i}" for i in range(options)]
    v.arrayList55 = ["1|X"] * options
    v.arrayList56 = [3] * options
    v.arrayList57 = [""] * options
    v.arrayList58 = ["PVC"] * options
    v.arrayList59 = [False] * options
    v.arrayList60 = ["0"] * options
    for name in ("3 4 5 6 7 9 10 11 12 13 14 15 26 29 30 31 32 43 44 63 64 65".split()):
        setattr(v, f"arrayList{name}", [])
    return h


def test_plain_option_material_line_and_registration():
    h = make()
    assert h.p03_materials() is None
    v = h.v
    # 3291-3298 (16.10a), 3501: text38 with Item\t replaced by LongItem\t; text33 from getItemSequence (3168)
    assert h.materialstr == "ABC\t[opt1]\t9-[opt1]-X\tPC\t0\t1\t0\t7\t\t\t10\t\r\n".replace("ABC\t", "LONGABC\t", 1)
    assert h.seq_calls == [("ABC", "1|X")]
    assert h.poc_calls == [("X", 200, 5)]                       # 3292
    assert (v.text14, v.text15) == ("ABC", "1|X")               # 3173-3174
    assert v.arrayList65 == ["ABC|[opt1]|X"]                    # 3388/3490
    assert v.arrayList3 == ["9-[opt1]-X"] and v.arrayList4 == ["[opt1]"]
    assert v.arrayList9 == ["ABC"] and v.arrayList10 == [["9-[opt1]-X"]] and v.arrayList11 == [["ABC|[opt1]|X"]]
    assert v.arrayList63 == [100] and v.arrayList64 == ["9-[opt1]-X"]
    assert v.arrayList5 == ["desc0"] and v.arrayList6 == [""] and v.arrayList7 == [3]   # 3543/3552/3554
    assert h.threadStage == "16.15a"


def test_description_translation_lookups_3532_3552():
    h = make()
    h.v.arrayList30 = ["dd0"]
    h.v.arrayList29 = ["TRANS"]
    h.v.arrayList32 = ["x", "dd0"]
    h.v.arrayList31 = ["a", "COLOURDESC"]
    h.p03_materials()
    assert h.v.arrayList5 == ["TRANS"] and h.v.arrayList6 == ["COLOURDESC"]


def test_increment_accumulation_16_10b():
    h = make({Q_NORMAL: [{"Item": "ABC", "MyIncrementalPrice": 12.5}]})
    h.p03_materials()
    # 2924 row "ABC|12.5"; 3269-3271 num30 = 12.5; 16.10b 3343 -> "\t12.5\t1\t0\t"
    assert h.materialstr == "LONGABC\t[opt1]\t9-[opt1]-X\tPC\t12.5\t1\t0\t7\t\t\t10\t\r\n"


def test_empty_increment_is_skipped_2922():
    h = make({Q_NORMAL: [{"Item": "ABC", "MyIncrementalPrice": None}]})
    h.p03_materials()
    assert "\t0\t1\t0\t" in h.materialstr


def test_intentional_deviation_embedded_token_entry_is_ignored_3269():
    # ExportThread.cs 3269 matches by substring: "XABC|4" contains "ABC|", Replace gives "X4" and
    # double.Parse throws (or "2ABC|4" silently sums 24). Deviation: only entries that START with
    # "<token>|" belong to the token, so these entries contribute nothing.
    h = make({Q_NORMAL: [{"Item": "XABC", "MyIncrementalPrice": 4}]})
    h.p03_materials()
    assert "	0	1	0	" in h.materialstr           # num30 stayed 0 (see test_empty_increment_is_skipped_2922)


def test_matching_entry_with_malformed_amount_still_raises_3269():
    h = make({Q_NORMAL: [{"Item": "ABC", "MyIncrementalPrice": "n/a"}]})
    with pytest.raises(LegacyFormatError):
        h.p03_materials()


def test_millercad_uses_inclist_and_binds_parameters():
    h = make(
        {Q_NORMAL: [{"Item": "ABC", "MyIncrementalPrice": 1, "IncList": 3.0}, {"Item": "ABC", "MyIncrementalPrice": 1, "IncList": ""}]},
        _millerCAD=True, _currency="GBP", _siteId=9, _effectiveDate="01/02/2024",
    )
    h.p03_materials()
    conn, sql, params, stage = h.db.calls[0]
    assert conn == "c2" and stage == "14"
    # 2886 / 2888 textual order: currency, text9, siteId (IncList), siteId, currency, optionValueId, ItemId
    assert params == ("GBP", "01/02/2024", 9, 9, "GBP", 100, 55)
    assert sql.count("?") == len(params)
    for data in ("GBP", "01/02/2024", "55"):
        assert data not in sql
    assert "\t3\t1\t0\t" in h.materialstr                       # 2912 uses IncList (3.0 -> "3")


def test_syteline_without_base_prices_uses_inclist_2915():
    h = make({Q_NORMAL: [{"Item": "ABC", "MyIncrementalPrice": 9, "IncList": 2.5}]},
             _syteline=True, _exportBasePrices=False)
    h.p03_materials()
    assert "\t2.5\t1\t0\t" in h.materialstr


def sp_script(stage14=(), stage15=(), parents=(("P1",), ("P2",))):
    return {
        Q_SP15: stage15,
        Q_PARENT: [{"parentitem": p[0]} for p in parents],
        Q_SP14: stage14,
        Q_NORMAL: [],
    }


def test_super_product_parents_and_additional_lines():
    h = make(sp_script(stage14=[{"Item": "P1", "MyIncrementalPrice": 3}]), sp=True, item="SP1")
    h.v.arrayList60 = ["2"]
    h.p03_materials()
    v = h.v
    # 3016/3035-3048: "P1|P2|" -> text30 "P1", extra parent "P2<5>"; arrayList26 gets optionId 5
    assert v.arrayList43 == ["P1|P2|"] and v.arrayList44 == ["55~5"]
    assert v.arrayList26 == [5]
    # 3146 text36 "_#_"; 3180 "9-P1-"; 3291-3298 (16.10b since num30 = 3)
    line1 = "P1\t[opt_#_1]\t9-P1-[opt_#_1]-X\tPC|TR0\t3\t1\t0\t[opt~#~1][seq]7\t\t\t10\t\r\n"
    # 3367-3373: text37.Replace("P1","P2"), [opt_1_ ; no matching increment -> 0
    line2 = "P2<5>\t[opt_1_1]\t9-P2-[opt_1_1]-X\tPC|TR0\t0\t1\t0\t[opt~1~1][seq]7\t\t\t10\t\r\n"
    assert h.materialstr == (line1 + line2).replace("SP1\t", "LONGSP1\t")
    # 3511-3530: registered component list gets "<text46>" and the P2 variant
    assert v.arrayList64 == ["9-P1-[opt_#_1]-X", "9-P2-[opt_1_1]-X"]  # 3520-3528: "[opt_#" -> "[opt_1"
    assert v.arrayList63 == [100, 100]


def test_super_product_fallback_extend_sp_opts_bound_15():
    h = make(sp_script(stage14=[], stage15=[{"Item": "P1", "MyIncrementalPrice": 6}]),
             sp=True, item="SP1", _extendSPOpts=True, _currency="GBP", _siteId=4)
    h.v.arrayList55 = ["1|AB|CD"]
    h.p03_materials()
    stage15 = [c for c in h.db.calls if Q_SP15 in c[1]]
    assert len(stage15) == 1
    conn, sql, params, stage = stage15[0]
    assert stage == "15" and conn == "c2"
    # 2947: text29 = after first "|" ; params siteId, currency, OrderCodeValue, optvalId, ItemId
    assert params == (4, "GBP", "AB|CD", 100, 55)
    assert "AB|CD" not in sql and sql.count("?") == 5
    assert "\t6\t1\t0\t" in h.materialstr


def test_super_product_fallback_not_extended_and_not_for_fabric_2932():
    h = make(sp_script(stage15=[{"Item": "P1", "MyIncrementalPrice": 6}]), sp=True, item="SP1")
    h.v.arrayList49 = [1]                                       # IsFabric != 0 -> no fallback query
    h.p03_materials()
    assert not [c for c in h.db.calls if Q_SP15 in c[1]]
    h2 = make(sp_script(stage15=[{"Item": "P1", "MyIncrementalPrice": 6}]), sp=True, item="SP1")
    h2.p03_materials()
    call = [c for c in h2.db.calls if Q_SP15 in c[1]][0]
    assert "optval.OptionValueId = ?" in call[1] and call[2] == (h2._siteId, "GBP", 100, 55)   # 2947 (!extend)


def test_16_10a_and_16_11a_when_only_additional_parent_has_increment():
    h = make(sp_script(stage14=[{"Item": "P2", "MyIncrementalPrice": 4}]), sp=True, item="SP1")
    h.p03_materials()
    # "P2|4" does not contain "P1|" -> num30 = 0 -> 16.10a (3288-3298); 16.11a (3309-3331) finds "P2|" -> 4
    assert h.materialstr == (
        "P1\t[opt_#_1]\t9-[opt_#_1]-X\tPC|TR0\t0\t1\t0\t[opt~#~1][seq]7\t\t\t10\t\r\n"
        "P2<5>\t[opt_1_1]\t9-[opt_1_1]-X\tPC|TR0\t4\t1\t0\t[opt~1~1][seq]7\t\t\t10\t\r\n"
    )


def test_intentional_deviation_embedded_token_entries_ignored_3316_and_3362():
    # Legacy: "XP2|4".Replace("P2|","") = "X4" -> double.Parse throws. Deviation: not a match.
    h = make(sp_script(stage14=[{"Item": "XP2", "MyIncrementalPrice": 4}]), sp=True, item="SP1")
    h.p03_materials()
    h = make(sp_script(stage14=[{"Item": "P2", "MyIncrementalPrice": 1}, {"Item": "XP2", "MyIncrementalPrice": 4}]),
             sp=True, item="SP1")
    h.p03_materials()                         # only "P2|1" is summed (16.11a), "XP2|4" is not a match


def test_increment_helpers_anchor_the_token():
    from services.syteline_export.pipeline.stage_p03_materials import _increment_amount, _increment_text
    assert _increment_text("ABC|1.5", "ABC") == "1.5"
    assert _increment_text("XABC|4", "ABC") is None and _increment_text("2ABC|4", "ABC") is None
    assert _increment_text("ABCD|4", "ABC") is None
    assert _increment_amount("ABC|2", "ABC") == 2.0 and _increment_amount("OTHER|2", "ABC") is None
    with pytest.raises(LegacyFormatError):
        _increment_amount("ABC|n/a", "ABC")


def test_parent_cache_hit_skips_query_3000():
    h = make(sp_script(), sp=True, item="SP1")
    h.v.arrayList43 = ["P1|"]
    h.v.arrayList44 = ["55~5"]
    h.p03_materials()
    assert not [c for c in h.db.calls if Q_PARENT in c[1]]
    # cached "P1|" behaves like the queried result: text36 "_#_" because text30 != Item (3144)
    assert h.materialstr.startswith("P1	[opt_#_1]	")


def test_access_flap_finish_second_iteration_3994():
    rows = {Q_PARENT: lambda conn, sql, params: [{"parentitem": "P1"}] if params[1] == 1142 else [],
            Q_SP15: [], Q_SP14: [], Q_NORMAL: []}
    h = make(rows, sp=True, item="SP1")
    h.v.arrayList50 = ["Access Flap Finish"]
    h.p03_materials()
    parent_calls = [c for c in h.db.calls if Q_PARENT in c[1]]
    assert [c[2] for c in parent_calls] == [(55, 5, 5), (55, 1142, 1142)]       # 3008, 2994-2996
    assert h.v.arrayList44 == ["55~1142"] and h.v.arrayList43 == ["P1|"]


def test_parent_option_replacement_and_9_counter_3085_3160():
    h = make()
    h.v.arrayList57 = ["10"]
    h.v.arrayList63 = [10]
    h.v.arrayList64 = ["9-PAR-[opt1]-Y"]
    h.v.arrayList47 = [9275]                                    # one of the OptionIds forcing replacement
    h.p03_materials()
    v = h.v
    assert v.arrayList14 == ["9-PAR-[opt1]-Y"] and v.arrayList15 == [2]
    assert h.materialstr.startswith("9-PAR-[opt1]-Y\t[opt1]\t")   # text30 replaced -> 3291
    assert "[seq]" not in h.materialstr and h.materialstr.endswith("\t2\t\t\t10\t\r\n")  # text33 "2" (3160)
    assert h.seq_calls == []                                    # getItemSequence not used for "9-" parents
    # 3108: starts with "9-" so arrayList59 stays False; 3386 -> registered under text30
    assert h.v.arrayList59 == [False] and h.v.arrayList9 == ["9-PAR-[opt1]-Y"]
    # second option with same parent increments the counter (3158)
    h2 = make(options=2)
    h2.v.arrayList57 = ["10", "10"]
    h2.v.arrayList63 = [10]
    h2.v.arrayList64 = ["9-PAR-[opt1]-Y"]
    h2.v.arrayList47 = [9275, 9313]
    h2.p03_materials()
    assert h2.v.arrayList15 == [3]


def test_unresolved_parent_marks_unavailable_and_records_feature_3108_3566():
    h = make()
    h.v.arrayList57 = ["10"]
    h.v.arrayList63 = [10]
    h.v.arrayList64 = ["zzz"]
    h.p03_materials()
    # not "9-" -> arrayList59 True (3110); non-SP + unavailable -> skip (3456-3460); 16.15b records parents
    assert h.v.arrayList59 == [True]
    assert h.materialstr == ""
    assert h.v.arrayList12 == ["ABC"] and h.v.arrayList13 == ["1|X"]
    assert h.threadStage == "16.15b"


def test_ignore_opt_deps_dedupe_3411_3435():
    h = make(options=2, _ignoreOptDeps=True)
    h.v.arrayList55 = ["1|X", "1|X"]
    h.p03_materials()
    # first option registered (flag8 False), second identical code skipped (3415: mymaterials contains text45)
    assert h.materialstr.count("LONGABC\t[opt1]") == 1
    assert h.v.arrayList65 == ["ABC|[opt1]|X"]
    assert h.v.arrayList12 == ["ABC"]                          # skipped one goes through 16.15b
    # 3178: !_ignoreOptDeps false -> no item prefix even with children
    assert "9-[opt1]-X" in h.materialstr


def test_fabric_options_3397_3410():
    h = make(options=2)
    h.v.arrayList49 = [2, 1]
    h.v.arrayList55 = ["1|X", "2|Y"]
    h.p03_materials()
    assert h.skippedFabricColours == ["1|X:desc0~1", "2|Y:desc1~2"]   # 3405
    assert h.v.arrayList65 == ["ABC|[opt2]|Y"]                        # fabric colour (2) skipped, 1 kept
    assert h.v.arrayList12 == []                                       # 3566: IsFabric < 2 only, 1st skipped has 2


def test_option_with_children_prefixes_item_3178():
    h = make()
    h.v.arrayList60 = ["3"]
    h.p03_materials()
    assert "\t9-ABC-[opt1]-X\t" in h.materialstr


def test_spaces_in_code_become_underscores_and_mrfn_suffix_3187_3190():
    h = make(item="MRFN1")
    h.v.arrayList55 = ["1|A B"]
    h.v.arrayList48 = [300564]
    h.p03_materials()
    assert "\t9-[opt1]-A_B-PVC\t" in h.materialstr
    h2 = make(item="MRFN1")
    h2.v.arrayList48 = [1]
    h2.p03_materials()
    assert "PVC" not in h2.materialstr


def test_hyphen_shortening_case_2_from_parent_list_3224_3256():
    # parent "P-1" from the cache: text31 "P-1|" has "-" -> num33 = 2; text39 "P-1" -> "P~1" -> "P-1" again
    h = make({Q_SP14: [{"Item": "P-1", "MyIncrementalPrice": 2}], Q_NORMAL: []}, sp=True, item="SP1")
    h.v.arrayList43 = ["P-1|"]
    h.v.arrayList44 = ["55~5"]
    h.p03_materials()
    assert "	2	1	0	" in h.materialstr


def test_hyphen_shortening_case_1_item_with_hyphen_3219_3244():
    h = make({Q_NORMAL: [{"Item": "A-B", "MyIncrementalPrice": 5}]}, item="A-B")
    h.p03_materials()
    assert "	5	1	0	" in h.materialstr


def test_hyphen_shortening_truncates_at_first_hyphen_3237():
    # 9- parent "9-ABC-DEF" -> text39 "ABC-DEF" (no hyphen in Item/text31) -> "ABC"
    h = make({Q_NORMAL: [{"Item": "ABC", "MyIncrementalPrice": 8}]})
    h.v.arrayList57 = ["10"]
    h.v.arrayList63 = [10]
    h.v.arrayList64 = ["9-ABC-DEF"]
    h.v.arrayList47 = [9275]
    h.p03_materials()
    assert "	8	1	0	" in h.materialstr


def test_malformed_data_throws():
    h = make()
    h.v.arrayList55 = ["noseparator"]
    with pytest.raises(LegacyRangeError):                       # 3137 Substring(0, -1)
        h.p03_materials()
    h = make()
    h.v.arrayList55 = ["a|X"]
    with pytest.raises(LegacyFormatError):                      # Conversions.ToInteger("a")
        h.p03_materials()
    h = make()
    h.v.arrayList57 = ["abc"]
    h.v.arrayList63 = [1]
    with pytest.raises(LegacyFormatError):                      # 3076 int.Parse("abc")
        h.p03_materials()
    h = make()
    h.v.sqlDataReader["IsSuperProduct"] = "maybe"
    with pytest.raises(LegacyFormatError):                      # 2889 bool.Parse
        h.p03_materials()
    h = make({Q_NORMAL: [{"Item": "ABC", "MyIncrementalPrice": "x"}]})
    with pytest.raises(LegacyFormatError):                      # 2924 double.Parse
        h.p03_materials()


def test_no_options_does_nothing():
    h = make(options=0)
    h.v.num18 = -1
    assert h.p03_materials() is None
    assert h.db.calls == [] and h.materialstr == ""


def test_stage_labels_progress():
    h = make()
    h.p03_materials()
    assert h.threadStage == "16.15a"
