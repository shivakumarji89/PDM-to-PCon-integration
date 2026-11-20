"""Reload Relations button and cache-aware navigation in the VARCOND panel."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from tests import varcond_fakes as fakes
from tests.test_varcond_background import _maintenance_panel
from ui.dialogs.varcond_generation_dialog import VarCondGenerationPanel


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _record_loads(panel, monkeypatch):
    calls = []
    monkeypatch.setattr(
        panel, "_load_maintenance_sources_async",
        lambda codes, refresh: calls.append(refresh),
    )
    return calls


def test_reload_button_is_shown_only_for_maintenance(app, monkeypatch):
    fakes.install(monkeypatch)
    development = VarCondGenerationPanel(fakes.build_context(), maintenance_check=lambda: False)

    assert development._reload_button.isHidden()

    maintenance = _maintenance_panel(monkeypatch)
    _record_loads(maintenance, monkeypatch)
    maintenance.refresh_from_snapshot()
    assert not maintenance._reload_button.isHidden()


def test_clicking_reload_requests_a_refresh_from_pdm(app, monkeypatch):
    fakes.install(monkeypatch)
    panel = _maintenance_panel(monkeypatch)
    calls = _record_loads(panel, monkeypatch)

    panel._reload_button.click()

    assert calls == [True]


def test_navigation_never_requests_a_refresh(app, monkeypatch):
    fakes.install(monkeypatch)
    panel = _maintenance_panel(monkeypatch)
    calls = _record_loads(panel, monkeypatch)

    panel.refresh_from_snapshot()
    panel.refresh_from_snapshot()

    assert calls and not any(calls)           # only "load what is missing"


def test_failed_reload_keeps_the_previous_relations_and_says_so(app, monkeypatch):
    fakes.install(monkeypatch)
    panel = _maintenance_panel(monkeypatch)
    generated = []

    class Service:
        def has_sources(self, codes):
            return True

    panel._maintenance_service = Service()
    monkeypatch.setattr(panel, "_generate_all", lambda: generated.append(True))
    panel._reload_requested = True

    panel._on_maintenance_sources_failed("PDM unavailable")

    assert generated == [True]
    assert "previous saved relations kept" in panel._summary.text()
    assert "PDM unavailable" in panel._summary.text()
