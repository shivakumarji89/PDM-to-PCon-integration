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

        product_values_by_property: dict[str, set[str]] = defaultdict(set)
        for vid in (ppv.get(product_of.get(aid, ""), []) or []):
            vid = str(vid)
            pid = value_to_prop.get(vid)
            if pid is not None and pid not in article_property_ids:
                product_values_by_property[pid].add(vid)

        # ProductAttributeValues can contain repeated rows for the same
        # AttributeValueId. Treat repeated copies as one value; otherwise a
        # valid product-level B property would be incorrectly rejected as
        # ambiguous before it reaches the decoder.
        for pid, vids in product_values_by_property.items():
            if len(vids) == 1:
                merged_values.append(next(iter(vids)))
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

        # Recover product-level-only properties, but preserve the exact structural
        # boundary used by the legacy decoder: head length plus the set of
        # configuration properties carried by the article. Mixing different
        # structures can manufacture a false positional code.
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

        by_structure: dict[tuple[int, frozenset[str]], list[str]] = defaultdict(list)
        for aid, head in heads.items():
            by_structure[(len(head), frozenset(assignments[aid].keys()))].append(aid)

        recovered_by_value: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        recovered_positions: dict[str, set[tuple[int, int]]] = defaultdict(set)

        for (head_len, signature), aids in by_structure.items():
            if len(aids) < 2:
                continue
            for pid in fallback_properties:
                if pid not in signature:
                    continue
                value_groups: dict[str, list[str]] = defaultdict(list)
                for aid in aids:
                    vid = assignments[aid].get(pid)
                    if vid is not None:
                        value_groups[vid].append(aid)
                if len(value_groups) < 2:
                    continue

                positions: list[int] = []
                for i in range(head_len):
                    if all(
                        len({heads[aid][i] for aid in group_aids}) == 1
                        for group_aids in value_groups.values()
                    ) and len({heads[group_aids[0]][i] for group_aids in value_groups.values()}) > 1:
                        positions.append(i)

                if not positions:
                    continue
                runs: list[tuple[int, int]] = []
                run_start = previous = positions[0]
                for pos in positions[1:]:
                    if pos == previous + 1:
                        previous = pos
                    else:
                        runs.append((run_start, previous + 1))
                        run_start = previous = pos
                runs.append((run_start, previous + 1))
                if len(runs) != 1:
                    continue

                start_pos, end_pos = runs[0]
                recovered_positions[pid].add((start_pos, end_pos - start_pos))
                for vid, group_aids in value_groups.items():
                    code = heads[group_aids[0]][start_pos:end_pos]
                    if code:
                        recovered_by_value[pid][vid].add(code)

        recovered: dict[str, dict[str, str]] = {}
        for pid, value_codes in recovered_by_value.items():
            positions = recovered_positions.get(pid, set())
            if len(positions) != 1:
                continue
            codes = {
                vid: next(iter(candidates))
                for vid, candidates in value_codes.items()
                if len(candidates) == 1
            }
            if len(codes) != len(value_codes):
                continue
            if len(codes) >= 2 and len(set(codes.values())) == len(codes):
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
