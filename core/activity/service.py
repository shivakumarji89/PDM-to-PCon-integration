"""Activity Framework - the central service and events.

The :class:`ActivityService` owns every :class:`~core.activity.models.Activity`
instance and is the single place that mutates them. Business code never mutates
an activity directly; it calls :meth:`ActivityService.start_activity`, receives
an :class:`~core.activity.handle.ActivityHandle`, and reports through the handle
(which forwards to this service by activity id).

Design:
  * **UI-independent** - only :mod:`PySide6.QtCore` is used (signals); no widgets.
  * **Not a singleton** - construct it and inject it (e.g. via the application
    context) so it stays testable and modular.
  * **Concurrent** - it manages many activities at once, keyed by unique id;
    every update is routed by id and never assumes a single running activity.
  * **Thread-aware** - mutations are guarded by a lock, and Qt signals emitted
    from a worker thread are delivered to the service's thread (queued), so UI
    consumers update safely.
  * **Lightweight** - each update performs a small in-place mutation and emits a
    single signal; there is no per-update object churn.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Mapping

from core.activity.events import (
    ActivityCancelled,
    ActivityChanged,
    ActivityCompleted,
    ActivityFailed,
    ActivityStarted,
)
from core.activity.handle import ActivityHandle
from core.activity.models import (
    Activity,
    ActivityPriority,
    ActivitySnapshot,
    ActivityStatus,
    ActivityType,
    LogLevel,
)
from core.events import EventBus


class ActivityService:
    """Owns and publishes updates for all activities (id-routed, concurrent).

    Consumers receive immutable :class:`~core.activity.models.ActivitySnapshot`
    objects wrapped in typed :class:`~core.activity.events.ActivityEvent` objects
    published through a shared :class:`~core.events.EventBus`; the mutable
    :class:`Activity` instances never leave the service.

    The service does **not** define its own event mechanism - it reuses the
    generic application event bus, so future services publish their own events
    the same way. The bus is injected (DI); when omitted a private bus is
    created, keeping the service usable standalone and testable.

    Guarantees (the contract UI components rely on):
      * **Event lifecycle / ordering** - for any activity the event order is
        always ``ActivityStarted`` -> zero or more ``ActivityChanged`` -> exactly
        one terminal event (``ActivityCompleted`` / ``ActivityFailed`` /
        ``ActivityCancelled``). No event is ever emitted after the terminal one;
        post-terminal updates (``update_*``, ``add_log``, a second ``cancel``)
        are silent no-ops. Because every event flows through the bus's single
        marshalling signal, delivery order is preserved.
      * **Single snapshot per change** - each state change builds exactly one
        :class:`ActivitySnapshot`, which is shared by every event subscriber and
        returned by the pull queries; multiple subscribers never trigger
        duplicate snapshot creation.
      * **UI independence** - no widgets, docks, dialogs or window are imported
        or referenced; the framework is reusable anywhere.
      * **Retention** - finished activities are retained (unlimited) by default;
        :meth:`clear_finished` is manual cleanup, and :meth:`_enforce_retention`
        is the single seam where future automatic policies attach.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.event_bus: EventBus = event_bus or EventBus()
        self._activities: dict[str, Activity] = {}
        # One cached snapshot per activity, refreshed on every state change so
        # events and pull queries reuse a single snapshot per update.
        self._snapshots: dict[str, ActivitySnapshot] = {}
        self._lock = threading.RLock()

    # -- creation ----------------------------------------------------------
    def start_activity(
        self,
        title: str,
        activity_type: str | ActivityType = ActivityType.GENERIC,
        *,
        total_items: int = 0,
        total_stages: int = 0,
        priority: ActivityPriority = ActivityPriority.NORMAL,
        supports_cancel: bool = False,
        context: Mapping[str, Any] | None = None,
        parent_id: str | None = None,
    ) -> ActivityHandle:
        """Create and start a new activity; return its :class:`ActivityHandle`.

        Publishes exactly one :class:`~core.activity.events.ActivityStarted`
        event - always the first event for the activity.
        """
        type_value = (
            activity_type.value
            if isinstance(activity_type, ActivityType)
            else str(activity_type)
        )
        activity = Activity(
            title=title,
            type=type_value,
            total_items=total_items,
            total_stages=total_stages,
            priority=priority,
            supports_cancel=supports_cancel,
            parent_id=parent_id,
        )
        activity.status = ActivityStatus.RUNNING
        activity.start_time = self._now()
        if context:
            activity.context.update(context)

        with self._lock:
            self._activities[activity.id] = activity
            if parent_id is not None:
                parent = self._activities.get(parent_id)
                if parent is not None:
                    parent.child_ids.append(activity.id)
            snapshot = self._refresh_snapshot(activity)

        self.event_bus.publish(ActivityStarted(snapshot=snapshot))
        return ActivityHandle(self, activity.id)

    # -- updates (routed by id; silent no-op after a terminal state) -------
    def update_step(
        self,
        activity_id: str,
        step: str | None = None,
        *,
        item: str | None = None,
        stage_name: str | None = None,
        stage_index: int | None = None,
        total_stages: int | None = None,
    ) -> None:
        with self._lock:
            activity = self._get_active(activity_id)
            if activity is None:
                return
            if step is not None:
                activity.current_step = step
            if item is not None:
                activity.current_item = item
            if stage_name is not None:
                activity.stage_name = stage_name
            if stage_index is not None:
                activity.stage_index = stage_index
            if total_stages is not None:
                activity.total_stages = total_stages
            snapshot = self._refresh_snapshot(activity)
        self.event_bus.publish(ActivityChanged(snapshot=snapshot))

    def update_items(
        self,
        activity_id: str,
        *,
        processed: int | None = None,
        total: int | None = None,
        increment: int | None = None,
    ) -> None:
        with self._lock:
            activity = self._get_active(activity_id)
            if activity is None:
                return
            if total is not None:
                activity.total_items = total
            if processed is not None:
                activity.processed_items = processed
            if increment:
                activity.processed_items += increment
            snapshot = self._refresh_snapshot(activity)
        self.event_bus.publish(ActivityChanged(snapshot=snapshot))

    def update_context(
        self,
        activity_id: str,
        values: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        with self._lock:
            activity = self._get_active(activity_id)
            if activity is None:
                return
            if values:
                activity.context.update(values)
            if kwargs:
                activity.context.update(kwargs)
            snapshot = self._refresh_snapshot(activity)
        self.event_bus.publish(ActivityChanged(snapshot=snapshot))

    def add_log(
        self, activity_id: str, message: str, level: LogLevel = LogLevel.INFO
    ) -> None:
        with self._lock:
            activity = self._get_active(activity_id)
            if activity is None:
                return
            activity.add_log(message, level)
            snapshot = self._refresh_snapshot(activity)
        self.event_bus.publish(ActivityChanged(snapshot=snapshot))

    # -- terminal transitions (each publishes exactly one terminal event) --
    def complete(self, activity_id: str, message: str = "") -> None:
        with self._lock:
            activity = self._get_active(activity_id)
            if activity is None:
                return
            activity.status = ActivityStatus.COMPLETED
            activity.end_time = self._now()
            if message:
                activity.add_log(message, LogLevel.SUCCESS)
            snapshot = self._refresh_snapshot(activity)
            self._enforce_retention()
        self.event_bus.publish(ActivityCompleted(snapshot=snapshot))

    def fail(self, activity_id: str, error_message: str = "") -> None:
        with self._lock:
            activity = self._get_active(activity_id)
            if activity is None:
                return
            activity.status = ActivityStatus.FAILED
            activity.end_time = self._now()
            activity.error_message = error_message
            if error_message:
                activity.add_log(error_message, LogLevel.ERROR)
            snapshot = self._refresh_snapshot(activity)
            self._enforce_retention()
        self.event_bus.publish(ActivityFailed(snapshot=snapshot))

    def cancel(self, activity_id: str, message: str = "") -> None:
        """Cancel an active activity.

        Cancelling an unknown or already-finished activity is a silent no-op and
        emits no event, preserving the ordering guarantee (no event after a
        terminal state).
        """
        with self._lock:
            activity = self._activities.get(activity_id)
            if activity is None or not activity.is_active:
                return
            activity.cancel_requested = True
            activity.status = ActivityStatus.CANCELLED
            activity.end_time = self._now()
            if message:
                activity.add_log(message, LogLevel.WARNING)
            snapshot = self._refresh_snapshot(activity)
            self._enforce_retention()
        self.event_bus.publish(ActivityCancelled(snapshot=snapshot))

    # -- queries (immutable cached snapshots only; Activity stays internal) -
    def get_snapshot(self, activity_id: str) -> ActivitySnapshot | None:
        """Return the current cached immutable snapshot, or ``None``."""
        with self._lock:
            return self._snapshots.get(activity_id)

    def is_cancel_requested(self, activity_id: str) -> bool:
        with self._lock:
            activity = self._activities.get(activity_id)
            return bool(activity is not None and activity.cancel_requested)

    def snapshots(self) -> list[ActivitySnapshot]:
        """Return the current cached snapshots of all activities."""
        with self._lock:
            return list(self._snapshots.values())

    def active_snapshots(self) -> list[ActivitySnapshot]:
        with self._lock:
            return [s for s in self._snapshots.values() if s.is_active]

    def finished_snapshots(self) -> list[ActivitySnapshot]:
        with self._lock:
            return [s for s in self._snapshots.values() if s.is_finished]

    def clear_finished(self) -> None:
        """Manually drop finished activities (their logs go with them).

        This is the *manual cleanup* retention operation; automatic policies can
        be added later via :meth:`_enforce_retention` without touching callers.
        """
        with self._lock:
            self._activities = {
                aid: a for aid, a in self._activities.items() if not a.is_finished
            }
            self._snapshots = {
                aid: s for aid, s in self._snapshots.items() if not s.is_finished
            }

    # -- internals ---------------------------------------------------------
    def _get_active(self, activity_id: str) -> Activity | None:
        activity = self._activities.get(activity_id)
        if activity is None or activity.is_finished:
            return None
        return activity

    def _refresh_snapshot(self, activity: Activity) -> ActivitySnapshot:
        """Build one snapshot for the current state and cache it.

        Called exactly once per state change, so all event subscribers and the
        pull queries share a single snapshot per update (no duplicates).
        """
        snapshot = ActivitySnapshot.from_activity(activity)
        self._snapshots[activity.id] = snapshot
        return snapshot

    def _enforce_retention(self) -> None:
        """Retention seam for finished activities.

        Intentionally a no-op today (unlimited history). It is the single place
        a future retention policy attaches - maximum history size, automatic
        cleanup, or time-based expiry - without changing the public API or any
        caller. Manual cleanup is already available via :meth:`clear_finished`.
        """

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
