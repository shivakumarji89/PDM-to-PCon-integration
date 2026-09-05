"""Review workspace for repository ↔ PDM source discovery.

This page is evidence-first: it compares a selected repository series with the
PDM records discovered for it, without asserting an automatic relationship.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
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

        self._load_snapshot_btn = QPushButton("Load Selected into Snapshot", box)
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

        candidates_box = QGroupBox(
            "PDM Candidates — Discovery Only (no automatic relationship)",
            box,
        )
        candidates_layout = QVBoxLayout(candidates_box)

        hint = QLabel(
            "Each row is a PDM record returned by discovery. Select rows to "
            "compare them with the repository series; no selection is saved or "
            "treated as verified at this stage.",
            candidates_box,
        )
        hint.setWordWrap(True)
        candidates_layout.addWidget(hint)

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

    def _selected_candidate(self) -> dict | None:
        """Return the selected discovery record without creating a saved mapping."""
        rows = self._pdm_candidates.selectionModel().selectedRows()
        if not rows:
            return None
        context = self._context.repository_context_service.active_context
        if context is None:
            return None
        row = rows[0].row()
        candidates = context.candidate_products or []
        return candidates[row] if 0 <= row < len(candidates) else None

    def _load_selected_candidate(self) -> None:
        """Bridge an explicitly selected PDM candidate into the normal Snapshot."""
        candidate = self._selected_candidate()
        if candidate is None:
            return

        from models.product import Product

        product = Product(
            id=str(candidate.get("id") or ""),
            code=str(candidate.get("code") or ""),
            name=str(candidate.get("name") or ""),
            category=str(candidate.get("category") or ""),
            description=str(candidate.get("catalogue") or ""),
        )
        result = self._context.pdm_service.load_product(product)
        if not result.ok:
            QMessageBox.warning(self, "Snapshot Load", result.message)
            return

        self._selection_info.setText(
            f"Loaded into Snapshot: {product.name}. Existing workflows can now use this context."
        )
        QMessageBox.information(
            self,
            "Snapshot Loaded",
            "The selected PDM candidate was loaded into the active Snapshot. "
            "No repository ↔ PDM relationship was saved or verified.",
        )

    def _clear_candidates(self, message: str) -> None:
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

        candidates = context.candidate_products or []
        if not candidates:
            self._clear_candidates("No PDM candidates found.")
            return

        self._pdm_candidates.clearSpans()
        self._pdm_candidates.clearContents()
        self._pdm_candidates.setRowCount(len(candidates))

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
