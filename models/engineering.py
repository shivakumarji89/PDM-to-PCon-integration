"""Engineering section of the Snapshot.

Root container for future engineering functionality (families, reduction rules,
property definitions/assignments, builder state, validation). This is the
minimal Phase-2 root: it holds an (empty) ``families`` collection only - no
methods, logic, services, serialization, or persistence.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from models.engineering_family import EngineeringFamily
from models.engineering_relationships import EngineeringRelationships
from models.engineering_class import EngineeringClass
from models.property_definition import PropertyDefinition


@dataclass
class Engineering:
    """Root container for all engineering information on a Snapshot.

    Owns Engineering Data created by the application - it never communicates
    with PDM (all source data arrives via the Snapshot). Phase 2 holds only an
    empty ``families`` collection and will gradually contain Families, Builder,
    Validation and other engineering concepts.
    """

    families: list[EngineeringFamily] = field(default_factory=list)
    properties: list[PropertyDefinition] = field(default_factory=list)
    classes: list[EngineeringClass] = field(default_factory=list)
    relationships: EngineeringRelationships = field(
        default_factory=EngineeringRelationships
    )
