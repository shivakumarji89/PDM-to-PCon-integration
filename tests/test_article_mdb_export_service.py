from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

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
            codes = ["BASE"]
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


def make_snapshot():
    article = Article(id="a1", code="BASE.01", product_id="p1")
    member = SimpleNamespace(
        id="m1", article_id="a1", reduced_article="BASE",
        relation_object="P_BASE", code_scheme="BASE",
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


if __name__ == "__main__":
    unittest.main()
