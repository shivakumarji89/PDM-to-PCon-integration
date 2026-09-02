"""Text workspace page.

A snapshot-driven workbench for authoring the product's OCD text blocks
(``tCOMd_Text``). Rows are derived once from the active snapshot's articles,
properties and values, then edited in-place across the four OCD languages. All
data lives on the in-memory snapshot; no database queries.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from core.engines.filtering import text_match
from models.text_block import TEXT_TYPE_CODES, TextBlock
from services.engineering.engineering_text_service import LANGUAGES
from ui import theme
from ui.pages.base_page import BasePage

_COL_TYPE = 0
_COL_NAME = 1
_COL_DE = 2
_COL_EN = 3
_COL_FR = 4
_COL_NL = 5

_FILTER_ALL = "All types"
_GROUP_NONE = "No grouping"
_GROUP_TYPE = "Group by type"


class TextPage(BasePage):
    """Engineering workspace for the active snapshot's text blocks."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Text",
            description="Author localized text blocks for articles, properties and values.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._all_blocks: list[TextBlock] = []
        self._row_blocks: list[TextBlock] = []
        self._populating = False

        # Debounce search typing so the table rebuilds once the user pauses.
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(200)
        self._filter_timer.timeout.connect(self._apply_filter)

        self.add_content(self._build_toolbar())
        self.add_content(self._build_table())
        self.refresh()

    # -- construction ------------------------------------------------------
    def _build_toolbar(self) -> QWidget:
        box = QGroupBox("Toolbar", self)
        layout = QHBoxLayout(box)
        self._search = QLineEdit(box)
        self._search.setPlaceholderText("Search text name or content...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._schedule_filter)
        layout.addWidget(self._search, 1)

        layout.addWidget(QLabel("Type:", box))
        self._filter = QComboBox(box)
        self._filter.addItem(_FILTER_ALL)
        self._filter.addItems(list(TEXT_TYPE_CODES))
        self._filter.currentIndexChanged.connect(self._apply_filter)
        layout.addWidget(self._filter)

        layout.addWidget(QLabel("Group:", box))
        self._group = QComboBox(box)
        self._group.addItems([_GROUP_NONE, _GROUP_TYPE])
        self._group.currentIndexChanged.connect(self._apply_filter)
        layout.addWidget(self._group)

        self._fill_btn = QPushButton("Fill from EN", box)
        self._fill_btn.setToolTip("Copy English into empty German/French/Dutch cells (shown rows).")
        self._fill_btn.clicked.connect(self._on_fill_from_en)
        layout.addWidget(self._fill_btn)

        self._rebuild_btn = QPushButton("Rebuild", box)
        self._rebuild_btn.setToolTip("Re-derive text blocks from the snapshot (discards edits).")
        self._rebuild_btn.clicked.connect(self._on_rebuild)
        layout.addWidget(self._rebuild_btn)
        return box

    def _build_table(self) -> QWidget:
        self._table = QTableWidget(0, 6, self)
        self._table.setObjectName("textTable")
        self._table.setHorizontalHeaderLabels(
            ["Type", "Text Name", "German", "English", "French", "Dutch"]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(28)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self._table.setSortingEnabled(True)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(_COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.ResizeToContents)
        for col in (_COL_DE, _COL_EN, _COL_FR, _COL_NL):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        self._table.itemChanged.connect(self._on_item_changed)
        return self._table

    # -- data --------------------------------------------------------------
    def refresh(self) -> None:
        snapshot = self._context.active_snapshot
        self._all_blocks = self._context.engineering_text_service.ensure_text_blocks(
            snapshot
        )
        self._apply_filter()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # Reload from the snapshot whenever the page is shown, matching every
        # other data page so navigating in always reflects the current product.
        super().showEvent(event)
        self.refresh()

    def _schedule_filter(self) -> None:
        """Debounce search typing so the table rebuilds once, not per keystroke."""
        self._filter_timer.start()

    def _apply_filter(self) -> None:
        query = self._search.text().strip()
        type_filter = self._filter.currentText()
        rows = [
            b
            for b in self._all_blocks
            if (type_filter == _FILTER_ALL or b.type_code == type_filter)
            and (
                not query
                or text_match(query, b.name, b.en, b.de, b.fr, b.nl)
            )
        ]
        # Option values rarely change - keep them at the bottom, out of the way
        # (stable: everything else keeps its order).
        rows.sort(key=lambda b: b.type_code == "optionvalue")
        self._populate(self._grouped(rows))

    def _grouped(self, rows: list[TextBlock]) -> list:
        """Return the rows, optionally sectioned by ('__header__', type) rows."""
        if self._group.currentText() != _GROUP_TYPE:
            return list(rows)
        order = {code: i for i, code in enumerate(TEXT_TYPE_CODES)}
        bottom = len(order) + 1  # option values rarely change -> keep last

        def key(block: TextBlock):
            rank = bottom if block.type_code == "optionvalue" else order.get(
                block.type_code, bottom - 1
            )
            return (rank, block.name)

        items: list = []
        last = object()
        for block in sorted(rows, key=key):
            if block.type_code != last:
                items.append(("__header__", block.type_code))
                last = block.type_code
            items.append(block)
        return items

    def _populate(self, items: list) -> None:
        self._populating = True
        grouped = any(isinstance(e, tuple) for e in items)
        self._table.setSortingEnabled(False)
        self._table.clearSpans()
        self._table.setRowCount(0)
        self._row_blocks = []
        untranslated = self._context.engineering_text_service.is_untranslated
        for entry in items:
            row = self._table.rowCount()
            self._table.insertRow(row)
            if isinstance(entry, tuple):
                header = QTableWidgetItem(str(entry[1]))
                font = header.font()
                font.setBold(True)
                header.setFont(font)
                header.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self._table.setItem(row, 0, header)
                self._table.setSpan(row, 0, 1, 6)
                self._row_blocks.append(None)
                continue
            block = entry
            type_item = QTableWidgetItem(block.type_code)
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item = QTableWidgetItem(block.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if untranslated(block):
                name_item.setForeground(QBrush(QColor(theme.COLOR_WARNING)))
                name_item.setToolTip("Untranslated (a language is empty).")
            self._table.setItem(row, _COL_TYPE, type_item)
            self._table.setItem(row, _COL_NAME, name_item)
            self._table.setItem(row, _COL_DE, QTableWidgetItem(block.de))
            self._table.setItem(row, _COL_EN, QTableWidgetItem(block.en))
            self._table.setItem(row, _COL_FR, QTableWidgetItem(block.fr))
            self._table.setItem(row, _COL_NL, QTableWidgetItem(block.nl))
            self._row_blocks.append(block)
        # Default to the curated order (option values at the bottom); a header
        # click can still sort. Clearing the indicator keeps insertion order.
        self._table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self._table.setSortingEnabled(not grouped)
        self._populating = False

    # -- editing -----------------------------------------------------------
    _LANG_COLUMNS = {_COL_DE: "de", _COL_EN: "en", _COL_FR: "fr", _COL_NL: "nl"}

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._populating:
            return
        language = self._LANG_COLUMNS.get(item.column())
        if language is None or language not in LANGUAGES:
            return
        row = item.row()
        if not (0 <= row < len(self._row_blocks)):
            return
        block = self._row_blocks[row]
        if block is None:
            return
        if self._context.engineering_text_service.set_language(
            block, language, item.text()
        ):
            self._context.snapshot_manager.mark_modified()

    def _on_fill_from_en(self) -> None:
        shown = [b for b in self._row_blocks if b is not None]
        if self._context.engineering_text_service.fill_empty_from_en(shown):
            self._context.snapshot_manager.mark_modified()
            self._apply_filter()

    def _on_rebuild(self) -> None:
        self._context.engineering_text_service.rebuild_text_blocks(
            self._context.active_snapshot
        )
        self._context.snapshot_manager.mark_modified()
        self.refresh()
