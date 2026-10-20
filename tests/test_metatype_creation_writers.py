"""Property-creation writers, multi-file plans, persisted-state tracking, per-article value table and creation gating.

Isolated temporary fixtures only (a production working copy and a distinct staging working copy). No real repository
is written; the one real-repository test is strictly read-only.
"""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QApplication

from core.application_context import ApplicationContext
from core.config import AppConfig
from models.metatype_creation import PropertyIdentity, Translations, TranslationKind, TranslationRow
from services.metatype import staged_writer
from services.metatype.article_edit_session import ArticleEditSession
from services.metatype.article_write_plan import plan_article_edits
from services.metatype.property_creation_plan import CreationInputs, plan_property_creation
from services.metatype.property_rules import ArticleValueTable, ModePolicy
from services.metatype.staged_writer import StagingAuthorization, apply_plan, plan_fingerprint, rollback, sha256
from services.metatype.table_append import LAYOUTS, plan_append
from services.metatype.text_encoding import Encoding
from tests.test_metatype_write_contract import K2, SCHEMA, declare, make_series

FULL_SCHEMA = (SCHEMA + declare("go_propvalues", LAYOUTS["go_propvalues"]) + declare("go_proporder", LAYOUTS["go_proporder"])
               + declare("go_texts", LAYOUTS["go_texts"]))
TEXTS = ("##\r\n#  texts\r\n\r\nGOLD\t\t;en;Gr\xf6\xdfe\r\nGOLD\t\t;de;Gr\xf6\xdfe\r\n".encode("cp1252"))
PROPERTY, OWNER = "GNewProp", "MT_A"


def build_series(root: Path, texts: bytes = TEXTS, order: bytes = b"V0;  10\r\n", propvalues: bytes = b"MT_A;GOld;V0;X == 1\r\n"):
    data = make_series(root, schema=FULL_SCHEMA)
    (data / "go_texts.csv").write_bytes(texts)
    (data / "go_proporder.csv").write_bytes(order)
    (data / "go_propvalues.csv").write_bytes(propvalues)
    return data


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def world(tmp_path):
    out = {"tmp": tmp_path, "backups": tmp_path / "backups"}
    for name in ("prod", "stage"):
        wc = tmp_path / name
        (wc / ".svn").mkdir(parents=True)
        (wc / "hmx").mkdir()
        build_series(wc / "hmx")
        out[name] = wc / "hmx"
    return out


def reconcile(root):
    return ApplicationContext(AppConfig(metatype_repository_root=str(root))).metatype_article_service.reconcile("demo", root=root)


def translations(values=("V1", "V2"), de="Gr\xf6\xdfe"):
    rows = [TranslationRow(PROPERTY, TranslationKind.PROPERTY, "Size", de, "Taille", "Maat")]
    rows += [TranslationRow(v, TranslationKind.VALUE, f"en {v}", de, f"fr {v}", f"nl {v}") for v in values]
    return Translations("demo", PROPERTY, rows, "t0", "t1")


def good_inputs(**over):
    table = ArticleValueTable(["ART1", "ART2"], ["V1", "V2"], {"ART1": "CFG_ART1", "ART2": "CFG_ART2"})
    table.set_value("ART1", "V1")
    table.set_value("ART2", "V2")
    base = dict(owner=OWNER, property_name=PROPERTY, values=["V1", "V2"], default="V1", article_values=table,
                mode_policy=ModePolicy(confirmed=True), order={"V1": 20, "V2": 30},
                conditions={"V2": "GOther == @X"}, translations=translations(), text_fallback_encoding=None)
    base.update(over)
    return CreationInputs(**base)


def auth_for(world):
    return StagingAuthorization(world["stage"], world["prod"], "owner")


def data_file(root: Path, name: str) -> Path:
    return root / "demo" / "1" / name


