"""Design-system component: SectionHeader.

A small heading with an optional subtitle, used to title sections in pages,
dialogs and dock panels. Token-driven and reusable.
"""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ui import theme
from ui.components._styles import label_color_qss


class SectionHeader(QWidget):
    """A titled section header with an optional subtitle."""

    def __init__(
        self, title: str = "", subtitle: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_1)

        self._title = QLabel(title, self)
        self._title.setFont(theme.font("section_header"))
        self._title.setStyleSheet(label_color_qss(theme.INK))
        layout.addWidget(self._title)

        self._subtitle = QLabel(subtitle, self)
        self._subtitle.setFont(theme.font("helper"))
        self._subtitle.setStyleSheet(label_color_qss(theme.MUTED))
        self._subtitle.setWordWrap(True)
        self._subtitle.setVisible(bool(subtitle))
        layout.addWidget(self._subtitle)

    def set_title(self, text: str) -> None:
        self._title.setText(text)

    def set_subtitle(self, text: str) -> None:
        self._subtitle.setText(text)
        self._subtitle.setVisible(bool(text))
