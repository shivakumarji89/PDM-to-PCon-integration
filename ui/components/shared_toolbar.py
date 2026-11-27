"""Shared toolbar shell for ProductStudio workflow pages.

Pages supply workflow-specific controls; this component owns the common
container, spacing, sizing and presentation metrics.
"""
from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QSizePolicy, QWidget
from ui import theme


class SharedToolbar(QGroupBox):
    """Standard toolbar surface; controls and callbacks remain page-owned."""

    def __init__(self, parent: QWidget | None = None, *, title: str = "") -> None:
        super().__init__(title, parent)
        self.setObjectName("sharedWorkflowToolbar")
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(
            theme.GROUP_PADDING, theme.GROUP_PADDING,
            theme.GROUP_PADDING, theme.GROUP_PADDING,
        )
        self._layout.setSpacing(theme.CONTROL_SPACING)

    @property
    def controls_layout(self) -> QHBoxLayout:
        return self._layout
