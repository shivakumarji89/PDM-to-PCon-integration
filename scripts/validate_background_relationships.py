"""Validate background relationship build + persistence (Phase D).

Headless, PDM-free checks that:
  * the :class:`~services.loading.loading_engine.LoadingEngine` engineering stage
    initializes the family AND builds the relationship maps in one pass; and
  * the family cache serializer (:meth:`PDMService.save_family_snapshot`) now
    persists the relationship maps.

Run:  python -m scripts.validate_background_relationships
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from core.application_context import ApplicationContext
from models.article import Article
from models.product import Product
from models.snapshot import Snapshot
from services.loading import LoadingEngine
from services.pdm_service import PDMService
from services.snapshot_serialization import engineering_relationships_to_dict


class _StubActivity:
    """Minimal ActivityHandle stand-in for the engineering stage."""

    def update_step(self, *args, **kwargs) -> None:
        pass


def _snapshot_with_articles() -> Snapshot:
    product = Product(id="prod1", code="DSK", name="Desk")
    snapshot = Snapshot(id="prod1", product=product)
    snapshot.articles = [
        Article(id="AR001", product_id="prod1", code="AR001"),
        Article(id="AR002", product_id="prod1", code="AR002"),
    ]
    return snapshot


def main() -> int:
    context = ApplicationContext()

    # 1) LoadingEngine engineering stage: init + relationship build together.
    engine = LoadingEngine(context)
    snapshot = _snapshot_with_articles()
    engine._engineering_initialization(snapshot, _StubActivity())

    assert snapshot.engineering.families, "engineering not initialized"
    members = snapshot.engineering.families[0].members
    assert len(members) == 2, "one member per article expected"
    # No assignments yet -> relationship maps exist but are empty (honest).
    rels = snapshot.engineering.relationships
    assert rels is not None
    assert rels.article_to_properties == {}
    assert rels.article_property_values == {}

    # 2) After assignments, rebuild fills the maps.
    context.engineering_assignment_service.set_value(members[0], "P001", "1200")
    context.engineering_assignment_service.set_value(members[1], "P001", "1400")
    context.engineering_relationship_service.rebuild(snapshot)
    rels = snapshot.engineering.relationships
    assert rels.article_to_properties == {
        "AR001": ["P001"],
        "AR002": ["P001"],
    }, rels.article_to_properties
    assert rels.property_to_values == {"P001": ["1200", "1400"]}

    # 3) Family cache serializer persists the relationship maps.
    engineering_dict = PDMService._engineering_dict(snapshot.engineering)
    assert "relationships" in engineering_dict, "relationships not serialized"
    assert engineering_dict["relationships"] == engineering_relationships_to_dict(
        rels
    )

    # 4) Full save_family_snapshot writes the relationships to disk.
    with tempfile.TemporaryDirectory() as tmp:
        original = PDMService._SNAPSHOT_CACHE_DIR
        try:
            PDMService._SNAPSHOT_CACHE_DIR = Path(tmp)
            pdm = PDMService(context)
            path = pdm.save_family_snapshot(snapshot, "Test Family")
            assert path is not None and path.exists(), "family snapshot not written"
            payload = json.loads(path.read_text(encoding="utf-8"))
            saved = payload["engineering"]["relationships"]
            assert saved["property_to_values"] == {"P001": ["1200", "1400"]}
        finally:
            PDMService._SNAPSHOT_CACHE_DIR = original

    print("PASS: background relationship build + family-cache persistence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
