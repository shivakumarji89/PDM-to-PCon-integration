"""Snapshot-aware catalogue refresh: the catalogue is loaded - and its progress popup shown - only when the
repository content differs from the catalogue now displayed.

``loads`` counts catalogue reads (``OcdCatalogueService.scan``); ``popups`` counts the progress popup being shown.
"""
from __future__ import annotations

import os
import shutil
from unittest.mock import Mock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

from services.ocd_engine.catalogue import OcdCatalogueService, forget_loaded, recall_loaded
from tests.ocd_engine.ocd_repo_fixture import write_plain_range
import ui.dialogs.progress_dialog as progress_module
import ui.pages.pcon_article_obx_generator_page as page_module
from ui.pages.pcon_article_obx_generator_page import PconArticleObxGeneratorPage


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    forget_loaded()
    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(page_module.QMessageBox, name, Mock())
    monkeypatch.setattr(page_module.QMessageBox, "question", Mock(return_value=QMessageBox.StandardButton.Yes))
    yield
    forget_loaded()


def drain() -> None:
    for _ in range(6):                    # a check can start a load, which is another pooled task
        assert QThreadPool.globalInstance().waitForDone(10000)
        for _ in range(30):
            QCoreApplication.processEvents()


def make_root(base, name="hmx"):
    root = base / name
    root.mkdir()
    write_plain_range(root, "demo", [("CHAIR1", "MK", "DM", "Demo Chair"), ("STOOL1", "MK", "DM", "Demo Stool")])
    write_plain_range(root, "office", [("DESK1", "EG", "AX", "Desk A")])
    return root


class Probe:
    """Counts catalogue reads and progress popups for one page."""

    def __init__(self, monkeypatch, root):
        self.service = OcdCatalogueService(root)
        self.popups = 0
        real_show = progress_module.ProgressDialog.show

        def counted(dialog):
            self.popups += 1
            return real_show(dialog)

        monkeypatch.setattr(progress_module.ProgressDialog, "show", counted)

    @property
    def loads(self):
        return self.service.scans


def open_page(probe):
    page = PconArticleObxGeneratorPage(context=None, catalogue=probe.service)
    drain()
    return page


def close(page):
    dialog = getattr(page, "_progress_dialog", None)
    if dialog is not None:
        dialog.hide()
    page.deleteLater()
    drain()


def programs(page):
    return page._scan.programs if page._scan is not None else []


def add_range(root):
    write_plain_range(root, "extra", [("NEW1", "MK", "", "New")])


# ------------------------------------------------------------------ 1-2: unchanged data
def test_the_first_open_loads_once_and_repeated_checks_load_nothing(tmp_path, monkeypatch):
    probe = Probe(monkeypatch, make_root(tmp_path))
    page = open_page(probe)
    assert probe.loads == 1 and probe.popups == 1 and len(programs(page)) == 2
    for _ in range(5):
        page._check_catalogue()
        drain()
    page._poll_catalogue()
    drain()
    assert probe.loads == 1 and probe.popups == 1
    assert "up to date" in page._catalogue_status.text()
    close(page)


