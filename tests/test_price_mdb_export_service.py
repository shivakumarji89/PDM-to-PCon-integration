from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from models.price_list import PriceList
from models.price_record import PriceRecord
from models.snapshot import Snapshot
from services.price_mdb_export_service import PriceMdbExportService


class _FakeMDB:
    def __init__(self):
        self.ops = []
        self.rows = {
            "SELECT com_ArticleID, com_ArticleCode FROM tCOMd_Article": [
                {"com_ArticleID": 4, "com_ArticleCode": "A1"},
            ],
            "SELECT TOP 1 com_PackageID FROM tCOMd_Package": [
                {"com_PackageID": 1},
            ],
            "SELECT com_PriceListID, com_PriceListLabel, sys_ISOCurrencyCode, com_PriceValidFrom, com_PriceValidTo FROM tCOMd_PriceList2": [
                {"com_PriceListID": 7, "com_PriceListLabel": "GBP_2026",
                 "sys_ISOCurrencyCode": "GBP", "com_PriceValidFrom": "2026-01-01",
                 "com_PriceValidTo": "9999-12-31"},
            ],
            "SELECT com_PriceID, com_ArticleID, com_PriceListID, com_VariantCondition, com_PriceLevelCode, sys_ISOCurrencyCode, com_PriceValue FROM tCOMd_Price": [],
            "SELECT com_GlobalPriceID, com_PackageID, com_PriceListID, com_VariantCondition, com_PriceLevelCode, sys_ISOCurrencyCode, com_PriceValue FROM tCOMd_GlobalPrice": [],
        }

    @staticmethod
    def is_available():
        return True

    def read_table(self, _mdb, sql):
        if sql.startswith("SELECT TOP 1 * FROM"):
            return []
        return self.rows.get(sql, [])

    def execute_batch(self, _mdb, ops, transaction=False):
        self.ops = ops
        self.transaction = transaction
        return SimpleNamespace(ok=True, first_error=lambda: None)


class PriceMdbExportServiceTests(unittest.TestCase):
    def test_export_only_inserts_and_skips_existing_identity(self):
        fake_mdb = _FakeMDB()
        context = SimpleNamespace(mdb_service=fake_mdb)
        snapshot = Snapshot()
        snapshot.price_lists = [
            PriceList(id="gbp_2026", label="GBP_2026", currency="GBP",
                      date_from="20260101", date_to="99991231")
        ]
        snapshot.price_records = [
            PriceRecord(article_code="A1", value=125.0, currency="GBP",
                        valid_from="2026-01-01", valid_to=""),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            mdb_path = Path(tmp) / "existing.mdb"
            mdb_path.touch()
            result = PriceMdbExportService(context).export(snapshot, mdb_path)

        self.assertTrue(result["ok"])
        self.assertEqual(result["inserted_prices"], 1)
        self.assertTrue(fake_mdb.transaction)
        self.assertTrue(fake_mdb.ops)
        self.assertTrue(all(op["op"] == "insert" for op in fake_mdb.ops))
        self.assertEqual(fake_mdb.ops[0]["table"], "tCOMd_Price")
        self.assertEqual(fake_mdb.ops[0]["rows"][0]["com_ArticleID"], 4)
        self.assertEqual(fake_mdb.ops[0]["rows"][0]["com_PriceListID"], 7)


    def test_existing_price_identity_is_skipped_without_update_or_delete(self):
        fake_mdb = _FakeMDB()
        fake_mdb.rows[
            "SELECT com_PriceID, com_ArticleID, com_PriceListID, com_VariantCondition, com_PriceLevelCode, sys_ISOCurrencyCode, com_PriceValue FROM tCOMd_Price"
        ] = [
            {"com_PriceID": 3, "com_ArticleID": 4, "com_PriceListID": 7,
             "com_VariantCondition": "", "com_PriceLevelCode": "B",
             "sys_ISOCurrencyCode": "GBP", "com_PriceValue": 125.0},
        ]
        context = SimpleNamespace(mdb_service=fake_mdb)
        snapshot = Snapshot()
        snapshot.price_lists = [
            PriceList(id="gbp_2026", label="GBP_2026", currency="GBP",
                      date_from="20260101", date_to="99991231")
        ]
        snapshot.price_records = [
            PriceRecord(article_code="A1", value=130.0, currency="GBP",
                        valid_from="2026-01-01", valid_to=""),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            mdb_path = Path(tmp) / "existing.mdb"
            mdb_path.touch()
            result = PriceMdbExportService(context).export(snapshot, mdb_path)

        self.assertTrue(result["ok"])
        self.assertEqual(result["inserted_prices"], 0)
        self.assertEqual(result["updated_prices"], 1)
        self.assertEqual(fake_mdb.ops[0]["op"], "update")
        self.assertEqual(fake_mdb.ops[0]["set"], {"com_PriceValue": 130.0})
        self.assertEqual(fake_mdb.ops[0]["where"], {"com_PriceID": 3})

    def test_export_fails_clearly_when_existing_price_is_zero(self):
        fake_mdb = _FakeMDB()
        fake_mdb.rows[
            "SELECT com_PriceID, com_ArticleID, com_PriceListID, com_VariantCondition, com_PriceLevelCode, sys_ISOCurrencyCode, com_PriceValue FROM tCOMd_Price"
        ] = [
            {"com_PriceID": 3, "com_ArticleID": 4, "com_PriceListID": 7,
             "com_VariantCondition": "", "com_PriceLevelCode": "B",
             "sys_ISOCurrencyCode": "GBP", "com_PriceValue": 0.0},
        ]
        context = SimpleNamespace(mdb_service=fake_mdb)
        snapshot = Snapshot()
        snapshot.price_lists = [
            PriceList(id="gbp_2026", label="GBP_2026", currency="GBP",
                      date_from="20260101", date_to="99991231")
        ]
        snapshot.price_records = [
            PriceRecord(article_code="A1", value=125.0, currency="GBP",
                        valid_from="2026-01-01", valid_to=""),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            mdb_path = Path(tmp) / "existing.mdb"
            mdb_path.touch()
            result = PriceMdbExportService(context).export(snapshot, mdb_path)

        self.assertTrue(result["ok"])
        self.assertEqual(result["updated_prices"], 1)
        self.assertEqual(fake_mdb.ops[0]["op"], "update")
        self.assertEqual(fake_mdb.ops[0]["set"], {"com_PriceValue": 125.0})
        self.assertEqual(fake_mdb.ops[0]["where"], {"com_PriceID": 3})

    def test_export_does_not_touch_mdb_when_no_prices_exist(self):
        fake_mdb = _FakeMDB()
        context = SimpleNamespace(mdb_service=fake_mdb)
        with tempfile.TemporaryDirectory() as tmp:
            mdb_path = Path(tmp) / "existing.mdb"
            mdb_path.touch()
            result = PriceMdbExportService(context).export(Snapshot(), mdb_path)
        self.assertFalse(result["ok"])
        self.assertEqual(fake_mdb.ops, [])


if __name__ == "__main__":
    unittest.main()
