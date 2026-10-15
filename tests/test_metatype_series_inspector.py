"""Metatype Step 1 (inspect_series): conventions summary from real-format series data."""
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from core.application_context import ApplicationContext
from core.config import AppConfig
from models.metatype_tables import TableLoadState  # noqa: F401
from services.metatype.metatype_table_loader import MetatypeTableLoader
from models.metatype_series import InspectionStatus, SeriesStatus
from services.metatype.series_inspector import (
    EXCLUDED_TABLES,
    STEP1_TABLES,
    TEMPLATE_REFERENCE_SERIES,
    UNRESOLVED,
    SeriesInspector,
    format_inspection_summary,
)

COLUMNS = {
    "go_types": "id name format default mode filter",
    "go_propvalues": "id name value condition",
    "go_proporder": "value number",
    "go_children": "child_key manufacturer program article_nr variant pos_x pos_y pos_z condition",
    "go_texts": "key language text",
}

# Shapes taken from atlas / pullman.
TYPES = (
    "# types\r\n"
    "MT_ATLAS_Table ;GType       ;   ;ATLAS_Table ;0 ;\r\n"
    "MT_ATLAS_Table ;GMode       ;   ;OCD         ;0 ;\r\n"
    "MT_ATLAS_Table ;GATLAS_Type ;ch ;ATLAS_Type_SG ;131 ;\r\n"
    "MT_ATLAS_Table ;GATLAS_Tray ;ch ;ATLAS_ST_None ;8329 ;\r\n"
    "MT_ATLAS_Table ;GATLAS_Kit  ;ch ;ATLAS_K_No ;11 ;\r\n"
    "MT_ATLAS_Table ;G_Other     ;ch ;X ;1 ;\r\n"
    "MT_ATLAS_Table ;GWidth      ;na ;800 ;1 ;\r\n"
    "MT_ATLAS_Part  ;GATLAS_Part ;ch ;P ;1 ;\r\n"
)
GOOD = {
    "go_types": TYPES,
    "go_propvalues": (
        "# only evaluated when flag 8192\r\n"
        "MT_ATLAS_Table ;GATLAS_Tray ;ATLAS_ST_None ;\r\n"
        "MT_ATLAS_Table ;GATLAS_Tray ;ATLAS_ST_Slim ;GATLAS_Type != @ATLAS_Type_PT\r\n"
        "MT_ATLAS_Table ;GATLAS_Kit  ;ATLAS_K_No ;\r\n"
    ),
    "go_proporder": "# order\r\nATLAS_Type_SG;  10\r\nATLAS_Type_SA;  20\r\nATLAS_Type_PR;  30\r\n",
    "go_children": (
        "CH_A;hmx;atlas;PIA1;;0;0;0;GATLAS_Type == @ATLAS_Type_SG\r\n"
        "CH_A;hmx;atlas;PIA1;;1;0;0;GATLAS_Type == @ATLAS_Type_SA\r\n"
        "CH_B;hmx;atlas;PIA2;;0;0;0;\r\n"
    ),
    "go_texts": b"K;en;caf\xe9\r\n",   # legacy code page: must never be decoded by Step 1
}


def schema(tables=COLUMNS) -> str:
    text = "# GO III (MT) Input Description, Version 1.16\n\n"
    for table, columns in tables.items():
        names = columns.split()
        text += f"table   {table}\t{table}.csv\t\tcsv\nfields  {len(names)}\n"
        text += "".join(f"field   {i}  {n}\t\tvstring\t\tdelim ; trim\n" for i, n in enumerate(names, 1))
    return text


def build(root: Path, name="atlas", files=None, tables=COLUMNS, with_schema=True) -> Path:
    data = root / name / "1"
    data.mkdir(parents=True, exist_ok=True)
    if with_schema:
        (data / "mt.inp_descr").write_text(schema(tables), encoding="utf-8")
    content = dict(GOOD)
    content.update(files or {})
    for table in tables:
        value = content.get(table)
        if value is None:
            continue
        (data / f"{table}.csv").write_bytes(value if isinstance(value, bytes) else value.encode("utf-8"))
    return data


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "hmx"
    path.mkdir()
    return path


def inspect(root, family="atlas", **kwargs):
    return SeriesInspector().inspect_series(root, family, **kwargs)


# the template's Step 1 contract ------------------------------------------------------------------------
def test_contract_reads_exactly_the_template_tables_and_leaves_texts_alone():
    assert STEP1_TABLES == ("go_types", "go_propvalues", "go_proporder", "go_children")
    assert EXCLUDED_TABLES == ("go_texts",)
    assert TEMPLATE_REFERENCE_SERIES == ("atlas", "pullman")


