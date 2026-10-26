"""Deterministic cancellation boundaries for published-package maintenance."""
from __future__ import annotations

import csv
import shutil
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope, checkpoint
from services import price_update_service as prices
from services.mdb_service import MDBBatchResult, MDBOpResult
from services.price_update_service import PriceUpdateService
from services.version_update_service import SeriesVersion, VersionUpdateService


@pytest.fixture
def workspace():
    # All test data stays in the project, including staged MDBs and backups.
    path = Path.cwd() / f".workflow-cancellation-{uuid4().hex}"
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _service(mdb=None):
    return PriceUpdateService(SimpleNamespace(
        mdb_service=mdb,
        price_list_service=SimpleNamespace(_day_before=lambda _: "20251231"),
    ))


def _package(path):
    path.mkdir()
    row = ["P", "EURO_2025", "ABC", "", "", "B", "", "", "10", "", "EUR",
           "20250101", "99991231"]
    with (path / "xocd_price.csv").open("w", newline="") as fh:
        csv.writer(fh, delimiter=";").writerow(row)
    (path / "xocd_pricelists.csv").write_text("EURO_2025;EURO_2025\n")
    return path


def _contents(path):
    return {p.name: p.read_bytes() for p in path.iterdir()}


def test_xocd_cancel_during_lookup_preserves_both_files_and_retry(workspace):
    pkg = _package(workspace / "Series")
    original = _contents(pkg)
    token = CancellationToken()

    def lookup(*_):
        token.request_cancel()
        return 25

    with cancellation_scope(token), pytest.raises(OperationCancelled):
        _service().roll_over_package_xocd(pkg, "20260101", "2026", lookup)
    assert _contents(pkg) == original

    result = _service().roll_over_package_xocd(pkg, "20260101", "2026", lambda *_: 25)
    assert result.applied
    assert result.lists[0].priced == 1
    assert result.lists[0].changed == 1
    assert b"EURO_2026" in (pkg / "xocd_price.csv").read_bytes()
    assert b"EURO_2026" in (pkg / "xocd_pricelists.csv").read_bytes()
    again = _service().roll_over_package_xocd(pkg, "20260101", "2026")
    assert again.lists[0].old_list == again.lists[0].new_list
    assert len(list(pkg.iterdir())) == 2


def test_xocd_cancel_while_staging_removes_sidecars(workspace, monkeypatch):
    pkg = _package(workspace / "Series")
    original = _contents(pkg)
    token = CancellationToken()
    write = PriceUpdateService._write_rows

    def cancel_after_first_stage(path, rows):
        write(path, rows)
        token.request_cancel()

    monkeypatch.setattr(PriceUpdateService, "_write_rows", staticmethod(cancel_after_first_stage))
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        _service().roll_over_package_xocd(pkg, "20260101", "2026")
    assert _contents(pkg) == original


def test_xocd_replacement_failure_rolls_back_package(workspace, monkeypatch):
    pkg = _package(workspace / "Series")
    original = _contents(pkg)
    replace = prices.os.replace

    def fail_price(source, dest):
        if str(source).endswith(".stage") and Path(dest).name == "xocd_price.csv":
            raise OSError("locked price file")
        replace(source, dest)

    monkeypatch.setattr(prices.os, "replace", fail_price)
    result = _service().roll_over_package_xocd(pkg, "20260101", "2026")
    assert "locked price file" in result.error
    assert not result.applied
    assert _contents(pkg) == original


def test_cancel_during_multifile_publication_finishes_current_package(workspace, monkeypatch):
    first = _package(workspace / "First")
    second = _package(workspace / "Second")
    original_second = _contents(second)
    token = CancellationToken()
    replace = prices.os.replace

    def cancel_between_files(source, dest):
        replace(source, dest)
        if Path(dest) == first / "xocd_pricelists.csv":
            token.request_cancel()

    monkeypatch.setattr(prices.os, "replace", cancel_between_files)
    with cancellation_scope(token), pytest.raises(OperationCancelled, match=r"1 package\(s\) committed"):
        _service().run_batch(workspace, False, "20260101", "2026", packages=[first, second])
    assert b"EURO_2026" in (first / "xocd_price.csv").read_bytes()
    assert b"EURO_2026" in (first / "xocd_pricelists.csv").read_bytes()
    assert _contents(second) == original_second


