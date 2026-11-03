"""Virtual table model for generated SKUs.

The generator can produce hundreds of thousands of SKUs. Creating a ``QTableWidgetItem`` per cell on the GUI
thread (the previous ``QTableWidget`` fill) takes minutes and freezes the window, so the view reads the
generator's own list lazily: publishing a result set is O(1) and only the visible rows are ever formatted.
"""
from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

HEADERS = ("#", "Base Article", "Final Article", "Variant Code", "Configuration", "Price", "Status")


class SkuResultsModel(QAbstractTableModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._skus: Sequence = ()

    def set_results(self, skus: Sequence) -> None:
        """Replace the rows. ``skus`` is kept by reference, not copied."""
        self.beginResetModel()
        self._skus = skus
        self.endResetModel()

    def clear(self) -> None:
        self.set_results(())

    def sku_at(self, row: int):
        return self._skus[row] if 0 <= row < len(self._skus) else None

    def text(self, row: int, column: int) -> str:
        sku = self._skus[row]
        if column == 0:
            return str(sku.index)
        if column == 1:
            return sku.base_article
        if column == 2:
            return sku.final_article
        if column == 3:
            return sku.variant_code or "—"
        if column == 4:
            return sku.configuration_text
        if column == 5:
            return f"{sku.price:.2f} {sku.currency}" if sku.price is not None else ""
        return sku.status if not sku.message else f"{sku.status}: {sku.message}"

    # ------------------------------------------------------------ Qt interface
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._skus)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return HEADERS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._skus):
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return self.text(index.row(), index.column())
        if role == Qt.ItemDataRole.ToolTipRole:
            sku = self._skus[index.row()]
            return sku.ofml_varcode if index.column() == 4 else self.text(index.row(), index.column())
        return None
