"""ExportJob safety contract: validation, lock, staging/publish, failure, cancel, cleanup.

The database is a synthetic scripted double (no real PDM). Item/option data are synthetic, so
these tests prove orchestration safety, not legacy output parity.
"""
import os
from decimal import Decimal
from pathlib import Path

import pytest

from services.syteline_export.config import SyteLineExportConfig
from services.syteline_export.job import ExportJob
from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.run import ExportRun

ITEM = dict(
    LongItem="ABC.1", Notes=None, LegacyItem=None, Height=None, Width=None, Depth=None,
    Item="ABC.1", Status=1, FSCCompliant=0, WeightKilos=1.5, VolumeLitres=2.5, Product="ABC",
    IsSuperProduct=False, ItemId=11, ShortDescription="A chair", AltDescription=None,
    MyBasePrice=Decimal("100.00"), ProductId=5, Product_Code="PC1", Description="Chairs",
    prodFS=None, ProductRangeId=1, rangeFS=None, ProductCategoryId=1, CommodityCode="CC",
    PriceCode="P1", ListPrice=None,
)
ITEM_SQL = "SELECT DISTINCT Item.Item AS LongItem"
LOCK_SQL = "SELECT ExtractUser FROM Site"


class FakeDb(ScriptedExportDb):
    """Unscripted statements return an empty result set (like an empty table)."""

    def _lookup(self, conn, sql, params):
        for needle, result in self.script.items():
            if needle in sql:
                return result(conn, sql, params) if callable(result) else result
        return []


def make_config(tmp_path, **overrides):
    values = dict(
        server="srv", database="db", output_directory=tmp_path, site="uk", site_id=1, catalogue_id=2,
        language_id=1, other_language_id=2, currency_id=3, currency="GBP", effective_date="2026-01-01",
        export_mode="syteline", active_only=True, options=frozenset({"products"}),
    )
    values.update(overrides)
    return SyteLineExportConfig(**values)


def make_job(tmp_path, script=None, **kwargs):
    script = {LOCK_SQL: [{"ExtractUser": None}], ITEM_SQL: [ITEM], **(script or {})}
    db = FakeDb(script)
    job = ExportJob(make_config(tmp_path), db, user_name="tester", **kwargs)
    return job, db


def staging_dirs(path: Path):
    return [p for p in path.iterdir() if p.name.startswith(".syteline-staging")]


def test_invalid_configuration_fails_before_any_database_or_file_activity(tmp_path):
    db = FakeDb({})
    config = make_config(tmp_path / "missing-folder")
    result = ExportJob(config, db).execute()
    assert result.status == "failed" and "Output folder must already exist" in result.message
    assert db.calls == []


def test_refuses_to_run_when_another_user_holds_the_site_lock(tmp_path):
    job, db = make_job(tmp_path, {LOCK_SQL: [{"ExtractUser": "alice"}]})
    result = job.execute()
    assert result.status == "blocked" and result.lock_holder == "alice"
    assert "alice" in result.message
    assert [c for c in db.calls if "UPDATE" in c[1]] == []   # nothing written
    assert staging_dirs(tmp_path) == [] and db.closed


def test_unreadable_lock_state_is_a_failure_not_a_guess(tmp_path):
    def boom(conn, sql, params):
        raise RuntimeError("db down")
    job, db = make_job(tmp_path, {LOCK_SQL: boom})
    result = job.execute()
    assert result.status == "failed" and "db down" in result.message and db.closed


def test_successful_run_publishes_atomically_and_releases_its_lock(tmp_path):
    job, db = make_job(tmp_path)
    result = job.execute()
    assert result.status == "success", (result.message, result.errors)
    names = {Path(f).name for f in result.files}
    assert {"PDMExport_item_data.txt", "PDMExport_material_data.txt"} <= names
    for f in result.files:
        assert Path(f).is_file() and Path(f).is_relative_to(tmp_path)
    assert staging_dirs(tmp_path) == []
    updates = [c for c in db.calls if c[1].startswith("UPDATE Site SET ExtractUser")]
    assert [("NULL" in u[1]) for u in updates] == [False, True]   # acquired once, released once
    assert db.closed
    item_file = next(Path(f) for f in result.files if f.endswith("PDMExport_item_data.txt"))
    assert "ABC.1\tno\tA chair" in item_file.read_bytes().decode("utf-8")


