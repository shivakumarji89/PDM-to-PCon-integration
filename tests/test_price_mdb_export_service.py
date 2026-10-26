from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from models.price_list import PriceList
from models.price_record import PriceRecord
from models.snapshot import Snapshot
from services.price_mdb_export_service import PriceMdbExportService


_TEXT_COLS = ["com_TextID", "com_PackageID", "com_TextTypeCode", "com_TextName",
              "com_StatusInfoID", "sys_tmpID", "sys_tmpTag", "com_Text_1_de", "com_Text_1_en",
              "com_Text_1_fr", "com_Text_1_nl"]
_TEXT_PROTO = [{c: None for c in _TEXT_COLS}]


def _generated_batch(ops, seeds=None):
    """Model AutoNumber allocation and same-transaction foreign-key resolution."""
    seeds = seeds or {"tCOMd_Text": 501, "tCOMd_PriceList2": 1001,
                      "tCOMd_Price": 101, "tCOMd_GlobalPrice": 101}
    identities, resolved, generated = {}, [], []
    for op in ops:
        ids = {}
        if op["op"] == "insert" and "identity" in op:
            pk = op["identity"]
            rows = []
            for row in op["rows"]:
                token = row[pk]
                assert isinstance(token, str) and token.startswith("new:")
                assert token not in identities
                value = seeds[op["table"]] + len(ids) * 7
                identities[token] = ids[token] = value
                rows.append({col: (value if col == pk else identities[v["$ref"]]
                                   if isinstance(v, dict) and "$ref" in v else v)
                             for col, v in row.items()})
            op = {**op, "rows": rows}
        resolved.append(op)
        generated.append(ids)
    return resolved, generated


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
        sql = sql.replace(", com_TextID FROM tCOMd_GlobalPrice", " FROM tCOMd_GlobalPrice")
        if sql.startswith("SELECT TOP 1 * FROM [tCOMd_Text]"):
            return _TEXT_PROTO
        if sql.startswith("SELECT MAX(com_TextID)"):
            return [{"max_id": 500}]
        if sql.startswith("SELECT TOP 1 * FROM"):
            return []
        return self.rows.get(sql, [])

    def execute_batch(self, _mdb, ops, transaction=False):
        self.submitted_ops = ops
        self.ops, generated = _generated_batch(ops)
        self.transaction = transaction
        return SimpleNamespace(ok=True, first_error=lambda: None, results=[
            SimpleNamespace(generated_ids=ids, inserted=len(op.get("rows", [])), updated=1)
            for op, ids in zip(self.ops, generated)
        ])


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
        self.submitted_ops = ops
        self.ops, generated = _generated_batch(ops, getattr(self, "identity_seeds", None))
        self.transaction = transaction
        results = [
            SimpleNamespace(
                ok=self.batch_ok, error=None,
                inserted=len(op["rows"]) if op["op"] == "insert" else 0,
                updated=0 if self.no_match else (1 if op["op"] == "update" else 0),
                generated_ids=ids,
            )
            for op, ids in zip(self.ops, generated)
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

    def test_multiple_new_lists_in_one_currency_have_distinct_generated_identities(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22])
        lists = [
            PriceList(id=f"EURO_{year}", label=f"EURO_{year}", currency="EUR",
                      date_from=f"{year}0101", date_to=f"{year}1231")
            for year in (2027, 2028)
        ]
        records = [
            PriceRecord(article_code="A1", currency="EUR", value=year,
                        valid_from=f"{year}-06-01") for year in (2027, 2028)
        ]
        result = _export(mdb, records, lists)
        assert result["ok"] and result["verified"], result
        assert result["inserted_price_lists"] == 2 and result["inserted_prices"] == 2
        rows = next(op["rows"] for op in mdb.ops if op["table"] == "tCOMd_Price")
        assert {r["com_PriceListID"] for r in rows} == {1001, 1008}

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
                        currency="EUR", valid_from="2026-10-16", product_code="FR-X"),
        ]
        result = _export(mdb, records)
        self.assertEqual((result["updated_global_prices"], result["inserted_global_prices"]), (1, 1))
        update = next(op for op in mdb.ops if op["op"] == "update")
        self.assertEqual(update["where"], {"com_GlobalPriceID": 100})
        self.assertEqual(update["set"], {"com_PriceValue": 284.0})
        insert = next(op for op in mdb.ops if op["op"] == "insert" and op["table"] == "tCOMd_GlobalPrice")
        self.assertEqual(insert["rows"][0]["com_PriceLevelCode"], "X")

    def test_missing_global_placeholder_is_created_with_price_and_text_for_full_pdm_workflow(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22])
        result = _export(
            mdb,
            [PriceRecord(
                is_global=True, variant_condition="GE2HDF.", value=114.0,
                currency="GBP", valid_from="2026-10-16", product_code="FR-AA-US",
            )],
        )

        self.assertTrue(result["ok"] and result["verified"], result)
        self.assertEqual(result["inserted_global_prices"], 1)
        self.assertEqual(result["updated_global_prices"], 0)
        self.assertEqual(result["text_summary"]["text_create"], 1)
        text = _texts_op(mdb)["rows"][0]
        global_row = next(
            op for op in mdb.ops
            if op["op"] == "insert" and op["table"] == "tCOMd_GlobalPrice"
        )["rows"][0]
        self.assertEqual(global_row["com_VariantCondition"], "GE2HDF.")
        self.assertEqual(global_row["com_PriceValue"], 114.0)
        self.assertEqual(global_row["com_PriceLevelCode"], "X")
        self.assertEqual(global_row["sys_ISOCurrencyCode"], "GBP")
        self.assertEqual(global_row["com_PriceListID"], 22)
        self.assertEqual(global_row["com_TextID"], text["com_TextID"])
        self.assertEqual(text["com_TextName"], "GE2HDF.")

    def test_article_base_duplicate_updates_only_last_row_returned(self):
        dup = {"com_ArticleID": 4, "com_PriceListID": 21, "com_VariantCondition": "",
               "com_PriceLevelCode": "B", "sys_ISOCurrencyCode": "EUR"}
        prices = [{"com_PriceID": 1, "com_PriceValue": 0.0, **dup},
                  {"com_PriceID": 2, "com_PriceValue": 9.0, **dup},   # already correct: left alone
                  {"com_PriceID": 3, "com_PriceValue": 1.0, **dup}]
        mdb = _RecordingMDB(_eur_gbp_lists(), prices=prices, linked=[21, 22])
        result = _export(mdb, [_rec(9.0, "EUR")])
        self.assertEqual([op["where"]["com_PriceID"] for op in mdb.ops], [3])
        self.assertEqual(result["updated_prices"], 1)
        self.assertEqual(result["inserted_prices"], 0)
        self.assertEqual(result["duplicate_matches"], 1)

    def test_article_base_duplicate_leaves_earlier_stale_row_if_last_returned_is_current(self):
        dup = {"com_ArticleID": 4, "com_PriceListID": 21, "com_VariantCondition": "",
               "com_PriceLevelCode": "B", "sys_ISOCurrencyCode": "EUR"}
        prices = [{"com_PriceID": 1, "com_PriceValue": 1.0, **dup},
                  {"com_PriceID": 2, "com_PriceValue": 9.0, **dup}]
        mdb = _RecordingMDB(_eur_gbp_lists(), prices=prices, linked=[21, 22])
        result = _export(mdb, [_rec(9.0, "EUR")])
        self.assertEqual(mdb.ops, [])
        self.assertEqual(result["updated_prices"], 0)
        self.assertEqual(result["skipped_existing"], 1)

    def test_article_surcharge_duplicate_updates_only_last_returned_row(self):
        dup = {"com_ArticleID": 4, "com_PriceListID": 21, "com_VariantCondition": " 8=AA",
               "com_PriceLevelCode": "X", "sys_ISOCurrencyCode": "EUR"}
        prices = [{"com_PriceID": 1, "com_PriceValue": 1.0, **dup},
                  {"com_PriceID": 2, "com_PriceValue": 2.0, **dup}]
        mdb = _RecordingMDB(_eur_gbp_lists(), prices=prices, linked=[21, 22])
        result = _export(mdb, [_rec(9.0, "EUR", variant_condition=" 8=AA", level="X")])
        self.assertEqual([op["where"]["com_PriceID"] for op in mdb.ops], [2])
        self.assertEqual(result["updated_prices"], 1)

    def test_global_base_duplicate_updates_only_last_returned_row(self):
        duplicate = {
            "com_PackageID": 1,
            "com_PriceListID": 21,
            "com_VariantCondition": "GE2HDF.",
            "com_PriceLevelCode": "X",
            "sys_ISOCurrencyCode": "EUR",
        }
        globals_ = [
            {"com_GlobalPriceID": 101, "com_PriceValue": 10.0, **duplicate},
            {"com_GlobalPriceID": 102, "com_PriceValue": 20.0, **duplicate},
        ]
        mdb = _RecordingMDB(_eur_gbp_lists(), globals_=globals_, linked=[21, 22])
        result = _export(
            mdb,
            [PriceRecord(
                is_global=True,
                variant_condition="GE2HDF.",
                value=114.0,
                currency="EUR",
                valid_from="2026-10-16",
            )],
        )
        self.assertEqual(
            [op["where"]["com_GlobalPriceID"] for op in mdb.ops], [102]
        )
        self.assertEqual(result["updated_global_prices"], 1)

    def test_global_surcharge_duplicate_updates_each_differing_row(self):
        duplicate = {
            "com_PackageID": 1,
            "com_PriceListID": 21,
            "com_VariantCondition": "GE2HDF. 3827=DB3",
            "com_PriceLevelCode": "X",
            "sys_ISOCurrencyCode": "EUR",
        }
        globals_ = [
            {"com_GlobalPriceID": 101, "com_PriceValue": 10.0, **duplicate},
            {"com_GlobalPriceID": 102, "com_PriceValue": 20.0, **duplicate},
        ]
        mdb = _RecordingMDB(_eur_gbp_lists(), globals_=globals_, linked=[21, 22])
        result = _export(
            mdb,
            [PriceRecord(
                is_global=True,
                variant_condition="GE2HDF. 3827=DB3",
                value=114.0,
                currency="EUR",
                valid_from="2026-10-16",
            )],
        )
        self.assertEqual(
            [op["where"]["com_GlobalPriceID"] for op in mdb.ops], [101, 102]
        )
        self.assertEqual(result["updated_global_prices"], 2)

    def test_revive_lookup_condition_is_still_a_surcharge_for_duplicate_updates(self):
        condition = "3848=RYMPSH.12SW_OKG"
        duplicate = {
            "com_PackageID": 1, "com_PriceListID": 21,
            "com_VariantCondition": condition, "com_PriceLevelCode": "X",
            "sys_ISOCurrencyCode": "EUR",
        }
        mdb = _RecordingMDB(_eur_gbp_lists(), globals_=[
            {"com_GlobalPriceID": 101, "com_PriceValue": 10.0, **duplicate},
            {"com_GlobalPriceID": 102, "com_PriceValue": 20.0, **duplicate},
        ], linked=[21, 22])
        result = _export(mdb, [PriceRecord(
            is_global=True, variant_condition=condition,
            source_item="RYMPSH.12SW", pdm_lookup_code=condition,
            value=52.0, currency="EUR",
        )])
        self.assertEqual([op["where"]["com_GlobalPriceID"] for op in mdb.ops], [101, 102])
        self.assertEqual(result["updated_global_prices"], 2)

    def test_revive_increment_without_source_item_base_is_not_inserted(self):
        condition = "3848=RYMPSH.12SW_OKG"
        mdb = _RecordingMDB(_eur_gbp_lists(), linked=[21, 22])
        result = _export(mdb, [PriceRecord(
            is_global=True, variant_condition=condition,
            source_item="RYMPSH.12SW", pdm_lookup_code=condition,
            value=52.0, currency="EUR",
        )])
        self.assertEqual(mdb.ops, [])
        self.assertEqual(result["skipped_no_base_price"], 1)

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


