"""Runtime Metatype creation: series selection, load, template Step 3 and the completion gate."""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

import services.metatype.metatype_creation_service as creation_module
from core.application_context import ApplicationContext
from core.config import AppConfig
from core.modules import WorkbenchModule, module_workflows
from core.workflow import WORKFLOW_ITEMS, WorkflowStep
from models.metatype_creation import Severity, StepState, TranslationKind, TranslationRow
from models.metatype_pattern import MetatypePattern
from models.metatype_series import SeriesConventions, SeriesStatus
from services.metatype.property_identity import validate_property_identity

COLUMNS = {
    "go_types": "id name format default mode filter",
    "go_propvalues": "id name value condition",
    "go_proporder": "value number",
    "go_children": "child_key manufacturer program article_nr variant pos_x pos_y pos_z condition",
    "go_texts": "key language text",
}
TYPES = (
    "MT_ATLAS ;GType      ;   ;ATLAS ;0 ;\r\n"
    "MT_ATLAS ;GATLAS_Type ;ch ;A ;131 ;\r\n"
    "MT_ATLAS ;GATLAS_Tray ;ch ;N ;137 ;\r\n"
    "MT_ATLAS ;GWidth      ;na ;800 ;1 ;\r\n"
)


def build(root: Path, name="atlas", types=TYPES, with_schema=True) -> Path:
    data = root / name / "1"
    data.mkdir(parents=True, exist_ok=True)
    if with_schema:
        text = "# GO III (MT) Input Description, Version 1.16\n\n"
        for table, columns in COLUMNS.items():
            names = columns.split()
            text += f"table   {table}\t{table}.csv\t\tcsv\nfields  {len(names)}\n"
            text += "".join(f"field   {i}  {n}\t\tvstring\t\tdelim ; trim\n" for i, n in enumerate(names, 1))
        (data / "mt.inp_descr").write_text(text, encoding="utf-8")
        for table in COLUMNS:
            body = types if table == "go_types" else (b"K;en;caf\xe9\r\n" if table == "go_texts" else "")
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


# runtime workflow registration: independent of PDM ----------------------------------------------------------
def test_metatype_module_exposes_all_seven_stages_without_a_product_step():
    steps = module_workflows(WorkbenchModule.METATYPE)
    assert steps == (
        WorkflowStep.METATYPE_ARTICLES,
        WorkflowStep.METATYPE_PROPERTIES,
        WorkflowStep.METATYPE_VALUES,
        WorkflowStep.METATYPE_TEXTS,
        WorkflowStep.METATYPE_SETUP,
        WorkflowStep.METATYPE_RELATIONS,
        WorkflowStep.METATYPE_REVIEW,
    )
    items = {item.step: item for item in WORKFLOW_ITEMS}
    assert all(step in items for step in steps)
    assert [items[step].title for step in steps] == [
        "Articles", "Properties", "Property Values", "Texts",
        "Setup", "Relations / Ordering", "Final Review",
    ]


def test_no_pdm_product_or_scan_is_needed(root, context):
    build(root)
    assert context.active_snapshot is None
    status = context.metatype_creation_service.start("atlas")
    assert [s.state for s in status.steps[:3]] == [StepState.DONE, StepState.DONE, StepState.PENDING]
    assert context.metatype_repository_service.last_result is None            # no Scan Repository was run
    assert context.metatype_relationship_service.last_result is None          # no Resolve Relationships


# series selection ------------------------------------------------------------------------------------------------
def test_list_series_is_a_shallow_listing_that_flags_series_without_data(root, context):
    build(root, "atlas")
    build(root, "pullman")
    build(root, "comma", with_schema=False)
    (root / "loose.txt").write_text("x")
    (root / ".svn").mkdir()
    choices = context.metatype_creation_service.list_series()
    assert [(c.name, c.has_schema) for c in choices] == [("atlas", True), ("comma", False), ("pullman", True)]
    assert choices[0].numbered_directories == ["1"]


def test_list_series_survives_a_missing_root(tmp_path):
    context = ApplicationContext(AppConfig(metatype_repository_root=str(tmp_path / "nope")))
    assert context.metatype_creation_service.list_series() == []


# load: Step 1 + Step 2 --------------------------------------------------------------------------------------------
def test_start_loads_only_the_selected_series_and_records_polymorphism(root, context):
    build(root, "atlas")
    build(root, "pullman")
    service = context.metatype_creation_service
    status = service.start("atlas")
    assert service.series == "atlas" and service.inspection.target_series == "atlas"
    assert context.metatype_pattern_service.selection_for("atlas").pattern is MetatypePattern.POLYMORPHISM
    assert context.metatype_series_service.last_result.references == []       # pullman was not touched
    assert status.steps[0].state is StepState.DONE and status.steps[1].state is StepState.DONE


