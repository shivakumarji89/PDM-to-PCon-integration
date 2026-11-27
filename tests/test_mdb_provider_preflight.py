"""Provider preflight for the 32-bit ACE OLEDB MDB bridge (no real ACE/MDB needed)."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from services import mdb_service as mod
from services.mdb_reverse_engineering_service import MdbReverseEngineeringService
from services import mdb_manufacturer as manufacturer_mod
from services.mdb_export_session_service import ExportSessionError, MdbExportSessionService
from services.mdb_service import (
    MDBProviderUnavailableError,
    MDBService,
    PROVIDER_MISSING_MESSAGE,
)


def _completed(code):
    return subprocess.CompletedProcess(args=[], returncode=code, stdout="", stderr="")


class ProviderPreflightTests(unittest.TestCase):
    def setUp(self):
        MDBService._provider_ok = False
        self.addCleanup(setattr, MDBService, "_provider_ok", False)
        self.svc = MDBService(SimpleNamespace())
        # Pretend the host and bridge exist so only the probe outcome varies.
        self.files = mock.patch.object(mod.os.path, "isfile", return_value=True)
        self.bridge = mock.patch.object(mod, "_BRIDGE", mock.Mock(is_file=lambda: True))
        self.files.start(); self.bridge.start()
        self.addCleanup(self.files.stop); self.addCleanup(self.bridge.stop)

    def test_provider_available(self):
        with mock.patch.object(mod.subprocess, "run", return_value=_completed(0)) as run:
            self.assertEqual(self.svc.check_provider(), (True, ""))
            self.svc.check_provider()  # cached success: no second probe
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args[0][0][0], mod._PS32)

    def test_provider_unavailable(self):
        with mock.patch.object(mod.subprocess, "run", return_value=_completed(4)):
            ok, reason = self.svc.check_provider()
        self.assertFalse(ok)
        self.assertIn("could not be initialized", reason)

    def test_provider_not_registered(self):
        with mock.patch.object(mod.subprocess, "run", return_value=_completed(3)):
            self.assertIn("not registered", self.svc.check_provider()[1])

    def test_probe_failure_oserror_and_timeout(self):
        for error in (OSError("boom"), subprocess.TimeoutExpired("ps", 60)):
            with mock.patch.object(mod.subprocess, "run", side_effect=error):
                ok, reason = self.svc.check_provider()
            self.assertFalse(ok)
            self.assertIn("could not run", reason)

    def test_failure_is_not_cached(self):
        with mock.patch.object(mod.subprocess, "run", return_value=_completed(4)):
            self.assertFalse(self.svc.check_provider()[0])
        with mock.patch.object(mod.subprocess, "run", return_value=_completed(0)):
            self.assertTrue(self.svc.check_provider()[0])

    def test_powershell_unavailable(self):
        self.files.stop()
        with mock.patch.object(mod.os.path, "isfile", return_value=False), \
                mock.patch.object(mod.subprocess, "run") as run:
            ok, reason = self.svc.check_provider()
        self.files.start()
        self.assertFalse(ok)
        self.assertIn("PowerShell", reason)
        run.assert_not_called()

    def test_bridge_script_unavailable(self):
        with mock.patch.object(mod, "_BRIDGE", mock.Mock(is_file=lambda: False)), \
                mock.patch.object(mod.subprocess, "run") as run:
            ok, reason = self.svc.check_provider()
        self.assertFalse(ok)
        self.assertIn("bridge script", reason)
        run.assert_not_called()

    def test_preflight_failure_blocks_table_reads_with_clear_error(self):
        with mock.patch.object(mod.subprocess, "run", return_value=_completed(4)) as run, \
                mock.patch.object(MDBService, "execute_batch") as batch:
            with self.assertRaises(MDBProviderUnavailableError) as caught:
                self.svc.read_tables("x.mdb", {"A": "SELECT 1", "B": "SELECT 2", "C": "SELECT 3"})
        batch.assert_not_called()                      # no per-table reads attempted
        self.assertEqual(run.call_count, 1)            # only the probe ran
        self.assertEqual(str(caught.exception), PROVIDER_MISSING_MESSAGE)
        self.assertNotIn("no bridge result returned", str(caught.exception))
        self.assertIn("MDB Reader Dependency Missing", str(caught.exception))
        self.assertIn("ACE OLEDB 16.0, 32-bit", str(caught.exception))

    def test_repository_read_surfaces_dependency_error_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            mdb = Path(tmp) / "pcr_data_com_ocd.mdb"
            mdb.write_bytes(b"x")
            ctx = SimpleNamespace(mdb_service=self.svc)
            with mock.patch.object(mod.subprocess, "run", return_value=_completed(4)):
                with self.assertRaises(MDBProviderUnavailableError):
                    MdbReverseEngineeringService(ctx).read(mdb)

    def test_available_provider_leaves_read_behaviour_unchanged(self):
        rows = {"A": [{"x": 1}], "B": []}
        fake = SimpleNamespace(ok=True, results=[
            mod.MDBOpResult(op="query", ok=True, rows=rows["A"]),
            mod.MDBOpResult(op="query", ok=True, rows=rows["B"]),
        ])
        with mock.patch.object(mod.subprocess, "run", return_value=_completed(0)), \
                mock.patch.object(MDBService, "execute_batch", return_value=fake) as batch:
            out = self.svc.read_tables("x.mdb", {"A": "SELECT 1", "B": "SELECT 2"})
        self.assertEqual(out, rows)
        batch.assert_called_once()

    def test_empty_read_does_not_probe(self):
        with mock.patch.object(mod.subprocess, "run") as run:
            self.assertEqual(self.svc.read_tables("x.mdb", {}), {})
        run.assert_not_called()


class _UnavailableMDB:
    """read_tables stand-in that fails the way a missing provider does."""

    def read_tables(self, path, sql_by_name):
        raise MDBProviderUnavailableError("probe failed")

    def is_available(self):
        return True


class ExecuteBatchPreflightTests(unittest.TestCase):
    def setUp(self):
        MDBService._provider_ok = False
        self.addCleanup(setattr, MDBService, "_provider_ok", False)
        self.svc = MDBService(SimpleNamespace())
        patches = (
            mock.patch.object(mod.os.path, "isfile", return_value=True),
            mock.patch.object(mod, "_BRIDGE", mock.Mock(is_file=lambda: True)),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_unavailable_provider_returns_failed_batch_and_runs_no_ops(self):
        ops = [{"op": "delete", "table": "T"}, {"op": "insert", "table": "T", "rows": [{"a": 1}]}]
        with mock.patch.object(mod.subprocess, "run", return_value=_completed(4)) as run:
            batch = self.svc.execute_batch("x.mdb", ops, transaction=True)
        self.assertFalse(batch.ok)
        self.assertEqual([r.op for r in batch.results], ["provider"])
        self.assertEqual(batch.first_error(), PROVIDER_MISSING_MESSAGE)  # no provider(...) wrapping
        self.assertEqual(run.call_count, 1)  # only the probe; the bridge never launched
        self.assertNotIn("-File", run.call_args[0][0])

    def test_failed_provider_logs_the_reason_for_it_support(self):
        with mock.patch.object(mod.subprocess, "run", return_value=_completed(4)):
            with self.assertLogs(mod._log, level="WARNING") as logs:
                batch = self.svc.execute_batch("x.mdb", [{"op": "query", "sql": "SELECT 1"}])
        self.assertTrue(any("could not be initialized" in line for line in logs.output))
        self.assertEqual(batch.first_error(), PROVIDER_MISSING_MESSAGE)  # user text unchanged
        self.assertFalse(any(PROVIDER_MISSING_MESSAGE in line for line in logs.output))  # log carries the reason, not the user text

    def test_read_tables_logs_the_reason_too(self):
        with mock.patch.object(mod.subprocess, "run", return_value=_completed(3)):
            with self.assertLogs(mod._log, level="WARNING") as logs:
                with self.assertRaises(MDBProviderUnavailableError):
                    self.svc.read_tables("x.mdb", {"A": "SELECT 1"})
        self.assertTrue(any("not registered" in line for line in logs.output))

    def test_other_failed_ops_keep_their_op_wrapping(self):
        batch = mod.MDBBatchResult(ok=False, results=[mod.MDBOpResult(op="insert", ok=False, error="dup")])
        self.assertEqual(batch.first_error(), "insert(dup)")

    def test_available_provider_runs_bridge_exactly_as_before(self):
        out_json = '{"ok": true, "results": [{"op": "query", "ok": true, "rows": [{"v": 7}]}]}'

        def fake_run(cmd, **kwargs):
            if "-File" not in cmd:
                return _completed(0)  # provider probe
            out_path = Path(cmd[cmd.index("-OutputPath") + 1])
            out_path.write_text(out_json, encoding="utf-8")
            return _completed(0)

        with mock.patch.object(mod.subprocess, "run", side_effect=fake_run):
            batch = self.svc.execute_batch("x.mdb", [{"op": "query", "sql": "SELECT 1"}])
        self.assertTrue(batch.ok)
        self.assertEqual(batch.results[0].rows, [{"v": 7}])


class ProviderErrorNotMisclassifiedTests(unittest.TestCase):
    def test_export_session_attach_does_not_report_schema_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            mdb = Path(tmp) / "pcr_data_com_ocd.mdb"
            mdb.write_bytes(b"x")
            ctx = SimpleNamespace(mdb_service=_UnavailableMDB(), data_dir=Path(tmp))
            service = MdbExportSessionService.__new__(MdbExportSessionService)
            service.context = ctx
            service.load = lambda snapshot: None
            service.product_key = lambda snapshot: "P1"
            with self.assertRaises(MDBProviderUnavailableError) as caught:
                service.attach_existing(SimpleNamespace(), mdb)
        self.assertNotIsInstance(caught.exception, ExportSessionError)
        self.assertNotIn("schema is not usable", str(caught.exception))

    def test_package_manufacturer_read_does_not_report_schema_error(self):
        with self.assertRaises(MDBProviderUnavailableError):
            manufacturer_mod.read_package_manufacturer(_UnavailableMDB(), "x.mdb")

    def test_manufacturer_code_read_does_not_report_read_error(self):
        with self.assertRaises(MDBProviderUnavailableError):
            manufacturer_mod.resolve_package_manufacturer(
                _UnavailableMDB(), "x.mdb",
                [{"com_PackageID": 1, "com_ManufacturerID": 2}], [],
            )

    def test_genuine_runtime_errors_are_still_wrapped(self):
        class Broken(_UnavailableMDB):
            def read_tables(self, path, sql_by_name):
                raise RuntimeError("bad table")
        with self.assertRaises(manufacturer_mod.ManufacturerLookupError) as caught:
            manufacturer_mod.read_package_manufacturer(Broken(), "x.mdb")
        self.assertIn("Template schema is not usable", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
