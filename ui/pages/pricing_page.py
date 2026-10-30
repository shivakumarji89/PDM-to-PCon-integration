"""Pricing workspace page.

A snapshot-driven workbench for computing the product's OCD price records
(``tCOMd_Price`` / ``tCOMd_GlobalPrice``) from PDM. Values are computed by SQL
Server's own ``fnGetListPrice*`` functions in a few batched queries, so they are
byte-identical to PDM's *Update pCon Prices* button - only far faster. The tool
auto-routes each item to article vs global pricing and diffs the result against
the stored baseline so only changed cells stand out.
"""
from __future__ import annotations

import shiboken6
from PySide6.QtCore import QObject, Qt, QThreadPool, QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QDate

from core.engines.filtering import text_match
from core.activity.models import ActivityType, LogLevel
from core.progress import ProgressReporter
from models.price_record import PriceRecord
from services.pricing_program import program_from_linked_repository, program_from_workspace_path
from services.pricing_service import PriceParams, PricingService, pricing_requires_recompute
from services.price_mdb_export_service import PriceMdbExportService
from services.price_text_blocks import (
    ISSUE_STATUSES, STATUS_CREATED, STATUS_NEW, STATUS_NA, record_result_key,
    row_result_key, text_block_cells,
)
from services.price_text_blocks import name_key as _text_name_key
from services.price_list_targets import computation_date, default_names
from ui.dialogs.price_export_preview_dialog import PriceExportPreviewDialog, list_lines
from ui.dialogs.price_list_target_dialog import PriceListTargetDialog
from ui.dialogs.progress_dialog import ProgressDialog
from ui.pages.base_page import BasePage
from ui.widgets.maintenance_source_tabs import (
    MaintenanceSourceMixin,
    read_only_in_mdb,
)
from ui.dialogs.price_list_manager_dialog import PriceListManagerDialog
from core.modules import WorkbenchModule

# Map ProgressReporter log kinds to activity log levels.
_ACT_LEVEL = {
    "info": LogLevel.INFO,
    "success": LogLevel.SUCCESS,
    "warning": LogLevel.WARNING,
    "error": LogLevel.ERROR,
}


from ui.workers.background_task import BackgroundTask, task_host


class _PricingRun(QObject):
    """One Compute Prices run: owns its reporter, worker signals and Activity.

    Parented to the background-task host rather than the page, so everything
    the worker thread uses outlives a page that is closed or destroyed mid-run.
    All slots run on the GUI thread (worker emissions are queued here). The page
    is only called back while it is alive and this is still its current run,
    and each run reports its outcome exactly once.
    """

    def __init__(self, page: QWidget, activity) -> None:
        super().__init__(task_host())
        self._page: QWidget | None = page
        self._activity = activity
        self.active = False
        self._failed_outcome = False
        self.reporter = ProgressReporter(self)
        # ActivityHandle uses __slots__ (no __weakref__), so it cannot be a
        # receiver itself; bridge through this GUI-thread object instead.
        self.reporter.step_changed.connect(self._on_step)
        self.reporter.activity.connect(self._on_activity)
        self.reporter.finished.connect(self._on_reporter_finished)
        page.destroyed.connect(self._on_page_destroyed)

    def start(self, task: BackgroundTask) -> None:
        self.active = True
        signals = task.signals
        signals.progress.connect(self._on_batch)
        signals.finished.connect(self._on_finished)
        signals.failed.connect(self._on_failed)
        signals.cancelled.connect(self._on_cancelled)
        QThreadPool.globalInstance().start(task)

    # -- page access -------------------------------------------------------
    def _live_page(self):
        page = self._page
        if page is None or not shiboken6.isValid(page):
            return None
        return page

    def _current_page(self):
        page = self._live_page()
        if page is None or getattr(page, "_price_run", None) is not self:
            return None
        return page

    def _on_page_destroyed(self, *_args) -> None:
        # Nothing is left to render the results; the worker keeps its objects
        # (owned by this run) until it finishes, and the request is advisory.
        self._page = None
        self.reporter.request_cancel()

    # -- Activity bridge ---------------------------------------------------
    def _on_step(self, text: str) -> None:
        self._activity.update_step(text)

    def _on_activity(self, kind: str, message: str) -> None:
        self._activity.add_log(message, _ACT_LEVEL.get(kind, LogLevel.INFO))

    def _on_reporter_finished(self, ok: bool, message: str) -> None:
        if ok:
            self._activity.complete(message)
        elif self.reporter.is_cancelled() and not self._failed_outcome:
            self._activity.cancel(message)
        else:
            self._activity.fail(message)

    # -- worker outcome ----------------------------------------------------
    def _on_batch(self, records) -> None:
        if self.reporter.is_cancelled():
            return
        page = self._current_page()
        if page is not None:
            page._append_batch(records)

    def _on_finished(self, result) -> None:
        self.reporter.finish(True, "Pricing completed")
        page = self._end_run()
        try:
            if page is not None:
                page._on_pricing_finished(result)
        finally:
            self._release()

    def _on_failed(self, message: str) -> None:
        # Close the reporter (progress popup + Activity) before the page reports
        # the error. finish() is idempotent and runs here on the GUI thread.
        self._failed_outcome = True
        self.reporter.finish(False, message)
        page = self._end_run()
        try:
            if page is not None:
                page._on_pricing_failed(message)
        finally:
            self._release()

    def _on_cancelled(self, message: str) -> None:
        self.reporter.finish(False, message)
        page = self._end_run()
        try:
            if page is not None:
                page._on_pricing_cancelled(message)
        finally:
            self._release()

    def _end_run(self):
        """Mark the run finished and detach it from the page (returns the page)."""
        page = self._current_page()
        self.active = False
        if page is not None:
            page._price_run = None
        return page

    def _release(self) -> None:
        page = self._live_page()
        monitor = getattr(page, "_monitor", None) if page is not None else None
        if monitor is not None:
            monitor.unbind_reporter(self.reporter)
        self._page = None
        # Deletes the reporter (and its timer) with this run, on the GUI thread.
        self.deleteLater()


