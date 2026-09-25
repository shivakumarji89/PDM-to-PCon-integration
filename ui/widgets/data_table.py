"""Standard table framework for the Engineering Workbench.

One reusable behaviour set applied to every table in the application so all
grids feel like a modern spreadsheet (Excel / Visual Studio data grid):
sorting, movable & resizable columns, show/hide columns, auto-fit, rich copy
(cell / row / with headers), a context menu and Ctrl+C. Presentation only -
no engineering logic.

Use :func:`standardize_table` to upgrade an existing ``QTableWidget`` in place
(without changing the page that built it), or subclass :class:`EngineeringTable`
for new tables.
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import QHeaderView, QMenu, QTableWidget


def standardize_table(table: QTableWidget, *, settings_key: str | None = None) -> None:
    """Apply the standard spreadsheet behaviours to ``table`` in place.

    Columns become user-resizable (drag) and movable, with a one-shot auto-fit
    to contents the first time rows appear so initial widths look right. The
    table's selection mode/behaviour and data chosen by the owning page are
    left untouched.
    """
    if table.property("_ews_standardized"):
        return
    table.setProperty("_ews_standardized", True)

    table.setAlternatingRowColors(True)
    table.setShowGrid(True)
    table.setWordWrap(False)
    table.setSortingEnabled(True)
    table.setCornerButtonEnabled(False)
    table.setTabKeyNavigation(True)

    header = table.horizontalHeader()
    header.setHighlightSections(False)
    header.setSectionsMovable(True)
    header.setStretchLastSection(True)
    # Excel-style: every column is user-resizable by dragging its border.
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    header.customContextMenuRequested.connect(
        lambda pos, t=table: _show_header_menu(t, pos)
    )
    _install_initial_autofit(table)

    table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    table.customContextMenuRequested.connect(
        lambda pos, t=table: _show_cell_menu(t, pos)
    )

    # Ctrl+C copies the current selection with headers (spreadsheet style).
    shortcut = QShortcut(QKeySequence.StandardKey.Copy, table)
    shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    shortcut.activated.connect(lambda t=table: _copy_selection(t, with_headers=True))

    if settings_key:
        _bind_persistence(table, settings_key)


class EngineeringTable(QTableWidget):
    """A ``QTableWidget`` that ships with the standard behaviours built in."""

    def __init__(self, rows: int = 0, columns: int = 0, parent=None,
                 *, settings_key: str | None = None) -> None:
        super().__init__(rows, columns, parent)
        standardize_table(self, settings_key=settings_key)


def _install_initial_autofit(table: QTableWidget) -> None:
    """Fit columns to contents the first time the table has rows, then leave
    them user-resizable (later data updates don't re-fit)."""
    if table.rowCount() > 0:
        table.resizeColumnsToContents()
        return
    model = table.model()

    def _fit(*_) -> None:
        table.resizeColumnsToContents()
        try:
            model.rowsInserted.disconnect(_fit)
        except (RuntimeError, TypeError):
            pass

    model.rowsInserted.connect(_fit)


# -- context menus ---------------------------------------------------------
def _show_cell_menu(table: QTableWidget, pos: QPoint) -> None:
    item = table.itemAt(pos)
    menu = QMenu(table)

    copy = menu.addAction("Copy")
    copy.setEnabled(item is not None)
    copy_row = menu.addAction("Copy Row")
    copy_row.setEnabled(item is not None)
    copy_sel = menu.addAction("Copy Selection with Headers")
    copy_sel.setEnabled(bool(table.selectedItems()))
    menu.addSeparator()
    autofit = menu.addAction("Auto-fit Columns")
    columns_menu = menu.addMenu("Columns")
    _fill_columns_menu(table, columns_menu)

    chosen = menu.exec(table.viewport().mapToGlobal(pos))
    if chosen is None:
        return
    if chosen is copy and item is not None:
        QGuiApplication.clipboard().setText(item.text())
    elif chosen is copy_row and item is not None:
        _copy_row(table, item.row(), with_headers=False)
    elif chosen is copy_sel:
        _copy_selection(table, with_headers=True)
    elif chosen is autofit:
        table.resizeColumnsToContents()


def _show_header_menu(table: QTableWidget, pos: QPoint) -> None:
    menu = QMenu(table)
    autofit = menu.addAction("Auto-fit Columns")
    menu.addSeparator()
    columns_menu = menu.addMenu("Show Columns")
    _fill_columns_menu(table, columns_menu)
    chosen = menu.exec(table.horizontalHeader().mapToGlobal(pos))
    if chosen is autofit:
        table.resizeColumnsToContents()


def _fill_columns_menu(table: QTableWidget, menu: QMenu) -> None:
    for col in range(table.columnCount()):
        header_item = table.horizontalHeaderItem(col)
        title = header_item.text() if header_item else f"Column {col + 1}"
        action = menu.addAction(title)
        action.setCheckable(True)
        action.setChecked(not table.isColumnHidden(col))
        action.toggled.connect(
            lambda visible, c=col, t=table: _set_column_visible(t, c, visible)
        )


def _set_column_visible(table: QTableWidget, column: int, visible: bool) -> None:
    # Never allow every column to be hidden.
    if not visible and _visible_column_count(table) <= 1:
        return
    table.setColumnHidden(column, not visible)


def _visible_column_count(table: QTableWidget) -> int:
    return sum(
        0 if table.isColumnHidden(c) else 1 for c in range(table.columnCount())
    )


# -- copy helpers ----------------------------------------------------------
def _headers(table: QTableWidget) -> list[str]:
    labels = []
    for col in range(table.columnCount()):
        if table.isColumnHidden(col):
            continue
        item = table.horizontalHeaderItem(col)
        labels.append(item.text() if item else "")
    return labels


def _copy_row(table: QTableWidget, row: int, *, with_headers: bool) -> None:
    cells = []
    for col in range(table.columnCount()):
        if table.isColumnHidden(col):
            continue
        item = table.item(row, col)
        cells.append(item.text() if item else "")
    lines = []
    if with_headers:
        lines.append("\t".join(_headers(table)))
    lines.append("\t".join(cells))
    QGuiApplication.clipboard().setText("\n".join(lines))


def _copy_selection(table: QTableWidget, *, with_headers: bool) -> None:
    ranges = table.selectedRanges()
    if not ranges:
        return
    rows = sorted({r for rng in ranges
                   for r in range(rng.topRow(), rng.bottomRow() + 1)})
    cols = sorted({c for rng in ranges
                   for c in range(rng.leftColumn(), rng.rightColumn() + 1)
                   if not table.isColumnHidden(c)})
    if not rows or not cols:
        return
    lines = []
    if with_headers:
        header_cells = []
        for col in cols:
            item = table.horizontalHeaderItem(col)
            header_cells.append(item.text() if item else "")
        lines.append("\t".join(header_cells))
    for row in rows:
        cells = []
        for col in cols:
            item = table.item(row, col)
            cells.append(item.text() if item else "")
        lines.append("\t".join(cells))
    QGuiApplication.clipboard().setText("\n".join(lines))


# -- optional column persistence ------------------------------------------
def _bind_persistence(table: QTableWidget, settings_key: str) -> None:
    from PySide6.QtCore import QSettings

    header = table.horizontalHeader()
    state = QSettings().value(f"tables/{settings_key}")
    if state is not None:
        header.restoreState(state)

    def save() -> None:
        QSettings().setValue(f"tables/{settings_key}", header.saveState())

    header.sectionResized.connect(lambda *_: save())
    header.sectionMoved.connect(lambda *_: save())
