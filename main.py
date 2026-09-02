"""MK Product Workbench - application entry point."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow

APP_NAME = "MK Product Workbench"
APP_ORG = "MK Engineering"
RESOURCES_DIR = Path(__file__).resolve().parent / "resources"


def load_stylesheet() -> str:
    """Return the application stylesheet, or an empty string if unavailable.

    Spacing placeholders (e.g. ``@PANEL_GUTTER@``) are substituted from the
    shared tokens in :mod:`ui.theme`, so the stylesheet and the Python layout
    code use one source of truth for the shell's gaps and insets.
    """
    qss_path = RESOURCES_DIR / "styles.qss"
    if not qss_path.exists():
        return ""
    from ui import theme

    text = qss_path.read_text(encoding="utf-8")
    for token, value in {
        "@PANEL_GUTTER@": theme.PANEL_GUTTER,
        "@PANEL_INSET@": theme.PANEL_INSET,
    }.items():
        text = text.replace(token, str(value))
    return text


def main() -> int:
    # Crisp High-DPI scaling on mixed-DPI / scaled displays.
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORG)
    app.setFont(QFont("Segoe UI", 9))

    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