def test_go_texts_is_not_opened_when_a_series_is_loaded(root, context, monkeypatch):
    build(root)
    opened = []
    from services.metatype.metatype_table_loader import MetatypeTableLoader
    original = MetatypeTableLoader._read_bytes
    monkeypatch.setattr(MetatypeTableLoader, "_read_bytes",
                        lambda self, path, limit: (opened.append(Path(path).name), original(self, path, limit))[1])
    context.metatype_creation_service.start("atlas")
    assert "go_texts.csv" not in opened and "go_types.csv" in opened


def test_series_without_metatype_data_cannot_be_named_into(root, context):
    build(root, "comma", with_schema=False)
    service = context.metatype_creation_service
    status = service.start("comma")
    assert status.steps[0].state is StepState.PENDING and not status.complete
    result = service.submit_property_identity("GCOMMA_Type", "Type")
    assert not result.accepted and result.errors[0].code == "SERIES_NOT_LOADED"
    assert service.identity is None


def test_loaded_series_with_no_metatype_yet_is_allowed_but_flagged(root, context):
    build(root, "newfam", types="# nothing\r\n")
    service = context.metatype_creation_service
    status = service.start("newfam")
    assert status.steps[0].state is StepState.DONE and "no_examples" not in status.steps[0].detail
    assert service.inspection.target.status is SeriesStatus.NO_EXAMPLES
    assert any("reference" in w.lower() or "no usable" in w.lower() for w in status.warnings)


# Step 3 ----------------------------------------------------------------------------------------------------------------
def test_valid_identity_is_confirmed_and_kept(root, context):
    build(root)
    service = context.metatype_creation_service
    service.start("atlas")
    result = service.submit_property_identity(" GATLAS_Surface ", " Surface type ")
    assert result.accepted and not result.errors
    assert (result.identity.name, result.identity.label, result.identity.series) == ("GATLAS_Surface", "Surface type", "atlas")
    assert result.identity.inspection_inspected_at == service.inspection.inspected_at
    assert service.identity is result.identity
    assert service.stage_status().steps[2].state is StepState.DONE


def test_invalid_identity_is_rejected_and_does_not_replace_the_earlier_one(root, context):
    build(root)
    service = context.metatype_creation_service
    service.start("atlas")
    first = service.submit_property_identity("GATLAS_Surface", "Surface").identity
    for name, label, code in (("", "x", "NAME_EMPTY"), ("Surface", "x", "NAME_START"),
                              ("GATLAS_Süß", "x", "NAME_CHARACTERS"), ("GATLAS Surface", "x", "NAME_CHARACTERS"),
                              ("GType", "x", "NAME_RESERVED"), ("GATLAS_Ok", "", "LABEL_EMPTY"),
                              ("GATLAS_Ok", "a\x07b", "LABEL_CONTROL_CHARACTER")):
        result = service.submit_property_identity(name, label)
        assert not result.accepted and code in {f.code for f in result.errors}, (name, label)
    assert service.identity is first


def test_identity_without_a_loaded_series_or_pattern_is_rejected(root, context):
    service = context.metatype_creation_service
    result = service.submit_property_identity("GATLAS_X", "X")
    assert not result.accepted and result.errors[0].code == "SERIES_NOT_LOADED"
    build(root)
    service.start("atlas")
    service._state().pattern_selection = None
    result = service.submit_property_identity("GATLAS_X", "X")
    assert not result.accepted and result.errors[0].code == "PATTERN_NOT_SELECTED"


def test_choosing_another_series_resets_the_workflow(root, context):
    build(root, "atlas")
    build(root, "pullman")
    service = context.metatype_creation_service
    service.start("atlas")
    service.submit_property_identity("GATLAS_Surface", "Surface")
    service.start("pullman")
    assert service.series == "pullman" and service.identity is None


def test_step3_writes_nothing_to_the_repository(root, context):
    data = build(root)
    before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()}
    service = context.metatype_creation_service
    service.start("atlas")
    service.submit_property_identity("GATLAS_Surface", "Surface")
    assert {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()} == before
    assert sorted(p.name for p in root.iterdir()) == ["atlas"]


# the identity rules in isolation ------------------------------------------------------------------------------------
def conventions(root, context) -> SeriesConventions:
    build(root)
    return context.metatype_series_service.inspect_series("atlas").target


