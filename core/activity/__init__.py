"""Activity Framework.

A reusable, feature-independent framework for reporting progress, status and
execution details of long-running operations (Load, Generate, Export, Import,
Validation, Synchronization, Batch, ...).

Step 1 exposes the pure data model only. Later steps add the service, events,
progress API and the reusable UI panel.
"""
from __future__ import annotations

from core.activity.events import (
    ActivityCancelled,
    ActivityChanged,
    ActivityCompleted,
    ActivityEvent,
    ActivityFailed,
    ActivityStarted,
)
from core.activity.handle import ActivityHandle
from core.activity.models import (
    Activity,
    ActivityLogEntry,
    ActivityPriority,
    ActivitySnapshot,
    ActivityStatus,
    ActivityType,
    LogLevel,
)
from core.activity.service import ActivityService

__all__ = [
    "Activity",
    "ActivityCancelled",
    "ActivityChanged",
    "ActivityCompleted",
    "ActivityEvent",
    "ActivityFailed",
    "ActivityHandle",
    "ActivityLogEntry",
    "ActivityPriority",
    "ActivityService",
    "ActivitySnapshot",
    "ActivityStarted",
    "ActivityStatus",
    "ActivityType",
    "LogLevel",
]
