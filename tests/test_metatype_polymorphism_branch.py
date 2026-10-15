"""Template Step 4 (Polymorphism branch): articles, unconditional/scoped switch, value acceptance."""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from core.application_context import ApplicationContext
from core.config import AppConfig
from models.metatype_creation import Severity, StepState, SwitchScope
from models.metatype_pattern import MetatypePattern
from services.metatype.metatype_table_loader import MetatypeTableLoader
from services.metatype.polymorphism_branch import validate_polymorphism_branch

COLUMNS = {
    "go_types": "id name format default mode filter",
    "go_articles": "id manufacturer program article_nr prm_key chprm_key",
    "go_propvalues": "id name value condition",
    "go_proporder": "value number",
    "go_children": "child_key manufacturer program article_nr variant pos_x pos_y pos_z condition",
    "go_texts": "key language text",
}
TYPES = (
    "MT_ATLAS ;GType      ;   ;ATLAS ;0 ;\r\n"
    "MT_ATLAS ;GATLAS_Type ;ch ;A ;131 ;\r\n"
)
ARTICLES = (
    "MT_ATLAS ;hmx ;atlas ;UPXSGA ;SET_1 ;\r\n"
    "MT_ATLAS ;hmx ;atlas ;UPXSAA ;SET_2 ;\r\n"
    "_native_ ;hmx ;atlas ;NATIVEONE ;SET_1 ;\r\n"
)


def build(root: Path, name="atlas", tables=COLUMNS) -> Path:
    data = root / name / "1"
    data.mkdir(parents=True, exist_ok=True)
    text = "# GO III (MT) Input Description, Version 1.16\n\n"
    for table, columns in tables.items():
        names = columns.split()
        text += f"table   {table}\t{table}.csv\t\tcsv\nfields  {len(names)}\n"
        text += "".join(f"field   {i}  {n}\t\tvstring\t\tdelim ; trim\n" for i, n in enumerate(names, 1))
    (data / "mt.inp_descr").write_text(text, encoding="utf-8")
    bodies = {"go_types": TYPES, "go_articles": ARTICLES, "go_texts": b"K;en;caf\xe9\r\n"}
    for table in tables:
        body = bodies.get(table, "")
        (data / f"{table}.csv").write_bytes(body if isinstance(body, bytes) else body.encode("utf-8"))
    return data


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "hmx"
    path.mkdir()
    return path


@pytest.fixture
def context(root):
    return ApplicationContext(AppConfig(metatype_repository_root=str(root)))


@pytest.fixture
def ready(root, context):
    """A loaded series with Step 3 confirmed."""
    build(root)
    service = context.metatype_creation_service
    service.start("atlas")
    assert service.submit_property_identity("GATLAS_Surface", "Surface type").accepted
    return service


def codes(result, severity=None):
    return {f.code for f in result.findings if severity is None or f.severity is severity}


# valid answers ------------------------------------------------------------------------------------------------------
def test_unconditional_switch_with_no_value_exceptions_is_confirmed(ready):
    identity = ready.identity
    result = ready.submit_polymorphism_branch([" UPXSGA ", "UPXSAA", ""], "unconditional", [], True)
    assert result.accepted and not result.errors and not result.findings
    branch = result.branch
    assert branch.articles == ["UPXSGA", "UPXSAA"]
    assert branch.scope is SwitchScope.UNCONDITIONAL and branch.scope_conditions == []
    assert branch.every_article_accepts_every_value is True
    assert branch.series == "atlas" and branch.property_name == "GATLAS_Surface"
    assert branch.inspection_inspected_at == ready.inspection.inspected_at
    assert ready.branch is branch and ready.identity is identity                 # Step 3 data preserved
    step = ready.stage_status().steps[3]
    assert step.state is StepState.DONE and "2 article(s), unconditional" in step.detail


def test_scoped_switch_keeps_the_users_condition_text_and_exceptions_are_recorded(ready):
    result = ready.submit_polymorphism_branch(
        ["UPXSGA", "UPXSAA"], SwitchScope.SCOPED, ["GRegion == @EU", "  parent property: GATLAS_Kit "], False)
    assert result.accepted
    assert result.branch.scope is SwitchScope.SCOPED
    assert result.branch.scope_conditions == ["GRegion == @EU", "parent property: GATLAS_Kit"]   # text, not parsed
    assert result.branch.every_article_accepts_every_value is False
    assert "VALUE_EXCEPTIONS_RECORDED" in codes(result, Severity.INFO)
    assert "scoped (2 condition(s))" in ready.stage_status().steps[3].detail
    assert "Step 4a" in ready.stage_status().steps[3].detail


