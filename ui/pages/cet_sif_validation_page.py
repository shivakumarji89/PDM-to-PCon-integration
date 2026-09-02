"""CET SIF Validation workspace page.

Standalone tool to validate a CET-generated SIF order file against PDM: load
one or more ``.sif`` files, click "Launch Item Entry", and every order line is
re-priced against PDM (via the same UDFs PDM uses) so any price discrepancy is
flagged. Self-contained and easily disconnectable - set
``CET_SIF_VALIDATION_ENABLED = False`` in :mod:`core.workflow`.
"""
from __future__ import annotations

from pathlib import Path
#from unittest import signals

from PySide6.QtCore import QDate, QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.components import SectionHeader, StatisticsGrid
from ui.pages.base_page import BasePage


class _SifSignals(QObject):
    finished = Signal(object)   # (site, results)
    failed = Signal(str)
    line_done = Signal(object)  # a single SifResult, streamed as it completes


class _SifWorker(QRunnable):
    """Runs the SIF validation off the UI thread, driving a ProgressReporter."""

    def __init__(self, svc, currency, lines, site_id, obx, validation_date, reporter, signals):
        super().__init__()
        self._svc = svc
        self._currency = currency
        self._lines = lines
        self._site_id = site_id
        self._obx = obx
        self._validation_date = validation_date
        self._reporter = reporter
        self._signals = signals
        
    def run(self) -> None:
        try:
            self._reporter.begin(max(len(self._lines), 1), title="Validate SIF",
                                 subject=f"{len(self._lines)} order line(s)")
            site, results = self._svc.validate(
                self._currency,
                self._lines,
                site=self._site_id,
                obx=self._obx,
                validation_date=self._validation_date,
                progress=lambda done, total, text: self._reporter.advance(text),
                stage=lambda text: self._reporter.note(text),
                on_result=lambda r: self._signals.line_done.emit(r),
            )

        except Exception as exc:  # never crash the worker thread
            self._reporter.finish(False, str(exc))
            self._signals.failed.emit(str(exc))
        else:
            self._reporter.finish(True, f"{len(results)} line(s)")
            self._signals.finished.emit((site, results))


