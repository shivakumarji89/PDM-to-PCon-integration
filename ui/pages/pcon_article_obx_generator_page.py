"""QA → Article OBX Generator (OCD Engine) workspace.

Fully standalone: the OCD repository folder is read directly (``OcdCatalogueService``), valid SKUs
are enumerated by the OCD Engine (``OcdArticleGenerator``) and exported with the existing OBX
serializer (``ocd_repository_obx``). No pCon plugin, SDK, launcher or running pCon.planner is involved.
See ``docs/04_Reference/pCon/Article_OBX_Generator/``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QDate, QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QToolButton,
    QSizePolicy,
    QSpinBox,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.article_obx.ocd_repository_obx import export_obx
from services.article_obx.validator_handoff import shared_handoff
from services.ocd_engine.catalogue import (
    CatalogueScan,
    OcdArticle,
    OcdCatalogueService,
    recall_loaded,
    remember_loaded,
    OcdProgram,
)
from services.ocd_engine.generator import (
    MODE_DEFAULT,
    MODE_FIXED,
    MODE_VARY,
    ArticleDescription,
    GenerationError,
    GenerationOutcome,
    OcdArticleGenerator,
    PropertyInfo,
    PropertyRule,
)
from ui import theme
from ui.components._styles import primary_button_qss, secondary_button_qss
from ui.dialogs.progress_dialog import ProgressDialog
from ui.pages.base_page import BasePage
from ui.pages.sku_results_model import SkuResultsModel
from ui.workers.background_task import ReportedTask

_MODE_LABELS = {MODE_VARY: "Vary (auto)", MODE_FIXED: "Fixed value", MODE_DEFAULT: "Default value"}
_SETTINGS_PREFIX = "pcon_sdk_obx/"   # legacy key prefix, kept so saved settings still apply



_FABRIC_AUTOMATIC = "Automatic"


class PconArticleObxGeneratorPage(BasePage):
    """Standalone QA workspace; needs neither pCon.planner nor a PDM product.

    ``catalogue`` and ``generator_factory`` let callers substitute the repository readers.
    """

    def __init__(self, context, parent: QWidget | None = None,
                 catalogue: OcdCatalogueService | None = None,
                 generator_factory: Callable[[Path], OcdArticleGenerator] | None = None) -> None:
        super().__init__(
            title="Article OBX Generator (OCD Engine)",
            description=(
                "Select base articles and generate every valid SKU automatically. The standalone "
                "OCD Engine evaluates relations, dependent properties and constraints; "
                "the valid configured articles are exported to one OBX."
            ),
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._settings = QSettings()
        self._catalogue_override = catalogue
        self._generator_factory = generator_factory or OcdArticleGenerator
        self._generators: dict[Path, OcdArticleGenerator] = {}
        self._scan: CatalogueScan | None = None
        self._catalogue_reader: OcdCatalogueService | None = None
        self._catalogue_poll = QTimer(self)
        self._catalogue_poll.setInterval(300_000)
        self._catalogue_poll.timeout.connect(self._poll_catalogue)
        self._loaded_key: tuple[str, str] | None = None    # (root, fingerprint) of the catalogue now shown
        self._check_run: ReportedTask | None = None        # the silent "has the repository changed?" check

        self._programs: list[OcdProgram] = []
        self._articles: list[OcdArticle] = []
        self._properties: list[PropertyInfo] = []
        self._outcome: GenerationOutcome | None = None
        self._outcome_program: OcdProgram | None = None
        self._outcome_price_date = ""
        self._validator_handoff = shared_handoff()
        self._run: ReportedTask | None = None

        self._build_content()
        self._set_status(self._catalogue_status, "Loading OCD catalogue automatically…")
        self.refresh()
        recalled = recall_loaded(self._catalogue_service().root) if self._catalogue_service().root else None
        if recalled is not None:
            # Another page instance already loaded this repository: show it without reading anything.
            self._loaded_key = (str(recalled.root), recalled.fingerprint)
            self._apply_scan(recalled, "Catalogue up to date")
        QTimer.singleShot(0, self._check_catalogue)
        self._catalogue_poll.start()

    # ------------------------------------------------------------------ build
    def _build_content(self) -> None:
        # Catalogue selection and OBX generation are one continuous workspace.
        workspace = QGroupBox("Article OBX Workspace", self)
        workspace_layout = QVBoxLayout(workspace)
        catalogue = self._build_catalogue_box()
        results = self._build_generation_box()
        for section in (catalogue, results):
            section.setTitle("")
            section.setStyleSheet("QGroupBox { border: 0; margin: 0; padding: 0; }")
            workspace_layout.addWidget(section)
        workspace_layout.setContentsMargins(8, 6, 8, 6)
        workspace_layout.setSpacing(4)
        self._normalize_group_boxes(workspace)
        self._content.addWidget(workspace, 1)

    def _button(self, text: str, slot, *, primary: bool = False) -> QPushButton:
        button = QPushButton(text, self)
        name = "pconObx" + "".join(part.capitalize() for part in text.replace("…", "").split())
        button.setObjectName(name)
        button.setStyleSheet(primary_button_qss(name) if primary else secondary_button_qss(name))
        button.clicked.connect(slot)
        return button

    def _build_catalogue_box(self) -> QGroupBox:
        box = QGroupBox("Catalogue", self)
        layout = QVBoxLayout(box)
        row = QHBoxLayout()
        row.addWidget(QLabel("Manufacturer:"))
        self._manufacturer = QComboBox(self)
        self._manufacturer.setMinimumWidth(78)
        self._manufacturer.setMaximumWidth(105)
        self._manufacturer.currentIndexChanged.connect(self._on_manufacturer_changed)
        row.addWidget(self._manufacturer)
        row.addWidget(QLabel("Program:"))
        self._program = QComboBox(self)
        self._program.setMinimumWidth(200)
        self._program.setMaximumWidth(300)
        self._program.currentIndexChanged.connect(self._on_program_changed)
        row.addWidget(self._program)
        # Series is derived from the selected program; keep its selector internal.
        self._series = QComboBox(self)
        self._series.currentIndexChanged.connect(self._on_series_changed)
        self._series.hide()

        row.addSpacing(8)
        row.addWidget(QLabel("Currency:"))
        self._currency = QComboBox(self)
        self._currency.setEditable(True)
        self._currency.setMinimumWidth(72)
        self._currency.setMaximumWidth(100)
        self._currency.setToolTip("Currency used for price resolution.")
        row.addWidget(self._currency)
        row.addWidget(QLabel("Price date:"))
        self._price_date = QDateEdit(QDate.currentDate(), self)
        self._price_date.setCalendarPopup(True)
        self._price_date.setDisplayFormat("yyyy-MM-dd")
        self._price_date.setMaximumWidth(140)
        row.addWidget(self._price_date)
        row.addSpacing(8)
        # Article lists load automatically when a program or series is selected.
        # Keep the related export and validator handoff actions in one dropdown,
        # matching the compact QToolButton style used by "Load OBX..." in Validation.
        self._obx_actions_button = QToolButton(self)
        self._obx_actions_button.setObjectName("pconObxActions")
        self._obx_actions_button.setText("OBX Actions")
        self._obx_actions_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._obx_actions_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._obx_actions_button.setMinimumHeight(36)
        self._obx_actions_button.setStyleSheet(
            "QToolButton { background:#FFFFFF; color:#1B2433; border:1px solid #C9D3DF; "
            "border-radius:6px; padding:7px 12px; } "
            "QToolButton:hover { background:#F3F7FB; border-color:#9AAABD; } "
            "QToolButton::menu-indicator { subcontrol-origin: padding; subcontrol-position: right center; "
            "right:8px; }"
        )
        self._obx_actions_button.setToolTip("Export the generated OBX or prepare a temporary OBX for validation.")
        self._obx_actions_menu = self._obx_actions_button.addMenu if False else None
        from PySide6.QtWidgets import QMenu
        obx_menu = QMenu(self._obx_actions_button)
        self._export_action = obx_menu.addAction("Export OBX")
        self._export_action.triggered.connect(self._export_obx)
        self._validator_action = obx_menu.addAction("Prepare for Validator")
        self._validator_action.setToolTip(
            "Create a temporary OBX for validation; the exported OBX file is not touched.")
        self._validator_action.triggered.connect(self._prepare_for_validator)
        self._obx_actions_button.setMenu(obx_menu)
        self._obx_actions_button.setEnabled(False)
        row.addWidget(self._obx_actions_button)
        self._diagnostics_button = self._button("Price Diagnostics", self._price_generated_skus)
        self._diagnostics_button.setEnabled(False)
        self._diagnostics_button.setToolTip(
            "Apply the selected currency and price date from ocd_price.csv to the already-generated SKU list. "
            "This does not enumerate SKUs again.")
        row.addWidget(self._diagnostics_button)
        layout.addLayout(row)

        self._catalogue_status = QLabel("", self)
        self._catalogue_status.setWordWrap(True)
        layout.addWidget(self._catalogue_status)

        # Article browsing/selection lives in a dialog so the generator workspace stays compact.
        self._article_dialog = QDialog(self)
        self._article_dialog.setWindowTitle("Load Articles")
        self._article_dialog.setModal(True)
        self._article_dialog.resize(900, 560)
        dialog_layout = QVBoxLayout(self._article_dialog)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self._article_filter = QLineEdit(self._article_dialog)
        self._article_filter.setPlaceholderText("Article number or label")
        self._article_filter.textChanged.connect(self._populate_articles)
        filter_row.addWidget(self._article_filter, 1)
        self._article_count = QLabel("0 articles", self._article_dialog)
        filter_row.addWidget(self._article_count)
        dialog_layout.addLayout(filter_row)

        self._article_table = QTableWidget(self._article_dialog)
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
        self._article_table.setMinimumHeight(300)
        self._article_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._article_table.itemSelectionChanged.connect(self._on_article_selection_changed)
        dialog_layout.addWidget(self._article_table, 1)

        dialog_actions = QHBoxLayout()
        # The one manual fabric option: which property holds the fabric information. Automatic = keyword discovery
        # plus the relation evidence; the type/colour/group roles are never chosen here.
        dialog_actions.addWidget(QLabel("Fabric property:"))
        self._fabric_property = QComboBox(self._article_dialog)
        self._fabric_property.setMinimumWidth(260)
        self._fabric_property.setMaximumWidth(420)
        self._fabric_property.setToolTip(
            "Automatic finds fabric properties by the keywords \"fabric\" / \"upholstery\" in the property name or "
            "text and reads the type/colour relationship from the data. Choose a property only when automatic "
            "discovery misses or misreads it; the relations are still evaluated.")
        self._fabric_property.addItem(_FABRIC_AUTOMATIC, "")
        dialog_actions.addWidget(self._fabric_property)
        dialog_actions.addStretch(1)
        close_button = self._button("Done", self._article_dialog.accept)
        dialog_actions.addWidget(close_button)
        dialog_layout.addLayout(dialog_actions)
        self._article_dialog.accepted.connect(self._on_article_dialog_done)
        return box

    def _build_properties_box(self) -> QGroupBox:
        box = QGroupBox("Automatic Permutation", self)
        layout = QVBoxLayout(box)
        message = QLabel(
            "The backend enumerates valid, unique SKUs from repository properties, relations, "
            "and constraints. No property inspection or SKU-count setting is required.",
            box)
        message.setWordWrap(True)
        message.setMaximumHeight(36)
        layout.addWidget(message)
        box.setMaximumHeight(78)
        return box

    def _build_generation_box(self) -> QGroupBox:
        box = QGroupBox("OBX Generation", self)
        layout = QVBoxLayout(box)
        self._generation_status = QLabel("No generation run yet.", self)
        self._generation_status.setWordWrap(True)
        layout.addWidget(self._generation_status)

        # Virtual model: hundreds of thousands of SKUs are shown without building a widget item per cell.
        self._result_model = SkuResultsModel(self)
        self._result_table = QTableView(self)
        self._result_table.setModel(self._result_model)
        self._result_table.horizontalHeader().setResizeContentsPrecision(200)
        self._result_table.verticalHeader().setDefaultSectionSize(24)
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
        layout.addLayout(footer)
        return box

    # --------------------------------------------------------------- settings
    def _save_settings(self) -> None:
        # Export destination is selected interactively each time Export OBX is clicked.
        return

    # ------------------------------------------------------------- lifecycle
    def refresh(self) -> None:
        self._update_controls()

    def is_ready(self) -> bool:
        return True

    def _update_controls(self) -> None:
        """Enable every control only when its prerequisites are met."""
        idle = self._run is None
        has_program = self._selected_program() is not None
        has_selection = bool(self._article_table.selectedIndexes())
        self._manufacturer.setEnabled(idle and self._manufacturer.count() > 0)
        self._program.setEnabled(idle and self._program.count() > 0)
        self._series.setEnabled(idle and self._series.count() > 1)
        self._article_filter.setEnabled(bool(self._articles))
        self._fabric_property.setEnabled(idle and self._fabric_property.count() > 1)
        has_exportable = self._outcome is not None and bool(self._outcome.exportable)
        self._obx_actions_button.setEnabled(idle and has_exportable)
        self._export_action.setEnabled(idle and has_exportable)
        self._validator_action.setEnabled(idle and has_exportable)
        self._diagnostics_button.setEnabled(idle and self._outcome is not None and bool(self._outcome.skus))

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

    def _start(self, title: str, work, finished, *, steps: int = 1, subject: str = "",
               status: QLabel | None = None, show_progress: bool = True) -> None:
        """Run work off the GUI thread; catalogue refreshes can be silent."""
        if self._run is not None and self._run.active:
            return
        run = ReportedTask(self)
        self._run = run
        reporter = run.reporter
        reporter.begin(max(1, steps), title=title, subject=subject)
        if show_progress:
            dialog = self._progress_monitor()
            dialog.bind(reporter)
            dialog.show()
            dialog.raise_()
        self._update_controls()

        def _done(result) -> None:
            self._run = None
            try:
                finished(result)
            finally:
                self._update_controls()

        target = status or self._generation_status

        def _failed(message: str) -> None:
            self._run = None
            self._update_controls()
            self._set_status(target, f"{title} failed: {message}", theme.COLOR_ERROR)
            QMessageBox.critical(self, title, f"{title} failed:\n\n{message}")

        def _cancelled(message: str) -> None:
            self._run = None
            self._update_controls()
            self._set_status(target, message, theme.COLOR_WARNING)

        run.start(lambda emit: work(reporter), finished=_done, failed=_failed, cancelled=_cancelled)

    @staticmethod
    def _set_status(label: QLabel, text: str, color: str | None = None) -> None:
        label.setText(text)
        label.setStyleSheet(f"color: {color};" if color else "")

    def _catalogue_service(self) -> OcdCatalogueService:
        if self._catalogue_reader is None:
            if self._catalogue_override is not None:
                self._catalogue_reader = self._catalogue_override
            else:
                config = getattr(self._context, "config", None)
                self._catalogue_reader = OcdCatalogueService(
                    getattr(config, "metatype_repository_root", "") or "")
        return self._catalogue_reader

    def _selected_program(self) -> OcdProgram | None:
        return self._program.currentData()

    def _generator_for(self, program: OcdProgram) -> OcdArticleGenerator:
        """One generator (and so one loaded dataset) per program folder."""
        key = Path(program.db_dir)
        if key not in self._generators:
            self._generators[key] = self._generator_factory(key)
        return self._generators[key]

    def _fill_currencies(self, currencies: list[str]) -> None:
        current = self._currency.currentText().strip()
        self._currency.clear()
        self._currency.addItems(currencies)
        if current and current.upper() in {value.upper() for value in currencies}:
            self._currency.setCurrentText(current)
        elif any(value.upper() == "EUR" for value in currencies):
            self._currency.setCurrentText(next(value for value in currencies if value.upper() == "EUR"))
        elif len(currencies) == 1:
            self._currency.setCurrentIndex(0)
        else:
            self._currency.setCurrentText("EUR")

    def _selected_articles(self) -> list[OcdArticle]:
        rows = sorted({index.row() for index in self._article_table.selectedIndexes()})
        selected = []
        for row in rows:
            item = self._article_table.item(row, 0)
            article = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
            if article is not None:
                selected.append(article)
        return selected

    # -------------------------------------------------------------- catalogue
    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self._check_catalogue()           # a check skipped while hidden happens when the page is shown

    def _poll_catalogue(self) -> None:
        if self.isVisible():              # other workflows are not interrupted by this page's housekeeping
            self._check_catalogue()

    def _check_catalogue(self) -> None:
        """Decide silently whether the loaded catalogue still matches the repository.

        Only the content fingerprint is computed (no catalogue is read, no popup shown). The catalogue is loaded -
        with its progress popup - only when the repository differs from what is shown, or nothing is shown yet.
        A failed check changes nothing, so the next check simply tries again.
        """
        if (self._run is not None and self._run.active) or (self._check_run is not None and self._check_run.active):
            return
        service = self._catalogue_service()
        if service.root is None:
            self._load_catalogue()        # surfaces "no repository configured" once, as a normal load error
            return
        run = ReportedTask(self)
        self._check_run = run

        def finished(fingerprint: str) -> None:
            self._check_run = None
            if self._scan is not None and self._loaded_key == (str(service.root), fingerprint):
                self._set_status(self._catalogue_status,
                                 f"Catalogue up to date ({len(self._scan.programs)} program(s)); checking automatically.",
                                 theme.COLOR_OK)
                return
            QTimer.singleShot(0, self._load_catalogue)    # not from inside this task's completion callback

        def failed(message: str) -> None:
            self._check_run = None
            self._set_status(self._catalogue_status, f"Catalogue check failed: {message}", theme.COLOR_WARNING)

        def cancelled(_message: str) -> None:
            self._check_run = None

        run.start(lambda _emit: service.fingerprint(), finished=finished, failed=failed, cancelled=cancelled)

    def _load_catalogue(self) -> None:
        if self._run is not None and self._run.active:
            return
        service = self._catalogue_service()
        self._set_status(self._catalogue_status, "Loading catalogue…")

        def work(reporter):
            reporter.note("Reading the OCD repository")

            def progress(done: int, total: int, name: str) -> None:
                reporter.note(f"Reading {name} ({done + 1}/{total})")

            scan = service.scan(progress)
            reporter.advance("Catalogue loaded")
            return scan

        self._start("Loading catalogue", work, self._on_catalogue_loaded,
                    subject=str(service.root or ""), status=self._catalogue_status)

    def _on_catalogue_loaded(self, scan: CatalogueScan) -> None:
        previous = self._scan
        # Recorded only after a successful load: a failed or cancelled load leaves the old key, so it is retried.
        if self._loaded_key is not None and self._loaded_key[1] != scan.fingerprint:
            self._generators.clear()      # their datasets were read from the data that has now changed
        self._loaded_key = (str(scan.root), scan.fingerprint)
        remember_loaded(scan)
        if previous is not None and previous.root == scan.root and previous.programs == scan.programs and previous.skipped == scan.skipped:
            self._set_status(self._catalogue_status,
                             f"Catalogue up to date ({len(scan.programs)} program(s)); checking automatically.",
                             theme.COLOR_OK)
            return
        self._apply_scan(scan, "Catalogue updated automatically")

    def _apply_scan(self, scan: CatalogueScan, headline: str) -> None:
        manufacturer_id = self._manufacturer.currentData()
        old_program = self._selected_program()
        program_name = old_program.program if old_program is not None else ""
        series_id = self._series.currentData() or ""
        self._scan = scan
        self._programs = scan.programs
        self._manufacturer.blockSignals(True)
        self._manufacturer.clear()
        for item in scan.manufacturers():
            self._manufacturer.addItem(item, item)
        index = self._manufacturer.findData(manufacturer_id)
        self._manufacturer.setCurrentIndex(index if index >= 0 else (0 if self._manufacturer.count() else -1))
        self._manufacturer.blockSignals(False)
        self._on_manufacturer_changed()
        if program_name:
            index = next((i for i in range(self._program.count())
                          if self._program.itemData(i).program == program_name), -1)
            if index >= 0:
                self._program.setCurrentIndex(index)
                series_index = self._series.findData(series_id)
                if series_index >= 0:
                    self._series.setCurrentIndex(series_index)
        skipped = f" {len(scan.skipped)} folder(s) without OCD data skipped." if scan.skipped else ""
        if not scan.programs:
            self._set_status(self._catalogue_status,
                             f"No OCD catalogue data found under {scan.root}.{skipped}", theme.COLOR_WARNING)
            return
        self._set_status(self._catalogue_status,
                         f"{headline}: {len(scan.programs)} program(s), "
                         f"{self._manufacturer.count()} manufacturer(s).{skipped}", theme.COLOR_OK)

    def _on_manufacturer_changed(self) -> None:
        manufacturer_id = self._manufacturer.currentData()
        self._program.blockSignals(True)
        self._program.clear()
        if self._scan is not None and manufacturer_id:
            for program in self._scan.programs_for(manufacturer_id):
                self._program.addItem(f"{program.program} ({program.article_count})", program)
        self._program.blockSignals(False)
        # Do not load the first program implicitly when only the manufacturer changes.
        # Wait until the user chooses a program.
        self._on_program_changed(auto_load=False)

    def _on_program_changed(self, *, auto_load: bool = True) -> None:
        program = self._selected_program()
        self._series.blockSignals(True)
        self._series.clear()
        if program is not None:
            self._series.addItem("(all series)", "")
            for series_id in program.series_ids:
                self._series.addItem(series_id, series_id)
            if len(program.series_ids) == 1:
                self._series.setCurrentIndex(1)
        self._series.blockSignals(False)
        self._on_series_changed(auto_load=auto_load)

    def _on_series_changed(self, *, auto_load: bool = True) -> None:
        """Any change upstream invalidates the loaded articles; they must be loaded again."""
        had_articles = bool(self._articles)
        self._articles = []
        self._article_filter.clear()
        self._populate_articles()
        if had_articles:
            self._set_status(self._catalogue_status, "Selection changed - loading the selected article list…")
        elif self._selected_program() is not None:
            self._set_status(self._catalogue_status, "Loading articles for the selected program…")
        self._update_controls()
        if auto_load and self._selected_program() is not None:
            self._load_articles()

    def _load_articles(self) -> None:
        program = self._selected_program()
        if program is None:
            QMessageBox.information(self, "Load Articles", "Load the catalogue and choose a program first.")
            return
        series_id = self._series.currentData() or ""
        service = self._catalogue_service()
        label = f"{program.program}" + (f" / {series_id}" if series_id else "")
        self._set_status(self._catalogue_status, f"Loading articles of {label}…")

        generator = self._generator_for(program)

        def work(reporter):
            reporter.note(f"Reading catalogue articles of {label}")
            articles = service.list_articles(program, series_id)
            try:
                currencies = generator.currencies()     # prices are optional until a SKU run needs them
            except GenerationError:
                currencies = []
            reporter.advance("Articles loaded")
            return articles, currencies

        def finished(result):
            articles, currencies = result
            self._fill_currencies(currencies)
            self._on_articles_loaded(articles, label)
            # Let the user choose articles; SKU generation begins after Done.
            self._article_filter.clear()
            self._article_dialog.show()
            self._article_dialog.raise_()
            self._article_dialog.activateWindow()

        self._start("Loading articles", work, finished, subject=label, status=self._catalogue_status)

    def _on_articles_loaded(self, articles: list[OcdArticle], label: str = "") -> None:
        self._articles = list(articles)
        self._populate_articles()
        if self._articles:
            self._article_table.clearSelection()
            self._set_status(self._catalogue_status,
                             f"Loaded {len(self._articles)} article(s) of {label}.", theme.COLOR_OK)
        else:
            self._set_status(self._catalogue_status,
                             f"No articles found for {label}.", theme.COLOR_WARNING)
        self._update_controls()

    def _on_article_dialog_done(self) -> None:
        selected = self._selected_articles()
        if not selected:
            self._set_status(self._generation_status, "Select at least one article to generate SKUs.", theme.COLOR_WARNING)
            return
        self._generate()

    def _on_article_selection_changed(self) -> None:
        self._refresh_fabric_choices()
        self._update_controls()

    def _refresh_fabric_choices(self) -> None:
        """List the properties of the selected articles; keep the choice if it is still offered, else go back to Automatic."""
        wanted = self._fabric_property.currentData() or ""
        program = self._selected_program()
        numbers = [a.article_number for a in self._selected_articles()]
        choices = []
        if program is not None and numbers:
            try:
                choices = self._generator_for(program).fabric_property_choices(numbers)
            except (GenerationError, OSError, ValueError, KeyError):
                choices = []                    # the generation run reports unreadable data
        choices.sort(key=lambda c: not c.candidate)          # keyword candidates first, otherwise article order
        box = self._fabric_property
        box.blockSignals(True)
        box.clear()
        box.addItem(_FABRIC_AUTOMATIC, "")
        for choice in choices:
            box.addItem(choice.display, choice.name)
            if choice.candidate:
                box.setItemData(box.count() - 1, "Contains a fabric/upholstery keyword", Qt.ItemDataRole.ToolTipRole)
        index = box.findData(wanted) if wanted else 0
        box.setCurrentIndex(index if index >= 0 else 0)
        box.blockSignals(False)

    def _populate_articles(self) -> None:
        needle = self._article_filter.text().strip().lower()
        rows = [
            a for a in self._articles
            if not needle or needle in a.article_number.lower() or needle in a.label.lower()
        ]
        self._article_table.setRowCount(len(rows))
        for row, article in enumerate(rows):
            values = [article.article_number, "—", article.label, article.program]   # OCD has no variant code
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(article.label or value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, article)
                self._article_table.setItem(row, column, item)
        self._article_count.setText(f"{len(rows)} of {len(self._articles)} articles")
        self._update_controls()

    # ------------------------------------------------------------- generation
    def _generate(self) -> None:
        program = self._selected_program()
        articles = self._selected_articles()
        if program is None or not articles:
            QMessageBox.information(self, "Generate OBX", "Select a program and at least one article.")
            return
        rules = []  # all repository properties are varied by the backend engine
        self._save_settings()
        self._outcome = None
        self._result_model.clear()
        self._validation_label.setText("")
        self._generation_status.setText("Enumerating valid SKUs with the OCD Engine…")
        generator = self._generator_for(program)
        numbers = [a.article_number for a in articles]
        price_date = self._price_date.date().toString("yyyy-MM-dd")
        fabric_property = self._fabric_property.currentData() or ""

        def work(reporter):
            reporter.note("Reading the OCD data")
            _ = generator.dataset
            outcome = generator.generate(numbers, rules, price=False,
                                         max_configurations=None, fabric_property=fabric_property,
                                         reporter=reporter)
            # Everything proportional to the result size happens here, off the GUI thread; the GUI only
            # swaps a reference (see ``_on_generated``).
            reporter.note(f"Preparing {len(outcome.skus):,} valid SKU(s) for display")
            return outcome

        def finished(outcome):
            self._outcome_program, self._outcome_price_date = program, ""
            self._on_generated(outcome)

        self._start("Generating valid SKUs", work, finished, steps=len(numbers),
                    subject=", ".join(numbers)[:80])

    def _on_generated(self, outcome: GenerationOutcome) -> None:
        self._outcome = outcome
        self._result_model.set_results(outcome.skus)

        summary = (
            f"Generated {len(outcome.skus):,} valid unique SKU(s) from {outcome.configurations:,} configuration(s), "
            f"{outcome.nodes:,} evaluated node(s)"
            f", {outcome.pruned} value(s) pruned"
            f"{', ' + str(outcome.invalid) + ' invalid configuration(s) rejected' if outcome.invalid else ''}"
            f"{', ' + str(outcome.duplicates) + ' duplicate SKU(s) removed' if outcome.duplicates else ''}"
            f"{' (limit reached)' if outcome.truncated else ''}."
        )
        summary += " Pricing not run; choose a currency and date, then click Price Diagnostics."
        self._generation_status.setText(summary)
        self._generation_status.setStyleSheet(
            f"color: {theme.COLOR_OK if outcome.skus and not outcome.truncated else theme.COLOR_WARNING};")
        self._validation_label.setText(" ".join(outcome.warnings[:5]))
        # one line per fabric colour decision: type, mechanism, candidates, rejections, chosen colour and why
        self._generation_status.setToolTip("\n".join(outcome.fabric_notes[:40]))
        self._update_controls()

    def _price_generated_skus(self) -> None:
        """Apply the chosen OCD CSV price list to the existing SKU rows without re-enumerating."""
        outcome, program = self._outcome, self._outcome_program
        if outcome is None or program is None or not outcome.skus:
            QMessageBox.information(self, "Price Diagnostics", "Generate valid SKUs first.")
            return
        currency = self._currency.currentText().strip()
        price_date = self._price_date.date().toString("yyyy-MM-dd")
        generator = self._generator_for(program)
        skus = outcome.skus
        self._generation_status.setText(f"Applying {currency or 'selected'} prices from ocd_price.csv…")

        def work(reporter):
            reporter.note(f"Pricing {len(skus):,} existing SKU(s)")
            return generator.price_skus(skus, currency=currency, price_date=price_date, reporter=reporter)

        def finished(priced_skus):
            outcome.skus = priced_skus
            self._outcome_price_date = price_date
            self._result_model.set_results(outcome.skus)
            self._generation_status.setText(
                f"Price diagnostics complete: {len(outcome.exportable):,} priced, "
                f"{outcome.unpriced:,} unpriced SKU(s) in {currency} for {price_date}. "
                "SKU enumeration was not repeated.")
            self._generation_status.setStyleSheet(
                f"color: {theme.COLOR_OK if outcome.exportable else theme.COLOR_WARNING};")
            self._update_controls()
            self._show_price_diagnostics()

        # The engine reports one completed progress unit per 500 priced SKUs.
        pricing_steps = max(1, (len(skus) + 499) // 500)
        self._start("Price Diagnostics", work, finished, steps=pricing_steps,
                    subject=f"{len(skus):,} SKU(s) - {currency} - {price_date}")

    def _price_diagnostics_text(self) -> str:
        """Diagnostics for the selected result row, or the first one; empty when nothing was generated."""
        outcome, program = self._outcome, self._outcome_program
        if outcome is None or program is None or not outcome.skus:
            return ""
        rows = self._result_table.selectionModel().selectedRows() if self._result_table.selectionModel() else []
        sku = outcome.skus[rows[0].row()] if rows else outcome.skus[0]
        try:
            lines = self._generator_for(program).price_diagnostics(
                sku.base_article, varconds=sku.varconds, currency=sku.currency,
                price_date=self._outcome_price_date, factors=dict(sku.pricing_factors))
        except GenerationError as exc:
            lines = [str(exc)]
        return "\n".join([f"selected: {program.program} / {sku.base_article} / {sku.final_article}",
                          f"price key(s) derived for this SKU: {list(sku.varconds) or '(none)'}", *lines])

    def _show_price_diagnostics(self) -> None:
        text = self._price_diagnostics_text()
        if not text:
            QMessageBox.information(self, "Price Diagnostics", "Generate valid SKUs first.")
            return
        box = QMessageBox(self)
        box.setWindowTitle("Price Diagnostics")
        box.setText("Price lookup for the selected SKU")
        view = QPlainTextEdit(text, box)
        view.setReadOnly(True)
        view.setMinimumSize(720, 320)
        box.layout().addWidget(view, 1, 0, 1, box.layout().columnCount())
        box.exec()

    # ------------------------------------------------------------------ export
    def _export_obx(self) -> None:
        outcome, program = self._outcome, self._outcome_program
        if outcome is None or program is None or not outcome.exportable:
            QMessageBox.information(self, "Export OBX", "Generate valid SKUs with a price first.")
            return
        suggested = self._settings.value(_SETTINGS_PREFIX + "outputPath", "generated.obx", type=str)
        path, _ = QFileDialog.getSaveFileName(
            self, "Export OBX", suggested or "generated.obx", "OBX files (*.obx)")
        if not path:
            return
        if not path.lower().endswith(".obx"):
            path += ".obx"
        if Path(path).exists():
            answer = QMessageBox.question(self, "Export OBX", f"{path} exists. Overwrite it?")
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._settings.setValue(_SETTINGS_PREFIX + "outputPath", path)
        skus, price_date = list(outcome.exportable), self._outcome_price_date
        series = self._series.currentData() or ""

        def work(reporter):
            reporter.note(f"Writing {len(skus)} SKU(s)")
            summary = export_obx(skus, path, manufacturer_id=program.manufacturer_id,
                                 price_date=price_date, series_id=series)
            reporter.advance("OBX written")
            return summary

        self._start("Exporting OBX", work, self._on_exported, subject=Path(path).name)

    def _prepare_for_validator(self) -> None:
        outcome, program = self._outcome, self._outcome_program
        if outcome is None or program is None or not outcome.exportable:
            QMessageBox.information(self, "Prepare for Validator", "Generate valid SKUs with a price first.")
            return
        skus, price_date = list(outcome.exportable), self._outcome_price_date
        series = self._series.currentData() or ""

        def work(reporter):
            reporter.note(f"Writing {len(skus)} SKU(s) to a temporary OBX")
            snapshot = self._validator_handoff.create(
                skus, manufacturer_id=program.manufacturer_id, price_date=price_date, series_id=series)
            reporter.advance("Temporary OBX written")
            return snapshot

        self._start("Preparing for Validator", work, self._on_validator_snapshot, subject=f"{len(skus)} SKU(s)")

    def _on_validator_snapshot(self, snapshot) -> None:
        text = (f"Temporary OBX ready ({snapshot.article_count} article line(s)). In OBX Validation choose "
                f"Load OBX... > Load from Article OBX Generator.")
        self._generation_status.setText(text)
        self._generation_status.setStyleSheet(f"color: {theme.COLOR_OK if snapshot.ok else theme.COLOR_ERROR};")
        self._validation_label.setText(" ".join(snapshot.problems))

    def _on_exported(self, summary) -> None:
        text = (f"Exported {summary.exported} SKU(s) to {summary.path}; "
                f"{summary.article_lines} article line(s) read back")
        if summary.skipped_unpriced:
            text += f", {summary.skipped_unpriced} unpriced SKU(s) not exported"
        self._generation_status.setText(text + ".")
        self._generation_status.setStyleSheet(f"color: {theme.COLOR_OK if summary.ok else theme.COLOR_ERROR};")
        problems = list(summary.problems)
        if summary.missing_final_articles:
            problems.append("Missing: " + ", ".join(summary.missing_final_articles[:10]))
        self._validation_label.setText(" ".join(problems))

