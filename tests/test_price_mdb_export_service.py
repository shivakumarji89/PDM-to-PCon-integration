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


_PRICE_SQL = ("SELECT com_PriceID, com_ArticleID, com_PriceListID, com_VariantCondition, "
              "com_PriceLevelCode, sys_ISOCurrencyCode, com_PriceValue FROM tCOMd_Price")
_GLOBAL_SQL = ("SELECT com_GlobalPriceID, com_PackageID, com_PriceListID, com_VariantCondition, "
               "com_PriceLevelCode, sys_ISOCurrencyCode, com_PriceValue FROM tCOMd_GlobalPrice")
_LISTS_SQL = ("SELECT com_PriceListID, com_PriceListLabel, sys_ISOCurrencyCode, "
              "com_PriceValidFrom, com_PriceValidTo FROM tCOMd_PriceList2")
_LINKED_SQL = "SELECT DISTINCT com_PriceListID FROM tCOMd_DistributionRegionPriceList"


class _RecordingMDB(_FakeMDB):
    """Fake bridge that reports per-op results like the real one."""

    def __init__(self, lists, prices=(), globals_=(), linked=(), batch_ok=True, no_match=False):
        super().__init__()
        self.rows[_LISTS_SQL] = list(lists)
        self.rows[_PRICE_SQL] = list(prices)
        self.rows[_GLOBAL_SQL] = list(globals_)
        self.rows[_LINKED_SQL] = [{"com_PriceListID": i} for i in linked]
        self.batch_ok = batch_ok
        self.no_match = no_match

    def execute_batch(self, _mdb, ops, transaction=False):
        self.ops = ops
        self.transaction = transaction
        results = [
            SimpleNamespace(
                ok=self.batch_ok, error=None,
                inserted=len(op["rows"]) if op["op"] == "insert" else 0,
                updated=0 if self.no_match else (1 if op["op"] == "update" else 0),
            )
            for op in ops
        ]
        return SimpleNamespace(
            ok=self.batch_ok, results=results,
            first_error=lambda: None if self.batch_ok else "update(boom)",
        )


def _plist(pid, label, ccy, start="2026-01-01", end="9999-12-31"):
    return {"com_PriceListID": pid, "com_PriceListLabel": label, "sys_ISOCurrencyCode": ccy,
            "com_PriceValidFrom": start, "com_PriceValidTo": end}


def _export(mdb, records, lists=()):
    snapshot = Snapshot()
    snapshot.price_lists = list(lists)
    snapshot.price_records = list(records)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "existing.mdb"
        path.touch()
        return PriceMdbExportService(SimpleNamespace(mdb_service=mdb)).export(snapshot, path)


def _eur_gbp_lists():
    return [_plist(21, "EURO_2026_2", "EUR"), _plist(22, "GBP_2026_2", "GBP")]


def _rec(value, ccy, **kw):
    kw.setdefault("article_code", "A1")
    return PriceRecord(value=value, currency=ccy, valid_from="2026-10-16", valid_to="", **kw)


