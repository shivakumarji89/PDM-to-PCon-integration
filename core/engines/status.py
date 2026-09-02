"""Workspace status engine.

Standardises the status text every workspace shows (validation summary,
warnings, readiness) so formatting is consistent throughout the application.
"""
from __future__ import annotations

from core.engines.validation import BaseValidation


def validation_summary(validation: BaseValidation) -> str:
    """One-line validation summary for a workspace status panel."""
    if validation.total == 0:
        return "Nothing to validate."
    if validation.ok:
        return "OK"
    return f"{len(validation.warnings)} issue group(s)"


def warnings_text(validation: BaseValidation) -> str:
    """Multi-line warnings text, or 'None' when there are no warnings."""
    return "\n".join(validation.warnings) if validation.warnings else "None"
