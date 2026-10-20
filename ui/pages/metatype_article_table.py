"""Interactive Articles work table for the Metatype page (Qt model/view).

``ArticleWorkTableModel`` reads and writes through an :class:`ArticleEditSession`; nothing the user sees is
the only copy of the data. Each row carries its article identity under ``KEY_ROLE`` so the proxy's sorting
and filtering can never attach an edit to another article. Edits only stage values in memory.
"""
from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QBrush, QColor

from models.metatype_articles import ArticleRow
from services.metatype.article_edit_session import ArticleEditSession, RowKey, row_key

KEY_ROLE = Qt.ItemDataRole.UserRole + 1
SORT_ROLE = Qt.ItemDataRole.UserRole + 2
STATUS_HEADER = "Mapping Status"
VALIDATION_HEADER = "Validation"
_MODIFIED = QBrush(QColor("#fff3c4"))
_ERROR = QBrush(QColor("#fbd5d5"))
_READONLY = QBrush(QColor("#6b6b6b"))
_VERDICT = {"ok": "OK", "warning": "Warning", "error": "Error", "unavailable": "Unavailable"}


class ArticleWorkTableModel(QAbstractTableModel):
    edited = Signal()

    def __init__(self, session: ArticleEditSession | None = None, parent=None) -> None:
        super().__init__(parent)
        self._session = session or ArticleEditSession()
        self._keys: list[RowKey] = []
        self._columns: list[str] = []
        self.reload()

    @property
    def session(self) -> ArticleEditSession:
        return self._session

    def reload(self) -> None:
        self.beginResetModel()
        result = self._session.result
        self._columns = list(result.columns) if result else []
        self._keys = [row_key(r) for r in result.rows] if result else []
        self.endResetModel()

    # -- structure --------------------------------------------------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._keys)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else (len(self._columns) + 2 if self._columns else 0)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            names = [*(self._session.column_label(c) for c in self._columns), STATUS_HEADER, VALIDATION_HEADER]
            return names[section] if 0 <= section < len(names) else None
        return None

    def key_for_row(self, row: int) -> RowKey:
        return self._keys[row]

    def column_name(self, column: int) -> str | None:
        return self._columns[column] if 0 <= column < len(self._columns) else None

    def _row(self, key: RowKey) -> ArticleRow | None:
        return self._session._index.get(key)

    # -- data -------------------------------------------------------------------------------------------
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        key = self._keys[index.row()]
        column = self.column_name(index.column())
        if role == KEY_ROLE:
            return key
        row = self._row(key)
        if column is not None:
            text = self._session.value(key, column)
            if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole, SORT_ROLE):
                return text.casefold() if role == SORT_ROLE else text
            if role == Qt.ItemDataRole.BackgroundRole and self._session.is_modified(key, column):
                return _MODIFIED
            if role == Qt.ItemDataRole.ForegroundRole and not self._session.cell_editable(key, column):
                return _READONLY
            if role == Qt.ItemDataRole.ToolTipRole and row is not None:
                return f"{row.source_file}, line {row.source_line}" + "".join(
                    f"\nmapping: {s.table} line {s.line} {s.values}" for s in row.mapping_sources)
            return None
        status_column = index.column() == len(self._columns)
        if role in (Qt.ItemDataRole.DisplayRole, SORT_ROLE):
            if status_column:
                text = row.status if row else ""
                if self._session.is_modified(key):
                    text += " (modified)"
            else:
                text = _VERDICT[self._session.severity(key)]
            return text.casefold() if role == SORT_ROLE else text
        if role == Qt.ItemDataRole.BackgroundRole and not status_column and self._session.severity(key) == "error":
            return _ERROR
        if role == Qt.ItemDataRole.ToolTipRole and not status_column:
            issues = self._session.issues(key)
            return "\n".join(f"{i.severity.upper()} [{i.code}] {i.message}" for i in issues) or "No findings."
        return None

    def flags(self, index):
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        column = self.column_name(index.column())
        if column is not None and self._session.cell_editable(self._keys[index.row()], column):
            return base | Qt.ItemFlag.ItemIsEditable
        return base

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        column = self.column_name(index.column())
        if column is None or not self._session.set_value(self._keys[index.row()], column, str(value)):
            return False
        row = index.row()
        self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))
        self.edited.emit()
        return True

    def discard_row(self, key: RowKey) -> None:
        if self._session.discard(key):
            self.refresh_rows()

    def refresh_rows(self) -> None:
        """Repaint every row after a bulk change (discard / refresh) without resetting selection."""
        if self._keys:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self._keys) - 1, self.columnCount() - 1))
        self.edited.emit()


class ArticleFilterProxy(QSortFilterProxyModel):
    """Text search across all columns plus a status filter; sorts on case-folded values."""

    FILTERS = ("All", "Mapped", "Unmapped", "Modified", "Errors", "Warnings")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._text = ""
        self._mode = "All"
        self.setSortRole(SORT_ROLE)
        self.setDynamicSortFilter(False)   # an edit must not make the row jump away under the cursor

    def set_text(self, text: str) -> None:
        self._text = text.strip().casefold()
        self.invalidate()

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self.invalidate()

    def filterAcceptsRow(self, source_row, source_parent) -> bool:
        model: ArticleWorkTableModel = self.sourceModel()
        key = model.key_for_row(source_row)
        session = model.session
        row = model._row(key)
        if self._mode == "Modified" and not session.is_modified(key):
            return False
        if self._mode == "Errors" and session.severity(key) != "error":
            return False
        if self._mode == "Warnings" and session.severity(key) != "warning":
            return False
        if self._mode in ("Mapped", "Unmapped") and row is not None:
            mapped = session._is_mapped(row)
            if mapped != (self._mode == "Mapped"):
                return False
        if self._text:
            haystack = " ".join(str(model.data(model.index(source_row, c)) or "")
                                for c in range(model.columnCount())).casefold()
            return self._text in haystack
        return True
