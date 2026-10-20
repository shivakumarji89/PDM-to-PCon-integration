"""Guarded staging persistence and the opt-in build step. Temporary fixtures only - never a real repository."""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from core.application_context import ApplicationContext
from core.config import AppConfig
from services.metatype import staged_writer
from services.metatype.article_edit_session import ArticleEditSession
from services.metatype.article_write_plan import plan_article_edits
from services.metatype.build_step import plan_build, run_build
from services.metatype.staged_writer import (
    StagingAuthorization, apply_plan, load_authorization, plan_fingerprint, rollback, sha256, verify_destination,
)
from tests.test_metatype_write_contract import K1, K2, make_series


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def world(tmp_path):
    """Production working copy and a distinct staging working copy holding identical series data."""
    prod_wc, stage_wc = tmp_path / "prod", tmp_path / "stage"
    for wc in (prod_wc, stage_wc):
        (wc / ".svn").mkdir(parents=True)
        (wc / "hmx").mkdir()
        make_series(wc / "hmx")
    return {"prod": prod_wc / "hmx", "stage": stage_wc / "hmx", "backups": tmp_path / "backups", "tmp": tmp_path}


def article_file(root: Path) -> Path:
    return root / "demo" / "1" / "go_articles.csv"


def make_plan(root):
    context = ApplicationContext(AppConfig(metatype_repository_root=str(root)))
    session = ArticleEditSession(context.metatype_article_service.reconcile("demo", root=root))
    session.set_value(K2, "id", "MT_B")
    session.set_value(K1, "chprm_key", "CHP_A, CHP_B")
    return session, plan_article_edits(session)


def auth_for(world):
    return StagingAuthorization(world["stage"], world["prod"], "owner")


# -- authorisation is absent unless fully configured ------------------------------------------------------------------
def test_default_config_authorises_nothing(world):
    cfg = AppConfig()
    assert cfg.metatype_staging_root == "" and cfg.metatype_build_authorised is False
    auth, problems = load_authorization(cfg.metatype_staging_root, cfg.metatype_repository_root, cfg.metatype_staging_authorised_by)
    assert auth is None and len(problems) == 2
    assert load_authorization(str(world["stage"]), str(world["prod"]), "")[0] is None        # root without an authoriser
    assert load_authorization("", str(world["prod"]), "owner")[0] is None                    # authoriser without a root
    assert load_authorization(str(world["stage"]), str(world["prod"]), "owner")[0] is not None


def test_destination_must_be_distinct_from_production(world):
    prod = world["prod"]
    assert verify_destination(StagingAuthorization(prod, prod, "o"))
    assert verify_destination(StagingAuthorization(prod / "demo", prod, "o"))               # inside production
    assert verify_destination(StagingAuthorization(world["tmp"], prod, "o"))                # contains production
    assert verify_destination(StagingAuthorization(world["tmp"] / "missing", prod, "o"))
    same_wc = world["prod"].parent / "hmx2"
    same_wc.mkdir()
    problems = verify_destination(StagingAuthorization(same_wc, prod, "o"))
    assert any("same working copy" in p for p in problems)
    svn = world["stage"].parent / ".svn"
    assert any("Subversion metadata" in p for p in verify_destination(StagingAuthorization(svn, prod, "o")))
    assert verify_destination(auth_for(world)) == []


def test_unauthorised_apply_writes_nothing(world):
    _, plan = make_plan(world["prod"])
    before = {p: sha256(p.read_bytes()) for p in (article_file(world["prod"]), article_file(world["stage"]))}
    result = apply_plan(plan, None, "x", world["backups"])
    assert not result.success and "not authorised" in result.problems[0]
    assert before == {p: sha256(p.read_bytes()) for p in before} and not world["backups"].exists()


# -- the happy path ---------------------------------------------------------------------------------------------------
def test_apply_writes_only_to_staging_and_verifies(world):
    session, plan = make_plan(world["prod"])
    auth = auth_for(world)
    prod_before = sha256(article_file(world["prod"]).read_bytes())
    token = plan_fingerprint(plan, auth)
    result = apply_plan(plan, auth, token, world["backups"])
    assert result.success and all(f.written and f.verified for f in result.files), result.problems
    staged = article_file(world["stage"])
    assert staged.read_bytes() == plan.files[0].new and b"MT_B" in staged.read_bytes()
    assert sha256(article_file(world["prod"]).read_bytes()) == prod_before                  # production untouched
    assert Path(result.files[0].backup).read_bytes() == plan.files[0].original               # rollback copy exists
    assert (Path(result.backup_dir) / "manifest.json").is_file()
    assert not list(staged.parent.glob(".*.tmp")) and "Written and verified" in result.summary()
    assert session.pending_count == 2                                                         # nothing claims persistence of the source
    assert rollback(result) == [] and sha256(staged.read_bytes()) == sha256(plan.files[0].original)   # explicit rollback


