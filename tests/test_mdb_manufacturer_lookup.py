"""Manufacturer lookup for both OCD template layouts (Package-level and ComGroup-level)."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.mdb_manufacturer import (
    LAYOUT_COMGROUP, LAYOUT_PACKAGE, ManufacturerLookupError,
    read_package_manufacturer, resolve_package_manufacturer)
from services.mdb_service import MDBService, _PS32


# ------------------------------------------------------------ pure logic

class _FakeSvc:
    def __init__(self, manufacturers, fail=False):
        self.manufacturers, self.fail = manufacturers, fail

    def read_tables(self, _mdb, queries):
        if self.fail:
            raise RuntimeError("query failed")
        sql = queries["manufacturer"]
        mid = int(sql.rsplit("=", 1)[1])
        return {"manufacturer": [{"reg_ManufacturerCode": c} for i, c in self.manufacturers if i == mid]}


def _resolve(packages, groups, manufacturers=((1, "hmx"), (2, "knl"))):
    return resolve_package_manufacturer(_FakeSvc(manufacturers), "x.mdb", packages, groups)


def test_layout_a_package_column():
    got = _resolve([{"com_PackageID": 1, "com_ComGroupID": 5, "com_ManufacturerID": 2}], [])
    assert (got.manufacturer_code, got.layout, got.comgroup_id) == ("knl", LAYOUT_PACKAGE, 5)


def test_layout_a_wins_over_groups():
    got = _resolve([{"com_PackageID": 1, "com_ComGroupID": 5, "com_ManufacturerID": 1}],
                   [{"com_ComGroupID": 5, "com_ManufacturerID": 2}])
    assert got.manufacturer_code == "hmx"


def test_layout_b_comgroup_column_maps_each_group_to_its_manufacturer():
    groups = [{"com_ComGroupID": 5, "com_ManufacturerID": 1}, {"com_ComGroupID": 6, "com_ManufacturerID": 2}]
    first = _resolve([{"com_PackageID": 1, "com_ComGroupID": 5}], groups)
    second = _resolve([{"com_PackageID": 2, "com_ComGroupID": 6}], groups)
    assert (first.manufacturer_code, first.layout) == ("hmx", LAYOUT_COMGROUP)
    assert second.manufacturer_code == "knl"        # the package's own group, never groups[0]


def test_layout_a_null_value_keeps_the_default_behaviour():
    got = _resolve([{"com_PackageID": 1, "com_ComGroupID": 5, "com_ManufacturerID": None}], [])
    assert got.manufacturer_code is None and got.layout == LAYOUT_PACKAGE


def test_no_manufacturer_column_anywhere_is_a_clear_error():
    with pytest.raises(ManufacturerLookupError, match="no com_ManufacturerID"):
        _resolve([{"com_PackageID": 1, "com_ComGroupID": 5}], [{"com_ComGroupID": 5}])


def test_missing_comgroup_relationship_is_a_clear_error():
    groups = [{"com_ComGroupID": 9, "com_ManufacturerID": 1}]
    with pytest.raises(ManufacturerLookupError, match="not in tCOMd_ComGroup"):
        _resolve([{"com_PackageID": 1, "com_ComGroupID": 5}], groups)
    with pytest.raises(ManufacturerLookupError, match="no com_ComGroupID"):
        _resolve([{"com_PackageID": 1, "com_ComGroupID": None}], groups)


def test_ambiguous_comgroup_and_null_group_manufacturer_are_errors():
    dup = [{"com_ComGroupID": 5, "com_ManufacturerID": 1}, {"com_ComGroupID": 5, "com_ManufacturerID": 2}]
    with pytest.raises(ManufacturerLookupError, match="ambiguous"):
        _resolve([{"com_PackageID": 1, "com_ComGroupID": 5}], dup)
    with pytest.raises(ManufacturerLookupError, match="no com_ManufacturerID value"):
        _resolve([{"com_PackageID": 1, "com_ComGroupID": 5}], [{"com_ComGroupID": 5, "com_ManufacturerID": None}])


def test_dangling_manufacturer_id_and_empty_package_are_errors():
    with pytest.raises(ManufacturerLookupError, match="missing from tCOMd_Manufacturer"):
        _resolve([{"com_PackageID": 1, "com_ManufacturerID": 99}], [])
    with pytest.raises(ManufacturerLookupError, match="tCOMd_Package is empty"):
        _resolve([], [])


def test_manufacturer_query_failure_is_not_treated_as_missing_data():
    with pytest.raises(ManufacturerLookupError, match="cannot be read"):
        resolve_package_manufacturer(
            _FakeSvc([], fail=True), "x.mdb", [{"com_PackageID": 1, "com_ManufacturerID": 1}], [])


# -------------------------------------------------- real ACE bridge, disposable MDBs

def _ps(script):
    return subprocess.run([_PS32, "-NoProfile", "-Command", script], capture_output=True, text=True)


def _build(path: Path, *, layout: str, with_group_table: bool = True) -> MDBService:
    made = _ps("$ErrorActionPreference='Stop'; $c=New-Object -ComObject ADOX.Catalog; "
               f"$c.Create('Provider=Microsoft.ACE.OLEDB.16.0;Data Source={path};'); $c.ActiveConnection.Close()")
    if made.returncode:
        pytest.skip("32-bit ACE provider is not installed")
    pkg_extra = ", com_ManufacturerID LONG" if layout == "A" else ""
    grp_extra = ", com_ManufacturerID LONG" if layout == "B" else ""
    ddl = [
        "CREATE TABLE tCOMd_Manufacturer (com_ManufacturerID COUNTER PRIMARY KEY, reg_ManufacturerCode TEXT(20))",
        f"CREATE TABLE tCOMd_Package (com_PackageID COUNTER PRIMARY KEY, com_ComGroupID LONG{pkg_extra})",
    ]
    if with_group_table:
        ddl.append(f"CREATE TABLE tCOMd_ComGroup (com_ComGroupID COUNTER PRIMARY KEY, com_ComGroupCode TEXT(20){grp_extra})")
    setup = "; ".join("$c.Execute('" + s + "') | Out-Null" for s in ddl)
    done = _ps("$ErrorActionPreference='Stop'; $c=New-Object -ComObject ADODB.Connection; "
               f"$c.Open('Provider=Microsoft.ACE.OLEDB.16.0;Data Source={path};'); {setup}; $c.Close()")
    assert done.returncode == 0, done.stderr
    svc = MDBService(SimpleNamespace())
    seed = [{"op": "insert", "table": "tCOMd_Manufacturer", "rows": [
        {"com_ManufacturerID": 1, "reg_ManufacturerCode": "hmx"},
        {"com_ManufacturerID": 2, "reg_ManufacturerCode": "knl"}]}]
    if layout == "A":
        seed.append({"op": "insert", "table": "tCOMd_Package", "rows": [
            {"com_PackageID": 1, "com_ComGroupID": 10, "com_ManufacturerID": 2}]})
        if with_group_table:
            seed.append({"op": "insert", "table": "tCOMd_ComGroup", "rows": [
                {"com_ComGroupID": 10, "com_ComGroupCode": "G"}]})
    else:
        seed.append({"op": "insert", "table": "tCOMd_Package", "rows": [
            {"com_PackageID": 7, "com_ComGroupID": 11}]})
        if with_group_table:
            seed.append({"op": "insert", "table": "tCOMd_ComGroup", "rows": [
                {"com_ComGroupID": 10, "com_ComGroupCode": "G1", "com_ManufacturerID": 1},
                {"com_ComGroupID": 11, "com_ComGroupCode": "G2", "com_ManufacturerID": 2}]})
    batch = svc.execute_batch(path, seed)
    assert batch.ok, batch.first_error()
    return svc


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_real_mdb_layout_a(tmp_path):
    mdb = tmp_path / "a.mdb"
    svc = _build(mdb, layout="A")
    before = _sha(mdb)
    got = read_package_manufacturer(svc, mdb)
    assert (got.manufacturer_code, got.layout, got.package["com_PackageID"]) == ("knl", LAYOUT_PACKAGE, 1)
    assert _sha(mdb) == before                      # lookup never writes


def test_real_mdb_layout_b_uses_the_packages_own_group(tmp_path):
    mdb = tmp_path / "b.mdb"
    svc = _build(mdb, layout="B")
    before = _sha(mdb)
    got = read_package_manufacturer(svc, mdb)
    assert (got.manufacturer_code, got.layout) == ("knl", LAYOUT_COMGROUP)   # group 11 -> mfr 2, not group 10
    assert got.comgroup_id == 11 and got.package["com_PackageID"] == 7
    assert _sha(mdb) == before


def test_real_mdb_sql_failure_is_reported_as_schema_error_not_empty(tmp_path):
    mdb = tmp_path / "nogroup.mdb"
    svc = _build(mdb, layout="B", with_group_table=False)
    with pytest.raises(ManufacturerLookupError, match="schema is not usable"):
        read_package_manufacturer(svc, mdb)
