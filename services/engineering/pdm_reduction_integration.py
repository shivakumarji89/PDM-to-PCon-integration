"""Bridge the PDM reduction result into the existing ArticleSet materializer.

The existing Articles UI consumes ``Snapshot.article_sets`` and derives
``MemberArticle.reduced_article`` from each set's ``base_length``.  This bridge
keeps that workflow intact while replacing the old base-length source with the
PDM-validated pre-dot reduction result.

It is intentionally isolated so the proven PDM reduction service remains
separate from the generic engineering reduction service.
"""
from __future__ import annotations

from services.engineering.engineering_reduction_service import EngineeringReductionService


_ORIGINAL_MATERIALIZE = EngineeringReductionService.materialize_article_sets
_PATCH_MARKER = "_pdm_reduction_materializer_patched"


def _materialize_with_pdm_base(self, snapshot):
    article_sets = _ORIGINAL_MATERIALIZE(self, snapshot)
    if snapshot is None or not article_sets:
        return article_sets

    # Do not silently fall back to the legacy base-length calculation. If the
    # PDM reduction service is unavailable or fails, that is an integration
    # failure that must remain visible instead of producing a plausible but
    # potentially incorrect ArticleSet result.
    result = self.context.pdm_article_reduction_service.discover(snapshot)

    base_by_product: dict[str, str] = {
        str(product_id): group.base_article
        for group in result.groups
        for product_id in group.product_ids
    }
    article_product = {
        str(article.id): str(getattr(article, "product_id", "") or "")
        for article in snapshot.articles
    }

    for article_set in article_sets:
        bases = {
            base_by_product.get(article_product.get(str(article_id), ""), "")
            for article_id in article_set.article_ids
        }
        bases.discard("")
        if len(bases) != 1:
            continue
        base = next(iter(bases))
        article_set.base_length = len(base)
        # Keep both ArticleSet representations synchronized.  Downstream
        # consumers may use either the length or the materialized base code.
        article_set.base_code = base

    return article_sets


if not getattr(EngineeringReductionService, _PATCH_MARKER, False):
    EngineeringReductionService.materialize_article_sets = _materialize_with_pdm_base
    setattr(EngineeringReductionService, _PATCH_MARKER, True)
