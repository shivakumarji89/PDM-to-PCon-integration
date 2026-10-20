"""Metatype creation workspace: the polymorphic Metatype stage.

The runtime creation page. It works directly on the configured HMX repository, independently of any PDM
product or connection: pick a series, load it, name the polymorphic property (template Step 3), and see
whether the stage is complete. Repository scanning, table loading and relationship checks are backend
rules and are not exposed as controls here. All logic lives in ``MetatypeCreationService``.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QPushButton, QStackedWidget, QTableView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from models.metatype_creation import (
    BranchResult, IdentityResult, PolymorphicStageStatus, SpecificationResult, StepState, SwitchScope, TranslationKind, TranslationResult,
    TranslationRow, ValidityResult, ValueValidityRow,
)
from models.metatype_articles import ArticleReconciliation, ReconciliationStatus
from services.metatype.article_edit_session import ArticleEditSession
from pathlib import Path

from services.metatype.article_write_plan import plan_article_edits
from services.metatype.owner_selection import OwnerSelection, OwnerState, build_owner_choice
from services.metatype.staged_writer import apply_plan, load_authorization, plan_fingerprint, review_text as staged_review
from ui.pages.metatype_owner_dialog import OwnerSelectionDialog
from services.metatype.property_creation_plan import CreationInputs, CreationPlan, plan_property_creation
from services.metatype.property_rules import ArticleValueTable, ModePolicy, config_ids_for
from services.metatype.text_encoding import Encoding
from ui.pages.metatype_value_table import ArticleValueModel, ArticleValueProxy
from services.metatype.value_validity import ALL_MARKER, parse_validity_cell
from ui.components._styles import primary_button_qss, secondary_button_qss
from ui.pages.base_page import BasePage
from ui.pages.metatype_article_table import KEY_ROLE, ArticleFilterProxy, ArticleWorkTableModel
from services.metatype.metatype_template_service import MetatypeTemplateService


class MetatypeCreationPage(BasePage):
    """Select a series, load it and create the polymorphic Metatype property."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Create Metatype",
            description="Polymorphic Metatype first: select a series from the HMX repository, load its data, "
                        "then name the property and answer the article questions. Loading is read-only; only the explicit Start Metatype from Scratch action copies bundled templates.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._service = context.metatype_creation_service
        self._template_service = MetatypeTemplateService(self._service.root)

        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.root_label = QLabel(f"Repository: {self._service.root}", panel)
        self.root_label.setObjectName("metatypeCreationRoot")
        self.root_label.setWordWrap(True)
        layout.addWidget(self.root_label)

        row = QHBoxLayout()
        self.series_combo = QComboBox(panel)
        self.series_combo.setObjectName("metatypeSeriesCombo")
        self.series_combo.setEditable(False)
        self.load_button = QPushButton("Load Series", panel)
        self.load_button.setObjectName("metatypeLoadSeriesButton")
        self.load_button.setStyleSheet(primary_button_qss("metatypeLoadSeriesButton"))
        self.load_button.setToolTip("Read the selected series' existing Metatype data (read-only).")
        self.load_button.clicked.connect(self.load_series)
        self.start_scratch_button = QPushButton("Start Metatype from Scratch", panel)
        self.start_scratch_button.setObjectName("metatypeStartFromScratchButton")
        self.start_scratch_button.setStyleSheet(secondary_button_qss("metatypeStartFromScratchButton"))
        self.start_scratch_button.setToolTip("Copy the complete bundled template set into this series only when explicitly confirmed.")
        self.start_scratch_button.clicked.connect(self.start_metatype_from_scratch)
        self.series_combo.currentIndexChanged.connect(self._sync_template_action)
        row.addWidget(QLabel("Series:", panel))
        row.addWidget(self.series_combo, 1)
        row.addWidget(self.load_button)
        row.addWidget(self.start_scratch_button)
        layout.addLayout(row)

        self.status_output = QPlainTextEdit(panel)
        self.status_output.setObjectName("metatypeStageStatus")
        self.status_output.setReadOnly(True)
        self.status_output.setMaximumHeight(170)
        self.status_output.setPlaceholderText("Select a series and choose Load Series, or explicitly start a new series from scratch.")
        layout.addWidget(self.status_output)

        self.workspace_stack = QStackedWidget(panel)
        self.workspace_stack.setObjectName("metatypeWorkspaceStack")
        self.workspace_stack
        self._workspace_pages = {}
        self._workspace_layouts = {}
        for title, key in (
            ("Articles", "articles"),
            ("Properties", "properties"),
            ("Property Values", "values"),
            ("Texts", "texts"),
            ("Setup", "setup"),
            ("Relations / Ordering", "relations"),
            ("Final Review", "review"),
        ):
            page = QWidget(self.workspace_stack)
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(8, 8, 8, 8)
            page_layout.setSpacing(8)
            self.workspace_stack.addWidget(page)
            self._workspace_pages[key] = page
            self._workspace_layouts[key] = page_layout
        layout.addWidget(self.workspace_stack, 1)

        group = QGroupBox("Step 3 - Property name", panel)
        form = QFormLayout(group)
        self.name_edit = QLineEdit(group)
        self.name_edit.setObjectName("metatypePropertyName")
        self.name_edit.setPlaceholderText("Technical property name, e.g. GATLAS_Example")
        self.label_edit = QLineEdit(group)
        self.label_edit.setObjectName("metatypePropertyLabel")
        self.label_edit.setPlaceholderText("English display label")
        form.addRow("Technical name:", self.name_edit)
        form.addRow("English label:", self.label_edit)
        self.confirm_button = QPushButton("Validate and Confirm", group)
        self.confirm_button.setObjectName("metatypeConfirmIdentityButton")
        self.confirm_button.setStyleSheet(secondary_button_qss("metatypeConfirmIdentityButton"))
        self.confirm_button.clicked.connect(self.confirm_identity)
        form.addRow(self.confirm_button)
        group.setEnabled(False)
        self._identity_group = group
        self._workspace_layouts["properties"].addWidget(group)

        self._build_articles_table(panel)

        group4 = QGroupBox("Step 4 - Articles the property switches between", panel)
        form4 = QFormLayout(group4)
        self.articles_edit = QPlainTextEdit(group4)
        self.articles_edit.setObjectName("metatypeSwitchArticles")
        self.articles_edit.setMaximumHeight(70)
        self.articles_edit.setPlaceholderText("One article number per line")
        self.articles_hint = QLabel("", group4)
        self.articles_hint.setObjectName("metatypeArticlesHint")
        self.articles_hint.setWordWrap(True)
        self.scope_combo = QComboBox(group4)
        self.scope_combo.setObjectName("metatypeSwitchScope")
        self.scope_combo.addItem("Choose...", None)
        self.scope_combo.addItem("Unconditional", SwitchScope.UNCONDITIONAL.value)
        self.scope_combo.addItem("Scoped to conditions", SwitchScope.SCOPED.value)
        self.scope_combo.currentIndexChanged.connect(self._scope_changed)
        self.conditions_edit = QPlainTextEdit(group4)
        self.conditions_edit.setObjectName("metatypeSwitchConditions")
        self.conditions_edit.setMaximumHeight(70)
        self.conditions_edit.setPlaceholderText("One condition per line (parent property, region, ...)")
        self.conditions_edit.setEnabled(False)
        self.values_combo = QComboBox(group4)
        self.values_combo.setObjectName("metatypeValuesAccepted")
        self.values_combo.addItem("Choose...", None)
        self.values_combo.addItem("Yes - every listed article accepts every property value", True)
        self.values_combo.addItem("No - there are exceptions (answer Step 4a below)", False)
        self.confirm_branch_button = QPushButton("Validate and Confirm", group4)
        self.confirm_branch_button.setObjectName("metatypeConfirmBranchButton")
        self.confirm_branch_button.setStyleSheet(secondary_button_qss("metatypeConfirmBranchButton"))
        self.confirm_branch_button.clicked.connect(self.confirm_branch)
        form4.addRow("Articles:", self.articles_edit)
        form4.addRow("", self.articles_hint)
        form4.addRow("Switch:", self.scope_combo)
        form4.addRow("Conditions:", self.conditions_edit)
        form4.addRow("Property values:", self.values_combo)
        form4.addRow(self.confirm_branch_button)
        group4.setEnabled(False)
        self._branch_group = group4
        self._workspace_layouts["articles"].addWidget(group4)

        group4a = QGroupBox("Step 4a - Value validity per article", panel)
        form4a = QFormLayout(group4a)
        self.validity_combo = QComboBox(group4a)
        self.validity_combo.setObjectName("metatypeValidityAnswer")
        self.validity_combo.addItem("Choose...", None)
        self.validity_combo.addItem("All articles accept the full value set", True)
        self.validity_combo.addItem("Some article only allows a subset of the values", False)
        self.validity_combo.currentIndexChanged.connect(self._validity_answer_changed)
        self.validity_table = QTableWidget(0, 2, group4a)
        self.validity_table.setObjectName("metatypeValidityTable")
        self.validity_table.setHorizontalHeaderLabels(["Value", "Valid for article(s)"])
        self.validity_table.horizontalHeader().setStretchLastSection(True)
        self.validity_table.setMaximumHeight(160)
        self.validity_table.setEnabled(False)
        self.validity_hint = QLabel(
            f"One row per property value. Valid for: \"{ALL_MARKER}\", or article numbers separated by commas "
            "(only articles listed in Step 4). Values are entered by you; they are not read from the repository.",
            group4a)
        self.validity_hint.setObjectName("metatypeValidityHint")
        self.validity_hint.setWordWrap(True)
        self.add_value_button = QPushButton("Add Value", group4a)
        self.add_value_button.setObjectName("metatypeAddValueButton")
        self.add_value_button.setStyleSheet(secondary_button_qss("metatypeAddValueButton"))
        self.add_value_button.clicked.connect(self.add_value_row)
        self.remove_value_button = QPushButton("Remove Selected", group4a)
        self.remove_value_button.setObjectName("metatypeRemoveValueButton")
        self.remove_value_button.setStyleSheet(secondary_button_qss("metatypeRemoveValueButton"))
        self.remove_value_button.clicked.connect(self.remove_value_row)
        row_buttons = QHBoxLayout()
        row_buttons.addWidget(self.add_value_button)
        row_buttons.addWidget(self.remove_value_button)
        row_buttons.addStretch(1)
        self.confirm_validity_button = QPushButton("Validate and Confirm", group4a)
        self.confirm_validity_button.setObjectName("metatypeConfirmValidityButton")
        self.confirm_validity_button.setStyleSheet(secondary_button_qss("metatypeConfirmValidityButton"))
        self.confirm_validity_button.clicked.connect(self.confirm_validity)
        form4a.addRow("Question:", self.validity_combo)
        form4a.addRow("", self.validity_hint)
        form4a.addRow(self.validity_table)
        form4a.addRow(row_buttons)
        form4a.addRow(self.confirm_validity_button)
        group4a.setEnabled(False)
        self._validity_group = group4a
        self._workspace_layouts["values"].addWidget(group4a)

        group5 = QGroupBox("Step 5 - Translations (German, French, Dutch)", panel)
        form5 = QFormLayout(group5)
        self.translation_table = QTableWidget(0, 5, group5)
        self.translation_table.setObjectName("metatypeTranslationTable")
        self.translation_table.setHorizontalHeaderLabels(["Technical value", "EN", "DE", "FR", "NL"])
        self.translation_table.horizontalHeader().setStretchLastSection(True)
        self.translation_table.setMaximumHeight(200)
        self.translation_hint = QLabel(
            "One row for the property and one for each value from Step 4a. The property's English label is "
            "the one from Step 3; enter the English text of each value. Confirm or correct the table, then "
            "confirm.", group5)
        self.translation_hint.setObjectName("metatypeTranslationHint")
        self.translation_hint.setWordWrap(True)
        self.confirm_translations_button = QPushButton("Validate and Confirm", group5)
        self.confirm_translations_button.setObjectName("metatypeConfirmTranslationsButton")
        self.confirm_translations_button.setStyleSheet(secondary_button_qss("metatypeConfirmTranslationsButton"))
        self.confirm_translations_button.clicked.connect(self.confirm_translations)
        form5.addRow(self.translation_hint)
        form5.addRow(self.translation_table)
        form5.addRow(self.confirm_translations_button)
        group5.setEnabled(False)
        self._translation_group = group5
        self._workspace_layouts["texts"].addWidget(group5)

        group6 = QGroupBox("Step 6 - Confirm the specification", panel)
        form6 = QFormLayout(group6)
        self.spec_output = QPlainTextEdit(group6)
        self.spec_output.setObjectName("metatypeSpecSummary")
        self.spec_output.setReadOnly(True)
        self.spec_output.setMaximumHeight(260)
        self.spec_output.setPlaceholderText("The summary appears here once Steps 1-5 are complete.")
        self.spec_hint = QLabel(
            "Review the summary. Confirming records your approval only: no repository file is edited, because "
            "writing the files is not implemented.", group6)
        self.spec_hint.setObjectName("metatypeSpecHint")
        self.spec_hint.setWordWrap(True)
        self.confirm_spec_button = QPushButton("Confirm Specification", group6)
        self.confirm_spec_button.setObjectName("metatypeConfirmSpecButton")
        self.confirm_spec_button.setStyleSheet(secondary_button_qss("metatypeConfirmSpecButton"))
        self.confirm_spec_button.clicked.connect(self.confirm_specification)
        form6.addRow(self.spec_hint)
        form6.addRow(self.spec_output)
        form6.addRow(self.confirm_spec_button)
        group6.setEnabled(False)
        self._spec_group = group6
        self._workspace_layouts["review"].addWidget(group6)

        setup_note = QLabel(
            "Setup options are not yet implemented. No setup table is edited by this workflow.", panel)
        setup_note.setWordWrap(True)
        setup_note.setObjectName("metatypeSetupPlaceholder")
        self._workspace_layouts["setup"].addWidget(setup_note)
        relations_note = QLabel(
            "Relations and ordering are not yet implemented. Relationship analysis is read-only; no ordering "
            "numbers or relation rows are generated.", panel)
        relations_note.setWordWrap(True)
        relations_note.setObjectName("metatypeRelationsPlaceholder")
        self._workspace_layouts["relations"].addWidget(relations_note)
        for key in self._workspace_layouts:
            self._workspace_layouts[key].addStretch(1)

        self.findings_output = QPlainTextEdit(panel)
        self.findings_output.setObjectName("metatypeFindings")
        self.findings_output.setReadOnly(True)
        self.findings_output.setMaximumHeight(140)
        self.findings_output.setPlaceholderText("Validation findings appear here.")
        layout.addWidget(self.findings_output)

        self.children_button = QPushButton("Continue to Child Metatypes", panel)
        self.children_button.setObjectName("metatypeChildrenButton")
        self.children_button.setStyleSheet(secondary_button_qss("metatypeChildrenButton"))
        self.children_button.setEnabled(False)
        self.children_button.setToolTip("Locked until the polymorphic stage is complete.")
        layout.addWidget(self.children_button)
        layout.addStretch(1)

        self.add_content(panel)
        self.refresh()

    # -- articles work table ------------------------------------------------------------------------------------
    def _build_articles_table(self, panel: QWidget) -> None:
        group = QGroupBox("Articles in the series", panel)
        box = QVBoxLayout(group)
        self.articles_session = ArticleEditSession()
        self.articles_model = ArticleWorkTableModel(self.articles_session, group)
        self.articles_proxy = ArticleFilterProxy(group)
        self.articles_proxy.setSourceModel(self.articles_model)
        self.articles_model.edited.connect(self._articles_edited)

        def button(text: str, name: str, slot, primary: bool = False, tip: str = "") -> QPushButton:
            widget = QPushButton(text, group)
            widget.setObjectName(name)
            widget.setStyleSheet((primary_button_qss if primary else secondary_button_qss)(name))
            widget.clicked.connect(slot)
            if tip:
                widget.setToolTip(tip)
            return widget

        self.articles_refresh_button = button(
            "Refresh", "metatypeArticlesRefreshButton", self.refresh_articles,
            tip="Reload the series from the repository; pending edits are kept.")
        self.articles_search = QLineEdit(group)
        self.articles_search.setObjectName("metatypeArticlesSearch")
        self.articles_search.setPlaceholderText("Search articles...")
        self.articles_search.setClearButtonEnabled(True)
        self.articles_search.textChanged.connect(self.articles_proxy.set_text)
        self.articles_filter = QComboBox(group)
        self.articles_filter.setObjectName("metatypeArticlesFilter")
        self.articles_filter.addItems(ArticleFilterProxy.FILTERS)
        self.articles_filter.currentTextChanged.connect(self.articles_proxy.set_mode)
        self.articles_validate_button = button("Validate", "metatypeArticlesValidateButton", self.validate_articles)
        self.articles_review_button = button("Review changes", "metatypeArticlesReviewButton", self.review_articles)
        self.articles_discard_button = button("Discard edits", "metatypeArticlesDiscardButton",
                                              self.discard_article_edits)
        self.articles_owner_button = button(
            "Choose owner Metatype...", "metatypeArticlesOwnerButton", self.choose_owner,
            tip="Resolve which Metatype owns the new property from the listed articles; asks when ambiguous.")
        self.articles_apply_button = button(
            "Apply to staging...", "metatypeArticlesApplyButton", self.apply_to_staging,
            tip="Writes only to an authorised staging working copy after review and confirmation.")
        self.articles_create_button = button(
            "Create Metatype", "metatypeArticlesCreateButton", self.create_from_articles, primary=True,
            tip="Creates the property in the authorised staging copy after review and confirmation; "
                "when a prerequisite is missing, click to see why.")
        bar = QHBoxLayout()
        for widget in (self.articles_refresh_button, self.articles_search, self.articles_filter,
                       self.articles_validate_button, self.articles_review_button, self.articles_discard_button,
                       self.articles_owner_button, self.articles_apply_button, self.articles_create_button):
            bar.addWidget(widget, 1 if widget is self.articles_search else 0)

        self.articles_load_status = QLabel("", group)
        self.articles_load_status.setObjectName("metatypeArticlesLoadStatus")
        self.articles_load_status.setWordWrap(True)
        self.articles_owner_label = QLabel("Owner Metatype: not resolved yet.", group)
        self.articles_owner_label.setObjectName("metatypeArticlesOwnerLabel")
        self.articles_owner_label.setWordWrap(True)
        self.owner_selection: OwnerSelection | None = None
        self.articles_counts = QLabel("", group)
        self.articles_counts.setObjectName("metatypeArticlesCounts")

        self.articles_table = QTableView(group)
        self.articles_table.setObjectName("metatypeArticlesTable")
        self.articles_table.setModel(self.articles_proxy)
        self.articles_table.setSortingEnabled(True)
        self.articles_table.setAlternatingRowColors(True)
        self.articles_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.articles_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.articles_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                                            | QAbstractItemView.EditTrigger.EditKeyPressed
                                            | QAbstractItemView.EditTrigger.AnyKeyPressed)
        self.articles_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.articles_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.articles_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.articles_table.horizontalHeader().setStretchLastSection(True)
        self.articles_table.setMinimumHeight(240)
        self.articles_diagnostics = QPlainTextEdit(group)
        self.articles_diagnostics.setObjectName("metatypeArticlesDiagnostics")
        self.articles_diagnostics.setReadOnly(True)
        self.articles_diagnostics.setMaximumHeight(120)
        self.articles_table.selectionModel().selectionChanged.connect(self._show_selected_row_diagnostics)
        box.addLayout(bar)
        box.addWidget(self.articles_load_status)
        box.addWidget(self.articles_owner_label)
        box.addWidget(self.articles_counts)
        box.addWidget(self.articles_table, 1)
        box.addWidget(self.articles_diagnostics)
        self._workspace_layouts["articles"].addWidget(group, 1)
        self._build_creation_group(panel)
        self._show_articles()

    def _load_articles(self, series: str) -> None:
        """Reconcile the loaded series' articles (read-only, in memory) and show the result."""
        self.articles_session.discard()           # a newly loaded series starts without carried-over edits
        self._reconcile_articles(series)
        self._show_articles()

    def _reconcile_articles(self, series: str):
        inspection = self._service.inspection
        target = inspection.target if inspection is not None else None
        return self._context.metatype_article_service.reconcile(
            series, root=inspection.repository_root if inspection is not None else None,
            directory=(target.directory or None) if target is not None else None)

    def refresh_articles(self) -> None:
        """Reload from the repository, keeping pending edits by article identity and reporting conflicts."""
        series = self._service.series
        if not series or self._service.inspection is None:
            return
        self._reconcile_articles(series)
        self._show_articles()
        report = self.articles_session.last_refresh
        notes = []
        if report is not None and report.conflicted:
            notes.append(f"{len(report.conflicted)} pending edit(s) now differ from a changed source value; "
                         "they were kept - review them before creating.")
        if report is not None and report.dropped:
            notes.append(f"{len(report.dropped)} pending edit(s) could not be kept (article gone or not editable): "
                         + "; ".join(f"{' / '.join(map(str, c.key))} {c.column}={c.new!r}" for c in report.dropped))
        if notes:
            self.articles_diagnostics.appendPlainText("\n" + "\n".join(notes))

    def validate_articles(self) -> None:
        problems = self.articles_session.validate_all()
        lines = [f"{i.severity.upper()} [{i.code}] {' / '.join(map(str, key))}: {i.message}"
                 for key, issues in problems.items() for i in issues]
        self.articles_diagnostics.setPlainText("\n".join(lines) if lines else "Validation found no problems.")
        self.articles_model.refresh_rows()

    def review_articles(self) -> str:
        plan = plan_article_edits(self.articles_session)
        text = self.articles_session.review_text()
        if self.articles_session.pending_count:
            text = text.replace("\nBlockers:", "\n" + plan.review_text() + "\n\nBlockers:", 1)
        self.articles_diagnostics.setPlainText(text)
        return text

    def discard_article_edits(self) -> None:
        if not self.articles_session.pending_count:
            return
        answer = QMessageBox.question(
            self, "Discard edits", f"Discard {self.articles_session.pending_count} pending edit(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Yes:
            self.articles_session.discard()
            self.articles_model.refresh_rows()

    # -- property creation (values, plan, gating) -------------------------------------------------------------
    def _build_creation_group(self, panel: QWidget) -> None:
        group = QGroupBox("Create the polymorphic property (staging only)", panel)
        box = QVBoxLayout(group)
        form = QFormLayout()

        def text_edit(name: str, hint: str, height: int = 56) -> QPlainTextEdit:
            widget = QPlainTextEdit(group)
            widget.setObjectName(name)
            widget.setPlaceholderText(hint)
            widget.setMaximumHeight(height)
            return widget

        self.creation_values_edit = text_edit("metatypeCreationValues", "Property values, one per line")
        self.creation_default_edit = QLineEdit(group)
        self.creation_default_edit.setObjectName("metatypeCreationDefault")
        self.creation_default_edit.setPlaceholderText("Default value (must be chosen; one of the values)")
        self.creation_filter_edit = QLineEdit(group)
        self.creation_filter_edit.setObjectName("metatypeCreationFilter")
        self.creation_filter_edit.setPlaceholderText("Filter: parent property names, comma separated (optional)")
        self.creation_order_edit = text_edit(
            "metatypeCreationOrder", "Optional sort order, one 'value;number' per line (1-255)")
        self.creation_conditions_edit = text_edit(
            "metatypeCreationConditions",
            "go_propvalues conditions, one 'value;condition' per line (needed when Step 4a has exceptions)")
        for label, widget in (("Values:", self.creation_values_edit), ("Default:", self.creation_default_edit),
                              ("Filter:", self.creation_filter_edit), ("Sort order:", self.creation_order_edit),
                              ("Conditions:", self.creation_conditions_edit)):
            form.addRow(label, widget)
        box.addLayout(form)
        self.value_model = ArticleValueModel(ArticleValueTable([], []), group)
        self.value_proxy = ArticleValueProxy(group)
        self.value_proxy.setSourceModel(self.value_model)
        self.value_table = QTableView(group)
        self.value_table.setObjectName("metatypeArticleValueTable")
        self.value_table.setModel(self.value_proxy)
        self.value_table.setSortingEnabled(True)
        self.value_table.setMinimumHeight(140)
        self.value_table.horizontalHeader().setStretchLastSection(True)
        self.value_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                                         | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.value_problem_filter = QComboBox(group)
        self.value_problem_filter.setObjectName("metatypeArticleValueFilter")
        self.value_problem_filter.addItems(["All articles", "Problems only"])
        self.value_problem_filter.currentIndexChanged.connect(lambda i: self.value_proxy.set_problems_only(bool(i)))
        self.creation_status = QLabel("Creation is disabled until every prerequisite is met.", group)
        self.creation_status.setObjectName("metatypeCreationStatus")
        self.creation_status.setWordWrap(True)
        self.creation_plan_button = QPushButton("Plan creation", group)
        self.creation_plan_button.setObjectName("metatypeCreationPlanButton")
        self.creation_plan_button.clicked.connect(self.plan_creation)
        self.creation_values_edit.textChanged.connect(self._sync_value_table)
        self.value_model.edited.connect(self._update_creation_state)
        self.creation_default_edit.textChanged.connect(self._update_creation_state)
        self.creation_filter_edit.textChanged.connect(self._update_creation_state)
        self.creation_order_edit.textChanged.connect(self._update_creation_state)
        self.creation_conditions_edit.textChanged.connect(self._update_creation_state)
        row = QHBoxLayout()
        row.addWidget(QLabel("Per-article values (every article needs its own explicit value):", group), 1)
        row.addWidget(self.value_problem_filter)
        box.addLayout(row)
        box.addWidget(self.value_table)
        box.addWidget(self.creation_status)
        box.addWidget(self.creation_plan_button)
        self._workspace_layouts["articles"].addWidget(group)
        self.last_creation_plan: CreationPlan | None = None
        self.last_write_result = None

    @staticmethod
    def _lines(widget: QPlainTextEdit) -> list[str]:
        return [line.strip(" \t") for line in widget.toPlainText().splitlines() if line.strip(" \t")]

    def _pairs(self, widget: QPlainTextEdit) -> tuple[dict[str, str], list[str]]:
        pairs: dict[str, str] = {}
        problems: list[str] = []
        for line in self._lines(widget):
            key, sep, rest = line.partition(";")
            if not sep or not key.strip() or not rest.strip():
                problems.append(f"'{line}' is not 'value;text'.")
            elif key.strip() in pairs:
                problems.append(f"'{key.strip()}' is listed twice.")
            else:
                pairs[key.strip()] = rest.strip()
        return pairs, problems

    def _sync_value_table(self, *_args) -> None:
        """Rebuild the per-article table for the Step 4 articles and current values; entered values are kept."""
        articles = list(dict.fromkeys(self._owner_articles()))
        values = list(dict.fromkeys(self._lines(self.creation_values_edit)))
        self.value_model.beginResetModel()
        self.value_model.table.rebuild(articles, values, config_ids_for(self.articles_session.result, articles))
        self.value_model.endResetModel()
        self._update_creation_state()

    def _current_owner(self) -> str | None:
        if self.owner_selection is not None and self.owner_selection.owner:
            return self.owner_selection.owner
        choice = build_owner_choice(self.articles_session.result, self._owner_articles())
        return choice.resolution.metatype_id if choice.state is OwnerState.UNIQUE else None

    def creation_inputs(self) -> tuple[CreationInputs, list[str]]:
        config = self._context.config
        identity, validity = self._service.identity, self._service.validity
        order, order_problems = self._pairs(self.creation_order_edit)
        conditions, condition_problems = self._pairs(self.creation_conditions_edit)
        numbers = {value: int(number) if number.isdigit() else -1 for value, number in order.items()}
        values = list(dict.fromkeys(self._lines(self.creation_values_edit)))
        wanted = config.metatype_text_fallback_encoding.strip().lower()
        fallback = {"cp1252": Encoding.CP1252, "utf-8": Encoding.UTF8}.get(wanted)
        inputs = CreationInputs(
            owner=self._current_owner(), property_name=identity.name if identity else "", values=values,
            default=self.creation_default_edit.text(), filter_names=self.creation_filter_edit.text(),
            article_values=self.value_model.table,
            mode_policy=ModePolicy(confirmed=config.metatype_mode_policy_confirmed),
            order=numbers, conditions=conditions,
            exceptions_recorded=bool(validity is not None and not validity.accepts_full_value_set),
            translations=self._service.translations, text_fallback_encoding=fallback)
        return inputs, order_problems + condition_problems

    def plan_creation(self) -> CreationPlan:
        inputs, input_problems = self.creation_inputs()
        plan = plan_property_creation(self.articles_session.result, inputs)
        plan.blockers.extend(input_problems)
        self.last_creation_plan = plan
        auth, _problems = self.staging_authorization()
        text = plan.review_text()
        if auth is not None and plan.ok:
            text = staged_review(plan.plan, auth)
        self.articles_diagnostics.setPlainText(text)
        self._update_creation_state()
        return plan

    def creation_blockers(self) -> list[str]:
        """Every reason creation is disabled (empty only when all prerequisites hold)."""
        inputs, input_problems = self.creation_inputs()
        plan = plan_property_creation(self.articles_session.result, inputs)
        reasons = list(plan.blockers) + input_problems + list(plan.plan.problems)
        if not reasons and not plan.plan.ok:
            reasons.append("The creation plan is not verified.")
        auth, auth_problems = self.staging_authorization()
        if auth is None:
            reasons.extend(auth_problems)
        return reasons

    def can_create(self) -> bool:
        return not self.creation_blockers()

    def _update_creation_state(self, *_args) -> None:
        if not hasattr(self, "creation_status"):
            return
        result = self.articles_session.result
        blockers = self.creation_blockers() if result is not None and result.series else ["No series is loaded."]
        self.articles_create_button.setEnabled(bool(result is not None and result.series))
        self.creation_status.setText(
            "Ready: review and confirm to write to staging." if not blockers else
            f"Creation disabled ({len(blockers)} reason(s)): " + " | ".join(blockers[:3])
            + (" ..." if len(blockers) > 3 else ""))

    # -- owner Metatype ---------------------------------------------------------------------------------------
    def _owner_articles(self) -> list[str]:
        branch = self._service.branch
        if branch is not None and branch.articles:
            return list(branch.articles)
        keys = [i.data(KEY_ROLE) for i in self.articles_table.selectionModel().selectedRows()]
        return [k[2] for k in keys if len(k) == 3 and k[0] != "<line>"]

    def choose_owner(self, dialog_factory=OwnerSelectionDialog) -> OwnerSelection:
        """Resolve the owner; ask the user only when it is ambiguous. Cancelling keeps everything as it was."""
        identity = self._service.identity
        choice = build_owner_choice(self.articles_session.result, self._owner_articles(),
                                    identity.name if identity is not None else "")
        selection = OwnerSelection(choice, identity.name if identity is not None else "")
        previous = self.owner_selection
        if choice.state is not OwnerState.UNIQUE:
            dialog = dialog_factory(choice, self)
            if dialog.exec() and dialog.selected_id:
                selection.select(dialog.selected_id)
            elif previous is not None and previous.choice.candidates == choice.candidates:
                selection = previous                      # cancelled: keep the earlier explicit choice
        self.owner_selection = selection
        self._show_owner()
        return selection

    def _show_owner(self) -> None:
        selection = self.owner_selection
        if selection is None:
            self.articles_owner_label.setText("Owner Metatype: not resolved yet.")
            return
        state = selection.choice.state
        if state is OwnerState.UNIQUE:
            text = f"Owner Metatype: {selection.owner} (unique - every listed article belongs to it)."
        elif state is OwnerState.NONE:
            text = f"Owner Metatype: NO valid candidate. {selection.choice.explanation}"
        elif selection.owner:
            text = f"Owner Metatype: {selection.owner} (explicitly selected from {len(selection.choice.candidates)} candidates)."
        else:
            text = (f"Owner Metatype: {len(selection.choice.candidates)} candidates, none selected - "
                    f"{selection.choice.explanation}")
        self.articles_owner_label.setText(text)

    # -- staged persistence -----------------------------------------------------------------------------------
    def staging_authorization(self):
        config = self._context.config
        return load_authorization(config.metatype_staging_root, config.metatype_repository_root,
                                  config.metatype_staging_authorised_by)

    def apply_to_staging(self, confirm=None, backup_root: Path | None = None):
        """Review, confirm and write the verified article edits to the authorised staging copy (never production)."""
        plan = plan_article_edits(self.articles_session)
        result = self._apply_plan(plan, confirm, backup_root, "Apply to staging")
        if result is not None:
            if result.success:
                done = self.articles_session.mark_applied(plan, result)
                self.articles_model.refresh_rows()
                self.articles_diagnostics.appendPlainText(
                    f"\n{done} edit(s) are now shown as written (verified in staging). The loaded source snapshot is "
                    "unchanged; Refresh reloads it.")
            else:
                self.articles_session.mark_failed(plan, "; ".join(result.problems))
                self.articles_model.refresh_rows()
        return result

    def _apply_plan(self, plan, confirm, backup_root, title):
        auth, problems = self.staging_authorization()
        if auth is None:
            self.articles_diagnostics.setPlainText(
                "Writing is disabled. " + " ".join(problems) + "\n\n" + (plan.review_text() if plan.files else ""))
            return None
        text = staged_review(plan, auth)
        self.articles_diagnostics.setPlainText(text)
        if not plan.ok:
            return None
        ask = confirm or (lambda review: QMessageBox.question(
            self, title, review + "\n\nWrite exactly these changes to the staging copy?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Yes)
        if not ask(text):
            return None                                   # cancelled: nothing written, pending edits stay as they are
        result = apply_plan(plan, auth, plan_fingerprint(plan, auth),
                            backup_root or Path(__file__).resolve().parents[2] / "workspace" / "metatype_backups")
        self.last_write_result = result
        self.articles_diagnostics.setPlainText(result.summary())
        return result

    def create_property(self, confirm=None, backup_root: Path | None = None):
        """Create the polymorphic property in the authorised staging copy; blocked unless every prerequisite holds."""
        blockers = self.creation_blockers()
        if blockers:
            self.articles_diagnostics.setPlainText(
                "Creation is disabled:\n" + "\n".join(f"  - {b}" for b in blockers))
            return None
        plan = self.plan_creation()
        result = self._apply_plan(plan.plan, confirm, backup_root, "Create property in staging")
        self._update_creation_state()
        return result

    def create_from_articles(self) -> None:
        """Create when every prerequisite holds (after review and confirmation); otherwise show exactly why."""
        if self.can_create():
            self.create_property()
            return
        self.articles_diagnostics.setPlainText(
            "\n".join(self.articles_session.creation_blockers()) + "\n\nCreation prerequisites not met:\n"
            + "\n".join(f"  - {b}" for b in self.creation_blockers()))

    def has_pending_article_edits(self) -> bool:
        return self.articles_session.pending_count > 0

    def _articles_edited(self) -> None:
        self._update_article_actions()

    def _show_selected_row_diagnostics(self, *_args) -> None:
        rows = self.articles_table.selectionModel().selectedRows()
        if len(rows) != 1:
            return
        key = rows[0].data(KEY_ROLE)
        issues = self.articles_session.issues(key)
        self.articles_diagnostics.setPlainText(" / ".join(map(str, key)) + "\n" + (
            "\n".join(f"{i.severity.upper()} [{i.code}] {i.message}" for i in issues) or "No findings."))

    def _update_article_actions(self) -> None:
        session = self.articles_session
        loaded = session.result is not None and bool(session.result.series) and session.result.series == self._service.series
        pending = session.pending_count
        counts = session.counts()
        self.articles_counts.setText(
            f"{counts['total']} article(s): {counts['mapped']} mapped, {counts['unmapped']} unmapped | "
            f"{counts['valid']} valid, {counts['warnings']} warning, {counts['invalid']} invalid"
            + (f", {counts['unavailable']} unavailable" if counts['unavailable'] else "") + " | "
            f"{pending} pending change(s)")
        self.articles_refresh_button.setEnabled(loaded)
        self.articles_validate_button.setEnabled(loaded)
        self.articles_review_button.setEnabled(pending > 0)
        self.articles_discard_button.setEnabled(pending > 0)
        self.articles_owner_button.setEnabled(loaded)
        self.articles_apply_button.setEnabled(pending > 0)
        self.articles_create_button.setEnabled(loaded)   # clickable to inspect blockers
        self._sync_value_table()

    def _show_articles(self) -> None:
        result = self._context.metatype_article_service.last_result
        if result is None or result.series != self._service.series:
            self.articles_session.refresh(ArticleReconciliation("", ReconciliationStatus.FAILED))
            self.articles_model.reload()
            self.articles_load_status.setText(
                "No articles loaded. Select a series and choose Load Series to read its article list.")
            self.articles_diagnostics.clear()
            self._update_article_actions()
            return
        if self.articles_session.result is not result:
            self.articles_session.refresh(result)
        self.articles_model.reload()
        self.articles_table.resizeColumnsToContents()
        verdict = {
            "complete": "Load complete",
            "partial": "PARTIAL load - this is not a complete reconciliation",
            "failed": "Load FAILED - no reconciliation is available",
        }[result.status.value]
        unmapped = sum(1 for row in result.rows if row.status == "Needs assignment")
        text = f"{verdict}: {len(result.rows)} article(s), {unmapped} needing assignment."
        if result.unavailable_fields:
            text += " Fields not declared by this schema: " + ", ".join(result.unavailable_fields) + "."
            if {"metatypeid", "childparentid"} & set(result.unavailable_fields):
                text += " Undeclared mapping columns cannot be edited."
        self.articles_load_status.setText(text)
        lines = [f"{d.severity.upper()} [{d.code}] {d.message}"
                 + (f" ({d.file}" + (f":{d.line}" if d.line else "") + ")" if d.file else "")
                 for d in result.diagnostics]
        self.articles_diagnostics.setPlainText("\n".join(lines) if lines else "No source problems found.")
        self._update_article_actions()

    # -- stage readiness --------------------------------------------------------------------------------------
    def is_ready_for_step(self, step) -> bool:
        """Report readiness for the requested sidebar stage, not for the shared page as a whole."""
        from core.enums import WorkflowStep

        status = self._service.stage_status()
        done = {item.key: item.state is StepState.DONE for item in status.steps}
        sources_current = not any("changed since" in warning.lower() for warning in status.warnings)
        if not sources_current:
            return False
        if step == WorkflowStep.METATYPE_ARTICLES:
            return done.get("1", False) and done.get("2", False) and done.get("4", False)
        if step == WorkflowStep.METATYPE_PROPERTIES:
            return done.get("3", False)
        if step == WorkflowStep.METATYPE_VALUES:
            return done.get("4a", False)
        if step == WorkflowStep.METATYPE_TEXTS:
            return done.get("5", False)
        # These stages are not implemented yet; never report them as complete.
        if step in (WorkflowStep.METATYPE_SETUP, WorkflowStep.METATYPE_RELATIONS):
            return False
        if step == WorkflowStep.METATYPE_REVIEW:
            return self._service.confirmation_is_current() and status.complete
        return False

    # -- workflow-panel integration ---------------------------------------------------------------------------
    def select_workflow_stage(self, step) -> None:
        """Select the content page associated with a left-panel Metatype workflow stage."""
        from core.enums import WorkflowStep

        indexes = {
            WorkflowStep.METATYPE_CREATION: 1,
            WorkflowStep.METATYPE_ARTICLES: 0,
            WorkflowStep.METATYPE_PROPERTIES: 1,
            WorkflowStep.METATYPE_VALUES: 2,
            WorkflowStep.METATYPE_TEXTS: 3,
            WorkflowStep.METATYPE_SETUP: 4,
            WorkflowStep.METATYPE_RELATIONS: 5,
            WorkflowStep.METATYPE_REVIEW: 6,
        }
        if step in indexes:
            self.workspace_stack.setCurrentIndex(indexes[step])

    # -- workspace lifecycle ------------------------------------------------------------------------------------
    def refresh(self) -> None:
        """Reload the series list and show the workflow state kept in the session (no repository scan)."""
        current = self._service.series or self.series_combo.currentData() or ""
        self.series_combo.blockSignals(True)
        self.series_combo.clear()
        for choice in self._service.list_series():
            suffix = "" if choice.has_schema else " (no Metatype data)"
            self.series_combo.addItem(choice.name + suffix, choice.name)
        index = self.series_combo.findData(current)
        if index >= 0:
            self.series_combo.setCurrentIndex(index)
        self.series_combo.blockSignals(False)
        self.load_button.setEnabled(self.series_combo.count() > 0)
        self.load_button.setText(
            "Reload Series (reset answers)" if self._service.inspection is not None else "Load Series")
        self._sync_template_action()
        self._show_status()
        self._restore_validity_widgets()
        self._sync_translation_table()
        self._show_articles()

    def _sync_template_action(self, *_args) -> None:
        """Offer template initialization only for a series without existing Metatype schema."""
        series = self.series_combo.currentData()
        enabled = False
        if series:
            try:
                enabled = self._template_service.inspect(str(series)).status == "empty"
            except (OSError, ValueError):
                enabled = False
        self.start_scratch_button.setEnabled(bool(series))
        self.load_button.setEnabled(bool(series))

    def start_metatype_from_scratch(self):
        """Explicitly initialize a selected series; existing series are always reused."""
        series = self.series_combo.currentData()
        if not series:
            return None
        try:
            inspection = self._template_service.inspect(str(series))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Metatype templates", str(exc))
            return None
        if inspection.status == "existing":
            QMessageBox.information(
                self, "Existing Metatype found",
                "This series already contains Metatype data. The existing files will be used; no templates were copied.",
            )
            self.start_scratch_button.setEnabled(False)
            self.load_button.setEnabled(True)
            return self.load_series()
        if inspection.status == "partial":
            QMessageBox.warning(
                self, "Partial Metatype data detected",
                inspection.message + "\n\nInitialization is blocked to prevent mixing template files with existing data. Resolve the partial directory manually, then retry.",
            )
            return inspection
        answer = QMessageBox.question(
            self, "Start Metatype from Scratch",
            f"Copy the complete empty template set into this series?\n\nSeries: {series}\nTarget: {inspection.target}\n\n"
            "No existing file will be overwritten. This only copies templates; it does not build the database.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return None
        try:
            result = self._template_service.initialize(str(series))
        except (OSError, ValueError) as exc:
            self.status_output.setPlainText("Metatype initialization failed: " + str(exc) + "\nNo template files were copied.")
            QMessageBox.critical(self, "Metatype initialization failed", str(exc))
            return None
        if result.status == "existing":
            QMessageBox.information(self, "Existing Metatype found", result.message)
            self.load_button.setEnabled(True)
            self.start_scratch_button.setEnabled(False)
            return self.load_series()
        if result.status != "initialized":
            self.status_output.setPlainText(result.message)
            QMessageBox.warning(self, "Metatype initialization blocked", result.message)
            return result
        QMessageBox.information(
            self, "Metatype templates copied",
            f"{result.message}\n\nTarget: {result.target}\n\nDatabase build was not started.",
        )
        self.refresh()
        index = self.series_combo.findData(series)
        if index >= 0:
            self.series_combo.setCurrentIndex(index)
        return self.load_series()

    # -- actions -----------------------------------------------------------------------------------------------------
    def load_series(self) -> PolymorphicStageStatus | None:
        series = self.series_combo.currentData()
        if not series:
            return None
        switching = bool(self._service.series and self._service.series != series
                         and self._service.inspection is not None)
        reloading = bool(self._service.series == series and self._service.inspection is not None)
        if (switching or reloading) and self.articles_session.pending_count:
            answer = QMessageBox.question(
                self, "Unsaved article edits",
                f"{self.articles_session.pending_count} pending article edit(s) will be discarded. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                index = self.series_combo.findData(self._service.series)
                if index >= 0:
                    self.series_combo.setCurrentIndex(index)
                return self._service.stage_status()
        if switching:
            answer = QMessageBox.question(
                self, "Switch Metatype series",
                f"Discard the current answers for '{self._service.series}' and load '{series}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                index = self.series_combo.findData(self._service.series)
                if index >= 0:
                    self.series_combo.setCurrentIndex(index)
                return self._service.stage_status()
        self.findings_output.clear()
        for edit in (self.articles_edit, self.conditions_edit):
            edit.clear()
        self.scope_combo.setCurrentIndex(0)
        self.values_combo.setCurrentIndex(0)
        self.validity_combo.setCurrentIndex(0)
        self.validity_table.setRowCount(0)
        self.translation_table.setRowCount(0)
        self.spec_output.clear()
        status = (self._service.discard_and_start(series) if switching or reloading
                  else self._service.start(series))
        self.load_button.setText("Reload Series (reset answers)")
        self._show_status()
        if self._service.series == series and self._service.inspection is not None:
            self._load_articles(str(series))
        return status

    def confirm_identity(self) -> IdentityResult:
        result = self._service.submit_property_identity(self.name_edit.text(), self.label_edit.text())
        self.findings_output.setPlainText(self._service.findings_text(result))
        self._show_status()
        return result

    def confirm_branch(self) -> BranchResult:
        articles = self.articles_edit.toPlainText().splitlines()
        conditions = self.conditions_edit.toPlainText().splitlines()
        result = self._service.submit_polymorphism_branch(
            articles, self.scope_combo.currentData(), conditions, self.values_combo.currentData())
        self.findings_output.setPlainText(self._service.findings_text(result))
        self._show_status()
        return result

    def confirm_validity(self) -> ValidityResult:
        result = self._service.submit_value_validity(self.validity_combo.currentData(), self._validity_rows())
        self.findings_output.setPlainText(self._service.findings_text(result))
        self._show_status()
        return result

    def confirm_specification(self) -> SpecificationResult:
        result = self._service.confirm_specification()
        self.findings_output.setPlainText(self._service.findings_text(result))
        self._show_status()
        return result

    def confirm_translations(self) -> TranslationResult:
        result = self._service.submit_translations(self._translation_rows())
        self.findings_output.setPlainText(self._service.findings_text(result))
        self._show_status()
        return result

    def _translation_rows(self) -> list[TranslationRow]:
        def text(row: int, column: int) -> str:
            item = self.translation_table.item(row, column)
            return item.text() if item else ""

        return [TranslationRow(text(i, 0), TranslationKind.PROPERTY if i == 0 else TranslationKind.VALUE,
                               text(i, 1), text(i, 2), text(i, 3), text(i, 4))
                for i in range(self.translation_table.rowCount())]

    def _sync_translation_table(self) -> None:
        """Rows follow the confirmed Step 3/4a data; text already typed (or kept in the session) is carried over."""
        table = self.translation_table
        rows = self._service.translation_rows()
        keys = [r.technical for r in rows]
        current = [table.item(i, 0).text() if table.item(i, 0) else "" for i in range(table.rowCount())]
        if current == keys:
            for index, row in enumerate(rows[:1]):                      # the property's EN label can change in Step 3
                self._set_cell(index, 1, row.en, editable=False)
            return
        typed = {r.technical: r for r in self._translation_rows() if r.technical}
        table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            prior = typed.get(row.technical)
            is_property = row.kind is TranslationKind.PROPERTY
            self._set_cell(index, 0, row.technical, editable=False)
            self._set_cell(index, 1, row.en if is_property or prior is None or not prior.en else prior.en,
                           editable=not is_property)
            for column, name in ((2, "de"), (3, "fr"), (4, "nl")):
                mine = getattr(prior, name, "") if prior is not None else ""
                self._set_cell(index, column, mine or getattr(row, name), editable=True)

    def _set_cell(self, row: int, column: int, text: str, editable: bool) -> None:
        item = QTableWidgetItem(text)
        if not editable:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.translation_table.setItem(row, column, item)

    def add_value_row(self) -> None:
        self.validity_table.insertRow(self.validity_table.rowCount())

    def remove_value_row(self) -> None:
        row = self.validity_table.currentRow()
        if row >= 0:
            self.validity_table.removeRow(row)

    def _validity_rows(self) -> list[ValueValidityRow]:
        rows: list[ValueValidityRow] = []
        for index in range(self.validity_table.rowCount()):
            value = self.validity_table.item(index, 0)
            cell = self.validity_table.item(index, 1)
            all_articles, articles = parse_validity_cell(cell.text() if cell else "")
            rows.append(ValueValidityRow(value.text() if value else "", all_articles, articles))
        return rows

    def _validity_answer_changed(self) -> None:
        self.validity_table.setEnabled(self.validity_combo.currentData() is False and self._validity_group.isEnabled())

    def _restore_validity_widgets(self) -> None:
        """Show the Step 4a input kept in the session again, unless the user has already typed here."""
        draft = self._service.validity_draft
        if draft is None or self.validity_combo.currentIndex() != 0 or self.validity_table.rowCount():
            return
        self.validity_combo.setCurrentIndex(self.validity_combo.findData(draft.accepts_full_value_set))
        for row in draft.rows:
            index = self.validity_table.rowCount()
            self.validity_table.insertRow(index)
            self.validity_table.setItem(index, 0, QTableWidgetItem(row.value))
            self.validity_table.setItem(index, 1, QTableWidgetItem(
                ALL_MARKER if row.all_articles else ", ".join(row.articles)))

    def _scope_changed(self) -> None:
        scoped = self.scope_combo.currentData() == SwitchScope.SCOPED.value
        self.conditions_edit.setEnabled(scoped and self._branch_group.isEnabled())

    # -- presentation ----------------------------------------------------------------------------------------------
    def _show_status(self) -> None:
        status = self._service.stage_status()
        self.status_output.setPlainText(self._service.summary_text())
        done = {step.key: step.state is StepState.DONE for step in status.steps}
        self._identity_group.setEnabled(done.get("1", False))
        self._branch_group.setEnabled(done.get("3", False))
        self._scope_changed()
        self._validity_group.setEnabled(done.get("4", False))
        self._validity_answer_changed()
        self._translation_group.setEnabled(done.get("4a", False))
        self._sync_translation_table()
        summary = self._service.specification_text()
        self._spec_group.setEnabled(summary is not None)
        self.spec_output.setPlainText(summary or "")
        known = self._service.known_articles
        self.articles_hint.setText(
            "The series' go_articles could not be read; articles are not checked." if known is None else
            f"{len({a.article_nr for a in known})} article(s) in this series, e.g. "
            + ", ".join(list(dict.fromkeys(a.article_nr for a in known))[:8]))
        self.children_button.setEnabled(status.children_unlocked)
        self.children_button.setToolTip(
            "Ready." if status.children_unlocked else
            "Locked until the polymorphic stage is complete: " + "; ".join(status.blocking[:3]))
