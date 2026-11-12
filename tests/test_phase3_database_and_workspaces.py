"""Phase 3: verified PDM database switching, repository availability on other computers, Knoll workspace discovery."""
from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from core import repository_workspace as rw
from core.application_context import ApplicationContext
from core.config import AppConfig, PDM_DATABASE_PRESETS
from core.pdm_connection import PdmConnectionState, switch_pdm_database, verify_connection
from repositories.pdm_repository import PDMRepository
from tests.ocd_engine.ocd_repo_fixture import write_plain_range

KNOLL_WORKSPACE = r"C:\KnollSVN\Staging\HermanMiller\_repository"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    previous = QSettings.defaultFormat()
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qt"))
    yield
    QSettings.setDefaultFormat(previous)


# ------------------------------------------------------------------ fake SQL Server driver
class FakeOdbc:
    """Stands in for pyodbc: records every connection string and answers ``SELECT DB_NAME()`` from it."""

    class Error(Exception):
        pass

    def __init__(self, unreachable=()):
        self.unreachable = set(unreachable)
        self.connection_strings: list[str] = []
        self.closed = 0

    def connect(self, connection_string):
        self.connection_strings.append(connection_string)
        fields = dict(part.split("=", 1) for part in connection_string.split(";") if "=" in part)
        if fields["DATABASE"] in self.unreachable:
            raise self.Error(f"Cannot open database {fields['DATABASE']}")
        return FakeConnection(self, fields["DATABASE"])


class FakeConnection:
    def __init__(self, odbc, database):
        self._odbc, self._database = odbc, database

    def cursor(self):
        return self

    def execute(self, _sql):
        return self

    def fetchone(self):
        return (self._database,)

    def close(self):
        self._odbc.closed += 1


@pytest.fixture
def odbc(monkeypatch):
    fake = FakeOdbc()
    monkeypatch.setattr(PDMRepository, "_driver", lambda self: fake)
    return fake


def _live_context():
    context = ApplicationContext(AppConfig())
    assert context.config.active_pdm_preset() == "PDM Live"
    return context


