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
_ORIGINAL_RESOLVE = EngineeringClassService.resolve_config_codes


def _config_props(snapshot):
    """Properties that participate in configuration-code resolution.

    Purely coded properties are already authoritative. A mixed/partially coded
    property still participates so only its missing values need resolution.
    """
    return [
        p for p in snapshot.properties
        if p.values and len(p.values) >= 2
        and any(not (v.code or "").strip() for v in p.values)
    ]


def _add_unresolved_slice_hints(self, snapshot, config_props):
    """Expose an Ignore choice even when a config property has no decodable span.

    The core decoder only creates ``_slice_hints`` for properties that it can
    position in the article head. That made an unresolved configuration property
    impossible to keep in the base from Class Creation because the UI only shows
    the Ignore checkbox when a hint exists. An unresolved property is still a
    legitimate user decision: it can be left in the base instead of pretending
    that a missing code was decoded.
    """
    hints = dict(getattr(self, "_slice_hints", {}) or {})
    overrides = getattr(snapshot, "config_ignore_overrides", None) or {}
    layout = getattr(self, "_position_layout", {}) or {}
    for prop in config_props:
        pid = str(prop.id)
        if pid in hints:
            continue
        entry = layout.get(pid, {})
        hints[pid] = {
            "overlaps": "",
            "auto_ignore": False,
            "ignored": bool(overrides.get(pid, False)),
            "has_dependent_options": bool(
                getattr(prop, "has_dependent_options", False)
            ),
            "width": int(entry.get("width", 0) or 0),
            "position": entry.get("position"),
            "unresolved": True,
        }
    self._slice_hints = hints


def _decode_with_product_fallback(self, snapshot):
    if snapshot is None:
        return _ORIGINAL_DECODE(self, snapshot)

    apv = snapshot.article_property_value_ids or {}
    ppv = snapshot.product_property_value_ids or {}
    if not apv or not ppv:
        decoded = _ORIGINAL_DECODE(self, snapshot)
        config_props = _config_props(snapshot)
        if config_props:
            _add_unresolved_slice_hints(self, snapshot, config_props)
        return decoded

    config_props = _config_props(snapshot)
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
        decoded = _ORIGINAL_DECODE(self, snapshot)
        _add_unresolved_slice_hints(self, snapshot, config_props)
        return decoded

    original_apv = snapshot.article_property_value_ids
    try:
        snapshot.article_property_value_ids = merged
        # The legacy decoder can legitimately return a partial result here:
        # article-level properties may decode while a product-level fallback
        # property remains unresolved because of its positional layout. Do not
        # return early on a non-empty result; recover the fallback-only
        # properties below and merge them into the valid legacy result.
        decoded = _ORIGINAL_DECODE(self, snapshot) or {}

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
            len_groups = [aids for aids in value_groups.values() if aids]
            if len(value_groups) < 2 or len(len_groups) != len(value_groups):
                continue

            positions_by_value: dict[str, list[int]] = {}
            widths: set[int] = set()
            for vid, aids in value_groups.items():
                sample = heads.get(aids[0], "")
                if not sample:
                    break
                candidate_positions: list[int] = []
                for i in range(len(sample)):
                    chars = {
                        heads[aid][i]
                        for aid in aids
                        if i < len(heads.get(aid, ""))
                    }
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

        for pid, codes in recovered.items():
            decoded.setdefault(pid, {}).update(codes)
        _add_unresolved_slice_hints(self, snapshot, config_props)
        return decoded
    finally:
        snapshot.article_property_value_ids = original_apv


def _resolve_with_mixed_properties(self, snapshot):
    result = _ORIGINAL_RESOLVE(self, snapshot)
    if snapshot is None:
        return result
    ignore = getattr(snapshot, "config_ignore_overrides", None) or {}
    overrides = getattr(snapshot, "config_code_overrides", None) or {}
    stored_all = getattr(snapshot, "config_value_codes", None) or {}
    decoded_all = self.decode_config_codes_by_value_id(snapshot) or {}
    for prop in _config_props(snapshot):
        pid = str(prop.id)
        if ignore.get(pid) is True:
            continue
        ov = overrides.get(pid, {})
        stored = stored_all.get(pid, {})
        decoded = decoded_all.get(pid, {})
        merged = {}
        for value in prop.values:
            vid = str(value.id)
            if ov.get(vid):
                merged[vid] = ov[vid]
            elif (value.code or "").strip():
                merged[vid] = value.code.strip()
            elif stored.get(vid):
                merged[vid] = stored[vid]
            elif decoded.get(vid):
                merged[vid] = decoded[vid]
        if merged:
            result[pid] = merged
    return result


EngineeringClassService._decode_config_codes_by_value_id = _decode_with_product_fallback
EngineeringClassService.resolve_config_codes = _resolve_with_mixed_properties