def test_review_shows_exact_destination_and_token(world):
    _, plan = make_plan(world["prod"])
    auth = auth_for(world)
    text = staged_writer.review_text(plan, auth)
    assert str(article_file(world["stage"])) in text and plan_fingerprint(plan, auth) in text and "NOTHING has been written" in text


# -- refusals before any write ----------------------------------------------------------------------------------------
def test_wrong_confirmation_token_writes_nothing(world):
    _, plan = make_plan(world["prod"])
    staged = article_file(world["stage"])
    before = staged.read_bytes()
    result = apply_plan(plan, auth_for(world), "0000", world["backups"])
    assert not result.success and "does not match" in result.problems[0] and staged.read_bytes() == before


def test_source_hash_mismatch_and_concurrent_change_abort(world):
    _, plan = make_plan(world["prod"])
    auth = auth_for(world)
    token = plan_fingerprint(plan, auth)
    staged = article_file(world["stage"])
    staged.write_bytes(staged.read_bytes() + b"MT_Z;hmx;test;ART9;C9;\r\n")                  # staging copy diverged
    changed = staged.read_bytes()
    result = apply_plan(plan, auth, token, world["backups"])
    assert not result.success and "differs from the file the plan was computed from" in result.problems[0]
    assert staged.read_bytes() == changed and not world["backups"].exists()


def test_target_outside_staging_or_missing_is_refused(world):
    _, plan = make_plan(world["prod"])
    plan.files[0].path = str(world["tmp"] / "elsewhere.csv")
    assert "neither under" in apply_plan(plan, auth_for(world), "x", world["backups"]).problems[0]
    plan.files[0].path = str(world["prod"] / "demo" / "1" / "nope.csv")
    assert not apply_plan(plan, auth_for(world), "x", world["backups"]).success
    plan.files[0].path = str(world["prod"] / "demo" / "1" / "mt.inp_descr")
    assert "not a .csv" in apply_plan(plan, auth_for(world), "x", world["backups"]).problems[0]


def test_unverified_plan_and_backup_inside_tree_are_refused(world):
    _, plan = make_plan(world["prod"])
    auth = auth_for(world)
    assert not apply_plan(plan, auth, plan_fingerprint(plan, auth), world["stage"] / "bk").success
    bad = make_plan(world["prod"])[1]
    bad.files[0].verified = False
    assert "not verified" in apply_plan(bad, auth, "x", world["backups"]).problems[0]


# -- failure and rollback ---------------------------------------------------------------------------------------------
def test_write_failure_after_first_file_rolls_back(world, monkeypatch):
    make_series(world["prod"], name="demo2")
    make_series(world["stage"], name="demo2")
    context = ApplicationContext(AppConfig(metatype_repository_root=str(world["prod"])))
    plans = []
    for series in ("demo", "demo2"):
        session = ArticleEditSession(context.metatype_article_service.reconcile(series, root=world["prod"]))
        session.set_value(K2, "id", "MT_B")
        plans.append(plan_article_edits(session))
    merged = plans[0]
    merged.files.extend(plans[1].files)
    auth = auth_for(world)
    files = [article_file(world["stage"]), world["stage"] / "demo2" / "1" / "go_articles.csv"]
    originals = [f.read_bytes() for f in files]
    real_replace, calls = os.replace, []

    def flaky(src, dst):
        calls.append(dst)
        if len(calls) == 2:
            raise OSError("disk full")
        real_replace(src, dst)

    monkeypatch.setattr(staged_writer.os, "replace", flaky)
    result = apply_plan(merged, auth, plan_fingerprint(merged, auth), world["backups"])
    monkeypatch.undo()
    assert not result.success and result.rolled_back and "disk full" in result.problems[0]
    assert [f.read_bytes() for f in files] == originals and "rolled back" in result.summary()


