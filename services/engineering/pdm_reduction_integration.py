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

    # Discover exact functional-PDM-filter groups.  The service is lazy-resolved
    # through ApplicationContext, so this bridge does not open another PDM
    # connection and does not introduce a module-level dependency cycle.
    try:
        result = self.context.pdm_article_reduction_service.discover(snapshot)
    except Exception:
        # Reduction discovery must never break the existing materialization path.
        return article_sets

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
            # A property-structure set spanning multiple validated PDM bases
            # cannot safely be assigned one length. Leave its existing length.
            continue
        base = next(iter(bases))
        article_set.base_length = len(base)

    return article_sets


if not getattr(EngineeringReductionService, _PATCH_MARKER, False):
    EngineeringReductionService.materialize_article_sets = _materialize_with_pdm_base
    setattr(EngineeringReductionService, _PATCH_MARKER, True)
