"""Template Step 5: translations (DE, FR, NL) for the property and the Step 4a values."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from core.application_context import ApplicationContext
from core.config import AppConfig
from models.metatype_creation import Severity, StepState, TranslationKind, TranslationRow, ValidityStatus, ValueValidityRow
from services.metatype.translations import expected_rows, validate_translations
from tests.test_metatype_polymorphism_branch import build

PROP = TranslationKind.PROPERTY
VAL = TranslationKind.VALUE
ARTS = ["UPXSGA", "UPXSAA"]


def tr(key, kind=VAL, en="", de="de", fr="fr", nl="nl"):
    return TranslationRow(key, kind, en, de, fr, nl)


def full_rows():
    return [tr("GATLAS_Surface", PROP), tr("1", en="One"), tr("2", en="Two")]


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


def make_ready(root, context, exceptions=True):
    build(root)
    service = context.metatype_creation_service
    service.start("atlas")
    assert service.submit_property_identity("GATLAS_Surface", "Surface type").accepted
    assert service.submit_polymorphism_branch(ARTS, "unconditional", [], not exceptions).accepted
    rows = [ValueValidityRow("1", False, ["UPXSGA"]), ValueValidityRow("2", True, [])] if exceptions else []
    assert service.submit_value_validity(not exceptions, rows).accepted
    return service


@pytest.fixture
def ready(root, context):
    return make_ready(root, context)


# expected rows -----------------------------------------------------------------------------------------------------------
def test_rows_are_the_property_then_each_4a_value(ready):
    rows = ready.expected_translation_rows()
    assert [(r.technical, r.kind, r.en) for r in rows] == [
        ("GATLAS_Surface", PROP, "Surface type"), ("1", VAL, ""), ("2", VAL, "")]


def test_without_4a_values_only_the_property_is_translated(root, context):
    service = make_ready(root, context, exceptions=False)
    assert [r.technical for r in service.expected_translation_rows()] == ["GATLAS_Surface"]
    assert service.submit_translations([tr("GATLAS_Surface", PROP)]).accepted
    assert service.stage_status().steps[5].state is StepState.DONE


# complete ---------------------------------------------------------------------------------------------------------------------
def test_complete_answer_is_confirmed_in_template_row_order(ready):
    result = ready.submit_translations(reversed(full_rows()))
    assert result.status is ValidityStatus.COMPLETE and result.accepted and not result.errors
    t = ready.translations
    assert t is result.translations and t.property_name == "GATLAS_Surface"
    assert [r.technical for r in t.rows] == ["GATLAS_Surface", "1", "2"]
    assert t.rows[0].en == "Surface type"                                        # taken from Step 3, not from the input
    assert (t.rows[1].en, t.rows[1].de, t.rows[1].fr, t.rows[1].nl) == ("One", "de", "fr", "nl")
    assert t.validity_confirmed_at == ready.validity.confirmed_at
    step = ready.stage_status().steps[5]
    assert step.key == "5" and step.state is StepState.DONE and "3 row(s)" in step.detail


def test_texts_are_trimmed(ready):
    rows = full_rows()
    rows[1].de = "  Eins  "
    assert ready.submit_translations(rows).accepted and ready.translations.rows[1].de == "Eins"


# incomplete -----------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("mutate, expected", [
    (lambda r: setattr(r[1], "de", " "), "TRANSLATION_MISSING"),
    (lambda r: setattr(r[0], "fr", ""), "TRANSLATION_MISSING"),
    (lambda r: setattr(r[2], "nl", ""), "TRANSLATION_MISSING"),
    (lambda r: setattr(r[1], "en", ""), "TRANSLATION_MISSING_EN"),
    (lambda r: r.pop(), "TRANSLATION_MISSING"),                                   # a row left out is not translated
])
def test_incomplete_answers(ready, mutate, expected):
    rows = full_rows()
    mutate(rows)
    result = ready.submit_translations(rows)
    assert result.status is ValidityStatus.INCOMPLETE and expected in codes(result, Severity.ERROR)
    assert ready.translations is None and ready.stage_status().steps[5].state is StepState.INCOMPLETE


def test_missing_language_messages_name_the_language(ready):
    rows = full_rows()
    rows[0].de = ""
    assert "German" in ready.submit_translations(rows).findings[0].message


# invalid -----------------------------------------------------------------------------------------------------------------------------
def test_unknown_or_duplicate_rows_are_invalid(ready):
    result = ready.submit_translations(full_rows() + [tr("9", en="Nine")])
    assert result.status is ValidityStatus.INVALID and "TRANSLATION_ROW_UNKNOWN" in codes(result)
    result = ready.submit_translations(full_rows() + [tr("1", en="One")])
    assert result.status is ValidityStatus.INVALID and "TRANSLATION_ROW_DUPLICATE" in codes(result)
    assert ready.stage_status().steps[5].state is StepState.INVALID


def test_every_finding_cites_the_template():
    _, findings, _ = validate_translations([], expected_rows("P", "Label", ["1"]))
    assert findings and all(f.basis.startswith("template Step 5") for f in findings)


# prerequisites and state -------------------------------------------------------------------------------------------------------------------
def test_step5_needs_step4a(root, context):
    build(root)
    service = context.metatype_creation_service
    service.start("atlas")
    service.submit_property_identity("GATLAS_Surface", "Surface")
    result = service.submit_translations([tr("GATLAS_Surface", PROP)])
    assert result.errors[0].code == "STEP4A_REQUIRED" and service.translation_draft is None
    assert service.stage_status().steps[5].detail == "Answer Step 4a first."
    assert service.translation_rows() == []


def test_rejected_answer_keeps_earlier_confirmed_one_and_is_kept_as_draft(ready):
    first = ready.submit_translations(full_rows()).translations
    bad = full_rows()
    bad[1].fr = ""
    ready.submit_translations(bad)
    assert ready.translations is first
    assert [r.fr for r in ready.translation_rows()] == ["fr", "", "fr"]           # draft shown again
    assert ready.stage_status().steps[5].state is StepState.DONE                   # earlier confirmed answer still counts


def test_changed_values_make_confirmed_translations_stale_without_losing_texts(ready):
    ready.submit_translations(full_rows())
    ready.submit_value_validity(False, [ValueValidityRow("1", False, ["UPXSGA"]), ValueValidityRow("3", True, [])])
    step = ready.stage_status().steps[5]
    assert step.state is StepState.INCOMPLETE                                      # stale rows are ignored, not invalid
    assert not ready.can_start_children()
    rows = ready.translation_rows()
    assert [r.technical for r in rows] == ["GATLAS_Surface", "1", "3"]
    assert rows[1].de == "de" and rows[1].en == "One" and rows[2].de == ""         # carried over by technical value


def test_changed_step3_label_makes_translations_stale(ready):
    ready.submit_translations(full_rows())
    ready.submit_property_identity("GATLAS_Surface", "Surface kind")
    assert ready.stage_status().steps[5].state is not StepState.DONE
    assert ready.translation_rows()[0].en == "Surface kind"


def test_dropping_4a_by_changing_step4_blocks_step5(ready):
    ready.submit_translations(full_rows())
    ready.submit_polymorphism_branch(["UPXSGA"], "unconditional", [], False)
    assert ready.stage_status().steps[5].detail == "Answer Step 4a first."


def test_state_lives_in_the_session_and_resets_with_a_new_series(root, context, ready):
    ready.submit_translations(full_rows())
    assert ApplicationContext.get_service(context, type(ready)).translations.rows[1].de == "de"
    assert context.workflow_session("metatype.creation")["context"].translations is ready.translations
    build(root, "pullman")
    ready.start("pullman")
    assert ready.translations is not None and ready._state().pending_series == "pullman"
    ready.discard_and_start("pullman")
    assert ready.translations is None and ready.translation_draft is None


def test_children_stay_locked_after_step5_because_step6_is_pending(ready):
    ready.submit_translations(full_rows())
    status = ready.stage_status()
    assert [s.state for s in status.steps[:6]] == [StepState.DONE] * 6
    assert [(s.key, s.state) for s in status.steps[6:]] == [("6", StepState.PENDING), ("6w", StepState.NOT_IMPLEMENTED)]
    assert not status.complete and not status.children_unlocked and not ready.can_start_children()
    assert any("go_texts" in lim and "Step 5" in lim for lim in status.limitations)


def test_step5_derives_nothing_and_writes_nothing(root, ready):
    data = root / "atlas" / "1"
    before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()}
    result = ready.submit_translations(full_rows())
    assert not {f for f in result.translations.__dataclass_fields__ if "mode" in f or "go_texts" in f or "csv" in f}
    assert {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()} == before


# page ---------------------------------------------------------------------------------------------------------------------------------------
def test_page_step5_flow_and_navigation(root, context):
    from PySide6.QtWidgets import QApplication, QTableWidgetItem
    from ui.pages.metatype_creation_page import MetatypeCreationPage

    app = QApplication.instance() or QApplication([])
    build(root)
    page = MetatypeCreationPage(context)
    assert not page._translation_group.isEnabled()
    page.series_combo.setCurrentIndex(0)
    page.load_button.click()
    page.name_edit.setText("GATLAS_Surface")
    page.label_edit.setText("Surface type")
    page.confirm_button.click()
    page.articles_edit.setPlainText("UPXSGA\nUPXSAA")
    page.scope_combo.setCurrentIndex(1)
    page.values_combo.setCurrentIndex(2)
    page.confirm_branch_button.click()
    assert not page._translation_group.isEnabled() and page.translation_table.rowCount() == 0

    page.validity_combo.setCurrentIndex(2)
    page.add_value_button.click()
    page.validity_table.setItem(0, 0, QTableWidgetItem("1"))
    page.validity_table.setItem(0, 1, QTableWidgetItem("UPXSGA"))
    page.confirm_validity_button.click()
    assert page._translation_group.isEnabled() and page.translation_table.rowCount() == 2
    table = page.translation_table
    assert table.item(0, 0).text() == "GATLAS_Surface" and table.item(0, 1).text() == "Surface type"
    assert not (table.item(0, 1).flags() & table.item(0, 1).flags().__class__.ItemIsEditable)   # EN from Step 3

    page.confirm_translations_button.click()                                      # nothing typed
    assert "TRANSLATION_MISSING" in page.findings_output.toPlainText()
    assert "[incomplete] Step 5" in page.status_output.toPlainText()

    for row in range(2):
        for column, text in ((2, "de"), (3, "fr"), (4, "nl")):
            table.setItem(row, column, QTableWidgetItem(f"{text}{row}"))
    page.confirm_translations_button.click()
    assert "Translations not accepted" in page.findings_output.toPlainText()      # value 1 has no English text
    table.setItem(1, 1, QTableWidgetItem("One"))
    page.confirm_translations_button.click()
    assert "Translations confirmed" in page.findings_output.toPlainText()
    assert "[done] Step 5" in page.status_output.toPlainText()
    assert "[not available yet] Step 6" in page.status_output.toPlainText()
    assert not page.children_button.isEnabled()

    again = MetatypeCreationPage(context)                                         # navigation: a rebuilt page
    assert again.translation_table.rowCount() == 2
    assert again.translation_table.item(1, 1).text() == "One" and again.translation_table.item(1, 3).text() == "fr1"

    page.load_button.click()
    assert page.translation_table.rowCount() == 0 and not page._translation_group.isEnabled()
    app.processEvents()
