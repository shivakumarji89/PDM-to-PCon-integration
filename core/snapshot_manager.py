"""In-memory snapshot manager.

Owns the single active :class:`~models.snapshot.Snapshot` for the running
application and tracks its lifecycle status. This is the central access point
for engineering data throughout the app.

Phase 3: in-memory only - no file, JSON, SQL, or MDB operations. The manager may
notify registered listeners when the active snapshot is modified, but it never
performs persistence itself: listeners (e.g. an autosave in the service layer)
own any file/JSON work.
"""
from __future__ import annotations

from typing import Callable

from core.enums import SnapshotStatus
from models.product import Product
from models.snapshot import Snapshot

#: A change listener receives the active snapshot (or ``None`` when cleared).
ChangeListener = Callable[[Snapshot | None], None]


class SnapshotManager:
    """Creates, holds, and clears the active in-memory snapshot."""

    def __init__(self) -> None:
        self._snapshot: Snapshot | None = None
        self._listeners: list[ChangeListener] = []

    def add_change_listener(self, listener: ChangeListener) -> None:
        """Register ``listener`` to be called when the snapshot is modified."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_change_listener(self, listener: ChangeListener) -> None:
        """Unregister a previously added change listener (no error if absent)."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_changed(self) -> None:
        """Notify every registered listener of the current snapshot."""
        for listener in list(self._listeners):
            listener(self._snapshot)

    def create_empty_snapshot(self, product: Product | None = None) -> Snapshot:
        """Create a new empty snapshot and make it active."""
        snapshot = Snapshot(status=SnapshotStatus.READY, product=product)
        self._snapshot = snapshot
        return snapshot

    def load_snapshot(self, snapshot: Snapshot) -> None:
        """Load an existing snapshot into memory as the active snapshot."""
        self._snapshot = snapshot
        snapshot.status = SnapshotStatus.READY

    def clear_snapshot(self) -> None:
        """Discard the active snapshot."""
        self._snapshot = None

    def get_active_snapshot(self) -> Snapshot | None:
        """Return the active snapshot, or ``None`` if none is loaded."""
        return self._snapshot

    def has_snapshot(self) -> bool:
        """Whether an active snapshot is currently loaded."""
        return self._snapshot is not None

    @property
    def status(self) -> SnapshotStatus:
        """Current snapshot status (``NOT_CREATED`` when none is loaded)."""
        if self._snapshot is None:
            return SnapshotStatus.NOT_CREATED
        return self._snapshot.status

    def mark_modified(self) -> None:
        """Flag the active snapshot as modified."""
        if self._snapshot is not None:
            self._snapshot.status = SnapshotStatus.MODIFIED
            self._notify_changed()

    def is_modified(self) -> bool:
        """Whether the active snapshot has been modified."""
        return self._snapshot is not None and self._snapshot.status == SnapshotStatus.MODIFIED
