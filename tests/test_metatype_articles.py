"""Articles reconciliation: synthetic fixtures in temp directories (never the real HMX repository)."""
import hashlib
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt

from core.application_context import ApplicationContext
from core.config import AppConfig
from models.metatype_articles import ReconciliationStatus
from services.metatype.metatype_article_service import MetatypeArticleService

FIELD = "field   {}  {}\t\tvstring\t\tdelim ; trim\n"


def declare(table, columns):
    return (f"table   {table}\t{table}.csv\t\tcsv\nfields  {len(columns)}\n"
            + "".join(FIELD.format(i, c) for i, c in enumerate(columns, 1)) + "\n")


def make_series(root: Path, files: dict[str, str], schema: str, name="atlas"):
    data = root / name / "1"
    data.mkdir(parents=True)
    (data / "mt.inp_descr").write_text("name go_tables\n\n" + schema, encoding="utf-8")
    for file, text in files.items():
        (data / file).write_text(text, encoding="utf-8")
    return data


EXAMPLE_COLUMNS = ["metatypeid", "manufacturer", "program", "article", "configid", "childparentid"]
EXAMPLE = declare("go_articles", EXAMPLE_COLUMNS)


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "hmx"
    path.mkdir()
    return path


@pytest.fixture
def context(root):
    return ApplicationContext(AppConfig(metatype_repository_root=str(root)))


def reconcile(context, root, series="atlas"):
    return context.metatype_article_service.reconcile(series, root=root)


def row_for(rec, article):
    matches = [r for r in rec.rows if article in r.values.values()]
    assert len(matches) == 1
    return matches[0]


# 1-3, 4: example layout -------------------------------------------------------------------------------------------------
def test_example_schema_preserves_values_and_includes_unmapped(context, root):
    make_series(root, {"go_articles.csv": (
        "MT_A ; hmx ; prog ; ART1 ; CFG1 ; PARENT1\n"
        ";hmx;prog;ART2;CFG2;\n")}, EXAMPLE)
    rec = reconcile(context, root)
    assert rec.columns == EXAMPLE_COLUMNS and rec.headers[-1] == "status"
    assert [r.status for r in rec.rows] == ["Mapped", "Needs assignment"]
    first, second = rec.rows
    assert first.values == {"metatypeid": "MT_A ", "manufacturer": " hmx ", "program": " prog ",
                            "article": " ART1 ", "configid": " CFG1 ", "childparentid": " PARENT1"}  # raw, untrimmed
    assert second.values["metatypeid"] == "" and second.values["childparentid"] == ""
    assert second.values["manufacturer"] == "hmx" and second.values["configid"] == "CFG2"  # never constructed
    assert (second.source_line, Path(second.source_file).name) == (2, "go_articles.csv")
    assert rec.status is ReconciliationStatus.COMPLETE and rec.unavailable_fields == []


def test_columns_come_from_mt_inp_descr_not_from_a_fixed_layout(context, root):
    cols = ["article", "program", "manufacturer", "metatypeid", "configid"]
    make_series(root, {"go_articles.csv": "A1;p;m;MT1;C1\n"}, declare("go_articles", cols))
    rec = reconcile(context, root)
    assert rec.columns == cols and rec.rows[0].values["article"] == "A1" and rec.rows[0].status == "Mapped"
    assert rec.unavailable_fields == ["childparentid"]


# 5: alternate schema, separate mapping table ----------------------------------------------------------------------------
MAP_SCHEMA = (declare("go_articles", ["id", "manufacturer", "program", "article_nr"])
              + declare("go_mtmap", ["manufacturer", "program", "article_nr", "metatypeid", "childparentid"]))


