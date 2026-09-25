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
        with tempfile.TemporaryDirectory(prefix="mdb_bridge_") as tmp:
            in_path = Path(tmp) / "in.json"
            out_path = Path(tmp) / "out.json"
            in_path.write_text(json.dumps(payload), encoding="utf-8")

            proc = subprocess.run(
                [
                    _PS32, "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(_BRIDGE), "-InputPath", str(in_path),
                    "-OutputPath", str(out_path),
                ],
                capture_output=True, text=True,
            )
            if not out_path.is_file():
                err = (proc.stderr or proc.stdout or "no bridge output").strip()
                return MDBBatchResult(ok=False, results=[MDBOpResult(op="bridge", ok=False, error=err[:500])])

            data = json.loads(out_path.read_text(encoding="utf-8-sig"))

        results = [
            MDBOpResult(
                op=r.get("op", ""),
                ok=bool(r.get("ok")),
                error=r.get("error"),
                rows=r.get("rows") or [],
                inserted=int(r.get("inserted") or 0),
                updated=int(r.get("updated") or 0),
            )
            for r in (data.get("results") or [])
        ]
        return MDBBatchResult(ok=bool(data.get("ok")), results=results)

    # -- Convenience wrappers -------------------------------------------

    def read_table(self, mdb_path: str | Path, sql: str) -> list[dict[str, Any]]:
        """Run a single SELECT and return its rows."""
        batch = self.execute_batch(mdb_path, [{"op": "query", "sql": sql}])
        if not batch.ok or not batch.results:
            return []
        return batch.results[0].rows

    def clear_tables(self, mdb_path: str | Path, tables: list[str]) -> MDBBatchResult:
        """DELETE all rows from each named table."""
        return self.execute_batch(mdb_path, [{"op": "delete", "table": t} for t in tables])

    def insert_rows(self, mdb_path: str | Path, table: str, rows: list[dict[str, Any]]) -> MDBBatchResult:
        """Insert rows into a single table."""
        return self.execute_batch(mdb_path, [{"op": "insert", "table": table, "rows": rows}])
