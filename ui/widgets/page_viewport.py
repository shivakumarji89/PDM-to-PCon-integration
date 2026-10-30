"""Centre-panel hosting that keeps page minimum sizes from driving the window.

``QStackedWidget`` reports the largest minimum size of *all* its pages, hidden
ones included, so a single tall workflow page would force every other page -
and the main window - to be that big. :class:`CurrentPageStack` reports only the
visible page, and :func:`scrollable` wraps a widget in a frameless scroll area
so a page that really needs more room than the window has scrolls instead of
being clipped or pushing the window off-screen.
"""
from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QFrame, QScrollArea, QStackedWidget, QWidget


class CurrentPageStack(QStackedWidget):
    """Stacked widget whose size hints come from the current page only."""

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt override
        page = self.currentWidget()
        return page.minimumSizeHint() if page is not None else QSize(0, 0)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        page = self.currentWidget()
        return page.sizeHint() if page is not None else QSize(0, 0)

    def heightForWidth(self, width: int) -> int:  # noqa: N802 - Qt override
        # QStackedLayout reports the largest height-for-width of *every* page,
        # so one tall hidden page would force all pages (and the scroll area)
        # to that height. Only the visible page counts.
        page = self.currentWidget()
        layout = page.layout() if page is not None else None
        if layout is not None and layout.hasHeightForWidth():
            return layout.heightForWidth(width)
        return -1


def scrollable(content: QWidget, parent: QWidget | None = None) -> QScrollArea:
    """Wrap ``content`` in a transparent scroll area that only scrolls when
    the viewport is smaller than the content's minimum size."""
    area = QScrollArea(parent)
    area.setObjectName("pageViewport")
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setWidgetResizable(True)
    area.viewport().setAutoFillBackground(False)
    area.setStyleSheet("QScrollArea#pageViewport { background: transparent; border: 0; }")
    area.setWidget(content)
    return area
