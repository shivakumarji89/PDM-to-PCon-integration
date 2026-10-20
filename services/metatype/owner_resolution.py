"""Which Metatype owns a new property? Resolved from the articles it switches between, or not at all.

Verified rule (docs/02_Domain/Engineering/Metatype_Write_Contract_Decisions.md, D1): in go_articles, column 1
(``id``, labelled ``[metatypeid]``) is the Metatype an article belongs to (822/822 real rows name a Metatype that
has go_types rows), and go_types holds one row per (Metatype, property). So the property belongs to the Metatype
named by the articles of Template Step 4. If those articles are unknown (new) or name more than one Metatype the
owner is *not* guessed: the result carries the candidates and the reason, and the user/owner must decide.

Pure and read-only: it only inspects an in-memory ``ArticleReconciliation``.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from models.metatype_articles import ArticleReconciliation


@dataclass(frozen=True)
class OwnerResolution:
    metatype_id: str | None             # set only when every listed article names the same Metatype
    candidates: tuple[str, ...] = ()    # every distinct Metatype id the matched articles name
    missing: tuple[str, ...] = ()       # listed articles that are not in go_articles
    reason: str = ""

    @property
    def resolved(self) -> bool:
        return self.metatype_id is not None


def resolve_owner_metatype(result: ArticleReconciliation | None, articles: Iterable[str]) -> OwnerResolution:
    wanted = [a.strip(" \t") for a in articles if a.strip(" \t")]
    if not wanted:
        return OwnerResolution(None, reason="No articles were listed, so no owning Metatype can be derived.")
    column = result.roles.get("metatypeid") if result is not None else None
    if result is None or column is None:
        return OwnerResolution(None, tuple(), tuple(wanted),
                               "The series schema does not identify the Metatype of an article (no metatypeid role).")
    by_article: dict[str, set[str]] = {}
    for row in result.rows:
        if row.identity is None:
            continue
        value = row.values.get(column, "").strip(" \t")
        if value:
            by_article.setdefault(row.identity[2], set()).add(value)
    missing = tuple(a for a in wanted if a not in by_article)
    found = sorted({m for a in wanted for m in by_article.get(a, ())})
    if missing:
        return OwnerResolution(None, tuple(found), missing,
                               f"Article(s) not in go_articles (new?): {', '.join(missing)}. The owning Metatype "
                               "must be chosen explicitly.")
    if len(found) != 1:
        return OwnerResolution(None, tuple(found), (),
                               f"The articles belong to {len(found)} different Metatypes ({', '.join(found)}); the "
                               "property would need a go_types row on each. Choose explicitly.")
    return OwnerResolution(found[0], tuple(found))
