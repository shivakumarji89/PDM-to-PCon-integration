"""Validate ArtBase derivation: per base master, the allowed value subset.

Headless, PDM-free. Mirrors the user's oak/hfk/bfk model: a value confined to a
base article restricts the other bases to their own value subset.

Run:  python scripts/validate_artbase.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.application_context import ApplicationContext
from models.article import Article
from models.article_set import ArticleSet, SetAttribute, SetValue
from models.engineering import Engineering
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict


def _snapshot() -> Snapshot:
    # Two base masters: GEP1 (article a1), GEP2 (articles a2, a3).
    a1 = Article(id="a1", code="GEP1OAK", product_id="P1")
    a2 = Article(id="a2", code="GEP2HFK", product_id="P1")
    a3 = Article(id="a3", code="GEP2BFK", product_id="P1")
    # Finish: oak only on GEP1; hfk, bfk only on GEP2 (each base a proper subset).
    finish = Property(id="F", name="Finish", display_order=1, values=[
        PropertyValue(id="oak", property_id="F", value="Oak", code="O"),
        PropertyValue(id="hfk", property_id="F", value="HFK", code="H"),
        PropertyValue(id="bfk", property_id="F", value="BFK", code="B"),
    ])
    # Grade: value G on every base (generic) -> no ArtBase entry expected.
    grade = Property(id="G", name="Grade", display_order=2, values=[
        PropertyValue(id="g1", property_id="G", value="Std", code="S"),
    ])
    m1 = MemberArticle(id="m1", article_id="a1", family_id="F1", reduced_article="GEP1")
    m2 = MemberArticle(id="m2", article_id="a2", family_id="F1", reduced_article="GEP2")
    m3 = MemberArticle(id="m3", article_id="a3", family_id="F1", reduced_article="GEP2")
    eng = Engineering(families=[EngineeringFamily(id="F1", members=[m1, m2, m3])])
    aset = ArticleSet(id="S", article_ids=["a1", "a2", "a3"], properties=[
        SetAttribute(id="F", name="Finish", values=[
            SetValue(id="oak", value="Oak", code="O", article_ids=["a1"]),
            SetValue(id="hfk", value="HFK", code="H", article_ids=["a2"]),
            SetValue(id="bfk", value="BFK", code="B", article_ids=["a3"]),
        ]),
        SetAttribute(id="G", name="Grade", values=[
            SetValue(id="g1", value="Std", code="S", article_ids=["a1", "a2", "a3"]),
        ]),
    ])
    return Snapshot(id="S", articles=[a1, a2, a3], properties=[finish, grade],
                    engineering=eng, article_sets=[aset])


def main() -> None:
    ctx = ApplicationContext()
    service = ctx.engineering_artbase_service
    snap = _snapshot()

    art = service.ensure_art_base(snap)
    # GEP1 restricted to {oak}; GEP2 restricted to {bfk, hfk} (sorted ids).
    assert art == {"GEP1": {"F": ["oak"]}, "GEP2": {"F": ["bfk", "hfk"]}}, art

    # Generic property (Grade, value on every base) yields NO ArtBase entry.
    assert all("G" not in ents for ents in art.values()), art

    # Deterministic + stored on the snapshot.
    assert service.build_art_base(snap) == art, "non-deterministic"
    assert snap.art_base == art

    # JSON round-trip preserves the restrictions.
    restored = snapshot_from_dict(snapshot_to_dict(snap))
    assert restored.art_base == art, restored.art_base

    print("validate_artbase: PASS")


if __name__ == "__main__":
    main()
