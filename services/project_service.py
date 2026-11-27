"""Project service: save/open the whole working session as a ``.mkproj`` file.

A project bundles the full engineering session - name, current workflow step and
the entire snapshot (properties, values, options, articles, the per-article
link, BOM, VARCOND terms, prefix lengths, option increments and every
engineering edit) - as one JSON document, so a user can close the app and later
reopen exactly where they left off. The snapshot round-trip reuses
:mod:`services.snapshot_serialization`.
"""
from __future__ import annotations

import json
from pathlib import Path

from core.enums import SnapshotStatus, WorkflowStep
from models.project import Project
from services.base_service import BaseService
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict

#: On-disk format marker and current schema version for ``.mkproj`` files.
PROJECT_FORMAT = "mkproj"
PROJECT_VERSION = 1
#: Default project file extension.
PROJECT_SUFFIX = ".mkproj"


class ProjectService(BaseService):
    """Manages project lifecycle: new, save, open, close."""

    def __init__(self, context) -> None:
        super().__init__(context)
        self._name: str = ""
        self._path: Path | None = None

    # -- state -------------------------------------------------------------
    @property
    def name(self) -> str:
        """The active project's name (empty when unnamed/none)."""
        return self._name

    @property
    def path(self) -> Path | None:
        """The active project's file path, or ``None`` if never saved."""
        return self._path

    # -- lifecycle ---------------------------------------------------------
    def new_project(self, name: str = "") -> None:
        """Start a fresh project: discard the active snapshot and reset state."""
        self.context.snapshot_manager.clear_snapshot()
        self._name = name
        self._path = None

    def save_project(
        self, path: str | Path, name: str = "", current_step: str = ""
    ) -> Path:
        """Write the active session to ``path`` as a ``.mkproj`` JSON document.

        ``current_step`` is the workflow step value to restore on reopen. Raises
        :class:`ValueError` when there is no active snapshot to save.
        """
        snapshot = self.context.active_snapshot
        if snapshot is None:
            raise ValueError("No active snapshot to save.")

        target = Path(path)
        if target.suffix == "":
            target = target.with_suffix(PROJECT_SUFFIX)
        target.parent.mkdir(parents=True, exist_ok=True)

        name = name or self._name or target.stem
        document = {
            "format": PROJECT_FORMAT,
            "version": PROJECT_VERSION,
            "name": name,
            "current_step": current_step,
            "snapshot": snapshot_to_dict(snapshot),
        }
        target.write_text(
            json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        self._name = name
        self._path = target
        # A freshly-saved snapshot is no longer "modified".
        snapshot.status = SnapshotStatus.READY
        return target

    def read_project(self, path: str | Path) -> Project:
        """Read and reconstruct a project without changing active application state.

        Safe to run in a worker thread: this performs file I/O and pure snapshot
        deserialization only. The returned Project is activated on the GUI thread.
        """
        source = Path(path)
        document = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("format") != PROJECT_FORMAT:
            raise ValueError(f"Not a {PROJECT_SUFFIX} project file: {source}")

        snapshot = snapshot_from_dict(document.get("snapshot") or {})
        return Project(
            name=document.get("name", "") or source.stem,
            selected_product=snapshot.product,
            snapshot=snapshot,
            current_step=self._step_from(document.get("current_step")),
        )

    def activate_project(self, project: Project, path: str | Path) -> Project:
        """Publish a previously-read project into active application state.

        Must be called on the GUI thread because it mutates the shared context.
        """
        self.context.snapshot_manager.load_snapshot(project.snapshot)
        # A saved project is a PDM-side working snapshot: publish it as such so
        # Maintenance's PDM tab resolves it (the MDB snapshot is left alone).
        self.context.adopt_loaded_pdm_snapshot()
        self._name = project.name
        self._path = Path(path)
        return project

    def load_project(self, path: str | Path) -> Project:
        """Synchronously restore a project for existing non-UI callers/tests.

        The UI uses read_project in a worker and activate_project on the GUI
        thread so large project files do not block the event loop.
        """
        project = self.read_project(path)
        return self.activate_project(project, path)

    def close_project(self) -> None:
        """Discard the active snapshot and clear project state."""
        self.context.snapshot_manager.clear_snapshot()
        self._name = ""
        self._path = None

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _step_from(value) -> WorkflowStep:
        """Map a stored step value back to a :class:`WorkflowStep` (PRODUCT fallback)."""
        try:
            return WorkflowStep(value)
        except (ValueError, TypeError):
            return WorkflowStep.PRODUCT
