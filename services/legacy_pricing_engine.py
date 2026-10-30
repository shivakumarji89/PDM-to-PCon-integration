"""Opt-in adapter for the compiled PDM Maintenance pricing engine.

Invokes UpdatePriceThread.execThread through the existing x86 PowerShell
harness. The caller must provide an isolated MDB copy. This is a parity
bridge, not a production replacement for PricingService.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


class LegacyPricingEngineError(RuntimeError):
    """The legacy pricing worker could not be invoked or did not finish."""


@dataclass(frozen=True)
class LegacyPricingEngineRequest:
    pdm_dir: str
    pcon_root: str
    workspace: str
    mode: str
    items: Sequence[str]
    program_code: str
    site_id: int
    catalogue_id: int
    mydate: str
    prevdate: str
    currency: str
    price_list_id: int
    price_list_label: str
    package_id: int
    isolated_mdb_confirmed: bool = False
    item_filter: str = ""
    variableincs: bool | None = None
    reset_to_zero: bool = False
    server: str = ""
    database: str = ""
    timeout_seconds: int = 300


@dataclass
class LegacyPricingEngineResult:
    finished: bool
    pdm_version: str = ""
    mode: str = ""
    variableincs: bool = False
    status: list[str] = field(default_factory=list)
    no_pdm_price: list[str] = field(default_factory=list)
    notfound: list[str] = field(default_factory=list)


def run_legacy_pricing_engine(
    request: LegacyPricingEngineRequest,
    *,
    powershell32: str = r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe",
    harness: str | Path | None = None,
) -> LegacyPricingEngineResult:
    """Run legacy pricing against an already prepared MDB copy.

    pcon_root must contain WS/<workspace>/pcr_data_com_ocd.mdb. The explicit
    confirmation is required because the legacy worker writes directly to that
    MDB and has no transaction or rollback.
    """
    if not request.isolated_mdb_confirmed:
        raise LegacyPricingEngineError(
            "Confirm pcon_root points to a disposable MDB copy, not the live OCD."
        )
    if request.mode not in {"article", "global", "placeholders"}:
        raise LegacyPricingEngineError("mode must be article, global, or placeholders.")
    if isinstance(request.items, (str, bytes)) or not request.items:
        raise LegacyPricingEngineError("At least one item code is required.")
    if any(not isinstance(item, str) or not item.strip() for item in request.items):
        raise LegacyPricingEngineError("Item codes must be non-empty strings.")
    if not request.workspace.strip() or not request.program_code.strip():
        raise LegacyPricingEngineError("workspace and program_code are required.")
    if min(request.site_id, request.catalogue_id, request.package_id, request.price_list_id) < 0:
        raise LegacyPricingEngineError("site, catalogue, package and list IDs must be non-negative.")
    if not request.price_list_label.strip() or not request.currency.strip() or not request.mydate.strip():
        raise LegacyPricingEngineError("Price-list label, currency and pricing date are required.")
    if request.timeout_seconds <= 0:
        raise LegacyPricingEngineError("timeout_seconds must be greater than zero.")

    pdm_dir = Path(request.pdm_dir).expanduser().resolve()
    if not (pdm_dir / "PDMMaintenance.exe").is_file():
        raise LegacyPricingEngineError(f"PDMMaintenance.exe not found in {pdm_dir}")
    mdb = Path(request.pcon_root).expanduser().resolve() / "WS" / request.workspace / "pcr_data_com_ocd.mdb"
    if not mdb.is_file():
        raise LegacyPricingEngineError(f"Expected isolated MDB copy does not exist: {mdb}")
    harness_path = Path(harness) if harness else (
        Path(__file__).resolve().parents[1] / "scripts" / "pdm_differential" / "run_pdm_price_update.ps1"
    )
    if not harness_path.is_file():
        raise LegacyPricingEngineError(f"Legacy pricing harness not found: {harness_path}")

    payload = {
        "pconRoot": str(Path(request.pcon_root).expanduser().resolve()) + "\\",
        "workspace": request.workspace,
        "mode": request.mode,
        "items": list(request.items),
        "itemFilter": request.item_filter,
        "programCode": request.program_code,
        "siteId": request.site_id,
        "catalogueId": request.catalogue_id,
        "mydate": request.mydate,
        "prevdate": request.prevdate,
        "currency": request.currency,
        "priceListId": request.price_list_id,
        "pricelist": request.price_list_label,
        "variableincsFromProgram": request.variableincs is None,
        "variableincs": bool(request.variableincs),
        "packageId": request.package_id,
        "resetToZero": request.reset_to_zero,
        "server": request.server,
        "database": request.database,
    }
    with tempfile.TemporaryDirectory(prefix="mk-legacy-pricing-") as temp:
        job_path, out_path = Path(temp) / "job.json", Path(temp) / "result.json"
        job_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        command = [
            powershell32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(harness_path.resolve()), "-JobPath", str(job_path), "-OutPath",
            str(out_path), "-PdmDir", str(pdm_dir),
        ]
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=request.timeout_seconds, check=False, shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LegacyPricingEngineError(
                f"Legacy pricing timed out after {request.timeout_seconds} seconds; "
                "a legacy modal dialog may be blocking execution."
            ) from exc
        except OSError as exc:
            raise LegacyPricingEngineError(f"Could not start legacy pricing worker: {exc}") from exc
        if not out_path.is_file():
            detail = (completed.stderr or completed.stdout or "no output").strip()
            raise LegacyPricingEngineError(
                f"Legacy worker produced no result (exit {completed.returncode}): {detail[:1000]}"
            )
        try:
            raw = json.loads(out_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LegacyPricingEngineError(f"Legacy worker returned invalid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise LegacyPricingEngineError("Legacy worker result must be a JSON object.")
    if completed.returncode != 0:
        raise LegacyPricingEngineError(
            str(raw.get("error") or completed.stderr or f"Legacy worker exited {completed.returncode}")
        )
    if not raw.get("finished"):
        details = "; ".join(str(x) for x in raw.get("status", []))
        raise LegacyPricingEngineError("Legacy pricing worker did not finish. " + details)
    return LegacyPricingEngineResult(
        finished=True,
        pdm_version=str(raw.get("pdmVersion", "")),
        mode=str(raw.get("mode", request.mode)),
        variableincs=bool(raw.get("variableincs", False)),
        status=[str(x) for x in raw.get("status", [])],
        no_pdm_price=[str(x) for x in raw.get("noPDMprice", [])],
        notfound=[str(x) for x in raw.get("notfound", [])],
    )
