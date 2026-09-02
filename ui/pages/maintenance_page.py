"""Maintenance workspace page - a launcher for the post-publish tools.

Each tool opens in its own pop-up so the page stays clear for at-a-glance
repository statistics. Tools: **Bulk Price Update** (price-list roll-over),
**Check Base Lengths** (vs PDM CAD Maintenance) and **Update Version** (OCD +
ODB export version).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.components import SectionHeader, StatisticsGrid
from ui.components._styles import card_qss, label_color_qss, primary_button_qss
from ui.pages.base_page import BasePage

#: The published-product workspaces the tools default to (both scanned together,
#: ``;``-separated); the non-product-folder guard keeps templates/backups out.
_DEFAULT_REPOS = [
    r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\WS\Seating\Seating",
    r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\WS\Tables\Tables",
]


class MaintenancePage(BasePage):
    """Launch the post-publish maintenance tools; each runs in a pop-up."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Maintenance",
            description="Post-publish tools for the published-package repository.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._button_seq = 0
        self.add_content(self._build_tools())
        self.add_content(self._build_statistics())

    # -- construction ---------------------------------------------------

    def _build_tools(self) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_2)
        layout.addWidget(SectionHeader(
            "Tools", "Run maintenance across the published-package repository."))

        row = QHBoxLayout()
        row.setSpacing(theme.SPACE_2)
        row.addWidget(self._tool_card(
            "Bulk Price Update",
            "Roll every or selected series' open price list forward to a new "
            "list with fresh PDM prices.",
            self._on_price_update))
        row.addWidget(self._tool_card(
            "Check Base Lengths",
            "Compare base articles against PDM CAD Maintenance and edit the "
            "central registry.",
            self._on_check_base_lengths))
        row.addWidget(self._tool_card(
            "Update Version",
            "Bulk-write the export version and today's date to OCD + ODB "
            "packages.",
            self._on_update_version))
        layout.addLayout(row)
        return container

    def _tool_card(self, title: str, description: str, handler) -> QWidget:
        card = QFrame(self)
        card.setObjectName("toolCard")
        card.setStyleSheet(card_qss("toolCard"))
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        inner = QVBoxLayout(card)
        inner.setContentsMargins(theme.SPACE_3, theme.SPACE_3, theme.SPACE_3, theme.SPACE_3)
        inner.setSpacing(theme.SPACE_1)

        heading = QLabel(title, card)
        heading.setFont(theme.font("section_header"))
        heading.setStyleSheet(label_color_qss(theme.INK))

        self._button_seq += 1
        name = f"toolButton{self._button_seq}"
        button = QPushButton("Open", card)
        button.setObjectName(name)
        button.setStyleSheet(primary_button_qss(name))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(handler)

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

    def _build_statistics(self) -> QWidget:
        container = QWidget(self)
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_2)
        layout.addWidget(SectionHeader(
            "Repository statistics", "At-a-glance figures will appear here."))
        grid = StatisticsGrid(columns=3, parent=container)
        grid.set_metric("series", "Series", "-")
        grid.set_metric("priced", "Priced packages", "-")
        grid.set_metric("mismatch", "Base-length mismatches", "-")
        layout.addWidget(grid)
        layout.addStretch(1)
        return container

    # -- helpers --------------------------------------------------------

    def _default_repo(self) -> str:
        """The default repository string (existing workspaces, ';'-joined)."""
        return ";".join(p for p in _DEFAULT_REPOS if Path(p).is_dir())

    # -- tool launchers -------------------------------------------------

    def _on_price_update(self) -> None:
        from ui.dialogs.price_rollover_dialog import PriceRolloverDialog

        PriceRolloverDialog(self._context, self._default_repo(), self).exec()

    def _on_check_base_lengths(self) -> None:
        from ui.dialogs.base_length_check_dialog import BaseLengthCheckDialog

        BaseLengthCheckDialog(self._context, self._default_repo(), self).exec()

    def _on_update_version(self) -> None:
        from ui.dialogs.version_update_dialog import VersionUpdateDialog

        VersionUpdateDialog(self._context.version_update_service, self._default_repo(), self).exec()
