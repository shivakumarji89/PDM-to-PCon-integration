"""Explicit pricing-program validation for Maintenance global pricing.

The PDM global price query treats a blank program like ``revive`` (component fabric
routing to ``28=``). Layout Screens and Nevi Screens keep ``8=`` in their MDBs, so a
blank program must never reach the repository in Maintenance: it is rejected here.
"""
from __future__ import annotations

from pathlib import PureWindowsPath

PROGRAM_LAYOUT = "layout_studio"
PROGRAM_NEVI = "nevi_enhanced"
PROGRAM_REVIVE = "revive"
SUPPORTED_PROGRAMS = (PROGRAM_LAYOUT, PROGRAM_NEVI, PROGRAM_REVIVE)

# Series labels as shown in the Maintenance workflow, plus the canonical codes.
_ALIASES = {
    "layoutscreens": PROGRAM_LAYOUT,
    "layoutstudio": PROGRAM_LAYOUT,
    "neviscreens": PROGRAM_NEVI,
    "nevienhanced": PROGRAM_NEVI,
    "revive": PROGRAM_REVIVE,
}


class PricingProgramError(ValueError):
    """The selected series/program cannot drive program-dependent pricing."""


def _key(value: str) -> str:
    return "".join(ch for ch in (value or "").casefold() if ch.isalnum())


def validate_pricing_program(program: str | None) -> str:
    """Return the canonical program code or raise :class:`PricingProgramError`."""
    text = (program or "").strip()
    if not text:
        raise PricingProgramError(
            "No Program is set for this series. Set it in Review > Generation > Program "
            "(Layout Screens: layout_studio, Nevi Screens: nevi_enhanced, Revive: revive) "
            "before computing or exporting prices. A blank Program is not treated as Revive."
        )
    canonical = _ALIASES.get(_key(text))
    if canonical is None:
        raise PricingProgramError(
            f"Unsupported Program '{text}'. Supported programs: {', '.join(SUPPORTED_PROGRAMS)}."
        )
    return canonical


def program_from_linked_repository(maintenance_state, snapshot) -> str:
    """Routing program named by the linked repository's package ``reg_ProgramCode``, or ``""``.

    Only the Maintenance state aligned to ``snapshot`` is consulted, and only a value that is one of the
    supported routing programs is used. Anything else (no link, other series, an unrecognised code such as
    a display name) yields ``""`` so the previous behaviour applies; nothing is guessed from names or
    article numbers.
    """
    if maintenance_state is None or snapshot is None:
        return ""
    if getattr(maintenance_state, "pdm_snapshot", None) is not snapshot:
        return ""
    package = getattr(getattr(maintenance_state, "mdb_import_snapshot", None), "product", None)
    code = str(getattr(package, "code", "") or "")
    try:
        return validate_pricing_program(code)
    except PricingProgramError:
        return ""


def program_from_workspace_path(repository_path: str | None) -> str:
    """Legacy PDM's default program: the workspace folder name, lower-cased, spaces as ``_``.

    ``PConPriceUpdate.InitWorkspace`` fills ``text_programcode`` from the ``WS/<Workspace>`` folder and passes
    it to ``UpdatePriceThread`` as both ``programCode`` and ``actualProgramCode`` (the latter must equal the
    MDB package ``reg_ProgramCode``), so legacy never prices with a blank program. ``repository_path`` is the
    linked ``pcr_data_com_ocd.mdb``; its parent folder is the workspace. Anything that is not an ``.mdb``
    file path inside a folder yields ``""``.
    """
    text = str(repository_path or "").strip()
    if not text.lower().endswith(".mdb"):
        return ""
    folder = PureWindowsPath(text.replace("/", "\\")).parent.name
    return folder.strip().lower().replace(" ", "_")
