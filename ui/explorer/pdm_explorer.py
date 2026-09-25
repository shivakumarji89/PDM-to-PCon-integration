"""Right panel PDM explorer.

Reflects the currently loaded product as a live reference view: a compact
"Active Product" identity panel and a tree of the loaded snapshot's structure
(properties, options, articles). The search box filters that loaded structure
in memory - product searching itself lives on the Product page, so this panel
does not duplicate it. Contains no SQL.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class PdmExplorer(QWidget):
    """Active-product reference panel bound to the application context."""

    def __init__(self, context=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pdmExplorer")
        self._context = context

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QLabel("PDM Explorer", self)
        header.setObjectName("panelHeader")
        layout.addWidget(header)

        self._search = QLineEdit(self)
        self._search.setObjectName("pdmSearch")
        self._search.setPlaceholderText("Filter loaded structure...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter_tree)
        layout.addWidget(self._search)

        self._tree = QTreeWidget(self)
        self._tree.setObjectName("pdmTree")
        self._tree.setHeaderLabel("Loaded Product")
        layout.addWidget(self._tree, 1)

        layout.addWidget(self._build_info_panel())
        self.refresh()

    def _build_info_panel(self) -> QWidget:
        box = QGroupBox("Active Product", self)
        box.setObjectName("productInfoPanel")
        form = QFormLayout(box)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)

        self._info_code = QLabel("-", box)
        self._info_name = QLabel("-", box)
        self._info_category = QLabel("-", box)
        self._info_catalogue = QLabel("-", box)
        self._info_status = QLabel("-", box)
        self._info_snapshot = QLabel("-", box)
        for w in (self._info_name, self._info_category, self._info_catalogue):
            w.setWordWrap(True)

        form.addRow("Code:", self._info_code)
        form.addRow("Name:", self._info_name)
        form.addRow("Category:", self._info_category)
        form.addRow("Catalogue:", self._info_catalogue)
        form.addRow("Status:", self._info_status)
        form.addRow("Snapshot:", self._info_snapshot)
        return box

    # -- refresh -----------------------------------------------------------
    def refresh(self) -> None:
        """Rebuild the panel from the active snapshot in the context."""
        snapshot = self._context.active_snapshot if self._context else None
        product = snapshot.product if snapshot else None

        if product is None:
            self._info_code.setText("-")
            self._info_name.setText("No product loaded")
            self._info_category.setText("-")
            self._info_catalogue.setText("-")
            self._info_status.setText("-")
            self._info_snapshot.setText("Not created")
        else:
            self._info_code.setText(product.code or "-")
            self._info_name.setText(product.name or "-")
            self._info_category.setText(product.category or "-")
            self._info_catalogue.setText(product.description or "-")
            self._info_status.setText(product.status or "-")
            self._info_snapshot.setText(self._context.snapshot_manager.status.value)

        self._populate_tree(snapshot)

    def _populate_tree(self, snapshot) -> None:
        self._tree.clear()
        if snapshot is None or snapshot.product is None:
            hint = QTreeWidgetItem(self._tree, ["Load a product on the Product page"])
            hint.setDisabled(True)
            return

        groups = (
            ("Properties", snapshot.properties, lambda p: p.name),
            ("Options", snapshot.options, lambda o: o.name),
            ("Articles", snapshot.articles, lambda a: a.code),
        )
        for title, items, label in groups:
            parent = QTreeWidgetItem(self._tree, [f"{title} ({len(items)})"])
            for item in items:
                QTreeWidgetItem(parent, [label(item) or "-"])
            parent.setExpanded(False)

    def _filter_tree(self, text: str) -> None:
        term = (text or "").strip().lower()
        for i in range(self._tree.topLevelItemCount()):
            parent = self._tree.topLevelItem(i)
            any_visible = False
            for j in range(parent.childCount()):
                child = parent.child(j)
                match = term in child.text(0).lower() if term else True
                child.setHidden(not match)
                any_visible = any_visible or match
            parent.setHidden(bool(term) and not any_visible)
            if term and any_visible:
                parent.setExpanded(True)
