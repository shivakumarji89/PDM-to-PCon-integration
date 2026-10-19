"""Transliteration of PDMMaintenance/SytelineBOMExport.cs (whole class, lines 9-173).

``BomExport.generate_bom_data`` mutates the four lists IN PLACE, exactly like the C# class does
(the caller's ``arrayList``/``arrayList2``/``arrayList114``/``arrayList115`` are the same ArrayList
objects, ExportThread.cs:7022-7031). Read PORTING_CONVENTIONS.md first.

SQL connection: the legacy code opens a brand new ``ConnectionFactory.CreateNewConnection`` per
iteration (not one of ExportThread's five). They are used for single statements only (no temp
tables), so the port uses ONE dedicated session named ``BOM_CONNECTION`` ("cbom").
"""
from __future__ import annotations

from typing import Any, Callable

from services.syteline_export.pipeline.db import ExportDb
from services.syteline_export.pipeline.netsem import list_contains, net_double, tostr

BOM_CONNECTION = "cbom"

_CATEGORY_SQL = (
    "select  distinct pc.productcategoryid from item inner join Product ON Product.ProductId = Item.ProductId "
    "inner join productrange pr on product.productrangeid = pr.productrangeid "
    "inner join productcategory pc on pr.productcategoryid = pc.productcategoryid where item = ?"
)

# SytelineBOMExport.cs:100 and :147 (identical token sequences; verified programmatically).
# Field list of the tab-joined row (58 fields: material + 32 listed + 25 empty trailing fields).
_SHEET1_FIELDS = (
    "no", None, "A", "", "0", "0", "", "", "ZZ-ZZ", "0", "0", "yes", "35", "0", "0", "", "", "",
    "DEF", "1", "0", "EA", "", "P", "", "no", "", "", "", "", "0", "0",
) + ("",) * 25


def _net_replace(text: str, old: str, new: str) -> str:
    """string.Replace(old, new): .NET throws ArgumentException for an empty oldValue."""
    if old == "":
        raise ValueError("String cannot be of zero length. (Parameter 'oldValue')")
    return text.replace(old, new)


def _sheet1_row(material: Any, description: Any) -> str:
    # Operators.ConcatenateObject chain of SytelineBOMExport.cs:100/:147 (material is field 0).
    fields = [tostr(material)] + [tostr(description) if f is None else f for f in _SHEET1_FIELDS]
    return "\t".join(fields)


