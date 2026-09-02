"""Reusable empty-state widget.

A configurable placeholder shown when a workspace has nothing to display
(no results, empty snapshot, disconnected, etc.). Purely presentational.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

# Standard messages so wording is consistent everywhere.
NO_RESULTS = "No results match your search."
EMPTY_SNAPSHOT = "No product loaded. Load a product to begin."
DISCONNECTED = "Not connected to PDM."
LOADING = "Loading..."
REFRESHING = "Refreshing..."
SEARCHING = "Searching..."


class EmptyStateWidget(QWidget):
    """Centered message shown in place of empty content."""

    def __init__(self, message: str = EMPTY_SNAPSHOT, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._label = QLabel(message, self)
        self._label.setObjectName("pagePlaceholder")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        layout.addWidget(self._label)

    def set_message(self, message: str) -> None:
        self._label.setText(message)
