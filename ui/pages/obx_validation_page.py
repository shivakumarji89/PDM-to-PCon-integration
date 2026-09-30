"""OBX Validation workspace page."""
from __future__ import annotations

from pathlib import Path
import hashlib
import math
import json
import time
import xml.etree.ElementTree as ET

from PySide6.QtCore import QDate, QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QDateEdit, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QMenu, QMessageBox, QProgressBar, QPushButton,
    QSizePolicy, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
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
    recovery = Signal(object)
    line_done = Signal(object)


class _ObxWorker(QRunnable):
    """Validate one fixed worker slice.

    Two instances run concurrently with eight lines each. The outer page
    dispatcher controls memory batching separately.
    """

    _WORKER_SIZE = 8

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

        def on_result(result) -> None:
            key = getattr(result, "seq", None)
            if key in completed:
                return
            completed[key] = result
            self._reporter.advance(f"Validated line {key}")
            self._signals.line_done.emit(result)

        self._reporter.note(f"Worker processing {len(pending)} line(s).")
        while pending:
            try:
                self._control.checkpoint()
                site, results = self._svc.validate(
                    self._currency, pending, site=self._site_id,
                    validation_date=self._validation_date, progress=None,
                    stage=lambda text: self._reporter.note(text),
                    on_result=on_result,
                )
                if site:
                    sites.update(site)
                for result in results:
                    on_result(result)

                skipped_items = list(getattr(self._svc, "last_skipped_items", []) or [])
                if skipped_items:
                    skipped_set = set(skipped_items)
                    skipped_lines = [
                        line for line in pending
                        if getattr(line, "base", "") in skipped_set
                    ]
                    self._signals.paused.emit((
                        sites,
                        skipped_lines,
                        f"{len(skipped_lines)} line(s) skipped during worker pricing.",
                    ))
                    return

                pending = [
                    line for line in pending
                    if getattr(line, "seq", None) not in completed
                ]
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
                self._signals.cancelled.emit(str(exc) or "Validation cancelled.")
                return
            except Exception as exc:
                if self._control.is_cancelled():
                    self._signals.cancelled.emit("Validation cancelled.")
                    return
                if self._control.is_paused():
                    reason = "Validation paused."
                    self._reporter.pause(reason)
                    pending = [line for line in pending if getattr(line, "seq", None) not in completed]
                    self._signals.paused.emit((sites, pending, reason))
                    return
                if not self._is_connection_error(exc):
                    self._signals.failed.emit(str(exc))
                    return
                pending = [line for line in pending if getattr(line, "seq", None) not in completed]
                recovery_attempts += 1
                message = f"PDM connection lost. Reconnecting (attempt {recovery_attempts})..."
                self._reporter.note(message)
                self._signals.recovery.emit((recovery_attempts, None, message))

        results = sorted(
            completed.values(),
            key=lambda result: self._seq_key(getattr(result, "seq", 0)),
        )
        self._signals.finished.emit((sites, results))

    @staticmethod
    def _seq_key(seq) -> int:
        try:
            return int(seq)
        except (TypeError, ValueError):
            return 0


