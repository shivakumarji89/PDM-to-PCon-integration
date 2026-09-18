"""Review workspace page.

A read-only engineering review of the active snapshot: aggregate counts,
validation warnings, errors, duplicates, missing relationships and overall
engineering readiness. Presents (never mutates) data from the snapshot.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.pages.base_page import BasePage
from services.xocd_export_service import XocdExportService


class ReviewPage(BasePage):
    """Read-only engineering review before generation."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Review",
            description="Read-only engineering review before generation.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._last_review = None  # cached review() output; reused by is_ready()

        self.add_content(self._build_toolbar())
        self.add_content(self._build_generation_summary())
        self.add_content(self._build_backend_review())

        self._last_review = None
        self._mdb_preview_rows = {}
        self._mdb_retained_rows = {}
        self._mdb_preview_result = None
        self.refresh()

    def _build_toolbar(self) -> QWidget:
        box = QGroupBox("Review Controls", self)
        layout = QHBoxLayout(box)
        self._refresh_btn = QPushButton("Refresh Review", box)
        self._refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(self._refresh_btn)
        self._mdb_preview_status = QLabel("MDB generation data not loaded.", box)
        self._mdb_preview_status.setWordWrap(True)
        layout.addWidget(self._mdb_preview_status, 1)
        return box

    def _build_generation_summary(self) -> QWidget:
        box = QGroupBox("Final Generation Summary", self)
        form = QFormLayout(box)
        self._generation_rows = {}
        for label in (
            "Template", "Program", "Series", "Manufacturer",
            "Package ID", "COM Group ID", "CAD Base-Length Overrides",
            "Generated MDB rows", "Generated MDB tables", "Retained template tables",
            "CAD Registry",
        ):
            value = QLabel("-", box)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._generation_rows[label] = value
            form.addRow(f"{label}:", value)
        return box

    def _build_backend_review(self) -> QWidget:
        box = QGroupBox(
            "Backend / Derived / Export Data (not repeated from the other workflows)",
            self,
        )
        layout = QVBoxLayout(box)

        self._backend_tabs = QTabWidget(box)
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

        return box

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
        snapshot = self._context.active_snapshot
        if snapshot is None:
            self._mdb_preview_rows = {}
            self._mdb_retained_rows = {}
            self._mdb_preview_result = None
            self._mdb_preview_status.setText("Load a product first.")
            self._clear_generation_summary()
            return

        try:
            result = self._context.ocd_export_service.preview(snapshot)
        except Exception as error:
            self._mdb_preview_rows = {}
            self._mdb_retained_rows = {}
            self._mdb_preview_result = None
            self._mdb_preview_status.setText(f"MDB generation data failed: {error}")
            self._clear_generation_summary()
            return

        self._mdb_preview_result = result
        self._mdb_preview_rows = result.preview_rows or {}
        self._mdb_retained_rows = result.retained_rows or {}

        if result.error:
            self._mdb_preview_status.setText(
                f"MDB generation data unavailable: {result.error}"
            )
            self._clear_generation_summary()
            return

        product = snapshot.product
        program = self._safe_xocd_value("program_key", product)
        series = self._safe_xocd_value("series_id", product)

        self._generation_rows["Template"].setText(result.template or "-")
        self._generation_rows["Program"].setText(str(result.program_code or program or "-"))
        self._generation_rows["Series"].setText(str(result.series_id or series or "-"))
        self._generation_rows["Manufacturer"].setText(
            str(result.manufacturer_id or "-")
        )
        self._generation_rows["Package ID"].setText(str(result.package_id if result.package_id is not None else "-"))
        self._generation_rows["COM Group ID"].setText(str(result.comgroup_id if result.comgroup_id is not None else "-"))
        self._generation_rows["CAD Base-Length Overrides"].setText(
            str(len(result.registry_overrides))
        )
        self._generation_rows["Generated MDB rows"].setText(
            str(sum(result.table_counts.values()))
        )
        self._generation_rows["Generated MDB tables"].setText(
            str(len(result.table_counts))
        )
        self._generation_rows["Retained template tables"].setText(
            str(len(result.retained_rows))
        )
        self._generation_rows["CAD Registry"].setText(
            result.registry_path or "-"
        )
        self._mdb_preview_status.setText(
            f"Generated {sum(result.table_counts.values())} backend/export rows "
            f"across {len(result.table_counts)} MDB tables. Read-only; nothing written."
        )

        package_selector, package_table = self._backend_tables["Package / Manufacturer"]
        package_selector.blockSignals(True)
        package_selector.clear()
        package_selector.addItems(list(result.retained_rows))
        package_selector.blockSignals(False)
        if package_selector.count():
            package_selector.setCurrentIndex(0)
            self._show_backend_table(package_selector.currentText(), package_table)

        for tab_name, (selector, table) in self._backend_tables.items():
            if tab_name == "Package / Manufacturer":
                continue
            name = selector.currentText()
            self._show_backend_table(name, table)

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
    def refresh(self) -> None:
        review = self._context.validation_service.review()
        self._last_review = review
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