def test_failure_mid_run_publishes_nothing_keeps_previous_output_and_releases_lock(tmp_path):
    previous = tmp_path / "temp"
    previous.mkdir()
    (previous / "PDMExport_item_data.txt").write_text("PREVIOUS GOOD OUTPUT", encoding="utf-8")

    def explode(conn, sql, params):
        raise RuntimeError("connection reset")
    job, db = make_job(tmp_path, {"SELECT SLFeatureLength": explode, "exec PDMOptionDataReport": explode})
    # make the per-item option report fail like a dropped connection
    original_query = db.query

    def failing_query(conn, sql, params=(), *, stage=""):
        if "PDMOptionDataReport" in sql:
            raise RuntimeError("connection reset")
        return original_query(conn, sql, params, stage=stage)
    db.query = failing_query
    result = job.execute()
    assert result.status == "failed", (result.message, result.errors)
    assert any("connection reset" in e for e in result.errors)
    assert result.files == ()
    assert (previous / "PDMExport_item_data.txt").read_text(encoding="utf-8") == "PREVIOUS GOOD OUTPUT"
    assert staging_dirs(tmp_path) == []
    released = [c for c in db.calls if c[1].startswith("UPDATE Site SET ExtractUser = NULL")]
    assert len(released) == 1 and db.closed


def test_cancel_before_start_discards_everything(tmp_path):
    job, db = make_job(tmp_path)
    job.cancel()
    result = job.execute()
    assert result.status == "cancelled" and result.files == ()
    assert staging_dirs(tmp_path) == [] and not (tmp_path / "temp").exists()
    assert db.calls == []  # A run cancelled before starting never owns or modifies the lock.


def test_cancel_during_the_item_loop_stops_before_the_next_item(tmp_path):
    second = dict(ITEM, LongItem="ABC.2", Item="ABC.2", ItemId=12)
    job, db = make_job(tmp_path, {ITEM_SQL: [ITEM, second]})
    original_query = db.query
    seen_items = []

    def query_and_cancel(conn, sql, params=(), *, stage=""):
        if "PDMOptionDataReport" in sql:
            seen_items.append(params[0])
            job.cancel()                # user presses Cancel while the first item is processing
        return original_query(conn, sql, params, stage=stage)
    db.query = query_and_cancel
    result = job.execute()
    assert result.status == "cancelled" and result.files == ()
    assert seen_items == ["ABC.1"]      # the loop condition stopped before ABC.2
    assert staging_dirs(tmp_path) == []


def test_take_over_clears_the_dead_lock_first_and_releases_at_the_end(tmp_path):
    holder = {"user": "alice"}

    def lock_state(conn, sql, params):       # stateful: the take-over UPDATE clears the holder
        return [{"ExtractUser": holder["user"]}]
    job, db = make_job(tmp_path, {LOCK_SQL: lock_state}, lock_policy="take_over")
    original_execute = db.execute

    def execute(conn, sql, params=(), *, stage=""):
        if sql.startswith("UPDATE Site SET ExtractUser = NULL"):
            holder["user"] = None
        return original_execute(conn, sql, params, stage=stage)
    db.execute = execute
    result = job.execute()
    assert result.status == "success", (result.message, result.errors)
    updates = [c[1] for c in db.calls if c[1].startswith("UPDATE Site SET ExtractUser")]
    assert ["NULL" in u for u in updates] == [True, False, True]   # clear, acquire, release


def test_publish_failure_is_reported_and_cleans_up(tmp_path, monkeypatch):
    job, db = make_job(tmp_path)
    monkeypatch.setattr(ExportJob, "_publish", lambda self, staging: (_ for _ in ()).throw(OSError("disk full")))
    result = job.execute()
    assert result.status == "failed" and "disk full" in result.message
    assert staging_dirs(tmp_path) == [] and db.closed


def test_run_factory_receives_the_database_and_uses_staging_directory(tmp_path):
    captured = {}

    def factory(db):
        run = ExportRun(db)
        original = run.init_thread

        def spy(**kw):
            captured.update(kw)
            return original(**kw)
        run.init_thread = spy
        return run
    job, _ = make_job(tmp_path, run_factory=factory)
    job.execute()
    assert captured["directory"].endswith(os.sep)
    assert Path(captured["directory"]).name.startswith(".syteline-staging")
    assert Path(captured["directory"]).parent == tmp_path


@pytest.mark.parametrize("text,expected", [
    ("2026-10-19", "19-Oct-2026"), ("2026-01-05", "05-Jan-2026"), ("2026-12-31", "31-Dec-2026"),
    ("", ""), ("19-Oct-2026", "19-Oct-2026"), ("2026-13-01", "2026-13-01"),
])
def test_effective_date_is_passed_in_the_legacy_unambiguous_format(text, expected):
    from services.syteline_export.job import legacy_effective_date
    assert legacy_effective_date(text) == expected


def test_run_receives_the_legacy_date_format(tmp_path):
    captured = {}

    def factory(db):
        run = ExportRun(db)
        original = run.init_thread

        def spy(**kw):
            captured.update(kw)
            return original(**kw)
        run.init_thread = spy
        return run
    job, _ = make_job(tmp_path, run_factory=factory)
    job.execute()
    assert captured["effectiveDate"] == "01-Jan-2026"
