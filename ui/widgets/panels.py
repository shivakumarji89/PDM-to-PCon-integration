"""Reusable key/value and summary panels.

Configurable, presentation-only building blocks that standardise how every
workspace shows its details, statistics, status and validation. Each panel is
a labelled group box driven by simple ``set_*`` calls; workspaces supply only
labels and values - the widgets own the layout, spacing and formatting.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

# Consistent status / validation colours, sourced from the design system so
# there is a single palette across the whole application.
from ui.theme import (  # noqa: E402
    COLOR_ERROR,
    COLOR_INFO,
    COLOR_OK,
    COLOR_WARNING,
)


class KeyValuePanel(QGroupBox):
    """A titled panel of ``label: value`` rows.

    Usage:
        panel = KeyValuePanel("Details", ["Code", "Name"])
        panel.set("Code", "ABC")
    """

    def __init__(self, title: str, labels: list[str] | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self._form = QFormLayout(self)
        self._values: dict[str, QLabel] = {}
        for label in labels or []:
            self.add_row(label)

    def add_row(self, label: str, wrap: bool = False) -> QLabel:
        value = QLabel("-", self)
        value.setWordWrap(wrap)
        self._values[label] = value
        self._form.addRow(f"{label}:", value)
        return value

    def set(self, label: str, value: str) -> None:
        if label in self._values:
            self._values[label].setText(value if value not in ("", None) else "-")

    def set_color(self, label: str, color: str) -> None:
        if label in self._values:
            self._values[label].setStyleSheet(f"color: {color};")


class StatisticsPanel(KeyValuePanel):
    """Statistics card. Inject metrics as ``{label: value}``."""

    def __init__(self, title: str = "Statistics", parent: QWidget | None = None) -> None:
        super().__init__(title, parent=parent)

    def set_metrics(self, metrics: dict[str, object]) -> None:
        for label, value in metrics.items():
            if label not in self._values:
                self.add_row(label)
            self.set(label, str(value))


class DetailsPanel(KeyValuePanel):
    """Details card. Workspaces supply fields/labels/values only."""

    def __init__(self, title: str = "Details", labels: list[str] | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(title, labels, parent)


class StatusPanel(KeyValuePanel):
    """Standard workspace status panel (loaded/selected/validation/etc.)."""

    def __init__(self, title: str = "Workspace Status", parent: QWidget | None = None) -> None:
        super().__init__(
            title,
            ["Loaded", "Selected", "Validation", "Warnings", "Readiness"],
            parent,
        )
        self._values["Warnings"].setWordWrap(True)


class ValidationSummary(QGroupBox):
    """Consistent validation summary with standard colours.

    Accepts any object exposing ``ok``, ``warnings`` and optionally ``errors``.
    """

    def __init__(self, title: str = "Validation", parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        layout = QVBoxLayout(self)
        self._status = QLabel("-", self)
        self._detail = QLabel("-", self)
        self._detail.setWordWrap(True)
        layout.addWidget(self._status)
        layout.addWidget(self._detail)

    def set_result(self, result) -> None:
        errors = list(getattr(result, "errors", []) or [])
        warnings = list(getattr(result, "warnings", []) or [])
        if errors:
            self._status.setText("Blocked")
            self._status.setStyleSheet(f"color: {COLOR_ERROR}; font-weight: 600;")
            self._detail.setText("\n".join(errors + warnings))
        elif warnings:
            self._status.setText("Warnings")
            self._status.setStyleSheet(f"color: {COLOR_WARNING}; font-weight: 600;")
            self._detail.setText("\n".join(warnings))
        elif getattr(result, "ok", True):
            self._status.setText("Ready")
            self._status.setStyleSheet(f"color: {COLOR_OK}; font-weight: 600;")
            self._detail.setText("No issues.")
        else:
            self._status.setText("Information")
            self._status.setStyleSheet(f"color: {COLOR_INFO}; font-weight: 600;")
            self._detail.setText("-")
