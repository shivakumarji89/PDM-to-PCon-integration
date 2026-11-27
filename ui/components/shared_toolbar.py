"""Shared toolbar shell for ProductStudio workflow pages.

Pages supply workflow-specific controls; this component owns the common
container, spacing, sizing and presentation metrics. Metrics mirror Articles.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy, QWidget
from ui import theme


class SharedToolbar(QFrame):
    """Standard toolbar surface; controls and callbacks remain page-owned."""

    SHELL_MARGINS = (theme.SPACE_3, 6, theme.SPACE_3, 6)
    CONTROL_SPACING = theme.SPACE_2
    GROUP_SPACING = theme.SPACE_2

    def __init__(self, parent: QWidget | None = None, *, title: str = "") -> None:
        super().__init__(parent)
        self.setObjectName("wfShellToolbar")
        self.setStyleSheet(
            f"QFrame#wfShellToolbar {{ background: {theme.WB_SURFACE}; "
            f"border: 1px solid {theme.WB_BORDER}; border-radius: {theme.RADIUS_LG}px; }} "
            "QLabel, QCheckBox { background: transparent; } "
            f"QCheckBox::indicator {{ width: 16px; height: 16px; "
            f"border: 1px solid {theme.LINE_STRONG}; border-radius: 4px; "
            f"background: {theme.WB_SURFACE}; }} "
            f"QCheckBox::indicator:checked {{ background: {theme.WB_GREEN}; "
            f"border-color: {theme.WB_GREEN}; }}"
        )
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(*self.SHELL_MARGINS)
        self._layout.setSpacing(self.CONTROL_SPACING)

    @property
    def controls_layout(self) -> QHBoxLayout:
        return self._layout

    def add_group(self, *widgets: QWidget, divider: bool = False) -> QWidget:
        """Create a transparent compact group, optionally separated by a divider."""
        host = QWidget(self)
        host.setObjectName("wfToolbarGroup")
        host.setStyleSheet(
            "QWidget#wfToolbarGroup { background: transparent; "
            + (f"border-left: 1px solid {theme.WB_DIVIDER}; " if divider else "")
            + "}"
        )
        group_layout = QHBoxLayout(host)
        group_layout.setContentsMargins(theme.SPACE_3 if divider else 0, 0, 0, 0)
        group_layout.setSpacing(self.GROUP_SPACING)
        for widget in widgets:
            group_layout.addWidget(widget)
        self._layout.addWidget(host)
        return host


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