class BomExport:
    def __init__(
        self,
        db: ExportDb,
        sheet1Data: list,
        sheet2Data: list,
        sheet2Items: list,
        sheet2OptValIds: list,
        *,
        report_error: Callable[[str, BaseException], None] | None = None,
        stage: str = "",
    ) -> None:
        self.db = db
        self.sheet1Data = sheet1Data
        self.sheet2Data = sheet2Data
        self.sheet2Items = sheet2Items
        self.sheet2OptValIds = sheet2OptValIds
        self._report_error = report_error
        self._stage = stage
        self.errors: list[str] = []

    def _q(self, sql: str, params: tuple) -> list[dict[str, Any]]:
        return self.db.query(BOM_CONNECTION, sql, params, stage=self._stage)

    # SytelineBOMExport.cs:19-172
    def generate_bom_data(self) -> bool:
        try:
            sheet1Data = self.sheet1Data
            sheet2Data = self.sheet2Data
            sheet2Items = self.sheet2Items
            sheet2OptValIds = self.sheet2OptValIds

            num = len(sheet2Data) - 1
            i = num
            while i >= 0:
                array = tostr(sheet2Data[i]).split("\t")
                if array[0] == "":
                    del sheet2Data[i]
                    del sheet2Items[i]
                    del sheet2OptValIds[i]
                i += -1

            num2 = len(sheet2Items) - 1  # bound fixed once, as in C# (for-loop limit)
            for j in range(0, num2 + 1):
                if tostr(sheet2Data[j]) == "":
                    continue
                array2 = tostr(sheet2Data[j]).split("\t")
                text = array2[2]
                newValue = "9-" + array2[1] + "-" + tostr(sheet2Items[j]) + "-" + array2[3]
                sheet2Data[j] = _net_replace(tostr(sheet2Data[j]), text, newValue)
                num3 = len(sheet2Items) - 1
                for k in range(0, num3 + 1):
                    array3 = tostr(sheet2Data[k]).split("\t")
                    if array3[0] == text:
                        sheet2Items[k] = _net_replace(tostr(sheet2Items[k]), text, newValue)
                num4 = len(sheet1Data) - 1
                for l in range(0, num4 + 1):
                    array4 = tostr(sheet1Data[l]).split("\t")
                    if array4[0] == text:
                        sheet1Data[l] = _net_replace(tostr(sheet1Data[l]), text, newValue)

            num5 = len(sheet1Data) - 1
            for m in range(0, num5 + 1):
                array5 = tostr(sheet1Data[m]).split("\t")
                # C# uses non-short-circuit '&': array5[24] is evaluated even when the item starts with "9-".
                cond_a = not array5[0].startswith("9-")
                cond_b = array5[24] == "M"
                if not (cond_a and cond_b):
                    continue
                # CreateNewConnection(autoOpen: true) per item -> shared session BOM_CONNECTION.
                rows = self._q(_CATEGORY_SQL, (array5[0],))
                if len(rows) > 0:  # HasRows; sqlDataReader.Read() reads the first row
                    cmdText2 = "exec MaterialBOM 1, ?, ?, 0"
                    params2 = (array5[0], tostr(rows[0]["productcategoryid"]))
                    rows2 = self._q(cmdText2, params2)
                    if len(rows2) > 0:
                        num6 = 2
                        num7 = len(sheet2Data) - 1
                        for n in range(0, num7 + 1):
                            array6 = tostr(sheet2Data[n]).split("\t")
                            if array6[0] == array5[0] and net_double(array6[7]) >= float(num6):
                                num6 = round(net_double(array6[7]) + 1.0)
                        for r in rows2:
                            text2 = _sheet1_row(r["material"], r["description"])
                            if not list_contains(sheet1Data, text2):
                                sheet1Data.append(text2)
                            value = (
                                array5[0] + "\t\t" + tostr(r["material"]) + "\t" + "\t" + "0" + "\t"
                                + tostr(r["qty"]) + "\t" + "0" + "\t" + str(num6) + "\t" + "\t" + "\t"
                                + "10" + "\t"
                            )
                            sheet2Data.append(value)
                            num6 += 1

            num8 = len(sheet2Items) - 1
            for num9 in range(0, num8 + 1):
                if tostr(sheet2Data[num9]) == "":
                    continue
                array7 = tostr(sheet2Data[num9]).split("\t")
                left = array7[2]
                rows3 = self._q(_CATEGORY_SQL, (tostr(sheet2Items[num9]),))
                if len(rows3) > 0:
                    cmdText4 = "exec MaterialBOM 1, ?, ?, ?"
                    params4 = (
                        tostr(sheet2Items[num9]),
                        tostr(rows3[0]["productcategoryid"]),
                        tostr(sheet2OptValIds[num9]),
                    )
                    rows4 = self._q(cmdText4, params4)
                    if len(rows4) > 0:
                        num10 = 2
                        num11 = len(sheet2Data) - 1
                        for num12 in range(0, num11 + 1):
                            array8 = tostr(sheet2Data[num12]).split("\t")
                            if left == array8[0] and net_double(array8[7]) >= float(num10):
                                num10 = round(net_double(array8[7]) + 1.0)
                        for r in rows4:
                            text3 = _sheet1_row(r["material"], r["description"])
                            if not list_contains(sheet1Data, text3):
                                sheet1Data.append(text3)
                            value2 = (
                                array7[2] + "\t\t" + tostr(r["material"]) + "\t" + "\t" + "0" + "\t"
                                + tostr(r["qty"]) + "\t" + "0" + "\t" + str(num10) + "\t" + "\t" + "\t"
                                + "10" + "\t"
                            )
                            sheet2Data.append(value2)
                            num10 += 1
            return True
        except Exception as ex:  # catch (Exception) { MsgBox(ex.ToString()); result = false; }
            self.errors.append(f"{type(ex).__name__}: {ex}")
            if self._report_error is not None:
                self._report_error("SytelineBOMExport.generateBOMData", ex)
            return False
