"""Per-article property-value table (decision D2), in the same model/proxy architecture as the Articles work table.

``ArticleValueModel`` reads and writes an :class:`ArticleValueTable`; row identity is the article number, so sorting
and filtering through the proxy can never attach a value to another article. A value is only ever typed by the user:
nothing is pre-filled or copied from one article to another. The ConfigID column is read-only (the article's existing
prm_key). Missing values, unknown values, missing ConfigIDs and ConfigID conflicts are shown per row.
"""
from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QBrush, QColor

from services.metatype.property_rules import ArticleValueTable

ARTICLE_ROLE = Qt.ItemDataRole.UserRole + 1
HEADERS = ("Article", "ConfigID (prm_key)", "Value", "Status")
_MISSING = QBrush(QColor("#fff3c4"))
_ERROR = QBrush(QColor("#fbd5d5"))
_READONLY = QBrush(QColor("#6b6b6b"))


class ArticleValueModel(QAbstractTableModel):
    edited = Signal()

    def __init__(self, table: ArticleValueTable | None = None, parent=None) -> None:
        super().__init__(parent)
        self._table = table or ArticleValueTable([], [])

    @property
    def table(self) -> ArticleValueTable:
        return self._table

    def reload(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._table.articles)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return HEADERS[section]
        return None

    def status(self, article: str) -> str:
        problems = self._table.article_problems(article)
        if not problems:
            return "OK"
        text = problems[0].split(": ", 1)[-1]
        return text if len(problems) == 1 else f"{text} (+{len(problems) - 1} more)"

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        article = self._table.articles[index.row()]
        column = index.column()
        if role == ARTICLE_ROLE:
            return article
        text = (article, self._table.config_ids.get(article, "").strip(" \t"),
                self._table.assigned.get(article, ""), self.status(article))[column]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return text
        if role == Qt.ItemDataRole.UserRole + 2:
            return text.casefold()
        if role == Qt.ItemDataRole.BackgroundRole:
            if column == 2 and article not in self._table.assigned:
                return _MISSING
            if column in (1, 3) and self._table.article_problems(article) and column == 3:
                return _ERROR
        if role == Qt.ItemDataRole.ForegroundRole and column != 2:
            return _READONLY
        if role == Qt.ItemDataRole.ToolTipRole and column == 3:
            return "\n".join(self._table.article_problems(article)) or "No findings."
        return None

    def flags(self, index):
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return base | Qt.ItemFlag.ItemIsEditable if index.isValid() and index.column() == 2 else base

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid() or index.column() != 2:
            return False
        if not self._table.set_value(self._table.articles[index.row()], str(value)):
            return False
        # a value can create or clear a ConfigID conflict on other rows, so repaint every row
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))
        self.edited.emit()
        return True


class ArticleValueProxy(QSortFilterProxyModel):
    """Text search and a 'problems only' switch; sorts on case-folded text; never re-sorts under the cursor."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._text = ""
        self._problems_only = False
        self.setSortRole(Qt.ItemDataRole.UserRole + 2)
        self.setDynamicSortFilter(False)

    def set_text(self, text: str) -> None:
        self._text = text.strip().casefold()
        self.invalidate()

    def set_problems_only(self, flag: bool) -> None:
        self._problems_only = flag
        self.invalidate()

    def filterAcceptsRow(self, source_row, source_parent) -> bool:
        model: ArticleValueModel = self.sourceModel()
        article = model.table.articles[source_row]
        if self._problems_only and not model.table.article_problems(article):
            return False
        if self._text:
            haystack = " ".join(str(model.data(model.index(source_row, c)) or "") for c in range(model.columnCount()))
            return self._text in haystack.casefold()
        return True
