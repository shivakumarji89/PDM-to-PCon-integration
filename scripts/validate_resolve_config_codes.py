"""Validate the merged config-code resolver and its persistence.

resolve_config_codes merges correlation + per-article slice, keeping only
per-concept collision-free codes, and lets a user override win. Overrides
persist with the project.

Run: python scripts/validate_resolve_config_codes.py
"""
from core.application_context import ApplicationContext
from models.article import Article
from models.product import Product
from models.property import Property
from models.property_value import PropertyValue
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict


def _override_and_persist():
    ctx = ApplicationContext()
    snap = ctx.snapshot_manager.create_empty_snapshot(Product(id="pA", code="A"))
    snap.id = "pA"
    prop = Property(id="T", name="Type", has_dependent_options=True, code_width=1,
                    values=[
                        PropertyValue(id="v1", property_id="T", value="Alpha"),
                        PropertyValue(id="v2", property_id="T", value="Beta"),
                    ])
    snap.properties = [prop]
    snap.property_values = list(prop.values)
    snap.articles = [Article(id="a1", code="A1", product_id="pA")]
    snap.product_property_value_ids = {"pA": ["v1"]}

    svc = ctx.engineering_class_service
    # No correlation/slice evidence (single product) -> unresolved without help.
    assert svc.resolve_config_codes(snap).get("T", {}) == {}, "should be empty"

    # User override wins.
    snap.config_code_overrides = {"T": {"v1": "Q", "v2": "Z"}}
    svc._resolve_key = None  # bust cache (overrides changed)
    resolved = svc.resolve_config_codes(snap).get("T", {})
    assert resolved == {"v1": "Q", "v2": "Z"}, resolved
    print("OK override wins")

    # Overrides survive save -> load.
    restored = snapshot_from_dict(snapshot_to_dict(snap))
    assert restored.config_code_overrides == {"T": {"v1": "Q", "v2": "Z"}}, \
        restored.config_code_overrides
    print("OK overrides persist through serialization")


def main() -> int:
    _override_and_persist()
    print("\nALL RESOLVE CONFIG CODE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
