"""Subprocess client for the optional x86 .NET Framework legacy VARCOND bridge.

The bridge is deliberately opt-in: the normal Workbench workflow remains on the
Python snapshot-based generator unless a caller explicitly invokes this client.
No SQL credentials are accepted here; legacy authentication is resolved by the
legacy application's existing connection policy and the current Windows user.
"""
from __future__ import annotations

import json
import os
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


@dataclass
class LegacyVarCondResponse:
    generated_text: str = ""
    statuses: list[str] = field(default_factory=list)


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
    if not request.item_codes:
        raise LegacyVarCondError("At least one article code is required.")
    if not request.filter.strip():
        raise LegacyVarCondError(
            "A non-empty filter is required to avoid the legacy all-items confirmation dialog."
        )
    if request.category_id < 0:
        raise LegacyVarCondError("A valid non-negative legacy category ID is required.")

    payload = {
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
    try:
        completed = subprocess.run(
            [str(helper.resolve())],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=request.timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise LegacyVarCondError(
            f"Legacy VARCOND bridge timed out after {request.timeout_seconds} seconds."
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

    if completed.returncode != 0 or not result.get("ok"):
        message = result.get("error") or completed.stderr or "unknown legacy bridge error"
        raise LegacyVarCondError(str(message))

    generated = result.get("generatedText", "")
    statuses = result.get("statuses", [])
    if not isinstance(generated, str) or not isinstance(statuses, list):
        raise LegacyVarCondError("Legacy bridge response has an unexpected shape.")
    return LegacyVarCondResponse(generated_text=generated, statuses=[str(s) for s in statuses])