# ------------------------------------------------------------------ Issue 1: PDM database
def test_switch_live_to_test_connects_to_the_selected_database(odbc):
    context = _live_context()
    result = switch_pdm_database(context, "PDM Test")

    server, database = PDM_DATABASE_PRESETS["PDM Test"]
    assert result.ok and result.state.verified
    assert (context.config.pdm_server, context.config.pdm_database) == (server, database)
    assert context.config.active_pdm_preset() == "PDM Test"
    # the connection really opened used the selected server/database, and was closed again
    assert odbc.connection_strings == [f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"]
    assert odbc.closed == 1
    assert context.pdm_connection_state.label == f"{server}/{database}"


def test_every_later_pdm_operation_uses_the_selected_database(odbc):
    context = _live_context()
    switch_pdm_database(context, "PDM Test")
    odbc.connection_strings.clear()

    PDMRepository(context).get_connection().close()
    context.get_service(__import__("services.pdm_service", fromlist=["PDMService"]).PDMService).repository.get_connection().close()

    assert len(odbc.connection_strings) == 2
    assert all("DATABASE=PDMTEST;" in cs and "SERVER=DBCHIP11V;" in cs for cs in odbc.connection_strings)


def test_switch_releases_the_previous_service_state(odbc):
    from services.pdm_service import PDMService

    context = _live_context()
    service = context.get_service(PDMService)
    _ = service.repository
    service._connected = True
    switch_pdm_database(context, "PDM Test")
    assert service._repository is None and not service.is_connected()


def test_failed_switch_keeps_previous_database_and_reports_error(odbc):
    context = _live_context()
    verified = verify_connection(context)
    assert verified.verified
    odbc.unreachable.add("PDMTEST")

    result = switch_pdm_database(context, "PDM Test")

    assert not result.ok and "PDMTEST" in result.error
    assert context.config.active_pdm_preset() == "PDM Live"
    assert context.pdm_connection_state == verified            # still describes the database really in use


def test_unknown_preset_changes_nothing(odbc):
    context = _live_context()
    result = switch_pdm_database(context, "No Such Database")
    assert not result.ok and context.config.active_pdm_preset() == "PDM Live"
    assert odbc.connection_strings == []


def test_connected_to_a_different_database_is_not_reported_verified(monkeypatch):
    context = _live_context()
    monkeypatch.setattr(PDMRepository, "test_connection", lambda self: "SomethingElse")
    state = verify_connection(context)
    assert not state.verified and "SomethingElse" in state.message


def _status_text(item) -> str:
    return item._second.text()


def test_status_strip_reflects_the_actual_connection(app, odbc):
    from ui.pages.module_home_page import ModuleHomePage

    context = _live_context()
    page = ModuleHomePage(context)
    assert _status_text(page._pdm_status) == "DBCHIP12V/PDMLive · Not verified"

    switch_pdm_database(context, "PDM Test")
    page.refresh_status()
    assert _status_text(page._pdm_status) == "DBCHIP11V/PDMTEST · Connected"
    assert "PDM Test" in page._pdm_status.toolTip()

    odbc.unreachable.add("PDMLive")
    switch_pdm_database(context, "PDM Live")                    # fails -> still on Test
    page.refresh_status()
    assert _status_text(page._pdm_status) == "DBCHIP11V/PDMTEST · Connected"


def test_startup_shows_selection_and_verifies_it_separately(app, odbc):
    from ui.main_window import MainWindow
    from PySide6.QtCore import QThreadPool

    window = MainWindow()
    try:
        home = window._module_home
        # selection is shown from the start and matches the selector; nothing is claimed as verified yet
        assert window._database_selector.currentText() == "PDM Live"
        assert _status_text(home._pdm_status) == "DBCHIP12V/PDMLive · Not verified"
        window.verify_pdm_connection_async()
        assert QThreadPool.globalInstance().waitForDone(10000)
        for _ in range(10):
            app.processEvents()
        assert _status_text(home._pdm_status) == "DBCHIP12V/PDMLive · Connected"
        assert odbc.connection_strings and all("DATABASE=PDMLive;" in c for c in odbc.connection_strings)
    finally:
        window.close()


def test_startup_check_failure_shows_not_connected_but_keeps_selection(app, odbc):
    from ui.main_window import MainWindow
    from PySide6.QtCore import QThreadPool

    odbc.unreachable.add("PDMLive")
    window = MainWindow()
    try:
        window.verify_pdm_connection_async()
        assert QThreadPool.globalInstance().waitForDone(10000)
        for _ in range(10):
            app.processEvents()
        assert _status_text(window._module_home._pdm_status) == "DBCHIP12V/PDMLive · Not connected"
        assert window._database_selector.currentText() == "PDM Live"
    finally:
        window.close()


def test_stale_check_cannot_overwrite_a_newer_selection(odbc):
    context = _live_context()
    original = PDMRepository.test_connection

    def switch_midway(self):
        name = original(self)
        context.config.set_pdm_database("PDM Test")       # selection changes while the check is in flight
        return name

    PDMRepository.test_connection = switch_midway
    try:
        verify_connection(context)
    finally:
        PDMRepository.test_connection = original
    assert context.pdm_connection_state is None


def test_main_window_selector_switches_and_reverts_on_failure(app, odbc, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from ui.main_window import MainWindow
    import ui.main_window as main_window_module

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a[2]))
    window = MainWindow()
    resets = []
    monkeypatch.setattr(window._product_page, "reset_for_database_switch", lambda: resets.append(1))
    try:
        window._database_selector.setCurrentText("PDM Test")
        assert window._context.config.pdm_database == "PDMTEST"
        assert "DBCHIP11V/PDMTEST · Connected" == _status_text(window._module_home._pdm_status)
        assert resets == [1]

        odbc.unreachable.add("PDMFrozen")
        window._database_selector.setCurrentText("PDM Frozen")
        assert window._context.config.pdm_database == "PDMTEST"          # unchanged
        assert window._database_selector.currentText() == "PDM Test"     # selector reverted
        assert "DBCHIP11V/PDMTEST · Connected" == _status_text(window._module_home._pdm_status)
        assert resets == [1] and len(warnings) == 1 and "PDMFrozen" in warnings[0]
    finally:
        window.close()


def test_registry_cache_is_not_served_across_databases(tmp_path, monkeypatch):
    from models.product import Product
    from services.pdm_service import PDMService

    monkeypatch.setattr(PDMService, "_REGISTRY_CACHE", tmp_path / "registry.json")
    context = _live_context()
    service = PDMService(context)
    service._save_registry_cache([Product(id="1", code="C", name="N", category="K", description="D")])
    assert service._load_registry_cache() is not None

    context.config.set_pdm_database("PDM Test")
    assert service._load_registry_cache() is None                # Live rows must not appear under Test


# ------------------------------------------------------------------ Issue 2: repository availability
def test_defaults_keep_the_existing_repository_paths():
    config = AppConfig()
    assert list(config.repository_browser_roots) == ["Seating", "Tables"]
    assert config.repository_browser_roots["Seating"].endswith(r"WS\Seating\Seating")
    assert KNOLL_WORKSPACE not in config.repository_browser_roots.values()    # Maintenance roots untouched


