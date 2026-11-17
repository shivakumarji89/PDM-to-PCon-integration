"""Incremental ProductStudio MDB export: session + Articles workflow.

Uses the real 32-bit ACE bridge on disposable MDBs created under ``tmp_path``
(skipped when the provider is unavailable). The bundled templates are not in the
repository, so the template resolver is pointed at generated stand-ins whose
schema mirrors the constraints that matter: NOT-NULL boilerplate columns and the
Article -> CodeScheme / Package / ComGroup and ArticleClass -> Article foreign keys.
"""
from __future__ import annotations

import inspect
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from models.article import Article
from models.snapshot import Snapshot
from services import ocd_export_service as ocd
from services.article_mdb_export_service import ArticleMdbExportService
from services.mdb_export_session_service import ExportSessionError, MdbExportSessionService
from services.mdb_service import MDBService, _PS32


def _run_ps(script: str) -> subprocess.CompletedProcess:
    return subprocess.run([_PS32, "-NoProfile", "-Command", script], capture_output=True, text=True)


def _build_template(path: Path, manufacturer: str, include_class: bool = True) -> None:
    created = _run_ps(
        "$ErrorActionPreference='Stop'; $c=New-Object -ComObject ADOX.Catalog; "
        f"$c.Create('Provider=Microsoft.ACE.OLEDB.16.0;Data Source={path};'); $c.ActiveConnection.Close()"
    )
    if created.returncode:
        if any(m in created.stderr.lower() for m in ("provider cannot be found", "class not registered", "80040154")):
            pytest.skip("32-bit ACE provider is not installed")
        pytest.fail(created.stderr)
    ddl = [
        "CREATE TABLE tCOMd_Manufacturer (com_ManufacturerID COUNTER PRIMARY KEY, reg_ManufacturerCode TEXT(20))",
        "CREATE TABLE tCOMd_ComGroup (com_ComGroupID COUNTER PRIMARY KEY, com_ComGroupCode TEXT(50), "
        "com_ComGroupLabel TEXT(100))",
        "CREATE TABLE tCOMd_Package (com_PackageID COUNTER PRIMARY KEY, com_ComGroupID LONG, "
        "com_ManufacturerID LONG, reg_ProgramCode TEXT(50), reg_ProgramLabel TEXT(100), "
        "com_MaterialMF TEXT(20), com_MaterialPK TEXT(20))",
        "CREATE TABLE tCOMd_CodeScheme (com_CodeSchemeID COUNTER PRIMARY KEY, com_CodeSchemeName TEXT(100), "
        "com_CodeSchemeBody TEXT(255), com_PackageID LONG NOT NULL, com_StatusInfoID LONG NOT NULL)",
        "CREATE TABLE tCOMd_Article (com_ArticleID COUNTER PRIMARY KEY, com_ArticleCode TEXT(100), "
        "com_ArticleTypeCode TEXT(1), com_ComGroupID LONG, com_PackageID LONG, "
        "com_CodeSchemeID LONG NOT NULL, com_RelObjID LONG, com_ShortTextID LONG, com_LongTextID LONG, "
        "com_Discountable YESNO, com_OrderUnitCode TEXT(10), com_StatusInfoID LONG NOT NULL)",
        "CREATE TABLE tCOMd_ArticleClass (com_ArticleClassID COUNTER PRIMARY KEY, com_ArticleID LONG, "
        "com_ClassID LONG)",
        "CREATE TABLE tCOMd_RelObj (com_RelObjID COUNTER PRIMARY KEY, com_RelObjName TEXT(100), "
        "com_PackageID LONG)",
        "CREATE TABLE tCOMd_Text (com_TextID COUNTER PRIMARY KEY, com_TextName TEXT(255), "
        "com_TextTypeCode TEXT(50), com_PackageID LONG)",
    ]
    done = {"tCOMd_Manufacturer", "tCOMd_ComGroup", "tCOMd_Package", "tCOMd_CodeScheme",
            "tCOMd_Article", "tCOMd_ArticleClass", "tCOMd_RelObj", "tCOMd_Text"}
    for table in ocd._PRODUCT_TABLES:
        if table in done:
            continue
        if table == "tCOMd_Class" and not include_class:
            continue
        ddl.append(f"CREATE TABLE {table} ({ocd._PK[table]} COUNTER PRIMARY KEY, com_PackageID LONG)")
    ddl += [
        "ALTER TABLE tCOMd_Article ADD CONSTRAINT fk_art_scheme FOREIGN KEY (com_CodeSchemeID) "
        "REFERENCES tCOMd_CodeScheme (com_CodeSchemeID)",
        "ALTER TABLE tCOMd_Article ADD CONSTRAINT fk_art_pkg FOREIGN KEY (com_PackageID) "
        "REFERENCES tCOMd_Package (com_PackageID)",
        "ALTER TABLE tCOMd_Article ADD CONSTRAINT fk_art_group FOREIGN KEY (com_ComGroupID) "
        "REFERENCES tCOMd_ComGroup (com_ComGroupID)",
        "ALTER TABLE tCOMd_ArticleClass ADD CONSTRAINT fk_ac_art FOREIGN KEY (com_ArticleID) "
        "REFERENCES tCOMd_Article (com_ArticleID)",
    ]
    setup = "; ".join("$c.Execute('" + sql.replace("'", "''") + "') | Out-Null" for sql in ddl)
    proc = _run_ps(
        "$ErrorActionPreference='Stop'; $c=New-Object -ComObject ADODB.Connection; "
        f"$c.Open('Provider=Microsoft.ACE.OLEDB.16.0;Data Source={path};'); {setup}; $c.Close()"
    )
    assert proc.returncode == 0, proc.stderr
    seed = [
        {"op": "insert", "table": "tCOMd_Manufacturer", "rows": [
            {"com_ManufacturerID": 1, "reg_ManufacturerCode": manufacturer}]},
        {"op": "insert", "table": "tCOMd_ComGroup", "rows": [
            {"com_ComGroupID": 1, "com_ComGroupCode": "EXAMPLE", "com_ComGroupLabel": "Example"}]},
        {"op": "insert", "table": "tCOMd_Package", "rows": [
            {"com_PackageID": 1, "com_ComGroupID": 1, "com_ManufacturerID": 1,
             "reg_ProgramCode": "EXAMPLE", "reg_ProgramLabel": "Example"}]},
        # Example product that initialization must remove.
        {"op": "insert", "table": "tCOMd_CodeScheme", "rows": [
            {"com_CodeSchemeID": 7, "com_CodeSchemeName": "EXAMPLE", "com_CodeSchemeBody": "@",
             "com_PackageID": 1, "com_StatusInfoID": 3}]},
        {"op": "insert", "table": "tCOMd_Article", "rows": [
            {"com_ArticleID": 9, "com_ArticleCode": "EXAMPLE", "com_ComGroupID": 1, "com_PackageID": 1,
             "com_CodeSchemeID": 7, "com_StatusInfoID": 3}]},
        {"op": "insert", "table": "tCOMd_ArticleClass", "rows": [
            {"com_ArticleClassID": 1, "com_ArticleID": 9, "com_ClassID": 1}]},
    ]
    if include_class:
        seed.append({"op": "insert", "table": "tCOMd_Class", "rows": [
            {"com_ClassID": 1, "com_PackageID": 1}]})
    batch = MDBService(SimpleNamespace()).execute_batch(path, seed)
    assert batch.ok, batch.first_error()


