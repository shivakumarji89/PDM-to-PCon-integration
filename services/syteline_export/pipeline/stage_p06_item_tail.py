"""ExportThread.cs 5009-5425: tail of the per-item loop body (stages 20.9, 21, 22, 23-23.3, 24).

Mechanical transliteration; see PORTING_CONVENTIONS.md.

CONTROL-FLOW NOTE: the C# ``else`` of stage 17.15b (line 4350) closes at line 5061, so the 20.9
write-out of ``materialstr`` (5009-5060) only runs when that ``else`` was taken.  The p05 chunk
records this in ``self.v.p05_else_branch``; this method reads it.  Lines 5062-5425 run for every
item (subject to the ``continue`` at 5062).

Helpers expected from other mixins: ``write_to_stream`` (IoMixin), ``write_data`` (IoMixin),
``get_feature_count`` (HelpersMiscMixin).  ``logMessage`` (static, no-op unless a developer-machine
hack is active) is omitted.
"""
from __future__ import annotations

import re

from services.syteline_export.pipeline.netsem import (
    LegacyFormatError,
    debug_feature_pos,  # noqa: F401  (kept for symmetry with sibling stages)
    debug_feature_template,
    debug_post_processed_feature_pos,
    index_of,
    is_knoll_catalogue,
    list_contains,
    list_index_of,
    net_double,
    net_int,
    substring,
    tostr,
)
from services.syteline_export.pipeline.run_base import Flow

_LONG_RE = re.compile(r"^[ \t\r\n]*[+-]?[0-9]+[ \t\r\n]*$", re.ASCII)


def _net_long(value) -> int:
    """``long.Parse(value.ToString())``."""
    text = tostr(value)
    if not _LONG_RE.match(text):
        raise LegacyFormatError(f"Input string was not in a correct format: {text!r}")
    number = int(text.strip())
    if not -(2 ** 63) <= number <= 2 ** 63 - 1:
        raise LegacyFormatError(f"Value was either too large or too small for an Int64: {text!r}")
    return number


def _pad2(number: int) -> str:
    """``(n >= 10) ? n.ToString() : "0" + n.ToString()``."""
    return str(number) if number >= 10 else "0" + str(number)


