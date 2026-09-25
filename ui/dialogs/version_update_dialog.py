"""Bulk export-version updater - pick series, key a version, write OCD + ODB.

Scans the repository for series, shows each one's current OCD/ODB version with a
checkbox, and writes a user-keyed ``Major.Minor.Build`` into the selected series'
both databases. Scan and apply run off the UI thread (each reads/writes many
MDBs through the 32-bit bridge) with a progress popup.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from ui.components import DialogTemplate

_COLS = ["", "Series", "OCD version", "ODB version", "Files"]


class _Signals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class _ScanWorker(QRunnable):
    """Discover series and read their current OCD/ODB versions."""

    def __init__(self, service, repo, reporter, signals):
        super().__init__()
        self._svc, self._repo, self._reporter, self._signals = service, repo, reporter, signals

    def run(self) -> None:
        try:
            folders = self._svc.series_folders(self._repo)
            self._reporter.begin(max(len(folders), 1), title="Scan Versions",
                                 subject=Path(self._repo.split(";")[0].strip()).name)
            series = self._svc.read_series(
                folders, progress=lambda d, t, text: self._reporter.advance(text))
        except Exception as exc:  # never crash the worker thread
            self._reporter.finish(False, str(exc))
            self._signals.failed.emit(str(exc))
        else:
            self._reporter.finish(True, f"{len(series)} series")
            self._signals.finished.emit(series)


class _ApplyWorker(QRunnable):
    """Write the keyed version into the selected series' OCD + ODB packages."""

    def __init__(self, service, series, mmb, reporter, signals):
        super().__init__()
        self._svc, self._series, self._mmb = service, series, mmb
        self._reporter, self._signals = reporter, signals

    def run(self) -> None:
        try:
            self._reporter.begin(max(len(self._series), 1), title="Update Version", subject="")
            results = self._svc.update(
                self._series, *self._mmb,
                progress=lambda d, t, text: self._reporter.advance(text))
        except Exception as exc:
            self._reporter.finish(False, str(exc))
            self._signals.failed.emit(str(exc))
        else:
            self._reporter.finish(True, f"{len(results)} updated")
            self._signals.finished.emit(results)


