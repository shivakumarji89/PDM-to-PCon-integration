"""Tests for ExportThread.cs 6780-7032 (stages 39-41). All fixtures are synthetic.

Expected values are derived from the C# (line numbers cited), not from running the port.
"""
import sys
import types

import pytest

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.netsem import LegacyFormatError, LegacyRangeError
from services.syteline_export.pipeline.run_base import ExportRunBase
from services.syteline_export.pipeline.stage_p10_bom import P10Mixin


class H(P10Mixin, ExportRunBase):
    pass


def make(script=None, *, flag2=False, a1=(), a2=(), csi=False, bom=False, text14="T14"):
    h = H(ScriptedExportDb(script or {}))
    h.v.flag2 = flag2
    h.v.arrayList = list(a1)
    h.v.arrayList2 = list(a2)
    h.v.text14 = text14
    h._formatCSI = csi
    h._exportBOMData = bom
    h._siteId = 7
    return h


def wide(first, n_fields=41):
    return "\t".join([first] + [f"f{i}" for i in range(1, n_fields)])


def test_flag2_replacements_6788_6802():
    h = make(flag2=True, a1=["x\tF23-02\tF25-05"], a2=["F23-02\tF25-04\tF25-05"])
    h.p10_bom()
    # sheet1 6788-6789; sheet2 replaces F23-02 and F25-04 only (6801-6802)
    assert h.v.arrayList[0] == "x\tF23-03\tF26-04"
    assert h.v.arrayList2[0] == "F23-03\tF26-04\tF25-05"
    assert h.threadStage == "39"


def test_flag2_compound_replacements_6790_6796():
    h = make(flag2=True, a1=["a\tF01-03\tF04-03\tF07-03\tF10-03\tF13-03\tF23-03", "b\t\tF16-07\t"])
    h.p10_bom()
    assert h.v.arrayList[0] == "a\tF01-03\tF04-03\tF13-03\tF23-03\t\t\t"
    assert h.v.arrayList[1] == "b\t\tF07-03\tF16-07"


def test_flag2_false_leaves_rows():
    h = make(a1=["	F23-02"], a2=["F23-02"])
    h.p10_bom()
    assert h.v.arrayList == ["	F23-02"] and h.v.arrayList2 == ["F23-02"]


def test_f14_insert_6808_6810():
    h = make(a1=["9-CN1G-F05-03-x\tF08-03\tz"])
    h.p10_bom()
    # row is too short to repack (6859), so only the 6810 replace is visible
    assert h.v.arrayList[0] == "9-CN1G-F05-03-x\tF08-03\tF14-03z"


def test_f14_not_inserted_if_present_or_no_f05():
    h = make(a1=["9-CN1L-F05-03-\tF08-03\tF14-03", "9-CN1R-\tF08-03\t"])
    h.p10_bom()
    # neither row is wide enough to be repacked (flag25 -> continue, 6859), so they are unchanged
    assert h.v.arrayList == ["9-CN1L-F05-03-\tF08-03\tF14-03", "9-CN1R-\tF08-03\t"]


def test_row_starting_with_tab_skipped_6818():
    h = make(a1=["\tabc"])
    h.p10_bom()
    assert h.v.arrayList == ["\tabc"]


def test_row_without_tab_throws_6822():
    h = make(a1=["notab"])
    with pytest.raises(LegacyRangeError):
        h.p10_bom()


def test_short_row_unchanged_6859():
    h = make(a1=["a\tb\tc"], a2=["a\tX\ty"])
    h.p10_bom()
    assert h.v.arrayList == ["a\tb\tc"]


def test_packing_6813_6882():
    row = wide("A")  # fields A,f1..f40
    h = make(a1=[row], a2=["A\tX\trest", "A\tY\trest", "A\tX\trest", "B\tZ\trest"])
    h.p10_bom()
    first34 = "".join(f + "\t" for f in ["A"] + [f"f{i}" for i in range(1, 34)])
    # text246 = "X\tY\t" (duplicate X ignored, B ignored), num285 = 2; pad num290=4..20 -> 17 tabs; tail f40
    assert h.v.arrayList[0] == first34 + "X\tY\t" + "\t" * 17 + "f40"


