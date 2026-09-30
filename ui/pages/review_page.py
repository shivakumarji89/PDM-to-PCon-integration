"""Review workspace page.

An engineering review of the active snapshot: aggregate counts,
validation warnings, errors, duplicates, missing relationships and overall
engineering readiness. Presents (never mutates) data from the snapshot.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.pages.base_page import BasePage
from services.xocd_export_service import XocdExportService
from ui.workers.background_task import BackgroundTask


class ReviewPage(BasePage):
    """Final development validation and generation preview before export."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Review",
            description="Final Development validation before export.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._last_review = None  # cached review() output; reused by is_ready()
        self._mdb_preview_rows = {}
        self._mdb_retained_rows = {}
        self._mdb_preview_result = None
        self._preview_task: BackgroundTask | None = None
        self._preview_signals = None
        self._preview_running = False
        self._preview_elapsed = 0
        self._technical_dialog: QDialog | None = None
        self._backend_tables = {}
        self._development_cards = {}
        self._mdb_cards = {}
        self._preview_elapsed_timer = QTimer(self)

        self.add_content(self._build_toolbar())
        self.add_content(self._build_generation_summary())
        self._preview_elapsed_timer.setInterval(1000)
        self._preview_elapsed_timer.timeout.connect(self._update_preview_progress)
        self.refresh()

    def _build_toolbar(self) -> QWidget:
        box = QGroupBox("Review Controls", self)
        layout = QHBoxLayout(box)
        self._refresh_btn = QPushButton("Refresh Review", box)
        # Explicit user refresh includes the potentially expensive MDB/XOCD
        # generation preview. Normal workspace finalization only refreshes the
        # lightweight validation state.
        self._refresh_btn.clicked.connect(lambda: self.refresh(include_preview=True))
        layout.addWidget(self._refresh_btn)
        self._mdb_preview_status = QLabel("MDB generation data not loaded.", box)
        self._mdb_preview_status.setWordWrap(True)
        layout.addWidget(self._mdb_preview_status, 1)
        self._mdb_preview_progress = QProgressBar(box)
        self._mdb_preview_progress.setRange(0, 0)
        self._mdb_preview_progress.setTextVisible(False)
        self._mdb_preview_progress.setFixedHeight(8)
        self._mdb_preview_progress.hide()
        layout.addWidget(self._mdb_preview_progress)
        return box

    def _build_generation_summary(self) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        info_box = QGroupBox("Generation Information", container)
        info_layout = QVBoxLayout(info_box)
        form = QFormLayout()
        self._generation_rows = {}
        for label in ("Template", "Program", "Series", "Manufacturer"):
            value = QLabel("-", info_box)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._generation_rows[label] = value
            form.addRow(f"{label}:", value)
        info_layout.addLayout(form)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self._edit_generation_btn = QPushButton("Edit generation info", info_box)
        self._edit_generation_btn.clicked.connect(self._edit_generation_info)
        actions.addWidget(self._edit_generation_btn)
        info_layout.addLayout(actions)
        layout.addWidget(info_box)

        development_box = QGroupBox("Development Summary", container)
        development_grid = QGridLayout(development_box)
        development_grid.setContentsMargins(8, 8, 8, 8)
        development_grid.setSpacing(8)
        development_metrics = (
            "Articles", "Classes", "Properties", "Property Values",
            "Options", "Option Values", "Permutations", "Texts",
            "Relations", "Pricing",
        )
        for index, label in enumerate(development_metrics):
            card = self._metric_card(label, development_box)
            self._development_cards[label] = card
            development_grid.addWidget(card, index // 5, index % 5)
        layout.addWidget(development_box)

        mdb_box = QGroupBox("MDB Generation Preview", container)
        mdb_layout = QVBoxLayout(mdb_box)
        mdb_grid = QGridLayout()
        mdb_grid.setSpacing(8)
        mdb_metrics = (
            "Articles to generate", "Classes to generate",
            "Properties to generate", "Property Values to generate",
            "MDB tables", "MDB rows",
        )
        for index, label in enumerate(mdb_metrics):
            card = self._metric_card(label, mdb_box)
            self._mdb_cards[label] = card
            mdb_grid.addWidget(card, index // 3, index % 3)
        mdb_layout.addLayout(mdb_grid)

        technical_actions = QHBoxLayout()
        technical_actions.addStretch(1)
        self._technical_details_btn = QPushButton("View technical details", mdb_box)
        self._technical_details_btn.clicked.connect(self._show_technical_details)
        technical_actions.addWidget(self._technical_details_btn)
        mdb_layout.addLayout(technical_actions)
        layout.addWidget(mdb_box)

        return container

    @staticmethod
    def _metric_card(title: str, parent: QWidget) -> QFrame:
        card = QFrame(parent)
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setFrameShadow(QFrame.Shadow.Raised)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        caption = QLabel(title, card)
        caption.setWordWrap(True)
        value = QLabel("-", card)
        value.setObjectName("reviewMetricValue")
        value.setStyleSheet("font-size: 18px; font-weight: 600;")
        value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(caption)
        layout.addWidget(value)
        card._value_label = value
        return card

    @staticmethod
    def _set_metric(card: QFrame, value: object) -> None:
        label = getattr(card, "_value_label", None)
        if label is not None:
            label.setText("-" if value is None else str(value))

    def _build_backend_review(self) -> QWidget:
        box = QGroupBox("Technical Details", self)
        layout = QHBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 4)
        note = QLabel(
            "MDB tables, retained template rows and generated backend mappings "
            "are available on demand.",
            box,
        )
        note.setWordWrap(True)
        layout.addWidget(note, 1)
        button = QPushButton("View technical details", box)
        button.clicked.connect(self._show_technical_details)
        layout.addWidget(button)
        return box

    def _show_technical_details(self) -> None:
        dialog = self._ensure_technical_dialog()
        self._populate_backend_tables()
        dialog.resize(1100, 700)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _ensure_technical_dialog(self) -> QDialog:
        if self._technical_dialog is not None:
            return self._technical_dialog

        dialog = QDialog(self)
        dialog.setWindowTitle("Review — Technical Details")
        dialog.setMinimumSize(900, 600)
        layout = QVBoxLayout(dialog)
        self._backend_tabs = QTabWidget(dialog)
        layout.addWidget(self._backend_tabs, 1)

        self._backend_tables = {}
        tab_specs = [
            ("Package / Manufacturer", (
                "tCOMd_ComGroup", "tCOMd_Package", "tCOMd_Manufacturer",
                "tCOMd_DistributionRegion", "tCOMd_OfmlType",
                "tCOMd_PriceList2", "tCOMd_DistributionRegionPriceList",
                "Generation CAD Base-Length Registry",
            )),
            ("Export Mapping", (
                "tCOMd_Article", "tCOMd_ArticleClass",
                "tCOMd_Class", "tCOMd_Property", "tCOMd_PropValue",
            )),
            ("Relations", (
                "tCOMd_RelObj", "tCOMd_Relation", "tCOMd_RelObjRel",
            )),
            ("Code Schemes", ("tCOMd_CodeScheme",)),
            ("Article Restrictions", ("tCOMd_ArtBase",)),
            ("Generated Text", ("tCOMd_Text",)),
            ("Value Tables", (
                "tCOMd_Table", "tCOMd_TableColumn", "tCOMd_TableLine",
            )),
            ("Export Pricing", ("tCOMd_Price", "tCOMd_GlobalPrice")),
        ]

        for tab_name, tables in tab_specs:
            tab = QWidget(self._backend_tabs)
            tab_layout = QVBoxLayout(tab)
            tab_layout.setContentsMargins(0, 0, 0, 0)
            selector = QComboBox(tab)
            selector.addItems(tables)
            table = QTableWidget(tab)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.setAlternatingRowColors(True)
            table.setSortingEnabled(False)
            selector.currentTextChanged.connect(
                lambda name, t=table: self._show_backend_table(name, t)
            )
            tab_layout.addWidget(selector)
            tab_layout.addWidget(table, 1)
            self._backend_tables[tab_name] = (selector, table)
            self._backend_tabs.addTab(tab, tab_name)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=dialog)
        buttons.rejected.connect(dialog.hide)
        layout.addWidget(buttons)
        self._technical_dialog = dialog
        return dialog

    def _populate_backend_tables(self) -> None:
        if not self._backend_tables:
            return
        for tab_name, (selector, table) in self._backend_tables.items():
            if tab_name == "Package / Manufacturer":
                names = list(self._mdb_retained_rows)
                selector.blockSignals(True)
                selector.clear()
                selector.addItems(names)
                selector.blockSignals(False)
            self._show_backend_table(selector.currentText(), table)

    def _show_backend_table(self, table_name: str, widget: QTableWidget) -> None:
        rows = self._review_rows_for_table(table_name)
        columns: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    columns.append(key)

        widget.clear()
        widget.setColumnCount(len(columns))
        widget.setRowCount(len(rows))
        widget.setHorizontalHeaderLabels(columns)

        for row_index, row in enumerate(rows):
            for column_index, key in enumerate(columns):
                value = row.get(key)
                widget.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem("" if value is None else str(value)),
                )

        widget.resizeColumnsToContents()
        widget.resizeRowsToContents()

    def _review_rows_for_table(self, table_name: str) -> list[dict]:
        """Return final MDB details, excluding source text already reviewed in Text.

        Everything else is intentionally complete: prototype/retained metadata
        and every generated column are kept visible so Review can be used as the
        final backend/export inspection point.
        """
        if table_name in self._mdb_retained_rows:
            return list(self._mdb_retained_rows.get(table_name, []))
        rows = list(self._mdb_preview_rows.get(table_name, []))
        if table_name == "tCOMd_Text":
            return [
                r for r in rows
                if str(r.get("com_TextTypeCode") or "").lower() == "price"
            ]
        return rows

    def _refresh_mdb_preview(self) -> None:
        """Refresh MDB/XOCD generation data without blocking the Qt event loop."""
        snapshot = self._context.active_snapshot
        if snapshot is None:
            self._mdb_preview_rows = {}
            self._mdb_retained_rows = {}
            self._mdb_preview_result = None
            self._mdb_preview_status.setText("Load a product first.")
            self._clear_generation_summary()
            return
        if self._preview_running:
            return

        self._preview_running = True
        self._preview_elapsed = 0

        # Generation information is derived from the active snapshot and does
        # not require the expensive MDB preview. Show it immediately instead of
        # leaving the Review header blank while Access/MDB work is running.
        product = snapshot.product
        derived_template = snapshot.generation_template or (
            self._context.ocd_export_service._infer_template(product)
        )
        derived_program = snapshot.generation_program or (
            self._safe_xocd_value("program_key", product) or ""
        )
        derived_series = snapshot.generation_series or (
            self._safe_xocd_value("series_id", product) or ""
        )
        self._generation_rows["Template"].setText(str(derived_template or "-"))
        self._generation_rows["Program"].setText(str(derived_program or "-"))
        self._generation_rows["Series"].setText(str(derived_series or "-"))
        self._generation_rows["Manufacturer"].setText(
            "Loading from template..."
        )
        self._set_metric(self._development_cards["Permutations"], "Calculating...")
        self._set_metric(self._mdb_cards["Articles to generate"], "Calculating...")
        self._set_metric(self._mdb_cards["Classes to generate"], "Calculating...")
        self._set_metric(self._mdb_cards["Properties to generate"], "Calculating...")
        self._set_metric(self._mdb_cards["Property Values to generate"], "Calculating...")
        self._set_metric(self._mdb_cards["MDB tables"], "Calculating...")
        self._set_metric(self._mdb_cards["MDB rows"], "Calculating...")

        self._refresh_btn.setEnabled(False)
        self._mdb_preview_progress.show()
        self._preview_elapsed_timer.start()
        self._update_preview_progress()

        def build(_emit):
            result = self._context.ocd_export_service.preview(snapshot)
            if not result.error:
                try:
                    permutations = self._context.article_permutation_service.build(snapshot)
                    result.permutation_count = len(permutations)
                except Exception as error:
                    result.logs.append(f"Permutation count unavailable: {error}")
                    result.permutation_count = None
            return result

        task = BackgroundTask(build)
        signals = task.signals
        signals.finished.connect(self._on_mdb_preview_finished)
        signals.failed.connect(self._on_mdb_preview_failed)
        self._preview_task = task
        self._preview_signals = signals
        QThreadPool.globalInstance().start(task)

    def _update_preview_progress(self) -> None:
        """Show live elapsed progress while the background MDB build is running.

        The exporter currently does not expose trustworthy percentage milestones,
        so the UI deliberately uses an indeterminate progress bar plus elapsed
        time instead of displaying a misleading percentage.
        """
        if not self._preview_running:
            return
        self._mdb_preview_status.setText(
            "Refreshing MDB/XOCD generation data… "
            f"{self._preview_elapsed}s elapsed. The UI remains responsive."
        )
        self._preview_elapsed += 1

    @Slot(object)
    def _on_mdb_preview_finished(self, result) -> None:
        self._mdb_preview_result = result
        self._mdb_preview_rows = result.preview_rows or {}
        self._mdb_retained_rows = result.retained_rows or {}

        if result.error:
            self._mdb_preview_status.setText(
                f"MDB generation data unavailable: {result.error}"
            )
            self._clear_generation_summary()
            return

        snapshot = self._context.active_snapshot
        product = snapshot.product if snapshot is not None else None
        program = self._safe_xocd_value("program_key", product) if product else None
        series = self._safe_xocd_value("series_id", product) if product else None

        self._generation_rows["Template"].setText(result.template or "-")
        self._generation_rows["Program"].setText(str(result.program_code or program or "-"))
        self._generation_rows["Series"].setText(str(result.series_id or series or "-"))
        self._generation_rows["Manufacturer"].setText(str(result.manufacturer_id or "-"))
        self._update_development_summary()
        self._mdb_preview_status.setText(
            f"Generated {sum(result.table_counts.values())} backend/export rows "
            f"across {len(result.table_counts)} MDB tables. Read-only; nothing written."
        )

        self._update_review_metrics(result)
        self._populate_backend_tables()

    def _update_development_summary(self) -> None:
        review = self._last_review
        counts = review.counts if review is not None else {}
        snapshot = self._context.active_snapshot
        self._set_metric(self._development_cards["Articles"], counts.get("Articles", 0))
        self._set_metric(self._development_cards["Properties"], counts.get("Properties", 0))
        self._set_metric(self._development_cards["Property Values"], counts.get("Property Values", 0))
        self._set_metric(self._development_cards["Options"], counts.get("Options", 0))
        self._set_metric(self._development_cards["Option Values"], counts.get("Option Values", 0))
        self._set_metric(
            self._development_cards["Classes"],
            len(getattr(getattr(snapshot, "engineering", None), "classes", []) or [])
            if snapshot is not None else 0,
        )
        self._set_metric(
            self._development_cards["Texts"],
            len(getattr(snapshot, "text_blocks", []) or [])
            if snapshot is not None else 0,
        )
        self._set_metric(
            self._development_cards["Relations"],
            len(getattr(snapshot, "relation_objects", []) or [])
            if snapshot is not None else 0,
        )
        self._set_metric(
            self._development_cards["Pricing"],
            len(getattr(snapshot, "price_records", []) or [])
            if snapshot is not None else 0,
        )
        permutation_count = (
            self._mdb_preview_result.permutation_count
            if self._mdb_preview_result is not None
            else None
        )
        self._set_metric(self._development_cards["Permutations"], permutation_count)

    def _update_review_metrics(self, result) -> None:
        rows = result.preview_rows or {}
        table_count = result.table_counts or {}
        self._set_metric(
            self._mdb_cards["Articles to generate"],
            len(rows.get("tCOMd_Article", [])),
        )
        self._set_metric(
            self._mdb_cards["Classes to generate"],
            len(rows.get("tCOMd_Class", [])),
        )
        self._set_metric(
            self._mdb_cards["Properties to generate"],
            len(rows.get("tCOMd_Property", [])),
        )
        self._set_metric(
            self._mdb_cards["Property Values to generate"],
            len(rows.get("tCOMd_PropValue", [])),
        )
        self._set_metric(self._mdb_cards["MDB tables"], len(table_count))
        self._set_metric(self._mdb_cards["MDB rows"], sum(table_count.values()))
        self._update_development_summary()

    def _edit_generation_info(self) -> None:
        snapshot = self._context.active_snapshot
        if snapshot is None or snapshot.product is None:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Generation Information")
        form = QFormLayout(dialog)
        template = QComboBox(dialog)
        template.addItems(("seating", "tables"))
        current_template = snapshot.generation_template or (
            self._mdb_preview_result.template if self._mdb_preview_result else ""
        )
        if not current_template:
            current_template = self._context.ocd_export_service._infer_template(
                snapshot.product
            )
        template.setCurrentText(current_template)

        derived_program = self._safe_xocd_value("program_key", snapshot.product) or ""
        derived_series = self._safe_xocd_value("series_id", snapshot.product) or ""
        program = QLineEdit(snapshot.generation_program or derived_program, dialog)
        series = QLineEdit(snapshot.generation_series or derived_series, dialog)
        manufacturer = QLabel(
            self._generation_rows["Manufacturer"].text() or "-", dialog
        )
        manufacturer.setToolTip(
            "Manufacturer is retained from the selected MDB template and is not "
            "a Review generation override."
        )

        form.addRow("Template:", template)
        form.addRow("Program:", program)
        form.addRow("Series:", series)
        form.addRow("Manufacturer:", manufacturer)
        note = QLabel(
            "Program and Series are a coupled generation override. "
            "Changing them affects generation only; the PDM Product remains unchanged.",
            dialog,
        )
        note.setWordWrap(True)
        form.addRow(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        form.addRow(buttons)

        def save() -> None:
            program_value = program.text().strip()
            series_value = series.text().strip()
            if not program_value or not series_value:
                return
            snapshot.generation_template = template.currentText().strip().lower()
            snapshot.generation_program = program_value
            snapshot.generation_series = series_value
            self.refresh(include_preview=True)
            dialog.accept()

        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    @Slot(str)
    def _on_mdb_preview_failed(self, error: str) -> None:
        self._mdb_preview_rows = {}
        self._mdb_retained_rows = {}
        self._mdb_preview_result = None
        self._mdb_preview_status.setText(f"MDB generation data failed: {error}")
        self._clear_generation_summary()

    @Slot()
    def _on_mdb_preview_thread_finished(self) -> None:
        self._preview_running = False
        self._preview_elapsed_timer.stop()
        self._mdb_preview_progress.hide()
        self._preview_thread = None
        self._preview_worker = None
        self._refresh_btn.setEnabled(True)

    @staticmethod
    def _safe_xocd_value(method_name: str, product):
        try:
            method = getattr(XocdExportService, method_name)
            return method(product)
        except Exception:
            return None

    def _clear_generation_summary(self) -> None:
        for widget in self._generation_rows.values():
            widget.setText("-")
        for cards in (self._development_cards, self._mdb_cards):
            for card in cards.values():
                self._set_metric(card, "-")
        self._mdb_retained_rows = {}
        for selector, table in self._backend_tables.values():
            table.clear()
            table.setRowCount(0)
            table.setColumnCount(0)

    # -- MDB -> XOCD reconciliation (the Asker) ---------------------------
    def _build_recon_group(self) -> QWidget:
        box = QGroupBox("MDB \u2192 XOCD Reconciliation", self)
        layout = QVBoxLayout(box)
        bar = QHBoxLayout()
        self._recon_btn = QPushButton("Check MDB for changes\u2026", box)
        self._recon_btn.setToolTip(
            "Diff an imported MDB against its exported XOCD package and choose "
            "which edits to fold back (XOCD stays the source of truth)."
        )
        self._recon_btn.clicked.connect(self._on_check_mdb)
        bar.addWidget(self._recon_btn)
        self._recon_status = QLabel("Not checked.", box)
        self._recon_status.setWordWrap(True)
        bar.addWidget(self._recon_status, 1)
        layout.addLayout(bar)
        return box

    def _on_check_mdb(self) -> None:
        from PySide6.QtWidgets import QFileDialog, QInputDialog

        xocd = QFileDialog.getExistingDirectory(
            self, "Select your XOCD package folder (source of truth)"
        )
        if not xocd:
            return
        repo = QFileDialog.getExistingDirectory(
            self, "Select the repository product db folder (ocd_*.csv - final output)"
        )
        if not repo:
            return
        svc = self._context.mdb_reconcile_service
        # The XOCD holds ALL products; scope to the one series this repo folder is
        # for, so other series are never flagged as removed.
        programs = svc.xocd_programs(xocd)
        program = svc._detect_program(xocd, repo) or (programs[0] if programs else None)
        if len(programs) > 1:
            idx = programs.index(program) if program in programs else 0
            chosen, ok = QInputDialog.getItem(
                self, "Select series",
                "Which product/series in the XOCD matches this repo folder?",
                programs, idx, False,
            )
            if not ok:
                return
            program = chosen
        try:
            report = svc.reconcile_repo(xocd, repo, program=program)
        except Exception as error:  # read failure
            self._recon_status.setText(f"Reconcile failed: {error}")
            self._recon_status.setStyleSheet(f"color: {theme.COLOR_WARNING};")
            return
        note = ("  " + " ".join(report.notes)) if report.notes else ""
        self._recon_status.setText(f"[{report.program or '?'}] {report.summary()}{note}")
        self._recon_status.setStyleSheet("")
        self._show_recon_dialog(xocd, report)

    def _show_recon_dialog(self, folder, report) -> None:
        from PySide6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
            QListWidgetItem,
            QMessageBox,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("MDB \u2192 XOCD Reconciliation")
        dialog.setMinimumSize(700, 460)
        layout = QVBoxLayout(dialog)
        header = QLabel(
            f"{report.summary()}. Repository vs XOCD - tick the changes to fold "
            "back into XOCD (double-click a row to open its XOCD file; blocked "
            "changes cannot be applied).", dialog,
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        listw = QListWidget(dialog)
        colours = {
            "safe": theme.COLOR_OK, "review": theme.COLOR_WARNING,
            "blocked": theme.COLOR_ERROR,
        }
        base_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        for change in report.changes:
            ref = f"  [{change.source_ref}]" if change.source_ref else ""
            entry = QListWidgetItem(
                f"[{change.verdict.upper()}] {change.kind} \u00b7 {change.summary}"
                f" \u2014 {change.reason}{ref}"
            )
            entry.setData(Qt.ItemDataRole.UserRole, change)
            entry.setForeground(QBrush(QColor(colours.get(change.verdict, theme.COLOR_WARNING))))
            if change.verdict == "blocked" or change.kind == "removed":
                entry.setFlags(base_flags)  # display only - not applicable
            else:
                entry.setFlags(base_flags | Qt.ItemFlag.ItemIsUserCheckable)
                entry.setCheckState(
                    Qt.CheckState.Checked if change.verdict == "safe"
                    else Qt.CheckState.Unchecked
                )
            listw.addItem(entry)
        if not report.changes:
            listw.addItem("No differences - the repository matches the XOCD package.")
        layout.addWidget(listw)

        def open_xocd(item) -> None:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            change = item.data(Qt.ItemDataRole.UserRole)
            if change is None or not change.source_ref:
                return
            name = change.source_ref.split(":")[0]
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(folder) / name)))

        listw.itemDoubleClicked.connect(open_xocd)

        buttons = QDialogButtonBox(dialog)
        apply_btn = buttons.addButton(
            "Apply selected", QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.addButton(QDialogButtonBox.StandardButton.Close)

        def on_apply() -> None:
            accepted = []
            for row in range(listw.count()):
                item = listw.item(row)
                change = item.data(Qt.ItemDataRole.UserRole)
                if change is None:
                    continue
                if (item.flags() & Qt.ItemFlag.ItemIsUserCheckable
                        and item.checkState() == Qt.CheckState.Checked):
                    accepted.append(change)
            total = self._context.mdb_reconcile_service.apply_repo_changes(
                folder, accepted
            )
            QMessageBox.information(
                dialog, "Reconciliation",
                f"Folded {total} change(s) back into the XOCD package.",
            )
            dialog.accept()

        apply_btn.clicked.connect(on_apply)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    # -- refresh -----------------------------------------------------------
    def refresh(self, include_preview: bool = False) -> None:
        review = self._context.validation_service.review()
        self._last_review = review
        self._update_development_summary()

        # MDB preview performs template discovery, Access reads and full export
        # row construction. It is deliberately not part of the synchronous
        # family-load finalization path; the user can request it explicitly
        # with Refresh Review.
        if include_preview:
            self._refresh_mdb_preview()

        if self._mdb_preview_result is not None and self._mdb_preview_result.error:
            # Keep the existing engineering readiness semantics; the generation
            # preview reports its own backend/export preparation failure.
            self._mdb_preview_status.setText(
                self._mdb_preview_status.text()
                + f" | Engineering validation: "
                + ("READY" if review.ready else "NOT READY")
            )

    def is_ready(self) -> bool:
        # Reuse the last refresh() output; refresh() always runs before readiness
        # is polled, so this avoids a second full review() per readiness check.
        review = self._last_review
        if review is None:
            review = self._context.validation_service.review()
            self._last_review = review
        return review.ready
