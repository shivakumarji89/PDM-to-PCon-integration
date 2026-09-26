"""Build Article OBX permutations from repository configuration data.

A permutation is a generated configuration, not an existing PDM Article row.
The repository Snapshot supplies the available values, base/article-set scope,
encoding codes, dependency/exclusion rules and relation restrictions.
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from typing import Iterable

from services.base_service import BaseService
from models.snapshot import Snapshot
from services.article_obx.article_obx_models import (
    ArticleConfigurationValue,
    ArticlePermutation,
)


@dataclass(frozen=True)
class _Dimension:
    kind: str
    entity_id: str
    name: str
    display_order: int
    values: tuple[object, ...]
    required: bool


class ArticlePermutationService(BaseService):
    """Generate valid article-number permutations from repository data."""

    def build(self, snapshot: Snapshot | None = None) -> list[ArticlePermutation]:
        snapshot = snapshot if snapshot is not None else self.context.repository_snapshot
        if snapshot is None:
            return []

        decoded = self._decoded_codes(snapshot)
        results: list[ArticlePermutation] = []
        seen: set[str] = set()

        for article_set in sorted(
            snapshot.article_sets,
            key=lambda item: (item.base_code or "", item.id or ""),
        ):
            base_code = (article_set.base_code or "").strip()
            if not base_code:
                continue

            dimensions = self._dimensions(snapshot, article_set)
            combinations = itertools.product(
                *(self._choices(d) for d in dimensions)
            ) if dimensions else [()]

            for selected in combinations:
                properties, options = self._materialize_values(
                    snapshot, dimensions, selected, decoded
                )
                selected_ids = {
                    value.value_id
                    for value in (*properties, *options)
                    if value.value_id
                }

                if not self._valid_exclusions(snapshot, selected_ids):
                    continue
                if not self._valid_dependencies(snapshot, selected_ids):
                    continue
                if not self._valid_art_base(snapshot, base_code, selected_ids):
                    continue
                if not self._valid_relations(snapshot, base_code, selected_ids, properties, options):
                    continue

                final_article = self._encode_article(
                    snapshot, article_set, properties, options, base_code, decoded
                )
                if not final_article or final_article in seen:
                    continue
                seen.add(final_article)

                results.append(
                    ArticlePermutation(
                        article_id="",
                        product_id=str(snapshot.product.id or "") if snapshot.product else "",
                        base_code=base_code,
                        final_article=final_article,
                        name="",
                        description="",
                        quantity=1,
                        is_super_item=bool(snapshot.product.is_super_product) if snapshot.product else False,
                        properties=tuple(properties),
                        options=tuple(options),
                    )
                )

        results.sort(
            key=lambda item: (
                item.base_code,
                item.final_article,
                tuple(v.value_id for v in item.properties),
                tuple(v.value_id for v in item.options),
            )
        )
        return results

    @staticmethod
    def _choices(dimension: _Dimension) -> tuple[object | None, ...]:
        if dimension.required:
            return dimension.values
        return (None, *dimension.values)

    @staticmethod
    def _dimensions(snapshot: Snapshot, article_set) -> tuple[_Dimension, ...]:
        dimensions: list[_Dimension] = []
        all_article_ids = {str(a) for a in article_set.article_ids}

        for kind, attributes in (
            ("property", article_set.properties),
            ("option", article_set.options),
        ):
            for attr in attributes:
                values = tuple(
                    sorted(
                        attr.values,
                        key=lambda value: (
                            value.code == "",
                            value.code or "",
                            value.value or "",
                            value.id or "",
                        ),
                    )
                )
                if not values:
                    continue

                coverage = {
                    str(article_id)
                    for value in values
                    for article_id in value.article_ids
                }
                required = bool(all_article_ids) and coverage >= all_article_ids
                dimensions.append(
                    _Dimension(
                        kind=kind,
                        entity_id=str(attr.id),
                        name=attr.name or "",
                        display_order=ArticlePermutationService._display_order(
                            snapshot, kind, str(attr.id)
                        ),
                        values=values,
                        required=required,
                    )
                )

        dimensions.sort(key=lambda d: (d.display_order, d.name, d.entity_id))
        return tuple(dimensions)

    @staticmethod
    def _display_order(snapshot: Snapshot, kind: str, entity_id: str) -> int:
        collection = snapshot.properties if kind == "property" else snapshot.options
        entity = next(
            (item for item in collection if str(item.id) == entity_id), None
        )
        value = getattr(entity, "display_order", None) if entity else None
        return int(value) if value is not None else 10**9

    @classmethod
    def _materialize_values(
        cls, snapshot: Snapshot, dimensions, selected, decoded
    ) -> tuple[list[ArticleConfigurationValue], list[ArticleConfigurationValue]]:
        properties: list[ArticleConfigurationValue] = []
        options: list[ArticleConfigurationValue] = []

        for dimension, value in zip(dimensions, selected):
            if value is None:
                continue

            if dimension.kind == "property":
                code = (getattr(value, "code", "") or "").replace("#", "")
                if not code:
                    code = decoded.get(dimension.entity_id, {}).get(str(value.id), "")
                item = ArticleConfigurationValue(
                    kind="property",
                    entity_id=dimension.entity_id,
                    value_id=str(value.id),
                    name=dimension.name,
                    value=value.value or "",
                    code=code,
                    display_order=dimension.display_order,
                )
                properties.append(item)
            else:
                code = (getattr(value, "code", "") or "").replace("#", "")
                item = ArticleConfigurationValue(
                    kind="option",
                    entity_id=dimension.entity_id,
                    value_id=str(value.id),
                    name=dimension.name,
                    value=value.value or "",
                    code=code,
                    display_order=dimension.display_order,
                )
                options.append(item)

        return properties, options

    def _decoded_codes(self, snapshot: Snapshot) -> dict[str, dict[str, str]]:
        try:
            cached = snapshot.config_value_codes or {}
        except AttributeError:
            cached = {}
        if cached:
            return cached
        service = getattr(self.context, "engineering_class_service", None)
        if service is not None:
            try:
                return service.resolve_config_codes(snapshot)
            except Exception:
                pass
        return {}

    @staticmethod
    def _valid_exclusions(snapshot: Snapshot, selected_ids: set[str]) -> bool:
        exclusions = getattr(snapshot, "attribute_value_exclusions", {}) or {}
        for value_id in selected_ids:
            if any(str(other) in selected_ids for other in exclusions.get(str(value_id), ())):
                return False
        return True

    @staticmethod
    def _valid_dependencies(snapshot: Snapshot, selected_ids: set[str]) -> bool:
        """A selected dependent value requires its enabling parent selection."""
        incoming: dict[str, set[str]] = {}
        for source, destinations in (
            list((getattr(snapshot, "attribute_option_dependencies", {}) or {}).items())
            + list((getattr(snapshot, "option_option_dependencies", {}) or {}).items())
        ):
            for destination in destinations or ():
                incoming.setdefault(str(destination), set()).add(str(source))

        return all(
            not incoming.get(value_id) or bool(incoming[value_id] & selected_ids)
            for value_id in selected_ids
        )

    @staticmethod
    def _valid_art_base(snapshot: Snapshot, base_code: str, selected_ids: set[str]) -> bool:
        art_base = getattr(snapshot, "art_base", {}) or {}
        restrictions = art_base.get(base_code) or {}
        for entity_id, allowed in restrictions.items():
            allowed_ids = {str(value) for value in allowed or ()}
            selected_for_entity = {
                value_id
                for value_id in selected_ids
                if value_id in allowed_ids
            }
            # If this entity has a restriction and a value was selected for it,
            # it must belong to the allowed set. An absent optional selection is
            # valid unless the source relation makes it mandatory.
            if allowed_ids and selected_for_entity:
                continue
            if allowed_ids and not selected_for_entity:
                # Only reject when the entity has no selectable value in the
                # allowed set but a candidate value from that entity is selected.
                # The latter is checked by the membership test below.
                continue
        selected_entities = ArticlePermutationService._selected_entity_values(snapshot, selected_ids)
        for entity_id, value_ids in restrictions.items():
            allowed_ids = {str(v) for v in value_ids or ()}
            for value_id in selected_entities.get(str(entity_id), ()):
                if value_id not in allowed_ids:
                    return False
        return True

    @staticmethod
    def _selected_entity_values(snapshot: Snapshot, selected_ids: set[str]) -> dict[str, set[str]]:
        result: dict[str, set[str]] = {}
        for prop in snapshot.properties:
            result[str(prop.id)] = {
                str(value.id) for value in prop.values if str(value.id) in selected_ids
            }
        for option in snapshot.options:
            result[str(option.id)] = {
                str(value.id) for value in option.values if str(value.id) in selected_ids
            }
        return result

    @classmethod
    def _valid_relations(
        cls,
        snapshot: Snapshot,
        base_code: str,
        selected_ids: set[str],
        properties: list[ArticleConfigurationValue],
        options: list[ArticleConfigurationValue],
    ) -> bool:
        selected_by_name = {
            value.name: value.value
            for value in (*properties, *options)
        }
        selected_by_name_upper = {
            key.upper(): value.upper()
            for key, value in selected_by_name.items()
        }

        for relation in getattr(snapshot, "relation_objects", []) or []:
            if str(getattr(relation, "type_code", "")) != "1":
                continue
            if str(getattr(relation, "domain", "")) != "C":
                continue
            value_id = str(getattr(relation, "value_id", "") or "")
            if not value_id or value_id not in selected_ids:
                continue
            if not cls._relation_body_matches(
                str(getattr(relation, "body", "") or ""),
                base_code,
                selected_by_name_upper,
            ):
                return False
        return True

    @staticmethod
    def _relation_body_matches(
        body: str, base_code: str, selected: dict[str, str]
    ) -> bool:
        restrictions = body.split("Restrictions:", 1)[-1].strip()
        if not restrictions:
            return True

        branches = re.split(r"\s+OR\s+", restrictions, flags=re.IGNORECASE)
        for branch in branches:
            terms = re.split(r"\s+AND\s+", branch, flags=re.IGNORECASE)
            if all(
                ArticlePermutationService._relation_term_matches(
                    term.strip(), base_code, selected
                )
                for term in terms
                if term.strip()
            ):
                return True
        return False

    @staticmethod
    def _relation_term_matches(term: str, base_code: str, selected: dict[str, str]) -> bool:
        term = term.strip(" ()")
        ban = re.search(r"\$BAN\s+IN\s*\(\s*'([^']*)'", term, re.IGNORECASE)
        if ban:
            return ban.group(1).upper() == base_code.upper()

        specified = re.search(r"SPECIFIED\s+([A-Z0-9_]+)", term, re.IGNORECASE)
        if specified:
            name = specified.group(1).upper()
            if name not in selected:
                return False

        value_match = re.search(
            r"([A-Z0-9_]+)\s+IN\s*\((.*?)\)",
            term,
            re.IGNORECASE | re.DOTALL,
        )
        if value_match:
            name = value_match.group(1).upper()
            values = {
                item.strip().strip("'").upper()
                for item in value_match.group(2).split(",")
            }
            return selected.get(name) in values

        return True

    @staticmethod
    def _encode_article(
        snapshot: Snapshot,
        article_set,
        properties: list[ArticleConfigurationValue],
        options: list[ArticleConfigurationValue],
        base_code: str,
        decoded: dict[str, dict[str, str]],
    ) -> str:
        head_tokens: list[str] = []
        tail_tokens: list[str] = []

        for value in sorted(properties, key=lambda item: (item.display_order, item.name, item.value_id)):
            prop = next(
                (p for p in snapshot.properties if str(p.id) == value.entity_id), None
            )
            if prop is None:
                continue
            source = next(
                (v for v in prop.values if str(v.id) == value.value_id), None
            )
            if source is None:
                continue
            token = value.code.strip()
            if not token:
                return ""
            if source.code:
                tail_tokens.append(token)
            else:
                head_tokens.append(token)

        for value in sorted(options, key=lambda item: (item.display_order, item.name, item.value_id)):
            if not value.code.strip():
                return ""
            head_tokens.append(value.code.strip())

        base = base_code.rstrip(".")
        article = base + "".join(head_tokens)

        if tail_tokens:
            article += "." + "".join(tail_tokens)

        return article
