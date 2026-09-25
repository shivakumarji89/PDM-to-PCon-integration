"""ProductProfileService - structural-trait classifier.

A read-only classifier run AFTER the snapshot is fully loaded (never during the
PDM pull, which stays a pure fetch). It inspects the complete snapshot and
produces a :class:`~models.product_profile.ProductProfile` describing the
product's structural "method", which is persisted with the project and read by
downstream workflows to pick their approach.

Extensible by design: each trait is produced by one detector in ``_DETECTORS``;
adding a newly-discovered method is a one-line append, no rewrite.
"""
from __future__ import annotations

import re

from models.product_profile import ProductProfile, VariantGroup
from models.snapshot import Snapshot
from services.base_service import BaseService

# First words of ProductRange.Name that denote parts / meta buckets rather than
# configurable end-products (from the PDM survey). Matched case-insensitively.
_COMPONENT_BUCKETS = {
    "super", "allsuperproducts", "components", "fabric", "worktops",
    "accessories", "understructure", "worksurfaces", "preconfigured",
    "pair", "full",
}

# 'Base (token)' - the trailing parenthesised variant token on a property name.
_VARIANT = re.compile(r"^(.*?)\s*\(([^)]{1,6})\)\s*$")


class ProductProfileService(BaseService):
    """Detects a loaded product's structural traits and stores the profile."""

    def classify(self, snapshot: Snapshot | None) -> ProductProfile:
        """Run every detector over ``snapshot`` and store/return its profile."""
        profile = ProductProfile()
        if snapshot is None:
            return profile
        for detect in self._DETECTORS:
            detect(self, snapshot, profile)
        profile.traits = self._summarize(profile)
        snapshot.product_profile = profile
        return profile

    # -- detectors (each mutates the profile; append new ones to _DETECTORS) --

    def _detect_super_product(self, snapshot: Snapshot, profile: ProductProfile):
        product = snapshot.product
        profile.super_product = bool(product and product.is_super_product)

    def _detect_component_bucket(self, snapshot: Snapshot, profile: ProductProfile):
        product = snapshot.product
        name = (product.range_name if product else "") or ""
        first = name.strip().split(" ")[0].lower()
        profile.component_bucket = first in _COMPONENT_BUCKETS

    def _detect_property_coding(self, snapshot: Snapshot, profile: ProductProfile):
        props = snapshot.properties
        profile.total_properties = len(props)
        coded = uncoded = 0
        for p in props:
            if any((v.code or "").strip() for v in p.values):
                coded += 1
            else:
                uncoded += 1
        profile.coded_properties = coded
        profile.uncoded_properties = uncoded

    def _detect_dependent_options(self, snapshot: Snapshot, profile: ProductProfile):
        profile.dependent_option_properties = sum(
            1 for p in snapshot.properties if p.has_dependent_options
        )

    def _detect_model_suffix(self, snapshot: Snapshot, profile: ProductProfile):
        profile.model_suffix_properties = sum(
            1 for p in snapshot.properties
            if any((v.model_suffix or "").strip() for v in p.values)
        )

    def _detect_instance_variants(self, snapshot: Snapshot, profile: ProductProfile):
        # Instance variants are consecutive single UPPERCASE letters (A,B,C..);
        # word tokens like '(Arras)' are semantic variants, not instances.
        groups: dict[str, set] = {}
        for p in snapshot.properties:
            m = _VARIANT.match(p.name or "")
            if not m:
                continue
            base, token = m.group(1).strip(), m.group(2).strip()
            if len(token) == 1 and token.isalpha() and token.isupper():
                groups.setdefault(base, set()).add(token)
        profile.instance_variant_groups = [
            VariantGroup(base=b, variants=sorted(v))
            for b, v in sorted(groups.items()) if len(v) >= 2
        ]

    _DETECTORS = [
        _detect_super_product,
        _detect_component_bucket,
        _detect_property_coding,
        _detect_dependent_options,
        _detect_model_suffix,
        _detect_instance_variants,
    ]

    @staticmethod
    def _summarize(profile: ProductProfile) -> list[str]:
        tags: list[str] = []
        if profile.super_product:
            tags.append("super_product")
        if profile.component_bucket:
            tags.append("component_bucket")
        if profile.instance_variant_groups:
            tags.append("instance_variant")
        if profile.total_properties:
            if profile.uncoded_properties > profile.coded_properties:
                tags.append("mostly_uncoded")
            elif profile.coded_properties and not profile.uncoded_properties:
                tags.append("fully_coded")
        if profile.dependent_option_properties:
            tags.append("dependent_options")
        if profile.model_suffix_properties:
            tags.append("model_suffix")
        return tags
