"""Deterministic cancellation contracts across shared and workflow boundaries."""
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QThreadPool
from PySide6.QtWidgets import QApplication

from core.cancellation import (
    CancellationToken, OperationCancelled, cancellation_scope, checkpoint, commit,
)
from core.progress import ProgressReporter
from core.snapshot_manager import SnapshotManager
from models.article import Article
from models.product import Product
from models.snapshot import Snapshot
from repositories.pdm_repository import PDMRepository
from services.pdm_service import PDMService, ProductLoadResult
from services.pricing_service import PriceParams, PricingService
from ui.dialogs.progress_dialog import ProgressDialog
from ui.workers.background_task import BackgroundTask, ReportedTask


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def flush():
    QCoreApplication.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def outcomes(task):
    log = []
    for name in ("finished", "failed", "cancelled", "progress"):
        getattr(task.signals, name).connect(lambda value, key=name: log.append((key, value)))
    return log


def test_cancel_before_start_never_invokes_work():
    work = Mock()
    task = BackgroundTask(work)
    log = outcomes(task)
    task.cancel()
    task.cancel()
    task.run()
    assert [kind for kind, value in log] == ["cancelled"]
    work.assert_not_called()
    flush()


def test_worker_cancels_between_batches_drops_queued_progress_and_can_retry():
    started, release = Event(), Event()
    processed = []

    def work(emit):
        processed.append(1)
        emit(1)
        started.set()
        assert release.wait(5)
        checkpoint()
        processed.append(2)
        return processed

    task = BackgroundTask(work)
    log = outcomes(task)
    QThreadPool.globalInstance().start(task)
    assert started.wait(5)
    task.cancel()
    task.cancel()
    release.set()
    assert QThreadPool.globalInstance().waitForDone(5000)
    flush()
    assert processed == [1]
    assert [kind for kind, value in log] == ["cancelled"]
    retry = BackgroundTask(lambda emit: "retry")
    retry_log = outcomes(retry)
    retry.run()
    assert retry_log == [("finished", "retry")]
    flush()


@pytest.mark.parametrize("request_first", [True, False])
def test_commit_and_cancellation_have_a_single_winner(request_first):
    token = CancellationToken()
    if request_first:
        token.request_cancel()
        with pytest.raises(OperationCancelled):
            token.commit()
    else:
        token.commit()
        assert not token.request_cancel()
        token.checkpoint()


def test_late_cancel_after_worker_completion_keeps_success():
    task = BackgroundTask(lambda emit: "done")
    log = outcomes(task)
    thread = Thread(target=task.run)
    thread.start()
    thread.join(5)
    assert not thread.is_alive()
    task.cancel()
    flush()
    assert log == [("finished", "done")]


def test_genuine_failure_remains_a_failure():
    def work(emit):
        raise ValueError("database broken")

    task = BackgroundTask(work)
    log = outcomes(task)
    task.run()
    assert log == [("failed", "database broken")]
    flush()


def test_cancel_before_reporter_begin_is_not_lost():
    reporter = ProgressReporter()
    reporter.request_cancel()
    reporter.begin(100)
    with pytest.raises(OperationCancelled):
        reporter.checkpoint()
    finished, progress = [], []
    reporter.finished.connect(lambda *args: finished.append(args))
    reporter.progress_changed.connect(progress.append)
    reporter.finish(True, "not success")
    reporter.finish(True, "duplicate")
    assert finished == [(False, "Cancelled by user.")]
    assert 100 not in progress


def test_progress_dialog_cancel_and_close_have_distinct_scopes():
    reporter = ProgressReporter()
    dialog = ProgressDialog()
    dialog.bind(reporter)
    dialog.show()
    dialog.close()
    assert not reporter.is_cancelled()  # close is the documented hide-monitor action
    dialog._cancel_btn.click()
    assert reporter.is_cancelled()
    assert not dialog._cancel_btn.isEnabled()
    reporter.finish(False, "Cancelled")
    assert dialog._cancel_btn.text() == "Close"
    assert dialog._cancel_btn.isEnabled()
    dialog.deleteLater()
    flush()


def test_reported_task_survives_destroyed_owner_without_callbacks():
    owner = QObject()
    run = ReportedTask(owner)
    started, release = Event(), Event()
    callbacks = Mock()

    def work(emit):
        started.set()
        assert release.wait(5)
        checkpoint()

    reporter = run.reporter
    run.start(work, finished=callbacks, failed=callbacks, cancelled=callbacks)
    assert started.wait(5)
    shiboken6.delete(owner)
    assert reporter.is_cancelled() and shiboken6.isValid(reporter)
    release.set()
    assert QThreadPool.globalInstance().waitForDone(5000)
    flush()
    callbacks.assert_not_called()
    assert not shiboken6.isValid(run)
    assert not shiboken6.isValid(reporter)


