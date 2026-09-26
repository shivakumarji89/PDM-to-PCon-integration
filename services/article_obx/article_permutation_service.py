"""Build valid article permutations from the established Snapshot."""
from __future__ import annotations

from services.base_service import BaseService
from models.snapshot import Snapshot
from services.article_obx.article_obx_models import (
    ArticleConfigurationValue,
    ArticlePermutation,
)


class ArticlePermutationService(BaseService):
    """Build one configuration record for each real Snapshot article."""

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

        permutations: list[ArticlePermutation] = []
        for article in snapshot.articles:
            article_id = str(article.id or "")
            if not article_id or not article.code:
                continue

            property_values: list[ArticleConfigurationValue] = []
            option_values: list[ArticleConfigurationValue] = []

            # BaseAttributeValues are the concrete article configuration. Do not
            # expand product-level values into combinations: the article itself
            # is the authoritative proof that this configuration exists.
            value_ids = [
                str(value_id)
                for value_id in (
                    snapshot.article_property_value_ids.get(article_id, [])
                    or snapshot.product_property_value_ids.get(
                        str(article.product_id or ""), []
                    )
                )
            ]

            for value_id in value_ids:
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

            property_values.sort(key=lambda x: (x.display_order, x.name, x.value_id))
            option_values.sort(key=lambda x: (x.display_order, x.name, x.value_id))

            permutations.append(
                ArticlePermutation(
                    article_id=article_id,
                    product_id=str(article.product_id or ""),
                    base_code=article.code,
                    final_article=article.code,
                    name=article.name or "",
                    description=article.description or "",
                    quantity=article.quantity or 1,
                    is_super_item=bool(article.is_super_item),
                    properties=tuple(property_values),
                    options=tuple(option_values),
                )
            )

        return permutations
