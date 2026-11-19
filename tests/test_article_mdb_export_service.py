from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from models.mdb_export_session import MdbExportSession
from models.snapshot import Snapshot
from models.article import Article
from services.article_mdb_export_service import ArticleMdbExportService


class FakeMDB:
    def __init__(self):
        self.rows = {
            "article_proto": [{
                "com_ArticleID": None, "com_ArticleCode": None, "com_ArticleTypeCode": None,
                "com_PackageID": None, "com_ComGroupID": None, "com_CodeSchemeID": None,
                "com_RelObjID": None, "com_ShortTextID": None, "com_LongTextID": None,
                "com_Discountable": None, "com_OrderUnitCode": None, "com_StatusInfoID": None,
            }],
            "articles": [],
            "package": [{"com_PackageID": 10, "com_ComGroupID": 20}],
            "group": [{"com_ComGroupID": 20}],
            "schemes": [{"com_CodeSchemeID": 30, "com_CodeSchemeName": "BASE", "com_PackageID": 10}],
            "relobjs": [{"com_RelObjID": 40, "com_RelObjName": "P_BASE", "com_PackageID": 10}],
            "texts": [],
            "max_article": [{"max_id": 4}],
        }
        self.ops = []
        self.transaction = False

    @staticmethod
    def is_available():
        return True

    def read_tables(self, _mdb, queries):
        return {key: self.rows.get(key, []) for key in queries}

    def read_table(self, _mdb, sql):
        if "WHERE com_ArticleCode IN" in sql:
            codes = re.findall(r"'([^']+)'", sql)
            return [r for r in self.rows["articles"] if r.get("com_ArticleCode") in codes]
        return []

    def execute_batch(self, _mdb, ops, transaction=False):
        self.ops = ops
        self.transaction = transaction
        for op in ops:
            if op["op"] == "insert" and op["table"] == "tCOMd_Article":
                self.rows["articles"].extend(op["rows"])
            elif op["op"] == "update" and op["table"] == "tCOMd_Article":
                for row in self.rows["articles"]:
                    if row.get("com_ArticleID") == op["where"]["com_ArticleID"]:
                        row.update(op["set"])
        return SimpleNamespace(ok=True, first_error=lambda: None)


def make_snapshot(code="BASE", relation="P_BASE", scheme=None):
    article = Article(id="a1", code=f"{code}.01", product_id="p1")
    member = SimpleNamespace(
        id="m1", article_id="a1", reduced_article=code,
        relation_object=relation, code_scheme=scheme or code,
        short_description="", long_description="",
    )
    family = SimpleNamespace(id="f1", name="Family", members=[member])
    snapshot = Snapshot(product=SimpleNamespace(id="p1"), articles=[article])
    snapshot.engineering.families = [family]
    return snapshot


class ArticleMdbExportServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeMDB()
        self.service = ArticleMdbExportService(SimpleNamespace(mdb_service=self.db))
        self.snapshot = make_snapshot()
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "target.mdb"
        self.path.touch()

    def tearDown(self):
        self.temp.cleanup()

    def test_dry_run_does_not_write(self):
        result = self.service.export(self.snapshot, self.path, dry_run=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(self.db.ops, [])

    def test_insert_uses_destination_ids_and_transaction(self):
        result = self.service.export(self.snapshot, self.path)
        self.assertTrue(result["ok"], result)
        self.assertTrue(self.db.transaction)
        op = next(op for op in self.db.ops if op["op"] == "insert")
        row = op["rows"][0]
        self.assertEqual(row["com_ArticleID"], 5)
        self.assertEqual(row["com_PackageID"], 10)
        self.assertEqual(row["com_ComGroupID"], 20)
        self.assertEqual(row["com_CodeSchemeID"], 30)
        self.assertEqual(row["com_RelObjID"], 40)
        self.assertIsNone(row["com_ShortTextID"])
        self.assertEqual(result["verified"], 1)

    def test_existing_article_id_is_preserved(self):
        self.db.rows["articles"] = [{
            "com_ArticleID": 91, "com_ArticleCode": "BASE",
            "com_ArticleTypeCode": "C", "com_PackageID": 10, "com_ComGroupID": 20,
            "com_CodeSchemeID": 30, "com_RelObjID": 40, "com_ShortTextID": None,
            "com_LongTextID": None, "com_Discountable": True, "com_OrderUnitCode": "C62",
        }]
        result = self.service.export(self.snapshot, self.path)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["unchanged"], 1)
        self.assertEqual(self.db.ops, [])

    # -- relation-object link policy (attached production workspaces) -----------------------------

    def _attached(self, attached=True):
        return MdbExportSession(
            product_key="id:p1", mdb_path=str(self.path), package_id=10, comgroup_id=20,
            attached_existing=attached, prototypes={},
        )

    def _seed(self, code, existing_relobj, relobjs, relation_name_for_existing=None):
        """A production-like MDB: ``code`` is bound to ``existing_relobj`` (None = missing link)."""
        self.db.rows["relobjs"] = [
            {"com_RelObjID": rid, "com_RelObjName": name, "com_PackageID": 10} for rid, name in relobjs]
        self.db.rows["schemes"] = [{"com_CodeSchemeID": 30, "com_CodeSchemeName": code, "com_PackageID": 10}]
        if relation_name_for_existing:
            self.db.rows["relations"] = [{"com_RelationID": 7, "com_RelationName": relation_name_for_existing}]
            self.db.rows["relobj_links"] = [{
                "com_RelObjID": existing_relobj, "com_RelationID": 7, "com_RelObjTypeCode": "3",
                "com_RelObjDomainCode": "P", "com_RelationOrder": 100}]
        self.db.rows["articles"] = [{
            "com_ArticleID": 20281, "com_ArticleCode": code, "com_ArticleTypeCode": "C", "com_PackageID": 10,
            "com_ComGroupID": 20, "com_CodeSchemeID": 30, "com_RelObjID": existing_relobj,
            "com_ShortTextID": None, "com_LongTextID": None, "com_Discountable": True, "com_OrderUnitCode": "C62",
        }]

    def _article_row(self):
        return next(r for r in self.db.rows["articles"] if r["com_ArticleID"] == 20281)

    def test_lino_existing_price_relation_is_preserved_over_incoming_object(self):
        """Lino MI1E3: existing P_PRICING_CHAIR must survive the incoming P_MI1E3 (an object with no relation)."""
        self._seed("MI1E3", 11588, [(11588, "P_PRICING_CHAIR"), (11222, "P_MI1E3")], "PA_PRICING_CHAIR")
        snapshot = make_snapshot("MI1E3", "P_MI1E3")
        session = self._attached()

        preview = self.service.export(snapshot, self.path, dry_run=True, session=session)
        self.assertTrue(preview["ok"], preview)
        self.assertEqual((preview["updated"], preview["inserted"]), (0, 0))
        self.assertEqual(preview["links_preserved"], 1)
        entry = preview["conflicts"][0]
        self.assertEqual(entry["action"], "preserved")
        self.assertEqual((entry["existing"]["id"], entry["existing"]["name"]), ("11588", "P_PRICING_CHAIR"))
        self.assertEqual((entry["incoming"]["id"], entry["incoming"]["name"]), ("11222", "P_MI1E3"))
        self.assertEqual(entry["existing"]["relations"][0]["relation"], "PA_PRICING_CHAIR")
        self.assertEqual(entry["existing"]["relations"][0]["domain"], "P")
        self.assertEqual(entry["incoming"]["relations"], [])
        message = next(w for w in preview["warnings"] if "PRESERVED" in w)
        self.assertIn("P_PRICING_CHAIR (id 11588", message)
        self.assertIn("P_MI1E3 (id 11222; no relation attached)", message)

        result = self.service.export(snapshot, self.path, session=session)
        self.assertTrue(result["ok"], result)
        self.assertEqual(self.db.ops, [])  # nothing was written at all
        self.assertEqual(self._article_row()["com_RelObjID"], 11588)

    def test_dalby_shared_series_relation_is_preserved_over_generated_relation(self):
        self._seed("NODLE100", 19573, [(19573, "P_PRICING_DALBY"), (19541, "P_PRICING_NODLE100")], "PA_PRICING_DALBY")
        snapshot = make_snapshot("NODLE100", "P_PRICING_NODLE100")
        result = self.service.export(snapshot, self.path, session=self._attached())
        self.assertTrue(result["ok"], result)
        self.assertEqual(self._article_row()["com_RelObjID"], 19573)
        self.assertEqual(self.db.ops, [])
        entry = result["conflicts"][0]
        self.assertEqual((entry["existing"]["name"], entry["incoming"]["name"]),
                         ("P_PRICING_DALBY", "P_PRICING_NODLE100"))

    def test_preserved_link_is_idempotent_across_repeated_exports(self):
        self._seed("MI1E3", 11588, [(11588, "P_PRICING_CHAIR"), (11222, "P_MI1E3")], "PA_PRICING_CHAIR")
        snapshot, session = make_snapshot("MI1E3", "P_MI1E3"), self._attached()
        first = self.service.export(snapshot, self.path, session=session)
        before = [dict(r) for r in self.db.rows["articles"]]
        for _ in range(3):
            again = self.service.export(snapshot, self.path, session=session)
            self.assertTrue(again["ok"], again)
            self.assertEqual((again["inserted"], again["updated"]), (0, 0))
        self.assertEqual(self.db.rows["articles"], before)
        self.assertEqual(self.db.ops, [])
        self.assertEqual(first["links_preserved"], 1)

    def test_missing_link_is_created(self):
        self._seed("MI1E3", None, [(11222, "P_MI1E3")])
        result = self.service.export(make_snapshot("MI1E3", "P_MI1E3"), self.path, session=self._attached())
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["conflicts"], [])
        self.assertEqual(self._article_row()["com_RelObjID"], 11222)
        # and is stable afterwards
        again = self.service.export(make_snapshot("MI1E3", "P_MI1E3"), self.path, session=self._attached())
        self.assertEqual((again["updated"], again["inserted"]), (0, 0))

    def test_dangling_link_counts_as_missing_and_is_repaired(self):
        self._seed("MI1E3", 999999, [(11222, "P_MI1E3")])
        result = self.service.export(make_snapshot("MI1E3", "P_MI1E3"), self.path, session=self._attached())
        self.assertTrue(result["ok"], result)
        self.assertEqual(self._article_row()["com_RelObjID"], 11222)

    def test_new_article_in_an_attached_workspace_gets_its_generated_link(self):
        self.db.rows["relobjs"] = [{"com_RelObjID": 11222, "com_RelObjName": "P_NEWCODE", "com_PackageID": 10}]
        result = self.service.export(make_snapshot("NEWCODE", "P_NEWCODE"), self.path, session=self._attached())
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(self.db.rows["articles"][0]["com_RelObjID"], 11222)

    def test_replacement_requires_the_explicit_authorization_flag(self):
        self._seed("MI1E3", 11588, [(11588, "P_PRICING_CHAIR"), (11222, "P_MI1E3")], "PA_PRICING_CHAIR")
        snapshot = make_snapshot("MI1E3", "P_MI1E3")
        result = self.service.export(snapshot, self.path, session=self._attached(), replace_existing_links=True)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["conflicts"][0]["action"], "replaced")
        self.assertEqual(self._article_row()["com_RelObjID"], 11222)

    def test_template_initialized_session_keeps_the_incoming_link(self):
        """Rows in a template-initialized MDB were all written by this application: incoming wins, visibly."""
        self._seed("MI1E3", 11588, [(11588, "P_PRICING_CHAIR"), (11222, "P_MI1E3")], "PA_PRICING_CHAIR")
        result = self.service.export(make_snapshot("MI1E3", "P_MI1E3"), self.path, session=self._attached(False))
        self.assertTrue(result["ok"], result)
        self.assertEqual(self._article_row()["com_RelObjID"], 11222)
        self.assertEqual(result["conflicts"][0]["action"], "replaced")
        self.assertTrue(any("REPLACED" in w for w in result["warnings"]))

    def test_a_minimal_schema_without_relation_columns_still_exports_and_preserves(self):
        """The relation info only describes a conflict; a schema lacking it (real-ACE stand-in templates did)
        must neither fail the export nor change the preservation decision."""
        class NoRelationInfo(FakeMDB):
            def read_tables(self, mdb, queries):
                if "relobj_links" in queries:
                    raise RuntimeError("No value given for one or more required parameters.")
                return super().read_tables(mdb, queries)

        self.db = NoRelationInfo()
        self.service = ArticleMdbExportService(SimpleNamespace(mdb_service=self.db))
        self._seed("MI1E3", 11588, [(11588, "P_PRICING_CHAIR"), (11222, "P_MI1E3")], "PA_PRICING_CHAIR")
        result = self.service.export(make_snapshot("MI1E3", "P_MI1E3"), self.path, session=self._attached())
        self.assertTrue(result["ok"], result)
        self.assertEqual(self._article_row()["com_RelObjID"], 11588)
        entry = result["conflicts"][0]
        self.assertEqual((entry["action"], entry["existing"]["name"], entry["incoming"]["name"]),
                         ("preserved", "P_PRICING_CHAIR", "P_MI1E3"))
        self.assertEqual(entry["existing"]["relations"], [])  # description is reduced, decision is not

    def test_existing_code_scheme_link_is_preserved_in_attached_mode(self):
        """A clone-on-write assignment must not be reverted by re-exporting Articles."""
        self._seed("NODLE100", 40, [(40, "P_NODLE100")])
        self.db.rows["schemes"] = [
            {"com_CodeSchemeID": 30, "com_CodeSchemeName": "NODLE100", "com_PackageID": 10},
            {"com_CodeSchemeID": 31, "com_CodeSchemeName": "NODLE100_CS12345678", "com_PackageID": 10},
        ]
        self._article_row()["com_CodeSchemeID"] = 31
        result = self.service.export(make_snapshot("NODLE100", "P_NODLE100"), self.path, session=self._attached())
        self.assertTrue(result["ok"], result)
        self.assertEqual(self._article_row()["com_CodeSchemeID"], 31)
        self.assertEqual(self.db.ops, [])

    def test_unchanged_links_produce_no_rebinding_warning(self):
        self.db.rows["articles"] = [{
            "com_ArticleID": 91, "com_ArticleCode": "BASE",
            "com_ArticleTypeCode": "C", "com_PackageID": 10, "com_ComGroupID": 20,
            "com_CodeSchemeID": 30, "com_RelObjID": 40, "com_ShortTextID": None,
            "com_LongTextID": None, "com_Discountable": True, "com_OrderUnitCode": "C62",
        }]
        result = self.service.export(self.snapshot, self.path, dry_run=True)
        self.assertFalse([w for w in result["warnings"] if "will be changed" in w])


if __name__ == "__main__":
    unittest.main()
