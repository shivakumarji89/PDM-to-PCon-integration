"""P11: write the item/material files, finish the run, error handler and ``finally`` (ExportThread.cs 7033-7483).

Legacy try-structure of execThread (ExportThread.cs 2194 ``try {`` ... 7432 ``catch (Exception ex13)`` ...
7455 ``finally``): the body stages run inside one ``try``.  Normal end of the body -> ``p11_write_outputs``
(7033-7430) is the last thing the try block does; any exception raised anywhere in the try body (including
inside ``p11_write_outputs``) jumps to the catch (``p11_on_error``, 7432-7454) and then ALWAYS ``p11_finally``
(7455-7480).  The ``return;`` statements inside the try body also run ``p11_finally`` (but not the catch).
The integrator must therefore call::

    try:
        ... stages ..., flow = self.p11_write_outputs()
    except Exception as exc:
        self.p11_on_error(exc)
    finally:
        self.p11_finally()

Legacy facts about the finally: it closes streamWriter2/3/4, releases ExtractUser when ``text4 == ""`` and
closes sqlConnection..4 (sqlConnection5 is never closed in legacy).
"""
from __future__ import annotations
from core.cancellation import OperationCancelled

import io
import traceback

from services.syteline_export.pipeline.netsem import list_contains, remove_non_alphanumeric, tostr
from services.syteline_export.pipeline.run_base import Flow

