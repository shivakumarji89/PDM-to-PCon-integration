"""ExportThread.cs 6326-6779: stage 35 (unique components / hard-coded rewrites), 35.1, 36, 37, 38.

Mechanical transliteration; see PORTING_CONVENTIONS.md. Locals shared with other ranges live on
``self.v``: ``arrayList`` (item-tab rows), ``arrayList2`` (material-tab rows), ``arrayList93``,
``text5`` ("yes" = fabric generation on) and ``text6`` (catalogue/range code used in "9-<text6>-").
"""
from __future__ import annotations

from services.syteline_export.pipeline.netsem import (
    debug_post_processed_feature_pos, index_of, is_knoll_catalogue, list_contains, list_index_of,
    net_int, substring, tostr,
)
from services.syteline_export.pipeline.run_base import Flow


def _fmt00(n: int) -> str:
    """C# ``int.ToString("00")``: at least two digits, '-' prefix for negatives."""
    return ("-" if n < 0 else "") + f"{abs(n):02d}"


class P09Mixin:
    def p09_item_material_patches(self) -> Flow | None:
        v = self.v
        self.threadStage = "35"
        arrayList = v.arrayList              # item tab rows (tab separated strings)
        arrayList2 = v.arrayList2            # material tab rows
        arrayList109 = []
        if self._uniqueComponents:
            for num242 in range(len(arrayList)):
                self.check_abort()
                text221 = tostr(arrayList[num242])
                text222 = substring(text221, 0, index_of(text221, "\t"))
                if text222.startswith("9-"):
                    text222 = substring(text222, 2)
                    if index_of(text222, "-") > -1:
                        text222 = substring(text222, 0, index_of(text222, "-"))
                if index_of(text221, "\t" + text222 + "-") > -1:
                    text221 = text221.replace("\t" + text222 + "-", "\t")
                if self._plcPhantoms and index_of(text221, "\t[") > -1:
                    text223 = substring(text221, index_of(text221, "\t[") + len("\t["))
                    text223 = substring(text223, 0, index_of(text223, "]"))
                    text221 = text221.replace("\t[" + text223 + "]-", "\t")
                if (index_of(text221, "9-FLC") > -1) & (index_of(text221, "0\t0\t\tF07-03\tF10-03") > -1):
                    text221 = text221.replace("0\t0\t\tF07-03\tF10-03", "0\t0\t\tF04-03\tF10-03")
                arrayList[num242] = text221
            for num244 in range(len(arrayList2)):
                self.check_abort()
                text224 = tostr(arrayList2[num244])
                text225 = substring(text224, 0, index_of(text224, "\t"))
                if text225.startswith("9-"):
                    text225 = substring(text225, 2)
                    if index_of(text225, "-") > -1:
                        text225 = substring(text225, 0, index_of(text225, "-"))
                if index_of(text224, "\t" + text225 + "-") > -1:
                    text224 = text224.replace("\t" + text225 + "-", "\t")
                if self._plcPhantoms and index_of(text224, "\t[") > -1:
                    text226 = substring(text224, index_of(text224, "\t[") + len("\t["))
                    text226 = substring(text226, 0, index_of(text226, "]"))
                    text224 = text224.replace("\t[" + text226 + "]-", "\t")
                if text224.startswith("9-FLC") & (index_of(text224, "-F01-03-") > -1) & (index_of(text224, "\tF07-03") > -1):
                    text224 = text224.replace("-F01-03-", "-F04-03-")
                arrayList2[num244] = text224
            if len(arrayList109) > 0:
                for num246 in range(len(arrayList109)):
                    self.check_abort()
                    arrayList2.append(tostr(arrayList109[num246]))
        for num248 in range(len(arrayList)):
            self.check_abort()
            text227 = tostr(arrayList[num248])
            if text227.startswith("CQND58") & (index_of(text227, "F01-03\tF10-07") > -1):
                text227 = text227.replace("F01-03\tF10-07", "F01-03\tF07-03\tF10-07")
                arrayList[num248] = text227
        self.threadStage = "35.1"
        arrayList109 = []
        flag24 = False
        for num250 in range(len(arrayList)):
            self.check_abort()
            s = tostr(arrayList[num250])
            if s.startswith("MG1") | s.startswith("SR1") | s.startswith("SR2") | s.startswith("SR3") | s.startswith("SR4"):
                flag24 = True
                break
        flag24 = False  # 6419: unconditional in legacy, so the two flag24 blocks below are dead (ported faithfully)
        if flag24:
            for num252 in range(len(arrayList)):
                self.check_abort()
                text228 = tostr(arrayList[num252])
                if text228.startswith("9-BOCFAB") & ((index_of(text228, "-ZB3\t") > -1) | (index_of(text228, "-ZNC\t") > -1)):
                    text229 = text228.replace("-ZB3\t", "-ZB3c\t").replace("-ZNC\t", "-ZNCc\t")
                    text229 = text229.replace("Beck ZB3", "Beck (CRB) ZB3").replace("Nico ZNC", "Nico (CRB) ZNC")
                    if not list_contains(arrayList, text229) and not list_contains(arrayList109, text229):
                        arrayList109.append(text229)
        if len(arrayList109) > 0:
            for num254 in range(len(arrayList109)):
                self.check_abort()
                arrayList.append(tostr(arrayList109[num254]))
        if flag24:
            for num256 in range(len(arrayList2)):
                self.check_abort()
                text230 = tostr(arrayList2[num256])
                if (index_of(text230, "-CRB\t") > -1) & (index_of(text230, "-ZB3\tZB3\t") > -1):
                    text230 = text230.replace("-ZB3\tZB3\t", "-ZB3c\tZB3\t")
                    arrayList2[num256] = text230
                elif (index_of(text230, "-CRB\t") > -1) & (index_of(text230, "-ZNC\tZNC\t") > -1):
                    text230 = text230.replace("-ZNC\tZNC\t", "-ZNCc\tZNC\t")
                    arrayList2[num256] = text230
                elif (index_of(text230, "-ZB3\t") > -1) & (
                    (index_of(text230, "9-FAB-ZB3A") > -1) | (index_of(text230, "9-FAB-ZB3B") > -1)
                    | (index_of(text230, "9-FAB-ZB3C") > -1) | (index_of(text230, "9-FAB-ZB3D") > -1)
                    | (index_of(text230, "9-FAB-ZB3E") > -1) | (index_of(text230, "9-FAB-ZB3F") > -1)
                ):
                    text230 = text230.replace("-ZB3\t", "-ZB3c\t")
                    arrayList2[num256] = text230
                elif (index_of(text230, "-ZNC\t") > -1) & (
                    (index_of(text230, "9-FAB-ZNCA") > -1) | (index_of(text230, "9-FAB-ZNCB") > -1)
                    | (index_of(text230, "9-FAB-ZNCC") > -1) | (index_of(text230, "9-FAB-ZNCD") > -1)
                ):
                    text230 = text230.replace("-ZNC\t", "-ZNCc\t")
                    arrayList2[num256] = text230
        self.threadStage = "36"
        # debug-only block omitted (flag default false): debugIncrements, debugItemFeatureTemplateResolutionForMaterials
        text231 = "2"  # material sequence (debugMaterialSequence is false)
        right10 = ""   # previous text240 (material key up to parent feature)
        if (not self._formatCSI) & (v.text5 == "yes"):
            # text232 (fabric debug text) is only ever displayed under debugSkippedFabricColours: omitted.
            num259 = 7
            num260 = 2
            arrayList110 = []
            self.threadStage = "37"
            for num262 in range(len(self.skippedFabricColours)):
                self.check_abort()
                self.threadStage = "37." + str(num262) + "-" + str(len(self.skippedFabricColours))
                text233 = tostr(self.skippedFabricColours[num262])
                if index_of(text233, "|") <= -1:
                    continue
                text234 = substring(text233, index_of(text233, "|") + 1)
                text235 = text234
                if index_of(text234, ":") > -1:
                    text235 = substring(text234, index_of(text234, ":") + 1)
                    if index_of(text235, "~") > -1:
                        text235 = substring(text235, 0, index_of(text235, "~"))
                    text234 = substring(text234, 0, index_of(text234, ":"))
                if not list_contains(arrayList110, "9-FAB-" + text234):
                    num263 = 0.0  # price/qty column of the material row
                    if len(text234) < 4:
                        continue
                    text236 = ""   # parent option code
                    text237 = ""
                    num264 = 0     # number of parent codes found
                    for num266 in range(len(self.skippedFabricColours)):
                        self.check_abort()
                        text238 = tostr(self.skippedFabricColours[num266])
                        if index_of(text238, "|") <= -1:
                            continue
                        text239 = substring(text238, index_of(text238, "|") + 1)
                        if index_of(text239, ":") > -1:
                            text237 = substring(text239, index_of(text239, ":") + 1)
                            if index_of(text237, "~") > -1:
                                text237 = substring(text237, 0, index_of(text237, "~"))
                            text239 = substring(text239, 0, index_of(text239, ":"))
                        if (len(text239) < len(text234)) & text234.startswith(text239):
                            text236 = text239
                            num264 += 1
                    if text236 == "":
                        text236 = substring(text234, 0, len(text234) - 2)
                        num264 = 1
                    num267 = num264
                    for num268 in range(1, num267 + 1):
                        self.check_abort()
                        self.threadStage = ("37." + str(num262) + "-" + str(len(self.skippedFabricColours))
                                            + "." + str(num268) + "~" + str(num264))
                        text240 = "9-" + v.text6 + "-"
                        num269 = len(text236)
                        if text236 == "CM0100":
                            num269 = 3
                        if num269 > num260:
                            num260 = num269
                        reverse = False
                        if num268 > 1:
                            reverse = True
                        parentlength = 0
                        substitutedoptcode = text236
                        # getParentStartPos(..., ref parentlength, ref substitutedoptcode) -> (result, parentlength, substitutedoptcode)
                        parentStartPos, parentlength, substitutedoptcode = self.get_parent_start_pos(
                            "9-" + v.text6, text236, reverse, parentlength, substitutedoptcode)
                        if parentlength > num260:
                            num260 = parentlength
                        if substitutedoptcode != text236:
                            text236 = substitutedoptcode
                        featpos2 = "F" + _fmt00(parentStartPos) + "-" + _fmt00(num260)
                        featpos2 = debug_post_processed_feature_pos(featpos2, "LL")
                        text240 = text240 + featpos2 + "-" + text236 + "\t"
                        if text240 != right10:
                            text231 = "2"
                            num270 = list_index_of(self.allSPFabricColours, text240)
                            if num270 == -1:
                                self.allSPFabricColours.append(text240)
                                arrayList111 = [text234]
                                self.allSPFabricColourCodes.append(arrayList111)
                                self.allSPFabricColourSequences.append(2)
                            else:
                                obj2 = list_contains(self.allSPFabricColourCodes[num270], text234)
                                if obj2 is False:
                                    arrayList112 = self.allSPFabricColourCodes[num270]
                                    arrayList112.append(text234)
                                    self.allSPFabricColourCodes[num270] = arrayList112
                                    self.allSPFabricColourSequences[num270] = self.allSPFabricColourSequences[num270] + 1
                                    text231 = tostr(self.allSPFabricColourSequences[num270])
                        else:
                            num271 = list_index_of(self.allSPFabricColours, text240)
                            if num271 == -1:
                                if index_of(text231, ">") > -1:
                                    text231 = substring(text231, index_of(text231, ">") + 1)
                                text231 = str(net_int(text231) + 1)
                            else:
                                obj2 = list_contains(self.allSPFabricColourCodes[num271], text234)
                                if obj2 is False:
                                    arrayList113 = self.allSPFabricColourCodes[num271]
                                    arrayList113.append(text234)
                                    self.allSPFabricColourCodes[num271] = arrayList113
                                    self.allSPFabricColourSequences[num271] = self.allSPFabricColourSequences[num271] + 1
                                    text231 = tostr(self.allSPFabricColourSequences[num271])
                        right10 = text240
                        self.threadStage = "38." + str(num262)
                        self.update_status_label(
                            "fabric: " + str(num262 + 1) + " of " + str(len(self.skippedFabricColours)))
                        text241 = "F" + _fmt00(parentStartPos + num260)
                        if is_knoll_catalogue(self._catalogueId):
                            num259 = 10
                        elif num260 == 4:
                            num259 = 8
                        text241 = text241 + "-" + _fmt00(num259 - num260)
                        text241 = debug_post_processed_feature_pos(text241, "MM")
                        text240 = text240 + text241 + "\t"
                        text242 = "9-FAB-" + text234
                        text240 += text242
                        num272 = list_index_of(self.allFabricColours, text242)
                        if num272 > -1:
                            text231 = tostr(self.allFabricColourSequences[num272])
                        text240 += "\t"
                        text240 = text240 + substring(text234, len(text236)) + "\t"
                        text240 = text240 + tostr(num263) + "\t1\t0\t"
                        text240 += text231
                        text240 += "\t\t\t10"
                        if index_of(text240, "9-FAB-CM01\t") == -1:
                            if not list_contains(self._additionalMaterialsWritten, text240):
                                arrayList2.append(text240)
                                self._additionalMaterialsWritten.append(text240)
                                arrayList110.append(text240)
                            text243 = text242 + "\tno\t" + text234 + "|" + text235 + "\t"
                            text243 = text243 + "A\t" + "\t0\t0\t" + "\t" + "\tZZ-ZZ\t"
                            text243 = text243 + "0\t0\tyes\t35\t0\t0\t" + "\t" + "\t" + "\t"
                            text243 = text243 + "DEF\t1\t0\tEA\t" + "\tP\t" + "\t"
                            text243 = text243 + "no\t" + "\t" + "\t" + "\t" + "\t0\t0\t" + "\t"
                            text243 += "\t" * 20  # do/while num273 = 1..20
                            text243 = text243 + "\t" + "\t" + "\t"
                            num274 = -1
                            for num276 in range(len(v.arrayList93)):
                                self.check_abort()
                                self.threadStage = ("38." + str(num262) + "." + str(num276 + 1) + "-"
                                                    + str(len(v.arrayList93)))
                                if tostr(v.arrayList93[num276]).startswith(text242 + "\t"):
                                    num274 = num276
                                    break
                            if (num274 == -1) & (not list_contains(self._additionalItemsWritten, text243)):
                                # logMessage("{6666} ...") omitted: dev-machine-only logging
                                arrayList.append(text243)
                                self._additionalItemsWritten.append(text243)
                        # else: legacy only records "EXCLUDED: 9-FAB-CM01" in debug text (omitted)
                # else: legacy only records "IGNORING" in debug text (omitted)
        return None
