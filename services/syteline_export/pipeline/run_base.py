"""State and plumbing shared by every transliterated stage of ExportThread.execThread.

``ExportRunBase`` reproduces the legacy constructor defaults, ``initThread`` and
``clearArrays`` (ExportThread.cs 203-436) so that stage mixins can use the same
``self._field`` names as the decompiled C#. Everything else (stage logic) lives in
mixins composed into ``ExportRun`` (see ``run.py``). Read PORTING_CONVENTIONS.md first.
"""
from __future__ import annotations

import enum
import logging
from types import SimpleNamespace
from typing import Any, Callable, Sequence

from core.cancellation import OperationCancelled, checkpoint
from services.syteline_export.pipeline.db import ExportDb

LOGGER = logging.getLogger("syteline_export")


class Flow(enum.Enum):
    """Result of a stage chunk that contained C# ``continue``/``break``/``return``."""

    NEXT_ITEM = "continue"      # C# `continue;` of the per-item loop (skip the rest of this item)
    BREAK_ITEMS = "break"       # C# `break;` out of the per-item loop
    RETURN = "return"           # C# `return;` from execThread (abort the whole run)


class ExportAborted(OperationCancelled):
    """Raised by the runner when the user cancels; never swallowed by stage code."""


class ExportRunBase:
    """Legacy ExportThread fields + initThread. ``v`` holds every decompiled local variable."""

    def __init__(
        self,
        db: ExportDb,
        *,
        status_callback: Callable[[str], None] | None = None,
        timer_callback: Callable[[str], None] | None = None,
    ) -> None:
        # --- constructor defaults, ExportThread.cs:203-285 --------------------------------
        self.db = db
        self._status_callback = status_callback
        self._timer_callback = timer_callback
        self.fatal_error: BaseException | None = None  # set when the legacy catch (7432) ran
        self.items_processed = 0
        self.outputs_written = False  # True once p11_write_outputs completed
        self.errors: list[str] = []        # every legacy MsgBox/swallowed-exception, kept for the result
        self.warnings: list[str] = []
        self.v = SimpleNamespace()          # decompiled local variables of execThread (flat namespace)
        self.threadStage = "-2"            # SytelineExport.threadStage (per-run instead of static)
        self._numFeatureSlots = 20
        self._formatCSI = False
        self._plcPhantoms = False
        self._parent = SimpleNamespace(processingQueue=False, currentExportQueue=[])
        self._exportDirectory = ""
        self._exportFileName = "PDMExport"
        self._itemFile = self._materialFile = self._superprodFile = ""
        self._descriptionFile = self._planningFile = ""
        self._priceformulaFile = self._productcodeFile = ""
        self.clear_arrays()
        self._prevConvertFeatLen = -1
        self._siteId = -1
        self._site = "uk"
        self._catalogueId = -1
        self._languageId = -1
        self._otherlanguageId = -1
        self._currency = "GBP"
        self._productCodeId = -1
        self._productCheck = False
        self._rangeCheck = False
        self._minItem = ""
        self._maxItem = ""
        self._listCheck = False
        self._activeOnly = False
        self._syteline = False
        self._millerCAD = False
        self._itemreport = False
        self._tradeNet = ""
        self._contract = ""
        self._exportBasePrices = True
        self._effectiveDate = ""
        self._exportAllCataloguesInSite = False
        self._exportBOMData = False
        self._extendSPOpts = False
        self._runAsService = False
        self._length5Feats = True
        self._ignoreOptDeps = False
        self._uniqueComponents = False
        self._flattenFabrics = False
        self._excludeSuperProducts = False
        self._superProductsOnly = False
        self.bocfabCodes: list = []
        self.bocfabSequences: list = []
        self._exportMaterialsForPDMReport = True
        self._exportSPComponentMaterials = True
        self._maxDescriptionLength = 200
        self._abortThread = False
        self._cancel_requested = False
        self._extract_user_acquired = False
        self._SPFeatureItems: list = []
        self._SPFeatureCount: list = []
        self.skippedFabricColours: list = []
        self.materialstr = ""
        self.preConv = ""
        self.ConvCount = 0
        self.asiaUniveralScreenRoots: list = []
        self.includesCOM = False
        self.materialsWritten: list | None = None
        self.cachedItemOptFeatKeys: list = []
        self.cachedItemOptFeatLens: list = []
        # SytelineExport.itemHasFabrics is a static ArrayList shared across runs in the legacy app;
        # it is per-run here so repeated runs cannot leak state into each other.
        self.itemHasFabrics: list = []

    # ExportThread.cs:357-386
    def clear_arrays(self) -> None:
        self._itemsWritten: list = []
        self._materialsOnItemTab: list = []
        self._convertedList: list = []
        self._convertedDesc: list = []
        self._convertedOtherDesc: list = []
        self._convertIsFab: list = []
        self._convertIsDepOpt: list = []
        self._convertHasSuperParent: list = []
        self._convertFeaturePos: list = []
        self._convertStatus: list = []
        self._convertFeatLen: list = []
        self._convertChildFeatLen: list = []
        self._convertOptionId: list = []
        self._itemList: list = []
        self._priceCodes: list = []
        self._productCodes: list = []
        self._additionalItemsWritten: list = []
        self._additionalMaterialsWritten: list = []
        self.allFabricColours: list = []
        self.allFabricColourSequences: list = []
        self.allSPFabricColours: list = []
        self.allSPFabricColourCodes: list = []
        self.allSPFabricColourSequences: list = []
        self.sequenceForItems: list = []
        self.sequenceForItemsOrderCodes: list = []
        self.sequenceForItemsIndexes: list = []

    # ExportThread.cs:387-431 (argument names are the legacy initThread names, snake-cased only
    # where the legacy name is not already a valid identifier; see SyteLineExportConfig).
    def init_thread(
        self, *, filename: str, directory: str, siteId: int, site: str, catalogueId: int,
        languageId: int, currency: str, productCodeId: int, productcheck: bool, rangecheck: bool,
        minitem: str, maxitem: str, listcheck: bool, itemlist: Sequence[str], activeonly: bool,
        syteline: bool, millerCAD: bool, itemreport: bool, sendTradeNet: str, sendContract: str,
        exportBasePrices: bool, effectiveDate: str, exportAllCataloguesInSite: bool,
        otherlanguageId: int, exportBOMData: bool, extendSPOpts: bool, runAsService: bool,
        length5Feats: bool, ignoreOptDeps: bool, uniqueComponents: bool, formatCSI: bool,
        plcPhantoms: bool, excludeSuperProducts: bool, superProductsOnly: bool,
        flattenFabrics: bool,
    ) -> None:
        self.clear_arrays()
        self._exportFileName = filename
        self._exportDirectory = directory
        self._siteId = siteId
        self._site = site
        self._catalogueId = catalogueId
        self._languageId = languageId
        self._otherlanguageId = otherlanguageId
        self._currency = currency
        self._productCodeId = productCodeId
        self._productCheck = productcheck
        self._rangeCheck = rangecheck
        self._minItem = minitem
        self._maxItem = maxitem
        self._listCheck = listcheck
        self._itemList = list(itemlist)
        self._activeOnly = activeonly
        self._syteline = syteline
        self._millerCAD = millerCAD
        self._itemreport = itemreport
        self._tradeNet = sendTradeNet
        self._contract = sendContract
        self._exportBasePrices = exportBasePrices
        self._effectiveDate = effectiveDate
        self._exportAllCataloguesInSite = exportAllCataloguesInSite
        self._exportBOMData = exportBOMData
        self._extendSPOpts = extendSPOpts
        self._runAsService = runAsService
        self._length5Feats = length5Feats
        self._ignoreOptDeps = ignoreOptDeps
        self._uniqueComponents = uniqueComponents
        if self._millerCAD:
            self._maxDescriptionLength = 40
        self._formatCSI = formatCSI
        self._plcPhantoms = plcPhantoms
        self._excludeSuperProducts = excludeSuperProducts
        self._superProductsOnly = superProductsOnly
        self._flattenFabrics = flattenFabrics
        # initThread leaves these untouched in legacy, so a reused ExportThread keeps stale state.
        # A new ExportRun is created per export here; reset the ones legacy forgot.
        self._abortThread = False
        self._prevConvertFeatLen = -1
        self.ConvCount = 0

    # ExportThread.cs:432-435
    def abort_thread(self) -> None:
        # execThread resets _abortThread = false at its start (ExportThread.cs:2100); remember the
        # request separately so a cancel pressed before/while setup runs is not lost.
        self._cancel_requested = True
        self._abortThread = True

    # --- replacements for legacy UI/MsgBox/static plumbing ---------------------------------
    def update_status_label(self, text: str) -> None:
        """UpdateStatusLabel?.Invoke(this, text)."""
        self.check_abort()
        LOGGER.info("[%s] %s", self.threadStage, text)
        if self._status_callback is not None:
            self._status_callback(text)

    def update_export_timer(self, action: str) -> None:
        """UpdateExportTimer?.Invoke(this, action) ('reset'|'start'|'stop')."""
        if self._timer_callback is not None:
            self._timer_callback(action)

    def msgbox(self, text: str, *, fatal: bool = False) -> None:
        """Interaction.MsgBox(...): record instead of blocking the worker thread on a modal dialog."""
        LOGGER.error("[stage %s] %s", self.threadStage, text)
        self.errors.append(f"[stage {self.threadStage}] {text}")

    def report_swallowed(self, context: str, exc: BaseException) -> None:
        """A legacy ``catch (Exception) { MsgBox(ex.ToString()); }`` that lets the run continue."""
        if isinstance(exc, OperationCancelled):
            raise exc
        self.check_abort()
        self.msgbox(f"{context}: {type(exc).__name__}: {exc}")

    def q(self, conn: str, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        """NewSqlCommand(...).ExecuteReader() fully fetched. conn is 'c1'..'c5' = sqlConnection..5."""
        self.check_abort()
        try:
            rows = self.db.query(conn, sql, params, stage=self.threadStage)
        except Exception:
            self.check_abort()
            raise
        self.check_abort()
        return rows

    def x(self, conn: str, sql: str, params: Sequence[Any] = ()) -> int:
        """NewSqlCommand(...).ExecuteNonQuery()."""
        self.check_abort()
        try:
            result = self.db.execute(conn, sql, params, stage=self.threadStage)
        except Exception:
            self.check_abort()
            raise
        if sql.startswith("UPDATE Site SET ExtractUser = ?"):
            self._extract_user_acquired = True
        self.check_abort()
        return result

    def check_abort(self) -> None:
        checkpoint()
        if self._abortThread or self._cancel_requested:
            raise ExportAborted()
