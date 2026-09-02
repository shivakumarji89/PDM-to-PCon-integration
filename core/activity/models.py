"""Activity Framework - data model.

Pure, dependency-free data structures describing the state of a single
long-running operation (a "activity"). This module contains no service logic,
no event publishing, and no UI - only data - so it stays lightweight and is
trivially unit-testable.

The model is intentionally open for extension:
  * ``Activity.type`` is a plain string (``ActivityType`` provides the common
    constants) so new operations never require changing this module.
  * Every field has a default, so additional fields can be added later without
    breaking existing consumers or call sites.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Mapping
from uuid import uuid4


class ActivityStatus(str, Enum):
    """Lifecycle state of an activity."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActivityType(str, Enum):
    """Common activity types (open vocabulary).

    Consumers may use one of these constants or pass any other string. The
    framework stores the value as a plain string, so new operations (Generate,
    Export, Import, Validation, Synchronization, Batch, Background Jobs, ...)
    can be reported without modifying the framework.
    """

    LOAD = "load"
    GENERATE = "generate"
    EXPORT = "export"
    IMPORT = "import"
    VALIDATION = "validation"
    SYNCHRONIZATION = "synchronization"
    BATCH = "batch"
    GENERIC = "generic"


class ActivityPriority(str, Enum):
    """Optional priority for future sorting and filtering."""

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class LogLevel(str, Enum):
    """Severity of an activity log entry."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ActivityLogEntry:
    """A single chronological log line belonging to an activity.

    Immutable: entries are appended and never modified, so freezing them makes
    them safe to hand out inside an :class:`ActivitySnapshot`.
    """

    message: str
    level: LogLevel = LogLevel.INFO
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class Activity:
    """The full state of one long-running operation.

    An *activity* models the lifecycle of an operation; measurable progress is
    optional. Progress can be item-based (``processed_items`` / ``total_items``),
    stage-based (``stage_index`` / ``total_stages``), or absent entirely (an
    indeterminate activity such as "Connecting to database"). Percentage is a
    derived value, never the primary source of truth.

    Pure data plus small, side-effect-free helpers. Every field has a default so
    the framework can evolve (new fields, child activities, richer timing)
    without breaking callers.
    """

    # -- identity ----------------------------------------------------------
    title: str = ""
    #: Activity type as a plain string (see :class:`ActivityType` for constants).
    type: str = ActivityType.GENERIC.value
    #: Stable unique identifier assigned at creation.
    id: str = field(default_factory=lambda: uuid4().hex)
    #: Optional priority for future sorting / filtering.
    priority: ActivityPriority = ActivityPriority.NORMAL

    # -- lifecycle ---------------------------------------------------------
    status: ActivityStatus = ActivityStatus.PENDING
    error_message: str = ""

    # -- progress (optional; percentage is derived, never stored) ----------
    total_items: int = 0
    processed_items: int = 0

    # -- stages (optional) -------------------------------------------------
    stage_name: str = ""
    stage_index: int = 0
    total_stages: int = 0

    # -- current activity detail ------------------------------------------
    current_step: str = ""
    current_item: str = ""

    # -- contextual information (optional, free-form) ----------------------
    #: Arbitrary context for display, e.g. {"Family": "Bolster", "Products": 1240}.
    context: dict[str, object] = field(default_factory=dict)

    # -- relationships (parent / child; ids only, the registry owns objects)
    parent_id: str | None = None
    child_ids: list[str] = field(default_factory=list)

    # -- cancellation (future-ready) --------------------------------------
    supports_cancel: bool = False
    cancel_requested: bool = False

    # -- timing ------------------------------------------------------------
    start_time: datetime | None = None
    end_time: datetime | None = None

    # -- logging -----------------------------------------------------------
    #: Chronological log; retained after completion for troubleshooting.
    log: list[ActivityLogEntry] = field(default_factory=list)

    # -- derived: progress -------------------------------------------------
    @property
    def progress_percent(self) -> float | None:
        """Derived completion percentage (0-100), or ``None`` when indeterminate.

        Preference order: item-based, then stage-based. An activity with neither
        items nor stages is indeterminate and returns ``None`` (a UI should show
        a busy/indeterminate indicator rather than a percentage).
        """
        if self.total_items > 0:
            return min(100.0, max(0.0, self.processed_items / self.total_items * 100.0))
        if self.total_stages > 0:
            return min(100.0, max(0.0, self.stage_index / self.total_stages * 100.0))
        return None

    @property
    def is_determinate(self) -> bool:
        """Whether the activity can report a percentage."""
        return self.total_items > 0 or self.total_stages > 0

    # -- derived: lifecycle ------------------------------------------------
    @property
    def is_active(self) -> bool:
        """Whether the activity is pending or running."""
        return self.status in (ActivityStatus.PENDING, ActivityStatus.RUNNING)

    @property
    def is_finished(self) -> bool:
        """Whether the activity reached a terminal state."""
        return self.status in (
            ActivityStatus.COMPLETED,
            ActivityStatus.FAILED,
            ActivityStatus.CANCELLED,
        )

    # -- derived: timing ---------------------------------------------------
    @property
    def duration_seconds(self) -> float:
        """Elapsed seconds (0 until started; to ``end_time`` once finished)."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or datetime.now(timezone.utc)
        return max(0.0, (end - self.start_time).total_seconds())

    @property
    def processing_rate(self) -> float | None:
        """Processed items per second, or ``None`` when not measurable.

        Future-ready: computed from ``processed_items`` and elapsed time; a UI
        may show it or ignore it.
        """
        duration = self.duration_seconds
        if duration <= 0.0 or self.processed_items <= 0:
            return None
        return self.processed_items / duration

    @property
    def estimated_remaining_seconds(self) -> float | None:
        """Rough ETA from the processing rate, or ``None`` when unknown.

        Future-ready: derived only; no timers or background work are involved.
        """
        rate = self.processing_rate
        if rate is None or self.total_items <= 0:
            return None
        remaining = max(0, self.total_items - self.processed_items)
        if remaining == 0:
            return 0.0
        return remaining / rate

    # -- helpers -----------------------------------------------------------
    def add_log(
        self, message: str, level: LogLevel = LogLevel.INFO
    ) -> ActivityLogEntry:
        """Append a chronological log entry and return it."""
        entry = ActivityLogEntry(message=message, level=level)
        self.log.append(entry)
        return entry


