"""HelpersMiscMixin: literal transliteration of ExportThread.cs helpers
getFeatureCount (709), GetShortProductCode (1559), getParentStartPos (1630), parseOptCode (1724),
formatCSIData (1744), GetProductDescription (1998), getFeatureLengthForItemOption (2031).
See PORTING_CONVENTIONS.md. Written independently of any other port in services/syteline_export.

Collaborators expected on the composed ExportRun (other agents' ranges):
  * ``is_integer(value)``                       <- isInteger (ExportThread.cs:949)
  * ``get_knoll_fabric_order_code(optionId, optvalId, originalCode, colour)`` <- cs:1199
"""
from __future__ import annotations

from services.syteline_export.pipeline.netsem import (
    index_of, list_index_of, net_int, substring, tostr,
)

# ConnectionFactory.CreateNewConnection(autoOpen: true) opens a fresh connection per call; it is not
# one of sqlConnection..sqlConnection5, so it gets its own session name.
NEW_CONN = "c6"


class HelpersMiscMixin:
    # ExportThread.cs:709-750
    def get_feature_count(self, superproduct):
        num = 0
        try:
            num2 = list_index_of(self._SPFeatureItems, superproduct)
            if num2 > -1:
                num = net_int(self._SPFeatureCount[num2])
            else:
                mysql = (
                    "SELECT max (len(itco.FeaturePositionString) - len(replace(itco.FeaturePositionString, '|', ''))) "
                    "AS optcount FROM ItemComponents itco INNER JOIN Item ON itco.ItemId = Item.ItemId "
                    "WHERE Item.Item = ?"
                )
                rows = self.q(NEW_CONN, mysql, (superproduct,))
                for row in rows:
                    if tostr(row["optcount"]) != "":
                        num = net_int(row["optcount"])
                self._SPFeatureItems.append(superproduct)
                self._SPFeatureCount.append(num)
        except Exception as exc:
            self.report_swallowed("getFeatureCount", exc)
        return num

    # ExportThread.cs:1559-1628
    def get_short_product_code(self, prodcode, rootproduct):
        text = ""
        text2 = prodcode
        try:
            if len(self.asiaUniveralScreenRoots) == 0:
                text = (
                    "SELECT DISTINCT SUBSTRING(Product.Product, 1, CHARINDEX('.', Product.Product)) AS RootProductPrefix "
                    "FROM Product INNER JOIN ProductOptionValues pov On Product.ProductId = pov.ProductId "
                    "INNER JOIN OptionValue optval ON pov.OptionValueId = optval.OptionValueId "
                    "WHERE optval.OptionId In (9277, 9275, 9313, 9281, 9279, 9325, 9285, 9283, 9327, 9289, 9287, 9329) "
                    "ORDER BY SUBSTRING(Product.Product, 1, CHARINDEX('.', Product.Product))"
                )
                rows = self.q(NEW_CONN, text)
                for row in rows:
                    self.asiaUniveralScreenRoots.append(tostr(row["RootProductPrefix"]))
            flag = False
            num = len(self.asiaUniveralScreenRoots) - 1
            for i in range(0, num + 1):
                if rootproduct.startswith(tostr(self.asiaUniveralScreenRoots[i])):
                    text3 = "S"
                    if tostr(rootproduct).endswith("B."):
                        text3 = "B"
                    text2 = "FRPD:" + text3
                    flag = True
                    break
            if not flag and (rootproduct.startswith("GHG") | rootproduct.startswith("GHS")):
                text4 = "M"
                if index_of(tostr(rootproduct), "M") == -1:
                    text4 = "D"
                text2 = "FRGH:" + text4
                flag = True
            if not flag:
                text2 = text2.replace("-", "")
                if len(text2) > 4:
                    text2 = substring(text2, 0, 4)
        except Exception as exc:
            self.report_swallowed("GetShortProductCode error (sql: " + text + ")", exc)
        return text2

    # ExportThread.cs:1630-1722. ref parentlength / ref substitutedoptcode: returns
    # (result, parentlength, substitutedoptcode). ``suffix`` is also reassigned inside (local only).
    def get_parent_start_pos(self, prefix, suffix, reverse, parentlength, substitutedoptcode):
        result = 1
        try:
            # (debug text accumulator `text` omitted: only shown under debug flags, default false)
            num = 0
            num2 = len(self.materialsWritten) - 1
            num3 = 1
            if reverse:
                num = num2
                num2 = 0
                num3 = -1
            flag = False
            num4 = num
            num5 = num2
            num6 = num3
            # C# `for (i = num4; ((num6>>31)^i) <= ((num6>>31)^num5); i += num6)`
            for i in range(num4, (num5 + 1) if num6 > 0 else (num5 - 1), num6):
                if index_of(tostr(self.materialsWritten[i]), "\t" + prefix) <= -1:
                    continue
                text2 = substring(
                    tostr(self.materialsWritten[i]),
                    index_of(tostr(self.materialsWritten[i]), "\t" + prefix),
                )
                text2 = text2.replace("{DEBUGAA}", "")
                text2 = text2.replace("{DEBUGBB}", "")
                text2 = text2.replace("{DEBUGCC}", "")
                text2 = text2.replace("{DEBUGDD}", "")
                text2 = text2.replace("{DEBUGEE}", "")
                text2 = text2.replace("{DEBUGFF}", "")
                text2 = text2.replace("{DEBUGII}", "")
                text2 = text2.replace("{DEBUGii}", "")
                num7 = 1
                while True:  # do { ... } while (num7 <= 2)
                    if num7 == 2 and (
                        ((suffix == "ON") | (suffix == "DE") | (suffix == "ES") | (suffix == "FI")
                         | (suffix == "ST") | (suffix == "WH") | (suffix == "LB") | (suffix == "LE")
                         | (suffix == "PE"))
                        & (index_of(text2, "-AT\t") > -1)
                    ):
                        suffix = "AT"
                        substitutedoptcode = "AT"
                    if index_of(text2, "-" + suffix + "\t") > -1:
                        text2 = substring(text2, 0, index_of(text2, "-" + suffix + "\t"))
                        if index_of(text2, "]-F") > -1:
                            text2 = substring(text2, index_of(text2, "]-F") + 3)
                            if index_of(text2, "-") > -1:
                                text3 = substring(text2, index_of(text2, "-") + 1)
                                if self.is_integer(text3):
                                    parentlength = net_int(text3)
                                text2 = substring(text2, 0, index_of(text2, "-"))
                                if self.is_integer(text2):
                                    result = net_int(text2)
                        flag = True
                        break
                    if flag:
                        break
                    num7 += 1
                    if not (num7 <= 2):
                        break
            # debug-only block omitted (flag default false)
        except Exception as exc:
            self.report_swallowed("getParentStartPos", exc)
        return result, parentlength, substitutedoptcode

    # ExportThread.cs:1724-1742
    def parse_opt_code(self, optcode, optvalId, optionId):
        try:
            optcode = optcode.replace("m", "").replace("c", "")
            if optionId == 8512 or optionId == 8524 or optionId == 8624:
                optcode = self.get_knoll_fabric_order_code(optionId, optvalId, optcode, False)
        except Exception as exc:
            self.report_swallowed("parseOptCode", exc)
        return optcode

    # ExportThread.cs:1744-1996. 212 tab separated columns terminated by CRLF.
    # ``volume`` is unused in legacy.
    def format_csi_data(self, myitem, issuper, shortdesc, statusflag, reasoncode, productcode,
                        volume, weight, UM, commcode, PM, template):
        text = ""
        try:
            arrayList = []
            arrayList.append(myitem)
            arrayList.append(shortdesc)
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append(myitem)
            arrayList.append("")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("1")
            arrayList.append(UM)
            arrayList.append("Material")
            if PM == "P":
                arrayList.append("Purchased")
            else:
                arrayList.append("Manufactured")
            arrayList.append(productcode)
            arrayList.append("C")
            arrayList.append("Actual")
            arrayList.append("Specific")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("1")
            arrayList.append(weight)
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("1")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("Job")
            arrayList.append("1")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("1")
            arrayList.append("1")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("Lead Time")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("1")
            arrayList.append("0")
            arrayList.append("&N")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("Lot – Lot Number")
            arrayList.append("Active")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("1")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append(commcode)
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("Never")
            arrayList.append("Prompt")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("1")
            arrayList.append("")
            arrayList.append(template.replace("X", "&"))
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("None")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("1")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("No-Pull-Up")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("1")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("-1")
            arrayList.append("")
            arrayList.append("")
            arrayList.append("No")
            arrayList.append("Yes")
            arrayList.append("No")
            arrayList.append("No")
            arrayList.append("No")
            arrayList.append("No")
            arrayList.append("")
            if PM == "P":
                arrayList.append("Purchased")
            else:
                arrayList.append("Manufactured")
            arrayList.append("Item")
            arrayList.append("30")
            arrayList.append("I")
            arrayList.append("")
            arrayList.append("No")
            arrayList.append("0")
            arrayList.append("0")
            arrayList.append("")
            arrayList.append("0")
            arrayList.append("No")
            arrayList.append("Yes")
            num = len(arrayList) - 1
            for i in range(0, num + 1):
                text += tostr(arrayList[i])
                if i < len(arrayList) - 1:
                    text += "\t"
            text += "\r\n"
        except Exception as exc:
            self.report_swallowed("formatCSIData", exc)
        return text

    # ExportThread.cs:1998-2029
    def get_product_description(self, myitem, shortdesc):
        text = ""
        try:
            text = (
                "SELECT DISTINCT attr.DisplayOrder, atval.AttributeValueId, atval.OrderCodeValue, od.ShortDescription "
                "FROM Item INNER JOIN BaseAttributeValues bav ON Item.ItemId = bav.ItemId "
                "INNER JOIN AttributeValue atval ON bav.AttributeValueId = atval.AttributeValueId "
                "INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId "
                "INNER JOIN OtherDescription od ON atval.DescriptionId = od.DescriptionId AND od.LanguageId = ? "
                "WHERE Item.Item = ? AND od.ShortDescription LIKE '% [[]%' ORDER BY attr.DisplayOrder"
            )
            rows = self.q(NEW_CONN, text, (self._languageId, myitem))
            for row in rows:
                text2 = tostr(row["ShortDescription"])
                text2 = substring(text2, index_of(text2, " [") + 2)
                text2 = substring(text2, 0, index_of(text2, "]"))
                shortdesc = shortdesc + " " + text2
        except Exception as exc:
            self.report_swallowed("GetProductDescription ERROR (sql: " + text + ")", exc)
        return shortdesc

    # ExportThread.cs:2031-2094
    def get_feature_length_for_item_option(self, myitem, optcodedesc):
        num = 2
        try:
            value = myitem + "~" + optcodedesc
            num2 = list_index_of(self.cachedItemOptFeatKeys, value)
            if num2 > -1:
                num = int(self.cachedItemOptFeatLens[num2])
            else:
                right = optcodedesc
                text2 = ""
                if index_of(optcodedesc, "|") > -1:
                    right = substring(optcodedesc, 0, index_of(optcodedesc, "|"))
                    text2 = substring(optcodedesc, index_of(optcodedesc, "|") + 1)
                num3 = -1
                # Deviation: legacy sends the bare "PDMOptionDataReport 'x'"; EXEC is needed to bind a parameter.
                rows = self.q(NEW_CONN, "EXEC PDMOptionDataReport ?", (myitem,))
                for row in rows:
                    if (tostr(row["ParentOptValCode"]) == right) & (
                        (tostr(row["ParentOptvalName"]) == text2) | (text2 == "")
                    ):
                        num3 = net_int(row["OptionId"])
                        break
                if num3 > -1:
                    # num3 comes from int.Parse; bound anyway
                    rows = self.q(NEW_CONN, "SELECT SLFeatureLength FROM [Option] WITH (NOLOCK) WHERE OptionId = ?", (num3,))
                    for row in rows:
                        num = net_int(row["SLFeatureLength"])
                self.cachedItemOptFeatKeys.append(value)
                self.cachedItemOptFeatLens.append(num)
        except Exception as exc:
            self.report_swallowed(
                "getFeatureLengthForItemOption ERROR (myitem: " + myitem + ", optcodedesc: " + optcodedesc + ")", exc)
        return num