# -- the five writers, one at a time ----------------------------------------------------------------------------------
def test_each_writer_appends_exact_rows_and_nothing_else(world):
    rec = reconcile(world["prod"])
    plan = plan_property_creation(rec, good_inputs())
    assert plan.ok, plan.blockers + plan.plan.problems
    assert [Path(f.path).name for f in plan.plan.files] == [
        "go_types.csv", "go_properties.csv", "go_propvalues.csv", "go_proporder.csv", "go_texts.csv"]
    new = {Path(f.path).name: f for f in plan.plan.files}
    assert plan.mode.mode == 3 | 128 | 8192
    assert new["go_types.csv"].new.endswith(b"\r\nMT_A;GNewProp;ch;V1;8323;\r\n")
    assert new["go_properties.csv"].new.endswith(b"MT_A;CFG_ART1;GNewProp;V1;;\r\nMT_A;CFG_ART2;GNewProp;V2;;\r\n")
    assert new["go_propvalues.csv"].new.endswith(b"MT_A;GNewProp;V2;GOther == @X\r\n")
    assert new["go_proporder.csv"].new == b"V0;  10\r\nV1;  20\r\nV2;  30\r\n"          # padding of the last row copied
    for file_plan in plan.plan.files:
        assert file_plan.new.startswith(file_plan.original) and file_plan.verified and not file_plan.problems


def test_go_texts_keeps_cp1252_crlf_comments_padding_and_orders_by_language(world):
    plan = plan_property_creation(reconcile(world["prod"]), good_inputs())
    texts = next(f for f in plan.plan.files if f.path.endswith("go_texts.csv"))
    assert texts.new.startswith(TEXTS)                                    # comments, blank line, old rows untouched
    appended = texts.new[len(TEXTS):].decode("cp1252").split("\r\n")
    assert appended[0] == "GNewProp\t\t;en;Size" and appended[1] == "V1\t\t;en;en V1"      # padding copied from last row
    assert [line.split(";")[1] for line in appended[:-1]] == ["en"] * 3 + ["de"] * 3 + ["fr"] * 3 + ["nl"] * 3
    assert "Gr\xf6\xdfe".encode("cp1252") in texts.new and b"\xc3" not in texts.new     # not re-encoded as UTF-8
    assert texts.new.count(b"\r\n") == texts.new.count(b"\n")


def test_bom_lf_and_unterminated_files_are_preserved(tmp_path):
    root = tmp_path / "hmx"
    root.mkdir()
    data = make_series(root, schema=FULL_SCHEMA)
    (data / "go_types.csv").write_bytes(b"\xef\xbb\xbfMT_A;GType;;T;0;\nMT_B;GType;;T;0;\n")          # BOM + LF
    (data / "go_proporder.csv").write_bytes(b"V0;10\nV1;11")                                       # no final newline
    (data / "go_properties.csv").write_bytes(b"MT_B;CFG_ART3;GP;V3;;\r\n# note\r\n\r\n")             # trailing comment/blank
    rec = reconcile(root)
    types = plan_append("go_types", rec.loader_result.table("go_types"), [["MT_A", "GNew", "ch", "V1", "3", ""]])
    assert types.ok and types.new == types.original + b"MT_A;GNew;ch;V1;3;\n" and types.new.startswith(b"\xef\xbb\xbf")
    order = plan_append("go_proporder", rec.loader_result.table("go_proporder"), [["V2", "12"]])
    assert order.ok and order.new == b"V0;10\nV1;11\nV2;12\n"                                   # terminator added, LF kept
    props = plan_append("go_properties", rec.loader_result.table("go_properties"), [["MT_A", "CFG_ART1", "GNew", "V1", "", ""]])
    assert props.ok and props.new == props.original + b"MT_A;CFG_ART1;GNew;V1;;\r\n"             # after comment and blank