def test_alternate_schema_joins_mapping_table_by_identity_only(context, root):
    make_series(root, {"go_articles.csv": "_native_;;;\nA;m;p;N1\nB;m;p;N2\n",
                       "go_mtmap.csv": "m;p;N2;MT9;P9\n"}, MAP_SCHEMA)
    rec = reconcile(context, root)
    assert rec.columns == ["id", "manufacturer", "program", "article_nr", "metatypeid", "childparentid"]
    assert [r.values["id"] for r in rec.rows] == ["A", "B"]          # reserved _native_ row not an article
    assert [r.status for r in rec.rows] == ["Needs assignment", "Mapped"]
    assert rec.rows[1].values["metatypeid"] == "MT9" and rec.rows[0].values["metatypeid"] == ""
    assert "configid" in rec.unavailable_fields and "metatypeid" not in rec.unavailable_fields
    assert any(d.code == "RESERVED_ROW_SKIPPED" for d in rec.diagnostics)


def test_schema_without_mapping_fields_is_partial_and_never_maps_id(context, root):
    make_series(root, {"go_articles.csv": "7;m;p;N1\n"}, declare("go_articles", ["id", "manufacturer", "program", "article_nr"]))
    rec = reconcile(context, root)
    assert rec.status is ReconciliationStatus.PARTIAL
    assert rec.unavailable_fields == ["metatypeid", "childparentid", "configid"]
    assert rec.rows[0].status == "Mapping unavailable" and rec.rows[0].values["id"] == "7"
    assert any(d.code == "MAPPING_FIELD_UNAVAILABLE" for d in rec.diagnostics)


# 6-8: source problems ---------------------------------------------------------------------------------------------------
def test_missing_mapping_file_is_diagnosed(context, root):
    make_series(root, {"go_articles.csv": "A;m;p;N1\n"}, MAP_SCHEMA)
    rec = reconcile(context, root)
    assert rec.mapping_tables == ["go_mtmap"] and "metatypeid" in rec.columns   # schema says it is a mapping table
    assert rec.status is ReconciliationStatus.PARTIAL
    assert any(d.code == "TABLE_MISSING" and d.table == "go_mtmap" for d in rec.diagnostics)
    assert any(d.code == "TABLE_MISSING" and d.table == "go_mtmap" for d in rec.loader_result.all_diagnostics())
    assert rec.rows[0].status == "Needs assignment"                              # not shown as complete or mapped


def test_missing_article_file_fails(context, root):
    make_series(root, {}, EXAMPLE)
    rec = reconcile(context, root)
    assert rec.status is ReconciliationStatus.FAILED and rec.rows == []
    assert any(d.code == "TABLE_MISSING" for d in rec.diagnostics)


def test_malformed_row_is_diagnosed_and_load_is_not_complete(context, root):
    make_series(root, {"go_articles.csv": "MT;m;p;A1;C1;P1\nbroken;line\nMT2;m;p;A2;C2;P2\n"}, EXAMPLE)
    rec = reconcile(context, root)
    assert rec.status is ReconciliationStatus.PARTIAL and len(rec.rows) == 2
    bad = [d for d in rec.diagnostics if d.code == "FIELD_COUNT_MISMATCH"]
    assert len(bad) == 1 and bad[0].line == 2


def test_unreadable_schema_or_series_fails(context, root):
    (root / "atlas" / "1").mkdir(parents=True)
    rec = reconcile(context, root)                                  # no mt.inp_descr
    assert rec.status is ReconciliationStatus.FAILED and any(d.code == "SCHEMA_MISSING" for d in rec.diagnostics)
    rec = reconcile(context, root, "absent")
    assert rec.status is ReconciliationStatus.FAILED and rec.rows == []


def test_undecodable_article_table_fails_and_bad_schema_declaration_is_partial(context, root):
    data = make_series(root, {}, EXAMPLE)
    (data / "go_articles.csv").write_bytes(b"MT;m;p;caf\xe9;C;P\n")
    assert reconcile(context, root).status is ReconciliationStatus.FAILED
    (root / "atlas").rename(root / "old")
    dup = declare("go_articles", EXAMPLE_COLUMNS).replace("field   6  childparentid", "field   6  configid")
    make_series(root, {"go_articles.csv": "MT;m;p;A;C;P\n"}, dup)
    rec = reconcile(context, root)
    assert rec.status is ReconciliationStatus.PARTIAL
    assert any(d.code == "SCHEMA_DECLARATION_PROBLEM" for d in rec.diagnostics)


