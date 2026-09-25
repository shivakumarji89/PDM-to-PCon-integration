"""A small modal 'working...' popup with a live status line.

For short SYNCHRONOUS operations (apply base length, grouping, class grouping)
that would otherwise freeze the UI silently. Use it as a context manager and
call :meth:`update_status` at each stage; the popup repaints between stages by
pumping the event loop, so the user sees realtime progress.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class BusyPopup(QDialog):
    """A tiny modal popup: bold title + live status line + indeterminate bar."""

    #: Re-entrancy guard: only one busy popup may be active at a time. A nested
    #: ``with BusyPopup(...)`` (e.g. an operation that triggers a refresh) is a
    #: no-op, so ``processEvents`` can never spawn a second modal dialog.
    _active = False

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("busyPopup")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedWidth(300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        title_label = QLabel(title, self)
        title_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(title_label)
        self._status = QLabel("Working...", self)
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        bar = QProgressBar(self)
        bar.setRange(0, 0)  # indeterminate
        bar.setTextVisible(False)
        layout.addWidget(bar)
        self._noop = False

    def update_status(self, text: str) -> None:
        """Set the status line and repaint (pumps the event loop)."""
        if self._noop:
            return
        self._status.setText(text)
        QApplication.processEvents()

    def __enter__(self) -> "BusyPopup":
        # Suppress if a popup is already active (never nest a modal + pump).
        if BusyPopup._active:
            self._noop = True
            return self
        BusyPopup._active = True
        parent = self.parentWidget()
        if parent is not None:
            center = parent.window().geometry().center()
            self.move(center.x() - self.width() // 2, center.y() - 40)
        self.show()
        QApplication.processEvents()
        return self

    def __exit__(self, *_exc) -> bool:
        if not self._noop:
            BusyPopup._active = False
            self.close()
        self.deleteLater()
        return False
