"""Engineering family management service.

Create, rename and delete engineering families on an already-populated Snapshot.
It mutates **only** ``snapshot.engineering.families`` and never touches source
data, PDM, the UI, or signals.

Rules (Phase 2 - Step 6):
  * The Default Family (see :data:`DEFAULT_FAMILY_ID`) always exists and cannot
    be renamed or deleted.
  * A new family starts empty; no members are moved.
  * A family is deletable only when it is empty; non-empty families are kept.

It performs no member movement, builder, reduction, validation, assignment, or
generation.
"""
from __future__ import annotations

from uuid import uuid4

from models.engineering_family import EngineeringFamily
from models.snapshot import Snapshot
from services.base_service import BaseService
from services.engineering.constants import DEFAULT_FAMILY_ID

#: Name given to a newly created family.
NEW_FAMILY_NAME = "New Family"


class EngineeringFamilyService(BaseService):
    """Create / rename / delete engineering families on a snapshot."""

    @staticmethod
    def is_default(family: EngineeringFamily | None) -> bool:
        """Whether ``family`` is the protected Default Family."""
        return getattr(family, "id", "") == DEFAULT_FAMILY_ID

    def create_family(
        self, snapshot: Snapshot | None, name: str = NEW_FAMILY_NAME
    ) -> EngineeringFamily | None:
        """Append a new, empty family and return it (or ``None`` if unavailable)."""
        if snapshot is None or snapshot.engineering is None:
            return None
        family = EngineeringFamily(id=uuid4().hex, name=name, members=[])
        snapshot.engineering.families.append(family)
        return family

    def rename_family(
        self,
        snapshot: Snapshot | None,
        family: EngineeringFamily | None,
        new_name: str,
    ) -> bool:
        """Rename ``family``. The Default Family and blank names are rejected."""
        if family is None or self.is_default(family):
            return False
        name = (new_name or "").strip()
        if not name:
            return False
        family.name = name
        return True

    def delete_family(
        self, snapshot: Snapshot | None, family: EngineeringFamily | None
    ) -> bool:
        """Delete ``family`` only when it is not the Default Family and is empty.

        Non-empty families are preserved (no members are moved).
        """
        if snapshot is None or snapshot.engineering is None or family is None:
            return False
        if self.is_default(family) or family.members:
            return False
        try:
            snapshot.engineering.families.remove(family)
        except ValueError:
            return False
        return True
