"""Tests for stage P01 (ExportThread.cs 2475-2606). All fixtures are synthetic."""
from decimal import Decimal

import pytest

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.netsem import LegacyFormatError
from services.syteline_export.pipeline.run_base import ExportRunBase, Flow
from services.syteline_export.pipeline.stage_p01_item_head import P01Mixin


class H(P01Mixin, ExportRunBase):
    def get_feature_count(self, superproduct):
        self.fc_calls.append(superproduct)
        return 7

    def get_short_product_code(self, prodcode, rootproduct):
        return f"{prodcode}/{rootproduct}"


def make(script=None, **fields):
    h = H(ScriptedExportDb({"PDMOptionDataReport": [], **(script or {})}))
    h.fc_calls = []
    h.status = []
    h._status_callback = h.status.append
    v = h.v
    v.num5 = 0
    v.arrayList23 = ["a", "b", "c"]
    v.arrayList27 = []
    v.arrayList28 = []
    v.right = ""
    v.num3 = 0
    v.flag3 = True
    for k, val in fields.items():
        setattr(h, k, val)
    return h


def row(**kw):
    base = dict(Item="X1", LongItem="LONG1", IsSuperProduct="False", Product="P", Height="1", Width="2",
                Depth="3", Product_Code="PC", MyBasePrice=Decimal("100"), ProductId=1, ItemId=2)
    base.update(kw)
    return base


def test_mk1_o_exception_and_exclude_super():  # cs 2478, 2489
    h = make(_excludeSuperProducts=True)
    h.v.sqlDataReader = row(Item="MK1ABCO", IsSuperProduct="True")
    assert h.p01_item_head() is None and h.v.flag4 is True
    h2 = make(_excludeSuperProducts=True)
    h2.v.sqlDataReader = row(Item="MK1ABC", IsSuperProduct="True")
    assert h2.p01_item_head() is Flow.NEXT_ITEM and h2.v.flag4 is False
    assert h2.v.num5 == 1 and h2.status == []  # skipped before the status label (2493)


def test_super_products_only_skips_non_super():  # cs 2489 second clause
    h = make(_superProductsOnly=True)
    h.v.sqlDataReader = row(IsSuperProduct="False")
    assert h.p01_item_head() is Flow.NEXT_ITEM


def test_bad_bool_throws():  # bool.Parse
    h = make()
    h.v.sqlDataReader = row(IsSuperProduct="maybe")
    with pytest.raises(LegacyFormatError):
        h.p01_item_head()


def test_header_fields_and_feature_count_and_status():  # cs 2493-2515
    h = make(_exportMaterialsForPDMReport=False, _catalogueId=5)
    h.v.sqlDataReader = row(IsSuperProduct="True", Item="S1", LongItem="LS", Product="PX")
    h.materialstr = "old"
    assert h.p01_item_head() is None
    v = h.v
    assert h.status == ["LS\r\n(1 of 3)"]
    assert h.fc_calls == ["LS"] and v.num3 == 7 and v.right == "PX"
    assert (v.text16, v.text17, v.text18) == ("1", "2", "3")
    assert v.rootproduct == "PX" and v.prodcode == "PC"
    assert v.text6 == "BOCFAB[PC/PX]"
    assert h.materialstr == "" and v.num6 == 1 and v.text19 == "" and v.text20 == ""
    assert v.arrayList3 == [] and v.arrayList46 == []
    assert v.option_rows is None
    # same product again: no new getFeatureCount
    h.v.sqlDataReader = row(IsSuperProduct="True", Item="S2", Product="PX")
    h.p01_item_head()
    assert h.fc_calls == ["LS"]


def test_text6_bocfab_plain_when_catalogue_229_or_flag3_false():  # cs 2504
    for cat, f3 in ((229, True), (5, False)):
        h = make(_exportMaterialsForPDMReport=False, _catalogueId=cat)
        h.v.flag3 = f3
        h.v.sqlDataReader = row()
        h.p01_item_head()
        assert h.v.text6 == "BOCFAB"


def test_option_report_sql_and_params():  # cs 2583-2606
    rows = [{"Option2": "o"}]
    h = make({"PDMOptionDataReport": rows}, _catalogueId=5)
    h.v.sqlDataReader = row(LongItem="LONG'1", Item="X1")
    h.v.arrayList27 = ["PC"]
    h.v.arrayList28 = [Decimal("1.5")]
    h.p01_item_head()
    conn, sql, params, stage = h.db.calls[-1]
    assert conn == "c2" and stage == "10" and params == ("LONG'1",)
    assert "LONG'1" not in sql and "DECLARE C1" not in sql
    assert sql.endswith("DROP TABLE #temptable") and "len(OrderCodeValue2) DESC" in sql
    assert h.v.option_rows == rows and h.v.num4 == Decimal("1.5")
    assert [c for c in h.db.calls if c[0] == "tradenet"] == []