def test_existing_name_is_a_warning_with_its_source_row(root, context):
    target = conventions(root, context)
    findings = validate_property_identity("GATLAS_Tray", "Tray", target)
    exists = [f for f in findings if f.code == "NAME_EXISTS"]
    assert exists and exists[0].severity is Severity.WARNING
    assert exists[0].evidence.table == "go_types" and exists[0].evidence.values[:2] == ("MT_ATLAS", "GATLAS_Tray")
    assert not [f for f in findings if f.severity is Severity.ERROR]


def test_prefix_not_used_by_the_series_is_a_warning_not_an_error(root, context):
    target = conventions(root, context)
    mismatch = [f for f in validate_property_identity("GOTHER_Thing", "Thing", target) if f.code == "PREFIX_MISMATCH"]
    assert mismatch and mismatch[0].severity is Severity.WARNING and "GATLAS_" in mismatch[0].message
    assert not [f for f in validate_property_identity("GATLAS_Thing", "Thing", target) if f.code == "PREFIX_MISMATCH"]
    assert [f.code for f in validate_property_identity("GThing", "Thing", target)].count("PREFIX_MISMATCH") == 1


def test_series_without_prefix_convention_skips_the_prefix_check(root, context):
    build(root, "bare", types="MT_B ;GType ;  ;B ;0 ;\r\nMT_B ;GWidth ;na ;1 ;1 ;\r\n")
    target = context.metatype_series_service.inspect_series("bare").target
    codes = [f.code for f in validate_property_identity("GBARE_Type", "Type", target)]
    assert "PREFIX_NO_CONVENTION" in codes and "PREFIX_MISMATCH" not in codes


def test_underscores_are_accepted_and_hard_rules_cite_their_source():
    findings = validate_property_identity("GATLAS_Example", "Example", None)
    assert findings == []
    bad = validate_property_identity("atlas", "x", None)
    assert bad[0].code == "NAME_START" and "MT_1.18.0" in bad[0].basis


# the completion gate ------------------------------------------------------------------------------------------------------
def test_gate_stays_closed_while_template_steps_are_unimplemented(root, context):
    build(root)
    service = context.metatype_creation_service
    service.start("atlas")
    service.submit_property_identity("GATLAS_Surface", "Surface")
    status = service.stage_status()
    assert [s.key for s in status.steps] == ["1", "2", "3", "4", "4a", "5", "6", "6w"]
    assert [s.state for s in status.steps[:3]] == [StepState.DONE] * 3
    assert status.steps[3].state is StepState.PENDING                      # Step 4 exists but is unanswered
    assert status.steps[4].state is StepState.PENDING                      # Step 4a exists but is unanswered
    assert status.steps[5].state is StepState.PENDING                      # Step 5 exists but is unanswered
    assert status.steps[6].state is StepState.PENDING and status.steps[7].state is StepState.NOT_IMPLEMENTED
    assert not status.complete and not status.children_unlocked and not service.can_start_children()
    assert len(status.blocking) == 5 and status.blocking[0].startswith("Step 4")
    assert "locked" in service.summary_text()


def test_gate_opens_only_when_every_step_is_done(root, context, monkeypatch):
    build(root)
    service = context.metatype_creation_service
    service.start("atlas")
    monkeypatch.setattr(creation_module, "_NOT_IMPLEMENTED", ())
    assert not service.stage_status().children_unlocked          # Step 3 still pending
    service.submit_property_identity("GATLAS_Surface", "Surface")
    assert not service.stage_status().children_unlocked          # Step 4 still pending
    service.submit_polymorphism_branch(["A1", "A2"], "unconditional", [], True)
    assert not service.stage_status().children_unlocked          # Step 4a still pending
    service.submit_value_validity(True)
    assert not service.stage_status().children_unlocked          # Step 5 still pending
    service.submit_translations([TranslationRow("GATLAS_Surface", TranslationKind.PROPERTY, "", "a", "b", "c")])
    assert not service.stage_status().children_unlocked          # Step 6 confirmation still pending
    assert service.confirm_specification().accepted
    status = service.stage_status()
    assert status.complete and status.children_unlocked and not status.blocking


def test_state_survives_navigation_and_staleness_is_flagged(root, context):
    data = build(root)
    service = context.metatype_creation_service
    service.start("atlas")
    service.submit_property_identity("GATLAS_Surface", "Surface")
    assert context.metatype_creation_service.identity.name == "GATLAS_Surface"      # same session state
    (data / "go_proporder.csv").write_text("A;10\r\n", encoding="utf-8")
    assert any("changed since" in w for w in service.stage_status().warnings)


