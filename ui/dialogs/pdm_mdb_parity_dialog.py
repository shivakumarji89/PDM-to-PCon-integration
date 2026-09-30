"""Maintenance parity dialog."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from services.pdm_mdb_parity_service import PdmMdbParityService
from ui.workers.background_task import BackgroundTask


class PdmMdbParityDialog(QDialog):
    """Read-only comparison of the PDM Snapshot against a reference MDB."""

    def __init__(self, context, parent=None) -> None:
        super().__init__(parent)
        self._context = context
        self._service = PdmMdbParityService(context)
        self._task: BackgroundTask | None = None
        self.setWindowTitle("PDM ↔ MDB Parity")
        self.resize(1100, 680)

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "Compare the current PDM Snapshot with a manually authored/reference "
                "MDB. The comparison is read-only."
            )
        )

        row = QHBoxLayout()
        self._path = QLineEdit(self)
        self._path.setPlaceholderText("Reference OCD MDB path")
        browse = QPushButton("Browse…", self)
        browse.clicked.connect(self._browse)
        row.addWidget(self._path, 1)
        row.addWidget(browse)
        root.addLayout(row)

        action = QHBoxLayout()
        self._run = QPushButton("Run Parity", self)
        self._run.clicked.connect(self._run_parity)
        self._status = QLabel("Select an MDB and run parity.", self)
        action.addWidget(self._run)
        action.addWidget(self._status, 1)
        root.addLayout(action)

        self._progress = QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.hide()
        root.addWidget(self._progress)

        self._table = QTableWidget(0, 5, self)
        self._table.setHorizontalHeaderLabels(
            ["Domain", "Status", "Key", "Expected", "Actual"]
        )
        self._table.setWordWrap(False)
        self._table.setAlternatingRowColors(True)
        root.addWidget(self._table, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, parent=self
        )
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select reference MDB",
            "",
            "Access database (*.mdb *.accdb);;All files (*)",
        )
        if path:
            self._path.setText(path)

    def _run_parity(self) -> None:
        path = self._path.text().strip()
        if not path:
            self._status.setText("Select a reference MDB first.")
            return
        if not Path(path).is_file():
            self._status.setText("The selected MDB does not exist.")
            return

        snapshot = self._context.pdm_snapshot
        if snapshot is None:
            self._status.setText(
                "No PDM Snapshot is loaded. Load PDM data in Development first."
            )
            return

        if snapshot.maintenance_alignment_status != "ALIGNED":
            self._status.setText(
                "Maintenance alignment is incomplete. "
                "Resolve the released MDB base-article alignment before parity."
            )
            return

        self._run.setEnabled(False)
        self._progress.show()
        self._table.setRowCount(0)
        self._status.setText("Starting parity check...")

        task = BackgroundTask(
            lambda emit: self._service.compare(snapshot, path, progress=emit)
        )
        self._task = task
        task.signals.progress.connect(self._on_progress)
        task.signals.finished.connect(self._on_finished)
        task.signals.failed.connect(self._on_failed)
        QThreadPool.globalInstance().start(task)

    def _on_progress(self, message: str) -> None:
        self._status.setText(message)

    def _on_finished(self, report) -> None:
        self._progress.hide()
        self._run.setEnabled(True)
        self._show_report(report)

    def _on_failed(self, message: str) -> None:
        self._progress.hide()
        self._run.setEnabled(True)
        self._status.setText(f"Parity failed: {message}")

    def _show_report(self, report) -> None:
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

        self._status.setText(
            f"{'PASS' if report.passed else 'DIFFERENCES FOUND'} — "
            f"{report.match_count} match, {report.missing_count} missing, "
            f"{report.extra_count} extra, {report.different_count} different."
        )
