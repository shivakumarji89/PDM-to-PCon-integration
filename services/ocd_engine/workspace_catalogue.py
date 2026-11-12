"""One catalogue over the primary OCD root plus every reachable repository workspace.

Unreachable workspaces are skipped and reported in ``infos``; they never fail the load of the others. Each
workspace's manufacturer comes from its own ``ocd_article`` data (see :func:`catalogue_roots`).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from core.repository_workspace import WorkspaceInfo, catalogue_roots, check_location
from services.ocd_engine.catalogue import CatalogueError, CatalogueScan, OcdCatalogueService


class WorkspaceCatalogueService:
    """Same interface as :class:`OcdCatalogueService` for the pieces the Article OBX page uses."""

    def __init__(self, primary_root: str | Path, workspace_paths: list[str]) -> None:
        self._primary = OcdCatalogueService(primary_root)
        self._workspace_paths = [str(p) for p in workspace_paths if str(p or "").strip()]
        self._services: dict[str, OcdCatalogueService] = {}      # catalogue root -> service (keeps its caches)
        self.infos: dict[str, WorkspaceInfo] = {}

    @classmethod
    def for_workspace(cls, workspace_path: str) -> "WorkspaceCatalogueService":
        """A catalogue over exactly one workspace (no primary root), e.g. one manufacturer's repository."""
        return cls("", [workspace_path])

    @property
    def root(self) -> Path | None:
        """The primary root; with none, the first catalogue root of the first workspace (what ``scan`` reports)."""
        if self._primary.root is not None:
            return self._primary.root
        extras = self._extras()
        if extras:
            return extras[0][1].root
        return Path(self._workspace_paths[0]) if self._workspace_paths else None

    def _extras(self) -> list[tuple[str, OcdCatalogueService]]:
        """(workspace path, service) for each catalogue root of each currently reachable workspace."""
        found: list[tuple[str, OcdCatalogueService]] = []
        for path in self._workspace_paths:
            if not check_location(path).connected:
                continue
            for root in catalogue_roots(path):
                found.append((path, self._services.setdefault(str(root), OcdCatalogueService(root))))
        return found

    def _primary_usable(self) -> bool:
        return self._primary.root is not None and self._primary.root.is_dir()

    def fingerprint(self) -> str:
        extras = self._extras()
        parts = [self._primary.fingerprint() if self._primary_usable() else "-"]
        if not extras and not self._primary_usable():
            return self._primary.fingerprint()            # raises the primary's own "not found" error
        parts += [service.fingerprint() for _path, service in extras]
        return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()

    def scan(self, progress=None) -> CatalogueScan:
        extras = self._extras()
        if self._primary_usable():
            merged = self._primary.scan(progress)
        elif extras:
            merged = CatalogueScan(root=extras[0][1].root)
        else:
            return self._primary.scan(progress)           # raises the primary's own "not found" error
        per_workspace: dict[str, tuple[set[str], list[tuple[str, str]], list[str]]] = {}
        for path, service in extras:
            try:
                sub = service.scan()
            except (CatalogueError, OSError) as error:
                merged.skipped.append((str(service.root), str(error)))
                continue
            merged.programs.extend(sub.programs)
            merged.skipped.extend(sub.skipped)
            entry = per_workspace.setdefault(path, (set(), [], []))
            entry[0].update(sub.manufacturers())
            entry[1].extend(sub.skipped)
            entry[2].append(str(service.root))
        self.infos = {}
        for path in self._workspace_paths:
            status = check_location(path)
            manufacturers, skipped, roots = per_workspace.get(path, (set(), [], []))
            self.infos[path] = WorkspaceInfo(path, status, tuple(roots),
                                             tuple(sorted(manufacturers, key=str.lower)), tuple(skipped))
        merged.fingerprint = self.fingerprint()
        return merged

    def list_articles(self, program, series_id: str = ""):
        return self._primary.list_articles(program, series_id)
