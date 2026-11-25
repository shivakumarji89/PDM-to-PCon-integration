"""Shared article selection scope for the Class Creation workspace and MDB export.

The Articles page's Export-column checkboxes are the single source of truth.
This module resolves the selected source articles to the PDM properties and
options they actually carry, so display and export use identical filtering.
"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field

from services.engineering.article_value_links import carried_value_ids, products_with_article_links
from services.engineering.class_naming import ATTRIBUTE, OPTION, VISUAL, class_kind

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClassCreationArticleScope:
    article_ids: frozenset[str] = frozenset()
    property_ids: frozenset[str] = frozenset()
    option_ids: frozenset[str] = frozenset()
    property_value_ids: dict[str, frozenset[str]] = field(default_factory=dict)
    option_value_ids: dict[str, frozenset[str]] = field(default_factory=dict)
    product_ranges: frozenset[str] = frozenset()
    group_names: frozenset[str] = frozenset()


def _category(snapshot) -> str:
    product = getattr(snapshot, "product", None)
    label = (
        (getattr(product, "category", "") or getattr(product, "range_name", "") or "").strip()
        if product is not None else ""
    )
    if label:
        return label
    metadata = getattr(snapshot, "metadata", None)
    return (getattr(metadata, "product_code", "") or "").strip() or "Class"


def _article_set_group_name(snapshot, article_id: str) -> str:
    """Mirror EngineeringClassService's stable article-set group naming."""
    used: set[str] = set()
    category = _category(snapshot)
    for index, aset in enumerate(getattr(snapshot, "article_sets", []) or []):
        base = (getattr(aset, "base_code", "") or "").strip() or f"{category}_{index + 1}"
        unique, suffix = base, 2
        while unique in used:
            unique, suffix = f"{base}_{suffix}", suffix + 1
        used.add(unique)
        if str(article_id) in {
            str(value) for value in (getattr(aset, "article_ids", []) or [])
        }:
            return unique
    return ""


def _uses_base_basis(snapshot) -> bool:
    return (
        bool(getattr(snapshot, "split_classes_by_group", False))
        and str(getattr(snapshot, "class_group_basis", "") or "").lower() == "base_article"
    )


def _explicit_base_of(snapshot, article_id: str) -> str:
    """Canonical base of one article from the resolver's own explicit tiers (reduced article,
    base-length override) - no price base, which needs the application context."""
    from services.engineering.base_identity import explicit_base

    code = next((str(getattr(a, "code", "") or "").strip() for a in (getattr(snapshot, "articles", []) or [])
                 if str(getattr(a, "id", "")) == str(article_id)), "")
    overrides = getattr(snapshot, "base_length_overrides", None) or {}
    for family in getattr(getattr(snapshot, "engineering", None), "families", None) or []:
        for member in getattr(family, "members", None) or []:
            if str(getattr(member, "article_id", "")) == str(article_id):
                return (explicit_base(member, code, overrides)[0] or "").strip()
    return ""


