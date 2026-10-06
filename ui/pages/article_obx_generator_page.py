"""Article OBX Generator workspace.

The first stage is an inspectable permutation builder. Pricing and OBX
generation remain a later action after the generated article numbers are
reviewed.
"""
from __future__ import annotations

from PySide6.QtCore import QDate, QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QSizePolicy,
)

from core.progress import ProgressReporter
from ui.components import SectionHeader
from ui.dialogs.progress_dialog import ProgressDialog
from ui.components._styles import secondary_button_qss
from ui.pages.base_page import BasePage


class _PermutationBuildSignals(QObject):
    """Signals emitted by the background permutation-build worker."""

    finished = Signal(object)
    failed = Signal(str)


class _PermutationBuildWorker(QRunnable):
    """Build permutations away from the UI thread."""

    def __init__(self, service, snapshot, reporter, signals) -> None:
        super().__init__()
        self._service = service
        self._snapshot = snapshot
        self._reporter = reporter
        self._signals = signals

    def run(self) -> None:
        try:
            result = self._service.build(self._snapshot, reporter=self._reporter)
        except Exception as error:  # defensive: never crash the worker thread
            self._signals.failed.emit(f"Unexpected error: {error}")
        else:
            self._signals.finished.emit(result)


class ArticleObxGeneratorPage(BasePage):
    """Inspect repository-generated article permutations."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Article OBX Generator",
            description=(
                "Generate and review valid article permutations from repository "
                "configuration data. Pricing and OBX generation follow after review."
            ),
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._permutations = []
        self._thread_pool = QThreadPool(self)
        self._build_signals = None
        self._build_reporter = None
        self._build_dialog = None
        self._currency = QComboBox(self)
        self._date = QDateEdit(self)
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        self._date.setDate(QDate.currentDate())

        self._status = QLabel("No repository snapshot loaded.", self)
        self._status.setWordWrap(True)

        self._build_button = QPushButton("Build Permutations", self)
        self._build_button.setStyleSheet(
            secondary_button_qss("articleObxBuildButton")
        )
        self._build_button.clicked.connect(self._build_permutations)

        self._build_content()
        self.refresh()

    def _build_content(self) -> None:
        source = QGroupBox("Repository Source", self)
        source_layout = QVBoxLayout(source)
        source_layout.addWidget(SectionHeader(
            "Repository Snapshot",
            "Only the repository snapshot is used. Existing materialized articles are not the permutation output."
        ))
        source_layout.addWidget(self._status)

        permutation_box = QGroupBox("Generated Article Permutations", self)
        permutation_layout = QVBoxLayout(permutation_box)

        self._table = QTableWidget(self)
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "#",
            "Base Article",
            "Generated Article",
            "Variant Code",
            "Configuration",
            "Status",
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self._table.setMinimumHeight(240)
        self._table.setMaximumHeight(380)
        self._table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        permutation_layout.addWidget(self._table)

        parameters = QGroupBox("OBX Parameters", self)
        parameter_layout = QHBoxLayout(parameters)
        parameter_layout.addWidget(QLabel("Currency:"))
        parameter_layout.addWidget(self._currency)
        parameter_layout.addSpacing(24)
        parameter_layout.addWidget(QLabel("Effective date:"))
        parameter_layout.addWidget(self._date)
        parameter_layout.addStretch(1)

        actions = QHBoxLayout()
        actions.addWidget(self._build_button)
        actions.addStretch(1)

        self.add_content(source)
        # Only the table area is allowed to expand (stretch=1); the OBX
        # parameters and the Build Permutations action stay stretch=0, so a
        # large result set can never push them out of the visible workspace.
        self._normalize_group_boxes(permutation_box)
        self._content.addWidget(permutation_box, 1)
        self.add_content(parameters)
        self._content.addLayout(actions)

    @staticmethod
    def _values_text(values) -> str:
        if not values:
            return "—"
        return ", ".join(
            f"{value.name}: {value.value}"
            + (f" [{value.code}]" if value.code else "")
            for value in values
        )

    def _build_permutations(self) -> None:
        snapshot = self._context.mdb_import_snapshot
        self._table.setRowCount(0)
        self._permutations = []

        if snapshot is None:
            self._status.setText(
                "No repository snapshot is loaded. Load/select the published "
                "repository through the existing repository workflow first."
            )
            return

        self._build_button.setEnabled(False)
        reporter = ProgressReporter(self)
        dialog = self._context_window_progress_monitor()
        dialog.bind(reporter)
        self._build_reporter = reporter
        self._build_dialog = dialog

        signals = _PermutationBuildSignals()
        signals.finished.connect(self._on_permutations_finished)
        signals.failed.connect(self._on_permutations_failed)
        self._build_signals = signals

        reporter.begin(
            max(1, len(snapshot.articles)),
            title="Building Article Permutations",
            subject=snapshot.product.code or snapshot.product.name,
        )
        reporter.note("Preparing repository configuration dimensions")

        worker = _PermutationBuildWorker(
            self._context.article_permutation_service,
            snapshot,
            reporter,
            signals,
        )
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._thread_pool.start(worker)

    def _context_window_progress_monitor(self) -> ProgressDialog:
        main = self.window()
        if hasattr(main, "progress_monitor"):
            return main.progress_monitor()
        dialog = getattr(self, "_progress_dialog", None)
        if dialog is None:
            dialog = ProgressDialog(self)
            self._progress_dialog = dialog
        return dialog

    def _on_permutations_finished(self, permutations) -> None:
        reporter = self._build_reporter
        self._permutations = list(permutations or [])
        self._populate_permutation_table()
        snapshot = self._context.mdb_import_snapshot
        if snapshot is not None:
            self._status.setText(
                f"Repository snapshot loaded: "
                f"{snapshot.product.code or snapshot.product.name} "
                f"| Repository articles: {len(snapshot.articles)} "
                f"| Generated permutations: {len(self._permutations)} "
                f"| Properties: {len(snapshot.properties)} "
                f"| Options: {len(snapshot.options)} "
                f"| Prices: {len(snapshot.price_records)}"
            )
        if reporter is not None:
            reporter.finish(True, f"Generated {len(self._permutations)} permutation(s)")
        self._build_button.setEnabled(True)
        self._build_reporter = None
        self._build_signals = None

    def _on_permutations_failed(self, message: str) -> None:
        reporter = self._build_reporter
        if reporter is not None:
            reporter.finish(False, message)
        self._status.setText(f"Permutation build failed: {message}")
        self._build_button.setEnabled(True)
        self._build_reporter = None
        self._build_signals = None
        QMessageBox.critical(
            self, "Build Permutations", f"Permutation build failed:\n\n{message}"
        )

    def _populate_permutation_table(self) -> None:
        self._table.setRowCount(len(self._permutations))
        for row, permutation in enumerate(self._permutations, start=1):
            configuration = "; ".join(
                f"{value.name}={value.value}"
                for value in (*permutation.properties, *permutation.options)
            ) or "—"
            values = [
                str(row),
                permutation.base_code,
                permutation.final_article,
                permutation.variant_code or "—",
                configuration,
                "Valid",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self._table.setItem(row - 1, column, item)

    def refresh(self) -> None:
        snapshot = self._context.mdb_import_snapshot
        self._currency.clear()

        if snapshot is None:
            self._status.setText(
                "No repository snapshot is loaded. Load/select the published repository "
                "through the existing repository workflow, then return here."
            )
            self._build_button.setEnabled(False)
            self._table.setRowCount(0)
            return

        currencies = sorted({
            str(price.currency or "").upper()
            for price in snapshot.price_records
            if str(price.currency or "").strip()
        })
        self._currency.addItems(currencies)
        self._build_button.setEnabled(bool(snapshot.articles))

    def is_ready(self) -> bool:
        return self._context.mdb_import_snapshot is not None
