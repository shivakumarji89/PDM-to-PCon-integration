"""VARCOND / Relations writer: existing relation-object links of an attached production workspace.

Real-data scenario (Dalby): every article points at the shared price relation object
``P_PRICING_DALBY``; the generated per-code relation ``P_PRICING_NODLE100`` must be created but must not
re-point the article. A link is created only when genuinely missing; replacement needs an explicit flag.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from models.mdb_export_session import MdbExportSession
from services import relation_mdb_export_service as module
from services.relation_mdb_export_service import RelationMdbExportService

TABLE_KEYS = {
    "tCOMd_RelObj": ("objects", "com_RelObjID"),
    "tCOMd_Relation": ("relations", "com_RelationID"),
    "tCOMd_RelObjRel": ("links", "com_RelObjRelID"),
    "tCOMd_Article": ("articles", "com_ArticleID"),
}


class FakeMdb:
    def __init__(self, data):
        self.data = data
        self.batches = []
        self.fail = False

    @staticmethod
    def is_available():
        return True

    def read_tables(self, _path, queries):
        out = {}
        for name in queries:
            if name == "object_max":
                out[name] = [{"max_id": max((r["com_RelObjID"] for r in self.data["objects"]), default=0)}]
            elif name == "relation_max":
                out[name] = [{"max_id": max((r["com_RelationID"] for r in self.data["relations"]), default=0)}]
            elif name == "link_max":
                out[name] = [{"max_id": max((r["com_RelObjRelID"] for r in self.data["links"]), default=0)}]
            elif name == "all_objects":
                out[name] = deepcopy(self.data["objects"])
            elif name == "all_links":
                out[name] = deepcopy(self.data["links"])
            elif name == "all_relations":
                out[name] = deepcopy(self.data["relations"])
            else:
                out[name] = deepcopy(self.data.get(name, []))
        return out

    def execute_batch(self, _path, operations, transaction=False):
        assert transaction is True
        self.batches.append(deepcopy(operations))
        if self.fail:
            return SimpleNamespace(ok=False, first_error=lambda: "injected failure")
        staged = deepcopy(self.data)
        for op in operations:
            key, pk = TABLE_KEYS[op["table"]]
            if op["op"] == "insert":
                staged[key].extend(deepcopy(op["rows"]))
            else:
                for row in staged[key]:
                    if row[pk] == op["where"][pk]:
                        row.update(op["set"])
        self.data.update(staged)  # all-or-nothing, like the real transaction
        return SimpleNamespace(ok=True, first_error=lambda: None)


def _world(article_link, attached=True):
    """Dalby-like MDB: article NODLE100 bound to ``article_link`` (None = missing)."""
    data = {
        "package": [{"com_PackageID": 10}],
        "objects": [{"com_RelObjID": 19573, "com_RelObjName": "P_PRICING_DALBY", "com_PackageID": 10}],
        "relations": [{"com_RelationID": 568100, "com_RelationName": "PA_PRICING_DALBY",
                       "com_RelationBody": "$VARCOND = 'series'", "com_PackageID": 10}],
        "links": [{"com_RelObjRelID": 1, "com_RelObjID": 19573, "com_RelationID": 568100,
                   "com_RelObjTypeCode": "3", "com_RelObjDomainCode": "P", "com_RelationOrder": 100}],
        "articles": [{"com_ArticleID": 20314, "com_ArticleCode": "NODLE100", "com_RelObjID": article_link,
                      "com_PackageID": 10}],
        "article_classes": [], "classes": [], "properties": [], "values": [],
    }
    db = FakeMdb(data)
    session = MdbExportSession(
        product_key="id:p1", mdb_path=__file__, package_id=10, attached_existing=attached,
        article_map={"NODLE100": {"mdb_id": 20314}},
        prototypes={"tCOMd_RelObj": {"com_StatusInfoID": 3}, "tCOMd_Relation": {"com_StatusInfoID": 3},
                    "tCOMd_RelObjRel": {"com_StatusInfoID": 3}},
    )
    sessions = SimpleNamespace(
        product_key=lambda _s: "id:p1",
        record_workflow=lambda current, workflow, counts: current.workflow_status.update({workflow: counts}),
        save=lambda _s: None)
    rel = SimpleNamespace(
        name="P_PRICING_NODLE100", relation_name="PA_PRICING_NODLE100", type_code="3", domain="P", order=100,
        body="$VARCOND = 'NODLE100-1'", article_codes=["NODLE100"], article_classes=[], property_ids=[],
        value_ids=[], rel_obj_id="", relation_id="")
    context = SimpleNamespace(
        mdb_service=db, mdb_export_session_service=sessions,
        xocd_export_service=SimpleNamespace(
            base_code_entries=lambda _s: [("a1", "NODLE100")], _value_code_map=lambda _s: {},
            _prop_ident=lambda n: n),
        engineering_class_service=SimpleNamespace(get_classes=lambda _s: []),
        engineering_relation_service=SimpleNamespace(ensure_relation_objects=lambda _s: [rel]),
    )
    return RelationMdbExportService(context), db, session, rel


@pytest.fixture(autouse=True)
def _scope(monkeypatch):
    monkeypatch.setattr(module, "build_class_creation_scope", lambda _s, _sel: SimpleNamespace(
        property_ids=[], option_ids=[], property_value_ids={}, option_value_ids={}))
    monkeypatch.setattr(module, "classes_for_article", lambda *_a, **_k: [])


SNAPSHOT = SimpleNamespace(product=SimpleNamespace(id="p1"), properties=[], options=[],
                           property_values=[], option_values=[])


def _run(service, session, **kw):
    return service.export_to_session(SNAPSHOT, session, {"a1"}, workflow="pricing_relations", **kw)


def _article_link(db):
    return db.data["articles"][0]["com_RelObjID"]


def test_dalby_shared_series_relation_is_preserved_but_generated_relation_is_created():
    service, db, session, _rel = _world(19573)
    preview = _run(service, session, dry_run=True)
    assert preview["ok"], preview
    entry = preview["conflicts"][0]
    assert entry["action"] == "preserved"
    assert (entry["existing"]["name"], entry["incoming"]["name"]) == ("P_PRICING_DALBY", "P_PRICING_NODLE100")
    assert entry["existing"]["relations"][0]["relation"] == "PA_PRICING_DALBY"
    assert "PRESERVED" in preview["warnings"][0] and "P_PRICING_DALBY (id 19573" in preview["warnings"][0]
    assert preview["counts"]["entity_links_updated"] == 0 and preview["counts"]["entity_links_preserved"] == 1
    assert db.batches == []  # preview wrote nothing

    result = _run(service, session)
    assert result["ok"], result
    assert result["counts"]["relation_objects_inserted"] == 1 and result["counts"]["relations_inserted"] == 1
    assert _article_link(db) == 19573  # the writer did NOT change the link
    assert {r["com_RelObjName"] for r in db.data["objects"]} == {"P_PRICING_DALBY", "P_PRICING_NODLE100"}


def test_preserved_link_is_stable_and_second_export_is_a_no_op():
    service, db, session, _rel = _world(19573)
    _run(service, session)
    snapshot_after_first = deepcopy(db.data)
    for _ in range(3):
        again = _run(service, session)
        assert again["ok"], again
        assert again["operations"] == 0
        assert _article_link(db) == 19573
    assert db.data == snapshot_after_first


def test_missing_link_is_created_and_then_stable():
    service, db, session, _rel = _world(None)
    result = _run(service, session)
    assert result["ok"], result
    assert result["conflicts"] == []
    new_id = next(r["com_RelObjID"] for r in db.data["objects"] if r["com_RelObjName"] == "P_PRICING_NODLE100")
    assert _article_link(db) == new_id
    assert _run(service, session)["operations"] == 0


def test_dangling_link_is_repaired():
    service, db, session, _rel = _world(424242)
    result = _run(service, session)
    assert result["ok"], result
    new_id = next(r["com_RelObjID"] for r in db.data["objects"] if r["com_RelObjName"] == "P_PRICING_NODLE100")
    assert _article_link(db) == new_id


def test_replacement_only_with_explicit_authorization():
    service, db, session, _rel = _world(19573)
    result = _run(service, session, replace_existing_links=True)
    assert result["ok"], result
    assert result["conflicts"][0]["action"] == "replaced"
    new_id = next(r["com_RelObjID"] for r in db.data["objects"] if r["com_RelObjName"] == "P_PRICING_NODLE100")
    assert _article_link(db) == new_id


def test_template_initialized_session_still_binds_the_generated_relation():
    service, db, session, _rel = _world(19573, attached=False)
    result = _run(service, session)
    assert result["ok"], result
    new_id = next(r["com_RelObjID"] for r in db.data["objects"] if r["com_RelObjName"] == "P_PRICING_NODLE100")
    assert _article_link(db) == new_id
    assert _run(service, session)["operations"] == 0


def test_injected_failure_rolls_back_objects_and_leaves_the_link_alone():
    service, db, session, _rel = _world(19573)
    before = deepcopy(db.data)
    db.fail = True
    result = _run(service, session)
    assert result["ok"] is False
    assert db.data == before
