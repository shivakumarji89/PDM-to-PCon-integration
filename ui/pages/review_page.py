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
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.pages.base_page import BasePage
from core.export_readiness import ERROR, scan_snapshot, summarise


class ReviewPage(BasePage):
    """Read-only engineering review before generation."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Review",
            description="Read-only engineering review before generation.",
            parent=parent,
            show_placeholder=False,
        )
        self._context = context
        self._last_review = None  # cached review() output; reused by is_ready()

        self.add_content(self._build_toolbar())
        self.add_content(self._build_source_comparison_group())
        self.add_content(self._build_summary_group())
        self.add_content(self._build_lists_row())
        self.add_content(self._build_readiness_group())
        self.add_content(self._build_export_readiness_group())
        self.add_content(self._build_recon_group())
        self.refresh()

    def _build_toolbar(self) -> QWidget:
        box = QGroupBox("Toolbar", self)
        layout = QHBoxLayout(box)
        self._refresh_btn = QPushButton("Refresh", box)
        self._refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(self._refresh_btn)
        layout.addStretch(1)
        return box

    def _build_source_comparison_group(self) -> QWidget:
        """Evidence-only comparison for an existing repository series.

        This deliberately displays source values and PDM search candidates
        without asserting that similarly named records are equivalent.
        """
        box = QGroupBox("Repository ↔ PDM Discovery", self)
        layout = QVBoxLayout(box)

        self._source_status = QLabel(
            "No repository series selected. Open a repository series from Product.",
            box,
        )
        self._source_status.setWordWrap(True)
        layout.addWidget(self._source_status)

        form = QFormLayout()
        self._source_rows = {}
        for key, label in (
            ("name", "Repository Name"),
            ("code", "Repository Code"),
            ("category", "Repository Category"),
            ("catalogue", "Repository Catalogue"),
        ):
            value = QLabel("-", box)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._source_rows[key] = value
            form.addRow(f"{label}:", value)
        layout.addLayout(form)

        candidates_label = QLabel(
            "PDM candidates (discovery only — not standardized mappings):", box
        )
        layout.addWidget(candidates_label)
        self._pdm_candidates = QListWidget(box)
        self._pdm_candidates.setMinimumHeight(110)
        layout.addWidget(self._pdm_candidates)
        return box

    def _build_summary_group(self) -> QWidget:
        box = QGroupBox("Engineering Summary (loaded / selected)", self)
        form = QFormLayout(box)
        self._rows = {}
        for label in ("Articles", "Properties", "Property Values", "Options", "Option Values"):
            value = QLabel("0 / 0", box)
            self._rows[label] = value
            form.addRow(f"{label}:", value)
        return box

    def _build_lists_row(self) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._build_list_box("Warnings"), 1)
        layout.addWidget(self._build_list_box("Duplicates"), 1)
        layout.addWidget(self._build_list_box("Missing Relationships"), 1)
        return row

    def _build_list_box(self, title: str) -> QWidget:
        box = QGroupBox(title, self)
        layout = QVBoxLayout(box)
        widget = QListWidget(box)
        layout.addWidget(widget)
        setattr(self, f"_list_{title.split()[0].lower()}", widget)
        return box

    def _build_readiness_group(self) -> QWidget:
        box = QGroupBox("Engineering Readiness", self)
        form = QFormLayout(box)
        self._readiness = QLabel("-", box)
        self._errors = QLabel("-", box)
        self._errors.setWordWrap(True)
        form.addRow("Status:", self._readiness)
        form.addRow("Errors:", self._errors)
        return box

    # -- export readiness (OCD/XOCD identifier + text checks) -------------
    def _build_export_readiness_group(self) -> QWidget:
        box = QGroupBox("Export Readiness (OCD / XOCD)", self)
        layout = QVBoxLayout(box)
        self._export_status = QLabel("-", box)
        layout.addWidget(self._export_status)
        self._export_list = QListWidget(box)
        self._export_list.setToolTip(
            "Disallowed characters or empty required fields in base articles, "
            "relation objects, code schemes and text - fix before export."
        )
        layout.addWidget(self._export_list)
        return box

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

    def _refresh_source_comparison(self) -> None:
        context = self._context.repository_context_service.active_context
        if context is None:
            self._source_status.setText(
                "No repository series selected. Open a repository series from Product."
            )
            for widget in self._source_rows.values():
                widget.setText("-")
            self._pdm_candidates.clear()
            self._pdm_candidates.addItem("None")
            return

        self._source_status.setText(
            f"Repository: {context.repository_path}\n"
            f"PDM discovery status: {context.pdm_match_status.replace('_', ' ')}"
        )
        for key, widget in self._source_rows.items():
            record = context.records.get(key)
            widget.setText(str(record.value if record and record.value not in (None, "") else "-"))

        self._pdm_candidates.clear()
        if context.candidate_products:
            for index, product in enumerate(context.candidate_products, start=1):
                self._pdm_candidates.addItem(
                    f"{index}. {product['name'] or '-'}"
                    f" | Code: {product['code'] or '-'}"
                    f" | Category: {product['category'] or '-'}"
                    f" | Catalogue: {product['catalogue'] or '-'}"
                )
        else:
            self._pdm_candidates.addItem("No PDM candidates found.")

    # -- refresh -----------------------------------------------------------
    def refresh(self) -> None:
        self._refresh_source_comparison()
        review = self._context.validation_service.review()
        self._last_review = review
        for label, widget in self._rows.items():
            total = review.counts.get(label, 0)
            selected = review.selected_counts.get(label, 0)
            widget.setText(f"{total} / {selected}")

        self._fill_list(self._list_warnings, review.warnings)
        self._fill_list(self._list_duplicates, review.duplicates)
        self._fill_list(self._list_missing, review.missing_relationships)

        self._readiness.setText("READY" if review.ready else "NOT READY")
        self._errors.setText("\n".join(review.errors) if review.errors else "None")

        # Export readiness: OCD/XOCD identifier + text problems (pre-export).
        findings = scan_snapshot(self._context.active_snapshot)
        errors, warns = summarise(findings)
        self._export_status.setText(
            "No export problems found." if not findings
            else f"{errors} error(s), {warns} warning(s)"
        )
        self._export_list.clear()
        if findings:
            for f in findings:
                tag = "ERROR" if f.severity == ERROR else "WARN"
                self._export_list.addItem(f"[{tag}] {f.field}: {f.message} ({f.entity_id})")
        else:
            self._export_list.addItem("None")

    @staticmethod
    def _fill_list(widget, items) -> None:
        widget.clear()
        if items:
            widget.addItems(items)
        else:
            widget.addItem("None")

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def is_ready(self) -> bool:
        # Reuse the last refresh() output; refresh() always runs before readiness
        # is polled, so this avoids a second full review() per readiness check.
        review = self._last_review
        if review is None:
            review = self._context.validation_service.review()
            self._last_review = review
        return review.ready