class FailingMDB(MDBService):
    """Real bridge, but a bad op is appended to every transactional write."""

    fail = False

    def execute_batch(self, mdb_path, ops, transaction=False):
        if self.fail and transaction and any(o["op"] in ("insert", "update") for o in ops):
            ops = [*ops, {"op": "insert", "table": "tCOMd_DoesNotExist", "rows": [{"x": 1}]}]
        return super().execute_batch(mdb_path, ops, transaction=transaction)


@pytest.fixture(scope="module")
def templates(tmp_path_factory):
    """Build the stand-in templates once; tests copy them."""
    if not Path(_PS32).is_file():
        pytest.skip("32-bit Windows PowerShell / ACE integration unavailable")
    base = tmp_path_factory.mktemp("templates")
    made = {"seating": base / "tpl_seating.mdb", "tables": base / "tpl_tables.mdb",
            "broken": base / "tpl_broken.mdb"}
    _build_template(made["seating"], "hmx")
    _build_template(made["tables"], "tbl")
    _build_template(made["broken"], "hmx", include_class=False)
    return made


@pytest.fixture
def env(tmp_path, monkeypatch, templates):
    import shutil
    seating = tmp_path / "tpl_seating.mdb"
    tables = tmp_path / "tpl_tables.mdb"
    shutil.copyfile(templates["seating"], seating)
    shutil.copyfile(templates["tables"], tables)
    asked: list[str] = []

    def resolve(kind):
        asked.append(kind)
        return {"hm_seating": seating, "hm_tables": tables}.get(kind)

    monkeypatch.setattr(ocd, "_template_for_kind", resolve)
    ctx = SimpleNamespace()
    ctx.mdb_service = FailingMDB(ctx)
    sessions = MdbExportSessionService(ctx)
    sessions.store_dir = tmp_path / "sessions"
    ctx.mdb_export_session_service = sessions
    articles = ArticleMdbExportService(ctx)
    return SimpleNamespace(ctx=ctx, sessions=sessions, articles=articles, db=ctx.mdb_service,
                           tmp=tmp_path, asked=asked)


