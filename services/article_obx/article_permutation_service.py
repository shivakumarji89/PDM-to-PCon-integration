"""Build valid article permutations from the established Snapshot."""
from __future__ import annotations

from services.base_service import BaseService
from models.snapshot import Snapshot
from services.article_obx.article_obx_models import (
    ArticleConfigurationValue,
    ArticlePermutation,
)


class ArticlePermutationService(BaseService):
    """Build deterministic permutations from the concrete PDM article set.

    The Snapshot already contains the materialised PDM Items (Articles). Those
    Items are the authoritative proof that a configuration exists. This service
    therefore does not invent a Cartesian product of product-level values.

    Product-level option values are availability data, not article selections.
    They are intentionally not copied into ArticlePermutation.options unless
    the same value id is explicitly present in the article's concrete value
    links. This prevents every offered option from being priced as selected.
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

        # Materialised ArticleSet is the established source for the reduced/base
        # article number. It is a derived view of the same Snapshot, not a new
        # domain entity.
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

            property_values: list[ArticleConfigurationValue] = []
            option_values: list[ArticleConfigurationValue] = []

            # BaseAttributeValues are the concrete article configuration.
            # Product-level values are only a fallback when PDM supplied no
            # article-level rows for this Item.
            selected_ids = [
                str(value_id)
                for value_id in (
                    snapshot.article_property_value_ids.get(article_id, [])
                    or snapshot.product_property_value_ids.get(
                        str(article.product_id or ""), []
                    )
                )
            ]

            for value_id in selected_ids:
                pv = property_by_value.get(value_id)
                if pv is not None:
                    prop = property_by_id.get(str(pv.property_id or ""))
                    if prop is not None:
                        property_values.append(
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
                    continue

                # This branch is intentionally narrow: only an ID explicitly
                # attached to the concrete article can become a selected option.
                # ProductOptionValues are never treated as article selections.
                ov = option_by_value.get(value_id)
                if ov is not None:
                    option = option_by_id.get(str(ov.option_id or ""))
                    if option is not None:
                        option_values.append(
                            ArticleConfigurationValue(
                                kind="option",
                                entity_id=str(option.id),
                                value_id=value_id,
                                name=option.name or "",
                                value=ov.value or "",
                                code=(ov.code or "").replace("#", ""),
                                display_order=option.display_order or 0,
                            )
                        )

            property_values = self._dedupe_values(property_values)
            option_values = self._dedupe_values(option_values)
            property_values.sort(
                key=lambda x: (x.display_order, x.name, x.value_id)
            )
            option_values.sort(
                key=lambda x: (x.display_order, x.name, x.value_id)
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
                    options=tuple(option_values),
                )
            )

        return permutations

    @staticmethod
    def _dedupe_values(
        values: list[ArticleConfigurationValue],
    ) -> list[ArticleConfigurationValue]:
        """Keep one deterministic row per configuration value id."""
        result: list[ArticleConfigurationValue] = []
        seen: set[str] = set()
        for value in values:
            key = f"{value.kind}:{value.entity_id}:{value.value_id}"
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result
