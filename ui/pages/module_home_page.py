"""Level-1 module home for MK Product Workbench."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.modules import MODULE_ITEMS, WorkbenchModule
from ui import theme
from ui.components._styles import card_qss, label_color_qss, primary_button_qss


class ModuleHomePage(QWidget):
    """Landing screen that exposes the top-level workbench modules.

    The module cards intentionally reuse the same visual structure as the
    workflow/tool cards used inside the existing workspaces: heading + action
    on the top row and supporting description below.
    """

    module_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("moduleHomePage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            theme.SPACE_6,
            theme.SPACE_6,
            theme.SPACE_6,
            theme.SPACE_6,
        )
        layout.setSpacing(theme.SECTION_SPACING)

        title = QLabel("MK Product Workbench", self)
        title.setObjectName("pageTitle")
        title.setFont(theme.font("workspace_title"))
        layout.addWidget(title)

        subtitle = QLabel("Select a module to continue.", self)
        subtitle.setObjectName("pageSubtitle")
        subtitle.setFont(theme.font("subtitle"))
        layout.addWidget(subtitle)

        divider = QFrame(self)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("pageDivider")
        layout.addWidget(divider)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(theme.SPACE_2)
        grid.setVerticalSpacing(theme.SPACE_2)

        for index, item in enumerate(MODULE_ITEMS):
            grid.addWidget(self._module_card(item.module, item.title, item.description), index // 2, index % 2)

        layout.addLayout(grid)
        layout.addStretch(1)

    def _module_card(
        self,
        module: WorkbenchModule,
        title: str,
        description: str,
    ) -> QWidget:
        """Build a module card using the same pattern as workspace tool cards."""
        card = QFrame(self)
        card.setObjectName("moduleCard")
        card.setStyleSheet(card_qss("moduleCard"))
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
        )

        inner = QVBoxLayout(card)
        inner.setContentsMargins(
            theme.SPACE_3,
            theme.SPACE_3,
            theme.SPACE_3,
            theme.SPACE_3,
        )
        inner.setSpacing(theme.SPACE_1)

        heading = QLabel(title, card)
        heading.setFont(theme.font("section_header"))
        heading.setStyleSheet(label_color_qss(theme.INK))

        button = QPushButton("Open", card)
        button.setObjectName(f"moduleCardButton_{module.value}")
        button.setStyleSheet(primary_button_qss(button.objectName()))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(
            lambda checked=False, selected=module: self.module_selected.emit(selected)
        )

        top = QHBoxLayout()
        top.setSpacing(theme.SPACE_2)
        top.addWidget(heading, 1)
        top.addWidget(button, 0, Qt.AlignmentFlag.AlignTop)
        inner.addLayout(top)

        caption = QLabel(description, card)
        caption.setFont(theme.font("helper"))
        caption.setStyleSheet(label_color_qss(theme.MUTED))
        caption.setWordWrap(True)
        inner.addWidget(caption)

        return card
