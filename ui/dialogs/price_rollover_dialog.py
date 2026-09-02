"""Price-list roll-over - the full tool in a pop-up.

Point it at a repository of published packages (XOCD folders or OCD MDBs),
optionally pick a subset of series, set the effective date and new-list token,
then Scan to preview and Apply to write each package's roll-over in place.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDate, QObject, QRunnable, QThreadPool, Signal
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

#: PDM SiteId for the UK region - the only region we operate.
_UK_SITE_ID = 1


class _RollSignals(QObject):
    finished = Signal(object)   # BatchResult
    failed = Signal(str)


class _RollWorker(QRunnable):
    """Runs the roll-over off the UI thread (it re-prices from PDM and writes
    every package), driving a ProgressReporter so the popup stays live."""

    def __init__(self, svc, repo, is_mdb, effective, token, lookup, apply, packages,
                 reporter, signals, special_map=None):
        super().__init__()
        self._svc, self._repo, self._is_mdb = svc, repo, is_mdb
        self._effective, self._token, self._lookup = effective, token, lookup
        self._apply, self._packages = apply, packages
        self._reporter, self._signals = reporter, signals
        self._special_map = special_map

    def run(self) -> None:
        try:
            packages = self._packages
            if packages is None:
                packages = [str(p) for p in self._svc._discover_packages(self._repo, self._is_mdb)]
            first = self._repo.split(";")[0].strip()
            # One step per package; sub-stages and the live "priced N/M" count
            # update the text only (via note), so the bar creeps smoothly through
            # each package instead of lurching on every chunk.
            self._reporter.begin(max(len(packages), 1),
                                 title="Apply Roll-over" if self._apply else "Scan Roll-over",
                                 subject=Path(first).name if first else "")
            result = self._svc.run_batch(
                self._repo, self._is_mdb, self._effective, self._token, self._lookup,
                apply=self._apply, packages=packages,
                progress=lambda done, total, text: self._reporter.advance(text),
                stage=lambda text: self._reporter.note(text),
                special_map=self._special_map)
        except Exception as exc:  # never crash the worker thread
            self._reporter.finish(False, str(exc))
            self._signals.failed.emit(str(exc))
        else:
            self._reporter.finish(True, f"{len(result.packages)} package(s)")
            self._signals.finished.emit(result)


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
        error = self._inputs_ok()
        if error:
            QMessageBox.information(self, "Price Update", error)
            return
        from core.progress import ProgressReporter

        svc = self._context.price_update_service
        # Apply KNOWN special-case mappings inline; NEW ones are collected during
        # the roll and confirmed at the END, then updated in place (only those).
        special_map = svc.load_special_map() if self._compute.isChecked() else None

        reporter = ProgressReporter(self)
        monitor = self._progress_monitor()
        monitor.bind(reporter)
        monitor.show()
        monitor.raise_()
        signals = _RollSignals()
        signals.finished.connect(lambda result: self._on_result(result, apply))
        signals.failed.connect(self._on_failed)
        self._signals = signals  # keep a reference alive
        QThreadPool.globalInstance().start(_RollWorker(
            self._context.price_update_service, self._repo.text().strip(), self._is_mdb(),
            self._effective_ymd(), self._token.text().strip(), self._lookup(special_map),
            apply, self._selected_packages, reporter, signals, special_map))

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
        try:
            records = svc.scan_special_articles(list(carried.keys()), mydate, _UK_SITE_ID)
        except Exception:
            records = []
        if not records:
            return False
        from ui.dialogs.special_article_dialog import SpecialArticleDialog
        dialog = SpecialArticleDialog(records, self)
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.mapping:
            return False
        svc.save_special_map(dialog.mapping)
        updated = 0
        for pkg_path, codes in carried.items():
            pkg_map = {c: dialog.mapping[c] for c in codes if c in dialog.mapping}
            if pkg_map:
                count, err = svc.apply_special_articles(pkg_path, pkg_map, mydate, _UK_SITE_ID)
                updated += count
        QMessageBox.information(
            self, "Price Update",
            f"Rolled over {len(result.packages)} package(s).\n"
            f"Updated {updated} special-case price row(s) in place. "
            "Commit the repository to publish.")
        return True

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
