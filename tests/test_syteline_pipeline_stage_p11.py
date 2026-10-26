"""Tests for stage_p11_finish (ExportThread.cs 7033-7483). All fixtures are synthetic."""
from __future__ import annotations

import pytest

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.run_base import ExportRunBase
from core.cancellation import OperationCancelled
from services.syteline_export.pipeline.stage_p11_finish import CSI_HEADERS, P11Mixin


class H(P11Mixin, ExportRunBase):
    """Harness with IoMixin stubs recording calls."""

    def __init__(self, db, **kw):
        super().__init__(db, **kw)
        self.calls = []
        self.fail_xls = False

    def write_data(self, w, data, is_item):
        self.calls.append(("write_data", data, is_item))
        w.write(data)

    def write_to_stream(self, w, data, ctx):
        self.calls.append(("write_to_stream", data, ctx))
        w.write(data)

    def write_price_formula_data(self):
        self.calls.append(("price",))

    def write_product_code_data(self):
        self.calls.append(("code",))

    def convert_to_xls(self):
        self.calls.append(("xls",))
        if self.fail_xls:
            raise RuntimeError("xls boom")


def make(tmp_path, rows1=(), rows2=(), **flags):
    h = H(ScriptedExportDb({"UPDATE Site SET ExtractUser = NULL": 1}))
    h._itemFile = str(tmp_path / "item.txt")
    h._materialFile = str(tmp_path / "mat.txt")
    h.v.arrayList = list(rows1)
    h.v.arrayList2 = list(rows2)
    h.v.text4 = ""
    for k, val in flags.items():
        setattr(h, k, val)
    return h


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def test_non_syteline_header_dedup_and_blank_skip(tmp_path):
    # C# 7343 header; 7346-7358: key = removeNonAlphaNumeric, blank (after Trim) rows not written but key registered
    h = make(tmp_path, rows1=["A-1\tx", "A1\tx", "  ", "B\ty"], rows2=["M-1", "M1", "N"])
    assert h.p11_write_outputs() is None
    assert read(h._itemFile) == "Item\tSuper Prod\tDescription\tStatus\tEurobase\tP/L\tPriceCode\r\n" + "A-1\tx\r\nB\ty\r\n"
    # "A-1\tx" and "A1\tx" have the same alnum key "A1x"? no: 'A-1\tx' -> 'A1x' both -> second skipped
    assert read(h._materialFile).startswith("Parent Item\tFeature\tComponent")
    assert read(h._materialFile).endswith("M-1\r\nN\r\n")
    assert ("write_data", "Item\tSuper Prod\tDescription\tStatus\tEurobase\tP/L\tPriceCode\r\n", False) in h.calls


def test_syteline_plain_header_has_20_feat_columns_in_place(tmp_path):
    h = make(tmp_path, _syteline=True)
    h.p11_write_outputs()
    cols = read(h._itemFile).rstrip("\r\n").split("\t")
    assert len(cols) == 34 + 20 + 31  # 7257-7290, 7291-7297 loop, 7298-7328
    assert cols[0] == "Item" and cols[33] == "Family Code" and cols[34] == "Feat1" and cols[53] == "Feat20"
    assert cols[54] == "Height" and cols[-1] == "Oke Programme"
    assert read(h._itemFile).endswith("\r\n")
    # header written piece by piece: no trailing tab before CRLF (7334)
    assert not read(h._itemFile).rstrip("\r\n").endswith("\t")


def test_syteline_csi_header(tmp_path):
    h = make(tmp_path, _syteline=True, _formatCSI=True)
    h.p11_write_outputs()
    cols = read(h._itemFile).rstrip("\r\n").split("\t")
    assert cols == CSI_HEADERS and len(cols) == 210 and cols[-1] == "C(IsBOMExistedStatic)"


def test_millercad_no_headers_no_xls(tmp_path):
    h = make(tmp_path, rows1=["I1"], rows2=["M1"], _millerCAD=True)
    h.p11_write_outputs()
    assert read(h._itemFile) == "I1\r\n"
    assert read(h._materialFile) == "M1\r\n"  # 7375 header skipped
    assert not any(c[0] in ("price", "code", "xls") for c in h.calls)  # 7407


def test_post_write_order_and_completion(tmp_path):
    events = []
    h = make(tmp_path)
    h._status_callback = events.append
    h._timer_callback = events.append
    h.p11_write_outputs()
    names = [c[0] for c in h.calls if c[0] in ("price", "code", "xls")]
    assert names == ["price", "code", "xls"]
    assert events == ["Exporting to Excel", "stop", "Export Complete"]
    assert h.warnings == ["Export Complete: PDM Data Export Complete"]


