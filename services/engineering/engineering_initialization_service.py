"""Engineering initialization service.

Populates the Engineering section of an already-populated Snapshot: it creates
a single default :class:`~models.engineering_family.EngineeringFamily` and one
:class:`~models.member_article.MemberArticle` per source article.

Scope (Phase 2 - Step 3):
  * Modifies **only** ``snapshot.engineering``; everything else in the Snapshot
    is read-only.
  * **Idempotent** - calling :meth:`initialize` again rebuilds the same state.
  * Never accesses PDM, touches the UI, emits signals, or modifies source data.

It does NOT perform builder, reduction, validation, assignment, or generation -
those remain the responsibility of their own services.
"""
from __future__ import annotations

from uuid import uuid4

from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.snapshot import Snapshot
from services.base_service import BaseService
from services.engineering.constants import DEFAULT_FAMILY_ID, DEFAULT_FAMILY_NAME


class EngineeringInitializationService(BaseService):
    """Initializes ``snapshot.engineering`` from an already-populated snapshot."""

    def initialize(self, snapshot: Snapshot | None) -> None:
        """Populate ``snapshot.engineering`` with the default engineering
        hierarchy: one Default Family whose members mirror the snapshot's
        articles.

        Idempotent: any families previously created here are discarded first, so
        calling this repeatedly yields the same result. Only
        ``snapshot.engineering`` is mutated; ``snapshot.articles`` and all other
        source data are read only.
        """
        if snapshot is None or snapshot.engineering is None:
            return

        # Idempotency: discard the families this service owns before rebuilding.
        snapshot.engineering.families.clear()

        # One default family with one member per source article (read-only read
        # of snapshot.articles - the articles themselves are never modified).
        family = EngineeringFamily(
            id=DEFAULT_FAMILY_ID,
            name=DEFAULT_FAMILY_NAME,
            members=[
                MemberArticle(
                    id=uuid4().hex,
                    article_id=article.id,
                    family_id=DEFAULT_FAMILY_ID,
                    reduced_article="",
                    long_description="",
                )
                for article in snapshot.articles
            ],
        )
        snapshot.engineering.families.append(family)

    def sync(self, snapshot: Snapshot | None) -> None:
        """Additively bring the engineering hierarchy up to date with articles.

        Unlike :meth:`initialize` (which rebuilds from scratch), this **preserves**
        every existing family, member, reduction and assignment and only appends a
        member for each source article that does not yet have one. It is used by
        incremental loading so early engineering work is never discarded when more
        products merge into the snapshot later.

        The Default Family is created if missing; new members are added there and
        stamped with its ``family_id``. Only ``snapshot.engineering`` is mutated.
        """
        if snapshot is None or snapshot.engineering is None:
            return

        families = snapshot.engineering.families
        default_family = next(
            (f for f in families if f.id == DEFAULT_FAMILY_ID), None
        )
        if default_family is None:
            default_family = EngineeringFamily(
                id=DEFAULT_FAMILY_ID, name=DEFAULT_FAMILY_NAME, members=[]
            )
            families.append(default_family)

        # Backfill: guarantee every existing member carries its owning family id
        # (older members / restored caches may predate the family_id field).
        for family in families:
            for member in family.members:
                if not member.family_id:
                    member.family_id = family.id

        # Article ids that already have a member in ANY family are left untouched.
        existing_ids = {
            member.article_id
            for family in families
            for member in family.members
        }
        for article in snapshot.articles:
            if article.id in existing_ids:
                continue
            default_family.members.append(
                MemberArticle(
                    id=uuid4().hex,
                    article_id=article.id,
                    family_id=default_family.id,
                    reduced_article="",
                    long_description="",
                )
            )
            existing_ids.add(article.id)
