"""Compatibility fix for mixed article-level and product-level PDM values.

Class Creation may receive BaseAttributeValues for some properties while
ProductAttributeValues still carries the remaining product configuration.
The core decoder historically used whole-row fallback, which dropped the
product-level properties whenever any article-level values existed.

This module keeps the existing decoder unchanged and supplies the missing
product-level values per property before decoding.
"""
from __future__ import annotations

from collections import defaultdict

from services.engineering.engineering_class_service import EngineeringClassService


_ORIGINAL_DECODE = EngineeringClassService._decode_config_codes_by_value_id


def _decode_with_product_fallback(self, snapshot):
    if snapshot is None:
        return _ORIGINAL_DECODE(self, snapshot)

    apv = snapshot.article_property_value_ids or {}
    ppv = snapshot.product_property_value_ids or {}
    if not apv or not ppv:
        return _ORIGINAL_DECODE(self, snapshot)

    config_props = [
        p for p in snapshot.properties
        if p.values and not any((v.code or "").strip() for v in p.values)
    ]
    if not config_props:
        return _ORIGINAL_DECODE(self, snapshot)

    value_to_prop = {
        str(v.id): str(p.id)
        for p in config_props
        for v in p.values
    }
    product_of = {
        str(a.id): str(getattr(a, "product_id", "") or "")
        for a in snapshot.articles
    }

    merged = {}
    changed = False
    for article in snapshot.articles:
        aid = str(article.id)
        article_values = [str(v) for v in (apv.get(aid) or [])]
        merged_values = list(article_values)
        article_property_ids = {
            value_to_prop[vid]
            for vid in article_values
            if vid in value_to_prop
        }

        product_values_by_property = defaultdict(list)
        for vid in (ppv.get(product_of.get(aid, ""), []) or []):
            vid = str(vid)
            pid = value_to_prop.get(vid)
            if pid is not None and pid not in article_property_ids:
                product_values_by_property[pid].append(vid)

        # Only supplement a missing property when the product carries exactly
        # one value for it. Multiple product values are ambiguous and must not
        # be guessed.
        for vids in product_values_by_property.values():
            if len(vids) == 1:
                merged_values.append(vids[0])
                changed = True

        merged[aid] = merged_values

    if not changed:
        return _ORIGINAL_DECODE(self, snapshot)

    # The decoder's positional result is correct only when the supplied
    # property signature is complete. The original decoder decides ownership
    # from the actual values, so use the merged rows only for this call.
    original_apv = snapshot.article_property_value_ids
    try:
        snapshot.article_property_value_ids = merged
        return _ORIGINAL_DECODE(self, snapshot)
    finally:
        snapshot.article_property_value_ids = original_apv


EngineeringClassService._decode_config_codes_by_value_id = _decode_with_product_fallback
