"""Validate base-article grouping (aggregation-backed reduction view).

Headless, PDM-free check that
:meth:`services.engineering.engineering_reduction_service.
EngineeringReductionService.group_by_base` collapses members to one node per
Base Article (``reduced_article``) while holding the UNION of their
property-value links (from ``snapshot.article_property_value_ids``) with
per-value member coverage, and skips members not yet reduced.

Run:  $env:PYTHONPATH="."; python scripts/validate_base_group.py
"""
from __future__ import annotations

from core.application_context import ApplicationContext
from models.engineering import Engineering
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.snapshot import Snapshot


def _snapshot() -> Snapshot:
    # Two RY3XB line items + one RY3XT + one not-yet-reduced (no base).
    m1 = MemberArticle(id="1", article_id="A1", reduced_article="RY3XB")
    m2 = MemberArticle(id="2", article_id="A2", reduced_article="RY3XB")
    m3 = MemberArticle(id="3", article_id="A3", reduced_article="RY3XT")
    m4 = MemberArticle(id="4", article_id="A4", reduced_article="")  # skipped
    engineering = Engineering(
        families=[EngineeringFamily(id="f", name="Default", members=[m1, m2, m3, m4])]
    )
    snap = Snapshot(id="p", engineering=engineering)
    # Property-value links per article (shared v10 across the two RY3XB, plus
    # a value only one of them carries).
    snap.article_property_value_ids = {
        "A1": ["v10", "v11"],
        "A2": ["v10", "v12"],
        "A3": ["v20"],
        "A4": ["v99"],
    }
    return snap


def main() -> int:
    ctx = ApplicationContext()
    snap = _snapshot()
    groups = ctx.engineering_reduction_service.group_by_base(snap)

    by_base = {g.base: g for g in groups}
    assert set(by_base) == {"RY3XB", "RY3XT"}, list(by_base)
    print("OK: one node per Base Article; unreduced member skipped")

    rb = by_base["RY3XB"]
    assert len(rb.members) == 2, len(rb.members)
    # Union of the two members' links (order-preserving, unique).
    assert set(rb.property_value_ids) == {"v10", "v11", "v12"}, rb.property_value_ids
    print("OK: base holds UNION of member property links")

    # Per-value coverage: v10 on both members, v11/v12 on one each.
    assert rb.value_coverage["v10"] == 2, rb.value_coverage
    assert rb.value_coverage["v11"] == 1 and rb.value_coverage["v12"] == 1
    print("OK: per-value member coverage retained (shared vs divergent)")

    rt = by_base["RY3XT"]
    assert set(rt.property_value_ids) == {"v20"} and len(rt.members) == 1
    print("OK: separate base kept independent")

    print("ALL BASE-GROUP CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