def test_conflicts_duplicates_and_value_limits_are_refused(world):
    rec = reconcile(world["prod"])
    types = rec.loader_result.table("go_types")
    assert "already defined" in plan_append("go_types", types, [["MT_A", "GType", "ch", "V", "3", ""]]).problems[0]
    both = plan_append("go_types", types, [["MT_A", "G", "ch", "V", "3", ""], ["MT_A", "G", "ch", "V", "3", ""]])
    assert "appears twice" in both.problems[0]
    order = rec.loader_result.table("go_proporder")
    assert any("uint8" in p for p in plan_append("go_proporder", order, [["V9", "256"]]).problems)
    assert any("uint8" in p for p in plan_append("go_proporder", order, [["V9", "0"]]).problems)
    assert any("already defined" in p for p in plan_append("go_proporder", order, [["V0", "11"]]).problems)
    assert plan_append("go_proporder", order, [["V0", "10"]], skip_existing=True).changes == []         # idempotent
    assert any("uint16" in p for p in plan_append("go_types", types, [["MT_A", "G", "ch", "V", "70000", ""]]).problems)
    assert any("delimiter" in p for p in plan_append("go_types", types, [["MT_A", "G;x", "ch", "V", "3", ""]]).problems)
    assert any("comment" in p for p in plan_append("go_types", types, [["#MT", "G", "ch", "V", "3", ""]]).problems)
    assert any("language" in p for p in plan_append("go_texts", rec.loader_result.table("go_texts"), [["K", "xx", "t"]]).problems)
    assert any("required" in p for p in plan_append("go_types", types, [["MT_A", "G", "", "V", "3", ""]]).problems)


def test_unsupported_layout_and_ambiguous_encoding_are_refused(tmp_path, world):
    root = tmp_path / "other"
    root.mkdir()
    reordered = declare("go_types", ["name", "id", "format", "default", "mode", "filter"])
    make_series(root, schema=reordered + declare("go_articles", ["id", "manufacturer", "program", "article_nr", "prm_key", "chprm_key"]))
    layout = plan_append("go_types", reconcile(root).loader_result.table("go_types"), [["a", "b", "ch", "d", "3", ""]])
    assert "not the verified layout" in layout.problems[0]
    data_file(world["prod"], "go_texts.csv").write_bytes("K;en;Gr\xfcn \xc3\xbc\r\n".encode("latin-1"))
    ambiguous = plan_append("go_texts", reconcile(world["prod"]).loader_result.table("go_texts"), [["N", "en", "x"]])
    assert "ambiguous" in ambiguous.problems[0]
    assert "not declared" in plan_append("go_texts", None, [["N", "en", "x"]]).problems[0]


def test_non_ascii_text_into_ascii_file_needs_the_owner_encoding(world):
    data_file(world["prod"], "go_texts.csv").write_bytes(b"A;en;plain\r\n")
    rec = reconcile(world["prod"])
    assert "decision D5" in plan_property_creation(rec, good_inputs()).plan.problems[0]
    plan = plan_property_creation(rec, good_inputs(text_fallback_encoding=Encoding.CP1252))
    assert plan.ok and "Gr\xf6\xdfe".encode("cp1252") in plan.plan.files[-1].new


# -- the multi-file plan: blockers keep it from being ok --------------------------------------------------------------
def test_unresolved_decisions_block_the_plan_without_inventing_values(world):
    rec = reconcile(world["prod"])
    blocked = plan_property_creation(rec, good_inputs(mode_policy=ModePolicy()))           # D4 unconfirmed
    assert not blocked.ok and any("not confirmed" in b for b in blocked.blockers) and blocked.plan.files == []
    assert any("owner Metatype" in b for b in plan_property_creation(rec, good_inputs(owner=None)).blockers)
    assert any("owns no go_types" in b for b in plan_property_creation(rec, good_inputs(owner="MT_Z")).blockers)
    assert any("Step 4a" in b for b in plan_property_creation(rec, good_inputs(conditions={}, exceptions_recorded=True)).blockers)
    assert any("cover every value" in b for b in plan_property_creation(rec, good_inputs(order={"V1": 10})).blockers)
    assert any("not a value" in b for b in plan_property_creation(rec, good_inputs(order={"V9": 10})).blockers)
    assert any("not a value" in b for b in plan_property_creation(rec, good_inputs(conditions={"V9": "x"})).blockers)
    assert any("default" in b for b in plan_property_creation(rec, good_inputs(default="")).blockers)
    assert any("not confirmed" in b for b in plan_property_creation(rec, good_inputs(translations=None)).blockers)
    partial = translations(values=("V1",))
    assert any("missing for: V2" in b for b in plan_property_creation(rec, good_inputs(translations=partial)).blockers)
    empty_de = translations(de="")
    assert any("de text is empty" in b for b in plan_property_creation(rec, good_inputs(translations=empty_de)).blockers)
    unset = good_inputs(article_values=None)
    assert any("per-article values" in b for b in plan_property_creation(rec, unset).blockers)


