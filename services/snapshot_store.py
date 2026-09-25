"""Snapshot store.

Filesystem persistence for the Engineering single source of truth. It writes a
fully loaded, engineering-enriched :class:`~models.snapshot.Snapshot` to a JSON
document and restores it again - with no PDM access on either side.

Responsibilities are deliberately narrow:
  * turn a Snapshot into JSON on disk (:meth:`save`) and back (:meth:`load`);
  * resolve a default file path from the snapshot ``id``.

It owns no application state and never mutates the Snapshot. All object-graph
knowledge lives in :mod:`services.snapshot_serialization`; this module only adds
the file/JSON layer. The default location is ``cache/pdm_snapshots/`` (created
on demand).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from models.snapshot import Snapshot
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict

#: Default directory for stored Engineering JSON documents.
DEFAULT_SNAPSHOT_DIRECTORY = Path("cache") / "pdm_snapshots"

#: File extension for stored snapshots.
SNAPSHOT_FILE_SUFFIX = ".json"

_SAFE_NAME = re.compile(r"[^0-9A-Za-z_.-]+")


class SnapshotStore:
    """Save and load Snapshots as JSON documents."""

    def __init__(self, directory: str | Path | None = None) -> None:
        self._directory = (
            Path(directory) if directory is not None else DEFAULT_SNAPSHOT_DIRECTORY
        )

    @property
    def directory(self) -> Path:
        """The directory in which snapshots are stored."""
        return self._directory

    def path_for(self, snapshot_id: str | None) -> Path:
        """Return the default file path for a snapshot ``id`` (sanitised)."""
        name = _SAFE_NAME.sub("_", str(snapshot_id)) if snapshot_id else "snapshot"
        return self._directory / f"{name}{SNAPSHOT_FILE_SUFFIX}"

    def save(self, snapshot: Snapshot, path: str | Path | None = None) -> Path:
        """Write ``snapshot`` to ``path`` (or the id-derived default) and return it."""
        target = Path(path) if path is not None else self.path_for(snapshot.id)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = snapshot_to_dict(snapshot)
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return target

    def load(self, path: str | Path) -> Snapshot:
        """Read and restore the Snapshot stored at ``path``."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return snapshot_from_dict(data)

    def load_by_id(self, snapshot_id: str | None) -> Snapshot | None:
        """Restore the snapshot stored under ``snapshot_id``, or ``None`` if absent."""
        target = self.path_for(snapshot_id)
        if not target.exists():
            return None
        return self.load(target)
