"""Generate workspace page.

Final engineering output stage. Produces a read-only, dry-run generation
summary, preview, and logs from the active snapshot - it writes nothing and is
the future integration point for MDB generation.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.pages.base_page import BasePage


class GeneratePage(BasePage):
    """Dry-run generation summary and preview."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Generate",
            description="Final engineering output (dry run - no files are written yet).",
            parent=parent,
            show_placeholder=False,
        )
        self._context = context
        self._last_result = None  # cached generate() output; reused by is_ready()

        self.add_content(self._build_toolbar())
        self.add_content(self._build_main_row())
        self.add_content(self._build_status_group())
        self.refresh()

    def _build_toolbar(self) -> QWidget:
        box = QGroupBox("Toolbar", self)
        layout = QHBoxLayout(box)
        self._run_btn = QPushButton("Run Dry-Run Generation", box)
        self._run_btn.clicked.connect(self.refresh)
        layout.addWidget(self._run_btn)
        layout.addStretch(1)
        return box

    def _build_main_row(self) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        preview_box = QGroupBox("Output Preview", row)
        pv = QVBoxLayout(preview_box)
        self._preview = QPlainTextEdit(preview_box)
        self._preview.setReadOnly(True)
        pv.addWidget(self._preview)
        layout.addWidget(preview_box, 2)

        logs_box = QGroupBox("Generation Logs", row)
        lv = QVBoxLayout(logs_box)
        self._logs = QListWidget(logs_box)
        lv.addWidget(self._logs)
        layout.addWidget(logs_box, 1)
        return row

    def _build_status_group(self) -> QWidget:
        box = QGroupBox("Generation Status", self)
        form = QFormLayout(box)
        self._result = QLabel("-", box)
        self._export_status = QLabel("-", box)
        self._export_status.setWordWrap(True)
        self._summary = QLabel("-", box)
        self._summary.setWordWrap(True)
        form.addRow("Result:", self._result)
        form.addRow("Export Status:", self._export_status)
        form.addRow("Summary:", self._summary)
        return box

    # -- refresh -----------------------------------------------------------
    def refresh(self) -> None:
        result = self._context.export_service.generate()
        self._last_result = result
        self._preview.setPlainText(result.preview or "(nothing to preview)")
        self._logs.clear()
        self._logs.addItems(result.logs or ["(no logs)"])
        self._result.setText("SUCCESS" if result.success else "NOT READY")
        self._export_status.setText(result.export_status or "-")
        self._summary.setText("\n".join(result.summary) if result.summary else "-")

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def is_ready(self) -> bool:
        # Reuse the last refresh() output; refresh() always runs before readiness
        # is polled, so this avoids a second full generate() per readiness check.
        result = self._last_result
        if result is None:
            result = self._context.export_service.generate()
            self._last_result = result
        return result.success
