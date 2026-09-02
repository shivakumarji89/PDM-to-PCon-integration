"""Design-system component: MetricTile and StatisticsGrid.

A :class:`MetricTile` is a small card that presents a single value under a quiet
label (the "label above value" pattern that replaces WinForms label:value rows).
A :class:`StatisticsGrid` arranges tiles in a responsive grid. Both are fully
token-driven and reusable across dialogs, panels and pages.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from ui import theme
from ui.components._styles import accent_card_qss, card_qss, label_color_qss


class MetricTile(QFrame):
    """A single labelled metric rendered as a compact card."""

    def __init__(
        self,
        label: str = "",
        value: str = "",
        variant: str = "default",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        accent = variant == "accent"
        name = "metricTileAccent" if accent else "metricTile"
        self.setObjectName(name)
        self.setStyleSheet(accent_card_qss(name) if accent else card_qss(name))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            theme.SPACE_3, theme.SPACE_3, theme.SPACE_3, theme.SPACE_3
        )
        layout.setSpacing(theme.SPACE_1)

        self._label = QLabel(label, self)
        self._label.setFont(theme.font("metric_label"))
        self._label.setStyleSheet(label_color_qss(theme.MUTED))

        self._value = QLabel(value, self)
        self._value.setFont(theme.font("metric_value"))
        self._value.setStyleSheet(
            label_color_qss(theme.ACCENT if accent else theme.INK)
        )
        self._value.setWordWrap(False)

        layout.addWidget(self._label)
        layout.addWidget(self._value)

    def set_label(self, text: str) -> None:
        self._label.setText(text)

    def set_value(self, value: str) -> None:
        self._value.setText(value or "-")


class StatisticsGrid(QWidget):
    """A responsive grid of :class:`MetricTile`s keyed by a stable name."""

    def __init__(self, columns: int = 3, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._columns = max(1, columns)
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(theme.SPACE_2)
        self._tiles: dict[str, MetricTile] = {}
        self._order: list[str] = []

    def set_metric(self, key: str, label: str, value: str) -> None:
        """Create the tile for ``key`` if needed, then update its value."""
        tile = self._tiles.get(key)
        if tile is None:
            tile = MetricTile(label, value)
            self._tiles[key] = tile
            self._order.append(key)
            index = len(self._order) - 1
            self._grid.addWidget(
                tile, index // self._columns, index % self._columns
            )
        else:
            tile.set_label(label)
            tile.set_value(value)

    def clear(self) -> None:
        """Remove every tile so a different metric set can be shown."""
        for tile in self._tiles.values():
            self._grid.removeWidget(tile)
            tile.deleteLater()
        self._tiles.clear()
        self._order.clear()