class _Bridge:
    def __init__(self, token=None, cancel_call=0, fail_call=0):
        self.token, self.cancel_call, self.fail_call = token, cancel_call, fail_call
        self.calls = []

    def is_available(self):
        return True

    def execute_batch(self, path, ops, transaction=False):
        self.calls.append((Path(path), ops, transaction))
        assert transaction
        Path(path).write_bytes(b"updated")
        if len(self.calls) == self.cancel_call:
            self.token.request_cancel()
        ok = len(self.calls) != self.fail_call
        return MDBBatchResult(ok=ok, results=[
            MDBOpResult(op="update", ok=ok, error=None if ok else "failed")])


@pytest.mark.parametrize("cancel_call", [1, 2])
def test_version_cancel_discards_staged_pair_and_retry(workspace, cancel_call):
    ocd, odb = workspace / "ocd.mdb", workspace / "odb.mdb"
    ocd.write_bytes(b"original ocd")
    odb.write_bytes(b"original odb")
    token = CancellationToken()
    bridge = _Bridge(token, cancel_call)
    svc = VersionUpdateService(SimpleNamespace(mdb_service=bridge))
    sv = SeriesVersion(str(workspace), program="P", ocd_path=str(ocd), odb_path=str(odb))
    original = _contents(workspace)
    with cancellation_scope(token), pytest.raises(OperationCancelled, match="0 series committed"):
        svc.update([sv], 1, 2, 3)
    assert _contents(workspace) == original
    assert all(path not in (ocd, odb) for path, _, _ in bridge.calls)
    assert all(len(ops) == 2 for _, ops, _ in bridge.calls)

    bridge.cancel_call = 0
    result = svc.update([sv], 1, 2, 3)[0]
    assert result.ocd_updated and result.odb_updated and result.error is None
    assert _contents(workspace) == {"ocd.mdb": b"updated", "odb.mdb": b"updated"}


def test_version_failed_second_database_leaves_pair_unchanged(workspace):
    ocd, odb = workspace / "ocd.mdb", workspace / "odb.mdb"
    ocd.write_bytes(b"ocd")
    odb.write_bytes(b"odb")
    bridge = _Bridge(fail_call=2)
    svc = VersionUpdateService(SimpleNamespace(mdb_service=bridge))
    sv = SeriesVersion(str(workspace), ocd_path=str(ocd), odb_path=str(odb))
    result = svc.update([sv], 2, 3, 4)[0]
    assert result.error
    assert not result.ocd_updated and not result.odb_updated
    assert _contents(workspace) == {"ocd.mdb": b"ocd", "odb.mdb": b"odb"}


def test_staged_price_mdb_transaction_cancel_preserves_final(workspace):
    path = workspace / "prices.mdb"
    path.write_bytes(b"original")
    token = CancellationToken()
    bridge = _Bridge(token, cancel_call=1)
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        prices._write_mdb(bridge, path, [{"op": "delete"}])
    assert _contents(workspace) == {"prices.mdb": b"original"}
    bridge.cancel_call = 0
    assert prices._write_mdb(bridge, path, [{"op": "delete"}]).ok
    assert _contents(workspace) == {"prices.mdb": b"updated"}


def test_query_cancel_on_return_stops_before_next_database(workspace):
    folder = workspace / "Series"
    folder.mkdir()
    (folder / "pcr_data_com_ocd.mdb").touch()
    (folder / "pcr_data_geo_odb.mdb").touch()
    token = CancellationToken()
    calls = []

    def read(*args):
        calls.append(args)
        token.request_cancel()
        return []

    svc = VersionUpdateService(SimpleNamespace(mdb_service=SimpleNamespace(read_table=read)))
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        svc.read_series([folder])
    assert len(calls) == 1


