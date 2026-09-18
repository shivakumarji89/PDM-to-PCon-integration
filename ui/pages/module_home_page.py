"""Level-1 module home for MK Product Workbench."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from core.modules import MODULE_ITEMS, WorkbenchModule
from ui import theme
from ui.components._styles import card_qss, primary_button_qss


class ModuleHomePage(QWidget):
    """Landing screen that exposes only the top-level workbench modules."""

    module_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("moduleHomePage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.SPACE_6, theme.SPACE_6, theme.SPACE_6, theme.SPACE_6)
        layout.setSpacing(theme.SPACE_2)

        title = QLabel("MK Product Workbench", self)
        title.setFont(theme.font("app_title"))
        title.setObjectName("moduleHomeTitle")
        layout.addWidget(title)

        subtitle = QLabel("Select a module to continue", self)
        subtitle.setFont(theme.font("subtitle"))
        subtitle.setObjectName("moduleHomeSubtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(theme.SPACE_4)

        grid = QGridLayout()
        grid.setHorizontalSpacing(theme.SPACE_4)
        grid.setVerticalSpacing(theme.SPACE_4)

        for index, item in enumerate(MODULE_ITEMS):
            card = QFrame(self)
            card.setObjectName("moduleCard")
            card.setStyleSheet(card_qss("moduleCard"))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(theme.SPACE_5, theme.SPACE_5, theme.SPACE_5, theme.SPACE_5)
            card_layout.setSpacing(theme.SPACE_2)

            button = QPushButton(item.title, card)
            button.setObjectName("moduleCardButton")
            button.setMinimumHeight(52)
            button.setFont(theme.font("card_title"))
            button.setStyleSheet(primary_button_qss("moduleCardButton"))
            button.clicked.connect(
                lambda checked=False, module=item.module: self.module_selected.emit(module)
            )
            card_layout.addWidget(button)

            description = QLabel(item.description, card)
            description.setObjectName("moduleCardDescription")
            description.setWordWrap(True)
            description.setFont(theme.font("subtitle"))
            card_layout.addWidget(description)
            card_layout.addStretch(1)

            row, column = divmod(index, 2)
            grid.addWidget(card, row, column)

        layout.addLayout(grid)
        layout.addStretch(1)

        hint = QLabel("The selected module opens its existing workflow tools.", self)
        hint.setObjectName("moduleHomeHint")
        hint.setFont(theme.font("helper"))
        layout.addWidget(hint)
