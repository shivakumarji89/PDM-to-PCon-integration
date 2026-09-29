"""Regression tests for relation derivation, bindings, and real MDB round-trips.

Set ``MK_REAL_OCD_MDB`` to a real ``pcr_data_com_ocd.mdb`` to run the two
database-backed tests in addition to the portable unit tests.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

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
from services.engineering.engineering_artbase_service import EngineeringArtbaseService
from services.engineering.engineering_relation_service import EngineeringRelationService
from services.mdb_service import MDBService
from services.ocd_export_service import OcdExportService
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict
import services.ocd_export_service as ocd_export_module


class _EngineeringClassService:
    @staticmethod
    def resolve_config_codes(_snapshot):
        return {}


class _Context:
    def __init__(self):
        self.engineering_class_service = _EngineeringClassService()
        self.engineering_relation_service = EngineeringRelationService(self)
        self.engineering_artbase_service = EngineeringArtbaseService(self)


def _snapshot() -> Snapshot:
    articles = [
        Article(id="a1", code="B1-1"),
        Article(id="a2", code="B1-2"),
        Article(id="a3", code="B2-1"),
    ]
    properties = [
        Property(id="size", name="Size", values=[
            PropertyValue(id="s1", property_id="size", value="1"),
            PropertyValue(id="s2", property_id="size", value="2"),
        ]),
        Property(id="choice", name="Choice", values=[
            PropertyValue(id="cy", property_id="choice", value="Yes", code="Y"),
            PropertyValue(id="cn", property_id="choice", value="No", code="N"),
        ]),
        Property(id="trim", name="Trim", values=[
            PropertyValue(id="oak", property_id="trim", value="Oak", code="OAK"),
            PropertyValue(id="wal", property_id="trim", value="Walnut", code="WAL"),
        ]),
        Property(id="brand", name="Brand", values=[
            PropertyValue(id="all", property_id="brand", value="All", code="ALL"),
        ]),
        Property(id="width", name="Width", values=[
            PropertyValue(id="w100", property_id="width", value="100", code="A"),
        ]),
    ]
    article_set = ArticleSet(
        id="set",
        article_ids=["a1", "a2", "a3"],
        properties=[
            SetAttribute(id="size", name="Size", values=[
                SetValue(id="s1", value="1", article_ids=["a1"]),
                SetValue(id="s2", value="2", article_ids=["a2", "a3"]),
            ]),
            SetAttribute(id="choice", name="Choice", values=[
                SetValue(id="cy", value="Yes", code="Y", article_ids=["a1"]),
                SetValue(id="cn", value="No", code="N", article_ids=["a2", "a3"]),
            ]),
            SetAttribute(id="trim", name="Trim", values=[
                SetValue(id="oak", value="Oak", code="OAK", article_ids=["a1", "a2"]),
                SetValue(id="wal", value="Walnut", code="WAL", article_ids=["a3"]),
            ]),
            SetAttribute(id="brand", name="Brand", values=[
                SetValue(id="all", value="All", code="ALL", article_ids=["a1", "a2", "a3"]),
            ]),
            SetAttribute(id="width", name="Width", values=[
                SetValue(id="w100", value="100", code="A", article_ids=["a1", "a2", "a3"]),
            ]),
        ],
    )
    members = [
        MemberArticle(id="m1", article_id="a1", family_id="f", reduced_article="BASE1"),
        MemberArticle(id="m2", article_id="a2", family_id="f", reduced_article="BASE1"),
        MemberArticle(id="m3", article_id="a3", family_id="f", reduced_article="BASE2"),
    ]
    return Snapshot(
        id="snapshot",
        articles=articles,
        properties=properties,
        engineering=Engineering(families=[EngineeringFamily(id="f", members=members)]),
        article_sets=[article_set],
    )


def _id(value) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        try:
            return str(int(float(text)))
        except ValueError:
            pass
    return text


def _valid_relation_links(data) -> Counter:
    object_ids = {_id(row.get("com_RelObjID")) for row in data.rows("tCOMd_RelObj")}
    relation_ids = {_id(row.get("com_RelationID")) for row in data.rows("tCOMd_Relation")}
    return Counter(
        (
            _id(row.get("com_RelObjID")),
            _id(row.get("com_RelationID")),
            str(row.get("com_RelObjTypeCode") or ""),
            str(row.get("com_RelObjDomainCode") or ""),
            _id(row.get("com_RelationOrder")),
        )
        for row in data.rows("tCOMd_RelObjRel")
        if _id(row.get("com_RelObjID")) in object_ids
        and _id(row.get("com_RelationID")) in relation_ids
    )


def _semantic_bindings(data, table: str) -> Counter:
    properties = {
        _id(row.get("com_PropertyID")): str(row.get("com_PropName") or "")
        for row in data.rows("tCOMd_Property")
    }
    if table == "tCOMd_Property":
        return Counter(
            (str(row.get("com_PropName") or ""), _id(row.get("com_RelObjID")))
            for row in data.rows(table)
            if row.get("com_RelObjID") not in (None, "")
        )
    return Counter(
        (
            properties.get(_id(row.get("com_PropertyID")), ""),
            str(row.get("com_PropValueFrom") or ""),
            _id(row.get("com_RelObjID")),
        )
        for row in data.rows(table)
        if row.get("com_RelObjID") not in (None, "")
    )


class RelationObjectWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.context = _Context()
        self.service = self.context.engineering_relation_service

    def test_universal_value_has_no_validity_relation(self):
        relations = self.service.build_relation_objects(_snapshot())

        self.assertNotIn("B_Brand_ALL", {relation.name for relation in relations})

    def test_article_coverage_correlation_does_not_create_dependency(self):
        snapshot = _snapshot()
        relations = self.service.build_relation_objects(snapshot)
        by_name = {relation.name: relation for relation in relations}

        self.assertNotIn("B_Choice_Y", by_name)
        self.assertFalse(any(name.startswith("B_") for name in by_name))
        self.assertNotIn("B_Trim_OAK", by_name)
        art_base = self.context.engineering_artbase_service.build_art_base(snapshot)
        self.assertEqual(art_base.get("BASE1", {}).get("trim"), ["oak"])
        self.assertEqual(art_base.get("BASE2", {}).get("trim"), ["wal"])
        self.assertEqual(art_base.get("BASE2", {}).get("choice"), ["cn"])

    def test_explicit_value_relation_excludes_only_its_target_from_artbase(self):
        snapshot = _snapshot()
        choice = next(prop for prop in snapshot.properties if prop.id == "choice")
        choice.values.append(
            PropertyValue(id="cb", property_id="choice", value="Base only", code="B")
        )
        choice_values = snapshot.article_sets[0].properties[1].values
        next(value for value in choice_values if value.id == "cn").article_ids = ["a2"]
        choice_values.append(
            SetValue(id="cb", value="Base only", code="B", article_ids=["a3"])
        )
        value_relation = RelationObject(
            name="B_Choice_Y",
            type_code="1",
            domain="C",
            body="Size IN ('1')",
            property_id="choice",
            value_id="cy",
            rel_obj_id="40",
            relation_id="90",
            value_ids=["cy"],
        )
        article_relation = RelationObject(
            name="B_Article_Only",
            type_code="1",
            domain="C",
            body="Type IN ('B')",
            rel_obj_id="41",
            relation_id="91",
        )
        snapshot.relation_objects = [value_relation, article_relation]

        rebuilt = self.service.rebuild_relation_objects(snapshot)
        art_base = self.context.engineering_artbase_service.build_art_base(snapshot)

        self.assertIn(value_relation, rebuilt)
        self.assertIn(article_relation, rebuilt)
        self.assertEqual(self.service.related_value_ids(snapshot), {"cy"})
        self.assertEqual(art_base.get("BASE1", {}).get("choice"), ["cn"])
        self.assertEqual(art_base.get("BASE2", {}).get("choice"), ["cb"])
        self.assertNotIn("cy", {
            value_id
            for properties in art_base.values()
            for value_ids in properties.values()
            for value_id in value_ids
        })

    def test_encoding_relation_is_independent_of_validity_relation(self):
        relations = self.service.build_relation_objects(_snapshot())
        by_name = {relation.name: relation for relation in relations}

        self.assertIn("A_Code_Width", by_name)
        self.assertIn("CodeWidth = 'A' IF Width = 100", by_name["A_Code_Width"].body)
        self.assertNotIn("B_Width_100", by_name)

    def test_explicit_bound_relation_is_preserved_and_exported(self):
        explicit = RelationObject(
            name="B_Choice_Y",
            type_code="1",
            domain="C",
            order=70,
            body="(SPECIFIED Size) AND (Size IN ('1'))",
            property_id="choice",
            value_id="cy",
            rel_obj_id="40",
            relation_id="90",
            relation_name="BA_Choice_Y",
            property_ids=["choice"],
            value_ids=["cy", "cy-alias"],
        )
        snapshot = Snapshot(relation_objects=[explicit])
        relations = self.service.rebuild_relation_objects(snapshot)

        self.assertIs(relations[0], explicit)
        self.assertEqual(self.service.related_value_ids(snapshot), {"cy", "cy-alias"})

        exporter = OcdExportService(self.context)
        protos = {name: {} for name in ("tCOMd_RelObj", "tCOMd_Relation", "tCOMd_RelObjRel")}

        objects, relation_rows, links, property_bindings, value_bindings = exporter._relations(
            snapshot, 1, protos
        )

        self.assertEqual(len(objects), 1)
        self.assertEqual(len(relation_rows), 1)
        self.assertEqual(len(links), 1)
        self.assertEqual(objects[0]["com_RelObjID"], 40)
        self.assertEqual(objects[0]["com_RelObjName"], "B_Choice_Y")
        self.assertEqual(relation_rows[0]["com_RelationID"], 90)
        self.assertEqual(relation_rows[0]["com_RelationName"], "BA_Choice_Y")
        self.assertEqual(relation_rows[0]["com_RelationBody"], explicit.body)
        self.assertEqual(links[0]["com_RelObjTypeCode"], "1")
        self.assertEqual(links[0]["com_RelObjDomainCode"], "C")
        self.assertEqual(links[0]["com_RelationOrder"], 70)
        self.assertEqual(property_bindings, {"choice": 40})
        self.assertEqual(value_bindings, {"cy": 40, "cy-alias": 40})

        restored = snapshot_from_dict(snapshot_to_dict(snapshot))
        self.assertEqual(restored.relation_objects[0].property_ids, ["choice"])
        self.assertEqual(restored.relation_objects[0].value_ids, ["cy", "cy-alias"])


_REAL_MDB = os.environ.get("MK_REAL_OCD_MDB", "")


@unittest.skipUnless(_REAL_MDB, "Set MK_REAL_OCD_MDB to a real OCD MDB")
class RealMdbRelationWorkflowTests(unittest.TestCase):
    def test_plateau_validity_relations_survive_rebuild_without_new_inferred_relations(self):
        context = ApplicationContext()
        data = context.mdb_reverse_engineering_service.read(_REAL_MDB)
        snapshot = context.mdb_reverse_engineering_service.import_snapshot(data)
        imported_validity = [
            (
                relation.name,
                relation.type_code,
                relation.domain,
                relation.body,
                relation.rel_obj_id,
                relation.relation_id,
                tuple(relation.value_ids),
            )
            for relation in snapshot.relation_objects
            if relation.name.startswith("B_")
            and relation.type_code == "1"
            and relation.domain == "C"
        ]
        self.assertTrue(imported_validity)
        self.assertFalse(snapshot.article_sets)

        rebuilt = context.engineering_relation_service.rebuild_relation_objects(snapshot)

        rebuilt_validity = [
            (
                relation.name,
                relation.type_code,
                relation.domain,
                relation.body,
                relation.rel_obj_id,
                relation.relation_id,
                tuple(relation.value_ids),
            )
            for relation in rebuilt
            if relation.name.startswith("B_")
            and relation.type_code == "1"
            and relation.domain == "C"
        ]
        self.assertEqual(rebuilt_validity, imported_validity)
        self.assertFalse(any(
            relation.name.startswith("B_") and not relation.rel_obj_id
            for relation in rebuilt
        ))

    def test_import_preserves_real_relation_ids_and_all_value_bindings(self):
        context = ApplicationContext()
        data = context.mdb_reverse_engineering_service.read(_REAL_MDB)
        snapshot = context.mdb_reverse_engineering_service.import_snapshot(data)
        expected_links = _valid_relation_links(data)
        imported_links = Counter(
            (
                _id(relation.rel_obj_id),
                _id(relation.relation_id),
                relation.type_code,
                relation.domain,
                str(relation.order),
            )
            for relation in snapshot.relation_objects
        )
        expected_values = {
            (_id(row.get("com_RelObjID")), _id(row.get("com_ValueID")))
            for row in data.rows("tCOMd_PropValue")
            if row.get("com_RelObjID") not in (None, "")
        }
        imported_values = {
            (_id(relation.rel_obj_id), _id(value_id.removeprefix("mdb:value:")))
            for relation in snapshot.relation_objects
            for value_id in relation.value_ids
        }

        self.assertTrue(any(obj_id != relation_id for obj_id, relation_id, *_ in expected_links))
        self.assertEqual(imported_links, expected_links)
        self.assertEqual(imported_values, expected_values)

    def test_export_round_trip_preserves_relation_ids_and_entity_bindings(self):
        context = ApplicationContext()
        source = Path(_REAL_MDB)
        source_data = context.mdb_reverse_engineering_service.read(source)
        snapshot = context.mdb_reverse_engineering_service.import_snapshot(source_data)

        class _PackageSchemaAdapter:
            def __init__(self, wrapped):
                self.wrapped = wrapped

            def __getattr__(self, name):
                return getattr(self.wrapped, name)

            def read_table(self, path, sql):
                if "SELECT com_PackageID, com_ComGroupID, com_ManufacturerID FROM tCOMd_Package" in sql:
                    rows = self.wrapped.read_table(path, "SELECT * FROM [tCOMd_Package]")
                    return [{**rows[0], "com_ManufacturerID": None}] if rows else []
                return self.wrapped.read_table(path, sql)

        context._services[MDBService] = _PackageSchemaAdapter(context.mdb_service)
        with patch.dict(ocd_export_module._TEMPLATES, {"tables": source}):
            with tempfile.TemporaryDirectory() as temp_dir:
                destination = Path(temp_dir) / "roundtrip.mdb"
                result = context.ocd_export_service.export(
                    snapshot, destination, template_kind="tables"
                )
                self.assertTrue(result.ok, result.error)
                output = context.mdb_reverse_engineering_service.read(
                    destination,
                    tables=[
                        "tCOMd_RelObj", "tCOMd_Relation", "tCOMd_RelObjRel",
                        "tCOMd_Property", "tCOMd_PropValue",
                    ],
                )

        self.assertEqual(_valid_relation_links(source_data), _valid_relation_links(output))
        self.assertEqual(
            _semantic_bindings(source_data, "tCOMd_Property"),
            _semantic_bindings(output, "tCOMd_Property"),
        )
        self.assertEqual(
            _semantic_bindings(source_data, "tCOMd_PropValue"),
            _semantic_bindings(output, "tCOMd_PropValue"),
        )


if __name__ == "__main__":
    unittest.main()