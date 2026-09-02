"""Base-length check results - a filterable, editable table.

Shows the base-length check per article with a Status filter and a search box
so a large result set is easy to review, and lets the ``Override_Length`` be
edited in place and saved back to the registry - no spreadsheet needed.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from ui.components import DialogTemplate

_COLS = ["Program", "Item", "Current Base", "CAD Len", "Expected Base", "Override", "Status"]
_STATUS_FILTERS = {"All": None, "Mismatch": "MISMATCH", "No CAD length": "NO_CAD", "OK": "OK"}


class BaseLengthDialog(DialogTemplate):
    """Review + edit the base-length check results."""

    def __init__(self, rows, registry_path, service, parent=None) -> None:
        super().__init__(parent)
        self._rows = rows
        self._registry_path = str(registry_path)
        self._service = service
        self.set_title("Base Length Check")
        self.setMinimumSize(820, 560)
        self._build_filters()
        self._build_table()
        self._build_footer()
        self._populate()
        self._apply_filter()

    # -- construction ---------------------------------------------------

    def _build_filters(self) -> None:
        row = QHBoxLayout()
        mism = sum(1 for r in self._rows if r["Status"] == "MISMATCH")
        row.addWidget(QLabel(f"{len(self._rows)} article(s), {mism} differ from CAD", self))
        row.addStretch(1)
        row.addWidget(QLabel("Status:", self))
        self._status = QComboBox(self)
        self._status.addItems(_STATUS_FILTERS.keys())
        # Default to Mismatch when there are any, so the useful rows show first.
        self._status.setCurrentText("Mismatch" if mism else "All")
        self._status.currentIndexChanged.connect(self._apply_filter)
        row.addWidget(self._status)
        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Search program / item / base...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)
        row.addWidget(self._search, 1)
        self.add_content_layout(row)

    def _build_table(self) -> None:
        self._table = QTableWidget(0, len(_COLS), self)
        self._table.setHorizontalHeaderLabels(_COLS)
        self._table.setSortingEnabled(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Item
        self.add_content(self._table)

    def _build_footer(self) -> None:
        save = QPushButton("Save Overrides", self)
        save.clicked.connect(self._on_save)
        open_csv = QPushButton("Open CSV", self)
        open_csv.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self._registry_path)))
        close = QPushButton("Close", self)
        close.clicked.connect(self.accept)
        for btn in (open_csv, save, close):
            self.add_footer_button(btn)

    # -- data -----------------------------------------------------------

    def _populate(self) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._rows))
        keys = ["Program", "Item", "CurrentBase", "CAD_Length", "Expected_Base",
                "Override_Length", "Status"]
        for r, data in enumerate(self._rows):
            for c, key in enumerate(keys):
                item = QTableWidgetItem(str(data.get(key, "")))
                if c != 5:  # only the Override column is editable
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(r, c, item)
        self._table.setSortingEnabled(True)
        self._table.resizeColumnsToContents()

    def _apply_filter(self, *_) -> None:
        want = _STATUS_FILTERS[self._status.currentText()]
        query = self._search.text().strip().lower()
        for r in range(self._table.rowCount()):
            status = self._table.item(r, 6).text()
            text = " ".join(self._table.item(r, c).text().lower() for c in (0, 1, 2))
            hidden = bool((want is not None and status != want)
                          or (query and query not in text))
            self._table.setRowHidden(r, hidden)

    def _on_save(self) -> None:
        keys = ["Program", "Item", "CurrentBase", "CAD_Length", "Expected_Base",
                "Override_Length", "Status"]
        rows = [
            {key: self._table.item(r, c).text() for c, key in enumerate(keys)}
            for r in range(self._table.rowCount())
        ]
        try:
            self._service.write_base_length_registry(
                self._registry_path, rows, preserve_edits=False)
        except OSError as exc:
            QMessageBox.warning(self, "Base Length Check", f"Could not save:\n{exc}")
            return
        QMessageBox.information(
            self, "Base Length Check",
            f"Saved overrides to:\n{self._registry_path}")
