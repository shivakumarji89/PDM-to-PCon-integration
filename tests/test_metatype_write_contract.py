"""Write contract: verified go_articles role aliases, reference warnings and the in-memory write plan.

Synthetic fixtures in temp directories. One class of test reads the real HMX repository strictly read-only
(skipped when it is absent). Nothing here writes to a repository.
"""
import hashlib
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.application_context import ApplicationContext
from core.config import AppConfig
from services.metatype.article_edit_session import ArticleEditSession
from services.metatype.article_write_plan import FilePlan, plan_article_edits, verify_file_plan

FIELD = "field   {}  {}\t\tvstring\t\tdelim ; trim\n"
ARTICLE_COLUMNS = ["id", "manufacturer", "program", "article_nr", "prm_key", "chprm_key"]
TYPES = ["id", "name", "format", "default", "mode", "filter"]
PROPS = ["id", "key", "name", "value", "variant_code", "variant_value"]
CHILDPROPS = ["key", "name", "value", "child_key"]


def declare(table, columns):
    return (f"table   {table}\t{table}.csv\t\tcsv\nfields  {len(columns)}\n"
            + "".join(FIELD.format(i, c) for i, c in enumerate(columns, 1)) + "\n")


SCHEMA = (declare("go_types", TYPES) + declare("go_articles", ARTICLE_COLUMNS) + declare("go_properties", PROPS)
          + declare("go_childprops", CHILDPROPS))
HEADER = "################\n#\n#   test - Articles\n#\n################\n\n#[metatypeid] ;[manufacturer];[program];[article];[configid];[childparentid]\n\n"
ARTICLES = ("MT_A            ;hmx ;test ;ART1 ;CFG_ART1 ;CHP_A\n"
            "MT_A            ;hmx ;test ;ART2 ;CFG_ART2 ;\n"
            "MT_B            ;hmx ;test ;ART3 ;CFG_ART3 ;CHP_A, CHP_B\n")
TYPES_CSV = "MT_A;GType;;T;0;\nMT_B;GType;;T;0;\n"
PROPS_CSV = "MT_A;CFG_ART1;GP;V1;;\nMT_A;CFG_ART2;GP;V2;;\nMT_B;CFG_ART3;GP;V3;;\n"
CHILD_CSV = "CHP_A;GC;YES;CH_A\nCHP_B;GC;YES;CH_B\n"
K1, K2, K3 = ("hmx", "test", "ART1"), ("hmx", "test", "ART2"), ("hmx", "test", "ART3")


def make_series(root: Path, articles=HEADER + ARTICLES, name="demo", types=TYPES_CSV, props=PROPS_CSV,
                child=CHILD_CSV, schema=SCHEMA, newline="\r\n", bom=False) -> Path:
    data = root / name / "1"
    data.mkdir(parents=True, exist_ok=True)
    (data / "mt.inp_descr").write_text("name go_tables\n\n" + schema, encoding="utf-8")
    body = articles.replace("\n", newline).encode("utf-8")
    (data / "go_articles.csv").write_bytes((b"\xef\xbb\xbf" if bom else b"") + body)
    for file, text in (("go_types.csv", types), ("go_properties.csv", props), ("go_childprops.csv", child)):
        (data / file).write_text(text, encoding="utf-8")
    return data


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


def session_for(context, root, series="demo"):
    return ArticleEditSession(context.metatype_article_service.reconcile(series, root=root))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# -- D7: roles are verified aliases of the manual's six-column layout ------------------------------------------------
def test_manual_layout_aliases_the_three_roles(context, root):
    make_series(root)
    session = session_for(context, root)
    rec = session.result
    assert rec.roles["metatypeid"] == "id"
    assert rec.roles["configid"] == "prm_key" and rec.roles["childparentid"] == "chprm_key"
    assert rec.unavailable_fields == [] and [r.status for r in rec.rows] == ["Mapped", "Mapped", "Mapped"]
    assert session.editable_columns() == ["id", "chprm_key"]
    assert session.column_label("id") == "MetatypeID (id)" and session.column_label("prm_key") == "ConfigID (prm_key)"
    assert session.column_label("article_nr") == "article_nr"


