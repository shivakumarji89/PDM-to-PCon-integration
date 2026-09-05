"""Review workspace for repository ↔ PDM source discovery.

This page is evidence-first: the user selects the correct PDM catalogue before
loading its complete product data into the established engineering workflow.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.pages.base_page import BasePage


class ReviewPage(BasePage):
    """Comparison workspace for repository evidence and PDM catalogues."""

    # Emitted after the selected catalogue has been loaded into the shared
    # Snapshot and engineering data is ready for downstream workflow pages.
    series_loaded = Signal(str)

    # Request the Product page to run the already-established asynchronous family
    # loader. This keeps Review free of duplicate loading/progress logic.
    catalogue_load_requested = Signal(object, str)

    _CATALOGUE_COLUMNS = (
        ("#", 42),
        ("Catalogue", 360),
        ("Lead Time", 100),
        ("Series Found", 110),
        ("Category", 220),
    )

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Review",
            description=(
                "Select the correct PDM catalogue and load its complete data "
                "into the established engineering workflow."
            ),
            parent=parent,
            show_placeholder=False,
        )
        self._context = context

        self.add_content(self._build_toolbar())
        self.add_content(self._build_source_comparison_group())
        self.refresh()

    def _build_toolbar(self) -> QWidget:
        box = QGroupBox("Review Actions", self)
        layout = QHBoxLayout(box)

        self._refresh_btn = QPushButton("Refresh Discovery", box)
        self._refresh_btn.clicked.connect(self._refresh_discovery)
        layout.addWidget(self._refresh_btn)

        self._selection_info = QLabel(
            "Select a PDM catalogue to load its complete product data.",
            box,
        )
        layout.addWidget(self._selection_info)

        self._load_snapshot_btn = QPushButton("Load Selected Catalogue", box)
        self._load_snapshot_btn.setEnabled(False)
        self._load_snapshot_btn.clicked.connect(self._load_selected_catalogue)
        layout.addWidget(self._load_snapshot_btn)

        layout.addStretch(1)
        return box

    def _build_source_comparison_group(self) -> QWidget:
        """Build the structured repository/PDM comparison workspace."""
        box = QGroupBox("Repository ↔ PDM Discovery", self)
        layout = QVBoxLayout(box)

        self._source_status = QLabel(
            "No repository series selected. Open a repository series from Product.",
            box,
        )
        self._source_status.setWordWrap(True)
        layout.addWidget(self._source_status)

        repository_box = QGroupBox("Repository Evidence", box)
        form = QFormLayout(repository_box)
        self._source_rows = {}
        for key, label in (
            ("name", "Name"),
            ("code", "Code"),
            ("category", "Category"),
            ("catalogue", "Catalogue"),
        ):
            value = QLabel("-", repository_box)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._source_rows[key] = value
            form.addRow(f"{label}:", value)
        layout.addWidget(repository_box)

        catalogues_box = QGroupBox(
            "Step 1 — Select PDM Catalogue / Lead Time",
            box,
        )
        catalogues_layout = QVBoxLayout(catalogues_box)
        catalogue_hint = QLabel(
            "Discovery groups matching PDM records by catalogue. Select the correct "
            "catalogue first; lead time is shown as evidence and is not auto-selected.",
            catalogues_box,
        )
        catalogue_hint.setWordWrap(True)
        catalogues_layout.addWidget(catalogue_hint)
        self._catalogue_search = QLineEdit(catalogues_box)
        self._catalogue_search.setPlaceholderText("Search catalogue or lead time...")
        self._catalogue_search.textChanged.connect(self._filter_catalogues)
        catalogues_layout.addWidget(self._catalogue_search)
        self._catalogues = QTableWidget(catalogues_box)
        self._catalogues.setColumnCount(len(self._CATALOGUE_COLUMNS))
        self._catalogues.setHorizontalHeaderLabels([column[0] for column in self._CATALOGUE_COLUMNS])
        for index, (_, width) in enumerate(self._CATALOGUE_COLUMNS):
            self._catalogues.setColumnWidth(index, width)
        self._catalogues.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._catalogues.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._catalogues.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._catalogues.verticalHeader().setVisible(False)
        self._catalogues.itemSelectionChanged.connect(self._on_catalogue_selection_changed)
        self._catalogues.setMinimumHeight(180)
        catalogues_layout.addWidget(self._catalogues)
        layout.addWidget(catalogues_box)


        return box

    @staticmethod
    def _value(product: dict, *keys: str) -> str:
        """Read the first available candidate field without guessing identity."""
        for key in keys:
            value = product.get(key)
            if value not in (None, ""):
                return str(value)
        return "-"

    @staticmethod
    def _candidate_to_product(candidate: dict):
        """Convert discovery evidence back into the existing Product model."""
        from models.product import Product

        return Product(
            id=str(candidate.get("id") or ""),
            code=str(candidate.get("code") or ""),
            name=str(candidate.get("name") or ""),
            category=str(candidate.get("category") or ""),
            description=str(candidate.get("catalogue") or ""),
            catalogue_id=(
                str(candidate.get("catalogue_id"))
                if candidate.get("catalogue_id") is not None
                else None
            ),
            lead_time=candidate.get("lead_time"),
            range_name=str(
                candidate.get("range_name")
                or candidate.get("range")
                or ""
            ),
        )

    def _selected_catalogue_name(self) -> str | None:
        """Return the explicitly selected PDM catalogue."""
        rows = self._catalogues.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._catalogues.item(rows[0].row(), 1)
        return item.text() if item and item.text() else None

    def _selected_catalogue_products(self, catalogue_name: str) -> list:
        """Return the complete PDM product set for the selected catalogue.

        Discovery candidates are only evidence used to identify the catalogue.
        Once the user explicitly selects it, the full PDM registry is used as
        the source boundary so downstream Articles receives every product and
        article belonging to that catalogue.
        """
        context = self._context.repository_context_service.active_context
        discovery_products = context.candidate_products if context else []

        matching_evidence = [
            item for item in discovery_products
            if self._value(item, "catalogue", "catalogue_name") == catalogue_name
        ]
        catalogue_ids = {
            str(item.get("catalogue_id"))
            for item in matching_evidence
            if item.get("catalogue_id") is not None
        }

        # The global registry contains the complete PDM hierarchy. Prefer the
        # stable catalogue ID; fall back to catalogue name only if legacy
        # discovery evidence has no ID.
        registry_products = self._context.pdm_service.get_cached_products()
        if catalogue_ids:
            products = [
                product for product in registry_products
                if product.catalogue_id is not None
                and str(product.catalogue_id) in catalogue_ids
            ]
        else:
            products = [
                product for product in registry_products
                if (product.description or "").strip() == catalogue_name
            ]

        return products

    def _load_selected_catalogue(self) -> None:
        """Hand the selected catalogue to the established Product family loader.

        Review resolves the product boundary; ProductPage owns the actual
        asynchronous load, reusable progress popup, activity reporting and
        engineering/workspace completion flow.
        """
        catalogue_name = self._selected_catalogue_name()
        if not catalogue_name:
            QMessageBox.warning(
                self, "Catalogue Load", "Select a PDM catalogue before loading."
            )
            return

        products = self._selected_catalogue_products(catalogue_name)
        if not products:
            QMessageBox.warning(
                self,
                "Catalogue Load",
                "No valid PDM products were found for the selected catalogue.",
            )
            return

        repository_context = self._context.repository_context_service.active_context
        if repository_context is not None:
            representative = next(
                (
                    item
                    for item in repository_context.candidate_products
                    if self._value(item, "catalogue", "catalogue_name") == catalogue_name
                ),
                None,
            )
            if representative is None:
                representative = dict(
                    (repository_context.established_connection or {}).get("pdm") or {}
                )
                representative["catalogue"] = catalogue_name

            selected_discovery = next(
                (
                    dict(item)
                    for item in repository_context.candidate_catalogues
                    if self._value(item, "catalogue") == catalogue_name
                ),
                {"catalogue": catalogue_name},
            )
            discovery = {
                "status": "recorded",
                "selected_catalogue": catalogue_name,
                "selected": selected_discovery,
                "catalogues": [
                    dict(item)
                    for item in repository_context.candidate_catalogues
                ],
            }
            self._context.repository_connection_service.establish(
                repository_path=repository_context.repository_path,
                repository_name=str(repository_context.records["name"].value or ""),
                repository_code=str(repository_context.records["code"].value or ""),
                repository_category=repository_context.category,
                pdm_candidate=representative,
                engineering_summary={
                    "article_count": None,
                    "article_length": None,
                    "links": [],
                },
                discovery=discovery,
            )

        self._selection_info.setText(
            f"Loading catalogue: {catalogue_name}. Please wait..."
        )
        self._load_snapshot_btn.setEnabled(False)
        self.catalogue_load_requested.emit(products, catalogue_name)

    def _clear_catalogues(self, message: str) -> None:
        self._catalogues.clearContents()
        self._catalogues.setRowCount(1)
        item = QTableWidgetItem(message)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self._catalogues.setItem(0, 0, item)
        self._catalogues.setSpan(0, 0, 1, len(self._CATALOGUE_COLUMNS))

    def _refresh_source_comparison(self) -> None:
        context = self._context.repository_context_service.active_context
        if context is None:
            self._source_status.setText(
                "No repository series selected. Open a repository series from Product."
            )
            for widget in self._source_rows.values():
                widget.setText("-")
            return

        self._source_status.setText(
            f"Repository: {context.repository_path}\n"
            f"PDM discovery status: {context.pdm_match_status.replace('_', ' ')}\n"
            f"{context.records['name'].notes}"
        )

        for key, widget in self._source_rows.items():
            record = context.records.get(key)
            widget.setText(
                str(record.value if record and record.value not in (None, "") else "-")
            )

        catalogues = context.candidate_catalogues or []
        self._catalogues.clearSpans()
        self._catalogues.clearContents()
        if not catalogues:
            self._clear_catalogues("No PDM catalogues found.")
            return

        self._catalogues.setRowCount(len(catalogues))
        for row, catalogue in enumerate(catalogues):
            values = (
                str(row + 1),
                self._value(catalogue, "catalogue"),
                (f"{catalogue.get('lead_time')}-day" if catalogue.get("lead_time") is not None else "-"),
                str(catalogue.get("product_count") or 0),
                ", ".join(catalogue.get("categories") or []) or "-",
            )
            for column, value in enumerate(values):
                self._catalogues.setItem(row, column, QTableWidgetItem(value))
        self._catalogues.resizeRowsToContents()

    def _on_catalogue_selection_changed(self) -> None:
        catalogue = self._selected_catalogue_name()
        if not catalogue:
            self._load_snapshot_btn.setEnabled(False)
            return
        self._selection_info.setText(
            f"Catalogue selected: {catalogue}. Ready to load all catalogue data into Articles."
        )
        self._load_snapshot_btn.setEnabled(True)

    def _filter_catalogues(self, text: str) -> None:
        query = text.casefold().strip()
        for row in range(self._catalogues.rowCount()):
            searchable = " ".join(
                self._catalogues.item(row, column).text()
                if self._catalogues.item(row, column) else ""
                for column in range(self._catalogues.columnCount())
            ).casefold()
            self._catalogues.setRowHidden(row, bool(query and query not in searchable))

    def _refresh_discovery(self) -> None:
        """Run a new PDM discovery only when explicitly requested by the user."""
        self._selection_info.setText("Refreshing PDM discovery...")
        self._load_snapshot_btn.setEnabled(False)
        self._context.repository_context_service.refresh_pdm_discovery()
        self._catalogue_search.clear()
        self._refresh_source_comparison()
        self._selection_info.setText(
            "Fresh PDM discovery loaded. Select a catalogue to load its complete product data."
        )

    def refresh(self) -> None:
        """Refresh the view without reconnecting to PDM."""
        self._selection_info.setText(
            "Select a PDM catalogue to load its complete product data."
        )
        self._load_snapshot_btn.setEnabled(False)
        self._refresh_source_comparison()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def is_ready(self) -> bool:
        return True
