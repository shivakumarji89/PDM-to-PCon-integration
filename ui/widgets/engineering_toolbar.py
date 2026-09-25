"""Reusable engineering toolbar.

A configurable toolbar that standardises workspace actions and their order:
Search, Refresh, Select All, Clear Selection, Filter, Sort, Export (future),
Settings (future). Workspaces enable only the parts they need and connect to
the emitted signals. Presentation only - no engineering logic.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class EngineeringToolbar(QGroupBox):
    """Standard workspace toolbar with a fixed, consistent action order."""

    search_changed = Signal(str)
    filter_changed = Signal(str)
    refresh_requested = Signal()
    select_all_requested = Signal()
    clear_selection_requested = Signal()
    export_requested = Signal()
    settings_requested = Signal()

    def __init__(
        self,
        title: str = "Toolbar",
        *,
        search: bool = True,
        search_placeholder: str = "Search...",
        filters: list[str] | None = None,
        selection: bool = True,
        refresh: bool = True,
        export_placeholder: bool = False,
        settings_placeholder: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, parent)
        layout = QHBoxLayout(self)

        self._search = None
        if search:
            self._search = QLineEdit(self)
            self._search.setPlaceholderText(search_placeholder)
            self._search.setClearButtonEnabled(True)
            self._search.textChanged.connect(self.search_changed)
            layout.addWidget(self._search, 1)

        self._filter = None
        if filters:
            layout.addWidget(QLabel("Filter:", self))
            self._filter = QComboBox(self)
            self._filter.addItems(filters)
            self._filter.currentTextChanged.connect(self.filter_changed)
            layout.addWidget(self._filter)

        if selection:
            self._add_button(layout, "Select All", self.select_all_requested)
            self._add_button(layout, "Clear Selection", self.clear_selection_requested)
        if refresh:
            self._add_button(layout, "Refresh", self.refresh_requested)
        if export_placeholder:
            btn = self._add_button(layout, "Export", self.export_requested)
            btn.setEnabled(False)
            btn.setToolTip("Export - available in a future phase")
        if settings_placeholder:
            btn = self._add_button(layout, "Settings", self.settings_requested)
            btn.setEnabled(False)
            btn.setToolTip("Settings - available in a future phase")

    def _add_button(self, layout: QHBoxLayout, text: str, signal) -> QPushButton:
        button = QPushButton(text, self)
        button.clicked.connect(signal)
        layout.addWidget(button)
        return button

    # -- accessors ---------------------------------------------------------
    @property
    def search_text(self) -> str:
        return self._search.text() if self._search else ""

    @property
    def filter_text(self) -> str:
        return self._filter.currentText() if self._filter else ""