def test_scopes_restore_outer_token():
    outer, inner = CancellationToken(), CancellationToken()
    with cancellation_scope(outer):
        with cancellation_scope(inner):
            inner.request_cancel()
            with pytest.raises(OperationCancelled):
                checkpoint()
        checkpoint()
    checkpoint()


def test_database_wait_finishes_current_call_but_never_fetches_or_starts_next_query():
    token = CancellationToken()
    entered, release = Event(), Event()
    cursor = Mock()

    def execute(*args):
        entered.set()
        assert release.wait(5)

    cursor.execute.side_effect = execute
    connection = Mock(cursor=lambda: cursor)
    repo = PDMRepository(SimpleNamespace())
    repo._pyodbc = SimpleNamespace(Error=type("DriverError", (Exception,), {}))
    result = []

    def work():
        with cancellation_scope(token):
            try:
                repo._execute("SELECT first", (), connection)
                repo._execute("SELECT second", (), connection)
            except OperationCancelled:
                result.append("cancelled")

    thread = Thread(target=work)
    thread.start()
    assert entered.wait(5)
    token.request_cancel()
    assert thread.is_alive()  # unsupported native call has NOT been forcibly stopped
    release.set()
    thread.join(5)
    assert not thread.is_alive()
    assert result == ["cancelled"]
    assert cursor.execute.call_count == 1
    cursor.fetchall.assert_not_called()


def test_pricing_cancel_after_base_query_preserves_complete_snapshot(monkeypatch):
    token = CancellationToken()
    previous = [object()]
    snapshot = Snapshot(product=Product(id="P"), articles=[Article(code="A")])
    snapshot.price_records = previous
    repo = Mock()
    repo.fetch_item_base_prices.side_effect = lambda *a, **k: token.request_cancel() or []
    monkeypatch.setattr("services.pricing_service.PDMRepository", lambda context: repo)
    service = PricingService(SimpleNamespace(active_snapshot=snapshot))
    monkeypatch.setattr(service, "_price_plan", lambda s: (["A", "B"], set()))
    monkeypatch.setattr(service, "_prefix_by_item", lambda s: {})
    monkeypatch.setattr(service, "target_currencies", lambda s, p: ["EUR"])
    batches = []
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        service.compute_streaming(PriceParams(currency="EUR"), snapshot, on_batch=batches.append)
    assert snapshot.price_records is previous
    assert batches == []
    repo.fetch_article_option_increment_prices.assert_not_called()
    repo.get_connection.return_value.close.assert_called_once()


def test_family_cancel_in_second_stage_keeps_previous_snapshot(monkeypatch):
    token = CancellationToken()
    manager = SnapshotManager()
    previous = manager.create_empty_snapshot(Product(id="old"))
    context = SimpleNamespace(snapshot_manager=manager, set_product_registry=Mock())
    service = PDMService(context)
    partial = Snapshot(product=Product(id="new"))
    monkeypatch.setattr(service, "load_family_articles",
                        lambda *a, **k: ProductLoadResult(True, "", partial, []))

    def details(*args, **kwargs):
        token.request_cancel()
        checkpoint()

    monkeypatch.setattr(service, "load_family_details", details)
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        service.load_family([Product(id="new")])
    assert manager.get_active_snapshot() is previous
    context.set_product_registry.assert_not_called()


def test_family_cancellation_during_engineering_never_publishes(monkeypatch):
    token = CancellationToken()
    manager = SnapshotManager()
    previous = manager.create_empty_snapshot(Product(id="old"))
    product = Product(id="new")
    new = Snapshot(product=product)

    def initialize(snapshot):
        assert snapshot is new
        token.request_cancel()
        checkpoint()

    context = SimpleNamespace(
        snapshot_manager=manager, set_product_registry=Mock(),
        engineering_initialization_service=SimpleNamespace(initialize=initialize),
    )
    service = PDMService(context)
    result = ProductLoadResult(True, "", new, [])
    monkeypatch.setattr(service, "load_family_articles", lambda *a, **k: result)
    monkeypatch.setattr(service, "load_family_details", lambda *a, **k: result)
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        service.load_family([product], initialize_engineering=True)
    assert manager.get_active_snapshot() is previous


