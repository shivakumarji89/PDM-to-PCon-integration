"""Validate the config-code diagnostics (EngineeringClassService.analyze_config_codes).

PDM-free: the analyzer must FIND and SUGGEST fixes for the tricky cases -
values it cannot decode, and mixed-width codes within one property (the real
``A`` / ``FN`` / ``FA`` Access-detail case that shifts later positions).

Run: python scripts/validate_config_diagnostics.py
"""
from core.application_context import ApplicationContext
from models.article import Article
from models.product import Product
from models.property import Property
from models.property_value import PropertyValue


def main() -> None:
    ctx = ApplicationContext()
    svc = ctx.engineering_class_service

    # 1) Unresolvable config attribute (single product -> no correlation evidence).
    snap = ctx.snapshot_manager.create_empty_snapshot(Product(id="pA", code="A"))
    snap.id = "pA"
    config = Property(id="G1", name="Config", has_dependent_options=True, values=[
        PropertyValue(id="gv1", property_id="G1", value="Y", code=""),
        PropertyValue(id="gv2", property_id="G1", value="Z", code=""),
    ])
    snap.properties = [config]
    snap.property_values = list(config.values)
    snap.articles = [Article(id="a1", code="AY", product_id="pA")]
    snap.product_property_value_ids = {"pA": ["gv1"]}
    findings = svc.analyze_config_codes(snap)
    kinds = {f.kind for f in findings if f.property_id == "G1"}
    assert "unresolved" in kinds, [f.kind for f in findings]
    assert all(f.suggestion for f in findings), "every finding needs a suggestion"
    print("OK: unresolved config attribute flagged with a suggestion")

    # 2) Mixed-width codes: Access = A / FN / FA across three correlated products.
    snap2 = ctx.snapshot_manager.create_empty_snapshot(Product(id="pB", code="B"))
    snap2.id = "pB"
    access = Property(id="AC", name="Access detail", has_dependent_options=True, values=[
        PropertyValue(id="cut", property_id="AC", value="Cutout", code=""),
        PropertyValue(id="fno", property_id="AC", value="FlashNo", code=""),
        PropertyValue(id="fwi", property_id="AC", value="FlashWith", code=""),
    ])
    snap2.properties = [access]
    snap2.property_values = list(access.values)
    snap2.articles = [
        Article(id="x1", code="RY3XSDABAD.", product_id="p1"),   # Cutout -> A
        Article(id="x2", code="RY3XSDABFND.", product_id="p2"),  # FlashNo -> FN
        Article(id="x3", code="RY3XSDABFAD.", product_id="p3"),  # FlashWith -> FA
    ]
    snap2.product_property_value_ids = {"p1": ["cut"], "p2": ["fno"], "p3": ["fwi"]}

    findings2 = svc.analyze_config_codes(snap2)
    ac_findings = [f for f in findings2 if f.property_id == "AC"]
    kinds2 = {f.kind for f in ac_findings}
    # Variable-width codes (the 'A' in 'A' vs 'FA') must be FOUND and advised on -
    # either an explicit unresolved flag or a mixed-width note.
    assert ac_findings, "Access-detail A/FN/FA must be flagged, not silently dropped"
    assert kinds2 & {"unresolved", "variable_width"}, kinds2
    assert all(f.suggestion for f in ac_findings), "every finding needs a suggestion"
    print(f"OK: A/FN/FA flagged as {sorted(kinds2)} with suggestions")

    print("\nALL CONFIG DIAGNOSTICS CHECKS PASSED")


if __name__ == "__main__":
    main()
