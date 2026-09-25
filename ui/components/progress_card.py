"""Design-system component: ProgressCard.

A card presenting a thick modern progress bar with a prominent stage line and
the current operation. Token-driven and reusable by dialogs, panels and pages.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout, QWidget

from ui import theme
from ui.components._styles import card_qss, label_color_qss, progressbar_qss


class ProgressCard(QFrame):
    """A modern progress surface: bar + stage + current operation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("progressCard")
        self.setStyleSheet(card_qss("progressCard"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            theme.SPACE_3, theme.SPACE_3, theme.SPACE_3, theme.SPACE_3
        )
        layout.setSpacing(theme.SPACE_2)

        self._bar = QProgressBar(self)
        self._bar.setObjectName("progressCardBar")
        self._bar.setStyleSheet(progressbar_qss("progressCardBar"))
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(theme.PROGRESS_H)
        layout.addWidget(self._bar)

        self._stage = QLabel("", self)
        self._stage.setFont(theme.font("metric_label"))
        self._stage.setStyleSheet(label_color_qss(theme.MUTED))
        self._stage.setVisible(False)
        layout.addWidget(self._stage)

        self._operation = QLabel("-", self)
        self._operation.setFont(theme.font("card_title"))
        self._operation.setStyleSheet(label_color_qss(theme.INK))
        # Single line so a changing step never resizes the dialog (no jumping).
        self._operation.setWordWrap(False)
        layout.addWidget(self._operation)

    def set_progress(self, percent: int) -> None:
        if self._bar.maximum() == 0:
            self._bar.setRange(0, 100)
        self._bar.setValue(max(0, min(100, int(percent))))

    def set_indeterminate(self, busy: bool) -> None:
        self._bar.setRange(0, 0) if busy else self._bar.setRange(0, 100)

    def set_stage(self, text: str) -> None:
        self._stage.setText(text)
        self._stage.setVisible(bool(text))

    def set_operation(self, text: str) -> None:
        self._operation.setText(text or "-")