def test_snapshot_cache_cancellation_removes_temporary_and_preserves_final(tmp_path, monkeypatch):
    token = CancellationToken()
    service = PDMService(SimpleNamespace())
    monkeypatch.setattr(service, "_SNAPSHOT_CACHE_DIR", tmp_path)
    path = tmp_path / "family.json"
    path.write_text("complete", encoding="utf-8")
    import services.pdm_service as module
    real_dumps = module.json.dumps

    def cancel_after_encoding(*args, **kwargs):
        result = real_dumps(*args, **kwargs)
        token.request_cancel()
        return result

    monkeypatch.setattr(module.json, "dumps", cancel_after_encoding)
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        service.save_family_snapshot(Snapshot(), "family")
    assert path.read_text(encoding="utf-8") == "complete"
    assert list(tmp_path.iterdir()) == [path]


def test_change_monitor_worker_outlives_closed_dialog_without_saving_watermark(monkeypatch):
    from ui.dialogs import pdm_changes_dialog as module

    entered, release = Event(), Event()
    save = Mock()
    monkeypatch.setattr(module, "_load_watermarks", lambda preset: {})
    monkeypatch.setattr(module, "_save_watermarks", save)

    def watermarks():
        entered.set()
        assert release.wait(5)
        return {"ProductId": 1}

    context = SimpleNamespace(
        config=SimpleNamespace(active_pdm_preset=lambda: "test"),
        pdm_service=SimpleNamespace(repository=SimpleNamespace(fetch_watermarks=watermarks)),
    )
    dialog = module.PdmChangesDialog(context)
    assert entered.wait(5)
    shiboken6.delete(dialog)
    release.set()
    assert QThreadPool.globalInstance().waitForDone(5000)
    flush()
    save.assert_not_called()


def test_loading_engine_returns_cancelled_without_next_query():
    from core.activity.service import ActivityService
    from services.loading.load_request import LoadRequest
    from services.loading.loading_engine import LoadingEngine

    token = CancellationToken()
    repo = Mock()
    repo.fetch_products_info.side_effect = lambda *a, **k: token.request_cancel() and []
    context = SimpleNamespace(
        activity_service=ActivityService(),
        pdm_service=SimpleNamespace(repository=repo),
    )
    with cancellation_scope(token):
        result = LoadingEngine(context).load(LoadRequest.for_product("p"))
    assert result.cancelled and not result.ok
    assert result.snapshot is None
    repo.fetch_products_attributes.assert_not_called()
    repo.get_connection.return_value.close.assert_called_once()
    assert context.activity_service.finished_snapshots()[0].status.value == "cancelled"


def test_add_family_cancels_working_copy_then_retry_inserts_only_once(monkeypatch):
    token = CancellationToken()
    manager = SnapshotManager()
    previous = manager.create_empty_snapshot(Product(id="old"))
    previous.articles = [Article(id="old", code="OLD")]
    row = SimpleNamespace(
        ProductId="new", ItemId="new", Item="NEW", Status=1, Notes="",
        IsSuperItem=False, WeightKilos=None, VolumeLitres=None,
        Height=None, Width=None, Depth=None,
    )
    repo = Mock()
    for name in (
        "fetch_products_info", "fetch_products_attributes", "fetch_products_options",
        "fetch_item_attribute_values", "fetch_item_components",
    ):
        getattr(repo, name).return_value = []
    repo.fetch_products_items.return_value = [row]

    def reduce(snapshot):
        assert snapshot is not previous
        assert [a.id for a in snapshot.articles] == ["old", "new"]
        token.request_cancel()
        checkpoint()

    context = SimpleNamespace(
        active_snapshot=previous, snapshot_manager=manager, set_product_registry=Mock(),
        engineering_reduction_service=SimpleNamespace(materialize_article_sets=reduce),
    )
    service = PDMService(context)
    service._repository = repo
    monkeypatch.setattr(service, "_fetch_prefix_length_rows", lambda *a: ([], []))
    monkeypatch.setattr(service, "_fetch_component_head_attrs", lambda *a: {})
    monkeypatch.setattr(service, "_fetch_option_increments", lambda *a: {})
    save = Mock()
    monkeypatch.setattr(service, "save_family_snapshot", save)
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        service.add_family_to_session([Product(id="new")])
    assert manager.get_active_snapshot() is previous
    assert [a.id for a in previous.articles] == ["old"]
    save.assert_not_called()
    context.set_product_registry.assert_not_called()
    context.engineering_reduction_service.materialize_article_sets = lambda s: []
    with cancellation_scope(CancellationToken()):
        result = service.add_family_to_session([Product(id="new")])
    assert result.ok
    assert [a.id for a in manager.get_active_snapshot().articles] == ["old", "new"]
    assert [a.id for a in previous.articles] == ["old"]
    save.assert_called_once()
