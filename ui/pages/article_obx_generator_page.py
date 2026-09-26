"""Article OBX Generator workspace.

The workspace first exposes the repository-backed article permutations. OBX
generation is intentionally a separate later action so the user can inspect
the resolved article list before producing a file.
"""
from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from ui.components import SectionHeader
from ui.components._styles import primary_button_qss, secondary_button_qss
from ui.pages.base_page import BasePage


class ArticleObxGeneratorPage(BasePage):
    """Inspect repository article permutations before OBX generation."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Article OBX Generator",
            description=(
                "Review article permutations from the repository, then use the "
                "selected effective date and currency for OBX generation."
            ),
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._permutations = []
        self._currency = QComboBox(self)
        self._date = QDateEdit(self)
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        self._date.setDate(QDate.currentDate())
        self._status = QLabel("No repository snapshot loaded.", self)
        self._status.setWordWrap(True)

        self._refresh_button = QPushButton("Refresh Permutations", self)
        self._refresh_button.setStyleSheet(
            secondary_button_qss("articleObxRefreshButton")
        )
        self._refresh_button.clicked.connect(self._load_permutations)

        self._build_content()
        self.refresh()

    def _build_content(self) -> None:
        source = QGroupBox("Repository Source", self)
        source_layout = QVBoxLayout(source)
        source_layout.addWidget(SectionHeader(
            "Repository Snapshot",
            "Article permutations are derived only from the repository snapshot loaded by the workbench."
        ))
        source_layout.addWidget(self._status)

        permutation_box = QGroupBox("Article Permutations", self)
        permutation_layout = QVBoxLayout(permutation_box)

        self._table = QTableWidget(self)
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Article",
            "Base Article",
            "Type",
            "Properties",
            "Options",
            "Quantity",
            "Status",
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        permutation_layout.addWidget(self._table)

        generation = QGroupBox("OBX Parameters", self)
        generation_layout = QHBoxLayout(generation)
        generation_layout.addWidget(QLabel("Currency:"))
        generation_layout.addWidget(self._currency)
        generation_layout.addSpacing(20)
        generation_layout.addWidget(QLabel("Effective date:"))
        generation_layout.addWidget(self._date)
        generation_layout.addStretch(1)

        actions = QHBoxLayout()
        actions.addWidget(self._refresh_button)
        actions.addStretch(1)

        self.add_content(source)
        self.add_content(permutation_box)
        self.add_content(generation)
        self._content.addLayout(actions)

    @staticmethod
    def _values_text(values) -> str:
        if not values:
            return "—"
        return ", ".join(
            f"{value.name}: {value.value}"
            + (f" [{value.code}]" if value.code else "")
            for value in values
        )

    def _load_permutations(self) -> None:
        snapshot = self._context.repository_snapshot
        self._table.setRowCount(0)
        self._permutations = []

        if snapshot is None:
            self._status.setText("No repository snapshot is loaded.")
            return

        service = self._context.article_permutation_service
        self._permutations = service.build(snapshot)

        self._table.setRowCount(len(self._permutations))
        for row, permutation in enumerate(self._permutations):
            values = [
                permutation.final_article,
                permutation.base_code,
                "Super Item" if permutation.is_super_item else "Article",
                self._values_text(permutation.properties),
                self._values_text(permutation.options),
                str(permutation.quantity),
                "Resolved",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self._table.setItem(row, column, item)

        self._status.setText(
            f"Repository snapshot loaded: "
            f"{snapshot.product.code or snapshot.product.name} "
            f"| Articles: {len(snapshot.articles)} "
            f"| Permutations: {len(self._permutations)} "
            f"| Properties: {len(snapshot.properties)} "
            f"| Options: {len(snapshot.options)} "
            f"| Prices: {len(snapshot.price_records)}"
        )

    def refresh(self) -> None:
        snapshot = self._context.repository_snapshot
        self._currency.clear()

        if snapshot is None:
            self._status.setText(
                "No repository snapshot is loaded. Load/select the published repository "
                "through the existing repository workflow, then return here."
            )
            self._refresh_button.setEnabled(False)
            self._table.setRowCount(0)
            return

        currencies = sorted({
            str(price.currency or "").upper()
            for price in snapshot.price_records
            if str(price.currency or "").strip()
        })
        self._currency.addItems(currencies)
        self._refresh_button.setEnabled(bool(snapshot.articles))
        self._load_permutations()

    def is_ready(self) -> bool:
        return self._context.repository_snapshot is not None