@pytest.mark.parametrize("operation", ["notes", "base", "increments", "warm_base", "warm_increments"])
@pytest.mark.parametrize("raise_in_query", [False, True])
def test_pdm_cancellation_not_swallowed(operation, raise_in_query, monkeypatch):
    from repositories import pdm_repository

    token = CancellationToken()
    closed = []

    def query(*_):
        token.request_cancel()
        if raise_in_query:
            checkpoint()
        return []

    repo = SimpleNamespace(
        get_connection=lambda: SimpleNamespace(close=lambda: closed.append(True)),
        fetch_item_notes=query, fetch_item_base_prices=query,
        fetch_item_option_increment_prices=query,
    )
    monkeypatch.setattr(pdm_repository, "PDMRepository", lambda _: repo)
    svc = _service()
    lookup = svc.make_pdm_lookup("01-Jan-2026", 1)
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        if operation == "notes":
            svc._fetch_notes(["ABC"])
        elif operation == "base":
            lookup("EUR", False, "ABC", "", "B")
        elif operation == "increments":
            lookup("EUR", False, "ABC", "OPT=CODE", "B")
        else:
            getattr(lookup, operation)("EUR", ["ABC"])
    lookup.close()
    assert closed


def test_base_check_cancels_between_packages_without_pdm_query(workspace, monkeypatch):
    packages = [_package(workspace / "First"), _package(workspace / "Second")]
    token = CancellationToken()
    svc = _service()
    reads = []
    monkeypatch.setattr(svc, "_discover_packages", lambda *_: packages)
    monkeypatch.setattr(svc, "_base_pairs_xocd", lambda pkg: reads.append(pkg) or [])
    monkeypatch.setattr(svc, "_fetch_notes", lambda _: pytest.fail("PDM must not start"))

    def progress(*_):
        token.request_cancel()

    with cancellation_scope(token), pytest.raises(OperationCancelled):
        svc.build_base_length_registry(workspace, progress=progress)
    assert len(reads) <= 1


def test_registry_cancel_during_write_keeps_existing_file(workspace, monkeypatch):
    path = workspace / "registry.csv"
    path.write_text("Program;Item;Override_Length\nP;ABC;3\n")
    original = path.read_bytes()
    token = CancellationToken()
    svc = _service()
    dict_writer = prices.csv.DictWriter

    def cancellable_writer(*args, **kwargs):
        writer = dict_writer(*args, **kwargs)

        def row(data):
            writer.writerow(data)
            token.request_cancel()

        return SimpleNamespace(writeheader=writer.writeheader, writerow=row)

    monkeypatch.setattr(prices.csv, "DictWriter", cancellable_writer)
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        svc.write_base_length_registry(path, [{"Program": "P", "Item": "ABC"}])
    assert _contents(workspace) == {"registry.csv": original}


def test_registry_publication_closes_cancellation_window(workspace, monkeypatch):
    path = workspace / "registry.csv"
    token = CancellationToken()
    replace = prices.os.replace
    requests = []

    def publish(source, target):
        requests.append(token.request_cancel())
        replace(source, target)

    monkeypatch.setattr(prices.os, "replace", publish)
    with cancellation_scope(token):
        _service().write_base_length_registry(path, [{"Program": "P", "Item": "ABC"}])
        token.checkpoint()
    assert requests == [False]
    assert path.is_file()
    assert len(list(workspace.iterdir())) == 1