def test_go_texts_is_neither_inspected_nor_reported_as_a_source(root):
    build(root)
    result = inspect(root)
    assert result.status is InspectionStatus.OK
    assert [s.table for s in result.target.sources] == list(STEP1_TABLES)
    assert result.excluded_tables == ["go_texts"]
    assert "go_texts.csv" not in json.dumps(result.to_dict()["target"])


# go_types ---------------------------------------------------------------------------------------------
def test_types_naming_prefixes_formats_and_settings(root):
    build(root)
    t = inspect(root).target.types
    assert t.metatype_count == 2
    assert {m.id: (m.property_count, m.setting_count) for m in t.metatypes} == {
        "MT_ATLAS_Table": (5, 2), "MT_ATLAS_Part": (1, 0)}
    assert [(p.value, p.count) for p in t.metatype_id_prefixes] == [("MT_", 2)]
    prefixes = {p.value: p.count for p in t.property_prefixes}
    assert prefixes == {"GATLAS_": 4, "G_": 1}                      # the na wrapper GWidth is not a series name
    assert t.native_wrapper_count == 1 and t.native_wrapper_examples[0].values[1] == "GWidth"
    assert t.template_prefix == "GATLAS_" and t.properties_following_template_prefix == 4
    assert {s.value for s in t.settings} == {"GType = ATLAS_Table", "GMode = OCD"}
    assert {f.value: f.count for f in t.formats} == {"ch": 5, "na": 1}


def test_unprefixed_non_native_properties_stay_visible_as_their_own_group(root):
    build(root, files={"go_types": "MT_X;GArm;ch;A;1;\r\nMT_X;GHeightCorrection;fn;0;1;\r\nMT_X;GDepth;na;600;1;\r\n"})
    t = inspect(root).target.types
    assert {p.value: p.count for p in t.property_prefixes} == {"(no underscore)": 2}
    assert t.native_wrapper_count == 1


def test_step1_loads_only_its_tables_and_never_opens_go_texts(root):
    build(root)
    opened = []

    class Recording(MetatypeTableLoader):
        def _read_bytes(self, path, limit):
            opened.append(Path(path).name)
            return super()._read_bytes(path, limit)

    result = SeriesInspector(Recording()).inspect_series(root, "atlas")
    assert result.status is InspectionStatus.OK
    assert sorted(opened) == sorted(["mt.inp_descr"] + [f"{t}.csv" for t in STEP1_TABLES])
    assert "go_texts.csv" not in opened


def test_loader_default_still_loads_every_declared_table(root):
    build(root)
    everything = MetatypeTableLoader().load_family(root, "atlas")
    assert [t.table for t in everything.tables] == list(COLUMNS)
    subset = MetatypeTableLoader().load_family(root, "atlas", tables=["go_types"])
    assert [t.table for t in subset.tables] == ["go_types"] and subset.unlisted_go_files == []


def test_types_modes_and_documented_bits_keep_row_evidence(root):
    build(root)
    t = inspect(root).target.types
    by_mode = {m.mode: m for m in t.modes}
    assert by_mode[131].bits == [1, 2, 128]
    assert by_mode[8329].bits == [1, 8, 128, 8192]
    assert by_mode[131].evidence[0].table == "go_types" and by_mode[131].evidence[0].line == 4
    assert by_mode[131].evidence[0].values[1] == "GATLAS_Type"
    assert [p.name for p in t.polymorphism_properties] == []          # no row has bit 4
    assert [p.name for p in t.child_properties] == ["GATLAS_Tray", "GATLAS_Kit"]
    assert [p.name for p in t.ordered_properties] == ["GATLAS_Type", "GATLAS_Tray"]
    assert [p.name for p in t.value_limited_properties] == ["GATLAS_Tray"]
    assert t.bit_counts[1] == sum(1 for m in t.modes if 1 in m.bits for _ in range(m.count))


def test_polymorphism_bit_is_listed_separately_from_child_bit(root):
    build(root, files={"go_types": "MT_X;GX_Type;ch;A;5;\r\nMT_X;GX_Head;ch;N;9;\r\n"})
    t = inspect(root).target.types
    assert [p.name for p in t.polymorphism_properties] == ["GX_Type"]
    assert [p.name for p in t.child_properties] == ["GX_Head"]


def test_non_numeric_mode_is_reported_not_guessed(root):
    build(root, files={"go_types": "MT_X;GX_A;ch;A;abc;\r\nMT_X;GX_B;ch;A;1;\r\n"})
    t = inspect(root).target.types
    assert [e.line for e in t.non_numeric_modes] == [1]
    assert [m.mode for m in t.modes] == [1]


