"""Base repository.

Repositories encapsulate data access for a specific entity. They receive the
shared :class:`ApplicationContext` so they can reach the relevant backend
services in a later phase. Phase 2 contains no data access.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.application_context import ApplicationContext


class BaseRepository:
    """Common base for entity repositories."""

    def __init__(self, context: "ApplicationContext") -> None:
        self.context = context
