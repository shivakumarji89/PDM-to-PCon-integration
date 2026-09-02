"""Permutation engine for the Builder (snapper-style OBX generation).

Pure, dependency-free functions that turn a set of selected articles and
property-value selections into the cartesian product of configurations, then
resolve hierarchy (parent -> child) dependencies. Ported from the snapper
generator's ``compute_permutations`` / ``expand_permutations_with_children``,
but driven from in-memory selections rather than OCD CSVs.
"""
from __future__ import annotations

import itertools
from typing import Any


def compute_permutations(
    articles: list[str],
    dimensions: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Cartesian product of ``articles`` x each property's selected values.

    ``dimensions`` maps a property name to its selected value codes. Returns a
    list of ``{"article": code, "properties": {prop: value}}``. Hierarchy child
    properties should be excluded here and injected later via
    :func:`expand_with_children`.
    """
    if not articles:
        return []
    if not dimensions:
        return [{"article": a, "properties": {}} for a in articles]

    prop_names = list(dimensions.keys())
    value_lists = [dimensions[p] for p in prop_names]
    out: list[dict[str, Any]] = []
    for article in articles:
        for combo in itertools.product(*value_lists):
            out.append(
                {"article": article, "properties": dict(zip(prop_names, combo))}
            )
    return out


def expand_with_children(
    permutations: list[dict[str, Any]],
    child_resolutions: dict[str, dict[str, Any]],
    distribute: bool = False,
) -> list[dict[str, Any]]:
    """Inject hierarchy child values into each permutation.

    ``child_resolutions`` maps a child property to ``{"parent": <parent prop>,
    "map": {parent_value: [child_values]}}``. For each permutation the child
    value is chosen from its parent's selected value:

    * ``distribute=False`` (default) - assign the first child value (one row).
    * ``distribute=True`` - expand into one row per child value (full coverage).

    A permutation whose parent value has no mapping is left unchanged.
    """
    if not child_resolutions:
        return permutations

    result = permutations
    for child_prop, spec in child_resolutions.items():
        parent = spec.get("parent")
        mapping = spec.get("map") or {}
        next_result: list[dict[str, Any]] = []
        for perm in result:
            parent_value = perm["properties"].get(parent)
            child_values = mapping.get(parent_value) if parent_value is not None else None
            if not child_values:
                next_result.append(perm)
                continue
            if distribute:
                for cv in child_values:
                    clone = {
                        "article": perm["article"],
                        "properties": {**perm["properties"], child_prop: cv},
                    }
                    next_result.append(clone)
            else:
                perm["properties"][child_prop] = child_values[0]
                next_result.append(perm)
        result = next_result
    return result


def build_varcode(article_class: str, properties: dict[str, str]) -> str:
    """OFML varcode ``CLASS.Prop=Val;CLASS.Prop2=Val2`` for one article class."""
    if not properties:
        return ""
    return ";".join(f"{article_class}.{k}={v}" for k, v in properties.items())


def build_varcode_multi(
    properties: dict[str, str],
    property_to_class: dict[str, str],
    default_class: str = "",
) -> str:
    """OFML varcode with a per-property article-class prefix.

    Falls back to ``default_class`` for any property without a specific class.
    """
    parts: list[str] = []
    for prop_name, value in properties.items():
        cls = property_to_class.get(prop_name) or default_class
        if cls and prop_name:
            parts.append(f"{cls}.{prop_name}={value}")
    return ";".join(parts)
