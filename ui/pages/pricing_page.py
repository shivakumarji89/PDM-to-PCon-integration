"""Pricing workspace page.

A snapshot-driven workbench for computing the product's OCD price records
(``tCOMd_Price`` / ``tCOMd_GlobalPrice``) from PDM. Values are computed by SQL
Server's own ``fnGetListPrice*`` functions in a few batched queries, so they are
byte-identical to PDM's *Update pCon Prices* button - only far faster. The tool
auto-routes each item to article vs global pricing and diffs the result against
the stored baseline so only changed cells stand out.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
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
from services.pricing_service import PriceParams, PricingService
from ui.dialogs.progress_dialog import ProgressDialog
from ui.pages.base_page import BasePage

# Map ProgressReporter log kinds to activity log levels.
_ACT_LEVEL = {
    "info": LogLevel.INFO,
    "success": LogLevel.SUCCESS,
    "warning": LogLevel.WARNING,
    "error": LogLevel.ERROR,
}


class _PricingSignals(QObject):
    """Signals emitted from the background pricing worker."""

    batch = Signal(list)      # list[PriceRecord] as each batch is computed
    finished = Signal(object)  # PriceComputeResult
    failed = Signal(str)       # error message


class _PricingWorker(QRunnable):
    """Computes prices off the UI thread so the progress popup stays live.

    Batches are marshalled to the UI via ``signals.batch``; the reporter (created
    on the UI thread) is driven from here and its cross-thread signals update the
    dialog smoothly because the UI thread is never blocked.
    """

    def __init__(self, context, params, snapshot, reporter, signals):
        super().__init__()
        self._context = context
        self._params = params
        self._snapshot = snapshot
        self._reporter = reporter
        self._signals = signals

    def run(self) -> None:
        try:
            result = PricingService(self._context).compute_streaming(
                self._params, self._snapshot,
                on_batch=lambda recs: self._signals.batch.emit(recs),
                reporter=self._reporter,
            )
        except Exception as error:  # defensive: never crash the worker thread
            self._reporter.finish(False, str(error))
            self._signals.failed.emit(str(error))
        else:
            self._signals.finished.emit(result)


_COL_ARTICLE = 0
_COL_VARCOND = 1
_COL_VALUE = 2
_COL_CURRENCY = 3
_COL_CHANGE = 4

_FILTER_ALL = "All records"
_FILTER_BASE = "Base (B)"
_FILTER_UPCHARGE = "Upcharge (X)"
_FILTER_GLOBAL = "Global / super"
_FILTER_CHANGED = "Changed only"

_CHANGED_BG = QColor(255, 244, 204)
_ADDED_BG = QColor(223, 245, 223)


class PricingPage(BasePage):
    """Compute and review OCD price records for the active snapshot."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Pricing",
            description="Compute PDM-accurate OCD prices and review year-over-year changes.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._records: list[PriceRecord] = []
        #: Diff state keyed like PriceRecord.key(): "added" / "changed" / prior value.
        self._added_keys: set = set()
        self._changed: dict = {}

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
        self._export_btn.setToolTip("Write changed price records to the OCD MDB.")
        self._export_btn.setEnabled(False)  # enabled once export is implemented
        layout.addWidget(self._export_btn)

        self._pricelists_btn = QPushButton("Price Lists\u2026", box)
        self._pricelists_btn.setToolTip(
            "Define named price lists (currency + validity) with date roll-over."
        )
        self._pricelists_btn.clicked.connect(self._on_manage_price_lists)
        layout.addWidget(self._pricelists_btn)

        layout.addStretch(1)
        return box

    # -- price lists (named lists + date roll-over) ----------------------
    def _on_manage_price_lists(self) -> None:
        snapshot = self._context.active_snapshot
        if snapshot is None:
            QMessageBox.information(self, "Price Lists", "Load a product first.")
            return
        svc = self._context.price_list_service
        dialog = QDialog(self)
        dialog.setWindowTitle("Price Lists")
        dialog.setMinimumSize(620, 380)
        layout = QVBoxLayout(dialog)

        table = QTableWidget(0, 5, dialog)
        table.setHorizontalHeaderLabels(
            ["Id", "Label", "Currency", "Valid From", "Valid To"]
        )
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)

        def render() -> None:
            table.setRowCount(0)
            for price_list in svc.price_lists(snapshot):
                row = table.rowCount()
                table.insertRow(row)
                cells = [
                    price_list.id, price_list.label, price_list.currency,
                    price_list.date_from, price_list.date_to,
                ]
                for col, value in enumerate(cells):
                    table.setItem(row, col, QTableWidgetItem(value))

        add_bar = QHBoxLayout()
        id_edit = QLineEdit(dialog)
        id_edit.setPlaceholderText("id e.g. euro_2026")
        label_edit = QLineEdit(dialog)
        label_edit.setPlaceholderText("label")
        cur_combo = QComboBox(dialog)
        cur_combo.addItems(["EUR", "GBP"])
        date_edit = QDateEdit(dialog)
        date_edit.setDisplayFormat("dd-MMM-yyyy")
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.currentDate())
        add_btn = QPushButton("Add", dialog)

        def on_add() -> None:
            created = svc.add_price_list(
                snapshot, id_edit.text(), label_edit.text(),
                cur_combo.currentText(), date_edit.date().toString("yyyyMMdd"),
            )
            if created is None:
                QMessageBox.warning(dialog, "Price Lists", "Enter a unique id.")
                return
            self._context.snapshot_manager.mark_modified()
            id_edit.clear()
            label_edit.clear()
            render()

        add_btn.clicked.connect(on_add)
        for widget in (id_edit, label_edit, cur_combo, date_edit, add_btn):
            add_bar.addWidget(widget)
        layout.addLayout(add_bar)

        button_bar = QHBoxLayout()
        remove_btn = QPushButton("Remove selected", dialog)

        def on_remove() -> None:
            row = table.currentRow()
            if row < 0 or table.item(row, 0) is None:
                return
            if svc.remove_price_list(snapshot, table.item(row, 0).text()):
                self._context.snapshot_manager.mark_modified()
                render()

        remove_btn.clicked.connect(on_remove)
        button_bar.addWidget(remove_btn)
        button_bar.addStretch(1)
        close_btn = QPushButton("Close", dialog)
        close_btn.clicked.connect(dialog.accept)
        button_bar.addWidget(close_btn)
        layout.addLayout(button_bar)

        render()
        dialog.exec()

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
        self._search.setPlaceholderText("Search article or variant condition...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._schedule_filter)
        frow.addWidget(self._search, 1)
        frow.addWidget(QLabel("Show:", filter_row))
        self._filter = QComboBox(filter_row)
        self._filter.addItems([
            _FILTER_ALL, _FILTER_BASE, _FILTER_UPCHARGE,
            _FILTER_GLOBAL, _FILTER_CHANGED,
        ])
        self._filter.currentIndexChanged.connect(self._apply_filter)
        frow.addWidget(self._filter)
        vlayout.addWidget(filter_row)

        self._table = QTableWidget(0, 5, container)
        self._table.setHorizontalHeaderLabels(
            ["Article", "Variant Condition", "Value", "Currency", "Change"]
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(_COL_VARCOND, QHeaderView.ResizeMode.Stretch)
        for c in (_COL_ARTICLE, _COL_VALUE, _COL_CURRENCY, _COL_CHANGE):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
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
        """Reload from the active snapshot's stored price records."""
        snapshot = self._context.active_snapshot
        self._records = list(snapshot.price_records) if snapshot else []
        self._added_keys = set()
        self._changed = {}
        self._populate()
        self._update_summary(unresolved=0)

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

    def _params(self) -> PriceParams:
        d = self._date.date()
        sel = self._currency.currentText()
        return PriceParams(
            currency="" if sel == "All" else sel,
            mydate=d.toString("dd-MMM-yyyy"),
            site_id=self._site.value(),
            valid_from=d.toString("yyyy-MM-dd"),
            valid_to="",
        )

    def _on_compute(self) -> None:
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
        self._baseline = [
            r for r in snapshot.price_records if (r.currency or "").upper() in currencies
        ]
        # Stream: clear the table and append records as each batch arrives so the
        # operator sees progress instead of a frozen window until the end.
        self._records = []
        self._added_keys = set()
        self._changed = {}
        self._table.setSortingEnabled(False)
        self._table.clearContents()
        self._table.setRowCount(0)
        self._compute_btn.setEnabled(False)

        self._price_params = params
        reporter = ProgressReporter(self)
        self._price_reporter = reporter
        monitor = self._progress_monitor()
        monitor.bind(reporter)
        monitor.show()
        monitor.raise_()
        # Also record the run in the Activity timeline so it lands in the log.
        activity = self._context.activity_service.start_activity(
            "Computing Prices", ActivityType.GENERIC,
            context={"Currency": params.currency, "Date": params.mydate},
        )
        self._price_activity = activity  # keep referenced for the run
        # Wrap in lambdas: ActivityHandle uses __slots__ (no __weakref__), so a
        # signal cannot connect directly to its bound methods.
        reporter.step_changed.connect(lambda text: activity.update_step(text))
        reporter.activity.connect(
            lambda kind, msg: activity.add_log(msg, _ACT_LEVEL.get(kind, LogLevel.INFO))
        )
        reporter.finished.connect(
            lambda ok, msg: activity.complete(msg) if ok else activity.fail(msg)
        )

        # Compute off the UI thread so the popup animates instead of freezing.
        signals = _PricingSignals()
        signals.batch.connect(self._append_batch)
        signals.finished.connect(self._on_pricing_finished)
        signals.failed.connect(self._on_pricing_failed)
        self._price_signals = signals
        worker = _PricingWorker(self._context, params, snapshot, reporter, signals)
        QThreadPool.globalInstance().start(worker)

    def _on_pricing_finished(self, result) -> None:
        diff = PricingService.diff(self._baseline, result.records)
        self._records = list(result.records)
        self._added_keys = {r.key() for r in diff.added}
        self._changed = {new.key(): old.value for old, new in diff.changed}
        self._populate()  # final authoritative render (filter + diff colours)
        self._update_summary(
            unresolved=len(result.unresolved), diff=diff, params=self._price_params
        )
        self._compute_btn.setEnabled(True)
        if result.warnings:
            QMessageBox.information(
                self, "Compute Prices", "\n".join(result.warnings)
            )

    def _on_pricing_failed(self, message: str) -> None:
        self._compute_btn.setEnabled(True)
        QMessageBox.critical(
            self, "Compute Prices", f"Price computation failed:\n\n{message}"
        )

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
        if term and not text_match(term, rec.article_code, rec.variant_condition):
            return False
        return True

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
        if added:
            change = "new"
        elif prev is not None:
            change = f"{prev:g} -> {rec.value:g}"
        else:
            change = ""
        self._set(row, _COL_CHANGE, change)
        if added or prev is not None:
            bg = _ADDED_BG if added else _CHANGED_BG
            for c in range(5):
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
        self._summary.setText("   ".join(parts))


def _v(widget: QWidget):
    """A zero-margin vertical layout on ``widget`` (local helper)."""
    from PySide6.QtWidgets import QVBoxLayout

    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    return layout
