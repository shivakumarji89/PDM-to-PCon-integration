"""ExportThread.cs 6780-7032: stages 39-41 (F-code fix-ups, option column packing, BOM branch).

Transliteration; see PORTING_CONVENTIONS.md. Locals used only inside this range are plain
Python locals; ``arrayList`` (sheet 1 rows), ``arrayList2`` (sheet 2 rows), ``flag2`` and
``text14`` are assigned elsewhere and live in ``self.v``.
"""
from __future__ import annotations

from services.syteline_export.pipeline.netsem import (
    index_of, net_double, net_int, substring, tostr,
)
from services.syteline_export.pipeline.run_base import Flow


class P10Mixin:
    def p10_bom(self) -> Flow | None:
        v = self.v
        self.threadStage = "39"
        arrayList114 = []  # sheet2Items: item per sheet-2 row
        arrayList115 = []  # sheet2OptValIds: option value id per sheet-2 row
        if v.flag2:
            for num278 in range(len(v.arrayList)):
                self.check_abort()
                v.arrayList[num278] = tostr(v.arrayList[num278]).replace("F23-02", "F23-03")
                v.arrayList[num278] = tostr(v.arrayList[num278]).replace("F25-05", "F26-04")
                v.arrayList[num278] = tostr(v.arrayList[num278]).replace("F01-03\tF04-03\tF07-03\tF10-03\tF13-03\tF23-03", "F01-03\tF04-03\tF13-03\tF23-03\t\t\t")
                v.arrayList[num278] = tostr(v.arrayList[num278]).replace("F01-03\tF04-03\tF07-03\tF10-03\tF13-03\tF16-05", "F01-03\tF04-03\tF13-03\tF16-05\t\t\t")
                v.arrayList[num278] = tostr(v.arrayList[num278]).replace("F01-03\tF04-03\tF10-03\tF13-03\tF16-05\t", "F01-03\tF04-03\tF13-03\t\t")
                v.arrayList[num278] = tostr(v.arrayList[num278]).replace("F01-03\tF04-03\tF13-03\tF16-05\t", "F01-03\tF04-03\tF13-03\t\t")
                v.arrayList[num278] = tostr(v.arrayList[num278]).replace("\t\tF16-07\t", "\t\tF07-03\tF16-07")
                v.arrayList[num278] = tostr(v.arrayList[num278]).replace("\t\tF21-07\t", "\t\tF07-03\tF16-05\tF21-07")
                v.arrayList[num278] = tostr(v.arrayList[num278]).replace("\t\tF16-05\tF21-07\t", "\t\tF07-03\tF16-05\tF21-07")
            for num280 in range(len(v.arrayList2)):
                self.check_abort()
                v.arrayList2[num280] = tostr(v.arrayList2[num280]).replace("F23-02", "F23-03")
                v.arrayList2[num280] = tostr(v.arrayList2[num280]).replace("F25-04", "F26-04")
        for num282 in range(len(v.arrayList)):
            self.check_abort()
            s = tostr(v.arrayList[num282])
            if (((index_of(s, "9-CN1G") > -1) | (index_of(s, "9-CN1L") > -1) | (index_of(s, "9-CN1R") > -1))
                    & (index_of(s, "-F05-03-") > -1)) and (
                    index_of(s, "F08-03") > -1 and index_of(s, "F14-03") == -1):
                v.arrayList[num282] = s.replace("F08-03\t", "F08-03\tF14-03")
        for num284 in range(len(v.arrayList)):
            self.check_abort()
            text244 = tostr(v.arrayList[num284])
            text245 = ""
            if index_of(text244, "\t") == 0:
                continue
            text245 = substring(text244, 0, index_of(text244, "\t"))
            text246 = ""
            num285 = 0
            for num287 in range(len(v.arrayList2)):
                self.check_abort()
                right11 = ""
                text247 = ""
                row2 = tostr(v.arrayList2[num287])
                if index_of(row2, "\t") > -1:
                    right11 = substring(row2, 0, index_of(row2, "\t"))
                    text247 = substring(row2, index_of(row2, "\t") + 1)
                    text247 = substring(text247, 0, index_of(text247, "\t"))
                if text245 == right11 and index_of(text246, text247 + "\t") == -1:
                    text246 = text246 + text247 + "\t"
                    num285 += 1
            text248 = ""
            text249 = ""
            flag25 = False
            num288 = 1
            while True:  # do { ... } while (num288 <= 34); `continue` jumps to the condition
                self.check_abort()
                if index_of(text244, "\t") > -1:
                    text248 = text248 + substring(text244, 0, index_of(text244, "\t")) + "\t"
                    text244 = substring(text244, index_of(text244, "\t") + 1)
                    num288 += 1
                    if num288 <= 34:
                        continue
                    break
                flag25 = True
                break
            if flag25:
                continue
            num289 = 1
            while index_of(text244, "\t") > -1:
                self.check_abort()
                text244 = substring(text244, index_of(text244, "\t") + 1)
                num289 += 1
                if num289 > 20:
                    break
            text249 = text244
            text250 = text248
            text250 += text246
            num290 = num285 + 2
            for _ in range(num290, 21):
                self.check_abort()
                text250 += "\t"
            text250 += text249
            v.arrayList[num284] = text250
        if not self._formatCSI and self._exportBOMData:
            left14 = ""
            arrayList116 = []  # option value ids of the current item's option report
            arrayList117 = []  # OrderCodeValue2 of the current item's option report
            arrayList118 = []  # IncPriceBase of the current item's option report
            for num293 in range(len(v.arrayList2)):
                self.check_abort()
                text251 = tostr(v.arrayList2[num293])
                value12 = "[undefined]"
                num294 = -1
                text252 = ""
                if index_of(text251, "\t") > 0:
                    text253 = substring(text251, 0, index_of(text251, "\t"))
                    if index_of(text253, "BOCFAB") > -1:
                        text253 = v.text14
                    elif text253.startswith("9-"):
                        text253 = substring(text253, index_of(text253, "-") + 1)
                        if index_of(text253, "-") > -1:
                            text253 = substring(text253, 0, index_of(text253, "-"))
                    text254 = substring(text251, index_of(text251, "\t") + 1)
                    text255 = ""
                    num295 = 0.0
                    if index_of(text254, "\t") > -1:
                        text254 = substring(text254, index_of(text254, "\t") + 1)
                        if index_of(text254, "\t") > -1:
                            text256 = substring(text254, 0, index_of(text254, "\t"))
                            text252 = text256
                            text254 = substring(text254, index_of(text254, "\t") + 1)
                            if index_of(text254, "\t") > -1:
                                text255 = substring(text254, index_of(text254, "\t") + 1)
                                if index_of(text255, "\t") > -1:
                                    text255 = substring(text255, 0, index_of(text255, "\t"))
                                    num295 = net_double(text255)
                                text254 = substring(text254, 0, index_of(text254, "\t"))
                                if index_of(text256, "9-FAB-") > -1:
                                    text254 = text256.replace("9-FAB-", "")
                    num296 = -1
                    # legacy concatenated the item code into the SQL; bound here
                    text257 = "SELECT ItemId FROM Item WHERE Item = ?"
                    self.threadStage = "40"
                    for row in self.q("c2", text257, (text253,)):
                        self.check_abort()
                        num296 = net_int(row["ItemId"])
                    if num296 > -1:
                        if left14 != text253:
                            arrayList116 = []
                            arrayList117 = []
                            arrayList118 = []
                            self.threadStage = "41"
                            # legacy: CommandType.StoredProcedure with @item/@siteId
                            for row in self.q(
                                "c2", "EXEC PDMOptionDataReportWithIncBase @item = ?, @siteId = ?",
                                (text253, self._siteId),
                            ):
                                self.check_abort()
                                arrayList116.append(net_int(row["OptionValueId"]))
                                arrayList117.append(tostr(row["OrderCodeValue2"]))
                                if tostr(row["IncPriceBase"]) != "":
                                    arrayList118.append(net_double(row["IncPriceBase"]))
                                else:
                                    arrayList118.append(0)
                        num297 = -1
                        num298 = 1
                        while True:
                            self.check_abort()
                            for num300 in range(len(arrayList117)):
                                self.check_abort()
                                if ((text254 == tostr(arrayList117[num300]))
                                        | ((num298 == 2) & (text254 + "#" == tostr(arrayList117[num300])))) \
                                        and num295 == arrayList118[num300]:
                                    num297 = num300
                                    break
                            if num297 > -1:
                                break
                            num298 += 1
                            if not num298 <= 2:
                                break
                        if num297 > -1:
                            value12 = text253
                            num294 = int(arrayList116[num297])
                        left14 = text253
                    else:
                        # legacy shows a modal debug_form (developer dialog); recorded instead
                        self.warnings.append(
                            "unable to establish itemId for [" + text253 + "]\r\n\r\n" + text257)
                if index_of(text252, "9-FAB-") > -1:
                    arrayList114.append("[generic]")
                else:
                    arrayList114.append(value12)
                arrayList115.append(num294)
            from services.syteline_export.pipeline.bom_export import BomExport
            sytelineBOMExport = BomExport(
                self.db, v.arrayList, v.arrayList2, arrayList114, arrayList115,
                report_error=self.report_swallowed, stage=self.threadStage,
                abort_check=self.check_abort,
            )
            if sytelineBOMExport.generate_bom_data():
                v.arrayList = sytelineBOMExport.sheet1Data
                v.arrayList2 = sytelineBOMExport.sheet2Data
        return None
