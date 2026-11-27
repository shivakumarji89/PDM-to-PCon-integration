"""Canonical base-article identity.

The Article workflow owns the unique base-article list. Every consumer - the Articles page,
the Class workflow, the full-series MDB export and the incremental article export - asks
this module for the base of an article, so they cannot disagree.

Precedence for one engineering member (first hit wins):

1. ``member.reduced_article``                 - what the user sees and edits in Articles;
2. ``snapshot.base_length_overrides[code]``   - an explicit base length for that article;
3. the price-base fallback                    - ``PricingService._prefix_by_item`` (article-set
   ``base_length``, PDM prefix length, ``.`` rule), supplied by the caller.

Article-set membership never takes part: a base that appears in several article sets is one
identity, and one set may hold several bases. Sets are recorded on the identity only as
information.

Pure functions over the snapshot; no services, no mutation.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

SOURCE_REDUCED = "reduced_article"
SOURCE_OVERRIDE = "base_length_override"
SOURCE_PRICE_BASE = "price_base"


class BaseIdentityConflict(ValueError):
    """An article id resolves to more than one base article; nothing may be exported from it."""

    def __init__(self, conflicts: list[tuple[str, str, str]]) -> None:
        shown = "; ".join(f"article {a}: '{x}' vs '{y}'" for a, x, y in conflicts[:5])
        more = f" (+{len(conflicts) - 5} more)" if len(conflicts) > 5 else ""
        super().__init__(
            f"{len(conflicts)} article id(s) resolve to more than one base article: {shown}{more}. "
            "Fix the base length / reduced article of the affected articles in the Articles page.")
        self.conflicts = conflicts


def explicit_base(member, code: str, overrides: Mapping[str, int] | None) -> tuple[str, str]:
    """``(base, source)`` from tiers 1-2 only (``("", "")`` when the user set neither)."""
    reduced = str(getattr(member, "reduced_article", "") or "").strip()
    if reduced:
        return reduced, SOURCE_REDUCED
    length = int((overrides or {}).get(code) or 0) if code else 0
    if length > 0:
        return code[:length], SOURCE_OVERRIDE
    return "", ""


@dataclass
class BaseIdentity:
    """One unique base article."""

    base: str
    article_ids: list[str] = field(default_factory=list)
    set_ids: list[str] = field(default_factory=list)   # informational only


@dataclass
class BaseIdentityMap:
    entries: list[tuple[str, str]] = field(default_factory=list)   # (article_id, base) per member
    by_article: dict[str, str] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)          # article_id -> tier used
    bases: dict[str, BaseIdentity] = field(default_factory=dict)   # unique, first-seen order
    # Articles whose explicit base differs from the price base: prices are keyed by the price
    # base, so these rows need attention before a price export. (article_id, base, price_base)
    divergences: list[tuple[str, str, str]] = field(default_factory=list)
    # Bases that would collide in a case-insensitive MDB: (first, second).
    case_collisions: list[tuple[str, str]] = field(default_factory=list)
    # One article id carried by several members that resolve to DIFFERENT bases:
    # (article_id, first base, other base). The article has no single identity.
    id_conflicts: list[tuple[str, str, str]] = field(default_factory=list)

    def base_of(self, article_id) -> str:
        return self.by_article.get(str(article_id), "")


def resolve_base_identities(
    snapshot, price_base_of: Mapping[str, str] | None = None
) -> BaseIdentityMap:
    """Resolve every engineering member of ``snapshot`` to its base article.

    ``price_base_of`` is the code -> price-base map (tier 3). Entries follow member order
    (families, then members), one per member, exactly like the historical
    ``base_code_entries``; an unresolved member yields ``""``.
    """
    price_base_of = price_base_of or {}
    overrides = getattr(snapshot, "base_length_overrides", None) or {}
    code_by_id = {str(a.id): str(a.code or "").strip() for a in getattr(snapshot, "articles", []) or []
                  if getattr(a, "id", None) is not None and a.code}
    set_of: dict[str, list[str]] = {}
    for aset in getattr(snapshot, "article_sets", None) or []:
        for article_id in getattr(aset, "article_ids", None) or []:
            set_of.setdefault(str(article_id), []).append(str(getattr(aset, "id", "") or ""))

    result = BaseIdentityMap()
    families = getattr(getattr(snapshot, "engineering", None), "families", None) or []
    for family in families:
        for member in getattr(family, "members", None) or []:
            article_id = str(getattr(member, "article_id", ""))
            code = code_by_id.get(article_id, "")
            base, source = explicit_base(member, code, overrides)
            price_base = str(price_base_of.get(code) or "").strip() if code else ""
            if not base and price_base:
                base, source = price_base, SOURCE_PRICE_BASE
            if not base:
                result.entries.append((article_id, base))
                continue
            known = result.by_article.get(article_id)
            if known is not None and known != base:
                result.id_conflicts.append((article_id, known, base))
                continue                      # never merged into either identity
            if known == base:
                continue                      # same id, same base: deduplicated
            result.entries.append((article_id, base))
            result.by_article[article_id] = base
            result.sources[article_id] = source
            identity = result.bases.setdefault(base, BaseIdentity(base))
            if article_id not in identity.article_ids:
                identity.article_ids.append(article_id)
            for set_id in set_of.get(article_id, []):
                if set_id not in identity.set_ids:
                    identity.set_ids.append(set_id)
            if source != SOURCE_PRICE_BASE and price_base and price_base != base:
                result.divergences.append((article_id, base, price_base))

    seen: dict[str, str] = {}
    for base in result.bases:
        first = seen.setdefault(base.casefold(), base)
        if first != base:
            result.case_collisions.append((first, base))
    return result


@dataclass(frozen=True)
class PriceBaseConflict:
    """A stored price record keyed to a base other than its article's canonical base."""

    item: str            # the full article code the record prices
    stored_base: str     # the record's article_code
    canonical_base: str  # the base the article resolves to now
    level: str = ""
    currency: str = ""


