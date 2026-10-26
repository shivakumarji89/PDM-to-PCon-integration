"""Export button workflow: gating, confirmation, background run, cancel and result states.

The job and worker are replaced by controllable fakes; nothing connects to a database.
"""
from __future__ import annotations

import pytest

from services.syteline_export.job import ExportResult
from tests.test_syteline_export_page import make_page


class FakeJob:
    def __init__(self, config, policy):
        self.config, self.policy, self.cancelled = config, policy, False

    def cancel(self):
        self.cancelled = True

    def execute(self):
        return ExportResult(status="success", message="ok")


@pytest.fixture
def page(monkeypatch, tmp_path):
    page = make_page(monkeypatch)
    page.pdm_user_id.setText("123")
    page._load_database_choices()
    page.output_directory.setText(str(tmp_path))
    page.jobs, page.workers, page.dialogs = [], [], []
    monkeypatch.setattr(page, "_confirm_export", lambda config: True)
    monkeypatch.setattr(page, "_offer_take_over", lambda holder: True)
    monkeypatch.setattr(page, "_show_result_message", lambda level, title, text: page.dialogs.append((level, title, text)))

    def make_job(config, policy, signals):
        job = FakeJob(config, policy)
        page.jobs.append(job)
        return job
    monkeypatch.setattr(page, "_make_job", make_job)
    monkeypatch.setattr(page, "_run_in_background", lambda worker: page.workers.append(worker))
    return page


def test_opening_the_page_never_starts_an_export(page):
    assert page._job is None and page.jobs == [] and page.workers == []
    assert page.export.isEnabled() and not page.cancel_export.isEnabled()


@pytest.mark.parametrize("tab", [1, 2, 3])
def test_export_is_disabled_on_tabs_whose_exporter_is_not_ported(page, tab):
    page.tabs.setCurrentIndex(tab)
    assert not page.export.isEnabled()
    assert "not ported" in page.export.toolTip()
    page._start_export()
    assert page.jobs == []
    page.tabs.setCurrentIndex(0)
    assert page.export.isEnabled()


def test_invalid_setup_does_not_start_and_reports_why(page):
    page.output_directory.setText("")
    page._start_export()
    assert page.jobs == [] and "choose an existing output folder" in page.status.text()


def test_declining_the_confirmation_starts_nothing(page, monkeypatch):
    monkeypatch.setattr(page, "_confirm_export", lambda config: False)
    page._start_export()
    assert page.jobs == [] and page._job is None and "not started" in page.status.text()


def test_start_runs_in_background_and_locks_conflicting_controls(page):
    page._start_export()
    assert len(page.jobs) == 1 and page.jobs[0].policy == "refuse" and len(page.workers) == 1
    assert not page.export.isEnabled() and page.cancel_export.isEnabled()
    assert not page.validate_setup.isEnabled() and not page.load_database_choices.isEnabled()
    page._start_export()                      # repeated click while running is ignored
    assert len(page.jobs) == 1
    assert page._elapsed_timer.isActive()


def test_cancel_requests_cancellation_and_disables_itself(page):
    page._start_export()
    page._cancel_running_export()
    assert page.jobs[0].cancelled and not page.cancel_export.isEnabled()
    assert "Cancelling" in page.status.text()


def test_cancel_waits_for_worker_and_discards_queued_blocked_retry(page):
    page._start_export()
    page._cancel_running_export()
    page._on_export_status("queued before cancellation")
    assert "Cancelling" in page.status.text()
    page._start_export()
    assert len(page.jobs) == 1 and not page.export.isEnabled()
    page._on_export_finished(ExportResult(status="blocked", message="locked", lock_holder="alice"))
    assert len(page.jobs) == 1  # A queued blocked result must not start a take-over.
    assert "cancelled" in page.status.text().lower()
    assert page.export.isEnabled()


def finish(page, **kw):
    page._on_export_finished(ExportResult(**kw))


def test_success_state_is_distinct_and_restores_controls(page, tmp_path):
    page._start_export()
    finish(page, status="success", message="Export completed successfully.", files=("a", "b"))
    assert "Export completed: 2 file(s)" in page.status.text()
    assert page.dialogs[-1][0] == "info"
    assert page.export.isEnabled() and not page.cancel_export.isEnabled() and not page._elapsed_timer.isActive()