def test_post_write_verification_failure_restores(world, monkeypatch):
    _, plan = make_plan(world["prod"])
    auth = auth_for(world)
    real = staged_writer._atomic_write
    monkeypatch.setattr(staged_writer, "_atomic_write", lambda t, d: real(t, d + b"#tamper\r\n") if d == plan.files[0].new else real(t, d))
    result = apply_plan(plan, auth, plan_fingerprint(plan, auth), world["backups"])
    assert not result.success and result.rolled_back and "re-read bytes differ" in result.problems[0]
    assert article_file(world["stage"]).read_bytes() == plan.files[0].original


def test_rollback_refuses_a_file_changed_after_writing(world):
    _, plan = make_plan(world["prod"])
    auth = auth_for(world)
    result = apply_plan(plan, auth, plan_fingerprint(plan, auth), world["backups"])
    staged = article_file(world["stage"])
    staged.write_bytes(staged.read_bytes() + b"#later\r\n")
    problems = rollback(result)
    assert problems and "changed after it was written" in problems[0] and b"#later" in staged.read_bytes()


# -- build step (never run here) --------------------------------------------------------------------------------------
class _Done:
    returncode, stdout, stderr = 0, "built", ""


def build_world(world):
    folder = world["stage"] / "demo" / "1"
    (folder / "ebmkdb.exe").write_bytes(b"MZ")
    return folder


def test_build_plan_needs_authorisation_and_confirmation(world):
    folder = build_world(world)
    auth = auth_for(world)
    assert "not been authorised" in plan_build(folder, auth, False).problems[0]
    assert not plan_build(folder, None, True).ok
    assert not plan_build(world["prod"] / "demo" / "1", auth, True).ok                     # production folder refused
    plan = plan_build(folder, auth, True)
    assert plan.ok and plan.command[1:] == ["mt.inp_descr", "demo.ebase"] and "NOT run" in plan.review_text() and plan.warnings
    calls = []
    runner = lambda *a, **k: calls.append((a, k)) or _Done()                               # noqa: E731
    assert not run_build(plan, "wrong", runner).ran and calls == []                       # no token -> never runs
    outcome = run_build(plan, plan.token, runner)
    assert outcome.ran and outcome.returncode == 0 and len(calls) == 1 and calls[0][1]["cwd"] == str(folder)


def test_build_refuses_when_the_database_changed_after_review(world):
    folder = build_world(world)
    plan = plan_build(folder, auth_for(world), True)
    (folder / "demo.ebase").write_bytes(b"new")
    runner = lambda *a, **k: pytest.fail("must not run")                                   # noqa: E731
    assert "changed since the review" in run_build(plan, plan.token, runner).problems[0]


# -- page integration -------------------------------------------------------------------------------------------------
def page_for(world, authorised, qapp):
    from ui.pages.metatype_creation_page import MetatypeCreationPage
    cfg = AppConfig(metatype_repository_root=str(world["prod"]),
                    metatype_staging_root=str(world["stage"]) if authorised else "",
                    metatype_staging_authorised_by="owner" if authorised else "")
    page = MetatypeCreationPage(ApplicationContext(cfg))
    page.series_combo.setCurrentIndex(page.series_combo.findData("demo"))
    page.load_series()
    page.articles_session.set_value(K2, "id", "MT_B")
    return page


def test_page_apply_is_disabled_without_authorisation(qapp, world):
    page = page_for(world, False, qapp)
    stage_before = article_file(world["stage"]).read_bytes()
    assert page.apply_to_staging(confirm=lambda text: pytest.fail("no prompt without authorisation")) is None
    assert "Writing is disabled" in page.articles_diagnostics.toPlainText()
    assert article_file(world["stage"]).read_bytes() == stage_before and page.articles_session.pending_count == 1


def test_page_apply_cancel_and_confirm(qapp, world):
    page = page_for(world, True, qapp)
    staged = article_file(world["stage"])
    before = staged.read_bytes()
    assert page.apply_to_staging(confirm=lambda text: False, backup_root=world["backups"]) is None
    assert staged.read_bytes() == before and page.articles_session.pending_count == 1       # cancel keeps edits
    shown = []
    result = page.apply_to_staging(confirm=lambda text: shown.append(text) or True, backup_root=world["backups"])
    assert result.success and b"MT_B" in staged.read_bytes() and "Confirmation token" in shown[0]
    assert "Written and verified" in page.articles_diagnostics.toPlainText()
    assert page.articles_session.pending_count == 0 and page.articles_session.cell_state(K2, "id") == "written"
