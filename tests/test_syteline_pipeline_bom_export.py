"""Tests for services/syteline_export/pipeline/bom_export.py (SytelineBOMExport.cs).

All fixtures are SYNTHETIC. Expected values are derived by reading SytelineBOMExport.cs (line numbers
cited), not by running the port.
"""
from decimal import Decimal

import pytest

from services.syteline_export.pipeline.bom_export import BOM_CONNECTION, BomExport
from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.netsem import LegacyFormatError

CAT = "distinct pc.productcategoryid"
BOM = "exec MaterialBOM"


def sheet1_row(item, kind="M"):
    fields = [""] * 30
    fields[0] = item
    fields[24] = kind
    return "\t".join(fields)


def make_db(categories=None, boms=None):
    categories = categories or {}
    boms = boms or {}

    def cat(conn, sql, params):
        return categories.get(params[0], [])

    def bom(conn, sql, params):
        return boms.get(params, [])

    return ScriptedExportDb({CAT: cat, BOM: bom})


def run(db, s1, s2, items, opts, errs=None):
    be = BomExport(db, s1, s2, items, opts, report_error=(lambda c, e: errs.append((c, e))) if errs is not None else None)
    return be, be.generate_bom_data()


def test_pass1_removes_rows_with_empty_first_field_in_all_three_lists():
    # cs:26-36
    s2 = ["\tx\ty\tz", "keep\tA\tC\tD\t\t\t\t1", "\tq"]
    items = ["i0", "i1", "i2"]
    opts = [1, 2, 3]
    s1 = []
    be, ok = run(make_db(), s1, s2, items, opts)
    assert ok is True
    # surviving row renamed in pass 2 (cs:44-47): text="C", new="9-A-i1-D"
    assert s2 == ["keep\tA\t9-A-i1-D\tD\t\t\t\t1"]
    assert items == ["i1"]
    assert opts == [2]


def test_pass2_rename_updates_sheet2_row_items_and_sheet1():
    # cs:44-65. r0 col2 "C1"; sheet1 row whose col0 == "C1" is rewritten; item k with col0=="C1" rewritten.
    s2 = ["PAR\tA\tC1\tD\t\t\t\t3", "C1\tB\tQQ\tR\t\t\t\t4"]
    items = ["itm", "xC1y"]
    opts = [5, 6]
    s1 = [sheet1_row("C1", "X").replace("\t\t", "\tfoo\tC1\t", 1), sheet1_row("other", "X")]
    be, ok = run(make_db(), s1, s2, items, opts)
    assert ok
    # j=0: new="9-A-itm-D"; r0 replaced; k=1 has col0 "C1" -> items[1]="x9-A-itm-Dy"; sheet1[0] replaced (all occurrences)
    assert s1[0].startswith("9-A-itm-D\tfoo\t9-A-itm-D\t")
    assert s1[1] == sheet1_row("other", "X")
    # j=1: text="QQ", new="9-B-x9-A-itm-Dy-R"
    assert s2[0] == "PAR\tA\t9-A-itm-D\tD\t\t\t\t3"
    assert s2[1] == "C1\tB\t9-B-x9-A-itm-Dy-R\tR\t\t\t\t4"
    assert items[1] == "x9-A-itm-Dy"


def test_pass2_skips_empty_sheet2_rows():
    # cs:40-43: Data[j]=="" -> continue. (pass 1 would have removed it unless first field is non-empty,
    # so an empty row can't survive pass 1; verify the whole thing is harmless for an empty list.)
    be, ok = run(make_db(), [], [], [], [])
    assert ok is True