def make_snapshot(product_id="P1", category="Seating chair", codes=("AAA", "BBB", "CCC")):
    arts, members = [], []
    for i, base in enumerate(codes, start=1):
        arts.append(Article(id=f"{product_id}-a{i}", code=f"{base}.01", product_id=product_id))
        members.append(SimpleNamespace(
            id=f"{product_id}-m{i}", article_id=f"{product_id}-a{i}", reduced_article=base,
            relation_object="", code_scheme="", short_description="", long_description=""))
    product = SimpleNamespace(id=product_id, code=f"CODE-{product_id}", name=f"Product {product_id}",
                              range_name="Range", category=category)
    snap = Snapshot(product=product, articles=arts)
    snap.engineering.families = [SimpleNamespace(id="f1", name="F", members=members)]
    return snap


def sel(snapshot, *indexes):
    return {str(snapshot.articles[i].id) for i in indexes}


def rows(env, mdb, sql):
    return env.db.read_table(mdb, sql)


def article_rows(env, mdb):
    return rows(env, mdb, "SELECT * FROM tCOMd_Article ORDER BY com_ArticleID")


def start(env, snap, indexes=(0, 1)):
    session = env.sessions.initialize(snap, env.tmp / "out")
    result = env.articles.export_to_session(snap, session, sel(snap, *indexes))
    assert result["ok"], result
    return session, result


# 1 ---------------------------------------------------------------------

def test_first_export_creates_mdb_from_correct_template(env):
    seating = make_snapshot("P1", "Seating chair")
    session, result = start(env, seating)
    assert env.asked == ["hm_seating"]
    assert Path(session.mdb_path).is_file()
    assert session.template_kind == "hm_seating"
    assert session.manufacturer_id == "hmx"
    assert (session.package_id, session.comgroup_id) == (1, 1)

    desk = make_snapshot("P2", "Height adjustable desk")
    desk_session = env.sessions.initialize(desk, env.tmp / "out_tables")
    assert desk_session.template_kind == "hm_tables"
    assert desk_session.manufacturer_id == "tbl"

    package = rows(env, session.mdb_path, "SELECT * FROM tCOMd_Package")[0]
    assert package["reg_ProgramLabel"] == "Range"
    assert rows(env, session.mdb_path, "SELECT * FROM tCOMd_ComGroup")[0]["com_ComGroupLabel"] == "Range"
    # Example-product rows from the template are gone; manufacturer data retained.
    assert not any(r["com_ArticleCode"] == "EXAMPLE" for r in article_rows(env, session.mdb_path))
    assert rows(env, session.mdb_path, "SELECT * FROM tCOMd_Manufacturer")[0]["reg_ManufacturerCode"] == "hmx"


# 2, 3 -------------------------------------------------------------------

def test_only_selected_articles_exported_with_retained_ids(env):
    snap = make_snapshot()
    session, result = start(env, snap, indexes=(0, 2))
    assert (result["inserted"], result["updated"], result["skipped"]) == (2, 0, 0)
    got = article_rows(env, session.mdb_path)
    assert [r["com_ArticleCode"] for r in got] == ["AAA", "CCC"]
    ids = {r["com_ArticleCode"]: r["com_ArticleID"] for r in got}
    assert session.article_ids() == ids
    assert result["article_ids"] == ids
    assert session.article_map["AAA"]["source_ids"] == ["P1-a1"]
    assert session.article_map["AAA"]["source_codes"] == ["AAA.01"]
    assert session.workflow_status["articles"]["status"] == "exported"
    # Only article-stage tables carry data.
    for table in ("tCOMd_Class", "tCOMd_Property", "tCOMd_PropValue", "tCOMd_Relation",
                  "tCOMd_RelObj", "tCOMd_Text", "tCOMd_ArtBase", "tCOMd_Price", "tCOMd_ArticleClass"):
        assert rows(env, session.mdb_path, f"SELECT * FROM {table}") == [], table
    # Minimum supporting code scheme, one per article.
    schemes = rows(env, session.mdb_path, "SELECT * FROM tCOMd_CodeScheme ORDER BY com_CodeSchemeID")
    assert [(s["com_CodeSchemeName"], s["com_CodeSchemeBody"]) for s in schemes] == [
        ("AAA", "@,@,@"), ("CCC", "@,@,@")]
    assert all(s["com_StatusInfoID"] == 3 for s in schemes)  # template boilerplate retained
    assert result["schemes_created"] == 2