# Column headers of the item file, ExportThread.cs 7044-7253 (_syteline and _formatCSI), then 7257-7290 and
# 7298-7328 (_syteline, not CSI; the Feat1..Feat20 loop 7291-7297 sits between the last two lists).
CSI_HEADERS = [
    "Item",
    "Description",
    "Revision",
    "Revision Track",
    "ECN",
    "Drawing Number",
    "Alternate Item",
    "Buyer",
    "Stocked",
    "Show In Dropt-Down Lists",
    "U/M",
    "Type",
    "Source",
    "Product Code",
    "ABC Code",
    "Cost Type",
    "Cost Method",
    "Unit Cost",
    "Current Unit Cost",
    "Lot Size",
    "Unit Weight",
    "Weight Units",
    "Quantity on Hand",
    "Non-Nettable Stock",
    "Safety Stock",
    "Quantity Ordered",
    "Quantity WIP",
    "Allocated to Prod",
    "Allocated To Customer Orders",
    "Reserved For Customer Orders",
    "Low Level",
    "Item Tax Category",
    "Active for Data Integration",
    "Planner Code",
    "Shrink Factor",
    "Phantom Flag",
    "MPS Flag",
    "Net Change",
    "MPS Plan Fence",
    "Family Code",
    "Production Type",
    "Rate/Day",
    "Inventory LCL %",
    "Inventory UCL %",
    "Supply Site",
    "Supply Whse",
    "Paper Work",
    "Lead Time",
    "Expedited Fixed",
    "Dock-to-Stock",
    "Variable",
    "Expedited Variable",
    "Separation",
    "Release 1",
    "Release 2",
    "Release 3",
    "MRP Item",
    "Infinite",
    "Planned Mfg Supply Switching",
    "Accept Requirements",
    "Pass Requirements",
    "Must use future POs before creating PLNs",
    "Supply Usage Tolerance",
    "Time Fence Rule",
    "Time Fence Value",
    "Setup Group",
    "Order Minimum",
    "Order Multiple",
    "Order Maximum",
    "Days Supply",
    "Use Reorder Point",
    "Reorder Point",
    "Forecast BOM Supply Flag",
    "Fixed Order Qty",
    "Earliest Planned Purchase Receipt",
    "Targeted Safety Stock Replenishment",
    "Lot Track",
    "Preassign Lots",
    "Lot Prefix",
    "S/N Track",
    "Preassign Serials",
    "S/N Prefix",
    "Shelf Life",
    "Issue By",
    "Material Status",
    "Reason",
    "Last Change",
    "User",
    "Backflush",
    "Backflush Location",
    "Preferred Co-product Mix",
    "Reservable",
    "Tax-Free Imported Material",
    "Tax Free Days",
    "Safety Stock Percent",
    "Tariff Classification",
    "PO Tolerance Over",
    "PO Tolerance Under",
    "Kit",
    "Print Kit Components on Customer Paperwork",
    "Std Due Period",
    "Commodity",
    "Commodity Description",
    "Origin",
    "Country",
    "Purchased YTD",
    "Manufactured YTD",
    "Used YTD",
    "Sold YTD",
    "USMCA Country of Origin",
    "Subject To RVC Requirements",
    "Wholesale Price",
    "Order Configurable",
    "Job Configurable",
    "Auto Job Generation",
    "Auto Item Creation",
    "Auto Job Generation For External Orders",
    "Auto Item Creation For External Orders",
    "Active For Customer Portal",
    "Name Space",
    "Configuration Flag",
    "Feature String",
    "Feature Template",
    "Last Import Date",
    "Save Current Revision Upon Import",
    "Overview",
    "Featured Item",
    "Top Seller",
    "Item Attribute Group",
    "Item Attribute Group Description",
    "Lot Attribute Group",
    "Lot Attribute Group Description",
    "Enable Pieces Inventory",
    "Piece Dimension Group",
    "Piece Dimension Group Description",
    "Country Of Origin",
    "ECCN or USML CAT",
    "HTS Code",
    "Origin Criteria",
    "Producer",
    "Portal Pricing Enabled",
    "Portal Pricing Site",
    "Freight",
    "Estimated Break Date",
    "Date of Last Report",
    "Commodity Jurisdiction",
    "Program (ITAR/EAR600 Series)",
    "Schedule B Number",
    "Length Linear Dimension",
    "Linear Dimension UM",
    "Width Linear Dimension",
    "Height Linear Dimension",
    "Density",
    "Density UM",
    "Area",
    "Area UM",
    "Bulk Mass",
    "Bulk Mass UM",
    "Ream Mass",
    "Ream Mass UM",
    "Paper Mass Basis",
    "Grade",
    "Abnormal Size",
    "Allow on Pick Workbench",
    "Charge Item",
    "Excise Tax Percent",
    "Includes Item Content",
    "Pull-Up SS Rule",
    "Pull-Up SS Value",
    "Subject To Excise Tax",
    "Model Year",
    "Prepared By",
    "Program",
    "Origin Date",
    "Core Team",
    "Revision Date",
    "Row Pointer",
    "CountStatic",
    "HeaderItemImage",
    "sDisableEnableTaxFreeMatl",
    "Logical Field",
    "Date Field",
    "Character Field 1",
    "Character Field 2",
    "Character Field 3",
    "Decimal Field 1",
    "Decimal Field 2",
    "Decimal Field 3",
    "DerUseGroupOrPieces",
    "Attribute Group",
    "Attribute Group",
    "DerLotLocExistsEdit",
    "DerCanLotSerialHidden",
    "DerHasRsvdInvHidden1",
    "HiddenCanChangeKit",
    "DerBOMExistEdit",
    "DerCostFormEdit",
    "UbUpdateAcctAndUCEdit",
    "Source",
    "C(UbRefTypeStatic)",
    "S/ NLength",
    "Tax Mode",
    "Tax Mode",
    "C(DerItemContentExistStatic)",
    "Cur Fix Ovhd Cost",
    "Cur Var Ovhd Cost",
    "Job",
    "Std Job Suffix",
    "C(DerHasAlternateBOMStatic)",
    "C(IsBOMExistedStatic)",
]

PLAIN_HEADERS_A = [
    "Item",
    "Super Prod",
    "Description",
    "Status",
    "Reason Code",
    "Eurobase",
    "Cost",
    "Curr",
    "Vendor",
    "P/L",
    "Cube",
    "Weight",
    "Stocked",
    "Lead Time",
    "Pre-EngineeringLeadtime",
    "Pre-ProductionLeadtime",
    "Drawing",
    "Handbook",
    "CNCItem",
    "Planner",
    "Days supply",
    "Man Offset",
    "UM",
    "Commodity Code",
    "P/M",
    "Manu Master",
    "Phantom",
    "Template",
    "ECO no.",
    "ECO date",
    "Work Centre",
    "Queue",
    "Run time",
    "Family Code",
]