_COL_ARTICLE = 0
_COL_VARCOND = 1
_COL_VALUE = 2
_COL_CURRENCY = 3
_COL_TEXT_ID = 4
_COL_TEXT = 5
_COL_CHANGE = 6
_NUM_COLS = 7

_FILTER_ALL = "All records"
_FILTER_BASE = "Base (B)"
_FILTER_UPCHARGE = "Upcharge (X)"
_FILTER_GLOBAL = "Global / super"
_FILTER_CHANGED = "Changed only"
_FILTER_TEXT_ISSUES = "Text block issues"

_CHANGED_BG = QColor(255, 244, 204)
_ADDED_BG = QColor(223, 245, 223)
_TEXT_NEW_BG = QColor(222, 235, 255)
_TEXT_ISSUE_FG = QColor(176, 0, 32)


@read_only_in_mdb(
    "_on_compute", "_on_pricing_finished", "_on_pricing_failed",
    "_open_price_list_manager", "_on_manage_price_lists", "_on_export_prices",
    "_on_preview_export",
)
class PricingPage(MaintenanceSourceMixin, BasePage):
    """Compute and review OCD price records for the active snapshot."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Pricing",
            description="Compute PDM-accurate OCD prices and review year-over-year changes.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._init_source_tabs(context)
        self._records: list[PriceRecord] = []
        #: Diff state keyed like PriceRecord.key(): "added" / "changed" / prior value.
        self._added_keys: set = set()
        self._changed: dict = {}
        self._pricing_currencies: set[str] = set()
        #: Row-level text-block results of the last export preview / export, keyed
        #: like ``PriceRecord.key()``. Empty until an MDB has actually been compared.
        self._text_results: dict[tuple, dict] = {}
        #: Imported-MDB price texts (name -> English content) for the Text Block column.
        self._price_texts: dict[str, str] = {}
        self._last_mdb_path = ""
        self._wf: dict = {}  # state of the running export workflow
        self._price_run: _PricingRun | None = None  # the active Compute Prices run

        # Debounce search typing so the table repopulates once the user pauses.
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(200)
        self._filter_timer.timeout.connect(self._apply_filter)

        self.add_content(self._build_toolbar())
        self.add_content(self._build_table())
        self.add_content(self._build_summary())
        self.refresh()

    # -- construction ------------------------------------------------------
    def _build_toolbar(self) -> QWidget:
        box = QGroupBox("Compute", self)
        layout = QHBoxLayout(box)

        layout.addWidget(QLabel("Currency:", box))
        self._currency = QComboBox(box)
        self._currency.addItems(["All", "GBP", "EUR"])
        self._currency.setToolTip(
            "Filters the table by currency. Compute pulls every price-list "
            "currency (e.g. EUR + GBP); with no lists it uses this currency "
            "(GBP when 'All')."
        )
        self._currency.currentIndexChanged.connect(self._apply_filter)
        layout.addWidget(self._currency)

        layout.addWidget(QLabel("Effective date:", box))
        self._date = QDateEdit(box)
        self._date.setDisplayFormat("dd-MMM-yyyy")
        self._date.setCalendarPopup(True)
        self._date.setDate(QDate.currentDate())
        layout.addWidget(self._date)

        layout.addWidget(QLabel("Site:", box))
        self._site = QSpinBox(box)
        self._site.setRange(1, 999)
        self._site.setValue(1)
        layout.addWidget(self._site)

        self._compute_btn = QPushButton("Compute Prices", box)
        self._compute_btn.setToolTip(
            "Pull PDM-accurate prices in batched queries and diff vs the baseline."
        )
        self._compute_btn.clicked.connect(self._on_compute)
        layout.addWidget(self._compute_btn)

        self._export_btn = QPushButton("Export to MDB...", box)
        self._export_btn.setToolTip(
            "Review the target price lists, preview the exact plan, then write prices and text blocks "
            "into an existing OCD MDB. Nothing is deleted; only price values of existing rows change."
        )
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export_prices)
        layout.addWidget(self._export_btn)

        self._preview_btn = QPushButton("Preview Export...", box)
        self._preview_btn.setToolTip(
            "Dry run against an existing OCD MDB: shows which price rows would be updated "
            "or inserted and which text blocks would be reused or created. Writes nothing."
        )
        self._preview_btn.setEnabled(False)
        self._preview_btn.clicked.connect(self._on_preview_export)
        layout.addWidget(self._preview_btn)

        self._pricelists_btn = QPushButton("Price Lists\u2026", box)
        self._pricelists_btn.setToolTip(
            "Define named price lists (currency + validity) with date roll-over."
        )
        self._pricelists_btn.clicked.connect(self._on_manage_price_lists)
        layout.addWidget(self._pricelists_btn)

        layout.addStretch(1)
        return box

    # -- price lists ------------------------------------------------------
    def _price_list_mode(self) -> str:
        """Select creation vs maintenance behavior from the active module."""
        module = getattr(self.window(), "_active_module", None)
        return "new_creation" if module == WorkbenchModule.DEVELOPMENT else "maintenance"

    def _price_list_currencies(self) -> list[str]:
        """Return currencies for the price-list workflow.
        
        Development creates the initial price-list set for both supported
        currencies. Maintenance continues from the currencies already present
        in the snapshot, with the selected currency used only when no list exists.
        """
        snapshot = self._context.active_snapshot
        if snapshot is None:
            return []
        if self._price_list_mode() == "new_creation":
            return ["GBP", "EUR"]

        currencies: list[str] = []
        for record in snapshot.price_records:
            currency = (record.currency or "").upper()
            if currency and currency not in currencies:
                currencies.append(currency)
        if currencies:
            return currencies
        selected = self._currency.currentText()
        if selected != "All":
            return [selected.upper()]
        return ["GBP"]

    def _open_price_list_manager(self) -> None:
        snapshot = self._context.active_snapshot
        if snapshot is None:
            QMessageBox.information(self, "Price Lists", "Load a product first.")
            return
        mode = self._price_list_mode()
        dialog = PriceListManagerDialog(
            self._context,
            snapshot,
            mode=mode,
            currencies=self._price_list_currencies(),
            effective_date=self._date.date().toString("yyyyMMdd"),
            parent=self,
        )
        dialog.exec()
        if dialog.applied:
            self.refresh()

    def _on_manage_price_lists(self) -> None:
        self._open_price_list_manager()

    def on_enter(self) -> None:
        """Refresh and offer the default first-list setup for Development."""
        snapshot = self._context.active_snapshot
        self.refresh()
        if snapshot is None:
            return
        module = getattr(self.window(), "_active_module", None)
        if module != WorkbenchModule.DEVELOPMENT or snapshot.price_lists:
            return
        if getattr(self, "_default_price_list_snapshot", None) is snapshot:
            return
        self._default_price_list_snapshot = snapshot
        QTimer.singleShot(0, self._open_price_list_manager)

    def _build_table(self) -> QWidget:
        box = QGroupBox("Price records", self)
        layout = QHBoxLayout(box)

        # Filter row above the table.
        container = QWidget(box)
        vlayout = _v(container)

        filter_row = QWidget(container)
        frow = QHBoxLayout(filter_row)
        frow.setContentsMargins(0, 0, 0, 0)
        self._search = QLineEdit(filter_row)
        self._search.setPlaceholderText("Search article, variant condition or text block...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._schedule_filter)
        frow.addWidget(self._search, 1)
        frow.addWidget(QLabel("Show:", filter_row))
        self._filter = QComboBox(filter_row)
        self._filter.addItems([
            _FILTER_ALL, _FILTER_BASE, _FILTER_UPCHARGE,
            _FILTER_GLOBAL, _FILTER_CHANGED, _FILTER_TEXT_ISSUES,
        ])
        self._filter.currentIndexChanged.connect(self._apply_filter)
        frow.addWidget(self._filter)
        vlayout.addWidget(filter_row)

        self._table = QTableWidget(0, _NUM_COLS, container)
        self._table.setHorizontalHeaderLabels(
            ["Article", "Variant Condition", "Value", "Currency",
             "Text Block ID", "Text Block", "Change"]
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(_COL_VARCOND, QHeaderView.ResizeMode.Stretch)
        for c in (_COL_ARTICLE, _COL_VALUE, _COL_CURRENCY, _COL_TEXT_ID, _COL_CHANGE):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_TEXT, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(_COL_TEXT, 220)
        vlayout.addWidget(self._table, 1)

        layout.addWidget(container)
        return box

    def _build_summary(self) -> QWidget:
        box = QGroupBox("Summary", self)
        layout = QHBoxLayout(box)
        self._summary = QLabel("No prices computed yet.", box)
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary, 1)
        return box

    # -- data --------------------------------------------------------------
    def refresh(self) -> None:
        """Reload stored records unless a streamed price computation is active.

        During computation the snapshot is intentionally committed only when the
        worker finishes. Re-reading it mid-run would replace the live accumulated
        rows with the previous snapshot and make earlier streamed rows disappear.
        Re-render the in-memory stream instead.
        """
        if getattr(self, "_pricing_running", False):
            self._populate()
            self._summary.setText(
                f"Computing prices... {len(self._records)} records so far"
            )
            return
        if self._begin_refresh():
            return
        snapshot = self._context.active_snapshot
        self._records = list(snapshot.price_records) if snapshot else []
        self._added_keys = set()
        self._changed = {}
        self._text_results = {}
        self._price_texts = {
            _text_name_key(t.name): (t.en or "")
            for t in (getattr(snapshot, "text_blocks", None) or [])
            if (t.type_code or "").lower() == "price"
        } if snapshot else {}
        self._populate()
        self._update_summary(unresolved=0)
        self._restore_export_buttons()
        if self.is_mdb_view() and snapshot is not None:
            self._summary.setText(
                f"Imported MDB: {len(self._records):,} price record(s), "
                f"{len(snapshot.price_lists):,} price list(s)."
            )

    def _lockable_widgets(self) -> list:
        return [getattr(self, "_compute_btn", None), getattr(self, "_pricelists_btn", None)]

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # Reload from the snapshot whenever the page is shown, matching every
        # other data page so navigating in always reflects the current product.
        super().showEvent(event)
        self.refresh()

    def is_ready(self) -> bool:
        snapshot = self._context.active_snapshot
        return snapshot is not None and snapshot.product is not None

    def _progress_monitor(self) -> ProgressDialog:
        """Lazily create the reusable progress popup for price computation."""
        monitor = getattr(self, "_monitor", None)
        if monitor is None:
            monitor = ProgressDialog(self)
            self._monitor = monitor
        return monitor

    def _program_code(self, snapshot) -> str:
        """Explicit Review program first; in Maintenance, else legacy's workspace-folder program, else the package code."""
        explicit = str(getattr(snapshot, "generation_program", "") or "")
        if explicit.strip():
            return explicit
        if getattr(self.window(), "_active_module", None) != WorkbenchModule.MAINTENANCE:
            return explicit
        state = self._context.maintenance_snapshot
        info = self._context.maintenance_repository_info or {}
        # Legacy PDM derives its program from the workspace folder (never blank); only trust a link that is
        # aligned to this snapshot, as for the package code below.
        if state is not None and getattr(state, "pdm_snapshot", None) is snapshot:
            workspace = program_from_workspace_path(info.get("path"))
            if workspace:
                return workspace
        return program_from_linked_repository(state, snapshot)

    def _params(self) -> PriceParams:
        d = self._date.date()
        sel = self._currency.currentText()
        snapshot = self._context.active_snapshot
        return PriceParams(
            currency="" if sel == "All" else sel,
            mydate=d.toString("dd-MMM-yyyy"),
            site_id=self._site.value(),
            valid_from=d.toString("yyyy-MM-dd"),
            valid_to="",
            program_code=self._program_code(snapshot),
        )

    def _on_compute(self) -> None:
        if self._pricing_in_progress():
            # One computation at a time: a second run would interleave batches
            # into the same table and commit over the first run's records.
            monitor = getattr(self, "_monitor", None)
            if monitor is not None:
                monitor.show()
                monitor.raise_()
            return
        snapshot = self._context.active_snapshot
        if snapshot is None:
            QMessageBox.information(self, "Compute Prices", "Load a product first.")
            return

        params = self._params()
        # Compute every price-list currency (EUR + GBP + ...), or the selected
        # currency when no lists are defined. Diff only within the computed
        # currencies; any other currency's records stay for their own lists.
        currencies = {
            c.upper()
            for c in PricingService(self._context).target_currencies(snapshot, params)
        }
        self._pricing_currencies = currencies
        self._baseline = [
            r for r in snapshot.price_records if (r.currency or "").upper() in currencies
        ]
        # Stream: clear the table and append records as each batch arrives so the
        # operator sees progress instead of a frozen window until the end.
        # Keep refresh()/showEvent from reloading the old snapshot during this run.
        self._pricing_running = True
        self._records = []
        self._added_keys = set()
        self._changed = {}
        self._text_results = {}  # recomputed prices have not been compared with an MDB
        self._table.setSortingEnabled(False)
        self._table.clearContents()
        self._table.setRowCount(0)
        self._compute_btn.setEnabled(False)
        self._export_btn.setEnabled(False)
        self._preview_btn.setEnabled(False)

        self._price_params = params
        self._pricing_snapshot = snapshot
        # Also record the run in the Activity timeline so it lands in the log.
        activity = self._context.activity_service.start_activity(
            "Computing Prices", ActivityType.GENERIC,
            context={"Currency": params.currency, "Date": params.mydate},
        )
        # The run (not the page) owns the reporter, the worker signals and the
        # Activity bridge, so they stay alive until the worker has finished even
        # if the page is closed or destroyed mid-run.
        run = _PricingRun(self, activity)
        self._price_run = run
        monitor = self._progress_monitor()
        monitor.bind(run.reporter)
        monitor.show()
        monitor.raise_()
        reporter = run.reporter
        context = self._context

        # Compute off the UI thread so the popup animates instead of freezing.
        # The worker only calls the reporter (whose signals are queued to the GUI
        # thread) and the batch callback; it never touches widgets or the page.
        def work(emit):
            return PricingService(context).compute_streaming(
                params,
                snapshot,
                on_batch=emit,
                reporter=reporter,
            )

        run.start(BackgroundTask(work, cancellation_token=reporter.cancellation_token))

    def _pricing_in_progress(self) -> bool:
        run = getattr(self, "_price_run", None)
        return run is not None and run.active

    def _on_pricing_finished(self, result) -> None:
        if self._context.active_snapshot is not getattr(self, "_pricing_snapshot", self._context.active_snapshot):
            self._on_pricing_cancelled("Pricing finished for the previous snapshot; current snapshot unchanged.")
            return
        run_currencies = set(self._pricing_currencies)
        self._pricing_running = False
        self._pricing_currencies = set()
        self._pricing_baseline = []
        snapshot = self._context.active_snapshot
        if snapshot is not None and run_currencies:
            snapshot.price_records = PricingService._accumulate_currencies(
                snapshot.price_records,
                result.records,
                run_currencies,
            )
            self._context.snapshot_manager.mark_modified()
        diff = PricingService.diff(self._baseline, result.records)
        self._records = list(result.records)
        self._added_keys = {r.key() for r in diff.added}
        self._changed = {new.key(): old.value for old, new in diff.changed}
        self._populate()  # final authoritative render (filter + diff colours)
        self._update_summary(
            unresolved=len(result.unresolved), diff=diff, params=self._price_params
        )
        self._compute_btn.setEnabled(True)
        self._restore_export_buttons()
        if result.warnings:
            QMessageBox.information(
                self, "Compute Prices", "\n".join(result.warnings)
            )

    def _on_pricing_failed(self, message: str) -> None:
        self._pricing_running = False
        self._pricing_currencies = set()
        self._pricing_baseline = []
        self._compute_btn.setEnabled(True)
        self.refresh()
        QMessageBox.critical(
            self, "Compute Prices", f"Price computation failed:\n\n{message}"
        )

    def _on_pricing_cancelled(self, message: str) -> None:
        self._pricing_running = False
        self._pricing_currencies = set()
        self._pricing_baseline = []
        self._compute_btn.setEnabled(True)
        self.refresh()
        self._summary.setText(message)
        self._restore_export_buttons()


    def _on_export_prices(self) -> None:
        """Export workflow: MDB -> review/rename target lists -> preview -> write."""
        self._start_export_workflow(write=True)

    def _on_preview_export(self) -> None:
        """Same workflow, but the preview offers no export button; nothing is written."""
        self._start_export_workflow(write=False)

    def _restore_export_buttons(self) -> None:
        enabled = (
            bool(self._records) and not self.is_mdb_view()
            and not getattr(self, "_pricing_running", False)
            and not pricing_requires_recompute(self._context.active_snapshot)
        )
        self._export_btn.setEnabled(enabled)
        self._preview_btn.setEnabled(enabled)

    def _start_export_workflow(self, write: bool) -> None:
        snapshot = self._context.active_snapshot
        if snapshot is None or not snapshot.price_records:
            QMessageBox.information(self, "Export Prices", "Compute prices before exporting.")
            self._restore_export_buttons()
            return
        if pricing_requires_recompute(snapshot):
            QMessageBox.warning(
                self, "Export Prices",
                "Stored fabric pricing requires recomputation. Click Compute Prices "
                "to resolve the PDM colour relationships before previewing or exporting.",
            )
            self._restore_export_buttons()
            return
        if not computation_date(snapshot.price_records):
            QMessageBox.warning(
                self, "Export Prices",
                "The computed prices carry no computation date. Recompute prices first; "
                "today's date is never substituted.")
            return
        mdb_path, _ = QFileDialog.getOpenFileName(
            self, "Select existing OCD MDB" + (" to export prices into" if write else " to preview against"),
            self._last_mdb_path, "Access database (*.mdb)",
        )
        if not mdb_path:
            return
        self._last_mdb_path = mdb_path
        self._wf = {"write": write, "path": mdb_path, "snapshot": snapshot, "targets": {}}
        self._export_btn.setEnabled(False)
        self._preview_btn.setEnabled(False)
        self._summary.setText("Reading price lists from the MDB...")
        self._lists_task = BackgroundTask(
            lambda _progress: PriceMdbExportService(self._context).read_price_lists(mdb_path)
        )
        self._lists_task.signals.finished.connect(self._on_lists_read)
        self._lists_task.signals.failed.connect(self._on_price_export_failed)
        QThreadPool.globalInstance().start(self._lists_task)

    def _on_lists_read(self, info: dict) -> None:
        """Let the user review / rename the EUR and GBP target lists, then preview."""
        if info.get("error"):
            self._summary.setText("Price export failed.")
            QMessageBox.critical(self, "Export Prices", info["error"])
            self._restore_export_buttons()
            return
        snapshot, mdb_path = self._wf["snapshot"], self._wf["path"]
        comp = computation_date(snapshot.price_records)
        record_currencies = {
            (r.currency or "").strip().upper()
            for r in snapshot.price_records if (r.currency or "").strip()
        }
        # Always offer the two primary destinations, even if one currency has
        # no resolved rows in this run; retain selectors for any extra currencies
        # already present in a legacy snapshot so strict export can route them too.
        currencies = ["EUR", "GBP"] + sorted(record_currencies - {"EUR", "GBP"})
        names = default_names(currencies, comp, info["lists"], snapshot.price_lists)
        dialog = PriceListTargetDialog(currencies, names, info["lists"], info["linked"], comp, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self._summary.setText("Export cancelled; nothing was written.")
            self._restore_export_buttons()
            return
        targets = dialog.names()
        self._wf["targets"] = targets
        self._summary.setText("Building export preview (nothing is written)...")
        self._preview_task = BackgroundTask(
            lambda _progress: PriceMdbExportService(self._context).export(
                snapshot, mdb_path, dry_run=True, list_targets=targets)
        )
        self._preview_task.signals.finished.connect(self._on_preview_finished)
        self._preview_task.signals.failed.connect(self._on_price_export_failed)
        QThreadPool.globalInstance().start(self._preview_task)

    def _on_preview_finished(self, result: dict) -> None:
        self._restore_export_buttons()
        if not result.get("ok"):
            self._summary.setText("Export preview failed.")
            QMessageBox.critical(self, "Preview Export", result.get("error") or "Preview failed.")
            return
        self._apply_text_results(result)
        write = bool(self._wf.get("write"))
        dialog = PriceExportPreviewDialog(result, self, allow_export=write)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        if not (write and accepted):
            self._summary.setText("Export preview: no MDB record was modified.")
            return
        # The write is bound to exactly this previewed plan: if the MDB or the
        # inputs differ when it runs, the export refuses and asks for a new preview.
        snapshot, mdb_path, targets = self._wf["snapshot"], self._wf["path"], self._wf["targets"]
        digest = result["plan_digest"]
        self._export_btn.setEnabled(False)
        self._preview_btn.setEnabled(False)
        self._summary.setText("Exporting prices to MDB... the application remains available.")
        self._export_task = BackgroundTask(
            lambda _progress: PriceMdbExportService(self._context).export(
                snapshot, mdb_path, list_targets=targets, expected_plan=digest)
        )
        self._export_task.signals.finished.connect(
            lambda res: self._on_price_export_finished(res, mdb_path)
        )
        self._export_task.signals.failed.connect(self._on_price_export_failed)
        QThreadPool.globalInstance().start(self._export_task)

    def _apply_text_results(self, result: dict) -> None:
        """Show the row-level text-block results of a preview / export in the table."""
        self._text_results = {row_result_key(e): e for e in (result.get("text_rows") or [])}
        self._populate()

    def _on_price_export_finished(self, result: dict, mdb_path: str) -> None:
        """Handle background export completion on the GUI thread."""
        self._restore_export_buttons()
        self._last_mdb_path = mdb_path
        if result.get("text_rows"):
            self._apply_text_results(result)
        if not result.get("ok"):
            self._summary.setText("Price export failed.")
            QMessageBox.critical(
                self, "Export Prices", result.get("error") or "Price export failed."
            )
            return
        self._summary.setText(
            f"Export complete: {result.get('inserted_prices', 0) + result.get('inserted_global_prices', 0):,} "
            f"rows added, {result.get('updated_prices', 0) + result.get('updated_global_prices', 0):,} corrected."
        )
        warnings = "\n".join(result.get("warnings") or [])
        QMessageBox.information(
            self,
            "Export Prices",
            "Price export completed. Only matching price rows were updated; price lists and unrelated rows were not replaced.\n\n"
            f"Price rows added: {result.get('inserted_prices', 0):,}\n"
            f"Global price rows added: {result.get('inserted_global_prices', 0):,}\n"
            f"Article price rows updated: {result.get('updated_prices', 0):,}\n"
            f"Global price rows updated: {result.get('updated_global_prices', 0):,}\n"
            f"Price lists added: {result.get('inserted_price_lists', 0):,}\n"
            f"Existing rows unchanged: {result.get('skipped_existing', 0):,}\n"
            f"Unmapped rows skipped: {result.get('skipped_unmapped', 0):,}\n"
            f"Ambiguous rows skipped: {result.get('skipped_ambiguous', 0):,}\n"
            f"Zero-price rows skipped: {result.get('skipped_zero_price', 0):,}\n"
            f"Read-back verified: {'yes' if result.get('verified') else 'not run'}\n"
            f"Writes that changed nothing: {result.get('failed', 0):,}\n\n"
            + "\n".join(list_lines(result) + _text_result_lines(result)) + "\n\n"
            f"File: {result.get('mdb_path', mdb_path)}"
            + (f"\n\n{warnings}" if warnings else ""),
        )

    def _on_price_export_failed(self, error: str) -> None:
        """Handle an unexpected background export exception."""
        self._restore_export_buttons()
        self._summary.setText("Price export failed.")
        QMessageBox.critical(self, "Export Prices", error or "Price export failed.")

    def _append_batch(self, records: list[PriceRecord]) -> None:
        """Append a freshly computed batch to the table live. No diff colour yet -
        the final populate re-renders with year-over-year highlighting."""
        self._records.extend(records)
        new_visible = [r for r in records if self._passes_filter(r)]
        if new_visible:
            self._table.setSortingEnabled(False)
            start = self._table.rowCount()
            self._table.setRowCount(start + len(new_visible))
            for i, rec in enumerate(new_visible):
                self._fill_row(start + i, rec, added=False, prev=None)
        self._summary.setText(
            f"Computing prices... {len(self._records)} records so far"
        )

    # -- rendering ---------------------------------------------------------
    def _passes_filter(self, rec: PriceRecord) -> bool:
        term = self._search.text().strip()
        cur = self._currency.currentText()
        if cur != "All" and (rec.currency or "").upper() != cur.upper():
            return False
        mode = self._filter.currentText()
        if mode == _FILTER_BASE and not (not rec.is_global and rec.level == "B"):
            return False
        if mode == _FILTER_UPCHARGE and rec.level != "X":
            return False
        if mode == _FILTER_GLOBAL and not rec.is_global:
            return False
        if mode == _FILTER_CHANGED and rec.key() not in self._changed \
                and rec.key() not in self._added_keys:
            return False
        if mode == _FILTER_TEXT_ISSUES and self._text_cells(rec)[2] not in ISSUE_STATUSES:
            return False
        if term:
            tid, tcontent, _status = self._text_cells(rec)
            if not text_match(term, rec.article_code, rec.variant_condition, tid, tcontent):
                return False
        return True

    def _text_cells(self, rec: PriceRecord) -> tuple[str, str, str]:
        """``(id, text, status)`` for the Text Block columns of one record."""
        return text_block_cells(
            rec, self._text_results.get(record_result_key(rec)),
            from_mdb=self.is_mdb_view(), price_texts=self._price_texts,
        )

    def _visible_records(self) -> list[PriceRecord]:
        return [rec for rec in self._records if self._passes_filter(rec)]

    def _populate(self) -> None:
        records = self._visible_records()
        # Sorting must be off while filling: with it on, each setItem re-sorts
        # the table live and scrambles cells (rows end up half-populated).
        was_sorting = self._table.isSortingEnabled()
        self._table.setSortingEnabled(False)
        self._table.setUpdatesEnabled(False)
        self._table.clearContents()
        self._table.setRowCount(len(records))
        for row, rec in enumerate(records):
            key = rec.key()
            self._fill_row(row, rec, key in self._added_keys, self._changed.get(key))
        self._table.setUpdatesEnabled(True)
        self._table.setSortingEnabled(was_sorting)
        self._table.viewport().update()

    def _fill_row(self, row: int, rec: PriceRecord, added: bool, prev) -> None:
        """Render one record into an existing table row (with diff colour)."""
        self._set(row, _COL_ARTICLE, rec.article_code)
        self._set(row, _COL_VARCOND, rec.variant_condition)
        self._set(row, _COL_VALUE, f"{rec.value:g}", align_right=True)
        self._set(row, _COL_CURRENCY, rec.currency)
        tid, tcontent, tstatus = self._text_cells(rec)
        self._set(row, _COL_TEXT_ID, tid, align_right=tstatus in (STATUS_CREATED, "existing"))
        self._set(row, _COL_TEXT, tcontent)
        for c in (_COL_TEXT_ID, _COL_TEXT):
            item = self._table.item(row, c)
            item.setToolTip(_STATUS_TIPS.get(tstatus, ""))
            if tstatus in ISSUE_STATUSES:
                item.setForeground(QBrush(_TEXT_ISSUE_FG))
            elif tstatus == STATUS_NEW:
                item.setBackground(QBrush(_TEXT_NEW_BG))
        if added:
            change = "new"
        elif prev is not None:
            change = f"{prev:g} -> {rec.value:g}"
        else:
            change = ""
        self._set(row, _COL_CHANGE, change)
        if added or prev is not None:
            bg = _ADDED_BG if added else _CHANGED_BG
            for c in range(_NUM_COLS):
                item = self._table.item(row, c)
                if item is not None:
                    item.setBackground(QBrush(bg))

    def _set(self, row: int, col: int, text: str, align_right: bool = False) -> None:
        item = QTableWidgetItem(text or "")
        if align_right:
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._table.setItem(row, col, item)

    def _schedule_filter(self) -> None:
        """Debounce search typing so the table repopulates once, not per keystroke."""
        self._filter_timer.start()

    def _apply_filter(self) -> None:
        self._populate()

    def _update_summary(self, unresolved: int, diff=None, params=None) -> None:
        if not self._records:
            self._summary.setText("No prices computed yet.")
            return
        base = sum(1 for r in self._records if not r.is_global and r.level == "B")
        ups = sum(1 for r in self._records if r.level == "X")
        glob = sum(1 for r in self._records if r.is_global)
        parts = [
            f"Base: {base}", f"Upcharge: {ups}", f"Global: {glob}",
            f"Total: {len(self._records)}",
        ]
        if unresolved:
            parts.append(f"Unresolved: {unresolved}")
        if diff is not None:
            parts.append(
                f"| Changes - added {len(diff.added)}, "
                f"changed {len(diff.changed)}, removed {len(diff.removed)}, "
                f"unchanged {diff.unchanged}"
            )
        if params is not None:
            cur = params.currency or "All"
            parts.insert(0, f"[{cur} @ {params.mydate}, site {params.site_id}]")
        if pricing_requires_recompute(self._context.active_snapshot):
            parts.insert(0, "Stored fabric pricing is outdated - Compute Prices to resolve colour conditions.")
        self._summary.setText("   ".join(parts))


_STATUS_TIPS = {
    "existing": "Text block already in the MDB (com_TextID).",
    "created": "Text block written by the export and confirmed by read-back.",
    "new": "Proposed: this text block would be created. Nothing has been written yet.",
    "missing": "The global price has no text reference (com_TextID).",
    "blocked": "Text mapping is missing or ambiguous; this row would not be inserted.",
    "unverified": "Written, but the read-back did not confirm the text block.",
    "unchecked": "Not compared with an MDB yet; use Preview Export to resolve it.",
    "n/a": "Article prices carry no text block.",
}


def _text_result_lines(result: dict) -> list[str]:
    """Post-export text-block totals: executed (and read-back verified) counts."""
    t = result.get("text_result") or {}
    linked = t.get("rows_linked")
    return [
        f"Text blocks created: {t.get('texts_created', 0):,}",
        f"Text blocks reused: {t.get('texts_reused', 0):,}",
        "Price rows linked to text blocks: " + ("not verified" if linked is None else f"{linked:,}"),
        f"Existing text links preserved: {t.get('links_preserved', 0):,}",
        f"Text operations skipped: {t.get('text_operations_skipped', 0):,}",
        f"Failed text operations: {t.get('text_operations_failed', 0):,}",
    ]


def _v(widget: QWidget):
    """A zero-margin vertical layout on ``widget`` (local helper)."""
    from PySide6.QtWidgets import QVBoxLayout

    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    return layout
