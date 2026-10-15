"""Metatype creation workspace: the polymorphic Metatype stage.

The runtime creation page. It works directly on the configured HMX repository, independently of any PDM
product or connection: pick a series, load it, name the polymorphic property (template Step 3), and see
whether the stage is complete. Repository scanning, table loading and relationship checks are backend
rules and are not exposed as controls here. All logic lives in ``MetatypeCreationService``.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from models.metatype_creation import (
    BranchResult, IdentityResult, PolymorphicStageStatus, SpecificationResult, StepState, SwitchScope, TranslationKind, TranslationResult,
    TranslationRow, ValidityResult, ValueValidityRow,
)
from services.metatype.value_validity import ALL_MARKER, parse_validity_cell
from ui.components._styles import primary_button_qss, secondary_button_qss
from ui.pages.base_page import BasePage


class MetatypeCreationPage(BasePage):
    """Select a series, load it and create the polymorphic Metatype property."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Create Metatype",
            description="Polymorphic Metatype first: select a series from the HMX repository, load its data, "
                        "then name the property and answer the article questions. Nothing is written to the repository.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._service = context.metatype_creation_service

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
        row.addWidget(QLabel("Series:", panel))
        row.addWidget(self.series_combo, 1)
        row.addWidget(self.load_button)
        layout.addLayout(row)

        self.status_output = QPlainTextEdit(panel)
        self.status_output.setObjectName("metatypeStageStatus")
        self.status_output.setReadOnly(True)
        self.status_output.setMaximumHeight(170)
        self.status_output.setPlaceholderText("Select a series and choose Load Series.")
        layout.addWidget(self.status_output)

        self.workspace_tabs = QTabWidget(panel)
        self.workspace_tabs.setObjectName("metatypeWorkspaceTabs")
        self.workspace_tabs.setDocumentMode(True)
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
            page = QWidget(self.workspace_tabs)
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(8, 8, 8, 8)
            page_layout.setSpacing(8)
            self.workspace_tabs.addTab(page, title)
            self._workspace_pages[key] = page
            self._workspace_layouts[key] = page_layout
        layout.addWidget(self.workspace_tabs, 1)

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
        self._show_status()
        self._restore_validity_widgets()
        self._sync_translation_table()

    # -- actions -----------------------------------------------------------------------------------------------------
    def load_series(self) -> PolymorphicStageStatus | None:
        series = self.series_combo.currentData()
        if not series:
            return None
        self.findings_output.clear()
        for edit in (self.articles_edit, self.conditions_edit):
            edit.clear()
        self.scope_combo.setCurrentIndex(0)
        self.values_combo.setCurrentIndex(0)
        self.validity_combo.setCurrentIndex(0)
        self.validity_table.setRowCount(0)
        self.translation_table.setRowCount(0)
        self.spec_output.clear()
        status = self._service.start(series)
        self._show_status()
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