class ObxValidationPage(BasePage):
    """Validate a PCon OBX file's prices against PDM."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(title="OBX Validation", description="Validate a PCon OBX file's prices against PDM.", parent=parent, show_placeholder=False, content_stretch=True)
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
        self._validation_start_time = 0.0
        self._validation_elapsed_seconds = 0.0
        self._last_checkpoint_count = 0
        self._session = self._context.workflow_session("obx_validation")
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
        load_menu.addAction("Select folder (including subfolders)...", self._on_load_folder)
        self._load_btn.setMenu(load_menu)
        self._launch_btn = QPushButton("Launch Item Entry", container)
        self._launch_btn.setEnabled(False)
        self._launch_btn.clicked.connect(self._on_launch)
        self._load_btn.setFixedSize(self._launch_btn.sizeHint())
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
        self._export_btn = QPushButton("Export Individual CSVs...", container)
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export)
        layout.addWidget(self._export_btn)

        self._failed_export_btn = QToolButton(container)
        self._failed_export_btn.setText("Export Failed OBX...")
        self._failed_export_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._failed_export_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        failed_menu = QMenu(self._failed_export_btn)
        failed_menu.addAction("All failed articles", lambda: self._export_failed_obx())
        failed_menu.addAction("Price mismatches only", lambda: self._export_failed_obx("price_mismatch"))
        failed_menu.addAction("Unresolved articles only", lambda: self._export_failed_obx("unresolved"))
        self._failed_export_btn.setMenu(failed_menu)
        self._failed_export_btn.setEnabled(False)
        layout.addWidget(self._failed_export_btn)
        self._toggle_btn = QPushButton("Show errors only", container)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)
        self._toggle_btn.toggled.connect(self._on_toggle_all)
        self._toggle_btn.setEnabled(False)
        layout.addWidget(self._toggle_btn)
        layout.addStretch(1)
        return container

    def _build_progress_panel(self) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("obxProgressPanel")
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(theme.SPACE_2, theme.SPACE_1, theme.SPACE_2, theme.SPACE_1)
        layout.setSpacing(theme.SPACE_1)
        header = QHBoxLayout()
        header.setContentsMargins(0, theme.SPACE_1, 0, theme.SPACE_1)
        self._progress_state = QLabel("READY", panel)
        self._progress_state.setStyleSheet("font-weight: 600;")
        self._file_label = QLabel("No OBX file loaded.", panel)
        self._file_label.setStyleSheet(f"color: {theme.MUTED};")
        header.addWidget(self._progress_state)
        header.addWidget(self._file_label, 1)
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
        self._metrics: dict[str, QLabel] = {}
        metrics = [
            ("completed", "Completed"), ("matched", "Matched"),
            ("mismatch", "Price mismatch"), ("unresolved", "Unresolved"), ("skipped", "Skipped"),
            ("duplicate", "Duplicate"), ("elapsed", "Elapsed"), ("eta", "ETA"),
            ("speed", "Speed"), ("site", "PDM site"), ("recovery", "Recovery"),
        ("unique", "Unique"),
        ]
        grid = QGridLayout()
        grid.setHorizontalSpacing(theme.SPACE_2)
        grid.setVerticalSpacing(0)
        for index, (key, title) in enumerate(metrics):
            label = QLabel(f"{title}: -", panel)
            self._metrics[key] = label
            grid.addWidget(label, index // 6, index % 6)
        layout.addLayout(grid)
        panel.setMaximumHeight(160)
        return panel

    def _build_results(self) -> QWidget:
        container = QWidget(self)
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_1)
        self._table = QTableWidget(0, 9, container)
        self._table.setHorizontalHeaderLabels(["#", "SKU", "Currency", "Category (PLC)", "Qty", "OBX price", "PDM price", "Source date", "Result"])
        self._table.setSortingEnabled(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)
        return container

    def _on_load(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Load OBX file(s)", "", "OBX files (*.obx);;All files (*.*)")
        if paths:
            self._load_paths(paths)

    @staticmethod
    def _discover_obx_files(folder: str | Path) -> list[str]:
        """Return OBX files in a folder and all of its subfolders."""
        folder_path = Path(folder)
        if not folder_path.is_dir():
            return []
        return sorted(
            str(path)
            for path in folder_path.rglob("*")
            if path.is_file() and path.suffix.lower() == ".obx"
        )

    def _on_load_folder(self) -> None:
        # Directory selection is intentional: the user chooses the folder from
        # its parent/location and does not need to open it to see its contents.
        folder = QFileDialog.getExistingDirectory(
            self, "Select OBX folder (all subfolders included)"
        )
        if not folder:
            return
        paths = self._discover_obx_files(folder)
        if not paths:
            QMessageBox.information(
                self,
                "OBX Validation",
                "No .obx files found in the selected folder or its subfolders.",
            )
            return
        self._load_paths(paths)

    def _load_paths(self, paths: list[str]) -> None:
        svc = self._context.obx_validation_service
        currency, lines = "", []
        skipped_count = 0
        self._file_of_seq: dict[int, str] = {}
        self._currency_of_path: dict[str, str] = {}
        loaded_paths: list[str] = []
        recovered_files: list[str] = []
        for path in paths:
            try:
                text = Path(path).read_text(encoding="utf-8", errors="ignore")
            except OSError as exc:
                QMessageBox.warning(self, "OBX Validation", f"Could not read {path}:\n{exc}")
                continue
            try:
                cur, file_lines = svc.parse_obx(text)
            except (ET.ParseError, ValueError) as exc:
                QMessageBox.warning(
                    self,
                    "OBX Validation",
                    f"Could not parse {Path(path).name}:\n{exc}\n\n"
                    "The file appears incomplete or malformed XML.",
                )
                continue
            skipped_count += getattr(svc, "last_parse_skipped_count", 0)
            if getattr(svc, "last_parse_recovered", False):
                recovered_files.append(Path(path).name)
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
        if recovered_files:
            QMessageBox.warning(
                self,
                "OBX Validation",
                "Recovered all completed OBX articles from the following file(s):\n\n"
                + "\n".join(recovered_files)
                + "\n\nThe incomplete trailing portion was not loaded.",
            )
        label = Path(loaded_paths[0]).name if len(loaded_paths) == 1 else f"{len(loaded_paths)} OBX files"
        currencies = sorted({l.currency for l in lines if l.currency}) or [currency]
        self._file_label.setText(f"{label}  •  {len(lines)} lines  •  {', '.join(c or '?' for c in currencies)}")
        self._launch_btn.setEnabled(bool(lines))
        self._pause_btn.setEnabled(False)
        self._pause_btn.setText("Pause Validation")
        self._cancel_btn.setEnabled(False)
        self._pending_lines = []
        self._is_paused = False
        self._reset_results()
        self._save_session()
        self._offer_checkpoint_resume()

    def _on_launch(self) -> None:
        if self._lines:
            self._start_validation(self._lines, fresh=True)

    def _on_pause_resume(self) -> None:
        control = self._active_control
        if control is not None:
            if control.is_paused():
                return
            # Toggle a pending pause request. This keeps the same button usable:
            # Pause -> Resume can cancel the request before the next DB checkpoint.
            if self._pause_btn.text() == "Resume Validation":
                control.resume()
                if self._active_reporter is not None:
                    self._active_reporter.start_timer()
                self._pause_btn.setText("Pause Validation")
                self._progress_state.setText("VALIDATING")
            else:
                self._on_pause()
            return
        if self._pending_lines:
            self._on_resume()

    def _on_pause(self) -> None:
        control = self._active_control
        reporter = self._active_reporter
        if control is None or reporter is None:
            return
        control.pause()
        reporter.stop_timer()
        reporter.pause("Pause requested. The active SQL operation will finish, then validation will pause before the next DB operation.")
        self._pause_btn.setText("Resume Validation")
        self._pause_btn.setEnabled(True)
        self._progress_state.setText("PAUSING")

    def _on_resume(self) -> None:
        if self._pending_lines:
            self._start_validation(self._pending_lines, fresh=False)

    def _on_cancel(self) -> None:
        control = self._active_control
        if control is None:
            return
        control.cancel()
        if self._active_reporter is not None:
            self._active_reporter.stop_timer()
        self._cancel_btn.setEnabled(False)
        self._pause_btn.setEnabled(False)
        self._progress_state.setText("CANCELLING")

    def _start_validation(self, lines: list, fresh: bool) -> None:
        from core.progress import ProgressReporter
        reporter = ProgressReporter(self)
        control = ValidationControl()
        self._active_control = control
        self._active_reporter = reporter
        self._reporter = reporter
        reporter.progress_changed.connect(self._on_progress_changed)
        reporter.elapsed_changed.connect(self._on_elapsed_changed)
        reporter.remaining_changed.connect(self._on_remaining_changed)
        reporter.step_changed.connect(self._on_progress_step)
        if fresh:
            self._begin_live()
            self._validation_start_time = time.perf_counter()
            self._validation_elapsed_seconds = 0.0
        self._is_paused = False
        self._pause_btn.setText("Pause Validation")
        self._pause_btn.setEnabled(True)
        self._cancel_btn.setEnabled(True)
        self._launch_btn.setEnabled(False)
        self._export_btn.setEnabled(bool(self._results))
        self._failed_export_btn.setEnabled(bool(self._results))
        self._progress_state.setText("VALIDATING")
        self._dispatch_remaining = list(lines)
        self._dispatch_batch_remaining = []
        self._dispatch_sites = {}
        self._dispatch_workers = 0
        self._dispatch_total = len(lines)
        reporter.begin(max(len(self._lines), 1), title="Validate OBX", subject=f"{len(self._lines)} order line(s)")
        self._dispatch_memory_batch()

    @staticmethod
    def _memory_batch_size(total_lines: int) -> int:
        """Scale the outer feed batch with workload size.

        The worker layer remains fixed at 2 x 8 lines. This outer batch only
        limits how many lines are queued for the next set of worker rounds.
        """
        if total_lines <= 0:
            return 0
        worker_round = 2 * _ObxWorker._WORKER_SIZE
        rounds = max(1, math.ceil(math.sqrt(total_lines / worker_round)))
        return min(total_lines, worker_round * rounds)

    def _dispatch_memory_batch(self) -> None:
        if self._active_control is None:
            return
        if not self._dispatch_batch_remaining:
            if not self._dispatch_remaining:
                results = sorted(
                    self._results,
                    key=lambda result: self._seq_key(getattr(result, "seq", 0)),
                )
                self._on_results((self._dispatch_sites, results))
                return
            batch_size = self._memory_batch_size(self._dispatch_total)
            self._dispatch_batch_remaining = self._dispatch_remaining[:batch_size]
            self._reporter.note(
                f"Loaded feed batch of {len(self._dispatch_batch_remaining)} line(s)."
            )

        worker_round = self._dispatch_batch_remaining[: 2 * _ObxWorker._WORKER_SIZE]
        self._dispatch_workers = 0
        validation_date = self._validation_date.date().toString("dd-MMM-yyyy")
        chunks = [
            worker_round[index:index + _ObxWorker._WORKER_SIZE]
            for index in range(0, len(worker_round), _ObxWorker._WORKER_SIZE)
        ]
        self._progress_state.setText(
            f"VALIDATING — feed batch {len(self._dispatch_batch_remaining)} lines, workers 8 + 8"
        )

        for chunk in chunks[:2]:
            signals = _ObxSignals()
            signals.finished.connect(self._on_worker_finished)
            signals.failed.connect(self._on_failed)
            signals.paused.connect(self._on_paused)
            signals.cancelled.connect(self._on_cancelled)
            signals.recovery.connect(self._on_recovery)
            signals.line_done.connect(self._on_line_done)
            self._dispatch_workers += 1
            QThreadPool.globalInstance().start(
                _ObxWorker(
                    self._context.obx_validation_service,
                    self._currency,
                    chunk,
                    None,
                    validation_date,
                    self._active_reporter,
                    signals,
                    self._active_control,
                )
            )

    def _on_worker_finished(self, payload) -> None:
        sites, _results = payload
        self._dispatch_sites.update(sites or {})
        self._dispatch_workers -= 1
        if self._dispatch_workers > 0 or self._active_control is None:
            return

        completed_seqs = {
            getattr(result, "seq", None) for result in self._results
        }
        self._dispatch_batch_remaining = [
            line for line in self._dispatch_batch_remaining
            if getattr(line, "seq", None) not in completed_seqs
        ]
        if self._dispatch_batch_remaining:
            self._dispatch_memory_batch()
            return

        self._dispatch_remaining = [
            line for line in self._dispatch_remaining
            if getattr(line, "seq", None) not in completed_seqs
        ]
        self._dispatch_memory_batch()

    def _release_active_control(self) -> None:
        self._active_control = None
        self._active_reporter = None
        self._reporter = None
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
        # SIF/OBX pricing reports the exact currency group currently being sent
        # to PDM, e.g. "Pricing ... (site 12, EUR)...". Surface that in the UI
        # so a multi-currency folder cannot look like one currency is being used
        # for every file.
        if text.startswith("Pricing ") and "(" in text and "," in text:
            try:
                detail = text.rsplit("(", 1)[1].split(")", 1)[0]
                site_text, currency = [part.strip() for part in detail.split(",", 1)]
                if site_text.lower().startswith("site "):
                    self._set_metric("site", f"{currency} / {site_text[5:].strip()}")
                self._progress_state.setText(f"VALIDATING {currency}")
            except (IndexError, ValueError):
                pass
        if text.startswith("PDM connection lost.") and "attempt " in text:
            try:
                self._recovery_attempt = int(text.split("attempt ", 1)[1].split(")", 1)[0].rstrip("."))
            except (ValueError, IndexError):
                pass
            self._set_metric("recovery", str(self._recovery_attempt))

    def _on_recovery(self, payload) -> None:
        attempt, _maximum, message = payload
        self._recovery_attempt = attempt
        self._set_metric("recovery", str(attempt))
        QMessageBox.warning(self, "OBX Validation - Recovery", message)

    def _on_failed(self, message: str) -> None:
        self._finalize_validation_elapsed()
        self._release_active_control()
        self._pause_btn.setText("Pause Validation")
        self._launch_btn.setEnabled(bool(self._lines))
        self._save_session()
        self._write_checkpoint()
        self._progress_state.setText("FAILED")
        QMessageBox.warning(self, "OBX Validation", f"Validation failed:\n{message}")

    def _on_cancelled(self, message: str) -> None:
        self._finalize_validation_elapsed()
        self._release_active_control()
        self._pending_lines = []
        self._is_paused = False
        self._pause_btn.setText("Pause Validation")
        self._launch_btn.setEnabled(bool(self._lines))
        self._delete_checkpoint()
        self._progress_state.setText("CANCELLED")

    def _on_paused(self, payload) -> None:
        self._finalize_validation_elapsed()
        sites, remaining_lines, reason = payload
        self._release_active_control()
        self._pending_lines = list(remaining_lines)
        self._is_paused = True
        self._save_session()
        self._write_checkpoint()
        self._launch_btn.setEnabled(False)
        self._pause_btn.setText("Resume Validation")
        self._pause_btn.setEnabled(bool(self._pending_lines))
        self._progress_state.setText("PAUSED")
        self._set_metric("completed", f"{len(self._results)}/{len(self._lines)}")
        self._set_metric("skipped", str(self._skipped_count))
        self._set_metric("duplicate", str(self._duplicate_count))
        self._export_btn.setEnabled(bool(self._results))
        self._failed_export_btn.setEnabled(bool(self._results))
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
        self._recovery_attempt = 0
        for key in ("completed", "matched", "mismatch", "unresolved", "elapsed", "eta", "speed", "site", "unique"):
            self._set_metric(key, "0" if key in {"completed", "matched", "mismatch", "unresolved"} else "-")
        self._set_metric("completed", f"0/{len(self._lines)}")
        self._set_metric("skipped", str(self._skipped_count))
        self._set_metric("duplicate", str(self._duplicate_count))
        self._set_metric("unique", str(max(0, len(self._lines) - self._duplicate_count)))
        self._set_metric("recovery", "0")
        self._toggle_btn.setEnabled(True)
        self._export_btn.setEnabled(False)

    def _on_line_done(self, r) -> None:
        self._results.append(r)
        self._export_btn.setEnabled(True)
        self._failed_export_btn.setEnabled(True)
        self._live["lines"] += 1
        key = "ok" if r.status == "ok" else ("mismatch" if r.status == "price_mismatch" else "unresolved")
        self._live[key] += 1
        completed = self._live["lines"]
        self._set_metric("completed", f"{completed}/{len(self._lines)}")
        self._set_metric("matched", str(self._live["ok"]))
        self._set_metric("mismatch", str(self._live["mismatch"]))
        self._set_metric("unresolved", str(self._live["unresolved"]))
        self._set_metric("skipped", str(self._skipped_count))
        self._set_metric("duplicate", str(self._duplicate_count))
        if self._show_all or r.status != "ok":
            self._append_row(r)
        if self._live["lines"] - self._last_checkpoint_count >= 100:
            self._save_session()
            self._write_checkpoint()
            self._last_checkpoint_count = self._live["lines"]

    def _on_results(self, payload) -> None:
        self._finalize_validation_elapsed()
        sites, results = payload
        self._release_active_control()
        self._pause_btn.setText("Pause Validation")
        self._results = results
        self._pending_lines = []
        self._save_session()
        self._is_paused = False
        self._launch_btn.setEnabled(bool(self._lines))
        self._pause_btn.setEnabled(False)
        ok = sum(1 for r in results if r.status == "ok")
        mism = sum(1 for r in results if r.status == "price_mismatch")
        unres = sum(1 for r in results if r.status == "unresolved")
        self._set_metric("completed", f"{len(results)}/{len(self._lines)}")
        self._set_metric("matched", str(ok))
        self._set_metric("mismatch", str(mism))
        self._set_metric("unresolved", str(unres))
        self._set_metric("skipped", str(self._skipped_count))
        self._set_metric("duplicate", str(self._duplicate_count))
        self._set_metric("eta", "0:00")
        self._set_metric("recovery", str(self._recovery_attempt))
        self._set_site_metrics(sites)
        self._delete_checkpoint()
        self._progress_state.setText("COMPLETE")
        self._progress_bar.setValue(100)
        self._progress_percent.setText("100%")
        self._toggle_btn.setEnabled(True)
        self._export_btn.setEnabled(bool(results))
        self._failed_export_btn.setEnabled(bool(results))
        self._render_table()

        # Automatic consolidated export happens only after the worker reports
        # the complete validation result. Paused/partial results are not exported
        # as the consolidated report.
        self._export_consolidated()
        site_text = ", ".join(f"{cur}→site {s}" for cur, s in sites.items())
        if mism == 0 and unres == 0:
            QMessageBox.information(self, "OBX Validation", f"All {len(results)} line(s) match PDM ({site_text}).")

    def _on_toggle_all(self, checked: bool) -> None:
        self._show_all = checked
        self._toggle_btn.setText("Show errors only" if checked else "Show all lines")
        self._render_table()

    def _export_consolidated(self) -> bool:
        """Write one consolidated CSV after the complete validation finishes."""
        results = sorted(list(self._results), key=lambda r: self._seq_key(getattr(r, "seq", 0)))
        paths = getattr(self, "_paths", [])
        if not results or not paths:
            return False

        target = Path(paths[0]).parent / "OBX_Validation_Consolidated.csv"
        try:
            self._context.obx_validation_service.export_csv(
                str(target),
                self._currency,
                results,
                elapsed_seconds=self._validation_elapsed_seconds,
            )
        except OSError as exc:
            QMessageBox.warning(
                self,
                "OBX Validation",
                f"Validation completed, but the consolidated CSV could not be written:\n{exc}",
            )
            return False

        self._progress_state.setText("COMPLETE — CSV EXPORTED")
        return True

    def _on_export(self) -> None:
        """Export each loaded source OBX to its own CSV on explicit request."""
        results = list(self._results)
        if not results:
            return
        paths = getattr(self, "_paths", [])
        if not paths:
            return

        svc = self._context.obx_validation_service
        file_of_seq = getattr(self, "_file_of_seq", {})
        cur_of_path = getattr(self, "_currency_of_path", {})
        written, failed = 0, []

        for src in paths:
            rows = sorted(
                (r for r in results if file_of_seq.get(r.seq) == src),
                key=lambda r: r.seq,
            )
            if not rows:
                continue
            target = Path(src).with_suffix(".csv")
            try:
                svc.export_csv(
                    str(target),
                    cur_of_path.get(src, self._currency),
                    rows,
                    elapsed_seconds=self._current_validation_elapsed(),
                )
                written += 1
            except OSError as exc:
                failed.append(f"{Path(src).name}: {exc}")

        if failed:
            QMessageBox.warning(
                self,
                "OBX Validation",
                f"Exported {written} report(s). Failed:\n" + "\n".join(failed),
            )
        else:
            state = "current results" if self._active_control is not None else "validation report"
            QMessageBox.information(
                self,
                "OBX Validation",
                f"Exported {written} {state} beside the source OBX file(s).",
            )

    def _export_failed_obx(self, status: str | None = None) -> None:
        """Write failed source articles back to filtered OBX files.

        Exports are kept per source file so a multi-file validation run can be
        corrected and revalidated without mixing unrelated OBX documents.
        """
        results = [
            result for result in self._results
            if result.status != "ok" and (status is None or result.status == status)
        ]
        if not results:
            label = "failed" if status is None else status.replace("_", " ")
            QMessageBox.information(
                self, "OBX Validation", f"No {label} articles are available to export."
            )
            return

        line_by_seq = {line.seq: line for line in self._lines}
        paths = getattr(self, "_paths", [])
        svc = self._context.obx_validation_service
        written = 0
        total = 0
        failures: list[str] = []

        for src in paths:
            source_results = [r for r in results if self._file_of_seq.get(r.seq) == src]
            if not source_results:
                continue
            selected_lines = [
                line_by_seq[r.seq] for r in source_results
                if r.seq in line_by_seq and line_by_seq[r.seq].source_index >= 0
            ]
            if not selected_lines:
                continue

            suffix = {
                None: "Failed",
                "price_mismatch": "Price_Mismatch",
                "unresolved": "Unresolved",
            }.get(status, "Failed")
            target = Path(src).with_name(f"{Path(src).stem}_{suffix}.obx")
            try:
                count = svc.export_filtered_obx(str(src), selected_lines, str(target))
                if count:
                    written += 1
                    total += count
            except (OSError, ET.ParseError, ValueError) as exc:
                failures.append(f"{Path(src).name}: {exc}")

        if failures:
            QMessageBox.warning(
                self,
                "OBX Validation",
                f"Exported {total} article(s) in {written} file(s).\n\nFailed:\n"
                + "\n".join(failures),
            )
        else:
            label = "failed" if status is None else status.replace("_", " ")
            QMessageBox.information(
                self,
                "OBX Validation",
                f"Exported {total} {label} article(s) in {written} filtered OBX file(s) beside the source files.",
            )

    def _checkpoint_path(self) -> Path | None:
        paths = getattr(self, "_paths", [])
        if not paths:
            return None
        digest = hashlib.sha1("|".join(str(Path(p).resolve()) for p in paths).encode()).hexdigest()[:12]
        return Path(paths[0]).parent / f".obx_validation_{digest}.checkpoint.json"

    def _write_checkpoint(self) -> None:
        path = self._checkpoint_path()
        if path is None or not self._results:
            return
        payload = {
            "version": 1,
            "paths": [str(Path(p).resolve()) for p in getattr(self, "_paths", [])],
            "files": [
                {"path": str(Path(p).resolve()), "size": Path(p).stat().st_size, "mtime_ns": Path(p).stat().st_mtime_ns}
                for p in getattr(self, "_paths", []) if Path(p).is_file()
            ],
            "validation_date": self._validation_date.date().toString("dd-MMM-yyyy"),
            "elapsed_seconds": self._current_validation_elapsed(),
            "results": [r.__dict__ for r in self._results],
        }
        try:
            path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        except OSError:
            pass

    def _delete_checkpoint(self) -> None:
        path = self._checkpoint_path()
        if path is None:
            return
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    def _offer_checkpoint_resume(self) -> None:
        path = self._checkpoint_path()
        if path is None or not path.is_file():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            expected = [str(Path(p).resolve()) for p in getattr(self, "_paths", [])]
            if payload.get("paths") != expected:
                return
            for item in payload.get("files", []):
                source = Path(item["path"])
                stat = source.stat()
                if stat.st_size != item["size"] or stat.st_mtime_ns != item["mtime_ns"]:
                    return
            data = payload.get("results", [])
        except (OSError, ValueError, TypeError, KeyError):
            return
        if not data:
            return
        answer = QMessageBox.question(
            self, "Resume OBX Validation",
            f"An interrupted validation checkpoint contains {len(data)} completed line(s).\n\nResume the remaining articles?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            self._delete_checkpoint()
            return
        from services.sif_validation_service import SifResult
        self._results = [SifResult(**item) for item in data]
        completed = {r.seq for r in self._results}
        self._pending_lines = [line for line in self._lines if line.seq not in completed]
        self._validation_elapsed_seconds = float(payload.get("elapsed_seconds", 0.0) or 0.0)
        self._render_table()
        self._set_metric("completed", f"{len(self._results)}/{len(self._lines)}")
        self._set_metric("matched", str(sum(r.status == "ok" for r in self._results)))
        self._set_metric("mismatch", str(sum(r.status == "price_mismatch" for r in self._results)))
        self._set_metric("unresolved", str(sum(r.status == "unresolved" for r in self._results)))
        self._set_metric("elapsed", self._format_duration(int(self._validation_elapsed_seconds)))
        self._set_metric("skipped", str(self._skipped_count))
        self._set_metric("duplicate", str(self._duplicate_count))
        self._export_btn.setEnabled(True)
        self._failed_export_btn.setEnabled(True)
        if self._pending_lines:
            self._start_validation(self._pending_lines, fresh=False)
        else:
            self._delete_checkpoint()

    def _save_session(self) -> None:
        session = self._session
        session.update({
            "currency": self._currency,
            "lines": self._lines,
            "results": self._results,
            "pending_lines": self._pending_lines,
            "paths": list(getattr(self, "_paths", [])),
            "source_path": self._source_path,
            "file_of_seq": dict(getattr(self, "_file_of_seq", {})),
            "currency_of_path": dict(getattr(self, "_currency_of_path", {})),
            "skipped_count": self._skipped_count,
            "duplicate_count": self._duplicate_count,
            "is_paused": self._is_paused,
            "validation_elapsed_seconds": self._validation_elapsed_seconds,
        })

    def _restore_session(self) -> None:
        session = self._session
        if not session.get("lines"):
            return
        self._currency = session.get("currency", "")
        self._lines = list(session.get("lines", []))
        self._results = list(session.get("results", []))
        self._pending_lines = list(session.get("pending_lines", []))
        self._paths = list(session.get("paths", []))
        self._source_path = session.get("source_path", "")
        self._file_of_seq = dict(session.get("file_of_seq", {}))
        self._currency_of_path = dict(session.get("currency_of_path", {}))
        self._skipped_count = int(session.get("skipped_count", 0))
        self._duplicate_count = int(session.get("duplicate_count", 0))
        self._is_paused = bool(session.get("is_paused", False))
        self._validation_elapsed_seconds = float(session.get("validation_elapsed_seconds", 0.0))
        self._render_table()

    def refresh(self) -> None:
        self._restore_session()

    def _reset_results(self) -> None:
        self._validation_start_time = 0.0
        self._validation_elapsed_seconds = 0.0
        self._last_checkpoint_count = 0
        self._results = []
        self._pending_lines = []
        self._is_paused = False
        self._table.setRowCount(0)
        self._progress_state.setText("READY")
        self._progress_bar.setValue(0)
        self._progress_percent.setText("0%")
        for key in ("completed", "matched", "mismatch", "unresolved", "elapsed", "eta", "speed", "site", "recovery"):
            self._set_metric(key, "-")
        self._set_metric("skipped", str(self._skipped_count))
        self._set_metric("duplicate", str(self._duplicate_count))
        self._toggle_btn.setChecked(True)
        self._toggle_btn.setEnabled(False)
        self._export_btn.setEnabled(False)
        self._failed_export_btn.setEnabled(False)
        self._pause_btn.setEnabled(False)
        self._pause_btn.setText("Pause Validation")
        self._cancel_btn.setEnabled(False)

    def _current_validation_elapsed(self) -> float:
        if self._validation_start_time <= 0:
            return self._validation_elapsed_seconds
        return max(
            self._validation_elapsed_seconds,
            time.perf_counter() - self._validation_start_time,
        )

    def _finalize_validation_elapsed(self) -> None:
        self._validation_elapsed_seconds = self._current_validation_elapsed()

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
            str(r.seq),
            r.sku,
            getattr(r, "currency", "") or "-",
            r.plc,
            str(r.qty),
            f"{r.sif_price:.2f}",
            "-" if r.pdm_price is None else f"{r.pdm_price:.2f}",
            r.source_date or "-",
            r.result,
        ]
        for col, text in enumerate(cells):
            cell = QTableWidgetItem(text)
            if col in (0, 4, 5, 6):
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if r.status != "ok":
                cell.setForeground(Qt.GlobalColor.red)
            self._table.setItem(row, col, cell)
