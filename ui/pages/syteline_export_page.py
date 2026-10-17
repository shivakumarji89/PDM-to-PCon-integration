"""Isolated SyteLine export configuration workspace.

Export execution deliberately remains disabled until legacy SQL, transformations,
external dependencies and reference-output parity have been verified.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QPlainTextEdit, QVBoxLayout, QWidget,
)
from core.application_context import ApplicationContext
from ui.pages.base_page import BasePage


class SyteLineExportPage(BasePage):
    """Standalone SyteLine export settings and validation page."""

    def __init__(self, context: ApplicationContext, parent: QWidget | None = None) -> None:
        super().__init__(
            "SyteLine Export",
            "Separate legacy-compatible export workspace. Existing modules and workflows are unchanged.",
            parent, show_placeholder=False, content_stretch=True,
        )
        self._context = context
        self._settings = QSettings()
        self._build_ui()
        self._load_settings()
        self._update_scope_controls()

    def _build_ui(self) -> None:
        root = QVBoxLayout()
        root.setSpacing(10)

        source = QGroupBox("Source and output")
        form = QFormLayout(source)
        self.server = QLineEdit()
        self.server.setPlaceholderText("SQL Server host\\instance")
        self.database = QLineEdit()
        self.database.setPlaceholderText("SyteLine database name")
        self.output_directory = QLineEdit()
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_directory, 1)
        output_row.addWidget(browse)
        output_widget = QWidget()
        output_widget.setLayout(output_row)
        form.addRow("SQL Server", self.server)
        form.addRow("Database", self.database)
        form.addRow("Output folder", output_widget)
        root.addWidget(source)

        scope = QGroupBox("Export scope")
        scope_form = QFormLayout(scope)
        self.site = QComboBox()
        self.site.setEditable(True)
        self.site.addItems(["uk", "us", "de", "fr", "nl"])
        self.product_line = QLineEdit()
        self.catalogue = QLineEdit()
        self.language = QLineEdit()
        self.currency = QComboBox()
        self.currency.setEditable(True)
        self.currency.addItems(["GBP", "EUR", "USD"])
        self.scope_mode = QComboBox()
        self.scope_mode.addItem("Selected products", "products")
        self.scope_mode.addItem("Item range", "range")
        self.scope_mode.addItem("Explicit item list", "list")
        self.min_item = QLineEdit()
        self.max_item = QLineEdit()
        self.item_list = QPlainTextEdit()
        self.item_list.setPlaceholderText("One item code per line")
        self.item_list.setMaximumHeight(72)
        for label, widget in (
            ("Site", self.site), ("Product line", self.product_line),
            ("Catalogue", self.catalogue), ("Language", self.language),
            ("Currency", self.currency), ("Scope", self.scope_mode),
            ("First item", self.min_item), ("Last item", self.max_item),
            ("Item list", self.item_list),
        ):
            scope_form.addRow(label, widget)
        self.scope_mode.currentIndexChanged.connect(self._update_scope_controls)
        root.addWidget(scope)

        options = QGroupBox("Export options")
        options_layout = QVBoxLayout(options)
        definitions = (
            ("products", "Products"), ("ranges", "Ranges"), ("lists", "Lists"),
            ("base_prices", "Base prices"), ("ofda", "OFDA data"),
            ("bom", "Bill of materials"), ("feature_options", "Feature options"),
            ("active_only", "Active items only"), ("all_catalogues", "All catalogues in site"),
            ("multi_site", "Multi-site"), ("multi_language", "Multi-language"),
            ("multi_currency", "Multi-currency"), ("plc_phantoms", "PLC phantoms"),
            ("flatten_fabrics", "Flatten fabrics"),
            ("exclude_super_products", "Exclude super-products"),
            ("super_products_only", "Super-products only"),
            ("include_url", "Include URL"), ("short_description", "Short descriptions"),
            ("validate_output", "Validate output"),
        )
        self.option_checks: dict[str, QCheckBox] = {}
        for key, caption in definitions:
            check = QCheckBox(caption)
            self.option_checks[key] = check
            options_layout.addWidget(check)
        for key in ("products", "base_prices", "validate_output"):
            self.option_checks[key].setChecked(True)
        root.addWidget(options)

        notice = QLabel(
            "Export execution is disabled in this stage. This page does not connect to "
            "SQL Server or read/write source data. The legacy SQL, transformation rules, "
            "dependencies and reference outputs must be mapped and tested before enabling export."
        )
        notice.setWordWrap(True)
        notice.setObjectName("pageSubtitle")
        root.addWidget(notice)

        actions = QHBoxLayout()
        save = QPushButton("Save configuration")
        save.clicked.connect(self._save_settings)
        validate = QPushButton("Validate configuration")
        validate.clicked.connect(self._validate_configuration)
        self.export_button = QPushButton("Export")
        self.export_button.setEnabled(False)
        self.export_button.setToolTip("Awaiting legacy query mapping and output-parity tests.")
        actions.addWidget(save)
        actions.addWidget(validate)
        actions.addWidget(self.export_button)
        actions.addStretch(1)
        root.addLayout(actions)
        self.status = QLabel("Configuration not yet validated.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        root.addStretch(1)

        content = QWidget()
        content.setLayout(root)
        self.add_content(content)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Choose SyteLine export folder", self.output_directory.text()
        )
        if path:
            self.output_directory.setText(path)

    def _update_scope_controls(self, *_args) -> None:
        mode = self.scope_mode.currentData()
        self.min_item.setEnabled(mode == "range")
        self.max_item.setEnabled(mode == "range")
        self.item_list.setEnabled(mode == "list")

    def _load_settings(self) -> None:
        defaults = {
            "server": "", "database": "", "output_directory": "", "site": "uk",
            "product_line": "", "catalogue": "", "language": "", "currency": "GBP",
            "scope_mode": "products", "min_item": "", "max_item": "", "item_list": "",
        }
        widgets = {
            "server": self.server, "database": self.database,
            "output_directory": self.output_directory, "product_line": self.product_line,
            "catalogue": self.catalogue, "language": self.language,
            "min_item": self.min_item, "max_item": self.max_item,
        }
        for key, widget in widgets.items():
            widget.setText(self._settings.value(f"syteline/{key}", defaults[key], type=str))
        self.site.setCurrentText(self._settings.value("syteline/site", "uk", type=str))
        self.currency.setCurrentText(self._settings.value("syteline/currency", "GBP", type=str))
        self.item_list.setPlainText(self._settings.value("syteline/item_list", "", type=str))
        mode_index = self.scope_mode.findData(
            self._settings.value("syteline/scope_mode", "products", type=str)
        )
        if mode_index >= 0:
            self.scope_mode.setCurrentIndex(mode_index)
        for key, check in self.option_checks.items():
            check.setChecked(self._settings.value(
                f"syteline/options/{key}",
                key in {"products", "base_prices", "validate_output"}, type=bool,
            ))

    def _save_settings(self) -> None:
        values = {
            "server": self.server.text().strip(), "database": self.database.text().strip(),
            "output_directory": self.output_directory.text().strip(),
            "site": self.site.currentText().strip(),
            "product_line": self.product_line.text().strip(),
            "catalogue": self.catalogue.text().strip(), "language": self.language.text().strip(),
            "currency": self.currency.currentText().strip(),
            "scope_mode": self.scope_mode.currentData(),
            "min_item": self.min_item.text().strip(), "max_item": self.max_item.text().strip(),
            "item_list": self.item_list.toPlainText(),
        }
        for key, value in values.items():
            self._settings.setValue(f"syteline/{key}", value)
        for key, check in self.option_checks.items():
            self._settings.setValue(f"syteline/options/{key}", check.isChecked())
        self._settings.sync()
        self.status.setText("Configuration saved locally. No database connection or export was run.")

    def _validate_configuration(self) -> None:
        errors: list[str] = []
        if not self.server.text().strip():
            errors.append("SQL Server is required.")
        if not self.database.text().strip():
            errors.append("Database name is required.")
        if not self.site.currentText().strip():
            errors.append("Site is required.")
        if not self.currency.currentText().strip():
            errors.append("Currency is required.")
        output = self.output_directory.text().strip()
        if not output:
            errors.append("Output folder is required.")
        elif not Path(output).expanduser().is_dir():
            errors.append("Output folder must already exist.")
        mode = self.scope_mode.currentData()
        if mode == "range":
            first, last = self.min_item.text().strip(), self.max_item.text().strip()
            if not first or not last:
                errors.append("Both range endpoints are required.")
            elif first > last:
                errors.append("First item must not sort after last item.")
        elif mode == "list":
            items = [x.strip() for x in self.item_list.toPlainText().splitlines() if x.strip()]
            if not items:
                errors.append("Enter at least one item code.")
            elif len(items) != len(set(items)):
                errors.append("Item list contains duplicates.")
        data_types = {"products", "ranges", "lists", "base_prices", "ofda", "bom"}
        if not any(self.option_checks[key].isChecked() for key in data_types):
            errors.append("Select at least one export data type.")
        if errors:
            self.status.setText("Configuration issues:\n• " + "\n• ".join(errors))
        else:
            self.status.setText(
                "Local configuration checks passed. SQL connectivity, extraction and output "
                "generation have not been tested."
            )
