"""Maintenance repository ↔ PDM linking dialog.

The Maintenance workflow first loads the published repository and a PDM
product through their normal workflows. This dialog only confirms and persists
that already-loaded relationship, then builds the Maintenance comparison
state.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class MaintenanceRepositoryLinkDialog(QDialog):
    """Confirm and establish the currently loaded Repository ↔ PDM link."""

    def __init__(self, context, parent=None) -> None:
        super().__init__(parent)
        self._context = context

        self.setWindowTitle("Maintenance — Establish Repository Link")
        self.resize(720, 520)

        root = QVBoxLayout(self)
        root.setSpacing(10)

        repository_box = QGroupBox("Loaded Repository", self)
        repository_layout = QVBoxLayout(repository_box)
        self._repository_info = QLabel("-", repository_box)
        self._repository_info.setWordWrap(True)
        repository_layout.addWidget(self._repository_info)
        root.addWidget(repository_box)

        product_box = QGroupBox("Loaded PDM Product", self)
        product_layout = QVBoxLayout(product_box)
        self._product_info = QLabel("-", product_box)
        self._product_info.setWordWrap(True)
        product_layout.addWidget(self._product_info)
        root.addWidget(product_box)

        self._status = QLabel("", self)
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        links_box = QGroupBox("Existing Maintenance Links", self)
        links_layout = QVBoxLayout(links_box)
        self._links = QListWidget(links_box)
        links_layout.addWidget(self._links)
        root.addWidget(links_box, 1)

        self._link_button = QPushButton("Establish Repository Link", self)
        self._link_button.clicked.connect(self._establish_link)
        root.addWidget(self._link_button)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._refresh_loaded_state()
        self._load_existing_links()

    def _refresh_loaded_state(self) -> None:
        repository = self._context.maintenance_repository_info
        pdm_snapshot = self._context.pdm_snapshot
        product = pdm_snapshot.product if pdm_snapshot is not None else None

        if repository is None:
            self._repository_info.setText(
                "No released MDB repository is loaded. Open a Series from "
                "the Repository workspace first."
            )
        else:
            self._repository_info.setText(
                f"Series: {repository.get('name') or '-'}\n"
                f"Program: {repository.get('code') or '-'}\n"
                f"Version: {repository.get('version') or '-'}\n"
                f"Path: {repository.get('path') or '-'}"
            )

        if product is None:
            self._product_info.setText(
                "No PDM product is loaded. Select and load a product from "
                "the Product workflow first."
            )
        else:
            self._product_info.setText(
                f"Product: {product.code or '-'} — {product.name or '-'}\n"
                f"Category: {product.category or '-'}\n"
                f"Catalogue: {product.description or '-'}\n"
                f"Articles loaded: {len(pdm_snapshot.articles):,}"
            )

        ready = repository is not None and product is not None
        self._link_button.setEnabled(ready)
        if not ready:
            self._status.setText(
                "Establish Link requires both the released MDB repository "
                "and a loaded PDM product."
            )
        else:
            self._status.setText(
                "The link will use exactly the repository and PDM product "
                "currently loaded in the Workbench."
            )

    def _establish_link(self) -> None:
        repository = self._context.maintenance_repository_info
        pdm_snapshot = self._context.pdm_snapshot
        product = pdm_snapshot.product if pdm_snapshot is not None else None

        if repository is None or pdm_snapshot is None or product is None:
            self._refresh_loaded_state()
            return

        existing = self._context.maintenance_repository_link_service.get(
            repository["path"]
        )
        if existing:
            pdm = existing.get("pdm", {})
            existing_product = (
                f"{pdm.get('product_code') or '-'} — "
                f"{pdm.get('product_name') or '-'}"
            )
            current_product = f"{product.code or '-'} — {product.name or '-'}"
            if existing_product != current_product:
                answer = QMessageBox.question(
                    self,
                    "Replace Repository Link",
                    f"This repository is already linked to {existing_product}.\n\n"
                    f"Replace it with {current_product}?",
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return

        self._context.maintenance_repository_link_service.establish(
            repository=repository,
            pdm_candidate=product,
        )

        from models.maintenance_snapshot import MaintenanceSnapshot
        from services.maintenance_alignment_service import MaintenanceAlignmentService

        state = MaintenanceSnapshot(
            pdm_snapshot=pdm_snapshot,
            repository_snapshot=self._context.repository_snapshot,
            mdb_snapshot=self._context.mdb_snapshot,
        )
        self._context.register_maintenance_snapshot(state)
        alignment = MaintenanceAlignmentService(self._context).align(state)

        if alignment.is_aligned:
            self._status.setText(
                f"Repository link established. Maintenance alignment is ALIGNED: "
                f"{len(alignment.relations):,} matched, 0 unresolved."
            )
            QMessageBox.information(
                self,
                "Repository Link",
                "Repository link established and Maintenance comparison is ready.",
            )
            self.accept()
        else:
            self._status.setText(
                f"Repository link established, but Maintenance alignment is "
                f"{alignment.status}: {len(alignment.unresolved_article_ids):,} "
                "unresolved article(s). Comparison remains blocked."
            )
            QMessageBox.warning(
                self,
                "Repository Link",
                "The repository link was established, but article alignment "
                "is incomplete. Maintenance comparison remains blocked.",
            )

    def _load_existing_links(self) -> None:
        self._links.clear()
        for connection in self._context.maintenance_repository_link_service.list_connections():
            repo = connection.get("repository", {})
            pdm = connection.get("pdm", {})
            item = QListWidgetItem(
                f"{repo.get('name') or '-'}  →  "
                f"{pdm.get('product_code') or '-'} — "
                f"{pdm.get('product_name') or '-'}"
            )
            item.setToolTip(repo.get("path") or "")
            self._links.addItem(item)
