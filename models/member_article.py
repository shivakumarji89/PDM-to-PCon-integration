"""MemberArticle model.

Represents an Article as a *member* of an
:class:`~models.engineering_family.EngineeringFamily`. Its responsibility is to
own engineering information that belongs to the membership - not the PDM source
Article itself.

Phase 2 - Step 2B is intentionally minimal: it carries its own ``id`` only (the
identity of the MemberArticle, not an Article identifier). How a MemberArticle
relates to an Article is deliberately undecided. Fields only - no methods,
logic, or services.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from models.property_assignment import PropertyAssignment


@dataclass
class MemberArticle:
    """A family member (Phase 2 - Step 2B: own identity only)."""

    id: str = ""
    article_id: str = ""
    family_id: str = ""
    reduced_article: str = ""
    short_description: str = ""
    long_description: str = ""
    relation_object: str = ""
    code_scheme: str = ""
    property_values: list[PropertyAssignment] = field(default_factory=list)