def test_undeclared_go_file_and_unrelated_table_problem_are_reported(context, root):
    make_series(root, {"go_articles.csv": "MT;m;p;A;C;P\n", "go_extra.csv": "x\n", "go_info.csv": "bad\n"},
                EXAMPLE + declare("go_info", ["key", "value"]))
    rec = reconcile(context, root)
    codes = {d.code for d in rec.diagnostics}
    assert {"UNDECLARED_GO_FILE", "UNRELATED_TABLE_NOT_CLEAN"} <= codes
    assert rec.status is ReconciliationStatus.COMPLETE               # unrelated problems do not block articles


# 9: duplicates and conflicts ---------------------------------------------------------------------------------------------
def test_conflicting_mappings_are_not_resolved(context, root):
    make_series(root, {"go_articles.csv": "A;m;p;N1\n",
                       "go_mtmap.csv": "m;p;N1;MT1;\nm;p;N1;MT2;\n"}, MAP_SCHEMA)
    rec = reconcile(context, root)
    row = rec.rows[0]
    assert row.status == "Conflicting mappings" and row.values["metatypeid"] == ""
    assert [s.values["metatypeid"] for s in row.mapping_sources] == ["MT1", "MT2"]
    assert [s.line for s in row.mapping_sources] == [1, 2]
    assert rec.status is ReconciliationStatus.PARTIAL
    assert any(d.code == "CONFLICTING_MAPPINGS" for d in rec.diagnostics)


def test_identical_duplicate_mapping_is_warned_but_not_a_conflict(context, root):
    make_series(root, {"go_articles.csv": "A;m;p;N1\n", "go_mtmap.csv": "m;p;N1;MT1;\nm;p;N1;MT1;\n"}, MAP_SCHEMA)
    rec = reconcile(context, root)
    assert rec.rows[0].status == "Mapped" and len(rec.rows[0].mapping_sources) == 2
    assert [d.code for d in rec.diagnostics if d.severity == "warning" and d.code == "DUPLICATE_MAPPING"]


def test_embedded_and_external_mapping_can_conflict(context, root):
    schema = declare("go_articles", ["manufacturer", "program", "article", "metatypeid"]) + declare(
        "go_mtmap", ["manufacturer", "program", "article", "metatypeid"])
    make_series(root, {"go_articles.csv": "m;p;N1;MT1\n", "go_mtmap.csv": "m;p;N1;MT2\n"}, schema)
    assert reconcile(context, root).rows[0].status == "Conflicting mappings"


def test_duplicate_article_identity_is_ambiguous_and_orphan_mapping_kept(context, root):
    make_series(root, {"go_articles.csv": "A;m;p;N1\nB;m;p;N1\nC;m;p;N3\n;m;p;\n",
                       "go_mtmap.csv": "m;p;N1;MT1;\nm;p;ZZ;MT5;\n"}, MAP_SCHEMA)
    rec = reconcile(context, root)
    assert [r.status for r in rec.rows] == ["Ambiguous identity", "Ambiguous identity", "Needs assignment",
                                            "Invalid identity"]
    assert len(rec.rows) == 4                                        # nothing discarded
    codes = {d.code for d in rec.diagnostics}
    assert {"AMBIGUOUS_ARTICLE_IDENTITY", "AMBIGUOUS_MAPPING_TARGET", "MAPPING_WITHOUT_ARTICLE",
            "MISSING_ARTICLE_IDENTITY"} <= codes
    assert len(rec.unmatched_mappings) == 2 and rec.status is ReconciliationStatus.PARTIAL


