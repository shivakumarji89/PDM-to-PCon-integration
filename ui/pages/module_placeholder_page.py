"""Placeholder workspace for modules whose workflows are not configured yet."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from core.modules import WorkbenchModule, module_title
from ui import theme
from ui.components._styles import secondary_button_qss


class ModulePlaceholderPage(QWidget):
    """Simple Level-2 shell for a module without registered workflows."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("modulePlaceholderPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.SPACE_6, theme.SPACE_6, theme.SPACE_6, theme.SPACE_6)
        layout.setSpacing(theme.SPACE_3)

        self._title = QLabel("", self)
        self._title.setFont(theme.font("workspace_title"))
        layout.addWidget(self._title)

        self._message = QLabel("", self)
        self._message.setFont(theme.font("subtitle"))
        self._message.setWordWrap(True)
        layout.addWidget(self._message)

        layout.addSpacing(theme.SPACE_3)
        self.back_button = QPushButton("← Back to Modules", self)
        self.back_button.setObjectName("backToModulesButton")
        self.back_button.setStyleSheet(secondary_button_qss("backToModulesButton"))
        layout.addWidget(self.back_button, 0)
        layout.addStretch(1)

    def set_module(self, module: WorkbenchModule) -> None:
        self._title.setText(module_title(module))
        self._message.setText(
            "No workflow is registered for this module yet. "
            "The module shell is ready for its workflow tools."
        )
