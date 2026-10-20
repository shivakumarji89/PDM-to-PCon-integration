"""Interactive Articles work table: edit session, Qt model/proxy identity, refresh, creation gating.

Synthetic fixtures in temp directories only (never the real HMX repository).
"""
import hashlib
import os
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from core.application_context import ApplicationContext
from core.config import AppConfig
from services.metatype.article_edit_session import ArticleEditSession, WRITER_BLOCKER
from ui.pages.metatype_article_table import KEY_ROLE, ArticleFilterProxy, ArticleWorkTableModel

FIELD = "field   {}  {}\t\tvstring\t\tdelim ; trim\n"
COLUMNS = ["metatypeid", "manufacturer", "program", "article", "configid", "childparentid"]


def declare(columns):
    return ("table   go_articles\tgo_articles.csv\t\tcsv\n" f"fields  {len(columns)}\n"
            + "".join(FIELD.format(i, c) for i, c in enumerate(columns, 1)) + "\n")


def make_series(root: Path, csv: str, columns=COLUMNS, name="atlas") -> Path:
    data = root / name / "1"
    data.mkdir(parents=True, exist_ok=True)
    (data / "mt.inp_descr").write_text("name go_tables\n\n" + declare(columns), encoding="utf-8")
    (data / "go_articles.csv").write_text(csv, encoding="utf-8")
    return data


def tree_hash(root: Path) -> dict[str, str]:
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


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


CSV = "MT_A;hmx;prog;ART1;CFG1;P1\n;hmx;prog;ART2;CFG2;\n;hmx;prog;ART3;CFG3;\n"
K1, K2, K3 = ("hmx", "prog", "ART1"), ("hmx", "prog", "ART2"), ("hmx", "prog", "ART3")


@pytest.fixture
def session(context, root):
    make_series(root, CSV)
    return ArticleEditSession(reconcile(context, root))


# -- editing rules ---------------------------------------------------------------------------------------------------
def test_only_declared_metatypeid_and_childparentid_are_editable(session):
    assert session.editable_columns() == ["metatypeid", "childparentid"]
    for column in ("manufacturer", "program", "article", "configid"):
        assert not session.set_value(K2, column, "X") and session.pending_count == 0
    assert session.set_value(K2, "metatypeid", "MT_B") and session.set_value(K2, "childparentid", "P9")
    assert session.value(K2, "metatypeid") == "MT_B" and session.source_value(K2, "metatypeid") == ""
    assert session.is_modified(K2) and not session.is_modified(K1)


def test_editing_back_to_source_value_is_not_a_change(session):
    session.set_value(K1, "metatypeid", "OTHER")
    session.set_value(K1, "metatypeid", "MT_A")         # the raw source value
    assert session.pending_count == 0


def test_undeclared_mapping_columns_are_not_editable_and_never_invented(context, root):
    make_series(root, "hmx;prog;ART1\n", columns=["manufacturer", "program", "article"])
    session = ArticleEditSession(reconcile(context, root))
    assert session.editable_columns() == []
    assert not session.set_value(K1, "metatypeid", "MT")
    assert session.severity(K1) == "unavailable" and session.counts()["valid"] == 0
    codes = {i.code for i in session.issues(K1)}
    assert {"METATYPEID_UNAVAILABLE", "CONFIGID_UNAVAILABLE"} <= codes


def test_conflicting_and_ambiguous_rows_are_not_editable(context, root):
    make_series(root, "A;hmx;prog;DUP;C;\nB;hmx;prog;DUP;C;\n;hmx;prog;OK;C;\n")
    session = ArticleEditSession(reconcile(context, root))
    dup = ("hmx", "prog", "DUP")
    assert not session.row_editable(dup) and not session.set_value(dup, "metatypeid", "X")
    assert session.severity(dup) == "error"
    assert session.row_editable(("hmx", "prog", "OK"))


# -- validation ------------------------------------------------------------------------------------------------------
def test_validation_distinguishes_error_warning_info(session):
    session.set_value(K2, "metatypeid", "A;B")
    session.set_value(K3, "metatypeid", " MT ")
    session.set_value(K1, "metatypeid", "")
    assert session.severity(K2) == "error" and "INVALID_CHARACTER" in {i.code for i in session.issues(K2)}
    assert session.severity(K3) == "warning" and "UNTRIMMED_VALUE" in {i.code for i in session.issues(K3)}
    assert session.severity(K1) == "warning" and "MAPPING_CLEARED" in {i.code for i in session.issues(K1)}
    fresh = ArticleEditSession(session.result)
    assert fresh.severity(K2) == "warning" or fresh.severity(K2) == "ok"   # unmapped is informational only
    assert "NEEDS_ASSIGNMENT" in {i.code for i in fresh.issues(K2)}


