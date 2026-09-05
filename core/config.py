"""Application configuration.

Holds static application settings, including the read-only PDM (SQL Server)
connection parameters used by the data-access layer.
"""
from __future__ import annotations

from dataclasses import dataclass


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
    repository_connection_registry: str = "workspace/repository_connections.json"

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