def test_articles_of_another_metatype_or_without_configid_block(world):
    rec = reconcile(world["prod"])
    table = ArticleValueTable(["ART1", "ART3"], ["V1", "V2"], {"ART1": "CFG_ART1", "ART3": "CFG_ART3"})
    table.set_value("ART1", "V1")
    table.set_value("ART3", "V2")
    assert any("ART3 belongs to MT_B" in b for b in plan_property_creation(rec, good_inputs(article_values=table)).blockers)
    nocfg = ArticleValueTable(["ART1", "ART2"], ["V1", "V2"], {"ART1": "CFG_ART1"})
    nocfg.set_value("ART1", "V1")
    nocfg.set_value("ART2", "V2")
    assert any("never inferred" in b for b in plan_property_creation(rec, good_inputs(article_values=nocfg)).blockers)
    clash = ArticleValueTable(["ART1", "ART2"], ["V1", "V2"], {"ART1": "C", "ART2": "C"})
    clash.set_value("ART1", "V1")
    clash.set_value("ART2", "V2")
    assert any("shared by articles with different values" in b for b in plan_property_creation(rec, good_inputs(article_values=clash)).blockers)


def test_existing_property_rows_conflict(world):
    types = data_file(world["prod"], "go_types.csv")
    types.write_bytes(types.read_bytes() + b"MT_A;GNewProp;ch;V1;3;\r\n")
    plan = plan_property_creation(reconcile(world["prod"]), good_inputs())
    assert not plan.ok and any("already defined" in p for p in plan.plan.problems)


# -- applying the multi-file plan to staging ---------------------------------------------------------------------------
def apply_creation(world, **kw):
    plan = plan_property_creation(reconcile(world["prod"]), good_inputs())
    auth = auth_for(world)
    return plan, auth, apply_plan(plan.plan, auth, plan_fingerprint(plan.plan, auth), world["backups"], **kw)


def test_creation_writes_all_files_to_staging_only_and_verifies(world):
    prod_before = {p.name: sha256(p.read_bytes()) for p in (world["prod"] / "demo" / "1").iterdir()}
    plan, auth, result = apply_creation(world)
    assert result.success and len(result.files) == 5 and all(f.verified for f in result.files), result.problems
    for file_plan in plan.plan.files:
        assert (world["stage"] / Path(file_plan.path).relative_to(world["prod"])).read_bytes() == file_plan.new
    assert prod_before == {p.name: sha256(p.read_bytes()) for p in (world["prod"] / "demo" / "1").iterdir()}
    assert rollback(result) == []
    assert data_file(world["stage"], "go_types.csv").read_bytes() == plan.plan.files[0].original