def test_configid_prm_key_is_read_only_and_never_generated(context, root):
    make_series(root)
    session = session_for(context, root)
    assert not session.set_value(K1, "prm_key", "CFG_X") and session.pending_count == 0
    assert session.value(K1, "prm_key").strip() == "CFG_ART1"


def test_other_layouts_get_no_alias(context, root):
    reordered = ["manufacturer", "program", "article_nr", "id", "prm_key", "chprm_key"]
    schema = declare("go_types", TYPES) + declare("go_articles", reordered)
    make_series(root, articles="hmx;test;ART1;MT_A;CFG;CHP\n", schema=schema)
    rec = context.metatype_article_service.reconcile("demo", root=root)
    assert "metatypeid" in rec.unavailable_fields and rec.rows[0].status == "Mapping unavailable"


# -- D9: reference rules are warnings, judged only when the table was read ---------------------------------------------
def test_dangling_references_are_warnings_not_errors(context, root):
    make_series(root, articles=HEADER + "MT_X;hmx;test;ART1;CFG_NOPE;CHP_A, CHP_ZZ\n")
    session = session_for(context, root)
    codes = {i.code: i.severity for i in session.issues(K1)}
    assert codes["METATYPEID_NOT_IN_GO_TYPES"] == "warning"
    assert codes["CONFIGID_NOT_IN_GO_PROPERTIES"] == "warning"
    assert codes["CHILDPARENTID_NOT_IN_GO_CHILDPROPS"] == "warning"
    assert "CHP_ZZ" in [i.message for i in session.issues(K1) if i.code.startswith("CHILDPARENT")][0]
    assert session.severity(K1) == "warning"          # never an error: the production repository has such rows


def test_clean_references_have_no_warning_and_comma_lists_resolve(context, root):
    make_series(root)
    session = session_for(context, root)
    assert all(session.severity(k) == "ok" for k in (K1, K2, K3))


def test_unreadable_reference_table_is_unknown_not_dangling(context, root):
    data = make_series(root)
    (data / "go_childprops.csv").unlink()
    session = session_for(context, root)
    assert "child_keys" not in session.result.references
    assert not any(i.code.startswith("CHILDPARENT") for i in session.issues(K1))


def test_comment_prefix_and_quote_are_errors(context, root):
    make_series(root)
    session = session_for(context, root)
    session.set_value(K1, "id", "#MT")
    session.set_value(K2, "chprm_key", 'A"B')
    assert "COMMENT_PREFIX" in {i.code for i in session.issues(K1)} and session.severity(K1) == "error"
    assert "INVALID_CHARACTER" in {i.code for i in session.issues(K2)}


