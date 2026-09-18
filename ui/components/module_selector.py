"""Top-level module selector.

This component selects the active workbench module without imposing workflow
rules. The selected module is exposed through a signal so the main window can
later map each module to its own workflow.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QLabel, QVBoxLayout, QWidget

from core.modules import MODULE_ITEMS, WorkbenchModule


class ModuleSelector(QWidget):
    """Compact selector for the five top-level workbench modules."""

    module_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("moduleSelector")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label = QLabel("Module:", self)
        label.setObjectName("moduleSelectorLabel")
        layout.addWidget(label)

        self._combo = QComboBox(self)
        self._combo.setObjectName("moduleSelectorCombo")

        for item in MODULE_ITEMS:
            self._combo.addItem(item.title, item.module)
            self._combo.setItemData(
                self._combo.count() - 1,
                item.description,
                role=3,  # Qt.ToolTipRole; avoids importing Qt only for the enum.
            )

        self._combo.currentIndexChanged.connect(self._on_changed)
        layout.addWidget(self._combo)

    def current_module(self) -> WorkbenchModule:
        """Return the currently selected module."""
        return self._combo.currentData()

    def set_module(self, module: WorkbenchModule) -> None:
        """Select a module without emitting a change notification."""
        for index in range(self._combo.count()):
            if self._combo.itemData(index) == module:
                self._combo.blockSignals(True)
                self._combo.setCurrentIndex(index)
                self._combo.blockSignals(False)
                return

    def _on_changed(self, index: int) -> None:
        module = self._combo.itemData(index)
        if isinstance(module, WorkbenchModule):
            self.module_changed.emit(module)
