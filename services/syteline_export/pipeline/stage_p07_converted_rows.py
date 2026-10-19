"""Stage P7: after the per-item loop, turn ``_convertedList`` into material rows
(ExportThread.cs 5427-5745; 5746-5747 only set ``threadStage`` "POST" then "29").

Mechanical transliteration; see PORTING_CONVENTIONS.md. Reads from ``self.v``: ``arrayList``
(sheet1Data rows, appended to), ``arrayList33``/``arrayList34`` (SLFeatureLength cache: value /
OptionId), ``streamWriter4`` (description file writer, may be None), ``text3`` (culture code),
``text6`` (BOCFAB prefix), ``prodcode``, ``rootproduct``.
"""
from __future__ import annotations

from services.syteline_export.pipeline.netsem import (
    debug_feature_pos,
    debug_post_processed_feature_pos,
    index_of,
    is_knoll_catalogue,
    list_index_of,
    net_int,
    substring,
    tostr,
)
from services.syteline_export.pipeline.run_base import Flow


def _fmt00(n: int) -> str:
    """C# ``int.ToString("00")`` (sign kept in front of the zero padded digits)."""
    return ("-" if n < 0 else "") + f"{abs(n):02d}"


class P07Mixin:
    # ExportThread.cs:5427-5745
    def p07_converted_rows(self) -> Flow | None:
        v = self.v
        # sqlDataReader.Close() (5427): rows are already fully fetched, nothing to close.
        self.threadStage = "25"
        text147 = ""  # all materialsWritten lines joined with CRLF
        for num165 in range(len(self.materialsWritten)):
            text147 = text147 + tostr(self.materialsWritten[num165]) + "\r\n"
        # text148 (debug-only report text, shown only under a debug flag) omitted
        # debug-only block omitted (flag default false)
        if not self._abortThread and not self._millerCAD:
            for num167 in range(len(self._convertedList)):
                item = tostr(self._convertedList[num167])
                if not (index_of(item, "--") == -1 and (not item.startswith("9-") or not self._superProductsOnly)):
                    continue
                text149 = "A"  # status flag
                text150 = ""  # reason code
                text152 = "yes"  # plan flag
                flag19 = True  # allowSPoptiondependencies
                if self._convertIsFab[num167] is False and (
                    self._convertIsDepOpt[num167] is False
                    or (self._convertHasSuperParent[num167] is True and not flag19)
                ):
                    text152 = "no"
                text153 = "M"  # M/P type
                right8 = ""
                right9 = "BOC"  # brand
                text154 = ""  # feature position
                text155 = ""  # slots

                if self._convertIsFab[num167] is True:
                    self.threadStage = "26a"
                    text156 = "FAB-F"
                    text157 = "FAB[" + self.get_short_product_code(v.prodcode, v.rootproduct) + "]-F"
                    if (index_of(item, "FAB-F") == -1) & (index_of(item, "-HAR-F") > -1):
                        text156 = "-HAR-F"
                    num168 = 0
                    num169 = 0
                    if index_of(item, text157) > -1:
                        if self.is_integer(substring(item, index_of(item, text157) + len(text157), 2)):
                            num168 = net_int(substring(item, index_of(item, text157) + len(text157), 2))
                        if self.is_integer(substring(item, index_of(item, text157) + len(text157) + 3, 2)):
                            num169 = net_int(substring(item, index_of(item, text157) + len(text157) + 3, 2))
                    else:
                        if self.is_integer(substring(item, index_of(item, text156) + len(text156), 2)):
                            num168 = net_int(substring(item, index_of(item, text156) + len(text156), 2))
                        if self.is_integer(substring(item, index_of(item, text156) + len(text156) + 3, 2)):
                            num169 = net_int(substring(item, index_of(item, text156) + len(text156) + 3, 2))
                    num168 += num169
                    text154 = ("F" + str(num168)) if num168 >= 10 else ("F0" + str(num168))
                    num170 = 7 - num169  # feature length
                    if is_knoll_catalogue(self._catalogueId):
                        num170 = 10 - num169
                    if (num169 == 4) & self.includesCOM:
                        num170 = 4
                    if num170 > 5:
                        num170 = 5
                    # text148 debug text omitted
                    text154 = text154 + "-0" + str(num170)
                    text154 = debug_post_processed_feature_pos(text154, "II")
                elif self._convertIsDepOpt[num167] is True:
                    self.threadStage = "26b"
                    text154 = substring(item, 2)
                    text158 = text154
                    if (index_of(text158, "{") > -1) & (index_of(text158, "}") > -1):
                        text158 = substring(text158, 0, index_of(text158, "{")) + substring(text158, index_of(text158, "}") + 1)
                    text159 = substring(text158, text158.rfind("-") + 1)  # unused later (kept: can throw)
                    text158 = substring(text158, 0, text158.rfind("-"))
                    num171 = text158.rfind("-F")
                    if (num171 < 4) & (len(text158) > 5):
                        num171 = substring(text158, 4).rfind("-F") + 4
                    num172 = 2  # feature length
                    num173 = list_index_of(v.arrayList34, self._convertOptionId[num167])
                    flag20 = False  # read from cache
                    flag21 = False  # read from child feature length
                    if num173 > -1:
                        num172 = int(v.arrayList33[num173])
                        flag20 = True
                    elif self._convertOptionId[num167] > -1:
                        v.text = "SELECT SLFeatureLength FROM [Option] WITH (NOLOCK) WHERE OptionId = ?"
                        rows = self.q("c2", v.text, (self._convertOptionId[num167],))
                        for row in rows:
                            num172 = net_int(row["SLFeatureLength"])
                        if self._flattenFabrics and (
                            self._convertOptionId[num167] == 8512
                            or self._convertOptionId[num167] == 8524
                            or self._convertOptionId[num167] == 8624
                        ):
                            num172 = 8
                        v.arrayList33.append(num172)
                        v.arrayList34.append(self._convertOptionId[num167])
                        flag20 = True
                    if num171 > -1:
                        num174 = net_int(substring(text158, num171 + 2, 2))
                        num175 = net_int(substring(text158, num171 + 5, 2))
                        num174 += num175
                        if not flag20:
                            if self._convertChildFeatLen[num167] > -1:
                                num172 = int(self._convertChildFeatLen[num167])
                                flag21 = True
                            else:
                                num172 = int(self._convertFeatLen[num167])
                        if (num172 > 2) & self._length5Feats:
                            num172 = 5
                        text158 = ("F" + str(num174)) if num174 >= 10 else ("F0" + str(num174))
                        if (
                            (index_of(text154, "-m") > -1) | (index_of(text154, "-c") > -1)
                            | text154.endswith("-M") | text154.endswith("-C")
                        ) & (not is_knoll_catalogue(self._catalogueId)):
                            num172 = 3
                        text158 = text158 + "-0" + str(num172)
                    text154 = debug_feature_pos(
                        text158,
                        "ii~len" + str(num172) + "(readcache=" + tostr(flag20) + ", readchild = " + tostr(flag21)
                        + "):" + tostr(self._convertOptionId[num167]),
                    )
                    # text148 debug text omitted
                    text160 = item
                    text161 = text147
                    text162 = ""
                    if self._uniqueComponents:
                        text162 = substring(text160, 2)
                        if index_of(text162, "-") > -1:
                            text162 = substring(text162, 0, index_of(text162, "-") + 1)
                    text163 = text160 + "\t" + text162 + "F"
                    if index_of(text161, text163) > -1:
                        while index_of(text161, text163) > -1:
                            text161 = substring(text161, index_of(text161, text163) + len(text163) - 1)
                            text164 = substring(text161, 0, index_of(text161, "\t"))  # throws if no tab (legacy 5603)
                            if index_of(text164, "-") > -1 and index_of(text155, text164) == -1:
                                text155 = text155 + text164 + "\t"
                else:
                    self.threadStage = "26c"
                    if index_of(item, "-05-") > -1:
                        text154 = substring(item, index_of(item, "-05-") - 3, 6)  # throws if < 3 chars before (5616)
                    if index_of(item, "-04-") > -1:
                        text154 = substring(item, index_of(item, "-04-") - 3, 6)
                    if index_of(item, "-03-") > -1:
                        text154 = substring(item, index_of(item, "-03-") - 3, 6)
                text154 = text154.replace(v.text6 + "-", "")
                if text152 == "no":
                    text153 = "P"
                    right8 = ""
                    right9 = ""
                    text154 = ""
                if text155 == "":
                    text155 = text154
                    if item.startswith("9-BOCFAB-OF") & (index_of(item, "2-HAR-F") > -1):
                        if text155 == "F04-04":
                            text155 = "F04-04\tF08-03"
                        if text155 == "F10-04":
                            text155 = "F10-04\tF14-03"
                self.threadStage = "27"
                num176 = 7
                if self.includesCOM:
                    num176 = 8
                if is_knoll_catalogue(self._catalogueId):
                    num176 = 10 if not self._flattenFabrics else 8
                if (text155 == "") & (index_of(item, "BOCFAB") > -1):
                    text165 = item
                    if index_of(text165, "-F") > -1:
                        text166 = substring(text165, index_of(text165, "-F") + 2)
                        if index_of(text166, "-") > -1 and self.is_integer(substring(text166, 0, index_of(text166, "-"))):
                            num177 = net_int(substring(text166, 0, index_of(text166, "-")))
                            text166 = substring(text166, index_of(text166, "-") + 1)
                            if index_of(text166, "-") > -1:
                                text166 = substring(text166, 0, index_of(text166, "-"))
                                if self.is_integer(text166):
                                    num178 = net_int(text166)
                                    text155 = "F" + _fmt00(num177 + num178) + "-" + _fmt00(num176 - num178)
                                    text155 = debug_post_processed_feature_pos(text155, "JJ")
                self.log_message("slots:\r\n" + item + "\r\n" + text155)
                # text148 debug text omitted
                num179 = 0.0  # volume
                num180 = 0.0  # weight
                text167 = ""  # output row
                if net_int(self._convertStatus[num167]) != 1:
                    text149 = "O"
                    status = net_int(self._convertStatus[num167])
                    if status == 0:
                        text150 = "URL"
                    elif status == 2:
                        text150 = "OBS"
                    elif status == 3:
                        text150 = "ON HOLD"
                self.threadStage = "28"
                desc = tostr(self._convertedDesc[num167])
                if self._syteline:
                    text167 = "".join([
                        item, "\t", "no", "\t", desc, "\t", text149, "\t", text150, "\t", "0", "\t", "0", "\t",
                        "\t", "\t", "ZZ-ZZ", "\t", tostr(num179), "\t", tostr(num180), "\t", "yes", "\t", "35",
                        "\t", "0", "\t", "0", "\t", "\t", "\t", "\t", "DEF", "\t", "1", "\t", "0", "\t", "EA",
                        "\t", "\t", text153, "\t", right8, "\t", "no", "\t", "", "\t", "\t", "\t", right9, "\t",
                        "0", "\t", "0", "\t", "\t", text155,
                    ])
                    num181 = 0
                    while True:
                        text167 += "\t"
                        num181 += 1
                        if not (num181 <= 4):
                            break
                else:
                    text167 = "".join([
                        item, "\t", "no", "\t", desc, "\t", text149, "\t", "0", "\t", "ZZ-ZZ", "\t", "",
                    ])
                text167 += "\r\n"
                if self._formatCSI:
                    text167 = self.format_csi_data(
                        item, "no", desc, text149, text150, "ZZ-ZZ", num179, num180, "EA", "", text153, "",
                    )
                elif self._flattenFabrics and text167.startswith("9-FAB-F"):
                    text168 = substring(text167, 0, index_of(text167, "\t"))
                    text169 = ""
                    if text168.rfind("-") > 5:
                        text169 = substring(text168, 0, 5) + substring(text168, text168.rfind("-"))
                    if text169 != "":
                        text167 = text167.replace(text168, text169)
                # logMessage argument is still evaluated in legacy (throws if no tab)
                self.log_message("{5555} sheet1Data.Add(" + substring(text167, 0, index_of(text167, "\t")) + ")")
                v.arrayList.append(text167)
                if (tostr(self._convertedOtherDesc[num167]) != "") and (self._languageId != self._otherlanguageId):
                    self.write_data(
                        v.streamWriter4,
                        v.text3 + "\t" + item + "\t" + tostr(self._convertedOtherDesc[num167]) + "\r\n",
                        False,
                    )
        self.threadStage = "POST"
        self.threadStage = "29"
        return None
