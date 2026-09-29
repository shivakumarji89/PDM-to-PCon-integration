"""Tests for Relation Object validity classification and MDB identity/binding export."""

import unittest

from models.article_set import ArticleSet, SetAttribute, SetValue
from models.engineering import Engineering
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.property import Property, PropertyValue
from models.relation_object import RelationObject
from models.snapshot import Snapshot
from services.engineering.engineering_relation_service import EngineeringRelationService
from services.ocd_export_service import OcdExportService


class _RelationContext:
    class _EngineeringClassService:
        @staticmethod
        def resolve_config_codes(snapshot):
            return {}

    engineering_class_service = _EngineeringClassService()


class _ExportContext:
    class _RelationService:
        @staticmethod
        def ensure_relation_objects(snapshot):
            return snapshot.relation_objects

    engineering_relation_service = _RelationService()


def _relation_snapshot() -> Snapshot:
    parent = Property(
        id="parent",
        name="Parent",
        values=[
            PropertyValue(id="parent-a", property_id="parent", value="A"),
            PropertyValue(id="parent-b", property_id="parent", value="B"),
        ],
    )
    child = Property(
        id="child",
        name="Child",
        values=[
            PropertyValue(id="child-x", property_id="child", value="X", code="X"),
            PropertyValue(id="child-y", property_id="child", value="Y", code="Y"),
        ],
    )
    article_ids = ["a1", "a2"]
    article_set = ArticleSet(
        id="set-1",
        article_ids=article_ids,
        properties=[
            SetAttribute(
                id="parent",
                name="Parent",
                values=[
                    SetValue(id="parent-a", value="A", article_ids=["a1"]),
                    SetValue(id="parent-b", value="B", article_ids=["a2"]),
                ],
            ),
            SetAttribute(
                id="child",
                name="Child",
                values=[
                    SetValue(id="child-x", value="X", code="X", article_ids=["a1"]),
                    SetValue(id="child-y", value="Y", code="Y", article_ids=article_ids),
                ],
            ),
        ],
    )
    family = EngineeringFamily(
        id="family-1",
        members=[
            MemberArticle(id="m1", article_id="a1", reduced_article="BASE"),
            MemberArticle(id="m2", article_id="a2", reduced_article="BASE"),
        ],
    )
    return Snapshot(
        properties=[parent, child],
        property_values=parent.values + child.values,
        article_sets=[article_set],
        engineering=Engineering(families=[family]),
    )


class EngineeringRelationServiceTests(unittest.TestCase):
    def test_universal_value_has_no_relation_classification(self):
        snapshot = _relation_snapshot()
        kinds = EngineeringRelationService(_RelationContext()).classify_values(snapshot)

        self.assertEqual(kinds["child-y"], "generic")

    def test_dependency_value_is_combination_only_when_explained_by_other_property(self):
        snapshot = _relation_snapshot()
        kinds = EngineeringRelationService(_RelationContext()).classify_values(snapshot)

        self.assertEqual(kinds["child-x"], "combination")
        relations = EngineeringRelationService(_RelationContext()).build_relation_objects(snapshot)
        relation = next(r for r in relations if r.value_id == "child-x")
        self.assertIn("SPECIFIED Parent", relation.body)
        self.assertIn("Parent IN ('A')", relation.body)
        self.assertEqual(relation.type_code, "1")
        self.assertEqual(relation.domain, "C")

    def test_export_preserves_distinct_relobj_and_relation_ids_and_bindings(self):
        snapshot = Snapshot(
            relation_objects=[
                RelationObject(
                    name="A_Code_Parent",
                    type_code="3",
                    domain="C",
                    order=10,
                    body="CodeParent = 'A'",
                    property_id="parent",
                    rel_obj_id="100",
                    relation_id="900",
                    relation_name="AA_Code_Parent",
                ),
                RelationObject(
                    name="B_Child_X",
                    type_code="1",
                    domain="C",
                    order=20,
                    body="Restrictions: (Parent IN ('A'))",
                    property_id="child",
                    value_id="child-x",
                    rel_obj_id="100",
                    relation_id="901",
                    relation_name="BA_Child_X",
                ),
                RelationObject(
                    name="A_Code_Child",
                    type_code="3",
                    domain="C",
                    order=30,
                    body="CodeChild = 'X'",
                    property_id="child",
                ),
            ]
        )
        service = OcdExportService(_ExportContext())
        protos = {
            "tCOMd_RelObj": {},
            "tCOMd_Relation": {},
            "tCOMd_RelObjRel": {},
        }

        obj_rows, relation_rows, links, property_map, value_map = service._relations(
            snapshot, 1, protos
        )

        self.assertEqual([row["com_RelObjID"] for row in obj_rows], [100, 1])
        self.assertEqual(
            [row["com_RelationID"] for row in relation_rows],
            [900, 901, 1],
        )
        self.assertEqual(
            [(row["com_RelObjID"], row["com_RelationID"]) for row in links],
            [(100, 900), (100, 901), (1, 1)],
        )
        self.assertEqual(property_map["parent"], 100)
        self.assertEqual(property_map["child"], 1)
        self.assertEqual(value_map["child-x"], 100)


if __name__ == "__main__":
    unittest.main()