def test_unknown_and_single_articles_are_warnings_not_errors(ready):
    result = ready.submit_polymorphism_branch(["BRANDNEW"], "unconditional", [], True)
    assert result.accepted
    assert codes(result, Severity.WARNING) == {"ARTICLE_UNKNOWN", "ARTICLES_SINGLE"}


# invalid answers --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("articles, scope, conditions, accepts, expected", [
    ([], "unconditional", [], True, "ARTICLES_EMPTY"),
    (["", "  "], "unconditional", [], True, "ARTICLES_EMPTY"),
    (["UPXSGA", "UPXSGA"], "unconditional", [], True, "ARTICLE_DUPLICATE"),
    (["UPXSGA", "UPXSAA"], None, [], True, "SCOPE_MISSING"),
    (["UPXSGA", "UPXSAA"], "sometimes", [], True, "SCOPE_MISSING"),
    (["UPXSGA", "UPXSAA"], "scoped", [], True, "SCOPE_CONDITIONS_MISSING"),
    (["UPXSGA", "UPXSAA"], "scoped", ["  "], True, "SCOPE_CONDITIONS_MISSING"),
    (["UPXSGA", "UPXSAA"], "unconditional", ["GRegion == @EU"], True, "SCOPE_CONDITIONS_UNEXPECTED"),
    (["UPXSGA", "UPXSAA"], "unconditional", [], None, "VALUES_UNANSWERED"),
])
def test_invalid_answers_are_rejected_and_do_not_replace_an_earlier_answer(ready, articles, scope, conditions, accepts, expected):
    first = ready.submit_polymorphism_branch(["UPXSGA", "UPXSAA"], "unconditional", [], True).branch
    result = ready.submit_polymorphism_branch(articles, scope, conditions, accepts)
    assert not result.accepted and result.branch is None
    assert expected in codes(result, Severity.ERROR)
    assert ready.branch is first


def test_every_finding_cites_the_template_question():
    findings, *_ = validate_polymorphism_branch([], None, [], None, None)
    assert {f.basis.split(" (")[0] for f in findings} == {"template Step 4"}
    assert all("(" in f.basis for f in findings)


# incomplete states / prerequisites ----------------------------------------------------------------------------------------
def test_step4_needs_a_loaded_series_and_confirmed_step3(root, context):
    service = context.metatype_creation_service
    assert service.submit_polymorphism_branch(["A"], "unconditional", [], True).errors[0].code == "STEP3_REQUIRED"
    build(root)
    service.start("atlas")
    result = service.submit_polymorphism_branch(["UPXSGA", "UPXSAA"], "unconditional", [], True)
    assert not result.accepted and result.errors[0].code == "STEP3_REQUIRED" and service.branch is None
    assert service.stage_status().steps[3].state is StepState.PENDING


def test_step4_is_only_the_polymorphism_branch(ready, context):
    ready._state().pattern_selection = context.metatype_pattern_service.select_pattern(
        "atlas", MetatypePattern.WITH_CHILDS).selection
    result = ready.submit_polymorphism_branch(["UPXSGA", "UPXSAA"], "unconditional", [], True)
    assert not result.accepted and result.errors[0].code == "PATTERN_NOT_POLYMORPHISM"


# article hints from the series' own go_articles ---------------------------------------------------------------------------------
def test_known_articles_come_from_go_articles_and_skip_the_reserved_native_id(ready):
    articles = ready.known_articles
    assert [(a.article_nr, a.metatype_id) for a in articles] == [("UPXSGA", "MT_ATLAS"), ("UPXSAA", "MT_ATLAS")]
    assert articles[0].line == 1


def test_series_without_go_articles_is_not_checked_but_not_blocked(root, context):
    build(root, tables={k: v for k, v in COLUMNS.items() if k != "go_articles"})
    service = context.metatype_creation_service
    service.start("atlas")
    service.submit_property_identity("GATLAS_Surface", "Surface")
    assert service.known_articles is None
    result = service.submit_polymorphism_branch(["X1", "X2"], "unconditional", [], True)
    assert result.accepted and codes(result, Severity.INFO) == {"ARTICLES_UNVERIFIED"}


def test_only_the_selected_series_tables_are_read_and_go_texts_is_not_opened(root, context, monkeypatch):
    build(root)
    opened = []
    original = MetatypeTableLoader._read_bytes
    monkeypatch.setattr(MetatypeTableLoader, "_read_bytes",
                        lambda self, path, limit: (opened.append(Path(path).name), original(self, path, limit))[1])
    context.metatype_creation_service.start("atlas")
    assert "go_texts.csv" not in opened and "go_articles.csv" in opened
    assert context.metatype_repository_service.last_result is None               # no repository scan