def test_completed_with_errors_is_a_warning_listing_problems(page):
    page._start_export()
    finish(page, status="completed_with_errors", message="m", files=("a",), errors=tuple(f"[stage 9] boom {i}" for i in range(7)))
    assert "WITH ERRORS (7)" in page.status.text()
    level, title, text = page.dialogs[-1]
    assert level == "warning" and "boom 0" in text and "2 more" in text


def test_cancelled_and_failed_states_say_nothing_was_published(page):
    page._start_export()
    finish(page, status="cancelled", message="Export cancelled; no output was published.")
    assert "cancelled" in page.status.text().lower() and page.dialogs[-1][0] == "info"
    page._start_export()
    finish(page, status="failed", message="db down", stage="17.2a", errors=("x",))
    assert "FAILED (stage 17.2a): db down" in page.status.text() and page.dialogs[-1][0] == "error"


def test_blocked_by_lock_offers_take_over_and_relaunches_with_that_policy(page):
    page._start_export()
    finish(page, status="blocked", message="alice is currently extracting", lock_holder="alice")
    assert [j.policy for j in page.jobs] == ["refuse", "take_over"] and page._job is page.jobs[1]


def test_blocked_by_lock_declined_take_over_stays_idle(page, monkeypatch):
    monkeypatch.setattr(page, "_offer_take_over", lambda holder: False)
    page._start_export()
    finish(page, status="blocked", message="alice is currently extracting", lock_holder="alice")
    assert len(page.jobs) == 1 and page._job is None and page.export.isEnabled()


def test_worker_always_emits_exactly_one_finished_even_if_the_job_crashes():
    from ui.pages.syteline_export_worker import ExportSignals, ExportWorker

    class Crashing:
        def execute(self):
            raise RuntimeError("boom")

    class Fine:
        def execute(self):
            return ExportResult(status="success", message="ok")

    outcomes = {}
    for name, job in (("crash", Crashing()), ("fine", Fine())):
        signals = ExportSignals()
        received = []
        signals.finished.connect(received.append)
        ExportWorker(job, signals).run()
        outcomes[name] = received
    assert [r.status for r in outcomes["crash"]] == ["failed"]
    assert "boom" in outcomes["crash"][0].message and outcomes["crash"][0].errors == ("RuntimeError: boom",)
    assert [r.status for r in outcomes["fine"]] == ["success"]


# ------------------------------------------------------------------ metadata loads off the UI thread
@pytest.fixture
def async_page(monkeypatch):
    page = make_page(monkeypatch)
    page._sync_metadata = False
    started = []
    from PySide6.QtCore import QThreadPool
    monkeypatch.setattr(QThreadPool.globalInstance(), "start", lambda worker: started.append(worker), raising=False)
    page.started = started
    return page


def test_database_choices_are_fetched_by_a_worker_and_applied_on_completion(async_page):
    page = async_page
    page.pdm_user_id.setText("123")
    page._load_database_choices()
    assert len(page.started) == 1 and not page.load_database_choices.isEnabled()
    assert page.site.count() == 0                     # nothing applied until the worker finishes
    page.started[0].run()
    assert page.site.currentData() == 1 and page.catalogue.currentData() == 10
    assert page.load_database_choices.isEnabled() and "Loaded 1 sites" in page.status.text()
    assert len(page.started) == 2                     # product codes follow, also off the UI thread
    page.started[1].run()
    assert page.product_line.currentData() == 8


def test_database_choices_failure_is_reported_and_reenables_loading(async_page, monkeypatch):
    page = async_page
    monkeypatch.setattr(page.metadata_service, "sites", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    page._load_database_choices()
    page.started[0].run()
    assert "could not be loaded: db down" in page.status.text() and page.load_database_choices.isEnabled()


def test_a_superseded_metadata_result_is_discarded(async_page):
    page = async_page
    page.pdm_user_id.setText("123")
    page._load_database_choices()
    page.load_database_choices.setEnabled(True)
    page._load_database_choices()                     # a newer request replaces the first
    first, second = page.started
    second.run()
    assert page.site.currentData() == 1
    page.site.clear()
    first.run()                                       # late arrival of the stale request
    assert page.site.count() == 0                     # not applied


def test_invalid_user_id_is_rejected_before_any_fetch(async_page):
    async_page.pdm_user_id.setText("abc")
    async_page._load_database_choices()
    assert async_page.started == [] and "positive integer" in async_page.status.text()