def test_multi_file_failure_rolls_every_file_back(world, monkeypatch):
    plan = plan_property_creation(reconcile(world["prod"]), good_inputs())
    auth = auth_for(world)
    names = ["go_types.csv", "go_properties.csv", "go_propvalues.csv", "go_proporder.csv", "go_texts.csv"]
    before = {n: data_file(world["stage"], n).read_bytes() for n in names}
    real, calls = os.replace, []

    def flaky(src, dst):
        calls.append(dst)
        if len(calls) == 4:
            raise OSError("disk full")
        real(src, dst)

    monkeypatch.setattr(staged_writer.os, "replace", flaky)
    result = apply_plan(plan.plan, auth, plan_fingerprint(plan.plan, auth), world["backups"])
    monkeypatch.undo()
    assert not result.success and result.rolled_back and "disk full" in result.problems[0]
    assert {n: data_file(world["stage"], n).read_bytes() for n in names} == before


def test_source_hash_mismatch_and_tampering_abort_before_any_write(world):
    plan = plan_property_creation(reconcile(world["prod"]), good_inputs())
    auth = auth_for(world)
    token = plan_fingerprint(plan.plan, auth)
    texts = data_file(world["stage"], "go_texts.csv")
    texts.write_bytes(texts.read_bytes() + b"Z;en;late\r\n")                      # concurrent change in staging
    names = ["go_types.csv", "go_properties.csv", "go_texts.csv"]
    snapshot = {n: data_file(world["stage"], n).read_bytes() for n in names}
    result = apply_plan(plan.plan, auth, token, world["backups"])
    assert not result.success and "differs from the file the plan was computed from" in result.problems[0]
    assert {n: data_file(world["stage"], n).read_bytes() for n in names} == snapshot
    plan.plan.files[0].new += b"MT_X;GHidden;ch;V;3;\r\n"                         # tampered plan: token no longer matches
    texts.write_bytes(TEXTS)
    assert "does not match" in apply_plan(plan.plan, auth, token, world["backups"]).problems[0]


def test_post_write_parse_verification_catches_bad_bytes(world, monkeypatch):
    plan = plan_property_creation(reconcile(world["prod"]), good_inputs())
    auth = auth_for(world)
    real = staged_writer._atomic_write
    first = plan.plan.files[0]
    monkeypatch.setattr(staged_writer, "_atomic_write", lambda t, d: real(t, d.replace(b";8323;", b";9999;"))
                        if d == first.new else real(t, d))
    result = apply_plan(plan.plan, auth, plan_fingerprint(plan.plan, auth), world["backups"])
    assert not result.success and result.rolled_back and "re-read bytes differ" in result.problems[0]
    assert data_file(world["stage"], "go_types.csv").read_bytes() == first.original


# -- persisted-state tracking ------------------------------------------------------------------------------------------
def edit_session(root):
    session = ArticleEditSession(reconcile(root))
    session.set_value(K2, "id", "MT_B")
    return session


def test_written_failed_pending_and_source_are_distinct(world):
    session = edit_session(world["prod"])
    assert session.cell_state(K2, "id") == "pending" and session.written_count == 0
    plan = plan_article_edits(session)
    auth = auth_for(world)
    bad = apply_plan(plan, auth, "wrong-token", world["backups"])
    session.mark_failed(plan, "; ".join(bad.problems))
    assert session.cell_state(K2, "id") == "failed" and "does not match" in session.failure_reason(K2, "id")
    assert session.pending_count == 1 and session.written_count == 0                  # a failed write is never "saved"
    assert session.mark_applied(plan, bad) == 0
    good = apply_plan(plan, auth, plan_fingerprint(plan, auth), world["backups"])
    assert session.mark_applied(plan, good) == 1
    assert session.cell_state(K2, "id") == "written" and session.pending_count == 0 and session.written_count == 1
    assert session.value(K2, "id") == "MT_B" and session.source_value(K2, "id").strip() == "MT_A"      # snapshot intact
    assert session.counts()["written"] == 1 and session.discard() == 0 and session.written_count == 1