# -- D3/D8: the in-memory write plan ---------------------------------------------------------------------------------------
def test_plan_changes_only_the_edited_field_and_verifies(context, root):
    data = make_series(root)
    path = data / "go_articles.csv"
    before = path.read_bytes()
    session = session_for(context, root)
    session.set_value(K2, "id", "MT_B")
    session.set_value(K2, "chprm_key", "CHP_B")
    plan = plan_article_edits(session)
    assert plan.ok and len(plan.files) == 1 and len(plan.files[0].changes) == 2
    new = plan.files[0].new
    old_lines, new_lines = before.split(b"\r\n"), new.split(b"\r\n")
    assert len(old_lines) == len(new_lines)
    differing = [i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
    assert differing == [old_lines.index(next(l for l in old_lines if b"ART2" in l))]   # exactly one physical line
    row = new_lines[differing[0]]
    assert row == b"MT_B            ;hmx ;test ;ART2 ;CFG_ART2 ;CHP_B"                  # padding kept, other fields intact
    assert path.read_bytes() == before                                                 # the plan wrote nothing
    assert "NOTHING has been written" in plan.review_text() and "verified by re-parsing" in plan.review_text()


def test_plan_preserves_bom_comments_blank_lines_and_terminators(context, root):
    data = make_series(root, bom=True, newline="\r\n")
    session = session_for(context, root)
    session.set_value(K1, "id", "MT_B")
    plan = plan_article_edits(session)
    assert plan.ok
    new = plan.files[0].new
    assert new.startswith(b"\xef\xbb\xbf") and new.count(b"\r\n") == (data / "go_articles.csv").read_bytes().count(b"\r\n")
    old_lines = (data / "go_articles.csv").read_bytes().split(b"\r\n")
    new_lines = new.split(b"\r\n")
    assert [i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b] == [8]   # only the ART1 record line
    assert new_lines[6].lstrip(b"\xef\xbb\xbf").startswith(b"#[metatypeid]")             # header comment untouched


def test_plan_handles_lf_files_and_physical_line_numbers_after_a_comment_header(context, root):
    make_series(root, newline="\n")
    session = session_for(context, root)
    row = session._index[K3]
    assert row.source_line == 11                   # 8 header/comment/blank lines + 2 records: physical lines
    session.set_value(K3, "chprm_key", "CHP_B")
    plan = plan_article_edits(session)
    assert plan.ok and plan.files[0].changes[0].line == 11 and b"\r" not in plan.files[0].new


def test_plan_without_edits_is_empty_and_whitespace_only_edit_is_not_a_change(context, root):
    make_series(root)
    session = session_for(context, root)
    assert plan_article_edits(session).files == [] and not plan_article_edits(session).ok
    session.set_value(K1, "id", "MT_A   ")
    plan = plan_article_edits(session)
    assert plan.files and not plan.files[0].changes and not plan.ok      # trimmed value equals the source


def test_plan_refuses_empty_metatypeid(context, root):
    make_series(root)
    session = session_for(context, root)
    session.set_value(K1, "id", "")
    plan = plan_article_edits(session)
    assert not plan.ok and any("empty MetatypeID" in p for f in plan.files for p in f.problems)


def test_plan_refuses_rows_with_validation_errors(context, root):
    make_series(root)
    session = session_for(context, root)
    session.set_value(K1, "id", "A;B")
    assert not plan_article_edits(session).ok


def test_plan_detects_a_file_changed_since_load(context, root):
    data = make_series(root)
    session = session_for(context, root)
    session.set_value(K2, "id", "MT_B")
    path = data / "go_articles.csv"
    path.write_bytes(path.read_bytes().replace(b"CFG_ART2", b"CFG_CHANGED"))
    plan = plan_article_edits(session)
    assert not plan.ok and any("changed since it was loaded" in p for f in plan.files for p in f.problems)


def test_plan_refuses_quoted_lines_and_non_utf8_files(context, root):
    data = make_series(root, articles=HEADER + 'MT_A;hmx;test;ART1;"CFG_ART1";\nMT_A;hmx;test;ART2;CFG_ART2;\n')
    session = session_for(context, root)
    session.set_value(K1, "id", "MT_B")
    assert any("quoting rule" in p for f in plan_article_edits(session).files for p in f.problems)

    session = session_for(context, root)
    session.set_value(K2, "id", "MT_B")
    path = data / "go_articles.csv"
    session_result_columns = session.result
    path.write_bytes(path.read_bytes() + b"\xfc\r\n")                   # invalid UTF-8 appended after load
    plan = plan_article_edits(session)
    assert not plan.ok and any("not valid UTF-8" in p for f in plan.files for p in f.problems)
    assert session_result_columns is session.result


def test_plan_refuses_mapping_fields_stored_in_another_table(context, root):
    schema = SCHEMA + declare("go_map", ["id", "manufacturer", "program", "article_nr", "childparentid"])
    data = make_series(root, schema=schema)
    (data / "go_map.csv").write_text("MT_A;hmx;test;ART1;CHP_B\n", encoding="utf-8")
    session = session_for(context, root)
    session.set_value(K1, "chprm_key", "CHP_B")
    plan = plan_article_edits(session)
    assert not plan.ok


def test_verify_catches_unplanned_changes(context, root):
    make_series(root)
    session = session_for(context, root)
    session.set_value(K2, "id", "MT_B")
    plan = plan_article_edits(session)
    good = plan.files[0]
    assert verify_file_plan(good, plan.files[0] and ARTICLE_COLUMNS) == []
    tampered = FilePlan(good.path, good.changes, good.original, good.new.replace(b"ART3", b"ARTX"))
    assert any("unplanned" in p for p in verify_file_plan(tampered, ARTICLE_COLUMNS))
    dropped = FilePlan(good.path, good.changes, good.original, good.original)
    assert any("not found" in p or "reads back" in p for p in verify_file_plan(dropped, ARTICLE_COLUMNS))
    lf = FilePlan(good.path, good.changes, good.original, good.new.replace(b"\r\n", b"\n"))
    assert any("terminator" in p for p in verify_file_plan(lf, ARTICLE_COLUMNS))


def test_planner_never_modifies_the_repository(context, root):
    data = make_series(root)
    before = {p.name: (digest(p), p.stat().st_mtime_ns) for p in data.iterdir()}
    session = session_for(context, root)
    session.set_value(K1, "id", "MT_B")
    session.set_value(K3, "chprm_key", "CHP_A")
    plan = plan_article_edits(session)
    assert plan.ok
    assert before == {p.name: (digest(p), p.stat().st_mtime_ns) for p in data.iterdir()}
    assert not session.can_create()                                    # authorisation (D8) still absent


# -- page: header labels and planned output in Review -------------------------------------------------------------------
def test_page_shows_role_labels_and_planned_output(qapp, context, root):
    from ui.pages.metatype_creation_page import MetatypeCreationPage

    make_series(root)
    page = MetatypeCreationPage(context)
    page.series_combo.setCurrentIndex(page.series_combo.findData("demo"))
    page.load_series()
    model = page.articles_model
    headers = [model.headerData(i, Qt.Orientation.Horizontal) for i in range(model.columnCount())]
    assert headers[:6] == ["MetatypeID (id)", "manufacturer", "program", "article_nr", "ConfigID (prm_key)", "ChildParentID (chprm_key)"]
    editable = {headers[c] for c in range(model.columnCount()) if model.flags(model.index(1, c)) & Qt.ItemFlag.ItemIsEditable}
    assert editable == {"MetatypeID (id)", "ChildParentID (chprm_key)"}
    assert model.setData(model.index(1, 0), "MT_B")
    text = page.review_articles()
    assert "Planned output" in text and "ART2" in text and "NOTHING has been written" in text and "Writing is blocked" in text


# -- real repository, read-only -------------------------------------------------------------------------------------------
REAL_ROOT = Path(AppConfig().metatype_repository_root)


@pytest.mark.skipif(not REAL_ROOT.exists(), reason="real HMX repository not available")
def test_every_real_series_loads_with_aliases_and_plans_verify_in_memory():
    ctx = ApplicationContext(AppConfig())
    checked = planned = 0
    before = {}
    # A fixed, representative sample (loading every table of all series takes ~40 s). It includes series whose
    # data holds dangling references (bound_screens, dalby, nevi_enhanced) and comma-list ChildParentIDs (pullman).
    sample = ("accessories", "aeron", "atlas", "bound_screens", "civic_tables", "cyclade_Tables", "dalby", "hatch",
              "layout_studio", "nevi_enhanced", "pullman", "verus")
    for descr in sorted(REAL_ROOT / name / "1" / "mt.inp_descr" for name in sample):
        if not descr.exists():
            continue
        series = descr.parent.parent.name
        articles = descr.parent / "go_articles.csv"
        if not articles.exists() or articles.stat().st_size == 0:
            continue
        before[articles] = digest(articles)
        rec = ctx.metatype_article_service.reconcile(series)
        if "metatypeid" not in rec.roles or not rec.rows:
            continue
        checked += 1
        session = ArticleEditSession(rec)
        assert session.editable_columns() and not session.is_column_editable(rec.roles.get("configid", "-"))
        row = next((r for r in rec.rows if session.row_editable(r.identity or ())), None)
        if row is None:
            continue
        session.set_value(row.identity, rec.roles["metatypeid"], "MT_PLAN_PROBE")
        plan = plan_article_edits(session)
        if plan.ok:
            planned += 1
        else:                                   # an honest refusal (e.g. quoted line / non-UTF-8) is acceptable
            assert all(f.problems for f in plan.files)
    assert checked >= 8 and planned >= 8, (checked, planned)
    assert before == {p: digest(p) for p in before}                    # the real repository was only read
