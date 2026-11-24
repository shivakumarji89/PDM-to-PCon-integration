"""Single rule for which PDM value ids an article carries.

``BaseAttributeValues`` (``snapshot.article_property_value_ids``) say what one article
carries. ``ProductAttributeValues`` (``snapshot.product_property_value_ids``) are the menu
the whole product OFFERS - one article carries a small part of it. So:

* if any article of a product has article-level links, article links are used throughout
  that product and an article without links carries nothing;
* the product menu is used only when no article of the product has article-level links
  (it is then the only data there is).
"""
from __future__ import annotations

from typing import Iterable, Mapping


def products_with_article_links(
    articles: Iterable, article_values: Mapping[str, list] | None,
) -> set[str]:
    """Product ids having at least one article with article-level value links."""
    article_values = article_values or {}
    return {
        str(getattr(a, "product_id", "") or "")
        for a in articles
        if article_values.get(str(getattr(a, "id", "")))
    }


def carried_value_ids(
    article_id: str,
    product_id: str,
    article_values: Mapping[str, list] | None,
    product_values: Mapping[str, list] | None,
    linked_products: set[str],
) -> tuple[list[str], bool]:
    """``(value ids the article carries, used_product_fallback)``."""
    own = [str(v) for v in ((article_values or {}).get(str(article_id)) or [])]
    if own:
        return own, False
    if str(product_id) in linked_products:
        return [], False
    menu = [str(v) for v in ((product_values or {}).get(str(product_id)) or [])]
    return menu, bool(menu)
