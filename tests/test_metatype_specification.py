"""Template Step 6: summary block and explicit confirmation (the writing half is not implemented)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from core.application_context import ApplicationContext
from core.config import AppConfig
from models.metatype_creation import StepState, TranslationKind, TranslationRow, ValidityStatus, ValueValidityRow
from tests.test_metatype_polymorphism_branch import build

PROP, VAL = TranslationKind.PROPERTY, TranslationKind.VALUE
ARTS = ["UPXSGA", "UPXSAA"]


def tr(key, kind=VAL, en="", de="de", fr="fr", nl="nl"):
    return TranslationRow(key, kind, en, de, fr, nl)


def full_rows():
    return [tr("GATLAS_Surface", PROP), tr("1", en="One", de="Eins"), tr("2", en="Two")]


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "hmx"
    path.mkdir()
    return path


@pytest.fixture
def context(root):
    return ApplicationContext(AppConfig(metatype_repository_root=str(root)))


def make_ready(root, context, scope="unconditional", conditions=(), exceptions=True):
    build(root)
    service = context.metatype_creation_service
    service.start("atlas")
    assert service.submit_property_identity("GATLAS_Surface", "Surface type").accepted
    assert service.submit_polymorphism_branch(ARTS, scope, list(conditions), not exceptions).accepted
    rows = [ValueValidityRow("1", False, ["UPXSGA"]), ValueValidityRow("2", True, [])] if exceptions else []
    assert service.submit_value_validity(not exceptions, rows).accepted
    translated = full_rows() if exceptions else full_rows()[:1]
    assert service.submit_translations(translated).accepted
    return service


@pytest.fixture
def ready(root, context):
    return make_ready(root, context)


# the summary: the six items the template lists --------------------------------------------------------------------------
def test_summary_contains_every_template_item(root, context):
    service = make_ready(root, context, "scoped", ["GRegion == @EU"])
    text = service.specification_text()
    assert "Metatype type: Polymorphism" in text
    assert "GATLAS_Surface - EN: Surface type | DE: de | FR: fr | NL: nl" in text            # property + labels
    assert "1 - EN: One | DE: Eins | FR: fr | NL: nl" in text                                # values + labels
    assert "The property switches between: UPXSGA, UPXSAA" in text                             # article mapping
    assert "Value 1: UPXSGA" in text and "Value 2: all articles" in text
    assert "| 1 | UPXSGA |" in text and "| 2 | all |" in text                                 # Step 4a table
    assert "scoped to:" in text and "- GRegion == @EU" in text                                # Step 4 scoping


def test_summary_without_values_or_exceptions(root, context):
    service = make_ready(root, context, exceptions=False)
    text = service.specification_text()
    assert "(none)" in text and "No exceptions: all articles accept the full value set." in text
    assert "The switch is unconditional." in text
    assert "mode" not in text.lower()                                                         # nothing derived


def test_summary_is_not_available_until_steps_1_to_5_are_done(root, context):
    build(root)
    service = context.metatype_creation_service
    assert service.specification_text() is None
    service.start("atlas")
    service.submit_property_identity("GATLAS_Surface", "Surface")
    assert service.specification_text() is None


# confirmation ----------------------------------------------------------------------------------------------------------------------------
def test_explicit_confirmation_is_recorded_and_step6_is_done(ready):
    assert ready.stage_status().steps[6].state is StepState.PENDING and ready.confirmation is None
    result = ready.confirm_specification()
    assert result.status is ValidityStatus.COMPLETE and result.accepted and result.summary_text
    assert ready.confirmation is result.confirmation and ready.confirmation_is_current()
    assert ready.confirmation.summary_text == ready.specification_text()
    step = ready.stage_status().steps[6]
    assert (step.key, step.state) == ("6", StepState.DONE)


def test_nothing_is_confirmed_by_merely_viewing_the_summary(ready):
    ready.specification_text()
    ready.stage_status()
    assert ready.confirmation is None


def test_confirmation_needs_steps_1_to_5(root, context):
    build(root)
    service = context.metatype_creation_service
    assert service.confirm_specification().errors[0].code == "SPEC_STEP_INCOMPLETE"
    service.start("atlas")
    service.submit_property_identity("GATLAS_Surface", "Surface")
    result = service.confirm_specification()
    assert result.status is ValidityStatus.INCOMPLETE and not result.accepted
    assert {f.code for f in result.errors} == {"SPEC_STEP_INCOMPLETE"} and len(result.errors) == 3   # 4, 4a, 5
    assert service.confirmation is None


def test_changed_upstream_content_makes_the_confirmation_stale_but_identical_reconfirmation_does_not(ready):
    ready.confirm_specification()
    ready.submit_property_identity("GATLAS_Surface", "Surface type")                       # same data again
    assert ready.confirmation_is_current()
    rows = full_rows()
    rows[2].fr = "deux"
    ready.submit_translations(rows)                                                        # content changed
    assert not ready.confirmation_is_current()
    step = ready.stage_status().steps[6]
    assert step.state is StepState.PENDING and "changed since" in step.detail
    assert ready.confirmation is not None                                                  # kept, just not current
    ready.confirm_specification()
    assert ready.confirmation_is_current() and ready.stage_status().steps[6].state is StepState.DONE


def test_property_renamed_after_steps_4_and_4a_blocks_confirmation(ready):
    ready.submit_property_identity("GATLAS_Other", "Other")
    result = ready.confirm_specification()
    assert result.status in (ValidityStatus.INVALID, ValidityStatus.INCOMPLETE) and not result.accepted
    assert ready.confirmation is None


def test_rename_carried_only_into_step5_is_refused_as_property_changed(ready):
    """Steps 4 and 4a still answer for the old name, so the summary would mix two property names."""
    ready.submit_property_identity("GATLAS_Other", "Other")
    rows = [tr("GATLAS_Other", PROP), tr("1", en="One"), tr("2", en="Two")]
    assert ready.submit_translations(rows).accepted
    assert ready.specification_text() is None
    result = ready.confirm_specification()
    assert result.status is ValidityStatus.INVALID and not result.accepted
    assert {f.code for f in result.errors} == {"SPEC_PROPERTY_CHANGED"} and len(result.errors) == 2   # Step 4 and 4a
    assert ready.confirmation is None


def test_step4_change_drops_4a_and_step6_goes_back_to_pending(ready):
    ready.confirm_specification()
    ready.submit_polymorphism_branch(ARTS, "unconditional", [], False)
    assert not ready.confirmation_is_current()
    assert ready.stage_status().steps[6].detail == "Complete Steps 1-5 first."


def test_loading_another_series_resets_the_confirmation(root, context, ready):
    ready.confirm_specification()
    build(root, "pullman")
    ready.start("pullman")
    assert ready.confirmation is None and ready.specification_text() is None


# the gate ------------------------------------------------------------------------------------------------------------------------------------
def test_children_stay_locked_because_writing_is_not_implemented(ready):
    ready.confirm_specification()
    status = ready.stage_status()
    assert [s.state for s in status.steps[:7]] == [StepState.DONE] * 7
    assert [(s.key, s.state) for s in status.steps[7:]] == [("6w", StepState.NOT_IMPLEMENTED)]
    assert not status.complete and not status.children_unlocked and not ready.can_start_children()
    assert status.blocking[0].startswith("Step 6w")
    assert any("Step 6" in lim and "authorises nothing" in lim for lim in status.limitations)


def test_confirmation_writes_nothing_to_the_repository(root, ready):
    data = root / "atlas" / "1"
    before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()}
    ready.confirm_specification()
    assert {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()} == before
    assert sorted(p.name for p in root.iterdir()) == ["atlas"]


def test_state_lives_in_the_session(ready, context):
    ready.confirm_specification()
    assert ApplicationContext.get_service(context, type(ready)).confirmation_is_current()
    assert context.workflow_session("metatype.creation")["confirmation"] is ready.confirmation


# page -------------------------------------------------------------------------------------------------------------------------------------------
def test_page_step6_flow_and_navigation(root, context):
    from PySide6.QtWidgets import QApplication
    from ui.pages.metatype_creation_page import MetatypeCreationPage

    app = QApplication.instance() or QApplication([])
    make_ready(root, context)
    page = MetatypeCreationPage(context)                                                   # navigation: page built later
    assert page._spec_group.isEnabled()
    assert "Metatype type: Polymorphism" in page.spec_output.toPlainText()
    assert "[todo] Step 6" in page.status_output.toPlainText()

    page.confirm_spec_button.click()
    assert "Specification confirmed" in page.findings_output.toPlainText()
    text = page.status_output.toPlainText()
    assert "[done] Step 6" in text and "[not available yet] Step 6w" in text
    assert not page.children_button.isEnabled()

    page.translation_table.item(1, 2).setText("Eins!")
    page.confirm_translations_button.click()                                               # changes the spec
    assert "[todo] Step 6" in page.status_output.toPlainText()
    assert "Eins!" in page.spec_output.toPlainText()

    page.series_combo.setCurrentIndex(0)
    page.load_button.click()                                                               # reloading resets
    assert page.spec_output.toPlainText() == "" and not page._spec_group.isEnabled()
    app.processEvents()
