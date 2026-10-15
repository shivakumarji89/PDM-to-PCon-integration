"""Metatype creation Step 2: choose Polymorphism Metatype or Metatype with Childs."""
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from core.application_context import ApplicationContext
from core.config import AppConfig
from models.metatype_pattern import (
    PATTERN_OPTIONS,
    MetatypePattern,
    SelectionStatus,
)

COLUMNS = {
    "go_types": "id name format default mode filter",
    "go_propvalues": "id name value condition",
    "go_proporder": "value number",
    "go_children": "child_key manufacturer program article_nr variant pos_x pos_y pos_z condition",
}


def build(root: Path, name: str, types: str = "MT_X ;GX_Type ;ch ;A ;131 ;\r\n") -> None:
    data = root / name / "1"
    data.mkdir(parents=True, exist_ok=True)
    text = "# GO III (MT) Input Description, Version 1.16\n\n"
    for table, columns in COLUMNS.items():
        names = columns.split()
        text += f"table   {table}\t{table}.csv\t\tcsv\nfields  {len(names)}\n"
        text += "".join(f"field   {i}  {n}\t\tvstring\t\tdelim ; trim\n" for i, n in enumerate(names, 1))
    (data / "mt.inp_descr").write_text(text, encoding="utf-8")
    for table in COLUMNS:
        (data / f"{table}.csv").write_text(types if table == "go_types" else "", encoding="utf-8")


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "hmx"
    path.mkdir()
    return path


@pytest.fixture
def context(root):
    return ApplicationContext(AppConfig(metatype_repository_root=str(root)))


# the template's Step 2 contract ---------------------------------------------------------------------------
def test_exactly_the_two_template_options_with_template_wording(context):
    options = context.metatype_pattern_service.options()
    assert options is PATTERN_OPTIONS
    assert [(o.pattern, o.label) for o in options] == [
        (MetatypePattern.POLYMORPHISM, "Polymorphism Metatype"),
        (MetatypePattern.WITH_CHILDS, "Metatype with Childs"),
    ]
    assert "no parent/child structure" in options[0].description
    assert "attaches/controls child articles" in options[1].description


def test_a_choice_needs_a_step1_summary_for_that_series(root, context):
    build(root, "fam")
    service = context.metatype_pattern_service
    assert not service.can_select("fam")
    result = service.select_pattern("fam", MetatypePattern.POLYMORPHISM)
    assert result.status is SelectionStatus.REJECTED and result.selection is None
    assert "Step 1 has not been run for 'fam'" in result.errors[0]
    assert service.last_selection is None

    context.metatype_series_service.inspect_series("fam")
    assert service.can_select("fam") and not service.can_select("other")
    other = service.select_pattern("other", "with_childs")
    assert other.status is SelectionStatus.REJECTED and "'other'" in other.errors[0]


def test_choice_is_recorded_with_its_step1_provenance(root, context):
    build(root, "fam")
    inspection = context.metatype_series_service.inspect_series("fam")
    service = context.metatype_pattern_service
    result = service.select_pattern("fam", "with_childs")        # plain string value is accepted
    assert result.status is SelectionStatus.SELECTED and not result.warnings and not result.errors
    selection = result.selection
    assert selection.pattern is MetatypePattern.WITH_CHILDS and selection.series == "fam"
    assert selection.inspection_inspected_at == inspection.inspected_at
    assert selection.inspection_status == "ok"
    assert service.last_selection is selection and service.selection_for("fam") is selection
    assert service.selection_for("other") is None
    assert json.loads(json.dumps(result.to_dict()))["selection"]["pattern"] == "with_childs"


def test_choosing_again_replaces_the_earlier_answer(root, context):
    build(root, "fam")
    context.metatype_series_service.inspect_series("fam")
    service = context.metatype_pattern_service
    service.select_pattern("fam", MetatypePattern.POLYMORPHISM)
    service.select_pattern("fam", MetatypePattern.WITH_CHILDS)
    assert service.last_selection.pattern is MetatypePattern.WITH_CHILDS


