"""Legacy-shaped SyteLine export workspace.

This phase mirrors the visible legacy PDM controls. Export execution remains guarded
until SQL mappings and output parity can be verified.
"""
from __future__ import annotations

from PySide6.QtCore import QDate, QSettings, Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QGridLayout, QHBoxLayout, QInputDialog, QLabel,
    QDateEdit, QFileDialog, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget,
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
        from services.syteline_export.metadata_service import SyteLineMetadataService
        self.metadata_service = SyteLineMetadataService(context)
        self._build_ui()
        self._load_settings()
        self._apply_authenticated_user_defaults()
        self._connect_autosave()
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

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Export PDM Data   v1.0.9686.24988"))
        title_row.addStretch(1)
        self.scheduler = QPushButton("Scheduler")
        self.scheduler.setEnabled(False)
        self.scheduler.setToolTip("Scheduler integration awaits the legacy workflow port.")
        title_row.addWidget(self.scheduler)
        title_row.addWidget(QLabel("PDM User ID:"))
        # User identity is supplied by the connected PDM session when available;
        # manual entry remains a fallback for environments without auth context.
        self.pdm_user_id = QLineEdit()
        self.pdm_user_id.setMaximumWidth(90)
        self.pdm_user_id.setPlaceholderText("PDM User ID")
        title_row.addWidget(self.pdm_user_id)
        self.load_database_choices = QPushButton("Load DB Choices")
        self.load_database_choices.clicked.connect(self._load_database_choices)
        title_row.addWidget(self.load_database_choices)
        root.addLayout(title_row)

        header = QLabel("Specify the export parameters:")
        root.addWidget(header)
        selectors = QGridLayout()
        self.site = self._combo([])
        self.language = self._combo([])
        self.other_language = self._combo([])
        # Match the fixed-width, non-editable selectors in the legacy WinForms
        # dialog. Values still come from live PDM metadata, never hard-coded.
        for widget in (self.site, self.language, self.other_language):
            widget.setEditable(False)
            widget.setMinimumWidth(105)
            widget.setMaximumWidth(150)
            widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            widget.setMinimumContentsLength(10)
        selectors.setColumnStretch(0, 1)
        selectors.setColumnStretch(1, 1)
        selectors.setColumnStretch(2, 1)
        for col, (label, widget) in enumerate([
            ("Site:", self.site), ("Language:", self.language), ("Other Language:", self.other_language)
        ]):
            selectors.addWidget(QLabel(label), 0, col)
            selectors.addWidget(widget, 1, col)
        root.addLayout(selectors)

        multi_selectors = QHBoxLayout()
        self.multi_sites = QPushButton("Sites…")
        self.multi_languages = QPushButton("Languages…")
        self.multi_currencies = QPushButton("Currencies…")
        self._multi_choices: dict[str, list[tuple[int, str]]] = {
            "sites": [], "languages": [], "currencies": [],
        }
        self.multi_sites.clicked.connect(lambda: self._choose_multiple("sites", self.site))
        self.multi_languages.clicked.connect(lambda: self._choose_multiple("languages", self.language))
        self.multi_currencies.clicked.connect(lambda: self._choose_multiple("currencies", self.currency))
        for button in (self.multi_sites, self.multi_languages, self.multi_currencies):
            button.setEnabled(False)
            button.setToolTip("Load database choices before selecting multiple values.")
            multi_selectors.addWidget(button)
        multi_selectors.addStretch(1)
        root.addLayout(multi_selectors)

        catalogue_label = QHBoxLayout()
        catalogue_label.addWidget(QLabel("Select a Catalogue to export:"))
        self.catalogue_required = QLabel("< Required >")
        self.catalogue_required.setStyleSheet("color: #b42318;")
        catalogue_label.addWidget(self.catalogue_required)
        catalogue_label.addStretch(1)
        root.addLayout(catalogue_label)
        self.catalogue = self._combo([])
        self.catalogue.setEditable(False)
        self.catalogue.setMinimumWidth(250)
        self.catalogue.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.catalogue.setMinimumContentsLength(28)
        root.addWidget(self.catalogue)

        override_row = QHBoxLayout()
        override_row.addWidget(QLabel("Catalogue Code override:"))
        self.catalogue_code_override = QLineEdit()
        self.catalogue_code_override.setPlaceholderText("Optional legacy catalogue code override")
        override_row.addWidget(self.catalogue_code_override, 1)
        root.addLayout(override_row)

        effective_row = QHBoxLayout()
        effective_row.addWidget(QLabel("Effective date:"))
        self.effective_date = QDateEdit()
        self.effective_date.setCalendarPopup(True)
        self.effective_date.setDisplayFormat("yyyy-MM-dd")
        self.effective_date.setDate(QDate.currentDate())
        effective_row.addWidget(self.effective_date)
        self.export_all_in_site = QCheckBox("Export All in Site")
        self.export_all_in_site.setChecked(True)
        self.export_bom_data = QCheckBox("Export BOM Data")
        self.export_bom_data.setEnabled(False)
        self.export_bom_data.setToolTip("BOM export remains disabled until legacy BOM queries and output parity are verified.")
        effective_row.addWidget(self.export_all_in_site)
        effective_row.addWidget(self.export_bom_data)
        effective_row.addStretch(1)
        root.addLayout(effective_row)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        self.output_directory = QLineEdit()
        self.output_directory.setPlaceholderText("Choose an existing output folder")
        self.browse_output = QPushButton("Browse...")
        self.browse_output.clicked.connect(self._browse_output_directory)
        output_row.addWidget(self.output_directory, 1)
        output_row.addWidget(self.browse_output)
        root.addLayout(output_row)

        self.filter_product_code = QCheckBox("Filter by Product Code")
        root.addWidget(self.filter_product_code)
        self.product_line = self._combo([])
        self.product_line.setEditable(False)
        self.product_line.setMinimumWidth(250)
        self.product_line.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.product_line.setMinimumContentsLength(28)
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
        self.currency = self._combo([])
        self.currency.setEditable(False)
        self.currency.setMinimumWidth(85)
        self.currency.setMaximumWidth(125)
        scope.addWidget(self.currency, 3, 1)
        list_buttons = QHBoxLayout()
        self.add_items = QPushButton("Add Item(s)")
        self.remove_items = QPushButton("Remove Selected")
        self.clear_items = QPushButton("Clear List")
        self.add_items.clicked.connect(self._add_items)
        self.remove_items.clicked.connect(self._remove_selected_items)
        self.clear_items.clicked.connect(self.item_list.clear)
        list_buttons.addWidget(self.add_items)
        list_buttons.addWidget(self.remove_items)
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
            ("separate_increments", "Separate Increments", False),
            ("superproducts_only", "SuperProducts Only", False),
            ("include_url", "Include URL", True),
            ("short_description", "Short Description", True),
        ], include_export_type=True)
        self._add_tab("SyteLine (CSI)", [
            ("csi_flatten_fabrics", "Flatten (Exclude) Fabric Type Level", False),
            ("csi_plc_phantoms", "PLC Phantoms", False),
            ("csi_short_phantoms", "Short Phantoms", False),
            ("csi_exclude_superproducts", "Exclude SuperProducts", False),
        ], include_site_ref=True)
        self._add_tab("OFDA (CET)", [
            ("ofda_export", "Export OFDA (CET) data", False),
            ("ofda_backup_xml", "Backup Previous OFDA XML (server only)", True),
            ("ofda_web_configurator", "Web Configurator Format", False),
            ("ofda_validate", "Validate export data", False),
        ], include_region=True)
        self._add_tab("Other", [
            ("other_naughtone", "Naughtone", False),
            ("other_unreleased_data", "Unreleased Data", False),
            ("other_attribute_group_codes", "Attribute Group Codes", False),
            ("other_exclude_panels", "Exclude Panels", False),
        ], include_pbom=True)
        root.addWidget(self.tabs, 1)

        buttons = QHBoxLayout()
        self.validate_setup = QPushButton("Validate Setup")
        self.validate_setup.clicked.connect(self._validate_setup)
        buttons.addWidget(self.validate_setup)
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
        self.status = QLabel("Ready — load database choices before configuring a legacy export.")
        self.status.setWordWrap(True)
        self.elapsed = QLabel("Time: 00:00:00")
        footer.addWidget(self.status, 1)
        footer.addWidget(self.elapsed)
        root.addLayout(footer)
        content = QWidget()
        content.setLayout(root)
        self.add_content(content)

    def _add_tab(
        self, title: str, definitions: list[tuple[str, str, bool]],
        include_export_type: bool = False, include_site_ref: bool = False,
        include_region: bool = False, include_pbom: bool = False,
    ) -> None:
        page = QWidget()
        layout = QGridLayout(page)
        row = 0
        if include_export_type:
            layout.addWidget(QLabel("Export Type:"), row, 0)
            # These are the three export modes shown in the legacy PDM form.
            # Keep the legacy ordering and default; execution routing is handled
            # separately and remains guarded until output parity is verified.
            self.export_type = self._combo(
                ["Exclude SuperProduct", "SuperProducts Only", "Verbose Extract (full)"],
                "Exclude SuperProduct",
            )
            layout.addWidget(self.export_type, row, 1, 1, 2)
            row += 1
            self.load_contract = QPushButton("Load")
            self.load_contract.setEnabled(False)
            self.load_contract.setToolTip("Contract choices require the legacy TradeNet contract lookup.")
            self.contract = self._combo([])
            self.contract.setEnabled(False)
            layout.addWidget(self.load_contract, row, 0)
            layout.addWidget(QLabel("Contract:"), row, 1)
            layout.addWidget(self.contract, row, 2)
            row += 1
        if include_site_ref:
            layout.addWidget(QLabel("Site Ref:"), row, 0)
            self.site_ref = QLineEdit()
            layout.addWidget(self.site_ref, row, 1, 1, 2)
            row += 1
        if include_region:
            layout.addWidget(QLabel("Region:"), row, 0)
            self.region = self._combo(["EMEA", "Asia", "LAC", "USA"], "EMEA")
            layout.addWidget(self.region, row, 1, 1, 2)
            row += 1
            self.compare_xml = QPushButton("Compare")
            self.validate_xml = QPushButton("Validate")
            for button in (self.compare_xml, self.validate_xml):
                button.setEnabled(False)
                button.setToolTip("Legacy XML comparison/validation requires the OFDA data and validation workflow.")
            layout.addWidget(self.compare_xml, row, 1)
            layout.addWidget(self.validate_xml, row, 2)
            row += 1
        if include_pbom:
            layout.addWidget(QLabel("PBOM Type:"), row, 0)
            self.pbom_type = self._combo(
                ["Item Price Extract", "PBOM Material Extract"],
                "Item Price Extract",
            )
            self.pbom_type.setEnabled(True)
            layout.addWidget(self.pbom_type, row, 1, 1, 2)
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
            self, "Add Item(s)", "Enter item codes (one per line or comma-separated):"
        )
        if not accepted:
            return
        existing = {self.item_list.item(i).text() for i in range(self.item_list.count())}
        for raw in text.replace(",", "\n").splitlines():
            item = raw.strip()
            if item and item not in existing:
                self.item_list.addItem(item)
                existing.add(item)

    def _remove_selected_items(self) -> None:
        for item in self.item_list.selectedItems():
            self.item_list.takeItem(self.item_list.row(item))

    def _show_params(self) -> None:
        """Display a read-only summary of the active legacy export parameters."""
        if self.tabs.currentIndex() == 0:
            mode = self.export_type.currentText()
        else:
            mode = self.tabs.tabText(self.tabs.currentIndex())
        lines = [
            f"Export tab: {self.tabs.tabText(self.tabs.currentIndex())}",
            f"Export type: {mode}",
            f"Site: {self.site.currentText() or '(not loaded)'}",
            f"Language: {self.language.currentText() or '(not loaded)'}",
            f"Other language: {self.other_language.currentText() or '(not loaded)'}",
            f"Catalogue: {self.catalogue.currentText() or '(not loaded)'}",
            f"Product-code filter: {self.product_line.currentText() if self.filter_product_code.isChecked() else '(disabled)'}",
            f"Currency: {self.currency.currentText() or '(not loaded)'}",
            f"Scope: {'specified item list' if self.list_check.isChecked() else 'item range' if self.range_check.isChecked() else 'product code' if self.filter_product_code.isChecked() else 'catalogue'}",
        ]
        if self.range_check.isChecked():
            lines.append(f"Item range: {self.min_item.text().strip()} through {self.max_item.text().strip()}")
        if self.list_check.isChecked():
            lines.append("Items: " + (", ".join(
                self.item_list.item(i).text() for i in range(self.item_list.count())
            ) or "(empty list)"))
        lines.append(f"Output folder: {self.output_directory.text().strip() or '(not set)'}")
        lines.append(f"Effective date: {self.effective_date.date().toString('yyyy-MM-dd')}")
        lines.append("")
        lines.append("Enabled options:")
        enabled = [checkbox.text() for checkbox in self.checks.values() if checkbox.isChecked()]
        enabled.extend(checkbox.text() for checkbox in (
            self.filter_product_code, self.range_check, self.list_check,
            self.export_all_in_site, self.export_bom_data,
        ) if checkbox.isChecked())
        lines.extend(f"• {name}" for name in enabled) if enabled else lines.append("• (none)")
        QMessageBox.information(self, "Export Parameters", "\\n".join(lines))

    def _update_scope_controls(self, source=None) -> None:
        # The legacy updateControls handler makes product, range and list modes
        # mutually exclusive. Normalize persisted combinations as well as clicks.
        if getattr(self, "_updating_scope_controls", False):
            return
        self._updating_scope_controls = True
        try:
            if source is not None and source.isChecked():
                for widget in (self.filter_product_code, self.range_check, self.list_check):
                    if widget is not source:
                        widget.setChecked(False)
            else:
                # Older saved settings may contain multiple checked modes.
                if self.list_check.isChecked():
                    self.filter_product_code.setChecked(False)
                    self.range_check.setChecked(False)
                elif self.range_check.isChecked():
                    self.filter_product_code.setChecked(False)
                    self.list_check.setChecked(False)
            ranged, listed = self.range_check.isChecked(), self.list_check.isChecked()
            self.min_item.setEnabled(ranged)
            self.max_item.setEnabled(ranged)
            self.item_list.setEnabled(listed)
            self.add_items.setEnabled(listed)
            self.remove_items.setEnabled(listed)
            self.clear_items.setEnabled(listed)
            self.product_line.setEnabled(self.filter_product_code.isChecked())
        finally:
            self._updating_scope_controls = False

    def _browse_output_directory(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select export output folder", self.output_directory.text())
        if selected:
            self.output_directory.setText(selected)

    def _validate_setup(self) -> None:
        from pathlib import Path
        from services.syteline_export.config import SyteLineExportConfig

        if not self.output_directory.text().strip():
            self.status.setText("Setup validation failed: choose an existing output folder.")
            return
        if self.list_check.isChecked():
            scope_mode = "list"
        elif self.range_check.isChecked():
            scope_mode = "range"
        elif self.filter_product_code.isChecked():
            scope_mode = "products"
        else:
            scope_mode = "catalogue"
        items = tuple(
            self.item_list.item(index).text().strip()
            for index in range(self.item_list.count())
            if self.item_list.item(index).text().strip()
        )
        options = set()
        # The item export is the primary output family in every scope mode.
        options.add("products")
        if self.range_check.isChecked():
            options.add("ranges")
        if self.list_check.isChecked():
            options.add("lists")
        if self.checks["base_prices"].isChecked():
            options.add("base_prices")
        if self.checks["ofda_export"].isChecked():
            options.add("ofda")
        if self.export_bom_data.isChecked():
            options.add("bom")
        config = SyteLineExportConfig(
            server=self._context.config.pdm_server,
            database=self._context.config.pdm_database,
            output_directory=Path(self.output_directory.text().strip()),
            site=str(self.site.currentData(Qt.ItemDataRole.UserRole + 1) or self.site.currentText()),
            product_line=self.product_line.currentText().split("  |  ", 1)[0].strip(),
            catalogue=self.catalogue.currentText().strip(),
            language=self.language.currentText().strip(),
            currency=self.currency.currentText().strip(),
            scope_mode=scope_mode,
            site_id=int(self.site.currentData() or 0),
            catalogue_id=int(self.catalogue.currentData() or 0),
            language_id=int(self.language.currentData() or 0),
            other_language_id=int(self.other_language.currentData() or 0),
            currency_id=int(self.currency.currentData() or 0),
            product_code_id=(
                int(self.product_line.currentData() or 0)
                if self.filter_product_code.isChecked() else -1
            ),
            effective_date=self.effective_date.date().toString("yyyy-MM-dd"),
            export_all_catalogues_in_site=self.export_all_in_site.isChecked(),
            active_only=self.checks["active_only"].isChecked(),
            export_base_prices=self.checks["base_prices"].isChecked(),
            export_bom_data=self.export_bom_data.isChecked(),
            extend_sp_options=self.checks["extend_sp_options"].isChecked(),
            length5_feats=self.checks["length_5_feats"].isChecked(),
            ignore_option_dependencies=self.checks["ignore_option_dependencies"].isChecked(),
            unique_components=self.checks["unique_phantoms"].isChecked(),
            plc_phantoms=self.checks["plc_prefix"].isChecked(),
            exclude_superproducts=(
                self.export_type.currentText() == "Exclude SuperProduct"
                if self.tabs.currentIndex() == 0
                else self.checks["csi_exclude_superproducts"].isChecked()
            ),
            superproducts_only=(
                self.export_type.currentText() == "SuperProducts Only"
                if self.tabs.currentIndex() == 0
                else self.checks["superproducts_only"].isChecked()
            ),
            flatten_fabrics=self.checks["flatten_fab"].isChecked(),
            include_url=self.checks["include_url"].isChecked(),
            short_description=self.checks["short_description"].isChecked(),
            export_mode=("syteline", "csi", "ofda", "other")[self.tabs.currentIndex()],
            min_item=self.min_item.text(),
            max_item=self.max_item.text(),
            item_list=items,
            options=frozenset(options),
        )
        errors = config.validate_for_execution()
        if errors:
            self.status.setText("Setup validation failed: " + " ".join(errors))
            return
        required_choices = (
            ("Site", self.site),
            ("Language", self.language),
            ("Other Language", self.other_language),
            ("Catalogue", self.catalogue),
            ("Currency", self.currency),
        )
        missing = [label for label, combo in required_choices if combo.currentData() is None]
        if missing:
            self.status.setText(
                "Setup validation failed: load/select live database choices for "
                + ", ".join(missing) + "."
            )
            return
        if self.filter_product_code.isChecked() and self.product_line.currentData() is None:
            self.status.setText("Setup validation failed: select a live product code or disable its filter.")
            return
        self.status.setText(
            "Setup is internally valid. Export is still disabled until item/material/BOM transformations "
            "and full legacy output parity are implemented and verified."
        )

    def _choose_multiple(self, kind: str, combo: QComboBox) -> None:
        """Show a checkable list for the legacy multi-site/language/currency controls."""
        if combo.count() == 0:
            self.status.setText("Load database choices before selecting multiple values.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle({"sites": "Select Sites", "languages": "Select Languages", "currencies": "Select Currencies"}[kind])
        layout = QVBoxLayout(dialog)
        listing = QListWidget(dialog)
        listing.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        selected_ids = {item_id for item_id, _ in self._multi_choices[kind]}
        for index in range(combo.count()):
            item = QListWidgetItem(combo.itemText(index), listing)
            item.setData(Qt.ItemDataRole.UserRole, combo.itemData(index))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if combo.itemData(index) in selected_ids
                else Qt.CheckState.Unchecked
            )
        layout.addWidget(listing)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.resize(300, 360)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._multi_choices[kind] = [
            (int(listing.item(i).data(Qt.ItemDataRole.UserRole)), listing.item(i).text())
            for i in range(listing.count())
            if listing.item(i).checkState() == Qt.CheckState.Checked
            and listing.item(i).data(Qt.ItemDataRole.UserRole) is not None
        ]
        button = {"sites": self.multi_sites, "languages": self.multi_languages, "currencies": self.multi_currencies}[kind]
        button.setText(f"{kind.title()} ({len(self._multi_choices[kind])})")
        self._save_settings()

    def _apply_authenticated_user_defaults(self) -> None:
        """Use available application authentication context without guessing IDs."""
        candidates = (
            self._context,
            getattr(self._context, "auth", None),
            getattr(self._context, "user", None),
            getattr(self._context, "session", None),
        )
        aliases = {
            "pdm_user_id": ("user_id", "UserId", "pdm_user_id"),
            "site_id": ("default_site_id", "DefaultSiteId", "site_id"),
            "language_id": ("default_language_id", "DefaultLanguageId", "language_id"),
            "currency_id": ("default_currency_id", "DefaultCurrencyId", "currency_id"),
            "catalogue_id": ("default_catalogue_id", "DefaultCatalogueId", "catalogue_id"),
        }
        for target, names in aliases.items():
            value = None
            for obj in candidates:
                if obj is None:
                    continue
                for name in names:
                    if isinstance(obj, dict) and name in obj:
                        value = obj[name]
                    elif hasattr(obj, name):
                        value = getattr(obj, name)
                    if value not in (None, ""):
                        break
                if value not in (None, ""):
                    break
            if value in (None, ""):
                continue
            if target == "pdm_user_id":
                self.pdm_user_id.setText(str(value))
                continue
            combo = {
                "site_id": self.site,
                "language_id": self.language,
                "currency_id": self.currency,
                "catalogue_id": self.catalogue,
            }[target]
            combo.setProperty("preferred_id", int(value))

    def _load_database_choices(self, *_args) -> None:
        """Load the same metadata families used by the legacy form, read-only."""
        self.load_database_choices.setEnabled(False)
        self.status.setText("Loading site, language and currency choices from PDM...")
        try:
            sites = self.metadata_service.sites()
            languages = self.metadata_service.languages()
            currencies = self.metadata_service.currencies()
            self._replace_choices(
                self.site, sites, self.settings.value(self.PREFIX + "site", "", type=str),
                preferred_id=self.site.property("preferred_id"),
            )
            self._replace_choices(
                self.language, languages, self.settings.value(self.PREFIX + "language", "", type=str),
                preferred_id=self.language.property("preferred_id"),
            )
            self._replace_choices(
                self.other_language, languages, self.settings.value(self.PREFIX + "other_language", "", type=str),
                preferred_id=self.other_language.property("preferred_id")
                if self.other_language.property("preferred_id") is not None
                else self.language.property("preferred_id"),
            )
            self._replace_choices(
                self.currency, currencies, self.settings.value(self.PREFIX + "currency", "", type=str),
                preferred_id=self.currency.property("preferred_id"),
            )
            user_text = self.pdm_user_id.text().strip()
            if user_text:
                try:
                    user_id = int(user_text)
                except ValueError as error:
                    raise ValueError("PDM User ID must be a positive integer.") from error
                if user_id < 1:
                    raise ValueError("PDM User ID must be a positive integer.")
                catalogues = self.metadata_service.catalogues(user_id)
                self._replace_choices(
                    self.catalogue, catalogues, self.settings.value(self.PREFIX + "catalogue", "", type=str),
                    preferred_id=self.catalogue.property("preferred_id"),
                )
            else:
                self.catalogue.clear()
                self.product_line.clear()
                self.status.setText(
                    "Sites, languages and currencies loaded. Enter the authenticated PDM User ID "
                    "to load only catalogues permitted for that user."
                )
            for button in (self.multi_sites, self.multi_languages, self.multi_currencies):
                button.setEnabled(True)
                button.setToolTip("Choose multiple database-backed values.")
            for kind, combo in (
                ("sites", self.site), ("languages", self.language), ("currencies", self.currency)
            ):
                available = {int(combo.itemData(i)): combo.itemText(i) for i in range(combo.count())
                             if combo.itemData(i) is not None}
                self._multi_choices[kind] = [
                    (item_id, label) for item_id, label in self._multi_choices[kind]
                    if item_id in available
                ]
                button = {"sites": self.multi_sites, "languages": self.multi_languages,
                          "currencies": self.multi_currencies}[kind]
                button.setText(f"{kind.title()} ({len(self._multi_choices[kind])})"
                               if self._multi_choices[kind] else f"{kind.title()}…")
            if self.site.currentData() is not None and self.catalogue.currentData() is not None:
                self._load_product_codes()
            self.status.setText(
                f"Loaded {len(sites)} sites, {len(languages)} languages and {len(currencies)} currencies. "
                + (f"Loaded {self.catalogue.count()} permitted catalogues." if user_text else
                   "Enter the authenticated PDM User ID and load again to retrieve permitted catalogues.")
            )
        except Exception as error:
            self.status.setText(f"Database choices could not be loaded: {error}")
        finally:
            self.load_database_choices.setEnabled(True)

    @staticmethod
    def _replace_choices(
        combo: QComboBox, choices, preferred_text: str = "", preferred_id=None
    ) -> None:
        current = combo.currentText() or preferred_text
        current_id = combo.currentData()
        combo.blockSignals(True)
        try:
            combo.clear()
            for choice in choices:
                combo.addItem(choice.label, userData=choice.id)
                combo.setItemData(combo.count() - 1, getattr(choice, "code", ""), Qt.ItemDataRole.UserRole + 1)
            index = combo.findData(preferred_id) if preferred_id not in (None, "") else -1
            if index < 0 and current_id is not None:
                index = combo.findData(current_id)
            if index < 0 and current:
                index = combo.findText(current)
            if index >= 0:
                combo.setCurrentIndex(index)
            elif combo.count():
                combo.setCurrentIndex(0)
        finally:
            combo.blockSignals(False)

    def _load_product_codes(self, *_args) -> None:
        site_id = self.site.currentData()
        catalogue_id = self.catalogue.currentData()
        if site_id is None or catalogue_id is None:
            return
        try:
            choices = self.metadata_service.product_codes(int(site_id), int(catalogue_id))
            current_id = self.product_line.currentData()
            preferred_text = self.settings.value(self.PREFIX + "product_line", "", type=str)
            self.product_line.blockSignals(True)
            try:
                self.product_line.clear()
                for choice in choices:
                    self.product_line.addItem(choice.label, userData=choice.id)
                index = self.product_line.findData(current_id)
                if index < 0 and preferred_text:
                    index = self.product_line.findText(preferred_text)
                if index >= 0:
                    self.product_line.setCurrentIndex(index)
                elif self.product_line.count():
                    self.product_line.setCurrentIndex(0)
            finally:
                self.product_line.blockSignals(False)
            self.status.setText(
                f"Loaded {len(choices)} product-code choices for the selected site and catalogue."
            )
        except Exception as error:
            self.product_line.clear()
            self.status.setText(f"Product-code choices could not be loaded: {error}")

    def _load_settings(self) -> None:
        for key, widget in [
            ("site", self.site), ("language", self.language), ("other_language", self.other_language),
            ("catalogue", self.catalogue), ("product_line", self.product_line), ("currency", self.currency),
            ("export_type", self.export_type), ("contract", self.contract),
        ]:
            widget.setCurrentText(self.settings.value(self.PREFIX + key, widget.currentText(), type=str))
        for key, widget in [
            ("min_item", self.min_item), ("max_item", self.max_item),
            ("catalogue_code_override", self.catalogue_code_override),
            ("output_directory", self.output_directory),
        ]:
            widget.setText(self.settings.value(self.PREFIX + key, widget.text(), type=str))
        self.pdm_user_id.setText(self.settings.value(self.PREFIX + "pdm_user_id", "", type=str))
        saved_date = self.settings.value(self.PREFIX + "effective_date", "", type=str)
        if saved_date:
            parsed_date = QDate.fromString(saved_date, "yyyy-MM-dd")
            if parsed_date.isValid():
                self.effective_date.setDate(parsed_date)
        for key, widget in [
            ("filter_product_code", self.filter_product_code),
            ("range_check", self.range_check), ("list_check", self.list_check),
            ("export_all_in_site", self.export_all_in_site), ("export_bom_data", self.export_bom_data),
        ]:
            widget.setChecked(self.settings.value(self.PREFIX + key, widget.isChecked(), type=bool))
        self.item_list.addItems(self.settings.value(self.PREFIX + "items", [], type=list))
        for kind in ("sites", "languages", "currencies"):
            saved = self.settings.value(self.PREFIX + "multi/" + kind, [], type=list)
            normalized = []
            for entry in saved:
                try:
                    normalized.append((int(entry[0]), str(entry[1])))
                except (TypeError, ValueError, IndexError):
                    continue
            self._multi_choices[kind] = normalized
            button = {
                "sites": self.multi_sites,
                "languages": self.multi_languages,
                "currencies": self.multi_currencies,
            }[kind]
            if normalized:
                button.setText(f"{kind.title()} ({len(normalized)})")
        if hasattr(self, "site_ref"):
            self.site_ref.setText(self.settings.value(self.PREFIX + "site_ref", "", type=str))
        if hasattr(self, "region"):
            self.region.setCurrentText(self.settings.value(self.PREFIX + "region", "EMEA", type=str))
        if hasattr(self, "pbom_type"):
            self.pbom_type.setCurrentText(self.settings.value(self.PREFIX + "pbom_type", "", type=str))
        for key, widget in self.checks.items():
            widget.setChecked(self.settings.value(self.PREFIX + "options/" + key, widget.isChecked(), type=bool))

    def _connect_autosave(self) -> None:
        for widget in [
            self.site, self.language, self.other_language, self.catalogue, self.product_line,
            self.currency, self.export_type, self.contract,
        ]:
            widget.currentTextChanged.connect(self._save_settings)
        for widget in [self.min_item, self.max_item, self.catalogue_code_override, self.output_directory]:
            widget.textChanged.connect(self._save_settings)
        self.effective_date.dateChanged.connect(self._save_settings)
        for widget in [
            self.filter_product_code, self.range_check, self.list_check,
            self.export_all_in_site, self.export_bom_data, *self.checks.values(),
        ]:
            widget.toggled.connect(self._save_settings)
        for attr in ("site_ref",):
            if hasattr(self, attr):
                getattr(self, attr).textChanged.connect(self._save_settings)
        for attr in ("region", "pbom_type"):
            if hasattr(self, attr):
                getattr(self, attr).currentTextChanged.connect(self._save_settings)
        self.item_list.model().rowsInserted.connect(self._save_settings)
        self.item_list.model().rowsRemoved.connect(self._save_settings)
        for widget in (self.filter_product_code, self.range_check, self.list_check):
            widget.toggled.connect(lambda checked, source=widget: self._update_scope_controls(source if checked else None))
        self.site.currentIndexChanged.connect(self._load_product_codes)
        self.catalogue.currentIndexChanged.connect(self._load_product_codes)
        self.pdm_user_id.textChanged.connect(self._save_settings)

    def _save_settings(self, *_args) -> None:
        for key, widget in [
            ("site", self.site), ("language", self.language), ("other_language", self.other_language),
            ("catalogue", self.catalogue), ("product_line", self.product_line), ("currency", self.currency),
            ("export_type", self.export_type), ("contract", self.contract),
        ]:
            self.settings.setValue(self.PREFIX + key, widget.currentText())
        for key, widget in [
            ("min_item", self.min_item), ("max_item", self.max_item),
            ("catalogue_code_override", self.catalogue_code_override),
            ("output_directory", self.output_directory),
        ]:
            self.settings.setValue(self.PREFIX + key, widget.text())
        self.settings.setValue(self.PREFIX + "pdm_user_id", self.pdm_user_id.text().strip())
        self.settings.setValue(self.PREFIX + "effective_date", self.effective_date.date().toString("yyyy-MM-dd"))
        for key, widget in [
            ("filter_product_code", self.filter_product_code),
            ("range_check", self.range_check), ("list_check", self.list_check),
            ("export_all_in_site", self.export_all_in_site), ("export_bom_data", self.export_bom_data),
        ]:
            self.settings.setValue(self.PREFIX + key, widget.isChecked())
        self.settings.setValue(self.PREFIX + "items", [
            self.item_list.item(i).text() for i in range(self.item_list.count())
        ])
        for kind, selected in self._multi_choices.items():
            self.settings.setValue(self.PREFIX + "multi/" + kind, selected)
        if hasattr(self, "site_ref"):
            self.settings.setValue(self.PREFIX + "site_ref", self.site_ref.text())
        if hasattr(self, "region"):
            self.settings.setValue(self.PREFIX + "region", self.region.currentText())
        if hasattr(self, "pbom_type"):
            self.settings.setValue(self.PREFIX + "pbom_type", self.pbom_type.currentText())
        for key, widget in self.checks.items():
            self.settings.setValue(self.PREFIX + "options/" + key, widget.isChecked())
        self.settings.sync()
