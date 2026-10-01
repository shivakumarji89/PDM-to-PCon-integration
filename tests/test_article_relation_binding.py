"""Article / ArticleClass -> RelationObject binding (tCOMd_Article / tCOMd_ArticleClass
.com_RelObjID): import, MDB export, XOCD export, sharing and conflicts."""

import os
import tempfile
import unittest
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from core.export_readiness import ERROR, resolve_entity_bindings, scan_snapshot
from models.engineering_class import EngineeringClass
from models.relation_object import RelationObject
from models.snapshot import Snapshot
from services.mdb_reverse_engineering_service import (
    MdbPackageData,
    MdbReverseEngineeringService,
    MdbTableData,
)
from services.ocd_export_service import OcdExportService
from services.pricing_relation_service import PricingRelationResult, PricingRelationService
from services.snapshot_serialization import relation_object_from_dict, relation_object_to_dict
from services.xocd_export_service import XocdExportService

_PROTOS = {"tCOMd_RelObj": {}, "tCOMd_Relation": {}, "tCOMd_RelObjRel": {}}


class _Context:
    class _RelationService:
        @staticmethod
        def ensure_relation_objects(snapshot):
            return snapshot.relation_objects

        @staticmethod
        def build_relation_objects(snapshot):
            return snapshot.relation_objects

    engineering_relation_service = _RelationService()


def _pricing():
    """Imported 'P_PRICING' container: a 3/P action plus a 4/C TABLE constraint
    (the real Always structure), bound to two articles."""
    common = dict(rel_obj_id="11935", article_codes=["NOALE18", "NOALE19"])
    return [
        RelationObject(name="P_PRICING_STOOL", type_code="3", domain="P", order=100,
                       body="$VARCOND = Number_Of_Fabrics", relation_id="564131",
                       relation_name="PA_PRICING_STOOL", **common),
        RelationObject(name="P_PRICING_STOOL", type_code="4", domain="C", order=110,
                       body="Restrictions: TABLE CHAIR_FABRIC ( A = A ).", relation_id="573511",
                       relation_name="BA_CHAIR_FABRIC", **common),
    ]


def _mdb_export(relations):
    service = OcdExportService(_Context())
    bindings = {}
    rows = service._relations(Snapshot(relation_objects=relations), 1, _PROTOS, bindings)
    return service, rows, bindings


