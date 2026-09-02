"""Engineering relationship service.

Rebuilds the explicit relationship maps held in
:class:`~models.engineering_relationships.EngineeringRelationships` from the
authoritative engineering object graph (families -> members -> property
assignments). It is the "relationship engine" of the architecture: it derives
the three relationship views from what is actually assigned and writes them onto
``snapshot.engineering.relationships``.

Rules:
  * Reads **only** ``snapshot.engineering`` (families, members, assignments);
    never touches source data, PDM, the UI, or signals.
  * **Deterministic**: ids and values appear in first-seen order and are unique.
  * **Idempotent**: calling :meth:`rebuild` again yields the same maps.
  * A member with no assignments contributes no relationships.
"""
from __future__ import annotations

from models.engineering_relationships import EngineeringRelationships
from models.snapshot import Snapshot
from services.base_service import BaseService


class EngineeringRelationshipService(BaseService):
    """Derive and store the engineering relationship maps."""

    def rebuild(self, snapshot: Snapshot | None) -> EngineeringRelationships | None:
        """Rebuild ``snapshot.engineering.relationships`` and return it.

        Returns ``None`` when there is no engineering section to work with.
        """
        if snapshot is None or snapshot.engineering is None:
            return None

        article_to_properties: dict[str, list[str]] = {}
        property_to_values: dict[str, list[str]] = {}
        article_property_values: dict[str, dict[str, str]] = {}

        for family in snapshot.engineering.families:
            for member in family.members:
                article_id = member.article_id
                if not article_id:
                    continue
                for assignment in member.property_values:
                    property_id = assignment.property_id
                    if not property_id:
                        continue
                    value = assignment.value

                    # Article -> Property (ordered, unique).
                    properties = article_to_properties.setdefault(article_id, [])
                    if property_id not in properties:
                        properties.append(property_id)

                    # Property -> Value (ordered, unique).
                    values = property_to_values.setdefault(property_id, [])
                    if value not in values:
                        values.append(value)

                    # Article -> Property -> Value (last assignment wins).
                    article_property_values.setdefault(article_id, {})[
                        property_id
                    ] = value

        relationships = EngineeringRelationships(
            article_to_properties=article_to_properties,
            property_to_values=property_to_values,
            article_property_values=article_property_values,
        )
        snapshot.engineering.relationships = relationships
        return relationships
