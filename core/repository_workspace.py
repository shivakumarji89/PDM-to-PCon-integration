"""Repository location validation and OCD workspace discovery.

A location counts as connected only after it has actually been listed; the configured path is never altered.
The manufacturer of a workspace comes from its data (the ``manufacturer`` column of ``ocd_article``), and the
catalogue roots come from its folder structure, so no manufacturer name appears here.
"""
from __future__ import annotations

import errno
import os
from dataclasses import dataclass, field
from pathlib import Path

CONNECTED = "connected"
MISSING = "missing"
NOT_A_FOLDER = "not_a_folder"
NO_PERMISSION = "no_permission"
UNREACHABLE = "unreachable"

#: Windows error codes for an unreachable network share (bad network path / name not found / path not found on host).
_NETWORK_WINERRORS = {53, 67, 1203, 1222}


@dataclass(frozen=True)
class LocationStatus:
    path: str
    state: str
    detail: str = ""

    @property
    def connected(self) -> bool:
        return self.state == CONNECTED


def check_location(path: str | os.PathLike) -> LocationStatus:
    """Validate that ``path`` is a folder this user can list on this computer."""
    text = str(path or "").strip()
    if not text:
        return LocationStatus(text, MISSING, "No path configured.")
    try:
        with os.scandir(text):
            pass
    except FileNotFoundError:
        return LocationStatus(text, MISSING, f"Folder not found on this computer: {text}")
    except NotADirectoryError:
        return LocationStatus(text, NOT_A_FOLDER, f"Not a folder: {text}")
    except PermissionError as error:
        return LocationStatus(text, NO_PERMISSION, f"Access denied: {text} ({error.strerror or error})")
    except OSError as error:
        winerror = getattr(error, "winerror", None)
        if winerror in _NETWORK_WINERRORS or error.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH):
            return LocationStatus(text, UNREACHABLE, f"Network location unreachable: {text}")
        return LocationStatus(text, MISSING, f"Cannot open {text}: {error.strerror or error}")
    return LocationStatus(text, CONNECTED)


@dataclass(frozen=True)
class WorkspaceInfo:
    """Result of connecting one OCD repository workspace."""

    path: str
    status: LocationStatus
    catalogue_roots: tuple[str, ...] = ()
    manufacturers: tuple[str, ...] = ()
    skipped: tuple[tuple[str, str], ...] = field(default=())

    @property
    def connected(self) -> bool:
        return self.status.connected


def catalogue_roots(workspace: str | os.PathLike) -> list[Path]:
    """Folders under ``workspace`` that directly hold program folders with OCD data.

    ``workspace`` itself when its sub-folders are programs; otherwise each sub-folder that is (the usual
    ``_repository/<manufacturer-folder>/<program>`` layout).
    """
    from services.ocd_engine.catalogue import find_db_dir

    root = Path(workspace)

    def programs_with_data(folder: Path) -> bool:
        try:
            for entry in os.scandir(folder):
                if entry.is_dir() and not entry.name.startswith(".") and find_db_dir(Path(entry.path)) is not None:
                    return True
        except OSError:
            return False
        return False

    if programs_with_data(root):
        return [root]
    try:
        children = sorted((Path(e.path) for e in os.scandir(root) if e.is_dir() and not e.name.startswith(".")),
                          key=lambda p: p.name.lower())
    except OSError:
        return []
    return [child for child in children if programs_with_data(child)]


def connect_workspace(path: str | os.PathLike) -> WorkspaceInfo:
    """Validate ``path`` and, when reachable, discover its catalogue roots and manufacturers from its data."""
    from services.ocd_engine.catalogue import CatalogueError, OcdCatalogueService

    status = check_location(path)
    if not status.connected:
        return WorkspaceInfo(str(path), status)
    roots = catalogue_roots(path)
    manufacturers: set[str] = set()
    skipped: list[tuple[str, str]] = []
    for root in roots:
        try:
            scan = OcdCatalogueService(root).scan()
        except (CatalogueError, OSError) as error:
            skipped.append((str(root), str(error)))
            continue
        manufacturers.update(scan.manufacturers())
        skipped.extend(scan.skipped)
    return WorkspaceInfo(str(path), status, tuple(str(r) for r in roots),
                         tuple(sorted(manufacturers, key=str.lower)), tuple(skipped))
