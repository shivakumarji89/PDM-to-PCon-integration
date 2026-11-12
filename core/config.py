"""Application configuration.

Holds static application settings, including the read-only PDM (SQL Server)
connection parameters used by the data-access layer.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_ENV_VAR = "MK_WORKBENCH_CONFIG"

#: Settings the per-machine override file may change, with the JSON type each accepts.
OVERRIDABLE: dict[str, type] = {
    "xocd_svn_path": str,
    "metatype_repository_root": str,
    "repository_browser_roots": dict,
    "repository_workspaces": list,
    "hm_repository_workspace": str,
    "knoll_repository_workspace": str,
}


def _default_override_path() -> Path:
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    return base / "workbench_config.json"


#: Selectable PDM databases, mapped to their (server, database) pair. Values
#: mirror the legacy PDM Maintenance tool's database selector.
PDM_DATABASE_PRESETS: dict[str, tuple[str, str]] = {
    "PDM Test": ("DBCHIP11V", "PDMTEST"),
    "PDM Live": ("DBCHIP12V", "PDMLive"),
    "PDM Frozen": ("DBCHIP12V", "PDMFrozen"),
}


@dataclass
class AppConfig:
    """Application settings with default values."""

    project_name: str = "MK Product Workbench"
    app_version: str = "0.4.0"
    workspace_path: str = "workspace/"
    snapshot_location: str = "workspace/snapshots/"
    temp_folder: str = "workspace/tmp/"
    # SVN XOCD publish target. Only this folder is ever used as the commit boundary.
    xocd_svn_path: str = r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\WS\Catalogue\Xocd"

    # PDM (SQL Server) connection parameters. Defaults mirror the proven V1
    # configuration; the connection string is assembled in PDMRepository.
    pdm_driver: str = "{SQL Server}"
    pdm_server: str = "DBCHIP12V"
    pdm_database: str = "PDMLive"
    pdm_trusted_connection: bool = True

    # Catalogue scope: only catalogues whose primary Site matches this region
    # (PDM ``Site.Site``) are fetched, so obsolete and non-region catalogues are
    # never stored. Default "UK".
    catalogue_region: str = "UK"
    # Persistent Maintenance repository ↔ PDM connection registry.
    repository_connection_registry: str = "workspace/repository_connections.json"

    # Published repository roots shown together in the Maintenance Repository Browser.
    # Each root contributes its immediate series folders to one logical browser.
    repository_browser_roots: dict[str, str] = field(default_factory=lambda: {
        "Seating": r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\WS\Seating\Seating",
        "Tables": r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\WS\Tables\Tables",
    })

    # OFML ``_repository`` workspace of each manufacturer. The home-page repository status and the QA module's
    # Manufacturer selector both read these two, and their catalogue (series/program/article) is discovered from
    # the folders and OCD data under each; nothing about series is configured. Override per machine.
    hm_repository_workspace: str = r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository"
    knoll_repository_workspace: str = r"C:\KnollSVN\Staging\HermanMiller\_repository"

    # Further OFML ``_repository`` workspaces merged into the Article OBX catalogue (manufacturer read from the
    # data). A missing or unreadable entry is reported, not an error.
    repository_workspaces: list[str] = field(default_factory=list)

    # Problems found while reading the per-machine override file (shown, never fatal).
    config_warnings: list[str] = field(default_factory=list)

    # Root of the OFML ``hmx`` engineering repository scanned (read-only) by the
    # Metatype module. Override per machine; scans also accept an explicit root.
    metatype_repository_root: str = r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx"

    # Metatype staged writing is OFF unless BOTH are set: a staging working copy distinct from the repository
    # above, and the name of whoever authorised writing to it. ebmkdb.exe is authorised separately.
    metatype_staging_root: str = ""
    metatype_staging_authorised_by: str = ""
    metatype_build_authorised: bool = False
    # Owner decisions that keep property creation blocked until set explicitly (see the Metatype decision document):
    metatype_mode_policy_confirmed: bool = False      # D4: confirm mode 3 (+128 sort order, +8192 validity)
    metatype_text_fallback_encoding: str = ""         # D5: "cp1252" or "utf-8" for non-ASCII text in an empty/ASCII go_texts

    @property
    def manufacturer_workspaces(self) -> dict[str, str]:
        """Manufacturer label -> configured ``_repository`` workspace, in display order."""
        return {"HM": self.hm_repository_workspace, "Knoll": self.knoll_repository_workspace}

    @classmethod
    def load(cls, path: str | os.PathLike | None = None) -> "AppConfig":
        """Defaults plus the optional per-machine override file.

        The file is ``$MK_WORKBENCH_CONFIG`` or ``workbench_config.json`` beside the application. It may
        override the keys in :data:`OVERRIDABLE`; ``%VAR%`` references in path values are expanded so one shared
        file can serve machines whose drive layout differs. An absent file means defaults; an unreadable or
        invalid one is recorded in ``config_warnings`` and the defaults are kept.
        """
        config = cls()
        source = Path(path) if path else Path(os.environ.get(CONFIG_ENV_VAR) or _default_override_path())
        if not source.is_file():
            if path or os.environ.get(CONFIG_ENV_VAR):
                config.config_warnings.append(f"Configuration file not found: {source}")
            return config
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("top level must be an object")
        except (OSError, ValueError) as error:
            config.config_warnings.append(f"Configuration file {source} ignored: {error}")
            return config
        for key, value in data.items():
            kind = OVERRIDABLE.get(key)
            if kind is None:
                config.config_warnings.append(f"Unknown configuration key ignored: {key}")
            elif kind is str and isinstance(value, str):
                setattr(config, key, os.path.expandvars(value) if key.endswith(("path", "root", "workspace")) else value)
            elif kind is list and isinstance(value, list) and all(isinstance(v, str) for v in value):
                setattr(config, key, [os.path.expandvars(v) for v in value])
            elif kind is dict and isinstance(value, dict) and all(isinstance(v, str) for v in value.values()):
                setattr(config, key, {str(k): os.path.expandvars(v) for k, v in value.items()})
            else:
                config.config_warnings.append(f"Invalid value for {key} ignored")
        return config

    def pdm_connection_string(self) -> str:
        """Assemble the pyodbc connection string for the PDM database."""
        parts = [
            f"DRIVER={self.pdm_driver};",
            f"SERVER={self.pdm_server};",
            f"DATABASE={self.pdm_database};",
        ]
        if self.pdm_trusted_connection:
            parts.append("Trusted_Connection=yes;")
        return "".join(parts)

    def set_pdm_database(self, preset_name: str) -> bool:
        """Point the PDM connection at the named preset's server/database.

        Returns ``True`` when the preset is known and applied, ``False``
        otherwise (the current connection is left unchanged).
        """
        preset = PDM_DATABASE_PRESETS.get(preset_name)
        if preset is None:
            return False
        self.pdm_server, self.pdm_database = preset
        return True

    def active_pdm_preset(self) -> str:
        """Return the preset name matching the current server/database, or ""."""
        for name, (server, database) in PDM_DATABASE_PRESETS.items():
            if server == self.pdm_server and database == self.pdm_database:
                return name
        return ""