def test_override_file_supports_another_computers_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_SVN_DRIVE", str(tmp_path))
    (tmp_path / "Seating").mkdir()
    settings = tmp_path / "workbench_config.json"
    settings.write_text(json.dumps({
        "repository_browser_roots": {"Seating": "%TEST_SVN_DRIVE%\\Seating"},
        "repository_workspaces": ["%TEST_SVN_DRIVE%\\Knoll\\_repository"],
        "pdm_server": "ignored",          # not overridable: the database is chosen through the presets
        "bogus": 1,
    }), encoding="utf-8")
    monkeypatch.setenv("MK_WORKBENCH_CONFIG", str(settings))

    config = AppConfig.load()

    assert config.repository_browser_roots == {"Seating": str(tmp_path / "Seating")}
    assert config.repository_workspaces == [str(tmp_path / "Knoll" / "_repository")]
    assert config.pdm_server == "DBCHIP12V"
    assert any("bogus" in w for w in config.config_warnings) and any("pdm_server" in w for w in config.config_warnings)
    assert rw.check_location(config.repository_browser_roots["Seating"]).connected


def test_bad_or_missing_override_file_never_breaks_startup(tmp_path, monkeypatch):
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    config = AppConfig.load(broken)
    assert config.repository_browser_roots == AppConfig().repository_browser_roots and config.config_warnings
    assert AppConfig.load(tmp_path / "absent.json").config_warnings


def test_other_computer_without_the_paths_shows_unavailable_not_connected(app, tmp_path):
    from ui.pages.module_home_page import ModuleHomePage

    config = AppConfig(
        repository_browser_roots={"Seating": str(tmp_path / "nope" / "Seating"), "Tables": str(tmp_path / "nope" / "Tables")},
        repository_workspaces=[str(tmp_path / "nope" / "_repository")],
    )
    context = ApplicationContext(config)
    page = ModuleHomePage(context)
    text = _status_text(page._repository_status)
    assert text.startswith("Not connected")
    assert not page._repository_status._dot.styleSheet().startswith("background:#27A032")
    assert "Folder not found" in page._repository_status.toolTip()
    # configured paths are reported, never rewritten
    assert config.repository_browser_roots["Seating"] == str(tmp_path / "nope" / "Seating")


def test_connected_only_after_the_location_is_validated(app, tmp_path):
    from ui.pages.module_home_page import ModuleHomePage

    (tmp_path / "Seating").mkdir()
    config = AppConfig(repository_browser_roots={"Seating": str(tmp_path / "Seating"), "Tables": str(tmp_path / "gone")},
                       repository_workspaces=[])
    page = ModuleHomePage(ApplicationContext(config))
    assert _status_text(page._repository_status) == "Seating"
    assert page._repository_status._dot.styleSheet().startswith("background:#27A032")


def test_location_states(tmp_path, monkeypatch):
    folder = tmp_path / "ok"
    folder.mkdir()
    a_file = tmp_path / "file.txt"
    a_file.write_text("x")
    assert rw.check_location(folder).connected
    assert rw.check_location(tmp_path / "missing").state == rw.MISSING
    assert rw.check_location("").state == rw.MISSING
    assert rw.check_location(a_file).state in (rw.NOT_A_FOLDER, rw.MISSING)   # Windows reports either for a file

    def denied(_path):
        raise PermissionError(13, "Access is denied")

    def no_network(_path):
        error = OSError(53, "The network path was not found")
        error.winerror = 53
        raise error

    monkeypatch.setattr(rw.os, "scandir", denied)
    status = rw.check_location(folder)
    assert status.state == rw.NO_PERMISSION and "Access denied" in status.detail
    monkeypatch.setattr(rw.os, "scandir", no_network)
    assert rw.check_location(r"\\server\share\_repository").state == rw.UNREACHABLE


def test_permission_error_is_not_reported_as_connected_in_status_strip(app, tmp_path, monkeypatch):
    from ui.pages.module_home_page import ModuleHomePage

    (tmp_path / "Seating").mkdir()
    config = AppConfig(repository_browser_roots={"Seating": str(tmp_path / "Seating")}, repository_workspaces=[])
    monkeypatch.setattr(rw.os, "scandir", lambda _p: (_ for _ in ()).throw(PermissionError(13, "Access is denied")))
    page = ModuleHomePage(ApplicationContext(config))
    assert "Access denied" in _status_text(page._repository_status)


# ------------------------------------------------------------------ Issue 3: Knoll workspace
def _knoll_workspace(base, *, nested=True):
    workspace = base / "KnollSVN" / "Staging" / "Knoll" / "_repository"
    workspace.mkdir(parents=True)
    root = workspace / "kn" if nested else workspace          # folder name is not the manufacturer
    root.mkdir(exist_ok=True)
    write_plain_range(root, "saarinen", [("SA1", "KNL", "SA", "Saarinen Chair"), ("SA2", "KNL", "SA", "Saarinen Table")])
    write_plain_range(root, "womb", [("WB1", "KNL", "WB", "Womb Chair")])
    return workspace


