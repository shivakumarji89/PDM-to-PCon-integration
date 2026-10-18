"""Legacy-shaped SyteLine export workspace.

This phase mirrors the visible legacy PDM controls. Export execution remains guarded
until SQL mappings and output parity can be verified.
"""
from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)
from core.application_context import ApplicationContext
from ui.pages.base_page import BasePage


class SyteLineExportPage(BasePage):
    """Legacy PDM export controls, isolated from other workbench workflows."""

    PREFIX = "syteline/"

    def __init__(self, context: ApplicationContext, parent: QWidget | None = None) -> None:
        super().__init__(
            "Export PDM Data",
            "Legacy SyteLine export configuration. Live export remains guarded pending parity verification.",
            parent, show_placeholder=False, content_stretch=True,
        )
        self._context = context
        self.settings = QSettings()
        self._build_ui()
        self._load_settings()
        self._update_scope_controls()

    @staticmethod
    def _combo(items: list[str], selected: str = "") -> QComboBox:
        widget = QComboBox()
        widget.addItems(items)
        if selected:
            widget.setCurrentText(selected)
        return widget

    def _build_ui(self) -> None:
        root = QVBoxLayout()
        root.setSpacing(6)
        header = QHBoxLayout()
        header.addWidget(QLabel("Specify the export parameters:"))
        header.addStretch(1)
        self.scheduler = QPushButton("Scheduler")
        self.scheduler.setEnabled(False)
        self.scheduler.setToolTip("Scheduler integration awaits the legacy workflow port.")
        header.addWidget(self.scheduler)
        root.addLayout(header)

        selectors = QGridLayout()
        self.site = self._combo(["UK", "US", "DE", "FR", "NL"], "UK")
        self.language = self._combo(["English", "German", "French", "Dutch"], "English")
        self.other_language = self._combo(["English", "German", "French", "Dutch"], "English")
        for col, (label, widget) in enumerate([
            ("Site:", self.site), ("Language:", self.language), ("Other Language:", self.other_language)
        ]):
            selectors.addWidget(QLabel(label), 0, col)
            selectors.addWidget(widget, 1, col)
        root.addLayout(selectors)

        catalogue_label = QHBoxLayout()
        catalogue_label.addWidget(QLabel("Select a Catalogue to export:"))
        self.catalogue_required = QLabel("< Required >")
        self.catalogue_required.setStyleSheet("color: #b42318;")
        catalogue_label.addWidget(self.catalogue_required)
        catalogue_label.addStretch(1)
        root.addLayout(catalogue_label)
        self.catalogue = self._combo([])
        self.catalogue.setEditable(True)
        self.catalogue.setPlaceholderText("Catalogue")
        root.addWidget(self.catalogue)

        self.filter_product_code = QCheckBox("Filter by Product Code")
        root.addWidget(self.filter_product_code)
        self.product_line = self._combo([])
        self.product_line.setEditable(True)
        self.product_line.setPlaceholderText("Product line / superproduct")
        root.addWidget(self.product_line)

        scope = QGridLayout()
        self.range_check = QCheckBox("Items within a range:")
        self.list_check = QCheckBox("Items from specified list:")
        self.min_item = QLineEdit("WE")
        self.max_item = QLineEdit("WE")
        self.min_item.setMaximumWidth(180)
        self.max_item.setMaximumWidth(180)
        self.item_list = QListWidget()
        self.item_list.setMaximumHeight(70)
        scope.addWidget(self.range_check, 0, 0, 1, 2)
        scope.addWidget(self.list_check, 0, 2, 1, 2)
        scope.addWidget(QLabel("From Item:"), 1, 0)
        scope.addWidget(self.min_item, 1, 1)
        scope.addWidget(self.item_list, 1, 2, 2, 1)
        scope.addWidget(QLabel("To Item:"), 2, 0)
        scope.addWidget(self.max_item, 2, 1)
        scope.addWidget(QLabel("Currency:"), 3, 0)
        self.currency = self._combo(["GBP", "EUR", "USD"], "GBP")
        scope.addWidget(self.currency, 3, 1)
        list_buttons = QHBoxLayout()
        self.add_items = QPushButton("Add Items…")
        self.clear_items = QPushButton("Clear List")
        self.add_items.clicked.connect(self._add_items)
        self.clear_items.clicked.connect(self.item_list.clear)
        list_buttons.addWidget(self.add_items)
        list_buttons.addWidget(self.clear_items)
        scope.addLayout(list_buttons, 3, 2)
        self.params = QPushButton("Params")
        self.params.clicked.connect(self._show_params)
        params_row = QHBoxLayout()
        params_row.addStretch(1)
        params_row.addWidget(self.params)
        scope.addLayout(params_row, 4, 2, 1, 2)
        root.addLayout(scope)

        self.tabs = QTabWidget()
        self.checks: dict[str, QCheckBox] = {}
        self._add_tab("SyteLine", [
            ("active_only", "Export Active Items Only", True),
            ("flatten_fab", "Flatten Fab", False),
            ("length_5_feats", "Use length 5 Feats", False),
            ("short_phantoms", "Short Phantoms", False),
            ("ignore_option_dependencies", "Ignore Option to Option Dependencies", False),
            ("extend_sp_options", "Extend SP Options", False),
            ("base_prices", "Export Base Prices", True),
            ("unique_phantoms", "Unique Phantoms", True),
            ("plc_prefix", "Use PLC Prefix", False),
        ], include_export_type=True)
        self._add_tab("SyteLine (CSI)", [
            ("csi_active_only", "Export Active Items Only", True),
            ("csi_short_descriptions", "Short Descriptions", False),
            ("csi_exclude_superproducts", "Exclude Superproducts", False),
            ("csi_superproducts_only", "Superproducts Only", False),
            ("csi_plc_phantoms", "PLC Phantoms", False),
            ("csi_short_phantoms", "Short Phantoms", False),
            ("csi_unique_fabrics", "Unique Fabric Types", False),
        ])
        self._add_tab("OFDA (CET)", [
            ("ofda_export", "Export OFDA (CET) data", False),
            ("ofda_validate", "Validate export data", False),
            ("ofda_designer_images", "Include designer images", False),
        ])
        self._add_tab("Other", [
            ("other_base_prices", "Export Base Prices", True),
            ("other_include_url", "Include URL items", False),
            ("other_short_descriptions", "Short descriptions", False),
            ("other_exclude_superproducts", "Exclude Superproducts", False),
            ("other_superproducts_only", "Superproducts Only", False),
            ("other_validate", "Validate export", False),
        ])
        root.addWidget(self.tabs, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.queue = QPushButton("Queue")
        self.export = QPushButton("Export")
        self.queue.setEnabled(False)
        self.export.setEnabled(False)
        self.queue.setToolTip("Queue execution is not yet ported.")
        self.export.setToolTip("Live export is disabled pending legacy query and output parity tests.")
        buttons.addWidget(self.queue)
        buttons.addWidget(self.export)
        root.addLayout(buttons)

        footer = QHBoxLayout()
        self.status = QLabel("Ready — live export is not yet enabled.")
        self.status.setWordWrap(True)
        self.elapsed = QLabel("Time: 00:00:00")
        footer.addWidget(self.status, 1)
        footer.addWidget(self.elapsed)
        root.addLayout(footer)
        content = QWidget()
        content.setLayout(root)
        self.add_content(content)

    def _add_tab(self, title: str, definitions: list[tuple[str, str, bool]], include_export_type: bool = False) -> None:
        page = QWidget()
        layout = QGridLayout(page)
        row = 0
        if include_export_type:
            layout.addWidget(QLabel("Export Type:"), row, 0)
            self.export_type = self._combo([
                "Verbose Extract (full)", "Verbose Extract", "Compact Extract"
            ], "Verbose Extract (full)")
            layout.addWidget(self.export_type, row, 1, 1, 2)
            row += 1
            self.load_contract = QPushButton("Load")
            self.load_contract.setEnabled(False)
            self.contract = self._combo([])
            self.contract.setEnabled(False)
            layout.addWidget(self.load_contract, row, 0)
            layout.addWidget(QLabel("Contract:"), row, 1)
            layout.addWidget(self.contract, row, 2)
            row += 1
        for key, label, default in definitions:
            check = QCheckBox(label)
            check.setChecked(default)
            self.checks[key] = check
            layout.addWidget(check, row, 0, 1, 3)
            row += 1
        layout.setRowStretch(row, 1)
        self.tabs.addTab(page, title)

    def _add_items(self) -> None:
        text, accepted = QInputDialog.getMultiLineText(
            self, "Add items", "Enter item codes (one per line or comma-separated):"
        )
        if not accepted:
            return
        existing = {self.item_list.item(i).text() for i in range(self.item_list.count())}
        for raw in text.replace(",", "\n").splitlines():
            item = raw.strip()
            if item and item not in existing:
                self.item_list.addItem(item)
                existing.add(item)

    def _show_params(self) -> None:
        QMessageBox.information(
            self, "Params",
            "The legacy Params dialog depends on database-backed definitions. "
            "Its source behavior must be ported before this action can be enabled.",
        )

    def _update_scope_controls(self, *_args) -> None:
        ranged, listed = self.range_check.isChecked(), self.list_check.isChecked()
        self.min_item.setEnabled(ranged)
        self.max_item.setEnabled(ranged)
        self.item_list.setEnabled(listed)
        self.add_items.setEnabled(listed)
        self.clear_items.setEnabled(listed)

    def _load_settings(self) -> None:
        for key, widget in [
            ("site", self.site), ("language", self.language), ("other_language", self.other_language),
            ("catalogue", self.catalogue), ("product_line", self.product_line), ("currency", self.currency),
            ("export_type", self.export_type), ("contract", self.contract),
        ]:
            widget.setCurrentText(self.settings.value(self.PREFIX + key, widget.currentText(), type=str))
        for key, widget in [("min_item", self.min_item), ("max_item", self.max_item)]:
            widget.setText(self.settings.value(self.PREFIX + key, widget.text(), type=str))
        for key, widget in [
            ("filter_product_code", self.filter_product_code), ("range_check", self.range_check),
            ("list_check", self.list_check),
        ]:
            widget.setChecked(self.settings.value(self.PREFIX + key, widget.isChecked(), type=bool))
        self.item_list.addItems(self.settings.value(self.PREFIX + "items", [], type=list))
        for key, widget in self.checks.items():
            widget.setChecked(self.settings.value(self.PREFIX + "options/" + key, widget.isChecked(), type=bool))
        self.range_check.toggled.connect(self._update_scope_controls)
        self.list_check.toggled.connect(self._update_scope_controls)

    def _save_settings(self) -> None:
        for key, widget in [
            ("site", self.site), ("language", self.language), ("other_language", self.other_language),
            ("catalogue", self.catalogue), ("product_line", self.product_line), ("currency", self.currency),
            ("export_type", self.export_type), ("contract", self.contract),
        ]:
            self.settings.setValue(self.PREFIX + key, widget.currentText())
        for key, widget in [("min_item", self.min_item), ("max_item", self.max_item)]:
            self.settings.setValue(self.PREFIX + key, widget.text())
        for key, widget in [
            ("filter_product_code", self.filter_product_code), ("range_check", self.range_check),
            ("list_check", self.list_check),
        ]:
            self.settings.setValue(self.PREFIX + key, widget.isChecked())
        self.settings.setValue(self.PREFIX + "items", [
            self.item_list.item(i).text() for i in range(self.item_list.count())
        ])
        for key, widget in self.checks.items():
            self.settings.setValue(self.PREFIX + "options/" + key, widget.isChecked())
        self.settings.sync()
        self.status.setText("Configuration saved locally; no database operation or export was executed.")
