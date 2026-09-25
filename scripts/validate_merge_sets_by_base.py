"""Validate base-article MERGE (same base -> one master, optional properties).

Headless, PDM-free check that
:meth:`services.engineering.engineering_reduction_service.
EngineeringReductionService.merge_sets_by_base` merges property-structure
classes that reduce to the SAME base article number into one master, flags the
properties only some variants carry as OPTIONAL, and keeps genuinely-different
bases separate.

Run:  $env:PYTHONPATH="."; python scripts/validate_merge_sets_by_base.py
"""
from __future__ import annotations

from core.application_context import ApplicationContext
from models.article import Article
from models.article_set import ArticleSet
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot


def _snapshot() -> Snapshot:
    # Three products. p1/p2 share base NOALE1 but p2 carries an extra property
    # (Height) -> those two classes must MERGE with Height optional. p3 is a
    # different base (NOALE2) and must stay separate.
    props = [
        Property(id="A", name="PropA", values=[PropertyValue(id="va", value="a")]),
        Property(id="B", name="PropB", values=[PropertyValue(id="vb", value="b")]),
        Property(id="H", name="Height", values=[PropertyValue(id="vh", value="h")]),
    ]
    snap = Snapshot(id="p")
    snap.properties = props
    snap.articles = [
        Article(id="a1", code="NOALE111", product_id="p1"),   # base NOALE1, {A,B}
        Article(id="a2", code="NOALE172L", product_id="p2"),  # base NOALE1, {A,B,H}
        Article(id="a3", code="NOALE211", product_id="p3"),   # base NOALE2, {A,B}
    ]
    snap.product_property_value_ids = {
        "p1": ["va", "vb"],
        "p2": ["va", "vb", "vh"],
        "p3": ["va", "vb"],
    }
    # Materialised sets give the base length (6 here). They key by the CLASSES
    # the classifier produces: {A,B} (a1,a3) and {A,B,H} (a2).
    snap.article_sets = [
        ArticleSet(article_ids=["a1", "a3"], base_length=6),
        ArticleSet(article_ids=["a2"], base_length=6),
    ]
    return snap


def main() -> int:
    ctx = ApplicationContext()
    snap = _snapshot()
    svc = ctx.engineering_reduction_service

    # Sanity: property structure splits into 2 classes ({A,B} and {A,B,H};
    # p1/p3 share the {A,B} signature).
    classes = svc.classify_by_properties(snap)
    assert len(classes) == 2, [c.property_names for c in classes]

    masters = svc.merge_sets_by_base(snap)
    by_base = {m.base: m for m in masters}
    assert set(by_base) == {"NOALE1", "NOALE2"}, list(by_base)
    print("OK: property classes merged to 2 base masters")

    n1 = by_base["NOALE1"]
    assert set(n1.article_ids) == {"a1", "a2"}, n1.article_ids
    assert n1.base_length == 6, n1.base_length
    assert set(n1.property_names) == {"PropA", "PropB", "Height"}, n1.property_names
    assert n1.optional_property_names == ("Height",), n1.optional_property_names
    print("OK: same-base classes merged; extra property flagged OPTIONAL")

    n2 = by_base["NOALE2"]
    assert set(n2.article_ids) == {"a3"}, n2.article_ids
    assert n2.optional_property_names == (), n2.optional_property_names
    print("OK: different base kept separate, no optional")

    # Determinism: same snapshot -> identical bases/optional.
    again = svc.merge_sets_by_base(snap)
    assert [(m.base, m.optional_property_names) for m in masters] == \
           [(m.base, m.optional_property_names) for m in again]
    print("OK: deterministic")

    print("ALL MERGE-SETS-BY-BASE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