def test_completion_message_suppressed_for_service_or_queue(tmp_path):
    h = make(tmp_path, _runAsService=True)
    h.p11_write_outputs()
    assert h.warnings == []
    h = make(tmp_path)
    h._parent.currentExportQueue = ["other"]
    h.p11_write_outputs()
    assert h.warnings == []  # 7426


def test_aborted_skips_xls_and_reports_abort(tmp_path):
    events = []
    h = make(tmp_path, _abortThread=True)
    h._status_callback = events.append
    with pytest.raises(OperationCancelled):
        h.p11_write_outputs()
    assert not any(c[0] in ("price", "code", "xls") for c in h.calls)
    assert events == []
    assert h.warnings == []
    assert not (tmp_path / "item.txt").exists()
    h = make(tmp_path, _abortThread=True, _runAsService=True)
    with pytest.raises(OperationCancelled):
        h.p11_write_outputs()
    assert h.warnings == []


def test_writer_error_is_swallowed_and_recorded(tmp_path):
    # 7360: myWriter1 error is shown and the run continues to writer 2
    h = make(tmp_path)
    h._itemFile = str(tmp_path / "no_such_dir" / "item.txt")
    h.p11_write_outputs()
    assert any(e.startswith("[stage -2] myWriter1 error:") for e in h.errors)
    assert read(h._materialFile).startswith("Parent Item")
    assert ("xls",) in h.calls


def test_exception_in_xls_propagates_to_caller(tmp_path):
    h = make(tmp_path)
    h.fail_xls = True
    with pytest.raises(RuntimeError):
        h.p11_write_outputs()


class FakeWriter:
    def __init__(self):
        self.closed = 0

    def close(self):
        self.closed += 1


def test_on_error_interactive_and_service(tmp_path):
    h = make(tmp_path)
    h.threadStage = "17.2a"
    h.v.text = "SELECT 1"
    events = []
    h._timer_callback = events.append
    h._status_callback = events.append
    try:
        raise ValueError("bad")
    except ValueError as exc:
        h.p11_on_error(exc)
    assert "ValueError: bad" in h.errors[0] and "17.2a" in h.errors[0] and h.errors[0].endswith("SELECT 1")
    assert h.errors[1].endswith("PDM Data Export Aborted")  # 7451
    assert events == ["stop"]
    h = make(tmp_path, _runAsService=True)
    events = []
    h._timer_callback = events.append
    h._status_callback = events.append
    h.p11_on_error(ValueError("x"))
    assert events == ["stop", "Export ERROR"] and len(h.errors) == 1  # 7447


def run_like_integrator(h, body):
    try:
        body()
    except Exception as exc:
        h.p11_on_error(exc)
    finally:
        h.p11_finally()


def test_finally_cleans_up_when_exception_raised_and_releases_once(tmp_path):
    h = make(tmp_path)
    h.v.streamWriter2, h.v.streamWriter3, h.v.streamWriter4 = FakeWriter(), FakeWriter(), FakeWriter()
    h._siteId = 7
    h._extract_user_acquired = True

    def body():
        raise RuntimeError("stage blew up")

    run_like_integrator(h, body)
    assert [w.closed for w in (h.v.streamWriter2, h.v.streamWriter3, h.v.streamWriter4)] == [1, 1, 1]
    releases = [c for c in h.db.calls if "ExtractUser = NULL" in c[1]]
    assert len(releases) == 1
    assert releases[0][0] == "c1" and releases[0][2] == (7,) and releases[0][3] == "42"  # 7464-7466, bound id
    assert "7" not in releases[0][1]
    assert h.threadStage == "42" and h._extract_user_acquired is False
    assert h.db.closed is True
    h.p11_finally()  # a second call must not release again
    assert len([c for c in h.db.calls if "ExtractUser = NULL" in c[1]]) == 1
    assert any("stage blew up" in e for e in h.errors)


def test_finally_does_not_release_when_not_acquired(tmp_path):
    h = make(tmp_path)
    run_like_integrator(h, lambda: None)
    assert h.db.calls == [] and h.db.closed is True


def test_finally_does_not_release_when_other_user_holds_lock(tmp_path):
    h = make(tmp_path)
    h._extract_user_acquired = True
    h.v.text4 = "someone"  # 7460 condition text4 == ""
    h.p11_finally()
    assert h.db.calls == []


def test_finally_release_failure_is_swallowed(tmp_path):
    h = make(tmp_path)
    h._extract_user_acquired = True
    h.db = ScriptedExportDb({})  # unscripted SQL raises AssertionError inside the legacy try/catch (7469)
    h.p11_finally()  # must not raise
    assert h.db.closed is True and any("ExtractUser release failed" in w for w in h.warnings)


def test_finally_tolerates_run_that_died_before_writers_exist(tmp_path):
    h = H(ScriptedExportDb({}))
    h.p11_finally()
    assert h.db.closed is True
