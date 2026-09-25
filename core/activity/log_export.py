"""Activity log export.

Renders :class:`~core.activity.models.ActivitySnapshot` objects into a plain
text log so the Activity timeline can be saved as a troubleshooting log file.
Pure and UI-independent (no widgets, no file IO) - callers decide where the text
goes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from core.activity.models import ActivitySnapshot

_LEVEL_WIDTH = 7


def _local(dt: datetime | None) -> str:
    if dt is None:
        return "--"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60:02d}s"


def format_activity_log(
    snapshots: Iterable[ActivitySnapshot], *, generated_at: datetime | None = None
) -> str:
    """Return a chronological plain-text log for ``snapshots``.

    The body merges every activity's log entries into one timeline sorted by
    timestamp (``[time] LEVEL [Activity] message``); a summary of each activity
    (status, duration, item counts, error) follows.
    """
    snapshots = list(snapshots)
    generated = generated_at or datetime.now(timezone.utc)

    lines: list[str] = [
        "# MK Product Workbench - Activity Log",
        f"# Generated: {_local(generated)}",
        f"# Activities: {len(snapshots)}",
        "",
    ]

    # Merged chronological stream of every log line across all activities.
    entries: list[tuple[datetime, str, str, str]] = []
    for snap in snapshots:
        for entry in snap.log:
            entries.append(
                (entry.timestamp, entry.level.value.upper(), snap.title, entry.message)
            )
    entries.sort(key=lambda item: item[0])
    for timestamp, level, title, message in entries:
        lines.append(f"[{_local(timestamp)}] {level:<{_LEVEL_WIDTH}} [{title}] {message}")

    if not entries:
        lines.append("(no log entries)")

    lines.extend(["", "=== Summary ==="])
    ordered = sorted(
        snapshots,
        key=lambda s: s.start_time or datetime.max.replace(tzinfo=timezone.utc),
    )
    for snap in ordered:
        items = (
            f", {snap.processed_items}/{snap.total_items} items"
            if snap.total_items else ""
        )
        error = f" - {snap.error_message}" if snap.error_message else ""
        lines.append(
            f"- {snap.title}: {snap.status.value.upper()} "
            f"in {_duration(snap.duration_seconds)}{items}{error}"
        )

    return "\n".join(lines) + "\n"
