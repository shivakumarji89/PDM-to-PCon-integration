"""EngineeringRelationships model.

An explicit, serializable projection of the engineering relationship graph held
under :class:`~models.engineering.Engineering`. Where the object graph stores
relationships implicitly (a member owns its property assignments), this model
makes the three relationship views the concept requires first-class and
persistable:

  * **Article -> Property**   - which property definitions an article uses.
  * **Property -> Value**     - which values a property takes across the family.
  * **Article -> Property -> Value** - the value an article gives each property.

Identifiers are the engineering-domain ids: article ids are
:attr:`~models.member_article.MemberArticle.article_id` (a source
:class:`~models.article.Article` id) and property ids are
:attr:`~models.property_definition.PropertyDefinition.id`.

Pure data - fields only. The maps are rebuilt by
:class:`~services.engineering.engineering_relationship_service.
EngineeringRelationshipService`; nothing here computes or mutates them.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EngineeringRelationships:
    """Explicit Article/Property/Value relationship maps (definition only)."""

    #: article_id -> ordered, unique property ids that article uses.
    article_to_properties: dict[str, list[str]] = field(default_factory=dict)

    #: property_id -> ordered, unique values seen for that property.
    property_to_values: dict[str, list[str]] = field(default_factory=dict)

    #: article_id -> { property_id -> assigned value }.
    article_property_values: dict[str, dict[str, str]] = field(default_factory=dict)
