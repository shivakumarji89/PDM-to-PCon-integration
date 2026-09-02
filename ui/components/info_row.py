"""Design-system component: InfoRow.

A single-line ``label ......... value`` row for compact detail lists. Provided
for reuse across the design system; note that stacked :class:`~ui.components.
metric.MetricTile`s are preferred for prominent values.
"""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ui import theme
from ui.components._styles import label_color_qss


class InfoRow(QWidget):
    """A quiet label on the left and a value on the right."""

    def __init__(
        self, label: str = "", value: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_2)

        self._label = QLabel(label, self)
        self._label.setFont(theme.font("helper"))
        self._label.setStyleSheet(label_color_qss(theme.MUTED))
        layout.addWidget(self._label)

        layout.addStretch(1)

        self._value = QLabel(value, self)
        self._value.setFont(theme.font("normal"))
        self._value.setStyleSheet(label_color_qss(theme.INK))
        layout.addWidget(self._value)

    def set_value(self, value: str) -> None:
        self._value.setText(value or "-")
