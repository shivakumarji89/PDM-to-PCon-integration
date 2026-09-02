"""Validate the Engineering relationship engine (Phase C).

Headless, PDM-free check that
:class:`services.engineering.engineering_relationship_service.
EngineeringRelationshipService` derives the three relationship views correctly
from member assignments, that they match the object graph both ways, and that
they survive an Engineering JSON round-trip.

Run:  python -m scripts.validate_relationship_engine
"""
from __future__ import annotations

from core.application_context import ApplicationContext
from models.engineering import Engineering
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.property_assignment import PropertyAssignment
from models.snapshot import Snapshot
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict


def _build_snapshot() -> Snapshot:
    """Two articles with overlapping property assignments."""
    ar1 = MemberArticle(
        id="m1", article_id="AR001",
        property_values=[
            PropertyAssignment(property_id="P001", value="1200"),
            PropertyAssignment(property_id="P003", value="Black"),
        ],
    )
    ar2 = MemberArticle(
        id="m2", article_id="AR002",
        property_values=[
            PropertyAssignment(property_id="P001", value="1400"),
            PropertyAssignment(property_id="P002", value="720"),
        ],
    )
    ar3 = MemberArticle(id="m3", article_id="AR003")  # no assignments
    engineering = Engineering(
        families=[
            EngineeringFamily(id="default", name="Default", members=[ar1, ar2, ar3])
        ]
    )
    return Snapshot(id="prod1", engineering=engineering)


def main() -> int:
    context = ApplicationContext()
    snapshot = _build_snapshot()

    rels = context.engineering_relationship_service.rebuild(snapshot)
    assert rels is not None

    # Article -> Property (ordered, unique; unassigned article absent).
    assert rels.article_to_properties == {
        "AR001": ["P001", "P003"],
        "AR002": ["P001", "P002"],
    }, rels.article_to_properties

    # Property -> Value (union across articles, first-seen order).
    assert rels.property_to_values == {
        "P001": ["1200", "1400"],
        "P003": ["Black"],
        "P002": ["720"],
    }, rels.property_to_values

    # Article -> Property -> Value.
    assert rels.article_property_values == {
        "AR001": {"P001": "1200", "P003": "Black"},
        "AR002": {"P001": "1400", "P002": "720"},
    }, rels.article_property_values

    # Reverse check: every map entry traces back to a real assignment.
    graph = {
        m.article_id: {a.property_id: a.value for a in m.property_values}
        for f in snapshot.engineering.families
        for m in f.members
        if m.property_values
    }
    assert rels.article_property_values == graph, "maps diverge from object graph"

    # Idempotent rebuild.
    again = context.engineering_relationship_service.rebuild(snapshot)
    assert again == rels, "rebuild is not idempotent"

    # Survives Engineering JSON round-trip.
    restored = snapshot_from_dict(snapshot_to_dict(snapshot))
    assert restored.engineering.relationships == rels, "relationships lost in JSON"
    assert restored == snapshot, "snapshot changed across JSON round-trip"

    print("PASS: relationship engine (maps, reverse-check, idempotent, JSON)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
