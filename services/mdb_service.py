"""MDB (Microsoft Access) read/write service.

Writing an ``.mdb`` requires the ACE OLEDB provider, which on this machine is
installed for 32-bit only. The application runs under 64-bit Python (no ACE
provider), so all database work is delegated to a 32-bit PowerShell bridge
(``resources/mdb_bridge.ps1``) that opens the file via ADODB and applies a JSON
batch of operations in a single session.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from services.base_service import BaseService

#: 32-bit Windows PowerShell - the only host with a working ACE OLEDB provider.
_PS32 = r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"

#: Bridge script, resolved relative to the repository root.
_BRIDGE = Path(__file__).resolve().parent.parent / "resources" / "mdb_bridge.ps1"


@dataclass
class MDBOpResult:
    """Outcome of a single bridge operation."""

    op: str
    ok: bool
    error: str | None = None
    rows: list[dict[str, Any]] = field(default_factory=list)
    inserted: int = 0
    updated: int = 0


@dataclass
class MDBBatchResult:
    """Outcome of a whole bridge batch."""

    ok: bool
    results: list[MDBOpResult] = field(default_factory=list)

    def first_error(self) -> str | None:
        for r in self.results:
            if not r.ok:
                return f"{r.op}({r.error})"
        return None


class MDBService(BaseService):
    """Interface to MDB (Access) operations via the 32-bit ADODB bridge."""

    # -- Environment -----------------------------------------------------

    @staticmethod
    def is_available() -> bool:
        """True when the 32-bit PowerShell host and bridge script both exist."""
        return os.path.isfile(_PS32) and _BRIDGE.is_file()

    # -- File-level helpers (no ACE provider needed) ---------------------

    @staticmethod
    def copy_template(template_path: str | Path, dest_path: str | Path) -> None:
        """Copy a template ``.mdb`` to the destination, creating parent dirs."""
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template_path, dest)

    # -- Batch execution -------------------------------------------------

    def execute_batch(self, mdb_path: str | Path, ops: list[dict[str, Any]], transaction: bool = False) -> MDBBatchResult:
        """Run a list of operations against ``mdb_path`` in one ADODB session.

        Each op is a dict: ``delete``/``insert``/``update``/``query`` (see
        ``resources/mdb_bridge.ps1`` for the accepted shapes). When
        ``transaction`` is set the whole batch is wrapped in one ADODB
        transaction (committed only if every op succeeds), so a partial failure
        leaves the file unchanged.
        """
        if not self.is_available():
            return MDBBatchResult(
                ok=False,
                results=[MDBOpResult(op="env", ok=False, error="32-bit PowerShell/ACE bridge unavailable")],
            )

        payload = {"mdb": str(Path(mdb_path)), "ops": ops, "transaction": bool(transaction)}
        tmp_path = Path(tempfile.mkdtemp(prefix="mdb_bridge_"))
        in_path = tmp_path / "in.json"
        out_path = tmp_path / "out.json"
        try:
            in_path.write_text(json.dumps(payload), encoding="utf-8")

            proc = subprocess.run(
                [
                    _PS32, "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(_BRIDGE), "-InputPath", str(in_path),
                    "-OutputPath", str(out_path),
                ],
                capture_output=True, text=True,
            )

            # The PowerShell/ADODB process can keep the output file handle
            # alive briefly after exiting. Read the file before cleanup and let
            # the OS/process finish independently of TemporaryDirectory teardown.
            if not out_path.is_file():
                err = (proc.stderr or proc.stdout or "no bridge output").strip()
                return MDBBatchResult(
                    ok=False,
                    results=[MDBOpResult(op="bridge", ok=False, error=err[:500])],
                )

            data = json.loads(out_path.read_text(encoding="utf-8-sig"))

            results = [
                MDBOpResult(
                    op=item.get("op", ""),
                    ok=bool(item.get("ok")),
                    error=item.get("error"),
                    rows=item.get("rows") or [],
                    inserted=int(item.get("inserted") or 0),
                    updated=int(item.get("updated") or 0),
                )
                for item in (data.get("results") or [])
            ]
            return MDBBatchResult(ok=bool(data.get("ok")), results=results)
        finally:
            # Best-effort cleanup. Windows may briefly retain ADODB/PowerShell
            # handles to out.json; failure to delete the temp file must not
            # interfere with the actual MDB result.
            try:
                shutil.rmtree(tmp_path, ignore_errors=True)
            except OSError:
                pass

    # -- Convenience wrappers -------------------------------------------

    def read_table(self, mdb_path: str | Path, sql: str) -> list[dict[str, Any]]:
        """Run a single SELECT and return its rows."""
        batch = self.execute_batch(mdb_path, [{"op": "query", "sql": sql}])
        if not batch.ok or not batch.results:
            return []
        return batch.results[0].rows

    def read_tables(self, mdb_path: str | Path, sql_by_name: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
        """Run multiple SELECTs in one MDB/ADODB session.

        This is substantially faster than calling ``read_table`` repeatedly,
        because the 32-bit PowerShell/ACE bridge is started only once.
        """
        if not sql_by_name:
            return {}
        ops = [{"op": "query", "sql": sql} for sql in sql_by_name.values()]
        batch = self.execute_batch(mdb_path, ops)
        names = list(sql_by_name)
        if not batch.results:
            raise RuntimeError(
                f"MDB batch read returned no results for {Path(mdb_path).name}."
            )

        # Do not silently convert a failed table query into an empty table.
        # Empty and failed are materially different during repository import.
        failures = []
        for index, name in enumerate(names):
            if index >= len(batch.results):
                failures.append(f"{name}: no bridge result returned")
                continue
            result = batch.results[index]
            if not result.ok:
                failures.append(f"{name}: {result.error or 'query failed'}")

        if failures:
            raise RuntimeError(
                f"MDB read failed for {Path(mdb_path).name}: "
                + "; ".join(failures)
            )

        return {
            name: batch.results[index].rows
            for index, name in enumerate(names)
        }

    def clear_tables(self, mdb_path: str | Path, tables: list[str]) -> MDBBatchResult:
        """DELETE all rows from each named table."""
        return self.execute_batch(mdb_path, [{"op": "delete", "table": t} for t in tables])

    def insert_rows(self, mdb_path: str | Path, table: str, rows: list[dict[str, Any]]) -> MDBBatchResult:
        """Insert rows into a single table."""
        return self.execute_batch(mdb_path, [{"op": "insert", "table": table, "rows": rows}])
