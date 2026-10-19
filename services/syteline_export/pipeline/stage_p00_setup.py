"""Stage P00: start of ExportThread.execThread up to the per-item loop (ExportThread.cs 2096-2473).

Mechanical transliteration; see PORTING_CONVENTIONS.md. Covers: file allocation/test-open, header
writes, the ExtractUser read + UPDATE, preload stages 3-7 (SyteLine only), the stage-8 item query
(executed twice in legacy: a count pass at 2437-2442 and the main pass at 2473) and the declaration
of every execThread local that the per-item loop owns.

Database connections: legacy opens sqlConnection..sqlConnection5 at 2198-2222. Here the ExportDb opens
sessions lazily on first use (c1..c5), so nothing is done for those statements.
"""
from __future__ import annotations

import getpass
import os
from decimal import Decimal

from services.syteline_export.pipeline.netsem import (
    is_knoll_catalogue,
    list_contains,
    list_remove,
    net_int,
    tostr,
)
from services.syteline_export.pipeline.run_base import Flow


class P00Mixin:
    @staticmethod
    def _environment_user_name() -> str:
        """Environment.UserName."""
        return os.environ.get("USERNAME") or getpass.getuser()  # Environment.UserName on Windows

    def p00_setup(self) -> Flow | None:
        v = self.v
        self.threadStage = "0"
        v.arrayList = []
        v.arrayList2 = []
        # SytelineExport.NewSqlCommand("", null, "", append: false) only resets the SQL log file (logSql
        # block, flag default false): omitted.
        v.text = ""
        self._abortThread = False
        self.update_status_label("Thread Executing")
        if not self._parent.processingQueue:
            self.update_export_timer("reset")
            self.update_export_timer("start")
        self.allocate_files()
        flag = False
        streamWriter = None
        try:
            streamWriter = self.open_writer(self._itemFile)
        except Exception:
            self.msgbox(
                "Unable to open the file specified for write operation\r\n\r\n" + self._itemFile
                + "\r\n\r\nPlease ensure it is not in use by a separate process"
            )
            self.update_export_timer("stop")
            flag = True
        finally:
            if streamWriter is not None:
                streamWriter.close()
        if flag:
            return Flow.RETURN
        v.text2 = ""
        numFeatureSlots = self._numFeatureSlots
        for i in range(1, numFeatureSlots + 1):
            v.text2 = v.text2 + "\tFeat" + str(i)
        v.streamWriter2 = None
        v.streamWriter3 = None
        v.streamWriter4 = None
        if (not self._millerCAD) & (not self._formatCSI):
            # not guarded by any try/catch in legacy: an open failure propagates out of execThread
            v.streamWriter2 = self.open_writer(self._superprodFile)
            self.write_to_stream(v.streamWriter2, "Item\tSuper Description\tSeq\tComponent\tQuantity\tDescription\tNum Features\tFP1\tFP2\tFP3\tFP4\tFP5\tFP6\tFP7\tFP8\tFP9\tFP10\tFP11\tFP12\r\n", "cccccc")
            v.streamWriter3 = self.open_writer(self._planningFile)
            self.write_to_stream(v.streamWriter3, "Item\tDescription\tProduct Code\tVendor Call\tStocked\tDock to Stock\tFixed lead time\tPlanner Code\tDays Supply\tSafety Stock\tBuyer\tCustomH\tCustomW\tCustomD\tGross Weight\tLocRank\tLocation\tOrigin Country\tPack qty\tAccept Requirement\tPass Requirement\tKanban qty\r\n", "dddddd")
            v.streamWriter3.close()
            v.streamWriter4 = self.open_writer(self._descriptionFile)
            self.write_to_stream(v.streamWriter4, "Lang\tItem\tDescription\r\n", "dddddd")
        v.sqlDataReader = None
        v.arrayList3 = []
        v.arrayList4 = []
        v.arrayList5 = []
        v.arrayList6 = []
        v.arrayList7 = []
        self.materialsWritten = []
        v.arrayList8 = []
        self._itemsWritten = []
        self._materialsOnItemTab = []
        v.text3 = ""  # culture code of the other language (stage 7)
        self.skippedFabricColours = []
        v.arrayList9 = []
        v.arrayList10 = []
        v.arrayList11 = []
        v.arrayList12 = []
        v.arrayList13 = []
        self.sequenceForItems = []
        self.sequenceForItemsIndexes = []
        v.arrayList14 = []
        v.arrayList15 = []
        v.flag2 = False
        v.text4 = ""  # ExtractUser value found on the Site row BEFORE this run (stage 1)
        v.text5 = "no"
        v.rootproduct = ""
        v.prodcode = ""
        v.text6 = ""
        v.flag3 = True
        v.text7 = ""
        v.text8 = ""
        # try { (2194)
        self.threadStage = "1"
        self.update_status_label("Connecting to Database")
        # sqlConnection..sqlConnection5 are opened lazily by the ExportDb (c1..c5).
        self.update_status_label("Connection OK")
        v.text9 = "'" + self._effectiveDate + "'"  # legacy SQL literal of the effective date (read by later chunks)
        v.text = "SELECT ExtractUser FROM Site WITH (NOLOCK) WHERE SiteId = ?"
        for row in self.q("c1", v.text, (self._siteId,)):
            v.text4 = tostr(row["ExtractUser"])
        # 2233: `if ((text4 != "" ? 1u : 0u) & 0u) != 0 { MsgBox(...); stop timer; return; }` is dead code in
        # legacy (the `& 0u` makes it unreachable). Nothing is checked or reported here; text4 is kept.
        self.threadStage = "2"
        v.text = "UPDATE Site SET ExtractUser = ? WHERE SiteId = ?"
        self.x("c1", v.text, (self._environment_user_name(), self._siteId))
        v.arrayList16 = []  # OptionValueIds in the catalogue
        arrayList17 = []    # OptionIds in the catalogue (not read after this range)
        v.arrayList18 = []  # OptionValueIds with Status = 1
        v.arrayList19 = []  # "ProductId~OptionValueId" exclusions
        v.arrayList20 = []  # "ItemId~OptionValueId" exclusions
        if self._syteline:
            self.update_status_label("Initialising SL8 Export ..")
            v.text = "SELECT DISTINCT optval.OptionValueId, optval.OptionId FROM CatalogueOptionValues cov WITH (NOLOCK) INNER JOIN OptionValue optval ON cov.OptionValueId = optval.OptionValueId WHERE cov.CatalogueId = ?"
            self.threadStage = "3"
            for row in self.q("c1", v.text, (self._catalogueId,)):
                v.arrayList16.append(net_int(row["OptionValueId"]))
                if not list_contains(arrayList17, net_int(row["OptionId"])):
                    arrayList17.append(net_int(row["OptionId"]))
            if is_knoll_catalogue(self._catalogueId):
                list_remove(v.arrayList16, 284979)
                list_remove(v.arrayList16, 286214)
                list_remove(v.arrayList16, 286909)
            self.threadStage = "4"
            v.text = "SELECT OptionValueId FROM OptionValue WITH (NOLOCK) WHERE Status = 1"
            for row in self.q("c1", v.text):
                v.arrayList18.append(net_int(row["OptionValueId"]))
            self.threadStage = "5"
            arrayList21 = []
            arrayList22 = []
            v.text = "SELECT cpoe.ProductId, optval.OptionValueId, optval.Name, optval.OrderCodeValue, optval_colours.OptionValueId AS colourId, optval_colours.Name AS colourName, optval_colours.OrderCodeValue AS colourCode FROM CatalogueProductOptionExclusions cpoe INNER JOIN OptionValue optval ON cpoe.OptionValueId = optval.OptionValueId LEFT OUTER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.OptionValueId AND optval.OrderCodeValue LIKE '%#' LEFT OUTER JOIN OptionValue optval_colours ON dov.AdditionalOptionValueId = optval_colours.OptionValueId WHERE cpoe.CatalogueId = ? ORDER BY optval.OptionId, optval.DisplayOrdinal"
            # debug-only block omitted (flag default false): SytelineExport.debugExclusions
            for row in self.q("c1", v.text, (self._catalogueId,)):
                text10 = tostr(row["OrderCodeValue"])
                text11 = tostr(row["ProductId"]) + "~" + tostr(row["OptionValueId"])
                if not list_contains(v.arrayList19, text11):
                    v.arrayList19.append(text11)
                if text10.endswith("#") and not list_contains(arrayList21, text10):
                    arrayList21.append(text10)
                if tostr(row["colourId"]) == "":
                    continue
                text12 = tostr(row["ProductId"]) + "~" + tostr(row["colourId"])
                if not list_contains(v.arrayList19, text12):
                    v.arrayList19.append(text12)
                if (text10 == "0Y#") & list_contains(arrayList21, "0#"):
                    if not list_contains(arrayList22, text12):
                        arrayList22.append(text12)
                elif ((text10 == "0#") & list_contains(arrayList21, "0Y#")) and not list_contains(arrayList22, text12):
                    arrayList22.append(text12)
            num = len(arrayList22) - 1
            for j in range(0, num + 1):
                list_remove(v.arrayList19, tostr(arrayList22[j]))
            self.threadStage = "6"
            v.text = "SELECT ItemId, OptionValueId FROM CatalogueItemOptionExclusions WHERE CatalogueId = ?"
            for row in self.q("c1", v.text, (self._catalogueId,)):
                v.arrayList20.append(tostr(row["ItemId"]) + "~" + tostr(row["OptionValueId"]))
            self.threadStage = "7"
            # legacy compares Language_Id with the quoted string '<id>'
            v.text = "SELECT CultureCode FROM Language WITH (NOLOCK) WHERE Language_Id = ?"
            rows5 = self.q("c5", v.text, (str(self._otherlanguageId),))
            if len(rows5) > 0:  # HasRows
                v.text3 = tostr(rows5[0]["CultureCode"])  # Read() once
        # ---- stage 8 main item query (2350-2431), every data value bound ----
        p: list = []
        text = "SELECT DISTINCT Item.Item AS LongItem, Item.Notes, Item.LegacyItem, Item.Height, Item.Width, Item.Depth, CASE WHEN len(Item.Item) > 22 THEN substring(Item.Item, 1, 22) ELSE Item.Item END AS Item, Item.Status, Item.FSCCompliant, Item.WeightKilos, Item.VolumeLitres, Product.Product, Product.IsSuperProduct, Item.ItemId, CASE WHEN item_desc.ShortDescription IS NOT NULL AND len(item_desc.ShortDescription) > 0 THEN SUBSTRING(item_desc.ShortDescription, 1, ?) WHEN pd.ShortDescription IS NULL THEN Item.Item ELSE SUBSTRING(pd.ShortDescription, 1, ?) END AS ShortDescription, SUBSTRING(alt_desc.ShortDescription, 1, ?) AS AltDescription,CASE WHEN pc.BasePriceRef = 1 THEN Item.BasePrice WHEN pc.BasePriceRef = 2 THEN Item.BasePrice2 WHEN pc.BasePriceRef = 3 THEN Item.BasePrice3 END AS MyBasePrice, "
        p += [self._maxDescriptionLength, self._maxDescriptionLength, self._maxDescriptionLength]
        if self._millerCAD | (self._syteline & (not self._exportBasePrices)):
            text = text + "dbo.fnGetListPriceByItem(Item.Item, ?, ?, ?, NULL) AS ListPrice, "
            p += [self._currency, tostr(self._effectiveDate), self._siteId]  # legacy passes text9 = quoted effective date
        text = (
            text + "Product.ProductId, pc.Product_Code, pc.Description, Product.OrderCodeFormatString AS prodFS, ProductRange.ProductRangeId, ProductRange.OrderCodeFormatString AS rangeFS, ProductRange.ProductCategoryId, Item.CommodityCode, pc.PriceCode FROM Item WITH (NOLOCK) CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN ProductRange ON Product.ProductRangeId = ProductRange.ProductRangeId "
            + "INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId LEFT OUTER JOIN ProductDescription pd ON Product.DescriptionId = pd.DescriptionId And pd.LanguageId = ?"
            + " LEFT OUTER JOIN OtherDescription item_desc ON Item.DescriptionId = item_desc.DescriptionId And item_desc.LanguageId = ?"
            + " "
        )
        p += [self._languageId, self._languageId]
        if self._syteline | self._millerCAD | self._itemreport:
            text += "INNER JOIN CatalogueItems ON Item.ItemId = CatalogueItems.ItemId "
        if self._millerCAD:
            text += "INNER JOIN Catalogue ON CatalogueItems.CatalogueId = Catalogue.CatalogueId "
        text = text + "LEFT OUTER JOIN ProductDescription alt_desc ON pd.DescriptionId = alt_desc.DescriptionId And alt_desc.LanguageId = ? "
        p.append(self._otherlanguageId)
        text = text + "WHERE pc.SiteId = ? "
        p.append(self._siteId)
        if self._productCheck:
            text = text + "And pc.ProductCodeId = ? And CatalogueItems.CatalogueId = ? "
            p += [self._productCodeId, self._catalogueId]
        elif self._rangeCheck:
            if not ((self._minItem == "BRW") & (self._maxItem == "BRW")):
                text = text + "AND (Item.Item > ? OR Item.Item LIKE ?) AND (Item.Item < ? OR Item.Item LIKE ?) "
                p += [self._minItem, self._minItem + "%", self._maxItem, self._maxItem + "%"]
            else:
                text = text + "And (Item.Item = 'BREF.CL' OR item.item = 'BRWBTEENONN.AAM' OR Item.Item = 'BRWLEELDLEFHN.AAMM' OR Item.Item = 'BRWUPMEELSBRSGN.AAMWM' OR Item.Item = 'BRWLEELDLEFHN.AAMM' OR Item.Item = 'BRWLEELDLEFHN.AAWM' OR Item.Item = 'BREUBLL.' OR Item.Item = 'BREUBLR.') "
            if self._syteline:
                text = text + "AND CatalogueItems.CatalogueId = ? "
                p.append(self._catalogueId)
        elif self._listCheck:
            if len(self._itemList) > 0:
                text += "AND ("
                num2 = len(self._itemList) - 1
                for k in range(0, num2 + 1):
                    text = text + "Item.Item = ?"
                    p.append(tostr(self._itemList[k]))
                    if k < len(self._itemList) - 1:
                        text += " OR "
                text += ") "
        elif self._syteline:
            text = text + "AND CatalogueItems.CatalogueId = ? "
            p.append(self._catalogueId)
        elif self._millerCAD:
            if not self._exportAllCataloguesInSite:
                text = text + "AND CatalogueItems.CatalogueId = ? "
                p.append(self._catalogueId)
            else:
                text = text + "AND Catalogue.PrimarySiteId = ? "
                p.append(self._siteId)
        elif self._itemreport:
            if self._activeOnly:
                text = text + "AND CatalogueItems.CatalogueId = ? "
                p.append(self._catalogueId)
            else:
                text = text.replace(
                    "INNER JOIN CatalogueItems ON Item.ItemId = CatalogueItems.ItemId ",
                    "LEFT OUTER JOIN CatalogueItems ON Item.ItemId = CatalogueItems.ItemId LEFT OUTER JOIN CatalogueItemsUnreleased ON Item.ItemId = CatalogueItemsUnreleased.ItemId ",
                )
                text = text + "AND (CatalogueItems.CatalogueId = ? OR CatalogueItemsUnreleased.CatalogueId = ?) "
                p += [self._catalogueId, self._catalogueId]
        if self._activeOnly:
            text += "AND Product.Status = 1 AND Item.Status = 1 "
        text13 = text
        p13 = list(p)  # parameters of the single SELECT; each UNION copy repeats them in the same order
        if not self._activeOnly:
            text = text13 + " UNION " + text13.replace("CatalogueItems", "CatalogueItemsUnreleased").replace("Item.Status", "0 AS Status")
            p = p + p13
        if self._excludeSuperProducts and self._activeOnly:
            text = (
                text + " UNION "
                + text13.replace(
                    "INNER JOIN CatalogueItems ON Item.ItemId",
                    "INNER JOIN ItemComponents itco ON Item.ItemId = itco.SubItemId \r\nINNER JOIN Item sp_item ON itco.ItemId = sp_item.ItemId \r\nINNER JOIN CatalogueItems ON sp_item.ItemId",
                )
                .replace("Item.Item ", "sp_item.Item ")
                .replace("sp_item.Item AS LongItem", "Item.Item AS LongItem")
                .replace("sp_item.Item END AS Item", "Item.Item END AS Item")
                .replace("pd.ShortDescription IS NULL THEN sp_item.Item", "pd.ShortDescription IS NULL THEN Item.Item")
            )
            p = p + p13
            text += " AND sp_item.Status = 1"
        text += " ORDER BY Item.Item"
        v.text = text
        self.threadStage = "8"
        # CommandTimeout = 600 in legacy; the Db default (900s) applies here.
        self.update_status_label("Loading Items...")
        # count pass (2436-2442): feeds only the "(n of N)" status text in the per-item loop (2493) via arrayList23.Count
        v.arrayList23 = []
        for row in self.q("c1", text, tuple(p)):
            v.arrayList23.append(tostr(row["LongItem"]))
        v.item_count = len(v.arrayList23)
        v.text14 = ""
        v.right = ""  # previous item's Product (2494/2498)
        v.text15 = ""
        v.num3 = 0
        v.arrayList24 = []
        v.arrayList25 = []
        v.arrayList26 = []
        v.num4 = Decimal(0)
        v.text16 = ""
        v.text17 = ""
        v.text18 = ""
        v.num5 = 0  # item counter
        for n in range(27, 45):
            setattr(v, "arrayList%d" % n, [])
        # main pass (2473): the query is executed a second time, as in legacy
        v.item_rows = self.q("c1", text, tuple(p))
        return None
