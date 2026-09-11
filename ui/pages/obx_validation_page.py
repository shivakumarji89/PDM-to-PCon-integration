"""OBX Validation workspace page."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDate, QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.errors import PDMConnectionError
from core.validation_control import ValidationCancelled, ValidationControl, ValidationPaused
from ui import theme
from ui.pages.base_page import BasePage


class _ObxSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    paused = Signal(object)
    cancelled = Signal(str)
    line_done = Signal(object)


class _ObxWorker(QRunnable):
    """Run OBX validation off the UI thread with recovery and checkpoints."""

    _MAX_RECOVERY_ATTEMPTS = 3

    def __init__(self, svc, currency, lines, site_id, validation_date, reporter, signals, control):
        super().__init__()
        self._svc = svc
        self._currency = currency
        self._lines = lines
        self._site_id = site_id
        self._validation_date = validation_date
        self._reporter = reporter
        self._signals = signals
        self._control = control

    @staticmethod
    def _is_connection_error(exc: Exception) -> bool:
        current = exc
        seen: set[int] = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, PDMConnectionError):
                return True
            text = str(current).lower()
            markers = (
                "08001", "08s01", "connectionread", "general network error",
                "communication link failure", "tcp provider", "connection is broken",
                "connection was closed", "server has gone away", "connection reset",
                "connection aborted", "network is unreachable", "network path was not found",
                "connection timeout", "connect timeout", "timed out",
            )
            if any(marker in text for marker in markers):
                return True
            current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
        return False

    def run(self) -> None:
        completed: dict[int, object] = {}
        pending = list(self._lines)
        sites: dict = {}
        recovery_attempts = 0
        total = len(self._lines)

        self._reporter.begin(max(total, 1), title="Validate OBX", subject=f"{total} order line(s)")

        def on_result(result) -> None:
            key = getattr(result, "seq", None)
            if key in completed:
                return
            completed[key] = result
            self._reporter.advance(f"Validated line {key}")
            self._signals.line_done.emit(result)

        while pending:
            try:
                self._control.checkpoint()
                site, results = self._svc.validate(
                    self._currency,
                    pending,
                    site=self._site_id,
                    validation_date=self._validation_date,
                    progress=None,
                    stage=lambda text: self._reporter.note(text),
                    on_result=on_result,
                    operation_control=self._control,
                )
                if site:
                    sites.update(site)
                for result in results:
                    on_result(result)
                pending = [line for line in pending if getattr(line, "seq", None) not in completed]
                recovery_attempts = 0
                if not pending:
                    break
            except ValidationPaused as exc:
                reason = str(exc) or "Validation paused."
                self._reporter.pause(reason)
                pending = [line for line in pending if getattr(line, "seq", None) not in completed]
                self._signals.paused.emit((sites, pending, reason))
                return
            except ValidationCancelled as exc:
                self._reporter.finish(False, "Validation cancelled.")
                self._signals.cancelled.emit(str(exc) or "Validation cancelled.")
                return
            except Exception as exc:
                if self._control.is_cancelled():
                    self._reporter.finish(False, "Validation cancelled.")
                    self._signals.cancelled.emit("Validation cancelled.")
                    return
                if self._control.is_paused():
                    reason = "Validation paused."
                    self._reporter.pause(reason)
                    pending = [line for line in pending if getattr(line, "seq", None) not in completed]
                    self._signals.paused.emit((sites, pending, reason))
                    return
                if not self._is_connection_error(exc):
                    self._reporter.finish(False, str(exc))
                    self._signals.failed.emit(str(exc))
                    return

                pending = [line for line in pending if getattr(line, "seq", None) not in completed]
                if recovery_attempts >= self._MAX_RECOVERY_ATTEMPTS:
                    reason = (
                        f"PDM connection unavailable after {self._MAX_RECOVERY_ATTEMPTS} "
                        f"recovery attempts."
                    )
                    self._reporter.pause(reason)
                    self._signals.paused.emit((sites, pending, reason))
                    return

                recovery_attempts += 1
                self._reporter.note(
                    f"PDM connection lost. Reconnecting (attempt {recovery_attempts}/"
                    f"{self._MAX_RECOVERY_ATTEMPTS})..."
                )

        results = sorted(completed.values(), key=lambda result: self._seq_key(getattr(result, "seq", 0)))
        self._reporter.finish(True, f"{len(results)} line(s)")
        self._signals.finished.emit((sites, results))

    @staticmethod
    def _seq_key(seq) -> int:
        try:
            return int(seq)
        except (TypeError, ValueError):
            return 0


class ObxValidationPage(BasePage):
    """Validate a CET OBX file's prices against PDM."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="OBX Validation",
            description="Validate a CET OBX file's prices against PDM.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._currency = ""
        self._lines: list = []
        self._results: list = []
        self._pending_lines: list = []
        self._source_path = ""
        self._show_all = True
        self._is_paused = False
        self._skipped_count = 0
        self._duplicate_count = 0
        self._active_control: ValidationControl | None = None
        self._active_reporter = None
        self._recovery_attempt = 0
        self.add_content(self._build_controls())
        self.add_content(self._build_progress_panel())
        self.add_content(self._build_results())

    def _build_controls(self) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_2)
        self._load_btn = QToolButton(container)
        self._load_btn.setText("Load OBX...")
        self._load_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._load_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        load_menu = QMenu(self._load_btn)
        load_menu.addAction("Select file(s)...", self._on_load)
        load_menu.addAction("Select folder...", self._on_load_folder)
        self._load_btn.setMenu(load_menu)
        self._launch_btn = QPushButton("Launch Item Entry", container)
        self._launch_btn.setEnabled(False)
        self._launch_btn.clicked.connect(self._on_launch)
        self._pause_btn = QPushButton("Pause Validation", container)
        self._pause_btn.setEnabled(False)
        self._pause_btn.clicked.connect(self._on_pause_resume)
        self._cancel_btn = QPushButton("Cancel Validation", container)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self._load_btn)
        layout.addWidget(self._launch_btn)
        layout.addWidget(self._pause_btn)
        layout.addWidget(self._cancel_btn)
        layout.addWidget(QLabel("Validation date:", container))
        self._validation_date = QDateEdit(container)
        self._validation_date.setDisplayFormat("dd-MMM-yyyy")
        self._validation_date.setCalendarPopup(True)
        self._validation_date.setDate(QDate.currentDate())
        layout.addWidget(self._validation_date)
        layout.addStretch(1)
        return container

    def _build_progress_panel(self) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("obxProgressPanel")
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(theme.SPACE_2, theme.SPACE_2, theme.SPACE_2, theme.SPACE_2)
        layout.setSpacing(theme.SPACE_1)

        header = QHBoxLayout()
        self._progress_state = QLabel("READY", panel)
        self._progress_state.setStyleSheet("font-weight: 600;")
        self._file_label = QLabel("No OBX file loaded.", panel)
        self._file_label.setStyleSheet(f"color: {theme.MUTED};")
        header.addWidget(self._progress_state)
        header.addWidget(self._file_label, 1)
        self._export_btn = QPushButton("Export to CSV...", panel)
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export)
        header.addWidget(self._export_btn)
        self._toggle_btn = QPushButton("Show errors only", panel)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)
        self._toggle_btn.toggled.connect(self._on_toggle_all)
        self._toggle_btn.setEnabled(False)
        header.addWidget(self._toggle_btn)
        layout.addLayout(header)

        progress_row = QHBoxLayout()
        self._progress_bar = QProgressBar(panel)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_percent = QLabel("0%", panel)
        self._progress_percent.setMinimumWidth(42)
        self._progress_percent.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(self._progress_bar, 1)
        progress_row.addWidget(self._progress_percent)
        layout.addLayout(progress_row)

        detail_row = QHBoxLayout()
        self._current_line = QLabel("Current line: -", panel)
        self._current_sku = QLabel("Current SKU: -", panel)
        self._current_status = QLabel("Status: -", panel)
        detail_row.addWidget(self._current_line)
        detail_row.addWidget(self._current_sku, 1)
        detail_row.addWidget(self._current_status)
        layout.addLayout(detail_row)

        self._metrics: dict[str, QLabel] = {}
        metrics = [
            ("completed", "Completed"), ("remaining", "Remaining"),
            ("matched", "Matched"), ("mismatch", "Price mismatch"),
            ("unresolved", "Unresolved"), ("skipped", "Skipped"),
            ("duplicate", "Duplicate"), ("elapsed", "Elapsed"),
            ("eta", "ETA"), ("speed", "Speed"),
            ("site", "PDM site"), ("recovery", "Recovery"),
        ]
        grid = QGridLayout()
        grid.setHorizontalSpacing(theme.SPACE_2)
        grid.setVerticalSpacing(theme.SPACE_1)
        for index, (key, title) in enumerate(metrics):
            label = QLabel(f"{title}: -", panel)
            self._metrics[key] = label
            grid.addWidget(label, index // 6, index % 6)
        layout.addLayout(grid)
        panel.setMaximumHeight(190)
        return panel

    def _build_results(self) -> QWidget:
        container = QWidget(self)
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_1)
        self._table = QTableWidget(0, 8, container)
        self._table.setHorizontalHeaderLabels(
            ["#", "SKU", "Category (PLC)", "Qty", "OBX price", "PDM price", "Source date", "Result"])
        self._table.setSortingEnabled(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)
        return container

    def _on_load(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Load OBX file(s)", "", "OBX files (*.obx);;All files (*.*)")
        if paths:
            self._load_paths(paths)

    def _on_load_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Load all OBX files in folder")
        if not folder:
            return
        folder_path = Path(folder)
        paths = sorted(str(p) for p in folder_path.iterdir() if p.is_file() and p.suffix.lower() == ".obx")
        if not paths:
            QMessageBox.information(self, "OBX Validation", "No .obx files found in that folder.")
            return
        self._load_paths(paths)

    def _load_paths(self, paths: list[str]) -> None:
        svc = self._context.obx_validation_service
        currency, lines = "", []
        skipped_count = 0
        self._file_of_seq: dict[int, str] = {}
        self._currency_of_path: dict[str, str] = {}
        loaded_paths: list[str] = []
        for path in paths:
            try:
                text = Path(path).read_text(encoding="utf-8", errors="ignore")
            except OSError as exc:
                QMessageBox.warning(self, "OBX Validation", f"Could not read {path}:\n{exc}")
                continue
            cur, file_lines = svc.parse_obx(text)
            skipped_count += getattr(svc, "last_parse_skipped_count", 0)
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
        self._skipped_count = skipped_count
        self._duplicate_count = svc.duplicate_count(lines)
        label = Path(loaded_paths[0]).name if len(loaded_paths) == 1 else f"{len(loaded_paths)} OBX files"
        currencies = sorted({l.currency for l in lines if l.currency}) or [currency]
        self._file_label.setText(
            f"{label}  •  {len(lines)} lines  •  {', '.join(c or '?' for c in currencies)}")
        self._launch_btn.setEnabled(bool(lines))
        self._pause_btn.setEnabled(False)
        self._pause_btn.setText("Pause Validation")
        self._cancel_btn.setEnabled(False)
        self._pending_lines = []
        self._is_paused = False
        self._reset_results()

    def _on_launch(self) -> None:
        if self._lines:
            self._start_validation(self._lines, fresh=True)

    def _on_pause_resume(self) -> None:
        if self._active_control is not None:
            self._on_pause()
        elif self._pending_lines:
            self._on_resume()

    def _on_pause(self) -> None:
        control = self._active_control
        reporter = self._active_reporter
        if control is None or reporter is None:
            return
        control.pause()
        reporter.pause("Pause requested. The active SQL operation will finish, then validation will pause before the next DB operation.")
        self._pause_btn.setText("Resume Validation")
        self._pause_btn.setEnabled(False)
        self._progress_state.setText("PAUSING")

    def _on_resume(self) -> None:
        if self._pending_lines:
            self._start_validation(self._pending_lines, fresh=False)

    def _on_cancel(self) -> None:
        control = self._active_control
        if control is None:
            return
        control.cancel()
        self._cancel_btn.setEnabled(False)
        self._pause_btn.setEnabled(False)
        self._progress_state.setText("CANCELLING")
        self._current_status.setText("Status: Cancellation requested. Stopping the active SQL operation...")

    def _start_validation(self, lines: list, fresh: bool) -> None:
        from core.progress import ProgressReporter

        reporter = ProgressReporter(self)
        control = ValidationControl()
        self._active_control = control
        self._active_reporter = reporter
        reporter.progress_changed.connect(self._on_progress_changed)
        reporter.elapsed_changed.connect(self._on_elapsed_changed)
        reporter.remaining_changed.connect(self._on_remaining_changed)
        reporter.step_changed.connect(self._on_progress_step)
        signals = _ObxSignals()
        signals.finished.connect(self._on_results)
        signals.failed.connect(self._on_failed)
        signals.paused.connect(self._on_paused)
        signals.cancelled.connect(self._on_cancelled)
        signals.line_done.connect(self._on_line_done)
        self._signals = signals
        if fresh:
            self._begin_live()
        self._is_paused = False
        self._pause_btn.setText("Pause Validation")
        self._pause_btn.setEnabled(True)
        self._cancel_btn.setEnabled(True)
        self._launch_btn.setEnabled(False)
        self._progress_state.setText("VALIDATING")
        validation_date = self._validation_date.date().toString("dd-MMM-yyyy")
        QThreadPool.globalInstance().start(_ObxWorker(
            self._context.obx_validation_service,
            self._currency,
            lines,
            None,
            validation_date,
            reporter,
            signals,
            control,
        ))

    def _release_active_control(self) -> None:
        self._active_control = None
        self._active_reporter = None
        self._pause_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)

    def _on_progress_changed(self, percent: int) -> None:
        self._progress_bar.setValue(percent)
        self._progress_percent.setText(f"{percent}%")

    def _on_elapsed_changed(self, seconds: int) -> None:
        self._set_metric("elapsed", self._format_duration(seconds))
        completed = len(self._results)
        if seconds > 0 and completed:
            self._set_metric("speed", f"{completed / seconds:.1f}/s")

    def _on_remaining_changed(self, seconds: int) -> None:
        self._set_metric("eta", self._format_duration(seconds) if seconds else "-")

    def _on_progress_step(self, text: str) -> None:
        if text.startswith("PDM connection lost.") and "attempt" in text:
            try:
                self._recovery_attempt = int(text.split("attempt ", 1)[1].split("/", 1)[0])
            except (ValueError, IndexError):
                pass
            self._set_metric("recovery", f"{self._recovery_attempt}/3")
        if text:
            self._current_status.setText(f"Status: {text}")

    def _on_failed(self, message: str) -> None:
        self._release_active_control()
        self._pause_btn.setText("Pause Validation")
        self._launch_btn.setEnabled(bool(self._lines))
        self._progress_state.setText("FAILED")
        self._current_status.setText(f"Status: {message}")
        QMessageBox.warning(self, "OBX Validation", f"Validation failed:\n{message}")

    def _on_cancelled(self, message: str) -> None:
        self._release_active_control()
        self._pending_lines = []
        self._is_paused = False
        self._pause_btn.setText("Pause Validation")
        self._launch_btn.setEnabled(bool(self._lines))
        self._progress_state.setText("CANCELLED")
        self._current_status.setText("Status: Validation cancelled by user.")

    def _on_paused(self, payload) -> None:
        sites, remaining_lines, reason = payload
        self._release_active_control()
        self._pending_lines = list(remaining_lines)
        self._is_paused = True
        self._launch_btn.setEnabled(False)
        self._pause_btn.setText("Resume Validation")
        self._pause_btn.setEnabled(bool(self._pending_lines))
        self._progress_state.setText("PAUSED")
        self._current_status.setText(f"Status: {reason}")
        self._set_metric("completed", str(len(self._results)))
        self._set_metric("remaining", str(len(self._pending_lines)))
        self._set_metric("skipped", str(self._skipped_count))
        self._set_metric("duplicate", str(self._duplicate_count))
        self._export_btn.setEnabled(bool(self._results))
        self._set_site_metrics(sites)

    def _begin_live(self) -> None:
        self._results = []
        self._pending_lines = []
        self._live = {"lines": 0, "ok": 0, "mismatch": 0, "unresolved": 0}
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        self._progress_state.setText("READY")
        self._progress_bar.setValue(0)
        self._progress_percent.setText("0%")
        self._current_line.setText("Current line: -")
        self._current_sku.setText("Current SKU: -")
        self._current_status.setText("Status: Ready to validate")
        self._recovery_attempt = 0
        for key in ("completed", "matched", "mismatch", "unresolved", "elapsed", "eta", "speed", "site"):
            self._set_metric(key, "0" if key in {"completed", "matched", "mismatch", "unresolved"} else "-")
        self._set_metric("remaining", str(len(self._lines)))
        self._set_metric("skipped", str(self._skipped_count))
        self._set_metric("duplicate", str(self._duplicate_count))
        self._set_metric("recovery", "0/3")
        self._toggle_btn.setEnabled(True)
        self._export_btn.setEnabled(False)

    def _on_line_done(self, r) -> None:
        self._results.append(r)
        self._export_btn.setEnabled(True)
        self._live["lines"] += 1
        key = "ok" if r.status == "ok" else ("mismatch" if r.status == "price_mismatch" else "unresolved")
        self._live[key] += 1
        completed = self._live["lines"]
        self._set_metric("completed", str(completed))
        self._set_metric("remaining", str(max(0, len(self._lines) - completed)))
        self._set_metric("matched", str(self._live["ok"]))
        self._set_metric("mismatch", str(self._live["mismatch"]))
        self._set_metric("unresolved", str(self._live["unresolved"]))
        self._set_metric("skipped", str(self._skipped_count))
        self._set_metric("duplicate", str(self._duplicate_count))
        self._current_line.setText(f"Current line: {r.seq}")
        self._current_sku.setText(f"Current SKU: {r.sku or '-'}")
        self._current_status.setText(f"Status: {r.result}")
        if self._show_all or r.status != "ok":
            self._append_row(r)

    def _on_results(self, payload) -> None:
        sites, results = payload
        self._release_active_control()
        self._pause_btn.setText("Pause Validation")
        self._results = results
        self._pending_lines = []
        self._is_paused = False
        self._launch_btn.setEnabled(bool(self._lines))
        self._pause_btn.setEnabled(False)
        ok = sum(1 for r in results if r.status == "ok")
        mism = sum(1 for r in results if r.status == "price_mismatch")
        unres = sum(1 for r in results if r.status == "unresolved")
        self._set_metric("completed", str(len(results)))
        self._set_metric("remaining", "0")
        self._set_metric("matched", str(ok))
        self._set_metric("mismatch", str(mism))
        self._set_metric("unresolved", str(unres))
        self._set_metric("skipped", str(self._skipped_count))
        self._set_metric("duplicate", str(self._duplicate_count))
        self._set_metric("eta", "0:00")
        self._set_metric("recovery", f"{self._recovery_attempt}/3")
        self._set_site_metrics(sites)
        self._progress_state.setText("COMPLETE")
        self._progress_bar.setValue(100)
        self._progress_percent.setText("100%")
        self._current_status.setText("Status: Validation complete")
        self._toggle_btn.setEnabled(True)
        self._export_btn.setEnabled(bool(results))
        self._render_table()
        site_text = ", ".join(f"{cur}→site {s}" for cur, s in sites.items())
        if mism == 0 and unres == 0:
            QMessageBox.information(self, "OBX Validation", f"All {len(results)} line(s) match PDM ({site_text}).")

    def _on_toggle_all(self, checked: bool) -> None:
        self._show_all = checked
        self._toggle_btn.setText("Show errors only" if checked else "Show all lines")
        self._render_table()

    def _on_export(self) -> None:
        if not self._results:
            return
        paths = getattr(self, "_paths", [])
        svc = self._context.obx_validation_service
        if len(paths) <= 1:
            default = str(Path(self._source_path).with_suffix(".csv")) if self._source_path else ""
            path, _ = QFileDialog.getSaveFileName(self, "Export validation report", default, "CSV files (*.csv);;All files (*.*)")
            if not path:
                return
            try:
                svc.export_csv(path, self._currency, self._results)
            except OSError as exc:
                QMessageBox.warning(self, "OBX Validation", f"Could not write CSV:\n{exc}")
                return
            QMessageBox.information(self, "OBX Validation", "Validation report exported successfully.")
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Choose a folder for the per-file CSV reports", str(Path(paths[0]).parent))
        if not out_dir:
            return
        file_of_seq = getattr(self, "_file_of_seq", {})
        cur_of_path = getattr(self, "_currency_of_path", {})
        written, failed = 0, []
        for src in paths:
            rows = sorted((r for r in self._results if file_of_seq.get(r.seq) == src), key=lambda r: r.seq)
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
        QMessageBox.information(self, "OBX Validation", msg)

    def _reset_results(self) -> None:
        self._results = []
        self._pending_lines = []
        self._is_paused = False
        self._table.setRowCount(0)
        self._progress_state.setText("READY")
        self._progress_bar.setValue(0)
        self._progress_percent.setText("0%")
        self._current_line.setText("Current line: -")
        self._current_sku.setText("Current SKU: -")
        self._current_status.setText("Status: Load an OBX file to begin")
        for key in ("completed", "matched", "mismatch", "unresolved", "elapsed", "eta", "speed", "site", "recovery"):
            self._set_metric(key, "-")
        self._set_metric("remaining", str(len(self._lines)))
        self._set_metric("skipped", str(self._skipped_count))
        self._set_metric("duplicate", str(self._duplicate_count))
        self._toggle_btn.setChecked(True)
        self._toggle_btn.setEnabled(False)
        self._export_btn.setEnabled(False)
        self._pause_btn.setEnabled(False)
        self._pause_btn.setText("Pause Validation")
        self._cancel_btn.setEnabled(False)

    def _set_metric(self, key: str, value: str) -> None:
        label = self._metrics.get(key)
        if label is not None:
            title = label.text().split(":", 1)[0]
            label.setText(f"{title}: {value}")

    def _set_site_metrics(self, sites: dict) -> None:
        if not sites:
            self._set_metric("site", "-")
            return
        self._set_metric("site", ", ".join(f"{cur} / {site}" for cur, site in sites.items()))

    @staticmethod
    def _format_duration(seconds: int) -> str:
        seconds = max(0, int(seconds))
        hours, rem = divmod(seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def _render_table(self) -> None:
        rows = self._results if self._show_all else [r for r in self._results if r.status != "ok"]
        rows = sorted(rows, key=lambda r: self._seq_key(r.seq))
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        for r in rows:
            self._put_row(self._table.rowCount(), r)

    @staticmethod
    def _seq_key(seq) -> int:
        try:
            return int(seq)
        except (TypeError, ValueError):
            return 0

    def _append_row(self, r) -> None:
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
            r.source_date or "-", r.result,
        ]
        for col, text in enumerate(cells):
            cell = QTableWidgetItem(text)
            if col in (0, 3, 4, 5):
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if r.status != "ok":
                cell.setForeground(Qt.GlobalColor.red)
            self._table.setItem(row, col, cell)