class ArticleRelationBindingTests(unittest.TestCase):
    def test_container_with_two_relations_binds_both_articles_to_one_relobj(self):
        service, (obj_rows, rel_rows, links, _, _), bindings = _mdb_export(_pricing())

        self.assertEqual([r["com_RelObjID"] for r in obj_rows], [11935])
        self.assertEqual(
            [(l["com_RelObjID"], l["com_RelationID"], l["com_RelObjTypeCode"],
              l["com_RelObjDomainCode"], l["com_RelationOrder"]) for l in links],
            [(11935, 564131, "3", "P", 100), (11935, 573511, "4", "C", 110)],
        )
        self.assertEqual(bindings["article"], {"NOALE18": 11935, "NOALE19": 11935})
        self.assertEqual(bindings["conflicts"], [])

        rows, _ = service._articles(["NOALE1", "NOALE18", "NOALE19"], 1, 1, {}, {}, {}, {},
                                    bindings["article"])
        self.assertEqual([r["com_RelObjID"] for r in rows], [None, 11935, 11935])

    def test_articles_without_bindings_stay_unbound(self):
        service, _, bindings = _mdb_export([RelationObject(name="A_Code_X", type_code="3")])

        self.assertEqual(bindings["article"], {})
        rows, _ = service._articles(["A1"], 1, 1, {}, {}, {}, {}, bindings["article"])
        self.assertIsNone(rows[0]["com_RelObjID"])
        # The legacy call (Review build) is unchanged.
        rows, _ = service._articles(["A1"], 1, 1, {}, {}, {}, {})
        self.assertIsNone(rows[0]["com_RelObjID"])

    def test_article_class_binding_shared_by_several_article_classes(self):
        # Real Revive/Ratio_Rebuild shape: B_RECT_BRACKET on three (article, class) rows.
        rel = RelationObject(
            name="B_RECT_BRACKET", type_code="1", domain="C", order=100,
            body="(SPECIFIED Screen_D AND Screen_D NOT IN ('NN'))",
            rel_obj_id="6089", relation_id="26900",
            article_classes=[("RY3A", "Bracket"), ("RY3B", "Bracket")],
        )
        service, _, bindings = _mdb_export([rel])
        self.assertEqual(bindings["article_class"], {("RY3A", "Bracket"): 6089, ("RY3B", "Bracket"): 6089})

        classes = [EngineeringClass(id="c1", name="Bracket"), EngineeringClass(id="c2", name="Other")]
        rows = service._article_classes(
            ["RY3A", "RY3B"], {}, classes, {"RY3A": 1, "RY3B": 2}, {"c1": 10, "c2": 20}, {},
            bindings["article_class"],
        )
        self.assertEqual(
            [(r["com_ArticleID"], r["com_ClassID"], r["com_RelObjID"]) for r in rows],
            [(1, 10, 6089), (1, 20, None), (2, 10, 6089), (2, 20, None)],
        )

    def test_xocd_uses_the_same_logical_binding_as_the_mdb_export(self):
        xocd = XocdExportService(_Context())
        snapshot = Snapshot(relation_objects=_pricing() + [
            RelationObject(name="B_TYPE_6", type_code="1", domain="C", body="$ BAN NOT IN ('X')",
                           rel_obj_id="22760", relation_id="573513", relation_name="BA_TYPE_6",
                           article_classes=[("NOALE18", "Chair")]),
        ])
        bindings = {}
        obj_rows, rel_rows, _ = xocd._relations(snapshot, {"program": "PRG"}, bindings)

        # One RelObjID per container; container rows keep their own relation name.
        self.assertEqual(
            [row[1:] for row in obj_rows],
            [[1, 100, "PA_PRICING_STOOL", "3", "P"], [1, 110, "BA_CHAIR_FABRIC", "4", "C"],
             [2, 100, "B_TYPE_6", "1", "C"]],
        )
        self.assertEqual(sorted({row[1] for row in rel_rows}),
                         ["BA_CHAIR_FABRIC", "B_TYPE_6", "PA_PRICING_STOOL"])
        self.assertEqual(bindings["article"], {"NOALE18": 1, "NOALE19": 1})
        self.assertEqual(bindings["article_class"], {("NOALE18", "Chair"): 2})

        _, _, _, _, _ = OcdExportService(_Context())._relations(snapshot, 1, _PROTOS, mdb := {})
        # Same entities bound, each to the same logical container on both paths.
        self.assertEqual(mdb["article"], {"NOALE18": 11935, "NOALE19": 11935})
        self.assertEqual(mdb["article_class"], {("NOALE18", "Chair"): 22760})

        with patch.object(XocdExportService, "_base_codes", return_value=["NOALE18", "NOALE1"]):
            rows = xocd._articles(snapshot, {"program": "PRG", "program_id": "P"}, {}, bindings["article"])
        self.assertEqual([r[8] for r in rows], [1, 0])

    def test_shared_relation_body_is_written_once_in_xocd(self):
        a = _pricing()
        b = [replace(r, name="P_PRICING_CHAIR", rel_obj_id="11936", article_codes=["NOALE1"])
             for r in a]
        _, rel_rows, _ = XocdExportService(_Context())._relations(
            Snapshot(relation_objects=a + b), {"program": "PRG"}
        )
        self.assertEqual(Counter(row[1] for row in rel_rows)["BA_CHAIR_FABRIC"], 1)

    def test_conflicting_bindings_are_reported_not_resolved(self):
        rels = [
            RelationObject(name="PA_PRICING", type_code="3", domain="P", article_codes=["A1"]),
            RelationObject(name="PA_OTHER", type_code="3", domain="P", article_codes=["A1"]),
        ]
        articles, _, conflicts = resolve_entity_bindings(rels)

        self.assertEqual(articles, {})
        self.assertEqual(len(conflicts), 1)
        self.assertIn("PA_OTHER, PA_PRICING", conflicts[0][1])
        findings = [f for f in scan_snapshot(Snapshot(relation_objects=rels)) if f.field == "RelObjID"]
        self.assertEqual([(f.entity_id, f.severity) for f in findings], [("A1", ERROR)])

    def test_imported_binding_takes_precedence_over_generated(self):
        imported = _pricing()
        generated = RelationObject(name="PA_PRICING", type_code="3", domain="P",
                                   article_codes=["NOALE1", "NOALE18"])
        _, _, bindings = _mdb_export(imported + [generated])

        self.assertEqual(bindings["conflicts"], [])
        self.assertEqual(bindings["article"]["NOALE18"], 11935)  # imported wins
        self.assertNotEqual(bindings["article"]["NOALE1"], 11935)  # generated still binds the rest

    def test_rows_of_one_container_are_not_a_conflict(self):
        self.assertEqual(resolve_entity_bindings(_pricing())[2], [])

    def test_bindings_survive_snapshot_serialization(self):
        rel = RelationObject(name="B_X", article_codes=["A1", "A2"], article_classes=[("A1", "Cls")])
        again = relation_object_from_dict(relation_object_to_dict(rel))
        self.assertEqual((again.article_codes, again.article_classes), (["A1", "A2"], [("A1", "Cls")]))
        self.assertEqual(relation_object_from_dict({"name": "old"}).article_codes, [])

    def test_mdb_import_reads_article_and_article_class_bindings(self):
        def table(name, rows):
            return MdbTableData(name=name, rows=tuple(rows))

        data = MdbPackageData(path="x.mdb", package={"com_PackageID": 1}, tables={t.name: t for t in [
            table("tCOMd_Class", [{"com_ClassID": 7, "com_ClassName": "Chair"}]),
            table("tCOMd_Article", [
                {"com_ArticleID": 1, "com_ArticleCode": "NOALE18", "com_RelObjID": 11935},
                {"com_ArticleID": 2, "com_ArticleCode": "NOALE19", "com_RelObjID": 11935.0},
                {"com_ArticleID": 3, "com_ArticleCode": "NOALE1", "com_RelObjID": None},
            ]),
            table("tCOMd_ArticleClass", [
                {"com_ArticleID": 1, "com_ClassID": 7, "com_RelObjID": 22760},
                {"com_ArticleID": 3, "com_ClassID": 7, "com_RelObjID": None},
            ]),
            table("tCOMd_RelObj", [{"com_RelObjID": 11935, "com_RelObjName": "P_PRICING_STOOL"},
                                   {"com_RelObjID": 22760, "com_RelObjName": "B_TYPE_6"}]),
            table("tCOMd_Relation", [
                {"com_RelationID": 564131, "com_RelationName": "PA_PRICING_STOOL", "com_RelationBody": "$VARCOND = X"},
                {"com_RelationID": 573511, "com_RelationName": "BA_CHAIR_FABRIC", "com_RelationBody": "TABLE"},
                {"com_RelationID": 573513, "com_RelationName": "BA_TYPE_6", "com_RelationBody": "$ BAN"},
            ]),
            table("tCOMd_RelObjRel", [
                {"com_RelObjID": 11935, "com_RelationID": 564131, "com_RelObjTypeCode": "3",
                 "com_RelObjDomainCode": "P", "com_RelationOrder": 100},
                {"com_RelObjID": 11935, "com_RelationID": 573511, "com_RelObjTypeCode": "4",
                 "com_RelObjDomainCode": "C", "com_RelationOrder": 110},
                {"com_RelObjID": 22760, "com_RelationID": 573513, "com_RelObjTypeCode": "1",
                 "com_RelObjDomainCode": "C", "com_RelationOrder": 100},
            ]),
        ]})
        snapshot = MdbReverseEngineeringService(None).import_snapshot(data)

        got = [(r.name, r.relation_name, r.type_code, r.domain, r.order, r.article_codes, r.article_classes)
               for r in snapshot.relation_objects]
        self.assertEqual(got, [
            ("P_PRICING_STOOL", "PA_PRICING_STOOL", "3", "P", 100, ["NOALE18", "NOALE19"], []),
            ("P_PRICING_STOOL", "BA_CHAIR_FABRIC", "4", "C", 110, ["NOALE18", "NOALE19"], []),
            ("B_TYPE_6", "BA_TYPE_6", "1", "C", 100, [], [("NOALE18", "Chair")]),
        ])


