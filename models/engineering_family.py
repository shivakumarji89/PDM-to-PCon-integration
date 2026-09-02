"""EngineeringFamily model.

The first engineering concept held under :class:`~models.engineering.Engineering`.
Phase 2 - Step 1 is intentionally minimal: it carries an identifier and a name
only. Members, reduction, properties, assignments, builder state and validation
are future additions. Fields only - no methods, logic, or services.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from models.member_article import MemberArticle


@dataclass
class EngineeringFamily:
    """A named engineering family (Phase 2 - Step 2B: identity + members)."""

    id: str = ""
    name: str = ""
    members: list[MemberArticle] = field(default_factory=list)