class _OptimizedFake(_RecordingMDB):
    """Fake with the bridge's batched ``read_tables`` so the production read
    path (targeted reads + post-write verification) is exercised."""

    def __init__(self, *args, texts=(), corrupt_readback=False, **kw):
        super().__init__(*args, **kw)
        self.texts = list(texts)
        self.corrupt = corrupt_readback

    def read_tables(self, _mdb, sql_by_name):
        out = {}
        for name, sql in sql_by_name.items():
            if name == "articles":
                out[name] = [{"com_ArticleID": 4, "com_ArticleCode": "A1"}]
            elif name == "packages":
                out[name] = [{"com_PackageID": 1}]
            elif name == "lists":
                out[name] = self.rows[_LISTS_SQL]
            elif name == "linked":
                out[name] = self.rows[_LINKED_SQL]
            elif name in ("price_proto", "global_proto", "list_proto"):
                out[name] = []
            elif name == "text_proto":
                out[name] = _TEXT_PROTO
            elif name == "text_max":
                out[name] = [{"max_id": 500}]
            elif name == "price_keys":
                out[name] = self.rows[_PRICE_SQL]
            elif name == "global_keys":
                out[name] = self.rows[_GLOBAL_SQL]
            elif name == "texts":
                out[name] = self.texts
            elif name in ("price_max", "global_max"):
                out[name] = [{"max_id": 100}]
            else:  # post-write read-back chunk: echo what the batch wrote
                out[name] = self._readback(name, sql)
        return out

    def _text_state(self):
        """Texts as the MDB holds them after the recorded batch."""
        state = {t["com_TextID"]: dict(t) for t in self.texts}
        for op in self.ops:
            if op["op"] == "insert" and op["table"] == "tCOMd_Text":
                for r in op["rows"]:
                    state[r["com_TextID"]] = dict(r)
        return state

    def _readback(self, name, sql=""):
        kind = name.split(":")[0]
        if kind == "texts":
            wanted = {int(x) for x in sql.split("IN (")[1].rstrip(")").split(",")}
            return [{**t, "id": t["com_TextID"]} for i, t in self._text_state().items() if i in wanted]
        if kind == "textdup":
            counts = {}
            for t in self._text_state().values():
                counts[t["com_TextName"]] = counts.get(t["com_TextName"], 0) + 1
            return [{"com_TextName": n, "n": c} for n, c in counts.items() if f"'{n}'" in sql]
        if kind == "lists":
            wanted = {int(x) for x in sql.split("IN (")[1].rstrip(")").split(",")}
            rows = [{**r, "id": r["com_PriceListID"]} for r in self.rows[_LISTS_SQL]]
            for op in self.ops:
                if op["op"] == "insert" and op["table"] == "tCOMd_PriceList2":
                    rows += [{**r, "id": r["com_PriceListID"]} for r in op["rows"]]
            return [r for r in rows if r["id"] in wanted]
        if kind == "links":
            wanted = {int(x) for x in sql.split("IN (")[1].rstrip(")").split(",")}
            return [{"id": g["com_GlobalPriceID"], "com_TextID": g.get("com_TextID")}
                    for g in self.rows[_GLOBAL_SQL] if g["com_GlobalPriceID"] in wanted]
        table = kind
        pk = "com_PriceID" if table == "tCOMd_Price" else "com_GlobalPriceID"
        rows = []
        for op in self.ops:
            if op["table"] != table:
                continue
            if op["op"] == "update":
                rows.append({"id": op["where"][pk], "com_PriceValue": op["set"]["com_PriceValue"],
                             "com_PriceListID": None,
                             "com_VariantCondition": op["set"].get("com_VariantCondition")})
            elif op["op"] == "insert":
                rows += [{"id": r[pk], "com_PriceValue": r["com_PriceValue"],
                          "com_PriceListID": r["com_PriceListID"],
                          "com_VariantCondition": r["com_VariantCondition"],
                          "sys_ISOCurrencyCode": r["sys_ISOCurrencyCode"],
                          "com_TextID": r.get("com_TextID")} for r in op["rows"]]
        if table == "tCOMd_GlobalPrice":  # updated rows keep the link they had
            seen = {r["id"] for r in rows}
            for g in self.rows[_GLOBAL_SQL]:
                for r in rows:
                    if r["id"] == g["com_GlobalPriceID"] and r["id"] in seen and "com_TextID" not in r:
                        r["com_TextID"] = g.get("com_TextID")
            for r in rows:
                r.setdefault("com_TextID", next((g.get("com_TextID") for g in self.rows[_GLOBAL_SQL]
                                                 if g["com_GlobalPriceID"] == r["id"]), None))
        if self.corrupt:
            rows = [{**r, "com_PriceValue": -1} for r in rows]
        return rows