def build_class_creation_scope(
    snapshot, selected_article_ids, base_of=None
) -> ClassCreationArticleScope:
    """Resolve selected article IDs to the exact property/option IDs and values.

    ``base_of`` (``{article id: canonical base}``) is only used on the base-article grouping
    basis to name the selected groups; callers hold it from ``base_code_entries``."""
    selected = {str(value) for value in (selected_article_ids or set()) if str(value)}
    articles = {
        str(getattr(article, "id", "")): article
        for article in (getattr(snapshot, "articles", []) or [])
        if getattr(article, "id", None) is not None
    }
    selected &= set(articles)
    if not selected:
        return ClassCreationArticleScope()

    property_by_value: dict[str, str] = {}
    for prop in getattr(snapshot, "properties", []) or []:
        pid = str(getattr(prop, "id", "") or "")
        for value in getattr(prop, "values", []) or []:
            property_by_value[str(getattr(value, "id", "") or "")] = pid
    for value in getattr(snapshot, "property_values", []) or []:
        property_by_value[str(getattr(value, "id", "") or "")] = str(
            getattr(value, "property_id", "") or ""
        )

    option_by_value: dict[str, str] = {}
    for option in getattr(snapshot, "options", []) or []:
        oid = str(getattr(option, "id", "") or "")
        for value in getattr(option, "values", []) or []:
            option_by_value[str(getattr(value, "id", "") or "")] = oid
    for value in getattr(snapshot, "option_values", []) or []:
        option_by_value[str(getattr(value, "id", "") or "")] = str(
            getattr(value, "option_id", "") or ""
        )

    article_values = getattr(snapshot, "article_property_value_ids", None) or {}
    product_values = getattr(snapshot, "product_property_value_ids", None) or {}
    product_options = getattr(snapshot, "product_option_value_ids", None) or {}
    product_ranges = getattr(snapshot, "product_range", None) or {}

    property_ids: set[str] = set()
    option_ids: set[str] = set()
    property_value_ids: dict[str, set[str]] = {}
    option_value_ids: dict[str, set[str]] = {}
    selected_ranges: set[str] = set()
    # Product values are the menu a product OFFERS, not what one article carries. Article-level
    # BaseAttributeValues therefore win for the whole product as soon as any of its articles has
    # them; an article without rows then contributes nothing. The product menu is used only when
    # no article of the product has article-level links (it is then the only data there is).
    linked_products = products_with_article_links(articles.values(), article_values)
    fallback_logged: set[str] = set()
    for article_id in selected:
        article = articles[article_id]
        product_id = str(getattr(article, "product_id", "") or "")
        raw_values, used_fallback = carried_value_ids(
            article_id, product_id, article_values, product_values, linked_products)
        if used_fallback and product_id not in fallback_logged:
            fallback_logged.add(product_id)
            _log.info(
                "Class scope: product %s has no article-level BaseAttributeValues; "
                "using product-level values (%d) for its articles.",
                product_id, len(raw_values),
            )
        for value_id in raw_values:
            value_id = str(value_id)
            property_id = property_by_value.get(value_id)
            if property_id:
                property_ids.add(property_id)
                property_value_ids.setdefault(property_id, set()).add(value_id)
        for value_id in product_options.get(product_id, []) or []:
            value_id = str(value_id)
            option_id = option_by_value.get(value_id)
            if option_id:
                option_ids.add(option_id)
                option_value_ids.setdefault(option_id, set()).add(value_id)
        raw_range = product_ranges.get(product_id)
        if raw_range:
            selected_ranges.add(str(raw_range))

    # ArticleSet is the richer Class Creation mapping. It includes derived
    # ModelSuffix values and exact per-value article coverage that may not be
    # represented in the direct PDM BaseAttributeValues links.
    for article_set in getattr(snapshot, "article_sets", []) or []:
        selected_in_set = selected.intersection(
            str(value) for value in (getattr(article_set, "article_ids", []) or [])
        )
        if not selected_in_set:
            continue
        for attribute in getattr(article_set, "properties", []) or []:
            property_id = str(getattr(attribute, "id", "") or "")
            if not property_id:
                continue
            property_ids.add(property_id)
            for value in getattr(attribute, "values", []) or []:
                value_id = str(getattr(value, "id", "") or "")
                carriers = {str(a) for a in (getattr(value, "article_ids", []) or [])}
                if value_id and selected_in_set.intersection(carriers):
                    property_value_ids.setdefault(property_id, set()).add(value_id)
        for option in getattr(article_set, "options", []) or []:
            option_id = str(getattr(option, "id", "") or "")
            if not option_id:
                continue
            option_ids.add(option_id)
            for value in getattr(option, "values", []) or []:
                value_id = str(getattr(value, "id", "") or "")
                carriers = {str(a) for a in (getattr(value, "article_ids", []) or [])}
                if value_id and selected_in_set.intersection(carriers):
                    option_value_ids.setdefault(option_id, set()).add(value_id)

    group_names: set[str] = set()
    if _uses_base_basis(snapshot):
        if base_of is None:
            from services.engineering.base_identity import resolve_base_identities

            base_of = resolve_base_identities(snapshot).by_article
        group_names = {
            str(base_of.get(a) or "").strip() for a in selected if str(base_of.get(a) or "").strip()
        }
    elif getattr(snapshot, "split_classes_by_group", False):
        service = getattr(getattr(snapshot, "_context", None), "engineering_class_service", None)
        # Resolve group labels from the same persisted grouping rules used by
        # Class Creation; this is best-effort and does not mutate the snapshot.
        try:
            from services.engineering.engineering_class_service import EngineeringClassService
            service = service or EngineeringClassService(None)
            groups = service.resolve_class_groups(snapshot, _category(snapshot))
        except Exception:
            groups = []
        if str(getattr(snapshot, "class_group_basis", "") or "range").lower() == "article_set":
            for article_id in selected:
                group_name = _article_set_group_name(snapshot, article_id)
                if group_name:
                    group_names.add(group_name)
        else:
            for group in groups:
                if selected_ranges.intersection(str(r) for r in (getattr(group, "source_ranges", ()) or ())):
                    group_names.add(str(group.name))
            # General carries product-wide properties/options that have no
            # ProductRange; keep it only when selected articles carry one.
            ranged_prop_ids = {
                str(pid) for pid, ranges in (getattr(snapshot, "attribute_range", None) or {}).items()
                if ranges
            }
            if property_ids - ranged_prop_ids:
                group_names.add("General")

    return ClassCreationArticleScope(
        article_ids=frozenset(selected),
        property_ids=frozenset(property_ids),
        option_ids=frozenset(option_ids),
        property_value_ids={k: frozenset(v) for k, v in property_value_ids.items()},
        option_value_ids={k: frozenset(v) for k, v in option_value_ids.items()},
        product_ranges=frozenset(selected_ranges),
        group_names=frozenset(group_names),
    )


