"""Shared workflow layout/card components and the Maintenance comparison pilot."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTableWidget

from models.maintenance_snapshot import MaintenanceAlignment
from services.maintenance_parity_service import DIFFERENT, MATCH, ParityDifference, ParityReport
from ui import theme
from ui.components import (
    ActionBar,
    ActionCard,
    CardRow,
    DataCard,
    InfoCard,
    KpiCard,
    MessageCard,
    ProgressStatusCard,
    StatusCard,
    set_button_role,
)
from ui.pages.base_page import BasePage
from ui.pages.maintenance_comparison_page import MaintenanceComparisonPage


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class _Ctx:
    def __init__(self, snapshot=None):
        self.maintenance_snapshot = snapshot


def _loaded_context(aligned=True):
    pdm = SimpleNamespace(articles=[1, 2, 3], product=SimpleNamespace(code="P1", name="Prod"))
    mdb = SimpleNamespace(articles=[1, 2], metadata=SimpleNamespace(source="x.mdb", notes="", product_code="P1"))
    state = SimpleNamespace(
        pdm_snapshot=pdm,
        mdb_import_snapshot=mdb,
        alignment=MaintenanceAlignment(status="ALIGNED" if aligned else "UNRESOLVED"),
    )
    return _Ctx(state)


# ---- shared components -------------------------------------------------------
def test_kpi_card_tone_and_value(app):
    card = KpiCard("Total", "12", "neutral")
    card.set_value("99")
    card.set_tone("danger")
    assert card.value_label.text() == "99"
    assert card.tone == "danger"
    assert theme.WB_RED_SOFT.lower() in card.styleSheet().lower()


def test_neutral_card_is_not_coloured(app):
    card = KpiCard("x", "1", "neutral")
    assert theme.WB_GREEN.lower() not in card.styleSheet().lower()
    assert theme.WB_RED.lower() not in card.styleSheet().lower()


def test_action_card_clicks_and_key(app):
    card = ActionCard("Go", "desc")
    hits = []
    card.clicked.connect(lambda: hits.append(1))
    card.show()
    QTest.mouseClick(card, Qt.MouseButton.LeftButton)
    QTest.keyClick(card, Qt.Key.Key_Return)
    assert len(hits) == 2


def test_message_card_hidden_until_message(app):
    card = MessageCard("warning")
    assert card.isHidden()
    card.show_message("Careful", "danger")
    assert not card.isHidden() and card.tone == "danger"
    card.show_message("")
    assert card.isHidden()


def test_info_card_rows_return_updatable_labels(app):
    card = InfoCard("Info")
    value = card.add_row("A", "1")
    value.setText("2")
    assert isinstance(value, QLabel) and value.text() == "2"


def test_progress_card_adopts_existing_bar(app):
    from PySide6.QtWidgets import QProgressBar

    bar = QProgressBar()
    card = ProgressStatusCard("P", bar=bar)
    assert card.bar is bar


def test_button_roles_and_actionbar_keep_signals(app):
    bar = ActionBar()
    a, b = QPushButton("Save"), QPushButton("Delete")
    clicks = []
    a.clicked.connect(lambda: clicks.append("a"))
    bar.add_group(a, role="primary")
    bar.add_group(b, role="danger")
    a.click()
    assert clicks == ["a"]
    assert a.property("wfRole") == "primary" and b.property("wfRole") == "danger"
    set_button_role(a, "bogus")
    assert a.property("wfRole") == "secondary"


def test_card_row_reflows_without_clipping(app):
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    host = QWidget()  # pages host the row inside a parent layout
    QVBoxLayout(host).setContentsMargins(0, 0, 0, 0)
    row = CardRow(200)
    host.layout().addWidget(row)
    for i in range(4):
        row.add_card(KpiCard(f"k{i}", "1"))
    host.resize(1000, 100)
    host.show()
    app.processEvents()
    assert row.columns() == 4
    host.resize(450, 100)
    app.processEvents()
    assert row.columns() == 2
    host.resize(150, 100)
    app.processEvents()
    assert row.columns() == 1
    assert row.width() >= 150


def test_basepage_default_layout_unchanged(app):
    page = BasePage("T", "D", show_placeholder=False)
    assert page.wf is None
    assert page.findChild(QLabel, "pageTitle").text() == "T"


def test_basepage_workflow_layout_routes_add_content(app):
    page = BasePage("T", "D", show_placeholder=False, workflow_layout=True, content_stretch=True)
    assert page.wf is not None
    marker = QLabel("x")
    page.add_content(marker)
    assert marker.parent() is page.wf._main
    assert page.wf.header.title_label.text() == "T"


# ---- pilot: Maintenance comparison -------------------------------------------
def test_pilot_empty_state(app):
    page = MaintenanceComparisonPage(_Ctx(None))
    page.resize(1100, 700)
    page.show()
    assert page._status.text() == "Load a Maintenance PDM scope first."
    assert page._alignment.text() == "Not loaded"
    assert page.is_ready() is False
    assert isinstance(page._table, QTableWidget) and page._table.rowCount() == 0
    assert page._alignment_card.tone == "neutral"


def test_pilot_blocked_when_not_aligned(app):
    page = MaintenanceComparisonPage(_loaded_context(aligned=False))
    assert page._pdm.text() == "3" and page._mdb.text() == "2"
    assert page._status.text().startswith("Comparison blocked")
    assert page._alignment_card.tone == "danger"
    assert page.wf.header.status_pill.text() == "Blocked"
    assert "P1" in page._pdm_identity.text()


def test_pilot_results_render_and_tone(app, monkeypatch):
    page = MaintenanceComparisonPage(_Ctx(None))
    report = ParityReport(
        differences=[
            ParityDifference("Class", MATCH, "k1", "a", "a"),
            ParityDifference("Class", DIFFERENT, "k2", "a", "b"),
        ]
    )
    page._on_finished(report)
    assert page._table.rowCount() == 2
    assert page._counts.text().startswith("1 match")
    assert page._status.text() == "PDM ↔ MDB comparison found differences."
    assert page.wf.header.status_pill.text() == "Differences"
    page._on_finished(ParityReport(differences=[ParityDifference("Class", MATCH, "k", "a", "a")]))
    assert page.wf.header.status_pill.text() == "Pass"
    assert page._results_card.tone == "success"
    page._on_failed("boom")
    assert page._status.text() == "Comparison failed: boom"
    assert page.wf.header.status_pill.text() == "Failed"


@pytest.mark.parametrize("size", [(1500, 900), (1000, 640), (700, 500)])
def test_pilot_resizes_without_error(app, size):
    page = MaintenanceComparisonPage(_loaded_context(aligned=False))
    page.resize(*size)
    page.show()
    app.processEvents()
    assert page.width() == size[0]
    assert page._table_card.isVisible()
    page.close()
