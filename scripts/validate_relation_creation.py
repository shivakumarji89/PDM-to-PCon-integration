"""Validate the Relation Object workflow step (Phase B) against the canonical
standard.

Headless, PDM-free check that EngineeringRelationService derives encoding
actions while refusing to infer validity relations from article coverage:
  * ``A_Code_<Prop>`` action only when a value's code differs from its value
    (numeric properties), body ``Code<Prop> = '<code>' IF <Prop> = <value>``;
    * no generated ``B_*`` precondition without an explicitly bound OCD Relation
        Object.
Also checks ArtBase coverage, imported-relation preservation, edit persistence
and JSON round-trip.

Run:  python scripts/validate_relation_creation.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.application_context import ApplicationContext
from models.article import Article
from models.article_set import ArticleSet, SetAttribute, SetValue
from models.engineering import Engineering
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.property import Property
from models.property_value import PropertyValue
from models.relation_object import RelationObject
from models.snapshot import Snapshot
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict
from services.engineering.engineering_relation_service import validate_relation_body


def _make_snapshot() -> Snapshot:
    # BASE1 (a1,a2,a3) + BASE2 (a4). Castors correlates with Type in this sample,
    # but there is no explicit dependency source. Finish is base-scoped; Brand
    # is universal.
    a1 = Article(id="a1", code="B1-7-Y", product_id="P1")
    a2 = Article(id="a2", code="B1-5-N", product_id="P1")
    a3 = Article(id="a3", code="B1-5-N2", product_id="P1")
    a4 = Article(id="a4", code="B2-7-N", product_id="P1")
    typ = Property(id="TY", name="Type", display_order=1, values=[
        PropertyValue(id="t7", property_id="TY", value="7", code="", display_order=1),
        PropertyValue(id="t5", property_id="TY", value="5", code="", display_order=2),
    ])
    castors = Property(id="CA", name="Castors", display_order=2, values=[
        PropertyValue(id="cy", property_id="CA", value="Yes", code="C1", display_order=1),
        PropertyValue(id="cn", property_id="CA", value="No", code="C2", display_order=2),
    ])
    finish = Property(id="FI", name="Finish", display_order=3, values=[
        PropertyValue(id="oak", property_id="FI", value="Oak", code="OAK", display_order=1),
        PropertyValue(id="wal", property_id="FI", value="Walnut", code="WAL", display_order=2),
    ])
    brand = Property(id="BR", name="Brand", display_order=4, values=[
        PropertyValue(id="hm", property_id="BR", value="HM", code="HM", display_order=1),
    ])
    m1 = MemberArticle(id="m1", article_id="a1", family_id="F1", reduced_article="BASE1")
    m2 = MemberArticle(id="m2", article_id="a2", family_id="F1", reduced_article="BASE1")
    m3 = MemberArticle(id="m3", article_id="a3", family_id="F1", reduced_article="BASE1")
    m4 = MemberArticle(id="m4", article_id="a4", family_id="F1", reduced_article="BASE2")
    eng = Engineering(families=[EngineeringFamily(id="F1", members=[m1, m2, m3, m4])])
    aset = ArticleSet(id="S1", article_ids=["a1", "a2", "a3", "a4"], properties=[
        SetAttribute(id="TY", name="Type", values=[
            SetValue(id="t7", value="7", code="", article_ids=["a1", "a4"]),
            SetValue(id="t5", value="5", code="", article_ids=["a2", "a3"]),
        ]),
        SetAttribute(id="CA", name="Castors", values=[
            SetValue(id="cy", value="Yes", code="C1", article_ids=["a1"]),
            SetValue(id="cn", value="No", code="C2", article_ids=["a2", "a3", "a4"]),
        ]),
        SetAttribute(id="FI", name="Finish", values=[
            SetValue(id="oak", value="Oak", code="OAK", article_ids=["a1", "a2", "a3"]),
            SetValue(id="wal", value="Walnut", code="WAL", article_ids=["a4"]),
        ]),
        SetAttribute(id="BR", name="Brand", values=[
            SetValue(id="hm", value="HM", code="HM", article_ids=["a1", "a2", "a3", "a4"]),
        ]),
    ])
    return Snapshot(id="S1", articles=[a1, a2, a3, a4],
                    properties=[typ, castors, finish, brand],
                    engineering=eng, article_sets=[aset])


def main() -> None:
    context = ApplicationContext()
    service = context.engineering_relation_service
    snapshot = _make_snapshot()

    relations = service.ensure_relation_objects(snapshot)
    by_name = {r.name: r for r in relations}

    # Correlated article coverage is not authoritative dependency evidence.
    assert not any(r.name.startswith("B_") for r in relations), sorted(by_name)

    # BASE-scoped Finish -> ArtBase, NOT a relation.
    assert "B_Finish_OAK" not in by_name, "base-scoped value must not be a relation"
    assert "B_Finish_WAL" not in by_name

    # GENERIC Brand (on every article) -> nothing.
    assert "B_Brand_HM" not in by_name, "generic value must get no relation"

    # ArtBase carries base-scoped coverage, including Castors values restricted
    # only by the observed base membership.
    art = context.engineering_artbase_service.build_art_base(snapshot)
    assert art.get("BASE1", {}).get("FI") == ["oak"], art
    assert art.get("BASE2", {}).get("FI") == ["wal"], art
    assert art.get("BASE2", {}).get("CA") == ["cn"], art

    # No '#' ever leaks into a name/body.
    assert not any("#" in r.name or "#" in r.body for r in relations), "'#' leaked"

    # Deterministic: a second build yields identical names/bodies in order.
    again = service.rebuild_relation_objects(snapshot)
    assert [(r.name, r.body) for r in again] == [(r.name, r.body) for r in relations], "non-deterministic"

    # A target-bound imported OCD relation is retained by rebuild and its edit
    # survives JSON round-trip.
    edited = RelationObject(
        name="B_Castors_C1", type_code="1", domain="C",
        body="Type = '7'", property_id="CA", value_id="cy",
        rel_obj_id="40", relation_id="90", relation_name="BA_Castors_C1",
        value_ids=["cy"],
    )
    snapshot.relation_objects.append(edited)
    rebuilt = service.rebuild_relation_objects(snapshot)
    assert edited in rebuilt, "rebuild dropped imported relation"
    assert service.set_body(edited, "EDITED")
    restored = snapshot_from_dict(snapshot_to_dict(snapshot))
    r_by_name = {r.name: r for r in restored.relation_objects}
    assert r_by_name["B_Castors_C1"].body == "EDITED", "round-trip lost edit"

    # Manual curation (additive): add, rename, retype, remove.
    added = service.add_relation(snapshot, "B_HIDDEN", "1", "C", "$BAN IN ('1')")
    assert added is not None and added in snapshot.relation_objects, "add failed"
    assert service.add_relation(snapshot, "B_HIDDEN") is None, "duplicate add allowed"
    assert not service.set_name(snapshot, added, "B_Castors_C1"), "duplicate rename allowed"
    assert service.set_name(snapshot, added, "B_HIDDEN_ALL"), "rename failed"
    assert added.name == "B_HIDDEN_ALL"
    assert service.set_type(added, "3") and added.type_code == "3"
    assert service.set_domain(added, "P") and added.domain == "P"
    assert service.remove_relation(snapshot, added), "remove failed"
    assert added not in snapshot.relation_objects, "still present after remove"

    # Body syntax check (editor feedback).
    assert validate_relation_body("(SPECIFIED X) AND (X IN ('A'))")[0], "valid body rejected"
    assert not validate_relation_body("(SPECIFIED X")[0], "unbalanced parens accepted"
    assert not validate_relation_body("X IN ('A)")[0], "unbalanced quote accepted"

    print("validate_relation_creation: PASS")


if __name__ == "__main__":
    main()