def classes_for_article(snapshot, classes, article_id: str, base_of=None) -> list:
    """Return copies of the classes applicable to one selected article.

    The class prefix follows the same split-by-range/article-set configuration
    used by Class Creation. Visual definitions remain product-wide.
    """
    base_token = ""
    if _uses_base_basis(snapshot):
        base_token = str((base_of or {}).get(str(article_id)) or "").strip() \
            or _explicit_base_of(snapshot, article_id)
        if not base_token:
            return []  # the base is unresolved here: never guess another base's classes
        base_of = {str(article_id): base_token}
    scope = build_class_creation_scope(snapshot, {str(article_id)}, base_of=base_of)
    if not scope.article_ids:
        return []
    product = getattr(snapshot, "product", None)
    category = _category(snapshot)
    token = ""
    if base_token:
        token = base_token  # exact canonical base code, never re-spelled
    elif getattr(snapshot, "split_classes_by_group", False):
        basis = str(getattr(snapshot, "class_group_basis", "") or "range").lower()
        group_name = ""
        if basis == "article_set":
            group_name = _article_set_group_name(snapshot, str(article_id))
        else:
            article = next(
                (a for a in (getattr(snapshot, "articles", []) or [])
                 if str(getattr(a, "id", "")) == str(article_id)), None
            )
            product_id = str(getattr(article, "product_id", "") or "") if article else ""
            raw_range = (getattr(snapshot, "product_range", None) or {}).get(product_id)
            if raw_range:
                try:
                    from services.engineering.engineering_class_service import EngineeringClassService
                    groups = EngineeringClassService(None).resolve_class_groups(snapshot, category)
                    group = next(
                        (g for g in groups if str(raw_range) in
                         {str(r) for r in (getattr(g, "source_ranges", ()) or ())}),
                        None,
                    )
                    group_name = str(group.name) if group else ""
                except Exception:
                    group_name = ""
            else:
                group_name = "General"
        if group_name:
            try:
                from services.engineering.engineering_class_service import EngineeringClassService
                token = EngineeringClassService._group_token(group_name)
            except Exception:
                token = ""
    else:
        try:
            from services.engineering.engineering_class_service import EngineeringClassService
            token = EngineeringClassService._group_token(category)
        except Exception:
            token = ""

    result = []
    for cls in classes or []:
        name = str(getattr(cls, "name", "") or "")
        class_token = name.rsplit("_", 1)[0]
        if token and (class_token.casefold() != token.casefold() if base_token
                      else class_token != token):
            continue
        suffix = class_kind(name) or ""
        relevant = []
        for assignment in getattr(cls, "properties", []) or []:
            pid = str(getattr(assignment, "property_id", "") or "")
            if suffix == ATTRIBUTE and pid in scope.property_ids:
                relevant.append(assignment)
            elif suffix == OPTION and pid in scope.option_ids:
                relevant.append(assignment)
            elif suffix == VISUAL:
                relevant.append(assignment)
            elif pid in scope.property_ids or pid in scope.option_ids:
                relevant.append(assignment)
        if not relevant:
            continue
        selected_class = copy.copy(cls)
        selected_class.properties = relevant
        result.append(selected_class)
    return result