class _RolloverBridge(_Bridge):
    def read_table(self, _path, sql):
        if "SELECT MAX" in sql:
            return [{"m": 1}]
        if "com_PriceValidFrom, com_PriceValidTo FROM" in sql:
            return [{
                "com_PriceListID": 1, "com_PriceListLabel": "EURO_2025",
                "sys_ISOCurrencyCode": "EUR", "com_PriceValidFrom": "20250101",
                "com_PriceValidTo": "99991231",
            }]
        if sql == "SELECT com_PriceListID FROM tCOMd_PriceList2":
            return [{"com_PriceListID": 1}]
        if "SELECT p.com_ArticleID," in sql:
            return [{
                "com_ArticleID": 1, "com_ArticleCode": "ABC", "com_PriceValue": 10,
                "com_PriceLevelCode": "B", "com_VariantCondition": "",
            }]
        return []


def test_rollover_mdb_cancel_at_transaction_return_and_retry(workspace):
    path = workspace / "pcr_data_com_ocd.mdb"
    path.write_bytes(b"original")
    token = CancellationToken()
    bridge = _RolloverBridge(token, cancel_call=1)
    svc = _service(bridge)
    with cancellation_scope(token), pytest.raises(OperationCancelled, match=r"0 package\(s\) committed"):
        svc.run_batch(workspace, True, "20260101", "2026", packages=[path])
    assert _contents(workspace) == {path.name: b"original"}
    assert bridge.calls[0][0] != path
    assert bridge.calls[0][2]
    bridge.cancel_call = 0
    result = svc.run_batch(workspace, True, "20260101", "2026", packages=[path])
    assert result.ok and result.packages[0].applied
    assert result.packages[0].lists[0].rows == 1
    assert _contents(workspace) == {path.name: b"updated"}


def test_version_cancel_after_first_series_reports_committed_count(workspace):
    paths = [workspace / "one.mdb", workspace / "two.mdb"]
    for path in paths:
        path.write_bytes(b"original")
    token = CancellationToken()
    bridge = _Bridge()
    svc = VersionUpdateService(SimpleNamespace(mdb_service=bridge))
    series = [SeriesVersion(str(workspace), ocd_path=str(path)) for path in paths]

    def progress(*_):
        token.request_cancel()

    with cancellation_scope(token), pytest.raises(OperationCancelled, match="1 series committed"):
        svc.update(series, 1, 2, 3, progress)
    assert _contents(workspace) == {"one.mdb": b"updated", "two.mdb": b"original"}


def test_special_scan_cancellation_closes_connection(monkeypatch):
    from repositories import pdm_repository

    token = CancellationToken()
    closed = []

    def read(*_):
        token.request_cancel()
        return []

    repo = SimpleNamespace(
        get_connection=lambda: SimpleNamespace(close=lambda: closed.append(True)))
    monkeypatch.setattr(pdm_repository, "PDMRepository", lambda _: repo)
    svc = _service(SimpleNamespace(read_table=read))
    monkeypatch.setattr(svc, "load_special_map", lambda: {})
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        svc.scan_special_articles(["one.mdb"], "01-Jan-2026", 1)
    assert closed == [True]


def test_special_reprice_cancellation_closes_lookup_without_writes(monkeypatch):
    token = CancellationToken()
    closed = []

    def lookup(*_):
        token.request_cancel()
        return 25

    lookup.close = lambda: closed.append(True)

    def read(_path, sql):
        if "FROM tCOMd_PriceList2" in sql:
            return [{
                "com_PriceListID": 1, "com_PriceListLabel": "EURO_2026",
                "com_PriceValidTo": "99991231", "sys_ISOCurrencyCode": "EUR",
            }]
        return [{"com_PriceID": 1, "com_ArticleCode": "ABC_X", "com_PriceValue": 10}]

    svc = _service(SimpleNamespace(
        is_available=lambda: True, read_table=read,
        execute_batch=lambda *_args, **_kwargs: pytest.fail("must not write")))
    monkeypatch.setattr(svc, "make_pdm_lookup", lambda *_args, **_kwargs: lookup)
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        svc.apply_special_articles("one.mdb", {"ABC_X": "ABC"}, "01-Jan-2026", 1)
    assert closed == [True]