def test_flatten_fabrics_and_OF_replace():  # cs 2584, 2590
    h = make(_flattenFabrics=True)
    h.v.sqlDataReader = row(Item="OF123")
    h.v.arrayList27, h.v.arrayList28 = ["PC"], [Decimal(0)]
    h.p01_item_head()
    sql = h.db.calls[-1][1]
    assert "DECLARE C1 CURSOR" in sql
    assert "len(REPLACE(OrderCodeValue2, '9B', '9B__'))" in sql
    assert "len(OrderCodeValue2)" not in sql


def test_not_entered_when_super_only_false_flag():  # cs 2517
    h = make(_exportMaterialsForPDMReport=False)
    h.v.sqlDataReader = row()
    h.p01_item_head()
    assert h.db.calls == [] and h.v.option_rows is None


def test_tradenet_discount_computed_cached_from_first_item():  # cs 2537-2581
    script = {"FROM dbo.Contract": [{"Contract_ID": "K", "Product_Code": "PC", "Purchase_Discount": Decimal("12.5")}]}
    h = make(script, _contract="K1", _tradeNet="TN")
    h.v.sqlDataReader = row(MyBasePrice=Decimal("100.10"))
    h.p01_item_head()
    # 100.10 * (1 - 0.125) = 87.5875 -> round(2) = 87.59
    assert h.v.num4 == Decimal("87.59")
    tn = [c for c in h.db.calls if c[0] == "tradenet"]
    assert len(tn) == 1 and tn[0][2] == ("PC", "K1") and "PC" not in tn[0][1] and tn[0][3] == "9"
    assert h.v.arrayList27 == ["PC"] and h.v.arrayList28 == [Decimal("87.59")]
    # second item, same Product_Code, different price: cached value reused (legacy defect), no query
    h.v.sqlDataReader = row(MyBasePrice=Decimal("999"))
    h.p01_item_head()
    assert h.v.num4 == Decimal("87.59")
    assert len([c for c in h.db.calls if c[0] == "tradenet"]) == 1


def test_tradenet_bankers_rounding():  # Math.Round midpoint -> even
    script = {"FROM dbo.Contract": [{"Purchase_Discount": Decimal("50")}]}
    h = make(script, _contract="K")
    h.v.sqlDataReader = row(MyBasePrice=Decimal("0.25"))  # 0.125 -> 0.12
    h.p01_item_head()
    assert h.v.num4 == Decimal("0.12")


def test_tradenet_null_price_gives_zero_and_no_rows_gives_zero():  # cs 2559, 2544
    script = {"FROM dbo.Contract": [{"Purchase_Discount": Decimal("10")}]}
    h = make(script)
    h.v.sqlDataReader = row(MyBasePrice=None)
    h.p01_item_head()
    assert h.v.num4 == Decimal(0)
    h2 = make({"FROM dbo.Contract": []})
    h2.v.sqlDataReader = row()
    h2.p01_item_head()
    assert h2.v.num4 == Decimal(0) and h2.v.arrayList28 == [Decimal(0)]


def test_tradenet_error_silently_zero_and_cached():  # cs 2568-2581 (legacy defect: error cached as 0)
    def boom(conn, sql, params):
        raise RuntimeError("no connect")

    h = make({"FROM dbo.Contract": boom})
    h.v.sqlDataReader = row()
    h.p01_item_head()
    assert h.v.num4 == Decimal(0) and h.v.arrayList28 == [Decimal(0)]
    assert h.errors == []  # legacy: no MsgBox, Debug.WriteLine only
    assert h.v.option_rows == []  # processing continues to the option report


def test_tradenet_dbnull_discount_throws_into_catch():  # VB DBNull <> 0 throws InvalidCast -> catch
    h = make({"FROM dbo.Contract": [{"Purchase_Discount": None}]})
    h.v.sqlDataReader = row()
    h.p01_item_head()
    assert h.v.num4 == Decimal(0)


def test_tradenet_float_discount():
    h = make({"FROM dbo.Contract": [{"Purchase_Discount": 20.0}]})
    h.v.sqlDataReader = row(MyBasePrice=50.0)
    h.p01_item_head()
    assert h.v.num4 == Decimal("40.0")


def test_option_report_failure_propagates():  # no catch around ExecuteReader in legacy range
    def boom(conn, sql, params):
        raise RuntimeError("sql")

    h = make({"PDMOptionDataReport": boom})
    h.v.sqlDataReader = row()
    h.v.arrayList27, h.v.arrayList28 = ["PC"], [Decimal(0)]
    with pytest.raises(RuntimeError):
        h.p01_item_head()
