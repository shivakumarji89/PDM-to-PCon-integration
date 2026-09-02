"""A reusable series picker - check which series an operation should touch.

Given a list of ``(label, path)`` series, shows a checkable list so the user
selects the subset to act on. Used to scope the price roll-over (and any other
repository-wide operation) to chosen series instead of the whole repository.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from ui.components import DialogTemplate


class SeriesSelectDialog(DialogTemplate):
    """Pick which series to include. ``selected_paths`` holds the result."""

    def __init__(self, items, title="Select Series", preselected=None, parent=None) -> None:
        super().__init__(parent)
        self._items = list(items)   # [(label, path)]
        self._preselected = set(preselected or [])
        self.selected_paths: list[str] = []
        self.set_title(title)
        self.setMinimumSize(460, 560)
        self._build_search()
        self._build_table()
        self._build_footer()
        self._populate()

    # -- construction ---------------------------------------------------

    def _build_search(self) -> None:
        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Search series...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)
        self.add_content(self._search)

    def _build_table(self) -> None:
        self._table = QTableWidget(0, 2, self)
        self._table.setHorizontalHeaderLabels(["", "Series"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 28)
        self.add_content(self._table)
        self._count = QLabel(self)
        self.add_content(self._count)

    def _build_footer(self) -> None:
        select_all = QPushButton("Select All", self)
        select_all.clicked.connect(lambda: self._set_all(True))
        clear = QPushButton("Clear", self)
        clear.clicked.connect(lambda: self._set_all(False))
        ok = QPushButton("OK", self)
        ok.clicked.connect(self._on_ok)
        cancel = QPushButton("Cancel", self)
        cancel.clicked.connect(self.reject)
        for btn in (select_all, clear, ok, cancel):
            self.add_footer_button(btn)

    # -- data -----------------------------------------------------------

    def _populate(self) -> None:
        self._table.setRowCount(len(self._items))
        for r, (label, path) in enumerate(self._items):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            preset = not self._preselected or path in self._preselected
            check.setCheckState(Qt.CheckState.Checked if preset else Qt.CheckState.Unchecked)
            self._table.setItem(r, 0, check)
            name = QTableWidgetItem(str(label))
            name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(r, 1, name)
        self._update_count()

    def _set_all(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for r in range(self._table.rowCount()):
            if not self._table.isRowHidden(r):
                self._table.item(r, 0).setCheckState(state)
        self._update_count()

    def _apply_filter(self, *_) -> None:
        query = self._search.text().strip().lower()
        for r in range(self._table.rowCount()):
            self._table.setRowHidden(r, bool(query and query not in self._table.item(r, 1).text().lower()))

    def _update_count(self) -> None:
        checked = sum(1 for r in range(self._table.rowCount())
                      if self._table.item(r, 0).checkState() == Qt.CheckState.Checked)
        self._count.setText(f"{checked} of {len(self._items)} selected")

    def _on_ok(self) -> None:
        self.selected_paths = [
            self._items[r][1] for r in range(self._table.rowCount())
            if self._table.item(r, 0).checkState() == Qt.CheckState.Checked
        ]
        self.accept()