def test_session_persists_and_is_recovered_after_restart(env):
    snap = make_snapshot()
    session, _ = start(env, snap)
    restarted = MdbExportSessionService(env.ctx)
    restarted.store_dir = env.sessions.store_dir
    recovered = restarted.get_active(snap)
    assert recovered.mdb_path == session.mdb_path
    assert recovered.article_ids() == session.article_ids()
    assert recovered.package_id == session.package_id
    # Stale session (MDB deleted) is reported, not mistaken for "first export".
    Path(session.mdb_path).unlink()
    with pytest.raises(ExportSessionError):
        restarted.get_active(snap)


# 4, 5, 6, 8 -------------------------------------------------------------

def test_repeat_export_reuses_mdb_without_duplicates_and_keeps_other_data(env):
    snap = make_snapshot()
    session, first = start(env, snap)
    before = article_rows(env, session.mdb_path)
    # Data owned by a later workflow, linked to an exported article id.
    art_id = session.article_ids()["AAA"]
    assert env.db.execute_batch(session.mdb_path, [
        {"op": "insert", "table": "tCOMd_Class", "rows": [{"com_ClassID": 40, "com_PackageID": 1}]},
        {"op": "insert", "table": "tCOMd_ArticleClass", "rows": [
            {"com_ArticleClassID": 5, "com_ArticleID": art_id, "com_ClassID": 40}]},
    ]).ok

    again = env.sessions.get_active(snap)  # session, not a new template copy
    assert again.mdb_path == session.mdb_path
    second = env.articles.export_to_session(snap, again, sel(snap, 0, 1))
    assert second["ok"], second
    assert (second["inserted"], second["updated"], second["skipped"]) == (0, 0, 2)
    assert second["schemes_created"] == 0
    assert article_rows(env, session.mdb_path) == before
    assert len(rows(env, session.mdb_path, "SELECT * FROM tCOMd_CodeScheme")) == 2
    # Previously exported / other-workflow records intact.
    assert rows(env, session.mdb_path, "SELECT * FROM tCOMd_ArticleClass")[0]["com_ArticleID"] == art_id
    assert len(rows(env, session.mdb_path, "SELECT * FROM tCOMd_Class")) == 1


def test_new_selection_adds_articles_without_changing_existing_ids(env):
    snap = make_snapshot()
    session, _ = start(env, snap, indexes=(0, 1))
    old_ids = dict(session.article_ids())
    result = env.articles.export_to_session(snap, session, sel(snap, 1, 2))
    assert (result["inserted"], result["skipped"]) == (1, 1)
    ids = session.article_ids()
    assert {k: ids[k] for k in old_ids} == old_ids
    assert ids["CCC"] not in old_ids.values()
    assert [r["com_ArticleCode"] for r in article_rows(env, session.mdb_path)] == ["AAA", "BBB", "CCC"]
    assert session.workflow_status["articles"]["counts"]["inserted"] == 1


def test_changed_row_is_updated_in_place_keeping_primary_key(env):
    snap = make_snapshot()
    session, _ = start(env, snap, indexes=(0,))
    art_id = session.article_ids()["AAA"]
    assert env.db.execute_batch(session.mdb_path, [
        {"op": "update", "table": "tCOMd_Article", "set": {"com_OrderUnitCode": "XXX"},
         "where": {"com_ArticleID": art_id}}]).ok
    result = env.articles.export_to_session(snap, session, sel(snap, 0))
    assert (result["inserted"], result["updated"]) == (0, 1)
    row = article_rows(env, session.mdb_path)[0]
    assert (row["com_ArticleID"], row["com_OrderUnitCode"]) == (art_id, "C62")


def test_foreign_keys_are_valid(env):
    snap = make_snapshot()
    session, _ = start(env, snap)
    orphans = rows(env, session.mdb_path,
        "SELECT a.com_ArticleID FROM tCOMd_Article a LEFT JOIN tCOMd_CodeScheme s "
        "ON a.com_CodeSchemeID = s.com_CodeSchemeID WHERE s.com_CodeSchemeID IS NULL")
    assert orphans == []
    for row in article_rows(env, session.mdb_path):
        assert (row["com_PackageID"], row["com_ComGroupID"]) == (session.package_id, session.comgroup_id)


