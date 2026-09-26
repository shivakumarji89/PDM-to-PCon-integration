"""Article OBX Generator workspace.

The first stage is an inspectable permutation builder. Pricing and OBX
generation remain a later action after the generated article numbers are
reviewed.
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
from ui.components._styles import secondary_button_qss
from ui.pages.base_page import BasePage


class ArticleObxGeneratorPage(BasePage):
    """Inspect repository-generated article permutations."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Article OBX Generator",
            description=(
                "Generate and review valid article permutations from repository "
                "configuration data. Pricing and OBX generation follow after review."
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

        self._build_button = QPushButton("Build Permutations", self)
        self._build_button.setStyleSheet(
            secondary_button_qss("articleObxBuildButton")
        )
        self._build_button.clicked.connect(self._build_permutations)

        self._build_content()
        self.refresh()

    def _build_content(self) -> None:
        source = QGroupBox("Repository Source", self)
        source_layout = QVBoxLayout(source)
        source_layout.addWidget(SectionHeader(
            "Repository Snapshot",
            "Only the repository snapshot is used. Existing materialized articles are not the permutation output."
        ))
        source_layout.addWidget(self._status)

        permutation_box = QGroupBox("Generated Article Permutations", self)
        permutation_layout = QVBoxLayout(permutation_box)

        self._table = QTableWidget(self)
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "#",
            "Base Article",
            "Generated Article",
            "Properties",
            "Options",
            "Configuration",
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
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        permutation_layout.addWidget(self._table)

        parameters = QGroupBox("OBX Parameters", self)
        parameter_layout = QHBoxLayout(parameters)
        parameter_layout.addWidget(QLabel("Currency:"))
        parameter_layout.addWidget(self._currency)
        parameter_layout.addSpacing(24)
        parameter_layout.addWidget(QLabel("Effective date:"))
        parameter_layout.addWidget(self._date)
        parameter_layout.addStretch(1)

        actions = QHBoxLayout()
        actions.addWidget(self._build_button)
        actions.addStretch(1)

        self.add_content(source)
        self.add_content(permutation_box)
        self.add_content(parameters)
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

    def _build_permutations(self) -> None:
        snapshot = self._context.repository_snapshot
        self._table.setRowCount(0)
        self._permutations = []

        if snapshot is None:
            self._status.setText("No repository snapshot is loaded.")
            return

        self._permutations = self._context.article_permutation_service.build(snapshot)

        self._table.setRowCount(len(self._permutations))
        for row, permutation in enumerate(self._permutations, start=1):
            configuration = "; ".join(
                f"{value.name}={value.value}"
                for value in (*permutation.properties, *permutation.options)
            ) or "—"
            values = [
                str(row),
                permutation.base_code,
                permutation.final_article,
                self._values_text(permutation.properties),
                self._values_text(permutation.options),
                configuration,
                "Valid",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self._table.setItem(row - 1, column, item)

        self._status.setText(
            f"Repository snapshot loaded: "
            f"{snapshot.product.code or snapshot.product.name} "
            f"| Repository articles: {len(snapshot.articles)} "
            f"| Generated permutations: {len(self._permutations)} "
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
            self._build_button.setEnabled(False)
            self._table.setRowCount(0)
            return

        currencies = sorted({
            str(price.currency or "").upper()
            for price in snapshot.price_records
            if str(price.currency or "").strip()
        })
        self._currency.addItems(currencies)
        self._build_button.setEnabled(bool(snapshot.article_sets))
        self._build_permutations()

    def is_ready(self) -> bool:
        return self._context.repository_snapshot is not None
