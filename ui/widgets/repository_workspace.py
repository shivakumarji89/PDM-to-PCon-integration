"""Shared Repository Workspace.

Provides the single repository-browser/open/extract workflow used by modules
that consume published repository snapshots. Module-specific pages consume the
resulting ApplicationContext.mdb_import_snapshot instead of implementing their
own repository loader.

The imported released MDB is registered once as ApplicationContext.mdb_import_snapshot.
Maintenance alignment and comparison use it without replacing the PDM snapshot.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.mdb_classification_service import MdbClassificationService
from ui.dialogs.progress_dialog import ProgressDialog
from ui.workers.background_task import ReportedTask
from core.cancellation import checkpoint


class _RepositoryClassTypeDialog(QDialog):
    """Let the user classify imported MDB classes before repository activation."""

    TYPES = ("Attribute", "Option", "Misc", "Unclassified")

    def __init__(self, snapshot, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Classify Repository Classes")
        self.resize(720, 560)
        self._snapshot = snapshot

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Classify the imported MDB classes so Class Creation can distinguish "
            "Attribute, Option and Misc classes. Names such as ATTR/ATTRIBUTE and "
            "OPT/OPTION are suggested automatically; review the suggestions before applying.",
            self,
        ))

        self._table = QTableWidget(self)
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["Class Name", "Class Type"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed
        )
        self._table.setColumnWidth(1, 190)
        self._table.verticalHeader().setDefaultSectionSize(40)

        classes = list(snapshot.engineering.classes if snapshot.engineering else [])
        self._table.setRowCount(len(classes))
        existing = getattr(snapshot, "mdb_class_types", {}) or {}
        for row, cls in enumerate(classes):
            name_item = QTableWidgetItem(cls.name)
            name_item.setData(Qt.ItemDataRole.UserRole, str(cls.id))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, name_item)

            combo = QComboBox(self._table)
            combo.addItems(self.TYPES)
            # The global QComboBox stylesheet uses vertical padding that can
            # clip text when the combo is embedded in a table cell. Give the
            # editor enough height and width for the complete class type.
            combo.setMinimumHeight(30)
            combo.setMinimumWidth(170)
            combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToContents
            )
            current = existing.get(str(cls.id))
            suggested = current if current in self.TYPES else MdbClassificationService.suggest(cls.name)
            combo.setCurrentText(suggested)
            combo.setToolTip(
                f"Suggested from class name: {suggested}. Review and change if needed."
            )
            self._table.setCellWidget(row, 1, combo)

        layout.addWidget(self._table, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Apply Classification")
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply(self) -> None:
        mapping: dict[str, str] = {}
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, 0)
            combo = self._table.cellWidget(row, 1)
            if name_item is None or combo is None:
                continue
            class_id = str(name_item.data(Qt.ItemDataRole.UserRole) or "")
            if class_id:
                mapping[class_id] = combo.currentText()
        self._snapshot.mdb_class_types = mapping
        self.accept()


class RepositoryWorkspace(QWidget):
    """Reusable repository browser and snapshot loader."""

    repository_loaded = Signal(object)  # (snapshot)
    repository_cleared = Signal()

    def __init__(self, context, parent=None) -> None:
        super().__init__(parent)
        self._context = context
        self._pool = QThreadPool.globalInstance()
        self._repository_path_value = ""
        self._repository_load_token = 0
        self._build_ui()

    @property
    def repository_path(self) -> str:
        return self._repository_path_value

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        repository_section = QGroupBox("Repository Workspace", self)
        repository_layout = QVBoxLayout(repository_section)
        repository_layout.setContentsMargins(8, 6, 8, 8)
        repository_layout.setSpacing(6)

        self._repository_path = QLabel("Not connected", repository_section)
        self._repository_path.setObjectName("pageSubtitle")
        self._repository_path.setWordWrap(True)
        repository_layout.addWidget(self._repository_path)

        self._repository_status = QLabel(
            "Click Open Repository to select a series from Seating or Tables.",
            repository_section,
        )
        self._repository_status.setObjectName("pageSubtitle")
        self._repository_status.setWordWrap(True)
        repository_layout.addWidget(self._repository_status)

        buttons = QHBoxLayout()
        self._open_repository_btn = QPushButton("Open Repository...", repository_section)
        self._open_repository_btn.setToolTip(
            "Select a published series from the configured repository roots"
        )
        self._open_repository_btn.clicked.connect(self.open_repository)
        buttons.addWidget(self._open_repository_btn)

        self._clear_repository_btn = QPushButton("Clear", repository_section)
        self._clear_repository_btn.setEnabled(False)
        self._clear_repository_btn.clicked.connect(self.clear_repository)
        buttons.addWidget(self._clear_repository_btn)
        repository_layout.addLayout(buttons)
        layout.addWidget(repository_section)

        source_section = QGroupBox("Data Sources", self)
        source_layout = QVBoxLayout(source_section)
        source_layout.setContentsMargins(8, 6, 8, 8)
        source_layout.setSpacing(6)
        source_note = QLabel(
            "Repository provides the published engineered baseline. "
            "Workflows consume the shared repository snapshot.",
            source_section,
        )
        source_note.setObjectName("pageSubtitle")
        source_note.setWordWrap(True)
        source_layout.addWidget(source_note)
        layout.addWidget(source_section)
        layout.addStretch(1)

    def refresh(self) -> None:
        roots = getattr(self._context.config, "repository_browser_roots", {}) or {}
        available = sum(1 for root in roots.values() if Path(root).is_dir())
        self._repository_status.setText(
            f"{available} of {len(roots)} configured repository roots available. "
            "Click Open Repository to select a series."
        )

    def _repository_series_items(self) -> list[tuple[str, Path]]:
        roots = getattr(self._context.config, "repository_browser_roots", {}) or {}
        items: list[tuple[str, Path]] = []
        for source_name, root_text in roots.items():
            root = Path(root_text)
            if not root.is_dir():
                continue
            try:
                series_dirs = sorted(
                    (item for item in root.iterdir() if item.is_dir()),
                    key=lambda item: item.name.casefold(),
                )
            except OSError:
                continue
            items.extend((source_name, series) for series in series_dirs)
        return items

    def open_repository(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Open Repository")
        dialog.resize(620, 520)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select a series repository to open:", dialog))

        tree = QTreeWidget(dialog)
        tree.setHeaderLabel("Repository / Series")
        tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        roots = getattr(self._context.config, "repository_browser_roots", {}) or {}
        for source_name in roots:
            root_item = QTreeWidgetItem([source_name])
            tree.addTopLevelItem(root_item)
            for category, series in self._repository_series_items():
                if category != source_name:
                    continue
                item = QTreeWidgetItem([series.name])
                item.setData(0, Qt.ItemDataRole.UserRole, str(series))
                item.setToolTip(0, str(series))
                root_item.addChild(item)
            root_item.setExpanded(True)

        layout.addWidget(tree, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open
            | QDialogButtonBox.StandardButton.Cancel,
            dialog,
        )
        buttons.button(QDialogButtonBox.StandardButton.Open).setEnabled(False)
        layout.addWidget(buttons)

        def update_open_state() -> None:
            item = tree.currentItem()
            path = str(item.data(0, Qt.ItemDataRole.UserRole) or "") if item else ""
            buttons.button(QDialogButtonBox.StandardButton.Open).setEnabled(bool(path))

        tree.itemSelectionChanged.connect(update_open_state)

        def accept_selection() -> None:
            item = tree.currentItem()
            path = str(item.data(0, Qt.ItemDataRole.UserRole) or "") if item else ""
            if path:
                dialog.accept()

        buttons.accepted.connect(accept_selection)
        buttons.rejected.connect(dialog.reject)
        tree.itemDoubleClicked.connect(lambda _item, _column: accept_selection())

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        item = tree.currentItem()
        path = str(item.data(0, Qt.ItemDataRole.UserRole) or "") if item else ""
        if path:
            self._select_repository_path(path)

    def _select_repository_path(self, path: str) -> None:
        if getattr(self, "_repository_run", None) is not None and self._repository_run.active:
            self._repository_progress_dialog.show()
            return
        self._repository_load_token += 1
        token = self._repository_load_token
        try:
            inspection = self._context.maintenance_repository_link_service.inspect_repository(path)
        except Exception as error:
            QMessageBox.warning(self, "Repository", str(error))
            return

        self._repository_path_value = str(inspection["path"])
        self._repository_path.setText(self._repository_path_value)
        self._repository_status.setText(
            f"Loading: {inspection['name']}  |  "
            f"Code: {inspection['code'] or '-'}  |  "
            f"Version: {inspection['version'] or '-'}"
        )
        self._start_repository_extraction(self._repository_path_value, token)

    def _start_repository_extraction(self, path: str, token: int) -> None:
        # Keep the reporter independent of the widget lifetime. Repository extraction
        # runs in QThreadPool and may finish after the workspace is replaced.
        run = ReportedTask(self)
        self._repository_run = run
        reporter = run.reporter
        self._repository_extract_reporter = reporter
        # Use the same visible progress monitor as Product loading. The
        # repository worker already reports each extraction stage through the
        # shared ProgressReporter; without this binding those updates were
        # invisible even though the backend was progressing.
        progress_dialog = getattr(self, "_repository_progress_dialog", None)
        if progress_dialog is None:
            progress_dialog = ProgressDialog(self)
            self._repository_progress_dialog = progress_dialog
        # Bind before begin(): binding resets the popup, which would otherwise
        # wipe the title and subject that begin() has just published.
        progress_dialog.bind(reporter)
        reporter.begin(5, title="Open Repository", subject=Path(path).name)
        reporter.log("info", f"Opening repository {Path(path).name}")
        progress_dialog.show()
        progress_dialog.raise_()

        context = self._context

        def work(emit):
            reporter.advance("Inspecting repository package...")
            repository = context.maintenance_repository_link_service.inspect_repository(path)
            checkpoint()
            reporter.advance("Reading MDB structural tables...")
            data = context.mdb_reverse_engineering_service.read(repository["ocd_path"], include_prices=True)
            checkpoint()
            reporter.advance("Mapping MDB data to Workbench workflows...")
            snapshot = context.mdb_reverse_engineering_service.import_snapshot(data)
            checkpoint()
            reporter.advance("Initializing engineering workspace...")
            context.engineering_initialization_service.initialize(snapshot)
            checkpoint()
            return repository, data, snapshot, sum(data.table_counts.values())

        run.start(work, finished=lambda payload: self._on_repository_extraction_finished(token, payload),
                  failed=lambda message: self._on_repository_extraction_failed(token, message),
                  cancelled=self._on_repository_cancelled)

    def _on_repository_cancelled(self, message: str) -> None:
        self._repository_status.setText(f"{message} Previous repository snapshot retained.")

    def _on_repository_extraction_finished(self, token: int, payload) -> None:
        # Ignore a late worker result if the user selected another repository.
        if token != self._repository_load_token:
            return
        repository, _data, snapshot, total_rows = payload
        classification_dialog = _RepositoryClassTypeDialog(snapshot, self)
        if classification_dialog.exec() != QDialog.DialogCode.Accepted:
            self._repository_extract_reporter.finish(
                False, "Repository class classification cancelled."
            )
            self._repository_status.setText(
                "Repository loaded; class classification cancelled."
            )
            return

        self._context.register_maintenance_repository_info(repository)
        self._context.register_mdb_import_snapshot(snapshot)
        if self._context.snapshot_source == "pdm" and self._context.pdm_snapshot is not None:
            from services.maintenance_alignment_service import MaintenanceAlignmentService
            MaintenanceAlignmentService(self._context).prepare_pdm_scope(
                self._context.pdm_snapshot,
                snapshot,
            )
        self._repository_status.setText(
            f"Loaded {repository['name']} | {total_rows:,} MDB rows mapped into Workbench."
        )
        self._repository_path.setText(repository["path"])
        self._repository_extract_reporter.finish(
            True, f"{repository['name']} loaded into Workbench."
        )
        self._clear_repository_btn.setEnabled(True)
        self.repository_loaded.emit(snapshot)

    def _on_repository_extraction_failed(self, token: int, message: str) -> None:
        if token != self._repository_load_token:
            return
        self._repository_status.setText("Repository extraction failed.")
        self._repository_extract_reporter.finish(False, "Repository extraction failed.")
        QMessageBox.warning(self, "Open Repository", message)

    def clear_repository(self) -> None:
        run = getattr(self, "_repository_run", None)
        if run is not None and run.active:
            run.reporter.request_cancel()
        self._repository_load_token += 1
        self._repository_path_value = ""
        self._context.register_maintenance_repository_info(None)
        self._repository_path.setText("Not connected")
        self._repository_status.setText(
            "Click Open Repository to select a series from Seating or Tables."
        )
        self._clear_repository_btn.setEnabled(False)
        if self._context.snapshot_source == "pdm":
            from services.maintenance_alignment_service import MaintenanceAlignmentService
            MaintenanceAlignmentService(self._context).restore_pdm_scope()
        self._context.register_mdb_import_snapshot(None)
        self.repository_cleared.emit()