# go_propvalues / go_proporder / go_children ---------------------------------------------------------------
def test_propvalues_structure_and_flag_consistency(root):
    build(root)
    v = inspect(root).target.propvalues
    assert (v.row_count, v.rows_with_condition) == (3, 1)
    assert {p.value: p.count for p in v.properties} == {
        "MT_ATLAS_Table / GATLAS_Tray": 2, "MT_ATLAS_Table / GATLAS_Kit": 1}
    assert v.condition_examples[0].line == 3
    assert v.rows_without_flag == ["MT_ATLAS_Table / GATLAS_Kit"]   # rows exist but 8192 is not set
    assert v.flagged_without_rows == []


def test_flag_without_rows_is_reported(root):
    build(root, files={"go_propvalues": ""})
    assert inspect(root).target.propvalues.flagged_without_rows == ["MT_ATLAS_Table / GATLAS_Tray"]


def test_proporder_numbers_and_step(root):
    build(root)
    o = inspect(root).target.proporder
    assert (o.row_count, o.min_number, o.max_number, o.common_step) == (3, 10, 30, 10)
    assert [e.values for e in o.entries][0] == ("ATLAS_Type_SG", "10")
    build(root, files={"go_proporder": "A;x\r\nB;5\r\n"})
    o = inspect(root).target.proporder
    assert [e.line for e in o.non_numeric] == [1] and o.common_step is None


def test_children_patterns(root):
    build(root)
    c = inspect(root).target.children
    assert (c.row_count, c.distinct_keys, c.rows_with_condition) == (3, 2, 2)
    assert [(k.value, k.count) for k in c.key_prefixes] == [("CH_", 3)]
    assert [(k.value, k.count) for k in c.repeated_keys] == [("CH_A", 2)]
    assert c.manufacturers[0].value == "hmx" and c.programs[0].value == "atlas"
    assert c.condition_examples[0].values[-1] == "GATLAS_Type == @ATLAS_Type_SG"


# missing / insufficient data ---------------------------------------------------------------------------
def test_missing_empty_and_undecodable_tables_are_reported(root):
    build(root, files={"go_propvalues": None, "go_proporder": "", "go_children": b"CH;\xe4;x\r\n"})
    series = inspect(root).target
    states = {s.table: s.state for s in series.sources}
    assert states["go_propvalues"] == "missing" and states["go_proporder"] == "empty"
    assert states["go_children"] == "decode_error"
    text = " ".join(series.notes)
    assert "go_propvalues.csv is missing" in text and "go_proporder.csv holds no data rows" in text
    assert "go_children.csv is decode_error" in text
    assert series.status is SeriesStatus.OK            # go_types still gives examples


def test_malformed_lines_flag_partial_counts(root):
    build(root, files={"go_children": "CH_A;hmx;atlas\r\nCH_B;hmx;atlas;P;;0;0;0;\r\n"})
    series = inspect(root).target
    assert series.children.row_count == 1
    assert any("rejected while loading" in n for n in series.notes)


def test_table_without_required_column_is_not_inspected(root):
    tables = dict(COLUMNS, go_proporder="value")
    build(root, tables=tables, files={"go_proporder": "A\r\n"})
    series = inspect(root).target
    assert series.proporder.row_count == 0 and any("lacks column" in n for n in series.notes)


def test_target_without_schema_fails_and_is_insufficient_without_references(root):
    build(root, "newseries", with_schema=False)
    result = inspect(root, "newseries")
    assert result.target.status is SeriesStatus.FAILED
    assert any("SCHEMA_MISSING" in n for n in result.target.notes)
    assert result.status is InspectionStatus.INSUFFICIENT
    assert [r.family_id for r in result.references] == ["atlas", "pullman"]     # template defaults, tried
    assert all(r.status is SeriesStatus.FAILED for r in result.references)


def test_blank_request_is_rejected(root):
    result = inspect(root, "  ")
    assert result.status is InspectionStatus.FAILED and result.target is None


# reference-series fallback ----------------------------------------------------------------------------------
def test_no_metatype_in_target_uses_template_reference_series(root):
    build(root, "newseries", files={"go_types": "# nothing yet\r\n"})
    build(root, "atlas")
    result = inspect(root, "newseries")
    assert result.target.status is SeriesStatus.NO_EXAMPLES
    assert result.status is InspectionStatus.REFERENCE_ONLY
    assert "template" in result.reference_reason and result.references[0].types.metatype_count == 2
    assert result.references[1].status is SeriesStatus.FAILED                    # pullman absent: reported


