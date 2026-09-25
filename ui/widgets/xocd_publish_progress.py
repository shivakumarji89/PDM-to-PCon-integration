"""Progress dialog for the automated XOCD SVN publish workflow."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
)


class XocdPublishProgress(QDialog):
    """Show the live XOCD publish stages and committed files."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export XOCD")
        self.resize(760, 620)
        self.setModal(False)

        root = QVBoxLayout(self)
        self.stage_label = QLabel("Starting XOCD publish...")
        self.stage_label.setObjectName("pageTitle")
        root.addWidget(self.stage_label)

        self.detail_label = QLabel("")
        self.detail_label.setWordWrap(True)
        root.addWidget(self.detail_label)

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 7)
        self.progress.setValue(0)
        root.addWidget(self.progress)

        self.log = QPlainTextEdit(self)
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1000)
        root.addWidget(self.log, 1)

        self.files_label = QLabel("Committed files")
        self.files_label.setObjectName("pageSubtitle")
        root.addWidget(self.files_label)

        self.files = QListWidget(self)
        root.addWidget(self.files, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.close_button = QPushButton("Close", self)
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.close)
        buttons.addWidget(self.close_button)
        root.addLayout(buttons)

    def set_stage(self, number: int, title: str, detail: str = "") -> None:
        self.progress.setValue(number)
        self.stage_label.setText(title)
        self.detail_label.setText(detail)

    def set_busy(self, busy: bool) -> None:
        self.progress.setRange(0, 0 if busy else 7)
        if not busy:
            self.progress.setValue(min(self.progress.value(), 7))

    def append_output(self, text: str) -> None:
        value = (text or "").replace("\r", "")
        for line in value.split("\n"):
            line = line.rstrip()
            if line:
                self.log.appendPlainText(line)

    def set_files(self, names: list[str]) -> None:
        self.files.clear()
        for name in names:
            self.files.addItem(name)
        self.files_label.setText(f"Committed files ({len(names)})")

    def complete(self, message: str) -> None:
        self.set_busy(False)
        self.progress.setValue(7)
        self.stage_label.setText("XOCD publish completed")
        self.detail_label.setText(message)
        self.close_button.setEnabled(True)

    def fail(self, message: str) -> None:
        self.set_busy(False)
        self.stage_label.setText("XOCD publish stopped")
        self.detail_label.setText(message)
        self.close_button.setEnabled(True)