def test_a_second_page_instance_on_unchanged_data_loads_nothing_and_shows_no_popup(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    first = Probe(monkeypatch, root)
    close(open_page(first))
    again = Probe(monkeypatch, root)                      # new service object, new page object, same repository
    second = open_page(again)
    assert again.loads == 0 and again.popups == 0
    assert programs(second) == recall_loaded(root).programs and second._manufacturer.count() == 2
    close(second)


# ------------------------------------------------------------------ 3: switching workflows
def test_showing_and_hiding_the_page_does_not_refresh_unchanged_data(tmp_path, monkeypatch):
    probe = Probe(monkeypatch, make_root(tmp_path))
    page = open_page(probe)
    for _ in range(3):                                    # switching to another workflow and back
        page.show()
        drain()
        page.hide()
        drain()
    assert probe.loads == 1 and probe.popups == 1
    close(page)


def test_the_poll_does_nothing_while_the_page_is_not_the_visible_workflow(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    probe = Probe(monkeypatch, root)
    page = open_page(probe)
    add_range(root)                                       # the repository changes while the page is hidden
    checks_before = probe.service.fingerprints
    page._poll_catalogue()
    drain()
    assert probe.service.fingerprints == checks_before and probe.loads == 1     # hidden: not even checked
    page.show()
    drain()
    assert probe.loads == 2 and any(p.program == "extra" for p in programs(page))   # picked up on show
    close(page)


# ------------------------------------------------------------------ 4-5: a genuine change
def test_a_repository_change_triggers_exactly_one_update_then_none(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    probe = Probe(monkeypatch, root)
    page = open_page(probe)
    assert probe.loads == 1 and probe.popups == 1
    add_range(root)
    page._check_catalogue()
    drain()
    assert probe.loads == 2 and probe.popups == 2
    assert any(p.program == "extra" for p in programs(page))
    assert "updated automatically" in page._catalogue_status.text()
    for _ in range(3):                                    # the same change must not be detected again
        page._check_catalogue()
        drain()
    assert probe.loads == 2 and probe.popups == 2
    close(page)


def test_a_changed_article_row_in_an_existing_range_is_detected(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    probe = Probe(monkeypatch, root)
    page = open_page(probe)
    shutil.rmtree(root / "demo")
    write_plain_range(root, "demo", [("CHAIR1", "MK", "DM", "Demo Chair"), ("STOOL1", "MK", "DM", "Demo Stool"),
                                     ("TABLE9", "MK", "DX", "Table")])
    page._check_catalogue()
    drain()
    assert probe.loads == 2 and next(p for p in programs(page) if p.program == "demo").article_count == 3
    close(page)


# ------------------------------------------------------------------ 6: failed / cancelled update can be retried
@pytest.mark.parametrize("error", [OSError("share unavailable"), "cancel"])
def test_a_failed_or_cancelled_update_is_retried_by_the_next_check(tmp_path, monkeypatch, error):
    from core.cancellation import OperationCancelled
    if error == "cancel":
        error = OperationCancelled("cancelled")
    root = make_root(tmp_path)
    probe = Probe(monkeypatch, root)
    page = open_page(probe)
    add_range(root)
    real_scan = probe.service.scan
    monkeypatch.setattr(probe.service, "scan", Mock(side_effect=error))
    page._check_catalogue()
    drain()
    assert not any(p.program == "extra" for p in programs(page))
    monkeypatch.setattr(probe.service, "scan", real_scan)
    page._check_catalogue()                               # nothing was recorded for the failure: this retries
    drain()
    assert any(p.program == "extra" for p in programs(page))
    loads = probe.loads
    page._check_catalogue()
    drain()
    assert probe.loads == loads                           # and the successful retry is final
    close(page)


# ------------------------------------------------------------------ 7: what the comparison is made of
def test_the_fingerprint_ignores_paths_instances_and_timestamps_but_not_content(tmp_path):
    one = make_root(tmp_path, "one")
    two = tmp_path / "elsewhere" / "temp_copy"
    shutil.copytree(one, two)
    fingerprint = OcdCatalogueService(one).fingerprint()
    assert OcdCatalogueService(one).fingerprint() == fingerprint            # a new instance
    assert OcdCatalogueService(two).fingerprint() == fingerprint            # another path, identical data
    article = next((one / "demo").rglob("ocd_article.csv"))
    original = article.read_bytes()
    article.write_bytes(original)                                           # rewritten: new mtime, same content
    assert OcdCatalogueService(one).fingerprint() == fingerprint
    article.write_bytes(original + b"X1;C;MK;DM;T1;;0;0;1;C62;U1\r\n")
    assert OcdCatalogueService(one).fingerprint() != fingerprint            # content changed


def test_a_range_gaining_data_changes_the_fingerprint_and_it_is_deterministic(tmp_path):
    root = make_root(tmp_path)
    (root / "assets").mkdir()
    service = OcdCatalogueService(root)
    before = service.fingerprint()
    assert service.fingerprint() == before
    write_plain_range(root, "assets", [("A1", "MK", "", "A")])
    assert service.fingerprint() != before


def test_the_check_does_not_read_the_catalogue(tmp_path):
    service = OcdCatalogueService(make_root(tmp_path))
    service.fingerprint()
    assert service.scans == 0