def _export_dry(mdb, records, lists=()):
    snapshot = Snapshot()
    snapshot.price_lists = list(lists)
    snapshot.price_records = list(records)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "existing.mdb"
        path.touch()
        return PriceMdbExportService(SimpleNamespace(mdb_service=mdb)).export(snapshot, path, dry_run=True)


def _eur_row(pid=1, value=1.0, **kw):
    return {"com_PriceID": pid, "com_ArticleID": 4, "com_PriceListID": 21, "com_VariantCondition": "",
            "com_PriceLevelCode": "B", "sys_ISOCurrencyCode": "EUR", "com_PriceValue": value, **kw}


class PriceMdbExportPdmParityTests(unittest.TestCase):
    """Behaviours taken from PDM's PriceMaintenance.UpdatePConItemPrice /
    AddMissingGlobalPricingRecords (see docs/03_Workflows/pricing_pdm_parity.md)."""

    def test_zero_price_never_written(self):
        # PDM: `if (num7 != 0.0 || resetToZero)` - a zero PDM price is "unresolved".
        mdb = _RecordingMDB(_eur_gbp_lists(), prices=[_eur_row(value=50.0)], linked=[21, 22])
        result = _export(mdb, [_rec(0.0, "EUR"), _rec(0.0, "GBP")])
        self.assertEqual(mdb.ops, [])
        self.assertEqual(result["skipped_zero_price"], 2)

    def test_global_insert_links_price_text_and_uses_list_validity(self):
        base_row = {"com_GlobalPriceID": 9, "com_PackageID": 1, "com_PriceListID": 21, "com_VariantCondition": "GESNNU.1",
                    "com_PriceLevelCode": "X", "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 1.0, "com_TextID": 77}
        mdb = _OptimizedFake(_eur_gbp_lists(), globals_=[base_row], linked=[21, 22],
                             texts=[{"com_TextID": 77, "com_TextName": "8"},
                                    {"com_TextID": 88, "com_TextName": "GE2HBS."}])
        records = [
            PriceRecord(is_global=True, variant_condition="GESNNU.1 8=1FD", value=58.0, currency="EUR",
                        valid_from="2026-10-16"),
            PriceRecord(is_global=True, variant_condition="GE2HBS.", value=69.0, currency="EUR",
                        valid_from="2026-10-16"),
            PriceRecord(is_global=True, variant_condition="NOTEXT.1", value=5.0, currency="EUR",
                        valid_from="2026-10-16", product_code="FR-AA-US"),
        ]
        result = _export(mdb, records)
        rows = next(op for op in mdb.ops if op["op"] == "insert" and op["table"] == "tCOMd_GlobalPrice")["rows"]
        # surcharge -> shared option-id text; known item -> its text; unknown item -> a NEW text.
        self.assertEqual([r["com_TextID"] for r in rows], [77, 88, 500 + 1])
        self.assertEqual({r["com_PriceLevelCode"] for r in rows}, {"X"})
        # PDM stamps new global rows with the price list's validity, not the record's date.
        self.assertEqual({r["com_PriceValidFrom"] for r in rows}, {"#2026-01-01 00:00:00#"})
        self.assertTrue(result["verified"])
        self.assertEqual(result["text_result"]["rows_linked"], 3)


    def test_existing_row_currency_is_not_part_of_identity(self):
        # PDM matches by list + article + variant + level; the list fixes the currency.
        mdb = _RecordingMDB(_eur_gbp_lists(), prices=[_eur_row(sys_ISOCurrencyCode="")], linked=[21, 22])
        result = _export(mdb, [_rec(9.0, "EUR")])
        self.assertEqual((result["updated_prices"], result["inserted_prices"]), (1, 0))

    def test_new_article_price_copies_the_articles_existing_validity(self):
        existing = _eur_row(com_VariantCondition=".L", com_PriceValidFrom="2026-03-01",
                            com_PriceValidTo="2026-12-31")
        mdb = _RecordingMDB(_eur_gbp_lists(), prices=[existing], linked=[21, 22])
        _export(mdb, [_rec(9.0, "EUR", variant_condition=".S")])
        row = next(op for op in mdb.ops if op["op"] == "insert")["rows"][0]
        self.assertEqual((row["com_PriceValidFrom"], row["com_PriceValidTo"]),
                         ("#2026-03-01 00:00:00#", "#2026-12-31 00:00:00#"))

    def test_dry_run_reports_the_plan_and_executes_nothing(self):
        mdb = _RecordingMDB(_eur_gbp_lists(), prices=[_eur_row()], linked=[21, 22])
        mdb.ops = None
        result = _export_dry(mdb, [_rec(9.0, "EUR"), _rec(4.0, "GBP")])
        self.assertIsNone(mdb.ops)  # execute_batch never called
        self.assertTrue(result["dry_run"])
        self.assertEqual((result["updated_prices"], result["inserted_prices"]), (1, 1))
        self.assertEqual((result["plan_updates"][0]["from"], result["plan_updates"][0]["to"]), (1.0, 9.0))

    def test_readback_mismatch_is_reported_as_failure(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), prices=[_eur_row()], linked=[21, 22], corrupt_readback=True)
        result = _export(mdb, [_rec(9.0, "EUR")])
        self.assertFalse(result["ok"])
        self.assertFalse(result["verified"])
        self.assertIn("verification failed", result["error"])
        self.assertTrue(result["verification_failures"])


class PriceMdbExportTargetReportTests(unittest.TestCase):
    def test_target_lists_report_link_status_and_warn_when_unlinked(self):
        lists = _eur_gbp_lists()
        mdb = _RecordingMDB(lists, prices=[_eur_row(value=1.0)], linked=[21])  # GBP list 22 unlinked
        result = _export(mdb, [_rec(9.0, "EUR"), _rec(4.0, "GBP")])
        targets = {t["id"]: t for t in result["target_lists"]}
        self.assertEqual((targets[21]["linked"], targets[21]["updates"]), (True, 1))
        self.assertEqual((targets[22]["linked"], targets[22]["inserts"]), (False, 1))
        self.assertTrue(any("GBP_2026_2" in w and "not linked" in w for w in result["warnings"]))

    def test_user_named_list_is_honoured_even_when_unlinked(self):
        # PDM writes to the list the user selected; only a warning is raised.
        lists = [_plist(21, "EURO_2026_2", "EUR"), _plist(30, "EURO_SPECIAL", "EUR")]
        mdb = _RecordingMDB(lists, linked=[21])
        result = _export(mdb, [_rec(9.0, "EUR")],
                         [PriceList(id="EURO_SPECIAL", label="EURO_SPECIAL", currency="EUR",
                                    date_from="20260101", date_to="99991231")])
        self.assertEqual(mdb.ops[0]["rows"][0]["com_PriceListID"], 30)
        self.assertTrue(any("EURO_SPECIAL" in w for w in result["warnings"]))

    def test_duplicate_matches_are_counted_when_only_last_base_row_is_updated(self):
        mdb = _RecordingMDB(_eur_gbp_lists(), prices=[_eur_row(1, 0.0), _eur_row(2, 0.0)], linked=[21, 22])
        result = _export(mdb, [_rec(9.0, "EUR")])
        self.assertEqual(result["duplicate_matches"], 1)
        self.assertEqual(result["updated_prices"], 1)


