"""Progress + results dialog for Basket Validation. The automation runs in a QThread; the UI stays responsive."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar, QPushButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout)

from services.basket_validation import entry
from services.basket_validation.entry import AutomationConfig, BasketValidationUnavailable, ValidationResult
from ui import theme


class BasketValidationWorker(QThread):
    progress = Signal(str, str)           # message, phase ("" when none)
    finished_ok = Signal(object)          # ValidationResult
    failed = Signal(str)

    def __init__(self, files: Sequence[Path], config: AutomationConfig, parent=None) -> None:
        super().__init__(parent)
        self._files, self._config = list(files), config
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        try:
            result = entry.run_validation(self._files, self._config, lambda m, p=None: self.progress.emit(m, p or ""), self._cancel)
        except BasketValidationUnavailable as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001 - surfaced to the user, never swallowed
            self.failed.emit(f"Unexpected error: {exc!r}")
        else:
            self.finished_ok.emit(result)


def _colour(status: str) -> str:
    return theme.COLOR_OK if status == entry.PASS else (theme.COLOR_WARNING if status in (entry.NOT_VERIFIED, "CANCELLED") else theme.COLOR_ERROR)


class BasketValidationDialog(QDialog):
    def __init__(self, files: Sequence[Path], config: AutomationConfig | None = None, parent=None, autostart: bool = True) -> None:
        super().__init__(parent)
        self.setWindowTitle("Basket Validation (pCon.basket CE)")
        self.resize(760, 560)
        self.result: ValidationResult | None = None
        self.error: str | None = None
        self._files = [Path(f) for f in files]
        self._config = config or entry.default_config()
        self._worker: BasketValidationWorker | None = None
        layout = QVBoxLayout(self)
        self.files_label = QLabel("Files: " + ", ".join(f.name for f in self._files), self)
        self.files_label.setWordWrap(True)
        self.status_label = QLabel("Starting...", self)
        self.status_label.setWordWrap(True)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, len(entry.PHASES))
        self.overall_label = QLabel("", self)
        self.overall_label.setStyleSheet("font-weight: bold;")
        self.overall_label.setWordWrap(True)
        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["File / check", "Result", "Detail"])
        self.tree.setColumnWidth(0, 360)
        self.log = QPlainTextEdit(self)
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        row = QHBoxLayout()
        self.evidence_button = QPushButton("Open Evidence Folder", self)
        self.evidence_button.setEnabled(False)
        self.evidence_button.clicked.connect(self.open_evidence_folder)
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self._on_cancel)
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.close)
        self.close_button.setEnabled(False)
        for w in (self.evidence_button, self.cancel_button, self.close_button):
            row.addWidget(w)
        for w in (self.files_label, self.status_label, self.progress_bar, self.overall_label, self.tree, self.log):
            layout.addWidget(w)
        layout.addLayout(row)
        if autostart:
            self.start()

    # ------------------------------------------------------------------ run
    def start(self) -> None:
        self._worker = BasketValidationWorker(self._files, self._config, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_result)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def wait(self, ms: int = 600000) -> bool:
        return self._worker.wait(ms) if self._worker else True

    def _on_cancel(self) -> None:
        if self._worker:
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Cancelling...")
            self._worker.cancel()

    def _on_progress(self, message: str, phase: str) -> None:
        self.status_label.setText(message)
        self.log.appendPlainText(message)
        if phase in entry.PHASES:
            self.progress_bar.setValue(entry.PHASES.index(phase) + 1)

    def _on_failed(self, message: str) -> None:
        self.error = message
        self._finish()
        self.status_label.setText("Basket Validation could not run.")
        self.overall_label.setText(f"ERROR - {message}")
        self.overall_label.setStyleSheet(f"font-weight: bold; color: {theme.COLOR_ERROR};")

    def _on_result(self, result: ValidationResult) -> None:
        self.result = result
        self._finish()
        self.status_label.setText("Finished.")
        if result.overall != "CANCELLED":
            self.progress_bar.setValue(len(entry.PHASES))
        integrity = " Original OBX files verified unchanged (SHA-256)." if result.originals_unchanged else ""
        self.overall_label.setText(f"Overall: {result.overall} - {result.message}{integrity}")
        self.overall_label.setStyleSheet(f"font-weight: bold; color: {_colour(result.overall)};")
        self.tree.clear()
        for f in result.files:
            top = QTreeWidgetItem([f.filename, f.status, f.reason])
            top.setForeground(1, QColor(_colour(f.status)))
            for key, ok in f.checks.items():
                child = QTreeWidgetItem([entry.CHECK_LABELS.get(key, key), "PASS" if ok else "FAIL", ""])
                child.setForeground(1, QColor(_colour("PASS" if ok else "FAIL")))
                top.addChild(child)
            for err in f.errors:
                top.addChild(QTreeWidgetItem(["Error", "", err]))
            self.tree.addTopLevelItem(top)
            top.setExpanded(True)

    def _finish(self) -> None:
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        self.evidence_button.setEnabled(self.evidence_folder() is not None)

    # ------------------------------------------------------------- evidence
    def evidence_folder(self) -> Path | None:
        return self.result.run_dir if self.result and self.result.run_dir else None

    def open_evidence_folder(self) -> None:
        folder = self.evidence_folder()
        if folder is not None and folder.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(15000)
        super().closeEvent(event)