# the gate and the recorded limitation ----------------------------------------------------------------------------------------------
def test_children_stay_locked_after_step4_because_later_steps_are_incomplete(ready):
    ready.submit_polymorphism_branch(["UPXSGA", "UPXSAA"], "unconditional", [], True)
    status = ready.stage_status()
    assert [s.state for s in status.steps[:4]] == [StepState.DONE] * 4
    assert [(s.key, s.state) for s in status.steps[4:]] == [
        ("4a", StepState.PENDING), ("5", StepState.PENDING), ("6", StepState.PENDING),
        ("6w", StepState.NOT_IMPLEMENTED)]
    assert not status.complete and not status.children_unlocked and not ready.can_start_children()
    assert [b.split(" ")[1] for b in status.blocking] == ["4a", "5", "6", "6w"]


def test_mode_encoding_is_recorded_as_a_limitation_and_no_mode_is_derived(ready):
    result = ready.submit_polymorphism_branch(["UPXSGA", "UPXSAA"], "unconditional", [], True)
    fields = set(result.branch.__dataclass_fields__)
    assert not {f for f in fields if "mode" in f.lower() or "bit" in f.lower()}
    limitations = ready.stage_status().limitations
    assert limitations and "Mode encoding is unresolved" in limitations[0] and "131" in limitations[0]
    assert "LIMITATION Mode encoding" in ready.summary_text()


# session state ------------------------------------------------------------------------------------------------------------------------
def test_step4_state_lives_in_the_workflow_session_and_survives_new_lookups(ready, context):
    ready.submit_polymorphism_branch(["UPXSGA", "UPXSAA"], "scoped", ["GRegion == @EU"], True)
    again = ApplicationContext.get_service(context, type(ready))
    assert again.branch.scope_conditions == ["GRegion == @EU"]
    assert context.workflow_session("metatype.creation")["context"].branch is ready.branch


def test_loading_another_series_resets_step4_and_changing_step3_flags_it(root, context, ready):
    ready.submit_polymorphism_branch(["UPXSGA", "UPXSAA"], "unconditional", [], True)
    ready.submit_property_identity("GATLAS_Other", "Other")
    assert any("review Step 4" in w for w in ready.stage_status().warnings)
    assert ready.branch.property_name == "GATLAS_Surface"                        # answer kept, not silently rewritten
    build(root, "pullman")
    ready.start("pullman")
    assert ready.branch is not None and ready._state().pending_series == "pullman"
    ready.discard_and_start("pullman")
    assert ready.branch is None and ready.identity is None


def test_step4_writes_nothing_to_the_repository(root, ready):
    data = root / "atlas" / "1"
    before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()}
    ready.submit_polymorphism_branch(["UPXSGA", "UPXSAA"], "unconditional", [], True)
    assert {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()} == before
    assert sorted(p.name for p in root.iterdir()) == ["atlas"]


# page -------------------------------------------------------------------------------------------------------------------------------------
def test_page_step4_flow(root, context):
    from PySide6.QtWidgets import QApplication
    from ui.pages.metatype_creation_page import MetatypeCreationPage

    app = QApplication.instance() or QApplication([])
    build(root)
    page = MetatypeCreationPage(context)
    assert not page._branch_group.isEnabled()
    page.series_combo.setCurrentIndex(0)
    page.load_button.click()
    assert not page._branch_group.isEnabled()                                  # Step 3 not confirmed yet
    page.name_edit.setText("GATLAS_Surface")
    page.label_edit.setText("Surface type")
    page.confirm_button.click()
    assert page._branch_group.isEnabled() and "2 article(s) in this series" in page.articles_hint.text()
    assert not page.conditions_edit.isEnabled()

    page.confirm_branch_button.click()                                         # nothing answered yet
    text = page.findings_output.toPlainText()
    assert "ARTICLES_EMPTY" in text and "SCOPE_MISSING" in text and "VALUES_UNANSWERED" in text

    page.articles_edit.setPlainText("UPXSGA\nUPXSAA")
    page.scope_combo.setCurrentIndex(2)
    assert page.conditions_edit.isEnabled()
    page.confirm_branch_button.click()
    assert "SCOPE_CONDITIONS_MISSING" in page.findings_output.toPlainText()
    page.conditions_edit.setPlainText("GRegion == @EU")
    page.values_combo.setCurrentIndex(1)
    page.confirm_branch_button.click()
    assert "Polymorphism branch confirmed" in page.findings_output.toPlainText()
    assert "[done] Step 4" in page.status_output.toPlainText()
    assert "LIMITATION Mode encoding" in page.status_output.toPlainText()
    assert not page.children_button.isEnabled()                                # Steps 4a, 5, 6 remain

    page.load_button.click()                                                   # reloading resets the answers
    assert page.articles_edit.toPlainText() == "" and not page._branch_group.isEnabled()
    app.processEvents()