def test_default_configuration_lists_the_hm_and_knoll_workspaces():
    config = AppConfig()
    assert config.knoll_repository_workspace == KNOLL_WORKSPACE
    assert list(config.manufacturer_workspaces) == ["HM", "Knoll"]
    assert config.hm_repository_workspace.endswith(r"HermanMiller\_repository")
    assert config.repository_workspaces == []                  # the extra-workspace list no longer carries Knoll


@pytest.mark.parametrize("nested", [True, False])
def test_knoll_workspace_is_recognised_and_manufacturer_discovered_from_data(tmp_path, nested):
    workspace = _knoll_workspace(tmp_path, nested=nested)
    info = rw.connect_workspace(workspace)
    assert info.connected
    assert info.manufacturers == ("KNL",)                      # taken from ocd_article, not from the path or a label
    assert len(info.catalogue_roots) == 1


def test_connecting_loads_the_knoll_manufacturer_context(tmp_path):
    workspace = _knoll_workspace(tmp_path)
    context = ApplicationContext(AppConfig(repository_workspaces=[str(workspace)]))
    info = context.connect_repository_workspace(str(workspace))
    assert context.repository_workspaces[str(workspace)] is info
    assert info.manufacturers == ("KNL",)


def test_knoll_programs_join_the_catalogue_beside_existing_manufacturers(tmp_path):
    from services.ocd_engine.workspace_catalogue import WorkspaceCatalogueService

    workspace = _knoll_workspace(tmp_path)
    hmx = tmp_path / "hmx"
    hmx.mkdir()
    write_plain_range(hmx, "aeron", [("AE1", "HM", "AE", "Aeron")])
    service = WorkspaceCatalogueService(hmx, [str(workspace), str(tmp_path / "unavailable")])

    scan = service.scan()

    assert scan.manufacturers() == ["HM", "KNL"]
    assert [p.program for p in scan.programs_for("HM")] == ["aeron"]            # existing manufacturer unchanged
    assert [p.program for p in scan.programs_for("KNL")] == ["saarinen", "womb"]
    assert service.infos[str(workspace)].manufacturers == ("KNL",)
    assert not service.infos[str(tmp_path / "unavailable")].connected
    assert service.list_articles(scan.programs_for("KNL")[0])[0].label == "Saarinen Chair"


def test_existing_roots_alone_discover_exactly_what_they_did_before(tmp_path):
    from services.ocd_engine.catalogue import OcdCatalogueService
    from services.ocd_engine.workspace_catalogue import WorkspaceCatalogueService

    hmx = tmp_path / "hmx"
    hmx.mkdir()
    write_plain_range(hmx, "aeron", [("AE1", "HM", "AE", "Aeron")])
    plain = OcdCatalogueService(hmx).scan()
    combined = WorkspaceCatalogueService(hmx, [str(tmp_path / "missing")]).scan()
    assert (plain.programs, plain.skipped) == (combined.programs, combined.skipped)


def test_missing_knoll_workspace_is_handled_gracefully(tmp_path):
    from services.ocd_engine.workspace_catalogue import WorkspaceCatalogueService

    missing = tmp_path / "KnollSVN" / "Staging" / "Knoll" / "_repository"
    info = rw.connect_workspace(missing)
    assert not info.connected and info.status.state == rw.MISSING and info.manufacturers == ()

    hmx = tmp_path / "hmx"
    hmx.mkdir()
    write_plain_range(hmx, "aeron", [("AE1", "HM", "AE", "Aeron")])
    service = WorkspaceCatalogueService(hmx, [str(missing)])
    assert service.scan().manufacturers() == ["HM"]
    assert service.fingerprint()


def test_inaccessible_knoll_workspace_is_reported_without_failing_others(tmp_path, monkeypatch):
    workspace = _knoll_workspace(tmp_path)
    real = os.scandir

    def selective(path):
        if str(path).startswith(str(workspace)):
            raise PermissionError(13, "Access is denied")
        return real(path)

    monkeypatch.setattr(rw.os, "scandir", selective)
    info = rw.connect_workspace(workspace)
    assert not info.connected and info.status.state == rw.NO_PERMISSION and info.manufacturers == ()


def test_only_missing_everything_still_raises_the_primary_error(tmp_path):
    from services.ocd_engine.catalogue import CatalogueError
    from services.ocd_engine.workspace_catalogue import WorkspaceCatalogueService

    service = WorkspaceCatalogueService(tmp_path / "no_hmx", [str(tmp_path / "no_knoll")])
    with pytest.raises(CatalogueError):
        service.scan()


def test_configured_knoll_path_is_never_rewritten(tmp_path):
    config = AppConfig(repository_workspaces=[str(tmp_path / "absent")])
    context = ApplicationContext(config)
    context.connect_repository_workspace(config.repository_workspaces[0])
    assert config.repository_workspaces == [str(tmp_path / "absent")]