def stale_price_bases(snapshot, identities: BaseIdentityMap | None = None) -> list[PriceBaseConflict]:
    """Stored price records whose base differs from the canonical base of the article they price.

    A record's key is ``article_code`` (base) plus a variant condition that starts with
    ``item[len(base):]``, so the priced article is ``article_code + variant_condition.split(" ")[0]``.
    Re-keying a stored record is unsafe (its condition depends on the base length); this only
    detects the mismatch so an export can stop instead of attaching prices to another base.
    Global records, records whose item is not an engineering member and records of an unresolved
    article are not judged.
    """
    records = getattr(snapshot, "price_records", None) or []
    if not records:
        return []
    identities = identities or resolve_base_identities(snapshot)
    base_by_code: dict[str, str] = {}
    for article in getattr(snapshot, "articles", []) or []:
        base = identities.base_of(article.id) if getattr(article, "id", None) is not None else ""
        if base and article.code:
            base_by_code.setdefault(str(article.code).strip(), base)
    found: dict[tuple, PriceBaseConflict] = {}
    for rec in records:
        if getattr(rec, "is_global", False):
            continue
        stored = str(getattr(rec, "article_code", "") or "").strip()
        if not stored:
            continue
        suffix = str(getattr(rec, "variant_condition", "") or "").split(" ", 1)[0]
        item = stored + suffix
        canonical = base_by_code.get(item)
        if canonical is None or canonical == stored:
            continue
        found.setdefault((item, stored), PriceBaseConflict(
            item, stored, canonical, str(getattr(rec, "level", "") or ""),
            str(getattr(rec, "currency", "") or "")))
    return list(found.values())


def describe_price_base_conflicts(conflicts: list[PriceBaseConflict], limit: int = 5) -> str:
    """One-paragraph error text for an export that must not run on stale price bases."""
    shown = "; ".join(
        f"{c.item}: priced under '{c.stored_base}', article base is '{c.canonical_base}'"
        for c in conflicts[:limit])
    more = f" (+{len(conflicts) - limit} more)" if len(conflicts) > limit else ""
    return (
        f"{len(conflicts)} stored price record(s) are keyed to a different base article than the "
        f"Article workflow now resolves: {shown}{more}. Prices are not re-keyed automatically; "
        "compute prices again so they follow the current base articles, then export."
    )