def test_packing_sheet2_row_without_tab_ignored():
    row = wide("A")
    h = make(a1=[row], a2=["A"])
    h.p10_bom()
    # right11 stays "" != "A": num285 = 0 -> 19 tabs (2..20)
    first34 = "".join(f + "\t" for f in ["A"] + [f"f{i}" for i in range(1, 34)])
    assert h.v.arrayList[0] == first34 + "\t" * 19 + "f40"


def test_sheet2_row_with_one_tab_throws_6834():
    row = wide("A")
    h = make(a1=[row], a2=["A\tonlyone"])
    with pytest.raises(LegacyRangeError):
        h.p10_bom()


def test_bom_disabled_makes_no_sql():
    h = make(a2=["I\tz\tA\tO\t0\tq"], bom=False)
    h.p10_bom()
    assert h.db.calls == []
    h2 = make(a2=["I\tz\tA\tO\t0\tq"], bom=True, csi=True)
    h2.p10_bom()
    assert h2.db.calls == []


class FakeBom:
    instances = []

    def __init__(self, db, sheet1, sheet2, items, opt_val_ids, **kwargs):
        self.args = (db, sheet1, sheet2, items, opt_val_ids)
        self.sheet1Data, self.sheet2Data = sheet1, sheet2
        self.sheet2Items, self.sheet2OptValIds = items, opt_val_ids
        FakeBom.instances.append(self)

    result = True

    def generate_bom_data(self):
        self.sheet1Data = ["NEW1"]
        self.sheet2Data = ["NEW2"]
        return FakeBom.result


@pytest.fixture
def fake_bom(monkeypatch):
    mod = types.ModuleType("services.syteline_export.pipeline.bom_export")
    mod.BomExport = FakeBom
    monkeypatch.setitem(sys.modules, "services.syteline_export.pipeline.bom_export", mod)
    FakeBom.instances = []
    FakeBom.result = True
    return FakeBom


def script(item_rows, option_rows):
    return {
        "SELECT ItemId FROM Item": lambda c, s, p: item_rows(p),
        "PDMOptionDataReportWithIncBase": lambda c, s, p: option_rows(p),
    }


def test_bom_lookup_and_match_6897_7020(fake_bom):
    # 'I'm' has an apostrophe: must be bound, never concatenated into SQL.
    a2 = ["I'm\tz\tA\tOPT1\t0\tq"]
    sc = script(
        lambda p: [{"ItemId": "5"}],
        lambda p: [
            {"OptionValueId": "11", "OrderCodeValue2": "OPT0", "IncPriceBase": "1.5"},
            {"OptionValueId": "12", "OrderCodeValue2": "OPT1", "IncPriceBase": ""},
        ],
    )
    h = make(sc, a1=["	k"], a2=a2, bom=True)
    h.p10_bom()
    b = fake_bom.instances[0]
    assert b.sheet2Items == ["I'm"] and b.sheet2OptValIds == [12]
    assert h.v.arrayList == ["NEW1"] and h.v.arrayList2 == ["NEW2"]
    for conn, sql, params, stage in h.db.calls:
        assert conn == "c2" and "I'm" not in sql
    assert h.db.calls[0][2] == ("I'm",) and h.db.calls[0][3] == "40"
    assert h.db.calls[1][2] == ("I'm", 7) and h.db.calls[1][3] == "41"
    assert h.threadStage == "41"


def test_price_must_match_and_hash_retry_6985(fake_bom):
    # 2nd pass (num298 == 2) accepts OPT1# ; price 2.5 must equal IncPriceBase
    a2 = ["I\tz\tA\tOPT1\t2.5\tq", "J\tz\tA\tOPT1\t9\tq"]
    sc = script(
        lambda p: [{"ItemId": "5"}],
        lambda p: [{"OptionValueId": "21", "OrderCodeValue2": "OPT1#", "IncPriceBase": "2.5"}],
    )
    h = make(sc, a2=a2, bom=True)
    h.p10_bom()
    b = fake_bom.instances[0]
    assert b.sheet2Items == ["I", "[undefined]"] and b.sheet2OptValIds == [21, -1]


