"""Subprocess client for the optional x86 .NET Framework legacy VARCOND bridge.

The bridge is deliberately opt-in: the normal Workbench workflow remains on the
Python snapshot-based generator unless a caller explicitly invokes this client.
No SQL credentials are accepted here; legacy authentication is resolved by the
legacy application's existing connection policy and the current Windows user.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class LegacyVarCondRequest:
    helper_exe: str
    legacy_assembly: str
    item_codes: Sequence[str]
    category_id: int
    filter: str
    server: str = ""
    database: str = ""
    pcon_path: str = ""
    prefix: str = ""
    property_substitutions: str = ""
    property_exclusions: str = ""
    timeout_seconds: int = 300
    #: Operator attestation that server/database was verified as non-production.
    #: The database-name check is only a tripwire and never sufficient on its own.
    confirm_non_production: bool = False


@dataclass
class LegacyVarCondResponse:
    generated_text: str = ""
    statuses: list[str] = field(default_factory=list)
    legacy_assembly_version: str = ""


class LegacyVarCondError(RuntimeError):
    """The legacy bridge could not produce a valid generation result."""


def generate_with_legacy(request: LegacyVarCondRequest) -> LegacyVarCondResponse:
    """Run one isolated legacy generation request and parse its JSON response."""
    helper = Path(request.helper_exe)
    assembly = Path(request.legacy_assembly)
    if not helper.is_file():
        raise LegacyVarCondError(f"Legacy bridge executable not found: {helper}")
    if not assembly.is_file():
        raise LegacyVarCondError(f"Legacy PDMMaintenance assembly not found: {assembly}")
    if isinstance(request.item_codes, (str, bytes)) or not request.item_codes:
        raise LegacyVarCondError("At least one article code is required.")
    if any(not isinstance(code, str) or not code.strip() for code in request.item_codes):
        raise LegacyVarCondError("Article codes must be non-empty strings.")
    if not request.filter.strip():
        raise LegacyVarCondError(
            "A non-empty filter is required to avoid the legacy all-items confirmation dialog."
        )
    if request.category_id < 0:
        raise LegacyVarCondError("A valid non-negative legacy category ID is required.")
    if not request.server.strip() or not request.database.strip():
        raise LegacyVarCondError(
            "Explicit test SQL server and database are required; legacy production defaults are blocked."
        )
    safe_markers = ("test", "dev", "uat", "prototype", "sandbox")
    if not any(marker in request.database.casefold() for marker in safe_markers):
        raise LegacyVarCondError(
            "Database name must clearly identify a test/dev/UAT/prototype/sandbox database."
        )

    unsafe_markers = ("live", "prod")
    if any(marker in request.database.casefold() for marker in unsafe_markers):
        raise LegacyVarCondError("Database name looks like a live/production database.")
    if not request.confirm_non_production:
        raise LegacyVarCondError(
            "confirm_non_production must be True: verify the server/database is "
            "non-production before running the legacy worker."
        )
    if request.timeout_seconds <= 0:
        raise LegacyVarCondError("timeout_seconds must be greater than zero.")

    payload = {
        "confirmNonProduction": True,
        "legacyAssemblyPath": str(assembly.resolve()),
        "itemCodes": list(request.item_codes),
        "categoryId": request.category_id,
        "filter": request.filter,
        "server": request.server,
        "database": request.database,
        "pConPath": request.pcon_path,
        "prefix": request.prefix,
        "propertySubstitutions": request.property_substitutions,
        "propertyExclusions": request.property_exclusions,
    }
    result, completed = _run_helper(helper, payload, request.timeout_seconds)
    if not isinstance(result, dict):
        raise LegacyVarCondError("Legacy bridge response must be a JSON object.")
    if completed.returncode != 0 or not result.get("ok"):
        message = result.get("error") or completed.stderr or "unknown legacy bridge error"
        raise LegacyVarCondError(str(message))

    generated = result.get("generatedText", "")
    statuses = result.get("statuses", [])
    if not isinstance(generated, str) or not isinstance(statuses, list):
        raise LegacyVarCondError("Legacy bridge response has an unexpected shape.")
    # The legacy worker swallows its own exceptions; never accept an aborted run
    # even if a helper build forgot to flag it.
    if "GENERATE_VARCOND_ABORTED" in statuses:
        raise LegacyVarCondError("Legacy worker reported GENERATE_VARCOND_ABORTED.")
    return LegacyVarCondResponse(
        generated_text=generated,
        statuses=[str(s) for s in statuses],
        legacy_assembly_version=str(result.get("legacyAssemblyVersion", "")),
    )


def verify_legacy_binding(helper_exe: str, legacy_assembly: str, timeout_seconds: int = 60) -> dict:
    """Database-free check that the helper's reflection contract matches the
    real legacy assembly (loads it, never configures it or connects)."""
    helper = Path(helper_exe)
    assembly = Path(legacy_assembly)
    if not helper.is_file():
        raise LegacyVarCondError(f"Legacy bridge executable not found: {helper}")
    if not assembly.is_file():
        raise LegacyVarCondError(f"Legacy PDMMaintenance assembly not found: {assembly}")
    if timeout_seconds <= 0:
        raise LegacyVarCondError("timeout_seconds must be greater than zero.")
    payload = {"dryRun": True, "legacyAssemblyPath": str(assembly.resolve())}
    result, completed = _run_helper(helper, payload, timeout_seconds)
    if not isinstance(result, dict):
        raise LegacyVarCondError("Legacy bridge response must be a JSON object.")
    if completed.returncode != 0 or not result.get("ok"):
        raise LegacyVarCondError(str(result.get("error") or completed.stderr or "dry run failed"))
    details = result.get("dryRun")
    if not isinstance(details, dict):
        raise LegacyVarCondError("Legacy bridge dry-run response has an unexpected shape.")
    return details


def _run_helper(helper: Path, payload: dict, timeout_seconds: int):
    try:
        completed = subprocess.run(
            [str(helper.resolve())],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise LegacyVarCondError(
            f"Legacy VARCOND bridge timed out after {timeout_seconds} seconds "
            "(a legacy modal dialog may be waiting for input)."
        ) from exc
    except OSError as exc:
        raise LegacyVarCondError(f"Could not start legacy VARCOND bridge: {exc}") from exc

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        detail = (completed.stderr or completed.stdout or "no output").strip()
        raise LegacyVarCondError(
            f"Legacy bridge returned invalid JSON (exit {completed.returncode}): {detail[:1000]}"
        ) from exc
    return result, completed
