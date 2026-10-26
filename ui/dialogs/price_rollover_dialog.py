"""Price-list roll-over - the full tool in a pop-up.

Point it at a repository of published packages (XOCD folders or OCD MDBs),
optionally pick a subset of series, set the effective date and new-list token,
then Scan to preview and Apply to write each package's roll-over in place.
"""
from __future__ import annotations

from pathlib import Path

from core.cancellation import OperationCancelled, checkpoint
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.components import DialogTemplate
from ui.workers.background_task import ReportedTask

#: PDM SiteId for the UK region - the only region we operate.
_UK_SITE_ID = 1


class PriceRolloverDialog(DialogTemplate):
    """Annual/mid-year price-list roll-over across a repository."""

    def __init__(self, context, repository: str = "", parent=None) -> None:
        super().__init__(parent)
        self._context = context
        #: Chosen subset of packages to roll (None = every series in the repository).
        self._selected_packages: list[str] | None = None
        self.set_title("Price List Roll-over")
        self.setMinimumSize(720, 640)
        self.add_content(self._build_form(repository))
        self.add_content(self._build_summary())
        self._build_footer()

    # -- construction ---------------------------------------------------

    def _build_form(self, repository: str) -> QWidget:
        box = QGroupBox("Roll-over", self)
        form = QFormLayout(box)

        self._target = QComboBox(box)
        self._target.addItems(["XOCD packages (folders)", "OCD MDBs (files)"])
        form.addRow("Repository holds", self._target)

        repo_row = QHBoxLayout()
        self._repo = QLineEdit(box)
        self._repo.setText(repository)
        self._repo.setPlaceholderText(
            "Repository root(s) - every package below is rolled over; separate several with ';'")
        browse = QPushButton("Browse...", box)
        browse.clicked.connect(self._on_browse)
        repo_row.addWidget(self._repo, 1)
        repo_row.addWidget(browse)
        form.addRow("Repository", repo_row)

        self._effective = QDateEdit(box)
        self._effective.setDisplayFormat("dd-MMM-yyyy")
        self._effective.setCalendarPopup(True)
        self._effective.setDate(QDate.currentDate())
        self._effective.dateChanged.connect(self._sync_old_end)
        form.addRow("Effective date", self._effective)

        self._old_end = QLineEdit(box)
        self._old_end.setReadOnly(True)
        form.addRow("Current list end", self._old_end)
        self._sync_old_end()

        self._token = QLineEdit(box)
        self._token.setPlaceholderText("New list token, e.g. 2026 (annual) or 2026_2 (mid-year)")
        self._token.setToolTip(
            "Keyed once and applied to every list: EURO_2025 -> EURO_<token>, GBP_2025 -> GBP_<token>.")
        form.addRow("New list token", self._token)

        self._site = QLineEdit(box)
        self._site.setReadOnly(True)
        self._site.setText(self._context.config.catalogue_region or "UK")
        self._site.setToolTip("PDM Site region. Fixed to the UK region.")
        form.addRow("Site", self._site)

        self._compute = QCheckBox("Pull fresh prices from PDM (off = roll the list dates only)", box)
        self._compute.setChecked(True)
        form.addRow("", self._compute)

        self._scope = QLineEdit(box)
        self._scope.setReadOnly(True)
        self._scope.setText("All series in the repository")
        self._repo.textChanged.connect(self._reset_selection)
        self._target.currentIndexChanged.connect(self._reset_selection)
        form.addRow("Roll-over scope", self._scope)
        return box

    def _build_summary(self) -> QWidget:
        box = QGroupBox("Plan", self)
        layout = QVBoxLayout(box)
        self._summary = QPlainTextEdit(box)
        self._summary.setReadOnly(True)
        self._summary.setPlaceholderText(
            "Set the effective date and new list token, then Scan to preview every "
            "package's roll-over before Apply.")
        layout.addWidget(self._summary)
        return box

    def _build_footer(self) -> None:
        select_btn = QPushButton("Select Series...", self)
        select_btn.setToolTip("Choose which series the roll-over touches (default: all).")
        select_btn.clicked.connect(self._on_select_series)
        scan_btn = QPushButton("Scan", self)
        scan_btn.clicked.connect(lambda: self._run(apply=False))
        apply_btn = QPushButton("Apply", self)
        apply_btn.clicked.connect(self._on_apply)
        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        for btn in (select_btn, scan_btn, apply_btn, close_btn):
            self.add_footer_button(btn)

    # -- helpers --------------------------------------------------------

    def _is_mdb(self) -> bool:
        return self._target.currentIndex() == 1

    def _sync_old_end(self, *_) -> None:
        self._old_end.setText(
            self._context.price_list_service._day_before(self._effective_ymd()))

    def _effective_ymd(self) -> str:
        return self._effective.date().toString("yyyyMMdd")

    def _on_browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select a repository root")
        if not path:
            return
        parts = [p.strip() for p in self._repo.text().split(";") if p.strip()]
        if path not in parts:
            parts.append(path)
        self._repo.setText(";".join(parts))

    def _inputs_ok(self) -> str | None:
        if not self._repo.text().strip():
            return "Choose the repository root."
        if not self._token.text().strip():
            return "Enter the new list token (e.g. 2026)."
        return None

    def _reset_selection(self, *_) -> None:
        self._selected_packages = None
        self._scope.setText("All series in the repository")

    def _on_select_series(self) -> None:
        from ui.dialogs.series_select_dialog import SeriesSelectDialog

        repo = self._repo.text().strip()
        if not repo:
            QMessageBox.information(self, "Select Series", "Choose the repository root.")
            return
        packages = self._context.price_update_service._discover_packages(repo, self._is_mdb())
        if not packages:
            QMessageBox.information(self, "Select Series", "No series found under the repository.")
            return
        items = [((p.parent.name if self._is_mdb() else p.name), str(p)) for p in packages]
        dialog = SeriesSelectDialog(
            items, title="Select Series to Roll Over",
            preselected=self._selected_packages, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        chosen = dialog.selected_paths
        if not chosen or len(chosen) == len(items):
            self._selected_packages = None
            self._scope.setText("All series in the repository")
        else:
            self._selected_packages = chosen
            self._scope.setText(f"{len(chosen)} of {len(items)} series selected")

    def _lookup(self, special_map=None):
        if not self._compute.isChecked():
            return None
        return self._context.price_update_service.make_pdm_lookup(
            self._effective.date().toString("dd-MMM-yyyy"), _UK_SITE_ID,
            special_map=special_map)

    # -- actions --------------------------------------------------------

    def _on_apply(self) -> None:
        if getattr(self, "_run_task", None) is not None and self._run_task.active:
            return
        error = self._inputs_ok()
        if error:
            QMessageBox.information(self, "Price Update", error)
            return
        answer = QMessageBox.question(
            self, "Price Update",
            f"Roll over {self._scope.text().lower()} under:\n{self._repo.text().strip()}\n\n"
            f"New list token '{self._token.text().strip()}', effective "
            f"{self._effective_ymd()} (current list ends {self._old_end.text()}).\n\n"
            "Apply in place?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._run(apply=True)

    def _run(self, apply: bool) -> None:
        if getattr(self, "_run_task", None) is not None and self._run_task.active:
            return
        error = self._inputs_ok()
        if error:
            QMessageBox.information(self, "Price Update", error)
            return
        svc = self._context.price_update_service
        # Apply KNOWN special-case mappings inline; NEW ones are collected during
        # the roll and confirmed at the END, then updated in place (only those).
        special_map = svc.load_special_map() if self._compute.isChecked() else None

        run = self._run_task = ReportedTask(self)
        reporter = run.reporter
        monitor = self._progress_monitor()
        monitor.bind(reporter)
        monitor.show()
        monitor.raise_()
        repo, is_mdb = self._repo.text().strip(), self._is_mdb()
        effective, token = self._effective_ymd(), self._token.text().strip()
        lookup = self._lookup(special_map)
        selected = list(self._selected_packages) if self._selected_packages is not None else None

        def work(_emit):
            packages = selected
            if packages is None:
                packages = svc._discover_packages(repo, is_mdb)
            reporter.begin(max(len(packages), 1),
                           title="Apply Roll-over" if apply else "Scan Roll-over",
                           subject=Path(repo.split(";")[0].strip()).name)
            try:
                return svc.run_batch(
                    repo, is_mdb, effective, token, lookup, apply=apply, packages=packages,
                    progress=lambda done, total, text: reporter.advance(text),
                    stage=reporter.note, special_map=special_map)
            finally:
                if lookup is not None and hasattr(lookup, "close"):
                    lookup.close()

        run.start(work, finished=lambda result: self._on_result(result, apply),
                  failed=self._on_failed, cancelled=self._on_cancelled)

    def _on_cancelled(self, message: str) -> None:
        self._summary.setPlainText(message)

    def done(self, result: int) -> None:
        run = getattr(self, "_run_task", None)
        if run is not None and run.active:
            run.reporter.request_cancel()
        super().done(result)

    def _progress_monitor(self):
        monitor = getattr(self, "_monitor", None)
        if monitor is None:
            from ui.dialogs.progress_dialog import ProgressDialog
            monitor = ProgressDialog(self)
            self._monitor = monitor
        return monitor

    def _on_failed(self, message: str) -> None:
        QMessageBox.warning(self, "Price Update", f"Roll-over failed:\n{message}")

    def _on_result(self, result, apply: bool) -> None:
        self._summary.setPlainText(self._render(result, apply))
        if result.error:
            QMessageBox.warning(self, "Price Update", result.error)
            return
        if apply and self._handle_special_articles(result):
            return  # specials confirmed + updated, with their own message
        elif apply:
            QMessageBox.information(
                self, "Price Update",
                f"Rolled over {len(result.packages)} package(s). "
                "Commit the repository to publish.")

    def _handle_special_articles(self, result) -> bool:
        """After the bulk roll, confirm any special-case (underscore) articles it
        had to carry, then re-price ONLY those items in place. Returns True when
        the special flow ran (so the caller skips the generic completion note)."""
        if not self._compute.isChecked():
            return False
        svc = self._context.price_update_service
        carried = {p.package: p.special_carried for p in result.packages if p.special_carried}
        if not carried:
            return False
        mydate = self._effective.date().toString("dd-MMM-yyyy")

        def work(reporter):
            reporter.begin(max(len(carried), 1), title="Check Special Articles", subject="")
            return svc.scan_special_articles(list(carried), mydate, _UK_SITE_ID)

        self._start_special(
            work, lambda records: self._on_special_scanned(records, result, carried, mydate),
            len(result.packages))
        return True

    def _start_special(self, work, finished, rolled: int) -> None:
        run = self._run_task = ReportedTask(self)
        reporter = run.reporter
        monitor = self._progress_monitor()
        monitor.bind(reporter)
        monitor.show()
        monitor.raise_()

        def execute(_emit):
            try:
                return work(reporter)
            except OperationCancelled as exc:
                raise OperationCancelled(
                    f"{rolled} package(s) already rolled over. Special-article step: {exc}") from exc

        run.start(execute, finished=finished, failed=self._on_failed,
                  cancelled=self._on_cancelled)

    def _on_special_scanned(self, records, result, carried, mydate) -> None:
        if not records:
            QMessageBox.information(
                self, "Price Update", f"Rolled over {len(result.packages)} package(s). "
                "Commit the repository to publish.")
            return
        from ui.dialogs.special_article_dialog import SpecialArticleDialog
        dialog = SpecialArticleDialog(records, self)
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.mapping:
            return
        svc, mapping = self._context.price_update_service, dict(dialog.mapping)

        def work(reporter):
            reporter.begin(max(len(carried), 1), title="Update Special Articles", subject="")
            svc.save_special_map(mapping)
            updated, completed = 0, 0
            errors = []
            try:
                for pkg_path, codes in carried.items():
                    checkpoint()
                    pkg_map = {c: mapping[c] for c in codes if c in mapping}
                    if pkg_map:
                        count, err = svc.apply_special_articles(
                            pkg_path, pkg_map, mydate, _UK_SITE_ID, stage=reporter.note)
                        updated += count
                        if err:
                            errors.append(f"{Path(pkg_path).parent.name}: {err}")
                    completed += 1
                    reporter.advance(Path(pkg_path).parent.name)
                checkpoint()
            except OperationCancelled as exc:
                raise OperationCancelled(
                    f"Cancelled after {completed} special-article package(s) completed; "
                    f"{updated} price row(s) committed.") from exc
            return updated, errors

        def finished(outcome):
            updated, errors = outcome
            message = (f"Rolled over {len(result.packages)} package(s).\n"
                       f"Updated {updated} special-case price row(s) in place. "
                       "Commit the repository to publish.")
            if errors:
                message += "\n\nErrors:\n" + "\n".join(errors)
            QMessageBox.information(self, "Price Update", message)

        self._start_special(work, finished, len(result.packages))

    @staticmethod
    def _render(result, applied: bool) -> str:
        head = "Applied" if applied else "Scanned"
        lines = [f"{head}: {result.repository}", f"{len(result.packages)} package(s)"]
        if result.error:
            lines.append(f"ERROR: {result.error}")
        for pkg in result.packages:
            name = Path(pkg.package).name
            if pkg.error:
                lines.append(f"  {name}: ERROR {pkg.error}")
                continue
            if not pkg.lists:
                lines.append(f"  {name}: no open price list found")
            for lr in pkg.lists:
                if lr.status == "done" and lr.old_list == lr.new_list:
                    lines.append(f"  {name} [{lr.currency}] {lr.old_list}: done (already current)")
                else:
                    lines.append(
                        f"  {name} [{lr.currency}] {lr.old_list} -> {lr.new_list} "
                        f"[{lr.status}]: {lr.rows} rows, {lr.changed} changed, {lr.carried} carried")
        return "\n".join(lines)
