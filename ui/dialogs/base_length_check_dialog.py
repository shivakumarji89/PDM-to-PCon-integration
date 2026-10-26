"""Base-length check - the trigger in a pop-up.

Point it at a repository, run the check (off the UI thread, with a progress
popup), write the central editable registry, then open the filterable results
table. Splits the base articles that differ from PDM CAD Maintenance from those
that match.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QComboBox,
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


class BaseLengthCheckDialog(DialogTemplate):
    """Check published base articles against PDM CAD Maintenance."""

    def __init__(self, context, repository: str = "", parent=None) -> None:
        super().__init__(parent)
        self._context = context
        self.set_title("Check Base Lengths")
        self.setMinimumSize(680, 460)
        self.add_content(self._build_form(repository))
        self.add_content(self._build_summary())
        self._build_footer()

    # -- construction ---------------------------------------------------

    def _build_form(self, repository: str) -> QWidget:
        box = QGroupBox("Base Length Check", self)
        form = QFormLayout(box)

        self._target = QComboBox(box)
        self._target.addItems(["XOCD packages (folders)", "OCD MDBs (files)"])
        form.addRow("Repository holds", self._target)

        repo_row = QHBoxLayout()
        self._repo = QLineEdit(box)
        self._repo.setText(repository)
        self._repo.setPlaceholderText("Repository root(s) - separate several with ';'")
        browse = QPushButton("Browse...", box)
        browse.clicked.connect(self._on_browse)
        repo_row.addWidget(self._repo, 1)
        repo_row.addWidget(browse)
        form.addRow("Repository", repo_row)
        return box

    def _build_summary(self) -> QWidget:
        box = QGroupBox("Result", self)
        layout = QVBoxLayout(box)
        self._summary = QPlainTextEdit(box)
        self._summary.setReadOnly(True)
        self._summary.setPlaceholderText(
            "Compare each package's base article against PDM CAD Maintenance "
            "(Item.Notes). Run the check to build the editable registry.")
        layout.addWidget(self._summary)
        return box

    def _build_footer(self) -> None:
        check_btn = QPushButton("Check", self)
        check_btn.clicked.connect(self._on_check)
        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        for btn in (check_btn, close_btn):
            self.add_footer_button(btn)

    # -- helpers --------------------------------------------------------

    def _is_mdb(self) -> bool:
        return self._target.currentIndex() == 1

    def _on_browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select a repository root")
        if not path:
            return
        parts = [p.strip() for p in self._repo.text().split(";") if p.strip()]
        if path not in parts:
            parts.append(path)
        self._repo.setText(";".join(parts))

    def _progress_monitor(self):
        monitor = getattr(self, "_monitor", None)
        if monitor is None:
            from ui.dialogs.progress_dialog import ProgressDialog
            monitor = ProgressDialog(self)
            self._monitor = monitor
        return monitor

    # -- actions --------------------------------------------------------

    def _on_check(self) -> None:
        if getattr(self, "_run_task", None) is not None and self._run_task.active:
            return
        repo = self._repo.text().strip()
        if not repo:
            QMessageBox.information(self, "Base Length Check", "Choose the repository root.")
            return
        run = self._run_task = ReportedTask(self)
        reporter = run.reporter
        monitor = self._progress_monitor()
        monitor.bind(reporter)
        monitor.show()
        monitor.raise_()
        svc, is_mdb = self._context.price_update_service, self._is_mdb()
        reg_dir = QSettings().value("baseLengthRegistryDir", "", type=str)
        target = svc.registry_path(reg_dir or None)

        def work(_emit):
            packages = svc._discover_packages(repo, is_mdb)
            reporter.begin(len(packages) + 1, title="Check Base Lengths",
                           subject=Path(repo.split(";")[0].strip()).name)
            rows = svc.build_base_length_registry(
                repo, is_mdb, progress=lambda done, total, text: reporter.advance(text))
            if not rows:
                return rows, None, ""
            try:
                path = svc.write_base_length_registry(target, rows)
            except OSError as exc:
                return rows, None, str(exc)
            return rows, path, ""

        run.start(work, finished=lambda outcome: self._on_ready(*outcome), failed=self._on_failed,
                  cancelled=self._on_cancelled)

    def _on_cancelled(self, message: str) -> None:
        self._summary.setPlainText(message + "\nRegistry unchanged.")

    def done(self, result: int) -> None:
        run = getattr(self, "_run_task", None)
        if run is not None and run.active:
            run.reporter.request_cancel()
        super().done(result)

    def _on_failed(self, message: str) -> None:
        QMessageBox.warning(self, "Base Length Check", f"Check failed:\n{message}")

    def _on_ready(self, rows, path=None, error="") -> None:
        """Write the registry, then open the filterable results table."""
        from ui.dialogs.base_length_dialog import BaseLengthDialog

        repo = self._repo.text().strip()
        if not rows:
            kind = "OCD MDBs (files)" if self._is_mdb() else "XOCD packages (folders)"
            other = "XOCD packages (folders)" if self._is_mdb() else "OCD MDBs (files)"
            QMessageBox.information(
                self, "Base Length Check",
                f"No articles found under:\n{repo}\n\nfor the '{kind}' target. "
                f"If this folder holds the other package form, switch 'Repository holds' "
                f"to '{other}' and try again.")
            return
        settings = QSettings()
        reg_dir = settings.value("baseLengthRegistryDir", "", type=str)
        svc = self._context.price_update_service
        if path is None:
            self._write_registry(svc, svc.registry_path(reg_dir or None), rows, settings, error)
            return
        self._summary.setPlainText(self._render_registry(rows, path))
        BaseLengthDialog(rows, path, svc, self).exec()

    def _write_registry(self, svc, target, rows, settings, error=""):
        """Choose a writable location and retry using a fresh cancellable run."""
        if getattr(self, "_run_task", None) is not None and self._run_task.active:
            return
        chosen, _ = QFileDialog.getSaveFileName(
            self, f"Cannot write to {target} ({error}). Choose a location:",
            str(target), "CSV (*.csv)")
        if not chosen:
            return
        run = self._run_task = ReportedTask(self)
        reporter = run.reporter
        monitor = self._progress_monitor()
        monitor.bind(reporter)
        monitor.show()
        monitor.raise_()

        def work(_emit):
            reporter.begin(1, title="Write Base Length Registry", subject=Path(chosen).name)
            return svc.write_base_length_registry(chosen, rows)

        def finished(path):
            settings.setValue("baseLengthRegistryDir", str(Path(chosen).parent))
            self._on_ready(rows, path)

        run.start(work, finished=finished, failed=self._on_failed, cancelled=self._on_cancelled)

    @staticmethod
    def _render_registry(rows, path) -> str:
        mism = [r for r in rows if r["Status"] == "MISMATCH"]
        no_cad = [r for r in rows if r["Status"] == "NO_CAD"]
        lines = [
            f"Base-length registry written: {path}",
            f"{len(rows)} article(s) - {len(mism)} differ from CAD, "
            f"{len(no_cad)} with no CAD length.",
            "",
        ]
        for r in mism[:100]:
            lines.append(
                f"  [{r['Program']}] {r['CurrentBase']}  (item {r['Item']}, "
                f"CAD len {r['CAD_Length']} -> {r['Expected_Base']})")
        lines.append("")
        lines.append(
            "Edit 'Override_Length' in the file where you disagree with CAD, then save. "
            "Blank = trust CAD." if mism else
            "All published articles match CAD Maintenance.")
        return "\n".join(lines)
