"""Build valid article permutations from the established Snapshot."""
from __future__ import annotations

from functools import lru_cache

from services.base_service import BaseService
from models.snapshot import Snapshot
from services.article_obx.article_obx_models import (
    ArticleConfigurationValue,
    ArticlePermutation,
)


class ArticlePermutationService(BaseService):
    """Resolve real PDM Articles into deterministic configuration permutations.

    Articles are the authoritative existence proof. The service never creates a
    blind Cartesian product. Property selections come from BaseAttributeValues;
    option selections are decoded from the concrete article number against the
    product's offered option values and existing dependency graph.
    """

    def build(self, snapshot: Snapshot | None = None) -> list[ArticlePermutation]:
        snapshot = snapshot if snapshot is not None else self.context.active_snapshot
        if snapshot is None:
            return []

        property_by_value = {
            str(value.id): value
            for value in snapshot.property_values
            if value.id is not None
        }
        property_by_id = {
            str(prop.id): prop
            for prop in snapshot.properties
            if prop.id is not None
        }
        option_by_value = {
            str(value.id): value
            for option in snapshot.options
            for value in option.values
            if value.id is not None
        }
        option_by_id = {
            str(option.id): option
            for option in snapshot.options
            if option.id is not None
        }

        base_by_article: dict[str, str] = {}
        for article_set in getattr(snapshot, "article_sets", []) or []:
            base = (article_set.base_code or "").strip()
            for article_id in article_set.article_ids:
                article_id = str(article_id)
                if article_id not in base_by_article and base:
                    base_by_article[article_id] = base

        permutations: list[ArticlePermutation] = []
        seen_article_ids: set[str] = set()

        for article in snapshot.articles:
            article_id = str(article.id or "")
            article_code = (article.code or "").strip()
            if not article_id or not article_code or article_id in seen_article_ids:
                continue
            seen_article_ids.add(article_id)

            property_values = self._resolve_properties(
                snapshot,
                article_id,
                str(article.product_id or ""),
                property_by_value,
                property_by_id,
            )

            selected_property_ids = {v.value_id for v in property_values}
            selected_options = self._resolve_options(
                snapshot=snapshot,
                article_code=article_code,
                base_code=base_by_article.get(article_id, ""),
                product_id=str(article.product_id or ""),
                selected_property_value_ids=selected_property_ids,
                option_by_value=option_by_value,
                option_by_id=option_by_id,
            )

            permutations.append(
                ArticlePermutation(
                    article_id=article_id,
                    product_id=str(article.product_id or ""),
                    base_code=base_by_article.get(article_id, article_code),
                    final_article=article_code,
                    name=article.name or "",
                    description=article.description or "",
                    quantity=article.quantity or 1,
                    is_super_item=bool(article.is_super_item),
                    properties=tuple(property_values),
                    options=tuple(selected_options),
                )
            )

        return permutations

    @staticmethod
    def _resolve_properties(
        snapshot: Snapshot,
        article_id: str,
        product_id: str,
        property_by_value: dict,
        property_by_id: dict,
    ) -> list[ArticleConfigurationValue]:
        selected_ids = [
            str(value_id)
            for value_id in (
                snapshot.article_property_value_ids.get(article_id, [])
                or snapshot.product_property_value_ids.get(product_id, [])
            )
        ]
        values: list[ArticleConfigurationValue] = []
        for value_id in selected_ids:
            pv = property_by_value.get(value_id)
            if pv is None:
                continue
            prop = property_by_id.get(str(pv.property_id or ""))
            if prop is None:
                continue
            values.append(
                ArticleConfigurationValue(
                    kind="property",
                    entity_id=str(prop.id),
                    value_id=value_id,
                    name=prop.name or "",
                    value=pv.value or "",
                    code=(pv.code or "").replace("#", ""),
                    display_order=prop.display_order or 0,
                )
            )
        values = ArticlePermutationService._dedupe_values(values)
        values.sort(key=lambda x: (x.display_order, x.name, x.value_id))
        return values

    @classmethod
    def _resolve_options(
        cls,
        snapshot: Snapshot,
        article_code: str,
        base_code: str,
        product_id: str,
        selected_property_value_ids: set[str],
        option_by_value: dict,
        option_by_id: dict,
    ) -> list[ArticleConfigurationValue]:
        """Decode selected options from the article-code suffix.

        Only offered values participate. DependentAttributeValues and
        DependentOptionValues narrow that candidate set. A dynamic-programming
        matcher finds complete, non-overlapping option selections whose codes
        exactly equal the article suffix. Zero matches means no option evidence;
        multiple matches are deliberately left unresolved rather than guessed.
        """
        offered_ids = {
            str(v)
            for v in (snapshot.product_option_value_ids.get(product_id, []) or [])
        }
        if not offered_ids:
            return []

        offered_by_option: dict[str, list] = {}
        for value_id in offered_ids:
            value = option_by_value.get(value_id)
            if value is None:
                continue
            option_id = str(value.option_id or "")
            if option_id:
                offered_by_option.setdefault(option_id, []).append(value)

        # Existing dependency graph: a selected property can enable additional
        # option values; selected parent option values can enable child values.
        # Dependency values are additive to the product-level offered set.
        enabled_ids = set(offered_ids)
        attribute_deps = getattr(snapshot, "attribute_option_dependencies", {}) or {}
        option_deps = getattr(snapshot, "option_option_dependencies", {}) or {}
        for property_value_id in selected_property_value_ids:
            enabled_ids.update(
                str(v) for v in attribute_deps.get(str(property_value_id), []) or []
            )

        candidates_by_option: dict[str, list] = {}
        for value_id in enabled_ids:
            value = option_by_value.get(value_id)
            if value is None:
                continue
            option_id = str(value.option_id or "")
            if not option_id:
                continue
            candidates_by_option.setdefault(option_id, []).append(value)

        if not candidates_by_option:
            return []

        # The reduced/base article is the known fixed portion. Only the tail is
        # decoded here. If the base is not a prefix, there is no safe suffix to
        # interpret as options.
        if not base_code or not article_code.startswith(base_code):
            return []
        suffix = article_code[len(base_code):]
        if not suffix:
            return []

        for values in candidates_by_option.values():
            values.sort(
                key=lambda v: (
                    -(len((v.code or "").replace("#", ""))),
                    getattr(v, "display_order", None) is None,
                    getattr(v, "display_order", None) or 0,
                    str(v.id),
                )
            )

        option_ids = sorted(
            candidates_by_option,
            key=lambda oid: (
                getattr(option_by_id.get(oid), "display_order", None) is None,
                getattr(option_by_id.get(oid), "display_order", None) or 0,
                getattr(option_by_id.get(oid), "name", "") or "",
                oid,
            ),
        )

        # An option with no usable codes cannot be decoded from an article
        # number. It is excluded rather than treated as a wildcard.
        option_ids = [
            oid for oid in option_ids
            if any((v.code or "").replace("#", "") for v in candidates_by_option[oid])
        ]

        @lru_cache(maxsize=None)
        def match(position: int, index: int, selected: tuple[str, ...]):
            if position == len(suffix):
                if cls._dependencies_are_valid(selected, option_deps):
                    return (selected,)
                return ()
            if index >= len(option_ids):
                return ()

            option_id = option_ids[index]
            results = []

            # An option is not necessarily selected. Skipping an option is valid
            # when its code is absent from the concrete article number.
            results.extend(match(position, index + 1, selected))

            for value in candidates_by_option[option_id]:
                code = (value.code or "").replace("#", "")
                if not code or not suffix.startswith(code, position):
                    continue
                next_selected = selected + (str(value.id),)
                results.extend(
                    match(position + len(code), index + 1, next_selected)
                )
                if len(results) > 2:
                    return tuple(results[:3])
            # De-duplicate equivalent selections reached through different paths.
            unique = []
            seen = set()
            for result in results:
                if result in seen:
                    continue
                seen.add(result)
                unique.append(result)
                if len(unique) >= 3:
                    break
            return tuple(unique)

        # Optional options may be omitted. If the suffix resolves to exactly one
        # valid selection set, materialize it; ambiguous matches remain empty.
        matches = match(0, 0, ())
        if len(matches) != 1:
            return []

        selected_ids = matches[0]
        resolved = []
        for value_id in selected_ids:
            value = option_by_value[value_id]
            option = option_by_id.get(str(value.option_id or ""))
            if option is None:
                continue
            resolved.append(
                ArticleConfigurationValue(
                    kind="option",
                    entity_id=str(option.id),
                    value_id=value_id,
                    name=option.name or "",
                    value=value.value or "",
                    code=(value.code or "").replace("#", ""),
                    display_order=option.display_order or 0,
                )
            )
        resolved = cls._dedupe_values(resolved)
        resolved.sort(key=lambda x: (x.display_order, x.name, x.value_id))
        return resolved

    @staticmethod
    def _dependencies_are_valid(
        selected_value_ids: tuple[str, ...],
        dependencies: dict,
    ) -> bool:
        """Validate the complete selected option set against dependency edges."""
        selected = {str(v) for v in selected_value_ids}
        for source, destinations in dependencies.items():
            source = str(source)
            if source not in selected:
                continue
            # Selecting a parent does not force every dependent value; the
            # dependency graph only establishes which child values are valid.
            # A selected child, however, must have at least one selected parent.
            for destination in destinations or []:
                if str(destination) in selected:
                    continue

        incoming: dict[str, set[str]] = {}
        for source, destinations in dependencies.items():
            for destination in destinations or []:
                incoming.setdefault(str(destination), set()).add(str(source))

        for value_id in selected:
            parents = incoming.get(value_id)
            if parents and not (parents & selected):
                return False
        return True

    @staticmethod
    def _dedupe_values(
        values: list[ArticleConfigurationValue],
    ) -> list[ArticleConfigurationValue]:
        result: list[ArticleConfigurationValue] = []
        seen: set[str] = set()
        for value in values:
            key = f"{value.kind}:{value.entity_id}:{value.value_id}"
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result
