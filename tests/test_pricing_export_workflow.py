"""End-to-end Pricing export workflow: target lists -> preview -> bound write."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from core.application_context import ApplicationContext
from core.modules import WorkbenchModule
from models.snapshot import Snapshot
from ui.dialogs.price_export_preview_dialog import PriceExportPreviewDialog
from ui.dialogs.price_list_target_dialog import PriceListTargetDialog, describe_plan
from ui.pages import pricing_page as pp
from ui.pages.pricing_page import PricingPage

from tests.test_price_mdb_export_service import (
    _OptimizedFake, _eur_row, _global, _on, _plist, _rec, _strict_lists,
)


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


class _Sync:
    """QThreadPool stand-in: run each task immediately on the calling thread."""

    def start(self, task):
        task.run()


@pytest.fixture
def wf(monkeypatch, tmp_path):
    mdb_file = tmp_path / "ocd.mdb"
    mdb_file.touch()
    state = {"errors": [], "infos": [], "dialogs": []}
    monkeypatch.setattr(pp.QThreadPool, "globalInstance", staticmethod(lambda: _Sync()))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(mdb_file), "")))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda p, t, m: state["errors"].append(m)))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda p, t, m: state["infos"].append(m)))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda p, t, m: state["errors"].append(m)))

    def make(records, fake, target_names=None, target_accept=True, export_accept=True, before_export=None):
        names = target_names or {"EUR": "EURO_2026_2", "GBP": "GBP_2026_2"}

        def target_exec(self):
            for ccy, text in names.items():
                if ccy in self.edits:
                    self.edits[ccy].setText(text)
            return QDialog.DialogCode.Accepted if target_accept and self.buttons.button(
                self.buttons.StandardButton.Ok).isEnabled() else QDialog.DialogCode.Rejected

        def preview_exec(self):
            state["dialogs"].append(self)
            if before_export:
                before_export()
            return QDialog.DialogCode.Accepted if export_accept and (
                self.export_button is not None and self.export_button.isEnabled()) else QDialog.DialogCode.Rejected

        monkeypatch.setattr(PriceListTargetDialog, "exec", target_exec)
        monkeypatch.setattr(PriceExportPreviewDialog, "exec", preview_exec)
        snap = Snapshot()
        snap.metadata.source = "PDM"
        snap.price_records = list(records)
        ctx = ApplicationContext()
        ctx.register_pdm_snapshot(snap)
        ctx.activate_snapshot_source("pdm")
        monkeypatch.setattr(ApplicationContext, "mdb_service", property(lambda self: fake))
        page = PricingPage(ctx)
        page._active_module = WorkbenchModule.MAINTENANCE
        page.refresh()
        return page

    return make, state


def test_write_workflow_uses_the_approved_lists_and_plan(wf):
    make, state = wf
    fake = _OptimizedFake(_strict_lists(), linked=[21, 22])
    page = make([_rec(10.0, "EUR"), _rec(9.0, "GBP"), _global("G.1", 5.0, "EUR")], fake)
    page._on_export_prices()
    assert not state["errors"], state["errors"]
    inserts = [op for op in fake.ops if op["op"] == "insert"]
    assert {r["com_PriceListID"] for op in inserts if op["table"] == "tCOMd_Price" for r in op["rows"]} == {21, 22}
    assert not any(op["table"] == "tCOMd_PriceList2" for op in fake.ops)        # reused, not recreated
    assert state["dialogs"][0].export_button is not None
    assert "Export complete" in page._summary.text()
    assert any("EUR -> EURO_2026_2" in line for line in state["dialogs"][0].summary_label.text().splitlines())


def test_preview_button_never_writes(wf):
    make, state = wf
    fake = _OptimizedFake(_strict_lists(), linked=[21, 22])
    page = make([_rec(10.0, "EUR")], fake)
    page._on_preview_export()
    assert fake.ops == []
    assert state["dialogs"][0].export_button is None
    assert "no MDB record was modified" in page._summary.text()


def test_cancelling_the_target_dialog_stops_before_any_preview(wf):
    make, state = wf
    fake = _OptimizedFake(_strict_lists(), linked=[21, 22])
    page = make([_rec(10.0, "EUR")], fake, target_accept=False)
    page._on_export_prices()
    assert fake.ops == [] and state["dialogs"] == []


def test_declining_the_preview_writes_nothing(wf):
    make, state = wf
    fake = _OptimizedFake(_strict_lists(), linked=[21, 22])
    page = make([_rec(10.0, "EUR")], fake, export_accept=False)
    page._on_export_prices()
    assert fake.ops == []


def test_renamed_list_is_created_exactly_as_approved(wf):
    make, state = wf
    fake = _OptimizedFake(_strict_lists(), linked=[21, 22])
    page = make([_on("EUR", "2027-01-05"), _on("GBP", "2027-01-05")], fake,
                target_names={"EUR": "EURO_2027", "GBP": "GBP_2027"})
    page._on_export_prices()
    assert not state["errors"], state["errors"]
    created = next(op for op in fake.ops if op["table"] == "tCOMd_PriceList2")["rows"]
    assert {r["com_PriceListLabel"] for r in created} == {"EURO_2027", "GBP_2027"}


def test_plan_goes_stale_when_the_mdb_changes_after_the_preview(wf):
    make, state = wf
    fake = _OptimizedFake(_strict_lists(), linked=[21, 22])
    page = make([_rec(10.0, "EUR")], fake,
                before_export=lambda: fake.rows.__setitem__(_price_sql(), [_eur_row(pid=1, value=1.0)]))
    page._on_export_prices()
    assert fake.ops == []
    assert any("Preview Export again" in e for e in state["errors"])


def _price_sql():
    from tests.test_price_mdb_export_service import _PRICE_SQL
    return _PRICE_SQL


def test_blocked_plan_leaves_the_export_button_disabled(wf):
    make, state = wf
    lists = [_plist(21, "EURO_2026_2", "EUR", "2026-09-07", "2026-12-31")]
    fake = _OptimizedFake(lists, linked=[21])
    page = make([_on("EUR", "2027-01-02")], fake, target_names={"EUR": "EURO_2026_2"})
    page._on_export_prices()
    assert fake.ops == []                       # the target dialog refused to accept the blocked list


def test_target_dialog_validates_live_and_describes_the_plan():
    lists = _strict_lists()
    dialog = PriceListTargetDialog(["EUR", "GBP"], {"EUR": "EURO_2026_2", "GBP": "GBP_2026_2"},
                                   lists, {"21"}, "20261016")
    ok = dialog.buttons.button(dialog.buttons.StandardButton.Ok)
    assert ok.isEnabled()
    assert "Reuse existing list id 21" in dialog.status["EUR"].text()
    assert "NOT region-linked" in dialog.status["GBP"].text()
    dialog.edits["GBP"].setText("bad/name")
    assert not ok.isEnabled() and "BLOCKED" in dialog.status["GBP"].text()
    dialog.edits["GBP"].setText("EURO 2026_2")               # same list name as EUR
    assert not ok.isEnabled()
    dialog.edits["GBP"].setText("GBP_2027")
    assert ok.isEnabled() and "Create new GBP list" in describe_plan(dialog.plans["GBP"])
    assert dialog.names() == {"EUR": "EURO_2026_2", "GBP": "GBP_2027"}



def test_target_selectors_offer_currency_scoped_lists_and_create_new():
    lists = _strict_lists()
    dialog = PriceListTargetDialog(
        ["EUR", "GBP"],
        {"EUR": "EURO_2026_2", "GBP": "GBP_2026_2"},
        lists,
        {"21", "22"},
        "20261016",
    )
    assert dialog.selectors["EUR"].count() == 2
    assert dialog.selectors["GBP"].count() == 2
    assert "EURO_2026_2" in dialog.selectors["EUR"].itemText(1)
    assert "GBP_2026_2" in dialog.selectors["GBP"].itemText(1)

    # Choosing Create must propose a distinct list name, not silently reuse
    # the list that was selected before changing the dropdown.
    dialog.selectors["EUR"].setCurrentIndex(0)
    assert dialog.edits["EUR"].isVisible()
    assert dialog.names()["EUR"] != "EURO_2026_2"
    assert dialog.plans["EUR"].action == "create"
    assert dialog.plans["EUR"].ok
