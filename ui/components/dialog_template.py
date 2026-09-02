"""Design-system template: DialogTemplate.

The standard modern dialog skeleton - Header / Content / Footer - that every
MK Product Workbench dialog composes. Subclasses add cards to the content and
buttons to the footer; they never set pixel values or colours directly.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.components._styles import dialog_qss, divider_qss, label_color_qss


class DialogTemplate(QDialog):
    """A Header / Content / Footer dialog skeleton driven by design tokens."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dialogTemplate")
        self.setModal(True)
        self.setStyleSheet(dialog_qss("dialogTemplate"))
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            theme.SPACE_5, theme.SPACE_4, theme.SPACE_5, theme.SPACE_4
        )
        root.setSpacing(theme.SPACE_3)

        # Header: title + trailing slot.
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self._title = QLabel("", self)
        self._title.setFont(theme.font("dialog_title"))
        self._title.setStyleSheet(label_color_qss(theme.INK))
        header.addWidget(self._title)
        header.addStretch(1)
        self._trailing = QHBoxLayout()
        self._trailing.setContentsMargins(0, 0, 0, 0)
        header.addLayout(self._trailing)
        root.addLayout(header)

        root.addWidget(self._divider())

        # Content.
        self._content_layout = QVBoxLayout()
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(theme.SPACE_3)
        root.addLayout(self._content_layout)

        root.addWidget(self._divider())

        # Footer: right-aligned actions.
        self._footer_layout = QHBoxLayout()
        self._footer_layout.setContentsMargins(0, 0, 0, 0)
        self._footer_layout.setSpacing(theme.SPACE_2)
        self._footer_layout.addStretch(1)
        root.addLayout(self._footer_layout)

    # -- header ------------------------------------------------------------
    def set_title(self, text: str) -> None:
        self._title.setText(text)
        self.setWindowTitle(text)

    def set_header_trailing(self, widget: QWidget) -> None:
        self._trailing.addWidget(widget)

    # -- content -----------------------------------------------------------
    def add_content(self, widget: QWidget) -> None:
        self._content_layout.addWidget(widget)

    def add_content_layout(self, layout: QLayout) -> None:
        self._content_layout.addLayout(layout)

    # -- footer ------------------------------------------------------------
    def add_footer_button(self, button: QPushButton) -> None:
        self._footer_layout.addWidget(button)

    # -- internals ---------------------------------------------------------
    def _divider(self) -> QFrame:
        line = QFrame(self)
        line.setObjectName("dialogDivider")
        line.setFixedHeight(1)
        line.setStyleSheet(divider_qss("dialogDivider"))
        return line
