"""Shared Repository Workspace.

Provides the single repository-browser/open/extract workflow used by modules
that consume published repository snapshots. Module-specific pages consume the
resulting ApplicationContext.repository_snapshot instead of implementing their
own repository loader.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, Signal
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

from core.progress import ProgressReporter
from ui.dialogs.progress_dialog import ProgressDialog


class _RepositoryExtractSignals(QObject):
    """Signals emitted by the background repository extraction worker."""

    finished = Signal(int, object)  # (load token, payload)
    failed = Signal(int, str)      # (load token, message)


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
            "Attribute, Option and Misc classes. No class names are hardcoded.",
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
            current = existing.get(str(cls.id), "Unclassified")
            combo.setCurrentText(current if current in self.TYPES else "Unclassified")
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


class _RepositoryExtractWorker(QRunnable):
    """Reads one selected repository MDB without blocking the UI."""

    def __init__(self, context, repository_path: str, reporter, signals, token: int) -> None:
        super().__init__()
        self._context = context
        self._repository_path = repository_path
        self._reporter = reporter
        self._signals = signals
        self._token = token

    def run(self) -> None:
        try:
            self._reporter.advance("Inspecting repository package...")
            repository = self._context.maintenance_repository_link_service.inspect_repository(
                self._repository_path
            )

            self._reporter.advance("Reading MDB structural tables...")
            data = self._context.mdb_reverse_engineering_service.read(
                repository["ocd_path"],
                include_prices=True,
            )

            self._reporter.advance("Mapping MDB data to Workbench workflows...")
            snapshot = self._context.mdb_reverse_engineering_service.import_snapshot(data)
            self._reporter.advance("Initializing engineering workspace...")
            self._context.engineering_initialization_service.initialize(snapshot)
            self._reporter.advance("Activating Articles, Class Creation, Text, Relations and Pricing...")
            total_rows = sum(data.table_counts.values())
            self._signals.finished.emit(
                self._token, (repository, data, snapshot, total_rows)
            )
        except RuntimeError as error:
            message = str(error)
            try:
                self._signals.failed.emit(self._token, message)
            except RuntimeError:
                # The widget may have been destroyed while the worker was
                # finishing. There is nothing left to update on the UI.
                pass
        except Exception as error:
            try:
                self._signals.failed.emit(self._token, str(error))
            except RuntimeError:
                pass




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
        # Invalidate the previous repository immediately. Otherwise downstream
        # workflows can display the old snapshot while the new repository is
        # still being extracted in the background.
        self._repository_load_token += 1
        token = self._repository_load_token
        self._context.register_repository_snapshot(None)
        self._context.register_maintenance_repository_info(None)
        self.repository_cleared.emit()
        try:
            inspection = self._context.maintenance_repository_link_service.inspect_repository(path)
        except Exception as error:
            QMessageBox.warning(self, "Repository", str(error))
            return

        self._repository_path_value = str(inspection["path"])
        self._context.register_maintenance_repository_info(inspection)
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
        reporter = ProgressReporter()
        self._repository_extract_reporter = reporter
        self._repository_extract_signals = _RepositoryExtractSignals()
        self._repository_extract_signals.finished.connect(
            self._on_repository_extraction_finished
        )
        self._repository_extract_signals.failed.connect(
            self._on_repository_extraction_failed
        )
        reporter.begin(5, title="Open Repository", subject=Path(path).name)
        reporter.log("info", f"Opening repository {Path(path).name}")

        # Use the same visible progress monitor as Product loading. The
        # repository worker already reports each extraction stage through the
        # shared ProgressReporter; without this binding those updates were
        # invisible even though the backend was progressing.
        progress_dialog = getattr(self, "_repository_progress_dialog", None)
        if progress_dialog is None:
            progress_dialog = ProgressDialog(self)
            self._repository_progress_dialog = progress_dialog
        progress_dialog.bind(reporter)
        progress_dialog.show()
        progress_dialog.raise_()

        worker = _RepositoryExtractWorker(
            self._context, path, reporter, self._repository_extract_signals, token
        )
        self._pool.start(worker)

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

        self._context.register_repository_snapshot(snapshot)
        self._context.activate_snapshot_source("repository")
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
        self._repository_load_token += 1
        self._repository_path_value = ""
        self._context.register_maintenance_repository_info(None)
        self._repository_path.setText("Not connected")
        self._repository_status.setText(
            "Click Open Repository to select a series from Seating or Tables."
        )
        self._clear_repository_btn.setEnabled(False)
        self._context.register_repository_snapshot(None)
        if self._context.snapshot_source == "repository":
            self._context.activate_snapshot_source("repository")
        self.repository_cleared.emit()