PLAIN_HEADERS_B = [
    "Height",
    "Width",
    "Depth",
    "DockToStock",
    "Feature String",
    "ItemType",
    "Modvatable",
    "Design Source",
    "Mfg Part Number",
    "Mfg Part Drawing Number",
    "Mfg Part Revision",
    "HSN Code",
    "Sequencing Material",
    "Board Store Type",
    "Grained",
    "Material Origin",
    "Material Type",
    "NCM",
    "Gender",
    "Item Notes",
    "Back Flush",
    "Backflush Locn",
    "Alternate Item",
    "Order Minimum",
    "Order Multiple",
    "Carton/Box Counting",
    "Enabled Roundup Control",
    "Issue UOM Precision",
    "One Off Product",
    "Jig/Hole Requirements",
    "Oke Programme",
]


def _open_writer(path: str):
    """``new StreamWriter(path, append: false)``: UTF-8 without BOM, no newline translation."""
    return io.open(path, "w", encoding="utf-8", errors="replace", newline="")


class P11Mixin:
    """Needs from IoMixin: write_data(writer, text, is_item), write_to_stream(writer, text, ctx),
    write_price_formula_data(), write_product_code_data(), convert_to_xls()."""

    _extract_user_acquired = False  # set True by P0 (legacy 2240 UPDATE Site SET ExtractUser) when this run did so

    # ExportThread.cs 7033-7430
    def p11_write_outputs(self) -> Flow | None:
        self.check_abort()
        v = self.v
        streamWriter5 = None
        try:  # 7034
            streamWriter5 = _open_writer(self._itemFile)
            if not self._millerCAD:
                if self._syteline:
                    arrayList119 = []  # header columns
                    if self._formatCSI:
                        arrayList119.extend(CSI_HEADERS)
                    else:
                        arrayList119.extend(PLAIN_HEADERS_A)
                        num301 = 1
                        while True:  # do { } while (num301 <= 20)
                            self.check_abort()
                            arrayList119.append("Feat" + str(num301))
                            num301 += 1
                            if not (num301 <= 20):
                                break
                        arrayList119.extend(PLAIN_HEADERS_B)
                    num302 = len(arrayList119) - 1
                    for num303 in range(0, num302 + 1):
                        self.check_abort()
                        self.write_data(streamWriter5, tostr(arrayList119[num303]), False)
                        if num303 < len(arrayList119) - 1:
                            self.write_data(streamWriter5, "\t", False)
                    self.write_data(streamWriter5, "\r\n", False)
                else:
                    self.write_data(streamWriter5, "Item\tSuper Prod\tDescription\tStatus\tEurobase\tP/L\tPriceCode\r\n", False)
            arrayList120 = []  # de-dup keys of sheet1 rows
            num304 = len(v.arrayList) - 1
            for num305 in range(0, num304 + 1):
                self.check_abort()
                if not list_contains(arrayList120, remove_non_alphanumeric(tostr(v.arrayList[num305]))):
                    arrayList120.append(remove_non_alphanumeric(tostr(v.arrayList[num305])))
                    if tostr(v.arrayList[num305]).strip() != "":
                        self.write_to_stream(streamWriter5, tostr(v.arrayList[num305]) + "\r\n", "sheet1Data")
        except OperationCancelled:
            raise
        except Exception as ex9:  # 7360
            self.msgbox("myWriter1 error: " + "".join(traceback.format_exception(ex9)))
        finally:
            if streamWriter5 is not None:
                streamWriter5.close()

        streamWriter6 = None
        try:  # 7372
            streamWriter6 = _open_writer(self._materialFile)
            if not self._millerCAD:
                self.write_to_stream(
                    streamWriter6,
                    "Parent Item\tFeature\tComponent\tOpt code\tInc. price\tMatl Qty\tScrap fact\tSeq\tEffect Date\tObs Date\tOper Num\tBackFlush\r\n",
                    "bbbbbb",
                )
            arrayList121 = []  # de-dup keys of sheet2 rows
            num306 = len(v.arrayList2) - 1
            for num307 in range(0, num306 + 1):
                self.check_abort()
                if not list_contains(arrayList121, remove_non_alphanumeric(tostr(v.arrayList2[num307]))):
                    arrayList121.append(remove_non_alphanumeric(tostr(v.arrayList2[num307])))
                    if tostr(v.arrayList2[num307]).strip() != "":
                        text259 = ""
                        self.write_to_stream(streamWriter6, tostr(v.arrayList2[num307]) + text259 + "\r\n", "sheet2Data")
        except OperationCancelled:
            raise
        except Exception as ex11:  # 7394
            self.msgbox("myWriter2 error: " + "".join(traceback.format_exception(ex11)))
        finally:
            if streamWriter6 is not None:
                streamWriter6.close()

        if getattr(v, "streamWriter2", None) is not None:  # 7405
            v.streamWriter2.close()
        if getattr(v, "streamWriter4", None) is not None:  # 7406
            v.streamWriter4.close()
        if (not self._abortThread) and (not self._millerCAD):  # 7407
            self.write_price_formula_data()
            self.write_product_code_data()
            self.update_status_label("Exporting to Excel")
            self.convert_to_xls()
        self.update_export_timer("stop")
        if self._abortThread:
            self.update_status_label("Export Aborted")
            if not self._runAsService:
                # MsgBox("PDM Data Export Aborted") -> informational record, not an error
                self.warnings.append("Export Aborted: PDM Data Export Aborted")
        else:
            self.update_status_label("Export Complete")
            # _parent.currentExportQueue is not in ExportRunBase: absent == empty queue (deviation)
            if (not self._runAsService) and (len(getattr(self._parent, "currentExportQueue", [])) == 0):
                self.warnings.append("Export Complete: PDM Data Export Complete")
        return None

    # ExportThread.cs 7432-7454 (catch (Exception ex13))
    def p11_on_error(self, exc: BaseException) -> None:
        v = self.v
        # debug_form.ShowDialog() replaced by recording the same text (ex.ToString, stage, last SQL text)
        text260 = (
            "".join(traceback.format_exception(exc)) + "\r\n\r\n" + self.threadStage + "\r\n\r\n"
            + tostr(getattr(v, "text", ""))
        )
        # debug-only block omitted (flag default false): if debugIncrements: text260 += text8
        self.msgbox(text260)
        self.update_export_timer("stop")
        if self._runAsService:
            self.update_status_label("Export ERROR")
        else:
            self.msgbox("PDM Data Export Aborted")

    # ExportThread.cs 7455-7480 (finally)
    def p11_finally(self) -> None:
        v = self.v
        for name in ("streamWriter2", "streamWriter3", "streamWriter4"):  # 7457-7459
            writer = getattr(v, name, None)
            if writer is not None:
                try:
                    writer.close()
                except Exception as exc:
                    self.warnings.append(f"Output writer close failed: {type(exc).__name__}: {exc}")
        # Legacy releases whenever text4 == ""; here additionally only when THIS run acquired ExtractUser
        # (legacy 2240) so a run that never took the lock cannot clear another run's lock.
        if tostr(getattr(v, "text4", "")) == "" and self._extract_user_acquired:
            try:
                v.text = "UPDATE Site SET ExtractUser = NULL WHERE SiteId = ?"
                self.threadStage = "42"
                self.db.execute("c1", v.text, (self._siteId,), stage=self.threadStage)
                self._extract_user_acquired = False  # released exactly once
            except Exception as ex15:  # 7469: empty catch in legacy
                self.warnings.append(f"ExtractUser release failed (ignored): {type(ex15).__name__}: {ex15}")
        # sqlConnection..4 .Close() (7476-7479); legacy never closes sqlConnection5 (leak) - db.close() closes all.
        self.db.close()
