"""Headless validation for the ProductProfile classifier + persistence.

Verifies, without a live PDM:
  * super-product, component-bucket, coded/uncoded, dependent-options,
    model-suffix and instance-variant (A/B) detection;
  * instance variants require consecutive UPPERCASE letters (semantic word
    tokens are ignored);
  * the profile round-trips through snapshot serialization (persists with the
    project).

Run:  $env:QT_QPA_PLATFORM="offscreen"; $env:PYTHONPATH="."; \
      python scripts/validate_product_profile.py
"""
from __future__ import annotations

import sys

from core.application_context import ApplicationContext
from models.product import Product
from models.property import Property
from models.property_value import PropertyValue
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict


def _prop(pid, name, *, code="", suffix="", dependent=False):
    p = Property(id=pid, name=name, has_dependent_options=dependent)
    p.values.append(
        PropertyValue(id=pid + "v", property_id=pid, value="V", code=code,
                      model_suffix=suffix)
    )
    return p


def main() -> int:
    ctx = ApplicationContext()
    svc = ctx.product_profile_service

    # 1) Ratio-like: super-product desk with A/B instance variants, mixed coding.
    product = Product(id="p1", code="RY3X", name="Ratio", range_name="Ratio Desk",
                      is_super_product=True)
    snap = ctx.snapshot_manager.create_empty_snapshot(product)
    snap.properties.extend([
        _prop("a", "Desk type (A)"),               # uncoded
        _prop("b", "Desk type (B)"),               # uncoded
        _prop("c", "Control box (A)"),
        _prop("d", "Control box (B)"),
        _prop("e", "Leg colour", code="R", dependent=True),  # coded + dependent
        _prop("f", "Depth (Arras)"),               # semantic token -> NOT a variant
    ])
    snap.property_values.extend(v for p in snap.properties for v in p.values)

    prof = svc.classify(snap)
    assert prof.super_product is True
    assert prof.component_bucket is False, "Ratio is a real series, not a bucket"
    assert prof.total_properties == 6
    assert prof.coded_properties == 1 and prof.uncoded_properties == 5
    assert prof.dependent_option_properties == 1
    bases = {g.base: g.variants for g in prof.instance_variant_groups}
    assert bases == {"Desk type": ["A", "B"], "Control box": ["A", "B"]}, bases
    assert "Depth" not in bases, "semantic '(Arras)' must not be an instance variant"
    assert set(prof.traits) >= {
        "super_product", "instance_variant", "mostly_uncoded", "dependent_options"
    }, prof.traits
    assert snap.product_profile is prof, "profile stored on the snapshot"
    print("OK: super + A/B instance variants + mixed coding + dependent detected")

    # 2) Simple fully-coded product, no variants, not super.
    p2 = Product(id="p2", code="S", name="Simple", range_name="Sayl",
                 is_super_product=False)
    s2 = ctx.snapshot_manager.create_empty_snapshot(p2)
    s2.properties.extend([
        _prop("x", "Colour", code="R"),
        _prop("y", "Size", code="L", suffix="_L"),
    ])
    s2.property_values.extend(v for p in s2.properties for v in p.values)
    prof2 = svc.classify(s2)
    assert prof2.super_product is False
    assert prof2.coded_properties == 2 and prof2.uncoded_properties == 0
    assert prof2.model_suffix_properties == 1
    assert not prof2.instance_variant_groups
    assert "fully_coded" in prof2.traits and "model_suffix" in prof2.traits
    assert "super_product" not in prof2.traits
    print("OK: simple fully-coded product classified (suffix detected)")

    # 3) Component bucket via range name.
    p3 = Product(id="p3", code="C", name="Comp", range_name="Components misc")
    s3 = ctx.snapshot_manager.create_empty_snapshot(p3)
    prof3 = svc.classify(s3)
    assert prof3.component_bucket is True
    assert "component_bucket" in prof3.traits
    print("OK: component bucket detected from range name")

    # 4) Persistence: profile survives a serialization round-trip.
    restored = snapshot_from_dict(snapshot_to_dict(snap))
    rp = restored.product_profile
    assert rp.super_product is True
    assert rp.coded_properties == 1 and rp.uncoded_properties == 5
    rbases = {g.base: g.variants for g in rp.instance_variant_groups}
    assert rbases == {"Desk type": ["A", "B"], "Control box": ["A", "B"]}, rbases
    assert set(rp.traits) == set(snap.product_profile.traits)
    print("OK: profile persists through serialization round-trip")

    print("ALL PRODUCT PROFILE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
