"""Stage 17 (feature-length / feature-template resolution): ExportThread.cs 3587-4191.

Mechanical transliteration of the ``for (int num53 = 0; num53 <= num52; num53++)`` loop that runs inside the
per-item loop of ``execThread``. Read PORTING_CONVENTIONS.md first.

Helpers owned by other agents (same legacy names, snake_case): ``parse_opt_code``, ``add_material_to_item_tab``,
``add_fabric_colour``.

Preconditions (assigned by the preceding chunk, ExportThread.cs 3579-3586, which is NOT in this range):
``v.num7 = 0`` and ``v.num8 = -1`` (``SytelineExport.threadStage = "17"``). ``arrayList68``, ``text53``, ``left5``
and ``right2`` (3582-3585) are initialised here because nothing outside this range reads them.
"""
from __future__ import annotations
from core.cancellation import OperationCancelled

from services.syteline_export.pipeline.netsem import (
    debug_feature_pos,
    debug_feature_template,
    index_of,
    list_contains,
    list_index_of,
    net_bool,
    net_double,
    net_int,
    substring,
    tostr,
)
from services.syteline_export.pipeline.run_base import Flow


def _eq(a, b) -> bool:
    """VB ``Operators.CompareObjectEqual(a, b, false)`` for the int / bool / string operands used here."""
    if isinstance(b, str):
        return tostr(a) == b
    if isinstance(b, bool):
        return isinstance(a, bool) and a == b
    if isinstance(a, bool):
        a = -1 if a else 0
    elif isinstance(a, str):
        a = net_double(a)
    return a == b


def _ne(a, b) -> bool:
    return not _eq(a, b)


def _to_int(o) -> int:
    """``Conversions.ToInteger(o)``."""
    if isinstance(o, int) and not isinstance(o, bool):
        return o
    return net_int(o)


