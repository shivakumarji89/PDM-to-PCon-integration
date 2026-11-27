"""Streaming-output tests for ``resources/mdb_bridge.ps1`` (real 32-bit ACE bridge).

Only newly created files under pytest's tmp_path are opened.
"""
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from services.mdb_service import MDBService, _BRIDGE, _PS32


@pytest.fixture
def mdb(tmp_path):
    if not Path(_PS32).is_file():
        pytest.skip("32-bit Windows PowerShell / ACE integration unavailable")
    path = tmp_path / "stream.mdb"
    script = (
        "$ErrorActionPreference = 'Stop'; "
        "$catalog = New-Object -ComObject ADOX.Catalog; "
        f"$catalog.Create(\"Provider=Microsoft.ACE.OLEDB.16.0;Data Source={path};\"); "
        "$catalog.ActiveConnection.Close()"
    )
    created = subprocess.run([_PS32, "-NoProfile", "-Command", script], capture_output=True, text=True)
    if created.returncode:
        if any(m in created.stderr.lower() for m in ("provider cannot be found", "class not registered", "80040154")):
            pytest.skip("32-bit ACE provider is not installed")
        pytest.fail(f"Could not create disposable ACE MDB: {created.stderr}")
    svc = MDBService(SimpleNamespace())
    return svc, path


def _run_ddl(svc, path):
    # DDL is not a bridge op, so use ADODB directly through the same 32-bit host.
    script = (
        "$ErrorActionPreference='Stop';$c=New-Object -ComObject ADODB.Connection;"
        f"$c.Open('Provider=Microsoft.ACE.OLEDB.16.0;Data Source={path};');"
        "$c.Execute('CREATE TABLE t (id LONG, txt TEXT(255), n DOUBLE, d DATETIME, m CURRENCY, b YESNO)')|Out-Null;"
        "$c.Execute('CREATE TABLE e (id LONG)')|Out-Null;$c.Close()"
    )
    done = subprocess.run([_PS32, "-NoProfile", "-Command", script], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


@pytest.fixture
def populated(mdb):
    svc, path = mdb
    _run_ddl(svc, path)
    return svc, path


def test_streamed_contract_and_value_semantics(populated):
    svc, path = populated
    tricky = 'quote " back\\slash é中 <tag> & \'apos\' \n newline'
    batch = svc.execute_batch(path, [
        {"op": "insert", "table": "t", "rows": [
            {"id": 1, "txt": tricky, "n": 1.5, "d": "#2024-03-05 06:07:08#", "m": 12.25, "b": True},
            {"id": 2, "txt": None, "n": None, "d": None, "m": None, "b": False},
        ]},
        {"op": "query", "sql": "SELECT * FROM t ORDER BY id"},
        {"op": "query", "sql": "SELECT * FROM t WHERE id = 1"},       # single row -> array
        {"op": "query", "sql": "SELECT * FROM e"},                      # empty -> []
        {"op": "update", "table": "t", "set": {"n": 2}, "where": {"id": 1}},
        {"op": "query", "sql": "SELECT n FROM t WHERE id = 1"},
    ])
    assert batch.ok, batch.first_error()
    ins, allrows, one, empty, upd, after = batch.results
    assert ins.inserted == 2 and upd.updated == 1
    assert [r["id"] for r in allrows.rows] == [1, 2]
    assert list(allrows.rows[0]) == ["id", "txt", "n", "d", "m", "b"]  # column order kept
    assert allrows.rows[0]["txt"] == tricky
    assert allrows.rows[0]["n"] == 1.5 and allrows.rows[0]["m"] == 12.25
    assert allrows.rows[0]["b"] is True
    assert str(allrows.rows[0]["d"]).startswith("/Date(")  # PowerShell 5.1 JSON date format
    assert allrows.rows[1]["txt"] is None and allrows.rows[1]["d"] is None
    assert len(one.rows) == 1 and one.rows[0]["id"] == 1
    assert empty.rows == []
    assert after.rows[0]["n"] == 2


def test_raw_json_shape(populated, tmp_path):
    svc, path = populated
    in_p, out_p = tmp_path / "in.json", tmp_path / "out.json"
    in_p.write_text(json.dumps({"mdb": str(path), "transaction": False, "ops": [
        {"op": "insert", "table": "t", "rows": [{"id": 7, "d": "#2020-01-02 03:04:05#"}]},
        {"op": "query", "sql": "SELECT id, d FROM t"},
        {"op": "query", "sql": "SELECT * FROM e"},
        {"op": "query", "sql": "SELECT * FROM nonexistent_table"},
    ]}), encoding="utf-8")
    subprocess.run([_PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(_BRIDGE),
                    "-InputPath", str(in_p), "-OutputPath", str(out_p)], capture_output=True, text=True)
    data = json.loads(out_p.read_text(encoding="utf-8-sig"))
    assert data["ok"] is False
    ins, q, empty, bad = data["results"]
    assert ins["inserted"] == 1 and ins["ok"] is True and "rows" not in ins
    assert q["rows"][0]["d"] == "/Date(%d)/" % 1577934245000 or str(q["rows"][0]["d"]).startswith("\\/Date(") or "Date(" in q["rows"][0]["d"]
    assert empty["rows"] == []
    assert bad["ok"] is False and bad["error"] and "rows" not in bad
    assert not list(tmp_path.glob("out.json.partial"))


def test_streaming_failure_leaves_no_output(populated, tmp_path):
    svc, path = populated
    in_p = tmp_path / "in.json"
    in_p.write_text(json.dumps({"mdb": str(path), "ops": [{"op": "query", "sql": "SELECT * FROM t"}]}),
                    encoding="utf-8")
    out_p = tmp_path / "missing_dir" / "out.json"  # cannot be written
    proc = subprocess.run([_PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(_BRIDGE),
                           "-InputPath", str(in_p), "-OutputPath", str(out_p)], capture_output=True, text=True)
    assert proc.returncode != 0
    assert not out_p.exists() and not Path(str(out_p) + ".partial").exists()
    assert "failed to write response" in proc.stderr


def test_large_result_does_not_oom(populated):
    """~160k wide rows via a cross join: the old aggregate ConvertTo-Json ran out of memory here."""
    svc, path = populated
    pad = "x" * 120
    batch = svc.execute_batch(path, [
        {"op": "insert", "table": "t", "rows": [{"id": i, "txt": pad} for i in range(400)]},
    ], transaction=True)
    assert batch.ok, batch.first_error()
    big = svc.execute_batch(path, [{"op": "query", "sql": (
        "SELECT a.id AS aid, b.id AS bid, a.txt AS atxt, b.txt AS btxt, a.n, b.n AS bn "
        "FROM t AS a, t AS b")}])
    assert big.ok, big.first_error()
    assert len(big.results[0].rows) == 400 * 400