def test_references_are_not_used_when_target_has_examples(root):
    build(root, "pullman")
    build(root, "atlas")
    result = inspect(root, "pullman")
    assert result.status is InspectionStatus.OK and result.references == []


def test_explicit_references_are_always_inspected_and_never_include_the_target(root):
    build(root, "atlas")
    build(root, "layout_studio")
    result = inspect(root, "atlas", reference_series=["layout_studio", "atlas", "layout_studio"])
    assert [r.family_id for r in result.references] == ["layout_studio"]
    assert result.status is InspectionStatus.OK and "caller" in result.reference_reason


def test_unresolved_template_decisions_are_carried_on_every_result(root):
    build(root)
    unresolved = " ".join(inspect(root).unresolved)
    assert unresolved == " ".join(UNRESOLVED)
    assert "hmx/layout" in unresolved and "'few' is not defined" in unresolved


# docs notes ----------------------------------------------------------------------------------------------------
def test_series_markdown_notes_are_listed_but_not_read(root):
    build(root)
    (root / "atlas" / "docs").mkdir()
    (root / "atlas" / "docs" / "metatype_notes.md").write_text("notes", encoding="utf-8")
    series = inspect(root).target
    assert [Path(p).name for p in series.docs_files] == ["metatype_notes.md"]
    assert not any("No in-series" in n for n in series.notes)


def test_missing_docs_are_stated(root):
    build(root)
    assert any("No in-series .md notes" in n for n in inspect(root).target.notes)


# evidence, persistence, staleness -------------------------------------------------------------------------------
def test_sources_identify_files_for_staleness_checks(root):
    data = build(root)
    inspector = SeriesInspector()
    result = inspector.inspect_series(root, "atlas")
    src = {s.table: s for s in result.target.sources}["go_types"]
    assert src.path == str(data / "go_types.csv") and src.row_count == 8 and src.modified_ns
    assert src.size_bytes == (data / "go_types.csv").stat().st_size
    assert inspector.check_staleness(result) == []

    (data / "go_types.csv").write_bytes(TYPES.encode() + b"MT_ATLAS_Part ;GATLAS_X ;ch ;P ;1 ;\r\n")
    assert inspector.check_staleness(result) == [str(data / "go_types.csv")]
    (data / "go_proporder.csv").unlink()
    assert str(data / "go_proporder.csv") in inspector.check_staleness(result)


def test_result_serialises_to_json_and_is_not_written_anywhere(root, tmp_path):
    build(root)
    before = sorted(p.name for p in tmp_path.rglob("*"))
    result = inspect(root)
    payload = json.dumps(result.to_dict())
    assert json.loads(payload)["target"]["types"]["metatype_count"] == 2
    assert sorted(p.name for p in tmp_path.rglob("*")) == before


def test_inspection_never_changes_the_repository(root):
    data = build(root)
    snapshot = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()}
    inspect(root)
    inspect(root, reference_series=["atlas"])
    assert {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in data.iterdir()} == snapshot


def test_summary_text_mentions_prefixes_exclusions_and_open_decisions(root):
    build(root)
    text = format_inspection_summary(inspect(root))
    assert "Series conventions for atlas - ok" in text and "GATLAS_" in text and "MT_" in text
    assert "Not read: go_texts" in text and "Open decisions:" in text


# integration with the Metatype module -------------------------------------------------------------------------------
def test_service_inspects_through_the_context_and_refreshes_on_request(root):
    build(root)
    context = ApplicationContext(AppConfig(metatype_repository_root=str(root)))
    service = context.metatype_series_service
    assert service is context.metatype_series_service and service.last_result is None
    first = service.inspect_series("atlas")
    assert service.last_result is first and first.status is InspectionStatus.OK
    assert service.stale_sources() == []

    data = root / "atlas" / "1"
    (data / "go_proporder.csv").write_text("A;10\r\n", encoding="utf-8")
    assert service.stale_sources() == [str(data / "go_proporder.csv")]
    second = service.inspect_series("atlas")                                   # explicit refresh
    assert second is not first and second.target.proporder.row_count == 1 and service.stale_sources() == []


def test_page_inspects_the_selected_family(root):
    from PySide6.QtWidgets import QApplication
    from ui.pages.metatype_repository_page import MetatypeRepositoryPage

    app = QApplication.instance() or QApplication([])
    build(root)
    page = MetatypeRepositoryPage(ApplicationContext(AppConfig(metatype_repository_root=str(root))))
    page.scan_button.click()
    assert not page.inspect_button.isEnabled()
    page.table.selectRow(0)
    assert page.inspect_button.isEnabled()
    page.inspect_button.click()
    assert "Series conventions for atlas - ok" in page.load_output.toPlainText()
    app.processEvents()
