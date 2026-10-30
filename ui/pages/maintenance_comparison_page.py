"""Maintenance PDM ↔ released MDB comparison workspace."""
from __future__ import annotations

from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from services.maintenance_parity_service import (
    MATCH,
    MaintenanceParityService,
)
from ui import theme
from ui.components import (
    CardRow,
    DataCard,
    InfoCard,
    KpiCard,
    StatusCard,
    style_progress_bar,
    style_table,
)
from ui.pages.base_page import BasePage
from ui.workers.background_task import BackgroundTask


class MaintenanceComparisonPage(BasePage):
    """Show the read-only comparison between the loaded PDM scope and MDB."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="PDM ↔ MDB Comparison",
            description=(
                "Compare the loaded Maintenance PDM scope with the released "
                "MDB repository data. This comparison is read-only."
            ),
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
            workflow_layout=True,
            header_glyph="⇄",
        )
        self._context = context
        self._service = MaintenanceParityService(context)
        self._task: BackgroundTask | None = None

        # Status banner (message + indeterminate progress while comparing).
        self._banner = StatusCard("Comparison status", "Waiting for Maintenance data.", "neutral", parent=self)
        self._status = self._banner.message_label
        self._progress = QProgressBar(self)
        self._progress.setRange(0, 0)
        style_progress_bar(self._progress, "success")
        self._progress.hide()
        self._banner.body.addWidget(self._progress)
        self.wf.add_summary(self._banner)

        # Summary cards: the value labels are the page's existing label fields.
        self._pdm_card = KpiCard("PDM articles", "-", "neutral", glyph="P", parent=self)
        self._mdb_card = KpiCard("Released MDB articles", "-", "neutral", glyph="M", parent=self)
        self._alignment_card = KpiCard("Alignment", "-", "neutral", parent=self)
        self._results_card = KpiCard("Results", "-", "neutral", compact_value=True, parent=self)
        self._pdm = self._pdm_card.value_label
        self._mdb = self._mdb_card.value_label
        self._alignment = self._alignment_card.value_label
        self._counts = self._results_card.value_label
        cards = CardRow(200, self)
        for card in (self._pdm_card, self._mdb_card, self._alignment_card, self._results_card):
            cards.add_card(card)
        self.wf.add_summary(cards)

        self._sources = InfoCard("Compared sources", parent=self)
        self._pdm_identity = self._sources.add_row("PDM source", "-")
        self._mdb_identity = self._sources.add_row("MDB source", "-")
        self.wf.add_summary(self._sources)

        self._table = QTableWidget(0, 5, self)
        self._table.setHorizontalHeaderLabels(
            ["Domain", "Status", "Comparison Key", "PDM (Selected Product)", "Released MDB (Linked Repository)"]
        )
        self._table.setWordWrap(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        style_table(self._table)
        self._table_card = DataCard("Differences", "No comparison results yet.", parent=self)
        self._table_card.set_content(self._table)
        self.add_content(self._table_card)

        self.refresh()

    def refresh(self) -> None:
        state = self._context.maintenance_snapshot
        if state is None or state.pdm_snapshot is None:
            self._status.setText("Load a Maintenance PDM scope first.")
            self._alignment.setText("Not loaded")
            self._pdm.setText("-")
            self._mdb.setText("-")
            self._counts.setText("-")
            self._pdm_identity.setText("-")
            self._mdb_identity.setText("-")
            self._table.setRowCount(0)
            self._sync_presentation()
            return

        if state.mdb_import_snapshot is None:
            self._status.setText("Load the released MDB repository first.")
            self._alignment.setText(state.alignment.status)
            self._pdm.setText(str(len(state.pdm_snapshot.articles)))
            self._mdb.setText("-")
            self._counts.setText("-")
            self._pdm_identity.setText(self._pdm_source_text(state.pdm_snapshot))
            self._mdb_identity.setText("-")
            self._table.setRowCount(0)
            self._sync_presentation()
            return

        self._alignment.setText(state.alignment.status)
        self._pdm.setText(str(len(state.pdm_snapshot.articles)))
        self._mdb.setText(str(len(state.mdb_import_snapshot.articles)))
        self._pdm_identity.setText(self._pdm_source_text(state.pdm_snapshot))
        self._mdb_identity.setText(self._mdb_source_text(state))

        if not state.alignment.is_aligned:
            self._status.setText(
                "Comparison blocked: Maintenance PDM ↔ MDB article alignment is incomplete."
            )
            self._counts.setText("Resolve alignment first")
            self._table.setRowCount(0)
            self._sync_presentation()
            return

        self._run_comparison()
        self._sync_presentation()

    @staticmethod
    def _pdm_source_text(snapshot) -> str:
        product = getattr(snapshot, "product", None)
        if product is None:
            return "PDM product: not loaded"
        code = str(getattr(product, "code", "") or "-")
        name = str(getattr(product, "name", "") or "-")
        return f"{code} — {name} (PDM)"

    @staticmethod
    def _mdb_source_text(state) -> str:
        snapshot = state.mdb_import_snapshot
        metadata = getattr(snapshot, "metadata", None)
        source = str(getattr(metadata, "source", "") or "MDB")
        notes = str(getattr(metadata, "notes", "") or "")
        product_code = str(getattr(metadata, "product_code", "") or "")
        identity = product_code or "Released repository"
        suffix = f" — {notes}" if notes else ""
        return f"{identity} — {source} (released MDB){suffix}"

    def is_ready(self) -> bool:
        state = self._context.maintenance_snapshot
        return bool(
            state
            and state.pdm_snapshot
            and state.mdb_import_snapshot
            and state.alignment.is_aligned
        )

    def _run_comparison(self) -> None:
        if self._task is not None:
            return
        self._progress.show()
        self._status.setText("Comparing PDM with released MDB...")
        self._counts.setText("Calculating...")
        self._table.setRowCount(0)
        self._sync_presentation()

        task = BackgroundTask(
            lambda emit: self._service.compare_loaded(
                self._context.maintenance_snapshot,
                progress=emit,
            )
        )
        self._task = task
        task.signals.progress.connect(self._on_progress)
        task.signals.finished.connect(self._on_finished)
        task.signals.failed.connect(self._on_failed)
        QThreadPool.globalInstance().start(task)

    def _on_progress(self, message: str) -> None:
        self._status.setText(message)
        self._sync_presentation()

    def _on_finished(self, report) -> None:
        self._task = None
        self._progress.hide()
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(report.differences))
        for row, difference in enumerate(report.differences):
            values = (
                difference.domain,
                difference.status,
                difference.key,
                difference.expected,
                difference.actual,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 1:
                    item.setForeground(QBrush(QColor(theme.WB_GREEN_DARK if value == MATCH else theme.WB_RED)))
                self._table.setItem(row, column, item)
        self._table.setSortingEnabled(True)
        self._counts.setText(
            f"{report.match_count} match | {report.missing_count} missing | "
            f"{report.extra_count} extra | {report.different_count} different"
        )
        self._status.setText(
            "PDM ↔ MDB comparison PASS."
            if report.passed
            else "PDM ↔ MDB comparison found differences."
        )
        self._sync_presentation()
        self.auto_fit_tables()

    def _on_failed(self, message: str) -> None:
        self._task = None
        self._progress.hide()
        self._status.setText(f"Comparison failed: {message}")
        self._counts.setText("-")
        self._sync_presentation()

    # -- presentation only: tones, pill and card captions follow the labels ----
    def _sync_presentation(self) -> None:
        status = self._status.text()
        alignment = self._alignment.text()
        running = not self._progress.isHidden()
        if status.startswith("Comparison failed") or status.startswith("Comparison blocked"):
            tone, pill = "danger", ("Blocked" if "blocked" in status else "Failed")
        elif "PASS" in status:
            tone, pill = "success", "Pass"
        elif "found differences" in status:
            tone, pill = "danger", "Differences"
        elif running:
            tone, pill = "warning", "Comparing"
        else:
            tone, pill = "neutral", "Not ready"
        self._banner.set_status(tone, message=None)
        self.wf.header.set_status(pill, tone)

        if alignment == "ALIGNED":
            self._alignment_card.set_tone("success")
        elif alignment in ("-", "Not loaded"):
            self._alignment_card.set_tone("neutral")
        else:
            self._alignment_card.set_tone("danger")
        self._pdm_card.set_tone("success" if self._pdm.text() not in ("-", "") else "neutral", "P")
        self._mdb_card.set_tone("success" if self._mdb.text() not in ("-", "") else "neutral", "M")
        self._results_card.set_tone(tone if tone != "warning" else "neutral")

        rows = self._table.rowCount()
        self._table_card.set_subtitle(f"{rows:,} compared item(s)" if rows else "No comparison results yet.")