"""Headless validation for the AI assistant request path.

Verifies that a single ``handle()`` call does NOT recompute the expensive
``validation_service.review()`` a second time: the readiness/warnings actions
reuse the EngineeringContext already built for that request. Also checks the
no-context fallback still works.

Run:  $env:PYTHONPATH="."; python scripts/validate_assistant.py
"""
from __future__ import annotations

import sys

from ai.actions import Action, ActionType
from ai.assistant import EngineeringAssistant
from core.application_context import ApplicationContext
from core.enums import WorkflowStep
from models.article import Article
from models.option import Option
from models.option_value import OptionValue
from models.product import Product
from models.property import Property
from models.property_value import PropertyValue


class _StubManager:
    """Minimal manager: the assistant only needs current_step()/progress() here."""

    def current_step(self) -> WorkflowStep:
        return WorkflowStep.REVIEW

    def progress(self) -> tuple[int, int]:
        return (0, 0)


def _snapshot(ctx: ApplicationContext):
    product = Product(id="p1", code="P1", name="Prod", range_name="Bolster")
    snap = ctx.snapshot_manager.create_empty_snapshot(product)
    snap.id = "p1"
    prop = Property(id="pr1", code="PR1", name="Colour")
    v1 = PropertyValue(id="pv1", property_id="pr1", value="Red", code="")
    v2 = PropertyValue(id="pv2", property_id="pr1", value="Blue", code="")
    prop.values.extend([v1, v2])
    snap.properties.append(prop)
    snap.property_values.extend([v1, v2])
    option = Option(id="op1", code="OP1", name="Base")
    ov1 = OptionValue(id="ov1", option_id="op1", value="Sled", code="")
    option.values.append(ov1)
    snap.options.append(option)
    snap.option_values.append(ov1)
    snap.articles.append(Article(id="a1", code="P1AB", product_id="p1"))
    snap.articles.append(Article(id="a2", code="P1BA", product_id="p1"))
    snap.product_property_value_ids = {"p1": ["pv1", "pv2"]}
    ctx.engineering_initialization_service.initialize(snap)


def _wrap_counters(ctx):
    """Wrap review() to count how many times it runs per request."""
    calls = {"review": 0}
    vs = ctx.validation_service
    orig_review = vs.review

    def counting_review(*a, **k):
        calls["review"] += 1
        return orig_review(*a, **k)

    vs.review = counting_review          # type: ignore[method-assign]
    return calls


def main() -> int:
    ctx = ApplicationContext()
    _snapshot(ctx)
    calls = _wrap_counters(ctx)
    assistant = EngineeringAssistant(ctx, _StubManager())

    # "show readiness": build_context computes review() ONCE; the readiness
    # action must reuse it (no second compute).
    calls["review"] = 0
    resp = assistant.handle("show readiness")
    assert calls["review"] == 1, f"review recomputed: {calls['review']} (expected 1)"
    assert "Engineering readiness:" in resp.message
    print("OK: 'show readiness' reuses context (review=1)")

    # "show warnings": needs only review; must not compute it twice.
    calls["review"] = 0
    resp = assistant.handle("show warnings")
    assert calls["review"] == 1, f"review recomputed: {calls['review']} (expected 1)"
    assert isinstance(resp.message, str) and resp.message
    print("OK: 'show warnings' reuses context (review=1)")

    # No-context fallback: executing the action directly still works and
    # computes on demand (exactly once).
    calls["review"] = 0
    msg = assistant._executor.execute(Action(ActionType.SHOW_READINESS))
    assert calls["review"] == 1, f"fallback review={calls['review']} (expected 1)"
    assert "Engineering readiness:" in msg
    print("OK: no-context fallback computes once and is correct")

    print("\nvalidate_assistant: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