def test_cache_by_left14_runs_report_once(fake_bom):
    a2 = ["I\tz\tA\tO\t0\tq", "I\tz\tA\tO\t0\tq"]
    sc = script(lambda p: [{"ItemId": 1}], lambda p: [{"OptionValueId": 3, "OrderCodeValue2": "O", "IncPriceBase": None}])
    h = make(sc, a2=a2, bom=True)
    h.p10_bom()
    procs = [c for c in h.db.calls if "PDMOption" in c[1]]
    assert len(procs) == 1
    assert fake_bom.instances[0].sheet2OptValIds == [3, 3]


def test_bocfab_uses_text14_and_9_prefix_6900_6910(fake_bom):
    a2 = ["BOCFAB1\tz\tA\tO\t0\tq", "9-KEY-xx\tz\tA\tO\t0\tq"]
    sc = script(lambda p: [{"ItemId": 1}], lambda p: [{"OptionValueId": 3, "OrderCodeValue2": "O", "IncPriceBase": ""}])
    h = make(sc, a2=a2, bom=True, text14="T14")
    h.p10_bom()
    lookups = [c[2] for c in h.db.calls if "SELECT ItemId" in c[1]]
    assert lookups == [("T14",), ("KEY",)]


def test_generic_fabric_6012(fake_bom):
    # text252 (3rd field) contains 9-FAB- => "[generic]" (7012-7014); text254 = text256 minus 9-FAB- (6934)
    a2 = ["I\tz\t9-FAB-C1\tOPT\t0\tq"]
    sc = script(lambda p: [{"ItemId": 1}], lambda p: [{"OptionValueId": 4, "OrderCodeValue2": "C1", "IncPriceBase": "0"}])
    h = make(sc, a2=a2, bom=True)
    h.p10_bom()
    b = fake_bom.instances[0]
    assert b.sheet2Items == ["[generic]"] and b.sheet2OptValIds == [4]


def test_item_not_found_records_warning_7005(fake_bom):
    a2 = ["I\tz\tA\tO\t0\tq"]
    sc = script(lambda p: [], lambda p: [])
    h = make(sc, a2=a2, bom=True)
    h.p10_bom()
    assert any("unable to establish itemId for [I]" in w for w in h.warnings)
    b = fake_bom.instances[0]
    assert b.sheet2Items == ["[undefined]"] and b.sheet2OptValIds == [-1]
    assert not any("PDMOption" in c[1] for c in h.db.calls)


def test_row_without_tab_gets_defaults_6897(fake_bom):
    h = make(script(lambda p: [], lambda p: []), a2=["\tx"], bom=True)  # IndexOf == 0 is not > 0
    h.p10_bom()
    assert fake_bom.instances[0].sheet2Items == ["[undefined]"]
    assert h.db.calls == []


def test_generate_false_keeps_arrays(fake_bom):
    fake_bom.result = False
    h = make(script(lambda p: [], lambda p: []), a1=["	k"], a2=[], bom=True)
    h.p10_bom()
    assert h.v.arrayList == ["	k"] and h.v.arrayList2 == []


def test_bad_price_throws_6929(fake_bom):
    h = make(script(lambda p: [], lambda p: []), a2=["I\tz\tA\tO\tabc\tq"], bom=True)
    with pytest.raises(LegacyFormatError):
        h.p10_bom()


def test_bad_option_value_id_throws_6965(fake_bom):
    sc = script(lambda p: [{"ItemId": 1}], lambda p: [{"OptionValueId": "x", "OrderCodeValue2": "O", "IncPriceBase": ""}])
    h = make(sc, a2=["I\tz\tA\tO\t0\tq"], bom=True)
    with pytest.raises(LegacyFormatError):
        h.p10_bom()


def test_bad_item_id_throws_6946(fake_bom):
    sc = script(lambda p: [{"ItemId": "zz"}], lambda p: [])
    h = make(sc, a2=["I\tz\tA\tO\t0\tq"], bom=True)
    with pytest.raises(LegacyFormatError):
        h.p10_bom()