class CetSifValidationPage(BasePage):
    """Validate a CET SIF order file's prices against PDM."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="CET SIF Validation",
            description="Validate a CET SIF order file's prices against PDM.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._currency = ""
        self._lines: list = []
        self._results: list = []
        self._source_path = ""
        self._show_all = True
        self.add_content(self._build_controls())
        self.add_content(self._build_results())

    # -- construction ---------------------------------------------------

    def _build_controls(self) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_2)
        layout.addWidget(SectionHeader(
            "Order file", "Load a CET SIF file, then launch item entry to validate every line against PDM."))
        row = QHBoxLayout()
        row.setSpacing(theme.SPACE_2)
        self._load_btn = QPushButton("Load SIF File...", container)
        self._load_btn.clicked.connect(self._on_load)
        self._folder_btn = QPushButton("Load Folder...", container)
        self._folder_btn.clicked.connect(self._on_load_folder)
        self._launch_btn = QPushButton("Launch Item Entry", container)
        self._launch_btn.setEnabled(False)
        self._launch_btn.clicked.connect(self._on_launch)
        row.addWidget(self._load_btn)
        row.addWidget(self._folder_btn)
        row.addWidget(self._launch_btn)
        row.addWidget(QLabel("Validation date:", container))
        self._validation_date = QDateEdit(container)
        self._validation_date.setDisplayFormat("dd-MMM-yyyy")
        self._validation_date.setCalendarPopup(True)
        self._validation_date.setDate(QDate.currentDate())
        row.addWidget(self._validation_date)
        row.addStretch(1)
        layout.addLayout(row)
        self._file_label = QLabel("No file loaded.", container)
        self._file_label.setStyleSheet(f"color: {theme.MUTED};")
        layout.addWidget(self._file_label)
        return container

    def _build_results(self) -> QWidget:
        container = QWidget(self)
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_2)
        head = QHBoxLayout()
        head.addWidget(SectionHeader("Results", "Every order line is listed with its PDM result - VALID or the error comment."))
        head.addStretch(1)
        self._export_btn = QPushButton("Export to CSV...", container)
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export)
        head.addWidget(self._export_btn, 0, Qt.AlignmentFlag.AlignTop)
        self._rebuild_btn = QPushButton("Rebuild table", container)
        self._rebuild_btn.setEnabled(False)
        self._rebuild_btn.clicked.connect(self._on_rebuild)
        head.addWidget(self._rebuild_btn, 0, Qt.AlignmentFlag.AlignTop)
        self._toggle_btn = QPushButton("Show errors only", container)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)
        self._toggle_btn.toggled.connect(self._on_toggle_all)
        self._toggle_btn.setEnabled(False)
        head.addWidget(self._toggle_btn, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(head)

        self._grid = StatisticsGrid(columns=4, parent=container)
        self._grid.set_metric("lines", "Order lines", "-")
        self._grid.set_metric("ok", "Matched", "-")
        self._grid.set_metric("mismatch", "Price mismatch", "-")
        self._grid.set_metric("unresolved", "Unresolved", "-")
        layout.addWidget(self._grid)

        self._table = QTableWidget(0, 7, container)
        self._table.setHorizontalHeaderLabels(
            ["#", "SKU", "Category (PLC)", "Qty", "SIF price", "PDM price", "Result"])
        self._table.setSortingEnabled(False)  # we control row order by seq; sorting would scatter cells
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)
        return container

    # -- actions --------------------------------------------------------

    def _on_load(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Load SIF / OBX file(s)",
            "",
            "SIF / OBX order files (*.sif *.obx);;SIF files (*.sif);;OBX files (*.obx);;All files (*.*)"
        )
        if paths:
            self._load_paths(paths)

    def _on_load_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Load all SIF / OBX files in folder"
        )

        if not folder:
            return

        folder_path = Path(folder)

        paths = sorted(
            str(p)
            for p in folder_path.iterdir()
            if p.is_file() and p.suffix.lower() in {".sif", ".obx"}
        )

        if not paths:
            QMessageBox.information(
                self,
                "CET SIF Validation",
                "No .sif or .obx files found in that folder."
            )
            return

        self._load_paths(paths)

    def _load_paths(self, paths: list[str]) -> None:
        svc = self._context.sif_validation_service
        currency, lines = "", []
        self._file_of_seq: dict[int, str] = {}
        self._currency_of_path: dict[str, str] = {}
        loaded_paths: list[str] = []
        for path in paths:
            try:
                text = Path(path).read_text(encoding="utf-8", errors="ignore")
            except OSError as exc:
                QMessageBox.warning(self, "CET SIF Validation", f"Could not read {path}:\n{exc}")
                continue
            if Path(path).suffix.lower() == ".obx":
                cur, file_lines = svc.parse_obx(text)
            else:
                cur, file_lines = svc.parse_sif(text)
            if not currency:
                currency = cur
            self._currency_of_path[path] = cur
            loaded_paths.append(path)
            for line in file_lines:
                line.seq = len(lines) + 1
                lines.append(line)
                self._file_of_seq[line.seq] = path
        self._currency = currency
        self._lines = lines
        self._paths = loaded_paths
        self._source_path = loaded_paths[0] if loaded_paths else ""
        label = paths[0] if len(paths) == 1 else f"{len(paths)} files"
        currencies = sorted({l.currency for l in lines if l.currency}) or [currency]
        self._file_label.setText(
            f"{Path(label).name if len(paths) == 1 else label}  \u2014  "
            f"{len(lines)} line(s), currency {', '.join(c or '?' for c in currencies)}")
        self._launch_btn.setEnabled(bool(lines))
        self._reset_results()

    def _on_launch(self) -> None:
        if not self._lines:
            return
        from core.progress import ProgressReporter

        reporter = ProgressReporter(self)
        monitor = self._progress_monitor()
        monitor.bind(reporter)
        monitor.show()
        monitor.raise_()
        signals = _SifSignals()
        signals.finished.connect(self._on_results)
        signals.failed.connect(self._on_failed)
        signals.line_done.connect(self._on_line_done)
        self._signals = signals  # keep a reference alive
        self._begin_live()
        site_id = None
        obx = bool(self._paths) and all(
            Path(p).suffix.lower() == ".obx"
            for p in self._paths
        )

        validation_date = self._validation_date.date().toString("dd-MMM-yyyy")
        
        QThreadPool.globalInstance().start(_SifWorker(
            self._context.sif_validation_service,
            self._currency,
            self._lines,
            site_id,
            obx,
            validation_date,
            reporter,
            signals,
        ))

    def _progress_monitor(self):
        monitor = getattr(self, "_monitor", None)
        if monitor is None:
            from ui.dialogs.progress_dialog import ProgressDialog
            monitor = ProgressDialog(self)
            self._monitor = monitor
        return monitor

    def _on_failed(self, message: str) -> None:
        QMessageBox.warning(self, "CET SIF Validation", f"Validation failed:\n{message}")

    def _begin_live(self) -> None:
        """Reset the results view so lines stream in one by one as they validate."""
        self._results = []
        self._live = {"lines": 0, "ok": 0, "mismatch": 0, "unresolved": 0}
        self._table.setSortingEnabled(False)  # global standardize_table() re-enables it; we order rows ourselves
        self._table.setRowCount(0)
        for key, label in (("lines", "Order lines"), ("ok", "Matched"),
                           ("mismatch", "Price mismatch"), ("unresolved", "Unresolved")):
            self._grid.set_metric(key, label, "0")
        self._toggle_btn.setEnabled(True)
        self._export_btn.setEnabled(False)
        self._rebuild_btn.setEnabled(True)

    def _on_line_done(self, r) -> None:
        """A single line finished validating - append it live and bump counters."""
        self._results.append(r)
        self._live["lines"] += 1
        key = "ok" if r.status == "ok" else ("mismatch" if r.status == "price_mismatch" else "unresolved")
        self._live[key] += 1
        self._grid.set_metric("lines", "Order lines", str(self._live["lines"]))
        self._grid.set_metric("ok", "Matched", str(self._live["ok"]))
        self._grid.set_metric("mismatch", "Price mismatch", str(self._live["mismatch"]))
        self._grid.set_metric("unresolved", "Unresolved", str(self._live["unresolved"]))
        if self._show_all or r.status != "ok":
            self._append_row(r)

    def _on_results(self, payload) -> None:
        sites, results = payload
        self._results = results
        ok = sum(1 for r in results if r.status == "ok")
        mism = sum(1 for r in results if r.status == "price_mismatch")
        unres = sum(1 for r in results if r.status == "unresolved")
        self._grid.set_metric("lines", "Order lines", str(len(results)))
        self._grid.set_metric("ok", "Matched", str(ok))
        self._grid.set_metric("mismatch", "Price mismatch", str(mism))
        self._grid.set_metric("unresolved", "Unresolved", str(unres))
        self._toggle_btn.setEnabled(True)
        self._export_btn.setEnabled(bool(results))
        self._rebuild_btn.setEnabled(bool(results))
        self._render_table()
        site_text = ", ".join(f"{cur}\u2192site {s}" for cur, s in sites.items())
        if mism == 0 and unres == 0:
            QMessageBox.information(
                self, "CET SIF Validation",
                f"All {len(results)} line(s) match PDM ({site_text}).")

    def _on_toggle_all(self, checked: bool) -> None:
        self._show_all = checked
        self._toggle_btn.setText("Show errors only" if checked else "Show all lines")
        self._render_table()

    def _on_rebuild(self) -> None:
        """Force a clean rebuild of the table from the validated data."""
        self._render_table()

    def _on_export(self) -> None:
        if not self._results:
            return
        paths = getattr(self, "_paths", [])
        svc = self._context.sif_validation_service
        # One source file -> a single CSV, as before.
        if len(paths) <= 1:
            default = str(Path(self._source_path).with_suffix(".csv")) if self._source_path else ""
            path, _ = QFileDialog.getSaveFileName(
                self, "Export validation report", default, "CSV files (*.csv);;All files (*.*)")
            if not path:
                return
            try:
                svc.export_csv(path, self._currency, self._results)
            except OSError as exc:
                QMessageBox.warning(self, "CET SIF Validation", f"Could not write CSV:\n{exc}")
                return
            QMessageBox.information(self, "CET SIF Validation", "Validation report exported successfully.")
            return
        # Folder / multiple files -> one CSV per source SIF file.
        out_dir = QFileDialog.getExistingDirectory(
            self, "Choose a folder for the per-file CSV reports",
            str(Path(paths[0]).parent))
        if not out_dir:
            return
        file_of_seq = getattr(self, "_file_of_seq", {})
        cur_of_path = getattr(self, "_currency_of_path", {})
        written, failed = 0, []
        for src in paths:
            rows = sorted((r for r in self._results if file_of_seq.get(r.seq) == src),
                          key=lambda r: r.seq)
            if not rows:
                continue
            target = str(Path(out_dir) / (Path(src).stem + ".csv"))
            try:
                svc.export_csv(target, cur_of_path.get(src, self._currency), rows)
                written += 1
            except OSError as exc:
                failed.append(f"{Path(src).name}: {exc}")
        msg = f"Exported {written} per-file report(s) to:\n{out_dir}"
        if failed:
            msg += "\n\nFailed:\n" + "\n".join(failed)
        QMessageBox.information(self, "CET SIF Validation", msg)

    # -- rendering ------------------------------------------------------

    def _reset_results(self) -> None:
        self._results = []
        self._table.setRowCount(0)
        for key, label in (("lines", "Order lines"), ("ok", "Matched"),
                           ("mismatch", "Price mismatch"), ("unresolved", "Unresolved")):
            self._grid.set_metric(key, label, "-")
        self._toggle_btn.setChecked(True)
        self._toggle_btn.setEnabled(False)
        self._export_btn.setEnabled(False)
        self._rebuild_btn.setEnabled(False)

    def _render_table(self) -> None:
        rows = self._results if self._show_all else [r for r in self._results if r.status != "ok"]
        rows = sorted(rows, key=lambda r: self._seq_key(r.seq))
        self._table.setSortingEnabled(False)  # global standardize_table() re-enables it; we order rows ourselves
        self._table.setRowCount(0)
        for r in rows:
            self._put_row(self._table.rowCount(), r)

    @staticmethod
    def _seq_key(seq) -> int:
        """Numeric sort key for the # column, tolerant of str/int seq values."""
        try:
            return int(seq)
        except (TypeError, ValueError):
            return 0

    def _append_row(self, r) -> None:
        """Insert a streamed result at its sorted # position so the table stays ascending."""
        seq = self._seq_key(r.seq)
        pos = self._table.rowCount()
        for i in range(self._table.rowCount()):
            it = self._table.item(i, 0)
            try:
                if it is not None and int(it.text()) > seq:
                    pos = i
                    break
            except (TypeError, ValueError):
                continue
        self._put_row(pos, r)
        if pos == self._table.rowCount() - 1:
            self._table.scrollToBottom()

    def _put_row(self, row: int, r) -> None:
        self._table.insertRow(row)
        cells = [
            str(r.seq), r.sku, r.plc, str(r.qty), f"{r.sif_price:.2f}",
            "-" if r.pdm_price is None else f"{r.pdm_price:.2f}",
            r.result,
        ]
        for col, text in enumerate(cells):
            cell = QTableWidgetItem(text)
            if col in (0, 3, 4, 5):
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if r.status != "ok":
                cell.setForeground(Qt.GlobalColor.red)
            self._table.setItem(row, col, cell)
