"""Explicit pricing-program validation for Maintenance global pricing.

The PDM global price query treats a blank program like ``revive`` (component fabric
routing to ``28=``). Layout Screens and Nevi Screens keep ``8=`` in their MDBs, so a
blank program must never reach the repository in Maintenance: it is rejected here.
"""
from __future__ import annotations

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
