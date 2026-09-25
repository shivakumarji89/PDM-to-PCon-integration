"""Activity Framework events.

Concrete :class:`~core.events.AppEvent` types published by the
:class:`~core.activity.service.ActivityService` through the shared application
:class:`~core.events.EventBus`. Activity events are the *first consumer* of the
generic event infrastructure; future services publish their own ``AppEvent``
subclasses the same way.

Event contract (the guarantee UI components rely on):
  * **Payload** - every activity event carries a single ``snapshot`` field, an
    immutable :class:`~core.activity.models.ActivitySnapshot`. Consumers never
    see mutable framework state, and a snapshot captured on one thread is safe
    to read on another.
  * **Immutability** - events and their snapshots are frozen dataclasses.
  * **Thread** - events may be *published* from any thread, but the bus
    delivers them to subscribers on the bus's own (typically UI) thread, so
    handlers can touch the UI directly.
  * **Ordering** - per activity: exactly one :class:`ActivityStarted`, then zero
    or more :class:`ActivityChanged`, then exactly one terminal event
    (:class:`ActivityCompleted`, :class:`ActivityFailed`, or
    :class:`ActivityCancelled`). Nothing is emitted after the terminal event.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.activity.models import ActivitySnapshot
from core.events import AppEvent


@dataclass(frozen=True)
class ActivityEvent(AppEvent):
    """Base for all activity lifecycle events.

    Payload: immutable ``snapshot`` (:class:`~core.activity.models.
    ActivitySnapshot`) captured at the moment of the change.
    """

    snapshot: ActivitySnapshot


@dataclass(frozen=True)
class ActivityStarted(ActivityEvent):
    """Emitted once when an activity starts; always the first event for it."""


@dataclass(frozen=True)
class ActivityChanged(ActivityEvent):
    """Emitted on any progress / step / item / context / log change (0..n)."""


@dataclass(frozen=True)
class ActivityCompleted(ActivityEvent):
    """Emitted once when an activity completes successfully (terminal)."""


@dataclass(frozen=True)
class ActivityFailed(ActivityEvent):
    """Emitted once when an activity fails (terminal); snapshot has the error."""


@dataclass(frozen=True)
class ActivityCancelled(ActivityEvent):
    """Emitted once when an active activity is cancelled (terminal)."""
