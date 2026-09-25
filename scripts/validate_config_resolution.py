"""Validate config-code resolution: automation flags what it can't assign,
generation is blocked until resolved, then it clears.

Run: python scripts/validate_config_resolution.py
"""
from core.application_context import ApplicationContext
from models.article import Article
from models.product import Product
from models.property import Property
from models.property_value import PropertyValue

_MSG = "configuration attribute(s) need a manual"


def main() -> None:
    ctx = ApplicationContext()
    snap = ctx.snapshot_manager.create_empty_snapshot(Product(id="pA", code="A"))
    snap.id = "pA"
    # One config attribute (uncoded, 2 values) with a single product -> no
    # correlation evidence -> the automation cannot assign it.
    config = Property(id="G1", name="Config", has_dependent_options=True, values=[
        PropertyValue(id="gv1", property_id="G1", value="Y", code=""),
        PropertyValue(id="gv2", property_id="G1", value="Z", code=""),
    ])
    snap.properties = [config]
    snap.property_values = list(config.values)
    snap.articles = [Article(id="a1", code="AY", product_id="pA")]
    snap.product_property_value_ids = {"pA": ["gv1"]}

    svc = ctx.engineering_class_service
    unresolved = svc.unresolved_config_codes(snap)
    assert [p.id for p in unresolved] == ["G1"], [p.id for p in unresolved]
    print("OK: automation reports the unresolvable config attribute")

    review = ctx.validation_service.review()
    assert not review.ready, "generation should be blocked while unresolved"
    assert any(_MSG in e for e in review.errors), review.errors
    print("OK: Generate is blocked while a config code is unresolved")

    # Single-value config attribute is NOT flagged (constant in the base).
    config.values.pop()
    snap.property_values = list(config.values)
    assert svc.unresolved_config_codes(snap) == []
    print("OK: single-value config attribute is not flagged")

    # Restore two values, then resolve manually -> unblocks.
    config.values.append(PropertyValue(id="gv2", property_id="G1", value="Z", code=""))
    snap.property_values = list(config.values)
    for value in config.values:
        value.code = value.value  # user assigns a code
    assert svc.unresolved_config_codes(snap) == []
    assert not any(_MSG in e for e in ctx.validation_service.review().errors)
    print("OK: assigning the codes clears the block")

    print("\nALL CONFIG RESOLUTION CHECKS PASSED")


if __name__ == "__main__":
    main()
