"""Prompt building.

Turns an :class:`EngineeringContext` into a compact textual summary that AI
providers consume. No engineering calculations - it only formats existing data.
"""
from __future__ import annotations

from ai.context import COLLECTIONS, EngineeringContext


def build_prompt(context: EngineeringContext) -> str:
    """Return a deterministic text summary of the engineering context."""
    lines = ["Engineering session summary:"]
    lines.append(f"- Product: {context.product_label}")
    lines.append(f"- Current step: {context.current_step.name.title()}")
    completed, total = context.progress
    lines.append(f"- Progress: {completed}/{total} steps completed")

    for key, label, _step, _svc in COLLECTIONS:
        lines.append(
            f"- {label.title()}: {context.counts.get(key, 0)} loaded, "
            f"{context.selected.get(key, 0)} selected"
        )

    lines.append(f"- Warnings: {len(context.warnings)}")
    lines.append(f"- Errors: {len(context.errors)}")
    lines.append(f"- Engineering readiness: {context.readiness}")
    return "\n".join(lines)