def test_written_state_survives_refresh_until_the_source_catches_up(world):
    session = edit_session(world["prod"])
    plan = plan_article_edits(session)
    auth = auth_for(world)
    session.mark_applied(plan, apply_plan(plan, auth, plan_fingerprint(plan, auth), world["backups"]))
    session.refresh(reconcile(world["prod"]))                                        # production still has the old value
    assert session.cell_state(K2, "id") == "written" and session.value(K2, "id") == "MT_B"
    assert session.set_value(K2, "id", "MT_C") and session.cell_state(K2, "id") == "pending"
    assert session.pending_changes()[0].old == "MT_B"                                 # baseline is the persisted value
    assert session.set_value(K2, "id", "MT_B") and session.cell_state(K2, "id") == "written"
    session.refresh(reconcile(world["stage"]))                                       # the written copy is now loaded
    assert session.cell_state(K2, "id") == "source" and session.written_count == 0


def test_failed_flag_survives_refresh_and_clears_on_new_edit(world):
    session = edit_session(world["prod"])
    plan = plan_article_edits(session)
    session.mark_failed(plan, "boom")
    session.refresh(reconcile(world["prod"]))
    assert session.cell_state(K2, "id") == "failed"
    session.set_value(K2, "id", "MT_Q")
    assert session.cell_state(K2, "id") == "pending"


def test_page_shows_written_after_verified_apply_and_failed_after_failure(qapp, world):
    page = make_page(world, authorised=True, qapp=qapp)
    page.articles_session.set_value(K2, "id", "MT_B")
    result = page.apply_to_staging(confirm=lambda t: True, backup_root=world["backups"])
    assert result.success and page.articles_session.cell_state(K2, "id") == "written"
    assert "now shown as written" in page.articles_diagnostics.toPlainText()
    page.articles_session.set_value(K2, "id", "MT_Z")
    staged = data_file(world["stage"], "go_articles.csv")
    staged.write_bytes(staged.read_bytes() + b"#concurrent\r\n")
    failed = page.apply_to_staging(confirm=lambda t: True, backup_root=world["backups"])
    assert failed is not None and not failed.success and page.articles_session.cell_state(K2, "id") == "failed"


# -- per-article value table (model, validation, UI) ------------------------------------------------------------------
def make_page(world, authorised, qapp, **cfg):
    from ui.pages.metatype_creation_page import MetatypeCreationPage
    config = AppConfig(metatype_repository_root=str(world["prod"]),
                       metatype_staging_root=str(world["stage"]) if authorised else "",
                       metatype_staging_authorised_by="owner" if authorised else "", **cfg)
    page = MetatypeCreationPage(ApplicationContext(config))
    page.series_combo.setCurrentIndex(page.series_combo.findData("demo"))
    page.load_series()
    return page


def feed_page(page, monkeypatch, articles=("ART1", "ART2")):
    cls = type(page._service)
    monkeypatch.setattr(page, "_owner_articles", lambda: list(articles))
    monkeypatch.setattr(cls, "identity", property(lambda self: PropertyIdentity("demo", PROPERTY, "Size", "t", "t")))
    monkeypatch.setattr(cls, "translations", property(lambda self: translations()))
    monkeypatch.setattr(cls, "validity", property(lambda self: None))
    page.creation_values_edit.setPlainText("V1\nV2")
    page.creation_default_edit.setText("V1")


def set_value(page, article, value):
    proxy = page.value_proxy
    for row in range(proxy.rowCount()):
        if proxy.index(row, 0).data() == article:
            assert proxy.setData(proxy.index(row, 2), value)
            return
    raise AssertionError(article)


def test_value_table_shows_missing_values_config_ids_and_conflicts(qapp, world, monkeypatch):
    page = make_page(world, False, qapp)
    feed_page(page, monkeypatch)
    model = page.value_model
    assert [model.index(r, 0).data() for r in range(2)] == ["ART1", "ART2"]
    assert [model.index(r, 1).data() for r in range(2)] == ["CFG_ART1", "CFG_ART2"]
    assert all(model.index(r, 2).data() == "" and "no value" in model.index(r, 3).data() for r in range(2))
    assert not model.flags(model.index(0, 1)) & Qt.ItemFlag.ItemIsEditable            # ConfigID is read-only
    assert model.flags(model.index(0, 2)) & Qt.ItemFlag.ItemIsEditable
    assert not model.setData(model.index(0, 0), "X") and not model.setData(model.index(0, 1), "X")
    set_value(page, "ART1", "V9")
    assert "not one of" in model.index(0, 3).data()
    set_value(page, "ART1", "V1")
    set_value(page, "ART2", "V2")
    assert model.index(0, 3).data() == "OK" and model.index(1, 3).data() == "OK" and model.table.complete