@dataclass(frozen=True)
class ActivitySnapshot:
    """An immutable, point-in-time view of an :class:`Activity`.

    The service publishes snapshots (not the live, mutable :class:`Activity`) so
    UI consumers can never accidentally mutate framework state, and so a value
    captured on one thread is safe to read on another. All derived values are
    pre-computed at capture time; ``context`` is a read-only mapping and ``log``
    is a tuple of frozen entries.
    """

    id: str
    type: str
    title: str
    status: ActivityStatus
    priority: ActivityPriority
    total_items: int
    processed_items: int
    progress_percent: float | None
    is_determinate: bool
    stage_name: str
    stage_index: int
    total_stages: int
    current_step: str
    current_item: str
    context: Mapping[str, object]
    parent_id: str | None
    child_ids: tuple[str, ...]
    supports_cancel: bool
    cancel_requested: bool
    start_time: datetime | None
    end_time: datetime | None
    duration_seconds: float
    processing_rate: float | None
    estimated_remaining_seconds: float | None
    error_message: str
    log: tuple[ActivityLogEntry, ...]
    is_active: bool
    is_finished: bool

    @classmethod
    def from_activity(cls, activity: Activity) -> "ActivitySnapshot":
        """Capture the current state of ``activity`` as an immutable snapshot."""
        return cls(
            id=activity.id,
            type=activity.type,
            title=activity.title,
            status=activity.status,
            priority=activity.priority,
            total_items=activity.total_items,
            processed_items=activity.processed_items,
            progress_percent=activity.progress_percent,
            is_determinate=activity.is_determinate,
            stage_name=activity.stage_name,
            stage_index=activity.stage_index,
            total_stages=activity.total_stages,
            current_step=activity.current_step,
            current_item=activity.current_item,
            context=MappingProxyType(dict(activity.context)),
            parent_id=activity.parent_id,
            child_ids=tuple(activity.child_ids),
            supports_cancel=activity.supports_cancel,
            cancel_requested=activity.cancel_requested,
            start_time=activity.start_time,
            end_time=activity.end_time,
            duration_seconds=activity.duration_seconds,
            processing_rate=activity.processing_rate,
            estimated_remaining_seconds=activity.estimated_remaining_seconds,
            error_message=activity.error_message,
            log=tuple(activity.log),
            is_active=activity.is_active,
            is_finished=activity.is_finished,
        )
