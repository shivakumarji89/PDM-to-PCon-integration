"""Stage P01: head of the per-item loop body of ExportThread.execThread (ExportThread.cs 2475-2606).

Mechanical transliteration; see PORTING_CONVENTIONS.md. The loop header (2474) belongs to the caller,
which sets ``v.sqlDataReader`` to the current item row before calling ``p01_item_head``.
"""
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_EVEN

from services.syteline_export.pipeline.netsem import (
    list_index_of,
    net_bool,
    tostr,
)
from services.syteline_export.pipeline.run_base import Flow

LOGGER = logging.getLogger("syteline_export")


def _vb_one_minus_over_100(discount):
    """Conversions.ToDecimal(Operators.SubtractObject(1, Operators.DivideObject(discount, 100)))."""
    if isinstance(discount, Decimal):
        return Decimal(1) - discount / Decimal(100)
    # int / int and double / int are Double in VB; ToDecimal of a double
    return Decimal(format(1 - float(discount) / 100.0, '.15g'))  # Convert.ToDecimal(double): 15 digits


def _vb_multiply(a, b):
    """Operators.MultiplyObject(a, b) where b is a Decimal."""
    if isinstance(a, float):
        return a * float(b)
    return Decimal(a) * b


def _math_round2_to_decimal(x):
    """Conversions.ToDecimal(Math.Round(x, 2)) (banker's rounding)."""
    if isinstance(x, float):
        return Decimal(format(round(x, 2), '.15g'))
    return Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


_TEMPTABLE_CREATE = (
    "SET NOCOUNT ON "  # only addition vs legacy: pyodbc would expose CREATE/INSERT counts as result sets
    "CREATE TABLE #temptable (Range2 varchar(100), ProductId INT, Product2 varchar(100), Option2 varchar(100), OptDescId INT, OptionId INT, OrderCodeFormatKey varchar(10), OptionValueId INT, OrderCodeValue2 varchar(20), Status INT, ParentOptId INT, ParentOptDescId INT, ParentOptName varchar(100), ParentOptValId INT, ParentOptValDescId INT, ParentOptValName varchar(100), ParentOptValCode varchar(20), ParentOptIsFabric INT, ParentDisplayOrder INT, DisplayOrder INT, EOSLiteDisplayOrder INT, DisplayOrdinal BIGINT, TertiayOption INT, IsFabric INT, optval_name varchar(100), optvalDescId INT, ImageFile varchar(255), ProductCategoryId INT, PriceBand INT) "
    "INSERT INTO #temptable execute PDMOptionDataReport ? "  # legacy: '" + LongItem + "' (bound)
)
_FLATTEN_FABRICS = "DECLARE @optvalId INT DECLARE @parentoptvalId INT DECLARE @parentoptvalcode varchar(20) DECLARE C1 CURSOR read_only FOR SELECT OptionValueId, ParentOptValId, ParentOptValCode FROM #temptable WHERE ParentOptValId IS NOT NULL AND IsFabric = 2 AND OrderCodeValue2 NOT LIKE '%#' OPEN C1 FETCH NEXT FROM C1 INTO @optvalId, @parentoptvalId, @parentoptvalcode While @@FETCH_STATUS = 0 BEGIN     DECLARE @newparentoptvalId INT     SET @newparentoptvalId = NULL     SELECT @newparentoptvalId = ParentOptValId FROM #temptable WHERE OptionValueId = @parentoptvalId     UPDATE #temptable SET ParentOptValId = @newparentoptvalId WHERE OptionValueId = @optvalId     UPDATE #temptable SET IsFabric = 1 WHERE OptionValueId = @optvalId AND IsFabric = 2     FETCH NEXT FROM C1 INTO @optvalId, @parentoptvalId, @parentoptvalcode END CLOSE C1 DEALLOCATE C1 "
_SELECT = "SELECT DISTINCT Range2, ProductId, Product2, Option2, OptDescId, #temptable.OptionId, OrderCodeFormatKey, #temptable.OptionValueId, CASE WHEN ParentOptValId IN (149730, 195468) THEN 'm' + OrderCodeValue2 /* Worksurfaces - Matching */ WHEN ParentOptValId IN (194397, 195469) THEN 'c' + OrderCodeValue2 /* Worksurfaces - Contrast */ WHEN ParentOptValId IN (197074, 197077) THEN 'm' + OrderCodeValue2 /* Wooden Panel - Matching */ WHEN ParentOptValId IN (197075, 197076) THEN 'c' + OrderCodeValue2 /* Wooden Panel - Contrast */ WHEN ParentOptValId IN (197237, 197329) THEN 'm' + OrderCodeValue2 /* Shelf - Matching */ WHEN ParentOptValId IN (197238, 197240) THEN 'c' + OrderCodeValue2 /* Shelf - Contrast */ ELSE OrderCodeValue2 END AS OrderCodeValue2, #temptable.Status, DisplayOrder, #temptable.DisplayOrdinal, TertiayOption, IsFabric, optval_name, optvalDescId, ParentOptValId, ParentOptValCode, CASE WHEN CHARINDEX('customers own', optval_name) > 0 /***OR OrderCodeValue2 = 'L80'***/ THEN 1 ELSE dbo.fnOptionChildCount(#temptable.OptionValueId) END AS OptChildCount, child_optval.OptionId AS OptChildId, #temptable.ImageFile, ProductCategoryId, PriceBand, optval.fsccompliant, len(OrderCodeValue2) FROM #temptable INNER JOIN OptionValue optval ON #temptable.OptionValueId = optval.OptionValueId LEFT OUTER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.OptionValueId LEFT OUTER JOIN OptionValue child_optval ON dov.AdditionalOptionValueId = child_optval.OptionValueId "
_ORDER_DROP = "ORDER BY Range2, Product2, DisplayOrder, len(OrderCodeValue2) DESC, #temptable.DisplayOrdinal DROP TABLE #temptable"