class PricingArticleBindingTests(unittest.TestCase):
    def test_non_super_price_relation_binds_every_exported_base_article(self):
        class _Ctx:
            class xocd_export_service:
                @staticmethod
                def _base_codes(snapshot):
                    return ["AS1E", "AS4E"]

        snapshot = Snapshot()
        rel = PricingRelationService(_Ctx()).commit(
            snapshot, PricingRelationResult(relation_name="PA_PRICING", body="$VARCOND = Type")
        )

        self.assertEqual((rel.type_code, rel.domain, rel.article_codes), ("3", "P", ["AS1E", "AS4E"]))
        self.assertEqual(snapshot.relation_objects, [rel])


_REAL_MDB = os.environ.get("MK_REAL_OCD_MDB", "")


def _entity_containers(data, table: str) -> Counter:
    """(entity key, sorted relation names of its RelObj container) - id-free."""
    relation_name = {str(int(float(r["com_RelationID"]))): r.get("com_RelationName") or ""
                     for r in data.rows("tCOMd_Relation")}
    names_by_obj = defaultdict(list)
    for link in data.rows("tCOMd_RelObjRel"):
        names_by_obj[str(int(float(link["com_RelObjID"])))].append(
            relation_name.get(str(int(float(link["com_RelationID"]))), ""))
    codes = {str(r["com_ArticleID"]): r.get("com_ArticleCode") for r in data.rows("tCOMd_Article")}
    classes = {str(r["com_ClassID"]): r.get("com_ClassName") for r in data.rows("tCOMd_Class")}
    out = Counter()
    for row in data.rows(table):
        if row.get("com_RelObjID") in (None, "") or not float(row["com_RelObjID"]):
            continue  # NULL or 0 = no relation object
        obj = str(int(float(row["com_RelObjID"])))
        key = codes.get(str(row["com_ArticleID"]))
        if table == "tCOMd_ArticleClass":
            key = (key, classes.get(str(row["com_ClassID"])))
        out[(key, tuple(sorted(names_by_obj.get(obj, []))))] += 1
    return out


