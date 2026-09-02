"""Clarify how special-case (underscore) article codes map to a PDM base item.

Some OCD article codes carry a non-standard ``_`` suffix (e.g. ``AZAUS_NE``) and
so have no direct PDM item - the roll would carry their old price. This dialog
lists those articles with a suggested base item (the part before the ``_``) plus
a live PDM price preview, and lets the user confirm/correct which base to price
from. The confirmed ``{article: base}`` map is returned in :attr:`mapping`.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from ui.components import DialogTemplate


class SpecialArticleDialog(DialogTemplate):
    """Confirm special-case article -> PDM base mappings. ``mapping`` = result."""

    def __init__(self, records, parent=None) -> None:
        super().__init__(parent)
        self._records = list(records)
        self.mapping: dict[str, str] = {}
        self.set_title("Special-case articles - confirm price base")
        self.setMinimumSize(680, 520)
        self._build_intro()
        self._build_table()
        self._build_footer()
        self._populate()

    # -- construction ---------------------------------------------------

    def _build_intro(self) -> None:
        intro = QLabel(
            "These article codes use an underscore and have no direct PDM item, "
            "so their price can't update on their own. Tick the ones that should "
            "price from the base item below (edit the base if needed). Unticked "
            "rows keep their current value.", self)
        intro.setWordWrap(True)
        self.add_content(intro)

    def _build_table(self) -> None:
        self._table = QTableWidget(0, 6, self)
        self._table.setHorizontalHeaderLabels(
            ["Use", "Article", "Package", "Price base (PDM item)", "EUR", "GBP"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 40)
        self._table.setColumnWidth(1, 130)
        self._table.setColumnWidth(2, 120)
        self._table.setColumnWidth(4, 70)
        self._table.setColumnWidth(5, 70)
        self.add_content(self._table)
        self._count = QLabel(self)
        self.add_content(self._count)

    def _build_footer(self) -> None:
        use_all = QPushButton("Use base for all", self)
        use_all.clicked.connect(lambda: self._set_all(True))
        clear = QPushButton("Clear all", self)
        clear.clicked.connect(lambda: self._set_all(False))
        ok = QPushButton("OK", self)
        ok.clicked.connect(self._on_ok)
        cancel = QPushButton("Cancel", self)
        cancel.clicked.connect(self.reject)
        for btn in (use_all, clear, ok, cancel):
            self.add_footer_button(btn)

    # -- data -----------------------------------------------------------

    @staticmethod
    def _money(val) -> str:
        return "-" if val is None else f"{float(val):.0f}"

    def _populate(self) -> None:
        self._table.setRowCount(len(self._records))
        for r, rec in enumerate(self._records):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check.setCheckState(
                Qt.CheckState.Checked if rec.get("suggested") else Qt.CheckState.Unchecked)
            self._table.setItem(r, 0, check)

            article = QTableWidgetItem(str(rec.get("article", "")))
            article.setFlags(article.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(r, 1, article)

            pkg = QTableWidgetItem(str(rec.get("package", "")))
            pkg.setFlags(pkg.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(r, 2, pkg)

            base = QTableWidgetItem(str(rec.get("base", "")))  # editable
            self._table.setItem(r, 3, base)

            prices = rec.get("base_prices", {})
            for col, cur in ((4, "EUR"), (5, "GBP")):
                cell = QTableWidgetItem(self._money(prices.get(cur)))
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._table.setItem(r, col, cell)
        self._table.itemChanged.connect(lambda *_: self._update_count())
        self._update_count()

    def _set_all(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for r in range(self._table.rowCount()):
            self._table.item(r, 0).setCheckState(state)
        self._update_count()

    def _update_count(self) -> None:
        checked = sum(1 for r in range(self._table.rowCount())
                      if self._table.item(r, 0).checkState() == Qt.CheckState.Checked)
        self._count.setText(f"{checked} of {len(self._records)} will price from base")

    def _on_ok(self) -> None:
        mapping: dict[str, str] = {}
        for r in range(self._table.rowCount()):
            if self._table.item(r, 0).checkState() != Qt.CheckState.Checked:
                continue
            article = self._table.item(r, 1).text().strip()
            base = self._table.item(r, 3).text().strip()
            if article and base:
                mapping[article] = base
        self.mapping = mapping
        self.accept()
