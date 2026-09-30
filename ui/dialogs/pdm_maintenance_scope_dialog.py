"""PDM scope selection for the Maintenance repository workflow."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

from models.product import Product


class PdmMaintenanceScopeDialog(QDialog):
    """Select one PDM Series -> Category -> Catalog scope for Maintenance."""

    def __init__(self, products: list[Product], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select PDM Maintenance Scope")
        self.resize(560, 300)
        self._products = list(products)
        self._selected_products: list[Product] = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Select the PDM scope to load into the Maintenance snapshot. "
            "The selection is applied only after the MDB repository has finished loading.",
            self,
        ))

        form = QFormLayout()
        self._series = QComboBox(self)
        self._category = QComboBox(self)
        self._catalog = QComboBox(self)
        self._series.currentIndexChanged.connect(self._refresh_categories)
        self._category.currentIndexChanged.connect(self._refresh_catalogs)
        self._catalog.currentIndexChanged.connect(self._update_summary)
        form.addRow("PDM Series:", self._series)
        form.addRow("Category:", self._category)
        form.addRow("Catalog:", self._catalog)
        layout.addLayout(form)

        self._summary = QLabel("", self)
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        layout.addWidget(buttons)

        self._populate_series()

    @property
    def selected_products(self) -> list[Product]:
        return list(self._selected_products)

    @staticmethod
    def _text(value: str | None, fallback: str) -> str:
        value = (value or "").strip()
        return value or fallback

    def _populate_series(self) -> None:
        series = sorted({
            self._text(p.range_name, "(Unassigned Series)")
            for p in self._products
        }, key=str.casefold)
        self._series.clear()
        self._series.addItems(series)
        self._refresh_categories()

    def _series_products(self) -> list[Product]:
        selected = self._series.currentText()
        return [
            p for p in self._products
            if self._text(p.range_name, "(Unassigned Series)") == selected
        ]

    def _refresh_categories(self) -> None:
        categories = sorted({
            self._text(p.category, "(Unassigned Category)")
            for p in self._series_products()
        }, key=str.casefold)
        self._category.blockSignals(True)
        self._category.clear()
        self._category.addItems(categories)
        self._category.blockSignals(False)
        self._refresh_catalogs()

    def _category_products(self) -> list[Product]:
        selected = self._category.currentText()
        return [
            p for p in self._series_products()
            if self._text(p.category, "(Unassigned Category)") == selected
        ]

    def _refresh_catalogs(self) -> None:
        catalogs = sorted({
            self._text(p.description, "(Unassigned Catalog)")
            for p in self._category_products()
        }, key=str.casefold)
        self._catalog.blockSignals(True)
        self._catalog.clear()
        self._catalog.addItems(catalogs)
        self._catalog.blockSignals(False)
        self._update_summary()

    def _selected_scope_products(self) -> list[Product]:
        selected = self._catalog.currentText()
        products = [
            p for p in self._category_products()
            if self._text(p.description, "(Unassigned Catalog)") == selected
        ]
        # A product may occur in more than one catalogue/category row. The
        # selected catalogue instance is authoritative for option gating.
        unique: dict[str, Product] = {}
        for product in products:
            if product.id:
                unique.setdefault(str(product.id), product)
        return list(unique.values())

    def _update_summary(self) -> None:
        products = self._selected_scope_products()
        self._summary.setText(
            f"{len(products):,} PDM product(s) will be loaded into the Maintenance snapshot."
            if products else
            "No PDM products are available for this scope."
        )
        self._ok_button.setEnabled(bool(products))

    def _accept_selection(self) -> None:
        products = self._selected_scope_products()
        if not products:
            return
        self._selected_products = products
        self.accept()
