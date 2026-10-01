"""Maintenance PDM ↔ released MDB comparison workspace."""
from __future__ import annotations

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.maintenance_parity_service import MaintenanceParityService
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
        )
        self._context = context
        self._service = MaintenanceParityService(context)
        self._task: BackgroundTask | None = None

        self._summary = QGroupBox("Comparison Summary", self)
        summary = QGridLayout(self._summary)
        self._status = QLabel("Waiting for Maintenance data.", self._summary)
        self._pdm = QLabel("-", self._summary)
        self._mdb = QLabel("-", self._summary)
        self._alignment = QLabel("-", self._summary)
        self._counts = QLabel("-", self._summary)
        self._pdm_identity = QLabel("-", self._summary)
        self._mdb_identity = QLabel("-", self._summary)
        self._pdm_identity.setWordWrap(True)
        self._mdb_identity.setWordWrap(True)
        summary.addWidget(QLabel("Status"), 0, 0)
        summary.addWidget(self._status, 0, 1, 1, 3)
        summary.addWidget(QLabel("PDM articles"), 1, 0)
        summary.addWidget(self._pdm, 1, 1)
        summary.addWidget(QLabel("Released MDB articles"), 1, 2)
        summary.addWidget(self._mdb, 1, 3)
        summary.addWidget(QLabel("PDM source"), 3, 0)
        summary.addWidget(self._pdm_identity, 3, 1, 1, 3)
        summary.addWidget(QLabel("MDB source"), 4, 0)
        summary.addWidget(self._mdb_identity, 4, 1, 1, 3)
        summary.addWidget(QLabel("Alignment"), 2, 0)
        summary.addWidget(self._alignment, 2, 1)
        summary.addWidget(QLabel("Results"), 2, 2)
        summary.addWidget(self._counts, 2, 3)
        self.add_content(self._summary)

        self._progress = QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.hide()
        self.add_content(self._progress)

        self._table = QTableWidget(0, 5, self)
        self._table.setHorizontalHeaderLabels(
            ["Domain", "Status", "Comparison Key", "PDM (Selected Product)", "Released MDB (Linked Repository)"]
        )
        self._table.setWordWrap(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self.add_content(self._table)

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
            return

        if state.mdb_snapshot is None:
            self._status.setText("Load the released MDB repository first.")
            self._alignment.setText(state.alignment.status)
            self._pdm.setText(str(len(state.pdm_snapshot.articles)))
            self._mdb.setText("-")
            self._counts.setText("-")
            self._pdm_identity.setText(self._pdm_source_text(state.pdm_snapshot))
            self._mdb_identity.setText("-")
            self._table.setRowCount(0)
            return

        self._alignment.setText(state.alignment.status)
        self._pdm.setText(str(len(state.pdm_snapshot.articles)))
        self._mdb.setText(str(len(state.mdb_snapshot.articles)))
        self._pdm_identity.setText(self._pdm_source_text(state.pdm_snapshot))
        self._mdb_identity.setText(self._mdb_source_text(state))

        if not state.alignment.is_aligned:
            self._status.setText(
                "Comparison blocked: Maintenance PDM ↔ MDB article alignment is incomplete."
            )
            self._counts.setText("Resolve alignment first")
            self._table.setRowCount(0)
            return

        self._run_comparison()

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
        snapshot = state.mdb_snapshot
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
            and state.mdb_snapshot
            and state.alignment.is_aligned
        )

    def _run_comparison(self) -> None:
        if self._task is not None:
            return
        self._progress.show()
        self._status.setText("Comparing PDM with released MDB...")
        self._counts.setText("Calculating...")
        self._table.setRowCount(0)

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
                self._table.setItem(row, column, QTableWidgetItem(str(value)))
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
        self.auto_fit_tables()

    def _on_failed(self, message: str) -> None:
        self._task = None
        self._progress.hide()
        self._status.setText(f"Comparison failed: {message}")
        self._counts.setText("-")
