"""Stages 29-34 post-processing and the HRB branch (ExportThread.cs 5749-6325).

Mechanical transliteration; see PORTING_CONVENTIONS.md. Decompiled names are kept.
"""
from __future__ import annotations

from services.syteline_export.pipeline.netsem import (
    LegacyRangeError,
    debug_post_processed_feature_pos,
    index_of,
    list_contains,
    list_index_of,
    net_double,
    net_int,
    substring,
    tostr,
)
from services.syteline_export.pipeline.run_base import LOGGER, Flow


def _rindex(text: str, needle: str) -> int:
    """string.LastIndexOf(string) (ordinal)."""
    return text.rfind(needle)


def _fmt00(number: int) -> str:
    """int.ToString("00")."""
    return ("-" if number < 0 else "") + f"{abs(number):02d}"


class P08Mixin:
    def p08_postprocess(self) -> Flow | None:
        v = self.v
        # ExportThread.cs:5748 `ArrayList arrayList93 = new ArrayList();` (read again by stage 38, line 6745+)
        v.arrayList93 = []
        arrayList93 = v.arrayList93
        if not self._formatCSI and self._syteline:  # 5749 (`!_formatCSI & _syteline`)
            if self._catalogueId != 229:  # 5751
                arrayList94: list = []  # additional materials (clone of v.arrayList2 on first need)
                arrayList95: list = []  # distinct item codes whose dependent fabrics were looked up
                arrayList96: list = []  # parallel: list of dependent OrderCodeValues
                arrayList97: list = []
                arrayList98: list = []
                num182 = len(self.materialsWritten) - 1
                for num183 in range(0, num182 + 1):
                    self.threadStage = "30a"
                    text170 = ""
                    text171 = tostr(self.materialsWritten[num183])
                    text172 = substring(text171, 0, index_of(text171, "\t"))  # material parent
                    self.update_status_label(
                        "matl: " + text172 + "\r\n(" + str(num183 + 1) + " of " + str(len(self.materialsWritten)) + ")"
                    )
                    text171 = substring(text171, index_of(text171, "\t") + 1)
                    text173 = substring(text171, 0, index_of(text171, "\t"))
                    text171 = substring(text171, index_of(text171, "\t") + 1)
                    text174 = substring(text171, 0, index_of(text171, "\t"))  # component
                    text171 = substring(text171, index_of(text171, "\t") + 1)
                    text175 = substring(text171, 0, index_of(text171, "\t"))
                    text171 = substring(text171, index_of(text171, "\t") + 1)
                    text176 = substring(text171, 0, index_of(text171, "\t"))
                    self.threadStage = "30b"
                    text171 = substring(text171, index_of(text171, "\t") + 1)
                    text177 = substring(text171, 0, index_of(text171, "\t"))
                    text171 = substring(text171, index_of(text171, "\t") + 1)
                    text178 = substring(text171, 0, index_of(text171, "\t"))
                    text171 = substring(text171, index_of(text171, "\t") + 1)
                    text179 = text171
                    self.threadStage = "30c"
                    if index_of(text179, "\t") > -1:
                        text179 = substring(text179, 0, index_of(text179, "\t"))
                    flag22 = False
                    if text172.startswith("AX") and index_of(text172, "OX") > -1:
                        flag22 = True
                    if flag22:
                        continue
                    if index_of(text174, "-" + v.text6 + "-") > -1:
                        self.threadStage = "30d"
                        value7 = substring(text174, 0, _rindex(text174, "-"))
                        text180 = substring(text174, _rindex(text174, "-") + 1)
                        num184 = len(arrayList95) - 1
                        for num185 in range(0, num184 + 1):
                            arrayList99 = arrayList96[num185]
                            num186 = len(arrayList99) - 1
                            for num187 in range(0, num186 + 1):
                                if (
                                    (tostr(arrayList99[num187]).replace("#", "") == text180)
                                    and not tostr(arrayList95[num185]).startswith(value7)
                                ) and not list_contains(arrayList97, text172 + "_" + tostr(arrayList95[num185])):
                                    text170 = tostr(arrayList95[num185])
                                    arrayList97.append(text172 + "_" + tostr(arrayList95[num185]))
                                    break
                            if text170 != "":
                                break
                        if text170 == "" and not list_contains(arrayList95, text174):
                            arrayList100: list = []
                            # legacy concatenated text180 into the SQL; bound here (value = text180 + "#")
                            v.text = (
                                "SELECT DISTINCT optval.OrderCodeValue FROM OptionValue optval WITH (NOLOCK) "
                                "INNER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId "
                                "INNER JOIN OptionValue parent_optval ON dov.OptionValueId = parent_optval.OptionValueId "
                                "WHERE parent_optval.OrderCodeValue = ? AND optval.OrderCodeValue LIKE '%#'"
                            )
                            self.threadStage = "30e"
                            for row in self.q("c1", v.text, (text180 + "#",)):
                                arrayList100.append(tostr(row["OrderCodeValue"]))
                            arrayList95.append(text174)
                            arrayList96.append(arrayList100)
                    self.threadStage = "30f"
                    if index_of(text174, "-" + v.text6 + "-") > -1 and text170 != "":
                        if len(arrayList93) == 0:
                            for num189 in range(0, len(v.arrayList)):
                                arrayList93.append(tostr(v.arrayList[num189]))
                        if len(arrayList94) == 0:
                            for num191 in range(0, len(v.arrayList2)):
                                arrayList94.append(tostr(v.arrayList2[num191]))
                        num192 = -1
                        num193 = len(arrayList93) - 1
                        for num194 in range(0, num193 + 1):
                            self.threadStage = "30." + str(num194 + 1) + "-" + str(len(arrayList93))
                            if tostr(arrayList93[num194]).startswith(text170 + "\t"):
                                num192 = num194
                                break
                        if num192 > -1:
                            featpos = text174.replace("9-" + v.text6 + "-", "").replace("-" + text175, "")
                            featpos = debug_post_processed_feature_pos(featpos, "ZZ")
                            text181 = tostr(arrayList93[num192])
                            text182 = ""
                            if index_of(text181, "BOC") > -1:
                                text182 = substring(text181, index_of(text181, "BOC"))
                                if index_of(text182, featpos) == -1:
                                    text183 = ""
                                    if index_of(text182, "F") > -1:
                                        text183 = substring(text182, _rindex(text182, "F"))
                                        text183 = substring(text183, 0, index_of(text183, "\t"))
                                        value8 = text181.replace(text183 + "\t\t", text183 + "\t" + featpos + "\t")
                                        arrayList93[num192] = value8
                        num192 = -1
                        num195 = len(arrayList94) - 1
                        for num196 in range(0, num195 + 1):
                            self.threadStage = "30b." + str(num196 + 1) + "-" + str(len(arrayList94))
                            if tostr(arrayList94[num196]).startswith(
                                text170 + "\t" + text173 + "\t" + text174 + "\t" + text175 + "\t"
                            ):
                                num192 = num196
                                break
                        if num192 > -1:
                            arrayList94[num192] = tostr(arrayList94[num192]).replace(
                                text172 + "\t" + text173 + "\t" + text174 + "\t" + text175 + "\t" + text176 + "\t"
                                + text177 + "\t" + text178 + "\t" + text179,
                                text170 + "\t" + text173 + "\t" + text174 + "\t" + text175 + "\t" + text176 + "\t"
                                + text177 + "\t" + text178 + "\t1",
                            )
                    self.threadStage = "31"
                    if text170 != "":
                        continue
                    num197 = len(self.skippedFabricColours) - 1
                    for num198 in range(0, num197 + 1):
                        self.threadStage = "32a"
                        text184 = tostr(self.skippedFabricColours[num198])
                        if index_of(text184, "|") <= -1:
                            continue
                        text185 = substring(text184, index_of(text184, "|") + 1)
                        text186 = text175  # noqa: F841 (assigned, never read afterwards in legacy)
                        num199 = 1
                        if index_of(text185, "~") > -1:
                            num199 = net_int(substring(text185, index_of(text185, "~") + 1))
                            text185 = substring(text185, 0, index_of(text185, "~"))
                        if index_of(text185, ":") > -1:
                            text186 = substring(text185, index_of(text185, ":") + 1)  # noqa: F841
                            text185 = substring(text185, 0, index_of(text185, ":"))
                        self.threadStage = "32b"
                        if not (
                            (len(text185) < 4)
                            and text174.endswith("-" + text185)
                            and (index_of(text174, "-" + v.text6 + "-") == -1)
                        ):
                            continue
                        if len(arrayList93) == 0:
                            for num201 in range(0, len(v.arrayList)):
                                arrayList93.append(tostr(v.arrayList[num201]))
                        self.threadStage = "32.1"
                        if len(arrayList94) == 0:
                            for num203 in range(0, len(v.arrayList2)):
                                arrayList94.append(tostr(v.arrayList2[num203]))
                        self.threadStage = "32.2"
                        if not (index_of(text174, "-F01-") > -1 and num199 == 1):
                            continue
                        flag23 = False
                        text187 = ""
                        if text174.startswith("9-"):
                            text187 = substring(text174, index_of(text174, "9-") + 2)
                            if index_of(text187, "-") > -1:
                                text187 = substring(text187, 0, index_of(text187, "-"))
                                if not list_contains(self.itemHasFabrics, text187):
                                    flag23 = True
                        if flag23:
                            continue
                        text188 = "9-" + v.text6 + "-F01-" + _fmt00(len(text185)) + "-" + text185
                        num204 = -1
                        num205 = len(arrayList94) - 1
                        for num206 in range(0, num205 + 1):
                            self.threadStage = "32." + str(num206 + 1) + "-" + str(len(arrayList94))
                            if tostr(arrayList94[num206]).startswith(
                                text172 + "\t" + text173 + "\t" + text174 + "\t" + text175 + "\t"
                            ):
                                num204 = num206
                                break
                        self.threadStage = "32.3"
                        if num204 <= -1:
                            continue
                        arrayList94[num204] = tostr(arrayList94[num204]).replace(
                            text172 + "\t" + text173 + "\t" + text174 + "\t" + text175 + "\t" + text176 + "\t"
                            + text177 + "\t" + text178,
                            text172 + "\t" + text173 + "\t" + text188 + "\t" + text175 + "\t" + text176 + "\t"
                            + text177 + "\t" + text178,
                        )
                        if list_contains(arrayList98, text174):
                            continue
                        arrayList98.append(text174)
                        if list_index_of(arrayList93, text174 + "\t") <= -1:
                            continue
                        self.threadStage = "32.4"
                        text189 = text188.replace("9-" + v.text6 + "-", "").replace("-" + text175, "")
                        text190 = text189.replace("F", "")
                        if index_of(text190, "-") > -1:
                            num207 = net_int(substring(text190, 0, index_of(text190, "-")))
                            num208 = net_int(substring(text190, index_of(text190, "-") + 1))
                            text189 = "F" + _fmt00(num207 + num208) + "-05"
                            text189 = debug_post_processed_feature_pos(text189, "KK")
                        else:
                            text189 = debug_post_processed_feature_pos(text189, "kk")
                        self.threadStage = "32.5"
                        num209 = -1
                        num210 = len(arrayList93) - 1
                        for num211 in range(0, num210 + 1):
                            self.threadStage = "32b." + str(num211 + 1) + "-" + str(len(arrayList93))
                            if tostr(arrayList93[num211]).startswith(text174 + "\t"):
                                num209 = num211
                                break
                        if num209 <= -1:
                            continue
                        self.threadStage = "32.6"
                        text191 = tostr(arrayList93[num209])
                        text192 = ""
                        if index_of(text191, "BOC") > -1:
                            self.threadStage = "32.7"
                            text192 = substring(text191, index_of(text191, "BOC"))
                            if index_of(text192, text189) == -1:
                                text193 = ""
                                if index_of(text192, "F") > -1:
                                    text193 = substring(text192, _rindex(text192, "F"))
                                    text193 = substring(text193, 0, index_of(text193, "\t"))
                                    value9 = text191.replace(text193 + "\t\t", text193 + "\t" + text189 + "\t")
                                    arrayList93[num209] = value9
                            continue
                        self.threadStage = "32.8"
                        text194 = text191
                        text195 = "DEF\t1\t0\tEA\t\tP\t\tno\t\t\t\t\t0\t0\t\t\t"
                        if index_of(text194, text195) > -1:
                            text194 = substring(text194, 0, index_of(text194, text195))
                        text196 = ""
                        if index_of(text194, "\t") > -1:
                            text196 = substring(text194, 0, index_of(text194, "\t"))
                            text194 = substring(text194, index_of(text194, "\t"))
                        text197 = "DEF\t1\t0\tEA\t\tM\t\tno\t\t\t\tBOC\t0\t0\t\t" + text189 + "\t"
                        self.threadStage = "32.9"
                        num212 = -1
                        num213 = len(arrayList93) - 1
                        for num214 in range(0, num213 + 1):
                            self.threadStage = "32c." + str(num214 + 1) + "-" + str(len(arrayList93))
                            if tostr(arrayList93[num214]).startswith(text196 + text194 + text195):
                                num212 = num214
                                break
                        if num212 > -1:
                            arrayList93[num212] = tostr(arrayList93[num212]).replace(
                                text196 + text194 + text195, text188 + text194 + text197
                            )
                self.threadStage = "33"
                arrayList101: list = []
                arrayList102: list = []
                if len(arrayList94) > 0:
                    for num216 in range(0, len(arrayList94)):
                        arrayList102.append(tostr(arrayList94[num216]))
                else:
                    for num218 in range(0, len(self.materialsWritten)):
                        arrayList102.append(tostr(self.materialsWritten[num218]))
                # arrayList102 is a snapshot; arrayList94 is appended to while arrayList102 is walked
                # (6103-6113), so the loop bound is fixed up-front exactly like num219 in legacy.
                num219 = len(arrayList102) - 1
                for num220 in range(0, num219 + 1):
                    text198 = tostr(arrayList102[num220]).replace("\r", "").replace("\n", "")
                    text198 = text198.strip("\t")
                    if not list_contains(arrayList101, text198):
                        arrayList101.append(text198)
                        arrayList94.append(text198)
                self.threadStage = "33.5"
                if self._flattenFabrics:
                    num221 = len(arrayList94) - 1
                    for num222 in range(0, num221 + 1):
                        text199 = tostr(arrayList94[num222])
                        if index_of(text199, "9-FAB-F") > -1:
                            text200 = substring(text199, index_of(text199, "9-FAB-F"))
                            text201 = ""
                            text200 = substring(text200, 0, index_of(text200, "\t"))
                            if _rindex(text200, "-") > 5:
                                text201 = substring(text200, 0, 5) + substring(text200, _rindex(text200, "-"))
                            if text201 != "":
                                text199 = text199.replace(text200, text201)
                                arrayList94[num222] = text199
                self.threadStage = "34"
                if len(arrayList93) > 0:
                    # text202 accumulator is only a debug string in legacy; dropped.
                    num223 = len(arrayList93) - 1
                    for num224 in range(0, num223 + 1):
                        text203 = tostr(arrayList93[num224])
                        if not list_contains(self._additionalItemsWritten, text203):
                            self._additionalItemsWritten.append(text203)
                            LOGGER.debug("{POST} sheet1Data.Add(%s)", text203)  # logMessage
                            v.arrayList.append(text203)
                if len(arrayList94) > 0:
                    v.arrayList2 = []  # `arrayList2 = new ArrayList()` rebinding
                    # text204 accumulator is only a debug string in legacy; dropped.
                    num225 = len(arrayList94) - 1
                    for num226 in range(0, num225 + 1):
                        text205 = tostr(arrayList94[num226])
                        if not list_contains(self._additionalMaterialsWritten, text205):
                            self._additionalMaterialsWritten.append(text205)
                            v.arrayList2.append(text205)
            elif self._catalogueId == 229:  # 6172
                self.threadStage = "HRB"
                arrayList103: list = []
                arrayList104: list = []
                arrayList105: list = []
                arrayList106: list = []
                arrayList107: list = []
                arrayList108: list = []
                text206 = ""
                text207 = ""
                num227 = len(self.materialsWritten) - 1
                for num228 in range(0, num227 + 1):
                    text208 = tostr(self.materialsWritten[num228])
                    text209 = substring(text208, 0, index_of(text208, "\t"))
                    if text209.startswith("OF"):
                        if text207 != text209:
                            arrayList108.clear()
                        text207 = text209
                    r1 = text208.replace(text209 + "\t", "")
                    text210 = substring(r1, 0, index_of(r1, "\t"))
                    r2 = text208.replace(text209 + "\t", "").replace(text210 + "\t", "")
                    text211 = substring(r2, 0, index_of(r2, "\t"))
                    r3 = text208.replace(text209 + "\t", "").replace(text210 + "\t", "").replace(text211 + "\t", "")
                    text212 = substring(r3, index_of(r3, "\t") + 1)
                    text212 = substring(text212, 0, index_of(text212, "\t"))
                    text210 = text210.replace(text209 + "-", "")
                    text210 = text210.replace("bocfab-", "")
                    if text210.startswith("HAR-"):
                        if (index_of(text210, "F01-03") > -1) or (index_of(text210, "F07-03") > -1):
                            if list_index_of(arrayList104, text211) == -1:
                                arrayList104.append(text211)
                                arrayList106.append(text212)
                            if list_index_of(arrayList108, text211) == -1:
                                arrayList108.append(text211)
                        else:
                            text213 = text211
                            text213 = text207 + "~" + text211
                            if list_index_of(arrayList105, text213) == -1:
                                arrayList105.append(text213)
                                arrayList107.append(text212)
                        if len(arrayList103) == 0:
                            arrayList103.append(
                                "Parent Item\tFeature\tComponent\tOpt code\tInc. price\tMatl Qty\tScrap fact\tSeq\t"
                                "Effect Date\tObs Date\tOper Num\tBackFlush"
                            )
                    if (len(arrayList108) > 0) and (len(arrayList103) > 0):
                        text214 = tostr(self.materialsWritten[num228])
                        if (index_of(text214, text209 + "\t" + text209 + "-HAR-F01-03") > -1) or (
                            index_of(text214, text209 + "\t" + text209 + "-HAR-F07-03") > -1
                        ):
                            text214 = text214.replace(text209 + "\t" + text209 + "-HAR-F01-03", text209 + "\tHAR-F01-03")
                            text214 = text214.replace(text209 + "\t" + text209 + "-HAR-F07-03", text209 + "\tHAR-F07-03")
                            text214 = text214.replace(text212 + "\t1\t0", "0\t1\t0")
                        elif (index_of(text214, text209 + "\tbocfab-HAR-F08-03") > -1) or (
                            index_of(text214, text209 + "\tbocfab-HAR-F14-03") > -1
                        ):
                            text215 = text214.replace("\t\t\t10\t", "")
                            text215 = substring(text215, _rindex(text215, "\t") + 1)
                            text214 = text214.replace(
                                text209 + "\tbocfab-HAR-F08-03", tostr(arrayList108[0]) + "\t" + "HAR-F08-03"
                            )
                            text214 = text214.replace(
                                text209 + "\tbocfab-HAR-F14-03", tostr(arrayList108[0]) + "\t" + "HAR-F14-03"
                            )
                            text214 = text214.replace(text212 + "\t0\t0", text212 + "\t1\t0")
                            text214 = text214.replace(
                                text212 + "\t1\t0\t" + text215,
                                text212 + "\t1\t0\t" + str(net_int(text215) - len(arrayList108)),
                            )
                        text214 = text214.replace("\tHAR-F", "\tF")
                        text214 = text214.replace("-" + v.text6 + "-", "-")
                        text214 = text214.replace("-BOCFAB-", "-")
                        arrayList103.append(text214)
                    else:
                        text206 = text206 + tostr(self.materialsWritten[num228]) + "\r\n"
                if len(text206) > 0:
                    array12 = text206.split("\r")
                    num229 = len(array12) - 1
                    for num230 in range(num229, -1, -1):
                        if array12[num230] != "":
                            if len(arrayList103) < 1:
                                # ArrayList.Insert(1, x) on an empty list throws ArgumentOutOfRangeException
                                raise LegacyRangeError("ArrayList.Insert index 1 out of range for empty list")
                            arrayList103.insert(1, array12[num230])
                if (len(arrayList104) > 0) and (len(arrayList103) > 0):
                    v.arrayList2 = []  # `arrayList2 = new ArrayList()` rebinding
                    for num232 in range(0, len(arrayList103)):
                        value10 = tostr(arrayList103[num232]).replace("HAR-F", "H-F").replace("-bocfab-", "-BOCFAB-")
                        v.arrayList2.append(value10)
                num233 = len(arrayList104) - 1
                for num234 in range(1, num233 + 1):  # legacy starts at 1, not 0
                    text216 = tostr(arrayList104[num234])
                    text216 = text216.replace("9-BOCFAB-", "")
                    if index_of(text216, "-HAR-") > -1:
                        text216 = substring(text216, 0, index_of(text216, "-HAR-"))
                    num235 = len(arrayList105) - 1
                    for num236 in range(0, num235 + 1):
                        if tostr(arrayList105[num236]).startswith(text216 + "~"):
                            text217 = tostr(arrayList105[num236]).replace(text216 + "~", "")
                            text218 = tostr(arrayList104[num234]) + "\t"
                            text219 = text217
                            text219 = substring(text219, index_of(text219, "-HAR-") + 5)
                            text219 = substring(text219, 0, _rindex(text219, "-"))
                            text218 = text218 + text219 + "\t"
                            text218 = text218 + text217 + "\t"
                            num237 = net_double(arrayList106[num234])
                            text220 = substring(text217, _rindex(text217, "-") + 1)
                            num238 = net_double(arrayList107[num236])
                            text218 = text218 + text220 + "\t"
                            if not (num237 > num238):
                                text218 = text218 + tostr(num238) + "\t"
                            else:
                                text218 = text218 + tostr(num237) + "\t"
                            text218 = text218 + "1\t0\t" + str(num236 + 102) + "\t\t\t10\t"
                            if (index_of(text218, "BOCFAB-OF") > -1) and (index_of(text218, "2-HAR") > -1):
                                text218 = text218.replace("-BOCFAB-", "-")
                            array13 = text218.replace("HAR-F", "H-F").replace("-bocfab-", "-BOCFAB-").split("\r")
                            for num240 in range(0, len(array13)):
                                value11 = array13[num240].replace("\n", "")
                                v.arrayList2.append(value11)
        return None
