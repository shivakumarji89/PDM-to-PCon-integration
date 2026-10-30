"""QA → Article OBX Generator (pCon SDK) workspace.

Automatic valid-SKU generation: the user picks manufacturer, program and base
articles and clicks *Generate Valid SKUs*. The MK OBX Generator plugin hosted
in pCon.planner then enumerates every configuration pCon's own product data
accepts (live value sets after each selection), creates the configured article
instances and exports them to one OBX. Inspecting properties is optional and
only serves to pin or exclude properties. See
``docs/04_Reference/pCon/SDK_Article_OBX_Generator.md``.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.pcon_sdk_obx import (
    BridgeSettings,
    PconCatalogService,
    PconConfigurationService,
    PconObxGenerationService,
    PconPluginBridge,
    PlanValidationError,
    ReferenceObxComparer,
)
from services.pcon_sdk_obx.configuration_service import MODE_DEFAULT, MODE_FIXED, MODE_VARY
from services.pcon_sdk_obx.protocol import (
    ArticleProperty,
    CatalogArticle,
    CatalogPackage,
    PropertyRule,
)
from ui import theme
from ui.components import SectionHeader
from ui.components._styles import primary_button_qss, secondary_button_qss
from ui.dialogs.progress_dialog import ProgressDialog
from ui.pages.base_page import BasePage
from ui.workers.background_task import ReportedTask

_MODE_LABELS = {MODE_VARY: "Vary (auto)", MODE_FIXED: "Fixed value", MODE_DEFAULT: "Keep pCon default"}
_SETTINGS_PREFIX = "pcon_sdk_obx/"


class PconArticleObxGeneratorPage(BasePage):
    """Standalone QA workspace; needs pCon.planner, not a PDM product."""

    def __init__(self, context, parent: QWidget | None = None,
                 bridge: PconPluginBridge | None = None) -> None:
        super().__init__(
            title="Article OBX Generator (pCon SDK)",
            description=(
                "Select base articles and generate every valid SKU automatically. pCon.planner "
                "evaluates relations, dependent properties and constraints through the Plugin SDK; "
                "the valid configured articles are exported to one OBX."
            ),
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._settings = QSettings()
        self._bridge = bridge or PconPluginBridge(self._load_bridge_settings())
        self._catalog = PconCatalogService(self._bridge)
        self._configuration = PconConfigurationService()
        self._generation = PconObxGenerationService(self._bridge)
        self._comparer = ReferenceObxComparer()

        self._packages: list[CatalogPackage] = []
        self._articles: list[CatalogArticle] = []
        self._properties: list[ArticleProperty] = []
        self._inspected_article: CatalogArticle | None = None
        self._outcome = None
        self._run: ReportedTask | None = None

        self._build_content()
        self.refresh()

    # ------------------------------------------------------------------ build
    def _build_content(self) -> None:
        self.add_content(self._build_connection_box())
        self.add_content(self._build_catalogue_box())
        properties = self._build_properties_box()
        self._normalize_group_boxes(properties)
        self._content.addWidget(properties, 1)
        results = self._build_generation_box()
        self._normalize_group_boxes(results)
        self._content.addWidget(results, 1)

    def _button(self, text: str, slot, *, primary: bool = False) -> QPushButton:
        button = QPushButton(text, self)
        name = "pconObx" + "".join(part.capitalize() for part in text.replace("…", "").split())
        button.setObjectName(name)
        button.setStyleSheet(primary_button_qss(name) if primary else secondary_button_qss(name))
        button.clicked.connect(slot)
        return button

    def _build_connection_box(self) -> QGroupBox:
        box = QGroupBox("pCon.planner Connection", self)
        layout = QVBoxLayout(box)
        layout.addWidget(SectionHeader(
            "Plugin status",
            "The MK OBX Generator plugin must be installed in pCon.planner and pCon.planner must be running.",
        ))
        self._connection_status = QLabel("", self)
        self._connection_status.setWordWrap(True)
        layout.addWidget(self._connection_status)

        row = QHBoxLayout()
        row.addWidget(QLabel("Job folder:"))
        self._job_dir_label = QLabel(str(self._bridge.job_dir), self)
        self._job_dir_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(self._job_dir_label, 1)
        self._check_button = self._button("Check Connection", self._check_connection)
        self._launch_button = self._button("Launch pCon.planner", self._launch_planner)
        self._install_button = self._button("Install Plugin", self._install_plugin)
        row.addWidget(self._check_button)
        row.addWidget(self._launch_button)
        row.addWidget(self._install_button)
        layout.addLayout(row)
        return box

    def _build_catalogue_box(self) -> QGroupBox:
        box = QGroupBox("Catalogue", self)
        layout = QVBoxLayout(box)
        row = QHBoxLayout()
        row.addWidget(QLabel("Manufacturer:"))
        self._manufacturer = QComboBox(self)
        self._manufacturer.setMinimumWidth(180)
        self._manufacturer.currentIndexChanged.connect(self._on_manufacturer_changed)
        row.addWidget(self._manufacturer)
        row.addWidget(QLabel("Program:"))
        self._program = QComboBox(self)
        self._program.setMinimumWidth(220)
        self._program.currentIndexChanged.connect(self._on_program_changed)
        row.addWidget(self._program)
        row.addWidget(QLabel("Series:"))
        self._series = QComboBox(self)
        self._series.setMinimumWidth(90)
        row.addWidget(self._series)
        row.addStretch(1)
        self._load_catalog_button = self._button("Load Catalogue", self._load_catalogue)
        self._load_articles_button = self._button("Load Articles", self._load_articles)
        row.addWidget(self._load_catalog_button)
        row.addWidget(self._load_articles_button)
        layout.addLayout(row)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self._article_filter = QLineEdit(self)
        self._article_filter.setPlaceholderText("Article number or label")
        self._article_filter.textChanged.connect(self._populate_articles)
        filter_row.addWidget(self._article_filter, 1)
        self._article_count = QLabel("0 articles", self)
        filter_row.addWidget(self._article_count)
        layout.addLayout(filter_row)

        self._article_table = QTableWidget(self)
        self._article_table.setColumnCount(4)
        self._article_table.setHorizontalHeaderLabels(["Article", "Variant Code", "Label", "Package"])
        self._article_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._article_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._article_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._article_table.setAlternatingRowColors(True)
        self._article_table.verticalHeader().setVisible(False)
        header = self._article_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._article_table.setMinimumHeight(140)
        self._article_table.setMaximumHeight(220)
        layout.addWidget(self._article_table)
        return box

    def _build_properties_box(self) -> QGroupBox:
        box = QGroupBox("Configuration Scope (optional)", self)
        layout = QVBoxLayout(box)
        row = QHBoxLayout()
        self._inspect_button = self._button("Inspect Properties", self._inspect_properties)
        self._inspect_button.setToolTip(
            "Optional: read the live properties of the first selected article to pin a value "
            "or exclude a property. Without this, every configurable property is varied.")
        row.addWidget(self._inspect_button)
        self._inspected_label = QLabel(
            "All configurable properties are varied automatically. Inspect to pin or exclude properties.",
            self)
        self._inspected_label.setWordWrap(True)
        row.addWidget(self._inspected_label, 1)
        row.addWidget(QLabel("Max configurations:"))
        self._max_configurations = QSpinBox(self)
        self._max_configurations.setRange(1, PconConfigurationService.MAX_CONFIGURATIONS_LIMIT)
        self._max_configurations.setValue(int(self._settings.value(_SETTINGS_PREFIX + "maxConfigurations", 500)))
        self._max_configurations.valueChanged.connect(self._update_estimate)
        row.addWidget(self._max_configurations)
        layout.addLayout(row)

        self._property_table = QTableWidget(self)
        self._property_table.setColumnCount(6)
        self._property_table.setHorizontalHeaderLabels(
            ["Key", "Name", "Current Value", "Mode", "Fixed Value", "Choices"])
        self._property_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._property_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._property_table.setAlternatingRowColors(True)
        self._property_table.verticalHeader().setVisible(False)
        header = self._property_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._property_table.setMinimumHeight(160)
        self._property_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._property_table, 1)

        self._estimate_label = QLabel("", self)
        self._estimate_label.setWordWrap(True)
        layout.addWidget(self._estimate_label)
        return box

    def _build_generation_box(self) -> QGroupBox:
        box = QGroupBox("OBX Generation", self)
        layout = QVBoxLayout(box)
        row = QHBoxLayout()
        row.addWidget(QLabel("Output OBX:"))
        self._output_path = QLineEdit(self)
        self._output_path.setText(self._settings.value(_SETTINGS_PREFIX + "outputPath", "", type=str))
        self._output_path.setPlaceholderText("C:\\path\\to\\generated.obx")
        row.addWidget(self._output_path, 1)
        row.addWidget(self._button("Browse…", self._browse_output))
        self._discard_planning = QCheckBox("Discard unsaved pCon.planner planning", self)
        self._discard_planning.setToolTip(
            "Generation starts a new planning in pCon.planner. Tick to allow discarding unsaved work.")
        row.addWidget(self._discard_planning)
        self._generate_button = self._button("Generate Valid SKUs", self._generate, primary=True)
        self._generate_button.setToolTip(
            "Enumerate every valid configuration of the selected base articles in pCon.planner, "
            "create the configured articles and export them to the OBX file.")
        row.addWidget(self._generate_button)
        layout.addLayout(row)

        self._generation_status = QLabel("No generation run yet.", self)
        self._generation_status.setWordWrap(True)
        layout.addWidget(self._generation_status)

        self._result_table = QTableWidget(self)
        self._result_table.setColumnCount(7)
        self._result_table.setHorizontalHeaderLabels(
            ["#", "Base Article", "Final Article", "Variant Code", "Configuration", "Price", "Status"])
        self._result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._result_table.setAlternatingRowColors(True)
        self._result_table.verticalHeader().setVisible(False)
        header = self._result_table.horizontalHeader()
        for column in (0, 1, 2, 3, 5, 6):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._result_table.setMinimumHeight(160)
        self._result_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._result_table, 1)

        footer = QHBoxLayout()
        self._validation_label = QLabel("", self)
        self._validation_label.setWordWrap(True)
        footer.addWidget(self._validation_label, 1)
        self._compare_button = self._button("Compare with Reference OBX…", self._compare_reference)
        self._compare_button.setEnabled(False)
        self._compare_button.setToolTip(
            "Compare the generated final article numbers with an OBX pCon.planner produced independently.")
        footer.addWidget(self._compare_button)
        self._open_folder_button = self._button("Open Output Folder", self._open_output_folder)
        self._open_folder_button.setEnabled(False)
        footer.addWidget(self._open_folder_button)
        layout.addLayout(footer)
        return box

    # --------------------------------------------------------------- settings
    def _load_bridge_settings(self) -> BridgeSettings:
        settings = BridgeSettings()
        job_dir = self._settings.value(_SETTINGS_PREFIX + "jobDir", "", type=str)
        if job_dir:
            settings.job_dir = Path(job_dir)
        planner = self._settings.value(_SETTINGS_PREFIX + "plannerExe", "", type=str)
        if planner:
            settings.planner_exe = planner
        return settings

    def _save_settings(self) -> None:
        self._settings.setValue(_SETTINGS_PREFIX + "outputPath", self._output_path.text())
        self._settings.setValue(_SETTINGS_PREFIX + "maxConfigurations", self._max_configurations.value())

    # ------------------------------------------------------------- lifecycle
    def refresh(self) -> None:
        self._update_connection_status()

    def is_ready(self) -> bool:
        return True

    def _update_connection_status(self) -> None:
        alive = self._bridge.is_plugin_alive()
        text = self._bridge.describe_status()
        if not self._bridge.plugin_installed():
            text += " Plugin is not installed in the user plugin folder."
        self._connection_status.setText(text)
        self._connection_status.setStyleSheet(
            f"color: {theme.COLOR_OK if alive else theme.COLOR_WARNING};")
        for button in (self._load_catalog_button, self._load_articles_button,
                       self._inspect_button, self._generate_button):
            button.setEnabled(alive and self._run is None)

    # --------------------------------------------------------------- helpers
    def _progress_monitor(self) -> ProgressDialog:
        main = self.window()
        if hasattr(main, "progress_monitor"):
            return main.progress_monitor()
        dialog = getattr(self, "_progress_dialog", None)
        if dialog is None:
            dialog = ProgressDialog(self)
            self._progress_dialog = dialog
        return dialog

    def _start(self, title: str, work, finished, *, steps: int = 1, subject: str = "") -> None:
        """Run ``work(reporter)`` off the GUI thread with the shared progress dialog."""
        if self._run is not None and self._run.active:
            return
        run = ReportedTask(self)
        self._run = run
        reporter = run.reporter
        dialog = self._progress_monitor()
        dialog.bind(reporter)
        reporter.begin(max(1, steps), title=title, subject=subject)
        dialog.show()
        dialog.raise_()
        self._update_connection_status()

        def _done(result) -> None:
            self._run = None
            try:
                finished(result)
            finally:
                self._update_connection_status()

        def _failed(message: str) -> None:
            self._run = None
            self._update_connection_status()
            self._generation_status.setText(f"{title} failed: {message}")
            QMessageBox.critical(self, title, f"{title} failed:\n\n{message}")

        def _cancelled(message: str) -> None:
            self._run = None
            self._update_connection_status()
            self._generation_status.setText(message)

        run.start(lambda emit: work(reporter), finished=_done, failed=_failed, cancelled=_cancelled)

    def _selected_package(self) -> CatalogPackage | None:
        return self._program.currentData()

    def _selected_articles(self) -> list[CatalogArticle]:
        rows = sorted({index.row() for index in self._article_table.selectedIndexes()})
        selected = []
        for row in rows:
            item = self._article_table.item(row, 0)
            article = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
            if article is not None:
                selected.append(article)
        return selected

    # ------------------------------------------------------------- connection
    def _check_connection(self) -> None:
        self._update_connection_status()
        if self._bridge.is_plugin_alive():
            try:
                info = self._bridge.ping()
            except Exception as exc:  # noqa: BLE001 - shown to the user
                QMessageBox.warning(self, "Check Connection", str(exc))
                return
            languages = ", ".join(info.get("languages", []) or []) or "n/a"
            self._connection_status.setText(
                f"{self._bridge.describe_status()} Article languages: {languages}.")

    def _launch_planner(self) -> None:
        try:
            self._bridge.launch_planner()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Launch pCon.planner", str(exc))
            return
        self._generation_status.setText(
            "pCon.planner is starting. Use Check Connection once it is ready (the plugin "
            "reports after the application finishes loading).")

    def _install_plugin(self) -> None:
        try:
            target = self._bridge.install_plugin()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Install Plugin", str(exc))
            return
        QMessageBox.information(
            self, "Install Plugin",
            f"Plugin copied to:\n{target}\n\nRestart pCon.planner to load it. The plugin only loads "
            "with a registered hash or a Plugin SDK developer licence (see the SDK reference document).")
        self._update_connection_status()

    # -------------------------------------------------------------- catalogue
    def _load_catalogue(self) -> None:
        def work(reporter):
            reporter.note("Reading registered OFML packages from pCon.planner")
            packages = self._catalog.list_packages()
            reporter.advance("Packages loaded")
            return packages

        self._start("Loading catalogue", work, self._on_catalogue_loaded)

    def _on_catalogue_loaded(self, packages: list[CatalogPackage]) -> None:
        self._packages = packages
        self._manufacturer.blockSignals(True)
        self._manufacturer.clear()
        for manufacturer_id, name in self._catalog.manufacturers(packages):
            self._manufacturer.addItem(f"{name} ({manufacturer_id})", manufacturer_id)
        self._manufacturer.blockSignals(False)
        self._on_manufacturer_changed()
        self._generation_status.setText(
            f"Catalogue loaded: {len(packages)} package(s), "
            f"{self._manufacturer.count()} manufacturer(s).")

    def _on_manufacturer_changed(self) -> None:
        manufacturer_id = self._manufacturer.currentData()
        self._program.blockSignals(True)
        self._program.clear()
        for package in self._catalog.programs_for(self._packages, manufacturer_id or ""):
            self._program.addItem(package.label, package)
        self._program.blockSignals(False)
        self._on_program_changed()

    def _on_program_changed(self) -> None:
        package = self._selected_package()
        self._series.clear()
        if package is not None:
            self._series.addItem("(by package)", "")
            for program_id in package.program_ids:
                self._series.addItem(program_id, program_id)
            if len(package.program_ids) == 1:
                self._series.setCurrentIndex(1)
        self._articles = []
        self._populate_articles()

    def _load_articles(self) -> None:
        package = self._selected_package()
        if package is None:
            QMessageBox.information(self, "Load Articles", "Load the catalogue and choose a program first.")
            return

        def work(reporter):
            reporter.note(f"Reading catalogue items of {package.label}")
            articles = self._catalog.list_articles(package)
            reporter.advance("Articles loaded")
            return articles

        self._start("Loading articles", work, self._on_articles_loaded, subject=package.label)

    def _on_articles_loaded(self, articles: list[CatalogArticle]) -> None:
        self._articles = articles
        self._populate_articles()

    def _populate_articles(self) -> None:
        needle = self._article_filter.text().strip().lower()
        rows = [
            a for a in self._articles
            if not needle or needle in a.article_number.lower() or needle in a.label.lower()
        ]
        self._article_table.setRowCount(len(rows))
        for row, article in enumerate(rows):
            values = [article.article_number, article.variant_code or "—", article.label, article.package_name]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(article.description or value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, article)
                self._article_table.setItem(row, column, item)
        self._article_count.setText(f"{len(rows)} of {len(self._articles)} articles")

    # ------------------------------------------------------------- properties
    def _inspect_properties(self) -> None:
        package = self._selected_package()
        selected = self._selected_articles()
        if package is None or not selected:
            QMessageBox.information(self, "Inspect Properties", "Select at least one article first.")
            return
        article = selected[0]
        series_id = self._series.currentData() or ""

        def work(reporter):
            reporter.note(f"Instantiating {article.article_number} in pCon.planner")
            info, properties = self._catalog.describe_article(package, article, series_id)
            reporter.advance("Properties read")
            return info, properties

        self._start("Inspecting properties", work,
                     lambda result: self._on_properties_loaded(article, *result),
                     subject=article.article_number)

    def _on_properties_loaded(self, article: CatalogArticle, info, properties: list[ArticleProperty]) -> None:
        self._inspected_article = article
        self._properties = properties
        selectable = {p.key for p in self._configuration.selectable_properties(properties)}
        self._inspected_label.setText(
            f"Inspected {article.article_number}: default final article {info.final_number or '—'}, "
            f"{len(properties)} properties, {len(selectable)} configurable (varied unless pinned/excluded)."
        )
        self._property_table.setRowCount(len(properties))
        for row, prop in enumerate(properties):
            key_item = QTableWidgetItem(prop.key)
            key_item.setData(Qt.ItemDataRole.UserRole, prop)
            self._property_table.setItem(row, 0, key_item)
            self._property_table.setItem(row, 1, QTableWidgetItem(prop.name or prop.key))
            self._property_table.setItem(row, 2, QTableWidgetItem(prop.value_text or prop.value_key))
            mode = QComboBox(self._property_table)
            for mode_key, label in _MODE_LABELS.items():
                mode.addItem(label, mode_key)
            mode.setEnabled(prop.key in selectable)
            mode.currentIndexChanged.connect(self._update_estimate)
            self._property_table.setCellWidget(row, 3, mode)
            value = QComboBox(self._property_table)
            for choice in prop.choices:
                value.addItem(choice.text or choice.key, choice.key)
            if prop.value_key:
                index = value.findData(prop.value_key)
                if index >= 0:
                    value.setCurrentIndex(index)
            value.setEnabled(prop.key in selectable)
            self._property_table.setCellWidget(row, 4, value)
            self._property_table.setItem(row, 5, QTableWidgetItem(str(len(prop.choices))))
        self._update_estimate()

    def _current_rules(self) -> list[PropertyRule]:
        rules: list[PropertyRule] = []
        for row in range(self._property_table.rowCount()):
            key_item = self._property_table.item(row, 0)
            mode_widget = self._property_table.cellWidget(row, 3)
            value_widget = self._property_table.cellWidget(row, 4)
            if key_item is None or mode_widget is None:
                continue
            if not mode_widget.isEnabled():
                continue  # not configurable: pCon keeps it, no instruction needed
            mode = mode_widget.currentData() or MODE_VARY
            if mode == MODE_VARY:
                continue  # automatic mode varies it anyway
            value_key = value_widget.currentData() if value_widget is not None else ""
            rules.append(PropertyRule(key=key_item.text(), mode=mode,
                                      value_key=value_key or "" if mode == MODE_FIXED else ""))
        return rules

    def _update_estimate(self) -> None:
        try:
            rules = tuple(self._current_rules())
        except ValueError as exc:
            self._estimate_label.setText(str(exc))
            return
        estimate = self._configuration.estimate(self._properties, rules, vary_all=True)
        articles = max(1, len(self._selected_articles()))
        bound = estimate.upper_bound * articles
        self._estimate_label.setText(
            f"{estimate.varied} varied propert{'y' if estimate.varied == 1 else 'ies'}; naive upper bound "
            f"{bound} configuration(s) for {articles} article(s). pCon.planner prunes values its relations "
            f"exclude and may reveal further dependent properties; generation stops at "
            f"{self._max_configurations.value()}."
        )

    # ------------------------------------------------------------- generation
    def _browse_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save generated OBX", self._output_path.text() or "generated.obx",
            "OBX files (*.obx)")
        if path:
            self._output_path.setText(path)

    def _generate(self) -> None:
        package = self._selected_package()
        articles = self._selected_articles()
        if package is None or not articles:
            QMessageBox.information(self, "Generate OBX", "Select a program and at least one article.")
            return
        rules = self._current_rules()
        if self._inspected_article is not None and rules:
            inspected = self._inspected_article.article_number
            if any(a.article_number != inspected for a in articles):
                answer = QMessageBox.question(
                    self, "Generate Valid SKUs",
                    f"Pinned/excluded properties were inspected on {inspected} but other articles are "
                    "selected. Rules for properties an article does not offer are skipped. Continue?")
                if answer != QMessageBox.StandardButton.Yes:
                    return
        try:
            plan = self._configuration.build_plan(
                package=package, series_id=self._series.currentData() or "",
                articles=articles, properties=self._properties, rules=rules,
                output_path=self._output_path.text().strip(),
                max_configurations=self._max_configurations.value(),
                discard_unsaved_planning=self._discard_planning.isChecked(),
                vary_all=True, deduplicate=True,
            )
        except (PlanValidationError, ValueError) as exc:
            QMessageBox.warning(self, "Generate Valid SKUs", str(exc))
            return
        if self._properties and self._inspected_article is not None:
            estimate = self._configuration.estimate(self._properties, plan.rules, vary_all=True)
            bound = estimate.upper_bound * len(articles)
            if bound > plan.max_configurations:
                answer = QMessageBox.question(
                    self, "Generate Valid SKUs",
                    f"The naive upper bound is {bound} configuration(s) but generation stops at "
                    f"{plan.max_configurations}. pCon.planner usually prunes far below the bound. "
                    "Continue with the current limit?")
                if answer != QMessageBox.StandardButton.Yes:
                    return
        self._save_settings()
        self._result_table.setRowCount(0)
        self._validation_label.setText("")
        self._open_folder_button.setEnabled(False)
        self._compare_button.setEnabled(False)
        self._generation_status.setText("Enumerating valid SKUs in pCon.planner…")

        def work(reporter):
            reporter.note("Waiting for pCon.planner to configure articles")
            return self._generation.generate(plan, reporter=reporter)

        self._start("Generating valid SKUs", work, self._on_generated,
                     steps=plan.max_configurations,
                     subject=", ".join(a.article_number for a in articles)[:80])

    def _on_generated(self, outcome) -> None:
        self._outcome = outcome
        result = outcome.result
        self._result_table.setRowCount(len(result.configurations))
        for row, config in enumerate(result.configurations):
            price = ""
            if config.sales_price is not None:
                price = f"{config.sales_price:.2f} {config.currency}".strip()
            elif config.purchase_price is not None:
                price = f"{config.purchase_price:.2f} {config.currency}".strip()
            values = [str(config.index), config.base_article, config.final_article,
                      config.variant_code or "—", config.configuration_text, price,
                      config.status if not config.message else f"{config.status}: {config.message}"]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self._result_table.setItem(row, column, item)

        summary = (
            f"Generated {result.generated} valid unique SKU(s) from {result.visited} evaluated node(s)"
            f"{', ' + str(result.skipped) + ' invalid/skipped' if result.skipped else ''}"
            f"{', ' + str(result.duplicates) + ' duplicate SKU(s) removed' if result.duplicates else ''}"
            f"{' (limit reached)' if result.truncated else ''}"
            f"{' (cancelled)' if result.cancelled else ''}; "
            f"basket items reported by pCon: {result.basket_items}."
        )
        if result.exported:
            summary += f" OBX: {result.output_path}"
        self._generation_status.setText(summary)
        self._generation_status.setStyleSheet(
            f"color: {theme.COLOR_OK if outcome.success else theme.COLOR_ERROR};")

        parts: list[str] = []
        validation = outcome.validation
        if validation is not None:
            parts.append(
                f"Validation: {validation.article_lines} article line(s) parsed, "
                f"{validation.expected_articles} expected"
                f"{', well-formed XML' if validation.well_formed else ', XML not well-formed'}."
            )
            if validation.missing_final_articles:
                parts.append("Missing: " + ", ".join(validation.missing_final_articles[:10]))
            if validation.lines_without_price:
                parts.append(f"{validation.lines_without_price} line(s) have no sale price.")
        parts.extend(outcome.errors)
        parts.extend(result.warnings[:5])
        self._validation_label.setText(" ".join(parts))
        exists = bool(result.output_path) and Path(result.output_path).exists()
        self._open_folder_button.setEnabled(exists)
        self._compare_button.setEnabled(exists)

    def _compare_reference(self) -> None:
        if self._outcome is None or not self._outcome.result.output_path:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Reference OBX generated by pCon.planner", "", "OBX files (*.obx);;All files (*.*)")
        if not path:
            return
        comparison = self._comparer.compare(self._outcome.result.output_path, path)
        self._last_comparison = comparison
        if comparison.problems:
            text = " ".join(comparison.problems)
        else:
            text = (f"Reference comparison: {len(comparison.matched)} matched, "
                    f"{len(comparison.missing_in_generated)} only in reference, "
                    f"{len(comparison.extra_in_generated)} only generated "
                    f"(reference {comparison.reference_lines} lines, generated {comparison.generated_lines}).")
            if comparison.missing_in_generated:
                text += " Only in reference: " + ", ".join(comparison.missing_in_generated[:10])
            if comparison.extra_in_generated:
                text += " Only generated: " + ", ".join(comparison.extra_in_generated[:10])
        self._validation_label.setText(text)
        self._validation_label.setStyleSheet(
            f"color: {theme.COLOR_OK if comparison.identical else theme.COLOR_WARNING};")

    def _open_output_folder(self) -> None:
        path = self._outcome.result.output_path if self._outcome else self._output_path.text()
        folder = Path(path).parent if path else None
        if folder is None or not folder.is_dir():
            return
        if os.name == "nt":
            subprocess.Popen(["explorer", str(folder)])