def test_row_is_not_valid_just_because_it_has_text(session):
    session.set_value(K2, "metatypeid", "a\nb")
    assert session.severity(K2) == "error"
    assert session.counts()["invalid"] == 1 and session.counts()["valid"] == 2


def test_counts_follow_edits(session):
    assert session.counts() == {"total": 3, "mapped": 1, "unmapped": 2, "invalid": 0, "warnings": 0,
                                "unavailable": 0, "valid": 3, "pending": 0, "written": 0}
    session.set_value(K2, "metatypeid", "MT_B")
    counts = session.counts()
    assert counts["mapped"] == 2 and counts["unmapped"] == 1 and counts["pending"] == 1


# -- refresh ---------------------------------------------------------------------------------------------------------
def test_refresh_keeps_edits_by_identity_when_rows_reorder(context, root, session):
    session.set_value(K2, "metatypeid", "MT_B")
    make_series(root, ";hmx;prog;ART3;CFG3;\n;hmx;prog;ART2;CFG2;\nMT_A;hmx;prog;ART1;CFG1;P1\n")
    report = session.refresh(reconcile(context, root))
    assert report.kept == 1 and not report.dropped and not report.conflicted
    assert session.value(K2, "metatypeid") == "MT_B" and session.value(K3, "metatypeid") == ""


def test_refresh_reports_dropped_and_conflicted_edits_never_silently(context, root, session):
    session.set_value(K1, "metatypeid", "MINE")
    session.set_value(K2, "metatypeid", "MT_B")
    make_series(root, "CHANGED;hmx;prog;ART1;CFG1;P1\n;hmx;prog;ART3;CFG3;\n")   # ART2 removed, ART1 remapped
    report = session.refresh(reconcile(context, root))
    assert [c.key for c in report.dropped] == [K2]
    assert [c.key for c in report.conflicted] == [K1]
    assert session.value(K1, "metatypeid") == "MINE" and session.source_value(K1, "metatypeid") == "CHANGED"


def test_refresh_drops_edit_the_source_already_satisfies(context, root, session):
    session.set_value(K2, "metatypeid", "MT_B")
    make_series(root, "MT_A;hmx;prog;ART1;CFG1;P1\nMT_B;hmx;prog;ART2;CFG2;\n;hmx;prog;ART3;CFG3;\n")
    report = session.refresh(reconcile(context, root))
    assert session.pending_count == 0 and report.kept == 0 and not report.dropped


# -- Qt model / proxy ------------------------------------------------------------------------------------------------
def build_model(session):
    model = ArticleWorkTableModel(session)
    proxy = ArticleFilterProxy()
    proxy.setSourceModel(model)
    return model, proxy


def column_of(model, name):
    return next(c for c in range(model.columnCount()) if model.headerData(c, Qt.Orientation.Horizontal) == name)


def test_flags_editable_vs_read_only(qapp, session):
    model, _ = build_model(session)
    for name in COLUMNS + ["Mapping Status", "Validation"]:
        flags = model.flags(model.index(0, column_of(model, name)))
        assert bool(flags & Qt.ItemFlag.ItemIsEditable) == (name in ("metatypeid", "childparentid")), name


def test_edit_through_sorted_filtered_proxy_hits_the_right_article(qapp, session):
    model, proxy = build_model(session)
    article_col = column_of(model, "article")
    proxy.sort(article_col, Qt.SortOrder.DescendingOrder)           # ART3, ART2, ART1
    assert [proxy.index(r, article_col).data() for r in range(3)] == ["ART3", "ART2", "ART1"]
    proxy.set_text("art2")
    assert proxy.rowCount() == 1
    index = proxy.index(0, column_of(model, "metatypeid"))
    assert index.data(KEY_ROLE) == K2
    assert proxy.setData(index, "MT_B")                              # proxy forwards to the source model
    proxy.set_text("")
    proxy.sort(article_col, Qt.SortOrder.AscendingOrder)
    assert session.value(K2, "metatypeid") == "MT_B"
    assert session.value(K1, "metatypeid") == "MT_A" and session.value(K3, "metatypeid") == ""
    assert session.pending_count == 1


def test_read_only_cell_rejects_setdata(qapp, session):
    model, _ = build_model(session)
    assert not model.setData(model.index(0, column_of(model, "article")), "HACK")
    assert not model.setData(model.index(0, column_of(model, "configid")), "HACK")
    assert session.pending_count == 0


def test_filters_and_modified_indicator(qapp, session):
    model, proxy = build_model(session)
    model.setData(model.index(1, column_of(model, "metatypeid")), "MT_B")
    status = model.index(1, column_of(model, "Mapping Status"))
    assert "(modified)" in status.data()
    assert model.index(1, column_of(model, "metatypeid")).data(Qt.ItemDataRole.BackgroundRole) is not None
    for mode, expected in (("All", 3), ("Mapped", 2), ("Unmapped", 1), ("Modified", 1), ("Errors", 0)):
        proxy.set_mode(mode)
        assert proxy.rowCount() == expected, mode


