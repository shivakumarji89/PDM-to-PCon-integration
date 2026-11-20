"""Production class identity in attached workspaces (engineering ``Desk_Attribute`` vs production ``DESK_ATTR``).

No stable mapping exists between the two, so a new engineering class next to unresolved production
classes is an identity conflict that stops the class operation with zero writes. An exact-name match is
the only reuse, and keeps the existing ID and name.
"""
from copy import deepcopy

import pytest

from test_class_creation_scheme_clone import _classes, _world, ids  # noqa: F401  (autouse fixture)


def _production(db, name="DESK_ATTR", class_id=500, linked=(0, 1, 2, 3, 4)):
    db.data["classes"].append({"com_ClassID": class_id, "com_ClassName": name, "com_PackageID": 10})
    for n, index in enumerate(linked):
        db.data["article_classes"].append({"com_ArticleClassID": 900 + class_id + n,
                                           "com_ArticleID": 100 + index, "com_ClassID": class_id,
                                           "com_ArticleClassOrder": 100})


def test_attached_new_class_beside_unresolved_production_class_is_a_conflict_and_writes_nothing(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    session.attached_existing = True
    _production(db)
    before = deepcopy(db.data)
    result = service.export_to_session(snapshot, session, ids(1))
    assert result["ok"] is False
    c = result["conflicts"][0]
    assert (c["kind"], c["article"], c["action"]) == ("class_identity", "AAA110", "stopped")
    assert c["incoming_classes"] == ["Desk_Attribute"] and c["existing_production_classes"] == ["DESK_ATTR"]
    assert "no reliable mapping" in result["error"] and "DESK_ATTR" in result["error"]
    assert db.data == before and db.batches == []      # no class, link, scheme or article change


def test_dry_run_reports_the_same_conflict(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    session.attached_existing = True
    _production(db)
    result = service.export_to_session(snapshot, session, ids(1), dry_run=True)
    assert result["ok"] is False and result["conflicts"][0]["kind"] == "class_identity"


def test_exact_name_match_reuses_the_production_class_id_and_name(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    session.attached_existing = True
    _production(db, name="Desk_Attribute", class_id=500, linked=())
    result = service.export_to_session(snapshot, session, ids(1))
    assert result["ok"], result
    assert result["counts"]["classes_inserted"] == 0 and result["counts"]["classes_reused"] == 1
    assert [(r["com_ClassID"], r["com_ClassName"]) for r in db.data["classes"]] == [(500, "Desk_Attribute")]
    assert [r["com_ClassID"] for r in db.data["article_classes"]] == [500]


def test_repeated_export_after_reuse_creates_no_duplicates(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    session.attached_existing = True
    _production(db, name="Desk_Attribute", class_id=500, linked=())
    assert service.export_to_session(snapshot, session, ids(1))["ok"]
    after = deepcopy(db.data)
    again = service.export_to_session(snapshot, session, ids(1))
    assert again["ok"] and db.data == after


def test_attached_article_without_production_classes_still_gets_its_new_class(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    session.attached_existing = True
    result = service.export_to_session(snapshot, session, ids(1))
    assert result["ok"] and result["counts"]["classes_inserted"] == 1


def test_unselected_articles_with_production_classes_do_not_block_other_articles(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    session.attached_existing = True
    _production(db, linked=(0, 2, 3, 4))          # article 1 has no production class
    before = deepcopy(db.data)
    result = service.export_to_session(snapshot, session, ids(1))
    assert result["ok"], result
    for i in (0, 2, 3, 4):
        assert next(r for r in db.data["articles"] if r["com_ArticleID"] == 100 + i) == \
               next(r for r in before["articles"] if r["com_ArticleID"] == 100 + i)


def test_template_initialized_session_keeps_previous_behaviour(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    session.attached_existing = False
    _production(db)
    result = service.export_to_session(snapshot, session, ids(1))
    assert result["ok"], result
    assert result["counts"]["classes_inserted"] == 1
    assert {r["com_ClassName"] for r in db.data["classes"]} == {"DESK_ATTR", "Desk_Attribute"}


def test_failed_transaction_after_identity_check_restores_state(tmp_path):
    service, db, session, snapshot = _world(tmp_path)
    session.attached_existing = True
    db.fail = True
    before = deepcopy(db.data)
    result = service.export_to_session(snapshot, session, ids(1))
    assert result["ok"] is False and db.data == before
