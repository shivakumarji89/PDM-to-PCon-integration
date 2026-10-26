"""Literal transliteration of ExportThread.cs helper methods (fabric / material-on-item-tab group).

Ported ranges (C:\\Users\\siaoca\\Desktop\\PDM\\PDMMaintenance\\ExportThread.cs):
  814-861   updateChildFeatureLengthForMaterialOnItemTab
  863-947   addMaterialToItemTab
  949-984   isInteger
  1090-1121 getTranslation
  1123-1197 getItemSequence
  1199-1282 GetKnollFabricOrderCode
  1284-1557 addFabricColour
See PORTING_CONVENTIONS.md. Synthetic-friendly: no real database is touched.
"""
from __future__ import annotations

from typing import Any

from services.syteline_export.pipeline.netsem import (
    debug_feature_pos,
    index_of,
    is_knoll_catalogue,
    list_contains,
    list_index_of,
    net_int,
    substring,
    tostr,
)

# ConnectionFactory.CreateNewConnection(autoOpen: true) is a brand new connection, not one of the five
# run connections (c1..c5); it keeps no session state, so any distinct name is equivalent.
_NEW_CONN = "c6"


def _to_integer(value: Any) -> int:
    """VB ``Conversions.ToInteger(object)``."""
    if value is None:
        return 0
    if isinstance(value, bool):
        return -1 if value else 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value)
    return net_int(value)


def _item(items: list, index: int) -> Any:
    """ArrayList indexer: negative / too large index throws ArgumentOutOfRangeException (not Python wrap-around)."""
    if index < 0 or index >= len(items):
        raise IndexError(f"Index was out of range: {index}")
    return items[index]


