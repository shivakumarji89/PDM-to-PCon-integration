"""Base class for all services.

Every service receives the shared :class:`ApplicationContext`, giving it
access to configuration, application state, and sibling services. Phase 2
contains no implementation.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.application_context import ApplicationContext


class BaseService:
    """Common base providing access to the application context."""

    def __init__(self, context: "ApplicationContext") -> None:
        self.context = context
