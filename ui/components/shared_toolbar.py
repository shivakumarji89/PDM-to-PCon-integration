"""Shared toolbar shell for ProductStudio workflow pages.

Pages supply workflow-specific controls; this component owns the common
container, spacing, sizing and presentation metrics.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy, QWidget
from ui import theme


class SharedToolbar(QFrame):
    """Standard toolbar surface; controls and callbacks remain page-owned."""

    def __init__(self, parent: QWidget | None = None, *, title: str = "") -> None:
        super().__init__(parent)
        self.setObjectName("wfShellToolbar")
        self.setStyleSheet(f"QFrame#wfShellToolbar {{ background: {theme.WB_SURFACE}; border: 1px solid {theme.WB_BORDER}; border-radius: {theme.RADIUS_LG}px; }} QLabel, QCheckBox {{ background: transparent; }}")
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(
            theme.SPACE_3, 6, theme.SPACE_3, 6,
        )
        self._layout.setSpacing(theme.SPACE_2)

    @property
    def controls_layout(self) -> QHBoxLayout:
        return self._layout


class SharedSourceToolbarRow(QWidget):
    """Uniform source-tab and workflow-control row used by ProductStudio pages."""

    def __init__(self, source_tabs: QWidget, toolbar: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sharedSourceToolbarRow")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.SECTION_SPACING)
        row.addWidget(source_tabs)
        row.addStretch(1)
        row.addWidget(toolbar)
