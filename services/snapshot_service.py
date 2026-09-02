"""Snapshot service.

Thin service facade over the shared :class:`~core.snapshot_manager.SnapshotManager`.
Phase 3 wires access to the in-memory snapshot; Engineering JSON persistence adds
explicit save/load plus an optional autosave that mirrors every modification to
disk. All file/JSON work is delegated to :class:`~services.snapshot_store.SnapshotStore`.
"""
from __future__ import annotations

from pathlib import Path

from models.product import Product
from models.snapshot import Snapshot
from services.base_service import BaseService
from services.snapshot_store import SnapshotStore


class SnapshotService(BaseService):
    """Provides application-level access to the active snapshot."""

    def __init__(self, context) -> None:
        super().__init__(context)
        self._store: SnapshotStore | None = None
        self._autosave: bool = False

    def create_snapshot(self, product: Product | None = None) -> Snapshot:
        """Create a new empty in-memory snapshot and make it active."""
        return self.context.snapshot_manager.create_empty_snapshot(product)

    def get_snapshot(self) -> Snapshot | None:
        """Return the active snapshot, or ``None`` if none is loaded."""
        return self.context.snapshot_manager.get_active_snapshot()

    def clear_snapshot(self) -> None:
        """Discard the active snapshot."""
        self.context.snapshot_manager.clear_snapshot()

    def is_modified(self) -> bool:
        """Whether the active snapshot has been modified."""
        return self.context.snapshot_manager.is_modified()

    # -- Engineering JSON persistence -------------------------------------
    def save_active_snapshot(self, path: str | Path | None = None) -> Path | None:
        """Persist the active snapshot to JSON and return the written path.

        Returns ``None`` when there is no active snapshot. Uses the configured
        autosave store when present, otherwise a default-located store.
        """
        snapshot = self.get_snapshot()
        if snapshot is None:
            return None
        store = self._store or SnapshotStore()
        return store.save(snapshot, path)

    def load_snapshot(self, path: str | Path) -> Snapshot:
        """Restore a snapshot from JSON and make it the active snapshot."""
        store = self._store or SnapshotStore()
        snapshot = store.load(path)
        self.context.snapshot_manager.load_snapshot(snapshot)
        return snapshot

    def enable_autosave(self, directory: str | Path | None = None) -> None:
        """Persist the active snapshot to disk on every modification.

        Registers a change listener on the shared snapshot manager; the listener
        writes the Engineering JSON whenever the snapshot is flagged modified.
        Safe to call more than once (the listener is only registered once).
        """
        self._store = SnapshotStore(directory)
        if not self._autosave:
            self.context.snapshot_manager.add_change_listener(
                self._on_snapshot_changed
            )
            self._autosave = True

    def disable_autosave(self) -> None:
        """Stop mirroring modifications to disk."""
        if self._autosave:
            self.context.snapshot_manager.remove_change_listener(
                self._on_snapshot_changed
            )
            self._autosave = False

    def _on_snapshot_changed(self, snapshot: Snapshot | None) -> None:
        """Autosave listener: write the snapshot when autosave is active."""
        if self._autosave and self._store is not None and snapshot is not None:
            self._store.save(snapshot)

