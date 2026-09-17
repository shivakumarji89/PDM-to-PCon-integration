"""Compatibility fix for mixed article-level and product-level PDM values.

Class Creation may receive BaseAttributeValues for some properties while
ProductAttributeValues still carries the remaining product configuration.
The core decoder historically used whole-row fallback, which dropped the
product-level properties whenever any article-level values existed.
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
    fallback_properties: set[str] = set()
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

        for pid, vids in product_values_by_property.items():
            if len(vids) == 1:
                merged_values.append(vids[0])
                fallback_properties.add(pid)
                changed = True

        merged[aid] = merged_values

    if not changed:
        return _ORIGINAL_DECODE(self, snapshot)

    original_apv = snapshot.article_property_value_ids
    try:
        snapshot.article_property_value_ids = merged
        decoded = _ORIGINAL_DECODE(self, snapshot)
        if decoded:
            return decoded

        # The completed signature can still be ambiguous to the legacy
        # positional decoder when the product-level property is the only source
        # for that property. Recover those properties directly from their value
        # groups. A property is accepted only when each of its values maps to one
        # stable, minimal contiguous run and the runs are consistent across all
        # values. Existing article-level properties are left entirely to the
        # original decoder.
        by_value: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        heads: dict[str, str] = {}
        assignments: dict[str, dict[str, str]] = defaultdict(dict)
        for article in snapshot.articles:
            aid = str(article.id)
            head = (getattr(article, "code", "") or "").split(".", 1)[0]
            if not head:
                continue
            heads[aid] = head
            for vid in merged.get(aid, []):
                pid = value_to_prop.get(str(vid))
                if pid is not None:
                    assignments[aid][pid] = str(vid)

        for aid, props in assignments.items():
            for pid, vid in props.items():
                if pid in fallback_properties:
                    by_value[pid][vid].append(aid)

        recovered: dict[str, dict[str, str]] = {}
        for pid, value_groups in by_value.items():
            if len(value_groups) < 2:
                continue
            positions_by_value: dict[str, list[int]] = {}
            widths: set[int] = set()
            for vid, aids in value_groups.items():
                if not aids:
                    continue
                sample = heads[aids[0]]
                candidate_positions: list[int] = []
                for i in range(len(sample)):
                    chars = {heads[aid][i] for aid in aids if i < len(heads[aid])}
                    if len(chars) == 1:
                        candidate_positions.append(i)
                runs: list[tuple[int, int]] = []
                if candidate_positions:
                    start = prev = candidate_positions[0]
                    for pos in candidate_positions[1:]:
                        if pos == prev + 1:
                            prev = pos
                        else:
                            runs.append((start, prev + 1))
                            start = prev = pos
                    runs.append((start, prev + 1))
                if len(runs) != 1:
                    break
                st, en = runs[0]
                positions_by_value[vid] = list(range(st, en))
                widths.add(en - st)
            else:
                if not positions_by_value or len(widths) != 1:
                    continue
                common_positions = set.intersection(
                    *(set(pos) for pos in positions_by_value.values())
                )
                if not common_positions:
                    continue
                ordered = sorted(common_positions)
                start = ordered[0]
                if ordered != list(range(start, start + len(ordered))):
                    continue
                codes: dict[str, str] = {}
                for vid, aids in value_groups.items():
                    sample = heads[aids[0]]
                    codes[vid] = sample[start:start + len(ordered)]
                if all(codes.values()) and len(set(codes.values())) == len(codes):
                    recovered[pid] = codes

        if decoded is None:
            decoded = {}
        for pid, codes in recovered.items():
            decoded.setdefault(pid, {}).update(codes)
        return decoded
    finally:
        snapshot.article_property_value_ids = original_apv


EngineeringClassService._decode_config_codes_by_value_id = _decode_with_product_fallback