# 9 ----------------------------------------------------------------------

def test_failed_export_leaves_existing_contents_untouched(env):
    snap = make_snapshot()
    session, _ = start(env, snap, indexes=(0,))
    before_articles = article_rows(env, session.mdb_path)
    before_schemes = rows(env, session.mdb_path, "SELECT * FROM tCOMd_CodeScheme")
    before_map = {k: dict(v) for k, v in session.article_map.items()}

    env.db.fail = True
    result = env.articles.export_to_session(snap, session, sel(snap, 0, 1, 2))
    env.db.fail = False

    assert not result["ok"]
    assert article_rows(env, session.mdb_path) == before_articles
    assert rows(env, session.mdb_path, "SELECT * FROM tCOMd_CodeScheme") == before_schemes
    assert session.article_map == before_map
    assert env.sessions.get_active(snap).article_ids() == session.article_ids()
    # And the next good run succeeds with the same ids.
    ok = env.articles.export_to_session(snap, session, sel(snap, 0, 1, 2))
    assert ok["ok"] and ok["inserted"] == 2 and ok["skipped"] == 1


def test_failed_initialization_creates_no_file_and_no_session(env, templates):
    broken = env.tmp / "broken.mdb"
    import shutil
    shutil.copyfile(templates["broken"], broken)
    snap = make_snapshot()
    env.asked.clear()
    ocd_resolve = ocd._template_for_kind
    ocd._template_for_kind = lambda kind: broken
    try:
        with pytest.raises(ExportSessionError):
            env.sessions.initialize(snap, env.tmp / "out")
    finally:
        ocd._template_for_kind = ocd_resolve
    assert list((env.tmp / "out").glob("*")) == []
    assert env.sessions.load(snap) is None


def test_initialize_never_overwrites_an_existing_file(env):
    snap = make_snapshot()
    target = env.tmp / "out" / "pcr_data_com_ocd.mdb"
    target.parent.mkdir()
    target.write_bytes(b"precious")
    with pytest.raises(ExportSessionError):
        env.sessions.initialize(snap, env.tmp / "out")
    assert target.read_bytes() == b"precious"
    assert env.sessions.load(snap) is None


# 10 ---------------------------------------------------------------------

def test_switching_products_never_reuses_another_products_session(env):
    a, b = make_snapshot("P1"), make_snapshot("P2", codes=("XXX",))
    session_a, _ = start(env, a)
    assert env.sessions.get_active(b) is None            # P2 has no MDB yet
    session_b = env.sessions.initialize(b, env.tmp / "out_b")
    assert session_b.mdb_path != session_a.mdb_path
    before_a = article_rows(env, session_a.mdb_path)

    # P2's data cannot be written through P1's session.
    wrong = env.articles.export_to_session(b, session_a, {str(b.articles[0].id)})
    assert not wrong["ok"] and "different product" in wrong["error"]
    assert article_rows(env, session_a.mdb_path) == before_a

    assert env.articles.export_to_session(b, session_b, {str(b.articles[0].id)})["ok"]
    assert article_rows(env, session_a.mdb_path) == before_a
    assert [r["com_ArticleCode"] for r in article_rows(env, session_b.mdb_path)] == ["XXX"]
    assert env.sessions.get_active(a).mdb_path == session_a.mdb_path


def test_nothing_selected_is_rejected_without_writing(env):
    snap = make_snapshot()
    session = env.sessions.initialize(snap, env.tmp / "out")
    assert not env.articles.export_to_session(snap, session, set())["ok"]
    assert not env.articles.export_to_session(snap, session, {"unknown-id"})["ok"]
    assert article_rows(env, session.mdb_path) == []


# 11 ---------------------------------------------------------------------

def test_legacy_full_export_cannot_overwrite_a_session_mdb(env):
    snap = make_snapshot()
    session, _ = start(env, snap)
    before = article_rows(env, session.mdb_path)
    snap.generation_template = "hm_seating"
    service = ocd.OcdExportService(env.ctx)
    result = service.export(snap, session.mdb_path)
    assert result.error and "active ProductStudio export MDB" in result.error
    assert article_rows(env, session.mdb_path) == before


def test_ocd_build_accepts_selected_article_ids():
    assert "selected_article_ids" in inspect.signature(ocd.OcdExportService._build).parameters