def test_value_table_never_reuses_a_value_and_flags_shared_configid(qapp, world, monkeypatch):
    page = make_page(world, False, qapp)
    feed_page(page, monkeypatch)
    set_value(page, "ART1", "V1")
    assert page.value_model.table.assigned == {"ART1": "V1"}                          # ART2 stays unassigned
    page.value_model.table.config_ids["ART2"] = "CFG_ART1"                            # force a shared ConfigID
    set_value(page, "ART2", "V2")
    assert "shared" in page.value_model.index(0, 3).data() and "shared" in page.value_model.index(1, 3).data()


def test_value_edits_survive_sorting_filtering_refresh_and_value_list_changes(qapp, world, monkeypatch):
    page = make_page(world, False, qapp)
    feed_page(page, monkeypatch)
    set_value(page, "ART2", "V2")
    page.value_table.sortByColumn(0, Qt.SortOrder.DescendingOrder)                    # ART2 is now row 0
    assert page.value_proxy.index(0, 0).data() == "ART2"
    set_value(page, "ART1", "V1")
    assert page.value_model.table.assigned == {"ART1": "V1", "ART2": "V2"}            # identity, not position
    page.value_proxy.set_text("art1")
    assert page.value_proxy.rowCount() == 1 and page.value_proxy.index(0, 0).data() == "ART1"
    page.value_proxy.set_text("")
    page.value_problem_filter.setCurrentIndex(1)                                      # problems only: none left
    assert page.value_proxy.rowCount() == 0
    page.value_problem_filter.setCurrentIndex(0)
    page.refresh_articles()
    assert page.value_model.table.assigned == {"ART1": "V1", "ART2": "V2"}
    page.creation_values_edit.setPlainText("V1\nV2\nV3")                              # value list grows: assignments kept
    assert page.value_model.table.assigned == {"ART1": "V1", "ART2": "V2"}
    monkeypatch.setattr(page, "_owner_articles", lambda: ["ART1"])
    page.refresh_articles()
    assert page.value_model.table.assigned == {"ART1": "V1"}                          # an article leaving the list drops


# -- creation gating --------------------------------------------------------------------------------------------------
def test_creation_is_disabled_with_specific_reasons_by_default(qapp, world, monkeypatch):
    page = make_page(world, False, qapp)
    assert not page.can_create()
    reasons = " ".join(page.creation_blockers())
    for expected in ("No staging working copy", "Nobody has authorised", "owner Metatype", "per-article values"):
        assert expected in reasons or expected.lower() in reasons.lower(), expected
    before = data_file(world["stage"], "go_types.csv").read_bytes()
    assert page.create_property() is None and "Creation is disabled" in page.articles_diagnostics.toPlainText()
    page.create_from_articles()
    assert "Creation prerequisites not met" in page.articles_diagnostics.toPlainText()
    assert data_file(world["stage"], "go_types.csv").read_bytes() == before


def ready_page(qapp, world, monkeypatch, **cfg):
    page = make_page(world, True, qapp, **cfg)
    feed_page(page, monkeypatch)
    set_value(page, "ART1", "V1")
    set_value(page, "ART2", "V2")
    page.creation_order_edit.setPlainText("V1;20\nV2;30")
    page.creation_conditions_edit.setPlainText("V2;GOther == @X")
    return page


