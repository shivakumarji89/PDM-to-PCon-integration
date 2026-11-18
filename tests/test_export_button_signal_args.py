"""Qt's QPushButton.clicked passes a ``checked`` bool; it must never replace a captured page."""
from __future__ import annotations

import os
import re
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

_app = QApplication.instance() or QApplication([])


def test_checked_argument_does_not_replace_captured_page():
    page = object()
    received = []
    handler = lambda _checked=False, page=page: received.append(page)
    button = QPushButton()
    button.clicked.connect(handler)
    button.click()
    assert received == [page]


def test_main_window_pricing_relation_export_lambda_ignores_checked():
    source = (Path(__file__).resolve().parents[1] / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert re.search(
        r"lambda _checked=False, page=page: self\._on_export_varcond_relations_mdb\(page\)", source
    )
    assert "lambda page=page:" not in source