class HelpersFabricMixin:
    # ExportThread.cs:814-861
    def update_child_feature_length_for_material_on_item_tab(self, myitem: str, myfeature: str, verbose: bool) -> None:
        try:
            flag = False
            num = len(self._convertedList) - 1
            for i in range(0, num + 1):
                self.check_abort()
                if tostr(self._convertedList[i]) != myitem:
                    continue
                num2 = 2
                if index_of(myfeature, "-") > -1:
                    myfeature = substring(myfeature, index_of(myfeature, "-") + 1)
                    if index_of(myfeature, "}") > -1:
                        myfeature = substring(myfeature, index_of(myfeature, "}") + 1)
                    num2 = net_int(myfeature)
                self._convertChildFeatLen[i] = num2
                flag = True
                break
            if not flag:
                text = "_convertedList does NOT contain: [" + myitem + "]\r\n\r\n"
                num3 = len(self._convertedList) - 1
                for j in range(0, num3 + 1):
                    self.check_abort()
                    text = text + tostr(self._convertedList[j]) + "\r\n"
                self.msgbox(text)
        except Exception as exc:
            self.report_swallowed("updateChildFeatureLengthForMaterialOnItemTab", exc)

    # ExportThread.cs:863-947
    def add_material_to_item_tab(
        self, material: str, description: str, otherdescription: str, status: int, dependentoption: bool,
        issuper: bool, feature: str, info: str, featlen: int, childoptIds: list, stage: str,
    ) -> None:
        try:
            # logMessage(...) omitted: developer-machine hack (Environment.UserName == "dbacw8", C:\Downloads\log.txt)
            num = -1
            num = _to_integer(_item(childoptIds, 0))
            # debug-only block omitted (flag default false)
            flag = False
            if index_of(material, "#") > -1:
                flag = True
            material = material.replace("#", "")
            if (not list_contains(self._materialsOnItemTab, material)) & (not list_contains(self._convertedList, material)):
                # debug-only block omitted (flag default false)
                self._convertedList.append(material)
                text = tostr(self._convertedList[len(self._convertedList) - 1])
                text2 = text
                text2 = substring(text2, text2.rfind("-") + 1)
                if text.endswith("5-5"):
                    text2 = "5-5"
                elif text.endswith("5-6"):
                    text2 = "5-6"
                elif text.startswith("9-FAB-5-5") | text.startswith("9-FAB-5-6"):
                    text2 = text.replace("9-FAB-", "")
                # debug-only block omitted (flag default false)
                if (material.startswith("MRFN") | material.startswith("9-MRFN")) & (index_of(material, "-AJ-") > -1):
                    text2 = "AJ"
                self._convertedDesc.append(text2 + "|" + description)
                if otherdescription.strip() == "":
                    self._convertedOtherDesc.append("")
                else:
                    self._convertedOtherDesc.append(text2 + "|" + otherdescription)
                self._convertStatus.append(status)
                self._convertIsFab.append(flag)
                self._convertIsDepOpt.append(dependentoption)
                self._convertHasSuperParent.append(issuper)
                self._convertFeaturePos.append(feature)
                if featlen == -1:
                    featlen = self._prevConvertFeatLen
                self._convertFeatLen.append(featlen)
                self._convertChildFeatLen.append(-1)
                self._convertOptionId.append(num)
            # else: debug-only block omitted (flag default false)
        except Exception as exc:
            self.report_swallowed("addMaterialToItemTab", exc)

    # ExportThread.cs:949-984
    def is_integer(self, value: str) -> bool:
        result = True
        try:
            if value is None or value == "":  # VB CompareString treats null as ""
                result = False
            else:
                text = "0123456789-"
                num = len(value) - 1
                for i in range(0, num + 1):
                    self.check_abort()
                    if text.find(value[i]) == -1:
                        result = False
                        break
        except Exception as exc:
            self.report_swallowed("isInteger", exc)
            result = False
        return result

    # ExportThread.cs:1090-1121
    def get_translation(self, optvaldescs: list, optvaldescIds: list, optvaldesctrans: list,
                        optvaldesctransIds: list, index: int) -> str:
        result = ""
        try:
            if index < len(optvaldescs):
                result = tostr(_item(optvaldescs, index))
            if index < len(optvaldescIds):
                num = _to_integer(_item(optvaldescIds, index))
                num2 = list_index_of(optvaldesctransIds, num)
                if num2 > -1:
                    text = tostr(_item(optvaldesctrans, num2))
                    if text != "":
                        result = text
        except Exception as exc:
            self.report_swallowed("getTranslation", exc)
        return result

    # ExportThread.cs:1123-1197
    def get_item_sequence(self, myparentitem: str, thisordercode: str) -> int:
        result = 2
        try:
            num = list_index_of(self.sequenceForItems, myparentitem)
            if num == -1:
                self.sequenceForItems.append(myparentitem)
                arrayList = []
                arrayList.append(thisordercode)
                self.sequenceForItemsOrderCodes.append(arrayList)
                arrayList2 = []
                arrayList2.append(2)
                self.sequenceForItemsIndexes.append(arrayList2)
                result = 2
            else:
                # late-bound ArrayList.IndexOf(thisordercode)
                value = list_index_of(_item(self.sequenceForItemsOrderCodes, num), thisordercode)
                num2 = _to_integer(value)
                if num2 > -1:
                    # late-bound ArrayList.Item(num2)
                    value = _item(_item(self.sequenceForItemsIndexes, num), num2)
                    result = _to_integer(value)
                else:
                    _item(self.sequenceForItemsOrderCodes, num).append(thisordercode)
                    num3 = _to_integer(len(_item(self.sequenceForItemsIndexes, num)) + 2)
                    _item(self.sequenceForItemsIndexes, num).append(num3)
                    result = num3
        except Exception as exc:
            self.report_swallowed("getItemSequence", exc)
        return result

    # ExportThread.cs:1199-1282
    def get_knoll_fabric_order_code(self, optionId: int, optvalId: int, originalCode: str, colour: bool) -> str:
        result = originalCode
        # sqlConnection = ConnectionFactory.CreateNewConnection(autoOpen: true) -> self.q(_NEW_CONN, ...)
        try:
            text = ""
            text2 = ""
            text3 = ("SELECT optval_FT.OrderCodeValue AS FT_code, optval.OrderCodeValue AS FC_code FROM OptionValue optval "
                     "INNER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId "
                     "INNER JOIN OptionValue optval_FT on dov.OptionValueId = optval_FT.OptionValueId ")
            if not colour:
                text3 = text3 + "WHERE optval_FT.OptionId = ? AND optval_FT.OptionValueId = ?"
            else:
                text3 = text3 + "WHERE optval.OptionId = ? AND optval.OptionValueId = ?"
            rows = self.q(_NEW_CONN, text3, (optionId, optvalId))
            for row in rows:
                self.check_abort()
                text = tostr(row["FT_code"])
                text2 = tostr(row["FC_code"])
                if not colour:
                    break
            if (text != "") & (text2 != ""):
                if text in ("DR#", "CRO#", "FED#", "H0#", "PE#", "TEX#", "WE#", "ALP#", "CP#", "CI#", "CUR#",
                            "ESO#", "EX#", "IS#", "T#", "VI#", "D#", "FI#", "H#", "HL#", "MOO#", "TOS#",
                            "AN#", "COL#"):
                    result = text2 if colour else " "
                elif text == "EVA#":
                    result = substring(text2, 1) if colour else "1"
                elif text == "HER#":
                    result = substring(text2, 1) if colour else " "
                else:
                    if colour:
                        result = text2.replace(
                            text.replace("VOX", "VO").replace("ADY", "AD").replace("VPY", "VP")
                            .replace("AUY", "AU").replace("0Y", "0").replace("#", ""),
                            "",
                        )
        except Exception as exc:
            self.report_swallowed("GetKnollFabricOrderCode", exc)
        return result

    # ExportThread.cs:1284-1557
    def add_fabric_colour(self, converted: str, fabrictypeoptvalId: int, optvals: list, ignorecolour: bool) -> None:
        text = ""
        try:
            # text2 (debug log accumulator, only shown under debguFabricColourAddition) omitted
            if index_of(converted, "{DEBUG") > -1:
                text3 = substring(converted, index_of(converted, "{DEBUG"))
                text3 = substring(text3, 0, index_of(text3, "}") + 1)
                if text3 == "":
                    # C# string.Replace("", ...) throws ArgumentException
                    raise ValueError("String cannot be of zero length.")
                converted = converted.replace(text3, "")
            # sqlConnection = ConnectionFactory.CreateNewConnection(autoOpen: true) -> self.q(_NEW_CONN, ...)
            num = -1
            if index_of(converted, "-05#") > -1:
                num = net_int(substring(converted, index_of(converted, "-05#") - 2, 2))
                num += 5
            elif index_of(converted, "-04#") > -1:
                num = net_int(substring(converted, index_of(converted, "-04#") - 2, 2))
                num += 4
            elif index_of(converted, "-03#") > -1:
                num = net_int(substring(converted, index_of(converted, "-03#") - 2, 2))
                num += 3
            else:
                num = net_int(substring(converted, index_of(converted, "-02#") - 2, 2))
                num += 2
            text4 = ""
            text4 = str(num) if num >= 10 else "0" + str(num)
            num2 = -1
            text5 = substring(converted, converted.rfind("-") + 1)
            if converted.endswith("-5-5"):
                text5 = "5-5"
            elif converted.endswith("-5-6"):
                text5 = "5-6"
            # Data values are bound (?); the fixed fabric-type ids 278577/276392/278576/276673 are literals in legacy.
            like1 = (text5.replace("ALP", "AL").replace("VOX", "VO").replace("ADY", "AD")
                     .replace("VPY", "VP").replace("0Y", "0") + "%")
            text = ("SELECT optval.OptionValueId, opt.OptionId, optval.Name, optval.OrderCodeValue, optval.SupplierCode, "
                    "optval.Status, od.ShortDescription, parent_optval.OrderCodeValue AS parent_code, opt.SLFeatureLength "
                    "FROM OptionValue optval WITH (NOLOCK) INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId "
                    "INNER JOIN OtherDescription od ON optval.DescriptionId = od.DescriptionId "
                    "INNER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId "
                    "INNER JOIN OptionValue parent_optval ON dov.OptionValueId = parent_optval.OptionValueId "
                    "AND (parent_optval.OptionValueId = ? OR parent_optval.OptionValueId = 278577 /* ZB3# for CRB */ "
                    "AND 276392 = ? OR parent_optval.OptionValueId = 278576 /* ZNC# for CRB */ AND 276673 = ?) "
                    "WHERE opt.IsFabric = 2 And (optval.OrderCodeValue LIKE ?")
            params1: list = [fabrictypeoptvalId, fabrictypeoptvalId, fabrictypeoptvalId, like1]
            text6 = ""
            text6_params: list = []
            if is_knoll_catalogue(self._catalogueId):
                text6 = " OR optval.OrderCodeValue LIKE ?"
                text6_params.append("%" + text5.replace("CUR", "CU").replace("MOO", "MO").replace("ALP", "AL")
                                    .replace("VOX", "VO").replace("ADY", "AD").replace("VPY", "VP")
                                    .replace("AUY", "AU").replace("0Y", "0").replace("H0", "H"))
                text6 += ") AND opt.OptionId IN (8513, 8525, 8625) AND optval.OrderCodeValue NOT IN ('1103AL', '1107AL', '1114AL', '584TES', '991TES'"
                if text5 == "CUR":
                    text6 += ") AND (optval.OrderCodevalue LIKE '%CU'"
                if text5 == "CU":
                    text6 += ") AND (optval.OrderCodevalue LIKE 'CU%'"
                if text5 == "MOO":
                    text6 += ") AND (optval.OrderCodevalue LIKE '%MO'"
                if text5 == "MO":
                    text6 += ") AND (optval.OrderCodevalue LIKE 'MO%'"
                if text5 == "ALP":
                    text6 += ") AND (optval.OrderCodevalue LIKE '%AL'"
                if text5 == "AL":
                    text6 += ") AND (optval.OrderCodevalue LIKE 'AL%'"
                if text5 == "H0":
                    text6 += ") AND (LEN(optval.OrderCodevalue) = 3"
                if text5 == "H":
                    text6 += ") AND (LEN(optval.OrderCodevalue) = 4"
                if text5 == "VOX":
                    text6 += ") AND optval.OrderCodevalue NOT IN ('VO785', 'VO947', 'VOBLK'"
                if text5 == "ADY":
                    text6 += ") AND optval.OrderCodevalue NOT IN ('AD6006', 'AD6021', 'AD6040'"
                if text5 == "VPY":
                    text6 += ") AND optval.OrderCodevalue NOT IN ('VP03', 'VP04', 'VP280', 'VPBLK'"
                if text5 == "AUY":
                    text6 += ") AND optval.OrderCodevalue NOT IN ('AU601'"
                text += text6
                params1.extend(text6_params)
            text = text + ") AND optval.OrderCodeValue NOT LIKE '%#' AND od.LanguageId = ? ORDER BY opt.OptionId, optval.DisplayOrdinal"
            params1.append(self._languageId)
            rows = self.q(_NEW_CONN, text, tuple(params1))
            if not rows:  # !sqlDataReader.HasRows
                like2 = (text5.replace("ALP", "AL").replace("VOX", "VO").replace("ADY", "AD")
                         .replace("VPY", "VP").replace("AUY", "AU").replace("0Y", "0") + "%")
                text = ("SELECT optval.OptionValueId, opt.OptionId, optval.Name, optval.OrderCodeValue, optval.SupplierCode, "
                        "optval.Status, od.ShortDescription, parent_optval.OrderCodeValue AS parent_code, opt.SLFeatureLength "
                        "FROM OptionValue optval WITH (NOLOCK) INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId "
                        "INNER JOIN OtherDescription od ON optval.DescriptionId = od.DescriptionId "
                        "LEFT OUTER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId "
                        "LEFT OUTER JOIN OptionValue parent_optval ON dov.OptionValueId = parent_optval.OptionValueId "
                        "WHERE opt.IsFabric = 2 AND (optval.OrderCodeValue LIKE ?")
                params2: list = [like2]
                if is_knoll_catalogue(self._catalogueId):
                    text += text6
                    params2.extend(text6_params)
                # od.LanguageId = 1 is a literal constant in legacy (not a data value)
                text += ") AND optval.OrderCodeValue NOT LIKE '%#' AND od.LanguageId = 1 ORDER BY opt.OptionId, optval.DisplayOrdinal"
                rows = self.q(_NEW_CONN, text, tuple(params2))
            # debug-only block omitted (flag default false)
            for row in rows:
                self.check_abort()
                if list_contains(optvals, net_int(row["OptionValueId"])):
                    num3 = net_int(row["OptionId"])
                    if not (num2 == -1 or num2 == num3):
                        continue
                    num4 = 0.0
                    text7 = "9-FAB-" + tostr(row["OrderCodeValue"])
                    text8 = "-05"
                    if not ignorecolour:
                        text9 = tostr(row["OrderCodeValue"])
                        if num3 == 8513 or num3 == 8525 or num3 == 8625:
                            text9 = self.get_knoll_fabric_order_code(num3, net_int(row["OptionValueId"]), text9, True)
                        else:
                            num5 = -1  # assigned but never read in legacy
                            if len(text9) > 2:
                                if (index_of(converted, "-05#") > -1) & (len(tostr(row["parent_code"])) == 5):
                                    text9 = substring(text9, 5)
                                    num5 = 5
                                elif (index_of(converted, "-04#") > -1) & (len(tostr(row["parent_code"])) == 5):
                                    text9 = substring(text9, 4)
                                    num5 = 4
                                elif ((index_of(converted, "-03#") > -1) | (index_of(converted, "-04#") > -1)) & (len(tostr(row["parent_code"])) == 4):
                                    text9 = substring(text9, 3)
                                    num5 = 3
                                else:
                                    text9 = substring(text9, 2)
                                    num5 = 2
                        if converted == self.preConv:
                            self.ConvCount += 1
                        else:
                            self.ConvCount = 2
                        self.preConv = converted
                        if index_of(converted, "-03#") > -1:
                            text8 = "-04"
                        if index_of(converted, "-04#") > -1:
                            text8 = "-04"
                        # C# '&' is non-short-circuit: int.Parse(SLFeatureLength) is evaluated even when _length5Feats
                        if (not self._length5Feats) & (net_int(row["SLFeatureLength"]) > 2):
                            num6 = net_int(row["SLFeatureLength"])
                            if (num6 > 4) & ((index_of(converted, "-03#") > -1) | (index_of(converted, "-04#") > -1)):
                                num6 = 4
                            text8 = "-0" + str(num6)
                        if index_of(converted, "-05#") > -1:
                            text8 = "-05"
                        text10 = debug_feature_pos(text4 + text8, "AA")
                        self.materialstr = (self.materialstr + converted + "\tF" + text10 + "\t" + text7 + "\t" + text9
                                            + "\t" + tostr(num4) + "\t1\t0\t" + str(self.ConvCount) + "\t\t\t10\t\r\n")
                        num7 = list_index_of(self.allFabricColours, text7)
                        text11 = str(self.ConvCount)
                        # debugMaterialSequence is false: no "~~~~~~" prefix
                        if num7 == -1:
                            self.allFabricColours.append(text7)
                            self.allFabricColourSequences.append(text11)
                        else:
                            self.allFabricColourSequences[num7] = text11.replace("~~~~~~", "//////")
                    if len(self._convertFeatLen) > 0:
                        if self._convertFeatLen[len(self._convertFeatLen) - 1] == -1:
                            self._convertFeatLen[len(self._convertFeatLen) - 1] = net_int(text8.replace("-0", ""))
                        self._prevConvertFeatLen = net_int(text8.replace("-0", ""))
                    text12 = tostr(row["ShortDescription"]).replace(">", " ")
                    if tostr(row["SupplierCode"]) != "":
                        text12 = text12 + " (" + tostr(row["SupplierCode"]) + ")"
                    # text2 debug log append omitted
                    self.add_material_to_item_tab(
                        text7, text12, "", net_int(row["Status"]), False, False, "", " [none]",
                        net_int(text8.replace("-0", "")), [-1], self.threadStage,
                    )
                    num2 = num3
                # else: text2 debug log append omitted
            # debug-only block omitted (flag default false)
        except Exception as exc:
            self.report_swallowed("addFabricColour error\r\n\r\n" + text, exc)
