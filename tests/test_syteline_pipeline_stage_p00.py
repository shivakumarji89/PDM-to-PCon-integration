"""Tests for stage P00 (ExportThread.cs 2096-2473). All fixtures are synthetic."""
from __future__ import annotations

import pytest

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.io_output import IoMixin
from services.syteline_export.pipeline.netsem import LegacyFormatError
from services.syteline_export.pipeline.run_base import ExportRunBase, Flow
from services.syteline_export.pipeline.stage_p00_setup import P00Mixin


class H(P00Mixin, IoMixin, ExportRunBase):
    base = ""

    def allocate_files(self):
        b = self.base
        self._itemFile = b + "item.txt"
        self._superprodFile = b + "sp.txt"
        self._planningFile = b + "plan.txt"
        self._descriptionFile = b + "desc.txt"

    @staticmethod
    def _environment_user_name():
        return "tester"


ITEM_Q = "SELECT DISTINCT Item.Item AS LongItem"


def make(tmp_path, items=None, script=None, **fields):
    items = items if items is not None else [{"LongItem": "A1"}, {"LongItem": "B2"}]
    s = {
        "SELECT ExtractUser": [],
        "UPDATE Site SET ExtractUser": 1,
        "FROM CatalogueOptionValues": [],
        "SELECT OptionValueId FROM OptionValue": [],
        "FROM CatalogueProductOptionExclusions": [],
        "FROM CatalogueItemOptionExclusions": [],
        "FROM Language": [],
        ITEM_Q: items,
    }
    s.update(script or {})
    h = H(ScriptedExportDb(s))
    h.base = str(tmp_path) + "/"
    h._siteId = 3
    h._catalogueId = 50
    h._languageId = 1
    h._otherlanguageId = 2
    h._currency = "GBP"
    h._effectiveDate = "2024-01-31"
    for k, val in fields.items():
        setattr(h, k, val)
    return h


def sql_calls(h, needle):
    return [c for c in h.db.calls if needle in c[1]]


def test_basic_non_syteline_headers_and_item_query(tmp_path):
    h = make(tmp_path)
    assert h.p00_setup() is None
    v = h.v
    # 2147-2153: three files get headers, planning is closed after its header
    assert (tmp_path / "plan.txt").read_text(encoding="utf-8").startswith("Item\tDescription\tProduct Code")
    v.streamWriter2.close()
    v.streamWriter4.close()
    assert (tmp_path / "sp.txt").read_text(encoding="utf-8").startswith("Item\tSuper Description\tSeq")
    assert (tmp_path / "desc.txt").read_text(encoding="utf-8").startswith("Lang\tItem\tDescription")
    assert v.text2.startswith("\tFeat1\tFeat2") and v.text2.endswith("\tFeat20")
    # 2438-2441 count pass and 2473 main pass: query executed twice
    assert len(sql_calls(h, ITEM_Q)) == 2
    assert v.arrayList23 == ["A1", "B2"] and v.item_count == 2
    assert [r["LongItem"] for r in v.item_rows] == ["A1", "B2"]
    assert v.num5 == 0 and v.right == "" and v.text4 == ""
    assert v.text9 == "'2024-01-31'" and v.text5 == "no" and v.flag3 is True
    # no preload for non-SyteLine (2248)
    assert not sql_calls(h, "CatalogueOptionValues")
    assert h.threadStage == "8"
    # not SyteLine: UNION of released/unreleased (2420-2423), params duplicated
    q = sql_calls(h, ITEM_Q)[0]
    assert " UNION " in q[1]  # no CatalogueItems join in this mode, so both halves are identical
    assert len(q[2]) == 2 * q[1].split(" UNION ")[0].count("?")


def test_millercad_and_csi_skip_extra_files(tmp_path):
    h = make(tmp_path, _millerCAD=True)
    h.p00_setup()
    assert h.v.streamWriter2 is None and h.v.streamWriter4 is None
    assert not (tmp_path / "sp.txt").exists()


def test_item_file_open_failure_returns(tmp_path):
    h = make(tmp_path)
    h.base = str(tmp_path / "missing") + "/"  # directory does not exist -> open fails (2115-2125)
    assert h.p00_setup() is Flow.RETURN
    assert any("Unable to open the file" in e for e in h.errors)
    assert not h.db.calls


def test_extract_user_read_and_unconditional_update(tmp_path):
    # 2228-2242: last row wins, dead guard never aborts, UPDATE always runs with the current user
    h = make(tmp_path, script={"SELECT ExtractUser": [{"ExtractUser": "bob"}, {"ExtractUser": None}, {"ExtractUser": "alice"}]})
    assert h.p00_setup() is None
    assert h.v.text4 == "alice"
    upd = sql_calls(h, "UPDATE Site SET ExtractUser")[0]
    assert upd[0] == "c1" and upd[2] == ("tester", 3) and "tester" not in upd[1]
    assert sql_calls(h, "SELECT ExtractUser")[0][2] == (3,)