class PriceMdbExportRealWorldRegressionTests(unittest.TestCase):
    """Behaviours verified against the real OCD MDB (see commit message)."""

    def test_snapshot_label_with_space_maps_to_existing_linked_list_not_a_new_one(self):
        # "EURO 2026_2" (space) used to miss "EURO_2026_2" and create an orphan list.
        mdb = _RecordingMDB(_eur_gbp_lists(), linked=[21, 22])
        result = _export(mdb, [_rec(50.0, "EUR")],
                         [PriceList(id="EURO 2026_2", label="EURO 2026_2", currency="EUR",
                                    date_from="20261016", date_to="99991231")])
        self.assertEqual(result["inserted_price_lists"], 0)
        self.assertEqual(result["inserted_prices"], 1)
        self.assertEqual(mdb.ops[0]["rows"][0]["com_PriceListID"], 21)

    def test_linked_list_preferred_over_orphan_lookalike(self):
        lists = _eur_gbp_lists() + [_plist(24, "EURO 2026_2", "EUR", "2026-10-16")]
        mdb = _RecordingMDB(lists, linked=[21, 22])
        _export(mdb, [_rec(50.0, "EUR")],
                [PriceList(id="EURO 2026_2", label="EURO 2026_2", currency="EUR",
                           date_from="20261016", date_to="99991231")])
        self.assertEqual(mdb.ops[0]["rows"][0]["com_PriceListID"], 21)

    def test_existing_eur_price_updated_and_gbp_goes_to_gbp_list(self):
        prices = [
            {"com_PriceID": 1, "com_ArticleID": 4, "com_PriceListID": 21, "com_VariantCondition": "",
             "com_PriceLevelCode": "B", "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 10.0},
            {"com_PriceID": 2, "com_ArticleID": 4, "com_PriceListID": 22, "com_VariantCondition": "",
             "com_PriceLevelCode": "B", "sys_ISOCurrencyCode": "GBP", "com_PriceValue": 0.0},
            {"com_PriceID": 3, "com_ArticleID": 9, "com_PriceListID": 21, "com_VariantCondition": "",
             "com_PriceLevelCode": "B", "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 77.0},
        ]
        mdb = _RecordingMDB(_eur_gbp_lists(), prices=prices, linked=[21, 22])
        result = _export(mdb, [_rec(12.5, "EUR"), _rec(11.0, "GBP")])
        self.assertEqual(result["updated_prices"], 2)
        self.assertEqual(result["inserted_prices"], 0)
        self.assertEqual({op["where"]["com_PriceID"]: op["set"]["com_PriceValue"] for op in mdb.ops},
                         {1: 12.5, 2: 11.0})  # EUR -> EUR row, zero GBP row corrected, row 3 untouched
        self.assertTrue(all(set(op["set"]) == {"com_PriceValue"} for op in mdb.ops))

    def test_global_price_matches_x_level_row_and_new_global_is_x_level(self):
        globals_ = [{"com_GlobalPriceID": 100, "com_PackageID": 1, "com_PriceListID": 21,
                     "com_VariantCondition": "GESNNS.1", "com_PriceLevelCode": "X",
                     "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 0.0}]
        mdb = _RecordingMDB(_eur_gbp_lists(), globals_=globals_, linked=[21, 22])
        records = [
            PriceRecord(is_global=True, variant_condition="GESNNS.1", level="", value=284.0,
                        currency="EUR", valid_from="2026-10-16"),
            PriceRecord(is_global=True, variant_condition="GESNNS.2", level="", value=296.0,
                        currency="EUR", valid_from="2026-10-16"),
        ]
        result = _export(mdb, records)
        self.assertEqual((result["updated_global_prices"], result["inserted_global_prices"]), (1, 1))
        update = next(op for op in mdb.ops if op["op"] == "update")
        self.assertEqual(update["where"], {"com_GlobalPriceID": 100})
        self.assertEqual(update["set"], {"com_PriceValue": 284.0})
        insert = next(op for op in mdb.ops if op["op"] == "insert")
        self.assertEqual(insert["rows"][0]["com_PriceLevelCode"], "X")

    def test_duplicate_matching_rows_are_all_corrected_deterministically(self):
        dup = {"com_ArticleID": 4, "com_PriceListID": 21, "com_VariantCondition": "",
               "com_PriceLevelCode": "B", "sys_ISOCurrencyCode": "EUR"}
        prices = [{"com_PriceID": 1, "com_PriceValue": 0.0, **dup},
                  {"com_PriceID": 2, "com_PriceValue": 9.0, **dup},   # already correct: left alone
                  {"com_PriceID": 3, "com_PriceValue": 1.0, **dup}]
        mdb = _RecordingMDB(_eur_gbp_lists(), prices=prices, linked=[21, 22])
        result = _export(mdb, [_rec(9.0, "EUR")])
        self.assertEqual([op["where"]["com_PriceID"] for op in mdb.ops], [1, 3])
        self.assertEqual(result["updated_prices"], 2)
        self.assertEqual(result["inserted_prices"], 0)

    def test_ambiguous_price_list_is_reported_not_guessed(self):
        lists = [_plist(5, "EURO_A", "EUR"), _plist(6, "EURO_B", "EUR")]
        mdb = _RecordingMDB(lists, linked=[5, 6])
        result = _export(mdb, [_rec(9.0, "EUR")])  # no snapshot list names either
        self.assertEqual(mdb.ops, [])
        self.assertEqual(result["skipped_ambiguous"], 1)
        self.assertEqual(result["skipped_unmapped"], 1)

    def test_failed_batch_reports_nothing_written(self):
        prices = [{"com_PriceID": 1, "com_ArticleID": 4, "com_PriceListID": 21, "com_VariantCondition": "",
                   "com_PriceLevelCode": "B", "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 1.0}]
        mdb = _RecordingMDB(_eur_gbp_lists(), prices=prices, linked=[21, 22], batch_ok=False)
        result = _export(mdb, [_rec(9.0, "EUR"), _rec(3.0, "GBP")])
        self.assertTrue(mdb.transaction)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "update(boom)")
        self.assertEqual((result["updated_prices"], result["inserted_prices"]), (0, 0))
        self.assertEqual(result["failed"], 2)

    def test_counts_come_from_executed_writes_not_plans(self):
        prices = [{"com_PriceID": 1, "com_ArticleID": 4, "com_PriceListID": 21, "com_VariantCondition": "",
                   "com_PriceLevelCode": "B", "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 1.0}]
        mdb = _RecordingMDB(_eur_gbp_lists(), prices=prices, linked=[21, 22], no_match=True)
        result = _export(mdb, [_rec(9.0, "EUR")])
        self.assertTrue(result["ok"])
        self.assertEqual(result["updated_prices"], 0)  # planned 1, the engine changed 0 rows
        self.assertEqual(result["failed"], 1)
        self.assertTrue(result["warnings"])

    def test_repeating_the_export_neither_inserts_nor_updates(self):
        row = {"com_PriceID": 1, "com_ArticleID": 4, "com_PriceListID": 21, "com_VariantCondition": "",
               "com_PriceLevelCode": "B", "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 9.0}
        mdb = _RecordingMDB(_eur_gbp_lists(), prices=[row], linked=[21, 22])
        result = _export(mdb, [_rec(9.0, "EUR"), _rec(9.0, "EUR")])  # also a repeated identity
        self.assertEqual(mdb.ops, [])
        self.assertEqual(result["skipped_existing"], 2)
        self.assertEqual((result["updated_prices"], result["inserted_prices"]), (0, 0))

    def test_new_price_list_without_region_link_is_flagged(self):
        mdb = _RecordingMDB([_plist(7, "NOPRICE", "EUR")], linked=[7])
        result = _export(mdb, [_rec(9.0, "EUR")],
                         [PriceList(id="EURO_2027", label="EURO_2027", currency="EUR",
                                    date_from="20260101", date_to="99991231")])
        self.assertEqual(result["inserted_price_lists"], 1)
        self.assertTrue(any("not linked" in w for w in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