# 11: no writes ------------------------------------------------------------------------------------------------------------
def snapshot(root: Path):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()} | {
        str(p) + "/": "" for p in root.rglob("*") if p.is_dir()}


def test_reconciliation_and_page_load_write_nothing(context, root):
    from PySide6.QtWidgets import QApplication
    from ui.pages.metatype_creation_page import MetatypeCreationPage

    make_series(root, {"go_articles.csv": "A;m;p;N1\n", "go_mtmap.csv": "m;p;N1;MT1;\nm;p;N1;MT2;\n"}, MAP_SCHEMA)
    before = snapshot(root)
    reconcile(context, root)
    QApplication.instance() or QApplication([])
    MetatypeCreationPage(context).load_series()
    assert snapshot(root) == before


def test_service_has_no_write_api():
    names = [n for n in dir(MetatypeArticleService) if not n.startswith("_")]
    assert sorted(names) == ["build", "last_result", "reconcile"]


# 10: page ------------------------------------------------------------------------------------------------------------------
@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_page_shows_empty_state_then_work_table_after_load(context, root, qapp, monkeypatch):
    from PySide6.QtWidgets import QAbstractItemView, QMessageBox
    from ui.pages.metatype_creation_page import MetatypeCreationPage

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    make_series(root, {"go_articles.csv": "MT;m;p;A1;C1;P1\n;m;p;A2;C2;\n"}, EXAMPLE)
    page = MetatypeCreationPage(context)
    model = page.articles_model
    assert "No articles loaded" in page.articles_load_status.text() and model.rowCount() == 0
    assert page.articles_table.objectName() == "metatypeArticlesTable"
    assert page.articles_edit.objectName() == "metatypeSwitchArticles"
    assert context.metatype_article_service.last_result is None          # nothing loaded before Load Series

    page.load_series()
    table = page.articles_table
    headers = [model.headerData(i, Qt.Orientation.Horizontal) for i in range(model.columnCount())]
    assert headers == EXAMPLE_COLUMNS + ["Mapping Status", "Validation"]
    assert model.rowCount() == 2
    status_col = len(EXAMPLE_COLUMNS)
    assert [model.index(r, status_col).data() for r in range(2)] == ["Mapped", "Needs assignment"]
    assert table.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectRows
    assert table.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection
    editable = {headers[c] for c in range(model.columnCount()) if model.flags(model.index(0, c)) & Qt.ItemFlag.ItemIsEditable}
    assert editable == {"metatypeid", "childparentid"}      # manufacturer/program/article/configid/status read-only
    assert page.articles_load_status.text().startswith("Load complete")
    assert page.workspace_stack.widget(0).isAncestorOf(table) and page.workspace_stack.widget(0).isAncestorOf(page.articles_edit)


def test_page_flags_partial_load_and_keeps_diagnostics(context, root, qapp):
    from ui.pages.metatype_creation_page import MetatypeCreationPage

    make_series(root, {"go_articles.csv": "MT;m;p;A1;C1;P1\nbroken\n"}, EXAMPLE)
    page = MetatypeCreationPage(context)
    page.load_series()
    assert page.articles_load_status.text().startswith("PARTIAL load")
    assert "FIELD_COUNT_MISMATCH" in page.articles_diagnostics.toPlainText()


def test_page_reports_failed_series_and_series_selection_still_requires_load(context, root, qapp):
    from ui.pages.metatype_creation_page import MetatypeCreationPage

    make_series(root, {"go_articles.csv": "MT;m;p;A1;C1;P1\n"}, EXAMPLE, name="atlas")
    (root / "empty" / "1").mkdir(parents=True)
    page = MetatypeCreationPage(context)
    page.series_combo.setCurrentIndex(page.series_combo.findData("atlas"))
    assert context.metatype_article_service.last_result is None          # selecting alone loads nothing
    page.load_series()
    assert context.metatype_article_service.last_result.series == "atlas"
    assert page.load_button.text() == "Reload Series (reset answers)"
