from pathlib import Path

import pytest

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


def test_read_uses_shared_mdb_service_and_excludes_prices_by_default(tmp_path):
    mdb = tmp_path / "pcr_data_com_ocd.mdb"
    mdb.touch()
    context = FakeContext()
    service = MdbReverseEngineeringService(context)

    result = service.read(mdb)

    assert result.package["reg_ProgramCode"] == "NEVI"
    assert result.com_group["com_ComGroupCode"] == "NEVI"
    assert result.first("tCOMd_Article")["com_ArticleCode"] == "A100"
    assert "tCOMd_Price" not in result.tables
    assert set(result.tables) == set(STRUCTURAL_TABLES)


def test_read_can_explicitly_include_prices(tmp_path):
    mdb = tmp_path / "pcr_data_com_ocd.mdb"
    mdb.touch()
    context = FakeContext()
    service = MdbReverseEngineeringService(context)

    result = service.read(mdb, include_prices=True)

    assert "tCOMd_Price" in result.tables
    assert "tCOMd_GlobalPrice" in result.tables


def test_read_rejects_unknown_tables(tmp_path):
    mdb = tmp_path / "pcr_data_com_ocd.mdb"
    mdb.touch()
    service = MdbReverseEngineeringService(FakeContext())

    with pytest.raises(ValueError, match="Unsupported MDB table"):
        service.read(mdb, tables=["tCOMd_NotARealTable"])


def test_missing_mdb_is_non_throwing(tmp_path):
    service = MdbReverseEngineeringService(FakeContext())

    result = service.read(tmp_path / "missing.mdb")

    assert result.tables == {}
    assert any("MDB not found" in note for note in result.notes)
