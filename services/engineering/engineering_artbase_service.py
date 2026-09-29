"""Engineering ArtBase service.

Derives the snapshot's OCD article base table (``ArtBase``): per BASE ARTICLE
(reduced master), the value set each property/option is *allowed*, restricted to
the values that base's articles actually carry.

This is the OCD-standard way to confine a value to certain base articles - a base
article then shows only its allowed values (e.g. base 1 -> oak; base 2 -> hfk,
bfk). A value scoped to a subset of bases is expressed here, not as a ``$BAN``
precondition. Derive-only; feeds OCD ArtBase export.
"""
from __future__ import annotations

from collections import defaultdict

from models.snapshot import Snapshot
from services.base_service import BaseService


class EngineeringArtbaseService(BaseService):
    """Build the active snapshot's article base (ArtBase) restrictions."""

    def ensure_art_base(
        self, snapshot: Snapshot | None
    ) -> dict[str, dict[str, list[str]]]:
        """Return the ArtBase restrictions, deriving them once if empty."""
        if snapshot is None:
            return {}
        if not snapshot.art_base:
            snapshot.art_base = self.build_art_base(snapshot)
        return snapshot.art_base

    def rebuild_art_base(
        self, snapshot: Snapshot | None
    ) -> dict[str, dict[str, list[str]]]:
        """Force a fresh derivation, discarding any prior result."""
        if snapshot is None:
            return {}
        snapshot.art_base = self.build_art_base(snapshot)
        return snapshot.art_base

    def build_art_base(
        self, snapshot: Snapshot
    ) -> dict[str, dict[str, list[str]]]:
        """base master -> {property/option id -> sorted value ids}, kept only
        where a base allows a PROPER SUBSET of an entity's values (a real
        restriction; a base allowing every value needs no ArtBase entry).
        Covers both properties and options."""
        base_by_article = self._base_by_article(snapshot)
        # Combination values are gated by a relation, not ArtBase - skip them.
        classify = self.context.engineering_relation_service.classify_values(snapshot)
        allowed: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
        full: dict[str, set] = defaultdict(set)
        for article_set in snapshot.article_sets:
            for attr in list(article_set.properties) + list(article_set.options):
                eid = str(attr.id)
                for value in attr.values:
                    vid = str(value.id)
                    if classify.get(vid) == "combination":
                        continue
                    bases = {
                        base_by_article.get(str(aid)) for aid in value.article_ids
                    }
                    bases.discard(None)
                    bases.discard("")
                    if not bases:
                        continue
                    full[eid].add(vid)
                    for base in bases:
                        allowed[base][eid].add(vid)
        result: dict[str, dict[str, list[str]]] = {}
        for base, entities in allowed.items():
            for eid, vids in entities.items():
                if vids < full[eid]:  # proper subset -> a real restriction
                    result.setdefault(base, {})[eid] = sorted(vids)
        return result

    @staticmethod
    def _base_by_article(snapshot: Snapshot) -> dict[str, str]:
        """article id -> its BASE article number (reduced code); un-reduced
        articles omitted (same base-only rule as the relation service)."""
        result: dict[str, str] = {}
        if snapshot.engineering is None:
            return result
        for family in snapshot.engineering.families:
            for member in family.members:
                base = (member.reduced_article or "").strip()
                if base:
                    result[str(member.article_id)] = base
        return result