class VersionUpdateDialog(DialogTemplate):
    """Select series and bulk-write a keyed export version to OCD + ODB."""

    def __init__(self, service, repository: str = "", parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._series: list = []
        self.set_title("Update Export Version")
        self.setMinimumSize(760, 560)
        self._build_inputs(repository)
        self._build_table()
        self._build_footer()

    # -- construction ---------------------------------------------------

    def _build_inputs(self, repository: str) -> None:
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Repository:", self))
        self._repo = QLineEdit(self)
        self._repo.setText(repository)
        self._repo.setPlaceholderText("Repository root(s) - separate several with ';'")
        browse = QPushButton("Browse...", self)
        browse.clicked.connect(self._on_browse)
        scan = QPushButton("Scan", self)
        scan.clicked.connect(self._on_scan)
        row1.addWidget(self._repo, 1)
        row1.addWidget(browse)
        row1.addWidget(scan)
        self.add_content_layout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("New version:", self))
        self._version = QLineEdit(self)
        self._version.setPlaceholderText("e.g. 1.34.0 (Major.Minor.Build)")
        self._version.setMaximumWidth(180)
        row2.addWidget(self._version)
        row2.addStretch(1)
        self.add_content_layout(row2)

    def _build_table(self) -> None:
        self._table = QTableWidget(0, len(_COLS), self)
        self._table.setHorizontalHeaderLabels(_COLS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 28)
        self.add_content(self._table)

    def _build_footer(self) -> None:
        select_all = QPushButton("Select All", self)
        select_all.clicked.connect(lambda: self._set_all(True))
        clear = QPushButton("Clear", self)
        clear.clicked.connect(lambda: self._set_all(False))
        apply = QPushButton("Apply", self)
        apply.clicked.connect(self._on_apply)
        close = QPushButton("Close", self)
        close.clicked.connect(self.accept)
        for btn in (select_all, clear, apply, close):
            self.add_footer_button(btn)

    # -- helpers --------------------------------------------------------

    def _progress_monitor(self):
        monitor = getattr(self, "_monitor", None)
        if monitor is None:
            from ui.dialogs.progress_dialog import ProgressDialog
            monitor = ProgressDialog(self)
            self._monitor = monitor
        return monitor

    def _start(self, worker_factory, on_ready) -> None:
        from core.progress import ProgressReporter
        reporter = ProgressReporter(self)
        monitor = self._progress_monitor()
        monitor.bind(reporter)
        monitor.show()
        monitor.raise_()
        signals = _Signals()
        signals.finished.connect(on_ready)
        signals.failed.connect(self._on_failed)
        self._signals = signals  # keep a reference alive
        QThreadPool.globalInstance().start(worker_factory(reporter, signals))

    def _set_all(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for r in range(self._table.rowCount()):
            self._table.item(r, 0).setCheckState(state)

    def _checked_series(self) -> list:
        return [self._series[r] for r in range(self._table.rowCount())
                if self._table.item(r, 0).checkState() == Qt.CheckState.Checked]

    # -- actions --------------------------------------------------------

    def _on_browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select a repository root")
        if not path:
            return
        parts = [p.strip() for p in self._repo.text().split(";") if p.strip()]
        if path not in parts:
            parts.append(path)
        self._repo.setText(";".join(parts))

    def _on_scan(self) -> None:
        repo = self._repo.text().strip()
        if not repo:
            QMessageBox.information(self, "Update Version", "Choose the repository root.")
            return
        self._start(
            lambda reporter, signals: _ScanWorker(self._service, repo, reporter, signals),
            self._on_scanned)

    def _on_scanned(self, series) -> None:
        self._series = list(series)
        self._table.setRowCount(len(self._series))
        for r, sv in enumerate(self._series):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check.setCheckState(Qt.CheckState.Unchecked)
            self._table.setItem(r, 0, check)
            files = "OCD+ODB" if sv.ocd_path and sv.odb_path else (
                "OCD only" if sv.ocd_path else "ODB only")
            for c, text in enumerate(
                (sv.program, sv.ocd_version or "-", sv.odb_version or "-", files), start=1
            ):
                item = QTableWidgetItem(str(text))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(r, c, item)
        self._table.resizeColumnsToContents()
        self._table.setColumnWidth(0, 28)
        if not self._series:
            QMessageBox.information(
                self, "Update Version",
                "No series found under the repository. Check the path and try again.")

    def _on_apply(self) -> None:
        mmb = self._service.parse_version(self._version.text())
        if mmb is None:
            QMessageBox.information(
                self, "Update Version", "Enter a version as Major.Minor.Build (e.g. 1.34.0).")
            return
        selected = self._checked_series()
        if not selected:
            QMessageBox.information(self, "Update Version", "Select at least one series.")
            return
        version = ".".join(str(n) for n in mmb)
        answer = QMessageBox.question(
            self, "Update Version",
            f"Write version {version} (and today's release date) into {len(selected)} "
            f"series' OCD + ODB packages?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._start(
            lambda reporter, signals: _ApplyWorker(
                self._service, selected, mmb, reporter, signals),
            self._on_applied)

    def _on_applied(self, results) -> None:
        ok = sum(1 for r in results if r.error is None)
        failed = [r for r in results if r.error is not None]
        message = f"Updated {ok} of {len(results)} series."
        if failed:
            message += "\n\nFailed:\n" + "\n".join(
                f"  {r.series}: {r.error}" for r in failed[:8])
        QMessageBox.information(self, "Update Version", message)
        self._on_scan()  # refresh the shown versions

    def _on_failed(self, message: str) -> None:
        QMessageBox.warning(self, "Update Version", f"Operation failed:\n{message}")