def test_unknown_pattern_is_rejected_and_keeps_the_previous_choice(root, context):
    build(root, "fam")
    context.metatype_series_service.inspect_series("fam")
    service = context.metatype_pattern_service
    service.select_pattern("fam", MetatypePattern.POLYMORPHISM)
    for bad in ("", "both", None):
        result = service.select_pattern("fam", bad)
        assert result.status is SelectionStatus.REJECTED and "Unknown pattern" in result.errors[0]
    assert service.last_selection.pattern is MetatypePattern.POLYMORPHISM


def test_blank_series_is_rejected(context):
    result = context.metatype_pattern_service.select_pattern("  ", MetatypePattern.POLYMORPHISM)
    assert result.status is SelectionStatus.REJECTED and result.errors


def test_failed_or_sparse_step1_is_handled_without_guessing(root, context):
    # No schema at all: Step 1 cannot summarise the series, but it still produced a (sparse) result.
    (root / "bare" / "1").mkdir(parents=True)
    inspection = context.metatype_series_service.inspect_series("bare")
    assert inspection.status.value == "insufficient"
    result = context.metatype_pattern_service.select_pattern("bare", MetatypePattern.POLYMORPHISM)
    assert result.status is SelectionStatus.SELECTED
    assert "no usable Metatype examples" in result.warnings[0]

    blank = context.metatype_series_service.inspect_series(" ")
    assert blank.status.value == "failed"
    assert not context.metatype_pattern_service.can_select(" ")


def test_reference_only_step1_is_flagged(root, context):
    build(root, "atlas")
    (root / "newfam" / "1").mkdir(parents=True)
    context.metatype_series_service.inspect_series("newfam")
    result = context.metatype_pattern_service.select_pattern("newfam", MetatypePattern.WITH_CHILDS)
    assert result.status is SelectionStatus.SELECTED and "reference series" in result.warnings[0]


def test_stale_step1_sources_are_flagged_not_blocked(root, context):
    build(root, "fam")
    context.metatype_series_service.inspect_series("fam")
    (root / "fam" / "1" / "go_proporder.csv").write_text("A;10\r\n", encoding="utf-8")
    result = context.metatype_pattern_service.select_pattern("fam", MetatypePattern.POLYMORPHISM)
    assert result.status is SelectionStatus.SELECTED and "changed since Step 1" in result.warnings[0]


def test_step2_changes_nothing_in_the_repository(root, context):
    build(root, "fam")
    context.metatype_series_service.inspect_series("fam")
    data = root / "fam" / "1"
    before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()}
    context.metatype_pattern_service.select_pattern("fam", MetatypePattern.WITH_CHILDS)
    assert {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()} == before


def test_summary_text(root, context):
    build(root, "fam")
    context.metatype_series_service.inspect_series("fam")
    service = context.metatype_pattern_service
    assert "Step 2 - fam: Metatype with Childs" in service.summary_text(
        service.select_pattern("fam", MetatypePattern.WITH_CHILDS))
    assert "no pattern selected" in service.summary_text(service.select_pattern("fam", "x"))


# page ---------------------------------------------------------------------------------------------------------------
def test_page_offers_both_choices_and_enables_selection_only_after_step1(root, context):
    from PySide6.QtWidgets import QApplication
    from ui.pages.metatype_repository_page import MetatypeRepositoryPage

    app = QApplication.instance() or QApplication([])
    build(root, "fam")
    page = MetatypeRepositoryPage(context)
    assert [page.pattern_combo.itemText(i) for i in range(page.pattern_combo.count())] == [
        "Polymorphism Metatype", "Metatype with Childs"]
    page.scan_button.click()
    page.table.selectRow(0)
    assert not page.pattern_button.isEnabled()

    page.inspect_button.click()
    assert page.pattern_button.isEnabled()
    page.pattern_combo.setCurrentIndex(1)
    page.pattern_button.click()
    assert "Step 2 - fam: Metatype with Childs" in page.load_output.toPlainText()
    assert context.metatype_pattern_service.last_selection.pattern is MetatypePattern.WITH_CHILDS
    app.processEvents()
