"""Metatype Repository Analysis workspace page.

Presents the read-only HMX repository scan. All filesystem work lives in
``MetatypeRepositoryService``; this page only collects the root, triggers the
scan and renders the structured result.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from models.metatype_scan import EntryKind, MetatypeScanResult, ScanStatus
from models.metatype_relationships import MetatypeRelationshipReport
from models.metatype_tables import MetatypeFamilyTables
from ui.components._styles import primary_button_qss, secondary_button_qss
from ui.pages.base_page import BasePage

_COLUMNS = ("Entry", "Kind", "Status", "Rule", "Numbered dirs", "Warnings", "Errors")


class MetatypeRepositoryPage(BasePage):
    """Scan the HMX repository and list each family's build classification."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Repository Analysis",
            description="Read-only scan of the HMX repository: which families have Metatype data and are built.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._service = context.metatype_repository_service
        self._loader = context.metatype_table_loader_service
        self._relationships = context.metatype_relationship_service
        self._series = context.metatype_series_service
        self._patterns = context.metatype_pattern_service

        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        row = QHBoxLayout()
        self._root_edit = QLineEdit(self._service.default_root, panel)
        self._root_edit.setObjectName("metatypeRootEdit")
        self._root_edit.setPlaceholderText("HMX repository root")
        browse = QPushButton("Browse…", panel)
        browse.setObjectName("metatypeBrowseButton")
        browse.setStyleSheet(secondary_button_qss("metatypeBrowseButton"))
        browse.clicked.connect(self._browse)
        self.scan_button = QPushButton("Scan Repository", panel)
        self.scan_button.setObjectName("metatypeScanButton")
        self.scan_button.setStyleSheet(primary_button_qss("metatypeScanButton"))
        self.scan_button.clicked.connect(self.run_scan)
        self.export_button = QPushButton("Export JSON…", panel)
        self.export_button.setObjectName("metatypeExportButton")
        self.export_button.setStyleSheet(secondary_button_qss("metatypeExportButton"))
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export)
        row.addWidget(self._root_edit, 1)
        row.addWidget(browse)
        row.addWidget(self.scan_button)
        row.addWidget(self.export_button)
        layout.addLayout(row)

        self.summary_label = QLabel("No scan has been run.", panel)
        self.summary_label.setObjectName("metatypeScanSummary")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, len(_COLUMNS), panel)
        self.table.setObjectName("metatypeFamilyTable")
        self.table.setHorizontalHeaderLabels(list(_COLUMNS))
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)
        self.table.itemSelectionChanged.connect(self._update_load_button)

        load_row = QHBoxLayout()
        self.load_button = QPushButton("Load Tables", panel)
        self.load_button.setObjectName("metatypeLoadButton")
        self.load_button.setStyleSheet(secondary_button_qss("metatypeLoadButton"))
        self.load_button.setToolTip("Read the selected family's go_*.csv tables (read-only).")
        self.load_button.setEnabled(False)
        self.load_button.clicked.connect(self.load_selected_family)
        load_row.addWidget(self.load_button)
        self.resolve_button = QPushButton("Resolve Relationships", panel)
        self.resolve_button.setObjectName("metatypeResolveButton")
        self.resolve_button.setStyleSheet(secondary_button_qss("metatypeResolveButton"))
        self.resolve_button.setToolTip("Check references and duplicate keys between the selected family's tables.")
        self.resolve_button.setEnabled(False)
        self.resolve_button.clicked.connect(self.resolve_selected_family)
        load_row.addWidget(self.resolve_button)
        self.inspect_button = QPushButton("Inspect Series", panel)
        self.inspect_button.setObjectName("metatypeInspectButton")
        self.inspect_button.setStyleSheet(secondary_button_qss("metatypeInspectButton"))
        self.inspect_button.setToolTip("Summarise the selected series' existing Metatype conventions (read-only).")
        self.inspect_button.setEnabled(False)
        self.inspect_button.clicked.connect(self.inspect_selected_series)
        load_row.addWidget(self.inspect_button)
        load_row.addStretch(1)
        layout.addLayout(load_row)

        pattern_row = QHBoxLayout()
        pattern_row.addWidget(QLabel("Kind of Metatype:", panel))
        self.pattern_combo = QComboBox(panel)
        self.pattern_combo.setObjectName("metatypePatternCombo")
        for option in self._patterns.options():
            self.pattern_combo.addItem(option.label, option.pattern.value)
            self.pattern_combo.setItemData(
                self.pattern_combo.count() - 1, option.description, Qt.ItemDataRole.ToolTipRole)
        self.pattern_button = QPushButton("Select Pattern", panel)
        self.pattern_button.setObjectName("metatypePatternButton")
        self.pattern_button.setStyleSheet(secondary_button_qss("metatypePatternButton"))
        self.pattern_button.setToolTip("Step 2: record which kind of Metatype to create (needs Inspect Series first).")
        self.pattern_button.setEnabled(False)
        self.pattern_button.clicked.connect(self.select_pattern)
        pattern_row.addWidget(self.pattern_combo)
        pattern_row.addWidget(self.pattern_button)
        pattern_row.addStretch(1)
        layout.addLayout(pattern_row)

        self.load_output = QPlainTextEdit(panel)
        self.load_output.setObjectName("metatypeLoadOutput")
        self.load_output.setReadOnly(True)
        self.load_output.setMaximumHeight(180)
        self.load_output.setPlaceholderText("Select a product family and choose Load Tables.")
        layout.addWidget(self.load_output)

        self.add_content(panel)
        self.refresh()

    # -- workspace lifecycle -----------------------------------------------
    def refresh(self) -> None:
        """Show the session's latest scan result, if any (never rescans)."""
        result = self._service.last_result
        if result is not None:
            self._show(result)

    # -- actions -------------------------------------------------------------
    def run_scan(self) -> MetatypeScanResult:
        result = self._service.scan(self._root_edit.text().strip())
        self._show(result)
        return result

    def selected_family_id(self) -> str:
        """Family id of the selected row if it is a confirmed product family, else ""."""
        row = self.table.currentRow()
        if row < 0 or self.table.item(row, 1) is None:
            return ""
        if self.table.item(row, 1).text() != EntryKind.PRODUCT_FAMILY.value:
            return ""
        return self.table.item(row, 0).text()

    def _update_load_button(self) -> None:
        selected = bool(self.selected_family_id())
        self.load_button.setEnabled(selected)
        self.resolve_button.setEnabled(selected)
        self.inspect_button.setEnabled(selected)
        self.pattern_button.setEnabled(self._patterns.can_select(self.selected_family_id()))

    def load_selected_family(self) -> MetatypeFamilyTables | None:
        family_id = self.selected_family_id()
        if not family_id:
            return None
        result = self._loader.load_family(family_id, root=self._root_edit.text().strip() or None)
        self.load_output.setPlainText(self._loader.summary_text(result))
        return result

    def resolve_selected_family(self) -> MetatypeRelationshipReport | None:
        family_id = self.selected_family_id()
        if not family_id:
            return None
        root = self._root_edit.text().strip() or None
        report = self._relationships.resolve_family(family_id, root=root)
        tables = self._loader.last_result
        self.load_output.setPlainText(
            self._loader.summary_text(tables) + "\n\n" + self._relationships.summary_text(report))
        return report

    def inspect_selected_series(self):
        family_id = self.selected_family_id()
        if not family_id:
            return None
        result = self._series.inspect_series(family_id, root=self._root_edit.text().strip() or None)
        self.load_output.setPlainText(self._series.summary_text(result))
        self._update_load_button()
        return result

    def select_pattern(self):
        family_id = self.selected_family_id()
        result = self._patterns.select_pattern(family_id, self.pattern_combo.currentData())
        self.load_output.setPlainText(self._patterns.summary_text(result))
        return result

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select HMX repository root", self._root_edit.text())
        if folder:
            self._root_edit.setText(folder)

    def _export(self) -> None:
        result = self._service.last_result
        if result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export scan report", "metatype_scan.json", "JSON (*.json)")
        if not path:
            return
        try:
            self._service.export_json(result, path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Export failed", str(exc))

    # -- rendering -------------------------------------------------------------
    def _show(self, result: MetatypeScanResult) -> None:
        self.export_button.setEnabled(True)
        self.summary_label.setText(self._service.summary_text(result))
        self.table.setRowCount(0)
        if result.status is ScanStatus.FAILED:
            return
        self.table.setRowCount(len(result.families))
        for row, family in enumerate(result.families):
            classification = family.classification
            values = (
                family.family_id,
                family.entry_kind.value,
                classification.status.value if classification else "",
                classification.rule if classification else "",
                ", ".join(d.name for d in family.numbered_directories),
                str(len(family.warnings)),
                str(len(family.errors)),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if classification:
                    item.setToolTip(classification.summary)
                if column >= 5:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, column, item)