def test_unloaded_stage_reports_why_it_is_blocked(context):
    status = context.metatype_creation_service.stage_status()
    assert status.blocking == ["No series has been loaded."] and not status.children_unlocked


# page ----------------------------------------------------------------------------------------------------------------------------
def test_sidebar_progress_uses_stage_specific_readiness(root, context):
    from PySide6.QtWidgets import QApplication, QStackedWidget
    from ui.pages.metatype_creation_page import MetatypeCreationPage
    from workflow.host import WorkspaceHost
    from workflow.manager import WorkflowManager

    app = QApplication.instance() or QApplication([])
    build(root, "atlas")
    page = MetatypeCreationPage(context)
    stack = QStackedWidget()
    stack.addWidget(page)
    steps = (
        WorkflowStep.METATYPE_ARTICLES,
        WorkflowStep.METATYPE_PROPERTIES,
        WorkflowStep.METATYPE_VALUES,
        WorkflowStep.METATYPE_TEXTS,
        WorkflowStep.METATYPE_SETUP,
        WorkflowStep.METATYPE_RELATIONS,
        WorkflowStep.METATYPE_REVIEW,
    )
    manager = WorkflowManager(context, WorkspaceHost(stack, {step: page for step in steps}), list(steps))
    assert manager.progress() == (0, 7)

    context.metatype_creation_service.start("atlas")
    manager.refresh()
    assert manager.progress() == (0, 7), "loading a series must not mark all shared-page stages complete"

    context.metatype_creation_service.submit_property_identity("GATLAS_Surface", "Surface")
    manager.refresh()
    assert manager.progress() == (1, 7)
    assert manager.is_ready(WorkflowStep.METATYPE_PROPERTIES)
    assert not manager.is_ready(WorkflowStep.METATYPE_ARTICLES)
    assert not manager.is_ready(WorkflowStep.METATYPE_VALUES)
    assert not manager.is_ready(WorkflowStep.METATYPE_TEXTS)
    assert not manager.is_ready(WorkflowStep.METATYPE_SETUP)
    assert not manager.is_ready(WorkflowStep.METATYPE_RELATIONS)
    assert not manager.is_ready(WorkflowStep.METATYPE_REVIEW)
    assert manager.session.state.value == "in_progress"
    assert "HMX series" in manager.recommended_action()
    app.processEvents()


def test_creation_page_flow(root, context):
    from PySide6.QtWidgets import QApplication
    from ui.pages.metatype_creation_page import MetatypeCreationPage

    app = QApplication.instance() or QApplication([])
    build(root, "atlas")
    build(root, "comma", with_schema=False)
    page = MetatypeCreationPage(context)
    assert [page.series_combo.itemText(i) for i in range(page.series_combo.count())] == [
        "atlas", "comma (no Metatype data)"]
    assert page.workspace_stack.count() == 7
    assert page.findChild(object, "metatypeWorkspaceTabs") is None
    from core.enums import WorkflowStep
    for step, index in (
        (WorkflowStep.METATYPE_ARTICLES, 0),
        (WorkflowStep.METATYPE_PROPERTIES, 1),
        (WorkflowStep.METATYPE_VALUES, 2),
        (WorkflowStep.METATYPE_TEXTS, 3),
        (WorkflowStep.METATYPE_SETUP, 4),
        (WorkflowStep.METATYPE_RELATIONS, 5),
        (WorkflowStep.METATYPE_REVIEW, 6),
    ):
        page.select_workflow_stage(step)
        assert page.workspace_stack.currentIndex() == index
    assert page.findChild(object, "metatypeSetupPlaceholder") is not None
    assert page.findChild(object, "metatypeRelationsPlaceholder") is not None
    assert not page.findChild(object, "metatypeScanButton")                  # no investigation controls
    assert not page._identity_group.isEnabled() and not page.children_button.isEnabled()

    page.series_combo.setCurrentIndex(0)
    page.load_button.click()
    assert page._identity_group.isEnabled()
    assert "Step 3" in page.status_output.toPlainText()

    page.name_edit.setText("Surface")
    page.label_edit.setText("Surface")
    page.confirm_button.click()
    assert "NAME_START" in page.findings_output.toPlainText()
    page.name_edit.setText("GATLAS_Surface")
    page.confirm_button.click()
    assert "confirmed" in page.findings_output.toPlainText()
    assert "[done] Step 3" in page.status_output.toPlainText()
    assert not page.children_button.isEnabled()
    assert "Locked" in page.children_button.toolTip()

    page.series_combo.setCurrentIndex(1)
    page.load_button.click()
    assert not page._identity_group.isEnabled()
    app.processEvents()
