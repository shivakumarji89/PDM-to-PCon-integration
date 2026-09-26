"""Generate Article OBX permutations from repository configuration data.

In the repository/MDB model an Article is a *base article*. A permutation is a
runtime configuration built from that base article's classes/properties,
property values, relations, ArtBase restrictions and code scheme. Existing
Article rows are therefore inputs (base identities), never generated variants.
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass

from models.snapshot import Snapshot
from services.article_obx.article_obx_models import (
    ArticleConfigurationValue,
    ArticlePermutation,
)
from services.base_service import BaseService


@dataclass(frozen=True)
class _Dimension:
    property_id: str
    name: str
    display_order: int
    values: tuple[object, ...]


class ArticlePermutationService(BaseService):
    """Build valid final article numbers from a repository Snapshot."""

    def build(self, snapshot: Snapshot | None = None) -> list[ArticlePermutation]:
        snapshot = (
            snapshot
            if snapshot is not None
            else self.context.repository_snapshot
        )
        if snapshot is None:
            return []

        results: list[ArticlePermutation] = []
        seen: set[str] = set()

        for article in sorted(
            snapshot.articles,
            key=lambda item: ((item.code or "").strip(), str(item.id or "")),
        ):
            base_code = (article.code or "").strip()
            if not base_code:
                continue

            dimensions = self._dimensions_for_article(snapshot, article.id, base_code)
            if not dimensions:
                final_article = base_code
                if final_article not in seen:
                    seen.add(final_article)
                    results.append(
                        self._make_permutation(
                            snapshot, article, base_code, (), (), final_article
                        )
                    )
                continue

            for selected_values in itertools.product(
                *(dimension.values for dimension in dimensions)
            ):
                properties = self._materialize_properties(
                    dimensions, selected_values
                )
                selected_ids = {value.value_id for value in properties}

                if not self._valid_art_base(snapshot, base_code, selected_ids):
                    continue
                if not self._valid_exclusions(snapshot, selected_ids):
                    continue
                if not self._valid_relations(
                    snapshot, base_code, selected_ids, properties
                ):
                    continue

                final_article = self._encode_article(
                    snapshot, article.id, base_code, properties
                )
                if not final_article or final_article in seen:
                    continue

                seen.add(final_article)
                results.append(
                    self._make_permutation(
                        snapshot,
                        article,
                        base_code,
                        properties,
                        (),
                        final_article,
                    )
                )

        results.sort(
            key=lambda item: (
                item.base_code,
                item.final_article,
                tuple(value.value_id for value in item.properties),
            )
        )
        return results

    def _dimensions_for_article(
        self,
        snapshot: Snapshot,
        article_id: str | None,
        base_code: str,
    ) -> tuple[_Dimension, ...]:
        property_ids = self._article_property_ids(snapshot, article_id)
        if not property_ids:
            property_ids = {
                str(prop.id)
                for prop in snapshot.properties
                if prop.id is not None
            }

        restrictions = (getattr(snapshot, "art_base", {}) or {}).get(base_code, {})
        dimensions: list[_Dimension] = []

        for prop in snapshot.properties:
            prop_id = str(prop.id or "")
            if not prop_id or prop_id not in property_ids:
                continue

            allowed_ids = {
                str(value_id)
                for value_id in restrictions.get(prop_id, [])
            }
            source_values = [
                value
                for value in prop.values
                if not allowed_ids or str(value.id) in allowed_ids
            ]
            source_values.sort(
                key=lambda value: (
                    value.display_order is None,
                    value.display_order or 0,
                    value.value or "",
                    str(value.id or ""),
                )
            )
            if not source_values:
                continue

            dimensions.append(
                _Dimension(
                    property_id=prop_id,
                    name=prop.name or prop.code or prop_id,
                    display_order=(
                        int(prop.display_order)
                        if prop.display_order is not None
                        else 10**9
                    ),
                    values=tuple(source_values),
                )
            )

        scheme_order = self._scheme_property_order(snapshot, article_id)
        if scheme_order:
            rank = {name: index for index, name in enumerate(scheme_order)}
            dimensions.sort(
                key=lambda item: (
                    rank.get(self._normalise_name(item.name), 10**6),
                    item.display_order,
                    item.name,
                )
            )
        else:
            dimensions.sort(
                key=lambda item: (
                    item.display_order,
                    item.name,
                    item.property_id,
                )
            )

        return tuple(dimensions)

    @staticmethod
    def _article_property_ids(snapshot: Snapshot, article_id: str | None) -> set[str]:
        links = (getattr(snapshot, "article_class_ids", {}) or {}).get(
            str(article_id or ""), []
        )
        if not links:
            return set()

        class_ids = {str(value) for value in links}
        property_ids: set[str] = set()
        for engineering_class in getattr(snapshot.engineering, "classes", []) or []:
            if str(engineering_class.id) not in class_ids:
                continue
            for assignment in engineering_class.properties:
                if assignment.property_id:
                    property_ids.add(str(assignment.property_id))
        return property_ids

    @classmethod
    def _scheme_property_order(
        cls, snapshot: Snapshot, article_id: str | None
    ) -> list[str]:
        scheme_id = (
            getattr(snapshot, "article_code_scheme_ids", {}) or {}
        ).get(str(article_id or ""))
        if not scheme_id:
            return []

        scheme = (getattr(snapshot, "code_schemes", {}) or {}).get(str(scheme_id), {})
        body = str(scheme.get("body") or "")
        if not body:
            return []

        # Current MK Workbench code-scheme rows use a compact body:
        # @,@,...,Class:Property Class:Property ...
        # The @ characters represent the base portion; the property tokens
        # define the deterministic variant-code property order.
        tokens = re.findall(r"([A-Za-z0-9_]+):([A-Za-z0-9_]+)", body)
        return [cls._normalise_name(prop) for _class_name, prop in tokens]

    @staticmethod
    def _normalise_name(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]+", "_", value or "").strip("_").upper()

    @staticmethod
    def _materialize_properties(
        dimensions: tuple[_Dimension, ...],
        selected_values: tuple[object, ...],
    ) -> tuple[ArticleConfigurationValue, ...]:
        values: list[ArticleConfigurationValue] = []
        for dimension, source in zip(dimensions, selected_values):
            values.append(
                ArticleConfigurationValue(
                    kind="property",
                    entity_id=dimension.property_id,
                    value_id=str(source.id),
                    name=dimension.name,
                    value=source.value or "",
                    code=(source.code or "").replace("#", ""),
                    display_order=dimension.display_order,
                )
            )
        return tuple(values)

    @staticmethod
    def _valid_art_base(
        snapshot: Snapshot, base_code: str, selected_ids: set[str]
    ) -> bool:
        restrictions = (getattr(snapshot, "art_base", {}) or {}).get(base_code, {})
        if not restrictions:
            return True

        for allowed_values in restrictions.values():
            allowed = {str(value_id) for value_id in allowed_values or ()}
            if not (selected_ids & allowed):
                return False
        return True

    @staticmethod
    def _valid_exclusions(snapshot: Snapshot, selected_ids: set[str]) -> bool:
        exclusions = getattr(snapshot, "attribute_value_exclusions", {}) or {}
        for value_id in selected_ids:
            if any(
                str(other) in selected_ids
                for other in exclusions.get(str(value_id), ())
            ):
                return False
        return True

    @staticmethod
    def _valid_relations(
        snapshot: Snapshot,
        base_code: str,
        selected_ids: set[str],
        properties: tuple[ArticleConfigurationValue, ...],
    ) -> bool:
        selected = {
            ArticlePermutationService._normalise_name(value.name): value.value.upper()
            for value in properties
        }

        for relation in getattr(snapshot, "relation_objects", []) or []:
            if str(getattr(relation, "domain", "")) != "C":
                continue

            type_code = str(getattr(relation, "type_code", "") or "")
            body = str(getattr(relation, "body", "") or "")

            if type_code in {"1", "2"}:
                value_id = str(getattr(relation, "value_id", "") or "")
                if not value_id or value_id not in selected_ids:
                    continue
                if not ArticlePermutationService._relation_body_matches(
                    body, base_code, selected
                ):
                    return False

            elif type_code == "4" and "TABLE" in body.upper():
                if not ArticlePermutationService._table_constraint_matches(
                    snapshot, body, base_code, selected
                ):
                    return False

        return True

    @staticmethod
    def _relation_body_matches(
        body: str,
        base_code: str,
        selected: dict[str, str],
    ) -> bool:
        restrictions = body.split("Restrictions:", 1)[-1].strip()
        if not restrictions:
            return True

        branches = re.split(r"\\s+OR\\s+", restrictions, flags=re.IGNORECASE)
        for branch in branches:
            terms = re.split(r"\\s+AND\\s+", branch, flags=re.IGNORECASE)
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
    def _table_constraint_matches(
        snapshot: Snapshot,
        body: str,
        base_code: str,
        selected: dict[str, str],
    ) -> bool:
        match = re.search(
            r"TABLE\s+([A-Za-z0-9_]+)\s*\((.*?)\)",
            body,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return True

        table_name = match.group(1).upper()
        table = next(
            (
                value_table
                for value_table in (getattr(snapshot, "value_tables", []) or [])
                if str(value_table.name or "").upper() == table_name
            ),
            None,
        )
        if table is None:
            # Relation exists but its table is not available in the repository
            # snapshot. Do not invent a restriction.
            return True

        access = {}
        for parameter in match.group(2).split(","):
            if "=" not in parameter:
                continue
            column, expression = parameter.split("=", 1)
            access[column.strip().upper()] = expression.strip()

        for line in table.lines:
            valid = True
            for column, expected in line.items():
                expression = access.get(str(column).upper())
                if expression is None:
                    continue
                expression = expression.strip()
                if expression.upper() == "$BAN":
                    actual = base_code
                else:
                    prop_match = re.search(
                        r"x\.([A-Za-z0-9_]+)", expression, re.IGNORECASE
                    )
                    if not prop_match:
                        continue
                    actual = selected.get(prop_match.group(1).upper())
                allowed = expected if isinstance(expected, (list, tuple)) else [expected]
                if str(actual or "").upper() not in {
                    str(value).upper() for value in allowed
                }:
                    valid = False
                    break
            if valid:
                return True

        return False

    @staticmethod
    def _relation_term_matches(
        term: str,
        base_code: str,
        selected: dict[str, str],
    ) -> bool:
        term = term.strip(" ()")

        ban = re.search(
            r"\\$BAN\\s+IN\\s*\\(\\s*'([^']*)'",
            term,
            re.IGNORECASE,
        )
        if ban:
            return ban.group(1).upper() == base_code.upper()

        specified = re.search(
            r"SPECIFIED\\s+([A-Z0-9_]+)",
            term,
            re.IGNORECASE,
        )
        if specified and specified.group(1).upper() not in selected:
            return False

        value_match = re.search(
            r"([A-Z0-9_]+)\\s+IN\\s*\\((.*?)\\)",
            term,
            re.IGNORECASE | re.DOTALL,
        )
        if value_match:
            name = value_match.group(1).upper()
            allowed = {
                item.strip().strip("'").upper()
                for item in value_match.group(2).split(",")
            }
            return selected.get(name) in allowed

        return True

    @classmethod
    def _encode_article(
        cls,
        snapshot: Snapshot,
        article_id: str | None,
        base_code: str,
        properties: tuple[ArticleConfigurationValue, ...],
    ) -> str:
        scheme_id = (
            getattr(snapshot, "article_code_scheme_ids", {}) or {}
        ).get(str(article_id or ""))
        scheme = (
            (getattr(snapshot, "code_schemes", {}) or {}).get(str(scheme_id), {})
            if scheme_id
            else {}
        )
        body = str(scheme.get("body") or "")

        if not body:
            ordered = properties
        else:
            order = cls._scheme_property_order(snapshot, article_id)
            rank = {name: index for index, name in enumerate(order)}
            ordered = tuple(
                sorted(
                    properties,
                    key=lambda value: (
                        rank.get(cls._normalise_name(value.name), 10**6),
                        value.display_order,
                        value.name,
                    ),
                )
            )

        tokens: list[str] = []
        for value in ordered:
            token = (value.code or "").strip()
            if not token:
                return ""
            tokens.append(token)

        # The repository's current code-scheme writer uses the base article as
        # the fixed @ portion and property values as the variant-code portion.
        return base_code + "".join(tokens)

    @staticmethod
    def _make_permutation(
        snapshot: Snapshot,
        article,
        base_code: str,
        properties,
        options,
        final_article: str,
    ) -> ArticlePermutation:
        return ArticlePermutation(
            article_id=str(article.id or ""),
            product_id=str(article.product_id or ""),
            base_code=base_code,
            final_article=final_article,
            name=article.name or "",
            description=article.description or "",
            quantity=1,
            is_super_item=False,
            properties=tuple(properties),
            options=tuple(options),
        )