def test_each_missing_prerequisite_keeps_creation_disabled(qapp, world, monkeypatch):
    page = ready_page(qapp, world, monkeypatch, metatype_mode_policy_confirmed=True)
    assert page.can_create(), page.creation_blockers()
    assert "Ready" in page.creation_status.text()
    page.creation_default_edit.setText("")
    assert not page.can_create() and any("default" in b for b in page.creation_blockers())
    page.creation_default_edit.setText("V1")
    page.creation_order_edit.setPlainText("V1;300")
    assert any("uint8" in b for b in page.creation_blockers())
    page.creation_order_edit.setPlainText("V1;20\nV2;30")
    page.creation_conditions_edit.setPlainText("garbage")
    assert any("not 'value;text'" in b for b in page.creation_blockers())


def test_unconfirmed_mode_policy_blocks_creation_even_when_everything_else_holds(qapp, world, monkeypatch):
    page = ready_page(qapp, world, monkeypatch)                                         # metatype_mode_policy_confirmed False
    assert not page.can_create() and any("not confirmed" in b for b in page.creation_blockers())


def test_page_creates_the_property_in_staging_after_confirmation(qapp, world, monkeypatch):
    page = ready_page(qapp, world, monkeypatch, metatype_mode_policy_confirmed=True)
    prod = {p.name: sha256(p.read_bytes()) for p in (world["prod"] / "demo" / "1").iterdir()}
    stage = data_file(world["stage"], "go_types.csv").read_bytes()
    assert page.create_property(confirm=lambda text: False, backup_root=world["backups"]) is None     # cancelled
    assert data_file(world["stage"], "go_types.csv").read_bytes() == stage
    shown = []
    result = page.create_property(confirm=lambda t: shown.append(t) or True, backup_root=world["backups"])
    assert result.success and "go_texts.csv" in shown[0] and "Confirmation token" in shown[0]
    assert b"MT_A;GNewProp;ch;V1;8323;" in data_file(world["stage"], "go_types.csv").read_bytes()
    assert prod == {p.name: sha256(p.read_bytes()) for p in (world["prod"] / "demo" / "1").iterdir()}
    assert "Written and verified" in page.articles_diagnostics.toPlainText()
    page.articles_create_button.click() if False else None


def test_ebmkdb_is_never_part_of_creation(qapp, world, monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("a process must not be started"))
    page = ready_page(qapp, world, monkeypatch, metatype_mode_policy_confirmed=True)
    assert page.create_property(confirm=lambda t: True, backup_root=world["backups"]).success


# -- real repository: read-only ---------------------------------------------------------------------------------------
REAL = Path(AppConfig().metatype_repository_root)


@pytest.mark.skipif(not REAL.exists(), reason="real HMX repository not available")
def test_real_series_tables_have_the_verified_layouts_read_only():
    ctx = ApplicationContext(AppConfig())
    checked = 0
    before = {}
    for name in ("atlas", "pullman", "verus", "aeron"):
        descr = REAL / name / "1" / "mt.inp_descr"
        if not descr.exists():
            continue
        for table in LAYOUTS:
            path = REAL / name / "1" / f"{table}.csv"
            if path.exists():
                before[path] = sha256(path.read_bytes())
        loaded = ctx.metatype_table_loader_service.load_family(name)
        for table, layout in LAYOUTS.items():
            declared = loaded.table(table)
            if declared is not None and declared.columns:
                assert [c.casefold() for c in declared.columns] == layout, (name, table)
                checked += 1
                plan = plan_append(table, declared, [["PROBE_ID", "PROBE", "ch", "d", "3", ""][:len(layout)]]
                                   if table != "go_texts" else [["PROBE", "en", "probe"]])
                if table == "go_proporder":
                    plan = plan_append(table, declared, [["PROBE_VALUE", "7"]])
                if plan.new:
                    assert plan.new.startswith(plan.original) and plan.verified, (name, table, plan.problems)
    assert checked >= 12
    assert before == {p: sha256(p.read_bytes()) for p in before}
