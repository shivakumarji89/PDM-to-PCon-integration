"""Activity Framework - the public operation handle.

An :class:`ActivityHandle` is the *only* API business code uses to report on an
operation. Business code never touches the :class:`~core.activity.models.Activity`
model directly; instead it holds a handle and calls these methods, and every
mutation is routed through the owning :class:`~core.activity.service.
ActivityService` by activity id.

The handle is a thin, dependency-free facade: it stores a reference to the
service and the activity id, and forwards each call. This keeps ownership of all
:class:`Activity` instances (and all event emission) inside the service.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from core.activity.models import LogLevel

if TYPE_CHECKING:  # avoid a runtime import cycle (service imports this module)
    from core.activity.service import ActivityService


class ActivityHandle:
    """The single public interface for reporting on one activity."""

    __slots__ = ("_service", "_id", "__weakref__")

    def __init__(self, service: "ActivityService", activity_id: str) -> None:
        self._service = service
        self._id = activity_id

    # -- identity ----------------------------------------------------------
    @property
    def id(self) -> str:
        """The activity's unique identifier."""
        return self._id

    @property
    def is_cancel_requested(self) -> bool:
        """Whether cancellation has been requested (future cooperative stop)."""
        return self._service.is_cancel_requested(self._id)

    # -- reporting API -----------------------------------------------------
    def update_step(
        self,
        step: str | None = None,
        *,
        item: str | None = None,
        stage_name: str | None = None,
        stage_index: int | None = None,
        total_stages: int | None = None,
    ) -> None:
        """Update the current step / item / stage."""
        self._service.update_step(
            self._id,
            step,
            item=item,
            stage_name=stage_name,
            stage_index=stage_index,
            total_stages=total_stages,
        )

    def update_items(
        self,
        processed: int | None = None,
        total: int | None = None,
        *,
        increment: int | None = None,
    ) -> None:
        """Update processed / total item counts (percentage is derived)."""
        self._service.update_items(
            self._id, processed=processed, total=total, increment=increment
        )

    def update_context(
        self, values: Mapping[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Merge contextual information (e.g. ``Family="Bolster"``)."""
        self._service.update_context(self._id, values, **kwargs)

    def add_log(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        """Append a chronological log entry."""
        self._service.add_log(self._id, message, level)

    # -- terminal transitions ---------------------------------------------
    def complete(self, message: str = "") -> None:
        """Mark the activity completed successfully."""
        self._service.complete(self._id, message)

    def fail(self, error_message: str = "") -> None:
        """Mark the activity failed with an optional error message."""
        self._service.fail(self._id, error_message)

    def cancel(self, message: str = "") -> None:
        """Request cancellation and mark the activity cancelled."""
        self._service.cancel(self._id, message)
