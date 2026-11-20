"""Class Creation on CodeSchemes shared across articles: update in place or clone-on-write.

Real workspaces share schemes (Dalby: 26 articles on 2 schemes; Lino: 3 on 1). Class Creation must extend
a scheme in place only when every article using it is selected; otherwise it clones the scheme, leaves the
original and all unselected articles untouched, and reassigns only the selected articles.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from models.mdb_export_session import MdbExportSession
from services import class_creation_mdb_export_service as module
from services.class_creation_mdb_export_service import ClassCreationMdbExportService

OLD_BODY = "@,@,@,@,@,@, ,OLD_ATTR:Frame_Finish, ,OLD_OPT:Top_Finish"
CODES = ["AAA100", "AAA110", "AAA120", "AAA130", "AAA140"]
TABLES = {
    "tCOMd_Class": ("classes", "com_ClassID"),
    "tCOMd_ArticleClass": ("article_classes", "com_ArticleClassID"),
    "tCOMd_CodeScheme": ("schemes", "com_CodeSchemeID"),
    "tCOMd_Article": ("articles", "com_ArticleID"),
}


class FakeMdb:
    def __init__(self, data):
        self.data, self.batches, self.fail = data, [], False

    @staticmethod
    def is_available():
        return True

    def read_tables(self, _path, queries):
        return {name: deepcopy(self.data.get(name, [])) for name in queries}

    def execute_batch(self, _path, operations, transaction=False):
        assert transaction is True
        self.batches.append(deepcopy(operations))
        staged = deepcopy(self.data)
        for op in operations:
            key, pk = TABLES[op["table"]]
            if op["op"] == "insert":
                staged[key].extend(deepcopy(op["rows"]))
            else:
                hit = [r for r in staged[key] if r[pk] == op["where"][pk]]
                assert hit, f"update of a missing row {op}"
                hit[0].update(deepcopy(op["set"]))
        if self.fail:
            return SimpleNamespace(ok=False, first_error=lambda: "injected failure")
        self.data.update(staged)
        return SimpleNamespace(ok=True, first_error=lambda: None)


def _world(tmp_path, shared=True, monkeypatch=None):
    """Five articles. shared=True: all on scheme 1 (named after the first article, like Dalby/Lino).
    shared=False: template-initialized layout, one scheme per article named after its code."""
    mdb = tmp_path / "x.mdb"
    mdb.touch()
    schemes, articles = [], []
    for index, code in enumerate(CODES):
        sid = 1 if shared else index + 1
        articles.append({"com_ArticleID": 100 + index, "com_ArticleCode": code, "com_PackageID": 10,
                         "com_CodeSchemeID": sid, "com_RelObjID": 7})
        if not shared or index == 0:
            schemes.append({"com_CodeSchemeID": sid, "com_CodeSchemeName": code, "com_PackageID": 10,
                            "com_CodeSchemeBody": OLD_BODY if shared else ",".join(["@"] * len(code)),
                            "com_CSVarCodeSep": "-", "com_CSVisibilityCode": "V", "com_CSTrim": False})
    data = {"package": [{"com_PackageID": 10}], "classes": [], "article_classes": [],
            "articles": articles, "schemes": schemes}
    db = FakeMdb(data)
    session = MdbExportSession(
        product_key="id:p1", mdb_path=str(mdb), package_id=10,
        article_map={code: {"mdb_id": 100 + i} for i, code in enumerate(CODES)},
        prototypes={"tCOMd_Class": {}, "tCOMd_ArticleClass": {}, "tCOMd_CodeScheme": {}})
    sessions = SimpleNamespace(
        product_key=lambda _s: "id:p1",
        record_workflow=lambda cur, wf, counts: cur.workflow_status.update({wf: counts}),
        save=lambda _s: None)
    classes = [SimpleNamespace(id="c1", name="Desk_Attribute", properties=[SimpleNamespace(property_id="p1")])]
    context = SimpleNamespace(
        mdb_export_session_service=sessions, mdb_service=db,
        xocd_export_service=SimpleNamespace(
            base_code_entries=lambda _s: [(f"a{i}", code) for i, code in enumerate(CODES)],
            _value_code_map=lambda _s: {}),
        engineering_class_service=SimpleNamespace(get_classes=lambda _s: classes),
        ocd_export_service=SimpleNamespace(
            _code_schemes=lambda _s, _p, _c, selected, _m, _proto: (
                [{"com_CodeSchemeBody": "@,@,@," + ",".join(
                    f"{a.property_id}:X" for cls in selected for a in cls.properties)}], {}, {})))
    snapshot = SimpleNamespace(product=SimpleNamespace(id="p1", category="Desk", range_name="Desk"))
    return ClassCreationMdbExportService(context), db, session, snapshot


@pytest.fixture(autouse=True)
def _classes(monkeypatch):
    monkeypatch.setattr(module, "classes_for_article",
                        lambda _snapshot, classes, _aid: [copy_cls for copy_cls in classes])


def ids(*indexes):
    return {f"a{i}" for i in indexes}


def _row(db, table, pk, value):
    return next(r for r in db.data[table] if r[pk] == value)


def _article_scheme(db, index):
    return _row(db, "articles", "com_ArticleID", 100 + index)["com_CodeSchemeID"]


# 1 -------------------------------------------------------------------------------------------------

def test_one_selected_article_sharing_a_scheme_with_unselected_articles_gets_a_clone(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    before = deepcopy(db.data)

    result = service.export_to_session(snapshot, session, ids(1))

    assert result["ok"] and result["verified"], result
    assert result["counts"]["code_schemes_cloned"] == 1
    assert result["counts"]["code_schemes_updated"] == 0
    assert result["counts"]["articles_reassigned"] == 1
    assert len(db.data["schemes"]) == 2
    clone = next(r for r in db.data["schemes"] if r["com_CodeSchemeID"] != 1)
    assert clone["com_CodeSchemeName"] == service.clone_name("AAA100", clone["com_CodeSchemeBody"])
    assert clone["com_CodeSchemeBody"] == OLD_BODY + ", ,p1:X"
    # settings of the source scheme are carried over, the id is new
    assert (clone["com_CSVarCodeSep"], clone["com_CSVisibilityCode"]) == ("-", "V")
    assert _article_scheme(db, 1) == clone["com_CodeSchemeID"]
    # 5: unselected articles and the original scheme are byte-for-byte unchanged
    for index in (0, 2, 3, 4):
        assert _article_scheme(db, index) == 1
        assert _row(db, "articles", "com_ArticleID", 100 + index) == before["articles"][index]
    assert _row(db, "schemes", "com_CodeSchemeID", 1) == before["schemes"][0]
    # the class link goes to the selected article only
    assert [r["com_ArticleID"] for r in db.data["article_classes"]] == [101]


# 2 -------------------------------------------------------------------------------------------------

def test_multiple_selected_articles_sharing_a_scheme_share_one_clone(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    result = service.export_to_session(snapshot, session, ids(1, 2))
    assert result["ok"], result
    assert result["counts"]["code_schemes_cloned"] == 1 and result["counts"]["articles_reassigned"] == 2
    assert len(db.data["schemes"]) == 2
    assert _article_scheme(db, 1) == _article_scheme(db, 2) != 1
    assert {_article_scheme(db, i) for i in (0, 3, 4)} == {1}
    assert sorted(r["com_ArticleID"] for r in db.data["article_classes"]) == [101, 102]


# 3 -------------------------------------------------------------------------------------------------

def test_all_articles_using_a_scheme_selected_updates_it_in_place(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    result = service.export_to_session(snapshot, session, ids(0, 1, 2, 3, 4))
    assert result["ok"], result
    assert result["counts"]["code_schemes_updated"] == 1 and result["counts"]["code_schemes_cloned"] == 0
    assert result["counts"]["articles_reassigned"] == 0
    assert len(db.data["schemes"]) == 1
    assert db.data["schemes"][0]["com_CodeSchemeID"] == 1
    assert db.data["schemes"][0]["com_CodeSchemeBody"] == OLD_BODY + ", ,p1:X"
    assert {_article_scheme(db, i) for i in range(5)} == {1}


# 4 -------------------------------------------------------------------------------------------------

def test_existing_scheme_content_and_spacing_are_preserved_verbatim(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    service.export_to_session(snapshot, session, ids(1))
    original = _row(db, "schemes", "com_CodeSchemeID", 1)["com_CodeSchemeBody"]
    clone = next(r for r in db.data["schemes"] if r["com_CodeSchemeID"] != 1)["com_CodeSchemeBody"]
    assert original == OLD_BODY
    assert clone.startswith(OLD_BODY)  # nothing rewritten, reordered or re-spaced


# 6 -------------------------------------------------------------------------------------------------

def test_repeated_export_creates_no_additional_schemes_or_links(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    assert service.export_to_session(snapshot, session, ids(1))["ok"]
    after_first = deepcopy(db.data)
    for _ in range(3):
        again = service.export_to_session(snapshot, session, ids(1))
        assert again["ok"], again
        assert again["operations"] == 0
    assert db.data == after_first
    assert len(db.batches) == 1


def test_a_later_export_of_another_article_reuses_the_existing_clone(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    assert service.export_to_session(snapshot, session, ids(1))["ok"]
    clone_id = _article_scheme(db, 1)
    result = service.export_to_session(snapshot, session, ids(2))
    assert result["ok"], result
    assert result["counts"]["code_schemes_cloned"] == 0
    assert result["counts"]["code_schemes_clone_reused"] == 1
    assert len(db.data["schemes"]) == 2
    assert _article_scheme(db, 2) == clone_id
    # no duplicate class links for either article
    links = [(r["com_ArticleID"], r["com_ClassID"]) for r in db.data["article_classes"]]
    assert len(links) == len(set(links)) == 2


def test_selecting_the_remaining_articles_afterwards_updates_the_original_in_place(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    service.export_to_session(snapshot, session, ids(1))
    result = service.export_to_session(snapshot, session, ids(0, 2, 3, 4))
    assert result["ok"], result
    assert result["counts"]["code_schemes_updated"] == 1 and result["counts"]["code_schemes_cloned"] == 0
    assert _row(db, "schemes", "com_CodeSchemeID", 1)["com_CodeSchemeBody"] == OLD_BODY + ", ,p1:X"
    assert len(db.data["schemes"]) == 2


def test_clone_names_are_deterministic_unique_and_within_the_column_limit(tmp_path):
    clone = ClassCreationMdbExportService.clone_name
    name = clone("AAA100", "body")
    assert name == clone("AAA100", "body") != clone("AAA100", "body2")
    assert len(clone("X" * 30, "body")) <= 30
    # a clone of a clone keeps the root name instead of stacking suffixes
    assert clone(name, "other").startswith("AAA100_CS") and clone(name, "other").count("_CS") == 1


# 7 -------------------------------------------------------------------------------------------------

def test_injected_failure_rolls_back_cloning_and_article_reassignment(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    before = deepcopy(db.data)
    db.fail = True
    result = service.export_to_session(snapshot, session, ids(1, 2))
    assert result["ok"] is False
    assert db.data == before  # no clone, no reassignment, no class, no link
    assert session.scheme_map == {}


# 8 -------------------------------------------------------------------------------------------------

def test_template_initialized_layout_is_updated_in_place_exactly_as_before(tmp_path):
    service, db, session, snapshot = _world(tmp_path, shared=False)
    result = service.export_to_session(snapshot, session, ids(0, 1))
    assert result["ok"], result
    assert result["counts"]["code_schemes_cloned"] == 0 and result["counts"]["articles_reassigned"] == 0
    assert result["counts"]["code_schemes_updated"] == 2
    assert len(db.data["schemes"]) == 5
    assert _row(db, "schemes", "com_CodeSchemeID", 1)["com_CodeSchemeBody"] == "@,@,@,@,@,@,p1:X"
    assert _row(db, "schemes", "com_CodeSchemeID", 3)["com_CodeSchemeBody"] == "@,@,@,@,@,@"
    assert [_article_scheme(db, i) for i in range(5)] == [1, 2, 3, 4, 5]


# safety ---------------------------------------------------------------------------------------------

def test_a_scheme_that_cannot_be_identified_fails_with_a_clear_error_and_writes_nothing(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    _row(db, "articles", "com_ArticleID", 101)["com_CodeSchemeID"] = 999
    before = deepcopy(db.data)
    result = service.export_to_session(snapshot, session, ids(1))
    assert result["ok"] is False
    assert "references CodeScheme id 999" in result["error"] and "safely" in result["error"]
    assert db.data == before and db.batches == []


def test_an_existing_scheme_with_the_clone_name_but_another_body_is_never_reused(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    name = service.clone_name("AAA100", OLD_BODY + ", ,p1:X")
    db.data["schemes"].append({"com_CodeSchemeID": 50, "com_CodeSchemeName": name, "com_PackageID": 10,
                               "com_CodeSchemeBody": "@,@,@,@,@,@,SOMETHING:Else"})
    before = deepcopy(db.data)
    result = service.export_to_session(snapshot, session, ids(1))
    assert result["ok"] is False and "refusing to reuse or overwrite" in result["error"]
    assert db.data == before


def test_article_code_length_not_matching_the_shared_pattern_is_refused(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    _row(db, "schemes", "com_CodeSchemeID", 1)["com_CodeSchemeBody"] = "@,@,@,@, ,OLD_ATTR:Frame_Finish"
    result = service.export_to_session(snapshot, session, ids(1))
    assert result["ok"] is False and "cannot be identified safely" in result["error"]


def test_dry_run_reports_the_clone_without_writing(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    preview = service.export_to_session(snapshot, session, ids(1), dry_run=True)
    assert preview["ok"] and preview["counts"]["code_schemes_cloned"] == 1
    assert db.batches == []