def test_pass3_sheet1_M_item_generates_material_rows_and_sheet2_rows():
    # cs:67-112, row text cs:100, sheet2 row cs:105
    s1 = [sheet1_row("ITEMX")]
    s2, items, opts = ["ITEMX\tA\tC1\tD\t\t\t\t4"], ["[undefined]"], [-1]
    db = make_db(
        {"ITEMX": [{"productcategoryid": 5}, {"productcategoryid": 6}]},
        {("ITEMX", "5"): [
            {"material": "MAT1", "description": "Desc 1", "qty": Decimal("2.0000")},
            {"material": "MAT2", "description": None, "qty": 1},
        ]},
    )
    be, ok = run(db, s1, s2, items, opts)
    assert ok
    # num6 starts 2, row col0==ITEMX col7=4 >=2 -> num6=5 (cs:93-96)
    assert s2[1] == "ITEMX\t\tMAT1\t\t0\t2.0000\t0\t5\t\t\t10\t"
    assert s2[2] == "ITEMX\t\tMAT2\t\t0\t1\t0\t6\t\t\t10\t"
    assert len(s2) == 3
    f = s1[1].split("\t")
    assert len(f) == 58
    assert f[:3] == ["MAT1", "no", "Desc 1"]
    assert f[3:10] == ["A", "", "0", "0", "", "", "ZZ-ZZ"]
    assert f[10:19] == ["0", "0", "yes", "35", "0", "0", "", "", ""]
    assert f[19:27] == ["DEF", "1", "0", "EA", "", "P", "", "no"]
    assert f[27:33] == ["", "", "", "", "0", "0"]
    assert all(x == "" for x in f[33:])
    assert s1[2].split("\t")[2] == ""  # DBNull description
    # catalogue lookup used first row's category (cs:81-82); connection name documented
    mat_calls = [c for c in db.calls if BOM in c[1]]
    assert mat_calls[0][0] == BOM_CONNECTION
    assert mat_calls[0][2] == ("ITEMX", "5")
    assert "exec MaterialBOM 1, ?, ?, 0" in mat_calls[0][1]


def test_pass3_default_num6_is_two_and_duplicates_not_added():
    s1 = [sheet1_row("ITEMX")]
    s2, items, opts = [], [], []
    mat = {"material": "MAT1", "description": "D", "qty": 3}
    db = make_db({"ITEMX": [{"productcategoryid": 5}]}, {("ITEMX", "5"): [mat, mat]})
    be, ok = run(db, s1, s2, items, opts)
    assert ok
    assert s2 == ["ITEMX\t\tMAT1\t\t0\t3\t0\t2\t\t\t10\t", "ITEMX\t\tMAT1\t\t0\t3\t0\t3\t\t\t10\t"]  # cs:101-107
    assert len(s1) == 2  # Contains() check -> single sheet1 row added
    # sheet2Items untouched, so phase 4 processes nothing (num8 from sheet2Items.Count)
    assert items == []


def test_pass3_skips_non_M_and_9_prefixed_items_and_no_rows():
    s1 = [sheet1_row("ITEMA", "X"), sheet1_row("9-ITEMB", "M"), sheet1_row("ITEMC")]
    db = make_db({"ITEMC": []})
    be, ok = run(db, s1, [], [], [])
    assert ok
    assert [c[2] for c in db.calls] == [("ITEMC",)]  # no category rows -> no MaterialBOM (cs:79)
    assert len(s1) == 3


def test_pass3_empty_material_bom_result_adds_nothing():
    s1 = [sheet1_row("ITEMC")]
    s2 = []
    db = make_db({"ITEMC": [{"productcategoryid": 1}]}, {("ITEMC", "1"): []})
    be, ok = run(db, s1, s2, [], [])
    assert ok and s2 == [] and len(s1) == 1  # cs:86


def test_pass4_option_bom_rows():
    # cs:113-159 / row texts cs:147,152
    s2 = ["PAR\tA\tC1\tD\t\t\t\t3", "9-A-ITM-D\tA\tZ9\tF\t\t\t\t6"]
    items = ["ITM", "I2"]
    opts = [77, -1]
    s1 = []
    db = make_db(
        {"ITM": [{"productcategoryid": 9}]},
        {("ITM", "9", "77"): [{"material": "MX", "description": None, "qty": 1}]},
    )
    be, ok = run(db, s1, s2, items, opts)
    assert ok
    assert s2[0] == "PAR\tA\t9-A-ITM-D\tD\t\t\t\t3"
    assert s2[1] == "9-A-ITM-D\tA\t9-A-I2-F\tF\t\t\t\t6"
    # num10: row1 col0 == left("9-A-ITM-D") and 6>=2 -> 7 (cs:140-143); value2 begins with array7[2] (cs:152)
    assert s2[2] == "9-A-ITM-D\t\tMX\t\t0\t1\t0\t7\t\t\t10\t"
    assert len(s2) == 3
    assert s1[0].split("\t")[:3] == ["MX", "no", ""]
    bom_calls = [c for c in db.calls if BOM in c[1]]
    assert len(bom_calls) == 1
    assert bom_calls[0][2] == ("ITM", "9", "77")
    assert "exec MaterialBOM 1, ?, ?, ?" in bom_calls[0][1]