@unittest.skipUnless(_REAL_MDB, "Set MK_REAL_OCD_MDB to a real OCD MDB")
class RealMdbArticleBindingTests(unittest.TestCase):
    def test_article_and_article_class_bindings_survive_import_and_export(self):
        from core.application_context import ApplicationContext
        from services import ocd_export_service as ocd_export_module
        from services.mdb_service import MDBService

        context = ApplicationContext()
        source = Path(_REAL_MDB)
        source_data = context.mdb_reverse_engineering_service.read(source)
        snapshot = context.mdb_reverse_engineering_service.import_snapshot(source_data)

        expected_articles = _entity_containers(source_data, "tCOMd_Article")
        self.assertTrue(expected_articles, "real MDB has no Article-bound relation object")
        imported = {c for r in snapshot.relation_objects for c in r.article_codes}
        self.assertEqual(imported, {key for key, _ in expected_articles})

        # Export writes one tCOMd_Article per *base* article, which Class
        # Creation derives as engineering family members. A raw MDB import has
        # none, so stand in for that step: each imported article is its own base.
        from models.engineering_family import EngineeringFamily
        from models.member_article import MemberArticle
        snapshot.engineering.families = [EngineeringFamily(id="mdb", members=[
            MemberArticle(id=f"m{i}", article_id=a.id, reduced_article=a.code)
            for i, a in enumerate(snapshot.articles)
        ])]

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
                result = context.ocd_export_service.export(snapshot, destination, template_kind="tables")
                self.assertTrue(result.ok, result.error)
                output = context.mdb_reverse_engineering_service.read(destination, tables=[
                    "tCOMd_RelObj", "tCOMd_Relation", "tCOMd_RelObjRel",
                    "tCOMd_Article", "tCOMd_ArticleClass", "tCOMd_Class",
                ])

        exported = _entity_containers(output, "tCOMd_Article")
        # Every source Article binding is written, to a container with the same relations.
        self.assertEqual(+(expected_articles - exported), Counter())
        self.assertEqual(
            +(_entity_containers(source_data, "tCOMd_ArticleClass")
              - _entity_containers(output, "tCOMd_ArticleClass")),
            Counter(),
        )


if __name__ == "__main__":
    unittest.main()
