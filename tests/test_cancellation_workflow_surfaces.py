from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QCoreApplication, QThreadPool
from PySide6.QtWidgets import QApplication

from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope, checkpoint
from models.article import Article
from models.product import Product
from models.snapshot import Snapshot
from services.article_obx.article_permutation_service import ArticlePermutationService
from services.sif_validation_service import SifLine, SifValidationService
from ui.pages.article_obx_generator_page import ArticleObxGeneratorPage
from ui.pages.cet_sif_validation_page import CetSifValidationPage
from ui.widgets.repository_workspace import RepositoryWorkspace


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def drain():
    assert QThreadPool.globalInstance().waitForDone(5000)
    QCoreApplication.processEvents()


def test_sif_monitor_cancels_real_worker_stream_and_allows_retry(monkeypatch):
    monkeypatch.setattr("ui.pages.cet_sif_validation_page.QMessageBox.information", Mock())
    started, release = Event(), Event()
    calls = []

    def validate(*args, **kwargs):
        calls.append(1)
        started.set()
        assert release.wait(5)
        checkpoint()
        return {}, []

    page = CetSifValidationPage(SimpleNamespace(
        sif_validation_service=SimpleNamespace(validate=validate),
    ))
    page._lines = [SifLine(seq=1, base="A")]
    page._on_launch()
    assert started.wait(5)
    assert not page._load_btn.isEnabled()
    page._on_launch()
    page._monitor._cancel_btn.click()
    release.set()
    drain()
    assert calls == [1]
    assert page._results == []
    assert page._launch_btn.isEnabled() and page._load_btn.isEnabled()
    assert "Cancelled" in page._file_label.text()
    page._on_launch()
    drain()
    assert calls == [1, 1]
    assert not page._validation_run.active
    page.deleteLater()


def test_permutation_monitor_stops_cpu_work_without_publishing_and_can_retry():
    started, release = Event(), Event()
    snapshot = Snapshot(product=Product(code="P"), articles=[Article(id="a", code="A")])
    calls = []

    def build(*args, **kwargs):
        calls.append(1)
        started.set()
        assert release.wait(5)
        checkpoint()
        return []

    context = SimpleNamespace(
        qa_snapshot=snapshot, ensure_qa_snapshot=lambda: snapshot,
        article_permutation_service=SimpleNamespace(build=build),
    )
    page = ArticleObxGeneratorPage(context)
    page._build_permutations()
    assert started.wait(5)
    page._build_dialog._cancel_btn.click()
    page._build_permutations()  # cannot overlap a worker still draining
    release.set()
    drain()
    assert calls == [1]
    assert page._permutations == [] and page._build_button.isEnabled()
    assert "Cancelled" in page._status.text()
    page._build_permutations()
    drain()
    assert calls == [1, 1]
    page.deleteLater()


def test_repository_cancel_waits_for_mdb_bridge_then_skips_mapping_and_publication():
    started, release = Event(), Event()
    old = Snapshot(product=Product(code="old"))
    inspector = Mock(return_value={"ocd_path": "example.mdb", "name": "new"})
    mapper = Mock()
    register = Mock()

    def read(*args, **kwargs):
        started.set()
        assert release.wait(5)
        return SimpleNamespace(table_counts={})

    context = SimpleNamespace(
        mdb_import_snapshot=old, register_mdb_import_snapshot=register,
        maintenance_repository_link_service=SimpleNamespace(inspect_repository=inspector),
        mdb_reverse_engineering_service=SimpleNamespace(read=read, import_snapshot=mapper),
    )
    page = RepositoryWorkspace(context)
    page._start_repository_extraction("example", 0)
    assert started.wait(5)
    page._repository_progress_dialog._cancel_btn.click()
    release.set()
    drain()
    mapper.assert_not_called()
    register.assert_not_called()
    assert context.mdb_import_snapshot is old
    assert "Previous repository snapshot retained" in page._repository_status.text()
    assert not page._repository_run.active
    page.deleteLater()


def test_permutation_recursion_checks_between_values(monkeypatch):
    token = CancellationToken()
    dimensions = [SimpleNamespace(entity_id="p", name="P", values=[
        SimpleNamespace(id="v1", value="1"), SimpleNamespace(id="v2", value="2"),
    ])]
    visited = []

    def accept(value_id, constraints, selected):
        visited.append(value_id)
        token.request_cancel()
        return True

    monkeypatch.setattr(ArticlePermutationService, "_value_satisfies_hierarchy", accept)
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        ArticlePermutationService._property_combinations(dimensions, ())
    assert visited == ["v1"]


def test_sif_cancel_between_lines_stops_results():
    token = CancellationToken()
    seen = []

    def result(row):
        seen.append(row.seq)
        token.request_cancel()

    service = SifValidationService(None)
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        service._validate_group(
            "XXX", [SifLine(seq=1), SifLine(seq=2)], None, None, None,
            "25-Oct-2026", [0], 2, None, None, result,
        )
    assert seen == [1]
