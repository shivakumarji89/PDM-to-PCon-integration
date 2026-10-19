"""ExportThread.cs 4192-5008: item-record header, item row emitters, stages 17.17-20.83.

Mechanical transliteration; see PORTING_CONVENTIONS.md.  Lines 4192-4197 are the tail of a
``debugOptionData`` block (flag default false, omitted); real code starts at 4199 ("17.11").

CONTROL-FLOW NOTE FOR THE INTEGRATOR: in C# the ``else`` that starts at line 4350 (stage 17.15b)
does NOT close at 5008; it also contains the code that follows (``logOutput`` debug block at 5009
and stage 20.9 onwards).  So everything after this method's range must run only when the
``else`` branch was taken.  This method records that in ``self.v.p05_else_branch`` (True when the
17.15b ``else`` ran, False when the 17.14 ``if`` ran).  Not a C# variable.

Helpers this mixin expects from other mixins (see the final report): ``write_data``,
``format_csi_data``, ``get_product_description``, ``get_short_product_code``,
``get_feature_length_for_item_option``, ``update_child_feature_length_for_material_on_item_tab``,
``add_material_to_item_tab``.
"""
from __future__ import annotations

from services.syteline_export.pipeline.netsem import (
    LegacyRangeError,
    debug_feature_pos,
    index_of,
    is_knoll_catalogue,
    list_contains,
    list_index_of,
    net_bool,
    net_double,
    net_int,
    substring,
    tostr,
)
from services.syteline_export.pipeline.run_base import Flow


def _index_of_from(text: str, needle: str, start: int) -> int:
    """``string.IndexOf(string, int)``: throws when startIndex > Length."""
    if start < 0 or start > len(text):
        raise LegacyRangeError(f"startIndex {start} out of range for length {len(text)}")
    return text.find(needle, start)


def _last_index_of(text: str, needle: str) -> int:
    return text.rfind(needle)


def _pad_right_cut(text: str, width: int) -> str:
    """``s.PadRight(width, ' ').Substring(0, width)``."""
    return text.ljust(width)[:width]


def _pad_left_cut(text: str, width: int, ch: str) -> str:
    """``s.PadLeft(width, ch).Substring(0, width)``."""
    return text.rjust(width, ch)[:width]