def test_row_level_diagnostics_in_tooltip_and_validation_column(qapp, session):
    model, _ = build_model(session)
    model.setData(model.index(1, column_of(model, "metatypeid")), "A;B")
    validation = model.index(1, column_of(model, "Validation"))
    assert validation.data() == "Error" and "INVALID_CHARACTER" in validation.data(Qt.ItemDataRole.ToolTipRole)


def test_edit_emits_data_changed_only_for_the_edited_row(qapp, session):
    model, _ = build_model(session)
    seen = []
    model.dataChanged.connect(lambda tl, br, roles=None: seen.append((tl.row(), br.row())))
    model.setData(model.index(2, column_of(model, "metatypeid")), "MT_C")
    assert seen == [(2, 2)]


def test_large_table_edit_sort_filter_stay_fast_and_correct(qapp, context, root):
    rows = "".join(f"MT{i % 7};hmx;prog;ART{i:05d};CFG{i};\n" for i in range(5000))
    make_series(root, rows)
    session = ArticleEditSession(reconcile(context, root))
    model, proxy = build_model(session)
    started = time.perf_counter()
    proxy.sort(column_of(model, "article"), Qt.SortOrder.DescendingOrder)
    proxy.set_text("art0123")
    target = proxy.index(0, column_of(model, "metatypeid"))
    key = target.data(KEY_ROLE)
    assert proxy.setData(target, "NEW")
    proxy.set_text("")
    assert time.perf_counter() - started < 10
    assert session.pending_count == 1 and session.value(key, "metatypeid") == "NEW"
    assert key[2].startswith("ART0123")


# -- creation gating / no writes -------------------------------------------------------------------------------------
def test_create_is_blocked_with_reasons_and_never_writes(session, root):
    before = tree_hash(root)
    assert not session.can_create()
    assert "There are no pending changes." in session.creation_blockers()
    session.set_value(K2, "metatypeid", "MT_B")
    blockers = session.creation_blockers()
    assert WRITER_BLOCKER in blockers and "There are no pending changes." not in blockers
    session.set_value(K3, "metatypeid", "bad;value")
    assert "Pending edits have validation errors." in session.creation_blockers()
    assert "MT_B" in session.review_text() and "nothing has been written" in session.review_text()
    assert tree_hash(root) == before


def test_missing_configid_is_reported_as_blocker(context, root):
    make_series(root, ";hmx;prog;ART1;\n", columns=["metatypeid", "manufacturer", "program", "article", "childparentid"])
    session = ArticleEditSession(reconcile(context, root))
    session.set_value(K1, "metatypeid", "MT")
    assert any("configid" in r for r in session.creation_blockers())


def test_discard_reverts_one_or_all_rows(session):
    session.set_value(K1, "metatypeid", "X")
    session.set_value(K2, "metatypeid", "Y")
    assert session.discard(K1) == 1 and session.pending_count == 1
    assert session.discard() == 1 and session.pending_count == 0 and session.value(K1, "metatypeid") == "MT_A"


# -- page integration ------------------------------------------------------------------------------------------------
def test_page_edit_refresh_and_reload_guard(qapp, context, root, monkeypatch):
    from ui.pages.metatype_creation_page import MetatypeCreationPage

    answers = []
    monkeypatch.setattr(QMessageBox, "question",
                        lambda *a, **k: answers.append(1) or QMessageBox.StandardButton.Cancel)
    data = make_series(root, CSV)
    page = MetatypeCreationPage(context)
    assert not page.articles_create_button.isEnabled()                # nothing loaded yet
    page.series_combo.setCurrentIndex(page.series_combo.findData("atlas"))
    page.load_series()
    model = page.articles_model
    assert page.articles_create_button.isEnabled() and not page.articles_review_button.isEnabled()
    assert model.setData(model.index(1, column_of(model, "metatypeid")), "MT_B")
    assert page.articles_review_button.isEnabled() and "1 pending change(s)" in page.articles_counts.text()

    (data / "go_articles.csv").write_text(CSV.replace("CFG2", "CFGX"), encoding="utf-8")   # source changed
    before = tree_hash(root)
    page.refresh_articles()
    assert page.articles_session.value(K2, "metatypeid") == "MT_B"       # edit survived the refresh
    assert "CFGX" in model.index(1, column_of(model, "configid")).data()

    page.load_series()                                                   # reload would discard: asked, declined
    assert answers and page.articles_session.pending_count == 1

    assert "MT_B" in page.review_articles()
    page.create_from_articles()
    assert "Writing is blocked" in page.articles_diagnostics.toPlainText()
    assert tree_hash(root) == before        # refresh, review, reload attempt and Create wrote nothing