def test_syteline_preloads(tmp_path):
    script = {
        "FROM CatalogueOptionValues": [
            {"OptionValueId": 10, "OptionId": 1}, {"OptionValueId": "11", "OptionId": 1},
            {"OptionValueId": 284979, "OptionId": 2},
        ],
        "SELECT OptionValueId FROM OptionValue": [{"OptionValueId": 5}, {"OptionValueId": 6}],
        "FROM CatalogueProductOptionExclusions": [
            {"ProductId": 7, "OptionValueId": 100, "OrderCodeValue": "0Y#", "colourId": None},
            {"ProductId": 7, "OptionValueId": 101, "OrderCodeValue": "0#", "colourId": 201},
            {"ProductId": 7, "OptionValueId": 102, "OrderCodeValue": "0Y#", "colourId": 202},
            {"ProductId": 8, "OptionValueId": 103, "OrderCodeValue": "XX", "colourId": 203},
        ],
        "FROM CatalogueItemOptionExclusions": [{"ItemId": 9, "OptionValueId": 4}],
        "FROM Language": [{"CultureCode": "fr-FR"}, {"CultureCode": "zz"}],
    }
    h = make(tmp_path, script=script, _syteline=True, _exportBasePrices=True)
    h.p00_setup()
    v = h.v
    assert v.arrayList16 == [10, 11, 284979]  # catalogue 50 is not Knoll (2264)
    assert v.arrayList18 == [5, 6]
    # 2303-2322: 0Y# row with colour 202 is added then removed because "0#" is present; 0# (colour 201)
    # processed when "0Y#" already seen -> removed too (text12 = 7~201); 7~100? (no colourId) stays.
    assert v.arrayList19 == ["7~100", "7~101", "7~102", "8~103", "8~203"]
    assert v.arrayList20 == ["9~4"]
    assert v.text3 == "fr-FR"  # first row only (2345)
    lang = sql_calls(h, "FROM Language")[0]
    assert lang[0] == "c5" and lang[2] == ("2",)
    assert h.threadStage == "8"


def test_knoll_catalogue_removes_option_values(tmp_path):
    script = {"FROM CatalogueOptionValues": [
        {"OptionValueId": 284979, "OptionId": 1}, {"OptionValueId": 286214, "OptionId": 1},
        {"OptionValueId": 286909, "OptionId": 1}, {"OptionValueId": 5, "OptionId": 1}]}
    h = make(tmp_path, script=script, _syteline=True, _catalogueId=649)
    h.p00_setup()
    assert h.v.arrayList16 == [5]


def test_language_without_rows_leaves_empty_culture(tmp_path):
    h = make(tmp_path, _syteline=True)
    h.p00_setup()
    assert h.v.text3 == ""


def test_malformed_option_value_id_throws(tmp_path):
    h = make(tmp_path, script={"FROM CatalogueOptionValues": [{"OptionValueId": "abc", "OptionId": 1}]}, _syteline=True)
    with pytest.raises(LegacyFormatError):
        h.p00_setup()


def test_listprice_column_and_params(tmp_path):
    h = make(tmp_path, _syteline=True, _exportBasePrices=False, _activeOnly=True, _catalogueId=50)
    h.p00_setup()
    q = sql_calls(h, ITEM_Q)[0]
    assert "dbo.fnGetListPriceByItem(Item.Item, ?, ?, ?, NULL) AS ListPrice" in q[1]
    # maxDesc x3, then currency, date, siteId, lang x2, otherlang, site, catalogue (2354-2397)
    assert q[2] == (200, 200, 200, "GBP", "2024-01-31", 3, 1, 1, 2, 3, 50)
    assert q[1].endswith("AND Product.Status = 1 AND Item.Status = 1  ORDER BY Item.Item")
    assert " UNION " not in q[1]  # activeOnly: no unreleased union (2420)
    assert "2024-01-31" not in q[1]


def test_product_check_range_list_branches(tmp_path):
    h = make(tmp_path, _productCheck=True, _productCodeId=9, _rangeCheck=True, _listCheck=True)
    h.p00_setup()
    q = sql_calls(h, ITEM_Q)[0]
    assert "And pc.ProductCodeId = ? And CatalogueItems.CatalogueId = ?" in q[1] and "Item.Item >" not in q[1]
    assert q[2][-2:] == (9, 50)

    h = make(tmp_path, _rangeCheck=True, _minItem="AA", _maxItem="ZZ", _syteline=True)
    h.p00_setup()
    q = sql_calls(h, ITEM_Q)[0]
    assert "(Item.Item > ? OR Item.Item LIKE ?) AND (Item.Item < ? OR Item.Item LIKE ?)" in q[1]
    assert ("AA", "AA%", "ZZ", "ZZ%", 50) == q[2][7:12]
    assert "AA" not in q[1]

    h = make(tmp_path, _rangeCheck=True, _minItem="BRW", _maxItem="BRW")
    h.p00_setup()
    q = sql_calls(h, ITEM_Q)[0]
    assert "Item.Item = 'BREF.CL'" in q[1] and "Item.Item >" not in q[1]

    h = make(tmp_path, _listCheck=True, _itemList=["X1", "O'Y"], _activeOnly=True)
    h.p00_setup()
    q = sql_calls(h, ITEM_Q)[0]
    assert "AND (Item.Item = ? OR Item.Item = ?) " in q[1] and "O'Y" not in q[1]
    assert q[2][-2:] == ("X1", "O'Y")


