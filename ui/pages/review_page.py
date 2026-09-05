"""Review workspace for repository ↔ PDM source discovery.

This page is evidence-first: it compares a selected repository series with the
PDM records discovered for it, without asserting an automatic relationship.
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
    """Comparison workspace for repository evidence and PDM candidates."""

    # Emitted only after a selected PDM series has been loaded into the shared
    # Snapshot and engineering data is ready for downstream workflow pages.
    series_loaded = Signal(str)

    _CATALOGUE_COLUMNS = (
        ("#", 42),
        ("Catalogue", 360),
        ("Lead Time", 100),
        ("Series Found", 110),
        ("Category", 220),
    )

    _COLUMNS = (
        ("#", 42),
        ("Product Name", 280),
        ("Product Code", 170),
        ("Category", 120),
        ("Range", 220),
        ("Catalogue", 180),
        ("Lead Time", 90),
        ("Status", 110),
    )

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Review",
            description=(
                "Compare repository evidence with PDM candidates. "
                "Candidates are discovery results and are not auto-mapped."
            ),
            parent=parent,
            show_placeholder=False,
        )
        self._context = context
        self._visible_candidates: list[dict] = []

        self.add_content(self._build_toolbar())
        self.add_content(self._build_source_comparison_group())
        self.refresh()

    def _build_toolbar(self) -> QWidget:
        box = QGroupBox("Review Actions", self)
        layout = QHBoxLayout(box)

        self._refresh_btn = QPushButton("Refresh Discovery", box)
        self._refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(self._refresh_btn)

        self._selection_info = QLabel(
            "Select a candidate to inspect its relationship with the repository.",
            box,
        )
        layout.addWidget(self._selection_info)

        self._load_snapshot_btn = QPushButton("Start Work & Establish Connection", box)
        self._load_snapshot_btn.setEnabled(False)
        self._load_snapshot_btn.clicked.connect(self._load_selected_candidate)
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

        candidates_box = QGroupBox(
            "Step 2 — Select PDM Series",
            box,
        )
        candidates_layout = QVBoxLayout(candidates_box)

        hint = QLabel(
            "After selecting a catalogue, only the PDM series belonging to that "
            "catalogue are shown below. Select the series to establish the connection.",
            candidates_box,
        )
        hint.setWordWrap(True)
        candidates_layout.addWidget(hint)

        self._candidate_search = QLineEdit(candidates_box)
        self._candidate_search.setPlaceholderText(
            "Search series by product name, code or category..."
        )
        self._candidate_search.textChanged.connect(self._filter_candidates)
        candidates_layout.addWidget(self._candidate_search)

        self._pdm_candidates = QTableWidget(candidates_box)
        self._pdm_candidates.setColumnCount(len(self._COLUMNS))
        self._pdm_candidates.setHorizontalHeaderLabels(
            [column[0] for column in self._COLUMNS]
        )
        for index, (_, width) in enumerate(self._COLUMNS):
            self._pdm_candidates.setColumnWidth(index, width)

        self._pdm_candidates.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._pdm_candidates.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._pdm_candidates.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._pdm_candidates.verticalHeader().setVisible(False)
        self._pdm_candidates.setAlternatingRowColors(True)
        self._pdm_candidates.itemSelectionChanged.connect(
            self._on_candidate_selection_changed
        )
        self._pdm_candidates.setMinimumHeight(240)
        candidates_layout.addWidget(self._pdm_candidates)

        layout.addWidget(candidates_box)
        return box

    @staticmethod
    def _value(product: dict, *keys: str) -> str:
        """Read the first available candidate field without guessing identity."""
        for key in keys:
            value = product.get(key)
            if value not in (None, ""):
                return str(value)
        return "-"

    def _on_candidate_selection_changed(self) -> None:
        rows = self._pdm_candidates.selectionModel().selectedRows()
        if not rows:
            self._selection_info.setText(
                "Select a candidate to inspect its relationship with the repository."
            )
            return

        row = rows[0].row()
        name_item = self._pdm_candidates.item(row, 1)
        name = name_item.text() if name_item else "-"
        self._selection_info.setText(
            f"Selected candidate: {name} — ready to load into the working Snapshot."
        )
        self._load_snapshot_btn.setEnabled(True)

    def _filter_candidates(self, text: str) -> None:
        """Filter visible rows only; discovery evidence remains unchanged."""
        query = text.casefold().strip()
        for row in range(self._pdm_candidates.rowCount()):
            searchable = " ".join(
                (
                    self._pdm_candidates.item(row, column).text()
                    if self._pdm_candidates.item(row, column)
                    else ""
                )
                for column in range(self._pdm_candidates.columnCount() - 1)
            ).casefold()
            self._pdm_candidates.setRowHidden(
                row, bool(query and query not in searchable)
            )

        self._pdm_candidates.clearSelection()

    def _selected_candidate(self) -> dict | None:
        """Return the selected discovery record without creating a saved mapping."""
        rows = self._pdm_candidates.selectionModel().selectedRows()
        if not rows:
            return None
        context = self._context.repository_context_service.active_context
        if context is None:
            return None
        row = rows[0].row()
        return self._visible_candidates[row] if 0 <= row < len(self._visible_candidates) else None

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

    def _selected_series_products(self, candidate: dict) -> list:
        """Return the complete PDM series represented by the selected row.

        Review discovery contains the product records already grouped by
        catalogue. Once a user chooses a catalogue and then a series/category,
        the downstream workflow must use the established *family* loader rather
        than loading one arbitrary product record. This keeps the existing
        Product -> Articles -> Class Creation pipeline unchanged.
        """
        context = self._context.repository_context_service.active_context
        all_candidates = context.candidate_products if context else []

        catalogue = self._value(candidate, "catalogue", "catalogue_name")
        category = self._value(candidate, "category", "category_name")

        series_candidates = [
            item for item in all_candidates
            if self._value(item, "catalogue", "catalogue_name") == catalogue
            and self._value(item, "category", "category_name") == category
        ]

        # The selected row must always remain a valid fallback even if discovery
        # evidence was reduced or filtered.
        if not series_candidates:
            series_candidates = [candidate]

        products = []
        seen = set()
        for item in series_candidates:
            product = self._candidate_to_product(item)
            if product.id and product.id not in seen:
                seen.add(product.id)
                products.append(product)
        return products

    def _load_selected_candidate(self) -> None:
        """Load the selected catalogue/series through the existing family flow."""
        candidate = self._selected_candidate()
        if candidate is None:
            return

        products = self._selected_series_products(candidate)
        if not products:
            QMessageBox.warning(
                self, "Snapshot Load", "No valid PDM products were found for the selected series."
            )
            return

        family_name = (
            self._value(candidate, "category", "category_name")
            if self._value(candidate, "category", "category_name") != "-"
            else self._value(candidate, "name", "product_name")
        )

        # IMPORTANT: use the established family loader. It is the existing
        # workflow responsible for loading all articles and their details into
        # one Snapshot. Do not replace it with single-product loading here.
        result = self._context.pdm_service.load_family(products, family_name)
        if not result.ok:
            QMessageBox.warning(self, "Snapshot Load", result.message)
            return

        snapshot = self._context.active_snapshot
        try:
            self._context.engineering_initialization_service.initialize(snapshot)
        except Exception as error:
            QMessageBox.warning(
                self,
                "Engineering Initialization",
                f"The PDM series loaded, but workflow initialization failed:\n{error}",
            )
            return

        repository_context = self._context.repository_context_service.active_context
        if repository_context is not None:
            engineering_summary = {
                "article_count": len(getattr(snapshot, "articles", []) or []),
                "article_length": None,
                "links": [],
            }
            self._context.repository_connection_service.establish(
                repository_path=repository_context.repository_path,
                repository_name=str(repository_context.records["name"].value or ""),
                repository_code=str(repository_context.records["code"].value or ""),
                repository_category=repository_context.category,
                pdm_candidate=candidate,
                engineering_summary=engineering_summary,
            )

        self.series_loaded.emit(family_name)
        self._selection_info.setText(
            f"Working connection established: {family_name} "
            f"({len(products)} PDM product record(s), "
            f"{len(getattr(snapshot, 'articles', []) or [])} articles loaded)."
        )
        QMessageBox.information(
            self,
            "Connection Established",
            f"The selected PDM series '{family_name}' was loaded through the "
            f"existing family workflow ({len(products)} product record(s), "
            f"{len(getattr(snapshot, 'articles', []) or [])} articles) and the "
            "repository ↔ PDM connection was stored in the central registry.",
        )

    def _clear_catalogues(self, message: str) -> None:
        self._catalogues.clearContents()
        self._catalogues.setRowCount(1)
        item = QTableWidgetItem(message)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self._catalogues.setItem(0, 0, item)
        self._catalogues.setSpan(0, 0, 1, len(self._CATALOGUE_COLUMNS))

    def _clear_candidates(self, message: str) -> None:
        self._visible_candidates = []
        self._pdm_candidates.clearContents()
        self._pdm_candidates.setRowCount(1)
        item = QTableWidgetItem(message)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self._pdm_candidates.setItem(0, 0, item)
        self._pdm_candidates.setSpan(0, 0, 1, len(self._COLUMNS))

    def _refresh_source_comparison(self) -> None:
        context = self._context.repository_context_service.active_context
        if context is None:
            self._source_status.setText(
                "No repository series selected. Open a repository series from Product."
            )
            for widget in self._source_rows.values():
                widget.setText("-")
            self._clear_candidates("No PDM discovery data available.")
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
            self._clear_candidates("Select a catalogue to load its series.")
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
        self._clear_candidates("Select a catalogue to load its series.")

    def _load_catalogue_series(self, catalogue_name: str) -> None:
        context = self._context.repository_context_service.active_context
        all_candidates = context.candidate_products if context else []
        self._visible_candidates = [
            product for product in all_candidates
            if self._value(product, "catalogue") == catalogue_name
        ]
        candidates = self._visible_candidates
        self._candidate_search.clear()
        self._pdm_candidates.clearSpans()
        self._pdm_candidates.clearContents()
        self._pdm_candidates.setRowCount(len(candidates))
        self._load_snapshot_btn.setEnabled(False)
        if not candidates:
            self._clear_candidates("No PDM series found for this catalogue.")
            return

        for row, product in enumerate(candidates):
            values = (
                str(row + 1),
                self._value(product, "name", "product_name"),
                self._value(product, "code", "product_code"),
                self._value(product, "category", "category_name"),
                self._value(product, "range_name", "range", "product_range"),
                self._value(product, "catalogue", "catalogue_name"),
                (
                    f"{product.get('lead_time')}-day"
                    if product.get("lead_time") is not None
                    else "-"
                ),
                "Candidate",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._pdm_candidates.setItem(row, column, item)

        self._pdm_candidates.resizeRowsToContents()

    def _on_catalogue_selection_changed(self) -> None:
        rows = self._catalogues.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        item = self._catalogues.item(row, 1)
        if item is None:
            return
        catalogue = item.text()
        self._selection_info.setText(
            f"Catalogue selected: {catalogue}. Select a PDM series next."
        )
        self._load_catalogue_series(catalogue)

    def _filter_catalogues(self, text: str) -> None:
        query = text.casefold().strip()
        for row in range(self._catalogues.rowCount()):
            searchable = " ".join(
                self._catalogues.item(row, column).text()
                if self._catalogues.item(row, column) else ""
                for column in range(self._catalogues.columnCount())
            ).casefold()
            self._catalogues.setRowHidden(row, bool(query and query not in searchable))

    def refresh(self) -> None:
        self._selection_info.setText(
            "Select a candidate to inspect its relationship with the repository."
        )
        self._load_snapshot_btn.setEnabled(False)
        self._refresh_source_comparison()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def is_ready(self) -> bool:
        return True