if __name__ == "__main__":
    unittest.main()


def _global(vc, value=10.0, ccy="EUR", **kw):
    kw.setdefault("product_code", "P-1")  # as computed by PricingService from PDM
    return PriceRecord(is_global=True, variant_condition=vc, value=value, currency=ccy,
                       valid_from="2026-10-16", **kw)


def _texts_op(mdb):
    return next((op for op in mdb.ops if op["op"] == "insert" and op["table"] == "tCOMd_Text"), None)


def _global_op(mdb):
    return next(op for op in mdb.ops if op["op"] == "insert" and op["table"] == "tCOMd_GlobalPrice")


class PriceTextLabelTests(unittest.TestCase):
    """PDM AddMissingGlobalPricingRecords naming (name = com_TextName, display = language text)."""

    def test_labels_follow_pdm(self):
        from services.price_text_blocks import price_text_labels
        self.assertEqual(price_text_labels("GE2HBS.", "FR-AA-US"), ("GE2HBS.", "GE2HBS.  (FR-AA-US)"))
        self.assertEqual(price_text_labels("GESNNU.1 8=1FD", "X"), ("8", "Surcharge 8"))
        self.assertEqual(price_text_labels("A_B.1", "X"), ("A_B.1", "A_B.1"))
        self.assertEqual(price_text_labels("NOCODE.1"), ("NOCODE.1", "NOCODE.1"))

    def test_language_columns_use_the_schemas_prefix(self):
        from services.price_text_blocks import language_columns
        self.assertEqual(language_columns(_TEXT_COLS),
                         ["com_Text_1_en", "com_Text_1_de", "com_Text_1_fr", "com_Text_1_nl"])
        self.assertEqual(language_columns(["com_TextID", "com_TextName"]), [])


