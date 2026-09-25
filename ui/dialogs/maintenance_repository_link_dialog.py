"""Maintenance repository ↔ PDM linking dialog.

This dialog is intentionally isolated from the Development Product page.
It establishes or reopens a persistent relationship for an existing published
series.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class MaintenanceRepositoryLinkDialog(QDialog):
    """Establish a Maintenance repository ↔ PDM product relationship."""

    def __init__(self, context, parent=None) -> None:
        super().__init__(parent)
        self._context = context
        self._repository: dict | None = None
        self._products: list = []

        self.setWindowTitle("Maintenance — Repository Link")
        self.resize(760, 620)

        root = QVBoxLayout(self)
        root.setSpacing(10)

        repository_box = QGroupBox("Repository", self)
        repository_layout = QVBoxLayout(repository_box)

        path_row = QHBoxLayout()
        self._path_label = QLabel("Not selected", repository_box)
        self._path_label.setWordWrap(True)
        self._browse = QPushButton("Browse...", repository_box)
        self._browse.clicked.connect(self._browse_repository)
        path_row.addWidget(self._path_label, 1)
        path_row.addWidget(self._browse)
        repository_layout.addLayout(path_row)

        self._repository_info = QLabel(
            "Select a published series folder containing pcr_data_com_ocd.mdb.",
            repository_box,
        )
        self._repository_info.setWordWrap(True)
        repository_layout.addWidget(self._repository_info)
        root.addWidget(repository_box)

        product_box = QGroupBox("PDM Product", self)
        product_layout = QVBoxLayout(product_box)

        search_row = QHBoxLayout()
        self._search = QLineEdit(product_box)
        self._search.setPlaceholderText("Search by product name, code or article...")
        self._search.returnPressed.connect(self._search_products)
        self._search_button = QPushButton("Search", product_box)
        self._search_button.clicked.connect(self._search_products)
        search_row.addWidget(self._search, 1)
        search_row.addWidget(self._search_button)
        product_layout.addLayout(search_row)

        self._results = QListWidget(product_box)
        self._results.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        product_layout.addWidget(self._results, 1)

        self._selected_product = QLabel("No PDM product selected.", product_box)
        self._selected_product.setWordWrap(True)
        self._results.itemSelectionChanged.connect(self._show_selected_product)
        product_layout.addWidget(self._selected_product)
        root.addWidget(product_box, 1)

        links_box = QGroupBox("Existing Maintenance Links", self)
        links_layout = QVBoxLayout(links_box)
        self._links = QListWidget(links_box)
        self._links.itemDoubleClicked.connect(self._use_existing_link)
        links_layout.addWidget(self._links)
        root.addWidget(links_box, 1)

        self._link_button = QPushButton("Establish Repository Link", self)
        self._link_button.setEnabled(False)
        self._link_button.clicked.connect(self._establish_link)
        root.addWidget(self._link_button)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._load_existing_links()

    def _browse_repository(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Select Published Series Repository"
        )
        if not directory:
            return
        try:
            repository = self._context.maintenance_repository_link_service.inspect_repository(
                directory
            )
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Repository", str(error))
            return

        self._repository = repository
        self._path_label.setText(repository["path"])
        version = repository.get("version") or "unknown"
        self._repository_info.setText(
            f"Series: {repository['name']}   "
            f"Program: {repository['code']}   Version: {version}"
        )
        self._update_link_enabled()

        existing = self._context.maintenance_repository_link_service.get(
            repository["path"]
        )
        if existing:
            pdm = existing.get("pdm", {})
            self._selected_product.setText(
                f"Existing link: {pdm.get('product_code') or '-'} — "
                f"{pdm.get('product_name') or '-'}"
            )

    def _search_products(self) -> None:
        text = self._search.text().strip()
        if not text:
            self._results.clear()
            return

        self._search_button.setEnabled(False)
        self._results.clear()
        try:
            products = self._context.pdm_service.search_products(text, 50)
            if len(text) >= 3 and len(products) < 50:
                seen = {str(p.id) for p in products}
                for product in self._context.pdm_service.search_products_by_article(text, 50):
                    if str(product.id) not in seen:
                        seen.add(str(product.id))
                        products.append(product)
                        if len(products) >= 50:
                            break
            self._products = products[:50]
            for product in self._products:
                item = QListWidgetItem(
                    f"{product.code} — {product.name} "
                    f"[{product.category or '-'}]"
                )
                item.setData(Qt.ItemDataRole.UserRole, product)
                self._results.addItem(item)
            if not self._products:
                self._selected_product.setText("No matching PDM products.")
        except Exception as error:
            QMessageBox.warning(self, "PDM Search", str(error))
        finally:
            self._search_button.setEnabled(True)
            self._update_link_enabled()

    def _show_selected_product(self) -> None:
        item = self._results.currentItem()
        product = item.data(Qt.ItemDataRole.UserRole) if item else None
        if product is None:
            self._selected_product.setText("No PDM product selected.")
        else:
            self._selected_product.setText(
                f"Selected: {product.code} — {product.name} | "
                f"Category: {product.category or '-'} | "
                f"Catalogue: {product.description or '-'}"
            )
        self._update_link_enabled()

    def _update_link_enabled(self) -> None:
        self._link_button.setEnabled(
            self._repository is not None and self._results.currentItem() is not None
        )

    def _establish_link(self) -> None:
        if self._repository is None:
            return
        item = self._results.currentItem()
        product = item.data(Qt.ItemDataRole.UserRole) if item else None
        if product is None:
            return

        existing = self._context.maintenance_repository_link_service.get(
            self._repository["path"]
        )
        if existing:
            answer = QMessageBox.question(
                self,
                "Replace Repository Link",
                "This repository already has an established PDM link. Replace it?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self._context.maintenance_repository_link_service.establish(
            repository=self._repository,
            pdm_candidate=product,
        )
        self._load_existing_links()
        self._repository_info.setText(
            f"Linked to {product.code} — {product.name}. "
            "The relationship is stored for Maintenance."
        )
        QMessageBox.information(self, "Repository Link", "Repository link established.")

    def _load_existing_links(self) -> None:
        self._links.clear()
        for connection in self._context.maintenance_repository_link_service.list_connections():
            repo = connection.get("repository", {})
            pdm = connection.get("pdm", {})
            item = QListWidgetItem(
                f"{repo.get('name') or '-'}  →  "
                f"{pdm.get('product_code') or '-'} — {pdm.get('product_name') or '-'}"
            )
            item.setToolTip(repo.get("path") or "")
            item.setData(Qt.ItemDataRole.UserRole, connection)
            self._links.addItem(item)

    def _use_existing_link(self, item: QListWidgetItem) -> None:
        connection = item.data(Qt.ItemDataRole.UserRole) or {}
        repo = connection.get("repository", {})
        path = repo.get("path", "")
        if not path:
            return
        try:
            self._repository = self._context.maintenance_repository_link_service.inspect_repository(path)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Repository", str(error))
            return
        self._context.maintenance_repository_link_service.touch(path)
        pdm = connection.get("pdm", {})
        self._path_label.setText(path)
        self._repository_info.setText(
            f"Existing link: {pdm.get('product_code') or '-'} — "
            f"{pdm.get('product_name') or '-'}"
        )
        self._selected_product.setText(
            f"Existing PDM link: {pdm.get('product_code') or '-'} — "
            f"{pdm.get('product_name') or '-'}"
        )
        self._update_link_enabled()
