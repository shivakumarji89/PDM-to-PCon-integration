"""Article OBX Generator workspace.

This module is intentionally repository-only. It consumes the repository
Snapshot already loaded by the workbench and never initiates a PDM read.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.components import SectionHeader, StatisticsGrid
from ui.components._styles import primary_button_qss, secondary_button_qss
from ui.pages.base_page import BasePage
from core.modules import WorkbenchModule
from core.enums import WorkflowStep


class ArticleObxGeneratorPage(BasePage):
    """Generate an Article OBX from the active repository snapshot."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Article OBX Generator",
            description=(
                "Build article permutations from repository data, resolve repository "
                "prices, and generate an OBX for a specified effective date."
            ),
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._currency = QComboBox(self)
        self._date = QLineEdit(self)
        self._date.setPlaceholderText("YYYYMMDD")
        self._status = QLabel("No repository snapshot loaded.", self)
        self._status.setWordWrap(True)
        self._generate_button = QPushButton("Generate OBX", self)
        self._generate_button.setObjectName("articleObxGenerateButton")
        self._generate_button.setStyleSheet(
            primary_button_qss("articleObxGenerateButton")
        )
        self._generate_button.clicked.connect(self._generate)

        self._build_content()
        self.refresh()

    def _build_content(self) -> None:
        source = QGroupBox("Repository Source", self)
        source_layout = QVBoxLayout(source)
        source_layout.addWidget(SectionHeader(
            "Repository Snapshot",
            "The generator uses only the repository snapshot currently loaded by the workbench."
        ))
        source_layout.addWidget(self._status)

        options = QGroupBox("OBX Generation", self)
        form = QFormLayout(options)
        form.addRow("Currency:", self._currency)
        form.addRow("Effective date:", self._date)

        actions = QHBoxLayout()
        actions.addWidget(self._generate_button)
        actions.addStretch(1)

        self.add_content(source)
        self.add_content(options)
        self.add_content(QWidget(self))
        self._content.addLayout(actions)

    def refresh(self) -> None:
        snapshot = self._context.repository_snapshot
        self._currency.clear()
        if snapshot is not None:
            currencies = sorted({
                str(price.currency or "").upper()
                for price in snapshot.price_records
                if str(price.currency or "").strip()
            })
            if not currencies:
                currencies = sorted({
                    str(price.currency or "").upper()
                    for price in snapshot.price_records
                    if str(price.currency or "").strip()
                })
            self._currency.addItems(currencies)

            self._status.setText(
                f"Repository snapshot loaded: {snapshot.product.code or snapshot.product.name} "
                f"| Articles: {len(snapshot.articles)} "
                f"| Properties: {len(snapshot.properties)} "
                f"| Options: {len(snapshot.options)} "
                f"| Prices: {len(snapshot.price_records)}"
            )
            self._generate_button.setEnabled(bool(snapshot.articles and snapshot.price_records))
        else:
            self._status.setText(
                "No repository snapshot is loaded. Load/select the published repository "
                "through the existing repository workflow, then return here."
            )
            self._generate_button.setEnabled(False)

    def is_ready(self) -> bool:
        return self._context.repository_snapshot is not None

    def _generate(self) -> None:
        snapshot = self._context.repository_snapshot
        currency = self._currency.currentText().strip().upper()
        effective_date = self._date.text().strip()

        if snapshot is None:
            QMessageBox.warning(self, "Article OBX Generator", "No repository snapshot is loaded.")
            return
        if not currency:
            QMessageBox.warning(self, "Article OBX Generator", "Select a currency.")
            return
        if len(effective_date) != 8 or not effective_date.isdigit():
            QMessageBox.warning(
                self, "Article OBX Generator",
                "Effective date must be entered as YYYYMMDD."
            )
            return

        result = self._context.article_obx_service.generate(
            currency=currency,
            effective_date=effective_date,
        )
        if not result.xml:
            QMessageBox.warning(
                self, "Article OBX Generator",
                "\n".join(result.warnings) or "No OBX was generated."
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Article OBX",
            f"{snapshot.product.code or 'article'}_{effective_date}.obx",
            "OBX files (*.obx);;XML files (*.xml)",
        )
        if not path:
            return

        self._context.article_obx_service.write(path, result)
        message = f"Generated {len(result.rows)} article(s)."
        if result.warnings:
            message += "\n\nWarnings:\n" + "\n".join(result.warnings)
        QMessageBox.information(self, "Article OBX Generator", message)
