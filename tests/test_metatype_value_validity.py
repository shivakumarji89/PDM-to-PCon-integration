"""Template Step 4a: value-by-value article validity."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from core.application_context import ApplicationContext
from core.config import AppConfig
from models.metatype_creation import Severity, StepState, ValidityStatus, ValueValidityRow
from services.metatype.value_validity import parse_validity_cell, validate_value_validity
from tests.test_metatype_polymorphism_branch import build

ARTS = ["UPXSGA", "UPXSAA"]


def row(value, articles="", all_articles=False):
    return ValueValidityRow(value, all_articles, [a for a in articles.split(",") if a])


def codes(result, severity=None):
    return {f.code for f in result.findings if severity is None or f.severity is severity}


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "hmx"
    path.mkdir()
    return path


@pytest.fixture
def context(root):
    return ApplicationContext(AppConfig(metatype_repository_root=str(root)))


def make_ready(root, context, every_value=False):
    build(root)
    service = context.metatype_creation_service
    service.start("atlas")
    assert service.submit_property_identity("GATLAS_Surface", "Surface type").accepted
    assert service.submit_polymorphism_branch(ARTS, "unconditional", [], every_value).accepted
    return service


@pytest.fixture
def ready(root, context):
    return make_ready(root, context)          # Step 4 answered "exceptions exist"


# complete ------------------------------------------------------------------------------------------------------------
def test_template_example_table_is_complete(ready):
    result = ready.submit_value_validity(False, [
        row("1", "UPXSGA,UPXSAA"), row("2", "UPXSGA"), row("3", all_articles=True), row("4", "UPXSAA")])
    assert result.status is ValidityStatus.COMPLETE and result.accepted and not result.errors
    assert "VALUE_SET_NOT_VERIFIED" in codes(result, Severity.INFO)
    v = ready.validity
    assert v is result.validity and v.articles == ARTS and v.property_name == "GATLAS_Surface"
    assert [(r.value, r.all_articles, r.articles) for r in v.rows][2] == ("3", True, [])
    assert v.branch_confirmed_at == ready.branch.confirmed_at
    step = ready.stage_status().steps[4]
    assert step.key == "4a" and step.state is StepState.DONE and "4 value(s)" in step.detail


def test_no_exceptions_answer_is_complete_when_step4_said_the_same(root, context):
    service = make_ready(root, context, every_value=True)
    result = service.submit_value_validity(True)
    assert result.accepted and service.validity.rows == []
    assert service.stage_status().steps[4].state is StepState.DONE


def test_step4a_is_never_skipped_even_when_step4_reports_no_exceptions(root, context):
    service = make_ready(root, context, every_value=True)
    assert service.stage_status().steps[4].state is StepState.PENDING
    assert not service.can_start_children()


# incomplete ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("accepts, rows, expected", [
    (None, [], "VALIDITY_UNANSWERED"),
    (False, [], "VALUES_MISSING"),
    (False, [row("", "UPXSGA")], "VALUE_NAME_MISSING"),
    (False, [row("1", "UPXSGA"), row("2")], "VALIDITY_MISSING"),     # no implied "all"
])
def test_incomplete_answers(ready, accepts, rows, expected):
    result = ready.submit_value_validity(accepts, rows)
    assert result.status is ValidityStatus.INCOMPLETE and not result.accepted
    assert expected in codes(result, Severity.ERROR) and ready.validity is None
    assert ready.stage_status().steps[4].state is StepState.INCOMPLETE


# invalid ----------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("accepts, rows, expected", [
    (False, [row("1", "NOPE")], "ARTICLE_NOT_IN_STEP4"),
    (False, [row("1", "UPXSGA"), row("1", "UPXSAA")], "VALUE_DUPLICATE"),
    (False, [row("1", "UPXSGA", all_articles=True)], "VALIDITY_ALL_AND_ARTICLES"),
    (False, [row("1", "UPXSGA,UPXSGA")], "ARTICLE_DUPLICATE_IN_ROW"),
    (True, [], "VALIDITY_CONTRADICTS_STEP4"),                        # Step 4 said exceptions exist
])
def test_invalid_answers(ready, accepts, rows, expected):
    result = ready.submit_value_validity(accepts, rows)
    assert result.status is ValidityStatus.INVALID and expected in codes(result, Severity.ERROR)
    assert ready.validity is None and ready.stage_status().steps[4].state is StepState.INVALID


def test_values_listed_although_everyone_accepts_everything_is_invalid(root, context):
    service = make_ready(root, context, every_value=True)
    result = service.submit_value_validity(True, [row("1", "UPXSGA")])
    assert result.status is ValidityStatus.INVALID and "VALUES_WITHOUT_EXCEPTIONS" in codes(result)
    assert "VALIDITY_CONTRADICTS_STEP4" in codes(service.submit_value_validity(False, [row("1", "UPXSGA")]))


def test_warnings_do_not_block(ready):
    result = ready.submit_value_validity(False, [row("1", all_articles=True)])
    assert result.accepted and "NO_EXCEPTION_IN_TABLE" in codes(result, Severity.WARNING)
    result = ready.submit_value_validity(False, [row("1", "UPXSGA"), row("2", "UPXSGA")])
    assert result.accepted and "ARTICLE_ACCEPTS_NO_VALUE" in codes(result, Severity.WARNING)


def test_blank_rows_are_ignored():
    status, _, cleaned = validate_value_validity(False, [row(""), row("1", "UPXSGA")], ARTS, False)
    assert status is ValidityStatus.COMPLETE and [r.value for r in cleaned] == ["1"]


def test_parse_validity_cell():
    assert parse_validity_cell(" ALL ") == (True, [])
    assert parse_validity_cell("A, B ,") == (False, ["A", "B"])
    assert parse_validity_cell("") == (False, [])


def test_every_finding_cites_the_template():
    _, findings, _ = validate_value_validity(None, [], ARTS, False)
    assert all(f.basis.startswith("template Step 4a") for f in findings)


# prerequisites and state --------------------------------------------------------------------------------------------------
def test_step4a_needs_step4(root, context):
    build(root)
    service = context.metatype_creation_service
    assert service.submit_value_validity(False, [row("1", "A")]).errors[0].code == "STEP4_REQUIRED"
    service.start("atlas")
    service.submit_property_identity("GATLAS_Surface", "Surface")
    assert service.submit_value_validity(True).errors[0].code == "STEP4_REQUIRED"
    assert service.validity is None and service.validity_draft is None
    assert service.stage_status().steps[4].detail == "Answer Step 4 first."


def test_rejected_answer_keeps_the_earlier_confirmed_one_but_is_kept_as_draft(ready):
    first = ready.submit_value_validity(False, [row("1", "UPXSGA")]).validity
    ready.submit_value_validity(False, [row("1", "NOPE")])
    assert ready.validity is first
    assert ready.validity_draft.rows[0].articles == ["NOPE"]


def test_state_lives_in_the_session(ready, context):
    ready.submit_value_validity(False, [row("1", "UPXSGA")])
    again = ApplicationContext.get_service(context, type(ready))
    assert again.validity.rows[0].value == "1"
    assert context.workflow_session("metatype.creation")["context"].validity is ready.validity


def test_changing_step4_drops_the_confirmed_4a_but_keeps_the_draft(ready):
    ready.submit_value_validity(False, [row("1", "UPXSGA")])
    ready.submit_polymorphism_branch(["UPXSGA"], "unconditional", [], False)
    assert ready.validity is None and ready.validity_draft is not None
    assert ready.stage_status().steps[4].state is StepState.PENDING or ready.stage_status().steps[4].state is StepState.INCOMPLETE
    # the draft is re-validated against the new article list
    ready.submit_polymorphism_branch(ARTS, "unconditional", [], False)
    ready.submit_value_validity(False, [row("1", "UPXSAA")])
    ready.submit_polymorphism_branch(["UPXSGA", "OTHER"], "unconditional", [], False)
    step = ready.stage_status().steps[4]
    assert step.state is StepState.INVALID and "not one of the articles" in step.detail


def test_loading_another_series_resets_4a(root, context, ready):
    ready.submit_value_validity(False, [row("1", "UPXSGA")])
    build(root, "pullman")
    ready.start("pullman")
    assert ready.validity is not None and ready._state().pending_series == "pullman"
    ready.discard_and_start("pullman")
    assert ready.validity is None and ready.validity_draft is None


def test_children_stay_locked_after_4a_because_steps_5_and_6_are_not_done(ready):
    ready.submit_value_validity(False, [row("1", "UPXSGA")])
    status = ready.stage_status()
    assert [s.state for s in status.steps[:5]] == [StepState.DONE] * 5
    assert [(s.key, s.state) for s in status.steps[5:]] == [
        ("5", StepState.PENDING), ("6", StepState.PENDING),
        ("6w", StepState.NOT_IMPLEMENTED)]
    assert not status.children_unlocked and not ready.can_start_children()
    assert any("4a" in lim and "skipped" in lim for lim in status.limitations)


def test_4a_derives_no_mode_and_writes_nothing(root, ready):
    data = root / "atlas" / "1"
    before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()}
    result = ready.submit_value_validity(False, [row("1", "UPXSGA")])
    assert not {f for f in result.validity.__dataclass_fields__ if "mode" in f.lower() or "bit" in f.lower()}
    assert {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()} == before


# page ---------------------------------------------------------------------------------------------------------------------------
def test_page_step4a_flow_and_navigation(root, context):
    from PySide6.QtWidgets import QApplication, QTableWidgetItem
    from ui.pages.metatype_creation_page import MetatypeCreationPage

    app = QApplication.instance() or QApplication([])
    build(root)
    page = MetatypeCreationPage(context)
    page.series_combo.setCurrentIndex(0)
    page.load_button.click()
    assert not page._validity_group.isEnabled()
    page.name_edit.setText("GATLAS_Surface")
    page.label_edit.setText("Surface type")
    page.confirm_button.click()
    assert not page._validity_group.isEnabled()                                  # Step 4 not confirmed yet
    page.articles_edit.setPlainText("UPXSGA\nUPXSAA")
    page.scope_combo.setCurrentIndex(1)
    page.values_combo.setCurrentIndex(2)                                         # exceptions exist
    page.confirm_branch_button.click()
    assert page._validity_group.isEnabled() and not page.validity_table.isEnabled()

    page.confirm_validity_button.click()                                         # nothing answered
    assert "VALIDITY_UNANSWERED" in page.findings_output.toPlainText()
    assert "[incomplete] Step 4a" in page.status_output.toPlainText()

    page.validity_combo.setCurrentIndex(2)
    assert page.validity_table.isEnabled()
    page.add_value_button.click()
    page.validity_table.setItem(0, 0, QTableWidgetItem("1"))
    page.validity_table.setItem(0, 1, QTableWidgetItem("NOPE"))
    page.confirm_validity_button.click()
    assert "ARTICLE_NOT_IN_STEP4" in page.findings_output.toPlainText()
    assert "[invalid] Step 4a" in page.status_output.toPlainText()

    page.validity_table.setItem(0, 1, QTableWidgetItem("UPXSGA"))
    page.add_value_button.click()
    page.validity_table.setItem(1, 0, QTableWidgetItem("2"))
    page.validity_table.setItem(1, 1, QTableWidgetItem("all"))
    page.confirm_validity_button.click()
    assert "Value validity confirmed" in page.findings_output.toPlainText()
    assert "[done] Step 4a" in page.status_output.toPlainText()
    assert not page.children_button.isEnabled()                                  # Steps 5 and 6 remain

    # a freshly built page (navigation) shows the kept answer again
    again = MetatypeCreationPage(context)
    assert again.validity_combo.currentData() is False and again.validity_table.rowCount() == 2
    assert again.validity_table.item(1, 1).text() == "all"

    page.load_button.click()                                                     # reloading resets
    assert page.validity_table.rowCount() == 0 and page.validity_combo.currentIndex() == 0
    assert not page._validity_group.isEnabled()
    app.processEvents()