def test_pass4_default_num10_is_two():
    s2, items, opts = ["PAR\tA\tC1\tD\t\t\t\t3"], ["ITM"], [-1]
    db = make_db({"ITM": [{"productcategoryid": 9}]}, {("ITM", "9", "-1"): [{"material": "MX", "description": "d", "qty": 1}]})
    be, ok = run(db, [], s2, items, opts)
    assert ok
    assert s2[1] == "9-A-ITM-D\t\tMX\t\t0\t1\t0\t2\t\t\t10\t"


def test_sql_is_parameterised():
    item = "O'X"
    s1 = [sheet1_row(item)]
    db = make_db({item: [{"productcategoryid": 5}]}, {(item, "5"): [{"material": "M'1", "description": "d", "qty": 1}]})
    be, ok = run(db, s1, [], [], [])
    assert ok
    assert len(db.calls) == 2
    for conn, sql, params, stage in db.calls:
        assert conn == BOM_CONNECTION
        assert "O'X" not in sql and "5" not in sql.replace("exec MaterialBOM 1", "").replace("0", "")
        assert item in params


# --- legacy failure behaviour: catch (Exception) -> MsgBox, return false (cs:162-169) ---------------

def test_empty_replace_text_returns_false_and_reports():
    # array2[2]=="" -> string.Replace("", ..) throws ArgumentException in .NET
    errs = []
    be, ok = run(make_db(), [], ["P\tA\t\tD"], ["i"], [1], errs)
    assert ok is False
    assert errs and errs[0][0] == "SytelineBOMExport.generateBOMData"
    assert isinstance(errs[0][1], ValueError)
    assert be.errors


def test_short_row_returns_false():
    errs = []
    be, ok = run(make_db(), [], ["P\tA\tC"], ["i"], [1], errs)  # array2[3] missing
    assert ok is False and isinstance(errs[0][1], IndexError)


def test_sheet1_short_row_evaluated_even_when_9_prefixed():
    # cs:71 uses non-short-circuit '&' so array5[24] is read for "9-" items too
    errs = []
    be, ok = run(make_db(), ["9-X\ta"], [], [], [], errs)
    assert ok is False and isinstance(errs[0][1], IndexError)


def test_bad_seq_number_raises_format_error():
    # cs:93: Conversions.ToDouble(array6[7]) on non-numeric
    s1 = [sheet1_row("ITEMX")]
    s2, items, opts = ["ITEMX\tA\tC1\tD\t\t\t\tnotnum"], ["i"], [1]
    db = make_db({"ITEMX": [{"productcategoryid": 5}]}, {("ITEMX", "5"): [{"material": "M", "description": "d", "qty": 1}]})
    errs = []
    be, ok = run(db, s1, s2, items, opts, errs)
    assert ok is False
    assert isinstance(errs[0][1], LegacyFormatError)


def test_failure_leaves_partial_mutation_in_place():
    # Lists are shared with the caller; legacy keeps whatever was mutated before the exception.
    s2 = ["P\tA\tC1\tD\t\t\t\t1", "Q\tA\t\tD"]
    items = ["a", "b"]
    be, ok = run(make_db(), [], s2, items, [1, 2])
    assert ok is False
    assert s2[0] == "P\tA\t9-A-a-D\tD\t\t\t\t1"


def test_works_without_error_callback():
    be, ok = run(make_db(), [], ["P\tA"], ["i"], [1])
    assert ok is False and be.errors