_TRADENET_SQL = (
    "SELECT DISTINCT Contract_ID, Product_Code, Purchase_Discount FROM dbo.Contract WITH (NOLOCK) "
    "WHERE Product_Code = ? AND Contract_ID = ?"
)


class P01Mixin:
    def p01_item_head(self) -> Flow | None:
        v = self.v
        # ---- ExportThread.cs 2476-2481
        v.num5 += 1  # item counter (declared at 2454, owned by the caller's setup)
        v.flag4 = False  # MK1*O exception to the super-product exclusion
        if tostr(v.sqlDataReader["Item"]).startswith("MK1") & tostr(v.sqlDataReader["Item"]).endswith("O"):
            v.flag4 = True
        # ---- 2487-2516 (unchecked block)
        if (
            (net_bool(v.sqlDataReader["IsSuperProduct"]) & self._excludeSuperProducts) and not v.flag4
        ) or ((not net_bool(v.sqlDataReader["IsSuperProduct"])) & self._superProductsOnly):
            return Flow.NEXT_ITEM
        self.update_status_label(
            tostr(v.sqlDataReader["LongItem"]) + "\r\n(" + str(v.num5) + " of " + str(len(v.arrayList23)) + ")"
        )
        if (tostr(v.sqlDataReader["Product"]) != v.right) & net_bool(v.sqlDataReader["IsSuperProduct"]):
            v.num3 = self.get_feature_count(tostr(v.sqlDataReader["LongItem"]))
        v.right = tostr(v.sqlDataReader["Product"])
        v.text16 = tostr(v.sqlDataReader["Height"])
        v.text17 = tostr(v.sqlDataReader["Width"])
        v.text18 = tostr(v.sqlDataReader["Depth"])
        v.rootproduct = tostr(v.sqlDataReader["Product"])
        v.prodcode = tostr(v.sqlDataReader["Product_Code"])
        if not (self._catalogueId == 229 or not v.flag3):
            v.text6 = "BOCFAB[" + self.get_short_product_code(v.prodcode, v.rootproduct) + "]"
        else:
            v.text6 = "BOCFAB"
        v.arrayList3 = []
        v.arrayList4 = []
        v.arrayList5 = []
        v.arrayList6 = []
        v.arrayList7 = []
        self.materialstr = ""
        v.arrayList45 = []
        v.arrayList46 = []
        v.text19 = ""
        v.num6 = 1
        v.text20 = ""

        # ---- 2517
        v.option_rows = None  # None = the `if` below was not entered (the 2607 loop and its block are skipped)
        if self._exportMaterialsForPDMReport & (not self._superProductsOnly):
            v.arrayList47 = []
            v.arrayList48 = []
            v.arrayList49 = []
            v.arrayList50 = []
            v.arrayList51 = []
            v.arrayList52 = []
            v.arrayList53 = []
            v.arrayList54 = []
            v.arrayList55 = []
            v.arrayList56 = []
            v.arrayList57 = []
            v.arrayList58 = []
            v.arrayList59 = []
            v.arrayList60 = []
            v.arrayList61 = []
            v.num7 = 0
            v.num8 = -1
            v.text21 = ""
            # ---- 2537-2582 trade-net discount, cached per Product_Code in arrayList27/28
            v.num9 = list_index_of(v.arrayList27, tostr(v.sqlDataReader["Product_Code"]))
            if v.num9 > -1:
                v.num4 = v.arrayList28[v.num9]
            else:
                v.num4 = Decimal(0)
                try:
                    # sqlConnection6 = new SqlConnection(database=_tradeNet; server=Global.connectedServer) -> "tradenet":
                    # the integrator must provide a "tradenet" session on database self._tradeNet.
                    v.mysql = _TRADENET_SQL
                    self.threadStage = "9"
                    for row6 in self.q("tradenet", v.mysql, (tostr(v.sqlDataReader["Product_Code"]), tostr(self._contract))):
                        discount = row6["Purchase_Discount"]
                        # Legacy: CompareObjectNotEqual(Purchase_Discount, 0) OR (Purchase_Discount != DBNull).
                        # VB compares DBNull with 0 first and throws InvalidCastException, swallowed below.
                        if discount is None:
                            raise TypeError("Conversion from type 'DBNull' to type 'Integer' is not valid.")
                        if (discount != 0) or (discount is not None):
                            v.num10 = _vb_one_minus_over_100(discount)
                            if v.sqlDataReader["MyBasePrice"] is None:
                                v.num4 = Decimal(0)
                            else:
                                v.num4 = _math_round2_to_decimal(_vb_multiply(v.sqlDataReader["MyBasePrice"], v.num10))
                except Exception as ex3:  # legacy catch (Exception): num4 = 0, Debug.WriteLine only
                    v.num4 = Decimal(0)
                    LOGGER.debug("Cannot connect to Tradenet Database (%s)", self._tradeNet)
                    # deviation: legacy is silent; the message is recorded (no behaviour change)
                    self.warnings.append(f"Cannot connect to Tradenet Database ({self._tradeNet}): {ex3}")
                # finally: sqlConnection6?.Close() -> session lifetime is owned by the Db
                v.arrayList27.append(tostr(v.sqlDataReader["Product_Code"]))
                v.arrayList28.append(v.num4)

            # ---- 2583-2593 option report SQL on c2 (sqlConnection2); #temptable is session scoped
            v.text21 = _TEMPTABLE_CREATE
            if self._flattenFabrics:
                v.text21 += _FLATTEN_FABRICS
            v.text21 += _SELECT
            v.text21 += _ORDER_DROP
            if tostr(v.sqlDataReader["Item"]).startswith("OF"):
                v.text21 = v.text21.replace("len(OrderCodeValue2)", "len(REPLACE(OrderCodeValue2, '9B', '9B__'))")
            # debug-only block omitted (flag default false)
            v.text22 = ""
            v.text23 = ""
            v.arrayList62 = []
            self.threadStage = "10"
            # CommandTimeout = 900 is the Db default.
            v.option_rows = self.q("c2", v.text21, (tostr(v.sqlDataReader["LongItem"]),))  # sqlDataReader2 rows
        return None