def test_listcheck_empty_list_adds_nothing(tmp_path):
    h = make(tmp_path, _listCheck=True, _itemList=[], _activeOnly=True)
    h.p00_setup()
    assert "AND (" not in sql_calls(h, ITEM_Q)[0][1]


def test_millercad_branches(tmp_path):
    h = make(tmp_path, _millerCAD=True, _exportAllCataloguesInSite=True, _activeOnly=True)
    h.p00_setup()
    q = sql_calls(h, ITEM_Q)[0]
    assert "INNER JOIN Catalogue ON" in q[1] and "AND Catalogue.PrimarySiteId = ? " in q[1]
    assert "ListPrice" in q[1] and q[2][-1] == 3
    h = make(tmp_path, _millerCAD=True, _activeOnly=True)
    h.p00_setup()
    assert "AND CatalogueItems.CatalogueId = ? " in sql_calls(h, ITEM_Q)[0][1]


def test_itemreport_branches(tmp_path):
    h = make(tmp_path, _itemreport=True, _activeOnly=True)
    h.p00_setup()
    q = sql_calls(h, ITEM_Q)[0]
    assert "AND CatalogueItems.CatalogueId = ? " in q[1] and "LEFT OUTER JOIN CatalogueItems" not in q[1]

    h = make(tmp_path, _itemreport=True, _activeOnly=False)
    h.p00_setup()
    q = sql_calls(h, ITEM_Q)[0]
    first = q[1].split(" UNION ")[0]
    assert "LEFT OUTER JOIN CatalogueItemsUnreleased ON Item.ItemId" in first
    assert "(CatalogueItems.CatalogueId = ? OR CatalogueItemsUnreleased.CatalogueId = ?)" in first
    # legacy defect preserved: the union's Replace re-expands the already-expanded name
    assert "CatalogueItemsUnreleasedUnreleased" in q[1]
    assert len(q[2]) == 2 * first.count("?")


def test_exclude_super_products_union(tmp_path):
    h = make(tmp_path, _syteline=True, _activeOnly=True, _excludeSuperProducts=True)
    h.p00_setup()
    q = sql_calls(h, ITEM_Q)[0]
    first, third = q[1].split(" UNION ")
    assert "INNER JOIN Item sp_item ON itco.ItemId = sp_item.ItemId" in third
    assert "WHERE pc.SiteId = ? " in third and third.endswith(" AND sp_item.Status = 1 ORDER BY Item.Item")
    assert "Item.Item AS LongItem" in third and "sp_item.Item AS LongItem" not in third
    assert len(q[2]) == 2 * first.count("?")


def test_description_length_millercad_bound(tmp_path):
    h = make(tmp_path, _millerCAD=True, _maxDescriptionLength=40)
    h.p00_setup()
    assert sql_calls(h, ITEM_Q)[0][2][:3] == (40, 40, 40)


def test_sql_is_parameterised(tmp_path):
    h = make(tmp_path, _syteline=True, _effectiveDate="2099-12-31", _currency="XYZ",
             script={"FROM Language": [{"CultureCode": "q"}]})
    h.p00_setup()
    for _conn, sql, params, _stage in h.db.calls:
        assert "2099-12-31" not in sql and "XYZ" not in sql and "tester" not in sql
    stages = [c[3] for c in h.db.calls]
    assert stages[0] == "1" and "2" in stages and stages[-1] == "8"


def test_resets_run_state_and_status(tmp_path):
    h = make(tmp_path)
    h._abortThread = True
    h._itemsWritten = ["old"]
    h.p00_setup()
    assert h._abortThread is False and h._itemsWritten == [] and h.materialsWritten == []
    assert h.skippedFabricColours == [] and h.sequenceForItems == [] and h.sequenceForItemsIndexes == []
    assert h.v.num4 == 0 and all(getattr(h.v, "arrayList%d" % n) == [] for n in range(24, 45))


def test_timer_not_started_when_processing_queue(tmp_path):
    seen = []
    h = H(ScriptedExportDb({}), timer_callback=seen.append)
    h.base = str(tmp_path / "missing") + "/"
    h._parent.processingQueue = True
    h.p00_setup()
    assert seen == ["stop"]  # only the failure path stops the timer (2122)
    h = H(ScriptedExportDb({}), timer_callback=seen.append)
    h.base = str(tmp_path / "missing") + "/"
    seen.clear()
    h.p00_setup()
    assert seen == ["reset", "start", "stop"]