class PriceMdbExportTextBlockTests(unittest.TestCase):
    def test_new_global_creates_text_with_pdm_columns_and_links_it(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22])
        result = _export(mdb, [_global("GE2HBS.", product_code="FR-AA-US")])
        text = _texts_op(mdb)["rows"][0]
        self.assertEqual(text["com_TextTypeCode"], "price")
        self.assertEqual(text["com_PackageID"], 1)
        self.assertEqual(text["com_TextName"], "GE2HBS.")
        for col in ("com_Text_1_en", "com_Text_1_de", "com_Text_1_fr", "com_Text_1_nl"):
            self.assertEqual(text[col], "GE2HBS.  (FR-AA-US)")
        self.assertNotIn("sys_tmpID", text)  # bookkeeping columns are never invented
        self.assertEqual(_global_op(mdb)["rows"][0]["com_TextID"], text["com_TextID"])
        self.assertEqual(mdb.ops[0]["table"], "tCOMd_Text")  # texts are written before their prices
        self.assertEqual(result["text_result"]["texts_created"], 1)
        self.assertTrue(result["verified"])

    def test_text_is_created_once_and_shared_by_eur_and_gbp_rows(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22])
        result = _export(mdb, [_global("GE2HBS.", 10, "EUR", product_code="P"),
                               _global("GE2HBS.", 9, "GBP", product_code="P")])
        self.assertEqual(len(_texts_op(mdb)["rows"]), 1)
        rows = _global_op(mdb)["rows"]
        self.assertEqual(len({r["com_TextID"] for r in rows}), 1)
        self.assertEqual(result["text_summary"]["text_create"], 1)
        self.assertEqual(result["text_summary"]["text_link_new"], 1)
        self.assertEqual(result["text_result"]["rows_linked"], 2)

    def test_existing_text_is_reused_not_duplicated(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22],
                             texts=[{"com_TextID": 88, "com_TextName": "ge2hbs."}])  # Jet compares case-insensitively
        result = _export(mdb, [_global("GE2HBS.")])
        self.assertIsNone(_texts_op(mdb))
        self.assertEqual(_global_op(mdb)["rows"][0]["com_TextID"], 88)
        self.assertEqual(result["text_summary"]["text_reuse"], 1)
        self.assertEqual(result["text_summary"]["text_create"], 0)
        self.assertEqual(result["text_result"]["texts_reused"], 1)

    def test_ambiguous_text_name_blocks_the_row_instead_of_guessing(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22],
                             texts=[{"com_TextID": 1, "com_TextName": "8"}, {"com_TextID": 2, "com_TextName": "8"}])
        result = _export(mdb, [_global("X.1"), _global("X.1 8=AA"), _global("OK.1")])
        self.assertEqual(result["text_summary"]["text_missing_or_ambiguous"], 1)
        self.assertEqual(result["skipped_text_blocked"], 1)
        self.assertEqual(result["inserted_global_prices"], 2)
        self.assertTrue(any(e["text_status"] == "ambiguous" for e in result["text_rows"]))

    def test_missing_language_columns_block_creation_with_a_reason(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22])
        orig = mdb.read_tables

        def no_lang_cols(m, q):
            out = orig(m, q)
            if "text_proto" in out:
                out["text_proto"] = [{"com_TextID": 1}]
            return out

        mdb.read_tables = no_lang_cols
        result = _export(mdb, [_global("NEW.1")])
        self.assertEqual(result["inserted_global_prices"], 0)
        self.assertEqual(mdb.ops, [])
        self.assertIn("language columns", result["text_rows"][0]["reason"])

    def test_existing_rows_keep_their_links_and_are_reported(self):
        globals_ = [
            {"com_GlobalPriceID": 100, "com_PackageID": 1, "com_PriceListID": 21, "com_VariantCondition": "L.1",
             "com_PriceLevelCode": "X", "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 1.0, "com_TextID": 55},
            {"com_GlobalPriceID": 101, "com_PackageID": 1, "com_PriceListID": 21, "com_VariantCondition": "U.1",
             "com_PriceLevelCode": "X", "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 1.0, "com_TextID": None},
        ]
        mdb = _OptimizedFake(_eur_gbp_lists(), globals_=globals_, linked=[21, 22],
                             texts=[{"com_TextID": 55, "com_TextName": "L.1"}])
        result = _export(mdb, [_global("L.1", 5.0), _global("U.1", 6.0)])
        self.assertEqual({op["op"] for op in mdb.ops}, {"update"})
        for op in mdb.ops:  # only the value is written: links are never touched
            self.assertEqual(set(op["set"]), {"com_PriceValue"})
        self.assertEqual(result["text_summary"]["text_preserve"], 1)
        self.assertEqual(result["text_summary"]["text_unlinked_existing"], 1)
        self.assertEqual(result["text_result"]["links_preserved"], 1)
        self.assertTrue(result["verified"])

    def test_article_prices_never_get_a_text(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22])
        result = _export(mdb, [_rec(9.0, "EUR")])
        self.assertIsNone(_texts_op(mdb))
        self.assertIsNone(next(op for op in mdb.ops if op["table"] == "tCOMd_Price")["rows"][0]["com_TextID"])
        self.assertEqual(result["text_rows"][0]["action"], "none")

    def test_dry_run_reports_text_operations_and_writes_nothing(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22],
                             texts=[{"com_TextID": 88, "com_TextName": "OLD."}])
        result = _export_dry(mdb, [_global("OLD."), _global("NEW.1"), _global("NEW.1", 8, "GBP"),
                                   _rec(9.0, "EUR")])
        self.assertEqual(mdb.ops, [])
        summary = result["text_summary"]
        self.assertEqual((summary["text_reuse"], summary["text_create"], summary["text_link_new"]), (1, 1, 1))
        self.assertEqual(summary["price_rows_to_insert"], 4)
        actions = {(e["variant_condition"], e["currency"]): e["action"] for e in result["text_rows"]}
        self.assertEqual(actions[("NEW.1", "EUR")], "create")
        # A planned text never shows an id: nothing has been written yet.
        self.assertTrue(all(e["text_id"] is None for e in result["text_rows"]
                            if e["action"] in ("create", "link_new")))
        self.assertEqual([e["text_id"] for e in result["text_rows"] if e["action"] == "reuse"], [88])

    def test_second_export_creates_no_rows_or_texts(self):
        first = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22])
        _export(first, [_global("NEW.1")])
        text = _texts_op(first)["rows"][0]
        written = _global_op(first)["rows"][0]
        second = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22],
                                globals_=[{**written, "com_GlobalPriceID": 100}],
                                texts=[{"com_TextID": text["com_TextID"], "com_TextName": text["com_TextName"]}])
        result = _export(second, [_global("NEW.1")])
        self.assertEqual(second.ops, [])
        self.assertEqual((result["inserted_global_prices"], result["text_result"]["texts_created"]), (0, 0))
        self.assertEqual(result["text_summary"]["text_preserve"], 1)

    def test_failed_batch_rolls_back_prices_and_texts_together(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22], batch_ok=False)
        result = _export(mdb, [_global("NEW.1")])
        self.assertFalse(result["ok"])
        self.assertTrue(mdb.transaction)  # prices and texts share one transaction
        self.assertEqual(result["text_result"]["texts_created"], 0)
        self.assertEqual(result["text_result"]["text_operations_failed"], 1)

    def test_readback_detects_a_missing_text_as_dangling(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22])
        base = mdb._readback
        mdb._readback = lambda name, sql="": [] if name.startswith("texts:") else base(name, sql)
        result = _export(mdb, [_global("NEW.1")])
        self.assertFalse(result["ok"])
        self.assertFalse(result["verified"])
        self.assertTrue(any("missing after write" in f or "dangling" in f
                            for f in result["verification_failures"]))
        self.assertEqual(result["text_result"]["texts_created"], 1)
        self.assertGreater(result["text_result"]["text_operations_failed"], 0)
        self.assertEqual(result["text_rows"][0]["text_status"], "unverified")
        self.assertIsNone(result["text_rows"][0]["text_id"])

    def test_readback_detects_a_wrong_link(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22],
                             texts=[{"com_TextID": 88, "com_TextName": "OLD."}])
        base = mdb._readback

        def wrong_link(name, sql=""):
            rows = base(name, sql)
            if name.startswith("tCOMd_GlobalPrice:"):
                rows = [{**r, "com_TextID": 999} for r in rows]
            return rows

        mdb._readback = wrong_link
        result = _export(mdb, [_global("OLD.")])
        self.assertFalse(result["verified"])
        self.assertTrue(any("text link 999 != 88" in f for f in result["verification_failures"]))

    def test_duplicate_text_after_write_is_a_failure(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22])
        base = mdb._readback
        mdb._readback = lambda name, sql="": ([{"com_TextName": "NEW.1", "n": 2}]
                                              if name.startswith("textdup:") else base(name, sql))
        result = _export(mdb, [_global("NEW.1")])
        self.assertFalse(result["verified"])
        self.assertTrue(any("duplicate texts" in f for f in result["verification_failures"]))

    def test_unknown_product_code_blocks_creation_instead_of_a_degraded_label(self):
        mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22],
                             texts=[{"com_TextID": 88, "com_TextName": "OLD."}])
        base = {"com_GlobalPriceID": 9, "com_PackageID": 1, "com_PriceListID": 21, "com_VariantCondition": "X_1",
                "com_PriceLevelCode": "X", "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 1.0, "com_TextID": 88}
        mdb = _OptimizedFake(_eur_gbp_lists(), globals_=[base], linked=[21, 22],
                             texts=[{"com_TextID": 88, "com_TextName": "OLD."}])
        result = _export(mdb, [_global("NEW.1", product_code=""), _global("OLD.", product_code=""),
                               _global("NEW_2.1", product_code=""), _global("X_1 8=AA", product_code="")])
        self.assertEqual(result["skipped_text_blocked"], 1)           # only the code-dependent label
        self.assertIn("Product_Code unknown", result["text_rows"][0]["reason"])
        self.assertEqual(result["inserted_global_prices"], 3)         # reuse / underscore / surcharge need no code
        names = [r["com_TextName"] for r in _texts_op(mdb)["rows"]]
        self.assertEqual(sorted(names), ["8", "NEW_2.1"])
        self.assertTrue(any("not inserted" in w for w in result["warnings"]))



class PriceMdbExportFarFutureValidityTests(unittest.TestCase):
    def test_new_article_price_copies_a_9999_validity_end_instead_of_blanking_it(self):
        # Real MDB: Access's "no end" 9999-12-31 arrives as /Date(253402194600000)/ and
        # must not collapse to "" (which Access rejects as a date: data type mismatch).
        existing = _eur_row(pid=1, value=1.0, com_PriceValidFrom="/Date(1788719400000)/",
                            com_PriceValidTo="/Date(253402194600000)/")
        mdb = _OptimizedFake(_eur_gbp_lists(), prices=[existing], linked=[21, 22])
        result = _export(mdb, [_rec(5.0, "EUR", variant_condition=" 99=ZZ", level="X")])
        row = next(op for op in mdb.ops if op["table"] == "tCOMd_Price")["rows"][0]
        self.assertTrue(result["ok"])
        self.assertRegex(row["com_PriceValidFrom"], r"^#2026-09-0[67] 00:00:00#$")
        self.assertRegex(row["com_PriceValidTo"], r"^#9999-12-(30|31) 00:00:00#$")


def _export_strict(mdb, records, targets, dry_run=False, expected_plan=None):
    snapshot = Snapshot()
    snapshot.price_records = list(records)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "existing.mdb"
        path.touch()
        return PriceMdbExportService(SimpleNamespace(mdb_service=mdb)).export(
            snapshot, path, dry_run=dry_run, list_targets=targets, expected_plan=expected_plan)


def _strict_lists():
    return [_plist(21, "EURO_2026_2", "EUR", "2026-09-07"), _plist(22, "GBP_2026_2", "GBP", "2026-09-07")]


_T = {"EUR": "EURO_2026_2", "GBP": "GBP_2026_2"}


def _on(ccy, day, value=5.0, **kw):
    kw.setdefault("article_code", "A1")
    return PriceRecord(value=value, currency=ccy, valid_from=day, **kw)


class PriceMdbExportListTargetTests(unittest.TestCase):
    def test_currency_is_routed_only_to_its_own_target_list(self):
        mdb = _OptimizedFake(_strict_lists(), linked=[21, 22])
        result = _export_strict(mdb, [_rec(10.0, "EUR"), _rec(9.0, "GBP"),
                                      _global("G.1", 5.0, "EUR"), _global("G.1", 4.0, "GBP")], _T)
        self.assertTrue(result["ok"] and result["verified"], result)
        by_ccy = {r["sys_ISOCurrencyCode"]: r["com_PriceListID"]
                  for op in mdb.ops if op["op"] == "insert" and op["table"] in ("tCOMd_Price", "tCOMd_GlobalPrice")
                  for r in op["rows"]}
        self.assertEqual(by_ccy, {"EUR": 21, "GBP": 22})
        for entry in result["text_rows"]:
            self.assertEqual(entry["list_id"], 21 if entry["currency"] == "EUR" else 22)

    def test_renamed_lists_are_created_with_chosen_names_currency_ids_and_dates(self):
        mdb = _OptimizedFake(_strict_lists(), linked=[21, 22])
        result = _export_strict(mdb, [_on("EUR", "2027-01-05", 10.0), _on("GBP", "2027-01-05", 9.0)],
                                {"EUR": "EURO_2027", "GBP": "gbp_2027"})
        self.assertTrue(result["ok"] and result["verified"], result)
        created = next(op for op in mdb.ops if op["table"] == "tCOMd_PriceList2")["rows"]
        self.assertEqual({(r["com_PriceListLabel"], r["sys_ISOCurrencyCode"]) for r in created},
                         {("EURO_2027", "EUR"), ("gbp_2027", "GBP")})        # chosen spelling preserved
        self.assertEqual({r["com_PriceValidFrom"] for r in created}, {"#2027-01-05 00:00:00#"})
        self.assertEqual({r["com_PriceValidTo"] for r in created}, {"#9999-12-31 00:00:00#"})
        self.assertEqual(result["inserted_price_lists"], 2)
        plan = {p["currency"]: p for p in result["list_plan"]}
        self.assertEqual((plan["EUR"]["action"], plan["GBP"]["action"]), ("create", "create"))
        ids = {r["com_PriceListID"] for r in created}
        prices = next(op for op in mdb.ops if op["table"] == "tCOMd_Price")["rows"]
        self.assertEqual({r["com_PriceListID"] for r in prices}, ids)       # rows use the new ids
        self.assertEqual(sorted(ids), [1001, 1008])  # generated by the MDB, not MAX+1

    def test_existing_lists_are_reused_not_duplicated_for_a_spelling_variant(self):
        mdb = _OptimizedFake(_strict_lists(), linked=[21, 22])
        result = _export_strict(mdb, [_rec(10.0, "EUR")], {"EUR": "euro 2026_2", "GBP": "GBP_2026_2"})
        self.assertEqual(result["inserted_price_lists"], 0)
        self.assertEqual([p["action"] for p in result["list_plan"]], ["reuse"])

    def test_list_whose_validity_does_not_cover_the_date_blocks_everything(self):
        lists = [_plist(21, "EURO_2026_2", "EUR", "2026-09-07", "2026-12-31")]
        mdb = _OptimizedFake(lists, linked=[21])
        result = _export_strict(mdb, [_on("EUR", "2027-01-02")], {"EUR": "EURO_2026_2"})
        self.assertFalse(result["ok"])
        self.assertIn("does not cover", result["error"])
        self.assertEqual(mdb.ops, [])

    def test_dry_run_with_an_invalid_target_reports_it_and_forbids_export(self):
        mdb = _OptimizedFake(_strict_lists(), linked=[21, 22])
        result = _export_strict(mdb, [_rec(10.0, "EUR")], {"EUR": "bad/name", "GBP": "GBP_2026_2"}, dry_run=True)
        self.assertTrue(result["ok"])
        self.assertFalse(result["export_allowed"])
        self.assertTrue(any("letters" in e for e in result["blocking_errors"]))
        self.assertEqual(mdb.ops, [])

    def test_ambiguous_list_match_stops_the_export(self):
        lists = [_plist(30, "EURO 2026_2", "EUR"), _plist(31, "Euro_2026_2", "EUR")]
        mdb = _OptimizedFake(lists, linked=[])
        result = _export_strict(mdb, [_rec(10.0, "EUR")], {"EUR": "EURO-2026-2"})
        self.assertFalse(result["ok"])
        self.assertIn("matches 2", result["error"])
        self.assertEqual(mdb.ops, [])

    def test_currency_without_a_target_is_blocked_with_a_reason(self):
        mdb = _OptimizedFake(_strict_lists(), linked=[21, 22])
        result = _export_strict(mdb, [_rec(10.0, "EUR"), _rec(7.0, "USD")], {"EUR": "EURO_2026_2"}, dry_run=True)
        self.assertFalse(result["export_allowed"])             # USD has no name -> blocking
        self.assertTrue(any(e.startswith("USD:") for e in result["blocking_errors"]))
        self.assertEqual(result["blocked_rows"][0]["currency"], "USD")

    def test_record_outside_the_list_period_is_blocked_individually(self):
        mdb = _OptimizedFake(_strict_lists(), linked=[21, 22])
        result = _export_strict(mdb, [_rec(10.0, "EUR"), _on("EUR", "2026-01-01", 3.0, variant_condition=" 9=Z", level="X")],
                                _T, dry_run=True)
        self.assertEqual(result["skipped_unmapped"], 1)
        self.assertIn("outside list", result["blocked_rows"][0]["reason"])
        self.assertEqual(result["inserted_prices"], 1)

    def test_preview_exposes_date_lists_ids_and_validity(self):
        mdb = _OptimizedFake(_strict_lists(), linked=[21])
        result = _export_strict(mdb, [_rec(10.0, "EUR"), _rec(9.0, "GBP")], _T, dry_run=True)
        self.assertEqual(result["computation_date"], "20261016")
        plan = {p["currency"]: p for p in result["list_plan"]}
        self.assertEqual((plan["EUR"]["list_id"], plan["GBP"]["list_id"]), (21, 22))
        self.assertEqual(plan["EUR"]["date_from"], "20260907")
        self.assertTrue(plan["EUR"]["linked"] and not plan["GBP"]["linked"])
        self.assertTrue(any("not linked" in w for w in plan["GBP"]["warnings"]))
        self.assertEqual(mdb.ops, [])

    def test_plan_digest_binds_the_export_to_the_previewed_plan(self):
        recs = [_rec(10.0, "EUR"), _global("G.1", 5.0, "EUR")]

        def preview(records=recs, targets=_T):
            return _export_strict(_OptimizedFake(_strict_lists(), linked=[21, 22]), records, targets, dry_run=True)

        base = preview()
        self.assertEqual(base["plan_digest"], preview()["plan_digest"])               # deterministic
        self.assertNotEqual(base["plan_digest"],
                            preview(targets={"EUR": "EURO_2026_3", "GBP": "GBP_2026_2"})["plan_digest"])
        self.assertNotEqual(base["plan_digest"], preview([_rec(11.0, "EUR"), recs[1]])["plan_digest"])

        stale = _OptimizedFake(_strict_lists(), linked=[21, 22])
        refused = _export_strict(stale, recs, _T, expected_plan="0" * 64)
        self.assertFalse(refused["ok"])
        self.assertIn("Preview Export again", refused["error"])
        self.assertEqual(stale.ops, [])
        fresh = _OptimizedFake(_strict_lists(), linked=[21, 22])
        done = _export_strict(fresh, recs, _T, expected_plan=base["plan_digest"])
        self.assertTrue(done["ok"])
        self.assertTrue(fresh.ops)

    def test_readback_flags_rows_pointing_at_a_list_of_the_wrong_currency(self):
        mdb = _OptimizedFake(_strict_lists(), linked=[21, 22])
        base = mdb._readback

        def swapped(name, sql=""):
            rows = base(name, sql)
            if name.startswith("lists:"):
                return [{**r, "sys_ISOCurrencyCode": "GBP" if r["id"] == 21 else "EUR"} for r in rows]
            return rows

        mdb._readback = swapped
        result = _export_strict(mdb, [_rec(10.0, "EUR")], _T)
        self.assertFalse(result["ok"])
        self.assertTrue(any("currency routing" in f for f in result["verification_failures"]))

    def test_created_list_is_verified_by_readback(self):
        mdb = _OptimizedFake(_strict_lists(), linked=[21, 22])
        base = mdb._readback
        mdb._readback = lambda name, sql="": ([{**r, "com_PriceListLabel": "OTHER"} for r in base(name, sql)]
                                              if name.startswith("lists:") else base(name, sql))
        result = _export_strict(mdb, [_on("EUR", "2027-01-05")], {"EUR": "EURO_2027"})
        self.assertFalse(result["verified"])
        self.assertTrue(any("label" in f for f in result["verification_failures"]))

    def test_repeating_a_strict_export_creates_nothing_new(self):
        recs = [_on("EUR", "2027-01-05")]
        first = _OptimizedFake(_strict_lists(), linked=[21, 22])
        _export_strict(first, recs, {"EUR": "EURO_2027"})
        new_list = next(op for op in first.ops if op["table"] == "tCOMd_PriceList2")["rows"][0]
        row = next(op for op in first.ops if op["table"] == "tCOMd_Price")["rows"][0]
        second = _OptimizedFake(_strict_lists() + [{**new_list, "com_PriceValidFrom": "2027-01-05",
                                                    "com_PriceValidTo": "9999-12-31"}],
                                prices=[{**row, "com_PriceID": 5}], linked=[21, 22])
        result = _export_strict(second, recs, {"EUR": "EURO_2027"})
        self.assertEqual(second.ops, [])
        self.assertEqual((result["inserted_price_lists"], result["inserted_prices"]), (0, 0))

    def test_nothing_is_ever_deleted_and_only_values_are_updated(self):
        mdb = _OptimizedFake(_strict_lists(), prices=[_eur_row(pid=1, value=1.0)], linked=[21, 22])
        _export_strict(mdb, [_rec(5.0, "EUR"), _rec(2.0, "GBP", variant_condition=" 9=Z", level="X")], _T)
        self.assertNotIn("delete", {op["op"] for op in mdb.ops})
        for op in mdb.ops:
            if op["op"] == "update":
                self.assertEqual(set(op["set"]), {"com_PriceValue"})


class PriceMdbExportLockTests(unittest.TestCase):
    def test_a_genuine_sharing_error_is_reported_clearly_and_nothing_is_claimed_written(self):
        mdb = _OptimizedFake(_strict_lists(), linked=[21, 22], batch_ok=False)
        mdb.execute_batch = lambda *_a, **_k: SimpleNamespace(
            ok=False, results=[], first_error=lambda: "insert(Could not lock table 'tCOMd_Price'; currently in use)")
        result = _export_strict(mdb, [_rec(10.0, "EUR")], _T)
        self.assertFalse(result["ok"])
        self.assertIn("locked or in use", result["error"])
        self.assertEqual(result["inserted_prices"], 0)


class PriceMdbExportUpchargeBaseTests(unittest.TestCase):
    """Found by the real-PDM differential (S1): PDM wrote nothing for an item it could not price, while
    Pricing inserted 7 upcharge rows for it. Every upcharge row in the real MDB has a base row."""

    def _upcharge(self, suffix=""):
        return _rec(7.0, "EUR", variant_condition=f"{suffix} 8992=BFK", level="X")

    def test_upcharge_without_a_base_row_is_not_inserted(self):
        mdb = _OptimizedFake(_strict_lists(), linked=[21, 22])
        result = _export_strict(mdb, [self._upcharge("ANNF.0608")], _T)
        self.assertEqual(result["inserted_prices"], 0)
        self.assertEqual(result["skipped_no_base_price"], 1)
        self.assertIn("no base price row", list(result["blocked_reasons"])[0])
        self.assertEqual(mdb.ops, [])

    def test_upcharge_is_inserted_when_the_base_row_already_exists(self):
        base = _eur_row(pid=1, value=5.0, com_VariantCondition="ANNF.0608")
        mdb = _OptimizedFake(_strict_lists(), prices=[base], linked=[21, 22])
        result = _export_strict(mdb, [self._upcharge("ANNF.0608")], _T)
        self.assertEqual((result["inserted_prices"], result["skipped_no_base_price"]), (1, 0))

    def test_upcharge_is_inserted_when_its_base_is_written_by_the_same_export_in_any_order(self):
        base = _rec(5.0, "EUR", variant_condition="ANNF.0608")
        for records in ([base, self._upcharge("ANNF.0608")], [self._upcharge("ANNF.0608"), base]):
            mdb = _OptimizedFake(_strict_lists(), linked=[21, 22])
            result = _export_strict(mdb, records, _T)
            self.assertEqual((result["inserted_prices"], result["skipped_no_base_price"]), (2, 0))

    def test_unpriced_base_does_not_count_as_a_base(self):
        mdb = _OptimizedFake(_strict_lists(), linked=[21, 22])
        result = _export_strict(mdb, [_rec(0.0, "EUR", variant_condition="ANNF.0608"), self._upcharge("ANNF.0608")], _T)
        self.assertEqual((result["inserted_prices"], result["skipped_no_base_price"], result["skipped_zero_price"]), (0, 1, 1))

    def test_existing_upcharge_rows_are_still_updated(self):
        row = _eur_row(pid=2, value=1.0, com_VariantCondition="ANNF.0608 8992=BFK", com_PriceLevelCode="X")
        mdb = _OptimizedFake(_strict_lists(), prices=[row], linked=[21, 22])
        result = _export_strict(mdb, [self._upcharge("ANNF.0608")], _T)
        self.assertEqual((result["updated_prices"], result["skipped_no_base_price"]), (1, 0))


class PriceMdbExportGlobalSurchargeBaseTests(unittest.TestCase):
    """Every real global surcharge row ('ITEM opt=val') has a base global row ('ITEM'): 0 of 16,594
    dangle in lists 21/22. A surcharge whose item has no base is not inserted."""

    def test_surcharge_without_a_base_global_row_is_not_inserted(self):
        mdb = _OptimizedFake(_strict_lists(), linked=[21, 22])
        result = _export_strict(mdb, [_global("ITEM.1 8=AA")], _T)
        self.assertEqual((result["inserted_global_prices"], result["skipped_no_base_price"]), (0, 1))
        self.assertEqual(mdb.ops, [])

    def test_surcharge_is_inserted_with_a_base_written_in_the_same_export_in_any_order_and_case(self):
        for records in ([_global("ITEM.1"), _global("item.1 8=AA")], [_global("item.1 8=AA"), _global("ITEM.1")]):
            mdb = _OptimizedFake(_strict_lists(), linked=[21, 22])
            result = _export_strict(mdb, records, _T)
            self.assertEqual((result["inserted_global_prices"], result["skipped_no_base_price"]), (2, 0))

    def test_surcharge_is_inserted_when_the_base_row_exists_in_the_mdb(self):
        base = {"com_GlobalPriceID": 9, "com_PackageID": 1, "com_PriceListID": 21, "com_VariantCondition": "ITEM.1",
                "com_PriceLevelCode": "X", "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 1.0, "com_TextID": 88}
        mdb = _OptimizedFake(_strict_lists(), globals_=[base], linked=[21, 22],
                             texts=[{"com_TextID": 88, "com_TextName": "8"}])
        result = _export_strict(mdb, [_global("ITEM.1 8=AA")], _T)
        self.assertEqual((result["inserted_global_prices"], result["skipped_no_base_price"]), (1, 0))

    def test_component_parent_condition_matches_and_updates_the_existing_target_row(self):
        item = "RYMPSH.12SW"
        condition = "3848=RYMPSH.12SW_OKG"
        globals_ = [
            {"com_GlobalPriceID": 9, "com_PackageID": 1, "com_PriceListID": 21,
             "com_VariantCondition": item, "com_PriceLevelCode": "X",
             "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 249.0, "com_TextID": 88},
            {"com_GlobalPriceID": 10, "com_PackageID": 1, "com_PriceListID": 21,
             "com_VariantCondition": condition, "com_PriceLevelCode": "X",
             "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 1.0, "com_TextID": 89},
        ]
        mdb = _OptimizedFake(_strict_lists(), globals_=globals_, linked=[21, 22],
                             texts=[{"com_TextID": 88, "com_TextName": item},
                                    {"com_TextID": 89, "com_TextName": "3848"}])
        records = [
            _global(item, 249.0),
            _global(f"{item} 3848=OKG", 52.0, source_item=item, pdm_lookup_code=condition),
        ]

        preview = _export_strict(mdb, records, _T, dry_run=True)
        result = _export_strict(mdb, records, _T)

        self.assertEqual((result["updated_global_prices"], result["inserted_global_prices"]), (1, 0))
        update = next(op for op in mdb.ops if op["op"] == "update" and op["table"] == "tCOMd_GlobalPrice")
        self.assertEqual(update["where"], {"com_GlobalPriceID": 10})
        self.assertEqual(update["set"], {"com_PriceValue": 52.0})
        self.assertEqual(preview["plan_updates"][0]["variant_condition"], condition)
        entry = next(e for e in result["text_rows"] if e["operation"] == "update")
        self.assertEqual(entry["variant_condition"], condition)
        self.assertEqual(entry["text_id"], 89)
        self.assertTrue(result["verified"])

    def test_missing_component_uses_option_suffix_and_second_run_does_not_duplicate(self):
        item = "RYMPSH.12SW"
        from decimal import Decimal
        from repositories.pdm_repository import GlobalOptionPriceRow
        from services.pricing_service import PriceParams, PricingService

        records, _ = PricingService.build_records(
            [], [GlobalOptionPriceRow(
                item, 62547, 3848, "OKG", f"{item}_OKG",
                f"3848={item}_OKG", Decimal("21"), None, Decimal("64"),
            )], {item}, {}, PriceParams(currency="EUR", program_code="revive",
                                       valid_from="2026-10-16"),
        )
        base = {"com_GlobalPriceID": 9, "com_PackageID": 1, "com_PriceListID": 21,
                "com_VariantCondition": item, "com_PriceLevelCode": "X",
                "com_PriceValue": 249.0, "com_TextID": 88}
        texts = [{"com_TextID": 88, "com_TextName": item}]
        mdb = _OptimizedFake(_strict_lists(), globals_=[base], linked=[21, 22], texts=texts)
        first = _export_strict(mdb, records * 2, _T)
        self.assertTrue(first["ok"], first)
        self.assertEqual((first["inserted_global_prices"], first["updated_global_prices"]), (1, 0))
        self.assertTrue(first["verified"])
        inserted = _global_op(mdb)["rows"]
        self.assertEqual(inserted[0]["com_VariantCondition"], f"{item} 3848=OKG")
        self.assertEqual(inserted[0]["com_PriceValue"], 64.0)
        text_op = _texts_op(mdb)
        assert text_op is not None
        text = text_op["rows"][0]
        self.assertEqual((text["com_TextName"], text["com_Text_1_en"]), ("3848", "Surcharge 3848"))
        self.assertEqual(inserted[0]["com_TextID"], text["com_TextID"])

        second_mdb = _OptimizedFake(_strict_lists(), globals_=[base, *inserted],
                                    linked=[21, 22], texts=[*texts, text])
        second = _export_strict(second_mdb, records, _T)
        self.assertEqual((second["inserted_global_prices"], second["updated_global_prices"]), (0, 0))
        self.assertEqual(second_mdb.ops, [])

        records[0].value = 65.0
        third = _export_strict(second_mdb, records, _T)
        self.assertEqual((third["inserted_global_prices"], third["updated_global_prices"]), (0, 1))
        update = second_mdb.ops[0]
        self.assertEqual(update["set"], {"com_PriceValue": 65.0})
        self.assertEqual(update["where"], {"com_GlobalPriceID": inserted[0]["com_GlobalPriceID"]})

    def test_worker_key_precedes_canonical_fallback_and_keeps_list_scope(self):
        item = "RYMPSH.12SW"
        canonical = f"{item} 3848=OKG"
        worker = f"3848={item}_OKG"
        rows = [
            {"com_GlobalPriceID": pid, "com_PackageID": package, "com_PriceListID": lid,
             "com_VariantCondition": condition, "com_PriceValue": value, "com_TextID": 88}
            for pid, package, lid, condition, value in [
                (1, 1, 21, canonical, 1), (2, 1, 21, worker, 2),
                (3, 1, 21, worker, 3), (4, 1, 22, worker, 4),
                (5, 2, 21, worker, 5),
            ]
        ]
        mdb = _OptimizedFake(_strict_lists(), globals_=rows, linked=[21, 22])
        result = _export_strict(mdb, [
            _global(canonical, 64.0, source_item=item, pdm_lookup_code=worker),
        ], _T)
        self.assertEqual((result["updated_global_prices"], result["inserted_global_prices"]), (2, 0))
        self.assertEqual([op["where"] for op in mdb.ops],
                         [{"com_GlobalPriceID": 2}, {"com_GlobalPriceID": 3}])
        self.assertEqual(result["duplicate_matches"], 1)

    def test_special_series_worker_keys_update_existing_rows_without_renaming(self):
        for item, option, code, worker in [
            ("MRFN121HWAP", 9227, "AJ", "AJ"),
            ("AS2EA32AA", 8, "1FD", "1FD#"),
            ("CN132AWAA", 8, "AJ", "AJ"),
            ("GETH.1022FS4W", 9168, "AA", "GETH.1022FS4W 9168=AA"),
            ("RYTRFA.0812SW", 6027, "OKG", "6027=RYTRFA.0812SW_OKG"),
            ("MEMO123", 8, "AA", "MEMO123AA"),
        ]:
            with self.subTest(item=item):
                stored = worker.replace("#", "")
                canonical = f"{item} {option}={code}" if item != "MEMO123" else worker
                row = {"com_GlobalPriceID": 9, "com_PackageID": 1, "com_PriceListID": 21,
                       "com_VariantCondition": stored, "com_PriceValue": 1.0, "com_TextID": 88}
                mdb = _OptimizedFake(_strict_lists(), globals_=[row], linked=[21, 22])
                records = [
                    _global(canonical, 64, source_item=item, pdm_lookup_code=worker),
                ]
                preview = _export_strict(mdb, records, _T, dry_run=True)
                result = _export_strict(mdb, records, _T)
                self.assertEqual((result["updated_global_prices"], result["inserted_global_prices"]), (1, 0))
                self.assertEqual(mdb.ops[0]["set"], {"com_PriceValue": 64.0})
                self.assertEqual(preview["plan_updates"][0]["variant_condition"], stored)

    def test_hash_and_hash_stripped_worker_matches_are_both_updated(self):
        rows = [
            {"com_GlobalPriceID": pid, "com_PackageID": 1, "com_PriceListID": 21,
             "com_VariantCondition": condition, "com_PriceValue": 1.0, "com_TextID": 88}
            for pid, condition in [(9, "1FD#"), (10, "1FD")]
        ]
        mdb = _OptimizedFake(_strict_lists(), globals_=rows, linked=[21, 22])
        result = _export_strict(mdb, [
            _global("AS2EA32AA 8=1FD", 64, source_item="AS2EA32AA", pdm_lookup_code="1FD#"),
        ], _T)
        self.assertEqual((result["updated_global_prices"], result["inserted_global_prices"]), (2, 0))
        self.assertEqual([op["where"] for op in mdb.ops],
                         [{"com_GlobalPriceID": 9}, {"com_GlobalPriceID": 10}])
        self.assertTrue(all(op["set"] == {"com_PriceValue": 64.0} for op in mdb.ops))