class P04Mixin:
    # ExportThread.cs:3587-4191
    def p04_feature_templates(self) -> Flow | None:
        v = self.v
        sd = v.sqlDataReader  # current item row (dict)

        def item() -> str:
            return tostr(sd["Item"])

        # ExportThread.cs:3582-3585. text53/left5/right2/text55/text54/text58 only build the [optdata] debug text that
        # is shown under SytelineExport.debugOptionData (default false): debug-only accumulators omitted.
        arrayList68 = []  # aeronFrameFinishMaterials

        num52 = len(v.arrayList45) - 1
        for num53_ in range(0, num52 + 1):  # num53_ == decompiled loop variable num53
            self.check_abort()
            flag9 = False
            if not (list_contains(v.arrayList18, v.arrayList45[num53_]) | (not self._syteline)):
                continue
            # (text54/left5 and text55/right2 blocks: debug-only text53 accumulation omitted, 3594-3613)
            if _eq(v.arrayList47[num53_], v.num8):
                continue
            v.num8 = _to_int(v.arrayList47[num53_])
            v.num7 += 1
            text56 = ""  # two-digit feature position prefix
            text57 = ""  # feature template for this option
            text56 = str(v.num6) if v.num6 >= 10 else "0" + str(v.num6)
            flag10 = False  # ignorecolour
            if num53_ > 0:
                if _eq(v.arrayList49[num53_], 2):
                    flag10 = True
            self.threadStage = "17.1"
            if _eq(v.arrayList49[num53_], 1):
                self.threadStage = "17.1a"
                text59 = self.parse_opt_code(
                    tostr(v.arrayList55[num53_]), _to_int(v.arrayList48[num53_]), _to_int(v.arrayList47[num53_])
                )
                num54 = len(substring(text59, index_of(text59, "|") + 1))
                if (
                    (num54 == 2)
                    & (substring(text59, index_of(text59, "|") + 1) == "9B")
                    & item().startswith("OF")
                ):
                    num54 = 3
                if (
                    _eq(v.arrayList47[num53_], 8512)
                    or _eq(v.arrayList47[num53_], 8524)
                    or _eq(v.arrayList47[num53_], 8624)
                    or (
                        (
                            _eq(v.arrayList47[num53_], 8513)
                            or _eq(v.arrayList47[num53_], 8525)
                            or _eq(v.arrayList47[num53_], 8625)
                        )
                        and self._flattenFabrics
                    )
                ):
                    num54 = 8 if self._flattenFabrics else 5
                if num54 == 5 or num54 == 8:
                    if num54 == 5:
                        text57 = v.text6 + "-F" + text56 + "-05#"
                        v.num6 += 10
                        v.text19 += "XXXXXXXXXX-"
                    else:
                        v.text6 = "FAB"
                        text57 = v.text6 + "-F" + text56 + "-08"
                        v.num6 += 8
                        v.text19 += "XXXXXXXX-"
                        if (item() == "420KIT") | (item() == "420KS"):
                            v.arrayList46.append(text57.replace("#", ""))
                    # debug-only block omitted (flag default false): debugItemFeatureTemplateResolutionForMaterials
                else:
                    if num54 == 4:
                        text57 = v.text6 + "-F" + text56 + "-04#"
                        if _eq(v.arrayList57[num53_], ""):
                            v.arrayList46.append(text57.replace("#", ""))
                        v.num6 += 8
                        if _eq(v.arrayList57[num53_], ""):
                            v.text19 += "XXXXXXXX-"
                    elif num54 == 3:
                        text57 = v.text6 + "-F" + text56 + "-03#"
                        if item().startswith("OF") & item().endswith("2"):
                            if not ((net_double(text56) == 8.0) | (net_double(text56) == 14.0)):
                                text57 = text57.replace("BOCFAB-", "BOCFAB-" + item() + "-HAR-")
                            else:
                                text57 = text57.replace("BOCFAB-", "bocfab-HAR-")
                        if _eq(v.arrayList57[num53_], ""):
                            v.arrayList46.append(text57.replace("#", ""))
                        v.num6 += 7
                        if _eq(v.arrayList57[num53_], ""):
                            v.text19 += "XXXXXXX-"
                    else:
                        num55 = 7
                        num56 = 2
                        flag11 = False  # cached
                        num57 = 2  # parent feature length
                        num58 = 5  # child feature length
                        if not self._length5Feats:
                            num59 = list_index_of(v.arrayList36, v.arrayList47[num53_])
                            if num59 > -1:
                                num57 = _to_int(v.arrayList37[num59])
                                num58 = _to_int(v.arrayList35[num59])
                                flag11 = True
                            else:
                                # id comes from an int column; bound as a parameter (conventions: no concatenation)
                                text60 = (
                                    "SELECT MAX(parent_opt.SLFeatureLength) AS parent_featlen, "
                                    "MAX(child_opt.SLFeatureLength) AS child_featlen FROM [Option] child_opt WITH (NOLOCK) "
                                    "INNER JOIN OptionValue optval ON child_opt.OptionId = optval.OptionId "
                                    "INNER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId "
                                    "INNER JOIN OptionValue parent_optval ON dov.OptionValueId = parent_optval.OptionValueId "
                                    "INNER JOIN [Option] parent_opt ON parent_optval.OptionId = parent_opt.OptionId "
                                    "WHERE parent_opt.OptionId = ?"
                                )
                                try:
                                    self.threadStage = "17.2a"
                                    # legacy opens a brand-new connection (sqlConnection7) for this query
                                    rows = self.q("c7", text60, (v.arrayList47[num53_],))
                                    for row in rows:
                                        self.check_abort()
                                        num57 = net_int(row["parent_featlen"])
                                        num58 = net_int(row["child_featlen"])
                                except OperationCancelled:
                                    raise
                                except Exception as exc:  # noqa: BLE001 - legacy catch (Exception) + MsgBox
                                    self.report_swallowed("17.2a option feature length: " + text60, exc)
                                v.arrayList37.append(num57)
                                v.arrayList35.append(num58)
                                v.arrayList36.append(v.arrayList47[num53_])
                            num56 = num57
                            num55 = num58 + num57
                            if 5 < num55 < 6:
                                num55 = 7
                        text61 = ""  # SytelineExport.debugFeatLength default false
                        text57 = v.text6 + "-F" + text56 + text61 + "-0" + str(num56) + "#"
                        if item().startswith("OF") & item().endswith("2"):
                            if not ((net_double(text56) == 8.0) | (net_double(text56) == 14.0)):
                                text57 = text57.replace("BOCFAB-", "BOCFAB-" + item() + "-HAR-")
                            else:
                                text57 = text57.replace("BOCFAB-", "bocfab-HAR-")
                        if _eq(v.arrayList57[num53_], ""):
                            v.arrayList46.append(text57.replace("#", ""))
                        v.num6 += num55
                        if _eq(v.arrayList57[num53_], ""):
                            for _ in range(1, num55 + 1):
                                self.check_abort()
                                v.text19 += debug_feature_template("X", "1")
                            v.text19 += "-"
            elif not flag10:
                self.threadStage = "17.1b"
                text62 = self.parse_opt_code(
                    tostr(v.arrayList55[num53_]), _to_int(v.arrayList48[num53_]), _to_int(v.arrayList47[num53_])
                )
                if (len(substring(text62, index_of(text62, "|") + 1)) > 2) & self._length5Feats:
                    self.threadStage = "17.2b"
                    text63 = substring(text62, index_of(text62, "|") + 1)
                    if index_of(text63, " ") > -1:
                        text57 = "F" + text56 + "-10"
                        v.num6 += 10
                        v.text19 += "XXXXXXXXXX-"
                    else:
                        text57 = "F" + text56 + "-05"
                        v.num6 += 5
                        v.text19 += "XXXXX-"
                    text57 = debug_feature_pos(text57, "BB:" + tostr(v.arrayList47[num53_]))
                else:
                    self.threadStage = "17.2c"
                    num62 = net_int(v.arrayList54[num53_])
                    if (num62 == 2) & (len(substring(text62, index_of(text62, "|") + 1)) > 2):
                        num62 = len(substring(text62, index_of(text62, "|") + 1))
                    if (num62 > 2) & self._length5Feats:
                        num62 = 5
                    text57 = "F" + text56 + "-0" + str(num62)
                    v.num6 += num62
                    for _ in range(1, num62 + 1):
                        self.check_abort()
                        v.text19 += debug_feature_template(
                            "X", "2#" + text57.replace("-", "~") + ":" + tostr(v.arrayList47[num53_])
                        )
                    v.text19 += "-"
                    text57 = debug_feature_pos(text57, "CC~len" + str(num62) + ":" + tostr(v.arrayList47[num53_]))
                    if self._uniqueComponents:
                        text64 = "[" + tostr(sd["Product_Code"]).replace("-", "").replace("_", "") + "]"
                        if ((index_of(text57, item() + "-") == -1) & (index_of(text57, text64 + "-") == -1)) & _eq(
                            v.arrayList60[num53_], 0
                        ):
                            if not self._plcPhantoms:
                                text57 = item() + "-" + text57
                            else:
                                text57 = text64 + "-" + text57
                        flag9 = True
                self.threadStage = "17.3"
                if (item().startswith("AER") & (not item().startswith("notAER1G"))) & _eq(v.arrayList47[num53_], 6431):
                    arrayList68.append("9-" + item() + "-" + text57 + "-CRB")
                    arrayList68.append("9-" + item() + "-" + text57 + "-VPR")
                    arrayList68.append("9-" + item() + "-" + text57 + "-G1")
                    if list_contains(v.arrayList16, 272082):
                        arrayList68.append("9-" + item() + "-" + text57 + "-BK")
                    if list_contains(v.arrayList16, 276007):
                        arrayList68.append("9-" + item() + "-" + text57 + "-MG1")
                    if list_contains(v.arrayList16, 276008):
                        arrayList68.append("9-" + item() + "-" + text57 + "-MCR")
                    if list_contains(v.arrayList16, 276009):
                        arrayList68.append("9-" + item() + "-" + text57 + "-MVR")
                    if list_contains(v.arrayList16, 276217):
                        arrayList68.append("9-" + item() + "-" + text57 + "-MBL")
                    if list_contains(v.arrayList16, 307282):
                        arrayList68.append("9-" + item() + "-" + text57 + "-DN2")
                    if list_contains(v.arrayList16, 307283):
                        arrayList68.append("9-" + item() + "-" + text57 + "-DJ2")
                    if list_contains(v.arrayList16, 307284):
                        arrayList68.append("9-" + item() + "-" + text57 + "-MN2")
                    if list_contains(v.arrayList16, 307285):
                        arrayList68.append("9-" + item() + "-" + text57 + "-MJ2")
                self.threadStage = "17.4"
                # VB OrObject/AndObject do not short-circuit: bool.Parse is always evaluated (and may throw)
                c174_a = _eq(v.arrayList57[num53_], "")
                c174_b1 = _eq(v.arrayList59[num53_], True)
                c174_b2 = net_bool(sd["IsSuperProduct"])
                c174_b = (c174_b1 and c174_b2) and (not v.flag4)
                if c174_a or c174_b:
                    # logMessage(...) omitted: developer-only log (logOutput && UserName == "dbacw8")
                    v.arrayList46.append(text57)
                elif (
                    _eq(v.arrayList57[num53_], "")
                    and _eq(v.arrayList59[num53_], False)
                    and _ne(v.arrayList49[num53_], 2)
                ):
                    # logMessage(...) omitted (developer-only)
                    text65 = text57
                    if (index_of(text65, "{") > -1) & (index_of(text65, "}") > -1):
                        text65 = substring(text65, 0, index_of(text65, "{")) + substring(
                            text65, index_of(text65, "}") + 1
                        )
                    num65 = 0
                    if index_of(text65, "-") > -1:
                        num65 = net_int(substring(text65, text65.rfind("-") + 1))
                    if num65 > 0:
                        for _ in range(1, num65 + 1):
                            self.check_abort()
                            v.text19 += debug_feature_template("X", "3")
                        v.text19 += "-"
            self.threadStage = "17.5"
            v.arrayList24.append(item() + "|[opt" + str(v.num7) + "]")
            v.arrayList25.append(text57)
            # text66 = materialstr is never read (dead store)
            self.materialstr = self.materialstr.replace("[opt" + str(v.num7) + "]", text57)
            self.materialstr = self.materialstr.replace("\t" + v.text6 + "-", "\t")
            self.threadStage = "17.6"
            text67 = item()
            if text67.startswith("AER") & (not text67.startswith("notAER1G")):
                v.flag2 = True
                if _eq(v.arrayList47[num53_], 6437):
                    self.threadStage = "17.7"
                    # text68 only feeds a debug message: omitted
                    text69 = ""  # -CRB
                    text70 = ""  # -VPR
                    text71 = ""  # -G1
                    left6 = ""  # -BK
                    text72 = ""  # -DN2
                    text73 = ""  # -DJ2
                    left7 = ""  # -MCR
                    left8 = ""  # -MVR
                    left9 = ""  # -MG1
                    left10 = ""  # -MBL
                    left11 = ""  # -MN2
                    left12 = ""  # -MJ2
                    for num69 in range(0, len(arrayList68)):
                        self.check_abort()
                        text74 = tostr(arrayList68[num69])
                        if (index_of(text74, text67) > -1) & text74.endswith("-G1"):
                            text71 = text74
                        if (index_of(text74, text67) > -1) & text74.endswith("-BK"):
                            left6 = text74
                        if (index_of(text74, text67) > -1) & text74.endswith("-CRB"):
                            text69 = text74
                        if (index_of(text74, text67) > -1) & text74.endswith("-VPR"):
                            text70 = text74
                        if (index_of(text74, text67) > -1) & text74.endswith("-DN2"):
                            text72 = text74
                        if (index_of(text74, text67) > -1) & text74.endswith("-DJ2"):
                            text73 = text74
                        if (index_of(text74, text67) > -1) & text74.endswith("-MCR"):
                            left7 = text74
                        if (index_of(text74, text67) > -1) & text74.endswith("-MVR"):
                            left8 = text74
                        if (index_of(text74, text67) > -1) & text74.endswith("-MG1"):
                            left9 = text74
                        if (index_of(text74, text67) > -1) & text74.endswith("-MBL"):
                            left10 = text74
                        if (index_of(text74, text67) > -1) & text74.endswith("-MN2"):
                            left11 = text74
                        if (index_of(text74, text67) > -1) & text74.endswith("-MJ2"):
                            left12 = text74
                    if text69 != "":
                        text75 = text67 + "\t" + text57 + "\t9-" + text57 + "-DCR\t"
                        if index_of(self.materialstr, text75) > -1:
                            text76 = substring(self.materialstr, index_of(self.materialstr, text75))
                            text76 = substring(text76, 0, index_of(text76, "\r\n"))
                            newValue = text69 + "\t" + text57 + "\t9-" + text57 + "-DCR\t"
                            text77 = text76.replace(text75, newValue)
                            if left7 != "":
                                text77 = text77 + "\r\n" + text77.replace("-CRB", "-MCR")
                            self.materialstr = self.materialstr.replace(text76, text77)
                    if text70 != "":
                        text78 = text67 + "\t" + text57 + "\t9-" + text57 + "-DVP\t"
                        if index_of(self.materialstr, text78) > -1:
                            text79 = substring(self.materialstr, index_of(self.materialstr, text78))
                            text79 = substring(text79, 0, index_of(text79, "\r\n"))
                            newValue2 = text70 + "\t" + text57 + "\t9-" + text57 + "-DVP\t"
                            text80 = text79.replace(text78, newValue2)
                            if left8 != "":
                                text80 = text80 + "\r\n" + text80.replace("-VPR", "-MVR")
                            self.materialstr = self.materialstr.replace(text79, text80)
                    if text72 != "":
                        text81 = text67 + "\t" + text57 + "\t9-" + text57 + "-DN4\t"
                        if index_of(self.materialstr, text81) > -1:
                            text82 = substring(self.materialstr, index_of(self.materialstr, text81))
                            text82 = substring(text82, 0, index_of(text82, "\r\n"))
                            newValue3 = text72 + "\t" + text57 + "\t9-" + text57 + "-DN4\t"
                            text83 = text82.replace(text81, newValue3)
                            if left11 != "":
                                text83 = text83 + "\r\n" + text83.replace("-DN2", "-MN2")
                            self.materialstr = self.materialstr.replace(text82, text83)
                    if text73 != "":
                        text84 = text67 + "\t" + text57 + "\t9-" + text57 + "-DJ4\t"
                        if index_of(self.materialstr, text84) > -1:
                            text85 = substring(self.materialstr, index_of(self.materialstr, text84))
                            text85 = substring(text85, 0, index_of(text85, "\r\n"))
                            newValue4 = text73 + "\t" + text57 + "\t9-" + text57 + "-DJ4\t"
                            text86 = text85.replace(text84, newValue4)
                            if left12 != "":
                                text86 = text86 + "\r\n" + text86.replace("-DJ2", "-MJ2")
                            self.materialstr = self.materialstr.replace(text85, text86)
                    if (text71 != "") | (left6 != ""):
                        text87 = text67 + "\t" + text57 + "\t9-" + text57 + "-BK\t"
                        if index_of(self.materialstr, text87) > -1:
                            text88 = substring(self.materialstr, index_of(self.materialstr, text87))
                            text88 = substring(text88, 0, index_of(text88, "\r\n"))
                            newValue5 = text71 + "\t" + text57 + "\t9-" + text57 + "-BK\t"
                            text89 = text88.replace(text87, newValue5)
                            text90 = text88.replace(text87, newValue5)
                            if left6 != "":
                                text89 = text89 + "\r\n" + text90.replace("-F04-03-G1", "-F04-03-BK")
                            if left9 != "":
                                text89 = text89 + "\r\n" + text90.replace("-F04-03-G1", "-F04-03-MG1")
                            if left10 != "":
                                text89 = text89 + "\r\n" + text90.replace("-F04-03-G1", "-F04-03-MBL")
                            if left11 != "":
                                text89 = text89 + "\r\n" + text90.replace("-F04-03-G1", "-F04-03-MN2")
                            if left12 != "":
                                text89 = text89 + "\r\n" + text90.replace("-F04-03-G1", "-F04-03-MJ2")
                            self.materialstr = self.materialstr.replace(text88, text89)
                    num70 = 10
                    while True:  # do { ... } while (num70 <= 99)
                        self.check_abort()
                        self.materialstr = self.materialstr.replace("DCR\t0\t1\t0\t" + str(num70), "DCR\t0\t1\t0\t4")
                        self.materialstr = self.materialstr.replace("DVP\t0\t1\t0\t" + str(num70), "DVP\t0\t1\t0\t4")
                        self.materialstr = self.materialstr.replace("DN4\t0\t1\t0\t" + str(num70), "DN4\t0\t1\t0\t4")
                        self.materialstr = self.materialstr.replace("DJ4\t0\t1\t0\t" + str(num70), "DJ4\t0\t1\t0\t4")
                        self.materialstr = self.materialstr.replace("BK\t0\t1\t0\t" + str(num70), "BK\t0\t1\t0\t4")
                        num70 += 1
                        if not (num70 <= 99):
                            break
                    self.materialstr = self.materialstr.replace("23103\t0\t1\t0\t4", "23103\t0\t1\t0\t5")
                    self.materialstr = self.materialstr.replace("23102\t0\t1\t0\t4", "23102\t0\t1\t0\t5")
                    self.materialstr = self.materialstr.replace("23101\t0\t1\t0\t4", "23101\t0\t1\t0\t5")
            self.threadStage = "17.8"
            # text53 debug text omitted
            self.preConv = ""
            self.ConvCount = 0
            # IsSuperProduct may be a bit (bool) or a number; VB compares bool with 0 numerically (False == 0)
            isp = sd["IsSuperProduct"]
            isp_zero = (not isp) if isinstance(isp, bool) else _eq(isp, 0)
            if not (isp_zero or v.flag4 or self._exportSPComponentMaterials):
                continue
            num71 = len(v.arrayList3) - 1
            num72 = 0
            while num72 <= num71:
                self.check_abort()
                comp = tostr(v.arrayList3[num72])
                opt_tag = "[opt" + str(v.num7) + "]"
                if index_of(comp, opt_tag) > -1:
                    self.threadStage = "17.9"
                    text91 = comp.replace(opt_tag, text57)
                    feature = ""
                    text92 = comp
                    if index_of(text92, "-" + item() + "-") > -1:
                        for num74 in range(0, len(v.arrayList65)):
                            self.check_abort()
                            if (index_of(tostr(v.arrayList65[num74]), text92) > -1) & (
                                index_of(tostr(v.arrayList65[num74]), "|") > -1
                            ):
                                feature = tostr(v.arrayList4[num74]).replace(opt_tag, text57)
                    elif list_index_of(v.arrayList65, comp) > -1:
                        feature = tostr(v.arrayList4[list_index_of(v.arrayList65, comp)]).replace(opt_tag, text57)
                    flag12 = False  # ignoreconvert
                    if (index_of(text91, v.text6 + "-") > -1) & (index_of(text91, "9-" + v.text6 + "-") == -1):
                        flag12 = True
                    self.threadStage = "17.10"
                    # debug-only block omitted (flag default false): debugItemsAndOptionsVerbose
                    # all three operands are always evaluated (non-short-circuit &), in this order
                    c1710_a = not list_contains(self._convertedList, text91.replace("#", ""))
                    c1710_b = not list_contains(self._convertedList, text91.replace("FAB-", "").replace("#", ""))
                    c1710_c = (
                        list_index_of(
                            self._convertedList, substring(text91, 0, 2) + v.text6 + "-" + substring(text91, 2)
                        )
                        == -1
                    )
                    if (c1710_a & c1710_b & c1710_c) and not flag12:
                        flag13 = False  # dependentoption
                        num75 = -1
                        if len(v.arrayList61[num53_]) > 0:
                            num75 = _to_int(v.arrayList61[num53_][0])
                        if (not flag9 or num75 > 0) & (index_of(text91, "-" + item() + "-") > -1):
                            flag13 = True
                        self.threadStage = "17.105"
                        self.add_material_to_item_tab(
                            text91,
                            tostr(v.arrayList5[num72]),
                            tostr(v.arrayList6[num72]),
                            _to_int(v.arrayList7[num72]),
                            flag13,
                            net_bool(sd["IsSuperProduct"]) and v.flag4,
                            feature,
                            comp
                            + ">>"
                            + tostr(v.arrayList45[num53_])
                            + ","
                            + tostr(v.arrayList47[num53_])
                            + ","
                            + tostr(v.arrayList55[num53_])
                            + ","
                            + tostr(v.arrayList49[num53_])
                            + ","
                            + tostr(v.arrayList57[num53_])
                            + ",["
                            + item()
                            + "]",
                            -1,
                            v.arrayList61[num53_],
                            self.threadStage,
                        )
                        if (
                            (index_of(text91, "-02#") > -1)
                            | (index_of(text91, "-03#") > -1)
                            | (index_of(text91, "-04#") > -1)
                            | (index_of(text91, "-05#") > -1)
                        ) & self._syteline:
                            self.add_fabric_colour(
                                text91, net_int(v.arrayList63[num72]), v.arrayList45, flag10
                            )
                    # else: text53 "ignoring [...]" debug text omitted
                # else: text53 "did not match" debug text omitted
                num72 += 1
            self.materialstr = (
                self.materialstr.replace("-02#", "-02")
                .replace("-03#", "-03")
                .replace("-04#", "-04")
                .replace("-05#", "-05")
            )
        # debug-only block omitted (flag default false): debugOptionData (4192-4197)
        return None
