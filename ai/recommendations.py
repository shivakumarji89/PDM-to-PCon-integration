"""Recommendation engine.

Generates contextual recommendations purely from an :class:`EngineeringContext`
(which itself is built from existing services). No engineering calculations.
"""
from __future__ import annotations

from ai.context import COLLECTIONS, EngineeringContext


class RecommendationEngine:
    """Produces deterministic recommendations from the engineering context."""

    def generate(self, context: EngineeringContext) -> list[str]:
        if not context.has_snapshot:
            return ["Load a product on the Product page to begin."]

        recommendations: list[str] = []

        for key, label, _step, _svc in COLLECTIONS:
            if context.counts.get(key, 0) > 0 and context.selected.get(key, 0) == 0:
                recommendations.append(f"You have not selected any {label}.")

        if context.errors:
            recommendations.append(
                f"Review contains {len(context.errors)} error(s) that block generation."
            )
        elif context.warnings:
            recommendations.append(
                f"Review contains {len(context.warnings)} warning(s)."
            )

        if context.missing_relationships:
            recommendations.append(
                "There are missing relationships - some values have no owner."
            )

        if context.readiness:
            recommendations.append("Generate is available.")
        else:
            recommendations.append("Generate is not available until Review is ready.")

        return recommendations