class P06Mixin:
    def p06_item_tail(self) -> Flow | None:
        v = self.v
        sqlDataReader = v.sqlDataReader  # current item row (dict)

        # debug-only block omitted (flag default false): logOutput "FULL materialstr" dialog (5009-5014)
        # ------------------------------------------------------------------ 20.9 (5015-5060)
        if v.p05_else_branch:
            self.threadStage = "20.9"
            text132 = "***"
            while len(self.materialstr) > 0:
                if index_of(self.materialstr, "\r\n") > -1:
                    text132 = substring(self.materialstr, 0, index_of(self.materialstr, "\r\n"))
                    if (index_of(text132, "BOCFAB") > -1) & (index_of(text132, "-CM01\t") > -1):
                        self.includesCOM = True
                    array11 = text132.split("\r")
                    for num129 in range(0, len(array11)):
                        text133 = array11[num129].replace("\n", "")
                        if text133 != "" and ((not list_contains(self.materialsWritten, text133))
                                              & (text133 != "") & (text133 != "\r\n")):
                            v.arrayList2.append(text133)
                            self.materialsWritten.append(text133)
                    if index_of(self.materialstr, "\r\n") < len(self.materialstr) - 1:
                        self.materialstr = substring(self.materialstr, index_of(self.materialstr, "\r\n") + 2)
                    else:
                        self.materialstr = ""
                else:
                    text132 = self.materialstr
                    if (index_of(text132, "BOCFAB") > -1) & (index_of(text132, "-CM01\t") > -1):
                        self.includesCOM = True
                    if (not list_contains(self.materialsWritten, text132)) & (text132 != "") & (text132 != "\r\n"):
                        v.arrayList2.append(text132)
                        self.materialsWritten.append(text132)
                    self.materialstr = ""

        # ------------------------------------------------------------------ 5062
        if not ((not self._formatCSI) & self._syteline):
            return Flow.NEXT_ITEM

        # ------------------------------------------------------------------ stage 21 SQL (5066-5071)
        # text9 == "'" + _effectiveDate + "'" (5069 / 2224): bound as a parameter.
        params: list = []
        text = (
            "SELECT Item.Item, prod1.Product, CASE WHEN pd1.ShortDescription IS NOT NULL THEN pd1.ShortDescription "
            "ELSE prod1.Name END AS [Super Description], ComponentSequence AS Seq, itm2.Item AS Component, "
            "itm2.WeightKilos, itm2.VolumeLitres, itm2.CommodityCode, Quantity, FeaturePositionString, "
            "CASE WHEN pd2.ShortDescription IS NOT NULL THEN pd2.ShortDescription WHEN od.ShortDescription IS NOT NULL "
            "THEN od.ShortDescription ELSE prod2.Name END AS Description, "
            "CASE WHEN pc.BasePriceRef = 1 THEN itm2.BasePrice WHEN pc.BasePriceRef = 2 THEN itm2.BasePrice2 "
            "WHEN pc.BasePriceRef = 3 THEN itm2.BasePrice3 END AS MyBasePrice, "
        )
        if self._millerCAD | (self._syteline & (not self._exportBasePrices)):
            text = text + "dbo.fnGetListPriceByItem(itm2.Item, ?, ?, ?, NULL) AS ListPrice, "
            params += [self._currency, self._effectiveDate, self._siteId]
        text = (
            text + "pc.Product_Code, pc.PriceCode, prod2.DescriptionId FROM Item WITH (NOLOCK) "
            "CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x "
            "INNER JOIN ItemComponents itco ON Item.ItemId = itco.ItemId "
            "INNER JOIN Item itm2 ON itco.SubItemId = itm2.ItemId "
            "INNER JOIN Product prod1 ON Item.ProductId = prod1.ProductId "
            "INNER JOIN Product prod2 ON itm2.ProductId = prod2.ProductId "
            "INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 "
            "WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 "
            "WHERE i2.ItemId = Item.ItemId ) ELSE prod2.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = ? "
            "LEFT OUTER JOIN OtherDescription od ON prod2.DescriptionId = od.DescriptionId "
            "And od.RelatedTable = 'SPComponent' AND od.LanguageId = ? "
            "LEFT OUTER JOIN ProductDescription pd1 ON prod1.DescriptionId = pd1.DescriptionId AND pd1.LanguageId = ? "
            "LEFT OUTER JOIN ProductDescription pd2 ON prod2.DescriptionId = pd2.DescriptionId AND pd2.LanguageId = ? "
            "WHERE Item.ItemId = ? ORDER BY Seq"
        )
        params += [self._siteId, self._languageId, self._languageId, self._languageId, sqlDataReader["ItemId"]]
        v.text = text
        self.threadStage = "21"
        rows2 = self.q("c2", text, tuple(params))  # sqlDataReader2
        for row2 in rows2:
            text134 = tostr(row2["FeaturePositionString"])  # FeaturePositionString, consumed below
            right6 = "P"      # item type column: P (plain) / M (has features)
            text135 = "no"    # noqa: F841  (assigned in legacy, never read)
            right7 = ""       # "BOC" when the component has a feature position string
            arrayList80 = []  # distinct OptionIds referenced by the feature position string
            arrayList81 = []  # 1-based positions (in the '|' split) of every non-empty option id
            text136 = ""      # feature template ("XXXX-XXXXXXX-...")
            arrayList82 = []  # per-feature "Fnn-0m" position strings (one per option, padded to _numFeatureSlots)
            text137 = ""      # last "Fnn-0m" appended to arrayList82
            arrayList83 = []  # material row strings
            arrayList84 = []  # other-language description rows parallel to arrayList83
            if text134 != "":
                right6 = "M"
                text135 = "yes"
                right7 = "BOC"
                num130 = 1
                while index_of(text134, "|") > -1:
                    text138 = substring(text134, 0, index_of(text134, "|"))
                    if text138 != "":
                        if not list_contains(arrayList80, net_int(text138)):
                            arrayList80.append(net_int(text138))
                        arrayList81.append(num130)
                    num130 += 1
                    text134 = "" if index_of(text134, "|") >= len(text134) - 1 else substring(text134, index_of(text134, "|") + 1)
                num131 = 1  # running feature position
                for num133 in range(0, len(arrayList80)):
                    # stage 22 SQL (5112); catalogue/language ids and the option id are bound.
                    mysql3 = (
                        "SELECT opt.IsFabric, optval.OptionValueId, opt.SLFeatureLength, optval.OrderCodeValue, "
                        "MAX(LEN(REPLACE(optval.OrderCodeValue, '#', ''))) AS max_length, "
                        "CASE WHEN od1.ShortDescription IS NULL THEN optval.Name ELSE od1.ShortDescription END AS Name, "
                        "optval.DisplayOrdinal, dov.AdditionalOptionValueId, "
                        "CASE WHEN parent.OptionId IS NULL THEN -1 ELSE parent.OptionId END AS parent_optid, "
                        "od2.ShortDescription FROM OptionValue optval WITH (NOLOCK) "
                        "INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId "
                        "INNER JOIN CatalogueOptionValues cov ON optval.OptionValueId = cov.OptionValueId "
                        "AND cov.CatalogueId = ? "
                        "LEFT OUTER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId "
                        "LEFT OUTER JOIN OptionValue parent ON dov.OptionValueId = parent.OptionValueId "
                        "LEFT OUTER JOIN OtherDescription od1 ON optval.DescriptionId = od1.DescriptionId "
                        "AND od1.LanguageId = ? "
                        "LEFT OUTER JOIN OtherDescription od2 ON optval.DescriptionId = od2.DescriptionId "
                        "AND od2.LanguageId = ? "
                        "GROUP BY opt.IsFabric, optval.OptionValueId, opt.SLFeatureLength, optval.OrderCodeValue, "
                        "od1.ShortDescription, optval.DisplayOrdinal, dov.AdditionalOptionValueId, parent.OptionId, "
                        "optval.Name, od2.ShortDescription, optval.OptionId HAVING optval.OptionId = ?"
                    )
                    self.threadStage = "22"
                    rows3 = self.q("c3", mysql3, (self._catalogueId, self._languageId, self._otherlanguageId,
                                                  arrayList80[num133]))
                    arrayList85 = []  # OrderCodeValue
                    arrayList86 = []  # SLFeatureLength
                    arrayList87 = []  # per-option feature length = max(SLFeatureLength, num134)
                    arrayList88 = []  # Name
                    arrayList89 = []  # IsFabric (0 normal, 1 fabric colour, 2 fabric)
                    arrayList90 = []  # is dependent (has AdditionalOptionValueId)
                    arrayList91 = []  # DisplayOrdinal (long; parsed only)
                    arrayList92 = []  # other-language ShortDescription
                    num134 = 2        # max code length seen (min 2)
                    for row3 in rows3:
                        if list_contains(v.arrayList45, net_int(row3["OptionValueId"])):
                            if tostr(row3["AdditionalOptionValueId"]) != "":
                                arrayList90.append(True)
                            else:
                                arrayList90.append(False)
                            num135 = net_int(row3["max_length"])
                            if num135 > num134:
                                num134 = num135
                            arrayList85.append(tostr(row3["OrderCodeValue"]))
                            arrayList86.append(net_int(row3["SLFeatureLength"]))
                            arrayList88.append(tostr(row3["Name"]))
                            arrayList89.append(net_int(row3["IsFabric"]))
                            if row3["ShortDescription"] is not None:
                                arrayList92.append(tostr(row3["ShortDescription"]))
                            else:
                                arrayList92.append("")
                            arrayList91.append(_net_long(row3["DisplayOrdinal"]))
                    # text139 "optcodes" accumulator is debug-only (never read): omitted.
                    for num137 in range(0, len(arrayList85)):
                        if arrayList86[num137] > num134:
                            arrayList87.append(arrayList86[num137])
                        else:
                            arrayList87.append(num134)
                    if len(arrayList85) <= 0:
                        continue
                    num138 = 2  # feature length of this option
                    num138 = int(arrayList87[0])
                    if (arrayList89[0] == 0) & (num138 > 2) & self._length5Feats:
                        num138 = 5
                    if (arrayList89[0] == 2) & (num138 == 5):
                        num138 = 4
                    text140 = "F"
                    text140 = text140 + str(num131) if num131 >= 10 else text140 + "0" + str(num131)
                    text140 = text140 + "-0" + str(num138)
                    text140 = debug_post_processed_feature_pos(text140, "FF")
                    if not arrayList90[0]:
                        arrayList82.append(text140)
                    if arrayList89[0] == 1:
                        if is_knoll_catalogue(self._catalogueId):
                            if not self._flattenFabrics:
                                text136 = text136 + debug_feature_template("XXXXXXXXXX", "10")
                            else:
                                text136 = text136 + debug_feature_template("XXXXXXXX", "8")
                        elif not list_contains(arrayList85, "CM01#"):
                            text136 = text136 + debug_feature_template("XXXXXXX", "7")
                        else:
                            text136 = text136 + debug_feature_template("XXXXXXXX", "8")
                    elif arrayList89[0] == 0:
                        for num140 in range(1, num138 + 1):
                            text136 += debug_feature_template("X", "4")
                    if num133 < len(arrayList80) - 1:
                        text136 += "-"
                    for num142 in range(0, len(arrayList85)):
                        text141 = "9-" + text140 + "-" + arrayList85[num142]
                        if arrayList89[num142] == 2:
                            text141 = "9-FAB-" + arrayList85[num142]
                        # material row: 5218 (field layout documented in the report)
                        text142 = (
                            text141 + "\tno\t" + arrayList85[num142] + "|" + arrayList88[num142]
                            + "\t" + "A" + "\t" + "\t" + "0" + "\t" + "0" + "\t" + "\t" + "\t" + "ZZ-ZZ"
                            + "\t" + "0" + "\t" + "0" + "\t" + "yes" + "\t" + "35" + "\t" + "0" + "\t" + "0"
                            + "\t" + "\t" + "\t" + "\t" + "DEF" + "\t" + "1" + "\t" + "0" + "\t" + "EA"
                            + "\t" + "\t" + "P" + "\t" + "\t" + "no" + "\t" + "\t" + "\t" + "\t" + "\t"
                            + "0" + "\t" + "0"
                        )
                        if not list_contains(arrayList83, text142):
                            arrayList83.append(text142)
                            if arrayList92[num142] != "":
                                arrayList84.append(text141 + "\t" + arrayList92[num142])
                            else:
                                arrayList84.append("")
                    num131 += num138
                    if (num138 == 4) & list_contains(arrayList85, "CM01#"):
                        num131 += 4
            if len(arrayList82) > 0:
                text137 = tostr(arrayList82[len(arrayList82) - 1])
            count2 = len(arrayList82)
            for num144 in range(count2, self._numFeatureSlots):
                arrayList82.append("")
            if text136.endswith("-"):
                text136 = substring(text136, 0, len(text136) - 1)
            self.threadStage = "23"
            v.num3 = self.get_feature_count(tostr(sqlDataReader["LongItem"]))  # feature count of the super product
            self.threadStage = "23.1"
            # superprod file row (5256)
            text143 = (
                tostr(row2["Item"]) + "\t" + tostr(row2["Super Description"]) + "\t" + tostr(row2["Seq"])
                + "\t" + tostr(row2["Component"]) + "\t" + tostr(row2["Quantity"]) + "\t"
                + tostr(row2["Description"]) + "\t" + str(v.num3) + "\t"
            )
            for num146 in range(0, len(arrayList81)):
                text143 = text143 + str(arrayList81[num146])
                if num146 < len(arrayList81) - 1:
                    text143 += "\t"
            self.threadStage = "23.2"
            self.write_to_stream(v.streamWriter2, text143 + "\r\n", "gggggg")
            self.threadStage = "23.3"
            if self._superProductsOnly:
                continue
            num147 = 0.0  # VolumeLitres
            if tostr(row2["VolumeLitres"]) != "":
                num147 = net_double(row2["VolumeLitres"])
            num148 = 0.0  # WeightKilos
            if tostr(row2["WeightKilos"]) != "":
                num148 = net_double(row2["WeightKilos"])
            text144 = ""  # component item row
            if self._syteline:
                text144 = (tostr(row2["Component"]) + "\tno\t" + tostr(row2["Description"]) + "\t" + "A" + "\t" + "\t")
                if self._exportBasePrices:
                    num149 = 0.0
                    if tostr(row2["MyBasePrice"]) != "":
                        num149 = net_double(row2["MyBasePrice"])
                    if num149 < 0.0:
                        num149 = 0.0
                    text144 = text144 + tostr(num149) + "\t"
                else:
                    num150 = 0.0
                    if tostr(row2["ListPrice"]) != "":
                        num150 = net_double(row2["ListPrice"])
                    if num150 < 0.0:
                        num150 = 0.0
                    text144 = text144 + tostr(num150) + "\t"
                if list_contains(v.arrayList12, tostr(row2["Component"])):
                    text145 = tostr(v.arrayList13[list_index_of(v.arrayList12, tostr(row2["Component"]))])
                    if index_of(text145, "|") > -1:
                        text145 = substring(text145, index_of(text145, "|") + 1)
                    num151 = len(text145)
                    if (num151 > 2) & self._length5Feats:
                        num151 = 5
                    num152 = 1
                    if text137 != "":
                        num153 = net_int(substring(text137, 0, index_of(text137, "-")).replace("F", ""))
                        num154 = net_int(substring(text137, index_of(text137, "-") + 1))
                        num152 = num153 + num154
                    text146 = "F"
                    text146 = text146 + str(num152) if num152 >= 10 else text146 + "0" + str(num152)
                    text146 += "-"
                    text146 = text146 + str(num151) if num151 >= 10 else text146 + "0" + str(num151)
                    text146 = debug_post_processed_feature_pos(text146, "GG")
                    for num156 in range(0, len(arrayList82)):
                        if tostr(arrayList82[num156]) == "":
                            text136 += "-"
                            for num158 in range(1, num151 + 1):
                                text136 += debug_feature_template("X", "5")
                            if self._ignoreOptDeps:
                                arrayList82[num156] = text146
                            else:
                                arrayList82[num156] = ""
                            break
                # component item row (5360); layout documented in the report
                text144 = (
                    text144 + "0\t\t\t" + tostr(row2["Product_Code"]) + "\t" + tostr(num147) + "\t" + tostr(num148)
                    + "\t" + "no" + "\t" + "35" + "\t" + "0" + "\t" + "0" + "\t" + "\t" + "\t" + "\t" + "\t"
                    + "1" + "\t" + "0" + "\t" + "EA" + "\t" + tostr(row2["CommodityCode"]) + "\t" + right6
                    + "\t" + "" + "\t" + "no" + "\t" + text136 + "\t" + "\t" + "\t" + right7 + "\t" + "0"
                    + "\t" + "0" + "\t" + "\t"
                )
                for num160 in range(0, len(arrayList82)):
                    text144 = text144 + tostr(arrayList82[num160])
                    if num160 < len(arrayList82) - 1:
                        text144 += "\t"
            else:
                # unreachable from the caller (5062 only lets _syteline through) but ported verbatim
                num161 = 0.0
                if tostr(row2["MyBasePrice"]) != "":
                    num161 = net_double(row2["MyBasePrice"])
                if num161 < 0.0:
                    num161 = 0.0
                if not list_contains(self._priceCodes, tostr(row2["PriceCode"])):
                    self._priceCodes.append(tostr(row2["PriceCode"]))
                if not list_contains(self._productCodes, tostr(row2["Product_Code"])):
                    self._productCodes.append(tostr(row2["Product_Code"]))
                text144 = (
                    tostr(row2["Component"]) + "\t" + "no" + "\t" + tostr(row2["Description"]) + "\t" + "A"
                    + "\t" + tostr(num161) + "\t" + tostr(row2["Product_Code"]) + "\t" + tostr(row2["PriceCode"])
                )
            if not list_contains(v.arrayList8, text144):
                v.arrayList8.append(text144)
                # logMessage("{3333} ...") omitted (no-op)
                v.arrayList.append(text144 + "\t\t\t\t")
                if row2["DescriptionId"] is not None:
                    self.threadStage = "24"
                    rows5 = self.q(
                        "c5",
                        "SELECT ShortDescription FROM ProductDescription WITH (NOLOCK) "
                        "WHERE LanguageId = ? AND DescriptionId = ?",
                        (self._otherlanguageId, row2["DescriptionId"]),
                    )
                    if (len(rows5) > 0) & (self._languageId != self._otherlanguageId):
                        self.write_data(
                            v.streamWriter4,
                            v.text3 + "\t" + tostr(row2["Component"]) + "\t" + tostr(rows5[0]["ShortDescription"]) + "\r\n",
                            False,
                        )
            for num163 in range(0, len(arrayList83)):
                if (not list_contains(v.arrayList8, arrayList83[num163])) and index_of(arrayList83[num163], "#") == -1:
                    v.arrayList8.append(arrayList83[num163])
                    # logMessage("{4444} ...") omitted (no-op)
                    v.arrayList.append(arrayList83[num163])
                    if (arrayList84[num163] != "") & (self._languageId != self._otherlanguageId):
                        self.write_data(v.streamWriter4, v.text3 + "\t" + arrayList84[num163] + "\r\n", False)
        # sqlDataReader2.Close() (5425): rows are fully fetched, nothing to close
        return None
