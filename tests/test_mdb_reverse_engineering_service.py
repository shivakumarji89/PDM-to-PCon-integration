import tempfile
import unittest
from pathlib import Path

from services.mdb_reverse_engineering_service import (
    MdbReverseEngineeringService,
    STRUCTURAL_TABLES,
)


class FakeMDB:
    def __init__(self):
        self.calls = []
        self.rows = {
            "tCOMd_Package": [{"com_PackageID": 1, "reg_ProgramCode": "NEVI"}],
            "tCOMd_ComGroup": [{"com_ComGroupID": 2, "com_ComGroupCode": "NEVI"}],
            "tCOMd_Article": [
                {"com_ArticleID": 10, "com_ArticleCode": "A100"},
                {"com_ArticleID": 11, "com_ArticleCode": "A200"},
            ],
        }

    def read_table(self, path, sql):
        self.calls.append((Path(path), sql))
        table = sql.split("[")[-1].split("]")[0]
        return self.rows.get(table, [])


class FakeContext:
    def __init__(self):
        self.mdb_service = FakeMDB()


class MdbReverseEngineeringServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mdb = Path(self.temp_dir.name) / "pcr_data_com_ocd.mdb"
        self.mdb.touch()
        self.context = FakeContext()
        self.service = MdbReverseEngineeringService(self.context)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_read_uses_shared_mdb_service_and_excludes_prices_by_default(self):
        result = self.service.read(self.mdb)

        self.assertEqual(result.package["reg_ProgramCode"], "NEVI")
        self.assertEqual(result.com_group["com_ComGroupCode"], "NEVI")
        self.assertEqual(result.first("tCOMd_Article")["com_ArticleCode"], "A100")
        self.assertNotIn("tCOMd_Price", result.tables)
        self.assertEqual(set(result.tables), set(STRUCTURAL_TABLES))
        self.assertTrue(self.context.mdb_service.calls)

    def test_read_can_explicitly_include_prices(self):
        result = self.service.read(self.mdb, include_prices=True)

        self.assertIn("tCOMd_Price", result.tables)
        self.assertIn("tCOMd_GlobalPrice", result.tables)

    def test_read_rejects_unknown_tables(self):
        with self.assertRaisesRegex(ValueError, "Unsupported MDB table"):
            self.service.read(self.mdb, tables=["tCOMd_NotARealTable"])

    def test_missing_mdb_is_non_throwing(self):
        result = self.service.read(Path(self.temp_dir.name) / "missing.mdb")

        self.assertEqual(result.tables, {})
        self.assertTrue(any("MDB not found" in note for note in result.notes))


if __name__ == "__main__":
    unittest.main()