def _f2(value: float) -> str:
    """``{value:f2}`` under .NET Framework: the double is first reduced to 15 significant digits
    and then rounded half away from zero (Python's ``format`` rounds the exact binary value
    half-even: 10.125 -> "10.12" there but "10.13" in .NET)."""
    from decimal import ROUND_HALF_UP, Decimal
    return format(Decimal(format(float(value), ".15g")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")


class P05Mixin:
    # ExportThread.cs:4199-5008
    def p05_item_row_and_renumber(self) -> Flow | None:
        v = self.v
        row = v.sqlDataReader
        self.threadStage = "17.11"
        v.text5 = "no"  # isSuperProduct yes/no
        if net_bool(row["IsSuperProduct"]) and not v.flag4:
            v.text5 = "yes"
            v.text19 = ""
            v.arrayList46 = []
        if tostr(row["Notes"]).find("X") > -1:
            v.text19 = tostr(row["Notes"])
        elif tostr(row["LegacyItem"]).find("X") > -1:
            v.text19 = tostr(row["LegacyItem"])
        self.threadStage = "17.12"
        text93 = "A"  # status flag
        text94 = ""  # reason code
        if net_int(row["Status"]) != 1:
            text93 = "O"
            status = net_int(row["Status"])
            if status == 0:
                text94 = "URL"
            elif status == 2:
                text94 = "OBS"
            elif status == 3:
                text94 = "ON HOLD"
        left13 = "yes"
        if len(v.text19) == 0:
            left13 = "no"
        if v.text19.endswith("-"):
            v.text19 = substring(v.text19, 0, len(v.text19) - 1)
        right3 = "M"
        right4 = "BOC"
        if left13 == "no":
            right3 = "P"
            right4 = ""
            v.text19 = ""
        num76 = 0.0  # weight
        if tostr(row["WeightKilos"]) != "":
            num76 = net_double(row["WeightKilos"])
        num77 = 0.0  # volume
        if tostr(row["VolumeLitres"]) != "":
            num77 = net_double(row["VolumeLitres"])
        text95 = self.get_product_description(tostr(row["LongItem"]), tostr(row["ShortDescription"]))
        fsc = row["FSCCompliant"]
        # ConditionalCompareObjectEqual(obj, 1): a DB bit/bool is not equal to 1 under VB (True is -1)
        if fsc is not None and not isinstance(fsc, bool) and fsc == 1:
            text95 += "#"

        self.threadStage = "17.13"
        if self._millerCAD:
            array8 = self.materialstr.split("\r")
            for num79 in range(len(array8)):
                if array8[num79].find("\t") > -1:
                    text96 = substring(array8[num79], 0, index_of(array8[num79], "\t"))
                    text97 = substring(array8[num79], 0, _index_of_from(array8[num79], "\t", len(text96) + 1))
                    text98 = substring(array8[num79], 0, _index_of_from(array8[num79], "\t", len(text97) + 1))
                    text99 = text97 + substring(array8[num79], len(text98))
                    num80 = text99.find("\t")
                    num80 = _index_of_from(text99, "\t", num80 + 1)
                    num80 = _index_of_from(text99, "\t", num80 + 1)
                    num80 = _index_of_from(text99, "\t", num80 + 1)
                    array8[num79] = substring(text99, 0, num80)
            self.materialstr = ""
            for num82 in range(len(array8)):
                text100 = ""
                text101 = array8[num82].replace("\r\n", "").replace("\r", "").replace("\n", "")
                if text101 == "":
                    continue
                text100 += _pad_right_cut(substring(text101, 0, index_of(text101, "\t")), 30)
                text101 = substring(text101, index_of(text101, "\t") + 1)
                text100 += _pad_right_cut(substring(text101, 0, index_of(text101, "\t")), 8)
                text101 = substring(text101, index_of(text101, "\t") + 1)
                text100 += _pad_right_cut(substring(text101, 0, index_of(text101, "\t")), 8)
                text101 = substring(text101, index_of(text101, "\t") + 1)
                text100 += _pad_left_cut(_f2(net_double(text101)), 8, "0")
                if net_bool(row["IsSuperProduct"]) and not v.flag4:
                    num83 = 0
                    if text100.find(" ") < len(tostr(row["Item"])):
                        num83 = len(tostr(row["Item"])) - text100.find(" ")
                    text100 = (tostr(row["Item"]) + " "
                               + substring(text100, text100.find(" ") + 1 + num83) + "\r\n")
                self.materialstr = self.materialstr + text100 + "\r\n"

        self.threadStage = "17.14"
        v.p05_else_branch = False
        if (v.text5 == "yes") & ((not self._exportSPComponentMaterials) | self._superProductsOnly):
            self.threadStage = "17.5a"
            if self._millerCAD:
                # fixed width: 30+10+30+10+_maxDescriptionLength then "[bitmap][feats]"
                v.arrayList.append(
                    _pad_right_cut(tostr(row["LongItem"]), 30)
                    + _pad_right_cut(tostr(row["Product_Code"]), 10)
                    + _pad_right_cut(tostr(row["Description"]), 30)
                    + _pad_left_cut(_f2(net_double(row["ListPrice"])), 10, "0")
                    + _pad_right_cut(text95.replace(">", " "), self._maxDescriptionLength)
                    + "[bitmap][feats]")
            elif self._syteline:
                # 35 tab-separated fields, 34 tabs, NO trailing CRLF (legacy)
                value4 = (tostr(row["LongItem"]) + "\t" + v.text5 + "\t" + text95.replace(">", " ") + "\t"
                          + text93 + "\t" + text94 + "\t0\t0\t\t\t" + tostr(row["Product_Code"]) + "\t"
                          + tostr(num77) + "\t" + tostr(num76) + "\tno\t35\t0\t0\t\t\t\tSUP\t1\t0\tEA\t"
                          + tostr(row["CommodityCode"]) + "\tP\t"
                          + "\tno\t" + "\t\t\t" + "\t0\t0\t\t")
                if self._formatCSI:
                    value4 = self.format_csi_data(
                        tostr(row["LongItem"]), v.text5, text95.replace(">", " "), text93, text94,
                        tostr(row["Product_Code"]), num77, num76, "EA", tostr(row["CommodityCode"]), "P", "")
                # logMessage: developer-only (dbacw8 + logOutput) -> omitted
                v.arrayList.append(value4)
                if (not self._formatCSI) & (row["AltDescription"] is not None) & (self._languageId != self._otherlanguageId):
                    self.write_data(
                        v.streamWriter4,
                        v.text3 + "\t" + tostr(row["LongItem"]) + "\t"
                        + tostr(row["AltDescription"]).replace(">", " ") + "\r\n",
                        False)
            else:
                if not list_contains(self._priceCodes, tostr(row["PriceCode"])):
                    self._priceCodes.append(tostr(row["PriceCode"]))
                if not list_contains(self._productCodes, tostr(row["Product_Code"])):
                    self._productCodes.append(tostr(row["Product_Code"]))
                # 7 fields, no CRLF (legacy)
                v.arrayList.append(
                    tostr(row["LongItem"]) + "\t" + v.text5 + "\t" + text95.replace(">", " ") + "\t"
                    + text93 + "\t" + "" + "\t" + tostr(row["Product_Code"]) + "\t" + tostr(row["PriceCode"]))
        else:
            v.p05_else_branch = True
            self.threadStage = "17.15b"
            text102 = ""  # the item record
            if self._millerCAD:
                num84 = 0.0
                if tostr(row["ListPrice"]) != "":
                    num84 = net_double(row["ListPrice"])
                text102 = (_pad_right_cut(tostr(row["LongItem"]), 30)
                           + _pad_right_cut(tostr(row["Product_Code"]), 10)
                           + _pad_right_cut(tostr(row["Description"]), 30)
                           + _pad_left_cut(_f2(num84), 10, "0")
                           + _pad_right_cut(text95.replace(">", " "), self._maxDescriptionLength))
                text103 = "1"
                num85 = 1
                while True:
                    text103 = (text103 + "0") if num85 > len(v.arrayList46) else (text103 + "1")
                    num85 += 1
                    if not (num85 <= 10):
                        break
                text102 += text103  # 11 chars
                text104 = ""
                for num87 in range(len(v.arrayList46)):
                    text104 = text104 + v.arrayList46[num87].replace("BOCFAB-", "")
                    if num87 != self._numFeatureSlots - 1:
                        text104 += " "
                text102 += _pad_right_cut(text104, 80)
            elif self._syteline:
                text102 = (tostr(row["LongItem"]) + "\t" + v.text5 + "\t" + text95.replace(">", " ") + "\t"
                           + text93 + "\t" + text94 + "\t")
                if self._exportBasePrices:
                    num88 = 0.0
                    if tostr(row["MyBasePrice"]) != "":
                        num88 = net_double(row["MyBasePrice"])
                    if num88 < 0.0:
                        num88 = 0.0
                    text102 = text102 + tostr(num88) + "\t"
                else:
                    num89 = 0.0
                    if tostr(row["ListPrice"]) != "":
                        num89 = net_double(row["ListPrice"])
                    if num89 < 0.0:
                        num89 = 0.0
                    text102 = text102 + tostr(num89) + "\t"
                right5 = ""
                if v.text5 == "yes":
                    right5 = "SUP"
                # fields 6..33 (field indexes, 0-based); see the test for the derived layout
                text102 = (text102 + tostr(v.num4) + "\t\t\t" + tostr(row["Product_Code"]) + "\t"
                           + tostr(num77) + "\t" + tostr(num76) + "\t" + "no" + "\t" + "35" + "\t" + "0" + "\t"
                           + "0" + "\t" + "\t" + "\t" + "\t" + right5 + "\t" + "1" + "\t" + "0" + "\t" + "EA"
                           + "\t" + tostr(row["CommodityCode"]) + "\t" + right3 + "\t" + "" + "\t" + "no"
                           + "\t" + v.text19 + "\t" + "\t" + "\t" + right4 + "\t" + "0" + "\t" + "0" + "\t" + "\t")
                for num91 in range(len(v.arrayList46)):
                    text105 = v.arrayList46[num91].replace(v.text6 + "-", "")
                    if text105.find("bocfab") == -1:
                        if text105.find("-HAR-") > -1:
                            text105 = substring(text105, text105.find("-HAR-") + 5)
                        text102 += text105
                    if num91 != self._numFeatureSlots - 1:
                        text102 += "\t"
                if len(v.arrayList46) < self._numFeatureSlots:
                    count = len(v.arrayList46)
                    for num93 in range(count, self._numFeatureSlots):
                        if num93 != self._numFeatureSlots:
                            text102 += "\t"
                text102 = text102 + "\t" + v.text16 + "\t" + v.text17 + "\t" + v.text18 + "\t"
            else:
                if not list_contains(self._priceCodes, tostr(row["PriceCode"])):
                    self._priceCodes.append(tostr(row["PriceCode"]))
                if not list_contains(self._productCodes, tostr(row["Product_Code"])):
                    self._productCodes.append(tostr(row["Product_Code"]))
                num94 = 0.0
                if tostr(row["MyBasePrice"]) != "":
                    num94 = net_double(row["MyBasePrice"])
                if num94 < 0.0:
                    num94 = 0.0
                text102 = (tostr(row["LongItem"]) + "\t" + v.text5 + "\t" + text95.replace(">", " ") + "\t"
                           + text93 + "\t" + tostr(num94) + "\t" + tostr(row["Product_Code"]) + "\t"
                           + tostr(row["PriceCode"]))
            text102 += "\r\n"
            if self._formatCSI:
                text102 = self.format_csi_data(
                    tostr(row["LongItem"]), v.text5, text95.replace(">", " "), text93, text94,
                    tostr(row["Product_Code"]), num77, num76, "EA", tostr(row["CommodityCode"]), "P", "")
            # logMessage("{2222} ...") developer-only -> omitted
            v.arrayList.append(text102)
            if (not self._formatCSI) & (row["AltDescription"] is not None) & (self._languageId != self._otherlanguageId):
                self.write_data(
                    v.streamWriter4,
                    v.text3 + "\t" + tostr(row["LongItem"]) + "\t"
                    + tostr(row["AltDescription"]).replace(">", " ") + "\r\n",
                    False)
            self.threadStage = "17.16"
            # debug-only block omitted (flag default false)
            # C#: ((!_formatCSI & bool.Parse(..)) && !flag4) & !_superProductsOnly  (Parse always runs)
            is_super = net_bool(row["IsSuperProduct"])
            if (((not self._formatCSI) & is_super) and not v.flag4) & (not self._superProductsOnly):
                self._p05_stage17_17_to_20_83(row)
        return None

    def _p05_stage17_17_to_20_83(self, row) -> None:
        """ExportThread.cs 4494-5007 (body of the ``if`` at 4492)."""
        v = self.v
        self.threadStage = "17.17"
        arrayList69: list = []   # item (sub-item) names seen
        arrayList70: list = []   # last feature placeholder per item
        arrayList71: list = []   # position (Fxx) per item
        arrayList72: list = []   # feature length per item
        arrayList73: list = []   # previous feature length per item
        arrayList74: list = []
        arrayList75: list = []
        array9 = self.materialstr.split("\r")
        arrayList76: list = []
        arrayList77: list = []
        # text106 (debug trace string), flag14 (only guards text106) and text107 ("" constant) are
        # debug-only accumulators: text106 is only shown under debugLengthTransitions; omitted.
        for num96 in range(len(array9)):
            if array9[num96].find("\t[opt") <= -1:
                continue
            text108 = substring(array9[num96], 0, array9[num96].find("\t[opt")).replace("\r", "").replace("\n", "")
            num97 = -1
            if text108.find("<") > -1:
                text109 = substring(text108, text108.find("<") + 1)
                text109 = substring(text109, 0, text109.find(">"))
                num97 = net_int(text109)
                text108 = substring(text108, 0, text108.find("<"))
            if text108.find("9-") > -1:
                text108 = substring(text108, 2)
                if text108.find("-[opt") > -1:
                    text108 = substring(text108, 0, text108.find("-[opt"))
            text110 = substring(array9[num96], array9[num96].find("\t[opt")).replace("\r", "").replace("\n", "")
            text110 = substring(text110, 0, text110.find("]") + 1).replace("\t", "")
            text111 = ""
            if array9[num96].find("[seq]") > -1:
                text111 = substring(array9[num96], array9[num96].find("[seq]") + 5)
                if text111.find("\t") > -1:
                    text111 = substring(text111, 0, text111.find("\t"))
                text111 = text111.replace("\r", "").replace("\n", "")
            self.threadStage = "17.18"
            num98 = 2  # feature length
            text112 = array9[num96]
            if text112.find("\t") > -1:
                text112 = substring(text112, text112.find("\t") + 1)
                if text112.find("\t") > -1:
                    text112 = substring(text112, text112.find("\t") + 1)
                    if text112.find("\t") > -1:
                        text112 = substring(text112, text112.find("\t") + 1)
                        if text112.find("|") > -1:
                            num98 = text112.find("|")
            if num98 < 2:
                num98 = 2
            flag15 = False  # isFabricReplacement
            arrayList78: list = []  # candidate option ids
            text114 = ""
            if array9[num96].find("]-") > -1:
                text114 = substring(array9[num96], _last_index_of(array9[num96], "]-") + 2)
                if text114.find("\t") > -1:
                    text114 = substring(text114, 0, text114.find("\t"))
            text113 = ("SELECT itco.FeaturePositionString FROM Item WITH (NOLOCK) "
                       "INNER JOIN ItemComponents itco ON Item.ItemId = itco.ItemId "
                       "INNER JOIN Item sub_item ON itco.SubItemId = sub_item.ItemId "
                       "WHERE Item.Item = ? AND sub_item.Item = ?")
            self.threadStage = "18"
            rows2 = self.q("c2", text113, (tostr(row["LongItem"]), text108))
            for r2 in rows2:
                text115 = tostr(r2["FeaturePositionString"])
                if text115.find("|") <= -1:
                    continue
                array10 = text115.split("|")
                for num100 in range(len(array10)):
                    # C# `&&` then non-short-circuit `|`: int.Parse(array10[i]) always runs when Length > 0
                    if len(array10[num100]) > 0:
                        parsed = net_int(array10[num100])
                        if (num97 == -1) | (num97 == parsed):
                            arrayList78.append(net_int(array10[num100]))
            num101 = -1
            if (text114 != "") & (len(arrayList78) > 0):
                for num103 in range(len(arrayList78)):
                    mysql2 = ("SELECT optval.OptionId FROM OptionValue optval WITH (NOLOCK) "
                              "WHERE optval.OptionId = ? AND (optval.OrderCodeValue = ? OR optval.OrderCodeValue = ?)")
                    self.threadStage = "19"
                    rows19 = self.q("c2", mysql2, (arrayList78[num103], text114, text114 + "#"))
                    if len(rows19) > 0:
                        num101 = list_index_of(arrayList78, net_int(rows19[0]["OptionId"]))
                    if num101 > -1:
                        break
            if num101 == -1:
                num101 = 0 if (not (text110.find("#_1") <= -1 and len(arrayList78) > 1)) else 1
            if (num101 > -1) & (num101 < len(arrayList78)):
                num104 = list_index_of(v.arrayList40, arrayList78[num101])
                if num104 > -1:
                    num98 = int(v.arrayList38[num104])
                    flag15 = bool(v.arrayList39[num104])
                else:
                    text113 = ("SELECT CASE WHEN fabric_opt.OptionId IS NULL THEN opt.SLFeatureLength ELSE fabric_opt.SLFeatureLength END AS SLFeatureLength, "
                               "CASE WHEN fabric_opt.OptionId IS NULL THEN MAX(LEN(REPLACE(optval.OrderCodeValue, '#', ''))) ELSE MAX(LEN(REPLACE(fabric_optval.OrderCodeValue, '#', ''))) END AS max_length, "
                               "CASE WHEN fabric_opt.OptionId IS NULL THEN opt.IsFabric ELSE fabric_opt.IsFabric END AS IsFabric "
                               "FROM [Option] opt WITH (NOLOCK) INNER JOIN OptionValue optval ON opt.OptionId = optval.OptionId "
                               "INNER JOIN CatalogueOptionValues cov ON optval.OptionValueId = cov.OptionValueId AND cov.CatalogueId = ? "
                               "LEFT OUTER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId "
                               "LEFT OUTER JOIN OptionValue fabric_optval ON dov.OptionValueId = fabric_optval.OptionValueId "
                               "LEFT OUTER JOIN [Option] fabric_opt ON fabric_optval.OptionId = fabric_opt.OptionId AND fabric_opt.IsFabric = 1 "
                               "GROUP BY opt.OptionId, opt.SLFeatureLength, opt.IsFabric, fabric_opt.OptionId, fabric_opt.SLFeatureLength, fabric_opt.IsFabric "
                               "HAVING opt.OptionId = ?")
                    self.threadStage = "20"
                    rows20 = self.q("c2", text113, (self._catalogueId, arrayList78[num101]))
                    for r20 in rows20:
                        num98 = net_int(r20["SLFeatureLength"])
                        num105 = net_int(r20["max_length"])
                        if num105 > num98 and num98 == 2:
                            num98 = num105
                        if net_int(r20["IsFabric"]) == 1:
                            flag15 = True
                    v.arrayList38.append(num98)
                    v.arrayList39.append(flag15)
                    v.arrayList40.append(arrayList78[num101])
            # (else branch of 4670 only appends to the debug string text106: omitted)
            if (not flag15 and num98 > 2) & self._length5Feats:
                num98 = 5
            self.threadStage = "20.1"
            if not list_contains(v.arrayList41, text108 + "~" + text110):
                v.arrayList41.append(text108 + "~" + text110)
                v.arrayList42.append(flag15)
            if not list_contains(arrayList69, text108):
                arrayList69.append(text108)
                arrayList70.append(text110)
                text116 = ""
                if text108.startswith("9-"):
                    for num107 in range(len(arrayList76)):
                        if text108.find(tostr(arrayList76[num107])) > -1:
                            text116 = tostr(arrayList76[num107])
                            break
                    # (checked{} block ends here)
                self.threadStage = "20.2"
                if text108.startswith("9-") & (list_index_of(arrayList69, text116) > -1):
                    num108 = int(arrayList73[list_index_of(arrayList69, text116)])
                    if not list_contains(arrayList77, text116):
                        idx = list_index_of(arrayList69, text116)
                        arrayList71[idx] = arrayList71[idx] + num108
                        arrayList77.append(text116)
                    arrayList71.append(arrayList71[list_index_of(arrayList69, text116)])
                    arrayList73.append(num108)
                    arrayList72.append(num98)
                else:
                    arrayList71.append(1)
                    arrayList73.append(num98)
                    arrayList72.append(num98)
                self.threadStage = "20.3"
                value5 = text108
                num109 = list_index_of(arrayList74, value5)
                if num109 == -1:
                    arrayList74.append(value5)
                    arrayList75.append(2)
                else:
                    arrayList75[num109] = arrayList75[num109] + 1
            else:
                self.threadStage = "20.4"
                if arrayList70[list_index_of(arrayList69, text108)] != text110:
                    num110 = int(arrayList73[list_index_of(arrayList69, text108)])
                    flag16 = False
                    text117 = tostr(arrayList70[list_index_of(arrayList69, text108)])
                    num111 = -2
                    num111 = list_index_of(v.arrayList41, text108 + "~" + text117)
                    if num111 > -1:
                        flag16 = bool(v.arrayList42[num111])
                    # (debug trace text106 omitted)
                    if num110 == 4 and flag15:
                        num110 = 8
                    elif flag16:
                        num110 = 7
                    elif not text108.startswith("9-"):
                        self.threadStage = "20.41"
                        for num115 in range(len(arrayList69)):
                            text118 = tostr(arrayList69[num115])
                            if not text118.startswith("9-" + text108):
                                continue
                            text119 = text110
                            if text119.find("_") <= -1:
                                continue
                            self.threadStage = "20.42"
                            num116 = net_int(substring(text119, _last_index_of(text119, "_") + 1).replace("]", ""))
                            if num116 <= 2:
                                continue
                            num116 -= 1
                            text119 = substring(text119, 0, _last_index_of(text119, "_") + 1) + str(num116) + "]"
                            if arrayList70[num115] == text119:
                                num110 = int(arrayList72[num115])
                                # debugLengthTransitions MsgBox omitted (flag false)
                                break
                    idx = list_index_of(arrayList69, text108)
                    arrayList71[idx] = arrayList71[idx] + num110
                    arrayList73[idx] = num98
                self.threadStage = "20.43"
                arrayList70[list_index_of(arrayList69, text108)] = text110
                value6 = text108
                num117 = list_index_of(arrayList74, value6)
                if num117 == -1:
                    arrayList74.append(value6)
                    arrayList75.append(2)
                else:
                    arrayList75[num117] = arrayList75[num117] + 1
            if list_contains(arrayList69, text108):
                self.threadStage = "20.5"
                num118 = int(arrayList71[list_index_of(arrayList69, text108)])  # featpos start
                text120 = "F"
                text121 = ""
                if flag15:
                    text121 = "BOCFAB[" + self.get_short_product_code(v.prodcode, v.rootproduct) + "]-"
                    text120 = text121 + "F"
                if num118 >= 10:
                    text120 = text120 + str(num118) + "-0" + str(num98)
                else:
                    text120 = text120 + "0" + str(num118) + "-0" + str(num98)
                text120 = debug_feature_pos(text120, "DD")
                self.threadStage = "20.6"
                text123 = ""  # debugMaterialSequence false
                self.materialstr = self.materialstr.replace(text110.replace("_", "~") + "[seq]" + text111,
                                                            text123 + text111)
                if text110 == "":
                    # .NET String.Replace throws ArgumentException for an empty oldValue; Python would
                    # silently insert text120 between every character of materialstr.
                    raise ValueError("String cannot be of zero length. (ExportThread.cs:4860)")
                self.materialstr = self.materialstr.replace(text110, text120)
                if text121 != "":
                    self.materialstr = self.materialstr.replace("\t" + text121, "\t")
            if not text108.startswith("9-") and not list_contains(arrayList76, text108):
                arrayList76.append(text108)
        self.threadStage = "20.7"
        # debugLengthTransitions block omitted (flag default false)
        for num122 in range(len(v.arrayList26)):
            self.materialstr = self.materialstr.replace("<" + tostr(v.arrayList26[num122]) + ">", "")
        self.threadStage = "20.8"
        array9 = self.materialstr.split("\r")
        text125 = ""
        flag17 = False  # never becomes True: text125 is "" and never reassigned (legacy dead code)
        for num124 in range(len(array9)):
            text126 = array9[num124].replace("\r", "").replace("\n", "")
            text127 = ""  # item
            text128 = ""  # feature
            text129 = ""  # component
            text130 = ""  # component description
            feature2 = ""
            if text126.find("\t") > -1:
                text127 = substring(text126, 0, text126.find("\t"))
                text126 = substring(text126, text126.find("\t") + 1)
                if text126.find("\t") > -1:
                    text128 = substring(text126, 0, text126.find("\t"))
                    text126 = substring(text126, text126.find("\t") + 1)
                    if text126.find("\t") > -1:
                        text129 = substring(text126, 0, text126.find("\t"))
                        text126 = substring(text126, text126.find("\t") + 1)
                        if text126.find("\t") > -1:
                            text130 = substring(text126, 0, text126.find("\t"))
            self.threadStage = "20.81"
            arrayList79: list = []
            if (text129 != "") & (len(text128) > 1):
                num125 = 2
                dependentoption = False
                flag18 = False
                if len(text129) > 5 and substring(text129, 5, 1) == "-":
                    flag18 = True
                if (not text129.startswith("9-F") or not flag18) & (text129.find("BOCFAB") == -1):
                    self.threadStage = "20.82"
                    dependentoption = True
                    text131 = text128
                    if text131.find("-F") > -1:
                        text131 = substring(text131, _last_index_of(text131, "-F") + 1)
                    num126 = net_int(substring(text131, 1, 2))
                    num127 = net_int(substring(text131, 4, 2))
                    self.threadStage = "20.825"
                    num125 = self.get_feature_length_for_item_option(tostr(row["LongItem"]), text130)
                    num126 += num127
                    feature2 = "F"
                    feature2 = (feature2 + str(num126)) if num126 >= 10 else (feature2 + "0" + str(num126))
                    feature2 = feature2 + "-0" + str(num125)
                    feature2 = debug_feature_pos(feature2, "EE")
                elif text127.startswith("9-") & text129.startswith("9-F"):
                    self.update_child_feature_length_for_material_on_item_tab(text127, text128, flag17)
                elif text127.startswith("9-") & text129.startswith("9-BOCFAB["):
                    if is_knoll_catalogue(self._catalogueId):
                        arrayList79.append(8512)
                    else:
                        arrayList79.append(8)
                    feature2 = text128
                if len(arrayList79) == 0:
                    arrayList79.append(-1)
                self.add_material_to_item_tab(
                    text129, substring(text130, index_of(text130, "|") + 1), "", 1, dependentoption,
                    net_bool(row["IsSuperProduct"]) and bool(v.flag4), feature2, " <missing>", num125,
                    arrayList79, self.threadStage)
            if text130 != "" and text130.find("|") > -1:
                self.threadStage = "20.83"
                try:
                    newValue6 = (array9[num124].replace("\r", "").replace("\n", "")
                                 .replace(text130, substring(text130, 0, text130.find("|"))))
                    self.materialstr = self.materialstr.replace(
                        array9[num124].replace("\r", "").replace("\n", ""), newValue6)
                except Exception as ex8:  # noqa: BLE001 - legacy catch (Exception) + MsgBox
                    self.report_swallowed(text130, ex8)
